#!/usr/bin/env python3
"""real-loo-stage.py -- the REAL source for a hop as distinct blocks instead of raw repeats. Read by crucible-hop6-stage.py with REAL_DIR=<OUT> (in place of its raw A2 copy loop).
Distinct blocks per task:
  test<k>  the task's demos + its real test pair k (the raw block, as the hops use today)
  loo<j>   tasks with >= 3 demos: demo j as the test, the other demos as demos
Sources: arc2 = ARC-AGI-2 public training minus P1/P2/P3 by task id (692); concept = ConceptARC (corpus + MinimalTasks, as hop 4).
Shares of TOTAL est tokens (the hops' tok(); default arc2 0.14, concept 0.035 of 85M): each source's distinct blocks are shuffled
and dealt round-robin, one file per copy, until its share is met, so copies of one block differ only by name (the packer's
--views 1 --view-offset 1 gives each copy its own view). Files are interleaved by token share, so a reader trimming to fewer
tokens keeps the ratio. Identical blocks (same content hash) are written once.
Writes OUT/blocks/NNNNNN_re-<src>-<task>-<variant>-c<copy>_001.json, OUT/manifest.json (one entry per distinct block: task, source,
variant, loo_index, sha256 of the block, est_tok, copies) and OUT/stage-report.json.
Usage: real-loo-stage.py OUT [--total 85e6] [--shares arc2=0.14,concept=0.035] [--seed 1019]
"""
import argparse, glob, hashlib, json, os, random, statistics as st, sys
HERE = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(os.path.dirname(HERE), "crucible")   # corpus, crucible
ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--total", type=float, default=85e6)
ap.add_argument("--shares", default="arc2=0.14,concept=0.035"); ap.add_argument("--seed", type=int, default=1019)
a = ap.parse_args(); OUT = a.out
if os.path.exists(OUT): sys.exit(f"FAIL: {OUT} exists. Nothing written.")
SH = {k: float(v) for k, v in (x.split("=") for x in a.shares.split(","))}
def gt(g): return len(g) * (len(g[0]) + 1) if g else 0
def tok(d): return sum(gt(p["input"]) + gt(p["output"]) + 8 for p in d["train"] + d["test"])   # = crucible-hop6-stage.py
def h(d): return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()
pr = json.load(open(os.path.join(HERE, "evals", "hop1-probes-20261007.json")))
HELD = set(pr["P1_nvarc_training"]) | set(pr["P2_arc_agi_2_training"]) | set(pr["P3_unseen"])
tasks = {"arc2": [], "concept": []}
for f in sorted(glob.glob(os.path.join(SRC, "data-arc-agi-2", "data", "training", "*.json"))):
    n = os.path.basename(f)[:-5]
    if n not in HELD: tasks["arc2"].append((n, json.load(open(f))))
for f in sorted(glob.glob(os.path.join(SRC, "data-sources", "conceptarc", "corpus", "**", "*.json"), recursive=True)
                + glob.glob(os.path.join(SRC, "data-sources", "conceptarc", "MinimalTasks", "*.json"))):
    tasks["concept"].append((os.path.basename(f)[:-5].replace("_", "-"), json.load(open(f))))
assert len(tasks["arc2"]) == 692, len(tasks["arc2"])
distinct = {}; seen = {}; dup = 0
for src, ts in tasks.items():
    out = []
    for n, t in ts:
        tr = t["train"]; te = [x for x in t["test"] if x.get("output")]
        cands = [(f"test{k}", None, {"train": tr, "test": [p]}) for k, p in enumerate(te)]
        if len(tr) >= 3: cands += [(f"loo{j}", j, {"train": tr[:j] + tr[j + 1:], "test": [tr[j]]}) for j in range(len(tr))]
        for var, j, d in cands:
            x = h(d)
            if x in seen: dup += 1; continue
            seen[x] = f"{src}/{n}/{var}"; out.append({"task": n, "source": src, "variant": var, "loo_index": j, "sha256": x, "est_tok": tok(d), "copies": 0, "_d": d})
    distinct[src] = out
streams = {}
for src, bl in distinct.items():
    random.Random(f"{a.seed}:{src}").shuffle(bl); budget = SH[src] * a.total; got = 0; s = []; c = 0
    while got < budget:
        for b in bl:
            if got >= budget: break
            b["copies"] += 1; s.append((f"re-{src}-{b['task']}-{b['variant']}-c{b['copies']}", b["_d"], b["est_tok"])); got += b["est_tok"]
        c += 1
    streams[src] = s
pos = {k: 0 for k in streams}; acc = {k: 0 for k in streams}; tot = {k: sum(x[2] for x in v) or 1 for k, v in streams.items()}; order = []
while any(pos[k] < len(v) for k, v in streams.items()):        # interleave by token share (as the hop stage scripts)
    k = min((k for k, v in streams.items() if pos[k] < len(v)), key=lambda k: acc[k] / tot[k])
    order.append(streams[k][pos[k]]); pos[k] += 1; acc[k] += order[-1][2]
os.makedirs(os.path.join(OUT, "blocks"))
for i, (key, d, _) in enumerate(order): json.dump(d, open(os.path.join(OUT, "blocks", f"{i:06d}_{key}_001.json"), "w"))
man = [{k: v for k, v in b.items() if k != "_d"} for bl in distinct.values() for b in bl]
json.dump(man, open(os.path.join(OUT, "manifest.json"), "w"), indent=0)
rep = {"total_target": a.total, "shares": SH, "seed": a.seed, "files": len(order), "excluded_probe_tasks": len(HELD), "duplicate_blocks_skipped": dup}
for src, bl in distinct.items():
    cp = [b["copies"] for b in bl]
    rep[src] = {"tasks": len(tasks[src]), "distinct_blocks": len(bl), "test_blocks": sum(b["variant"].startswith("test") for b in bl),
                "loo_blocks": sum(b["variant"].startswith("loo") for b in bl), "est_tokens": sum(x[2] for x in streams[src]),
                "copies_per_block": {"min": min(cp), "median": st.median(cp), "max": max(cp)}}
json.dump(rep, open(os.path.join(OUT, "stage-report.json"), "w"), indent=1); print(json.dumps(rep, indent=1))
