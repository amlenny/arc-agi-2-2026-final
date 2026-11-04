"""80a900e0 -- each wall shoots off its ends, away from the ring it guards.

The board is a diagonal lattice.  Rings of coloured cells sit on it and are
left alone; beside them lie short straight WALLS running along a ring's edge.

Only the two END cells of a wall fire.  Each fires square out from the wall on
the side facing away from the ring -- the side that is not already blocked by
coloured cells -- and the shot runs on to the edge of the board.
"""

N8 = [(-1, -1), (-1, 1), (1, -1), (1, 1), (-1, 0), (1, 0), (0, -1), (0, 1)]


def transform(gi):
    H, W = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    plain = set(sorted(tally, key=lambda v: -tally[v])[:2])
    ink = {(r, c) for r in range(H) for c in range(W) if gi[r][c] not in plain}

    seen, walls = set(), []
    for p in sorted(ink):
        if p in seen:
            continue
        st, comp = [p], []
        seen.add(p)
        while st:
            y, x = st.pop()
            comp.append((y, x))
            for dy, dx in N8:
                q = (y + dy, x + dx)
                if q in ink and q not in seen and gi[q[0]][q[1]] == gi[p[0]][p[1]]:
                    seen.add(q)
                    st.append(q)
        if len(comp) < 2:
            continue
        if len({r - c for r, c in comp}) == 1:
            walls.append((comp, (1, 1)))
        elif len({r + c for r, c in comp}) == 1:
            walls.append((comp, (1, -1)))

    go = [row[:] for row in gi]
    for comp, run in walls:
        hue = gi[comp[0][0]][comp[0][1]]
        tips = [min(comp), max(comp)]
        for ty, tx in tips:
            for dy, dx in ((-run[0], run[1]), (run[0], -run[1])):
                if (ty + dy, tx + dx) in ink:
                    continue
                y, x = ty + dy, tx + dx
                while 0 <= y < H and 0 <= x < W:
                    go[y][x] = hue
                    y, x = y + dy, x + dx
                break
    return go
