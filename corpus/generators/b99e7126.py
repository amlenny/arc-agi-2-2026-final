"""b99e7126 -- the odd tile draws itself across the whole tiling.

The board is a tiling of identical 3x3 tiles.  A few tiles are odd: an extra
ink is laid over them, and the shape that ink makes inside a tile is the same
shape the odd tiles are meant to make across the tiling.

Slide that 3x3 shape over the grid of tiles until it covers every odd tile
already there, then mark the rest of it.
"""


def transform(gi):
    H, W = len(gi), len(gi[0])
    bars = [r for r in range(H) if len(set(gi[r])) == 1]
    posts = [c for c in range(W) if len({gi[r][c] for r in range(H)}) == 1]
    rows = [(bars[i] + 1, bars[i + 1]) for i in range(len(bars) - 1)]
    cols = [(posts[i] + 1, posts[i + 1]) for i in range(len(posts) - 1)]
    if not rows or not cols:
        return [row[:] for row in gi]

    def tile(i, j):
        r0, r1 = rows[i]
        c0, c1 = cols[j]
        return tuple(tuple(gi[r][c] for c in range(c0, c1)) for r in range(r0, r1))

    tally = {}
    for i in range(len(rows)):
        for j in range(len(cols)):
            tally[tile(i, j)] = tally.get(tile(i, j), 0) + 1
    plain = max(tally, key=lambda k: tally[k])
    odd = next((k for k in tally if k != plain), None)
    if odd is None:
        return [row[:] for row in gi]

    ink = next(iter({v for row in odd for v in row} - {v for row in plain for v in row}))
    mark = [(a, b) for a in range(len(odd)) for b in range(len(odd[0])) if odd[a][b] == ink]
    tall = max(a for a, _ in mark) + 1
    wide = max(b for _, b in mark) + 1
    mark = [(a - min(x for x, _ in mark), b - min(y for _, y in mark)) for a, b in mark]

    here = {(i, j) for i in range(len(rows)) for j in range(len(cols))
            if tile(i, j) == odd}

    go = [row[:] for row in gi]
    for di in range(len(rows) - tall + 1):
        for dj in range(len(cols) - wide + 1):
            spread = {(a + di, b + dj) for a, b in mark}
            if here <= spread:
                for i, j in spread:
                    r0, _ = rows[i]
                    c0, _ = cols[j]
                    for a in range(len(odd)):
                        for b in range(len(odd[0])):
                            go[r0 + a][c0 + b] = odd[a][b]
                return go
    return go
