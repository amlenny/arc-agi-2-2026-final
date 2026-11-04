"""71e489b6 -- ring the punctures, rub out the specks.

The board is really a few big blue panels laid out on a grid of row bands and
column bands.  Someone has speckled it: stray blue cells dropped on bare board,
and single cells punched out of the panels.

Recover the panels -- the bands show up as the places where one row (or column)
stops resembling the last -- and each block votes on its own colour.  Then rub
out the strays, leave every puncture open, and ring each puncture in orange.

WHICH COLOUR IS THE PANEL AND WHICH THE BARE BOARD is read off the damage, not
assumed.  A hole punched in a panel can be several cells across; a speck dropped
on bare board is always a single cell.  Take each colour in turn to be the board
and rebuild: the right way round leaves every stray a lone cell and at least one
puncture bigger than that, on all five pairs.  Counting the defects instead ties
on demo 2, three against three, and the commonest colour is the board on two
pairs and the panel on three.
"""


def _roles(gi, rows, cols):
    """(board, panel) -- decided by the shape of the damage."""
    H, W = len(gi), len(gi[0])
    hues = sorted({v for row in gi for v in row})
    if len(hues) != 2:
        return None
    best = None
    for bg in hues:
        ink = next(v for v in hues if v != bg)
        clean = [[bg] * W for _ in range(H)]
        for rb in rows:
            for cb in cols:
                block = [gi[r][c] for r in rb for c in cb]
                if block.count(ink) * 2 > len(block):
                    for r in rb:
                        for c in cb:
                            clean[r][c] = ink
        punct = {(r, c) for r in range(H) for c in range(W)
                 if clean[r][c] == ink and gi[r][c] == bg}
        stray = {(r, c) for r in range(H) for c in range(W)
                 if clean[r][c] == bg and gi[r][c] == ink}

        def biggest(ps):
            seen, top = set(), 0
            for p in ps:
                if p in seen:
                    continue
                stack, n = [p], 0
                seen.add(p)
                while stack:
                    y, x = stack.pop()
                    n += 1
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            q = (y + dy, x + dx)
                            if q in ps and q not in seen:
                                seen.add(q)
                                stack.append(q)
                top = max(top, n)
            return top

        key = (biggest(stray), -biggest(punct))
        if best is None or key < best[0]:
            best = (key, bg, ink)
    return best[1], best[2]

RING = 7            # painted by the rule; it appears in no input
SPLIT = 5           # rows this different belong to different bands


def _bands(n, dist):
    cuts = [0] + [i for i in range(1, n) if dist(i - 1, i) >= SPLIT] + [n]
    return [range(cuts[i], cuts[i + 1]) for i in range(len(cuts) - 1)]


def transform(gi):
    H, W = len(gi), len(gi[0])
    rows = _bands(H, lambda a, b: sum(gi[a][c] != gi[b][c] for c in range(W)))
    cols = _bands(W, lambda a, b: sum(gi[r][a] != gi[r][b] for r in range(H)))
    cast = _roles(gi, rows, cols)
    if cast is None:
        return [row[:] for row in gi]
    bg, ink = cast

    clean = [[bg] * W for _ in range(H)]
    for rb in rows:
        for cb in cols:
            block = [gi[r][c] for r in rb for c in cb]
            if block.count(ink) * 2 > len(block):
                for r in rb:
                    for c in cb:
                        clean[r][c] = ink

    holes = {(r, c) for r in range(H) for c in range(W) if clean[r][c] == ink and gi[r][c] == bg}
    go = [row[:] for row in clean]
    for r, c in holes:
        go[r][c] = bg
    for r, c in holes:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                a, b = r + dr, c + dc
                if 0 <= a < H and 0 <= b < W and (a, b) not in holes:
                    go[a][b] = RING
    return go
