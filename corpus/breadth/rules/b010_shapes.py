# b010_shapes.py -- shape matching, ordering and alignment: templates up to rotation, mirror pairs, holes and
# fitting pieces, aligning to edges / centre lines / markers / lattices, lineups sorted by a property, slots,
# convex and orthogonal hulls, shape classes, panels, rotation families.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


# ---------------------------------------------------------------- local helpers
def _norm(cs):
    r0 = min(r for r, _ in cs); c0 = min(c for _, c in cs)
    return frozenset((r - r0, c - c0) for r, c in cs)


def _hw(sh):
    return max(r for r, _ in sh) + 1, max(c for _, c in sh) + 1


def _rot(sh):
    h, _ = _hw(sh)
    return _norm({(c, h - 1 - r) for r, c in sh})


def _rots(sh):
    out = [sh]
    for _ in range(3):
        out.append(_rot(out[-1]))
    return out


def _canon(sh):
    return min(tuple(sorted(s)) for s in _rots(sh))


def _flip(sh):
    _, w = _hw(sh)
    return _norm({(r, w - 1 - c) for r, c in sh})


def _shape(rng, lo=3, hi=6):
    return _norm(set(random_shape(rng, rng.randint(lo, hi))))


def _stamp(g, sh, r0, c0, col):
    for r, c in sh:
        g[r0 + r][c0 + c] = col
    return g


def _col(g, o):
    return g[o[0][0]][o[0][1]]


def _bh(o):
    r0, c0, r1, c1 = bbox(o); return r1 - r0 + 1


def _bw(o):
    r0, c0, r1, c1 = bbox(o); return c1 - c0 + 1


def _big(rng):
    return rng.random() < 0.4


def _size(rng, lo, hi, big=None):
    """Grid dims; about 40% of the time both sides land in the 21-30 band."""
    if _big(rng) if big is None else big:
        return rng.randint(21, 30), rng.randint(21, 30)
    return size(rng, lo, hi)


def _put(rng, g, sh, col, margin=1, tries=120, rows=None, cols_=None):
    """Stamp sh at a random spot whose bounding box plus margin is empty; rows/cols_ bound the top-left corner."""
    H, W = dims(g); h, w = _hw(sh)
    rlo, rhi = rows or (0, H - h); clo, chi = cols_ or (0, W - w)
    rhi, chi = min(rhi, H - h), min(chi, W - w)
    if rlo > rhi or clo > chi:
        return None
    for _ in range(tries):
        r0, c0 = rng.randint(rlo, rhi), rng.randint(clo, chi)
        if all(g[r][c] == 0 for r in range(max(0, r0 - margin), min(H, r0 + h + margin))
               for c in range(max(0, c0 - margin), min(W, c0 + w + margin))):
            _stamp(g, sh, r0, c0, col); return r0, c0
    return None


def _row_layout(rng, shapes, cols_, H=None, tops=None, gap=(1, 3), pad=(0, 2), wmax=30, big=None):
    """Objects left to right in disjoint column bands, each at its own random (or given) top row.
    In big mode (about 40%) the free dimensions are pushed into the 21-30 band."""
    hs = [_hw(s)[0] for s in shapes]; ws = [_hw(s)[1] for s in shapes]
    big = _big(rng) if big is None else big
    H = H or (rng.randint(21, 30) if big else rng.randint(max(hs) + 1, max(hs) + 6))
    gaps = [rng.randint(*gap) for _ in shapes[1:]] + [0]; base = sum(ws) + sum(gaps)
    if big and base <= wmax:
        W = rng.randint(max(21, base), wmax) if max(21, base) <= wmax else base
        lp = rng.randint(0, W - base); rp = W - base - lp
    else:
        lp = rng.randint(*pad); rp = rng.randint(*pad); W = lp + base + rp
    if W > wmax or H > 30 or max(hs) > H:
        return None
    g = blank(H, W); c = lp
    for i, (sh, col) in enumerate(zip(shapes, cols_)):
        r0 = tops[i] if tops else rng.randint(0, H - hs[i])
        _stamp(g, sh, r0, c, col); c += ws[i] + gaps[i]
    return g


def _band_layout(rng, shapes, cols_, W=None, lefts=None, hmax=30, big=None):
    """Objects top to bottom in disjoint row bands (the transpose of _row_layout)."""
    g = _row_layout(rng, [_norm({(c, r) for r, c in s}) for s in shapes], cols_, H=W, tops=lefts, wmax=hmax, big=big)
    return None if g is None else transpose(g)


def _scatter(rng, shapes, cols_, lo=9, hi=20, margin=1):
    h, w = _size(rng, lo, hi); g = blank(h, w)
    for sh, col in zip(shapes, cols_):
        if _put(rng, g, sh, col, margin=margin) is None:
            return None
    return g


def _distinct(rng, k, lo=3, hi=6, key=lambda s: s, avoid=()):
    out, seen = [], set(avoid)
    for _ in range(200):
        s = _shape(rng, lo, hi)
        if key(s) not in seen:
            seen.add(key(s)); out.append(s)
        if len(out) == k:
            return out
    return None


# 1 template matched up to rotation is recoloured
def gi_tmpl_rot(rng):
    t = _shape(rng, 3, 6); others = _distinct(rng, rng.randint(2, 4), 3, 6, key=_canon, avoid=[_canon(t)])
    if others is None: return None
    T = rng.choice([c for c in COLOURS if c != 8])
    shapes = [t, rng.choice(_rots(t)[1:])] + others
    return _scatter(rng, shapes, [T] + [8] * (len(shapes) - 1))
def tf_tmpl_rot(g):
    obs = objects(g, 0); tm = [o for o in obs if _col(g, o) != 8]
    if len(tm) != 1: return None
    tc = _canon(_norm(tm[0])); hits = [o for o in obs if _col(g, o) == 8 and _canon(_norm(o)) == tc]
    if len(hits) != 1: return None
    out = copy(g)
    for r, c in hits[0]: out[r][c] = _col(g, tm[0])
    return out
rule("recolour_rotation_match_of_template", "The one grey object that is a rotated copy of the coloured template takes the template's colour.", gi_tmpl_rot, tf_tmpl_rot)


# 2 connect the mirror-image pair
def gi_mirror_pair(rng):
    s = _shape(rng, 3, 6)
    if _flip(s) == s: return None
    ds = _distinct(rng, rng.randint(1, 3), 3, 6, avoid=[s, _flip(s)])
    if ds is None or any(_flip(d) in (s, _flip(s)) for d in ds): return None
    h = _hw(s)[0]; dh = max(_hw(d)[0] for d in ds); big = _big(rng)
    H = rng.randint(21, 30) if big else rng.randint(h + dh + 1, min(30, h + dh + 6))
    pr = rng.randint(0, H - h); i = rng.randint(0, len(ds)); shapes = ds[:i] + [s, _flip(s)] + ds[i:]
    tops = []
    for sh in shapes:
        oh = _hw(sh)[0]
        ok = [r for r in range(0, H - oh + 1) if r + oh <= pr or r >= pr + h] if sh not in (s, _flip(s)) else [pr]
        if not ok: return None
        tops.append(rng.choice(ok))
    cols_ = [rng.choice([c for c in COLOURS if c != 5]) for _ in shapes]
    return _row_layout(rng, shapes, cols_, H=H, tops=tops, gap=(1, 4), big=big)
def tf_mirror_pair(g):
    obs = sorted(objects(g, 0), key=lambda o: bbox(o)[1]); pairs = []
    for i, a in enumerate(obs):
        for b in obs[i + 1:]:
            na, nb = _norm(a), _norm(b)
            if na != nb and _flip(na) == nb and bbox(a)[0] == bbox(b)[0]: pairs.append((a, b))
    if len(pairs) != 1: return None
    a, b = pairs[0]; r0, _, r1, c1 = bbox(a); c2 = bbox(b)[1]; out = copy(g); row = (r0 + r1) // 2
    for c in range(c1 + 1, c2): out[row][c] = 5
    return out
rule("connect_mirror_image_pair", "The two objects that are mirror images of each other are joined by a grey line along their middle row.", gi_mirror_pair, tf_mirror_pair)


# 3 / 23 piece that fits the hole
def _hole_scene(rng, k_lo=2, k_hi=3):
    h, w = _size(rng, 11, 22); g = blank(h, w); hole = _shape(rng, 3, 6); hh, hw = _hw(hole)
    bh, bw = hh + rng.randint(2, 4), hw + rng.randint(2, 4)
    if bh > h - 2 or bw > w - 2: return None
    k = rng.randint(k_lo, k_hi); A, *cs = colours(rng, k + 1)
    r0, c0 = rng.randint(0, h - bh), rng.randint(0, w - bw); rect(g, r0, c0, r0 + bh - 1, c0 + bw - 1, A)
    _stamp(g, hole, rng.randint(r0 + 1, r0 + bh - hh - 1), rng.randint(c0 + 1, c0 + bw - hw - 1), 0)
    pieces = _distinct(rng, k - 1, 3, 6, avoid=[hole])
    if pieces is None: return None
    pieces.append(hole); rng.shuffle(pieces)
    for sh, col in zip(pieces, cs):
        if _put(rng, g, sh, col) is None: return None
    return g
def _hole_parts(g):
    obs = objects(g, 0); blk = max(obs, key=len); r0, c0, r1, c1 = bbox(blk)
    hole = {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if g[r][c] == 0}
    if not hole: return None
    hn = _norm(hole); fits = [o for o in obs if o is not blk and _norm(o) == hn]
    return (blk, hole, fits[0]) if len(fits) == 1 else None
def gi_hole_crop(rng):
    return _hole_scene(rng, 2, 4)
def tf_hole_crop(g):
    p = _hole_parts(g)
    return crop(g, *bbox(p[2])) if p else None
rule("crop_piece_fitting_hole", "Output the one loose piece whose shape exactly fits the hole cut out of the big block.", gi_hole_crop, tf_hole_crop)
def gi_hole_move(rng):
    return _hole_scene(rng, 2, 3)
def tf_hole_move(g):
    p = _hole_parts(g)
    if not p: return None
    blk, hole, piece = p; out = copy(g); col = _col(g, piece)
    for r, c in piece: out[r][c] = 0
    for r, c in hole: out[r][c] = col
    return out
rule("move_piece_into_hole", "The loose piece that fits the hole in the big block is moved into the hole, leaving its old place empty.", gi_hole_move, tf_hole_move)


# 4 / 5 align in row bands
def _bands(rng, k_lo=2, k_hi=5, wmax=30):
    big = _big(rng); k = rng.randint(k_lo, k_hi + (2 if big else 0)); shapes = [_shape(rng, 2, 7) for _ in range(k)]
    W = rng.randint(21, wmax) if big else rng.randint(max(_hw(s)[1] for s in shapes) + 2, 24)
    return _band_layout(rng, shapes, [rng.choice(COLOURS) for _ in shapes], W=W, big=big)
def _reposition(g, where):
    H, W = dims(g); out = blank(H, W)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o); nr, nc = where(r0, c0, r1 - r0 + 1, c1 - c0 + 1, H, W)
        for r, c in o: out[r - r0 + nr][c - c0 + nc] = _col(g, o)
    return out
rule("align_objects_left_edge", "Every object slides horizontally until it touches the left edge, keeping its rows.", _bands,
     lambda g: _reposition(g, lambda r0, c0, h, w, H, W: (r0, 0)))
rule("align_objects_centre_column", "Every object slides horizontally so it is centred on the grid's middle column, keeping its rows.", _bands,
     lambda g: _reposition(g, lambda r0, c0, h, w, H, W: (r0, (W - w) // 2)))


# 6 / 7 / 8 lineups sorted by a property
def _lineup(g, key):
    obs = sorted(objects(g, 0), key=key); ks = [key(o) for o in obs]
    if len(set(ks)) != len(ks): return None
    shs = [(_norm(o), _col(g, o)) for o in obs]
    H = max(_hw(s)[0] for s, _ in shs); W = sum(_hw(s)[1] for s, _ in shs) + len(shs) - 1
    out = blank(H, W); c = 0
    for s, col in shs:
        h, w = _hw(s); _stamp(out, s, H - h, c, col); c += w + 1
    return out
def _row_scene(rng, k_lo=3, k_hi=5, lo=2, hi=7, distinct_cols=False, key=None):
    k = rng.randint(k_lo, k_hi); shapes = _distinct(rng, k, lo, hi, key=key) if key else [_shape(rng, lo, hi) for _ in range(k)]
    if shapes is None: return None
    cols_ = colours(rng, k) if distinct_cols else [rng.choice(COLOURS) for _ in shapes]
    return _row_layout(rng, shapes, cols_)
rule("lineup_by_height", "The objects are lined up bottom-aligned one column apart, shortest on the left and tallest on the right.",
     lambda rng: _row_scene(rng, key=lambda s: _hw(s)[0]), lambda g: _lineup(g, _bh))
rule("lineup_by_colour_value", "The objects are lined up bottom-aligned one column apart in increasing order of their colour number.",
     lambda rng: _row_scene(rng, distinct_cols=True), lambda g: _lineup(g, lambda o: _col(g, o)), digits=True)
rule("lineup_by_cell_count", "The objects are lined up bottom-aligned one column apart, fewest cells on the left and most on the right.",
     lambda rng: _row_scene(rng, lo=2, hi=9, key=len), lambda g: _lineup(g, len))


# 9 slots down the left column, filled in left-to-right object order
def gi_left_slots(rng):
    big = _big(rng); k = rng.randint(2, 5 if big else 4); shapes = []
    while len(shapes) < k:
        s = _shape(rng, 2, 6)
        if max(_hw(s)) <= 4: shapes.append(s)
    rows_ = []; r = rng.randint(0, 1)
    for _ in range(k):
        rows_.append(r); r += 5 + rng.randint(0, 1)
    if rows_[-1] + 4 > 30: return None
    H = rng.randint(max(21, rows_[-1] + 4), 30) if big else rng.randint(rows_[-1] + 4, min(30, rows_[-1] + 7))
    W = rng.randint(21, 30) if big else rng.randint(12, 24); g = blank(H, W)
    for r in rows_: g[r][0] = 5
    lefts = set()
    for sh in shapes:
        p = _put(rng, g, sh, rng.choice([c for c in COLOURS if c != 5]), cols_=(2, W))
        if p is None or p[1] in lefts: return None
        lefts.add(p[1])
    return g
def tf_left_slots(g):
    H, W = dims(g); slots = sorted(r for r in range(H) if g[r][0] == 5)
    obs = sorted([o for o in objects(g, 0) if _col(g, o) != 5], key=lambda o: bbox(o)[1])
    if len(obs) != len(slots): return None
    out = blank(H, W)
    for r in slots: out[r][0] = 5
    for o, r in zip(obs, slots):
        r0, c0, _, _ = bbox(o)
        for y, x in o: out[y - r0 + r][x - c0 + 1] = _col(g, o)
    return out
rule("fill_left_slots_in_column_order", "Grey markers down the left edge are slots; the objects move beside them top to bottom in their left-to-right order.", gi_left_slots, tf_left_slots)


# 10 orthogonally convex fill
def _ortho_close(o):
    cs = set(o)
    while True:
        new = set(cs)
        for r in {r for r, _ in cs}:
            xs = [c for rr, c in cs if rr == r]; new |= {(r, c) for c in range(min(xs), max(xs) + 1)}
        for c in {c for _, c in cs}:
            ys = [r for r, cc in cs if cc == c]; new |= {(r, c) for r in range(min(ys), max(ys) + 1)}
        if new == cs: return cs
        cs = new
def gi_ortho(rng):
    k = rng.randint(2, 5); shapes = [_shape(rng, 5, 11) for _ in range(k)]
    if all(_ortho_close(s) == s for s in shapes): return None
    return _scatter(rng, shapes, [rng.choice(COLOURS) for _ in range(k)], 9, 20)
def tf_ortho(g):
    out = copy(g)
    for o in objects(g, 0):
        for r, c in _ortho_close(o): out[r][c] = _col(g, o)
    return out
rule("fill_to_orthogonal_convex", "Every object is filled in until each of its rows and columns is one unbroken run of cells.", gi_ortho, tf_ortho)


# 11 recolour by shape class
def _class_shape(rng, kind):
    if kind == 0: s = {(0, i) for i in range(rng.randint(2, 6))}
    elif kind == 1: a, b = rng.randint(2, 4), rng.randint(2, 4); s = {(i, 0) for i in range(a)} | {(a - 1, j) for j in range(b)}
    elif kind == 2: b = rng.choice([3, 5]); s = {(0, j) for j in range(b)} | {(i, b // 2) for i in range(rng.randint(2, 4))}
    elif kind == 3: n = rng.randint(2, 4); s = {(i, j) for i in range(n) for j in range(n)}
    else: a = rng.randint(1, 2); s = {(a, j) for j in range(2 * a + 1)} | {(i, a) for i in range(2 * a + 1)}
    s = _norm(s)
    for _ in range(rng.randint(0, 3)): s = _rot(s)
    return s
def _classify(sh):
    h, w = _hw(sh)
    if h == 1 or w == 1: return 1
    if h == w and len(sh) == h * w: return 4
    if h == w and h % 2 and sh == {(h // 2, c) for c in range(w)} | {(r, w // 2) for r in range(h)}: return 5
    for er in (0, h - 1):
        row = {(er, c) for c in range(w)}
        for ec in (0, w - 1):
            if sh == row | {(r, ec) for r in range(h)}: return 2
        if w % 2 and sh == row | {(r, w // 2) for r in range(h)}: return 3
    for ec in (0, w - 1):
        if h % 2 and sh == {(r, ec) for r in range(h)} | {(h // 2, c) for c in range(w)}: return 3
    return None
def gi_classes(rng):
    k = rng.randint(3, 6); kinds = [rng.randrange(5) for _ in range(k)]
    if len(set(kinds)) < 2: return None
    col = rng.randint(6, 9)
    return _scatter(rng, [_class_shape(rng, kd) for kd in kinds], [col] * k, 10, 22)
def tf_classes(g):
    out = copy(g)
    for o in objects(g, 0):
        k = _classify(_norm(o))
        if k is None: return None
        for r, c in o: out[r][c] = k
    return out
rule("recolour_by_shape_class", "Each shape is recoloured by its kind: straight lines 1, L shapes 2, T shapes 3, solid squares 4, plus signs 5.", gi_classes, tf_classes)


# 12 shape common to every panel
def gi_panels_common(rng):
    if _big(rng):
        k = rng.randint(2, 3); ph = rng.randint(21, 30); pw = rng.randint(-(-(22 - k) // k), (31 - k) // k)
    else:
        k = rng.randint(2, 4); ph, pw = rng.randint(7, 11), rng.randint(7, 10)
    if k * pw + k - 1 > 30: return None
    common = _shape(rng, 3, 5); panels = []
    for _ in range(k):
        p = blank(ph, pw); shs = _distinct(rng, rng.randint(1, 2), 3, 5, avoid=[common]) or []
        shs.append(common); rng.shuffle(shs); cs = colours(rng, len(shs), exclude=(0, 5))
        for s, col in zip(shs, cs):
            if _put(rng, p, s, col) is None: return None
        panels.append(p)
    return [sum([p[r] + ([5] if i < k - 1 else []) for i, p in enumerate(panels)], []) for r in range(ph)]
def tf_panels_common(g):
    H, W = dims(g); seps = [c for c in range(W) if g[0][c] and all(g[r][c] == g[0][c] for r in range(H))]
    b = [-1] + seps + [W]; panels = [crop(g, 0, a + 1, H - 1, z - 1) for a, z in zip(b, b[1:]) if z - a > 1]
    sets = [{_norm(o): _col(p, o) for o in objects(p, 0)} for p in panels]
    common = set(sets[0])
    for s in sets[1:]: common &= set(s)
    if len(common) != 1: return None
    sh = common.pop(); h, w = _hw(sh)
    return _stamp(blank(h, w), sh, 0, 0, sets[0][sh])
rule("crop_shape_common_to_all_panels", "The grid is split into panels; output the one shape that appears in every panel, in its colour from the leftmost panel.", gi_panels_common, tf_panels_common)


# 13 / 38 rotation families
def _families(rng, sizes):
    groups, canons = [], set()
    for m in sizes:
        for _ in range(100):
            s = _shape(rng, 3, 5)
            if _canon(s) not in canons: break
        else: return None
        canons.add(_canon(s)); groups += [rng.choice(_rots(s)) for _ in range(m)]
    rng.shuffle(groups)
    return _scatter(rng, groups, [rng.choice(COLOURS) for _ in groups], 10, 22)
def gi_uniq_rot(rng):
    return _families(rng, [rng.randint(2, 3) for _ in range(rng.randint(1, 2))] + [1])
def tf_uniq_rot(g):
    obs = objects(g, 0); cnt = {}
    for o in obs: cnt[_canon(_norm(o))] = cnt.get(_canon(_norm(o)), 0) + 1
    singles = [o for o in obs if cnt[_canon(_norm(o))] == 1]
    return crop(g, *bbox(singles[0])) if len(singles) == 1 else None
rule("crop_shape_unique_under_rotation", "Shapes come in rotated families; output the one shape that has no rotated copy anywhere.", gi_uniq_rot, tf_uniq_rot)
def gi_big_family(rng):
    return _families(rng, rng.sample([1, 2, 3, 4], rng.randint(2, 3)))
def tf_big_family(g):
    obs = objects(g, 0); cnt = {}
    for o in obs: cnt[_canon(_norm(o))] = cnt.get(_canon(_norm(o)), 0) + 1
    best = max(cnt.values())
    if list(cnt.values()).count(best) != 1: return None
    o = min((o for o in obs if cnt[_canon(_norm(o))] == best), key=lambda o: bbox(o)[:2])
    return crop(g, *bbox(o))
rule("crop_most_common_rotation_family", "Shapes come in rotated families; output the topmost member of the family with the most members.", gi_big_family, tf_big_family)


# 14 largest bounding box (not the most cells)
def gi_bigbox(rng):
    k = rng.randint(3, 5); g = _scatter(rng, [_shape(rng, 3, 9) for _ in range(k)], [rng.choice(COLOURS) for _ in range(k)], 10, 20)
    if g is None: return None
    obs = objects(g, 0); areas = sorted(_bh(o) * _bw(o) for o in obs)
    if areas[-1] == areas[-2]: return None
    return g if max(obs, key=lambda o: _bh(o) * _bw(o)) is not max(obs, key=len) else None
def tf_bigbox(g):
    return crop(g, *bbox(max(objects(g, 0), key=lambda o: _bh(o) * _bw(o))))
rule("crop_largest_bounding_box", "Output the object whose bounding rectangle covers the most area, even if another object has more cells.", gi_bigbox, tf_bigbox)


# 15 recolour by left-edge order
def gi_leftorder(rng):
    k = rng.randint(2, 6); g = _scatter(rng, [_shape(rng, 2, 7) for _ in range(k)], [rng.choice(COLOURS) for _ in range(k)], 8, 20)
    if g is None: return None
    lefts = [bbox(o)[1] for o in objects(g, 0)]
    return g if len(set(lefts)) == len(lefts) else None
def tf_leftorder(g):
    out = copy(g)
    for i, o in enumerate(sorted(objects(g, 0), key=lambda o: bbox(o)[1])):
        for r, c in o: out[r][c] = i + 1
    return out
rule("recolour_by_left_edge_order", "Objects are numbered by their left edge: the leftmost becomes 1, the next 2, and so on.", gi_leftorder, tf_leftorder, digits=True)


# 16 most corners
def _corners(cs):
    s = set(cs); r0, c0, r1, c1 = bbox(cs); n = 0
    for r in range(r0, r1 + 2):
        for c in range(c0, c1 + 2):
            q = [(r - 1, c - 1) in s, (r - 1, c) in s, (r, c - 1) in s, (r, c) in s]; k = sum(q)
            n += 1 if k in (1, 3) else (2 if k == 2 and q[0] == q[3] else 0)
    return n
def gi_corners(rng):
    k = rng.randint(2, 5); g = _scatter(rng, [_shape(rng, 2, 9) for _ in range(k)], [rng.choice(COLOURS[1:]) for _ in range(k)], 9, 20)
    if g is None: return None
    cs = sorted(_corners(o) for o in objects(g, 0))
    return g if cs[-1] != cs[-2] else None
def tf_corners(g):
    out = copy(g)
    for r, c in max(objects(g, 0), key=_corners): out[r][c] = 1
    return out
rule("mark_object_with_most_corners", "The object whose outline has the most corners is recoloured 1; the rest are unchanged.", gi_corners, tf_corners)


# 17 snap to a lattice of step 5
def gi_lattice(rng):
    s = 5; big = _big(rng); ni, nj = (rng.randint(4, 5), rng.randint(4, 5)) if big else (rng.randint(2, 5), rng.randint(2, 5))
    H, W = ni * s + rng.randint(1 if big else 0, 5), nj * s + rng.randint(1 if big else 0, 5)
    if H > 30 or W > 30: return None
    g = blank(H, W); spots = [(i, j) for i in range(ni) for j in range(nj)]
    for i, j in rng.sample(spots, rng.randint(2, min(7, len(spots)))):
        while True:
            sh = _shape(rng, 2, 5)
            if max(_hw(sh)) <= 3: break
        _stamp(g, sh, i * s + rng.randint(0, 1), j * s + rng.randint(0, 1), rng.choice(COLOURS))
    return g
def tf_lattice(g):
    H, W = dims(g); out = blank(H, W)
    for o in objects(g, 0):
        r0, c0, _, _ = bbox(o)
        for r, c in o: out[r - r0 % 5][c - c0 % 5] = _col(g, o)
    return out
rule("snap_objects_to_lattice", "Every object moves up and left so its top-left corner lands on the nearest row and column that are multiples of five.", gi_lattice, tf_lattice)


# 18 stretch the smallest rectangle to the largest's size
def tf_stretch(g):
    obs = objects(g, 0); area = lambda o: _bh(o) * _bw(o)
    small, big = min(obs, key=area), max(obs, key=area); H, W = dims(g)
    r0, c0, _, _ = bbox(small); bh, bw = _bh(big), _bw(big)
    if r0 + bh > H or c0 + bw > W: return None
    cells_ = {(r, c) for r in range(r0, r0 + bh) for c in range(c0, c0 + bw)}
    if cells_ & {rc for o in obs if o is not small for rc in o}: return None
    out = copy(g)
    for r, c in cells_: out[r][c] = _col(g, small)
    return out
def gi_stretch(rng):
    h, w = _size(rng, 10, 22); g = blank(h, w); k = rng.randint(2, 4); areas = []
    for _ in range(k):
        rh, rw = rng.randint(1, 5), rng.randint(1, 5)
        if _put(rng, g, frozenset((r, c) for r in range(rh) for c in range(rw)), rng.choice(COLOURS)) is None: return None
        areas.append(rh * rw)
    areas.sort()
    if areas[0] == areas[1] or areas[-1] == areas[-2]: return None
    return g if tf_stretch(g) is not None else None
rule("stretch_smallest_rect_to_largest", "The smallest rectangle grows from its top-left corner until it is the same height and width as the largest rectangle.", gi_stretch, tf_stretch)


# 19 align against a marker line
def gi_marker_line(rng):
    g = _bands(rng, 2, 5, wmax=26)
    if g is None: return None
    W = len(g[0]); a = rng.randint(0, min(3, 29 - W - 1)); b = rng.randint(1, min(3, 29 - W - a))
    return [[0] * a + [5] + [0] * b + row for row in g]
def tf_marker_line(g):
    H, W = dims(g); m = next(c for c in range(W) if all(g[r][c] == 5 for r in range(H)))
    out = blank(H, W)
    for r in range(H): out[r][m] = 5
    for o in components(g, lambda v: v not in (0, 5), conn8=True):
        c0 = bbox(o)[1]
        for r, c in o: out[r][c - c0 + m + 1] = _col(g, o)
    return out
rule("align_objects_against_marker_line", "Every object slides left until it touches the grey vertical line, keeping its rows.", gi_marker_line, tf_marker_line)


# 20 stack by width
def gi_stackw(rng):
    k = rng.randint(3, 5); g = _scatter(rng, [_shape(rng, 2, 7) for _ in range(k)], [rng.choice(COLOURS) for _ in range(k)], 9, 20)
    if g is None: return None
    ws = [_bw(o) for o in objects(g, 0)]
    return g if len(set(ws)) == len(ws) else None
def tf_stackw(g):
    obs = sorted(objects(g, 0), key=_bw); shs = [(_norm(o), _col(g, o)) for o in obs]
    H = sum(_hw(s)[0] for s, _ in shs) + len(shs) - 1; W = max(_hw(s)[1] for s, _ in shs); out = blank(H, W); r = 0
    for s, col in shs:
        _stamp(out, s, r, 0, col); r += _hw(s)[0] + 1
    return out
rule("stack_objects_by_width", "The objects are stacked top to bottom against the left edge, one row apart, narrowest on top and widest at the bottom.", gi_stackw, tf_stackw)


# 21 identical shapes share a colour, numbered by the group's topmost member
def gi_shape_groups(rng):
    k = rng.randint(2, 3); base = _distinct(rng, k, 3, 6)
    if base is None: return None
    mult = [rng.randint(1, 3) for _ in base]
    if max(mult) < 2: return None
    shapes = [s for s, m in zip(base, mult) for _ in range(m)]; rng.shuffle(shapes)
    return _scatter(rng, shapes, [8] * len(shapes), 10, 22)
def tf_shape_groups(g):
    obs = objects(g, 0); top = {}
    for o in obs: top[_norm(o)] = min(top.get(_norm(o), 99), bbox(o)[0])
    order = {n: i + 1 for i, n in enumerate(sorted(top, key=lambda n: (top[n], sorted(n))))}
    out = copy(g)
    for o in obs:
        for r, c in o: out[r][c] = order[_norm(o)]
    return out
rule("recolour_by_shape_group_order", "Identical shapes share a colour: the group whose member is highest gets 1, the next group 2, and so on.", gi_shape_groups, tf_shape_groups)


# 22 / 34 template matches: count bar, keep only
def _tmpl_scene(rng, m_lo, m_hi):
    t = _shape(rng, 3, 6); m = rng.randint(m_lo, m_hi); d = rng.randint(0, 3)
    others = _distinct(rng, d, 3, 6, key=_canon, avoid=[_canon(t)]) if d else []
    if others is None: return None
    T = rng.choice([c for c in COLOURS if c != 8])
    shapes = [t] + [rng.choice(_rots(t)) for _ in range(m)] + others
    return _scatter(rng, shapes, [T] + [8] * (len(shapes) - 1), 10, 22)
def _tmpl_hits(g):
    obs = objects(g, 0); tm = [o for o in obs if _col(g, o) != 8]
    if len(tm) != 1: return None
    tc = _canon(_norm(tm[0]))
    return _col(g, tm[0]), [o for o in obs if _col(g, o) == 8 and _canon(_norm(o)) == tc]
def tf_tmpl_count(g):
    p = _tmpl_hits(g)
    return [[p[0]] * len(p[1]) + [0]] if p and p[1] else None
rule("template_rotation_match_count_bar", "Output one row in the template's colour as long as the number of grey objects that are rotated copies of it, followed by one empty cell.",
     lambda rng: _tmpl_scene(rng, 1, 6), tf_tmpl_count)
def tf_tmpl_keep(g):
    p = _tmpl_hits(g)
    if not p or not p[1]: return None
    H, W = dims(g); out = blank(H, W)
    for o in p[1]:
        for r, c in o: out[r][c] = p[0]
    return out
rule("keep_only_template_matches", "Only the grey objects that are rotated copies of the coloured template remain, repainted in the template's colour.",
     lambda rng: _tmpl_scene(rng, 1, 3), tf_tmpl_keep)


# 24 align tops to the tallest
def gi_tops(rng):
    g = _row_scene(rng, 3, 5, 2, 7)
    if g is None: return None
    hs = sorted(_bh(o) for o in objects(g, 0))
    return g if hs[-1] != hs[-2] else None
def tf_tops(g):
    top = bbox(max(objects(g, 0), key=_bh))[0]
    return _reposition(g, lambda r0, c0, h, w, H, W: (top, c0))
rule("align_tops_to_tallest", "Every object moves straight up or down so its top row is level with the top of the tallest object.", gi_tops, tf_tops)


# 25 mirror the positions, not the shapes
def gi_mirpos(rng):
    k = rng.randint(2, 5); shapes = [_shape(rng, 3, 6) for _ in range(k)]
    if all(_flip(s) == s for s in shapes): return None
    return _scatter(rng, shapes, [rng.choice(COLOURS) for _ in shapes], 8, 20)
def tf_mirpos(g):
    return _reposition(g, lambda r0, c0, h, w, H, W: (r0, W - c0 - w))
rule("mirror_positions_not_shapes", "Each object moves to the mirror-image position across the grid's vertical centre line without being flipped itself.", gi_mirpos, tf_mirpos)


# 26 solid versus sparse bounding boxes
def gi_solid(rng):
    k = rng.randint(3, 6); shapes = []
    for _ in range(k):
        if rng.random() < 0.45:
            rh, rw = rng.randint(1, 4), rng.randint(1, 4); shapes.append(frozenset((r, c) for r in range(rh) for c in range(rw)))
        else:
            s = _shape(rng, 3, 7); h, w = _hw(s)
            if len(s) < h * w: shapes.append(s)
    kinds = {len(s) == _hw(s)[0] * _hw(s)[1] for s in shapes}
    if len(kinds) < 2: return None
    return _scatter(rng, shapes, [rng.choice(COLOURS[2:]) for _ in shapes], 9, 20)
def tf_solid(g):
    out = copy(g)
    for o in objects(g, 0):
        v = 1 if len(o) == _bh(o) * _bw(o) else 2
        for r, c in o: out[r][c] = v
    return out
rule("recolour_solid_vs_sparse", "Objects that completely fill their bounding rectangle become 1; objects that leave gaps in it become 2.", gi_solid, tf_solid)


# 27 tallest object
def gi_tallest(rng):
    k = rng.randint(3, 5); g = _scatter(rng, [_shape(rng, 2, 8) for _ in range(k)], [rng.choice(COLOURS) for _ in range(k)], 9, 20)
    if g is None: return None
    hs = sorted(_bh(o) for o in objects(g, 0))
    return g if hs[-1] != hs[-2] else None
def tf_tallest(g):
    return crop(g, *bbox(max(objects(g, 0), key=_bh)))
rule("crop_tallest_object", "Output the bounding box of the object that spans the most rows.", gi_tallest, tf_tallest)


# 28 / 35 slots along the top row
def _top_slots(rng, k, maxw, same_col):
    cols_ = [5] * k if same_col else colours(rng, k, exclude=(0, 5)); big = _big(rng)
    xs = []; x = rng.randint(0, 2)
    for _ in range(k):
        xs.append(x); x += maxw + rng.randint(1, 3 if big else 2)
    if xs[-1] + maxw > 30: return None
    W = rng.randint(max(21, xs[-1] + maxw), 30) if big else rng.randint(xs[-1] + maxw, min(30, xs[-1] + maxw + 3))
    H = rng.randint(21, 30) if big else rng.randint(10, 22); g = blank(H, W)
    for x, col in zip(xs, cols_): g[0][x] = col
    return g, xs, cols_
def gi_colour_slots(rng):
    k = rng.randint(2, 4); t = _top_slots(rng, k, 4, False)
    if t is None: return None
    g, xs, cols_ = t; order = list(range(k)); rng.shuffle(order)
    for i in order:
        while True:
            s = _shape(rng, 2, 6)
            if max(_hw(s)) <= 4: break
        if _put(rng, g, s, cols_[i], rows=(2, 99)) is None: return None
    return g
def tf_colour_slots(g):
    H, W = dims(g); out = blank(H, W); slot = {g[0][c]: c for c in range(W) if g[0][c]}
    for c in range(W): out[0][c] = g[0][c]
    for o in [o for o in objects(g, 0) if bbox(o)[0] > 0]:
        r0, c0, _, _ = bbox(o); x = slot.get(_col(g, o))
        if x is None or x + _bw(o) > W: return None
        for r, c in o: out[r - r0 + 1][c - c0 + x] = _col(g, o)
    return out
rule("objects_move_under_colour_slots", "Each object moves up to hang directly under the top-row marker of its own colour.", gi_colour_slots, tf_colour_slots)
def gi_size_slots(rng):
    k = rng.randint(2, 4); t = _top_slots(rng, k, 4, True)
    if t is None: return None
    g, xs, cols_ = t; ns = rng.sample(range(2, 9), k)
    for n in ns:
        while True:
            s = _norm(set(random_shape(rng, n)))
            if max(_hw(s)) <= 4: break
        if _put(rng, g, s, rng.choice([c for c in COLOURS if c != 5]), rows=(2, 99)) is None: return None
    return g
def tf_size_slots(g):
    H, W = dims(g); out = blank(H, W); xs = [c for c in range(W) if g[0][c] == 5]
    for x in xs: out[0][x] = 5
    obs = sorted([o for o in objects(g, 0) if bbox(o)[0] > 0], key=len)
    if len(obs) != len(xs) or len({len(o) for o in obs}) != len(obs): return None
    for o, x in zip(obs, xs):
        r0, c0, _, _ = bbox(o)
        if x + _bw(o) > W: return None
        for r, c in o: out[r - r0 + 1][c - c0 + x] = _col(g, o)
    return out
rule("top_slots_filled_by_size_order", "Grey markers along the top row are slots; the objects hang under them left to right from fewest cells to most.", gi_size_slots, tf_size_slots)


# 29 pack left within each band
def gi_pack(rng):
    big = _big(rng); W = rng.randint(21, 30) if big else rng.randint(12, 28); rows = []; nb = rng.randint(2, 4); target = rng.randint(21, 29)
    while len(rows) < target if big else nb > 0:
        nb -= 1; shs = [_shape(rng, 2, 6) for _ in range(rng.randint(1, 3))]; hb = max(_hw(s)[0] for s in shs) + rng.randint(0, 1)
        band = blank(hb, W); c = rng.randint(0, 3)
        for s in shs:
            h, w = _hw(s)
            if c + w > W: break
            _stamp(band, s, rng.randint(0, hb - h), c, rng.choice(COLOURS)); c += w + rng.randint(2, 4)
        if len(rows) + hb > 30: break
        rows += band + [[0] * W]
    return rows[:-1]
def tf_pack(g):
    H, W = dims(g); out = blank(H, W); obs = objects(g, 0); band = [0] * H; b = 0
    for r in range(H):
        if any(g[r]): band[r] = b
        elif r and any(g[r - 1]): b += 1
    for k in range(b + 1):
        c = 0
        for o in sorted([o for o in obs if band[bbox(o)[0]] == k and any(g[bbox(o)[0]])], key=lambda o: bbox(o)[1]):
            c0 = bbox(o)[1]
            for r, x in o: out[r][x - c0 + c] = _col(g, o)
            c += _bw(o) + 1
    return out
rule("pack_objects_left_in_bands", "Within each horizontal band the objects slide left in order until they sit one column apart from the left edge.", gi_pack, tf_pack)


# 30 rotate grey objects to the template's orientation
def tf_rot_align(g):
    obs = objects(g, 0); tm = [o for o in obs if _col(g, o) != 8]
    if len(tm) != 1: return None
    t = _norm(tm[0]); H, W = dims(g); out = copy(g); taken = set(tm[0]); h, w = _hw(t)
    greys = [o for o in obs if _col(g, o) == 8]
    for o in greys:
        for r, c in o: out[r][c] = 0
    for o in greys:
        if _canon(_norm(o)) != _canon(t): return None
        r0, c0, _, _ = bbox(o)
        if r0 + h > H or c0 + w > W: return None
        new = {(r0 + r, c0 + c) for r, c in t}
        if new & taken: return None
        taken |= new
        for r, c in new: out[r][c] = 8
    return out
def gi_rot_align(rng):
    for _ in range(20):
        t = _shape(rng, 3, 6)
        if len(set(_rots(t))) == 4: break
    else: return None
    k = rng.randint(2, 4); h, w = _size(rng, 10, 20); g = blank(h, w); T = rng.choice([c for c in COLOURS if c != 8])
    if _put(rng, g, t, T) is None: return None
    for _ in range(k):
        if _put(rng, g, rng.choice(_rots(t)[1:]), 8, margin=2) is None: return None
    return g if tf_rot_align(g) is not None else None
rule("rotate_objects_to_template_orientation", "Every grey object is a rotated copy of the coloured template; each is turned in place, about its top-left corner, to match the template's orientation.", gi_rot_align, tf_rot_align)


# 31 centre the object inside its frame
def gi_centre_frame(rng):
    big = _big(rng); fh, fw = rng.randint(6, 24 if big else 14), rng.randint(6, 24 if big else 14)
    h, w = (rng.randint(max(21, fh), 30), rng.randint(max(21, fw), 30)) if big else (rng.randint(fh, min(30, fh + 6)), rng.randint(fw, min(30, fw + 6)))
    g = blank(h, w); F, O = colours(rng, 2); r0, c0 = rng.randint(0, h - fh), rng.randint(0, w - fw)
    rect(g, r0, c0, r0 + fh - 1, c0 + fw - 1, F, fill=False)
    for _ in range(30):
        s = _shape(rng, 2, 6); sh, sw = _hw(s)
        if sh <= fh - 3 and sw <= fw - 3: break
    else: return None
    _stamp(g, s, rng.randint(r0 + 1, r0 + fh - 1 - sh), rng.randint(c0 + 1, c0 + fw - 1 - sw), O)
    return g
def tf_centre_frame(g):
    obs = objects(g, 0)
    if len(obs) != 2: return None
    frame = max(obs, key=len); o = min(obs, key=len); r0, c0, r1, c1 = bbox(frame); ih, iw = r1 - r0 - 1, c1 - c0 - 1
    out = copy(g)
    for r, c in o: out[r][c] = 0
    y0, x0, _, _ = bbox(o); ny, nx = r0 + 1 + (ih - _bh(o)) // 2, c0 + 1 + (iw - _bw(o)) // 2
    for r, c in o: out[r - y0 + ny][c - x0 + nx] = _col(g, o)
    return out
rule("centre_object_in_frame", "The object inside the hollow frame is moved to the centre of the frame's interior.", gi_centre_frame, tf_centre_frame)


# 32 mirror-image pairs recoloured
def gi_mirror_groups(rng):
    p = rng.randint(1, 2); bases = []
    while len(bases) < p:
        s = _shape(rng, 3, 6)
        if _flip(s) != s and all(s not in (b, _flip(b)) for b in bases): bases.append(s)
    avoid = [x for b in bases for x in (b, _flip(b))]
    singles = _distinct(rng, rng.randint(1, 3), 3, 6, avoid=avoid) or []
    if any(_flip(s) in avoid or _flip(s) in singles for s in singles): return None
    shapes = [x for b in bases for x in (b, _flip(b))] + singles; rng.shuffle(shapes)
    return _scatter(rng, shapes, [8] * len(shapes), 10, 22)
def tf_mirror_groups(g):
    obs = objects(g, 0); by = {}
    for o in obs: by.setdefault(_norm(o), []).append(o)
    if any(len(v) > 1 for v in by.values()): return None
    pairs = {frozenset((n, _flip(n))) for n in by if _flip(n) != n and _flip(n) in by}
    if not pairs: return None
    order = sorted(pairs, key=lambda pr: min(bbox(by[n][0])[1] for n in pr)); out = copy(g)
    for i, pr in enumerate(order):
        for n in pr:
            for r, c in by[n][0]: out[r][c] = i + 1
    return out
rule("recolour_mirror_pairs", "Two grey objects that are mirror images of each other form a pair; the leftmost pair becomes 1, the next 2; unpaired objects stay grey.", gi_mirror_groups, tf_mirror_groups, digits=True)


# 33 recolour by height
def gi_height(rng):
    k = rng.randint(2, 5); g = _scatter(rng, [_shape(rng, 2, 8) for _ in range(k)], [rng.choice(COLOURS) for _ in range(k)], 8, 20)
    if g is None: return None
    hs = [_bh(o) for o in objects(g, 0)]
    return g if len(set(hs)) > 1 and max(hs) <= 9 else None
def tf_height(g):
    out = copy(g)
    for o in objects(g, 0):
        for r, c in o: out[r][c] = _bh(o)
    return out
rule("recolour_by_bbox_height", "Every object is recoloured with the number of rows it spans.", gi_height, tf_height, digits=True)


# 36 the odd shape under rotation
def gi_odd_rot(rng):
    s = _shape(rng, 3, 6); k = rng.randint(2, 5)
    odd = _distinct(rng, 1, 3, 6, key=_canon, avoid=[_canon(s)])
    if odd is None: return None
    shapes = [rng.choice(_rots(s)) for _ in range(k)] + odd; rng.shuffle(shapes)
    return _scatter(rng, shapes, [rng.choice(COLOURS[2:]) for _ in shapes], 9, 22)
def tf_odd_rot(g):
    obs = objects(g, 0); cnt = {}
    for o in obs: cnt[_canon(_norm(o))] = cnt.get(_canon(_norm(o)), 0) + 1
    odd = [o for o in obs if cnt[_canon(_norm(o))] == 1]
    if len(odd) != 1 or len(cnt) != 2: return None
    out = copy(g)
    for r, c in odd[0]: out[r][c] = 2
    return out
rule("recolour_odd_shape_under_rotation", "All objects are rotated copies of one shape except one; that odd object is recoloured 2.", gi_odd_rot, tf_odd_rot)


# 37 convex hull fill
def _hull_fill(cs):
    pts = sorted(set(cs))
    if len(pts) < 3: return set(pts)
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and cross(h[-2], h[-1], p) <= 0: h.pop()
            h.append(p)
        return h
    hull = half(pts)[:-1] + half(pts[::-1])[:-1]; r0, c0, r1, c1 = bbox(pts)
    return {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)
            if all(cross(hull[i], hull[(i + 1) % len(hull)], (r, c)) >= 0 for i in range(len(hull)))}
def gi_hull(rng):
    k = rng.randint(2, 5); shapes = [_shape(rng, 5, 10) for _ in range(k)]
    if all(_hull_fill(s) == set(s) for s in shapes): return None
    return _scatter(rng, shapes, [rng.choice(COLOURS) for _ in range(k)], 9, 20)
def tf_hull(g):
    out = copy(g)
    for o in objects(g, 0):
        for r, c in _hull_fill(o): out[r][c] = _col(g, o)
    return out
rule("fill_convex_hull", "Every object is filled out to its convex hull: any cell inside the tightest convex outline around the object is painted.", gi_hull, tf_hull)


# 39 objects jump onto their grey ghosts
def gi_ghosts(rng):
    k = rng.randint(2, 4); shapes = _distinct(rng, k, 3, 6)
    if shapes is None: return None
    cols_ = [rng.choice([c for c in COLOURS if c != 5]) for _ in shapes]
    pairs = list(zip(shapes + shapes, cols_ + [5] * k)); rng.shuffle(pairs)
    return _scatter(rng, [s for s, _ in pairs], [c for _, c in pairs], 10, 22)
def tf_ghosts(g):
    obs = objects(g, 0); ghosts = {}
    for o in obs:
        if _col(g, o) == 5: ghosts.setdefault(_norm(o), []).append(o)
    out = copy(g)
    for o in obs:
        if _col(g, o) == 5: continue
        gs = ghosts.get(_norm(o), [])
        if len(gs) != 1: return None
        for r, c in o: out[r][c] = 0
        for r, c in gs[0]: out[r][c] = _col(g, o)
    return out
rule("objects_jump_to_matching_ghosts", "Each coloured object jumps onto the grey outline of the same shape, which takes its colour; its old place is emptied.", gi_ghosts, tf_ghosts)


# 40 space evenly
def gi_even(rng):
    k = rng.randint(3, 5); shapes = [_shape(rng, 2, 6) for _ in range(k)]; ws = [_hw(s)[1] for s in shapes]
    big = _big(rng); g0 = max(1, -(-(21 - sum(ws)) // (k + 1))) if big else 1; g1 = (30 - sum(ws)) // (k + 1) if big else 3
    if g0 > g1: return None
    gap = rng.randint(g0, g1); W = sum(ws) + (k + 1) * gap
    if W > 30: return None
    hs = [_hw(s)[0] for s in shapes]; H = rng.randint(21, 30) if big else rng.randint(max(hs), max(hs) + 5); g = blank(H, W)
    free = W - sum(ws); cuts = sorted(rng.sample(range(1, free + k), k)) if free + k - 1 >= k else None
    if cuts is None: return None
    gaps = [b - a - 1 for a, b in zip([0] + cuts, cuts + [free + k])]
    if any(x < 1 for x in gaps[1:-1]): return None
    c = gaps[0]
    for s, gp in zip(shapes, gaps[1:]):
        _stamp(g, s, rng.randint(0, H - _hw(s)[0]), c, rng.choice(COLOURS)); c += _hw(s)[1] + gp
    return g
def tf_even(g):
    H, W = dims(g); obs = sorted(objects(g, 0), key=lambda o: bbox(o)[1]); free = W - sum(_bw(o) for o in obs)
    if free % (len(obs) + 1): return None
    gap = free // (len(obs) + 1); out = blank(H, W); c = gap
    for o in obs:
        r0, c0, _, _ = bbox(o)
        for r, x in o: out[r][x - c0 + c] = _col(g, o)
        c += _bw(o) + gap
    return out
rule("space_objects_evenly", "The objects keep their order and rows but are respaced so the gaps between them and to both side edges are all equal.", gi_even, tf_even)
