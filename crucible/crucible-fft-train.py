#!/usr/bin/env python3
# crucible-fft-train.py — FULL fine-tune on a PACKED corpus (crucible-fft-pack.py), multi-GPU FSDP2.
#
#   accelerate launch --config_file fft-fsdp.yaml crucible-fft-train.py \
#       --model-dir <base> --packed <pack-dir> --save-dir <model-out> --out runs/fft-<..>.json
#
# BUILT FOR THROUGHPUT, because it runs on rented hardware:
#   * no tokenizing or JSON on the GPU box: crucible-fft-pack.py did it on CPU beforehand
#   * packed, padding-free rows: whole blocks back to back in fixed-length rows, positions reset at
#     every block start, FlashAttention varlen so no token attends across a block boundary. Every
#     forward carries --pack-tokens real tokens instead of one ~2k block.
#   * fixed row length -> static shapes -> --compile works without recompiling every step
#   * Liger fused RMSNorm / SwiGLU / RoPE. (Fused linear-CE is OFF: vocab is 16, there is no big
#     logits tensor to avoid.)
#   * activation checkpointing OFF by default; it costs ~30% compute. Turn it on only if the
#     memory probe (--probe) says the row length does not fit.
#   * token-weighted loss across grad-accum and ranks (num_items_in_batch), so a row of long blocks
#     and a row of short ones weigh by their loss tokens, as a single big batch would.
#
# COMPARABILITY with the LoRA lineage: examples are encoded by crucible-grids15.encode_ttt_example
# (loss on output grids only), screened by the same pair hash, and the holdout is the same blocks
# evaluated the same way -- per block mean loss, per task mean, mean over tasks.
#
# OUTPUT: --save-dir gets a full bf16 model + tokenizer, the artifact the Kaggle upload takes today.

import argparse, json, math, os, sys, time

ap = argparse.ArgumentParser(description="Full fine-tune on a packed corpus (FSDP2).")
ap.add_argument("--model-dir", required=True)
ap.add_argument("--packed", required=True, help="output dir of crucible-fft-pack.py")
ap.add_argument("--lr", type=float, default=1e-5)
ap.add_argument("--epochs", type=int, default=2)
ap.add_argument("--warmup-ratio", type=float, default=0.03)
ap.add_argument("--min-lr-ratio", type=float, default=0.0)
ap.add_argument("--weight-decay", type=float, default=0.0)
ap.add_argument("--max-grad-norm", type=float, default=1.0)
ap.add_argument("--grad-accum", type=int, default=1, help="rows per rank per optimizer step")
ap.add_argument("--attn", default="kernels-community/flash-attn2",
                help="attn_implementation. Hopper: kernels-community/flash-attn3")
ap.add_argument("--liger", default="on", choices=["on", "off"])
ap.add_argument("--optim", default="adamw", choices=["adamw", "adamw8bit"],
                help="adamw: torch fused AdamW, fp32 state (multi-GPU FSDP). adamw8bit: bitsandbytes "
                     "AdamW8bit, 8-bit state -- the single-GPU (Colab A100 80GB) mode, where fp32 weights + "
                     "fp32 grads + fp32 Adam state (~64 GB for 4B) would not leave room for activations.")
ap.add_argument("--master-dtype", default="fp32", choices=["fp32", "bf16"],
                help="dtype of the weights the optimizer updates. fp32 (default): FSDP2 keeps an fp32 "
                     "master copy and casts to bf16 for forward/backward (fft-fsdp.yaml mixed_precision "
                     "bf16). bf16: the old behaviour -- AdamW steps bf16 weights directly, and at lr ~1e-5 "
                     "most updates are below bf16's resolution at the weight's value and round away "
                     "(the same failure the LoRA trainer had: 48% of lora_A updates lost at 2e-5).")
ap.add_argument("--grad-ckpt", default="off", choices=["on", "off"])
ap.add_argument("--compile", default="off", choices=["on", "off"])
ap.add_argument("--probe", type=int, default=0,
                help="run N optimizer steps, report peak memory and tokens/s, and exit. Use it on "
                     "the rented box to pick --pack-tokens/--grad-ckpt before the real run.")
ap.add_argument("--probe-eval", default="off", choices=["on", "off"],
                help="with --probe: read the holdout and P1/P2/P3 at step 0 and at the probe's last step and record them "
                     "(the lr probe compares learning rates on these)")
ap.add_argument("--peak-tflops", type=float, default=989.0,
                help="per-GPU dense bf16 peak for the MFU readout (H100 SXM 989)")
ap.add_argument("--tripwire-loss", type=float, default=2.0)
ap.add_argument("--tripwire-steps", type=int, default=20)
ap.add_argument("--log-every", type=int, default=10)
ap.add_argument("--checkpoint-every", type=int, default=200)
ap.add_argument("--ckpt-dir", default="")
ap.add_argument("--probe-every", type=int, default=0, help="probes (P1-P4) every N steps as well as at checkpoints, for a gate that needs a reading sustained over several reads; 0 = only at checkpoints")
ap.add_argument("--async-ckpt", default="off", choices=["on", "off"],
                help="on: copy weights + optimizer state to CPU RAM "
                     "(seconds), write them with accelerate's own writer in a background thread (same files as save_state). "
                     "Single process only; falls back to the blocking save when free RAM cannot hold the copy.")
ap.add_argument("--resume-from", default="")
ap.add_argument("--continue-from", default="",
                help="start a NEW hop from a previous hop's checkpoint: weights and optimizer moments load, the step "
                     "counter and the lr schedule start fresh (FFT spec: each hop runs its own warmup and decay)")
ap.add_argument("--probes", default="", help="JSON {set: [ARC-style blocks]}: teacher-forced exact-match reads at "
                "step 0, every checkpoint and the end (FFT spec §1 P1/P2/P3). A fall of --probe-alert-drop or "
                "more on P1 or P2 against step 0 is logged as an ALERT; the run is never stopped by it.")
ap.add_argument("--probe-alert-drop", type=int, default=5)
ap.add_argument("--checkpoint-at-hours", type=float, default=0.0,
                help="also save ONE checkpoint when this process has run this many hours (0 = off), so its upload can "
                     "verify before a session time limit (Colab Pro+ 24 h: 22.5 leaves ~90 min for the ~50 min upload)")
ap.add_argument("--w-copied", type=float, default=-1.0,
                help="weighted loss (as the LoRA legs): answer cells equal to the input cell weigh this, changed cells "
                     "--w-changed, markers 1.0; only where the pair keeps its shape. <0 = unweighted (default)")
ap.add_argument("--w-changed", type=float, default=1.0)
ap.add_argument("--keep-local", type=int, default=2,
                help="local checkpoint dirs (ckpt/step-NNNNNN) kept; a dir holding an UPLOADING file is never pruned")
ap.add_argument("--holdout-every", type=int, default=0, help="optimizer steps; 0 = start and end only")
ap.add_argument("--save-dir", required=True)
ap.add_argument("--out", required=True)
args = ap.parse_args()

import numpy as np
import torch
from accelerate import Accelerator
from transformers import AutoModelForCausalLM, AutoTokenizer
import importlib.util as _ilu, os as _os
_sp = _ilu.spec_from_file_location("g15", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "crucible-grids15.py"))
fmt = _ilu.module_from_spec(_sp); _sp.loader.exec_module(fmt)


acc = Accelerator(gradient_accumulation_steps=args.grad_accum)
W, R = acc.num_processes, acc.process_index
say = acc.print

# ---- packed data ----
idx = json.load(open(os.path.join(args.packed, "index.json")))
L = idx["pack_tokens"]
tokens = np.fromfile(os.path.join(args.packed, "tokens.u8"), np.uint8).reshape(-1, L)
mask = np.fromfile(os.path.join(args.packed, "mask.u8"), np.uint8).reshape(-1, L)
rows = json.load(open(os.path.join(args.packed, "rows.json")))
if len(rows) != tokens.shape[0]:
    sys.exit(f"FAIL: rows.json has {len(rows)} rows, tokens.u8 has {tokens.shape[0]}")
hold = None
if os.path.exists(os.path.join(args.packed, "holdout.json")):
    hold = (np.fromfile(os.path.join(args.packed, "holdout.u8"), np.uint8),
            np.fromfile(os.path.join(args.packed, "holdout_mask.u8"), np.uint8),
            json.load(open(os.path.join(args.packed, "holdout.json"))))

per_step = W * args.grad_accum
steps_per_epoch = len(rows) // per_step
total_steps = steps_per_epoch * args.epochs
dropped = len(rows) - steps_per_epoch * per_step
if total_steps == 0:
    sys.exit("FAIL: fewer rows than one optimizer step")

say("== CRUCIBLE FFT (packed) ==")
say(f"  packed            {args.packed}  sha {idx['sha256_tokens_mask'][:16]}")
say(f"  corpus            {idx['blocks']} blocks -> {idx['rows']} rows x {L} tokens, fill {idx['fill']:.1%}, "
    f"{idx['loss_tokens']:,} loss tokens, {idx['rejected_vs_eval']} rejected vs eval")
say(f"  ranks {W}  grad-accum {args.grad_accum}  -> {per_step} rows = {per_step*L:,} tokens per optimizer step")
say(f"  schedule          {steps_per_epoch} steps/epoch x {args.epochs} = {total_steps}  "
    f"({dropped} tail row(s) dropped so every rank runs the same count)")
say(f"  kernels           attn={args.attn} liger={args.liger} grad-ckpt={args.grad_ckpt} compile={args.compile}")

# ---- model ----
tokenizer = fmt.load_tokenizer()
if args.liger == "on":
    from liger_kernel.transformers import apply_liger_kernel_to_qwen3
    apply_liger_kernel_to_qwen3(rope=True, rms_norm=True, swiglu=True,
                                cross_entropy=False, fused_linear_cross_entropy=False)
MASTER = torch.float32 if args.master_dtype == "fp32" else torch.bfloat16
if args.master_dtype == "fp32" and acc.state.mixed_precision != "bf16":
    sys.exit("FAIL: --master-dtype fp32 needs mixed_precision bf16 in the accelerate config "
             "(fft-fsdp.yaml), or forward/backward would run in fp32")
model = AutoModelForCausalLM.from_pretrained(args.model_dir, dtype=MASTER,
                                             attn_implementation=args.attn, local_files_only=True)
model.config.use_cache = False
if args.grad_ckpt == "on":
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
n_params = sum(p.numel() for p in model.parameters())
say(f"  model             {n_params/1e9:.3f}B params, all trainable, master {args.master_dtype}, compute bf16")

if args.optim == "adamw8bit":
    import bitsandbytes as bnb
    opt = bnb.optim.AdamW8bit(model.parameters(), lr=args.lr, weight_decay=args.weight_decay,
                              betas=(0.9, 0.95), eps=1e-8)
else:
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay,
                            betas=(0.9, 0.95), eps=1e-8, fused=True)
def _meminfo():
    m = {l.split(":")[0]: int(l.split()[1]) * 1024 for l in open("/proc/meminfo") if l.split()[0].rstrip(":") in ("MemTotal", "MemAvailable")}
    return m.get("MemTotal", 0), m.get("MemAvailable", 0)


say(f"  optimizer         {args.optim}")
_mt, _ma = _meminfo(); say(f"  RAM               {_mt/2**30:.0f} GiB total, {_ma/2**30:.0f} GiB available; async checkpoints {args.async_ckpt}")
warm = max(1, int(total_steps * args.warmup_ratio))


def lr_at(s):
    if s < warm:
        return (s + 1) / warm
    # Spec §1: 3% warmup, then LINEAR to min_lr_ratio (0 by default), as NVARC.
    prog = (s - warm) / max(1, total_steps - warm)
    return args.min_lr_ratio + (1 - args.min_lr_ratio) * (1 - prog)


sched = torch.optim.lr_scheduler.LambdaLR(opt, lr_at)
# Scheduler NOT prepared: accelerate's wrapper steps it once per process per call.
model, opt = acc.prepare(model, opt)
if args.compile == "on":
    model = torch.compile(model)


def cell_weights(ids_np, m_np, spans):
    """Per-token loss weight for one packed row (--w-copied >= 0). For each block, each answer span (a run of the
    loss mask) is compared cell by cell with the input grid that precedes it in the same block, when both grids
    have the same shape: copied cells weigh --w-copied, changed cells --w-changed; row/end markers and answers of
    resized pairs weigh 1.0. Non-loss tokens weigh 0."""
    w = np.zeros(len(ids_np), dtype=np.float32)
    w[m_np.astype(bool)] = 1.0
    nl = fmt.NEWLINE_ID
    digits = set(range(10))
    def grid_at(a, b):
        rows_, cur, pos_ = [], [], []
        for k in range(a, b):
            t = int(ids_np[k])
            if t in digits: cur.append((t, k))
            elif t == nl:
                if cur: rows_.append(cur); cur = []
        if cur: rows_.append(cur)
        return rows_
    for start, n in spans:
        mm = m_np[start:start + n].astype(bool)
        k = 0; prev_end = 0
        while k < n:
            if mm[k]:
                a = k
                while k < n and mm[k]: k += 1
                out_g = grid_at(start + a, start + k)
                # the input grid: exactly the user turn's grid -- the tokens between the LAST user role token and
                # the IM_END that closes it, in [prev_end, a)
                seg_ids = ids_np[start + prev_end:start + a]
                us = [j for j in range(len(seg_ids)) if int(seg_ids[j]) == fmt.USER_ID]
                in_g = []
                if us:
                    u = us[-1]
                    e = next((j for j in range(u, len(seg_ids)) if int(seg_ids[j]) == fmt.IM_END_ID), len(seg_ids))
                    in_g = grid_at(start + prev_end + u + 1, start + prev_end + e)
                if out_g and len(in_g) == len(out_g) and all(len(x) == len(y) for x, y in zip(in_g, out_g)):
                    for ri, ro in zip(in_g, out_g):
                        for (ti, _), (to, ko) in zip(ri, ro):
                            w[ko] = W_COPIED if ti == to else W_CHANGED
                prev_end = k
            else:
                k += 1
    return w


W_COPIED, W_CHANGED = args.w_copied, args.w_changed


def row_batch(r):
    """One packed row -> input_ids, labels, position_ids, FlashAttention varlen kwargs."""
    ids = torch.from_numpy(tokens[r].astype(np.int64))
    m = torch.from_numpy(mask[r].astype(bool))
    labels = torch.where(m, ids, torch.full_like(ids, -100))
    pos = torch.empty(L, dtype=torch.long)
    cu = [0]
    for start, n in rows[r]:
        pos[start:start + n] = torch.arange(n)
        cu.append(start + n)
    if cu[-1] < L:                      # pad tail: its own masked run
        pos[cu[-1]:] = torch.arange(L - cu[-1])
        cu.append(L)
    lens = [b - a for a, b in zip(cu, cu[1:])]
    dev = acc.device
    kw = dict(cu_seq_lens_q=torch.tensor(cu, dtype=torch.int32, device=dev),
              cu_seq_lens_k=torch.tensor(cu, dtype=torch.int32, device=dev),
              max_length_q=max(lens), max_length_k=max(lens))
    if W_COPIED >= 0:
        w = torch.from_numpy(cell_weights(tokens[r], mask[r], rows[r]))
        return (ids[None].to(dev, non_blocking=True), labels[None].to(dev, non_blocking=True),
                pos[None].to(dev, non_blocking=True), kw, float(w[1:].sum()), w[None].to(dev, non_blocking=True))
    return (ids[None].to(dev, non_blocking=True), labels[None].to(dev, non_blocking=True),
            pos[None].to(dev, non_blocking=True), kw, int(m[1:].sum()), None)


def block_loss(ids, m):
    """Mean loss over one unpacked block's loss tokens -- the LoRA trainer's per-block definition."""
    ids = torch.from_numpy(ids.astype(np.int64))[None].to(acc.device)
    lab = torch.where(torch.from_numpy(m.astype(bool))[None].to(acc.device), ids, torch.full_like(ids, -100))
    return model(input_ids=ids, labels=lab).loss.float()


t0 = time.time()
step, hist, holdout_evals, probe_evals = 0, [], [], []
gnorms = []   # pre-clip global grad norm per optimizer step (logged as a window mean)
ckpt = args.ckpt_dir or (os.path.splitext(args.out)[0] + "-ckpt")
probes = None
if args.probes:
    _raw = json.load(open(args.probes))
    probes = {}
    for _name, _blocks in _raw.items():
        enc = []
        for _b in _blocks:
            demos = [{"input": p["input"], "output": p["output"]} for p in _b["train"] + _b["test"] if p.get("output")]
            ids, labels = fmt.encode_ttt_example(tokenizer, demos)
            if len(ids) <= 8192: enc.append((ids, labels))
        probes[_name] = enc
    say("  probes            " + "  ".join(f"{k} {len(v)}" for k, v in probes.items()))


def write_record(status, **extra):
    if acc.is_main_process:
        # Departures from the FFT spec's full-run recipe (8 GPUs, fp32 AdamW state), stated in the
        # record so a trial's loss curve is never read as the recipe's.
        dev = ([f"optim {args.optim} (spec: adamw, fp32 state)"] if args.optim != "adamw" else []) + \
              ([f"{W} GPU(s) (spec: 8)"] if W != 8 else []) + \
              ([f"master {args.master_dtype} (spec: fp32)"] if args.master_dtype != "fp32" else [])
        json.dump({"status": status, "deviations": dev, "config": vars(args), "packed_index": idx, "ranks": W,
                   "step": step, "total_steps": total_steps, "loss_history": hist,
                   "holdout_evals": holdout_evals, "probe_evals": probe_evals, "hours": (time.time() - t0) / 3600, **extra},
                  open(args.out, "w"), indent=1)


def eval_holdout(tag):
    if hold is None:
        return
    ht, hm, meta = hold
    model.eval(); e0 = time.time()
    tids = sorted({x[0] for x in meta})
    sums = torch.zeros(len(tids), device=acc.device); cnts = torch.zeros(len(tids), device=acc.device)
    items = meta + [meta[0]] * ((-len(meta)) % W)          # equal forwards on every rank (FSDP)
    with torch.no_grad():
        for i in range(R, len(items), W):
            tid, at, n = items[i]
            l = block_loss(ht[at:at + n], hm[at:at + n])
            if i < len(meta):
                k = tids.index(tid); sums[k] += l; cnts[k] += 1
    sums, cnts = acc.reduce(sums, "sum"), acc.reduce(cnts, "sum")
    model.train()
    per_task = {t: float(s / c) for t, s, c in zip(tids, sums, cnts)}
    mean = sum(per_task.values()) / len(per_task)
    prev = holdout_evals[-1]["mean"] if holdout_evals else None
    holdout_evals.append({"tag": tag, "step": step, "mean": mean, "tasks": len(per_task),
                          "blocks": len(meta), "minutes": (time.time() - e0) / 60, "per_task": per_task})
    d = f"   {mean - prev:+.4f} vs previous" if prev is not None else ""
    say(f"  HOLDOUT [{tag}]  step {step}  mean {mean:.4f} over {len(per_task)} tasks / {len(meta)} blocks  "
        f"{(time.time()-e0)/60:.1f} min{d}", flush=True)
    write_record("running")


def eval_probes(tag):
    """Teacher-forced exact match per probe set: a block counts when every answer token's argmax is right."""
    if not probes:
        return
    model.eval(); e0 = time.time(); res = {}; loss = {}
    with torch.no_grad():
        for name, enc in probes.items():
            hit = torch.zeros(1, device=acc.device); n = torch.zeros(1, device=acc.device); nll = torch.zeros(1, device=acc.device)
            for i in range(R, len(enc), W):
                ids, labels = enc[i]
                x = torch.tensor([ids], device=acc.device); y = torch.tensor(labels[1:], device=acc.device)
                lg = model(input_ids=x).logits[0, :-1].float(); pred = lg.argmax(-1)
                # Exact on the FINAL answer only (FFT spec: "per answer"): the last labelled span is the test
                # output. Every earlier output is context. Scoring all outputs (as before 2026-10-10) demanded the
                # first demo's output too, which has no prior example: P1 read 0/99 on the untouched base.
                m = y != -100
                idx = torch.nonzero(m).flatten()
                gaps = torch.nonzero(idx[1:] - idx[:-1] > 1).flatten()
                last = idx[gaps[-1] + 1:] if len(gaps) else idx
                hit += float(bool((pred[last] == y[last]).all())); n += 1
                nll += torch.nn.functional.cross_entropy(lg[last], y[last])
            hit, n, nll = acc.reduce(hit, "sum"), acc.reduce(n, "sum"), acc.reduce(nll, "sum")
            res[name] = [int(hit.item()), int(n.item())]; loss[name] = round(float(nll.item() / max(1, n.item())), 5)
    model.train()
    probe_evals.append({"tag": tag, "step": step, "exact": res, "loss": loss, "minutes": (time.time() - e0) / 60})
    base = probe_evals[0]["exact"]
    say(f"  PROBES [{tag}]  step {step}  " + "  ".join(f"{k} {v[0]}/{v[1]} (loss {loss[k]:.4f})" for k, v in res.items())
        + f"  {(time.time()-e0)/60:.1f} min", flush=True)
    for k in ("P1", "P2"):
        if k in res and k in base and base[k][0] - res[k][0] >= args.probe_alert_drop:
            say(f"  ALERT: {k} exact fell {base[k][0]} -> {res[k][0]} since step 0 (>= {args.probe_alert_drop}); "
                f"run continues", flush=True)
    write_record("running")


_ckpt_thread = None


def _finish_checkpoint(d, _s0, how):
    import shutil
    if acc.is_main_process:
        json.dump({"step": int(os.path.basename(d)[5:]), "total_steps": total_steps, "lr": args.lr}, open(os.path.join(d, "step.json"), "w"))
        open(os.path.join(d, "COMPLETE"), "w").write(os.path.basename(d)[5:])
        _gb = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(d) for f in fs) / 2**30
        say(f"  CHECKPOINT {os.path.basename(d)} -> {d}: {_gb:.1f} GiB, {how}, written in {time.time()-_s0:.0f} s")
        olds = sorted(x for x in os.listdir(ckpt) if x.startswith("step-"))[:-args.keep_local]
        for x in olds:
            if not os.path.exists(os.path.join(ckpt, x, "UPLOADING")):
                shutil.rmtree(os.path.join(ckpt, x), ignore_errors=True)


def wait_checkpoint():
    global _ckpt_thread
    if _ckpt_thread is not None:
        _ckpt_thread.join(); _ckpt_thread = None


def save_checkpoint():
    """ckpt/step-NNNNNN with step.json and a COMPLETE marker written last (the uploader only takes
    COMPLETE dirs); keep the newest --keep-local, never pruning a dir the uploader marked UPLOADING.
    --async-ckpt on: snapshot to CPU RAM, then write in a background thread while training continues."""
    global _ckpt_thread
    _s0 = time.time(); d = os.path.join(ckpt, f"step-{step:06d}")
    if args.async_ckpt == "on" and W == 1:
        wait_checkpoint()                       # never two writes at once
        need = sum(p.numel() * p.element_size() for p in model.parameters()) + sum(
            v.numel() * v.element_size() for st in opt.state.values() for v in st.values() if torch.is_tensor(v))
        _, avail = _meminfo()
        if avail > need * 1.15:
            import copy, threading
            from accelerate.checkpointing import save_accelerator_state
            def cpu(x):
                if torch.is_tensor(x): return x.detach().to("cpu", copy=True)
                if isinstance(x, dict): return {k: cpu(v) for k, v in x.items()}
                if isinstance(x, (list, tuple)): return type(x)(cpu(v) for v in x)
                return copy.deepcopy(x)
            class _Frozen:
                def __init__(self, sd): self.sd = sd
                def state_dict(self): return self.sd
            # exactly what acc.save_state passes, as CPU copies: models via get_state_dict(unwrap=False), the
            # accelerator's registered optimizers / schedulers; dataloaders and scaler as they are
            msds = [cpu(acc.get_state_dict(m, unwrap=False)) for m in acc._models]
            opts = [_Frozen(cpu(o.state_dict())) for o in acc._optimizers]
            schs = [_Frozen(copy.deepcopy(s.state_dict())) for s in acc._schedulers]
            dls, stp, scl = list(acc._dataloaders), acc.step, acc.scaler
            say(f"  CHECKPOINT step {step}: snapshot {need/2**30:.1f} GiB to RAM in {time.time()-_s0:.1f} s "
                f"(RAM available {avail/2**30:.0f} GiB); writing in the background")
            def _write():
                os.makedirs(d, exist_ok=True)
                save_accelerator_state(d, msds, opts, schs, dls, acc.state.process_index, stp, scl)
                _finish_checkpoint(d, _s0, "background write")
            _ckpt_thread = threading.Thread(target=_write, daemon=False); _ckpt_thread.start()
            return
        say(f"  CHECKPOINT step {step}: RAM available {avail/2**30:.0f} GiB < {need*1.15/2**30:.0f} GiB needed -- blocking save")
    acc.save_state(d)
    _finish_checkpoint(d, _s0, "blocking save")
    acc.wait_for_everyone()


start_step = 0
if args.resume_from:
    acc.load_state(args.resume_from)
    # load_state restores the saved param_groups, including weight_decay; a restart that CHANGES it (2026-10-11:
    # hop 1 resumed from s000170 with --weight-decay 0.1) must re-apply the requested value.
    for _g in opt.param_groups:
        _g["weight_decay"] = args.weight_decay
    start_step = json.load(open(os.path.join(args.resume_from, "step.json")))["step"]
    for _ in range(start_step):
        sched.step()
    say(f"  resumed           {args.resume_from} at step {start_step}")
if args.continue_from:
    if args.resume_from:
        sys.exit("FAIL: --continue-from starts a new hop; --resume-from continues this one. Use one.")
    acc.load_state(args.continue_from)
    for _g in opt.param_groups:          # this hop's weight decay; lr comes from this hop's schedule (sched.base_lrs)
        _g["weight_decay"] = args.weight_decay
    for _g, _b in zip(opt.param_groups, sched.base_lrs):
        _g["lr"] = _b * lr_at(0)
    say(f"  continued from    {args.continue_from} (weights + optimizer; step 0, fresh schedule at lr {args.lr:g})")
step = start_step
if not args.probe or args.probe_eval == "on":
    eval_holdout("before training")
    eval_probes("before training" if start_step == 0 else f"resumed at {start_step}")

# PROBE MASTER CHECK: the bf16 save only shows updates that survive bf16 rounding, so the real test
# of --master-dtype is the optimizer's own tensor. Snapshot this rank's local shard of one mid-depth
# MLP weight before step 1 and report the fraction of its elements that step 1 changed (the
# acceptance test: >= 99% with fp32 masters).
_probe_p = None
if args.probe:
    _names = [n for n, _ in model.named_parameters() if n.endswith("mlp.down_proj.weight")]
    _pn = _names[len(_names) // 2] if _names else None
    _probe_p = dict(model.named_parameters()).get(_pn) if _pn else None
    if _probe_p is not None:
        _loc = _probe_p.to_local() if hasattr(_probe_p, "to_local") else _probe_p.data
        _probe_before = _loc.detach().clone()
        say(f"  probe master      {_pn}: local shard {tuple(_loc.shape)} {_loc.dtype} on rank {R}")
model.train()
win_loss = torch.zeros(1, device=acc.device); win_tok = torch.zeros(1, device=acc.device)
tick, tick_tokens = time.time(), 0
torch.cuda.reset_peak_memory_stats()
for ep in range(args.epochs):
    for s in range(steps_per_epoch):
        g = ep * steps_per_epoch + s
        if g < start_step:
            continue
        base = s * per_step
        mine = [base + m * W + R for m in range(args.grad_accum)]
        batches = [row_batch(r) for r in mine]
        # global loss-token count for this optimizer step -> token-weighted mean across rank/accum
        n_local = torch.tensor([sum(b[4] for b in batches)], device=acc.device, dtype=torch.float32)
        n_global = float(acc.reduce(n_local.clone(), "sum"))
        for ids, labels, pos, kw, n_tok, wts in batches:
            with acc.accumulate(model):
                if wts is None:
                    out = model(input_ids=ids, labels=labels, position_ids=pos,
                                num_items_in_batch=torch.tensor(n_global / W, device=acc.device), **kw)
                else:
                    # weighted: sum(w * nll) / (global weight / W) -- the same normalisation as the unweighted path,
                    # with token counts replaced by weights. Vocab 16, so the logits cost nothing.
                    o = model(input_ids=ids, position_ids=pos, **kw)
                    nll = torch.nn.functional.cross_entropy(o.logits[0, :-1].float(), labels[0, 1:],
                                                            ignore_index=-100, reduction="none")
                    o.loss = (nll * wts[0, 1:]).sum() / (n_global / W)
                    out = o
                # out.loss is already sum/(global tokens / W); accelerate divides by grad_accum
                # on top of that, so it is undone here. FSDP's mean over W completes the weighting.
                acc.backward(out.loss * args.grad_accum)
                if acc.sync_gradients:
                    _gn = acc.clip_grad_norm_(model.parameters(), args.max_grad_norm)
                    gnorms.append(float(_gn) if _gn is not None else float("nan"))   # pre-clip global norm
                opt.step(); opt.zero_grad(set_to_none=True)
                if acc.sync_gradients:
                    sched.step()
            win_loss += out.loss.detach().float() * (n_global / W); win_tok += n_tok
        step = g + 1
        if _probe_p is not None and step == start_step + 1:
            _loc = _probe_p.to_local() if hasattr(_probe_p, "to_local") else _probe_p.data
            _frac = (_loc.detach() != _probe_before).float().mean().item()
            say(f"  probe master      after step 1: {_frac:.2%} of the {_loc.dtype} master shard changed "
                f"on rank {R} ({'PASS' if _frac >= 0.99 else 'FAIL'} vs >= 99%)")
            _probe_p = None
        tick_tokens += per_step * L
        mean = float(acc.reduce(win_loss.clone(), "sum") / acc.reduce(win_tok.clone(), "sum"))
        hist.append(mean); win_loss.zero_(); win_tok.zero_()
        if not math.isfinite(mean):
            write_record("crashed", note="non-finite loss"); sys.exit(f"FAIL: non-finite loss at step {step}")
        if step == args.tripwire_steps and sum(hist[-step:]) / step > args.tripwire_loss:
            write_record("halted"); sys.exit(f"HALT: loss over first {step} steps > {args.tripwire_loss}")
        if step % args.log_every == 0 or step == total_steps or (args.probe and step - start_step <= args.probe):
            dt = time.time() - tick
            tps = tick_tokens / dt
            mfu = 6 * n_params * tps / (W * args.peak_tflops * 1e12)
            w = hist[-args.log_every:]
            gw = gnorms[-args.log_every:] or [float("nan")]
            say(f"  step {step}/{total_steps}  loss {sum(w)/len(w):.4f}  lr {sched.get_last_lr()[0]:.2e}  "
                f"gnorm {sum(gw)/len(gw):.3f} (max {max(gw):.3f}, clipped {sum(x > args.max_grad_norm for x in gw)}/{len(gw)})  {tps:,.0f} tok/s  MFU {mfu:.1%}  mem {torch.cuda.max_memory_allocated()/2**30:.1f} GiB  "
                f"{(time.time()-t0)/60:.1f} min", flush=True)
            tick, tick_tokens = time.time(), 0
        if args.probe and step - start_step >= args.probe:
            # Resume check (spec §6 probe 4): fp32 master checksums at the step the probe ends, so an
            # uninterrupted run and a resumed run can be compared at the same step.
            with torch.no_grad():
                _ps = dict(model.named_parameters())
                for _n in [n for n in _ps if n.endswith(("embed_tokens.weight", "layers.18.mlp.down_proj.weight"))
                           or n.split(".")[-2:] == ["norm", "weight"] and "layers." not in n]:
                    _t = _ps[_n].detach().float()
                    say(f"  CHECKSUM step {step} {_n}: sum {_t.sum().item():.10e}  abs {_t.abs().sum().item():.10e}")
            if args.probe_eval == "on":
                eval_holdout(f"probe end step {step}"); eval_probes(f"probe end step {step}")
                write_record("probe", lr=args.lr)
            say(f"  PROBE done: peak {torch.cuda.max_memory_allocated()/2**30:.1f} GiB on rank {R}; "
                f"projected {total_steps * per_step * L / max(tps,1) / 3600:.2f} h for the full run")
            sys.exit(0)
        _timed = (args.checkpoint_at_hours and not getattr(args, "_timed_done", False)
                  and (time.time() - t0) / 3600 >= args.checkpoint_at_hours and step < total_steps)
        if _timed:
            args._timed_done = True
            say(f"  TIMED CHECKPOINT at {(time.time() - t0) / 3600:.2f} h (--checkpoint-at-hours {args.checkpoint_at_hours})")
        if _timed or (args.checkpoint_every and step % args.checkpoint_every == 0 and step < total_steps):
            save_checkpoint()
            eval_probes(f"step {step}")
            write_record("running")
            tick, tick_tokens = time.time(), 0      # keep checkpoint time out of tok/s
        elif args.probe_every and step % args.probe_every == 0 and step < total_steps:
            eval_probes(f"step {step}")
            write_record("running")
            tick, tick_tokens = time.time(), 0      # keep probe time out of tok/s
        if args.holdout_every and step % args.holdout_every == 0 and step < total_steps:
            eval_holdout(f"step {step}")
            tick, tick_tokens = time.time(), 0      # keep holdout time out of tok/s
    say(f"  epoch {ep+1}/{args.epochs} done at step {step}")

eval_holdout("after training")
eval_probes("after training")
# The FINAL state as a full checkpoint (weights + optimizer), so a following leg continues from the end of this one, not
# from the last every-N checkpoint (10-16: hop 4 leg 1 ended at 329, its last checkpoint due was 252 and failed to upload,
# so only s000168 carried optimizer state). The uploader sends it; the notebook waits for in-flight uploads (90 min).
if args.checkpoint_every and step % args.checkpoint_every != 0:
    say(f"  FINAL CHECKPOINT at step {step}")
    save_checkpoint()
acc.wait_for_everyone()
state = acc.get_state_dict(model)
wait_checkpoint()   # a background checkpoint write must finish before the final save
if acc.is_main_process:
    un = acc.unwrap_model(model)
    un = getattr(un, "_orig_mod", un)
    un.config.use_cache = True
    # The Kaggle artifact is bf16 whatever the master dtype was.
    state = {k: (v.to(torch.bfloat16) if v.is_floating_point() else v) for k, v in state.items()}
    un.config.torch_dtype = torch.bfloat16
    un.save_pretrained(args.save_dir, state_dict=state, safe_serialization=True)
    tokenizer.save_pretrained(args.save_dir)
acc.wait_for_everyone()
win = hist[-50:]
say(f"\n  {step} steps, {(time.time()-t0)/3600:.2f} h   final loss {sum(win)/len(win):.4f}")
say(f"  model written to {args.save_dir}")
write_record("finished", final_loss=sum(win) / len(win), save_dir=args.save_dir)
say(f"  wrote {args.out}")
