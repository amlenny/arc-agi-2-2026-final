# b084_pipelines2.py -- THREE-STEP PIPELINES, SECOND SET: every rule chains three simple operations stated in order in its
# sentence. Steps come from one small library (each step is a pure grid function with a fixed phrase), a triple is accepted
# for an input only if every step changes the grid and no later grid equals an earlier one (so no step undoes another),
# and the rule list is checked so that no two rules agree in two of their three step positions.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

OC = [1, 2, 3, 4, 6, 7, 8, 9]


class St:
    def __init__(s, fam, fn, text): s.fam, s.fn, s.text = fam, fn, text


def _ok(g): return bool(g) and bool(g[0]) and 1 <= len(g) <= 30 and 1 <= len(g[0]) <= 30


def _ob(g):
    out = []
    for comp in objects(g, bg=0, conn8=False):
        r0, c0, r1, c1 = bbox(comp)
        out.append(dict(cells=comp, col=g[comp[0][0]][comp[0][1]], r0=r0, c0=c0, r1=r1, c1=c1, n=len(comp)))
    return sorted(out, key=lambda o: (o['r0'], o['c0']))


def _cut(g, o):
    out = blank(o['r1'] - o['r0'] + 1, o['c1'] - o['c0'] + 1)
    for r, c in o['cells']: out[r - o['r0']][c - o['c0']] = o['col']
    return out


def _pick(os_, key, big=True):
    if not os_: return None
    ks = [key(o) for o in os_]; b = max(ks) if big else min(ks)
    if ks.count(b) > 1: return None
    return os_[ks.index(b)]


def _paint(g, cells_, col):
    out = copy(g)
    for r, c in cells_: out[r][c] = col
    return out


# ------------------------------------------------------------------ steps
def rot_cw(): return St('rot_cw', rot90, "turn the picture a quarter turn clockwise")
def rot_ccw(): return St('rot_ccw', lambda g: rot90(rot90(rot90(g))), "turn the picture a quarter turn anticlockwise")
def rot_180(): return St('rot_180', lambda g: rot90(rot90(g)), "turn the picture upside down")
def flip_h(): return St('flip_h', flip_h_, "mirror the picture left to right")
def flip_v(): return St('flip_v', flip_v_, "mirror the picture top to bottom")
def flip_h_(g): return [r[::-1] for r in g]
def flip_v_(g): return g[::-1]
def transpose_(): return St('transpose', transpose, "transpose the picture (rows become columns)")

def crop_all(): return St('crop_all', lambda g: (lambda cs: crop(g, *bbox(cs)) if cs else None)(cells(g, lambda v: v)), "cut the picture to the bounding box of all coloured cells")
def crop_largest(): return St('crop_largest', lambda g: (lambda o: _cut(g, o) if o else None)(_pick(_ob(g), lambda o: o['n'])), "cut out the largest object (most cells; rejected if two tie)")
def crop_smallest(): return St('crop_smallest', lambda g: (lambda o: _cut(g, o) if o else None)(_pick(_ob(g), lambda o: o['n'], False)), "cut out the smallest object (fewest cells; rejected if two tie)")

def scale2(): return St('scale2', lambda g: [[v for v in r for _ in (0, 1)] for r in g for _ in (0, 1)], "enlarge it two times (every cell becomes a 2 by 2 block)")
def shrink2():
    def f(g):
        if len(g) % 2 or len(g[0]) % 2: return None
        return [[g[r][c] for c in range(0, len(g[0]), 2)] for r in range(0, len(g), 2)]
    return St('shrink2', f, "shrink the grid by half, keeping the top-left cell of every 2 by 2 block (the sides are even)")
def tile_v(): return St('tile_v', lambda g: g + g, "stack two copies one above the other")
def tile_h(): return St('tile_h', lambda g: [r + r for r in g], "place two copies side by side")
def tile_22(): return St('tile_22', lambda g: [r + r for r in g] * 2, "tile it two by two")
def mirror_right(): return St('mirror_right', lambda g: [r + r[::-1] for r in g], "append its left-right mirror image on the right")
def mirror_below(): return St('mirror_below', lambda g: g + g[::-1], "append its top-bottom mirror image underneath")
def del_first_row(): return St('del_first_row', lambda g: g[1:] or None, "delete the first row")
def del_last_row(): return St('del_last_row', lambda g: g[:-1] or None, "delete the last row")
def del_first_col(): return St('del_first_col', lambda g: [r[1:] for r in g] if len(g[0]) > 1 else None, "delete the first column")
def del_last_col(): return St('del_last_col', lambda g: [r[:-1] for r in g] if len(g[0]) > 1 else None, "delete the last column")
def add_border(c): return St('add_border', lambda g: [[c] * (len(g[0]) + 2)] + [[c] + r + [c] for r in g] + [[c] * (len(g[0]) + 2)], f"add a one-cell border of colour {c} around the whole picture")
def ring_recolour(c):
    def f(g):
        H, W = dims(g); return [[c if r in (0, H - 1) or k in (0, W - 1) else g[r][k] for k in range(W)] for r in range(H)]
    return St('ring_recolour', f, f"repaint every cell of the outermost ring of the grid (the first and last row and column) colour {c}")
def baseline(c): return St('baseline', lambda g: g + [[c] * len(g[0])], f"add a full-width row of colour {c} underneath")

def swap12(): return St('swap12', lambda g: [[2 if v == 1 else 1 if v == 2 else v for v in r] for r in g], "swap colours 1 and 2")
def recol_all(c): return St('recol_all', lambda g: [[c if v else 0 for v in r] for r in g], f"repaint every coloured cell colour {c}")
def checker(c): return St('checker', lambda g: [[c if v and (r + k) % 2 else v for k, v in enumerate(row)] for r, row in enumerate(g)], f"repaint colour {c} every coloured cell whose row index plus column index is odd (counting from 0)")
def _recol_obj(key, big, c, fam, text):
    def f(g):
        o = _pick(_ob(g), key, big)
        return _paint(g, o['cells'], c) if o else None
    return St(fam, f, text)
def recol_largest(c): return _recol_obj(lambda o: o['n'], True, c, 'recol_largest', f"repaint the largest object colour {c} (rejected on a tie)")
def recol_smallest(c): return _recol_obj(lambda o: o['n'], False, c, 'recol_smallest', f"repaint the smallest object colour {c} (rejected on a tie)")
def recol_lowest(c): return _recol_obj(lambda o: (o['r1'], -o['c0']), True, c, 'recol_lowest', f"repaint colour {c} the object whose bottom row is lowest in the grid (the leftmost wins a tie)")
def recol_leftmost(c): return _recol_obj(lambda o: (-o['c0'], -o['r0']), True, c, 'recol_leftmost', f"repaint colour {c} the object that starts furthest left (the topmost wins a tie)")
def recol_by_size_digit():
    def f(g):
        out = copy(g)
        for o in _ob(g):
            if o['n'] > 9: return None
            for r, c in o['cells']: out[r][c] = o['n']
        return out
    return St('recol_by_size', f, "repaint every object with the colour value equal to its number of cells (every object has at most 9)")

def denoise():
    def f(g):
        H, W = dims(g); out = copy(g)
        for r, c in cells(g, lambda v: v):
            if not any(0 <= r + a < H and 0 <= c + b < W and g[r + a][c + b] for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)): out[r][c] = 0
        return out
    return St('denoise', f, "erase every coloured cell with no coloured cell among its 8 neighbours")
def del_largest(): return St('del_largest', lambda g: (lambda o: _paint(g, o['cells'], 0) if o else None)(_pick(_ob(g), lambda o: o['n'])), "delete the largest object (rejected on a tie)")
def del_smallest(): return St('del_smallest', lambda g: (lambda o: _paint(g, o['cells'], 0) if o else None)(_pick(_ob(g), lambda o: o['n'], False)), "delete the smallest object (rejected on a tie)")
def del_border():
    def f(g):
        H, W = dims(g); out = copy(g)
        for o in _ob(g):
            if any(r in (0, H - 1) or c in (0, W - 1) for r, c in o['cells']):
                for r, c in o['cells']: out[r][c] = 0
        return out
    return St('del_border', f, "delete every object that touches the grid edge")

def _holes(g):
    comps = components(g, 0, conn8=False); H, W = dims(g)
    return [cp for cp in comps if not any(r in (0, H - 1) or c in (0, W - 1) for r, c in cp)]
def fill_holes(c):
    def f(g):
        out = copy(g)
        for cp in _holes(g):
            for r, k in cp: out[r][k] = c
        return out
    return St('fill_holes', f, f"fill every enclosed empty region (one that cannot reach the grid edge through empty cells) with colour {c}")
def keep_holed():
    def f(g):
        os_ = _ob(g); idx = {}
        for i, o in enumerate(os_):
            for cell in o['cells']: idx[cell] = i
        H, W = dims(g); keep = set()
        for cp in _holes(g):
            nb = {idx[(r + a, k + b)] for r, k in cp for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (r + a, k + b) in idx}
            if len(nb) == 1: keep |= nb
        if not keep: return None
        out = copy(g)
        for i, o in enumerate(os_):
            if i not in keep:
                for r, c in o['cells']: out[r][c] = 0
        return out
    return St('keep_holed', f, "keep only the objects that enclose at least one empty hole and erase the others")
def _colcount(g):
    d = {}
    for r in g:
        for v in r:
            if v: d[v] = d.get(v, 0) + 1
    return d
def keep_rarest():
    def f(g):
        d = _colcount(g)
        if len(d) < 2: return None
        m = min(d.values())
        if list(d.values()).count(m) > 1: return None
        k = next(c for c, n in d.items() if n == m); return [[v if v == k else 0 for v in r] for r in g]
    return St('keep_rarest', f, "keep only the colour with the fewest cells (rejected on a tie) and erase every other colour")
def keep_commonest():
    def f(g):
        d = _colcount(g)
        if len(d) < 2: return None
        m = max(d.values())
        if list(d.values()).count(m) > 1: return None
        k = next(c for c, n in d.items() if n == m); return [[v if v == k else 0 for v in r] for r in g]
    return St('keep_commonest', f, "keep only the colour with the most cells (rejected on a tie) and erase every other colour")
def outline():
    def f(g):
        H, W = dims(g)
        return [[v if v and any(not (0 <= r + a < H and 0 <= c + b < W) or g[r + a][c + b] == 0 for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))) else 0 for c, v in enumerate(row)] for r, row in enumerate(g)]
    return St('outline', f, "keep only the cells that touch an empty cell or the grid edge on one of their four sides")
def bbox_fill():
    def f(g):
        os_ = _ob(g); out = blank(*dims(g))
        for o in os_:
            for r in range(o['r0'], o['r1'] + 1):
                for c in range(o['c0'], o['c1'] + 1):
                    if g[r][c] and (r, c) not in set(o['cells']): return None
                    out[r][c] = o['col']
        return out
    return St('bbox_fill', f, "replace each object by the solid rectangle of its bounding box in its colour (rejected if a box would cover another object)")
def frame_each(c):
    def f(g):
        H, W = dims(g); out = copy(g)
        for o in _ob(g):
            for r in range(o['r0'] - 1, o['r1'] + 2):
                for k in range(o['c0'] - 1, o['c1'] + 2):
                    if r in (o['r0'] - 1, o['r1'] + 1) or k in (o['c0'] - 1, o['c1'] + 1):
                        if not (0 <= r < H and 0 <= k < W) or g[r][k]: return None
                        out[r][k] = c
        return out
    return St('frame_each', f, f"draw a one-cell frame of colour {c} just outside each object's bounding box (rejected if it leaves the grid or meets a coloured cell)")

def _slide(g, d):
    H, W = dims(g); out = blank(H, W)
    if d in 'ud':
        for c in range(W):
            col = [g[r][c] for r in range(H) if g[r][c]]
            for i, v in enumerate(col): out[(H - len(col) + i) if d == 'd' else i][c] = v
    else:
        for r in range(H):
            row = [v for v in g[r] if v]
            for i, v in enumerate(row): out[r][(W - len(row) + i) if d == 'r' else i] = v
    return out
def fall_down(): return St('fall_down', lambda g: _slide(g, 'd'), "let every cell fall straight down until it meets the floor or another cell")
def rise_up(): return St('rise_up', lambda g: _slide(g, 'u'), "let every cell rise straight up until it meets the ceiling or another cell")
def slide_left(): return St('slide_left', lambda g: _slide(g, 'l'), "slide every row's cells left against the wall, keeping their order")
def slide_right(): return St('slide_right', lambda g: _slide(g, 'r'), "slide every row's cells right against the wall, keeping their order")

def sort_left_by_size():
    def f(g):
        os_ = _ob(g)
        if len(os_) < 2: return None
        os_ = sorted(os_, key=lambda o: (o['n'], o['r0'], o['c0'])); H = max(o['r1'] - o['r0'] + 1 for o in os_)
        W = sum(o['c1'] - o['c0'] + 1 for o in os_) + len(os_) - 1
        if W > 30: return None
        out = blank(H, W); x = 0
        for o in os_:
            cg = _cut(g, o); h = len(cg)
            paste(out, cg, H - h, x, transparent=0); x += len(cg[0]) + 1
        return out
    return St('sort_left_by_size', f, "cut out all objects and lay them in one row, bottom-aligned with one empty column between, from fewest cells on the left to most (equal sizes in reading order of their top-left cells)")
def equalise_height():
    def f(g):
        os_ = _ob(g); H = max(o['r1'] - o['r0'] + 1 for o in os_) if os_ else 0; out = copy(g)
        for o in os_:
            h = o['r1'] - o['r0'] + 1
            for k in range(1, H - h + 1):
                for r, c in o['cells']:
                    if r == o['r0']:
                        if r - k < 0 or out[r - k][c]: return None
                        out[r - k][c] = o['col']
        return out
    return St('equalise_height', f, "extend every object upward by repeating its top row until it is as tall as the tallest object (rejected if that leaves the grid)")
def stack_column():
    def f(g):
        os_ = _ob(g)
        if len(os_) < 2: return None
        W = max(o['c1'] - o['c0'] + 1 for o in os_); H = sum(o['r1'] - o['r0'] + 1 for o in os_) + len(os_) - 1
        if H > 30: return None
        out = blank(H, W); y = 0
        for o in os_:
            cg = _cut(g, o); paste(out, cg, y, 0, transparent=0); y += len(cg) + 1
        return out
    return St('stack_column', f, "cut out the objects and stack them in one column, left-aligned with one empty row between, in reading order of their top-left cells")
def objs_to_bars():
    def f(g):
        os_ = sorted(_ob(g), key=lambda o: (o['c0'], o['r0']))
        if len(os_) < 2: return None
        H = max(o['n'] for o in os_); W = len(os_)
        if H > 30: return None
        out = blank(H, W)
        for i, o in enumerate(os_):
            for k in range(o['n']): out[H - 1 - k][i] = o['col']
        return out
    return St('objs_to_bars', f, "turn each object into a vertical bar of its colour as tall as its cell count, bottom-aligned, the bars side by side without gaps in order of the objects' leftmost columns (higher object first on a tie)")
def _bars(g):
    return [(sum(1 for r in range(len(g)) if g[r][c]), [g[r][c] for r in range(len(g)) if g[r][c]][:1]) for c in range(len(g[0]))]
def sort_bars():
    def f(g):
        H, W = dims(g); cols_ = sorted(range(W), key=lambda c: (sum(1 for r in range(H) if g[r][c]), c))
        return [[g[r][c] for c in cols_] for r in range(H)]
    return St('sort_bars', f, "reorder the bar columns from shortest on the left to tallest on the right (equal heights keep their order)")
def mark_median(c):
    def f(g):
        H, W = dims(g)
        if W % 2 == 0: return None
        out = copy(g)
        for r in range(H):
            if g[r][W // 2]: out[r][W // 2] = c
        return out
    return St('mark_median', f, f"repaint the middle bar colour {c} (rejected if the number of bars is even)")
def bar_filled(c):
    def f(g):
        n = len(components(g, c, conn8=False)); return [[c] * n + [0] * (10 - n)] if 1 <= n <= 9 else None
    return St('bar_filled', f, f"replace the picture by a one-row bar of width 10 in colour {c} as long as the number of separate regions of colour {c} (1 to 9)")
def bar_objects(c):
    def f(g):
        n = len(_ob(g)); return [[c] * n + [0] * (10 - n)] if 1 <= n <= 9 else None
    return St('bar_objects', f, f"replace the picture by a one-row bar of width 10 in colour {c} as long as the number of objects (1 to 9)")

def _panels(g):
    W = len(g[0]); seps = [c for c in range(W) if all(r[c] == 5 for r in g)]
    if len(seps) != 1: return None
    s = seps[0]; a = [r[:s] for r in g]; b = [r[s + 1:] for r in g]
    return (a, b) if len(a[0]) == len(b[0]) else None
def panels_and():
    def f(g):
        p = _panels(g)
        if not p: return None
        a, b = p; return [[a[r][c] if a[r][c] and b[r][c] else 0 for c in range(len(a[0]))] for r in range(len(a))]
    return St('panels_and', f, "split at the grey 5 column and keep only the cells coloured in both halves, in the left half's colour")
def panels_xor():
    def f(g):
        p = _panels(g)
        if not p: return None
        a, b = p; return [[(a[r][c] or b[r][c]) if bool(a[r][c]) != bool(b[r][c]) else 0 for c in range(len(a[0]))] for r in range(len(a))]
    return St('panels_xor', f, "split at the grey 5 column and keep only the cells coloured in exactly one half, in that half's colour")
def panels_stack():
    def f(g):
        p = _panels(g)
        if not p: return None
        return p[0] + p[1]
    return St('panels_stack', f, "split at the grey 5 column and stack the left half above the right half")


# ------------------------------------------------------------------ scenes
def _hw(rng, lo=8, hi=18, p=0.4):
    if rng.random() < p: return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)
def obj_scene(k=(2, 5), n=(3, 8), cols=OC, distinct=True, odd=False, size=(8, 18), noise=0):
    def sc(rng):
        h, w = _hw(rng, *size); g = blank(h, w); kk = rng.randint(*k) + (2 if h * w > 400 else 0)
        if odd and kk % 2 == 0: kk += 1
        shapes = [random_shape(rng, rng.randint(*n)) for _ in range(kk)]
        cs = rng.sample(cols, min(kk, len(cols))) if distinct else [rng.choice(cols) for _ in range(kk)]
        if len(cs) < kk: cs += [rng.choice(cols) for _ in range(kk - len(cs))]
        if place_shapes(rng, g, shapes, cs, margin=1) is None: return None
        for _ in range(noise * (2 if h * w > 400 else 1)):
            r, c = rng.randrange(h), rng.randrange(w)
            if all(g[y][x] == 0 for y in range(max(0, r - 1), min(h, r + 2)) for x in range(max(0, c - 1), min(w, c + 2))): g[r][c] = rng.choice(cols)
        return g
    return sc
def rect_scene(k=(3, 6), cols=OC, hollow_p=0.5, size=(9, 18)):
    def sc(rng):
        h, w = _hw(rng, *size); g = blank(h, w); kk = rng.randint(*k) + (3 if h * w > 400 else 0)
        # make each rectangle either fully solid or a clean ring
        shapes = []
        for _ in range(kk):
            a, b = rng.randint(3, 6), rng.randint(3, 6); ring = rng.random() < hollow_p
            shapes.append([(r, c) for r in range(a) for c in range(b) if not ring or r in (0, a - 1) or c in (0, b - 1)])
        cs = [rng.choice(cols) for _ in shapes]
        return g if place_shapes(rng, g, shapes, cs, margin=1) is not None else None
    return sc
def dots_scene(cols=OC, dens=0.18, ncol=(2, 4)):
    def sc(rng):
        h, w = _hw(rng, 8, 16); cs = rng.sample(cols, rng.randint(*ncol)); g = blank(h, w)
        for r in range(h):
            for c in range(w):
                if rng.random() < dens: g[r][c] = rng.choice(cs) if rng.random() < 0.6 else cs[0]
        return g
    return sc
def panels_scene(dens=0.3):
    def sc(rng):
        h, w = (rng.randint(8, 30), rng.randint(10, 14)) if rng.random() < 0.45 else (rng.randint(6, 14), rng.randint(5, 9)); cs = rng.sample(OC, 2)
        mk = lambda: [[rng.choice(cs) if rng.random() < dens else 0 for _ in range(w)] for _ in range(h)]
        a, b = mk(), mk(); return [x + [5] + y for x, y in zip(a, b)]
    return sc
def blocks_scene(inner):
    def sc(rng):
        g = inner(rng)
        if g is None: return None
        g = [[v for v in r for _ in (0, 1)] for r in g for _ in (0, 1)]
        return g if len(g) <= 30 and len(g[0]) <= 30 else None
    return sc


# ------------------------------------------------------------------ pipelines
def _run(g, steps):
    cur, seen = g, [g]
    for s in steps:
        nxt = s.fn(cur)
        if not _ok(nxt) or any(nxt == p for p in seen): return None
        seen.append(nxt); cur = nxt
    return cur if len({v for r in cur for v in r}) >= 2 else None

RULES = []
def pipe(name, scene, steps, digits=False, small=False):
    desc = ", then ".join(s.text for s in steps) + "."
    desc = desc[0].upper() + desc[1:]
    def gen(rng, scene=scene, steps=steps):
        for _ in range(600):
            g = scene(rng)
            if g is not None and _run(g, steps) is not None: return g
        raise RuntimeError(name)
    RULES.append((name, [s.fam for s in steps]))
    rule(name, desc, gen, lambda g, steps=steps: _run(g, steps), digits=digits, small_ok=small)

O = obj_scene()
O4 = obj_scene(cols=[1, 2, 3, 4], distinct=True, k=(2, 4))
O3 = obj_scene(k=(3, 6), n=(3, 6))
OD = obj_scene(k=(3, 7), odd=True, n=(3, 7))
OS = obj_scene(k=(2, 5), n=(3, 9))
NZ = obj_scene(noise=6, k=(2, 4))
RC = rect_scene()
RH = rect_scene(cols=[1, 2, 4, 6, 7, 8, 9], hollow_p=0.7)
RH5 = rect_scene(cols=[1, 2, 3, 4, 6, 7, 8, 9], hollow_p=0.7)
DT = dots_scene(); DT12 = dots_scene(cols=[1, 2, 3], ncol=(3, 3))
def rarest_scene(rng):
    for _ in range(100):
        h, w = _hw(rng, 14, 20, 0.5); a, b, c = rng.sample([1, 2, 4, 6, 7, 8, 9], 3); k = rng.randint(1, 5); g = blank(h, w)
        shapes, cs = [], []
        for _i in range(k): shapes.append([(r, q) for r in range(3) for q in range(3) if (r, q) != (1, 1)]); cs.append(a)
        tot = 0
        while tot <= 8 * k: shapes.append([(r, q) for r in range(4) for q in range(4)]); cs.append(b); tot += 16
        shapes.append([(r, q) for r in range(4) for q in range(4)]); cs.append(c); shapes.append([(r, q) for r in range(3) for q in range(4)]); cs.append(c)
        if place_shapes(rng, g, shapes, cs, margin=1) is not None: return g
    return None
PN = panels_scene()
BL = blocks_scene(obj_scene(k=(2, 4), n=(3, 6), size=(5, 11)))

# A: object scene
pipe("crop_largest_mirror_then_grey_border", O, [crop_largest(), flip_h(), add_border(5)])
pipe("row_by_size_equal_height_baseline", O3, [sort_left_by_size(), equalise_height(), baseline(5)])
pipe("object_bars_sorted_median_marked", OD, [objs_to_bars(), sort_bars(), mark_median(5)])
pipe("quarter_turn_drop_top_row_swap_one_two", O4, [rot_cw(), del_first_row(), swap12()])
pipe("drop_edge_objects_grey_smallest_tile_beside", O, [del_border(), recol_smallest(5), tile_h()], small=True)
pipe("drop_smallest_slide_right_mirror_below", O, [del_smallest(), slide_right(), mirror_below()], small=True)
pipe("smallest_object_tiled_then_outlined", O, [crop_smallest(), tile_22(), outline()])
pipe("slide_left_quarter_turn_object_count_bar", O, [slide_left(), rot_cw(), bar_objects(4)])
pipe("solid_boxes_upside_down_blue_border", O, [bbox_fill(), rot_180(), add_border(1)])
pipe("largest_object_turned_mirrored_beside", O, [crop_largest(), rot_cw(), mirror_right()])
pipe("crop_enlarge_smallest_grey", O, [crop_all(), scale2(), recol_smallest(5)], small=True)
pipe("flip_slide_left_lowest_grey", O, [flip_v(), slide_left(), recol_lowest(5)])
pipe("drop_largest_turn_anticlockwise_green_border", O, [del_largest(), rot_ccw(), add_border(3)])
pipe("size_digits_crop_largest_grey_border", OS, [recol_by_size_digit(), crop_largest(), add_border(5)], digits=True)
# N: noisy objects
pipe("denoise_slide_right_lowest_grey", NZ, [denoise(), slide_right(), recol_lowest(5)])
pipe("denoise_outline_tile_beside", NZ, [denoise(), outline(), tile_h()], small=True)
pipe("rise_denoise_upside_down", NZ, [rise_up(), denoise(), rot_180()])
# R: rectangles
pipe("outline_tile_beside_grey_baseline", RC, [outline(), tile_h(), baseline(5)], small=True)
pipe("enlarge_outline_drop_last_column", RC, [scale2(), outline(), del_last_col()], small=True)
pipe("fill_holes_flip_crop_to_content", RC, [fill_holes(5), flip_v(), crop_all()])
pipe("drop_edge_rectangles_outline_stack_two", RC, [del_border(), outline(), tile_v()], small=True)
pipe("holed_rectangles_slide_right_smallest_grey", RH, [keep_holed(), slide_right(), recol_smallest(5)])
pipe("frame_each_crop_upside_down", RC, [frame_each(5), crop_all(), rot_180()])
pipe("largest_grey_transpose_fall", RC, [recol_largest(5), transpose_(), fall_down()])
# H: holey
pipe("rarest_colour_fill_holes_row_by_size", rarest_scene, [keep_rarest(), fill_holes(3), sort_left_by_size()])
pipe("holed_objects_fill_stack_column", RH5, [keep_holed(), fill_holes(5), stack_column()], small=True)
pipe("drop_smallest_fill_holes_crop", RH, [del_smallest(), fill_holes(3), crop_all()])
pipe("holed_objects_crop_object_count_bar", RH, [keep_holed(), crop_all(), bar_objects(4)])
pipe("smallest_fill_holes_enlarge", RH, [crop_smallest(), fill_holes(5), scale2()])
# D: dots
pipe("rise_anticlockwise_swap_one_two", DT12, [rise_up(), rot_ccw(), swap12()])
pipe("commonest_colour_fall_stack_two", DT, [keep_commonest(), fall_down(), tile_v()], small=True)
pipe("drop_first_column_commonest_enlarge", DT, [del_first_col(), keep_commonest(), scale2()], small=True)
pipe("slide_left_rarest_mirror_beside", DT, [slide_left(), keep_rarest(), mirror_right()], small=True)
pipe("slide_right_flip_rarest_colour", DT, [slide_right(), flip_v(), keep_rarest()])
pipe("drop_last_row_upside_down_all_grey", DT, [del_last_row(), rot_180(), recol_all(5)])
# P: two panels
pipe("panels_and_fall_grey_ring", PN, [panels_and(), fall_down(), ring_recolour(5)])
pipe("panels_stacked_outline_transpose", PN, [panels_stack(), outline(), transpose_()])
pipe("panels_xor_quarter_turn_baseline", PN, [panels_xor(), rot_cw(), baseline(5)])
# B: blocks
pipe("shrink_transpose_grey_ring", BL, [shrink2(), transpose_(), ring_recolour(5)])
pipe("shrink_quarter_turn_drop_first_column", BL, [shrink2(), rot_cw(), del_first_col()])


def _check_distinct():
    for i, (n1, a) in enumerate(RULES):
        for n2, b in RULES[i + 1:]:
            if sum(x == y for x, y in zip(a, b)) >= 2: print("PAIR", n1, n2, a, b)
_check_distinct()
