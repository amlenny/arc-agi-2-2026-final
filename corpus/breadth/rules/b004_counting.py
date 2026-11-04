# b004_counting.py -- theme: COUNTING / SUMMARY / OUTPUT-SIZE-CHANGE. Forty rules that count, compare,
# select-by-frequency, histogram, downsample, split-and-combine panels. Each computes something different.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


# ---------------------------------------------------------------- shared helpers (this file only)
def _scene(rng, k_lo=2, k_hi=5, n_lo=3, n_hi=8, lo=6, hi=18, margin=1, cols=None):
    """k separated same-colour objects on black; cols(rng, k) picks the colour list."""
    h, w = size(rng, lo, hi); g = blank(h, w)
    k = rng.randint(k_lo, k_hi)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    cs = cols(rng, k) if cols else [rng.choice(COLOURS) for _ in range(k)]
    if place_shapes(rng, g, shapes, cs, margin=margin) is None:
        return None
    return g if len(objects(g, 0)) == k else None


def _nz(g):
    return {c: n for c, n in counts(g).items() if c}


def _scatter(rng, lo=5, hi=14, k_lo=2, k_hi=5, dens=(0.15, 0.5)):
    h, w = size(rng, lo, hi); g = blank(h, w); cs = colours(rng, rng.randint(k_lo, k_hi))
    for col in cs:
        sprinkle(rng, g, rng.randint(1, max(1, int(h * w * rng.uniform(*dens) / len(cs)))), col)
    return g


def _distinct_counts(g):
    cnt = _nz(g); return len(cnt) >= 2 and len(set(cnt.values())) == len(cnt)


def _col_of(g, o):
    return g[o[0][0]][o[0][1]]


def _shape(o):
    r0, c0, _, _ = bbox(o); return tuple(sorted((r - r0, c - c0) for r, c in o))


def _halves_v(rng, lo=4, hi=12, p=0.45):
    h, hw = rng.randint(lo, hi), rng.randint(lo, hi); sep, a, b = colours(rng, 3)
    L = [[a if rng.random() < p else 0 for _ in range(hw)] for _ in range(h)]
    R = [[b if rng.random() < p else 0 for _ in range(hw)] for _ in range(h)]
    return [L[r] + [sep] + R[r] for r in range(h)]


def _split_v(g):
    m = len(g[0]) // 2
    return [row[:m] for row in g], [row[m + 1:] for row in g], g[0][m]


def _halves_h(rng, lo=4, hi=12, p=0.45):
    return transpose(_halves_v(rng, lo, hi, p))


def _split_h(g):
    m = len(g) // 2
    return g[:m], g[m + 1:], g[m][0]


def _panels(rng, fill, P=None, lo=3, hi=6):
    """P panels side by side separated by one-cell lines of one colour; fill(rng, h, pw, cols) makes a panel."""
    P = P or rng.randint(2, 4); h, pw = rng.randint(lo, hi), rng.randint(lo, hi); sep = rng.choice(COLOURS)
    cs = [c for c in COLOURS if c != sep]
    panels = fill(rng, h, pw, cs, P)
    g = []
    for r in range(h):
        row = []
        for i, p in enumerate(panels):
            if i: row.append(sep)
            row += p[r]
        g.append(row)
    return g if len(_split_panels(g)) == P else None


def _split_panels(g):
    h, w = dims(g); seps = [c for c in range(w) if g[0][c] and all(g[r][c] == g[0][c] for r in range(h))]
    cuts = [-1] + seps + [w]
    return [[row[a + 1:b] for row in g] for a, b in zip(cuts, cuts[1:]) if b - a > 1]


def _blocks(rng, k, fill, lo=2, hi=7):
    bh, bw = rng.randint(lo, hi), rng.randint(lo, hi); g = blank(bh * k, bw * k)
    for i in range(bh):
        for j in range(bw):
            paste(g, fill(rng, k), i * k, j * k)
    return g


def _block_view(g, k):
    h, w = dims(g)
    return [[crop(g, i * k, j * k, i * k + k - 1, j * k + k - 1) for j in range(w // k)] for i in range(h // k)]


# ================================================================ 1-8: colour-frequency summaries
def gi_hist_cols(rng):
    g = _scatter(rng, 5, 12, 2, 5); cnt = _nz(g)
    return g if len(cnt) >= 2 and max(cnt.values()) <= 30 else None
def tf_hist_cols(g):
    cnt = _nz(g); cs = sorted(cnt); H = max(cnt.values()); out = blank(H, len(cs))
    for i, c in enumerate(cs):
        for r in range(H - cnt[c], H): out[r][i] = c
    return out
rule("colour_cell_histogram_columns", "One column per colour in colour order; each column is a bottom-aligned bar as tall as that colour's cell count.", gi_hist_cols, tf_hist_cols)


def gi_hist_rows(rng):
    g = _scatter(rng, 5, 12, 2, 5)
    return g if _distinct_counts(g) and max(_nz(g).values()) <= 30 else None
def tf_hist_rows(g):
    cnt = _nz(g); order = sorted(cnt, key=lambda c: -cnt[c]); W = max(cnt.values())
    return [[c] * cnt[c] + [0] * (W - cnt[c]) for c in order]
rule("colour_cell_histogram_rows_by_freq", "One left-aligned bar per colour, most frequent colour on top, each bar as long as that colour's cell count.", gi_hist_rows, tf_hist_rows)


def gi_sq(rng):
    g = _scene(rng, 1, 7, 1, 5, 6, 16)
    if g is None: return None
    top = sorted(_nz(g).values()); return g if len(top) == 1 or top[-1] != top[-2] else None
def tf_sq(g):
    n = len(objects(g, 0)); c = max(_nz(g).items(), key=lambda kv: kv[1])[0]
    return [row + [0] for row in blank(n, n, c)]
rule("object_count_square_majority", "Output an N by N square of the colour with the most cells, where N is the number of objects, followed by one empty cell in each row.", gi_sq, tf_sq)
def gi_distinct(rng):
    g = _scatter(rng, 5, 14, 2, 6); return g if _distinct_counts(g) else None
def tf_most(g):
    c, n = max(_nz(g).items(), key=lambda kv: kv[1]); return [[c] * n + [0]] if n <= 29 else None
rule("most_frequent_colour_bar", "Output one row of the most frequent colour, as long as that colour's cell count, followed by one empty cell.", gi_distinct, tf_most)
def gi_least(rng):
    g = _scatter(rng, 6, 14, 2, 5); c = min(_nz(g).items(), key=lambda kv: kv[1])[0] if _distinct_counts(g) else None
    return g if c and len(cells(g, lambda v: v == c)) >= 2 else None
def tf_least(g):
    c = min(_nz(g).items(), key=lambda kv: kv[1])[0]; pts = cells(g, lambda v: v == c)
    return [[v if v == c else 0 for v in row] for row in crop(g, *bbox(pts))]
rule("crop_least_frequent_colour_cells", "Output the bounding box of the cells of the rarest colour, with every other colour erased.", gi_least, tf_least)


def gi_three(rng):
    h, w = size(rng, 5, 14); g = blank(h, w); cs = colours(rng, rng.randint(2, 5))
    sprinkle(rng, g, 3, cs[0])
    for c in cs[1:]: sprinkle(rng, g, rng.choice([1, 2, 4, 5, 6, 7, 8]), c)
    return g if list(_nz(g).values()).count(3) == 1 else None
def tf_three(g):
    cand = [c for c, n in _nz(g).items() if n == 3]
    if len(cand) != 1: return None
    pts = cells(g, lambda v: v == cand[0]); sub = crop(g, *bbox(pts))
    return [[v if v == cand[0] else 0 for v in row] for row in sub]
rule("three_cell_colour_crop", "Find the one colour that appears exactly three times and output the bounding box of those three cells alone.", gi_three, tf_three)


def tf_freq_row(g):
    cnt = _nz(g); return [sorted(cnt, key=lambda c: -cnt[c])]
rule("colours_by_frequency_row_desc", "Output one row listing the colours from most frequent on the left to least frequent on the right.", gi_distinct, tf_freq_row)


def tf_freq_col(g):
    cnt = _nz(g); return [[c] for c in sorted(cnt, key=lambda c: cnt[c])]
rule("colours_by_frequency_column_asc", "Output one column listing the colours from least frequent at the top to most frequent at the bottom.", gi_distinct, tf_freq_col)


# ================================================================ 9-14: compare two halves
def gi_hv(rng): return _halves_v(rng)
def gi_hh(rng): return _halves_h(rng)

def tf_and(g):
    L, R, s = _split_v(g); return [[s if a and b else 0 for a, b in zip(lr, rr)] for lr, rr in zip(L, R)]
rule("halves_and_vertical_split", "Left and right halves are divided by a line; output the cells filled in both halves, in the line's colour.", gi_hv, tf_and)


def tf_or(g):
    T, B, s = _split_h(g); return [[s if a or b else 0 for a, b in zip(tr, br)] for tr, br in zip(T, B)]
rule("halves_or_horizontal_split", "Top and bottom halves are divided by a line; output the cells filled in either half, in the line's colour.", gi_hh, tf_or)


def tf_xor(g):
    L, R, s = _split_v(g); return [[s if bool(a) != bool(b) else 0 for a, b in zip(lr, rr)] for lr, rr in zip(L, R)]
rule("halves_xor_vertical_split", "Left and right halves are divided by a line; output the cells filled in exactly one half, in the line's colour.", gi_hv, tf_xor)


def tf_nor(g):
    T, B, s = _split_h(g); return [[s if not a and not b else 0 for a, b in zip(tr, br)] for tr, br in zip(T, B)]
rule("halves_nor_horizontal_split", "Top and bottom halves are divided by a line; output the cells empty in both halves, in the line's colour.", gi_hh, tf_nor)


def tf_minus(g):
    L, R, s = _split_v(g); out = [[a if a and not b else 0 for a, b in zip(lr, rr)] for lr, rr in zip(L, R)]
    return out if any(v for row in out for v in row) else None
rule("halves_left_minus_right", "Left and right halves are divided by a line; output the left half with every cell that is also filled on the right removed.", gi_hv, tf_minus)


def gi_diff(rng):
    h, hw = rng.randint(4, 12), rng.randint(4, 12); cs = colours(rng, rng.randint(2, 4))
    L = [[rng.choice(cs) if rng.random() < 0.55 else 0 for _ in range(hw)] for _ in range(h)]
    R = copy(L)
    for _ in range(rng.randint(1, max(1, h * hw // 4))):
        r, c = rng.randrange(h), rng.randrange(hw); R[r][c] = rng.choice([v for v in [0] + cs if v != R[r][c]])
    return [L[r] + R[r] for r in range(h)]
def tf_diff(g):
    m = len(g[0]) // 2; out = [[row[m + c] if row[m + c] != row[c] else 0 for c in range(m)] for row in g]
    return out if any(v for row in out for v in row) else None
rule("right_half_differences", "The right half is a copy of the left half with some cells changed; output only the changed cells with their right-half colours.", gi_diff, tf_diff)


# ================================================================ 15-18: odd-one-out and repetition
def gi_odd_shape(rng):
    h, w = size(rng, 8, 18); g = blank(h, w); k = rng.randint(3, 6); col = rng.choice(COLOURS)
    base = random_shape(rng, rng.randint(2, 6)); odd = random_shape(rng, rng.randint(2, 6))
    if tuple(odd) == tuple(base): return None
    shapes = [base] * (k - 1) + [odd]; rng.shuffle(shapes)
    if place_shapes(rng, g, shapes, [col] * k, margin=1) is None: return None
    return g if len(objects(g, 0)) == k else None
def tf_odd_shape(g):
    obs = objects(g, 0); sh = [_shape(o) for o in obs]; uniq = [o for o, s in zip(obs, sh) if sh.count(s) == 1]
    return crop(g, *bbox(uniq[0])) if len(uniq) == 1 and len(obs) >= 3 else None
rule("odd_shape_object_crop", "All objects share one shape except one; output the bounding box of the differently shaped object.", gi_odd_shape, tf_odd_shape)


def gi_odd_size(rng):
    h, w = size(rng, 8, 18); g = blank(h, w); k = rng.randint(3, 6); n = rng.randint(2, 6)
    m = rng.choice([x for x in range(1, 9) if x != n])
    shapes = [random_shape(rng, n) for _ in range(k - 1)] + [random_shape(rng, m)]; rng.shuffle(shapes)
    if place_shapes(rng, g, shapes, [rng.choice(COLOURS) for _ in range(k)], margin=1) is None: return None
    return g if len(objects(g, 0)) == k else None
def tf_odd_size(g):
    obs = objects(g, 0); sz = [len(o) for o in obs]; uniq = [o for o in obs if sz.count(len(o)) == 1]
    return crop(g, *bbox(uniq[0])) if len(uniq) == 1 and len(obs) >= 3 else None
rule("odd_size_object_crop", "All objects have the same number of cells except one; output the bounding box of the object with a different cell count.", gi_odd_size, tf_odd_size)


def gi_repeat(rng):
    h, w = size(rng, 9, 20); g = blank(h, w); t = rng.randint(2, 4); k = rng.randint(1, 3)
    rep = random_shape(rng, rng.randint(2, 5)); others = [random_shape(rng, rng.randint(2, 6)) for _ in range(k)]
    if any(tuple(o) == tuple(rep) for o in others) or len({tuple(o) for o in others}) < k: return None
    cs = colours(rng, k + 1); shapes = [rep] * t + others; cols = [cs[0]] * t + cs[1:]
    idx = list(range(len(shapes))); rng.shuffle(idx)
    if place_shapes(rng, g, [shapes[i] for i in idx], [cols[i] for i in idx], margin=1) is None: return None
    return g if len(objects(g, 0)) == t + k else None
def tf_repeat(g):
    obs = objects(g, 0); sh = [_shape(o) for o in obs]; best = max(set(sh), key=sh.count)
    if sh.count(best) < 2 or [sh.count(s) for s in set(sh)].count(sh.count(best)) > 1: return None
    return crop(g, *bbox(obs[sh.index(best)]))
rule("most_repeated_shape_crop", "Output the one shape that occurs more often than any other shape in the grid.", gi_repeat, tf_repeat)


def gi_stairs(rng):
    return _scene(rng, 1, 8, 1, 4, 6, 16, cols=lambda rng, k: [rng.choice(COLOURS)] * k)
def tf_stairs(g):
    n = len(objects(g, 0)); c = max(_nz(g).items(), key=lambda kv: kv[1])[0]
    return [[c if j <= i else 0 for j in range(n)] for i in range(n)]
rule("object_count_staircase", "Output an N-step staircase (row i has i filled cells from the left) in the objects' colour, where N is the number of objects.", gi_stairs, tf_stairs)


# ================================================================ 19: holes
def gi_holes(rng):
    h, w = size(rng, 8, 20); g = blank(h, w); k = rng.randint(2, 5); got = 0; any_hole = False
    for _ in range(60):
        rh, rw = rng.randint(3, 6), rng.randint(3, 6)
        if rh + 2 > h or rw + 2 > w: continue
        r0, c0 = rng.randint(1, h - rh - 1), rng.randint(1, w - rw - 1)
        if any(g[r][c] for r in range(r0 - 1, r0 + rh + 1) for c in range(c0 - 1, c0 + rw + 1)): continue
        rect(g, r0, c0, r0 + rh - 1, c0 + rw - 1, rng.choice(COLOURS))
        inner = [(r, c) for r in range(r0 + 1, r0 + rh - 1) for c in range(c0 + 1, c0 + rw - 1)]
        nh = rng.randint(0, min(4, len(inner)))
        for r, c in rng.sample(inner, nh): g[r][c] = 0
        any_hole |= nh > 0; got += 1
        if got == k: break
    return g if got >= 2 and any_hole else None
def tf_holes(g):
    obs = sorted(objects(g, 0, conn8=False), key=lambda o: bbox(o)[0]); rows = []
    for o in obs:
        sub = crop(g, *bbox(o)); rows.append((_col_of(g, o), len(components(sub, 0))))
    W = max(n for _, n in rows)
    return [[c] * n + [0] * (W - n) for c, n in rows] if W else None
rule("holes_per_object_bars", "One row per rectangle from top to bottom; each row is a bar in that rectangle's colour as long as its number of holes.", gi_holes, tf_holes)


# ================================================================ 20-23: panels
def _fill_random(rng, h, pw, cs, P):
    out = []
    for _ in range(P):
        p = blank(h, pw); k = rng.randint(1, h * pw - 1); c = rng.choice(cs)
        sprinkle(rng, p, k, c if rng.random() < 0.5 else rng.choice(cs)); out.append(p)
    return out
def gi_panel_cells(rng):
    g = _panels(rng, _fill_random)
    if g is None: return None
    ns = [sum(1 for row in p for v in row if v) for p in _split_panels(g)]
    return g if ns.count(max(ns)) == 1 else None
def tf_panel_cells(g):
    ps = _split_panels(g); return max(ps, key=lambda p: sum(1 for row in p for v in row if v))
rule("panel_most_cells", "The grid is split into panels by lines; output the panel containing the most coloured cells.", gi_panel_cells, tf_panel_cells)


def _fill_odd(rng, h, pw, cs, P):
    base = blank(h, pw); sprinkle(rng, base, rng.randint(2, h * pw // 2), rng.choice(cs))
    odd = copy(base)
    for _ in range(rng.randint(1, 3)):
        r, c = rng.randrange(h), rng.randrange(pw); odd[r][c] = rng.choice(cs) if odd[r][c] == 0 else 0
    ps = [copy(base) for _ in range(P - 1)] + [odd]; rng.shuffle(ps); return ps
def gi_panel_odd(rng):
    g = _panels(rng, _fill_odd, P=rng.randint(3, 4)); return g if g and tf_panel_odd(g) else None
def tf_panel_odd(g):
    ps = _split_panels(g); uniq = [p for p in ps if sum(1 for q in ps if q == p) == 1]
    return uniq[0] if len(uniq) == 1 and len(ps) >= 3 else None
rule("panel_odd_one_out", "The grid is split into identical panels by lines, except one; output the panel that differs.", gi_panel_odd, tf_panel_odd)


def _fill_colours(rng, h, pw, cs, P):
    out = []
    for _ in range(P):
        p = blank(h, pw)
        for c in rng.sample(cs, rng.randint(1, min(5, len(cs)))): sprinkle(rng, p, rng.randint(1, 3), c)
        out.append(p)
    return out
def gi_panel_colours(rng):
    g = _panels(rng, _fill_colours, lo=3, hi=6)
    if g is None: return None
    ns = [len({v for row in p for v in row if v}) for p in _split_panels(g)]
    return g if ns.count(max(ns)) == 1 else None
def tf_panel_colours(g):
    return max(_split_panels(g), key=lambda p: len({v for row in p for v in row if v}))
rule("panel_most_colours", "The grid is split into panels by lines; output the panel that uses the most distinct colours.", gi_panel_colours, tf_panel_colours)


def _fill_vote(rng, h, pw, cs, P):
    base = blank(h, pw); sprinkle(rng, base, rng.randint(h * pw // 4, h * pw * 2 // 3), rng.choice(cs)); out = []
    for _ in range(P):
        p = copy(base)
        for _ in range(rng.randint(1, max(1, h * pw // 6))):
            r, c = rng.randrange(h), rng.randrange(pw); p[r][c] = rng.choice(cs) if p[r][c] == 0 else 0
        out.append(p)
    return out
def gi_vote(rng):
    g = _panels(rng, _fill_vote, P=3); return g if g and tf_vote(g) else None
def tf_vote(g):
    ps = _split_panels(g); h, w = dims(ps[0]); out = blank(h, w)
    for r in range(h):
        for c in range(w):
            vs = [p[r][c] for p in ps]; m = max(set(vs), key=vs.count)
            if vs.count(m) < 2: return None
            out[r][c] = m
    return out if out not in ps else None
rule("panels_majority_vote", "Three panels divided by lines are noisy copies of one picture; output the picture where each cell takes the value at least two panels agree on.", gi_vote, tf_vote)


# ================================================================ 24-25: block summaries
def _fill_major(rng, k):
    c = rng.choice([0] + COLOURS); b = blank(k, k, c)
    for _ in range(rng.randint(0, 3)):
        r, x = rng.randrange(k), rng.randrange(k); b[r][x] = rng.choice([v for v in [0] + COLOURS if v != c])
    return b
def gi_major(rng):
    g = _blocks(rng, 3, _fill_major, 2, 7); return g if tf_major(g) else None
def tf_major(g):
    out = []
    for brow in _block_view(g, 3):
        row = []
        for b in brow:
            vs = [v for r in b for v in r]; m = max(set(vs), key=vs.count)
            if vs.count(m) < 5: return None
            row.append(m)
        out.append(row)
    return out if any(v for r in out for v in r) else None
rule("downsample_majority_blocks", "Each 3 by 3 block of the grid becomes one cell of the colour that fills most of that block.", gi_major, tf_major)


def _fill_count(rng, k):
    b = blank(k, k); sprinkle(rng, b, rng.randint(0, k * k), rng.choice(COLOURS)); return b
def gi_count_blocks(rng):
    g = _blocks(rng, 3, _fill_count, 2, 7); return g if any(v for r in g for v in r) else None
def tf_count_blocks(g):
    return [[sum(1 for r in b for v in r if v) for b in brow] for brow in _block_view(g, 3)]
rule("block_cell_count_digits", "Each 3 by 3 block becomes one cell whose value is the number of coloured cells in that block.", gi_count_blocks, tf_count_blocks, digits=True)


# ================================================================ 26-29: counts and selections
def gi_objs9(rng):
    return _scene(rng, 1, 9, 1, 5, 6, 18)
def tf_count_diag(g):
    n = len(objects(g, 0)); c = max(_nz(g).items(), key=lambda kv: kv[1])[0]
    return [[c if i == j else 0 for j in range(n)] for i in range(n)] if n >= 2 else None
rule("object_count_diagonal", "Output an N by N grid with only its main diagonal filled in the most common colour, where N is the number of objects.", gi_objs9, tf_count_diag)


def gi_objs_cols(rng):
    g = _scene(rng, 2, 8, 1, 4, 6, 18, cols=lambda rng, k: [rng.choice(colours(rng, 3)) for _ in range(k)])
    return g if g and len(_nz(g)) >= 2 else None
def tf_objs_per_colour(g):
    cnt = {}
    for o in objects(g, 0): c = _col_of(g, o); cnt[c] = cnt.get(c, 0) + 1
    W = max(cnt.values()); return [[c] * cnt[c] + [0] * (W - cnt[c]) for c in sorted(cnt)]
rule("objects_per_colour_bars", "One row per colour in colour order; each row is a bar as long as the number of separate objects of that colour.", gi_objs_cols, tf_objs_per_colour)
def gi_rowmost(rng):
    g = _scatter(rng, 5, 14, 2, 5); ns = [sum(1 for v in row if v) for row in g]
    return g if ns.count(max(ns)) == 1 and max(ns) > 0 else None
def tf_rowmost(g):
    return [max(g, key=lambda row: sum(1 for v in row if v))]
rule("row_with_most_cells", "Output the single row that contains the most coloured cells.", gi_rowmost, tf_rowmost)


def gi_colmost(rng):
    g = _scatter(rng, 5, 14, 3, 6); ns = [len({v for v in col if v}) for col in transpose(g)]
    return g if ns.count(max(ns)) == 1 else None
def tf_colmost(g):
    col = max(transpose(g), key=lambda col: len({v for v in col if v})); return [[v] for v in col]
rule("column_with_most_colours", "Output the single column that contains the most distinct colours.", gi_colmost, tf_colmost)


# ================================================================ 30-35: recolour / filter by count
def gi_rank(rng):
    g = _scene(rng, 2, 6, 1, 9, 7, 18, cols=lambda rng, k: [rng.choice(COLOURS)] * k)
    if g is None: return None
    sz = [len(o) for o in objects(g, 0)]; return g if len(set(sz)) == len(sz) else None
def tf_rank(g):
    obs = sorted(objects(g, 0), key=len); out = copy(g)
    for i, o in enumerate(obs):
        for r, c in o: out[r][c] = i + 1
    return out
# recolour_objects_by_size_rank dropped 2026-10-12 (trio review: behavioural duplicate or one global operation)
def gi_cellcount(rng):
    return _scene(rng, 2, 6, 1, 9, 7, 18, cols=lambda rng, k: [rng.choice(COLOURS)] * k)
def tf_cellcount(g):
    out = copy(g)
    for o in objects(g, 0):
        for r, c in o: out[r][c] = len(o)
    return out
rule("recolour_objects_by_cell_count", "Every object is recoloured with the value equal to its number of cells.", gi_cellcount, tf_cellcount, digits=True)


def tf_fill_major(g):
    c = max(_nz(g).items(), key=lambda kv: kv[1])[0]; return [[v if v else c for v in row] for row in g]
rule("fill_background_with_majority", "Every empty cell is painted with the colour that already covers the most cells.", gi_distinct, tf_fill_major)


def tf_remove_least(g):
    c = min(_nz(g).items(), key=lambda kv: kv[1])[0]; return [[0 if v == c else v for v in row] for row in g]
rule("remove_least_frequent_colour", "All cells of the colour that appears fewest times are erased.", gi_distinct, tf_remove_least)


def tf_keep_most(g):
    c = max(_nz(g).items(), key=lambda kv: kv[1])[0]; return [[v if v == c else 0 for v in row] for row in g]
rule("keep_only_most_frequent_colour", "Only the cells of the colour that appears most often are kept; everything else is erased.", gi_distinct, tf_keep_most)


def gi_nbr(rng):
    g = _scatter(rng, 5, 14, 1, 3, (0.3, 0.6)); return g
def tf_nbr(g):
    h, w = dims(g); out = blank(h, w)
    for r in range(h):
        for c in range(w):
            if g[r][c]:
                out[r][c] = sum(1 for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)) if 0 <= r + dr < h and 0 <= c + dc < w and g[r + dr][c + dc])
    return out if any(v for row in out for v in row) else None
rule("cell_neighbour_count_digits", "Every coloured cell becomes the count of its coloured side-neighbours; isolated cells vanish.", gi_nbr, tf_nbr, digits=True)


# ================================================================ 36-40: more comparisons and orderings
def gi_half_more(rng):
    g = _halves_v(rng, 4, 12, rng.uniform(0.2, 0.6)); L, R, _ = _split_v(g)
    nl, nr = sum(v > 0 for row in L for v in row), sum(v > 0 for row in R for v in row)
    return g if nl != nr else None
def tf_half_more(g):
    L, R, _ = _split_v(g)
    return L if sum(v > 0 for row in L for v in row) > sum(v > 0 for row in R for v in row) else R
rule("half_with_more_cells", "Two halves are divided by a line; output the half that contains more coloured cells.", gi_half_more, tf_half_more)


def gi_parity(rng):
    return _scene(rng, 1, 8, 1, 4, 6, 16, cols=lambda rng, k: [rng.choice(COLOURS)] * k)
def tf_parity(g):
    n = len(objects(g, 0)); c = max(_nz(g).items(), key=lambda kv: kv[1])[0]
    sq = blank(1, 1, c) if n % 2 == 0 else blank(2, 2, c)
    return [row + [0] for row in sq]
rule("object_count_parity_square", "If the number of objects is even output a 1 by 1 cell of their colour, if odd a 2 by 2 square of it, each followed by one empty cell in each row.", gi_parity, tf_parity)
def gi_rowmaj(rng):
    h, w = size(rng, 4, 14); cs = colours(rng, rng.randint(2, 4)); g = blank(h, w)
    for r in range(h):
        if rng.random() < 0.85:
            a = rng.choice(cs); k = rng.randint(1, w)
            for c in rng.sample(range(w), k): g[r][c] = a if rng.random() < 0.7 else rng.choice(cs)
    return g if tf_rowmaj(g) else None
def tf_rowmaj(g):
    out = []
    for row in g:
        cnt = {v: row.count(v) for v in set(row) if v}
        if not cnt: out.append([0]); continue
        top = sorted(cnt.values())
        if len(top) > 1 and top[-1] == top[-2]: return None
        out.append([max(cnt, key=cnt.get)])
    return out if any(v[0] for v in out) else None
rule("row_majority_column", "Each row is reduced to one cell of its most common colour, giving a single column; empty rows stay empty.", gi_rowmaj, tf_rowmaj)


def gi_segments(rng):
    h, w = size(rng, 5, 16); g = blank(h, w); lens = []
    for r in rng.sample(range(h), rng.randint(2, min(h, 6))):
        L = rng.randint(1, w); c0 = rng.randint(0, w - L); col = rng.choice(COLOURS); lens.append(L)
        for c in range(c0, c0 + L): g[r][c] = col
    return g if lens.count(max(lens)) == 1 and max(lens) < w else None
def tf_segments(g):
    best = max(objects(g, 0, conn8=False), key=len); return [[_col_of(g, best)] * len(best) + [0]]
rule("longest_segment_row", "Output the single longest horizontal line as a row of its own colour and length, followed by one empty cell.", gi_segments, tf_segments)
def gi_sizecol(rng):
    g = _scene(rng, 2, 7, 1, 9, 7, 18)
    if g is None: return None
    sz = [len(o) for o in objects(g, 0)]; return g if len(set(sz)) == len(sz) else None
def tf_sizecol(g):
    return [[_col_of(g, o)] for o in sorted(objects(g, 0), key=len)]
rule("objects_sorted_by_size_column", "Output one column listing each object's colour, smallest object at the top and largest at the bottom.", gi_sizecol, tf_sizecol)
