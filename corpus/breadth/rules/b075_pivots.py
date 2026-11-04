# b075_pivots.py -- TRANSFORMS ABOUT A MARKED PIVOT OR AXIS (not about the grid centre): a pivot cell of a fixed
# colour (grey 5 unless stated), or an axis defined by two marker cells, sits somewhere in the grid, and each object
# is rotated, reflected, scaled, orbited, copied or left alone relative to it. Rules differ in which objects move
# (nearest, farthest, by side, by size, by colour, by quadrant), what is kept, clipped, cancelled or erased.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

PIV = 5
OBJC = [1, 2, 3, 4, 6, 7, 8, 9]


# ---------------- point maps about a pivot p=(pr,pc) ----------------
def cw(r, c, p): return (p[0] + (c - p[1]), p[1] - (r - p[0]))
def ccw(r, c, p): return (p[0] - (c - p[1]), p[1] + (r - p[0]))
def r180(r, c, p): return (2 * p[0] - r, 2 * p[1] - c)
def mv(r, c, p): return (r, 2 * p[1] - c)          # reflect across the vertical line through p
def mh(r, c, p): return (2 * p[0] - r, c)          # reflect across the horizontal line through p
def md(r, c, p): return (p[0] + (c - p[1]), p[1] + (r - p[0]))   # across the main diagonal (top-left to bottom-right) through p
def ma(r, c, p): return (p[0] - (c - p[1]), p[1] - (r - p[0]))   # across the anti-diagonal through p
def turns(k):
    def f(r, c, p):
        for _ in range(k % 4): r, c = cw(r, c, p)
        return (r, c)
    return f


# ---------------- reading and applying ----------------
def parse(g, pivcols=(PIV,), ocols=None):
    pivs = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v in pivcols]
    objs = []
    for comp in objects(g, bg=0, conn8=True):
        col = g[comp[0][0]][comp[0][1]]
        if col in pivcols or (ocols is not None and col not in ocols): continue
        objs.append((col, sorted(comp)))
    return pivs, objs


def _one(g, pivcols=(PIV,), ocols=None):
    pivs, objs = parse(g, pivcols, ocols)
    return (pivs[0] if len(pivs) == 1 else None), objs


def _J(old, new, col): return dict(old=old, new=new, col=col)
def _app(fn, p, cells): return [fn(r, c, p) for r, c in cells]


def _res(g, jobs, keep=False, clip=False, erase=()):
    if jobs is None: return None
    out = copy(g); H, W = dims(g)
    if not keep:
        for j in jobs:
            for r, c in j['old']: out[r][c] = 0
    for r, c in erase: out[r][c] = 0
    for j in jobs:
        for r, c in j['new']:
            if 0 <= r < H and 0 <= c < W: out[r][c] = j['col']
            elif not clip: return None
    return out


def _valid(g, jobs, keep, clip):
    H, W = dims(g); allold = set()
    for j in jobs: allold |= set(j['old'])
    nz = {(r, c) for r in range(H) for c in range(W) if g[r][c]}
    occ = nz if keep else nz - allold
    seen = set(); changed = False
    for j in jobs:
        new = [(r, c) for r, c in j['new'] if 0 <= r < H and 0 <= c < W]
        if len(new) < len(j['new']) and not clip: return False
        ns = set(new)
        if ns & seen or ns & occ: return False
        if not keep and ns & (allold - set(j['old'])): return False
        seen |= ns
        if set(j['new']) != set(j['old']): changed = True
    return changed


def _gen(rng, build, plan, keep=False, clip=False):
    for _ in range(600):
        g = build(rng)
        if g is None: continue
        jobs = plan(g)
        if jobs and _valid(g, jobs, keep, clip): return g
    raise RuntimeError("gen")


# ---------------- scene builders ----------------
def _dims(rng, lo=8, hi=18, bigp=0.4):
    if rng.random() < bigp: return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _expand(cells):
    return {(r + a, c + b) for r, c in cells for a in (-1, 0, 1) for b in (-1, 0, 1)}


def _put(rng, blocked, n, win, tries=40):
    sh = random_shape(rng, n); sh_h = max(r for r, _ in sh) + 1; sh_w = max(c for _, c in sh) + 1
    r0, c0, r1, c1 = win
    if r1 - r0 + 1 < sh_h or c1 - c0 + 1 < sh_w: return None
    for _ in range(tries):
        a = rng.randint(r0, r1 - sh_h + 1); b = rng.randint(c0, c1 - sh_w + 1)
        cells = [(a + r, b + c) for r, c in sh]
        if not any(x in blocked for x in cells):
            blocked |= _expand(cells); return cells
    return None


def _stamp(g, cells, col):
    for r, c in cells: g[r][c] = col


def _pivot_mid(rng, h, w, cap=9):
    pr = rng.randint(h // 3, 2 * h // 3); pc = rng.randint(w // 3, 2 * w // 3)
    R = min(pr, pc, h - 1 - pr, w - 1 - pc, cap)
    return pr, pc, R


def _win(h, w, pr, pc, R): return (max(0, pr - R), max(0, pc - R), min(h - 1, pr + R), min(w - 1, pc + R))


def b_win(rng, k=(2, 4), n=(3, 6), objcols=OBJC, rad_div=1, pivcol=PIV, digit=None):
    h, w = _dims(rng); pr, pc, R = _pivot_mid(rng, h, w); R //= rad_div
    if R < 3: return None
    g = blank(h, w); g[pr][pc] = pivcol; blocked = _expand([(pr, pc)])
    if digit: g[pr][pc + 1] = digit; blocked |= _expand([(pr, pc + 1)])
    placed = 0
    for _ in range(rng.randint(*k)):
        cells = _put(rng, blocked, rng.randint(*n), _win(h, w, pr, pc, R))
        if cells: _stamp(g, cells, rng.choice(objcols)); placed += 1
    return g if placed >= 2 else None


def b_free(rng, k=(3, 5), n=(3, 5), objcols=OBJC, pivcol=PIV):
    h, w = _dims(rng); pr, pc = rng.randrange(h), rng.randrange(w)
    g = blank(h, w); g[pr][pc] = pivcol; blocked = _expand([(pr, pc)]); placed = 0
    for _ in range(rng.randint(*k)):
        cells = _put(rng, blocked, rng.randint(*n), (0, 0, h - 1, w - 1))
        if cells: _stamp(g, cells, rng.choice(objcols)); placed += 1
    return g if placed >= 2 else None


def b_sides(rng, vertical=False):
    h, w = _dims(rng); pr, pc, R = _pivot_mid(rng, h, w)
    if R < 4: return None
    g = blank(h, w); g[pr][pc] = PIV; blocked = _expand([(pr, pc)]); placed = 0
    for _ in range(rng.randint(3, 5)):
        side = rng.choice((0, 1))
        if vertical: win = (pr - R, pc - R, pr - 2, pc + R) if side else (pr + 2, pc - R, pr + R, pc + R)
        else: win = (pr - R, pc - R, pr + R, pc - 2) if side else (pr - R, pc + 2, pr + R, pc + R)
        cells = _put(rng, blocked, rng.randint(3, 5), win)
        if cells: _stamp(g, cells, rng.choice(OBJC)); placed += 1
    return g if placed >= 2 else None


def b_quad(rng):
    h, w = _dims(rng); pr, pc, R = _pivot_mid(rng, h, w)
    if R < 4: return None
    g = blank(h, w); g[pr][pc] = PIV; blocked = _expand([(pr, pc)]); placed = 0; quads = set()
    for _ in range(rng.randint(3, 5)):
        qa, qb = rng.choice((0, 1)), rng.choice((0, 1))
        win = ((pr - R, pr - 2) if qa else (pr + 2, pr + R), (pc - R, pc - 2) if qb else (pc + 2, pc + R))
        cells = _put(rng, blocked, rng.randint(3, 4), (win[0][0], win[1][0], win[0][1], win[1][1]))
        if cells: _stamp(g, cells, rng.choice(OBJC)); placed += 1; quads.add((qa, qb))
    return g if placed >= 3 and len(quads) >= 2 else None


def b_cat(rng, cols):
    h, w = _dims(rng); pr, pc, R = _pivot_mid(rng, h, w, 8)
    if R < 4: return None
    g = blank(h, w); g[pr][pc] = PIV; blocked = _expand([(pr, pc)]); placed = 0
    for col in rng.sample(cols, rng.randint(2, len(cols))):
        cells = _put(rng, blocked, rng.randint(3, 5), _win(h, w, pr, pc, R))
        if cells: _stamp(g, cells, col); placed += 1
    return g if placed >= 2 else None


def b_sizes(rng, nlo, nhi):
    h, w = _dims(rng); pr, pc, R = _pivot_mid(rng, h, w)
    if R < 4: return None
    g = blank(h, w); g[pr][pc] = PIV; blocked = _expand([(pr, pc)]); placed = 0
    sizes = rng.sample(range(nlo, nhi + 1), min(rng.randint(3, 5), nhi - nlo + 1))
    for n in sizes:
        cells = _put(rng, blocked, n, _win(h, w, pr, pc, R))
        if cells: _stamp(g, cells, rng.choice(OBJC)); placed += 1
    return g if placed >= 2 else None


def b_two(rng):
    h, w = _dims(rng, 10, 18)
    for _ in range(40):
        a = (rng.randrange(3, h - 3), rng.randrange(3, w - 3)); b = (rng.randrange(3, h - 3), rng.randrange(3, w - 3))
        if max(abs(a[0] - b[0]), abs(a[1] - b[1])) >= 7: break
    else: return None
    g = blank(h, w); blocked = set(); placed = 0
    for p in (a, b): g[p[0]][p[1]] = PIV; blocked |= _expand([p])
    for _ in range(rng.randint(3, 5)):
        p = rng.choice((a, b)); R = min(p[0], p[1], h - 1 - p[0], w - 1 - p[1], 5)
        cells = _put(rng, blocked, rng.randint(3, 5), _win(h, w, p[0], p[1], R))
        if cells: _stamp(g, cells, rng.choice(OBJC)); placed += 1
    return g if placed >= 3 else None


def b_inside(rng):
    h, w = _dims(rng); g = blank(h, w); blocked = set(); placed = 0
    for i in range(rng.randint(2, 4)):
        cells = _put(rng, blocked, rng.randint(4, 6), (0, 0, h - 1, w - 1))
        if not cells: continue
        col = rng.choice(OBJC); _stamp(g, cells, col)
        if i < rng.randint(1, 3) or i == 0:
            r, c = rng.choice(cells); g[r][c] = PIV
        placed += 1
    return g if placed >= 2 else None


def b_axis(rng, kind, touch=False):
    if kind == 'any': kind = rng.choice(('v', 'h', 'd'))
    if kind == 'h':
        g = b_axis(rng, 'v', touch)
        return transpose(g) if g else None
    h, w = _dims(rng, 9, 18); g = blank(h, w); blocked = set()
    if kind == 'v':
        c = rng.randint(w // 4, 3 * w // 4); r1 = rng.randint(0, h - 5); r2 = rng.randint(r1 + 3, h - 1)
        marks = [(r1, c), (r2, c)]; line = {(r, c) for r in range(h)}
    else:
        L = rng.randint(3, min(h, w) - 2); r1 = rng.randint(0, h - 1 - L); sgn = rng.choice((1, -1))
        c1 = rng.randint(0, w - 1 - L) if sgn == 1 else rng.randint(L, w - 1)
        marks = [(r1, c1), (r1 + L, c1 + sgn * L)]
        line = {(r1 + t, c1 + sgn * t) for t in range(-h, h)}
        line = {(r, c) for r, c in line if 0 <= r < h and 0 <= c < w}
    for m in marks: g[m[0]][m[1]] = PIV; blocked |= _expand([m])
    if not touch: blocked |= line
    placed = 0
    for _ in range(rng.randint(2, 4)):
        cells = _put(rng, blocked, rng.randint(3, 5), (0, 0, h - 1, w - 1))
        if cells: _stamp(g, cells, rng.choice(OBJC)); placed += 1
    return g if placed >= 2 else None


# ---------------- plans ----------------
def pl_all(fn, ocols=None, pivcols=(PIV,)):
    def plan(g):
        p, objs = _one(g, pivcols, ocols)
        if p is None or not objs: return None
        return [_J(cs, _app(fn, p, cs), col) for col, cs in objs]
    return plan


def mk_rule(name, desc, build, plan, keep=False, clip=False, erase_piv=False, digits=False, pivcols=(PIV,)):
    def gi(rng): return _gen(rng, build, plan, keep, clip)
    def tf(g):
        jobs = plan(g)
        er = parse(g, pivcols)[0] if erase_piv else ()
        return _res(g, jobs, keep, clip, er)
    rule(name, desc, gi, tf, digits=digits)


S = " A single grey (5) pivot cell and several single-colour objects (always at least one empty cell apart) sit in the grid; "
OLD = "each object's old cells become black."
W = lambda **kw: (lambda rng: b_win(rng, **kw))
F = lambda **kw: (lambda rng: b_free(rng, **kw))

# ================================================================== 1-7 per-object point maps about the pivot
mk_rule("pivot_rotate_quarter_turn_clockwise", "Each object is rotated a quarter turn clockwise about the grey (5) pivot cell and drawn there in its own colour; " + OLD, W(), pl_all(cw))
mk_rule("pivot_rotate_quarter_turn_anticlockwise", "Each object is rotated a quarter turn anticlockwise about the grey (5) pivot cell and drawn there in its own colour; " + OLD, W(), pl_all(ccw))
mk_rule("pivot_rotate_half_turn", "Each object is rotated half a turn (point reflection) about the grey (5) pivot cell; " + OLD, W(), pl_all(r180))
mk_rule("pivot_reflect_across_vertical_line", "Each object is reflected left-right across the vertical line through the grey (5) pivot cell (the pivot stays); " + OLD, W(), pl_all(mv))
mk_rule("pivot_reflect_across_horizontal_line", "Each object is reflected top-bottom across the horizontal line through the grey (5) pivot cell (the pivot stays); " + OLD, W(), pl_all(mh))
mk_rule("pivot_reflect_across_main_diagonal", "Each object is reflected across the diagonal running from top-left to bottom-right through the grey (5) pivot cell; " + OLD, W(), pl_all(md))
mk_rule("pivot_reflect_across_anti_diagonal", "Each object is reflected across the diagonal running from top-right to bottom-left through the grey (5) pivot cell; " + OLD, W(), pl_all(ma))

# ================================================================== 8-9 copies
mk_rule("pivot_vertical_reflection_copy_kept", "Every object keeps its place and gains a mirror copy in its own colour on the other side of the vertical line through the grey (5) pivot cell.", W(), pl_all(mv), keep=True)
def pl_pinwheel(g):
    p, objs = _one(g)
    if p is None or not objs: return None
    return [_J(cs, _app(cw, p, cs) + _app(r180, p, cs) + _app(ccw, p, cs), col) for col, cs in objs]
mk_rule("pivot_pinwheel_three_more_copies", "Every object stays and gets three copies in its own colour, rotated 90, 180 and 270 degrees clockwise about the grey (5) pivot cell.", W(k=(1, 2), n=(3, 5)), pl_pinwheel, keep=True)

# ================================================================== 10-11 nearest / farthest
def pl_pick(far, fn):
    def plan(g):
        p, objs = _one(g)
        if p is None or len(objs) < 2: return None
        d = lambda cs: (max if far else min)((r - p[0]) ** 2 + (c - p[1]) ** 2 for r, c in cs)
        i = min(range(len(objs)), key=lambda i: ((-d(objs[i][1]) if far else d(objs[i][1])), i))
        col, cs = objs[i]
        return [_J(cs, _app(fn, p, cs), col)]
    return plan
mk_rule("nearest_object_rotates_others_stay", "Only the object with a cell closest to the grey (5) pivot (squared Euclidean distance; ties go to the object whose topmost-then-leftmost cell comes first in reading order) is rotated a quarter turn clockwise about the pivot; the rest stay.", W(k=(3, 5)), pl_pick(False, cw))
mk_rule("farthest_object_reflects_others_stay", "Only the object with a cell farthest from the grey (5) pivot (squared Euclidean distance; ties go to the object whose topmost-then-leftmost cell comes first in reading order) is reflected across the vertical line through the pivot; the rest stay.", W(k=(3, 5)), pl_pick(True, mv))

# ================================================================== 12 scale
def pl_scale(g):
    p, objs = _one(g)
    if p is None or not objs: return None
    jobs = []
    for col, cs in objs:
        new = [(p[0] + 2 * (r - p[0]) + x, p[1] + 2 * (c - p[1]) + y) for r, c in cs for x in (0, 1) for y in (0, 1)]
        jobs.append(_J(cs, new, col))
    return jobs
mk_rule("scale_double_about_pivot", "Each object is enlarged to twice its size about the grey (5) pivot: a cell at offset (dr,dc) from the pivot becomes the 2x2 block whose top-left cell is at offset (2dr,2dc); " + OLD, W(k=(1, 3), n=(3, 5), rad_div=2), pl_scale)

# ================================================================== 13 digit beside pivot
def pl_digit(g):
    pivs, objs = parse(g, ocols=(4, 6, 7, 8, 9))
    if len(pivs) != 1: return None
    p = pivs[0]; d = g[p[0]][p[1] + 1] if p[1] + 1 < len(g[0]) else 0
    if d not in (1, 2, 3): return None
    return [_J(cs, _app(turns(d), p, cs), col) for col, cs in objs]
mk_rule("digit_beside_pivot_sets_clockwise_turns", "The cell right of the grey (5) pivot holds a digit d (1, 2 or 3); every object (colours 4, 6, 7, 8 or 9) is rotated d quarter turns clockwise about the pivot, and the pivot and digit stay; " + OLD,
        lambda rng: b_win(rng, objcols=[4, 6, 7, 8, 9], digit=rng.choice((1, 2, 3))), pl_digit, digits=True)

# ================================================================== 14-15 sides
def pl_sides(vertical):
    def plan(g):
        p, objs = _one(g)
        if p is None or not objs: return None
        jobs = []
        for col, cs in objs:
            a = [r if vertical else c for r, c in cs]; ref = p[0] if vertical else p[1]
            if all(x < ref for x in a): fn = cw if vertical else mv
            elif all(x > ref for x in a): fn = mh if vertical else cw
            else: return None
            jobs.append(_J(cs, _app(fn, p, cs), col))
        return jobs
    return plan
mk_rule("left_objects_reflect_right_objects_rotate", "Objects entirely left of the grey (5) pivot's column are reflected across the vertical line through the pivot; objects entirely right of it are rotated a quarter turn clockwise about the pivot; " + OLD, lambda rng: b_sides(rng), pl_sides(False))
mk_rule("above_objects_rotate_below_objects_flip", "Objects entirely above the grey (5) pivot's row are rotated a quarter turn clockwise about the pivot; objects entirely below it are reflected across the horizontal line through the pivot; " + OLD, lambda rng: b_sides(rng, True), pl_sides(True))

# ================================================================== 16-17, 33 colour selects
def pl_pcol(g):
    p, objs = _one(g, (1, 2, 3))
    if p is None or not objs: return None
    fn = {1: cw, 2: mv, 3: mh}[g[p[0]][p[1]]]
    return [_J(cs, _app(fn, p, cs), col) for col, cs in objs]
mk_rule("pivot_colour_selects_transform", "The pivot cell is blue (1), red (2) or green (3): blue rotates every object a quarter turn clockwise about the pivot, red reflects every object across the vertical line through it, green reflects across the horizontal line through it; " + OLD,
        lambda rng: b_win(rng, objcols=[4, 5, 6, 7, 8, 9], pivcol=rng.choice((1, 2, 3))), pl_pcol, digits=True)
def pl_ocol(g):
    p, objs = _one(g)
    if p is None or not objs: return None
    jobs = []
    for col, cs in objs:
        fn = {1: cw, 2: mv, 3: mh}.get(col)
        if fn: jobs.append(_J(cs, _app(fn, p, cs), col))
    return jobs
mk_rule("object_colour_selects_transform", "About the grey (5) pivot, a blue (1) object rotates a quarter turn clockwise, a red (2) object reflects across the vertical line through the pivot, a green (3) object reflects across the horizontal line through the pivot, and a yellow (4) object stays; " + OLD, lambda rng: b_cat(rng, [1, 2, 3, 4]), pl_ocol, digits=True)
def pl_ocoldigit(g):
    p, objs = _one(g)
    if p is None or not objs: return None
    return [_J(cs, _app(turns(col), p, cs), col) for col, cs in objs if col in (1, 2, 3)]
mk_rule("object_colour_value_sets_clockwise_turns", "An object of colour 1, 2 or 3 is rotated that many quarter turns clockwise about the grey (5) pivot; " + OLD, lambda rng: b_cat(rng, [1, 2, 3]), pl_ocoldigit, digits=True)

# ================================================================== 18 two pivots
def pl_two(g):
    pivs, objs = parse(g)
    if len(pivs) != 2 or not objs: return None
    jobs = []
    for col, cs in objs:
        d = [min(abs(r - p[0]) + abs(c - p[1]) for r, c in cs) for p in pivs]
        p = pivs[0] if d[0] <= d[1] else pivs[1]
        jobs.append(_J(cs, _app(cw, p, cs), col))
    return jobs
mk_rule("two_pivots_nearer_one_rotates", "Two grey (5) pivot cells are present; each object is rotated a quarter turn clockwise about the pivot nearer to it (Manhattan distance from the pivot to the object's closest cell; a tie goes to the pivot first in reading order); " + OLD, b_two, pl_two)

# ================================================================== 19 pivot inside object
def pl_inside(g):
    pivs, objs = parse(g)
    if not pivs: return None
    jobs = []; used = set()
    for p in pivs:
        near = [(col, cs) for col, cs in objs if any(max(abs(r - p[0]), abs(c - p[1])) <= 1 for r, c in cs)]
        if not near: return None
        cells_ = [x for _, cs in near for x in cs]
        if used & set(cells_): return None
        used |= set(cells_)
        jobs.append(_J(cells_, _app(cw, p, cells_), near[0][0]))
    return jobs
mk_rule("pivot_inside_object_rotates_only_it", "Some objects have one of their cells coloured grey (5), the pivot of that object; each such object (its coloured cells) is rotated a quarter turn clockwise about its own pivot cell, which stays, and objects without a grey cell stay; " + OLD, b_inside, pl_inside)

# ================================================================== 20 pivot erased
mk_rule("pivot_erased_after_rotation", "Each object is rotated a quarter turn clockwise about the grey (5) pivot cell, and the pivot cell itself is then erased to black; " + OLD, F(k=(2, 4)), pl_all(cw), erase_piv=True)

# ================================================================== 21-25, 38 axis through two markers
def pl_axis(kinds, skip_touch=False):
    def plan(g):
        pivs, objs = parse(g)
        if len(pivs) != 2 or not objs: return None
        p, q = pivs; dr, dc = q[0] - p[0], q[1] - p[1]
        if dc == 0 and 'v' in kinds: fn = mv
        elif dr == 0 and 'h' in kinds: fn = mh
        elif abs(dr) == abs(dc) and 'd' in kinds and dr: fn = md if dr == dc else ma
        else: return None
        jobs = []
        for col, cs in objs:
            if skip_touch and any(fn(r, c, p) == (r, c) for r, c in cs): continue
            jobs.append(_J(cs, _app(fn, p, cs), col))
        return jobs
    return plan
AX = "Two grey (5) marker cells lie in the same column, and objects sit on either side of that column (never touching it); "
mk_rule("axis_markers_vertical_reflect", "Two grey (5) marker cells share a column and define the vertical axis line through that column (extended over the whole grid); each object is reflected across it, the markers stay; " + OLD, lambda rng: b_axis(rng, 'v'), pl_axis('v'))
mk_rule("axis_markers_horizontal_reflect", "Two grey (5) marker cells share a row and define the horizontal axis line through that row (extended over the whole grid); each object is reflected across it, the markers stay; " + OLD, lambda rng: b_axis(rng, 'h'), pl_axis('h'))
mk_rule("axis_markers_diagonal_reflect", "Two grey (5) marker cells lie on a common diagonal (equal row and column distance) and define the diagonal axis line through them, extended over the whole grid; each object is reflected across it and the markers stay; " + OLD, lambda rng: b_axis(rng, 'd'), pl_axis('d'))
mk_rule("axis_markers_any_direction_reflect", "Two grey (5) marker cells share a row, a column or a diagonal and define the axis line through them, extended over the whole grid; each object is reflected across it, the markers stay; " + OLD, lambda rng: b_axis(rng, 'any'), pl_axis('vhd'))
mk_rule("axis_markers_vertical_reflection_copy", "Two grey (5) marker cells share a column and define a vertical axis; every object keeps its place and gains a mirror copy in its own colour on the other side of the axis.", lambda rng: b_axis(rng, 'v'), pl_axis('v'), keep=True)
mk_rule("axis_touching_objects_stay_others_reflect", "Two grey (5) marker cells share a column and define a vertical axis; objects that have a cell on the axis column stay, every other object is reflected across the axis; " + OLD, lambda rng: b_axis(rng, 'v', True), pl_axis('v', True))

# ================================================================== 26-29 free placement, boundary and orbit rules
def pl_cancel(g):
    p, objs = _one(g)
    if p is None or not objs: return None
    H, W2 = dims(g); jobs = []
    for col, cs in objs:
        new = _app(mv, p, cs)
        if all(0 <= r < H and 0 <= c < W2 for r, c in new): jobs.append(_J(cs, new, col))
    return jobs
mk_rule("reflection_cancelled_if_it_leaves_grid", "Each object is reflected across the vertical line through the grey (5) pivot cell, but an object whose reflection would extend past the grid edge is cancelled and stays where it is; " + OLD, F(k=(3, 5)), pl_cancel)
mk_rule("rotation_clipped_at_grid_edge", "Each object is rotated a quarter turn clockwise about the grey (5) pivot cell; cells that would land outside the grid are clipped away; " + OLD, F(k=(2, 4)), pl_all(cw), clip=True)
def pl_orbit(fn):
    def plan(g):
        p, objs = _one(g)
        if p is None or not objs: return None
        jobs = []
        for col, cs in objs:
            r0, c0 = cs[0]; nr, nc = fn(r0, c0, p); dr, dc = nr - r0, nc - c0
            jobs.append(_J(cs, [(r + dr, c + dc) for r, c in cs], col))
        return jobs
    return plan
mk_rule("orbit_quarter_turn_keeping_orientation", "Each object orbits the grey (5) pivot without turning: it is shifted so that its topmost-then-leftmost cell moves a quarter turn clockwise around the pivot; " + OLD, F(k=(2, 4), n=(3, 5)), pl_orbit(cw))
mk_rule("orbit_half_turn_keeping_orientation", "Each object orbits the grey (5) pivot without turning: it is shifted so that its topmost-then-leftmost cell moves half a turn around the pivot; " + OLD, F(k=(2, 4), n=(3, 5)), pl_orbit(r180))

# ================================================================== 30-32 size selects
def pl_size(g):
    p, objs = _one(g)
    if p is None or not objs: return None
    return [_J(cs, _app(cw if len(cs) >= 5 else mv, p, cs), col) for col, cs in objs]
mk_rule("size_selects_rotate_or_reflect", "An object of 5 or more cells is rotated a quarter turn clockwise about the grey (5) pivot; an object of 4 or fewer cells is reflected across the vertical line through the pivot; " + OLD, lambda rng: b_sizes(rng, 2, 7), pl_size)
def pl_largest(g):
    p, objs = _one(g)
    if p is None or len(objs) < 2: return None
    big = min(range(len(objs)), key=lambda i: (-len(objs[i][1]), i))
    return [_J(cs, _app(cw if i == big else mv, p, cs), col) for i, (col, cs) in enumerate(objs)]
mk_rule("largest_rotates_others_reflect", "The object with the most cells (ties go to the one whose topmost-then-leftmost cell comes first in reading order) is rotated a quarter turn clockwise about the grey (5) pivot; every other object is reflected across the vertical line through the pivot; " + OLD, lambda rng: b_sizes(rng, 2, 7), pl_largest)
def pl_mod4(g):
    p, objs = _one(g)
    if p is None or not objs: return None
    return [_J(cs, _app(turns(len(cs)), p, cs), col) for col, cs in objs]
mk_rule("turns_equal_cell_count_mod_four", "An object with n cells (3 to 7) is rotated n mod 4 quarter turns clockwise about the grey (5) pivot (so 4 cells means no turn); " + OLD, lambda rng: b_sizes(rng, 3, 7), pl_mod4)

# ================================================================== 34-35 recoloured copies
def pl_copy8(g):
    p, objs = _one(g)
    if p is None or not objs: return None
    return [_J(cs, _app(r180, p, cs), 8) for col, cs in objs]
mk_rule("half_turn_copy_recoloured_cyan", "Every object stays and gains a half-turn copy about the grey (5) pivot cell, drawn in cyan (8).", F(k=(2, 4), objcols=[1, 2, 3, 4, 6, 7, 9]), pl_copy8, keep=True)
def _single_pivots(g):
    return [comp[0] for comp in objects(g, bg=0, conn8=True) if len(comp) == 1]
def pl_pcopy(g):
    pivs = _single_pivots(g)
    objs = [(g[c[0][0]][c[0][1]], sorted(c)) for c in objects(g, bg=0, conn8=True) if len(c) > 1]
    if len(pivs) != 1 or not objs: return None
    p = pivs[0]; pc_ = g[p[0]][p[1]]
    return [_J(cs, _app(mv, p, cs), pc_) for col, cs in objs]
def b_pcopy(rng):
    pc_ = rng.choice(OBJC)
    return b_win(rng, k=(2, 4), n=(3, 5), objcols=[c for c in OBJC if c != pc_], pivcol=pc_)
mk_rule("reflection_copy_takes_pivot_colour", "A single-cell pivot (any colour) and several larger objects are present; every object stays and gains a mirror copy across the vertical line through the pivot, drawn in the pivot's colour.", b_pcopy, pl_pcopy, keep=True)

# ================================================================== 36-37 quadrants
def _quad(cs, p):
    rs = {r < p[0] for r, c in cs if r != p[0]}; cc = {c < p[1] for r, c in cs if c != p[1]}
    if len(rs) != 1 or len(cc) != 1 or any(r == p[0] or c == p[1] for r, c in cs): return None
    return (rs.pop(), cc.pop())   # (above?, left?)
def pl_fold(g):
    p, objs = _one(g)
    if p is None or not objs: return None
    jobs = []
    for col, cs in objs:
        q = _quad(cs, p)
        if q is None: return None
        fn = {(True, True): None, (True, False): mv, (False, True): mh, (False, False): r180}[q]
        jobs.append(_J(cs, cs if fn is None else _app(fn, p, cs), col))
    return jobs
mk_rule("fold_objects_into_top_left_quadrant", "Each object lies in one quadrant around the grey (5) pivot; objects are reflected across the pivot's vertical and/or horizontal line as needed (a half turn for bottom-right ones) so that all end up in the top-left quadrant; " + OLD, b_quad, pl_fold)
def pl_into_tr(g):
    p, objs = _one(g)
    if p is None or not objs: return None
    jobs = []
    for col, cs in objs:
        q = _quad(cs, p)
        if q is None: return None
        k = {(True, True): 1, (True, False): 0, (False, True): 2, (False, False): 3}[q]
        jobs.append(_J(cs, _app(turns(k), p, cs), col))
    return jobs
mk_rule("rotate_objects_into_top_right_quadrant", "Each object lies in one quadrant around the grey (5) pivot; each is rotated clockwise about the pivot by whole quarter turns (the fewest needed, 0 to 3) until it lies in the top-right quadrant; " + OLD, b_quad, pl_into_tr)

# ================================================================== 39 distance band
def pl_band(g):
    p, objs = _one(g)
    if p is None or not objs: return None
    jobs = []
    for col, cs in objs:
        d = min(max(abs(r - p[0]), abs(c - p[1])) for r, c in cs)
        jobs.append(_J(cs, _app(cw if d <= 3 else r180, p, cs), col))
    return jobs
mk_rule("distance_band_selects_quarter_or_half_turn", "An object whose closest cell is within 3 cells of the grey (5) pivot (Chebyshev distance 3 or less) is rotated a quarter turn clockwise about it; a farther object is rotated a half turn about it; " + OLD, F(k=(3, 5), n=(3, 5)), pl_band)
