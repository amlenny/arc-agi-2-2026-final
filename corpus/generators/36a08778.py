"""36a08778 -- let the water go.

A few magenta cells are already wet.  Water falls straight down; when a red
shelf stops it, it runs along the shelf to either side until it finds an edge
to pour off, and falls again.  A red cell never gets wet, and water reaching
the bottom of the board simply leaves.

Which colour is which is read off the board, not assumed: a shelf lies along a
row, so it always has cells side by side, and water never does -- it starts as
loose drops.
"""


def _cast(gi):
    """Board colour, shelf colour, water colour -- told apart by shape."""
    H, W = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])
    beside = {}
    for hue in tally:
        beside[hue] = sum(1 for r in range(H) for c in range(W - 1)
                          if gi[r][c] == hue and gi[r][c + 1] == hue)
    rest = [h for h in tally if h != bg]
    shelf = max(rest, key=lambda h: beside[h])
    water = next(h for h in rest if h != shelf)
    return bg, shelf, water


def transform(gi):
    H, W = len(gi), len(gi[0])
    _, SHELF, WATER = _cast(gi)
    wet = {(r, c) for r in range(H) for c in range(W) if gi[r][c] == WATER}
    stack = list(wet)
    while stack:
        r, c = stack.pop()
        if r + 1 >= H:
            continue
        if gi[r + 1][c] != SHELF:
            if (r + 1, c) not in wet:
                wet.add((r + 1, c))
                stack.append((r + 1, c))
            continue
        for step in (-1, 1):
            b = c + step
            if 0 <= b < W and gi[r][b] != SHELF and (r, b) not in wet:
                wet.add((r, b))
                stack.append((r, b))

    go = [row[:] for row in gi]
    for r, c in wet:
        go[r][c] = WATER
    return go
