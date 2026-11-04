"""269e22fb -- the fragment is a window on the whole motif.

One asymmetric motif runs through every pair of the task; a pair shows a
fragment of it in one of the eight orientations, and the answer is that same
motif whole, in that same orientation.

No rule maps a fragment to the whole, so there is nothing to solve pair by pair
-- the motif is a PARAMETER of the task, not something derivable from one pair.
What IS checkable here is the relation: the fragment must be a genuine window of
the answer, in register, and the answer must be more than the fragment handed
back.  The cross-pair half -- that every pair's answer is the same motif under a
dihedral turn -- can only be gated on the whole task at once, and that gate is
`verify_fragment_source` in midband.py, which owns this source.

"""


def verify(gi, go):
    h, w = len(gi), len(gi[0])
    H, W = len(go), len(go[0])
    if h > H or w > W:
        return False
    if h == H and w == W:
        return False                       # an answer that just echoes the fragment
    return any(all(go[r + i][c + j] == gi[i][j] for i in range(h) for j in range(w))
               for r in range(H - h + 1) for c in range(W - w + 1))


# block-level gate for the stagers (lora-stage.py / crucible-small-pool-verify.py prefer verify_block > verify > transform).
# verify() above is the pair-level half only: a corrupted cell OUTSIDE the fragment's window passes it. The whole-task half -- every
# answer is one dihedral image of the first on a two-colour palette -- is midband.verify_fragment_source, which owns this source.
import importlib.util as _ilu, os as _os
_p = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "midband.py")
_s = _ilu.spec_from_file_location("_mb_269e22fb", _p)
_m = _ilu.module_from_spec(_s); _s.loader.exec_module(_m)


def verify_block(task):
    pairs = list(task.get("train", [])) + [p for p in task.get("test", []) if p.get("output")]
    if not pairs or not all(verify(p["input"], p["output"]) for p in pairs):
        return False
    return bool(_m.verify_fragment_source({"train": task.get("train", []), "test": [p for p in task.get("test", []) if p.get("output")]}))
