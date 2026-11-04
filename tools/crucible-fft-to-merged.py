#!/usr/bin/env python3
"""crucible-fft-to-merged.py <fft model.safetensors> <reference merged dir> <out dir> <step> -- turn an FFT checkpoint's
weights (fp32, from accelerate save_state) into a merged bf16 model dir in the exact layout the ship pipeline takes
(LEG-PROCEDURE §5): the reference dir's config/tokenizer files (same base architecture), model.safetensors in bf16 with
the reference's tensor names and shapes (refuses on any mismatch), TRAINED-TO-STEP, merge-provenance.json.
"""
import json, os, shutil, sys, hashlib, torch
from safetensors import safe_open
from safetensors.torch import save_file
src, ref, out, step = sys.argv[1:5]
if os.path.exists(out): sys.exit(f"FAIL: {out} exists. Nothing written.")
with safe_open(f"{ref}/model.safetensors", "pt") as r: rk = {k: (r.get_slice(k).get_shape(), r.get_slice(k).get_dtype()) for k in r.keys()}
with safe_open(src, "pt") as s: sk = list(s.keys())
def norm(k):
    for p in ("_orig_mod.", "module."): k = k.replace(p, "")
    return k
m = {norm(k): k for k in sk}
miss = sorted(set(rk) - set(m)); extra = sorted(set(m) - set(rk))
if miss: sys.exit(f"FAIL: {len(miss)} reference tensors missing in the checkpoint, e.g. {miss[:5]}; checkpoint has e.g. {sk[:5]}")
if extra: print(f"note: {len(extra)} checkpoint tensors not in the reference, dropped: {extra[:5]}")
os.makedirs(out); t = {}
with safe_open(src, "pt") as s:
    for k in rk:
        x = s.get_tensor(m[k])
        if list(x.shape) != list(rk[k][0]): sys.exit(f"FAIL: {k} shape {list(x.shape)} != reference {rk[k][0]}")
        t[k] = x.to(torch.bfloat16).contiguous()
save_file(t, f"{out}/model.safetensors", metadata={"format": "pt"})
for f in os.listdir(ref):
    if f not in ("model.safetensors", "merge-provenance.json", "model-metadata.json", "model-instance-metadata.json", "TRAINED-TO-STEP"):
        shutil.copy(f"{ref}/{f}", f"{out}/{f}")
open(f"{out}/TRAINED-TO-STEP", "w").write(f"FFT step {step}\n")
fp = sum(float(v.float().abs().sum()) for v in t.values())
json.dump({"source": src, "kind": "full fine-tune checkpoint, fp32 -> bf16", "step": step, "config_tokenizer_from": ref,
           "tensors": len(t), "fingerprint_abs_sum": fp}, open(f"{out}/merge-provenance.json", "w"), indent=1)
print(f"wrote {out}: {len(t)} tensors bf16, fingerprint {fp:.1f}")
