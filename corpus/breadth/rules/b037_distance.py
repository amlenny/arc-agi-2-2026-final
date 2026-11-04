# b037_distance.py -- distance and nearest-relations rules: nearest/farthest object recolouring,
# connecting, deleting, ranking and marking; marker-anchored radii and medians; grid-centre and
# border distance maps. Deterministic tie-breaking throughout is reading order (topmost, then
# leftmost) via _reading/_sorted_objs, or ascending index when iterating pairs.
import sys, os
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


def _dsize(rng, lo=6, hi=18, p_big=0.34):
    if rng.random() < p_big:
        return size(rng, 21, 30)
    return size(rng, lo, hi)


def _mdist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _centroid(o):
    rs = [r for r, _ in o]; cs = [c for _, c in o]
    return sum(rs) / len(rs), sum(cs) / len(cs)


def _obj_colour(g, o):
    return g[o[0][0]][o[0][1]]


def _reading(o):
    return min(o)


def _sorted_objs(g, bg=0):
    return sorted(objects(g, bg), key=_reading)


def _min_cell_dist(o1, o2):
    return min(_mdist(p, q) for p in o1 for q in o2)


def _nearest_cells(o1, o2):
    best = None; bd = None
    for p in o1:
        for q in o2:
            d = _mdist(p, q)
            if bd is None or d < bd:
                bd, best = d, (p, q)
    return best, bd


def _unused_colour(g, exclude=()):
    used = {v for row in g for v in row} | set(exclude)
    for c in COLOURS:
        if c not in used:
            return c
    return 9


def _draw_link(out, p, q, col):
    r0, c0 = p; r1, c1 = q
    steps = max(abs(r1 - r0), abs(c1 - c0))
    for s in range(1, steps):
        rr = r0 + round((r1 - r0) * s / steps); cc = c0 + round((c1 - c0) * s / steps)
        if out[rr][cc] == 0:
            out[rr][cc] = col
    return steps


def _scene(rng, k_lo=3, k_hi=6, n_lo=3, n_hi=8, lo=6, hi=18, margin=1, distinct_colours=True, p_big=0.34, exclude=()):
    h, w = _dsize(rng, lo, hi, p_big)
    g = blank(h, w)
    k = rng.randint(k_lo, k_hi)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    pool = [c for c in COLOURS if c not in exclude]
    if distinct_colours:
        if k > len(pool):
            return None
        cols = rng.sample(pool, k)
    else:
        cols = [rng.choice(pool) for _ in range(k)]
    if place_shapes(rng, g, shapes, cols, margin=margin) is None:
        return None
    return g


def _marker_scene(rng, marker_col=1, k_lo=3, k_hi=6, n_lo=3, n_hi=8, lo=7, hi=18, p_big=0.34, distinct=True):
    h, w = _dsize(rng, lo, hi, p_big)
    g = blank(h, w)
    k = rng.randint(k_lo, k_hi)
    pool = [c for c in COLOURS if c != marker_col]
    if distinct:
        if k > len(pool):
            return None
        cols = rng.sample(pool, k)
    else:
        cols = [rng.choice(pool) for _ in range(k)]
    shapes = [[(0, 0)]] + [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    if place_shapes(rng, g, shapes, [marker_col] + cols, margin=1) is None:
        return None
    return g


def _two_marker_scene(rng, m1=1, m2=2, k_lo=3, k_hi=6, n_lo=3, n_hi=8, lo=8, hi=20, p_big=0.34):
    h, w = _dsize(rng, lo, hi, p_big)
    g = blank(h, w)
    k = rng.randint(k_lo, k_hi)
    pool = [c for c in COLOURS if c not in (m1, m2)]
    if k > len(pool):
        return None
    cols = rng.sample(pool, k)
    shapes = [[(0, 0)], [(0, 0)]] + [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    if place_shapes(rng, g, shapes, [m1, m2] + cols, margin=1) is None:
        return None
    return g


# 1 every object recoloured by the colour of its single nearest other object.
def gi1(rng):
    return _scene(rng, k_lo=3, k_hi=6, n_lo=3, n_hi=9, lo=6, hi=18)
def tf1(g):
    objs = _sorted_objs(g)
    if len(objs) < 2:
        return None
    out = copy(g)
    for i, o in enumerate(objs):
        bd = bj = None
        for j, o2 in enumerate(objs):
            if j == i:
                continue
            d = _min_cell_dist(o, o2)
            if bd is None or d < bd:
                bd, bj = d, j
        col = _obj_colour(g, objs[bj])
        for r, c in o:
            out[r][c] = col
    return out
rule("recolour_object_by_nearest_other_object", "Every object is recoloured with the colour of the single other object closest to it.", gi1, tf1)


# 2 the two closest objects in the whole grid are joined by a line.
def gi2(rng):
    return _scene(rng, k_lo=3, k_hi=5, n_lo=3, n_hi=7, lo=9, hi=22, margin=2)
def tf2(g):
    objs = _sorted_objs(g)
    if len(objs) < 2:
        return None
    best = None
    for i in range(len(objs)):
        for j in range(i + 1, len(objs)):
            (p, q), d = _nearest_cells(objs[i], objs[j])
            if best is None or d < best[0]:
                best = (d, p, q)
    _, p, q = best
    out = copy(g); col = _unused_colour(g)
    steps = _draw_link(out, p, q, col)
    return out if steps > 0 else None
rule("join_two_closest_objects_with_line", "The two objects that are closest to each other anywhere in the grid are joined by a straight line.", gi2, tf2)


# 3 the two farthest objects (by centroid) are both recoloured to a fixed colour.
def gi3(rng):
    return _scene(rng, k_lo=3, k_hi=6, n_lo=3, n_hi=8, lo=6, hi=20, exclude=(5,))
def tf3(g):
    objs = _sorted_objs(g)
    if len(objs) < 2:
        return None
    best = None
    for i in range(len(objs)):
        for j in range(i + 1, len(objs)):
            d = _mdist(_centroid(objs[i]), _centroid(objs[j]))
            if best is None or d > best[0]:
                best = (d, i, j)
    _, i, j = best
    out = copy(g)
    for r, c in objs[i] + objs[j]:
        out[r][c] = 5
    return out
rule("recolour_two_farthest_objects", "The two objects whose centres are farthest apart are both recoloured to the same colour.", gi3, tf3)


# 4 every dot moves halfway to its nearest other dot.
def gi4(rng):
    return _dots(rng, k_lo=3, k_hi=6, lo=8, hi=20, min_gap=4)
def _dots(rng, k_lo=3, k_hi=7, lo=6, hi=18, min_gap=2, p_big=0.34, distinct_colours=True, exclude=()):
    h, w = _dsize(rng, lo, hi, p_big)
    g = blank(h, w)
    k = rng.randint(k_lo, k_hi)
    pool = [c for c in COLOURS if c not in exclude]
    if distinct_colours and k > len(pool):
        return None
    pts = []
    for _ in range(400):
        if len(pts) >= k:
            break
        p = (rng.randrange(h), rng.randrange(w))
        if all(_mdist(p, q) >= min_gap for q in pts):
            pts.append(p)
    if len(pts) < k:
        return None
    cols = rng.sample(pool, k) if distinct_colours else [rng.choice(pool) for _ in range(k)]
    for (r, c), col in zip(pts, cols):
        g[r][c] = col
    return g
def tf4(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) < 2:
        return None
    out = blank(*dims(g))
    moved_any = False
    for p in pts:
        col = g[p[0]][p[1]]
        best = None
        for q in pts:
            if q == p:
                continue
            d = _mdist(p, q)
            if best is None or d < best[1]:
                best = (q, d)
        q, _ = best
        hr = p[0] + (q[0] - p[0]) // 2; hc = p[1] + (q[1] - p[1]) // 2
        if (hr, hc) != p:
            moved_any = True
        out[hr][hc] = col
    return out if moved_any else None
rule("dot_moves_halfway_to_nearest_dot", "Every single-cell dot moves halfway (rounding down) toward its nearest other dot.", gi4, tf4)


# 5 every object farther from a marker than the closest one is deleted.
def gi5(rng):
    return _marker_scene(rng, marker_col=1, k_lo=3, k_hi=6, n_lo=3, n_hi=7, lo=8, hi=22)
def tf5(g):
    objs = objects(g, 0)
    marker = [o for o in objs if _obj_colour(g, o) == 1]
    others = [o for o in objs if _obj_colour(g, o) != 1]
    if not marker or len(others) < 2:
        return None
    ranked = sorted(others, key=lambda o: (_min_cell_dist(o, marker[0]), _reading(o)))
    keep = ranked[0]
    out = copy(g)
    for o in others:
        if o is not keep:
            for r, c in o:
                out[r][c] = 0
    return out
rule("delete_objects_beyond_marker_radius", "Only the object closest to the marker cell survives; every other object is deleted.", gi5, tf5)


# 6 the grid is painted with concentric Chebyshev distance bands from its centre.
def gi6(rng):
    h, w = _dsize(rng, lo=7, hi=20, p_big=0.4)
    return blank(h, w)
def tf6(g):
    h, w = dims(g)
    cr, cc = (h - 1) / 2, (w - 1) / 2
    out = blank(h, w)
    for r in range(h):
        for c in range(w):
            d = int(max(abs(r - cr), abs(c - cc)))
            out[r][c] = (d % 9) + 1
    return out
rule("distance_band_rings_from_centre", "Every cell is coloured by its Chebyshev distance from the grid centre, cycling through nine colours.", gi6, tf6, digits=True)


# 7 the object whose centre is closest to the grid centre is highlighted.
def gi7(rng):
    return _scene(rng, k_lo=3, k_hi=6, n_lo=3, n_hi=8, lo=6, hi=20)
def tf7(g):
    h, w = dims(g); centre = ((h - 1) / 2, (w - 1) / 2)
    objs = _sorted_objs(g)
    if len(objs) < 2:
        return None
    best = None
    for i, o in enumerate(objs):
        d = _mdist(_centroid(o), centre)
        if best is None or d < best[0]:
            best = (d, i)
    _, i = best
    col = _unused_colour(g)
    out = copy(g)
    for r, c in objs[i]:
        out[r][c] = col
    return out
rule("mark_closest_object_to_grid_centre", "The object whose centre is nearest the centre of the grid is recoloured.", gi7, tf7)


# 8 every object recoloured by its rank in distance to a marker.
def gi8(rng):
    return _marker_scene(rng, marker_col=1, k_lo=3, k_hi=7, n_lo=3, n_hi=7, lo=8, hi=22)
def tf8(g):
    objs = objects(g, 0)
    marker = [o for o in objs if _obj_colour(g, o) == 1]
    others = sorted([o for o in objs if _obj_colour(g, o) != 1], key=lambda o: (_min_cell_dist(o, marker[0]), _reading(o)))
    if not marker or len(others) < 2:
        return None
    out = copy(g)
    for rank, o in enumerate(others, start=1):
        col = ((rank - 1) % 9) + 1
        for r, c in o:
            out[r][c] = col
    return out
rule("rank_objects_by_distance_to_marker_digits", "Every object is recoloured with its rank (1 = closest) in distance to the marker cell.", gi8, tf8, digits=True)


# 9 a mutual-nearest-neighbour pair of dots is joined by a line.
def gi9(rng):
    h, w = _dsize(rng, lo=10, hi=22, p_big=0.3)
    g = blank(h, w)
    found = False; r0 = c0 = r1 = c1 = gap = 0
    for _ in range(80):
        r0, c0 = rng.randrange(h), rng.randrange(w)
        gap = rng.randint(2, 4)
        if c0 + gap < w:
            r1, c1 = r0, c0 + gap
        elif r0 + gap < h:
            r1, c1 = r0 + gap, c0
        else:
            continue
        found = True; break
    if not found:
        return None
    pool = colours(rng, 2)
    g[r0][c0], g[r1][c1] = pool[0], pool[1]
    noise_cols = [c for c in COLOURS if c not in pool]
    placed = [(r0, c0), (r1, c1)]
    for _ in range(rng.randint(1, 3)):
        for _ in range(100):
            r, c = rng.randrange(h), rng.randrange(w)
            if all(_mdist((r, c), p) >= gap + 3 for p in placed):
                g[r][c] = rng.choice(noise_cols); placed.append((r, c)); break
    return g
def tf9(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) < 2:
        return None
    def nearest(p):
        return min(((q, _mdist(p, q)) for q in pts if q != p), key=lambda x: x[1])[0]
    for p in pts:
        q = nearest(p)
        if nearest(q) == p:
            out = copy(g); col = _unused_colour(g)
            steps = _draw_link(out, p, q, col)
            return out if steps > 0 else None
    return None
rule("mutual_nearest_neighbour_dots_joined", "The pair of dots that are each other's nearest neighbour are joined by a line.", gi9, tf9)


# 10 the object equidistant from two markers is highlighted.
def gi10(rng):
    return _two_marker_scene(rng, m1=1, m2=2, k_lo=3, k_hi=6, n_lo=3, n_hi=7, lo=9, hi=22)
def tf10(g):
    objs = objects(g, 0)
    m1o = [o for o in objs if _obj_colour(g, o) == 1]
    m2o = [o for o in objs if _obj_colour(g, o) == 2]
    others = sorted([o for o in objs if _obj_colour(g, o) not in (1, 2)], key=_reading)
    if not m1o or not m2o or not others:
        return None
    best = None
    for i, o in enumerate(others):
        diff = abs(_min_cell_dist(o, m1o[0]) - _min_cell_dist(o, m2o[0]))
        if best is None or diff < best[0]:
            best = (diff, i)
    _, i = best
    col = _unused_colour(g, exclude=(1, 2))
    out = copy(g)
    for r, c in others[i]:
        out[r][c] = col
    return out
rule("object_equidistant_from_two_markers_highlighted", "The object whose distance to marker 1 is closest to equalling its distance to marker 2 is highlighted.", gi10, tf10)


# 11 the interior of a hollow rectangle is painted by distance to the frame wall.
def gi11(rng):
    h, w = _dsize(rng, lo=9, hi=22, p_big=0.4)
    g = blank(h, w)
    wall = rng.choice(COLOURS)
    pad_r = rng.randint(0, max(0, (h - 5) // 2)); pad_c = rng.randint(0, max(0, (w - 5) // 2))
    r0, c0, r1, c1 = pad_r, pad_c, h - 1 - pad_r, w - 1 - pad_c
    if r1 - r0 < 3 or c1 - c0 < 3:
        return None
    rect(g, r0, c0, r1, c1, wall, fill=False)
    return g
def tf11(g):
    wall = next(v for row in g for v in row if v)
    pts = cells(g, lambda v: v == wall)
    r0 = min(r for r, _ in pts); c0 = min(c for _, c in pts); r1 = max(r for r, _ in pts); c1 = max(c for _, c in pts)
    out = copy(g)
    for r in range(r0 + 1, r1):
        for c in range(c0 + 1, c1):
            d = min(r - r0, r1 - r, c - c0, c1 - c)
            out[r][c] = (d % 9) + 1
    return out
rule("distance_map_from_border_inside_frame", "The interior of the hollow rectangle is filled with each cell's distance to the frame wall.", gi11, tf11, digits=True)


# 12 the background cell farthest from every object is marked.
def gi12(rng):
    return _scene(rng, k_lo=2, k_hi=5, n_lo=3, n_hi=7, lo=8, hi=22)
def tf12(g):
    h, w = dims(g)
    objs = objects(g, 0)
    if not objs:
        return None
    occ = [p for o in objs for p in o]
    best = None
    for r in range(h):
        for c in range(w):
            if g[r][c] != 0:
                continue
            d = min(_mdist((r, c), p) for p in occ)
            if best is None or d > best[0]:
                best = (d, (r, c))
    if best is None:
        return None
    col = _unused_colour(g)
    out = copy(g); br, bc = best[1]; out[br][bc] = col
    return out
rule("cell_farthest_from_all_objects_marked", "The empty cell with the largest distance to the nearest object is marked.", gi12, tf12)


# 13 every object steps one cell toward its nearest same-colour object.
def gi13(rng):
    h, w = _dsize(rng, lo=10, hi=22, p_big=0.3)
    g = blank(h, w)
    cols_ab = colours(rng, 2)
    shapes = [random_shape(rng, rng.randint(3, 6)) for _ in range(4)]
    cols = [cols_ab[0], cols_ab[0], cols_ab[1], cols_ab[1]]
    if place_shapes(rng, g, shapes, cols, margin=2) is None:
        return None
    return g
def tf13(g):
    h, w = dims(g); objs = objects(g, 0)
    if len(objs) < 4:
        return None
    out = blank(h, w)
    for o in objs:
        col = _obj_colour(g, o)
        same = [o2 for o2 in objs if o2 is not o and _obj_colour(g, o2) == col]
        if not same:
            for r, c in o:
                out[r][c] = col
            continue
        target = min(same, key=lambda o2: _mdist(_centroid(o), _centroid(o2)))
        cr, cc = _centroid(o); tr, tc = _centroid(target)
        dr = (tr > cr) - (tr < cr); dc = (tc > cc) - (tc < cc)
        moved = [(r + dr, c + dc) for r, c in o]
        cells_to_use = moved if all(0 <= r < h and 0 <= c < w for r, c in moved) else o
        for r, c in cells_to_use:
            out[r][c] = col
    return out
rule("objects_step_toward_nearest_same_colour_object", "Every object moves one step toward the nearest other object sharing its colour.", gi13, tf13)


# 14 the median object by distance to a marker is highlighted.
def gi14(rng):
    return _marker_scene(rng, marker_col=1, k_lo=3, k_hi=7, n_lo=3, n_hi=7, lo=8, hi=22)
def tf14(g):
    objs = objects(g, 0)
    marker = [o for o in objs if _obj_colour(g, o) == 1]
    others = sorted([o for o in objs if _obj_colour(g, o) != 1], key=lambda o: (_min_cell_dist(o, marker[0]), _reading(o)))
    if not marker or len(others) < 3:
        return None
    mid = others[len(others) // 2]
    col = _unused_colour(g)
    out = copy(g)
    for r, c in mid:
        out[r][c] = col
    return out
rule("median_object_by_distance_to_marker", "The object with the middle-ranked distance to the marker is highlighted.", gi14, tf14)


# 15 the two closest objects swap colours.
def gi15(rng):
    return _scene(rng, k_lo=4, k_hi=7, n_lo=3, n_hi=7, lo=8, hi=22)
def tf15(g):
    objs = _sorted_objs(g)
    if len(objs) < 2:
        return None
    best = None
    for i in range(len(objs)):
        for j in range(i + 1, len(objs)):
            d = _min_cell_dist(objs[i], objs[j])
            if best is None or d < best[0]:
                best = (d, i, j)
    _, i, j = best
    ci = _obj_colour(g, objs[i]); cj = _obj_colour(g, objs[j])
    out = copy(g)
    for r, c in objs[i]:
        out[r][c] = cj
    for r, c in objs[j]:
        out[r][c] = ci
    return out
rule("nearest_pair_different_colours_swap_colours", "The two closest objects in the grid swap colours with each other.", gi15, tf15)


# 16 the farthest pair among objects sharing the most common repeated colour is connected.
def gi16(rng):
    h, w = _dsize(rng, lo=10, hi=24, p_big=0.3)
    g = blank(h, w)
    col_a = rng.choice(COLOURS)
    other_pool = [c for c in COLOURS if c != col_a]
    n_a = rng.randint(2, 4); n_other = rng.randint(0, 2)
    shapes = [random_shape(rng, rng.randint(3, 6)) for _ in range(n_a + n_other)]
    cols = [col_a] * n_a + [rng.choice(other_pool) for _ in range(n_other)]
    if place_shapes(rng, g, shapes, cols, margin=2) is None:
        return None
    return g
def tf16(g):
    objs = objects(g, 0)
    cnt = Counter(_obj_colour(g, o) for o in objs)
    cands = [c for c, n in cnt.items() if n >= 2]
    if not cands:
        return None
    col = min(cands)
    group = [o for o in objs if _obj_colour(g, o) == col]
    best = None
    for i in range(len(group)):
        for j in range(i + 1, len(group)):
            d = _mdist(_centroid(group[i]), _centroid(group[j]))
            if best is None or d > best[0]:
                best = (d, i, j)
    _, i, j = best
    (p, q), _d = _nearest_cells(group[i], group[j])
    out = copy(g); link = _unused_colour(g)
    steps = _draw_link(out, p, q, link)
    return out if steps > 0 else None
rule("farthest_same_colour_pair_connected", "The two farthest-apart objects sharing the grid's most-repeated colour are joined by a line.", gi16, tf16)


# 17 objects are output as a single row, ordered by distance to the top-left corner.
def gi17(rng):
    return _scene(rng, k_lo=3, k_hi=6, n_lo=3, n_hi=8, lo=6, hi=20)
def tf17(g):
    objs = sorted(objects(g, 0), key=lambda o: (min(_mdist(p, (0, 0)) for p in o), _reading(o)))
    if len(objs) < 2:
        return None
    return [[_obj_colour(g, o) for o in objs]]
rule("objects_ranked_by_distance_to_corner", "Output one row listing every object's colour, ordered by increasing distance to the top-left corner.", gi17, tf17)


# 18 the two closest objects both take a fixed shared colour.
def gi18(rng):
    return _scene(rng, k_lo=3, k_hi=6, n_lo=3, n_hi=8, lo=6, hi=20, exclude=(7,))
def tf18(g):
    objs = _sorted_objs(g)
    if len(objs) < 2:
        return None
    best = None
    for i in range(len(objs)):
        for j in range(i + 1, len(objs)):
            d = _min_cell_dist(objs[i], objs[j])
            if best is None or d < best[0]:
                best = (d, i, j)
    _, i, j = best
    out = copy(g)
    for r, c in objs[i] + objs[j]:
        out[r][c] = 7
    return out
rule("smallest_gap_pair_merged_colour", "The two objects separated by the smallest gap are both recoloured the same fixed colour.", gi18, tf18)


# 19 the marker cell encodes how many objects lie within a radius of it.
def gi19(rng):
    return _marker_scene(rng, marker_col=1, k_lo=3, k_hi=7, n_lo=3, n_hi=7, lo=8, hi=22)
def tf19(g):
    h, w = dims(g); objs = objects(g, 0)
    marker = [o for o in objs if _obj_colour(g, o) == 1]
    others = [o for o in objs if _obj_colour(g, o) != 1]
    if not marker or not others:
        return None
    radius = max(2, (h + w) // 6)
    count = sum(1 for o in others if _min_cell_dist(o, marker[0]) <= radius)
    out = copy(g)
    mr, mc = marker[0][0]; new = ((count % 9) + 1)
    if new == g[mr][mc]:
        return None
    out[mr][mc] = new
    return out
rule("marker_recoloured_by_count_within_radius", "The marker cell is recoloured to the count of objects within a fixed radius of it.", gi19, tf19, digits=True)


# 20 objects are split into two colours by whether they are nearer or farther than the median.
def gi20(rng):
    return _marker_scene(rng, marker_col=1, k_lo=4, k_hi=7, n_lo=3, n_hi=7, lo=9, hi=22)
def tf20(g):
    objs = objects(g, 0)
    marker = [o for o in objs if _obj_colour(g, o) == 1]
    others = [o for o in objs if _obj_colour(g, o) != 1]
    if not marker or len(others) < 2:
        return None
    dists = sorted(_min_cell_dist(o, marker[0]) for o in others)
    median = dists[len(dists) // 2]
    near_col = _unused_colour(g); far_col = _unused_colour(g, exclude=(near_col,))
    out = copy(g)
    for o in others:
        d = _min_cell_dist(o, marker[0])
        col = near_col if d <= median else far_col
        for r, c in o:
            out[r][c] = col
    return out
rule("objects_split_near_far_of_marker", "Objects nearer than the median distance to the marker take one colour; farther objects take another.", gi20, tf20)


# 21 the object farthest from the marker is deleted.
def gi21(rng):
    return _marker_scene(rng, marker_col=1, k_lo=3, k_hi=6, n_lo=3, n_hi=7, lo=8, hi=22)
def tf21(g):
    objs = objects(g, 0)
    marker = [o for o in objs if _obj_colour(g, o) == 1]
    others = [o for o in objs if _obj_colour(g, o) != 1]
    if not marker or len(others) < 2:
        return None
    far = sorted(others, key=lambda o: (_min_cell_dist(o, marker[0]), _reading(o)))[-1]
    out = copy(g)
    for r, c in far:
        out[r][c] = 0
    return out
rule("farthest_object_from_marker_deleted", "The object farthest from the marker cell is deleted.", gi21, tf21)


# 22 every object recoloured by its rank in distance to the grid centre.
def gi22(rng):
    return _scene(rng, k_lo=3, k_hi=7, n_lo=3, n_hi=7, lo=8, hi=22)
def tf22(g):
    h, w = dims(g); centre = ((h - 1) / 2, (w - 1) / 2)
    objs = sorted(objects(g, 0), key=lambda o: (_mdist(_centroid(o), centre), _reading(o)))
    if len(objs) < 2:
        return None
    out = copy(g)
    for rank, o in enumerate(objs, start=1):
        col = ((rank - 1) % 9) + 1
        for r, c in o:
            out[r][c] = col
    return out
rule("objects_recoloured_by_distance_rank_to_centre_digits", "Every object is recoloured with its rank in distance to the grid centre.", gi22, tf22, digits=True)


# 23 a marked dot moves to the midpoint between its two nearest other dots.
def gi23(rng):
    h, w = _dsize(rng, lo=9, hi=22, p_big=0.3)
    g = blank(h, w)
    anchor_cols = colours(rng, 3, exclude=(0, 1))
    pts = []
    for _ in range(200):
        if len(pts) >= 4:
            break
        p = (rng.randrange(h), rng.randrange(w))
        if all(_mdist(p, q) >= 3 for q in pts):
            pts.append(p)
    if len(pts) < 4:
        return None
    g[pts[0][0]][pts[0][1]] = 1
    for p, c in zip(pts[1:], anchor_cols):
        g[p[0]][p[1]] = c
    ds = sorted(_mdist(pts[0], p) for p in pts[1:])
    if ds[0] == ds[1]:
        return None
    return g
def tf23(g):
    pts = cells(g, lambda v: v != 0)
    mover = next((p for p in pts if g[p[0]][p[1]] == 1), None)
    if mover is None:
        return None
    anchors = [p for p in pts if p != mover]
    if len(anchors) < 2:
        return None
    anchors_sorted = sorted(anchors, key=lambda p: (_mdist(mover, p), p))
    a, b = anchors_sorted[0], anchors_sorted[1]
    mr, mc = (a[0] + b[0]) // 2, (a[1] + b[1]) // 2
    if (mr, mc) == mover:
        return None
    out = copy(g)
    out[mover[0]][mover[1]] = 0
    out[mr][mc] = 1
    return out
rule("mover_dot_to_midpoint_of_two_nearest_anchors", "The marked dot moves to the midpoint between the two anchor dots nearest to it.", gi23, tf23)


# 24 of the closest pair, the smaller object takes the colour of the bigger one.
def gi24(rng):
    return _scene(rng, k_lo=3, k_hi=6, n_lo=2, n_hi=9, lo=6, hi=20)
def tf24(g):
    objs = _sorted_objs(g)
    if len(objs) < 2:
        return None
    best = None
    for i in range(len(objs)):
        for j in range(i + 1, len(objs)):
            d = _min_cell_dist(objs[i], objs[j])
            if best is None or d < best[0]:
                best = (d, i, j)
    _, i, j = best
    oi, oj = objs[i], objs[j]
    if len(oi) == len(oj):
        return None
    smaller, bigger = (oi, oj) if len(oi) < len(oj) else (oj, oi)
    col = _obj_colour(g, bigger)
    out = copy(g)
    for r, c in smaller:
        out[r][c] = col
    return out
rule("closest_pair_smaller_absorbs_colour", "Of the two closest objects, the smaller one takes the colour of the bigger one.", gi24, tf24)


# 25 every object takes the colour of whichever of two markers is nearer to it.
def gi25(rng):
    return _two_marker_scene(rng, m1=1, m2=2, k_lo=3, k_hi=6, n_lo=3, n_hi=7, lo=9, hi=22)
def tf25(g):
    objs = objects(g, 0)
    m1o = [o for o in objs if _obj_colour(g, o) == 1]
    m2o = [o for o in objs if _obj_colour(g, o) == 2]
    others = [o for o in objs if _obj_colour(g, o) not in (1, 2)]
    if not m1o or not m2o or not others:
        return None
    out = copy(g)
    for o in others:
        d1 = _min_cell_dist(o, m1o[0]); d2 = _min_cell_dist(o, m2o[0])
        col = 1 if d1 <= d2 else 2
        for r, c in o:
            out[r][c] = col
    return out
rule("objects_recoloured_by_closer_of_two_markers", "Every object takes the colour of whichever of the two markers is nearer to it.", gi25, tf25)


# 26 a reserved corner cell encodes the smallest pairwise distance between any two objects.
def gi26(rng):
    g = _scene(rng, k_lo=3, k_hi=6, n_lo=3, n_hi=7, lo=8, hi=22)
    if g is None or g[0][0] != 0:
        return None
    return g
def tf26(g):
    objs = _sorted_objs(g)
    if len(objs) < 2:
        return None
    best = None
    for i in range(len(objs)):
        for j in range(i + 1, len(objs)):
            d = _min_cell_dist(objs[i], objs[j])
            if best is None or d < best:
                best = d
    out = copy(g)
    out[0][0] = ((best - 1) % 9) + 1
    return out
rule("closest_pair_distance_encoded_in_marker_digits", "The top-left cell is recoloured to encode the smallest distance between any two objects.", gi26, tf26, digits=True)


# 27 a reserved corner cell encodes how many objects lie within a radius of the grid centre.
def gi27(rng):
    g = _scene(rng, k_lo=2, k_hi=7, n_lo=3, n_hi=7, lo=8, hi=24)
    if g is None or g[0][0] != 0:
        return None
    return g
def tf27(g):
    h, w = dims(g); centre = ((h - 1) / 2, (w - 1) / 2)
    objs = objects(g, 0)
    if not objs:
        return None
    radius = max(2, (h + w) // 4)
    count = sum(1 for o in objs if _mdist(_centroid(o), centre) <= radius)
    out = copy(g)
    out[0][0] = (count % 9) + 1
    return out
rule("centre_radius_object_count_encoded_in_marker_digits", "The top-left cell is recoloured to encode how many objects lie within a radius of the grid centre.", gi27, tf27, digits=True)


# 28 at each corner, the single object cell nearest to it is marked.
def gi28(rng):
    return _scene(rng, k_lo=3, k_hi=6, n_lo=4, n_hi=9, lo=10, hi=24)
def tf28(g):
    h, w = dims(g); corners = [(0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)]
    objs = objects(g, 0)
    if not objs:
        return None
    allcells = [p for o in objs for p in o]
    col = _unused_colour(g)
    out = copy(g); changed = False
    for corner in corners:
        best = min(allcells, key=lambda p: (_mdist(p, corner), p))
        if out[best[0]][best[1]] != col:
            out[best[0]][best[1]] = col; changed = True
    return out if changed else None
rule("mark_nearest_object_cell_to_each_corner", "For each of the four corners, the single object cell nearest to it is recoloured.", gi28, tf28)


# 29 the two farthest objects get their bounding boxes outlined.
def gi29(rng):
    return _scene(rng, k_lo=3, k_hi=5, n_lo=3, n_hi=7, lo=10, hi=24, margin=2)
def tf29(g):
    h, w = dims(g)
    objs = _sorted_objs(g)
    if len(objs) < 2:
        return None
    best = None
    for i in range(len(objs)):
        for j in range(i + 1, len(objs)):
            d = _mdist(_centroid(objs[i]), _centroid(objs[j]))
            if best is None or d > best[0]:
                best = (d, i, j)
    _, i, j = best
    col = _unused_colour(g)
    out = copy(g); changed = False
    for o in (objs[i], objs[j]):
        r0, c0, r1, c1 = bbox(o)
        r0 = max(0, r0 - 1); c0 = max(0, c0 - 1); r1 = min(h - 1, r1 + 1); c1 = min(w - 1, c1 + 1)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if (r in (r0, r1) or c in (c0, c1)) and out[r][c] == 0:
                    out[r][c] = col; changed = True
    return out if changed else None
rule("farthest_object_pair_bbox_outlined", "The two objects whose centres are farthest apart each get their bounding box outlined.", gi29, tf29)


# 30 a dot slides along its row until it is adjacent to its nearest neighbour.
def gi30(rng):
    h, w = _dsize(rng, lo=10, hi=24, p_big=0.3)
    g = blank(h, w)
    r = rng.randrange(h)
    gap = rng.randint(4, min(10, w - 1))
    c0 = rng.randint(0, w - 1 - gap); c1 = c0 + gap
    cols = colours(rng, 2)
    g[r][c0], g[r][c1] = cols[0], cols[1]
    others = [c for c in COLOURS if c not in cols]
    for _ in range(rng.randint(0, 2)):
        for _ in range(60):
            rr, cc = rng.randrange(h), rng.randrange(w)
            if _mdist((rr, cc), (r, c0)) > gap + 3 and _mdist((rr, cc), (r, c1)) > gap + 3:
                g[rr][cc] = rng.choice(others); break
    return g
def tf30(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) < 2:
        return None
    best = None
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            d = _mdist(pts[i], pts[j])
            if best is None or d < best[0]:
                best = (d, pts[i], pts[j])
    d, p, q = best
    if d <= 1:
        return None
    out = copy(g); colp = g[p[0]][p[1]]
    if p[0] == q[0]:
        newc = q[1] - 1 if q[1] > p[1] else q[1] + 1
        out[p[0]][p[1]] = 0; out[p[0]][newc] = colp
    elif p[1] == q[1]:
        newr = q[0] - 1 if q[0] > p[0] else q[0] + 1
        out[p[0]][p[1]] = 0; out[newr][p[1]] = colp
    else:
        return None
    return out
rule("dot_slides_adjacent_to_nearest_dot", "The globally closest dot slides along its row or column until it is adjacent to its nearest neighbour.", gi30, tf30)


# 31 the marker encodes how many objects are closer to it than average.
def gi31(rng):
    return _marker_scene(rng, marker_col=1, k_lo=3, k_hi=7, n_lo=3, n_hi=7, lo=9, hi=22)
def tf31(g):
    objs = objects(g, 0)
    marker = [o for o in objs if _obj_colour(g, o) == 1]
    others = [o for o in objs if _obj_colour(g, o) != 1]
    if not marker or len(others) < 2:
        return None
    ds = [_min_cell_dist(o, marker[0]) for o in others]
    avg = sum(ds) / len(ds)
    count = sum(1 for d in ds if d < avg)
    out = copy(g); mr, mc = marker[0][0]; new = (count % 9) + 1
    if new == g[mr][mc]:
        return None
    out[mr][mc] = new
    return out
rule("count_objects_closer_than_average_distance_digits", "The marker cell is recoloured to the count of objects closer to it than the average distance.", gi31, tf31, digits=True)


# 32 every object recoloured by the majority colour of its two nearest neighbours.
def gi32(rng):
    return _scene(rng, k_lo=4, k_hi=7, n_lo=3, n_hi=7, lo=9, hi=22, distinct_colours=False)
def tf32(g):
    objs = _sorted_objs(g)
    if len(objs) < 3:
        return None
    out = copy(g); changed = False
    for i, o in enumerate(objs):
        dists = sorted((_min_cell_dist(o, o2), j) for j, o2 in enumerate(objs) if j != i)
        if len(dists) < 2:
            continue
        cols = [_obj_colour(g, objs[dists[0][1]]), _obj_colour(g, objs[dists[1][1]])]
        newcol = cols[0] if cols[0] == cols[1] else min(cols)
        if newcol != _obj_colour(g, o):
            changed = True
        for r, c in o:
            out[r][c] = newcol
    return out if changed else None
rule("nearest_neighbour_colour_majority_vote", "Every object is recoloured by the majority (or smaller, if tied) colour among its two nearest neighbours.", gi32, tf32)


# 33 every object recoloured by the colour of its second-nearest other object.
def gi33(rng):
    return _scene(rng, k_lo=4, k_hi=7, n_lo=3, n_hi=7, lo=9, hi=22)
def tf33(g):
    objs = _sorted_objs(g)
    if len(objs) < 3:
        return None
    out = copy(g)
    for i, o in enumerate(objs):
        dists = sorted((_min_cell_dist(o, o2), j) for j, o2 in enumerate(objs) if j != i)
        second = dists[1][1]
        col = _obj_colour(g, objs[second])
        for r, c in o:
            out[r][c] = col
    return out
rule("second_nearest_object_colour_assigned", "Every object is recoloured with the colour of its second-nearest other object, skipping its very nearest.", gi33, tf33)


# 34 objects are coloured by the parity of their distance to the marker.
def gi34(rng):
    return _marker_scene(rng, marker_col=1, k_lo=3, k_hi=7, n_lo=1, n_hi=1, lo=8, hi=22, distinct=False)
def tf34(g):
    objs = objects(g, 0)
    marker = [o for o in objs if _obj_colour(g, o) == 1]
    others = [o for o in objs if _obj_colour(g, o) != 1]
    if not marker or len(others) < 2:
        return None
    even_col = _unused_colour(g); odd_col = _unused_colour(g, exclude=(even_col,))
    out = copy(g)
    for o in others:
        d = _min_cell_dist(o, marker[0])
        col = even_col if d % 2 == 0 else odd_col
        for r, c in o:
            out[r][c] = col
    return out
rule("dots_coloured_by_parity_of_distance_to_marker", "Every dot takes one colour if its distance to the marker is even, another if it is odd.", gi34, tf34)


# 35 the object closest to the average position of all objects is highlighted.
def gi35(rng):
    return _scene(rng, k_lo=3, k_hi=7, n_lo=3, n_hi=7, lo=8, hi=22)
def tf35(g):
    objs = _sorted_objs(g)
    if len(objs) < 3:
        return None
    cents = [_centroid(o) for o in objs]
    avg = (sum(c[0] for c in cents) / len(cents), sum(c[1] for c in cents) / len(cents))
    best = None
    for i, c in enumerate(cents):
        d = _mdist(c, avg)
        if best is None or d < best[0]:
            best = (d, i)
    _, i = best
    col = _unused_colour(g)
    out = copy(g)
    for r, c in objs[i]:
        out[r][c] = col
    return out
rule("object_nearest_to_average_position_highlighted", "The object closest to the average centre of all objects is highlighted.", gi35, tf35)


# 36 objects farther than the median distance from the shared centroid are deleted.
def gi36(rng):
    return _scene(rng, k_lo=4, k_hi=7, n_lo=3, n_hi=7, lo=9, hi=22)
def tf36(g):
    objs = _sorted_objs(g)
    if len(objs) < 4:
        return None
    cents = [_centroid(o) for o in objs]
    avg = (sum(c[0] for c in cents) / len(cents), sum(c[1] for c in cents) / len(cents))
    dists = [_mdist(c, avg) for c in cents]
    med = sorted(dists)[len(dists) // 2]
    out = copy(g); changed = False
    for o, d in zip(objs, dists):
        if d > med:
            for r, c in o:
                out[r][c] = 0
            changed = True
    return out if changed else None
rule("objects_beyond_median_distance_from_centroid_deleted", "Objects farther than the median distance from the shared centroid of all objects are deleted.", gi36, tf36)


# 37 the object with the largest average distance to every other object is deleted.
def gi37(rng):
    return _scene(rng, k_lo=4, k_hi=7, n_lo=3, n_hi=7, lo=9, hi=22)
def tf37(g):
    objs = _sorted_objs(g)
    if len(objs) < 3:
        return None
    best = None
    for i, o in enumerate(objs):
        total = sum(_mdist(_centroid(o), _centroid(o2)) for j, o2 in enumerate(objs) if j != i)
        avgd = total / (len(objs) - 1)
        if best is None or avgd > best[0]:
            best = (avgd, i)
    _, i = best
    out = copy(g)
    for r, c in objs[i]:
        out[r][c] = 0
    return out
rule("outlier_object_farthest_from_all_others_deleted", "The object with the largest average distance to every other object is deleted.", gi37, tf37)


# 38 the object with the smallest total distance to every other object is highlighted.
def gi38(rng):
    return _scene(rng, k_lo=4, k_hi=7, n_lo=3, n_hi=7, lo=9, hi=22)
def tf38(g):
    objs = _sorted_objs(g)
    if len(objs) < 3:
        return None
    best = None
    for i, o in enumerate(objs):
        total = sum(_mdist(_centroid(o), _centroid(o2)) for j, o2 in enumerate(objs) if j != i)
        if best is None or total < best[0]:
            best = (total, i)
    _, i = best
    col = _unused_colour(g)
    out = copy(g)
    for r, c in objs[i]:
        out[r][c] = col
    return out
rule("object_with_min_total_distance_to_others_highlighted", "The most central object, with the smallest total distance to every other object, is highlighted.", gi38, tf38)


# 39 an isolated single-cell dot takes the colour of the object nearest to it.
def gi39(rng):
    h, w = _dsize(rng, lo=9, hi=22, p_big=0.3)
    g = blank(h, w)
    k = rng.randint(2, 5)
    cols = colours(rng, k)
    shapes = [random_shape(rng, rng.randint(3, 7)) for _ in range(k)]
    if place_shapes(rng, g, shapes, cols, margin=2) is None:
        return None
    dotcol = _unused_colour(g)
    h2, w2 = dims(g)
    for _ in range(100):
        r, c = rng.randrange(h2), rng.randrange(w2)
        if g[r][c] == 0:
            occ = [p for o in objects(g, 0) for p in o]
            if all(_mdist((r, c), p) >= 2 for p in occ):
                g[r][c] = dotcol
                return g
    return None
def tf39(g):
    objs = objects(g, 0)
    dotobjs = [o for o in objs if len(o) == 1]
    bigobjs = [o for o in objs if len(o) > 1]
    if not dotobjs or not bigobjs:
        return None
    dot = dotobjs[0][0]
    best = min(bigobjs, key=lambda o: (_min_cell_dist([dot], o), _reading(o)))
    col = _obj_colour(g, best)
    out = copy(g)
    out[dot[0]][dot[1]] = col
    return out
rule("isolated_dot_takes_colour_of_nearest_object", "The one isolated single-cell dot takes the colour of the larger object nearest to it.", gi39, tf39)


# 40 the two closest cells belonging to the two closest objects are each marked.
def gi40(rng):
    return _scene(rng, k_lo=3, k_hi=6, n_lo=3, n_hi=7, lo=8, hi=22, margin=2)
def tf40(g):
    objs = _sorted_objs(g)
    if len(objs) < 2:
        return None
    best = None
    for i in range(len(objs)):
        for j in range(i + 1, len(objs)):
            (p, q), d = _nearest_cells(objs[i], objs[j])
            if best is None or d < best[0]:
                best = (d, p, q)
    _, p, q = best
    col = _unused_colour(g)
    out = copy(g)
    out[p[0]][p[1]] = col; out[q[0]][q[1]] = col
    return out
rule("two_nearest_objects_corner_markers", "The nearest-approach cell on each of the two closest objects is marked with the same highlight colour.", gi40, tf40)
