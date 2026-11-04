"""7ed72f31 -- every mirror throws a copy of whatever leans on it.

Colour 2 marks the mirrors.  A straight run of 2s is a plain mirror: the shape
resting against it is reflected across that line.  A LONE 2 is a pivot instead:
the shape is turned a half turn about that single cell.

The original shape stays; only the reflection is added.
"""

N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _blobs(pool):
    seen, out = set(), []
    for p in sorted(pool):
        if p in seen:
            continue
        st, comp = [p], []
        seen.add(p)
        while st:
            y, x = st.pop()
            comp.append((y, x))
            for dy, dx in N8:
                q = (y + dy, x + dx)
                if q in pool and q not in seen:
                    seen.add(q)
                    st.append(q)
        out.append(comp)
    return out


def _glass(gi, bg):
    H, W = len(gi), len(gi[0])
    best, span = None, -1
    for hue in {v for row in gi for v in row} - {bg}:
        seen, ok, n = set(), True, 0
        for r in range(H):
            for c in range(W):
                if gi[r][c] != hue or (r, c) in seen:
                    continue
                stack, cur = [(r, c)], []
                seen.add((r, c))
                while stack:
                    y, x = stack.pop()
                    cur.append((y, x))
                    for a, b in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                        if 0 <= a < H and 0 <= b < W and (a, b) not in seen and gi[a][b] == hue:
                            seen.add((a, b))
                            stack.append((a, b))
                n += len(cur)
                if len({y for y, _ in cur}) > 1 and len({x for _, x in cur}) > 1:
                    ok = False
        if ok and n > span:
            best, span = hue, n
    return best


def transform(gi):
    H, W = len(gi), len(gi[0])
    flat = [v for row in gi for v in row]
    bg = max(set(flat), key=flat.count)

    # THE MIRROR COLOUR IS READ OFF THE BOARD: a mirror is a straight run or a single cell, never
    # a shape, so it is a colour EVERY piece of which is straight. Demo 0 has a second such colour
    # and the mirrors are the heavier of the two, 11 cells against 5.
    GLASS = _glass(gi, bg)
    if GLASS is None:
        return [row[:] for row in gi]
    glass = {(r, c) for r in range(H) for c in range(W) if gi[r][c] == GLASS}
    stuff = {(r, c) for r in range(H) for c in range(W)
             if gi[r][c] not in (bg, GLASS)}
    pieces = _blobs(stuff)

    go = [row[:] for row in gi]
    for mirror in _blobs(glass):
        rows = {p[0] for p in mirror}
        cols = {p[1] for p in mirror}
        if len(mirror) == 1:
            y0, x0 = mirror[0]
            flip = lambda p: (2 * y0 - p[0], 2 * x0 - p[1])
        elif len(rows) == 1:
            y0 = rows.pop()
            flip = lambda p: (2 * y0 - p[0], p[1])
        elif len(cols) == 1:
            x0 = cols.pop()
            flip = lambda p: (p[0], 2 * x0 - p[1])
        else:
            continue
        near = set(mirror)
        for y, x in mirror:
            for dy, dx in N8:
                near.add((y + dy, x + dx))
        for piece in pieces:
            if not (set(piece) & near):
                continue
            for y, x in piece:
                q = flip((y, x))
                if 0 <= q[0] < H and 0 <= q[1] < W:
                    go[q[0]][q[1]] = gi[y][x]
    return go
