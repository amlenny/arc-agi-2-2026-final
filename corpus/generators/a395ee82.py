"""a395ee82 -- the little constellation says where to print the figure.

One colour draws a FIGURE.  Elsewhere lies a constellation of loose dots spaced
two apart, one of which is in the figure's own colour: that dot is the origin,
and it stands for the figure where it already is.

Blow the constellation up so that one step of two becomes one whole figure --
a step down is the figure's height, a step across is its width -- and print a
copy of the figure at every dot.  The copy at the origin is printed in the dot
colour; the rest in the figure's own.  Nothing else survives.
"""

N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def transform(gi):
    H, W = len(gi), len(gi[0])
    flat = [v for row in gi for v in row]
    bg = max(set(flat), key=flat.count)

    seen, blobs = set(), []
    for r in range(H):
        for c in range(W):
            if gi[r][c] == bg or (r, c) in seen:
                continue
            st, comp = [(r, c)], []
            seen.add((r, c))
            while st:
                y, x = st.pop()
                comp.append((y, x))
                for dy, dx in N8:
                    q = (y + dy, x + dx)
                    if (0 <= q[0] < H and 0 <= q[1] < W and gi[q[0]][q[1]] == gi[r][c]
                            and q not in seen):
                        seen.add(q)
                        st.append(q)
            blobs.append(comp)

    art = max(blobs, key=len)
    ink = gi[art[0][0]][art[0][1]]
    r0 = min(p[0] for p in art); r1 = max(p[0] for p in art)
    c0 = min(p[1] for p in art); c1 = max(p[1] for p in art)
    tall, wide = r1 - r0 + 1, c1 - c0 + 1
    form = [(y - r0, x - c0) for y, x in art]

    spot = next((b[0] for b in blobs if b is not art and gi[b[0][0]][b[0][1]] == ink), None)
    if spot is None:
        return [row[:] for row in gi]
    dot = next(v for v in set(flat) - {bg, ink})

    stars = [(r, c) for r in range(H) for c in range(W) if gi[r][c] == dot] + [spot]
    go = [[bg] * W for _ in range(H)]
    for sy, sx in stars:
        i, j = (sy - spot[0]) // 2, (sx - spot[1]) // 2
        hue = dot if (i, j) == (0, 0) else ink
        for dy, dx in form:
            y, x = r0 + i * tall + dy, c0 + j * wide + dx
            if 0 <= y < H and 0 <= x < W:
                go[y][x] = hue
    return go
