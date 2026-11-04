"""2ba387bc -- pair the empty boxes off against the full ones.

The board is scattered with four-by-four boxes, some hollow and some solid.
Take the hollow ones down the board in order and the solid ones likewise, and
set them side by side a pair to a row -- hollow on the left, solid on the right.
Whichever kind runs out first leaves its side of the last rows blank.
"""

SIDE = 4


def transform(gi):
    H, W = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])

    seen, hollow, solid = set(), [], []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or gi[r][c] == bg:
                continue
            hue = gi[r][c]
            stack, cur = [(r, c)], []
            seen.add((r, c))
            while stack:
                x, y = stack.pop()
                cur.append((x, y))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        a, b = x + dx, y + dy
                        if 0 <= a < H and 0 <= b < W and (a, b) not in seen and gi[a][b] == hue:
                            seen.add((a, b))
                            stack.append((a, b))
            (solid if len(cur) == SIDE * SIDE else hollow).append((r, c, hue))

    hollow.sort()
    solid.sort()
    go = []
    for i in range(max(len(hollow), len(solid))):
        for a in range(SIDE):
            row = []
            for kind, box in ((0, hollow), (1, solid)):
                if i >= len(box):
                    row += [bg] * SIDE
                    continue
                hue = box[i][2]
                row += [hue if kind or a in (0, SIDE - 1) or b in (0, SIDE - 1) else bg
                        for b in range(SIDE)]
            go.append(row)
    return go
