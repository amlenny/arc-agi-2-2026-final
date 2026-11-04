# Rule authored from the evaluation demonstrations of 16de56c4.
#
# Each populated LINE carries a seed of two or more cells of one colour whose spacing is a PERIOD.
# The periodic pattern is extended along the whole line, away from the edge the seed sits against.
#
# TWO THINGS THE DEMOS FORCE that a first reading misses:
#   * A lone cell of a DIFFERENT colour in the same line RECOLOURS the whole pattern to its own
#     colour and marks where the pattern stops. Demo 0 row 8 seeds 9,9 at period 2 and holds a lone
#     6 at column 6; the output is 6s at 0,2,4,6 — the seed's spacing, the marker's colour, ending
#     at the marker. Row 11 seeds 8,8 at period 1 with a lone 3 at column 7 and fills 0..7 with 3s,
#     leaving column 8 background.
#   * With no marker the pattern simply runs to the far edge.
#
# The AXIS is per grid, not per line: demo 0 works in rows, demos 1 and 2 in columns. The axis is
# the one whose lines hold the seeds.
from collections import Counter


def _solve_line(vals, bg):
    """One line in, one line out, or None if this line carries no seed."""
    n = len(vals)
    occ = [(i, v) for i, v in enumerate(vals) if v != bg]
    if len(occ) < 2:
        return None
    by_col = {}
    for i, v in occ:
        by_col.setdefault(v, []).append(i)
    seeds = [(v, idx) for v, idx in by_col.items() if len(idx) >= 2]
    if not seeds:
        return None
    scol, sidx = min(seeds, key=lambda s: min(s[1]))
    sidx = sorted(sidx)
    period = min(b - a for a, b in zip(sidx, sidx[1:]))
    if period <= 0:
        return None

    lattice = set()
    i = sidx[0]
    while i >= 0:
        lattice.add(i)
        i -= period
    i = sidx[0]
    while i < n:
        lattice.add(i)
        i += period

    # A LONE CELL OF ANOTHER COLOUR ONLY COUNTS IF IT SITS ON THE LATTICE. Demo 1's column 18
    # holds a 5 at row 3 beside a 9 seed of period 2 whose lattice is the even rows; the 5 is off
    # the lattice, so it is not a marker, it is not consumed, and the pattern stays 9. Treating
    # every foreign cell as a marker recoloured that column to 5 and lost four cells.
    marks = [(i, v) for i, v in occ if v != scol and i in lattice]
    colour = marks[0][1] if marks else scol

    out = [bg] * n
    for i in sorted(lattice):
        if marks:
            # the marker bounds the pattern on ITS OWN side of the seed and nowhere else
            m = marks[0][0]
            if m > sidx[0] and i > m:
                continue
            if m < sidx[0] and i < m:
                continue
        out[i] = colour
    # anything off the lattice is not part of this pattern and is left exactly as it was
    for i, v in occ:
        if i not in lattice:
            out[i] = v
    return out


def transform(grid):
    h, w = len(grid), len(grid[0])
    # The board is the commonest colour -- 0 on every pair here, but read rather than assumed.
    bg = Counter(v for row in grid for v in row).most_common(1)[0][0]
    rows = [[grid[r][c] for c in range(w)] for r in range(h)]
    cols = [[grid[r][c] for r in range(h)] for c in range(w)]

    row_hits = sum(1 for line in rows if _solve_line(line, bg) is not None)
    col_hits = sum(1 for line in cols if _solve_line(line, bg) is not None)

    out = [row[:] for row in grid]
    if row_hits >= col_hits:
        for r in range(h):
            got = _solve_line(rows[r], bg)
            if got is not None:
                for c in range(w):
                    out[r][c] = got[c]
    else:
        for c in range(w):
            got = _solve_line(cols[c], bg)
            if got is not None:
                for r in range(h):
                    out[r][c] = got[r]
    return out
