# b058_predicates.py -- 40 rules: keep/delete/recolour objects by a TWO-PROPERTY predicate
# (AND, OR or XOR of two object properties: size, border-touch, shape (box/hole/tall/wide/square),
# symmetry, colour uniqueness, neighbour count/size, twin-shape match, key-colour/marker position).
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


# ---------------------------------------------------------------- shared helpers
def _touches_border(obj, h, w):
    return any(r == 0 or r == h - 1 or c == 0 or c == w - 1 for r, c in obj)

def _bbdims(obj):
    r0, c0, r1, c1 = bbox(obj)
    return r1 - r0 + 1, c1 - c0 + 1

def _is_tall(obj):
    hh, ww = _bbdims(obj); return hh > ww

def _is_wide(obj):
    hh, ww = _bbdims(obj); return ww > hh

def _is_box(obj):
    hh, ww = _bbdims(obj)
    return hh >= 2 and ww >= 2 and len(obj) == 2 * hh + 2 * ww - 4

def _bg_reachable(g, bg=0):
    h, w = dims(g); seen = set(); st = []
    for r in range(h):
        for c in (0, w - 1):
            if g[r][c] == bg: st.append((r, c))
    for c in range(w):
        for r in (0, h - 1):
            if g[r][c] == bg: st.append((r, c))
    while st:
        r, c = st.pop()
        if (r, c) in seen: continue
        seen.add((r, c))
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w and g[nr][nc] == bg and (nr, nc) not in seen:
                st.append((nr, nc))
    return seen

def _has_hole(g, obj, reach, bg=0):
    r0, c0, r1, c1 = bbox(obj)
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if g[r][c] == bg and (r, c) not in reach:
                return True
    return False

def _adjacent(a, b):
    aset = set(a)
    for r, c in b:
        if (r - 1, c) in aset or (r + 1, c) in aset or (r, c - 1) in aset or (r, c + 1) in aset:
            return True
    return False

def _neighbours(obj, obs):
    return [o for o in obs if o is not obj and _adjacent(obj, o)]

def _shape_key(obj):
    r0, c0, _, _ = bbox(obj)
    return frozenset((r - r0, c - c0) for r, c in obj)

def _is_symmetric(obj):
    r0, c0, r1, c1 = bbox(obj); s = frozenset(obj)
    mv = frozenset((r, c0 + c1 - c) for r, c in obj)
    mh = frozenset((r0 + r1 - r, c) for r, c in obj)
    return mv == s or mh == s

def _centroid(obj):
    rs = [r for r, _ in obj]; cs = [c for _, c in obj]
    return sum(rs) / len(rs), sum(cs) / len(cs)

def _colour(g, obj):
    r, c = obj[0]; return g[r][c]

def _scene(rng, k_lo=4, k_hi=8, n_lo=2, n_hi=12, lo=10, hi=28, margin=1, exclude=()):
    h, w = size(rng, lo, hi); g = blank(h, w)
    k = rng.randint(k_lo, k_hi)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    pool = [c for c in COLOURS if c not in exclude]
    cols = [rng.choice(pool) for _ in range(k)]
    if place_shapes(rng, g, shapes, cols, margin=margin) is None:
        return None
    return g

def _scene_bh(rng, lo=12, hi=28, k_lo=4, k_hi=7):
    """mix of solid blobs, thin 2-row boxes (box, no hole), full rings (box & hole), hole-blobs (hole, no box)."""
    h, w = size(rng, lo, hi); g = blank(h, w)
    k = rng.randint(k_lo, k_hi)
    shapes = []
    for _ in range(k):
        kind = rng.choice(('solid', 'ring3', 'ring2', 'holeblob'))
        if kind == 'solid':
            shapes.append(random_shape(rng, rng.randint(3, 7)))
        elif kind == 'ring3':
            hh = rng.randint(3, 5); ww = rng.randint(3, 5)
            shapes.append([(r, c) for r in range(hh) for c in range(ww) if r in (0, hh - 1) or c in (0, ww - 1)])
        elif kind == 'ring2':
            ww = rng.randint(3, 5)
            shapes.append([(r, c) for r in range(2) for c in range(ww)])
        else:
            base = random_shape(rng, rng.randint(9, 14))
            r0, c0, r1, c1 = bbox(base); baseset = set(base)
            interior = [(r, c) for r, c in base if r0 < r < r1 and c0 < c < c1
                        and all((r + dr, c + dc) in baseset for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
            if interior:
                rc = rng.choice(interior); base = [p for p in base if p != rc]
            shapes.append(base)
    cols = [rng.choice(COLOURS) for _ in shapes]
    if place_shapes(rng, g, shapes, cols, margin=1) is None:
        return None
    return g

def _mixed(g, pred):
    if g is None: return None
    obs = objects(g, 0)
    if len(obs) < 3: return None
    vals = [pred(o, g, obs) for o in obs]
    if all(vals) or not any(vals): return None
    return g

def _apply(g, obs, pred, mode, colour=None):
    out = copy(g)
    for o in obs:
        m = pred(o)
        if mode == 'keep' and not m:
            for r, c in o: out[r][c] = 0
        elif mode == 'delete' and m:
            for r, c in o: out[r][c] = 0
        elif mode == 'recolour' and m:
            for r, c in o: out[r][c] = colour
    return out


# ============================================================ 1
def _p1(o, g, obs): return len(o) > 6 and _touches_border(o, *dims(g))
def gi1(rng): return _mixed(_scene(rng, 5, 9, 3, 14, 12, 28), _p1)
def tf1(g): return _apply(g, objects(g, 0), lambda o: _p1(o, g, None), 'keep')
rule("keep_large_border_touching_objects",
     "Keep only objects that are large (more than 6 cells) AND touch the grid border; every other object is deleted.",
     gi1, tf1)


# ============================================================ 2
def _p2(o, g, obs): return _is_box(o) or (lambda r: _has_hole(g, o, r))(_bg_reachable(g))
def gi2(rng): return _mixed(_scene_bh(rng), _p2)
def tf2(g):
    reach = _bg_reachable(g)
    pred = lambda o: _is_box(o) or _has_hole(g, o, reach)
    return _apply(g, objects(g, 0), pred, 'recolour', 6)
rule("recolour_box_or_hole_objects",
     "Recolour to 6 every object that is a hollow rectangle outline OR has an enclosed interior hole (background cell not reachable from the grid edge); other objects are unchanged.",
     gi2, tf2)


# ============================================================ 3
def _p3(o, g, obs): return _is_tall(o) and _colour(g, o) != 5
def gi3(rng): return _mixed(_scene(rng, 5, 9, 3, 12, 10, 28), _p3)
def tf3(g): return _apply(g, objects(g, 0), lambda o: _p3(o, g, None), 'delete')
rule("delete_tall_non_grey_objects",
     "Delete every object whose bounding box is taller than it is wide AND whose colour is not grey (5); grey and non-tall objects are kept.",
     gi3, tf3)


# ============================================================ 4
def _largest_of_colour(o, g, obs):
    col = _colour(g, o); same = [x for x in obs if _colour(g, x) == col]
    return len(o) >= max(len(x) for x in same)
def _is_global_largest(o, g, obs):
    return len(o) >= max(len(x) for x in obs)
def _p4(o, g, obs): return _largest_of_colour(o, g, obs) and not _is_global_largest(o, g, obs)
def gi4(rng): return _mixed(_scene(rng, 5, 9, 2, 12, 10, 28), _p4)
def tf4(g):
    obs = objects(g, 0)
    return _apply(g, obs, lambda o: _p4(o, g, obs), 'keep')
rule("keep_largest_per_colour_not_overall",
     "Keep only objects that are the largest (by cell count, ties included) among objects of their own colour AND are not the single largest object in the grid; delete every other object.",
     gi4, tf4)


# ============================================================ 5
def gi5(rng):
    g = _scene(rng, 5, 9, 3, 12, 12, 28, margin=1)
    if g is None: return None
    h, w = dims(g)
    if g[0][0] != 0 or g[0][1] != 0: return None
    keycol = rng.choice(COLOURS); bar = rng.randint(2, 8)
    g[0][0] = keycol; g[0][1] = bar
    obs = [o for o in objects(g, 0) if (0, 0) not in o and (0, 1) not in o]
    pred = lambda o: _colour(g, o) == keycol and len(o) > bar
    return _mixed2(g, obs, pred)
def _mixed2(g, obs, pred):
    if len(obs) < 3: return None
    vals = [pred(o) for o in obs]
    if all(vals) or not any(vals): return None
    return g
def tf5(g):
    keycol = g[0][0]; bar = g[0][1]
    obs = [o for o in objects(g, 0) if (0, 0) not in o and (0, 1) not in o]
    pred = lambda o: _colour(g, o) == keycol and len(o) > bar
    return _apply(g, obs, pred, 'keep')
rule("keep_key_colour_over_bar_objects",
     "Cell (0,0) is a key colour and cell (0,1) holds a bar digit. Keep only objects whose colour matches the key AND whose cell count exceeds the bar digit; delete the rest.",
     gi5, tf5)


# ============================================================ 6
def _p6(o, g, obs):
    nb = _neighbours(o, obs)
    return len(nb) == 1 and len(o) < len(nb[0])
def gi6(rng): return _mixed(_scene(rng, 6, 10, 2, 10, 12, 28, margin=0), _p6)
def tf6(g):
    obs = objects(g, 0)
    return _apply(g, obs, lambda o: _p6(o, g, obs), 'recolour', 7)
rule("recolour_single_neighbour_smaller_objects",
     "Recolour to 7 every object that touches exactly one other object AND is smaller (fewer cells) than that single neighbour; all other objects are unchanged.",
     gi6, tf6)


# ============================================================ 7
def gi7(rng):
    h, w = size(rng, 12, 28); g = blank(h, w)
    shapes = []
    hh, ww = 2, 3; shapes.append([(r, c) for r in range(hh) for c in range(ww)])          # symmetric, even (6)
    hh, ww = 3, 3; shapes.append([(r, c) for r in range(hh) for c in range(ww)])          # symmetric, odd (9)
    for _ in range(rng.randint(2, 4)):
        for _try in range(8):
            s = random_shape(rng, rng.randint(4, 9))
            if not _is_symmetric(s):
                shapes.append(s); break
    if len(shapes) < 3: return None
    cols = [rng.choice(COLOURS) for _ in shapes]
    if place_shapes(rng, g, shapes, cols, margin=1) is None: return None
    obs = objects(g, 0)
    if len(obs) < 3: return None
    return g
def tf7(g):
    out = copy(g)
    for o in objects(g, 0):
        if _is_symmetric(o):
            col = 1 if len(o) % 2 == 0 else 2
            for r, c in o: out[r][c] = col
    return out
rule("symmetric_parity_recolour_objects",
     "An object that is mirror-symmetric (about its horizontal or vertical bounding-box axis) becomes colour 1 if it has an even cell count, colour 2 if odd; asymmetric objects are left unchanged.",
     gi7, tf7)


# ============================================================ 8
def gi8(rng):
    g = _scene(rng, 5, 9, 3, 12, 14, 28, exclude=(5,))
    if g is None: return None
    h, w = dims(g)
    occ = {c for r, c in cells(g, lambda v: v != 0)}
    cands = [c for c in range(1, w - 1) if c not in occ]
    if not cands: return None
    cm = rng.choice(cands)
    for r in range(h): g[r][cm] = 5
    obs = [o for o in objects(g, 0) if _colour(g, o) != 5]
    pred = lambda o: _centroid(o)[0] < h / 2 and _centroid(o)[1] < cm
    return _mixed2(g, obs, pred)
def tf8(g):
    h, w = dims(g)
    cm = next(c for c in range(w) if all(g[r][c] == 5 for r in range(h)))
    obs = [o for o in objects(g, 0) if _colour(g, o) != 5]
    pred = lambda o: _centroid(o)[0] < h / 2 and _centroid(o)[1] < cm
    return _apply(g, obs, pred, 'keep')
rule("keep_top_half_left_of_marker_objects",
     "A grey (5) vertical marker line marks a column. Keep only objects whose centroid row is in the top half of the grid AND whose centroid column is left of the marker column; delete the rest.",
     gi8, tf8)


# ============================================================ 9
def gi9(rng):
    h, w = size(rng, 12, 28); g = blank(h, w)
    base = random_shape(rng, rng.randint(3, 8))
    c1, c2 = rng.sample(COLOURS, 2)
    shapes = [base, base]; cols = [c1, c2]
    for _ in range(rng.randint(2, 4)):
        shapes.append(random_shape(rng, rng.randint(3, 8))); cols.append(rng.choice(COLOURS))
    if place_shapes(rng, g, shapes, cols, margin=1) is None: return None
    obs = objects(g, 0)
    if len(obs) < 3: return None
    def has_twin_diff(o):
        k = _shape_key(o); col = _colour(g, o)
        return any(_shape_key(x) == k and _colour(g, x) != col for x in obs if x is not o)
    return _mixed2(g, obs, has_twin_diff)
def tf9(g):
    obs = objects(g, 0)
    def has_twin_diff(o):
        k = _shape_key(o); col = _colour(g, o)
        return any(_shape_key(x) == k and _colour(g, x) != col for x in obs if x is not o)
    return _apply(g, obs, has_twin_diff, 'recolour', 9)
rule("recolour_twin_diff_colour_objects",
     "Recolour to 9 every object that has a same-shape twin elsewhere in the grid AND whose colour differs from that twin's colour; objects with no such twin are unchanged.",
     gi9, tf9)


# ============================================================ 10
def _p10(o, g, obs): return (len(o) > 6) != _touches_border(o, *dims(g))
def gi10(rng): return _mixed(_scene(rng, 5, 9, 2, 12, 12, 28), _p10)
def tf10(g): return _apply(g, objects(g, 0), lambda o: _p10(o, g, None), 'delete')
rule("delete_large_xor_border_objects",
     "Delete every object for which exactly one of the two holds: it is large (more than 6 cells), it touches the grid border; objects where both or neither hold are kept.",
     gi10, tf10)


# ============================================================ 11
def gi11(rng): return _mixed(_scene_bh(rng), lambda o, g, obs: _is_box(o) != (lambda r: _has_hole(g, o, r))(_bg_reachable(g)))
def tf11(g):
    reach = _bg_reachable(g)
    pred = lambda o: _is_box(o) != _has_hole(g, o, reach)
    return _apply(g, objects(g, 0), pred, 'recolour', 2)
rule("recolour_box_xor_hole_objects",
     "Recolour to 2 every object for which exactly one of the two holds: it is a hollow rectangle outline, it has an enclosed interior hole; objects with both or neither are unchanged.",
     gi11, tf11)


# ============================================================ 12
def _p12(o, g, obs): return _is_tall(o) != (_colour(g, o) == 5)
def gi12(rng): return _mixed(_scene(rng, 5, 9, 3, 12, 10, 28), _p12)
def tf12(g): return _apply(g, objects(g, 0), lambda o: _p12(o, g, None), 'keep')
rule("keep_tall_xor_grey_objects",
     "Keep only objects for which exactly one of the two holds: taller bounding box than wide, colour grey (5); objects with both or neither are deleted.",
     gi12, tf12)


# ============================================================ 13
def _p13(o, g, obs): return len(o) <= 3 and len(_neighbours(o, obs)) == 0
def gi13(rng): return _mixed(_scene(rng, 6, 10, 1, 6, 12, 28, margin=0), _p13)
def tf13(g):
    obs = objects(g, 0)
    return _apply(g, obs, lambda o: _p13(o, g, obs), 'delete')
rule("delete_small_isolated_objects",
     "Delete every object with 3 or fewer cells AND that touches no other object; objects that are bigger, or that touch something, are kept.",
     gi13, tf13)


# ============================================================ 14
def _p14(o, g, obs):
    hh, ww = _bbdims(o); return ww > hh and ww % 2 == 0
def gi14(rng): return _mixed(_scene(rng, 5, 9, 3, 12, 10, 28, exclude=(3,)), _p14)
def tf14(g): return _apply(g, objects(g, 0), lambda o: _p14(o, g, None), 'recolour', 3)
rule("recolour_wide_even_width_objects",
     "Recolour to 3 every object whose bounding box is wider than it is tall AND whose width in cells is even; other objects are unchanged.",
     gi14, tf14)


# ============================================================ 15
def _p15(o, g, obs):
    col = _colour(g, o)
    return sum(1 for x in obs if _colour(g, x) == col) == 1 and len(o) > 6
def gi15(rng): return _mixed(_scene(rng, 5, 9, 2, 12, 10, 28), _p15)
def tf15(g):
    obs = objects(g, 0)
    return _apply(g, obs, lambda o: _p15(o, g, obs), 'keep')
rule("keep_unique_colour_large_objects",
     "Keep only objects whose colour is used by no other object in the grid AND whose cell count is more than 6; delete every other object.",
     gi15, tf15)


# ============================================================ 16
def _p16(o, g, obs): return _touches_border(o, *dims(g)) and _is_global_largest(o, g, obs)
def gi16(rng): return _mixed(_scene(rng, 5, 9, 3, 14, 12, 28), _p16)
def tf16(g):
    obs = objects(g, 0)
    return _apply(g, obs, lambda o: _p16(o, g, obs), 'delete')
rule("delete_border_and_largest_object",
     "Delete every object that touches the grid border AND is the single largest object (ties included) by cell count; all other objects are kept.",
     gi16, tf16)


# ============================================================ 17
def gi17(rng): return _mixed(_scene_bh(rng), lambda o, g, obs: _is_box(o) and (lambda r: _has_hole(g, o, r))(_bg_reachable(g)))
def tf17(g):
    reach = _bg_reachable(g)
    pred = lambda o: _is_box(o) and _has_hole(g, o, reach)
    return _apply(g, objects(g, 0), pred, 'recolour', 4)
rule("recolour_box_and_hole_objects",
     "Recolour to 4 every object that is a hollow rectangle outline AND has an enclosed interior hole; objects lacking either property are unchanged.",
     gi17, tf17)


# ============================================================ 18
def _p18(o, g, obs): return len(_neighbours(o, obs)) >= 2 and len(o) > 6
def gi18(rng): return _mixed(_scene(rng, 6, 10, 2, 10, 12, 28, margin=0), _p18)
def tf18(g):
    obs = objects(g, 0)
    return _apply(g, obs, lambda o: _p18(o, g, obs), 'keep')
rule("keep_multi_touch_large_objects",
     "Keep only objects that touch 2 or more other objects AND have more than 6 cells; delete every other object.",
     gi18, tf18)


# ============================================================ 19
def _p19(o, g, obs):
    nb = _neighbours(o, obs)
    return len(nb) >= 1 and all(len(o) < len(x) for x in nb)
def gi19(rng): return _mixed(_scene(rng, 6, 10, 2, 10, 12, 28, margin=0), _p19)
def tf19(g):
    obs = objects(g, 0)
    return _apply(g, obs, lambda o: _p19(o, g, obs), 'delete')
rule("delete_smallest_in_cluster_objects",
     "Delete every object that touches at least one other object AND is smaller (fewer cells) than every object it touches; isolated or non-smallest objects are kept.",
     gi19, tf19)


# ============================================================ 20
def gi20(rng):
    g = _scene(rng, 5, 9, 3, 12, 14, 28, exclude=(5, 8))
    if g is None: return None
    h, w = dims(g)
    occ = {c for r, c in cells(g, lambda v: v != 0)}
    cands = [c for c in range(1, w - 1) if c not in occ]
    if not cands: return None
    cm = rng.choice(cands)
    for r in range(h): g[r][cm] = 5
    obs = [o for o in objects(g, 0) if _colour(g, o) != 5]
    pred = lambda o: (_centroid(o)[0] < h / 2) != (_centroid(o)[1] < cm)
    return _mixed2(g, obs, pred)
def tf20(g):
    h, w = dims(g)
    cm = next(c for c in range(w) if all(g[r][c] == 5 for r in range(h)))
    obs = [o for o in objects(g, 0) if _colour(g, o) != 5]
    pred = lambda o: (_centroid(o)[0] < h / 2) != (_centroid(o)[1] < cm)
    return _apply(g, obs, pred, 'recolour', 8)
rule("recolour_half_xor_marker_objects",
     "A grey (5) vertical marker line marks a column. Recolour to 8 every object for which exactly one of the two holds: centroid row in the top half, centroid column left of the marker; others are unchanged.",
     gi20, tf20)


# ============================================================ 21
def _p21(o, g, obs): return len(o) % 2 == 0 and not _is_symmetric(o)
def gi21(rng): return _mixed(_scene(rng, 5, 9, 3, 12, 10, 28), _p21)
def tf21(g): return _apply(g, objects(g, 0), lambda o: _p21(o, g, None), 'delete')
rule("delete_even_asymmetric_objects",
     "Delete every object with an even cell count AND that is not mirror-symmetric about either bounding-box axis; odd-count or symmetric objects are kept.",
     gi21, tf21)


# ============================================================ 22
def _p22(o, g, obs): return _is_tall(o) and _touches_border(o, *dims(g))
def gi22(rng): return _mixed(_scene(rng, 5, 9, 3, 12, 10, 28, exclude=(1,)), _p22)
def tf22(g): return _apply(g, objects(g, 0), lambda o: _p22(o, g, None), 'recolour', 1)
rule("recolour_tall_border_objects",
     "Recolour to 1 every object whose bounding box is taller than it is wide AND that touches the grid border; other objects are unchanged.",
     gi22, tf22)


# ============================================================ 23
def _p23(o, g, obs): return _is_wide(o) or _touches_border(o, *dims(g))
def gi23(rng): return _mixed(_scene(rng, 5, 9, 3, 12, 10, 28), _p23)
def tf23(g): return _apply(g, objects(g, 0), lambda o: _p23(o, g, None), 'keep')
rule("keep_wide_or_border_objects",
     "Keep only objects whose bounding box is wider than it is tall OR that touch the grid border; delete every other object.",
     gi23, tf23)


# ============================================================ 24
def gi24(rng): return _mixed(_scene_bh(rng), lambda o, g, obs: (lambda r: _has_hole(g, o, r))(_bg_reachable(g)) and not _is_global_largest(o, g, obs))
def tf24(g):
    reach = _bg_reachable(g); obs = objects(g, 0)
    pred = lambda o: _has_hole(g, o, reach) and not _is_global_largest(o, g, obs)
    return _apply(g, obs, pred, 'delete')
rule("delete_hole_not_largest_objects",
     "Delete every object that has an enclosed interior hole AND is not the single largest object (ties included) by cell count; holeless or largest objects are kept.",
     gi24, tf24)


# ============================================================ 25
def _p25(o, g, obs): return _is_global_largest(o, g, obs) != _largest_of_colour(o, g, obs)
def gi25(rng): return _mixed(_scene(rng, 5, 9, 2, 12, 10, 28, exclude=(5,)), _p25)
def tf25(g):
    obs = objects(g, 0)
    return _apply(g, obs, lambda o: _p25(o, g, obs), 'recolour', 5)
rule("recolour_largest_xor_colour_objects",
     "Recolour to 5 every object for which exactly one of the two holds: it is the single largest object overall, it is the largest of its own colour; objects with both or neither are unchanged.",
     gi25, tf25)


# ============================================================ 26
def gi26(rng):
    g = _scene(rng, 5, 9, 3, 12, 12, 28, margin=1)
    if g is None: return None
    h, w = dims(g)
    if g[0][0] != 0 or g[0][1] != 0: return None
    keycol = rng.choice(COLOURS); bar = rng.randint(2, 8)
    g[0][0] = keycol; g[0][1] = bar
    obs = [o for o in objects(g, 0) if (0, 0) not in o and (0, 1) not in o]
    pred = lambda o: (_colour(g, o) == keycol) != (len(o) > bar)
    return _mixed2(g, obs, pred)
def tf26(g):
    keycol = g[0][0]; bar = g[0][1]
    obs = [o for o in objects(g, 0) if (0, 0) not in o and (0, 1) not in o]
    pred = lambda o: (_colour(g, o) == keycol) != (len(o) > bar)
    return _apply(g, obs, pred, 'keep')
rule("keep_key_xor_bar_objects",
     "Cell (0,0) is a key colour and cell (0,1) holds a bar digit. Keep only objects for which exactly one of the two holds: colour matches the key, cell count exceeds the bar digit; delete the rest.",
     gi26, tf26)


# ============================================================ 27
def _p27(o, g, obs):
    nb = _neighbours(o, obs)
    return len(nb) == 1 and len(o) > len(nb[0])
def gi27(rng): return _mixed(_scene(rng, 6, 10, 2, 10, 12, 28, margin=0), _p27)
def tf27(g):
    obs = objects(g, 0)
    return _apply(g, obs, lambda o: _p27(o, g, obs), 'delete')
rule("delete_single_neighbour_bigger_objects",
     "Delete every object that touches exactly one other object AND is bigger (more cells) than that single neighbour; objects with a different neighbour count, or that are not bigger, are kept.",
     gi27, tf27)


# ============================================================ 28
def gi28(rng): return _mixed(_scene_bh(rng), lambda o, g, obs: _is_box(o) and _touches_border(o, *dims(g)))
def tf28(g):
    pred = lambda o: _is_box(o) and _touches_border(o, *dims(g))
    return _apply(g, objects(g, 0), pred, 'recolour', 6)
rule("recolour_box_border_objects",
     "Recolour to 6 every object that is a hollow rectangle outline AND touches the grid border; objects lacking either property are unchanged.",
     gi28, tf28)


# ============================================================ 29
def _p29(o, g, obs): return len(o) <= 6 and _touches_border(o, *dims(g))
def gi29(rng): return _mixed(_scene(rng, 5, 9, 2, 12, 12, 28), _p29)
def tf29(g): return _apply(g, objects(g, 0), lambda o: _p29(o, g, None), 'keep')
rule("keep_small_border_objects",
     "Keep only objects with 6 or fewer cells AND that touch the grid border; delete every other object.",
     gi29, tf29)


# ============================================================ 30
def gi30(rng): return _mixed(_scene_bh(rng), lambda o, g, obs: _is_wide(o) != (lambda r: _has_hole(g, o, r))(_bg_reachable(g)))
def tf30(g):
    reach = _bg_reachable(g)
    pred = lambda o: _is_wide(o) != _has_hole(g, o, reach)
    return _apply(g, objects(g, 0), pred, 'delete')
rule("delete_wide_xor_hole_objects",
     "Delete every object for which exactly one of the two holds: bounding box wider than tall, has an enclosed interior hole; objects with both or neither are kept.",
     gi30, tf30)


# ============================================================ 31
def _p31(o, g, obs): return (len(_neighbours(o, obs)) == 0) != (len(o) > 6)
def gi31(rng): return _mixed(_scene(rng, 6, 10, 2, 12, 12, 28, margin=0), _p31)
def tf31(g):
    obs = objects(g, 0)
    return _apply(g, obs, lambda o: _p31(o, g, obs), 'recolour', 3)
rule("recolour_isolated_xor_large_objects",
     "Recolour to 3 every object for which exactly one of the two holds: it touches no other object, it has more than 6 cells; objects with both or neither are unchanged.",
     gi31, tf31)


# ============================================================ 32
def gi32(rng):
    g = _scene(rng, 5, 9, 3, 12, 14, 28, exclude=(5,))
    if g is None: return None
    h, w = dims(g)
    occ = {c for r, c in cells(g, lambda v: v != 0)}
    cands = [c for c in range(1, w - 1) if c not in occ]
    if not cands: return None
    cm = rng.choice(cands)
    for r in range(h): g[r][cm] = 5
    obs = [o for o in objects(g, 0) if _colour(g, o) != 5]
    pred = lambda o: _centroid(o)[0] >= h / 2 and _centroid(o)[1] >= cm
    return _mixed2(g, obs, pred)
def tf32(g):
    h, w = dims(g)
    cm = next(c for c in range(w) if all(g[r][c] == 5 for r in range(h)))
    obs = [o for o in objects(g, 0) if _colour(g, o) != 5]
    pred = lambda o: _centroid(o)[0] >= h / 2 and _centroid(o)[1] >= cm
    return _apply(g, obs, pred, 'keep')
rule("keep_bottom_half_right_of_marker_objects",
     "A grey (5) vertical marker line marks a column. Keep only objects whose centroid row is in the bottom half of the grid AND whose centroid column is at or right of the marker column; delete the rest.",
     gi32, tf32)


# ============================================================ 33
def gi33(rng):
    h, w = size(rng, 12, 28); g = blank(h, w)
    base = random_shape(rng, rng.randint(3, 8))
    c1 = rng.choice(COLOURS)
    shapes = [base, base]; cols = [c1, c1]
    for _ in range(rng.randint(2, 4)):
        shapes.append(random_shape(rng, rng.randint(3, 8))); cols.append(rng.choice(COLOURS))
    if place_shapes(rng, g, shapes, cols, margin=1) is None: return None
    obs = objects(g, 0)
    def has_twin_same(o):
        k = _shape_key(o); col = _colour(g, o)
        return any(_shape_key(x) == k and _colour(g, x) == col for x in obs if x is not o)
    return _mixed2(g, obs, has_twin_same)
def tf33(g):
    obs = objects(g, 0)
    def has_twin_same(o):
        k = _shape_key(o); col = _colour(g, o)
        return any(_shape_key(x) == k and _colour(g, x) == col for x in obs if x is not o)
    return _apply(g, obs, has_twin_same, 'delete')
rule("delete_twin_same_colour_objects",
     "Delete every object that has a same-shape twin elsewhere in the grid AND shares that twin's colour; objects with no such matching twin are kept.",
     gi33, tf33)


# ============================================================ 34
def _p34(o, g, obs): return _largest_of_colour(o, g, obs) and _touches_border(o, *dims(g))
def gi34(rng): return _mixed(_scene(rng, 5, 9, 2, 12, 10, 28, exclude=(7,)), _p34)
def tf34(g):
    obs = objects(g, 0)
    return _apply(g, obs, lambda o: _p34(o, g, obs), 'recolour', 7)
rule("recolour_largest_per_colour_border_objects",
     "Recolour to 7 every object that is the largest (ties included) of its own colour AND touches the grid border; other objects are unchanged.",
     gi34, tf34)


# ============================================================ 35
def _p35(o, g, obs):
    col = _colour(g, o); uniq = sum(1 for x in obs if _colour(g, x) == col) == 1
    return uniq != _touches_border(o, *dims(g))
def gi35(rng): return _mixed(_scene(rng, 5, 9, 2, 12, 12, 28), _p35)
def tf35(g):
    obs = objects(g, 0)
    return _apply(g, obs, lambda o: _p35(o, g, obs), 'keep')
rule("keep_unique_colour_xor_border_objects",
     "Keep only objects for which exactly one of the two holds: its colour is used by no other object, it touches the grid border; delete objects with both or neither.",
     gi35, tf35)


# ============================================================ 36
def _p36(o, g, obs): return (len(o) <= 6) != (not _is_symmetric(o))
def gi36(rng): return _mixed(_scene(rng, 5, 9, 3, 12, 10, 28), _p36)
def tf36(g): return _apply(g, objects(g, 0), lambda o: _p36(o, g, None), 'delete')
rule("delete_small_xor_asymmetric_objects",
     "Delete every object for which exactly one of the two holds: it has 6 or fewer cells, it is NOT mirror-symmetric about either bounding-box axis; objects with both or neither are kept.",
     gi36, tf36)


# ============================================================ 37
def _p37(o, g, obs):
    nb = _neighbours(o, obs)
    return len(nb) >= 2 and all(len(o) > len(x) for x in nb)
def gi37(rng): return _mixed(_scene(rng, 6, 10, 2, 10, 12, 28, margin=0), _p37)
def tf37(g):
    obs = objects(g, 0)
    return _apply(g, obs, lambda o: _p37(o, g, obs), 'recolour', 9)
rule("recolour_cluster_leader_objects",
     "Recolour to 9 every object that touches 2 or more other objects AND is bigger (more cells) than every object it touches; other objects are unchanged.",
     gi37, tf37)


# ============================================================ 38
def gi38(rng):
    g = _scene(rng, 5, 9, 3, 12, 12, 28, margin=1)
    if g is None: return None
    h, w = dims(g)
    if g[0][0] != 0 or g[0][1] != 0: return None
    keycol = rng.choice(COLOURS)
    g[0][0] = keycol; g[0][1] = keycol
    obs = [o for o in objects(g, 0) if (0, 0) not in o and (0, 1) not in o]
    pred = lambda o: _colour(g, o) == keycol and _touches_border(o, h, w)
    return _mixed2(g, obs, pred)
def tf38(g):
    keycol = g[0][0]; h, w = dims(g)
    obs = [o for o in objects(g, 0) if (0, 0) not in o and (0, 1) not in o]
    pred = lambda o: _colour(g, o) == keycol and _touches_border(o, h, w)
    return _apply(g, obs, pred, 'keep')
rule("keep_key_colour_border_objects",
     "Cell (0,0) (and the matching cell (0,1)) mark a key colour. Keep only objects whose colour matches the key AND that touch the grid border; delete the rest.",
     gi38, tf38)


# ============================================================ 39
def _p39(o, g, obs): return _is_tall(o) != _touches_border(o, *dims(g))
def gi39(rng): return _mixed(_scene(rng, 5, 9, 3, 12, 10, 28), _p39)
def tf39(g): return _apply(g, objects(g, 0), lambda o: _p39(o, g, None), 'delete')
rule("delete_tall_xor_border_objects",
     "Delete every object for which exactly one of the two holds: bounding box taller than wide, touches the grid border; objects with both or neither are kept.",
     gi39, tf39)


# ============================================================ 40
def gi40(rng): return _mixed(_scene_bh(rng), lambda o, g, obs: (lambda r: _has_hole(g, o, r))(_bg_reachable(g)) != _touches_border(o, *dims(g)))
def tf40(g):
    reach = _bg_reachable(g)
    pred = lambda o: _has_hole(g, o, reach) != _touches_border(o, *dims(g))
    return _apply(g, objects(g, 0), pred, 'recolour', 2)
rule("recolour_hole_xor_border_objects",
     "Recolour to 2 every object for which exactly one of the two holds: it has an enclosed interior hole, it touches the grid border; objects with both or neither are unchanged.",
     gi40, tf40)
