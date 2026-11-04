#!/usr/bin/env python3
"""Screen a freshly generated tree into ours-fresh-<date>/<kind>/: legal grids, no all-zero grid, block
and pair content-hash dedup against every existing tree, canon() vs the 120 eval pairs, equal count
per task, and a manifest with every number. Usage: screen-ours-fresh.py SRC_TREE KIND OUT_ROOT"""
import sys, os, json, glob, hashlib, collections, importlib.util
DIAG = os.path.dirname(os.path.abspath(__file__))
src_tree, kind, out_root = sys.argv[1], sys.argv[2], sys.argv[3]
sp = importlib.util.spec_from_file_location("cv", os.path.join(DIAG, "corpus-verify.py")); cv = importlib.util.module_from_spec(sp); sp.loader.exec_module(cv)
def h(obj): return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
def legal(g):
    return isinstance(g, list) and 1 <= len(g) <= 30 and all(isinstance(r, list) and len(r) == len(g[0]) and 1 <= len(r) <= 30 and all(isinstance(v, int) and 0 <= v <= 9 for v in r) for r in g)
def blank(g): return all(v == 0 for r in g for v in r)
# existing content: every block and every pair under every curriculum/synthetic/remix tree
seen_blocks, seen_pairs, ntrees, nfiles = set(), set(), 0, 0
for tree in sorted(glob.glob(os.path.join(DIAG, "curriculum-t*")) + glob.glob(os.path.join(DIAG, "synthetic*")) + glob.glob(os.path.join(DIAG, "remix*"))):
    if not os.path.isdir(tree) or os.path.abspath(tree) == os.path.abspath(src_tree): continue
    ntrees += 1
    for f in glob.glob(os.path.join(tree, "**", "*.json"), recursive=True):
        if os.path.basename(f).startswith("_") or os.path.basename(f) in ("curriculum.json", "WHY.txt"): continue
        try: b = json.load(open(f))
        except Exception: continue
        if not isinstance(b, dict) or "train" not in b: continue
        nfiles += 1
        seen_blocks.add(h({"train": b["train"], "test": b["test"]}))
        for p in b["train"] + b.get("test", []): seen_pairs.add(h([p["input"], p.get("output")]))
# the 120 eval pairs, canonical
ev = {}
for split in ("evaluation",):
    for f in glob.glob(os.path.join(os.path.dirname(DIAG), "crucible", "data-arc-agi-2", "data", split, "*.json")):
        t = json.load(open(f))
        for p in t["train"] + t["test"]:
            if p.get("output"): ev[cv.canon(p["input"], p["output"])] = os.path.basename(f)
kept = collections.defaultdict(list); rej = collections.Counter(); per_task_seen = collections.Counter()
for f in sorted(glob.glob(os.path.join(src_tree, "*", "*.json"))):
    name = os.path.basename(f)
    if name.startswith("_"): continue
    task = os.path.basename(os.path.dirname(f)); b = json.load(open(f)); per_task_seen[task] += 1
    pairs = b["train"] + b["test"]
    if not all(legal(p["input"]) and legal(p["output"]) for p in pairs): rej["illegal-grid"] += 1; continue
    if any(blank(p["input"]) or blank(p["output"]) for p in pairs): rej["blank-grid"] += 1; continue
    if h({"train": b["train"], "test": b["test"]}) in seen_blocks: rej["dup-block"] += 1; continue
    if any(h([p["input"], p["output"]]) in seen_pairs for p in pairs): rej["dup-pair"] += 1; continue
    if any(cv.canon(p["input"], p["output"]) in ev for p in pairs): rej["eval-canon-hit"] += 1; continue
    for p in pairs: seen_pairs.add(h([p["input"], p["output"]]))      # within-tree dedup too
    seen_blocks.add(h({"train": b["train"], "test": b["test"]}))
    kept[task].append((name, b))
n_equal = min(len(v) for v in kept.values()) if kept else 0
if len(sys.argv) > 4:
    n_equal = min(n_equal, int(sys.argv[4]))      # optional per-task cap, so the delivery lands on the number asked
out = os.path.join(out_root, kind); os.makedirs(out, exist_ok=True)
written = collections.Counter()
for task, blocks in sorted(kept.items()):
    for name, b in blocks[:n_equal]:
        json.dump(b, open(os.path.join(out, name), "w")); written[task] += 1
man = {"kind": kind, "built_from": os.path.abspath(src_tree), "date": os.path.basename(out_root), "tasks": len(written),
       "blocks": sum(written.values()), "per_task": n_equal, "per_task_written": dict(written), "generated_per_task": dict(per_task_seen),
       "rejected": dict(rej), "dedup_against": {"trees": ntrees, "blocks": nfiles, "distinct_pairs": len(seen_pairs)},
       "eval_canon_hits": rej["eval-canon-hit"], "format": "<kind>_<task>_<grade>_<n>.json, train 3 demos + test 1 with output, _skeleton_sha per block",
       "gates": ["legal grid 1-30 a side, ints 0-9", "no all-zero grid", "block content hash and pair content hash unseen in every curriculum-t*/synthetic*/remix* tree and within this set", "canon() vs 120 eval pairs = 0", "equal per task"]}
json.dump(man, open(os.path.join(out, "manifest.json"), "w"), indent=1)
print(json.dumps({k: man[k] for k in ("tasks", "blocks", "per_task", "rejected", "dedup_against", "eval_canon_hits")}))
