# Rule authored from the evaluation demonstrations of 446ef5d2.
#
# The pieces of one figure lie scattered. The answer reassembles them into a single rectangle.
#
#   * one piece carries a MARKER colour — the colour that appears in exactly one piece. That piece
#     does not move; the finished figure is positioned so it lands back where it already is. The
#     marker cells are scaffolding and are not part of the piece.
#   * the marker hangs off the corner of the rectangle that piece occupies: top-left in demo 1,
#     bottom-right in demo 0.
#   * every other piece is translated into place. Nothing rotates and nothing reflects.
#
# THE PIECES ARE NOT RECTANGLES. Both demonstrations happen to use solid blocks, and a packer
# written against their bounding boxes reproduces them and then fails test 0, where the bounding
# boxes total 228 cells against a 220-cell figure. What tiles exactly is the CELLS: 220 = 22x10,
# and the same holds in all four pairs. So this is exact cover by polyominoes, not by rectangles.
#
# EXACT TILING ALONE DOES NOT PICK THE ARRANGEMENT. Demo 1's four pieces are all 3x3, so every
# permutation fills the box and three in four are wrong. The finished figure is a closed FRAME:
# every cell on its border is one colour. That is what selects the assembly, and it is checked
# rather than assumed.
from collections import Counter, deque


def _components(grid, bg):
    h, w = len(grid), len(grid[0])
    seen, out = set(), []
    for r in range(h):
        for c in range(w):
            if grid[r][c] == bg or (r, c) in seen:
                continue
            q, cs = deque([(r, c)]), []
            seen.add((r, c))
            while q:
                y, x = q.popleft()
                cs.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        a, b = y + dy, x + dx
                        if 0 <= a < h and 0 <= b < w and (a, b) not in seen and grid[a][b] != bg:
                            seen.add((a, b))
                            q.append((a, b))
            out.append(cs)
    return out


def _tile(cells, grid):
    """A piece as offsets from its own top-left, with colours. Pieces are NOT rectangles."""
    r0 = min(y for y, _ in cells)
    c0 = min(x for _, x in cells)
    return sorted(((y - r0, x - c0, grid[y][x]) for y, x in cells))


def _pack(H, W, tiles, ai, apos):
    """Exact cover of H x W by the tiles, no rotation, anchor pinned at apos."""
    grid = [[None] * W for _ in range(H)]
    used = [False] * len(tiles)

    def place(i, r, c):
        for dy, dx, v in tiles[i]:
            a, b = r + dy, c + dx
            if not (0 <= a < H and 0 <= b < W) or grid[a][b] is not None:
                return False
        for dy, dx, v in tiles[i]:
            grid[r + dy][c + dx] = v
        return True

    def lift(i, r, c):
        for dy, dx, _ in tiles[i]:
            grid[r + dy][c + dx] = None

    if not place(ai, *apos):
        return None
    used[ai] = True

    def solve():
        spot = None
        for r in range(H):
            for c in range(W):
                if grid[r][c] is None:
                    spot = (r, c)
                    break
            if spot:
                break
        if spot is None:
            if not all(used):
                return False
            edge = ([grid[0][c] for c in range(W)] + [grid[H - 1][c] for c in range(W)]
                    + [grid[r][0] for r in range(H)] + [grid[r][W - 1] for r in range(H)])
            return len(set(edge)) == 1
        r, c = spot
        for i in range(len(tiles)):
            if used[i]:
                continue
            # the piece's own first cell must land on the first empty cell, or an earlier cell
            # would be left uncoverable
            dy0, dx0, _ = tiles[i][0]
            if place(i, r - dy0, c - dx0):
                used[i] = True
                if solve():
                    return True
                used[i] = False
                lift(i, r - dy0, c - dx0)
        return False

    return [row[:] for row in grid] if solve() else None


def transform(grid):
    h, w = len(grid), len(grid[0])
    bg = Counter(v for row in grid for v in row).most_common(1)[0][0]
    comps = _components(grid, bg)
    if not comps:
        return [row[:] for row in grid]
    colours = [{grid[y][x] for y, x in cs} for cs in comps]

    # THE MARKER is the colour living in exactly one piece; that piece is the one that stays put.
    marker = None
    for col in set().union(*colours):
        holders = [i for i, s in enumerate(colours) if col in s]
        if len(holders) == 1:
            n = sum(1 for y, x in comps[holders[0]] if grid[y][x] == col)
            if marker is None or n < marker[2]:
                marker = (col, holders[0], n)
    if marker is None:
        return [row[:] for row in grid]
    mcol, ai, _ = marker

    tiles, keeps = [], []
    for i, cs in enumerate(comps):
        keep = [(y, x) for y, x in cs if grid[y][x] != mcol] if i == ai else list(cs)
        keeps.append(keep)
        tiles.append(_tile(keep, grid))
    total = sum(len(t) for t in tiles)
    ar0 = min(y for y, _ in keeps[ai]); ac0 = min(x for _, x in keeps[ai])
    ah = max(y for y, _ in keeps[ai]) - ar0 + 1
    aw = max(x for _, x in keeps[ai]) - ac0 + 1

    mk = [(y, x) for y, x in comps[ai] if grid[y][x] == mcol]
    my = sum(y for y, _ in mk) / len(mk)
    mx = sum(x for _, x in mk) / len(mk)
    at_bottom = my > ar0 + (ah - 1) / 2
    at_right = mx > ac0 + (aw - 1) / 2

    for H in range(1, total + 1):
        if total % H:
            continue
        W = total // H
        if H < ah or W < aw:
            continue
        # the corner the marker points at first, then anywhere else it could sit
        prefer = [((H - ah) if at_bottom else 0, (W - aw) if at_right else 0)]
        cand = prefer + [(r, c) for r in range(H - ah + 1) for c in range(W - aw + 1)
                         if (r, c) != prefer[0]]
        for ar, ac in cand:
            packed = _pack(H, W, tiles, ai, (ar, ac))
            if packed is None:
                continue
            oy, ox = ar0 - ar, ac0 - ac
            if oy < 0 or ox < 0 or oy + H > h or ox + W > w:
                continue
            out = [[bg] * w for _ in range(h)]
            for a in range(H):
                for b in range(W):
                    out[oy + a][ox + b] = packed[a][b]
            return out
    return [row[:] for row in grid]
