"""b10624e5 -- one quarter holds the whole badge, the rest hold a seed.

A cross of one colour cuts the board into quarters.  The many-coloured quarter shows
the badge in full.  Each other quarter shows only one patch of it -- the seed.

Mirror the badge into that quarter (across the cross, so left-right and/or
top-bottom as its position demands), blow it up until its matching patch is the
size of the seed, and lay it down over the seed.
"""


def transform(gi):
    H, W = len(gi), len(gi[0])
    flat = [v for row in gi for v in row]
    bg = max(set(flat), key=flat.count)

    bar = next(r for r in range(H) if len(set(gi[r])) == 1 and gi[r][0] != bg)
    col = next(c for c in range(W) if len({gi[r][c] for r in range(H)}) == 1
               and gi[0][c] != bg)
    line = gi[bar][0]

    quads = {}
    for vy, rows in ((0, range(0, bar)), (1, range(bar + 1, H))):
        for vx, cs in ((0, range(0, col)), (1, range(col + 1, W))):
            cells = {(r, c): gi[r][c] for r in rows for c in cs if gi[r][c] != bg}
            quads[(vy, vx)] = cells

    home = max(quads, key=lambda k: (len(set(quads[k].values())), len(quads[k])))
    art = quads[home]
    r0 = min(r for r, _ in art); r1 = max(r for r, _ in art)
    c0 = min(c for _, c in art); c1 = max(c for _, c in art)
    grid = [[art.get((r, c), bg) for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]

    fine = 1                                  # the badge may already be drawn large
    for u in range(min(len(grid), len(grid[0])), 1, -1):
        if len(grid) % u or len(grid[0]) % u:
            continue
        if all(len({grid[a * u + y][b * u + x] for y in range(u) for x in range(u)}) == 1
               for a in range(len(grid) // u) for b in range(len(grid[0]) // u)):
            fine = u
            break
    unit = {(a, b): grid[a * fine][b * fine]
            for a in range(len(grid) // fine) for b in range(len(grid[0]) // fine)
            if grid[a * fine][b * fine] != bg}
    tall = len(grid) // fine
    wide = len(grid[0]) // fine

    go = [row[:] for row in gi]
    for spot, seed in quads.items():
        if spot == home or not seed:
            continue
        turn = dict(unit)
        if spot[0] != home[0]:
            turn = {(tall - 1 - r, c): v for (r, c), v in turn.items()}
        if spot[1] != home[1]:
            turn = {(r, wide - 1 - c): v for (r, c), v in turn.items()}

        tint = list(seed.values())
        hue = max(set(tint), key=tint.count)
        mine = [p for p, v in turn.items() if v == hue]
        if not mine:
            continue
        pr = min(r for r, _ in mine); pc = min(c for _, c in mine)
        ph = max(r for r, _ in mine) - pr + 1
        sr = min(r for r, _ in seed); sc = min(c for _, c in seed)
        sh = max(r for r, _ in seed) - sr + 1
        if sh % ph:
            continue
        step = sh // ph
        for (r, c), v in turn.items():
            for a in range(step):
                for b in range(step):
                    y = sr + (r - pr) * step + a
                    x = sc + (c - pc) * step + b
                    if 0 <= y < H and 0 <= x < W and y != bar and x != col:
                        go[y][x] = v
    return go
