# Rule authored from the evaluation demonstrations of 332f06d7.
#
# A block of 0s sits inside a snaking corridor of 1s cut through a wall of 3s. The block SLIDES
# along the corridor and stops at the END OF THE CORRIDOR — the placement reachable from its
# start that is farthest away in slide-steps. The cells it vacates become corridor.
#
# THE 2-BLOCK IS NOT A DESTINATION MARKER, and reading it as one is what stalled this task. It is
# the same size as the hole and it sits at a corridor end, so in demos 0 and 3 the hole lands on
# it and consumes it — which looks like "travel to the 2". In demos 1, 2 and the test the 2 sits
# in a DIFFERENT corridor component the hole cannot reach at all, and it survives untouched. Its
# only role is decorative once the hole's own bounding box gives the block size.
#
# Farthest-placement is exact and unambiguous on every pair: the maximising placement is unique
# in all five (max slide-distance 24, 13, 14, 21, 37) with no tie to break.
from collections import Counter, deque


def transform(grid):
    h, w = len(grid), len(grid[0])
    out = [row[:] for row in grid]

    # The wall is the colour that frames the grid; the corridor is the commonest colour that is
    # not wall. Neither is hardcoded because demo 2's grid holds MORE 1s than 3s, so "commonest
    # colour is the background" reads the corridor as the wall and finds no corridor at all.
    border = ([grid[0][c] for c in range(w)] + [grid[h - 1][c] for c in range(w)] +
              [grid[r][0] for r in range(h)] + [grid[r][w - 1] for r in range(h)])
    wall = Counter(border).most_common(1)[0][0]
    fill = Counter(v for row in grid for v in row if v != wall).most_common(1)[0][0]

    # THE HOLE AND THE SIZE KEY ARE THE SAME SIZE, so counting cannot tell them apart. What does:
    # the key is stuck to the edge of the board in every pair and the hole never is. Board and
    # corridor are read off too -- the board is the border's own colour (NOT the commonest: the
    # corridor outweighs it in demo 2 and the test), and the corridor is the commonest of the rest.
    small = [v for v in {x for row in grid for x in row} if v not in (wall, fill)]
    HOLE = next((v for v in small
                 if not any(grid[r][c] == v for r in range(h) for c in range(w)
                            if r in (0, h - 1) or c in (0, w - 1))), None)
    if HOLE is None:
        return out
    hole = [(r, c) for r in range(h) for c in range(w) if grid[r][c] == HOLE]
    if not hole:
        return out
    r0 = min(r for r, _ in hole)
    c0 = min(c for _, c in hole)
    bh = max(r for r, _ in hole) - r0 + 1
    bw = max(c for _, c in hole) - c0 + 1

    def fits(r, c):
        return (0 <= r and 0 <= c and r + bh <= h and c + bw <= w and
                all(grid[rr][cc] != wall
                    for rr in range(r, r + bh) for cc in range(c, c + bw)))

    placements = {(r, c) for r in range(h) for c in range(w) if fits(r, c)}

    # Slide one cell at a time, four ways, staying wholly inside the corridor.
    dist = {(r0, c0): 0}
    q = deque([(r0, c0)])
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (r + dr, c + dc)
            if n in placements and n not in dist:
                dist[n] = dist[(r, c)] + 1
                q.append(n)

    dr0, dc0 = max(dist, key=lambda p: dist[p])

    for r, c in hole:
        out[r][c] = fill
    for r in range(dr0, dr0 + bh):
        for c in range(dc0, dc0 + bw):
            out[r][c] = HOLE
    return out


def _stops_short(gi):
    """Does a NECK stop the block short of corridor it is otherwise connected to?

    NOT the same as "corridor the block cannot cover". A dead-end pocket narrower than the block
    holds no placement at all and stops nothing; the block was never going there. A STOPPING neck
    is where a placement that WOULD fit, and whose cells are corridor-connected to the block's own,
    cannot be slid to. That is the only case where "slide until it jams" and "redraw it at the far
    end" give different answers, so it is the only case a reader can learn the difference from.
    """
    h, w = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    wall = max(tally, key=lambda k: tally[k])
    host = {(y, x) for y in range(h) for x in range(w) if gi[y][x] != wall}
    rest = [c for c in tally if c != wall]
    if not rest:
        return False
    corr = max(rest, key=lambda c: tally[c])
    holes = [c for c in rest if c != corr]
    if not holes:
        return False
    block = min(holes, key=lambda c: tally[c])
    cells = [(y, x) for y in range(h) for x in range(w) if gi[y][x] == block]
    if not cells:
        return False
    bs = max(y for y, _ in cells) - min(y for y, _ in cells) + 1
    if bs < 1 or len(cells) != bs * bs:
        return False
    start = (min(y for y, _ in cells), min(x for _, x in cells))
    fits = {(y, x) for y in range(h) for x in range(w)
            if all((y + a, x + b) in host for a in range(bs) for b in range(bs))}
    if start not in fits:
        return False
    seen, q = {start}, [start]
    while q:
        cur = q.pop(0)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (cur[0] + dy, cur[1] + dx)
            if n in fits and n not in seen:
                seen.add(n)
                q.append(n)
    conn, cq = set(cells), list(cells)
    while cq:
        cur = cq.pop(0)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (cur[0] + dy, cur[1] + dx)
            if n in host and n not in conn:
                conn.add(n)
                cq.append(n)
    for p in fits - seen:
        if all((p[0] + a, p[1] + b) in conn for a in range(bs) for b in range(bs)):
            return True
    return False


def verify_block(task):
    """Every pair reproduced, AND no block that hides the mechanic in its answer.

    A TRAP BLOCK is one whose TEST pair turns on a stopping neck while none of its demos carries
    one. A reader given three neck-free demos can infer "redraw the block at the far end of the
    corridor", which fits all three, and is then wrong on a test where the block jams short -- and
    the distinction appears only in the answer they cannot see. Refusing the BLOCK rather than the
    board is what this contract is for: the source itself necks 2 of its 5 pairs, so demos can and
    should carry them.
    """
    pairs = [(p["input"], p["output"]) for p in task["train"]]
    pairs += [(p["input"], p["output"]) for p in task["test"]]
    for gi, go in pairs:
        try:
            if transform([r[:] for r in gi]) != go:
                return False
        except Exception:
            return False
    if _stops_short(pairs[-1][0]) and not any(_stops_short(gi) for gi, _ in pairs[:-1]):
        return False
    return True
