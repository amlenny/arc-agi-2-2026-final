"""8f3a5a89 -- one lap of the room, hand on the wall.

A lone marker sits in one of the rooms the blue walls cut the board into.  Walk
that room's whole outside edge with a hand on the wall -- the grid's own rim
counts as wall -- and leave orange behind.

Only walls this room touches are kept -- a whole wall, not just the face of it;
the other rooms, and whatever they contain, are wiped back to bare board.  A blue island floating
free inside the room is not part of the outside edge, so the walk never reaches
it and it stays unmarked.
"""

TRAIL = 7
NBRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def transform(gi):
    H, W = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])
    mark = min((v for v in tally if v != bg), key=lambda v: tally[v])
    wall = next(v for v in tally if v not in (bg, mark))

    start = next((r, c) for r in range(H) for c in range(W) if gi[r][c] == mark)

    room = {start}
    stack = [start]
    while stack:
        x, y = stack.pop()
        for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= a < H and 0 <= b < W and (a, b) not in room and gi[a][b] != wall:
                room.add((a, b))
                stack.append((a, b))

    # the rim of the board and every wall hanging off it, as one mass
    rim = {(r, c) for r in range(-1, H + 1) for c in (-1, W)}
    rim |= {(r, c) for r in (-1, H) for c in range(-1, W + 1)}
    stack = list(rim)
    while stack:
        x, y = stack.pop()
        for dx, dy in NBRS:
            a, b = x + dx, y + dy
            if 0 <= a < H and 0 <= b < W and (a, b) not in rim and gi[a][b] == wall:
                rim.add((a, b))
                stack.append((a, b))

    go = [[bg] * W for _ in range(H)]
    seen = set()
    for r in range(H):
        for c in range(W):
            if gi[r][c] != wall or (r, c) in seen:
                continue
            blob, stack, seen2 = [], [(r, c)], {(r, c)}
            while stack:
                x, y = stack.pop()
                blob.append((x, y))
                for dx, dy in NBRS:
                    a, b = x + dx, y + dy
                    if 0 <= a < H and 0 <= b < W and (a, b) not in seen2 and gi[a][b] == wall:
                        seen2.add((a, b))
                        stack.append((a, b))
            seen |= seen2
            if any((x + dx, y + dy) in room for x, y in blob for dx, dy in NBRS):
                for x, y in blob:
                    go[x][y] = wall
    for r, c in room:
        if any((r + dx, c + dy) in rim for dx, dy in NBRS):
            go[r][c] = TRAIL
    go[start[0]][start[1]] = mark
    return go
