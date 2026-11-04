# Rule authored from the evaluation demonstrations of 35ab12c3.
#
# TWO STAGES.
#
# 1. CONNECT. Points of the same colour that share a row, column or diagonal are joined by a
#    straight segment — but greedily, shortest first, and each point takes at most TWO edges. The
#    degree cap is what the data demands: demo 0's colour 3 has six points forming a hexagon, and
#    the aligned pair (10,2)-(10,9) is the hexagon's long diagonal and is NOT drawn, because both
#    endpoints already hold two shorter diagonal edges. Connecting every aligned pair would draw
#    it.
#
# 2. ECHO. A colour with a SINGLE point, sitting next to a point of another colour, reproduces
#    that colour's whole completed shape offset by its own displacement — and every cell of the
#    echo that would land on an already-drawn cell is dropped. The clipping is not incidental: in
#    demo 2 a colour-4 dot echoes a three-cell line and keeps exactly one cell, because the other
#    two collide with the line it is echoing. A lone point with no such neighbour stays a point.

from collections import Counter


def _aligned(a, b):
    dr, dc = b[0] - a[0], b[1] - a[1]
    return dr == 0 or dc == 0 or abs(dr) == abs(dc)


def _segment(a, b):
    dr, dc = b[0] - a[0], b[1] - a[1]
    n = max(abs(dr), abs(dc))
    sr = (dr > 0) - (dr < 0)
    sc = (dc > 0) - (dc < 0)
    return [(a[0] + sr * i, a[1] + sc * i) for i in range(n + 1)]


def transform(grid):
    h, w = len(grid), len(grid[0])
    bg = Counter(v for row in grid for v in row).most_common(1)[0][0]

    pts = {}
    for r in range(h):
        for c in range(w):
            if grid[r][c] != bg:
                pts.setdefault(grid[r][c], []).append((r, c))

    out = [row[:] for row in grid]
    drawn = {}                              # colour -> the cells its completed shape occupies

    for col, cells in pts.items():
        if len(cells) < 2:
            continue
        edges = sorted(((max(abs(a[0] - b[0]), abs(a[1] - b[1])), a, b)
                        for i, a in enumerate(cells) for b in cells[i + 1:] if _aligned(a, b)),
                       key=lambda e: e[0])
        deg = {p: 0 for p in cells}
        shape = set(cells)
        for _, a, b in edges:
            if deg[a] >= 2 or deg[b] >= 2:
                continue
            deg[a] += 1
            deg[b] += 1
            shape.update(_segment(a, b))
        drawn[col] = shape
        for r, c in shape:
            out[r][c] = col

    taken = {p for s in drawn.values() for p in s}
    for col, cells in pts.items():
        if len(cells) != 1:
            continue
        (dr, dc), = cells
        src = next((grid[dr + i][dc + j]
                    for i in (-1, 0, 1) for j in (-1, 0, 1)
                    if (i or j) and 0 <= dr + i < h and 0 <= dc + j < w
                    and grid[dr + i][dc + j] not in (bg, col)
                    and grid[dr + i][dc + j] in drawn), None)
        if src is None:
            continue
        anchor = next(((dr + i, dc + j)
                       for i in (-1, 0, 1) for j in (-1, 0, 1)
                       if (i or j) and 0 <= dr + i < h and 0 <= dc + j < w
                       and grid[dr + i][dc + j] == src), None)
        off = (dr - anchor[0], dc - anchor[1])
        for r, c in drawn[src]:
            nr, nc = r + off[0], c + off[1]
            if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in taken:
                out[nr][nc] = col
    return out
