#!/usr/bin/env python3
# ours-fresh-package.py -- screen freshly built blocks and lay them out for a curriculum build.
#
# Reads the per-task block directories a builder wrote (one problem per file, train + test with
# outputs), applies the gates below to every block, and writes the survivors as
# <out>/<kind>_<task>_<NNNN>.json with a manifest.json beside them.
#
# Gates, each counted in the manifest:
#   invalid    a grid that is not a rectangle of 0-9 values, 1-30 a side (corpus-verify.valid_grid)
#   blank      any input or output grid that is all zero
#   dup_block  the block's content hash occurs in an existing tree (curriculum-t*, synthetic*, remix*)
#   dup_pair   any of its pairs' content hashes occurs in one of those trees
#   eval_canon any pair equal to one of the 120 evaluation pairs under relabel + dihedral view
#              (corpus-verify.canon) -- must be zero
#   holdout    any input equal, under relabel + dihedral view, to an input of a held-out block
#   repeat     the block repeats one already kept in this run
# Then every task in the set is cut to the same count, the smallest any task reached, unless
# --per-task is given.
#
# usage: ours-fresh-package.py --kind nbrB --build DIR --out DIR --tasks t1,t2,... [--per-task N]
import argparse, glob, hashlib, importlib.util, json, os, pickle, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location("cv", os.path.join(HERE, "corpus-verify.py"))
cv = importlib.util.module_from_spec(sp)
sys.argv, _argv = [sys.argv[0]], sys.argv
sp.loader.exec_module(cv)
sys.argv = _argv
DATA = os.environ.get("ARC_DATA") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "crucible", "data-kaggle")


def blk_hash(b):
    core = {"train": b["train"], "test": b["test"]}
    return hashlib.sha1(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def pair_hash(p):
    return hashlib.sha1(json.dumps([p["input"], p["output"]], separators=(",", ":")).encode()).hexdigest()


def pairs(b):
    return [p for p in b.get("train", []) + b.get("test", []) if "output" in p]


def existing_index(skip):
    """Content hashes of every block and pair already in the trees a curriculum could have drawn."""
    roots = sorted(set(glob.glob(os.path.join(HERE, "curriculum-t*")) + glob.glob(os.path.join(HERE, "synthetic*"))
                       + glob.glob(os.path.join(HERE, "remix*"))))
    roots = [r for r in roots if os.path.isdir(r) and not os.path.abspath(r).startswith(skip)]
    bh, ph, hold, nfiles = set(), set(), set(), 0
    for root in roots:
        for dirpath, _dirs, files in os.walk(root):
            held = "_holdout" in dirpath.split(os.sep)
            for f in files:
                if not f.endswith(".json") or f.startswith("_") or f in ("curriculum.json", "manifest.json"):
                    continue
                try:
                    b = json.load(open(os.path.join(dirpath, f)))
                except Exception:
                    continue
                if not isinstance(b, dict) or "train" not in b:
                    continue
                nfiles += 1
                try:
                    bh.add(blk_hash(b))
                except Exception:
                    pass
                for p in pairs(b):
                    ph.add(pair_hash(p))
                    if held:
                        hold.add(cv.canon_input(p["input"]))
    return bh, ph, hold, nfiles, roots


def eval_canons():
    ch = json.load(open(os.path.join(DATA, "arc-agi_evaluation_challenges.json")))
    so = json.load(open(os.path.join(DATA, "arc-agi_evaluation_solutions.json")))
    out = set()
    for tid, t in ch.items():
        for p in t["train"]:
            out.add(cv.canon(p["input"], p["output"]))
        for p, o in zip(t["test"], so[tid]):
            out.add(cv.canon(p["input"], o))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True)
    ap.add_argument("--build", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--per-task", type=int, default=0)
    ap.add_argument("--dir-prefix", default="", help="builder's task directory prefix, e.g. mech_")
    ap.add_argument("--index-cache", default="", help="pickle of the existing-tree index; built if absent")
    ap.add_argument("--demos", type=int, default=3, help="train pairs per block (the FFT blocks carry 5-7)")
    a = ap.parse_args()
    tasks = [t for t in a.tasks.split(",") if t]
    skip = os.path.abspath(os.path.dirname(a.out.rstrip("/")))
    if a.index_cache and os.path.exists(a.index_cache):
        bh, ph, hold, nfiles, roots = pickle.load(open(a.index_cache, "rb"))
    else:
        bh, ph, hold, nfiles, roots = existing_index(skip)
        if a.index_cache:
            pickle.dump((bh, ph, hold, nfiles, roots), open(a.index_cache, "wb"))
    ev = eval_canons()
    counts = {k: 0 for k in ("seen", "invalid", "blank", "dup_block", "dup_pair", "eval_canon", "holdout", "repeat")}
    kept, mine = {}, set()
    for t in tasks:
        kept[t] = []
        for f in sorted(glob.glob(os.path.join(a.build, a.dir_prefix + t, "*.json"))):
            if os.path.basename(f).startswith("_"):
                continue
            b = json.load(open(f))
            counts["seen"] += 1
            ps = pairs(b)
            grids = [g for p in ps for g in (p["input"], p["output"])]
            if len(b.get("train", [])) != a.demos or len(b.get("test", [])) != 1 or len(ps) != a.demos + 1 \
                    or any(cv.valid_grid(g) for g in grids):
                counts["invalid"] += 1; continue
            if any(all(v == 0 for row in g for v in row) for g in grids):
                counts["blank"] += 1; continue
            h = blk_hash(b)
            if h in bh:
                counts["dup_block"] += 1; continue
            if any(pair_hash(p) in ph for p in ps):
                counts["dup_pair"] += 1; continue
            if any(cv.canon(p["input"], p["output"]) in ev for p in ps):
                counts["eval_canon"] += 1; continue
            if any(cv.canon_input(p["input"]) in hold for p in ps):
                counts["holdout"] += 1; continue
            if h in mine:
                counts["repeat"] += 1; continue
            mine.add(h)
            kept[t].append(b)
    target = a.per_task or min(len(v) for v in kept.values())
    os.makedirs(a.out, exist_ok=True)
    per_task, total = {}, 0
    for t in tasks:
        for i, b in enumerate(kept[t][:target]):
            with open(os.path.join(a.out, f"{a.kind}_{t}_{i:04d}.json"), "w") as fh:
                json.dump(b, fh)
        per_task[t] = {"survived": len(kept[t]), "written": min(target, len(kept[t]))}
        total += per_task[t]["written"]
    man = {"kind": a.kind, "blocks": total, "tasks": len(tasks), "per_task_target": target,
           "per_task": per_task, "screen": counts, "build_dir": a.build,
           "dedup_against": {"roots": [os.path.relpath(r, HERE) for r in roots], "files_indexed": nfiles,
                             "block_hashes": len(bh), "pair_hashes": len(ph), "holdout_inputs": len(hold)},
           "eval_canon_hits_in_output": 0, "format": f"{a.demos} train + 1 test, outputs on all"}
    json.dump(man, open(os.path.join(a.out, "manifest.json"), "w"), indent=1)
    print(json.dumps({k: man[k] for k in ("kind", "blocks", "tasks", "per_task_target", "screen")}))


if __name__ == "__main__":
    main()
