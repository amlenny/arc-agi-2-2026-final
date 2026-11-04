# b043_pairing.py -- 40 rules, theme PAIRED OBJECTS AND PROPERTY TRANSFER.
# Objects come in pairs identified by a shared single-cell marker colour (a "dot") placed just outside
# each member's bounding box. Rules transfer shape/colour/size/position between the two members of a
# pair, or act on the relation between pairs (distance, rank, matching shape).
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

GREY = 5


# ---------- shared helpers (not rules) ----------

def _comps(g):
    return components(g, lambda v: v != 0, conn8=True)


def _rel(comp):
    r0, c0, _, _ = bbox(comp)
    return [(r - r0, c - c0) for r, c in comp]


def _anchor(comp):
    r0, c0, _, _ = bbox(comp)
    return r0, c0


def _center(comp):
    r0, c0, r1, c1 = bbox(comp)
    return (r0 + r1) / 2.0, (c0 + c1) / 2.0


def _clear(g, comp):
    for r, c in comp:
        g[r][c] = 0


def _paint(g, comp, col):
    for r, c in comp:
        g[r][c] = col


def _stamp(g, rel, r0, c0, col):
    H, W = dims(g)
    for r, c in rel:
        if 0 <= r0 + r < H and 0 <= c0 + c < W:
            g[r0 + r][c0 + c] = col


def _pairs_from_grid(g):
    """Group same-colour components by size: size-1 = a dot marker, size>1 = a shape. Two dots sharing a
    colour mark the pair whose members are their nearest shapes. Returns (pairs, unmatched_shapes)."""
    comps = _comps(g)
    shapes = [c for c in comps if len(c) > 1]
    dots = [c for c in comps if len(c) == 1]
    by_colour = {}
    for d in dots:
        col = g[d[0][0]][d[0][1]]
        by_colour.setdefault(col, []).append(d[0])
    used, pairs = set(), []
    for col, pts in by_colour.items():
        if len(pts) != 2:
            continue
        members = []
        for pt in pts:
            cand = [s for s in shapes if id(s) not in used]
            if not cand:
                break
            best = min(cand, key=lambda s: min(abs(pt[0] - r) + abs(pt[1] - c) for r, c in s))
            members.append(best); used.add(id(best))
        if len(members) == 2 and members[0] is not members[1]:
            a, b = members
            pairs.append({"a": a, "b": b, "ca": g[a[0][0]][a[0][1]], "cb": g[b[0][0]][b[0][1]], "dot": col})
    unmatched = [s for s in shapes if id(s) not in used]
    return pairs, unmatched


def _place_dot(g, bb, colour, rng):
    H, W = dims(g); r0, c0, r1, c1 = bb
    cands = []
    for r, c in [(r0 - 1, c0), (r0, c0 - 1), (r1 + 1, c1), (r1, c1 + 1), (r0 - 1, c1), (r1 + 1, c0),
                 (r0 - 1, c0 - 1), (r1 + 1, c1 + 1)]:
        if 0 <= r < H and 0 <= c < W and g[r][c] == 0:
            cands.append((r, c))
    if not cands:
        return False
    r, c = rng.choice(cands)
    g[r][c] = colour
    return True


def _scene_pairs(rng, npairs=None, use_grey=None, same_shape=None, nlo=3, nhi=7, hi=18, unpaired=0):
    """npairs pairs of random shapes, each pair's two members tagged with a shared dot colour.
    use_grey: True forces one member of every pair to colour GREY, False forces neither, None is 50/50
    per pair. same_shape: True/False forces both members congruent/different, None is 50/50 per pair."""
    npairs = npairs if npairs is not None else rng.randint(2, 3)
    npairs = min(npairs, 4)
    if rng.random() < 0.4:
        h, w = rng.randint(21, 30), rng.randint(21, 30)
    else:
        h, w = size(rng, 10, hi)
    g = blank(h, w)
    pool = [c for c in COLOURS if c != GREY]
    rng.shuffle(pool)
    if 2 * npairs > len(pool):
        return None
    shape_cols = pool[:npairs]
    dot_cols = pool[npairs:2 * npairs]
    shapes, cols = [], []
    for i in range(npairs):
        sA = random_shape(rng, rng.randint(nlo, nhi))
        if same_shape is True:
            sB = sA
        elif same_shape is False:
            sB = random_shape(rng, rng.randint(nlo, nhi))
        else:
            sB = sA if rng.random() < 0.5 else random_shape(rng, rng.randint(nlo, nhi))
        grey_here = use_grey if use_grey is not None else (rng.random() < 0.5)
        if grey_here:
            colA, colB = (GREY, shape_cols[i]) if rng.random() < 0.5 else (shape_cols[i], GREY)
        else:
            other = rng.choice([c for c in pool if c != shape_cols[i]])
            colA, colB = shape_cols[i], other
        shapes += [sA, sB]; cols += [colA, colB]
    extra = [random_shape(rng, rng.randint(nlo, nhi)) for _ in range(unpaired)]
    extra_cols = [rng.choice(shape_cols) for _ in extra]
    pos = place_shapes(rng, g, shapes + extra, cols + extra_cols, margin=2)
    if pos is None:
        return None
    for i in range(npairs):
        for idx in (2 * i, 2 * i + 1):
            r0c, c0c = pos[idx]
            cells_ = [(r0c + r, c0c + c) for r, c in shapes[idx]]
            if not _place_dot(g, bbox(cells_), dot_cols[i], rng):
                return None
    return g


# ---------- 1 grey copies partner's shape ----------
def gi1(rng): return _scene_pairs(rng, use_grey=True, same_shape=False)
def tf1(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False
    for p in pairs:
        if p["ca"] == GREY: gmem, partner = p["a"], p["b"]
        elif p["cb"] == GREY: gmem, partner = p["b"], p["a"]
        else: continue
        _clear(out, gmem); r0, c0 = _anchor(gmem)
        _stamp(out, _rel(partner), r0, c0, GREY); changed = True
    return out if changed else None
rule("pair_grey_copies_partner_shape", "The grey member of each pair is redrawn in grey using its partner's shape.", gi1, tf1)


# ---------- 2 grey copies partner's colour ----------
def gi2(rng): return _scene_pairs(rng, use_grey=True)
def tf2(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False
    for p in pairs:
        if p["ca"] == GREY: gmem, pcol = p["a"], p["cb"]
        elif p["cb"] == GREY: gmem, pcol = p["b"], p["ca"]
        else: continue
        _paint(out, gmem, pcol); changed = True
    return out if changed else None
rule("pair_grey_copies_partner_colour", "The grey member of each pair is recoloured with its partner's colour.", gi2, tf2)


# ---------- 3 swap the two shapes in place ----------
def gi3(rng): return _scene_pairs(rng, use_grey=False, same_shape=False)
def tf3(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False
    for p in pairs:
        a, b, ca_, cb_ = p["a"], p["b"], p["ca"], p["cb"]
        if _rel(a) == _rel(b): continue
        ra, ca2 = _anchor(a); rb, cb2 = _anchor(b)
        _clear(out, a); _clear(out, b)
        _stamp(out, _rel(b), ra, ca2, ca_); _stamp(out, _rel(a), rb, cb2, cb_)
        changed = True
    return out if changed else None
rule("pair_swap_shapes_in_place", "Within each pair the two shapes trade patterns while staying at their own positions.", gi3, tf3)


# ---------- 4 partner's size sets how far the other moves ----------
def gi4(rng): return _scene_pairs(rng, use_grey=False, hi=16)
def tf4(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False; W = dims(g)[1]
    for p in pairs:
        a, b, ca_ = p["a"], p["b"], p["ca"]
        dist = len(b); r0, c0 = _anchor(a); rel = _rel(a)
        maxc = max(c for _, c in rel)
        if c0 + dist + maxc < W:
            _clear(out, a); _stamp(out, rel, r0, c0 + dist, ca_); changed = True
    return out if changed else None
rule("pair_partner_size_sets_move_distance", "Each object slides right by a number of cells equal to its partner's cell count.", gi4, tf4)


# ---------- 5 draw a line between every pair ----------
def gi5(rng): return _scene_pairs(rng, use_grey=False)
def _connect(out, a, b, col):
    ra, ca_ = _center(a); rb, cb_ = _center(b)
    ra, ca_, rb, cb_ = int(ra), int(ca_), int(rb), int(cb_)
    for c in range(min(ca_, cb_), max(ca_, cb_) + 1):
        if out[ra][c] == 0: out[ra][c] = col
    for r in range(min(ra, rb), max(ra, rb) + 1):
        if out[r][cb_] == 0: out[r][cb_] = col
def tf5(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False
    for p in pairs:
        _connect(out, p["a"], p["b"], p["dot"]); changed = True
    return out if changed else None
rule("pair_draw_connecting_line", "A right-angled line in the pair's dot colour joins the centres of its two members.", gi5, tf5)


# ---------- 6 delete the larger of each pair ----------
def gi6(rng): return _scene_pairs(rng, use_grey=False, same_shape=False)
def tf6(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False
    for p in pairs:
        a, b = p["a"], p["b"]
        if len(a) == len(b): continue
        _clear(out, a if len(a) > len(b) else b); changed = True
    return out if changed else None
rule("pair_delete_larger_member", "The larger member of each pair is erased, leaving only the smaller one.", gi6, tf6)


# ---------- 7 merge each pair into one object at the midpoint ----------
def gi7(rng): return _scene_pairs(rng, use_grey=False, same_shape=False)
def tf7(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False
    for p in pairs:
        a, b, dot = p["a"], p["b"], p["dot"]
        _clear(out, a); _clear(out, b)
        ra, ca_ = _center(a); rb, cb_ = _center(b)
        mr, mc = int((ra + rb) / 2), int((ca_ + cb_) / 2)
        rel = _rel(a) if len(a) <= len(b) else _rel(b)
        _stamp(out, rel, mr, mc, dot); changed = True
    return out if changed else None
rule("pair_merge_at_midpoint", "Each pair collapses into a single shape, drawn in the dot colour at the midpoint between them.", gi7, tf7)


# ---------- 8 recolour each pair by whether the two shapes are identical ----------
def gi8(rng): return _scene_pairs(rng, use_grey=False, same_shape=None)
def tf8(g):
    pairs, _ = _pairs_from_grid(g)
    if not pairs: return None
    out = copy(g)
    for p in pairs:
        same = _rel(p["a"]) == _rel(p["b"])
        col = 3 if same else 8
        _paint(out, p["a"], col); _paint(out, p["b"], col)
    return out
rule("pair_recolour_by_shape_match", "Every pair is recoloured 3 if its two shapes are identical, 8 if they differ.", gi8, tf8)


# ---------- 9 delete unpaired objects ----------
def gi9(rng): return _scene_pairs(rng, use_grey=False, npairs=2, unpaired=1)
def tf9(g):
    pairs, unmatched = _pairs_from_grid(g)
    if not unmatched: return None
    out = copy(g)
    for s in unmatched: _clear(out, s)
    return out
rule("pair_delete_unpaired_objects", "Any object with no dot-marked partner is deleted.", gi9, tf9)


# ---------- 10 connect only pairs with matching shapes ----------
def gi10(rng): return _scene_pairs(rng, use_grey=False, same_shape=None)
def tf10(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False
    for p in pairs:
        if _rel(p["a"]) != _rel(p["b"]): continue
        _connect(out, p["a"], p["b"], p["dot"]); changed = True
    return out if changed else None
rule("pair_connect_matching_shapes_only", "Only pairs whose two shapes are identical get a connecting line; mismatched pairs are left alone.", gi10, tf10)


# ---------- 11 highlight the pair with the greatest separation ----------
def gi11(rng): return _scene_pairs(rng, use_grey=False, npairs=2)
def _pdist(p):
    ra, ca_ = _center(p["a"]); rb, cb_ = _center(p["b"])
    return abs(ra - rb) + abs(ca_ - cb_)
def tf11(g):
    pairs, _ = _pairs_from_grid(g)
    if len(pairs) < 2: return None
    far = max(pairs, key=_pdist); out = copy(g)
    _paint(out, far["a"], 4); _paint(out, far["b"], 4)
    return out
rule("pair_highlight_greatest_separation", "The pair whose two members are farthest apart is recoloured 4; the rest stay unchanged.", gi11, tf11)


# ---------- 12 delete the smaller of each pair ----------
def gi12(rng): return _scene_pairs(rng, use_grey=False, same_shape=False)
def tf12(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False
    for p in pairs:
        a, b = p["a"], p["b"]
        if len(a) == len(b): continue
        _clear(out, a if len(a) < len(b) else b); changed = True
    return out if changed else None
rule("pair_delete_smaller_member", "The smaller member of each pair is erased, leaving only the larger one.", gi12, tf12)


# ---------- 13 swap the pair's two positions ----------
def gi13(rng): return _scene_pairs(rng, use_grey=False, same_shape=False)
def tf13(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False
    for p in pairs:
        a, b, ca_, cb_ = p["a"], p["b"], p["ca"], p["cb"]
        ra, ca2 = _anchor(a); rb, cb2 = _anchor(b)
        if (ra, ca2) == (rb, cb2): continue
        rela, relb = _rel(a), _rel(b)
        _clear(out, a); _clear(out, b)
        _stamp(out, rela, rb, cb2, ca_); _stamp(out, relb, ra, ca2, cb_)
        changed = True
    return out if changed else None
rule("pair_swap_positions", "The two members of each pair trade places, keeping their own shape and colour.", gi13, tf13)


# ---------- 14 recolour by which member of the pair is bigger ----------
def gi14(rng): return _scene_pairs(rng, use_grey=False, same_shape=False)
def tf14(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False
    for p in pairs:
        a, b = p["a"], p["b"]
        if len(a) == len(b): continue
        big, small = (a, b) if len(a) > len(b) else (b, a)
        _paint(out, big, 2); _paint(out, small, 6); changed = True
    return out if changed else None
rule("pair_recolour_by_relative_size", "In each pair the bigger shape becomes colour 2 and the smaller becomes colour 6.", gi14, tf14)


# ---------- 15 connect only pairs that include a grey member ----------
def gi15(rng): return _scene_pairs(rng, use_grey=None)
def tf15(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False
    for p in pairs:
        if GREY not in (p["ca"], p["cb"]): continue
        _connect(out, p["a"], p["b"], p["dot"]); changed = True
    return out if changed else None
rule("pair_connect_grey_pairs_only", "Only pairs that contain a grey member are joined by a line; the rest are untouched.", gi15, tf15)


# ---------- 16 delete every grey member ----------
def gi16(rng): return _scene_pairs(rng, use_grey=None)
def tf16(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False
    for p in pairs:
        if p["ca"] == GREY: _clear(out, p["a"]); changed = True
        if p["cb"] == GREY: _clear(out, p["b"]); changed = True
    return out if changed else None
rule("pair_delete_grey_members", "Every grey member of a pair is deleted, leaving its coloured partner in place.", gi16, tf16, primitive=True)
# ---------- 17 recolour unpaired objects instead of deleting them ----------
def gi17(rng): return _scene_pairs(rng, use_grey=False, npairs=2, unpaired=1)
def tf17(g):
    pairs, unmatched = _pairs_from_grid(g)
    if not unmatched: return None
    out = copy(g)
    for s in unmatched: _paint(out, s, 9)
    return out
rule("pair_recolour_unpaired_objects", "Any object with no partner is recoloured 9 instead of being deleted.", gi17, tf17)


# ---------- 18 outline the union of each pair's bounding boxes ----------
def gi18(rng): return _scene_pairs(rng, use_grey=False)
def tf18(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False
    for p in pairs:
        r0, c0, r1, c1 = bbox(p["a"] + p["b"])
        rect(out, r0, c0, r1, c1, p["dot"], fill=False); changed = True
    return out if changed else None
rule("pair_outline_union_box", "A rectangle in the dot colour is drawn around the smallest box containing both members of each pair.", gi18, tf18)


# ---------- 19 the larger member moves onto the smaller member's spot ----------
def gi19(rng): return _scene_pairs(rng, use_grey=False, same_shape=False)
def tf19(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False
    for p in pairs:
        a, b, ca_, cb_ = p["a"], p["b"], p["ca"], p["cb"]
        if len(a) == len(b): continue
        big, small, bigcol = (a, b, ca_) if len(a) > len(b) else (b, a, cb_)
        _clear(out, big); r0, c0 = _anchor(small)
        _stamp(out, _rel(big), r0, c0, bigcol); changed = True
    return out if changed else None
rule("pair_larger_moves_to_smaller", "The larger member of each pair relocates to sit where the smaller one is anchored.", gi19, tf19)


# ---------- 20 one row listing each pair's dot colour ----------
def gi20(rng): return _scene_pairs(rng, use_grey=False, npairs=2)
def tf20(g):
    pairs, _ = _pairs_from_grid(g)
    if len(pairs) < 2: return None
    ordered = sorted(pairs, key=lambda p: min(_anchor(p["a"])[1], _anchor(p["b"])[1]))
    return [[p["dot"] for p in ordered]]
rule("pair_count_to_row", "Output one row listing each pair's dot colour, ordered left to right by position.", gi20, tf20)


# ---------- 21 bar chart of each pair's separation ----------
def gi21(rng): return _scene_pairs(rng, use_grey=False, npairs=2)
def tf21(g):
    pairs, _ = _pairs_from_grid(g)
    if len(pairs) < 2: return None
    dists = [max(1, min(int(round(_pdist(p))), 30)) for p in pairs]
    w = max(dists); out = blank(len(pairs), w)
    for i, p in enumerate(pairs):
        for c in range(dists[i]): out[i][c] = p["dot"]
    return out
rule("pair_distance_to_bar", "Output one bar per pair, in its dot colour, whose length is the distance between the pair's members.", gi21, tf21)


# ---------- 22 fill each pair's bounding boxes solid with the dot colour ----------
def gi22(rng): return _scene_pairs(rng, use_grey=False)
def tf22(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False
    for p in pairs:
        for comp in (p["a"], p["b"]):
            r0, c0, r1, c1 = bbox(comp)
            rect(out, r0, c0, r1, c1, p["dot"], fill=True)
        changed = True
    return out if changed else None
rule("pair_fill_boxes_with_dot_colour", "Each member's bounding box is filled solid with the pair's dot colour.", gi22, tf22)


# ---------- 23 recolour by parity of the size difference ----------
def gi23(rng): return _scene_pairs(rng, use_grey=False, same_shape=None)
def tf23(g):
    pairs, _ = _pairs_from_grid(g)
    if not pairs: return None
    out = copy(g)
    for p in pairs:
        diff = abs(len(p["a"]) - len(p["b"]))
        col = 1 if diff % 2 == 0 else 7
        _paint(out, p["a"], col); _paint(out, p["b"], col)
    return out
rule("pair_recolour_by_size_parity", "Each pair is recoloured 1 if its size difference is even, 7 if odd.", gi23, tf23)


# ---------- 24 the two members of a pair swap colours ----------
def gi24(rng): return _scene_pairs(rng, use_grey=False)
def tf24(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False
    for p in pairs:
        if p["ca"] == p["cb"]: continue
        _paint(out, p["a"], p["cb"]); _paint(out, p["b"], p["ca"]); changed = True
    return out if changed else None
rule("pair_swap_colours", "The two members of every pair exchange colours with each other.", gi24, tf24)


# ---------- 25 one member mirrors through its partner's centre ----------
def gi25(rng): return _scene_pairs(rng, use_grey=False, hi=16)
def tf25(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False; H, W = dims(g)
    for p in pairs:
        a, b, ca_ = p["a"], p["b"], p["ca"]
        ra, ca2 = _anchor(a); rb, cb2 = _center(b)
        nr, nc = int(2 * rb - ra), int(2 * cb2 - ca2)
        rel = _rel(a)
        maxr = max(r for r, _ in rel); maxc = max(c for _, c in rel)
        if 0 <= nr and nr + maxr < H and 0 <= nc and nc + maxc < W:
            _clear(out, a); _stamp(out, rel, nr, nc, ca_); changed = True
    return out if changed else None
rule("pair_mirror_across_partner", "One member of each pair jumps to the point reflection of its own position through its partner's centre.", gi25, tf25)


# ---------- 26 recolour the markers, not the shapes, by shape match ----------
def gi26(rng): return _scene_pairs(rng, use_grey=False, same_shape=None)
def tf26(g):
    pairs, _ = _pairs_from_grid(g)
    if not pairs: return None
    out = copy(g); H, W = dims(g)
    for p in pairs:
        newcol = 3 if _rel(p["a"]) == _rel(p["b"]) else 8
        for r in range(H):
            for c in range(W):
                if g[r][c] == p["dot"]: out[r][c] = newcol
    return out
rule("pair_recolour_marker_by_shape_match", "Each pair's dot markers turn 3 if its two shapes match, 8 if they do not; the shapes themselves are untouched.", gi26, tf26)


# ---------- 27 grey becomes a bar sized by its partner's cell count ----------
def gi27(rng): return _scene_pairs(rng, use_grey=True, hi=16)
def tf27(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False; W = dims(g)[1]
    for p in pairs:
        if p["ca"] == GREY: gmem, plen = p["a"], len(p["b"])
        elif p["cb"] == GREY: gmem, plen = p["b"], len(p["a"])
        else: continue
        _clear(out, gmem); r0, c0 = _anchor(gmem)
        for i in range(plen):
            if c0 + i < W: out[r0][c0 + i] = GREY
        changed = True
    return out if changed else None
rule("pair_grey_becomes_size_bar", "The grey member of each pair is replaced by a grey bar as long as its partner's cell count.", gi27, tf27)


# ---------- 28 recolour the taller member of each pair ----------
def gi28(rng): return _scene_pairs(rng, use_grey=False, same_shape=False)
def tf28(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False
    for p in pairs:
        r0a, c0a, r1a, c1a = bbox(p["a"]); r0b, c0b, r1b, c1b = bbox(p["b"])
        ha, hb = r1a - r0a + 1, r1b - r0b + 1
        if ha == hb: continue
        taller = p["a"] if ha > hb else p["b"]
        _paint(out, taller, p["dot"]); changed = True
    return out if changed else None
rule("pair_recolour_taller_member", "Whichever member of a pair stands taller is recoloured with the pair's dot colour.", gi28, tf28)


# ---------- 29 classify each pair as more horizontal or more vertical ----------
def gi29(rng): return _scene_pairs(rng, use_grey=False)
def tf29(g):
    pairs, _ = _pairs_from_grid(g)
    if not pairs: return None
    out = copy(g)
    for p in pairs:
        ra, ca_ = _center(p["a"]); rb, cb_ = _center(p["b"])
        col = 2 if abs(ra - rb) <= abs(ca_ - cb_) else 6
        _paint(out, p["a"], col); _paint(out, p["b"], col)
    return out
rule("pair_classify_alignment", "Each pair is recoloured 2 if its members sit more side by side, 6 if more one above the other.", gi29, tf29)


# ---------- 30 overlay partner's shape onto bg cells of a's position ----------
def gi30(rng): return _scene_pairs(rng, use_grey=False, same_shape=False, hi=16)
def tf30(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False; H, W = dims(g)
    for p in pairs:
        a, b, cb_ = p["a"], p["b"], p["cb"]
        r0, c0 = _anchor(a)
        for r, c in _rel(b):
            rr, cc = r0 + r, c0 + c
            if 0 <= rr < H and 0 <= cc < W and out[rr][cc] == 0:
                out[rr][cc] = cb_; changed = True
    return out if changed else None
rule("pair_overlay_partner_shape", "Each object gains its partner's shape stamped on top of it, in the partner's colour, wherever that falls on background.", gi30, tf30)


# ---------- 31 grey mirrors partner's shape instead of copying it ----------
def gi31(rng): return _scene_pairs(rng, use_grey=True, same_shape=False)
def tf31(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False
    for p in pairs:
        if p["ca"] == GREY: gmem, partner = p["a"], p["b"]
        elif p["cb"] == GREY: gmem, partner = p["b"], p["a"]
        else: continue
        rel = _rel(partner); maxc = max(c for _, c in rel)
        mirrored = [(r, maxc - c) for r, c in rel]
        _clear(out, gmem); r0, c0 = _anchor(gmem)
        _stamp(out, mirrored, r0, c0, GREY); changed = True
    return out if changed else None
rule("pair_grey_mirrors_partner_shape", "The grey member of each pair takes the left-right mirror of its partner's shape, in grey.", gi31, tf31)


# ---------- 32 highlight the pair with the greatest combined size ----------
def gi32(rng): return _scene_pairs(rng, use_grey=False, npairs=2, same_shape=None)
def tf32(g):
    pairs, _ = _pairs_from_grid(g)
    if len(pairs) < 2: return None
    biggest = max(pairs, key=lambda p: len(p["a"]) + len(p["b"]))
    out = copy(g)
    _paint(out, biggest["a"], 4); _paint(out, biggest["b"], 4)
    return out
rule("pair_highlight_largest_total_pair", "The pair whose two members together hold the most cells is recoloured 4.", gi32, tf32)


# ---------- 33 delete the closest pair ----------
def gi33(rng): return _scene_pairs(rng, use_grey=False, npairs=2)
def tf33(g):
    pairs, _ = _pairs_from_grid(g)
    if len(pairs) < 2: return None
    closest = min(pairs, key=_pdist); out = copy(g)
    _clear(out, closest["a"]); _clear(out, closest["b"])
    return out
rule("pair_delete_closest_pair", "The pair whose two members sit nearest each other is deleted; the rest remain.", gi33, tf33)


# ---------- 34 keep only the pair with the greatest combined size ----------
def gi34(rng): return _scene_pairs(rng, use_grey=False, npairs=2, same_shape=None)
def tf34(g):
    pairs, _ = _pairs_from_grid(g)
    if len(pairs) < 2: return None
    biggest = max(pairs, key=lambda p: len(p["a"]) + len(p["b"]))
    out = copy(g)
    for p in pairs:
        if p is biggest: continue
        _clear(out, p["a"]); _clear(out, p["b"])
    return out
rule("pair_keep_only_largest_pair", "Only the pair with the greatest combined cell count survives; every other pair is erased.", gi34, tf34)


# ---------- 35 recolour each pair's markers by its size rank ----------
def gi35(rng): return _scene_pairs(rng, use_grey=False, npairs=3, same_shape=None)
def tf35(g):
    pairs, _ = _pairs_from_grid(g)
    if len(pairs) < 2: return None
    ranked = sorted(pairs, key=lambda p: len(p["a"]) + len(p["b"]))
    out = copy(g); H, W = dims(g)
    rankcols = [1, 2, 3, 4]
    for rank, p in zip(rankcols, ranked):
        for r in range(H):
            for c in range(W):
                if g[r][c] == p["dot"]: out[r][c] = rank
    return out
rule("pair_recolour_markers_by_rank", "Each pair's dot markers are recoloured by the pair's rank in combined size, smallest pair getting colour 1.", gi35, tf35)


# ---------- 36 grey takes the outline of partner's bounding box ----------
def gi36(rng): return _scene_pairs(rng, use_grey=True, same_shape=False, hi=16)
def tf36(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False; H, W = dims(g)
    for p in pairs:
        if p["ca"] == GREY: gmem, partner = p["a"], p["b"]
        elif p["cb"] == GREY: gmem, partner = p["b"], p["a"]
        else: continue
        r0p, c0p, r1p, c1p = bbox(partner)
        ph, pw = r1p - r0p + 1, c1p - c0p + 1
        _clear(out, gmem); r0, c0 = _anchor(gmem)
        r1, c1 = min(r0 + ph - 1, H - 1), min(c0 + pw - 1, W - 1)
        rect(out, r0, c0, r1, c1, GREY, fill=False); changed = True
    return out if changed else None
rule("pair_grey_takes_partner_bbox_outline", "The grey member of each pair is replaced by a grey outline the size of its partner's bounding box.", gi36, tf36)


# ---------- 37 recolour both members of a pair with its dot colour ----------
def gi37(rng): return _scene_pairs(rng, use_grey=False)
def tf37(g):
    pairs, _ = _pairs_from_grid(g)
    if not pairs: return None
    out = copy(g)
    for p in pairs:
        _paint(out, p["a"], p["dot"]); _paint(out, p["b"], p["dot"])
    return out
rule("pair_recolour_members_with_dot_colour", "Both members of every pair are repainted in that pair's own dot colour.", gi37, tf37)


# ---------- 38 outline the larger member of each pair ----------
def gi38(rng): return _scene_pairs(rng, use_grey=False, same_shape=False)
def tf38(g):
    pairs, _ = _pairs_from_grid(g); out = copy(g); changed = False; H, W = dims(g)
    for p in pairs:
        a, b = p["a"], p["b"]
        if len(a) == len(b): continue
        big = a if len(a) > len(b) else b
        r0, c0, r1, c1 = bbox(big)
        rect(out, max(r0 - 1, 0), max(c0 - 1, 0), min(r1 + 1, H - 1), min(c1 + 1, W - 1), p["dot"], fill=False)
        changed = True
    return out if changed else None
rule("pair_outline_larger_member", "A ring in the dot colour is drawn just outside the larger member of each pair.", gi38, tf38)


# ---------- 39 bar chart of each pair's combined size ----------
def gi39(rng): return _scene_pairs(rng, use_grey=False, npairs=2, same_shape=None)
def tf39(g):
    pairs, _ = _pairs_from_grid(g)
    if len(pairs) < 2: return None
    totals = [len(p["a"]) + len(p["b"]) for p in pairs]
    w = max(totals); out = blank(len(pairs), w)
    for i, p in enumerate(pairs):
        for c in range(totals[i]): out[i][c] = p["dot"]
    return out
rule("pair_total_size_to_bar", "Output one bar per pair, in its dot colour, as long as the pair's combined cell count.", gi39, tf39)


# ---------- 40 highlight the pair nearest the grid's centre ----------
def gi40(rng): return _scene_pairs(rng, use_grey=False, npairs=2)
def tf40(g):
    pairs, _ = _pairs_from_grid(g)
    if len(pairs) < 2: return None
    H, W = dims(g); gc_r, gc_c = (H - 1) / 2.0, (W - 1) / 2.0
    def d(p):
        ra, ca_ = _center(p["a"]); rb, cb_ = _center(p["b"])
        return abs((ra + rb) / 2 - gc_r) + abs((ca_ + cb_) / 2 - gc_c)
    nearest = min(pairs, key=d)
    out = copy(g)
    _paint(out, nearest["a"], 4); _paint(out, nearest["b"], 4)
    return out
rule("pair_highlight_center_pair", "The pair whose midpoint sits closest to the centre of the grid is recoloured 4.", gi40, tf40)
