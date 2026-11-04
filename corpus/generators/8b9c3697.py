"""8b9c3697 -- the red block that fits a comb's stub slides home.

Each comb has one tooth shorter than its neighbours.  A red block slides in a
straight line and parks against the tip of that stub -- and it only counts as
parked if the stub is exactly as wide as the block, the block meets it square
on, and the block ends up inside the comb.

The lane it travelled down is left black behind it.  Any red block with nowhere
to go is swept off the board.
"""

TRAIL = 0               # left behind by the rule; it appears in no input
STEPS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def _comps(g, pred):
    H, W = len(g), len(g[0])
    seen, out = set(), []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or not pred(g[r][c]):
                continue
            stack, cur = [(r, c)], []
            seen.add((r, c))
            while stack:
                x, y = stack.pop()
                cur.append((x, y))
                for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= a < H and 0 <= b < W and (a, b) not in seen and pred(g[a][b]):
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
    # THE BLOCK COLOUR IS READ OFF THE BOARD: a block is a solid rectangle and a comb never is.
    # Every piece of the block colour is solid on all four pairs (5, 6, 7 and 11 of them) and not
    # one piece of the comb colour is. Checked by relabelling rather than by the separation alone:
    # with few pairs to test against, total separation can be coincidence.
    CART = None
    for hue in tally:
        if hue == bg:
            continue
        pieces = _comps(gi, lambda v, hue=hue: v == hue)
        if pieces and all(len(p) == (max(r for r, _ in p) - min(r for r, _ in p) + 1)
                                  * (max(c for _, c in p) - min(c for _, c in p) + 1)
                          for p in pieces):
            CART = hue
            break
    if CART is None:
        return [row[:] for row in gi]
    comb = lambda v: v not in (bg, CART)

    boxes = [(min(r for r, _ in s), max(r for r, _ in s),
              min(c for _, c in s), max(c for _, c in s)) for s in _comps(gi, comb)]

    go = [[bg] * W for _ in range(H)]
    for r in range(H):
        for c in range(W):
            if comb(gi[r][c]):
                go[r][c] = gi[r][c]

    for block in _comps(gi, lambda v: v == CART):
        span = len({c for _, c in block}), len({r for r, _ in block})
        home = None
        for dr, dc in STEPS:
            wide = span[0] if dr else span[1]          # the block's leading edge
            lead = [p for p in block if (p[0] + dr, p[1] + dc) not in block]
            k = 0
            while True:
                ahead = [(r + dr * (k + 1), c + dc * (k + 1)) for r, c in lead]
                if any(not (0 <= r < H and 0 <= c < W) for r, c in ahead):
                    k = None
                    break
                if any(comb(gi[r][c]) for r, c in ahead):
                    if not all(comb(gi[r][c]) for r, c in ahead):
                        k = None
                    break
                k += 1
            if k is None or k == 0:
                continue
            stub = [(r + dr * (k + 1), c + dc * (k + 1)) for r, c in lead]
            run = set(stub)
            for r, c in stub:                          # how wide the stub really is
                for step in (-1, 1):
                    a, b = r + dc * step, c + dr * step
                    while 0 <= a < H and 0 <= b < W and comb(gi[a][b]):
                        run.add((a, b))
                        a, b = a + dc * step, b + dr * step
            if len(run) != wide:
                continue
            rest = [(r + dr * k, c + dc * k) for r, c in block]
            if not any(r0 <= r <= r1 and c0 <= c <= c1
                       for r, c in rest for r0, r1, c0, c1 in boxes):
                continue
            home = (k, dr, dc, rest)
        if home is None:
            continue
        k, dr, dc, rest = home
        for r, c in block:
            for i in range(k + 1):
                go[r + dr * i][c + dc * i] = TRAIL
        for r, c in rest:
            go[r][c] = CART
    return go
