"""58f5dbd5 -- punch each slab with its own stencil.

Solid slabs of colour are ranged in a block on one side of the board; scattered
on the other side are little stencils, one drawn in each slab's colour.  Punch
the stencil out of the middle of its slab -- where the stencil has ink the slab
is knocked through to bare board, where it has none the slab stays -- and hand
back the slabs alone.
"""


def _blobs(gi, hue):
    H, W = len(gi), len(gi[0])
    seen, out = set(), []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or gi[r][c] != hue:
                continue
            stack, cur = [(r, c)], []
            seen.add((r, c))
            while stack:
                x, y = stack.pop()
                cur.append((x, y))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        a, b = x + dx, y + dy
                        if 0 <= a < H and 0 <= b < W and (a, b) not in seen and gi[a][b] == hue:
                            seen.add((a, b))
                            stack.append((a, b))
            out.append(cur)
    return out


def transform(gi):
    H, W = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])

    slabs, stencils = {}, {}
    for hue in set(tally) - {bg}:
        for blob in _blobs(gi, hue):
            r0 = min(r for r, _ in blob)
            r1 = max(r for r, _ in blob)
            c0 = min(c for _, c in blob)
            c1 = max(c for _, c in blob)
            if len(blob) == (r1 - r0 + 1) * (c1 - c0 + 1) and r1 - r0 >= 3:
                slabs[hue] = (r0, r1, c0, c1)
            else:
                stencils[hue] = {(r - r0, c - c0) for r, c in blob}

    go = [row[:] for row in gi]
    for hue, (r0, r1, c0, c1) in slabs.items():
        cut = stencils.get(hue, set())
        for a in range(r1 - r0 - 1):
            for b in range(c1 - c0 - 1):
                if (a, b) in cut:
                    go[r0 + 1 + a][c0 + 1 + b] = bg

    r0 = min(b[0] for b in slabs.values()) - 1
    r1 = max(b[1] for b in slabs.values()) + 1
    c0 = min(b[2] for b in slabs.values()) - 1
    c1 = max(b[3] for b in slabs.values()) + 1
    return [[go[r][c] for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
