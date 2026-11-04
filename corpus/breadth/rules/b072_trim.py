# b072_trim.py -- TRIM OR GROW TO AN INVARIANT: every object is edited, object by object, until it satisfies one stated
# internal property (inscribed square, symmetry, rectangle, equal row lengths, uniform wall thickness, equal plus arms,
# whole periods, no 1-wide spurs or notches, equal bounding boxes, thickness one ...). The property is the whole rule.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


def D(rng, lo=8, hi=30):
    if hi >= 21 and rng.random() < 0.45:
        return rng.randint(21, hi)
    return rng.randint(lo, min(hi, 20))


def src(rng, ex=(0,)):
    return rng.choice([c for c in range(1, 10) if c not in ex])


def mk(gen, tf, cond=None, tries=90):
    def make(rng):
        last = None
        for _ in range(tries):
            g = gen(rng)
            if g is None: continue
            last = g
            o = tf(g)
            if o is None or o == g: continue
            if cond is None or cond(g, o): return g
        return last if last is not None else blank(8, 8)
    return make


def scatter_subs(rng, H, Wd, subs, margin=1):
    g = blank(H, Wd); boxes = []
    for sub in subs:
        h, w = dims(sub)
        if h > H or w > Wd: return None
        for _ in range(150):
            r0, c0 = rng.randint(0, H - h), rng.randint(0, Wd - w)
            if all(r0 > b[2] + margin or r0 + h - 1 < b[0] - margin or c0 > b[3] + margin or c0 + w - 1 < b[1] - margin for b in boxes):
                boxes.append((r0, c0, r0 + h - 1, c0 + w - 1)); paste(g, sub, r0, c0, transparent=0); break
        else:
            return None
    return g


def scene(subfn, kmax=6, lo=10, margin=1, per=120):
    def gen(rng):
        H, Wd = D(rng, lo, 30), D(rng, lo, 30); k = rng.randint(1, max(1, min(kmax, 1 + H * Wd // per))); subs = []
        for _ in range(k):
            s = subfn(rng)
            if s is None: return None
            subs.append(s)
        return scatter_subs(rng, H, Wd, subs, margin)
    return gen


def per(fn, conn8=True):
    """apply fn(cellset, bbox, colour) -> set of cells to every same-colour object; None rejects the input"""
    def tf(g):
        H, W = dims(g); cm = objects(g, 0, conn8=conn8)
        if not cm: return None
        out = copy(g); new = []
        for c in cm:
            col = g[c[0][0]][c[0][1]]; res = fn(set(c), bbox(c), col)
            if res is None or any(not (0 <= r < H and 0 <= x < W) for r, x in res): return None
            for r, x in c: out[r][x] = 0
            new.append((res, col))
        for res, col in new:
            for r, x in res: out[r][x] = col
        return out
    return tf


def solid(S, r0, c0, r1, c1): return all((r, c) in S for r in range(r0, r1 + 1) for c in range(c0, c1 + 1))


def rblob(rng, lo=4, hi=9):
    h, w = rng.randint(lo, hi), rng.randint(lo, hi); S = set()
    for i in range(rng.randint(2, 4)):
        for _ in range(20):
            rh, rw = rng.randint(2, h), rng.randint(2, w); r0, c0 = rng.randint(0, h - rh), rng.randint(0, w - rw)
            cs = {(r, c) for r in range(r0, r0 + rh) for c in range(c0, c0 + rw)}
            if not S or S & cs: S |= cs; break
    r0, c0, r1, c1 = bbox(list(S)); a = src(rng)
    g = blank(r1 - r0 + 1, c1 - c0 + 1)
    for r, c in S: g[r - r0][c - c0] = a
    return g


def rect_sub(rng, hlo=2, hhi=8, wlo=2, whi=9):
    h, w = rng.randint(hlo, hhi), rng.randint(wlo, whi); return [[src(rng)] * w for _ in range(h)] if False else (lambda a: [[a] * w for _ in range(h)])(src(rng))


# ============================================================ scene A: blobs (symmetry, squares, rectangles)
def f_square(S, b, col):
    r0, c0, r1, c1 = b
    for k in range(min(r1 - r0, c1 - c0) + 1, 1, -1):
        for r in range(r0, r1 - k + 2):
            for c in range(c0, c1 - k + 2):
                if solid(S, r, c, r + k - 1, c + k - 1): return {(y, x) for y in range(r, r + k) for x in range(c, c + k)}
    return None
rule("blob_trimmed_to_largest_inscribed_square", "Each object is cut down to its largest solid square (side at least 2) made only of its own cells; among equal squares the one with the highest top row wins, then the one with the leftmost left column; all other cells of the object are erased.",
     mk(scene(rblob), per(f_square)), per(f_square))


def f_rect(S, b, col):
    r0, c0, r1, c1 = b; best = None
    for a in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            for d in range(a, r1 + 1):
                for e in range(c, c1 + 1):
                    if not solid(S, a, c, d, e): break
                    key = (-(d - a + 1) * (e - c + 1), a, c, d - a)
                    if best is None or key < best[0]: best = (key, (a, c, d, e))
    a, c, d, e = best[1]
    return {(y, x) for y in range(a, d + 1) for x in range(c, e + 1)}
rule("blob_trimmed_to_largest_rectangle", "Each object is cut down to the solid rectangle of most cells that fits inside it; ties go to the rectangle with the higher top row, then the leftmost left column, then the smaller height; every other cell of the object is erased.",
     mk(scene(rblob), per(f_rect)), per(f_rect))


def f_trimlr(S, b, col):
    r0, c0, r1, c1 = b; return {(r, c) for r, c in S if (r, c0 + c1 - c) in S}
rule("blob_trimmed_to_left_right_symmetry", "Each object keeps only the cells whose mirror image across the vertical centre line of the object's original bounding box is also a cell of the object; cells without a mirror partner are erased.",
     mk(scene(rblob), per(f_trimlr)), per(f_trimlr))


def f_growlr(S, b, col):
    r0, c0, r1, c1 = b; return S | {(r, c0 + c1 - c) for r, c in S}
rule("blob_grown_to_left_right_symmetry", "Each object gets the mirror image of every one of its cells added across the vertical centre line of its bounding box, so it becomes left-right symmetric (same colour).",
     mk(scene(rblob), per(f_growlr)), per(f_growlr))


def f_grow4(S, b, col):
    r0, c0, r1, c1 = b; T = S | {(r, c0 + c1 - c) for r, c in S}; return T | {(r0 + r1 - r, c) for r, c in T}
rule("blob_grown_to_four_fold_symmetry", "Each object gets added, in its own colour, the mirror image of every cell across both the vertical and the horizontal centre lines of its bounding box (and the double mirror), so it becomes symmetric both left-right and top-bottom.",
     mk(scene(rblob), per(f_grow4)), per(f_grow4))


def f_trim4(S, b, col):
    r0, c0, r1, c1 = b
    return {(r, c) for r, c in S if (r, c0 + c1 - c) in S and (r0 + r1 - r, c) in S and (r0 + r1 - r, c0 + c1 - c) in S}
rule("blob_trimmed_to_four_fold_symmetry", "Each object keeps only the cells whose mirror images across the vertical centre line, the horizontal centre line and both of its original bounding box are all cells of the object; every other cell is erased.",
     mk(scene(rblob), per(f_trim4)), per(f_trim4))


def f_bbox(S, b, col):
    r0, c0, r1, c1 = b; return {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)}
rule("blob_grown_to_fill_its_bounding_box", "Each object grows, in its own colour, until it is a solid rectangle: every empty cell inside the object's bounding box takes the object's colour.",
     mk(scene(rblob), per(f_bbox)), per(f_bbox))


# ============================================================ scene B: rectangles with 1-wide defects
def b_spurs(rng):
    h, w = rng.randint(4, 8), rng.randint(4, 8); m = 3; g = blank(h + 2 * m, w + 2 * m); a = src(rng)
    for r in range(h):
        for c in range(w): g[m + r][m + c] = a
    for _ in range(rng.randint(1, 4)):
        side = rng.randrange(4); L = rng.randint(1, 3)
        if side < 2:
            c = m + rng.randint(1, w - 2)
            for i in range(L): g[(m - 1 - i) if side == 0 else (m + h + i)][c] = a
        else:
            r = m + rng.randint(1, h - 2)
            for i in range(L): g[r][(m - 1 - i) if side == 2 else (m + w + i)] = a
    return g


def f_spur(S, b, col):
    K = {(r, c) for r, c in S if any(all((r + dr + i, c + dc + j) in S for i in (0, 1) for j in (0, 1)) for dr in (-1, 0) for dc in (-1, 0))}
    return K or None
rule("one_wide_spurs_removed", "Each object keeps only the cells that belong to some 2x2 block of its own cells; every cell that sticks out as a one-cell-wide spur of any length is erased.",
     mk(scene(b_spurs), per(f_spur)), per(f_spur))


def b_notch(rng):
    h, w = rng.randint(4, 9), rng.randint(4, 9); a = src(rng); g = [[a] * w for _ in range(h)]
    for _ in range(rng.randint(1, 4)):
        if rng.random() < .5: g[rng.choice((0, h - 1))][rng.randint(1, w - 2)] = 0
        else: g[rng.randint(1, h - 2)][rng.choice((0, w - 1))] = 0
    return g


def f_notch(S, b, col):
    r0, c0, r1, c1 = b; out = set(S)
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if (r, c) not in S and (((r, c - 1) in S and (r, c + 1) in S) or ((r - 1, c) in S and (r + 1, c) in S)): out.add((r, c))
    return out
rule("one_wide_notches_filled", "Inside each object's bounding box every empty cell that has an object cell directly on both sides of it (left and right, or above and below) is filled with the object's colour, closing one-cell-wide notches.",
     mk(scene(b_notch), per(f_notch)), per(f_notch))


def b_cols(rng):
    h, w = rng.randint(5, 9), rng.randint(5, 10); a = src(rng); g = [[a] * w for _ in range(h)]
    for c in range(w):
        if rng.random() < .55:
            for r in range(rng.randint(1, 2)): g[r][c] = 0
        if rng.random() < .45:
            for r in range(rng.randint(1, 2)): g[h - 1 - r][c] = 0
    return g


def f_fullcol(S, b, col):
    r0, c0, r1, c1 = b; K = {(r, c) for r, c in S if all((y, c) in S for y in range(r0, r1 + 1))}
    return K or None
rule("keep_only_full_height_columns", "Each object keeps only the cells in columns that are filled from the top row to the bottom row of the object's bounding box; cells in any shorter column are erased.",
     mk(scene(b_cols), per(f_fullcol)), per(f_fullcol))


def b_rect(rng):
    h, w = rng.randint(2, 9), rng.randint(2, 9)
    if h == w: return None
    a = src(rng); return [[a] * w for _ in range(h)]


def f_tosq(S, b, col):
    r0, c0, r1, c1 = b; m = min(r1 - r0, c1 - c0) + 1
    return {(r, c) for r in range(r0, r0 + m) for c in range(c0, c0 + m)}
rule("rectangle_trimmed_to_square_from_bottom_right", "Each solid rectangle that is not square is cut down to a square with its top-left corner fixed: if it is taller than wide, rows are removed from the bottom; if it is wider than tall, columns are removed from the right.",
     mk(scene(b_rect), per(f_tosq)), per(f_tosq))


def b_rect_res(rng):
    h, w = rng.randint(2, 8), rng.randint(2, 8)
    if h == w: return None
    m = max(h, w); a = src(rng); g = blank(m, m)
    for r in range(h):
        for c in range(w): g[r][c] = a
    return g


def f_grsq(S, b, col):
    r0, c0, r1, c1 = b; m = max(r1 - r0, c1 - c0) + 1
    return {(r, c) for r in range(r0, r0 + m) for c in range(c0, c0 + m)}
rule("rectangle_grown_to_square_down_or_right", "Each solid rectangle that is not square grows into a square with its top-left corner fixed: if it is wider than tall, rows are added at the bottom; if it is taller than wide, columns are added on the right (in its own colour).",
     mk(scene(b_rect_res), per(f_grsq)), per(f_grsq))


# ============================================================ scene C: cross-shaped objects
def b_cross(rng):
    h, w = rng.randint(5, 11), rng.randint(5, 11); a = src(rng); g = [[a] * w for _ in range(h)]
    t1, t2 = rng.randint(1, (h - 1) // 2), rng.randint(1, (h - 1) // 2); l1, l2 = rng.randint(1, (w - 1) // 2), rng.randint(1, (w - 1) // 2)
    cs = [(0, 0, rng.randint(1, h - 2 - 0), rng.randint(1, l1)), (0, 1, rng.randint(1, t1), rng.randint(1, l2)), (1, 0, rng.randint(1, t2), rng.randint(1, l1)), (1, 1, rng.randint(1, t2), rng.randint(1, l2))]
    # corner cuts limited so a central full row band and full column band survive
    mh, mw = (h - 1) // 2, (w - 1) // 2
    for bot, rgt, ch, cw in cs:
        ch, cw = min(ch, mh), min(cw, mw)
        for r in range(ch):
            for c in range(cw): g[h - 1 - r if bot else r][w - 1 - c if rgt else c] = 0
    return g


def f_core(S, b, col):
    r0, c0, r1, c1 = b
    fr = [r for r in range(r0, r1 + 1) if all((r, c) in S for c in range(c0, c1 + 1))]
    fc = [c for c in range(c0, c1 + 1) if all((r, c) in S for r in range(r0, r1 + 1))]
    return {(r, c) for r in fr for c in fc} or None
rule("cross_trimmed_to_convex_core", "Each object keeps only the cells where a row that is completely filled across the object's bounding box meets a column that is completely filled down it (its convex core); all arms and corner-adjacent cells outside that core are erased.",
     mk(scene(b_cross), per(f_core)), per(f_core))


# ============================================================ scene D: bars and skylines
def bar_sub(rng, grow=None):
    L = rng.randint(1, 14); a = src(rng)
    return [[a] * L + [0] * ((-L) % grow if grow else 0)]


def f_odd(S, b, col):
    r0, c0, r1, c1 = b; L = c1 - c0 + 1
    return {(r0, c) for c in range(c0, c0 + (L if L % 2 else L - 1))}
rule("bars_trimmed_to_odd_length", "Each horizontal bar with an even number of cells loses its rightmost cell so that its length is odd; bars that are already odd stay.",
     mk(scene(bar_sub, 8, 8, 1, 40), per(f_odd)), per(f_odd))


def f_m3(S, b, col):
    r0, c0, r1, c1 = b; L = (c1 - c0 + 1) // 3 * 3
    return {(r0, c) for c in range(c0, c0 + L)}
rule("bars_trimmed_to_multiple_of_three", "Each horizontal bar is cut from its right end to the largest length that is a multiple of 3, and bars shorter than 3 cells are erased.",
     mk(scene(bar_sub, 8, 8, 1, 40), per(f_m3)), per(f_m3))


def sub4(rng): return bar_sub(rng, 4)


def f_g4(S, b, col):
    r0, c0, r1, c1 = b; L = c1 - c0 + 1; L += (-L) % 4
    return {(r0, c) for c in range(c0, c0 + L)}
rule("bars_grown_to_multiple_of_four", "Each horizontal bar is extended to the right, in its own colour, to the next length that is a multiple of 4 (a bar already of such a length stays).",
     mk(scene(sub4, 8, 8, 1, 40), per(f_g4)), per(f_g4))


def bars_short(g):
    cm = objects(g, 0, conn8=True)
    if len(cm) < 2: return None
    m = min(len(c) for c in cm); out = copy(g)
    for c in cm:
        if any(len({x for _, x in c}) != len(c) for _ in [0]): return None
        cs = sorted(x for _, x in c)
        for r, x in c:
            if x > cs[0] + m - 1: out[r][x] = 0
    return out
rule("bars_all_trimmed_to_shortest_bar", "Every horizontal bar is shortened from its right end to the length of the shortest bar in the grid.",
     mk(scene(bar_sub, 8, 8, 1, 40), bars_short, lambda g, o: len(objects(g, 0, True)) >= 2), bars_short)


def sky_sub(rng, full=False):
    h = rng.randint(3, 8); Ls = [rng.randint(1, 10) for _ in range(h)]; a = src(rng)
    return [[a] * L + [0] * (10 - L if full else 0) for L in Ls] if False else [[a] * L + [0] * (max(Ls) - L) for L in Ls]


def f_skymin(S, b, col):
    r0, c0, r1, c1 = b; rows = {}
    for r, c in S: rows[r] = rows.get(r, 0) + 1
    m = min(rows.values()); return {(r, c0 + i) for r in rows for i in range(m)}
rule("stacked_rows_trimmed_to_shortest", "Each object is a stack of left-aligned rows of different lengths; every row is cut from its right end down to the length of the object's shortest row.",
     mk(scene(sky_sub, 4, 10, 1, 90), per(f_skymin)), per(f_skymin))


def f_skymax(S, b, col):
    r0, c0, r1, c1 = b; rows = {}
    for r, c in S: rows[r] = rows.get(r, 0) + 1
    m = max(rows.values()); return {(r, c0 + i) for r in rows for i in range(m)}
rule("stacked_rows_grown_to_longest", "Each object is a stack of left-aligned rows of different lengths; every row is extended to the right, in the object's colour, to the length of the object's longest row.",
     mk(scene(sky_sub, 4, 10, 1, 90), per(f_skymax)), per(f_skymax))


def f_widest(S, b, col):
    rows = {}
    for r, c in S: rows.setdefault(r, []).append(c)
    m = max(len(v) for v in rows.values()); return {(r, c) for r, v in rows.items() if len(v) == m for c in v}
rule("keep_only_the_widest_rows", "Each object is a stack of left-aligned rows of different lengths; only the rows as long as the object's longest row are kept (all of them, if several tie) and the shorter rows are erased.",
     mk(scene(sky_sub, 4, 10, 1, 90), per(f_widest)), per(f_widest))


# ============================================================ frames
def frame_sub(rng):
    h, w = rng.randint(8, 16), rng.randint(8, 16); t = [rng.randint(1, 3) for _ in range(4)]
    if len(set(t)) == 1: return None
    a = src(rng); g = [[a] * w for _ in range(h)]
    for r in range(t[0], h - t[1]):
        for c in range(t[2], w - t[3]): g[r][c] = 0
    return g


def thick(S, b):
    r0, c0, r1, c1 = b; t = []
    for line, rng_, axis in ((range(r0, r1 + 1), range(c0, c1 + 1), 0), (range(r1, r0 - 1, -1), range(c0, c1 + 1), 0), (range(c0, c1 + 1), range(r0, r1 + 1), 1), (range(c1, c0 - 1, -1), range(r0, r1 + 1), 1)):
        n = 0
        for x in line:
            if all(((x, y) if axis == 0 else (y, x)) in S for y in rng_): n += 1
            else: break
        t.append(n)
    return t


def f_ftrim(S, b, col):
    r0, c0, r1, c1 = b; m = min(thick(S, b))
    return {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if r - r0 < m or r1 - r < m or c - c0 < m or c1 - c < m}
rule("frame_trimmed_to_thinnest_wall", "Each rectangular frame has four walls of possibly different thickness; the inner edge of every wall is trimmed away so that all four walls have the thickness of the thinnest wall (the outer outline stays).",
     mk(scene(frame_sub, 3, 12, 1, 150), per(f_ftrim)), per(f_ftrim))


def f_fgrow(S, b, col):
    r0, c0, r1, c1 = b; m = max(thick(S, b))
    return {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if r - r0 < m or r1 - r < m or c - c0 < m or c1 - c < m}
rule("frame_grown_to_thickest_wall", "Each rectangular frame has four walls of possibly different thickness; the thinner walls grow inward, in the frame's colour, until all four walls have the thickness of the thickest wall (the outer outline stays).",
     mk(scene(frame_sub, 3, 12, 1, 150), per(f_fgrow)), per(f_fgrow))


# ============================================================ plus shapes with unequal arms
def plus_sub(rng, canvas=False):
    ar = [rng.randint(1, 6) for _ in range(4)]
    if len(set(ar)) == 1: return None
    R = max(ar); a = src(rng); g = blank(2 * R + 1, 2 * R + 1); g[R][R] = a
    for i in range(1, ar[0] + 1): g[R - i][R] = a
    for i in range(1, ar[1] + 1): g[R + i][R] = a
    for i in range(1, ar[2] + 1): g[R][R - i] = a
    for i in range(1, ar[3] + 1): g[R][R + i] = a
    return g


def arms(S):
    ctr = [(r, c) for r, c in S if all((r + dr, c + dc) in S for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)))]
    if len(ctr) != 1: return None
    r, c = ctr[0]; out = []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        n = 0
        while (r + dr * (n + 1), c + dc * (n + 1)) in S: n += 1
        out.append(n)
    return r, c, out


def f_pmin(S, b, col):
    a = arms(S)
    if not a: return None
    r, c, ar = a; m = min(ar); return {(r, c)} | {(r + dr * i, c + dc * i) for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)) for i in range(1, m + 1)}
rule("plus_arms_trimmed_to_shortest", "Each plus-shaped object (one centre cell with four straight arms of different lengths) has every arm cut from its tip down to the length of its shortest arm.",
     mk(scene(plus_sub, 3, 14, 1, 150), per(f_pmin, False)), per(f_pmin, False))


def f_pmax(S, b, col):
    a = arms(S)
    if not a: return None
    r, c, ar = a; m = max(ar); return {(r, c)} | {(r + dr * i, c + dc * i) for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)) for i in range(1, m + 1)}
rule("plus_arms_grown_to_longest", "Each plus-shaped object (one centre cell with four straight arms of different lengths) has every shorter arm extended, in the object's colour, to the length of its longest arm.",
     mk(scene(plus_sub, 3, 14, 1, 150), per(f_pmax, False)), per(f_pmax, False))


# ============================================================ periodic strips
def strip_sub(rng, rem_ok=True):
    p = rng.randint(2, 5); hh = rng.randint(1, 3); k = rng.randint(3, 5) if p < 4 else rng.randint(3, 4)
    a, b = rng.sample(range(1, 10), 2); tile = [[rng.choice((a, b)) for _ in range(p)] for _ in range(hh)]
    cols = [tuple(tile[r][c] for r in range(hh)) for c in range(p)]
    if any(all(cols[i] == cols[(i + q) % p] for i in range(p)) for q in range(1, p) if p % q == 0): return None
    if len(set(cols)) == 1: return None
    L = p * k + rng.randint(1, p - 1)
    return [[tile[r][c % p] for c in range(L)] for r in range(hh)]


def mobj(g):
    return components(g, lambda v: v != 0, conn8=False) if False else _mc(g)


def _mc(g):
    H, W = dims(g); seen = set(); out = []
    for r in range(H):
        for c in range(W):
            if g[r][c] and (r, c) not in seen:
                st = [(r, c)]; seen.add((r, c)); cm = []
                while st:
                    y, x = st.pop(); cm.append((y, x))
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        ny, nx = y + dr, x + dc
                        if 0 <= ny < H and 0 <= nx < W and g[ny][nx] and (ny, nx) not in seen: seen.add((ny, nx)); st.append((ny, nx))
                out.append(cm)
    return out


def strip_tf(mode):
    def tf(g):
        H, W = dims(g); out = copy(g); cms = _mc(g)
        if not cms: return None
        for cm in cms:
            r0, c0, r1, c1 = bbox(cm); L = c1 - c0 + 1
            cols = [tuple(g[r][c0 + i] for r in range(r0, r1 + 1)) for i in range(L)]
            p = next((q for q in range(1, L) if all(cols[i] == cols[i + q] for i in range(L - q))), None)
            if p is None or L < 2 * p + 1: return None
            newL = L // p * p if mode == 'trim' else (-(-L // p) * p if mode == 'grow' else p)
            if c0 + newL > W: return None
            for r in range(r0, r1 + 1):
                for i in range(max(L, newL)):
                    out[r][c0 + i] = cols[i % p][r - r0] if i < newL else 0
        return out
    return tf


def strip_res(rng):
    s = strip_sub(rng)
    if s is None: return None
    L = len(s[0]); cols = [tuple(s[r][c] for r in range(len(s))) for c in range(L)]
    p = next(q for q in range(1, L) if all(cols[i] == cols[i + q] for i in range(L - q)))
    pad = (-L) % p
    return [row + [0] * pad for row in s]
rule("periodic_strip_trimmed_to_whole_periods", "Each horizontal strip repeats a tile of columns (its shortest repeating width, the period) and ends partway through a tile; the incomplete last tile is erased so the strip holds a whole number of periods.",
     mk(scene(strip_sub, 5, 12, 1, 90), strip_tf('trim')), strip_tf('trim'))
rule("periodic_strip_completed_to_whole_periods", "Each horizontal strip repeats a tile of columns (its shortest repeating width, the period) and ends partway through a tile; the strip is continued to the right, repeating the pattern, until the last tile is complete.",
     mk(scene(strip_res, 5, 12, 1, 90), strip_tf('grow')), strip_tf('grow'))
rule("periodic_strip_reduced_to_one_period", "Each horizontal strip repeats a tile of columns (its shortest repeating width, the period); everything after the first period, counted from the strip's left end, is erased.",
     mk(scene(strip_sub, 5, 12, 1, 90), strip_tf('one')), strip_tf('one'))


# ============================================================ touching objects
def touch_sub(rng):
    h1, w1, h2, w2 = rng.randint(2, 6), rng.randint(2, 6), rng.randint(2, 6), rng.randint(2, 6)
    if h1 * w1 == h2 * w2: return None
    a, b = rng.sample(range(1, 10), 2); side = rng.random() < .5
    if side:
        off = rng.randint(-(h2 - 1), h1 - 1); top = min(0, off); g = blank(max(h1, off + h2) - top, w1 + w2)
        for r in range(h1):
            for c in range(w1): g[r - top][c] = a
        for r in range(h2):
            for c in range(w2): g[off + r - top][w1 + c] = b
    else:
        off = rng.randint(-(w2 - 1), w1 - 1); lft = min(0, off); g = blank(h1 + h2, max(w1, off + w2) - lft)
        for r in range(h1):
            for c in range(w1): g[r][c - lft] = a
        for r in range(h2):
            for c in range(w2): g[h1 + r][off + c - lft] = b
    return g


def tf_touch(g):
    cms = [c for col in range(1, 10) for c in components(g, col, conn8=False)]
    out = copy(g); idx = {}
    for i, c in enumerate(cms):
        for p in c: idx[p] = i
    adj = {}
    for p, i in idx.items():
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            q = (p[0] + dr, p[1] + dc)
            if q in idx and idx[q] != i: adj.setdefault(i, set()).add(idx[q])
    if not adj or any(len(v) != 1 for v in adj.values()): return None
    done = set()
    for i, v in adj.items():
        j = next(iter(v))
        if (min(i, j), max(i, j)) in done: continue
        done.add((min(i, j), max(i, j)))
        if len(cms[i]) == len(cms[j]): return None
        big, small = (i, j) if len(cms[i]) > len(cms[j]) else (j, i)
        for p in cms[big]:
            if any(idx.get((p[0] + dr, p[1] + dc)) == small for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))): out[p[0]][p[1]] = 0
    return out
rule("larger_touching_rectangle_gives_up_contact_edge", "Rectangles of different colours come in touching pairs; in each pair the rectangle with more cells loses every cell that is edge-adjacent to the other rectangle (its contact line), so the pair no longer touches (pairs never have equal areas).",
     mk(scene(touch_sub, 3, 10, 1, 120), tf_touch), tf_touch)


def lane_gen(rng):
    H, Wd = D(rng, 10, 30), D(rng, 14, 30); g = blank(H, Wd); r = rng.randint(0, 1)
    while r + 3 <= H:
        hl = rng.randint(2, 4)
        if r + hl > H: break
        c = rng.randint(0, 2)
        while c < Wd - 1:
            w = rng.randint(1, 4); h = rng.randint(1, hl); r0 = r + rng.randint(0, hl - h); a = src(rng)
            if c + w > Wd: break
            for y in range(r0, r0 + h):
                for x in range(c, c + w): g[y][x] = a
            c += w + rng.randint(1, 6)
        r += hl + 1
    return g


def tf_lane(g):
    out = copy(g); H, W = dims(g)
    for r in range(H):
        for c in range(W - 1):
            if g[r][c] and g[r][c + 1] == 0:
                x = c + 1
                while x < W and g[r][x] == 0: x += 1
                if x < W:
                    for y in range(c + 1, x): out[r][y] = g[r][c]
    return out
rule("rectangles_grow_right_until_touching", "In each row, every object whose row is followed (further right) by another object cell grows to the right, in its own colour, across the empty cells in between until it touches that next object; rows with nothing further right are unchanged.",
     mk(lane_gen, tf_lane), tf_lane)


# ============================================================ equalise bounding boxes
def eq_gen(grow):
    def gen(rng):
        H, Wd = D(rng, 10, 30), D(rng, 10, 30); k = rng.randint(2, 5); dims_ = [(rng.randint(2, 8), rng.randint(2, 9)) for _ in range(k)]
        mh, mw = max(d[0] for d in dims_), max(d[1] for d in dims_)
        if len({d[0] for d in dims_}) < 2 and len({d[1] for d in dims_}) < 2: return None
        subs = []
        for (h, w) in dims_:
            a = src(rng); sh, sw = (mh, mw) if grow else (h, w); s = blank(sh, sw)
            for r in range(h):
                for c in range(w): s[r][c] = a
            subs.append(s)
        return scatter_subs(rng, H, Wd, subs)
    return gen


def eq_tf(grow):
    def tf(g):
        cm = objects(g, 0, conn8=True)
        if len(cm) < 2: return None
        bs = [bbox(c) for c in cm]; hs = [b[2] - b[0] + 1 for b in bs]; ws = [b[3] - b[1] + 1 for b in bs]
        th, tw = (max(hs), max(ws)) if grow else (min(hs), min(ws)); out = copy(g)
        for c, b in zip(cm, bs):
            col = g[c[0][0]][c[0][1]]
            for r, x in c: out[r][x] = 0
        for c, b in zip(cm, bs):
            col = g[c[0][0]][c[0][1]]
            for r in range(b[0], b[0] + th):
                for x in range(b[1], b[1] + tw):
                    if r >= len(g) or x >= len(g[0]): return None
                    out[r][x] = col
        return out
    return tf
rule("rectangles_trimmed_to_smallest_height_and_width", "Every solid rectangle keeps its top-left corner and is cut (rows removed from the bottom, columns removed from the right) to the smallest height and the smallest width found among all rectangles in the grid.",
     mk(eq_gen(False), eq_tf(False)), eq_tf(False))
rule("rectangles_grown_to_largest_height_and_width", "Every solid rectangle keeps its top-left corner and grows (rows added at the bottom, columns added on the right, in its own colour) to the largest height and the largest width found among all rectangles in the grid.",
     mk(eq_gen(True), eq_tf(True)), eq_tf(True))


# ============================================================ L shapes and thick bars
def l_sub(rng):
    h, w = rng.randint(2, 9), rng.randint(2, 9)
    if h == w: return None
    a = src(rng); g = blank(h, w)
    for r in range(h): g[r][0] = a
    for c in range(w): g[h - 1][c] = a
    for _ in range(rng.randrange(4)): g = rot90(g)
    return g


def f_L(S, b, col):
    r0, c0, r1, c1 = b; cs = [(r0, c0), (r0, c1), (r1, c0), (r1, c1)]; emp = [p for p in cs if p not in S]
    if len(emp) != 1: return None
    er, ec = emp[0]; cr, cc = (r0 + r1 - er, c0 + c1 - ec); m = min(r1 - r0, c1 - c0) + 1
    return {(r, c) for r, c in S if abs(r - cr) < m and abs(c - cc) < m}
rule("l_shape_arms_trimmed_to_equal_length", "Each L-shaped object (one cell thick, two arms of different lengths meeting at a corner cell) has its longer arm cut from the tip until both arms have the length of the shorter one, corner cell included.",
     mk(scene(l_sub, 4, 10, 1, 100), per(f_L, False)), per(f_L, False))


def thick_sub(rng, thin=False):
    t = 1 if thin else rng.randint(2, 5); L = rng.randint(max(t + 2, 4), 14); a = src(rng); pad = 1 if thin else 0
    g = blank(t + 2 * pad, L)
    for r in range(t):
        for c in range(L): g[r + pad][c] = a
    return transpose(g) if rng.random() < .5 else g


def f_line(S, b, col):
    r0, c0, r1, c1 = b
    if r1 - r0 < c1 - c0: m = r0 + (r1 - r0) // 2; return {(m, c) for c in range(c0, c1 + 1)}
    m = c0 + (c1 - c0) // 2; return {(r, m) for r in range(r0, r1 + 1)}
rule("thick_bar_trimmed_to_middle_line", "Each solid bar thicker than one cell is cut down to a line one cell thick along its long direction: the middle row (or column) is kept, and for an even thickness the one nearer the top (or left) of the two middle ones.",
     mk(scene(thick_sub, 6, 10, 1, 90), per(f_line)), per(f_line))


def thin_res(rng): return thick_sub(rng, True)


def f_thick3(S, b, col):
    r0, c0, r1, c1 = b
    if r1 - r0 < c1 - c0: return {(r, c) for r in range(r0 - 1, r0 + 2) for c in range(c0, c1 + 1)}
    return {(r, c) for r in range(r0, r1 + 1) for c in range(c0 - 1, c0 + 2)}
rule("one_cell_line_thickened_to_three", "Each straight line one cell thick (longer than 1 cell) is thickened to three cells by adding, in its own colour, one parallel line on each side along its whole length.",
     mk(scene(thin_res, 6, 10, 3, 90), per(f_thick3)), per(f_thick3))
