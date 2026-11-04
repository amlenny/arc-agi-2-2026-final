# b017_interactions.py -- OBJECT INTERACTIONS, MERGING AND SPLITTING: touching objects merge, split at necks,
# absorb dots, swap or pass on colours, stop short of collisions, fuse across one-cell gaps. "Objects" are
# same-colour side-connected pieces; a "cluster" is a side-connected group of pieces regardless of colour.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

GREY = 5
N4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
N8 = N4 + [(-1, -1), (-1, 1), (1, -1), (1, 1)]
PAL = [c for c in COLOURS if c != GREY]


def _size(rng, lo=8, hi=18):
    """About a third of inputs land in the 21-30 band."""
    if rng.random() < 0.35: return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _col(g, cells_): return g[cells_[0][0]][cells_[0][1]]


def _paint(g, cells_, col):
    for r, c in cells_: g[r][c] = col


def _touch4(a, b):
    s = set(b); return any((r + dr, c + dc) in s for r, c in a for dr, dc in N4)


def _blobs(g, conn8=False):
    """Connected groups of non-empty cells regardless of colour (glib.components splits by colour)."""
    H, W = dims(g); seen = set(); out = []; nb = N8 if conn8 else N4
    for r in range(H):
        for c in range(W):
            if g[r][c] == 0 or (r, c) in seen: continue
            st = [(r, c)]; seen.add((r, c)); comp = []
            while st:
                y, x = st.pop(); comp.append((y, x))
                for dy, dx in nb:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and g[ny][nx] != 0 and (ny, nx) not in seen:
                        seen.add((ny, nx)); st.append((ny, nx))
            out.append(comp)
    return out


def _parts(g, blob):
    """Same-colour side-connected pieces of one blob."""
    s = set(blob); seen = set(); out = []
    for cell in sorted(blob):
        if cell in seen: continue
        col = g[cell[0]][cell[1]]; st = [cell]; seen.add(cell); comp = []
        while st:
            y, x = st.pop(); comp.append((y, x))
            for dy, dx in N4:
                n = (y + dy, x + dx)
                if n in s and n not in seen and g[n[0]][n[1]] == col: seen.add(n); st.append(n)
        out.append(comp)
    return out


def _objs(g): return components(g, lambda v: v != 0)


def _ring_ok(g, cells_, margin, allow=()):
    H, W = dims(g); al = set(allow)
    for r, c in cells_:
        for dr in range(-margin, margin + 1):
            for dc in range(-margin, margin + 1):
                nr, nc = r + dr, c + dc
                if 0 <= nr < H and 0 <= nc < W and g[nr][nc] != 0 and (nr, nc) not in al: return False
    return True


def _place_free(rng, g, shape, col, margin=1, tries=80):
    """Stamp shape where nothing lies within `margin` cells of it. Returns the cells (shape order) or None."""
    H, W = dims(g); h = max(r for r, _ in shape) + 1; w = max(c for _, c in shape) + 1
    if h > H or w > W: return None
    for _ in range(tries):
        r0, c0 = rng.randint(0, H - h), rng.randint(0, W - w)
        cells_ = [(r0 + r, c0 + c) for r, c in shape]
        if _ring_ok(g, cells_, margin):
            _paint(g, cells_, col); return cells_
    return None


def _attach(rng, g, anchor, allow, shape, col, margin=1, tries=60):
    """Stamp shape so one cell sits side-on to an anchor cell; nothing but `allow` within margin."""
    H, W = dims(g)
    for _ in range(tries):
        tr, tc = rng.choice(anchor); dr, dc = rng.choice(N4); sr, sc = rng.choice(shape)
        cells_ = [(tr + dr - sr + r, tc + dc - sc + c) for r, c in shape]
        if all(0 <= r < H and 0 <= c < W and g[r][c] == 0 for r, c in cells_) and _ring_ok(g, cells_, margin, allow):
            _paint(g, cells_, col); return cells_
    return None


def _shape(rng, lo=3, hi=8): return random_shape(rng, rng.randint(lo, hi))


def _rect(rng, hlo=2, hhi=4, wlo=2, whi=4):
    h, w = rng.randint(hlo, hhi), rng.randint(wlo, whi)
    return [(r, c) for r in range(h) for c in range(w)]


def _hw(sh): return max(r for r, _ in sh) + 1, max(c for _, c in sh) + 1


def _cluster_scene(rng, clusters=(1, 3), parts=(2, 3), lone=(0, 2), lo=8, hi=18, margin=1, rect=False, sizes=None, pal=PAL):
    """Groups of side-touching shapes of distinct colours, plus lone shapes. Returns (grid, groups) or None."""
    h, w = _size(rng, lo, hi); g = blank(h, w); groups = []
    shp = (lambda n: _rect(rng)) if rect else (lambda n: random_shape(rng, n))
    for _ in range(rng.randint(*clusters)):
        k = rng.randint(*parts); cols = rng.sample(pal, k)
        ns = rng.sample(range(3, 10), k) if sizes == "distinct" else [rng.randint(3, 8) for _ in range(k)]
        first = _place_free(rng, g, shp(ns[0]), cols[0], margin)
        if first is None: return None
        grp = [first]
        for i in range(1, k):
            nxt = _attach(rng, g, rng.choice(grp), [c for p in grp for c in p], shp(ns[i]), cols[i], margin)
            if nxt is None: return None
            grp.append(nxt)
        groups.append(grp)
    for _ in range(rng.randint(*lone)):
        _place_free(rng, g, shp(rng.randint(3, 8)), rng.choice(pal), margin)
    return g, groups


# 1 touching cluster takes the colour of its largest piece
def gi_merge_largest(rng):
    s = _cluster_scene(rng, (1, 3), (2, 3), (0, 2), sizes="distinct")
    return s[0] if s else None
def tf_merge_largest(g):
    out = copy(g); hit = False
    for b in _blobs(g):
        ps = sorted(_parts(g, b), key=len)
        if len(ps) < 2: continue
        if len(ps[-1]) == len(ps[-2]): return None
        _paint(out, b, _col(g, ps[-1])); hit = True
    return out if hit else None
rule("touching_cluster_takes_largest_part_colour", "Objects of different colours that touch merge into one object painted in the colour of the piece with the most cells; lone objects are unchanged.", gi_merge_largest, tf_merge_largest)


# 2 one-cell-wide neck erased; smaller piece turns grey
def _necked(rng):
    ha, wa, hb, wb = (rng.randint(2, 5) for _ in range(4))
    if ha * wa == hb * wb: return None
    L = rng.randint(1, 4); rr = rng.randrange(ha); tb = rr - rng.randrange(hb)
    cells_ = [(r, c) for r in range(ha) for c in range(wa)] + [(rr, wa + i) for i in range(L)] + [(tb + r, wa + L + c) for r in range(hb) for c in range(wb)]
    r0 = min(r for r, _ in cells_); sh = [(r - r0, c) for r, c in cells_]
    return [(c, r) for r, c in sh] if rng.random() < 0.5 else sh
def gi_neck(rng):
    h, w = _size(rng, 10, 18); g = blank(h, w); n = 0
    for _ in range(rng.randint(1, 3)):
        sh = _necked(rng)
        if sh and _place_free(rng, g, sh, rng.choice(PAL), 1): n += 1
    return g if n else None
def tf_neck(g):
    out = copy(g)
    for o in _objs(g):
        s = set(o)
        solid = {(r, c) for r, c in o if any(all((r + dr + i, c + dc + j) in s for i in (0, 1) for j in (0, 1)) for dr in (-1, 0) for dc in (-1, 0))}
        neck = s - solid
        if not neck or not solid: continue
        for r, c in neck: out[r][c] = 0
        ps = _parts(out, sorted(solid))
        if len(ps) != 2 or len(ps[0]) == len(ps[1]): return None
        _paint(out, min(ps, key=len), GREY)
    return out
rule("neck_cut_smaller_piece_grey", "Each object is two blocks joined by a one-cell-wide neck; the neck is erased and the smaller of the two blocks turns grey (5).", gi_neck, tf_neck)


# 3/4 rectangles in column slots; row-overlapping neighbours get a band
def _slots(rng, n, total, gap=1, lo=2, hi=6):
    lens = [rng.randint(lo, hi) for _ in range(n)]
    spare = total - sum(lens) - gap * (n - 1)
    if spare < 0: return None
    pads = [0] * (n + 1)
    for _ in range(spare): pads[rng.randrange(n + 1)] += 1
    out, pos = [], pads[0]
    for i, L in enumerate(lens):
        out.append((pos, pos + L - 1)); pos += L + gap + pads[i + 1]
    return out
def _slot_rects(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w); n = rng.randint(2, 4 if w < 21 else 6)
    sl = _slots(rng, n, w, gap=rng.randint(1, 3), lo=2, hi=5)
    if sl is None: return None
    for c0, c1 in sl:
        hh = rng.randint(2, max(2, h // 2)); r0 = rng.randint(0, h - hh)
        rect(g, r0, c0, r0 + hh - 1, c1, rng.choice([x for x in PAL if x != 8]))
    return g
def gi_rowband(rng):
    g = _slot_rects(rng)
    return g if g and tf_rowband(g) else None
def tf_rowband(g):
    out = copy(g); obs = sorted(_objs(g), key=lambda o: bbox(o)[1]); hit = False
    for a, b in zip(obs, obs[1:]):
        ar0, ac0, ar1, ac1 = bbox(a); br0, bc0, br1, bc1 = bbox(b)
        lo, hi = max(ar0, br0), min(ar1, br1)
        if lo > hi or bc0 <= ac1 + 1: continue
        for r in range(lo, hi + 1):
            for c in range(ac1 + 1, bc0): out[r][c] = 8
        hit = True
    return out if hit else None
rule("row_overlap_neighbours_get_grey_band", "Rectangles stand in separate column slots; where two neighbouring rectangles share some rows, the gap between them on those rows is filled with colour 8.", gi_rowband, tf_rowband)

def gi_colband(rng):
    g = _slot_rects(rng)
    return transpose(g) if g and tf_colband(transpose(g)) else None
def tf_colband(g):
    t = transpose(g); out = copy(t); obs = sorted(_objs(t), key=lambda o: bbox(o)[1]); hit = False
    for a, b in zip(obs, obs[1:]):
        ar0, ac0, ar1, ac1 = bbox(a); br0, bc0, br1, bc1 = bbox(b)
        lo, hi = max(ar0, br0), min(ar1, br1)
        if lo > hi or bc0 <= ac1 + 1: continue
        for r in range(lo, hi + 1):
            for c in range(ac1 + 1, bc0): out[r][c] = _col(t, a)
        hit = True
    return transpose(out) if hit else None
rule("column_overlap_neighbours_band_upper_colour", "Rectangles stand in separate row slots; where two neighbouring rectangles share some columns, the gap between them on those columns is filled in the upper rectangle's colour.", gi_colband, tf_colband)


# 5 rigid fall stopping one cell short of the obstacle
def gi_fallshort(rng):
    h, w = _size(rng, 10, 18); g = blank(h, w)
    for _ in range(rng.randint(1, 3)):
        _place_free(rng, g, [(0, i) for i in range(rng.randint(3, 8))], GREY, 1)
    n = 0
    for _ in range(rng.randint(2, 4)):
        if _place_free(rng, g, _shape(rng, 2, 6), rng.choice(PAL), 1): n += 1
    return g if n else None
def tf_fallshort(g):
    H, W = dims(g); out = copy(g)
    for o in sorted(components(g, lambda v: v not in (0, GREY)), key=lambda o: -max(r for r, _ in o)):
        col = _col(g, o)
        for r, c in o: out[r][c] = 0
        s = 0
        while all(r + s + 2 < H and out[r + s + 1][c] == 0 and out[r + s + 2][c] == 0 for r, c in o): s += 1
        for r, c in o: out[r + s][c] = col
    return out
rule("objects_fall_stop_one_short_of_obstacle", "Each coloured object falls as a rigid piece and stops one empty cell above the first grey bar, settled object or floor beneath it.", gi_fallshort, tf_fallshort)


# 6 objects absorb the grey dots touching them
def gi_absorb(rng):
    h, w = _size(rng); g = blank(h, w); objs_ = []
    for _ in range(rng.randint(2, 4)):
        o = _place_free(rng, g, _shape(rng, 3, 8), rng.choice(PAL), 2)
        if o: objs_.append(o)
    if not objs_: return None
    n = 0; allc = [c for o in objs_ for c in o]
    for _ in range(rng.randint(1, 5)):
        if _attach(rng, g, rng.choice(objs_), allc, [(0, 0)], GREY, 1): n += 1
    for _ in range(rng.randint(0, 4)): _place_free(rng, g, [(0, 0)], GREY, 2)
    return g if n else None
def tf_absorb(g):
    out = copy(g); H, W = dims(g); hit = False
    for r, c in cells(g, lambda v: v == GREY):
        ns = {g[r + dr][c + dc] for dr, dc in N4 if 0 <= r + dr < H and 0 <= c + dc < W} - {0, GREY}
        if len(ns) > 1: return None
        if ns: out[r][c] = ns.pop(); hit = True
    return out if hit else None
rule("objects_absorb_touching_grey_dots", "Every grey dot that shares a side with a coloured object is absorbed, taking that object's colour; grey dots touching nothing stay grey.", gi_absorb, tf_absorb)


# 7 dots within two cells of an object take its colour; farther dots vanish
def gi_neardots(rng):
    h, w = _size(rng, 9, 18); g = blank(h, w); objs_ = []
    for _ in range(rng.randint(1, 3)):
        o = _place_free(rng, g, _shape(rng, 3, 8), rng.choice(PAL), 3)
        if o: objs_.append(o)
    if not objs_: return None
    used = {_col(g, o) for o in objs_}; dpal = [x for x in PAL if x not in used]; allc = [c for o in objs_ for c in o]; n = 0
    for _ in range(rng.randint(2, 8)):
        r, c = rng.randrange(h), rng.randrange(w)
        if g[r][c] or not _ring_ok(g, [(r, c)], 1, allc): continue
        g[r][c] = rng.choice(dpal); n += 1
    return g if n else None
def tf_neardots(g):
    out = copy(g); obs = _objs(g); big = [o for o in obs if len(o) > 1]; hit = False
    if not big: return None
    for d in obs:
        if len(d) != 1: continue
        (r, c), = d
        dist = lambda o: min(max(abs(r - y), abs(c - x)) for y, x in o)
        best = min(dist(o) for o in big)
        if best > 2: out[r][c] = 0
        else:
            cols = {_col(g, o) for o in big if dist(o) == best}
            if len(cols) > 1: return None
            out[r][c] = cols.pop()
        hit = True
    return out if hit else None
rule("near_dots_take_object_colour_far_dots_vanish", "A single dot within two cells (king moves) of an object takes the colour of the nearest object; dots farther away than that are erased.", gi_neardots, tf_neardots)


# 8 / 21 / 22 solid rectangles holding single cells of another colour
def _dotted_rects(rng, dots=(1, 1), p_dot=0.7):
    h, w = _size(rng, 9, 18); g = blank(h, w); n = 0
    for _ in range(rng.randint(2, 4)):
        col = rng.choice(PAL); cells_ = _place_free(rng, g, _rect(rng, 3, 6, 3, 6), col, 1)
        if cells_ is None or rng.random() > p_dot: continue
        r0, c0, r1, c1 = bbox(cells_); inner = [(r, c) for r in range(r0 + 1, r1) for c in range(c0 + 1, c1)]
        dcol = rng.choice([x for x in PAL if x != col])
        for r, c in rng.sample(inner, min(len(inner), rng.randint(*dots))):
            if all(g[r + dr][c + dc] == col for dr, dc in N4): g[r][c] = dcol; n += 1
    return g if n else None
def gi_hostdot(rng): return _dotted_rects(rng, (1, 1))
def tf_hostdot(g):
    out = copy(g); hit = False
    for b in _blobs(g):
        ps = sorted(_parts(g, b), key=len)
        if len(ps) != 2 or len(ps[0]) != 1: continue
        _paint(out, b, _col(g, ps[0])); hit = True
    return out if hit else None
rule("inner_dot_recolours_host_object", "A solid block holding one cell of a different colour is repainted entirely in that cell's colour; blocks without such a cell are unchanged.", gi_hostdot, tf_hostdot)


# 9 same-colour objects one cell apart are welded with grey
def _gap_pairs(rng, same_prob):
    h, w = _size(rng, 8, 18); g = blank(h, w); same = 0; pairs = 0
    for _ in range(rng.randint(1, 3)):
        a = _rect(rng, 2, 5, 2, 5); b = _rect(rng, 2, 5, 2, 5); (ha, wa), (hb, wb) = _hw(a), _hw(b)
        off = rng.randint(-(hb - 1), ha - 1); r0 = min(0, off)
        ca = [(r - r0, c) for r, c in a]; cb = [(off + r - r0, wa + 1 + c) for r, c in b]
        if rng.random() < 0.5: ca = [(c, r) for r, c in ca]; cb = [(c, r) for r, c in cb]
        col_a = rng.choice(PAL); col_b = col_a if rng.random() < same_prob else rng.choice([x for x in PAL if x != col_a])
        pl = _place_free(rng, g, ca + cb, col_a, 2)
        if pl is None: continue
        _paint(g, pl[len(ca):], col_b); pairs += 1; same += col_a == col_b
    return g, pairs, same
def gi_weld(rng):
    g, pairs, same = _gap_pairs(rng, 0.7)
    return g if same else None
def tf_weld(g):
    H, W = dims(g); out = copy(g); hit = False; cid = {}
    for i, o in enumerate(_objs(g)):
        for cell in o: cid[cell] = i
    for r in range(H):
        for c in range(W):
            if g[r][c]: continue
            for a, b in (((r, c - 1), (r, c + 1)), ((r - 1, c), (r + 1, c))):
                if a in cid and b in cid and cid[a] != cid[b] and g[a[0]][a[1]] == g[b[0]][b[1]]:
                    out[r][c] = GREY; hit = True
    return out if hit else None
rule("same_colour_blocks_one_apart_welded_grey", "Two separate blocks of the same colour with exactly one empty cell between them are welded: the gap cells turn grey (5); gaps between different colours stay open.", gi_weld, tf_weld)


# 10 chain takes the colour of its leftmost member
def gi_chainhead(rng):
    s = _cluster_scene(rng, (1, 3), (2, 4), (0, 2))
    return s[0] if s and tf_chainhead(s[0]) else None
def tf_chainhead(g):
    out = copy(g); hit = False
    for b in _blobs(g):
        ps = _parts(g, b)
        if len(ps) < 2: continue
        mins = sorted(bbox(p)[1] for p in ps)
        if mins[0] == mins[1]: return None
        _paint(out, b, _col(g, min(ps, key=lambda p: bbox(p)[1]))); hit = True
    return out if hit else None
rule("touching_chain_takes_leftmost_colour", "A group of touching objects is repainted entirely in the colour of the member that reaches farthest left.", gi_chainhead, tf_chainhead)


# 11 middle of a three-high stack takes the top's colour
def gi_sandwich(rng):
    h, w = _size(rng, 9, 18); g = blank(h, w); n = 0
    for _ in range(rng.randint(1, 3)):
        k = rng.choice([2, 3, 3, 3]); cols = rng.sample(PAL, k); shapes = []; top = 0; off = 0; pw = 0
        for i in range(k):
            sh = _rect(rng, 1, 3, 2, 5); hh, ww = _hw(sh)
            if i: off = off + rng.randint(-(ww - 1), pw - 1)
            shapes.append([(top + r, off + c) for r, c in sh]); top += hh; pw = ww
        c0 = min(c for s in shapes for _, c in s); shapes = [[(r, c - c0) for r, c in s] for s in shapes]
        pl = _place_free(rng, g, [cell for s in shapes for cell in s], cols[0], 1)
        if pl is None: continue
        i = 0
        for s, col in zip(shapes, cols): _paint(g, pl[i:i + len(s)], col); i += len(s)
        n += k == 3
    return g if n else None
def tf_sandwich(g):
    out = copy(g); hit = False
    for b in _blobs(g):
        ps = _parts(g, b)
        if len(ps) < 3: continue
        for p in ps:
            r0, _, r1, _ = bbox(p)
            above = [q for q in ps if q is not p and _touch4(p, q) and bbox(q)[2] < r0]
            below = [q for q in ps if q is not p and _touch4(p, q) and bbox(q)[0] > r1]
            if len(above) == 1 and len(below) == 1: _paint(out, p, _col(g, above[0])); hit = True
    return out if hit else None
rule("sandwiched_block_takes_upper_colour", "A block touched by one block above it and one below it takes the colour of the block above; stacks of two are unchanged.", gi_sandwich, tf_sandwich)


# 12 touching pairs exchange colours
def gi_pairswap(rng):
    s = _cluster_scene(rng, (1, 4), (2, 2), (0, 2))
    return s[0] if s else None
def tf_pairswap(g):
    out = copy(g); hit = False
    for b in _blobs(g):
        ps = _parts(g, b)
        if len(ps) != 2: continue
        _paint(out, ps[0], _col(g, ps[1])); _paint(out, ps[1], _col(g, ps[0])); hit = True
    return out if hit else None
rule("touching_pairs_exchange_colours", "Every pair of touching objects swaps colours, each keeping its shape and place; objects touching nothing are unchanged.", gi_pairswap, tf_pairswap)


# 13 / 14 hollow frames with an object inside
def _frames_scene(rng):
    h, w = _size(rng, 9, 18); g = blank(h, w); n = 0
    for _ in range(rng.randint(1, 3)):
        fh, fw = rng.randint(5, 9), rng.randint(5, 9)
        sh = [(r, c) for r in range(fh) for c in range(fw) if r in (0, fh - 1) or c in (0, fw - 1)]
        col = rng.choice(PAL); pl = _place_free(rng, g, sh, col, 1)
        if pl is None or rng.random() > 0.75: continue
        r0, c0, r1, c1 = bbox(pl); ih, iw = r1 - r0 - 3, c1 - c0 - 3
        for _ in range(20):
            inner = random_shape(rng, rng.randint(1, min(6, ih * iw))); sh_h, sh_w = _hw(inner)
            if sh_h <= ih and sh_w <= iw:
                rr, cc = r0 + 2 + rng.randint(0, ih - sh_h), c0 + 2 + rng.randint(0, iw - sh_w)
                _paint(g, [(rr + r, cc + c) for r, c in inner], rng.choice([x for x in PAL if x != col])); n += 1; break
    return g if n else None
def _frame_of(g, o):
    r0, c0, r1, c1 = bbox(o)
    if r1 - r0 < 2 or c1 - c0 < 2 or len(o) != 2 * (r1 - r0 + c1 - c0): return None
    if any(r not in (r0, r1) and c not in (c0, c1) for r, c in o): return None
    return [(r, c) for r in range(r0 + 1, r1) for c in range(c0 + 1, c1) if g[r][c]]
def tf_frametakes(g):
    out = copy(g); hit = False
    for o in _objs(g):
        inside = _frame_of(g, o)
        if not inside: continue
        cols = {g[r][c] for r, c in inside}
        if len(cols) != 1: return None
        _paint(out, o, cols.pop()); hit = True
    return out if hit else None
rule("enclosing_frame_takes_enclosed_colour", "A hollow frame that surrounds an object is repainted in that object's colour; empty frames keep their own colour.", _frames_scene, tf_frametakes)

def tf_enclosedtakes(g):
    out = copy(g); hit = False
    for o in _objs(g):
        inside = _frame_of(g, o)
        if not inside: continue
        _paint(out, inside, _col(g, o)); hit = True
    return out if hit else None
rule("enclosed_object_takes_frame_colour", "An object lying inside a hollow frame is repainted in the frame's colour; the frame itself is unchanged.", _frames_scene, tf_enclosedtakes)


# 15 the object touched by the most others turns grey
def gi_hub(rng):
    h, w = _size(rng, 10, 20); g = blank(h, w); hc = rng.choice(PAL)
    hub = _place_free(rng, g, _shape(rng, 5, 10), hc, 1)
    if hub is None: return None
    k = 0
    for _ in range(rng.randint(2, 4)):
        if _attach(rng, g, hub, hub, _shape(rng, 2, 5), rng.choice([x for x in PAL if x != hc]), 1): k += 1
    if k < 2: return None
    for _ in range(rng.randint(0, 2)):
        ac = rng.choice(PAL); a = _place_free(rng, g, _shape(rng, 3, 6), ac, 1)
        if a: _attach(rng, g, a, a, _shape(rng, 2, 5), rng.choice([x for x in PAL if x != ac]), 1)
    for _ in range(rng.randint(0, 2)): _place_free(rng, g, _shape(rng, 2, 6), rng.choice(PAL), 1)
    return g
def tf_hub(g):
    ps = _objs(g); cnt = [sum(1 for q in ps if q is not p and _touch4(p, q)) for p in ps]
    m = max(cnt)
    if m == 0 or cnt.count(m) > 1: return None
    out = copy(g); _paint(out, ps[cnt.index(m)], GREY); return out
rule("most_touched_object_turns_grey", "The one object that is touched by more other objects than any other turns grey (5); everything else is unchanged.", gi_hub, tf_hub)


# 16 smaller of a touching pair is erased
def gi_eat(rng):
    s = _cluster_scene(rng, (1, 4), (2, 2), (0, 2), sizes="distinct")
    return s[0] if s else None
def tf_eat(g):
    out = copy(g); hit = False
    for b in _blobs(g):
        ps = sorted(_parts(g, b), key=len)
        if len(ps) != 2: continue
        if len(ps[0]) == len(ps[1]): return None
        _paint(out, ps[0], 0); hit = True
    return out if hit else None
rule("smaller_of_touching_pair_erased", "Wherever two objects touch, the one with fewer cells is erased and the larger stays; lone objects are unchanged.", gi_eat, tf_eat)


# 17 cluster recoloured by its number of pieces
def gi_partcount(rng):
    s = _cluster_scene(rng, (1, 4), (1, 4), (0, 2), pal=[6, 7, 8, 9])
    return s[0] if s else None
def tf_partcount(g):
    out = copy(g)
    for b in _blobs(g): _paint(out, b, len(_parts(g, b)))
    return out
rule("cluster_recoloured_by_piece_count", "Each group of touching objects is repainted in the colour whose number is the count of separate pieces in the group (a lone object becomes 1).", gi_partcount, tf_partcount, digits=True)


# 18 touching pairs are pulled apart: the right one steps right
def gi_pullapart(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w); n = 0
    for _ in range(rng.randint(1, 4)):
        a = _rect(rng, 1, 4, 1, 4); b = _rect(rng, 1, 4, 1, 4); (ha, wa), (hb, wb) = _hw(a), _hw(b)
        off = rng.randint(-(hb - 1), ha - 1); r0 = min(0, off)
        ca = [(r - r0, c) for r, c in a]; cb = [(off + r - r0, wa + c) for r, c in b]; ph = [(off + r - r0, wa + wb) for r in range(hb)]
        pl = _place_free(rng, g, ca + cb + ph, 1, 1)
        if pl is None: continue
        c1, c2 = rng.sample(PAL, 2); _paint(g, pl[:len(ca)], c1); _paint(g, pl[len(ca):len(ca) + len(cb)], c2); _paint(g, pl[len(ca) + len(cb):], 0); n += 1
    return g if n else None
def tf_pullapart(g):
    H, W = dims(g); out = copy(g); hit = False
    for b in _blobs(g):
        ps = _parts(g, b)
        if len(ps) != 2: continue
        L, R = sorted(ps, key=lambda p: bbox(p)[3])
        if bbox(R)[1] <= bbox(L)[3]: return None
        col = _col(g, R)
        for r, c in R: out[r][c] = 0
        if any(c + 1 >= W or out[r][c + 1] != 0 for r, c in R): return None
        for r, c in R: out[r][c + 1] = col
        hit = True
    return out if hit else None
rule("touching_pair_pulled_apart_right_steps", "In every side-by-side pair of touching blocks the right-hand block moves one cell to the right, opening a one-cell gap.", gi_pullapart, tf_pullapart)


# 19 a grey dot beside an object cuts that row out of it
def gi_cutrow(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w); n = 0
    for _ in range(rng.randint(1, 4)):
        sh = _rect(rng, 3, 7, 2, 6); hh, ww = _hw(sh); rr = rng.randint(1, hh - 2)
        full = sh + [(rr, -1) if rng.random() < 0.5 else (rr, ww)]; c0 = min(c for _, c in full)
        pl = _place_free(rng, g, [(r, c - c0) for r, c in full], rng.choice(PAL), 1)
        if pl: g[pl[-1][0]][pl[-1][1]] = GREY; n += 1
    for _ in range(rng.randint(0, 2)): _place_free(rng, g, _rect(rng, 2, 5, 2, 5), rng.choice(PAL), 1)
    return g if n else None
def tf_cutrow(g):
    H, W = dims(g); out = copy(g); obs = _objs(g); hit = False
    for r, c in cells(g, lambda v: v == GREY):
        out[r][c] = 0
        for dc in (-1, 1):
            if 0 <= c + dc < W and g[r][c + dc] not in (0, GREY):
                for y, x in next(o for o in obs if (r, c + dc) in o):
                    if y == r: out[y][x] = 0
                hit = True
    return out if hit else None
rule("grey_dot_beside_block_cuts_its_row", "A grey dot touching the side of a block marks a row: that row of the block is erased, cutting it in two, and the dot disappears.", gi_cutrow, tf_cutrow)


# 20 touching pair replaced by its filled joint bounding box
def gi_bboxmerge(rng):
    s = _cluster_scene(rng, (1, 3), (2, 2), (0, 2), margin=3, rect=True)
    return s[0] if s and tf_bboxmerge(s[0]) else None
def tf_bboxmerge(g):
    out = copy(g); hit = False; bl = _blobs(g); own = {cell: i for i, b in enumerate(bl) for cell in b}
    for i, b in enumerate(bl):
        ps = sorted(_parts(g, b), key=len)
        if len(ps) != 2: continue
        if len(ps[0]) == len(ps[1]): return None
        r0, c0, r1, c1 = bbox(b)
        box = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)]
        if any(own.get(cell, i) != i for cell in box): return None
        _paint(out, box, _col(g, ps[1])); hit = True
    return out if hit else None
rule("touching_pair_merged_to_filled_box", "Two touching blocks merge into one solid rectangle covering both their extents, painted in the colour of the block with more cells.", gi_bboxmerge, tf_bboxmerge)


# 21 inner dots punched out of their host
def gi_punch(rng): return _dotted_rects(rng, (1, 3))
def tf_punch(g):
    H, W = dims(g); out = copy(g); hit = False
    for r in range(1, H - 1):
        for c in range(1, W - 1):
            ns = {g[r + dr][c + dc] for dr, dc in N4}
            if g[r][c] and len(ns) == 1 and 0 not in ns and g[r][c] not in ns: out[r][c] = 0; hit = True
    return out if hit else None
rule("inner_dots_punched_out_of_blocks", "Every cell of a different colour buried inside a solid block is punched out, leaving an empty hole where it was.", gi_punch, tf_punch)


# 22 inner dot paints its row and column across the host
def gi_cross(rng): return _dotted_rects(rng, (1, 1))
def tf_cross(g):
    out = copy(g); hit = False
    for b in _blobs(g):
        ps = sorted(_parts(g, b), key=len)
        if len(ps) != 2 or len(ps[0]) != 1: continue
        (dr, dc), = ps[0]
        _paint(out, [(r, c) for r, c in b if r == dr or c == dc], g[dr][dc]); hit = True
    return out if hit else None
rule("inner_dot_paints_cross_through_block", "A single odd-coloured cell inside a solid block paints its whole row and column within that block in its colour.", gi_cross, tf_cross)


# 23 objects that share rows with another object turn grey
def gi_sharerows(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w)
    for _ in range(rng.randint(3, 6)): _place_free(rng, g, _shape(rng, 2, 7), rng.choice(PAL), 1)
    return g if tf_sharerows(g) else None
def tf_sharerows(g):
    out = copy(g); obs = _objs(g); hit = False
    for o in obs:
        r0, _, r1, _ = bbox(o)
        if any(q is not o and bbox(q)[0] <= r1 and bbox(q)[2] >= r0 for q in obs): _paint(out, o, GREY); hit = True
    return out if hit else None
rule("objects_sharing_a_row_turn_grey", "Every object that lies on at least one row also occupied by another object turns grey (5); objects alone on all their rows keep their colour.", gi_sharerows, tf_sharerows)


# 24 touching clusters fall as single rigid bodies
def gi_clusterfall(rng):
    s = _cluster_scene(rng, (1, 3), (2, 3), (0, 2), lo=9, hi=18)
    return s[0] if s else None
def tf_clusterfall(g):
    H, W = dims(g); out = copy(g)
    for b in sorted(_blobs(g), key=lambda b: -max(r for r, _ in b)):
        cols = [g[r][c] for r, c in b]
        for r, c in b: out[r][c] = 0
        s = 0
        while all(r + s + 1 < H and out[r + s + 1][c] == 0 for r, c in b): s += 1
        for (r, c), v in zip(b, cols): out[r + s][c] = v
    return out
rule("touching_clusters_fall_as_one_body", "Objects that touch each other fall together as one rigid body until they rest on the floor or on something below; colours are kept.", gi_clusterfall, tf_clusterfall)


# 25 object takes the majority colour of the dots touching it
def gi_majdots(rng):
    h, w = _size(rng, 9, 18); g = blank(h, w); n = 0
    for _ in range(rng.randint(1, 3)):
        col = rng.choice(PAL); o = _place_free(rng, g, _shape(rng, 4, 9), col, 2)
        if o is None: continue
        c1, c2 = rng.sample([x for x in PAL if x != col], 2); k1 = rng.randint(2, 4); k2 = rng.randint(0, k1 - 1); got = {c1: 0, c2: 0}
        for dc in [c1] * k1 + [c2] * k2:
            if _attach(rng, g, o, o, [(0, 0)], dc, 1): got[dc] += 1
        if got[c1] == got[c2]: return None
        n += 1
    for _ in range(rng.randint(0, 2)): _place_free(rng, g, _shape(rng, 3, 6), rng.choice(PAL), 2)
    return g if n else None
def tf_majdots(g):
    out = copy(g); obs = _objs(g); dots = [o for o in obs if len(o) == 1]; hit = False
    for o in obs:
        if len(o) == 1: continue
        mine = [d for d in dots if _touch4(d, o)]
        if not mine: continue
        cnt = {}
        for d in mine: cnt[_col(g, d)] = cnt.get(_col(g, d), 0) + 1
        best = max(cnt.values())
        if list(cnt.values()).count(best) > 1: return None
        _paint(out, o, next(k for k, v in cnt.items() if v == best))
        for d in mine: out[d[0][0]][d[0][1]] = 0
        hit = True
    return out if hit else None
rule("object_takes_majority_touching_dot_colour", "Each object surrounded by single dots takes the colour that the most dots touching it share, and those dots vanish.", gi_majdots, tf_majdots)


# 26 facing blocks approach and stop one cell apart
def gi_approach(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w); r = 0; n = 0
    while r < h:
        hh = rng.randint(1, 3)
        if r + hh > h: break
        if rng.random() < 0.6:
            wa, wb = rng.randint(1, 4), rng.randint(1, 4); gap = rng.choice([3, 5, 7, 9])
            if wa + wb + gap <= w:
                c0 = rng.randint(0, w - wa - wb - gap)
                rect(g, r, c0, r + hh - 1, c0 + wa - 1, rng.choice(PAL)); rect(g, r, c0 + wa + gap, r + hh - 1, c0 + wa + gap + wb - 1, rng.choice(PAL)); n += 1
        r += hh + rng.randint(1, 3)
    return g if n else None
def tf_approach(g):
    out = copy(g); bands = {}; hit = False
    for o in _objs(g): bands.setdefault((bbox(o)[0], bbox(o)[2]), []).append(o)
    for os_ in bands.values():
        if len(os_) != 2: return None
        L, R = sorted(os_, key=lambda o: bbox(o)[1]); gap = bbox(R)[1] - bbox(L)[3] - 1
        if gap == 1: continue
        if gap < 3 or gap % 2 == 0: return None
        s = (gap - 1) // 2; cl, cr = _col(g, L), _col(g, R)
        for r, c in L + R: out[r][c] = 0
        for r, c in L: out[r][c + s] = cl
        for r, c in R: out[r][c - s] = cr
        hit = True
    return out if hit else None
rule("facing_blocks_approach_stop_one_apart", "Two blocks on the same rows slide toward each other at equal speed and stop when a single empty column separates them.", gi_approach, tf_approach)


# 27 dots fate by how many objects they touch
def gi_contactdots(rng):
    h, w = _size(rng, 9, 18); g = blank(h, w); objs_ = []; n = 0
    for _ in range(rng.randint(1, 2)):
        a = _rect(rng, 2, 5, 2, 4); b = _rect(rng, 2, 5, 2, 4); (ha, wa), (hb, wb) = _hw(a), _hw(b)
        off = rng.randint(-(hb - 1), ha - 1); r0 = min(0, off)
        sa = [(r - r0, c) for r, c in a]; sb = [(off + r - r0, wa + 1 + c) for r, c in b]; ca, cb = rng.sample(PAL, 2)
        pl = _place_free(rng, g, sa + sb, ca, 2)
        if pl is None: continue
        _paint(g, pl[len(sa):], cb); objs_ += [pl[:len(sa)], pl[len(sa):]]
    for _ in range(rng.randint(0, 2)):
        o = _place_free(rng, g, _shape(rng, 3, 7), rng.choice(PAL), 2)
        if o: objs_.append(o)
    if not objs_: return None
    dpal = [x for x in PAL if x not in {_col(g, o) for o in objs_}]; allc = [c for o in objs_ for c in o]
    if not dpal: return None
    for _ in range(rng.randint(2, 6)):
        if _attach(rng, g, rng.choice(objs_), allc, [(0, 0)], rng.choice(dpal), 1): n += 1
    for _ in range(rng.randint(0, 3)): _place_free(rng, g, [(0, 0)], rng.choice(dpal), 2)
    return g if n else None
def tf_contactdots(g):
    out = copy(g); obs = _objs(g); big = [o for o in obs if len(o) > 1]; hit = False
    for d in obs:
        if len(d) != 1: continue
        t = [o for o in big if _touch4(d, o)]; (r, c), = d
        out[r][c] = 0 if not t else (_col(g, t[0]) if len(t) == 1 else GREY); hit = True
    return out if hit else None
rule("dots_fate_by_objects_touched", "A single dot touching no object vanishes, one touching exactly one object takes that object's colour, and one touching two objects turns grey (5).", gi_contactdots, tf_contactdots)


# 28 count of touching groups -> bar
def gi_groupcount(rng):
    s = _cluster_scene(rng, (1, 6), (2, 3), (0, 3), lo=10, hi=20)
    return s[0] if s else None
def tf_groupcount(g):
    n = sum(1 for b in _blobs(g) if len(_parts(g, b)) >= 2); w = len(g[0])
    return [[GREY] * n + [0] * (w - n)] if 0 < n < w else None
rule("touching_group_count_bar", "Output one row as wide as the grid with a grey bar as long as the number of groups of two or more touching objects.", gi_groupcount, tf_groupcount)


# 29 one bar per cluster, length = pieces
def gi_piecebars(rng):
    s = _cluster_scene(rng, (1, 4), (1, 4), (0, 3))
    return s[0] if s else None
def tf_piecebars(g):
    ks = [len(_parts(g, b)) for b in sorted(_blobs(g), key=lambda b: min(b))]; w = max(ks) + 1
    return [[GREY] * k + [0] * (w - k) for k in ks]
rule("cluster_piece_counts_as_bars", "Output one row per group of touching objects, top group first: a grey bar as long as the number of separate pieces in that group.", gi_piecebars, tf_piecebars)


# 30 crop the largest touching group
def gi_cropcluster(rng):
    s = _cluster_scene(rng, (2, 4), (2, 3), (0, 3), sizes="distinct")
    return s[0] if s and tf_cropcluster(s[0]) else None
def tf_cropcluster(g):
    bl = sorted(_blobs(g), key=len)
    if len(bl) < 2 or len(bl[-1]) == len(bl[-2]) or len(_parts(g, bl[-1])) < 2: return None
    return crop(g, *bbox(bl[-1]))
rule("crop_largest_touching_group", "Output the bounding box of the group of touching objects that covers the most cells in total.", gi_cropcluster, tf_cropcluster)


# 31 part of an object below the grey line is recoloured
def gi_linecross(rng):
    h, w = _size(rng, 9, 18); g = blank(h, w); lr = rng.randint(3, h - 4); n = 0; pal = [x for x in PAL if x != 8]
    for _ in range(rng.randint(1, 4)):
        sh = _shape(rng, 4, 10); hh, ww = _hw(sh); col = rng.choice(pal)
        if rng.random() < 0.7 and hh >= 3:
            r0 = rng.randint(max(0, lr - hh + 2), lr - 1); c0 = rng.randint(0, w - ww); cells_ = [(r0 + r, c0 + c) for r, c in sh]
            if r0 + hh - 1 <= lr or not _ring_ok(g, cells_, 1): continue
            _paint(g, cells_, col); n += 1
        else:
            for _ in range(20):
                r0 = rng.randint(0, h - hh); c0 = rng.randint(0, w - ww); cells_ = [(r0 + r, c0 + c) for r, c in sh]
                if all(r != lr for r, _ in cells_) and _ring_ok(g, cells_, 1): _paint(g, cells_, col); break
    for c in range(w):
        if g[lr][c] == 0: g[lr][c] = GREY
    return g if n and tf_linecross(g) else None
def tf_linecross(g):
    H, W = dims(g); out = copy(g)
    rows = [r for r in range(H) if all(g[r][c] != 0 for c in range(W)) and g[r].count(GREY) * 2 > W]
    if len(rows) != 1: return None
    lr = rows[0]; hit = False
    for o in components(g, lambda v: v not in (0, GREY)):
        if any(r < lr for r, _ in o) and any(r > lr for r, _ in o):
            for r, c in o:
                if r > lr: out[r][c] = 8
            hit = True
    return out if hit else None
rule("object_part_below_grey_line_recoloured", "Objects crossing the grey line keep their colour above it and become colour 8 below it; objects wholly on one side are unchanged.", gi_linecross, tf_linecross)


# 32 empty cells inside a touching group's joint box turn grey
def gi_boxgaps(rng):
    s = _cluster_scene(rng, (1, 3), (2, 3), (0, 2), margin=3)
    return s[0] if s and tf_boxgaps(s[0]) else None
def tf_boxgaps(g):
    out = copy(g); hit = False; bl = _blobs(g); own = {cell: i for i, b in enumerate(bl) for cell in b}
    for i, b in enumerate(bl):
        if len(_parts(g, b)) < 2: continue
        r0, c0, r1, c1 = bbox(b)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if own.get((r, c), i) != i: return None
                if g[r][c] == 0: out[r][c] = GREY; hit = True
    return out if hit else None
rule("touching_group_box_gaps_filled_grey", "For every group of touching objects, the empty cells inside the group's joint bounding box are painted grey (5); lone objects get nothing.", gi_boxgaps, tf_boxgaps)


# 33 a dot touching a group recolours the whole group
def gi_dotcluster(rng):
    s = _cluster_scene(rng, (1, 3), (2, 3), (0, 2))
    if not s: return None
    g, groups = s; n = 0
    for grp in groups:
        if rng.random() < 0.75:
            dc = rng.choice([x for x in PAL if x not in {_col(g, p) for p in grp}])
            if _attach(rng, g, rng.choice(grp), [c for p in grp for c in p], [(0, 0)], dc, 1): n += 1
    return g if n else None
def tf_dotcluster(g):
    out = copy(g); hit = False
    for b in _blobs(g):
        ps = _parts(g, b); dots = [p for p in ps if len(p) == 1]
        if len(ps) < 2 or len(dots) != 1: continue
        _paint(out, b, _col(g, dots[0])); out[dots[0][0][0]][dots[0][0][1]] = 0; hit = True
    return out if hit else None
rule("dot_recolours_whole_touched_group", "A single dot touching a group of touching objects repaints the entire group in the dot's colour and then disappears; groups without a dot are unchanged.", gi_dotcluster, tf_dotcluster)


# 34 grow one layer; cells wanted by two objects stay empty
def gi_growcontest(rng):
    h, w = _size(rng, 9, 18); g = blank(h, w)
    for _ in range(rng.randint(2, 6)): _place_free(rng, g, _shape(rng, 2, 7), rng.choice(PAL), rng.choice([1, 2]))
    return g if any(v for row in g for v in row) else None
def tf_growcontest(g):
    H, W = dims(g); out = copy(g); claim = {}
    for i, o in enumerate(_objs(g)):
        for r, c in o:
            for dr, dc in N4:
                nr, nc = r + dr, c + dc
                if 0 <= nr < H and 0 <= nc < W and g[nr][nc] == 0: claim.setdefault((nr, nc), set()).add((i, g[r][c]))
    for (r, c), who in claim.items():
        if len(who) == 1: out[r][c] = next(iter(who))[1]
    return out
rule("objects_grow_one_layer_contested_cells_stay_empty", "Every object grows by one cell on all four sides, except that an empty cell adjacent to two different objects is claimed by neither and stays empty.", gi_growcontest, tf_growcontest)


# 35 grey object recoloured by the number of dots touching it
def gi_dotcount(rng):
    h, w = _size(rng, 9, 18); g = blank(h, w); dc = rng.choice(PAL); n = 0
    for _ in range(rng.randint(1, 4)):
        o = _place_free(rng, g, _shape(rng, 3, 8), GREY, 2)
        if o is None: continue
        k = rng.randint(0, 4)
        for _ in range(k):
            if _attach(rng, g, o, o, [(0, 0)], dc, 1): n += 1
    return g if n else None
def tf_dotcount(g):
    out = copy(g); dots = [o for o in _objs(g) if len(o) == 1 and _col(g, o) != GREY]
    for o in components(g, GREY):
        mine = [d for d in dots if _touch4(d, o)]
        _paint(out, o, len(mine))
        for d in mine: out[d[0][0]][d[0][1]] = 0
    return out
rule("grey_object_becomes_touching_dot_count", "Each grey object is repainted in the colour whose number equals how many single dots touch it, and the dots vanish; a grey object touched by no dot disappears.", gi_dotcount, tf_dotcount, digits=True)


# 36 different-colour blocks one apart fuse and take the left colour
def gi_fuseleft(rng):
    g, pairs, same = _gap_pairs(rng, 0.0)
    return g if pairs and tf_fuseleft(g) else None
def tf_fuseleft(g):
    out = copy(g); obs = _objs(g); hit = False
    for A in obs:
        for B in obs:
            ar0, ac0, ar1, ac1 = bbox(A); br0, bc0, br1, bc1 = bbox(B)
            if A is B or bc0 != ac1 + 2: continue
            lo, hi = max(ar0, br0), min(ar1, br1)
            gap = [(r, ac1 + 1) for r in range(lo, hi + 1) if g[r][ac1 + 1] == 0 and g[r][ac1] and g[r][bc0]]
            if not gap: continue
            _paint(out, gap + B, _col(g, A)); hit = True
    return out if hit else None
rule("side_by_side_blocks_one_apart_fuse_left_colour", "Two side-by-side blocks of different colours separated by one empty column are fused: the gap is filled and the right block repainted in the left block's colour; blocks stacked one row apart are unchanged.", gi_fuseleft, tf_fuseleft)


# 37 blocks meeting only at a corner are joined through grey
def gi_corner(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w); n = 0
    for _ in range(rng.randint(1, 4)):
        ac = rng.choice(PAL); a = _place_free(rng, g, _rect(rng, 1, 4, 1, 4), ac, 1)
        if a is None: continue
        r0, c0, r1, c1 = bbox(a); b = _rect(rng, 1, 4, 1, 4); hb, wb = _hw(b)
        cr, cc = rng.choice([(r0 - hb, c0 - wb), (r0 - hb, c1 + 1), (r1 + 1, c0 - wb), (r1 + 1, c1 + 1)])
        cells_ = [(cr + r, cc + c) for r, c in b]
        if all(0 <= r < h and 0 <= c < w and g[r][c] == 0 for r, c in cells_) and _ring_ok(g, cells_, 1, a):
            _paint(g, cells_, rng.choice([x for x in PAL if x != ac])); n += 1
    return g if n else None
def tf_corner(g):
    H, W = dims(g); out = copy(g); hit = False
    for r in range(H - 1):
        for c in range(W - 1):
            a, b, d, e = g[r][c], g[r + 1][c + 1], g[r][c + 1], g[r + 1][c]
            if a and b and a != b and d == 0 and e == 0: out[r][c + 1] = out[r + 1][c] = GREY; hit = True
            if d and e and d != e and a == 0 and b == 0: out[r][c] = out[r + 1][c + 1] = GREY; hit = True
    return out if hit else None
rule("corner_touching_blocks_joined_grey", "Two blocks of different colours that meet only at a corner are joined: the two empty cells beside that corner turn grey (5).", gi_corner, tf_corner)


# 38 smaller of a touching pair jumps to the other side of the larger
def gi_jump(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w); n = 0
    for _ in range(rng.randint(1, 3)):
        hh = rng.randint(1, 4); wa, wb = rng.sample(range(1, 6), 2); small = min(wa, wb)
        full = [(r, c) for r in range(hh) for c in range(wa + wb + small)]
        pl = _place_free(rng, g, full, 1, 2)
        if pl is None: continue
        _paint(g, pl, 0); r0, c0 = pl[0]; start = c0 if wa < wb else c0 + small
        ca, cb = rng.sample(PAL, 2)
        rect(g, r0, start, r0 + hh - 1, start + wa - 1, ca); rect(g, r0, start + wa, r0 + hh - 1, start + wa + wb - 1, cb); n += 1
    return g if n else None
def tf_jump(g):
    H, W = dims(g); out = copy(g); hit = False
    for b in _blobs(g):
        ps = _parts(g, b)
        if len(ps) != 2: continue
        L, R = sorted(ps, key=lambda p: bbox(p)[1])
        if len(L) == len(R): return None
        lr0, lc0, lr1, lc1 = bbox(L); rr0, rc0, rr1, rc1 = bbox(R)
        mover, shift = (L, rc1 - lc0 + 1) if len(L) < len(R) else (R, lc0 - rc1 - 1)
        col = _col(g, mover)
        for r, c in mover: out[r][c] = 0
        if any(not 0 <= c + shift < W or out[r][c + shift] != 0 for r, c in mover): return None
        for r, c in mover: out[r][c + shift] = col
        hit = True
    return out if hit else None
rule("smaller_of_touching_pair_jumps_over_larger", "In each pair of touching blocks the smaller block jumps over the larger one and lands touching its far side.", gi_jump, tf_jump)


# 39 slide right, then groups that end up touching take the rightmost colour
def gi_slidemerge(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w)
    for _ in range(rng.randint(2, 5)): _place_free(rng, g, _shape(rng, 2, 7), rng.choice(PAL), 1)
    return g if tf_slidemerge(g) else None
def tf_slidemerge(g):
    H, W = dims(g); out = blank(H, W)
    for o in sorted(_objs(g), key=lambda o: -max(c for _, c in o)):
        col = _col(g, o); s = 0
        while all(c + s + 1 < W and out[r][c + s + 1] == 0 for r, c in o): s += 1
        for r, c in o: out[r][c + s] = col
    for b in _blobs(out):
        ps = sorted(_parts(out, b), key=lambda p: bbox(p)[3])
        if len(ps) < 2: continue
        if bbox(ps[-1])[3] == bbox(ps[-2])[3]: return None
        _paint(out, b, _col(out, ps[-1]))
    return out if any(v for row in out for v in row) else None
rule("slide_right_then_touching_take_rightmost_colour", "Every object slides right until it hits the wall or another object; objects that end up touching are then all painted in the colour of the one reaching farthest right.", gi_slidemerge, tf_slidemerge)


# 40 touching groups get a grey halo
def gi_halo(rng):
    s = _cluster_scene(rng, (1, 3), (2, 3), (1, 3), margin=3)
    return s[0] if s else None
def tf_halo(g):
    H, W = dims(g); out = copy(g); hit = False
    for b in _blobs(g):
        if len(_parts(g, b)) < 2: continue
        for r, c in b:
            for dr, dc in N8:
                nr, nc = r + dr, c + dc
                if 0 <= nr < H and 0 <= nc < W and g[nr][nc] == 0: out[nr][nc] = GREY; hit = True
    return out if hit else None
rule("touching_groups_get_grey_halo", "Every group of two or more touching objects is surrounded by a one-cell grey (5) halo, corners included; objects touching nothing get no halo.", gi_halo, tf_halo)
