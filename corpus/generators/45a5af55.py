"""45a5af55 -- the stack of stripes is really a set of nested frames.

Read the board top to bottom as a stack of coloured stripes.  The first stripe
is the outermost frame, the next sits inside it, and so on; each keeps its own
thickness.  The last stripe is not a frame at all -- it is the block in the
middle, so the finished square is two of every stripe but that one.
"""


def transform(gi):
    bands = []
    for row in gi:
        if bands and bands[-1][0] == row[0]:
            bands[-1][1] += 1
        else:
            bands.append([row[0], 1])

    side = 2 * sum(t for _, t in bands[:-1]) + bands[-1][1]
    depth = []
    for ink, t in bands:
        depth += [ink] * t
    return [[depth[min(r, c, side - 1 - r, side - 1 - c)] for c in range(side)]
            for r in range(side)]
