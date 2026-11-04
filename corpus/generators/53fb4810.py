"""53fb4810 -- every streamer is played out to the edge.

Each arrowhead trails a banner behind it, a couple of coloured threads whose
pattern repeats.  Read the repeat off the length already flown and carry it on,
band after band, until it runs off the board -- straight over anything already
in the way.

Which colour is the arrowhead comes off the board, not from a constant: an
arrowhead is a BLOB and a thread is a LINE, so the head is the only colour with
a component spanning more than one row AND more than one column.  Total
separation on all three pairs -- every other colour has none at all.
"""

SIDES = ((-1, 0), (1, 0), (0, -1), (0, 1))


def _head(gi, bg):
    """The arrowhead colour: the one whose pieces are two-dimensional."""
    H, W = len(gi), len(gi[0])
    blobs = {}
    for hue in {v for row in gi for v in row} - {bg}:
        seen, n = set(), 0
        for r in range(H):
            for c in range(W):
                if gi[r][c] != hue or (r, c) in seen:
                    continue
                stack, cur = [(r, c)], []
                seen.add((r, c))
                while stack:
                    x, y = stack.pop()
                    cur.append((x, y))
                    for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                        if 0 <= a < H and 0 <= b < W and (a, b) not in seen and gi[a][b] == hue:
                            seen.add((a, b))
                            stack.append((a, b))
                if len({x for x, _ in cur}) > 1 and len({y for _, y in cur}) > 1:
                    n += 1
        if n:
            blobs[hue] = n
    if len(blobs) != 1:
        return None
    return next(iter(blobs))


def transform(gi):
    H, W = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])
    HEAD = _head(gi, bg)
    if HEAD is None:
        return [row[:] for row in gi]

    seen, heads = set(), []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or gi[r][c] != HEAD:
                continue
            stack, cur = [(r, c)], []
            seen.add((r, c))
            while stack:
                x, y = stack.pop()
                cur.append((x, y))
                for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= a < H and 0 <= b < W and (a, b) not in seen and gi[a][b] == HEAD:
                        seen.add((a, b))
                        stack.append((a, b))
            heads.append(cur)

    go = [row[:] for row in gi]
    for head in heads:
        r0 = min(r for r, _ in head)
        r1 = max(r for r, _ in head)
        c0 = min(c for _, c in head)
        c1 = max(c for _, c in head)
        for dr, dc in SIDES:
            edge = ([(r0 - 1 if dr < 0 else r1 + 1, c) for c in range(c0, c1 + 1)] if dr
                    else [(r, c0 - 1 if dc < 0 else c1 + 1) for r in range(r0, r1 + 1)])
            if any(not (0 <= r < H and 0 <= c < W) for r, c in edge):
                continue
            threads = [p for p in edge if gi[p[0]][p[1]] not in (bg, HEAD)]
            if not threads:
                continue

            flown = []
            k = 0
            while True:
                band = [(r + dr * k, c + dc * k) for r, c in threads]
                if any(not (0 <= r < H and 0 <= c < W) for r, c in band):
                    break
                if all(gi[r][c] == bg for r, c in band):
                    break
                flown.append([gi[r][c] for r, c in band])
                k += 1
            if not flown:
                continue
            beat = next((p for p in range(1, len(flown) + 1)
                         if all(flown[i] == flown[i % p] for i in range(len(flown)))), len(flown))
            while True:
                band = [(r + dr * k, c + dc * k) for r, c in threads]
                if any(not (0 <= r < H and 0 <= c < W) for r, c in band):
                    break
                for (r, c), v in zip(band, flown[k % beat]):
                    go[r][c] = v
                k += 1
    return go
