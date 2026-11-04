# b061_slopes.py -- lines at non-45/non-axis slopes and step patterns: ratios like 1:2, 2:1, 1:3, 2:3,
# knight-step vectors, Bresenham segments, diagonal sliding, billiard reflection, and slope-keyed legends.
# Every rasterisation rule is stated exactly: step vectors are reduced integer ratios (no rounding needed
# when the generator places markers at exact multiples of the ratio); the two Bresenham rules state their
# floor-rounding explicitly since their markers are NOT constrained to an exact ratio.
import sys, os
from math import gcd
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


def rand_dims(rng, p_big=0.45):
    if rng.random() < p_big:
        return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(7, 20), rng.randint(7, 20)


def ray_forward(h, w, r0, c0, dr, dc):
    pts = []
    r, c = r0, c0
    while 0 <= r < h and 0 <= c < w:
        pts.append((r, c)); r += dr; c += dc
    return pts


def ray_both(h, w, r0, c0, dr, dc):
    pts = ray_forward(h, w, r0, c0, dr, dc)
    r, c = r0 - dr, c0 - dc
    while 0 <= r < h and 0 <= c < w:
        pts.append((r, c)); r -= dr; c -= dc
    return pts


def bres_floor(r0, c0, r1, c1):
    """Bresenham segment r0,c0 -> r1,c1 inclusive: n = max(|dr|,|dc|) steps, point i is
    (r0 + (dr*i)//n, c0 + (dc*i)//n) using Python floor (toward -inf) integer division."""
    dr, dc = r1 - r0, c1 - c0
    n = max(abs(dr), abs(dc))
    if n == 0:
        return [(r0, c0)]
    return [(r0 + (dr * i) // n, c0 + (dc * i) // n) for i in range(n + 1)]


def _single_dots(g):
    return [o[0] for o in objects(g, 0) if len(o) == 1]


def _place_dot_with_room(rng, h, w, mkray, tries=60):
    for _ in range(tries):
        r0, c0 = rng.randrange(h), rng.randrange(w)
        pts = mkray(h, w, r0, c0)
        if len(pts) >= 3:
            return r0, c0, pts
    return None


def _noise_shapes(rng, g, avoid, h, w, k_lo=1, k_hi=3):
    cols = rng.sample(COLOURS, rng.randint(k_lo, k_hi))
    for oc in cols:
        shape = random_shape(rng, rng.randint(2, 4))
        sh = max(r for r, _ in shape) + 1; sw = max(c for _, c in shape) + 1
        if sh > h or sw > w:
            continue
        for _ in range(30):
            r0, c0 = rng.randint(0, h - sh), rng.randint(0, w - sw)
            abscells = [(r0 + r, c0 + c) for r, c in shape]
            if all(g[a][b] == 0 and (a, b) not in avoid for a, b in abscells):
                for a, b in abscells: g[a][b] = oc
                break
    return g


# ---------------------------------------------------------------- Group 1: two dots at a reduced
# integer slope extend to both edges; a fixed count of noise dots of OTHER colours mark the rest.
def _mk_two_dot_slope(dr, dc):
    def gi(rng):
        h, w = rand_dims(rng)
        g = blank(h, w)
        col = rng.choice(COLOURS)
        n = rng.randint(1, 3)
        placed = None
        for _ in range(60):
            r0, c0 = rng.randrange(h), rng.randrange(w)
            r1, c1 = r0 + n * dr, c0 + n * dc
            if 0 <= r1 < h and 0 <= c1 < w:
                placed = (r0, c0, r1, c1); break
        if placed is None:
            return None
        r0, c0, r1, c1 = placed
        g[r0][c0] = col; g[r1][c1] = col
        line_set = set(ray_both(h, w, r0, c0, dr, dc))
        other = [c for c in COLOURS if c != col]
        noise_cols = rng.sample(other, rng.randint(1, min(4, len(other))))
        for oc in noise_cols:
            for _ in range(40):
                r, c = rng.randrange(h), rng.randrange(w)
                if (r, c) not in line_set and g[r][c] == 0:
                    g[r][c] = oc; break
        return g

    def tf(g):
        h, w = dims(g)
        pts = cells(g, lambda v: v != 0)
        cc = Counter(g[r][c] for r, c in pts)
        cand = [col for col, n in cc.items() if n == 2]
        if len(cand) != 1:
            return None
        col = cand[0]
        pr = [(r, c) for r, c in pts if g[r][c] == col]
        (r0, c0), (r1, c1) = pr
        vr, vc = r1 - r0, c1 - c0
        g0 = gcd(abs(vr), abs(vc))
        if g0 == 0:
            return None
        vr, vc = vr // g0, vc // g0
        if (abs(vr), abs(vc)) != (abs(dr), abs(dc)):
            return None
        out = copy(g)
        for r, c in ray_both(h, w, r0, c0, vr, vc):
            out[r][c] = col
        return out
    return gi, tf


for _dr, _dc, _nm in ((1, 2, "slope12"), (2, 1, "slope21"), (1, 3, "slope13"), (3, 1, "slope31"),
                      (2, 3, "slope23"), (3, 2, "slope32"), (1, 5, "slope15"), (5, 1, "slope51")):
    _gi, _tf = _mk_two_dot_slope(_dr, _dc)
    rule(f"{_nm}_two_dots_extend_edges",
         f"Two cells of the same colour sit a {_dr}-down-by-{_dc}-across step apart (or a multiple of it); "
         f"the straight line through them at that slope is extended in both directions to the grid edges.",
         _gi, _tf)


# ---------------------------------------------------------------- Group 2: a lone dot (the one size-1
# object) emits a straight ray at a fixed slope to the edge, in its own colour. Noise objects are size >= 2
# so the single dot is always unambiguous.
def _mk_ray_from_dot(dr, dc):
    def gi(rng):
        h, w = rand_dims(rng)
        g = blank(h, w)
        found = _place_dot_with_room(rng, h, w, lambda h, w, r, c: ray_forward(h, w, r, c, dr, dc))
        if found is None:
            return None
        r0, c0, pts = found
        col = rng.choice(COLOURS)
        g[r0][c0] = col
        _noise_shapes(rng, g, set(pts), h, w)
        return g

    def tf(g):
        h, w = dims(g)
        dots = _single_dots(g)
        if len(dots) != 1:
            return None
        r0, c0 = dots[0]
        col = g[r0][c0]
        out = copy(g)
        for r, c in ray_forward(h, w, r0, c0, dr, dc):
            out[r][c] = col
        return out
    return gi, tf


for _dr, _dc, _nm in ((1, 4, "14"), (4, 1, "41"), (3, 4, "34"), (4, 3, "43"), (2, 5, "25"), (5, 2, "52")):
    _gi, _tf = _mk_ray_from_dot(_dr, _dc)
    rule(f"ray_from_dot_slope{_nm}",
         f"The one isolated single cell (every noise shape is at least two cells) shoots a ray of its own "
         f"colour at slope {_dr}-down-by-{_dc}-across, continuing to the grid edge.",
         _gi, _tf)


# ---------------------------------------------------------------- Group 3: knight-step chains (one
# isolated dot, step repeatedly by the given vector).
def _mk_chain_both_ways(dr, dc):
    def gi(rng):
        h, w = rand_dims(rng)
        g = blank(h, w)
        found = _place_dot_with_room(rng, h, w, lambda h, w, r, c: ray_both(h, w, r, c, dr, dc))
        if found is None:
            return None
        r0, c0, pts = found
        col = rng.choice(COLOURS)
        g[r0][c0] = col
        _noise_shapes(rng, g, set(pts), h, w)
        return g

    def tf(g):
        h, w = dims(g)
        dots = _single_dots(g)
        if len(dots) != 1:
            return None
        r0, c0 = dots[0]
        col = g[r0][c0]
        out = copy(g)
        for r, c in ray_both(h, w, r0, c0, dr, dc):
            out[r][c] = col
        return out
    return gi, tf


rule("knight_vector_up1_right2_chain_both_ways",
     "The one isolated dot repeats the knight step one up, two across in both directions, colouring every "
     "cell it lands on the same colour, until the step would leave the grid.",
     *_mk_chain_both_ways(-1, 2))
rule("knight_vector_up2_right1_chain_both_ways",
     "The one isolated dot repeats the knight step two up, one across in both directions, colouring every "
     "cell it lands on the same colour, until the step would leave the grid.",
     *_mk_chain_both_ways(-2, 1))
rule("knight_vector_up1_right3_chain_both_ways",
     "The one isolated dot repeats the step one up, three across in both directions, colouring every cell "
     "it lands on the same colour, until the step would leave the grid.",
     *_mk_chain_both_ways(-1, 3))


def _mk_chain_colour_alt(dr, dc):
    def gi(rng):
        h, w = rand_dims(rng)
        g = blank(h, w)
        found = _place_dot_with_room(rng, h, w, lambda h, w, r, c: ray_forward(h, w, r, c, dr, dc))
        if found is None:
            return None
        r0, c0, pts = found
        col = rng.choice(COLOURS)
        g[r0][c0] = col
        _noise_shapes(rng, g, set(pts), h, w)
        return g

    def tf(g):
        h, w = dims(g)
        dots = _single_dots(g)
        if len(dots) != 1:
            return None
        r0, c0 = dots[0]
        col = g[r0][c0]
        col2 = col % 9 + 1
        pts = ray_forward(h, w, r0, c0, dr, dc)
        if len(pts) < 3:
            return None
        out = copy(g)
        for i, (r, c) in enumerate(pts):
            out[r][c] = col if i % 2 == 0 else col2
        return out
    return gi, tf


rule("knight_vector_up1_right2_chain_colour_alternates",
     "The one isolated dot repeats the knight step one up, two across, colouring the cells it lands on "
     "alternately its own colour and colour (its colour mod 9) + 1, starting with its own colour.",
     *_mk_chain_colour_alt(-1, 2), digits=True)
rule("knight_vector_up2_right1_chain_colour_alternates",
     "The one isolated dot repeats the knight step two up, one across, colouring the cells it lands on "
     "alternately its own colour and colour (its colour mod 9) + 1, starting with its own colour.",
     *_mk_chain_colour_alt(-2, 1), digits=True)


# ---------------------------------------------------------------- Group 4: every object slides along a
# fixed diagonal ratio until the next step would leave the grid; later objects (scan order) paint over
# earlier ones on collision.
def slide_final(h, w, obj, dr, dc):
    k = 0
    while all(0 <= r + (k + 1) * dr < h and 0 <= c + (k + 1) * dc < w for r, c in obj):
        k += 1
    return [(r + k * dr, c + k * dc) for r, c in obj]


def _mk_object_slide(dr, dc):
    def gi(rng):
        h, w = rand_dims(rng)
        g = blank(h, w)
        k = rng.randint(2, 4)
        placed = 0
        attempts = 0
        while placed < k and attempts < 300:
            attempts += 1
            shape = random_shape(rng, rng.randint(2, 5))
            sh = max(r for r, _ in shape) + 1; sw = max(c for _, c in shape) + 1
            steps = rng.randint(1, 3)
            max_r0 = h - sh - steps * max(dr, 0); max_c0 = w - sw - steps * max(dc, 0)
            min_r0 = -steps * min(dr, 0); min_c0 = -steps * min(dc, 0)
            if max_r0 < min_r0 or max_c0 < min_c0:
                continue
            r0, c0 = rng.randint(min_r0, max_r0), rng.randint(min_c0, max_c0)
            abscells = [(r0 + r, c0 + c) for r, c in shape]
            if all(0 <= a < h and 0 <= b < w and g[a][b] == 0 for a, b in abscells):
                col = rng.choice(COLOURS)
                for a, b in abscells: g[a][b] = col
                placed += 1
        return g if placed >= 2 else None

    def tf(g):
        h, w = dims(g)
        out = blank(h, w)
        for o in objects(g, 0):
            col = g[o[0][0]][o[0][1]]
            for r, c in slide_final(h, w, o, dr, dc):
                out[r][c] = col
        return out
    return gi, tf


rule("object_slides_slope12_to_edge",
     "Every object slides as a rigid shape along the one-down-two-across diagonal, as far as it can go "
     "while staying on the grid; objects are redrawn in scan order so a later one overwrites an earlier "
     "one where they collide.",
     *_mk_object_slide(1, 2))
rule("object_slides_slope21_to_edge",
     "Every object slides as a rigid shape along the two-down-one-across diagonal, as far as it can go "
     "while staying on the grid; objects are redrawn in scan order so a later one overwrites an earlier "
     "one where they collide.",
     *_mk_object_slide(2, 1))


# ---------------------------------------------------------------- Group 5: general Bresenham segments
# between two markers of the same colour (any slope, not constrained to a nice ratio).
def _two_marker_scene(rng, h, w, same_colour=True):
    g = blank(h, w)
    if same_colour:
        col = rng.choice(COLOURS)
        cols = (col, col)
    else:
        cols = tuple(rng.sample(COLOURS, 2))
    for _ in range(60):
        r0, c0 = rng.randrange(h), rng.randrange(w)
        r1, c1 = rng.randrange(h), rng.randrange(w)
        if (r0, c0) != (r1, c1) and abs(r0 - r1) + abs(c0 - c1) >= 4:
            g[r0][c0] = cols[0]; g[r1][c1] = cols[1]
            return g
    return None


def gi_bres1(rng):
    h, w = rand_dims(rng)
    return _two_marker_scene(rng, h, w, same_colour=True)


def tf_bres1(g):
    h, w = dims(g)
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 2:
        return None
    (r0, c0), (r1, c1) = pts
    col = g[r0][c0]
    if g[r1][c1] != col:
        return None
    out = copy(g)
    for r, c in bres_floor(r0, c0, r1, c1):
        out[r][c] = col
    return out
rule("bresenham_line_between_two_markers",
     "A straight line (Bresenham, each point i of n = max(|dr|,|dc|) placed at r0 + floor(dr*i/n), "
     "c0 + floor(dc*i/n)) is drawn between the two same-colour markers, in their colour.",
     gi_bres1, tf_bres1)


def gi_bres2(rng):
    h, w = rand_dims(rng)
    return _two_marker_scene(rng, h, w, same_colour=False)


def tf_bres2(g):
    h, w = dims(g)
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 2:
        return None
    (r0, c0), (r1, c1) = pts
    colA, colB = g[r0][c0], g[r1][c1]
    if colA == colB:
        return None
    seg = bres_floor(r0, c0, r1, c1)
    n = len(seg)
    out = copy(g)
    for i, (r, c) in enumerate(seg):
        out[r][c] = colA if i < n // 2 else colB
    return out
rule("bresenham_line_split_colour_by_half",
     "A straight Bresenham line is drawn between the two differently-coloured markers; the floor(n/2) "
     "points nearer the first marker take its colour and the rest take the second marker's colour.",
     gi_bres2, tf_bres2)


# ---------------------------------------------------------------- Group 6: a 45-degree ray bounces off
# the border like a billiard ball and stops after a fixed number of bounces, clamped to the border cell
# it was heading for.
def billiard_path(h, w, r0, c0, bounces):
    dr, dc = 1, 1
    r, c = r0, c0
    pts = [(r, c)]
    nbounce = 0
    for _ in range(4 * (h + w) + 10):
        nr, nc = r + dr, c + dc
        hit_r = nr < 0 or nr >= h
        hit_c = nc < 0 or nc >= w
        if hit_r or hit_c:
            if nbounce >= bounces:
                nr = max(0, min(h - 1, nr)); nc = max(0, min(w - 1, nc))
                pts.append((nr, nc))
                break
            if hit_r: dr = -dr
            if hit_c: dc = -dc
            nbounce += 1
            nr, nc = r + dr, c + dc
        r, c = nr, nc
        pts.append((r, c))
    return pts


def _mk_billiard(bounces):
    def gi(rng):
        h, w = rand_dims(rng, p_big=0.4)
        if h < 9 or w < 9:
            return None
        g = blank(h, w)
        r0, c0 = rng.randint(1, h - 2), rng.randint(1, w - 2)
        col = rng.choice(COLOURS)
        g[r0][c0] = col
        pts = billiard_path(h, w, r0, c0, bounces)
        if len(pts) < 5:
            return None
        return g

    def tf(g):
        h, w = dims(g)
        dots = _single_dots(g)
        if len(dots) != 1:
            return None
        r0, c0 = dots[0]
        col = g[r0][c0]
        out = copy(g)
        for r, c in billiard_path(h, w, r0, c0, bounces):
            out[r][c] = col
        return out
    return gi, tf


rule("ray45_reflects_once_off_border",
     "A ray leaves the dot heading down-right at 45 degrees; it reflects once off whichever border it "
     "reaches first (angle of incidence = angle of reflection) and is drawn onward to the next border, "
     "where it stops.",
     *_mk_billiard(1))
rule("ray45_reflects_twice_off_border",
     "A ray leaves the dot heading down-right at 45 degrees and reflects off borders twice, each time "
     "flipping the row or column direction it just hit; it is drawn onward from the second reflection to "
     "the next border, where it stops.",
     *_mk_billiard(2))


# ---------------------------------------------------------------- 15 one-off rules.

# bishop: four fixed diagonal rays from the one dot, each 45-degree direction a fixed colour regardless
# of the dot's own colour (NE=2, SE=3, SW=4, NW=6), drawn in that order so a corner cell gets the last one.
def gi_bishop(rng):
    h, w = rand_dims(rng)
    g = blank(h, w)
    r0, c0 = rng.randint(1, h - 2), rng.randint(1, w - 2)
    g[r0][c0] = rng.choice(COLOURS)
    return g
def tf_bishop(g):
    h, w = dims(g)
    dots = _single_dots(g)
    if len(dots) != 1:
        return None
    r0, c0 = dots[0]
    out = copy(g)
    for (dr, dc), col in (((-1, 1), 2), ((1, 1), 3), ((1, -1), 4), ((-1, -1), 6)):
        for r, c in ray_forward(h, w, r0, c0, dr, dc):
            out[r][c] = col
    return out
rule("bishop_four_diagonal_rays_coded_by_direction",
     "The one dot emits all four 45-degree rays to the edges; each is painted a fixed colour by direction "
     "(NE=2, SE=3, SW=4, NW=6), drawn in that order so the corner cell carries the last one painted.",
     gi_bishop, tf_bishop, digits=True)


# knight moves: the (up to 8) knight-move destinations from the one dot are marked its own colour.
def gi_knightmoves(rng):
    h, w = rand_dims(rng)
    g = blank(h, w)
    for _ in range(40):
        r0, c0 = rng.randint(2, h - 3), rng.randint(2, w - 3)
        g2 = blank(h, w); g2[r0][c0] = rng.choice(COLOURS)
        return g2
    return None
def tf_knightmoves(g):
    h, w = dims(g)
    dots = _single_dots(g)
    if len(dots) != 1:
        return None
    r0, c0 = dots[0]
    col = g[r0][c0]
    out = copy(g)
    vecs = [(a, b) for a in (-2, -1, 1, 2) for b in (-2, -1, 1, 2) if abs(a) != abs(b)]
    n = 0
    for dr, dc in vecs:
        r, c = r0 + dr, c0 + dc
        if 0 <= r < h and 0 <= c < w:
            out[r][c] = col; n += 1
    return out if n else None
rule("knight_moves_marked_same_colour",
     "Every cell a knight could reach in one move from the dot is painted the dot's own colour.",
     gi_knightmoves, tf_knightmoves)


# mirrored rays at slope 1:2, mirrored left-right, from the one dot, both the dot's colour.
def gi_mirrorrays(rng):
    h, w = rand_dims(rng)
    g = blank(h, w)
    r0, c0 = rng.randint(0, h - 1), rng.randint(0, w - 1)
    g[r0][c0] = rng.choice(COLOURS)
    return g
def tf_mirrorrays(g):
    h, w = dims(g)
    dots = _single_dots(g)
    if len(dots) != 1:
        return None
    r0, c0 = dots[0]
    col = g[r0][c0]
    out = copy(g)
    for dr, dc in ((1, 2), (1, -2)):
        for r, c in ray_forward(h, w, r0, c0, dr, dc):
            out[r][c] = col
    return out
rule("mirrored_slope_rays_vertical_axis",
     "The one dot emits two rays going down, one stepping one-down-two-right and the other one-down-two-"
     "left, mirror images of each other, both in its own colour.",
     gi_mirrorrays, tf_mirrorrays)


# slope of the two dots (from a fixed set of 4) encoded as a colour in a 1x2 output.
_SLOPE_CODE = {(1, 2): 2, (2, 1): 3, (1, 3): 4, (3, 1): 6}
def gi_slopecode(rng):
    h, w = rand_dims(rng)
    g = blank(h, w)
    dr, dc = rng.choice(list(_SLOPE_CODE))
    n = rng.randint(1, 3)
    col = rng.choice(COLOURS)
    for _ in range(60):
        r0, c0 = rng.randrange(h), rng.randrange(w)
        r1, c1 = r0 + n * dr, c0 + n * dc
        if 0 <= r1 < h and 0 <= c1 < w:
            g[r0][c0] = col; g[r1][c1] = col
            return g
    return None
def tf_slopecode(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 2:
        return None
    (r0, c0), (r1, c1) = pts
    vr, vc = r1 - r0, c1 - c0
    g0 = gcd(abs(vr), abs(vc))
    if g0 == 0:
        return None
    key = (abs(vr) // g0, abs(vc) // g0)
    code = _SLOPE_CODE.get(key)
    if code is None:
        return None
    return [[code, 0]]
rule("slope_pair_encoded_as_single_colour",
     "The slope of the line through the two marker dots is looked up in a fixed table (1:2->2, 2:1->3, "
     "1:3->4, 3:1->6) and that colour is output as the first of two cells, the second left background.",
     gi_slopecode, tf_slopecode, digits=True)


# zigzag staircase whose tread length is the length of a horizontal bar object.
def zigzag_pts(h, w, r0, c0, L):
    pts = [(r0, c0)]
    r, c = r0, c0
    for _ in range(h + w + 5):
        prev = (r, c)
        for _ in range(L):
            if c + 1 >= w:
                break
            c += 1; pts.append((r, c))
        if r + 1 >= h:
            break
        r += 1; pts.append((r, c))
        if (r, c) == prev:
            break
    return pts
def gi_zigzag(rng):
    h, w = rand_dims(rng)
    g = blank(h, w)
    L = rng.randint(2, 5)
    cb, cs = rng.sample(COLOURS, 2)
    for _ in range(40):
        br, bc0 = rng.randrange(h), rng.randrange(w - L)
        sr, sc = rng.randrange(h), rng.randrange(w)
        bar_cells = {(br, bc0 + i) for i in range(L)}
        if (sr, sc) not in bar_cells and all(g[r][c] == 0 for r, c in bar_cells) and g[sr][sc] == 0:
            for r, c in bar_cells: g[r][c] = cb
            g[sr][sc] = cs
            return g
    return None
def tf_zigzag(g):
    h, w = dims(g)
    obs = objects(g, 0)
    bars = [o for o in obs if len(o) >= 2 and len({r for r, _ in o}) == 1]
    seeds = [o for o in obs if len(o) == 1]
    if len(bars) != 1 or len(seeds) != 1:
        return None
    L = len(bars[0])
    r0, c0 = seeds[0][0]
    cs = g[r0][c0]
    pts = zigzag_pts(h, w, r0, c0, L)
    if len(pts) < 3:
        return None
    out = copy(g)
    for r, c in pts: out[r][c] = cs
    return out
rule("zigzag_period_from_bar_length",
     "The lone dot traces a staircase whose tread length equals the length of the separate horizontal "
     "bar (right L cells, down 1 cell, repeat), drawn in the dot's own colour, stopping at the edge.",
     gi_zigzag, tf_zigzag)


# two straight segments at different fixed slopes; the steeper one takes the other's colour.
def _seg_cells(r0, c0, dr, dc, length):
    return [(r0 + i * dr, c0 + i * dc) for i in range(length)]
def gi_steeper(rng):
    h, w = rand_dims(rng)
    g = blank(h, w)
    colA, colB = rng.sample(COLOURS, 2)
    for _ in range(60):
        lenA, lenB = rng.randint(3, 5), rng.randint(3, 5)
        if h - 1 - lenA < 0 or w - 1 - 2 * lenA < 0 or h - 1 - lenB < 0 or w - 1 - 4 * lenB < 0:
            continue
        ar, ac = rng.randint(0, h - 1 - lenA), rng.randint(0, w - 1 - 2 * lenA)
        br, bc = rng.randint(0, h - 1 - lenB), rng.randint(0, w - 1 - 4 * lenB)
        segA = _seg_cells(ar, ac, 1, 2, lenA)
        segB = _seg_cells(br, bc, 1, 4, lenB)
        if set(segA) & set(segB):
            continue
        for r, c in segA: g[r][c] = colA
        for r, c in segB: g[r][c] = colB
        return g
    return None
def tf_steeper(g):
    pts = cells(g, lambda v: v != 0)
    by_col = {}
    for r, c in pts:
        by_col.setdefault(g[r][c], []).append((r, c))
    if len(by_col) != 2:
        return None
    def slope_mag(o):
        rs = [r for r, _ in o]; cs = [c for _, c in o]
        dr = max(rs) - min(rs); dc = max(cs) - min(cs)
        return dr / dc if dc else float("inf")
    (colA, segA), (colB, segB) = list(by_col.items())
    steep_col, other_col = (colA, colB) if slope_mag(segA) > slope_mag(segB) else (colB, colA)
    out = copy(g)
    for r, c in pts:
        if g[r][c] == steep_col:
            out[r][c] = other_col
    return out
rule("steeper_line_recoloured_to_other",
     "Of the two straight line segments, the one with the larger rise-over-run magnitude is recoloured "
     "with the other segment's colour.",
     gi_steeper, tf_steeper)


# three segments at three fixed slopes sorted by slope magnitude into a column, smallest on top.
def gi_sortedslope(rng):
    h, w = rand_dims(rng)
    g = blank(h, w)
    cols = rng.sample(COLOURS, 3)
    slopes = [(1, 4), (1, 3), (1, 2)]
    rng.shuffle(slopes)
    placed = []
    for (dr, dc), col in zip(slopes, cols):
        ok = False
        for _ in range(60):
            length = rng.randint(3, 5)
            if h - 1 - dr * (length - 1) < 0 or w - 1 - dc * (length - 1) < 0:
                continue
            r0 = rng.randint(0, h - 1 - dr * (length - 1))
            c0 = rng.randint(0, w - 1 - dc * (length - 1))
            seg = _seg_cells(r0, c0, dr, dc, length)
            if all(g[r][c] == 0 for r, c in seg):
                for r, c in seg: g[r][c] = col
                ok = True; break
        if not ok:
            return None
        placed.append(True)
    return g
def tf_sortedslope(g):
    pts = cells(g, lambda v: v != 0)
    by_col = {}
    for r, c in pts:
        by_col.setdefault(g[r][c], []).append((r, c))
    if len(by_col) != 3:
        return None
    def slope_mag(o):
        rs = [r for r, _ in o]; cs = [c for _, c in o]
        dr = max(rs) - min(rs); dc = max(cs) - min(cs)
        return dr / dc if dc else float("inf")
    ordered = sorted(by_col.items(), key=lambda kv: slope_mag(kv[1]))
    cols = [col for col, _ in ordered]
    return [[c] for c in cols]
rule("lines_sorted_by_slope_into_column",
     "The three straight segments are listed top to bottom in a one-column output, ordered by increasing "
     "rise-over-run slope magnitude.",
     gi_sortedslope, tf_sortedslope)


# staircase whose vertical step size is 1 for an odd dot colour, 2 for an even dot colour (digits).
def gi_stairparity(rng):
    h, w = rand_dims(rng)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    dr = 1 if col % 2 == 1 else 2
    found = _place_dot_with_room(rng, h, w, lambda h, w, r, c: ray_forward(h, w, r, c, dr, 1))
    if found is None:
        return None
    r0, c0, _ = found
    g[r0][c0] = col
    return g
def tf_stairparity(g):
    h, w = dims(g)
    dots = _single_dots(g)
    if len(dots) != 1:
        return None
    r0, c0 = dots[0]
    col = g[r0][c0]
    dr = 1 if col % 2 == 1 else 2
    out = copy(g)
    for r, c in ray_forward(h, w, r0, c0, dr, 1):
        out[r][c] = col
    return out
rule("staircase_step_from_colour_parity",
     "The lone dot continues as a staircase stepping one down per column if its colour is odd, two down "
     "per column if its colour is even, drawn in its own colour to the edge.",
     gi_stairparity, tf_stairparity, digits=True)


# fixed period-3 staircase: right, right, down, repeating, from the one dot.
def pattern_pts(h, w, r0, c0, moves):
    pts = [(r0, c0)]
    r, c = r0, c0
    for _ in range(200):
        for dr, dc in moves:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < h and 0 <= nc < w):
                return pts
            r, c = nr, nc; pts.append((r, c))
    return pts
def gi_period3(rng):
    h, w = rand_dims(rng)
    g = blank(h, w)
    found = _place_dot_with_room(rng, h, w, lambda h, w, r, c: pattern_pts(h, w, r, c, [(0, 1), (0, 1), (1, 0)]))
    if found is None:
        return None
    r0, c0, _ = found
    g[r0][c0] = rng.choice(COLOURS)
    return g
def tf_period3(g):
    h, w = dims(g)
    dots = _single_dots(g)
    if len(dots) != 1:
        return None
    r0, c0 = dots[0]
    col = g[r0][c0]
    out = copy(g)
    for r, c in pattern_pts(h, w, r0, c0, [(0, 1), (0, 1), (1, 0)]):
        out[r][c] = col
    return out
rule("staircase_fixed_period_three",
     "The lone dot repeats the fixed pattern right, right, down from its own position, drawn in its own "
     "colour, until the next move would leave the grid.",
     gi_period3, tf_period3)


# two dots at slope 1:2 n steps apart; the line between them (not extended) has its floor-rounded
# midpoint recoloured with a separate key dot's colour.
def gi_midpoint(rng):
    h, w = rand_dims(rng)
    g = blank(h, w)
    n = rng.randint(2, 5)
    col, key = rng.sample(COLOURS, 2)
    for _ in range(60):
        r0, c0 = rng.randrange(h), rng.randrange(w)
        r1, c1 = r0 + n, c0 + 2 * n
        if 0 <= r1 < h and 0 <= c1 < w:
            seg = {(r0 + i, c0 + 2 * i) for i in range(n + 1)}
            kr, kc = rng.randrange(h), rng.randrange(w)
            if (kr, kc) not in seg and g[kr][kc] == 0:
                g[r0][c0] = col; g[r1][c1] = col; g[kr][kc] = key
                return g
    return None
def tf_midpoint(g):
    pts = cells(g, lambda v: v != 0)
    cc = Counter(g[r][c] for r, c in pts)
    pair_cols = [c for c, n in cc.items() if n == 2]
    key_cols = [c for c, n in cc.items() if n == 1]
    if len(pair_cols) != 1 or len(key_cols) != 1:
        return None
    col = pair_cols[0]; key = key_cols[0]
    ends = [(r, c) for r, c in pts if g[r][c] == col]
    (r0, c0), (r1, c1) = sorted(ends)
    vr, vc = r1 - r0, c1 - c0
    g0 = gcd(abs(vr), abs(vc))
    if g0 == 0:
        return None
    vr, vc = vr // g0, vc // g0
    n = max(abs(r1 - r0), abs(c1 - c0)) // max(abs(vr), abs(vc))
    seg = [(r0 + i * vr, c0 + i * vc) for i in range(n + 1)]
    out = copy(g)
    for r, c in seg: out[r][c] = col
    mr, mc = seg[len(seg) // 2]
    out[mr][mc] = key
    return out
rule("slope_line_midpoint_marked_by_key",
     "The straight segment between the two same-colour markers is drawn in their colour, then its floor("
     "length/2) midpoint cell is recoloured with the colour of the separate single key dot.",
     gi_midpoint, tf_midpoint)


# dots along the top row each emit a down-right slope 1:2 ray in their own colour.
def gi_parallelrays(rng):
    h, w = rand_dims(rng)
    g = blank(h, w)
    k = rng.randint(2, min(4, w))
    cols = rng.sample(COLOURS, k)
    chosen = rng.sample(range(w), k)
    for c0, col in zip(chosen, cols):
        g[0][c0] = col
    return g
def tf_parallelrays(g):
    h, w = dims(g)
    out = copy(g)
    for c0 in range(w):
        col = g[0][c0]
        if col != 0:
            for r, c in ray_forward(h, w, 0, c0, 1, 2):
                out[r][c] = col
    return out
rule("parallel_rays_from_top_row_dots",
     "Every coloured dot on the top row shoots a one-down-two-right ray in its own colour to the bottom "
     "or side edge.",
     gi_parallelrays, tf_parallelrays)


# the one dot fans out four fixed-ratio forward rays, all its own colour.
def gi_fanfixed(rng):
    h, w = rand_dims(rng)
    g = blank(h, w)
    r0, c0 = rng.randint(0, h - 1), rng.randint(0, w // 2)
    g[r0][c0] = rng.choice(COLOURS)
    return g
def tf_fanfixed(g):
    h, w = dims(g)
    dots = _single_dots(g)
    if len(dots) != 1:
        return None
    r0, c0 = dots[0]
    col = g[r0][c0]
    out = copy(g)
    for dr, dc in ((1, 2), (2, 1), (-1, 2), (-2, 1)):
        for r, c in ray_forward(h, w, r0, c0, dr, dc):
            out[r][c] = col
    return out
rule("dot_fans_four_fixed_slopes",
     "The one dot shoots four rays, in its own colour, at slopes one-down-two-across, two-down-one-"
     "across, one-up-two-across and two-up-one-across, each continued to the grid edge.",
     gi_fanfixed, tf_fanfixed)


# a grey (colour 5) dot plus two single-cell digit markers decode a slope each via a fixed table.
_CODE_SLOPE = {1: (1, 2), 2: (2, 1), 3: (1, 3), 4: (3, 1), 6: (2, 3), 7: (3, 2)}
def gi_codedraysn(rng):
    h, w = rand_dims(rng)
    g = blank(h, w)
    r0, c0 = rng.randint(2, h - 3), rng.randint(2, w - 3)
    g[r0][c0] = 5
    codes = rng.sample(list(_CODE_SLOPE), 2)
    placed = 0
    for code in codes:
        for _ in range(40):
            r, c = rng.randrange(h), rng.randrange(w)
            if g[r][c] == 0 and (r, c) != (r0, c0):
                g[r][c] = code; placed += 1; break
    return g if placed == 2 else None
def tf_codedraysn(g):
    h, w = dims(g)
    dots = [o[0] for o in objects(g, 0) if len(o) == 1 and g[o[0][0]][o[0][1]] == 5]
    if len(dots) != 1:
        return None
    r0, c0 = dots[0]
    out = copy(g)
    for r in range(h):
        for c in range(w):
            if g[r][c] in _CODE_SLOPE:
                dr, dc = _CODE_SLOPE[g[r][c]]
                for rr, cc in ray_forward(h, w, r0, c0, dr, dc):
                    out[rr][cc] = 5
    return out
rule("dot_rays_from_two_digit_codes",
     "The grey (5) dot shoots one ray per digit marker present, each marker's VALUE looked up in a fixed "
     "table (1->1:2, 2->2:1, 3->1:3, 4->3:1, 6->2:3, 7->3:2) to get that ray's slope, every ray drawn grey "
     "to the edge.",
     gi_codedraysn, tf_codedraysn, digits=True)


# a ray of slope 1:2 from the one dot, truncated to a length equal to the count of separate marker cells.
def gi_raylen(rng):
    h, w = rand_dims(rng)
    g = blank(h, w)
    n = rng.randint(2, 6)
    found = _place_dot_with_room(rng, h, w, lambda h, w, r, c: ray_forward(h, w, r, c, 1, 2))
    if found is None:
        return None
    r0, c0, pts = found
    col, mcol = rng.sample(COLOURS, 2)
    g[r0][c0] = col
    shape = random_shape(rng, n)
    sh = max(r for r, _ in shape) + 1; sw = max(c for _, c in shape) + 1
    if sh > h or sw > w:
        return None
    for _ in range(40):
        rr, cc = rng.randint(0, h - sh), rng.randint(0, w - sw)
        abscells = [(rr + r, cc + c) for r, c in shape]
        if all(g[a][b] == 0 and (a, b) not in set(pts) for a, b in abscells):
            for a, b in abscells: g[a][b] = mcol
            return g
    return None
def tf_raylen(g):
    h, w = dims(g)
    dots = _single_dots(g)
    if len(dots) != 1:
        return None
    r0, c0 = dots[0]
    col = g[r0][c0]
    n = sum(1 for row in g for v in row if v not in (0, col))
    pts = ray_forward(h, w, r0, c0, 1, 2)[:max(1, n)]
    out = copy(g)
    for r, c in pts: out[r][c] = col
    return out
rule("ray_length_equals_marker_count",
     "The one dot shoots a one-down-two-right ray in its own colour, stopping after as many cells ("
     "including itself) as there are separate marker cells of the other colour elsewhere on the grid.",
     gi_raylen, tf_raylen)


# a ray of slope 1:2 from the one dot, stopping at (not through) the first already-coloured obstacle cell.
def gi_rayobstacle(rng):
    h, w = rand_dims(rng)
    g = blank(h, w)
    found = _place_dot_with_room(rng, h, w, lambda h, w, r, c: ray_forward(h, w, r, c, 1, 2))
    if found is None:
        return None
    r0, c0, pts = found
    col = rng.choice(COLOURS)
    g[r0][c0] = col
    _noise_shapes(rng, g, {pts[0]}, h, w, k_lo=1, k_hi=2)
    return g
def tf_rayobstacle(g):
    h, w = dims(g)
    dots = _single_dots(g)
    if len(dots) != 1:
        return None
    r0, c0 = dots[0]
    col = g[r0][c0]
    out = copy(g)
    for r, c in ray_forward(h, w, r0, c0, 1, 2):
        if (r, c) != (r0, c0) and g[r][c] != 0:
            break
        out[r][c] = col
    return out
rule("ray_stops_before_obstacle",
     "The one dot shoots a one-down-two-right ray in its own colour, stopping at the last empty cell "
     "before the first already-coloured cell on that path, or at the edge if none is in the way.",
     gi_rayobstacle, tf_rayobstacle)
