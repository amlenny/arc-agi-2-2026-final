#!/usr/bin/env python3
# crucible-sdg-train.py — fine-tune the base on NOVEL authored tasks, with the gates that decide
# whether the corpus is worth training on at all.
#
#   crucible-sdg-train.py --model-dir <dir> --corpus <dir-or-manifest> --data data-kaggle \
#                         --out runs/sdg-<...>.json
#
# THE OPENING LOSS is measured and recorded for every run. It is not a gate: it does not predict
# whether training the corpus will help, so nothing is refused on the strength of it.
#
# CONTAMINATION is checked at the CONTENT level, not by id: a task can be renamed. Every corpus
# demonstration pair is hashed against every evaluation pair, because pair-level collision is the
# case id-matching and whole-task hashing both miss — one such collision exists in the ARC-AGI-1
# corpus against the evaluation split.
#
# Checkpoints carry optimizer state so a resume continues rather than restarts. Batch 1, no
# padding, and NO REORDERING: the order the corpus sits in on disk is the order it is trained in.
#
# The corpus is authored against novel rules, not against evaluation
# answers. The morning read is the stratified gauntlet against a FROZEN baseline.

import argparse
import hashlib
import json
import os
import random
import sys
import time
import importlib.util


def _sib(stem):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), stem + ".py")
    spec = importlib.util.spec_from_file_location(stem.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


scorer = _sib("crucible-score")
fmt = _sib("crucible-grids15")


def parse_args():
    ap = argparse.ArgumentParser(description="Fine-tune on a novel authored corpus, gated on "
                                             "novelty and contamination.")
    ap.add_argument("--model-dir", required=True)
    # THE COUNT AS AN ASSERTION, not as something an operator reads off the screen. The empty-
    # corpus guard fires at exactly zero and nothing fires between 1 and N-1; this closes that.
    ap.add_argument("--expect-tasks", type=int, default=0,
                    help="Abort unless EXACTLY this many tasks load. 0 disables. Use it whenever "
                         "the corpus size is known in advance — a manifest with a wrong prefix on "
                         "some entries otherwise trains a smaller corpus under the right name.")
    ap.add_argument("--corpus", required=True,
                    help="Directory of task JSONs, or a manifest listing them.")
    ap.add_argument("--curriculum", default="",
                    help='JSON manifest of ordered stages: {"stages":[{"name":..,"dir":..},..]}. '
                         "Each stage's directory is loaded whole, stages in the order given. "
                         "Without it, --corpus is loaded as one stage. Either way the order on "
                         "disk is the order trained.")
    ap.add_argument("--data", default="data-kaggle")
    ap.add_argument("--lora-r", type=int, default=32)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--lora-targets", default="all", choices=["all", "attn-mlp"],
                    help="all = attention + MLP + embed_tokens + lm_head (every leg before 2026-10-25); attn-mlp = attention + MLP only. "
                         "2026-10-25: FT-045r (all) learned its 10 tasks but P1/P2/P3 fell 45/81/92 -> 31/54/41 -- the shared "
                         "embedding and output head moved for every grid")
    ap.add_argument("--lora-modules", default="",
                    help="comma list of module names the adapter targets, overriding --lora-targets (e.g. gate_proj,up_proj,down_proj). "
                         "2026-10-27: every adapter so far wrote the same seven matrices in all 36 layers, the ones holding the "
                         "merged-in tasks; separate rounds can now write separate weights")
    ap.add_argument("--lora-layers", default="",
                    help="layer range A-B (inclusive) the adapter is applied to (PEFT layers_to_transform); default every layer. "
                         "With --resume-from, both settings are read from the saved adapter_config.json when not given")
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--epochs", type=int, default=1,
                    help="Fixed epoch count. Ignored when --train-to-floor is set.")
    # DOSE. Three epochs was a convention. The TTT inside one 20-task eval is 2560 optimizer steps;
    # the 157-task corpus run was 471. Comparing those and reporting "no transfer" measures the
    # dose, not the corpus.
    ap.add_argument("--train-to-floor", action="store_true",
                    help="Train until the epoch-mean loss floors, or --max-epochs, whichever first.")
    ap.add_argument("--max-epochs", type=int, default=10,
                    help="Hard ceiling for --train-to-floor. Also sizes the LR schedule.")
    ap.add_argument("--floor-rel", type=float, default=0.02,
                    help="Relative epoch-over-epoch improvement below which the loss counts as flat.")
    ap.add_argument("--floor-patience", type=int, default=2,
                    help="Consecutive flat epochs required to call it a floor. One flat epoch is "
                         "noise; the patience is what makes it a measurement.")
    ap.add_argument("--max-seq-len", type=int, default=8192)
    ap.add_argument("--augment", type=int, default=-1,
                    help="seed for per-block augmentation, as crucible-fft-pack.py (FFT spec strategy 1): one random "
                         "dihedral, one permutation of all 10 colours incl. 0, demo-order shuffle; the first block of "
                         "each task stays unaugmented. -1 = off (every leg before FT-035).")
    ap.add_argument("--with-test-pair", default="off", choices=["on", "off"],
                    help="also train each block's test pair (it has an output). off = demos only, as every leg "
                         "before FT-035 trained.")
    ap.add_argument("--warmup-ratio", type=float, default=0.03)
    ap.add_argument("--max-grad-norm", type=float, default=1.0)
    ap.add_argument("--weight-decay", type=float, default=0.01, help="AdamW weight decay (0.01 = torch default, what every leg before FT-042 run 3 used)")
    ap.add_argument("--novelty-probe", type=int, default=32,
                    help="Examples used to measure the opening loss.")
    ap.add_argument("--tripwire-loss", type=float, default=2.0)
    ap.add_argument("--tripwire-steps", type=int, default=20)
    ap.add_argument("--checkpoint-every", type=int, default=200)
    ap.add_argument("--ckpt-dir", default="")
    ap.add_argument("--resume-from", default="")
    ap.add_argument("--score-only", action="store_true",
                    help="take ONE holdout read (loss + solved counts) of the --resume-from adapter (none = the base) and exit: no "
                         "training step, no checkpoint, no adapter save. The record goes to --out.")
    ap.add_argument("--resume-optimizer", action="store_true",
                    help="also restore Adam moments from <resume-from>/optim.pt. Without this a "
                         "resume rebuilds the optimizer with ZERO moments and re-runs warmup at "
                         "full LR on converged weights, which is not a continuation.")
    ap.add_argument("--schedule-offset", type=int, default=0,
                    help="treat training as starting at this step for the LR schedule")
    ap.add_argument("--schedule-total", type=int, default=0,
                    help="size the LR schedule to this many steps instead of this corpus. Set both "
                         "to continue a run's schedule: a 4th round over a 3-round run is "
                         "--schedule-offset 17328 --schedule-total 23104, so LR picks up at 25% of "
                         "peak and decays to zero across the added round. Restoring the finished "
                         "run's scheduler verbatim instead would give LR ZERO and train nothing.")
    # ---- HELD-OUT MECHANICS ----
    # Instances of the SAME generators the corpus trains, drawn after the training blocks and
    # gated per input against the whole training set, so no input the model saw appears here.
    # Forward-only: it measures whether the mechanic transferred, and changes nothing.
    ap.add_argument("--holdout-root", default="",
                    help="Directory laid out as <root>/<task-id>/_holdout/*.json. Empty disables "
                         "the evaluation. The holdout sits outside every curriculum directory, so "
                         "--corpus and the stage dirs cannot pick it up.")
    ap.add_argument("--holdout-max-per-task", type=int, default=0,
                    help="Cap blocks evaluated per task. 0 = every block. The pass is forward-only "
                         "but not free: it costs one forward per block at every boundary.")
    ap.add_argument("--holdout-every", type=int, default=0,
                    help="Also evaluate every N optimizer steps. 0 = section boundaries only "
                         "(plus one before the first step and one after the last).")
    ap.add_argument("--adapter-dtype", default="fp32", choices=["fp32", "bf16"],
                    help="dtype the ADAPTER is held and updated in. fp32 is a master copy: the base "
                         "stays bf16 and compute runs under bf16 autocast, but every optimizer step "
                         "lands on fp32 weights. bf16 is the pre-2026-09-26 behaviour, kept ONLY to "
                         "reproduce old runs: measured on the FT-021 adapter, a full-size Adam step "
                         "at lr 2e-5 is under half a bf16 ulp on 48%% of lora_A (88%% at 5e-6), so "
                         "those updates round to zero and the weight never moves.")
    ap.add_argument("--w-copied", type=float, default=0.1,
                    help="TRAINING weight on answer cells equal to the input cell at the same position "
                         "(same-shape pairs). Measured 2026-09-27 on FT-020, held-out blocks of the 39: "
                         "copied cells are 79%% of answer tokens at 0.008 nats, CHANGED cells 8%% at "
                         "0.153 and 59%% of all loss; the mean loss was mostly the copy signal. 1.0 = "
                         "the pre-2026-09-27 unweighted loss.")
    ap.add_argument("--w-changed", type=float, default=1.0,
                    help="training weight on answer cells the rule changed. Reshaped outputs and "
                         "row/end markers always weigh 1.0.")
    ap.add_argument("--holdout-root-unseen", default="",
                    help="Second holdout, same layout, of tasks kept ENTIRELY out of training. "
                         "Reported as HOLDOUT-UNSEEN beside the seen-task HOLDOUT, which only "
                         "measures new instances of trained tasks.")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


def pair_hash(a, b):
    return hashlib.sha256(json.dumps([a, b], separators=(",", ":")).encode()).hexdigest()


HOLDOUT_DIR = "_holdout"


def load_corpus(path, skipped=None, pruned=None):
    """Task dicts from a directory of JSONs or a manifest of paths.

    skipped: optional list; every file that could not be read is appended to it. The caller
    decides whether a skip is fatal — this function must not swallow the fact that one happened.

    pruned: optional list; every _holdout directory NOT descended into is appended to it. The
    holdout sits inside each task directory, so walking a task directory or the corpus root picks
    it up and TRAINS ON IT, which silently converts the held-out measurement into a training-set
    one that still reports as a holdout. It is pruned here, at the only place that reads it.
    """
    files = []
    if os.path.isdir(path):
        for root, dirs, names in os.walk(path):
            if HOLDOUT_DIR in dirs:
                dirs.remove(HOLDOUT_DIR)
                if pruned is not None:
                    pruned.append(os.path.join(root, HOLDOUT_DIR))
            files += [os.path.join(root, n) for n in names if n.endswith(".json")]
    else:
        base = os.path.dirname(os.path.abspath(path))
        for line in open(path):
            line = line.strip()
            if not line:
                continue
            files.append(line if os.path.isabs(line) else os.path.join(base, line))
    tasks = []
    for f in sorted(files):
        try:
            d = json.load(open(f))
        except Exception as e:
            # Recorded, not just printed. stderr scrolls past; a list can be checked.
            if skipped is not None:
                skipped.append((f, str(e)))
            print(f"  skipping unreadable {os.path.basename(f)}: {e}", file=sys.stderr)
            continue
        if isinstance(d, dict) and d.get("train"):
            tasks.append((os.path.basename(f)[:-5], d))
        elif isinstance(d, dict):
            for tid, t in d.items():
                if isinstance(t, dict) and t.get("train"):
                    tasks.append((tid, t))
    return tasks


def load_holdout(root, cap=0):
    """{task-id: [demo blocks]} from <root>/<task-id>/_holdout/*.json.

    Keyed by the DIRECTORY name, which is the task id. The filenames carry the skeleton that built
    the block, which is not always the same id, and keying on those would silently merge tasks.
    """
    if not os.path.isdir(root):
        raise SystemExit(f"FAIL: --holdout-root {root!r} is not a directory.")
    out = {}
    for tid in sorted(os.listdir(root)):
        d = os.path.join(root, tid, "_holdout")
        if not os.path.isdir(d):
            continue
        blocks = []
        for n in sorted(os.listdir(d)):
            if not n.endswith(".json"):
                continue
            f = os.path.join(d, n)
            try:
                doc = json.load(open(f))
            except Exception as e:
                # Fatal for the same reason an unreadable corpus entry is: a holdout that is
                # quietly smaller than the one named is a different measurement under its name.
                raise SystemExit(f"FAIL: holdout block {f} unreadable: {e}")
            raw = []
            if isinstance(doc, dict) and doc.get("train"):
                raw = [doc]
            elif isinstance(doc, dict):
                raw = [v for v in doc.values() if isinstance(v, dict) and v.get("train")]
            for blk in raw:
                demos = [{"input": p["input"], "output": p["output"]} for p in blk["train"]]
                if len(demos) >= 2:
                    blocks.append((n, demos))
        if cap:
            blocks = _spread_grades(blocks, cap)
        if blocks:
            out[tid] = [d for _, d in blocks]
    return out


HOLDOUT_GRADES = ("timid", "mid", "bold", "size")


def _spread_grades(blocks, cap):
    """Take `cap` blocks SPREAD ACROSS GRADES, not the first `cap` of a sort.

    This was `blocks[:cap]`, and where the carve is deeper than the cap that took the
    alphabetically-first names. "bold" sorts before "mid", "size" and "timid", so a balanced
    20-block carve reached the trainer as one grade. Measured 2026-09-18 across every holdout
    tree: t148-18h-v2 is timid 739 / mid 748 / bold 716 / size 757 ON DISK and reached the
    trainer as 97% bold, with 146 of its 148 pools contributing four blocks of a single grade.
    t160-18h and t160-iter are 96% bold the same way. FT-011's, FT-012's and FT-013's held-out
    curves are therefore bold-only, and the decision to train ONE round rather than two rests on
    one of them.

    The 4-block carves (t170, t171, t172, t172b) were accidentally correct: carve depth equalled
    the cap, so nothing was truncated away.

    Round-robin over sorted grades, sorted names within each grade, so the selection is
    deterministic and a rerun holds out the same blocks. A name carrying no grade goes in a
    trailing bucket rather than being dropped.

    HOLDOUT NUMBERS FROM BEFORE THIS CHANGE ARE NOT COMPARABLE TO ONES AFTER IT on any run whose
    carve was deeper than its cap. That is the point of the fix, and it is also its cost.
    """
    if len(blocks) <= cap:
        return blocks
    buckets = {g: [] for g in HOLDOUT_GRADES}
    buckets[None] = []
    for name, demos in blocks:
        parts = name[:-5].split("_") if name.endswith(".json") else name.split("_")
        g = next((x for x in HOLDOUT_GRADES if x in parts), None)
        buckets[g].append((name, demos))
    order = [g for g in HOLDOUT_GRADES if buckets[g]] + ([None] if buckets[None] else [])
    picked, i = [], 0
    while len(picked) < cap and any(buckets[g] for g in order):
        g = order[i % len(order)]
        if buckets[g]:
            picked.append(buckets[g].pop(0))
        i += 1
    return picked


def main():
    args = parse_args()
    ev = scorer.load_tasks(args.data, "evaluation")

    eval_pairs = {}
    for tid, t in ev.items():
        for p in t.get("train", []):
            eval_pairs.setdefault(pair_hash(p["input"], p["output"]), set()).add(tid)
        for te in t.get("test", []):
            if te.get("output"):
                eval_pairs.setdefault(pair_hash(te["input"], te["output"]), set()).add(tid)

    skipped, pruned = [], []
    stage_plan = []
    if args.curriculum:
        # Stage order lives in the manifest and the filesystem, so the order the model saw is
        # inspectable afterwards. Tasks carry their stage index only so the plan can be reported
        # accurately once the contamination screen has removed whatever it removes.
        with open(args.curriculum) as fh:
            manifest = json.load(fh)
        tasks = []
        for i, st in enumerate(manifest["stages"]):
            sub = load_corpus(st["dir"], skipped, pruned)
            if not sub:
                sys.exit(f"FAIL: curriculum stage {i+1} ({st.get('name','?')}) loaded 0 tasks "
                         f"from {st['dir']!r}. A stage that contributes nothing is a silently "
                         f"shorter curriculum than the one recorded.")
            for tid, t in sub:
                t["_stage"] = i
            tasks += sub
            stage_plan.append((st.get("name", f"stage{i+1}"), st["dir"], len(sub)))
    else:
        tasks = load_corpus(args.corpus, skipped, pruned)
    if pruned:
        print(f"  pruned     {len(pruned)} {HOLDOUT_DIR} director(ies) from the training walk "
              f"(they are the held-out set; training them would make the holdout meaningless)",
              flush=True)
    # ANY SKIP IS FATAL. A corpus that is partly unreadable is not this corpus, and the failure
    # must land before the model is loaded rather than as a stderr line under a success report.
    if skipped:
        print(f"FAIL: {len(skipped)} corpus entr(ies) could not be read. A partial corpus trains "
              f"a smaller set under this one's name.", file=sys.stderr)
        for f, e in skipped[:10]:
            print(f"       {f}: {e}", file=sys.stderr)
        if len(skipped) > 10:
            print(f"       ... and {len(skipped) - 10} more", file=sys.stderr)
        sys.exit(2)
    # FAIL LOUD ON AN EMPTY CORPUS. load_corpus accepts a directory of task JSONs or a manifest of
    # one-path-per-line; handed anything else it returns [] rather than complaining. Pointing it at
    # a curated mix FILE — corpus/mix-pruned.json, exactly the thing an operator would reach for —
    # reads that file's JSON text as a list of paths, finds none of them, and yields ZERO tasks.
    # The run would then train on nothing and report an opening loss computed over an empty corpus,
    # which is a number that looks like a result. An instrument that can silently measure nothing
    # is worse than one that crashes.
    if not tasks:
        raise SystemExit(
            f"FAIL: --corpus {args.corpus!r} yielded 0 tasks.\n"
            f"  load_corpus takes a DIRECTORY of task JSONs, or a MANIFEST file listing one path\n"
            f"  per line. A curated-mix JSON (e.g. corpus/mix-pruned.json) is neither: its lines\n"
            f"  are JSON text, not paths, so every entry is unreadable and the corpus comes back\n"
            f"  empty. Point at the directory, or at a manifest of paths.")
    if args.expect_tasks and len(tasks) != args.expect_tasks:
        sys.exit(f"FAIL: --expect-tasks {args.expect_tasks} but {len(tasks)} loaded from "
                 f"{args.corpus}. Refusing to train a corpus that is not the one asked for.")
    print(f"  corpus     {len(tasks)} tasks from {args.corpus}"
          + (f"  (expected {args.expect_tasks}, MATCHED)" if args.expect_tasks else ""), flush=True)
    if not tasks:
        sys.exit(f"FAIL: no tasks found in {args.corpus}")

    clean, rejected = [], []
    for tid, t in tasks:
        hits = set()
        for p in t.get("train", []) + [x for x in t.get("test", []) if x.get("output")]:
            hits |= eval_pairs.get(pair_hash(p["input"], p["output"]), set())
        if hits:
            rejected.append((tid, sorted(hits)))
        else:
            clean.append((tid, t))

    print("== SDG micro-pilot ==", flush=True)
    print(f"  corpus            {len(tasks)} tasks from {args.corpus}", flush=True)
    print(f"  CONTAMINATION     content-level pair hashing vs the evaluation split", flush=True)
    print(f"     rejected       {len(rejected)}", flush=True)
    for tid, hits in rejected[:10]:
        print(f"       {tid} shares a pair with {hits}", flush=True)
    print(f"     clean          {len(clean)}", flush=True)
    print(f"  adapter           r={args.lora_r} alpha={args.lora_alpha}, {args.epochs} epoch(s)",
          flush=True)
    if not clean:
        sys.exit("FAIL: every task collided with the evaluation split. Nothing to train.")

    # Loaded HERE, before the model: a wrong --holdout-root must fail in seconds, not after the
    # weights are on the GPU.
    holdout = {}
    if args.holdout_root:
        holdout = load_holdout(args.holdout_root, args.holdout_max_per_task)
        if not holdout:
            sys.exit(f"FAIL: --holdout-root {args.holdout_root!r} yielded 0 holdout blocks. "
                     f"Expected <root>/<task-id>/_holdout/*.json.")
        # The holdout never touches the weights, so a collision here is not a leak into the model.
        # It would still make the measurement partly a read of the evaluation split, so it goes.
        dropped = 0
        for tid in list(holdout):
            keep = []
            for demos in holdout[tid]:
                if any(eval_pairs.get(pair_hash(p["input"], p["output"])) for p in demos):
                    dropped += 1
                else:
                    keep.append(demos)
            if keep:
                holdout[tid] = keep
            else:
                del holdout[tid]
        nblocks = sum(len(v) for v in holdout.values())
        print(f"  HOLDOUT           {nblocks} blocks over {len(holdout)} tasks from "
              f"{args.holdout_root}", flush=True)
        if dropped:
            print(f"     screened out   {dropped} block(s) sharing a pair with the evaluation split",
                  flush=True)
    else:
        print("  HOLDOUT           none (--holdout-root not given)", flush=True)
    unseen_sets = {}
    for _root in [r for r in args.holdout_root_unseen.split(",") if r]:
        unseen = load_holdout(_root, args.holdout_max_per_task)
        for tid in list(unseen):
            keep = [d for d in unseen[tid]
                    if not any(eval_pairs.get(pair_hash(p["input"], p["output"])) for p in d)]
            if keep:
                unseen[tid] = keep
            else:
                del unseen[tid]
        if not unseen:
            sys.exit(f"FAIL: --holdout-root-unseen {_root!r} yielded 0 blocks.")
        # UNSEEN MEANS UNSEEN: no training block may name a held-out task. Block names carry the
        # task id(s) they derive from (remix blocks carry two), so a match anywhere is a leak.
        leaks = [tid for tid, _ in clean if any(u in tid for u in unseen)]
        if leaks:
            sys.exit(f"FAIL: {len(leaks)} training block(s) name an unseen-holdout task, e.g. "
                     f"{leaks[:3]}. The unseen number would be a seen one.")
        _name = os.path.basename(os.path.normpath(_root))
        unseen_sets[_name] = unseen
        print(f"  HOLDOUT-UNSEEN    [{_name}] {sum(len(v) for v in unseen.values())} blocks over "
              f"{len(unseen)} tasks kept out of training, from {_root}  (0 leaks)", flush=True)

    if args.dry_run:
        print("\n  DRY RUN — nothing executed.")
        return

    import torch
    from peft import LoraConfig, get_peft_model, get_peft_model_state_dict, set_peft_model_state_dict
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not torch.cuda.is_available():
        sys.exit("FAIL: no GPU visible.")
    tokenizer = fmt.load_tokenizer()   # embedded base tokenizer: role tokens kept
    fmt.assert_tokenizer(tokenizer)
    model = AutoModelForCausalLM.from_pretrained(args.model_dir, dtype=torch.bfloat16,
                                                 device_map="auto", local_files_only=True)
    model.config.use_cache = False
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    _tm = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"] + (["embed_tokens", "lm_head"] if args.lora_targets == "all" else [])
    _lt = None
    _saved = os.path.join(args.resume_from, "adapter_config.json") if args.resume_from else ""
    if _saved and os.path.isfile(_saved):          # a resumed/scored adapter is rebuilt exactly as it was saved
        _sc = json.load(open(_saved))
        if not args.lora_modules and _sc.get("target_modules"): _tm = sorted(_sc["target_modules"])
        if not args.lora_layers and _sc.get("layers_to_transform") is not None: _lt = list(_sc["layers_to_transform"])
        if _sc.get("r"): args.lora_r = int(_sc["r"])                  # FT-052r (r64) scored at the default r32 -> size mismatch
        if _sc.get("lora_alpha"): args.lora_alpha = int(_sc["lora_alpha"])
    if args.lora_modules: _tm = [x for x in args.lora_modules.split(",") if x]
    if args.lora_layers:
        _a, _b = (int(x) for x in args.lora_layers.split("-")); _lt = list(range(_a, _b + 1))
    print(f"  LoRA targets      {','.join(_tm)}  layers {'all' if _lt is None else f'{_lt[0]}-{_lt[-1]}'}  r {args.lora_r} alpha {args.lora_alpha}", flush=True)
    model = get_peft_model(model, LoraConfig(
        r=args.lora_r, lora_alpha=args.lora_alpha, lora_dropout=0.0, bias="none",
        task_type="CAUSAL_LM", use_rslora=True, target_modules=_tm, layers_to_transform=_lt))
    # PEFT creates the adapter in fp32 over a bf16 base (autocast_adapter_dtype). Every run before
    # 2026-09-26 cast it back to bf16 here, which made most small updates round to zero.
    if args.adapter_dtype == "bf16":
        for p in model.parameters():
            if p.dtype == torch.float32:
                p.data = p.data.to(torch.bfloat16)
    if args.resume_from:
        state = torch.load(os.path.join(args.resume_from, "adapter.pt"), map_location="cpu")
        set_peft_model_state_dict(model, state)
        print(f"  resumed adapter from {args.resume_from}", flush=True)
        _resume_opt = os.path.join(args.resume_from, "optim.pt") if args.resume_optimizer else None
    # Checked AFTER any resume load, so a bf16 adapter.pt from an old run cannot slip past it.
    n_fp32 = sum(p.numel() for p in model.parameters() if p.requires_grad and p.dtype == torch.float32)
    n_tr = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  ADAPTER DTYPE     {args.adapter_dtype}: {n_fp32:,} of {n_tr:,} trainable params held "
          f"in fp32", flush=True)
    if args.adapter_dtype == "fp32" and n_fp32 != n_tr:
        sys.exit("FAIL: --adapter-dtype fp32 but some trainable params are not fp32.")

    # Examples: whole tasks as demo blocks, exactly the shape inference uses.
    #
    # THE ORDER ON DISK IS THE ORDER TRAINED, and nothing re-sorts. load_corpus walks files in
    # sorted order, so each source file arrives as one unbroken block; with --curriculum the stage
    # directories are read in the authored order.
    #
    # Sorting the whole corpus by any key interleaves every mechanic with every other, because
    # sources overlap in whatever the key measures. A corpus that holds N instances per source
    # exists to show one concept N times consecutively, and only the on-disk order delivers that.
    examples = []
    stage_counts = [0] * len(stage_plan)
    prev_stage = -1
    _seen_task, _n_aug, _n_keep = set(), 0, 0

    def _aug(demos, r, keep_colours=False):
        # keep_colours: a block marked "_colour_values_matter" (breadth rules whose answer depends on the colour
        # values, HOP2 corpus spec packing rule 4) gets the dihedral only; a colour permutation would change its rule.
        perm = list(range(10)); r.shuffle(perm); k = r.randrange(8)
        if keep_colours: perm = list(range(10))
        def tf(g):
            g = [[perm[v] for v in row] for row in g]
            if k & 4: g = [list(x) for x in zip(*g)]
            if k & 1: g = [row[::-1] for row in g]
            if k & 2: g = g[::-1]
            return g
        out = [{"input": tf(d["input"]), "output": tf(d["output"])} for d in demos]
        if args.with_test_pair == "on" and len(out) > 2:
            head, last = out[:-1], out[-1:]; r.shuffle(head); return head + last
        r.shuffle(out); return out

    for _i, (tid, t) in enumerate(clean):
        pairs = list(t["train"])
        if args.with_test_pair == "on":
            pairs += [p for p in t.get("test", []) if p.get("output")]
        demos = [{"input": p["input"], "output": p["output"]} for p in pairs]
        if len(demos) < 2:
            continue
        if args.augment >= 0:
            _parts = os.path.basename(str(tid)).split("_")
            _task = "_".join(_parts[1:-1]) if len(_parts) >= 3 else str(tid)
            if _task in _seen_task:
                demos = _aug(demos, random.Random(f"{args.augment}:{_i}"), bool(t.get("_colour_values_matter"))); _n_aug += 1
                _n_keep += bool(t.get("_colour_values_matter"))
            else:
                _seen_task.add(_task)
        examples.append(demos)
        if stage_plan:
            i = t["_stage"]
            # The stage split is carried by ORDER, not by a second pass. If anything upstream ever
            # reorders `clean`, the stages silently interleave and the run trains a curriculum
            # nobody authored -- so check it here rather than trust it.
            if i < prev_stage:
                sys.exit(f"FAIL: task {tid} from stage {i + 1} appears after stage "
                         f"{prev_stage + 1}. The corpus order was not preserved; refusing to "
                         f"train an order that is not the one in the manifest.")
            prev_stage = i
            stage_counts[i] += 1

    if stage_plan:
        print(f"  CURRICULUM        {len(stage_plan)} stages, in the order given", flush=True)
        at = 0
        for i, (name, d, loaded) in enumerate(stage_plan):
            n = stage_counts[i]
            drop = f"  ({loaded - n} screened out)" if loaded != n else ""
            print(f"     stage {i + 1}  {name:24} {n:5} blocks   steps {at + 1}-{at + n}{drop}",
                  flush=True)
            at += n
    print(f"  examples          {len(examples)} demo blocks, corpus order, batch 1; test pair {args.with_test_pair}; "
          f"augment {'off' if args.augment < 0 else f'seed {args.augment}, {_n_aug} blocks augmented ({_n_keep} dihedral only), {len(_seen_task)} tasks kept identity on their first block'}", flush=True)

    def encode_classes(block):
        """encode_ttt_example's ids/labels plus a class per token: 0 prompt, 1 copied cell,
        2 changed cell, 3 reshaped-output cell or row/end marker. Built pair by pair from the same
        prompt/answer strings, and checked token-for-token against encode_ttt_example."""
        ids, cls = [], []
        for pair in block:
            prompt = (f"{fmt.IM_START}user\n{fmt.grid_to_text(pair['input'])}{fmt.IM_END}"
                      f"{fmt.IM_START}assistant\n")
            p_ids = tokenizer.encode(prompt); a_ids = tokenizer.encode(fmt.reply_text(pair["output"]))
            gi, go = pair["input"], pair["output"]
            same = len(gi) == len(go) and len(gi[0]) == len(go[0])
            c = []
            for r, row in enumerate(go):
                c += [(1 if gi[r][k] == v else 2) if same else 3 for k, v in enumerate(row)]
                if r < len(go) - 1:
                    c.append(3)
            c += [3] * (len(a_ids) - len(c))
            ids += p_ids + a_ids; cls += [0] * len(p_ids) + c
        ref, _ = fmt.encode_ttt_example(tokenizer, block)
        if ref != ids:
            raise SystemExit("FAIL: class encoding diverged from encode_ttt_example")
        return ids, cls


    def _nll(block):
        enc_ids, cls = encode_classes(block)
        ids = torch.tensor([enc_ids[:args.max_seq_len]], device=model.device)
        cls = torch.tensor(cls[:args.max_seq_len], device=model.device)
        # bf16 compute over fp32 adapter weights: matmuls run in bf16, updates land in fp32.
        with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
            logits = model(input_ids=ids).logits[0, :-1].float()
        nll = torch.nn.functional.cross_entropy(logits, ids[0, 1:], reduction="none")
        # Per-token argmax hits from the same forward, for the solved count (_solved); read after the call.
        _nll.correct = logits.argmax(-1) == ids[0, 1:]
        _nll.truncated = len(enc_ids) > args.max_seq_len
        return nll, cls[1:]

    def _solved(c):
        """Teacher-forced exact match on the FINAL answer, the FFT probes' rule (crucible-fft-train.py eval_probes):
        the last contiguous answer span is the test output; solved when every token's argmax is right. A block cut by
        --max-seq-len has lost its test output and counts as unsolved. Call right after _nll."""
        if _nll.truncated:
            return 0
        idx = torch.nonzero(c > 0).flatten()
        if not len(idx):
            return 0
        gaps = torch.nonzero(idx[1:] - idx[:-1] > 1).flatten()
        last = idx[gaps[-1] + 1:] if len(gaps) else idx
        return int(bool(_nll.correct[last].all()))

    def loss_on(block):
        """UNWEIGHTED mean over answer tokens -- the lineage's held-out number, unchanged."""
        nll, c = _nll(block)
        return nll[c > 0].mean()

    def train_loss_on(block):
        """Weighted mean: changed cells carry the signal, copied cells a little."""
        nll, c = _nll(block)
        w = torch.zeros_like(nll)
        w[c == 1] = args.w_copied; w[c == 2] = args.w_changed; w[c == 3] = 1.0
        return (nll * w).sum() / w.sum()

    def changed_loss_on(block):
        nll, c = _nll(block)
        return (nll[c == 2].sum(), int((c == 2).sum()))

    # ---- OPENING LOSS ----  measured, reported, not a gate. See the header.
    model.eval()
    probe, n = 0.0, 0
    _ops = [0.0, 0]
    with torch.no_grad():
        step = max(1, len(examples) // max(args.novelty_probe, 1))
        for block in examples[::step][:args.novelty_probe]:
            _v, _c = _nll(block)
            probe += float(_v[_c > 0].mean())
            _ops[0] += float(_v[_c == 2].sum()); _ops[1] += int((_c == 2).sum())
            n += 1
    opening = probe / max(n, 1)
    opening_changed = _ops[0] / max(_ops[1], 1)
    print(f"  OPENING LOSS      changed-cell {opening_changed:.4f}/tok   (all answer tokens "
          f"{opening:.4f}) over {n} examples   (recorded, not a gate)", flush=True)

    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.lr, weight_decay=args.weight_decay)
    # The schedule is sized to the MAXIMUM dose, not the expected one. An early stop therefore
    # ends at a non-zero LR — stated in the run record rather than hidden, because a schedule sized
    # to a smaller budget would drive LR to zero and then present the resulting flat epochs as a
    # floor found in the data.
    budget_epochs = args.max_epochs if args.train_to_floor else args.epochs
    total = len(examples) * budget_epochs
    sched_total = args.schedule_total or total
    off = args.schedule_offset
    warm = max(1, int(sched_total * args.warmup_ratio))
    # `s` counts steps in THIS invocation; the schedule is evaluated at s + offset so a continued
    # run picks up its parent's decay instead of restarting warmup on converged weights.
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min(1.0, (s + off + 1) / warm) * max(0.0, 1 - (s + off) / max(sched_total, 1)))
    if off or args.schedule_total:
        lr0 = args.lr * min(1.0, (off + 1) / warm) * max(0.0, 1 - off / max(sched_total, 1))
        print(f"  LR SCHEDULE       continued: step {off} of {sched_total}, opening lr {lr0:.3e} "
              f"(peak {args.lr:.3e}, {100*lr0/args.lr:.0f}% of peak)", flush=True)
    ckpt = args.ckpt_dir or os.path.splitext(args.out)[0] + "-ckpt"
    os.makedirs(ckpt, exist_ok=True)

    if args.resume_optimizer:
        _p = os.path.join(args.resume_from, "optim.pt")
        if not os.path.isfile(_p):
            sys.exit(f"FAIL: --resume-optimizer given but {_p} does not exist. A resume without "
                     f"the optimizer is not a continuation; refusing to pretend it is.")
        _st = torch.load(_p, map_location="cpu")
        opt.load_state_dict(_st["opt"])
        print(f"  resumed OPTIMIZER from {_p}  (parent was at step {_st.get('step','?')})", flush=True)

    model.train()
    hist, step, t0 = [], 0, time.time()

    # ---- NOTHING IS LOST ON A KILL OR A CRASH ----
    # Weights already survive via --checkpoint-every. The RUN RECORD did not, and a run whose
    # record says "unfinished" is refused by every downstream guard even though its adapter is
    # sitting right there. save_state() writes a complete, honestly-labelled record from any exit.
    epoch_means, flat_run, stop_reason = [], 0, None
    holdout_evals = []
    malformed = []

    def save_state(status, note=""):
        try:
            torch.save(get_peft_model_state_dict(model), os.path.join(ckpt, "adapter.pt"))
            model.save_pretrained(ckpt)
        except Exception as e:                      # a save failure must not mask the real error
            print(f"  WARNING: adapter save failed during {status}: {e}", file=sys.stderr)
        w = hist[-100:] if len(hist) >= 100 else hist
        rec = {"config": vars(args), "opening_loss": opening, "status": status,
               "steps": step, "epoch_means": epoch_means, "stop_reason": stop_reason,
               "loss_history": hist, "clean": len(clean),
               "holdout_evals": holdout_evals, "malformed": malformed,
               "rejected": [t for t, _ in rejected], "adapter": ckpt,
               "best_checkpoint": (ckpt + "-best") if os.path.isdir(ckpt + "-best") else None,
               "hours": (time.time() - t0) / 3600}
        if note:
            rec["note"] = note
        if w:
            rec["final_loss"] = sum(w) / len(w)
        try:
            with open(args.out, "w") as fh:
                json.dump(rec, fh, indent=1)
            print(f"  saved {status} state: {step} steps, adapter in {ckpt}, record in {args.out}",
                  flush=True)
        except Exception as e:
            print(f"  WARNING: record write failed during {status}: {e}", file=sys.stderr)

    def _on_signal(signum, _frame):
        name = {2: "SIGINT", 15: "SIGTERM"}.get(signum, str(signum))
        print(f"\n  {name} received at step {step} — saving before exit.", flush=True)
        save_state("interrupted", f"{name} at step {step}")
        sys.exit(130 if signum == 2 else 143)

    import signal
    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    def eval_holdout(tag):
        """Forward-only mean loss on held-out instances of the mechanics being trained.

        Per TASK, not pooled: a pooled mean hides the case this exists to catch, where a few tasks
        move a long way and the rest move the other way. No backward pass, no optimizer step, and
        training mode is restored on the way out.
        """
        if not holdout:
            return None
        was_training = model.training
        model.eval()
        ev_t0 = time.time()
        def _pass(sets):
            pt, nb = {}, 0
            ch_sum = [0.0, 0]
            cp_sum = [0.0, 0]
            _pass.solved = 0
            with torch.no_grad():
                for tid in sorted(sets):
                    tot = 0.0
                    for demos in sets[tid]:
                        # ONE forward per block: both numbers come from the same NLL vector. Two
                        # calls doubled every read (31 min vs 15) on FT-022.
                        _v, _c = _nll(demos)
                        _pass.solved += _solved(_c)
                        tot += float(_v[_c > 0].mean())
                        ch_sum[0] += float(_v[_c == 2].sum()); ch_sum[1] += int((_c == 2).sum())
                        cp_sum[0] += float(_v[_c == 1].sum()); cp_sum[1] += int((_c == 1).sum())
                    pt[tid] = tot / len(sets[tid])
                    nb += len(sets[tid])
            _pass.changed = ch_sum[0] / max(ch_sum[1], 1)
            _pass.copied = cp_sum[0] / max(cp_sum[1], 1)
            return pt, nb
        per_task, blocks = _pass(holdout)
        seen_changed = _pass.changed
        seen_copied = _pass.copied
        seen_solved = _pass.solved
        u_res, u_solved = {}, {}
        for n, u in unseen_sets.items():
            u_res[n] = _pass(u); u_solved[n] = _pass.solved
        if was_training:
            model.train()
        mean = sum(per_task.values()) / len(per_task)
        rec = {"tag": tag, "step": step, "mean": mean, "tasks": len(per_task), "blocks": blocks,
               "minutes": (time.time() - ev_t0) / 60, "at_hours": (time.time() - t0) / 3600,
               "per_task": per_task, "changed_cell_nll": seen_changed, "copied_cell_nll": seen_copied,
               "solved": seen_solved}
        rec["unseen"] = {n: {"mean": sum(pt.values()) / len(pt), "blocks": nb, "per_task": pt, "solved": u_solved[n]}
                         for n, (pt, nb) in u_res.items()}
        prev = holdout_evals[-1]["mean"] if holdout_evals else None
        uprev = holdout_evals[-1].get("unseen", {}) if holdout_evals else {}
        holdout_evals.append(rec)
        delta = f"   {mean - prev:+.4f} vs previous" if prev is not None else ""
        cprev = holdout_evals[-2].get("changed_cell_nll") if len(holdout_evals) > 1 else None
        cdelta = f"   {seen_changed - cprev:+.4f} vs previous" if cprev is not None else ""
        print(f"  HOLDOUT [{tag}]  step {step}  changed-cell {seen_changed:.4f}/tok{cdelta}   "
              f"copied-cell {seen_copied:.4f}/tok   "
              f"(all answer tokens {mean:.4f}{delta.replace('   ', ' ')})  solved {seen_solved}/{blocks}  "
              f"{len(per_task)} tasks / {blocks} blocks  {rec['minutes']:.1f} min", flush=True)
        for n, u in rec["unseen"].items():
            ud = (f"   {u['mean'] - uprev[n]['mean']:+.4f} vs previous" if n in uprev else "")
            print(f"  HOLDOUT-UNSEEN [{n}] [{tag}]  step {step}  mean {u['mean']:.4f}  solved {u['solved']}/{u['blocks']}"
                  f"  over {len(u['per_task'])} tasks / {u['blocks']} blocks{ud}", flush=True)
        # DIVERGENCE HALT at every read, not only the step-20 tripwire: the fp32 adapter applies
        # ~1.9x the integrated update of any earlier run in the schedule's second half, and a late
        # divergence would otherwise burn the whole run and its slot.
        best = min(h.get("changed_cell_nll", h["mean"]) for h in holdout_evals)
        # Keep the adapter at the best changed-cell holdout read: after a self-stop
        # the leg's output is this checkpoint, not the halting step's. Recorded as best_checkpoint in the run record.
        if seen_changed <= best and len(holdout_evals) > 1:
            try:
                _bd = ckpt + "-best"; os.makedirs(_bd, exist_ok=True)
                model.save_pretrained(_bd); json.dump({"step": step, "changed_cell_nll": seen_changed}, open(os.path.join(_bd, "best.json"), "w"))
                rec["best_checkpoint"] = _bd
                print(f"  best holdout so far -> {_bd} (step {step})", flush=True)
            except Exception as e:
                print(f"  WARNING: best-checkpoint save failed: {e}", file=sys.stderr)
        if len(holdout_evals) > 1 and seen_changed > 1.5 * best:
            save_state("halted", f"changed-cell holdout {seen_changed:.4f} > 1.5 x best {best:.4f}")
            print(f"\n  HALT: changed-cell holdout {seen_changed:.4f} exceeds 1.5x its best {best:.4f}. "
                  f"State saved.", flush=True)
            sys.exit(3)
        # Written at every evaluation, not only at the end: a run killed between two boundaries
        # would otherwise lose every measurement it had already paid the forward passes for.
        save_state("running", f"holdout evaluated at {tag}")
        return rec

    # SECTION BOUNDARIES IN STEP TERMS. The evaluation fires where the curriculum changes what it
    # is teaching, which is the only place a per-section comparison can be read off.
    boundaries = {}
    if stage_plan:
        at = 0
        for i, n in enumerate(stage_counts):
            at += n
            if n:
                boundaries[at] = stage_plan[i][0]

    if args.score_only:
        if not holdout:
            sys.exit("FAIL: --score-only needs --holdout-root")
        # Without --resume-from the adapter is fresh (LoRA B = 0), so the read scores the base model itself.
        r = eval_holdout(f"score-only {args.resume_from or 'BASE (fresh adapter)'}")
        with open(args.out, "w") as fh:
            json.dump({"config": vars(args), "score_only": True, "holdout_evals": holdout_evals}, fh, indent=1)
        print(f"  SCORE-ONLY done: {args.resume_from} -> {args.out}", flush=True)
        sys.exit(0)
    if holdout:
        first = eval_holdout("before training")
        n_bound = len(boundaries) or 1
        projected = first["minutes"] * (n_bound * budget_epochs + 1) / 60
        print(f"  holdout schedule  before training, at {n_bound} section boundar(ies) per epoch "
              f"x {budget_epochs} epoch(s), and after the last step", flush=True)
        print(f"     projected cost {projected:.2f} h of forward passes over the whole run "
              f"(--holdout-max-per-task trims it)", flush=True)
    try:
      for ep in range(budget_epochs):
          ep_start = len(hist)
          for ei, block in enumerate(examples):
              try:
                  loss = train_loss_on(block)
              except ValueError as e:
                  # A block that cannot be serialized is a corpus defect, not a reason to lose the
                  # run. Two malformed blocks out of 10,728 ended one at step 8817 with 8,778
                  # steps of finished curriculum behind it. Skip, count, and carry the count in the
                  # record so a corpus that is quietly rotting stays visible.
                  malformed.append({"index": ei, "error": str(e)})
                  print(f"  skipping malformed block {ei}: {e}", flush=True)
                  continue
              loss.backward()
              torch.nn.utils.clip_grad_norm_(
                  [p for p in model.parameters() if p.requires_grad], args.max_grad_norm)
              opt.step()
              sched.step()
              opt.zero_grad(set_to_none=True)
              hist.append(float(loss))
              step += 1

              if step == args.tripwire_steps:
                  mean = sum(hist) / len(hist)
                  print(f"  step {step}: mean loss {mean:.4f}", flush=True)
                  if mean > args.tripwire_loss:
                      print(f"\n  HALT: mean loss {mean:.4f} over the first {step} steps exceeds "
                            f"{args.tripwire_loss}.", flush=True)
                      print("  The corpus is not being learned; continuing would burn hours to "
                            "confirm it.", flush=True)
                      with open(args.out, "w") as fh:
                          json.dump({"halted": "loss tripwire", "mean_loss": mean, "step": step,
                                     "opening_loss": opening, "config": vars(args),
                                     "loss_history": hist}, fh, indent=1)
                      sys.exit(0)
              if step % args.checkpoint_every == 0:
                  torch.save(get_peft_model_state_dict(model),
                             os.path.join(ckpt, "adapter.pt"))
                  # adapter.pt is for --resume-from; save_pretrained is for the MERGE. A checkpoint
                  # that only the trainer can read is not a checkpoint of anything downstream.
                  model.save_pretrained(ckpt)
                  torch.save({"opt": opt.state_dict(), "sched": sched.state_dict(), "step": step},
                             os.path.join(ckpt, "optim.pt"))
                  w = hist[-args.checkpoint_every:]
                  print(f"  step {step}/{total}  loss {sum(w)/len(w):.4f}  "
                        f"{(time.time()-t0)/60:.1f} min", flush=True)
                  with open(args.out, "w") as fh:
                      json.dump({"config": vars(args), "opening_loss": opening, "step": step,
                                 "total": total, "loss_history": hist,
                                 "holdout_evals": holdout_evals, "malformed": malformed,
                                 "clean": len(clean), "rejected": [t for t, _ in rejected]},
                                fh, indent=1)

              if holdout:
                  if (ei + 1) in boundaries:
                      eval_holdout(f"end of {boundaries[ei + 1]}, epoch {ep + 1}")
                  elif args.holdout_every and step % args.holdout_every == 0:
                      eval_holdout(f"step {step}")

          # ---- END OF EPOCH: has the loss floored? ----
          ep_hist = hist[ep_start:]
          if ep_hist:
              ep_mean = sum(ep_hist) / len(ep_hist)
              epoch_means.append(ep_mean)
              if len(epoch_means) >= 2:
                  prev = epoch_means[-2]
                  rel = (prev - ep_mean) / prev if prev else 0.0
                  flat_run = flat_run + 1 if rel < args.floor_rel else 0
                  print(f"  epoch {ep+1}/{budget_epochs}  mean loss {ep_mean:.4f}  "
                        f"rel improvement {rel:+.3%}  flat epochs {flat_run}/{args.floor_patience}",
                        flush=True)
              else:
                  print(f"  epoch {ep+1}/{budget_epochs}  mean loss {ep_mean:.4f}", flush=True)
              if args.train_to_floor and flat_run >= args.floor_patience:
                  stop_reason = (f"loss floored: {flat_run} consecutive epochs under "
                                 f"{args.floor_rel:.1%} relative improvement")
                  print(f"  STOP — {stop_reason}", flush=True)
                  break
      if args.train_to_floor and stop_reason is None:
          stop_reason = f"reached --max-epochs {args.max_epochs} without flooring"
          print(f"  STOP — {stop_reason}. The loss was STILL FALLING; this is a dose ceiling, "
                f"not a converged run.", flush=True)

    except BaseException as e:
        # Save, record WHY, then re-raise. A crash that silently becomes a saved run is worse than
        # losing the run: the next stage would consume a half-trained adapter as if it were finished.
        save_state("crashed", f"{type(e).__name__}: {e}")
        raise

    # Skipped when the last section boundary already landed on this step, rather than paying for
    # the same measurement twice and recording it as two.
    if holdout and (not holdout_evals or holdout_evals[-1]["step"] != step):
        eval_holdout("after training")

    torch.save(get_peft_model_state_dict(model), os.path.join(ckpt, "adapter.pt"))
    model.save_pretrained(ckpt)
    win = hist[-100:] if len(hist) >= 100 else hist
    print(f"\n  {step} steps, {(time.time()-t0)/3600:.2f} h", flush=True)
    print(f"  opening loss {opening:.4f} -> final {sum(win)/len(win):.4f}", flush=True)
    # State what was written and in which form, because the failure this fixes was invisible:
    # the run reported success and the merge refused the result twenty minutes later.
    have_cfg = os.path.isfile(os.path.join(ckpt, "adapter_config.json"))
    print(f"  adapter written to {ckpt}", flush=True)
    print(f"  PEFT dir  adapter_config.json {'present' if have_cfg else 'MISSING'}  "
          f"(merge-loadable: {'yes' if have_cfg else 'NO — merge will refuse this'})", flush=True)
    with open(args.out, "w") as fh:
        json.dump({"config": vars(args), "opening_loss": opening,
                   "epoch_means": epoch_means, "stop_reason": stop_reason,
                   "epochs_run": len(epoch_means), "epoch_budget": budget_epochs,
                   "lr_schedule_note": ("the LR schedule is sized to the epoch BUDGET, so a run "
                                        "that stopped early ended at a non-zero learning rate and "
                                        "is not identical to a fixed-length run of the same count"),
                   "final_loss": sum(win) / len(win), "steps": step,
                   "holdout_evals": holdout_evals, "malformed": malformed,
                   "holdout_note": ("mean of PER-TASK means over held-out instances of the trained "
                                    "mechanics; forward-only, never trained on"),
                   "hours": (time.time() - t0) / 3600, "loss_history": hist,
                   "clean": len(clean), "rejected": [t for t, _ in rejected],
                   "adapter": ckpt}, fh, indent=1)
    print(f"  wrote {args.out}", flush=True)


if __name__ == "__main__":
    main()
