# b012_sequences.py -- rows and columns treated as sequences: sort, dedupe, reverse, encode, align, zip.
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


def _noise(rng, h, w, k=None, dens=None, cols=None):
    cols = cols or colours(rng, k or rng.randint(2, 5))
    dens = dens if dens is not None else rng.uniform(0.3, 0.7)
    return [[rng.choice(cols) if rng.random() < dens else 0 for _ in range(w)] for _ in range(h)]


def _first(r):
    return next((i for i, v in enumerate(r) if v), None)


def _runs(r):
    """Maximal runs of one non-zero colour: list of (colour, start, length)."""
    out, i = [], 0
    while i < len(r):
        if r[i] == 0:
            i += 1; continue
        j = i
        while j < len(r) and r[j] == r[i]:
            j += 1
        out.append((r[i], i, j - i)); i = j
    return out


# 1 sort each row's cells by colour value, empties first.
def gi_sortrow(rng):
    return _noise(rng, *_hw(rng), k=rng.randint(3, 6))
def tf_sortrow(g):
    return [sorted(r) for r in g]
rule("sort_row_cells_ascending", "Each row's cells are sorted left to right by colour number, empty cells first then 1, 2, 3 and so on.", gi_sortrow, tf_sortrow, digits=True)


# 2 sort rows by number of coloured cells.
def gi_sortrows(rng):
    return _noise(rng, *_hw(rng))
def tf_sortrows(g):
    return sorted(g, key=lambda r: sum(1 for v in r if v))
rule("sort_rows_by_cell_count", "The rows are reordered top to bottom from fewest coloured cells to most, ties keeping their original order.", gi_sortrows, tf_sortrows)


# 3 remove duplicate rows, keeping the first occurrence.
def _row_pool(rng, h, w, m):
    pool = []
    while len(pool) < m:
        r = _noise(rng, 1, w, k=rng.randint(2, 4), dens=rng.uniform(0.4, 0.8))[0]
        if any(r) and r not in pool: pool.append(r)
    return pool
def gi_dedup(rng):
    h, w = _hw(rng); m = rng.randint(2, max(2, h // 2)); pool = _row_pool(rng, h, w, m)
    return [rng.choice(pool)[:] for _ in range(h)]
def tf_dedup(g):
    out = []
    for r in g:
        if r not in out: out.append(r[:])
    return out if len(out) < len(g) else None
rule("remove_duplicate_rows", "Every row that is an exact copy of an earlier row is deleted, so each distinct row appears once in its first position.", gi_dedup, tf_dedup)


# 4 reverse every other row.
def gi_revalt(rng):
    return _noise(rng, *_hw(rng))
def tf_revalt(g):
    return [r[::-1] if i % 2 else r[:] for i, r in enumerate(g)]
rule("reverse_every_other_row", "The second, fourth, sixth... rows are mirrored left to right; the other rows stay as they are.", gi_revalt, tf_revalt)


# 5 run-length encode a single row into a two-column table.
def gi_rle(rng):
    w = _n(rng, 5, 16); row = []; prev = 0
    while len(row) < w:
        c = rng.choice([x for x in COLOURS if x != prev]); n = rng.randint(1, min(9, w - len(row)))
        row += [c] * n; prev = c
    return [row]
def tf_rle(g):
    return [[c, n] for c, _, n in _runs(g[0])]
rule("run_length_encode_row", "Each run of one colour in the single row becomes one output row: the run's colour on the left and its length as a digit on the right.", gi_rle, tf_rle, digits=True)


# 6 expand a run-length code (colour, length) into left-aligned bars.
def gi_rld(rng):
    h = _n(rng, 4, 14)
    return [[rng.choice(COLOURS), rng.randint(1, 9)] for _ in range(h)]
def tf_rld(g):
    w = max(r[1] for r in g)
    return [[r[0]] * r[1] + [0] * (w - r[1]) for r in g]
rule("expand_run_length_code_to_bars", "Each input row is a colour and a length digit; output one left-aligned bar per row in that colour and of that length.", gi_rld, tf_rld, digits=True)


# 7 move the first cell of each row to the end.
def gi_firstend(rng):
    return _noise(rng, *_hw(rng))
def tf_firstend(g):
    return [r[1:] + r[:1] for r in g]
rule("first_cell_of_row_to_end", "In every row the leftmost cell is removed and appended at the right end, shifting the rest one cell left.", gi_firstend, tf_firstend)


# 8 each row becomes a 9-cell table of per-colour counts.
def gi_rowhist(rng):
    return _noise(rng, *_hw(rng), k=rng.randint(4, 7), dens=rng.uniform(0.4, 0.7))
def tf_rowhist(g):
    out = []
    for r in g:
        cnt = [sum(1 for v in r if v == c) for c in range(1, 10)]
        if max(cnt) > 9: return None
        out.append(cnt)
    return out
rule("row_colour_count_table", "Each row becomes a nine-cell row whose c-th cell holds, as a digit, how many cells of colour c the row contained.", gi_rowhist, tf_rowhist, digits=True)


# 9 keep only palindrome rows.
def gi_palin(rng):
    h, w = _hw(rng); cols = colours(rng, rng.randint(2, 4)); g = []
    for _ in range(h):
        if rng.random() < 0.5:
            half = [rng.choice(cols) if rng.random() < 0.6 else 0 for _ in range(w // 2)]
            r = half + ([rng.choice(cols + [0])] if w % 2 else []) + half[::-1]
            if not any(r): r[0] = r[-1] = cols[0]
        else:
            r = _noise(rng, 1, w, cols=cols)[0]
        g.append(r)
    return g
def tf_palin(g):
    out = [r[:] for r in g if r == r[::-1]]
    return out if 0 < len(out) < len(g) else None
rule("keep_palindrome_rows", "Only the rows that read the same left to right as right to left are kept, in their original order.", gi_palin, tf_palin)


# 10 align rows so their first coloured cell sits in column 0.
def gi_alignl(rng):
    return _noise(rng, *_hw(rng), dens=rng.uniform(0.2, 0.5))
def tf_alignl(g):
    out = []
    for r in g:
        k = _first(r); out.append(r[:] if k is None else r[k:] + [0] * k)
    return out
rule("align_rows_to_first_coloured_cell", "Every row slides left, without wrapping, until its first coloured cell is against the left edge.", gi_alignl, tf_alignl)


# 11 interleave the rows of the top half with the rows of the bottom half.
def gi_ilv(rng):
    h, w = _hw(rng); h += h % 2
    return _noise(rng, h, w)
def tf_ilv(g):
    h = len(g) // 2; out = []
    for i in range(h): out += [g[i][:], g[i + h][:]]
    return out
rule("interleave_half_rows", "The rows of the top half and bottom half are shuffled together like cards: first row of the top half, first of the bottom half, second of the top, and so on.", gi_ilv, tf_ilv)


# 12 roll each row right by the index of its first coloured cell.
def gi_rollfirst(rng):
    return _noise(rng, *_hw(rng), dens=rng.uniform(0.2, 0.5))
def tf_rollfirst(g):
    out = []
    for r in g:
        k = _first(r) or 0; out.append(r[len(r) - k:] + r[:len(r) - k] if k else r[:])
    return out
rule("roll_rows_right_by_first_cell_index", "Each row is shifted right, wrapping round, by the column number of its first coloured cell.", gi_rollfirst, tf_rollfirst)


# 13 each row replaced by its distinct colours in ascending order, packed left.
def gi_distinct(rng):
    return _noise(rng, *_hw(rng), k=rng.randint(3, 7))
def tf_distinct(g):
    w = len(g[0]); out = []
    for r in g:
        d = sorted(set(v for v in r if v)); out.append(d + [0] * (w - len(d)))
    return out
rule("row_distinct_colours_packed_left", "Each row is replaced by the list of colours it contains, each once, in increasing colour order, packed against the left edge.", gi_distinct, tf_distinct)


# 14 the left column of digits picks the rows: keep rows marked 1, drop rows marked 2.
def gi_select(rng):
    h, w = _hw(rng); g = _noise(rng, h, w, cols=colours(rng, rng.randint(2, 4), exclude=(0, 1, 2)))
    marks = [rng.choice([1, 2]) for _ in range(h)]
    if len(set(marks)) < 2: marks[0], marks[1] = 1, 2
    for r, m in zip(g, marks): r[0] = m
    return g
def tf_select(g):
    return [r[1:] for r in g if r[0] == 1]
rule("left_digit_column_selects_rows", "The left column holds a 1 or a 2 per row; only the rows marked 1 survive, with the marker column removed.", gi_select, tf_select)


# 15 the top row's pattern is copied into every row with a grey marker at its left.
def gi_copytop(rng):
    h, w = _hw(rng, 6, 16); cols = colours(rng, rng.randint(2, 4), exclude=(0, 5))
    g = _noise(rng, h, w, cols=cols, dens=rng.uniform(0.3, 0.6)); g[0] = [0] + [rng.choice(cols) for _ in range(w - 1)]
    marks = [i for i in range(1, h) if rng.random() < 0.4] or [rng.randint(1, h - 1)]
    for i in range(1, h): g[i][0] = 5 if i in marks else 0
    return g
def tf_copytop(g):
    return [g[0][:]] + [[5] + g[0][1:] if r[0] == 5 else r[:] for r in g[1:]]
rule("copy_top_row_into_marked_rows", "Every row with a grey marker in its left cell is overwritten with the top row's pattern; unmarked rows are left alone.", gi_copytop, tf_copytop)


# 16 one cell per row; shift rows so the cells form the main diagonal.
def gi_diag(rng):
    h = _n(rng, 5, 14); w = rng.randint(h, min(30, h + 10)) if h <= 20 else rng.randint(h, 30)
    g = blank(h, w); cols = colours(rng, rng.randint(2, 5))
    for i in range(h): g[i][rng.randrange(w)] = rng.choice(cols)
    return g
def tf_diag(g):
    h, w = dims(g); out = blank(h, w)
    for i, r in enumerate(g): out[i][i] = r[_first(r)]
    return out
rule("shift_rows_to_form_diagonal", "Each row holds one cell; every row slides so its cell lands on the main diagonal, row i's cell in column i.", gi_diag, tf_diag)


# 17 stable sort of columns by the colour of their top cell.
def gi_sortcols(rng):
    h, w = _hw(rng); g = _noise(rng, h, w, k=rng.randint(3, 6))
    g[0] = [rng.choice(COLOURS) for _ in range(w)]
    return g
def tf_sortcols(g):
    cols = sorted(transpose(g), key=lambda c: c[0])
    return transpose(cols)
rule("sort_columns_by_top_cell_colour", "The columns are reordered left to right by the colour number of their top cell, equal colours keeping their original order.", gi_sortcols, tf_sortcols, digits=True)


# 18 de-interleave columns: even columns to the left block, odd to the right.
def gi_deilvc(rng):
    return _noise(rng, *_hw(rng))
def tf_deilvc(g):
    return [r[0::2] + r[1::2] for r in g]
rule("deinterleave_columns_even_odd", "The first, third, fifth... columns are gathered on the left and the second, fourth, sixth... columns on the right, each group keeping its order.", gi_deilvc, tf_deilvc)


# 19 de-interleave rows: even rows on top, odd rows below.
def gi_deilvr(rng):
    return _noise(rng, *_hw(rng))
def tf_deilvr(g):
    return [r[:] for r in g[0::2]] + [r[:] for r in g[1::2]]
rule("deinterleave_rows_even_odd", "The first, third, fifth... rows are stacked on top and the second, fourth, sixth... rows below them, each group keeping its order.", gi_deilvr, tf_deilvr)


# 20 sort rows as sequences (lexicographically).
def gi_lex(rng):
    return _noise(rng, *_hw(rng), k=rng.randint(2, 4), dens=rng.uniform(0.5, 0.9))
def tf_lex(g):
    return sorted(r[:] for r in g)
rule("sort_rows_lexicographically", "The rows are put in dictionary order: compared cell by cell from the left, the row with the lower colour at the first difference comes first.", gi_lex, tf_lex)


# 21 sort rows by the colour of their first coloured cell.
def gi_sortfirstcol(rng):
    return _noise(rng, *_hw(rng), k=rng.randint(3, 7))
def tf_sortfirstcol(g):
    return sorted((r[:] for r in g), key=lambda r: r[_first(r)] if _first(r) is not None else 0)
rule("sort_rows_by_leading_colour", "The rows are reordered by the colour number of each row's first coloured cell, lowest on top; empty rows go first and ties keep their order.", gi_sortfirstcol, tf_sortfirstcol, digits=True)


# 22 reverse the order of a row's coloured cells while empties stay put.
def gi_revcells(rng):
    return _noise(rng, *_hw(rng), k=rng.randint(3, 6))
def tf_revcells(g):
    out = []
    for r in g:
        vals = [v for v in r if v][::-1]; it = iter(vals)
        out.append([next(it) if v else 0 for v in r])
    return out
rule("reverse_coloured_cells_in_place", "In each row the coloured cells swap colours so their left-to-right sequence is reversed, while the empty cells stay exactly where they are.", gi_revcells, tf_revcells)


# 23 stable sort of columns by number of coloured cells.
def gi_sortcolcnt(rng):
    return _noise(rng, *_hw(rng))
def tf_sortcolcnt(g):
    return transpose(sorted(transpose(g), key=lambda c: sum(1 for v in c if v)))
rule("sort_columns_by_cell_count", "The columns are reordered left to right from fewest coloured cells to most, ties keeping their original order.", gi_sortcolcnt, tf_sortcolcnt)


# 24 collapse each row's runs to single cells, packed left.
def gi_collapse(rng):
    return _noise(rng, *_hw(rng), k=rng.randint(2, 4), dens=rng.uniform(0.6, 0.95))
def tf_collapse(g):
    w = len(g[0]); out = []
    for r in g:
        seq = [c for c, _, _ in _runs(r)]; out.append(seq + [0] * (w - len(seq)))
    return out
rule("collapse_row_runs_packed_left", "Reading each row left to right, every unbroken run of one colour shrinks to a single cell and the cells are packed against the left edge.", gi_collapse, tf_collapse)


# 25 swap each pair of adjacent rows.
def gi_swappairs(rng):
    h, w = _hw(rng); h += h % 2
    return _noise(rng, h, w)
def tf_swappairs(g):
    out = []
    for i in range(0, len(g), 2): out += [g[i + 1][:], g[i][:]]
    return out
rule("swap_adjacent_row_pairs", "Rows are taken in pairs from the top and the two rows of each pair trade places.", gi_swappairs, tf_swappairs)


# 26 reverse the row order inside each half.
def gi_revhalves(rng):
    return _noise(rng, *_hw(rng))
def tf_revhalves(g):
    h = len(g) // 2
    return [r[:] for r in g[:h][::-1]] + [r[:] for r in g[h:][::-1]]
rule("reverse_row_order_within_halves", "The top half's rows are flipped top to bottom and so are the bottom half's rows, each half staying in its own place.", gi_revhalves, tf_revhalves)


# 27 sort each column's cells descending so the high colours rise to the top.
def gi_sortcolcells(rng):
    return _noise(rng, *_hw(rng), k=rng.randint(3, 6))
def tf_sortcolcells(g):
    return transpose([sorted(c, reverse=True) for c in transpose(g)])
rule("sort_column_cells_descending", "Each column's cells are sorted top to bottom from the highest colour number down to the lowest, with empty cells at the bottom.", gi_sortcolcells, tf_sortcolcells, digits=True)


# 28 sort rows by how many distinct colours they hold.
def gi_sortdistinct(rng):
    return _noise(rng, *_hw(rng), k=rng.randint(3, 7), dens=rng.uniform(0.2, 0.6))
def tf_sortdistinct(g):
    return sorted((r[:] for r in g), key=lambda r: len(set(v for v in r if v)))
rule("sort_rows_by_distinct_colour_count", "The rows are reordered top to bottom from fewest different colours to most, ties keeping their original order.", gi_sortdistinct, tf_sortdistinct)


# 29 keep only rows that occur more than once.
def gi_repeated(rng):
    h, w = _hw(rng, 6, 16); m = rng.randint(2, max(2, h // 3)); pool = _row_pool(rng, h, w, m + h)
    g = [rng.choice(pool[:m])[:] for _ in range(h)]
    for i in rng.sample(range(h), rng.randint(1, max(1, h // 3))): g[i] = pool[m + i][:]
    return g
def tf_repeated(g):
    out = [r[:] for r in g if g.count(r) > 1]
    return out if 0 < len(out) < len(g) else None
rule("keep_only_repeated_rows", "Rows that appear only once are deleted; every row that has at least one exact duplicate elsewhere is kept, duplicates included.", gi_repeated, tf_repeated)


# 30 remove duplicate columns, keeping the first occurrence.
def gi_dedupcols(rng):
    h, w = _hw(rng); m = rng.randint(2, max(2, w // 2)); pool = _row_pool(rng, w, h, m)
    return transpose([rng.choice(pool)[:] for _ in range(w)])
def tf_dedupcols(g):
    out = []
    for c in transpose(g):
        if c not in out: out.append(c)
    return transpose(out) if len(out) < len(g[0]) else None
rule("remove_duplicate_columns", "Every column that is an exact copy of a column further left is deleted, so each distinct column appears once in its first position.", gi_dedupcols, tf_dedupcols)


# 31 the rows repeat with a common period; crop to one period.
def gi_period(rng):
    p = rng.randint(2, 6); w = _n(rng, max(5, 2 * p), 16); h = _n(rng, 4, 14)
    if w < 2 * p: w = 2 * p
    cols = colours(rng, rng.randint(2, 4)); g = []
    for _ in range(h):
        pat = [rng.choice(cols) if rng.random() < 0.7 else 0 for _ in range(p)]
        g.append([pat[i % p] for i in range(w)])
    return g
def tf_period(g):
    w = len(g[0])
    for q in range(2, w):
        if all(r[i] == r[i - q] for r in g for i in range(q, w)):
            return [r[:q] for r in g]
    return None
rule("crop_to_row_period", "Every row repeats the same block of cells over and over; output just the first copy of that block, the shortest period shared by all rows.", gi_period, tf_period)


# 32 each row holds exactly two colours; they trade places.
def gi_swap2(rng):
    h, w = _hw(rng); g = []
    for _ in range(h):
        a, b = colours(rng, 2); r = [rng.choice([a, b]) if rng.random() < 0.6 else 0 for _ in range(w)]
        i, j = rng.sample(range(w), 2); r[i], r[j] = a, b
        g.append(r)
    return g
def tf_swap2(g):
    out = []
    for r in g:
        a, b = sorted(set(v for v in r if v)); out.append([b if v == a else a if v == b else 0 for v in r])
    return out
rule("swap_two_colours_in_each_row", "Each row uses exactly two colours; within the row every cell of one colour becomes the other colour and vice versa.", gi_swap2, tf_swap2)


# 33 align rows so their last coloured cell sits against the right edge.
def gi_alignr(rng):
    return _noise(rng, *_hw(rng), dens=rng.uniform(0.2, 0.5))
def tf_alignr(g):
    w = len(g[0]); out = []
    for r in g:
        k = _first(r[::-1]); out.append(r[:] if k is None else [0] * k + r[:w - k])
    return out
rule("align_rows_to_last_coloured_cell", "Every row slides right, without wrapping, until its last coloured cell is against the right edge.", gi_alignr, tf_alignr)


# 34 zip each pair of rows cell by cell into one row of double width.
def gi_zip(rng):
    h = _n(rng, 4, 14); h += h % 2; w = rng.randint(3, 15)
    return _noise(rng, h, w)
def tf_zip(g):
    return [[v for pair in zip(g[i], g[i + 1]) for v in pair] for i in range(0, len(g), 2)]
rule("zip_row_pairs_into_one_row", "Each pair of rows is merged into a single row twice as wide by alternating cells: first cell of the upper row, first of the lower, second of the upper, and so on.", gi_zip, tf_zip)


# 35 unzip each row into two rows: even-position cells, then odd-position cells.
def gi_unzip(rng):
    h = rng.randint(3, 15); w = _n(rng, 6, 16); w += w % 2
    return _noise(rng, h, w)
def tf_unzip(g):
    return [half for r in g for half in (r[0::2], r[1::2])]
rule("unzip_rows_even_odd_cells", "Each row splits into two rows half as wide: its first, third, fifth... cells on top and its second, fourth, sixth... cells beneath.", gi_unzip, tf_unzip)


# 36 each row becomes a bar as long as its number of runs, in the row's colour.
def gi_runbar(rng):
    h, w = _hw(rng); cols = colours(rng, rng.randint(2, 5))
    return [[c if rng.random() < 0.5 else 0 for c in [rng.choice(cols)] * w] for _ in range(h)]
def tf_runbar(g):
    w = len(g[0]); out = []
    for r in g:
        rs = _runs(r); out.append([rs[0][0]] * len(rs) + [0] * (w - len(rs)) if rs else [0] * w)
    return out
rule("row_run_count_bar", "Each one-colour row is replaced by a left-aligned bar of that colour with one cell per separate run of cells the row had.", gi_runbar, tf_runbar)


# 37 sort rows by the column of their first coloured cell.
def gi_sortfirstpos(rng):
    return _noise(rng, *_hw(rng), dens=rng.uniform(0.15, 0.4))
def tf_sortfirstpos(g):
    w = len(g[0])
    return sorted((r[:] for r in g), key=lambda r: _first(r) if _first(r) is not None else w)
rule("sort_rows_by_first_cell_position", "The rows are reordered so the row whose first coloured cell is furthest left comes on top, ties keeping their order and empty rows going last.", gi_sortfirstpos, tf_sortfirstpos)


# 38 rows with a grey marker on the left are mirrored.
def gi_revmarked(rng):
    h, w = _hw(rng); g = _noise(rng, h, w, cols=colours(rng, rng.randint(2, 4), exclude=(0, 5)))
    marks = [i for i in range(h) if rng.random() < 0.4] or [rng.randrange(h)]
    for i in range(h): g[i][0] = 5 if i in marks else 0
    return g
def tf_revmarked(g):
    return [[5] + r[1:][::-1] if r[0] == 5 else r[:] for r in g]
rule("reverse_rows_with_left_grey_marker", "Every row whose left cell is grey has the rest of the row mirrored left to right; rows without the marker are unchanged.", gi_revmarked, tf_revmarked)


# 39 roll each row so its one grey cell comes first.
def gi_rollgrey(rng):
    h, w = _hw(rng); g = _noise(rng, h, w, cols=colours(rng, rng.randint(2, 4), exclude=(0, 5)))
    for r in g: r[rng.randrange(w)] = 5
    return g
def tf_rollgrey(g):
    return [r[r.index(5):] + r[:r.index(5)] for r in g]
rule("roll_rows_to_put_grey_first", "Each row is rotated, wrapping round, until its single grey cell is in the leftmost column.", gi_rollgrey, tf_rollgrey)


# 40 only the longest run(s) in each row survive.
def gi_longestrun(rng):
    return _noise(rng, *_hw(rng), k=rng.randint(2, 4), dens=rng.uniform(0.6, 0.9))
def tf_longestrun(g):
    out = []
    for r in g:
        rs = _runs(r); m = max((n for _, _, n in rs), default=0); nr = [0] * len(r)
        for c, s, n in rs:
            if n == m: nr[s:s + n] = [c] * n
        out.append(nr)
    return out
rule("keep_longest_run_per_row", "In each row only the longest unbroken run of one colour is kept in place (all of them if tied); every other cell is erased.", gi_longestrun, tf_longestrun)
