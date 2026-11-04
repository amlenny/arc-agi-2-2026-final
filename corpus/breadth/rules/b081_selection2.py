# b081_selection2.py -- SELECTING PART OF THE SCENE, SECOND SET: the output is ONLY the selected part (rows,
# columns, a quadrant, a cropped object, kept-in-place objects or cells, or a size written as digits).
# Background is 0. An object is a 4-connected same-colour component. "Reading order" = row-major from the top-left
# of an object's first cell. A cropped object is its bounding box with every cell not belonging to it set to 0.
import sys, os
from fractions import Fraction
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


# ---------- helpers ----------
def _hw(rng, lo=4, hi=16, p=0.35):
    if rng.random() < p:
        return rng.randint(21, 30), rng.randint(21, 30), True
    return rng.randint(lo, hi), rng.randint(lo, hi), False


def _put(rng, g, shapes, cols, margin=1):
    return g if place_shapes(rng, g, shapes, cols, margin=margin, tries=400) is not None else None


def _objs(g):
    out = []
    for c in sorted({v for r in g for v in r if v}):
        for comp in components(g, c):
            out.append((c, sorted(comp)))
    out.sort(key=lambda o: o[1][0])
    return out


def _hb(o):
    r0, c0, r1, c1 = bbox(o[1])
    return r1 - r0 + 1, c1 - c0 + 1


def _crop(g, o):
    r0, c0, r1, c1 = bbox(o[1]); out = blank(r1 - r0 + 1, c1 - c0 + 1)
    for r, c in o[1]: out[r - r0][c - c0] = o[0]
    return out if len({v for r in out for v in r}) > 1 else None


def _keep(g, objs):
    out = blank(*dims(g))
    for c, cl in objs:
        for r, x in cl: out[r][x] = c
    return out


def _nz(r): return sum(1 for v in r if v)


def _nd(r): return len({v for v in r if v})


def gen_noise(rng, k=(2, 5), dens=(0.3, 0.7), excl=(0,), lo=4, hi=16):
    h, w, _ = _hw(rng, lo, hi)
    pal = colours(rng, rng.randint(*k), exclude=excl); d = rng.uniform(*dens)
    return [[rng.choice(pal) if rng.random() < d else 0 for _ in range(w)] for _ in range(h)]


def gen_obj(rng, klo=3, khi=8, nlo=2, nhi=10, plo=2, phi=5, margin=1, p=0.35, lo=6, hi=18):
    h, w, big = _hw(rng, lo, hi, p); g = blank(h, w)
    k = rng.randint(klo, khi) * (2 if big else 1); pal = colours(rng, rng.randint(plo, phi))
    return _put(rng, g, [random_shape(rng, rng.randint(nlo, nhi)) for _ in range(k)], [rng.choice(pal) for _ in range(k)], margin)


def gen_digits(rng, vmax=9):
    h, w, _ = _hw(rng, 4, 14)
    return [[rng.randint(0, vmax) for _ in range(w)] for _ in range(h)]


def _nbr_objs(g, objs):
    """for each object, the set of indices of other objects edge-adjacent to it"""
    H, W = dims(g); idx = {}
    for i, (c, cl) in enumerate(objs):
        for p in cl: idx[p] = i
    res = []
    for i, (c, cl) in enumerate(objs):
        s = set()
        for r, x in cl:
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                q = (r + dr, x + dc)
                if q in idx and idx[q] != i: s.add(idx[q])
        res.append(s)
    return res


def _enclosed(g):
    H, W = dims(g); out = []
    for comp in components(g, 0):
        if any(r in (0, H - 1) or c in (0, W - 1) for r, c in comp): continue
        out.append(comp)
    return out


# ---------- 1 ----------
def gi_1(rng): return gen_noise(rng, (4, 7), (0.5, 0.9), lo=5, hi=14)
def tf_1(g):
    out = [r for r in g if _nd(r) in (2, 3, 5, 7)]
    return out if 0 < len(out) < len(g) else None
rule("rows_prime_distinct_colours", "Output only the rows whose number of DISTINCT non-background colours is a prime number (2, 3, 5 or 7), in their original order.", gi_1, tf_1)


# ---------- 2 ----------
def gi_2(rng):
    g = gen_noise(rng, (3, 5), (0.3, 0.55)); cnt = counts(g)
    r = rng.choice([c for c in COLOURS if c not in cnt]); H, W = dims(g)
    for _ in range(rng.randint(1, 3)): g[rng.randrange(H)][rng.randrange(W)] = r
    return g
def tf_2(g):
    cnt = counts(g); cnt.pop(0, None); rare = min(cnt, key=lambda c: (cnt[c], c))
    cols = [c for c in range(len(g[0])) if any(r[c] == rare for r in g)]
    out = [[r[c] for c in cols] for r in g]
    return out if len(cols) < len(g[0]) and len({v for r in out for v in r}) > 1 else None
rule("columns_holding_rarest_colour", "The rarest non-background colour is the one with the fewest cells in the grid (tie: lower colour value). Output only the columns containing at least one cell of that colour, in their original order, full height.", gi_2, tf_2)


# ---------- 3 ----------
def gi_3(rng): return gen_obj(rng, 4, 9, 3, 8, 3, 5, margin=0, lo=6, hi=12)
def tf_3(g):
    objs = _objs(g); nb = _nbr_objs(g, objs)
    sc = [len({objs[j][0] for j in s}) for s in nb]
    if not objs or max(sc) == 0: return None
    return _crop(g, objs[sc.index(max(sc))])
rule("object_most_neighbour_colours_crop", "For each object count the distinct OTHER colours among the objects edge-touching it; output the bounding-box crop of the object with the highest count (tie: first in reading order), with cells of other objects blanked to 0.", gi_3, tf_3)


# ---------- 4 ----------
def gi_4(rng):
    h = rng.choice([rng.randint(8, 18), rng.randint(21, 30)]); w = rng.randint(6, 30); g = blank(h, w)
    k = rng.randint(2, 5)
    return _put(rng, g, [random_shape(rng, rng.randint(2, 7)) for _ in range(k)], colours(rng, k))
def tf_4(g):
    k = len(_objs(g)); out = g[::k]
    return out if len({v for r in out for v in r}) > 1 and len(out) < len(g) else None
rule("every_kth_row_k_is_object_count", "Let k be the number of objects in the grid. Output rows 0, k, 2k, 3k, ... (counting from 0 at the top), full width.", gi_4, tf_4)


# ---------- 5 ----------
def gi_5(rng):
    g = gen_noise(rng, (2, 4), (0.2, 0.5), excl=(0, 5), lo=7, hi=16); H, W = dims(g)
    for _ in range(rng.randint(2, 4)): g[rng.randrange(H)][rng.randrange(W)] = 5
    return g
def tf_5(g):
    gr = [r for r, row in enumerate(g) for v in row if v == 5]
    a, b = min(gr), max(gr)
    out = g[a + 1:b]
    return out if out and len({v for r in out for v in r}) > 1 else None
rule("rows_between_first_and_last_grey", "Grey (5) cells are scattered. Output only the rows strictly between the row of the topmost grey cell and the row of the bottommost grey cell, full width.", gi_5, tf_5)


# ---------- 6 ----------
def gi_6(rng):
    h, w, _ = _hw(rng, 6, 16, 0.5); h -= h % 2; w -= w % 2; h = max(h, 22) if h >= 20 else h; w = max(w, 22) if w >= 20 else w; g = blank(h, w); pal = colours(rng, rng.randint(2, 4))
    for qr in (0, 1):
        for qc in (0, 1):
            d = rng.uniform(0.3, 0.9)
            for r in range(qr * h // 2, (qr + 1) * h // 2):
                for c in range(qc * w // 2, (qc + 1) * w // 2):
                    if rng.random() < d: g[r][c] = rng.choice(pal)
    return g
def tf_6(g):
    H, W = dims(g); qs = []
    for qr in (0, 1):
        for qc in (0, 1):
            q = [r[qc * W // 2:(qc + 1) * W // 2] for r in g[qr * H // 2:(qr + 1) * H // 2]]
            qs.append((sum(1 for r in q for v in r if v == 0), len(qs), q))
    q = min(qs)[2]
    return q if len({v for r in q for v in r}) > 1 else None
rule("quadrant_fewest_background_cells", "Split the grid (even height and width) into four equal quadrants. Output the quadrant with the fewest background (0) cells; ties go to the first in the order top-left, top-right, bottom-left, bottom-right.", gi_6, tf_6)


# ---------- 7 ----------
def gi_7(rng):
    h, w, big = _hw(rng, 7, 18); g = blank(h, w); k = rng.randint(3, 7) * (2 if big else 1); sh = []
    for i in range(k):
        while True:
            s = random_shape(rng, rng.randint(3, 9))
            hh = max(r for r, _ in s) + 1; ww = max(c for _, c in s) + 1
            if (hh == ww) == (i == 0 or rng.random() < .3) and len(s) < hh * ww or (hh != ww and i):
                break
        sh.append(s)
    pal = colours(rng, rng.randint(2, 4))
    return _put(rng, g, sh, [rng.choice(pal) for _ in sh])
def tf_7(g):
    cand = []
    for o in _objs(g):
        h, w = _hb(o)
        if h == w >= 2 and len(o[1]) < h * w: cand.append(o)
    if not cand: return None
    o = max(cand, key=lambda o: (len(o[1]), -_objs(g).index(o)))
    return _crop(g, o)
rule("square_bbox_object_crop", "Candidates are objects whose bounding box is a square of side 2 or more and that do not fill it completely. Output the crop of the candidate with the most cells (tie: first in reading order), other cells blanked to 0.", gi_7, tf_7)


# ---------- 8 ----------
def gi_8(rng): return gen_noise(rng, (2, 4), (0.3, 0.8), lo=6, hi=18)
def tf_8(g):
    H = len(g); n = H // 3
    if n < 2: return None
    sc = []
    for b in range(n):
        band = g[3 * b:3 * b + 3]
        sc.append((sum(1 for r in band for i in range(len(r) - 1) if r[i] != r[i + 1]), -b))
    b = -max(sc)[1]
    return g[3 * b:3 * b + 3]
rule("band3_most_colour_changes", "Cut the grid into bands of 3 rows from the top (a leftover shorter band is ignored). In each band count horizontally adjacent cell pairs with different values (background included). Output the band with the most changes; ties go to the topmost.", gi_8, tf_8)


# ---------- 9 ----------
def gi_9(rng):
    g = gen_noise(rng, (2, 4), (0.4, 0.8)); H, W = dims(g)
    for j in range(W // 2):
        if rng.random() < 0.35:
            for r in range(H): g[r][W - 1 - j] = g[r][j]
    return g
def tf_9(g):
    H, W = dims(g)
    cols = [j for j in range(W) if j != W - 1 - j and all(g[r][j] == g[r][W - 1 - j] for r in range(H))]
    out = [[g[r][j] for j in cols] for r in range(H)]
    return out if cols and len(cols) < W and len({v for r in out for v in r}) > 1 else None
rule("columns_equal_to_mirror_column", "Column j and column w-1-j are mirror partners. Output only the columns that are identical to their mirror partner, in original order (for an odd width the middle column is not selected).", gi_9, tf_9)


# ---------- 10 ----------
def gi_10(rng): return gen_noise(rng, (3, 5), (0.15, 0.35), lo=6, hi=18)
def tf_10(g):
    H, W = dims(g); out = blank(H, W)
    for r in range(H):
        for c in range(W):
            v = g[r][c]
            if v and g[r].count(v) == 1 and sum(1 for y in range(H) if g[y][c] == v) == 1: out[r][c] = v
    return out if any(any(r) for r in out) and out != g else None
rule("lone_in_row_and_column_cells_kept", "A coloured cell survives, in place, only if its colour occurs exactly once in its row AND exactly once in its column; every other cell becomes 0.", gi_10, tf_10)


# ---------- 11 ----------
def gi_11(rng): return gen_obj(rng, 4, 9, 3, 8, 3, 5, margin=0, lo=6, hi=12)
def tf_11(g):
    objs = _objs(g); nb = _nbr_objs(g, objs); sc = [len(s) for s in nb]
    if not objs or max(sc) == 0: return None
    return _crop(g, objs[sc.index(max(sc))])
rule("object_touching_most_objects_crop", "Output the bounding-box crop of the object that edge-touches the largest number of other objects (tie: first in reading order), with cells of other objects blanked to 0.", gi_11, tf_11)


# ---------- 12 ----------
def gi_12(rng):
    h, w, _ = _hw(rng, 5, 16); pal = colours(rng, rng.randint(2, 3)); g = []
    for _ in range(h):
        sub = rng.sample(pal, rng.randint(1, len(pal))) if rng.random() < 0.5 else pal
        g.append([rng.choice(sub) if rng.random() < 0.8 else 0 for _ in range(w)])
    return g
def tf_12(g):
    allc = {v for r in g for v in r if v}
    out = [r for r in g if allc <= set(r)]
    return out if 0 < len(out) < len(g) else None
rule("rows_with_every_colour_present", "Output only the rows that contain every non-background colour that occurs anywhere in the grid, in original order.", gi_12, tf_12)


# ---------- 13 ----------
def gi_13(rng): return gen_obj(rng, 4, 8, 3, 10, 2, 4, lo=7, hi=18)
def tf_13(g):
    H, W = dims(g); best = (0, 0)
    for r0 in range(H):
        ok = [True] * W
        for r1 in range(r0, H):
            run = 0
            for c in range(W):
                ok[c] = ok[c] and g[r1][c] == 0
                run = run + 1 if ok[c] else 0
                if run:
                    best = max(best, ((r1 - r0 + 1) * run, r1 - r0 + 1, run)) if True else best
    return None
def _bg_rect(g):
    H, W = dims(g); best = (0, 0, 0)
    for r0 in range(H):
        ok = [True] * W
        for r1 in range(r0, H):
            run = 0
            for c in range(W):
                ok[c] = ok[c] and g[r1][c] == 0
                run = run + 1 if ok[c] else 0
                if run:
                    best = max(best, ((r1 - r0 + 1) * run, r1 - r0 + 1, run))
    return best
def tf_13(g):
    a, h, w = _bg_rect(g); h, w = min(h, 9), min(w, 9)
    return [[h, w]] if h != w else None
rule("largest_empty_rectangle_size_digits", "Find the largest axis-aligned rectangle made only of background (0) cells (most cells; tie: the one with the greater height, then the greater width). Output a 1x2 row of digits: its height, then its width, each capped at 9. Inputs where the two digits are equal are not used.", gi_13, tf_13, digits=True)


# ---------- 14 ----------
def gi_14(rng): return gen_obj(rng, 3, 7, 2, 9, 2, 5)
def tf_14(g):
    objs = _objs(g); H, W = dims(g); best = None
    for i, (c, cl) in enumerate(objs):
        n = len(cl); sr = sum(r for r, _ in cl); sc = sum(x for _, x in cl)
        d = (Fraction(sr, n) - Fraction(H - 1, 2)) ** 2 + (Fraction(sc, n) - Fraction(W - 1, 2)) ** 2
        if best is None or d < best[0]: best = (d, i)
    return _crop(g, objs[best[1]])
rule("object_nearest_grid_centre_crop", "Compare each object's centroid (mean row, mean column of its cells) with the grid's centre point ((h-1)/2, (w-1)/2) by squared Euclidean distance. Output the crop of the object with the smallest distance (tie: first in reading order), other cells blanked to 0.", gi_14, tf_14)


# ---------- 15 ----------
def gi_15(rng): return gen_obj(rng, 4, 9, 1, 9, 2, 5)
def tf_15(g):
    objs = [o for o in _objs(g) if _hb(o)[0] == _hb(o)[1]]
    return _keep(g, objs) if objs and len(objs) < len(_objs(g)) else None
rule("square_bbox_objects_kept_in_place", "Keep, in place, every object whose bounding box has equal height and width (single cells count); all other objects are erased to 0.", gi_15, tf_15)


# ---------- 16 ----------
def gi_16(rng):
    h, w, big = _hw(rng, 8, 18); g = blank(h, w); k = rng.randint(2, 5) * (2 if big else 1); pal = colours(rng, rng.randint(2, 4)); sh = []
    for _ in range(k):
        a, b = rng.randint(4, 7), rng.randint(4, 7); holes = []; m = rng.randint(0, 3)
        for _ in range(8):
            q = (rng.randint(1, a - 2), rng.randint(1, b - 2))
            if len(holes) < m and all(max(abs(q[0] - x), abs(q[1] - y)) >= 2 for x, y in holes): holes.append(q)
        sh.append([cc for cc in [(r, c) for r in range(a) for c in range(b)] if cc not in holes])
    return _put(rng, g, sh, [rng.choice(pal) for _ in sh])
def tf_16(g):
    objs = _objs(g); idx = {p: i for i, (c, cl) in enumerate(objs) for p in cl}; hc = [0] * len(objs)
    for comp in _enclosed(g):
        r, c = comp[0]
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            if (r + dr, c + dc) in idx: hc[idx[(r + dr, c + dc)]] += 1; break
    if not objs or max(hc) == 0: return None
    return _crop(g, objs[hc.index(max(hc))])
rule("object_most_holes_crop", "A hole is a background region fully enclosed by an object (not touching the grid edge). Output the crop of the object with the most holes (tie: first in reading order), other cells blanked to 0.", gi_16, tf_16)


# ---------- 17 ----------
def gi_17(rng): return gen_obj(rng, 4, 9, 2, 8, 2, 4)
def tf_17(g):
    cnt = {}
    for c, _ in _objs(g): cnt[c] = cnt.get(c, 0) + 1
    best = min(cnt, key=lambda c: (-cnt[c], c))
    out = [[v if v == best else 0 for v in r] for r in g]
    return out if len(cnt) >= 2 else None
rule("colour_with_most_objects_kept", "Count the objects of each colour; keep, in place, only the cells of the colour with the most objects (tie: lower colour value). Every other cell becomes 0.", gi_17, tf_17)


# ---------- 18 ----------
def gi_18(rng): return gen_obj(rng, 3, 8, 1, 9, 3, 6)
def tf_18(g):
    cnt = counts(g); cnt.pop(0, None)
    if len(cnt) < 2: return None
    c = min(cnt, key=lambda c: (cnt[c], c)); cl = cells(g, lambda v: v == c)
    return _crop(g, (c, cl))
rule("colour_fewest_cells_cropped", "Find the non-background colour with the fewest cells in total (tie: lower colour value). Output the bounding box of all its cells, with every cell of another colour set to 0.", gi_18, tf_18)


# ---------- 19 ----------
def gi_19(rng):
    h, w, _ = _hw(rng, 5, 16); pal = colours(rng, 3); base = []
    while len(base) < rng.randint(3, max(3, h // 2)):
        r = [rng.choice(pal + [0]) for _ in range(w)]
        if r not in base: base.append(r)
    rows = [b[:] for b in base for _ in range(rng.choice([1, 1, 2, 3]))]
    rng.shuffle(rows); return rows[:30]
def tf_19(g):
    out = [r for r in g if g.count(r) == 1]
    return out if out and len(out) < len(g) and len({v for r in out for v in r}) > 1 else None
rule("rows_occurring_exactly_once", "Output only the rows that have no exact duplicate anywhere else in the grid, in their original order.", gi_19, tf_19)


# ---------- 20 ----------
def gi_20(rng): return gen_digits(rng)
def tf_20(g):
    s = [sum(r) for r in g]; m = max(s); out = [r for r, x in zip(g, s) if x == m]
    return out if len(out) < len(g) and len({v for r in out for v in r}) > 1 else None
rule("rows_with_maximum_digit_sum", "Treat the cells as digits. Output only the rows whose digit sum equals the largest row sum (all tied rows are kept), in original order.", gi_20, tf_20, digits=True)


# ---------- 21 ----------
def gi_21(rng):
    h, w, _ = _hw(rng, 5, 16); g = []
    for _ in range(h):
        m = rng.randint(1, min(w, 9)); row = [0] * w
        for p in rng.sample(range(w), m): row[p] = rng.randint(1, max(1, m if rng.random() < .6 else 9))
        if rng.random() < .5: row[rng.choice([p for p in range(w) if row[p]])] = m
        g.append(row)
    return g
def tf_21(g):
    out = [r for r in g if _nz(r) == max(r)]
    return out if out and len(out) < len(g) and len({v for r in out for v in r}) > 1 else None
rule("rows_cellcount_equals_max_digit", "Treat the cells as digits. Output only the rows in which the number of non-zero cells equals the row's largest digit, in original order.", gi_21, tf_21, digits=True)


# ---------- 22 ----------
def gi_22(rng): return gen_digits(rng)
def tf_22(g):
    out = [[v if v and v == max(r) else 0 for v in r] for r in g]
    return out if out != g and any(any(r) for r in out) else None
rule("row_maximum_digits_kept", "In each row keep, in place, every cell equal to the row's largest digit (all ties), provided it is not 0; every other cell becomes 0.", gi_22, tf_22, digits=True)


# ---------- 23 ----------
def gi_23(rng): return gen_digits(rng)
def tf_23(g):
    H, W = dims(g); out = blank(H, W)
    for r in range(H):
        for c in range(W):
            v = g[r][c]
            if v and all(g[r + dr][c + dc] < v for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)) if 0 <= r + dr < H and 0 <= c + dc < W): out[r][c] = v
    return out if any(any(r) for r in out) else None
rule("strict_local_maxima_digits_kept", "Treat the cells as digits. A non-zero cell survives, in place, if it is strictly greater than each of its existing up/down/left/right neighbours; every other cell becomes 0.", gi_23, tf_23, digits=True)


# ---------- 24 ----------
def gi_24(rng): return gen_noise(rng, (2, 4), (0.1, 0.3), lo=6, hi=18)
def tf_24(g):
    H, W = dims(g); out = blank(H, W)
    for r in range(H):
        for c in range(W):
            if g[r][c] and not any(g[r + dr][c + dc] for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr or dc) and 0 <= r + dr < H and 0 <= c + dc < W): out[r][c] = g[r][c]
    return out if any(any(r) for r in out) and out != g else None
rule("isolated_cells_kept", "A coloured cell survives, in place, only if none of its eight surrounding cells is coloured; every other cell becomes 0.", gi_24, tf_24)


# ---------- 25 ----------
def gi_25(rng):
    h, w, big = _hw(rng, 7, 18); g = blank(h, w); k = rng.randint(3, 7) * (2 if big else 1); pal = colours(rng, rng.randint(2, 4))
    return _put(rng, g, [[(r, c) for r in range(rng.randint(2, 6)) for c in range(rng.randint(2, 6))] for _ in range(k)], [rng.choice(pal) for _ in range(k)]) if False else _rects(rng, g, k, pal)
def _rects(rng, g, k, pal):
    sh = []
    for _ in range(k):
        a, b = rng.randint(2, 6), rng.randint(2, 6); sh.append([(r, c) for r in range(a) for c in range(b)])
    return _put(rng, g, sh, [rng.choice(pal) for _ in sh])
def tf_25(g):
    H, W = dims(g); out = blank(H, W)
    for r in range(1, H - 1):
        for c in range(1, W - 1):
            v = g[r][c]
            if v and all(g[r + dr][c + dc] == v for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))): out[r][c] = v
    return out if any(any(r) for r in out) else None
rule("interior_cells_of_objects_kept", "A coloured cell survives, in place, only if its up, down, left and right neighbours all exist and have its own colour; every other cell (edges of objects included) becomes 0.", gi_25, tf_25)


# ---------- 26 ----------
def gi_26(rng): return gen_noise(rng, (2, 5), (0.3, 0.7))
def tf_26(g):
    seen, out = set(), blank(*dims(g))
    for r, row in enumerate(g):
        for c, v in enumerate(row):
            if v and v not in seen: seen.add(v); out[r][c] = v
    return out if len(seen) >= 2 else None
rule("first_cell_of_each_colour_kept", "For each colour, only its first cell in reading order (row by row, left to right) survives, in place; every other cell becomes 0.", gi_26, tf_26)


# ---------- 27 ----------
def gi_27(rng): return gen_noise(rng, (2, 5), (0.3, 0.7))
def tf_27(g):
    seen, out = set(), blank(*dims(g))
    for r in range(len(g) - 1, -1, -1):
        for c, v in enumerate(g[r]):
            if v and v not in seen: seen.add(v); out[r][c] = v
    return out if len(seen) >= 2 else None
rule("lowest_cell_of_each_colour_kept", "For each colour, only its lowest cell survives, in place: the cell in the bottommost row holding that colour, the leftmost such cell if several. Every other cell becomes 0.", gi_27, tf_27)


# ---------- 28 ----------
def gi_28(rng):
    h, w, _ = _hw(rng, 5, 16); k = rng.randint(2, 5); pal = colours(rng, k); g = []
    pal = pal + [pal[0]] * 0
    for _ in range(h):
        row = [0] * w
        for p in rng.sample(range(w), rng.randint(0, min(w, k + 2))): row[p] = rng.choice(pal)
        g.append(row)
    g[0][0:k] = pal if w >= k else g[0][0:k]
    return g
def tf_28(g):
    k = len({v for r in g for v in r if v}); out = [r for r in g if _nz(r) == k]
    return out if 0 < len(out) < len(g) and len({v for r in out for v in r}) > 1 else None
rule("rows_cellcount_equals_colour_count", "Let k be the number of distinct non-background colours in the whole grid. Output only the rows that contain exactly k coloured cells, in original order.", gi_28, tf_28)


# ---------- 29 ----------
def gi_29(rng): return gen_obj(rng, 2, 6, 2, 8, 2, 4, lo=8, hi=20)
def tf_29(g):
    W = len(g[0]); ne = [any(r[c] for r in g) for c in range(W)]; best = None; c = 0
    while c < W:
        if ne[c]:
            d = c
            while d < W and ne[d]: d += 1
            if best is None or d - c > best[1] - best[0]: best = (c, d)
            c = d
        else: c += 1
    if best is None or best[1] - best[0] == W: return None
    return [r[best[0]:best[1]] for r in g]
rule("widest_nonempty_column_block", "Columns containing any coloured cell form blocks separated by completely empty columns. Output the widest block of consecutive non-empty columns (tie: the leftmost), full height.", gi_29, tf_29)


# ---------- 30 ----------
def gi_30(rng):
    h, w, big = _hw(rng, 9, 18); g = blank(h, w); nb = rng.randint(2, 3); bases = [random_shape(rng, rng.randint(3, 6)) for _ in range(nb)]
    sig = lambda s: tuple(sorted(s))
    odd = random_shape(rng, rng.randint(3, 6))
    while sig(odd) in [sig(b) for b in bases]: odd = random_shape(rng, rng.randint(3, 6))
    sh = [b for b in bases for _ in range(rng.randint(2, 3 if not big else 4))] + [odd]
    rng.shuffle(sh); pal = colours(rng, rng.randint(2, 4))
    return _put(rng, g, sh, [rng.choice(pal) for _ in sh])
def tf_30(g):
    objs = _objs(g); grp = {}
    for o in objs:
        r0, c0, _, _ = bbox(o[1]); grp.setdefault(tuple(sorted((r - r0, c - c0) for r, c in o[1])), []).append(o)
    one = [v[0] for v in grp.values() if len(v) == 1]
    return _crop(g, one[0]) if len(one) == 1 else None
rule("odd_one_out_shape_crop", "Objects are compared by shape only (cells relative to the bounding box, no rotation or mirroring, colour ignored). Exactly one object has a shape no other object shares: output its crop, other cells blanked to 0.", gi_30, tf_30)


# ---------- 31 ----------
def gi_31(rng):
    h, w, big = _hw(rng, 8, 18); g = blank(h, w); pal = colours(rng, rng.randint(2, 3)); u = rng.choice([c for c in COLOURS if c not in pal])
    k = rng.randint(4, 8) * (2 if big else 1); cols = [rng.choice(pal) for _ in range(k)]
    for c in pal:
        if cols.count(c) < 2: cols[rng.randrange(k)] = c; cols[(cols.index(c) + 1) % k] = c
    cols.append(u); sh = [random_shape(rng, rng.randint(2, 8)) for _ in cols]
    return _put(rng, g, sh, cols)
def tf_31(g):
    objs = _objs(g); cnt = {}
    for c, _ in objs: cnt[c] = cnt.get(c, 0) + 1
    one = [o for o in objs if cnt[o[0]] == 1]
    return _crop(g, one[0]) if len(one) == 1 else None
rule("only_object_of_its_colour_crop", "Exactly one object has a colour that no other object has: output its crop, other cells blanked to 0.", gi_31, tf_31)


# ---------- 32 ----------
def gi_32(rng): return gen_obj(rng, 4, 9, 1, 10, 2, 4)
def tf_32(g):
    best = {}
    for i, o in enumerate(_objs(g)):
        if o[0] not in best or len(o[1]) > len(best[o[0]][1]): best[o[0]] = o
    out = _keep(g, list(best.values()))
    return out if out != g else None
rule("largest_object_per_colour_kept", "For each colour keep, in place, only its largest object (most cells; tie: first in reading order); all other objects are erased to 0.", gi_32, tf_32)


# ---------- 33 ----------
def gi_33(rng): return gen_obj(rng, 4, 9, 1, 12, 2, 5)
def tf_33(g):
    objs = _objs(g); tot = sum(len(o[1]) for o in objs); n = len(objs)
    keep = [o for o in objs if len(o[1]) * n >= tot]
    return _keep(g, keep) if 0 < len(keep) < n else None
rule("objects_at_least_mean_size_kept", "Compute the mean object size (total object cells divided by the number of objects). Keep, in place, every object whose cell count is at least that mean; all smaller objects are erased to 0.", gi_33, tf_33)


# ---------- 34 ----------
def gi_34(rng): return gen_obj(rng, 4, 9, 2, 9, 2, 5, lo=8, hi=20)
def tf_34(g):
    H, W = dims(g); objs = _objs(g)
    keep = [o for o in objs if not any(r in (0, H - 1) or c in (0, W - 1) for r, c in o[1])]
    if not keep or len(keep) == len(objs): return None
    r0, c0, r1, c1 = bbox([p for o in keep for p in o[1]])
    out = crop(_keep(g, keep), r0, c0, r1, c1)
    return out if len({v for r in out for v in r}) > 1 else None
rule("objects_off_the_border_cropped", "Keep only the objects having no cell on the grid's outer edge; output the bounding box around all kept objects together, with erased objects shown as 0.", gi_34, tf_34)
