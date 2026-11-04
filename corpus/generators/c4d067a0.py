"""c4d067a0 -- the little chart says what the big picture should be.

In one corner sits a chart: single cells on a lattice two apart, each standing
for one tile of a much larger picture.  A few tiles of that picture are already
painted -- solid squares laid out on their own wider lattice.

Read the chart, line it up against the tiles already painted, and paint the
rest.  The chart itself stays where it is.
"""

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


def transform(gi):
    H, W = len(gi), len(gi[0])
    flat = [v for row in gi for v in row]
    bg = max(set(flat), key=flat.count)

    seen, lumps = set(), []
    for r in range(H):
        for c in range(W):
            if gi[r][c] == bg or (r, c) in seen:
                continue
            st, comp = [(r, c)], []
            seen.add((r, c))
            while st:
                y, x = st.pop()
                comp.append((y, x))
                for dy, dx in N4:
                    q = (y + dy, x + dx)
                    if (0 <= q[0] < H and 0 <= q[1] < W and gi[q[0]][q[1]] == gi[r][c]
                            and q not in seen):
                        seen.add(q)
                        st.append(q)
            lumps.append(comp)

    dots = [c[0] for c in lumps if len(c) == 1]
    tiles = []
    for comp in lumps:
        r0 = min(p[0] for p in comp); r1 = max(p[0] for p in comp)
        c0 = min(p[1] for p in comp); c1 = max(p[1] for p in comp)
        if len(comp) > 1 and len(comp) == (r1 - r0 + 1) * (c1 - c0 + 1) == (r1 - r0 + 1) ** 2:
            tiles.append((r0, c0, r1 - r0 + 1, gi[r0][c0]))
    if not dots or len(tiles) < 2:
        return [row[:] for row in gi]

    rows = list(range(min(p[0] for p in dots), max(p[0] for p in dots) + 1, 2))
    cols = list(range(min(p[1] for p in dots), max(p[1] for p in dots) + 1, 2))
    chart = [[gi[r][c] for c in cols] for r in rows]

    wide = tiles[0][2]
    steps = {abs(a[0] - b[0]) for a in tiles for b in tiles if a[0] != b[0]} | \
            {abs(a[1] - b[1]) for a in tiles for b in tiles if a[1] != b[1]}
    step = min(steps) if steps else wide

    go = [row[:] for row in gi]
    for i in range(len(rows)):
        for j in range(len(cols)):
            base = (tiles[0][0] - i * step, tiles[0][1] - j * step)
            if chart[i][j] != tiles[0][3]:
                continue
            ok = True
            for tr, tc, _, hue in tiles:
                a, b = (tr - base[0]), (tc - base[1])
                if a % step or b % step or not (0 <= a // step < len(rows)) \
                        or not (0 <= b // step < len(cols)) or chart[a // step][b // step] != hue:
                    ok = False
                    break
            if not ok:
                continue
            for p in range(len(rows)):
                for q in range(len(cols)):
                    hue = chart[p][q]
                    if hue == bg:
                        continue
                    for y in range(wide):
                        for x in range(wide):
                            ry, rx = base[0] + p * step + y, base[1] + q * step + x
                            if 0 <= ry < H and 0 <= rx < W:
                                go[ry][rx] = hue
            return go
    return go
