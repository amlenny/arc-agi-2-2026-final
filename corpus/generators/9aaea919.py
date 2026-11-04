"""9aaea919 -- one pile takes what the marked piles give up.

Piles of identical tokens stand in columns, and a strip along the bottom marks
some of the columns.  A red mark spends that pile: its tokens turn grey and stop
counting for it.  A green mark receives: that pile grows by as many tokens as
all the spent piles held between them.  The strip itself is cleared away.
"""

# SPEND AND TAKE ARE NAMED BY THEIR COLOURS. Mark count cannot separate them: three pairs carry one
# of each. Pile size cannot: the receiver holds more on demo 1 and fewer on demo 0. Overflow cannot:
# piles run 1 to 3 tokens on a 30-row grid, so both assignments fit. Exactly one assignment
# reproduces every pair, so the choice is decidable from the demonstrations but not from a grid.
SPEND = 2
TAKE = 3
GREY = 5


def transform(gi):
    H, W = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])

    live = {(r, c) for r in range(H - 1) for c in range(W) if gi[r][c] != bg}
    seen, piles = set(), {}
    for p in sorted(live):
        if p in seen:
            continue
        stack, cur = [p], []
        seen.add(p)
        while stack:
            x, y = stack.pop()
            cur.append((x, y))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (x + dx, y + dy)
                    if q in live and q not in seen:
                        seen.add(q)
                        stack.append(q)
        piles.setdefault(min(c for _, c in cur), []).append(cur)

    marks = {}
    c = 0
    while c < W:
        if gi[H - 1][c] != bg:
            start = c
            while c < W and gi[H - 1][c] == gi[H - 1][start]:
                c += 1
            marks[start] = gi[H - 1][start]
        else:
            c += 1

    spent = sum(len(piles[k]) for k, v in marks.items() if v == SPEND and k in piles)

    go = [row[:] for row in gi]
    for c in range(W):
        go[H - 1][c] = bg
    for at, kind in marks.items():
        if at not in piles:
            continue
        if kind == SPEND:
            for token in piles[at]:
                for r, c in token:
                    go[r][c] = GREY
        elif kind == TAKE:
            token = min(piles[at], key=lambda t: min(r for r, _ in t))
            top = min(r for r, _ in token)
            tall = max(r for r, _ in token) - top + 1
            for i in range(1, spent + 1):
                for r, c in token:
                    go[r - i * (tall + 1)][c] = gi[r][c]
    return go
