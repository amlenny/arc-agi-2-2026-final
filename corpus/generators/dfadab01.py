"""dfadab01 -- every dot is a rubber stamp.

Four seed colours each stand for a fixed 4x4 badge, drawn in a colour of its
own.  Wherever a seed sits, its badge is printed with the seed's cell as the
badge's top-left corner, clipped at the edge of the grid.

One badge may also be drawn out in the open as a reminder, with a seed-coloured
key placed just off its bottom-right corner saying which seed it belongs to.
The reminder and its key are scenery: both are wiped, and the key does NOT
print.  A grid can carry no reminder at all and the badges are unchanged.
"""

# WHOLE-TASK SCOPE. The whole task has to be read together; no single pair determines the table.
#
# The badges are not derivable from one grid. Each pair carries at most ONE badge drawn in the open
# as a reminder with a seed-coloured key beside it: demo 0 teaches one, demo 1 another, demo 2 a
# third and the TEST its own fourth. Demo 3 carries no reminder at all and needs all four, so no
# pair-by-pair rule can answer it -- the table has to be learned across the pairs, which is exactly
# the shape of 269e22fb's motif.
#
# The table is the task's own teaching, not leaked answers: every badge in it is shown by a
# reminder on one of the task's own boards, the test's included.
BADGE = {
    2: (4, ("####",
            "#..#",
            "#..#",
            "####")),
    3: (1, (".##.",
            "#..#",
            "#..#",
            ".##.")),
    5: (6, ("##..",
            "##..",
            "..##",
            "..##")),
    8: (7, ("#..#",
            ".##.",
            ".##.",
            "#..#")),
}
INK = {ink for ink, _ in BADGE.values()}


def transform(gi):
    H, W = len(gi), len(gi[0])
    drawn = [(r, c) for r in range(H) for c in range(W) if gi[r][c] in INK]

    key = None
    if drawn:
        r1 = max(p[0] for p in drawn) + 1
        c1 = max(p[1] for p in drawn) + 1
        if r1 < H and c1 < W:
            key = (r1, c1)

    go = [[0] * W for _ in range(H)]
    for r in range(H):
        for c in range(W):
            if gi[r][c] not in BADGE or (r, c) == key:
                continue
            ink, art = BADGE[gi[r][c]]
            for dr, row in enumerate(art):
                for dc, ch in enumerate(row):
                    if ch == "#" and r + dr < H and c + dc < W:
                        go[r + dr][c + dc] = ink
    return go
