"""3a25b0d8 -- colour the blank copy the way the finished one is coloured.

Two drawings of the same figure lie on the board.  One has had every pocket
inside it painted; the other is a bare outline, and its pockets are different
sizes.  Hand back the bare one with its pockets painted -- pocket for
pocket, each matched to the one in the same place in the figure, so neither the
sizes nor the exact edges have to agree.
"""


def _blobs(cells):
    left = set(cells)
    out = []
    while left:
        seed = left.pop()
        blob, stack = [seed], [seed]
        while stack:
            x, y = stack.pop()
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                p = (x + dr, y + dc)
                if p in left:
                    left.discard(p)
                    blob.append(p)
                    stack.append(p)
        out.append(blob)
    return out


def _where(blobs, r0, r1, c0, c1):
    """Each pocket's middle, measured against the drawing's own size."""
    tall = max(1, r1 - r0)
    wide = max(1, c1 - c0)
    return [(((min(r for r, _ in b) + max(r for r, _ in b)) / 2 - r0) / tall,
             ((min(c for _, c in b) + max(c for _, c in b)) / 2 - c0) / wide) for b in blobs]


def _pairoff(here, there):
    """Match pocket to pocket, closest first -- the two drawings differ in the
    detail of where a pocket starts, so only its place in the figure is trusted."""
    gaps = sorted((abs(a[0] - b[0]) + abs(a[1] - b[1]), i, j)
                  for i, a in enumerate(here) for j, b in enumerate(there))
    taken, given, out = set(), set(), {}
    for _, i, j in gaps:
        if i in taken or j in given:
            continue
        taken.add(i)
        given.add(j)
        out[i] = j
    return out


def transform(gi):
    H, W = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])
    ink = {(r, c) for r in range(H) for c in range(W) if gi[r][c] != bg}

    seen, drawings = set(), []
    for p in sorted(ink):
        if p in seen:
            continue
        blob, stack = [p], [p]
        seen.add(p)
        while stack:
            x, y = stack.pop()
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    q = (x + dr, y + dc)
                    if q in ink and q not in seen:
                        seen.add(q)
                        blob.append(q)
                        stack.append(q)
        drawings.append(blob)

    bare = next(d for d in drawings if len({gi[r][c] for r, c in d}) == 1)
    done = next(d for d in drawings if d is not bare)

    shade = {}
    for r, c in done:
        shade[gi[r][c]] = shade.get(gi[r][c], 0) + 1
    line = max(shade, key=lambda k: shade[k])

    dr0 = min(r for r, _ in done)
    dr1 = max(r for r, _ in done)
    dc0 = min(c for _, c in done)
    dc1 = max(c for _, c in done)
    pockets = _blobs([p for p in done if gi[p[0]][p[1]] != line])
    seats = _where(pockets, dr0, dr1, dc0, dc1)

    r0 = min(r for r, _ in bare)
    r1 = max(r for r, _ in bare)
    c0 = min(c for _, c in bare)
    c1 = max(c for _, c in bare)
    box = {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)} - set(bare)
    holes = [h for h in _blobs(box)
             if not any(r in (r0, r1) or c in (c0, c1) for r, c in h)]
    match = _pairoff(_where(holes, r0, r1, c0, c1), seats)

    go = [[bg] * (c1 - c0 + 1) for _ in range(r1 - r0 + 1)]
    for r, c in bare:
        go[r - r0][c - c0] = gi[r][c]
    for i, hole in enumerate(holes):
        seed = pockets[match[i]][0]
        for r, c in hole:
            go[r - r0][c - c0] = gi[seed[0]][seed[1]]
    return go
