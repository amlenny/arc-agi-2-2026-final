#!/usr/bin/env python3
"""lineage-query.py -- what has model X trained on, and which pool files has it never seen. Read-only.
Lineage: lineage-map.json (model -> parent -> its runs' dirs); blocks -> pool files: evals/lineage/lineage.sqlite (lineage-index.py).
For MODEL (and every ancestor) it collects the pool files its dirs map to, per pool, and writes
  evals/lineage/never-seen-<MODEL>.json   per pool: total, seen, never_seen (pool file paths); per dir: blocks and unmatched
  evals/lineage/seen-<MODEL>.picks.json   {"blocks": {pool: [absolute paths seen]}} -- feed to a builder as EXCLUDE_PICKS=<this>
Pools: s120, s120-holdout, s120-fresh, breadth, breadth-deep100, remix* (files from lineage.sqlite); nvarc (files under $NVARC_DIR);
real-arc2 / real-concept (task ids). Unmatched blocks (how = none) cannot be credited to a pool file, so never_seen can overstate
by at most that many; the report gives the count for every dir in the lineage. A pool file canon-equal to a seen one is seen.
Usage: lineage-query.py MODEL [--pool POOL ...]
"""
import argparse, glob, json, os, sqlite3, sys
HERE = os.path.dirname(os.path.abspath(__file__))
NV = os.environ.get("NVARC_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "crucible", "data-sources", "nvarc-synthetic-puzzles"))
SRC = os.path.join(os.path.dirname(HERE), "crucible")
ap = argparse.ArgumentParser(); ap.add_argument("model"); ap.add_argument("--pool", nargs="*", default=None); a = ap.parse_args()
M = json.load(open(os.path.join(HERE, "lineage-map.json")))["models"]
if a.model not in M: sys.exit(f"FAIL: {a.model} not in lineage-map.json ({', '.join(M)})")
chain, x = [], a.model
while x: chain.append(x); x = M[x]["parent"]
dirs = [d for m in chain for d in M[m]["dirs"]]
db = sqlite3.connect(os.path.join(HERE, "evals", "lineage", "lineage.sqlite"))
done = {d: (n, mt) for d, n, mt in db.execute("select dir, blocks, matched from done")}
missing = [d for d in dirs if d not in done]
if missing: sys.exit(f"FAIL: not indexed yet: {missing} (run lineage-index.py)")
universe = {}
for p, f in db.execute("select pool, file from pool"): universe.setdefault(p, set()).add(f)
universe["nvarc"] = {os.path.relpath(f, NV) for f in glob.glob(os.path.join(NV, "nvarc_*", "*", "*.json"))}
universe["real-arc2"] = {os.path.basename(f)[:-5] for f in glob.glob(os.path.join(SRC, "data-arc-agi-2", "data", "training", "*.json"))}
universe["real-concept"] = {os.path.basename(f)[:-5].replace("_", "-") for f in glob.glob(os.path.join(SRC, "data-sources", "conceptarc", "corpus", "**", "*.json"), recursive=True)
                            + glob.glob(os.path.join(SRC, "data-sources", "conceptarc", "MinimalTasks", "*.json"))}
seen = {}
q = "select pool, pool_file from train where dir in (%s) and pool_file is not null" % ",".join("?" * len(dirs))
for p, f in (db.execute(q, dirs) if dirs else []): seen.setdefault(p, set()).add(f)
# a block is credited to ONE pool file (lineage-index.py: the first canon hit), but pools hold canon-equal copies (deep100 starts
# with breadth's own files): every pool file canon-equal to a seen one counts as seen too (10-19, the breadth2 check found 83)
pcanon = {}; bycanon = {}
for p, f, h in db.execute("select pool, file, canon from pool"):
    if h: pcanon[(p, f)] = h; bycanon.setdefault(h, []).append((p, f))
sc = {pcanon[(p, f)] for p, fs in seen.items() for f in fs if (p, f) in pcanon}
via_canon = 0
for h in sc:
    for p, f in bycanon[h]:
        if f not in seen.setdefault(p, set()): seen[p].add(f); via_canon += 1
for m in chain:   # a model's own pretraining recorded as whole pools (BASE-NV: NVARC's data), every file counts as seen
    for p in M[m].get("seen_all_pools", []): seen.setdefault(p, set()).update(universe.get(p, set()))
pools = a.pool or sorted(set(universe) | set(seen))
absp = lambda p, f: os.path.join(NV, f) if p == "nvarc" else (f if p.startswith("real-") else os.path.join(HERE, f))
rep = {"model": a.model, "lineage": chain, "seen_via_canon_copy": via_canon, "dirs": {d: {"blocks": done[d][0], "unmatched": done[d][0] - done[d][1]} for d in dirs},
       "seen_all_pools": {m: M[m]["seen_all_pools"] for m in chain if M[m].get("seen_all_pools")}, "pools": {}}
for p in pools:
    U, S = universe.get(p, set()), seen.get(p, set())
    rep["pools"][p] = {"total": len(U), "seen": len(S & U), "seen_not_in_pool_index": len(S - U), "never_seen": sorted(absp(p, f) for f in U - S)}
out = os.path.join(HERE, "evals", "lineage")
json.dump(rep, open(os.path.join(out, f"never-seen-{a.model}.json"), "w"), indent=1)
json.dump({"model": a.model, "blocks": {p: sorted(absp(p, f) for f in seen.get(p, set())) for p in pools}},
          open(os.path.join(out, f"seen-{a.model}.picks.json"), "w"))
print(f"{a.model}: lineage {' <- '.join(chain)} | seen via a canon-equal copy {via_canon} | dirs {len(dirs)}, unmatched blocks {sum(v['unmatched'] for v in rep['dirs'].values())}")
for p, v in rep["pools"].items():
    print(f"  {p:16} total {v['total']:7} | seen {v['seen']:7} | never seen {len(v['never_seen']):7}" + (f" | seen but not in pool index {v['seen_not_in_pool_index']}" if v["seen_not_in_pool_index"] else ""))
if rep["seen_all_pools"]: print("  whole pools seen in pretraining:", rep["seen_all_pools"])
