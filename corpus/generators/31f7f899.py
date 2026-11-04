# Rule authored from the evaluation demonstrations of 31f7f899.
#
# One full-length line crosses the grid — the axis. Perpendicular bars of other colours cross it,
# each centred on the axis and each a different length. The transformation SORTS the lengths
# ascending and reassigns them along the axis in position order, so the bars keep their colour and
# their position and trade lengths. Demo 0 goes 9,7,5,3 -> 3,5,7,9 and demo 1 goes 5,9,5,3,11 ->
# 3,5,5,9,11, which is sorting rather than reversal; the second case distinguishes them.

from collections import Counter


def transform(grid):
    h, w = len(grid), len(grid[0])
    bg = Counter(v for row in grid for v in row).most_common(1)[0][0]

    # The axis is the full row or full column with no background in it.
    axis_row = next((r for r in range(h) if all(grid[r][c] != bg for c in range(w))), None)
    axis_col = next((c for c in range(w) if all(grid[r][c] != bg for r in range(h))), None)

    out = [row[:] for row in grid]

    if axis_row is not None:
        axis_colour = Counter(grid[axis_row]).most_common(1)[0][0]
        bars = []
        for c in range(w):
            col = [grid[r][c] for r in range(h)]
            colour = col[axis_row]
            if colour in (bg, axis_colour):
                continue
            r0 = r1 = axis_row
            while r0 - 1 >= 0 and col[r0 - 1] == colour:
                r0 -= 1
            while r1 + 1 < h and col[r1 + 1] == colour:
                r1 += 1
            bars.append({"pos": c, "colour": colour, "len": r1 - r0 + 1})
        if not bars:
            return out
        for b in bars:                       # erase every bar, keep the axis cell
            for r in range(h):
                if r != axis_row and out[r][b["pos"]] == b["colour"]:
                    out[r][b["pos"]] = bg
        for b, ln in zip(bars, sorted(x["len"] for x in bars)):
            # An even length cannot sit symmetrically on the axis; the extra cell goes ABOVE.
            top = axis_row - ln // 2
            for r in range(top, top + ln):
                if 0 <= r < h:
                    out[r][b["pos"]] = b["colour"]
        return out

    if axis_col is not None:
        axis_colour = Counter(grid[r][axis_col] for r in range(h)).most_common(1)[0][0]
        bars = []
        for r in range(h):
            colour = grid[r][axis_col]
            if colour in (bg, axis_colour):
                continue
            c0 = c1 = axis_col
            while c0 - 1 >= 0 and grid[r][c0 - 1] == colour:
                c0 -= 1
            while c1 + 1 < w and grid[r][c1 + 1] == colour:
                c1 += 1
            bars.append({"pos": r, "colour": colour, "len": c1 - c0 + 1})
        if not bars:
            return out
        for b in bars:
            for c in range(w):
                if c != axis_col and out[b["pos"]][c] == b["colour"]:
                    out[b["pos"]][c] = bg
        for b, ln in zip(bars, sorted(x["len"] for x in bars)):
            left = axis_col - ln // 2
            for c in range(left, left + ln):
                if 0 <= c < w:
                    out[b["pos"]][c] = b["colour"]
        return out

    return out
