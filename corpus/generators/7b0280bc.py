# Rule authored from the evaluation demonstrations of 7b0280bc.
#
# The grid is a MAZE. Two square blocks of one colour are the ends; the corridors between them are
# drawn in two more colours. The answer recolours the route joining the ends — the corridor colour
# laid in square turns becomes 3, the colour laid in straight runs becomes 5 — and leaves every
# other corridor, and the end blocks themselves, alone.
#
# THE END BLOCKS ARE SQUARE, of whatever size: 2x2 in all three demonstrations and 3x3 in the test,
# so the size cannot be assumed. What names the colour is that it forms exactly TWO blocks and
# nothing else. The turn colour also makes squares, but it makes many.
#
# THE ROUTE LEAVES AN END SQUARELY, never off a corner. A diagonal exit picks up a stray cell
# touching the corner of demo 2's lower block and sets off down a stub.
#
# THE ROUTE IS EVERY CELL ON A SHORTEST WAY THROUGH, not a single traced line: cells where
# distance-from-one-end + distance-from-the-other equals the total. The test's corridors are two
# cells wide where the demonstrations' are one, and a traced path takes one column and drops the
# other. Widening it instead by repainting whole colour-components does not work — clipping the
# foot of a long segment then drags an entire dead-end branch in.
#
# A DIAGONAL STEP IS ONLY LEGAL AS A GENUINE DIAGONAL RUN, with both cells it squeezes past empty.
# Allowing corner-cutting welds corridors that merely pass close, and in the test that manufactures
# a SECOND route of exactly equal length — at which point the shortest-path set contains both and
# the answer is ambiguous. Demo 0's staircase is a real diagonal and has background either side, so
# it still travels.
from collections import Counter, deque


def _comps(grid, pred, diag=True):
    h, w = len(grid), len(grid[0])
    steps = ([(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)] if diag
             else [(1, 0), (-1, 0), (0, 1), (0, -1)])
    seen, out = set(), []
    for r in range(h):
        for c in range(w):
            if not pred(r, c) or (r, c) in seen:
                continue
            q, cs = deque([(r, c)]), []
            seen.add((r, c))
            while q:
                y, x = q.popleft()
                cs.append((y, x))
                for dy, dx in steps:
                    a, b = y + dy, x + dx
                    if 0 <= a < h and 0 <= b < w and (a, b) not in seen and pred(a, b):
                        seen.add((a, b))
                        q.append((a, b))
            out.append(cs)
    return out


def transform(grid):
    h, w = len(grid), len(grid[0])
    bg = Counter(v for row in grid for v in row).most_common(1)[0][0]
    palette = sorted({v for row in grid for v in row} - {bg})
    if len(palette) != 3:
        return [row[:] for row in grid]

    # THE ANCHORS are the colour that appears as exactly two 2x2 squares and nothing else.
    anchor = None
    for col in palette:
        cs = _comps(grid, lambda r, c, col=col: grid[r][c] == col)
        # THE ANCHOR BLOCKS ARE SQUARE, of whatever size — 2x2 in every demonstration and 3x3 in
        # the test, so the size cannot be hard-coded. What identifies the colour is that it forms
        # exactly TWO of them and nothing else; the corner colour also makes squares but makes
        # many.
        def square(g):
            ys = [y for y, _ in g]; xs = [x for _, x in g]
            side = max(ys) - min(ys) + 1
            return (side >= 2 and max(xs) - min(xs) + 1 == side and len(g) == side * side)

        if len(cs) == 2 and all(square(g) for g in cs):
            anchor = (col, cs)
            break
    if anchor is None:
        return [row[:] for row in grid]
    acol, ablocks = anchor

    rest = [c for c in palette if c != acol]
    # of the two corridor colours, the one laid in 2x2 blocks marks the corners and becomes 3;
    # the one laid in straight runs becomes 5
    def blockiness(col):
        n = 0
        for r in range(h - 1):
            for c in range(w - 1):
                if all(grid[r + dy][c + dx] == col for dy in (0, 1) for dx in (0, 1)):
                    n += 1
        return n / max(1, sum(1 for row in grid for v in row if v == col))
    corner = max(rest, key=blockiness)
    line = [c for c in rest if c != corner][0]

    road = lambda r, c: grid[r][c] in (corner, line)
    # THE ROUTE LEAVES AN ANCHOR SQUARELY, never off its corner. Allowing a diagonal exit picks up
    # an isolated cell touching the anchor's corner and sets off down a stub instead of the
    # corridor — demo 2 has exactly such a cell beside its lower anchor.
    def touching(block):
        return {(y + dy, x + dx) for y, x in block
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if 0 <= y + dy < h and 0 <= x + dx < w and road(y + dy, x + dx)}

    starts, goals = touching(ablocks[0]), touching(ablocks[1])
    if not starts or not goals:
        return [row[:] for row in grid]

    # THE ROUTE IS EVERY CELL ON A SHORTEST WAY THROUGH, not one traced line. The corridors are
    # two cells wide in the test where they are one in every demonstration, and a single traced
    # path takes one column and drops the other. Cells satisfying
    #     distance-from-one-anchor + distance-from-the-other == the total
    # are exactly the ones lying on some shortest route: that takes both columns of a wide corridor
    # and no cell of a dead end, which expanding whole colour-components does not manage — there,
    # clipping the foot of a long segment drags the entire branch in.
    def step_ok(y, x, dy, dx):
        """A diagonal step is only legal as a genuine diagonal RUN — both cells it squeezes past
        empty. Otherwise it is corner-cutting, and it welds corridors that merely pass close: in
        the test that manufactures a second route of equal length and the answer becomes
        ambiguous. Demo 0's staircase is a real diagonal and has background on both sides."""
        if not (dy and dx):
            return True
        return not road(y + dy, x) and not road(y, x + dx)

    def bfs(src):
        dist = {c: 0 for c in src}
        q = deque(src)
        while q:
            y, x = q.popleft()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    a, b = y + dy, x + dx
                    if (0 <= a < h and 0 <= b < w and (a, b) not in dist and road(a, b)
                            and step_ok(y, x, dy, dx)):
                        dist[(a, b)] = dist[(y, x)] + 1
                        q.append((a, b))
        return dist

    ds, dg = bfs(starts), bfs(goals)
    reach = [ds[c] for c in goals if c in ds]
    if not reach:
        return [row[:] for row in grid]
    total = min(reach)
    path = [c for c in ds if c in dg and ds[c] + dg[c] == total]

    # A SEGMENT IS RECOLOURED WHOLE. The route is traced one cell at a time, but the answer
    # repaints every piece it passes through entire — so each cell drags its own colour-component
    # along. That covers both the corner turns, which the route clips on one cell of a block, and
    # the corridors themselves, which are two cells wide in the test where the demonstrations are
    # one. Straight segments are separate components joined by the corners, so a branch the route
    # never enters is never picked up.
    blocks = {}
    for col in (corner, line):
        for cs in _comps(grid, lambda r, c, col=col: grid[r][c] == col, diag=False):
            for cell in cs:
                blocks[cell] = cs
    paint = set()
    for cell in path:
        paint.add(cell)
        if cell in blocks:
            paint.update(blocks[cell])

    out = [row[:] for row in grid]
    for y, x in paint:
        out[y][x] = 3 if grid[y][x] == corner else 5
    return out
