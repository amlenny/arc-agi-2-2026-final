"""6ffbe589 -- the dial is square and each colour turns by its own count.

One square panel holds the picture.  Scattered outside it are loose scraps, one
per colour.  A scrap says how far that colour turns: a quarter turn clockwise
for every cell it holds.  A colour with no scrap outside does not turn at all.

The answer is the panel alone, each colour layer spun on the spot by its own
number of quarter turns.  The scraps are spent and do not appear.
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


def _panel(parts):
    """The panel: the big huddle of pieces.  Pieces within two cells of each
    other belong to the same huddle; the scraps lie well clear of it."""
    root = list(range(len(parts)))

    def find(i):
        while root[i] != i:
            root[i] = root[root[i]]
            i = root[i]
        return i

    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            if any(abs(y - b) <= 2 and abs(x - a) <= 2
                   for y, x in parts[i] for b, a in parts[j]):
                root[find(i)] = find(j)
    huddle = {}
    for i in range(len(parts)):
        huddle.setdefault(find(i), []).extend(parts[i])
    big = max(huddle.values(), key=len)
    ys = [y for y, _ in big]
    xs = [x for _, x in big]
    return min(ys), min(xs), max(max(ys) - min(ys), max(xs) - min(xs)) + 1


def transform(gi):
    H, W = len(gi), len(gi[0])
    flat = [v for row in gi for v in row]
    bg = max(set(flat), key=flat.count)
    shades = set(flat) - {bg}

    parts = _blobs({(r, c) for r in range(H) for c in range(W) if gi[r][c] != bg})
    spot = _panel(parts)
    if spot is None:
        return [row[:] for row in gi]
    r0, c0, n = spot

    turns = {}
    for col in shades:
        turns[col] = sum(1 for r in range(H) for c in range(W)
                         if gi[r][c] == col and not (r0 <= r < r0 + n and c0 <= c < c0 + n)) % 4

    go = [[bg] * n for _ in range(n)]
    for r in range(n):
        for c in range(n):
            col = gi[r0 + r][c0 + c]
            if col == bg:
                continue
            y, x = r, c
            for _ in range(turns[col]):
                y, x = x, n - 1 - y
            go[y][x] = col
    return go
