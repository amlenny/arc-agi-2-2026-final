"""faa9f03d -- wires drawn wrong, redrawn right.

Every colour other than the two marker colours is one WIRE: a rook path of
straight runs whose two ends leave the grid.  The drawing of it is faulty in
three separate ways, and each fault has its own repair:

  * gaps            -- a wire is missing cells mid-run.  Fill them.
  * colour 4        -- sits next to a corner and points the way the arm off
                       that corner really goes.  The arm as drawn leaves the
                       corner the OTHER way: delete it, and everything hanging
                       off it, and run a fresh arm from the corner in the 4's
                       direction to the edge of the grid.
  * colour 2 (red)  -- marks the corners of a wire, and marks that wire as
                       drawn on the WRONG SIDE.  Its depth is inverted: where
                       the drawing has it in front it belongs behind, and where
                       the drawing has it behind it belongs in front.

So the over/under is read off the drawing and then flipped for every wire
carrying red.  Where two wires cross, the one in front is unbroken and the one
behind is cut.
"""

def _cast(gi):
    """Board, wires, corner-mark and arrow-mark, read off the grid.

    A wire is a rook path, so it has a long straight run: every wire here has at least 5 collinear
    cells and no mark has more than 4. Of the two marks, the corner mark is the one that sits ON a
    bend -- a cell with a wire neighbour both vertically and horizontally. The arrow sits beside a
    corner rather than on it and never touches two perpendicular arms. Measured across the five
    pairs: the corner mark lands on a bend 2 of 4, 8 of 8 and 6 of 6 times, the arrow 0 of 1, 0 of 1
    and 0 of 2. Either mark may be absent from a pair, which is why one cannot be inferred from the
    other's absence.
    """
    H, W = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    BG = max(tally, key=lambda k: tally[k])
    wires, marks = set(), []
    for v in tally:
        if v == BG:
            continue
        run = max([sum(1 for c in range(W) if gi[r][c] == v) for r in range(H)]
                  + [sum(1 for r in range(H) if gi[r][c] == v) for c in range(W)])
        (wires.add(v) if run >= 5 else marks.append(v))
    RED = ARROW = None
    for v in marks:
        bend = False
        for r in range(H):
            for c in range(W):
                if gi[r][c] != v:
                    continue
                near = [(dy, dx) for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))
                        if 0 <= r + dy < H and 0 <= c + dx < W and gi[r + dy][c + dx] in wires]
                if any(d[0] for d in near) and any(d[1] for d in near):
                    bend = True
        if bend:
            RED = v
        else:
            ARROW = v
    return BG, RED, ARROW


N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


# ---------------------------------------------------------------- wire pieces

def _owners(g, cols, RED):
    """Which wire each red marker belongs to."""
    H, W = len(g), len(g[0])
    own = {}
    reds = [(r, c) for r in range(H) for c in range(W) if g[r][c] == RED]
    for _ in range(len(reds) + 1):
        for p in reds:
            if p in own:
                continue
            near = set()
            for dy, dx in N4:
                y, x = p[0] + dy, p[1] + dx
                if 0 <= y < H and 0 <= x < W:
                    if g[y][x] in cols:
                        near.add(g[y][x])
                    elif (y, x) in own:
                        near.add(own[(y, x)])
            if len(near) == 1:
                own[p] = near.pop()
    return own


def _legends(v, d, drawn, H, W):
    """Where a leg leaving v in direction d may end: a drawn cell with nothing
    drawn immediately beyond it, holding at least one more drawn cell than v."""
    out = []
    p, seen = v, 0
    while True:
        p = (p[0] + d[0], p[1] + d[1])
        if not (0 <= p[0] < H and 0 <= p[1] < W):
            break
        if p in drawn:
            seen += 1
            nxt = (p[0] + d[0], p[1] + d[1])
            if nxt not in drawn and seen >= 1:
                out.append(p)
    return out


def _leg(v, w):
    dy = (w[0] > v[0]) - (w[0] < v[0])
    dx = (w[1] > v[1]) - (w[1] < v[1])
    n = max(abs(w[0] - v[0]), abs(w[1] - v[1]))
    return [(v[0] + dy * k, v[1] + dx * k) for k in range(n + 1)]


def _path(drawn, H, W):
    """The wire as drawn: the shortest chain of straight legs that covers every
    drawn cell and leaves the grid at both ends."""
    def onedge(p):
        return p[0] in (0, H - 1) or p[1] in (0, W - 1)

    starts = sorted(p for p in drawn if onedge(p))

    def dfs(verts, d, covered, used, budget):
        v = verts[-1]
        if budget == 0:
            return None
        for w in _legends(v, d, drawn, H, W):
            cells = _leg(v, w)
            if any(p in used for p in cells[1:]):
                continue
            got = covered | (drawn & set(cells))
            if len(got) == len(covered):
                continue
            if len(got) == len(drawn) and onedge(w):
                return verts + [w]
            for e in N4:
                if e[0] * d[0] + e[1] * d[1] == 0:
                    r = dfs(verts + [w], e, got, used | set(cells), budget - 1)
                    if r:
                        return r
        return None

    for legs in range(1, 13):
        for s in starts:
            for d in N4:
                r = dfs([s], d, {s}, {s}, legs)
                if r:
                    return r
    return None


def _cells(verts):
    out = set()
    for p, q in zip(verts, verts[1:]):
        out.update(_leg(p, q))
    return out


# ------------------------------------------------------------------ the arrow


def _redirect(verts, corner, d, H, W):
    """Cut the arm that leaves `corner` the wrong way and run a new one in
    direction d to the edge."""
    i = verts.index(corner)
    back = (-d[0], -d[1])
    side = None
    for j in (i - 1, i + 1):
        if 0 <= j < len(verts):
            v = verts[j]
            step = ((v[0] > corner[0]) - (v[0] < corner[0]),
                    (v[1] > corner[1]) - (v[1] < corner[1]))
            if step == back:
                side = j
    if side is None:
        return verts
    end = corner
    while 0 <= end[0] + d[0] < H and 0 <= end[1] + d[1] < W:
        end = (end[0] + d[0], end[1] + d[1])
    kept = verts[i:] if side < i else verts[: i + 1]
    return ([end] + kept) if side < i else (kept + [end])


# ----------------------------------------------------------------- transform

def transform(gi):
    H, W = len(gi), len(gi[0])
    BG, RED, ARROW = _cast(gi)
    cols = sorted({v for row in gi for v in row} - {BG, RED, ARROW})
    own = _owners(gi, cols, RED)

    drawn, reds, before = {}, {}, {}
    for c in cols:
        reds[c] = {p for p, o in own.items() if o == c}
        drawn[c] = {(r, x) for r in range(H) for x in range(W) if gi[r][x] == c} | reds[c]
        before[c] = _path(drawn[c], H, W)
        if before[c] is None:
            return [row[:] for row in gi]

    after = {c: list(v) for c, v in before.items()}
    for r in range(H):
        for x in range(W):
            if gi[r][x] != ARROW:
                continue
            for dy, dx in N4:
                y, z = r - dy, x - dx
                if not (0 <= y < H and 0 <= z < W):
                    continue
                for c in cols:
                    if (y, z) in after[c][1:-1]:
                        after[c] = _redirect(after[c], (y, z), (dy, dx), H, W)

    ink = {c: _cells(after[c]) for c in cols}
    was = {c: _cells(before[c]) for c in cols}

    above = set()
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            vote = None
            for p in was[a] & was[b]:
                if gi[p[0]][p[1]] == a:
                    vote = (a, b)
                elif gi[p[0]][p[1]] == b:
                    vote = (b, a)
            if vote is None:
                continue
            if (bool(reds[a]) != bool(reds[b])):
                vote = (vote[1], vote[0])
            above.add(vote)

    order, left = [], list(cols)
    while left:
        low = [c for c in left if not any(t == c and o in left for t, o in above)]
        order += low
        left = [c for c in left if c not in low]

    go = [[BG] * W for _ in range(H)]
    for c in order:
        for y, x in ink[c]:
            go[y][x] = c
    return go

