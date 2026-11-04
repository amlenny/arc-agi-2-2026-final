# b055_guides.py -- GUIDE LINES AND SNAPPING: dotted grey lattice guides crossing the grid; objects snap to,
# are cut by, stretch between, or are judged by their position relative to the guides.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

G = 5  # guide colour: grey, fixed under colour permutation (never remapped by the packer)


def _objs(g, extra_exclude=()):
    excl = {0, G, *extra_exclude}
    return components(g, lambda v: v not in excl, conn8=True)


def _col(g, o):
    return g[o[0][0]][o[0][1]]


def _rows_with(g, colour=G):
    return sorted(r for r, row in enumerate(g) if colour in row)


def _cols_with(g, colour=G):
    return sorted(c for c in range(len(g[0])) if any(row[c] == colour for row in g))


def _draw_hguides(g, rows, colour=G, phase=0):
    w = len(g[0])
    for r in rows:
        for c in range(w):
            if (c + phase) % 2 == 0:
                g[r][c] = colour


def _draw_vguides(g, cols, colour=G, phase=0):
    h = len(g)
    for c in cols:
        for r in range(h):
            if (r + phase) % 2 == 0:
                g[r][c] = colour


def _place(rng, g, shape, col, tries=400):
    H, W = dims(g)
    rh = max(r for r, _ in shape) + 1; rw = max(c for _, c in shape) + 1
    if rh > H or rw > W: return None
    for _ in range(tries):
        r0 = rng.randint(0, H - rh); c0 = rng.randint(0, W - rw)
        if all(g[r0 + r][c0 + c] == 0 for r, c in shape):
            for r, c in shape: g[r0 + r][c0 + c] = col
            return r0, c0
    return None


def _rect(rh, rw):
    return [(r, c) for r in range(rh) for c in range(rw)]


def _size(rng, lo=12, hi=28):
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _move(out, o, col, dr, dc):
    for r, c in o: out[r][c] = 0
    for r, c in o: out[r + dr][c + dc] = col


# ---------------------------------------------------------------- 1
def gi_snap_top_above(rng):
    h, w = _size(rng, 14, 28); g = blank(h, w)
    rows = sorted(rng.sample(range(1, max(2, h // 2)), rng.randint(2, 3)))
    if rows[-1] + 4 >= h: return None
    _draw_hguides(g, rows)
    rh, rw = rng.randint(1, 3), rng.randint(1, 4)
    r0 = rng.randint(rows[-1] + 2, h - rh); c0 = rng.randint(0, w - rw)
    if any(g[r0 + r][c0 + c] != 0 for r, c in _rect(rh, rw)): return None
    col = rng.choice(COLOURS)
    for r, c in _rect(rh, rw): g[r0 + r][c0 + c] = col
    return g
def tf_snap_top_above(g):
    out = copy(g); rows = _rows_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o); cands = [r for r in rows if r < r0]
        if not cands: continue
        tgt = max(cands); dr = tgt - r0
        if dr: _move(out, o, _col(g, o), dr, 0)
    return out
rule("snap_top_edge_to_guide_above", "Every object moves straight up so its top edge lands exactly on the nearest dotted guide line above it; an object with no guide above it does not move.", gi_snap_top_above, tf_snap_top_above)


# ---------------------------------------------------------------- 2
def gi_snap_bottom_below(rng):
    h, w = _size(rng, 14, 28); g = blank(h, w)
    rows = sorted(rng.sample(range(h // 2 + 1, h - 1), rng.randint(2, 3)))
    if rows[0] < 4: return None
    _draw_hguides(g, rows)
    rh, rw = rng.randint(1, 3), rng.randint(1, 4)
    r0 = rng.randint(0, rows[0] - rh - 2); c0 = rng.randint(0, w - rw)
    if r0 < 0 or any(g[r0 + r][c0 + c] != 0 for r, c in _rect(rh, rw)): return None
    col = rng.choice(COLOURS)
    for r, c in _rect(rh, rw): g[r0 + r][c0 + c] = col
    return g
def tf_snap_bottom_below(g):
    out = copy(g); rows = _rows_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o); cands = [r for r in rows if r > r1]
        if not cands: continue
        tgt = min(cands); dr = tgt - r1
        if dr: _move(out, o, _col(g, o), dr, 0)
    return out
rule("snap_bottom_edge_to_guide_below", "Every object moves straight down so its bottom edge lands exactly on the nearest dotted guide line below it; an object with no guide below it does not move.", gi_snap_bottom_below, tf_snap_bottom_below)


# ---------------------------------------------------------------- 3
def gi_snap_left_right(rng):
    h, w = _size(rng, 14, 28); g = blank(h, w)
    cols = sorted(rng.sample(range(1, max(2, w // 2)), rng.randint(2, 3)))
    if cols[-1] + 4 >= w: return None
    _draw_vguides(g, cols)
    rh, rw = rng.randint(1, 4), rng.randint(1, 3)
    c0 = rng.randint(cols[-1] + 2, w - rw); r0 = rng.randint(0, h - rh)
    if any(g[r0 + r][c0 + c] != 0 for r, c in _rect(rh, rw)): return None
    col = rng.choice(COLOURS)
    for r, c in _rect(rh, rw): g[r0 + r][c0 + c] = col
    return g
def tf_snap_left_right(g):
    out = copy(g); cols = _cols_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o); cands = [c for c in cols if c < c0]
        if not cands: continue
        tgt = max(cands); dc = tgt - c0
        if dc: _move(out, o, _col(g, o), 0, dc)
    return out
rule("snap_left_edge_to_guide_right", "Every object moves straight left so its left edge lands exactly on the nearest dotted vertical guide to its left; an object with no guide to its left does not move.", gi_snap_left_right, tf_snap_left_right)


# ---------------------------------------------------------------- 4
def gi_snap_right_left(rng):
    h, w = _size(rng, 14, 28); g = blank(h, w)
    cols = sorted(rng.sample(range(w // 2 + 1, w - 1), rng.randint(2, 3)))
    if cols[0] < 4: return None
    _draw_vguides(g, cols)
    rh, rw = rng.randint(1, 4), rng.randint(1, 3)
    c0 = rng.randint(0, cols[0] - rw - 2); r0 = rng.randint(0, h - rh)
    if c0 < 0 or any(g[r0 + r][c0 + c] != 0 for r, c in _rect(rh, rw)): return None
    col = rng.choice(COLOURS)
    for r, c in _rect(rh, rw): g[r0 + r][c0 + c] = col
    return g
def tf_snap_right_left(g):
    out = copy(g); cols = _cols_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o); cands = [c for c in cols if c > c1]
        if not cands: continue
        tgt = min(cands); dc = tgt - c1
        if dc: _move(out, o, _col(g, o), 0, dc)
    return out
rule("snap_right_edge_to_guide_left", "Every object moves straight right so its right edge lands exactly on the nearest dotted vertical guide to its right; an object with no guide to its right does not move.", gi_snap_right_left, tf_snap_right_left)


# ---------------------------------------------------------------- 5
def gi_snap_top_either(rng):
    h, w = _size(rng, 14, 28); g = blank(h, w)
    rows = sorted(rng.sample(range(2, h - 2), rng.randint(2, 4)))
    _draw_hguides(g, rows)
    rh, rw = rng.randint(1, 3), rng.randint(1, 4)
    pos = _place(rng, g, _rect(rh, rw), rng.choice(COLOURS))
    if pos is None: return None
    return g
def tf_snap_top_either(g):
    out = copy(g); rows = _rows_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        tgt = min(rows, key=lambda r: (abs(r - r0), r))  # tie: the upper guide (smaller row) wins
        dr = tgt - r0
        if dr: _move(out, o, _col(g, o), dr, 0)
    return out
rule("snap_top_edge_to_nearest_guide", "Every object moves vertically so its top edge lands on whichever dotted guide line is closest to it; if two guides are equally close the upper one is used.", gi_snap_top_either, tf_snap_top_either)


# ---------------------------------------------------------------- 6
def gi_snap_left_either(rng):
    h, w = _size(rng, 14, 28); g = blank(h, w)
    cols = sorted(rng.sample(range(2, w - 2), rng.randint(2, 4)))
    _draw_vguides(g, cols)
    rh, rw = rng.randint(1, 4), rng.randint(1, 3)
    pos = _place(rng, g, _rect(rh, rw), rng.choice(COLOURS))
    if pos is None: return None
    return g
def tf_snap_left_either(g):
    out = copy(g); cols = _cols_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        tgt = min(cols, key=lambda c: (abs(c - c0), c))  # tie: the left guide (smaller column) wins
        dc = tgt - c0
        if dc: _move(out, o, _col(g, o), 0, dc)
    return out
rule("snap_left_edge_to_nearest_guide", "Every object moves horizontally so its left edge lands on whichever dotted vertical guide is closest to it; if two guides are equally close the left one is used.", gi_snap_left_either, tf_snap_left_either)


# ---------------------------------------------------------------- 7
def gi_cut_lower(rng):
    h, w = _size(rng, 14, 28); g = blank(h, w)
    row = rng.randint(4, h - 5)
    _draw_hguides(g, [row])
    rh, rw = rng.randint(3, 6), rng.randint(2, 5)
    r0 = rng.randint(max(0, row - rh + 2), row - 1); c0 = rng.randint(0, w - rw)
    if r0 + rh <= row + 1 or r0 >= row: return None
    if any(g[r0 + r][c0 + c] != 0 for r, c in _rect(rh, rw) if 0 <= r0 + r < h and r0 + r != row): return None
    col = rng.choice(COLOURS)
    for r, c in _rect(rh, rw):
        if 0 <= r0 + r < h: g[r0 + r][c0 + c] = col
    if r0 >= row or r0 + rh - 1 <= row: return None
    return g
def tf_cut_lower(g):
    out = copy(g); rows = _rows_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        guide = next((r for r in rows if r0 < r < r1), None)
        if guide is None: continue
        for r, c in o:
            if r > guide: out[r][c] = 0
    return out
rule("cut_object_at_guide_lower_deleted", "An object that straddles a dotted horizontal guide line is cut at that line and the part below the line is deleted.", gi_cut_lower, tf_cut_lower)


# ---------------------------------------------------------------- 8
def gi_cut_upper(rng):
    return gi_cut_lower(rng)
def tf_cut_upper(g):
    out = copy(g); rows = _rows_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        guide = next((r for r in rows if r0 < r < r1), None)
        if guide is None: continue
        for r, c in o:
            if r < guide: out[r][c] = 0
    return out
rule("cut_object_at_guide_upper_deleted", "An object that straddles a dotted horizontal guide line is cut at that line and the part above the line is deleted.", gi_cut_upper, tf_cut_upper)


# ---------------------------------------------------------------- 9
def gi_cut_right(rng):
    h, w = _size(rng, 14, 28); g = blank(h, w)
    col_ = rng.randint(4, w - 5)
    _draw_vguides(g, [col_])
    rh, rw = rng.randint(2, 5), rng.randint(3, 6)
    c0 = rng.randint(max(0, col_ - rw + 2), col_ - 1); r0 = rng.randint(0, h - rh)
    if c0 >= col_ or c0 + rw - 1 <= col_: return None
    if any(g[r0 + r][c0 + c] != 0 for r, c in _rect(rh, rw) if 0 <= c0 + c < w and c0 + c != col_): return None
    col = rng.choice(COLOURS)
    for r, c in _rect(rh, rw):
        if 0 <= c0 + c < w: g[r0 + r][c0 + c] = col
    return g
def tf_cut_right(g):
    out = copy(g); cols = _cols_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        guide = next((c for c in cols if c0 < c < c1), None)
        if guide is None: continue
        for r, c in o:
            if c > guide: out[r][c] = 0
    return out
rule("cut_object_at_guide_right_deleted", "An object that straddles a dotted vertical guide line is cut at that line and the part to the right of the line is deleted.", gi_cut_right, tf_cut_right)


# ---------------------------------------------------------------- 10
def gi_cut_left(rng):
    return gi_cut_right(rng)
def tf_cut_left(g):
    out = copy(g); cols = _cols_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        guide = next((c for c in cols if c0 < c < c1), None)
        if guide is None: continue
        for r, c in o:
            if c < guide: out[r][c] = 0
    return out
rule("cut_object_at_guide_left_deleted", "An object that straddles a dotted vertical guide line is cut at that line and the part to the left of the line is deleted.", gi_cut_left, tf_cut_left)


# ---------------------------------------------------------------- 11
def gi_stretch_h(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    rows = sorted(rng.sample(range(2, h - 2), 2))
    if rows[1] - rows[0] < 4: return None
    _draw_hguides(g, rows)
    rh, rw = 1, rng.randint(1, 4)
    r0 = rng.randint(rows[0] + 1, rows[1] - 1); c0 = rng.randint(0, w - rw)
    if any(g[r0][c0 + c] != 0 for c in range(rw)): return None
    col = rng.choice(COLOURS)
    for c in range(rw): g[r0][c0 + c] = col
    return g
def tf_stretch_h(g):
    out = copy(g); rows = _rows_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        below = [r for r in rows if r <= r0]; above_lo = [r for r in rows if r >= r1]
        if not below or not above_lo: continue
        top, bot = max(below), min(above_lo)
        col = _col(g, o)
        for r in range(top, bot + 1):
            for c in range(c0, c1 + 1): out[r][c] = col
    return out
rule("stretch_object_between_guides", "An object lying between two horizontal dotted guide lines is stretched vertically to fill the whole gap between the two lines, keeping its left-right extent.", gi_stretch_h, tf_stretch_h)


# ---------------------------------------------------------------- 12
def gi_stretch_v(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    cols = sorted(rng.sample(range(2, w - 2), 2))
    if cols[1] - cols[0] < 4: return None
    _draw_vguides(g, cols)
    rh, rw = rng.randint(1, 4), 1
    c0 = rng.randint(cols[0] + 1, cols[1] - 1); r0 = rng.randint(0, h - rh)
    if any(g[r0 + r][c0] != 0 for r in range(rh)): return None
    col = rng.choice(COLOURS)
    for r in range(rh): g[r0 + r][c0] = col
    return g
def tf_stretch_v(g):
    out = copy(g); cols = _cols_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        left = [c for c in cols if c <= c0]; right = [c for c in cols if c >= c1]
        if not left or not right: continue
        lft, rgt = max(left), min(right)
        col = _col(g, o)
        for c in range(lft, rgt + 1):
            for r in range(r0, r1 + 1): out[r][c] = col
    return out
rule("stretch_object_between_vertical_guides", "An object lying between two vertical dotted guide lines is stretched horizontally to fill the whole gap between the two lines, keeping its top-bottom extent.", gi_stretch_v, tf_stretch_v)


# ---------------------------------------------------------------- 13
def gi_centre_h(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    rows = sorted(rng.sample(range(2, h - 2), 2))
    if rows[1] - rows[0] < 5: return None
    _draw_hguides(g, rows)
    rh, rw = rng.randint(1, 2), rng.randint(1, 4)
    span = rows[1] - rows[0] - 1
    if rh >= span: return None
    r0 = rng.randint(rows[0] + 1, rows[1] - rh); c0 = rng.randint(0, w - rw)
    if any(g[r0 + r][c0 + c] != 0 for r, c in _rect(rh, rw)): return None
    col = rng.choice(COLOURS)
    for r, c in _rect(rh, rw): g[r0 + r][c0 + c] = col
    return g
def tf_centre_h(g):
    out = copy(g); rows = _rows_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        below = [r for r in rows if r < r0]; above_lo = [r for r in rows if r > r1]
        if not below or not above_lo: continue
        top, bot = max(below), min(above_lo)
        mid = (top + bot) // 2; oh = r1 - r0
        newr0 = mid - oh // 2
        dr = newr0 - r0
        if dr: _move(out, o, _col(g, o), dr, 0)
    return out
rule("object_centred_between_guides", "An object lying between two horizontal dotted guide lines moves vertically so it is centred in the gap between them, rounding up when the gap cannot be split evenly.", gi_centre_h, tf_centre_h)


# ---------------------------------------------------------------- 14
def gi_centre_v(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    cols = sorted(rng.sample(range(2, w - 2), 2))
    if cols[1] - cols[0] < 5: return None
    _draw_vguides(g, cols)
    rh, rw = rng.randint(1, 4), rng.randint(1, 2)
    span = cols[1] - cols[0] - 1
    if rw >= span: return None
    c0 = rng.randint(cols[0] + 1, cols[1] - rw); r0 = rng.randint(0, h - rh)
    if any(g[r0 + r][c0 + c] != 0 for r, c in _rect(rh, rw)): return None
    col = rng.choice(COLOURS)
    for r, c in _rect(rh, rw): g[r0 + r][c0 + c] = col
    return g
def tf_centre_v(g):
    out = copy(g); cols = _cols_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        left = [c for c in cols if c < c0]; right = [c for c in cols if c > c1]
        if not left or not right: continue
        lft, rgt = max(left), min(right)
        mid = (lft + rgt) // 2; ow = c1 - c0
        newc0 = mid - ow // 2
        dc = newc0 - c0
        if dc: _move(out, o, _col(g, o), 0, dc)
    return out
rule("object_centred_between_vertical_guides", "An object lying between two vertical dotted guide lines moves horizontally so it is centred in the gap between them, rounding up when the gap cannot be split evenly.", gi_centre_v, tf_centre_v)


# ---------------------------------------------------------------- 15
def _guide_rows_any_colour(g, min_frac=0.33):
    """Rows that are dotted guide lines (any colour): at least min_frac of the width non-background,
    distinguishing a guide line from a small object sitting on an ordinary row."""
    w = len(g[0]); out = {}
    for r, row in enumerate(g):
        nz = [v for v in row if v != 0]
        if len(nz) >= max(2, int(w * min_frac)):
            out[r] = max(set(nz), key=nz.count)
    return out


def gi_colour_match(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    rows = sorted(rng.sample(range(3, h - 3), 2))
    if rows[1] - rows[0] < 4: return None
    gcol_a, gcol_b = colours(rng, 2)
    _draw_hguides(g, [rows[0]], gcol_a); _draw_hguides(g, [rows[1]], gcol_b)
    other = rng.choice([c for c in COLOURS if c not in (gcol_a, gcol_b)])
    plan = [gcol_a, gcol_b, other]; rng.shuffle(plan)
    free_rows = [r for r in range(h) if r not in rows]
    placed = 0
    for col in plan:
        rw = rng.randint(1, 3); ok = False
        for r0 in rng.sample(free_rows, len(free_rows)):
            for _ in range(10):
                c0 = rng.randint(0, w - rw)
                if all(g[r0][c0 + c] == 0 for c in range(rw)):
                    for c in range(rw): g[r0][c0 + c] = col
                    placed += 1; ok = True; break
            if ok: break
    if placed < 3: return None
    return g
def tf_colour_match(g):
    out = copy(g); guide_rows = _guide_rows_any_colour(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o); col = _col(g, o)
        match_rows = [r for r, c_ in guide_rows.items() if c_ == col]
        if not match_rows: continue
        tgt = min(match_rows, key=lambda r: abs(r - r0))
        dr = tgt - r0
        if dr: _move(out, o, col, dr, 0)
    return out
rule("guide_colour_matched_object_snaps", "Each dotted horizontal guide line has its own colour; an object moves vertically to sit on the closest guide line sharing its colour, and does not move if no guide shares its colour.", gi_colour_match, tf_colour_match)


# ---------------------------------------------------------------- 16
def gi_solid_touch(rng):
    h, w = _size(rng, 14, 26); g = blank(h, w)
    row = rng.randint(3, h - 4)
    _draw_hguides(g, [row])
    placed = 0
    for i in range(rng.randint(2, 3)):
        rw = rng.randint(1, 3); on_guide = i < 2
        for _ in range(30):
            r0 = row if on_guide else rng.choice([r for r in range(h) if r != row])
            c0 = rng.randint(0, w - rw)
            if all(g[r0][c0 + c] == 0 for c in range(rw)):
                for c in range(rw): g[r0][c0 + c] = rng.choice(COLOURS)
                placed += 1; break
    if placed < 2: return None
    return g
def tf_solid_touch(g):
    out = copy(g); rows = _rows_with(g)
    for r in rows:
        touched_cols = set()
        for o in _objs(g):
            r0, c0, r1, c1 = bbox(o)
            if r0 <= r <= r1: touched_cols.update(range(c0, c1 + 1))
        for c in touched_cols: out[r][c] = G
    return out
rule("guide_solid_where_touched", "Wherever an object touches a dotted horizontal guide line, the gaps in the line are filled in for those columns so the line becomes solid there.", gi_solid_touch, tf_solid_touch)


# ---------------------------------------------------------------- 17
def gi_busiest(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    n = rng.randint(2, 3)
    rows = sorted(rng.sample(range(2, h - 2), n))
    if any(rows[i + 1] - rows[i] < 3 for i in range(len(rows) - 1)): return None
    _draw_hguides(g, rows)
    winner = rng.choice(rows)
    k1 = rng.randint(2, 3)
    for _ in range(k1):
        pos = _place(rng, g, _rect(1, rng.randint(1, 2)), rng.choice(COLOURS))
    for r in rows:
        if r != winner and rng.random() < 0.6:
            _place(rng, g, _rect(1, 1), rng.choice(COLOURS))
    objs = _objs(g)
    cnt = {r: 0 for r in rows}
    for o in objs:
        r0, c0, r1, c1 = bbox(o)
        for r in rows:
            if r0 <= r <= r1: cnt[r] += 1
    vals = sorted(cnt.values(), reverse=True)
    if len(vals) < 2 or vals[0] == vals[1] or vals[0] == 0: return None
    return g
def tf_busiest(g):
    out = copy(g); rows = _rows_with(g)
    cnt = {r: 0 for r in rows}
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        for r in rows:
            if r0 <= r <= r1: cnt[r] += 1
    best = max(rows, key=lambda r: (cnt[r], -r))
    for c in range(len(g[0])):
        if out[best][c] != 0: out[best][c] = 9
    return out
rule("busiest_guide_recoloured", "The dotted guide line crossed by the most objects is recoloured to colour 9; ties go to the topmost of the tied lines.", gi_busiest, tf_busiest)


# ---------------------------------------------------------------- 18
def gi_slide_left(rng):
    h, w = _size(rng, 14, 28); g = blank(h, w)
    row = rng.randint(2, h - 3)
    _draw_hguides(g, [row])
    k = rng.randint(2, 3); placed = 0
    for _ in range(k):
        rw = rng.randint(1, 3); c0 = rng.randint(2, w - rw - 1)
        if any(g[row][c0 + c] != 0 for c in range(rw)): continue
        col = rng.choice(COLOURS)
        for c in range(rw): g[row][c0 + c] = col
        placed += 1
    if placed < 2: return None
    return g
def tf_slide_left(g):
    out = copy(g); rows = _rows_with(g); w = len(g[0])
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        if r0 not in rows or r0 != r1: continue
        for r, c in o: out[r][c] = 0
    col_cursor = 0
    for o in sorted(_objs(g), key=lambda o: bbox(o)[1]):
        r0, c0, r1, c1 = bbox(o)
        if r0 not in rows or r0 != r1: continue
        ow = c1 - c0
        for i in range(ow + 1): out[r0][col_cursor + i] = _col(g, o)
        col_cursor += ow + 2
    return out
rule("objects_on_guide_slide_left", "Every flat object sitting on a dotted horizontal guide line slides left, packed one empty column apart starting from the left edge, in their original left-to-right order.", gi_slide_left, tf_slide_left)


# ---------------------------------------------------------------- 19
def gi_evenly_h(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    row = rng.randint(2, h - 3)
    _draw_hguides(g, [row])
    k = rng.randint(3, 4); used = set()
    for _ in range(k):
        for _ in range(40):
            c0 = rng.randint(1, w - 2)
            if c0 not in used and c0 - 1 not in used and c0 + 1 not in used:
                used.add(c0); g[row][c0] = rng.choice(COLOURS); break
    if len(used) < 3: return None
    return g
def tf_evenly_h(g):
    out = copy(g); rows = _rows_with(g); w = len(g[0])
    for row in rows:
        objs = [o for o in _objs(g) if all(r == row for r, c in o)]
        if len(objs) < 2: continue
        objs = sorted(objs, key=lambda o: bbox(o)[1])
        for o in objs:
            for r, c in o: out[r][c] = 0
        lo = min(bbox(o)[1] for o in objs); hi = max(bbox(o)[3] for o in objs)
        step = (hi - lo) / (len(objs) - 1) if len(objs) > 1 else 0
        for i, o in enumerate(objs):
            newc = lo + round(i * step)
            out[row][newc] = _col(g, o)
    return out
rule("objects_evenly_spaced_along_guide", "The single-cell objects sitting on a dotted horizontal guide line are redistributed to be evenly spaced between the leftmost and rightmost of them, keeping their left-to-right order.", gi_evenly_h, tf_evenly_h)


# ---------------------------------------------------------------- 20
def gi_off_deleted(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    n = rng.randint(1, 2)
    rows = sorted(rng.sample(range(2, h - 2), n))
    _draw_hguides(g, rows)
    on_k = rng.randint(1, 2); off_k = rng.randint(1, 2)
    for _ in range(on_k):
        row = rng.choice(rows); rw = rng.randint(1, 3); c0 = rng.randint(0, w - rw)
        if any(g[row][c0 + c] != 0 for c in range(rw)): continue
        for c in range(rw): g[row][c0 + c] = rng.choice(COLOURS)
    placed_off = 0
    for _ in range(off_k):
        pos = _place(rng, g, _rect(rng.randint(1, 2), rng.randint(1, 3)), rng.choice(COLOURS))
        if pos: placed_off += 1
    if placed_off < 1: return None
    objs = _objs(g)
    if len(objs) < 2: return None
    return g
def tf_off_deleted(g):
    out = copy(g); rows = _rows_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        if not any(r0 <= r <= r1 for r in rows):
            for r, c in o: out[r][c] = 0
    return out
rule("objects_off_guide_deleted", "Any object that does not touch a dotted horizontal guide line is deleted; objects touching a guide line are left in place.", gi_off_deleted, tf_off_deleted)


# ---------------------------------------------------------------- 21
def gi_off_deleted_v(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    n = rng.randint(1, 2)
    cols = sorted(rng.sample(range(2, w - 2), n))
    _draw_vguides(g, cols)
    on_k = rng.randint(1, 2); off_k = rng.randint(1, 2)
    for _ in range(on_k):
        c0 = rng.choice(cols); rh = rng.randint(1, 3); r0 = rng.randint(0, h - rh)
        if any(g[r0 + r][c0] != 0 for r in range(rh)): continue
        for r in range(rh): g[r0 + r][c0] = rng.choice(COLOURS)
    placed_off = 0
    for _ in range(off_k):
        pos = _place(rng, g, _rect(rng.randint(1, 3), rng.randint(1, 2)), rng.choice(COLOURS))
        if pos: placed_off += 1
    if placed_off < 1: return None
    objs = _objs(g)
    if len(objs) < 2: return None
    return g
def tf_off_deleted_v(g):
    out = copy(g); cols = _cols_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        if not any(c0 <= c <= c1 for c in cols):
            for r, c in o: out[r][c] = 0
    return out
rule("objects_off_vertical_guide_deleted", "Any object that does not touch a dotted vertical guide line is deleted; objects touching a guide line are left in place.", gi_off_deleted_v, tf_off_deleted_v)


# ---------------------------------------------------------------- 22
def gi_nearest_solid_h(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    rows = sorted(rng.sample(range(2, h - 2), rng.randint(2, 3)))
    if any(rows[i + 1] - rows[i] < 3 for i in range(len(rows) - 1)): return None
    _draw_hguides(g, rows)
    pos = _place(rng, g, _rect(rng.randint(1, 2), rng.randint(1, 3)), rng.choice(COLOURS))
    if pos is None: return None
    return g
def tf_nearest_solid_h(g):
    out = copy(g); rows = _rows_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        tgt = min(rows, key=lambda r: (min(abs(r - r0), abs(r - r1)), r))
        col = _col(g, o)
        for c in range(len(g[0])):
            if out[tgt][c] != 0: out[tgt][c] = col
    return out
rule("nearest_guide_drawn_solid_in_object_colour", "For every object, whichever dotted horizontal guide line is closest to it is redrawn with its gaps filled in, in that object's colour; a tie favours the upper line.", gi_nearest_solid_h, tf_nearest_solid_h)


# ---------------------------------------------------------------- 23
def gi_nearest_solid_v(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    cols = sorted(rng.sample(range(2, w - 2), rng.randint(2, 3)))
    if any(cols[i + 1] - cols[i] < 3 for i in range(len(cols) - 1)): return None
    _draw_vguides(g, cols)
    pos = _place(rng, g, _rect(rng.randint(1, 3), rng.randint(1, 2)), rng.choice(COLOURS))
    if pos is None: return None
    return g
def tf_nearest_solid_v(g):
    out = copy(g); cols = _cols_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        tgt = min(cols, key=lambda c: (min(abs(c - c0), abs(c - c1)), c))
        col = _col(g, o)
        for r in range(len(g)):
            if out[r][tgt] != 0: out[r][tgt] = col
    return out
rule("nearest_vertical_guide_drawn_solid_in_object_colour", "For every object, whichever dotted vertical guide line is closest to it is redrawn with its gaps filled in, in that object's colour; a tie favours the left line.", gi_nearest_solid_v, tf_nearest_solid_v)


# ---------------------------------------------------------------- 24
def gi_reflect_h(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    row = rng.randint(h // 3, 2 * h // 3)
    _draw_hguides(g, [row])
    rh, rw = rng.randint(1, 3), rng.randint(1, 3)
    span = min(row, h - 1 - row) - 1
    if span < rh: return None
    r0 = rng.randint(max(0, row - span), row - rh); c0 = rng.randint(0, w - rw)
    if any(g[r0 + r][c0 + c] != 0 for r, c in _rect(rh, rw)): return None
    col = rng.choice(COLOURS)
    for r, c in _rect(rh, rw): g[r0 + r][c0 + c] = col
    return g
def tf_reflect_h(g):
    out = copy(g); rows = _rows_with(g); h = len(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        tgt = min(rows, key=lambda r: min(abs(r - r0), abs(r - r1)))
        col = _col(g, o)
        for r, c in o: out[r][c] = 0
        for r, c in o:
            nr = 2 * tgt - r
            if 0 <= nr < h: out[nr][c] = col
    return out
rule("object_reflected_across_nearest_guide", "Every object is mirrored vertically across whichever dotted horizontal guide line is closest to it, and removed from its original spot; distance is measured from the object's nearer edge.", gi_reflect_h, tf_reflect_h)


# ---------------------------------------------------------------- 25
def gi_reflect_v(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    col_ = rng.randint(w // 3, 2 * w // 3)
    _draw_vguides(g, [col_])
    rh, rw = rng.randint(1, 3), rng.randint(1, 3)
    span = min(col_, w - 1 - col_) - 1
    if span < rw: return None
    c0 = rng.randint(max(0, col_ - span), col_ - rw); r0 = rng.randint(0, h - rh)
    if any(g[r0 + r][c0 + c] != 0 for r, c in _rect(rh, rw)): return None
    col = rng.choice(COLOURS)
    for r, c in _rect(rh, rw): g[r0 + r][c0 + c] = col
    return g
def tf_reflect_v(g):
    out = copy(g); cols = _cols_with(g); w = len(g[0])
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        tgt = min(cols, key=lambda c: min(abs(c - c0), abs(c - c1)))
        col = _col(g, o)
        for r, c in o: out[r][c] = 0
        for r, c in o:
            nc = 2 * tgt - c
            if 0 <= nc < w: out[r][nc] = col
    return out
rule("object_reflected_across_nearest_vertical_guide", "Every object is mirrored horizontally across whichever dotted vertical guide line is closest to it, and removed from its original spot; distance is measured from the object's nearer edge.", gi_reflect_v, tf_reflect_v)


# ---------------------------------------------------------------- 26
def gi_dup_h(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    rows = sorted(rng.sample(range(2, h - 2), rng.randint(2, 3)))
    _draw_hguides(g, rows)
    rh, rw = 1, rng.randint(1, 3)
    r0 = rng.randint(0, h - rh); c0 = rng.randint(0, w - rw)
    if any(g[r0][c0 + c] != 0 for c in range(rw)): return None
    col = rng.choice(COLOURS)
    for c in range(rw): g[r0][c0 + c] = col
    if r0 in rows: return None
    return g
def tf_dup_h(g):
    out = copy(g); rows = _rows_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o); col = _col(g, o); oh = r1 - r0
        for r, c in o: out[r][c] = 0
        for guide in rows:
            for r, c in o:
                nr = guide + (r - r0)
                if 0 <= nr < len(g): out[nr][c] = col
    return out
rule("object_duplicated_at_each_guide_crossing", "A single object is removed and a copy of it is stamped at the same columns on every dotted horizontal guide line, top edge aligned to the line.", gi_dup_h, tf_dup_h)


# ---------------------------------------------------------------- 27
def gi_dup_v(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    cols = sorted(rng.sample(range(2, w - 2), rng.randint(2, 3)))
    _draw_vguides(g, cols)
    rh, rw = rng.randint(1, 3), 1
    r0 = rng.randint(0, h - rh); c0 = rng.randint(0, w - rw)
    if any(g[r0 + r][c0] != 0 for r in range(rh)): return None
    col = rng.choice(COLOURS)
    for r in range(rh): g[r0 + r][c0] = col
    if c0 in cols: return None
    return g
def tf_dup_v(g):
    out = copy(g); cols = _cols_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o); col = _col(g, o)
        for r, c in o: out[r][c] = 0
        for guide in cols:
            for r, c in o:
                nc = guide + (c - c0)
                if 0 <= nc < len(g[0]): out[r][nc] = col
    return out
rule("object_duplicated_at_each_vertical_guide_crossing", "A single object is removed and a copy of it is stamped at the same rows on every dotted vertical guide line, left edge aligned to the line.", gi_dup_v, tf_dup_v)


# ---------------------------------------------------------------- 28
def gi_gap_count_h(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    rows = sorted(rng.sample(range(2, h - 2), 2))
    gap = rows[1] - rows[0] - 1
    if not (1 <= gap <= 9) or gap < 2: return None
    _draw_hguides(g, rows)
    rh, rw = 1, rng.randint(1, 4)
    r0 = rng.randint(rows[0] + 1, rows[1] - 1); c0 = rng.randint(0, w - rw)
    if any(g[r0][c0 + c] != 0 for c in range(rw)): return None
    for c in range(rw): g[r0][c0 + c] = rng.choice(COLOURS)
    return g
def tf_gap_count_h(g):
    out = copy(g); rows = _rows_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        below = [r for r in rows if r < r0]; above_lo = [r for r in rows if r > r1]
        if not below or not above_lo: continue
        top, bot = max(below), min(above_lo); gap = bot - top - 1
        for r, c in o: out[r][c] = gap
    return out
rule("gap_width_recolours_object", "An object lying between two horizontal dotted guide lines is recoloured to the colour whose number equals the count of empty rows strictly between the two lines.", gi_gap_count_h, tf_gap_count_h, digits=True)


# ---------------------------------------------------------------- 29
def gi_gap_count_v(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    cols = sorted(rng.sample(range(2, w - 2), 2))
    gap = cols[1] - cols[0] - 1
    if not (1 <= gap <= 9) or gap < 2: return None
    _draw_vguides(g, cols)
    rh, rw = rng.randint(1, 4), 1
    c0 = rng.randint(cols[0] + 1, cols[1] - 1); r0 = rng.randint(0, h - rh)
    if any(g[r0 + r][c0] != 0 for r in range(rh)): return None
    for r in range(rh): g[r0 + r][c0] = rng.choice(COLOURS)
    return g
def tf_gap_count_v(g):
    out = copy(g); cols = _cols_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        left = [c for c in cols if c < c0]; right = [c for c in cols if c > c1]
        if not left or not right: continue
        lft, rgt = max(left), min(right); gap = rgt - lft - 1
        for r, c in o: out[r][c] = gap
    return out
rule("vertical_gap_width_recolours_object", "An object lying between two vertical dotted guide lines is recoloured to the colour whose number equals the count of empty columns strictly between the two lines.", gi_gap_count_v, tf_gap_count_v, digits=True)


# ---------------------------------------------------------------- 30
def gi_band_index_h(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    n = rng.randint(2, 3)
    rows = sorted(rng.sample(range(3, h - 3), n))
    if any(rows[i + 1] - rows[i] < 3 for i in range(len(rows) - 1)): return None
    _draw_hguides(g, rows)
    bands = [0] + rows + [h - 1]
    placed = 0
    for i in range(len(bands) - 1):
        lo, hi_ = bands[i] + (1 if i > 0 else 0), bands[i + 1] - (1 if i < len(bands) - 2 else 0)
        if hi_ - lo < 0: continue
        rw = rng.randint(1, 3); c0 = rng.randint(0, w - rw); r0 = rng.randint(lo, hi_)
        if any(g[r0][c0 + c] != 0 for c in range(rw)): continue
        for c in range(rw): g[r0][c0 + c] = rng.choice(COLOURS)
        placed += 1
    if placed < 2: return None
    return g
def tf_band_index_h(g):
    out = copy(g); rows = _rows_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        band = sum(1 for r in rows if r < r0) + 1
        band = min(band, 9)
        for r, c in o: out[r][c] = band
    return out
rule("band_index_recolours_object", "The grid is divided into horizontal bands by the dotted guide lines; every object is recoloured to the colour whose number equals its band's position counting from the top, starting at 1.", gi_band_index_h, tf_band_index_h, digits=True)


# ---------------------------------------------------------------- 31
def gi_band_index_v(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    n = rng.randint(2, 3)
    cols = sorted(rng.sample(range(3, w - 3), n))
    if any(cols[i + 1] - cols[i] < 3 for i in range(len(cols) - 1)): return None
    _draw_vguides(g, cols)
    bands = [0] + cols + [w - 1]
    placed = 0
    for i in range(len(bands) - 1):
        lo, hi_ = bands[i] + (1 if i > 0 else 0), bands[i + 1] - (1 if i < len(bands) - 2 else 0)
        if hi_ - lo < 0: continue
        rh = rng.randint(1, 3); r0 = rng.randint(0, h - rh); c0 = rng.randint(lo, hi_)
        if any(g[r0 + r][c0] != 0 for r in range(rh)): continue
        for r in range(rh): g[r0 + r][c0] = rng.choice(COLOURS)
        placed += 1
    if placed < 2: return None
    return g
def tf_band_index_v(g):
    out = copy(g); cols = _cols_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        band = sum(1 for c in cols if c < c0) + 1
        band = min(band, 9)
        for r, c in o: out[r][c] = band
    return out
rule("vertical_band_index_recolours_object", "The grid is divided into vertical bands by the dotted guide lines; every object is recoloured to the colour whose number equals its band's position counting from the left, starting at 1.", gi_band_index_v, tf_band_index_v, digits=True)


# ---------------------------------------------------------------- 32
def gi_cross_count_h(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    n = rng.randint(2, 4)
    rows = sorted(rng.sample(range(2, h - 2), n))
    if any(rows[i + 1] - rows[i] < 2 for i in range(len(rows) - 1)): return None
    _draw_hguides(g, rows)
    rh = rows[-1] - rows[0] + 1
    if rh > h: return None
    rw = rng.randint(1, 3); c0 = rng.randint(0, w - rw)
    if any(g[rows[0] + r][c0 + c] != 0 for r in range(rh) for c in range(rw)): return None
    col = rng.choice(COLOURS)
    for r in range(rh):
        for c in range(rw): g[rows[0] + r][c0 + c] = col
    return g
def tf_cross_count_h(g):
    out = copy(g); rows = _rows_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        n = sum(1 for r in rows if r0 <= r <= r1)
        if n == 0: continue
        n = min(n, 9)
        for r, c in o: out[r][c] = n
    return out
rule("count_guides_crossed_recolours_object", "An object spanning several dotted horizontal guide lines is recoloured to the colour whose number equals how many of those lines it crosses.", gi_cross_count_h, tf_cross_count_h, digits=True)


# ---------------------------------------------------------------- 33
def gi_cross_count_v(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    n = rng.randint(2, 4)
    cols = sorted(rng.sample(range(2, w - 2), n))
    if any(cols[i + 1] - cols[i] < 2 for i in range(len(cols) - 1)): return None
    _draw_vguides(g, cols)
    rw = cols[-1] - cols[0] + 1
    if rw > w: return None
    rh = rng.randint(1, 3); r0 = rng.randint(0, h - rh)
    if any(g[r0 + r][cols[0] + c] != 0 for r in range(rh) for c in range(rw)): return None
    col = rng.choice(COLOURS)
    for r in range(rh):
        for c in range(rw): g[r0 + r][cols[0] + c] = col
    return g
def tf_cross_count_v(g):
    out = copy(g); cols = _cols_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        n = sum(1 for c in cols if c0 <= c <= c1)
        if n == 0: continue
        n = min(n, 9)
        for r, c in o: out[r][c] = n
    return out
rule("vertical_count_guides_crossed_recolours_object", "An object spanning several dotted vertical guide lines is recoloured to the colour whose number equals how many of those lines it crosses.", gi_cross_count_v, tf_cross_count_v, digits=True)


# ---------------------------------------------------------------- 34
def gi_match_or_delete(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    rows = sorted(rng.sample(range(3, h - 3), 2))
    if rows[1] - rows[0] < 4: return None
    gcol_a, gcol_b = colours(rng, 2)
    _draw_hguides(g, [rows[0]], gcol_a); _draw_hguides(g, [rows[1]], gcol_b)
    other = rng.choice([c for c in COLOURS if c not in (gcol_a, gcol_b)])
    plan = [gcol_a, other]; rng.shuffle(plan)
    free_rows = [r for r in range(h) if r not in rows]
    placed = 0
    for col in plan:
        rw = rng.randint(1, 3); ok = False
        for r0 in rng.sample(free_rows, len(free_rows)):
            for _ in range(10):
                c0 = rng.randint(0, w - rw)
                if all(g[r0][c0 + c] == 0 for c in range(rw)):
                    for c in range(rw): g[r0][c0 + c] = col
                    placed += 1; ok = True; break
            if ok: break
    if placed < 2: return None
    return g
def tf_match_or_delete(g):
    out = copy(g); guide_rows = _guide_rows_any_colour(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o); col = _col(g, o)
        match_rows = [r for r, c_ in guide_rows.items() if c_ == col]
        if not match_rows:
            for r, c in o: out[r][c] = 0
            continue
        tgt = min(match_rows, key=lambda r: abs(r - r0))
        dr = tgt - r0
        if dr: _move(out, o, col, dr, 0)
    return out
rule("guide_matching_colour_moves_else_deleted", "Each dotted horizontal guide line has its own colour; an object whose colour matches a guide line moves to sit on the closest matching line, and an object matching no line is deleted.", gi_match_or_delete, tf_match_or_delete)


# ---------------------------------------------------------------- 35
def gi_intersection(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    row = rng.randint(3, h - 4); col_ = rng.randint(3, w - 4)
    _draw_hguides(g, [row]); _draw_vguides(g, [col_])
    rh, rw = rng.randint(1, 2), rng.randint(1, 2)
    quad = rng.choice([(0, row - rh, 0, col_ - rw), (0, row - rh, col_ + 1, w - rw),
                        (row + 1, h - rh, 0, col_ - rw), (row + 1, h - rh, col_ + 1, w - rw)])
    r_lo, r_hi, c_lo, c_hi = quad
    if r_hi < r_lo or c_hi < c_lo: return None
    r0 = rng.randint(r_lo, r_hi); c0 = rng.randint(c_lo, c_hi)
    if any(not (0 <= r0 + r < h and 0 <= c0 + c < w) or g[r0 + r][c0 + c] != 0 for r, c in _rect(rh, rw)): return None
    col = rng.choice(COLOURS)
    for r, c in _rect(rh, rw): g[r0 + r][c0 + c] = col
    return g
def tf_intersection(g):
    out = copy(g); rows = _rows_with(g); cols = _cols_with(g)
    if not rows or not cols: return None
    row, col_ = rows[0], cols[0]
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o); col = _col(g, o)
        nr0 = row + 1 if r1 < row else row - (r1 - r0)
        nc0 = col_ + 1 if c1 < col_ else col_ - (c1 - c0)
        dr, dc = nr0 - r0, nc0 - c0
        if dr or dc: _move(out, o, col, dr, dc)
    return out
rule("object_moves_to_guide_intersection", "With one horizontal and one vertical dotted guide line, every object moves diagonally so its corner nearest the intersection touches that intersection.", gi_intersection, tf_intersection)


# ---------------------------------------------------------------- 36
def gi_mark_intersections(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    n_h = rng.randint(1, 2); n_v = rng.randint(1, 2)
    rows = sorted(rng.sample(range(2, h - 2), n_h))
    cols = sorted(rng.sample(range(2, w - 2), n_v))
    _draw_hguides(g, rows); _draw_vguides(g, cols)
    k = rng.randint(1, 2)
    for _ in range(k):
        _place(rng, g, _rect(1, rng.randint(1, 2)), rng.choice(COLOURS))
    return g
def tf_mark_intersections(g):
    out = copy(g); rows = _rows_with(g); cols = _cols_with(g)
    for r in rows:
        for c in cols: out[r][c] = 9
    return out
rule("mark_guide_intersections", "Every point where a dotted horizontal guide line crosses a dotted vertical guide line is marked with colour 9; objects are left untouched.", gi_mark_intersections, tf_mark_intersections)


# ---------------------------------------------------------------- 37
def gi_slide_top_v(rng):
    h, w = _size(rng, 14, 28); g = blank(h, w)
    col_ = rng.randint(2, w - 3)
    _draw_vguides(g, [col_])
    k = rng.randint(2, 3); placed = 0
    for _ in range(k):
        rh = rng.randint(1, 3); r0 = rng.randint(2, h - rh - 1)
        if any(g[r0 + r][col_] != 0 for r in range(rh)): continue
        col = rng.choice(COLOURS)
        for r in range(rh): g[r0 + r][col_] = col
        placed += 1
    if placed < 2: return None
    return g
def tf_slide_top_v(g):
    out = copy(g); cols = _cols_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        if c0 not in cols or c0 != c1: continue
        for r, c in o: out[r][c] = 0
    row_cursor = 0
    for o in sorted(_objs(g), key=lambda o: bbox(o)[0]):
        r0, c0, r1, c1 = bbox(o)
        if c0 not in cols or c0 != c1: continue
        oh = r1 - r0
        for i in range(oh + 1): out[row_cursor + i][c0] = _col(g, o)
        row_cursor += oh + 2
    return out
rule("objects_on_vertical_guide_slide_up", "Every single-column object sitting on a dotted vertical guide line slides up, packed one empty row apart starting from the top edge, in their original top-to-bottom order.", gi_slide_top_v, tf_slide_top_v)


# ---------------------------------------------------------------- 38
def gi_evenly_v(rng):
    h, w = _size(rng, 16, 28); g = blank(h, w)
    col_ = rng.randint(2, w - 3)
    _draw_vguides(g, [col_])
    k = rng.randint(3, 4); used = set()
    for _ in range(k):
        for _ in range(40):
            r0 = rng.randint(1, h - 2)
            if r0 not in used and r0 - 1 not in used and r0 + 1 not in used:
                used.add(r0); g[r0][col_] = rng.choice(COLOURS); break
    if len(used) < 3: return None
    return g
def tf_evenly_v(g):
    out = copy(g); cols = _cols_with(g)
    for c in cols:
        objs = [o for o in _objs(g) if all(c2 == c for r, c2 in o)]
        if len(objs) < 2: continue
        objs = sorted(objs, key=lambda o: bbox(o)[0])
        for o in objs:
            for r, cc in o: out[r][cc] = 0
        lo = min(bbox(o)[0] for o in objs); hi = max(bbox(o)[2] for o in objs)
        step = (hi - lo) / (len(objs) - 1) if len(objs) > 1 else 0
        for i, o in enumerate(objs):
            newr = lo + round(i * step)
            out[newr][c] = _col(g, o)
    return out
rule("objects_evenly_spaced_along_vertical_guide", "The single-cell objects sitting on a dotted vertical guide line are redistributed to be evenly spaced between the topmost and bottommost of them, keeping their top-to-bottom order.", gi_evenly_v, tf_evenly_v)


# ---------------------------------------------------------------- 39
def gi_split_colours(rng):
    h, w = _size(rng, 14, 28); g = blank(h, w)
    row = rng.randint(4, h - 5)
    _draw_hguides(g, [row])
    rh, rw = rng.randint(4, 7), rng.randint(2, 5)
    r0 = rng.randint(max(0, row - rh + 2), row - 1); c0 = rng.randint(0, w - rw)
    if r0 >= row or r0 + rh - 1 <= row + 1: return None
    if any(0 <= r0 + r < h and r0 + r != row and g[r0 + r][c0 + c] != 0 for r, c in _rect(rh, rw)): return None
    col1, col2 = colours(rng, 2)
    for r, c in _rect(rh, rw):
        if 0 <= r0 + r < h: g[r0 + r][c0 + c] = col1
    return g, row, r0, rh, c0, rw, col1, col2
def _gi_split_wrap(rng):
    res = gi_split_colours(rng)
    if res is None: return None
    g, row, r0, rh, c0, rw, col1, col2 = res
    return g
def tf_split_colours(g):
    out = copy(g); rows = _rows_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        guide = next((r for r in rows if r0 < r < r1), None)
        if guide is None: continue
        col = _col(g, o)
        other = 9 if col != 9 else 8
        for r, c in o:
            if r > guide: out[r][c] = other
    return out
rule("object_split_into_two_colours_at_guide", "An object that straddles a dotted horizontal guide line keeps its original colour above the line, and the part below the line is recoloured to 9 (or 8 if the object was already 9).", _gi_split_wrap, tf_split_colours)


# ---------------------------------------------------------------- 40
def gi_tie_bottom(rng):
    h, w = _size(rng, 14, 28); g = blank(h, w)
    rows = sorted(rng.sample(range(2, h - 2), rng.randint(2, 4)))
    _draw_hguides(g, rows)
    rh, rw = rng.randint(1, 3), rng.randint(1, 4)
    pos = _place(rng, g, _rect(rh, rw), rng.choice(COLOURS))
    if pos is None: return None
    return g
def tf_tie_bottom(g):
    out = copy(g); rows = _rows_with(g)
    for o in _objs(g):
        r0, c0, r1, c1 = bbox(o)
        tgt = min(rows, key=lambda r: (abs(r - r1), r))  # tie: the upper guide (smaller row) wins
        dr = tgt - r1
        if dr: _move(out, o, _col(g, o), dr, 0)
    return out
rule("snap_bottom_edge_to_nearest_guide", "Every object moves vertically so its bottom edge lands on whichever dotted guide line is closest to it; if two guides are equally close the upper one is used.", gi_tie_bottom, tf_tie_bottom)
