# b050_setops.py -- 40 rules, theme SET OPERATIONS ON COLLECTIONS OF OBJECTS. Two or three panels (
# separated by a reserved separator colour, SEP=9) each hold a set of shapes (connected same-colour
# blobs with a margin gap so components never merge). Rules compare shapes ACROSS panels by identity
# (shape+colour, shape only, colour only, or shape up to rotation) and compute set operations: left
# minus right, intersection, union, symmetric difference, majority-of-three, exactly-once, etc.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

SEP = 9
SHAPE_COLS = list(range(1, 9))


# ---------- shared helpers (not rules) ----------

def _hw(rng, w_lo=7, w_hi=13, p_big=0.4):
    h = rng.randint(21, 30) if rng.random() < p_big else rng.randint(7, 16)
    w = rng.randint(w_lo, w_hi)
    return h, w


def _hw3(rng, p_big=0.4):
    h = rng.randint(21, 30) if rng.random() < p_big else rng.randint(7, 16)
    w = rng.randint(6, 9)
    return h, w


def _normcells(cells_):
    r0, c0, _, _ = bbox(cells_)
    return tuple(sorted((r - r0, c - c0) for r, c in cells_))


def _rotvariants(cells_):
    pts = list(_normcells(cells_))
    outs = []
    cur = pts
    for _ in range(4):
        outs.append(_normcells(cur)); cur = [(c, -r) for r, c in cur]
    cur = [(r, -c) for r, c in pts]
    for _ in range(4):
        outs.append(_normcells(cur)); cur = [(c, -r) for r, c in cur]
    return outs


def _canon_rot(cells_):
    return min(_rotvariants(cells_))


def _objs(panel):
    return components(panel, lambda v: v != 0, conn8=False)


def _col(panel, obj):
    return panel[obj[0][0]][obj[0][1]]


def _sig_s(obj):
    return _normcells(obj)


def _sig_sc(panel, obj):
    return (_normcells(obj), _col(panel, obj))


def _crop_obj(panel, obj):
    r0, c0, r1, c1 = bbox(obj)
    return crop(panel, r0, c0, r1, c1)


def _row_from_crops(crops):
    if not crops:
        return None
    h = max(len(cg) for cg in crops)
    w = sum(len(cg[0]) for cg in crops) + (len(crops) - 1)
    g = blank(h, w)
    x = 0
    for cg in crops:
        ch, cw = dims(cg)
        for r in range(ch):
            for c in range(cw):
                if cg[r][c]:
                    g[r][c + x] = cg[r][c]
        x += cw + 1
    return g


def _swatch_row(cols_list):
    cs = sorted(set(cols_list))
    if not cs:
        return None
    g = blank(1, len(cs) * 2 - 1)
    for i, c in enumerate(cs):
        g[0][i * 2] = c
    return g


def _bar(n, colour, width=10, h=1):
    if n <= 0 or n >= width:
        return None
    g = blank(h, width)
    for i in range(n):
        g[0][i] = colour
    return g


def _outline(g, obj, colour):
    r0, c0, r1, c1 = bbox(obj)
    H, W = dims(g)
    for r in range(r0 - 1, r1 + 2):
        for c in range(c0 - 1, c1 + 2):
            if 0 <= r < H and 0 <= c < W and (r < r0 or r > r1 or c < c0 or c > c1) and g[r][c] == 0:
                g[r][c] = colour
    return g


def _join2(a, b, sep=SEP):
    h = len(a)
    return [a[r] + [sep] + b[r] for r in range(h)]


def _split2(g):
    h, w = dims(g)
    sc = [c for c in range(w) if g[0][c] != 0 and all(g[r][c] == g[0][c] for r in range(h))]
    if len(sc) != 1:
        return None
    sep = g[0][sc[0]]; c0 = sc[0]
    left = [row[:c0] for row in g]; right = [row[c0 + 1:] for row in g]
    if not left[0] or not right[0]:
        return None
    return left, right, sep


def _join3(a, b, c, sep=SEP):
    h = len(a)
    return [a[r] + [sep] + b[r] + [sep] + c[r] for r in range(h)]


def _split3(g):
    h, w = dims(g)
    sc = [c for c in range(w) if g[0][c] != 0 and all(g[r][c] == g[0][c] for r in range(h))]
    if len(sc) != 2:
        return None
    sep = g[0][sc[0]]
    if g[0][sc[1]] != sep:
        return None
    c0, c1 = sc
    a = [row[:c0] for row in g]; b = [row[c0 + 1:c1] for row in g]; c = [row[c1 + 1:] for row in g]
    if not a[0] or not b[0] or not c[0]:
        return None
    return a, b, c, sep


def _new_templates(rng, n, size_lo, size_hi, avoid=None, tries=400):
    out = list(avoid) if avoid else []
    start = len(out)
    t = 0
    while len(out) - start < n and t < tries:
        t += 1
        s = random_shape(rng, rng.randint(size_lo, size_hi))
        sig = _canon_rot(s)
        if all(_canon_rot(x) != sig for x in out):
            out.append(s)
    return out[start:] if len(out) - start == n else None


def _two_panels(rng, k_common=1, k_left=1, k_right=1, size_lo=3, size_hi=7, recolour_common=False, rotate_common=False):
    h, w = _hw(rng)
    total = k_common + k_left + k_right
    if total > len(SHAPE_COLS):
        return None
    templates = _new_templates(rng, total, size_lo, size_hi)
    if templates is None:
        return None
    common, lonly, ronly = templates[:k_common], templates[k_common:k_common + k_left], templates[k_common + k_left:]
    cols = rng.sample(SHAPE_COLS, total)
    lspecs, rspecs = [], []
    for i, s in enumerate(common):
        cl = cols[i]
        cr = rng.choice([x for x in SHAPE_COLS if x != cl]) if recolour_common else cl
        sr = rng.choice(_rotvariants(s)) if rotate_common else s
        lspecs.append((s, cl)); rspecs.append((sr, cr))
    j = k_common
    for s in lonly:
        lspecs.append((s, cols[j])); j += 1
    for s in ronly:
        rspecs.append((s, cols[j])); j += 1
    gl, gr = blank(h, w), blank(h, w)
    if place_shapes(rng, gl, [s for s, _ in lspecs], [c for _, c in lspecs], margin=1) is None:
        return None
    if place_shapes(rng, gr, [s for s, _ in rspecs], [c for _, c in rspecs], margin=1) is None:
        return None
    return gl, gr


def _two_panels_colour_link(rng, k_link=1, k_left_extra=1, k_right_extra=1, size_lo=3, size_hi=7):
    h, w = _hw(rng)
    total_t = k_link * 2 + k_left_extra + k_right_extra
    n_cols = k_link + k_left_extra + k_right_extra
    if n_cols > len(SHAPE_COLS):
        return None
    templates = _new_templates(rng, total_t, size_lo, size_hi)
    if templates is None:
        return None
    cols = rng.sample(SHAPE_COLS, n_cols)
    i = ci = 0
    lspecs, rspecs = [], []
    for _ in range(k_link):
        c = cols[ci]; ci += 1
        lspecs.append((templates[i], c)); i += 1
        rspecs.append((templates[i], c)); i += 1
    for _ in range(k_left_extra):
        c = cols[ci]; ci += 1
        lspecs.append((templates[i], c)); i += 1
    for _ in range(k_right_extra):
        c = cols[ci]; ci += 1
        rspecs.append((templates[i], c)); i += 1
    gl, gr = blank(h, w), blank(h, w)
    if place_shapes(rng, gl, [s for s, _ in lspecs], [c for _, c in lspecs], margin=1) is None:
        return None
    if place_shapes(rng, gr, [s for s, _ in rspecs], [c for _, c in rspecs], margin=1) is None:
        return None
    return gl, gr


def _two_panels_size_link(rng, k_link=1, k_left_extra=1, k_right_extra=1, size_lo=3, size_hi=8):
    h, w = _hw(rng)
    templates, lsh, rsh = [], [], []
    def newshape(n):
        for _ in range(100):
            s = random_shape(rng, n)
            if all(_canon_rot(t) != _canon_rot(s) for t in templates):
                templates.append(s); return s
        return None
    for _ in range(k_link):
        n = rng.randint(size_lo, size_hi)
        a, b = newshape(n), newshape(n)
        if a is None or b is None:
            return None
        lsh.append(a); rsh.append(b)
    for _ in range(k_left_extra):
        a = newshape(rng.randint(size_lo, size_hi))
        if a is None:
            return None
        lsh.append(a)
    for _ in range(k_right_extra):
        b = newshape(rng.randint(size_lo, size_hi))
        if b is None:
            return None
        rsh.append(b)
    total = len(lsh) + len(rsh)
    if total > len(SHAPE_COLS):
        return None
    cols = rng.sample(SHAPE_COLS, total)
    lcols, rcols = cols[:len(lsh)], cols[len(lsh):]
    gl, gr = blank(h, w), blank(h, w)
    if place_shapes(rng, gl, lsh, lcols, margin=1) is None:
        return None
    if place_shapes(rng, gr, rsh, rcols, margin=1) is None:
        return None
    return gl, gr


def _three_panels(rng, k3=1, kAB=1, kAC=1, kBC=1, kA=1, kB=1, kC=1, size_lo=3, size_hi=5):
    h, w = _hw3(rng)
    total = k3 + kAB + kAC + kBC + kA + kB + kC
    if total > len(SHAPE_COLS):
        return None
    templates = _new_templates(rng, total, size_lo, size_hi)
    if templates is None:
        return None
    i = 0
    def take(k):
        nonlocal i
        chunk = templates[i:i + k]; i += k; return chunk
    s3, sAB, sAC, sBC, sA, sB, sC = take(k3), take(kAB), take(kAC), take(kBC), take(kA), take(kB), take(kC)
    cols = rng.sample(SHAPE_COLS, total)
    col_of = {id(t): cols[j] for j, t in enumerate(templates)}
    a_sh = s3 + sAB + sAC + sA
    b_sh = s3 + sAB + sBC + sB
    c_sh = s3 + sAC + sBC + sC
    ga, gb, gc = blank(h, w), blank(h, w), blank(h, w)
    if place_shapes(rng, ga, a_sh, [col_of[id(s)] for s in a_sh], margin=1) is None:
        return None
    if place_shapes(rng, gb, b_sh, [col_of[id(s)] for s in b_sh], margin=1) is None:
        return None
    if place_shapes(rng, gc, c_sh, [col_of[id(s)] for s in c_sh], margin=1) is None:
        return None
    return ga, gb, gc


# ================================================================== 1
def gi_1(rng):
    p = _two_panels(rng, rng.randint(1, 3), rng.randint(1, 3), rng.randint(0, 2))
    if p is None: return None
    return _join2(*p)
def tf_1(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    rsig = {_sig_sc(gr, o) for o in _objs(gr)}
    out = copy(gl)
    for o in _objs(gl):
        if _sig_sc(gl, o) in rsig:
            for r, c in o: out[r][c] = 0
    return out
rule("shapes_left_not_right_erased", "Output the left panel with every shape (same shape and colour) that also appears in the right panel erased.", gi_1, tf_1)


# ================================================================== 2
def gi_2(rng):
    p = _two_panels(rng, rng.randint(1, 3), rng.randint(0, 2), rng.randint(1, 3))
    if p is None: return None
    return _join2(*p)
def tf_2(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    lsig = {_sig_sc(gl, o) for o in _objs(gl)}
    out = copy(gr)
    for o in _objs(gr):
        if _sig_sc(gr, o) in lsig:
            for r, c in o: out[r][c] = 0
    return out
rule("shapes_right_not_left_erased", "Output the right panel with every shape (same shape and colour) that also appears in the left panel erased.", gi_2, tf_2)


# ================================================================== 3
def gi_3(rng):
    p = _two_panels(rng, rng.randint(1, 3), rng.randint(1, 2), rng.randint(0, 2))
    if p is None: return None
    return _join2(*p)
def tf_3(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    rsig = {_sig_sc(gr, o) for o in _objs(gr)}
    out = copy(gl)
    for o in _objs(gl):
        if _sig_sc(gl, o) not in rsig:
            for r, c in o: out[r][c] = 0
    return out
rule("shapes_common_both_kept_left", "Output the left panel keeping only the shapes (same shape and colour) that also appear in the right panel, erasing the rest.", gi_3, tf_3)


# ================================================================== 4
def gi_4(rng):
    p = _two_panels(rng, rng.randint(1, 3), rng.randint(0, 2), rng.randint(1, 2))
    if p is None: return None
    return _join2(*p)
def tf_4(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    lsig = {_sig_sc(gl, o) for o in _objs(gl)}
    out = copy(gr)
    for o in _objs(gr):
        if _sig_sc(gr, o) not in lsig:
            for r, c in o: out[r][c] = 0
    return out
rule("shapes_common_both_kept_right", "Output the right panel keeping only the shapes (same shape and colour) that also appear in the left panel, erasing the rest.", gi_4, tf_4)


# ================================================================== 5
def gi_5(rng):
    p = _two_panels(rng, rng.randint(1, 3), rng.randint(0, 2), rng.randint(0, 2))
    if p is None: return None
    return _join2(*p)
def tf_5(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    rsig = {_sig_sc(gr, o) for o in _objs(gr)}
    m = [o for o in _objs(gl) if _sig_sc(gl, o) in rsig]
    if not m: return None
    m.sort(key=len)
    return _row_from_crops([_crop_obj(gl, o) for o in m])
rule("shapes_common_both_row", "Output a single row listing, left to right by size, the shapes (same shape and colour) present in both panels.", gi_5, tf_5)


# ================================================================== 6
def gi_6(rng):
    p = _two_panels(rng, rng.randint(1, 2), rng.randint(1, 2), rng.randint(1, 2))
    if p is None: return None
    return _join2(*p)
def tf_6(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    seen, items = set(), []
    for panel in (gl, gr):
        for o in _objs(panel):
            sg = _sig_sc(panel, o)
            if sg not in seen:
                seen.add(sg); items.append((panel, o))
    if len(items) < 2: return None
    items.sort(key=lambda po: len(po[1]))
    return _row_from_crops([_crop_obj(p, o) for p, o in items])
rule("shapes_union_row", "Output a single row listing, left to right by size, every distinct shape (by shape and colour) found in either panel, with duplicates removed.", gi_6, tf_6)


# ================================================================== 7
def gi_7(rng):
    p = _two_panels(rng, rng.randint(0, 1), rng.randint(1, 2), rng.randint(1, 2))
    if p is None: return None
    return _join2(*p)
def tf_7(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    cnt, occ = {}, []
    for panel in (gl, gr):
        for o in _objs(panel):
            sg = _sig_sc(panel, o); cnt[sg] = cnt.get(sg, 0) + 1; occ.append((panel, o, sg))
    items = [(p, o) for p, o, sg in occ if cnt[sg] == 1]
    if not items: return None
    items.sort(key=lambda po: len(po[1]))
    return _row_from_crops([_crop_obj(p, o) for p, o in items])
rule("shapes_symmetric_difference_row", "Output a single row listing, left to right by size, the shapes (by shape and colour) present in exactly one of the two panels.", gi_7, tf_7)


# ================================================================== 8
def gi_8(rng):
    p = _two_panels(rng, rng.randint(1, 2), rng.randint(1, 2), rng.randint(1, 2))
    if p is None: return None
    return _join2(*p)
def tf_8(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    lsig = {_sig_sc(gl, o) for o in _objs(gl)}
    out = copy(gl)
    for o in _objs(gr):
        if _sig_sc(gr, o) not in lsig:
            for r, c in o: out[r][c] = gr[r][c]
    return out
rule("shapes_union_merged_inplace", "Output the left panel with the right panel's shapes pasted in at their own positions, skipping any shape (by shape and colour) already present on the left.", gi_8, tf_8)


# ================================================================== 9
def gi_9(rng):
    p = _two_panels(rng, rng.randint(1, 2), rng.randint(1, 3), rng.randint(0, 2))
    if p is None: return None
    return _join2(*p)
def tf_9(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    rsig = {_sig_s(o) for o in _objs(gr)}
    out = copy(gl)
    for o in _objs(gl):
        col = 5 if _sig_s(o) in rsig else 2
        for r, c in o: out[r][c] = col
    return out
rule("recolour_shared_vs_unique_left", "Output the left panel with every shape shared (by shape, any colour) with the right panel recoloured 5, and shapes unique to the left recoloured 2.", gi_9, tf_9)


# ================================================================== 10
def gi_10(rng):
    p = _two_panels(rng, rng.randint(1, 2), rng.randint(0, 2), rng.randint(1, 3))
    if p is None: return None
    return _join2(*p)
def tf_10(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    lsig = {_sig_s(o) for o in _objs(gl)}
    out = copy(gr)
    for o in _objs(gr):
        col = 5 if _sig_s(o) in lsig else 3
        for r, c in o: out[r][c] = col
    return out
rule("recolour_shared_vs_unique_right", "Output the right panel with every shape shared (by shape, any colour) with the left panel recoloured 5, and shapes unique to the right recoloured 3.", gi_10, tf_10)


# ================================================================== 11
def gi_11(rng):
    p = _two_panels(rng, rng.randint(1, 3), rng.randint(0, 2), rng.randint(0, 2))
    if p is None: return None
    return _join2(*p)
def tf_11(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    lsig = {_sig_s(o) for o in _objs(gl)}
    rsig = {_sig_s(o) for o in _objs(gr)}
    return _bar(len(lsig & rsig), 4)
rule("shared_shape_count_bar", "Output a 1-row bar whose length equals the number of shapes (by shape, any colour) found in both panels.", gi_11, tf_11)
# ================================================================== 12
def gi_12(rng):
    p = _two_panels(rng, rng.randint(0, 1), rng.randint(1, 3), rng.randint(0, 2))
    if p is None: return None
    return _join2(*p)
def tf_12(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    rsig = {_sig_s(o) for o in _objs(gr)}
    n = sum(1 for o in _objs(gl) if _sig_s(o) not in rsig)
    return _bar(n, 6)
rule("left_only_shape_count_bar", "Output a 1-row bar whose length equals the number of shapes (by shape, any colour) in the left panel that do not appear in the right panel.", gi_12, tf_12)
# ================================================================== 13
def gi_13(rng):
    p = _two_panels_colour_link(rng, rng.randint(1, 2), rng.randint(1, 2), rng.randint(0, 2))
    if p is None: return None
    return _join2(*p)
def tf_13(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    rcols = {_col(gr, o) for o in _objs(gr)}
    out = copy(gl)
    for o in _objs(gl):
        if _col(gl, o) not in rcols:
            for r, c in o: out[r][c] = 0
    return out
rule("shapes_matched_by_colour_kept", "Output the left panel keeping only shapes whose colour also appears on some shape in the right panel, even if the shapes differ; erase the rest.", gi_13, tf_13)


# ================================================================== 14
def gi_14(rng):
    p = _two_panels(rng, rng.randint(0, 2), rng.randint(1, 3), rng.randint(0, 2))
    if p is None: return None
    return _join2(*p)
def tf_14(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    lc = {_col(gl, o) for o in _objs(gl)}; rc = {_col(gr, o) for o in _objs(gr)}
    return _swatch_row(lc - rc)
rule("colours_only_in_left_row", "Output a 1-row swatch, lowest value first, of the colours used in the left panel that are not used anywhere in the right panel.", gi_14, tf_14)


# ================================================================== 15
def gi_15(rng):
    p = _two_panels(rng, rng.randint(0, 2), rng.randint(0, 2), rng.randint(1, 3))
    if p is None: return None
    return _join2(*p)
def tf_15(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    lc = {_col(gl, o) for o in _objs(gl)}; rc = {_col(gr, o) for o in _objs(gr)}
    return _swatch_row(rc - lc)
rule("colours_only_in_right_row", "Output a 1-row swatch, lowest value first, of the colours used in the right panel that are not used anywhere in the left panel.", gi_15, tf_15)


# ================================================================== 16
def gi_16(rng):
    p = _two_panels(rng, rng.randint(1, 3), rng.randint(0, 2), rng.randint(0, 2))
    if p is None: return None
    return _join2(*p)
def tf_16(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    lc = {_col(gl, o) for o in _objs(gl)}; rc = {_col(gr, o) for o in _objs(gr)}
    return _swatch_row(lc & rc)
rule("colours_common_both_row", "Output a 1-row swatch, lowest value first, of the colours used in both panels.", gi_16, tf_16)


# ================================================================== 17
def gi_17(rng):
    p = _two_panels(rng, rng.randint(1, 2), rng.randint(1, 3), rng.randint(0, 2), rotate_common=True)
    if p is None: return None
    return _join2(*p)
def tf_17(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    rsig = {_canon_rot(o) for o in _objs(gr)}
    out = copy(gl)
    for o in _objs(gl):
        if _canon_rot(o) not in rsig:
            for r, c in o: out[r][c] = 0
    return out
rule("shapes_matched_up_to_rotation_kept", "Output the left panel keeping only shapes that match a shape in the right panel after some rotation or reflection, erasing the rest.", gi_17, tf_17)


# ================================================================== 18
def gi_18(rng):
    p = _two_panels(rng, rng.randint(0, 2), rng.randint(1, 3), rng.randint(0, 2), rotate_common=True)
    if p is None: return None
    return _join2(*p)
def tf_18(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    rsig = {_canon_rot(o) for o in _objs(gr)}
    out = copy(gl)
    for o in _objs(gl):
        if _canon_rot(o) in rsig:
            for r, c in o: out[r][c] = 0
    return out
rule("shapes_unmatched_up_to_rotation_kept", "Output the left panel keeping only shapes with no match in the right panel under any rotation or reflection, erasing the matches.", gi_18, tf_18)


# ================================================================== 19
def gi_19(rng):
    p = _two_panels_size_link(rng, rng.randint(1, 2), rng.randint(0, 2), rng.randint(1, 2))
    if p is None: return None
    return _join2(*p)
def tf_19(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    lsizes = {len(o) for o in _objs(gl)}
    out = copy(gr)
    for o in _objs(gr):
        if len(o) not in lsizes:
            for r, c in o: out[r][c] = 0
    return out
rule("right_shapes_with_size_twin_kept", "Output the right panel keeping only shapes whose cell count matches the cell count of some shape in the left panel, erasing the rest.", gi_19, tf_19)


# ================================================================== 20
def gi_20(rng):
    p = _two_panels_size_link(rng, rng.randint(1, 2), rng.randint(1, 2), rng.randint(0, 2))
    if p is None: return None
    return _join2(*p)
def tf_20(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    rsizes = {len(o) for o in _objs(gr)}
    out = copy(gl)
    for o in _objs(gl):
        if len(o) not in rsizes:
            for r, c in o: out[r][c] = 0
    return out
rule("left_shapes_with_size_twin_kept", "Output the left panel keeping only shapes whose cell count matches the cell count of some shape in the right panel, erasing the rest.", gi_20, tf_20)


# ================================================================== 21
def gi_21(rng):
    p = _two_panels_size_link(rng, rng.randint(1, 2), rng.randint(0, 2), rng.randint(1, 2))
    if p is None: return None
    return _join2(*p)
def tf_21(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    lsizes = {len(o) for o in _objs(gl)}
    out = copy(gr)
    for o in _objs(gr):
        if len(o) in lsizes:
            for r, c in o: out[r][c] = 0
    return out
rule("right_minus_left_sizes", "Output the right panel with every shape whose cell count matches some shape's cell count in the left panel erased.", gi_21, tf_21)


# ================================================================== 22
def gi_22(rng):
    p = _two_panels(rng, rng.randint(1, 2), rng.randint(1, 2), rng.randint(0, 2))
    if p is None: return None
    return _join2(*p)
def tf_22(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    rsig = {_sig_sc(gr, o) for o in _objs(gr)}
    keep = [o for o in _objs(gl) if _sig_sc(gl, o) not in rsig]
    if not keep: return None
    out = copy(gl)
    for o in _objs(gl):
        if _sig_sc(gl, o) in rsig:
            for r, c in o: out[r][c] = 0
    cells_ = [c for o in keep for c in o]
    r0, c0, r1, c1 = bbox(cells_)
    return crop(out, r0, c0, r1, c1)
rule("left_minus_shared_cropped", "Output the left panel, with shapes also present on the right erased, cropped tightly to the bounding box of what remains.", gi_22, tf_22)


# ================================================================== 23
def gi_23(rng):
    p = _three_panels(rng, rng.randint(1, 2), rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1))
    if p is None: return None
    return _join3(*p)
def tf_23(g):
    sp = _split3(g)
    if sp is None: return None
    a, b, c, sep = sp
    sa = {_sig_s(o) for o in _objs(a)}; sb = {_sig_s(o) for o in _objs(b)}; sc = {_sig_s(o) for o in _objs(c)}
    common = sa & sb & sc
    items = [o for o in _objs(a) if _sig_s(o) in common]
    if not items: return None
    items.sort(key=len)
    return _row_from_crops([_crop_obj(a, o) for o in items])
rule("three_panel_all_common_row", "Output a single row of the shapes (by shape, any colour) present in all three panels, smallest first.", gi_23, tf_23)


# ================================================================== 24
def gi_24(rng):
    p = _three_panels(rng, rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1), rng.randint(1, 2), rng.randint(0, 1), rng.randint(0, 1))
    if p is None: return None
    return _join3(*p)
def tf_24(g):
    sp = _split3(g)
    if sp is None: return None
    a, b, c, sep = sp
    cnt, occ = {}, []
    for panel in (a, b, c):
        for o in _objs(panel):
            sg = _sig_s(o); cnt[sg] = cnt.get(sg, 0) + 1; occ.append((panel, o, sg))
    items = [(p, o) for p, o, sg in occ if cnt[sg] == 1]
    if not items: return None
    items.sort(key=lambda po: len(po[1]))
    return _row_from_crops([_crop_obj(p, o) for p, o in items])
rule("three_panel_exactly_once_row", "Output a single row of the shapes (by shape, any colour) that appear in exactly one of the three panels, smallest first.", gi_24, tf_24)


# ================================================================== 25
def gi_25(rng):
    p = _three_panels(rng, rng.randint(1, 2), rng.randint(1, 1), rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1))
    if p is None: return None
    return _join3(*p)
def tf_25(g):
    sp = _split3(g)
    if sp is None: return None
    a, b, c, sep = sp
    cnt = {}
    for panel in (a, b, c):
        for o in _objs(panel):
            sg = _sig_s(o); cnt[sg] = cnt.get(sg, 0) + 1
    out = copy(a)
    for o in _objs(a):
        if cnt[_sig_s(o)] < 2:
            for r, c in o: out[r][c] = 0
    return out
rule("three_panel_majority_kept", "Output the first panel keeping only shapes (by shape, any colour) that appear in at least two of the three panels, erasing the rest.", gi_25, tf_25)


# ================================================================== 26
def gi_26(rng):
    p = _two_panels(rng, rng.randint(0, 2), rng.randint(1, 3), rng.randint(1, 3))
    if p is None: return None
    return _join2(*p)
def tf_26(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    lsig = {_sig_s(o) for o in _objs(gl)}; rsig = {_sig_s(o) for o in _objs(gr)}
    nl = sum(1 for o in _objs(gl) if _sig_s(o) not in rsig)
    nr = sum(1 for o in _objs(gr) if _sig_s(o) not in lsig)
    if nl == nr: return None
    return gl if nl > nr else gr
rule("panel_with_more_exclusive_shapes", "Output whichever panel, left or right, holds more shapes (by shape, any colour) that are absent from the other panel.", gi_26, tf_26)


# ================================================================== 27
def gi_27(rng):
    p = _three_panels(rng, rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1), 1, rng.randint(0, 1), rng.randint(0, 1))
    if p is None: return None
    return _join3(*p)
def tf_27(g):
    sp = _split3(g)
    if sp is None: return None
    a, b, c, sep = sp
    cnt = {}
    for panel in (a, b, c):
        for o in _objs(panel):
            sg = _sig_s(o); cnt[sg] = cnt.get(sg, 0) + 1
    holders = set()
    for idx, panel in enumerate((a, b, c)):
        for o in _objs(panel):
            if cnt[_sig_s(o)] == 1:
                holders.add(idx)
    if len(holders) != 1: return None
    return (a, b, c)[holders.pop()]
rule("odd_one_out_panel_of_three", "Output the one panel, of three, that contains a shape (by shape, any colour) found in no other panel.", gi_27, tf_27)


# ================================================================== 28
def gi_28(rng):
    p = _two_panels(rng, rng.randint(0, 1), rng.randint(1, 6), rng.randint(0, 6))
    if p is None: return None
    return _join2(*p)
def tf_28(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    n = abs(len(_objs(gl)) - len(_objs(gr)))
    return _bar(n, 7)
rule("shapes_count_difference_bar", "Output a 1-row bar whose length equals the difference between the number of shapes in the left panel and the number in the right panel.", gi_28, tf_28)
# ================================================================== 29
def gi_29(rng):
    p = _two_panels(rng, rng.randint(0, 2), rng.randint(1, 2), rng.randint(1, 2))
    if p is None: return None
    return _join2(*p)
def tf_29(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    sigs = {_sig_s(o) for o in _objs(gl)} | {_sig_s(o) for o in _objs(gr)}
    return _bar(len(sigs), 8)
rule("shapes_total_distinct_count_bar", "Output a 1-row bar whose length equals the number of distinct shapes (by shape, any colour) found across both panels.", gi_29, tf_29)


# ================================================================== 30
def gi_30(rng):
    p = _two_panels(rng, rng.randint(1, 2), rng.randint(1, 2), rng.randint(0, 2))
    if p is None: return None
    return _join2(*p)
def tf_30(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    rsig = {_sig_s(o) for o in _objs(gr)}
    shared = sorted([o for o in _objs(gl) if _sig_s(o) in rsig], key=len)
    uniq = sorted([o for o in _objs(gl) if _sig_s(o) not in rsig], key=len)
    items = shared + uniq
    if not items: return None
    return _row_from_crops([_crop_obj(gl, o) for o in items])
rule("left_shapes_grouped_row", "Output a single row of every left-panel shape, cropped and ordered smallest to largest, shapes shared with the right panel first, then shapes unique to the left.", gi_30, tf_30)


# ================================================================== 31
def gi_31(rng):
    p = _two_panels(rng, rng.randint(1, 2), rng.randint(1, 2), rng.randint(0, 2))
    if p is None: return None
    return _join2(*p)
def tf_31(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    rsig = {_sig_s(o) for o in _objs(gr)}
    shared = [o for o in _objs(gl) if _sig_s(o) in rsig]
    if not shared: return None
    big = max(shared, key=len)
    out = copy(gl)
    for r, c in big: out[r][c] = 5
    return out
rule("largest_shared_shape_recolour", "Output the left panel with the largest shape that is also present in the right panel recoloured 5.", gi_31, tf_31)


# ================================================================== 32
def gi_32(rng):
    p = _two_panels(rng, rng.randint(0, 2), rng.randint(1, 3), rng.randint(0, 2))
    if p is None: return None
    return _join2(*p)
def tf_32(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    rsig = {_sig_s(o) for o in _objs(gr)}
    uniq = [o for o in _objs(gl) if _sig_s(o) not in rsig]
    if not uniq: return None
    small = min(uniq, key=len)
    out = copy(gl)
    for r, c in small: out[r][c] = 3
    return out
rule("smallest_unique_left_shape_recolour", "Output the left panel with the smallest shape that is unique to the left panel recoloured 3.", gi_32, tf_32)


# ================================================================== 33
def gi_33(rng):
    p = _two_panels_colour_link(rng, rng.randint(1, 2), rng.randint(0, 2), rng.randint(1, 2))
    if p is None: return None
    return _join2(*p)
def tf_33(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    rcols = {_col(gr, o) for o in _objs(gr)}
    m = [o for o in _objs(gl) if _col(gl, o) in rcols]
    if not m: return None
    m.sort(key=len)
    return _row_from_crops([_crop_obj(gl, o) for o in m])
rule("shapes_matched_by_colour_row", "Output a single row, smallest first, of the left panel's shapes whose colour also appears on some shape in the right panel.", gi_33, tf_33)


# ================================================================== 34
def gi_34(rng):
    p = _two_panels_colour_link(rng, rng.randint(1, 2), rng.randint(1, 2), rng.randint(0, 2))
    if p is None: return None
    return _join2(*p)
def tf_34(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    rcols = {_col(gr, o) for o in _objs(gr)}
    m = [o for o in _objs(gl) if _col(gl, o) not in rcols]
    if not m: return None
    m.sort(key=len)
    return _row_from_crops([_crop_obj(gl, o) for o in m])
rule("shapes_unique_colour_row", "Output a single row, smallest first, of the left panel's shapes whose colour appears on no shape in the right panel.", gi_34, tf_34)


# ================================================================== 35
def gi_35(rng):
    p = _three_panels(rng, rng.randint(1, 2), rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1))
    if p is None: return None
    return _join3(*p)
def tf_35(g):
    sp = _split3(g)
    if sp is None: return None
    a, b, c, sep = sp
    seen, items = set(), []
    for panel in (a, b, c):
        for o in _objs(panel):
            sg = _sig_s(o)
            if sg not in seen:
                seen.add(sg); items.append((panel, o))
    if len(items) < 2: return None
    items.sort(key=lambda po: len(po[1]))
    return _row_from_crops([_crop_obj(p, o) for p, o in items])
rule("three_panel_union_row", "Output a single row, smallest first, of every distinct shape (by shape, any colour) found across the three panels, each in its own colour.", gi_35, tf_35)


# ================================================================== 36
def gi_36(rng):
    p = _three_panels(rng, 0, rng.randint(1, 2), rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 2))
    if p is None: return None
    return _join3(*p)
def tf_36(g):
    sp = _split3(g)
    if sp is None: return None
    a, b, c, sep = sp
    sa = {_sig_s(o) for o in _objs(a)}; sb = {_sig_s(o) for o in _objs(b)}; sc = {_sig_s(o) for o in _objs(c)}
    want = (sa & sb) - sc
    items = [o for o in _objs(a) if _sig_s(o) in want]
    if not items: return None
    items.sort(key=len)
    return _row_from_crops([_crop_obj(a, o) for o in items])
rule("pairwise_common_ab_not_c_row", "Output a single row, smallest first, of the shapes (by shape, any colour) present in the first and second panels but absent from the third.", gi_36, tf_36)


# ================================================================== 37
def gi_37(rng):
    p = _two_panels(rng, rng.randint(1, 2), rng.randint(0, 2), rng.randint(1, 2))
    if p is None: return None
    return _join2(*p)
def tf_37(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    lsig = {_sig_s(o) for o in _objs(gl)}
    out = copy(gr)
    for o in _objs(gr):
        if _sig_s(o) in lsig:
            _outline(out, o, 6)
    return out
rule("right_panel_with_left_shared_outlined", "Output the right panel with a border drawn in colour 6 around every shape that also appears (by shape, any colour) in the left panel.", gi_37, tf_37)


# ================================================================== 38
def gi_38(rng):
    p = _two_panels(rng, rng.randint(1, 2), rng.randint(1, 2), rng.randint(0, 2))
    if p is None: return None
    return _join2(*p)
def tf_38(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    rsig = {_sig_s(o) for o in _objs(gr)}
    out = copy(gl)
    for o in _objs(gl):
        if _sig_s(o) in rsig:
            _outline(out, o, 5)
    return out
rule("left_panel_with_right_shared_outlined", "Output the left panel with a border drawn in colour 5 around every shape that also appears (by shape, any colour) in the right panel.", gi_38, tf_38)


# ================================================================== 39
def gi_39(rng):
    p = _three_panels(rng, 0, rng.randint(1, 1), rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1))
    if p is None: return None
    return _join3(*p)
def tf_39(g):
    sp = _split3(g)
    if sp is None: return None
    a, b, c, sep = sp
    cnt, occ = {}, []
    for panel in (a, b, c):
        for o in _objs(panel):
            sg = _sig_s(o); cnt[sg] = cnt.get(sg, 0) + 1; occ.append((panel, o, sg))
    items = [(p, o) for p, o, sg in occ if cnt[sg] == 2]
    if not items: return None
    seen, uniq = set(), []
    for p, o in items:
        sg = _sig_s(o)
        if sg not in seen:
            seen.add(sg); uniq.append((p, o))
    uniq.sort(key=lambda po: len(po[1]))
    return _row_from_crops([_crop_obj(p, o) for p, o in uniq])
rule("three_panel_exactly_two_row", "Output a single row, smallest first, of the shapes (by shape, any colour) that appear in exactly two of the three panels.", gi_39, tf_39)


# ================================================================== 40
def gi_40(rng):
    p = _two_panels(rng, rng.randint(0, 2), rng.randint(1, 2), rng.randint(0, 2))
    if p is None: return None
    return _join2(*p)
def tf_40(g):
    sp = _split2(g)
    if sp is None: return None
    gl, gr, sep = sp
    rsig = {_sig_sc(gr, o) for o in _objs(gr)}
    m = [o for o in _objs(gl) if _sig_sc(gl, o) not in rsig]
    if not m: return None
    m.sort(key=len)
    return _row_from_crops([_crop_obj(gl, o) for o in m])
rule("shapes_left_not_right_row", "Output a single row, smallest first, of the shapes (same shape and colour) present in the left panel but not the right.", gi_40, tf_40)
