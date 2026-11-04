# Rule authored from the evaluation demonstrations of 142ca369.
#
# NOT "each bar emits a ray". There is ONE BALL per launcher, travelling diagonally and BOUNCING
# off the bars, and it takes the colour of whatever it last bounced off. That is why the bars'
# directions looked unfixable: a bar does not choose a direction, it reflects whatever arrives.
#
#   launcher   the L-shaped 3-cell piece (a 2x2 with a corner missing); the ball leaves its
#              corner along the diagonal the L points down, in the L's own colour
#   bounce     the ball turns on the first cell ORTHOGONALLY TOUCHING a reflector, and that cell
#              already carries the new colour. WHICH STEP FLIPS COMES FROM THE SIDE IT TOUCHES,
#              not from the reflector's own shape: touching above or below flips the row step,
#              touching left or right flips the column step. Reading it off the bar's orientation
#              works for demos 1 and 2 and collapses on demo 0, whose reflectors are single
#              cells with no orientation at all.
#   stop       leaving the grid
#
# PIECES ARE 4-CONNECTED, NOT 8-CONNECTED. Every launcher and every bar is orthogonally joined, so
# nothing is lost by it, and diagonal joining is actively wrong: two launchers of the SAME colour
# that meet at a corner merge into one 6-cell piece, which is then read as a reflector and never
# fires. No demo packs launchers that closely; test 0 packs fourteen of them along the edges and
# two such merges cost it 88 cells.
from collections import Counter, deque


def _components(grid, bg):
    h, w = len(grid), len(grid[0])
    seen, out = set(), []
    for r in range(h):
        for c in range(w):
            if grid[r][c] != bg and (r, c) not in seen:
                q = deque([(r, c)])
                seen.add((r, c))
                cells = []
                while q:
                    y, x = q.popleft()
                    cells.append((y, x))
                    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                            n = (y + dy, x + dx)
                            if (0 <= n[0] < h and 0 <= n[1] < w and n not in seen
                                    and grid[n[0]][n[1]] == grid[r][c]):
                                seen.add(n)
                                q.append(n)
                out.append(sorted(cells))
    return out


def _sign(v):
    return (v > 0) - (v < 0)


def transform(grid):
    h, w = len(grid), len(grid[0])
    out = [row[:] for row in grid]
    bg = Counter(v for row in grid for v in row).most_common(1)[0][0]

    bars = {}          # cell -> colour, for every piece that is not a launcher
    launchers = []
    for cells in _components(grid, bg):
        col = grid[cells[0][0]][cells[0][1]]
        rs = {r for r, _ in cells}
        cs = {c for _, c in cells}
        if len(cells) != 3 or len(rs) == 1 or len(cs) == 1:
            for p in cells:
                bars[p] = col
        if len(cells) == 3 and len(rs) > 1 and len(cs) > 1:
            apex = None
            for p in cells:
                if all(abs(p[0] - q[0]) + abs(p[1] - q[1]) == 1 for q in cells if q != p):
                    apex = p
                    break
            if apex is None:
                continue
            arms = [q for q in cells if q != apex]
            dr = -_sign(sum(_sign(q[0] - apex[0]) for q in arms))
            dc = -_sign(sum(_sign(q[1] - apex[1]) for q in arms))
            if dr and dc:
                launchers.append((apex, dr, dc, col))

    for (apex, dr, dc, col) in launchers:
        r, c = apex
        cur = col
        last = None
        for _ in range(4 * h * w):
            r, c = r + dr, c + dc
            if not (0 <= r < h and 0 <= c < w) or (r, c) in bars:
                break
            touch = None
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                n = (r + dy, c + dx)
                if n in bars:
                    touch = (n, dy, dx)
                    break
            if touch and touch[0] != last:
                n, dy, dx = touch
                last = n
                cur = bars[n]
                if dy:
                    dr = -dr
                else:
                    dc = -dc
            elif not touch:
                last = None
            if grid[r][c] == bg:
                out[r][c] = cur
    return out
