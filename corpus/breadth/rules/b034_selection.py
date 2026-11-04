# b034_selection.py -- selecting rows, columns and cells by property; output ONLY the selection.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


def _hw(rng, lo=5, hi=16, big=0.35):
    """Both sides 21-30 about a third of the time, else lo..hi."""
    if rng.random() < big:
        return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _n(rng, lo=5, hi=16, big=0.35):
    return rng.randint(21, 30) if rng.random() < big else rng.randint(lo, hi)


def _noise(rng, h, w, k=None, dens=None, cols=None, exclude=(0,)):
    cols = cols or colours(rng, k or rng.randint(2, 5), exclude=exclude)
    dens = dens if dens is not None else rng.uniform(0.3, 0.7)
    return [[rng.choice(cols) if rng.random() < dens else 0 for _ in range(w)] for _ in range(h)]


def _ndist(r):
    return len(set(v for v in r if v))


# 1 keep only the rows that contain exactly two distinct colours.
def gi_two_colour_rows(rng):
    h, w = _hw(rng, 6, 18); cols = colours(rng, rng.randint(3, 6)); g = []
    for _ in range(h):
        k = rng.choice([1, 2, 2, 3, 3])
        rc = rng.sample(cols, min(k, len(cols)))
        g.append([rng.choice(rc) if rng.random() < 0.7 else 0 for _ in range(w)])
    return g
def tf_two_colour_rows(g):
    out = [r[:] for r in g if _ndist(r) == 2]
    return out if 0 < len(out) < len(g) else None
rule("two_colour_rows_only", "Output only the rows that contain exactly two distinct colours, in their original order.", gi_two_colour_rows, tf_two_colour_rows)


# 2 keep only the columns whose top and bottom cells are the same non-zero colour.
def gi_columns_top_bottom_match(rng):
    h, w = _hw(rng, 6, 18); g = _noise(rng, h, w, k=rng.randint(3, 6))
    for c in range(w):
        if rng.random() < 0.5:
            v = rng.choice([x for x in COLOURS])
            g[0][c] = v; g[h - 1][c] = v
    return g
def tf_columns_top_bottom_match(g):
    h, w = dims(g)
    keep = [c for c in range(w) if g[0][c] != 0 and g[0][c] == g[h - 1][c]]
    if not (0 < len(keep) < w): return None
    return [[r[c] for c in keep] for r in g]
rule("columns_top_bottom_match", "Output only the columns whose top cell and bottom cell are the same non-empty colour.", gi_columns_top_bottom_match, tf_columns_top_bottom_match)


# 3 keep only the rows that are identical to the row directly above them.
def gi_rows_identical_above(rng):
    h, w = _hw(rng, 6, 18); cols = colours(rng, rng.randint(2, 5))
    rows = [_noise(rng, 1, w, cols=cols, dens=rng.uniform(0.3, 0.7))[0]]
    for _ in range(h - 1):
        rows.append(rows[-1][:] if rng.random() < 0.35 else _noise(rng, 1, w, cols=cols, dens=rng.uniform(0.3, 0.7))[0])
    return rows
def tf_rows_identical_above(g):
    out = [g[i][:] for i in range(1, len(g)) if g[i] == g[i - 1]]
    return out if out else None
rule("rows_identical_to_row_above", "Output only the rows that are an exact copy of the row immediately above them.", gi_rows_identical_above, tf_rows_identical_above)


# 4 keep the single row with the most distinct colours.
def gi_row_most_distinct(rng):
    h, w = _hw(rng, 6, 18); cols = colours(rng, rng.randint(4, 7)); g = []
    for _ in range(h):
        k = rng.randint(1, min(len(cols), w))
        rc = rng.sample(cols, k)
        row = [0] * w
        for i, c in enumerate(rng.sample(range(w), k)):
            row[c] = rc[i]
        g.append(row)
    counts_ = [_ndist(r) for r in g]
    return g if counts_.count(max(counts_)) == 1 else None
def tf_row_most_distinct(g):
    best = max(g, key=_ndist)
    return [best[:]]
rule("row_most_distinct_colours", "Output just the single row that contains the greatest number of distinct colours.", gi_row_most_distinct, tf_row_most_distinct)


# 5 keep only the columns that have no empty (background) cells.
def gi_columns_no_empty(rng):
    h, w = _hw(rng, 6, 18); g = _noise(rng, h, w, k=rng.randint(2, 5), dens=rng.uniform(0.4, 0.75))
    for c in range(w):
        if rng.random() < 0.4:
            col = rng.choice(COLOURS)
            for r in range(h): g[r][c] = col
    return g
def tf_columns_no_empty(g):
    h, w = dims(g)
    keep = [c for c in range(w) if all(r[c] != 0 for r in g)]
    if not (0 < len(keep) < w): return None
    return [[r[c] for c in keep] for r in g]
rule("columns_no_empty_cells", "Output only the columns that are completely filled, with no empty cells anywhere in them.", gi_columns_no_empty, tf_columns_no_empty)


# 6 within each row, keep only cells that are the sole cell of their colour in that row; erase the rest.
def gi_row_unique_colour_cells(rng):
    h, w = _hw(rng, 6, 18)
    return _noise(rng, h, w, k=rng.randint(2, 5), dens=rng.uniform(0.4, 0.75))
def tf_row_unique_colour_cells(g):
    out = []
    for r in g:
        cnt = {}
        for v in r:
            if v: cnt[v] = cnt.get(v, 0) + 1
        out.append([v if v and cnt[v] == 1 else 0 for v in r])
    return out
rule("row_unique_colour_cells_only", "In every row, only the cells whose colour appears exactly once in that row survive; every other cell is erased.", gi_row_unique_colour_cells, tf_row_unique_colour_cells)


# 7 keep only the rows whose count of coloured cells is a prime number (2, 3, 5 or 7).
def gi_rows_prime_count(rng):
    h, w = _hw(rng, 6, 18); col = rng.choice(COLOURS); g = blank(h, w)
    for r in range(h):
        k = rng.choice([0, 1, 2, 3, 4, 5, 6, 7, 8])
        k = min(k, w)
        for c in rng.sample(range(w), k): g[r][c] = col
    return g
def tf_rows_prime_count(g):
    primes = {2, 3, 5, 7}
    out = [r[:] for r in g if sum(1 for v in r if v) in primes]
    return out if 0 < len(out) < len(g) else None
rule("rows_prime_cell_count", "Output only the rows whose number of coloured cells is a prime number: two, three, five or seven.", gi_rows_prime_count, tf_rows_prime_count)


# 8 the rows that contain grey (colour 5) form one contiguous block; cut that block out as a strip.
def gi_grey_block_strip(rng):
    h, w = _hw(rng, 8, 20); g = _noise(rng, h, w, k=rng.randint(2, 5), exclude=(0, 5))
    n = rng.randint(1, max(1, h // 2))
    r0 = rng.randint(0, h - n)
    for r in range(r0, r0 + n):
        c = rng.randrange(w); g[r][c] = 5
    return g
def tf_grey_block_strip(g):
    rows = [i for i, r in enumerate(g) if 5 in r]
    if not rows or rows != list(range(rows[0], rows[-1] + 1)): return None
    out = [g[i][:] for i in rows]
    return out if len(out) < len(g) else None
rule("grey_block_strip_cut", "Find the contiguous block of rows that contain any grey cell and output just that strip.", gi_grey_block_strip, tf_grey_block_strip)


# 9 keep columns alternately starting from the first non-empty column (keep, drop, keep, drop...).
def gi_alt_columns(rng):
    h, w = _hw(rng, 8, 20); g = _noise(rng, h, w, k=rng.randint(2, 5))
    pad = rng.randint(0, 2)
    for c in range(pad):
        for r in range(h): g[r][c] = 0
    return g if pad < w - 2 else None
def tf_alt_columns(g):
    h, w = dims(g)
    start = next((c for c in range(w) if any(r[c] for r in g)), None)
    if start is None: return None
    keep = [c for c in range(start, w) if (c - start) % 2 == 0]
    if not (0 < len(keep) < w): return None
    return [[r[c] for c in keep] for r in g]
rule("alternating_columns_from_first_nonempty", "Starting at the first column that has any colour, keep every other column (keep, drop, keep, drop) and output the kept ones.", gi_alt_columns, tf_alt_columns)


# 10 output the central three rows of the grid.
def gi_central_three(rng):
    h = _n(rng, 7, 20); w = rng.randint(4, 16)
    return _noise(rng, h, w, k=rng.randint(2, 5))
def tf_central_three(g):
    h = len(g)
    if h < 5: return None
    mid = h // 2
    return [g[mid - 1][:], g[mid][:], g[mid + 1][:]]
rule("central_three_rows", "Output only the three rows at the vertical centre of the grid.", gi_central_three, tf_central_three)


# 11 two rows are marked grey; output the rows strictly between them.
def gi_rows_between_grey(rng):
    h, w = _hw(rng, 8, 20); g = _noise(rng, h, w, k=rng.randint(2, 5), exclude=(0, 5))
    a, b = sorted(rng.sample(range(h), 2))
    if b - a < 2: return None
    for row, idx in ((a, 0), (b, 0)):
        g[row] = [0] * w; g[row][idx] = 5
    return g
def tf_rows_between_grey(g):
    marked = [i for i, r in enumerate(g) if 5 in r]
    if len(marked) != 2: return None
    a, b = sorted(marked)
    out = [g[i][:] for i in range(a + 1, b)]
    return out if out else None
rule("rows_between_grey_markers", "Two rows carry a grey marker cell; output only the rows strictly between them.", gi_rows_between_grey, tf_rows_between_grey)


# 12 keep only cells that lie on both a fully-coloured row and a fully-coloured column of one colour.
def gi_cells_row_col_cross(rng):
    h, w = _hw(rng, 8, 20); g = _noise(rng, h, w, k=rng.randint(3, 6), dens=rng.uniform(0.3, 0.5))
    col = rng.choice(COLOURS)
    r = rng.randrange(h); c = rng.randrange(w)
    for x in range(w): g[r][x] = col
    for y in range(h): g[y][c] = col
    return g
def tf_cells_row_col_cross(g):
    h, w = dims(g)
    full_rows = [r for r in range(h) if len(set(g[r])) == 1 and g[r][0] != 0]
    full_cols = [c for c in range(w) if len(set(g[r][c] for r in range(h))) == 1 and g[0][c] != 0]
    out = blank(h, w)
    for r in full_rows:
        for c in full_cols:
            out[r][c] = g[r][c]
    return out if any(v for row in out for v in row) and out != g else None
rule("cells_on_colour_cross_lines", "A cell survives only if it sits on BOTH a row of a single colour and a column of a single colour; every other cell is erased.", gi_cells_row_col_cross, tf_cells_row_col_cross)


# 13 sort rows by number of coloured cells descending, keep only the top k where k = number of distinct colours in the grid.
def gi_top_k_rows(rng):
    h, w = _hw(rng, 8, 20); cols = colours(rng, rng.randint(2, 5)); g = blank(h, w)
    for r in range(h):
        col = rng.choice(cols)
        k = rng.randint(0, w)
        for c in rng.sample(range(w), k): g[r][c] = col
    return g if len(set(cols)) < h else None
def tf_top_k_rows(g):
    k = len(set(v for row in g for v in row if v))
    if not (0 < k < len(g)): return None
    ordered = sorted(g, key=lambda r: -sum(1 for v in r if v))
    return [r[:] for r in ordered[:k]]
rule("top_k_rows_by_density", "Count the distinct colours k in the grid; output the k rows with the most coloured cells, most first.", gi_top_k_rows, tf_top_k_rows)


# 14 a single grey cell marks a point; output the cross of its full row and column.
def gi_cross_single_grey(rng):
    h, w = _hw(rng, 7, 18); g = _noise(rng, h, w, k=rng.randint(2, 5), exclude=(0, 5))
    g[rng.randrange(h)][rng.randrange(w)] = 5
    return g
def tf_cross_single_grey(g):
    pos = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v == 5]
    if len(pos) != 1: return None
    r0, c0 = pos[0]; h, w = dims(g)
    out = blank(h, w)
    for c in range(w): out[r0][c] = g[r0][c]
    for r in range(h): out[r][c0] = g[r][c0]
    return out
rule("cross_through_single_grey_cell", "A single grey cell marks a point; output just its full row and its full column, everything else erased.", gi_cross_single_grey, tf_cross_single_grey)


# 15 keep only columns that are the exact mirror of another column (its vertical twin elsewhere in the grid).
def gi_mirror_matching_columns(rng):
    h, w = _hw(rng, 6, 18); g = _noise(rng, h, w, k=rng.randint(2, 5), dens=rng.uniform(0.4, 0.7))
    if w < 4: return None
    pairs = rng.randint(1, max(1, w // 3))
    used = set()
    for _ in range(pairs):
        a, b = rng.sample([c for c in range(w) if c not in used], 2)
        col = [g[r][a] for r in range(h)]
        for r in range(h): g[r][b] = col[r]
        used |= {a, b}
    return g
def tf_mirror_matching_columns(g):
    h, w = dims(g)
    colvals = [[g[r][c] for r in range(h)] for c in range(w)]
    keep = sorted({c for c in range(w) for c2 in range(w) if c != c2 and colvals[c] == colvals[c2]})
    if not (0 < len(keep) < w): return None
    return [[r[c] for c in keep] for r in g]
rule("mirror_matching_columns_only", "Output only the columns that have an exact duplicate elsewhere in the grid; columns with no twin are dropped.", gi_mirror_matching_columns, tf_mirror_matching_columns)


# 16 keep only the single column with the most distinct colours.
def gi_column_most_distinct(rng):
    h, w = _hw(rng, 6, 18); cols = colours(rng, rng.randint(4, 7)); g = blank(h, w)
    for c in range(w):
        k = rng.randint(1, min(len(cols), h))
        rc = rng.sample(cols, k)
        for i, r in enumerate(rng.sample(range(h), k)): g[r][c] = rc[i]
    counts_ = [len(set(g[r][c] for r in range(h) if g[r][c])) for c in range(w)]
    return g if counts_.count(max(counts_)) == 1 else None
def tf_column_most_distinct(g):
    h, w = dims(g)
    best_c = max(range(w), key=lambda c: len(set(g[r][c] for r in range(h) if g[r][c])))
    return [[row[best_c]] for row in g]
# column_most_distinct_colours dropped 2026-10-12 (trio review: behavioural duplicate or one global operation)
# 17 keep only columns where one colour makes up a strict majority of that column's coloured cells.
def gi_columns_majority_colour(rng):
    h, w = _hw(rng, 8, 20); cols = colours(rng, rng.randint(2, 4)); g = blank(h, w)
    for c in range(w):
        maj = rng.choice(cols)
        for r in range(h):
            if rng.random() < 0.8:
                g[r][c] = maj if rng.random() < 0.65 else rng.choice(cols)
    return g
def tf_columns_majority_colour(g):
    h, w = dims(g)
    keep = []
    for c in range(w):
        vals = [g[r][c] for r in range(h) if g[r][c]]
        if not vals: continue
        cnt = {}
        for v in vals: cnt[v] = cnt.get(v, 0) + 1
        top = max(cnt.values())
        if top > len(vals) / 2: keep.append(c)
    if not (0 < len(keep) < w): return None
    return [[r[c] for c in keep] for r in g]
rule("columns_majority_colour_only", "Output only the columns where more than half of the coloured cells share one colour.", gi_columns_majority_colour, tf_columns_majority_colour)


# 18 keep only rows that use a single colour (apart from background).
def gi_monochrome_rows(rng):
    h, w = _hw(rng, 6, 18); cols = colours(rng, rng.randint(2, 5)); g = []
    for _ in range(h):
        if rng.random() < 0.45:
            c = rng.choice(cols)
            g.append([c if rng.random() < 0.7 else 0 for _ in range(w)])
        else:
            g.append(_noise(rng, 1, w, cols=cols, dens=rng.uniform(0.4, 0.7))[0])
    return g
def tf_monochrome_rows(g):
    out = [r[:] for r in g if _ndist(r) == 1]
    return out if 0 < len(out) < len(g) else None
rule("monochrome_rows_only", "Output only the rows that use exactly one non-empty colour throughout.", gi_monochrome_rows, tf_monochrome_rows)


# 19 within each row, keep only cells matching that row's most common non-empty colour; erase the rest.
def gi_cells_equal_row_mode(rng):
    h, w = _hw(rng, 6, 18)
    return _noise(rng, h, w, k=rng.randint(2, 5), dens=rng.uniform(0.4, 0.75))
def tf_cells_equal_row_mode(g):
    out = []
    for r in g:
        cnt = {}
        for v in r:
            if v: cnt[v] = cnt.get(v, 0) + 1
        if not cnt:
            out.append(r[:]); continue
        mode = max(cnt.items(), key=lambda kv: kv[1])[0]
        out.append([v if v == mode else 0 for v in r])
    return out if out != g else None
rule("cells_equal_to_row_mode", "In every row, only the cells whose colour is that row's most common colour survive; every other cell is erased.", gi_cells_equal_row_mode, tf_cells_equal_row_mode)


# 20 keep only the rows whose coloured-cell count is strictly above the grid's average.
def gi_rows_above_average(rng):
    h, w = _hw(rng, 8, 20); col = rng.choice(COLOURS); g = blank(h, w)
    for r in range(h):
        k = rng.randint(0, w)
        for c in rng.sample(range(w), k): g[r][c] = col
    return g
def tf_rows_above_average(g):
    counts_ = [sum(1 for v in r if v) for r in g]
    avg = sum(counts_) / len(counts_)
    out = [g[i][:] for i, c in enumerate(counts_) if c > avg]
    return out if 0 < len(out) < len(g) else None
rule("rows_above_average_density", "Output only the rows whose number of coloured cells is strictly greater than the grid's average.", gi_rows_above_average, tf_rows_above_average)


# 21 keep only columns whose colour values sum to an even number (digits: colour values ARE numbers here).
def gi_columns_even_sum(rng):
    h, w = _hw(rng, 6, 16); g = blank(h, w)
    for c in range(w):
        for r in range(h):
            if rng.random() < 0.6: g[r][c] = rng.randint(1, 9)
    return g if any(v for row in g for v in row) else None
def tf_columns_even_sum(g):
    h, w = dims(g)
    keep = [c for c in range(w) if sum(g[r][c] for r in range(h)) % 2 == 0]
    if not (0 < len(keep) < w): return None
    return [[r[c] for c in keep] for r in g]
rule("columns_even_colour_sum", "Treat each colour digit as a number; output only the columns whose digits add up to an even total.", gi_columns_even_sum, tf_columns_even_sum, digits=True)


# 22 keep only the rows that have no empty cell (fully coloured rows).
def gi_rows_without_background(rng):
    h, w = _hw(rng, 6, 18); g = _noise(rng, h, w, k=rng.randint(2, 5), dens=rng.uniform(0.4, 0.75))
    for r in range(h):
        if rng.random() < 0.4:
            col = rng.choice(COLOURS)
            g[r] = [col] * w
    return g
def tf_rows_without_background(g):
    out = [r[:] for r in g if 0 not in r]
    return out if 0 < len(out) < len(g) else None
rule("rows_without_background_cell", "Output only the rows that are completely filled with colour and contain no empty cells.", gi_rows_without_background, tf_rows_without_background)


# 23 keep only columns that are identical to the column directly to their left.
def gi_columns_identical_left(rng):
    h, w = _hw(rng, 6, 18); g = _noise(rng, h, w, k=rng.randint(2, 5), dens=rng.uniform(0.4, 0.7))
    if w < 2: return None
    for c in range(1, w):
        if rng.random() < 0.35:
            for r in range(h): g[r][c] = g[r][c - 1]
    return g
def tf_columns_identical_left(g):
    h, w = dims(g)
    keep = [c for c in range(1, w) if all(g[r][c] == g[r][c - 1] for r in range(h))]
    if not keep: return None
    return [[r[c] for c in keep] for r in g]
rule("columns_identical_to_left_neighbour", "Output only the columns that are an exact copy of the column immediately to their left.", gi_columns_identical_left, tf_columns_identical_left)


# 24 keep the single column with the fewest distinct colours (ties broken by leftmost).
def gi_single_column_fewest_colours(rng):
    h, w = _hw(rng, 6, 18); h = max(h, 4); cols = colours(rng, rng.randint(3, 6))
    g = blank(h, w)
    winner = rng.randrange(w)
    for c in range(w):
        k = 2 if c == winner else rng.randint(3, min(len(cols), h))
        rc = rng.sample(cols, k)
        for r in range(h): g[r][c] = rc[r % k]
    return g
def tf_single_column_fewest_colours(g):
    h, w = dims(g)
    best_c = min(range(w), key=lambda c: len(set(g[r][c] for r in range(h))))
    return [[row[best_c]] for row in g]
rule("single_column_fewest_colours", "Output just the single column that uses the fewest distinct colours.", gi_single_column_fewest_colours, tf_single_column_fewest_colours)


# 25 a grey row splits the grid; output only the rows above it.
def gi_rows_above_separator(rng):
    h, w = _hw(rng, 8, 20); g = _noise(rng, h, w, k=rng.randint(2, 5), exclude=(0, 5))
    r0 = rng.randint(1, h - 2)
    g[r0] = [5] * w
    return g
def tf_rows_above_separator(g):
    sep = next((i for i, r in enumerate(g) if all(v == 5 for v in r)), None)
    if sep is None or sep == 0: return None
    return [g[i][:] for i in range(sep)]
rule("rows_above_grey_separator", "A solid grey row splits the grid in two; output only the rows above that separator.", gi_rows_above_separator, tf_rows_above_separator)


# 26 a grey row splits the grid; output only the rows below it.
def gi_rows_below_separator(rng):
    h, w = _hw(rng, 8, 20); g = _noise(rng, h, w, k=rng.randint(2, 5), exclude=(0, 5))
    r0 = rng.randint(1, h - 2)
    g[r0] = [5] * w
    return g
def tf_rows_below_separator(g):
    sep = next((i for i, r in enumerate(g) if all(v == 5 for v in r)), None)
    if sep is None or sep >= len(g) - 1: return None
    return [g[i][:] for i in range(sep + 1, len(g))]
rule("rows_below_grey_separator", "A solid grey row splits the grid in two; output only the rows below that separator.", gi_rows_below_separator, tf_rows_below_separator)


# 27 two full columns of grey mark boundaries; output only the columns strictly between them.
def gi_columns_between_markers(rng):
    h, w = _hw(rng, 8, 20); g = _noise(rng, h, w, k=rng.randint(2, 5), exclude=(0, 5))
    a, b = sorted(rng.sample(range(w), 2))
    if b - a < 2: return None
    for c in (a, b):
        for r in range(h): g[r][c] = 5
    return g
def tf_columns_between_markers(g):
    h, w = dims(g)
    marked = [c for c in range(w) if all(r[c] == 5 for r in g)]
    if len(marked) != 2: return None
    a, b = sorted(marked)
    keep = list(range(a + 1, b))
    if not keep: return None
    return [[r[c] for c in keep] for r in g]
rule("columns_between_marker_columns", "Two solid grey columns mark boundaries; output only the columns strictly between them.", gi_columns_between_markers, tf_columns_between_markers)


# 28 output only the cells on the outer border of the grid.
def gi_border_cells(rng):
    h, w = _hw(rng, 7, 18)
    return _noise(rng, h, w, k=rng.randint(2, 5), dens=rng.uniform(0.3, 0.6))
def tf_border_cells(g):
    h, w = dims(g)
    if h < 3 or w < 3: return None
    out = blank(h, w)
    for c in range(w): out[0][c] = g[0][c]; out[h - 1][c] = g[h - 1][c]
    for r in range(h): out[r][0] = g[r][0]; out[r][w - 1] = g[r][w - 1]
    return out
rule("border_cells_only", "Output only the cells on the outer border of the grid; everything inside is erased.", gi_border_cells, tf_border_cells)


# 29 output only the four corner cells of the grid, everything else erased.
def gi_corner_cells(rng):
    h, w = _hw(rng, 7, 18)
    g = _noise(rng, h, w, k=rng.randint(2, 5), dens=rng.uniform(0.3, 0.6))
    for (r, c) in ((0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)):
        if g[r][c] == 0: g[r][c] = rng.choice(COLOURS)
    return g
def tf_corner_cells(g):
    h, w = dims(g)
    if h < 2 or w < 2: return None
    out = blank(h, w)
    for (r, c) in ((0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)):
        out[r][c] = g[r][c]
    return out
rule("corner_cells_only", "Output only the four corner cells of the grid; everything else is erased.", gi_corner_cells, tf_corner_cells)


# 30 keep only the rows at odd row-index positions (1, 3, 5...), dropping the even-indexed rows.
def gi_odd_index_rows(rng):
    h, w = _hw(rng, 6, 18)
    return _noise(rng, h, w, k=rng.randint(2, 5))
def tf_odd_index_rows(g):
    out = [g[i][:] for i in range(1, len(g), 2)]
    return out if out else None
rule("odd_index_rows_only", "Output only the rows at odd positions (second, fourth, sixth...), discarding the rest.", gi_odd_index_rows, tf_odd_index_rows)


# 31 keep every third row, starting from the first.
def gi_every_third_row(rng):
    h = _n(rng, 9, 24); w = rng.randint(4, 16)
    return _noise(rng, h, w, k=rng.randint(2, 5))
def tf_every_third_row(g):
    out = [g[i][:] for i in range(0, len(g), 3)]
    return out if 0 < len(out) < len(g) else None
rule("every_third_row_only", "Output only every third row, starting with the first, discarding the other rows.", gi_every_third_row, tf_every_third_row)


# 32 keep only the rows whose first and last coloured cells share the same colour.
def gi_rows_first_last_match(rng):
    h, w = _hw(rng, 6, 18); g = _noise(rng, h, w, k=rng.randint(2, 5), dens=rng.uniform(0.4, 0.7))
    return g if w >= 2 else None
def tf_rows_first_last_match(g):
    out = [r[:] for r in g if r[0] != 0 and r[0] == r[-1]]
    return out if 0 < len(out) < len(g) else None
rule("rows_first_last_cell_match", "Output only the rows whose leftmost cell and rightmost cell are the same non-empty colour.", gi_rows_first_last_match, tf_rows_first_last_match)


# 33 keep only the columns whose number of distinct colours equals a target shown as a 1x1 key cell's count elsewhere -- simplified: equals the most common per-column colour count.
def gi_columns_colour_count_target(rng):
    h, w = _hw(rng, 8, 20); cols = colours(rng, rng.randint(3, 6)); g = blank(h, w)
    for c in range(w):
        k = rng.randint(1, min(len(cols), h))
        rc = rng.sample(cols, k)
        for r in range(h): g[r][c] = rng.choice(rc) if rng.random() < 0.8 else 0
    return g
def tf_columns_colour_count_target(g):
    h, w = dims(g)
    per_col = [len(set(g[r][c] for r in range(h) if g[r][c])) for c in range(w)]
    tallies = {}
    for v in per_col: tallies[v] = tallies.get(v, 0) + 1
    target = max(tallies.items(), key=lambda kv: kv[1])[0]
    keep = [c for c in range(w) if per_col[c] == target]
    if not (0 < len(keep) < w): return None
    return [[r[c] for c in keep] for r in g]
rule("columns_matching_common_colour_count", "Find the most frequent number of distinct colours per column; output only the columns that have exactly that many distinct colours.", gi_columns_colour_count_target, tf_columns_colour_count_target)


# 34 one colour acts as a key placed once outside the field; output only the rows that contain that key colour.
def gi_rows_containing_key_colour(rng):
    h, w = _hw(rng, 8, 20); cols = colours(rng, rng.randint(3, 6)); key = cols[0]
    g = _noise(rng, h, w, cols=cols, dens=rng.uniform(0.3, 0.55))
    if not any(key in r for r in g):
        g[rng.randrange(h)][rng.randrange(w)] = key
    return g
def tf_rows_containing_key_colour(g):
    key = min(v for row in g for v in row if v)
    out = [r[:] for r in g if key in r]
    return out if 0 < len(out) < len(g) else None
rule("rows_containing_key_colour", "The lowest-numbered colour present is the key; output only the rows that contain at least one cell of that colour.", gi_rows_containing_key_colour, tf_rows_containing_key_colour, digits=True)


# 35 keep only the rows that have at least one exact duplicate elsewhere in the grid.
def gi_duplicate_rows_only(rng):
    h, w = _hw(rng, 8, 20); cols = colours(rng, rng.randint(2, 5))
    pool = []
    while len(pool) < max(2, h // 2):
        r = _noise(rng, 1, w, cols=cols, dens=rng.uniform(0.4, 0.7))[0]
        if any(r): pool.append(r)
    g = []
    for _ in range(h):
        g.append(pool[rng.randrange(len(pool))][:] if rng.random() < 0.6 else _noise(rng, 1, w, cols=cols, dens=rng.uniform(0.4, 0.7))[0])
    return g
def tf_duplicate_rows_only(g):
    cnt = {}
    for r in g: cnt[tuple(r)] = cnt.get(tuple(r), 0) + 1
    out = [r[:] for r in g if cnt[tuple(r)] > 1]
    return out if 0 < len(out) < len(g) else None
# duplicate_rows_only dropped 2026-10-12 (trio review: behavioural duplicate or one global operation)
# 36 within each row, erase the row's majority colour and keep only the minority-coloured cells.
def gi_minority_cells_in_row(rng):
    h, w = _hw(rng, 6, 18); cols = colours(rng, rng.randint(2, 4)); g = []
    for _ in range(h):
        maj = rng.choice(cols); row = []
        for _c in range(w):
            if rng.random() < 0.55: row.append(maj)
            elif rng.random() < 0.6: row.append(rng.choice([c for c in cols if c != maj]))
            else: row.append(0)
        g.append(row)
    return g
def tf_minority_cells_in_row(g):
    out = []
    for r in g:
        cnt = {}
        for v in r:
            if v: cnt[v] = cnt.get(v, 0) + 1
        if not cnt:
            out.append(r[:]); continue
        maj = max(cnt.items(), key=lambda kv: kv[1])[0]
        out.append([v if v and v != maj else 0 for v in r])
    return out if out != g else None
rule("minority_cells_in_row", "In every row, erase the row's most common colour and keep only the less common coloured cells.", gi_minority_cells_in_row, tf_minority_cells_in_row)


# 37 keep only columns that read the same top to bottom as bottom to top (palindromic columns).
def gi_symmetric_columns(rng):
    h, w = _hw(rng, 6, 18); g = _noise(rng, h, w, k=rng.randint(2, 5), dens=rng.uniform(0.4, 0.7))
    for c in range(w):
        if rng.random() < 0.4:
            col = [g[r][c] for r in range(h // 2)]
            for i, v in enumerate(col): g[h - 1 - i][c] = v
            if h % 2: g[h // 2][c] = rng.choice(COLOURS + [0])
    return g
def tf_symmetric_columns(g):
    h, w = dims(g)
    keep = [c for c in range(w) if [g[r][c] for r in range(h)] == [g[h - 1 - r][c] for r in range(h)]]
    if not (0 < len(keep) < w): return None
    return [[r[c] for c in keep] for r in g]
rule("symmetric_columns_only", "Output only the columns that read the same from top to bottom as from bottom to top.", gi_symmetric_columns, tf_symmetric_columns)


# 38 keep only rows whose coloured cells form a single contiguous run (one unbroken block, no gaps).
def gi_rows_single_run(rng):
    h, w = _hw(rng, 7, 18); col = rng.choice(COLOURS); g = blank(h, w)
    for r in range(h):
        if rng.random() < 0.5 and w >= 2:
            a, b = sorted(rng.sample(range(w), 2))
            for c in range(a, b + 1): g[r][c] = col
        else:
            for c in range(w):
                if rng.random() < 0.4: g[r][c] = col
    return g
def tf_rows_single_run(g):
    def is_run(r):
        idx = [i for i, v in enumerate(r) if v]
        return len(idx) >= 1 and idx == list(range(idx[0], idx[-1] + 1))
    out = [r[:] for r in g if is_run(r)]
    return out if 0 < len(out) < len(g) else None
rule("rows_single_contiguous_run_only", "Output only the rows whose coloured cells form one unbroken block with no gaps.", gi_rows_single_run, tf_rows_single_run)


# 39 keep only the columns that use exactly one non-empty colour throughout (monochrome columns).
def gi_monochrome_columns(rng):
    h, w = _hw(rng, 6, 18); cols = colours(rng, rng.randint(2, 5)); g = blank(h, w)
    for c in range(w):
        if rng.random() < 0.45:
            col = rng.choice(cols)
            for r in range(h):
                if rng.random() < 0.7: g[r][c] = col
        else:
            for r in range(h):
                if rng.random() < 0.6: g[r][c] = rng.choice(cols)
    return g
def tf_monochrome_columns(g):
    h, w = dims(g)
    keep = [c for c in range(w) if len(set(g[r][c] for r in range(h) if g[r][c])) == 1]
    if not (0 < len(keep) < w): return None
    return [[r[c] for c in keep] for r in g]
rule("monochrome_columns_only", "Output only the columns that use exactly one non-empty colour throughout.", gi_monochrome_columns, tf_monochrome_columns)


# 40 find the tallest contiguous band of rows sharing the same dominant colour; output just that band.
def gi_widest_band_rows(rng):
    h, w = _hw(rng, 9, 22); cols = colours(rng, rng.randint(3, 6)); g = []
    bands = []
    left = h
    while left > 0:
        n = rng.randint(1, min(4, left)); bands.append(n); left -= n
    if len(set(bands)) < 2 and len(bands) > 1:
        bands[0] += 1; bands[-1] = max(1, bands[-1] - 1)
    for n in bands:
        col = rng.choice(cols)
        for _ in range(n):
            g.append([col if rng.random() < 0.7 else 0 for _ in range(w)])
    return g if len(bands) > 1 else None
def tf_widest_band_rows(g):
    h = len(g)
    def dom(r):
        cnt = {}
        for v in r:
            if v: cnt[v] = cnt.get(v, 0) + 1
        return max(cnt.items(), key=lambda kv: kv[1])[0] if cnt else None
    doms = [dom(r) for r in g]
    best_start, best_len = 0, 0
    i = 0
    while i < h:
        j = i
        while j < h and doms[j] == doms[i] and doms[i] is not None:
            j += 1
        if j - i > best_len:
            best_len = j - i; best_start = i
        i = j if j > i else i + 1
    if best_len == 0 or best_len == h: return None
    return [r[:] for r in g[best_start:best_start + best_len]]
rule("widest_colour_band_rows", "Rows group into contiguous bands sharing one dominant colour; output only the rows of the tallest such band.", gi_widest_band_rows, tf_widest_band_rows)
