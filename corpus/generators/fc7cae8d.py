"""fc7cae8d -- turn the slab until its two rails point the right way.

A slab sits in the middle of the board with a rail of colour down two of its
sides.  Speckles of those same colours are scattered along the board's own
edges, and that is where each rail belongs.  Turn the slab -- or flip it -- so
both rails face their own edge, then take the rails off and hand back what is
left.
"""

SIDES = ("top", "bottom", "left", "right")
TURNS = {
    "as is":  {"top": "top", "bottom": "bottom", "left": "left", "right": "right"},
    "right":  {"top": "right", "right": "bottom", "bottom": "left", "left": "top"},
    "about":  {"top": "bottom", "bottom": "top", "left": "right", "right": "left"},
    "left":   {"top": "left", "left": "bottom", "bottom": "right", "right": "top"},
    "sideways": {"left": "right", "right": "left", "top": "top", "bottom": "bottom"},
    "over":   {"top": "bottom", "bottom": "top", "left": "left", "right": "right"},
    "spilt":  {"top": "left", "left": "top", "bottom": "right", "right": "bottom"},
    "tipped": {"top": "right", "right": "top", "bottom": "left", "left": "bottom"},
}


def _turn(g, name):
    if name in ("right", "about", "left"):
        for _ in range({"right": 1, "about": 2, "left": 3}[name]):
            g = [list(row) for row in zip(*g[::-1])]
        return g
    if name == "sideways":
        return [row[::-1] for row in g]
    if name == "over":
        return [row[:] for row in g[::-1]]
    if name == "spilt":
        return [list(row) for row in zip(*g)]
    if name == "tipped":
        return [list(row) for row in zip(*[row[::-1] for row in g[::-1]])]
    return [row[:] for row in g]


def transform(gi):
    H, W = len(gi), len(gi[0])
    # The board is the commonest colour -- 0 on every pair here, read rather than assumed.
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])
    live = {(r, c) for r in range(1, H - 1) for c in range(1, W - 1) if gi[r][c] != bg}
    seen, slab = set(), []
    for p in sorted(live):
        if p in seen:
            continue
        stack, cur = [p], []
        seen.add(p)
        while stack:
            x, y = stack.pop()
            cur.append((x, y))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (x + dx, y + dy)
                    if q in live and q not in seen:
                        seen.add(q)
                        stack.append(q)
        if len(cur) > len(slab):
            slab = cur

    r0 = min(r for r, _ in slab)
    r1 = max(r for r, _ in slab)
    c0 = min(c for _, c in slab)
    c1 = max(c for _, c in slab)
    block = [[gi[r][c] for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]

    def most(cells):
        seen2 = {}
        for v in cells:
            seen2[v] = seen2.get(v, 0) + 1
        return max(seen2, key=lambda k: seen2[k])

    body = most([v for row in block for v in row])
    edge = {"top": block[0], "bottom": block[-1],
            "left": [row[0] for row in block], "right": [row[-1] for row in block]}
    rails = {s: most(edge[s]) for s in SIDES if most(edge[s]) != body}

    speck = {"top": gi[0], "bottom": gi[H - 1],
             "left": [gi[r][0] for r in range(H)], "right": [gi[r][W - 1] for r in range(H)]}
    belongs = {}
    for s in SIDES:
        hue = most([v for v in speck[s] if v != bg])
        belongs[hue] = s

    name = next(t for t, way in TURNS.items()
                if all(way[s] == belongs.get(rails[s]) for s in rails))

    keep = [row[:] for row in block]
    if "top" in rails:
        keep = keep[1:]
    if "bottom" in rails:
        keep = keep[:-1]
    if "left" in rails:
        keep = [row[1:] for row in keep]
    if "right" in rails:
        keep = [row[:-1] for row in keep]
    return _turn(keep, name)
