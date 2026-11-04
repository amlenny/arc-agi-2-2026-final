# 5961cc34 — a stream leaves a nozzle, lights the shapes it reaches, and erases the ones it misses.
#
# THE RULE, as the demonstrations force it:
#   * A single cell of colour 4 is the NOZZLE, with a short tail of 2s behind it. The stream leaves
#     the nozzle in the direction AWAY from that tail.
#   * Everything the stream passes through becomes 2.
#   * Reaching a shape lights the WHOLE shape, and the stream leaves again through that shape's
#     DOOR — its cells of colour 3.
#   * THE STREAM IS AS WIDE AS THE DOOR IT LEFT THROUGH. This is the part a one-cell ray gets
#     wrong: doors come as pairs of 3s, so a stream leaving a shape is two cells wide and stays
#     two cells wide until the next shape. A single-cell ray misses 12-14 cells per
#     demonstration, all of them the second rail of a two-wide run.
#   * Any shape the stream never reaches is ERASED. In demo 0 the stream reaches nothing and the
#     output is a bare line with the untouched shape gone — which is what excludes the simpler
#     reading that shapes are merely recoloured.
from collections import Counter, deque


def transform(grid):
    g = [row[:] for row in grid]
    h, w = len(g), len(g[0])
    bg = Counter(v for row in g for v in row).most_common(1)[0][0]

    # ALL THREE ROLES ARE READ OFF THE BOARD. The nozzle is the only colour with exactly one cell
    # on it, in all five pairs. The stream is the tail behind that cell -- its one non-background
    # neighbour. Of the two colours left, the shapes are the common one and the doors the rare one
    # (14 v 2, 46 v 8, 66 v 6, 29 v 3, 94 v 6).
    tally = Counter(v for row in g for v in row)
    singles = [v for v in tally if tally[v] == 1]
    if len(singles) != 1:
        return [row[:] for row in grid]
    NOZZLE = singles[0]
    nr, nc = next((r, c) for r in range(h) for c in range(w) if g[r][c] == NOZZLE)
    tail = {g[a][b] for a, b in ((nr + 1, nc), (nr - 1, nc), (nr, nc + 1), (nr, nc - 1))
            if 0 <= a < h and 0 <= b < w} - {bg, NOZZLE}
    if len(tail) != 1:
        return [row[:] for row in grid]
    STREAM = next(iter(tail))
    rest = [v for v in tally if v not in (bg, NOZZLE, STREAM)]
    if len(rest) != 2:
        return [row[:] for row in grid]
    DOOR = min(rest, key=lambda v: tally[v])

    src = None
    for r in range(h):
        for c in range(w):
            if g[r][c] == NOZZLE:
                src = (r, c)
    if src is None:
        return g
    sr, sc = src

    direction = None
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nr, nc = sr + dr, sc + dc
        if 0 <= nr < h and 0 <= nc < w and g[nr][nc] == STREAM:
            direction = (-dr, -dc)
    if direction is None:
        return g

    # shapes: connected runs of anything that is not background, stream or nozzle
    seen, shapes = set(), []
    for r in range(h):
        for c in range(w):
            if (r, c) in seen or g[r][c] in (bg, STREAM, NOZZLE):
                continue
            stack, cells = [(r, c)], []
            seen.add((r, c))
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if (0 <= ny < h and 0 <= nx < w and (ny, nx) not in seen
                            and g[ny][nx] not in (bg, STREAM, NOZZLE)):
                        seen.add((ny, nx))
                        stack.append((ny, nx))
            shapes.append(cells)
    owner = {cell: i for i, cells in enumerate(shapes) for cell in cells}

    out = [[bg] * w for _ in range(h)]
    out[sr][sc] = STREAM
    for r in range(h):
        for c in range(w):
            if g[r][c] == STREAM:
                out[r][c] = STREAM

    # One ray per door cell, so a two-wide door produces a two-wide run.
    rays = deque([(sr, sc, direction[0], direction[1])])
    lit = set()
    guard = 0
    while rays and guard < 8 * h * w:
        r, c, dr, dc = rays.popleft()
        while True:
            guard += 1
            if guard > 8 * h * w:
                break
            r, c = r + dr, c + dc
            if not (0 <= r < h and 0 <= c < w):
                break
            i = owner.get((r, c))
            if i is None:
                out[r][c] = STREAM
                continue
            if i in lit:
                break
            lit.add(i)
            cells = shapes[i]
            for y, x in cells:
                out[y][x] = STREAM
            doors = [(y, x) for y, x in cells if g[y][x] == DOOR]
            if not doors:
                break
            cy = sum(y for y, _ in cells) / len(cells)
            cx = sum(x for _, x in cells) / len(cells)
            dy = sum(y for y, _ in doors) / len(doors) - cy
            dx = sum(x for _, x in doors) / len(doors) - cx
            if abs(dy) >= abs(dx):
                ndr, ndc = (1 if dy > 0 else -1), 0
            else:
                ndr, ndc = 0, (1 if dx > 0 else -1)
            for y, x in doors:
                rays.append((y, x, ndr, ndc))
            break
    return out
