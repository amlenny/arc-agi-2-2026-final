# b085_overlays2.py -- LAYER COMBINATION WITH A KEY, SECOND SET. Layout (unless a rule says otherwise): row 0 is a
# key row (cells left to right, padded with 0), row 1 is a full separator row of one colour S, then the panels
# side by side, equal size, joined by one-cell columns of S. S never appears inside a panel. 0 is empty/clear.
# "A over B" means: A's cell where A is non-zero, else B's cell. Panels are numbered 1, 2, 3 from the left.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


# ---------- scaffold ----------
def _pd(rng, k, lo=4, hi=12, p=0.35, hcap=30):
    if rng.random() < p: H, W = rng.randint(21, 30), rng.randint(21, 30)
    else: H, W = rng.randint(lo + 2, hi + 2), rng.randint(lo + 3, hi + 6)
    return max(3, min(H - 2, hcap)), max(3, (W - (k - 1)) // k)


def _noise(rng, ph, pw, cols, dens):
    d = rng.uniform(*dens)
    return [[rng.choice(cols) if rng.random() < d else 0 for _ in range(pw)] for _ in range(ph)]


def _blob(rng, ph, pw, cols, dens):
    g = blank(ph, pw); n = rng.randint(1, 3)
    if place_shapes(rng, g, [random_shape(rng, rng.randint(2, max(3, ph * pw // 8))) for _ in range(n)], [rng.choice(cols) for _ in range(n)], margin=1) is None:
        return _noise(rng, ph, pw, cols, dens)
    return g


def _join(panels, sep):
    return [sum(([sep] * (i > 0) + p[r] for i, p in enumerate(panels)), []) for r in range(len(panels[0]))]


def _asm(legend, sep, panels):
    body = _join(panels, sep); W = len(body[0])
    return [(list(legend) + [0] * W)[:W], [sep] * W] + body


def _parse(g):
    sep = g[1][0]; body = g[2:]; w = len(body[0]); panels, start = [], 0
    for c in [c for c in range(w) if all(r[c] == sep for r in body)] + [w]:
        if c > start: panels.append([row[start:c] for row in body])
        start = c + 1
    return g[0], sep, panels


def build(rng, k, leg=None, ncol=3, kind=_noise, dens=(0.3, 0.6), excl=(), hcap=30, lo=4, hi=12, p=0.35, sq=False):
    ph, pw = _pd(rng, k, lo, hi, p, hcap)
    if sq: ph = pw = min(ph, pw)
    sep = rng.choice([c for c in COLOURS if c not in excl])
    cols = colours(rng, ncol, exclude=(0, sep) + tuple(excl))
    panels = [kind(rng, ph, pw, cols, dens) for _ in range(k)]
    W = k * pw + k - 1
    return _asm(leg(rng, cols, sep, W) if leg else [0] * W, sep, panels)


def _over(a, b): return a if a else b


def _st(g):
    leg, sep, ps = _parse(g)
    return leg, ps


def _map(ps, f):
    return [[f(*[p[r][c] for p in ps]) for c in range(len(ps[0][0]))] for r in range(len(ps[0]))]


def _ok(out):
    return out if len({v for r in out for v in r}) > 1 else None


def lg_perm(rng, cols, sep, W):
    c = cols[:]; rng.shuffle(c); return c


# ---------- 1 ----------
def gi_1(rng): return build(rng, 2, lg_perm, ncol=3, kind=_noise, dens=(0.4, 0.8))
def tf_1(g):
    leg, (a, b) = _st(g); rk = {c: i for i, c in enumerate(x for x in leg if x)}
    return _ok(_map([a, b], lambda x, y: x if not y else y if not x else (x if rk.get(x, 99) <= rk.get(y, 99) else y)))
rule("two_panels_colour_priority_from_key", "The key row lists colours from highest to lowest priority. Two panels are overlaid: where both are non-zero the cell takes whichever of the two colours is earlier in the key; where only one is non-zero it shows through.", gi_1, tf_1)


# ---------- 2 ----------
def gi_2(rng): return build(rng, 3, lg_perm, ncol=3, kind=_blob, dens=(0.5, 0.8))
def tf_2(g):
    leg, ps = _st(g); rk = {c: i for i, c in enumerate(x for x in leg if x)}
    def f(*v):
        cnt = {}
        for x in v:
            if x: cnt[x] = cnt.get(x, 0) + 1
        return min(cnt, key=lambda c: (-cnt[c], rk.get(c, 99))) if cnt else 0
    return _ok(_map(ps, f))
rule("three_panel_vote_ties_by_key_order", "Three panels vote cell by cell, empty cells not voting: the colour with the most votes wins; if colours tie, the one listed earlier in the key row wins. A cell nobody colours stays 0.", gi_2, tf_2)


# ---------- 3 ----------
def gi_3(rng):
    g = build(rng, 3, None, ncol=3, kind=_blob, excl=(5,)); leg, sep, ps = _parse(g)
    ps[2] = [[5 if rng.random() < 0.4 else 0 for _ in r] for r in ps[2]]
    return _asm(leg, sep, ps)
def tf_3(g):
    leg, (a, b, m) = _st(g)
    return _ok(_map([a, b, m], lambda x, y, z: _over(y, x) if z == 5 else _over(x, y)))
rule("a_over_b_except_under_grey_mask", "Panel 3 is a mask drawn in grey (5). Panels 1 (A) and 2 (B) are overlaid with A over B, except where the mask is grey: there B goes over A. The mask itself is not drawn.", gi_3, tf_3)


# ---------- 4 ----------
def lg_quad(rng, cols, sep, W): return [rng.choice([1, 2]) for _ in range(4)]
def gi_4(rng): return build(rng, 2, lg_quad, ncol=3, kind=_blob, dens=(0.5, 0.8), lo=6, hi=14)
def tf_4(g):
    leg, (a, b) = _st(g); H, W = len(a), len(a[0]); out = blank(H, W)
    for r in range(H):
        for c in range(W):
            q = (r >= H // 2) * 2 + (c >= W // 2); t = (a, b) if leg[q] == 1 else (b, a)
            out[r][c] = _over(t[0][r][c], t[1][r][c])
    return _ok(out)
rule("quadrant_top_panel_from_key", "The first four key cells (each 1 or 2) say which panel lies on top in the top-left, top-right, bottom-left and bottom-right quadrants (rows split at h//2, columns at w//2). In each quadrant the top panel's non-zero cells win; the other panel shows through elsewhere.", gi_4, tf_4, digits=True)


# ---------- 5 ----------
def lg_one(rng, cols, sep, W): return [rng.choice([c for c in COLOURS if c not in cols and c != sep])]
def gi_5(rng): return build(rng, 2, lg_one, ncol=3, kind=_noise, dens=(0.3, 0.6))
def tf_5(g):
    leg, (a, b) = _st(g); return _ok(_map([a, b], lambda x, y: leg[0] if bool(x) != bool(y) else 0))
rule("xor_of_two_panels_in_key_colour", "Two panels are compared cell by cell: a cell that is non-zero in exactly one panel is painted with the key colour (first key cell); every other cell is 0.", gi_5, tf_5)


# ---------- 6 ----------
def lg_k(rng, cols, sep, W): return [rng.randint(1, 3)]
def gi_6(rng): return build(rng, 4, lg_k, ncol=3, excl=(8,), dens=(0.3, 0.6), lo=4, hi=10)
def tf_6(g):
    leg, ps = _st(g); k = leg[0]
    return _ok(_map(ps, lambda *v: 8 if sum(1 for x in v if x) == k else 0))
rule("exactly_k_of_four_panels_set_digit", "The first key cell is a digit k (1 to 3). Four panels are overlaid; every cell that is non-zero in exactly k of the four panels is painted 8, every other cell is 0.", gi_6, tf_6, digits=True)


# ---------- 7 ----------
def gi_7(rng): return build(rng, 2, None, ncol=5, dens=(0.4, 0.8), hcap=14)
def tf_7(g):
    leg, (a, b) = _st(g)
    lo = _map([a, b], lambda x, y: min(x, y) if x and y else x or y)
    hi = _map([a, b], lambda x, y: max(x, y))
    return _ok(lo + hi)
rule("min_then_max_of_two_digit_panels", "Two panels of digits are combined cell by cell, a 0 meaning no value. Output two stacked halves: the top half holds, per cell, the smaller of the two values (the single value if only one is non-zero), the bottom half the larger.", gi_7, tf_7, digits=True)


# ---------- 8 ----------
def lg_pairs(rng, cols, sep, W):
    n = rng.randint(1, min(3, len(cols))); src = rng.sample(cols, n); out = []
    for s in src: out += [s, rng.choice([c for c in COLOURS if c not in (s, sep)])]
    return out
def gi_8(rng): return build(rng, 2, lg_pairs, ncol=3, kind=_blob, dens=(0.5, 0.8))
def tf_8(g):
    leg, (a, b) = _st(g); d = {leg[i]: leg[i + 1] for i in range(0, len(leg) - 1, 2) if leg[i]}
    return _ok(_map([a, b], lambda x, y: d.get(y, y) if y else x))
rule("remap_b_by_key_pairs_then_over_a", "The key row holds (from, to) colour pairs. Panel 2 (B) has each listed colour replaced by its partner (unlisted colours stay); then B is laid over panel 1 (A): B's non-zero cells win, A shows through elsewhere.", gi_8, tf_8)


# ---------- 9 ----------
def gi_9(rng): return build(rng, 3, None, ncol=3, kind=_noise, dens=(0.15, 0.7))
def tf_9(g):
    leg, ps = _st(g); n = [sum(1 for r in p for v in r if v) for p in ps]
    order = sorted(range(3), key=lambda i: (-n[i], i))
    return _ok(_map([ps[i] for i in order], lambda *v: next((x for x in v if x), 0)))
rule("panel_with_most_cells_on_top", "Three panels are stacked in order of their number of non-zero cells: the panel with the most cells is on top, then the next; equal counts put the left panel higher. At each cell the highest panel's non-zero colour shows; else 0.", gi_9, tf_9)


# ---------- 12 ----------
def gi_12(rng):
    ph, pw = _pd(rng, 3, 4, 10); pw = min(pw, 8)
    sep = rng.choice(COLOURS); cols = colours(rng, 3, exclude=(0, sep))
    ps = [_noise(rng, ph, pw, cols, (0.4, 0.8)) for _ in range(3)]
    key = [rng.randint(1, 3) for _ in range(ph)]
    body = _join(ps, sep)
    return [[key[r], sep] + body[r] for r in range(ph)]
def tf_12(g):
    sep = g[0][1]; body = [r[2:] for r in g]; w = len(body[0])
    cuts = [c for c in range(w) if all(r[c] == sep for r in body)]; pw = (w - len(cuts)) // (len(cuts) + 1)
    out = []
    for r, row in enumerate(g):
        k = row[0] - 1; out.append(body[r][k * (pw + 1):k * (pw + 1) + pw])
    return _ok(out)
rule("each_row_takes_panel_named_in_key_column", "Column 0 holds a digit 1-3 per row, column 1 is a separator column; the three panels follow, joined by separator columns. Output row r is row r of the panel whose number the key column gives for that row.", gi_12, tf_12, digits=True)


# ---------- 12b ----------
def lg_colkey(rng, cols, sep, W): return [rng.randint(1, 3) for _ in range(W)]
def gi_12b(rng): return build(rng, 3, lg_colkey, ncol=3, dens=(0.4, 0.8), hi=10)
def tf_12b(g):
    leg, ps = _st(g); pw = len(ps[0][0])
    return _ok([[ps[leg[c] - 1][r][c] for c in range(pw)] for r in range(len(ps[0]))])
rule("each_column_takes_panel_named_in_key_row", "The first w key cells (w = panel width) are digits 1-3. Three panels follow; output column c is column c of the panel whose number the key gives for that column.", gi_12b, tf_12b, digits=True)


# ---------- 13 ----------
def gi_13(rng):
    ph, pw = _pd(rng, 3, 7, 12); pw = max(pw, 5); sep = rng.choice(COLOURS); bs = colours(rng, 3, exclude=(0, sep)); ps = []
    for b in bs:
        h, w = rng.randint(3, ph), rng.randint(3, pw); r0, c0 = rng.randint(0, ph - h), rng.randint(0, pw - w)
        f = rng.choice([x for x in COLOURS if x not in (b, sep)] + [0, 0]); p = blank(ph, pw)
        rect(p, r0, c0, r0 + h - 1, c0 + w - 1, f); rect(p, r0, c0, r0 + h - 1, c0 + w - 1, b, fill=False); ps.append(p)
    return _asm([], sep, ps)
def tf_13(g):
    leg, ps = _st(g)
    bc = [next(v for r in p for v in r if v) for p in ps]
    order = sorted(range(3), key=lambda i: -bc[i])
    return _ok(_map([ps[i] for i in order], lambda *v: next((x for x in v if x), 0)))
rule("stack_layers_by_border_colour_value", "Each panel holds one rectangle with a one-cell border (its first non-zero cell in reading order is a border cell). The panels are stacked as layers: the panel whose border colour value is highest lies on top, the lowest at the bottom. Each cell shows the top layer's non-zero colour; else 0.", gi_13, tf_13, digits=True)


# ---------- 19 ----------
def lg_d24(rng, cols, sep, W): return [rng.randint(2, 4)]
def gi_19(rng): return build(rng, 2, lg_d24, ncol=3, dens=(0.5, 0.9), kind=_noise)
def tf_19(g):
    leg, (a, b) = _st(g); d = leg[0]
    return _ok([[b[r][c] if c % d == 0 else a[r][c] for c in range(len(a[0]))] for r in range(len(a))])
rule("columns_from_b_at_multiples_of_key_digit", "The first key cell is a digit d (2-4). Output panel 1 (A) with every column whose index (counted from 0) is a multiple of d replaced by the same column of panel 2 (B).", gi_19, tf_19, digits=True)


# ---------- 20 ----------
def gi_20(rng):
    g = build(rng, 2, None, ncol=3, dens=(0.5, 0.9), kind=_noise); leg, sep, ps = _parse(g)
    leg[0] = rng.randint(1, min(9, len(ps[0]) - 1)); return _asm(leg, sep, ps)
def tf_20(g):
    leg, (a, b) = _st(g); s = leg[0]; return _ok(a[:s] + b[s:])
rule("rows_above_seam_from_a_below_from_b", "The first key cell is a digit s. Output the first s rows of panel 1 (A) followed by the remaining rows of panel 2 (B), from row s down.", gi_20, tf_20, digits=True)


# ---------- 21 ----------
def lg_12(rng, cols, sep, W): return [rng.randint(1, 2)]
def gi_21(rng): return build(rng, 2, lg_12, ncol=3, dens=(0.6, 0.95), sq=True, hi=11)
def tf_21(g):
    leg, (a, b) = _st(g); u, v = (a, b) if leg[0] == 1 else (b, a); n = len(a)
    return _ok([[u[r][c] if c > r else v[r][c] for c in range(n)] for r in range(n)])
rule("diagonal_split_panel_above_from_key", "The panels are square. The first key cell (1 or 2) names the panel used for cells strictly above the main diagonal (column > row); the other panel supplies the diagonal and everything below it.", gi_21, tf_21, digits=True)


# ---------- 22 ----------
def lg_cap(rng, cols, sep, W): return [rng.randint(5, 9)]
def gi_22(rng): return build(rng, 2, lg_cap, ncol=4, dens=(0.3, 0.7))
def tf_22(g):
    leg, (a, b) = _st(g); return _ok(_map([a, b], lambda x, y: min(x + y, leg[0])))
rule("sum_of_two_digit_panels_capped_by_key", "Add the two panels cell by cell as digits and cap each sum at the first key cell's digit (a digit 5-9).", gi_22, tf_22, digits=True)


# ---------- 23 ----------
def lg_t(rng, cols, sep, W): return [rng.randint(2, 5)]
def gi_23(rng): return build(rng, 2, lg_t, ncol=5, dens=(0.6, 1.0))
def tf_23(g):
    leg, (a, b) = _st(g); t = leg[0]; return _ok(_map([a, b], lambda x, y: abs(x - y) if abs(x - y) >= t else 0))
rule("abs_difference_at_least_key_threshold", "For each cell take the absolute difference of the two panels' digits; keep it as a digit if it is at least the first key cell's digit, otherwise the cell becomes 0.", gi_23, tf_23, digits=True)


# ---------- 24 ----------
def gi_24(rng): return build(rng, 2, lg_one, ncol=2, dens=(0.5, 0.9), kind=_noise)
def tf_24(g):
    leg, (a, b) = _st(g); return _ok(_map([a, b], lambda x, y: leg[0] if x and x == y else _over(x, y)))
rule("agreement_painted_key_colour_else_a_over_b", "Two panels are overlaid: where both hold the same non-zero colour the cell is painted with the key colour (first key cell); everywhere else panel 1 goes over panel 2.", gi_24, tf_24)


# ---------- 25 ----------
def lg_ord(rng, cols, sep, W):
    o = [1, 2, 3]; rng.shuffle(o); return o
def gi_25(rng): return build(rng, 3, lg_ord, ncol=3, dens=(0.3, 0.6), kind=_blob)
def tf_25(g):
    leg, ps = _st(g); out = blank(len(ps[0]), len(ps[0][0]))
    for k in leg[:3]:
        out = _map([ps[k - 1], out], lambda x, y: x or y)
    return _ok(out)
rule("paint_panels_in_key_order", "The first three key cells are a permutation of 1, 2, 3: the order in which the panels are painted onto an empty canvas, the first named painted first. Each later panel overwrites earlier cells wherever it is non-zero.", gi_25, tf_25, digits=True)


# ---------- 26 ----------
def gi_26(rng): return build(rng, 3, None, ncol=3, dens=(0.3, 0.7))
def tf_26(g):
    leg, ps = _st(g)
    return _ok(_map(ps, lambda *v: (lambda n: v[n - 1] if n else 0)(sum(1 for x in v if x))))
rule("cell_shows_panel_numbered_by_overlap_count", "Count how many of the three panels are non-zero at a cell. If the count is 0 the cell is 0; otherwise the cell shows the colour that panel number (count) has there (counting panels 1, 2, 3 from the left; it may be 0).", gi_26, tf_26)


# ---------- 27 ----------
def gi_27(rng): return build(rng, 2, lg_one, ncol=5, dens=(0.5, 0.9))
def tf_27(g):
    leg, (a, b) = _st(g); return _ok(_map([a, b], lambda x, y: leg[0] if x > y else 0))
rule("mark_cells_where_panel_one_digit_exceeds_two", "Compare the panels as digits cell by cell; a cell where panel 1's digit is strictly greater than panel 2's is painted with the key colour (first key cell), every other cell is 0.", gi_27, tf_27, digits=True)


# ---------- 30 ----------
def lg_vis(rng, cols, sep, W):
    while True:
        v = [rng.choice([1, 2]) for _ in range(3)]
        if v.count(1) >= 2: return v
def gi_30(rng): return build(rng, 3, lg_vis, ncol=3, dens=(0.3, 0.6), kind=_blob)
def tf_30(g):
    leg, ps = _st(g); vis = [ps[i] for i in range(3) if leg[i] == 1]
    return _ok(_map(vis, lambda *v: next((x for x in v if x), 0)))
rule("visible_layers_from_key_flags", "The first three key cells are flags for panels 1-3: 1 means visible, 2 means hidden. The visible panels are stacked with the leftmost visible panel on top; each cell shows the top-most non-zero colour among them, else 0.", gi_30, tf_30, digits=True)


# ---------- 33 ----------
def gi_33(rng):
    ph, pw = _pd(rng, 3, 6, 12); pw = max(pw, 5); sep = rng.choice(COLOURS); cs = colours(rng, 3, exclude=(0, sep)); ps = []
    for c in cs:
        h, w = rng.randint(2, ph), rng.randint(2, pw); r0, c0 = rng.randint(0, ph - h), rng.randint(0, pw - w)
        p = blank(ph, pw); rect(p, r0, c0, r0 + h - 1, c0 + w - 1, c); ps.append(p)
    return _asm([], sep, ps)
def tf_33(g):
    leg, ps = _st(g); n = [sum(1 for r in p for v in r if v) for p in ps]
    order = sorted(range(3), key=lambda i: (-n[i], i)); out = blank(len(ps[0]), len(ps[0][0]))
    for i in order: out = _map([ps[i], out], lambda x, y: x or y)
    return _ok(out)
rule("smaller_rectangles_painted_on_top", "Each of the three panels holds one solid rectangle. They are painted onto an empty canvas from the largest rectangle (most cells) to the smallest, so smaller ones end on top; equal sizes are painted left panel first.", gi_33, tf_33)


# ---------- 35 ----------
def lg_pq(rng, cols, sep, W): return rng.sample(cols, 2)
def gi_35(rng): return build(rng, 2, lg_pq, ncol=3, kind=_blob, dens=(0.5, 0.8))
def tf_35(g):
    leg, (a, b) = _st(g); p, q = leg[0], leg[1]; sw = lambda x: q if x == p else p if x == q else x
    return _ok(_map([a, b], lambda x, y: _over(sw(x), sw(y))))
rule("swap_two_key_colours_then_a_over_b", "The first two key cells are colours p and q. In both panels every p becomes q and every q becomes p; then panel 1 (A) is laid over panel 2 (B).", gi_35, tf_35)


# ---------- 37 ----------
def lg_w(rng, cols, sep, W): return [rng.randint(1, 3) for _ in range(3)]
def gi_37(rng): return build(rng, 3, lg_w, ncol=4, dens=(0.5, 0.9))
def tf_37(g):
    leg, ps = _st(g)
    def f(*v):
        s = {}
        for w, x in zip(leg, v):
            if x: s[x] = s.get(x, 0) + w
        return min(s, key=lambda c: (-s[c], c)) if s else 0
    return _ok(_map(ps, f))
rule("weighted_vote_with_key_weights", "The first three key cells are weights (1-3) for panels 1, 2, 3. At each cell every non-zero panel adds its weight to its colour; the colour with the largest total wins (tie: lower colour value). A cell nobody colours stays 0.", gi_37, tf_37, digits=True)


# ---------- 38 ----------
def gi_38(rng):
    g = build(rng, 2, None, ncol=3, kind=_noise, dens=(0.5, 0.9)); leg, sep, ps = _parse(g)
    leg[0] = ps[0][0][0] or max(max(r) for r in ps[0]); return _asm(leg, sep, ps)
def tf_38(g):
    leg, (a, b) = _st(g); k = leg[0]; return _ok(_map([a, b], lambda x, y: y if x == k else x))
rule("b_shows_through_where_a_has_key_colour", "The first key cell is a colour k. Output panel 1 (A), except that every cell of A holding colour k is replaced by panel 2's cell at the same position (which may be 0).", gi_38, tf_38)


# ---------- 42 ----------
def lg_k3(rng, cols, sep, W): return [rng.randint(1, 3)]
def gi_42(rng): return build(rng, 3, lg_k3, ncol=5, dens=(0.4, 0.8), p=0.5)
def tf_42(g):
    leg, ps = _st(g); k = leg[0]
    return _ok(_map(ps, lambda *v: (lambda s: s[k - 1] if len(s) >= k else 0)(sorted(x for x in v if x))))
rule("kth_smallest_nonzero_digit_of_three_panels", "The first key cell is a digit k (1-3). At each cell list the non-zero digits of the three panels in ascending order; the cell becomes the k-th of them (the smallest for k=1), or 0 if fewer than k are non-zero.", gi_42, tf_42, digits=True)


# ---------- 43 ----------
def lg_roll(rng, cols, sep, W): return [rng.randint(1, 4)]
def gi_43(rng): return build(rng, 2, lg_roll, ncol=3, kind=_blob, dens=(0.5, 0.8))
def tf_43(g):
    leg, (a, b) = _st(g); d = leg[0]; w = len(b[0]); br = [r[w - d:] + r[:w - d] for r in b]
    return _ok(_map([a, br], _over))
rule("roll_b_right_by_key_digit_then_a_over_b", "The first key cell is a digit d. Panel 2 (B) is rotated d columns to the right, wrapping round; then panel 1 (A) is laid over it.", gi_43, tf_43, digits=True)


# ---------- 44 ----------
def lg_flip(rng, cols, sep, W): return [rng.randint(1, 3)]
def gi_44(rng): return build(rng, 2, lg_flip, ncol=3, kind=_blob, dens=(0.5, 0.8))
def tf_44(g):
    leg, (a, b) = _st(g); m = leg[0]
    b2 = [r[::-1] for r in b] if m == 1 else b[::-1] if m == 2 else [r[::-1] for r in b[::-1]]
    return _ok(_map([a, b2], _over))
rule("key_digit_picks_flip_of_b_then_a_over_b", "The first key cell picks how panel 2 (B) is turned: 1 mirrors it left-right, 2 mirrors it top-bottom, 3 rotates it a half turn. Then panel 1 (A) is laid over the turned B.", gi_44, tf_44, digits=True)


# ---------- 45 ----------
def lg_mod(rng, cols, sep, W): return [rng.randint(3, 9)]
def gi_45(rng): return build(rng, 2, lg_mod, ncol=5, dens=(0.6, 1.0))
def tf_45(g):
    leg, (a, b) = _st(g); m = leg[0]; return _ok(_map([a, b], lambda x, y: (x + y) % m))
rule("sum_of_two_digit_panels_mod_key_digit", "Add the two panels cell by cell as digits and take the remainder after dividing by the first key cell's digit m (3-9).", gi_45, tf_45, digits=True)


# ---------- 46 ----------
def gi_46(rng): return build(rng, 2, lg_one, ncol=3, kind=_blob, dens=(0.5, 0.8))
def tf_46(g):
    leg, (a, b) = _st(g); return _ok(_map([a, b], lambda x, y: x or y or leg[0]))
rule("a_over_b_background_filled_with_key_colour", "Panel 1 (A) is laid over panel 2 (B); every cell that is still 0 afterwards is painted with the key colour (first key cell).", gi_46, tf_46)
