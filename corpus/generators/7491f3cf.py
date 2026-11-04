# Rule authored from the evaluation demonstrations of 7491f3cf.
#
# Four panels between border columns. The last is blank and is the answer; panels 1 and 2 hold a
# motif each; PANEL 0 IS A KEY, and reading it as a third motif is what makes this look like an
# interlocking-shapes puzzle. It is not. The key holds a connected LINE plus one isolated MARKER
# cell, and it says how to divide the blank panel:
#
#   * the line cuts the panel into regions
#   * the region holding the MARKER is filled from panel 1
#   * every other region is filled from panel 2
#   * a cell ON the line takes panel 1's mark if panel 1 has one there, otherwise panel 2's
#
# The line is not always straight — the test's is an L down a column then along a row, which is
# why the split is done by flood fill from the marker rather than by a slope or an axis test.
#
# This is TRAP 30 in the ledger: k=2 local consistency reads 1.000 with 175/175 test patches
# unseen, so a rule fitted to the demonstrations' neighbourhoods generalises to nothing. Nothing
# here is fitted — the division is read off the key panel and the marks are copied.
from collections import Counter, deque


def _regions(mask, n):
    """4-connected regions of the cells NOT on the line."""
    lab = [[-1] * n for _ in range(n)]
    k = 0
    for r in range(n):
        for c in range(n):
            if mask[r][c] or lab[r][c] >= 0:
                continue
            q = deque([(r, c)])
            lab[r][c] = k
            while q:
                y, x = q.popleft()
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    a, b = y + dy, x + dx
                    if 0 <= a < n and 0 <= b < n and not mask[a][b] and lab[a][b] < 0:
                        lab[a][b] = k
                        q.append((a, b))
            k += 1
    return lab


def transform(grid):
    h, w = len(grid), len(grid[0])
    out = [row[:] for row in grid]
    border = grid[0][0]

    dcols = [c for c in range(w) if all(grid[r][c] == border for r in range(h))]
    rows = [r for r in range(h) if not all(grid[r][c] == border for c in range(w))]
    spans, prev = [], 0
    for c in dcols + [w]:
        if c > prev:
            spans.append((prev, c - 1))
        prev = c + 1
    if len(spans) < 4 or not rows:
        return out

    panels = [[[grid[r][c] for c in range(a, b + 1)] for r in rows] for a, b in spans]
    n = len(rows)

    def split(p):
        cnt = Counter(v for row in p for v in row)
        bg = cnt.most_common(1)[0][0]
        marks = {(r, c) for r in range(len(p)) for c in range(len(p[0])) if p[r][c] != bg}
        fg = next((v for row in p for v in row if v != bg), bg)
        return bg, fg, marks

    key, a_pan, b_pan, tgt = panels[0], panels[1], panels[2], panels[3]
    kbg, _, kmarks = split(key)
    abg, acol, amarks = split(a_pan)
    bbg, bcol, bmarks = split(b_pan)
    tbg = Counter(v for row in tgt for v in row).most_common(1)[0][0]

    # the marker is the isolated key cell; everything else in the key is the line
    def isolated(p):
        return all(max(abs(p[0] - q[0]), abs(p[1] - q[1])) > 1 for q in kmarks if q != p)

    marker = next((p for p in sorted(kmarks) if isolated(p)), None)
    if marker is None:
        return out
    line = kmarks - {marker}

    mask = [[(r, c) in line for c in range(n)] for r in range(n)]
    lab = _regions(mask, n)
    home = lab[marker[0]][marker[1]]

    a0, b0 = spans[3]
    for r in range(n):
        for c in range(n):
            if (r, c) in line:
                v = acol if (r, c) in amarks else (bcol if (r, c) in bmarks else tbg)
            elif lab[r][c] == home:
                v = acol if (r, c) in amarks else tbg
            else:
                v = bcol if (r, c) in bmarks else tbg
            out[rows[r]][a0 + c] = v
    return out
