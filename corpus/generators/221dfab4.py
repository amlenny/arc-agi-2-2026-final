# Rule authored from the evaluation demonstrations of 221dfab4.
#
# The KEY is the run of 4s on one edge. It marches straight across the grid in steps of TWO,
# stamping its own shape each time, and the stamp colour cycles Y, Y, G starting from the key
# itself — so every third stamp is green. The lanes it steps over are wiped to background, which
# is why blobs appear to have holes punched through them along one band.
#
# ON A GREEN STAMP THE WHOLE LANE TURNS: every run of blob colour in that row goes green too,
# including runs nowhere near the band. That is what made this look length-driven — demo 0 row 18
# has two separate runs and a gap, and the output is one unbroken green line across all three
# because the stamp fills the gap between them.
#
# The key is horizontal on a top/bottom edge and vertical on a side edge, so the march axis is
# read off the key rather than assumed.
from collections import Counter

GREEN = 3


def transform(grid):
    # THE KEY NAMES ITSELF BY WHERE IT SITS: it is the run on an edge, and it is the only colour
    # that never leaves the border -- 4/4, 3/3, 8/8, 5/5 of its cells on it, against 0 of 172,
    # 4 of 199, 12 of 220 and 0 of 285 for the blobs.
    _H, _W = len(grid), len(grid[0])
    _t = {}
    for _row in grid:
        for _v in _row:
            _t[_v] = _t.get(_v, 0) + 1
    _bg = max(_t, key=lambda k: _t[k])
    KEY = next((v for v in _t if v != _bg
                and all(r in (0, _H - 1) or c in (0, _W - 1)
                        for r in range(_H) for c in range(_W) if grid[r][c] == v)), None)
    if KEY is None:
        return [row[:] for row in grid]
    h, w = len(grid), len(grid[0])
    out = [row[:] for row in grid]
    cnt = Counter(v for row in grid for v in row)
    bg = cnt.most_common(1)[0][0]
    blob = next((v for v in cnt if v not in (bg, KEY)), None)
    keys = [(r, c) for r in range(h) for c in range(w) if grid[r][c] == KEY]
    if not keys or blob is None:
        return out

    kr = sorted({r for r, _ in keys})
    kc = sorted({c for _, c in keys})
    horiz = len(kc) > len(kr)                 # a horizontal key marches up or down

    if horiz:
        line, span = kr[0], kc
        step = 1 if line == 0 else -1
        limit = h
    else:
        line, span = kc[0], kr
        step = 1 if line == 0 else -1
        limit = w

    def put(pos, colour):
        for k in span:
            if horiz:
                out[pos][k] = colour
            else:
                out[k][pos] = colour

    def lane_green(pos):
        """Every run of blob colour in the lane goes green."""
        n = w if horiz else h
        for k in range(n):
            v = grid[pos][k] if horiz else grid[k][pos]
            if v == blob:
                if horiz:
                    out[pos][k] = GREEN
                else:
                    out[k][pos] = GREEN

    i = 1
    while True:
        blank = line + step * (2 * i - 1)
        stamp = line + step * (2 * i)
        if 0 <= blank < limit:
            put(blank, bg)
        if not (0 <= stamp < limit):
            break
        # i % 3 == 2 lands on the third stamp counting the key as the first
        if i % 3 == 2:
            lane_green(stamp)
            put(stamp, GREEN)
        else:
            put(stamp, KEY)
        i += 1
    return out
