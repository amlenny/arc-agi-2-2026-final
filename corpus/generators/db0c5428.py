"""db0c5428 -- the motif goes on outwards, and inwards too.

The motif is nine tiles in a square with the middle one punched out.  It carries
on beyond itself: each tile is stamped again, turned half a turn, one tile-width
further out in its own direction -- so the copies land at twice the spacing and
the corners reach furthest.

The punched-out middle is the same figure one size down: read it off the motif
by taking every second cell around the hole, and put the motif's own ground
colour at its centre.
"""


def transform(gi):
    H, W = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])
    ink = [(r, c) for r in range(H) for c in range(W) if gi[r][c] != bg]
    r0 = min(r for r, _ in ink)
    c0 = min(c for _, c in ink)
    m = (max(r for r, _ in ink) - r0 + 1) // 3

    ground = max((v for v in tally if v != bg), key=lambda k: tally[k])
    go = [row[:] for row in gi]

    for i in range(3):
        for j in range(3):
            if i == 1 and j == 1:
                continue
            tile = [[gi[r0 + m * i + a][c0 + m * j + b] for b in range(m)] for a in range(m)]
            top, left = r0 - m + 2 * m * i, c0 - m + 2 * m * j
            for a in range(m):
                for b in range(m):
                    r, c = top + a, left + b
                    if 0 <= r < H and 0 <= c < W:
                        go[r][c] = tile[m - 1 - a][m - 1 - b]

    for a in range(m):
        for b in range(m):
            r, c = r0 + m + a, c0 + m + b
            go[r][c] = gi[r0 + m - 1 + 2 * a][c0 + m - 1 + 2 * b]
    go[r0 + m + m // 2][c0 + m + m // 2] = ground
    return go
