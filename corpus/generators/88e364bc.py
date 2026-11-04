"""88e364bc -- the loose pips slide the way their own key says.

Each key is a small framed box.  Inside it sits a short arrow: a line of pips
tipped with a 2.  The way the line points at its 2 is the direction that the
box's FRAME COLOUR sends things.

Every loose 4 on the board slides in a straight line until it fetches up
against a wall, and the wall it lands against tells you which key it was
obeying: a 4 travels the direction whose key colour matches the wall that stops
it.  It comes to rest on the last clear cell.

A diagonal slide will not cut a corner: a wall on either side of the step stops
it just as surely as a wall in the step itself.
"""

# SLIDER AND TIP ARE NAMED BY THEIR COLOURS. Both are scattered single cells, which is what makes
# them hard to separate. Cell count does not: the slider outnumbers the tip on some pairs and not
# others. Enclosure does not: the key frames are solid blocks rather than hollow rectangles, so a
# ring test finds no box at all. Adjacency to the arrow line separates them on four pairs and fails
# on test 0, whose arrows are bare tips with no line and whose only other neighbour is a wall.
PIP, TIP = 4, 2
N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _keys(gi, bg, H, W):
    """Each key box: its frame colour and the way its arrow points."""
    out = {}
    for r in range(H):
        for c in range(W):
            if gi[r][c] != TIP:
                continue
            st, comp, seen = [(r, c)], [], {(r, c)}
            while st:
                y, x = st.pop()
                comp.append((y, x))
                for dy, dx in N8:
                    q = (y + dy, x + dx)
                    if (0 <= q[0] < H and 0 <= q[1] < W and gi[q[0]][q[1]] != bg
                            and q not in seen):
                        seen.add(q)
                        st.append(q)
            shade = [gi[y][x] for y, x in comp]
            frame = max(set(shade), key=shade.count)
            for dy, dx in N8:
                y, x = r - dy, c - dx
                if (0 <= y < H and 0 <= x < W and gi[y][x] not in (bg, frame, TIP)):
                    out[frame] = (dy, dx)
    return out


def transform(gi):
    H, W = len(gi), len(gi[0])
    flat = [v for row in gi for v in row]
    bg = max(set(flat), key=flat.count)
    keys = _keys(gi, bg, H, W)

    pips = [(r, c) for r in range(H) for c in range(W) if gi[r][c] == PIP]
    go = [row[:] for row in gi]
    for r, c in pips:
        go[r][c] = bg

    rest = []
    for r, c in pips:
        for frame, (dy, dx) in keys.items():
            y, x = r, c
            while True:
                ny, nx = y + dy, x + dx
                if not (0 <= ny < H and 0 <= nx < W):
                    y = None
                    break
                stop = None
                if go[ny][nx] != bg:
                    stop = go[ny][nx]
                elif dy and dx:                       # no cutting a corner
                    for cy, cx in ((y, nx), (ny, x)):
                        if go[cy][cx] != bg:
                            stop = go[cy][cx]
                if stop is not None:
                    if stop != frame:
                        y = None
                    break
                y, x = ny, nx
            if y is not None:
                rest.append((y, x))
                break
    for y, x in rest:
        go[y][x] = PIP
    return go
