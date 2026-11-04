#!/usr/bin/env python3
# harness.py -- the breadth rules: thousands of DISTINCT rules, a dozen blocks each. A rule is two pure functions, make_input(rng) -> grid and transform(grid) -> grid;
# the transform IS the ground truth, so no second solver is required (that requirement held mechanics to
# 76 rules in six weeks). Gates per pair: well-formed grids (1..30 x 1..30, ints 0..9), deterministic
# transform, output != input, no benchmark grid (midband.is_benchmark_pair, colour+view canonical),
# distinct canonical inputs within a pool. Per block: at least two distinct outputs (a block whose answers
# are all the same grid teaches a constant). Per rule: reject rate < 90%, at least `min_blocks` blocks.
# Block format is the corpus's: {"train": [{input, output} x 3-5], "test": [{input, output}], "_rule_sha"}.
import hashlib, inspect, json, os, sys, random

DIAG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DIAG)
import midband as mb  # noqa: E402  -- is_benchmark_pair and _canon, the corpus's own screen

RULES = {}


class Rule:
    def __init__(self, name, desc, make_input, transform, demos=(3, 5), batch=None, digits=False, primitive=False, small_ok=False):
        self.name, self.desc, self.make_input, self.transform, self.demos = name, desc, make_input, transform, demos
        self.digits = digits   # colour values carry NUMBERS (counts, lengths, indices); the packer must not colour-permute
        self.primitive = primitive  # an honest one-operation rule (transpose, rot90); exempt from the trivial-block gate
        self.small_ok = small_ok    # the output size cap forbids 21-30 inputs; exempt from the large-input share gate
        self.batch = batch or os.path.basename(inspect.getsourcefile(make_input))
        self.sha = hashlib.sha256((inspect.getsource(make_input) + inspect.getsource(transform)).encode()).hexdigest()


def rule(name, desc, make_input, transform, demos=(3, 5), digits=False, primitive=False, small_ok=False):
    """Register a rule. name: [a-z0-9_]+ unique across every batch file. desc: one plain-English sentence
    a human could apply by hand; it goes in _meta.json and is the review surface."""
    if name in RULES:
        raise ValueError(f"duplicate rule name {name} ({RULES[name].batch} and {inspect.getsourcefile(make_input)})")
    if not name.replace("_", "").isalnum() or name != name.lower():
        raise ValueError(f"bad rule name {name}")
    RULES[name] = Rule(name, desc, make_input, transform, demos, digits=digits, primitive=primitive, small_ok=small_ok)
    return RULES[name]


def well_formed(g):
    return (isinstance(g, list) and 1 <= len(g) <= 30 and all(isinstance(r, list) for r in g)
            and 1 <= len(g[0]) <= 30 and all(len(r) == len(g[0]) for r in g)
            and all(isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 9 for r in g for v in r))


def canon(g):
    return mb._canon(g)


# --- simple-hypothesis screen (ported from the trio's review, breadth-review-20261012/screen.py) ---
def _dihedral(g, k):
    h = [r[:] for r in g]
    if k & 4: h = [list(r) for r in zip(*h)]
    if k & 1: h = h[::-1]
    if k & 2: h = [r[::-1] for r in h]
    return h


def _cmap_fit(pairs, k):
    m = {}
    for p in pairs:
        a = _dihedral(p["input"], k); b = p["output"]
        if len(a) != len(b) or len(a[0]) != len(b[0]): return None
        for ra, rb in zip(a, b):
            for x, y in zip(ra, rb):
                if m.setdefault(x, y) != y: return None
    return m


def _crop_nonbg(g):
    import collections
    flat = [v for r in g for v in r]; bg = collections.Counter(flat).most_common(1)[0][0]
    cells = [(i, j) for i, r in enumerate(g) for j, v in enumerate(r) if v != bg]
    if not cells: return None
    i0, i1 = min(c[0] for c in cells), max(c[0] for c in cells); j0, j1 = min(c[1] for c in cells), max(c[1] for c in cells)
    return [r[j0:j1 + 1] for r in g[i0:i1 + 1]]


def _hyps():
    for k in range(8): yield (lambda k: lambda g: _dihedral(g, k))(k)
    yield _crop_nonbg
    for k in (2, 3, 4): yield (lambda k: lambda g: [[v for v in r for _ in range(k)] for r in g for _ in range(k)])(k)
    for a, b in ((1, 2), (2, 1), (2, 2), (3, 3)): yield (lambda a, b: lambda g: [r * b for r in g] * a)(a, b)


def simple_hypothesis_explains(pairs):
    """True if one global dihedral map, colour map (with or without a dihedral), crop, integer upscale or tiling
    reproduces every pair. Such a block teaches a primitive, not the rule."""
    for f in _hyps():
        try:
            if all(f(p["input"]) == p["output"] for p in pairs): return True
        except Exception:
            pass
    for k in range(8):
        m = _cmap_fit(pairs, k)
        if m is not None and any(a != b for a, b in m.items()): return True
    return False


def colour_values_matter(r, pairs, rng):
    """G7: does transform(perm(x)) == perm(transform(x)) for permutations of the colours 1-9 other than grey 5?
    A rule that picks a colour by its NUMBER fails this; its pool must not be colour-permuted by the packer."""
    cols = [1, 2, 3, 4, 6, 7, 8, 9]
    for _ in range(4):
        p = cols[:]; rng.shuffle(p); perm = dict(zip(cols, p)); perm[0] = 0; perm[5] = 5
        for pr in pairs[:6]:
            try:
                a = r.transform([[perm[v] for v in row] for row in pr["input"]])
            except Exception:
                return True
            if a != [[perm[v] for v in row] for row in pr["output"]]: return True
    return False


def draw_pair(r, rng, seen_inputs, why):
    try:
        inp = r.make_input(rng)
    except Exception as e:  # an author bug is a reject with a reason, not a crash of the build
        why["gen_error"] += 1; why.setdefault("_err", str(e)[:120]); return None
    if inp is None:
        why["gen_none"] += 1; return None   # the author's own input filter; cheap, not counted against the rule
    if not well_formed(inp):
        why["bad_input"] += 1; return None
    try:
        out = r.transform([row[:] for row in inp])
        out2 = r.transform([row[:] for row in inp])
    except Exception as e:
        why["tf_error"] += 1; why.setdefault("_err", str(e)[:120]); return None
    if out is None:
        why["tf_none"] += 1; return None
    if not well_formed(out):
        why["bad_output"] += 1; return None
    if out != out2:
        why["nondeterministic"] += 1; return None
    if out == inp:
        why["identity"] += 1; return None
    if len({v for row in out for v in row}) == 1:
        why["empty_output"] += 1; return None   # an all-one-colour answer teaches nothing
    ci = canon(inp)
    if ci in seen_inputs:
        why["dup_input"] += 1; return None
    if mb.is_benchmark_pair(inp, out):
        why["benchmark"] += 1; return None
    seen_inputs.add(ci)
    return {"input": inp, "output": out}


def draw_block(r, seed, seen_inputs, why):
    rng = random.Random(seed)
    # BREADTH_DEMOS="lo,hi" (NVARC-style 5-7-pair puzzles): override every rule's demo range. Unset = the rule's own.
    _dr = tuple(int(x) for x in os.environ["BREADTH_DEMOS"].split(",")) if os.environ.get("BREADTH_DEMOS") else r.demos
    n_demo = rng.randint(*_dr)
    pairs = []
    tries = 0
    while len(pairs) < n_demo + 1 and tries < (n_demo + 1) * 40:
        tries += 1
        p = draw_pair(r, rng, seen_inputs, why)
        if p:
            pairs.append(p)
    if len(pairs) < n_demo + 1:
        why["short_block"] += 1; return None
    if len({json.dumps(p["output"]) for p in pairs}) < 2:   # raw, not canonical: a 1x1 answer differing by colour is a different answer
        why["constant_answers"] += 1; return None
    if any(p["output"] == pairs[-1]["output"] for p in pairs[:-1]):   # G3: copying a demo answer must not score
        why["test_answer_in_demos"] += 1; return None
    if not r.primitive and simple_hypothesis_explains(pairs):          # G1: the block is one global operation
        why["trivial_block"] += 1; return None
    if not r.primitive and simple_hypothesis_explains(pairs[:-1]):     # G2: the demos admit a simpler rule than the test needs
        why["underspecified_block"] += 1; return None
    return {"train": pairs[:-1], "test": [pairs[-1]], "_rule_sha": r.sha}


def build_pool(r, out_root, blocks=12, min_blocks=8, seed_salt="breadth"):
    seed_salt = os.environ.get("BREADTH_SEED_SALT", seed_salt)   # a new salt draws blocks never generated before
    d = os.path.join(out_root, r.name)
    why = {k: 0 for k in ("gen_error", "gen_none", "bad_input", "tf_error", "tf_none", "bad_output", "nondeterministic",
                          "identity", "empty_output", "dup_input", "benchmark", "short_block", "constant_answers",
                          "test_answer_in_demos", "trivial_block", "underspecified_block")}
    seen, got, idx = set(), [], 0
    while len(got) < blocks and idx < blocks * 6:
        seed = int(hashlib.sha256(f"{seed_salt}:{r.name}:{idx}".encode()).hexdigest()[:12], 16)
        idx += 1
        b = draw_block(r, seed, seen, why)
        if b:
            got.append(b)
    pairs_tried = sum(v for k, v in why.items() if not k.startswith("_") and k != "gen_none") + sum(len(b["train"]) + 1 for b in got)
    reject_rate = 1 - sum(len(b["train"]) + 1 for b in got) / max(1, pairs_tried)
    all_pairs = [p for b in got for p in b["train"] + b["test"]]
    big_share = round(sum(1 for p in all_pairs if max(len(p["input"]), len(p["input"][0])) >= 21) / max(1, len(all_pairs)), 3)
    cvm = r.digits or colour_values_matter(r, all_pairs, random.Random(hashlib.sha256(r.name.encode()).hexdigest()))
    ok = len(got) >= min_blocks and reject_rate < 0.9
    small_grid_warning = not r.small_ok and big_share < 0.25   # G4 is recorded, not enforced, for the pre-rule batches (295 rules); the pack reads it
    meta = {"source": r.name, "lane": "breadth", "batch": r.batch, "desc": r.desc, "rule_sha": r.sha, "digits": r.digits,
            "colour_values_matter": bool(cvm), "primitive": r.primitive, "big_input_share": big_share, "small_grid_warning": small_grid_warning,
            "blocks": len(got), "pairs": sum(len(b["train"]) + 1 for b in got), "rejects": {k: v for k, v in why.items() if v},
            "reject_rate": round(reject_rate, 3), "ok": ok,
            "gate": "well-formed; deterministic transform; output != input; no single-colour answer; no benchmark grid up to "
                    "colour and view; distinct canonical inputs per pool; >= 2 distinct answers per block; test answer differs "
                    "from every demo answer (G3); no block explained by a global dihedral/colour-map/crop/scale/tile (G1) nor "
                    "its demos alone (G2) unless primitive; >= 25% of inputs 21-30 a side unless small_ok (G4); reject rate < 0.9; "
                    "colour_values_matter = digits or a failed colour-permutation equivariance test (G7)"}
    if ok:
        os.makedirs(d, exist_ok=True)
        for f in os.listdir(d):
            if f.endswith(".json"):
                os.remove(os.path.join(d, f))   # a rebuild replaces the pool wholesale; one rule sha per pool
        for i, b in enumerate(got):
            json.dump(b, open(os.path.join(d, f"{r.name}_{i:04d}.json"), "w"))
        json.dump(meta, open(os.path.join(d, "_meta.json"), "w"), indent=1)
    return meta
