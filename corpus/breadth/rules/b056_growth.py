# b056_growth.py -- directed growth and sprouting: 40 rules. Every rule states the growth direction,
# the amount, and the stop condition in its one-sentence description.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


def _big(rng, lo=7, hi=16, p=0.4, blo=21, bhi=30):
    if rng.random() < p:
        return rng.randint(blo, bhi), rng.randint(blo, bhi)
    return rng.randint(lo, hi), rng.randint(lo, hi)


# 1 rectangle grows by 1 cell at each end of its LONGER axis.
def gi_1(rng):
    h, w = _big(rng, 8, 18)
    rh = rng.randint(2, max(2, min(6, h - 4)))
    rw = rng.randint(2, max(2, min(6, w - 4)))
    if rh == rw:
        return None
    r0 = rng.randint(2, h - 2 - rh)
    c0 = rng.randint(2, w - 2 - rw)
    g = blank(h, w)
    rect(g, r0, c0, r0 + rh - 1, c0 + rw - 1, rng.choice(COLOURS))
    return g
def tf_1(g):
    h, w = dims(g)
    obs = objects(g, 0)
    if len(obs) != 1:
        return None
    o = obs[0]
    r0, c0, r1, c1 = bbox(o)
    col = g[o[0][0]][o[0][1]]
    out = copy(g)
    if (r1 - r0) > (c1 - c0):
        for c in range(c0, c1 + 1):
            out[r0 - 1][c] = col
            out[r1 + 1][c] = col
    else:
        for r in range(r0, r1 + 1):
            out[r][c0 - 1] = col
            out[r][c1 + 1] = col
    return out
rule("grow_rect_long_axis_both_ends", "The rectangle grows by one cell at each end of its longer axis (ties rejected), extending until that single row or pair of rows is added.", gi_1, tf_1)


# 2 rectangle grows by 1 cell at each end of its SHORTER axis.
def tf_2(g):
    h, w = dims(g)
    obs = objects(g, 0)
    if len(obs) != 1:
        return None
    o = obs[0]
    r0, c0, r1, c1 = bbox(o)
    col = g[o[0][0]][o[0][1]]
    out = copy(g)
    if (r1 - r0) < (c1 - c0):
        for c in range(c0, c1 + 1):
            out[r0 - 1][c] = col
            out[r1 + 1][c] = col
    else:
        for r in range(r0, r1 + 1):
            out[r][c0 - 1] = col
            out[r][c1 + 1] = col
    return out
rule("grow_rect_short_axis_both_ends", "The rectangle grows by one cell at each end of its shorter axis (ties rejected), extending a single row or column on each side.", gi_1, tf_2)


# 3 rectangle grows toward the nearest wall until it touches it (tie-break top>bottom>left>right, rejected).
def gi_3(rng):
    h, w = _big(rng, 9, 18)
    rh = rng.randint(2, max(2, min(6, h - 4)))
    rw = rng.randint(2, max(2, min(6, w - 4)))
    r0 = rng.randint(1, h - 2 - rh)
    c0 = rng.randint(1, w - 2 - rw)
    g = blank(h, w)
    rect(g, r0, c0, r0 + rh - 1, c0 + rw - 1, rng.choice(COLOURS))
    dT, dB, dL, dR = r0, h - 1 - (r0 + rh - 1), c0, w - 1 - (c0 + rw - 1)
    ds = [dT, dB, dL, dR]
    if len(set(ds)) != 4:
        return None
    return g
def tf_3(g):
    h, w = dims(g)
    obs = objects(g, 0)
    o = obs[0]
    r0, c0, r1, c1 = bbox(o)
    col = g[o[0][0]][o[0][1]]
    dT, dB, dL, dR = r0, h - 1 - r1, c0, w - 1 - c1
    out = copy(g)
    m = min(dT, dB, dL, dR)
    if m == dT:
        rect(out, 0, c0, r0 - 1, c1, col)
    elif m == dB:
        rect(out, r1 + 1, c0, h - 1, c1, col)
    elif m == dL:
        rect(out, r0, 0, r1, c0 - 1, col)
    else:
        rect(out, r0, c1 + 1, r1, w - 1, col)
    return out
rule("grow_rect_toward_nearest_wall_until_touch", "The rectangle grows toward whichever of the four walls it is currently closest to (distances must be all distinct), extending straight across until it touches that wall.", gi_3, tf_3)


# 4 rectangle grows toward the wall marked by a single grey cell sitting on that wall's edge row/column.
def gi_4(rng):
    h, w = _big(rng, 9, 18)
    rh = rng.randint(2, max(2, min(6, h - 6)))
    rw = rng.randint(2, max(2, min(6, w - 6)))
    r0 = rng.randint(2, h - 3 - rh)
    c0 = rng.randint(2, w - 3 - rw)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    rect(g, r0, c0, r0 + rh - 1, c0 + rw - 1, col)
    side = rng.choice(["top", "bottom", "left", "right"])
    if side == "top":
        g[0][rng.randrange(c0, c0 + rw)] = 5
    elif side == "bottom":
        g[h - 1][rng.randrange(c0, c0 + rw)] = 5
    elif side == "left":
        g[rng.randrange(r0, r0 + rh)][0] = 5
    else:
        g[rng.randrange(r0, r0 + rh)][w - 1] = 5
    return g
def tf_4(g):
    h, w = dims(g)
    obs = objects(g, 0)
    rectobj = max(obs, key=len)
    marker = min(obs, key=len)
    r0, c0, r1, c1 = bbox(rectobj)
    col = g[rectobj[0][0]][rectobj[0][1]]
    mr, mc = marker[0]
    out = copy(g)
    if mr == 0:
        rect(out, 0, c0, r0 - 1, c1, col)
    elif mr == h - 1:
        rect(out, r1 + 1, c0, h - 1, c1, col)
    elif mc == 0:
        rect(out, r0, 0, r1, c0 - 1, col)
    else:
        rect(out, r0, c1 + 1, r1, w - 1, col)
    return out
rule("grow_rect_toward_marker_wall_side", "A single grey cell sits on one of the four walls; the rectangle grows straight toward that wall, overwriting the marker, until it touches the edge.", gi_4, tf_4)


# 5 seed sprouts a plus of arm length equal to its own colour value (digits).
def gi_5(rng):
    c = rng.randint(1, 9)
    lo = 2 * c + 3
    h, w = _big(rng, max(lo, 9), max(lo + 6, 18), blo=max(lo, 21))
    g = blank(h, w)
    r = rng.randint(c, h - 1 - c)
    cc = rng.randint(c, w - 1 - c)
    g[r][cc] = c
    return g
def tf_5(g):
    h, w = dims(g)
    r, cc = cells(g, lambda v: v != 0)[0]
    c = g[r][cc]
    out = copy(g)
    for k in range(1, c + 1):
        out[r - k][cc] = c
        out[r + k][cc] = c
        out[r][cc - k] = c
        out[r][cc + k] = c
    return out
rule("seed_sprout_plus_length_digit", "The seed cell sprouts a plus sign; each of the four arms grows outward by exactly as many cells as the seed's own colour value, then stops.", gi_5, tf_5, digits=True)


# 6 seed sprouts only a vertical arm, length = colour value.
def gi_6(rng):
    c = rng.randint(1, 9)
    lo = 2 * c + 3
    h, w = _big(rng, max(lo, 9), max(lo + 4, 18), blo=max(lo, 21))
    g = blank(h, w)
    r = rng.randint(c, h - 1 - c)
    cc = rng.randint(1, w - 2)
    g[r][cc] = c
    return g
def tf_6(g):
    r, cc = cells(g, lambda v: v != 0)[0]
    c = g[r][cc]
    out = copy(g)
    for k in range(1, c + 1):
        out[r - k][cc] = c
        out[r + k][cc] = c
    return out
rule("seed_sprout_vertical_arm_length_digit", "The seed cell grows a vertical arm upward and downward, each side extending by as many cells as the seed's colour value, then stopping.", gi_6, tf_6, digits=True)


# 7 seed sprouts only a horizontal arm, length = colour value.
def gi_7(rng):
    c = rng.randint(1, 9)
    lo = 2 * c + 3
    h, w = _big(rng, max(lo, 9), max(lo + 4, 18), blo=max(lo, 21))
    g = blank(h, w)
    r = rng.randint(1, h - 2)
    cc = rng.randint(c, w - 1 - c)
    g[r][cc] = c
    return g
def tf_7(g):
    r, cc = cells(g, lambda v: v != 0)[0]
    c = g[r][cc]
    out = copy(g)
    for k in range(1, c + 1):
        out[r][cc - k] = c
        out[r][cc + k] = c
    return out
rule("seed_sprout_horizontal_arm_length_digit", "The seed cell grows a horizontal arm leftward and rightward, each side extending by as many cells as the seed's colour value, then stopping.", gi_7, tf_7, digits=True)


# 8 seed sprouts a diagonal X, each of 4 diagonal arms length = colour value.
def gi_8(rng):
    c = rng.randint(1, 9)
    lo = 2 * c + 3
    h, w = _big(rng, max(lo, 9), max(lo + 4, 18), blo=max(lo, 21))
    g = blank(h, w)
    r = rng.randint(c, h - 1 - c)
    cc = rng.randint(c, w - 1 - c)
    g[r][cc] = c
    return g
def tf_8(g):
    r, cc = cells(g, lambda v: v != 0)[0]
    c = g[r][cc]
    out = copy(g)
    for k in range(1, c + 1):
        out[r - k][cc - k] = c
        out[r - k][cc + k] = c
        out[r + k][cc - k] = c
        out[r + k][cc + k] = c
    return out
rule("seed_sprout_diagonal_x_length_digit", "The seed cell grows an X of four diagonal arms, each extending by as many cells as the seed's colour value, then stopping.", gi_8, tf_8, digits=True)


# --- helper: hollow rectangular frame with an object inside ---
def _framed(rng, h, w, pad=3):
    fr0, fc0 = rng.randint(1, 3), rng.randint(1, 3)
    fr1, fc1 = h - 1 - rng.randint(1, 3), w - 1 - rng.randint(1, 3)
    if fr1 - fr0 < pad * 2 or fc1 - fc0 < pad * 2:
        return None
    fcol = 5
    g = blank(h, w)
    rect(g, fr0, fc0, fr1, fc1, fcol, fill=False)
    return g, fr0, fc0, fr1, fc1


# 9 object inside a grey frame grows vertically (both ends) until it touches the frame.
def gi_9(rng):
    h, w = _big(rng, 14, 22)
    fr = _framed(rng, h, w)
    if fr is None:
        return None
    g, fr0, fc0, fr1, fc1 = fr
    rh = rng.randint(1, 2)
    rw = rng.randint(2, max(2, min(5, fc1 - fc0 - 2)))
    r0 = rng.randint(fr0 + 2, fr1 - 2 - rh)
    c0 = rng.randint(fc0 + 1, fc1 - 1 - rw)
    rect(g, r0, c0, r0 + rh - 1, c0 + rw - 1, rng.choice([c for c in COLOURS if c != 5]))
    return g
def tf_9(g):
    h, w = dims(g)
    frame = next(o for o in objects(g, 0) if g[o[0][0]][o[0][1]] == 5)
    fr0, fc0, fr1, fc1 = bbox(frame)
    obj = next(o for o in objects(g, 0) if g[o[0][0]][o[0][1]] != 5)
    r0, c0, r1, c1 = bbox(obj)
    col = g[obj[0][0]][obj[0][1]]
    out = copy(g)
    rect(out, fr0 + 1, c0, r0 - 1, c1, col)
    rect(out, r1 + 1, c0, fr1 - 1, c1, col)
    return out
rule("object_grows_vertically_until_frame", "Inside a grey rectangular frame, the small object grows straight up and straight down until each side touches the frame's inner wall.", gi_9, tf_9)


# 10 object inside a grey frame grows horizontally (both ends) until it touches the frame.
def gi_10(rng):
    h, w = _big(rng, 14, 22)
    fr = _framed(rng, h, w)
    if fr is None:
        return None
    g, fr0, fc0, fr1, fc1 = fr
    rw = rng.randint(1, 2)
    rh = rng.randint(2, max(2, min(5, fr1 - fr0 - 2)))
    c0 = rng.randint(fc0 + 2, fc1 - 2 - rw)
    r0 = rng.randint(fr0 + 1, fr1 - 1 - rh)
    rect(g, r0, c0, r0 + rh - 1, c0 + rw - 1, rng.choice([c for c in COLOURS if c != 5]))
    return g
def tf_10(g):
    h, w = dims(g)
    frame = next(o for o in objects(g, 0) if g[o[0][0]][o[0][1]] == 5)
    fr0, fc0, fr1, fc1 = bbox(frame)
    obj = next(o for o in objects(g, 0) if g[o[0][0]][o[0][1]] != 5)
    r0, c0, r1, c1 = bbox(obj)
    col = g[obj[0][0]][obj[0][1]]
    out = copy(g)
    rect(out, r0, fc0 + 1, r1, c0 - 1, col)
    rect(out, r0, c1 + 1, r1, fc1 - 1, col)
    return out
rule("object_grows_horizontally_until_frame", "Inside a grey rectangular frame, the small object grows straight left and straight right until each side touches the frame's inner wall.", gi_10, tf_10)


# 11 objects left of centre column grow 2 cells rightward, objects right of centre grow 2 cells leftward.
def gi_11(rng):
    h, w = _big(rng, 12, 22)
    mid = w // 2
    g = blank(h, w)
    rh = rng.randint(2, 4)
    r0a = rng.randint(1, h - 1 - rh)
    c0a = rng.randint(1, mid - 6)
    r0b = rng.randint(1, h - 1 - rh)
    c0b = rng.randint(mid + 4, w - 4)
    if c0a + 2 >= mid - 2 or c0b - 2 <= mid + 2:
        return None
    cols = colours(rng, 2)
    rect(g, r0a, c0a, r0a + rh - 1, c0a + 1, cols[0])
    rect(g, r0b, c0b, r0b + rh - 1, c0b + 1, cols[1])
    return g
def tf_11(g):
    h, w = dims(g)
    mid = w // 2
    out = copy(g)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o)
        col = g[o[0][0]][o[0][1]]
        if c1 < mid:
            rect(out, r0, c1 + 1, r1, c1 + 2, col)
        else:
            rect(out, r0, c0 - 2, r1, c0 - 1, col)
    return out
rule("grow_left_objects_right_two_cells", "Every object left of the grid's centre column grows two cells to the right, and every object right of centre grows two cells to the left.", gi_11, tf_11)


# 12 objects above centre row grow 2 cells downward, objects below centre grow 2 cells upward.
def gi_12(rng):
    h, w = _big(rng, 12, 22)
    mid = h // 2
    g = blank(h, w)
    rw = rng.randint(2, 4)
    c0a = rng.randint(1, w - 1 - rw)
    r0a = rng.randint(1, mid - 6)
    c0b = rng.randint(1, w - 1 - rw)
    r0b = rng.randint(mid + 4, h - 4)
    if r0a + 2 >= mid - 2 or r0b - 2 <= mid + 2:
        return None
    cols = colours(rng, 2)
    rect(g, r0a, c0a, r0a + 1, c0a + rw - 1, cols[0])
    rect(g, r0b, c0b, r0b + 1, c0b + rw - 1, cols[1])
    return g
def tf_12(g):
    h, w = dims(g)
    mid = h // 2
    out = copy(g)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o)
        col = g[o[0][0]][o[0][1]]
        if r1 < mid:
            rect(out, r1 + 1, c0, r1 + 2, c1, col)
        else:
            rect(out, r0 - 2, c0, r0 - 1, c1, col)
    return out
rule("grow_top_objects_down_two_cells", "Every object above the grid's centre row grows two cells downward, and every object below centre grows two cells upward.", gi_12, tf_12)


# 13 horizontal bar grows rightward by the number of loose dots sharing its colour.
def gi_13(rng):
    h, w = _big(rng, 10, 20)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    r = rng.randint(1, h - 2)
    c0 = rng.randint(1, 4)
    blen = rng.randint(1, 3)
    rect(g, r, c0, r, c0 + blen - 1, col)
    k = rng.randint(1, min(5, w - (c0 + blen) - 2))
    free = [(rr, cc) for rr in range(h) for cc in range(c0 + blen + 2, w) if g[rr][cc] == 0]
    if len(free) < k:
        return None
    for rr, cc in rng.sample(free, k):
        g[rr][cc] = col
    return g
def tf_13(g):
    h, w = dims(g)
    obs = objects(g, 0)
    bar = max(obs, key=len)
    col = g[bar[0][0]][bar[0][1]]
    k = sum(1 for o in obs if len(o) == 1 and g[o[0][0]][o[0][1]] == col)
    r0, c0, r1, c1 = bbox(bar)
    out = copy(g)
    rect(out, r0, c1 + 1, r1, c1 + k, col)
    return out
rule("bar_grows_right_by_same_colour_dot_count", "The bar grows rightward by as many cells as there are loose single-cell dots of its own colour on the grid, then stops.", gi_13, tf_13)


# 14 vertical bar grows downward by the TOTAL count of loose dots (any colour).
def gi_14(rng):
    h, w = _big(rng, 10, 20)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    c = rng.randint(1, w - 2)
    r0 = rng.randint(1, 3)
    blen = rng.randint(1, 3)
    rect(g, r0, c, r0 + blen - 1, c, col)
    k = rng.randint(1, min(5, h - (r0 + blen) - 2))
    free = [(rr, cc) for rr in range(r0 + blen + 2, h) for cc in range(w) if g[rr][cc] == 0]
    if len(free) < k:
        return None
    others = [x for x in COLOURS if x != col]
    for rr, cc in rng.sample(free, k):
        g[rr][cc] = rng.choice(others)
    return g
def tf_14(g):
    h, w = dims(g)
    obs = objects(g, 0)
    bar = max(obs, key=len)
    col = g[bar[0][0]][bar[0][1]]
    k = sum(1 for o in obs if len(o) == 1)
    r0, c0, r1, c1 = bbox(bar)
    out = copy(g)
    rect(out, r1 + 1, c0, r1 + k, c0, col)
    return out
rule("bar_grows_down_by_total_dot_count", "The vertical bar grows downward by as many cells as the total number of loose single-cell dots anywhere on the grid, regardless of their colour, then stops.", gi_14, tf_14)


# 15 a hollow rectangle frame fills inward by k rings, k given by a lone digit marker.
def gi_15(rng):
    h, w = _big(rng, 12, 22)
    g = blank(h, w)
    col = rng.choice([c for c in COLOURS if c != 5])
    rh = rng.randint(8, min(14, h - 2))
    rw = rng.randint(8, min(14, w - 2))
    r0 = rng.randint(1, h - 1 - rh)
    c0 = rng.randint(1, w - 1 - rw)
    rect(g, r0, c0, r0 + rh - 1, c0 + rw - 1, col, fill=False)
    maxring = (min(rh, rw) - 1) // 2
    if maxring < 2:
        return None
    k = rng.randint(2, maxring + 1)
    spots = [(rr, cc) for rr in range(h) for cc in range(w)
             if not (r0 - 1 <= rr <= r0 + rh and c0 - 1 <= cc <= c0 + rw) and g[rr][cc] == 0]
    if not spots:
        return None
    mr, mc = rng.choice(spots)
    g[mr][mc] = k
    return g
def tf_15(g):
    obs = objects(g, 0)
    marker = next(o for o in obs if len(o) == 1)
    frame = next(o for o in obs if len(o) != 1)
    k = g[marker[0][0]][marker[0][1]]
    col = g[frame[0][0]][frame[0][1]]
    r0, c0, r1, c1 = bbox(frame)
    out = copy(g)
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if min(r - r0, r1 - r, c - c0, c1 - c) < k:
                out[r][c] = col
    return out
rule("blob_frame_fills_rings_by_marker_digit", "A hollow rectangle fills inward, ring by ring from its border, for as many rings as the colour value of the single marker cell elsewhere on the grid says, then stops.", gi_15, tf_15, digits=True)


# 16 a hollow rectangle frame always fills inward by exactly two rings (fixed amount, no marker).
def gi_16(rng):
    h, w = _big(rng, 12, 22)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    rh = rng.randint(7, min(14, h - 2))
    rw = rng.randint(7, min(14, w - 2))
    r0 = rng.randint(1, h - 1 - rh)
    c0 = rng.randint(1, w - 1 - rw)
    rect(g, r0, c0, r0 + rh - 1, c0 + rw - 1, col, fill=False)
    if (min(rh, rw) - 1) // 2 < 2:
        return None
    return g
def tf_16(g):
    obs = objects(g, 0)
    frame = obs[0]
    col = g[frame[0][0]][frame[0][1]]
    r0, c0, r1, c1 = bbox(frame)
    out = copy(g)
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if min(r - r0, r1 - r, c - c0, c1 - c) < 2:
                out[r][c] = col
    return out
rule("blob_frame_fills_fixed_two_rings", "A hollow rectangle always fills inward from its border by exactly two rings, regardless of its size, then stops.", gi_16, tf_16)


# 17 a short diagonal line crystal grows by 1 cell at each end, continuing the same diagonal direction.
def gi_17(rng):
    h, w = _big(rng, 10, 20)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    L = rng.randint(2, 4)
    dr = rng.choice([-1, 1])
    dc = rng.choice([-1, 1])
    r0 = rng.randint(L + 1, h - 2 - L)
    c0 = rng.randint(L + 1, w - 2 - L)
    for k in range(L):
        g[r0 + k * dr][c0 + k * dc] = col
    return g
def tf_17(g):
    pts = cells(g, lambda v: v != 0)
    col = g[pts[0][0]][pts[0][1]]
    pts.sort()
    r0, c0 = pts[0]
    r1, c1 = pts[-1]
    dr = 1 if r1 > r0 else -1
    dc = 1 if c1 > c0 else -1
    out = copy(g)
    out[r0 - dr][c0 - dc] = col
    out[r1 + dr][c1 + dc] = col
    return out
rule("crystal_grows_diagonal_both_ends", "The diagonal line crystal grows by one cell at each end, continuing in the same diagonal direction the line already runs, then stops.", gi_17, tf_17)


# 18 a seed cell grows a diagonal crystal toward the bottom-right corner until it hits the bottom or right wall.
def gi_18(rng):
    h, w = _big(rng, 9, 18)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    r = rng.randint(1, h - 4)
    c = rng.randint(1, w - 4)
    g[r][c] = col
    return g
def tf_18(g):
    h, w = dims(g)
    r, c = cells(g, lambda v: v != 0)[0]
    col = g[r][c]
    out = copy(g)
    rr, cc = r, c
    while rr < h - 1 and cc < w - 1:
        rr += 1
        cc += 1
        out[rr][cc] = col
    return out
rule("crystal_grows_diagonal_to_bottom_right_wall", "The seed cell grows a diagonal line down and to the right, one cell per step, stopping the instant it reaches the bottom or the right wall.", gi_18, tf_18)


# 19 trunk grows straight up from a seed at the bottom; at every grey cell in its column it sprouts a branch.
def gi_19(rng):
    h, w = _big(rng, 12, 22)
    g = blank(h, w)
    col = rng.choice([c for c in COLOURS if c != 5])
    c0 = rng.randint(3, w - 4)
    g[h - 1][c0] = col
    rows = rng.sample(range(2, h - 2), rng.randint(1, 3))
    for rr in rows:
        g[rr][c0] = 5
    return g
def tf_19(g):
    h, w = dims(g)
    seed = cells(g, lambda v: v != 0 and v != 5)[0]
    col = g[seed[0]][seed[1]]
    c0 = seed[1]
    branch_rows = [r for r in range(h) if g[r][c0] == 5]
    out = copy(g)
    for r in range(h):
        out[r][c0] = col
    for r in branch_rows:
        for k in (1, 2):
            if c0 - k >= 0:
                out[r][c0 - k] = col
            if c0 + k < w:
                out[r][c0 + k] = col
    return out
rule("trunk_grows_up_branches_at_grey", "The trunk grows straight up from its seed at the bottom edge to the top edge, and at every grey cell in its column it sprouts a branch two cells long on each side.", gi_19, tf_19)


# 20 roots grow straight down from a seed at the top; branches at grey cells, mirror of rule 19.
def gi_20(rng):
    h, w = _big(rng, 12, 22)
    g = blank(h, w)
    col = rng.choice([c for c in COLOURS if c != 5])
    c0 = rng.randint(3, w - 4)
    g[0][c0] = col
    rows = rng.sample(range(2, h - 2), rng.randint(1, 3))
    for rr in rows:
        g[rr][c0] = 5
    return g
def tf_20(g):
    h, w = dims(g)
    seed = cells(g, lambda v: v != 0 and v != 5)[0]
    col = g[seed[0]][seed[1]]
    c0 = seed[1]
    branch_rows = [r for r in range(h) if g[r][c0] == 5]
    out = copy(g)
    for r in range(h):
        out[r][c0] = col
    for r in branch_rows:
        for k in (1, 2):
            if c0 - k >= 0:
                out[r][c0 - k] = col
            if c0 + k < w:
                out[r][c0 + k] = col
    return out
# roots_grow_down_branches_at_grey dropped 2026-10-12 (review 2: behavioural duplicate of trunk_grows_up_branches_at_grey)
# 21 vine grows along a row of grey dots, recolouring every dot in that row to the seed's colour.
def gi_21(rng):
    h, w = _big(rng, 9, 20)
    g = blank(h, w)
    col = rng.choice([c for c in COLOURS if c != 5])
    r = rng.randint(1, h - 2)
    g[r][0] = col
    k = rng.randint(2, min(6, w - 2))
    cols_ = sorted(rng.sample(range(2, w), k))
    for c in cols_:
        g[r][c] = 5
    return g
def tf_21(g):
    h, w = dims(g)
    out = copy(g)
    for r in range(h):
        seed_cols = [c for c in range(w) if g[r][c] != 0 and g[r][c] != 5]
        if len(seed_cols) == 1 and any(g[r][c] == 5 for c in range(w)):
            col = g[r][seed_cols[0]]
            for c in range(w):
                if g[r][c] == 5:
                    out[r][c] = col
    return out
rule("vine_follows_dotted_guide_row", "The vine grows along the row from its seed, recolouring every grey dot in that same row to the seed's colour, then stops at the last dot.", gi_21, tf_21)


# 22 vine grows along a column of grey dots, column version of rule 21.
def gi_22(rng):
    h, w = _big(rng, 9, 20)
    g = blank(h, w)
    col = rng.choice([c for c in COLOURS if c != 5])
    c = rng.randint(1, w - 2)
    g[0][c] = col
    k = rng.randint(2, min(6, h - 2))
    rows_ = sorted(rng.sample(range(2, h), k))
    for r in rows_:
        g[r][c] = 5
    return g
def tf_22(g):
    h, w = dims(g)
    out = copy(g)
    for c in range(w):
        seed_rows = [r for r in range(h) if g[r][c] != 0 and g[r][c] != 5]
        if len(seed_rows) == 1 and any(g[r][c] == 5 for r in range(h)):
            col = g[seed_rows[0]][c]
            for r in range(h):
                if g[r][c] == 5:
                    out[r][c] = col
    return out
rule("vine_follows_dotted_guide_column", "The vine grows along the column from its seed, recolouring every grey dot in that same column to the seed's colour, then stops at the last dot.", gi_22, tf_22)


# 23 two seeds on the same row grow toward each other one cell at a time until they meet at the midpoint.
def gi_23(rng):
    h, w = _big(rng, 9, 20)
    g = blank(h, w)
    r = rng.randint(0, h - 1)
    c1, c2 = sorted(rng.sample(range(w), 2))
    if c2 - c1 < 3:
        return None
    cols = colours(rng, 2)
    g[r][c1] = cols[0]
    g[r][c2] = cols[1]
    return g
def tf_23(g):
    r = cells(g, lambda v: v != 0)[0][0]
    pts = [(rr, c) for rr, c in cells(g, lambda v: v != 0) if rr == r]
    (r1, c1), (r2, c2) = sorted(pts, key=lambda p: p[1])
    colA, colB = g[r1][c1], g[r2][c2]
    gap = c2 - c1 - 1
    half = (gap + 1) // 2
    out = copy(g)
    for k in range(1, half + 1):
        out[r][c1 + k] = colA
    for k in range(1, gap - half + 1):
        out[r][c2 - k] = colB
    return out
rule("seeds_grow_toward_each_other_meet_middle", "Two seeds on the same row grow toward each other one cell per step until they meet at the midpoint; if the gap is odd, the left seed's colour claims the extra cell.", gi_23, tf_23)


# 24 object grows rightward one cell at a time, stopping the instant it is blocked by the wall or another object.
def gi_24(rng):
    h, w = _big(rng, 9, 20)
    g = blank(h, w)
    r0 = rng.randint(1, h - 3)
    rh = rng.randint(1, 2)
    c0 = rng.randint(1, w - 6)
    col = rng.choice(COLOURS)
    rect(g, r0, c0, r0 + rh - 1, c0 + 1, col)
    if rng.random() < 0.6:
        blockcol = rng.choice([c for c in COLOURS if c != col])
        bc = rng.randint(c0 + 4, w - 2)
        rect(g, r0, bc, r0 + rh - 1, bc, blockcol)
    return g
def tf_24(g):
    h, w = dims(g)
    obs = objects(g, 0)
    obj = max(obs, key=len)
    r0, c0, r1, c1 = bbox(obj)
    col = g[obj[0][0]][obj[0][1]]
    limit = w - 1
    for o in obs:
        if o is obj:
            continue
        orr0, occ0, orr1, occ1 = bbox(o)
        if orr0 <= r1 and orr1 >= r0 and occ0 > c1:
            limit = min(limit, occ0 - 1)
    out = copy(g)
    rect(out, r0, c1 + 1, r1, limit, col)
    return out
rule("object_grows_rightward_until_blocked", "The object grows rightward one cell at a time, stopping the instant it would touch another object or, failing that, the right wall.", gi_24, tf_24)


# 25 a blob grows one layer outward, but only into neighbouring cells already marked grey; other grey stays grey.
def gi_25(rng):
    h, w = _big(rng, 10, 20)
    g = blank(h, w)
    col = rng.choice([c for c in COLOURS if c != 5])
    shape = random_shape(rng, rng.randint(3, 7))
    r0 = rng.randint(2, h - 6)
    c0 = rng.randint(2, w - 6)
    for r, c in shape:
        g[r0 + r][c0 + c] = col
    k = rng.randint(2, 6)
    free = [(r, c) for r in range(h) for c in range(w) if g[r][c] == 0]
    if len(free) < k:
        return None
    for r, c in rng.sample(free, k):
        g[r][c] = 5
    return g
def tf_25(g):
    h, w = dims(g)
    obj = next(o for o in objects(g, 0) if g[o[0][0]][o[0][1]] != 5)
    objset = set(obj)
    col = g[obj[0][0]][obj[0][1]]
    out = copy(g)
    for r, c in obj:
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w and g[nr][nc] == 5:
                out[nr][nc] = col
    return out
rule("grow_only_into_grey_hint_cells", "The object grows outward by one layer, but only into neighbouring cells that are grey hints; any grey cell it cannot reach stays grey.", gi_25, tf_25)


# 26 a blob grows one layer outward; each new cell takes the colour of whichever loose dot is nearest to it.
def gi_26(rng):
    h, w = _big(rng, 11, 20)
    g = blank(h, w)
    objcol = 5
    shape = random_shape(rng, rng.randint(4, 8))
    r0 = rng.randint(2, h - 6)
    c0 = rng.randint(2, w - 6)
    for r, c in shape:
        g[r0 + r][c0 + c] = objcol
    dotcols = colours(rng, 2)
    free = [(r, c) for r in range(h) for c in range(w) if g[r][c] == 0]
    if len(free) < 2:
        return None
    pts = rng.sample(free, 2)
    for (r, c), col in zip(pts, dotcols):
        g[r][c] = col
    return g
def tf_26(g):
    h, w = dims(g)
    obj = next(o for o in objects(g, 0) if g[o[0][0]][o[0][1]] == 5)
    dots = [(r, c) for r, c in cells(g, lambda v: v not in (0, 5))]
    objset = set(obj)
    layer = set()
    for r, c in obj:
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w and g[nr][nc] == 0:
                layer.add((nr, nc))
    out = copy(g)
    for r, c in layer:
        dr0, dc0 = min(dots, key=lambda p: abs(p[0] - r) + abs(p[1] - c))
        out[r][c] = g[dr0][dc0]
    return out
rule("grow_layer_coloured_by_nearest_dot", "The grey blob grows one empty layer outward; each new cell is painted with the colour of whichever loose dot is nearest to it by taxicab distance.", gi_26, tf_26)


# 27 seed grows a hollow square ring at a radius equal to its own colour value (digits).
def gi_27(rng):
    c = rng.randint(1, 8)
    lo = 2 * c + 3
    h, w = _big(rng, max(lo, 9), max(lo + 6, 18), blo=max(lo, 21))
    g = blank(h, w)
    r = rng.randint(c, h - 1 - c)
    cc = rng.randint(c, w - 1 - c)
    g[r][cc] = c
    return g
def tf_27(g):
    r, cc = cells(g, lambda v: v != 0)[0]
    c = g[r][cc]
    h, w = dims(g)
    out = copy(g)
    for rr in range(h):
        for ccc in range(w):
            if max(abs(rr - r), abs(ccc - cc)) == c:
                out[rr][ccc] = c
    return out
rule("seed_grows_square_ring_radius_digit", "The seed grows a hollow square ring whose Chebyshev radius equals the seed's own colour value, drawing only that ring's border.", gi_27, tf_27, digits=True)


# 28 a short bar grows left and right until it fills its entire row.
def gi_28(rng):
    h, w = _big(rng, 9, 20)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    r = rng.randint(0, h - 1)
    blen = rng.randint(1, max(1, w // 4))
    c0 = rng.randint(1, w - 2 - blen)
    rect(g, r, c0, r, c0 + blen - 1, col)
    return g
def tf_28(g):
    h, w = dims(g)
    r, c0 = cells(g, lambda v: v != 0)[0]
    row = [c for c in range(w) if g[r][c] != 0]
    col = g[r][row[0]]
    out = copy(g)
    for c in range(w):
        out[r][c] = col
    return out
rule("bar_grows_to_fill_its_row", "The short horizontal bar grows left and right until it reaches both walls, filling its entire row.", gi_28, tf_28)


# 29 a short bar grows up and down until it fills its entire column.
def gi_29(rng):
    h, w = _big(rng, 9, 20)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    c = rng.randint(0, w - 1)
    blen = rng.randint(1, max(1, h // 4))
    r0 = rng.randint(1, h - 2 - blen)
    rect(g, r0, c, r0 + blen - 1, c, col)
    return g
def tf_29(g):
    h, w = dims(g)
    r0, c = cells(g, lambda v: v != 0)[0]
    col_ = [r for r in range(h) if g[r][c] != 0]
    col = g[col_[0]][c]
    out = copy(g)
    for r in range(h):
        out[r][c] = col
    return out
rule("bar_grows_to_fill_its_column", "The short vertical bar grows up and down until it reaches both walls, filling its entire column.", gi_29, tf_29)


# 30 rectangle grows leftward only, until it touches the left wall.
def gi_30(rng):
    h, w = _big(rng, 9, 20)
    g = blank(h, w)
    rh = rng.randint(2, 5)
    rw = rng.randint(2, 5)
    r0 = rng.randint(1, h - 2 - rh)
    c0 = rng.randint(3, w - 2 - rw)
    rect(g, r0, c0, r0 + rh - 1, c0 + rw - 1, rng.choice(COLOURS))
    return g
def tf_30(g):
    obs = objects(g, 0)
    o = obs[0]
    r0, c0, r1, c1 = bbox(o)
    col = g[o[0][0]][o[0][1]]
    out = copy(g)
    rect(out, r0, 0, r1, c0 - 1, col)
    return out
rule("object_grows_until_touch_left_wall", "The rectangle grows only to the left, one row-wide slab at a time, until it touches the left wall.", gi_30, tf_30)


# 31 rectangle grows rightward only, until it touches the right wall.
def gi_31(rng):
    h, w = _big(rng, 9, 20)
    g = blank(h, w)
    rh = rng.randint(2, 5)
    rw = rng.randint(2, 5)
    r0 = rng.randint(1, h - 2 - rh)
    c0 = rng.randint(1, w - 4 - rw)
    rect(g, r0, c0, r0 + rh - 1, c0 + rw - 1, rng.choice(COLOURS))
    return g
def tf_31(g):
    h, w = dims(g)
    obs = objects(g, 0)
    o = obs[0]
    r0, c0, r1, c1 = bbox(o)
    col = g[o[0][0]][o[0][1]]
    out = copy(g)
    rect(out, r0, c1 + 1, r1, w - 1, col)
    return out
rule("object_grows_until_touch_right_wall", "The rectangle grows only to the right, one row-wide slab at a time, until it touches the right wall.", gi_31, tf_31)


# 32 rectangle grows upward only, until it touches the top wall.
def gi_32(rng):
    h, w = _big(rng, 9, 20)
    g = blank(h, w)
    rh = rng.randint(2, 5)
    rw = rng.randint(2, 5)
    r0 = rng.randint(3, h - 2 - rh)
    c0 = rng.randint(1, w - 2 - rw)
    rect(g, r0, c0, r0 + rh - 1, c0 + rw - 1, rng.choice(COLOURS))
    return g
def tf_32(g):
    obs = objects(g, 0)
    o = obs[0]
    r0, c0, r1, c1 = bbox(o)
    col = g[o[0][0]][o[0][1]]
    out = copy(g)
    rect(out, 0, c0, r0 - 1, c1, col)
    return out
rule("object_grows_until_touch_top_wall", "The rectangle grows only upward, one column-wide slab at a time, until it touches the top wall.", gi_32, tf_32)


# 33 rectangle grows downward only, until it touches the bottom wall.
def gi_33(rng):
    h, w = _big(rng, 9, 20)
    g = blank(h, w)
    rh = rng.randint(2, 5)
    rw = rng.randint(2, 5)
    r0 = rng.randint(1, h - 4 - rh)
    c0 = rng.randint(1, w - 2 - rw)
    rect(g, r0, c0, r0 + rh - 1, c0 + rw - 1, rng.choice(COLOURS))
    return g
def tf_33(g):
    h, w = dims(g)
    obs = objects(g, 0)
    o = obs[0]
    r0, c0, r1, c1 = bbox(o)
    col = g[o[0][0]][o[0][1]]
    out = copy(g)
    rect(out, r1 + 1, c0, h - 1, c1, col)
    return out
rule("object_grows_until_touch_bottom_wall", "The rectangle grows only downward, one column-wide slab at a time, until it touches the bottom wall.", gi_33, tf_33)


# 34 seed grows a fixed four-step staircase: right 2, down 1, repeated four times.
def gi_34(rng):
    h, w = _big(rng, 14, 22)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    r = rng.randint(1, h - 6)
    c = rng.randint(1, w - 10)
    g[r][c] = col
    return g
def tf_34(g):
    r, c = cells(g, lambda v: v != 0)[0]
    col = g[r][c]
    out = copy(g)
    rr, cc = r, c
    for _ in range(4):
        out[rr][cc + 1] = col
        out[rr][cc + 2] = col
        out[rr + 1][cc + 2] = col
        rr += 1
        cc += 2
    return out
rule("seed_grows_fixed_staircase_four_steps", "The seed grows a staircase of exactly four fixed steps, each step two cells right then one cell down, then stops.", gi_34, tf_34)


# 35 a hollow rectangle thickens inward by exactly one ring (its border gets one cell thicker).
def gi_35(rng):
    h, w = _big(rng, 11, 20)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    rh = rng.randint(6, min(12, h - 2))
    rw = rng.randint(6, min(12, w - 2))
    r0 = rng.randint(1, h - 1 - rh)
    c0 = rng.randint(1, w - 1 - rw)
    rect(g, r0, c0, r0 + rh - 1, c0 + rw - 1, col, fill=False)
    return g
def tf_35(g):
    obs = objects(g, 0)
    frame = obs[0]
    col = g[frame[0][0]][frame[0][1]]
    r0, c0, r1, c1 = bbox(frame)
    out = copy(g)
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if min(r - r0, r1 - r, c - c0, c1 - c) < 2:
                out[r][c] = col
    return out
# frame_thickens_inward_one_ring dropped 2026-10-12 (review 2: behavioural duplicate of blob_frame_fills_fixed_two_rings)
# 36 seed sprouts plus arms that each grow until reaching the inner wall of a grey frame.
def gi_36(rng):
    h, w = _big(rng, 13, 22)
    fr = _framed(rng, h, w, pad=3)
    if fr is None:
        return None
    g, fr0, fc0, fr1, fc1 = fr
    col = rng.choice([c for c in COLOURS if c != 5])
    r = rng.randint(fr0 + 2, fr1 - 2)
    c = rng.randint(fc0 + 2, fc1 - 2)
    g[r][c] = col
    return g
def tf_36(g):
    frame = next(o for o in objects(g, 0) if g[o[0][0]][o[0][1]] == 5)
    fr0, fc0, fr1, fc1 = bbox(frame)
    seed = next(o for o in objects(g, 0) if g[o[0][0]][o[0][1]] != 5)
    r, c = seed[0]
    col = g[r][c]
    out = copy(g)
    rect(out, fr0 + 1, c, r, c, col)
    rect(out, r, fc0 + 1, r, c, col)
    rect(out, r, c, fr1 - 1, c, col)
    rect(out, r, c, r, fc1 - 1, col)
    return out
rule("seed_sprout_plus_arms_until_frame", "The seed sprouts a plus sign; each of its four arms grows outward until it touches the inner wall of the surrounding grey frame, then stops.", gi_36, tf_36)


# 37 seed grows a fixed six-cell zigzag: right, up, right, up, right, up.
def gi_37(rng):
    h, w = _big(rng, 13, 22)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    r = rng.randint(4, h - 2)
    c = rng.randint(1, w - 5)
    g[r][c] = col
    return g
def tf_37(g):
    r, c = cells(g, lambda v: v != 0)[0]
    col = g[r][c]
    out = copy(g)
    rr, cc = r, c
    for _ in range(3):
        cc += 1
        out[rr][cc] = col
        rr -= 1
        out[rr][cc] = col
    return out
rule("seed_grows_zigzag_fixed_six_cells", "The seed grows a fixed zigzag of six cells, alternating one step right and one step up three times, then stops.", gi_37, tf_37)


# 38 rectangle grows outward equally on all four sides until its bounding box just reaches a single marker cell.
def gi_38(rng):
    h, w = _big(rng, 14, 24)
    g = blank(h, w)
    rh = rng.randint(2, 4)
    rw = rng.randint(2, 4)
    r0 = rng.randint(5, h - 6 - rh)
    c0 = rng.randint(5, w - 6 - rw)
    col = rng.choice(COLOURS)
    rect(g, r0, c0, r0 + rh - 1, c0 + rw - 1, col)
    r1, c1 = r0 + rh - 1, c0 + rw - 1
    k = rng.randint(1, 4)
    mcol = rng.choice([c for c in COLOURS if c != col])
    side = rng.choice(["t", "b", "l", "r"])
    if side == "t":
        g[r0 - k][rng.randint(c0, c1)] = mcol
    elif side == "b":
        g[r1 + k][rng.randint(c0, c1)] = mcol
    elif side == "l":
        g[rng.randint(r0, r1)][c0 - k] = mcol
    else:
        g[rng.randint(r0, r1)][c1 + k] = mcol
    return g
def tf_38(g):
    h, w = dims(g)
    obs = objects(g, 0)
    rectobj = max(obs, key=len)
    marker = min(obs, key=len)
    r0, c0, r1, c1 = bbox(rectobj)
    mr, mc = marker[0]
    col = g[rectobj[0][0]][rectobj[0][1]]
    k = max(r0 - mr, mr - r1, c0 - mc, mc - c1, 0)
    nr0, nr1 = max(0, r0 - k), min(h - 1, r1 + k)
    nc0, nc1 = max(0, c0 - k), min(w - 1, c1 + k)
    out = copy(g)
    rect(out, nr0, nc0, nr1, nc1, col)
    return out
rule("grow_rect_uniform_until_reaches_marker", "The rectangle grows outward equally on all four sides, one layer at a time, until its bounding box just reaches the single marker cell, then stops.", gi_38, tf_38)


# 39 of two seeds, the one nearer the top-left grows diagonally to the top-left wall, the other to the bottom-right wall.
def gi_39(rng):
    h, w = _big(rng, 11, 20)
    g = blank(h, w)
    cols = colours(rng, 2)
    r1, c1 = rng.randint(2, h // 2 - 1), rng.randint(2, w // 2 - 1)
    r2, c2 = rng.randint(h // 2 + 1, h - 3), rng.randint(w // 2 + 1, w - 3)
    g[r1][c1] = cols[0]
    g[r2][c2] = cols[1]
    return g
def tf_39(g):
    h, w = dims(g)
    pts = cells(g, lambda v: v != 0)
    out = copy(g)
    a, b = sorted(pts, key=lambda p: p[0] + p[1])
    colA = g[a[0]][a[1]]
    colB = g[b[0]][b[1]]
    rr, cc = a
    while rr > 0 and cc > 0:
        rr -= 1
        cc -= 1
        out[rr][cc] = colA
    rr, cc = b
    while rr < h - 1 and cc < w - 1:
        rr += 1
        cc += 1
        out[rr][cc] = colB
    return out
rule("two_seeds_grow_opposite_diagonals_to_corners", "Of the two seeds, the one nearer the top-left grows diagonally up and to the left until it hits a wall, and the other grows diagonally down and to the right until it hits a wall.", gi_39, tf_39)


# 40 rectangle grows straight down until it reaches a grey guide line, which absorbs its colour where they overlap.
def gi_40(rng):
    h, w = _big(rng, 13, 22)
    g = blank(h, w)
    rh = rng.randint(2, 4)
    rw = rng.randint(2, 5)
    line_r = rng.randint(h - 5, h - 2)
    r0 = rng.randint(1, line_r - rh - 2)
    c0 = rng.randint(1, w - 2 - rw)
    col = rng.choice([c for c in COLOURS if c != 5])
    rect(g, r0, c0, r0 + rh - 1, c0 + rw - 1, col)
    for c in range(w):
        g[line_r][c] = 5
    return g
def tf_40(g):
    h, w = dims(g)
    obj = next(o for o in objects(g, 0) if g[o[0][0]][o[0][1]] != 5)
    r0, c0, r1, c1 = bbox(obj)
    col = g[obj[0][0]][obj[0][1]]
    line_r = next(r for r in range(h) if g[r][0] == 5)
    out = copy(g)
    rect(out, r1 + 1, c0, line_r, c1, col)
    return out
rule("object_grows_downward_until_touch_dot_colour", "The rectangle grows straight down until it reaches the grey guide line spanning the grid, recolouring the overlapped part of the line to its own colour, then stops.", gi_40, tf_40)
