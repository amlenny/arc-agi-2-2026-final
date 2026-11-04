"""a251c730 -- stamp the worked panel's badges onto the bare one.

Two framed panels sit on the patterned board.  One has badges drawn out in full;
the other has only their middles, dropped on their own.  Every badge is pinned
by that middle, so stamp each badge onto the bare panel wherever its own middle
sits, and hand that panel back.
"""


def _blobs(cells, near):
    left = set(cells)
    out = []
    while left:
        seed = left.pop()
        blob, stack = [seed], [seed]
        while stack:
            x, y = stack.pop()
            for dr, dc in near:
                p = (x + dr, y + dc)
                if p in left:
                    left.discard(p)
                    blob.append(p)
                    stack.append(p)
        out.append(blob)
    return out


ROUND = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b]


def _panels(gi):
    """Every rectangle drawn as a plain frame round a plainer inside."""
    H, W = len(gi), len(gi[0])
    right = [[1] * W for _ in range(H)]
    down = [[1] * H for _ in range(W)]
    for r in range(H):
        for c in range(W - 2, -1, -1):
            if gi[r][c] == gi[r][c + 1]:
                right[r][c] = right[r][c + 1] + 1
    for c in range(W):
        for r in range(H - 2, -1, -1):
            if gi[r][c] == gi[r + 1][c]:
                down[c][r] = down[c][r + 1] + 1

    found = []
    for r0 in range(H):
        for c0 in range(W):
            hue = gi[r0][c0]
            for c1 in range(c0 + 3, min(W, c0 + right[r0][c0])):
                for r1 in range(r0 + 3, min(H, r0 + min(down[c0][r0], down[c1][r0]))):
                    if gi[r1][c0] != hue or right[r1][c0] < c1 - c0 + 1:
                        continue
                    seen = {}
                    for r in range(r0 + 1, r1):
                        for c in range(c0 + 1, c1):
                            seen[gi[r][c]] = seen.get(gi[r][c], 0) + 1
                    paper = max(seen, key=lambda k: seen[k])
                    if paper == hue or seen[paper] * 2 < sum(seen.values()):
                        continue
                    found.append((r0, r1, c0, c1))
    found.sort(key=lambda b: -(b[1] - b[0]) * (b[3] - b[2]))
    out = []
    for b in found:
        if all(b[1] < o[0] or o[1] < b[0] or b[3] < o[2] or o[3] < b[2] for o in out):
            out.append(b)
        if len(out) == 2:
            break
    return out


def transform(gi):
    boards = _panels(gi)
    faces = []
    for r0, r1, c0, c1 in boards:
        seen = {}
        for r in range(r0 + 1, r1):
            for c in range(c0 + 1, c1):
                seen[gi[r][c]] = seen.get(gi[r][c], 0) + 1
        paper = max(seen, key=lambda k: seen[k])
        marks = [(r, c) for r in range(r0 + 1, r1) for c in range(c0 + 1, c1)
                 if gi[r][c] != paper]
        faces.append((r0, r1, c0, c1, paper, marks))

    worked, bare = sorted(faces, key=lambda f: -len(f[5]))
    pins = {gi[r][c] for r, c in bare[5]}

    badges = {}
    for blob in _blobs(worked[5], ROUND):
        pin = next(p for p in blob if gi[p[0]][p[1]] in pins)
        badges[gi[pin[0]][pin[1]]] = [(r - pin[0], c - pin[1], gi[r][c]) for r, c in blob]

    r0, r1, c0, c1, paper, marks = bare
    go = [[gi[r][c] for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
    for r, c in marks:
        for dr, dc, hue in badges[gi[r][c]]:
            go[r + dr - r0][c + dc - c0] = hue
    return go
