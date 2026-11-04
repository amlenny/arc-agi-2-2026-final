# b048_coordinates.py -- coordinates and indexing: rows/columns as addresses, corner digits as
# lookup keys, centroids, rankings and swaps keyed by position. One author, this file only.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


def _sz(rng, lo=5, hi=16, biglo=21, bighi=30, pbig=0.35):
    if rng.random() < pbig:
        return rng.randint(biglo, bighi), rng.randint(biglo, bighi)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _sqsz(rng, lo=5, hi=16, biglo=21, bighi=30, pbig=0.35):
    n = rng.randint(biglo, bighi) if rng.random() < pbig else rng.randint(lo, hi)
    return n, n


def _scene(rng, h, w, k_lo, k_hi, n_lo, n_hi, margin=1, exclude=(0,)):
    g = blank(h, w)
    k = rng.randint(k_lo, k_hi)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    cols = colours(rng, k, exclude=exclude) if k <= 9 - len(exclude) else [rng.choice(COLOURS) for _ in range(k)]
    if place_shapes(rng, g, shapes, cols, margin=margin) is None:
        return None
    return g


# 1 two markers: cell at (row of A, column of B) is filled.
def gi_cell2mark(rng):
    h, w = _sz(rng, 6, 16); g = blank(h, w)
    ra, rb = rng.sample(range(h), 2); ca, cb = rng.sample(range(w), 2)
    g[ra][ca] = 8; g[rb][cb] = 9
    return g
def tf_cell2mark(g):
    (ra, ca), = cells(g, lambda v: v == 8); (rb, cb), = cells(g, lambda v: v == 9)
    out = copy(g); out[ra][cb] = 5
    return out
rule("cell_at_two_marker_coordinates", "The cell at (row of marker A, column of marker B) is filled.", gi_cell2mark, tf_cell2mark)


# 2 swapped roles of the same two markers.
def tf_cell2mark_swap(g):
    (ra, ca), = cells(g, lambda v: v == 8); (rb, cb), = cells(g, lambda v: v == 9)
    out = copy(g); out[rb][ca] = 5
    return out
rule("cell_at_swapped_marker_coordinates", "The cell at (row of marker B, column of marker A) is filled.", gi_cell2mark, tf_cell2mark_swap)


# 3 a digit in the top-left corner names a row to fill.
def gi_cornerrow(rng):
    h, w = _sz(rng, 6, 20, 21, 30, 0.3)
    d = rng.randint(1, min(9, h)); g = blank(h, w); g[0][0] = d
    return g
def tf_cornerrow(g):
    out = copy(g); d = g[0][0]
    for c in range(len(g[0])): out[d - 1][c] = 4
    return out
rule("corner_digit_fills_named_row", "The digit in the top-left corner names a row, which is filled.", gi_cornerrow, tf_cornerrow, digits=True)


# 4 a digit in the corner names a column to fill.
def gi_cornercol(rng):
    h, w = _sz(rng, 6, 20, 21, 30, 0.3)
    d = rng.randint(1, min(9, w)); g = blank(h, w); g[0][0] = d
    return g
def tf_cornercol(g):
    out = copy(g); d = g[0][0]
    for r in range(len(g)): out[r][d - 1] = 4
    return out
rule("corner_digit_fills_named_column", "The digit in the top-left corner names a column, which is filled.", gi_cornercol, tf_cornercol, digits=True)


# 5 a digit pair in the corner names one cell to fill.
def gi_cornerpair(rng):
    h, w = _sz(rng, 6, 20, 21, 30, 0.3)
    if w < 2: return None
    r = rng.randint(1, min(9, h)); c = rng.randint(1, min(9, w))
    g = blank(h, w); g[0][0] = r; g[0][1] = c
    return g
def tf_cornerpair(g):
    out = copy(g); r, c = g[0][0], g[0][1]; out[r - 1][c - 1] = 6
    return out
rule("corner_digit_pair_fills_cell", "Two digits in the top-left corner give a row and a column; that one cell is filled.", gi_cornerpair, tf_cornerpair, digits=True)


# 6 the same digit pair, but it fills the whole row-and-column cross.
def tf_cornerpair_cross(g):
    out = copy(g); r, c = g[0][0], g[0][1]; w = len(g[0])
    for cc in range(w): out[r - 1][cc] = 6
    for rr in range(len(g)): out[rr][c - 1] = 6
    return out
rule("corner_digit_pair_fills_row_and_column_cross", "Two digits in the corner give a row and a column; both are filled entirely.", gi_cornerpair, tf_cornerpair_cross, digits=True)


# 7 objects are moved to the row given by their own colour value.
def gi_rowbyval(rng):
    h, w = _sz(rng, 12, 20, 21, 30, 0.3); h = max(h, 11)
    g = blank(h, w); k = rng.randint(2, 4); cols = colours(rng, k); used = set()
    for c in cols:
        n = rng.randint(2, 4); c0 = rng.randint(0, w - n)
        for _ in range(30):
            r = rng.randrange(h)
            if r not in used: used.add(r); break
        for i in range(n): g[r][c0 + i] = c
    return g
def tf_rowbyval(g):
    h, w = dims(g); out = blank(h, w)
    for c in set(v for row in g for v in row if v):
        pts = cells(g, lambda v, c=c: v == c); t = c - 1
        if 0 <= t < h:
            for r, cc in pts: out[t][cc] = c
    return out
rule("object_row_set_by_colour_value", "Each coloured bar moves straight up or down to the row equal to its own colour.", gi_rowbyval, tf_rowbyval, digits=True)


# 8 objects are moved to the column given by their own colour value.
def gi_colbyval(rng):
    h, w = _sz(rng, 12, 20, 21, 30, 0.3); w = max(w, 11)
    g = blank(h, w); k = rng.randint(2, 4); cols = colours(rng, k); used = set()
    for c in cols:
        n = rng.randint(2, 4); r0 = rng.randint(0, h - n)
        for _ in range(30):
            cc = rng.randrange(w)
            if cc not in used: used.add(cc); break
        for i in range(n): g[r0 + i][cc] = c
    return g
def tf_colbyval(g):
    h, w = dims(g); out = blank(h, w)
    for c in set(v for row in g for v in row if v):
        pts = cells(g, lambda v, c=c: v == c); t = c - 1
        if 0 <= t < w:
            for r, cc in pts: out[r][t] = c
    return out
rule("object_column_set_by_colour_value", "Each coloured bar slides left or right to the column equal to its own colour.", gi_colbyval, tf_colbyval, digits=True)


# 9 a corner digit k picks the k-th object in reading order to recolour.
def gi_readorder(rng):
    h, w = _sz(rng, 9, 18, 21, 30, 0.3); h = max(h, 9)
    inner = blank(h - 1, w); k = rng.randint(2, 5)
    shapes = [random_shape(rng, rng.randint(2, 5)) for _ in range(k)]
    cols = colours(rng, k, exclude=(0, 5))
    if place_shapes(rng, inner, shapes, cols, margin=1) is None: return None
    g = inner + [[0] * w]; g[-1][-1] = rng.randint(1, k)
    return g
def tf_readorder(g):
    sub = g[:-1]; obs = sorted(objects(sub, 0), key=lambda o: bbox(o)[:2])
    d = g[-1][-1]
    if d > len(obs): return None
    out = copy(g)
    for r, c in obs[d - 1]: out[r][c] = 5
    return out
rule("reading_order_digit_recolours_object", "A digit in the bottom-right corner picks the k-th object in reading order, which is recoloured.", gi_readorder, tf_readorder, digits=True)


# 10 same layout, but the k-th object is deleted instead of recoloured.
def tf_readorder_del(g):
    sub = g[:-1]; obs = sorted(objects(sub, 0), key=lambda o: bbox(o)[:2])
    d = g[-1][-1]
    if d > len(obs): return None
    out = copy(g)
    for r, c in obs[d - 1]: out[r][c] = 0
    return out
rule("reading_order_digit_deletes_object", "A digit in the bottom-right corner picks the k-th object in reading order, which is erased.", gi_readorder, tf_readorder_del, digits=True)


# 11 every cell whose row index equals its column index is filled (square grids).
def gi_diag(rng):
    n, _ = _sqsz(rng, 6, 20, 21, 30, 0.3); g = blank(n, n)
    c = rng.choice([x for x in COLOURS if x != 5]); sprinkle(rng, g, rng.randint(0, n), c)
    return g
def tf_diag(g):
    out = copy(g)
    for i in range(len(g)): out[i][i] = 5
    return out
rule("diagonal_row_equals_column_filled", "Every cell whose row index equals its column index is filled.", gi_diag, tf_diag)


# 12 the anti-diagonal (row + column = width - 1) is filled.
def tf_antidiag(g):
    out = copy(g); n = len(g)
    for i in range(n): out[i][n - 1 - i] = 5
    return out
rule("anti_diagonal_filled", "Every cell on the anti-diagonal, where row plus column equals the last index, is filled.", gi_diag, tf_antidiag)


# 13 a corner digit offsets which diagonal (row - column = offset) gets filled.
def gi_offdiag(rng):
    n, _ = _sqsz(rng, 7, 20, 21, 30, 0.3); g = blank(n, n)
    o = rng.randint(0, min(8, n - 2)); g[0][n - 1] = o
    c = rng.choice([x for x in COLOURS if x not in (4, o)])
    sprinkle(rng, g, rng.randint(1, max(1, n - 2)), c)
    return g
def tf_offdiag(g):
    out = copy(g); n = len(g); o = g[0][n - 1]
    for r in range(n):
        c = r - o
        if 0 <= c < n: out[r][c] = 4
    return out
rule("offset_diagonal_by_corner_digit", "A digit in the top-right corner gives an offset; the diagonal row minus column equal to that offset is filled.", gi_offdiag, tf_offdiag, digits=True)


# 14 cells where row + column equals the number of scattered markers are filled.
def gi_rcmarkercount(rng):
    n, _ = _sqsz(rng, 6, 20, 21, 30, 0.3); g = blank(n, n)
    k = rng.randint(1, min(9, 2 * n - 2))
    free = [(r, c) for r in range(n) for c in range(n)]
    for r, c in rng.sample(free, k): g[r][c] = 8
    return g
def tf_rcmarkercount(g):
    n = len(g); cnt = len(cells(g, lambda v: v == 8)); out = copy(g)
    for r in range(n):
        c = cnt - r
        if 0 <= c < n: out[r][c] = 5
    return out
rule("row_plus_column_equals_marker_count_filled", "Cells where row index plus column index equals the number of scattered markers are filled.", gi_rcmarkercount, tf_rcmarkercount)


# 15 lookup: the colour atop column j is painted onto the marker sitting in row j of the left edge.
def gi_collookup(rng):
    h, w = _sz(rng, 6, 16, 21, 30, 0.3); h = max(h, 3); w = max(w, 3)
    g = blank(h, w)
    for j in range(w): g[0][j] = rng.choice([c for c in COLOURS if c != 8])
    m = rng.randint(1, min(4, h - 1, w - 1))
    for r in rng.sample(range(1, min(h, w)), m): g[r][0] = 8
    return g
def tf_collookup(g):
    out = copy(g); w = len(g[0])
    for r in range(1, len(g)):
        if g[r][0] == 8 and r < w: out[r][0] = g[0][r]
    return out
rule("column_top_colour_painted_onto_row_marker", "A marker on the left edge at row j is recoloured with whatever colour sits atop column j.", gi_collookup, tf_collookup)


# 16 two border digit strips (one digit each) address a single cell.
def gi_tworulers(rng):
    h, w = _sz(rng, 6, 20, 21, 30, 0.3); h = max(h, 2); w = max(w, 2)
    rr = rng.randint(1, min(9, h)); cc = rng.randint(1, min(9, w))
    g = blank(h, w); g[0][1] = cc; g[1][0] = rr
    return g
def tf_tworulers(g):
    out = copy(g); cc = g[0][1]; rr = g[1][0]; out[rr - 1][cc - 1] = 5
    return out
rule("two_border_digit_strips_address_cell", "A digit on the top strip and a digit on the left strip together address one cell, which is filled.", gi_tworulers, tf_tworulers, digits=True)


# 17 the object whose top-left corner has the smallest row+column sum is recoloured.
def gi_mincorner(rng):
    h, w = _sz(rng, 8, 18, 21, 30, 0.3)
    g = _scene(rng, h, w, 3, 5, 3, 8, exclude=(0, 6))
    if g is None: return None
    obs = objects(g, 0); sums = sorted(sum(bbox(o)[:2]) for o in obs)
    return g if sums[0] != sums[1] else None
def tf_mincorner(g):
    obs = objects(g, 0); best = min(obs, key=lambda o: sum(bbox(o)[:2])); out = copy(g)
    for r, c in best: out[r][c] = 6
    return out
rule("min_corner_sum_object_recoloured", "The object whose top-left corner has the smallest row-plus-column sum is recoloured.", gi_mincorner, tf_mincorner)


# 18 the object whose top-left corner has the largest row+column sum is recoloured.
def gi_maxcorner(rng):
    h, w = _sz(rng, 8, 18, 21, 30, 0.3)
    g = _scene(rng, h, w, 3, 5, 3, 8, exclude=(0, 7))
    if g is None: return None
    obs = objects(g, 0); sums = sorted(sum(bbox(o)[:2]) for o in obs)
    return g if sums[-1] != sums[-2] else None
def tf_maxcorner(g):
    obs = objects(g, 0); best = max(obs, key=lambda o: sum(bbox(o)[:2])); out = copy(g)
    for r, c in best: out[r][c] = 7
    return out
rule("max_corner_sum_object_recoloured", "The object whose top-left corner has the largest row-plus-column sum is recoloured.", gi_maxcorner, tf_maxcorner)


# 19 two markers in column 0 name two rows; those rows are swapped.
def gi_swaprows(rng):
    h, w = _sz(rng, 6, 18, 21, 30, 0.3); h = max(h, 3)
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.4: g[r][c] = rng.choice([x for x in COLOURS if x not in (8, 9)])
    for _ in range(5):
        r1, r2 = rng.sample(range(h), 2)
        if g[r1] != g[r2]: break
    else:
        return None
    g[r1][0] = 8; g[r2][0] = 8
    return g
def tf_swaprows(g):
    rs = [r for r in range(len(g)) if g[r][0] == 8]
    if len(rs) != 2: return None
    r1, r2 = rs; out = copy(g); out[r1], out[r2] = g[r2][:], g[r1][:]
    return out
rule("swap_two_marked_rows", "The two rows carrying a marker in the left column swap places.", gi_swaprows, tf_swaprows)


# 20 two markers in row 0 name two columns; those columns are swapped.
def gi_swapcols(rng):
    h, w = _sz(rng, 6, 18, 21, 30, 0.3); w = max(w, 3)
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.4: g[r][c] = rng.choice([x for x in COLOURS if x not in (8, 9)])
    for _ in range(5):
        c1, c2 = rng.sample(range(w), 2)
        if [row[c1] for row in g] != [row[c2] for row in g]: break
    else:
        return None
    g[0][c1] = 8; g[0][c2] = 8
    return g
def tf_swapcols(g):
    cs = [c for c in range(len(g[0])) if g[0][c] == 8]
    if len(cs) != 2: return None
    c1, c2 = cs; out = copy(g)
    for row in out: row[c1], row[c2] = row[c2], row[c1]
    return out
rule("swap_two_marked_columns", "The two columns carrying a marker in the top row swap places.", gi_swapcols, tf_swapcols)


# 21 the cell at the centroid of each object is marked.
def gi_centroid(rng):
    h, w = _sz(rng, 8, 18, 21, 30, 0.3)
    return _scene(rng, h, w, 2, 5, 4, 10, exclude=(0, 5))
def tf_centroid(g):
    out = copy(g)
    for o in objects(g, 0):
        rs = [r for r, _ in o]; cs = [c for _, c in o]
        out[sum(rs) // len(rs)][sum(cs) // len(cs)] = 5
    return out
rule("object_centroid_marked", "The cell at the centroid of each object is marked.", gi_centroid, tf_centroid)


# 22 the object covering the grid's centre cell is recoloured.
def gi_centreobj(rng):
    for _ in range(8):
        h, w = rng.randint(7, 14), rng.randint(7, 14)
        g = _scene(rng, h, w, 3, 6, 4, 9, exclude=(0, 9, 8))
        if g is None: continue
        cr, cc = h // 2, w // 2
        for o in objects(g, 0):
            if (cr, cc) in set(o): return g
    return None
def tf_centreobj(g):
    h, w = dims(g); cr, cc = h // 2, w // 2
    owner = next(o for o in objects(g, 0) if (cr, cc) in set(o))
    col = g[owner[0][0]][owner[0][1]]; nc = 9 if col != 9 else 8
    out = copy(g)
    for r, c in owner: out[r][c] = nc
    return out
rule("centre_cell_object_recoloured", "The object that covers the exact centre cell of the grid is recoloured.", gi_centreobj, tf_centreobj)


# 23 objects are recoloured by the parity of their left column index.
def gi_colparity(rng):
    h, w = _sz(rng, 8, 18, 21, 30, 0.3)
    g = _scene(rng, h, w, 3, 6, 3, 8, exclude=(0, 2, 3))
    if g is None: return None
    pars = {bbox(o)[1] % 2 for o in objects(g, 0)}
    return g if len(pars) > 1 else None
def tf_colparity(g):
    out = copy(g)
    for o in objects(g, 0):
        col = 2 if bbox(o)[1] % 2 == 0 else 3
        for r, c in o: out[r][c] = col
    return out
rule("objects_recoloured_by_column_index_parity", "Each object is recoloured by whether its left column index is even or odd.", gi_colparity, tf_colparity)


# 24 objects are recoloured by the parity of their top row index.
def gi_rowparity(rng):
    h, w = _sz(rng, 8, 18, 21, 30, 0.3)
    g = _scene(rng, h, w, 3, 6, 3, 8, exclude=(0, 2, 3))
    if g is None: return None
    pars = {bbox(o)[0] % 2 for o in objects(g, 0)}
    return g if len(pars) > 1 else None
def tf_rowparity(g):
    out = copy(g)
    for o in objects(g, 0):
        col = 2 if bbox(o)[0] % 2 == 0 else 3
        for r, c in o: out[r][c] = col
    return out
rule("objects_recoloured_by_row_index_parity", "Each object is recoloured by whether its top row index is even or odd.", gi_rowparity, tf_rowparity)


# 25 a digit stashed in the bottom-right corner names a row; the object starting on that row is recoloured.
def gi_rowdigitsel(rng):
    h, w = _sz(rng, 9, 18, 21, 30, 0.3); h = max(h, 9)
    inner = blank(h - 1, min(w, 9) if False else w)
    k = rng.randint(2, 5); rows = rng.sample(range(0, min(9, h - 1)), min(k, min(9, h - 1)))
    for i, r0 in enumerate(rows):
        n = rng.randint(2, 4); c0 = rng.randint(0, w - n); col = colours(rng, 1, exclude=(0,))[0]
        for j in range(n): inner[r0][c0 + j] = col
    g = inner + [[0] * w]; g[-1][-1] = rng.choice(rows) + 1
    return g
def tf_rowdigitsel(g):
    d = g[-1][-1]; sub = g[:-1]; obs = objects(sub, 0)
    target = next((o for o in obs if bbox(o)[0] == d - 1), None)
    if target is None: return None
    out = copy(g)
    for r, c in target: out[r][c] = 5
    return out
rule("row_digit_marker_selects_object", "A digit in the bottom-right corner names a row; the object starting on that row is recoloured.", gi_rowdigitsel, tf_rowdigitsel, digits=True)


# 26 a digit stashed in the bottom-right corner names a column; the object starting on that column is recoloured.
def gi_coldigitsel(rng):
    h, w = _sz(rng, 9, 18, 21, 30, 0.3); w = max(w, 9)
    inner = [row[:-1] for row in blank(h, w)]
    k = rng.randint(2, 5); wcols = rng.sample(range(0, min(9, w - 1)), min(k, min(9, w - 1)))
    for c0 in wcols:
        n = rng.randint(2, 4); r0 = rng.randint(0, h - n); col = colours(rng, 1, exclude=(0,))[0]
        for j in range(n): inner[r0 + j][c0] = col
    g = [row + [0] for row in inner]
    for row in g: pass
    g[0][-1] = rng.choice(wcols) + 1
    return g
def tf_coldigitsel(g):
    d = g[0][-1]; sub = [row[:-1] for row in g]; obs = objects(sub, 0)
    target = next((o for o in obs if bbox(o)[1] == d - 1), None)
    if target is None: return None
    out = copy(g)
    for r, c in target: out[r][c] = 5
    return out
rule("column_digit_marker_selects_object", "A digit in the top-right corner names a column; the object starting on that column is recoloured.", gi_coldigitsel, tf_coldigitsel, digits=True)


# 27 the object's own top row index is written as a digit in the top-left corner.
def gi_writetoprow(rng):
    h, w = _sz(rng, 10, 18, 21, 30, 0.3)
    shape = random_shape(rng, rng.randint(3, 6)); mh = max(r for r, _ in shape) + 1
    r0 = rng.randint(0, min(8, h - mh)); c0 = rng.randint(1, w - 1 - max(c for _, c in shape))
    g = blank(h, w); col = rng.choice([x for x in COLOURS if x != 1])
    for r, c in shape: g[r0 + r][c0 + c] = col
    return g
def tf_writetoprow(g):
    obs = objects(g, 0)
    if not obs: return None
    r0 = bbox(obs[0])[0]; out = copy(g); out[0][0] = r0 + 1
    return out if out != g else None
rule("object_top_row_written_as_corner_digit", "The object's own top row index (1-based) is written as a digit in the top-left corner.", gi_writetoprow, tf_writetoprow, digits=True)


# 28 the object's own left column index is written as a digit in the top-left corner.
def gi_writeleftcol(rng):
    h, w = _sz(rng, 10, 18, 21, 30, 0.3)
    shape = random_shape(rng, rng.randint(3, 6)); mw = max(c for _, c in shape) + 1
    c0 = rng.randint(0, min(8, w - mw)); r0 = rng.randint(1, h - 1 - max(r for r, _ in shape))
    g = blank(h, w); col = rng.choice([x for x in COLOURS if x != 1])
    for r, c in shape: g[r0 + r][c0 + c] = col
    return g
def tf_writeleftcol(g):
    obs = objects(g, 0)
    if not obs: return None
    c0 = bbox(obs[0])[1]; out = copy(g); out[0][0] = c0 + 1
    return out if out != g else None
rule("object_left_column_written_as_corner_digit", "The object's own left column index (1-based) is written as a digit in the top-left corner.", gi_writeleftcol, tf_writeleftcol, digits=True)


# 29 two digits in the corner give a row range, which is filled.
def gi_rowrange(rng):
    h, w = _sz(rng, 7, 20, 21, 30, 0.3); h = max(h, 3)
    a, b = sorted(rng.sample(range(1, min(9, h) + 1), 2))
    g = blank(h, w); g[0][0] = a; g[0][1] = b
    return g
def tf_rowrange(g):
    out = copy(g); a, b = g[0][0], g[0][1]
    for r in range(a - 1, b):
        for c in range(len(g[0])): out[r][c] = 4
    return out
rule("corner_digit_names_row_range_filled", "Two digits in the corner give a first and last row; every row in between is filled.", gi_rowrange, tf_rowrange, digits=True)


# 30 two digits in the corner give a column range, which is filled.
def gi_colrange(rng):
    h, w = _sz(rng, 7, 20, 21, 30, 0.3); w = max(w, 3)
    a, b = sorted(rng.sample(range(1, min(9, w) + 1), 2))
    g = blank(h, w); g[0][0] = a; g[0][1] = b
    return g
def tf_colrange(g):
    out = copy(g); a, b = g[0][0], g[0][1]
    for c in range(a - 1, b):
        for r in range(len(g)): out[r][c] = 4
    return out
rule("corner_digit_names_column_range_filled", "Two digits in the corner give a first and last column; every column in between is filled.", gi_colrange, tf_colrange, digits=True)


# 31 objects are ranked by their top row and recoloured 1..k in that order.
def gi_rankrow(rng):
    h, w = _sz(rng, 8, 18, 21, 30, 0.3)
    k = rng.randint(2, 6)
    g = _scene(rng, h, w, k, k, 3, 7)
    if g is None: return None
    obs = objects(g, 0); rows = sorted(bbox(o)[0] for o in obs)
    return g if len(set(rows)) == len(rows) else None
def tf_rankrow(g):
    obs = sorted(objects(g, 0), key=lambda o: bbox(o)[0]); out = copy(g)
    for i, o in enumerate(obs, 1):
        for r, c in o: out[r][c] = i
    return out if out != g else None
# objects_ranked_by_row_recoloured_sequentially dropped 2026-10-12 (trio review: behavioural duplicate or one global operation)
# 32 objects are ranked by their left column and recoloured 1..k in that order.
def gi_rankcol(rng):
    h, w = _sz(rng, 8, 18, 21, 30, 0.3)
    k = rng.randint(2, 6)
    g = _scene(rng, h, w, k, k, 3, 7)
    if g is None: return None
    obs = objects(g, 0); cols = sorted(bbox(o)[1] for o in obs)
    return g if len(set(cols)) == len(cols) else None
def tf_rankcol(g):
    obs = sorted(objects(g, 0), key=lambda o: bbox(o)[1]); out = copy(g)
    for i, o in enumerate(obs, 1):
        for r, c in o: out[r][c] = i
    return out if out != g else None
# objects_ranked_by_column_recoloured_sequentially dropped 2026-10-12 (trio review: behavioural duplicate or one global operation)
# 33 a corner digit gives a distance; the cell that far down the main diagonal from the corner is marked.
def gi_cornerdist(rng):
    n, _ = _sqsz(rng, 6, 20, 21, 30, 0.3)
    d = rng.randint(1, min(9, n)); g = blank(n, n); g[0][0] = d
    c = rng.choice([x for x in COLOURS if x not in (5, d)])
    sprinkle(rng, g, rng.randint(1, max(1, n - 1)), c)
    return g
def tf_cornerdist(g):
    out = copy(g); d = g[0][0]; out[d - 1][d - 1] = 5
    return out
rule("marker_digit_sets_mark_distance_from_corner", "A digit in the corner gives a distance; the cell that far down the main diagonal is marked.", gi_cornerdist, tf_cornerdist, digits=True)


# 34 two row markers and two column markers; those rows swap and those columns swap.
def gi_swaprc(rng):
    h, w = _sz(rng, 7, 18, 21, 30, 0.3); h = max(h, 4); w = max(w, 4)
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.35: g[r][c] = rng.choice([x for x in COLOURS if x not in (8, 9)])
    r1, r2 = rng.sample(range(h), 2); c1, c2 = rng.sample(range(w), 2)
    g[r1][0] = 8; g[r2][0] = 8; g[0][c1] = 9; g[0][c2] = 9
    return g
def tf_swaprc(g):
    rows = [r for r in range(len(g)) if g[r][0] == 8]; cols = [c for c in range(len(g[0])) if g[0][c] == 9]
    if len(rows) != 2 or len(cols) != 2: return None
    r1, r2 = rows; c1, c2 = cols; out = copy(g)
    out[r1], out[r2] = g[r2][:], g[r1][:]
    for row in out: row[c1], row[c2] = row[c2], row[c1]
    return out
rule("swap_rows_and_columns_indicated_by_markers", "Two markers on the left name a row pair to swap, two on the top name a column pair to swap.", gi_swaprc, tf_swaprc)


# 35 a margin column holds, per row, the count of coloured cells in that row (capped at 9).
def gi_rowcountmargin(rng):
    h, w = _sz(rng, 6, 18, 21, 30, 0.3)
    g = blank(h, w + 1)
    for r in range(h):
        k = rng.randint(0, w); col = rng.choice(COLOURS)
        for c in rng.sample(range(w), k): g[r][c] = col
    return g
def tf_rowcountmargin(g):
    out = copy(g)
    for r, row in enumerate(g):
        cnt = sum(1 for v in row[:-1] if v); out[r][-1] = min(cnt, 9)
    return out
rule("object_count_per_row_written_in_margin_digit", "An extra right-hand column holds, for each row, the number of coloured cells in that row.", gi_rowcountmargin, tf_rowcountmargin, digits=True)


# 36 a margin row holds, per column, the count of coloured cells in that column (capped at 9).
def gi_colcountmargin(rng):
    h, w = _sz(rng, 6, 18, 21, 30, 0.3)
    g = blank(h + 1, w)
    for c in range(w):
        k = rng.randint(0, h); col = rng.choice(COLOURS)
        for r in rng.sample(range(h), k): g[r][c] = col
    return g
def tf_colcountmargin(g):
    out = copy(g); h = len(g) - 1
    for c in range(len(g[0])):
        cnt = sum(1 for r in range(h) if g[r][c]); out[-1][c] = min(cnt, 9)
    return out
rule("object_count_per_column_written_in_margin_digit", "An extra bottom row holds, for each column, the number of coloured cells in that column.", gi_colcountmargin, tf_colcountmargin, digits=True)


# 37 the total object count n marks the cell (n, n) on the main diagonal.
def gi_countdiagcell(rng):
    h, w = _sz(rng, 8, 18, 21, 30, 0.3)
    k = rng.randint(2, min(7, h, w))
    return _scene(rng, h, w, k, k, 3, 7, exclude=(0, 7))
def tf_countdiagcell(g):
    h, w = dims(g); n = len(objects(g, 0))
    if n > min(h, w): return None
    out = copy(g); out[n - 1][n - 1] = 7
    return out
rule("object_count_marks_diagonal_cell", "The total number of objects, n, is used to mark the cell at row n, column n.", gi_countdiagcell, tf_countdiagcell)


# 38 the midpoint cell between two markers is filled.
def gi_midpoint(rng):
    h, w = _sz(rng, 6, 18, 21, 30, 0.3)
    g = blank(h, w)
    while True:
        ra, ca = rng.randrange(h), rng.randrange(w); rb, cb = rng.randrange(h), rng.randrange(w)
        if (ra, ca) != (rb, cb): break
    g[ra][ca] = 8; g[rb][cb] = 9
    return g
def tf_midpoint(g):
    (ra, ca), = cells(g, lambda v: v == 8); (rb, cb), = cells(g, lambda v: v == 9)
    out = copy(g); out[(ra + rb) // 2][(ca + cb) // 2] = 5
    return out
rule("marker_pair_midpoint_cell_filled", "The cell midway between two markers is filled.", gi_midpoint, tf_midpoint)


# 39 a corner digit (1-4) picks a diagonal direction for a ray fired from a marker.
def gi_diagray(rng):
    h, w = _sz(rng, 8, 18, 21, 30, 0.3)
    g = blank(h, w); r = rng.randint(1, h - 2); c = rng.randint(1, w - 2)
    g[r][c] = 8; d = rng.randint(1, 4)
    if g[0][w - 1] == 8: return None
    g[0][w - 1] = d
    return g
def tf_diagray(g):
    h, w = dims(g); d = g[0][w - 1]
    (r, c), = cells(g, lambda v: v == 8)
    dr, dc = {1: (1, 1), 2: (1, -1), 3: (-1, 1), 4: (-1, -1)}[d]
    out = copy(g); rr, cc = r + dr, c + dc
    while 0 <= rr < h and 0 <= cc < w:
        out[rr][cc] = 5; rr += dr; cc += dc
    return out if out != g else None
rule("corner_digit_selects_diagonal_direction_path", "A digit in the top-right corner (1-4) picks a diagonal direction; a ray of that direction is drawn from the marker.", gi_diagray, tf_diagray, digits=True)


# 40 two markers are opposite corners of a rectangle, whose outline is drawn.
def gi_rectmarkers(rng):
    h, w = _sz(rng, 6, 16, 21, 30, 0.3); h = max(h, 4); w = max(w, 4)
    g = blank(h, w); ra, rb = rng.sample(range(h), 2); ca, cb = rng.sample(range(w), 2)
    g[ra][ca] = 8; g[rb][cb] = 8
    return g
def tf_rectmarkers(g):
    (r0, c0), (r1, c1) = sorted(cells(g, lambda v: v == 8))
    r0, r1 = min(r0, r1), max(r0, r1); c0, c1 = min(c0, c1), max(c0, c1)
    out = copy(g); rect(out, r0, c0, r1, c1, 5, fill=False)
    return out
rule("two_markers_define_rectangle_filled", "Two markers are treated as opposite corners of a rectangle, whose outline is drawn.", gi_rectmarkers, tf_rectmarkers)
