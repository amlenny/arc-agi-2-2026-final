"""aa4ec2a5 -- outline every blob, and light up the ones that hold something.

Every blue blob gets a red outline traced round it.  A blob that has swallowed a
pocket of background turns azure and the pocket it swallowed turns magenta; a
solid blob keeps its blue.

The board colour and the blob colour are read off the board.  The other three --
outline, lit, pocket -- appear in no input; they are colours this rule paints,
so there is nothing to read them from.
"""

LIT = 8
POCKET = 6
EDGE = 2
NBRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _comps(g, pred):
    H, W = len(g), len(g[0])
    seen, out = set(), []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or not pred(g[r][c]):
                continue
            stack, cur = [(r, c)], []
            seen.add((r, c))
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


def transform(gi):
    H, W = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    BG = max(tally, key=lambda k: tally[k])
    SOLID = next(v for v in tally if v != BG)
    go = [row[:] for row in gi]
    blobs = _comps(gi, lambda v: v != BG)
    held = set()
    for cells in blobs:
        pocket = _pockets(cells)
        held |= pocket
        for r, c in pocket:
            go[r][c] = POCKET
        for r, c in cells:
            go[r][c] = LIT if pocket else SOLID
    for cells in blobs:
        for r, c in cells:
            for dr, dc in NBRS:
                a, b = r + dr, c + dc
                if 0 <= a < H and 0 <= b < W and gi[a][b] == BG and (a, b) not in held:
                    go[a][b] = EDGE
    return go
