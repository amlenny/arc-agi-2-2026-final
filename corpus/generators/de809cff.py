"""de809cff -- every pinhole in a sheet shows the other sheet through it.

Two colours of sheet overlap on the board and both are pinholed.  Specks of
stray colour are scattered about too -- loose ones on bare board, a few dropped
onto the wrong sheet.

Find the sheets by their solid middles: a cell ringed on every side by its own
colour is inside a sheet for certain, and one such patch grown out by a
single cell gives back the whole rectangle.  A speck has no solid middle, so it
never makes a sheet, and repainting the sheets wipes it away.

Where two sheets overlap only the top one shows, so the whole overlap takes
whichever colour it mostly carries.  Then each pinhole -- a bare cell with sheet under it -- is stamped with a
three-by-three patch in the *other* sheet's colour and azure at the hole.
Overlapping patches merge.
"""

PIN = 8
NBRS = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b]
SOLID = 3           # a core patch smaller than this is a speck, not a sheet


def _sheets(gi, bg):
    H, W = len(gi), len(gi[0])
    core = [[gi[r][c] if gi[r][c] != bg and all(gi[r + dr][c + dc] == gi[r][c] for dr, dc in NBRS
                                                if 0 <= r + dr < H and 0 <= c + dc < W) else bg
             for c in range(W)] for r in range(H)]
    seen, out = set(), []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or core[r][c] == bg:
                continue
            ink = core[r][c]
            stack, cur = [(r, c)], []
            seen.add((r, c))
            while stack:
                x, y = stack.pop()
                cur.append((x, y))
                for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= a < H and 0 <= b < W and (a, b) not in seen and core[a][b] == ink:
                        seen.add((a, b))
                        stack.append((a, b))
            if len(cur) < SOLID:
                continue
            out.append(_grow(gi, bg, ink,
                             min(r for r, _ in cur), max(r for r, _ in cur),
                             min(c for _, c in cur), max(c for _, c in cur)))
    return out


def _grow(gi, bg, ink, r0, r1, c0, c1):
    """Push the rectangle out while the next line is still sheet, not bare board."""
    H, W = len(gi), len(gi[0])
    moved = True
    while moved:
        moved = False
        for side in range(4):
            if side == 0 and r0 > 0:
                line = [gi[r0 - 1][c] for c in range(c0, c1 + 1)]
            elif side == 1 and r1 < H - 1:
                line = [gi[r1 + 1][c] for c in range(c0, c1 + 1)]
            elif side == 2 and c0 > 0:
                line = [gi[r][c0 - 1] for r in range(r0, r1 + 1)]
            elif side == 3 and c1 < W - 1:
                line = [gi[r][c1 + 1] for r in range(r0, r1 + 1)]
            else:
                continue
            if line.count(bg) * 6 > len(line) or ink not in line:
                continue
            r0 -= side == 0
            r1 += side == 1
            c0 -= side == 2
            c1 += side == 3
            moved = True
    return ink, r0, r1, c0, c1


def transform(gi):
    H, W = len(gi), len(gi[0])
    # THE BARE BOARD IS THE BORDER'S OWN COLOUR, not the commonest -- both sheets outweigh it on
    # every pair here (152 and 135 against 113; 167 and 107 against 126; 379 and 279 against 242),
    # while it holds a clear plurality of the border (39 of 64, 31 of 55, 80 of 115).
    edge = {}
    for r in range(H):
        for c in range(W):
            if r in (0, H - 1) or c in (0, W - 1):
                edge[gi[r][c]] = edge.get(gi[r][c], 0) + 1
    bg = max(edge, key=lambda k: edge[k])
    tally = {}
    for row in gi:
        for v in row:
            if v != bg:
                tally[v] = tally.get(v, 0) + 1
    inks = sorted(tally, key=lambda k: -tally[k])[:2]
    other = {inks[0]: inks[1], inks[1]: inks[0]}

    sheets = sorted(set(_sheets(gi, bg)))
    cover = [[[] for _ in range(W)] for _ in range(H)]
    for i, (ink, r0, r1, c0, c1) in enumerate(sheets):
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                cover[r][c].append(i)

    vote = {}
    laid = [[bg] * W for _ in range(H)]
    for r in range(H):
        for c in range(W):
            here = cover[r][c]
            if not here:
                continue
            inked = {sheets[i][0] for i in here}
            if len(inked) == 1:
                laid[r][c] = inked.pop()
                continue
            tag = tuple(sorted(here))
            if tag not in vote:
                tally2 = {sheets[i][0]: 0 for i in tag}
                for a in range(H):
                    for b in range(W):
                        if tuple(sorted(cover[a][b])) == tag and gi[a][b] in tally2:
                            tally2[gi[a][b]] += 1
                vote[tag] = max(tally2, key=lambda k: tally2[k])
            laid[r][c] = vote[tag]

    go = [row[:] for row in laid]
    holes = [(r, c) for r in range(H) for c in range(W)
             if gi[r][c] == bg and laid[r][c] != bg]
    for r, c in holes:
        ink = other[laid[r][c]]
        for dr, dc in NBRS + [(0, 0)]:
            a, b = r + dr, c + dc
            if 0 <= a < H and 0 <= b < W:
                go[a][b] = ink
    for r, c in holes:
        go[r][c] = PIN
    return go
