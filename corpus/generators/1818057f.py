"""1818057f -- find the plus signs in the speckle and light them up.

The board is a noise of two colours.  Wherever the SPARSER of the two happens to
form a plus -- a cell with it directly above, below, left and right -- that plus
turns azure.  Everything else is left exactly as it was.

Which colour that is comes off the board: it is the rarer one in all four pairs
(31 v 89, 99 v 156, 58 v 86, 199 v 285).  Counting plusses does NOT decide it --
in two pairs the other colour forms far more of them, and in the test both form
six.  Azure appears in no input, so it is the colour this rule paints.
"""

LIT = 8


def transform(gi):
    H, W = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    INK = min(tally, key=lambda k: tally[k])
    go = [row[:] for row in gi]
    for r in range(1, H - 1):
        for c in range(1, W - 1):
            arms = [(r, c), (r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
            if all(gi[a][b] == INK for a, b in arms):
                for a, b in arms:
                    go[a][b] = LIT
    return go
