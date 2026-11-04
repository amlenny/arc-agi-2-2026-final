"""7c66cb00 -- each tray keeps only what is drawn in its own colour.

Little emblems float above a stack of trays.  A tray is filled with one colour
and rimmed in another.  Of each emblem, only the cells drawn in that tray's fill
colour count for it: cut them out, drop them to the tray's floor keeping their
columns, and draw them in the tray's rim colour.  An emblem with none of that
colour leaves the tray alone.  The emblems themselves are cleared away.
"""


def transform(gi):
    H, W = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])

    trays, r = [], 0
    while r < H:
        if gi[r][0] != bg and gi[r][0] == gi[r][W - 1]:
            top = r
            while r < H and gi[r][0] == gi[top][0] and gi[r][W - 1] == gi[top][0]:
                r += 1
            middle = {}
            for a in range(top, r):
                for b in range(1, W - 1):
                    middle[gi[a][b]] = middle.get(gi[a][b], 0) + 1
            trays.append((top, r - 1, gi[top][0], max(middle, key=lambda k: middle[k])))
        else:
            r += 1

    floor = trays[0][0] if trays else H
    live = {(a, b) for a in range(floor) for b in range(W) if gi[a][b] != bg}
    seen, emblems = set(), []
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
        emblems.append(cur)

    go = [row[:] for row in gi]
    for a in range(floor):
        for b in range(W):
            go[a][b] = bg
    for top, bottom, rim, fill in trays:
        for cur in emblems:
            cut = [(a, b) for a, b in cur if gi[a][b] == fill]
            if not cut:
                continue
            drop = bottom - max(a for a, _ in cut)
            for a, b in cut:
                go[a + drop][b] = rim
    return go
