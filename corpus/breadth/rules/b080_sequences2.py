# b080_sequences2.py -- ROWS AND COLUMNS AS SEQUENCES, SECOND SET: run-length codes, run reordering, per-row
# statistics, prefix operations, sequence arithmetic on digit rows. Background is 0. A "run" is a maximal
# stretch of equal non-background cells in one row. Rows are processed independently unless stated.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


# ---------- helpers ----------
def _hw(rng, hcap=30, p=0.35, lo=4, hi=14):
    if rng.random() < p:
        return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(max(lo, 6), hi + 4)


def _mkrow(rng, w, pal, lmax, adj):
    row = [0] * w; pos = rng.randint(0, 2); prev = None
    while True:
        g = 0 if (adj and prev and rng.random() < 0.4) else rng.randint(1, 3) if prev else rng.randint(0, 2)
        c = rng.choice([x for x in pal if x != prev] if g == 0 else pal); l = rng.randint(1, lmax)
        if pos + g + l > w: break
        for i in range(l): row[pos + g + i] = c
        prev = c; pos += g + l
        if rng.random() < 0.12: break
    if not any(row):
        row[rng.randint(0, w - 1)] = pal[0]
    return row


def _runs(r):
    out, i = [], 0
    while i < len(r):
        if r[i]:
            j = i
            while j < len(r) and r[j] == r[i]: j += 1
            out.append((r[i], i, j - i)); i = j
        else:
            i += 1
    return out


def _pack(rs, w):
    row = []
    for k, (c, l) in enumerate(rs):
        row += ([0] if k else []) + [c] * l
    return row + [0] * (w - len(row))


def gen_a(rng, hcap=30, lmax=6, excl=(0,)):
    """gapped runs, every row has at least one run, runs separated by >=1 background cell"""
    h, w = _hw(rng); h = min(h, hcap)
    pal = colours(rng, rng.randint(2, 4), exclude=excl)
    return [_mkrow(rng, w, pal, lmax, False) for _ in range(h)]


def gen_b(rng, hcap=30, lmax=6, excl=(0,)):
    """runs that may touch when their colours differ"""
    h, w = _hw(rng); h = min(h, hcap)
    pal = colours(rng, rng.randint(3, 5), exclude=excl)
    return [_mkrow(rng, w, pal, lmax, True) for _ in range(h)]


def gen_c(rng, hcap=30, dens=None, excl=(0,)):
    """noise rows"""
    h, w = _hw(rng); h = min(h, hcap)
    pal = colours(rng, rng.randint(2, 4), exclude=excl); d = dens or rng.uniform(0.4, 0.8)
    return [[rng.choice(pal) if rng.random() < d else 0 for _ in range(w)] for _ in range(h)]


def gen_d(rng, hcap=30):
    """digit grids 0..9 as data"""
    h, w = _hw(rng); h = min(h, hcap)
    return [[rng.randint(0, 9) for _ in range(w)] for _ in range(h)]


# ---------- 1 ----------
def gi_1(rng): return gen_a(rng, lmax=7)
def tf_1(g):
    rs = [_runs(r) for r in g]; m = max(len(x) for x in rs)
    return [sum(([c, l] for c, _, l in x), []) + [0] * (2 * (m - len(x))) for x in rs]
rule("rle_each_row_pairs", "Each row becomes its run-length code: for every run of one non-background colour, left to right, the colour then its length as a digit; rows are padded with 0 on the right to twice the largest run count of any row.", gi_1, tf_1, digits=True)


# ---------- 2 ----------
def gi_2(rng):
    big = rng.random() < 0.4
    h = rng.randint(21, 30) if big else rng.randint(3, 12); rows = []
    mr = 11 if big else rng.randint(2, 5)
    pal = colours(rng, rng.randint(3, 5))
    for i in range(h):
        n = mr if i == 0 else rng.randint(1, mr); row = []; prev = None
        for _ in range(n):
            c = rng.choice([x for x in pal if x != prev]); prev = c
            row += [c, rng.randint(1, 2 if big else 5)]
        rows.append(row + [0] * (2 * mr - len(row)))
    return rows
def tf_2(g):
    out = []
    for r in g:
        row = []
        for i in range(0, len(r), 2):
            if r[i]: row += [r[i]] * r[i + 1]
        out.append(row)
    W = max(len(x) for x in out)
    return [x + [0] * (W - len(x)) for x in out] if W <= 30 else None
rule("decode_row_run_length_code", "Each row is a run-length code of (colour, length digit) pairs, padded with 0; output each row expanded into its runs placed end to end from the left, padded with 0 on the right to the width of the longest decoded row.", gi_2, tf_2, digits=True)


# ---------- 3 ----------
def gi_3(rng): return gen_a(rng, lmax=5)
def tf_3(g):
    return [_pack(sorted([(c, l) for c, _, l in _runs(r)], key=lambda x: x[1]), len(r)) for r in g]
rule("sort_row_runs_by_length", "In each row the runs are re-ordered by length, shortest first (equal lengths keep their left-to-right order), and packed against the left edge with exactly one background cell between neighbouring runs.", gi_3, tf_3)


# ---------- 4 ----------
def gi_4(rng): return gen_a(rng, lmax=6)
def tf_4(g):
    out = []
    for r in g:
        rs = [(c, l) for c, _, l in _runs(r)]; i = max(range(len(rs)), key=lambda k: (rs[k][1], -k))
        out.append(_pack([rs[i]] + rs[:i] + rs[i + 1:], len(r)))
    return out
rule("longest_run_to_front_per_row", "In each row the longest run (leftmost if tied) moves to the left edge; the other runs follow in their original order, all separated by exactly one background cell.", gi_4, tf_4)


# ---------- 5 ----------
def gi_5(rng): return gen_c(rng)
def tf_5(g):
    out = []
    for r in g:
        k = sum(1 for v in r if v == 0) % len(r); out.append(r[k:] + r[:k])
    return out
rule("rotate_row_left_by_background_count", "Each row is rotated to the left, wrapping round, by as many cells as the row has background (0) cells, taken modulo the row width.", gi_5, tf_5)


# ---------- 6 ----------
def gi_6(rng): return gen_a(rng, hcap=15)
def tf_6(g):
    out = []
    for r in g:
        rs = _runs(r); c, s, l = max(rs, key=lambda x: (x[2], -x[1])); w = len(r)
        out.append(r[:s] + [0] * (w - s)); out.append(r[s + l:] + [0] * (s + l))
    return out
rule("split_row_at_longest_run", "Each row becomes two rows: first the cells to the LEFT of its longest run (leftmost if tied), then the cells to the RIGHT of it, each placed from the left edge and padded with 0 on the right; the run itself is dropped.", gi_6, tf_6)


# ---------- 7 ----------
def gi_7(rng): return gen_c(rng)
def tf_7(g):
    out = []
    for r in g:
        cnt = counts([r]); cnt.pop(0, None)
        out.append([min(cnt, key=lambda c: (-cnt[c], c))] * len(r) if cnt else r[:])
    return out
rule("fill_row_with_majority_colour", "Each row is filled completely with its most frequent non-background colour (equal counts: lower colour value); a row with no coloured cell stays empty.", gi_7, tf_7)


# ---------- 8 ----------
def gi_8(rng): return gen_b(rng, lmax=7)
def tf_8(g):
    out = [r[:] for r in g]
    for y, r in enumerate(g):
        for c, s, l in _runs(r):
            for i in range(l): out[y][s + i] = l
    return out
rule("run_cells_become_run_length", "Every cell of a run in a row is replaced by the length of that run as a digit; background cells stay 0.", gi_8, tf_8, digits=True)


# ---------- 9 ----------
def gi_9(rng): return gen_b(rng)
def tf_9(g):
    return sorted(g, key=lambda r: len(_runs(r)))
rule("sort_rows_by_run_count", "The rows are reordered top to bottom from the fewest runs to the most, a run being an unbroken stretch of one non-background colour; rows with equal run counts keep their original order.", gi_9, tf_9)


# ---------- 10 ----------
def gi_10(rng):
    big = rng.random() < 0.4
    h = rng.randint(21, 30) if big else rng.randint(4, 10); w = rng.randint(21, 30) if big else rng.randint(5, 14)
    pal = colours(rng, rng.randint(1, 3)); g = blank(h, w)
    for c in range(w):
        for i in range(rng.randint(0, min(h, 9))): g[h - 1 - i][c] = rng.choice(pal)
    return g
def tf_10(g):
    row = [sum(1 for r in g if r[c]) for c in range(len(g[0]))]
    return [row] if len(set(row)) > 1 else None
rule("bar_chart_heights_as_digits", "The grid is a bar chart, one bar per column rising from the bottom; output one row with each column's bar height (its number of coloured cells) as a digit, left to right.", gi_10, tf_10, digits=True)


# ---------- 11 ----------
def gi_11(rng):
    h, w = _hw(rng, lo=1, hi=5); g = []
    for _ in range(h):
        v = rng.randint(0, 9); row = []
        for _ in range(w):
            row.append(v); v = max(0, min(9, v + rng.randint(-3, 3)))
        g.append(row)
    return g
def tf_11(g):
    out = [[min(abs(r[i] - 2 * r[i + 1] + r[i + 2]), 9) for i in range(len(r) - 2)] for r in g]
    return out if len({v for r in out for v in r}) > 1 else None
rule("row_second_difference_digits", "Each row is a sequence of digits; output, for every triple of neighbouring cells a, b, c, the digit |a - 2b + c| (capped at 9), so each output row is two cells shorter than its input row.", gi_11, tf_11, digits=True)


# ---------- 13 ----------
def gi_13(rng):
    big = rng.random() < 0.35
    h = rng.randint(21, 30) if big else rng.randint(3, 8); w = rng.randint(21, 30) if big else rng.randint(7, 16)
    pal = colours(rng, rng.randint(2, 3)); L = rng.randint(2, w - 3)
    pre = [rng.choice(pal + [0]) for _ in range(L)]
    return [pre + [rng.choice(pal + [0]) for _ in range(w - L)] for _ in range(h)]
def tf_13(g):
    L = 0
    while L < len(g[0]) and len({r[L] for r in g}) == 1: L += 1
    p = g[0][:L]
    return [p] if L >= 2 and len(set(p)) > 1 else None
rule("longest_common_prefix_of_rows", "Output one row: the longest left-to-right stretch of columns in which every row of the input has the same value (background counts as a value), starting at column 0; cut off at the first column where any two rows differ.", gi_13, tf_13)


# ---------- 14 ----------
def gi_14(rng):
    g = gen_c(rng, dens=0.7); w = len(g[0])
    for r in g:
        if rng.random() < 0.4:
            for j in range(w // 2): r[w - 1 - j] = r[j]
    return g
def tf_14(g): return [r[:] if r == r[::-1] else [0] * len(r) for r in g]
rule("erase_non_palindrome_rows", "Rows that read the same left to right and right to left stay unchanged; every other row is erased to background in place.", gi_14, tf_14)


# ---------- 15 ----------
def gi_15(rng):
    g = gen_c(rng, dens=0.5, excl=(0, 5)); w = len(g[0])
    for r in g: r[rng.randrange(w)] = 5
    return g
def tf_15(g):
    w = len(g[0]); t = g[0].index(5); out = []
    for r in g:
        k = (t - r.index(5)) % w; out.append(r[w - k:] + r[:w - k] if k else r[:])
    return out
rule("roll_rows_to_align_grey_with_top_row", "Every row holds exactly one grey (5) cell; each row is rotated right, wrapping round, so its grey cell lands in the column where the top row's grey cell is. The top row stays.", gi_15, tf_15)


# ---------- 18 ----------
def gi_18(rng): return gen_b(rng, lmax=8)
def tf_18(g):
    return [(lambda ls: ls + [0] * (len(r) - len(ls)))(sorted((l for _, _, l in _runs(r)), reverse=True)) for r in g]
rule("row_run_lengths_sorted_desc", "Each row is replaced by the lengths of its non-background runs as digits, largest first, packed against the left edge and padded with 0 on the right to the original width.", gi_18, tf_18, digits=True)


# ---------- 19 ----------
def gi_19(rng):
    h, w = rng.randint(2, 5), rng.randint(4, 8); pal = colours(rng, rng.randint(2, 3))
    return [_mkrow(rng, w, pal, 4, True) for _ in range(h)]
def tf_19(g):
    flat = [v for r in g for v in r]; rows = []; i = 0
    while i < len(flat):
        j = i
        while j < len(flat) and flat[j] == flat[i]: j += 1
        n = j - i
        while n > 0: rows.append([flat[i], min(n, 9)]); n -= 9
        i = j
    return rows if len(rows) <= 30 else None
rule("rle_whole_grid_reading_order", "Read all cells row by row, left to right, top to bottom, as one sequence and run-length encode it, background runs included: output one row per run, the colour (0 for background) then the run length as a digit; runs longer than 9 are cut into pieces of 9.", gi_19, tf_19, digits=True, small_ok=True)


# ---------- 20 ----------
def gi_20(rng):
    h, w = _hw(rng, lo=4, hi=12); k = rng.randint(2, max(2, h // 2)); pal = colours(rng, 3); rows = []
    base = [[rng.choice(pal + [0]) for _ in range(w)] for _ in range(k)]
    for i, b in enumerate(base):
        if i and b == base[i - 1]: b[0] = (b[0] % 9) + 1
    out = []
    for b in base: out += [b[:] for _ in range(rng.randint(1, 3))]
    return out[:30]
def tf_20(g):
    out = [g[0][:]]
    for r in g[1:]:
        if r != out[-1]: out.append(r[:])
    return out
rule("merge_consecutive_duplicate_rows", "Whenever a row is identical to the row directly above it, it is deleted, so each stack of identical neighbouring rows becomes one row. Identical rows that are not neighbours both stay.", gi_20, tf_20)


# ---------- 21 ----------
def gi_21(rng):
    h, w = _hw(rng, lo=4, hi=10); w = min(w, 29); k = rng.randint(2, 5); pal = colours(rng, 3, exclude=(0,))
    base = []
    while len(base) < k:
        r = [rng.choice(pal + [0]) for _ in range(w)]
        if r not in base: base.append(r)
    rows = [b[:] for b in base for _ in range(rng.randint(1, 4))]
    rng.shuffle(rows); return rows[:30]
def tf_21(g):
    order, n = [], {}
    for r in g:
        t = tuple(r)
        if t not in n: order.append(t); n[t] = 0
        n[t] += 1
    return [list(t) + [min(n[t], 9)] for t in order]
rule("distinct_rows_with_multiplicity_column", "Keep each distinct row once, in the order of its first appearance, and append one extra cell on the right holding how many times that row occurred in the input as a digit (cap 9).", gi_21, tf_21, digits=True)


# ---------- 22 ----------
def gi_22(rng): return gen_b(rng, lmax=9)
def tf_22(g):
    return sorted(g, key=lambda r: -max((l for _, _, l in _runs(r)), default=0))
rule("sort_rows_by_longest_run_desc", "The rows are reordered top to bottom by the length of their longest run of one non-background colour, longest first; rows with equal longest runs keep their original order.", gi_22, tf_22)


# ---------- 23 ----------
def gi_23(rng): return gen_c(rng, dens=0.5)
def tf_23(g):
    out = []
    for i, r in enumerate(g):
        k = i % len(r); out.append(r[k:] + r[:k])
    return out
rule("shear_rows_rotate_left_by_row_index", "Row i (counting from 0 at the top) is rotated to the left, wrapping round, by i cells modulo the row width.", gi_23, tf_23)


# ---------- 24 ----------
def gi_24(rng): return gen_d(rng)
def tf_24(g):
    out = []
    for r in g:
        m, row = 0, []
        for v in r: m = max(m, v); row.append(m)
        out.append(row)
    return out
rule("row_running_maximum_digits", "Each cell becomes the largest digit found in its row from the left edge up to and including that cell.", gi_24, tf_24, digits=True)


# ---------- 25 ----------
def gi_25(rng): return gen_c(rng, dens=0.5)
def tf_25(g):
    out = []
    for r in g:
        n, row = 0, []
        for v in r:
            if v: n += 1
            row.append(min(n, 9) if v else 0)
        out.append(row)
    return out
rule("number_coloured_cells_left_to_right", "In each row the coloured cells are numbered 1, 2, 3, ... from left to right (numbers above 9 stay 9), the cell's colour replaced by its number as a digit; background stays 0.", gi_25, tf_25, digits=True)


# ---------- 26 ----------
def gi_26(rng): return gen_b(rng, lmax=5)
def tf_26(g):
    out = [r[:] for r in g]
    for y, r in enumerate(g):
        rs = _runs(r)
        if len(rs) >= 2:
            (c1, s1, l1), (c2, s2, l2) = rs[0], rs[-1]
            for i in range(l1): out[y][s1 + i] = c2
            for i in range(l2): out[y][s2 + i] = c1
    return out
rule("swap_first_and_last_run_colours", "In each row with at least two runs, the first run and the last run (left to right) exchange colours; all other cells are unchanged.", gi_26, tf_26)


# ---------- 27 ----------
def gi_27(rng):
    h, w = _hw(rng); h = min(h, 30); pal = colours(rng, 2)
    return [_mkrow(rng, w, pal, 3, False) for _ in range(h)]
def tf_27(g):
    out = [r[:] for r in g]
    for y, r in enumerate(g):
        rs = _runs(r)
        for (c1, s1, l1), (c2, s2, l2) in zip(rs, rs[1:]):
            if c1 == c2:
                for x in range(s1 + l1, s2): out[y][x] = c1
    return out
rule("bridge_same_colour_runs_in_row", "In each row, whenever two neighbouring runs (no other coloured cell between them) have the same colour, the background cells between them are filled with that colour.", gi_27, tf_27)


# ---------- 28 ----------
def gi_28(rng): return gen_b(rng, lmax=9)
def tf_28(g):
    out = []
    for r in g:
        rs = _runs(r)
        if not rs: out.append([0, 0]); continue
        c, s, l = max(rs, key=lambda x: (x[2], -x[1])); out.append([c, l])
    return out
rule("row_longest_run_colour_length_table", "Output one row per input row with two cells: the colour of that row's longest run (leftmost if tied), then that run's length as a digit; a row with no coloured cell gives 0, 0.", gi_28, tf_28, digits=True)


# ---------- 31 ----------
def gi_31(rng): return gen_a(rng, lmax=5)
def tf_31(g):
    return [_pack(sorted([(c, l) for c, _, l in _runs(r)], key=lambda x: x[0]), len(r)) for r in g]
rule("sort_row_runs_by_colour_value", "In each row the runs are re-ordered by colour value, lowest first (equal colours keep their left-to-right order), and packed against the left edge with exactly one background cell between neighbouring runs.", gi_31, tf_31, digits=True)


# ---------- 34 ----------
def gi_34(rng): return gen_c(rng, dens=0.6)
def tf_34(g):
    out = []
    for r in g:
        w = len(r); k = (w + 1) // 2; out.append(r[:k] + r[:w - k][::-1])
    return out
rule("mirror_left_half_over_right_half", "In each row the cells of the right half are overwritten by the mirror image of the left half (for odd widths the middle cell stays and the left half is the cells before it).", gi_34, tf_34)


# ---------- 35 ----------
def gi_35(rng): return gen_b(rng, lmax=6)
def tf_35(g):
    out = [[0] * len(r) for r in g]
    for y, r in enumerate(g):
        rs = _runs(r)
        m = min(l for _, _, l in rs)
        for c, s, l in rs:
            for i in range(m): out[y][s + i] = c
    return out
rule("trim_runs_to_shortest_in_row", "In each row every run is cut from its right end down to the length of the shortest run in that row; the removed cells become background.", gi_35, tf_35)


# ---------- 37 ----------
def gi_37(rng): return gen_d(rng)
def tf_37(g):
    row = [sum(r[c] for r in g) % 10 for c in range(len(g[0]))]
    return [row] if len(set(row)) > 1 else None
rule("column_digit_sums_mod10_row", "Output one row: for each column, the sum of all its digits modulo 10.", gi_37, tf_37, digits=True)


# ---------- 38 ----------
def gi_38(rng): return gen_d(rng)
def tf_38(g):
    out = [[max(r) - min(r)] for r in g]
    return out if len({x[0] for x in out}) > 1 else None
rule("row_value_range_column", "Output one column: for each row, the largest digit minus the smallest digit in that row.", gi_38, tf_38, digits=True)


# ---------- 39 ----------
def gi_39(rng):
    h, w = _hw(rng, lo=3, hi=10); h = min(h, 30); pal = colours(rng, 3); g = []
    for _ in range(h):
        p = rng.randint(2, min(5, w // 3)); pat = [rng.choice(pal) for _ in range(p)]
        v = rng.randint(2 * p, w - 1); g.append([pat[i % p] if i < v else 0 for i in range(w)])
    return g
def tf_39(g):
    out = []
    for r in g:
        v = max(i for i, x in enumerate(r) if x) + 1
        vis = r[:v]
        q = next((q for q in range(1, v) if all(vis[i] == vis[i + q] for i in range(v - q))), v)
        if q > v // 2: return None
        out.append([vis[i % q] for i in range(len(r))])
    return out
rule("continue_row_period_to_edge", "Each row starts with a repeating pattern that stops at some column, background after it; find the smallest period of the visible part (the cells up to its last coloured cell) and continue the pattern to the right edge.", gi_39, tf_39)


# ---------- 41 ----------
def gi_41(rng): return gen_b(rng, lmax=7, excl=(0, 5))
def tf_41(g):
    out = [r[:] for r in g]
    for y, r in enumerate(g):
        c, s, l = max(_runs(r), key=lambda x: (x[2], -x[1]))
        for i in range(l): out[y][s + i] = 5
    return out
rule("recolour_longest_run_grey_per_row", "In each row the longest run (leftmost if tied) is recoloured grey (5); every other cell is unchanged.", gi_41, tf_41)
