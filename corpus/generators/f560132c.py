"""f560132c -- the odd shape carries the plan, the rest are the pieces.

One shape is speckled inside with a small block of other colours: that block is
the PLAN.  It says how the finished square is laid out -- which colour sits
top-left, which sits middle-right, and so on.  A blank cell in the plan means
that quarter of the square is left empty.

Every shape on the board, the speckled one included, is a piece.  Turned as
needed they tile a square exactly, and each piece is repainted in the plan
colour of the quarter it settles in.  The piece carrying the plan is laid down
just as it lies -- that is what fixes which way up the finished square goes.
"""

N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
N4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]


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


def _plug(comp):
    """The piece as a solid: its cells plus any pocket sealed inside it."""
    held = set(comp)
    r0 = min(p[0] for p in held); r1 = max(p[0] for p in held)
    c0 = min(p[1] for p in held); c1 = max(p[1] for p in held)
    free, edge = set(), []
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if (r, c) not in held:
                free.add((r, c))
                if r in (r0, r1) or c in (c0, c1):
                    edge.append((r, c))
    out, st = set(edge), list(edge)
    while st:
        y, x = st.pop()
        for dy, dx in N4:
            q = (y + dy, x + dx)
            if q in free and q not in out:
                out.add(q)
                st.append(q)
    return held | (free - out)


def _turns(cells):
    r0 = min(p[0] for p in cells); c0 = min(p[1] for p in cells)
    base = [(r - r0, c - c0) for r, c in cells]
    seen, out = set(), []
    for k in range(4):
        pts = base
        for _ in range(k % 4):
            pts = [(c, -r) for r, c in pts]
        a = min(p[0] for p in pts); b = min(p[1] for p in pts)
        key = frozenset((r - a, c - b) for r, c in pts)
        if key not in seen:
            seen.add(key)
            out.append(sorted(key))
    return out


def _pack(pieces, n, fits):
    board = [[-1] * n for _ in range(n)]
    order = sorted(range(len(pieces)), key=lambda i: -len(pieces[i][0]))

    def go(used):
        spot = next(((r, c) for r in range(n) for c in range(n) if board[r][c] < 0), None)
        if spot is None:
            return fits(board)
        for i in order:
            if i in used:
                continue
            for shape in pieces[i]:
                dy, dx = spot[0] - shape[0][0], spot[1] - shape[0][1]
                put = [(r + dy, c + dx) for r, c in shape]
                if any(not (0 <= r < n and 0 <= c < n) or board[r][c] >= 0 for r, c in put):
                    continue
                for r, c in put:
                    board[r][c] = i
                if go(used | {i}):
                    return True
                for r, c in put:
                    board[r][c] = -1
        return False

    return board if go(frozenset()) else None


def transform(gi):
    H, W = len(gi), len(gi[0])
    # The board is the commonest colour -- 0 on every pair here, read rather than assumed. A blank
    # square in the plan is board colour too, and it is painted as such.
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])
    comps = _blobs({(r, c) for r in range(H) for c in range(W) if gi[r][c] != bg})

    plan, spot = None, None
    for comp in comps:
        shade = {gi[y][x] for y, x in comp}
        if len(shade) == 1:
            continue
        body = max(shade, key=lambda v: sum(1 for y, x in comp if gi[y][x] == v))
        odd = [(y, x) for y, x in comp if gi[y][x] != body]
        r0 = min(p[0] for p in odd); r1 = max(p[0] for p in odd)
        c0 = min(p[1] for p in odd); c1 = max(p[1] for p in odd)
        plan = [[gi[r][c] if (r, c) in set(odd) else bg for c in range(c0, c1 + 1)]
                for r in range(r0, r1 + 1)]
        spot = comps.index(comp)
    if plan is None:
        return [row[:] for row in gi]

    solid = [_plug(comp) for comp in comps]
    n = int(round(sum(len(s) for s in solid) ** 0.5))
    if n * n != sum(len(s) for s in solid):
        return [row[:] for row in gi]

    k = len(plan)
    step = n / k

    def berth(board):
        out = {}
        for i in range(len(solid)):
            pts = [(r, c) for r in range(n) for c in range(n) if board[r][c] == i]
            my = sum(p[0] for p in pts) / len(pts)
            mx = sum(p[1] for p in pts) / len(pts)
            out[i] = (min(k - 1, int(my // step)), min(k - 1, int(mx // step)))
        return out

    lay = [_turns(s) for s in solid]
    lay[spot] = lay[spot][:1]              # the plan-bearing piece is never turned
    board = _pack(lay, n,
                  lambda b: len(set(berth(b).values())) == len(solid))
    if board is None:
        return [row[:] for row in gi]

    seat = {i: plan[a][b] for i, (a, b) in berth(board).items()}
    return [[seat[board[r][c]] for c in range(n)] for r in range(n)]
