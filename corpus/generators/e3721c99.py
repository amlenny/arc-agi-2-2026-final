"""e3721c99 -- holes are the key, and the legend says what each count is worth.

A blue rule runs across the board -- a straight line or an elbow, always the one
shape that reaches two edges of the grid.  Behind it sits a legend: a handful of
small shapes, each a different colour, each pierced by a different number of
enclosed holes.

The grey blobs on the working side are counted the same way.  A blob takes the
colour of the legend shape with the same number of holes; a blob whose count is
not in the legend is rubbed out.
"""


def _comps(g, pred):
    H, W = len(g), len(g[0])
    seen = set()
    out = []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or not pred(g[r][c]):
                continue
            stack = [(r, c)]
            seen.add((r, c))
            cur = []
            while stack:
                x, y = stack.pop()
                cur.append((x, y))
                for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= a < H and 0 <= b < W and (a, b) not in seen and pred(g[a][b]):
                        seen.add((a, b))
                        stack.append((a, b))
            out.append(cur)
    return out


def _holes(cells):
    """Enclosed pockets of the shape, counted inside its own bounding box."""
    S = set(cells)
    r0 = min(r for r, _ in S)
    r1 = max(r for r, _ in S)
    c0 = min(c for _, c in S)
    c1 = max(c for _, c in S)
    H, W = r1 - r0 + 1, c1 - c0 + 1
    solid = [[(r0 + r, c0 + c) in S for c in range(W)] for r in range(H)]
    seen = set()
    n = 0
    for r in range(H):
        for c in range(W):
            if solid[r][c] or (r, c) in seen:
                continue
            stack = [(r, c)]
            seen.add((r, c))
            open_air = False
            while stack:
                x, y = stack.pop()
                if x in (0, H - 1) or y in (0, W - 1):
                    open_air = True
                for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= a < H and 0 <= b < W and (a, b) not in seen and not solid[a][b]:
                        seen.add((a, b))
                        stack.append((a, b))
            if not open_air:
                n += 1
    return n


def _edges(cells, H, W):
    e = set()
    for r, c in cells:
        if r == 0:
            e.add("t")
        if r == H - 1:
            e.add("b")
        if c == 0:
            e.add("l")
        if c == W - 1:
            e.add("r")
    return e


def transform(gi):
    H, W = len(gi), len(gi[0])
    # BOARD AND BLANK ARE READ OFF THE BOARD. The board is the commonest colour and the blank
    # pieces waiting to be coloured are the second commonest, on every pair of this task
    # (620/202, 621/246, 522/284, 529/279).
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    order = sorted(tally, key=lambda k: -tally[k])
    bg, BLANK = order[0], order[1]
    shapes = []
    for cid in {v for row in gi for v in row} - {bg, BLANK}:
        for cc in _comps(gi, lambda v, cid=cid: v == cid):
            shapes.append((cid, cc))

    rule = next((s for s in shapes if len(_edges(s[1], H, W)) >= 2), None)
    legend = {}
    for cid, cc in shapes:
        if rule is not None and cc is rule[1]:
            continue
        legend[_holes(cc)] = cid

    go = [row[:] for row in gi]
    for cc in _comps(gi, lambda v: v == BLANK):
        paint = legend.get(_holes(cc), bg)
        for r, c in cc:
            go[r][c] = paint
    return go
