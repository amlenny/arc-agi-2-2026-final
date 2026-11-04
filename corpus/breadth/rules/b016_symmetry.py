# b016_symmetry.py -- SYMMETRY DETECTION AND REPAIR: mark or remove the cells that break a symmetric picture,
# add the fewest cells to restore it, draw the axis, classify the grid's symmetry group, recolour objects by
# which symmetries they hold (up-down, point, diagonal, quarter-turn, type, order), find the odd/asymmetric
# object, join mirrored dot pairs, mirror objects only when partnered or touching the axis, complete objects
# about their own grey pivot or axis, and count symmetric vs asymmetric objects.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

GREY = 5


# ---- local helpers -------------------------------------------------------------------------------------
def _dims(rng, lo=6, hi=18, big=0.35):
    if rng.random() < big:
        return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _noise(rng, h, w, pal, dens):
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < dens:
                g[r][c] = rng.choice(pal)
    return g


def _sym(g, kind):
    """Copy the canonical half over the other so the grid gains the named symmetries (lr, ud, rot, diag)."""
    h, w = dims(g); out = copy(g)
    if 'lr' in kind:
        out = [row[:(w + 1) // 2] + row[:w // 2][::-1] for row in out]
    if 'ud' in kind:
        out = out[:(h + 1) // 2] + [row[:] for row in out[:h // 2][::-1]]
    if 'rot' in kind:
        for r in range(h):
            for c in range(w):
                if (r, c) < (h - 1 - r, w - 1 - c):
                    out[h - 1 - r][w - 1 - c] = out[r][c]
    if 'diag' in kind:
        for r in range(h):
            for c in range(r):
                out[r][c] = out[c][r]
    return out


def _norm(cs):
    r0 = min(r for r, _ in cs); c0 = min(c for _, c in cs)
    return frozenset((r - r0, c - c0) for r, c in cs)


def _hw(cs):
    return max(r for r, _ in cs) + 1, max(c for _, c in cs) + 1


def _xf(cs, kind, box=None):
    """The named rigid image of a normalised cell set within its bounding box (or the given square box)."""
    h, w = box or _hw(cs)
    f = {'lr': lambda r, c: (r, w - 1 - c), 'ud': lambda r, c: (h - 1 - r, c), 'rot': lambda r, c: (h - 1 - r, w - 1 - c),
         'rot90': lambda r, c: (c, h - 1 - r), 'rot270': lambda r, c: (w - 1 - c, r), 'diag': lambda r, c: (c, r),
         'anti': lambda r, c: (w - 1 - c, h - 1 - r)}[kind]
    return frozenset(f(r, c) for r, c in cs)


def _is_sym(cs, kind):
    n = _norm(cs); return n == _xf(n, kind)


def _order(cs):
    n = _norm(cs); return 1 + sum(n == _xf(n, k) for k in ('lr', 'ud', 'rot', 'rot90', 'rot270', 'diag', 'anti'))


def _connected(cs):
    cs = set(cs); st = [next(iter(cs))]; seen = {st[0]}
    while st:
        y, x = st.pop()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if (y + dy, x + dx) in cs and (y + dy, x + dx) not in seen:
                    seen.add((y + dy, x + dx)); st.append((y + dy, x + dx))
    return len(seen) == len(cs)


def _sym_shape(rng, n, kinds):
    """A connected shape holding all the named symmetries: the group closure of a random shape in a square box."""
    for _ in range(60):
        s = _norm(random_shape(rng, n)); K = max(_hw(s))
        for _ in range(4):
            for k in kinds:
                s = s | _xf(s, k, (K, K))
        s = _norm(s)
        if len(s) <= 4 * n and _connected(s) and all(_is_sym(s, k) for k in kinds):
            return s
    return None


def _asym_shape(rng, n, kinds):
    for _ in range(60):
        s = _norm(random_shape(rng, n))
        if not any(_is_sym(s, k) for k in kinds):
            return s
    return None


def _blobs(g, bg=0):
    """8-connected components of non-background cells regardless of colour (glib.components splits by colour)."""
    H, W = dims(g); seen = set(); out = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or (r, c) in seen:
                continue
            comp, st = [], [(r, c)]; seen.add((r, c))
            while st:
                y, x = st.pop(); comp.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen and g[ny][nx] != bg:
                            seen.add((ny, nx)); st.append((ny, nx))
            out.append(comp)
    return out


def _col(g, o):
    return g[o[0][0]][o[0][1]]


def _mixed_scene(rng, kinds, pal, lo=7, hi=18, need_both=True, p_sym=0.5):
    """k objects, each either holding all `kinds` symmetries or none of them; both sorts present if need_both."""
    h, w = _dims(rng, lo, hi); big = h >= 21
    k = rng.randint(5, 10) if big else rng.randint(3, 5); shapes = []
    for _ in range(k):
        n = rng.randint(3, 9 if big else 7)
        s = _sym_shape(rng, n, kinds) if rng.random() < p_sym else _asym_shape(rng, n, kinds)
        if s is None:
            return None
        shapes.append(s)
    flags = [all(_is_sym(s, k_) for k_ in kinds) for s in shapes]
    if need_both and len(set(flags)) < 2:
        return None
    g = blank(h, w)
    if place_shapes(rng, g, shapes, [rng.choice(pal) for _ in shapes], margin=1) is None:
        return None
    return g if len(objects(g, 0)) == k else None


def _pal(rng, k_lo=1, k_hi=3, exclude=(0, GREY)):
    return colours(rng, rng.randint(k_lo, k_hi), exclude=exclude)


# ---- 1-2 left-right extras: mark grey / remove ---------------------------------------------------------
def gi_lr_extras(rng):
    h, w = _dims(rng); pal = _pal(rng)
    g = _sym(_noise(rng, h, w, pal, rng.uniform(.15, .4)), 'lr')
    free = [(r, c) for r in range(h) for c in range(w) if g[r][c] == 0 and c != w - 1 - c and g[r][w - 1 - c] == 0]
    rng.shuffle(free); used = set()
    for r, c in free[:rng.randint(1, 6)]:
        if (r, w - 1 - c) not in used:
            g[r][c] = rng.choice(pal); used.add((r, c))
    return g


def tf_mark_lr_extras(g):
    h, w = dims(g); out = copy(g); n = 0
    for r in range(h):
        for c in range(w):
            if g[r][c] and g[r][w - 1 - c] == 0:
                out[r][c] = GREY; n += 1
    return out if n else None


def tf_remove_lr_extras(g):
    h, w = dims(g); out = copy(g); n = 0
    for r in range(h):
        for c in range(w):
            if g[r][c] and g[r][w - 1 - c] == 0:
                out[r][c] = 0; n += 1
    return out if n else None


rule("mark_leftright_extra_cells_grey", "The picture is left-right symmetric except for a few extra cells with no mirror partner; those cells become grey.", gi_lr_extras, tf_mark_lr_extras)
rule("remove_leftright_extra_cells", "The picture is left-right symmetric except for a few extra cells with no mirror partner; those cells are erased.", gi_lr_extras, tf_remove_lr_extras)


# ---- 3-4 scattered missing cells restored (up-down, point) ---------------------------------------------
def _holes(rng, g, partner):
    h, w = dims(g)
    cells_ = [(r, c) for r in range(h) for c in range(w) if g[r][c] and partner(r, c) != (r, c)]
    rng.shuffle(cells_); gone = set()
    for r, c in cells_[:rng.randint(1, 8)]:
        if partner(r, c) not in gone:
            g[r][c] = 0; gone.add((r, c))
    return g if gone else None


def gi_ud_holes(rng):
    h, w = _dims(rng); g = _sym(_noise(rng, h, w, _pal(rng, 1, 4, (0,)), rng.uniform(.2, .45)), 'ud')
    return _holes(rng, g, lambda r, c: (h - 1 - r, c))


def tf_ud_holes(g):
    h, w = dims(g)
    return [[g[r][c] or g[h - 1 - r][c] for c in range(w)] for r in range(h)]


def gi_rot_holes(rng):
    h, w = _dims(rng); g = _sym(_noise(rng, h, w, _pal(rng, 1, 4, (0,)), rng.uniform(.2, .45)), 'rot')
    return _holes(rng, g, lambda r, c: (h - 1 - r, w - 1 - c))


def tf_rot_holes(g):
    h, w = dims(g)
    return [[g[r][c] or g[h - 1 - r][w - 1 - c] for c in range(w)] for r in range(h)]


rule("add_updown_missing_cells", "The picture is top-bottom symmetric with scattered cells missing; each empty cell takes the colour of its vertical mirror partner.", gi_ud_holes, tf_ud_holes)
rule("add_point_symmetric_missing_cells", "The picture is symmetric under a half turn with scattered cells missing; each empty cell takes the colour of the cell opposite it through the centre.", gi_rot_holes, tf_rot_holes)


# ---- 5 remove to four-fold symmetric ---------------------------------------------------------------------
def gi_four_extras(rng):
    h, w = _dims(rng); pal = _pal(rng, 1, 3, (0,))
    g = _sym(_noise(rng, h, w, pal, rng.uniform(.15, .35)), 'lrud')
    mates = lambda r, c: {(r, w - 1 - c), (h - 1 - r, c), (h - 1 - r, w - 1 - c)}
    free = [(r, c) for r in range(h) for c in range(w) if g[r][c] == 0 and (r, c) not in mates(r, c)
            and all(g[y][x] == 0 for y, x in mates(r, c))]
    rng.shuffle(free); used = set()
    for r, c in free[:rng.randint(1, 8)]:
        if not (mates(r, c) & used):
            g[r][c] = rng.choice(pal); used.add((r, c))
    return g if used else None


def tf_four_extras(g):
    h, w = dims(g)
    return [[g[r][c] if g[r][c] == g[r][w - 1 - c] == g[h - 1 - r][c] == g[h - 1 - r][w - 1 - c] else 0
             for c in range(w)] for r in range(h)]


rule("remove_to_fourfold_symmetric", "Only cells that have the same colour at all four mirror positions (left-right and top-bottom) stay; every other cell is erased.", gi_four_extras, tf_four_extras)


# ---- 6 four-fold defects marked grey -----------------------------------------------------------------
def gi_four_defects(rng):
    h, w = _dims(rng); pal = _pal(rng, 2, 4)
    g = _sym(_noise(rng, h, w, pal, rng.uniform(.5, .85)), 'lrud')
    mates = lambda r, c: {(r, w - 1 - c), (h - 1 - r, c), (h - 1 - r, w - 1 - c)}
    cand = [(r, c) for r in range(h) for c in range(w) if (r, c) not in mates(r, c)]
    rng.shuffle(cand); used = set()
    for r, c in cand[:rng.randint(1, 6)]:
        if not ((mates(r, c) | {(r, c)}) & used):
            g[r][c] = rng.choice([v for v in pal + [0] if v != g[r][c]]); used |= mates(r, c) | {(r, c)}
    return g


def tf_four_defects(g):
    h, w = dims(g); out = copy(g); n = 0
    for r in range(h):
        for c in range(w):
            m = (g[r][w - 1 - c], g[h - 1 - r][c], g[h - 1 - r][w - 1 - c])
            if m[0] == m[1] == m[2] != g[r][c]:
                out[r][c] = GREY; n += 1
    return out if n else None


rule("mark_fourfold_defects_grey", "The picture is mirror-symmetric both ways except for a few cells; a cell whose three mirror positions all agree on a different colour becomes grey.", gi_four_defects, tf_four_defects)


# ---- 7 diagonal extras marked ----------------------------------------------------------------------------
def gi_diag_extras(rng):
    n = rng.randint(21, 30) if rng.random() < .35 else rng.randint(6, 18); pal = _pal(rng)
    g = _sym(_noise(rng, n, n, pal, rng.uniform(.15, .4)), 'diag')
    free = [(r, c) for r in range(n) for c in range(n) if r != c and g[r][c] == 0 and g[c][r] == 0]
    rng.shuffle(free); used = set()
    for r, c in free[:rng.randint(1, 6)]:
        if (c, r) not in used:
            g[r][c] = rng.choice(pal); used.add((r, c))
    return g


def tf_diag_extras(g):
    n = len(g); out = copy(g); k = 0
    for r in range(n):
        for c in range(n):
            if g[r][c] and g[c][r] == 0:
                out[r][c] = GREY; k += 1
    return out if k else None


rule("mark_diagonal_extra_cells_grey", "The square picture is symmetric across its main diagonal except for a few extra cells whose transposed partner is empty; those cells become grey.", gi_diag_extras, tf_diag_extras)


# ---- 8-9 draw the single symmetric object's axis -------------------------------------------------------
def _axis_scene(rng, kind):
    h, w = _dims(rng); big = h >= 21
    for _ in range(40):
        s = _sym_shape(rng, rng.randint(4, 12 if big else 7), [kind])
        if s and _hw(s)[1 if kind == 'lr' else 0] % 2 == 1 and min(_hw(s)) >= 2:
            break
    else:
        return None
    a = _asym_shape(rng, rng.randint(3, 7), [kind]); c1, c2 = colours(rng, 2, (0, GREY))
    g = blank(h, w)
    if place_shapes(rng, g, [s, a], [c1, c2], margin=1) is None:
        return None
    return g if len(objects(g, 0)) == 2 else None


def gi_vaxis(rng):
    return _axis_scene(rng, 'lr')


def tf_vaxis(g):
    obs = [o for o in objects(g, 0) if _is_sym(o, 'lr') and (bbox(o)[3] - bbox(o)[1]) % 2 == 0]
    if len(obs) != 1:
        return None
    r0, c0, r1, c1 = bbox(obs[0]); ca = (c0 + c1) // 2; out = copy(g)
    for r in range(len(g)):
        if out[r][ca] == 0:
            out[r][ca] = GREY
    return out


def gi_haxis(rng):
    return _axis_scene(rng, 'ud')


def tf_haxis(g):
    obs = [o for o in objects(g, 0) if _is_sym(o, 'ud') and (bbox(o)[2] - bbox(o)[0]) % 2 == 0]
    if len(obs) != 1:
        return None
    r0, c0, r1, c1 = bbox(obs[0]); ra = (r0 + r1) // 2; out = copy(g)
    for c in range(len(g[0])):
        if out[ra][c] == 0:
            out[ra][c] = GREY
    return out


rule("draw_vertical_axis_of_symmetric_object", "One of the two objects is left-right symmetric; a grey line is drawn down the whole grid along that object's axis column, over empty cells.", gi_vaxis, tf_vaxis)
rule("draw_horizontal_axis_of_symmetric_object", "One of the two objects is top-bottom symmetric; a grey line is drawn across the whole grid along that object's axis row, over empty cells.", gi_haxis, tf_haxis)


# ---- 10 whole-grid axes drawn ----------------------------------------------------------------------------
def gi_grid_axes(rng):
    big = rng.random() < .35
    h = rng.choice(range(21, 30, 2)) if big else rng.choice(range(5, 19, 2))
    w = rng.choice(range(21, 30, 2)) if big else rng.choice(range(5, 19, 2))
    kind = rng.choice(['lr', 'ud', 'lrud'])
    g = _sym(_noise(rng, h, w, _pal(rng, 1, 4), rng.uniform(.25, .45)), kind)
    return g


def tf_grid_axes(g):
    h, w = dims(g); lr = g == flip_h(g); ud = g == flip_v(g)
    if not (lr or ud):
        return None
    out = copy(g)
    if lr:
        for r in range(h):
            out[r][w // 2] = GREY
    if ud:
        out[h // 2] = [GREY] * w
    return out


rule("draw_all_grid_symmetry_axes", "A grey line is drawn through the grid's centre column if the whole picture is left-right symmetric and through its centre row if it is top-bottom symmetric.", gi_grid_axes, tf_grid_axes)


# ---- 11 whole-grid symmetry group as a background code ---------------------------------------
def gi_group(rng):
    h, w = _dims(rng, 5, 16); kind = rng.choice(['lr', 'ud', 'lrud', 'rot', 'none'])
    g = _noise(rng, h, w, colours(rng, rng.randint(1, 3), (0, 1, 2, 3, 4, 5)), rng.uniform(.25, .5))
    return _sym(g, kind) if kind != 'none' else g


def _group(g):
    lr = g == flip_h(g); ud = g == flip_v(g); rot = g == flip_h(flip_v(g))
    return 3 if lr and ud else 1 if lr else 2 if ud else 4 if rot else 5


def tf_group_bg(g):
    k = _group(g)
    return [[v if v else k for v in row] for row in g]


rule("background_coded_by_grid_symmetry", "The background is flooded with a code colour for the whole picture's symmetry: 1 left-right only, 2 top-bottom only, 3 both, 4 half-turn only, 5 none.", gi_group, tf_group_bg, digits=True)


# ---- 12 symmetrize each object by adding its mirror cells --------------------------------------------------
def gi_obj_symmetrize(rng):
    h, w = _dims(rng, 8, 18); big = h >= 21; k = rng.randint(5, 9) if big else rng.randint(2, 5)
    shapes = [_norm(random_shape(rng, rng.randint(3, 7))) for _ in range(k)]
    if all(_is_sym(s, 'lr') for s in shapes):
        return None
    g = blank(h, w)
    if place_shapes(rng, g, shapes, [rng.choice(_pal(rng, 2, 4, (0,))) for _ in shapes], margin=2) is None:
        return None
    return g if len(objects(g, 0)) == k else None


def tf_obj_symmetrize(g):
    out = copy(g)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o); v = _col(g, o)
        for r, c in o: out[r][c0 + c1 - c] = v
    return out


rule("symmetrize_each_object_by_adding", "Each object gains the mirror image of its own cells within its bounding box, so every object becomes left-right symmetric with the fewest added cells.", gi_obj_symmetrize, tf_obj_symmetrize)


# ---- 13-16 recolour objects symmetric vs not, by kind --------------------------------------------------
def _recolour_by(kind):
    def tf(g):
        out = copy(g)
        for o in objects(g, 0):
            v = 1 if _is_sym(o, kind) else 2
            for r, c in o: out[r][c] = v
        return out
    return tf


def gi_ud_objs(rng): return _mixed_scene(rng, ['ud'], colours(rng, 4, (0, 1, 2)))
def gi_rot_objs(rng): return _mixed_scene(rng, ['rot'], colours(rng, 4, (0, 1, 2)))
def gi_diag_objs(rng): return _mixed_scene(rng, ['diag'], colours(rng, 4, (0, 1, 2)))
def gi_rot90_objs(rng): return _mixed_scene(rng, ['rot90'], colours(rng, 4, (0, 1, 2)), p_sym=0.55)


rule("recolour_updown_symmetric_objects", "Objects that are top-bottom symmetric become 1; objects that are not become 2.", gi_ud_objs, _recolour_by('ud'))
rule("recolour_point_symmetric_objects", "Objects that look the same after a half turn become 1; objects that do not become 2.", gi_rot_objs, _recolour_by('rot'))
rule("recolour_diagonal_symmetric_objects", "Objects that are symmetric across their main diagonal (unchanged by transposing) become 1; objects that are not become 2.", gi_diag_objs, _recolour_by('diag'))
rule("recolour_quarter_turn_symmetric_objects", "Objects that look the same after a quarter turn become 1; objects that do not become 2.", gi_rot90_objs, _recolour_by('rot90'))


# ---- 17 symmetry type code ----------------------------------------------------------------------------------
def gi_sym_type(rng):
    h, w = _dims(rng, 8, 18); big = h >= 21; k = rng.randint(5, 10) if big else rng.randint(3, 5); shapes = []
    for _ in range(k):
        t = rng.choice(['lr', 'ud', 'both', 'none']); n = rng.randint(3, 8 if big else 6)
        s = (_asym_shape(rng, n, ['lr', 'ud']) if t == 'none' else _sym_shape(rng, n, ['lr', 'ud'] if t == 'both' else [t]))
        if s is None:
            return None
        shapes.append(s)
    codes = {_type_code(s) for s in shapes}
    if len(codes) < 2:
        return None
    g = blank(h, w)
    if place_shapes(rng, g, shapes, [rng.choice(colours(rng, 3, (0, 1, 2, 3, 4))) for _ in shapes], margin=1) is None:
        return None
    return g if len(objects(g, 0)) == k else None


def _type_code(o):
    lr, ud = _is_sym(o, 'lr'), _is_sym(o, 'ud')
    return 3 if lr and ud else 1 if lr else 2 if ud else 4


def tf_sym_type(g):
    out = copy(g)
    for o in objects(g, 0):
        for r, c in o: out[r][c] = _type_code(o)
    return out


rule("recolour_objects_by_symmetry_type", "Each object is recoloured by its symmetry: 1 left-right only, 2 top-bottom only, 3 both, 4 neither.", gi_sym_type, tf_sym_type, digits=True)


# ---- 18 symmetry order ----------------------------------------------------------------------------------------
def gi_order(rng):
    h, w = _dims(rng, 8, 18); big = h >= 21; k = rng.randint(5, 10) if big else rng.randint(3, 5); shapes = []
    for _ in range(k):
        n = rng.randint(3, 7); t = rng.choice(['plain', 'lr', 'four', 'rot90', 'rot'])
        s = _norm(random_shape(rng, n)) if t == 'plain' else _sym_shape(rng, n, {'lr': ['lr'], 'four': ['lr', 'ud'], 'rot90': ['rot90'], 'rot': ['rot']}[t])
        if s is None:
            return None
        shapes.append(s)
    if len({_order(s) for s in shapes}) < 2:
        return None
    g = blank(h, w)
    if place_shapes(rng, g, shapes, [rng.choice(colours(rng, 3, (0, 1, 2, 4, 8))) for _ in shapes], margin=1) is None:
        return None
    return g if len(objects(g, 0)) == k else None


def tf_order(g):
    out = copy(g)
    for o in objects(g, 0):
        for r, c in o: out[r][c] = _order(o)
    return out


rule("recolour_objects_by_symmetry_order", "Each object is recoloured by how many of the eight rotations and reflections leave it unchanged: 1, 2, 4 or 8.", gi_order, tf_order, digits=True)


# ---- 19 panel that mirrors the first ---------------------------------------------------------------------
def gi_panel(rng):
    P = rng.randint(3, 4); pw = rng.randint(3, 6 if P == 4 else 9)
    ph = rng.randint(21, 30) if rng.random() < .35 else rng.randint(3, 12)
    pal = _pal(rng, 2, 3); base = _noise(rng, ph, pw, pal, rng.uniform(.3, .6))
    if base == flip_h(base) or not any(v for row in base for v in row):
        return None
    j = rng.randint(1, P - 1); panels = [base]
    for i in range(1, P):
        if i == j:
            panels.append(flip_h(base))
        else:
            q = _noise(rng, ph, pw, pal, rng.uniform(.3, .6))
            if q in (base, flip_h(base)):
                return None
            panels.append(q)
    return [sum((p[r] + ([GREY] if i < P - 1 else []) for i, p in enumerate(panels)), []) for r in range(ph)]


def tf_panel(g):
    h, w = dims(g); seps = [c for c in range(w) if all(g[r][c] == GREY for r in range(h))]
    b = [-1] + seps + [w]; panels = [[row[a + 1:z] for row in g] for a, z in zip(b, b[1:])]
    m = [p for p in panels[1:] if p == flip_h(panels[0])]
    return m[0] if len(m) == 1 else None


rule("crop_panel_mirroring_first", "Panels are separated by grey lines; output the one panel that is the left-right mirror image of the leftmost panel.", gi_panel, tf_panel)


# ---- 20 the only asymmetric object ------------------------------------------------------------------------
def gi_odd_asym(rng):
    h, w = _dims(rng, 8, 18); big = h >= 21; k = rng.randint(5, 10) if big else rng.randint(3, 5)
    shapes = [_sym_shape(rng, rng.randint(3, 7), ['lr']) for _ in range(k - 1)] + [_asym_shape(rng, rng.randint(3, 7), ['lr'])]
    if any(s is None for s in shapes):
        return None
    rng.shuffle(shapes); g = blank(h, w)
    if place_shapes(rng, g, shapes, [rng.choice(_pal(rng, 2, 4)) for _ in shapes], margin=1) is None:
        return None
    return g if len(objects(g, 0)) == k else None


def tf_odd_asym(g):
    odd = [o for o in objects(g, 0) if not _is_sym(o, 'lr')]
    return crop(g, *bbox(odd[0])) if len(odd) == 1 else None


rule("crop_only_asymmetric_object", "Every object is left-right symmetric except one; output that object's bounding box.", gi_odd_asym, tf_odd_asym)


# ---- 21 mirrored dot pairs joined -------------------------------------------------------------------------
def gi_dot_pairs(rng):
    h, w = _dims(rng, 6, 18); g = blank(h, w); rows = list(range(h)); rng.shuffle(rows)
    k = rng.randint(2, 4) if h < 21 else rng.randint(4, 9); m = rng.randint(1, 3) if h < 21 else rng.randint(2, 6)
    for i, r in enumerate(rows[:k + m]):
        col = rng.choice(COLOURS)
        if i < k:
            c = rng.randint(0, w // 2 - 2) if w // 2 >= 2 else None
            if c is None or w - 1 - c - c < 2:
                return None
            g[r][c] = g[r][w - 1 - c] = col
        else:
            c = rng.randrange(w)
            if c != w - 1 - c:
                g[r][c] = col
    return g if k + m <= h else None


def tf_dot_pairs(g):
    h, w = dims(g); out = copy(g); n = 0
    for r in range(h):
        for c in range(w // 2):
            if g[r][c] and g[r][c] == g[r][w - 1 - c]:
                for x in range(c, w - c): out[r][x] = g[r][c]
                n += 1
    return out if n else None


rule("join_mirrored_dot_pairs", "Two dots of one colour that mirror each other across the grid's centre column are joined by a line of that colour; dots without a mirror partner stay as they are.", gi_dot_pairs, tf_dot_pairs)


# ---- 22 mirror only objects with a partner marker ----------------------------------------------------------
def gi_partner(rng):
    h, ca = _dims(rng, 8, 14); ca = min(ca, 14); w = 2 * ca + 1; big = h >= 21
    k = rng.randint(4, 7) if big else rng.randint(2, 4); left = blank(h, ca)
    shapes = [random_shape(rng, rng.randint(3, 6)) for _ in range(k)]; pal = colours(rng, k, (0, GREY))
    if place_shapes(rng, left, shapes, pal, margin=1) is None:
        return None
    g = [row + [GREY] + [0] * ca for row in left]
    obs = objects(left, 0)
    if len(obs) != k:
        return None
    rng.shuffle(obs)
    for o in obs[:rng.randint(1, k - 1)]:
        r, c = rng.choice(o); g[r][2 * ca - c] = left[r][c]
    return g


def tf_partner(g):
    h, w = dims(g); ca = w // 2; out = copy(g); n = 0
    for o in objects(g, 0):
        v = _col(g, o)
        if v == GREY or any(c >= ca for _, c in o):
            continue
        if any(g[r][2 * ca - c] == v for r, c in o):
            for r, c in o: out[r][2 * ca - c] = v
            n += 1
    return out if n else None


rule("mirror_objects_with_partner_marker", "A grey line divides the grid; an object on the left is reflected across the line only if a dot of its own colour already sits somewhere in its mirror footprint.", gi_partner, tf_partner)


# ---- 23 mirror only objects touching the axis ------------------------------------------------------------
def gi_touch_axis(rng):
    h, ca = _dims(rng, 8, 14); ca = min(ca, 14); w = 2 * ca + 1; big = h >= 21
    for _ in range(20):
        k = rng.randint(4, 7) if big else rng.randint(2, 4); left = blank(h, ca)
        shapes = [random_shape(rng, rng.randint(3, 6)) for _ in range(k)]
        if place_shapes(rng, left, shapes, [rng.choice(colours(rng, 3, (0, GREY))) for _ in shapes], margin=1) is None:
            continue
        obs = objects(left, 0)
        touch = [any(c == ca - 1 for _, c in o) for o in obs]
        if len(obs) == k and len(set(touch)) == 2:
            return [row + [GREY] + [0] * ca for row in left]
    return None


def tf_touch_axis(g):
    h, w = dims(g); ca = w // 2; out = copy(g); n = 0
    for o in objects(g, 0):
        v = _col(g, o)
        if v == GREY or any(c >= ca for _, c in o) or not any(c == ca - 1 for _, c in o):
            continue
        for r, c in o: out[r][2 * ca - c] = v
        n += 1
    return out if n else None


rule("mirror_only_objects_touching_axis", "A grey line divides the grid; only the objects that touch the line are reflected across it, the others stay unmirrored.", gi_touch_axis, tf_touch_axis)


# ---- 24 delete point-asymmetric objects ----------------------------------------------------------------
def gi_del_rot(rng):
    return _mixed_scene(rng, ['rot'], _pal(rng, 2, 4, (0,)))


def tf_del_rot(g):
    out = copy(g)
    for o in objects(g, 0):
        if not _is_sym(o, 'rot'):
            for r, c in o: out[r][c] = 0
    return out


rule("delete_point_asymmetric_objects", "Objects that do not look the same after a half turn are erased; the point-symmetric ones stay.", gi_del_rot, tf_del_rot)


# ---- 25-26 mark each symmetric object's own axis column / centre cell ------------------------------------
def gi_obj_axis(rng):
    g = _mixed_scene(rng, ['lr'], _pal(rng, 2, 4))
    if g is None:
        return None
    return g if any(_is_sym(o, 'lr') and (bbox(o)[3] - bbox(o)[1]) % 2 == 0 for o in objects(g, 0)) else None


def tf_obj_axis(g):
    out = copy(g)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o)
        if _is_sym(o, 'lr') and (c1 - c0) % 2 == 0:
            for r, c in o:
                if c == (c0 + c1) // 2: out[r][c] = GREY
    return out


def gi_obj_centre(rng):
    g = _mixed_scene(rng, ['rot'], _pal(rng, 2, 4))
    if g is None:
        return None
    return g if any(_is_sym(o, 'rot') and (bbox(o)[3] - bbox(o)[1]) % 2 == 0 and (bbox(o)[2] - bbox(o)[0]) % 2 == 0 for o in objects(g, 0)) else None


def tf_obj_centre(g):
    out = copy(g)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o)
        if _is_sym(o, 'rot') and (c1 - c0) % 2 == 0 and (r1 - r0) % 2 == 0:
            out[(r0 + r1) // 2][(c0 + c1) // 2] = GREY
    return out


rule("mark_object_axis_column_grey", "Every left-right symmetric object of odd width has the cells on its own centre column recoloured grey; other objects are untouched.", gi_obj_axis, tf_obj_axis)
rule("mark_point_symmetric_centres_grey", "Every half-turn symmetric object with odd height and width gets a grey cell at the centre of its bounding box; other objects are untouched.", gi_obj_centre, tf_obj_centre)


# ---- 27 restore one missing cell per symmetric object ----------------------------------------------------
def gi_restore(rng):
    h, w = _dims(rng, 8, 18); big = h >= 21; k = rng.randint(4, 8) if big else rng.randint(2, 4); shapes = []
    for _ in range(k):
        s = _sym_shape(rng, rng.randint(4, 8), ['lr'])
        if s is None:
            return None
        sh, sw = _hw(s)
        cand = [(r, c) for r, c in s if 2 * c != sw - 1 and any((r, x) in s for x in range(sw) if x != c)
                and any((y, c) in s for y in range(sh) if y != r) and _connected(s - {(r, c)})]
        if not cand:
            return None
        shapes.append(s - {rng.choice(sorted(cand))})
    g = blank(h, w)
    if place_shapes(rng, g, shapes, [rng.choice(_pal(rng, 2, 4, (0,))) for _ in shapes], margin=1) is None:
        return None
    return g if len(objects(g, 0)) == k else None


def tf_restore(g):
    out = copy(g); n = 0
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o); v = _col(g, o)
        for r, c in o:
            if out[r][c0 + c1 - c] == 0:
                out[r][c0 + c1 - c] = v; n += 1
    return out if n else None


rule("restore_missing_cell_per_symmetric_object", "Each object is meant to be left-right symmetric but has one cell missing; the missing cell is filled in from its mirror partner.", gi_restore, tf_restore)


# ---- 28 grey axis segment between mirror twins ----------------------------------------------------------
def gi_twin_axis(rng):
    h, w = _dims(rng, 8, 18); big = h >= 21; k = rng.randint(2, 4) if big else rng.randint(1, 2)
    shapes, cols = [], []
    for _ in range(k):
        s = _asym_shape(rng, rng.randint(3, 6), ['lr'])
        if s is None:
            return None
        sw = _hw(s)[1]; gap = rng.choice([1, 3, 5])
        shapes.append(s | {(r, c + sw + gap) for r, c in _xf(s, 'lr')}); cols.append(rng.choice(colours(rng, 1, (0, GREY))))
    for _ in range(rng.randint(0, 2)):
        a = _asym_shape(rng, rng.randint(3, 6), ['lr'])
        if a is None:
            return None
        shapes.append(a); cols.append(rng.choice(colours(rng, 1, (0, GREY))))
    g = blank(h, w)
    if place_shapes(rng, g, shapes, cols, margin=1) is None:
        return None
    return g if len(objects(g, 0)) == len(shapes) + k else None


def tf_twin_axis(g):
    obs = objects(g, 0); out = copy(g); n = 0
    for a in obs:
        for b in obs:
            ra, rb = bbox(a), bbox(b)
            if a is b or (ra[0], ra[2]) != (rb[0], rb[2]) or rb[1] <= ra[3] or _col(g, a) != _col(g, b):
                continue
            gap = rb[1] - ra[3] - 1
            if gap % 2 == 0 or _norm(b) != _xf(_norm(a), 'lr'):
                continue
            cm = ra[3] + 1 + gap // 2
            for r in range(ra[0], ra[2] + 1): out[r][cm] = GREY
            n += 1
    return out if n else None


rule("axis_segment_between_mirror_twins", "Where an object and its left-right mirror image sit side by side on the same rows, a grey segment is drawn down the midline between them; lone objects get nothing.", gi_twin_axis, tf_twin_axis)


# ---- 29 erase objects without a mirror twin -------------------------------------------------------------------
def gi_twins(rng):
    h, w = _dims(rng, 8, 18); big = h >= 21; k = rng.randint(2, 4) if big else rng.randint(1, 2)
    shapes = []
    for _ in range(k):
        s = _norm(random_shape(rng, rng.randint(3, 6))); shapes += [s, _xf(s, 'lr')]
    for _ in range(rng.randint(1, 3) if not big else rng.randint(2, 4)):
        a = _norm(random_shape(rng, rng.randint(3, 6)))
        if any(a == _xf(s, 'lr') for s in shapes):
            return None
        shapes.append(a)
    g = blank(h, w)
    if place_shapes(rng, g, shapes, [rng.choice(_pal(rng, 2, 4, (0,))) for _ in shapes], margin=1) is None:
        return None
    return g if len(objects(g, 0)) == len(shapes) else None


def tf_twins(g):
    obs = objects(g, 0); norms = [_norm(o) for o in obs]; out = copy(g); n = 0
    for i, o in enumerate(obs):
        if not any(j != i and norms[j] == _xf(norms[i], 'lr') for j in range(len(obs))):
            for r, c in o: out[r][c] = 0
            n += 1
    return out if n else None


rule("erase_objects_without_mirror_twin", "An object survives only if some other object is its left-right mirror image; objects with no mirror twin anywhere are erased.", gi_twins, tf_twins)


# ---- 30-31 colour mismatches across the axis: repair right from left / mark both ---------------------------
def gi_colour_mismatch(rng):
    h, w = _dims(rng); pal = _pal(rng, 2, 4)
    g = _sym(_noise(rng, h, w, pal, rng.uniform(.3, .6)), 'lr')
    right = [(r, c) for r in range(h) for c in range(w) if c > w - 1 - c and g[r][c]]
    if not right:
        return None
    for r, c in rng.sample(right, min(len(right), rng.randint(1, 6))):
        g[r][c] = rng.choice([v for v in pal if v != g[r][c]])
    return g


def tf_repaint_right(g):
    h, w = dims(g); out = copy(g); n = 0
    for r in range(h):
        for c in range(w):
            if c > w - 1 - c and g[r][c] and g[r][w - 1 - c] and g[r][c] != g[r][w - 1 - c]:
                out[r][c] = g[r][w - 1 - c]; n += 1
    return out if n else None


def tf_mark_mismatch(g):
    h, w = dims(g); out = copy(g); n = 0
    for r in range(h):
        for c in range(w):
            if g[r][c] and g[r][w - 1 - c] and g[r][c] != g[r][w - 1 - c]:
                out[r][c] = GREY; n += 1
    return out if n else None


rule("repaint_right_half_to_match_left_colours", "The picture's shape is left-right symmetric but some cells on the right have the wrong colour; each is repainted with its mirror partner's colour.", gi_colour_mismatch, tf_repaint_right)
rule("mark_colour_mismatched_mirror_cells", "The picture's shape is left-right symmetric; wherever a cell and its mirror partner differ in colour, both cells become grey.", gi_colour_mismatch, tf_mark_mismatch)


# ---- 32 the odd quadrant filled grey -------------------------------------------------------------------------
def gi_quad(rng):
    big = rng.random() < .35
    ph, pw = (rng.randint(11, 15), rng.randint(11, 15)) if big else (rng.randint(3, 9), rng.randint(3, 9))
    pal = _pal(rng, 1, 3); q = _noise(rng, ph, pw, pal, rng.uniform(.3, .7))
    g = [row + row[::-1] for row in q]; g = g + [row[:] for row in g[::-1]]
    qi = rng.randrange(4); r_off = (qi // 2) * ph; c_off = (qi % 2) * pw; before = copy(g)
    for _ in range(rng.randint(1, 3)):
        r, c = r_off + rng.randrange(ph), c_off + rng.randrange(pw)
        g[r][c] = rng.choice([v for v in pal + [0] if v != g[r][c]])
    return g if g != before else None


def tf_quad(g):
    h, w = dims(g); ph, pw = h // 2, w // 2
    tl = crop(g, 0, 0, ph - 1, pw - 1); tr = flip_h(crop(g, 0, pw, ph - 1, w - 1))
    bl = flip_v(crop(g, ph, 0, h - 1, pw - 1)); br = flip_h(flip_v(crop(g, ph, pw, h - 1, w - 1)))
    qs = [tl, tr, bl, br]
    odd = [i for i in range(4) if all(qs[j] == qs[k] for j in range(4) for k in range(4) if i not in (j, k)) and qs[i] != qs[(i + 1) % 4]]
    if len(odd) != 1:
        return None
    i = odd[0]; out = copy(g)
    rect(out, (i // 2) * ph, (i % 2) * pw, (i // 2) * ph + ph - 1, (i % 2) * pw + pw - 1, GREY)
    return out


rule("odd_quadrant_filled_grey", "The four quadrants should be mirror images of each other; the one quadrant that breaks the symmetry is filled entirely grey.", gi_quad, tf_quad)


# ---- 33 handedness --------------------------------------------------------------------------------------------------
def gi_hand(rng):
    for _ in range(40):
        s = _norm(random_shape(rng, rng.randint(4, 7)))
        rots = {s, _xf(s, 'rot90'), _xf(s, 'rot'), _xf(s, 'rot270')}
        refl = {_xf(s, k) for k in ('lr', 'ud', 'diag', 'anti')}
        if not (rots & refl):
            break
    else:
        return None
    h, w = _dims(rng, 8, 18); big = h >= 21; k = rng.randint(5, 10) if big else rng.randint(3, 6)
    shapes = [rng.choice(sorted(rots, key=sorted) if rng.random() < .5 else sorted(refl, key=sorted)) for _ in range(k)]
    g = blank(h, w)
    if place_shapes(rng, g, shapes, [rng.choice(colours(rng, 3, (0, 1, 2))) for _ in shapes], margin=1) is None:
        return None
    if len(objects(g, 0)) != k:
        return None
    out = tf_hand(g)
    return g if out and len({v for row in out for v in row} - {0}) == 2 else None


def tf_hand(g):
    obs = sorted(objects(g, 0), key=lambda o: bbox(o)[:2])
    if not obs:
        return None
    ref = _norm(obs[0]); orbit = {ref, _xf(ref, 'rot90'), _xf(ref, 'rot'), _xf(ref, 'rot270')}; out = copy(g)
    for o in obs:
        v = 1 if _norm(o) in orbit else 2
        for r, c in o: out[r][c] = v
    return out


rule("recolour_by_handedness_vs_topmost", "All objects are the same shape turned or flipped; those that are a pure rotation of the topmost object become 1, those that are its mirror image become 2.", gi_hand, tf_hand)


# ---- 34 crop the most symmetric object -------------------------------------------------------------------------
def gi_most_sym(rng):
    h, w = _dims(rng, 8, 18); big = h >= 21; k = rng.randint(4, 8) if big else rng.randint(3, 5); shapes = []
    for _ in range(k):
        n = rng.randint(3, 7); t = rng.choice(['plain', 'plain', 'lr', 'ud', 'four', 'rot90'])
        s = _norm(random_shape(rng, n)) if t == 'plain' else _sym_shape(rng, n, {'lr': ['lr'], 'ud': ['ud'], 'four': ['lr', 'ud'], 'rot90': ['rot90']}[t])
        if s is None:
            return None
        shapes.append(s)
    orders = sorted(_order(s) for s in shapes)
    if orders[-1] == orders[-2]:
        return None
    top = max(shapes, key=_order)
    if len(top) == _hw(top)[0] * _hw(top)[1]:
        return None
    g = blank(h, w)
    if place_shapes(rng, g, shapes, [rng.choice(_pal(rng, 2, 4, (0,))) for _ in shapes], margin=1) is None:
        return None
    return g if len(objects(g, 0)) == k else None


def tf_most_sym(g):
    obs = sorted(objects(g, 0), key=_order)
    if len(obs) < 2 or _order(obs[-1]) == _order(obs[-2]):
        return None
    return crop(g, *bbox(obs[-1]))


rule("crop_most_symmetric_object", "Output the bounding box of the object with the most symmetries (the most rotations and reflections that leave it unchanged).", gi_most_sym, tf_most_sym)


# ---- 35 complete each object by a half turn about its grey pivot -------------------------------------------
def gi_pivot(rng):
    h, w = _dims(rng, 8, 18); big = h >= 21; k = rng.randint(3, 6) if big else rng.randint(1, 3)
    fulls, parts, pivots = [], [], []
    for _ in range(k):
        s = _norm(random_shape(rng, rng.randint(3, 6))); p = rng.choice(sorted(s))
        full = s | {(2 * p[0] - r, 2 * p[1] - c) for r, c in s}
        if full == s:
            return None
        r0 = min(r for r, _ in full); c0 = min(c for _, c in full)
        fulls.append(frozenset((r - r0, c - c0) for r, c in full)); parts.append({(r - r0, c - c0) for r, c in s}); pivots.append((p[0] - r0, p[1] - c0))
    g = blank(h, w); cols = [rng.choice(colours(rng, 3, (0, GREY))) for _ in fulls]
    pos = place_shapes(rng, g, fulls, cols, margin=1)
    if pos is None:
        return None
    for (r0, c0), full, part, (pr, pc), col in zip(pos, fulls, parts, pivots, cols):
        for r, c in full: g[r0 + r][c0 + c] = 0
        for r, c in part: g[r0 + r][c0 + c] = col
        g[r0 + pr][c0 + pc] = GREY
    return g


def tf_pivot(g):
    h, w = dims(g); out = copy(g)
    for b in _blobs(g):
        piv = [(r, c) for r, c in b if g[r][c] == GREY]
        if len(piv) != 1:
            return None
        pr, pc = piv[0]
        for r, c in b:
            if g[r][c] != GREY:
                y, x = 2 * pr - r, 2 * pc - c
                if not (0 <= y < h and 0 <= x < w):
                    return None
                out[y][x] = g[r][c]
    return out


rule("complete_object_half_turn_about_grey_pivot", "Each object holds one grey cell; the object's coloured cells are copied to their opposite positions through that grey cell so the object becomes point-symmetric about it.", gi_pivot, tf_pivot)


# ---- 36 complete each object across its grey axis column -----------------------------------------------------
def gi_grey_axis(rng):
    h, w = _dims(rng, 8, 18); big = h >= 21; k = rng.randint(3, 6) if big else rng.randint(1, 3)
    fulls, parts, cols = [], [], []
    for _ in range(k):
        s = _norm(random_shape(rng, rng.randint(3, 6))); sh, sw = _hw(s)
        axis = {(r, sw) for r in range(sh)}
        fulls.append(frozenset(s | axis | {(r, 2 * sw - c) for r, c in s})); parts.append(s | axis); cols.append(rng.choice(colours(rng, 3, (0, GREY))))
    g = blank(h, w); pos = place_shapes(rng, g, fulls, cols, margin=1)
    if pos is None:
        return None
    for (r0, c0), full, part, col in zip(pos, fulls, parts, cols):
        for r, c in full: g[r0 + r][c0 + c] = 0
        for r, c in part: g[r0 + r][c0 + c] = GREY if g[r0 + r][c0 + c] == 0 and c == max(x for _, x in part) else col
    return g


def tf_grey_axis(g):
    h, w = dims(g); out = copy(g)
    for b in _blobs(g):
        ax = {c for r, c in b if g[r][c] == GREY}
        if len(ax) != 1:
            return None
        ca = ax.pop()
        for r, c in b:
            if g[r][c] != GREY:
                x = 2 * ca - c
                if not 0 <= x < w:
                    return None
                out[r][x] = g[r][c]
    return out


rule("complete_object_across_its_grey_column", "Each object has a grey column on one side; the object's coloured cells are reflected across that grey column so each object becomes left-right symmetric about it.", gi_grey_axis, tf_grey_axis)


# ---- 37 count the symmetry-breaking cells ------------------------------------------------------------------
def tf_defect_count(g):
    h, w = dims(g); m = sum(1 for r in range(h) for c in range(w) if g[r][c] and g[r][w - 1 - c] == 0)
    return [[GREY] * m + [0] * (9 - m)] if 1 <= m <= 8 else None


rule("count_leftright_extra_cells_row", "Output a row of nine cells with as many grey cells, from the left, as there are cells breaking the picture's left-right symmetry.", gi_lr_extras, tf_defect_count)


# ---- 38 symmetric objects rise, asymmetric sink --------------------------------------------------------------
def gi_rise_sink(rng):
    h, w = _dims(rng, 8, 18); g = blank(h, w); c = rng.randint(0, 1); flags = []
    while c < w - 2:
        n = rng.randint(3, 6)
        s = _sym_shape(rng, n, ['lr']) if rng.random() < .5 else _asym_shape(rng, n, ['lr'])
        if s is None:
            return None
        sh, sw = _hw(s)
        if c + sw > w or sh > h - 3:
            break
        r0 = rng.randint(1, h - sh - 1); col = rng.choice(COLOURS)
        for r, x in s: g[r0 + r][c + x] = col
        flags.append(_is_sym(s, 'lr')); c += sw + rng.randint(1, 3)
    return g if len(flags) >= 2 and len(set(flags)) == 2 and len(objects(g, 0)) == len(flags) else None


def tf_rise_sink(g):
    h, w = dims(g); out = blank(h, w)
    for o in objects(g, 0):
        r0, _, r1, _ = bbox(o); v = _col(g, o); d = -r0 if _is_sym(o, 'lr') else h - 1 - r1
        for r, c in o: out[r + d][c] = v
    return out


rule("symmetric_objects_rise_asymmetric_sink", "Every left-right symmetric object slides straight up to the top edge; every asymmetric object slides straight down to the bottom edge.", gi_rise_sink, tf_rise_sink)


# ---- 39 two-row tally of symmetric vs asymmetric objects --------------------------------------------------------
def gi_tally(rng):
    return _mixed_scene(rng, ['lr'], _pal(rng, 2, 4, (0,)), need_both=False)


def tf_tally(g):
    obs = objects(g, 0); k = len(obs); ns = sum(_is_sym(o, 'lr') for o in obs)
    if k < 2:
        return None
    return [[1] * ns + [0] * (k - ns), [2] * (k - ns) + [0] * ns]


rule("tally_symmetric_vs_asymmetric_objects", "Output two rows as wide as the number of objects: the top row has one cell of colour 1 per left-right symmetric object, the bottom row one cell of colour 2 per asymmetric object, both packed left.", gi_tally, tf_tally)


# ---- 40 objects straddling a drawn axis recoloured by symmetry about it ------------------------------------------
def gi_straddle(rng):
    h, w = _dims(rng, 9, 19); w -= 1 - w % 2; ca = w // 2; g = blank(h, w); taken = set(); big = h >= 21

    def put(s, col, r0, c0):
        cells_ = {(r0 + r, c0 + c) for r, c in s}
        if any(not (0 <= r < h and 0 <= c < w) for r, c in cells_):
            return False
        foot = {(r + dr, c + dc) for r, c in cells_ for dr in (-1, 0, 1) for dc in (-1, 0, 1)}
        if foot & taken:
            return False
        taken.update(foot)
        for r, c in cells_: g[r][c] = col
        return True

    kinds = []
    for _ in range(rng.randint(4, 8) if big else rng.randint(2, 4)):
        n = rng.randint(4, 8); col = rng.choice(colours(rng, 3, (0, 1, 2, GREY))); t = rng.choice(['sym', 'asym', 'off'])
        if t == 'sym':
            s = _sym_shape(rng, n, ['lr'])
            if s is None or _hw(s)[1] % 2 == 0:
                continue
            c0 = ca - _hw(s)[1] // 2
        elif t == 'asym':
            s = _norm(random_shape(rng, n)); sw = _hw(s)[1]
            if sw < 2:
                continue
            c0 = rng.randint(ca - sw + 1, ca)
            if {(r, 2 * (ca - c0) - c) for r, c in s} == set(s):
                continue
        else:
            s = _norm(random_shape(rng, n)); sw = _hw(s)[1]
            if rng.random() < .5:
                if ca - 1 - sw < 0: continue
                c0 = rng.randint(0, ca - 1 - sw)
            else:
                if ca + 2 + sw > w: continue
                c0 = rng.randint(ca + 2, w - sw)
        sh = _hw(s)[0]
        if sh > h:
            continue
        for _ in range(30):
            if put(s, col, rng.randint(0, h - sh), c0):
                kinds.append(t); break
    if len(kinds) < 2 or len({k for k in kinds if k != 'off'}) < 2:
        return None
    for r in range(h):
        if g[r][ca] == 0: g[r][ca] = GREY
    return g


def tf_straddle(g):
    h, w = dims(g); ca = w // 2; out = copy(g); n = 0
    for o in objects(g, 0):
        if _col(g, o) == GREY:
            continue
        r0, c0, r1, c1 = bbox(o)
        if not (c0 <= ca <= c1):
            continue
        v = 1 if {(r, 2 * ca - c) for r, c in o} == set(o) else 2
        for r, c in o: out[r][c] = v
        n += 1
    return out if n else None


rule("straddling_objects_recoloured_by_axis_symmetry", "A grey line runs down the grid; objects lying across it become 1 if they are mirror-symmetric about that line and 2 if not, while objects wholly on one side keep their colour.", gi_straddle, tf_straddle)
