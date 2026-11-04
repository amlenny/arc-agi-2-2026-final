"""7666fa5d -- shade the gap between every pair of parallel diagonals.

The board carries a set of diagonal strokes, all leaning the same way.  Take any
two of them: the strip of board lying between them, over the stretch where both
strokes actually run, is shaded red.  Cells the strokes themselves occupy keep
their own colour.

Diagonal coordinates make this straightforward -- u = r + c counts across the
strokes, v = r - c counts along them, and only cells whose u and v share a
parity are on the lattice.
"""

FILL = 2


def _strokes(S, step):
    back = (-step[0], -step[1])
    out = []
    for p in S:
        if (p[0] + back[0], p[1] + back[1]) in S:
            continue
        q, run = p, []
        while q in S:
            run.append(q)
            q = (q[0] + step[0], q[1] + step[1])
        if len(run) > 1:
            out.append(run)
    return out


def transform(gi):
    H, W = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])
    S = {(r, c) for r in range(H) for c in range(W) if gi[r][c] != bg}

    down_left = _strokes(S, (1, -1))
    lean = (1, -1) if sum(len(s) for s in down_left) >= sum(len(s) for s in _strokes(S, (1, 1))) else (1, 1)
    strokes = down_left if lean == (1, -1) else _strokes(S, (1, 1))

    def across(r, c):
        return r + c if lean == (1, -1) else r - c

    def along(r, c):
        return r - c if lean == (1, -1) else r + c

    bands = [(across(*s[0]), min(along(*p) for p in s), max(along(*p) for p in s)) for s in strokes]

    go = [row[:] for row in gi]
    for i, (u1, lo1, hi1) in enumerate(bands):
        for u2, lo2, hi2 in bands[i + 1:]:
            lo, hi = max(lo1, lo2), min(hi1, hi2)
            if lo > hi or u1 == u2:
                continue
            for u in range(min(u1, u2) + 1, max(u1, u2)):
                for v in range(lo, hi + 1):
                    if (u + v) % 2:
                        continue
                    r = (u + v) // 2
                    c = (u - v) // 2 if lean == (1, -1) else (v - u) // 2
                    if 0 <= r < H and 0 <= c < W and (r, c) not in S:
                        go[r][c] = FILL
    return go
