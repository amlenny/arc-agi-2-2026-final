"""800d221b -- each cable takes the colour its terminal votes for.

One colour runs as a single connected CABLE across the grid.  Somewhere on it
sits a solid 3x3 knot; cutting the knot out leaves the cable in separate
strands, and each strand runs out to a TERMINAL -- a patch speckled in the two
remaining colours.

A strand is repainted in whichever of the two colours holds the majority of its
terminal.  The knot's ring is left alone; only its middle cell is filled in, and
it reports the winner: the colour that ended up covering more of the cable.
"""

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


def _comps(keep, H, W):
    seen, out = set(), []
    for p in sorted(keep):
        if p in seen:
            continue
        st, comp = [p], []
        seen.add(p)
        while st:
            y, x = st.pop()
            comp.append((y, x))
            for dy, dx in N4:
                q = (y + dy, x + dx)
                if q in keep and q not in seen:
                    seen.add(q)
                    st.append(q)
        out.append(comp)
    return out


def transform(gi):
    H, W = len(gi), len(gi[0])
    flat = [v for row in gi for v in row]
    bg = max(set(flat), key=flat.count)
    shades = sorted(set(flat) - {bg})

    cable = None
    for s in shades:
        cells = {(r, c) for r in range(H) for c in range(W) if gi[r][c] == s}
        if len(_comps(cells, H, W)) == 1:
            cable = s
    if cable is None:
        return [row[:] for row in gi]
    paint = [s for s in shades if s != cable]

    wire = {(r, c) for r in range(H) for c in range(W) if gi[r][c] == cable}
    knot = None
    for r in range(H - 2):
        for c in range(W - 2):
            if all((r + a, c + b) in wire for a in range(3) for b in range(3)):
                knot = (r + 1, c + 1)
    if knot is None:
        return [row[:] for row in gi]
    lump = {(knot[0] + a, knot[1] + b) for a in (-1, 0, 1) for b in (-1, 0, 1)}

    pads = _comps({(r, c) for r in range(H) for c in range(W) if gi[r][c] in paint}, H, W)

    go = [row[:] for row in gi]
    tally = {s: 0 for s in paint}
    for strand in _comps(wire - lump, H, W):
        touch = set()
        for y, x in strand:
            for dy, dx in N4:
                q = (y + dy, x + dx)
                if 0 <= q[0] < H and 0 <= q[1] < W and gi[q[0]][q[1]] in paint:
                    touch.add(q)
        votes = [gi[y][x] for pad in pads if set(pad) & touch for y, x in pad]
        if not votes:
            continue
        win = max(paint, key=votes.count)
        tally[win] += len(strand)
        for y, x in strand:
            go[y][x] = win

    go[knot[0]][knot[1]] = max(paint, key=lambda s: tally[s])
    return go
