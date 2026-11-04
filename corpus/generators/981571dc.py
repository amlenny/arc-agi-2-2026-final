"""981571dc -- the wallpaper is symmetric; the holes are punched out of it.

A dense patterned board has black cells punched into it.  The pattern is not
periodic, it is *reflected*: it comes back on itself about a diagonal, about the
other diagonal, and about the two mid-lines.  Every hole therefore has partners
elsewhere on the board that still carry its colour.

Work out which reflections the surviving cells agree with, then keep bouncing
colours across those mirrors until nothing black is left.
"""


def _mirrors(gi, HOLE):
    """Every reflection the un-punched cells are consistent with."""
    H, W = len(gi), len(gi[0])
    keep = []
    cand = []
    for k in range(-(W - 1), H):                       # about r - c = k
        cand.append(lambda r, c, k=k: (c + k, r - k))
    for k in range(H + W):                             # about r + c = k
        cand.append(lambda r, c, k=k: (k - c, k - r))
    for a in range(2 * W):                             # about the column a/2
        cand.append(lambda r, c, a=a: (r, a - c))
    for a in range(2 * H):                             # about the row a/2
        cand.append(lambda r, c, a=a: (a - r, c))
    for f in cand:
        seen = agree = 0
        for r in range(H):
            for c in range(W):
                x, y = f(r, c)
                if not (0 <= x < H and 0 <= y < W):
                    continue
                seen += 1
                if gi[r][c] != HOLE and gi[x][y] != HOLE:
                    if gi[r][c] != gi[x][y]:
                        agree = -10 ** 9
                    else:
                        agree += 1
        if seen >= H * W // 4 and agree > seen // 8:
            keep.append(f)
    return keep


def transform(gi):
    H, W = len(gi), len(gi[0])
    # THE HOLE COLOUR IS WHATEVER BREAKS THE SYMMETRY. Take each colour in turn to be the punched
    # one and count the reflections the rest agrees with: the true hole colour leaves four on
    # every pair and every other colour leaves none at all.
    HOLE, best = None, -1
    for hue in {v for row in gi for v in row}:
        n = len(_mirrors(gi, hue))
        if n > best:
            HOLE, best = hue, n
    go = [row[:] for row in gi]
    mirrors = _mirrors(gi, HOLE)
    moved = True
    while moved:
        moved = False
        for r in range(H):
            for c in range(W):
                if go[r][c] != HOLE:
                    continue
                for f in mirrors:
                    x, y = f(r, c)
                    if 0 <= x < H and 0 <= y < W and go[x][y] != HOLE:
                        go[r][c] = go[x][y]
                        moved = True
                        break
    return go
