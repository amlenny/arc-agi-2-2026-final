"""8f215267 -- each box is a tally of the litter in its own colour.

Down the side stand hollow boxes.  Scattered about are loose scraps.  Count the
scraps that share a box's colour and lay that many beads inside the box, along
its middle row, every other cell, packed against the right wall.  The scraps
themselves are swept away, and a colour with no box leaves nothing behind.
"""

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


def transform(gi):
    H, W = len(gi), len(gi[0])
    flat = [v for row in gi for v in row]
    bg = max(set(flat), key=flat.count)

    seen, lots = set(), []
    for r in range(H):
        for c in range(W):
            if gi[r][c] == bg or (r, c) in seen:
                continue
            st, comp = [(r, c)], []
            seen.add((r, c))
            while st:
                y, x = st.pop()
                comp.append((y, x))
                for dy, dx in N4:
                    q = (y + dy, x + dx)
                    if (0 <= q[0] < H and 0 <= q[1] < W and gi[q[0]][q[1]] == gi[r][c]
                            and q not in seen):
                        seen.add(q)
                        st.append(q)
            lots.append(comp)

    boxes, scraps = {}, {}
    for comp in lots:
        hue = gi[comp[0][0]][comp[0][1]]
        r0 = min(p[0] for p in comp); r1 = max(p[0] for p in comp)
        c0 = min(p[1] for p in comp); c1 = max(p[1] for p in comp)
        rim = {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)
               if r in (r0, r1) or c in (c0, c1)}
        if set(comp) == rim and r1 - r0 > 1 and c1 - c0 > 1:
            boxes[hue] = (r0, r1, c0, c1)
        else:
            scraps[hue] = scraps.get(hue, 0) + 1

    go = [row[:] for row in gi]
    for comp in lots:
        hue = gi[comp[0][0]][comp[0][1]]
        if hue in boxes and set(comp) == {(r, c)
                                          for r in range(boxes[hue][0], boxes[hue][1] + 1)
                                          for c in range(boxes[hue][2], boxes[hue][3] + 1)
                                          if r in boxes[hue][:2] or c in boxes[hue][2:]}:
            continue
        for y, x in comp:
            go[y][x] = bg

    for hue, (r0, r1, c0, c1) in boxes.items():
        mid = (r0 + r1) // 2
        for k in range(scraps.get(hue, 0)):
            x = c1 - 2 - 2 * k
            if c0 < x < c1:
                go[mid][x] = hue
    return go
