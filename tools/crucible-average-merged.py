#!/usr/bin/env python3
"""Weighted average of N MERGED models, tensor by tensor.

The other way to build a soup. crucible-soup-stack.py averages ADAPTERS, which is exact and cheap
but only defined when every delta is measured from the same origin; FT-009 was trained over
FT-007's merged weights, so its adapter's stored base_layer rows are not BASE-NV's and the
algebra depends on how the merge script folds the resized embedding rows. This tool does not
need to know: it averages the finished weights, where 0.5*X + 0.5*Y means exactly that.

Costs a merge per parent and a full-size output. Use the adapter route when the bases match.

Every model must hold the same tensor names, shapes and dtypes. Computation is float32, the
result is cast back to the input dtype -- bf16 in this lineage -- so the output is the correctly
rounded average rather than an average of roundings.
"""
import argparse, json, os, sys
import torch
from safetensors.torch import load_file, save_file


def main():
    ap = argparse.ArgumentParser(description="weighted average of N merged models")
    ap.add_argument("--model", action="append", required=True, metavar="DIR:COEF")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    specs = []
    for s in a.model:
        d, _, c = s.rpartition(":")
        if not d:
            sys.exit(f"FAIL: --model wants DIR:COEF, got {s!r}")
        specs.append((os.path.abspath(os.path.expanduser(d)), float(c)))
    if len(specs) < 2:
        sys.exit("FAIL: give at least two models.")
    if os.path.exists(a.out):
        sys.exit(f"FAIL: {a.out} exists. Refusing to overwrite a merged model.")

    tot = sum(c for _, c in specs)
    print("== inputs")
    for d, c in specs:
        print(f"   {c:+.4g} * {d}")
    print(f"   coefficients sum to {tot:.6g}"
          + ("" if abs(tot - 1.0) < 1e-9 else "   <- NOT 1, this is not an average"))

    tens = [load_file(os.path.join(d, "model.safetensors")) for d, _ in specs]
    keys = sorted(tens[0])
    for t, (d, _) in zip(tens[1:], specs[1:]):
        if sorted(t) != keys:
            sys.exit(f"FAIL: {d} holds a different tensor set.")
    for k in keys:
        for t, (d, _) in zip(tens, specs):
            if t[k].shape != tens[0][k].shape or t[k].dtype != tens[0][k].dtype:
                sys.exit(f"FAIL: {k} differs in shape or dtype in {d}.")

    out, ident = {}, 0
    for k in keys:
        acc = None
        for t, (_, c) in zip(tens, specs):
            x = t[k].float() * c
            acc = x if acc is None else acc + x
        out[k] = acc.to(tens[0][k].dtype)
        if all(torch.equal(t[k], tens[0][k]) for t in tens[1:]):
            ident += 1

    os.makedirs(a.out, exist_ok=True)
    save_file(out, os.path.join(a.out, "model.safetensors"))
    for d, _ in specs[:1]:
        for f in os.listdir(d):
            if f.endswith(".json") or f.startswith("tokenizer"):
                if f in ("merge-provenance.json", "model-metadata.json", "model-instance-metadata.json"):
                    continue
                with open(os.path.join(d, f), "rb") as fh, open(os.path.join(a.out, f), "wb") as gh:
                    gh.write(fh.read())
    json.dump({"average_of": [d for d, _ in specs], "coefficients": [c for _, c in specs],
               "tensors": len(keys), "identical_across_inputs": ident,
               "method": "tensor-wise weighted average in float32, cast back to the input dtype"},
              open(os.path.join(a.out, "average-provenance.json"), "w"), indent=1)
    print(f"== {len(keys)} tensors averaged, {ident} were identical across all inputs")
    print(f"   wrote {a.out}")


if __name__ == "__main__":
    main()
