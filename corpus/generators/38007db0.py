"""38007db0 -- keep the odd one out of every row of tiles.

The board is a rack of identical tiles, several to a row.  In each row all but
one are the same; hand back a single column of tiles holding, for each row, the
one that does not match its neighbours.
"""


def _runs(gaps, n):
    out, start = [], 0
    for x in sorted(gaps) + [n]:
        if x > start:
            out.append((start, x - 1))
        start = x + 1
    return out


def transform(gi):
    H, W = len(gi), len(gi[0])
    bars = [r for r in range(H) if len(set(gi[r])) == 1]
    posts = [c for c in range(W) if len({gi[r][c] for r in range(H)}) == 1]
    rows = _runs(bars, H)
    cols = _runs(posts, W)
    frame = gi[bars[0]][0] if bars else gi[0][posts[0]]

    wide = cols[0][1] - cols[0][0] + 1
    go = [[frame] * (wide + 2) for _ in range(H)]
    for r0, r1 in rows:
        tiles = [tuple(tuple(gi[r][c] for c in range(c0, c1 + 1)) for r in range(r0, r1 + 1))
                 for c0, c1 in cols]
        odd = next(t for t in tiles if tiles.count(t) == 1)
        for i, r in enumerate(range(r0, r1 + 1)):
            for j, v in enumerate(odd[i]):
                go[r][j + 1] = v
    return go
