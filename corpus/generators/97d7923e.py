# Rule authored from the evaluation demonstrations of 97d7923e.
#
# Vertical BARS stand in the grid, each capped top and bottom in one colour with a different colour
# down its middle. Alongside them sit MARKERS — short runs of a single colour, no middle.
#
# A marker's LENGTH selects which bar of its own family to convert: one cell picks the longest bar
# capped in that colour, two cells the second longest. The chosen bar's middle is repainted in the
# cap colour; every other bar is left alone.
#
# Length alone does not decide it, and demo 2 is what shows this: its two families each hold a
# six-cell bar, and only one of the two is converted — the family with the single-cell marker takes
# its longest, the family with the two-cell marker takes its SECOND longest and leaves the six-cell
# one untouched.
from collections import Counter


def _runs(grid, bg):
    """Vertical runs of non-background cells, as (col, r0, r1, [colours])."""
    h, w = len(grid), len(grid[0])
    out = []
    for c in range(w):
        r = 0
        while r < h:
            if grid[r][c] == bg:
                r += 1
                continue
            r0 = r
            while r < h and grid[r][c] != bg:
                r += 1
            out.append((c, r0, r - 1, [grid[y][c] for y in range(r0, r)]))
    return out


def transform(grid):
    h, w = len(grid), len(grid[0])
    bg = Counter(v for row in grid for v in row).most_common(1)[0][0]
    runs = _runs(grid, bg)

    bars, marks = [], []
    for c, r0, r1, vals in runs:
        if len(set(vals)) == 1:
            # a MARKER is a run of one colour; its LENGTH says which bar of that family to convert
            marks.append((vals[0], len(vals)))
        elif len(vals) >= 3 and vals[0] == vals[-1] and len(set(vals[1:-1])) == 1 \
                and vals[1] != vals[0]:
            bars.append((vals[0], vals[1], c, r0, r1, len(vals)))

    out = [row[:] for row in grid]
    for ecol, k in marks:
        fam = sorted((b for b in bars if b[0] == ecol), key=lambda b: -b[5])
        if len(fam) < k:
            continue
        _, mcol, c, r0, r1, _ = fam[k - 1]
        for y in range(r0 + 1, r1):
            out[y][c] = ecol
    return out
