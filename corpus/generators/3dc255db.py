# Rule authored from the evaluation demonstrations of 3dc255db.
#
# Shapes are 8-connected same-colour components. A component whose cells all fall inside a LARGER
# component's bounding box is an IMPURITY trapped in that shape. Each impurity cell is removed,
# and the same number of cells of the impurity colour is emitted from the shape's TIP, travelling
# outward, stopping at the grid edge — demo 2 traps seven and only three fit before the border.
#
# The TIP is the side of the bounding box holding exactly one shape cell. Two shapes have more
# than one such side; among them the tip is the one nearest the shape's centroid, which is the
# apex of the arrow rather than the end of one of its arms.

from collections import deque


def _components(grid, colour):
    h, w = len(grid), len(grid[0])
    seen, out = set(), []
    for r in range(h):
        for c in range(w):
            if grid[r][c] != colour or (r, c) in seen:
                continue
            q, comp = deque([(r, c)]), []
            seen.add((r, c))
            while q:
                y, x = q.popleft()
                comp.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if (0 <= ny < h and 0 <= nx < w and (ny, nx) not in seen
                                and grid[ny][nx] == colour):
                            seen.add((ny, nx))
                            q.append((ny, nx))
            out.append(comp)
    return out


def _bbox(cells):
    rs = [r for r, _ in cells]
    cs = [c for _, c in cells]
    return min(rs), max(rs), min(cs), max(cs)


def _tip(cells):
    """(row, col, drow, dcol) of the shape's apex and the direction it points."""
    r0, r1, c0, c1 = _bbox(cells)
    cr = sum(r for r, _ in cells) / len(cells)
    cc = sum(c for _, c in cells) / len(cells)
    cands = []
    for side, sel, step in (("top", [p for p in cells if p[0] == r0], (-1, 0)),
                            ("bottom", [p for p in cells if p[0] == r1], (1, 0)),
                            ("left", [p for p in cells if p[1] == c0], (0, -1)),
                            ("right", [p for p in cells if p[1] == c1], (0, 1))):
        if len(sel) == 1:
            r, c = sel[0]
            cands.append((abs(r - cr) + abs(c - cc), r, c, step[0], step[1]))
    if not cands:
        return None
    cands.sort()
    _, r, c, dr, dc = cands[0]
    return r, c, dr, dc


def transform(grid):
    h, w = len(grid), len(grid[0])
    out = [row[:] for row in grid]
    # THE BOARD IS READ OFF THE BOARD -- the commonest colour, which is 0 on every pair of
    # this task but is not assumed to be.
    tally = {}
    for row in grid:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])
    colours = {v for row in grid for v in row if v != bg}

    comps = []
    for col in colours:
        for cells in _components(grid, col):
            comps.append((col, cells))

    for col, cells in comps:
        r0, r1, c0, c1 = _bbox(cells)
        trapped = [(oc, ocells) for oc, ocells in comps
                   if oc != col and len(ocells) < len(cells)
                   and all(r0 <= r <= r1 and c0 <= c <= c1 for r, c in ocells)]
        if not trapped:
            continue
        n = sum(len(ocells) for _, ocells in trapped)
        icol = trapped[0][0]
        for _, ocells in trapped:
            for r, c in ocells:
                out[r][c] = bg
        tip = _tip(cells)
        if tip is None:
            continue
        r, c, dr, dc = tip
        for i in range(1, n + 1):
            nr, nc = r + dr * i, c + dc * i
            if not (0 <= nr < h and 0 <= nc < w):
                break
            out[nr][nc] = icol
    return out
