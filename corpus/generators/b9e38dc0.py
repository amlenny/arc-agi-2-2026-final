"""b9e38dc0 -- the jet keeps the nozzle's spread.

A funnel is drawn on the board with a spot of colour caught inside it.  The
colour fills the funnel and pours out of the mouth -- and it keeps spreading the
way the funnel's walls were going, as if they carried on past their own ends,
step for step, to the edge of the board.
"""

ROUND = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b]


def transform(gi):
    H, W = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])
    ink = {k: v for k, v in tally.items() if k != bg}
    wall = max(ink, key=lambda k: ink[k])

    walls = {(r, c) for r in range(H) for c in range(W) if gi[r][c] == wall}
    r0 = min(r for r, _ in walls)
    r1 = max(r for r, _ in walls)
    c0 = min(c for _, c in walls)
    c1 = max(c for _, c in walls)
    seed_hue = next(k for k in ink if k != wall
                    and all(r0 <= r <= r1 and c0 <= c <= c1
                            for r in range(H) for c in range(W) if gi[r][c] == k))

    block = set(walls)
    studs = [(r, c) for r in range(H) for c in range(W)
             if gi[r][c] not in (bg, wall, seed_hue)]
    block |= set(studs)

    for tip in [p for p in walls
                if sum(1 for d in ROUND if (p[0] + d[0], p[1] + d[1]) in walls) == 1]:
        walk, seen = [tip], {tip}
        while True:
            here = walk[-1]
            step = next(((here[0] + a, here[1] + b) for a, b in ROUND
                         if (here[0] + a, here[1] + b) in walls
                         and (here[0] + a, here[1] + b) not in seen), None)
            if step is None:
                break
            seen.add(step)
            walk.append(step)
        gaps = [(walk[i + 1][0] - walk[i][0], walk[i + 1][1] - walk[i][1])
                for i in range(len(walk) - 1)]
        beat = next((p for p in range(1, 4)
                     if len(gaps) >= 2 * p and all(gaps[i] == gaps[i + p] for i in range(p))), None)
        if beat is None:
            continue
        step = (sum(d[0] for d in gaps[:beat]), sum(d[1] for d in gaps[:beat]))
        for k in range(1, max(H, W) + 1):
            for j in range(beat):
                block.add((walk[j][0] - k * step[0], walk[j][1] - k * step[1]))

    spot = [(r, c) for r in range(H) for c in range(W) if gi[r][c] == seed_hue]
    tips = [p for p in walls
            if sum(1 for d in ROUND if (p[0] + d[0], p[1] + d[1]) in walls) == 1]
    away = (sum(p[0] for p in tips) / len(tips) - sum(p[0] for p in spot) / len(spot),
            sum(p[1] for p in tips) / len(tips) - sum(p[1] for p in spot) / len(spot))
    flow = ((1 if away[0] > 0 else -1), 0) if abs(away[0]) >= abs(away[1]) else (0, 1 if away[1] > 0 else -1)
    start = (sum(p[0] for p in spot) / len(spot), sum(p[1] for p in spot) / len(spot))
    for r, c in studs:                      # a stud shades the lee side of itself
        if (r - start[0]) * flow[0] + (c - start[1]) * flow[1] <= 0:
            continue                        # upstream of the spot: nothing to shade
        while 0 <= r < H and 0 <= c < W:
            block.add((r, c))
            r, c = r + flow[0], c + flow[1]

    wet = set(spot)
    stack = list(wet)
    while stack:
        x, y = stack.pop()
        for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= a < H and 0 <= b < W and (a, b) not in wet and (a, b) not in block:
                wet.add((a, b))
                stack.append((a, b))

    go = [row[:] for row in gi]
    for r, c in wet:
        go[r][c] = seed_hue
    return go
