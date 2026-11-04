# Rule authored from the evaluation demonstrations of 62593bfd.
#
# Every shape slides vertically to an edge, keeping its columns and its internal structure. WHICH
# edge is decided by whether its cell count is shared with another shape: a size that appears more
# than once goes to the TOP, a size that appears exactly once goes to the BOTTOM. Demo 1 settles
# it — the two 9-cell shapes and the two 3-cell shapes all rise, while the lone 4-cell and 5-cell
# shapes fall, and no rule based on position, colour, profile or symmetry separates those the same
# way.

from collections import Counter, deque


def _components(grid, bg):
    h, w = len(grid), len(grid[0])
    seen, out = set(), []
    for r in range(h):
        for c in range(w):
            if grid[r][c] == bg or (r, c) in seen:
                continue
            q, cells = deque([(r, c)]), []
            seen.add((r, c))
            while q:
                y, x = q.popleft()
                cells.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if (0 <= ny < h and 0 <= nx < w and (ny, nx) not in seen
                                and grid[ny][nx] != bg):
                            seen.add((ny, nx))
                            q.append((ny, nx))
            out.append(cells)
    return out


def transform(grid):
    h, w = len(grid), len(grid[0])
    bg = Counter(v for row in grid for v in row).most_common(1)[0][0]
    shapes = _components(grid, bg)
    sizes = Counter(len(s) for s in shapes)

    out = [[bg] * w for _ in range(h)]
    for cells in shapes:
        top = min(r for r, _ in cells)
        bottom = max(r for r, _ in cells)
        # Shared size rises, unique size falls. Flush against the edge either way.
        shift = -top if sizes[len(cells)] > 1 else (h - 1 - bottom)
        for r, c in cells:
            out[r + shift][c] = grid[r][c]
    return out
