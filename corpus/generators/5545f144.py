# Rule authored from the evaluation demonstrations of 5545f144.
#
# IT IS PAC-MAN. The panels are consecutive frames of one sprite eating pellets, and the answer
# is the frame after the last one, when every pellet has been eaten.
#
#   * the "noise dots" are PELLETS. Their sets are strictly nested across panels because each
#     frame eats a fixed number of them.
#   * the sprite's ORIENTATION is simply which way it is travelling — it is not a puzzle about
#     rotation, it is a sprite facing its direction of motion.
#   * the sprite always comes to rest with its NOSE on the pellet it just ate, which is why the
#     answer looks like it is anchored on a leftover dot.
#
# Movement is forced: the sprite runs in a straight line to the FARTHEST pellet in front of it,
# eating everything on the way, and when nothing is left ahead it turns to the side that still
# has one. Every turn in every pair has exactly one option.
#
# THE STARTING DIRECTION is the only thing not given by the first frame alone. Three of the four
# faces of demo 1's sprite are a single cell, so "the nose is the cell that sticks out" does not
# pick one. The other frames settle it — a candidate direction is only accepted if simulating it
# puts the sprite exactly where each later panel shows it. The test has one frame and no such
# check, and needs none: its sprite has exactly one single-cell face, pointing up.
from collections import Counter, deque

DIRS = {(-1, 0): "U", (1, 0): "D", (0, -1): "L", (0, 1): "R"}


def _groups(cells):
    seen, out = set(), []
    for p in sorted(cells):
        if p in seen:
            continue
        q = deque([p])
        seen.add(p)
        g = []
        while q:
            y, x = q.popleft()
            g.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    n = (y + dy, x + dx)
                    if n in cells and n not in seen:
                        seen.add(n)
                        q.append(n)
        out.append(sorted(g))
    return out


def _rot(cells, k):
    cur = list(cells)
    for _ in range(k % 4):
        cur = [(c, -r) for r, c in cur]
    r0 = min(r for r, _ in cur)
    c0 = min(c for _, c in cur)
    return sorted((r - r0, c - c0) for r, c in cur)


def transform(grid):
    h, w = len(grid), len(grid[0])
    cnt = Counter(v for row in grid for v in row)
    bg = cnt.most_common(1)[0][0]
    div = [c for c in range(w) if len({grid[r][c] for r in range(h)}) == 1 and grid[0][c] != bg]
    mark = next((v for v in cnt if v != bg and (not div or v != grid[0][div[0]])), None)
    if mark is None:
        return [row[:] for row in grid]

    spans, prev = [], 0
    for c in div + [w]:
        if c > prev:
            spans.append((prev, c - 1))
        prev = c + 1
    pw = spans[0][1] - spans[0][0] + 1
    panels = []
    for (a, b) in spans:
        cells = {(r, c - a) for r in range(h) for c in range(a, b + 1) if grid[r][c] == mark}
        panels.append(cells)
    cells0 = panels[0]
    sprite = set(max(_groups(cells0), key=len))
    pellets0 = cells0 - sprite

    def nose_for(d):
        key = {(-1, 0): lambda p: p[0], (1, 0): lambda p: -p[0],
               (0, -1): lambda p: p[1], (0, 1): lambda p: -p[1]}[d]
        m = min(key(p) for p in sprite)
        edge = [p for p in sprite if key(p) == m]
        return edge[0] if len(edge) == 1 else None

    def ahead_of(pos, d, left):
        return [p for p in left
                if (p[0] - pos[0]) * d[0] + (p[1] - pos[1]) * d[1] > 0
                and (p[0] == pos[0] if d[0] == 0 else p[1] == pos[1])]

    def run(d0):
        pos = nose_for(d0)
        if pos is None:
            return None
        d, left, trail = d0, set(pellets0), []
        while left:
            fwd = ahead_of(pos, d, left)
            if fwd:
                far = max(fwd, key=lambda p: abs(p[0] - pos[0]) + abs(p[1] - pos[1]))
                for p in sorted(fwd, key=lambda p: abs(p[0] - pos[0]) + abs(p[1] - pos[1])):
                    left.discard(p)
                    trail.append((p, d))
                pos = far
                continue
            turns = [t for t in DIRS
                     if t[0] * d[0] + t[1] * d[1] == 0 and ahead_of(pos, t, left)]
            if len(turns) != 1:
                return None
            d = turns[0]
        return trail

    cand = []
    for d0 in DIRS:
        trail = run(d0)
        if trail is None:
            continue
        ok = True
        for i in range(1, len(panels)):
            n = len(cells0) - len(panels[i])
            if not (1 <= n <= len(trail)) or trail[n - 1][0] not in panels[i]:
                ok = False
                break
        if ok:
            cand.append((d0, trail))
    if len(cand) != 1:
        return [row[:] for row in grid]
    d0, trail = cand[0]
    endpos, dend = trail[-1]

    order = [(-1, 0), (0, 1), (1, 0), (0, -1)]
    k = (order.index(dend) - order.index(d0)) % 4
    src = sorted(sprite)
    idx = src.index(nose_for(d0))
    rr = list(src)
    for _ in range(k):
        rr = [(c, -r) for r, c in rr]
    r0 = min(r for r, _ in rr)
    c0 = min(c for _, c in rr)
    rr = [(r - r0, c - c0) for r, c in rr]
    off = rr[idx]

    out = [[bg] * pw for _ in range(h)]
    for (r, c) in rr:
        y, x = endpos[0] + r - off[0], endpos[1] + c - off[1]
        if 0 <= y < h and 0 <= x < pw:
            out[y][x] = mark
    return out
