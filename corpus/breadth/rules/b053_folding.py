# b053_folding.py -- PAPER FOLDING AND UNFOLDING. Fold along a grey (colour 5) line and overlay the
# moved flap onto the fixed sheet; every rule states its fold direction and its overlap rule. Grey (5)
# marks fold lines and markers throughout, matching the harness's colour-permutation exemption for 5.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

GREY = 5


# ---------- shared fold/overlay machinery ----------
def _combine(a, b, mode, third=None):
    if a and b:
        if mode == "upper": return a
        if mode == "lower": return b
        if mode == "third": return third
        if mode == "cancel": return 0
        if mode == "match": return a if a == b else third
    return a or b


def _dist_v(half, side):
    return flip_h(half) if side == "left" else half


def _undist_v(dg, side):
    return flip_h(dg) if side == "left" else dg


def _dist_h(half, side):
    return flip_v(half) if side == "top" else half


def _undist_h(dg, side):
    return flip_v(dg) if side == "top" else dg


def fold_v(g, line, moving_side, mode, third=None, crop_to_fold=False):
    """Fold the grid along vertical column `line` (removed). moving_side 'left' or 'right' names the
    flap that moves; it is mirrored across the line and overlaid on the other (fixed) flap. mode is the
    overlap rule where both flaps are coloured."""
    h, w = dims(g)
    left = [row[:line] for row in g]
    right = [row[line + 1:] for row in g]
    if moving_side == "left":
        moving, fixed, fixed_side = left, right, "right"
    else:
        moving, fixed, fixed_side = right, left, "left"
    mdist = _dist_v(moving, moving_side)
    fdist = _dist_v(fixed, fixed_side)
    mw = len(mdist[0]); fw = len(fdist[0])
    n = min(mw, fw) if crop_to_fold else fw
    out_dist = [row[:n] for row in fdist]
    for r in range(h):
        for d in range(min(mw, n)):
            out_dist[r][d] = _combine(mdist[r][d], out_dist[r][d], mode, third)
    return _undist_v(out_dist, fixed_side) if not crop_to_fold else [row[:] for row in out_dist] if fixed_side == "right" else _undist_v(out_dist, "left")


def fold_h(g, line, moving_side, mode, third=None, crop_to_fold=False):
    h, w = dims(g)
    top = g[:line]
    bottom = g[line + 1:]
    if moving_side == "top":
        moving, fixed, fixed_side = top, bottom, "bottom"
    else:
        moving, fixed, fixed_side = bottom, top, "top"
    mdist = _dist_h(moving, moving_side)
    fdist = _dist_h(fixed, fixed_side)
    mh = len(mdist); fh = len(fdist)
    n = min(mh, fh) if crop_to_fold else fh
    out_dist = [row[:] for row in fdist[:n]]
    for d in range(min(mh, n)):
        for c in range(w):
            out_dist[d][c] = _combine(mdist[d][c], out_dist[d][c], mode, third)
    return _undist_h(out_dist, fixed_side)


def _rand_grid(rng, lo, hi, density=0.35):
    h, w = size(rng, lo, hi)
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < density:
                g[r][c] = rng.choice([x for x in COLOURS if x != GREY])
    return g


def _centered_v(rng, lo, hi):
    """Odd width, grey column exactly centred."""
    h = rng.randint(lo, hi)
    half = rng.randint(lo // 2 or 2, hi // 2)
    g = _rand_grid(rng, 1, 1, 0)  # placeholder, replaced below
    w = 2 * half + 1
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if c == half:
                g[r][c] = GREY
            elif rng.random() < 0.4:
                g[r][c] = rng.choice([x for x in COLOURS if x != GREY])
    return g, half


def _centered_h(rng, lo, hi):
    w = rng.randint(lo, hi)
    half = rng.randint(lo // 2 or 2, hi // 2)
    h = 2 * half + 1
    g = blank(h, w)
    for c in range(w):
        for r in range(h):
            if r == half:
                g[r][c] = GREY
            elif rng.random() < 0.4:
                g[r][c] = rng.choice([x for x in COLOURS if x != GREY])
    return g, half


# ====================== 1-4: single fold, upper/lower wins ======================
def gi_f1(rng):
    g, half = _centered_v(rng, 11, 29)
    return g if half >= 2 else None
def tf_f1(g):
    line = g[0].index(GREY)
    return fold_v(g, line, "left", "upper")
rule("fold_left_onto_right_upper_wins",
     "The grid is folded along the vertical grey line: the left half is mirrored onto the right half, and where both layers are coloured the moved (left) layer's colour wins.",
     gi_f1, tf_f1)


def gi_f2(rng):
    g, half = _centered_v(rng, 11, 29)
    return g if half >= 2 else None
def tf_f2(g):
    line = g[0].index(GREY)
    return fold_v(g, line, "right", "lower")
rule("fold_right_onto_left_lower_wins",
     "The grid is folded along the vertical grey line: the right half is mirrored onto the left half, and where both layers are coloured the original (left, now-bottom) layer's colour wins.",
     gi_f2, tf_f2)


def gi_f3(rng):
    g, half = _centered_h(rng, 11, 29)
    return g if half >= 2 else None
def tf_f3(g):
    line = [row[0] for row in g].index(GREY)
    return fold_h(g, line, "top", "upper")
rule("fold_top_onto_bottom_upper_wins",
     "The grid is folded along the horizontal grey line: the top half is mirrored down onto the bottom half, and where both layers are coloured the moved (top) layer's colour wins.",
     gi_f3, tf_f3)


def gi_f4(rng):
    g, half = _centered_h(rng, 11, 29)
    return g if half >= 2 else None
def tf_f4(g):
    line = [row[0] for row in g].index(GREY)
    return fold_h(g, line, "bottom", "lower")
rule("fold_bottom_onto_top_lower_wins",
     "The grid is folded along the horizontal grey line: the bottom half is mirrored up onto the top half, and where both layers are coloured the original (top) layer's colour wins.",
     gi_f4, tf_f4)


# ====================== 5-8: overlap colour / cancel ======================
def gi_f5(rng):
    g, half = _centered_v(rng, 11, 29)
    return g if half >= 2 else None
def tf_f5(g):
    line = g[0].index(GREY)
    return fold_v(g, line, "left", "third", third=GREY)
rule("fold_left_onto_right_overlap_third_colour",
     "The grid is folded along the vertical grey line, left mirrored onto right; any cell coloured in both layers becomes grey, and cells coloured in only one layer keep that colour.",
     gi_f5, tf_f5)


def gi_f6(rng):
    g, half = _centered_h(rng, 11, 29)
    return g if half >= 2 else None
def tf_f6(g):
    line = [row[0] for row in g].index(GREY)
    return fold_h(g, line, "top", "third", third=GREY)
rule("fold_top_onto_bottom_overlap_third_colour",
     "The grid is folded along the horizontal grey line, top mirrored onto bottom; any cell coloured in both layers becomes grey, and cells coloured in only one layer keep that colour.",
     gi_f6, tf_f6)


def gi_f7(rng):
    g, half = _centered_v(rng, 11, 29)
    return g if half >= 2 else None
def tf_f7(g):
    line = g[0].index(GREY)
    return fold_v(g, line, "right", "cancel")
rule("fold_right_onto_left_overlap_cancels",
     "The grid is folded along the vertical grey line, right mirrored onto left; a cell coloured in both layers cancels to background, and a cell coloured in only one layer keeps that colour.",
     gi_f7, tf_f7)


def gi_f8(rng):
    g, half = _centered_h(rng, 11, 29)
    return g if half >= 2 else None
def tf_f8(g):
    line = [row[0] for row in g].index(GREY)
    return fold_h(g, line, "bottom", "cancel")
rule("fold_bottom_onto_top_overlap_cancels",
     "The grid is folded along the horizontal grey line, bottom mirrored onto top; a cell coloured in both layers cancels to background, and a cell coloured in only one layer keeps that colour.",
     gi_f8, tf_f8)


# ====================== 9-12: fold line off-centre, given by a border marker ======================
def _marker_v(rng, lo, hi):
    h, w = size(rng, lo, hi)
    line = rng.randint(2, w - 3)
    g = blank(h, w)
    g[0][0] = GREY  # corner tag: a grey line exists
    for r in range(h):
        g[r][line] = GREY
        for c in range(w):
            if c != line and rng.random() < 0.4:
                g[r][c] = rng.choice([x for x in COLOURS if x != GREY])
    g[0][w - 1] = line  # marker cell on the border row encodes the fold column (digits matter)
    return g
def gi_f9(rng):
    return _marker_v(rng, 12, 29)
def tf_f9(g):
    line = g[0][len(g[0]) - 1]
    gg = copy(g); gg[0][len(g[0]) - 1] = gg[0][len(g[0]) - 1] if False else gg[0][len(g[0]) - 1]
    gg[0][-1] = 0
    left_w, right_w = line, len(g[0]) - line - 1
    moving_side = "left" if left_w <= right_w else "right"
    return fold_v(gg, line, moving_side, "upper")
rule("fold_vertical_at_marker_column_upper_wins",
     "The fold column equals the number written in the top-right marker cell (then cleared); the shorter side is mirrored onto the longer side and the moved layer's colour wins on overlap.",
     gi_f9, tf_f9, digits=True)


def _marker_h(rng, lo, hi):
    h, w = size(rng, lo, hi)
    line = rng.randint(2, h - 3)
    g = blank(h, w)
    for c in range(w):
        g[line][c] = GREY
        for r in range(h):
            if r != line and rng.random() < 0.4:
                g[r][c] = rng.choice([x for x in COLOURS if x != GREY])
    g[0][0] = line
    return g
def gi_f10(rng):
    return _marker_h(rng, 12, 29)
def tf_f10(g):
    line = g[0][0]
    gg = copy(g); gg[0][0] = 0
    top_h, bot_h = line, len(g) - line - 1
    moving_side = "top" if top_h <= bot_h else "bottom"
    return fold_h(gg, line, moving_side, "lower")
rule("fold_horizontal_at_marker_row_lower_wins",
     "The fold row equals the number written in the top-left marker cell (then cleared); the shorter side is mirrored onto the longer side and the original (longer) layer's colour wins on overlap.",
     gi_f10, tf_f10, digits=True)


def gi_f11(rng):
    return _marker_v(rng, 12, 29)
def tf_f11(g):
    line = g[0][-1]
    gg = copy(g); gg[0][-1] = 0
    left_w, right_w = line, len(g[0]) - line - 1
    moving_side = "left" if left_w <= right_w else "right"
    return fold_v(gg, line, moving_side, "third", third=GREY)
rule("fold_vertical_at_marker_column_overlap_third_colour",
     "The fold column equals the number written in the top-right marker cell (then cleared); the shorter side folds onto the longer side and a cell coloured in both layers becomes grey.",
     gi_f11, tf_f11, digits=True)


def gi_f12(rng):
    return _marker_h(rng, 12, 29)
def tf_f12(g):
    line = g[0][0]
    gg = copy(g); gg[0][0] = 0
    top_h, bot_h = line, len(g) - line - 1
    moving_side = "top" if top_h <= bot_h else "bottom"
    return fold_h(gg, line, moving_side, "cancel")
rule("fold_horizontal_at_marker_row_overlap_cancels",
     "The fold row equals the number written in the top-left marker cell (then cleared); the shorter side folds onto the longer side and a cell coloured in both layers cancels to background.",
     gi_f12, tf_f12, digits=True)


# ====================== 13-16: fold twice, to a quarter ======================
def _full_grid(rng, lo, hi):
    h2 = rng.randint(lo // 2, hi // 2); w2 = rng.randint(lo // 2, hi // 2)
    h, w = 2 * h2 + 1, 2 * w2 + 1
    g = blank(h, w)
    for r in range(h):
        g[r][w2] = GREY
    for c in range(w):
        g[h2][c] = GREY
    for r in range(h):
        for c in range(w):
            if g[r][c] != GREY and rng.random() < 0.35:
                g[r][c] = rng.choice([x for x in COLOURS if x != GREY])
    return g, h2, w2
def gi_f13(rng):
    g, h2, w2 = _full_grid(rng, 11, 23)
    return g if h2 >= 2 and w2 >= 2 else None
def tf_f13(g):
    h2 = [row[0] for row in g].index(GREY); w2 = g[0].index(GREY)
    step1 = fold_v(g, w2, "left", "upper")
    gg_line = [row[0] for row in step1].index(GREY)
    return fold_h(step1, gg_line, "top", "upper")
rule("fold_vertical_then_horizontal_quarter_upper_wins",
     "The sheet is folded along the vertical grey line (left onto right, moved layer wins) and then along the horizontal grey line (top onto bottom, moved layer wins), ending at quarter size.",
     gi_f13, tf_f13)


def gi_f14(rng):
    g, h2, w2 = _full_grid(rng, 11, 23)
    return g if h2 >= 2 and w2 >= 2 else None
def tf_f14(g):
    w2 = g[0].index(GREY)
    step1 = fold_v(g, w2, "left", "third", third=GREY)
    gg_line = [row[0] for row in step1].index(GREY)
    return fold_h(step1, gg_line, "top", "third", third=GREY)
rule("fold_vertical_then_horizontal_quarter_overlap_third_colour",
     "The sheet is folded vertically then horizontally to quarter size; at each fold a cell coloured in both overlapping layers becomes grey.",
     gi_f14, tf_f14)


def gi_f15(rng):
    g, h2, w2 = _full_grid(rng, 11, 23)
    return g if h2 >= 2 and w2 >= 2 else None
def tf_f15(g):
    h2 = [row[0] for row in g].index(GREY)
    step1 = fold_h(g, h2, "top", "lower")
    gg_line = step1[0].index(GREY)
    return fold_v(step1, gg_line, "left", "lower")
rule("fold_horizontal_then_vertical_quarter_lower_wins",
     "The sheet is folded along the horizontal grey line (top onto bottom, original layer wins) then along the vertical grey line (left onto right, original layer wins), ending at quarter size.",
     gi_f15, tf_f15)


def gi_f16(rng):
    g, h2, w2 = _full_grid(rng, 11, 23)
    return g if h2 >= 2 and w2 >= 2 else None
def tf_f16(g):
    w2 = g[0].index(GREY)
    h2 = [row[0] for row in g].index(GREY)
    step1 = fold_v(g, w2, "left", "cancel")
    return fold_h(step1, h2, "top", "cancel")
rule("fold_vertical_then_horizontal_quarter_overlap_cancels",
     "The sheet is folded vertically then horizontally to quarter size; at each fold a cell coloured in both overlapping layers cancels to background.",
     gi_f16, tf_f16)


# ====================== 17-20: diagonal fold ======================
def _diag_grid(rng, lo, hi):
    n = rng.randint(lo, hi)
    g = blank(n, n)
    for r in range(n):
        for c in range(n):
            if rng.random() < 0.3:
                g[r][c] = rng.choice([x for x in COLOURS if x != GREY])
    return g
def tf_diag_main(g, mode, third=None):
    n = len(g)
    out = [row[:] for row in g]
    for r in range(n):
        for c in range(r + 1, n):
            a = g[r][c]; b = out[c][r]
            out[c][r] = _combine(a, b, mode, third)
            out[r][c] = 0
    return out
def gi_f17(rng):
    return _diag_grid(rng, 11, 29)
def tf_f17(g):
    return tf_diag_main(g, "upper")
rule("fold_main_diagonal_upper_wins",
     "The square grid is folded along its main (top-left to bottom-right) diagonal: the upper-right triangle is reflected onto the lower-left triangle, and the moved cell's colour wins on overlap.",
     gi_f17, tf_f17)


def tf_diag_anti(g, mode, third=None):
    n = len(g)
    out = [row[:] for row in g]
    for r in range(n):
        for c in range(n - r, n):
            rr, cc = n - 1 - c, n - 1 - r
            a = g[r][c]; b = out[rr][cc]
            out[rr][cc] = _combine(a, b, mode, third)
            out[r][c] = 0
    return out
def gi_f18(rng):
    return _diag_grid(rng, 11, 29)
def tf_f18(g):
    return tf_diag_anti(g, "upper")
rule("fold_anti_diagonal_upper_wins",
     "The square grid is folded along its anti-diagonal (top-right to bottom-left): the upper-left triangle is reflected onto the lower-right triangle, and the moved cell's colour wins on overlap.",
     gi_f18, tf_f18)


def gi_f19(rng):
    return _diag_grid(rng, 11, 29)
def tf_f19(g):
    return tf_diag_main(g, "third", third=GREY)
rule("fold_main_diagonal_overlap_third_colour",
     "The square grid is folded along its main diagonal; a cell coloured in both the moved and the fixed triangle becomes grey, and a cell coloured in only one triangle keeps that colour.",
     gi_f19, tf_f19)


def gi_f20(rng):
    return _diag_grid(rng, 11, 29)
def tf_f20(g):
    return tf_diag_anti(g, "cancel")
rule("fold_anti_diagonal_overlap_cancels",
     "The square grid is folded along its anti-diagonal; a cell coloured in both the moved and the fixed triangle cancels to background, and a cell coloured in only one triangle keeps that colour.",
     gi_f20, tf_f20)


# ====================== 21-24: unfolding ======================
def gi_f21(rng):
    h, w = size(rng, 6, 15)
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.35:
                g[r][c] = rng.choice([x for x in COLOURS if x != GREY])
    return g if any(v for row in g for v in row) else None
def tf_f21(g):
    top = [row + row[::-1] for row in g]
    return top + [row[:] for row in top[::-1]]
# unfold_quarter_to_full_sheet_both_axes dropped 2026-10-12 (review 2: behavioural duplicate of tile_2x2_mirrored)
def gi_f22(rng):
    h, w = size(rng, 6, 20)
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.35:
                g[r][c] = rng.choice([x for x in COLOURS if x != GREY])
    return g if any(v for row in g for v in row) else None
def tf_f22(g):
    return [row + row[::-1] for row in g]
rule("unfold_half_to_full_vertical_mirror",
     "The grid is the left half of a sheet folded along a vertical crease; unfolding appends its mirror image on the right, doubling the width.",
     gi_f22, tf_f22)


def gi_f23(rng):
    h, w = size(rng, 6, 20)
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.35:
                g[r][c] = rng.choice([x for x in COLOURS if x != GREY])
    return g if any(v for row in g for v in row) else None
def tf_f23(g):
    return g + g[::-1]
rule("unfold_half_to_full_horizontal_mirror",
     "The grid is the top half of a sheet folded along a horizontal crease; unfolding appends its mirror image below, doubling the height.",
     gi_f23, tf_f23)


def gi_f24(rng):
    w0 = rng.randint(3, 9); k = rng.randint(2, 4)
    h = rng.randint(5, 20)
    g = blank(h, w0)
    for r in range(h):
        for c in range(w0):
            if rng.random() < 0.4:
                g[r][c] = rng.choice([x for x in COLOURS if x != GREY])
    g[0][0] = k
    return g if any(v for row in g for v in row[1:]) else None
def tf_f24(g):
    k = g[0][0]
    gg = copy(g); gg[0][0] = 0
    panels = []
    for i in range(k):
        panels.append(flip_h(gg) if i % 2 else [row[:] for row in gg])
    out = [[] for _ in range(len(gg))]
    for p in panels:
        for r in range(len(gg)):
            out[r] += p[r]
    return out
rule("unfold_strip_to_full_accordion",
     "The grid is one panel of an accordion-folded strip; the top-left cell (then cleared) gives the panel count K, and unfolding lays out K copies left to right, alternating a mirrored flip for every second panel.",
     gi_f24, tf_f24, digits=True)


# ====================== 25-28: the classic punch-hole puzzle ======================
def _punch_base(rng, lo, hi):
    h, w = size(rng, lo, hi)
    g = blank(h, w)
    holes = rng.randint(1, max(1, (h * w) // 10))
    pts = set()
    for _ in range(holes):
        pts.add((rng.randrange(h), rng.randrange(w)))
    for r, c in pts:
        g[r][c] = rng.choice([x for x in COLOURS if x != GREY])
    return g if pts else None
def gi_f25(rng):
    return _punch_base(rng, 8, 20)
def tf_f25(g):
    return [row + row[::-1] for row in g]
# punch_holes_unfold_vertical dropped 2026-10-12 (review 2: behavioural duplicate of unfold_half_to_full_vertical_mirror)
def gi_f26(rng):
    return _punch_base(rng, 8, 20)
def tf_f26(g):
    return g + g[::-1]
# punch_holes_unfold_horizontal dropped 2026-10-12 (review 2: behavioural duplicate of unfold_half_to_full_horizontal_mirror)
def gi_f27(rng):
    return _punch_base(rng, 8, 16)
def tf_f27(g):
    top = [row + row[::-1] for row in g]
    return top + [row[:] for row in top[::-1]]
# punch_holes_unfold_quarter_both_axes dropped 2026-10-12 (review 2: behavioural duplicate of tile_2x2_mirrored)
def gi_f28(rng):
    n = rng.randint(8, 20)
    g = blank(n, n)
    holes = rng.randint(1, max(1, n * n // 10))
    pts = set()
    for _ in range(holes):
        r = rng.randrange(n); c = rng.randrange(n - r)
        pts.add((r, c))
    for r, c in pts:
        g[r][c] = rng.choice([x for x in COLOURS if x != GREY])
    return g if pts else None
def tf_f28(g):
    n = len(g)
    out = [row[:] for row in g]
    for r in range(n):
        for c in range(n):
            if g[r][c]:
                out[c][r] = g[r][c]
    return out
rule("punch_holes_unfold_diagonal",
     "The grid is the triangle of a sheet folded along its main diagonal, shown with its punch holes; unfolding reflects every hole across the diagonal so each one appears on both sides.",
     gi_f28, tf_f28)


# ====================== 29-31: accordion fold ======================
def gi_f29(rng):
    k = rng.randint(2, 4)
    w0 = rng.randint(2, min(9, 30 // k)); h = rng.randint(5, 20)
    w = w0 * k
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.3:
                g[r][c] = rng.choice([x for x in COLOURS if x != GREY])
    for r in range(h):
        g[r][0] = k if r == 0 else g[r][0]
    g[0][0] = k
    return g, w0
def gi_f29b(rng):
    r = gi_f29(rng)
    return r[0] if r else None
def tf_f29(g):
    k = g[0][0]
    gg = copy(g); gg[0][0] = 0
    w = len(gg[0]); w0 = w // k
    panels = [[row[c0:c0 + w0] for row in gg] for c0 in range(0, w, w0)]
    out = [row[:] for row in panels[0]]
    for i in range(1, len(panels)):
        p = flip_h(panels[i]) if i % 2 else panels[i]
        for r in range(len(out)):
            for c in range(w0):
                out[r][c] = _combine(p[r][c], out[r][c], "upper")
    return out
rule("accordion_fold_strip_overlap_upper_wins",
     "The strip has width a multiple of panel width K (K given, then cleared, by the top-left cell); it is accordion-folded panel by panel onto the first panel, alternating a mirror flip, and the latest-folded layer's colour wins on overlap.",
     gi_f29b, tf_f29, digits=True)


def gi_f30(rng):
    r = gi_f29(rng)
    return r[0] if r else None
def tf_f30(g):
    k = g[0][0]
    gg = copy(g); gg[0][0] = 0
    w = len(gg[0]); w0 = w // k
    panels = [[row[c0:c0 + w0] for row in gg] for c0 in range(0, w, w0)]
    out = [row[:] for row in panels[0]]
    for i in range(1, len(panels)):
        p = flip_h(panels[i]) if i % 2 else panels[i]
        for r in range(len(out)):
            for c in range(w0):
                out[r][c] = _combine(p[r][c], out[r][c], "third", third=GREY)
    return out
rule("accordion_fold_strip_overlap_third_colour",
     "The strip has width a multiple of panel width K (K given, then cleared, by the top-left cell); it is accordion-folded panel by panel onto the first panel, alternating a mirror flip, and any cell covered by two or more coloured layers becomes grey.",
     gi_f30, tf_f30, digits=True)


def gi_f31(rng):
    r = gi_f29(rng)
    return r[0] if r else None
def tf_f31(g):
    k = g[0][0]
    gg = copy(g); gg[0][0] = 0
    h = len(gg); w = len(gg[0]); w0 = w // k
    panels = [[row[c0:c0 + w0] for row in gg] for c0 in range(0, w, w0)]
    stack = [[0] * w0 for _ in range(h)]
    for i, p in enumerate(panels):
        pp = flip_h(p) if i % 2 else p
        for r in range(h):
            for c in range(w0):
                if pp[r][c]:
                    stack[r][c] += 1
    best = max((v for row in stack for v in row), default=0)
    if best == 0 or best >= k:
        return None
    col = next((v for row in gg for v in row if v), 1)
    return [[col] * best + [0] * (k - best)]
rule("accordion_fold_count_layers_to_bar",
     "The strip is accordion-folded panel by panel onto the first panel; find the cell covered by the most coloured layers and output a single row of width K (the panel count) with that many leading cells coloured and the rest background.",
     gi_f31, tf_f31, digits=True, small_ok=True)


# ====================== 32-33: fold then crop to the folded size ======================
def gi_f32(rng):
    g, half = _centered_v(rng, 11, 29)
    return g if half >= 2 else None
def tf_f32(g):
    line = g[0].index(GREY)
    return fold_v(g, line, "left", "upper", crop_to_fold=True)
rule("fold_vertical_crop_to_folded_size",
     "The grid is folded along the vertical grey line, left mirrored onto right with the moved layer winning on overlap, then the output is cropped to exactly the width of the folded (left) flap.",
     gi_f32, tf_f32)


def gi_f33(rng):
    g, half = _centered_h(rng, 11, 29)
    return g if half >= 2 else None
def tf_f33(g):
    line = [row[0] for row in g].index(GREY)
    return fold_h(g, line, "top", "lower", crop_to_fold=True)
rule("fold_horizontal_crop_to_folded_size",
     "The grid is folded along the horizontal grey line, top mirrored onto bottom with the original (bottom) layer winning on overlap, then the output is cropped to exactly the height of the folded (top) flap.",
     gi_f33, tf_f33)


# ====================== 34-35: fold a corner triangle flap ======================
def _corner_grid(rng, lo, hi):
    n = rng.randint(lo, hi)
    g = blank(n, n)
    for r in range(n):
        for c in range(n):
            if rng.random() < 0.3:
                g[r][c] = rng.choice([x for x in COLOURS if x != GREY])
    k = rng.randint(2, n - 2)
    return g, k
def gi_f34(rng):
    r = _corner_grid(rng, 12, 29)
    return r[0] if r else None
def tf_f34(g):
    n = len(g)
    k = max(2, n // 3)
    out = [row[:] for row in g]
    for r in range(k):
        for c in range(k - r):
            if r + c <= k - 1 and (r, c) != (0, 0):
                rr, cc = c, r
                a = g[r][c]; b = out[rr][cc]
                out[rr][cc] = _combine(a, b, "upper")
                out[r][c] = 0
    return out
rule("fold_top_left_corner_triangle_upper_wins",
     "The triangular flap in the top-left corner, of fixed size one third of the grid side, is folded across its own diagonal onto the cells below it; the moved cell's colour wins on overlap.",
     gi_f34, tf_f34)


def gi_f35(rng):
    r = _corner_grid(rng, 12, 29)
    return r[0] if r else None
def tf_f35(g):
    n = len(g)
    k = max(2, n // 3)
    out = [row[:] for row in g]
    for r in range(k):
        for c in range(n - k, n):
            cc = c - (n - k)
            if cc < k - r:
                rr, ccol = cc, n - 1 - r
                a = g[r][c]; b = out[rr][ccol]
                out[rr][ccol] = _combine(a, b, "third", third=GREY)
                out[r][c] = 0
    return out
rule("fold_top_right_corner_triangle_overlap_third_colour",
     "The triangular flap in the top-right corner, of fixed size one third of the grid side, is folded across its own diagonal onto the cells to its left; a cell coloured in both layers becomes grey.",
     gi_f35, tf_f35)


# ====================== 36-37: fold, count overlaps into a bar ======================
def gi_f36(rng):
    g, half = _centered_v(rng, 11, 29)
    return g if half >= 3 else None
def tf_f36(g):
    line = g[0].index(GREY)
    h = len(g)
    left = [row[:line] for row in g]; right = [row[line + 1:] for row in g]
    ld = _dist_v(left, "left"); rd = _dist_v(right, "right")
    n = min(len(ld[0]), len(rd[0]))
    cnt = sum(1 for r in range(h) if any(ld[r][d] and rd[r][d] for d in range(n)))
    if cnt == 0 or cnt >= h: return None
    col = next((v for row in g for v in row if v and v != GREY), 1)
    return [[col] * cnt + [0] * (h - cnt)]
rule("fold_vertical_count_overlap_cells_to_row",
     "The grid is folded along the vertical grey line, left onto right; count the rows that contain at least one cell coloured in both layers, and output a single row of width H (the grid's height) with that many leading cells coloured and the rest background.",
     gi_f36, tf_f36, small_ok=True)


def gi_f37(rng):
    g, half = _centered_h(rng, 11, 29)
    return g if half >= 3 else None
def tf_f37(g):
    line = [row[0] for row in g].index(GREY)
    w = len(g[0])
    top = g[:line]; bottom = g[line + 1:]
    td = _dist_h(top, "top"); bd = _dist_h(bottom, "bottom")
    n = min(len(td), len(bd))
    cnt = sum(1 for c in range(w) if any(td[d][c] and bd[d][c] for d in range(n)))
    if cnt == 0 or cnt >= w: return None
    col = next((v for row in g for v in row if v and v != GREY), 1)
    return [[col]] * cnt + [[0]] * (w - cnt)
rule("fold_horizontal_count_overlap_cells_to_column",
     "The grid is folded along the horizontal grey line, top onto bottom; count the columns that contain at least one cell coloured in both layers, and output a single column of height W (the grid's width) with that many leading cells coloured and the rest background.",
     gi_f37, tf_f37, small_ok=True)


# ====================== 38-39: fold, mark mismatches rather than overwrite ======================
def gi_f38(rng):
    g, half = _centered_v(rng, 11, 29)
    return g if half >= 2 else None
def tf_f38(g):
    line = g[0].index(GREY)
    return fold_v(g, line, "left", "match", third=GREY)
rule("fold_vertical_mark_mismatches",
     "The grid is folded along the vertical grey line, left onto right; a cell coloured the same way in both layers keeps that colour, a cell coloured in only one layer keeps that colour, and a cell coloured differently in each layer turns grey.",
     gi_f38, tf_f38)


def gi_f39(rng):
    g, half = _centered_h(rng, 11, 29)
    return g if half >= 2 else None
def tf_f39(g):
    line = [row[0] for row in g].index(GREY)
    return fold_h(g, line, "top", "match", third=GREY)
rule("fold_horizontal_mark_mismatches",
     "The grid is folded along the horizontal grey line, top onto bottom; a cell coloured the same way in both layers keeps that colour, a cell coloured in only one layer keeps that colour, and a cell coloured differently in each layer turns grey.",
     gi_f39, tf_f39)


# ====================== 40: diagonal fold then crop to the folded triangle's bounding box ======================
def gi_f40(rng):
    return _diag_grid(rng, 12, 29)
def tf_f40(g):
    n = len(g)
    folded = tf_diag_main(g, "upper")
    rows = [r for r in range(n) if any(folded[r])]
    cols = [c for c in range(n) if any(folded[r][c] for r in range(n))]
    if not rows or not cols:
        return None
    return [row[min(cols):max(cols) + 1] for row in folded[min(rows):max(rows) + 1]]
rule("fold_diagonal_crop_to_triangle_bbox",
     "The square grid is folded along its main diagonal (upper-right triangle mirrored onto lower-left, moved layer wins on overlap), then cropped to the bounding box of the remaining coloured cells.",
     gi_f40, tf_f40)
