# 4a21e3da — markers cut the grid, and each piece of the shape retreats to its own corner.
#
# THE RULE, as demos and the held-out pair jointly force it:
#   * Each cell of colour 2 sits on an edge and defines a DIVIDER through itself — a marker on the
#     left or right edge divides by its ROW, one on the top or bottom edge divides by its COLUMN.
#   * The dividers cut the grid into quadrants (or halves, when there is only one marker).
#   * The shape is cut by the same lines. Each piece TRANSLATES to the corner of the quadrant it
#     fell in, flush against both walls of that corner, with its internal arrangement untouched.
#     Not reflected — translated. Demo 2's left piece maps cols 5-8 to cols 0-3 cell for cell.
#   * The divider row/column itself belongs to neither piece; it carries the marker's line.
#
# The corner is chosen by which side of each divider the piece lies on, so a piece above-and-left
# goes top-left, below-and-right goes bottom-right, and so on.
from collections import Counter


def transform(grid):
    g = [row[:] for row in grid]
    h, w = len(g), len(g[0])
    bg = Counter(v for row in g for v in row).most_common(1)[0][0]
    # THE MARKER NAMES ITSELF BY WHERE IT SITS. Every marker is on an edge -- that is what lets it
    # define a divider -- and it is the only colour that never appears in the interior: 2/2, 1/1,
    # 1/1, 2/2, 1/1 on the border across the five pairs, against 0 of 24-46 for the shape.
    marks = [v for v in {x for row in g for x in row} - {bg}
             if all(r in (0, h - 1) or c in (0, w - 1)
                    for r in range(h) for c in range(w) if g[r][c] == v)]
    if len(marks) != 1:
        return [row[:] for row in grid]
    MARK = marks[0]

    marks = [(r, c) for r in range(h) for c in range(w) if g[r][c] == MARK]
    div_rows, div_cols = set(), set()
    # An axis with no divider still needs an alignment, and it is NOT a default: the pieces go to
    # the edge THE MARKER SITS ON. Demo 2 has only a column divider and its marker is on the bottom
    # edge, so both pieces settle against the bottom. Defaulting to the top put every piece in the
    # wrong half and cost 24-56 cells per demonstration.
    row_edge = col_edge = None
    for r, c in marks:
        if c in (0, w - 1):
            div_rows.add(r)
            col_edge = "left" if c == 0 else "right"
        else:
            div_cols.add(c)
            row_edge = "top" if r == 0 else "bottom"

    shape = [(r, c) for r in range(h) for c in range(w)
             if g[r][c] not in (bg, MARK)]

    out = [[bg] * w for _ in range(h)]

    # Cells of the shape that lie ON a divider do not travel; they stay exactly where they are.
    stay = [(r, c) for r, c in shape if r in div_rows or c in div_cols]

    # The marker's line runs from its own edge along the divider as far as the furthest staying
    # cell, and no further — it does not span the whole grid. Where a staying cell sits, the shape
    # keeps the square. With nothing staying, the line runs the full length.
    for c in div_cols:
        block = [r for r, cc in stay if cc == c]
        if block:
            lo, hi = min(block), max(block)
            span = range(lo, h) if row_edge == "bottom" else range(0, hi + 1)
        else:
            span = range(h)
        for r in span:
            out[r][c] = MARK
    for r in div_rows:
        block = [c for rr, c in stay if rr == r]
        if block:
            lo, hi = min(block), max(block)
            span = range(lo, w) if col_edge == "right" else range(0, hi + 1)
        else:
            span = range(w)
        for c in span:
            out[r][c] = MARK
    for r, c in stay:
        out[r][c] = g[r][c]

    # cut the shape at the dividers and send each piece to its corner
    groups = {}
    for r, c in shape:
        if r in div_rows or c in div_cols:
            continue                      # a cell on a divider belongs to no piece
        above = all(r < dr for dr in div_rows) if div_rows else (row_edge != "bottom")
        left = all(c < dc for dc in div_cols) if div_cols else (col_edge != "right")
        groups.setdefault((above, left), []).append((r, c))

    # THE QUADRANT DIAGONALLY OPPOSITE THE MARKERS IS DROPPED. With two dividers the markers meet
    # at one corner — top-right in demo 0, bottom-left in the held-out pair — and the piece from the
    # far quadrant does not appear in the output at all. Every other piece travels to its own
    # corner. With a single divider there is no opposite quadrant and nothing is dropped, which is
    # why demo 2 keeps both of its halves.
    if div_rows and div_cols:
        drop = (row_edge == "bottom", col_edge == "right")
        groups.pop(drop, None)

    for (above, left), cells in groups.items():
        r0, r1 = min(r for r, _ in cells), max(r for r, _ in cells)
        c0, c1 = min(c for _, c in cells), max(c for _, c in cells)
        ph, pw = r1 - r0 + 1, c1 - c0 + 1
        # flush against the corner of the quadrant the piece came from
        tr = 0 if above else h - ph
        tc = 0 if left else w - pw
        for r, c in cells:
            y, x = tr + (r - r0), tc + (c - c0)
            if 0 <= y < h and 0 <= x < w:
                out[y][x] = g[r][c]
    return out
