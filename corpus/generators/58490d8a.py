"""58490d8a -- the tally sheet counts what is scattered on the board.

A blank sheet is pinned to the board, one coloured dot down its left edge for
each colour worth counting.  Away from the sheet, shapes of those colours lie
about.  Fill each dot's row with one dot per shape of its colour, every other
cell, and hand back the sheet alone.

The sheet colour is read off the board: the sheet is a solid patch, so it is the
colour whose bounding box holds no board colour at all, and the largest such --
demo 2 has a stray 2x2 that also qualifies, against a 5x5 sheet.
"""


def _paper(gi, bg):
    H, W = len(gi), len(gi[0])
    best = None
    for v in {x for row in gi for x in row} - {bg}:
        cs = [(r, c) for r in range(H) for c in range(W) if gi[r][c] == v]
        r0 = min(r for r, _ in cs); r1 = max(r for r, _ in cs)
        c0 = min(c for _, c in cs); c1 = max(c for _, c in cs)
        if any(gi[r][c] == bg for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)):
            continue
        area = (r1 - r0 + 1) * (c1 - c0 + 1)
        if best is None or area > best[0]:
            best = (area, v)
    return best[1] if best else None


def transform(gi):
    H, W = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])
    PAPER = _paper(gi, bg)
    if PAPER is None:
        return [row[:] for row in gi]
    sheet = [(r, c) for r in range(H) for c in range(W) if gi[r][c] == PAPER]
    r0 = min(r for r, _ in sheet)
    r1 = max(r for r, _ in sheet)
    c0 = min(c for _, c in sheet)
    c1 = max(c for _, c in sheet)
    pinned = {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)}

    seen = set()
    tally = {}
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or (r, c) in pinned or gi[r][c] == PAPER:
                continue
            ink = gi[r][c]
            stack = [(r, c)]
            seen.add((r, c))
            size = 0
            while stack:
                x, y = stack.pop()
                size += 1
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        a, b = x + dx, y + dy
                        if (0 <= a < H and 0 <= b < W and (a, b) not in seen
                                and (a, b) not in pinned and gi[a][b] == ink):
                            seen.add((a, b))
                            stack.append((a, b))
            tally[ink] = tally.get(ink, 0) + 1

    go = [[PAPER] * (c1 - c0 + 1) for _ in range(r1 - r0 + 1)]
    for r, c in pinned:
        if gi[r][c] == PAPER:
            continue
        for i in range(tally.get(gi[r][c], 0)):
            go[r - r0][c - c0 + 2 * i] = gi[r][c]
    return go
