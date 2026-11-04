"""lineage_canon.py -- block hashes for the lineage index.
raw_hash(d)   = the builders' content hash: sha256 of {"train", "test"} with sort_keys (crucible-pick-120-blocks.py ch()).
canon_hash(d) = view-invariant: the same for every dihedral view, colour permutation and demo order of a block (the packer's and
                the curricula's transforms). Per dihedral: transform every grid, order the demos by their own colour-anonymous form,
                then renumber colours over the whole block (demos, then test) by first appearance; the smallest form over the 8.
"""
import hashlib, json
D8 = [lambda g: g, lambda g: [list(r) for r in zip(*g[::-1])], lambda g: [r[::-1] for r in g[::-1]],
      lambda g: [list(r) for r in zip(*g)][::-1], lambda g: [r[::-1] for r in g], lambda g: g[::-1],
      lambda g: [list(r) for r in zip(*g)], lambda g: [list(r)[::-1] for r in zip(*g)][::-1]]


def raw_hash(d):
    return hashlib.sha256(json.dumps({"train": d["train"], "test": d["test"]}, sort_keys=True).encode()).hexdigest()


def _relabel(grids):
    m = {}; out = []
    for g in grids:
        out.append(tuple(tuple(m.setdefault(v, len(m)) for v in r) for r in g))
    return tuple(out)


def canon_hash(d):
    best = None
    pairs = [(p["input"], p["output"]) for p in d["train"]]; tests = [(p["input"], p["output"]) for p in d["test"]]
    for t in D8:
        tp = [(t(i), t(o)) for i, o in pairs]; tt = [(t(i), t(o)) for i, o in tests]
        tp.sort(key=lambda p: _relabel(p))
        form = (len(tp), _relabel([g for p in tp + tt for g in p]))
        if best is None or form < best: best = form
    return hashlib.sha256(repr(best).encode()).hexdigest()
