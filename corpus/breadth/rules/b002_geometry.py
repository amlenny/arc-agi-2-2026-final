# b002_geometry.py -- GEOMETRY: symmetry completion, whole-grid and per-object transforms, tiling, scaling,
# shears, cyclic shifts, kaleidoscopes, axis mirrors, motif repetition, rings, diagonals, checkerboards.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


# ---- local helpers -------------------------------------------------------------------------------------
def _noise(rng, h, w, p=0.4, cols=None, bg=0):
    """h x w grid with each cell coloured with probability p from cols (default 1..9)."""
    cols = cols or COLOURS
    g = blank(h, w, bg)
    for r in range(h):
        for c in range(w):
            if rng.random() < p:
                g[r][c] = rng.choice(cols)
    return g


def _nonblank(g):
    return any(v for row in g for v in row)


def _rot(g, k):
    for _ in range(k % 4):
        g = rot90(g)
    return g


def _roll(seq, k):
    k %= len(seq)
    return seq[-k:] + seq[:-k] if k else seq[:]


def _occlude(rng, g, hmax, wmax, allow=lambda r0, c0, r1, c1: True):
    """Paint a random rectangle of 0 over g; returns (r0,c0,r1,c1) or None."""
    H, W = dims(g)
    for _ in range(50):
        h, w = rng.randint(2, hmax), rng.randint(2, wmax)
        r0, c0 = rng.randint(0, H - h), rng.randint(0, W - w)
        if allow(r0, c0, r0 + h - 1, c0 + w - 1):
            rect(g, r0, c0, r0 + h - 1, c0 + w - 1, 0)
            return r0, c0, r0 + h - 1, c0 + w - 1
    return None


def _scene(rng, k_lo, k_hi, n_lo, n_hi, lo, hi, margin=1):
    h, w = size(rng, lo, hi); g = blank(h, w)
    k = rng.randint(k_lo, k_hi)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    cols = [rng.choice(COLOURS) for _ in range(k)]
    if place_shapes(rng, g, shapes, cols, margin=margin) is None:
        return None
    return g


# 1 whole grid rotated 90 clockwise -----------------------------------------------------------------------
def gi_rot90(rng):
    h, w = size(rng, 3, 12)
    return _noise(rng, h, w, 0.45) if h != w else None
def tf_rot90(g):
    return rot90(g)
rule("rot90_whole_grid", "The whole grid is rotated a quarter turn clockwise.", gi_rot90, tf_rot90, primitive=True)


# 2 transpose ---------------------------------------------------------------------------------------------
def gi_transpose(rng):
    h, w = size(rng, 3, 14)
    return _noise(rng, h, w, 0.4)
def tf_transpose(g):
    return transpose(g)
rule("transpose_grid", "Rows become columns: the grid is flipped across its top-left to bottom-right diagonal.", gi_transpose, tf_transpose, primitive=True)


# 3 anti-transpose ----------------------------------------------------------------------------------------
def gi_antitr(rng):
    h, w = size(rng, 3, 14)
    return _noise(rng, h, w, 0.4)
def tf_antitr(g):
    return _rot(transpose(g), 2)
rule("antitranspose_grid", "The grid is flipped across its top-right to bottom-left diagonal.", gi_antitr, tf_antitr, primitive=True)


# 4 rotate the grid by a quarter turn per object -----------------------------------------------------------
def gi_rotcount(rng):
    g = _scene(rng, 1, 3, 2, 6, 6, 12, margin=1)
    return g if g is not None and len(objects(g, 0)) in (1, 2, 3) else None
def tf_rotcount(g):
    return _rot(g, len(objects(g, 0)))
rule("rotate_grid_quarter_turn_per_object", "Count the objects and rotate the whole grid clockwise by that many quarter turns.", gi_rotcount, tf_rotcount)


# 5 four-fold mirror symmetry completion with an occluder --------------------------------------------------
def gi_sym4(rng):
    h, w = size(rng, 6, 16); q = _noise(rng, (h + 1) // 2, (w + 1) // 2, 1.0)
    g = [[q[min(r, h - 1 - r)][min(c, w - 1 - c)] for c in range(w)] for r in range(h)]
    return g if _occlude(rng, g, max(2, h // 2 - 1), max(2, w // 2 - 1)) else None
def tf_sym4(g):
    h, w = dims(g); out = copy(g)
    for r in range(h):
        for c in range(w):
            if g[r][c] == 0:
                v = [g[r][w - 1 - c], g[h - 1 - r][c], g[h - 1 - r][w - 1 - c]]
                v = [x for x in v if x]
                if not v: return None
                out[r][c] = v[0]
    return out
rule("sym4_complete_occluded", "The picture is mirror-symmetric left-right and top-bottom; the black patch is restored from its mirror images.", gi_sym4, tf_sym4)


# 6 diagonal symmetry completion --------------------------------------------------------------------------
def gi_diagsym(rng):
    n = rng.randint(6, 16); q = _noise(rng, n, n, 1.0)
    g = [[q[min(r, c)][max(r, c)] for c in range(n)] for r in range(n)]
    return g if _occlude(rng, g, n // 2, n // 2, lambda r0, c0, r1, c1: r1 < c0 or c1 < r0) else None
def tf_diagsym(g):
    n = len(g); out = copy(g)
    for r in range(n):
        for c in range(n):
            if g[r][c] == 0:
                if g[c][r] == 0: return None
                out[r][c] = g[c][r]
    return out
rule("diagonal_sym_complete_occluded", "The picture is symmetric across its main diagonal; the black patch is filled from the transposed position.", gi_diagsym, tf_diagsym)


# 7 rotational symmetry completion -------------------------------------------------------------------------
def gi_rotsym(rng):
    n = rng.randint(6, 16); g = _noise(rng, n, n, 1.0)
    for r in range(n):
        for c in range(n):
            v = g[r][c]; g[c][n - 1 - r] = v; g[n - 1 - r][n - 1 - c] = v; g[n - 1 - c][r] = v
    return g if _occlude(rng, g, n // 2 - 1 if n > 7 else 2, n // 2 - 1 if n > 7 else 2) else None
def tf_rotsym(g):
    n = len(g); out = copy(g)
    for r in range(n):
        for c in range(n):
            if g[r][c] == 0:
                v = [x for x in (g[c][n - 1 - r], g[n - 1 - r][n - 1 - c], g[n - 1 - c][r]) if x]
                if not v: return None
                out[r][c] = v[0]
    return out
rule("rotational_sym_complete_occluded", "The picture repeats under quarter turns about its centre; the black patch is restored from the rotated copies.", gi_rotsym, tf_rotsym)


# 8 mirror symmetry: output only the hidden patch ---------------------------------------------------------
def gi_hidden(rng):
    h, w = rng.randint(5, 16), rng.randint(6, 16); half = _noise(rng, h, (w + 1) // 2, 1.0)
    g = [[half[r][min(c, w - 1 - c)] for c in range(w)] for r in range(h)]
    return g if _occlude(rng, g, h, w // 2, lambda r0, c0, r1, c1: c1 < w // 2 or c0 > (w - 1) // 2) else None
def tf_hidden(g):
    z = cells(g, lambda v: v == 0)
    if not z: return None
    r0, c0, r1, c1 = bbox(z); w = len(g[0])
    return [[g[r][w - 1 - c] for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
rule("mirror_sym_output_hidden_patch", "The picture is left-right symmetric with a black patch; output just the patch's true contents.", gi_hidden, tf_hidden)


# 9 each object rotated 90 in place -----------------------------------------------------------------------
def gi_objrot(rng):
    return _scene(rng, 2, 4, 3, 6, 8, 16, margin=3)
def tf_objrot(g):
    h, w = dims(g); out = blank(h, w); taken = set()
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o); col = g[o[0][0]][o[0][1]]
        for r, c in o:
            nr, nc = r0 + (c - c0), c0 + (r1 - r)
            if not (0 <= nr < h and 0 <= nc < w) or (nr, nc) in taken: return None
            taken.add((nr, nc)); out[nr][nc] = col
    return out
# rotate_each_object_90 dropped 2026-10-12 (trio review: behavioural duplicate or one global operation)
# 10 each object mirrored left-right within its box --------------------------------------------------------
def gi_objflip(rng):
    return _scene(rng, 2, 5, 3, 8, 7, 16, margin=1)
def tf_objflip(g):
    h, w = dims(g); out = blank(h, w)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o); col = g[o[0][0]][o[0][1]]
        for r, c in o: out[r][c0 + c1 - c] = col
    return out
# flip_each_object_horizontal dropped 2026-10-12 (trio review: behavioural duplicate or one global operation)
# 11 each object rotated 180 within its box ----------------------------------------------------------------
def gi_objrot180(rng):
    return _scene(rng, 2, 5, 3, 8, 7, 16, margin=1)
def tf_objrot180(g):
    h, w = dims(g); out = blank(h, w)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o); col = g[o[0][0]][o[0][1]]
        for r, c in o: out[r0 + r1 - r][c0 + c1 - c] = col
    return out
rule("rotate_each_object_180", "Every object is turned upside down (half turn) inside its own bounding box.", gi_objrot180, tf_objrot180)


# 12 2x2 tiling where each copy is rotated one more quarter turn --------------------------------------------
def gi_tilerot(rng):
    n = rng.randint(2, 6); g = _noise(rng, n, n, 0.5)
    return g if _nonblank(g) else None
def tf_tilerot(g):
    a, b, c, d = g, rot90(g), _rot(g, 3), _rot(g, 2)
    return [x + y for x, y in zip(a, b)] + [x + y for x, y in zip(c, d)]
rule("tile_2x2_pinwheel_rotations", "The grid is tiled two by two; going clockwise each copy is rotated one more quarter turn.", gi_tilerot, tf_tilerot)


# 13 three copies side by side, middle one mirrored ---------------------------------------------------------
def gi_tile3(rng):
    h, w = rng.randint(2, 10), rng.randint(2, 8); g = _noise(rng, h, w, 0.5)
    return g if _nonblank(g) and w * 3 <= 30 else None
def tf_tile3(g):
    return [row + row[::-1] + row for row in g]
rule("tile_three_across_middle_mirrored", "Three copies of the grid are laid side by side, the middle copy mirrored left-right.", gi_tile3, tf_tile3)


# 14 scale up by the number of distinct colours ------------------------------------------------------------
def gi_scalek(rng):
    k = rng.randint(2, 4); h, w = size(rng, 3, 6); cols = colours(rng, k)
    g = _noise(rng, h, w, 0.6, cols)
    return g if len(set(v for row in g for v in row if v)) == k and h * k <= 30 and w * k <= 30 else None
def tf_scalek(g):
    k = len(set(v for row in g for v in row if v))
    return [[v for v in row for _ in range(k)] for row in g for _ in range(k)]
rule("scale_up_by_colour_count", "Each cell becomes a k by k block where k is the number of distinct colours in the grid.", gi_scalek, tf_scalek)


# 15 scale down a block-uniform grid to one cell per block ---------------------------------------------------
def _blockk(g):
    h, w = dims(g)
    for k in range(2, min(h, w) + 1):
        if h % k == 0 and w % k == 0 and all(g[r][c] == g[r - r % k][c - c % k] for r in range(h) for c in range(w)):
            return k
    return None
def gi_shrink(rng):
    k = rng.randint(2, 4); h, w = size(rng, 3, 7); s = _noise(rng, h, w, 0.6)
    if _blockk(s) is not None or not _nonblank(s): return None
    return [[v for v in row for _ in range(k)] for row in s for _ in range(k)]
def tf_shrink(g):
    k = _blockk(g)
    return [row[::k] for row in g[::k]] if k else None
rule("scale_down_uniform_blocks", "The grid is made of equal square blocks of one colour each; shrink every block to a single cell.", gi_shrink, tf_shrink)


# 16 crop the lone object and double its size ----------------------------------------------------------------
def gi_cropx2(rng):
    g = _scene(rng, 1, 1, 3, 9, 7, 16, margin=0)
    return g if g is not None and len(objects(g, 0)) == 1 else None
def tf_cropx2(g):
    o = objects(g, 0)[0]; sub = crop(g, *bbox(o))
    return [[v for v in row for _ in range(2)] for row in sub for _ in range(2)]
rule("crop_object_scale_double", "Cut out the single object's bounding box and enlarge it to twice its size.", gi_cropx2, tf_cropx2)


# 17 shear rows right by their index (grid widens) ---------------------------------------------------------------
def gi_shear(rng):
    h, w = rng.randint(3, 10), rng.randint(3, 12)
    return _noise(rng, h, w, 0.5) if h + w <= 28 else None
def tf_shear(g):
    h, w = dims(g)
    return [[0] * r + row + [0] * (h - 1 - r) for r, row in enumerate(g)]
rule("shear_rows_right_by_index", "Row i is pushed i cells to the right, widening the grid so the shape leans like a parallelogram.", gi_shear, tf_shear)


# 18 cyclic shear: row i rolled right by i -------------------------------------------------------------------------
def gi_cshear(rng):
    h, w = size(rng, 3, 14)
    return _noise(rng, h, w, 0.4)
def tf_cshear(g):
    return [_roll(row, r) for r, row in enumerate(g)]
rule("roll_rows_right_by_index", "Row i is shifted right by i cells, with cells that fall off the right edge wrapping to the left.", gi_cshear, tf_cshear)


# 19 column j rolled down by j -----------------------------------------------------------------------------------------
def gi_cols(rng):
    h, w = size(rng, 3, 14)
    return _noise(rng, h, w, 0.4)
def tf_cols(g):
    h, w = dims(g); out = blank(h, w)
    for c in range(w):
        col = _roll([g[r][c] for r in range(h)], c)
        for r in range(h): out[r][c] = col[r]
    return out
rule("roll_columns_down_by_index", "Column j is shifted down by j cells, wrapping from the bottom back to the top.", gi_cols, tf_cols)


# 20 even rows roll left one, odd rows roll right one -----------------------------------------------------------------
def gi_parity(rng):
    h, w = size(rng, 3, 14)
    return _noise(rng, h, w, 0.4) if w >= 3 else None
def tf_parity(g):
    return [_roll(row, 1 if r % 2 else -1) for r, row in enumerate(g)]
rule("roll_rows_alternating_direction", "Even rows shift one cell left and odd rows one cell right, both wrapping around.", gi_parity, tf_parity)


# 21 kaleidoscope: the top-left wedge reflected eight ways ---------------------------------------------------------------
def gi_kal(rng):
    n = rng.randint(5, 16)
    return _noise(rng, n, n, 0.5)
def tf_kal(g):
    n = len(g); out = blank(n, n)
    for r in range(n):
        for c in range(n):
            a, b = min(r, n - 1 - r), min(c, n - 1 - c)
            out[r][c] = g[min(a, b)][max(a, b)]
    return out
rule("kaleidoscope_eightfold", "The wedge between the top edge and the main diagonal is reflected into all eight symmetric positions.", gi_kal, tf_kal)


# 22 mirror across a drawn axis line -----------------------------------------------------------------------------------
def gi_axis(rng):
    h, w = size(rng, 6, 16); ax = rng.choice([c for c in COLOURS]); g = blank(h, w)
    cols = [c for c in COLOURS if c != ax]
    if rng.random() < 0.5:
        k = rng.randint(2, h - 3)
        for c in range(w): g[k][c] = ax
        for r in range(k) if rng.random() < 0.5 else range(k + 1, h):
            for c in range(w):
                if rng.random() < 0.35: g[r][c] = rng.choice(cols)
    else:
        k = rng.randint(2, w - 3)
        for r in range(h): g[r][k] = ax
        for c in range(k) if rng.random() < 0.5 else range(k + 1, w):
            for r in range(h):
                if rng.random() < 0.35: g[r][c] = rng.choice(cols)
    return g if sum(1 for row in g for v in row if v and v != ax) >= 2 else None
def tf_axis(g):
    h, w = dims(g); out = copy(g)
    rows = [r for r in range(h) if len(set(g[r])) == 1 and g[r][0]]
    colsx = [c for c in range(w) if len({g[r][c] for r in range(h)}) == 1 and g[0][c]]
    if len(rows) + len(colsx) != 1: return None
    if rows:
        k = rows[0]
        for r in range(h):
            for c in range(w):
                m = 2 * k - r
                if r != k and g[r][c] and 0 <= m < h: out[m][c] = g[r][c]
    else:
        k = colsx[0]
        for r in range(h):
            for c in range(w):
                m = 2 * k - c
                if c != k and g[r][c] and 0 <= m < w: out[r][m] = g[r][c]
    return out
rule("mirror_across_drawn_axis_line", "A full line of one colour is a mirror: the cells on its occupied side are reflected onto the empty side.", gi_axis, tf_axis)


# 23 mirror across a drawn diagonal line -------------------------------------------------------------------------------
def gi_diagline(rng):
    n = rng.randint(5, 16); ax = rng.choice(COLOURS); g = blank(n, n); cols = [c for c in COLOURS if c != ax]
    for i in range(n): g[i][i] = ax
    for r in range(n):
        for c in range(r):
            if rng.random() < 0.4: g[r][c] = rng.choice(cols)
    return g if sum(1 for row in g for v in row if v and v != ax) >= 2 else None
def tf_diagline(g):
    n = len(g); out = copy(g)
    for r in range(n):
        for c in range(r):
            if g[r][c]: out[c][r] = g[r][c]
    return out
rule("mirror_across_diagonal_line", "The drawn diagonal is a mirror: everything below it is reflected to the matching spot above it.", gi_diagline, tf_diagline)


# 24 repeat a motif away from the edge it touches ----------------------------------------------------------------------
def gi_motif(rng):
    h, w = size(rng, 7, 18); g = blank(h, w); mh, mw = rng.randint(2, 4), rng.randint(2, 4)
    m = _noise(rng, mh, mw, 0.7, colours(rng, rng.randint(1, 3)))
    if not all(any(m[r][c] for r in range(mh)) for c in range(mw)) or not all(any(m[r]) for r in range(mh)): return None
    if rng.random() < 0.5:
        paste(g, m, rng.randint(1, h - mh), 0)
    else:
        paste(g, m, 0, rng.randint(1, w - mw))
    return g
def tf_motif(g):
    h, w = dims(g); pts = cells(g, lambda v: v != 0); r0, c0, r1, c1 = bbox(pts); m = crop(g, r0, c0, r1, c1); out = copy(g)
    if c0 == 0 and r0 > 0:
        for x in range(c1 + 2, w, c1 - c0 + 2): paste(out, m, r0, x, transparent=0)
    elif r0 == 0 and c0 > 0:
        for y in range(r1 + 2, h, r1 - r0 + 2): paste(out, m, y, c0, transparent=0)
    else:
        return None
    return out
rule("repeat_motif_away_from_edge", "The motif touching one edge is copied repeatedly toward the opposite edge with a one-cell gap between copies.", gi_motif, tf_motif)


# 25 square rings from a seed cell -------------------------------------------------------------------------------------
def gi_cheb(rng):
    h, w = size(rng, 5, 16); g = blank(h, w); g[rng.randrange(h)][rng.randrange(w)] = rng.choice(COLOURS)
    return g
def tf_cheb(g):
    h, w = dims(g); (sr, sc), = cells(g, lambda v: v != 0); col = g[sr][sc]
    return [[col if max(abs(r - sr), abs(c - sc)) % 2 == 0 else 0 for c in range(w)] for r in range(h)]
rule("square_rings_from_seed", "Concentric square rings of the seed's colour spread from the seed cell, every other ring left black.", gi_cheb, tf_cheb)


# 26 diamond rings in two colours from a two-cell seed ------------------------------------------------------------------
def gi_manh(rng):
    h, w = size(rng, 5, 16); g = blank(h, w); a, b = colours(rng, 2)
    r, c = rng.randrange(h), rng.randrange(w - 1); g[r][c] = a; g[r][c + 1] = b
    return g
def tf_manh(g):
    h, w = dims(g); (sr, sc), _ = sorted(cells(g, lambda v: v != 0), key=lambda t: t[1]); a, b = g[sr][sc], g[sr][sc + 1]
    return [[a if (abs(r - sr) + abs(c - sc)) % 2 == 0 else b for c in range(w)] for r in range(h)]
rule("diamond_rings_two_colour", "From the left seed cell, diamond-shaped rings alternate the left seed's colour and the right seed's colour.", gi_manh, tf_manh)


# 27 every coloured cell extends along both diagonals ------------------------------------------------------------------
def gi_diagx(rng):
    h, w = size(rng, 6, 16); g = blank(h, w)
    sprinkle(rng, g, rng.randint(1, 4), 0)
    for _ in range(rng.randint(1, 4)):
        g[rng.randrange(h)][rng.randrange(w)] = rng.choice(COLOURS)
    return g
def tf_diagx(g):
    h, w = dims(g); out = copy(g)
    for r, c in cells(g, lambda v: v != 0):
        col = g[r][c]
        for dr, dc in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            y, x = r + dr, c + dc
            while 0 <= y < h and 0 <= x < w:
                if g[y][x] == 0: out[y][x] = col
                y += dr; x += dc
    return out
rule("diagonals_through_cells", "Each coloured cell shoots lines of its colour along both diagonals out to the grid edges.", gi_diagx, tf_diagx)


# 28 checkerboard from corner seeds ------------------------------------------------------------------------------------
def gi_check(rng):
    h, w = size(rng, 4, 26)
    if h % 2 and w % 2: return None
    a, b = colours(rng, 2, exclude=(0,)); g = blank(h, w)
    for r, c in ((0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)):
        g[r][c] = a if (r + c) % 2 == 0 else b
    return g
def tf_check(g):
    h, w = dims(g); a = g[0][0]; b = g[0][w - 1] if (w - 1) % 2 else g[h - 1][0]
    return [[a if (r + c) % 2 == 0 else b for c in range(w)] for r in range(h)]
rule("checkerboard_from_corner_seeds", "The four corner cells fix a two-colour checkerboard that is extended over the whole grid.", gi_check, tf_check)
# 29 solid rectangles become checkerboards ------------------------------------------------------------------------------
def gi_rectcheck(rng):
    h, w = size(rng, 7, 18); g = blank(h, w); n = 0
    for _ in range(30):
        rh, rw = rng.randint(2, 6), rng.randint(2, 6)
        if rh > h - 1 or rw > w - 1: continue
        r0, c0 = rng.randint(0, h - rh), rng.randint(0, w - rw)
        if all(g[r][c] == 0 for r in range(max(0, r0 - 1), min(h, r0 + rh + 1)) for c in range(max(0, c0 - 1), min(w, c0 + rw + 1))):
            rect(g, r0, c0, r0 + rh - 1, c0 + rw - 1, rng.choice(COLOURS)); n += 1
        if n >= rng.randint(1, 4): break
    return g if n else None
def tf_rectcheck(g):
    out = copy(g)
    for o in objects(g, 0, conn8=False):
        r0, c0, r1, c1 = bbox(o)
        for r, c in o:
            if (r - r0 + c - c0) % 2: out[r][c] = 0
    return out
rule("rectangles_to_checkerboard", "Every solid rectangle is turned into a checkerboard of its colour and black, starting coloured at its top-left.", gi_rectcheck, tf_rectcheck)


# 30 top-row colours run down-right diagonally, wrapping ----------------------------------------------------------------
def gi_stripes(rng):
    h, w = size(rng, 4, 16); g = blank(h, w)
    for c in rng.sample(range(w), rng.randint(1, max(1, w // 3))):
        g[0][c] = rng.choice(COLOURS)
    return g
def tf_stripes(g):
    h, w = dims(g); out = blank(h, w)
    for c in range(w):
        if g[0][c]:
            for r in range(h): out[r][(c + r) % w] = g[0][c]
    return out
rule("diagonal_stripes_from_top_row", "Each coloured cell in the top row trails a diagonal stripe down and to the right, wrapping at the right edge.", gi_stripes, tf_stripes)


# 31 quadrants rotate clockwise ----------------------------------------------------------------------------------------
def _quads(g):
    h, w = dims(g); hh, hw = h // 2, w // 2
    return [crop(g, 0, 0, hh - 1, hw - 1), crop(g, 0, hw, hh - 1, w - 1), crop(g, hh, hw, h - 1, w - 1), crop(g, hh, 0, h - 1, hw - 1)]
def _assemble(tl, tr, br, bl):
    return [a + b for a, b in zip(tl, tr)] + [a + b for a, b in zip(bl, br)]
def gi_quadrot(rng):
    h, w = rng.randint(2, 7) * 2, rng.randint(2, 7) * 2
    return _noise(rng, h, w, 0.4)
def tf_quadrot(g):
    tl, tr, br, bl = _quads(g)
    return _assemble(bl, tl, tr, br)
rule("quadrants_cycle_clockwise", "The four quarters of the grid move one place clockwise without turning.", gi_quadrot, tf_quadrot)


# 32 diagonal quadrants swap -------------------------------------------------------------------------------------------
def gi_quadswap(rng):
    h, w = rng.randint(2, 7) * 2, rng.randint(2, 7) * 2
    return _noise(rng, h, w, 0.4)
def tf_quadswap(g):
    tl, tr, br, bl = _quads(g)
    return _assemble(br, bl, tl, tr)
rule("quadrants_swap_diagonally", "The top-left and bottom-right quarters trade places, and so do the top-right and bottom-left.", gi_quadswap, tf_quadswap)


# 33 rotate so the marker corner lands top-left -----------------------------------------------------------------------
def gi_marker(rng):
    h, w = size(rng, 4, 12); g = _noise(rng, h, w, 0.4, [c for c in COLOURS if c != 9])
    k = rng.choice([1, 2, 3]); r, c = [(0, w - 1), (h - 1, w - 1), (h - 1, 0)][k - 1]; g[r][c] = 9
    return g
def tf_marker(g):
    h, w = dims(g)
    k = [(0, w - 1), (h - 1, w - 1), (h - 1, 0)].index(next((r, c) for r, c in cells(g, lambda v: v == 9)))
    return _rot(g, 3 - k)
rule("rotate_marker_corner_to_top_left", "Rotate the whole grid until the corner holding the grey marker is at the top-left.", gi_marker, tf_marker)


# 34 fold the left half onto the right half -----------------------------------------------------------------------------
def gi_fold(rng):
    h, w = rng.randint(3, 14), rng.randint(2, 7) * 2
    return _noise(rng, h, w, 0.3)
def tf_fold(g):
    h, w = dims(g); hw = w // 2
    out = [[row[hw + c] or row[hw - 1 - c] for c in range(hw)] for row in g]
    return out if out != [row[hw:] for row in g] else None
rule("fold_left_half_onto_right", "The grid is folded in half; the right half shows through, with the mirrored left half filling its blank cells.", gi_fold, tf_fold)


# 35 stretch vertically by two -------------------------------------------------------------------------------------------
def gi_stretch(rng):
    h, w = rng.randint(2, 12), rng.randint(3, 16)
    return _noise(rng, h, w, 0.4)
def tf_stretch(g):
    return [row[:] for row in g for _ in range(2)]
rule("stretch_vertical_double", "Every row is doubled so the grid is twice as tall but no wider.", gi_stretch, tf_stretch)


# 36 interleave each row with its mirror -----------------------------------------------------------------------------------
def gi_inter(rng):
    h, w = rng.randint(2, 12), rng.randint(3, 16)
    return _noise(rng, h, w, 0.4)
def tf_inter(g):
    return [x for row in g for x in (row[:], row[::-1])]
rule("interleave_rows_with_mirror", "Under every row a left-right mirrored copy of it is inserted, doubling the height.", gi_inter, tf_inter)


# 37 roll each row by the value of its leading cell ---------------------------------------------------------------------
def gi_rollkey(rng):
    h, w = size(rng, 3, 14); g = _noise(rng, h, w, 0.35)
    for r in range(h): g[r][0] = rng.choice(COLOURS)
    return g
def tf_rollkey(g):
    return [_roll(row, row[0]) for row in g]
rule("roll_rows_by_leading_colour_value", "Each row is shifted right, wrapping, by as many cells as the number of its leftmost colour.", gi_rollkey, tf_rollkey, digits=True)


# 38 fill the triangle that holds the marker ----------------------------------------------------------------------------
def gi_tri(rng):
    n = rng.randint(4, 16); a, b = colours(rng, 2); g = blank(n, n); anti = rng.random() < 0.5
    for i in range(n): g[i][n - 1 - i if anti else i] = a
    r, c = rng.randrange(n), rng.randrange(n)
    if g[r][c]: return None
    g[r][c] = b
    return g
def tf_tri(g):
    n = len(g); out = copy(g)
    anti = sum(1 for i in range(n) if g[i][n - 1 - i]) > sum(1 for i in range(n) if g[i][i])
    side = lambda r, c: (r + c) - (n - 1) if anti else r - c
    marks = [(r, c) for r, c in cells(g, lambda v: v != 0) if side(r, c) != 0]
    if len(marks) != 1: return None
    (mr, mc), = marks; b = g[mr][mc]; s = side(mr, mc)
    for r in range(n):
        for c in range(n):
            if side(r, c) * s > 0: out[r][c] = b
    return out
rule("fill_triangle_holding_marker", "A diagonal line splits the square; the whole triangle containing the lone marker cell is filled with the marker's colour.", gi_tri, tf_tri)


# 39 concentric rings inward from a border ------------------------------------------------------------------------------
def gi_border(rng):
    h, w = size(rng, 5, 24); g = blank(h, w)
    return rect(g, 0, 0, h - 1, w - 1, rng.choice(COLOURS), fill=False)
def tf_border(g):
    h, w = dims(g); col = g[0][0]
    return [[col if min(r, c, h - 1 - r, w - 1 - c) % 2 == 0 else 0 for c in range(w)] for r in range(h)]
rule("rings_inward_from_border", "Starting from the coloured border, concentric rectangular rings alternate colour and black toward the centre.", gi_border, tf_border)


# 40 fractal: stamp the grid into each black cell -----------------------------------------------------------------------
def gi_fractal(rng):
    n = rng.randint(2, 5); g = _noise(rng, n, n, 0.5, [rng.choice(COLOURS)])
    k = sum(1 for row in g for v in row if v)
    return g if 1 <= k < n * n else None
def tf_fractal(g):
    n = len(g); out = blank(n * n, n * n)
    for r in range(n):
        for c in range(n):
            if g[r][c] == 0: paste(out, g, r * n, c * n)
    return out
rule("fractal_stamp_into_blank_cells", "The grid is enlarged by its own size; a copy of the grid is stamped where each black cell was and coloured cells become blank blocks.", gi_fractal, tf_fractal)
