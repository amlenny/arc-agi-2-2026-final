"""6e4f6532 -- carry each piece to its socket and turn it to face the walls.

The grid is a set of panels walled off by solid bands of colour.  Inside them
sit PIECES -- bodies carrying a blob and a few marker cells in the wall colours
-- and SOCKETS, loose blobs with the same shape as some piece's blob.

Both colours are read off the board.  The blob colour is the only one whose
pieces PAIR UP: every shape it draws appears an even number of times, once on a
piece and once as the socket waiting for it, congruent up to a turn or a flip.
No other colour does that on any pair.  The body colour is then simply whatever
those blobs are attached to -- far and away the commonest thing beside them.

Each piece travels to the socket matching its 9-blob, and is turned (any of the
eight square symmetries) so that every marker points at the wall of its own
colour in the panel it lands in.  Two markers on perpendicular sides pin the
turn exactly.  The 9-blob comes to rest on the socket, which is why the grid
ends up with half the 9s it started with.
"""

N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
N4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]

TURNS = (
    lambda r, c: (r, c),
    lambda r, c: (c, -r),
    lambda r, c: (-r, -c),
    lambda r, c: (-c, r),
    lambda r, c: (-r, c),
    lambda r, c: (r, -c),
    lambda r, c: (c, r),
    lambda r, c: (-c, -r),
)


def _walls(g, bg):
    """Rows and columns given over entirely to one wall colour."""
    H, W = len(g), len(g[0])
    rows, cols = {}, {}
    for _ in range(3):
        for r in range(H):
            seen = {g[r][c] for c in range(W) if c not in cols}
            if len(seen) == 1 and bg not in seen:
                rows[r] = seen.pop()
        for c in range(W):
            seen = {g[r][c] for r in range(H) if r not in rows}
            if len(seen) == 1 and bg not in seen:
                cols[c] = seen.pop()
    return rows, cols


def _spans(n, cut):
    out, cur = [], []
    for i in range(n):
        if i in cut:
            if cur:
                out.append(cur)
            cur = []
        else:
            cur.append(i)
    if cur:
        out.append(cur)
    return out


def _panels(g, rows, cols):
    """Each open rectangle, with the wall colour on each of its four sides."""
    H, W = len(g), len(g[0])
    out = []
    for rs in _spans(H, rows):
        for cs in _spans(W, cols):
            side = {}
            if rs[0] - 1 in rows:
                side[(-1, 0)] = rows[rs[0] - 1]
            if rs[-1] + 1 in rows:
                side[(1, 0)] = rows[rs[-1] + 1]
            if cs[0] - 1 in cols:
                side[(0, -1)] = cols[cs[0] - 1]
            if cs[-1] + 1 in cols:
                side[(0, 1)] = cols[cs[-1] + 1]
            out.append({"rows": (rs[0], rs[-1]), "cols": (cs[0], cs[-1]), "side": side})
    return out


def _blobs(g, bg, rows, cols):
    H, W = len(g), len(g[0])
    free = lambda y, x: (0 <= y < H and 0 <= x < W and y not in rows
                         and x not in cols and g[y][x] != bg)
    seen, out = set(), []
    for r in range(H):
        for c in range(W):
            if not free(r, c) or (r, c) in seen:
                continue
            st, comp = [(r, c)], []
            seen.add((r, c))
            while st:
                y, x = st.pop()
                comp.append((y, x))
                for dy, dx in N8:
                    if free(y + dy, x + dx) and (y + dy, x + dx) not in seen:
                        seen.add((y + dy, x + dx))
                        st.append((y + dy, x + dx))
            out.append(comp)
    return out


def _norm(cells):
    r0 = min(p[0] for p in cells)
    c0 = min(p[1] for p in cells)
    return frozenset((p[0] - r0, p[1] - c0) for p in cells)


def _outward(p, core):
    """Which way a marker faces: away from the cell of the piece it is stuck to."""
    for dy, dx in N4:
        if (p[0] + dy, p[1] + dx) in core:
            return (-dy, -dx)
    return None


def _cast(g):
    """Blob colour, then body colour: the blob's pieces pair up congruently, the body is what
    they lean on."""
    from collections import Counter as _C, deque as _D

    H, W = len(g), len(g[0])
    tally = _C(v for row in g for v in row)
    bg = tally.most_common(1)[0][0]

    def pieces(v):
        seen, out = set(), []
        for r in range(H):
            for c in range(W):
                if g[r][c] != v or (r, c) in seen:
                    continue
                q, cur = _D([(r, c)]), []
                seen.add((r, c))
                while q:
                    y, x = q.popleft()
                    cur.append((y, x))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        a, b = y + dy, x + dx
                        if 0 <= a < H and 0 <= b < W and (a, b) not in seen and g[a][b] == v:
                            seen.add((a, b))
                            q.append((a, b))
                out.append(cur)
        return out

    def canon(cells):
        best = None
        for k in range(4):
            cells = [(c, -r) for r, c in cells]
            for m in (cells, [(r, -c) for r, c in cells]):
                r0 = min(r for r, _ in m); c0 = min(c for _, c in m)
                k2 = tuple(sorted((r - r0, c - c0) for r, c in m))
                if best is None or k2 < best:
                    best = k2
        return best

    PIN = None
    for v in tally:
        if v == bg:
            continue
        ps = pieces(v)
        if len(ps) > 1 and all(n % 2 == 0 for n in _C(canon(p) for p in ps).values()):
            PIN = v
            break
    if PIN is None:
        return None, None
    nb = _C()
    for r in range(H):
        for c in range(W):
            if g[r][c] != PIN:
                continue
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = r + dy, c + dx
                if 0 <= a < H and 0 <= b < W and g[a][b] not in (PIN, bg):
                    nb[g[a][b]] += 1
    if not nb:
        return None, None
    return nb.most_common(1)[0][0], PIN


def transform(gi):
    BODY, PIN = _cast(gi)
    if PIN is None or BODY is None:
        return [row[:] for row in gi]
    H, W = len(gi), len(gi[0])
    flat = [v for row in gi for v in row]
    bg = max(set(flat), key=flat.count)
    rows, cols = _walls(gi, bg)
    panels = _panels(gi, rows, cols)

    pieces, sockets = [], []
    for comp in _blobs(gi, bg, rows, cols):
        kinds = {gi[y][x] for y, x in comp}
        (pieces if BODY in kinds else sockets if kinds == {PIN} else []).append(comp)

    go = [row[:] for row in gi]
    for comp in pieces + sockets:
        for y, x in comp:
            go[y][x] = bg

    for comp in pieces:
        core = {(y, x) for y, x in comp if gi[y][x] in (BODY, PIN)}
        marks = [((y, x), gi[y][x], _outward((y, x), core))
                 for y, x in comp if gi[y][x] not in (BODY, PIN)]
        for sock in sockets:
            panel = _sit(panels, sock[0])
            if panel is None:
                continue
            for turn in TURNS:
                if not all(m[2] and panel["side"].get(turn(*m[2])) == m[1] for m in marks):
                    continue
                spun = [(turn(y, x), gi[y][x]) for y, x in comp]
                got = [p for p, v in spun if v == PIN]
                if _norm(got) != _norm(sock) or len(got) != len(sock):
                    continue
                dr = min(p[0] for p in sock) - min(p[0] for p in got)
                dc = min(p[1] for p in sock) - min(p[1] for p in got)
                if {(p[0] + dr, p[1] + dc) for p in got} != set(sock):
                    continue
                for (y, x), v in spun:
                    go[y + dr][x + dc] = v
                sockets.remove(sock)
                break
            else:
                continue
            break
    return go


def _sit(panels, p):
    for q in panels:
        if q["rows"][0] <= p[0] <= q["rows"][1] and q["cols"][0] <= p[1] <= q["cols"][1]:
            return q
    return None
