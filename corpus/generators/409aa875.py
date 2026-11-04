# Rule authored from the evaluation demonstrations of 409aa875.
#
# THE COMPONENTS ARE ARROWS, not a periodic band. Reading the rows of 9s as a band with a period
# is what stalled this: the "period 3" of demo 2 is just four copies of the same arrow sitting in
# a row, and the "fragment" is a fifth copy somewhere else. Each 3-cell component is an arrow —
# an apex plus two arms — and it fires a mark FIVE CELLS from the apex along the direction it
# points, orthogonal or diagonal.
#
#   apex       the cell 4-adjacent to both others; where no cell is (the V and arrow forms, whose
#              arms sit diagonally off the tip), the cell 8-adjacent to both. Taking 8-adjacency
#              first is wrong and silently so: in a compact L every cell is 8-adjacent to the
#              other two, so the apex came out as whichever was scanned first and demo 0's corner
#              at (3,12) fired from the wrong cell in the wrong direction.
#   direction  minus the sum of the unit steps apex->arm, so the arms point back down the shaft
#   mark       apex + 5 * direction
#
# Three things happen where a mark lands, and all three are forced by the demos:
#   * empty cell            -> painted 9
#   * inside another arrow  -> that WHOLE arrow is recoloured 9. Demo 2's lone copy at (11,13)
#                              fires onto (6,8) and recolours the band arrow sitting there; the
#                              test's arrow at (7,1) fires onto the colour-6 arrow at (2,1) and
#                              turns all three of its cells 9.
#   * two marks on one cell -> painted 1, NOT 9. This is the only source of colour 1, which is
#                              absent from every input: demo 0 puts the V at (14,6) and the
#                              corner at (3,12) both onto (9,7), and the test puts the V at
#                              (14,13) and the corner at (14,8) both onto (9,14).
from collections import Counter, deque


def _components(grid, bg):
    h, w = len(grid), len(grid[0])
    seen, out = set(), []
    for r in range(h):
        for c in range(w):
            if grid[r][c] != bg and (r, c) not in seen:
                q = deque([(r, c)])
                seen.add((r, c))
                cells = []
                while q:
                    y, x = q.popleft()
                    cells.append((y, x))
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            n = (y + dy, x + dx)
                            if (0 <= n[0] < h and 0 <= n[1] < w and n not in seen
                                    and grid[n[0]][n[1]] != bg):
                                seen.add(n)
                                q.append(n)
                out.append(cells)
    return out


def _sign(v):
    return (v > 0) - (v < 0)


def transform(grid):
    h, w = len(grid), len(grid[0])
    out = [row[:] for row in grid]
    bg = Counter(v for row in grid for v in row).most_common(1)[0][0]

    comps = _components(grid, bg)
    owner = {}
    for i, cells in enumerate(comps):
        for p in cells:
            owner[p] = i

    marks = {}
    for cells in comps:
        if len(cells) != 3:
            continue
        apex = None
        for adj in (1, 2):                       # 1 = orthogonal only, 2 = allow diagonal
            hits = [p for p in cells
                    if all(abs(p[0] - q[0]) + abs(p[1] - q[1]) <= adj
                           and max(abs(p[0] - q[0]), abs(p[1] - q[1])) == 1
                           for q in cells if q != p)]
            if len(hits) == 1:
                apex = hits[0]
                break
        if apex is None:
            continue
        arms = [q for q in cells if q != apex]
        dr = sum(_sign(q[0] - apex[0]) for q in arms)
        dc = sum(_sign(q[1] - apex[1]) for q in arms)
        dr, dc = -_sign(dr), -_sign(dc)
        if dr == 0 and dc == 0:
            continue
        t = (apex[0] + 5 * dr, apex[1] + 5 * dc)
        if 0 <= t[0] < h and 0 <= t[1] < w:
            marks[t] = marks.get(t, 0) + 1

    for t, n in marks.items():
        if t in owner:
            for p in comps[owner[t]]:
                out[p[0]][p[1]] = 9
        else:
            out[t[0]][t[1]] = 1 if n > 1 else 9
    return out
