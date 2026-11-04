#!/usr/bin/env python3
"""nv-stage.py <out> --ours-share S [--total 85e6] [--seed N] -- NVARC-style corpus: every synthetic showing is a NEW 5-7-pair puzzle, shown once (the packer then gives it one fresh view).
  br    synthetic-breadth-nv1 (crucible-breadth-nv-build.sh: new blocks of 5-7 pairs per breadth rule, never generated before);
        the 128 P4 rules are excluded, as every builder
  ours  S120: per rule, the pairs of its S120-fresh blocks never seen by FFT-002, kept only if every pair passes generators/<rule>.py
        transform(); dealt (shuffled, each pair once) into 5-7-pair showings. A rule with a failing pair is left out
  re    real-loo-corpus blocks, each once: the real share (pairs are fixed)
  rmx   remix blocks never seen by FFT-002, as staged
Shares: re 0.045, rmx 0.05, ours S, br the rest. Streams interleaved by token share (as every stage). Writes <out>/blocks,
<out>/hop2-probes.json, <out>/stage-report.json.
"""
import argparse, glob, importlib.util, json, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--ours-share", type=float, required=True)
ap.add_argument("--total", type=float, default=85e6); ap.add_argument("--seed", type=int, default=7272)
ap.add_argument("--breadth-dir", default="synthetic-breadth-nv1", help="tree of fresh breadth puzzles ")
ap.add_argument("--re-share", type=float, default=0.045, help="real-loo share; above one pass, blocks repeat as named copies (each gets its own fresh view at pack time)")
ap.add_argument("--rmx-share", type=float, default=0.05)
ap.add_argument("--re-dir", default="real-loo-corpus", help="real pool (layout of real-loo-corpus); real-pool-corpus = (real-loo + rotate + rotate-1 + MINI-ARC + ARC-1-only, probe-screened)")
ap.add_argument("--re-schemes", default="", help="comma list of manifest 'scheme' values to use (current,rotate,rotate-1); empty = all")
ap.add_argument("--skip-br", default="", help="file of br block paths already used by another corpus (vol7a/vol7b disjoint)")
ap.add_argument("--ours-samples", type=int, default=0, help="S120 the NVARC way: per rule, verified pairs grouped into puzzles of "
                "--ours-puzzle-pairs (min 12), each puzzle sampled this many times as a random 5-7 of its pairs; 0 = each pair dealt once")
ap.add_argument("--ours-puzzle-pairs", type=int, default=30)
ap.add_argument("--br-samples", type=int, default=0, help="breadth the same NVARC way: each breadth block is one puzzle (all its "
                "pairs, e.g. 30-pair hi-loss blocks), sampled this many times as a random 5-7 of its pairs; 0 = each block as staged")
a = ap.parse_args(); OUT = os.path.join(HERE, a.out)
if os.path.exists(OUT): sys.exit(f"FAIL: {OUT} exists")
def gt(g): return len(g) * (len(g[0]) + 1) if g else 0
def tok(d): return sum(gt(p["input"]) + gt(p["output"]) + 8 for p in d["train"] + d["test"])
rnd = random.Random(a.seed)
SH = {"re": a.re_share, "rmx": a.rmx_share, "ours": a.ours_share}; SH["br"] = 1 - sum(SH.values()); T = {k: v * a.total for k, v in SH.items()}
import gzip
NS = json.load(gzip.open(os.path.join(HERE, "evals", "lineage", "never-seen-FFT-002.json.gz"), "rt"))
for _v in NS["pools"].values():
    _v["never_seen"] = [os.path.join(HERE, f) for f in _v.get("never_seen", [])]
man = json.load(open(os.path.join(HERE, "synthetic-breadth", "_MANIFEST-breadth.json")))["rules"]; P4 = set(sorted(man)[19::20])
streams = {}
# br: new puzzles, P4 rules out, a disjoint set if --skip-br
skip = set(open(a.skip_br).read().split()) if a.skip_br else set()
br = [f for f in sorted(glob.glob(os.path.join(HERE, a.breadth_dir, "*", "*.json")))
      if not os.path.basename(f).startswith("_") and os.path.basename(os.path.dirname(f)) not in P4 and f not in skip]
rnd.shuffle(br); got = 0; streams["br"] = []
# colour_values_matter lives in <rule>/_meta.json (or the tree's _MANIFEST-breadth.json); the packer reads it only from the
# block ("_colour_values_matter"). Copy it onto every staged br block.
_bm = os.path.join(HERE, a.breadth_dir, "_MANIFEST-breadth.json")
_bman = json.load(open(_bm)).get("rules", {}) if os.path.exists(_bm) else {}
_cvm = {}
def cvm(rule):
    if rule not in _cvm:
        mp = os.path.join(HERE, a.breadth_dir, rule, "_meta.json")
        _cvm[rule] = bool((json.load(open(mp)) if os.path.exists(mp) else _bman.get(rule, {})).get("colour_values_matter"))
    return _cvm[rule]
for f in br:
    if got >= T["br"]: break
    d = json.load(open(f)); rule = os.path.basename(os.path.dirname(f)); key = f"br-{rule}"
    if cvm(rule): d["_colour_values_matter"] = True
    if not a.br_samples:
        streams["br"].append((key, d, tok(d), f)); got += tok(d); continue
    q = [p for p in d["train"] + d["test"] if p.get("output")]
    if len(q) < 5: continue
    for _ in range(a.br_samples):
        if got >= T["br"]: break
        g = rnd.sample(q, min(len(q), rnd.randint(5, 7))); x = {"train": g[:-1], "test": [g[-1]]}
        if cvm(rule): x["_colour_values_matter"] = True
        streams["br"].append((key, x, tok(x), f)); got += tok(x)
# ours: fresh draws from verified pools
FRESH = ("nbrB", "fft-nbrB", "nbrB-doesnt-fixed", "fft-nbrB-doesnt-fixed", "midband")
pool = {}
for f in NS["pools"]["s120-fresh"]["never_seen"]:
    q = os.path.relpath(f, HERE).split(os.sep)
    if os.path.basename(f).count("_") < 2 or q[0] != "ours-fresh-20261003" or q[1] not in FRESH: continue
    pool.setdefault(os.path.basename(f).split("_")[1], []).append(f)
def gen(rule):
    p = os.path.join(HERE, "generators", f"{rule}.py")
    if not os.path.exists(p): return None
    s = importlib.util.spec_from_file_location(f"g_{rule}", p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
streams["ours"] = []; ours_rep = {"kept": {}, "left_out": {}, "as_staged": {}}
if T["ours"] > 0:
    per_rule = T["ours"] / max(1, len(pool));
    for rule in sorted(pool):
        m = gen(rule); fs = pool[rule][:]; rnd.shuffle(fs)
        # 3 generators have no transform() and 16b78196's disagrees with most of its pool; dropping them cut two of the
        # never-solved 57. A rule that cannot be verified keeps its blocks AS STAGED (fixed pairs) up to its token budget instead.
        why = None if (m is not None and hasattr(m, "transform")) else "no transform()"
        pairs = []; tk = 0; checked = failed = 0
        if why is None:
            for f in fs:
                d = json.load(open(f)); ps = d["train"] + [t for t in d["test"] if t.get("output")]; checked += 1
                try:
                    if any(m.transform(p["input"]) != p["output"] for p in ps): failed += 1; continue
                except Exception as e:
                    why = f"transform raised {type(e).__name__}"; break
                pairs += ps; tk += tok({"train": ps, "test": []})
                # NVARC sampling reuses each pair ~K*6/P times: collect only the pool that budget needs
                if tk >= 1.15 * per_rule * (1 if not a.ours_samples else a.ours_puzzle_pairs / (6.0 * a.ours_samples)): break
            if why is None and checked and failed / checked > 0.5: why = f"transform fails {failed}/{checked} blocks"
        if why:
            got = 0; n = 0
            for f in fs:
                if got >= per_rule: break
                d = json.load(open(f)); d = {"train": d["train"], "test": [t for t in d["test"] if t.get("output")]}
                if not d["test"]: continue
                streams["ours"].append((f"ours-{rule}", d, tok(d), None)); got += tok(d); n += 1
            ours_rep["as_staged"][rule] = {"why": why, "blocks": n}; continue
        rnd.shuffle(pairs); i = 0; n = 0; got = 0
        if a.ours_samples:
            P = a.ours_puzzle_pairs; puz = [pairs[j:j + P] for j in range(0, len(pairs), P)]
            puz = [q for q in puz if len(q) >= 12] or ([pairs] if len(pairs) >= 5 else [])
            while puz and got < per_rule:
                for q in puz:
                    if got >= per_rule: break
                    for _ in range(a.ours_samples):
                        if got >= per_rule: break
                        g = rnd.sample(q, min(len(q), rnd.randint(5, 7)))
                        d = {"train": g[:-1], "test": [g[-1]]}; streams["ours"].append((f"ours-{rule}", d, tok(d), None)); got += tok(d); n += 1
            ours_rep["kept"][rule] = n; continue
        while len(pairs) - i >= 5 and got < per_rule:
            k = rnd.randint(5, 7); g = pairs[i:i + k]; i += k
            d = {"train": g[:-1], "test": [g[-1]]}; streams["ours"].append((f"ours-{rule}", d, tok(d), None)); got += tok(d); n += 1
        ours_rep["kept"][rule] = n
# re: real-loo once
rl = json.load(open(os.path.join(HERE, a.re_dir, "manifest.json")))
rl = rl if isinstance(rl, list) else rl.get("blocks", rl)
_sch = set(x for x in a.re_schemes.split(",") if x)
c1 = {f"re-{b['source']}-{b['task']}-{b['variant']}-c1" for b in rl if not _sch or b.get("scheme") in _sch}; streams["re"] = []; got = 0; rep_copy = 0
refs = [f for f in sorted(glob.glob(os.path.join(HERE, a.re_dir, "blocks", "*.json")))
        if os.path.basename(f).split("_", 1)[1].rsplit("_", 1)[0] in c1]
while refs and got < T["re"]:   # copy n > 0 is a NAMED copy (-r<n>), so the packer gives it its own fresh view
    for f in refs:
        if got >= T["re"]: break
        k = os.path.basename(f).split("_", 1)[1].rsplit("_", 1)[0]; k = k if rep_copy == 0 else f"{k}-r{rep_copy}"
        d = json.load(open(f)); streams["re"].append((k, d, tok(d), None)); got += tok(d)
    rep_copy += 1
# rmx: never seen by FFT-002
rm = [f for p, v in NS["pools"].items() if p.startswith("remix") for f in v["never_seen"]]; rnd.shuffle(rm); streams["rmx"] = []; got = 0
for f in rm:
    if got >= T["rmx"]: break
    try: d = json.load(open(f))
    except Exception: continue
    if not (isinstance(d, dict) and d.get("train")): continue
    streams["rmx"].append((f"rmx-{os.path.basename(os.path.dirname(f))}", d, tok(d), None)); got += tok(d)
# interleave by token share
for v in streams.values(): random.Random(a.seed + 1).shuffle(v)
pos = {k: 0 for k in streams}; acc = {k: 0 for k in streams}; tot = {k: sum(x[2] for x in v) or 1 for k, v in streams.items()}; order = []
while any(pos[k] < len(v) for k, v in streams.items()):
    k = min((k for k, v in streams.items() if pos[k] < len(v)), key=lambda k: acc[k] / tot[k])
    order.append(streams[k][pos[k]]); acc[k] += streams[k][pos[k]][2]; pos[k] += 1
os.makedirs(os.path.join(OUT, "blocks")); cnt = {}
for n, (key, d, _, _) in enumerate(order):
    cnt[key] = cnt.get(key, 0) + 1; json.dump(d, open(os.path.join(OUT, "blocks", f"{n:06d}_{key}_{cnt[key]:03d}.json"), "w"))
open(os.path.join(OUT, "br-used.txt"), "w").write("\n".join(x[3] for x in streams["br"]) + "\n")
os.system(f"cp {HERE}/hop6-corpus/hop2-probes.json {OUT}/")
et = {k: sum(x[2] for x in v) for k, v in streams.items()}; TT = sum(et.values())
pairs_hist = {}
for k, v in streams.items():
    h = {}
    for x in v: n = len(x[1]["train"]) + len(x[1]["test"]); h[n] = h.get(n, 0) + 1
    pairs_hist[k] = dict(sorted(h.items()))
rep = {"blocks": len(order), "est_tokens": et, "est_total": TT, "share": {k: round(v / TT, 4) for k, v in et.items()}, "shares_target": SH,
       "blocks_by_source": {k: len(v) for k, v in streams.items()}, "pairs_per_block": pairs_hist, "ours": ours_rep, "seed": a.seed,
       "br_rules": len({x[0] for x in streams["br"]}), "excluded_p4_rules": len(P4), "re_passes": rep_copy, "breadth_dir": a.breadth_dir, "ours_samples": a.ours_samples, "ours_puzzle_pairs": a.ours_puzzle_pairs, "br_samples": a.br_samples, "br_colour_values_matter_rules": sum(_cvm.values())}
json.dump(rep, open(os.path.join(OUT, "stage-report.json"), "w"), indent=1)
print(json.dumps({k: rep[k] for k in ("blocks", "est_total", "share", "blocks_by_source", "br_rules")}), "as_staged", ours_rep["as_staged"],
      "| ours rules kept", len(ours_rep["kept"]), "left out", len(ours_rep["left_out"]))
