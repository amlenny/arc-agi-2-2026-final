# Rule authored from the evaluation demonstrations of 1ae2feb7.
#
# A vertical divider splits the grid. Each row's left segment carries a run of colour; that run's
# LENGTH becomes a PERIOD and its colour is stamped across the right side, starting one cell after
# the divider. Demo 0 row 7 runs five 3s and stamps 3 every fifth cell; row 5's run touching the
# divider is a single 8 and stamps every cell.
from collections import Counter


def transform(grid):
    h, w = len(grid), len(grid[0])
    # The board is the commonest colour -- 0 on every pair here, read rather than assumed.
    tally = {}
    for row in grid:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])
    out = [row[:] for row in grid]

    # THE DIVIDER NEED NOT BE A FULL COLUMN. Requiring every cell to match found demo 0's
    # divider and missed test 0's, whose last row is blank so the column has a hole in it. What
    # identifies a divider is that its non-background cells are all ONE colour and there are
    # nearly h of them — a hole does not stop it being the divider.
    div = None
    best = 0
    for c in range(w):
        vals = [grid[r][c] for r in range(h) if grid[r][c] != bg]
        if len(vals) >= h - 2 and len(set(vals)) == 1 and len(vals) > best:
            best = len(vals)
            div = c
    if div is None:
        return out

    # THE PATTERN SIDE IS NOT ALWAYS THE LEFT. Test 2 puts the runs to the RIGHT of the divider
    # and stamps leftward. Rather than write the mirror image of the loop, the grid is flipped so
    # the populated side is always on the left, and flipped back at the end.
    lhs = sum(1 for r in range(h) for c in range(div) if grid[r][c] != bg)
    rhs = sum(1 for r in range(h) for c in range(div + 1, w) if grid[r][c] != bg)
    flip = rhs > lhs
    if flip:
        grid = [row[::-1] for row in grid]
        out = [row[::-1] for row in out]
        div = w - 1 - div

    for r in range(h):
        left = grid[r][:div]
        runs = []
        c = 0
        while c < div:
            if left[c] != bg:
                s = c
                while c < div and left[c] == left[s]:
                    c += 1
                runs.append((left[s], c - s, s))
            else:
                c += 1
        if not runs:
            continue
        # EVERY run stamps, each at its own period, all starting one cell past the divider.
        # Runs nearer the divider take precedence where two land on the same cell. Demo 1 row 7
        # runs 3s (period 3) and 4s (period 2): the 4s hold 6,8,10,12,14 and the 3s show only at
        # 9 and 15, because 12 is already a 4. Stamping just the nearest run left those 3s out.
        done = set()
        for colour, period, _ in reversed(runs):
            x = div + 1
            while x < w:
                if x not in done:
                    out[r][x] = colour
                    done.add(x)
                x += period
    if flip:
        out = [row[::-1] for row in out]
    return out
