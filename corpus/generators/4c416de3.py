# Rule authored from the evaluation demonstrations of 4c416de3.
#
# Each grid holds black rectangular FRAMES, lone coloured dots sitting diagonally inside a corner,
# and exactly ONE completed example — a cluster wrapped around one corner. That cluster is the
# TEMPLATE, and every lone dot is expanded into it at the dot's own corner, in the dot's colour.
#
# THE TEMPLATE IS REFLECTED, NOT COPIED, and that is the whole difficulty the ledger records as
# "lone dots anchor on different template cells depending on which corner they sit in". The
# template is defined relative to its corner with the frame's interior in a particular diagonal
# direction; a dot at another corner has the interior in a different direction, so the offsets
# flip sign on the axes that differ. Demo 0's template sits at a top-right corner and the same
# shape has to serve a top-left, a bottom-left and a bottom-right dot.
#
# The templates are not the same shape between grids — demo 0's covers its corner cell and trails
# two cells inward, demo 1's leaves the corner black and trails one — so nothing about the shape
# is assumed. It is read out of whichever grid is being solved.
from collections import Counter, deque


def _comps(cells, grid):
    seen, out = set(), []
    for p in sorted(cells):
        if p in seen:
            continue
        col = grid[p[0]][p[1]]
        q = deque([p])
        seen.add(p)
        got = []
        while q:
            y, x = q.popleft()
            got.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    n = (y + dy, x + dx)
                    if n in cells and n not in seen and grid[n[0]][n[1]] == col:
                        seen.add(n)
                        q.append(n)
        out.append((col, sorted(got)))
    return out


def _sign(v):
    return (v > 0) - (v < 0)


def transform(grid):
    h, w = len(grid), len(grid[0])
    out = [row[:] for row in grid]
    bg = Counter(v for row in grid for v in row).most_common(1)[0][0]

    # THE FRAME COLOUR IS READ OFF THE BOARD: the frames are the only large things here, so it is
    # the non-background colour whose biggest piece has the biggest bounding box, and it is not
    # close -- 64 against 4, 25 against 4, 49 against 4, 64 against 4 on the four pairs. Testing
    # for a clean hollow rectangle does NOT work: demo 0's frame is broken where the dots sit on it.
    FRAME, span = None, -1
    for v in {x for row in grid for x in row} - {bg}:
        for _, f in _comps({(r, c) for r in range(h) for c in range(w) if grid[r][c] == v}, grid):
            rs = [r for r, _ in f]; cs = [c for _, c in f]
            a = (max(rs) - min(rs) + 1) * (max(cs) - min(cs) + 1)
            if a > span:
                FRAME, span = v, a
    frames = _comps({(r, c) for r in range(h) for c in range(w) if grid[r][c] == FRAME}, grid)
    corners = []
    for _, f in frames:
        rs = [r for r, _ in f]
        cs = [c for _, c in f]
        r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs)
        for cr in {r0, r1}:
            for cc in {c0, c1}:
                # inward is toward the frame's own middle; a degenerate frame has no inward and
                # is left to the template's tail to decide
                corners.append((cr, cc,
                                1 if cr == r0 and r1 > r0 else (-1 if r1 > r0 else 0),
                                1 if cc == c0 and c1 > c0 else (-1 if c1 > c0 else 0)))

    dots = _comps({(r, c) for r in range(h) for c in range(w)
                   if grid[r][c] not in (bg, FRAME)}, grid)
    if not dots or not corners:
        return out

    def anchor(cells):
        """The corner this cluster belongs to.

        NEAREST IS NOT ENOUGH. Demo 1's lone 6 is Chebyshev distance 1 from a corner of each of
        two different frames, and the tie goes the wrong way half the time. What settles it is
        direction: the dot has to lie INWARD from its corner along the diagonal, into the frame
        it is sitting in. The other candidate has it sitting outside.
        """
        pts = set(cells)
        best = None
        for (cr, cc, dr, dc) in corners:
            for sr in ((dr,) if dr else (1, -1)):
                for sc in ((dc,) if dc else (1, -1)):
                    # ANY distance inward, not a contiguous run: a lone dot sits two steps in
                    # with nothing between it and its corner, so requiring k=1 to be occupied
                    # rejects exactly the cells this rule exists to expand.
                    if not any((cr + k * sr, cc + k * sc) in pts
                               for k in range(1, max(h, w))):
                        continue
                    d = max(max(abs(r - cr), abs(c - cc)) for r, c in cells)
                    if best is None or d < best[0]:
                        best = (d, cr, cc, sr, sc)
        return best

    tcol, tcells = max(dots, key=lambda t: len(t[1]))
    got = anchor(tcells)
    if got is None:
        return out
    td, tr, tc, tdr, tdc = got
    shape = [(r - tr, c - tc) for r, c in tcells]

    for col, cells in dots:
        if cells == tcells:
            continue
        got = anchor(cells)
        if got is None:
            continue
        d, cr, cc, dr, dc = got
        fr = 1 if dr == tdr else -1
        fc = 1 if dc == tdc else -1
        for (a, b) in shape:
            y, x = cr + a * fr, cc + b * fc
            if 0 <= y < h and 0 <= x < w:
                out[y][x] = col
    return out
