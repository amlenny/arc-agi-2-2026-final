# Rule authored from the evaluation demonstrations of dbff022c.
#
# A KEY lists colour pairs; every closed shape whose colour appears on the key's first line has its
# enclosed hollows filled with the partner colour. A shape whose colour appears only as a TARGET is
# left hollow — demo 0's seven-shape has a four-cell pocket and keeps it, which is what shows the
# mapping runs one way rather than pairing the two colours.
#
# THE KEY is the one blob that is a solid rectangle two cells thick carrying more than one colour;
# every other blob is a single-colour outline.
#
# WHICH LINE OF THE KEY COMES FIRST is the one nearer its own edge of the grid. All three
# demonstrations put the key at the top or the left, so simply taking the first line fits every one
# of them — and the test puts it along the BOTTOM, where that reading inverts every pair and fills
# the wrong shapes with the wrong colours.
#
# A hollow is background unreachable from the grid border, and it is filled only when a SINGLE
# shape colour surrounds it, so a pocket pinched between two different shapes is left alone.
from collections import Counter, deque


def _blobs(grid, bg, same_colour):
    h, w = len(grid), len(grid[0])
    seen, out = set(), []
    for r in range(h):
        for c in range(w):
            if grid[r][c] == bg or (r, c) in seen:
                continue
            col = grid[r][c]
            q, cs = deque([(r, c)]), []
            seen.add((r, c))
            while q:
                y, x = q.popleft()
                cs.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        a, b = y + dy, x + dx
                        if (0 <= a < h and 0 <= b < w and (a, b) not in seen
                                and grid[a][b] != bg
                                and (not same_colour or grid[a][b] == col)):
                            seen.add((a, b))
                            q.append((a, b))
            out.append(cs)
    return out


def transform(grid):
    h, w = len(grid), len(grid[0])
    bg = Counter(v for row in grid for v in row).most_common(1)[0][0]

    # THE KEY is the one blob that is a SOLID rectangle two cells thick and carries more than one
    # colour. Every other blob is a single-colour outline. Its pairs are read across the thin
    # dimension: two rows deep means top-to-bottom, two columns means left-to-right.
    key = None
    for cs in _blobs(grid, bg, same_colour=False):
        r0 = min(y for y, _ in cs); r1 = max(y for y, _ in cs)
        c0 = min(x for _, x in cs); c1 = max(x for _, x in cs)
        hh, ww = r1 - r0 + 1, c1 - c0 + 1
        if len(cs) != hh * ww or 2 not in (hh, ww):
            continue
        if len({grid[y][x] for y, x in cs}) < 2:
            continue
        # WHICH LINE OF THE KEY COMES FIRST is the one nearer its own edge of the grid. Every
        # demonstration puts the key at the top or the left and reads inwards, so "first line
        # wins" fits all three — and the test puts it at the BOTTOM, where that reading inverts
        # every pair and fills the wrong shapes with the wrong colours.
        pairs = {}
        if hh == 2:
            a, b = (r0, r1) if r0 <= (h - 1 - r1) else (r1, r0)
            for x in range(c0, c1 + 1):
                pairs[grid[a][x]] = grid[b][x]
        else:
            a, b = (c0, c1) if c0 <= (w - 1 - c1) else (c1, c0)
            for y in range(r0, r1 + 1):
                pairs[grid[y][a]] = grid[y][b]
        key = (set(cs), pairs)
        break
    if key is None:
        return [row[:] for row in grid]
    kcells, pairs = key

    # background reachable from the border is outside; anything else is enclosed
    outside = set()
    q = deque()
    for r in range(h):
        for c in (0, w - 1):
            if grid[r][c] == bg and (r, c) not in outside:
                outside.add((r, c)); q.append((r, c))
    for c in range(w):
        for r in (0, h - 1):
            if grid[r][c] == bg and (r, c) not in outside:
                outside.add((r, c)); q.append((r, c))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = y + dy, x + dx
            if 0 <= a < h and 0 <= b < w and grid[a][b] == bg and (a, b) not in outside:
                outside.add((a, b))
                q.append((a, b))

    out = [row[:] for row in grid]
    seen = set()
    for r in range(h):
        for c in range(w):
            if grid[r][c] != bg or (r, c) in outside or (r, c) in seen:
                continue
            q, pocket, walls = deque([(r, c)]), [], set()
            seen.add((r, c))
            while q:
                y, x = q.popleft()
                pocket.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    a, b = y + dy, x + dx
                    if not (0 <= a < h and 0 <= b < w):
                        continue
                    if grid[a][b] == bg:
                        if (a, b) not in seen:
                            seen.add((a, b))
                            q.append((a, b))
                    elif (a, b) not in kcells:
                        walls.add(grid[a][b])
            # a pocket belongs to one shape, and that shape is filled only if the key names it
            if len(walls) == 1:
                col = walls.pop()
                if col in pairs:
                    for y, x in pocket:
                        out[y][x] = pairs[col]
    return out
