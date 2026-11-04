# b029_fitting.py -- pieces, holes and packing: loose pieces that fit holes (as is, rotated, mirrored, scaled),
# the piece that fits nothing, holes that nothing fits, pieces joined into rectangles, plugs and gaps, pieces
# packed into containers and bins, cuts along marked lines, shapes and their negatives.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


# ---------------------------------------------------------------- helpers
def _size(rng, lo=10, hi=20):
    """Grid dims; about 40% of inputs land both sides in the 21-30 band."""
    if rng.random() < 0.4:
        return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _norm(cells_):
    r0 = min(r for r, _ in cells_); c0 = min(c for _, c in cells_)
    return frozenset((r - r0, c - c0) for r, c in cells_)


def _shape(rng, lo, hi):
    return _norm(random_shape(rng, rng.randint(lo, hi)))


def _hw(sh):
    return max(r for r, _ in sh) + 1, max(c for _, c in sh) + 1


def _is_rect(sh):
    h, w = _hw(sh); return len(sh) == h * w


def _rot(sh):
    return _norm({(c, -r) for r, c in sh})


def _rots(sh):
    out = []; s = sh
    for _ in range(4):
        out.append(s); s = _rot(s)
    return out


def _flip(sh):
    return _norm({(r, -c) for r, c in sh})


def _syms(sh):
    return set(_rots(sh)) | set(_rots(_flip(sh)))


def _scale2(sh):
    return frozenset((2 * r + dr, 2 * c + dc) for r, c in sh for dr in (0, 1) for dc in (0, 1))


def _stamp(g, sh, r0, c0, col):
    for r, c in sh:
        g[r0 + r][c0 + c] = col


def _free(g, sh, r0, c0, margin=1):
    H, W = dims(g); h, w = _hw(sh)
    if r0 < 0 or c0 < 0 or r0 + h > H or c0 + w > W:
        return False
    return all(g[r][c] == 0 for r in range(r0 - margin, r0 + h + margin) for c in range(c0 - margin, c0 + w + margin)
               if 0 <= r < H and 0 <= c < W)


def _put(rng, g, sh, col, margin=1, tries=120, rows=None, cols_=None):
    """Stamp sh at a random spot whose bounding box plus margin is empty; rows/cols_ bound the top-left corner."""
    H, W = dims(g); h, w = _hw(sh)
    rlo, rhi = rows or (0, H - h); clo, chi = cols_ or (0, W - w)
    rhi, chi = min(rhi, H - h), min(chi, W - w)
    if rlo > rhi or clo > chi:
        return None
    for _ in range(tries):
        r0, c0 = rng.randint(rlo, rhi), rng.randint(clo, chi)
        if _free(g, sh, r0, c0, margin):
            _stamp(g, sh, r0, c0, col); return r0, c0
    return None


def _distinct(rng, k, lo, hi, avoid=(), under=lambda s: {s}, ok=lambda s: True):
    """k shapes pairwise distinct (under the given equivalence) and distinct from every shape in avoid."""
    out, seen = [], set()
    for a in avoid:
        seen |= under(a)
    for _ in range(300):
        if len(out) == k:
            return out
        s = _shape(rng, lo, hi)
        if ok(s) and not (under(s) & seen):
            seen |= under(s); out.append(s)
    return None


def _blobs(g, bg=0, conn8=False):
    """Connected components of non-background cells regardless of colour."""
    H, W = dims(g); seen, out = set(), []
    nb = [(-1, 0), (1, 0), (0, -1), (0, 1)] + ([(-1, -1), (-1, 1), (1, -1), (1, 1)] if conn8 else [])
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or (r, c) in seen:
                continue
            comp, st = [], [(r, c)]; seen.add((r, c))
            while st:
                y, x = st.pop(); comp.append((y, x))
                for dy, dx in nb:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen and g[ny][nx] != bg:
                        seen.add((ny, nx)); st.append((ny, nx))
            out.append(comp)
    return out


def _col(g, cells_):
    return g[cells_[0][0]][cells_[0][1]]


def _holes(g, blk):
    """Empty components inside the block's bounding box, as lists of grid cells."""
    r0, c0, r1, c1 = bbox(blk); sub = crop(g, r0, c0, r1, c1)
    return [[(r + r0, c + c0) for r, c in comp] for comp in components(sub, 0)]


def _inner(g, blk):
    """Non-block-colour, non-empty components inside the block's bounding box (embedded pieces)."""
    r0, c0, r1, c1 = bbox(blk); A = g[r0][c0]; sub = crop(g, r0, c0, r1, c1)
    return [[(r + r0, c + c0) for r, c in comp] for comp in components(sub, lambda v: v not in (0, A))]


def _block_with_holes(rng, g, holes, col, slack=3, margin=1, layout=None):
    """A solid rectangle of colour col with the given hole shapes punched out, at least `margin` block cells
    between holes and from the edge. Returns (r0, c0, bh, bw, [hole anchors]) or None."""
    H, W = dims(g); hs = [_hw(s) for s in holes]; m = margin
    if (layout or rng.choice("hv")) == "h":
        bh = max(h for h, _ in hs) + 2 * m + rng.randint(0, slack); bw = sum(w for _, w in hs) + m * (len(holes) + 1) + rng.randint(0, slack)
    else:
        bh = sum(h for h, _ in hs) + m * (len(holes) + 1) + rng.randint(0, slack); bw = max(w for _, w in hs) + 2 * m + rng.randint(0, slack)
    if bh > H - 2 or bw > W - 2:
        return None
    tmp = blank(bh + 2 * m, bw + 2 * m)
    for r in range(bh + 2 * m):
        for c in range(bw + 2 * m):
            if r < m or c < m or r >= bh + m or c >= bw + m:
                tmp[r][c] = 9
    pos = []
    for s in holes:
        p = _put(rng, tmp, s, 1, margin=m, rows=(m, bh + m), cols_=(m, bw + m))
        if p is None:
            return None
        pos.append((p[0] - m, p[1] - m))
    r0, c0 = rng.randint(0, H - bh), rng.randint(0, W - bw)
    if not all(g[r][c] == 0 for r in range(max(0, r0 - 1), min(H, r0 + bh + 1)) for c in range(max(0, c0 - 1), min(W, c0 + bw + 1))):
        return None
    for r in range(bh):
        for c in range(bw):
            g[r0 + r][c0 + c] = 0 if tmp[r + m][c + m] == 1 else col
    return r0, c0, bh, bw, [(r0 + a, c0 + b) for a, b in pos]


def _frame_shape(fh, fw):
    return frozenset((r, c) for r in range(fh) for c in range(fw) if r in (0, fh - 1) or c in (0, fw - 1))


def _rect_shape(h, w):
    return frozenset((r, c) for r in range(h) for c in range(w))


def _mask(g, r0, c0, r1, c1, v):
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if g[r][c] == 0 or g[r][c] == -1:
                g[r][c] = v


def _unmask(g):
    for row in g:
        for c, v in enumerate(row):
            if v == -1:
                row[c] = 0
    return g


def _biggest(g, conn8=False):
    obs = _blobs(g, conn8=conn8); return obs, max(obs, key=len)


def _fit_pieces(g, obs, blk, hole, under=lambda s: {s}):
    hn = _norm(hole)
    return [o for o in obs if o is not blk and hn in under(_norm(o))]


def _rect_pairs(obs):
    """Pairs (P, Q, dr, dc) whose union after shifting Q by (dr, dc) relative to P is a solid rectangle."""
    out = []
    for i, P in enumerate(obs):
        for Q in obs[i + 1:]:
            p, q = _norm(P), _norm(Q); hp, wp = _hw(p); hq, wq = _hw(q)
            for dr in range(-hq, hp + 1):
                for dc in range(-wq, wp + 1):
                    qs = {(r + dr, c + dc) for r, c in q}
                    if qs & p:
                        continue
                    u = p | qs; h, w = _hw(_norm(u))
                    if h * w == len(u):
                        out.append((P, Q, dr, dc))
    return out


def _nonrect(s):
    return not _is_rect(s)


# ---------------------------------------------------------------- 1 several holes, several pieces
def _multi_hole_scene(rng, k_lo=2, k_hi=4, extra=0, missing=0, under=lambda s: {s}, margin=1, piece_of=lambda s: s):
    h, w = _size(rng, 12, 20); g = blank(h, w); k = rng.randint(k_lo, k_hi)
    holes = _distinct(rng, k, 3, 6, under=under)
    if not holes: return None
    A, *cs = colours(rng, k + extra + 1, exclude=(0, 5))
    if _block_with_holes(rng, g, holes, A, margin=margin) is None: return None
    pieces = [piece_of(s) for s in holes[missing:]]
    if extra:
        more = _distinct(rng, extra, 3, 6, avoid=holes, under=under)
        if not more: return None
        pieces += more
    rng.shuffle(pieces)
    for s, c in zip(pieces, cs):
        if _put(rng, g, s, c) is None: return None
    return g


def tf_each_hole(g):
    obs, blk = _biggest(g); out = copy(g)
    for hole in _holes(g, blk):
        fits = _fit_pieces(g, obs, blk, hole)
        if len(fits) != 1: return None
        col = _col(g, fits[0])
        for r, c in fits[0]: out[r][c] = 0
        for r, c in hole: out[r][c] = col
    return out
rule("pieces_each_into_matching_hole", "The big block has several holes; each loose piece moves into the one hole its shape exactly fits, leaving its old place empty.",
     lambda rng: _multi_hole_scene(rng, 2, 4), tf_each_hole)


# 2 piece fits only after rotation
def _asym_rot(s):
    return len(set(_rots(s))) == 4
def _rotated_copy(rng, s):
    return rng.choice([t for t in _rots(s) if t != s])
def gi_rotated(rng):
    h, w = _size(rng, 11, 20); g = blank(h, w)
    hole = _distinct(rng, 1, 4, 7, ok=_asym_rot)
    if not hole: return None
    hole = hole[0]; k = rng.randint(1, 3); A, *cs = colours(rng, k + 2)
    if _block_with_holes(rng, g, [hole], A) is None: return None
    others = _distinct(rng, k, 3, 6, avoid=[hole], under=lambda s: set(_rots(s)))
    if not others: return None
    pieces = [_rotated_copy(rng, hole)] + others; rng.shuffle(pieces)
    for s, c in zip(pieces, cs):
        if _put(rng, g, s, c) is None: return None
    return g
def tf_rotated(g):
    obs, blk = _biggest(g); holes = _holes(g, blk)
    if len(holes) != 1: return None
    fits = _fit_pieces(g, obs, blk, holes[0], under=lambda s: set(_rots(s)))
    if len(fits) != 1: return None
    out = copy(g); col = _col(g, fits[0])
    for r, c in fits[0]: out[r][c] = 0
    for r, c in holes[0]: out[r][c] = col
    return out
rule("rotated_piece_into_hole", "One loose piece fits the block's hole once it is turned; it is rotated and placed into the hole, and its old place is emptied.", gi_rotated, tf_rotated)


# 3 fill all holes, output just the block
def tf_fill_crop(g):
    out = tf_each_hole(g)
    if out is None: return None
    return crop(out, *bbox(max(_blobs(g), key=len)))
rule("pieces_fill_holes_crop_block", "Every loose piece is put into the hole it fits; output just the big block, now solid with the pieces showing in their own colours.",
     lambda rng: _multi_hole_scene(rng, 2, 4), tf_fill_crop)


# 4 the one piece fitting nothing turns grey
def tf_misfit(g):
    obs, blk = _biggest(g); holes = [_norm(h) for h in _holes(g, blk)]
    mis = [o for o in obs if o is not blk and _norm(o) not in holes]
    if len(mis) != 1: return None
    out = copy(g)
    for r, c in mis[0]: out[r][c] = 5
    return out
rule("misfit_piece_turns_grey", "Every loose piece fits one of the block's holes except one; that misfit piece is recoloured grey (5) and nothing else changes.",
     lambda rng: _multi_hole_scene(rng, 1, 3, extra=1), tf_misfit)


# 5 holes with no piece filled grey, pieces move in
def tf_leftover_grey(g):
    obs, blk = _biggest(g); out = copy(g)
    for hole in _holes(g, blk):
        fits = _fit_pieces(g, obs, blk, hole)
        if len(fits) > 1: return None
        col = 5 if not fits else _col(g, fits[0])
        for r, c in (fits[0] if fits else []): out[r][c] = 0
        for r, c in hole: out[r][c] = col
    return out
rule("pieces_fill_holes_leftover_holes_grey", "Each loose piece moves into the hole it fits; any hole that no piece fits is filled grey (5).",
     lambda rng: _multi_hole_scene(rng, 2, 4, missing=1), tf_leftover_grey)


# 6 two pieces that together make a rectangle are joined
def _split_rect(rng, h, w):
    cells_ = [(r, c) for r in range(h) for c in range(w)]
    for _ in range(40):
        n = rng.randint(2, h * w - 2); cur = {rng.choice(cells_)}
        while len(cur) < n:
            r, c = rng.choice(sorted(cur)); dr, dc = rng.choice([(-1, 0), (1, 0), (0, -1), (0, 1)])
            if 0 <= r + dr < h and 0 <= c + dc < w: cur.add((r + dr, c + dc))
        rest = set(cells_) - cur
        tmp = blank(h, w)
        for r, c in rest: tmp[r][c] = 1
        if len(components(tmp, 1)) == 1 and not _is_rect(_norm(cur)) and not _is_rect(_norm(rest)):
            return _norm(cur), _norm(rest)
    return None
def gi_join_rect(rng):
    H, W = _size(rng, 11, 20); g = blank(H, W); sp = _split_rect(rng, rng.randint(2, 5), rng.randint(3, 6))
    if sp is None: return None
    k = rng.randint(0, 2); cs = colours(rng, 2 + k); shapes = list(sp)
    if k:
        more = _distinct(rng, k, 3, 6, avoid=shapes)
        if not more: return None
        shapes += more
    order = list(range(len(shapes))); rng.shuffle(order)
    for i in order:
        if _put(rng, g, shapes[i], cs[i]) is None: return None
    return g if len(_rect_pairs(_blobs(g))) == 1 else None
def tf_join_rect(g):
    pr = _rect_pairs(_blobs(g))
    if len(pr) != 1: return None
    P, Q, dr, dc = pr[0]; p, q = _norm(P), _norm(Q)
    cells_ = {(r, c): _col(g, P) for r, c in p}; cells_.update({(r + dr, c + dc): _col(g, Q) for r, c in q})
    r0 = min(r for r, _ in cells_); c0 = min(c for _, c in cells_)
    h = max(r for r, _ in cells_) - r0 + 1; w = max(c for _, c in cells_) - c0 + 1; out = blank(h, w)
    for (r, c), v in cells_.items(): out[r - r0][c - c0] = v
    return out
rule("two_pieces_join_into_rectangle", "Exactly two of the loose pieces fit together into a solid rectangle; output that rectangle assembled, each piece keeping its colour.", gi_join_rect, tf_join_rect)


# 7 plug bar seals the gap in a container wall
def gi_plug(rng):
    H, W = _size(rng, 11, 20); g = blank(H, W); fh, fw = rng.randint(5, 10), rng.randint(5, 10); L = rng.randint(2, min(4, fh - 3, fw - 3))
    F, *cs = colours(rng, rng.randint(2, 4)); side = rng.randrange(4)
    fr = _frame_shape(fh, fw)
    if side < 2:
        c0 = rng.randint(1, fw - 1 - L); gap = {(0 if side == 0 else fh - 1, c0 + i) for i in range(L)}; plug = _rect_shape(1, L)
    else:
        r0 = rng.randint(1, fh - 1 - L); gap = {(r0 + i, 0 if side == 2 else fw - 1) for i in range(L)}; plug = _rect_shape(L, 1)
    if _put(rng, g, fr - gap, F) is None: return None
    _mask(g, 0, 0, H - 1, W - 1, 0)
    lens = [n for n in range(2, 6) if n != L]; rng.shuffle(lens)
    bars = [plug] + [_rect_shape(1, n) if rng.random() < 0.5 else _rect_shape(n, 1) for n in lens[:len(cs) - 1]]
    rng.shuffle(bars)
    for s, c in zip(bars, cs):
        if _put(rng, g, s, c) is None: return None
    return g
def tf_plug(g):
    obs, fr = _biggest(g); r0, c0, r1, c1 = bbox(fr); F = _col(g, fr)
    gap = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if (r in (r0, r1) or c in (c0, c1)) and g[r][c] == 0]
    if not gap: return None
    gh, gw = _hw(_norm(gap))
    fits = [o for o in obs if o is not fr and len(o) == len(gap) and _hw(_norm(o)) == (gh, gw)]
    if len(fits) != 1: return None
    out = copy(g); col = _col(g, fits[0])
    for r, c in fits[0]: out[r][c] = 0
    for r, c in gap: out[r][c] = col
    return out
rule("plug_bar_seals_container_gap", "The hollow container has a gap in one wall; the loose bar of exactly the gap's length and direction moves into the gap and seals it.", gi_plug, tf_plug)


# 8 pieces stacked into a column container from the bottom, reading order
def _u_shape(ih, iw):
    return frozenset({(r, 0) for r in range(ih + 1)} | {(r, iw + 1) for r in range(ih + 1)} | {(ih, c) for c in range(iw + 2)})
def gi_stack_col(rng):
    H, W = _size(rng, 12, 20); g = blank(H, W); iw = rng.randint(2, 5); k = rng.randint(2, 4)
    hs = [rng.randint(1, 2) for _ in range(k)]; ih = sum(hs) + rng.randint(1, 3)
    F, *cs = colours(rng, k + 1)
    p = _put(rng, g, _u_shape(ih, iw), F)
    if p is None: return None
    _mask(g, p[0] - 1, p[1], p[0] + ih, p[1] + iw + 1, -1)
    for ph, c in zip(hs, cs):
        if _put(rng, g, _rect_shape(ph, iw), c) is None: return None
    return _unmask(g)
def _stack(g, order_key, align="left"):
    obs, U = _biggest(g); r0, c0, r1, c1 = bbox(U); out = copy(g); top = r1
    pieces = sorted([o for o in obs if o is not U], key=order_key)
    for o in pieces:
        for r, c in o: out[r][c] = 0
    for o in pieces:
        pr0, pc0, pr1, pc1 = bbox(o); h = pr1 - pr0 + 1
        for r, c in o: out[top - h + (r - pr0)][c0 + 1 + (c - pc0)] = g[r][c]
        top -= h
        if top <= r0: return None
    return out
def tf_stack_col(g):
    return _stack(g, lambda o: bbox(o)[:2])
rule("pieces_stack_in_column_container_reading_order", "The bars are dropped into the open-topped column one after another in reading order (top row first, then left to right), the first landing on the floor and each next resting on the one before.",
     gi_stack_col, tf_stack_col)


# 9 cut piece along grey line, parts separate
def gi_cut(rng):
    H, W = _size(rng, 10, 20); g = blank(H, W); k = rng.randint(1, 3); cs = colours(rng, k, exclude=(0, 5))
    for c in cs:
        h, w = rng.randint(3, 7), rng.randint(3, 7); p = _put(rng, g, _rect_shape(h, w), c, margin=2, rows=(0, H - h - 1), cols_=(0, W - w - 1))
        if p is None: return None
        if rng.random() < 0.5:
            r = p[0] + rng.randint(1, h - 2)
            for x in range(p[1], p[1] + w): g[r][x] = 5
        else:
            x = p[1] + rng.randint(1, w - 2)
            for r in range(p[0], p[0] + h): g[r][x] = 5
    return g
def _cuts(g, min_size=1):
    """Per blob of at least min_size cells: (cells, grey cells, horizontal?) with the grey line spanning the bbox."""
    out = []
    for o in _blobs(g):
        if len(o) < min_size: continue
        r0, c0, r1, c1 = bbox(o); grey = [(r, c) for r, c in o if g[r][c] == 5]
        if not grey: return None
        rows = {r for r, _ in grey}; cols_ = {c for _, c in grey}
        if len(rows) == 1 and len(grey) == c1 - c0 + 1: out.append((o, grey, True))
        elif len(cols_) == 1 and len(grey) == r1 - r0 + 1: out.append((o, grey, False))
        else: return None
    return out
def tf_cut(g):
    cuts = _cuts(g)
    if not cuts: return None
    H, W = dims(g); out = copy(g)
    for o, grey, horiz in cuts:
        gr, gc = grey[0]
        far = [(r, c) for r, c in o if (r > gr if horiz else c > gc)]
        for r, c in grey + far: out[r][c] = 0
        for r, c in far:
            nr, nc = (r + 1, c) if horiz else (r, c + 1)
            if nr >= H or nc >= W: return None
            out[nr][nc] = g[r][c]
    return out
rule("piece_cut_along_grey_line_parts_separate", "Each block is cut along its grey line: the grey cells vanish and the part below (or right of) the line moves one cell further away, leaving a two-cell gap.", gi_cut, tf_cut)


# 10 pieces replaced by their negative inside their bounding box
def gi_negate(rng):
    H, W = _size(rng, 8, 18); g = blank(H, W); k = rng.randint(1, 4)
    shapes = _distinct(rng, k, 4, 9, ok=lambda s: _nonrect(s) and min(_hw(s)) >= 2)
    if not shapes: return None
    for s, c in zip(shapes, [rng.choice(COLOURS) for _ in range(k)]):
        if _put(rng, g, s, c) is None: return None
    return g
def tf_negate(g):
    out = copy(g)
    for o in objects(g, 0, conn8=False):
        r0, c0, r1, c1 = bbox(o); col = _col(g, o); cells_ = set(o)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                out[r][c] = 0 if (r, c) in cells_ else col
    return out
rule("pieces_negated_in_bounding_box", "Every piece is replaced by its negative: inside its bounding box the filled cells become empty and the empty cells take the piece's colour.", gi_negate, tf_negate)


# 11 shape and its negative swap places
def gi_swap_neg(rng):
    H, W = _size(rng, 8, 18); g = blank(H, W); A, B = colours(rng, 2)
    for _ in range(30):
        s = _shape(rng, 4, 10); h, w = _hw(s)
        if min(h, w) < 2 or _is_rect(s): continue
        neg = frozenset((r, c) for r in range(h) for c in range(w) if (r, c) not in s)
        if _hw(neg) != (h, w) or min(r for r, _ in neg) or min(c for _, c in neg): continue
        break
    else: return None
    if _put(rng, g, s, A) is None or _put(rng, g, neg, B) is None: return None
    return g
def tf_swap_neg(g):
    cols_ = sorted(set(v for row in g for v in row if v))
    if len(cols_) != 2: return None
    a = cells(g, lambda v: v == cols_[0]); b = cells(g, lambda v: v == cols_[1])
    ba, bb = bbox(a), bbox(b)
    if (ba[2] - ba[0], ba[3] - ba[1]) != (bb[2] - bb[0], bb[3] - bb[1]): return None
    out = blank(*dims(g))
    for r, c in _norm(a): out[bb[0] + r][bb[1] + c] = cols_[0]
    for r, c in _norm(b): out[ba[0] + r][ba[1] + c] = cols_[1]
    return out
rule("shape_swaps_place_with_its_negative", "The grid holds a shape and its negative (the rest of the same box); the two trade places, each drawn where the other was in its own colour.", gi_swap_neg, tf_swap_neg)


# 12 pieces sorted into bins by cell count; bins carry capacity marks
def gi_bins(rng):
    H, W = _size(rng, 14, 22); g = blank(H, W); ns = rng.sample([2, 3, 4, 5], rng.randint(2, 3))
    F = rng.choice([c for c in COLOURS if c != 5]); pieces = []
    for n in ns:
        cnt = rng.randint(1, 3); iw = max(4 * cnt - 1, n); fr = set(_frame_shape(5, iw + 2))
        p = _put(rng, g, frozenset(fr), F, margin=1)
        if p is None: return None
        for i in range(n): g[p[0]][p[1] + 1 + i] = 5
        _mask(g, p[0] + 1, p[1] + 1, p[0] + 3, p[1] + iw, -1)
        for _ in range(cnt):
            pieces.append(_norm(random_shape(rng, n)))
    pieces = [s for s in pieces if max(_hw(s)) <= 3]
    if len(pieces) < sum(1 for _ in ns) or len(pieces) < 2: return None
    rng.shuffle(pieces)
    for s in pieces:
        if _put(rng, g, s, rng.choice([c for c in COLOURS if c not in (5, F)])) is None: return None
    return _unmask(g)
def tf_bins(g):
    obs = _blobs(g); bins = [o for o in obs if any(g[r][c] == 5 for r, c in o)]; pieces = [o for o in obs if o not in bins]
    out = copy(g)
    for o in pieces:
        for r, c in o: out[r][c] = 0
    for b in bins:
        n = sum(1 for r, c in b if g[r][c] == 5); r0, c0, r1, c1 = bbox(b)
        mine = sorted([o for o in pieces if len(o) == n], key=lambda o: bbox(o)[:2])
        for i, o in enumerate(mine):
            pr0, pc0, _, pc1 = bbox(o)
            if c0 + 1 + 4 * i + (pc1 - pc0) >= c1: return None
            for r, c in o: out[r0 + 1 + (r - pr0)][c0 + 1 + 4 * i + (c - pc0)] = g[r][c]
    return out if out != g else None
rule("pieces_sorted_into_bins_by_capacity_marks", "Each bin's top wall carries grey marks; every loose piece moves into the bin whose mark count equals its cell count, pieces lined up left to right inside in reading order.", gi_bins, tf_bins)


# 13 the piece completing a symmetric figure is placed
def gi_sym_complete(rng):
    H, W = _size(rng, 11, 20); g = blank(H, W); A, B, *cs = colours(rng, rng.randint(3, 5))
    for _ in range(40):
        half = _shape(rng, 5, 10); h, w = _hw(half)
        fig = set(half) | {(r, 2 * w - 1 - c) for r, c in half}
        right = sorted((r, c) for r, c in fig if c >= w)
        n = rng.randint(2, min(5, len(right) - 1)); chunk = {rng.choice(right)}
        while len(chunk) < n:
            r, c = rng.choice(sorted(chunk)); dr, dc = rng.choice([(-1, 0), (1, 0), (0, -1), (0, 1)])
            if (r + dr, c + dc) in fig and c + dc >= w: chunk.add((r + dr, c + dc))
        rest = fig - chunk
        tmp = blank(h, 2 * w)
        for r, c in rest: tmp[r][c] = 1
        if len(components(tmp, 1, conn8=True)) == 1 and _hw(_norm(rest)) == (h, 2 * w) and min(min(rest)) == 0 and min(c for _, c in rest) == 0:
            break
    else: return None
    if _put(rng, g, frozenset(rest), A) is None: return None
    ch = _norm(chunk); others = _distinct(rng, len(cs), 2, 5, avoid=[ch])
    if others is None: return None
    pieces = [ch] + others; pc = [B] + cs; order = list(range(len(pieces))); rng.shuffle(order)
    for i in order:
        if _put(rng, g, pieces[i], pc[i]) is None: return None
    return g
def tf_sym_complete(g):
    obs, fig = _biggest(g, conn8=True); r0, c0, r1, c1 = bbox(fig); cells_ = set(fig)
    missing = {(r, c0 + c1 - c) for r, c in fig if (r, c0 + c1 - c) not in cells_}
    if not missing: return None
    fits = [o for o in obs if o is not fig and _norm(o) == _norm(missing)]
    if len(fits) != 1: return None
    out = copy(g); col = _col(g, fits[0])
    for r, c in fits[0]: out[r][c] = 0
    for r, c in missing: out[r][c] = col
    return out
rule("piece_completing_symmetric_figure_placed", "The large figure is left-right symmetric except for a missing chunk; the loose piece shaped like that chunk moves in to complete the symmetry, in its own colour.",
     gi_sym_complete, tf_sym_complete)


# 14 tab pieces join notch pieces where the tab row matches
def gi_tabs(rng):
    H, W = _size(rng, 12, 22); g = blank(H, W); k = rng.randint(2, 3); hh = rng.randint(3, 6); rows = rng.sample(range(hh), k)
    cs = colours(rng, 2 * k); shapes = []
    for i, t in enumerate(rows):
        wl, wr = rng.randint(2, 4), rng.randint(2, 4)
        shapes.append(frozenset(_rect_shape(hh, wl) | {(t, wl)}))
        shapes.append(frozenset(_rect_shape(hh, wr) - {(t, 0)}))
    order = list(range(2 * k)); rng.shuffle(order)
    for i in order:
        if _put(rng, g, shapes[i], cs[i]) is None: return None
    return g
def _tab_notch(g):
    tabs, notches = [], []
    for o in _blobs(g):
        r0, c0, r1, c1 = bbox(o); hh = r1 - r0 + 1; right = [r for r, c in o if c == c1]; left = [r for r, c in o if c == c0]
        if len(right) == 1 and len(o) == hh * (c1 - c0) + 1: tabs.append((o, right[0] - r0))
        elif len(left) == hh - 1 and len(o) == hh * (c1 - c0 + 1) - 1: notches.append((o, next(r for r in range(r0, r1 + 1) if r not in left) - r0))
        else: return None
    return tabs, notches
def tf_tabs(g):
    tn = _tab_notch(g)
    if not tn: return None
    tabs, notches = tn; rows = []
    for o, t in sorted(tabs, key=lambda x: bbox(x[0])[:2]):
        m = [n for n, u in notches if u == t]
        if len(m) != 1: return None
        a = crop(g, *bbox(o)); b = crop(g, *bbox(m[0])); joined = [row + [0] * len(b[0]) for row in a]
        paste(joined, b, 0, len(a[0]) - 1, transparent=0); rows.append(joined)
    w = max(len(r[0]) for r in rows); out = []
    for i, blk in enumerate(rows):
        out += [row + [0] * (w - len(row)) for row in blk] + ([[0] * w] if i < len(rows) - 1 else [])
    return out
rule("tab_pieces_join_notch_pieces", "Each piece with a tab sticking out of its right side fits the piece with a notch at the same height on its left side; output the joined pairs stacked top to bottom in the tab pieces' reading order, one empty row apart.",
     gi_tabs, tf_tabs)


# 15 hole shape output as a solid piece
def gi_hole_solid(rng):
    H, W = _size(rng, 10, 20); g = blank(H, W); hole = _distinct(rng, 1, 4, 9, ok=_nonrect)
    if not hole: return None
    k = rng.randint(0, 3); A, *cs = colours(rng, k + 1)
    if _block_with_holes(rng, g, hole, A) is None: return None
    others = _distinct(rng, k, 3, 6, avoid=hole) if k else []
    if others is None: return None
    for s, c in zip(others, cs):
        if _put(rng, g, s, c) is None: return None
    return g
def tf_hole_solid(g):
    obs, blk = _biggest(g); holes = _holes(g, blk)
    if len(holes) != 1: return None
    r0, c0, r1, c1 = bbox(holes[0]); out = blank(r1 - r0 + 1, c1 - c0 + 1)
    for r, c in holes[0]: out[r - r0][c - c0] = _col(g, blk)
    return out
rule("hole_shape_output_solid", "Output the hole cut out of the big block as a solid piece in the block's colour, cropped to the hole's bounding box.", gi_hole_solid, tf_hole_solid)


# 16 number of pieces fitting the hole as a bar
def gi_fit_count(rng):
    H, W = _size(rng, 11, 20); g = blank(H, W); hole = _shape(rng, 3, 5); n = rng.randint(1, 4); m = rng.randint(1, 3)
    A = rng.choice(COLOURS)
    if _block_with_holes(rng, g, [hole], A) is None: return None
    others = _distinct(rng, m, 3, 5, avoid=[hole])
    if not others: return None
    pieces = [hole] * n + others; rng.shuffle(pieces)
    for s in pieces:
        if _put(rng, g, s, rng.choice(COLOURS)) is None: return None
    return g
def tf_fit_count(g):
    obs, blk = _biggest(g); holes = _holes(g, blk)
    if len(holes) != 1: return None
    n = len(_fit_pieces(g, obs, blk, holes[0])); total = len(obs) - 1
    return [[_col(g, blk)] * n + [0] * (total - n)] if 0 < n < total else None
rule("fitting_piece_count_bar", "Output one row as wide as the number of loose pieces: a bar in the block's colour as long as the number of pieces that exactly fit the block's hole, the rest empty.",
     gi_fit_count, tf_fit_count)


# 17 rectangles drop into floor slots
def gi_slots(rng):
    H, W = _size(rng, 11, 20); g = blank(H, W); fh = rng.randint(3, 6); k = rng.randint(2, 4); A, *cs = colours(rng, k + 1)
    dimsets = [(d, w) for d in range(1, fh) for w in range(1, 5)]; rng.shuffle(dimsets); slots = dimsets[:k]
    if sum(w for _, w in slots) + k + 1 > W: return None
    for r in range(H - fh, H):
        for c in range(W): g[r][c] = A
    c = rng.randint(1, W - sum(w for _, w in slots) - k)
    for d, w in slots:
        if c + w > W - 1: return None
        for r in range(H - fh, H - fh + d):
            for x in range(c, c + w): g[r][x] = 0
        c += w + rng.randint(1, 2)
        if c > W - 1: return None
    _mask(g, H - fh - 1, 0, H - 1, W - 1, -1)
    for (d, w), col in zip(slots, cs):
        if _put(rng, g, _rect_shape(d, w), col) is None: return None
    return _unmask(g)
def tf_slots(g):
    obs, floor = _biggest(g); out = copy(g)
    for slot in _holes(g, floor):
        sh = _norm(slot); fits = [o for o in obs if o is not floor and _norm(o) == sh]
        if len(fits) != 1: return None
        col = _col(g, fits[0])
        for r, c in fits[0]: out[r][c] = 0
        for r, c in slot: out[r][c] = col
    return out
rule("rectangles_drop_into_floor_slots", "The floor along the bottom has rectangular slots cut into its top; each loose rectangle drops into the one slot of exactly its size.", gi_slots, tf_slots)


# 18 jagged strips reassembled into a rectangle
def gi_jagged(rng):
    H, W = _size(rng, 11, 20); g = blank(H, W); w = rng.randint(3, 8); k = rng.randint(2, 4); gap = rng.randint(2, 3)
    bases = [i * gap for i in range(k + 1)]; b = [[0] * w] + [[base + rng.randint(0, 1) for _ in range(w)] for base in bases[1:-1]] + [[bases[-1]] * w]
    strips = [frozenset((r, c) for c in range(w) for r in range(b[i][c], b[i + 1][c])) for i in range(k)]
    tops = [_norm({(b[i][c], c) for c in range(w)}) for i in range(k)]
    if len(set(tops)) != k: return None
    cs = colours(rng, k); order = list(range(k)); rng.shuffle(order)
    for i in order:
        if _put(rng, g, _norm(strips[i]), cs[i]) is None: return None
    return g
def _profile(o, top=True):
    r0, c0, r1, c1 = bbox(o)
    prof = {}
    for r, c in o:
        prof[c] = (min if top else max)(prof.get(c, r), r)
    return [prof[c] for c in range(c0, c1 + 1)]
def tf_jagged(g):
    obs = _blobs(g); w = len(_profile(obs[0]))
    if any(len(_profile(o)) != w for o in obs): return None
    flat = [o for o in obs if len(set(_profile(o))) == 1]
    if len(flat) != 1: return None
    placed = {}; cur = flat[0]; off = 0; used = [cur]
    r0, c0 = bbox(cur)[:2]
    for r, c in cur: placed[(r - r0, c - c0)] = g[r][c]
    while len(used) < len(obs):
        bot = {}
        for (r, c) in placed: bot[c] = max(bot.get(c, r), r)
        need = [bot[c] + 1 for c in range(w)]
        cand = []
        for o in obs:
            if any(o is u for u in used): continue
            r0, c0 = bbox(o)[:2]; top = _profile(o); d = need[0] - top[0]
            if [t + d for t in top] == need: cand.append((o, d))
        if len(cand) != 1: return None
        o, d = cand[0]; r0, c0 = bbox(o)[:2]
        for r, c in o: placed[(r + d, c - c0)] = g[r][c]
        used.append(o)
    h = max(r for r, _ in placed) + 1; out = blank(h, w)
    for (r, c), v in placed.items(): out[r][c] = v
    return out if h * w == len(placed) else None
rule("jagged_strips_reassembled", "The equally wide strips have jagged top and bottom edges that interlock; starting from the strip with a flat top, they are stacked so every edge meshes, and the assembled rectangle is output.",
     gi_jagged, tf_jagged)


# 19 hole rim takes the colour of the piece that fits it
def tf_rim(g):
    obs, blk = _biggest(g); out = copy(g); A = _col(g, blk); H, W = dims(g)
    for hole in _holes(g, blk):
        fits = _fit_pieces(g, obs, blk, hole)
        if len(fits) != 1: return None
        col = _col(g, fits[0])
        for r, c in hole:
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                if 0 <= r + dr < H and 0 <= c + dc < W and g[r + dr][c + dc] == A: out[r + dr][c + dc] = col
    return out
rule("hole_rim_takes_fitting_piece_colour", "The pieces stay put, but around each hole the block cells touching that hole are recoloured in the colour of the loose piece whose shape fits it.",
     lambda rng: _multi_hole_scene(rng, 1, 3, margin=2), tf_rim)


# 20 piece fits only after mirroring
def _chiral(s):
    return _flip(s) not in _rots(s)
def gi_flipped(rng):
    h, w = _size(rng, 11, 20); g = blank(h, w)
    hole = _distinct(rng, 1, 4, 7, ok=_chiral)
    if not hole: return None
    hole = hole[0]; k = rng.randint(1, 3); A, *cs = colours(rng, k + 2)
    if _block_with_holes(rng, g, [hole], A) is None: return None
    others = _distinct(rng, k, 3, 6, avoid=[hole], under=_syms)
    if not others: return None
    pieces = [rng.choice(_rots(_flip(hole)))] + others; rng.shuffle(pieces)
    for s, c in zip(pieces, cs):
        if _put(rng, g, s, c) is None: return None
    return g
def tf_flipped(g):
    obs, blk = _biggest(g); holes = _holes(g, blk)
    if len(holes) != 1 or _fit_pieces(g, obs, blk, holes[0], under=lambda s: set(_rots(s))): return None
    fits = _fit_pieces(g, obs, blk, holes[0], under=_syms)
    if len(fits) != 1: return None
    out = copy(g); col = _col(g, fits[0])
    for r, c in fits[0]: out[r][c] = 0
    for r, c in holes[0]: out[r][c] = col
    return out
rule("flipped_piece_into_hole", "One loose piece is the mirror image of the block's hole; it is flipped over and placed in the hole, its old place emptied.", gi_flipped, tf_flipped)


# 21 pieces recoloured by whether they fit any hole
def tf_fit_class(g):
    obs, blk = _biggest(g); holes = {_norm(h) for h in _holes(g, blk)}; out = copy(g); seen = set()
    for o in obs:
        if o is blk: continue
        v = 1 if _norm(o) in holes else 2; seen.add(v)
        for r, c in o: out[r][c] = v
    return out if seen == {1, 2} else None
rule("pieces_coloured_by_whether_they_fit", "Loose pieces whose shape exactly fits one of the block's holes become colour 1; pieces that fit no hole become colour 2; the block is unchanged.",
     lambda rng: _multi_hole_scene(rng, 1, 3, extra=rng.randint(1, 2)), tf_fit_class)


# 22 biggest rectangle that fits inside the frame moves in
def gi_frame_fit(rng):
    H, W = _size(rng, 11, 20); g = blank(H, W); ih, iw = rng.randint(2, 5), rng.randint(2, 5); k = rng.randint(2, 4)
    F, *cs = colours(rng, k + 1); p = _put(rng, g, _frame_shape(ih + 2, iw + 2), F)
    if p is None: return None
    _mask(g, p[0], p[1], p[0] + ih + 1, p[1] + iw + 1, -1)
    rects = []
    for _ in range(60):
        h, w = rng.randint(1, 6), rng.randint(1, 6)
        if (h, w) not in rects: rects.append((h, w))
        if len(rects) == k: break
    fits = [(h * w, h, w) for h, w in rects if h <= ih and w <= iw]
    if not fits or len(fits) == k or sorted(fits)[-1][0] in [a for a, _, _ in sorted(fits)[:-1]]: return None
    for (h, w), c in zip(rects, cs):
        if _put(rng, g, _rect_shape(h, w), c) is None: return None
    return _unmask(g)
def tf_frame_fit(g):
    obs, fr = _biggest(g); r0, c0, r1, c1 = bbox(fr); ih, iw = r1 - r0 - 1, c1 - c0 - 1
    fits = [o for o in obs if o is not fr and _hw(_norm(o))[0] <= ih and _hw(_norm(o))[1] <= iw]
    if not fits: return None
    big = max(fits, key=len)
    if sum(1 for o in fits if len(o) == len(big)) != 1: return None
    out = copy(g); pr0, pc0 = bbox(big)[:2]
    for r, c in big: out[r][c] = 0
    for r, c in big: out[r0 + 1 + r - pr0][c0 + 1 + c - pc0] = g[r][c]
    return out
rule("biggest_rectangle_fitting_frame_moves_in", "Of the loose rectangles small enough to fit inside the hollow frame, the one with the most cells moves into the frame's top-left inner corner; the others stay.",
     gi_frame_fit, tf_frame_fit)


# 23 pieces fall; narrow ones pass through the gap in the container's lid
def gi_gap_fall(rng):
    H, W = _size(rng, 12, 22); g = blank(H, W); fh = rng.randint(4, 7); fw = rng.randint(7, min(W, 14)); L = rng.randint(2, fw - 4)
    F, *cs = colours(rng, rng.randint(3, 5)); c0 = rng.randint(0, W - fw); gc = rng.randint(c0 + 1, c0 + fw - 1 - L)
    for r, c in _frame_shape(fh, fw): g[H - fh + r][c0 + c] = F
    for c in range(gc, gc + L): g[H - fh][c] = 0
    r = H - fh - 2; kinds = set()
    for i, col in enumerate(cs):
        narrow = rng.random() < 0.5 if i < len(cs) - 2 else (i == len(cs) - 1 and "n" not in kinds) or (i == len(cs) - 2 and "w" in kinds and "n" not in kinds) or rng.random() < 0.5
        kinds.add("n" if narrow else "w")
        if narrow:
            w = rng.randint(1, L); x = rng.randint(gc, gc + L - w)
        else:
            w = rng.randint(L + 1, L + 3); x = rng.randint(max(0, gc + L - w), min(gc, W - w))
        h = rng.randint(1, 2); r -= h
        if r < 0: break
        for rr in range(r, r + h):
            for cc in range(x, x + w): g[rr][cc] = col
        r -= rng.randint(1, 2)
    return g if len(_blobs(g)) >= 3 and kinds == {"n", "w"} else None
def tf_gap_fall(g):
    obs, fr = _biggest(g); H, W = dims(g); out = copy(g)
    pieces = sorted([o for o in obs if o is not fr], key=lambda o: -bbox(o)[2])
    for o in pieces:
        for r, c in o: out[r][c] = 0
    for o in pieces:
        d = 0; cells_ = set(o)
        while all(r + d + 1 < H and out[r + d + 1][c] == 0 for r, c in o): d += 1
        for r, c in o: out[r + d][c] = g[r][c]
    return out
rule("pieces_fall_narrow_ones_through_gap", "Every piece above the lidded container falls straight down as a rigid block: pieces narrow enough to pass through the gap in the lid land inside, wider ones come to rest on the lid or on pieces beneath them.",
     gi_gap_fall, tf_gap_fall)


# 24 the block slides so its hole swallows the piece
def gi_swallow(rng):
    H, W = _size(rng, 10, 20); g = blank(H, W); hole = _shape(rng, 3, 6); A, B = colours(rng, 2)
    p = _block_with_holes(rng, g, [hole], A)
    if p is None: return None
    q = _put(rng, g, hole, B)
    if q is None: return None
    r0, c0, bh, bw, (ha,) = p; dr, dc = q[0] - ha[0], q[1] - ha[1]
    return g if 0 <= r0 + dr and r0 + dr + bh <= H and 0 <= c0 + dc and c0 + dc + bw <= W else None
def tf_swallow(g):
    obs, blk = _biggest(g); holes = _holes(g, blk)
    if len(holes) != 1 or len(obs) != 2: return None
    piece = [o for o in obs if o is not blk][0]
    if _norm(piece) != _norm(holes[0]): return None
    dr = bbox(piece)[0] - bbox(holes[0])[0]; dc = bbox(piece)[1] - bbox(holes[0])[1]; H, W = dims(g)
    out = blank(H, W); A = _col(g, blk)
    for r, c in blk:
        if not (0 <= r + dr < H and 0 <= c + dc < W): return None
        out[r + dr][c + dc] = A
    for r, c in piece: out[r][c] = g[r][c]
    return out
rule("block_slides_to_swallow_piece", "The loose piece stays where it is; the big block slides as a whole so that its hole lands exactly over the piece, swallowing it.", gi_swallow, tf_swallow)


# 25 embedded pieces are ejected to the right of the block
def gi_eject(rng):
    H, W = _size(rng, 10, 20); g = blank(H, W); k = rng.randint(1, 3); A, *cs = colours(rng, k + 1)
    shapes = [_shape(rng, 2, 5) for _ in range(k)]
    p = _block_with_holes(rng, g, shapes, A, layout="v")
    if p is None: return None
    r0, c0, bh, bw, pos = p
    if c0 + bw + 1 + max(_hw(s)[1] for s in shapes) > W: return None
    for s, c, (a, b) in zip(shapes, cs, pos): _stamp(g, s, a, b, c)
    return g
def tf_eject(g):
    obs, blk = _biggest(g); r0, c0, r1, c1 = bbox(blk); A = g[r0][c0]; out = copy(g); W = len(g[0])
    inner = _inner(g, blk)
    if not inner: return None
    for o in inner:
        pc0 = bbox(o)[1]
        for r, c in o:
            nc = c1 + 2 + (c - pc0)
            if nc >= W: return None
            out[r][c] = A; out[r][nc] = g[r][c]
    return out
rule("embedded_pieces_ejected_right", "Each differently coloured piece embedded in the big block pops out to the right: it reappears one empty column beyond the block's right edge on the same rows, and the block closes up in its own colour.",
     gi_eject, tf_eject)


# 26 grey pieces take the colour of the block whose hole they fit
def gi_block_colour(rng):
    H, W = _size(rng, 12, 22); g = blank(H, W); k = rng.randint(2, 3); cs = colours(rng, k, exclude=(0, 5))
    holes = _distinct(rng, k, 3, 6)
    if not holes: return None
    for s, c in zip(holes, cs):
        if _block_with_holes(rng, g, [s], c, slack=1) is None: return None
    rng.shuffle(holes)
    for s in holes:
        if _put(rng, g, s, 5) is None: return None
    return g
def tf_block_colour(g):
    obs = _blobs(g); out = copy(g); greys = [o for o in obs if _col(g, o) == 5]; blocks = [o for o in obs if _col(g, o) != 5]
    if not greys: return None
    for o in greys:
        owners = [b for b in blocks for h in _holes(g, b) if _norm(h) == _norm(o)]
        if len(owners) != 1: return None
        for r, c in o: out[r][c] = _col(g, owners[0])
    return out
rule("pieces_take_colour_of_block_they_fit", "Each grey piece fits the hole of exactly one coloured block; the piece is recoloured in that block's colour and stays where it is.", gi_block_colour, tf_block_colour)


# 27 bars stacked into the column container, widest at the bottom
def gi_stack_width(rng):
    H, W = _size(rng, 12, 20); g = blank(H, W); iw = rng.randint(3, 6); k = rng.randint(2, min(4, iw))
    ws = rng.sample(range(1, iw + 1), k); ih = k + rng.randint(1, 3); F, *cs = colours(rng, k + 1)
    p = _put(rng, g, _u_shape(ih, iw), F)
    if p is None: return None
    _mask(g, p[0] - 1, p[1], p[0] + ih, p[1] + iw + 1, -1)
    for w, c in zip(ws, cs):
        if _put(rng, g, _rect_shape(1, w), c) is None: return None
    return _unmask(g)
def tf_stack_width(g):
    return _stack(g, lambda o: -len(o))
rule("pieces_stack_in_column_widest_at_bottom", "The bars are stacked inside the open-topped column against its left wall, the widest on the floor and each narrower bar on top of the one before.", gi_stack_width, tf_stack_width)


# 28 pieces embedded in the block move to the holes they fit
def gi_embedded_relocate(rng):
    H, W = _size(rng, 12, 22); g = blank(H, W); k = rng.randint(1, 3); A, *cs = colours(rng, k + 1)
    shapes = _distinct(rng, k, 3, 5)
    if not shapes: return None
    slots = shapes + shapes; p = _block_with_holes(rng, g, slots, A, slack=2)
    if p is None: return None
    pos = p[4]
    for s, c, (a, b) in zip(shapes, cs, pos[k:]): _stamp(g, s, a, b, c)
    return g
def tf_embedded_relocate(g):
    obs, blk = _biggest(g); A = g[bbox(blk)[0]][bbox(blk)[1]]; out = copy(g); holes = _holes(g, blk); inner = _inner(g, blk)
    if not inner or len(holes) != len(inner): return None
    for o in inner:
        m = [h for h in holes if _norm(h) == _norm(o)]
        if len(m) != 1: return None
        col = _col(g, o)
        for r, c in o: out[r][c] = A
        for r, c in m[0]: out[r][c] = col
    return out
rule("embedded_pieces_relocate_to_fitting_holes", "Inside the big block, each embedded coloured piece moves to the empty hole of exactly its shape; the block fills in behind it.", gi_embedded_relocate, tf_embedded_relocate)


# 29 cut along the grey line, parts laid side by side
def gi_cut_one(rng):
    H, W = _size(rng, 8, 18); g = blank(H, W); c = rng.choice([x for x in COLOURS if x != 5]); h, w = rng.randint(3, 8), rng.randint(3, 8)
    p = _put(rng, g, _rect_shape(h, w), c)
    if p is None: return None
    if rng.random() < 0.5:
        r = p[0] + rng.randint(1, h - 2)
        for x in range(p[1], p[1] + w): g[r][x] = 5
    else:
        x = p[1] + rng.randint(1, w - 2)
        for r in range(p[0], p[0] + h): g[r][x] = 5
    for _ in range(rng.randint(0, 3)):
        _put(rng, g, _rect_shape(1, 1), rng.choice([x for x in COLOURS if x not in (5, c)]))
    return g
def tf_cut_side(g):
    cuts = _cuts(g, min_size=2)
    if not cuts or len(cuts) != 1: return None
    o, grey, horiz = cuts[0]; gr, gc = grey[0]
    near = [(r, c) for r, c in o if (r < gr if horiz else c < gc)]; far = [(r, c) for r, c in o if (r > gr if horiz else c > gc)]
    a, b = crop(g, *bbox(near)), crop(g, *bbox(far)); h = max(len(a), len(b)); w = len(a[0]) + 1 + len(b[0]); out = blank(h, w)
    paste(out, a, 0, 0); paste(out, b, 0, len(a[0]) + 1)
    return out
rule("cut_along_grey_line_parts_side_by_side", "The block is cut along its grey line and the two parts are output side by side, the top or left part first, one empty column between them and top-aligned.",
     gi_cut_one, tf_cut_side)


# 30 single-cell pegs fill single-cell holes in reading order
def gi_pegs(rng):
    H, W = _size(rng, 9, 18); g = blank(H, W); k = rng.randint(2, 6); A = rng.choice(COLOURS)
    one = _rect_shape(1, 1)
    if _block_with_holes(rng, g, [one] * k, A, slack=4) is None: return None
    cs = [rng.choice([c for c in COLOURS if c != A]) for _ in range(k)]
    if len(set(cs)) < 2: return None
    for c in cs:
        if _put(rng, g, one, c) is None: return None
    return g
def tf_pegs(g):
    obs, blk = _biggest(g); holes = sorted(h[0] for h in _holes(g, blk)); pegs = sorted(o[0] for o in obs if o is not blk)
    if len(holes) != len(pegs) or not holes: return None
    out = copy(g)
    for (hr, hc), (pr, pc) in zip(holes, pegs):
        out[hr][hc] = g[pr][pc]; out[pr][pc] = 0
    return out
rule("pegs_fill_holes_in_order", "The block has single-cell holes and there are as many loose single cells; taking both in reading order, the first peg fills the first hole, the second the second, and so on.",
     gi_pegs, tf_pegs)


# 31 crop the one hole that no piece fits
def tf_orphan_hole(g):
    obs, blk = _biggest(g); orphans = [h for h in _holes(g, blk) if not _fit_pieces(g, obs, blk, h)]
    if len(orphans) != 1 or _is_rect(_norm(orphans[0])): return None
    r0, c0, r1, c1 = bbox(orphans[0]); out = blank(r1 - r0 + 1, c1 - c0 + 1)
    for r, c in orphans[0]: out[r - r0][c - c0] = 5
    return out
rule("crop_hole_with_no_fitting_piece", "Every hole in the block has a matching loose piece except one; output that unmatched hole's shape as a solid grey piece, cropped to its bounding box.",
     lambda rng: _multi_hole_scene(rng, 2, 4, missing=1), tf_orphan_hole)


# 32 vertical strips pack the frame left to right
def gi_strips(rng):
    H, W = _size(rng, 12, 22); g = blank(H, W); ih = rng.randint(2, 6); k = rng.randint(2, 4); ws = [rng.randint(1, 3) for _ in range(k)]
    iw = sum(ws); F, *cs = colours(rng, k + 1); p = _put(rng, g, _frame_shape(ih + 2, iw + 2), F)
    if p is None: return None
    _mask(g, p[0], p[1], p[0] + ih + 1, p[1] + iw + 1, -1)
    for w, c in zip(ws, cs):
        if _put(rng, g, _rect_shape(ih, w), c) is None: return None
    return _unmask(g)
def tf_strips(g):
    obs, fr = _biggest(g); r0, c0, r1, c1 = bbox(fr); out = copy(g); x = c0 + 1
    for o in sorted([o for o in obs if o is not fr], key=lambda o: bbox(o)[:2]):
        pr0, pc0, pr1, pc1 = bbox(o)
        for r, c in o: out[r][c] = 0
        if x + pc1 - pc0 >= c1: return None
        for r, c in o: out[r0 + 1 + r - pr0][x + c - pc0] = g[r][c]
        x += pc1 - pc0 + 1
    return out if x == c1 else None
rule("strips_pack_frame_left_to_right", "The loose vertical strips are as tall as the frame's inside; in reading order they are packed into the frame from its left wall rightward until they fill it exactly.",
     gi_strips, tf_strips)


# 33 small piece doubled fills the hole
def gi_double(rng):
    H, W = _size(rng, 12, 22); g = blank(H, W); small = _shape(rng, 2, 4); hole = _scale2(small); k = rng.randint(1, 3)
    A, *cs = colours(rng, k + 2)
    if _block_with_holes(rng, g, [hole], A) is None: return None
    others = _distinct(rng, k, 2, 5, avoid=[small])
    if not others: return None
    pieces = [small] + others; rng.shuffle(pieces)
    for s, c in zip(pieces, cs):
        if _put(rng, g, s, c) is None: return None
    return g
def tf_double(g):
    obs, blk = _biggest(g); holes = _holes(g, blk)
    if len(holes) != 1: return None
    hn = _norm(holes[0]); fits = [o for o in obs if o is not blk and _scale2(_norm(o)) == hn]
    if len(fits) != 1: return None
    out = copy(g); col = _col(g, fits[0])
    for r, c in fits[0]: out[r][c] = 0
    for r, c in holes[0]: out[r][c] = col
    return out
rule("small_piece_doubles_into_hole", "The block's hole is a double-size copy of one small loose piece; that piece is enlarged to twice its size and placed in the hole, its old place emptied.", gi_double, tf_double)


# 34 holes lined up as solid pieces
def gi_holes_row(rng):
    H, W = _size(rng, 12, 22); g = blank(H, W); k = rng.randint(2, 4); A = rng.choice(COLOURS)
    holes = _distinct(rng, k, 3, 7, ok=_nonrect)
    if not holes: return None
    return g if _block_with_holes(rng, g, holes, A) else None
def tf_holes_row(g):
    obs, blk = _biggest(g); holes = sorted(_holes(g, blk), key=lambda h: bbox(h)[:2]); A = _col(g, blk)
    if len(holes) < 2: return None
    hs = [_norm(h) for h in holes]; H = max(_hw(s)[0] for s in hs); W = sum(_hw(s)[1] for s in hs) + len(hs) - 1; out = blank(H, W); x = 0
    for s in hs:
        for r, c in s: out[r][x + c] = A
        x += _hw(s)[1] + 1
    return out
rule("holes_lined_up_as_solid_pieces", "Each hole in the block is turned into a solid piece of the block's colour; the pieces are output side by side in the holes' reading order, top-aligned, one empty column apart.",
     gi_holes_row, tf_holes_row)


# 35 complementary pairs share a colour
def gi_pair_colour(rng):
    H, W = _size(rng, 12, 22); g = blank(H, W); n = rng.randint(2, 3); shapes, cs = [], []
    for _ in range(n):
        sp = _split_rect(rng, rng.randint(2, 4), rng.randint(2, 5))
        if sp is None: return None
        shapes += list(sp)
    cs = colours(rng, 2 * n); order = list(range(2 * n)); rng.shuffle(order)
    for i in order:
        if _put(rng, g, shapes[i], cs[i]) is None: return None
    pr = _rect_pairs(_blobs(g)); ids = [id(x) for P, Q, _, _ in pr for x in (P, Q)]
    return g if len(pr) == n and len(set(ids)) == 2 * n else None
def tf_pair_colour(g):
    obs = _blobs(g); pr = _rect_pairs(obs); ids = [id(x) for P, Q, _, _ in pr for x in (P, Q)]
    if len(set(ids)) != len(ids) or 2 * len(pr) != len(obs): return None
    out = copy(g)
    for P, Q, _, _ in pr:
        first = min((P, Q), key=lambda o: bbox(o)[:2]); col = _col(g, first)
        for o in (P, Q):
            for r, c in o: out[r][c] = col
    return out
rule("rectangle_complement_pairs_share_colour", "The pieces pair up so that each pair would fit together into a solid rectangle; both pieces of a pair are recoloured in the colour of whichever comes first in reading order.",
     gi_pair_colour, tf_pair_colour)


# 36 piece fills the hole, block border takes its colour
def tf_fill_border(g):
    obs, blk = _biggest(g); holes = _holes(g, blk)
    if len(holes) != 1: return None
    fits = _fit_pieces(g, obs, blk, holes[0])
    if len(fits) != 1: return None
    out = copy(g); col = _col(g, fits[0]); r0, c0, r1, c1 = bbox(blk)
    for r, c in fits[0]: out[r][c] = 0
    for r, c in holes[0]: out[r][c] = col
    for r, c in blk:
        if r in (r0, r1) or c in (c0, c1): out[r][c] = col
    return out
rule("piece_fills_hole_block_border_takes_its_colour", "The loose piece that fits the block's hole moves into it, and the block's outer border is then repainted in that piece's colour.",
     lambda rng: _multi_hole_scene(rng, 1, 1, extra=rng.randint(1, 3)), tf_fill_border)


# 37 rectangles move into the frames whose insides they exactly fill
def gi_frames_fill(rng):
    H, W = _size(rng, 12, 22); g = blank(H, W); k = rng.randint(2, 3); F = rng.choice(COLOURS); cs = colours(rng, k, exclude=(0, F))
    dimsets = []
    for _ in range(50):
        h, w = rng.randint(1, 4), rng.randint(1, 4)
        if (h, w) not in dimsets and (w, h) not in dimsets: dimsets.append((h, w))
        if len(dimsets) == k: break
    if len(dimsets) < k: return None
    for h, w in dimsets:
        p = _put(rng, g, _frame_shape(h + 2, w + 2), F)
        if p is None: return None
        _mask(g, p[0], p[1], p[0] + h + 1, p[1] + w + 1, -1)
    for (h, w), c in zip(dimsets, cs):
        if _put(rng, g, _rect_shape(h, w), c) is None: return None
    return _unmask(g)
def tf_frames_fill(g):
    obs = _blobs(g); frames = [o for o in obs if _holes(g, o) and len(_holes(g, o)) == 1]; pieces = [o for o in obs if o not in frames]
    out = copy(g)
    if not frames or not pieces: return None
    for fr in frames:
        hole = _holes(g, fr)[0]; m = [p for p in pieces if _norm(p) == _norm(hole)]
        if len(m) != 1: return None
        col = _col(g, m[0])
        for r, c in m[0]: out[r][c] = 0
        for r, c in hole: out[r][c] = col
    return out
rule("rectangles_into_matching_frames", "Each loose rectangle exactly fills the inside of one hollow frame; every rectangle moves into its frame, leaving its old place empty.", gi_frames_fill, tf_frames_fill)


# 38 pieces move onto their grey silhouettes
def gi_silhouette(rng):
    H, W = _size(rng, 11, 22); g = blank(H, W); k = rng.randint(1, 4); cs = colours(rng, k, exclude=(0, 5))
    shapes = _distinct(rng, k, 3, 6)
    if not shapes: return None
    items = [(s, c) for s, c in zip(shapes, cs)] + [(s, 5) for s in shapes]; rng.shuffle(items)
    for s, c in items:
        if _put(rng, g, s, c) is None: return None
    return g
def tf_silhouette(g):
    obs = _blobs(g); out = copy(g); greys = [o for o in obs if _col(g, o) == 5]; pieces = [o for o in obs if _col(g, o) != 5]
    if not greys or len(greys) != len(pieces): return None
    for o in pieces:
        m = [s for s in greys if _norm(s) == _norm(o)]
        if len(m) != 1: return None
        col = _col(g, o)
        for r, c in o: out[r][c] = 0
        for r, c in m[0]: out[r][c] = col
    return out
rule("pieces_move_onto_grey_silhouettes", "Every coloured piece has a grey silhouette of its exact shape somewhere else; each piece moves onto its silhouette, painting it in the piece's colour, and its old place is emptied.",
     gi_silhouette, tf_silhouette)


# 39 crop the piece turned so it fits the hole
def tf_rot_crop(g):
    obs, blk = _biggest(g); holes = _holes(g, blk)
    if len(holes) != 1: return None
    fits = _fit_pieces(g, obs, blk, holes[0], under=lambda s: set(_rots(s)))
    if len(fits) != 1 or _norm(fits[0]) == _norm(holes[0]): return None
    r0, c0, r1, c1 = bbox(holes[0]); out = blank(r1 - r0 + 1, c1 - c0 + 1)
    for r, c in holes[0]: out[r - r0][c - c0] = _col(g, fits[0])
    return out
rule("crop_piece_rotated_to_fit_hole", "One loose piece fits the block's hole after turning; output that piece alone, rotated into the orientation that fits the hole.", gi_rotated, tf_rot_crop)


# 40 pieces fitting each hole, as bars
def gi_per_hole(rng):
    H, W = _size(rng, 12, 22); g = blank(H, W); k = rng.randint(2, 3); A, *cs = colours(rng, k + 1)
    holes = _distinct(rng, k, 3, 5)
    if not holes: return None
    if _block_with_holes(rng, g, holes, A) is None: return None
    ns = [rng.randint(0, 3) for _ in range(k)]
    if sum(ns) < 2 or len(set(ns)) == 1: return None
    pieces = [(s, c) for s, c, n in zip(holes, cs, ns) for _ in range(n)]; rng.shuffle(pieces)
    for s, c in pieces:
        if _put(rng, g, s, c) is None: return None
    return g
def tf_per_hole(g):
    obs, blk = _biggest(g); holes = sorted(_holes(g, blk), key=lambda h: bbox(h)[:2]); total = len(obs) - 1
    if len(holes) < 2 or total < 1: return None
    out = []
    for h in holes:
        fits = _fit_pieces(g, obs, blk, h)
        out.append([_col(g, fits[0])] * len(fits) + [0] * (total - len(fits)) if fits else [0] * total)
    return out
rule("fitting_pieces_per_hole_bars", "Output one row per hole in reading order, as wide as the number of loose pieces: a bar as long as the number of pieces fitting that hole, in those pieces' colour.",
     gi_per_hole, tf_per_hole)
