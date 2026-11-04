# Rule authored from the evaluation demonstrations of 3e6067c3.
#
# Framed boxes each hold one colour. A KEY LINE near an edge lists colours in order. The rule walks
# the key and, for each consecutive pair, fills the background gap between those two boxes — so the
# output traces a path through the grid visiting the boxes in the key's order.
from collections import Counter


def _key_line(grid, bg, frame):
    """The row or column listing colours as isolated singletons."""
    h, w = len(grid), len(grid[0])
    best = None
    for r in range(h):
        vals = [grid[r][c] for c in range(w)]
        nz = [c for c in range(w) if vals[c] not in (bg,)]
        if len(nz) < 3 or any(vals[c] == frame for c in nz):
            continue
        if all(c + 1 not in nz for c in nz):          # every mark isolated
            seq = [vals[c] for c in nz]
            if best is None or len(seq) > len(best[1]):
                best = (("row", r), seq)
    for c in range(w):
        vals = [grid[r][c] for r in range(h)]
        nz = [r for r in range(h) if vals[r] not in (bg,)]
        if len(nz) < 3 or any(vals[r] == frame for r in nz):
            continue
        if all(r + 1 not in nz for r in nz):
            seq = [vals[r] for r in nz]
            if best is None or len(seq) > len(best[1]):
                best = (("col", c), seq)
    return best


def transform(grid):
    h, w = len(grid), len(grid[0])
    flat = [v for row in grid for v in row]
    bg = Counter(flat).most_common(1)[0][0]
    frame = Counter(v for v in flat if v != bg).most_common(1)[0][0]

    key = _key_line(grid, bg, frame)
    if key is None:
        return [row[:] for row in grid]
    (kind, kidx), order = key

    # box interiors: components of any colour that is neither background nor frame, ignoring the
    # key line itself
    seen, boxes = set(), {}
    for r in range(h):
        for c in range(w):
            v = grid[r][c]
            if v in (bg, frame) or (r, c) in seen:
                continue
            if (kind == "row" and r == kidx) or (kind == "col" and c == kidx):
                continue
            stack, comp = [(r, c)], []
            seen.add((r, c))
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if (0 <= ny < h and 0 <= nx < w and (ny, nx) not in seen
                            and grid[ny][nx] == v):
                        seen.add((ny, nx))
                        stack.append((ny, nx))
            boxes.setdefault(v, []).append(comp)

    def band(comp):
        return ((min(r for r, _ in comp), max(r for r, _ in comp)),
                (min(c for _, c in comp), max(c for _, c in comp)))

    out = [row[:] for row in grid]

    # A COLOUR CAN OWN MORE THAN ONE BOX AND THE KEY CAN VISIT IT TWICE. Demo 0's key is
    # 2,3,9,4,2,6,7,5 and there are two 2-boxes; always taking the first one dropped two
    # connectors. The next box is chosen as the one ALIGNED with the current box — sharing its row
    # band or its column band — preferring one not visited yet.
    visited = set()
    cur = None
    for a, b in zip(order, order[1:]):
        if a not in boxes or b not in boxes:
            continue
        if cur is None:
            cur = boxes[a][0]
            visited.add(id(cur))
        ra, cca = band(cur)
        cands = [x for x in boxes[b] if band(x)[0] == ra or band(x)[1] == cca]
        if not cands:
            cands = boxes[b]
        fresh = [x for x in cands if id(x) not in visited]
        nxt = (fresh or cands)[0]
        rb, ccb = band(nxt)

        if ra == rb:
            lo, hi = (cca[1], ccb[0]) if cca[1] < ccb[0] else (ccb[1], cca[0])
            for r in range(ra[0], ra[1] + 1):
                for c in range(lo + 1, hi):
                    if out[r][c] == bg:
                        out[r][c] = a
        elif cca == ccb:
            lo, hi = (ra[1], rb[0]) if ra[1] < rb[0] else (rb[1], ra[0])
            for c in range(cca[0], cca[1] + 1):
                for r in range(lo + 1, hi):
                    if out[r][c] == bg:
                        out[r][c] = a
        visited.add(id(nxt))
        cur = nxt
    return out
