# Rule authored from the evaluation demonstrations of 291dc1e1.
#
# A corner cell marks the origin; two lines run off it along the grid's edges, one in each of two
# colours. Between them sit rectangular blocks. The answer stacks those blocks vertically, in
# reading order, each centred in a strip as wide as the widest block.
#
# THE ORIGIN DECIDES THE READING ORDER, and that is the whole difficulty. The blocks are read fast
# along the line whose colour is the lower of the two, travelling AWAY from the origin, and slow
# along the other. Demo 3's origin is the top-RIGHT corner, so its blocks come out right-to-left;
# a fixed raster scan reproduces the other three demonstrations and gets that one backwards.
#
# WHEN THE FAST AXIS IS VERTICAL the block is rotated 90 degrees counter-clockwise so that axis
# lies horizontal in the answer. The tile's rows then run DESCENDING COLUMN — not ascending
# distance from the origin, which coincides with it only while the origin sits left of the blocks.
# That holds in demo 0 and fails in the test, where the origin is on the right.
#
# The axis lines are excluded from the blocks BY POSITION, never by colour: demo 0's six-block
# carries a cell of each axis colour inside it, and dropping cells by colour punches holes in the
# shape that resurface as background in the answer.
from collections import Counter, deque


def _build(grid, _unused=None):
    h, w = len(grid), len(grid[0])
    cnt = Counter(v for row in grid for v in row)
    bg = cnt.most_common(1)[0][0]
    # origin: the lone cell whose colour appears exactly once
    origin = None
    for r in range(h):
        for c in range(w):
            if cnt[grid[r][c]] == 1:
                origin = (r, c, grid[r][c])
    if origin is None:
        return None
    orow, ocol, _ = origin
    # the two axis lines: full runs sharing the origin's row / column
    rowline = [grid[orow][c] for c in range(w) if c != ocol]
    colline = [grid[r][ocol] for r in range(h) if r != orow]
    hcol = rowline[0] if len(set(rowline)) == 1 else None
    vcol = colline[0] if len(set(colline)) == 1 else None
    if hcol is None or vcol is None:
        return None
    # THE FAST AXIS IS THE LONGER LINE, read off the board rather than by comparing colour values.
    # It is the longer one in all five pairs -- 20 against 8, 10 against 7, 27 against 7, 22
    # against 7, 27 against 7 -- and comparing the two colour numbers happened to agree only
    # because the same colour drew the long line every time.
    one_is_horizontal = len(rowline) >= len(colline)
    one = hcol if one_is_horizontal else vcol
    axis_colours = {hcol, vcol, grid[orow][ocol]}

    seen, shapes = set(), []
    for r in range(h):
        for c in range(w):
            if (r, c) in seen or grid[r][c] == bg or r == orow or c == ocol:
                continue
            q, cells = deque([(r, c)]), []
            seen.add((r, c))
            while q:
                y, x = q.popleft()
                cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    a, b = y + dy, x + dx
                    if (0 <= a < h and 0 <= b < w and (a, b) not in seen
                            and grid[a][b] != bg and a != orow and b != ocol):
                        seen.add((a, b))
                        q.append((a, b))
            shapes.append(cells)

    def dist_h(c):
        return abs(c - ocol)

    def dist_v(r):
        return abs(r - orow)

    tiles = []
    for cells in shapes:
        if one_is_horizontal:
            fast, slow = dist_h, dist_v
            key = (min(slow(r) for r, _ in cells), min(fast(c) for _, c in cells))
        else:
            fast, slow = dist_v, dist_h
            key = (min(slow(c) for _, c in cells), min(fast(r) for r, _ in cells))
        if one_is_horizontal:
            A = sorted({dist_v(r) for r, _ in cells})
            B = sorted({dist_h(c) for _, c in cells})
            m = {(dist_v(r), dist_h(c)): grid[r][c] for r, c in cells}
        else:
            # the vertical 1-axis becomes the tile's horizontal one: the shape rotated 90 CCW.
            # Tile rows run DESCENDING COLUMN, not ascending distance from the origin — the two
            # coincide only when the origin sits left of the shapes, which is demo 0 but not the
            # test, where the origin is on the right.
            A = sorted({c for _, c in cells}, reverse=True)
            B = sorted({dist_v(r) for r, _ in cells})
            m = {(c, dist_v(r)): grid[r][c] for r, c in cells}
        tile = [[m.get((a, b), bg) for b in B] for a in A]
        tiles.append((key, tile))

    tiles.sort(key=lambda t: t[0])
    if not tiles:
        return None
    ow = max(len(t[0]) for _, t in tiles)
    out = []
    for _, t in tiles:
        pad = (ow - len(t[0])) // 2
        for row in t:
            out.append([bg] * pad + list(row) + [bg] * (ow - pad - len(row)))
    return out


def transform(grid):
    return _build(grid, True)
