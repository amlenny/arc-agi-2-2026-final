# Rule authored from the evaluation demonstrations of dd6b8c4b.
#
# A 3x3 BOX sits in a maze of walls, and loose cells of one colour are scattered about. The box
# fills with that colour — ONE CELL PER LOOSE CELL CONSUMED — in reading order across its nine
# cells, centre included. The loose cells that are consumed vanish; the rest stay put.
#
# ONLY WHAT THE BOX CAN REACH is available. The walls pen it in: a loose cell counts only if it can
# be reached from the box without crossing one. Demo 0's box sits in a corridor with a single gap
# and consumes exactly the two cells beyond it, leaving nine others untouched — including a pair
# sealed inside a closed ring. Demo 2 has no walls at all and every loose cell goes. Test 1 has two
# sealed at the top edge, which is what keeps the count at nine.
#
# THE BACKGROUND IS WHAT LINES THE BORDER, not the commonest colour: test 0 is a dense maze whose
# walls outnumber its open space 52 to 49, and a straight tally names the wall colour as background.
#
# THE BOX is found by its counts — ring colour appearing exactly eight times on the grid, centre
# colour once. Walls throw up plenty of 3x3s with a uniform ring and a different middle.
#
# ORDER OF CONSUMPTION: lone cells first, then whole clusters by how near they lie — by DISTANCE,
# not by size. Demo 1 swallows a nearer two-cell cluster entire, then peels one cell off a five-cell
# one, passing over a farther two-cell cluster completely. Ties between equally distant clusters go
# by reading order, which is the whole of the difference on test 1.
from collections import Counter, deque


def _groups(cells):
    """4-connected clusters of a cell set."""
    left, out = set(cells), []
    while left:
        seed = next(iter(left))
        q, grp = deque([seed]), []
        left.discard(seed)
        while q:
            y, x = q.popleft()
            grp.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (y + dy, x + dx)
                if n in left:
                    left.discard(n)
                    q.append(n)
        out.append(grp)
    return out


def transform(grid):
    h, w = len(grid), len(grid[0])
    # THE BACKGROUND IS WHAT LINES THE BORDER, not the commonest colour. Test 0 is a dense maze
    # whose walls outnumber its open space 52 to 49, and a straight tally names the wall colour as
    # background — after which nothing else resolves.
    edge = ([grid[0][c] for c in range(w)] + [grid[h - 1][c] for c in range(w)]
            + [grid[r][0] for r in range(h)] + [grid[r][w - 1] for r in range(h)])
    bg = Counter(edge).most_common(1)[0][0]

    # THE BOX is the 3x3 whose ring is one colour and whose centre is another.
    # its ring colour occurs EXACTLY eight times on the grid and its centre colour once — walls
    # throw up plenty of 3x3s with a uniform ring, and taking any of them finds the wrong box.
    tally = Counter(v for row in grid for v in row)
    box = None
    for r in range(h - 2):
        for c in range(w - 2):
            ring = [grid[r + a][c + b] for a in range(3) for b in range(3) if (a, b) != (1, 1)]
            mid = grid[r + 1][c + 1]
            if (len(set(ring)) == 1 and ring[0] != bg and mid != bg and mid != ring[0]
                    and tally[ring[0]] == 8 and tally[mid] == 1):
                box = (r, c, ring[0], mid)
                break
        if box:
            break
    if box is None:
        return [row[:] for row in grid]
    br, bc, bcol, mcol = box
    bcells = [(br + a, bc + b) for a in range(3) for b in range(3)]

    rest = {v for row in grid for v in row} - {bg, bcol, mcol}
    if not rest:
        return [row[:] for row in grid]
    if len(rest) == 1:
        loose, wall = rest.pop(), None
    else:
        # the WALL is the colour with the biggest single structure; the other is scattered
        def biggest(col):
            return max((len(g) for g in _groups({(r, c) for r in range(h) for c in range(w)
                                                 if grid[r][c] == col})), default=0)
        wall = max(rest, key=biggest)
        loose = [c for c in rest if c != wall][0]

    # WHAT THE BOX CAN REACH. The walls pen it in: only loose cells reachable from the box without
    # crossing one are available. Demo 0's box sits in a corridor with a single gap, and the only
    # loose cells through it are the two the answer consumes; demo 2 has no walls at all and every
    # one goes.
    seen, q = set(), deque()
    for (y, x) in bcells:
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = y + dy, x + dx
            if (0 <= a < h and 0 <= b < w and (a, b) not in bcells
                    and grid[a][b] != wall and (a, b) not in seen):
                seen.add((a, b)); q.append((a, b))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = y + dy, x + dx
            if (0 <= a < h and 0 <= b < w and (a, b) not in seen and (a, b) not in bcells
                    and grid[a][b] != wall):
                seen.add((a, b))
                q.append((a, b))

    avail = {p for p in seen if grid[p[0]][p[1]] == loose}
    # ISOLATED CELLS ARE TAKEN FIRST, then the nearest member of a cluster — demo 1 has capacity for
    # nine, finds eight lone cells, and peels exactly one cell off its five-cell cluster.
    # LONE CELLS FIRST, then whole clusters in order of how near they lie — by DISTANCE, not by
    # size. Demo 1 swallows a nearer two-cell cluster entire, then peels a single cell off a
    # five-cell one, passing over a farther two-cell cluster completely.
    cy, cx = br + 1, bc + 1

    def near(g):
        return min(max(abs(p[0] - cy), abs(p[1] - cx)) for p in g)

    order = []
    for g in sorted(_groups(avail),
                    key=lambda g: (0 if len(g) == 1 else 1, near(g), min(g))):
        for p in sorted(g, key=lambda p: (max(abs(p[0] - cy), abs(p[1] - cx)), p)):
            order.append(p)
    take = order[:len(bcells)]

    out = [row[:] for row in grid]
    for p in take:
        out[p[0]][p[1]] = bg
    for i in range(len(take)):
        y, x = bcells[i]
        out[y][x] = loose
    return out
