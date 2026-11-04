#!/usr/bin/env python
# corpus-replay.py — replay every banked block against its source task's CURRENT admitted
# generator. Report by default; --fix sets the rule-false ones aside.
#
# WHY THIS EXISTS. build-neighborhoods.py verifies at WRITE time and is additive-idempotent, so a
# block is checked once, on the day it is created, and never again. That is not enough on its own:
# when a GENERATOR is corrected afterwards, every block banked under the old rule silently becomes
# rule-false, and re-running the builder does nothing because the slots are already full. It has
# happened twice in this tree — three skeletons that were wrong at write time and later rewritten,
# and 247ef758, whose generator's motif ORDER was corrected on 2026-09-01 and which took 314
# already-banked blocks down with it across three corpora.
#
# So the write-time gate answers "was this right when written" and this answers "is this right
# NOW". A corpus must pass this before anything trains on it or reads from it. Nothing here is
# deleted: rejected blocks are written out under rejected-<stamp>/ with their source and reason.
import argparse, glob, importlib.util, json, os, re, sys, time

_TASKID = re.compile(r"^[0-9a-f]{8}$")


def source_of(base):
    """The task id in a batch filename, or None if there isn't one.

    These trees carry several naming shapes and the old parse — split("_", 1)[1][:-5] — only
    handled the first:

        nbrB_62593bfd.json              -> 62593bfd
        nbrB_62593bfd_timid_025.json    -> 62593bfd   (one-block-per-file form)
        midband_13e47133.json           -> 13e47133
        motion_corner_pull_320000.json  -> None       (carries no task id; not from this corpus)

    On the second shape it produced "62593bfd_timid_025", which matches no file in generators/, so
    1,300 blocks that had perfectly good verifiers reported UNGATED. A task id is eight hex
    characters and no other segment in these names is, so scanning segments is unambiguous.
    """
    stem = base[:-5] if base.endswith(".json") else base
    for seg in stem.split("_"):
        if _TASKID.match(seg):
            return seg
    return None

HERE = os.path.dirname(os.path.abspath(__file__))
_cache = {}


def verifier(source):
    """(kind, fn) or None. Mirrors build-neighborhoods.verifier — the two must agree on which
    contract a source uses, or a block admitted at write time reads as ungated at replay time."""
    if source not in _cache:
        path = os.path.join(HERE, "generators", f"{source}.py")
        found = None
        if os.path.isfile(path):
            sp = importlib.util.spec_from_file_location(f"g_{source}", path)
            mod = importlib.util.module_from_spec(sp)
            sp.loader.exec_module(mod)
            # verify_block sees the WHOLE block. Some mechanics carry their convention at block
            # level rather than pair level -- a colour role that the demos teach and the test then
            # relies on. Asking a bare per-pair solver to recover that from one grid asks the wrong
            # question and reports rule-false on data whose answer the demos do determine.
            if getattr(mod, "verify_block", None):
                found = ("verify_block", mod.verify_block)
            elif getattr(mod, "verify", None):
                found = ("verify", mod.verify)
            elif getattr(mod, "transform", None):
                found = ("transform", mod.transform)
        _cache[source] = found
    return _cache[source]


def block_ok(found, blk):
    kind, fn = found
    if kind == "verify_block":
        try:
            return bool(fn(blk))
        except Exception:
            return False
    for p in blk.get("train", []) + blk.get("test", []):
        try:
            ok = (fn(p["input"], p["output"]) if kind == "verify"
                  else fn([r[:] for r in p["input"]]) == p["output"])
            if not ok:
                return False
        except Exception:
            return False
    return True


def sweep(tree, fix, stamp, only=None):
    """only: a set of task ids to act on, or None for every source in the tree.

    --fix is whole-tree by default, and that is wrong when the rule-false blocks in one tree come
    from two different causes. In corpus-hard they do: 247ef758's 86 are a settled generator
    correction, while 3dc255db / 4a21e3da / 5961cc34 fail 100% of their banked blocks against a
    generator that is itself under adjudication. Setting the second group aside would decide that
    question by deleting one side of it, so the fix has to be scopeable to the settled source.
    """
    # RECURSIVE. The midband corpus is one directory per source task holding one problem per
    # file, so a flat *.json glob over its root matches nothing and reports a clean sweep of zero
    # blocks. source_of already handles the one-block-per-file name, which is what those files use.
    files = sorted(glob.glob(os.path.join(tree, "**", "*.json"), recursive=True))
    tot = ver = bad = ung = 0
    for f in files:
        base = os.path.basename(f)
        if base.startswith("_"):
            continue
        source = source_of(base)
        if only is not None and source not in only:
            continue
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if not isinstance(d, dict) or not d:
            continue
        # TWO FILE SHAPES LIVE IN THESE TREES and assuming one of them crashes on the other.
        #   {block_id: {train, test}}   the nbrB/midband batch form
        #   {train, test}               a SINGLE task per file, which every motion_* file is
        # Iterating the second yields ("train", [...]) and hands a list to the block checker.
        if "train" in d and isinstance(d.get("train"), list):
            d = {os.path.basename(f)[:-5]: d}
        # And drop sibling metadata keys. build-neighborhoods.py's own comment warns that a
        # top-level "_meta" sits in the same map as the tasks and crashes any reader that reaches
        # for ["train"]; 100 files in corpus-mixed carry one anyway.
        d = {k: v for k, v in d.items() if not k.startswith("_")}
        if not d:
            continue
        fn = verifier(source) if source else None
        if fn is None:
            ung += len(d)
            tot += len(d)
            # SAY WHICH KIND OF UNGATED. One string for three conditions is how corpus-midband got
            # read as an unverified corpus when its verifiers merely live elsewhere.
            why = ("no task id in filename" if not source
                   else f"no verifier for {source} in generators/")
            print(f"  {base:<30} {len(d):>5} blocks   UNGATED ({why})")
            continue
        keep, drop = {}, {}
        for k, blk in d.items():
            (keep if block_ok(fn, blk) else drop)[k] = blk
        tot += len(d)
        ver += len(keep)
        bad += len(drop)
        flag = "" if not drop else f"   <-- {len(drop)} RULE-FALSE"
        print(f"  {base:<30} {len(d):>5} blocks   verified {len(keep):>5}{flag}")
        if drop and fix:
            out = os.path.join(HERE, f"rejected-{stamp}")
            os.makedirs(out, exist_ok=True)
            with open(os.path.join(out, f"{tree.strip('/').replace('/', '_')}__{base}"), "w") as fh:
                json.dump(drop, fh)
            with open(f, "w") as fh:
                json.dump(keep, fh)
    return tot, ver, bad, ung



# ---- DIVERSITY AND SELF-MATCH ---------------------------------------------------------------
# Everything above answers "is every block rule-true". Neither of the two failures below is a rule
# failure, and neither is visible to any of it:
#
#   a batch can be 100% verified and still be a handful of shapes wearing many colourings
#   a batch can be 100% verified, pass a byte-level contamination screen, and still be canonically
#   IDENTICAL to the very task it was derived from
#
# 2d0172a1 was both: 800 grids collapsed to 16 distinct forms, and 45% of them matched its own
# source task once colour and orientation were normalised away. neighborhood-split.json says why
# in its own screen_caveat — "a contamination screen hashes grids and detects COPIED content. It
# cannot detect DERIVED content." A hash cannot; canonicalisation can.
DATA = os.path.join(os.path.dirname(HERE), "crucible", "data-kaggle")
_own = {}


def _relabel(g):
    """Colours renumbered by order of first appearance, so palette choice stops mattering."""
    m, nxt, out = {}, 0, []
    for row in g:
        r2 = []
        for v in row:
            if v not in m:
                m[v] = nxt
                nxt += 1
            r2.append(m[v])
        out.append(tuple(r2))
    return tuple(out)


def canon(g):
    """Smallest colour-anonymous form over all eight dihedral views."""
    cur, best = [list(r) for r in g], None
    for _ in range(4):
        for form in (cur, [r[::-1] for r in cur]):
            n = _relabel(form)
            if best is None or n < best:
                best = n
        cur = [list(r) for r in zip(*cur[::-1])]
    return best


def source_forms(task):
    """(grid forms, PAIR forms) of the source task, answers included.

    The pair set is the one that decides anything. A grid-level match says an answer SHAPE recurs,
    and for a task whose answer is a canonical rendering — nested rectangles, say — every correct
    corpus reproduces those shapes; demanding otherwise demands the corpus avoid correct answers.
    A PAIR match says the model was shown the source's own question WITH its own answer, and that
    is what makes a later measurement of the source uninterpretable.
    """
    if task in _own:
        return _own[task]
    grids, pairs = set(), set()
    try:
        ch = json.load(open(os.path.join(DATA, "arc-agi_evaluation_challenges.json")))
        sol = json.load(open(os.path.join(DATA, "arc-agi_evaluation_solutions.json")))
        for pr in ch.get(task, {}).get("train", []):
            gi, go = canon(pr["input"]), canon(pr["output"])
            grids |= {gi, go}
            pairs.add((gi, go))
        for i, pr in enumerate(ch.get(task, {}).get("test", [])):
            gi = canon(pr["input"])
            grids.add(gi)
            if task in sol and i < len(sol[task]):
                go = canon(sol[task][i])
                grids.add(go)
                pairs.add((gi, go))
    except Exception:
        pass
    _own[task] = (grids, pairs)
    return _own[task]


def shape_report(tree):
    """Per-source diversity and self-match. Thresholds are advisory except self-match, which is
    not — a block canonically equal to its own source makes any measurement of that source
    uninterpretable, because the model will have been trained on the answer."""
    bad = 0
    print(f"\n== {tree} — DIVERSITY / SELF-MATCH")
    print(f"  {'source':<12}{'in forms':>10}{'out forms':>11}{'dims':>6}"
          f"{'grid s-m':>10}{'PAIR s-m':>10}")
    for f in sorted(glob.glob(os.path.join(tree, "**", "*.json"), recursive=True)):
        base = os.path.basename(f)
        if base.startswith("_"):
            continue
        task = source_of(base)
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if "train" in d and isinstance(d.get("train"), list):
            d = {base[:-5]: d}
        prs = [(p["input"], p["output"]) for blk in d.values() if isinstance(blk, dict)
               for p in blk.get("train", []) + blk.get("test", [])]
        if not prs:
            continue
        sg, sp = source_forms(task) if task else (set(), set())
        ci = [canon(a) for a, _ in prs]
        co = [canon(b) for _, b in prs]
        dims = {(len(g), len(g[0])) for pr in prs for g in pr}
        gm = sum(1 for f in ci + co if f in sg)
        pm = sum(1 for f in zip(ci, co) if f in sp)
        ri, ro = len(set(ci)) / len(ci), len(set(co)) / len(co)
        note = ""
        if pm:
            note = "   <== PAIR SELF-MATCH: must not train"
            bad += 1
        elif ri < 0.9:
            note = "   <== thin inputs"
        print(f"  {task or base:<12}{ri:>10.3f}{ro:>11.3f}{len(dims):>6}{gm:>10}{pm:>10}{note}")
    return bad

def main():
    ap = argparse.ArgumentParser(description="Replay banked blocks against current generators.")
    ap.add_argument("trees", nargs="+")
    ap.add_argument("--fix", action="store_true",
                    help="move rule-false blocks out to rejected-<stamp>/ and rewrite the file")
    ap.add_argument("--stamp", default="", help="suffix for the rejected directory")
    ap.add_argument("--shape", action="store_true",
                    help="also report per-source diversity and self-match against the source task")
    ap.add_argument("--only", default="", metavar="ID[,ID...]",
                    help="restrict the sweep to these task ids; everything else is skipped "
                         "entirely, not counted")
    a = ap.parse_args()
    stamp = a.stamp or "replay"
    only = {x.strip() for x in a.only.split(",") if x.strip()} or None
    grand = [0, 0, 0, 0]
    for tree in a.trees:
        if "preserved" in tree:
            print(f"== {tree} — SKIPPED. The preserved tree is the record of what actually "
                  f"trained, bad blocks included; correcting it would destroy the evidence.")
            continue
        print(f"== {tree}" + (f"   [only: {', '.join(sorted(only))}]" if only else ""))
        t = sweep(tree, a.fix, stamp, only)
        for i in range(4):
            grand[i] += t[i]
    print(f"\n  TOTAL {grand[0]} blocks   verified {grand[1]}   rule-false {grand[2]}   "
          f"ungated {grand[3]}")
    selfmatch = 0
    if a.shape:
        for tree in a.trees:
            if "preserved" not in tree:
                selfmatch += shape_report(tree)
        if selfmatch:
            print(f"\n  {selfmatch} source(s) CANONICALLY MATCH THEIR OWN SOURCE TASK. Rule-true is "
                  f"not enough: training on these makes any measurement of those sources "
                  f"uninterpretable.")
    if only:
        print(f"  SCOPED RUN — these counts cover only {', '.join(sorted(only))}, "
              f"not the whole tree. Re-run without --only for the tree verdict.")
    if grand[2] and not a.fix:
        print("  RULE-FALSE BLOCKS PRESENT — this corpus must not be consumed. Re-run with --fix.")
    sys.exit(1 if (grand[2] or selfmatch) else 0)


if __name__ == "__main__":
    main()
