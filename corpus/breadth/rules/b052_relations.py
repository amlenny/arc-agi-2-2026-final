# b052_relations.py -- spatial relations to a grey reference object. One author, 40 rules.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

REF = 5


# ---------- shared helpers ----------
def _hw(rng, lo=8, hi=20, big_p=0.4):
    if rng.random() < big_p:
        return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _parts(g):
    obs = objects(g, 0)
    ref = next((o for o in obs if g[o[0][0]][o[0][1]] == REF), None)
    others = [o for o in obs if o is not ref]
    return ref, others


def _bbox_gap(b1, b2):
    r0, c0, r1, c1 = b1; R0, C0, R1, C1 = b2
    dr = max(0, max(r0 - R1, R0 - r1)); dc = max(0, max(c0 - C1, C0 - c1))
    return dr + dc


def _scene_ref(rng, k_lo=2, k_hi=5, n_lo=3, n_hi=8, big_p=0.4, margin=1, ref_lo=2, ref_hi=4):
    h, w = _hw(rng, big_p=big_p)
    g = blank(h, w)
    k = rng.randint(k_lo, k_hi)
    rh, rw = rng.randint(ref_lo, ref_hi), rng.randint(ref_lo, ref_hi)
    ref_cells = [(r, c) for r in range(rh) for c in range(rw)]
    shapes = [ref_cells] + [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    cols = [REF] + colours(rng, k, exclude=(0, REF))
    if place_shapes(rng, g, shapes, cols, margin=margin) is None:
        return None
    return g


def _free(g, r0, c0, r1, c1, margin=1):
    H, W = dims(g)
    for r in range(r0 - margin, r1 + 1 + margin):
        for c in range(c0 - margin, c1 + 1 + margin):
            if 0 <= r < H and 0 <= c < W and g[r][c] != 0:
                return False
    return True


def _occupy(g, r0, c0, r1, c1, col):
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            g[r][c] = col


def _place_rect(g, rng, rh, rw, colour, tries=60, margin=1):
    H, W = dims(g)
    if rh > H or rw > W:
        return None
    for _ in range(tries):
        r0 = rng.randint(0, H - rh); c0 = rng.randint(0, W - rw)
        r1, c1 = r0 + rh - 1, c0 + rw - 1
        if _free(g, r0, c0, r1, c1, margin):
            _occupy(g, r0, c0, r1, c1, colour)
            return (r0, c0, r1, c1)
    return None


def _place_axis_object(g, rng, ref, direction, gap_hi=4):
    r0, c0, r1, c1 = ref
    h, w = dims(g)
    acol = colours(rng, 1, exclude=(0, REF))[0]
    gap = rng.randint(1, gap_hi)
    if direction in ("up", "down"):
        aw = rng.randint(1, c1 - c0 + 1); ah = rng.randint(1, 3)
        ac0 = rng.randint(c0, c1 - aw + 1)
        if direction == "up":
            ar1 = r0 - 1 - gap; ar0 = ar1 - ah + 1
            if ar0 < 0: return None
        else:
            ar0 = r1 + 1 + gap; ar1 = ar0 + ah - 1
            if ar1 >= h: return None
        if not _free(g, ar0, ac0, ar1, ac0 + aw - 1, margin=1): return None
        _occupy(g, ar0, ac0, ar1, ac0 + aw - 1, acol)
    else:
        ah = rng.randint(1, r1 - r0 + 1); aw = rng.randint(1, 3)
        ar0 = rng.randint(r0, r1 - ah + 1)
        if direction == "left":
            ac1 = c0 - 1 - gap; ac0_ = ac1 - aw + 1
            if ac0_ < 0: return None
        else:
            ac0_ = c1 + 1 + gap; ac1 = ac0_ + aw - 1
            if ac1 >= w: return None
        if not _free(g, ar0, ac0_, ar0 + ah - 1, ac1, margin=1): return None
        _occupy(g, ar0, ac0_, ar0 + ah - 1, ac1, acol)
    return True


def _scene_axis(rng, direction, big_p=0.4, k_extra=(1, 3)):
    h, w = _hw(rng, big_p=big_p)
    g = blank(h, w)
    rh, rw = rng.randint(2, 4), rng.randint(2, 4)
    ref = _place_rect(g, rng, rh, rw, REF, margin=2)
    if ref is None: return None
    if _place_axis_object(g, rng, ref, direction) is None: return None
    for _ in range(rng.randint(*k_extra)):
        eh, ew = rng.randint(1, 3), rng.randint(1, 3)
        ecol = colours(rng, 1, exclude=(0, REF))[0]
        _place_rect(g, rng, eh, ew, ecol, margin=1)
    return g


def _scene_axis_pair(rng, d1, d2, big_p=0.4):
    h, w = _hw(rng, big_p=big_p)
    g = blank(h, w)
    rh, rw = rng.randint(2, 4), rng.randint(2, 4)
    ref = _place_rect(g, rng, rh, rw, REF, margin=2)
    if ref is None: return None
    for d in (d1, d2):
        if _place_axis_object(g, rng, ref, d) is None: return None
    for _ in range(rng.randint(0, 2)):
        eh, ew = rng.randint(1, 3), rng.randint(1, 3)
        ecol = colours(rng, 1, exclude=(0, REF))[0]
        _place_rect(g, rng, eh, ew, ecol, margin=1)
    return g


def _scene_touch(rng, big_p=0.4):
    h, w = _hw(rng, big_p=big_p)
    g = blank(h, w)
    rh, rw = rng.randint(2, 4), rng.randint(2, 4)
    ref = _place_rect(g, rng, rh, rw, REF, margin=2)
    if ref is None: return None
    r0, c0, r1, c1 = ref
    side = rng.choice(["up", "down", "left", "right"])
    acol = colours(rng, 1, exclude=(0, REF))[0]
    if side == "up":
        ah = rng.randint(1, 3); aw = rng.randint(1, c1 - c0 + 1); ac0 = rng.randint(c0, c1 - aw + 1)
        ar1 = r0 - 1; ar0 = ar1 - ah + 1
        if ar0 < 0: return None
    elif side == "down":
        ah = rng.randint(1, 3); aw = rng.randint(1, c1 - c0 + 1); ac0 = rng.randint(c0, c1 - aw + 1)
        ar0 = r1 + 1; ar1 = ar0 + ah - 1
        if ar1 >= h: return None
    elif side == "left":
        aw = rng.randint(1, 3); ah = rng.randint(1, r1 - r0 + 1); ar0 = rng.randint(r0, r1 - ah + 1)
        ar1 = ar0 + ah - 1
        ac1 = c0 - 1; ac0 = ac1 - aw + 1
        if ac0 < 0: return None
    else:
        aw = rng.randint(1, 3); ah = rng.randint(1, r1 - r0 + 1); ar0 = rng.randint(r0, r1 - ah + 1)
        ar1 = ar0 + ah - 1
        ac0 = c1 + 1; ac1 = ac0 + aw - 1
        if ac1 >= w: return None
    for r in range(ar0, ar1 + 1):
        for c in range(ac0, ac1 + 1):
            if g[r][c] != 0: return None
            g[r][c] = acol
    for _ in range(rng.randint(0, 3)):
        eh, ew = rng.randint(1, 3), rng.randint(1, 3)
        ecol = colours(rng, 1, exclude=(0, REF))[0]
        _place_rect(g, rng, eh, ew, ecol, margin=1)
    return g


def _scene_frame(rng, big_p=0.4):
    h, w = _hw(rng, big_p=big_p)
    g = blank(h, w)
    rh, rw = rng.randint(6, 10), rng.randint(6, 10)
    if rh + 2 >= h or rw + 2 >= w: return None
    r0 = rng.randint(1, h - rh - 1); c0 = rng.randint(1, w - rw - 1)
    r1, c1 = r0 + rh - 1, c0 + rw - 1
    rect(g, r0, c0, r1, c1, REF, fill=False)
    n_in = rng.randint(1, 2)
    for _ in range(n_in):
        ih, iw = rng.randint(1, 2), rng.randint(1, 2)
        ir0 = rng.randint(r0 + 1, r1 - ih); ic0 = rng.randint(c0 + 1, c1 - iw)
        if _free(g, ir0, ic0, ir0 + ih - 1, ic0 + iw - 1, margin=0):
            _occupy(g, ir0, ic0, ir0 + ih - 1, ic0 + iw - 1, colours(rng, 1, exclude=(0, REF))[0])
    H, W = dims(g)
    n_out = rng.randint(1, 3); placed_out = 0; tries = 0
    while placed_out < n_out and tries < 30:
        tries += 1
        eh, ew = rng.randint(1, 3), rng.randint(1, 3)
        er0 = rng.randint(0, H - eh); ec0 = rng.randint(0, W - ew)
        er1, ec1 = er0 + eh - 1, ec0 + ew - 1
        if er1 >= r0 - 1 and er0 <= r1 + 1 and ec1 >= c0 - 1 and ec0 <= c1 + 1:
            continue
        if not _free(g, er0, ec0, er1, ec1, margin=1): continue
        _occupy(g, er0, ec0, er1, ec1, colours(rng, 1, exclude=(0, REF))[0])
        placed_out += 1
    if len(objects(g, 0)) < 3: return None
    return g


def _scene_two_refs(rng, big_p=0.4):
    h, w = _hw(rng, big_p=big_p)
    g = blank(h, w)
    ref1 = _place_rect(g, rng, rng.randint(2, 3), rng.randint(2, 3), REF, margin=2)
    if ref1 is None: return None
    ref2 = _place_rect(g, rng, rng.randint(2, 3), rng.randint(2, 3), REF, margin=2)
    if ref2 is None: return None
    for _ in range(rng.randint(2, 4)):
        eh, ew = rng.randint(1, 3), rng.randint(1, 3)
        ecol = colours(rng, 1, exclude=(0, REF))[0]
        _place_rect(g, rng, eh, ew, ecol, margin=1)
    if len(objects(g, 0)) < 4: return None
    return g


# ================= 1 quadrant recolour =================
def tf_quadrant(g):
    ref, others = _parts(g)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    out = copy(g); changed = False
    for o in others:
        ob0, obc0, ob1, obc1 = bbox(o)
        if ob1 < r0: col = 1
        elif ob0 > r1: col = 2
        elif obc1 < c0: col = 3
        elif obc0 > c1: col = 4
        else: continue
        for r, c in o: out[r][c] = col
        changed = True
    return out if changed else None
rule("ref_quadrant_recolour",
     "A grey reference rectangle sits among other objects; an object entirely above it is recoloured 1, else entirely below 2, else entirely left of its columns 3, else entirely right of its columns 4, checked in that order so an object both above and left is coloured 1; objects sharing rows and columns with the reference are left unchanged.",
     lambda rng: _scene_ref(rng, 2, 5, 4, 10), tf_quadrant)


# ================= 2 rows-overlap deleted =================
def tf_rows_overlap_deleted(g):
    ref, others = _parts(g)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    out = copy(g); changed = False
    for o in others:
        ob0, obc0, ob1, obc1 = bbox(o)
        if ob0 <= r1 and ob1 >= r0:
            for r, c in o: out[r][c] = 0
            changed = True
    return out if changed else None
rule("ref_rows_overlap_deleted",
     "A grey reference rectangle sits among other objects; any object whose row range overlaps the reference's row range by at least one row, regardless of its columns, is deleted (set to background); other objects are left unchanged.",
     lambda rng: _scene_ref(rng, 2, 6, 3, 8), tf_rows_overlap_deleted)


# ================= 3 cols-overlap deleted =================
def tf_cols_overlap_deleted(g):
    ref, others = _parts(g)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    out = copy(g); changed = False
    for o in others:
        ob0, obc0, ob1, obc1 = bbox(o)
        if obc0 <= c1 and obc1 >= c0:
            for r, c in o: out[r][c] = 0
            changed = True
    return out if changed else None
rule("ref_cols_overlap_deleted",
     "A grey reference rectangle sits among other objects; any object whose column range overlaps the reference's column range by at least one column, regardless of its rows, is deleted (set to background); other objects are left unchanged.",
     lambda rng: _scene_ref(rng, 2, 6, 3, 8), tf_cols_overlap_deleted)


# ================= 4 cols-within recoloured =================
def tf_cols_within(g):
    ref, others = _parts(g)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    out = copy(g); changed = False
    for o in others:
        _, obc0, _, obc1 = bbox(o)
        if obc0 >= c0 and obc1 <= c1:
            for r, c in o: out[r][c] = 9
            changed = True
    return out if changed else None
rule("ref_cols_within_recoloured",
     "A grey reference rectangle sits among other objects; any object whose entire column range lies within the reference's column range is recoloured 9; objects extending outside that column range are left unchanged.",
     lambda rng: _scene_ref(rng, 2, 6, 3, 8), tf_cols_within)


# ================= 5 rows-within recoloured =================
def tf_rows_within(g):
    ref, others = _parts(g)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    out = copy(g); changed = False
    for o in others:
        ob0, _, ob1, _ = bbox(o)
        if ob0 >= r0 and ob1 <= r1:
            for r, c in o: out[r][c] = 8
            changed = True
    return out if changed else None
rule("ref_rows_within_recoloured",
     "A grey reference rectangle sits among other objects; any object whose entire row range lies within the reference's row range is recoloured 8; objects extending outside that row range are left unchanged.",
     lambda rng: _scene_ref(rng, 2, 6, 3, 8), tf_rows_within)


# ================= 6-9 axis moves onto reference =================
def tf_above_drops(g):
    ref, others = _parts(g)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    cands = [o for o in others if bbox(o)[1] <= c1 and bbox(o)[3] >= c0 and bbox(o)[2] < r0]
    if not cands: return None
    cands.sort(key=lambda o: r0 - bbox(o)[2])
    obj = cands[0]
    delta = r0 - bbox(obj)[2] - 1
    if delta <= 0: return None
    out = copy(g); col = g[obj[0][0]][obj[0][1]]
    for r, c in obj: out[r][c] = 0
    for r, c in obj: out[r + delta][c] = col
    return out
rule("ref_object_above_drops_on",
     "A grey reference rectangle has one object above it sharing at least one column; that nearest column-aligned object above (smallest row gap; there is only ever one by construction) drops straight down until its bottom row touches the reference's top row; all else is unchanged.",
     lambda rng: _scene_axis(rng, "up"), tf_above_drops)


def tf_below_rises(g):
    ref, others = _parts(g)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    cands = [o for o in others if bbox(o)[1] <= c1 and bbox(o)[3] >= c0 and bbox(o)[0] > r1]
    if not cands: return None
    cands.sort(key=lambda o: bbox(o)[0] - r1)
    obj = cands[0]
    shift = bbox(obj)[0] - r1 - 1
    if shift <= 0: return None
    out = copy(g); col = g[obj[0][0]][obj[0][1]]
    for r, c in obj: out[r][c] = 0
    for r, c in obj: out[r - shift][c] = col
    return out
rule("ref_object_below_rises_on",
     "A grey reference rectangle has one object below it sharing at least one column; that nearest column-aligned object below (smallest row gap) rises straight up until its top row touches the reference's bottom row; all else is unchanged.",
     lambda rng: _scene_axis(rng, "down"), tf_below_rises)


def tf_left_slides(g):
    ref, others = _parts(g)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    cands = [o for o in others if bbox(o)[0] <= r1 and bbox(o)[2] >= r0 and bbox(o)[3] < c0]
    if not cands: return None
    cands.sort(key=lambda o: c0 - bbox(o)[3])
    obj = cands[0]
    delta = c0 - bbox(obj)[3] - 1
    if delta <= 0: return None
    out = copy(g); col = g[obj[0][0]][obj[0][1]]
    for r, c in obj: out[r][c] = 0
    for r, c in obj: out[r][c + delta] = col
    return out
rule("ref_object_left_slides_on",
     "A grey reference rectangle has one object to its left sharing at least one row; that nearest row-aligned object to the left (smallest column gap) slides right until its right column touches the reference's left column; all else is unchanged.",
     lambda rng: _scene_axis(rng, "left"), tf_left_slides)


def tf_right_slides(g):
    ref, others = _parts(g)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    cands = [o for o in others if bbox(o)[0] <= r1 and bbox(o)[2] >= r0 and bbox(o)[1] > c1]
    if not cands: return None
    cands.sort(key=lambda o: bbox(o)[1] - c1)
    obj = cands[0]
    shift = bbox(obj)[1] - c1 - 1
    if shift <= 0: return None
    out = copy(g); col = g[obj[0][0]][obj[0][1]]
    for r, c in obj: out[r][c] = 0
    for r, c in obj: out[r][c - shift] = col
    return out
rule("ref_object_right_slides_on",
     "A grey reference rectangle has one object to its right sharing at least one row; that nearest row-aligned object to the right (smallest column gap) slides left until its left column touches the reference's right column; all else is unchanged.",
     lambda rng: _scene_axis(rng, "right"), tf_right_slides)


# ================= 10 diagonal erased =================
def tf_diagonal_erased(g):
    ref, others = _parts(g)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    out = copy(g); changed = False
    for o in others:
        ob0, obc0, ob1, obc1 = bbox(o)
        shares_row = ob0 <= r1 and ob1 >= r0
        shares_col = obc0 <= c1 and obc1 >= c0
        if not shares_row and not shares_col:
            for r, c in o: out[r][c] = 0
            changed = True
    return out if changed else None
rule("ref_diagonal_object_erased",
     "A grey reference rectangle sits among other objects; any object sharing no row and no column with the reference (purely diagonal to it) is erased to background; objects sharing a row or a column are left unchanged.",
     lambda rng: _scene_ref(rng, 3, 7, 3, 8), tf_diagonal_erased)


# ================= 11 relative size move =================
def tf_size_relative_move(g):
    ref, others = _parts(g)
    if ref is None: return None
    rb = bbox(ref); rcen = ((rb[0] + rb[2]) / 2, (rb[1] + rb[3]) / 2)
    rarea = len(ref)
    out = copy(g); changed = False
    H, W = dims(g)
    for o in others:
        ob = bbox(o); ocen = ((ob[0] + ob[2]) / 2, (ob[1] + ob[3]) / 2)
        dr, dc = ocen[0] - rcen[0], ocen[1] - rcen[1]
        if (dr == 0 and dc == 0) or len(o) == rarea: continue
        axis_row = abs(dr) >= abs(dc)
        sr = (1 if dr > 0 else -1) if axis_row else 0
        sc = 0 if axis_row else (1 if dc > 0 else -1)
        sign = 1 if len(o) > rarea else -1
        dr_, dc_ = sign * sr, sign * sc
        if any(not (0 <= r + dr_ < H and 0 <= c + dc_ < W) for r, c in o): continue
        col = g[o[0][0]][o[0][1]]
        for r, c in o: out[r][c] = 0
        for r, c in o: out[r + dr_][c + dc_] = col
        changed = True
    return out if changed else None
rule("ref_relative_size_move",
     "A grey reference rectangle sits among other objects; an object with more cells than the reference moves one step away from it, one with fewer cells moves one step toward it, along whichever of the row or column axis has the larger centre-to-centre gap (ties go to the row axis); objects with exactly the reference's cell count do not move.",
     lambda rng: _scene_ref(rng, 2, 6, 3, 10, margin=2), tf_size_relative_move)


# ================= 12 touching turns grey =================
def tf_touch_recolour(g):
    ref, others = _parts(g)
    if ref is None: return None
    rc = set(ref)
    out = copy(g); changed = False
    for o in others:
        if any((r + dr, c + dc) in rc for r, c in o for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))):
            for r, c in o: out[r][c] = REF
            changed = True
    return out if changed else None
rule("ref_touching_object_turns_grey",
     "A grey reference rectangle sits among other objects; any object with a cell orthogonally adjacent to a reference cell is recoloured grey; objects not touching the reference keep their colour.",
     _scene_touch, tf_touch_recolour)


# ================= 13/14 two refs =================
def tf_between_refs(g):
    obs = objects(g, 0)
    refs = [o for o in obs if g[o[0][0]][o[0][1]] == REF]
    if len(refs) != 2: return None
    refs = sorted(refs, key=lambda o: bbox(o)[:2])
    b1, b2 = bbox(refs[0]), bbox(refs[1])
    if b1[1] > b2[1]: b1, b2 = b2, b1
    lo, hi = b1[3], b2[1]
    if lo >= hi: return None
    out = copy(g); changed = False
    for o in obs:
        if o in refs: continue
        _, oc0, _, oc1 = bbox(o)
        if oc0 > lo and oc1 < hi:
            for r, c in o: out[r][c] = 7
            changed = True
    return out if changed else None
rule("ref_between_two_recoloured",
     "Two grey reference rectangles stand at different columns; any other object whose entire column range lies strictly between the right edge of the left reference and the left edge of the right reference is recoloured 7; objects outside or straddling that gap are left unchanged.",
     _scene_two_refs, tf_between_refs)


def tf_outside_span_erased(g):
    obs = objects(g, 0)
    refs = [o for o in obs if g[o[0][0]][o[0][1]] == REF]
    if len(refs) != 2: return None
    b1, b2 = bbox(refs[0]), bbox(refs[1])
    if b1[1] > b2[1]: b1, b2 = b2, b1
    lo, hi = b1[3], b2[1]
    if lo >= hi: return None
    out = copy(g); changed = False
    for o in obs:
        if o in refs: continue
        _, oc0, _, oc1 = bbox(o)
        if oc1 < lo or oc0 > hi:
            for r, c in o: out[r][c] = 0
            changed = True
    return out if changed else None
rule("ref_outside_two_span_erased",
     "Two grey reference rectangles stand at different columns; any other object whose column range lies entirely outside the gap between the two references (entirely left of the left reference or entirely right of the right one) is erased to background; objects inside or straddling the gap are left unchanged.",
     _scene_two_refs, tf_outside_span_erased)


# ================= 15 nearest four directions =================
def tf_nearest_four(g):
    ref, others = _parts(g)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    def cand(pred, keyf):
        cs = [o for o in others if pred(bbox(o))]
        return min(cs, key=keyf) if cs else None
    up = cand(lambda b: b[1] <= c1 and b[3] >= c0 and b[2] < r0, lambda o: r0 - bbox(o)[2])
    down = cand(lambda b: b[1] <= c1 and b[3] >= c0 and b[0] > r1, lambda o: bbox(o)[0] - r1)
    left = cand(lambda b: b[0] <= r1 and b[2] >= r0 and b[3] < c0, lambda o: c0 - bbox(o)[3])
    right = cand(lambda b: b[0] <= r1 and b[2] >= r0 and b[1] > c1, lambda o: bbox(o)[1] - c1)
    out = copy(g); changed = False
    for obj, col in ((up, 1), (down, 2), (left, 3), (right, 4)):
        if obj is None: continue
        for r, c in obj: out[r][c] = col
        changed = True
    return out if changed else None
rule("ref_nearest_four_directions_marked",
     "A grey reference rectangle sits among other objects; among objects that fully overlap its column range, the nearest one strictly above is recoloured 1 and the nearest strictly below 2; among objects that fully overlap its row range, the nearest one strictly left is recoloured 3 and the nearest strictly right 4; a direction with no aligned object is left unmarked; nearest means smallest gap to the reference.",
     lambda rng: _scene_ref(rng, 3, 6, 3, 8), tf_nearest_four)


# ================= 16/17 centre-relative mirror =================
def tf_mirror_left_objects(g):
    ref, others = _parts(g)
    if ref is None: return None
    rb = bbox(ref); rcc = (rb[1] + rb[3]) / 2
    out = copy(g); changed = False
    for o in others:
        ob0, obc0, ob1, obc1 = bbox(o)
        if (obc0 + obc1) / 2 < rcc:
            sub = flip_h(crop(g, ob0, obc0, ob1, obc1))
            for r, c in o: out[r][c] = 0
            paste(out, sub, ob0, obc0)
            changed = True
    return out if changed else None
rule("ref_left_of_centre_mirrored_h",
     "A grey reference rectangle sits among other objects; any object whose bounding-box centre column is strictly left of the reference's centre column is mirrored horizontally within its own bounding box; objects at or right of the reference's centre column are left unchanged.",
     lambda rng: _scene_ref(rng, 2, 6, 4, 10, margin=1), tf_mirror_left_objects)


def tf_mirror_above_objects(g):
    ref, others = _parts(g)
    if ref is None: return None
    rb = bbox(ref); rcr = (rb[0] + rb[2]) / 2
    out = copy(g); changed = False
    for o in others:
        ob0, obc0, ob1, obc1 = bbox(o)
        if (ob0 + ob1) / 2 < rcr:
            sub = flip_v(crop(g, ob0, obc0, ob1, obc1))
            for r, c in o: out[r][c] = 0
            paste(out, sub, ob0, obc0)
            changed = True
    return out if changed else None
rule("ref_above_centre_mirrored_v",
     "A grey reference rectangle sits among other objects; any object whose bounding-box centre row is strictly above the reference's centre row is mirrored vertically within its own bounding box; objects at or below the reference's centre row are left unchanged.",
     lambda rng: _scene_ref(rng, 2, 6, 4, 10, margin=1), tf_mirror_above_objects)


# ================= 18/19 hollow frame =================
def tf_frame_keep_enclosed(g):
    obs = objects(g, 0)
    ref = next((o for o in obs if g[o[0][0]][o[0][1]] == REF), None)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    out = copy(g); kept_any = False
    for o in obs:
        if o is ref: continue
        ob0, obc0, ob1, obc1 = bbox(o)
        if r0 < ob0 and ob1 < r1 and c0 < obc0 and obc1 < c1:
            kept_any = True; continue
        for r, c in o: out[r][c] = 0
    return out if kept_any else None
rule("ref_frame_enclosed_kept",
     "A grey reference hollow rectangle (frame) encloses some objects and others lie outside it; objects whose whole bounding box falls strictly inside the frame's interior are kept unchanged; every object not strictly enclosed is deleted to background; the frame itself always stays.",
     _scene_frame, tf_frame_keep_enclosed)


def tf_frame_recolour_interior(g):
    obs = objects(g, 0)
    ref = next((o for o in obs if g[o[0][0]][o[0][1]] == REF), None)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    out = copy(g); changed = False
    for o in obs:
        if o is ref: continue
        ob0, obc0, ob1, obc1 = bbox(o)
        if r0 < ob0 and ob1 < r1 and c0 < obc0 and obc1 < c1:
            for r, c in o: out[r][c] = 6
            changed = True
    return out if changed else None
rule("ref_frame_interior_recoloured",
     "A grey reference hollow rectangle (frame) encloses some objects and others lie outside it; objects whose whole bounding box falls strictly inside the frame's interior are recoloured 6; objects outside the frame are left unchanged.",
     _scene_frame, tf_frame_recolour_interior)


# ================= 20/21 nearest/farthest overall =================
def tf_nearest_overall_grey(g):
    ref, others = _parts(g)
    if ref is None or not others: return None
    rb = bbox(ref)
    best = min(others, key=lambda o: (_bbox_gap(rb, bbox(o)), bbox(o)[:2]))
    out = copy(g)
    for r, c in best: out[r][c] = REF
    return out
rule("ref_nearest_overall_turns_grey",
     "A grey reference rectangle sits among other objects; the single object closest to it, measured by the Manhattan gap between their bounding boxes (ties broken by the smallest top-left row then column), is recoloured grey; all other objects are left unchanged.",
     lambda rng: _scene_ref(rng, 2, 6, 3, 8), tf_nearest_overall_grey)


def tf_farthest_overall_erased(g):
    ref, others = _parts(g)
    if ref is None or not others: return None
    rb = bbox(ref)
    worst = min(others, key=lambda o: (-_bbox_gap(rb, bbox(o)), bbox(o)[:2]))
    out = copy(g)
    for r, c in worst: out[r][c] = 0
    return out
rule("ref_farthest_overall_erased",
     "A grey reference rectangle sits among other objects; the single object farthest from it, measured by the Manhattan gap between their bounding boxes (ties broken by the smallest top-left row then column), is erased to background; all other objects are left unchanged.",
     lambda rng: _scene_ref(rng, 2, 6, 3, 8), tf_farthest_overall_erased)


# ================= 22 rank by distance =================
def tf_rank_distance(g):
    ref, others = _parts(g)
    if ref is None or len(others) < 2: return None
    rb = bbox(ref)
    ordered = sorted(others, key=lambda o: (_bbox_gap(rb, bbox(o)), bbox(o)[:2]))
    out = copy(g)
    for i, o in enumerate(ordered):
        col = min(9, i + 1)
        for r, c in o: out[r][c] = col
    return out
rule("ref_rank_by_distance_recoloured",
     "A grey reference rectangle sits among other objects; objects are ranked by their Manhattan bounding-box gap to the reference, nearest first (ties broken by smallest top-left row then column), and recoloured with their rank: 1 for nearest, 2 for next, and so on, capped at 9.",
     lambda rng: _scene_ref(rng, 3, 7, 3, 8), tf_rank_distance, digits=True)


# ================= 23/24 pair swap =================
def tf_swap_vert(g):
    ref, others = _parts(g)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    above = [o for o in others if bbox(o)[1] <= c1 and bbox(o)[3] >= c0 and bbox(o)[2] < r0]
    below = [o for o in others if bbox(o)[1] <= c1 and bbox(o)[3] >= c0 and bbox(o)[0] > r1]
    if not above or not below: return None
    above.sort(key=lambda o: r0 - bbox(o)[2]); below.sort(key=lambda o: bbox(o)[0] - r1)
    a, b = above[0], below[0]
    ca, cb = g[a[0][0]][a[0][1]], g[b[0][0]][b[0][1]]
    if ca == cb: return None
    out = copy(g)
    for r, c in a: out[r][c] = cb
    for r, c in b: out[r][c] = ca
    return out
rule("ref_vertical_pair_swap_colours",
     "A grey reference rectangle has one column-aligned object above it and one below; the nearest column-aligned object above (smallest row gap) and the nearest below swap colours with each other; all else is unchanged.",
     lambda rng: _scene_axis_pair(rng, "up", "down"), tf_swap_vert)


def tf_swap_horiz(g):
    ref, others = _parts(g)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    left = [o for o in others if bbox(o)[0] <= r1 and bbox(o)[2] >= r0 and bbox(o)[3] < c0]
    right = [o for o in others if bbox(o)[0] <= r1 and bbox(o)[2] >= r0 and bbox(o)[1] > c1]
    if not left or not right: return None
    left.sort(key=lambda o: c0 - bbox(o)[3]); right.sort(key=lambda o: bbox(o)[1] - c1)
    a, b = left[0], right[0]
    ca, cb = g[a[0][0]][a[0][1]], g[b[0][0]][b[0][1]]
    if ca == cb: return None
    out = copy(g)
    for r, c in a: out[r][c] = cb
    for r, c in b: out[r][c] = ca
    return out
rule("ref_horizontal_pair_swap_colours",
     "A grey reference rectangle has one row-aligned object to its left and one to its right; the nearest row-aligned object to the left (smallest column gap) and the nearest to the right swap colours with each other; all else is unchanged.",
     lambda rng: _scene_axis_pair(rng, "left", "right"), tf_swap_horiz)


# ================= 25/26 distance buckets =================
def tf_distance_bucket2(g):
    ref, others = _parts(g)
    if ref is None or not others: return None
    rb = bbox(ref); H, W = dims(g); R = max(H, W) // 3
    out = copy(g); changed = False
    for o in others:
        col = 2 if _bbox_gap(rb, bbox(o)) <= R else 1
        for r, c in o: out[r][c] = col
        changed = True
    return out if changed else None
rule("ref_distance_bucket_binary",
     "A grey reference rectangle sits among other objects; an object whose Manhattan bounding-box gap to the reference is at most one third of the grid's longer side is recoloured 2; farther objects are recoloured 1.",
     lambda rng: _scene_ref(rng, 2, 6, 3, 8), tf_distance_bucket2)


def tf_distance_bucket3(g):
    ref, others = _parts(g)
    if ref is None or not others: return None
    rb = bbox(ref); H, W = dims(g); R1 = max(H, W) // 4; R2 = max(H, W) // 2
    out = copy(g); changed = False
    for o in others:
        d = _bbox_gap(rb, bbox(o))
        col = 1 if d <= R1 else (2 if d <= R2 else 3)
        for r, c in o: out[r][c] = col
        changed = True
    return out if changed else None
rule("ref_distance_bucket_triple",
     "A grey reference rectangle sits among other objects; an object with Manhattan bounding-box gap to the reference at most one quarter of the grid's longer side is recoloured 1, at most one half is recoloured 2, and farther objects are recoloured 3.",
     lambda rng: _scene_ref(rng, 2, 6, 3, 8), tf_distance_bucket3)


# ================= 27 direction counts bar =================
def tf_direction_counts(g):
    ref, others = _parts(g)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    cnt = [0, 0, 0, 0]
    for o in others:
        ob0, obc0, ob1, obc1 = bbox(o)
        if ob1 < r0: cnt[0] += 1
        elif ob0 > r1: cnt[1] += 1
        elif obc1 < c0: cnt[2] += 1
        elif obc0 > c1: cnt[3] += 1
    return [[min(9, c) for c in cnt]]
rule("ref_direction_counts_bar",
     "A grey reference rectangle sits among other objects; output a single row of four cells giving, in order, the count (capped at 9) of objects entirely above, entirely below, entirely left of, and entirely right of the reference, with each object assigned to the first of those four categories it satisfies in that order.",
     lambda rng: _scene_ref(rng, 3, 8, 2, 6), tf_direction_counts, digits=True)


# ================= 28/29 draw line to reference =================
def tf_draw_line_vertical(g):
    ref, others = _parts(g)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    cands = []
    for o in others:
        ob0, obc0, ob1, obc1 = bbox(o)
        if obc0 <= c1 and obc1 >= c0:
            if ob1 < r0: cands.append((r0 - ob1 - 1, o, obc0, obc1))
            elif ob0 > r1: cands.append((ob0 - r1 - 1, o, obc0, obc1))
    if not cands: return None
    cands.sort(key=lambda t: (t[0], bbox(t[1])[:2]))
    gap, o, obc0, obc1 = cands[0]
    if gap == 0: return None
    ob0, _, ob1, _ = bbox(o)
    col = g[o[0][0]][o[0][1]]
    out = copy(g); cmid = (obc0 + obc1) // 2
    if ob1 < r0:
        for r in range(ob1 + 1, r0): out[r][cmid] = col
    else:
        for r in range(r1 + 1, ob0): out[r][cmid] = col
    return out
rule("ref_vertical_align_draws_line",
     "A grey reference rectangle has a column-aligned object above or below it; the nearest such object (smallest row gap; ties broken by smallest top-left row then column) draws a one-cell-wide vertical line of its own colour through its bounding-box midpoint column, filling the gap between it and the reference, without the object itself moving.",
     lambda rng: _scene_ref(rng, 2, 6, 3, 8, margin=2), tf_draw_line_vertical)


def tf_draw_line_horizontal(g):
    ref, others = _parts(g)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    cands = []
    for o in others:
        ob0, obc0, ob1, obc1 = bbox(o)
        if ob0 <= r1 and ob1 >= r0:
            if obc1 < c0: cands.append((c0 - obc1 - 1, o, ob0, ob1))
            elif obc0 > c1: cands.append((obc0 - c1 - 1, o, ob0, ob1))
    if not cands: return None
    cands.sort(key=lambda t: (t[0], bbox(t[1])[:2]))
    gap, o, ob0, ob1 = cands[0]
    if gap == 0: return None
    _, obc0, _, obc1 = bbox(o)
    col = g[o[0][0]][o[0][1]]
    out = copy(g); rmid = (ob0 + ob1) // 2
    if obc1 < c0:
        for c in range(obc1 + 1, c0): out[rmid][c] = col
    else:
        for c in range(c1 + 1, obc0): out[rmid][c] = col
    return out
rule("ref_horizontal_align_draws_line",
     "A grey reference rectangle has a row-aligned object left or right of it; the nearest such object (smallest column gap; ties broken by smallest top-left row then column) draws a one-cell-tall horizontal line of its own colour through its bounding-box midpoint row, filling the gap between it and the reference, without the object itself moving.",
     lambda rng: _scene_ref(rng, 2, 6, 3, 8, margin=2), tf_draw_line_horizontal)


# ================= 30/31 area comparisons =================
def tf_equal_area_grey(g):
    ref, others = _parts(g)
    if ref is None: return None
    rarea = len(ref)
    out = copy(g); changed = False
    for o in others:
        if len(o) == rarea:
            for r, c in o: out[r][c] = REF
            changed = True
    return out if changed else None
rule("ref_equal_area_turns_grey",
     "A grey reference object sits among other objects; any other object with exactly the same number of cells as the reference is recoloured grey; objects with a different cell count are left unchanged.",
     lambda rng: _scene_ref(rng, 2, 6, 3, 8), tf_equal_area_grey)


def tf_area_multiple(g):
    ref, others = _parts(g)
    if ref is None: return None
    rarea = len(ref)
    out = copy(g); changed = False
    for o in others:
        if rarea > 0 and len(o) > rarea and len(o) % rarea == 0:
            for r, c in o: out[r][c] = 6
            changed = True
    return out if changed else None
def gi_area_multiple(rng):
    h, w = _hw(rng, big_p=0.4)
    g = blank(h, w)
    rh, rw = rng.randint(2, 3), rng.randint(2, 3)
    rarea = rh * rw
    ref_cells = [(r, c) for r in range(rh) for c in range(rw)]
    k = rng.randint(2, 3)
    mult_shape = random_shape(rng, k * rarea)
    extra_n = rng.randint(1, 3)
    extra_shapes = [random_shape(rng, rng.randint(1, 4)) for _ in range(extra_n)]
    shapes = [ref_cells, mult_shape] + extra_shapes
    cols = [REF] + colours(rng, 1 + extra_n, exclude=(0, REF))
    if place_shapes(rng, g, shapes, cols, margin=1) is None:
        return None
    return g
rule("ref_area_multiple_recoloured",
     "A grey reference object sits among other objects; any other object whose cell count is a whole multiple of the reference's cell count (and larger than it) is recoloured 6; all other objects are left unchanged.",
     gi_area_multiple, tf_area_multiple)


# ================= 32 bbox overlap, not touching =================
def gi_bbox_overlap(rng):
    h = rng.randint(21, 30) if rng.random() < 0.4 else rng.randint(14, 20)
    w = rng.randint(21, 30) if rng.random() < 0.4 else rng.randint(14, 20)
    g = blank(h, w)
    rh, rw = rng.randint(2, 4), rng.randint(2, 4)
    r0 = rng.randint(3, h - rh - 4); c0 = rng.randint(3, w - rw - 4)
    r1, c1 = r0 + rh - 1, c0 + rw - 1
    _occupy(g, r0, c0, r1, c1, REF)
    acol = colours(rng, 1, exclude=(0, REF))[0]
    vc = c0 - 2; hr = r1 + 2
    for r in range(r0 - 2, hr + 1):
        g[r][vc] = acol
    for c in range(vc, c1 + 1):
        g[hr][c] = acol
    for _ in range(rng.randint(0, 2)):
        eh, ew = rng.randint(1, 3), rng.randint(1, 3)
        ecol = colours(rng, 1, exclude=(0, REF))[0]
        _place_rect(g, rng, eh, ew, ecol, margin=1)
    return g
def tf_bbox_overlap_recolour(g):
    ref, others = _parts(g)
    if ref is None: return None
    rb = bbox(ref); rc = set(ref)
    out = copy(g); changed = False
    for o in others:
        ob = bbox(o)
        overlap = not (ob[2] < rb[0] or ob[0] > rb[2] or ob[3] < rb[1] or ob[1] > rb[3])
        if not overlap: continue
        touching = any((r + dr, c + dc) in rc for r, c in o for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)))
        if touching: continue
        for r, c in o: out[r][c] = 7
        changed = True
    return out if changed else None
rule("ref_bbox_overlap_not_touching_recoloured",
     "A grey reference object sits among other objects; any other object whose bounding box overlaps the reference's bounding box but whose cells do not actually touch the reference is recoloured 7; objects with no bounding-box overlap, or that do touch, are left unchanged.",
     gi_bbox_overlap, tf_bbox_overlap_recolour)


# ================= 33/34 band + side =================
def tf_row_band_side(g):
    ref, others = _parts(g)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    out = copy(g); changed = False
    for o in others:
        ob0, obc0, ob1, obc1 = bbox(o)
        if ob0 > r1 or ob1 < r0: continue
        if obc1 < c0: col = 1
        elif obc0 > c1: col = 2
        else: continue
        for r, c in o: out[r][c] = col
        changed = True
    return out if changed else None
rule("ref_row_band_side_recoloured",
     "A grey reference rectangle sits among other objects; an object whose row range overlaps the reference's row range AND lies entirely left of it is recoloured 1, and one that overlaps the row range AND lies entirely right is recoloured 2; objects whose row range does not overlap the reference's are left unchanged.",
     lambda rng: _scene_ref(rng, 2, 6, 3, 8), tf_row_band_side)


def tf_col_band_side(g):
    ref, others = _parts(g)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    out = copy(g); changed = False
    for o in others:
        ob0, obc0, ob1, obc1 = bbox(o)
        if obc0 > c1 or obc1 < c0: continue
        if ob1 < r0: col = 3
        elif ob0 > r1: col = 4
        else: continue
        for r, c in o: out[r][c] = col
        changed = True
    return out if changed else None
rule("ref_col_band_side_recoloured",
     "A grey reference rectangle sits among other objects; an object whose column range overlaps the reference's column range AND lies entirely above it is recoloured 3, and one that overlaps the column range AND lies entirely below is recoloured 4; objects whose column range does not overlap the reference's are left unchanged.",
     lambda rng: _scene_ref(rng, 2, 6, 3, 8), tf_col_band_side)


# ================= 35 nearer to which of two refs =================
def tf_nearest_ref_side(g):
    obs = objects(g, 0)
    refs = [o for o in obs if g[o[0][0]][o[0][1]] == REF]
    if len(refs) != 2: return None
    refs = sorted(refs, key=lambda o: bbox(o)[:2])
    def cen(o):
        b = bbox(o); return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    c1_, c2_ = cen(refs[0]), cen(refs[1])
    out = copy(g); changed = False
    for o in obs:
        if o in refs: continue
        oc = cen(o)
        d1 = abs(oc[0] - c1_[0]) + abs(oc[1] - c1_[1])
        d2 = abs(oc[0] - c2_[0]) + abs(oc[1] - c2_[1])
        col = 3 if d1 < d2 else (4 if d2 < d1 else 8)
        for r, c in o: out[r][c] = col
        changed = True
    return out if changed else None
rule("ref_two_refs_nearest_side_recoloured",
     "Two grey reference objects stand apart, the one with the smaller top-left (row, column) being 'first'; every other object is recoloured 3 if its centroid is closer (Manhattan distance between centroids) to the first reference, 4 if closer to the second, or 8 if equidistant.",
     _scene_two_refs, tf_nearest_ref_side)


# ================= 36 quadrant nearest-only =================
def tf_quadrant_nearest_only(g):
    ref, others = _parts(g)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    groups = {1: [], 2: [], 3: [], 4: []}
    for o in others:
        ob0, obc0, ob1, obc1 = bbox(o)
        if ob1 < r0: groups[1].append(o)
        elif ob0 > r1: groups[2].append(o)
        elif obc1 < c0: groups[3].append(o)
        elif obc0 > c1: groups[4].append(o)
    out = copy(g); changed = False
    for col, grp in groups.items():
        if not grp: continue
        nearest = min(grp, key=lambda o: (_bbox_gap((r0, c0, r1, c1), bbox(o)), bbox(o)[:2]))
        for r, c in nearest: out[r][c] = col
        changed = True
    return out if changed else None
rule("ref_quadrant_nearest_only_marked",
     "A grey reference rectangle sits among other objects grouped as entirely above, below, left of or right of it (checked in that priority order); in each non-empty group, only the object nearest the reference by Manhattan bounding-box gap (ties broken by smallest top-left row then column) is recoloured 1/2/3/4 for above/below/left/right; farther objects in the same group are left unchanged.",
     lambda rng: _scene_ref(rng, 4, 8, 2, 6), tf_quadrant_nearest_only)


# ================= 37/38 largest/smallest per quadrant =================
def tf_largest_per_quadrant_erased(g):
    ref, others = _parts(g)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    groups = {0: [], 1: [], 2: [], 3: []}
    for o in others:
        ob0, obc0, ob1, obc1 = bbox(o)
        if ob1 < r0: groups[0].append(o)
        elif ob0 > r1: groups[1].append(o)
        elif obc1 < c0: groups[2].append(o)
        elif obc0 > c1: groups[3].append(o)
    out = copy(g); changed = False
    for grp in groups.values():
        if not grp: continue
        biggest = max(grp, key=lambda o: (len(o), tuple(-v for v in bbox(o)[:2])))
        for r, c in biggest: out[r][c] = 0
        changed = True
    return out if changed else None
rule("ref_quadrant_largest_erased",
     "A grey reference rectangle sits among other objects grouped as entirely above, below, left of or right of it (checked in that priority order); in each non-empty group, the object with the most cells (ties broken by smallest top-left row then column) is erased to background; the rest of that group is left unchanged.",
     lambda rng: _scene_ref(rng, 4, 8, 2, 6), tf_largest_per_quadrant_erased)


def tf_smallest_per_quadrant_grey(g):
    ref, others = _parts(g)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    groups = {0: [], 1: [], 2: [], 3: []}
    for o in others:
        ob0, obc0, ob1, obc1 = bbox(o)
        if ob1 < r0: groups[0].append(o)
        elif ob0 > r1: groups[1].append(o)
        elif obc1 < c0: groups[2].append(o)
        elif obc0 > c1: groups[3].append(o)
    out = copy(g); changed = False
    for grp in groups.values():
        if not grp: continue
        smallest = min(grp, key=lambda o: (len(o), bbox(o)[:2]))
        for r, c in smallest: out[r][c] = REF
        changed = True
    return out if changed else None
rule("ref_quadrant_smallest_turns_grey",
     "A grey reference rectangle sits among other objects grouped as entirely above, below, left of or right of it (checked in that priority order); in each non-empty group, the object with the fewest cells (ties broken by smallest top-left row then column) is recoloured grey; the rest of that group is left unchanged.",
     lambda rng: _scene_ref(rng, 4, 8, 2, 6), tf_smallest_per_quadrant_grey)


# ================= 39 quadrant counts at corners =================
def tf_corner_counts(g):
    ref, others = _parts(g)
    if ref is None: return None
    r0, c0, r1, c1 = bbox(ref)
    cnt = [0, 0, 0, 0]
    for o in others:
        ob0, obc0, ob1, obc1 = bbox(o)
        if ob1 < r0: cnt[0] += 1
        elif ob0 > r1: cnt[1] += 1
        elif obc1 < c0: cnt[2] += 1
        elif obc0 > c1: cnt[3] += 1
    H, W = dims(g)
    out = copy(g)
    out[0][0] = min(9, cnt[0]); out[0][W - 1] = min(9, cnt[1])
    out[H - 1][0] = min(9, cnt[2]); out[H - 1][W - 1] = min(9, cnt[3])
    return out
rule("ref_quadrant_counts_at_corners",
     "A grey reference rectangle sits among other objects; all objects and the reference are left in place, and the grid's four corner cells are overwritten with counts (capped at 9) of objects entirely above (top-left corner), entirely below (top-right corner), entirely left of (bottom-left corner) and entirely right of (bottom-right corner) the reference, each object counted in the first category it satisfies in that order.",
     lambda rng: _scene_ref(rng, 3, 8, 2, 6, margin=1), tf_corner_counts, digits=True)


# ================= 40 swap nearest and farthest =================
def tf_swap_nearest_farthest(g):
    ref, others = _parts(g)
    if ref is None or len(others) < 2: return None
    rb = bbox(ref)
    nearest = min(others, key=lambda o: (_bbox_gap(rb, bbox(o)), bbox(o)[:2]))
    farthest = min(others, key=lambda o: (-_bbox_gap(rb, bbox(o)), bbox(o)[:2]))
    if nearest is farthest: return None
    cn, cf = g[nearest[0][0]][nearest[0][1]], g[farthest[0][0]][farthest[0][1]]
    if cn == cf: return None
    out = copy(g)
    for r, c in nearest: out[r][c] = cf
    for r, c in farthest: out[r][c] = cn
    return out
rule("ref_swap_nearest_and_farthest_colours",
     "A grey reference rectangle sits among at least two other objects; the object nearest the reference and the object farthest from it, measured by Manhattan bounding-box gap (ties broken by smallest top-left row then column), swap colours with each other; all other objects are left unchanged.",
     lambda rng: _scene_ref(rng, 3, 7, 3, 8), tf_swap_nearest_farthest)
