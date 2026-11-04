"""7b80bb43 -- pull the kinks out of the wires.

Wires run straight across the board, dashed here and there.  Where one has
kinked, the cells step off the line diagonally instead: no cell of a kink has a
neighbour straight above, below, or beside it.

Rub every kink out.  Where a kink hung off a wire, that wire carries straight on
past it, the way the kink was drifting, until it meets its own next stretch.  A
kink attached to nothing was never a wire; it just goes.
"""

SLACK = 5           # a wire may skip this many cells and still be the same wire
NBRS = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b]


def transform(gi):
    H, W = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])
    ink = {(r, c) for r in range(H) for c in range(W) if gi[r][c] != bg}
    hue = next(gi[r][c] for r, c in ink)

    def stretch(p, dr, dc):
        run, q = [p], (p[0] + dr, p[1] + dc)
        while q in ink:
            run.append(q)
            q = (q[0] + dr, q[1] + dc)
        q = (p[0] - dr, p[1] - dc)
        while q in ink:
            run.insert(0, q)
            q = (q[0] - dr, q[1] - dc)
        return run

    flatrun = {p: stretch(p, 0, 1) for p in ink}
    tallrun = {p: stretch(p, 1, 0) for p in ink}
    lines = []
    for runs, along in ((flatrun, 1), (tallrun, 0)):
        for run in {tuple(v) for v in runs.values()}:
            if len(run) < 2:
                continue
            if len(run) == 2 and any(len(flatrun[p]) == len(tallrun[p]) or
                                     (len(flatrun[p]) < len(tallrun[p])) != (along == 0)
                                     for p in run):
                continue
            lines.append((along, run[0][1 - along], run[0][along], run[-1][along]))

    def onwire(p):
        for along, fixed, lo, hi in lines:
            if p[1 - along] == fixed and lo - SLACK <= p[along] <= hi + SLACK:
                return True
        return False

    kinked = {p for p in ink if not onwire(p)}
    go = [[hue if (r, c) in ink and (r, c) not in kinked else bg for c in range(W)]
          for r in range(H)]

    loose = set(kinked)
    while loose:
        seed = loose.pop()
        kink, stack = [seed], [seed]
        while stack:
            x, y = stack.pop()
            for dr, dc in NBRS:
                p = (x + dr, y + dc)
                if p in loose:
                    loose.discard(p)
                    kink.append(p)
                    stack.append(p)

        anchors = {(x + dr, y + dc) for x, y in kink for dr, dc in NBRS}
        for a in anchors & (ink - kinked):
            upright = any((a[0] + dr, a[1]) in ink - kinked for dr in (-1, 1))
            flat = any((a[0], a[1] + dc) in ink - kinked for dc in (-1, 1))
            steps = []
            if upright:
                drift = sum(x - a[0] for x, _ in kink)
                steps.append((1 if drift > 0 else -1, 0))
            if flat:
                drift = sum(y - a[1] for _, y in kink)
                steps.append((0, 1 if drift > 0 else -1))
            for dr, dc in steps:
                run, r, c = [], a[0] + dr, a[1] + dc
                while 0 <= r < H and 0 <= c < W and (r, c) not in ink:
                    run.append((r, c))
                    r, c = r + dr, c + dc
                if not (0 <= r < H and 0 <= c < W):
                    continue
                for x, y in run:
                    go[x][y] = hue
    return go
