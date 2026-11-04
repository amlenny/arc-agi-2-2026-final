#!/usr/bin/env python3
# crucible-screen-corpus.py -- content-level contamination screen for an authored corpus.
#
#   crucible-screen-corpus.py [--corpus corpus-midband] [--split evaluation training]
#
# Hashes every (input, output) grid pair in the corpus and every pair in the named ARC splits,
# and reports any literal collision. A generator that happens to re-emit a benchmark pair would
# put scoring data into the training mix without anyone noticing; this is the check that says it
# did not. Reports counts only -- it never writes.

import argparse, hashlib, json, os, sys
from collections import Counter

CR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "crucible", "data-arc-agi-2", "data")
KAG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "crucible", "data-kaggle")
DIAG = os.path.dirname(os.path.abspath(__file__))


def h(pair):
    return hashlib.sha1(json.dumps(pair, separators=(",", ":")).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="corpus-midband")
    # ARC-1 EVALUATION IS SCREENED BY DEFAULT AND IS READ-ONLY. It is the only external instrument
    # the lineage has never trained on, and it stays that way only if nothing can emit one of its
    # grids -- including by accident. Invented mechanics and composed mechanics are not derived from
    # any task, so they can collide with a grid nobody read. The public 120 stopped refereeing the
    # moment the corpus was derived from them; this screen is what prevents the same mechanism here.
    ap.add_argument("--split", nargs="*",
                    default=["kaggle-evaluation", "evaluation", "training", "arc1-evaluation"])
    a = ap.parse_args()

    # Split name -> directory. CR points at the ARC-2 data root, so ARC-1 needs its own absolute
    # path; it is named explicitly so a typo cannot silently screen nothing.
    _ARC1 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "crucible", "data-sources", "arc-agi-1", "data")
    SPLIT_DIR = {"arc1-evaluation": os.path.join(_ARC1, "evaluation"),
                 "arc1-training": os.path.join(_ARC1, "training")}

    bench = {}
    for sp in a.split:
        if sp == "kaggle-evaluation":
            # THE SCORED SET IS NOT THE REPO COPY. crucible/data-arc-agi-2 differs from the
            # Kaggle evaluation file on six tasks: 4a21e3da, abc82100, b6f77b65, f560132c and
            # faa9f03d each hold FEWER test pairs in the repo, and d8e07eb2 differs in content.
            # Six scored pairs therefore existed in no split this screen read, so a corpus block
            # duplicating one of them would have passed. The repo copy stays screened as well --
            # a pair it holds and Kaggle does not is still a pair we must not emit.
            ch = json.load(open(os.path.join(KAG, "arc-agi_evaluation_challenges.json")))
            so = json.load(open(os.path.join(KAG, "arc-agi_evaluation_solutions.json")))
            n = 0
            for t in sorted(ch):
                for pr in ch[t].get("train", []):
                    bench[h([pr["input"], pr["output"]])] = (sp, t); n += 1
                for i, pr in enumerate(ch[t].get("test", [])):
                    outs = so.get(t) or []
                    if i < len(outs):
                        bench[h([pr["input"], outs[i]])] = (sp, t); n += 1
            print("  %-16s %5d pairs" % (sp, n))
            continue
        d = SPLIT_DIR.get(sp, os.path.join(CR, sp))
        if not os.path.isdir(d):
            print("  missing split:", d); sys.exit(2)
        n = 0
        for fn in sorted(os.listdir(d)):
            t = json.load(open(os.path.join(d, fn)))
            for k in ("train", "test"):
                for p in t.get(k, []):
                    if "output" in p:
                        bench[h([p["input"], p["output"]])] = (sp, fn[:-5]); n += 1
        print("  %-16s %5d pairs" % (sp, n))

    # Accept an absolute path as given, and resolve a bare name under DIAG. Resolving everything
    # under DIAG meant a corpus built anywhere else raised FileNotFoundError, which the caller
    # reported as a benchmark collision -- a missing directory read as contaminated data.
    root = a.corpus if os.path.isabs(a.corpus) else os.path.join(DIAG, a.corpus)
    if not os.path.isdir(root):
        sys.exit(f"FAIL: no corpus directory at {root!r}. This is a path error, NOT a collision.")
    # WALK, don't listdir. The corpus is one directory per source task holding one problem per
    # file; a flat listdir over the root sees only directories and screens nothing, which reads as
    # a clean corpus. Files are counted under the directory that holds them so the per-task totals
    # below stay per-task.
    #
    # Two file shapes are accepted: a single problem, {train, test}, and a flat map of
    # id -> problem. The band90 lane still writes the flat map, and a screener that understood only
    # one of the two would silently skip the other lane's corpus rather than fail.
    hits, tot = [], Counter()
    for dirpath, _dirnames, names in os.walk(root):
        label = os.path.relpath(dirpath, root)
        for fn in sorted(names):
            if not fn.endswith(".json") or fn.startswith("_"):
                continue   # _MANIFEST / _meta are metadata, not tasks
            d = json.load(open(os.path.join(dirpath, fn)))
            if isinstance(d, dict) and d.get("train"):
                blocks = {fn[:-5]: d}
            elif isinstance(d, dict):
                blocks = {k: v for k, v in d.items() if isinstance(v, dict) and v.get("train")}
            else:
                sys.exit(f"FAIL: {os.path.join(dirpath, fn)} is neither a problem nor a map of "
                         f"problems. Refusing to report a corpus clean that it could not read.")
            key = fn if label == "." else label
            for tid, t in blocks.items():
                for k in ("train", "test"):
                    for p in t.get(k, []):
                        tot[key] += 1
                        hit = bench.get(h([p["input"], p["output"]]))
                        if hit:
                            hits.append((tid, hit))
    if not tot:
        sys.exit(f"FAIL: {root} holds no readable problems. This is a path or layout error, "
                 f"NOT a clean corpus.")
    print()
    for fn in sorted(tot):
        print("  %-28s %5d pairs" % (fn, tot[fn]))
    print("\n  TOTAL %d pairs screened, %d literal collisions with %s"
          % (sum(tot.values()), len(hits), "+".join(a.split)))
    for tid, hit in hits[:20]:
        print("     ", tid, "==", hit)
    sys.exit(1 if hits else 0)


main()
