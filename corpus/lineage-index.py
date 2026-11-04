#!/usr/bin/env python3
"""lineage-index.py -- content-hash lineage index: every training block in the corpus tree's corpora and curricula, mapped back to
the pool file it came from. Read-only on the data; writes evals/lineage/lineage.sqlite.
Pools (table pool: pool, key, file, canon):
  s120     synthetic/<task>/*.json (the 120 + mech_*), key = task dir; _holdout/ indexed as pool s120-holdout
  s120-fresh  ours-fresh-*/<task>/*.json (later solve-alike deliveries); remix*  synthetic-remix*/<mech+task>/*.json
  breadth  synthetic-breadth/<rule>/*.json and synthetic-breadth-deep100/<rule>/*.json (pools breadth, breadth-deep100)
  nvarc    $NVARC_DIR (default $HOME/ml/kaggle-datasets/sorokin--nvarc-synthetic-puzzles)/nvarc_{training,full}/<dir>/<file>.json:
           matched by name or by pair content, never indexed as blocks (3M pairs)
  real     ARC-AGI-2 training / ConceptARC tasks, matched by name (re-arc2-<task>, re-concept-<task>)
Training blocks (table train: dir, file, pool, pool_file, how): every *.json under hop*-corpus/blocks, fft*-corpus/blocks, breadth2-corpus/blocks,
vol*-corpus/blocks (the volume-plan segments), real-loo-corpus/blocks and
curriculum-*/s* (not -holdout, not -nvarc-src). how =
  canon   view-invariant block hash (lineage_canon.canon_hash) equal to one pool file's
  name    NVARC file stem in a hop block name (nv-<kind>-<stem>), or a real task id (re-<arc2|concept|mini>-<task>[-<variant>][-c<k>],
          arc2train_<task>_NNN)
  pairs   curriculum NVARC block (nv_nvarc_<dir>_NNN / nvarc_<dir>_NNN): every pair's view-invariant hash found in one file of <dir>
  none    no match (counted per dir in the report)
Usage: lineage-index.py [--workers 6] [--only DIR...]   (re-run adds dirs not yet indexed; --redo DIR re-indexes one)
"""
import argparse, glob, hashlib, json, os, re, sqlite3, sys, time
import multiprocessing as _mp
Pool = _mp.get_context("fork").Pool   # python 3.14 defaults to forkserver, which re-runs this unguarded script in every worker
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lineage_canon as L
NV = os.environ.get("NVARC_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "crucible", "data-sources", "nvarc-synthetic-puzzles"))
DB = os.path.join(HERE, "evals", "lineage", "lineage.sqlite")
ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=6); ap.add_argument("--only", nargs="*", default=None)
ap.add_argument("--redo", nargs="*", default=[]); a = ap.parse_args()


def canon_file(f):
    try: return f, L.canon_hash(json.load(open(f)))
    except Exception: return f, None


def pair_hash(i, o):
    return L.canon_hash({"train": [], "test": [{"input": i, "output": o}]})


def train_dirs():
    ds = [os.path.join(d, "blocks") for d in sorted(glob.glob(os.path.join(HERE, "hop*-corpus")) + glob.glob(os.path.join(HERE, "fft*-corpus"))
                                                       + glob.glob(os.path.join(HERE, "breadth2-corpus")) + glob.glob(os.path.join(HERE, "vol*-corpus"))) + [os.path.join(HERE, "real-loo-corpus")]]
    for c in sorted(glob.glob(os.path.join(HERE, "curriculum-*"))):
        if c.endswith("-holdout") or "-nvarc-src" in c or "holdout.partial" in c: continue
        ds += sorted(s for s in glob.glob(os.path.join(c, "s*")) if os.path.isdir(s))
    return [d for d in ds if os.path.isdir(d) and glob.glob(os.path.join(d, "*.json"))]


os.makedirs(os.path.dirname(DB), exist_ok=True)
db = sqlite3.connect(DB); db.execute("pragma journal_mode=wal")
db.execute("create table if not exists pool (pool text, key text, file text, canon text)")
db.execute("create table if not exists train (dir text, file text, pool text, pool_file text, how text)")
db.execute("create table if not exists done (dir text primary key, blocks int, matched int, t real)")
db.execute("create index if not exists pool_canon on pool (canon)")
rel = lambda p: os.path.relpath(p, HERE)
t0 = time.time()
with Pool(a.workers) as P:
    have = {p for (p,) in db.execute("select distinct pool from pool")}; jobs = []   # pools are added incrementally, by name
    if "s120" not in have:
        for f in glob.glob(os.path.join(HERE, "synthetic", "*", "*.json")) + glob.glob(os.path.join(HERE, "synthetic", "*", "_holdout", "*.json")):
            if os.path.basename(f).startswith("_"): continue
            jobs.append(("s120-holdout" if "/_holdout/" in f else "s120", f.split(os.sep)[-3 if "/_holdout/" in f else -2], f))
    roots = [("breadth", "synthetic-breadth"), ("breadth-deep100", "synthetic-breadth-deep100")]
    roots += [("s120-fresh", os.path.basename(x)) for x in sorted(glob.glob(os.path.join(HERE, "ours-fresh-*"))) if os.path.isdir(x)]
    roots += [(os.path.basename(x).replace("synthetic-", ""), os.path.basename(x)) for x in sorted(glob.glob(os.path.join(HERE, "synthetic-remix*"))) if os.path.isdir(x)]
    for pool, root in roots:
        if db.execute("select 1 from pool where file like ? limit 1", (root + "/%",)).fetchone(): continue
        pat = os.path.join(HERE, root, "**", "*.json") if pool == "s120-fresh" else os.path.join(HERE, root, "*", "*.json")   # fresh deliveries nest k<N>/ dirs
        jobs += [(pool, f.split(os.sep)[-2], f) for f in glob.glob(pat, recursive=True) if not os.path.basename(f).startswith("_")]
    if jobs:
        print(f"pools: {len(jobs)} blocks to hash", flush=True)
        meta = {f: (p, k) for p, k, f in jobs}; rows = []
        for f, h in P.imap_unordered(canon_file, [f for _, _, f in jobs], chunksize=256):
            p, k = meta[f]; rows.append((p, k, rel(f), h))
            if len(rows) % 50000 == 0: print(f"  pool {len(rows)} {time.time() - t0:.0f}s", flush=True)
        db.executemany("insert into pool values (?,?,?,?)", rows); db.commit()
    canon = {}
    for p, f, h in db.execute("select pool, file, canon from pool"):
        canon.setdefault(h, []).append((p, f))
    nvp = {}                                             # NVARC dir -> {pair hash: file}, built on demand

    def nv_dir(d):
        if d not in nvp:
            m = {}
            for f in glob.glob(os.path.join(NV, "nvarc_*", d, "*.json")):
                try:
                    for pr in json.load(open(f)): m.setdefault(pair_hash(pr["input"], pr["output"]), set()).add(os.path.relpath(f, NV))
                except Exception: pass
            nvp[d] = m
        return nvp[d]
    # hop 1 trained on a manifest of paths (pool files used directly, plus its own nvarc/ and real/ copies): its lineage IS the list
    man = os.path.join(HERE, "hop1-corpus", "manifest.txt")
    if os.path.exists(man) and (a.only is None or "hop1-corpus/manifest" in a.only) and not db.execute("select 1 from done where dir='hop1-corpus/manifest'").fetchone():
        out = []
        for p in (x.strip() for x in open(man) if x.strip()):
            q = os.path.relpath(p, HERE) if os.path.isabs(p) else p; parts = q.split(os.sep); b = parts[-1]
            if parts[0] == "synthetic": out.append(("hop1-corpus/manifest", b, "s120-holdout" if "_holdout" in parts else "s120", q, "manifest"))
            elif parts[0] in ("synthetic-breadth", "synthetic-breadth-deep100"): out.append(("hop1-corpus/manifest", b, parts[0].replace("synthetic-", ""), q, "manifest"))
            elif parts[0].startswith("synthetic-"): out.append(("hop1-corpus/manifest", b, parts[0].replace("synthetic-", ""), q, "manifest"))
            elif parts[0].startswith("ours-fresh-"): out.append(("hop1-corpus/manifest", b, "s120-fresh", q, "manifest"))
            elif parts[:2] == ["hop1-corpus", "nvarc"]:
                m = re.match(r"n[ft]_([0-9a-f]{8})_([0-9a-f]{8})_\d+\.json$", b); hit = glob.glob(os.path.join(NV, "nvarc_*", m.group(1), f"{m.group(1)}_{m.group(2)}.json")) if m else []
                out.append(("hop1-corpus/manifest", b, "nvarc", os.path.relpath(hit[0], NV) if hit else None, "name" if hit else "none"))
            elif parts[:2] == ["hop1-corpus", "real"]:
                m = re.match(r"(arc2|concept|mini)_(.+)_\d+\.json$", b); out.append(("hop1-corpus/manifest", b, "real-" + m.group(1) if m else None, m.group(2) if m else None, "name" if m else "none"))
            else: out.append(("hop1-corpus/manifest", b, None, q, "none"))
        db.executemany("insert into train values (?,?,?,?,?)", out); mt = sum(x[4] != "none" for x in out)
        db.execute("insert into done values (?,?,?,?)", ("hop1-corpus/manifest", len(out), mt, time.time())); db.commit()
        print(f"hop1-corpus/manifest: {len(out)} paths, matched {mt}", flush=True)
    for d in train_dirs():
        r = rel(d)
        if r in a.redo: db.execute("delete from train where dir=?", (r,)); db.execute("delete from done where dir=?", (r,))
        if a.only is not None and r not in a.only: continue
        if db.execute("select 1 from done where dir=?", (r,)).fetchone(): continue
        fs = sorted(glob.glob(os.path.join(d, "*.json"))); out = []; need = []
        for f in fs:
            b = os.path.basename(f)
            m = re.search(r"_nv-n[tf]-([0-9a-f]{8}_[0-9a-f]{8})_", b) or re.search(r"_nv-n[tf]-([^_]+_[^_]+)_\d+\.json$", b)
            if m:
                st = m.group(1); hit = glob.glob(os.path.join(NV, "nvarc_*", st.split("_")[0], st + ".json"))
                out.append((r, b, "nvarc", os.path.relpath(hit[0], NV) if hit else None, "name" if hit else "none")); continue
            m = re.search(r"_re-(arc2|concept|mini)-(.+?)(?:-(?:test|loo)\d+)?(?:-c\d+)?_\d+\.json$", b) or re.search(r"(?:^|_)(arc2)train_([0-9a-f]{8})(?:_c?\d+)?\.json$", b)
            if m: out.append((r, b, "real-" + m.group(1), m.group(2), "name")); continue
            m = re.search(r"(?:^|_)(?:nv_)?nvarc_([0-9a-f]{8})_\d+\.json$", b)
            if m:
                try:
                    blk = json.load(open(f)); mp = nv_dir(m.group(1)); sets = [mp.get(pair_hash(p["input"], p["output"]), set()) for p in blk["train"] + blk["test"]]
                    common = set.intersection(*sets) if sets else set()
                    out.append((r, b, "nvarc", sorted(common)[0] if common else None, "pairs" if common else "none"))
                except Exception: out.append((r, b, "nvarc", None, "none"))
                continue
            need.append(f)
        for f, h in P.imap_unordered(canon_file, need, chunksize=128):
            hit = canon.get(h)
            out.append((r, os.path.basename(f), hit[0][0] if hit else None, hit[0][1] if hit else None, "canon" if hit else "none"))
        db.executemany("insert into train values (?,?,?,?,?)", out)
        mt = sum(x[4] != "none" for x in out)
        db.execute("insert into done values (?,?,?,?)", (r, len(out), mt, time.time())); db.commit()
        print(f"{r}: {len(out)} blocks, matched {mt} ({mt / max(1, len(out)):.1%}) | {time.time() - t0:.0f}s", flush=True)
print("done", f"{time.time() - t0:.0f}s ->", rel(DB))
