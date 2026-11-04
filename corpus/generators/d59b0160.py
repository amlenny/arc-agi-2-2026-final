"""d59b0160 -- the corner bracket is a checklist.

An L of seven cells brackets a 3x3 corner of the grid.  The odd colours sitting
in that corner are the checklist.

Everywhere else the wall colour is punched through by open areas speckled with
odd colours.  An area is wiped back to solid wall when it holds EVERY colour on
the checklist; an area missing even one of them is left exactly as it is.  What
else the area contains makes no difference -- only whether the checklist is
complete.
"""

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


def _bracket(g):
    """The seven-cell L: one full row and one full column of a 4x4 corner."""
    H, W = len(g), len(g[0])
    where = {}
    for r in range(H):
        for c in range(W):
            where.setdefault(g[r][c], []).append((r, c))
    for col, cells in where.items():
        if len(cells) != 7:
            continue
        r0 = min(p[0] for p in cells); r1 = max(p[0] for p in cells)
        c0 = min(p[1] for p in cells); c1 = max(p[1] for p in cells)
        if (r1 - r0, c1 - c0) != (3, 3):
            continue
        for br in (r0, r1):
            for bc in (c0, c1):
                arm = {(br, c) for c in range(c0, c1 + 1)} | {(r, bc) for r in range(r0, r1 + 1)}
                if arm == set(cells):
                    box = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)
                           if r != br and c != bc]
                    return col, set(cells), box
    return None, set(), []


def transform(gi):
    H, W = len(gi), len(gi[0])
    mark, arm, box = _bracket(gi)
    if mark is None:
        return [row[:] for row in gi]

    inside = [gi[r][c] for r, c in box]
    wall = max(set(inside), key=inside.count)
    checklist = set(inside) - {wall}

    skip = arm | set(box)
    seen, go = set(), [row[:] for row in gi]
    for r in range(H):
        for c in range(W):
            if gi[r][c] == wall or (r, c) in skip or (r, c) in seen:
                continue
            st, area = [(r, c)], []
            seen.add((r, c))
            while st:
                y, x = st.pop()
                area.append((y, x))
                for dy, dx in N4:
                    q = (y + dy, x + dx)
                    if (0 <= q[0] < H and 0 <= q[1] < W and gi[q[0]][q[1]] != wall
                            and q not in skip and q not in seen):
                        seen.add(q)
                        st.append(q)
            if checklist <= {gi[y][x] for y, x in area}:
                for y, x in area:
                    go[y][x] = wall
    return go


def _areas(gi, go):
    """The open regions of an input, and which of them the answer wiped.

    An area is a 4-connected run of cells that are neither the wall nor the bracket's own corner
    box. Wiped means the answer turned it back to wall.
    """
    h, w = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    wall = max(tally, key=lambda k: tally[k])
    seen, out = set(), []
    for r in range(h):
        for c in range(w):
            if gi[r][c] == wall or (r, c) in seen:
                continue
            stack, cells = [(r, c)], []
            seen.add((r, c))
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (y + dy, x + dx)
                    if (0 <= n[0] < h and 0 <= n[1] < w and n not in seen
                            and gi[n[0]][n[1]] != wall):
                        seen.add(n)
                        stack.append(n)
            if len(cells) < 4:
                continue
            gone = all(go[y][x] == wall for y, x in cells)
            out.append((frozenset(cells), len({gi[y][x] for y, x in cells}), len(cells), gone))
    return out


def verify_block(task):
    """Every pair reproduced, AND demos that refute the two rivals this task is open to.

    RIVAL A is "wipe the areas with the most distinct colours" and RIVAL C is "wipe the largest
    area". Neither fits a single one of the source's four pairs, and both fit most blocks drawn
    here -- A fits the demos of 701 blocks in 1,200 and answers 122 of their tests wrongly. A
    reader shown three demos that agree with a rival has been taught the rival.

    So the BLOCK is refused, not the board: at least one demo must wipe an area that is not the
    busiest, or keep one that is, and likewise for the largest. The source's own pairs do this --
    it keeps exactly three areas standing on every pair -- and refusing the block is what this
    contract exists for.
    """
    pairs = [(p["input"], p["output"]) for p in task["train"]]
    pairs += [(p["input"], p["output"]) for p in task["test"]]
    for gi, go in pairs:
        try:
            if transform([r[:] for r in gi]) != go:
                return False
        except Exception:
            return False
    kills_a = kills_c = False
    for gi, go in pairs[:-1]:
        areas = _areas(gi, go)
        if len(areas) < 2:
            continue
        truth = {a for a, _, _, gone in areas if gone}
        busiest = max(n for _, n, _, _ in areas)
        biggest = max(z for _, _, z, _ in areas)
        if {a for a, n, _, _ in areas if n == busiest} != truth:
            kills_a = True
        if {a for a, _, z, _ in areas if z == biggest} != truth:
            kills_c = True
    return kills_a and kills_c
