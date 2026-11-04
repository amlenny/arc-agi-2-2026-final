# b076_legends2.py -- SUMMARY OUTPUTS, SECOND SET: the output is a small summary of the scene (legend, table,
# histogram, digit row) with mechanics not in b051/b042: orderings by object size / mean width / centroid,
# per-colour statistics of largest objects, holes, symmetry, touching, border contact, band histograms, binary
# count. An object = 4-connected same-colour component; background is 0; "reading order" = row-major from the
# top-left of an object's first cell. Rows narrower than their stated fixed width are padded with 0 on the right.
import sys, os
from fractions import Fraction
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


# ---------- helpers ----------
def _hw(rng, lo=6, hi=18, p=0.35):
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


def _cols(g):
    return sorted({v for r in g for v in r if v})


def _row9(xs):
    return [xs + [0] * (9 - len(xs))]


def _rectsh(h, w):
    return [(r, c) for r in range(h) for c in range(w)]


def _hb(o):
    r0, c0, r1, c1 = bbox(o[1])
    return r1 - r0 + 1, c1 - c0 + 1


def _touch_border(g, o):
    H, W = dims(g)
    return any(r in (0, H - 1) or c in (0, W - 1) for r, c in o[1])


def _by_col(obs):
    d = {}
    for o in obs:
        d.setdefault(o[0], []).append(o)
    return d


# generator A: repeated palette, random blobs
def gen_a(rng, klo=4, khi=9, nlo=2, nhi=9, plo=2, phi=5, p=0.35):
    h, w, big = _hw(rng, 6, 18, p)
    g = blank(h, w)
    k = rng.randint(klo, khi) * (2 if big else 1)
    pal = colours(rng, rng.randint(plo, phi))
    return _put(rng, g, [random_shape(rng, rng.randint(nlo, nhi)) for _ in range(k)], [rng.choice(pal) for _ in range(k)])


# generator B: every object its own colour
def gen_b(rng, klo=3, khi=8, nlo=2, nhi=12, p=0.35):
    h, w, big = _hw(rng, 6, 18, p)
    g = blank(h, w)
    k = rng.randint(klo, min(khi, 9))
    return _put(rng, g, [random_shape(rng, rng.randint(nlo, nhi)) for _ in range(k)], colours(rng, k))


# generator C: solid rectangles
def gen_c(rng, klo=3, khi=8, p=0.35, maxs=5):
    h, w, big = _hw(rng, 7, 18, p)
    g = blank(h, w)
    k = rng.randint(klo, khi) * (2 if big else 1)
    pal = colours(rng, rng.randint(2, 5))
    sh = [_rectsh(rng.randint(1, maxs), rng.randint(1, maxs)) for _ in range(k)]
    return _put(rng, g, sh, [rng.choice(pal) for _ in range(k)])


# generator D: horizontal and vertical bars
def gen_d(rng, klo=3, khi=8, p=0.35):
    h, w, big = _hw(rng, 7, 18, p)
    g = blank(h, w)
    k = rng.randint(klo, khi) * (2 if big else 1)
    pal = colours(rng, rng.randint(2, 5))
    sh = [_rectsh(1, rng.randint(2, 6)) if rng.random() < .5 else _rectsh(rng.randint(2, 6), 1) for _ in range(k)]
    return _put(rng, g, sh, [rng.choice(pal) for _ in range(k)])


# generator E: a few big objects plus many specks
def gen_e(rng, p=0.4, speck_hi=14):
    h, w, big = _hw(rng, 8, 18, p)
    g = blank(h, w)
    pal = colours(rng, rng.randint(2, 5))
    nb = rng.randint(1, 4); ns = rng.randint(2, speck_hi)
    if big: ns = rng.randint(6, 24)
    sh = [random_shape(rng, rng.randint(4, 10)) for _ in range(nb)] + [random_shape(rng, rng.randint(1, 2)) for _ in range(ns)]
    return _put(rng, g, sh, [rng.choice(pal) for _ in sh])


# generator G: dense, touching objects
def gen_g(rng, p=0.3):
    h, w, big = _hw(rng, 6, 12, p)
    g = blank(h, w)
    k = rng.randint(4, 9) * (3 if big else 1)
    pal = colours(rng, rng.randint(3, 5))
    return _put(rng, g, [random_shape(rng, rng.randint(3, 8)) for _ in range(k)], [rng.choice(pal) for _ in range(k)], margin=0)


# generator H: solid rectangles with punched single-cell holes
def gen_h(rng, p=0.35):
    h, w, big = _hw(rng, 8, 18, p)
    g = blank(h, w)
    k = rng.randint(2, 5) * (2 if big else 1)
    pal = colours(rng, rng.randint(2, 4))
    sh = []
    for _ in range(k):
        a, b = rng.randint(4, 7), rng.randint(4, 7)
        holes = []
        for _ in range(8):
            q = (rng.randint(1, a - 2), rng.randint(1, b - 2))
            if all(max(abs(q[0] - x), abs(q[1] - y)) >= 2 for x, y in holes) and len(holes) < rng.randint(0, 3):
                holes.append(q)
        sh.append([cc for cc in _rectsh(a, b) if cc not in holes])
    return _put(rng, g, sh, [rng.choice(pal) for _ in range(k)])


# generator I: mix of solid rectangles, left-right symmetric shapes and random shapes
def gen_i(rng, p=0.35):
    h, w, big = _hw(rng, 7, 18, p)
    g = blank(h, w)
    k = rng.randint(4, 9) * (2 if big else 1)
    pal = colours(rng, rng.randint(2, 4))
    sh = []
    for _ in range(k):
        t = rng.randint(0, 2)
        if t == 0:
            sh.append(_rectsh(rng.randint(1, 4), rng.randint(2, 4)))
        elif t == 1:
            hs = random_shape(rng, rng.randint(2, 5)); wd = max(c for _, c in hs) + 1
            sh.append(sorted(set(hs) | {(r, 2 * wd - 1 - c) for r, c in hs}))
        else:
            sh.append(random_shape(rng, rng.randint(3, 8)))
    return _put(rng, g, sh, [rng.choice(pal) for _ in range(k)])


def _enclosed(g):
    """Background regions (4-connected) that do not touch the grid edge: list of (colour_of_wall, cells)."""
    H, W = dims(g); out = []
    for comp in components(g, 0):
        if any(r in (0, H - 1) or c in (0, W - 1) for r, c in comp):
            continue
        r, c = comp[0]; wall = 0
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            if g[r + dr][c + dc]: wall = g[r + dr][c + dc]
        out.append((wall, comp))
    return out


# ---------- 1 ----------
def gi_1(rng): return gen_b(rng, 3, 8, 2, 12)
def tf_1(g):
    best = {}
    for c, cl in _objs(g): best[c] = max(best.get(c, 0), len(cl))
    if len(best) < 2: return None
    return [[c] for c in sorted(best, key=lambda c: (-best[c], c))]
rule("sz_colour_column_by_largest_object", "Output one column listing each colour present once, ordered by the cell count of that colour's largest object from largest to smallest; equal sizes put the lower colour value first.", gi_1, tf_1)


# ---------- 2 ----------
def _cls(o):
    h, w = _hb(o); n = len(o[1])
    return 1 if n == 1 else 2 if h == 1 else 3 if w == 1 else 4 if n == h * w else 5
def gi_2(rng):
    h, w, big = _hw(rng, 8, 18, 0.35); g = blank(h, w)
    cl = rng.sample([1, 2, 3, 4, 5], rng.randint(2, 5)); sh = []
    for t in cl:
        for _ in range(rng.randint(1, 3 if not big else 5)):
            if t == 1: sh.append([(0, 0)])
            elif t == 2: sh.append(_rectsh(1, rng.randint(2, 5)))
            elif t == 3: sh.append(_rectsh(rng.randint(2, 5), 1))
            elif t == 4: sh.append(_rectsh(rng.randint(2, 4), rng.randint(2, 4)))
            else:
                while True:
                    s = random_shape(rng, rng.randint(4, 8))
                    hh = max(r for r, _ in s) + 1; ww = max(c for _, c in s) + 1
                    if hh > 1 and ww > 1 and len(s) < hh * ww: break
                sh.append(s)
    pal = colours(rng, rng.randint(2, 4))
    return _put(rng, g, sh, [rng.choice(pal) for _ in sh])
def tf_2(g):
    pres = {_cls(o) for o in _objs(g)}
    return [[i if i in pres else 0 for i in range(1, 6)]]
rule("shape_class_presence_label_row", "Output one row of width 5; column i-1 holds the number i if the scene has an object of class i, else 0. Classes: 1 single cell; 2 horizontal bar (one row, 2+ cells); 3 vertical bar (one column, 2+ cells); 4 solid rectangle at least 2x2; 5 any other shape.", gi_2, tf_2, digits=True)


# ---------- 3 ----------
def gi_3(rng): return gen_a(rng, 4, 10, 2, 6, 3, 6)
def tf_3(g):
    cnt = {}
    for c, _ in _objs(g): cnt[c] = cnt.get(c, 0) + 1
    if len(cnt) < 2: return None
    return [[c, min(cnt[c], 9)] for c in sorted(cnt, key=lambda c: (-cnt[c], c))]
rule("colour_object_count_table_sorted", "Two-column table, one row per colour present: the colour, then its number of objects as a digit (cap 9). Rows run from the most objects to the fewest; equal counts put the lower colour value first.", gi_3, tf_3, digits=True)


# ---------- 4 ----------
def gi_4(rng): return gen_e(rng)
def tf_4(g):
    cnt = {}
    for c, _ in _objs(g): cnt[c] = cnt.get(c, 0) + 1
    cs = sorted(cnt)
    if len(cs) < 2: return None
    out = blank(6, len(cs))
    for j, c in enumerate(cs):
        for i in range(min(cnt[c], 6)): out[5 - i][j] = c
    return out
rule("object_count_column_histogram", "Output a grid 6 rows tall with one column per colour present, ascending left to right. Each column holds a bar of that colour rising from the bottom, as tall as the number of objects of that colour (cap 6); the rest is background.", gi_4, tf_4)


# ---------- 5 ----------
def gi_5(rng): return gen_b(rng, 5, 9, 2, 8, 0.45)
def tf_5(g):
    out = []
    for r0 in range(0, len(g), 3):
        cnt = {}
        for row in g[r0:r0 + 3]:
            for v in row:
                if v: cnt[v] = cnt.get(v, 0) + 1
        out.append([min(cnt, key=lambda c: (-cnt[c], c)) if cnt else 0])
    return out if len({r[0] for r in out}) > 1 else None
rule("band3_dominant_colour_column", "Cut the grid into horizontal bands of 3 rows starting at the top (the last band may be shorter). Output one column with one cell per band: its most frequent non-background colour (ties: lower colour value), or 0 if the band is empty.", gi_5, tf_5)


# ---------- 6 ----------
def gi_6(rng): return gen_d(rng, 4, 9)
def tf_6(g):
    obs = _objs(g); a = set(); b = set()
    for o in obs: (a if _touch_border(g, o) else b).add(o[0])
    b -= a
    if not a or not b: return None
    return _row9(sorted(a)) + _row9(sorted(b))
rule("border_touching_vs_interior_colour_rows", "Output two rows of width 9, padded with 0 on the right. Row 0 lists, ascending, the colours having at least one cell on the grid's outer edge; row 1 lists, ascending, the colours having no cell on the edge.", gi_6, tf_6)


# ---------- 7 ----------
def gi_7(rng): return gen_d(rng, 4, 10)
def tf_7(g):
    H, W = dims(g); out = blank(9, W)
    for c in range(W):
        n = min(sum(1 for r in range(H) if g[r][c]), 9)
        for i in range(n): out[8 - i][c] = 5
    return out
rule("column_occupancy_bar_chart", "Output a grid 9 rows tall and as wide as the input. Column j holds a bar of colour 5 rising from the bottom, as tall as the number of non-background cells in input column j (cap 9); the rest is background.", gi_7, tf_7)


# ---------- 8 ----------
def gi_8(rng):
    h, w, big = _hw(rng, 6, 18, 0.35); w -= w % 2; g = blank(h, w)
    pal = colours(rng, rng.randint(3, 6)); k = rng.randint(4, 9) * (2 if big else 1)
    return _put(rng, g, [random_shape(rng, rng.randint(2, 7)) for _ in range(k)], [rng.choice(pal) for _ in range(k)])
def tf_8(g):
    W = len(g[0]); L = {v for r in g for v in r[:W // 2] if v}; R = {v for r in g for v in r[W // 2:] if v}
    s = sorted(L & R)
    return _row9(s) if s and (L | R) != set(s) else None
rule("colours_in_both_halves_row", "Split the grid down the middle into a left half and a right half (the width is even). Output one row of width 9: the colours that occur in both halves, ascending, padded with 0 on the right.", gi_8, tf_8)


# ---------- 9 ----------
def _edges(g):
    H, W = dims(g); e = {}
    for r in range(H):
        for c in range(W):
            for dr, dc in ((0, 1), (1, 0)):
                if r + dr < H and c + dc < W:
                    a, b = g[r][c], g[r + dr][c + dc]
                    if a and b and a != b:
                        k = (min(a, b), max(a, b)); e[k] = e.get(k, 0) + 1
    return e
def gi_9(rng): return gen_g(rng)
def tf_9(g):
    e = _edges(g)
    if not e: return None
    m = max(e.values()); best = [k for k in e if e[k] == m]
    return [list(best[0])] if len(best) == 1 else None
rule("most_touching_colour_pair", "Count, for each pair of different non-background colours, the edge-adjacent (up/down/left/right) cell pairs where one cell has the first colour and the other the second. Output a 1x2 row with the pair of colours that has the most such adjacencies, lower colour value first.", gi_9, tf_9)


# ---------- 10 ----------
def gi_10(rng): return gen_h(rng)
def tf_10(g):
    hc = {}
    for wall, comp in _enclosed(g): hc[wall] = hc.get(wall, 0) + 1
    if not hc: return None
    m = max(hc.values()); best = [c for c in hc if hc[c] == m]
    return [[best[0], min(m, 9)]] if len(best) == 1 else None
rule("colour_with_most_holes_pair", "Count the holes (background regions fully enclosed by cells, not touching the grid edge) belonging to each colour. Output a 1x2 row: the colour with the most holes in total, then that hole count as a digit (cap 9). Inputs where two colours tie are not used.", gi_10, tf_10, digits=True)


# ---------- 11 ----------
def gi_11(rng): return gen_c(rng, 4, 9)
def tf_11(g):
    d = _by_col(_objs(g))
    if len(d) < 2: return None
    mw = {c: Fraction(sum(_hb(o)[1] for o in os_), len(os_)) for c, os_ in d.items()}
    return _row9(sorted(d, key=lambda c: (-mw[c], c)))
rule("colour_rank_by_mean_width_row", "Output one row of width 9: the colours present ordered by the mean bounding-box width of their objects, widest first; equal means put the lower colour value first; padded with 0 on the right.", gi_11, tf_11)


# ---------- 12 ----------
def gi_12(rng): return gen_a(rng, 4, 10, 2, 7, 2, 6)
def tf_12(g):
    cnt = {}
    for c, _ in _objs(g): cnt[c] = cnt.get(c, 0) + 1
    return [[min(cnt.get(i, 0), 9) for i in range(1, 10)]]
rule("object_count_digit_row_1to9", "Output one row of width 9; column i-1 holds, as a digit, the number of objects of colour i (cap 9), or 0 if colour i is absent.", gi_12, tf_12, digits=True)


# ---------- 13 ----------
def gi_13(rng):
    h, w, big = _hw(rng, 9, 18, 0.35)
    k = rng.randint(3, 6 if not big else 8); key = colours(rng, k)
    sep = rng.choice([c for c in COLOURS if c not in key])
    g = blank(h, w); g[0][:k] = key; g[1] = [sep] * w
    sub = blank(h - 2, w); n = rng.randint(k, 2 * k)
    if _put(rng, sub, [random_shape(rng, rng.randint(2, 9)) for _ in range(n)], [key[i % k] for i in range(n)]) is None: return None
    return g[:2] + sub
def tf_13(g):
    key = [v for v in g[0] if v]; cnt = counts(g[2:])
    out = sorted(key, key=lambda c: (-cnt.get(c, 0), c))
    return [out] if out != key else None
rule("key_band_resorted_by_cell_count", "Row 0 holds a key of swatches, a full separator row sits below it, and the scene follows. Output the key's colours as one row, re-ordered by that colour's total cell count in the scene below the separator, largest first; ties keep the lower colour value first.", gi_13, tf_13)


# ---------- 14 ----------
def gi_14(rng): return gen_a(rng, 4, 9, 2, 9, 2, 5)
def tf_14(g):
    d = _by_col(_objs(g))
    if len(d) < 2: return None
    out = []
    for c in sorted(d):
        o = max(d[c], key=lambda o: (len(o[1]), -d[c].index(o)))
        h, w = _hb(o); out.append([c, min(h, 9), min(w, 9)])
    return out
rule("colour_largest_object_bbox_table", "Three-column table, one row per colour present in ascending colour order: the colour, the bounding-box height, and the bounding-box width of its largest object (most cells; tie: first in reading order), each size capped at 9.", gi_14, tf_14, digits=True)


# ---------- 15 ----------
def gi_15(rng): return gen_c(rng, 4, 9, 0.35, 4)
def tf_15(g):
    d = _by_col(_objs(g))
    if len(d) < 2: return None
    return [[c, min(len({len(o[1]) for o in d[c]}), 9)] for c in sorted(d)]
rule("colour_distinct_size_count_table", "Two-column table, one row per colour present in ascending order: the colour, then the number of different object sizes (cell counts) among that colour's objects, as a digit (cap 9).", gi_15, tf_15, digits=True)


# ---------- 16 ----------
def gi_16(rng): return gen_g(rng)
def tf_16(g):
    cs = _cols(g); deg = {c: 0 for c in cs}
    for a, b in _edges(g): deg[a] += 1; deg[b] += 1
    if len(cs) < 2 or not any(deg.values()): return None
    return [[c, deg[c]] for c in cs]
rule("colour_touch_degree_table", "Two-column table, one row per colour present in ascending order: the colour, then the number of other colours it shares at least one edge (up/down/left/right) with, as a digit.", gi_16, tf_16, digits=True)


# ---------- 17 ----------
def gi_17(rng): return gen_h(rng)
def tf_17(g):
    cs = _cols(g); hc = {c: 0 for c in cs}
    for wall, _ in _enclosed(g): hc[wall] += 1
    if len(cs) < 2 or not any(hc.values()): return None
    return [[c, min(hc[c], 9)] for c in cs]
rule("colour_hole_count_table", "Two-column table, one row per colour present in ascending order: the colour, then the number of holes (background regions fully enclosed, not touching the grid edge) in that colour's objects, as a digit (cap 9; 0 allowed).", gi_17, tf_17, digits=True)


# ---------- 18 ----------
def gi_18(rng): return gen_a(rng, 4, 9, 2, 8, 3, 6)
def tf_18(g):
    sx = {}; n = {}
    for r, row in enumerate(g):
        for c, v in enumerate(row):
            if v: sx[v] = sx.get(v, 0) + c; n[v] = n.get(v, 0) + 1
    if len(n) < 2: return None
    return _row9(sorted(n, key=lambda v: (Fraction(sx[v], n[v]), v)))
rule("colour_order_by_mean_column_row", "Output one row of width 9: the colours present ordered by the mean column index of all their cells, smallest (leftmost) first; equal means put the lower colour value first; padded with 0 on the right.", gi_18, tf_18)


# ---------- 19 ----------
def gi_19(rng): return gen_b(rng, 3, 8, 2, 12)
def tf_19(g):
    cs = _cols(g)
    if len(cs) < 2: return None
    out = []
    for c in cs:
        r0, c0, r1, c1 = bbox(cells(g, lambda v: v == c))
        out.append([c, min(r1 - r0 + 1, 9), min(c1 - c0 + 1, 9)])
    return out
rule("colour_union_bbox_size_table", "Three-column table, one row per colour present in ascending order: the colour, then the height and the width of the bounding box around ALL cells of that colour, each capped at 9.", gi_19, tf_19, digits=True)


# ---------- 20 ----------
def gi_20(rng): return gen_a(rng, 5, 10, 2, 6, 3, 6)
def tf_20(g):
    cnt = {}
    for c, _ in _objs(g): cnt[c] = cnt.get(c, 0) + 1
    hi = min(cnt, key=lambda c: (-cnt[c], c)); lo = min(cnt, key=lambda c: (cnt[c], c))
    return [[hi, lo]] if hi != lo else None
rule("most_and_fewest_objects_colour_pair", "Output a 1x2 row: the colour having the most objects, then the colour having the fewest objects (ties for either: lower colour value). Inputs where both are the same colour are not used.", gi_20, tf_20)


# ---------- 21 ----------
def gi_21(rng): return gen_c(rng, 4, 9, 0.35, 5)
def tf_21(g):
    d = _by_col(_objs(g))
    if len(d) < 3: return None
    cells_ = {c: sum(len(o[1]) for o in d[c]) for c in d}
    top = sorted(d, key=lambda c: (-cells_[c], c))[:3]
    return [[c, min(len(d[c]), 9)] for c in top]
rule("top3_colours_by_cells_with_object_count", "Output a 3-row, 2-column table: the three colours with the most cells in total (ties: lower colour value first), largest first, each followed by its number of objects as a digit (cap 9).", gi_21, tf_21, digits=True)


# ---------- 22 ----------
def gi_22(rng): return gen_b(rng, 3, 8, 1, 12)
def tf_22(g):
    out = []
    d = _by_col(_objs(g))
    if len(d) < 2: return None
    for c in sorted(d):
        n = max(len(o[1]) for o in d[c]); out.append([c, 1 if n <= 3 else 2 if n <= 6 else 3])
    return out if len({r[1] for r in out}) > 1 else None
rule("colour_size_class_table", "Two-column table, one row per colour present in ascending order: the colour, then a class digit from its largest object's cell count: 1 for 1-3 cells, 2 for 4-6 cells, 3 for 7 or more.", gi_22, tf_22, digits=True)


# ---------- 23 ----------
def gi_23(rng): return gen_a(rng, 4, 10, 2, 7, 2, 5)
def tf_23(g):
    H = len(g); b = H // 3; cnt = [0, 0, 0]
    for c, cl in _objs(g): cnt[min(cl[0][0] // b, 2)] += 1
    return [[5] * min(n, 9) + [0] * (9 - min(n, 9)) for n in cnt]
rule("object_count_thirds_bar_rows", "Cut the grid into three horizontal thirds: rows 0..h//3-1, then h//3..2*(h//3)-1, then the rest. Output 3 rows of width 9, one per third top to bottom: a bar of colour 5 as long as the number of objects whose first cell in reading order lies in that third (cap 9), padded with 0 on the right.", gi_23, tf_23)


# ---------- 24 ----------
def gi_24(rng): return gen_a(rng, 4, 9, 2, 9, 2, 5)
def tf_24(g):
    d = _by_col(_objs(g))
    if len(d) < 2: return None
    cl = {c: sum(len(o[1]) for o in d[c]) for c in d}; out = []
    for c in sorted(d, key=lambda c: (-cl[c], c)): out += [c, min(len(d[c]), 9)]
    return [out]
rule("interleaved_colour_objcount_row", "Output one row of pairs: each colour present followed by its object count as a digit (cap 9), the pairs ordered by the colour's total cell count, largest first, ties lower colour value first.", gi_24, tf_24, digits=True)


# ---------- 25 ----------
def gi_25(rng): return gen_e(rng, 0.4, 25)
def tf_25(g):
    n = len(_objs(g))
    if not 1 <= n <= 30: return None
    return [[8 if (n >> i) & 1 else 0 for i in range(4, -1, -1)]]
rule("object_count_binary_row", "Count all objects (4-connected same-colour components). Output a row of 5 cells holding that count in binary, most significant bit on the left: colour 8 for a 1 bit, 0 for a 0 bit.", gi_25, tf_25)


# ---------- 26 ----------
def gi_26(rng): return gen_b(rng, 3, 9, 2, 10)
def tf_26(g):
    cnt = counts(g); cnt.pop(0, None)
    if len(cnt) < 2: return None
    order = sorted(cnt, key=lambda c: (-cnt[c], c))
    return [[order.index(i) + 1 if i in cnt else 0 for i in range(1, 10)]]
rule("colour_cellcount_rank_digit_row", "Output one row of width 9; column i-1 holds the rank of colour i by total cell count as a digit (1 = most cells; ties: lower colour value ranks first), or 0 if colour i is absent.", gi_26, tf_26, digits=True)


# ---------- 27 ----------
def gi_27(rng): return gen_a(rng, 5, 10, 2, 7, 3, 6, 0.4)
def tf_27(g):
    d = _by_col(_objs(g))
    if len(d) < 2: return None
    out = []
    for c in sorted(d):
        a = sum(1 for o in d[c] if _touch_border(g, o)); out.append([c, min(a, 9), min(len(d[c]) - a, 9)])
    return out
rule("colour_border_interior_object_table", "Three-column table, one row per colour present in ascending order: the colour, the number of its objects having a cell on the grid's outer edge, then the number having none, both as digits (cap 9).", gi_27, tf_27, digits=True)


# ---------- 28 ----------
def gi_28(rng): return gen_i(rng)
def _sym(o):
    r0, c0, r1, c1 = bbox(o[1]); s = {(r - r0, c - c0) for r, c in o[1]}; w = c1 - c0
    return s == {(r, w - c) for r, c in s}
def tf_28(g):
    d = _by_col(_objs(g))
    if len(d) < 2: return None
    out = [[c, min(sum(1 for o in d[c] if _sym(o)), 9)] for c in sorted(d)]
    return out if len({r[1] for r in out}) > 1 else None
rule("colour_mirror_symmetric_count_table", "Two-column table, one row per colour present in ascending order: the colour, then how many of its objects are left-right mirror symmetric (the object equals its own horizontal mirror image inside its bounding box), as a digit (cap 9, 0 allowed).", gi_28, tf_28, digits=True)


# ---------- 29 ----------
def gi_29(rng): return gen_i(rng)
def tf_29(g):
    d = _by_col(_objs(g))
    if len(d) < 2: return None
    out = []
    for c in sorted(d):
        a = sum(1 for o in d[c] if len(o[1]) == _hb(o)[0] * _hb(o)[1]); out.append([c, min(a, 9), min(len(d[c]) - a, 9)])
    return out
rule("colour_rectangle_vs_other_count_table", "Three-column table, one row per colour present in ascending order: the colour, the number of its objects that are solid rectangles (every cell of the bounding box filled; single cells and bars count), then the number of its other objects, both as digits (cap 9).", gi_29, tf_29, digits=True)


# ---------- 30 ----------
def gi_30(rng): return gen_c(rng, 5, 10, 0.35, 5)
def tf_30(g):
    n = [0, 0, 0]
    for o in _objs(g):
        h, w = _hb(o); n[0 if h > w else 1 if w > h else 2] += 1
    return [[1, min(n[0], 9)], [2, min(n[1], 9)], [3, min(n[2], 9)]]
rule("tall_wide_square_count_table", "Output a 3-row, 2-column table. Column 0 holds the labels 1, 2, 3 top to bottom; column 1 holds the number of objects whose bounding box is taller than wide (label 1), wider than tall (label 2), or square (label 3), as digits (cap 9).", gi_30, tf_30, digits=True)


# ---------- 31 ----------
def gi_31(rng): return gen_e(rng, 0.4, 10)
def tf_31(g):
    obs = _objs(g)
    if not 2 <= len(obs) <= 24: return None
    obs = sorted(enumerate(obs), key=lambda x: (-len(x[1][1]), x[0]))
    return [[o[0]] * min(len(o[1]), 9) + [0] * (9 - min(len(o[1]), 9)) for _, o in obs]
rule("objects_sorted_by_size_bar_rows", "One row of width 9 per object: a bar in the object's colour as long as its cell count (cap 9), padded with 0 on the right. Rows are ordered by object size, largest first; equal sizes keep reading order of their first cells.", gi_31, tf_31)


# ---------- 32 ----------
def gi_32(rng): return gen_e(rng, 0.4, 12)
def tf_32(g):
    sz = {}
    for _, cl in _objs(g): sz[len(cl)] = sz.get(len(cl), 0) + 1
    s = min(sz, key=lambda k: (-sz[k], k)); a, b = min(s, 9), min(sz[s], 9)
    return [[a, b]] if a != b else None
rule("modal_object_size_pair", "Output a 1x2 row: the most common object size (cell count; ties: the smaller size) as a digit capped at 9, then how many objects have that size as a digit capped at 9. Inputs where the two digits are equal are not used.", gi_32, tf_32, digits=True)


# ---------- 33 ----------
def gi_33(rng): return gen_c(rng, 5, 10, 0.35, 4)
def tf_33(g):
    s = sorted(len(cl) for _, cl in _objs(g))
    if len(s) < 3: return None
    out = [min(s[0], 9), min(s[(len(s) - 1) // 2], 9), min(s[-1], 9)]
    return [out] if len(set(out)) > 1 else None
rule("object_size_min_median_max_row", "List all object sizes (cell counts) in ascending order. Output a 1x3 row of digits capped at 9: the smallest, the median (the element at index (n-1)//2 of the sorted list), and the largest.", gi_33, tf_33, digits=True)


# ---------- 34 ----------
def gi_34(rng): return gen_b(rng, 3, 8, 1, 12)
def tf_34(g):
    obs = _objs(g); big = max(obs, key=lambda o: (len(o[1]), -obs.index(o))); sm = min(obs, key=lambda o: (len(o[1]), obs.index(o)))
    return [[big[0]], [sm[0]]] if big[0] != sm[0] else None
rule("largest_smallest_object_colour_column", "Output a 2x1 column: the colour of the largest object (most cells; tie: first in reading order of first cells) on top, the colour of the smallest object (fewest cells; tie: first in reading order) below.", gi_34, tf_34)


# ---------- 35 ----------
def gi_35(rng): return gen_a(rng, 6, 9, 4, 9, 2, 5, 0.4)
def tf_35(g):
    er = sum(1 for r in g if not any(r)); ec = sum(1 for c in zip(*g) if not any(c))
    a, b = min(er, 9), min(ec, 9)
    return [[a, b]] if a != b else None
rule("empty_rows_columns_pair", "Output a 1x2 row of digits: the number of completely empty rows, then the number of completely empty columns, each capped at 9. Inputs where the two digits are equal are not used.", gi_35, tf_35, digits=True)


# ---------- 36 ----------
def gi_36(rng): return gen_h(rng)
def tf_36(g):
    a, b = min(len(_objs(g)), 9), min(len(_enclosed(g)), 9)
    return [[a, b]] if a != b else None
rule("objects_and_holes_pair", "Output a 1x2 row of digits: the number of objects, then the number of holes (background regions fully enclosed, not touching the grid edge), each capped at 9. Inputs where the two digits are equal are not used.", gi_36, tf_36, digits=True)


# ---------- 37 ----------
def gi_37(rng): return gen_b(rng, 3, 9, 2, 10)
def tf_37(g):
    top = {}
    for r, row in enumerate(g):
        for v in row:
            if v and v not in top: top[v] = r
    if len(top) < 2: return None
    return [[c] for c in sorted(top, key=lambda c: (top[c], c))]
rule("colour_order_by_topmost_row_column", "Output one column listing each colour present once, ordered by the highest row (smallest row index) holding any of its cells, topmost first; equal rows put the lower colour value first.", gi_37, tf_37)
