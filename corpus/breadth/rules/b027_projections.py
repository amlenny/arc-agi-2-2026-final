# b027_projections.py -- PROJECTIONS AND SILHOUETTES: objects projected onto walls as bars, row/column occupancy
# strips, profiles (first cell per row), skylines, shadows cast from a light, silhouettes merged, outlined,
# cropped, and rectangles reconstructed from their two projections.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

GREY, SHADE = 5, 8


def _hw(rng, lo=6, hi=16, big=0.4):
    """Grid size: a 40% share lands in the 21-30 band."""
    if rng.random() < big:
        return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _scene(rng, k_lo=2, k_hi=5, n_lo=3, n_hi=8, margin=1, big=0.4, exclude=(0,), lo=6, hi=16):
    h, w = _hw(rng, lo, hi, big); g = blank(h, w)
    k = rng.randint(k_lo, k_hi)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    cols = [rng.choice([c for c in COLOURS if c not in exclude]) for _ in range(k)]
    if place_shapes(rng, g, shapes, cols, margin=margin) is None:
        return None
    return g


def _slots(rng, total, sizes, lo=0):
    """Start positions for segments of the given sizes, in order, pairwise separated by >= 1, inside [lo, total)."""
    need = sum(sizes) + len(sizes) - 1
    if need > total - lo:
        return None
    slack = total - lo - need; starts = []; pos = lo
    for s in sizes:
        gap = rng.randint(0, slack); slack -= gap; pos += gap
        starts.append(pos); pos += s + 1
    return starts


def _packed(rng, h, w, k, n_lo=3, n_hi=8, rows_disjoint=False, cols_disjoint=True, exclude=(0,), r_lo=0, c_lo=0):
    """k shapes whose column ranges (and/or row ranges) are pairwise disjoint. Returns grid or None."""
    g = blank(h, w)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    hs = [max(r for r, _ in s) + 1 for s in shapes]; ws = [max(c for _, c in s) + 1 for s in shapes]
    if max(hs) > h - r_lo or max(ws) > w - c_lo:
        return None
    cs = _slots(rng, w, ws, c_lo) if cols_disjoint else None
    rs = None
    if rows_disjoint:   # row slots are packed in a shuffled order so row order is independent of column order
        order = list(range(k)); rng.shuffle(order)
        packed = _slots(rng, h, [hs[i] for i in order], r_lo)
        if packed is not None:
            rs = [0] * k
            for j, i in enumerate(order): rs[i] = packed[j]
    if (cols_disjoint and cs is None) or (rows_disjoint and rs is None):
        return None
    pal = [c for c in COLOURS if c not in exclude]
    for i, s in enumerate(shapes):
        r0 = rs[i] if rs is not None else rng.randint(r_lo, h - hs[i])
        c0 = cs[i] if cs is not None else rng.randint(c_lo, w - ws[i])
        col = rng.choice(pal)
        for r, c in s:
            g[r0 + r][c0 + c] = col
    return g if len(objects(g, 0)) == k else None


def _ocol(g, o):
    return g[o[0][0]][o[0][1]]


# 1 every object becomes a bar of its width on the bottom edge.
def gi_floor_bars(rng):
    h, w = _hw(rng); k = rng.randint(2, 5)
    g = _packed(rng, h - 1, w, k)
    return g + [[0] * w] if g else None
def tf_floor_bars(g):
    h, w = dims(g); out = blank(h, w)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o)
        for c in range(c0, c1 + 1): out[h - 1][c] = _ocol(g, o)
    return out
rule("objects_projected_to_floor_bars", "Every object is replaced by a bar on the bottom edge, in its colour, spanning exactly the columns it occupied.", gi_floor_bars, tf_floor_bars)


# 2 every object becomes a bar of its height on the left edge.
def gi_left_bars(rng):
    h, w = _hw(rng); k = rng.randint(2, 5)
    g = _packed(rng, h, w - 1, k, rows_disjoint=True, cols_disjoint=False)
    return [[0] + row for row in g] if g else None
def tf_left_bars(g):
    h, w = dims(g); out = blank(h, w)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o)
        for r in range(r0, r1 + 1): out[r][0] = _ocol(g, o)
    return out
rule("objects_projected_to_left_wall_bars", "Every object is replaced by a bar on the left edge, in its colour, spanning exactly the rows it occupied.", gi_left_bars, tf_left_bars)


# 3 one object; mark its rows on the left border and its columns on the top border.
def gi_mark_border(rng):
    h, w = _hw(rng); g = blank(h - 1, w - 1)
    if place_shapes(rng, g, [random_shape(rng, rng.randint(4, 14))], [rng.choice(COLOURS)], margin=0) is None: return None
    return [[0] * w] + [[0] + row for row in g]
def tf_mark_border(g):
    out = copy(g); o = objects(g, 0)[0]; col = _ocol(g, o); r0, c0, r1, c1 = bbox(o)
    for r in range(r0, r1 + 1): out[r][0] = col
    for c in range(c0, c1 + 1): out[0][c] = col
    return out
rule("object_rows_and_columns_marked_on_border", "The object's rows are marked on the left edge and its columns on the top edge, both in the object's colour.", gi_mark_border, tf_mark_border)


# 4 union silhouette of all objects collapsed to one row.
def gi_union_row(rng):
    g = _scene(rng, 2, 6, 2, 8, exclude=(0, GREY))
    if g is None: return None
    occ = [any(g[r][c] for r in range(len(g))) for c in range(len(g[0]))]
    return g if any(occ) and not all(occ) else None
def tf_union_row(g):
    h, w = dims(g)
    return [[GREY if any(g[r][c] for r in range(h)) else 0 for c in range(w)]]
rule("union_silhouette_collapsed_to_row", "Output a single row as wide as the grid, grey (5) in every column that holds at least one coloured cell.", gi_union_row, tf_union_row)


# 5 light marker on one wall; every object casts a same-shape colour-8 shadow onto the opposite wall.
def _light_scene(rng):
    h, w = _hw(rng, 8, 16); g = blank(h - 2, w - 2); k = rng.randint(1, 4)
    k_ok = _packed(rng, h - 2, w - 2, k, 3, 8, rows_disjoint=rng.random() < 0.5, cols_disjoint=True, exclude=(0, GREY, SHADE))
    if k_ok is None: return None
    g = [[0] * w] + [[0] + row + [0] for row in k_ok] + [[0] * w]
    side = rng.choice("LRTB")
    if side == "L": g[rng.randint(1, h - 2)][0] = GREY
    elif side == "R": g[rng.randint(1, h - 2)][w - 1] = GREY
    elif side == "T": g[0][rng.randint(1, w - 2)] = GREY
    else: g[h - 1][rng.randint(1, w - 2)] = GREY
    return g
def _light_side(g):
    h, w = dims(g); (r, c), = cells(g, lambda v: v == GREY)
    return "L" if c == 0 else "R" if c == w - 1 else "T" if r == 0 else "B"
def tf_light_shadow(g):
    h, w = dims(g); out = copy(g); side = _light_side(g)
    for o in objects(g, 0):
        if _ocol(g, o) == GREY: continue
        r0, c0, r1, c1 = bbox(o)
        dr, dc = {"L": (0, w - 1 - c1), "R": (0, -c0), "T": (h - 1 - r1, 0), "B": (-r0, 0)}[side]
        for r, c in o:
            if out[r + dr][c + dc] == 0: out[r + dr][c + dc] = SHADE
    return out
rule("light_casts_shape_shadow_on_far_wall", "The grey cell on the border is a light; every object casts a colour-8 copy of its own shape onto the wall opposite the light, keeping its shape.", _light_scene, tf_light_shadow)


# 6 two overlapping shapes merged into one silhouette in the colour of the topmost cell.
def gi_merge(rng):
    h, w = _hw(rng, 7, 16); g = blank(h, w); a, b = colours(rng, 2)
    sa = random_shape(rng, rng.randint(6, 16), conn8=False); sb = random_shape(rng, rng.randint(6, 16), conn8=False)
    ha, wa = max(r for r, _ in sa) + 1, max(c for _, c in sa) + 1; hb, wb = max(r for r, _ in sb) + 1, max(c for _, c in sb) + 1
    if ha > h or wa > w or hb > h or wb > w: return None
    ra, ca = rng.randint(0, h - ha), rng.randint(0, w - wa)
    rb, cb = rng.randint(max(0, ra - hb + 1), min(h - hb, ra + ha - 1)), rng.randint(max(0, ca - wb + 1), min(w - wb, ca + wa - 1))
    A = {(ra + r, ca + c) for r, c in sa}; B = {(rb + r, cb + c) for r, c in sb}
    if not (A & B) or A <= B or B <= A: return None
    for r, c in A: g[r][c] = a
    for r, c in B: g[r][c] = b
    return g
def tf_merge(g):
    cs = cells(g, lambda v: v != 0); col = g[cs[0][0]][cs[0][1]]
    out = blank(*dims(g))
    for r, c in cs: out[r][c] = col
    return out
rule("overlapping_pair_merged_one_colour", "The two overlapping shapes become one solid silhouette painted in the colour of the topmost (then leftmost) coloured cell.", gi_merge, tf_merge)


# 7 row occupancy as a single column.
def gi_row_occ(rng):
    g = _scene(rng, 2, 6, 2, 8, exclude=(0, GREY))
    if g is None: return None
    occ = [any(row) for row in g]
    return g if any(occ) and not all(occ) else None
def tf_row_occ(g):
    return [[GREY if any(row) else 0] for row in g]
rule("row_occupancy_as_column", "Output a single column as tall as the grid, grey (5) on every row that holds at least one coloured cell.", gi_row_occ, tf_row_occ)


# 8 an occupancy strip is appended below the grid.
def gi_occ_strip(rng):
    g = _scene(rng, 2, 6, 2, 8, exclude=(0, GREY), hi=15)
    return g if g and len(g) <= 29 else None
def tf_occ_strip(g):
    h, w = dims(g)
    return copy(g) + [[GREY if any(g[r][c] for r in range(h)) else 0 for c in range(w)]]
rule("occupancy_strip_appended_below", "One new row is added beneath the grid, grey (5) under every column that holds a coloured cell and empty under the rest.", gi_occ_strip, tf_occ_strip)


# 9 left profile: only the first coloured cell of each row survives.
def gi_left_profile(rng):
    g = _scene(rng, 2, 6, 4, 12, margin=1)
    if g is None: return None
    return g if sum(1 for row in g if sum(1 for v in row if v) >= 2) >= 2 else None
def tf_left_profile(g):
    out = blank(*dims(g))
    for r, row in enumerate(g):
        for c, v in enumerate(row):
            if v: out[r][c] = v; break
    return out
rule("left_profile_first_cell_per_row", "Seen from the left only the first coloured cell of each row is visible; every other cell is erased.", gi_left_profile, tf_left_profile)


# 10 solid skyline: each column filled grey from its highest cell down to the floor.
def gi_skyline(rng):
    g = _scene(rng, 2, 6, 2, 9, exclude=(0, GREY))
    if g is None: return None
    tops = [next((r for r in range(len(g)) if g[r][c]), None) for c in range(len(g[0]))]
    return g if len(set(tops)) >= 3 else None
def tf_skyline(g):
    h, w = dims(g); out = blank(h, w)
    for c in range(w):
        top = next((r for r in range(h) if g[r][c]), None)
        if top is not None:
            for r in range(top, h): out[r][c] = GREY
    return out
rule("solid_skyline_from_highest_cells", "Each column is filled grey (5) from its highest coloured cell down to the bottom edge; empty columns stay empty.", gi_skyline, tf_skyline)


# 11 outline of the union silhouette of all objects.
def gi_outline(rng):
    h, w = _hw(rng, 7, 16); g = blank(h, w); k = rng.randint(2, 5)
    for _ in range(k):
        rh, rw = rng.randint(2, max(2, h // 3)), rng.randint(2, max(2, w // 3))
        r0, c0 = rng.randint(0, h - rh), rng.randint(0, w - rw)
        rect(g, r0, c0, r0 + rh - 1, c0 + rw - 1, rng.choice([c for c in COLOURS if c != GREY]))
    return g if 0 < sum(1 for row in g for v in row if v) < h * w else None
def tf_outline(g):
    h, w = dims(g); out = blank(h, w)
    for r in range(h):
        for c in range(w):
            if g[r][c] and any(not (0 <= r + dr < h and 0 <= c + dc < w) or g[r + dr][c + dc] == 0 for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[r][c] = GREY
    return out
rule("footprint_outline_of_union", "All overlapping blocks are merged into one silhouette, and only its outline (cells with an empty side-neighbour or on the edge) is drawn, in grey (5).", gi_outline, tf_outline)


# 12 diagonal shadow of the silhouette on the floor (light at 45 degrees from the upper left).
def gi_diag_floor(rng):
    g = _scene(rng, 1, 4, 3, 9, exclude=(0, SHADE))
    if g is None: return None
    h, w = dims(g)
    hits = {c + (h - 1 - r) for r, c in cells(g, lambda v: v != 0) if c + (h - 1 - r) < w and r < h - 1}
    return g if hits and not any(g[h - 1][c] for c in hits) else None
def tf_diag_floor(g):
    h, w = dims(g); out = copy(g)
    for r, c in cells(g, lambda v: v != 0):
        x = c + (h - 1 - r)
        if x < w and out[h - 1][x] == 0: out[h - 1][x] = SHADE
    return out
rule("diagonal_shadow_onto_floor", "Light falls diagonally from the upper left: every coloured cell darkens the floor cell found by moving down-right to the bottom edge, in colour 8.", gi_diag_floor, tf_diag_floor)


# 13 project colours onto the top edge: each column takes the colour of its highest cell.
def gi_top_colours(rng):
    g = _scene(rng, 2, 6, 2, 8)
    return g if g and len({v for row in g for v in row}) >= 3 else None
def tf_top_colours(g):
    h, w = dims(g)
    return [[next((g[r][c] for r in range(h) if g[r][c]), 0) for c in range(w)]]
rule("top_edge_colour_projection", "Output a single row as wide as the grid where each column shows the colour of its highest coloured cell, or empty if the column has none.", gi_top_colours, tf_top_colours)


# 14 two projections given as bars (floor and right wall); reconstruct the rectangle.
def gi_two_bars(rng):
    h, w = _hw(rng, 6, 16); g = blank(h, w); a, b = colours(rng, 2, exclude=(0, GREY))
    r0 = rng.randint(0, h - 3); r1 = rng.randint(r0, h - 2); c0 = rng.randint(0, w - 3); c1 = rng.randint(c0, w - 2)
    for c in range(c0, c1 + 1): g[h - 1][c] = a
    for r in range(r0, r1 + 1): g[r][w - 1] = b
    return g
def tf_two_bars(g):
    h, w = dims(g); out = copy(g)
    cs = [c for c in range(w - 1) if g[h - 1][c]]; rs = [r for r in range(h - 1) if g[r][w - 1]]
    for r in rs:
        for c in cs: out[r][c] = GREY
    return out
rule("rectangle_from_floor_and_wall_bars", "A bar on the bottom edge gives the columns and a bar on the right edge gives the rows; the grey (5) rectangle they describe is drawn where they meet.", gi_two_bars, tf_two_bars)


# 15 marks along the top edge and the left edge; fill every interior cell whose row and column are both marked.
def gi_cross(rng):
    h, w = _hw(rng, 5, 14); g = blank(h, w); a, b = colours(rng, 2, exclude=(0, GREY))
    cs = [c for c in range(1, w) if rng.random() < 0.4]; rs = [r for r in range(1, h) if rng.random() < 0.4]
    if not cs or not rs or len(cs) == w - 1 or len(rs) == h - 1: return None
    for c in cs: g[0][c] = a
    for r in rs: g[r][0] = b
    return g
def tf_cross(g):
    h, w = dims(g); out = copy(g)
    for r in range(1, h):
        for c in range(1, w):
            if g[r][0] and g[0][c]: out[r][c] = GREY
    return out
rule("marked_rows_cross_marked_columns", "Marks along the top edge pick columns and marks along the left edge pick rows; every interior cell on both a picked row and a picked column turns grey (5).", gi_cross, tf_cross)


# 16 several objects mark their rows on the right wall.
def gi_right_marks(rng):
    h, w = _hw(rng); k = rng.randint(2, 5)
    g = _packed(rng, h, w - 1, k, rows_disjoint=True, cols_disjoint=False)
    return [row + [0] for row in g] if g else None
def tf_right_marks(g):
    h, w = dims(g); out = copy(g)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o)
        for r in range(r0, r1 + 1): out[r][w - 1] = _ocol(g, o)
    return out
rule("objects_mark_their_rows_on_right_wall", "Each object paints the right-edge cells of every row it occupies in its own colour; the objects stay.", gi_right_marks, tf_right_marks)


# 17 column cell counts as grey bars from the floor.
def gi_col_counts(rng):
    h, w = _hw(rng); g = blank(h, w)
    for _ in range(rng.randint(h * w // 8, h * w // 3)):
        g[rng.randrange(h)][rng.randrange(w)] = rng.choice([c for c in COLOURS if c != GREY])
    cnt = [sum(1 for r in range(h) if g[r][c]) for c in range(w)]
    return g if len(set(cnt)) >= 3 else None
def tf_col_counts(g):
    h, w = dims(g); out = blank(h, w)
    for c in range(w):
        n = sum(1 for r in range(h) if g[r][c])
        for r in range(h - n, h): out[r][c] = GREY
    return out
rule("column_cell_counts_as_grey_bars", "Each column becomes a grey (5) bar standing on the bottom edge whose height is the number of coloured cells that column held.", gi_col_counts, tf_col_counts)


# 18 row cell counts as a digit column.
def gi_row_digits(rng):
    h, w = _hw(rng, 5, 14); g = blank(h, w); cnt = []
    for r in range(h):
        n = rng.randint(0, min(9, w - 1)); cnt.append(n)
        for c in rng.sample(range(w), n): g[r][c] = rng.choice(COLOURS)
    return g if len(set(cnt)) >= 2 else None
def tf_row_digits(g):
    return [[sum(1 for v in row if v)] for row in g]
rule("row_cell_counts_as_digit_column", "Output a single column as tall as the grid where each cell is the digit counting the coloured cells in that row.", gi_row_digits, tf_row_digits, digits=True)


# 19 seen from above: only the highest cell of each column keeps its colour; cells below it turn grey.
def gi_from_above(rng):
    g = _scene(rng, 2, 6, 3, 10, exclude=(0, GREY))
    if g is None: return None
    h, w = dims(g)
    return g if sum(1 for c in range(w) if sum(1 for r in range(h) if g[r][c]) >= 2) >= 2 else None
def tf_from_above(g):
    h, w = dims(g); out = copy(g)
    for c in range(w):
        seen = False
        for r in range(h):
            if g[r][c]:
                if seen: out[r][c] = GREY
                seen = True
    return out
rule("hidden_from_above_turn_grey", "Looking down each column, the first coloured cell keeps its colour and every coloured cell beneath it turns grey (5).", gi_from_above, tf_from_above)


# 20 objects become width bars stacked on the floor, ordered by left edge.
def gi_stacked_bars(rng):
    g = _scene(rng, 2, 6, 2, 9)
    if g is None: return None
    lefts = [bbox(o)[1] for o in objects(g, 0)]
    return g if len(set(lefts)) == len(lefts) else None
def tf_stacked_bars(g):
    h, w = dims(g); out = blank(h, w); obs = sorted(objects(g, 0), key=lambda o: bbox(o)[1])
    if len(obs) > h: return None
    for i, o in enumerate(obs):
        r0, c0, r1, c1 = bbox(o)
        for c in range(c0, c1 + 1): out[h - 1 - i][c] = _ocol(g, o)
    return out
rule("objects_become_width_bars_stacked_from_floor", "Each object becomes a bar over its own columns in its colour; the bars are stacked from the bottom edge upward, the leftmost object lowest.", gi_stacked_bars, tf_stacked_bars)


# 21 horizontal profile: keep only the first and last coloured cell of every row.
def gi_row_edges(rng):
    g = gi_outline(rng)
    return g if g and sum(1 for row in g if sum(1 for v in row if v) >= 3) >= 2 else None
def tf_row_edges(g):
    out = blank(*dims(g))
    for r, row in enumerate(g):
        idx = [c for c, v in enumerate(row) if v]
        if idx:
            out[r][idx[0]] = row[idx[0]]; out[r][idx[-1]] = row[idx[-1]]
    return out
rule("row_profile_edges_only", "In every row only the first and the last coloured cell are kept; everything between them is erased.", gi_row_edges, tf_row_edges)


# 22 each object casts a shadow to the right as long as it is tall.
def gi_shadow_h(rng):
    g = _scene(rng, 1, 4, 3, 9, margin=2, exclude=(0, SHADE))
    return g
def tf_shadow_h(g):
    h, w = dims(g); out = copy(g)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o); L = r1 - r0 + 1
        for r in range(r0, r1 + 1):
            cs = [c for _, c in o if _ == r]
            for x in range(max(cs) + 1, min(w, max(cs) + 1 + L)):
                if out[r][x] == 0: out[r][x] = SHADE
    return out
rule("shadow_right_as_long_as_object_tall", "Every object casts a colour-8 shadow to its right on each of its rows, as many cells long as the object is tall.", gi_shadow_h, tf_shadow_h)


# 23 every cell slides diagonally down-right to the border.
def gi_diag_slide(rng):
    h, w = _hw(rng, 5, 14); g = blank(h, w); seen = set()
    for _ in range(rng.randint(3, (h + w) // 2)):
        r, c = rng.randrange(h - 1), rng.randrange(w - 1); d = min(h - 1 - r, w - 1 - c)
        if (r + d, c + d) in seen or g[r][c]: continue
        seen.add((r + d, c + d)); g[r][c] = rng.choice(COLOURS)
    return g if len(seen) >= 2 else None
def tf_diag_slide(g):
    h, w = dims(g); out = blank(h, w)
    for r, c in cells(g, lambda v: v != 0):
        d = min(h - 1 - r, w - 1 - c); out[r + d][c + d] = g[r][c]
    return out
rule("cells_slide_diagonally_to_border", "Every coloured cell slides down and to the right until it reaches the bottom or right edge, and stays there.", gi_diag_slide, tf_diag_slide)


# 24 rows of the colour-1 object crossed with columns of the colour-2 object.
def gi_rows_x_cols(rng):
    h, w = _hw(rng, 7, 16); g = blank(h, w)
    if place_shapes(rng, g, [random_shape(rng, rng.randint(3, 9)), random_shape(rng, rng.randint(3, 9))], [1, 2], margin=1) is None: return None
    (A,), (B,) = components(g, 1), components(g, 2)
    r0, _, r1, _ = bbox(A); _, c0, _, c1 = bbox(B)
    return g if any(g[r][c] == 0 for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)) else None
def tf_rows_x_cols(g):
    out = copy(g); A = cells(g, lambda v: v == 1); B = cells(g, lambda v: v == 2)
    r0, _, r1, _ = bbox(A); _, c0, _, c1 = bbox(B)
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if out[r][c] == 0: out[r][c] = GREY
    return out
rule("rows_of_one_cross_columns_of_two", "Where the rows spanned by the colour-1 object cross the columns spanned by the colour-2 object, empty cells are painted grey (5).", gi_rows_x_cols, tf_rows_x_cols)


# 25 objects recoloured by their width.
def gi_width_digit(rng):
    g = _scene(rng, 2, 6, 2, 9)
    if g is None: return None
    obs = objects(g, 0)
    return g if all(bbox(o)[3] - bbox(o)[1] + 1 <= 9 for o in obs) and any(_ocol(g, o) != bbox(o)[3] - bbox(o)[1] + 1 for o in obs) else None
def tf_width_digit(g):
    out = copy(g)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o)
        for r, c in o: out[r][c] = c1 - c0 + 1
    return out
rule("objects_recoloured_by_width", "Every object is repainted in the colour whose number equals how many columns the object spans.", gi_width_digit, tf_width_digit, digits=True)


# 26 objects project bars onto both the floor and the left wall and stay in place.
def gi_two_walls(rng):
    h, w = _hw(rng, 8, 16); k = rng.randint(2, 4)
    g = _packed(rng, h - 1, w - 1, k, 3, 8, rows_disjoint=True, cols_disjoint=True)
    return [[0] + row for row in g] + [[0] * w] if g else None
def tf_two_walls(g):
    h, w = dims(g); out = copy(g)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o); col = _ocol(g, o)
        for r in range(r0, r1 + 1): out[r][0] = col
        for c in range(c0, c1 + 1): out[h - 1][c] = col
    return out
rule("objects_project_onto_floor_and_left_wall", "Each object paints a bar of its colour on the left edge over its rows and another on the bottom edge under its columns; the objects stay.", gi_two_walls, tf_two_walls)


# 27 a grey floor bar is repainted beneath each object's columns.
def gi_floor_paint(rng):
    h, w = _hw(rng); k = rng.randint(2, 5)
    g = _packed(rng, h - 2, w, k, exclude=(0, GREY))
    return g + [[0] * w, [GREY] * w] if g else None
def tf_floor_paint(g):
    h, w = dims(g); out = copy(g)
    for o in objects(g, 0):
        if _ocol(g, o) == GREY: continue
        r0, c0, r1, c1 = bbox(o)
        for c in range(c0, c1 + 1): out[h - 1][c] = _ocol(g, o)
    return out
rule("floor_bar_painted_under_objects", "The grey bar along the bottom edge is repainted, under each object's columns, in that object's colour.", gi_floor_paint, tf_floor_paint)


# 28 crop the union silhouette of everything, in grey.
def gi_crop_union(rng):
    g = _scene(rng, 2, 5, 2, 8, exclude=(0, GREY))
    if g is None: return None
    r0, c0, r1, c1 = bbox(cells(g, lambda v: v != 0))
    return g if any(g[r][c] == 0 for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)) else None
def tf_crop_union(g):
    cs = cells(g, lambda v: v != 0); sub = crop(g, *bbox(cs))
    return [[GREY if v else 0 for v in row] for row in sub]
rule("crop_union_silhouette_grey", "Output the bounding box of all coloured cells together, every coloured cell shown as grey (5) and the gaps left empty.", gi_crop_union, tf_crop_union)


# 29 the single shape's row widths as left-aligned bars.
def gi_row_widths(rng):
    h, w = _hw(rng, 6, 14); g = blank(h, w); col = rng.choice(COLOURS)
    s = random_shape(rng, rng.randint(6, 18))
    if place_shapes(rng, g, [s], [col], margin=0) is None: return None
    rows = {}
    for r, c in s: rows[r] = rows.get(r, 0) + 1
    return g if len(set(rows.values())) >= 2 else None
def tf_row_widths(g):
    o = objects(g, 0)[0]; col = _ocol(g, o); r0, c0, r1, c1 = bbox(o)
    ws = [sum(1 for r, c in o if r == rr) for rr in range(r0, r1 + 1)]
    return [[col] * n + [0] * (max(ws) - n) for n in ws]
rule("shape_row_cell_counts_as_bars", "Output one row per row of the shape: a left-aligned bar in the shape's colour as long as the number of cells the shape has on that row.", gi_row_widths, tf_row_widths)


# 30 each colour's column projection on its own row, colours in ascending order.
def gi_colour_proj(rng):
    g = _scene(rng, 3, 7, 2, 8)
    if g is None: return None
    return g if len({v for row in g for v in row if v}) >= 2 else None
def tf_colour_proj(g):
    h, w = dims(g); cols = sorted({v for row in g for v in row if v})
    return [[k if any(g[r][c] == k for r in range(h)) else 0 for c in range(w)] for k in cols]
rule("each_colour_column_projection_stacked", "Output one row per colour present, lowest colour number first, each row marking in that colour the columns where the colour appears.", gi_colour_proj, tf_colour_proj)


# 31 each object's width as a bar, one row per object top to bottom.
def gi_width_bars(rng):
    g = _scene(rng, 2, 6, 2, 9)
    if g is None: return None
    obs = objects(g, 0); tops = [bbox(o)[0] for o in obs]
    return g if len(set(tops)) == len(tops) and len({bbox(o)[3] - bbox(o)[1] for o in obs}) >= 2 else None
def tf_width_bars(g):
    obs = sorted(objects(g, 0), key=lambda o: bbox(o)[0]); ws = [bbox(o)[3] - bbox(o)[1] + 1 for o in obs]
    return [[_ocol(g, o)] * n + [0] * (max(ws) - n) for o, n in zip(obs, ws)]
rule("object_widths_as_bars_top_to_bottom", "Output one row per object, from the highest object down: a left-aligned bar in the object's colour as long as the object is wide.", gi_width_bars, tf_width_bars)


# 32 snow caps: the cell just above each column's highest cell turns grey.
def gi_snow(rng):
    g = _scene(rng, 2, 6, 3, 9, exclude=(0, GREY))
    return g if g and not any(g[0]) else None
def tf_snow(g):
    h, w = dims(g); out = copy(g)
    for c in range(w):
        top = next((r for r in range(h) if g[r][c]), None)
        if top: out[top - 1][c] = GREY
    return out
rule("snow_caps_on_skyline", "In every column that holds a coloured cell, the empty cell directly above the highest coloured cell turns grey (5), like snow settling on a skyline.", gi_snow, tf_snow)


# 33 light marker on one wall; objects project bars onto the opposite wall.
def gi_light_bars(rng):
    h, w = _hw(rng, 8, 16); k = rng.randint(2, 4); side = rng.choice("LRTB")
    inner = _packed(rng, h - 2, w - 2, k, 3, 8, rows_disjoint=side in "LR", cols_disjoint=side in "TB", exclude=(0, GREY))
    if inner is None: return None
    g = [[0] * w] + [[0] + row + [0] for row in inner] + [[0] * w]
    if side == "L": g[rng.randint(1, h - 2)][0] = GREY
    elif side == "R": g[rng.randint(1, h - 2)][w - 1] = GREY
    elif side == "T": g[0][rng.randint(1, w - 2)] = GREY
    else: g[h - 1][rng.randint(1, w - 2)] = GREY
    return g
def tf_light_bars(g):
    h, w = dims(g); out = copy(g); side = _light_side(g)
    for o in objects(g, 0):
        if _ocol(g, o) == GREY: continue
        r0, c0, r1, c1 = bbox(o); col = _ocol(g, o)
        if side in "LR":
            x = w - 1 if side == "L" else 0
            for r in range(r0, r1 + 1): out[r][x] = col
        else:
            y = h - 1 if side == "T" else 0
            for c in range(c0, c1 + 1): out[y][c] = col
    return out
rule("light_projects_object_bars_on_far_wall", "The grey cell on the border is a light; each object paints a bar of its colour on the wall opposite the light over the rows or columns it spans.", gi_light_bars, tf_light_bars)


# 34 each object is reflected in the floor as a colour-8 mirror image standing on the bottom edge.
def gi_reflection(rng):
    h, w = _hw(rng, 8, 16); k = rng.randint(1, 4)
    g = _packed(rng, h - 1, w, k, 3, 8, exclude=(0, SHADE))
    if g is None: return None
    return g + [[0] * w]
def tf_reflection(g):
    h, w = dims(g); out = copy(g)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o)
        for r, c in o:
            y = h - 1 - (r - r0)
            if y > r1 and out[y][c] == 0: out[y][c] = SHADE
    return out
rule("floor_reflection_in_colour_eight", "Every object is reflected in the bottom edge: its upside-down mirror image is drawn in colour 8 with its top row on the floor, where the background is empty.", gi_reflection, tf_reflection)


# 35 the empty top row counts how many objects span each column.
def gi_col_obj_counts(rng):
    g = _scene(rng, 2, 7, 2, 8)
    if g is None: return None
    g = [[0] * len(g[0])] + g
    cnt = [sum(1 for o in objects(g, 0) if bbox(o)[1] <= c <= bbox(o)[3]) for c in range(len(g[0]))]
    return g if max(cnt) >= 2 and max(cnt) <= 9 and len(g) <= 30 else None
def tf_col_obj_counts(g):
    out = copy(g); w = len(g[0])
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o)
        for c in range(c0, c1 + 1): out[0][c] += 1
    return out
rule("top_row_counts_objects_per_column", "The empty top row is filled with digits: each cell counts how many objects span that column, 0 where none does.", gi_col_obj_counts, tf_col_obj_counts, digits=True)


# 36 row projection of two objects: own colour where one, grey where both.
def gi_row_overlap(rng):
    h, w = _hw(rng, 6, 16); g = blank(h, w); a, b = colours(rng, 2, exclude=(0, GREY))
    if place_shapes(rng, g, [random_shape(rng, rng.randint(4, 12)), random_shape(rng, rng.randint(4, 12))], [a, b], margin=1) is None: return None
    (A,), (B,) = components(g, a), components(g, b)
    ra = set(range(bbox(A)[0], bbox(A)[2] + 1)); rb = set(range(bbox(B)[0], bbox(B)[2] + 1))
    return g if (ra & rb) and (ra ^ rb) else None
def tf_row_overlap(g):
    h, w = dims(g); out = []
    for r in range(h):
        s = {v for v in g[r] if v}
        out.append([GREY if len(s) == 2 else s.pop() if s else 0])
    return out
rule("row_projection_two_objects_overlap_grey", "Output a single column: each row shows the colour of the object lying on that row, grey (5) where both objects do, empty where neither.", gi_row_overlap, tf_row_overlap)


# 37 empty columns are marked on the floor.
def gi_empty_cols(rng):
    h, w = _hw(rng); k = rng.randint(2, 5)
    g = _packed(rng, h - 1, w, k, 2, 8, exclude=(0, GREY))
    if g is None: return None
    g = g + [[0] * w]
    return g if any(not any(g[r][c] for r in range(h)) for c in range(w)) else None
def tf_empty_cols(g):
    h, w = dims(g); out = copy(g)
    for c in range(w):
        if not any(g[r][c] for r in range(h)): out[h - 1][c] = GREY
    return out
rule("empty_columns_marked_on_floor", "Every column that holds no coloured cell gets a grey (5) cell on the bottom edge; columns with cells are untouched.", gi_empty_cols, tf_empty_cols)


# 38 left and right profiles as two columns.
def gi_two_profiles(rng):
    g = _scene(rng, 2, 6, 2, 9)
    if g is None: return None
    out = tf_two_profiles(g)
    return g if sum(1 for a, b in out if a != b) >= 2 else None
def tf_two_profiles(g):
    out = []
    for row in g:
        idx = [c for c, v in enumerate(row) if v]
        out.append([row[idx[0]], row[idx[-1]]] if idx else [0, 0])
    return out
rule("left_and_right_profile_columns", "Output two columns as tall as the grid: the left column shows each row's first coloured cell and the right column its last coloured cell.", gi_two_profiles, tf_two_profiles)


# 39 each object casts a colour-8 copy of itself shifted down and right by its own height.
def gi_shadow_copy(rng):
    g = _scene(rng, 1, 4, 3, 8, margin=1, exclude=(0, SHADE))
    if g is None: return None
    h, w = dims(g)
    return g if all(bbox(o)[2] + (bbox(o)[2] - bbox(o)[0] + 1) < h and bbox(o)[3] + (bbox(o)[2] - bbox(o)[0] + 1) < w for o in objects(g, 0)) else None
def tf_shadow_copy(g):
    h, w = dims(g); out = copy(g)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o); d = r1 - r0 + 1
        for r, c in o:
            if r + d < h and c + d < w and out[r + d][c + d] == 0: out[r + d][c + d] = SHADE
    return out
rule("shadow_copy_offset_by_own_height", "Every object casts a colour-8 copy of its shape shifted down and to the right by as many cells as the object is tall, drawn on empty cells only.", gi_shadow_copy, tf_shadow_copy)


# 40 floor marks the columns covered by two or more objects.
def gi_shared_cols(rng):
    g = _scene(rng, 2, 5, 3, 9, exclude=(0, GREY))
    if g is None: return None
    g = g + [[0] * len(g[0])]
    if len(g) > 30: return None
    w = len(g[0]); cnt = [sum(1 for o in objects(g, 0) if bbox(o)[1] <= c <= bbox(o)[3]) for c in range(w)]
    return g if any(n >= 2 for n in cnt) and any(n == 1 for n in cnt) else None
def tf_shared_cols(g):
    h, w = dims(g); out = copy(g); cnt = [0] * w
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o)
        for c in range(c0, c1 + 1): cnt[c] += 1
    for c in range(w):
        if cnt[c] >= 2: out[h - 1][c] = GREY
    return out
rule("floor_marks_columns_shared_by_objects", "Every column spanned by two or more objects gets a grey (5) cell on the bottom edge; columns under at most one object stay empty there.", gi_shared_cols, tf_shared_cols)
