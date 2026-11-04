"""d35bdbdc -- rings on a wiggly 5-path.

The grid carries 3x3 shapes (solid rings or plus/diamonds, possibly clipped by a
grid edge), each with a centre cell whose colour names another shape by ITS body
colour.  A single wiggly line of colour 5 threads across the background.

The two shapes sitting at the ENDS of that line survive; every other shape is
erased outright.  A survivor keeps its body and takes the centre colour of the
shape its own centre named.  The line itself is untouched.
"""

# THE BOARD AND THE LINE NAME THEMSELVES BY WEIGHT. The board is the commonest colour and the line
# the second commonest, on all six pairs (49/15, 42/13, 45/10, 65/10, 32/23, 34/24). Both are set
# from the grid at the top of transform; the helpers read them from here.
BG   = 0
LINE = 5
N8   = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
N4   = [(-1,0),(1,0),(0,-1),(0,1)]


def _shapes(g):
    """Every ring/plus body: a same-coloured component whose bbox is 3x3
    (or 3x2 / 2x3 when the grid edge cuts it off).  Returns body colour,
    cells, centre position and centre colour."""
    H, W = len(g), len(g[0])
    seen = set()
    out  = []
    for r in range(H):
        for c in range(W):
            col = g[r][c]
            if col in (BG, LINE) or (r, c) in seen:
                continue
            stack, comp = [(r, c)], []
            seen.add((r, c))
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for dy, dx in N8:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and g[ny][nx] == col and (ny, nx) not in seen:
                        seen.add((ny, nx))
                        stack.append((ny, nx))
            r0 = min(p[0] for p in comp); r1 = max(p[0] for p in comp)
            c0 = min(p[1] for p in comp); c1 = max(p[1] for p in comp)
            cy = _mid(r0, r1, H)
            cx = _mid(c0, c1, W)
            if cy is None or cx is None:
                continue
            out.append({"body": col, "cells": comp, "ctr": (cy, cx), "cc": g[cy][cx]})
    return out


def _mid(a, b, n):
    """Centre index of a span that is 3 long, allowing one row/col to be cut
    off by the grid edge."""
    if b - a == 2:
        return a + 1
    if b - a == 1:
        if b == n - 1:
            return a + 1
        if a == 0:
            return b - 1
    return None


def _line_ends(g):
    """The two ends of the wiggly line: the pair of line cells furthest apart
    along the line."""
    H, W = len(g), len(g[0])
    cells = [(r, c) for r in range(H) for c in range(W) if g[r][c] == LINE]
    if len(cells) < 2:
        return []
    idx  = {p: i for i, p in enumerate(cells)}
    adj  = [[] for _ in cells]
    for p, i in idx.items():
        for dy, dx in N8:
            q = (p[0] + dy, p[1] + dx)
            if q in idx:
                adj[i].append(idx[q])
    best, ends = -1, []
    for s in range(len(cells)):
        dist = [-1] * len(cells)
        dist[s] = 0
        queue = [s]
        while queue:
            nxt = []
            for u in queue:
                for v in adj[u]:
                    if dist[v] < 0:
                        dist[v] = dist[u] + 1
                        nxt.append(v)
            queue = nxt
        far = max(dist)
        if far > best:
            best, ends = far, []
        if far == best:
            ends.append(cells[s])
    return ends


def transform(gi):
    global BG, LINE
    H, W  = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    order = sorted(tally, key=lambda k: -tally[k])
    if len(order) < 2:
        return [row[:] for row in gi]
    BG, LINE = order[0], order[1]
    shapes = _shapes(gi)
    bodies = {}
    for s in shapes:
        bodies.setdefault(s["body"], []).append(s)

    keep = []
    for end in _line_ends(gi):
        for s in shapes:
            if s["cc"] not in bodies:                 # nothing to inherit
                continue
            cy, cx = s["ctr"]
            if end[0] != cy and end[1] != cx:         # line meets the shape square on
                continue
            if not any((end[0] + dy, end[1] + dx) in set(s["cells"]) for dy, dx in N4):
                continue
            if s not in keep:
                keep.append(s)

    go = [row[:] for row in gi]
    for s in shapes:
        for y, x in s["cells"]:
            go[y][x] = BG
        cy, cx = s["ctr"]
        go[cy][cx] = BG
    for s in keep:
        for y, x in s["cells"]:
            go[y][x] = s["body"]
        cy, cx = s["ctr"]
        go[cy][cx] = bodies[s["cc"]][0]["cc"]
    return go
