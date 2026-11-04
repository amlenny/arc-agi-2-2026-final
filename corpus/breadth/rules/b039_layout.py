# b039_layout.py -- 40 rules: arranging objects into layouts by colour/size/position properties.
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


def _dims(rng, lo=6, hi=18):
    if rng.random() < 0.34:
        return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _rectshape(h, w):
    return [(r, c) for r in range(h) for c in range(w)]


def _sq(s):
    return _rectshape(s, s)


def _dot():
    return [(0, 0)]


def _scatter(rng, h, w, shapes, cols_, margin=1):
    g = blank(h, w)
    pos = place_shapes(rng, g, shapes, cols_, margin=margin)
    if pos is None:
        return None, None
    return g, pos


def _perimeter(h, w):
    pts = []
    for c in range(w): pts.append((0, c))
    for r in range(1, h): pts.append((r, w - 1))
    if h > 1:
        for c in range(w - 2, -1, -1): pts.append((h - 1, c))
    for r in range(h - 2, 0, -1): pts.append((r, 0))
    return pts


# 1 two colours of dots, stacked into a 2-column table (colour A left, colour B right)
def gi_table2col(rng):
    h, w = _dims(rng, 10, 20)
    k = rng.randint(3, min(7, h - 1))
    colA, colB = colours(rng, 2)
    na = rng.randint(1, k - 1); nb = k - na
    cols_ = [colA] * na + [colB] * nb
    rng.shuffle(cols_)
    shapes = [_dot() for _ in cols_]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_table2col(g):
    h, w = dims(g)
    present = sorted({v for row in g for v in row if v != 0})
    if len(present) != 2:
        return None
    colA, colB = present
    pts = sorted(cells(g, lambda v: v != 0), key=lambda rc: (rc[0], rc[1]))
    out = blank(h, w)
    ia = ib = 0
    for r, c in pts:
        col = g[r][c]
        if col == colA:
            if ia < h: out[ia][0] = col
            ia += 1
        else:
            if ib < h: out[ib][w - 1] = col
            ib += 1
    return out
rule("two_column_table_colour_classes", "Dots of one colour are stacked down the left column and dots of the other colour down the right column, in their original top-to-bottom order.", gi_table2col, tf_table2col)


# 2 interior dots moved onto the border, spaced around it in their original reading order
def gi_ringreading(rng):
    h, w = _dims(rng, 9, 20)
    k = rng.randint(3, 7)
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    shapes = [_dot() for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    if g is None:
        return None
    for r, c in pos:
        if r == 0 or c == 0 or r == h - 1 or c == w - 1:
            return None
    return g
def tf_ringreading(g):
    h, w = dims(g)
    pts = sorted(cells(g, lambda v: v != 0), key=lambda rc: (rc[0], rc[1]))
    if not pts:
        return None
    perim = _perimeter(h, w); P = len(perim); k = len(pts)
    out = blank(h, w)
    for i, (r, c) in enumerate(pts):
        pr, pc = perim[(i * P) // k]
        out[pr][pc] = g[r][c]
    return out
rule("ring_border_reading_order", "Every dot moves onto the grid's border, evenly spaced around the perimeter in the same left-to-right, top-to-bottom order the dots originally had.", gi_ringreading, tf_ringreading)


# 3 solid squares of varying size placed on the main diagonal, smallest first
def gi_diagsize(rng):
    h, w = _dims(rng, 20, 28)
    k = rng.randint(3, 5)
    sides = [rng.randint(1, 3) for _ in range(k)]
    if len(set(sides)) == 1:
        sides[0] = 1 if sides[0] != 1 else 3
    shapes = [_sq(s) for s in sides]
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=2)
    return g
def tf_diagsize(g):
    h, w = dims(g)
    obs = objects(g, 0)
    info = sorted(((len(o), g[o[0][0]][o[0][1]], bbox(o)[2] - bbox(o)[0] + 1) for o in obs), key=lambda t: t[0])
    k = len(info); n = min(h, w)
    if k < 2:
        return None
    maxs = max(s for _, _, s in info)
    step = max(2, (n - maxs) // (k - 1))
    out = blank(h, w)
    for i, (_, col, s) in enumerate(info):
        r0 = min(i * step, n - s)
        rect(out, r0, r0, r0 + s - 1, r0 + s - 1, col)
    return out
rule("diagonal_slots_by_size", "Every solid square object slides onto the main diagonal, ordered smallest to largest from the top-left corner.", gi_diagsize, tf_diagsize)


# 4 small squares sorted into a matrix: row by colour rank, column by size rank within that colour
def gi_matrixrc(rng):
    h, w = _dims(rng, 14, 24)
    cols_set = colours(rng, 3)
    objs = []
    for col in cols_set:
        for _ in range(rng.randint(1, 3)):
            objs.append((rng.randint(1, 3), col))
    rng.shuffle(objs)
    shapes = [_sq(s) for s, _ in objs]
    cols_ = [c for _, c in objs]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_matrixrc(g):
    h, w = dims(g)
    obs = objects(g, 0)
    byc = {}
    for o in obs:
        col = g[o[0][0]][o[0][1]]
        byc.setdefault(col, []).append(len(o))
    cols_sorted = sorted(byc)
    if len(cols_sorted) < 2:
        return None
    out = blank(h, w)
    step = 2
    for ri, col in enumerate(cols_sorted):
        sizes_sorted = sorted(byc[col])
        for ci, _ in enumerate(sizes_sorted):
            rr, cc = ri * step, ci * step
            if rr < h and cc < w:
                out[rr][cc] = col
    return out
rule("matrix_rows_colour_cols_size_rank", "Objects are collapsed to single markers and arranged into a table: row by colour, column by ascending size within that colour.", gi_matrixrc, tf_matrixrc)


# 5 scattered dots moved to the top row, evenly spaced, keeping left-to-right order
def gi_topedge(rng):
    h, w = _dims(rng, 10, 22)
    k = rng.randint(3, min(8, w))
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    shapes = [_dot() for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    if g is None:
        return None
    if any(r == 0 for r, _ in pos):
        return None
    return g
def tf_topedge(g):
    h, w = dims(g)
    pts = sorted(cells(g, lambda v: v != 0), key=lambda rc: rc[1])
    if not pts:
        return None
    k = len(pts)
    out = blank(h, w)
    for i, (r, c) in enumerate(pts):
        cc = (i * w) // k
        out[0][cc] = g[r][c]
    return out
rule("markers_evenly_along_top_edge", "Every dot moves to the top row, evenly spaced left to right, keeping the dots' original left-to-right order.", gi_topedge, tf_topedge)


# 6 each object moves into the corner of the quadrant it currently sits in
def gi_quadcorner(rng):
    h, w = _dims(rng, 14, 24)
    if h % 2: h += 1
    if w % 2: w += 1
    k = rng.randint(2, 4)
    shapes = [_sq(rng.randint(1, 3)) for _ in range(k)]
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_quadcorner(g):
    h, w = dims(g)
    obs = objects(g, 0)
    out = blank(h, w)
    for o in obs:
        r0, c0, r1, c1 = bbox(o); sh, sw = r1 - r0 + 1, c1 - c0 + 1
        col = g[o[0][0]][o[0][1]]
        cr, cc = (r0 + r1) / 2, (c0 + c1) / 2
        nr = 0 if cr < h / 2 else h - sh
        nc = 0 if cc < w / 2 else w - sw
        rect(out, nr, nc, nr + sh - 1, nc + sw - 1, col)
    return out
rule("quadrant_objects_to_matching_corner", "Each object slides to the single grid corner that lies in the same quadrant it currently occupies.", gi_quadcorner, tf_quadcorner)


# 7 translate the whole set of objects, preserving relative layout, so the group is centred
def gi_grouptranslate(rng):
    h, w = _dims(rng, 14, 24)
    k = rng.randint(2, 4)
    shapes = [_sq(rng.randint(1, 2)) for _ in range(k)]
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_grouptranslate(g):
    h, w = dims(g)
    pts = cells(g, lambda v: v != 0)
    if not pts:
        return None
    r0, c0, r1, c1 = bbox(pts)
    dr = (h - (r1 - r0 + 1)) // 2 - r0
    dc = (w - (c1 - c0 + 1)) // 2 - c0
    if dr == 0 and dc == 0:
        return None
    out = blank(h, w)
    for r, c in pts:
        nr, nc = r + dr, c + dc
        if 0 <= nr < h and 0 <= nc < w:
            out[nr][nc] = g[r][c]
    return out
rule("translate_group_to_grid_centre", "The whole set of objects slides as one rigid group, keeping their relative positions, so the group's bounding box is centred in the grid.", gi_grouptranslate, tf_grouptranslate)


# 8 keep a centre marker fixed; move the other dots to equal distance from it at the same angle
def gi_ringradius(rng):
    h, w = _dims(rng, 15, 25)
    if h % 2 == 0: h += 1
    if w % 2 == 0: w += 1
    cy, cx = h // 2, w // 2
    key = rng.choice(COLOURS)
    g = blank(h, w); g[cy][cx] = key
    k = rng.randint(2, 4)
    other = [c for c in COLOURS if c != key]
    maxr = min(cy, cx) - 1
    if maxr < 2:
        return None
    used = {(cy, cx)}
    for _ in range(k):
        for _try in range(30):
            ang = rng.uniform(0, 2 * math.pi); rad = rng.uniform(1.5, maxr)
            r = cy + round(rad * math.sin(ang)); c = cx + round(rad * math.cos(ang))
            if (r, c) not in used and 0 <= r < h and 0 <= c < w:
                used.add((r, c)); g[r][c] = rng.choice(other); break
        else:
            return None
    return g
def tf_ringradius(g):
    h, w = dims(g)
    pts = cells(g, lambda v: v != 0)
    cy, cx = None, None
    cnt = counts(g)
    key_col = None
    for p in pts:
        pass
    byc = {}
    for r, c in pts:
        byc.setdefault(g[r][c], []).append((r, c))
    key_col = next((c for c, v in byc.items() if len(v) == 1 and c == min(byc)), None)
    if key_col is None:
        return None
    cy, cx = byc[key_col][0]
    others = [(r, c, g[r][c]) for r, c in pts if (r, c) != (cy, cx)]
    if not others:
        return None
    R = min(cy, cx, h - 1 - cy, w - 1 - cx) - 1
    if R < 1:
        return None
    out = blank(h, w); out[cy][cx] = key_col
    used = {(cy, cx)}
    for r, c, col in others:
        ang = math.atan2(r - cy, c - cx)
        nr, nc = cy + round(R * math.sin(ang)), cx + round(R * math.cos(ang))
        tries = 0
        while (nr, nc) in used and tries < 8:
            ang += 0.15; nr, nc = cy + round(R * math.sin(ang)), cx + round(R * math.cos(ang)); tries += 1
        if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in used:
            used.add((nr, nc)); out[nr][nc] = col
    if len({v for row in out for v in row}) < 2:
        return None
    return out
rule("ring_around_marker_equal_radius", "A fixed centre marker stays put; every other dot moves to the same distance from it, keeping its original angle.", gi_ringradius, tf_ringradius)


# 9 dots placed into a fixed lattice of slots, ordered by ascending colour value
def gi_latticecolour(rng):
    h, w = _dims(rng, 14, 24)
    k = rng.randint(3, 6)
    cols_ = rng.sample(COLOURS, k)
    shapes = [_dot() for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_latticecolour(g):
    h, w = dims(g)
    pts = sorted(cells(g, lambda v: v != 0), key=lambda rc: g[rc[0]][rc[1]])
    if not pts:
        return None
    step = 2
    ncols = max(1, w // step)
    out = blank(h, w)
    for i, (r, c) in enumerate(pts):
        rr, cc = (i // ncols) * step, (i % ncols) * step
        if rr < h and cc < w:
            out[rr][cc] = g[r][c]
    return out
rule("lattice_slots_by_colour_value", "Dots are placed one per slot on a fixed grid lattice, in ascending order of their colour's numeric value.", gi_latticecolour, tf_latticecolour, digits=True)


# 10 grid split into horizontal bands, one object per band, pushed flush to the right
def gi_rjustify(rng):
    nb = 3
    bh = rng.randint(2, 4)
    h = nb * bh
    w = rng.randint(10, 20)
    g = blank(h, w)
    cols_ = colours(rng, nb)
    for i in range(nb):
        s = rng.randint(1, min(3, w - 2))
        c0 = rng.randint(0, w - s - 1)
        rect(g, i * bh, c0, i * bh, c0 + s - 1, cols_[i])
    return g
def tf_rjustify(g):
    h, w = dims(g)
    out = blank(h, w)
    bh = h // 3
    for i in range(3):
        row = i * bh
        run = [(c, g[row][c]) for c in range(w) if g[row][c] != 0]
        if not run:
            continue
        s = len(run); col = run[0][1]
        for j in range(s):
            out[row][w - 1 - j] = col
    if out == g:
        return None
    return out
rule("right_justify_per_row_band", "The grid is divided into horizontal bands, each holding one bar; every bar slides to the right edge of its band.", gi_rjustify, tf_rjustify)


# 11 objects at varying rows move vertically so their centres land on the middle row
def gi_aligncentre(rng):
    h, w = _dims(rng, 12, 20)
    if h % 2 == 0: h += 1
    k = rng.randint(2, 4)
    shapes = [_sq(rng.randint(1, 3)) for _ in range(k)]
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_aligncentre(g):
    h, w = dims(g)
    mid = h // 2
    obs = objects(g, 0)
    out = blank(h, w)
    for o in obs:
        r0, c0, r1, c1 = bbox(o); sh = r1 - r0 + 1
        col = g[o[0][0]][o[0][1]]
        nr = mid - sh // 2
        nr = max(0, min(h - sh, nr))
        rect(out, nr, c0, nr + sh - 1, c1, col)
    if out == g:
        return None
    return out
rule("align_centres_to_middle_row", "Every object slides vertically, without changing its column, so its centre lands on the grid's middle row.", gi_aligncentre, tf_aligncentre)


# 12 bars of varying length, several colours; stack each colour's bars by ascending length in its own column band
def gi_stacksize(rng):
    h, w = _dims(rng, 16, 26)
    cols_set = colours(rng, 3)
    objs = []
    for col in cols_set:
        for _ in range(rng.randint(2, 3)):
            objs.append((rng.randint(1, 4), col))
    rng.shuffle(objs)
    shapes = [[(0, i) for i in range(n)] for n, _ in objs]
    cols_ = [c for _, c in objs]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_stacksize(g):
    h, w = dims(g)
    obs = objects(g, 0)
    byc = {}
    for o in obs:
        col = g[o[0][0]][o[0][1]]
        byc.setdefault(col, []).append(len(o))
    cols_sorted = sorted(byc)
    if len(cols_sorted) < 2:
        return None
    out = blank(h, w)
    bandw = max(1, w // len(cols_sorted))
    for bi, col in enumerate(cols_sorted):
        lens = sorted(byc[col])
        c0 = bi * bandw
        for ri, n in enumerate(lens):
            if ri < h and c0 + n <= w:
                for j in range(n):
                    out[ri][c0 + j] = col
    return out
rule("stack_small_over_large_colour_column", "Bars are grouped by colour into their own column band, stacked with the shortest bar on top and the longest on the bottom.", gi_stacksize, tf_stacksize)


# 13 several small blobs scattered anywhere; each goes into its own panel of a contact-sheet grid
def gi_panelsheet(rng):
    h, w = _dims(rng, 15, 25)
    k = rng.randint(3, 4)
    shapes = [_sq(1) for _ in range(k)]
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=2)
    return g
def tf_panelsheet(g):
    h, w = dims(g)
    pts = sorted(cells(g, lambda v: v != 0), key=lambda rc: (rc[0], rc[1]))
    k = len(pts)
    if k < 2:
        return None
    pcols = math.ceil(math.sqrt(k)); prows = math.ceil(k / pcols)
    ph, pw = h // prows, w // pcols
    if ph < 1 or pw < 1:
        return None
    out = blank(h, w)
    for i, (r, c) in enumerate(pts):
        pr, pc = i // pcols, i % pcols
        out[pr * ph + ph // 2][pc * pw + pw // 2] = g[r][c]
    return out
rule("one_object_per_panel_sheet", "Objects are distributed one per panel of a contact-sheet grid, each centred in its own panel, in their original reading order.", gi_panelsheet, tf_panelsheet)


# 14 objects on the left half get a mirrored copy added on the right half
def gi_mirrordup(rng):
    h, w = _dims(rng, 12, 20)
    if w % 2: w += 1
    k = rng.randint(2, 4)
    shapes = [_sq(rng.randint(1, 2)) for _ in range(k)]
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    g = blank(h, w // 2)
    pos = place_shapes(rng, g, shapes, cols_, margin=1)
    if pos is None:
        return None
    return [row + [0] * (w // 2) for row in g]
def tf_mirrordup(g):
    h, w = dims(g)
    half = w // 2
    out = copy(g)
    for r in range(h):
        for c in range(half):
            if g[r][c] != 0:
                out[r][w - 1 - c] = g[r][c]
    if out == g:
        return None
    return out
rule("mirror_duplicate_opposite_side", "Every object confined to the left half gets a mirror-image copy added on the right half.", gi_mirrordup, tf_mirrordup)


# 15 dots of several colours scattered; regroup into horizontal bands, one per colour, ascending
def gi_colourrows(rng):
    h, w = _dims(rng, 14, 24)
    k = rng.randint(3, 5)
    cols_set = rng.sample(COLOURS, k)
    dots = []
    for col in cols_set:
        for _ in range(rng.randint(2, 4)):
            dots.append(col)
    rng.shuffle(dots)
    shapes = [_dot() for _ in dots]
    g, pos = _scatter(rng, h, w, shapes, dots, margin=1)
    return g
def tf_colourrows(g):
    h, w = dims(g)
    pts = cells(g, lambda v: v != 0)
    byc = {}
    for r, c in pts:
        byc.setdefault(g[r][c], []).append((r, c))
    cols_sorted = sorted(byc)
    if len(cols_sorted) < 2:
        return None
    nb = len(cols_sorted)
    bh = max(1, h // nb)
    out = blank(h, w)
    for bi, col in enumerate(cols_sorted):
        members = sorted(byc[col], key=lambda rc: rc[1])
        n = len(members); row = min(bi * bh, h - 1)
        for i in range(n):
            cc = (i * w) // n
            out[row][cc] = col
    return out
rule("colour_rows_banded_ascending", "Dots are regrouped into horizontal bands, one band per colour ordered by ascending colour value, spread evenly within the band.", gi_colourrows, tf_colourrows, digits=True)


# 16 objects of varying size scattered; sorted into 3 vertical bands by size tercile
def gi_sizecols(rng):
    h, w = _dims(rng, 16, 26)
    k = rng.randint(4, 6)
    shapes = [_sq(rng.randint(1, 4)) for _ in range(k)]
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_sizecols(g):
    h, w = dims(g)
    obs = objects(g, 0)
    if len(obs) < 3:
        return None
    info = sorted(((len(o), g[o[0][0]][o[0][1]]) for o in obs), key=lambda t: t[0])
    n = len(info)
    bands = [info[:n // 3] or info[:1], info[n // 3:2 * n // 3] or info[:1], info[2 * n // 3:] or info[-1:]]
    out = blank(h, w)
    bandw = max(1, w // 3)
    for bi, band in enumerate(bands):
        c0 = bi * bandw
        for ri, (_, col) in enumerate(band):
            if ri < h:
                out[ri][c0] = col
    if len({v for row in out for v in row}) < 2:
        return None
    return out
rule("size_tercile_columns", "Objects are collapsed to markers and sorted into three column bands by size tercile: small, medium, large, left to right.", gi_sizecols, tf_sizecols)


# 17 objects placed along a spiral path outward from centre, ordered by ascending size
def gi_spiralsize(rng):
    h, w = _dims(rng, 16, 26)
    k = rng.randint(3, 5)
    shapes = [_sq(rng.randint(1, 3)) for _ in range(k)]
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def _spiral(cy, cx, h, w):
    pts = [(cy, cx)]; r, c = cy, cx
    dr, dc = 0, 1; steps = 1; turns = 0
    while len(pts) < h * w:
        for _ in range(2):
            for _ in range(steps):
                r, c = r + dr, c + dc
                if 0 <= r < h and 0 <= c < w:
                    pts.append((r, c))
            dr, dc = -dc, dr
            turns += 1
        steps += 1
        if turns > 4 * (h + w):
            break
    return pts
def tf_spiralsize(g):
    h, w = dims(g)
    obs = objects(g, 0)
    info = sorted(((len(o), g[o[0][0]][o[0][1]]) for o in obs), key=lambda t: t[0])
    if len(info) < 2:
        return None
    path = _spiral(h // 2, w // 2, h, w)
    out = blank(h, w)
    used = set(); idx = 0
    for _, col in info:
        while idx < len(path) and path[idx] in used:
            idx += 1
        if idx >= len(path):
            break
        out[path[idx][0]][path[idx][1]] = col
        used.add(path[idx]); idx += 1
    return out
rule("spiral_slots_by_size", "Objects are collapsed to markers and placed along a spiral path outward from the centre, smallest object first.", gi_spiralsize, tf_spiralsize)


# 18 each object slides flush to whichever of the 4 edges it is currently closest to
def gi_nearestedge(rng):
    h, w = _dims(rng, 14, 24)
    k = rng.randint(2, 4)
    shapes = [_sq(rng.randint(1, 2)) for _ in range(k)]
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_nearestedge(g):
    h, w = dims(g)
    obs = objects(g, 0)
    out = blank(h, w)
    for o in obs:
        r0, c0, r1, c1 = bbox(o); sh, sw = r1 - r0 + 1, c1 - c0 + 1
        col = g[o[0][0]][o[0][1]]
        cr, cc = (r0 + r1) / 2, (c0 + c1) / 2
        d = {"top": cr, "bottom": h - 1 - cr, "left": cc, "right": w - 1 - cc}
        edge = min(d, key=d.get)
        nr, nc = r0, c0
        if edge == "top": nr = 0
        elif edge == "bottom": nr = h - sh
        elif edge == "left": nc = 0
        elif edge == "right": nc = w - sw
        rect(out, nr, nc, nr + sh - 1, nc + sw - 1, col)
    if out == g:
        return None
    return out
rule("slide_each_to_nearest_edge", "Each object slides flush against whichever of the four grid edges it currently sits closest to.", gi_nearestedge, tf_nearestedge)


# 19 dots with odd/even colour values snap onto a checkerboard pattern matching their parity
def gi_checkerparity(rng):
    h, w = _dims(rng, 14, 24)
    k = rng.randint(3, 6)
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    shapes = [_dot() for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_checkerparity(g):
    h, w = dims(g)
    pts = cells(g, lambda v: v != 0)
    if not pts:
        return None
    out = blank(h, w)
    used = set()
    for r, c in pts:
        col = g[r][c]; parity = col % 2
        best = None; bd = None
        for rr in range(h):
            for cc in range(w):
                if (rr + cc) % 2 == parity and (rr, cc) not in used:
                    d = abs(rr - r) + abs(cc - c)
                    if bd is None or d < bd:
                        bd = d; best = (rr, cc)
        if best:
            out[best[0]][best[1]] = col; used.add(best)
    if out == g or len({v for row in out for v in row}) < 2:
        return None
    return out
rule("checkerboard_slot_by_colour_parity", "Each dot snaps to the nearest checkerboard square whose colour (black or white) matches the parity of the dot's own colour value.", gi_checkerparity, tf_checkerparity, digits=True)


# 20 objects of varying size scattered; small ones move to a top row, large ones to a bottom row
def gi_mediansplit(rng):
    h, w = _dims(rng, 14, 24)
    k = rng.randint(4, 6)
    shapes = [_sq(rng.randint(1, 4)) for _ in range(k)]
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_mediansplit(g):
    h, w = dims(g)
    obs = objects(g, 0)
    if len(obs) < 3:
        return None
    sizes = sorted(len(o) for o in obs)
    med = sizes[len(sizes) // 2]
    small = [o for o in obs if len(o) <= med]
    large = [o for o in obs if len(o) > med]
    if not small or not large:
        return None
    out = blank(h, w)
    for i, o in enumerate(small):
        cc = (i * w) // max(1, len(small))
        out[0][cc] = g[o[0][0]][o[0][1]]
    for i, o in enumerate(large):
        cc = (i * w) // max(1, len(large))
        out[h - 1][cc] = g[o[0][0]][o[0][1]]
    return out
rule("median_split_rows_by_size", "Objects at or below the median size move to the top row; objects above it move to the bottom row, each spread evenly.", gi_mediansplit, tf_mediansplit)


# 21 objects placed on 4 cardinal rays from the centre, farther out for larger objects
def gi_fanrays(rng):
    h, w = _dims(rng, 16, 26)
    k = rng.randint(3, 6)
    shapes = [_sq(rng.randint(1, 3)) for _ in range(k)]
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_fanrays(g):
    h, w = dims(g)
    obs = objects(g, 0)
    if len(obs) < 2:
        return None
    info = sorted(((len(o), g[o[0][0]][o[0][1]]) for o in obs), key=lambda t: t[0])
    cy, cx = h // 2, w // 2
    dirs = [(-1, 0), (0, 1), (1, 0), (0, -1)]
    out = blank(h, w)
    for i, (_, col) in enumerate(info):
        dy, dx = dirs[i % 4]
        dist = i // 4 + 1
        r, c = cy + dy * dist, cx + dx * dist
        if 0 <= r < h and 0 <= c < w:
            out[r][c] = col
    if len({v for row in out for v in row}) < 2:
        return None
    return out
rule("fan_out_rays_by_size_rank", "Objects are collapsed to markers and placed along the four cardinal rays from the centre, farther out for each next size rank.", gi_fanrays, tf_fanrays)


# 22 objects move onto the vertical or horizontal axis through the centre, forming a plus
def gi_plusaxis(rng):
    h, w = _dims(rng, 14, 24)
    k = rng.randint(2, 4)
    shapes = [_sq(rng.randint(1, 2)) for _ in range(k)]
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_plusaxis(g):
    h, w = dims(g)
    cy, cx = h // 2, w // 2
    obs = objects(g, 0)
    out = blank(h, w)
    for o in obs:
        r0, c0, r1, c1 = bbox(o); sh, sw = r1 - r0 + 1, c1 - c0 + 1
        col = g[o[0][0]][o[0][1]]
        cr, cc = (r0 + r1) / 2, (c0 + c1) / 2
        if abs(cr - cy) >= abs(cc - cx):
            nc = cx - sw // 2; nr = r0
        else:
            nr = cy - sh // 2; nc = c0
        nr = max(0, min(h - sh, nr)); nc = max(0, min(w - sw, nc))
        rect(out, nr, nc, nr + sh - 1, nc + sw - 1, col)
    if out == g:
        return None
    return out
rule("plus_formation_by_axis_dominance", "Each object slides onto the horizontal or vertical centre axis, whichever its original offset was closer to, forming a plus shape.", gi_plusaxis, tf_plusaxis)


# 23 solid-square objects of differing size become concentric square border rings, largest outermost
def gi_concentric(rng):
    h, w = _dims(rng, 18, 26)
    if h != w:
        w = h
    k = rng.randint(2, 4)
    shapes = [_sq(rng.randint(1, 3)) for _ in range(k)]
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=2)
    return g
def tf_concentric(g):
    h, w = dims(g)
    obs = objects(g, 0)
    info = sorted(((len(o), g[o[0][0]][o[0][1]]) for o in obs), key=lambda t: -t[0])
    out = blank(h, w)
    n = min(h, w)
    for i, (_, col) in enumerate(info):
        inset = i * 2
        if n - 2 * inset < 1:
            break
        rect(out, inset, inset, h - 1 - inset, w - 1 - inset, col, fill=False)
    if len({v for row in out for v in row}) < 2:
        return None
    return out
rule("concentric_rings_by_size", "Objects are collapsed to concentric square border rings, the largest object forming the outermost ring and successively smaller objects nested inside.", gi_concentric, tf_concentric)


# 24 each dot's quadrant maps to a fixed edge-midpoint anchor (clock-style positions)
def gi_quadedge(rng):
    h, w = _dims(rng, 14, 24)
    if h % 2: h += 1
    if w % 2: w += 1
    k = rng.randint(2, 4)
    shapes = [_dot() for _ in range(k)]
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_quadedge(g):
    h, w = dims(g)
    pts = cells(g, lambda v: v != 0)
    out = blank(h, w)
    anchors = {(0, 0): (0, w // 4), (0, 1): (0, 3 * w // 4), (1, 0): (h - 1, w // 4), (1, 1): (h - 1, 3 * w // 4)}
    used = set()
    for r, c in pts:
        q = (1 if r >= h // 2 else 0, 1 if c >= w // 2 else 0)
        a = anchors[q]
        while a in used and a[1] + 1 < w:
            a = (a[0], a[1] + 1)
        used.add(a)
        out[a[0]][a[1]] = g[r][c]
    if out == g:
        return None
    return out
rule("quadrant_to_edge_anchor", "Each dot moves from its quadrant to that quadrant's fixed anchor point on the top or bottom edge.", gi_quadedge, tf_quadedge)


# 25 grid split into vertical column bands, one object per band, pushed flush to the bottom
def gi_bjustify(rng):
    nb = 3
    bw = rng.randint(2, 4)
    w = nb * bw
    h = rng.randint(10, 20)
    g = blank(h, w)
    cols_ = colours(rng, nb)
    for i in range(nb):
        s = rng.randint(1, min(3, h - 2))
        r0 = rng.randint(0, h - s - 1)
        rect(g, r0, i * bw, r0 + s - 1, i * bw, cols_[i])
    return g
def tf_bjustify(g):
    h, w = dims(g)
    out = blank(h, w)
    bw = w // 3
    for i in range(3):
        col_idx = i * bw
        run = [(r, g[r][col_idx]) for r in range(h) if g[r][col_idx] != 0]
        if not run:
            continue
        s = len(run); col = run[0][1]
        for j in range(s):
            out[h - 1 - j][col_idx] = col
    if out == g:
        return None
    return out
rule("bottom_justify_per_column_band", "The grid is divided into vertical bands, each holding one bar; every bar slides to the bottom of its band.", gi_bjustify, tf_bjustify)


# 26 objects split by a size threshold into two stacked columns: small left, large right
def gi_sizelr(rng):
    h, w = _dims(rng, 16, 26)
    k = rng.randint(4, 6)
    shapes = [_sq(rng.randint(1, 4)) for _ in range(k)]
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_sizelr(g):
    h, w = dims(g)
    obs = objects(g, 0)
    if len(obs) < 3:
        return None
    sizes = sorted(len(o) for o in obs)
    med = sizes[len(sizes) // 2]
    small = [o for o in obs if len(o) <= med]
    large = [o for o in obs if len(o) > med]
    if not small or not large:
        return None
    out = blank(h, w)
    for i, o in enumerate(small):
        if i < h: out[i][0] = g[o[0][0]][o[0][1]]
    for i, o in enumerate(large):
        if i < h: out[i][w - 1] = g[o[0][0]][o[0][1]]
    return out
rule("size_class_left_right_columns", "Objects at or below the median size stack down the left column; objects above it stack down the right column.", gi_sizelr, tf_sizelr)


# 27 scattered dots placed in reading order into a boustrophedon (zigzag) grid of slots
def gi_zigzag(rng):
    h, w = _dims(rng, 14, 24)
    k = rng.randint(5, 9)
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    shapes = [_dot() for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_zigzag(g):
    h, w = dims(g)
    pts = sorted(cells(g, lambda v: v != 0), key=lambda rc: (rc[0], rc[1]))
    k = len(pts)
    if k < 2:
        return None
    cols_n = min(w, max(2, math.ceil(math.sqrt(k))))
    out = blank(h, w)
    step = max(1, w // cols_n)
    for i, (r, c) in enumerate(pts):
        row = i // cols_n; pos_in_row = i % cols_n
        cc = pos_in_row if row % 2 == 0 else cols_n - 1 - pos_in_row
        if row < h and cc * step < w:
            out[row][cc * step] = g[r][c]
    return out
rule("zigzag_slots_by_reading_order", "Dots are laid into rows of slots alternating left-to-right then right-to-left, in their original reading order.", gi_zigzag, tf_zigzag)


# 28 up to 4 objects of differing size get a fixed rank-to-corner assignment
def gi_cornerrank(rng):
    h, w = _dims(rng, 14, 24)
    if h % 2: h += 1
    if w % 2: w += 1
    k = rng.randint(2, 4)
    sides = rng.sample([1, 2, 3, 4], k)
    shapes = [_sq(s) for s in sides]
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_cornerrank(g):
    h, w = dims(g)
    obs = objects(g, 0)
    if len(obs) < 2:
        return None
    info = sorted(((len(o), g[o[0][0]][o[0][1]], bbox(o)[2] - bbox(o)[0] + 1) for o in obs), key=lambda t: t[0])
    corners = [(0, 0), (0, "r"), ("b", 0), ("b", "r")]
    out = blank(h, w)
    for i, (_, col, s) in enumerate(info[:4]):
        cr, cc = corners[i]
        nr = 0 if cr == 0 else h - s
        nc = 0 if cc == 0 else w - s
        rect(out, nr, nc, nr + s - 1, nc + s - 1, col)
    return out
rule("corners_by_size_rank", "The smallest object moves to the top-left corner, the next to top-right, then bottom-left, then bottom-right, by ascending size rank.", gi_cornerrank, tf_cornerrank)


# 29 scattered dots re-sequenced into a single-file queue ordered by distance from the origin
def gi_queuedist(rng):
    h, w = _dims(rng, 14, 24)
    k = rng.randint(3, 6)
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    shapes = [_dot() for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_queuedist(g):
    h, w = dims(g)
    pts = cells(g, lambda v: v != 0)
    if len(pts) < 2:
        return None
    ranked = sorted(pts, key=lambda rc: rc[0] * rc[0] + rc[1] * rc[1])
    out = blank(h, w)
    mid = h // 2
    for i, (r, c) in enumerate(ranked):
        if i < w:
            out[mid][i] = g[r][c]
    return out
rule("queue_by_distance_from_origin", "Dots line up in a single row, ordered by increasing distance from the grid's top-left corner.", gi_queuedist, tf_queuedist)


# 30 dots of many colours sorted by colour value and wrapped row by row into a compact block
def gi_sortedwrap(rng):
    h, w = _dims(rng, 14, 24)
    k = rng.randint(4, 8)
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    shapes = [_dot() for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_sortedwrap(g):
    h, w = dims(g)
    pts = sorted(cells(g, lambda v: v != 0), key=lambda rc: g[rc[0]][rc[1]])
    k = len(pts)
    if k < 2:
        return None
    ncols = max(1, math.ceil(math.sqrt(k)))
    out = blank(h, w)
    for i, (r, c) in enumerate(pts):
        rr, cc = i // ncols, i % ncols
        if rr < h and cc < w:
            out[rr][cc] = g[r][c]
    return out
rule("colour_sorted_wrap_grid", "Dots are sorted by ascending colour value and packed row by row into a compact square block from the top-left.", gi_sortedwrap, tf_sortedwrap, digits=True)


# 31 4 objects, one per quadrant, rotate their quadrant assignment clockwise
def gi_pinwheel(rng):
    h, w = _dims(rng, 16, 26)
    if h % 2: h += 1
    if w % 2: w += 1
    hh, hw = h // 2, w // 2
    cols_ = colours(rng, 4)
    g = blank(h, w)
    quads = [(0, 0), (0, hw), (hh, 0), (hh, hw)]
    for (qr, qc), col in zip(quads, cols_):
        r = qr + rng.randint(0, hh - 2); c = qc + rng.randint(0, hw - 2)
        g[r][c] = col
    return g
def tf_pinwheel(g):
    h, w = dims(g)
    hh, hw = h // 2, w // 2
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 4:
        return None
    out = blank(h, w)
    for r, c in pts:
        qi = (0 if r < hh else 1, 0 if c < hw else 1)
        nxt = {(0, 0): (0, 1), (0, 1): (1, 1), (1, 1): (1, 0), (1, 0): (0, 0)}[qi]
        dr, dc = r % hh, c % hw
        nr = nxt[0] * hh + dr; nc = nxt[1] * hw + dc
        out[nr][nc] = g[r][c]
    if out == g:
        return None
    return out
rule("pinwheel_rotate_quadrant_objects", "The object in each quadrant swaps to the next quadrant clockwise, keeping its position relative to that quadrant's corner.", gi_pinwheel, tf_pinwheel)


# 32 dots placed on the border, ordered around it by ascending size instead of reading order
def gi_borderbysize(rng):
    h, w = _dims(rng, 14, 24)
    k = rng.randint(3, 6)
    shapes = [_sq(rng.randint(1, 3)) for _ in range(k)]
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=2)
    return g
def tf_borderbysize(g):
    h, w = dims(g)
    obs = objects(g, 0)
    if len(obs) < 2:
        return None
    info = sorted(((len(o), g[o[0][0]][o[0][1]]) for o in obs), key=lambda t: t[0])
    perim = _perimeter(h, w); P = len(perim); k = len(info)
    out = blank(h, w)
    for i, (_, col) in enumerate(info):
        pr, pc = perim[(i * P) // k]
        out[pr][pc] = col
    return out
rule("border_slots_by_size_order", "Objects are collapsed to markers and placed around the grid's border, walking clockwise from the top-left corner in order of ascending size.", gi_borderbysize, tf_borderbysize)


# 33 up to 4 objects placed on the diagonals, farther out for each next size rank, forming a diamond
def gi_diamond(rng):
    h, w = _dims(rng, 16, 26)
    if h != w: w = h
    k = rng.randint(2, 4)
    shapes = [_sq(rng.randint(1, 2)) for _ in range(k)]
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_diamond(g):
    h, w = dims(g)
    obs = objects(g, 0)
    if len(obs) < 2:
        return None
    info = sorted(((len(o), g[o[0][0]][o[0][1]]) for o in obs), key=lambda t: t[0])
    cy, cx = h // 2, w // 2
    diags = [(-1, -1), (-1, 1), (1, 1), (1, -1)]
    out = blank(h, w)
    for i, (_, col) in enumerate(info[:4]):
        dy, dx = diags[i % 4]
        dist = i // 4 + 2
        r, c = cy + dy * dist, cx + dx * dist
        if 0 <= r < h and 0 <= c < w:
            out[r][c] = col
    if len({v for row in out for v in row}) < 2:
        return None
    return out
rule("diamond_points_by_size_rank", "Objects are collapsed to markers and placed on the four diagonals from the centre, farther out for each next size rank, forming a diamond.", gi_diamond, tf_diamond)


# 34 dots of several colours scattered; regroup so every occurrence of a colour sits in one dedicated column
def gi_onecolumn(rng):
    h, w = _dims(rng, 14, 24)
    k = rng.randint(3, 5)
    cols_set = rng.sample(COLOURS, k)
    dots = []
    for col in cols_set:
        for _ in range(rng.randint(2, 4)):
            dots.append(col)
    rng.shuffle(dots)
    shapes = [_dot() for _ in dots]
    g, pos = _scatter(rng, h, w, shapes, dots, margin=1)
    return g
def tf_onecolumn(g):
    h, w = dims(g)
    pts = cells(g, lambda v: v != 0)
    byc = {}
    for r, c in pts:
        byc.setdefault(g[r][c], []).append((r, c))
    cols_sorted = sorted(byc)
    if len(cols_sorted) < 2:
        return None
    out = blank(h, w)
    step = max(1, w // len(cols_sorted))
    for ci, col in enumerate(cols_sorted):
        members = sorted(byc[col], key=lambda rc: rc[0])
        cc = ci * step
        for ri, _ in enumerate(members):
            if ri < h:
                out[ri][cc] = col
    return out
rule("columns_one_per_colour", "Every dot of a given colour is regrouped into that colour's own dedicated column, stacked from the top in original top-to-bottom order.", gi_onecolumn, tf_onecolumn, digits=True)


# 35 scattered dots repositioned evenly along the main diagonal, in their original reading order
def gi_diagreading(rng):
    h, w = _dims(rng, 14, 24)
    k = rng.randint(3, 7)
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    shapes = [_dot() for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_diagreading(g):
    h, w = dims(g)
    pts = sorted(cells(g, lambda v: v != 0), key=lambda rc: (rc[0], rc[1]))
    k = len(pts)
    if k < 2:
        return None
    n = min(h, w)
    out = blank(h, w)
    for i, (r, c) in enumerate(pts):
        d = (i * (n - 1)) // (k - 1) if k > 1 else 0
        out[d][d] = g[r][c]
    return out
rule("diagonal_evenly_by_reading_order", "Dots move onto the main diagonal, evenly spaced from corner to corner, kept in their original reading order.", gi_diagreading, tf_diagreading)


# 36 dots around a centre marker snap to one of 8 compass directions at a fixed radius per direction
def gi_compassbucket(rng):
    h, w = _dims(rng, 17, 27)
    if h % 2 == 0: h += 1
    if w % 2 == 0: w += 1
    cy, cx = h // 2, w // 2
    key = rng.choice(COLOURS)
    g = blank(h, w); g[cy][cx] = key
    other = [c for c in COLOURS if c != key]
    k = rng.randint(3, 6)
    maxr = min(cy, cx) - 1
    if maxr < 2:
        return None
    used = {(cy, cx)}
    for _ in range(k):
        for _try in range(30):
            ang = rng.uniform(0, 2 * math.pi); rad = rng.uniform(1.5, maxr)
            r = cy + round(rad * math.sin(ang)); c = cx + round(rad * math.cos(ang))
            if (r, c) not in used and 0 <= r < h and 0 <= c < w:
                used.add((r, c)); g[r][c] = rng.choice(other); break
        else:
            return None
    return g
def tf_compassbucket(g):
    h, w = dims(g)
    pts = cells(g, lambda v: v != 0)
    byc = {}
    for r, c in pts:
        byc.setdefault(g[r][c], []).append((r, c))
    key_col = min(byc)
    if len(byc[key_col]) != 1:
        return None
    cy, cx = byc[key_col][0]
    others = [(r, c, g[r][c]) for r, c in pts if (r, c) != (cy, cx)]
    if not others:
        return None
    R = min(cy, cx, h - 1 - cy, w - 1 - cx) - 1
    if R < 1:
        return None
    out = blank(h, w); out[cy][cx] = key_col
    used = {(cy, cx)}
    buckets = [i * math.pi / 4 for i in range(8)]
    for r, c, col in others:
        ang = math.atan2(r - cy, c - cx)
        bang = min(buckets, key=lambda b: min(abs(b - ang), 2 * math.pi - abs(b - ang)))
        nr, nc = cy + round(R * math.sin(bang)), cx + round(R * math.cos(bang))
        tries = 0
        step_r = R
        while (nr, nc) in used and tries < 6:
            step_r -= 1
            nr, nc = cy + round(step_r * math.sin(bang)), cx + round(step_r * math.cos(bang))
            tries += 1
        if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in used:
            used.add((nr, nc)); out[nr][nc] = col
    if len({v for row in out for v in row}) < 2:
        return None
    return out
rule("compass_bucket_slots_around_marker", "Every dot around the fixed centre marker snaps to the nearest of eight compass directions, at a shared fixed distance from the marker.", gi_compassbucket, tf_compassbucket)


# 37 objects of varying size scattered; small ones move to a left column, large ones to a right column
def gi_mediancols(rng):
    h, w = _dims(rng, 14, 24)
    k = rng.randint(4, 6)
    shapes = [_sq(rng.randint(1, 4)) for _ in range(k)]
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_mediancols(g):
    h, w = dims(g)
    obs = objects(g, 0)
    if len(obs) < 3:
        return None
    sizes = sorted(len(o) for o in obs)
    med = sizes[len(sizes) // 2]
    small = [o for o in obs if len(o) <= med]
    large = [o for o in obs if len(o) > med]
    if not small or not large:
        return None
    out = blank(h, w)
    for i, o in enumerate(small):
        rr = (i * h) // max(1, len(small))
        out[rr][0] = g[o[0][0]][o[0][1]]
    for i, o in enumerate(large):
        rr = (i * h) // max(1, len(large))
        out[rr][w - 1] = g[o[0][0]][o[0][1]]
    return out
rule("median_split_columns_by_size", "Objects at or below the median size move to the left column, spread evenly; objects above it move to the right column.", gi_mediancols, tf_mediancols)


# 38 bars of varying width stacked into two rows, the second row offset by half a bar width
def gi_stagger(rng):
    h, w = _dims(rng, 14, 24)
    k = rng.randint(4, 7)
    widths = [rng.randint(1, 3) for _ in range(k)]
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    shapes = [[(0, i) for i in range(wd)] for wd in widths]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_stagger(g):
    h, w = dims(g)
    obs = objects(g, 0)
    if len(obs) < 2:
        return None
    info = sorted(((bbox(o)[3] - bbox(o)[1] + 1, g[o[0][0]][o[0][1]]) for o in obs), key=lambda t: (t[0], t[1]))
    out = blank(h, w)
    row0_x = 0; row1_x = max(1, (info[0][0] if info else 1) // 2)
    for i, (wd, col) in enumerate(info):
        row = i % 2
        if row == 0:
            if row0_x + wd <= w and 0 < h:
                rect(out, 0, row0_x, 0, row0_x + wd - 1, col); row0_x += wd
        else:
            if row1_x + wd <= w and 1 < h:
                rect(out, 1, row1_x, 1, row1_x + wd - 1, col); row1_x += wd
    if len({v for row in out for v in row}) < 2:
        return None
    return out
rule("staggered_rows_by_width", "Bars are packed in ascending width order into two brick-wall rows, the second row offset by half a bar width from the first.", gi_stagger, tf_stagger)


# 39 up to 4 objects, one per quadrant; each slides to the centre of its own quadrant
def gi_centrequad(rng):
    h, w = _dims(rng, 14, 24)
    if h % 2: h += 1
    if w % 2: w += 1
    k = rng.randint(2, 4)
    shapes = [_sq(rng.randint(1, 2)) for _ in range(k)]
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_centrequad(g):
    h, w = dims(g)
    hh, hw = h // 2, w // 2
    obs = objects(g, 0)
    out = blank(h, w)
    for o in obs:
        r0, c0, r1, c1 = bbox(o); sh, sw = r1 - r0 + 1, c1 - c0 + 1
        col = g[o[0][0]][o[0][1]]
        cr, cc = (r0 + r1) / 2, (c0 + c1) / 2
        qr, qc = (0 if cr < hh else 1), (0 if cc < hw else 1)
        qh, qw = hh, hw
        nr = qr * (h - hh) + (qh - sh) // 2
        nc = qc * (w - hw) + (qw - sw) // 2
        nr = max(0, min(h - sh, nr)); nc = max(0, min(w - sw, nc))
        rect(out, nr, nc, nr + sh - 1, nc + sw - 1, col)
    if out == g:
        return None
    return out
rule("centre_each_in_own_quadrant", "Each object slides to the centre of whichever quadrant it currently occupies, without leaving that quadrant.", gi_centrequad, tf_centrequad)


# 40 objects placed in reading order into a boustrophedon grid of slots, ordered by ascending size
def gi_snakesize(rng):
    h, w = _dims(rng, 15, 25)
    k = rng.randint(4, 8)
    shapes = [_sq(rng.randint(1, 3)) for _ in range(k)]
    cols_ = [rng.choice(COLOURS) for _ in range(k)]
    g, pos = _scatter(rng, h, w, shapes, cols_, margin=1)
    return g
def tf_snakesize(g):
    h, w = dims(g)
    obs = objects(g, 0)
    if len(obs) < 2:
        return None
    info = sorted(((len(o), g[o[0][0]][o[0][1]]) for o in obs), key=lambda t: t[0])
    k = len(info)
    cols_n = min(w, max(2, math.ceil(math.sqrt(k))))
    step = max(1, w // cols_n)
    out = blank(h, w)
    for i, (_, col) in enumerate(info):
        row = i // cols_n; pos_in_row = i % cols_n
        cc = pos_in_row if row % 2 == 0 else cols_n - 1 - pos_in_row
        if row < h and cc * step < w:
            out[row][cc * step] = col
    return out
rule("snake_slots_by_size_rank", "Objects are collapsed to markers and laid into rows of slots alternating direction, ordered by ascending size.", gi_snakesize, tf_snakesize)
