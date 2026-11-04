"""b6f77b65 -- knock the marked pieces out and let the scaffold settle.

The colour in the top corner names the pieces to take away.  What is left is a
scaffold of uprights and crossbars.

An upright that stood on something drops until its foot lands on whatever is
left below it; one that stood on nothing was hanging from its bar all
along, and goes wherever that bar goes.  A crossbar
is carried at each end by an upright -- its own where it has one, the
neighbouring one at the other end -- and it rides at the height of the LOWER of
those two tops, sliding along its own upright to get there.  Take an upright
away and the bar it was carrying comes off altogether: it drops, straight past
its own upright, until something is under it.

KNOWN-BAD DEMO: train[1].  Taking pieces away means most pairs LOSE cells --
seven of the eight do -- so nothing here is conserved in general.  What train[1]
alone does is GAIN one.  It is the only pair in the task where any colour comes
out with more cells than it went in: the maroon upright at column 5 finishes one
cell longer, a cell appearing from nowhere at (4,5).  The extra cell is an
error.  This generator keeps every piece the length it was, so it disagrees
with that one cell and nothing else.
"""


def _bodies(gi, bg):
    H, W = len(gi), len(gi[0])
    out = []
    for r in range(1, H):
        for c in range(W):
            hue = gi[r][c]
            if hue == bg:
                continue
            if gi[r - 1][c] != hue and r + 1 < H and gi[r + 1][c] == hue:
                run, k = [], r
                while k < H and gi[k][c] == hue:
                    run.append((k, c))
                    k += 1
                out.append({"hue": hue, "cells": run, "post": True})
            if (c == 0 or gi[r][c - 1] != hue) and c + 1 < W and gi[r][c + 1] == hue:
                run, k = [], c
                while k < W and gi[r][k] == hue:
                    run.append((r, k))
                    k += 1
                out.append({"hue": hue, "cells": run, "post": False})
    return out


def transform(gi):
    H, W = len(gi), len(gi[0])
    tally = {}
    for row in gi:
        for v in row:
            tally[v] = tally.get(v, 0) + 1
    bg = max(tally, key=lambda k: tally[k])      # the board, read off the board
    keys = {gi[0][c] for c in range(W) if gi[0][c] != bg}
    every = _bodies(gi, bg)
    for b in every:
        b["gone"] = b["hue"] in keys
        b["twin"] = None

    def upright(at):
        return next((b for b in every if b["post"] and at in b["cells"]), None)

    live = [b for b in every if not b["gone"]]
    ink = {p for b in every for p in b["cells"]}
    for post in [b for b in live if b["post"]]:
        foot = post["cells"][-1]
        post["hangs"] = foot[0] + 1 < H and (foot[0] + 1, foot[1]) not in ink
        post["drop"] = None
    for bar in [b for b in live if not b["post"]]:
        row, c0, c1 = bar["cells"][0][0], bar["cells"][0][1], bar["cells"][-1][1]
        ends = [upright((row, c0)) or upright((row, c0 - 1)),
                upright((row, c1)) or upright((row, c1 + 1))]
        own = upright((row, c0)) or upright((row, c1))
        bar["loose"] = any(e is None or e["gone"] for e in ends)
        bar["props"] = [] if bar["loose"] else ends
        if own is not None and not own["gone"]:
            bar["twin"] = own
            own["twin"] = bar
            own["drop"] = own["cells"][0][0] - row

    for _ in range(4 * H):
        still = True
        for post in [b for b in live if b["post"] and not b["hangs"]]:
            foot = post["cells"][-1]
            block = {p for o in live if o is not post and o is not post["twin"]
                     for p in o["cells"]}
            if foot[0] + 1 < H and (foot[0] + 1, foot[1]) not in block:
                post["cells"] = [(r + 1, c) for r, c in post["cells"]]
                still = False
        for post in [b for b in live if b["post"] and b["hangs"] and b["twin"]]:
            want = post["twin"]["cells"][0][0] + post["drop"]
            if want != post["cells"][0][0]:
                shift = want - post["cells"][0][0]
                post["cells"] = [(r + shift, c) for r, c in post["cells"]]
                still = False
        for bar in [b for b in live if not b["post"]]:
            row = bar["cells"][0][0]
            if bar["loose"]:
                block = {p for o in live if o is not bar and o is not bar["twin"]
                         for p in o["cells"]}
                if row + 1 < H and not any((row + 1, c) in block for _, c in bar["cells"]):
                    bar["cells"] = [(r + 1, c) for r, c in bar["cells"]]
                    still = False
                continue
            carry = [p for p in bar["props"] if not (p is bar["twin"] and p["hangs"])]
            if not carry:
                continue
            sit = max(p["cells"][0][0] for p in carry)
            if sit != row:
                bar["cells"] = [(sit, c) for _, c in bar["cells"]]
                still = False
        if still:
            break

    go = [[bg] * W for _ in range(H)]
    for c in range(W):
        go[0][c] = gi[0][c]
    for b in live:
        for r, c in b["cells"]:
            go[r][c] = b["hue"]
    return go
