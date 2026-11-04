#!/usr/bin/env python
# crucible-profile.py — inference and test-time-training budget profiler.
#
# PURPOSE: one comparable table of decode throughput and LoRA step time for the same model on
# the same prompt batch, across whatever hardware it is run on. How many samples fit per task,
# and whether per-task test-time training fits the runtime budget, are arithmetic on those two
# numbers.
#
# SAME SCRIPT, THREE VENUES, ON PURPOSE. A Kaggle-only notebook would produce numbers that
# cannot be compared to home measurements taken with different batch shapes or token counts, and
# the whole point of the table is the comparison. Device detection is automatic; nothing about
# the measurement changes between venues.
#
# WHAT IS MEASURED
#   load_s        wall time to get weights onto the device(s)
#   gen_tok_s     decode throughput on a fixed prompt batch at a fixed new-token count
#   ttt_step_s    one LoRA optimizer step on a demo-pair-shaped batch — the unit that decides
#                 whether per-task test-time training fits the runtime budget
#
# HONEST LIMITS, so the table is not over-read:
#   * Multi-GPU here is device_map="auto" pipeline sharding, NOT tensor parallel. On L4x4 that
#     buys memory, not speed — layers run sequentially across cards. Expect throughput at or
#     slightly below single-card unless a batch large enough to keep every stage busy is used.
#     A real L4x4 speedup needs vLLM/TP and is a separate measurement.
#   * On an integrated GPU with unified memory, "VRAM" is system RAM. Bandwidth-bound decode
#     there is not comparable to a discrete card's dedicated memory on absolute grounds — such a
#     row is for sizing local work, not for ranking hardware.
#   * Thinking mode inflates token counts several-fold. This measures raw decode at a fixed
#     token count, which is deliberately mode-independent.
#
# THIS HARNESS CANNOT FETCH, deliberately. It takes a LOCAL model DIRECTORY and refuses anything
# that is not one. Passing a hub id to from_pretrained is a silent download path, so accepting
# ids would mean the harness behaves differently depending on whether a cache happens to be warm
# — and a competition submission runs with no network at all. Materialize weights beforehand with
# crucible-fetch.py (the only place hub access lives), or attach them as a Kaggle input mounted
# under /kaggle/input. Same shape at every venue.
import argparse
import json
import os
import platform
import time

PROMPT = (
    "You are given a grid transformation puzzle. The grid is 10 by 10 with colors 0-9.\n"
    "Example input row: 0 0 3 3 0 0 0 5 5 0\n"
    "Example output row: 0 0 5 5 0 0 0 3 3 0\n"
    "Describe the transformation rule and apply it to a new grid.\n"
)


def pick_dtype():
    """bf16 where the hardware has it, fp16 otherwise — and SAY WHICH.

    bf16 needs compute capability 8.0+ (Ampere). Turing T4 is 7.5 and Pascal P100 is 6.0, so a
    hardcoded bfloat16 either errors or silently falls back on those. The choice is recorded in
    the result row because fp16 and bf16 throughput are not comparable numbers: a table mixing
    them without saying so would invite exactly the wrong conclusion about which venue is faster.
    """
    import torch
    if not torch.cuda.is_available():
        return torch.float32, "fp32 (no cuda)"
    major, minor = torch.cuda.get_device_capability(0)
    if major >= 8:
        return torch.bfloat16, "bf16"
    return torch.float16, f"fp16 (sm{major}{minor} predates bf16)"


def describe_devices():
    import torch
    info = {"host": platform.node(), "torch": torch.__version__,
            "cuda_available": torch.cuda.is_available(), "devices": []}
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            p = torch.cuda.get_device_properties(i)
            info["devices"].append({
                "index": i, "name": p.name,
                "total_mem_gb": round(p.total_memory / 1e9, 1),
                "capability": f"{p.major}.{p.minor}",
            })
    info["hip"] = getattr(getattr(__import__("torch"), "version", None), "hip", None)
    return info


def profile_one(model_dir, batch=8, new_tokens=256, ttt_steps=5, ttt_seq_len=1024,
                ttt_batch=2, lora_r=16, label_in="", skip_ttt=False,
                allow_ttt_failure=False):
    """Profile ONE model and return the result row.

    Callable rather than CLI-only so the local run and the Kaggle kernel execute the same
    code. A hand-copied kernel would drift, and the comparison between venues is the only
    reason the measurement exists.
    """
    # Refuse anything that is not a materialized directory. A hub id would load fine here on a
    # machine with a warm cache and silently download on one without, which is exactly the
    # difference the offline venue cannot tolerate.
    if not os.path.isdir(model_dir):
        raise SystemExit(
            f"FAIL: {model_dir!r} is not a directory. This harness does not fetch — pass a local "
            f"model directory. Materialize one with crucible-fetch.py, or attach the model as a "
            f"Kaggle input and pass its /kaggle/input/... mount path.")
    if not any(f.endswith(".safetensors") for f in os.listdir(model_dir)):
        raise SystemExit(f"FAIL: no .safetensors in {model_dir!r} — not a model directory.")



    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    dev = describe_devices()
    dtype, dtype_note = pick_dtype()
    label = label_in or (f"{len(dev['devices'])}x{dev['devices'][0]['name']}"
                        if dev["devices"] else "cpu")
    print(f"== CRUCIBLE profiler ==\nlabel: {label}\nhost: {dev['host']}  torch {dev['torch']}"
          f"  hip={dev['hip']}")
    for d in dev["devices"]:
        print(f"  gpu{d['index']}: {d['name']}  {d['total_mem_gb']} GB  sm{d['capability']}")
    print(f"precision: {dtype_note}")
    print(f"model={model_dir} batch={batch} new_tokens={new_tokens} "
          f"ttt: steps={ttt_steps} seq={ttt_seq_len} batch={ttt_batch} r={lora_r}\n",
          flush=True)

    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=dtype, device_map="auto")
    model.eval()
    load_s = time.time() - t0
    print(f"  load_s        {load_s:.1f}", flush=True)

    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    msgs = [{"role": "user", "content": PROMPT}]
    # enable_thinking is pinned OFF so the measurement is raw decode at a fixed token count and
    # not a measurement of how long this model likes to think.
    try:
        text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True,
                                       enable_thinking=False)
    except TypeError:
        text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    enc = tok([text] * batch, return_tensors="pt").to(model.device)

    # Warm-up pass excluded from the timing: the first generate() pays kernel autotune and
    # allocator growth, which would otherwise land entirely in the reported throughput.
    with torch.no_grad():
        model.generate(**enc, max_new_tokens=8, do_sample=False, pad_token_id=pad)
    if torch.cuda.is_available():
        torch.cuda.synchronize()

    t0 = time.time()
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=new_tokens, do_sample=True,
                             temperature=0.9, top_p=1.0, top_k=0, pad_token_id=pad,
                             min_new_tokens=new_tokens)
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    gen_s = time.time() - t0
    new_tok = int((out.shape[1] - enc["input_ids"].shape[1]) * out.shape[0])
    gen_tok_s = new_tok / gen_s
    print(f"  gen_s         {gen_s:.2f}  for {new_tok} new tokens")
    print(f"  gen_tok_s     {gen_tok_s:.1f}   (batch {batch}, aggregate)", flush=True)

    peak_gb = (torch.cuda.max_memory_allocated() / 1e9) if torch.cuda.is_available() else None
    ttt_step_s = None
    if not skip_ttt:
        # Imported OUTSIDE the try: a MISSING DEPENDENCY must kill the run, not be reported as a
        # soft failure. An offline notebook without peft would otherwise complete, look healthy
        # and produce a table with a silently empty column.
        from peft import LoraConfig, get_peft_model
        try:
            # Reset the peak counter so the number reported below is the TTT phase alone, not
            # the generation phase's high-water mark — this is the value that decides whether
            # per-task LoRA fits the runtime budget, so it must not be overstated.
            if torch.cuda.is_available():
                torch.cuda.reset_peak_memory_stats()
            model.gradient_checkpointing_enable()
            model.enable_input_require_grads()
            peft_model = get_peft_model(model, LoraConfig(
                r=lora_r, lora_alpha=lora_r * 2, lora_dropout=0.0, bias="none",
                task_type="CAUSAL_LM",
                target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]))
            peft_model.train()
            opt = torch.optim.AdamW([p for p in peft_model.parameters() if p.requires_grad],
                                    lr=1e-4)
            ids = torch.randint(0, tok.vocab_size, (ttt_batch, ttt_seq_len),
                                device=model.device)
            # One un-timed step first, same reason as the generation warm-up.
            loss = peft_model(input_ids=ids, labels=ids).loss
            loss.backward(); opt.step(); opt.zero_grad()
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            t0 = time.time()
            for _ in range(ttt_steps):
                loss = peft_model(input_ids=ids, labels=ids).loss
                loss.backward(); opt.step(); opt.zero_grad()
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            ttt_step_s = (time.time() - t0) / ttt_steps
            print(f"  ttt_step_s    {ttt_step_s:.2f}   "
                  f"(LoRA r={lora_r}, batch {ttt_batch} x {ttt_seq_len} tok)", flush=True)
            if torch.cuda.is_available():
                peak_gb = torch.cuda.max_memory_allocated() / 1e9
        except ImportError:
            # A dependency problem must never be reported as a soft failure. peft imports fine
            # on Kaggle but pulls torchao in lazily, so the incompatibility surfaces here rather
            # than at the top-level import — and a swallowed ImportError produces a COMPLETE run
            # with an empty column, which on a submission is a scored run of garbage.
            raise
        except Exception as e:
            # TTT failure is RUN failure unless explicitly permitted. Continuing past it yields a
            # row with an empty column from a run that reports success — the same silent
            # degradation a swallowed ImportError produces, just with a different cause.
            print(f"  ttt_step_s    FAILED: {type(e).__name__}: {str(e)[:140]}", flush=True)
            if not allow_ttt_failure:
                raise

    if peak_gb:
        print(f"  peak_mem_gb   {peak_gb:.1f}")

    row = {"label": label, "model": model_dir, "devices": dev, "dtype": dtype_note,
           "batch": batch, "new_tokens": new_tokens, "load_s": round(load_s, 1),
           "gen_s": round(gen_s, 2), "gen_tok_s": round(gen_tok_s, 1),
           "ttt": {"steps": ttt_steps, "seq_len": ttt_seq_len, "batch": ttt_batch,
                   "lora_r": lora_r,
                   "step_s": None if ttt_step_s is None else round(ttt_step_s, 3)},
           "peak_mem_gb": None if peak_gb is None else round(peak_gb, 1),
           "multi_gpu_note": ("pipeline-sharded via device_map=auto, NOT tensor parallel — "
                              "on multi-GPU this buys memory, not speed")}
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True,
                    help="LOCAL directory holding the weights; this tool never fetches")
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--new-tokens", type=int, default=256)
    ap.add_argument("--ttt-steps", type=int, default=5)
    ap.add_argument("--ttt-seq-len", type=int, default=1024)
    ap.add_argument("--ttt-batch", type=int, default=2)
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--label", default=os.environ.get("CRUCIBLE_LABEL", ""))
    ap.add_argument("--out", default="crucible-profile.json")
    ap.add_argument("--skip-ttt", action="store_true",
                    help="deliberately profile generation only; never a fallback for a missing "
                         "dependency")
    ap.add_argument("--allow-ttt-failure", action="store_true",
                    help="report a TTT failure and keep going instead of failing the run. For "
                         "exploratory profiling only — in validation shape TTT failure IS run "
                         "failure, because a row with an empty column from a successful-looking "
                         "run is the failure mode this harness exists to prevent")
    a = ap.parse_args()
    row = profile_one(a.model_dir, batch=a.batch, new_tokens=a.new_tokens, ttt_steps=a.ttt_steps,
                      ttt_seq_len=a.ttt_seq_len, ttt_batch=a.ttt_batch, lora_r=a.lora_r,
                      label_in=a.label, skip_ttt=a.skip_ttt,
                      allow_ttt_failure=a.allow_ttt_failure)
    with open(a.out, "w") as fh:
        json.dump(row, fh, indent=1)
    print(f"\n  wrote {a.out}")


if __name__ == "__main__":
    main()
