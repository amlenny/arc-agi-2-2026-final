# b064_weaving.py -- WEAVING: over-under and braids. Horizontal and vertical strands cross; at each
# crossing the strand on top alternates (over, under, over...) along the row, starting with horizontal
# on top unless stated otherwise. A key cell (or a fixed rule) sets which family starts on top. The
# crossing cell shows whichever strand is ON TOP at that crossing. "Phase" = which family is on top at
# the first crossing of a strand / row / column; it is always stated or fixed by a key cell.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


def _classify_hv(g, colset):
    # Decide which of the two colours is the horizontal strand colour and which is the
    # vertical strand colour from GEOMETRY, never from the order counts() returns them in.
    # A horizontal strand is a full-width (or long horizontal) run; a vertical strand is a
    # full-height (or long vertical) run. Whichever family was painted last in the generator
    # will show a literal complete row/column; the other may be interrupted at crossings, so
    # we test both orientations for both colours and fall back to elimination.
    h, w = dims(g)
    hcol = None; vcol = None
    for c in colset:
        full_row = any(all(g[r][cc] == c for cc in range(w)) for r in range(h))
        full_col = any(all(g[r][cc] == c for r in range(h)) for cc in range(w))
        if full_row and not full_col:
            hcol = c
        elif full_col and not full_row:
            vcol = c
    if hcol is None and vcol is not None:
        hcol = next(c for c in colset if c != vcol)
    if vcol is None and hcol is not None:
        vcol = next(c for c in colset if c != hcol)
    return hcol, vcol


def _hv_grid(rng, lo=10, hi=24, nh_lo=2, nh_hi=4, nv_lo=2, nv_hi=4, hcol=None, vcol=None, gap=3):
    h, w = size(rng, lo, hi)
    g = blank(h, w)
    hcol = hcol if hcol is not None else rng.choice(COLOURS)
    vcol = vcol if vcol is not None else rng.choice([c for c in COLOURS if c != hcol])
    nh = rng.randint(nh_lo, min(nh_hi, h // gap))
    nv = rng.randint(nv_lo, min(nv_hi, w // gap))
    if nh < 1 or nv < 1: return None
    rows = sorted(rng.sample(range(h), nh))
    cols = sorted(rng.sample(range(w), nv))
    if any(rows[i + 1] - rows[i] < 2 for i in range(len(rows) - 1)): return None
    if any(cols[i + 1] - cols[i] < 2 for i in range(len(cols) - 1)): return None
    for r in rows:
        for c in range(w): g[r][c] = hcol
    for c in cols:
        for r in range(h): g[r][c] = vcol
    return g, rows, cols, hcol, vcol


# 1. baseline alternation: on each horizontal strand, crossings alternate h-on-top, v-on-top, h-on-top...
def gi_alt_row(rng):
    t = _hv_grid(rng, 10, 26)
    return None if t is None else t[0]
def tf_alt_row(g):
    h, w = dims(g)
    hcol = {}; vcol = {}
    rows = [r for r in range(h) if g[r].count(g[r][0]) == w or len(set(g[r])) <= 2]
    out = copy(g)
    cnt = {}
    colset = counts(g)
    cols_present = [c for c in colset if c != 0]
    if len(cols_present) != 2: return None
    a, b = cols_present
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (a, b)) == w]
    collines = [c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (a, b)) == h]
    if not rowlines or not collines: return None
    for r in rowlines:
        k = 0
        for c in sorted(collines):
            out[r][c] = a if k % 2 == 0 else b
            k += 1
    return out
rule("weave_alternate_horizontal_strand", "Horizontal and vertical strands cross on a grid; on every horizontal strand each crossing alternates the two colours left to right starting with the horizontal strand's colour (phase fixed at the leftmost crossing).", gi_alt_row, tf_alt_row)


# 2. key cell sets which family starts on top at every crossing.
def gi_key_top(rng):
    t = _hv_grid(rng, 10, 26)
    if t is None: return None
    g, rows, cols, hcol, vcol = t
    top_h = rng.random() < 0.5
    g[0][0] = hcol if top_h else vcol
    return g
def tf_key_top(g):
    h, w = dims(g)
    key = g[0][0]
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (a, b)) == w]
    collines = [c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (a, b)) == h]
    if not rowlines or not collines: return None
    out = copy(g)
    for r in rowlines:
        for c in sorted(collines):
            out[r][c] = key
    out[0][0] = key
    return out
rule("weave_key_sets_top_strand", "The cell at the top-left corner is the key: it names the colour that lies on top at every crossing of the horizontal and vertical strands.", gi_key_top, tf_key_top)


# 3. colour of one family always goes over (fixed by rule, not alternation).
def gi_always_over(rng):
    t = _hv_grid(rng, 10, 26)
    return None if t is None else t[0]
def tf_always_over(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    over = min(a, b)
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (a, b)) == w]
    collines = [c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (a, b)) == h]
    if not rowlines or not collines: return None
    out = copy(g)
    for r in rowlines:
        for c in sorted(collines):
            out[r][c] = over
    return out
rule("weave_lower_colour_always_over", "Horizontal and vertical strands cross on a grid; whichever strand carries the numerically lower colour value always shows at every crossing cell.", gi_always_over, tf_always_over)


# 4. crossing cell shows a third colour (where the under strand would show).
def gi_third_colour(rng):
    h, w = size(rng, 10, 26)
    g = blank(h, w)
    hcol, vcol, under_mark = colours(rng, 3)
    nh = rng.randint(2, min(4, h // 3)); nv = rng.randint(2, min(4, w // 3))
    rows = sorted(rng.sample(range(h), nh)); cols = sorted(rng.sample(range(w), nv))
    if any(rows[i + 1] - rows[i] < 2 for i in range(len(rows) - 1)): return None
    if any(cols[i + 1] - cols[i] < 2 for i in range(len(cols) - 1)): return None
    for r in rows:
        for c in range(w): g[r][c] = hcol
    for c in cols:
        for r in range(h): g[r][c] = vcol
    g[0][0] = under_mark
    return g
def tf_third_colour(g):
    h, w = dims(g)
    under_mark = g[0][0]
    colset = [c for c in counts(g) if c != 0 and c != under_mark]
    if len(colset) != 2: return None
    hcol, vcol = _classify_hv(g, colset)
    if hcol is None or vcol is None: return None
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (hcol, vcol)) == w]
    collines = [c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (hcol, vcol)) == h]
    if not rowlines or not collines: return None
    out = copy(g)
    k0 = 0
    for ri, r in enumerate(rowlines):
        k = 0
        for c in sorted(collines):
            out[r][c] = under_mark if k % 2 == 1 else hcol
            k += 1
    out[0][0] = under_mark
    return out
rule("weave_crossing_shows_third_colour", "The top-left cell names a third colour; on every horizontal strand, alternating crossings (starting on top) show the horizontal colour then that third colour marking where the vertical strand would show through underneath.", gi_third_colour, tf_third_colour)


# 5. two diagonal strands braided with alternating crossings.
def gi_diag_braid(rng):
    h, w = size(rng, 14, 26)
    p = rng.randint(3, 5)
    a, b = colours(rng, 2)
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if (r - c) % p == 0: g[r][c] = a
    for r in range(h):
        for c in range(w):
            if (r + c) % p == 0: g[r][c] = b
    return g
def tf_diag_braid(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    out = copy(g)
    crossings = []
    # infer period by scanning the b-diagonal spacing on row 0
    p = None
    bcols = sorted(c for c in range(w) if g[0][c] == b)
    if len(bcols) >= 2: p = bcols[1] - bcols[0]
    if p is None:
        acols = sorted(c for c in range(w) if g[0][c] == a)
        p = acols[1] - acols[0] if len(acols) >= 2 else 4
    for r in range(h):
        for c in range(w):
            on_a = (r - c) % p == 0
            on_b = (r + c) % p == 0
            if on_a and on_b:
                crossings.append((r, c))
    if not crossings: return None
    for k, (r, c) in enumerate(sorted(crossings)):
        out[r][c] = a if k % 2 == 0 else b
    return out
rule("diagonal_braid_alternating_crossing", "Two families of diagonal strands braid across the grid, one sloping down-right and one down-left at the same fixed period; every cell where both families meet is a crossing, and in reading order the crossings alternate which family's colour shows, starting with the down-right colour on top.", gi_diag_braid, tf_diag_braid)


# 6. basket weave, band width 2.
def gi_basket(rng):
    h, w = size(rng, 10, 26)
    a, b = colours(rng, 2)
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            br = (r // 2) % 2
            bc = (c // 2) % 2
            g[r][c] = a if br == bc else b
    return g
def tf_basket(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    out = blank(h, w)
    for r in range(h):
        for c in range(w):
            br = (r // 2) % 2
            bc = (c // 2) % 2
            out[r][c] = b if br == bc else a
    return out
rule("basket_weave_band_width_two", "A basket weave of two colours in bands two cells wide is drawn; the transform swaps which colour occupies the matching-band squares versus the mismatched-band squares.", gi_basket, tf_basket)


# 7. checkerboard weave, phase set by a corner cell.
def gi_checker_phase(rng):
    h, w = size(rng, 10, 26)
    a, b = colours(rng, 2)
    phase = rng.choice([0, 1])
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            g[r][c] = a if (r + c) % 2 == phase else b
    g[0][0] = a if phase == 0 else b
    return g
def tf_checker_phase(g):
    h, w = dims(g)
    phase_colour = g[0][0]
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    other = b if phase_colour == a else a
    out = blank(h, w)
    for r in range(h):
        for c in range(w):
            out[r][c] = other if (r + c) % 2 == 0 else phase_colour
    out[0][0] = other
    return out
rule("checker_weave_phase_swap", "A checkerboard weave's phase (which colour sits at the top-left) is given by the top-left cell; the transform swaps the two colours everywhere, flipping which colour starts the pattern.", gi_checker_phase, tf_checker_phase)


# 8. lifted crossings: every crossing where vertical is on top is marked grey.
def gi_lifted(rng):
    t = _hv_grid(rng, 10, 26)
    if t is None: return None
    g, rows, cols, hcol, vcol = t
    return g
def tf_lifted(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (a, b)) == w]
    collines = [c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (a, b)) == h]
    if not rowlines or not collines: return None
    out = copy(g)
    for r in rowlines:
        k = 0
        for c in sorted(collines):
            if k % 2 == 1:
                out[r][c] = 5
            k += 1
    return out
rule("weave_mark_vertical_on_top_grey", "On every horizontal strand, crossings alternate horizontal-on-top then vertical-on-top starting on top; every crossing where the vertical strand is on top is recoloured grey.", gi_lifted, tf_lifted)


# 9. strands cut at under crossings: output only the over segments (horizontal strand only).
def gi_cut_under(rng):
    t = _hv_grid(rng, 10, 26, nh_lo=1, nh_hi=1)
    if t is None: return None
    g, rows, cols, hcol, vcol = t
    return g
def tf_cut_under(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (a, b)) == w]
    collines = sorted(c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (a, b)) == h)
    if len(rowlines) != 1 or not collines: return None
    r = rowlines[0]
    out = copy(g)
    for c in range(w):
        if out[r][c] not in (0,) and c not in collines:
            continue
    for ci, c in enumerate(collines):
        if ci % 2 == 1:
            out[r][c] = 0
    return out
rule("weave_cut_strand_at_under_crossing", "A single horizontal strand crosses several vertical strands, alternating over-under starting over; the horizontal strand is erased (set to background) at every crossing where it goes under, leaving only its over segments visible.", gi_cut_under, tf_cut_under)


# 10. count over-crossings per horizontal strand as a bar.
def gi_overcount_bar(rng):
    h, w = size(rng, 10, 24)
    g = blank(h, w)
    hcol, vcol = colours(rng, 2)
    nh = rng.randint(2, min(4, h // 3))
    nv = rng.randint(2, min(6, w // 2))
    rows = sorted(rng.sample(range(h), nh))
    if any(rows[i+1]-rows[i] < 2 for i in range(len(rows)-1)): return None
    cols = sorted(rng.sample(range(w), nv))
    for r in rows:
        for c in range(w): g[r][c] = hcol
    for c in cols:
        for r in range(h): g[r][c] = vcol
    return g
def tf_overcount_bar(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (a, b)) == w]
    collines = [c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (a, b)) == h]
    if not rowlines or not collines: return None
    out = blank(len(rowlines), len(collines))
    for i, r in enumerate(rowlines):
        over = (len(collines) + 1) // 2
        for c in range(over):
            out[i][c] = a
    return out
rule("weave_over_crossing_count_bar", "For each horizontal strand, count how many of its crossings have it on top (it alternates on top first); output one row per strand with that many cells filled in the strand's colour from the left.", gi_overcount_bar, tf_overcount_bar)


# 11. defect correction: one crossing breaks the alternation; restore it.
def gi_defect(rng):
    t = _hv_grid(rng, 12, 26, nh_lo=1, nh_hi=1, nv_lo=4, nv_hi=6)
    if t is None: return None
    g, rows, cols, hcol, vcol = t
    r = rows[0]
    k = 0
    for c in sorted(cols):
        g[r][c] = hcol if k % 2 == 0 else vcol
        k += 1
    bad = rng.randrange(len(cols))
    cbad = sorted(cols)[bad]
    g[r][cbad] = vcol if g[r][cbad] == hcol else hcol
    return g
def tf_defect(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (a, b)) == w]
    collines = sorted(c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (a, b)) == h)
    if len(rowlines) != 1 or not collines: return None
    r = rowlines[0]
    out = copy(g)
    for k, c in enumerate(collines):
        out[r][c] = a if k % 2 == 0 else b
    return out
rule("weave_fix_crossing_defect", "A single horizontal strand crosses several vertical strands and should alternate on-top/under starting on top; one crossing breaks the pattern, and the transform restores strict alternation.", gi_defect, tf_defect)


# 12. woven texture continued across a blank region.
def gi_continue_texture(rng):
    h, w = size(rng, 12, 26)
    a, b = colours(rng, 2)
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            g[r][c] = a if (r + c) % 2 == 0 else b
    br, bc = rng.randint(2, h - 5), rng.randint(2, w - 5)
    bh, bw = rng.randint(2, min(4, h - br - 1)), rng.randint(2, min(4, w - bc - 1))
    for r in range(br, br + bh):
        for c in range(bc, bc + bw):
            g[r][c] = 0
    return g
def tf_continue_texture(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    out = copy(g)
    for r in range(h):
        for c in range(w):
            if out[r][c] == 0:
                out[r][c] = a if (r + c) % 2 == 0 else b
    return out
rule("weave_continue_texture_blank_region", "A checkerboard weave of two colours fills the grid except for one blank rectangular patch; the transform continues the same (row+col)-parity pattern into the blank patch.", gi_continue_texture, tf_continue_texture)


# 13. vertical-strand starting on top variant.
def gi_alt_col(rng):
    t = _hv_grid(rng, 10, 26)
    return None if t is None else t[0]
def tf_alt_col(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (a, b)) == w]
    collines = [c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (a, b)) == h]
    if not rowlines or not collines: return None
    out = copy(g)
    for c in sorted(collines):
        k = 0
        for r in sorted(rowlines):
            out[r][c] = b if k % 2 == 0 else a
            k += 1
    return out
rule("weave_alternate_vertical_strand", "Horizontal and vertical strands cross on a grid; on every vertical strand each crossing alternates top to bottom, starting with the vertical strand's own colour on top at the topmost crossing.", gi_alt_col, tf_alt_col)


# 14. two colour blocks used for warp, third for weft, recolour weft at over-crossings.
def gi_warp_weft(rng):
    h, w = size(rng, 10, 26)
    warp, weft = colours(rng, 2)
    g = blank(h, w)
    nv = rng.randint(2, min(5, w // 2))
    cols = sorted(rng.sample(range(w), nv))
    for c in cols:
        for r in range(h): g[r][c] = warp
    nh = rng.randint(2, min(5, h // 2))
    rows = sorted(rng.sample(range(h), nh))
    if any(rows[i+1]-rows[i] < 2 for i in range(len(rows)-1)): return None
    for r in rows:
        for c in range(w): g[r][c] = weft
    return g
def tf_warp_weft(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    weft, warp = _classify_hv(g, colset)
    if weft is None or warp is None: return None
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (warp, weft)) == w]
    collines = sorted(c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (warp, weft)) == h)
    if not rowlines or not collines: return None
    out = copy(g)
    for r in rowlines:
        for ci, c in enumerate(collines):
            out[r][c] = weft if ci % 2 == 0 else warp
    return out
rule("weave_warp_weft_recolour_over", "The vertical warp strands and horizontal weft strands cross; on each weft (horizontal) strand the weft colour shows at every other crossing starting with the first (leftmost), alternating with the warp colour.", gi_warp_weft, tf_warp_weft)


# 15. braid of three vertical strands plaited in a fixed cyclic order.
def gi_plait3(rng):
    h = rng.randint(12, 26)
    spacing = rng.randint(2, 4)
    pad = rng.randint(0, 3)
    start = rng.randint(0, 2)
    w = pad + spacing * 2 + 3
    a, b, c = colours(rng, 3)
    order = [a, b, c]
    g = blank(h, w)
    positions = [pad + i * spacing for i in range(3)]
    for r in range(h):
        shift = (r + start) % 3
        seq = order[shift:] + order[:shift]
        for pos, col in zip(positions, seq):
            g[r][pos] = col
    return g
def tf_plait3(g):
    h, w = dims(g)
    colset = sorted(c for c in counts(g) if c != 0)
    if len(colset) != 3: return None
    positions = sorted(c for c in range(w) if any(g[r][c] != 0 for r in range(h)))
    if len(positions) != 3: return None
    out = copy(g)
    for r in range(h):
        seq = [g[r][p] for p in positions]
        if any(v == 0 for v in seq): continue
        rot = seq[1:] + seq[:1]
        for pos, col in zip(positions, rot):
            out[r][pos] = col
    return out
rule("three_strand_plait_shift", "Three vertical strands plait together, cyclically shifting which strand occupies each of the three lanes every row; the transform advances the plait by one more row of cyclic shift.", gi_plait3, tf_plait3)


# 16. herringbone weave block pattern.
def gi_herringbone(rng):
    h, w = size(rng, 12, 26)
    a, b = colours(rng, 2)
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            g[r][c] = a if ((r + c) // 2) % 2 == 0 else b
    return g
def tf_herringbone(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    out = blank(h, w)
    for r in range(h):
        for c in range(w):
            out[r][c] = b if ((r + c) // 2) % 2 == 0 else a
    return out
rule("herringbone_weave_swap", "A herringbone weave pattern of two colours, in diagonal bands two cells wide, has its two colours swapped everywhere.", gi_herringbone, tf_herringbone)


# 17. single vertical strand woven through a row of fixed horizontal bars, over pattern 1-1-2 repeat.
def gi_period3(rng):
    t = _hv_grid(rng, 12, 26, nh_lo=1, nh_hi=1, nv_lo=5, nv_hi=8)
    if t is None: return None
    g, rows, cols, hcol, vcol = t
    return g
def tf_period3(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (a, b)) == w]
    collines = sorted(c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (a, b)) == h)
    if len(rowlines) != 1 or len(collines) < 3: return None
    r = rowlines[0]
    out = copy(g)
    pattern = [a, a, b]
    for i, c in enumerate(collines):
        out[r][c] = pattern[i % 3]
    return out
rule("weave_period_three_over_over_under", "A single horizontal strand crosses several vertical strands using a three-step over-over-under repeat (the strand's own colour twice then the vertical colour once, left to right).", gi_period3, tf_period3)


# 18. mark every under-crossing of vertical strands with grey, leave over as-is (vertical perspective, phase vertical first).
def gi_vert_under_mark(rng):
    t = _hv_grid(rng, 10, 26)
    return None if t is None else t[0]
def tf_vert_under_mark(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (a, b)) == w]
    collines = [c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (a, b)) == h]
    if not rowlines or not collines: return None
    out = copy(g)
    for c in sorted(collines):
        k = 0
        for r in sorted(rowlines):
            if k % 2 == 1:
                out[r][c] = 5
            k += 1
    return out
rule("weave_mark_vertical_under_grey", "Crossings on each vertical strand alternate on top then under starting on top at the topmost crossing; every crossing where the vertical strand goes under is recoloured grey.", gi_vert_under_mark, tf_vert_under_mark)


# 19. double-width braid: two strands per family, interleaved, output cropped to the braid band.
def gi_braid_band(rng):
    h, w = size(rng, 14, 26)
    if w < 6: return None
    c1 = rng.randint(1, w // 2 - 1); c2 = rng.randint(w // 2 + 1, w - 2)
    a, b = colours(rng, 2)
    g = blank(h, w)
    for r in range(h):
        off = r % 4
        if off < 2:
            g[r][c1] = a; g[r][c2] = b
        else:
            g[r][c1] = b; g[r][c2] = a
    return g
def tf_braid_band(g):
    h, w = dims(g)
    colset = sorted(c for c in counts(g) if c != 0)
    if len(colset) != 2: return None
    a, b = colset
    strandcols = [c for c in range(w) if any(g[r][c] != 0 for r in range(h))]
    if len(strandcols) != 2: return None
    c1, c2 = strandcols
    out = copy(g)
    for r in range(h):
        off = (r + 2) % 4
        if off < 2:
            out[r][c1] = a; out[r][c2] = b
        else:
            out[r][c1] = b; out[r][c2] = a
    return out
rule("braid_two_strand_phase_advance", "Two strands braid in a narrow vertical band, swapping which lane each colour occupies every two rows; the transform advances the swap phase by two rows.", gi_braid_band, tf_braid_band)


# 20. weave grid where crossing count per vertical strand becomes a column of dots.
def gi_vertcount_col(rng):
    return gi_overcount_bar(rng)
def tf_vertcount_col(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (a, b)) == w]
    collines = [c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (a, b)) == h]
    if not rowlines or not collines: return None
    out = blank(len(collines), len(rowlines))
    for ci in range(len(collines)):
        under = len(rowlines) // 2
        for r in range(under):
            out[ci][r] = b
    return out
rule("weave_under_crossing_count_bar_vertical", "For each vertical strand, count how many of its crossings have it going under (horizontal alternates on top first); output one row per strand with that many cells filled in the horizontal colour from the left.", gi_vertcount_col, tf_vertcount_col)


# 21. twill weave: diagonal stepping pattern of two colours.
def gi_twill(rng):
    h, w = size(rng, 12, 26)
    a, b = colours(rng, 2)
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            g[r][c] = a if (r - c) % 4 < 2 else b
    return g
def tf_twill(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    out = blank(h, w)
    for r in range(h):
        for c in range(w):
            out[r][c] = a if (r - c) % 4 >= 2 else b
    return out
rule("twill_weave_diagonal_shift", "A twill weave made of diagonal two-cell-wide steps of two colours is shifted by two steps along the diagonal, swapping which colour occupies each stripe.", gi_twill, tf_twill)


# 22. recolour crossings by which strand is on top, output a legend row below.
def gi_legend(rng):
    t = _hv_grid(rng, 10, 24, nh_lo=1, nh_hi=1, nv_lo=3, nv_hi=5)
    if t is None: return None
    g, rows, cols, hcol, vcol = t
    return g
def tf_legend(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (a, b)) == w]
    collines = sorted(c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (a, b)) == h)
    if len(rowlines) != 1 or not collines: return None
    r = rowlines[0]
    out = copy(g)
    for k, c in enumerate(collines):
        out[r][c] = a if k % 2 == 0 else b
    legend = [0] * w
    for k, c in enumerate(collines):
        legend[c] = a if k % 2 == 0 else b
    return out + [legend]
rule("weave_legend_row_of_top_colour", "A single horizontal strand crosses several vertical strands alternating on top starting on top; the strand is set to the alternating pattern, and one extra row below the grid repeats which colour was on top at each crossing column.", gi_legend, tf_legend)


# 23. recolour the whole vertical strand by whether its first crossing (topmost) has it on top or under.
def gi_strand_status(rng):
    h, w = size(rng, 12, 26)
    hcol, vcol = colours(rng, 2)
    g = blank(h, w)
    nv = rng.randint(2, min(5, w // 2))
    cols = sorted(rng.sample(range(w), nv))
    for c in cols:
        for r in range(h): g[r][c] = vcol
    row = rng.randrange(h)
    for c in range(w): g[row][c] = hcol
    return g
def tf_strand_status(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (a, b)) == w]
    collines = sorted(c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (a, b)) == h)
    if len(rowlines) != 1 or not collines: return None
    row = rowlines[0]
    out = copy(g)
    for i, c in enumerate(collines):
        top = a if i % 2 == 0 else b
        for r in range(h):
            if r != row:
                out[r][c] = top
    return out
rule("weave_strand_recoloured_by_crossing_status", "One horizontal strand crosses several vertical strands, alternating on top starting on top; every vertical strand is recoloured in its entirety to whichever colour was on top at its single crossing.", gi_strand_status, tf_strand_status)


# 24. zigzag braid using a single strand bouncing between two columns, crossing a fixed vertical line.
def gi_zigzag_cross(rng):
    h = rng.randint(12, 26)
    w = rng.randint(6, 12)
    a, b = colours(rng, 2)
    g = blank(h, w)
    vc = w // 2
    for r in range(h): g[r][vc] = b
    lo, hi = vc - 2, vc + 2
    if lo < 0 or hi >= w: return None
    c = lo
    step = 1
    for r in range(h):
        g[r][c] = a
        c += step
        if c >= hi or c <= lo: step = -step
    return g
def tf_zigzag_cross(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    vc_col = next(c for c in range(w) if sum(1 for r in range(h) if g[r][c] != 0) == h)
    a = next(c for c in colset if c != g[0][vc_col])
    b = g[0][vc_col]
    out = copy(g)
    for r in range(h):
        if out[r][vc_col] == a:
            out[r][vc_col] = b
    return out
rule("zigzag_strand_crosses_vertical_bar", "A zigzagging diagonal strand crosses one fixed vertical bar; every cell where the zigzag strand sits exactly on the bar is recoloured to the bar's colour, showing the bar always on top there.", gi_zigzag_cross, tf_zigzag_cross)


# 25. weave with one strand recoloured where it would be on top, based on key choosing horizontal-always.
def gi_fixed_h_over(rng):
    t = _hv_grid(rng, 10, 26)
    return None if t is None else t[0]
def tf_fixed_h_over(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (a, b)) == w]
    collines = [c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (a, b)) == h]
    if not rowlines or not collines: return None
    hcol = a if sum(1 for v in g[rowlines[0]] if v == a) > w // 2 else b
    out = copy(g)
    for r in rowlines:
        for c in collines:
            out[r][c] = hcol
    return out
rule("weave_horizontal_always_over", "Horizontal and vertical strands cross; the horizontal strand's own colour always shows at every crossing, so the horizontal family is always on top regardless of position.", gi_fixed_h_over, tf_fixed_h_over)


# 26. weave with vertical always over (complement of above, different fixed rule, still distinct description).
def gi_fixed_v_over(rng):
    t = _hv_grid(rng, 10, 26)
    return None if t is None else t[0]
def gi_fixed_v_over2(rng):
    h, w = size(rng, 10, 26)
    g = blank(h, w)
    hcol, vcol = colours(rng, 2)
    nh = rng.randint(2, min(4, h // 3)); nv = rng.randint(2, min(4, w // 3))
    rows = sorted(rng.sample(range(h), nh)); cols = sorted(rng.sample(range(w), nv))
    if any(rows[i+1]-rows[i] < 2 for i in range(len(rows)-1)): return None
    if any(cols[i+1]-cols[i] < 2 for i in range(len(cols)-1)): return None
    for c in cols:
        for r in range(h): g[r][c] = vcol
    for r in rows:
        for c in range(w): g[r][c] = hcol
    return g
def tf_fixed_v_over(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (a, b)) == w]
    collines = [c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (a, b)) == h]
    if not rowlines or not collines: return None
    vcol = a if sum(1 for row in g for v in [row[collines[0]]] if v == a) > h // 2 else b
    out = copy(g)
    for r in rowlines:
        for c in collines:
            out[r][c] = vcol
    return out
rule("weave_vertical_always_over", "Horizontal and vertical strands cross; the vertical strand's own colour always shows at every crossing, so the vertical family is always on top regardless of position.", gi_fixed_v_over2, tf_fixed_v_over)


# 27. braid with a defect: a crossing coloured neither strand colour, fix to current alternation colour.
def gi_wrong_colour_defect(rng):
    t = _hv_grid(rng, 12, 26, nh_lo=1, nh_hi=1, nv_lo=4, nv_hi=7)
    if t is None: return None
    g, rows, cols, hcol, vcol = t
    r = rows[0]
    k = 0
    for c in sorted(cols):
        g[r][c] = hcol if k % 2 == 0 else vcol
        k += 1
    bad_idx = rng.randrange(len(cols))
    others = [x for x in COLOURS if x not in (hcol, vcol)]
    if not others: return None
    g[r][sorted(cols)[bad_idx]] = rng.choice(others)
    return g
def tf_wrong_colour_defect(g):
    h, w = dims(g)
    cnt = counts(g)
    cnt.pop(0, None)
    if len(cnt) != 3: return None
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] != 0) == w]
    if len(rowlines) != 1: return None
    r = rowlines[0]
    cols_colour = {}
    for c in range(w):
        v = g[r][c]
        cols_colour[v] = cols_colour.get(v, 0) + 1
    hcol = max(cols_colour, key=lambda k: cols_colour[k])
    collines = sorted(c for c in range(w) if g[r][c] != hcol or True)
    vcols = [c for c in range(w)]
    out = copy(g)
    k = 0
    for c in range(w):
        out[r][c] = hcol if k % 2 == 0 else [x for x in cnt if x != hcol][0]
        k += 1
    return out
rule("weave_fix_wrong_colour_crossing", "A single horizontal strand crosses several vertical strands alternating its colour and the vertical colour starting on top; one crossing was painted a third, wrong colour, and the transform repaints it to match the strict alternation.", gi_wrong_colour_defect, tf_wrong_colour_defect)


# 28. count of over-crossings used to recolour the strand itself (self-referential, by threshold).
def gi_self_recolour(rng):
    t = _hv_grid(rng, 12, 26, nh_lo=1, nh_hi=1, nv_lo=3, nv_hi=9)
    if t is None: return None
    g, rows, cols, hcol, vcol = t
    return g
def tf_self_recolour(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (a, b)) == w]
    collines = sorted(c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (a, b)) == h)
    if len(rowlines) != 1 or not collines: return None
    r = rowlines[0]
    n_over = (len(collines) + 1) // 2
    out = copy(g)
    mark = 5 if n_over >= len(collines) - n_over else 3
    if mark not in (a, b):
        for c in range(w):
            if c not in collines:
                out[r][c] = mark
    return out if mark not in (a, b) else None
rule("weave_strand_coloured_by_over_majority", "A single horizontal strand crosses several vertical strands, alternating on top starting on top; if it is on top at a majority of crossings its non-crossing segments are painted grey, otherwise orange.", gi_self_recolour, tf_self_recolour)


# 29. rotate the whole weave pattern's phase by shifting alternation start.
def gi_phase_shift_key(rng):
    t = _hv_grid(rng, 12, 26, nh_lo=1, nh_hi=1, nv_lo=3, nv_hi=7)
    if t is None: return None
    g, rows, cols, hcol, vcol = t
    g[rows[0]][0] = vcol if g[rows[0]][0] == hcol else g[rows[0]][0]
    g[0][0] = hcol
    return g
def tf_phase_shift_key(g):
    h, w = dims(g)
    key = g[0][0]
    cnt = counts(g)
    cnt.pop(0, None)
    if len(cnt) != 2: return None
    other = [x for x in cnt if x != key][0]
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (key, other)) == w]
    collines = sorted(c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (key, other)) == h)
    if len(rowlines) != 1 or not collines: return None
    r = rowlines[0]
    out = copy(g)
    for k, c in enumerate(collines):
        out[r][c] = other if k % 2 == 0 else key
    out[0][0] = key
    return out
rule("weave_phase_set_by_corner_key_opposite", "The top-left cell names the key colour; a single horizontal strand crosses several vertical strands, alternating so the OTHER (non-key) colour is on top at the first crossing instead of the strand's own colour.", gi_phase_shift_key, tf_phase_shift_key)


# 30. grid of many small plus-shaped crossings (4-connected strands) recoloured by local alternation parity.
def gi_plus_lattice(rng):
    h, w = size(rng, 14, 26)
    a, b = colours(rng, 2)
    g = blank(h, w)
    step = 4
    for r in range(1, h, step):
        for c in range(w): g[r][c] = a
    for c in range(1, w, step):
        for r in range(h): g[r][c] = b
    return g if h > step and w > step else None
def tf_plus_lattice(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (a, b)) == w]
    collines = [c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (a, b)) == h]
    if not rowlines or not collines: return None
    out = copy(g)
    for ri, r in enumerate(sorted(rowlines)):
        for ci, c in enumerate(sorted(collines)):
            out[r][c] = a if (ri + ci) % 2 == 0 else b
    return out
rule("plus_lattice_crossing_checker_alternate", "A lattice of evenly-spaced horizontal and vertical strands crosses repeatedly; each crossing is recoloured by checkerboard parity of its row-strand and column-strand indices, starting horizontal-on-top at the first crossing of each.", gi_plus_lattice, tf_plus_lattice)


# 31. braid: strand colours swap entirely when a key cell is a third marker colour.
def gi_swap_on_marker(rng):
    t = _hv_grid(rng, 10, 24)
    if t is None: return None
    g, rows, cols, hcol, vcol = t
    others = [c for c in COLOURS if c not in (hcol, vcol)]
    if not others: return None
    marker = rng.choice(others)
    if rng.random() < 0.5:
        g[0][0] = marker
    return g
def tf_swap_on_marker(g):
    h, w = dims(g)
    cnt = counts(g)
    marker = g[0][0]
    has_marker = marker != 0 and (h == 1 or w == 1 or marker not in [g[r][c] for r in range(1, h) for c in range(1, w)] or True)
    cnt2 = dict(cnt); cnt2.pop(0, None)
    strand_cols = [c for c in cnt2 if c != marker] if marker in cnt2 else [c for c in cnt2]
    if marker in cnt2 and len(strand_cols) == 2:
        a, b = strand_cols
        out = copy(g)
        for r in range(h):
            for c in range(w):
                if out[r][c] == a: out[r][c] = b
                elif out[r][c] == b: out[r][c] = a
        out[0][0] = marker
        return out
    return None
rule("weave_swap_strand_colours_on_marker", "Horizontal and vertical strands cross on a grid; if the top-left cell carries a third marker colour, the two strand colours are swapped everywhere else in the grid.", gi_swap_on_marker, tf_swap_on_marker)


# 32. weave where only the crossings matter: output a condensed grid of just the crossing cells in order.
def gi_condense_crossings(rng):
    t = _hv_grid(rng, 12, 26, nh_lo=2, nh_hi=4, nv_lo=2, nv_hi=4)
    return None if t is None else t[0]
def tf_condense_crossings(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    rowlines = sorted(r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (a, b)) == w)
    collines = sorted(c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (a, b)) == h)
    if not rowlines or not collines: return None
    out = blank(len(rowlines), len(collines))
    for ri in range(len(rowlines)):
        for ci in range(len(collines)):
            out[ri][ci] = a if (ri + ci) % 2 == 0 else b
    return out
rule("weave_condense_to_crossing_grid", "Horizontal and vertical strands cross on a larger grid; output a small grid with one cell per crossing, each coloured by the usual alternation (horizontal strand's colour where it is on top, starting on top at the first crossing of each strand in reading order).", gi_condense_crossings, tf_condense_crossings)


# 33. basket weave band width 2, phase from a corner marker rather than fixed.
def gi_basket_phase(rng):
    h, w = size(rng, 12, 26)
    a, b = colours(rng, 2)
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            br = (r // 2) % 2
            bc = (c // 2) % 2
            g[r][c] = a if br == bc else b
    g[0][0] = b  # marker names the colour that should take over the matching bands (forces a swap)
    return g
def tf_basket_phase(g):
    h, w = dims(g)
    marker = g[0][0]
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    other = b if marker == a else a
    out = blank(h, w)
    for r in range(h):
        for c in range(w):
            br = (r // 2) % 2
            bc = (c // 2) % 2
            out[r][c] = marker if br == bc else other
    out[0][0] = marker
    return out
rule("basket_weave_phase_from_corner", "A basket weave in two-cell bands has its phase (which colour fills the matching-band squares) given by the top-left cell; the transform redraws the weave so the matching-band squares are the marker's colour.", gi_basket_phase, tf_basket_phase)


# 34. partial weave completed symmetrically (mirrored half).
def gi_half_weave(rng):
    h, w = size(rng, 12, 26)
    if w % 2 != 0: w += 1
    a, b = colours(rng, 2)
    phase = rng.randint(0, 1)
    g = blank(h, w)
    half = w // 2
    for r in range(h):
        for c in range(half):
            g[r][c] = a if (r + c + phase) % 2 == 0 else b
    return g
def tf_half_weave(g):
    h, w = dims(g)
    half = w // 2
    out = copy(g)
    for r in range(h):
        for c in range(half):
            out[r][w - 1 - c] = out[r][c]
    return out
rule("weave_pattern_mirrored_to_fill_half", "A checkerboard weave fills only the left half of the grid; the transform mirrors that half into the right half, completing the pattern symmetrically.", gi_half_weave, tf_half_weave)


# 35. strands of fixed colour always over regardless of alternation elsewhere (colour-keyed, not position-keyed).
def gi_colour_always_wins(rng):
    h, w = size(rng, 10, 26)
    g = blank(h, w)
    special = rng.choice(COLOURS)
    other = rng.choice([c for c in COLOURS if c != special])
    nh = rng.randint(2, min(4, h // 3)); nv = rng.randint(2, min(4, w // 3))
    rows = sorted(rng.sample(range(h), nh)); cols = sorted(rng.sample(range(w), nv))
    if any(rows[i+1]-rows[i] < 2 for i in range(len(rows)-1)): return None
    if any(cols[i+1]-cols[i] < 2 for i in range(len(cols)-1)): return None
    is_special_h = rng.random() < 0.5
    hcol = special if is_special_h else other
    vcol = other if is_special_h else special
    for r in rows:
        for c in range(w): g[r][c] = hcol
    for c in cols:
        for r in range(h): g[r][c] = vcol
    g[0][0] = special
    return g
def tf_colour_always_wins(g):
    h, w = dims(g)
    special = g[0][0]
    cnt = counts(g)
    cnt.pop(0, None)
    strand_cols = [c for c in cnt if c != special or True]
    cols2 = sorted(set(strand_cols))
    if len(cols2) != 2 or special not in cols2: return None
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in cols2) == w]
    collines = [c for c in range(w) if sum(1 for r in range(h) if g[r][c] in cols2) == h]
    if not rowlines or not collines: return None
    out = copy(g)
    for r in rowlines:
        for c in collines:
            out[r][c] = special
    out[0][0] = special
    return out
rule("weave_special_colour_always_on_top", "The top-left cell names a special colour; wherever strands of that colour cross a strand of any other colour, the special colour always shows, regardless of whether it belongs to the horizontal or vertical family.", gi_colour_always_wins, tf_colour_always_wins)


# 36. braid continuation: extend a partial braid pattern downward by repeating its period.
def gi_braid_extend(rng):
    period = rng.randint(2, 4)
    h, w = size(rng, 14, 26)
    if w < 6: return None
    c1 = rng.randint(1, w // 2 - 1); c2 = rng.randint(w // 2 + 1, w - 2)
    a, b = colours(rng, 2)
    g = blank(h, w)
    given = period * 2
    if given >= h - 2: return None
    for r in range(given):
        off = r % period
        if off < period // 2 + period % 2:
            g[r][c1] = a; g[r][c2] = b
        else:
            g[r][c1] = b; g[r][c2] = a
    return g
def tf_braid_extend(g):
    h, w = dims(g)
    colset = sorted(c for c in counts(g) if c != 0)
    if len(colset) != 2: return None
    a, b = colset
    strandcols = [c for c in range(w) if any(g[r][c] != 0 for r in range(h))]
    if len(strandcols) != 2: return None
    c1, c2 = strandcols
    given_rows = sorted(r for r in range(h) if g[r][c1] != 0)
    if len(given_rows) < 2: return None
    period = None
    for p in (2, 3, 4):
        if len(given_rows) >= p and all(g[given_rows[i]][c1] == g[given_rows[i % p]][c1] for i in range(len(given_rows))):
            period = p; break
    if period is None: period = 2
    out = copy(g)
    for r in range(h):
        off = r % period
        if off < period // 2 + period % 2:
            out[r][c1] = a; out[r][c2] = b
        else:
            out[r][c1] = b; out[r][c2] = a
    return out
rule("braid_continue_given_period", "A two-strand braid pattern repeating with a short period is given for only the first few rows; the transform continues the same periodic swap pattern down the full height of the grid.", gi_braid_extend, tf_braid_extend)


# 37. weave where crossings are counted and the max-crossing strand is marked grey end to end.
def gi_busiest_strand(rng):
    h, w = size(rng, 12, 26)
    hcol, vcol = colours(rng, 2)
    g = blank(h, w)
    nh = rng.randint(2, min(4, h // 3))
    rows = sorted(rng.sample(range(h), nh))
    if any(rows[i+1]-rows[i] < 2 for i in range(len(rows)-1)): return None
    nv = rng.randint(2, min(6, w // 2))
    cols = sorted(rng.sample(range(w), nv))
    if any(cols[i+1]-cols[i] < 2 for i in range(len(cols)-1)): return None
    for r in rows:
        for c in range(w): g[r][c] = hcol
    for c in cols:
        for r in range(h): g[r][c] = vcol
    return g if len(set(len(cols) for _ in rows)) >= 1 else None
def tf_busiest_strand(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (a, b)) == w]
    collines = [c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (a, b)) == h]
    if len(rowlines) < 2 or not collines: return None
    busiest = max(rowlines, key=lambda r: len(collines))
    out = copy(g)
    for c in range(w):
        out[busiest][c] = 5
    return out
rule("weave_busiest_strand_marked_grey", "Horizontal strands cross the same set of vertical strands; the horizontal strand with the most crossings (ties broken by the first such strand in row order) is recoloured entirely grey.", gi_busiest_strand, tf_busiest_strand)


# 38. weave recoloured by distance from top-left key cell's row (banding).
def gi_distance_band(rng):
    t = _hv_grid(rng, 12, 26, nh_lo=3, nh_hi=5, nv_lo=1, nv_hi=1)
    if t is None: return None
    g, rows, cols, hcol, vcol = t
    return g
def tf_distance_band(g):
    h, w = dims(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    rowlines = sorted(r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (a, b)) == w)
    collines = [c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (a, b)) == h]
    if len(rowlines) < 2 or not collines: return None
    out = copy(g)
    for i, r in enumerate(rowlines):
        for c in collines:
            out[r][c] = a if i % 2 == 0 else b
    return out
rule("weave_crossing_colour_by_strand_order", "Several horizontal strands cross one vertical strand; the crossing alternates by the horizontal strand's order from the top, starting with the horizontal colour on top for the first strand.", gi_distance_band, tf_distance_band)


# 39. diagonal lattice weave: two sets of diagonals crossing, alternation by sum parity.
def gi_diag_lattice(rng):
    n = rng.randint(14, 26)
    a, b = colours(rng, 2)
    g = blank(n, n)
    step = rng.randint(3, 5)
    off = rng.randint(0, step - 1)
    for k in range(-n + off, n, step):
        for i in range(n):
            j = i + k
            if 0 <= j < n: g[i][j] = a
    for k in range(off, 2 * n, step):
        for i in range(n):
            j = k - i
            if 0 <= j < n: g[i][j] = b
    return g
def tf_diag_lattice(g):
    n = len(g)
    colset = [c for c in counts(g) if c != 0]
    if len(colset) != 2: return None
    a, b = colset
    out = copy(g)
    for i in range(n):
        for j in range(n):
            if g[i][j] in (a, b):
                out[i][j] = a if (i + j) % 2 == 0 else b
    return out
rule("diagonal_lattice_weave_parity_crossing", "Two families of diagonal strands cross in a lattice; every crossing cell is recoloured by the parity of its row plus column index, the even parity showing the first strand colour on top.", gi_diag_lattice, tf_diag_lattice)


# 40. weave corrected: restore a missing strand segment using the alternation of its neighbours.
def gi_missing_segment(rng):
    t = _hv_grid(rng, 12, 26, nh_lo=1, nh_hi=1, nv_lo=4, nv_hi=7)
    if t is None: return None
    g, rows, cols, hcol, vcol = t
    r = rows[0]
    k = 0
    for c in sorted(cols):
        g[r][c] = hcol if k % 2 == 0 else vcol
        k += 1
    gap = rng.randrange(len(cols))
    cgap = sorted(cols)[gap]
    g[r][cgap] = 0
    return g
def tf_missing_segment(g):
    h, w = dims(g)
    cnt = counts(g)
    cnt.pop(0, None)
    if len(cnt) != 2: return None
    a, b = sorted(cnt)
    rowlines = [r for r in range(h) if sum(1 for c in range(w) if g[r][c] in (a, b)) >= w - 1]
    collines = sorted(c for c in range(w) if g[0][c] in (a, b) or sum(1 for r in range(h) if g[r][c] in (a, b)) >= 1)
    collines = sorted(c for c in range(w) if sum(1 for r in range(h) if g[r][c] in (a, b)) >= h - 1 and sum(1 for r in range(h) if g[r][c] != 0) >= h - 1)
    if len(rowlines) != 1: return None
    r = rowlines[0]
    gapcols = [c for c in range(w) if g[r][c] == 0]
    if len(gapcols) != 1: return None
    gapc = gapcols[0]
    allcols = sorted(c for c in range(w) if g[r][c] != 0 or c == gapc)
    out = copy(g)
    for k, c in enumerate(allcols):
        out[r][c] = a if k % 2 == 0 else b
    return out
rule("weave_restore_missing_strand_segment", "A single horizontal strand crosses several vertical strands alternating on top starting on top; one crossing cell was left blank where the strand should be, and the transform fills it in following the alternation of its neighbours.", gi_missing_segment, tf_missing_segment)
