"""78332cb0 -- thread the panels back onto their pipe.

The board is cut into panels by plain rules.  Each panel holds a length of pipe
that meets its edges at one or two places; those are the ends that have to line
up.  Chain the panels so every pipe end meets the next one's, and lay them out
in a single strip running the way the pipe runs.
"""



def _runs(gaps, n):
    out, start = [], 0
    for x in sorted(gaps) + [n]:
        if x > start:
            out.append((start, x - 1))
        start = x + 1
    return out


def transform(gi):
    # THE RULE COLOUR IS READ OFF THE BOARD: of the colours that are not the board itself, it is
    # the one drawing the most complete lines across the grid. The board draws more (it is the
    # commonest colour and fills whole rows of empty panels), which is why it has to be excluded
    # first: 6 full rows of board against 2 rule lines in demo 1.
    _t = {}
    for _row in gi:
        for _v in _row:
            _t[_v] = _t.get(_v, 0) + 1
    _bg = max(_t, key=lambda k: _t[k])
    _H, _W = len(gi), len(gi[0])
    RULE = max((v for v in _t if v != _bg),
               key=lambda v: (sum(1 for r in range(_H) if all(gi[r][c] == v for c in range(_W)))
                              + sum(1 for c in range(_W) if all(gi[r][c] == v for r in range(_H)))))
    H, W = len(gi), len(gi[0])
    bars = [r for r in range(H) if all(v == RULE for v in gi[r])]
    posts = [c for c in range(W) if all(gi[r][c] == RULE for r in range(H))]
    rows = _runs(bars, H)
    cols = _runs(posts, W)

    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])

    panels, ports = [], []
    for r0, r1 in rows:
        for c0, c1 in cols:
            tile = [[gi[r][c] for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
            h, w = len(tile), len(tile[0])
            ends = set()
            for a in range(h):
                for b in range(w):
                    if tile[a][b] == bg:
                        continue
                    if a == 0:
                        ends.add(("top", b))
                    if a == h - 1:
                        ends.add(("bottom", b))
                    if b == 0:
                        ends.add(("left", a))
                    if b == w - 1:
                        ends.add(("right", a))
            panels.append(tile)
            ports.append(ends)

    flat = any(side in ("left", "right") for e in ports for side, _ in e)
    lead, follow = ("right", "left") if flat else ("bottom", "top")

    order = [i for i, e in enumerate(ports)
             if len(e) == 1 and next(iter(e))[0] == lead]
    while True:
        side, at = next(p for p in ports[order[-1]] if p[0] == lead) \
            if any(p[0] == lead for p in ports[order[-1]]) else (None, None)
        if side is None:
            break
        nxt = next(i for i, e in enumerate(ports)
                   if i not in order and (follow, at) in e)
        order.append(nxt)

    tiles = [panels[i] for i in order]
    h, w = len(tiles[0]), len(tiles[0][0])
    if flat:
        return [[tiles[k][a][b] if b < w else RULE
                 for k in range(len(tiles)) for b in range(w + (k < len(tiles) - 1))]
                for a in range(h)]
    out = []
    for k, tile in enumerate(tiles):
        out += [row[:] for row in tile]
        if k < len(tiles) - 1:
            out.append([RULE] * w)
    return out
