# build-neighborhoods.py — emit graded neighbourhood batches, gated before they leave.
import hashlib, importlib.util, json, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
def sib(stem, path=None):
    sp = importlib.util.spec_from_file_location(stem.replace("-","_"), path or os.path.join(HERE, f"{stem}.py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
nb = sib("neighborhoods")
sc = sib("crucible-score", os.path.join(os.path.dirname(HERE), "crucible", "crucible-score.py"))


def ghash(g): return hashlib.sha256(json.dumps(g, separators=(",",":")).encode()).hexdigest()


def _relabel_canon(g):
    """Smallest colour-anonymous form over all eight dihedral views.

    ghash above compares raw bytes, so it only catches a grid that is identical to an evaluation
    grid cell for cell. A generated grid that is an evaluation grid turned, mirrored or recoloured
    passes it untouched: 143 grids in corpus-solvealike are evaluation grids in another view and
    the byte screen caught none of them. Same implementation as corpus-replay.canon.
    """
    cur, best = [list(r) for r in g], None
    for _ in range(4):
        for form in (cur, [r[::-1] for r in cur]):
            m, nxt, out = {}, 0, []
            for row in form:
                r2 = []
                for v in row:
                    if v not in m:
                        m[v] = nxt
                        nxt += 1
                    r2.append(m[v])
                out.append(tuple(r2))
            n = tuple(out)
            if best is None or n < best:
                best = n
        cur = [list(r) for r in zip(*cur[::-1])]
    return best

tasks = sc.load_tasks(os.path.join(os.path.dirname(HERE), "crucible", "data-kaggle"), "evaluation")
ev = set()
ev_canon = set()
for t in tasks.values():
    for p in t["train"] + t["test"]:
        ev.add(ghash(p["input"]))
        ev_canon.add(_relabel_canon(p["input"]))
        if p.get("output") is not None:
            ev.add(ghash(p["output"]))
            ev_canon.add(_relabel_canon(p["output"]))

# How many independent draws a slot gets before it is left empty. Bounded so one unfillable slot
# cannot spin; deterministic so the same slot fails the same way on every run.
VERIFY_TRIES = int(os.environ.get("NBR_VERIFY_TRIES", "40"))
REJECTED = {}
ATTEMPTS = {}
# blocks this run generated into each source's _holdout/, kept apart from the training set
HOLDOUT = {}
# WHAT A SHORT HOLDOUT COST BEFORE IT WAS LEFT SHORT. Two very different things produce the same
# "6 of 8" on a report: a generator whose input space genuinely runs out, and a slot that simply
# was not given enough draws. Read without this, every short holdout looks like the first, and a
# reader is entitled to assume it was never really tried. Per source: the budget each slot was
# given, the highest attempt count any filled slot needed, and the slots that exhausted the budget.
HOLDOUT_TRIES = {}
# tids this run actually generated, per source. The write pass uses it so a block already on
# disk is never reopened for writing.
CREATED = {}
_VERIFIERS = {}


def slot_seed(cls, source, grade, k, attempt, j):
    """Every seed is DERIVED from its coordinates, never drawn. sha256 for the same reason the
    slot tag uses it: hash() is salted per process and would reseed the whole corpus each run."""
    # NBR_SEED_SALT draws a fresh set of slots from the same skeletons, for blocks that must not
    # repeat a pool's own; unset, every seed is what it always was.
    salt = os.environ.get("NBR_SEED_SALT", "")
    tag = f"{cls}|{source}|{grade}|{k}|{attempt}|{j}{'|' + salt if salt else ''}".encode()
    return 880000 + int(hashlib.sha256(tag).hexdigest()[:8], 16) % 10000000


def verifier(source):
    """The admitted check for the source task as (kind, fn), or None if there isn't one yet.

    TWO CONTRACTS, and which one a source uses is a fact about the task, not a preference:

      verify_block(task) -> bool  a BLOCK CHECK, and it wins over both of the others where it
                                exists. Some mechanics draw a COLOUR ROLE once per block -- which
                                frame colour parks at which wall, say -- and a solver handed one
                                grid cannot recover a convention only the demos carry. Checking
                                such a task pair by pair forces every block in the corpus onto the
                                one role assignment the solver happens to default to, which is how
                                a task ends up looking hue-keyed when it is not. verify_block
                                recovers the roles from the demos and requires the test to follow.

      verify(gi, go) -> bool    a CHECK. For sources whose skeleton CONSTRUCTS the answer and
                                derives the problem from it. Nothing has to work out where a piece
                                goes, so demanding an independent re-derivation means writing a
                                solver for a problem that was never open — and then constraining
                                the skeleton until that solver can win, which is how 16b78196 came
                                to reject 23% of its slots and still disagree on 15% of the rest.

      transform(gi) -> grid     a SOLVER. Reproduces the answer independently. Right for every
                                source whose skeleton draws an instance rather than building its
                                solution, and it is the stronger check where it is honest.

    verify_block wins over verify, which wins over transform. A source with none emits ungated,
    as before.
    """
    if source not in _VERIFIERS:
        path = os.path.join(HERE, "generators", f"{source}.py")
        found = None
        if os.path.isfile(path):
            sp = importlib.util.spec_from_file_location(f"gen_{source}", path)
            m = importlib.util.module_from_spec(sp)
            sp.loader.exec_module(m)
            if getattr(m, "verify_block", None):
                found = ("verify_block", m.verify_block)
            elif getattr(m, "verify", None):
                found = ("verify", m.verify)
            elif getattr(m, "transform", None):
                found = ("transform", m.transform)
        _VERIFIERS[source] = found
    return _VERIFIERS[source]


_GATES = {}


def block_gate(source):
    """The BLOCK GATE for a source, from neighborhoods.BLOCK_GATES, or None.

    SEPARATE FROM THE VERIFIER, AND ADDITIVE RATHER THAN EXCLUSIVE, which is the whole reason it is
    its own hook. verify_block REPLACES the per-pair solver check for its source, so a gate written
    as a verify_block silently drops rule fidelity unless it re-runs the solver on every pair
    itself. The two ask different questions: a verifier asks whether the block's answers follow the
    rule, a gate asks whether the block is worth shipping -- typically whether its DEMOS separate a
    reading its TEST turns on. A gate runs only after the verifier has passed.

    A GATE IS A BLOCK-LEVEL CONDITION AND A SKELETON CANNOT EXPRESS ONE. A skeleton is called once
    per pair and never sees the block, so "at least one demo must do X" is not something it can
    refuse a draw on. Approximating it per pair -- refusing every pair that fails X -- both changes
    the pool more than asked and costs the build: on 3a25b0d8 that stand-in ran more than five times
    the whole build without completing a single block, against 115 seconds ungated.

    The gate takes the same shape verify_block does: gate(task) -> bool, with the last pair as the
    test and the rest as its demos.
    """
    if source not in _GATES:
        got = None
        try:
            import neighborhoods as _nb
            got = getattr(_nb, "BLOCK_GATES", {}).get(source)
        except Exception:
            got = None
        _GATES[source] = got
    return _GATES[source]


def verifies(source, pairs):
    """The verifier and then the gate. BOTH DRAWS CONSULT THIS, which is the point: when the
    equivalent consult was added to the midband builder the holdout draw was left ungated and 3 of
    16 holdout blocks came out traps while the training pool read clean."""
    if not _rule_verifies(source, pairs):
        return False
    gate = block_gate(source)
    if gate is None:
        return True
    task = {"train": [{"input": gi, "output": go} for gi, go in pairs[:-1]],
            "test": [{"input": pairs[-1][0], "output": pairs[-1][1]}]}
    try:
        return bool(gate(task))
    except Exception:
        return False


def _rule_verifies(source, pairs):
    """A variant is admissible iff the admitted rule reproduces its output from its input.

    NO GENERATOR MEANS NO GATE, and that is stated rather than silently passed: a source with no
    file in generators/ emits unverified, exactly as it did before. Everything with a generator
    is now checked, which is the difference between a corpus of the rule and a corpus of whatever
    the skeleton happened to draw.
    """
    # A SKELETON THAT GIVES UP RETURNS None, and that is a failed attempt, not a crash. Tightening
    # corridor_farthest's geometry made this reachable for the first time.
    if any(p is None for p in pairs):
        return False
    # CONTAMINATION IS A REJECTION, NOT A FOOTNOTE. The screen was printed at the end of a run and
    # nothing acted on it; a block whose grid is byte-identical to an evaluation grid is exactly
    # what must not leave here, and at these grid sizes a timid instance can collide by chance —
    # one did on the first verified 5961cc34 batch.
    for gi, go in pairs:
        if ghash(gi) in ev or ghash(go) in ev:
            return False
        if _relabel_canon(gi) in ev_canon or _relabel_canon(go) in ev_canon:
            return False
    # A PAIR THAT ANSWERS WITH ITS OWN INPUT TEACHES NOTHING, and one such pair spoils the block it
    # sits in. "The rule reproduces its output from its input" is trivially true when the rule did
    # nothing, so verification cannot see it and the block ships looking verified. Rejecting only
    # blocks that are identity THROUGHOUT is far too narrow: corpus-solvealike holds 71 identity
    # pairs, and 69 of them sit in 51 blocks that also carry real pairs. Redrawing is cheap --
    # VERIFY_TRIES gives each slot 40 independent attempts -- so one bad pair rejects the draw.
    if any(gi == go for gi, go in pairs):
        return False
    found = verifier(source)
    if found is None:
        return True
    kind, fn = found
    if kind == "verify_block":
        # THE WHOLE BLOCK AT ONCE. The role assignment is drawn once per block, so the last pair
        # is the test and the rest are the demos it has to follow from -- checking any pair on its
        # own would only ask whether the solver's DEFAULT roles happen to fit.
        task = {"train": [{"input": gi, "output": go} for gi, go in pairs[:-1]],
                "test": [{"input": pairs[-1][0], "output": pairs[-1][1]}]}
        try:
            return bool(fn(task))
        except Exception:
            return False
    for gi, go in pairs:
        try:
            ok = fn(gi, go) if kind == "verify" else (fn([r[:] for r in gi]) == go)
            if not ok:
                return False
        except Exception:
            return False
    return True


def pool_root():
    """Where the per-task directories live. One directory per SOURCE TASK, one problem per file."""
    return os.environ.get("NBR_OUT", os.path.join(HERE, "synthetic"))


def task_dir(source):
    return os.path.join(pool_root(), source)


def load_task_dir(source):
    """Every block already banked for this source, keyed by task id, from one file per block."""
    d = task_dir(source)
    out = {}
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json") or fn.startswith("_"):
            continue
        with open(os.path.join(d, fn)) as fh:
            block = json.load(fh)
        out[fn[:-5]] = block
    return out


_GATE_SHA = {}


def gate_sha(source=None):
    """sha256 over the gates that ADMITTED a block: the shared too_flat, in_grade_band and
    grade_band, plus this source's own BLOCK_GATES entry where it has one.

    A SHA SHOULD COVER EXACTLY THE THING IT NAMES, and skeleton_sha names what DREW a block. The
    gates are a different fact -- what ADMITTED it -- and one hash cannot carry both without lying
    about one of them. The reason it is the right shape is a result from two
    days ago: a whole-FILE sha would have marked e87109e9 and edb79dae stale when their function
    bodies had not moved, and forced two pointless regenerations. Reaching skeleton_sha into shared
    gates is that same over-scoping one level up -- it would restamp 46,000 blocks as stale over a
    change that touched no generator at all.

    So: two shas, each answering its own question, and neither restamping the other's blocks. What
    this buys concretely is that "which flatness bound screened this block" stops being recoverable
    only from the directory's builder_file_sha; two blocks carrying the same skeleton_sha may have
    been admitted under different bounds, and until now nothing on the block said so.
    """
    import inspect
    if _GATE_SHA.get(source) is None:
        parts = []
        for name in ("too_flat", "in_grade_band", "grade_band"):
            fn = getattr(nb, name, None)
            if fn is None:
                continue
            try:
                parts.append(inspect.getsource(fn))
            except Exception:
                pass
        # THE SOURCE'S OWN BLOCK GATE IS PART OF WHAT ADMITTED THE BLOCK, and nothing recorded it:
        # a pool built with a block gate and one built without carried the same gate_sha. It is
        # folded in PER SOURCE for the reason this hash is per-gate in the first place -- a gate
        # added for one task must not restamp every other task's blocks, and for a source with no
        # gate the hashed parts are unchanged, so no existing pool moves.
        gate = (getattr(nb, "BLOCK_GATES", {}) or {}).get(source)
        if gate is not None:
            try:
                parts.append(inspect.getsource(gate))
            except Exception:
                parts.append(repr(gate))
        # THE NUMBERS THE GATES COMPARE AGAINST ARE PART OF WHAT ADMITTED THE BLOCK. too_flat,
        # in_grade_band and grade_band are hashed above as source text, but the bounds they read
        # live in difficulty-anchors.json, so a regenerated anchor changed what was admitted while
        # this sha stood still, and two pools admitted under different bounds were indistinguishable
        # -- the screens could not tell them apart and nothing else recorded it either.
        #
        # Folded in PER SOURCE, like the block gate above and for the same reason: an anchor
        # recomputed for one task must not restamp every other task's blocks, which a whole-file
        # hash would do. Serialised with sorted keys and fixed separators, so a rewrite that only
        # reorders the file does not read as a change.
        anch = (nb.anchors() or {}).get(source)
        if anch is not None:
            parts.append(json.dumps(anch, sort_keys=True, separators=(",", ":")))
        _GATE_SHA[source] = (hashlib.sha256("".join(parts).encode()).hexdigest() if parts else None)
    return _GATE_SHA[source]


def skeleton_sha(source):
    """sha256 over the source text of BOTH halves of the admit path.

    The skeleton draws the board and the task's transform decides which draws are kept, so a change
    to either changes the population inside a directory. Hashing the skeleton alone would let a
    rule edit alter what is in a directory that still reports the same sha.
    """
    import inspect
    parts = []
    fn = nb.CLASS_B.get(source) or nb.CLASS_A.get(source)
    if fn is not None:
        try:
            parts.append(inspect.getsource(fn))
        except Exception:
            pass
    found = verifier(source)
    if found:
        try:
            parts.append(inspect.getsource(found[1]))
        except Exception:
            pass
    if not parts:
        return None
    return hashlib.sha256("".join(parts).encode()).hexdigest()


def file_sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def read_meta(source):
    p = os.path.join(task_dir(source), "_meta.json")
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p))
    except Exception:
        return None


def check_provenance(sources):
    """Report which sources will add blocks from a DIFFERENT skeleton than the ones already there.

    This used to refuse. Refusing was right while the pool was transient -- a directory holding
    instances from two skeleton versions with no way to tell them apart is worse than one that has
    to be rebuilt. It is wrong once the pool is training input, because data that has been trained
    on is not removed to make room for better data: a widened skeleton must ADD its blocks beside
    the old ones.

    What makes that safe is per-block provenance rather than per-directory. Every block records the
    skeleton that made it, so a directory may hold several versions and each block still says which
    one it came from. The refusal is replaced by a report.
    """
    mixed = []
    for src in sources:
        meta = read_meta(src)
        if meta is None:
            continue
        now = skeleton_sha(src)
        # THE BLOCKS SAY WHAT THEY CARRY; the meta's own skeleton_sha has named a version no block
        # held. skeleton_versions_present is the record, skeleton_sha the fallback.
        present = set((meta.get("skeleton_versions_present") or {}).keys()) or {meta.get("skeleton_sha")}
        present.discard(None)
        present.discard("unrecorded")
        if now and present and present != {now}:
            mixed.append((src, ",".join(v[:12] for v in sorted(present)), now[:12]))
    for src, was, now in mixed:
        print(f"  {src}: existing blocks built by {was}, this code is {now}")
    if mixed:
        # A TOP-UP AFTER A SKELETON CHANGE IS REFUSED, not reported. The report form left
        # 195c6913 as 852 blocks of one distribution and 200 of another under one directory,
        # and a rebuild is part of the fix: archive the directory and build
        # it from empty, the way rebuild-sha-11.sh does. NBR_ALLOW_BLEND=1 is the deliberate
        # override, and it has to be typed.
        if os.environ.get("NBR_ALLOW_BLEND") == "1":
            print(f"  {len(mixed)} directories will hold more than one skeleton version "
                  f"(NBR_ALLOW_BLEND=1); every block records its own.")
        else:
            sys.exit(f"REFUSED: {len(mixed)} task director{'y' if len(mixed) == 1 else 'ies'} "
                     f"already hold blocks from a different skeleton version. Archive to "
                     f"synthetic-archive/<task>-<why>-<date> and rebuild from empty, or set "
                     f"NBR_ALLOW_BLEND=1 to blend on purpose.")


def canon_block_key(block):
    """A colour- and orientation-blind key for a WHOLE block: the sorted canonical form of every
    input it contains.

    THE EXACT HASH CANNOT SEE A RECOLOURING. Two blocks that differ only by a relabelling of their
    colours, or by a dihedral view, hash differently and both bank. That is tolerable inside a
    training set and NOT tolerable between the training set and the holdout: a held-out problem
    that is a recolouring of a trained one measures memorisation rather than generalisation, and
    it would read as a clean generalisation score.
    """
    forms = sorted(repr(_relabel_canon(p["input"])) for p in block["train"] + block["test"])
    return hashlib.sha256("|".join(forms).encode()).hexdigest()


def crop_canon(g):
    """Canonical form of a grid AFTER cropping to the bounding box of its non-modal colour.

    TRANSLATION SURVIVES COLOUR AND ROTATION. _relabel_canon is blind to recolouring and to the
    eight dihedral views, and blind to nothing else -- the same shape drawn four columns to the
    right is a different form to it. Measured on this pool, cropping first roughly triples the
    matches on 88bcf3b4 (2 -> 17) and quintuples them on e12f9a14 (11 -> 52).
    """
    flat = [v for row in g for v in row]
    bg = max(set(flat), key=flat.count)
    pts = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v != bg]
    if not pts:
        return _relabel_canon(g)
    r0 = min(p[0] for p in pts); r1 = max(p[0] for p in pts)
    c0 = min(p[1] for p in pts); c1 = max(p[1] for p in pts)
    return _relabel_canon([row[c0:c1 + 1] for row in g[r0:r1 + 1]])


def holdout_dir(source):
    return os.path.join(task_dir(source), "_holdout")


def load_holdout(source):
    d = holdout_dir(source)
    out = {}
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if fn.endswith(".json") and not fn.startswith("_"):
            with open(os.path.join(d, fn)) as fh:
                out[fn[:-5]] = json.load(fh)
    return out


def block_hash(block):
    """Content hash of a whole block. Same form both lanes use, so the two agree:
    sha256 over json.dumps([train, test], sort_keys=True, separators=(",", ":"))."""
    return hashlib.sha256(json.dumps([block["train"], block["test"]], sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def pair_hash(pair):
    """Content hash of ONE pair, so a demonstration and a scored question are comparable.

    A DEMO-LEAK is one block's test pair appearing as a worked example in another: the answer to
    a scored question is shown, solved, somewhere else in the same task. block_hash cannot see it
    -- the two blocks differ everywhere else -- and test_hash cannot either, because the pair sits
    on the demo side of the other block."""
    return hashlib.sha256(json.dumps([pair["input"], pair["output"]], sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def test_hash(block):
    """Content hash of the SCORED PAIR alone, so two blocks posing one question are detectable.

    Deliberately not canonical: a relabelled or reflected question is a different question to a
    reader, and the canonical screen upstream is what refuses those against the benchmark. This
    asks only whether the identical pair has already been banked in this task."""
    return hashlib.sha256(json.dumps(block["test"], sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def emit(cls, source, per_grade=int(os.environ.get("NBR_PER_GRADE", "3")),
         demos=int(os.environ.get("NBR_DEMOS", "3")), seed0=880000):   # NBR_DEMOS: pairs before the test, for longer blocks
    """Bring one source UP TO per_grade blocks per grade. Idempotent. Never removes one.

    THE KNOB IS A TARGET, NOT AN INCREMENT. Two wrong versions came before this. The first wrote a
    fresh dict over the file, so re-running at a smaller number DELETED the tail — 2999 tasks became
    312 because someone changed a number and re-ran. The fix for that made it purely additive, which
    was worse in a quieter way: every rebuild bolted another full batch onto every rule already
    present, so six rebuilds took the original six rules to 3052 each while the newest sat at 500.
    Nobody asked for either number.

    So: count what each grade already has, generate only the shortfall, and number new blocks above
    the highest index present. Re-running with the same target does nothing. Raising it tops up.
    Lowering it does nothing rather than deleting, because deleting is what started this.
    """

    out = load_task_dir(source)
    kept = len(out)
    rejected = []
    REJECTED[source] = rejected
    created = set()
    CREATED[source] = created
    # PER-SLOT ATTEMPT COUNTS. A slot that agreed first try and a slot that needed twelve look
    # identical once banked, and the difference is the whole early warning: a skeleton that only
    # agrees with its own rule sometimes still fills the corpus, because retrying until agreement
    # banks exactly the subspace where it happens to be right. Every block stays individually
    # rule-true and the corpus is quietly biased anyway. High counts here say so at write time.
    tries = []
    ATTEMPTS[source] = tries
    # seeded from what is already on disk, so a top-up cannot re-emit a block this task already has
    seen_blocks = {block_hash(b) for b in out.values() if "train" in b}
    # AND THE SCORED QUESTION SEPARATELY, because block_hash covers the demos too: two blocks
    # carrying the SAME test pair with different demonstrations hash differently and both are
    # kept, so the corpus asks one question twice and scores it twice. That is the only
    # self-contamination category that corrupts a SCORE rather than diluting exposure.
    #
    # 97d7923e timid and aa4ec2a5 size, one each in 943 and 799 distinct questions -- a birthday
    # collision, not a narrow draw space, so no skeleton change prevents it and no rebuild clears
    # it: a slot's seed is fixed and reproduces the same pair.
    seen_tests = {test_hash(b) for b in out.values() if "test" in b}
    # AND EACH SIDE'S PAIRS, so a scored question cannot be banked as someone else's worked
    # example. 32 of those across the corpus before this, one or two per task at a repeat rate of
    # 0.02% to 0.09% -- chance rather than a narrow draw space, which is why no skeleton change
    # prevented them and no rebuild cleared them.
    seen_test_pairs = {pair_hash(p) for b in out.values() if "test" in b for p in b["test"]}
    seen_demo_pairs = {pair_hash(p) for b in out.values() if "train" in b for p in b["train"]}

    # THE SCREEN HAS TO RUN BOTH WAYS, AND IT RAN ONE. A held-out block is drawn to be canonically
    # unlike everything in training AT THE MOMENT IT IS DRAWN -- and then a later top-up adds fresh
    # training blocks that nothing screens against the holdout, so training walks into a held-out
    # input from the other side. e12f9a14 leaked exactly this way: two pairs of a size holdout
    # block, clean when written, matched training blocks added to that directory hours afterwards.
    # The holdout is the fixed reference and training is what moves, so training is what gives way.
    _prior_hold = load_holdout(source)
    hold_canon = {crop_canon(p["input"]) for b in _prior_hold.values() if "train" in b
                  for p in b["train"] + b["test"]}

    # continue numbering above whatever is already banked, so new blocks cannot collide with or
    # silently replace an existing task id
    used = []
    for tid in out:
        tail = tid.rsplit("_", 1)[-1]
        if tail.isdigit():
            used.append(int(tail))
    base = max(used) if used else 0

    have = {g: 0 for g in nb.GRADES}
    for tid in out:
        parts = tid.rsplit("_", 2)
        if len(parts) == 3 and parts[1] in have:
            have[parts[1]] += 1

    # DETERMINISTIC SLOTS, so a rejected one stays rejected instead of being retried with a fresh
    # seed on every run. Counting successes and generating "the shortfall" looks idempotent and is
    # not: a generator that cannot fill a grade drifts up by a few blocks every single run. Here a
    # slot's seed comes from its own index, so re-running reproduces the same rejections and adds
    # nothing.
    for grade in nb.GRADES:
        for k in range(per_grade):
            if have[grade] >= per_grade:
                break
            tid = f"nbr{cls}_{source}_{grade}_s{k:04d}"
            if tid in out:
                continue
            # sha256, not hash(): str hashing is salted per process, so hash() would give this
            # slot a different seed on every run and defeat the whole point of a fixed slot.
            #
            # A SKELETON RETURNS ONE PAIR PER CALL, so a block is demos+1 calls at distinct seeds.
            # The line that did this was missing and the builder raised NameError on the first
            # block it tried to make — which is why every one of the 72,489 banked blocks carries
            # a pre-fix id and not one carries this version's. "Three runs, delta 0" was a builder
            # that could not generate, not an idempotent one.
            #
            # THE PAIRS ARE VERIFIED BEFORE THE BLOCK IS KEPT. A skeleton is a CLAIM about what its
            # source task does; a wrong claim trains the model confidently on a rule the benchmark
            # does not contain, which is worse than no data. The admitted generator in generators/
            # is the check: a variant is right iff that generator reproduces its output from its
            # input. A slot whose attempts all fail stays empty and stays empty on re-runs, because
            # every seed here is derived, not drawn.
            have[grade] += 1
            pairs = None
            for attempt in range(VERIFY_TRIES):
                cand = [nb.build(cls, source, grade, slot_seed(cls, source, grade, k, attempt, j))
                        for j in range(demos + 1)]
                if not verifies(source, cand):
                    continue
                block = {"train": [{"input": a, "output": b} for a, b in cand[:-1]],
                         "test": [{"input": cand[-1][0], "output": cand[-1][1]}]}
                # A DUPLICATE BLOCK COSTS A SLOT AND TEACHES NOTHING THE FIRST COPY DID NOT.
                # Every pair in it verifies, so nothing upstream objects: 50 of 9bbf930d's 300
                # blocks were exact copies of each other and 12 of a47bf94d's. Redraw instead.
                # EXACT HASH ONLY IN THE TRAINING LOOP. The canonical key costs eight dihedral
                # rotations of every input in every candidate, and with up to 250 verify tries a
                # slot that is 170,000 canonicalisations for one task -- it took a five-task
                # rebuild from minutes to over an hour and a half. It buys little here: two
                # training blocks that differ only by a recolouring are wasteful, not harmful.
                # Where it is load-bearing is the HOLDOUT, which must not be a recolouring of
                # anything trained on, and it is still applied there.
                if block_hash(block) in seen_blocks:
                    continue
                if test_hash(block) in seen_tests:
                    continue                      # this scored question is already banked
                if any(pair_hash(p) in seen_demo_pairs for p in block["test"]):
                    continue                      # its answer is a worked example elsewhere
                if any(pair_hash(p) in seen_test_pairs for p in block["train"]):
                    continue                      # it would demonstrate a banked question
                # the one canonical check the training loop does pay for: not against the other
                # training blocks, which is merely wasteful, but against the HOLDOUT, where a
                # collision destroys the measurement the holdout exists to make
                if hold_canon and any(crop_canon(p["input"]) in hold_canon
                                      for p in block["train"] + block["test"]):
                    continue
                pairs = cand
                break
            tries.append(attempt + 1 if pairs is not None else VERIFY_TRIES)
            if pairs is None:
                rejected.append(tid)
                continue
            out[tid] = {"train": [{"input": a, "output": b} for a, b in pairs[:-1]],
                        "test": [{"input": pairs[-1][0], "output": pairs[-1][1]}]}
            seen_blocks.add(block_hash(out[tid]))
            seen_tests.add(test_hash(out[tid]))
            seen_test_pairs.update(pair_hash(p) for p in out[tid]["test"])
            seen_demo_pairs.update(pair_hash(p) for p in out[tid]["train"])
            # Exemptions ride on EVERY BLOCK, not as a top-level key. A top-level "_meta" entry
            # sits in the same map as the tasks, so every reader that iterates the batch and
            # reaches for ["train"] would crash on it — including three scripts in this tree. A
            # sibling key beside train/test is invisible to those readers and still travels with
            # the data.
            # EVERY BLOCK RECORDS THE SKELETON THAT MADE IT. A sibling key beside train/test is
            # invisible to readers that iterate the batch and reach for ["train"], and it is what
            # lets one directory hold instances from several skeleton versions without losing
            # track of which is which.
            out[tid]["_skeleton_sha"] = skeleton_sha(source)
            out[tid]["_gate_sha"] = gate_sha(source)
            created.add(tid)
            m = nb.SKELETON_META.get(source)
            if m:
                out[tid]["_meta"] = dict(m, source_task=source, skeleton=cls)

    # THE HOLDOUT IS GENERATED WITH THE TASK, NOT CARVED OUT OF A CURRICULUM. A holdout cut per
    # run differs from run to run, so two runs' per-task losses would be measured against two
    # different yardsticks and could not be compared -- which is the whole point of having one.
    # Generated here it is the same yardstick for every run that ever touches this task.
    #
    # DRAWN LAST, AND CANONICALLY DISTINCT FROM EVERY TRAINING BLOCK ALREADY BANKED. seen_canon
    # carries the whole training set by this point, so a held-out block cannot be a recolouring or
    # a turn of one the model trained on -- which would measure memorisation and read as
    # generalisation.
    # THE GATE IS AT PAIR LEVEL, NOT BLOCK LEVEL. A block-wide key asks whether the SET of four
    # inputs has been seen jointly, and a block needs only one fresh input to be novel as a set
    # while its other three are recall. The model trains on individual demonstration pairs, so the
    # pair is the level that matters. Measured before this changed: 19 tasks leaked at pair
    # level while every one of them reported zero block-level overlap -- 8b7bacbf had all 32 of
    # its held-out inputs already in training, 27 of them byte-identical.
    # CROP-NORMALISATION IS RIGHT FOR MOST MECHANICS AND WRONG FOR SOME, and where it is wrong the
    # symptom is indistinguishable from a narrow generator: the holdout simply never fills. For a
    # mechanic whose answer depends on where a figure sits relative to the frame -- a bloom
    # unwinding, anything reflecting or wrapping at an edge -- the position IS the content, and
    # cropping to the bounding box deletes exactly the thing that varies. Measured here rather than
    # assumed: 8b7bacbf's 1057 canonical forms collapse to 35 under the crop, so gating on it would
    # reject every possible holdout forever and no widening of the generator would help.
    ins = [p["input"] for b in out.values() if "train" in b for p in b["train"] + b["test"]]
    plain = {_relabel_canon(g) for g in ins}
    cropped = {crop_canon(g) for g in ins}
    use_crop = not plain or len(cropped) >= len(plain) / 5
    if not use_crop:
        print(f"  {source}: crop-normalisation collapses {len(plain)} canonical forms to "
              f"{len(cropped)}; position is content here, so the crop key is not used")
    key = crop_canon if use_crop else _relabel_canon
    train_inputs = {key(p["input"])
                    for b in out.values() if "train" in b
                    for p in b["train"] + b["test"]}
    held = _prior_hold
    fresh = set()
    HOLDOUT[source] = (held, fresh)
    htries = {"budget_per_slot": VERIFY_TRIES, "filled": {}, "exhausted": [], "intended": 0}
    HOLDOUT_TRIES[source] = htries
    hold_n = int(os.environ.get("NBR_HOLDOUT_PER_GRADE", "0"))
    # carried out to the write pass, which is a different scope: what this run ASKED FOR is not
    # otherwise visible there, and deriving it from what landed is exactly the thing that made a
    # short holdout indistinguishable from a complete one
    htries["intended"] = hold_n * len(nb.GRADES)
    if hold_n:
        have_h = {g: 0 for g in nb.GRADES}
        for tid in held:
            parts = tid.rsplit("_", 2)
            if len(parts) == 3 and parts[1] in have_h:
                have_h[parts[1]] += 1
        for grade in nb.GRADES:
            for k in range(hold_n):
                if have_h[grade] >= hold_n:
                    break
                tid = f"nbr{cls}_{source}_{grade}_h{k:04d}"
                if tid in held:
                    continue
                have_h[grade] += 1
                pairs = None
                used = 0
                for attempt in range(VERIFY_TRIES):
                    used = attempt + 1
                    cand = [nb.build(cls, source, grade,
                                     slot_seed(cls, source, grade, 9000 + k, attempt, j))
                            for j in range(demos + 1)]
                    if not verifies(source, cand):
                        continue
                    block = {"train": [{"input": a, "output": b} for a, b in cand[:-1]],
                             "test": [{"input": cand[-1][0], "output": cand[-1][1]}]}
                    if block_hash(block) in seen_blocks:
                        continue
                    if test_hash(block) in seen_tests:
                        continue                  # this scored question is already banked
                    if any(pair_hash(p) in seen_demo_pairs for p in block["test"]):
                        continue                  # its answer is a worked example elsewhere
                    if any(pair_hash(p) in seen_test_pairs for p in block["train"]):
                        continue                  # it would demonstrate a banked question
                    if any(key(p["input"]) in train_inputs
                           for p in block["train"] + block["test"]):
                        continue
                    pairs = cand
                    break
                if pairs is None:
                    htries["exhausted"].append(tid)
                    continue
                htries["filled"][tid] = used
                held[tid] = {"train": [{"input": a, "output": b} for a, b in pairs[:-1]],
                             "test": [{"input": pairs[-1][0], "output": pairs[-1][1]}]}
                seen_blocks.add(block_hash(held[tid]))
                seen_tests.add(test_hash(held[tid]))
                seen_test_pairs.update(pair_hash(p) for p in held[tid]["test"])
                seen_demo_pairs.update(pair_hash(p) for p in held[tid]["train"])
                # a held-out block also becomes part of what later holdout draws must avoid
                for p in held[tid]["train"] + held[tid]["test"]:
                    train_inputs.add(key(p["input"]))
                held[tid]["_skeleton_sha"] = skeleton_sha(source)
                held[tid]["_gate_sha"] = gate_sha(source)
                fresh.add(tid)
                m = nb.SKELETON_META.get(source)
                if m:
                    held[tid]["_meta"] = dict(m, source_task=source, skeleton=cls)
    return out

if __name__ == "__main__":
    OUT = os.environ.get("NBR_OUT", "probes-nbr")
    os.makedirs(OUT, exist_ok=True)
    batches = {}
    # CLASS A IS RETIRED, 2026-08-31: drop the no-solve-alikes and generate more of the solve
    # alikes." Class A derived from no-candidate tasks; Class B derives from near-misses, which is
    # the population that can actually convert. The five nbrA_*.json already on disk are left where
    # they are rather than deleted — they are measured artifacts and deleting them is a
    # separate decision — but nothing rebuilds them.
    #
    # Sources are read from neighborhoods.CLASS_B rather than listed here, so adding a skeleton
    # cannot silently fail to produce a batch. That is exactly what happened when 62593bfd and
    # 3dc255db were registered and this loop kept emitting the original two.
    wanted = sorted(nb.CLASS_B)
    # NBR_ONLY narrows a run to named sources. The default stays "everything in CLASS_B" for the
    # reason above; this is opt-in, it is reported, and a name that is not a registered source is
    # a hard failure rather than a silently empty run.
    only = [x for x in os.environ.get("NBR_ONLY", "").replace(",", " ").split() if x]
    if only:
        unknown = [x for x in only if x not in nb.CLASS_B]
        if unknown:
            raise SystemExit("NBR_ONLY names sources with no skeleton: " + " ".join(unknown))
        wanted = sorted(set(only))
        print(f"  NBR_ONLY: building {len(wanted)} of {len(nb.CLASS_B)} sources — "
              + " ".join(wanted))
    # EVERY SOURCE IS CHECKED BEFORE THE FIRST WRITE. See check_provenance.
    check_provenance(wanted)
    for src in wanted:
        batches[src] = emit("B", src)

    print("== neighbourhood pool ==  one directory per source task, one problem per file")
    total = 0
    for src, b in batches.items():
        d = task_dir(src)
        os.makedirs(d, exist_ok=True)
        hits = sum(1 for t in b.values() for p in t["train"] + t["test"]
                   if ghash(p["input"]) in ev or ghash(p["output"]) in ev)
        grades = {}
        for tid in b:
            grades[tid.split("_")[2]] = grades.get(tid.split("_")[2], 0) + 1
        # ONLY THE BLOCKS THIS RUN MADE ARE WRITTEN. Writing the whole batch reopened every
        # block already on disk in "w" mode and wrote it back. The bytes came out identical --
        # they were loaded from those same files and json.dump reproduces them -- so the hashes
        # still matched and nothing looked wrong, but 14,100 files that no one asked to change
        # were rewritten three times in one day and every mtime moved. A harness does not touch
        # existing tests. Removing or replacing them is a decision someone makes on purpose, not
        # something a write loop does on the way past.
        fresh = CREATED.get(src, set())
        for tid in fresh:
            with open(os.path.join(d, f"{tid}.json"), "w") as fh:
                json.dump(b[tid], fh)
        # the holdout writes into its own subdirectory, and only what this run made. A directory
        # never matches a *.json filter and every curriculum reader skips names starting with an
        # underscore, so these blocks cannot reach a training set through any cut -- they are
        # reachable only by being asked for by path.
        held, hfresh = HOLDOUT.get(src, ({}, set()))
        if hfresh:
            hd = holdout_dir(src)
            os.makedirs(hd, exist_ok=True)
            for tid in hfresh:
                with open(os.path.join(hd, f"{tid}.json"), "w") as fh:
                    json.dump(held[tid], fh)
        versions = {}
        gates = {}
        for block in b.values():
            k = block.get("_skeleton_sha") or "unrecorded"
            versions[k] = versions.get(k, 0) + 1
            g = block.get("_gate_sha") or "unrecorded"
            gates[g] = gates.get(g, 0) + 1
        # THE RECORD NAMES WHAT IS IN THE DIRECTORY, NOT WHAT THE CODE CURRENTLY SAYS.
        #
        # emit() is a top-up: it generates only the shortfall. Run against a full directory after a
        # skeleton change it generates NOTHING and still reached here, where skeleton_sha was
        # stamped from current code -- so the pool advertised a version none of its blocks carried.
        # d59b0160 read skeleton_sha 36bbb380 beside skeleton_versions_present {250ec41e: 1200}.
        #
        # Where a top-up DID generate it is worse: four pools hold blocks from two to four
        # versions and _meta named the NEWEST every time. 195c6913 advertised f4c14413 while 852
        # of its 1,052 blocks carry ef0e32af and draw half the ink. The record named the minority.
        code_sha = skeleton_sha(src)
        present = max(versions, key=lambda k: (versions[k], k == code_sha)) if versions else code_sha
        if present != code_sha:
            print(f"  {src}: skeleton_sha names the blocks, not the code — "
                  f"blocks {present[:8]} x{versions[present]} of {sum(versions.values())}, "
                  f"code {code_sha[:8]}")
        if len(versions) > 1:
            print(f"  {src}: MIXED SKELETON VERSIONS — "
                  + ", ".join(f"{k[:8]} x{n}" for k, n in sorted(versions.items(),
                                                                 key=lambda kv: -kv[1])))
        meta = {"source": src,
                "lane": "band90",
                "skeleton": getattr(nb.CLASS_B.get(src), "__name__", None),
                "skeleton_sha": present,
                "skeleton_sha_code": code_sha,
                "skeleton_versions_present": versions,
                "gate_sha": gate_sha(src),
                "gate_versions_present": gates,
                "builder_file_sha": file_sha(os.path.join(HERE, "neighborhoods.py")),
                "grades": grades}
        if held:
            hg = {}
            for tid in held:
                parts = tid.rsplit("_", 2)
                if len(parts) == 3:
                    hg[parts[1]] = hg.get(parts[1], 0) + 1
            # THE INTENDED COUNT BESIDE THE ACTUAL. A short holdout and a complete one look
            # identical from outside: nothing on disk says whether 8 blocks is the whole quota or
            # a quarter of it, so a reader checking the pool has to invent the target. A check
            # that did so derived it from block depth and got a nonsense "67 tasks short". It is the
            # same class of gap as retry cost reading as unattempted. Recorded as what this run
            # ASKED FOR, carried forward at its high-water mark so a later top-up that asks for
            # less cannot quietly shrink the target it is measured against.
            prev_int = ((read_meta(src) or {}).get("holdout") or {}).get("intended") or 0
            meta["holdout"] = {"dir": "_holdout", "blocks": len(held), "grades": hg}
            want_h = max(prev_int, (HOLDOUT_TRIES.get(src) or {}).get("intended", 0))
            if want_h:
                # a run that asks for no holdout at all must not record a target of zero
                meta["holdout"]["intended"] = want_h
            # WHAT THE SHORTFALL COST, CARRIED FORWARD ACROSS RUNS. A run at 40 draws a slot and a
            # run at 2,500 both end with the same empty slot, and only the number says which of the
            # two happened. The highest budget any run has spent on this source is kept, so raising
            # the budget records the raise and a later cheap run cannot erase it.
            ht = HOLDOUT_TRIES.get(src) or {}
            prev = ((read_meta(src) or {}).get("holdout") or {}).get("tries") or {}
            if ht.get("filled") or ht.get("exhausted") or prev:
                budget = max(ht.get("budget_per_slot", 0), prev.get("budget_per_slot", 0))
                filled = dict(ht.get("filled") or {})
                # A SLOT THAT HAS SINCE FILLED IS NOT STILL EXHAUSTED. Carrying the previous
                # run's list forward wholesale left 5545f144 reporting two exhausted size slots on
                # the very run that filled them, which is the opposite of what this record is for.
                stuck = set(ht.get("exhausted") or [])
                stuck |= set(prev.get("slots_that_exhausted_the_budget") or [])
                stuck -= set(held)
                meta["holdout"]["tries"] = {
                    "budget_per_slot": budget,
                    # the highest attempt count ANY run has needed here, not just this one's:
                    # a later cheap top-up that fills nothing must not erase what the hard run cost
                    "worst_slot_filled_at": max([prev.get("worst_slot_filled_at", 0)]
                                                + list(filled.values())),
                    "slots_that_exhausted_the_budget": sorted(stuck),
                }
        was = read_meta(src)
        drift = ""
        if was and was.get("builder_file_sha") not in (None, meta["builder_file_sha"]):
            # REPORTED, NOT REFUSED. The file moving says something else in it changed; only the
            # skeleton's own source says this directory's population would change.
            drift = "  builder-file drift"
        # the index is rewritten only when it would actually differ, so a run that generates
        # nothing leaves the directory alone entirely rather than restamping every _meta.json
        mpath = os.path.join(d, "_meta.json")
        blob = json.dumps(meta, indent=2)
        if not os.path.exists(mpath) or open(mpath).read() != blob:
            with open(mpath, "w") as fh:
                fh.write(blob)
        rej = len(REJECTED.get(src, []))
        gate = "gated" if verifier(src) else "UNGATED (no generator)"
        tr = ATTEMPTS.get(src) or []
        first = sum(1 for t in tr if t == 1)
        agree = f"  first-try {first}/{len(tr)} max {max(tr)}" if tr else ""
        total += len(b)
        print(f"  {src:<10} {len(b):>4} blocks  grades {grades}  copied-content {hits}  "
              f"{gate}{f', {rej} slots failed verify' if rej else ''}{agree}{drift}")
    print(f"\n  {len(batches)} task directories, {total} blocks, under {pool_root()}")
    # SILENCE MUST NOT PRESENT AS SUCCESS. A run that enumerated nothing, or a source that ended
    # with no blocks at all, prints a tidy summary and exits 0 -- which reads as a clean corpus
    # having read one. Both are failures and say so in the exit code.
    empty = sorted(src for src, b in batches.items() if not b)
    if not batches or total == 0:
        raise SystemExit("FAILED: no blocks were read or written; "
                         f"nothing under {pool_root()} matched a known source")
    if empty:
        raise SystemExit(f"FAILED: {len(empty)} source(s) hold no blocks at all: "
                         + " ".join(empty))
    print("  copied-content counts BYTE matches; the canonical screen inside ok() is what rejects "
          "a source grid turned, mirrored or recoloured, and it rejects rather than reports.")
