"""e8686506 -- the loose pieces fit together into one block.

Scattered about the board are pieces that between them tile a rectangle exactly,
each staying the way up it was found, and the rectangle is as wide as the widest
piece.  More than one way of fitting them usually works; the one wanted is the
one where the pieces stay the pieces -- no two of the same colour ending up
against each other, which would read as a single larger piece.

The lone cells are the last to go in: they take whatever gaps the real pieces
leave.
"""


def _pieces(gi, bg):
    """Every piece on the board: its colour and its shape, corner-joins counting."""
    H, W = len(gi), len(gi[0])
    seen, out = set(), []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or gi[r][c] == bg:
                continue
            hue = gi[r][c]
            stack, cur = [(r, c)], []
            seen.add((r, c))
            while stack:
                x, y = stack.pop()
                cur.append((x, y))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        a, b = x + dx, y + dy
                        if 0 <= a < H and 0 <= b < W and (a, b) not in seen and gi[a][b] == hue:
                            seen.add((a, b))
                            stack.append((a, b))
            r0 = min(x for x, _ in cur)
            c0 = min(y for _, y in cur)
            out.append((hue, tuple(sorted((x - r0, y - c0) for x, y in cur))))
    return out


def transform(gi):
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])

    pieces = _pieces(gi, bg)
    want = sorted((hue, tuple(cells)) for hue, cells in pieces)
    lumps = [p for p in pieces if len(p[1]) > 1]
    crumbs = [p[0] for p in pieces if len(p[1]) == 1]
    total = sum(len(p[1]) for p in pieces)
    wide = max(max(b for _, b in p[1]) + 1 for p in pieces)
    tall = max(max(a for a, _ in p[1]) + 1 for p in pieces)

    for W in range(wide, total + 1):
        if total % W or total // W < tall:
            continue
        H = total // W
        board = [[None] * W for _ in range(H)]
        used = [False] * len(lumps)
        answer = []

        def fit(spare):
            if answer:
                return
            spot = next(((r, c) for r in range(H) for c in range(W) if board[r][c] is None), None)
            if spot is None:
                laid = [[v if v != "?" else crumbs[0] for v in row] for row in board]
                if sorted(_pieces(laid, None)) == want:
                    answer.append(laid)
                return
            for i, (hue, cells) in enumerate(lumps):
                if used[i]:
                    continue
                off = (spot[0] - cells[0][0], spot[1] - cells[0][1])
                put = [(a + off[0], b + off[1]) for a, b in cells]
                if any(not (0 <= a < H and 0 <= b < W) or board[a][b] is not None for a, b in put):
                    continue
                used[i] = True
                for a, b in put:
                    board[a][b] = hue
                fit(spare)
                for a, b in put:
                    board[a][b] = None
                used[i] = False
            if spare:
                board[spot[0]][spot[1]] = "?"
                fit(spare - 1)
                board[spot[0]][spot[1]] = None

        fit(len(crumbs))
        if answer:
            return answer[0]
    return [row[:] for row in gi]
