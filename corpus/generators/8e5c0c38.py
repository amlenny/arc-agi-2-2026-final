"""8e5c0c38 -- trim each figure until it stands square with itself.

Every figure is meant to be symmetrical left to right.  Slide a mirror line
across it and find the placing that saves the most cells; every cell whose
reflection is missing is a blemish and gets rubbed out.  The line may fall on a
column or between two columns, and each colour is judged on its own.
"""


def transform(gi):
    H, W = len(gi), len(gi[0])
    flat = [v for row in gi for v in row]
    bg = max(set(flat), key=flat.count)

    go = [row[:] for row in gi]
    for shade in set(flat) - {bg}:
        cells = {(r, c) for r in range(H) for c in range(W) if gi[r][c] == shade}
        lo = min(c for _, c in cells)
        hi = max(c for _, c in cells)
        best = None
        for twice in range(2 * lo, 2 * hi + 1):
            keep = {(r, c) for r, c in cells if (r, twice - c) in cells}
            if best is None or len(keep) > len(best):
                best = keep
        for r, c in cells - best:
            go[r][c] = bg
    return go
