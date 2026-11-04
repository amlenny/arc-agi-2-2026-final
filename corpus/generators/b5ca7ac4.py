"""b5ca7ac4 -- the crates slide to the wall their frame belongs to.

Every crate is 5x5: a one-cell frame round a 3x3 core.  Frames of 8 belong at
the left wall, frames of 2 at the right.  Each crate slides straight along its
own rows until it meets the wall or the back of a crate already parked there;
it never changes row.  The crate nearest its wall parks first.
"""
import itertools

# EACH WALL IS NAMED BY ITS FRAME COLOUR, and which colour names which wall is a CONVENTION THE
# BLOCK CARRIES, not a fact about any one grid. The two frame colours have congruent cell sets, so
# no shape-intrinsic feature separates them, and position does not either. Measured on all four
# pairs:
#   mean column of each colour's crates        right on demos 1 and 2, wrong on demo 0 and the test
#   leftmost crate of each colour              wrong on demo 0 and demo 2
#   frame of the first crate in reading order  2, 2, 2, 8 while the left wall is 8 every time
#   core colours grouped by frame              no pattern; demo 2's 8-crates hold 2-coloured cores
#   cell conservation under the swap           both assignments conserve exactly
#
# THAT IS NOT AN IMPOSSIBILITY, IT IS THE WRONG QUESTION. A solver handed a single grid cannot
# recover the assignment and never could; a solver handed the BLOCK can read it straight off any
# demo's answer -- the frame colour of the crates parked against the left wall IS the left colour.
# So the roles are arguments with the task's own values as defaults, and verify_block below
# recovers them from the demos and then requires the test to follow.
LEFT, RIGHT = 8, 2


def transform(gi, left=LEFT, right=RIGHT):
    H, W = len(gi), len(gi[0])
    flat = [v for row in gi for v in row]
    bg = max(set(flat), key=flat.count)

    crates = []
    for r in range(H - 4):
        for c in range(W - 4):
            ring = {gi[r + a][c + b] for a in range(5) for b in range(5)
                    if a in (0, 4) or b in (0, 4)}
            core = {gi[r + a][c + b] for a in (1, 2, 3) for b in (1, 2, 3)}
            if len(ring) == 1 and len(core) == 1 and bg not in ring | core and ring != core:
                crates.append((r, c, ring.pop(), core.pop()))

    go = [[bg] * W for _ in range(H)]
    for wall in (left, right):
        mine = [k for k in crates if k[2] == wall]
        mine.sort(key=lambda k: k[1], reverse=(wall == right))
        parked = []
        for r, c, ring, core in mine:
            lane = range(W - 5, -1, -1) if wall == right else range(W - 4)
            for x in lane:
                if all(not (abs(r - pr) < 5 and abs(x - px) < 5) for pr, px in parked):
                    parked.append((r, x))
                    for a in range(5):
                        for b in range(5):
                            go[r + a][x + b] = ring if a in (0, 4) or b in (0, 4) else core
                    break
    return go


def _palette(task):
    """Colours present in the block. The roles are drawn from these, so enumerating the block's own
    colours is narrower than a fixed palette and stays correct if the palette changes."""
    seen = set()
    for p in task.get("train", []) + task.get("test", []):
        for g in (p.get("input"), p.get("output")):
            for row in g or []:
                seen.update(row)
    return sorted(seen)


def _fits(pairs, roles):
    for p in pairs:
        try:
            if transform([r[:] for r in p["input"]], *roles) != p["output"]:
                return False
        except Exception:
            return False
    return True


def verify_block(task):
    """BLOCK-LEVEL. Which frame colour parks at which wall is drawn once per block, so it cannot be
    checked one pair at a time. Every assignment consistent with all the demos must also reproduce
    the test: ambiguity is a failure, not a pass -- if two assignments fit the demos and disagree
    on the test, the answer is not determined by the block."""
    demos = task.get("train", [])
    tests = [p for p in task.get("test", []) if p.get("output")]
    if not demos or not tests:
        return False
    fits = [c for c in itertools.permutations(_palette(task), 2) if _fits(demos, c)]
    if not fits:
        return False
    return all(_fits(tests, c) for c in fits)
