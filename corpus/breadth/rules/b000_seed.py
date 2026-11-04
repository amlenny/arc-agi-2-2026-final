# b000_seed.py -- seed batch proving the harness: ten rules of different kinds.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


def _scene(rng, k_lo=2, k_hi=5, n_lo=3, n_hi=8, lo=6, hi=18, margin=1):
    h, w = size(rng, lo, hi); g = blank(h, w)
    k = rng.randint(k_lo, k_hi)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    cols = [rng.choice(COLOURS) for _ in range(k)]
    if place_shapes(rng, g, shapes, cols, margin=margin) is None:
        return None
    return g


# 1 gravity: every non-background cell falls straight down.
def gi_gravity(rng):
    h, w = size(rng, 5, 15); g = blank(h, w)
    for _ in range(rng.randint(3, h * w // 3)):
        g[rng.randrange(h)][rng.randrange(w)] = rng.choice(COLOURS)
    return g
def tf_gravity(g):
    h, w = dims(g); out = blank(h, w)
    for c in range(w):
        col = [g[r][c] for r in range(h) if g[r][c] != 0]
        for i, v in enumerate(reversed(col)):
            out[h - 1 - i][c] = v
    return out
rule("gravity_down", "Every coloured cell falls straight down until it rests on the floor or another cell.", gi_gravity, tf_gravity)


# 2 largest object recoloured to the colour of the smallest.
def gi_largest(rng):
    g = _scene(rng, 3, 5, 2, 9)
    if g is None: return None
    sizes = sorted(len(o) for o in objects(g, 0))
    return g if sizes[-1] != sizes[-2] and sizes[0] != sizes[1] else None
def tf_largest(g):
    obs = objects(g, 0); big = max(obs, key=len); small = min(obs, key=len)
    out = copy(g); col = g[small[0][0]][small[0][1]]
    for r, c in big: out[r][c] = col
    return out
rule("largest_takes_smallest_colour", "The largest object is recoloured with the colour of the smallest object.", gi_largest, tf_largest)


# 3 count objects -> horizontal bar of that length.
def gi_count(rng):
    return _scene(rng, 1, 8, 1, 4, 6, 16)
def tf_count(g):
    n = len(objects(g, 0))
    return [[g[o[0][0]][o[0][1]] for o in sorted(objects(g, 0), key=lambda o: (o[0][1], o[0][0]))]] if n else None
rule("objects_to_colour_row", "Output one row listing each object's colour, ordered left to right by object position.", gi_count, tf_count)


# 4 mirror completion: the right half is the mirror of the left; input has the right half blank.
def gi_mirror(rng):
    h, w = rng.randint(4, 14), rng.randint(2, 7); left = blank(h, w)
    for _ in range(rng.randint(h, h * w // 2 + h)):
        left[rng.randrange(h)][rng.randrange(w)] = rng.choice(COLOURS)
    return [row + [0] * w for row in left]
def tf_mirror(g):
    w = len(g[0]) // 2
    return [row[:w] + row[:w][::-1] for row in g]
rule("mirror_left_to_right", "The empty right half is filled with the mirror image of the left half.", gi_mirror, tf_mirror)


# 5 connect same-colour pairs on a row or column with a line of that colour.
def gi_connect(rng):
    h, w = size(rng, 7, 18); g = blank(h, w); cols = colours(rng, rng.randint(1, 4)); used = set()
    for col in cols:
        for _ in range(30):
            if rng.random() < 0.5:
                r = rng.randrange(h); a, b = sorted(rng.sample(range(w), 2))
                seg = {(r, x) for x in range(a, b + 1)}
            else:
                c = rng.randrange(w); a, b = sorted(rng.sample(range(h), 2))
                seg = {(y, c) for y in range(a, b + 1)}
            if len(seg) >= 3 and not (seg & used):
                used |= seg; ends = sorted(seg); g[ends[0][0]][ends[0][1]] = col; g[ends[-1][0]][ends[-1][1]] = col
                break
    return g
def tf_connect(g):
    out = copy(g); h, w = dims(g)
    for col in set(v for row in g for v in row if v):
        pts = cells(g, lambda v: v == col)
        if len(pts) != 2: continue
        (r1, c1), (r2, c2) = pts
        if r1 == r2:
            for x in range(min(c1, c2), max(c1, c2) + 1): out[r1][x] = col
        elif c1 == c2:
            for y in range(min(r1, r2), max(r1, r2) + 1): out[y][c1] = col
    return out
rule("connect_same_colour_pairs", "Two cells of the same colour on one row or column are joined by a straight line of that colour.", gi_connect, tf_connect)


# 6 tile the input 2x2 with alternating flips.
def gi_tile(rng):
    h, w = size(rng, 2, 6); g = blank(h, w)
    for _ in range(rng.randint(2, h * w)):
        g[rng.randrange(h)][rng.randrange(w)] = rng.choice(COLOURS)
    return g if any(v for row in g for v in row) else None
def tf_tile(g):
    top = [row + row[::-1] for row in g]
    return top + top[::-1]
rule("tile_2x2_mirrored", "The grid is tiled two by two, each copy mirrored so the whole is symmetric.", gi_tile, tf_tile)


# 7 crop to the object with a unique colour.
def gi_cropuniq(rng):
    h, w = size(rng, 8, 20); g = blank(h, w); k = rng.randint(3, 6)
    uniq, shared = colours(rng, 2)
    shapes = [random_shape(rng, rng.randint(3, 8)) for _ in range(k)]
    cols = [uniq] + [shared] * (k - 1)
    if place_shapes(rng, g, shapes, cols, margin=1) is None: return None
    return g if len(objects(g, 0)) == k else None
def tf_cropuniq(g):
    obs = objects(g, 0); cnt = {}
    for o in obs:
        col = g[o[0][0]][o[0][1]]; cnt[col] = cnt.get(col, 0) + 1
    o = next(o for o in obs if cnt[g[o[0][0]][o[0][1]]] == 1)
    return crop(g, *bbox(o))
rule("crop_unique_colour_object", "Output the bounding box of the one object whose colour appears on no other object.", gi_cropuniq, tf_cropuniq)


# 8 fill enclosed rectangles' interiors with a fixed colour keyed by a corner marker cell.
def gi_frames(rng):
    h, w = size(rng, 8, 20); g = blank(h, w); key = rng.choice(COLOURS); g[0][0] = key
    wall = rng.choice([c for c in COLOURS if c != key]); n = 0
    for _ in range(40):
        r0, c0 = rng.randint(1, h - 4), rng.randint(1, w - 4); r1, c1 = rng.randint(r0 + 2, min(h - 1, r0 + 7)), rng.randint(c0 + 2, min(w - 1, c0 + 7))
        if all(g[r][c] == 0 for r in range(r0 - 1, r1 + 2) for c in range(c0 - 1, c1 + 2) if 0 <= r < h and 0 <= c < w):
            rect(g, r0, c0, r1, c1, wall, fill=False); n += 1
        if n >= rng.randint(1, 3): break
    return g if n else None
def tf_frames(g):
    out = copy(g); key = g[0][0]; h, w = dims(g)
    for o in components(g, lambda v: v != 0 and v != key, conn8=False):
        r0, c0, r1, c1 = bbox(o)
        if len(o) == 2 * (r1 - r0 + c1 - c0) and r1 - r0 >= 2 and c1 - c0 >= 2:
            rect(out, r0 + 1, c0 + 1, r1 - 1, c1 - 1, key)
    return out
rule("fill_frames_with_corner_key", "Every hollow rectangle is filled inside with the colour of the marker in the top-left corner.", gi_frames, tf_frames)


# 9 sort columns by their height (bars) ascending.
def gi_bars(rng):
    h, w = rng.randint(4, 12), rng.randint(3, 10); col = rng.choice(COLOURS); g = blank(h, w)
    hs = [rng.randint(0, h) for _ in range(w)]
    for c, k in enumerate(hs):
        for r in range(h - k, h): g[r][c] = col
    return g if len(set(hs)) > 1 else None
def tf_bars(g):
    h, w = dims(g); hs = sorted(sum(1 for r in range(h) if g[r][c]) for c in range(w)); col = max(v for row in g for v in row)
    out = blank(h, w)
    for c, k in enumerate(hs):
        for r in range(h - k, h): out[r][c] = col
    return out
rule("sort_bars_ascending", "The vertical bars are reordered from shortest on the left to tallest on the right.", gi_bars, tf_bars)


# 10 two-step: move every object to touch the top edge, then recolour by column parity.
def gi_lift(rng):
    return _scene(rng, 2, 5, 2, 6, 7, 16, margin=1)
def tf_lift(g):
    h, w = dims(g); out = blank(h, w); a, b = 1, 2
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o)
        for r, c in o:
            out[r - r0][c] = a if c0 % 2 == 0 else b
    return out
rule("lift_to_top_recolour_parity", "Every object slides up to the top edge and is recoloured 1 if its left edge is in an even column, 2 if odd.", gi_lift, tf_lift)
