"""bf45cf4b -- stamp the patterned block wherever the stencil is solid.

Two shapes lie on the board: a stencil drawn in one flat colour, and a block of
several colours.  Blow the stencil up so each of its cells is a whole block --
printed where the stencil is solid, left bare where it is not.
"""


def _shapes(gi, bg):
    H, W = len(gi), len(gi[0])
    seen, out = set(), []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or gi[r][c] == bg:
                continue
            stack, cur = [(r, c)], []
            seen.add((r, c))
            while stack:
                x, y = stack.pop()
                cur.append((x, y))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        a, b = x + dx, y + dy
                        if 0 <= a < H and 0 <= b < W and (a, b) not in seen and gi[a][b] != bg:
                            seen.add((a, b))
                            stack.append((a, b))
            out.append(cur)
    return out


def _crop(gi, cells):
    r0 = min(r for r, _ in cells)
    r1 = max(r for r, _ in cells)
    c0 = min(c for _, c in cells)
    c1 = max(c for _, c in cells)
    return [[gi[r][c] for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]


def transform(gi):
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])

    parts = [_crop(gi, cells) for cells in _shapes(gi, bg)]
    stencil = next(p for p in parts if len({v for row in p for v in row} - {bg}) == 1)
    block = next(p for p in parts if p is not stencil)

    th, tw = len(block), len(block[0])
    return [[block[r % th][c % tw] if stencil[r // th][c // tw] != bg else bg
             for c in range(len(stencil[0]) * tw)]
            for r in range(len(stencil) * th)]
