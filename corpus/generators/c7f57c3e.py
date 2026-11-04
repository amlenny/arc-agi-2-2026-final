"""c7f57c3e -- every gadget throws its switch.

Two kinds of gadget are on the board, the same machine in its two settings, and
each one appears at whatever size it likes.  Every gadget flips to the other
setting.

The blue cage is what stays put: the two settings share it exactly, so lining
the new drawing up on the cage is what tells you where it goes -- the tail
swaps ends around it and the core changes colour.
"""



def _comps(g, bg):
    H, W = len(g), len(g[0])
    seen, out = set(), []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or g[r][c] == bg:
                continue
            stack, cur = [(r, c)], []
            seen.add((r, c))
            while stack:
                x, y = stack.pop()
                cur.append((x, y))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        a, b = x + dx, y + dy
                        if 0 <= a < H and 0 <= b < W and (a, b) not in seen and g[a][b] != bg:
                            seen.add((a, b))
                            stack.append((a, b))
            out.append(cur)
    return out


def _shrink(pat):
    """The pattern at its own scale, plus that scale."""
    h, w = len(pat), len(pat[0])
    for k in range(min(h, w), 0, -1):
        if h % k or w % k:
            continue
        if all(pat[r][c] == pat[r // k * k][c // k * k] for r in range(h) for c in range(w)):
            return tuple(tuple(pat[r * k][c * k] for c in range(w // k)) for r in range(h // k)), k
    return tuple(tuple(row) for row in pat), 1


def _anchor(pat, CAGE):
    cells = [(r, c) for r, row in enumerate(pat) for c, v in enumerate(row) if v == CAGE]
    return min(r for r, _ in cells), min(c for _, c in cells)


def transform(gi):
    H, W = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])

    # THE CAGE COLOUR IS READ OFF THE BOARD: it is in every gadget -- that is what makes it the
    # cage -- and where a second colour is too, the cage is the heavier of them inside every
    # gadget (18 v 11 and 24 v 6 across the demos; only one candidate on the test).
    parts = _comps(gi, bg)
    if not parts:
        return [row[:] for row in gi]
    shared = set.intersection(*[{gi[y][x] for y, x in p} for p in parts])
    if not shared:
        return [row[:] for row in gi]
    CAGE = max(shared, key=lambda v: tally[v])

    found = []
    for cells in parts:
        r0 = min(r for r, _ in cells)
        c0 = min(c for _, c in cells)
        r1 = max(r for r, _ in cells)
        c1 = max(c for _, c in cells)
        pat = [[gi[r][c] for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
        shape, k = _shrink(pat)
        found.append((r0, c0, shape, k))

    settings = []
    for _, _, shape, _ in found:
        if shape not in settings:
            settings.append(shape)

    go = [[bg] * W for _ in range(H)]
    for r0, c0, shape, k in found:
        other = settings[1 - settings.index(shape)] if len(settings) == 2 else shape
        ar, ac = _anchor(shape, CAGE)
        br, bc = _anchor(other, CAGE)
        top = r0 + k * (ar - br)
        left = c0 + k * (ac - bc)
        for r, row in enumerate(other):
            for c, v in enumerate(row):
                if v == bg:
                    continue
                for dr in range(k):
                    for dc in range(k):
                        go[top + r * k + dr][left + c * k + dc] = v
    return go
