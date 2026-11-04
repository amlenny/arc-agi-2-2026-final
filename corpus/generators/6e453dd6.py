"""6e453dd6 -- slide the cut-outs up against the rail, and the ones that press
a sealed pocket right onto it leak through.

A rail runs down the board; the rest is solid field with holes cut into it.  The
rail names itself: it is the only colour that fills one whole column and appears
nowhere else, so its cell count is exactly the board's height.  The field also
has full columns but far more cells besides.
Each hole slides sideways, shape intact, until it butts against the rail.

Some holes have sealed a pocket of field inside themselves.  A pocket only
leaks when the slide has pushed it hard against the rail -- one cell of hole
wall between the pocket and the rail, nothing more.  Then its rows are painted
red on the far side, all the way out.
"""

LEAK = 2                # painted by the rule; it appears in no input


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


def _pockets(cells):
    """The field-cells this hole has sealed inside itself."""
    S = set(cells)
    r0 = min(r for r, _ in S)
    r1 = max(r for r, _ in S)
    c0 = min(c for _, c in S)
    c1 = max(c for _, c in S)
    free = {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)} - S
    air = {p for p in free if p[0] in (r0, r1) or p[1] in (c0, c1)}
    edge = list(air)
    while edge:
        x, y = edge.pop()
        for p in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if p in free and p not in air:
                air.add(p)
                edge.append(p)
    return free - air


def _cast(gi):
    """Rail, field, hole -- all three read off the board.  The rail fills exactly one column and
    occupies nothing else; the field is what is left over most; the hole is the third colour."""
    H, W = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    rails = [v for v in tally if tally[v] == H
             and sum(1 for c in range(W) if all(gi[r][c] == v for r in range(H))) == 1]
    if len(rails) != 1:
        return None
    RAIL = rails[0]
    rest = [v for v in tally if v != RAIL]
    if len(rest) != 2:
        return None
    field = max(rest, key=lambda v: tally[v])
    hole = next(v for v in rest if v != field)
    return RAIL, field, hole


def transform(gi):
    H, W = len(gi), len(gi[0])
    cast = _cast(gi)
    if cast is None:
        return [row[:] for row in gi]
    RAIL, field, hole = cast
    rail = next(c for c in range(W) if all(gi[r][c] == RAIL for r in range(H)))

    go = [[RAIL if c == rail else field for c in range(W)] for _ in range(H)]
    for cells in _comps(gi, lambda v: v == hole):
        left = max(c for _, c in cells) < rail
        step = (rail - 1 - max(c for _, c in cells)) if left else (rail + 1 - min(c for _, c in cells))
        for r, c in cells:
            go[r][c + step] = hole
        touching = rail - 2 if left else rail + 2
        for r, c in _pockets(cells):
            if c + step != touching:
                continue
            for c2 in (range(rail + 1, W) if left else range(rail)):
                go[r][c2] = LEAK
    return go
