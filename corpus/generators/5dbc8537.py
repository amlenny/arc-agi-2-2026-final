# Rule authored from the evaluation demonstrations of 5dbc8537.
#
# The grid is two panels. One is a BOARD: a plain background punched with holes. The other holds
# loose MOTIFS. The answer is the board with every hole filled by the motif that fits it, and the
# board's dimensions are the answer's.
#
#   * the split runs down a column in demo 0 and across a row in demo 1, so the seam is found
#     rather than assumed — it is where the dominant colour of a line changes.
#   * THE HOLE COLOUR IS THE OTHER PANEL'S BACKGROUND. That is what ties the halves together and
#     identifies which of the two is the board.
#   * the motifs tile the holes exactly: same cell count, translation only, no rotation.
#
# A MOTIF IS A CONNECTED RUN OF ANYTHING NOT BACKGROUND — never one component per colour. Demo 1's
# first motif is a 4/7 CHECKERBOARD and its fourth is a ring of 1s with 9s inside it. Split by
# colour, the checkerboard becomes twenty-four separate single cells; the tiling then has many
# solutions and the answer's alternating run is unreachable except by luck. A solver built that way
# returns a perfectly valid cover that is wrong in thirty-one cells. Held together, each motif is
# one rigid piece and the cover is all but forced.
#
# The cover is Algorithm X over bitmasks with the pieces counted by FORM rather than tracked
# individually, and failed (covered, counts) states memoised — identical motifs otherwise reach the
# same board by different orders and the same dead subtree is re-explored factorially.
from collections import Counter, deque


def _shapes(panel, bg):
    """The motifs, as connected runs of ANYTHING that is not background.

    NOT one component per colour. Demo 1's first motif is a 4/7 CHECKERBOARD and its fourth is a
    ring of 1s with 9s inside; splitting components by colour shatters the checkerboard into
    twenty-four separate cells, and the tiling then has many solutions of which the intended one is
    merely one — the answer's alternating 4747 run is unreachable as anything but luck. Held
    together, each motif is one rigid piece and the cover is decided.
    """
    h, w = len(panel), len(panel[0])
    seen, out = set(), []
    for r in range(h):
        for c in range(w):
            if panel[r][c] == bg or (r, c) in seen:
                continue
            q, cs = deque([(r, c)]), []
            seen.add((r, c))
            while q:
                y, x = q.popleft()
                cs.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    a, b = y + dy, x + dx
                    if (0 <= a < h and 0 <= b < w and (a, b) not in seen and panel[a][b] != bg):
                        seen.add((a, b))
                        q.append((a, b))
            r0 = min(y for y, _ in cs); c0 = min(x for _, x in cs)
            out.append(tuple(sorted((y - r0, x - c0, panel[y][x]) for y, x in cs)))
    return out


def _fill(board, holes, shapes, hole_col):
    """Exact cover of the hole cells by the shapes, translation only.

    ALGORITHM X OVER BITMASKS, with the pieces counted by FORM rather than tracked individually.
    Three things make the difference on demo 1, which is a single 74-cell region covered by 34
    pieces drawn from 10 forms, many of them one or two cells:

      * cells are numbered and every placement is a bitmask, so overlap and cover are one machine
        instruction rather than a set operation
      * the search always expands the LOWEST uncovered cell and, among the columns, prefers the one
        with fewest surviving placements — Knuth's S heuristic, which is what stops the branching
        factor exploding on the single-cell pieces
      * failed states are MEMOISED on (covered, remaining counts). Identical pieces reach the same
        board by different orders, and without this the same dead subtree is re-explored
        factorially many times. This is the one that actually decides it.
    """
    H, W = len(board), len(board[0])
    cells = sorted(holes)
    idx = {c: i for i, c in enumerate(cells)}
    N = len(cells)

    stock = {}
    for sh in shapes:
        stock[sh] = stock.get(sh, 0) + 1
    forms = sorted(stock)
    counts = tuple(stock[f] for f in forms)

    plc = [[] for _ in forms]                      # form -> [(mask, [cell indices])]
    for fi, cs in enumerate(forms):
        for r in range(H):
            for c in range(W):
                spots = [(r + dy, c + dx, v) for dy, dx, v in cs]
                if all((y, x) in idx for y, x, _ in spots):
                    m = 0
                    for y, x, _ in spots:
                        m |= 1 << idx[(y, x)]
                    plc[fi].append((m, spots))
    by_cell = [[] for _ in range(N)]
    for fi, lst in enumerate(plc):
        for m, spots in lst:
            for y, x, _ in spots:
                by_cell[idx[(y, x)]].append((fi, m, spots))

    FULL = (1 << N) - 1
    dead = set()

    def solve(cov, cnt):
        if cov == FULL:
            return [] if not any(cnt) else None
        key = (cov, cnt)
        if key in dead:
            return None
        # Knuth's S heuristic: the uncovered cell with the fewest surviving placements
        best_i, best = None, None
        rest = ~cov & FULL
        i = 0
        t = rest
        while t:
            if t & 1:
                opts = [(fi, m, sp) for fi, m, sp in by_cell[i] if cnt[fi] and not (m & cov)]
                if not opts:
                    dead.add(key)
                    return None
                if best is None or len(opts) < len(best):
                    best_i, best = i, opts
                    if len(opts) == 1:
                        break
            t >>= 1
            i += 1
        for fi, m, sp in best:
            nc = list(cnt)
            nc[fi] -= 1
            got = solve(cov | m, tuple(nc))
            if got is not None:
                return [(fi, sp)] + got
        dead.add(key)
        return None

    got = solve(0, counts)
    if got is None:
        return None
    out = [row[:] for row in board]
    for _, sp in got:
        for y, x, v in sp:
            out[y][x] = v
    return out


def transform(grid):
    h, w = len(grid), len(grid[0])
    # FIND THE SEAM instead of trying every cut. The two panels have different backgrounds, so
    # the seam is where the dominant colour of a column (or row) changes. Sweeping all w + h cuts
    # and packing each is exponential work for a boundary that is directly observable.
    def seams(vectors):
        dom = [Counter(v).most_common(1)[0][0] for v in vectors]
        return [i for i in range(1, len(dom)) if dom[i] != dom[i - 1]]

    cols = [[grid[r][c] for r in range(h)] for c in range(w)]
    splits = ([("v", k) for k in seams(cols)] + [("h", k) for k in seams(grid)])
    for kind, k in splits:
        if kind == "v":
            P = [[row[:k] for row in grid], [row[k:] for row in grid]]
        else:
            P = [grid[:k], grid[k:]]
        for a in (0, 1):
            board, spanel = P[a], P[1 - a]
            bcnt = Counter(v for row in board for v in row)
            scnt = Counter(v for row in spanel for v in row)
            if len(bcnt) != 2 or len(scnt) < 2:
                continue
            bbg = bcnt.most_common(1)[0][0]
            hole_col = [x for x in bcnt if x != bbg][0]
            sbg = scnt.most_common(1)[0][0]
            # THE HOLE COLOUR IS THE OTHER PANEL'S BACKGROUND. That is what ties the two halves
            # together and what identifies which half is the board.
            if hole_col != sbg:
                continue
            shapes = sorted(_shapes(spanel, sbg), key=len, reverse=True)
            holes = {(r, c) for r in range(len(board)) for c in range(len(board[0]))
                     if board[r][c] == hole_col}
            if not shapes or sum(len(s) for s in shapes) != len(holes):
                continue
            got = _fill(board, holes, shapes, hole_col)
            if got is not None:
                return got
    return [row[:] for row in grid]
