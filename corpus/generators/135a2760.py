"""135a2760 -- mend the wallpaper inside every frame.

The board is a set of framed panels: peel off the plain borders, ring after
ring, and what is left in each panel is a strip of repeating pattern running
along its long side.  A few cells have been knocked out of step.  Read the
repeat off the strip and put every cell back to what its position says it
should be.
"""


def _panels(gi, r0, r1, c0, c1, rules, out):
    """Peel plain rings, split on the board's own rules, and what is left is a strip."""
    if r1 - r0 >= 2 and c1 - c0 >= 2:
        ring = {gi[r][c] for r in (r0, r1) for c in range(c0, c1 + 1)}
        ring |= {gi[r][c] for c in (c0, c1) for r in range(r0, r1 + 1)}
        if len(ring) == 1:
            _panels(gi, r0 + 1, r1 - 1, c0 + 1, c1 - 1, rules, out)
            return
    for r in range(r0 + 1, r1):
        if r in rules[0]:
            _panels(gi, r0, r - 1, c0, c1, rules, out)
            _panels(gi, r + 1, r1, c0, c1, rules, out)
            return
    for c in range(c0 + 1, c1):
        if c in rules[1]:
            _panels(gi, r0, r1, c0, c - 1, rules, out)
            _panels(gi, r0, r1, c + 1, c1, rules, out)
            return
    out.append((r0, r1, c0, c1))


def _repeat(lines):
    """The shortest repeat that leaves the fewest cells out of step."""
    n, wide = len(lines), len(lines[0])
    best, pick = None, n
    for p in range(1, max(2, n // 3 + 1)):
        off = 0
        for i in range(p):
            band = [lines[j] for j in range(i, n, p)]
            for k in range(wide):
                seen = [row[k] for row in band]
                off += len(seen) - seen.count(max(set(seen), key=seen.count))
        if best is None or off < best:
            best, pick = off, p
    return pick


def transform(gi):
    H, W = len(gi), len(gi[0])
    go = [row[:] for row in gi]
    rules = ({r for r in range(H) if len(set(gi[r])) == 1},
             {c for c in range(W) if len({gi[r][c] for r in range(H)}) == 1})
    panels = []
    _panels(gi, 0, H - 1, 0, W - 1, rules, panels)
    for r0, r1, c0, c1 in panels:
        tall = (r1 - r0) >= (c1 - c0)
        lines = ([[gi[r][c] for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)] if tall
                 else [[gi[r][c] for r in range(r0, r1 + 1)] for c in range(c0, c1 + 1)])
        p = _repeat(lines)
        n = len(lines)
        for i in range(p):
            band = list(range(i, n, p))
            for k in range(len(lines[0])):
                seen = [lines[j][k] for j in band]
                best = max(set(seen), key=seen.count)
                for j in band:
                    if tall:
                        go[r0 + j][c0 + k] = best
                    else:
                        go[r0 + k][c0 + j] = best
    return go
