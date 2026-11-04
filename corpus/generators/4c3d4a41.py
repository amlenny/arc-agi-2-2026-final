"""4c3d4a41 -- the stand is carried into the case and the bars ride up on it.

Off to one side stands a stepped stand; in the case are coloured bars, one
per slot.  Pick the stand up and set it down inside the case, its legs under the
slots, keeping its height.

Each bar now rests on top of its leg.  It keeps its own length unless the room
left above the leg is shorter, in which case only what fits stays, and any room
still spare above the bar shows grey.
"""



def _comps(g, pred):
    H, W = len(g), len(g[0])
    seen, out = set(), []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or not pred(g[r][c]):
                continue
            stack, cur = [(r, c)], []
            seen.add((r, c))
            while stack:
                x, y = stack.pop()
                cur.append((x, y))
                for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= a < H and 0 <= b < W and (a, b) not in seen and pred(g[a][b]):
                        seen.add((a, b))
                        stack.append((a, b))
            out.append(cur)
    return out


def transform(gi):
    H, W = len(gi), len(gi[0])
    # THE STAND AND THE BOARD NAME THEMSELVES BY WEIGHT. The board is the commonest colour; the
    # stand is the commonest of what is left, and it is not close -- 45-54 cells against 1-4 for
    # every bar, on all four pairs. It is also the only colour in two pieces (case and stand).
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])
    rest = [v for v in tally if v != bg]
    if not rest:
        return [row[:] for row in gi]
    GREY = max(rest, key=lambda v: tally[v])
    paint = [(r, c) for r in range(H) for c in range(W) if gi[r][c] not in (bg, GREY)]
    parts = _comps(gi, lambda v: v == GREY)
    case = next(p for p in parts
                if all(min(r for r, _ in p) <= r <= max(r for r, _ in p) and
                       min(c for _, c in p) <= c <= max(c for _, c in p) for r, c in paint))
    stand = next(p for p in parts if p is not case)

    slots = sorted({c for _, c in paint})
    legs = sorted({c for _, c in stand if sum(1 for r, x in stand if x == c) > 1})
    shift = slots[0] - legs[0]
    top = min(r for r, _ in case) + 1

    go = [[bg] * W for _ in range(H)]
    for r, c in case:
        go[r][c] = GREY
    for r, c in stand:
        go[r][c + shift] = GREY

    for i, slot in enumerate(slots):
        ink = gi[next(r for r, c in paint if c == slot)][slot]
        bar = sum(1 for r, c in paint if c == slot)
        head = min(r for r, c in stand if c == legs[i])
        room = head - top
        for k in range(room):
            go[top + k][slot] = GREY if k < room - min(bar, room) else ink
    return go
