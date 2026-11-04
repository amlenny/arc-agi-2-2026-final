#!/usr/bin/env python3
"""crucible-pick-120-blocks.py --hard H --easy E --close C --out FILE [--exclude-curriculum DIR,...] -- per task of the 120,
pick blocks from its pool (synthetic/<task>, never _holdout) by difficulty measured against the REAL eval puzzle
(data-arc-agi-2/data/evaluation/<task>.json). hardest + easiest + closest to the actual problem's difficulty.
Features per block / per real task: mean grid cells (in+out), mean changed cells (same-shape pairs; else output cells),
distinct colours. Difficulty = sum of features normalised by the real task's. HARD = highest difficulty; EASY = lowest;
CLOSE = smallest distance to the real task's features (log ratios). Disjoint, deterministic. Writes {task: [paths]}.
"""
import argparse, glob, hashlib, json, math, os
ap = argparse.ArgumentParser(); ap.add_argument("--hard", type=int, required=True); ap.add_argument("--easy", type=int, required=True)
ap.add_argument("--close", type=int, required=True); ap.add_argument("--out", required=True); ap.add_argument("--exclude-curriculum", default="")
a = ap.parse_args(); D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "corpus"); EV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "crucible", "data-arc-agi-2", "data", "evaluation")
def h(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
EX = set()
for c in [x for x in a.exclude_curriculum.split(",") if x]: EX |= {h(p) for p in glob.glob(f"{D}/{c}/s*/*.json")}
# EXCLUDE_CONTENT=dir[,dir]: drop any block whose CONTENT (train+test) matches a
# block in <dir>/blocks -- the FFT hop corpora store re-serialized copies, so a file-byte hash would miss them.
def ch(d): return hashlib.sha256(json.dumps({"train": d["train"], "test": d["test"]}, sort_keys=True).encode()).hexdigest()
EXC = set()
# EXCLUDE_PICKS=picks-a.json[,...]: exclude every pool file an earlier picks file named, by PATH. --exclude-curriculum
# compares file bytes against the curriculum's transformed copies and never matched: FT-042b/c re-picked the same 1,200 files
# in all 8 epochs.
EXP = set()
for c in [x for x in os.environ.get("EXCLUDE_PICKS", "").split(",") if x]:
    EXP |= {q for v in json.load(open(c if c.startswith("/") else f"{D}/{c}"))["blocks"].values() for q in v}
for c in [x for x in os.environ.get("EXCLUDE_CONTENT", "").split(",") if x]:
    for q in glob.glob(f"{D}/{c}/blocks/*.json"):
        try: EXC.add(ch(json.load(open(q))))
        except Exception: pass
def feats(task):
    ps = task["train"] + [p for p in task.get("test", []) if p.get("output")]
    cells = sum(len(p["input"]) * len(p["input"][0]) + len(p["output"]) * len(p["output"][0]) for p in ps) / len(ps)
    ch = []
    for p in ps:
        i, o = p["input"], p["output"]
        ch.append(sum(a_ != b_ for ri, ro in zip(i, o) for a_, b_ in zip(ri, ro)) if (len(i), len(i[0])) == (len(o), len(o[0])) else len(o) * len(o[0]))
    cols = len({v for p in ps for g in (p["input"], p["output"]) for r in g for v in r})
    return (cells, sum(ch) / len(ch) + 1, cols)
def blank(d): return any(not any(v for row in g for v in row) for p in d["train"] + d.get("test", []) for g in (p.get("input"), p.get("output")) if g)
tasks = sorted(os.path.basename(d) for d in glob.glob(f"{D}/synthetic/*") if len(os.path.basename(d)) == 8 and not os.path.basename(d).startswith("mech_"))
assert len(tasks) == 120
out, rep = {}, {}
for t in tasks:
    real = feats(json.load(open(f"{EV}/{t}.json")))
    pool = []
    for p in sorted(glob.glob(f"{D}/synthetic/{t}/*.json")):
        if os.path.basename(p).startswith("_"): continue
        d = json.load(open(p))
        if blank(d) or (EX and h(p) in EX) or (EXC and ch(d) in EXC) or p in EXP: continue
        f = feats(d); diff = sum(x / r for x, r in zip(f, real)); dist = sum(math.log(x / r) ** 2 for x, r in zip(f, real))
        pool.append((p, diff, dist))
    need = a.hard + a.easy + a.close
    if len(pool) < need: raise SystemExit(f"FAIL: {t} has {len(pool)} usable blocks < {need}")
    by_d = sorted(pool, key=lambda x: (x[1], x[0])); hard = by_d[-a.hard:]; easy = by_d[:a.easy]
    taken = {x[0] for x in hard + easy}
    close = sorted((x for x in pool if x[0] not in taken), key=lambda x: (x[2], x[0]))[:a.close]
    out[t] = [x[0] for x in hard + easy + close]
    rep[t] = {"pool": len(pool), "real": [round(v, 1) for v in real], "hard_diff": round(hard[0][1], 2), "easy_diff": round(easy[-1][1], 2),
              "close_dist_max": round(close[-1][2], 3)}
json.dump({"hard": a.hard, "easy": a.easy, "close": a.close, "blocks": out, "report": rep}, open(a.out, "w"), indent=1)
print(f"wrote {a.out}: 120 tasks x {need} blocks; e.g. {tasks[0]} {rep[tasks[0]]}")
