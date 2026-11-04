"""a25697e4 -- carry each two-tone tool over and seat it in its socket.

A SOCKET is a one-colour shape with a bite taken out of it: fill the bite and
its bounding box comes out solid.  A TOOL is a two-colour shape lying elsewhere.

Each tool is carried to the socket whose bite its LEADING PART -- one whole
colour of it -- fills exactly, turned however it must be to seat.  If seating it needs a MIRROR rather than a
turn, the tool has been flipped over, and its two colours change places.
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


def _poses(cells):
    out = []
    for k in range(8):
        pts = list(cells)
        for _ in range(k % 4):
            pts = [(c, -r) for r, c in pts]
        if k >= 4:
            pts = [(r, -c) for r, c in pts]
        out.append((k >= 4, pts))
    return out


def transform(gi):
    H, W = len(gi), len(gi[0])
    flat = [v for row in gi for v in row]
    bg = max(set(flat), key=flat.count)

    parts = _blobs({(r, c) for r in range(H) for c in range(W) if gi[r][c] != bg})
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
    lumps = {}
    for i in range(len(parts)):
        lumps.setdefault(find(i), []).extend(parts[i])

    sockets, tools = [], []
    for comp in lumps.values():
        shade = {gi[y][x] for y, x in comp}
        if len(shade) == 1:
            r0 = min(p[0] for p in comp); r1 = max(p[0] for p in comp)
            c0 = min(p[1] for p in comp); c1 = max(p[1] for p in comp)
            bite = {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)} - set(comp)
            if bite:
                sockets.append((comp, bite, (r0, r1, c0, c1)))
        else:
            tools.append(comp)

    go = [row[:] for row in gi]
    for comp in tools:
        for y, x in comp:
            go[y][x] = bg

    taken = set()
    for comp in tools:
        base = [(y, x, gi[y][x]) for y, x in comp]
        pair = sorted({v for _, _, v in base})
        done = False
        for si, (shape, bite, box) in enumerate(sockets):
            if si in taken or done:
                continue
            r0, r1, c0, c1 = box
            for flip, pts in _poses([(y, x) for y, x, _ in base]):
                for (py, px), (ay, ax) in [(p, b) for p in pts for b in bite]:
                    dy, dx = ay - py, ax - px
                    put = [(r + dy, c + dx) for r, c in pts]
                    if any(not (0 <= r < H and 0 <= c < W) for r, c in put):
                        continue
                    inside = {p for p in put if r0 <= p[0] <= r1 and c0 <= p[1] <= c1}
                    if inside != bite:
                        continue
                    seatv = {v for p, (_, _, v) in zip(put, base) if p in inside}
                    if len(seatv) != 1:
                        continue
                    nose = seatv.pop()
                    if any(p not in inside for p, (_, _, v) in zip(put, base) if v == nose):
                        continue
                    swap = {pair[0]: pair[1], pair[1]: pair[0]} if flip else {}
                    for (r, c), (_, _, v) in zip(put, base):
                        go[r][c] = swap.get(v, v)
                    taken.add(si)
                    done = True
                    break
                if done:
                    break
    return go
