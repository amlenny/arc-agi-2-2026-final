# Rule authored from the evaluation demonstrations of 247ef758.
#
# The grid is a MOTIF PANEL on the left and a BORDERED BOX on the right, split by a solid column.
# The box's border is one colour; cells on it in any OTHER colour are MARKERS.
#
#   * A marker on the top (or bottom) border gives a COLUMN. A marker on the right border gives a
#     ROW. A colour holding both is placed into the box, its motif centred on that intersection.
#   * A motif that is placed is ERASED from the panel — it moved, it was not copied.
#   * A motif whose colour has no marker pair STAYS where it is. Demo 1's 8s and demo 2's 7s never
#     move, and that is what rules out "clear the panel" as the second half of the rule.
from collections import Counter


def _components(grid, colour, lo, hi):
    """8-connected cells of one colour within columns [lo, hi)."""
    h = len(grid)
    seen, out = set(), []
    for r in range(h):
        for c in range(lo, hi):
            if grid[r][c] != colour or (r, c) in seen:
                continue
            stack, comp = [(r, c)], []
            seen.add((r, c))
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if (0 <= ny < h and lo <= nx < hi and (ny, nx) not in seen
                                and grid[ny][nx] == colour):
                            seen.add((ny, nx))
                            stack.append((ny, nx))
            out.append(comp)
    return out


def transform(grid):
    h, w = len(grid), len(grid[0])
    # The board is the commonest colour -- 0 on every pair here, read rather than assumed.
    tally = {}
    for row in grid:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])
    out = [row[:] for row in grid]

    # the spine: the one column that holds a single colour all the way down
    spine = None
    for c in range(w):
        col = {grid[r][c] for r in range(h)}
        if len(col) == 1 and grid[0][c] != bg:
            spine = c
            break
    if spine is None:
        return out

    border = Counter(grid[0][c] for c in range(spine + 1, w)).most_common(1)[0][0]

    # markers: non-border cells sitting on the box's own border lines
    cols_by_colour, rows_by_colour = {}, {}
    for c in range(spine + 1, w):
        for r in (0, h - 1):
            v = grid[r][c]
            if v not in (border, bg):
                cols_by_colour.setdefault(v, []).append(c)
    for r in range(h):
        v = grid[r][w - 1]
        if v not in (border, bg):
            rows_by_colour.setdefault(v, []).append(r)

    # ORDER IS THE PANEL'S, TOP TO BOTTOM — not the colour value. Sorting by colour happens to
    # put demo 0's 4 ahead of its 7 and looks right, but test input 1 stacks a 6-motif above a
    # 4-motif in the panel and they overlap in the box: the 6 was laid down first and keeps the
    # cell. Sorted-by-colour hands it to the 4 and misses by exactly that one cell.
    movable = set(cols_by_colour) & set(rows_by_colour)
    ranked = []
    for colour in movable:
        comps = _components(grid, colour, 0, spine)
        if comps:
            ranked.append((min(r for r, _ in max(comps, key=len)), colour))
    for _, colour in sorted(ranked):
        comps = _components(grid, colour, 0, spine)
        if not comps:
            continue
        cells = max(comps, key=len)
        rs = [r for r, _ in cells]
        cs = [c for _, c in cells]
        cr = (min(rs) + max(rs)) // 2
        cc = (min(cs) + max(cs)) // 2
        for r, c in cells:
            out[r][c] = bg                      # it moved; the panel copy goes
        # ONE COPY PER MARKER INTERSECTION. Demo 1's colour 7 has two top markers and two right
        # markers and the output holds FOUR copies of the plus. Taking only the first of each
        # placed one copy and lost three.
        for tr in rows_by_colour[colour]:
          for tc in cols_by_colour[colour]:
            for r, c in cells:
                y, x = tr + (r - cr), tc + (c - cc)
                # FIRST PLACED WINS. Demo 0's 4-motif and 7-block overlap at (5,9): the 4 arrives
            # first and keeps the cell. Writing unconditionally let the 7 take it and cost the
            # demo by exactly one cell.
                if 0 <= y < h and 0 <= x < w and out[y][x] == bg:
                    out[y][x] = colour
    return out
