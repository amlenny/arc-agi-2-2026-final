#!/usr/bin/env python3
# crucible-build-midband.py — emit the middle-band corpus from verified skeletons.
#
#   crucible-build-midband.py [--per-grade 25] [--out synthetic] [--only 0934a4d8,13e47133]
#
# ONE DIRECTORY PER SOURCE TASK, ONE PROBLEM PER FILE:
#
#     synthetic/0934a4d8/midband_0934a4d8_timid_000.json
#     synthetic/0934a4d8/midband_0934a4d8_timid_001.json
#     synthetic/0934a4d8/_meta.json
#
# The count of a task IS its directory, so asking for 400 of one task and 40 of another is two
# runs of --only rather than a knob that applies to every source at once. --per-grade is a TARGET
# per grade per task: a task already at the target is left alone, a task below it is topped up
# with blocks numbered above the highest index present. Lowering the target does nothing; this
# builder never removes a block it did not just write.
#
# Task ids are unique across the whole 120, so the band90 lane writes its own task directories
# into the same pool. There is no midband/ or band90/ level -- band is a property of a task,
# recorded in the split JSONs, not a directory.
#
# A CHECK THAT BUILDS WHAT THE CODE NEEDS PROVES NOTHING. draw_roles was verified by exec'ing
# this file with `mb` supplied in the namespace, so it resolved a global the module does not
# have and the check passed on the strength of the harness rather than the code. It raised
# NameError on the first block of the first real build. Verify a module-level function by
# importing this file the way python imports it and calling the function, with nothing supplied
# that a caller would not supply.
#
# TWO GATES BEFORE ANYTHING IS WRITTEN, both refusals rather than warnings:
#   1. every skeleton's solver must reproduce EVERY demo of its source task. A generator is a claim
#      about what the source does; a wrong claim trains the model confidently on a fiction.
#   2. every emitted instance is round-tripped through that same solver and discarded unless it
#      comes back exactly. Up to a third of raw instances are not uniquely recoverable — the answer
#      is not derivable from the input — and those teach guessing.
#
# FORMAT: each file holds ONE problem, {train, test}, 3 demo pairs + 1 test. The filename is the
# instance id, <lane>_<source>_<grade>_<nnn>.json, so a block stays self-identifying after it is
# copied into a stage directory and a training run can be cited as a range of ids.

import argparse
import hashlib
sys_path_ops = __import__('os').path.dirname(__import__('os').path.abspath(__file__))
__import__('sys').path.insert(0, sys_path_ops)
from crucible_pool import closure_sha
import importlib.util
import inspect
import itertools
import json
import os
import random
import sys

DIAG = os.path.dirname(os.path.abspath(__file__))
CR = os.path.join(os.path.dirname(DIAG), "crucible")


def sib(stem, path):
    sp = importlib.util.spec_from_file_location(stem, path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def crop(g):
    """Bounding box of the non-modal colour. Kills translation and padding.

    canon() folds colour and the eight dihedral views but not position: a motif drawn two rows
    lower is a different grid to it. Measured across the pool, translation roughly DOUBLED the
    number of held-out inputs that were already in training -- 197 canonical hits became 358 once
    position was normalised away, and one task went from 46 of 64 to 64 of 64.
    """
    n = {}
    for row in g:
        for v in row:
            n[v] = n.get(v, 0) + 1
    bg = max(n, key=n.get)
    cells = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v != bg]
    if not cells:
        return g
    r0, r1 = min(r for r, _ in cells), max(r for r, _ in cells)
    c0, c1 = min(c for _, c in cells), max(c for _, c in cells)
    return [row[c0:c1 + 1] for row in g[r0:r1 + 1]]


def draw_roles(mb, name, rng):
    """The role palette for one block. Default excludes 0, because a role drawn as 0 on a
    generator whose source never uses 0 as a role teaches a convention the source does not have.

    A skeleton whose SOURCE keys on 0 says so in midband.ROLE_PALETTES[name]: a callable taking
    rng and returning the role tuple. Scoped per skeleton on purpose -- quadrant_roles (f931b4a8)
    has EMPTY = 0 in 7 of 7 source pairs and a pool that never draws 0 fails the floor, while
    wall_snake's source roles are 3, 2, 1 and 0 there would be a widening it has never had.
    No entry, no change.
    """
    pal = getattr(mb, "ROLE_PALETTES", {}).get(name)
    if pal:
        return tuple(pal(rng))
    return tuple(rng.sample([1, 2, 3, 4, 6, 7, 8, 9], 4))


def demos_pin_roles(blk, solve, nroles):
    """Do this block's demos determine its colour roles, or is the answer a guess?

    emit_verified checks each pair against the roles the GENERATOR drew, which proves the pair is
    recoverable given private information. It cannot see that a block's three demos might all come
    out degenerate -- every bar skipped, say, leaving two colours on the grid -- so nothing in the
    demos says which colour plays which part. Measured on one such block: 30 role assignments fit
    all three demos and none reproduced the test.

    Same test the exported block verifier applies, run at admission so the block is never written.
    """
    demos = blk.get("train", [])
    tests = [p for p in blk.get("test", []) if p.get("output")]
    if not demos or not tests:
        return False
    pal = sorted({v for p in demos + tests for g in (p["input"], p["output"]) for row in g for v in row})

    def fits(pairs, roles):
        for p in pairs:
            try:
                if solve([r[:] for r in p["input"]], *roles) != p["output"]:
                    return False
            except Exception:
                return False
        return True

    ok = [c for c in itertools.permutations(pal, nroles) if fits(demos, c)]
    return bool(ok) and all(fits(tests, c) for c in ok)


def crop_is_informative(blocks, canon):
    """Does cropping preserve what varies in this mechanic, or delete it?

    Crop-normalisation kills translation, which is what makes it worth having: a motif drawn two
    rows lower is the same problem. But for a mechanic where POSITION is the content -- a bloom
    whose answer depends on how close its centre sits to each edge -- the bounding box is the same
    shape every time and cropping collapses the whole task to a handful of forms. Measured on
    da515329: 1,200 inputs, 691 canonical forms, FOUR crop-canonical forms. Gating on that rejects
    every possible holdout, not because the generator is narrow but because the key is blind.

    So it is decided per task from the data rather than assumed: if cropping collapses the space to
    under a fifth of what canon alone distinguishes, it is destroying signal and is not used here.

    THE FIFTH IS NOT A TUNED NUMBER. Measured across all 57 tasks in the pool, the crop/canon ratio
    is bimodal with nothing between 0.02 and 0.61: da515329 at 0.01 and 8b7bacbf at 0.02, then
    cb2d8a2c at 0.61 and everything else 0.89-1.00. Any cut in [0.05, 0.50] selects the same two
    tasks, so this sits in a gap thirty times wider than the region it has to discriminate.
    """
    c, k = set(), set()
    for b in blocks:
        for p in b.get("train", []) + b.get("test", []):
            g = p["input"]
            c.add(json.dumps(canon(g), separators=(",", ":")))
            k.add(json.dumps(canon(crop(g)), separators=(",", ":")))
    return len(k) >= 0.2 * max(len(c), 1), len(c), len(k)


def input_keys(task, canon, use_crop=True):
    """Every identity a block's INPUTS carry: canonical, and canonical after cropping.

    PAIR LEVEL, NOT BLOCK LEVEL. A block key over the joint set of four inputs reports a block as
    novel when only one of its inputs is new and the other three are already trained on -- measured,
    18 of 57 tasks leaked that way while every block-level check read clean. The model trains on
    individual demonstration pairs, so a repeated pair is a repeated problem however novel the
    block containing it looks.
    """
    ks = set()
    for p in task.get("train", []) + task.get("test", []):
        g = p["input"]
        ks.add(json.dumps(canon(g), separators=(",", ":")))
        if use_crop:
            ks.add("crop:" + json.dumps(canon(crop(g)), separators=(",", ":")))
    return ks


def canon_key(task, canon):
    """Identity of a block up to colour relabel and orientation.

    Byte-equality is too weak a distinctness test. A block whose inputs are a recolouring or a
    rotation of another block's is the same problem shown twice, and the model trains under colour
    augmentation anyway, so the exact-hash gate lets a duplicate through that the training run
    cannot tell apart. canon() is the smallest colour-anonymous form over the eight dihedral views;
    the key is taken over the block's INPUTS, since two blocks posing the same questions are the
    same block whatever the answers look like.
    """
    ins = sorted(json.dumps(canon(p["input"]), separators=(",", ":"))
                 for p in task.get("train", []) + task.get("test", []))
    return hashlib.sha256("|".join(ins).encode()).hexdigest()


def load_canon():
    """corpus-replay.py's canon(), so the builder and the sweep share one definition."""
    sp = importlib.util.spec_from_file_location("cr", os.path.join(DIAG, "corpus-replay.py"))
    m = importlib.util.module_from_spec(sp)
    try:
        sp.loader.exec_module(m)
    except SystemExit:
        pass
    return m.canon


def sha_of(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


SHAS_V2 = {}   # task id -> closure sha for this run, filled in main()


def skeleton_sha(*fns):
    """sha256 over the source text of the functions that actually build a task's instances.

    NOT the sha of midband.py. A whole-file sha says "the file was in this state", which is not a
    fact about the blocks in one task directory -- adding a 24th skeleton would invalidate the 23
    directories whose builders did not change a line. The function bodies are the narrower and
    more informative fact: this directory was built by these functions.

    Both the generator and the solver go in. The solver is a gate, not a bystander: it decides
    which draws are admitted, so changing it changes the population even with the generator fixed.
    """
    src = "".join(inspect.getsource(f) for f in fns)
    return hashlib.sha256(src.encode()).hexdigest()


def read_task_dir(d):
    """grade -> sorted instance ids already present in one task's directory."""
    have = {}
    if not os.path.isdir(d):
        return have
    for f in sorted(os.listdir(d)):
        if not f.endswith(".json") or f.startswith("_"):
            continue
        have.setdefault(f[:-5].split("_")[-2], []).append(f[:-5])
    return have


def pair_hash(pair):
    """Content hash of ONE pair, so a demonstration and a scored question are comparable."""
    return hashlib.sha256(json.dumps([pair["input"], pair["output"]], sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def banked_pairs(d0):
    """Every scored pair and every demonstration already on disk for this task, main AND holdout.

    A DEMO-LEAK is one block's scored question appearing as a worked example in another block of
    the same task: the answer is shown, solved, somewhere the model trains on. The block-level
    canonical key cannot see it -- the two blocks differ everywhere else -- so the pairs are
    tracked by side. Eleven of these stood corpus-wide, all midband, at one or two per task.
    """
    tests, demos = set(), set()
    for d in (d0, os.path.join(d0, "_holdout")):
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.endswith(".json") and not f.startswith("_"):
                b = json.load(open(os.path.join(d, f)))
                tests.update(pair_hash(q) for q in b.get("test", []))
                demos.update(pair_hash(q) for q in b.get("train", []))
    return tests, demos


def demo_leak(blk, tests, demos):
    """Would banking this block show a banked question's answer, or score a banked example?"""
    return (any(pair_hash(q) in demos for q in blk["test"])
            or any(pair_hash(q) in tests for q in blk["train"]))


def bank_pairs(blk, tests, demos):
    tests.update(pair_hash(q) for q in blk["test"])
    demos.update(pair_hash(q) for q in blk["train"])



def legal_block(blk):
    """Every grid 1-30 a side and integers 0-9, no all-zero grid: what the format can carry and the
    model can be asked. a32d8b75 drew 753 pairs wider than 30 on 10-03 and nothing in this builder
    refused them; the fresh-blocks screen did."""
    for p in blk.get("train", []) + blk.get("test", []):
        for g in (p.get("input"), p.get("output")):
            if not (isinstance(g, list) and 1 <= len(g) <= 30 and all(isinstance(r, list) and len(r) == len(g[0])
                    and 1 <= len(r) <= 30 and all(isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 9 for v in r) for r in g)):
                return False
            if all(v == 0 for r in g for v in r):
                return False
    return True

def next_index(ids):
    """One above the highest trailing index present, so a top-up never reuses a filename."""
    return max((int(i.split("_")[-1]) for i in ids), default=-1) + 1


def check_provenance(out, wanted, file_sha):
    """Refuse, BEFORE anything is written, to top up a task directory built by a different rule.

    Runs over every selected task up front rather than per task at its own write step. Numbering
    appends above the highest index present, so a rebuild after a skeleton change does not
    overwrite the older blocks -- it sits down beside them. Discovering that on task 20 after
    nineteen directories have already been added to is discovering it too late.

    skeleton_sha refuses. builder_file_sha is reported and does not: it answers "what else was in
    the tree at the time", which is worth recording and is not a fact about these blocks.
    """
    mixed, drift = [], []
    for src, sk_sha in sorted(wanted.items()):
        d = os.path.join(out, src)
        if not os.path.isdir(d):
            continue
        blocks = [f for f in os.listdir(d) if f.endswith(".json") and not f.startswith("_")]
        if not blocks:
            continue
        mp = os.path.join(d, "_meta.json")
        if not os.path.exists(mp):
            mixed.append((src, len(blocks), "no _meta.json — existing blocks are unattributed"))
            continue
        m = json.load(open(mp))
        if m.get("skeleton_sha") != sk_sha or (m.get("skeleton_sha_v2") and m.get("skeleton_sha_v2") != SHAS_V2.get(src)):
            mixed.append((src, len(blocks),
                          f"existing blocks built by {str(m.get('skeleton_sha'))[:16]}, "
                          f"this run is {sk_sha[:16]}"))
        elif m.get("builder_file_sha") != file_sha:
            drift.append((src, str(m.get("builder_file_sha"))[:16]))
    for src, was in drift:
        print(f"  NOTE {src}: built when midband.py was {was}, now {file_sha[:16]}. Its own "
              f"skeleton is unchanged, so this run tops it up.")
    if mixed:
        print(f"\n  {len(mixed)} task director(ies) will hold blocks from more than one version "
              f"of their rule:")
        for src, n, why in mixed:
            print(f"     {src}  {n:4d} existing block(s)  {why}")
        print("  Proceeding. The new blocks are added beside the old ones and carry their own "
              "_skeleton_sha; _meta.json records every version present with its count.")


# WHAT A CARVE SPENT, RECORDED. A holdout that fell short and one that filled easily leave the
# same artefact unless the attempt is written down, and on eee78d87 -- 12 of 16 with timid at zero
# -- nothing on disk could say whether the space was exhausted, the budget was short, or a gate
# refused every candidate. band90 records budget, best fill and which slots exhausted, and that is
# what made an over-long build there checkable rather than a guess. This loop carves a GRADE at a
# time rather than a slot at a time, so it records per grade: what it spent, what it made and what
# it was asked for. Unlike the rest of _meta.json, which is rewritten from what is on disk, this
# describes THIS RUN's carve -- a directory topped up later keeps the record of the run that
# carved it.
HOLDOUT_BUDGET = 1500
HOLDOUT_TRIES = {}


def write_holdout(out, src, blocks, sk_sha):
    """One file per held-out problem under <out>/<src>/_holdout/.

    An underscore-prefixed SUBDIRECTORY of the task, not a sibling of the curriculum. Every reader
    that builds a curriculum filters on `.json` and skips names beginning with `_`, so a holdout
    here cannot reach a training set no matter which flags the trainer is given -- the safety is in
    the layout rather than in anyone remembering a rule. And because it belongs to the task it is
    the SAME yardstick for every run that ever touches that task, which is the whole point: a
    holdout carved per curriculum would differ run to run and the losses would not compare.
    """
    d = os.path.join(out, src, "_holdout")
    os.makedirs(d, exist_ok=True)
    for tid, t in blocks.items():
        json.dump(dict(t, _skeleton_sha=sk_sha), open(os.path.join(d, f"{tid}.json"), "w"))
    return len([f for f in os.listdir(d) if f.endswith(".json")])


def read_holdout(d):
    h = os.path.join(d, "_holdout")
    if not os.path.isdir(h):
        return {}
    out = {}
    for f in sorted(os.listdir(h)):
        if f.endswith(".json"):
            out.setdefault(f[:-5].split("_")[-2], []).append(f[:-5])
    return out


def write_blocks(out, src, name, blocks, sk_sha, file_sha, grades, holdout=0):
    """One file per problem under <out>/<src>/, plus that task's _meta.json.

    EVERY BLOCK CARRIES ITS OWN _skeleton_sha. A directory may hold blocks from more than one
    version of its rule -- corrected skeletons add beside the old blocks rather than replacing
    them, because data already trained on is not deleted to make room. Per-directory provenance
    cannot describe that; per-block provenance can.

    _meta.json is rewritten from what is on disk after the write, not from what this run emitted,
    so the counts describe the directory rather than the last top-up. skeleton_versions_present
    is the sha -> count map over every block actually present; blocks written before this field
    existed count as "unrecorded". The top-level skeleton_sha names the rule THIS run used and
    does NOT describe every block in the directory.
    """
    d = os.path.join(out, src)
    os.makedirs(d, exist_ok=True)
    for tid, t in blocks.items():
        json.dump(dict(t, _skeleton_sha=sk_sha), open(os.path.join(d, f"{tid}.json"), "w"))
    have = read_task_dir(d)
    versions = {}
    for ids in have.values():
        for iid in ids:
            b = json.load(open(os.path.join(d, iid + ".json")))
            k = b.get("_skeleton_sha") or "unrecorded"
            versions[k] = versions.get(k, 0) + 1
    hg = read_holdout(d)
    _tr = HOLDOUT_TRIES.get(src) or {}
    json.dump({"source": src, "skeleton": name, "lane": "midband",
               "skeleton_sha": sk_sha, "skeleton_sha_v2": SHAS_V2.get(src), "skeleton_versions_present": versions,
               "builder_file_sha": file_sha,
               "grades": {g: len(have.get(g, [])) for g in grades},
               "holdout": {"dir": "_holdout", "blocks": sum(len(v) for v in hg.values()),
                           # INTENDED beside BLOCKS, as band90 and mechanics record it: without it
                           # a carve that fell short reads identically to a complete one, and on
                           # 23 midband pools nothing could say which it was.
                           "intended": holdout * len(grades),
                           "grades": {g: len(hg.get(g, [])) for g in grades},
                           **({"tries": {
                               "budget_per_grade": HOLDOUT_BUDGET,
                               "spent": {g: r["spent"] for g, r in sorted(_tr.items())},
                               "grades_that_exhausted_the_budget": sorted(
                                   g for g, r in _tr.items()
                                   if r["made"] < r["asked"] and r["spent"] >= HOLDOUT_BUDGET)}}
                              if _tr else {})}},
              open(os.path.join(d, "_meta.json"), "w"), indent=1)
    return d, sum(len(v) for v in have.values())


def main():
    ap = argparse.ArgumentParser(description="emit the middle-band corpus")
    ap.add_argument("--per-grade", type=int, default=25,
                    help="TARGET blocks per grade per task, not an increment")
    ap.add_argument("--out", default=os.path.join(DIAG, "synthetic"))
    ap.add_argument("--holdout-per-grade", type=int, default=0,
                    help="blocks per grade written to <task>/_holdout/ and NEVER trained on. "
                         "Belongs to the TASK, not to a curriculum, so every run measures against "
                         "the same yardstick and per-task losses compare across runs.")
    ap.add_argument("--only", default="",
                    help="comma-separated source task ids; default is every eligible skeleton")
    ap.add_argument("--seed", type=int, default=4242)
    a = ap.parse_args()

    mb = sib("midband", os.path.join(DIAG, "midband.py"))
    sc = sib("crucible_score", os.path.join(CR, "crucible-score.py"))
    ev = sc.load_tasks(os.path.join(CR, "data-kaggle"), "evaluation")
    split = json.load(open(os.path.join(DIAG, "midband-split.json")))
    elig = set(split["ALL_DERIVATION_ELIGIBLE"])

    # GATE 1 — a skeleton that cannot reproduce its source does not get to emit.
    # A NAMED EXCEPTION, not a loosened gate. The gate stays "reproduce every demo"; anything
    # here had to be inspected, understood, and written down with the exact deviation. A skeleton
    # cannot slip through by merely scoring well.
    KNOWN_BAD_DEMO = {
        "align_anchor": ("581f7754 demo 1 places one 3x3 ring at columns 8-10 when every rule in "
                         "the task puts it at 9-11 — it moves a column sideways while all three "
                         "other objects in that same demo move purely along the alignment axis. "
                         "Demos 0 and 2 reproduce exactly. Renderer verified faithful (420 cells "
                         "checked against the JSON, 0 mismatches), so the anomaly is in the "
                         "benchmark data. The generator emits "
                         "the CLEAN rule."),
    }

    print("== GATE 1: skeletons must reproduce their source task ==")
    live = {}
    for name, (src, gen, solve) in mb.SKELETONS.items():
        if src not in elig:
            print(f"  {name:16s} REFUSED — {src} is not derivation-eligible")
            continue
        demos = ev[src]["train"]
        hit = sum(1 for p in demos if solve(p["input"]) == p["output"])
        ok = hit == len(demos)
        if not ok and name in KNOWN_BAD_DEMO and hit == len(demos) - 1:
            print(f"  {name:16s} {src}  {hit}/{len(demos)} demos  PASS (named exception)")
            print(f"       {KNOWN_BAD_DEMO[name][:96]}...")
            ok = True
        else:
            print(f"  {name:16s} {src}  {hit}/{len(demos)} demos  {'PASS' if ok else 'REFUSED'}")
        if ok:
            live[name] = (src, gen, solve)
    if not live:
        sys.exit("FAIL: no skeleton passed gate 1. Nothing written.")

    os.makedirs(a.out, exist_ok=True)
    file_sha = sha_of(os.path.join(DIAG, "midband.py"))

    # --only names TASKS, not skeletons, because the task id is what the pool is keyed by and what
    # the 120 are named by. An id that names nothing this builder owns is an error rather than a
    # silent no-op: asking for a task and getting an empty run looks like the task produced nothing.
    task_sk = {v[0]: (k, v) for k, v in live.items()}
    task_wt = {v[0]: (k, v) for k, v in getattr(mb, "TASK_SKELETONS", {}).items()}
    if a.only:
        want = [t.strip() for t in a.only.split(",") if t.strip()]
        unknown = [t for t in want if t not in task_sk and t not in task_wt]
        if unknown:
            sys.exit(f"FAIL: --only names {unknown}, which this builder does not own. It builds "
                     f"{sorted(set(task_sk) | set(task_wt))}")
        task_sk = {t: v for t, v in task_sk.items() if t in want}
        task_wt = {t: v for t, v in task_wt.items() if t in want}

    shas = {t: skeleton_sha(v[1][1], v[1][2]) for t, v in {**task_sk, **task_wt}.items()}
    # THE CLOSURE SHA BESIDE THE LEGACY ONE: covers every helper and data table the skeleton reaches.
    shas_v2 = {t: closure_sha(v[1][1], v[1][2]) for t, v in {**task_sk, **task_wt}.items()}
    SHAS_V2.update(shas_v2)
    check_provenance(a.out, shas, file_sha)

    rng = random.Random(a.seed)
    print()
    print("== GATE 2: every instance round-trips through its own solver ==")
    total = 0
    canon = load_canon()
    for src, (name, (_, gen, solve)) in sorted(task_sk.items()):
        d0 = os.path.join(a.out, src)
        have = read_task_dir(d0)
        # Seed from the blocks already present so a top-up cannot re-draw one of them recoloured.
        seen_canon = set()
        for ids in have.values():
            for iid in ids:
                seen_canon.add(canon_key(json.load(open(os.path.join(d0, iid + ".json"))), canon))
        # AND FROM THE HELD-OUT BLOCKS. The exclusion between the two sets ran ONE WAY: the holdout
        # is carved last and checked against the main pool, but read_task_dir() skips names
        # beginning with "_", so a later TOP-UP of the main pool never saw the holdout and could
        # draw straight into it. That is how a32d8b75 came to hold a block whose scored test pair
        # was train[1] of a main-pool block written nine and a half hours afterwards -- the holdout
        # was correct when carved and was invalidated later by a run that could not see it.
        # A holdout is only held out if BOTH directions exclude.
        _hd = os.path.join(d0, "_holdout")
        for ids in read_holdout(d0).values():
            for iid in ids:
                seen_canon.add(canon_key(json.load(open(os.path.join(_hd, iid + ".json"))), canon))
        seen_tests, seen_demos = banked_pairs(d0)
        tasks, short, added, recol, unpinned, gated, leaked = {}, 0, 0, 0, 0, 0, 0
        # Mechanics that draw colour ROLES per block need their demos to pin those roles. Read from
        # what the generator reports in `_roles`, not from the solver signature: nearly every solver
        # here carries an optional marker= it infers from the grid, which would call 22 of 23
        # sources role-carrying when two are.
        _probe = gen(rng, "mid")
        nroles = len(_probe.get("_roles") or ()) if _probe else 0
        for grade in mb.GRADES:
            # THE STRIKE BUDGET IS PER GRADE, NOT PER TASK (fixed 2026-09-15). `short` used to be
            # initialised once per task, so rejections in timid and mid spent the 200 strikes that
            # bold and size then did not have. GRADES runs timid, mid, bold, size, which means the
            # starved grades are always the REACH ones -- a gated 21897d95 build filled timid 150
            # and mid 150 and then gave bold 2 and size 1, and the pool still looked broadly full.
            # Any pool built with a non-trivial rejection rate carries this skew.
            short = 0
            n = next_index(have.get(grade, []))
            want = a.per_grade - len(have.get(grade, []))
            made = 0
            while made < want:
                # ONE PALETTE PER BLOCK. A problem and its own demos must share a colouring:
                # the convention is what the demos teach, so randomising per PAIR would leave a
                # block whose demos disagree and whose test is unanswerable. Generators that do
                # not take `roles` ignore this and draw their own colours per pair as before.
                roles = draw_roles(mb, name, rng)
                parts = [mb.emit_verified(gen, solve, rng, grade, roles=roles) for _ in range(4)]
                if any(p is None for p in parts):
                    short += 1
                    if short > 200:
                        break
                    continue
                blk = {"train": [{"input": p["input"], "output": p["output"]} for p in parts[:3]],
                       "test": [{"input": parts[3]["input"], "output": parts[3]["output"]}]}
                if nroles and not demos_pin_roles(blk, solve, nroles):
                    short += 1
                    unpinned += 1
                    if short > 200:
                        break
                    continue
                # A SKELETON MAY REFUSE ITS OWN BLOCK. Some mechanics can draw a test whose answer
                # turns on a branch none of the demos exercise -- 21897d95 drew 88 of 400 whose
                # rotation cue appears in no demo -- and such a block is unanswerable from what it
                # shows, however rule-true it is. The skeleton knows its own branches, so the test
                # lives beside it in midband.BLOCK_GATES rather than here. No entry, no change.
                gate = getattr(mb, "BLOCK_GATES", {}).get(name)
                if gate and not gate(blk):
                    short += 1
                    gated += 1
                    if short > 200:
                        break
                    continue
                ck = canon_key(blk, canon)
                if ck in seen_canon:
                    recol += 1          # a recolouring or rotation of a block already banked
                    short += 1
                    if short > 200:
                        break
                    continue
                if demo_leak(blk, seen_tests, seen_demos):
                    leaked += 1
                    short += 1
                    if short > 200:
                        break
                    continue
                if not legal_block(blk):
                    short += 1
                    continue
                seen_canon.add(ck)
                bank_pairs(blk, seen_tests, seen_demos)
                tasks[f"midband_{src}_{grade}_{n:03d}"] = blk
                n += 1
                made += 1
                added += 1
        # HELD-OUT BLOCKS ARE DRAWN LAST AND UNDER THE SAME CANONICAL GATE, seeded with every
        # training block already banked. A held-out problem that is a recolouring of a trained one
        # measures memorisation, not generalisation -- the point of the set is that the model has
        # never seen these questions in any orientation or palette.
        hold = {}
        if a.holdout_per_grade:
            # Seed from the TRAINING SET AS IT STANDS NOW, every input of every block. Drawn after
            # the training blocks in this same run, so a regeneration cannot leave the holdout
            # validated against a set that no longer exists.
            banked = [json.load(open(os.path.join(d0, iid + ".json")))
                      for ids in read_task_dir(d0).values() for iid in ids] + list(tasks.values())
            use_crop, ncanon, ncrop = crop_is_informative(banked, canon)
            if not use_crop:
                print(f"       {src}: crop-normalisation collapses {ncanon} canonical forms to "
                      f"{ncrop}; position is content here, so the crop key is not used")
            seen_inp = set()
            for b0 in banked:
                seen_inp |= input_keys(b0, canon, use_crop)
            hh = read_holdout(d0)
            for grade in mb.GRADES:
                n = next_index(hh.get(grade, []))
                want = a.holdout_per_grade - len(hh.get(grade, []))
                made, tries = 0, 0
                while made < want and tries < HOLDOUT_BUDGET:
                    tries += 1
                    roles = draw_roles(mb, name, rng)
                    parts = [mb.emit_verified(gen, solve, rng, grade, roles=roles) for _ in range(4)]
                    if any(p is None for p in parts):
                        continue
                    blk = {"train": [{"input": p["input"], "output": p["output"]} for p in parts[:3]],
                           "test": [{"input": parts[3]["input"], "output": parts[3]["output"]}]}
                    # THE YARDSTICK IS GATED TOO. The holdout draw used to skip
                    # BLOCK_GATES, so 21897d95's training pool was gated to zero traps while 3 of
                    # its 16 held-out blocks were unanswerable from their own demos. A held-out
                    # block that cannot be solved from what it shows measures nothing about the
                    # model, and it inflates that task's loss permanently, in every run that reads
                    # the same seal.
                    hgate = getattr(mb, "BLOCK_GATES", {}).get(name)
                    if hgate and not hgate(blk):
                        continue
                    ik = input_keys(blk, canon, use_crop)
                    if ik & seen_inp:
                        continue          # an input this block poses is already trained on
                    if demo_leak(blk, seen_tests, seen_demos) or not legal_block(blk):
                        continue
                    seen_inp |= ik
                    seen_canon.add(canon_key(blk, canon))
                    bank_pairs(blk, seen_tests, seen_demos)
                    hold[f"midband_{src}_{grade}_{n:03d}"] = blk
                    n += 1
                    made += 1
                HOLDOUT_TRIES.setdefault(src, {})[grade] = {
                    "spent": tries, "made": made, "asked": want}
        nh = write_holdout(a.out, src, hold, shas[src]) if a.holdout_per_grade else 0
        d, held = write_blocks(a.out, src, name, tasks, shas[src], file_sha, mb.GRADES, a.holdout_per_grade)
        total += held
        note = f"   (+{added} new)" if added and held != added else ""
        note += f"   [{nh} held out]" if nh else ""
        print(f"  {name:16s} {held:4d} blocks -> {src}/{note}"
              + (f"   ({short} rejected instance-sets" if short else "")
              + (f", {recol} recolourings" if short and recol else "")
              + (f", {unpinned} whose demos did not pin the roles" if short and unpinned else "")
              + (f", {gated} refused by the skeleton's own gate" if short and gated else "")
              + (")" if short else ""))

    # WHOLE-TASK skeletons emit {train,test} directly — their rule only exists across a task, not
    # within a pair, so they are gated by a task-level verifier instead of a per-instance solver.
    for src, (name, (_, gen, ver)) in sorted(task_wt.items()):
        if src not in elig:
            print(f"  {name:16s} REFUSED — {src} is not derivation-eligible")
            continue
        if not ver(ev[src]):
            print(f"  {name:16s} REFUSED — verifier fails on the SOURCE task {src}")
            continue
        have = read_task_dir(os.path.join(a.out, src))
        seen_tests, seen_demos = banked_pairs(os.path.join(a.out, src))
        tasks, tries = {}, 0
        # Grades are filled to the same target here as everywhere else. The earlier form counted
        # blocks against per_grade * len(GRADES) and assigned the grade by position, which reaches
        # the right total by a route that cannot be asked for one grade at a time.
        for grade in mb.GRADES:
            n = next_index(have.get(grade, []))
            want = a.per_grade - len(have.get(grade, []))
            made, tries = 0, 0
            while made < want and tries < 4000:
                tries += 1
                t = gen(rng, grade)
                # whole-task generators bypass emit_verified, so screen their pairs here too
                if t and any(mb.is_benchmark_pair(pr["input"], pr["output"])
                             for pr in t["train"] + t["test"]):
                    continue
                if t and ver(t) and legal_block(t) and not demo_leak(t, seen_tests, seen_demos):
                    bank_pairs(t, seen_tests, seen_demos)
                    tasks[f"midband_{src}_{grade}_{n:03d}"] = t
                    n += 1
                    made += 1
        # THE HOLDOUT IS DRAWN HERE TOO. This loop never carved one: 269e22fb's eight held-out
        # blocks were a one-off carve from spare pool blocks on 2026-09-11, so a rebuild of the
        # pool left the task with no yardstick at all. Same shape as the per-pair path above --
        # seeded from every banked input as it stands after this run's draws, gated by the same
        # verifier, and refusing any block that poses an input already trained on.
        hold = {}
        if a.holdout_per_grade:
            d0 = os.path.join(a.out, src)
            banked = [json.load(open(os.path.join(d0, iid + ".json")))
                      for ids in have.values() for iid in ids] + list(tasks.values())
            use_crop, ncanon, ncrop = crop_is_informative(banked, canon)
            seen_inp = set()
            for b0 in banked:
                seen_inp |= input_keys(b0, canon, use_crop)
            hh = read_holdout(d0)
            for grade in mb.GRADES:
                n = next_index(hh.get(grade, []))
                want = a.holdout_per_grade - len(hh.get(grade, []))
                made, tries = 0, 0
                while made < want and tries < HOLDOUT_BUDGET:
                    tries += 1
                    t = gen(rng, grade)
                    if not t or not ver(t):
                        continue
                    if any(mb.is_benchmark_pair(pr["input"], pr["output"]) for pr in t["train"] + t["test"]):
                        continue
                    ik = input_keys(t, canon, use_crop)
                    if ik & seen_inp or demo_leak(t, seen_tests, seen_demos) or not legal_block(t):
                        continue
                    seen_inp |= ik
                    bank_pairs(t, seen_tests, seen_demos)
                    hold[f"midband_{src}_{grade}_{n:03d}"] = t
                    n += 1
                    made += 1
                HOLDOUT_TRIES.setdefault(src, {})[grade] = {
                    "spent": tries, "made": made, "asked": want}
        nh = write_holdout(a.out, src, hold, shas[src]) if a.holdout_per_grade else 0
        d, held = write_blocks(a.out, src, name, tasks, shas[src], file_sha, mb.GRADES, a.holdout_per_grade)
        total += held
        print(f"  {name:16s} {held:4d} blocks -> {src}/   (whole-task, source-verified)"
              + (f"  holdout {nh}" if a.holdout_per_grade else ""))

    # The pool manifest is written per LANE, not per directory: this builder owns only its own
    # task directories, and the band90 lane writes its own into the same pool. Merging both into
    # one _MANIFEST.json would mean whichever ran last described the whole pool including tasks it
    # knows nothing about. Each task directory carries its own _meta.json; this is the lane index.
    man = {"lane": "MIDDLE BAND — unsolved tasks in no neighbourhood class",
           "layout": "one directory per source task, one problem per file",
           "sources": {**{n: v[0] for n, v in sorted(live.items())},
                       **{n: v[0] for n, v in sorted(getattr(mb, "TASK_SKELETONS", {}).items())}},
           "built_this_run": sorted(set(task_sk) | set(task_wt)),
           "per_grade_target": a.per_grade, "grades": mb.GRADES, "blocks": total,
           "builder_file_sha": file_sha,
           "skeleton_sha": shas,
           "known_bad_demos": KNOWN_BAD_DEMO,
           "gates": ["skeleton reproduces every source demo (or a NAMED exception below)",
                     "every emitted instance round-trips through its own solver"],
           "merge_note": ("task ids are unique across the 120, so lanes share this pool by "
                          "owning disjoint task directories."),
           "evaluation_rule": ("rules are derived FROM the public 120; no public task appears IN "
                               "the corpus -- gate 3 hashes every pair against evaluation+training. "
                               "Adapters are measured on held-out INSTANCES plus external sets.")}
    json.dump(man, open(os.path.join(a.out, "_MANIFEST-midband.json"), "w"), indent=1)

    # GATE 3: rules are derived FROM the public 120, but no public task may appear IN the corpus.
    # Content-level pair hashing against evaluation AND training. This catches literal re-emission;
    # it does NOT catch near-duplicates, and that limit is stated rather than papered over.
    import subprocess
    print()
    print("== GATE 3: no public benchmark pair may appear in the corpus ==", flush=True)
    rc = subprocess.run([sys.executable, os.path.join(DIAG, "crucible-screen-corpus.py"),
                         "--corpus", os.path.abspath(a.out.rstrip("/"))]).returncode
    if rc != 0:
        sys.exit("FAIL: gate 3 did not pass. See the screener's own output above for whether that "
                 "is a benchmark collision or a failure to read the corpus.")

    print()
    print(f"  TOTAL {total} blocks in {len(set(task_sk) | set(task_wt))} task directories, "
          f"{total * 4} grid-pairs -> {a.out}")


if __name__ == "__main__":
    main()
