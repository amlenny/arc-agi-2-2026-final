"""a47bf94d -- follow the plumbing and label both ends.

Pipes run through the board, crossing one another; the bridge colour is just pipe
too, painted in at a crossing so you can see which run goes straight through.
The pipe colour is read off the board -- it is far and away the commonest thing
on it after the board itself (40, 56, 47 and 100 cells against 20, 9, 22 and 41
for the next).  The bridge colour needed no constant at all: the only place it
was ever named excludes it from a pad's contents, and a bridge never lies in a
pad, so removing it changes nothing on any pair -- measured, not assumed.  Every
pipe end stops two cells short of a 3x3 pad.

Trace each pipe from pad to pad -- straight on at a crossing, round the bend
where there is only one way on.  A pad holding a solid block is the sender: it
becomes an open DIAMOND, and the pad at the far end is stamped with a CROSS in
the same colour.  A pad already holding a cross keeps it, and its far pad gets
the diamond.  A pipe already labelled at both ends is left alone.
"""

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


def _pad(g, mid):
    H, W = len(g), len(g[0])
    return [(mid[0] + a, mid[1] + b) for a in (-1, 0, 1) for b in (-1, 0, 1)
            if 0 <= mid[0] + a < H and 0 <= mid[1] + b < W]


def transform(gi):
    H, W = len(gi), len(gi[0])
    flat = [v for row in gi for v in row]
    bg = max(set(flat), key=flat.count)
    PIPE = max((v for v in set(flat) if v != bg), key=flat.count)
    DIAMOND = {(-1, 0), (1, 0), (0, -1), (0, 1)}
    CROSS = {(0, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)}
    SOLID = {(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1)}

    pads = {}
    for r in range(1, H - 1):
        for c in range(1, W - 1):
            here = {(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1)
                    if gi[r + a][c + b] != bg}
            if here not in (DIAMOND, CROSS, SOLID):
                continue
            shade = {gi[r + a][c + b] for a, b in here}
            if len(shade) != 1:
                continue
            hue = shade.pop()
            ring = [(r + a, c + b) for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2)
                    if abs(a) == 2 or abs(b) == 2]
            if any(0 <= y < H and 0 <= x < W and gi[y][x] == hue for y, x in ring):
                continue
            pads[(r, c)] = (hue, len(here))
    inpad = {(r + a, c + b) for (r, c), _ in pads.items()
             for a in (-1, 0, 1) for b in (-1, 0, 1) if gi[r + a][c + b] != bg}
    line = {(r, c) for r in range(H) for c in range(W)
            if gi[r][c] != bg and (r, c) not in inpad}

    shade = [gi[y][x] for y, x in line]
    pipecol = max(set(shade), key=shade.count)
    rooms, seen = [], set()
    for p in sorted(line):
        if p in seen or gi[p[0]][p[1]] == pipecol:
            continue
        st, blob = [p], []
        seen.add(p)
        while st:
            y, x = st.pop()
            blob.append((y, x))
            for dy, dx in N4:
                q = (y + dy, x + dx)
                if q in line and q not in seen and gi[q[0]][q[1]] == gi[p[0]][p[1]]:
                    seen.add(q)
                    st.append(q)
        if len(blob) >= 4:
            rooms.append(set(blob))
    inroom = {p for room in rooms for p in room}
    tube = line - inroom

    doors = []
    for room in rooms:
        d = sorted({(y + dy, x + dx) for y, x in room for dy, dx in N4} & tube)
        doors.append(d)

    ends = []
    for p in tube:
        near = [d for d in N4 if (p[0] + d[0], p[1] + d[1]) in line]
        if len(near) == 1:
            ends.append((p, (-near[0][0], -near[0][1])))

    def onward(here, step):
        nxt = (here[0] + step[0], here[1] + step[1])
        if nxt in tube:
            return nxt, step
        if nxt in inroom:
            i = next(k for k, room in enumerate(rooms) if nxt in room)
            if len(doors[i]) == 2:
                out = [d for d in doors[i] if d != here][0]
                away = [d for d in N4
                        if (out[0] + d[0], out[1] + d[1]) not in rooms[i]
                        and (out[0] + d[0], out[1] + d[1]) in line]
                return out, (away[0] if len(away) == 1 else step)
            probe = nxt
            while probe in inroom:
                probe = (probe[0] + step[0], probe[1] + step[1])
            return (probe, step) if probe in tube else (None, None)
        turn = [d for d in N4
                if (here[0] + d[0], here[1] + d[1]) in line
                and (d[0], d[1]) != (-step[0], -step[1])]
        if len(turn) != 1:
            return None, None
        return onward(here, turn[0])

    seen, runs = set(), []
    for start, out in ends:
        if start in seen:
            continue
        here, step = start, (-out[0], -out[1])
        seen.add(here)
        # A TRACE CAN CYCLE, and this loop had nothing to stop it. Where a pipe leaves a room by
        # the door it came in at, or a crossing hands it back onto a run it has already walked,
        # the walk returns to a cell it has been at in the same direction and goes round for ever.
        # None of the source's four boards does it, so the loop was unreachable until a board was
        # drawn with a room on it; the guard costs one set and changes no source answer.
        walked = {(here, step)}
        while True:
            here2, step2 = onward(here, step)
            if here2 is None or (here2, step2) in walked:
                break
            here, step = here2, step2
            walked.add((here, step))
            seen.add(here)
        far = [(p, d) for p, d in ends if p == here]
        if far:
            runs.append(((start, out), far[0]))

    go = [row[:] for row in gi]
    for (pa, da), (pb, db) in runs:
        mids = [(pa[0] + 2 * da[0], pa[1] + 2 * da[1]),
                (pb[0] + 2 * db[0], pb[1] + 2 * db[1])]
        look = []
        for mid in mids:
            cells = [(y, x) for y, x in _pad(gi, mid) if gi[y][x] not in (bg, PIPE)]
            look.append((len(cells), gi[cells[0][0]][cells[0][1]] if cells else None))
        if all(n in (4, 5) for n, _ in look):
            continue
        shade = next((v for _, v in look if v is not None), None)
        if shade is None:
            continue
        sender = 0 if look[0][0] == 9 else 1 if look[1][0] == 9 else (1 if look[0][0] == 5 else 0)
        for i, mid in enumerate(mids):
            for y, x in _pad(gi, mid):
                if (y, x) in inpad:
                    go[y][x] = bg
            dy, dx = mid
            if i == sender:
                spots = [(dy - 1, dx), (dy + 1, dx), (dy, dx - 1), (dy, dx + 1)]
            else:
                spots = [(dy, dx), (dy - 1, dx - 1), (dy - 1, dx + 1),
                         (dy + 1, dx - 1), (dy + 1, dx + 1)]
            for y, x in spots:
                if 0 <= y < H and 0 <= x < W:
                    go[y][x] = shade
    return go
