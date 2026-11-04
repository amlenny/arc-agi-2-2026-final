# Rule authored from the evaluation demonstrations of 65b59efc.
#
# The grid is a lattice of NxN blocks separated by single lines, and it holds three things:
#
#   row of MOTIFS   one NxN figure per block-column, each in its own colour
#   row of MASKS    one NxN pattern per block-column, saying WHERE its motif goes
#   last row, KEY   one colour per block-column, the colour that motif is drawn in
#
# The answer is N^2 x N^2: for every mask cell that is set, its motif is stamped into the
# corresponding cell of the NxN meta-grid.
#
# A MASK IS MATCHED TO ITS MOTIF BY COLOUR, NOT BY COLUMN, and that is the whole trick. In demo 0
# the mask in column 1 is yellow and selects the YELLOW motif, which lives in column 2. The key,
# by contrast, is positional — the colour under column i recolours the motif in column i. Lining
# the masks up by column instead reproduces two of the three motifs and invents the third.
from collections import Counter


def transform(grid):
    h, w = len(grid), len(grid[0])
    cnt = Counter(v for row in grid for v in row)
    bg = cnt.most_common(1)[0][0]

    def line_colour(vals):
        s = {v for v in vals if v != bg}
        if len(s) != 1:
            return None
        c = s.pop()
        return c if sum(1 for v in vals if v == c) >= 2 else None

    votes = Counter()
    for r in range(h):
        c = line_colour(grid[r])
        if c is not None:
            votes[c] += 1
    for c0 in range(w):
        c = line_colour([grid[r][c0] for r in range(h)])
        if c is not None:
            votes[c] += 1
    if not votes:
        return [row[:] for row in grid]
    sep = votes.most_common(1)[0][0]

    srow = [r for r in range(h) if line_colour(grid[r]) == sep]
    scol = [c for c in range(w) if line_colour([grid[r][c] for r in range(h)]) == sep]

    def spans(cuts, n):
        out, prev = [], 0
        for x in sorted(cuts) + [n]:
            if x > prev:
                out.append((prev, x - 1))
            prev = x + 1
        return out

    rowb = spans(srow, h)
    colb = spans(scol, w)
    if len(rowb) < 2 or not colb:
        return [row[:] for row in grid]
    N = colb[0][1] - colb[0][0] + 1
    rowb = [rb for rb in rowb if rb[1] - rb[0] + 1 == N]
    if len(rowb) < 2:
        return [row[:] for row in grid]

    def block(rb, cb):
        cells = {(r - rb[0], c - cb[0])
                 for r in range(rb[0], rb[1] + 1) for c in range(cb[0], cb[1] + 1)
                 if grid[r][c] not in (bg, sep)}
        if not cells:
            return None, None
        col = grid[rb[0] + next(iter(cells))[0]][cb[0] + next(iter(cells))[1]]
        return col, cells

    motifs = {}
    for cb in colb:
        col, cells = block(rowb[0], cb)
        if col is not None:
            motifs[col] = cells
    masks = []
    for cb in colb:
        col, cells = block(rowb[1], cb)
        if col is not None:
            masks.append((col, cells))

    # the key is the last row carrying marks; column i's colour repaints column i's motif
    keyrow = max((r for r in range(h)
                  if any(grid[r][c] not in (bg, sep) for c in range(w))), default=None)
    recolour = {}
    for cb in colb:
        vals = [grid[keyrow][c] for c in range(cb[0], cb[1] + 1) if grid[keyrow][c] not in (bg, sep)]
        col, _ = block(rowb[0], cb)
        if vals and col is not None:
            recolour[col] = vals[0]

    out = [[bg] * (N * N) for _ in range(N * N)]
    for mcol, mcells in masks:
        shape = motifs.get(mcol)
        if shape is None:
            continue
        paint = recolour.get(mcol, mcol)
        for (mr, mc) in mcells:
            for (a, b) in shape:
                out[mr * N + a][mc * N + b] = paint
    return out
