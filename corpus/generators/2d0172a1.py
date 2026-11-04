# Rule authored from the evaluation demonstrations of 2d0172a1.
#
# The curves nest, and the answer is that nesting drawn as nested RECTANGLES: a curve enclosing
# nothing becomes a single cell, a curve with contents becomes a ring around its contents plus two
# cells of padding on every side.
#
# THE OUTSIDE IS NOT THE REGION AT (0,0). Demo 0's top-left corner sits in a three-cell pocket the
# curve happens to close off, so seeding the flood fill there builds the entire tree inside out.
# The outside is the LARGEST background region.
#
# SIBLINGS ARE NOT LAID OUT IN A LINE. Reading them as a line fits all three demonstrations, because
# no demonstration has more than two children under one curve, and two of anything is a line. Test 1
# has three: one above the middle curve and one to its left. Each sibling keeps THE SIDE IT LIES ON
# in the input — the dominant axis of the offset between its bounding-box centre and the main
# sibling's — one cell clear of the main sibling.
#
# THE MAIN SIBLING is the one that draws largest. Everything else hangs off it, aligned on its AXIS:
# the centre of the innermost thing nested inside it, carried up recursively. Aligning on the main
# sibling's own midline instead is right whenever the drawing happens to be symmetric and wrong when
# it is not — demo 0's outer curve draws 11 rows with its midline at row 5, and its satellite sits
# at row 4, on the axis.
#
# WHAT RESTS ON TWO EXAMPLES, flagged rather than hidden: the top level is a bounding box with one
# blank line past the outermost satellite. Only demo 0 (satellite to the right) and test 1
# (satellite below) exercise it, so the trailing line is confirmed on those two sides only.
from collections import Counter, deque


def _regions(grid, fg):
    h, w = len(grid), len(grid[0])
    lab = [[-1] * w for _ in range(h)]
    sizes, k = [], 0
    for r in range(h):
        for c in range(w):
            if grid[r][c] == fg or lab[r][c] >= 0:
                continue
            q = deque([(r, c)])
            lab[r][c] = k
            n = 0
            while q:
                y, x = q.popleft()
                n += 1
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    a, b = y + dy, x + dx
                    if 0 <= a < h and 0 <= b < w and grid[a][b] != fg and lab[a][b] < 0:
                        lab[a][b] = k
                        q.append((a, b))
            sizes.append(n)
            k += 1
    return lab, sizes


def _comps(grid, fg):
    h, w = len(grid), len(grid[0])
    seen, out = set(), []
    for r in range(h):
        for c in range(w):
            if grid[r][c] == fg and (r, c) not in seen:
                q = deque([(r, c)])
                seen.add((r, c))
                cs = []
                while q:
                    y, x = q.popleft()
                    cs.append((y, x))
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            n = (y + dy, x + dx)
                            if (0 <= n[0] < h and 0 <= n[1] < w and n not in seen
                                    and grid[n[0]][n[1]] == fg):
                                seen.add(n)
                                q.append(n)
                out.append(sorted(cs))
    return out


def _tree(grid, fg):
    """The nesting: which curve sits inside which."""
    h, w = len(grid), len(grid[0])
    lab, sizes = _regions(grid, fg)
    outer = sizes.index(max(sizes))
    comps = _comps(grid, fg)
    touch = []
    for cs in comps:
        s = set()
        for y, x in cs:
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = y + dy, x + dx
                if 0 <= a < h and 0 <= b < w and lab[a][b] >= 0:
                    s.add(lab[a][b])
        touch.append(s)

    depth = {outer: 0}
    frontier, placed = [outer], set()
    while frontier:
        nxt = []
        for i, s in enumerate(touch):
            if i in placed or not (s & set(frontier)):
                continue
            placed.add(i)
            d = min(depth[r] for r in s if r in depth)
            for r in s:
                if r not in depth:
                    depth[r] = d + 1
                    nxt.append(r)
        frontier = nxt

    par = {i: min((r for r in s if r in depth), key=lambda r: depth[r])
           for i, s in enumerate(touch)}
    kids = {i: [] for i in range(len(comps))}
    roots = []
    for i in range(len(comps)):
        pr = par[i]
        if pr == outer:
            roots.append(i)
            continue
        for j in range(len(comps)):
            if j != i and pr in touch[j] and depth[pr] == depth[par[j]] + 1:
                kids[j].append(i)
                break
    return comps, kids, roots


def transform(grid):
    cnt = Counter(v for row in grid for v in row)
    if len(cnt) != 2:
        return [row[:] for row in grid]
    fg = min(cnt, key=lambda v: cnt[v])
    bg = next(v for v in cnt if v != fg)
    comps, kids, roots = _tree(grid, fg)

    def box(i):
        rs = [r for r, _ in comps[i]]
        cs = [c for _, c in comps[i]]
        return min(rs), max(rs), min(cs), max(cs)

    def mid(i):
        r0, r1, c0, c1 = box(i)
        return (r0 + r1) / 2, (c0 + c1) / 2

    def arrange(ids):
        """Place siblings around the main one. Returns the drawings, their offsets, the main,
        and which sides carry a satellite."""
        parts = {i: draw(i) for i in ids}
        main = max(ids, key=lambda i: (len(parts[i][0]) * len(parts[i][0][0]),
                                       (box(i)[1] - box(i)[0] + 1) * (box(i)[3] - box(i)[2] + 1),
                                       -box(i)[0], -box(i)[2]))
        mh, mw = len(parts[main][0]), len(parts[main][0][0])
        axr, axc = parts[main][1]
        place, sides = {main: (0, 0)}, []
        for i in ids:
            if i == main:
                continue
            g, (par_, pac) = parts[i]
            ph, pw = len(g), len(g[0])
            dr = mid(i)[0] - mid(main)[0]
            dc = mid(i)[1] - mid(main)[1]
            if abs(dr) >= abs(dc):
                top, side = (-1 - ph, "up") if dr < 0 else (mh + 1, "down")
                place[i] = (top, axc - pac)
            else:
                left, side = (-1 - pw, "left") if dc < 0 else (mw + 1, "right")
                place[i] = (axr - par_, left)
            sides.append(side)
        return parts, place, main, sides

    def stamp(parts, place):
        cells = set()
        for j, (t, l) in place.items():
            g = parts[j][0]
            for a in range(len(g)):
                for b in range(len(g[0])):
                    if g[a][b] == fg:
                        cells.add((t + a, l + b))
        return cells

    def draw(i):
        """(drawing, axis) — the axis is the centre of the innermost thing nested inside."""
        if not kids[i]:
            return [[fg]], (0, 0)
        parts, place, main, _ = arrange(kids[i])
        cells = stamp(parts, place)
        r0 = min(r for r, _ in cells); r1 = max(r for r, _ in cells)
        c0 = min(c for _, c in cells); c1 = max(c for _, c in cells)
        H, W = (r1 - r0 + 1) + 4, (c1 - c0 + 1) + 4
        out = [[bg] * W for _ in range(H)]
        for c in range(W):
            out[0][c] = out[H - 1][c] = fg
        for r in range(H):
            out[r][0] = out[r][W - 1] = fg
        for (r, c) in cells:
            out[r - r0 + 2][c - c0 + 2] = fg
        mt, ml = place[main]
        mar, mac = parts[main][1]
        return out, (mt - r0 + 2 + mar, ml - c0 + 2 + mac)

    if len(roots) == 1:
        return draw(roots[0])[0]

    parts, place, main, sides = arrange(roots)
    cells = stamp(parts, place)
    r0 = min(r for r, _ in cells); r1 = max(r for r, _ in cells)
    c0 = min(c for _, c in cells); c1 = max(c for _, c in cells)
    r0 -= "up" in sides
    r1 += "down" in sides
    c0 -= "left" in sides
    c1 += "right" in sides
    out = [[bg] * (c1 - c0 + 1) for _ in range(r1 - r0 + 1)]
    for (r, c) in cells:
        out[r - r0][c - c0] = fg
    return out
