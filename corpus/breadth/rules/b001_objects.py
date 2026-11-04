# b001_objects.py -- 40 object rules: selecting, recolouring, moving, deleting, duplicating, resizing and
# matching objects by size, colour, shape, position, count, touching and enclosure.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


# ---------------------------------------------------------------- helpers (local to this batch)
def _scene(rng, k_lo=2, k_hi=5, n_lo=3, n_hi=8, lo=6, hi=18, margin=1, distinct=False, cols=None):
    h, w = size(rng, lo, hi); g = blank(h, w)
    k = rng.randint(k_lo, k_hi)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    pal = list(cols) if cols else COLOURS
    cs = rng.sample(pal, k) if distinct else [rng.choice(pal) for _ in range(k)]
    if place_shapes(rng, g, shapes, cs, margin=margin) is None: return None
    return g if len(objects(g, 0)) == k else None


def _col(g, o):
    return g[o[0][0]][o[0][1]]


def _norm(o):
    r0, c0, _, _ = bbox(o)
    return tuple(sorted((r - r0, c - c0) for r, c in o))


def _erase(out, o):
    for r, c in o: out[r][c] = 0


def _holes(o):
    """Enclosed empty regions inside an object: 4-connected non-object cells of its bbox that do not reach
    the bbox border. Returns the list of hole cell-lists."""
    s = set(o); r0, c0, r1, c1 = bbox(o)
    free = {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if (r, c) not in s}
    seen = set(); holes = []
    for st in sorted(free):
        if st in seen: continue
        comp, stack, open_ = [], [st], False; seen.add(st)
        while stack:
            y, x = stack.pop(); comp.append((y, x))
            if y in (r0, r1) or x in (c0, c1): open_ = True
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if (ny, nx) in free and (ny, nx) not in seen:
                    seen.add((ny, nx)); stack.append((ny, nx))
        if not open_: holes.append(comp)
    return holes


def _ring(rng, n):
    """A random blob dilated by one ring, with the blob removed: a shape with at least one hole."""
    core = set(random_shape(rng, n))
    ring = {(r + dr, c + dc) for r, c in core for dr in (-1, 0, 1) for dc in (-1, 0, 1)} - core
    r0 = min(r for r, _ in ring); c0 = min(c for _, c in ring)
    return sorted((r - r0, c - c0) for r, c in ring)


def _rect_shape(h, w, hollow=False):
    return [(r, c) for r in range(h) for c in range(w) if not hollow or r in (0, h - 1) or c in (0, w - 1)]


def _paint(out, cells_, col):
    """Paint cells; return False on out-of-bounds or collision with a non-background cell."""
    H, W = dims(out)
    for r, c in cells_:
        if not (0 <= r < H and 0 <= c < W) or out[r][c] != 0: return False
    for r, c in cells_: out[r][c] = col
    return True


def _nearest_wall(g, o):
    h, w = dims(g); r0, c0, r1, c1 = bbox(o)
    d = {"u": r0, "d": h - 1 - r1, "l": c0, "r": w - 1 - c1}
    best = min(d.values())
    return [k for k, v in d.items() if v == best], best


# 1 delete the smallest object
def gi_del_small(rng):
    g = _scene(rng, 3, 6, 1, 8)
    if g is None: return None
    s = sorted(len(o) for o in objects(g, 0))
    return g if s[0] != s[1] else None
def tf_del_small(g):
    obs = objects(g, 0); s = sorted(len(o) for o in obs)
    if s[0] == s[1]: return None
    out = copy(g); _erase(out, min(obs, key=len)); return out
rule("delete_smallest_object", "The single smallest object is erased; everything else stays.", gi_del_small, tf_del_small)


# 2 keep only objects touching the border
def gi_border(rng):
    g = _scene(rng, 3, 7, 2, 7, 7, 18)
    if g is None: return None
    h, w = dims(g); t = [any(r in (0, h - 1) or c in (0, w - 1) for r, c in o) for o in objects(g, 0)]
    return g if any(t) and not all(t) else None
def tf_border(g):
    h, w = dims(g); out = blank(h, w)
    for o in objects(g, 0):
        if any(r in (0, h - 1) or c in (0, w - 1) for r, c in o):
            for r, c in o: out[r][c] = g[r][c]
    return out
rule("keep_border_touching_objects", "Only objects that touch the edge of the grid are kept; the rest are erased.", gi_border, tf_border)


# 3 recolour each object by its number of holes
def gi_holes(rng):
    h, w = size(rng, 8, 20); g = blank(h, w); k = rng.randint(2, 5); col = rng.choice([5, 6, 7, 8, 9]); shapes = []
    for _ in range(k):
        rh, rw = rng.randint(3, 7), rng.randint(3, 7); s = set(_rect_shape(rh, rw)); nh = rng.randint(0, 3)
        inner = [(r, c) for r in range(1, rh - 1, 2) for c in range(1, rw - 1, 2)]
        for p in rng.sample(inner, min(nh, len(inner))): s.discard(p)
        shapes.append(sorted(s))
    if place_shapes(rng, g, shapes, [col] * k, margin=1) is None: return None
    return g if len({len(_holes(o)) for o in objects(g, 0)}) >= 2 else None
def tf_holes(g):
    out = copy(g)
    for o in objects(g, 0):
        n = len(_holes(o))
        if n > 3: return None
        for r, c in o: out[r][c] = n + 1
    return out
rule("recolour_by_hole_count", "Each object is recoloured 1, 2, 3 or 4 according to how many holes it has (holes plus one).", gi_holes, tf_holes, digits=True)


# 4 slide every object to its nearest wall
def gi_slide(rng):
    g = _scene(rng, 2, 4, 2, 6, 7, 16)
    if g is None: return None
    return g if all(len(_nearest_wall(g, o)[0]) == 1 and _nearest_wall(g, o)[1] > 0 for o in objects(g, 0)) else None
def tf_slide(g):
    h, w = dims(g); out = blank(h, w)
    for o in objects(g, 0):
        ks, d = _nearest_wall(g, o)
        if len(ks) != 1: return None
        dr, dc = {"u": (-d, 0), "d": (d, 0), "l": (0, -d), "r": (0, d)}[ks[0]]
        if not _paint(out, [(r + dr, c + dc) for r, c in o], _col(g, o)): return None
    return out
rule("slide_to_nearest_wall", "Every object slides straight toward whichever grid edge is closest until it touches it.", gi_slide, tf_slide)


# 5 swap the colours of the two largest objects
def gi_swap2(rng):
    g = _scene(rng, 2, 5, 2, 9)
    if g is None: return None
    obs = sorted(objects(g, 0), key=len, reverse=True)
    if len(obs) > 2 and len(obs[1]) == len(obs[2]): return None
    return g if len(obs[0]) != len(obs[1]) and _col(g, obs[0]) != _col(g, obs[1]) else None
def tf_swap2(g):
    obs = sorted(objects(g, 0), key=len, reverse=True); a, b = obs[0], obs[1]
    if len(a) == len(b) or (len(obs) > 2 and len(b) == len(obs[2])): return None
    out = copy(g); ca, cb = _col(g, a), _col(g, b)
    for r, c in a: out[r][c] = cb
    for r, c in b: out[r][c] = ca
    return out
rule("swap_two_largest_colours", "The two largest objects exchange colours; all other objects are unchanged.", gi_swap2, tf_swap2)


# 6 draw a bounding frame one cell outside each object
def gi_box(rng):
    return _scene(rng, 1, 4, 2, 7, 7, 18, margin=2)
def tf_box(g):
    h, w = dims(g); out = copy(g)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o); col = _col(g, o)
        for r in range(r0 - 1, r1 + 2):
            for c in range(c0 - 1, c1 + 2):
                if 0 <= r < h and 0 <= c < w and (r in (r0 - 1, r1 + 1) or c in (c0 - 1, c1 + 1)):
                    out[r][c] = col
    return out
rule("frame_each_object", "A rectangular frame in the object's own colour is drawn one cell outside each object's bounding box.", gi_box, tf_box)


# 7 hollow out objects: interior cells become background
def gi_hollow(rng):
    h, w = size(rng, 7, 20); g = blank(h, w); k = rng.randint(1, 4)
    shapes = [_rect_shape(rng.randint(3, 7), rng.randint(3, 7)) for _ in range(k)]
    return g if place_shapes(rng, g, shapes, [rng.choice(COLOURS) for _ in range(k)], margin=1) else None
def tf_hollow(g):
    h, w = dims(g); out = copy(g)
    for r in range(1, h - 1):
        for c in range(1, w - 1):
            v = g[r][c]
            if v and all(g[r + dr][c + dc] == v for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))):
                out[r][c] = 0
    return out
rule("hollow_out_objects", "Every object keeps only its outline; cells surrounded on four sides by the same colour become empty.", gi_hollow, tf_hollow)


# 8 fill holes with the object's colour
def gi_fillholes(rng):
    h, w = size(rng, 8, 20); g = blank(h, w); k = rng.randint(1, 4)
    shapes = [_ring(rng, rng.randint(1, 5)) for _ in range(k)]
    if place_shapes(rng, g, shapes, [rng.choice(COLOURS) for _ in range(k)], margin=1) is None: return None
    return g if len(objects(g, 0)) == k else None
def tf_fillholes(g):
    out = copy(g)
    for o in objects(g, 0):
        for hole in _holes(o):
            for r, c in hole: out[r][c] = _col(g, o)
    return out
rule("fill_object_holes", "Every enclosed hole inside an object is filled with that object's colour.", gi_fillholes, tf_fillholes)


# 9 punch out the centre cell of each odd-sized rectangle
def gi_punch(rng):
    h, w = size(rng, 7, 20); g = blank(h, w); k = rng.randint(1, 5)
    shapes = [_rect_shape(rng.choice([3, 5, 7]), rng.choice([3, 5, 7])) for _ in range(k)]
    return g if place_shapes(rng, g, shapes, [rng.choice(COLOURS) for _ in range(k)], margin=1) else None
def tf_punch(g):
    out = copy(g)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o); out[(r0 + r1) // 2][(c0 + c1) // 2] = 0
    return out
rule("punch_rect_centres", "The exact centre cell of each rectangle is removed, leaving a one-cell hole.", gi_punch, tf_punch)


# 10 keep shapes that appear exactly twice
def gi_twice(rng):
    h, w = size(rng, 9, 22); g = blank(h, w); k = rng.randint(2, 4)
    bases = [random_shape(rng, rng.randint(2, 5)) for _ in range(k)]
    mult = [rng.choice([1, 2, 2, 3]) for _ in range(k)]
    if 2 not in mult or all(m == 2 for m in mult): return None
    shapes = [b for b, m in zip(bases, mult) for _ in range(m)]
    if place_shapes(rng, g, shapes, [rng.choice(COLOURS) for _ in shapes], margin=1) is None: return None
    obs = objects(g, 0); cnt = {}
    for o in obs: cnt[_norm(o)] = cnt.get(_norm(o), 0) + 1
    return g if len(obs) == len(shapes) and sorted(cnt.values()) == sorted(mult) else None
def tf_twice(g):
    obs = objects(g, 0); cnt = {}
    for o in obs: cnt[_norm(o)] = cnt.get(_norm(o), 0) + 1
    out = blank(*dims(g))
    for o in obs:
        if cnt[_norm(o)] == 2:
            for r, c in o: out[r][c] = g[r][c]
    return out
rule("keep_shapes_appearing_twice", "Only shapes that occur exactly twice in the grid are kept, regardless of colour.", gi_twice, tf_twice)


# 11 delete the largest object
def gi_del_big(rng):
    g = _scene(rng, 2, 6, 1, 9)
    if g is None: return None
    s = sorted((len(o) for o in objects(g, 0)), reverse=True)
    return g if s[0] != s[1] else None
def tf_del_big(g):
    obs = objects(g, 0); s = sorted((len(o) for o in obs), reverse=True)
    if s[0] == s[1]: return None
    out = copy(g); _erase(out, max(obs, key=len)); return out
rule("delete_largest_object", "The single largest object is erased; everything else stays.", gi_del_big, tf_del_big)


# 12 recolour objects by size rank
def gi_rank(rng):
    g = _scene(rng, 2, 6, 1, 10, 7, 18, cols=[7, 8, 9])
    if g is None: return None
    s = [len(o) for o in objects(g, 0)]
    return g if len(set(s)) == len(s) else None
def tf_rank(g):
    obs = sorted(objects(g, 0), key=len); out = copy(g)
    if len({len(o) for o in obs}) != len(obs): return None
    for i, o in enumerate(obs):
        for r, c in o: out[r][c] = i + 1
    return out
rule("recolour_by_size_rank", "Objects are recoloured by size order: the smallest becomes 1, the next 2, and so on.", gi_rank, tf_rank, digits=True)


# 13 histogram of object counts per colour
def gi_hist(rng):
    g = _scene(rng, 3, 8, 1, 5, 7, 18)
    if g is None: return None
    return g if len({_col(g, o) for o in objects(g, 0)}) >= 2 else None
def tf_hist(g):
    cnt = {}
    for o in objects(g, 0): cnt[_col(g, o)] = cnt.get(_col(g, o), 0) + 1
    m = max(cnt.values())
    return [[col] * n + [0] * (m - n) for col, n in sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))]
rule("colour_object_count_histogram", "Output one row per colour, a bar as long as the number of objects of that colour, most numerous colour on top.", gi_hist, tf_hist)


# 14 rigid gravity: objects fall as solid pieces
def gi_rigid(rng):
    return _scene(rng, 2, 5, 2, 6, 7, 16, distinct=True)
def tf_rigid(g):
    h, w = dims(g); out = blank(h, w)
    for o in sorted(objects(g, 0), key=lambda o: -max(r for r, _ in o)):
        d = 0
        while all(r + d + 1 < h and out[r + d + 1][c] == 0 for r, c in o): d += 1
        for r, c in o: out[r + d][c] = g[r][c]
    return out
rule("rigid_object_gravity", "Each object drops as one solid piece until it rests on the floor or on another object.", gi_rigid, tf_rigid)


# 15 duplicate every object immediately to its right
def gi_dup(rng):
    h, wl = rng.randint(6, 16), rng.randint(4, 11); left = blank(h, wl); k = rng.randint(1, 3)
    shapes = [random_shape(rng, rng.randint(2, 6)) for _ in range(k)]
    if place_shapes(rng, left, shapes, [rng.choice(COLOURS) for _ in range(k)], margin=1) is None: return None
    g = [row + [0] * (wl + 2) for row in left]
    return g if len(objects(g, 0)) == k else None
def tf_dup(g):
    out = copy(g)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o); dc = c1 - c0 + 2
        if not _paint(out, [(r, c + dc) for r, c in o], _col(g, o)): return None
    return out
rule("duplicate_objects_right", "Each object gets an identical copy placed one empty column to its right.", gi_dup, tf_dup)


# 16 crop the largest object and double its size
def gi_crop2x(rng):
    g = _scene(rng, 2, 5, 2, 8, 7, 18)
    if g is None: return None
    s = sorted((len(o) for o in objects(g, 0)), reverse=True)
    return g if s[0] != s[1] else None
def tf_crop2x(g):
    obs = sorted(objects(g, 0), key=len, reverse=True)
    if len(obs) > 1 and len(obs[0]) == len(obs[1]): return None
    sub = crop(g, *bbox(obs[0]))
    return [[v for v in row for _ in (0, 1)] for row in sub for _ in (0, 1)]
rule("crop_largest_scaled_2x", "The largest object is cut out and drawn at twice its size, each cell becoming a 2x2 block.", gi_crop2x, tf_crop2x)


# 17 a single-cell marker recolours the object it touches
def gi_marker(rng):
    g = _scene(rng, 2, 5, 3, 8, 8, 18)
    if g is None: return None
    h, w = dims(g); obs = objects(g, 0); hit = 0
    for o in rng.sample(obs, rng.randint(1, len(obs))):
        halo = [(r + dr, c + dc) for r, c in o for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                if 0 <= r + dr < h and 0 <= c + dc < w and g[r + dr][c + dc] == 0]
        if not halo: continue
        r, c = rng.choice(halo); g[r][c] = rng.choice([x for x in COLOURS if x != _col(g, o)]); hit += 1
    return g if hit and len(objects(g, 0)) == len(obs) + hit else None
def tf_marker(g):
    obs = objects(g, 0); out = copy(g); h, w = dims(g)
    singles = [o for o in obs if len(o) == 1]; bodies = [o for o in obs if len(o) > 1]
    if not singles: return None
    for (r, c), in singles:
        near = [b for b in bodies if any(abs(r - y) <= 1 and abs(c - x) <= 1 for y, x in b)]
        if len(near) != 1: return None
        for y, x in near[0]: out[y][x] = g[r][c]
        out[r][c] = 0
    return out
rule("marker_recolours_touched_object", "Each lone single cell recolours the object it touches to its own colour and then disappears.", gi_marker, tf_marker)


# 18 fill each hollow frame with the colour of the dot inside it
def gi_framedot(rng):
    h, w = size(rng, 8, 20); g = blank(h, w); k = rng.randint(1, 4)
    dimsl = [(rng.randint(4, 8), rng.randint(4, 8)) for _ in range(k)]
    shapes = [_rect_shape(a, b, hollow=True) for a, b in dimsl]
    fcols = [rng.choice(COLOURS) for _ in range(k)]
    pos = place_shapes(rng, g, shapes, fcols, margin=1)
    if pos is None: return None
    for (r0, c0), (a, b), fc in zip(pos, dimsl, fcols):
        g[rng.randint(r0 + 1, r0 + a - 2)][rng.randint(c0 + 1, c0 + b - 2)] = rng.choice([x for x in COLOURS if x != fc])
    return g
def tf_framedot(g):
    out = copy(g)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o)
        if len(o) != 2 * (r1 - r0 + c1 - c0): continue
        dots = [(r, c) for r in range(r0 + 1, r1) for c in range(c0 + 1, c1) if g[r][c]]
        if len(dots) != 1: return None
        rect(out, r0 + 1, c0 + 1, r1 - 1, c1 - 1, g[dots[0][0]][dots[0][1]])
    return out
rule("fill_frame_with_inner_dot_colour", "The inside of every hollow rectangle is filled with the colour of the single dot it contains.", gi_framedot, tf_framedot)


# 19 reduce every object to one cell at its centre
def gi_centres(rng):
    return _scene(rng, 2, 7, 2, 9, 6, 18)
def tf_centres(g):
    out = blank(*dims(g))
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o); out[(r0 + r1) // 2][(c0 + c1) // 2] = _col(g, o)
    return out
rule("objects_to_centre_cells", "Every object is replaced by a single cell of its colour at the centre of its bounding box.", gi_centres, tf_centres)


# 20 crop the largest object
def gi_croplarge(rng):
    g = _scene(rng, 2, 6, 2, 9, 7, 20)
    if g is None: return None
    s = sorted((len(o) for o in objects(g, 0)), reverse=True)
    return g if s[0] != s[1] else None
def tf_croplarge(g):
    obs = sorted(objects(g, 0), key=len, reverse=True)
    if len(obs) > 1 and len(obs[0]) == len(obs[1]): return None
    return crop(g, *bbox(obs[0]))
rule("crop_largest_object", "Output is the bounding box of the largest object.", gi_croplarge, tf_croplarge)


# 21 recolour by aspect: wide, tall, square
def gi_aspect(rng):
    g = _scene(rng, 2, 6, 2, 8, 7, 18, cols=[4, 5, 6, 7, 8, 9])
    if g is None: return None
    asp = {(lambda b: (b[3] - b[1] > b[2] - b[0]) - (b[3] - b[1] < b[2] - b[0]))(bbox(o)) for o in objects(g, 0)}
    return g if len(asp) >= 2 else None
def tf_aspect(g):
    out = copy(g)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o); hh, ww = r1 - r0, c1 - c0
        col = 1 if ww > hh else 2 if hh > ww else 3
        for r, c in o: out[r][c] = col
    return out
rule("recolour_by_aspect", "Objects wider than tall become 1, taller than wide become 2, and square-boxed objects become 3.", gi_aspect, tf_aspect)


# 22 keep only objects of the colour with the most objects
def gi_majority(rng):
    g = _scene(rng, 3, 8, 1, 6, 7, 18)
    if g is None: return None
    cnt = {}
    for o in objects(g, 0): cnt[_col(g, o)] = cnt.get(_col(g, o), 0) + 1
    v = sorted(cnt.values(), reverse=True)
    return g if len(v) >= 2 and v[0] != v[1] else None
def tf_majority(g):
    obs = objects(g, 0); cnt = {}
    for o in obs: cnt[_col(g, o)] = cnt.get(_col(g, o), 0) + 1
    v = sorted(cnt.values(), reverse=True)
    if len(v) < 2 or v[0] == v[1]: return None
    keep = max(cnt, key=cnt.get); out = blank(*dims(g))
    for o in obs:
        if _col(g, o) == keep:
            for r, c in o: out[r][c] = keep
    return out
rule("keep_majority_colour_objects", "Only objects of the colour that has the most separate objects are kept.", gi_majority, tf_majority)


# 23 shapes with a twin vs unique shapes
def gi_twin(rng):
    h, w = size(rng, 9, 22); g = blank(h, w); k = rng.randint(2, 4)
    bases = [random_shape(rng, rng.randint(2, 5)) for _ in range(k)]
    mult = [rng.choice([1, 2, 3]) for _ in range(k)]
    if all(m == 1 for m in mult) or all(m > 1 for m in mult): return None
    shapes = [b for b, m in zip(bases, mult) for _ in range(m)]
    if place_shapes(rng, g, shapes, [rng.choice([3, 4, 5, 6, 7, 8, 9]) for _ in shapes], margin=1) is None: return None
    obs = objects(g, 0); cnt = {}
    for o in obs: cnt[_norm(o)] = cnt.get(_norm(o), 0) + 1
    return g if len(obs) == len(shapes) and sorted(cnt.values()) == sorted(mult) else None
def tf_twin(g):
    obs = objects(g, 0); cnt = {}
    for o in obs: cnt[_norm(o)] = cnt.get(_norm(o), 0) + 1
    out = copy(g)
    for o in obs:
        for r, c in o: out[r][c] = 1 if cnt[_norm(o)] > 1 else 2
    return out
rule("twin_shapes_vs_unique_recolour", "Objects whose shape appears elsewhere in the grid become 1; objects with a unique shape become 2.", gi_twin, tf_twin)


# 24 object sizes as rows, largest first
def gi_sizerows(rng):
    g = _scene(rng, 2, 7, 1, 9, 6, 18)
    if g is None: return None
    return g if len({len(o) for o in objects(g, 0)}) >= 2 else None
def tf_sizerows(g):
    obs = sorted(objects(g, 0), key=lambda o: (-len(o), _col(g, o))); m = len(obs[0])
    return [[_col(g, o)] * len(o) + [0] * (m - len(o)) for o in obs]
rule("object_sizes_as_rows", "Output one row per object, a bar of its colour as long as its cell count, largest object on top.", gi_sizerows, tf_sizerows)


# 25 fill each object's bounding box
def gi_fillbox(rng):
    g = _scene(rng, 1, 5, 3, 9, 6, 18)
    if g is None: return None
    obs = objects(g, 0)
    if all((lambda b: (b[2] - b[0] + 1) * (b[3] - b[1] + 1) == len(o))(bbox(o)) for o in obs): return None
    return g
def tf_fillbox(g):
    out = copy(g); obs = objects(g, 0)
    for o in obs: rect(out, *bbox(o), _col(g, o))
    for o in obs:
        if any(out[r][c] != g[r][c] for r, c in o): return None
    return out
rule("fill_object_bounding_boxes", "Each object is expanded to completely fill its own bounding rectangle.", gi_fillbox, tf_fillbox)


# 26 delete objects that touch no other object
def _touching(g, obs):
    h, w = dims(g); res = []
    for o in obs:
        col = _col(g, o)
        res.append(any(0 <= r + dr < h and 0 <= c + dc < w and g[r + dr][c + dc] not in (0, col)
                       for r, c in o for dr in (-1, 0, 1) for dc in (-1, 0, 1)))
    return res
def gi_isolated(rng):
    g = _scene(rng, 3, 7, 2, 7, 7, 18, margin=0, distinct=True)
    if g is None: return None
    t = _touching(g, objects(g, 0))
    return g if any(t) and not all(t) else None
def tf_isolated(g):
    obs = objects(g, 0); t = _touching(g, obs); out = copy(g)
    for o, touch in zip(obs, t):
        if not touch: _erase(out, o)
    return out
rule("delete_isolated_objects", "Objects that do not touch any other object (even diagonally) are erased.", gi_isolated, tf_isolated)


# 27 crop the interior of the one large frame
def gi_frameint(rng):
    h, w = size(rng, 9, 22); g = blank(h, w); fc = rng.choice(COLOURS)
    a, b = rng.randint(5, min(12, h - 2)), rng.randint(5, min(12, w - 2))
    r0, c0 = rng.randint(1, h - a - 1), rng.randint(1, w - b - 1)
    rect(g, r0, c0, r0 + a - 1, c0 + b - 1, fc, fill=False)
    for _ in range(rng.randint(2, (a - 2) * (b - 2) // 2)):
        g[rng.randint(r0 + 1, r0 + a - 2)][rng.randint(c0 + 1, c0 + b - 2)] = rng.choice([x for x in COLOURS if x != fc])
    for _ in range(rng.randint(2, 10)):
        r, c = rng.randrange(h), rng.randrange(w)
        if not (r0 - 1 <= r <= r0 + a and c0 - 1 <= c <= c0 + b): g[r][c] = rng.choice([x for x in COLOURS if x != fc])
    return g
def tf_frameint(g):
    for o in objects(g, 0, conn8=False):
        r0, c0, r1, c1 = bbox(o)
        if r1 - r0 >= 4 and c1 - c0 >= 4 and len(o) == 2 * (r1 - r0 + c1 - c0):
            return crop(g, r0 + 1, c0 + 1, r1 - 1, c1 - 1)
    return None
rule("crop_frame_interior", "Output is everything inside the large hollow rectangle, without the frame itself.", gi_frameint, tf_frameint)


# 28 recolour objects by vertical order
def gi_vorder(rng):
    g = _scene(rng, 2, 6, 1, 7, 7, 18, cols=[7, 8, 9])
    if g is None: return None
    tops = [bbox(o)[0] for o in objects(g, 0)]
    return g if len(set(tops)) == len(tops) else None
def tf_vorder(g):
    obs = sorted(objects(g, 0), key=lambda o: bbox(o)[0]); out = copy(g)
    if len({bbox(o)[0] for o in obs}) != len(obs): return None
    for i, o in enumerate(obs):
        for r, c in o: out[r][c] = i + 1
    return out
rule("recolour_by_vertical_order", "Objects are numbered from the top of the grid down: the highest becomes 1, the next 2, and so on.", gi_vorder, tf_vorder, digits=True)


# 29 mirror each object left-right inside its own box
def gi_mirrorobj(rng):
    g = _scene(rng, 1, 5, 3, 9, 6, 18)
    if g is None: return None
    return g if any(_norm(o) != _norm([(r, -c) for r, c in o]) for o in objects(g, 0)) else None
def tf_mirrorobj(g):
    out = blank(*dims(g))
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o)
        for r, c in o: out[r][c0 + c1 - c] = g[r][c]
    return out
rule("mirror_each_object_horizontally", "Every object is flipped left-to-right within its own bounding box, staying in place.", gi_mirrorobj, tf_mirrorobj)


# 30 rotate each object a quarter turn about its top-left corner
def gi_rotobj(rng):
    g = _scene(rng, 1, 4, 3, 7, 8, 18, margin=2)
    return g
def tf_rotobj(g):
    out = blank(*dims(g))
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o); hh = r1 - r0
        if not _paint(out, [(r0 + (c - c0), c0 + (hh - (r - r0))) for r, c in o], _col(g, o)): return None
    return out
rule("rotate_each_object_quarter_turn", "Every object is rotated 90 degrees clockwise, keeping its top-left corner fixed.", gi_rotobj, tf_rotobj)


# 31 objects cast a shadow to the right wall
def gi_shadow(rng):
    return _scene(rng, 1, 5, 2, 7, 6, 18)
def tf_shadow(g):
    h, w = dims(g); out = copy(g)
    for o in objects(g, 0):
        col = _col(g, o)
        for r in {r for r, _ in o}:
            c = max(c for y, c in o if y == r) + 1
            while c < w and g[r][c] == 0:
                out[r][c] = col; c += 1
    return out
rule("objects_cast_shadow_right", "Every row of each object extends rightward in its colour until it hits the wall or another object.", gi_shadow, tf_shadow)


# 32 keep only the largest object of each colour
def gi_largestper(rng):
    g = _scene(rng, 3, 8, 1, 7, 7, 20, cols=colours(rng, rng.randint(1, 3)))
    if g is None: return None
    by = {}
    for o in objects(g, 0): by.setdefault(_col(g, o), []).append(len(o))
    if all(len(v) == 1 for v in by.values()): return None
    return g if all(sorted(v)[-1] != sorted(v)[-2] for v in by.values() if len(v) > 1) else None
def tf_largestper(g):
    by = {}
    for o in objects(g, 0): by.setdefault(_col(g, o), []).append(o)
    out = blank(*dims(g))
    for col, obs in by.items():
        obs = sorted(obs, key=len, reverse=True)
        if len(obs) > 1 and len(obs[0]) == len(obs[1]): return None
        for r, c in obs[0]: out[r][c] = col
    return out
rule("keep_largest_per_colour", "For each colour, only its largest object survives; smaller objects of that colour are erased.", gi_largestper, tf_largestper)


# 33 recolour by size parity
def gi_parity(rng):
    g = _scene(rng, 2, 7, 1, 9, 6, 18, cols=[3, 4, 5, 6, 7, 8, 9])
    if g is None: return None
    return g if len({len(o) % 2 for o in objects(g, 0)}) == 2 else None
def tf_parity(g):
    out = copy(g)
    for o in objects(g, 0):
        for r, c in o: out[r][c] = 1 if len(o) % 2 else 2
    return out
rule("recolour_by_size_parity", "Objects with an odd number of cells become 1; objects with an even number become 2.", gi_parity, tf_parity)


# 34 crop the shape that occurs most often
def gi_common(rng):
    h, w = size(rng, 9, 22); g = blank(h, w); k = rng.randint(2, 3)
    bases = [random_shape(rng, rng.randint(2, 6)) for _ in range(k)]
    mult = rng.sample([1, 2, 3, 4], k)
    cs = colours(rng, k)
    shapes = [b for b, m in zip(bases, mult) for _ in range(m)]; cols_ = [c for c, m in zip(cs, mult) for _ in range(m)]
    if place_shapes(rng, g, shapes, cols_, margin=1) is None: return None
    obs = objects(g, 0); cnt = {}
    for o in obs: cnt[_norm(o)] = cnt.get(_norm(o), 0) + 1
    return g if len(obs) == len(shapes) and sorted(cnt.values()) == sorted(mult) else None
def tf_common(g):
    obs = objects(g, 0); cnt = {}
    for o in obs: cnt[(_norm(o), _col(g, o))] = cnt.get((_norm(o), _col(g, o)), 0) + 1
    v = sorted(cnt.values(), reverse=True)
    if len(v) > 1 and v[0] == v[1]: return None
    best = max(cnt, key=cnt.get)
    o = next(o for o in obs if (_norm(o), _col(g, o)) == best)
    return crop(g, *bbox(o))
rule("crop_most_frequent_shape", "Output is one copy of the shape that appears most often in the grid.", gi_common, tf_common)


# 35 two objects swap places
def gi_swappos(rng):
    g = _scene(rng, 2, 2, 2, 8, 6, 16, distinct=True)
    return g
def tf_swappos(g):
    obs = objects(g, 0)
    if len(obs) != 2: return None
    out = blank(*dims(g)); a, b = obs; (ar, ac, _, _), (br, bc, _, _) = bbox(a), bbox(b)
    if not _paint(out, [(r - ar + br, c - ac + bc) for r, c in a], _col(g, a)): return None
    if not _paint(out, [(r - br + ar, c - bc + ac) for r, c in b], _col(g, b)): return None
    return out
rule("swap_two_object_positions", "The two objects trade places: each one's top-left corner moves to where the other's was.", gi_swappos, tf_swappos)


# 36 the largest object and the background exchange colours
def gi_invert(rng):
    g = _scene(rng, 1, 4, 3, 9, 6, 16)
    if g is None: return None
    s = sorted((len(o) for o in objects(g, 0)), reverse=True)
    return g if len(s) == 1 or s[0] != s[1] else None
def tf_invert(g):
    obs = sorted(objects(g, 0), key=len, reverse=True)
    if len(obs) > 1 and len(obs[0]) == len(obs[1]): return None
    big = set(obs[0]); col = _col(g, obs[0])
    return [[0 if (r, c) in big else col if v == 0 else v for c, v in enumerate(row)] for r, row in enumerate(g)]
rule("largest_object_swaps_with_background", "The largest object becomes empty and the empty background takes its colour; other objects stay.", gi_invert, tf_invert)


# 37 a line from each object to its nearest wall
def gi_wallline(rng):
    g = _scene(rng, 1, 4, 2, 7, 8, 18)
    if g is None: return None
    return g if all(len(_nearest_wall(g, o)[0]) == 1 and _nearest_wall(g, o)[1] > 0 for o in objects(g, 0)) else None
def tf_wallline(g):
    h, w = dims(g); out = copy(g)
    for o in objects(g, 0):
        ks, _ = _nearest_wall(g, o)
        if len(ks) != 1: return None
        dr, dc = {"u": (-1, 0), "d": (1, 0), "l": (0, -1), "r": (0, 1)}[ks[0]]
        r0, c0, r1, c1 = bbox(o); r, c = (r0 + r1) // 2, (c0 + c1) // 2; s = set(o); col = _col(g, o)
        while 0 <= r < h and 0 <= c < w and (r, c) in s: r += dr; c += dc
        while 0 <= r < h and 0 <= c < w and g[r][c] == 0:
            out[r][c] = col; r += dr; c += dc
    return out
rule("line_from_object_to_nearest_wall", "From the middle of each object a line of its colour is drawn straight to the nearest grid edge.", gi_wallline, tf_wallline)


# 38 keep only objects with holes
def gi_keepholes(rng):
    h, w = size(rng, 8, 20); g = blank(h, w); k = rng.randint(2, 5)
    kinds = [rng.random() < 0.5 for _ in range(k)]
    if all(kinds) or not any(kinds): return None
    shapes = [_ring(rng, rng.randint(1, 4)) if k_ else random_shape(rng, rng.randint(2, 8)) for k_ in kinds]
    if place_shapes(rng, g, shapes, [rng.choice(COLOURS) for _ in range(k)], margin=1) is None: return None
    return g if len(objects(g, 0)) == k else None
def tf_keepholes(g):
    out = blank(*dims(g))
    for o in objects(g, 0):
        if _holes(o):
            for r, c in o: out[r][c] = g[r][c]
    return out
rule("keep_objects_with_holes", "Only objects that enclose at least one hole are kept; solid objects are erased.", gi_keepholes, tf_keepholes)


# 39 recolour by mirror symmetry
def gi_sym(rng):
    h, w = size(rng, 7, 20); g = blank(h, w); k = rng.randint(2, 6); shapes = []
    for _ in range(k):
        if rng.random() < 0.5:
            half = random_shape(rng, rng.randint(1, 4)); ww = max(c for _, c in half) + 1
            shapes.append(sorted(set(half) | {(r, 2 * ww - 1 - c) for r, c in half}))
        else:
            shapes.append(random_shape(rng, rng.randint(2, 7)))
    if place_shapes(rng, g, shapes, [rng.choice([3, 4, 5, 6, 7, 8, 9]) for _ in range(k)], margin=1) is None: return None
    obs = objects(g, 0)
    return g if len(obs) == k and len({_norm(o) == _norm([(r, -c) for r, c in o]) for o in obs}) == 2 else None
def tf_sym(g):
    out = copy(g)
    for o in objects(g, 0):
        col = 1 if _norm(o) == _norm([(r, -c) for r, c in o]) else 2
        for r, c in o: out[r][c] = col
    return out
rule("recolour_by_mirror_symmetry", "Objects that are left-right symmetric become 1; objects that are not become 2.", gi_sym, tf_sym)


# 40 grow every object by one cell on each side
def gi_dilate(rng):
    return _scene(rng, 1, 4, 1, 7, 7, 18, margin=2)
def tf_dilate(g):
    h, w = dims(g); out = copy(g)
    for o in objects(g, 0):
        col = _col(g, o)
        for r, c in o:
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                if 0 <= r + dr < h and 0 <= c + dc < w and out[r + dr][c + dc] == 0: out[r + dr][c + dc] = col
    return out
rule("grow_objects_one_cell", "Every object grows by one cell up, down, left and right in its own colour.", gi_dilate, tf_dilate)
