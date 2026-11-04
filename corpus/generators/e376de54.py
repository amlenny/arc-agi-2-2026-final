"""e376de54 -- comb the strokes to the middle one's length.

The grid holds a ladder of parallel strokes, all running the same way.  One end
of the ladder is square: those end cells lie on a straight line.  The other end
is ragged, the strokes having been drawn too long or too short.

The stroke in the MIDDLE of the ladder is the correct one.  Every other stroke
is trimmed or grown from its square end until it matches that length; direction
and colour are untouched.
"""

WAYS = ((0, 1), (1, 0), (1, 1), (1, -1))


def _strokes(g, bg, d):
    H, W = len(g), len(g[0])
    out = []
    for r in range(H):
        for c in range(W):
            v = g[r][c]
            if v == bg:
                continue
            b = (r - d[0], c - d[1])
            if 0 <= b[0] < H and 0 <= b[1] < W and g[b[0]][b[1]] == v:
                continue
            run = []
            y, x = r, c
            while 0 <= y < H and 0 <= x < W and g[y][x] == v:
                run.append((y, x))
                y, x = y + d[0], x + d[1]
            out.append((v, run))
    return out


def _straight(pts):
    if len(pts) < 3:
        return True
    (r0, c0), (r1, c1) = pts[0], pts[1]
    dr, dc = r1 - r0, c1 - c0
    return all((p[0] - r0) * dc == (p[1] - c0) * dr for p in pts[2:])


def transform(gi):
    H, W = len(gi), len(gi[0])
    flat = [v for row in gi for v in row]
    bg = max(set(flat), key=flat.count)

    best = None
    for d in WAYS:
        runs = _strokes(gi, bg, d)
        if best is None or len(runs) < len(best[1]):
            best = (d, runs)
    d, runs = best

    heads = sorted(run[0] for _, run in runs)
    tails = sorted(run[-1] for _, run in runs)
    if _straight(heads):
        anchor, step = 0, d
    elif _straight(tails):
        anchor, step = -1, (-d[0], -d[1])
    else:
        return [row[:] for row in gi]

    order = sorted(runs, key=lambda vr: vr[1][anchor])
    want = len(order[len(order) // 2][1])

    go = [[bg] * W for _ in range(H)]
    for v, run in runs:
        y, x = run[anchor]
        for _ in range(want):
            if 0 <= y < H and 0 <= x < W:
                go[y][x] = v
            y, x = y + step[0], x + step[1]
    return go
