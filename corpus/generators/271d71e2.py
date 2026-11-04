# Rule authored from the evaluation demonstrations of 271d71e2.
#
# Each assembly is a BOX — a rectangular ring — whose interior is partly filled, sitting beside a
# bar of MARKER cells with a second marker bar further along the same line. The box travels toward
# the markers, and its interior fills as it goes: one cell per step. It is a counter.
#
#   steps = min( unfilled interior cells , distance to the FAR marker - 1 )
#
# Both limits bind somewhere in the data — demo 0's left box is stopped by the marker after one
# step of a possible six, demo 1's first box by its own interior after three of a possible five.
# The near bar rides along one cell ahead of the box; everything it vacates becomes background.
#
# THE BACKGROUND IS THE BIGGEST CONNECTED REGION, not the commonest colour. On demo 0's 8x8 the box
# borders outnumber the empty cells, so a frequency count names the border colour as background and
# nothing parses at all.
#
# THE TRAVEL SIDE IS THE ONE WITH A MARKER TOUCHING THE BOX. Looking for a marker anywhere along a
# direction finds bars belonging to OTHER assemblies further down the grid, and demo 1's third box
# sets off the wrong way.
#
# THE FILL GROWS OUTWARD FROM WHAT IS ALREADY FILLED, layer by layer, ties broken by nearness to
# the leading edge — not simply nearest-edge-first. In demo 2 a cell two layers out but hard
# against the leading edge is filled BEFORE a nearer-looking one the growth has not reached.
#
# WHICH COLOUR MEANS FILLED is decided by mean distance from the leading edge, voted across every
# box holding both. The single nearest cell is not enough: a leading row reading 5,5,7 hands back
# the wrong colour on the tie-break, and inverting it makes every box creep one cell instead of
# travelling — which is how the test failed while all three demonstrations passed.
from collections import Counter, deque


def _comps(grid, colour):
    h, w = len(grid), len(grid[0])
    seen, out = set(), []
    for r in range(h):
        for c in range(w):
            if grid[r][c] != colour or (r, c) in seen:
                continue
            q, cs = deque([(r, c)]), []
            seen.add((r, c))
            while q:
                y, x = q.popleft()
                cs.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    a, b = y + dy, x + dx
                    if 0 <= a < h and 0 <= b < w and (a, b) not in seen and grid[a][b] == colour:
                        seen.add((a, b))
                        q.append((a, b))
            out.append(cs)
    return out


def transform(grid):
    h, w = len(grid), len(grid[0])
    # THE BACKGROUND IS THE BIGGEST CONNECTED REGION, not the commonest colour. On demo 0's 8x8
    # the box borders outnumber the empty cells, so a frequency count names the border colour as
    # background and nothing parses at all.
    bg = max({v for row in grid for v in row},
             key=lambda v: max((len(cs) for cs in _comps(grid, v)), default=0))
    palette = {v for row in grid for v in row} - {bg}

    # a BOX is a component that is exactly the border ring of its own bounding box
    boxes = []
    for col in sorted(palette):
        for cs in _comps(grid, col):
            r0 = min(y for y, _ in cs); r1 = max(y for y, _ in cs)
            c0 = min(x for _, x in cs); c1 = max(x for _, x in cs)
            if r1 - r0 < 2 or c1 - c0 < 2:
                continue
            ring = {(y, x) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1)
                    if y in (r0, r1) or x in (c0, c1)}
            if set(cs) == ring:
                boxes.append((col, r0, c0, r1, c1))
    if not boxes:
        return [row[:] for row in grid]

    border_cols = {b[0] for b in boxes}
    inner = set()
    for _, r0, c0, r1, c1 in boxes:
        for y in range(r0 + 1, r1):
            for x in range(c0 + 1, c1):
                if grid[y][x] != bg:
                    inner.add(grid[y][x])
    marker = list(palette - border_cols - inner)
    if len(marker) != 1 or len(inner) != 2:
        return [row[:] for row in grid]
    M = marker[0]

    DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))
    out = [row[:] for row in grid]

    # FILLED vs UNFILLED: in a box holding both, the filled colour is the one lying nearer the
    # side the box travels toward. The counter fills from the leading edge backwards.
    def markers_along(r0, c0, r1, c1, d):
        dy, dx = d
        cells = []
        if dy:
            rng = range(r1 + 1, h) if dy > 0 else range(r0 - 1, -1, -1)
            for y in rng:
                if any(grid[y][x] == M for x in range(c0, c1 + 1)):
                    cells.append(y)
        else:
            rng = range(c1 + 1, w) if dx > 0 else range(c0 - 1, -1, -1)
            for x in rng:
                if any(grid[y][x] == M for y in range(r0, r1 + 1)):
                    cells.append(x)
        return cells

    plan = []
    for col, r0, c0, r1, c1 in boxes:
        # THE TRAVEL SIDE IS THE ONE WITH A MARKER TOUCHING THE BOX. Merely finding a marker
        # somewhere along a direction picks up bars belonging to OTHER assemblies further down the
        # grid — demo 1's third box sees a stray marker above it and sets off the wrong way.
        d = None
        for dy, dx in DIRS:
            if dy:
                y = r1 + 1 if dy > 0 else r0 - 1
                touching = 0 <= y < h and any(grid[y][x] == M for x in range(c0, c1 + 1))
            else:
                x = c1 + 1 if dx > 0 else c0 - 1
                touching = 0 <= x < w and any(grid[y][x] == M for y in range(r0, r1 + 1))
            if touching:
                d = (dy, dx)
                break
        if d is None:
            continue
        plan.append((col, r0, c0, r1, c1, d, markers_along(r0, c0, r1, c1, d)))

    # FILLED vs UNFILLED, decided by MEAN distance from the leading edge and voted across every
    # box that holds both. Taking the single nearest cell is not enough: a box whose leading row
    # reads 5,5,7 hands back the wrong colour on the tie-break, and getting this backwards inverts
    # every count in the grid — the boxes then creep one cell instead of travelling.
    votes = {c: 0 for c in inner}
    for col, r0, c0, r1, c1, d, mk in plan:
        dy, dx = d
        cells = [(y, x) for y in range(r0 + 1, r1) for x in range(c0 + 1, c1)]

        def lead(p):
            y, x = p
            return (r1 - y) if dy > 0 else (y - r0) if dy < 0 else (c1 - x) if dx > 0 else (x - c0)

        groups = {}
        for pnt in cells:
            groups.setdefault(grid[pnt[0]][pnt[1]], []).append(lead(pnt))
        if len(set(groups) & inner) == 2:
            a, b = sorted(inner)
            ma = sum(groups[a]) / len(groups[a])
            mb = sum(groups[b]) / len(groups[b])
            votes[a if ma < mb else b] += 1
    if not any(votes.values()):
        return [row[:] for row in grid]
    F = max(votes, key=lambda c: votes[c])
    U = (inner - {F}).pop()

    for col, r0, c0, r1, c1, d, mk in plan:
        dy, dx = d
        cells = [(y, x) for y in range(r0 + 1, r1) for x in range(c0 + 1, c1)]

        def lead(p):
            y, x = p
            return (r1 - y) if dy > 0 else (y - r0) if dy < 0 else (c1 - x) if dx > 0 else (x - c0)

        # THE FILL GROWS OUTWARD FROM WHAT IS ALREADY FILLED, layer by layer, ties broken by
        # nearness to the leading edge. Ordering purely by distance from that edge reproduces the
        # simple boxes and gets demo 1's third one wrong by two cells, and demo 2's by one: there,
        # a cell two layers out but hard against the leading edge is filled BEFORE a nearer-looking
        # one that the growth has not reached yet.
        inside = set(cells)
        seeds = {p for p in cells if grid[p[0]][p[1]] == F}
        if not seeds:
            edge0 = min(lead(p) for p in cells)
            seeds = {p for p in cells if lead(p) == edge0}
            order, front = [], sorted(seeds, key=lambda p: (lead(p), p))
            done = set(seeds)
        else:
            order, done = [], set(seeds)
            front = sorted({(y + dy2, x + dx2) for y, x in seeds
                            for dy2, dx2 in ((1, 0), (-1, 0), (0, 1), (0, -1))}
                           & inside - done, key=lambda p: (lead(p), p))
            done |= set(front)
        while front:
            order.extend(p for p in front if grid[p[0]][p[1]] == U)
            nxt = sorted({(y + dy2, x + dx2) for y, x in front
                          for dy2, dx2 in ((1, 0), (-1, 0), (0, 1), (0, -1))}
                         & inside - done, key=lambda p: (lead(p), p))
            done |= set(nxt)
            front = nxt
        unfilled = order
        far = mk[-1]
        edge = (r1 if dy > 0 else r0) if dy else (c1 if dx > 0 else c0)
        room = abs(far - edge) - 1
        steps = min(len(unfilled), room)

        # clear the box, its interior, and every marker between it and the far bar
        for y in range(r0, r1 + 1):
            for x in range(c0, c1 + 1):
                out[y][x] = bg
        for m in mk[:-1]:
            if dy:
                for x in range(c0, c1 + 1):
                    out[m][x] = bg
            else:
                for y in range(r0, r1 + 1):
                    out[y][m] = bg

        turned = set(unfilled[:steps])
        for y in range(r0, r1 + 1):
            for x in range(c0, c1 + 1):
                v = grid[y][x]
                if (y, x) in turned:
                    v = F
                out[y + dy * steps][x + dx * steps] = v
        # the near bar rides along, one cell ahead of the box's leading edge
        ne = edge + dy * steps + dy if dy else edge + dx * steps + dx
        if dy:
            if 0 <= ne < h:
                for x in range(c0, c1 + 1):
                    out[ne][x] = M
        else:
            if 0 <= ne < w:
                for y in range(r0, r1 + 1):
                    out[y][ne] = M
    return out
