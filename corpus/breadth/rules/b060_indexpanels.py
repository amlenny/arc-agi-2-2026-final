# b060_indexpanels.py -- A SMALL GRID INDEXES A GRID OF PANELS: a 3x3 selector sits above a grey
# separator above a 3x3 grid of panels. The selector's marked/coloured cells name, recolour, reorder,
# wipe, overlay or otherwise index the panels below by row-major position (row i, col j -> panel i*3+j).
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

SEP = 5
IDX = [(i, j) for i in range(3) for j in range(3)]


# ---------- local panel-grid plumbing (copied locally per AUTHORING.md; do not import other batches) ----------
def _patt(rng, h, w, cols, density=0.5):
    p = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < density:
                p[r][c] = rng.choice(cols)
    if not any(v for row in p for v in row):
        p[rng.randrange(h)][rng.randrange(w)] = rng.choice(cols)
    return p


def _hpanels(panels, sep=SEP):
    out = [list(panels[0][r]) for r in range(len(panels[0]))]
    for p in panels[1:]:
        for r in range(len(out)):
            out[r] += [sep] + p[r]
    return out


def _vpanels(panels, sep=SEP):
    out = [row[:] for row in panels[0]]
    for p in panels[1:]:
        out.append([sep] * len(out[0])); out += [row[:] for row in p]
    return out


def _split_cols(g, sep=SEP):
    H, W = dims(g); parts, cur = [], []
    for c in range(W):
        if all(g[r][c] == sep for r in range(H)):
            if cur: parts.append(cur); cur = []
        else:
            cur.append(c)
    if cur: parts.append(cur)
    return [[[g[r][c] for c in cs] for r in range(H)] for cs in parts]


def _split_rows(g, sep=SEP):
    return [transpose(p) for p in _split_cols(transpose(g), sep)]


def _grid_split(g, sep=SEP):
    return [_split_cols(band, sep) for band in _split_rows(g, sep)]


def _panel_grid(rng, m, n, make):
    return _vpanels([_hpanels([make(i, j) for j in range(n)]) for i in range(m)])


def _dom(p):
    cnt = counts(p); cnt.pop(0, None)
    return max(cnt.items(), key=lambda kv: kv[1])[0] if cnt else 0


def _hgap(a, b, gap=1, fill=0):
    return [ra + [fill] * gap + rb for ra, rb in zip(a, b)]


def _crop_nonbg(p):
    pts = cells(p, lambda v: v != 0)
    if not pts: return None
    r0, c0, r1, c1 = bbox(pts)
    return crop(p, r0, c0, r1, c1)


def _nonconst(g):
    return g if g is not None and len({v for row in g for v in row}) > 1 else None


# ---------- scene builder: 3x3 selector (cells h_sel x s) over SEP over 3x3 panel grid (cells s x s) ----------
def _s(rng, lo=2, hi=7):
    return rng.randint(lo, hi)


def _sel(rng, s, marks, h_sel=1):
    """marks: dict idx(0-8) -> colour for marked cells; unlisted idx are 0."""
    def mk(i, j):
        return blank(h_sel, s, marks.get(i * 3 + j, 0))
    return _panel_grid(rng, 3, 3, mk)


def _sel_digit(rng, s, marks):
    """Like _sel but for digit values that may equal SEP (5): a blank anchor row keeps a
    digit-5 cell's own column from ever being entirely SEP, which would be misread as a separator."""
    def mk(i, j):
        v = marks.get(i * 3 + j, 0)
        return [[0] * s, [v] * s]
    return _panel_grid(rng, 3, 3, mk)


def _pan(rng, s, cols, special=None, density=0.5):
    special = special or {}
    def mk(i, j):
        idx = i * 3 + j
        return special[idx] if idx in special else _patt(rng, s, s, cols, density)
    return _panel_grid(rng, 3, 3, mk)


def _compose(sel, pan):
    return _vpanels([sel, pan])


def _parse(g):
    gp = _grid_split(g)
    if len(gp) != 6 or any(len(b) != 3 for b in gp):
        return None
    sel = [[_dom(gp[i][j]) for j in range(3)] for i in range(3)]
    pan = [[gp[3 + i][j] for j in range(3)] for i in range(3)]
    return sel, pan


def _flat(m):
    return [m[i][j] for i in range(3) for j in range(3)]


def _marked(flat_sel):
    return [k for k, v in enumerate(flat_sel) if v]


# =========================================================================================
# 1
def gi_1(rng):
    s = _s(rng); cols = colours(rng, 4, exclude=(0, SEP))
    idx = rng.randrange(9); mc = rng.choice(cols)
    return _compose(_sel(rng, s, {idx: mc}), _pan(rng, s, cols))
def tf_1(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; m = _marked(_flat(sel))
    if len(m) != 1: return None
    i, j = divmod(m[0], 3)
    return pan[i][j]
rule("selector_single_mark_selects_panel", "The 3x3 selector above the separator has exactly one coloured cell; the output is the panel at that same row-major position (row i, column j -> panel i,j) in the 3x3 panel grid below, unchanged.", gi_1, tf_1)


# 2
def gi_2(rng):
    s = _s(rng, 3, 7); cols = colours(rng, 4, exclude=(0, SEP))
    idx = rng.randrange(9); mc = rng.choice(cols)
    return _compose(_sel(rng, s, {idx: mc}), _pan(rng, s, cols, density=0.35))
def tf_2(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; m = _marked(_flat(sel))
    if len(m) != 1: return None
    i, j = divmod(m[0], 3)
    out = _crop_nonbg(pan[i][j])
    if out is None: return None
    return out if (len(out) < len(pan[i][j]) or len(out[0]) < len(pan[i][j][0])) else None
rule("selector_single_mark_crops_marked_panel_to_content", "The selector's one coloured cell names a panel by its row-major position; the output is that panel cropped tightly to the bounding box of its non-background cells.", gi_2, tf_2)


# 3
def gi_3(rng):
    s = _s(rng); cols = colours(rng, 4, exclude=(0, SEP))
    idx = rng.randrange(9); mc = rng.choice(cols)
    return _compose(_sel(rng, s, {idx: mc}), _pan(rng, s, cols))
def tf_3(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; m = _marked(_flat(sel))
    if len(m) != 1: return None
    i, j = divmod(m[0], 3)
    return rot90(pan[i][j])
rule("selector_single_mark_outputs_panel_rotated_90cw", "The selector's one coloured cell names a panel by its row-major position; the output is that panel rotated ninety degrees clockwise.", gi_3, tf_3)


# 4
def gi_4(rng):
    s = _s(rng); cols = colours(rng, 4, exclude=(0, SEP))
    idx = rng.randrange(9); mc = rng.choice(cols)
    return _compose(_sel(rng, s, {idx: mc}), _pan(rng, s, cols))
def tf_4(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; m = _marked(_flat(sel))
    if len(m) != 1: return None
    i, j = divmod(m[0], 3)
    return transpose(pan[i][j])
rule("selector_single_mark_outputs_panel_transposed", "The selector's one coloured cell names a panel by its row-major position; the output is that panel transposed across its main diagonal.", gi_4, tf_4)


# 5
def gi_5(rng):
    s = _s(rng, 3, 7); cols = colours(rng, 4, exclude=(0, SEP))
    idx = rng.randrange(9); mc = rng.choice(cols)
    return _compose(_sel(rng, s, {idx: mc}), _pan(rng, s, cols, density=0.45))
def tf_5(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; m = _marked(_flat(sel))
    if len(m) != 1: return None
    i, j = divmod(m[0], 3); p = pan[i][j]; d = _dom(p)
    if d == 0 or 0 not in {v for row in p for v in row}: return None
    return [[d if v else 0 for v in row] for row in p]
rule("selector_single_mark_outputs_panel_dominant_colour_block", "The selector's one coloured cell names a panel by its row-major position; the output is that panel with every non-background cell repainted to that panel's own most frequent colour.", gi_5, tf_5)


# 6
def gi_6(rng):
    s = _s(rng); cols = colours(rng, 4, exclude=(0, SEP)); k = rng.randint(1, 9)
    idxs = rng.sample(range(9), k); mc = rng.choice(cols)
    return _compose(_sel(rng, s, {i: mc for i in idxs}), _pan(rng, s, cols))
def tf_6(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; k = len(_marked(_flat(sel)))
    if k < 1 or k > 9: return None
    i, j = divmod(k - 1, 3)
    return pan[i][j]
rule("selector_mark_count_selects_nth_panel_reading_order", "Count the selector's coloured cells (k); the output is the k-th panel counting left to right, top to bottom through the 3x3 panel grid (k=1 is the top-left panel), unchanged.", gi_6, tf_6)


# 7
def gi_7(rng):
    k = rng.randint(2, 4); s = rng.randint(2, min(7, (30 - (k - 1)) // k)); cols = colours(rng, 4, exclude=(0, SEP))
    idxs = rng.sample(range(9), k); mc = rng.choice(cols)
    return _compose(_sel(rng, s, {i: mc for i in idxs}), _pan(rng, s, cols))
def tf_7(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; m = _marked(_flat(sel))
    if len(m) < 2: return None
    panels = [pan[i][j] for i, j in (divmod(k, 3) for k in m)]
    return _hpanels(panels)
rule("selector_marked_panels_assembled_row_reading_order", "The selector's coloured cells name two or more panels; the output joins exactly those panels side by side, in reading order (left to right, top to bottom) of their selector position, with grey separators between them.", gi_7, tf_7)


# 8
def gi_8(rng):
    k = rng.randint(2, 4); s = rng.randint(2, min(7, (30 - (k - 1)) // k)); cols = colours(rng, 4, exclude=(0, SEP))
    idxs = rng.sample(range(9), k); mc = rng.choice(cols)
    return _compose(_sel(rng, s, {i: mc for i in idxs}), _pan(rng, s, cols))
def tf_8(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; m = sorted(_marked(_flat(sel)), key=lambda k: (k % 3, k // 3))
    if len(m) < 2: return None
    panels = [pan[i][j] for i, j in (divmod(k, 3) for k in m)]
    return _vpanels(panels)
rule("selector_marked_panels_assembled_column_major", "The selector's coloured cells name two or more panels; the output stacks exactly those panels top to bottom, in column-major order of their selector position (column 0 top-to-bottom, then column 1, then column 2), with grey separators between them.", gi_8, tf_8)


# 9
def gi_9(rng):
    k = rng.randint(2, 3); s = _s(rng, 4, 7); cols = colours(rng, 4, exclude=(0, SEP))
    idxs = rng.sample(range(9), k); mc = rng.choice(cols)
    return _compose(_sel(rng, s, {i: mc for i in idxs}), _pan(rng, s, cols, density=0.35))
def tf_9(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; m = _marked(_flat(sel))
    if len(m) < 2: return None
    crops = [_crop_nonbg(pan[i][j]) for i, j in (divmod(k, 3) for k in m)]
    if any(c is None for c in crops): return None
    return _hpanels(crops)
rule("selector_marked_panels_cropped_and_joined", "The selector's coloured cells name two or more panels; each named panel is cropped to the bounding box of its non-background cells and the crops are joined side by side in reading order, with grey separators between them.", gi_9, tf_9)


# 10
def gi_10(rng):
    s = _s(rng); cols = colours(rng, 5, exclude=(0, SEP))
    a, b = rng.sample(range(9), 2); mc = rng.choice(cols)
    return _compose(_sel(rng, s, {a: mc, b: mc}), _pan(rng, s, cols))
def tf_10(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; m = _marked(_flat(sel))
    if len(m) != 2: return None
    a, b = m; ai, aj = divmod(a, 3); bi, bj = divmod(b, 3)
    panels = [[list(r) for r in pan[i][j]] for i in range(3) for j in range(3)]
    flat = [panels[i] for i in range(9)]
    flat[a], flat[b] = flat[b], flat[a]
    npan = [[flat[i * 3 + j] for j in range(3)] for i in range(3)]
    return _vpanels([_hpanels(row) for row in npan])
rule("selector_marked_pair_panels_swap_positions", "Exactly two selector cells share a colour; the two panels at those row-major positions trade places in the 3x3 panel grid while every other panel stays put, grey separators redrawn.", gi_10, tf_10)


# 11
def gi_11(rng):
    s = _s(rng); cols = colours(rng, 5, exclude=(0, SEP))
    a, b = rng.sample(range(9), 2); mc = rng.choice(cols)
    return _compose(_sel(rng, s, {a: mc, b: mc}), _pan(rng, s, cols))
def tf_11(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; m = _marked(_flat(sel))
    if len(m) != 2: return None
    a, b = m; ai, aj = divmod(a, 3); bi, bj = divmod(b, 3)
    da, db = _dom(pan[ai][aj]), _dom(pan[bi][bj])
    if da == 0 or db == 0 or da == db: return None
    npan = [[[row[:] for row in pan[i][j]] for j in range(3)] for i in range(3)]
    npan[ai][aj] = [[db if v == da else v for v in row] for row in pan[ai][aj]]
    npan[bi][bj] = [[da if v == db else v for v in row] for row in pan[bi][bj]]
    return _vpanels([_hpanels(row) for row in npan])
rule("selector_marked_pair_panels_swap_colours", "Exactly two selector cells share a colour; the two panels at those row-major positions keep their place but trade dominant colours with each other, every other panel left unchanged.", gi_11, tf_11)


# 12
def gi_12(rng):
    s = _s(rng); cols = colours(rng, 4, exclude=(0, SEP))
    a, b = rng.sample(range(9), 2); mc = rng.choice(cols)
    return _compose(_sel(rng, s, {a: mc, b: mc}), _pan(rng, s, cols, density=0.4))
def tf_12(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; m = _marked(_flat(sel))
    if len(m) != 2: return None
    a, b = m; pa = pan[a // 3][a % 3]; pb = pan[b // 3][b % 3]
    out = [[pa[r][c] if pa[r][c] else pb[r][c] for c in range(len(pa[0]))] for r in range(len(pa))]
    return _nonconst(out)
rule("selector_two_marks_overlay_panels_or", "Exactly two selector cells share a colour, naming two panels in order of their row-major position; the output overlays them into one panel the same size, a cell taking the first-named panel's colour if it is non-background there, else the second-named panel's colour.", gi_12, tf_12)


# 13
def gi_13(rng):
    s = _s(rng, 3, 7); cols = colours(rng, 4, exclude=(0, SEP))
    a, b = rng.sample(range(9), 2); mc = rng.choice(cols)
    return _compose(_sel(rng, s, {a: mc, b: mc}), _pan(rng, s, cols, density=0.3))
def tf_13(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; m = _marked(_flat(sel))
    if len(m) != 2: return None
    a, b = m; pa = pan[a // 3][a % 3]; pb = pan[b // 3][b % 3]
    merged = [[pa[r][c] if pa[r][c] else pb[r][c] for c in range(len(pa[0]))] for r in range(len(pa))]
    out = _crop_nonbg(merged)
    return _nonconst(out)
rule("selector_two_marks_overlay_panels_or_cropped", "Exactly two selector cells share a colour, naming two panels in order of their row-major position; the output overlays them (first-named panel's colour wins where both are coloured) and crops the result to its non-background bounding box.", gi_13, tf_13)


# 14
def gi_14(rng):
    s = _s(rng, 3, 7); cols = colours(rng, 3, exclude=(0, SEP))
    a, b = rng.sample(range(9), 2); mc = rng.choice(cols)
    return _compose(_sel(rng, s, {a: mc, b: mc}), _pan(rng, s, cols, density=0.55))
def tf_14(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; m = _marked(_flat(sel))
    if len(m) != 2: return None
    a, b = m; pa = pan[a // 3][a % 3]; pb = pan[b // 3][b % 3]
    out = [[pa[r][c] if (pa[r][c] and pa[r][c] == pb[r][c]) else 0 for c in range(len(pa[0]))] for r in range(len(pa))]
    return _nonconst(out)
rule("selector_two_marks_overlay_panels_and", "Exactly two selector cells share a colour, naming two panels; the output keeps a cell's colour only where both named panels have that same non-background colour at that cell, and is background everywhere else.", gi_14, tf_14)


# 15
def gi_15(rng):
    s = _s(rng); cols = colours(rng, 5, exclude=(0, SEP))
    assign = {i: rng.choice(cols) for i in range(9)}
    return _compose(_sel(rng, s, assign), _pan(rng, s, cols, density=0.5))
def tf_15(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr
    npan = [[[[sel[i][j] if v else 0 for v in row] for row in pan[i][j]] for j in range(3)] for i in range(3)]
    return _nonconst(_vpanels([_hpanels(row) for row in npan]))
rule("selector_cells_recolour_their_panels", "Every selector cell carries a colour; each panel's non-background cells are repainted with the colour of the selector cell at that same row-major position, backgrounds left alone, grey separators redrawn.", gi_15, tf_15)


# 16
def gi_16(rng):
    s = _s(rng); cols = colours(rng, 4, exclude=(0, SEP)); mc = rng.choice(cols)
    keep = set(rng.sample(range(9), rng.randint(2, 7)))
    return _compose(_sel(rng, s, {i: mc for i in keep}), _pan(rng, s, cols, density=0.5))
def tf_16(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; flat = _flat(sel); m = set(_marked(flat))
    if not m or len(m) == 9: return None
    npan = [[pan[i][j] if (i * 3 + j) in m else blank(len(pan[i][j]), len(pan[i][j][0])) for j in range(3)] for i in range(3)]
    return _vpanels([_hpanels(row) for row in npan])
rule("selector_empty_cells_wipe_their_panels", "Selector cells are either coloured or empty; every panel whose selector cell is empty is wiped to background, every panel whose selector cell is coloured is left unchanged, grey separators redrawn.", gi_16, tf_16)


# 17
def gi_17(rng):
    s = _s(rng); cols = colours(rng, 4, exclude=(0, SEP)); mc = rng.choice(cols)
    keep = set(rng.sample(range(9), rng.randint(2, 7)))
    return _compose(_sel(rng, s, {i: mc for i in keep}), _pan(rng, s, cols, density=0.5))
def tf_17(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; m = set(_marked(_flat(sel)))
    if not m or len(m) == 9: return None
    npan = [[pan[i][j] if (i * 3 + j) in m else blank(len(pan[i][j]), len(pan[i][j][0]), SEP) for j in range(3)] for i in range(3)]
    return _vpanels([_hpanels(row) for row in npan])
rule("selector_marks_panels_to_keep_rest_filled_grey", "Selector cells are either coloured or empty; every panel whose selector cell is coloured is kept unchanged, every panel whose selector cell is empty is filled solid grey, grey separators redrawn.", gi_17, tf_17)


# 18
def gi_18(rng):
    s = _s(rng); cols = colours(rng, 5, exclude=(0, SEP)); a, b = rng.sample(cols, 2)
    marks = {}
    which = [rng.choice((a, b)) for _ in range(9)]
    if len(set(which)) < 2: which[0], which[1] = a, b
    marks = {i: which[i] for i in range(9)}
    return _compose(_sel(rng, s, marks), _pan(rng, s, cols, density=0.5))
def tf_18(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; vals = {v for v in _flat(sel) if v}
    if len(vals) != 2: return None
    a, b = sorted(vals)
    npan = [[[[b if v == a else (a if v == b else v) for v in row] for row in pan[i][j]] for j in range(3)] for i in range(3)]
    return _vpanels([_hpanels(row) for row in npan])
rule("selector_two_colours_swap_panels_globally", "The selector uses exactly two colours across its nine cells; in every panel, every cell of the first colour becomes the second colour and every cell of the second colour becomes the first, wherever that panel's selector cell falls, grey separators redrawn.", gi_18, tf_18)


# 19
def gi_19(rng):
    s = _s(rng); cols = colours(rng, 4, exclude=(0, SEP)); mc = rng.choice(cols)
    m = set(rng.sample(range(9), rng.randint(1, 6)))
    return _compose(_sel(rng, s, {i: mc for i in m}), _pan(rng, s, cols, density=0.4))
def tf_19(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; m = set(_marked(_flat(sel)))
    if not m: return None
    npan = [[flip_h(pan[i][j]) if (i * 3 + j) in m else pan[i][j] for j in range(3)] for i in range(3)]
    return _vpanels([_hpanels(row) for row in npan])
rule("selector_marked_panels_flip_horizontal", "The selector's coloured cells name one or more panels; each named panel is flipped left to right while every other panel stays as it was, grey separators redrawn.", gi_19, tf_19)


# 20
def gi_20(rng):
    s = _s(rng); cols = colours(rng, 4, exclude=(0, SEP)); mc = rng.choice(cols)
    m = set(rng.sample(range(9), rng.randint(1, 6)))
    return _compose(_sel(rng, s, {i: mc for i in m}), _pan(rng, s, cols, density=0.4))
def tf_20(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; m = set(_marked(_flat(sel)))
    if not m: return None
    npan = [[flip_v(pan[i][j]) if (i * 3 + j) in m else pan[i][j] for j in range(3)] for i in range(3)]
    return _vpanels([_hpanels(row) for row in npan])
rule("selector_marked_panels_flip_vertical", "The selector's coloured cells name one or more panels; each named panel is flipped top to bottom while every other panel stays as it was, grey separators redrawn.", gi_20, tf_20)


# 21
def gi_21(rng):
    s = _s(rng); cols = colours(rng, 4, exclude=(0, SEP)); mc = rng.choice(cols)
    m = set(rng.sample(range(9), rng.randint(1, 6)))
    return _compose(_sel(rng, s, {i: mc for i in m}), _pan(rng, s, cols, density=0.4))
def tf_21(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; m = set(_marked(_flat(sel)))
    if not m: return None
    npan = [[flip_h(flip_v(pan[i][j])) if (i * 3 + j) in m else pan[i][j] for j in range(3)] for i in range(3)]
    return _vpanels([_hpanels(row) for row in npan])
rule("selector_marked_panels_rotate_180", "The selector's coloured cells name one or more panels; each named panel is rotated a hundred eighty degrees while every other panel stays as it was, grey separators redrawn.", gi_21, tf_21)


# 22 (digits)
def gi_22(rng):
    s = _s(rng); cols = colours(rng, 5, exclude=(0, SEP))
    perm = list(range(1, 10)); rng.shuffle(perm)
    marks = {i: perm[i] for i in range(9)}
    return _compose(_sel_digit(rng, s, marks), _pan(rng, s, cols, density=0.5))
def tf_22(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; flat_sel = _flat(sel)
    if sorted(flat_sel) != list(range(1, 10)): return None
    flat_pan = _flat(pan)
    newflat = [None] * 9
    for pos in range(9):
        newflat[flat_sel[pos] - 1] = flat_pan[pos]
    npan = [[newflat[i * 3 + j] for j in range(3)] for i in range(3)]
    return _vpanels([_hpanels(row) for row in npan])
rule("selector_permutation_reorders_panels", "The nine selector cells hold a permutation of the digits 1 through 9 (colour value is the digit); the panel currently at the selector's row-major position p moves to the new row-major position equal to that cell's digit minus one, grey separators redrawn.", gi_22, tf_22, digits=True)


# 23 (digits, small_ok)
def gi_23(rng):
    s = rng.randint(1, 2); cols = colours(rng, 5, exclude=(0, SEP))
    perm = list(range(1, 10)); rng.shuffle(perm)
    marks = {i: perm[i] for i in range(9)}
    return _compose(_sel_digit(rng, s, marks), _pan(rng, s, cols, density=0.5))
def tf_23(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; flat_sel = _flat(sel)
    if sorted(flat_sel) != list(range(1, 10)): return None
    flat_pan = _flat(pan)
    order = sorted(range(9), key=lambda k: flat_sel[k])
    return _hpanels([flat_pan[k] for k in order])
rule("selector_values_sort_panels_ascending", "Every selector cell holds a distinct digit 1 through 9 (colour value is the digit); the output joins all nine panels in a single row, ordered left to right by their selector digit from lowest to highest, grey separators between them.", gi_23, tf_23, demos=(3, 4), digits=True, small_ok=True)


# 24
def gi_24(rng):
    s = _s(rng); cols = colours(rng, 4, exclude=(0, SEP)); mc = rng.choice(cols)
    rows = [rng.randint(0, 3) for _ in range(3)]
    if len(set(rows)) < 2 or rows.count(max(rows)) > 1: rows = [1, 2, 3]
    marks = {}
    for i in range(3):
        for j in rng.sample(range(3), rows[i]):
            marks[i * 3 + j] = mc
    return _compose(_sel(rng, s, marks), _pan(rng, s, cols))
def tf_24(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr
    counts3 = [sum(1 for j in range(3) if sel[i][j]) for i in range(3)]
    best = max(counts3)
    if counts3.count(best) != 1 or best == 0: return None
    i = counts3.index(best)
    return _hpanels([pan[i][j] for j in range(3)])
rule("selector_row_with_most_marks_outputs_panel_row", "Count the coloured cells in each selector row; the row with strictly the most marks (ties never occur) names a panel row, and the output joins that row's three panels left to right, grey separators between them.", gi_24, tf_24)


# 25
def gi_25(rng):
    s = _s(rng); cols = colours(rng, 4, exclude=(0, SEP)); mc = rng.choice(cols)
    colsN = [rng.randint(0, 3) for _ in range(3)]
    if len(set(colsN)) < 2 or colsN.count(max(colsN)) > 1: colsN = [1, 2, 3]
    marks = {}
    for j in range(3):
        for i in rng.sample(range(3), colsN[j]):
            marks[i * 3 + j] = mc
    return _compose(_sel(rng, s, marks), _pan(rng, s, cols))
def tf_25(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr
    counts3 = [sum(1 for i in range(3) if sel[i][j]) for j in range(3)]
    best = max(counts3)
    if counts3.count(best) != 1 or best == 0: return None
    j = counts3.index(best)
    return _vpanels([pan[i][j] for i in range(3)])
rule("selector_col_with_most_marks_outputs_panel_col", "Count the coloured cells in each selector column; the column with strictly the most marks (ties never occur) names a panel column, and the output stacks that column's three panels top to bottom, grey separators between them.", gi_25, tf_25)


# 26
def gi_26(rng):
    s = _s(rng); cols = colours(rng, 4, exclude=(0, SEP)); mc = rng.choice(cols)
    full = rng.randrange(3); marks = {i * 3 + full: mc for i in range(3)}
    for j in range(3):
        if j == full: continue
        for i in rng.sample(range(3), rng.randint(0, 2)):  # never all 3, so column j stays non-full
            marks[i * 3 + j] = mc
    return _compose(_sel(rng, s, marks), _pan(rng, s, cols))
def tf_26(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr
    full = [j for j in range(3) if all(sel[i][j] for i in range(3))]
    if len(full) != 1: return None
    j = full[0]
    return _vpanels([pan[i][j] for i in range(3)])
rule("selector_full_column_marks_select_panel_column", "Exactly one selector column has all three cells coloured; the output stacks that column's three panels top to bottom, grey separators between them.", gi_26, tf_26)


# 27
def gi_27(rng):
    s = _s(rng); cols = colours(rng, 4, exclude=(0, SEP)); mc = rng.choice(cols)
    rows = rng.sample(range(3), rng.randint(1, 2))
    marks = {i * 3 + j: mc for i in rows for j in range(3)}
    return _compose(_sel(rng, s, marks), _pan(rng, s, cols))
def tf_27(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr
    full = [i for i in range(3) if all(sel[i][j] for j in range(3))]
    if not full or len(full) == 3: return None
    return _vpanels([_hpanels([pan[i][j] for j in range(3)]) for i in full])
rule("selector_fully_marked_rows_stacked", "The selector rows that are fully coloured (all three cells) name panel rows to keep; the output stacks only those panel rows, top to bottom in their original order, each row's three panels joined left to right, grey separators throughout.", gi_27, tf_27)


# 28
def gi_28(rng):
    s = _s(rng); cols = colours(rng, 4, exclude=(0, SEP)); mc = rng.choice(cols)
    colsel = rng.sample(range(3), rng.randint(1, 2))
    marks = {i * 3 + j: mc for j in colsel for i in range(3)}
    return _compose(_sel(rng, s, marks), _pan(rng, s, cols))
def tf_28(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr
    full = [j for j in range(3) if all(sel[i][j] for i in range(3))]
    if not full or len(full) == 3: return None
    return _hpanels([_vpanels([pan[i][j] for i in range(3)]) for j in full])
rule("selector_fully_marked_columns_joined", "The selector columns that are fully coloured (all three cells) name panel columns to keep; the output joins only those panel columns, left to right in their original order, each column's three panels stacked top to bottom, grey separators throughout.", gi_28, tf_28)


# 29
def gi_29(rng):
    s = _s(rng); cols = colours(rng, 4, exclude=(0, SEP)); mc = rng.choice(cols)
    k = rng.choice([1, 2, 4, 5, 7, 8])
    idxs = rng.sample(range(9), k)
    return _compose(_sel(rng, s, {i: mc for i in idxs}), _pan(rng, s, cols))
def tf_29(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; k = len(_marked(_flat(sel))); m = k % 3
    if m == 0: return None
    rows = [pan[(i - m) % 3] for i in range(3)]
    return _vpanels([_hpanels(row) for row in rows])
rule("selector_mark_count_shifts_panels_down", "Count the selector's coloured cells (k); the three panel rows are cyclically shifted down by k modulo 3 positions (a row that would fall off the bottom reappears at the top), grey separators redrawn.", gi_29, tf_29)


# 30
def gi_30(rng):
    s = _s(rng); cols = colours(rng, 4, exclude=(0, SEP)); mc = rng.choice(cols)
    k = rng.choice([1, 2, 4, 5, 7, 8])
    idxs = rng.sample(range(9), k)
    return _compose(_sel(rng, s, {i: mc for i in idxs}), _pan(rng, s, cols))
def tf_30(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; k = len(_marked(_flat(sel))); m = k % 3
    if m == 0: return None
    npan = [[pan[i][(j - m) % 3] for j in range(3)] for i in range(3)]
    return _vpanels([_hpanels(row) for row in npan])
rule("selector_mark_count_shifts_panels_right", "Count the selector's coloured cells (k); the three panel columns are cyclically shifted right by k modulo 3 positions (a column that would fall off the right reappears on the left), grey separators redrawn.", gi_30, tf_30)


# 31
def gi_31(rng):
    s = _s(rng); cols = colours(rng, 5, exclude=(0, SEP)); mc = rng.choice(cols)
    idx = rng.randrange(9)
    return _compose(_sel(rng, s, {idx: mc}), _pan(rng, s, cols, density=0.5))
def tf_31(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; m = _marked(_flat(sel))
    if len(m) != 1: return None
    ki = m[0]
    out = [[_dom(pan[i][j]) for j in range(3)] for i in range(3)]
    out[ki // 3][ki % 3] = 0
    return _nonconst(out)
rule("selector_marks_knockout_cell_in_dominant_colour_map", "The output is the 3x3 panel grid downscaled to one cell per panel (that panel's most frequent non-background colour), except the cell at the selector's single coloured position is forced to background.", gi_31, tf_31)


# 32
def gi_32(rng):
    s = _s(rng, 3, 7); cols = colours(rng, 4, exclude=(0, SEP)); mc = rng.choice(cols)
    idx = rng.randrange(9)
    return _compose(_sel(rng, s, {idx: mc}), _pan(rng, s, cols, density=0.5))
def tf_32(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; m = _marked(_flat(sel))
    if len(m) != 1: return None
    ki = m[0]; i0, j0 = divmod(ki, 3)
    d = _dom(pan[i0][j0])
    if d == 0: return None
    s = len(pan[i0][j0])
    hollow = blank(s, s); rect(hollow, 0, 0, s - 1, s - 1, d, fill=False)
    npan = [[pan[i][j] for j in range(3)] for i in range(3)]
    npan[i0][j0] = hollow
    return _vpanels([_hpanels(row) for row in npan])
rule("selector_marked_panel_becomes_hollow_border", "The selector's one coloured cell names a panel by its row-major position; that panel is replaced by a hollow square outline in its own dominant colour (border coloured, interior background), every other panel unchanged, grey separators redrawn.", gi_32, tf_32)


# 33
def gi_33(rng):
    s = _s(rng, 3, 7); cols = colours(rng, 4, exclude=(0, SEP))
    assign = {i: rng.choice(cols) for i in range(9) if rng.random() < 0.6}
    if not assign: assign[rng.randrange(9)] = rng.choice(cols)
    return _compose(_sel(rng, s, assign), _pan(rng, s, cols, density=0.5))
def tf_33(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr
    s = len(pan[0][0])
    if s < 3: return None
    npan = [[[row[:] for row in pan[i][j]] for j in range(3)] for i in range(3)]
    for i in range(3):
        for j in range(3):
            if sel[i][j]:
                for a in range(3):
                    for b in range(3):
                        npan[i][j][a][b] = sel[a][b]
    return _nonconst(_vpanels([_hpanels(row) for row in npan]))
rule("selector_pattern_stamped_into_marked_panels_corner", "The selector's one or more coloured cells name panels; the whole 3x3 selector pattern is copied, cell for cell, into the top-left 3x3 corner of each named panel, every other panel unchanged.", gi_33, tf_33)


# 34
def gi_34(rng):
    s = _s(rng); cols = colours(rng, 4, exclude=(0, SEP)); mc = rng.choice(cols)
    f = rng.randint(0, 9); filled = set(rng.sample(range(9), f))
    marked = set(filled)
    toggle = rng.randrange(9)
    if toggle in marked: marked = marked - {toggle}
    else: marked = marked | {toggle}
    special = {i: (_patt(rng, s, s, cols, 0.5) if i in filled else blank(s, s)) for i in range(9)}
    return _compose(_sel(rng, s, {i: mc for i in marked}), _pan(rng, s, cols, special=special))
def tf_34(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; marked = set(_marked(_flat(sel)))
    filled = {i for i in range(9) if any(v for row in pan[i // 3][i % 3] for v in row)}
    diff = marked ^ filled
    if len(diff) != 1: return None
    ki = next(iter(diff)); i, j = divmod(ki, 3)
    return pan[i][j]
rule("selector_binary_pattern_differs_from_panel_occupancy_at_one_cell_selects_it", "Treat the selector's coloured cells as a yes/no pattern and the panels that are non-empty as a second yes/no pattern over the same nine positions; those two patterns disagree at exactly one position, and the output is the panel at that position.", gi_34, tf_34)


# 35
def gi_35(rng):
    s = _s(rng); cols = colours(rng, 5, exclude=(0, SEP)); maj, other = cols[0], cols[1]
    npos = rng.sample(range(9), rng.randint(2, 4))
    marks = {i: (other if i in npos else maj) for i in range(9)}
    target = rng.randrange(9)
    special = {target: _patt(rng, s, s, [maj], 0.6)}
    others_cols = [c for c in cols if c != maj]
    for i in range(9):
        if i != target:
            special[i] = _patt(rng, s, s, [rng.choice(others_cols)], 0.6)
    return _compose(_sel(rng, s, marks), _pan(rng, s, cols, special=special))
def tf_35(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; flat = _flat(sel); vals = [v for v in flat if v]
    if not vals: return None
    cnt = {}
    for v in vals: cnt[v] = cnt.get(v, 0) + 1
    best = max(cnt.values())
    maj = [v for v in vals if cnt[v] == best][0]
    hits = [k for k in range(9) if _dom(pan[k // 3][k % 3]) == maj]
    if len(hits) != 1: return None
    i, j = divmod(hits[0], 3)
    return pan[i][j]
rule("selector_mark_colour_frequency_selects_panel", "Among the selector's coloured cells, find the colour used most often (it is the strict majority); the output is the one panel whose own dominant colour equals that majority colour.", gi_35, tf_35)


# 36
def gi_36(rng):
    s = _s(rng); cols = colours(rng, 4, exclude=(0, SEP)); mc = rng.choice(cols)
    main = rng.random() < 0.5
    idxs = (0, 4, 8) if main else (2, 4, 6)
    return _compose(_sel(rng, s, {i: mc for i in idxs}), _pan(rng, s, cols))
def tf_36(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr
    main = sel[0][0] != 0
    anti = sel[0][2] != 0
    if main == anti: return None
    idxs = (0, 4, 8) if main else (2, 4, 6)
    return _hpanels([pan[k // 3][k % 3] for k in idxs])
rule("selector_diagonal_choice_selects_diagonal_panels", "The selector marks either the main diagonal (top-left to bottom-right) or the anti-diagonal (top-right to bottom-left) of the 3x3 grid; the output joins that diagonal's three panels left to right in that diagonal's order, grey separators between them.", gi_36, tf_36)


# 37
def gi_37(rng):
    s = _s(rng, 2, 6); cols = colours(rng, 4, exclude=(0, SEP)); mc = rng.choice(cols)
    corners = rng.random() < 0.5
    idxs = (0, 2, 8, 6) if corners else (1, 5, 7, 3)
    return _compose(_sel(rng, s, {i: mc for i in idxs}), _pan(rng, s, cols))
def tf_37(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; flat = set(_marked(_flat(sel)))
    if flat == {0, 2, 6, 8}:
        order = (0, 2, 8, 6)
    elif flat == {1, 3, 5, 7}:
        order = (1, 5, 7, 3)
    else:
        return None
    return _hpanels([pan[k // 3][k % 3] for k in order])
rule("selector_border_marks_select_corner_or_edge_subset", "The selector marks either its four corner cells or its four edge-midpoint cells; the output joins the four named panels in clockwise order starting from the top (corners: top-left, top-right, bottom-right, bottom-left; edges: top, right, bottom, left), grey separators between them.", gi_37, tf_37)


# 38
def gi_38(rng):
    s = _s(rng); cols = colours(rng, 5, exclude=(0, SEP)); mc = rng.choice(cols)
    extra = set(rng.sample([i for i in range(9) if i != 4], rng.randint(0, 3)))
    return _compose(_sel(rng, s, {4: mc, **{i: mc for i in extra}}), _pan(rng, s, cols))
def tf_38(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr
    if not sel[1][1]: return None
    centre = pan[1][1]
    npan = [[centre for j in range(3)] for i in range(3)]
    out = _vpanels([_hpanels(row) for row in npan])
    return out if any(pan[i][j] != centre for i in range(3) for j in range(3) if (i, j) != (1, 1)) else None
rule("selector_center_mark_broadcasts_panel", "The selector's centre cell is always coloured; the output replaces every one of the nine panels with a copy of the centre panel, keeping the same 3x3 layout and grey separators.", gi_38, tf_38)


# 39
def gi_39(rng):
    s = _s(rng); cols = colours(rng, 4, exclude=(0, SEP))
    a, b = rng.sample(range(9), 2); ca, cb = rng.sample(cols, 2)
    return _compose(_sel(rng, s, {a: ca, b: cb}), _pan(rng, s, cols))
def tf_39(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; m = _marked(_flat(sel))
    if len(m) != 2: return None
    a, b = sorted(m)
    pa, pb = pan[a // 3][a % 3], pan[b // 3][b % 3]
    return _hgap(pa, pb, gap=1)
rule("selector_marks_select_panel_pair_joined_with_blank_gap", "Exactly two selector cells are coloured, naming two panels by their row-major position; the output joins the lower-indexed panel then the higher-indexed panel side by side with a single background column between them (no grey separator).", gi_39, tf_39)


# 40
def gi_40(rng):
    s = _s(rng); cols = colours(rng, 6, exclude=(0, SEP)); mc = cols[:]
    k = rng.randint(1, 6); chosen = rng.sample(cols, k)
    marks = {i: rng.choice(chosen) for i in range(9)}
    if len(set(marks.values())) != k: return None
    target = k - 1
    special = {target: _patt(rng, s, s, [cols[0]], 0.5)}
    return _compose(_sel(rng, s, marks), _pan(rng, s, cols, density=0.5))
def tf_40(g):
    pr = _parse(g)
    if pr is None: return None
    sel, pan = pr; flat = _flat(sel)
    k = len({v for v in flat if v})
    if k < 1 or k > 9: return None
    i, j = divmod(k - 1, 3)
    return pan[i][j]
rule("selector_distinct_colour_count_selects_panel_rank", "Count the number of distinct colours used among the selector's nine cells (k); the output is the k-th panel counting left to right, top to bottom through the 3x3 panel grid (k=1 is the top-left panel), unchanged.", gi_40, tf_40)
