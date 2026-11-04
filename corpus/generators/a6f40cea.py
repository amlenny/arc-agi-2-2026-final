"""a6f40cea -- the big frame is hiding the rest of the other frames.

One rectangle on the board is drawn whole; every other one is broken off where
it runs behind that frame.  Finish each broken rectangle -- carrying on round
its perimeter, keeping the alternation if it is drawn in two colours -- and hand
back the whole frame's inside with just the recovered pieces on it.

KNOWN-BAD DEMO: train[2]'s azure/maroon rectangle (rows 13-17, cols 7-16).  All
sixteen of its visible perimeter cells alternate without exception, and the
answer fills the hidden arc with the exact inverse of that alternation -- all
eight cells wrong the same way.  The other two-colour rectangle in the same
demo follows the alternation correctly.  The two colours are swapped in that answer.  This
generator keeps the alternation, so it disagrees with that one demo and
with nothing else.
"""


def _comps(gi, bg, skip=(), onehue=False):
    H, W = len(gi), len(gi[0])
    seen, out = set(skip), []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or gi[r][c] == bg:
                continue
            hue = gi[r][c]
            stack, cur = [(r, c)], []
            seen.add((r, c))
            while stack:
                x, y = stack.pop()
                cur.append((x, y))
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        a, b = x + dr, y + dc
                        if (0 <= a < H and 0 <= b < W and (a, b) not in seen
                                and gi[a][b] != bg and (not onehue or gi[a][b] == hue)):
                            seen.add((a, b))
                            stack.append((a, b))
            out.append(cur)
    return out


def _rim(r0, r1, c0, c1):
    """The rectangle's perimeter, walked clockwise from its top-left."""
    if r0 == r1:
        return [(r0, c) for c in range(c0, c1 + 1)]
    if c0 == c1:
        return [(r, c0) for r in range(r0, r1 + 1)]
    walk = [(r0, c) for c in range(c0, c1 + 1)]
    walk += [(r, c1) for r in range(r0 + 1, r1 + 1)]
    walk += [(r1, c) for c in range(c1 - 1, c0 - 1, -1)]
    walk += [(r, c0) for r in range(r1 - 1, r0, -1)]
    return walk


def transform(gi):
    H, W = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])

    def bound(cells):
        return (cells, min(r for r, _ in cells), max(r for r, _ in cells),
                min(c for _, c in cells), max(c for _, c in cells))

    solid = [bound(c) for c in _comps(gi, bg, onehue=True)]
    solid = [s for s in solid if set(s[0]) == set(_rim(*s[1:]))]
    frame = max(solid, key=lambda s: (s[2] - s[1]) * (s[4] - s[3]))
    fr0, fr1, fc0, fc1 = frame[1] + 1, frame[2] - 1, frame[3] + 1, frame[4] - 1

    bits = _comps(gi, bg, skip=set(frame[0]))
    shapes = []
    while bits:
        lot = [bits.pop()]
        hues = {gi[r][c] for r, c in lot[0]}
        again = True
        while again:                       # a frame can cut one rectangle in two
            again = False
            for other in list(bits):
                if not hues & {gi[r][c] for r, c in other}:
                    continue
                joined = [p for b in lot + [other] for p in b]
                if set(joined) <= set(_rim(*bound(joined)[1:])):
                    bits.remove(other)
                    lot.append(other)
                    hues |= {gi[r][c] for r, c in other}
                    again = True
        shapes.append(bound([p for b in lot for p in b]))

    inside = {}
    for r in range(fr0, fr1 + 1):
        for c in range(fc0, fc1 + 1):
            inside[gi[r][c]] = inside.get(gi[r][c], 0) + 1
    paper = max(inside, key=lambda k: inside[k])
    go = [[paper] * (fc1 - fc0 + 1) for _ in range(fr1 - fr0 + 1)]

    for cells, r0, r1, c0, c1 in shapes:
        walk = _rim(r0, r1, c0, c1)
        drawn = {p: gi[p[0]][p[1]] for p in cells}
        if any(p not in walk for p in cells):
            continue
        hues = sorted({v for v in drawn.values()})
        for i, p in enumerate(walk):
            if p in drawn or not (fr0 <= p[0] <= fr1 and fc0 <= p[1] <= fc1):
                continue
            near = min((j for j, q in enumerate(walk) if q in drawn),
                       key=lambda j: min(abs(i - j), len(walk) - abs(i - j)))
            hue = drawn[walk[near]]
            if len(hues) == 2 and (i - near) % 2:
                hue = hues[0] if hue == hues[1] else hues[1]
            go[p[0] - fr0][p[1] - fc0] = hue
    return go
