# Rule authored from the evaluation demonstrations of 67e490f4.
#
# A solid PANEL is punched through with motif-shaped holes, and the field around it is littered
# with small coloured shapes. Each hole is the same shape as exactly one of the loose shapes, and
# the answer is the panel with every hole filled in that shape's colour.
#
# The panel colour's cell count is IDENTICAL in input and output in every pair (92, 128, 144) —
# the panel itself is untouched and only the holes are painted, which is what fixes the output
# region as the panel's bounding box.
#
# The holes are drawn in the FIELD's background colour, so they cannot be found by colour; they
# are found as the non-panel cells inside the panel's box.
from collections import Counter, deque


def _blobs(cells):
    seen, out = set(), []
    for p in sorted(cells):
        if p in seen:
            continue
        q = deque([p])
        seen.add(p)
        got = []
        while q:
            y, x = q.popleft()
            got.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    n = (y + dy, x + dx)
                    if n in cells and n not in seen:
                        seen.add(n)
                        q.append(n)
        out.append(sorted(got))
    return out


def _norm(cells):
    r0 = min(r for r, _ in cells)
    c0 = min(c for _, c in cells)
    return tuple(sorted((r - r0, c - c0) for r, c in cells))


def _canon(cells):
    """Smallest of the eight rotations/reflections. The holes appear in orientations the loose
    shapes never take — demo 1 punches the same corner four ways and only one way is lying in the
    field — so an orientation-sensitive match cannot work."""
    best = None
    cur = list(cells)
    for _ in range(4):
        for form in (cur, [(r, -c) for r, c in cur]):
            n = _norm(form)
            if best is None or n < best:
                best = n
        cur = [(c, -r) for r, c in cur]
    return best


def transform(grid):
    h, w = len(grid), len(grid[0])
    cnt = Counter(v for row in grid for v in row)
    bg = cnt.most_common(1)[0][0]
    panel = max((v for v in cnt if v != bg), key=lambda v: cnt[v])

    pc = [(r, c) for r in range(h) for c in range(w) if grid[r][c] == panel]
    r0 = min(r for r, _ in pc); r1 = max(r for r, _ in pc)
    c0 = min(c for _, c in pc); c1 = max(c for _, c in pc)

    # the loose shapes: everything outside the panel's box that is not background
    # PER COLOUR, or 8-connectivity welds shapes of different colours that merely touch on a
    # diagonal — demo 1 loses one of colour 3's corners that way, and the vote it should win
    # against colour 6 comes out a tie.
    tally = {}
    for col in cnt:
        if col in (bg, panel):
            continue
        cells = {(r, c) for r in range(h) for c in range(w)
                 if grid[r][c] == col and not (r0 <= r <= r1 and c0 <= c <= c1)}
        for blob in _blobs(cells):
            k = (_canon(blob), col)
            tally[k] = tally.get(k, 0) + 1
    loose = {}
    for (shape, col), k in sorted(tally.items(), key=lambda t: (-t[1], t[0][1])):
        # MOST COPIES WINS. Several colours carry the same shape as decoys; the real one is the
        # one lying around most often — five 2x2 squares in colour 8 against three in colour 2.
        loose.setdefault(shape, col)

    out = [[grid[r][c] for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
    holes = {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)
             if grid[r][c] != panel}
    for blob in _blobs(holes):
        col = loose.get(_canon(blob))
        if col is None:
            continue
        for (r, c) in blob:
            out[r - r0][c - c0] = col
    return out
