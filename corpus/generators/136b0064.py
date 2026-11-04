# Rule authored from the evaluation demonstrations of 136b0064.
#
# The grid is a GLYPH PANEL, a solid separator column, and an empty strip. The strip holds one
# marker cell; the answer draws a PATH from it, and the glyphs say how the path moves.
#
#   * glyphs are 3x3 blocks on a 4-cell pitch, at panel rows 0, 4, 8, ... and columns 0, 4, ...
#   * THEY ARE READ COLUMN-MAJOR — the whole left column of blocks top to bottom, then the next
#     column. Reading them in raster order reproduces demo 1 by luck (its panel is one block wide
#     per row) and gets demo 0 and demo 2 wrong from the second glyph on.
#   * each glyph is one MOVE. Every cell the move enters is painted in that glyph's own colour;
#     the cell it starts from is left as it was, so segments abut rather than overlap.
#
# THE ALPHABET IS FOUR SHAPES, and it is stated as a lookup rather than derived because that is
# what the task shows: all three demonstrations and both test inputs draw from exactly these four,
# and nothing in the data says what a fifth would mean. Guessing a general encoding here would be
# inventing a rule the task never demonstrates.
#
#     #.#  #.#  ###   down 1, left 1
#     ##.  #.#  .#.   down 1, right 2
#     #.#  .#.  .#.   down 2
#     ###  .#.  #.#   down 1, left 3
#
# The strip's marker is colour 5 in every pair, but it is found as "the only non-background cell
# right of the separator" rather than by that value, so a recoloured instance still parses.
from collections import Counter

PITCH = 4
GLYPH = 3

# frozenset of (row, col) offsets -> the move as a list of (dr, dc) steps
ALPHABET = {
    frozenset({(0, 0), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2)}):
        [(1, 0), (0, -1)],
    frozenset({(0, 0), (0, 1), (1, 0), (1, 2), (2, 1)}):
        [(1, 0), (0, 1), (0, 1)],
    frozenset({(0, 0), (0, 2), (1, 1), (2, 1)}):
        [(1, 0), (1, 0)],
    frozenset({(0, 0), (0, 1), (0, 2), (1, 1), (2, 0), (2, 2)}):
        [(1, 0), (0, -1), (0, -1), (0, -1)],
}


def transform(grid):
    h, w = len(grid), len(grid[0])
    bg = Counter(v for row in grid for v in row).most_common(1)[0][0]

    # the separator is the full column of a single non-background colour
    sep = None
    for c in range(w):
        col = {grid[r][c] for r in range(h)}
        if len(col) == 1 and col.pop() != bg:
            sep = c
            break
    if sep is None:
        return [row[:] for row in grid]

    ow = w - sep - 1
    out = [[bg] * ow for _ in range(h)]

    # the marker: the only non-background cell right of the separator
    start = None
    for r in range(h):
        for c in range(sep + 1, w):
            if grid[r][c] != bg:
                start = (r, c - sep - 1, grid[r][c])
    if start is None:
        return out
    sr, sc, smark = start
    out[sr][sc] = smark

    # glyphs, column-major
    glyphs = []
    for gc in range(0, sep, PITCH):
        for gr in range(0, h, PITCH):
            cells = {(dy, dx) for dy in range(GLYPH) for dx in range(GLYPH)
                     if gr + dy < h and gc + dx < sep and grid[gr + dy][gc + dx] != bg}
            if not cells:
                continue
            dy, dx = min(cells)
            glyphs.append((frozenset(cells), grid[gr + dy][gc + dx]))

    r, c = sr, sc
    for shape, colour in glyphs:
        move = ALPHABET.get(shape)
        if move is None:
            break
        for dr, dc in move:
            r, c = r + dr, c + dc
            if not (0 <= r < h and 0 <= c < ow):
                return out
            out[r][c] = colour
    return out
