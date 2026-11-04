#!/usr/bin/env python3
"""train-hop.py HOP --model-dir DIR --packed DIR --save-dir DIR --ckpt-dir DIR [--probes FILE] [--continue-from CKPT] [--resume-from CKPT] [--run]
Build the crucible-fft-train.py command for one hop from configs/hops.json and print it; --run executes it from crucible/.
The Colab and Kaggle plumbing the hops actually ran under (dataset upload, notebook, checkpoint upload) is not part of this repo.
--model-dir is the parent hop's merged model for a fresh-optimizer hop, or the base model for hop3. A carried-optimizer hop also
takes --continue-from with the parent's final checkpoint. --resume-from continues a stopped run on the same schedule."""
import argparse, json, os, shlex, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("hop")
for name in ("model-dir", "packed", "save-dir", "ckpt-dir"):
    ap.add_argument(f"--{name}", required=True)
ap.add_argument("--out", default="", help="run record JSON; default <save-dir>.json")
ap.add_argument("--probes", default="", help="probe blocks JSON; monitoring only, off when empty")
ap.add_argument("--continue-from", default="")
ap.add_argument("--resume-from", default="")
ap.add_argument("--run", action="store_true")
a = ap.parse_args()
hops = {h["hop"]: h for h in json.load(open(os.path.join(ROOT, "configs", "hops.json")))["hops"]}
if a.hop not in hops:
    sys.exit(f"FAIL: unknown hop {a.hop}; known: {sorted(hops)}")
h = hops[a.hop]
cmd = ["accelerate", "launch", "--config_file", "fft-single.yaml", "crucible-fft-train.py",
       "--model-dir", a.model_dir, "--packed", a.packed, "--save-dir", a.save_dir, "--out", a.out or a.save_dir.rstrip("/") + ".json", "--ckpt-dir", a.ckpt_dir,
       "--optim", h["optim"], "--master-dtype", h["master_dtype"], "--grad-ckpt", h["grad_ckpt"], "--grad-accum", h["grad_accum"], "--lr", h["lr"],
       "--epochs", h["epochs"], "--checkpoint-every", h["checkpoint_every"], "--checkpoint-at-hours", "22.0", "--keep-local", "2",
       "--weight-decay", h["weight_decay"], "--max-grad-norm", h["max_grad_norm"], "--w-copied", h["w_copied"], "--w-changed", h["w_changed"]]
if float(h["min_lr_ratio"].split()[0]) != 0:
    cmd += ["--min-lr-ratio", h["min_lr_ratio"]]
cmd += ["--async-ckpt", h["async_ckpt"], "--holdout-every", h["holdout_every"], "--log-every", h["log_every"]]
if a.probes:
    cmd += ["--probe-every", h["probe_every"], "--probes", a.probes]
if a.continue_from:
    cmd += ["--continue-from", a.continue_from]
if a.resume_from:
    cmd += ["--resume-from", a.resume_from]
print(shlex.join(cmd))
if a.run:
    sys.exit(subprocess.call(cmd, cwd=os.path.join(ROOT, "crucible")))
