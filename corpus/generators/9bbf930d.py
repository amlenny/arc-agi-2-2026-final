"""9bbf930d -- the marker rolls out of a channel that has been unlocked.

Coloured bars stack down the grid with a clear channel between each pair, and a
marker waits at the left wall of every channel.  A channel unlocks only when
the bars above and below it are the SAME colour; the markers in the others stay
put.

An unlocked marker rolls right and keeps going, turning wherever the way ahead
is walled and exactly one side is open, until it reaches the edge of the grid
or a spot with no single way on.  It will not run down a channel that still
holds its own marker, so it halts at that junction instead.
"""


def transform(gi):
    H, W = len(gi), len(gi[0])
    road = gi[0][1]
    mark = gi[0][0]

    def bar(r):
        row = [v for c, v in enumerate(gi[r]) if c and v != road]
        return max(set(row), key=row.count) if row else None

    open_row = [r for r in range(1, H - 1, 2) if bar(r - 1) == bar(r + 1) and bar(r - 1) is not None]

    taken = set()
    for r in range(1, H - 1, 2):
        if r in open_row:
            continue
        c = 1
        while c < W and gi[r][c] == road:
            taken.add((r, c))
            c += 1

    go = [row[:] for row in gi]
    for r in open_row:
        cur, d = (r, 1), (0, 1)
        for _ in range(4 * H * W):
            n = (cur[0] + d[0], cur[1] + d[1])
            if not (0 <= n[0] < H and 0 <= n[1] < W):
                break
            if gi[n[0]][n[1]] == road and not (d[0] == 0 and n in taken):
                cur = n
                continue
            ways = []
            for e in ((d[1], d[0]), (-d[1], -d[0])):
                m = (cur[0] + e[0], cur[1] + e[1])
                if (0 <= m[0] < H and 0 <= m[1] < W and gi[m[0]][m[1]] == road
                        and not (e[0] == 0 and m in taken)):
                    ways.append(e)
            if len(ways) != 1:
                break
            d = ways[0]
        go[r][0] = road
        go[cur[0]][cur[1]] = mark
    return go
