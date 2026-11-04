# Rule authored from the evaluation demonstrations of 2b83f449.
#
# Horizontal walls of 8 with a green cap at each end, and 777 triples floating between them. Each
# triple becomes a VERTICAL CONNECTOR: its centre and the wall cells directly above and below turn
# 6, punching through both walls, while its two flanks turn wall colour and bridge the gap. The
# walls are therefore cut by the 6s and joined by the bridges, and what was a stack of separate
# rows becomes a set of connected COMPONENTS.
#
# THE CAPS ARE NOT ALLOCATED, THEY FALL. Every cap belongs to whichever component its own wall end
# is in, drops to that component's lowest row and stacks there. That is the whole conservation
# story: a component holding two caps shows two cells of green, one holding none shows nothing —
# which is why demo 0 has two components with no green at all, and why a row can end up with four
# caps or with none while the total never changes.
#
# WHICH END THEY STACK AT IS FORCED: the end of the bottom run that is not walled off by a 6. Only
# when both ends are clear does the side they came from decide, which happens three times across
# the four pairs.
from collections import deque

BAR = 6                 # painted by the rule; it appears in no input


def _cast(grid):
    """Wall, cap, triple, background -- each named by what it does, not by its number.

    cap     the only colour that never leaves the border: 12/12, 10/10, 18/18 cells on it
    wall    the colour that spans the board between the caps -- most rows of width w-2 or more
            (5, 6, 8 rows against 0, 0, 2 for the background)
    triple  of the two left, the one whose every piece is a horizontal run of exactly three
    """
    h, w = len(grid), len(grid[0])
    hues = {v for row in grid for v in row}
    caps = [v for v in hues
            if all(r in (0, h - 1) or c in (0, w - 1)
                   for r in range(h) for c in range(w) if grid[r][c] == v)]
    if len(caps) != 1:
        return None
    CAP = caps[0]
    wide = {v: sum(1 for r in range(h)
                   if sum(1 for c in range(w) if grid[r][c] == v) >= w - 2)
            for v in hues - {CAP}}
    WALL = max(wide, key=lambda v: wide[v])
    rest = [v for v in hues - {CAP, WALL}]
    if len(rest) != 2:
        return None

    def triples_only(v):
        seen, ok = set(), True
        for r in range(h):
            for c in range(w):
                if grid[r][c] != v or (r, c) in seen:
                    continue
                stack, cur = [(r, c)], []
                seen.add((r, c))
                while stack:
                    y, x = stack.pop()
                    cur.append((y, x))
                    for a, b in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                        if 0 <= a < h and 0 <= b < w and (a, b) not in seen and grid[a][b] == v:
                            seen.add((a, b))
                            stack.append((a, b))
                if len(cur) != 3 or len({y for y, _ in cur}) != 1:
                    ok = False
        return ok

    trips = [v for v in rest if triples_only(v)]
    if len(trips) != 1:
        return None
    TRIPLE = trips[0]
    BG = next(v for v in rest if v != TRIPLE)
    return WALL, CAP, TRIPLE, BG


def transform(grid):
    h, w = len(grid), len(grid[0])
    cast = _cast(grid)
    if cast is None:
        return [row[:] for row in grid]
    WALL, CAP, TRIPLE, BG = cast
    bars = set()
    flanks = set()
    for r in range(h):
        c = 0
        while c < w:
            if grid[r][c] == TRIPLE:
                s = c
                while c < w and grid[r][c] == TRIPLE:
                    c += 1
                mid = (s + c - 1) // 2
                for rr in (r - 1, r, r + 1):
                    if 0 <= rr < h:
                        bars.add((rr, mid))
                for x in range(s, c):
                    if x != mid:
                        flanks.add((r, x))
            else:
                c += 1

    struct = {(r, c) for r in range(h) for c in range(w)
              if (r, c) not in bars and (grid[r][c] in (WALL, CAP) or (r, c) in flanks)}

    seen, comps = set(), []
    for p in sorted(struct):
        if p in seen:
            continue
        q = deque([p])
        seen.add(p)
        g = []
        while q:
            y, x = q.popleft()
            g.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (y + dy, x + dx)
                if n in struct and n not in seen:
                    seen.add(n)
                    q.append(n)
        comps.append(set(g))

    out = [[BG] * w for _ in range(h)]
    for (r, c) in struct:
        out[r][c] = WALL
    for (r, c) in bars:
        out[r][c] = BAR

    for comp in comps:
        owned = [p for p in comp if grid[p[0]][p[1]] == CAP]
        if not owned:
            continue
        bot = max(r for r, _ in comp)
        run = sorted(c for r, c in comp if r == bot)
        lo, hi = run[0], run[-1]
        left_open = lo - 1 < 0 or (bot, lo - 1) not in bars
        right_open = hi + 1 >= w or (bot, hi + 1) not in bars
        if left_open and not right_open:
            side = -1
        elif right_open and not left_open:
            side = 1
        else:
            side = -1 if owned[0][1] * 2 < w else 1
        for i in range(len(owned)):
            c = lo + i if side < 0 else hi - i
            if lo <= c <= hi:
                out[bot][c] = CAP
    return out
