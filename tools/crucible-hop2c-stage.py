#!/usr/bin/env python3
"""crucible-hop2c-stage.py -- hop 2c's corpus (FFT, from s001020): breadth + the 120 solve-alikes, with NVARC below half. Split: breadth 50 / the 120 30 / NVARC 15 / arc2train 5 by est tokens.
  BREADTH  blocks --breadth-skip.. (7: hop 2a's pack held 0-6) of every non-held-out rule, round-robin by rule; 128 held out = P4.
  OURS     the 120 tasks' synthetic/<task> blocks (hop 1 trained none of them), equal count per task, shuffled over the run;
           the packer's --holdout-root synthetic keeps the 196-task holdout blocks out.
  NVARC    files neither hop 1 nor hop 2a used (--exclude-corpus), P1/P2/P3 excluded, one random augmentation per block.
  ARC2     ARC-AGI-2 training minus P1/P2/P3 tasks, as fresh augmented views (seed hop2c), none equal to hop 1's / hop 2a's.
Pack with --augment -1 (everything here is already as intended; ours blocks go unaugmented as in the legs' first block).
"""
import argparse, glob, hashlib, json, os, random, sys

ap = argparse.ArgumentParser()
ap.add_argument("--shares", default="0.5,0.3,0.15,0.05", help="breadth,ours,nvarc,arc2 est-token shares")
ap.add_argument("--total-tok", type=float, default=118e6)
ap.add_argument("--real-all", action="store_true", help="real share = ARC-AGI-2 train + ConceptARC + MINI-ARC (hop 2a's real sources)")
ap.add_argument("--name", default="hop2c")
ap.add_argument("--ours-picks", default="", help="the 120 from a crucible-pick-120-blocks.py file instead of K per task")
ap.add_argument("--real-raw", action="store_true", help="ARC-AGI-2 public training puzzles as staged (one each, no stage-side views): the packer makes the views")
ap.add_argument("--breadth-per-rule", type=int, default=13)
ap.add_argument("--real-share", type=float, default=0.25)
ap.add_argument("--nvarc-share", type=float, default=0.25)
ap.add_argument("--total-tokens", type=float, default=0, help="est tokens of the whole corpus; required with --breadth-per-rule 0")
ap.add_argument("--breadth-skip", type=int, default=0, help="skip each rule's first K blocks (already trained on)")
ap.add_argument("--seed-tag", default="hop2a", help="real-view seed prefix; a new tag gives new views")
ap.add_argument("--exclude-corpus", default="", help="a prior corpus blocks dir: its real views and NVARC files are not reused")
ap.add_argument("--tag", default="", help="output dir suffix, for variants (hop2a-corpus<tag>)")
a = ap.parse_args()
D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "corpus"); SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "crucible"); BR = f"{D}/synthetic-breadth"
NV = os.environ.get("NVARC_SYNTHETIC", os.path.join(SRC, "data-sources", "nvarc-synthetic-puzzles")); OUT = f"{D}/{a.name}-corpus{a.tag}"; SH = [float(x) for x in a.shares.split(",")]
SHA = "1e93c428ef63bdf8618595105ecd00245e87781ae6ad4e046ae1a81c32b6b50f"
if hashlib.sha256(open(f"{BR}/_MANIFEST-breadth.json", "rb").read()).hexdigest() != SHA: sys.exit("FAIL: breadth manifest is not the frozen tree's")
if os.path.exists(OUT): sys.exit(f"FAIL: {OUT} exists. Nothing written.")
def gt(g): return len(g) * (len(g[0]) + 1) if g else 0
def tok(d): return sum(gt(p["input"]) + gt(p["output"]) + 8 for p in d["train"] + d["test"])
def h(d): return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()
def blank(d): return any(not any(v for row in g for v in row) for p in d["train"] + d["test"] for g in (p["input"], p["output"]))

# ---- BREADTH ----
man = json.load(open(f"{BR}/_MANIFEST-breadth.json"))["rules"]; rules = sorted(man)
held = rules[19::20]; train = [r for r in rules if r not in set(held)]
def rb(r): return sorted(f"{BR}/{r}/{n}" for n in os.listdir(f"{BR}/{r}") if n.endswith(".json") and not n.startswith("_"))
rnd = random.Random(1021); breadth = []
src = {r: rb(r)[a.breadth_skip:a.breadth_skip + a.breadth_per_rule] for r in train}
bgot = 0
for i in range(a.breadth_per_rule):
    if bgot >= SH[0] * a.total_tok: break
    rr = [r for r in train if i < len(src[r])]; rnd.shuffle(rr)
    for r in rr:
        if bgot >= SH[0] * a.total_tok: break
        d = json.load(open(src[r][i]))
        if man[r].get("colour_values_matter"): d["_colour_values_matter"] = True
        breadth.append((f"br-{r}", d, tok(d))); bgot += breadth[-1][2]
TOTAL = a.total_tok

# ---- probes held out of REAL and NVARC (as hop 1) ----
pr = json.load(open(f"{D}/evals/hop1-probes-20261007.json"))
HELD = set(pr["P1_nvarc_training"]) | set(pr["P2_arc_agi_2_training"]) | set(pr["P3_unseen"])
NEVER = set(json.load(open(f"{D}/evals/never-seen-by-nvarc.json"))["tasks"])   # never train on these
HELD |= NEVER

# ---- REAL: fresh views ----
hop1_real = {h(json.load(open(p))) for p in glob.glob(f"{D}/hop1-corpus/real/*.json")}
for xc in [x for x in a.exclude_corpus.split(",") if x]: hop1_real |= {h(json.load(open(p))) for p in glob.glob(f"{xc}/*_re-*.json")}
puz = []
for f in sorted(os.listdir(f"{SRC}/data-arc-agi-2/data/training")):
    if f.endswith(".json") and f[:-5] not in HELD: puz.append(("arc2", f[:-5], f"{SRC}/data-arc-agi-2/data/training/{f}"))
if a.real_all:
    for p in sorted(glob.glob(f"{SRC}/data-sources/conceptarc/corpus/**/*.json", recursive=True) + glob.glob(f"{SRC}/data-sources/conceptarc/MinimalTasks/*.json")):
        puz.append(("concept", os.path.basename(p)[:-5], p))
    for p in sorted(glob.glob(f"{SRC}/data-sources/mini-arc/data/MiniARC/*.json")):
        puz.append(("mini", os.path.basename(p)[:-5][:40], p))
def aug(task, r):
    perm = list(range(1, 10)); r.shuffle(perm); cmap = [0] + perm; t = r.randrange(8)
    def tf(g):
        g = [[cmap[v] for v in row] for row in g]
        if t & 4: g = [list(x) for x in zip(*g)]
        if t & 1: g = [row[::-1] for row in g]
        if t & 2: g = g[::-1]
        return g
    tr = [{"input": tf(p["input"]), "output": tf(p["output"])} for p in task["train"]]; r.shuffle(tr)
    return {"train": tr, "test": [{"input": tf(p["input"]), "output": tf(p["output"])} for p in task["test"]]}
P = []
for s, n, p in puz:
    d = json.load(open(p)); d = {"train": d["train"], "test": [x for x in d["test"] if x.get("output")]}
    if d["test"] and d["train"]: P.append((s, n, d, random.Random(f"{a.seed_tag}:{s}:{n}")))
target_r, real, got, dup, k = SH[3] * TOTAL, [], 0, 0, 0
if a.real_raw:   # one raw copy per puzzle, round-robin until the share; the packer's --views makes the views
    k = 0
    while got < target_r:   # repeated raw copies get different packer views (block names differ)
        for s, n, d, r in P:
            real.append((f"re-{s}-{n}", d, tok(d))); got += real[-1][2]
            if got >= target_r: break
        k += 1
while got < target_r:
    for s, n, d, r in P:
        v = aug(d, r)
        if h(v) in hop1_real: dup += 1; continue
        real.append((f"re-{s}-{n}", v, tok(v))); got += real[-1][2]
        if got >= target_r: break
    k += 1
    if k > 200: break

# ---- NVARC: files hop 1 never used ----
used = {"_".join(os.path.basename(p).split("_")[1:-1]) for p in glob.glob(f"{D}/hop1-corpus/nvarc/*.json")}
for xc in [x for x in a.exclude_corpus.split(",") if x]: used |= {"_".join(os.path.basename(p)[:-5].split("_")[1:-1])[6:] for p in glob.glob(f"{xc}/*_nv-*.json")}
files = []
for pool, kind in (("nvarc_training", "nt"), ("nvarc_full", "nf")):
    for dd in sorted(os.listdir(f"{NV}/{pool}")):
        if not os.path.isdir(f"{NV}/{pool}/{dd}"): continue
        for f in sorted(os.listdir(f"{NV}/{pool}/{dd}")):
            if not f.endswith(".json"): continue
            ids = f[:-5].split("_", 1)
            if dd in HELD or any(x in HELD for x in ids) or f[:-5] in used: continue
            files.append((kind, f[:-5], f"{NV}/{pool}/{dd}/{f}"))
fresh_files = len(files); random.Random(1022).shuffle(files)
target_n, nv, got_n = SH[2] * TOTAL, [], 0
for kind, name, path in files:
    if got_n >= target_n: break
    pairs = json.load(open(path))
    for i in range(0, len(pairs) - 4, 5):
        blk = {"train": pairs[i:i + 4], "test": [pairs[i + 4]]}
        if blank(blk): continue
        blk = aug(blk, random.Random(f"hop2c-nv:{name}:{i}"))
        nv.append((f"nv-{kind}-{name}", blk, tok(blk))); got_n += nv[-1][2]

# ---- OURS: the 120 tasks ----
tasks = sorted(os.path.basename(x) for x in glob.glob(f"{D}/synthetic/*") if len(os.path.basename(x)) == 8 and not os.path.basename(x).startswith("mech_"))
assert len(tasks) == 120, len(tasks)
pools = {t_: sorted(f"{D}/synthetic/{t_}/{f}" for f in os.listdir(f"{D}/synthetic/{t_}") if f.endswith(".json") and not f.startswith("_")) for t_ in tasks}
ro = random.Random(1043); [ro.shuffle(v) for v in pools.values()]
avg = {t_: sum(tok(json.load(open(p))) for p in pools[t_][:20]) / 20 for t_ in tasks}
K = int(SH[1] * TOTAL / sum(avg.values())); ours = []
if a.ours_picks:
    pk = json.load(open(a.ours_picks))["blocks"]; K = len(next(iter(pk.values())))
    for t_ in tasks: ours.extend((f"ours-{t_}", json.load(open(p)), 0) for p in pk[t_])
for t_ in ([] if a.ours_picks else tasks):
    got_t = [p for p in pools[t_][4:] if not blank(json.load(open(p)))][:K]   # first 4 left for the packer's holdout read
    if len(got_t) < K: sys.exit(f"FAIL: {t_} has {len(got_t)} blocks for K={K}")
    ours.extend((f"ours-{t_}", json.load(open(p)), 0) for p in got_t)
ro.shuffle(ours); ours = [(k_, d_, tok(d_)) for k_, d_, _ in ours]

# ---- interleave by token share ----
streams = {"br": breadth, "ours": ours, "nv": nv, "re": real}; pos = {k: 0 for k in streams}; acc = {k: 0 for k in streams}
tot = {k: sum(x[2] for x in v) or 1 for k, v in streams.items()}; order = []
while any(pos[k] < len(v) for k, v in streams.items()):
    k = min((k for k, v in streams.items() if pos[k] < len(v)), key=lambda k: acc[k] / tot[k])
    item = streams[k][pos[k]]; pos[k] += 1; acc[k] += item[2]; order.append(item)
os.makedirs(f"{OUT}/blocks"); cnt = {}
for n, (key, d, _) in enumerate(order):
    cnt[key] = cnt.get(key, 0) + 1
    json.dump(d, open(f"{OUT}/blocks/{n:06d}_{key}_{cnt[key]:03d}.json", "w"))
probes = json.load(open(f"{D}/hop2-corpus/hop2-probes.json")); json.dump(probes, open(f"{OUT}/hop2-probes.json", "w"))
rep = {"blocks": len(order), "est_tokens": {k: sum(x[2] for x in v) for k, v in streams.items()},
       "blocks_by_source": {k: len(v) for k, v in streams.items()}, "breadth_rules": len(train), "breadth_skip": a.breadth_skip,
       "arc2_puzzles": len(P), "ours_tasks": len(tasks), "ours_per_task": K, "shares": a.shares, "real_views_dropped_as_hop1_copies": dup, "nvarc_fresh_files_available": fresh_files,
       "nvarc_files_used": len({x[0] for x in nv}), "excluded_held_probe_tasks": len(HELD), "seed_tag": a.seed_tag, "breadth_skip": a.breadth_skip, "probes": {k: len(v) for k, v in probes.items()}}
json.dump(rep, open(f"{OUT}/stage-report.json", "w"), indent=1); print(json.dumps(rep, indent=1))
