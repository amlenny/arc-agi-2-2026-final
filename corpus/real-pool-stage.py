#!/usr/bin/env python3
"""real-pool-stage.py -- the real pool for the next runs: every distinct re-split block of the real tasks, each written ONCE (copy c1),
in real-loo-stage.py's layout and manifest, so a builder deals repeats itself.
Sources: arc2 = ARC-AGI-2 public training minus the hop-1 probes P1/P2/P3 (692, = real-loo); concept = ConceptARC corpus +
MinimalTasks (= real-loo); mini = MINI-ARC (149); arc1 = the ARC-AGI-1 tasks none of whose pairs is in ARC-AGI-2 training or
evaluation (25, real-pool-inventory.py). RE-ARC is not included.
Variants per task (P = all pairs with a known output, demos then tests), with the manifest's "scheme":
  current   test<k>: the demos + real test pair k (= real-loo);  loo<j>: >= 3 demos, demo j as the test, the other demos as demos
  rotate    rot<i>: pair i of P as the test, the other P-1 as demos (P >= 3)
  rotate-1  rot<i>x<k>: rot<i> without pair k (P >= 4)
Identical blocks (same content hash) are written once, under the first scheme that produced them (current, then rotate, then
rotate-1). Screens, per block: no pair canonically equal (corpus-verify.canon, = the packer's screen) to a pair of the 120 eval tasks
(data-kaggle evaluation challenges + solutions) or of a probe task (P1/P2/P3); a block with one is dropped and counted.
Files: OUT/blocks/NNNNNN_re-<src>-<task>-<variant>-c1_001.json, shuffled within source and interleaved by token share;
OUT/manifest.json (task, source, variant, scheme, loo_index, sha256, est_tok, copies=1); OUT/stage-report.json.
Usage: real-pool-stage.py [OUT=real-pool-corpus] [--seed 1022]
"""
import argparse, collections, glob, hashlib, importlib.util, json, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(os.path.dirname(HERE), "crucible")
ap = argparse.ArgumentParser(); ap.add_argument("out", nargs="?", default=os.path.join(HERE, "real-pool-corpus"))
ap.add_argument("--seed", type=int, default=1022); a = ap.parse_args(); OUT = a.out
if os.path.exists(OUT): sys.exit(f"FAIL: {OUT} exists. Nothing written.")
_cv = importlib.util.spec_from_file_location("corpus_verify", os.path.join(HERE, "corpus-verify.py"))
cv = importlib.util.module_from_spec(_cv); _cv.loader.exec_module(cv)
def gt(g): return len(g) * (len(g[0]) + 1) if g else 0
def tok(d): return sum(gt(p["input"]) + gt(p["output"]) + 8 for p in d["train"] + d["test"])   # = real-loo-stage.py
def h(d): return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()
def load(fs, key=lambda f: os.path.basename(f)[:-5]):
    out = {}
    for f in fs:
        try: d = json.load(open(f))
        except Exception: continue
        if isinstance(d, dict) and isinstance(d.get("train"), list): out[key(f)] = d   # task files only
    return out
pr = json.load(open(os.path.join(HERE, "evals", "hop1-probes-20261007.json")))
HELD = set(pr["P1_nvarc_training"]) | set(pr["P2_arc_agi_2_training"]) | set(pr["P3_unseen"])
A2 = load(sorted(glob.glob(os.path.join(SRC, "data-arc-agi-2", "data", "training", "*.json"))))
EVA = load(sorted(glob.glob(os.path.join(SRC, "data-arc-agi-2", "data", "evaluation", "*.json"))))
# screen: canonical pairs of the 120 eval tasks (with solutions) and of the probe tasks
dk = os.path.join(SRC, "data-kaggle"); ch = json.load(open(os.path.join(dk, "arc-agi_evaluation_challenges.json")))
so = json.load(open(os.path.join(dk, "arc-agi_evaluation_solutions.json"))); bad = set()
for t, d in ch.items():
    for p in d["train"]: bad.add(cv.canon(p["input"], p["output"]))
    for p, o in zip(d["test"], so[t]): bad.add(cv.canon(p["input"], o))
for t in HELD:
    for p in A2[t]["train"] + A2[t]["test"]:
        if p.get("output"): bad.add(cv.canon(p["input"], p["output"]))
taken = {json.dumps([p["input"], p["output"]]) for t in list(A2.values()) + list(EVA.values()) for p in t["train"] + t["test"] if p.get("output")}
a1 = load(sorted(glob.glob(os.path.join(SRC, "data-sources", "arc-agi-1", "data", "*", "*.json"))))
tasks = {"arc2": {k: v for k, v in A2.items() if k not in HELD},
         "concept": load(sorted(glob.glob(os.path.join(SRC, "data-sources", "conceptarc", "corpus", "**", "*.json"), recursive=True)
                             + glob.glob(os.path.join(SRC, "data-sources", "conceptarc", "MinimalTasks", "*.json"))),
                         key=lambda f: os.path.basename(f)[:-5].replace("_", "-")),
         "mini": load(sorted(glob.glob(os.path.join(SRC, "data-sources", "mini-arc", "data", "**", "*.json"), recursive=True)),
                      key=lambda f: os.path.basename(f)[:-5].replace("_", "-")),
         "arc1": {k: v for k, v in a1.items()
                  if not any(json.dumps([p["input"], p["output"]]) in taken for p in v["train"] + v["test"] if p.get("output"))}}
assert len(tasks["arc2"]) == 692, len(tasks["arc2"])
distinct = {}; seen = {}; dup = 0; screened = collections.Counter()
for src, ts in tasks.items():
    out = []
    for n, t in sorted(ts.items()):
        tr = [p for p in t["train"] if p.get("output")]; te = [x for x in t["test"] if x.get("output")]; P = tr + te
        c = [("current", f"test{k}", None, {"train": tr, "test": [p]}) for k, p in enumerate(te)]
        if len(tr) >= 3: c += [("current", f"loo{j}", j, {"train": tr[:j] + tr[j + 1:], "test": [tr[j]]}) for j in range(len(tr))]
        if len(P) >= 3: c += [("rotate", f"rot{i}", None, {"train": P[:i] + P[i + 1:], "test": [P[i]]}) for i in range(len(P))]
        if len(P) >= 4:
            c += [("rotate-1", f"rot{i}x{k}", None, {"train": [P[m] for m in range(len(P)) if m not in (i, k)], "test": [P[i]]})
                  for i in range(len(P)) for k in range(len(P)) if k != i]
        for sch, var, j, d in c:
            x = h(d)
            if x in seen: dup += 1; continue
            seen[x] = f"{src}/{n}/{var}"
            if any(cv.canon(p["input"], p["output"]) in bad for p in d["train"] + d["test"]): screened[src] += 1; continue
            out.append({"task": n, "source": src, "variant": var, "scheme": sch, "loo_index": j, "sha256": x, "est_tok": tok(d), "copies": 1, "_d": d})
    random.Random(f"{a.seed}:{src}").shuffle(out); distinct[src] = out
pos = {k: 0 for k in distinct}; acc = {k: 0 for k in distinct}; tot = {k: sum(b["est_tok"] for b in v) or 1 for k, v in distinct.items()}; order = []
while any(pos[k] < len(v) for k, v in distinct.items()):        # interleave by token share (as real-loo-stage.py)
    k = min((k for k, v in distinct.items() if pos[k] < len(v)), key=lambda k: acc[k] / tot[k])
    order.append(distinct[k][pos[k]]); pos[k] += 1; acc[k] += order[-1]["est_tok"]
os.makedirs(os.path.join(OUT, "blocks"))
for i, b in enumerate(order):
    json.dump(b["_d"], open(os.path.join(OUT, "blocks", f"{i:06d}_re-{b['source']}-{b['task']}-{b['variant']}-c1_001.json"), "w"))
json.dump([{k: v for k, v in b.items() if k != "_d"} for b in order], open(os.path.join(OUT, "manifest.json"), "w"), indent=0)
rep = {"note": "every distinct re-split block of the real tasks, once (c1); builders deal repeats", "seed": a.seed, "files": len(order),
       "excluded_probe_tasks": len(HELD), "duplicate_blocks_skipped": dup, "screened_eval_or_probe_pair": dict(screened),
       "re_arc": "not included", "sources": {}}
for src, bl in distinct.items():
    rep["sources"][src] = {"tasks": len(tasks[src]), "blocks": len(bl), "est_tok": sum(b["est_tok"] for b in bl),
                           "by_scheme": {s: {"blocks": sum(b["scheme"] == s for b in bl), "est_tok": sum(b["est_tok"] for b in bl if b["scheme"] == s)}
                                         for s in ("current", "rotate", "rotate-1")}}
rep["total"] = {s: {"blocks": sum(b["scheme"] == s for b in order), "est_tok": sum(b["est_tok"] for b in order if b["scheme"] == s)} for s in ("current", "rotate", "rotate-1")}
rep["total"]["all"] = {"blocks": len(order), "est_tok": sum(b["est_tok"] for b in order)}
json.dump(rep, open(os.path.join(OUT, "stage-report.json"), "w"), indent=1); print(json.dumps(rep, indent=1))
