# b020_conditionals.py -- cross-object conditionals: a property of one thing in the scene (a key cell, a marker,
# a bar, a count, the largest object, the grid's own shape) decides which transform the OTHER things receive.
# Every rule has two or more branches and the generators force both branches to occur across a pool.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

NO5 = [c for c in COLOURS if c != 5]


# ---------------------------------------------------------------- local helpers
def _size(rng, lo=7, hi=18, big=0.35):
    """Grid dims; about a third of the time both sides land in the 21-30 band."""
    if rng.random() < big:
        return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _col(g, o):
    return g[o[0][0]][o[0][1]]


def _hw(sh):
    return max(r for r, _ in sh) + 1, max(c for _, c in sh) + 1


def _norm(o):
    r0 = min(r for r, _ in o); c0 = min(c for _, c in o)
    return frozenset((r - r0, c - c0) for r, c in o)


def _shape(rng, lo=3, hi=8):
    return random_shape(rng, rng.randint(lo, hi))


def _shape_pred(rng, pred, lo=3, hi=8, tries=80):
    for _ in range(tries):
        sh = _shape(rng, lo, hi)
        if pred(sh):
            return sh
    return None


def _rect(h, w):
    return [(r, c) for r in range(h) for c in range(w)]


def _ring(h, w):
    return [(r, c) for r in range(h) for c in range(w) if r in (0, h - 1) or c in (0, w - 1)]


def _is_ring(o):
    r0, c0, r1, c1 = bbox(o)
    return r1 - r0 >= 2 and c1 - c0 >= 2 and len(o) == 2 * (r1 - r0 + c1 - c0)


def _free(g, r0, c0, h, w, margin=1):
    H, W = dims(g)
    if r0 < 0 or c0 < 0 or r0 + h > H or c0 + w > W:
        return False
    return all(g[r][c] == 0 for r in range(r0 - margin, r0 + h + margin) for c in range(c0 - margin, c0 + w + margin)
               if 0 <= r < H and 0 <= c < W)


def _place(rng, g, sh, col, margin=1, tries=100, rows=None, cols_=None):
    """Stamp sh (list of (r,c)) in colour col at a random free spot with `margin` empty cells around; returns (r0,c0)."""
    H, W = dims(g); h, w = _hw(sh)
    rlo, rhi = rows or (0, H - h); clo, chi = cols_ or (0, W - w)
    rhi, chi = min(rhi, H - h), min(chi, W - w); rlo, clo = max(rlo, 0), max(clo, 0)
    if rlo > rhi or clo > chi:
        return None
    for _ in range(tries):
        r0, c0 = rng.randint(rlo, rhi), rng.randint(clo, chi)
        if _free(g, r0, c0, h, w, margin):
            for r, c in sh:
                g[r0 + r][c0 + c] = col
            return r0, c0
    return None


def _place_multi(rng, g, cells_cols, margin=1, tries=100):
    """Stamp a multi-colour piece given as [(r,c,col)] at a random free spot."""
    H, W = dims(g); h = max(r for r, _, _ in cells_cols) + 1; w = max(c for _, c, _ in cells_cols) + 1
    for _ in range(tries):
        if h > H or w > W:
            return None
        r0, c0 = rng.randint(0, H - h), rng.randint(0, W - w)
        if _free(g, r0, c0, h, w, margin):
            for r, c, col in cells_cols:
                g[r0 + r][c0 + c] = col
            return r0, c0
    return None


def _place_touching(rng, g, sh, col, target, tries=200):
    """Stamp sh so that it is 8-adjacent to some cell of `target` and to nothing else coloured."""
    H, W = dims(g); h, w = _hw(sh)
    for _ in range(tries):
        r0, c0 = rng.randint(0, H - h), rng.randint(0, W - w)
        cs = [(r0 + r, c0 + c) for r, c in sh]
        if any(g[r][c] for r, c in cs):
            continue
        nb = {(r + dr, c + dc) for r, c in cs for dr in (-1, 0, 1) for dc in (-1, 0, 1)} - set(cs)
        nb = {(r, c) for r, c in nb if 0 <= r < H and 0 <= c < W}
        if nb & target and all(g[r][c] == 0 for r, c in nb - target):
            for r, c in cs:
                g[r][c] = col
            return r0, c0
    return None


def _blobs(g, bg=0):
    """4-connected components of non-background cells regardless of colour (glib.components splits by colour)."""
    H, W = dims(g); seen, out = set(), []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or g[r][c] == bg:
                continue
            comp, st = [], [(r, c)]; seen.add((r, c))
            while st:
                y, x = st.pop(); comp.append((y, x))
                for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen and g[ny][nx] != bg:
                        seen.add((ny, nx)); st.append((ny, nx))
            out.append(comp)
    return out


def _touches_border(o, H, W):
    return any(r in (0, H - 1) or c in (0, W - 1) for r, c in o)


def _scene(rng, k_lo=2, k_hi=5, n_lo=3, n_hi=8, lo=7, hi=18, cols=None, margin=1):
    H, W = _size(rng, lo, hi); g = blank(H, W); k = rng.randint(k_lo, k_hi); pal = cols or COLOURS
    for _ in range(k):
        _place(rng, g, _shape(rng, n_lo, n_hi), rng.choice(pal), margin=margin)
    return g if len(objects(g, 0)) >= max(1, k_lo) else None


def _slide_into(g, out, occ, obs, dr, dc):
    """Rigidly slide each object of obs in direction (dr,dc) until the wall or an occupied cell; writes into out/occ."""
    H, W = dims(g)
    key = {(0, -1): lambda o: min(c for _, c in o), (0, 1): lambda o: -max(c for _, c in o),
           (-1, 0): lambda o: min(r for r, _ in o), (1, 0): lambda o: -max(r for r, _ in o)}[(dr, dc)]
    for o in sorted(obs, key=key):
        cur = o
        while True:
            nxt = [(r + dr, c + dc) for r, c in cur]
            if all(0 <= r < H and 0 <= c < W and (r, c) not in occ for r, c in nxt):
                cur = nxt
            else:
                break
        for (r, c), (r0, c0) in zip(cur, o):
            out[r][c] = g[r0][c0]; occ.add((r, c))
    return out


def _cell_gravity(g, dr, dc):
    """Every coloured cell falls in direction (dr,dc) and stacks against that edge."""
    H, W = dims(g); out = blank(H, W)
    if dc == 0:
        for c in range(W):
            col = [g[r][c] for r in range(H) if g[r][c]]
            for i, v in enumerate(col):
                out[H - len(col) + i if dr > 0 else i][c] = v
    else:
        for r in range(H):
            row = [v for v in g[r] if v]
            for i, v in enumerate(row):
                out[r][W - len(row) + i if dc > 0 else i] = v
    return out


def _scale(sub, k):
    return [[v for v in row for _ in range(k)] for row in sub for _ in range(k)]


def _holes(g, o):
    r0, c0, r1, c1 = bbox(o); cs = set(o)
    sub = [[1 if (r, c) in cs else 0 for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
    h, w = dims(sub)
    return sum(1 for comp in components(sub, 0) if not any(r in (0, h - 1) or c in (0, w - 1) for r, c in comp))


def _grey_cell(g):
    gs = cells(g, lambda v: v == 5)
    return gs[0] if len(gs) == 1 else None


# ================================================================ rules

# 1 the largest object's colour is painted onto every object touching the border.
def gi_border_paint(rng):
    H, W = _size(rng, 9, 18); g = blank(H, W); cb = rng.choice(COLOURS); big = _shape(rng, 10, 16); hb, wb = _hw(big)
    if _place(rng, g, big, cb, rows=(1, H - hb - 1), cols_=(1, W - wb - 1)) is None: return None
    others = colours(rng, 3, exclude=(0, cb))
    for _ in range(rng.randint(1, 3)):
        sh = _shape(rng, 2, 5); h, w = _hw(sh); side = rng.randrange(4)
        rows = [(0, 0), (H - h, H - h), (0, H - h), (0, H - h)][side]; cols_ = [(0, W - w), (0, W - w), (0, 0), (W - w, W - w)][side]
        _place(rng, g, sh, rng.choice(others), rows=rows, cols_=cols_)
    for _ in range(rng.randint(0, 3)):
        sh = _shape(rng, 2, 5); h, w = _hw(sh); _place(rng, g, sh, rng.choice(others), rows=(1, H - h - 1), cols_=(1, W - w - 1))
    obs = objects(g, 0); sizes = sorted(len(o) for o in obs)
    return g if len(obs) >= 2 and sizes[-1] > sizes[-2] and any(_touches_border(o, H, W) for o in obs) else None
def tf_border_paint(g):
    H, W = dims(g); obs = objects(g, 0); big = max(obs, key=len); cb = _col(g, big); out = copy(g)
    for o in obs:
        if o is not big and _touches_border(o, H, W):
            for r, c in o: out[r][c] = cb
    return out
rule("largest_colour_paints_border_objects", "Every object touching the grid edge is repainted in the colour of the largest object; everything else stays.", gi_border_paint, tf_border_paint)


# 2 the number of grey dots sets how many quarter turns the main shape is rotated; output the shape alone.
def gi_turns(rng):
    H, W = _size(rng, 8, 18); g = blank(H, W); k = rng.randint(1, 3)
    sh = _shape(rng, 6, 12); h, w = _hw(sh)
    if h * w == len(sh) or _place(rng, g, sh, rng.choice(NO5)) is None: return None
    for _ in range(k):
        if _place(rng, g, [(0, 0)], 5) is None: return None
    return g
def tf_turns(g):
    obs = objects(g, 0); dots = [o for o in obs if len(o) == 1 and _col(g, o) == 5]; main = [o for o in obs if len(o) > 1]
    if len(main) != 1: return None
    out = crop(g, *bbox(main[0]))
    for _ in range(len(dots)): out = rot90(out)
    return out
rule("dot_count_sets_quarter_turns", "Output the single shape alone, rotated clockwise by one quarter turn for each grey dot in the grid.", gi_turns, tf_turns)


# 3 closed frames are filled; frames with a gap vanish.
def gi_frames_gap(rng):
    H, W = _size(rng, 9, 18); g = blank(H, W); n = rng.randint(2, 4)
    kinds = [True, False] + [rng.random() < 0.5 for _ in range(n - 2)]; rng.shuffle(kinds)
    for closed, col in zip(kinds, colours(rng, n)):
        h, w = rng.randint(3, 8), rng.randint(3, 8); pos = _place(rng, g, _ring(h, w), col)
        if pos is None: return None
        if not closed:
            r0, c0 = pos; side = rng.randrange(4)
            r, c = [(r0, c0 + rng.randint(1, w - 2)), (r0 + h - 1, c0 + rng.randint(1, w - 2)),
                    (r0 + rng.randint(1, h - 2), c0), (r0 + rng.randint(1, h - 2), c0 + w - 1)][side]
            g[r][c] = 0
    return g
def tf_frames_gap(g):
    out = copy(g)
    for o in components(g, lambda v: v != 0):
        r0, c0, r1, c1 = bbox(o); per = 2 * (r1 - r0 + c1 - c0)
        if r1 - r0 < 2 or c1 - c0 < 2: continue
        if len(o) == per: rect(out, r0 + 1, c0 + 1, r1 - 1, c1 - 1, _col(g, o))
        elif len(o) == per - 1:
            for r, c in o: out[r][c] = 0
    return out
rule("closed_frames_fill_gapped_frames_vanish", "A hollow rectangle with no gap is filled solid in its own colour; a rectangle with one gap in its wall is erased.", gi_frames_gap, tf_frames_gap)


# 4 the colour of the top-left cell decides whether objects slide left (1) or right (2).
def gi_corner_slide(rng):
    H, W = _size(rng, 8, 18); g = blank(H, W); g[0][0] = rng.choice((1, 2))
    for _ in range(rng.randint(2, 5)):
        sh = _shape(rng, 2, 7); h, w = _hw(sh); _place(rng, g, sh, rng.choice(COLOURS[2:]), rows=(2, H - h))
    return g if len(objects(g, 0)) >= 3 else None
def tf_corner_slide(g):
    H, W = dims(g); obs = [o for o in objects(g, 0) if o != [(0, 0)]]; out = blank(H, W); out[0][0] = g[0][0]
    return _slide_into(g, out, {(0, 0)}, obs, 0, -1 if g[0][0] == 1 else 1)
rule("corner_colour_sets_slide_direction", "If the top-left cell is colour 1 every object slides left until blocked, if colour 2 every object slides right; the corner cell stays.", gi_corner_slide, tf_corner_slide)


# 5 objects taller than the grey bar are flipped upside down; shorter ones are erased.
def gi_bar_flip(rng):
    H, W = _size(rng, 9, 18); g = blank(H, W); hb = rng.randint(2, 5)
    if _place(rng, g, [(r, 0) for r in range(hb)], 5) is None: return None
    preds = [lambda sh: _hw(sh)[0] > hb, lambda sh: _hw(sh)[0] <= hb] + [rng.choice([lambda sh: _hw(sh)[0] > hb, lambda sh: _hw(sh)[0] <= hb]) for _ in range(rng.randint(0, 3))]
    for p in preds:
        sh = _shape_pred(rng, lambda s: p(s) and _hw(s)[0] <= min(9, H - 1), 3, 9)
        if sh is None: return None
        _place(rng, g, sh, rng.choice(NO5))
    obs = [o for o in objects(g, 0) if _col(g, o) != 5]; hs = [bbox(o)[2] - bbox(o)[0] + 1 for o in obs]
    return g if any(h > hb for h in hs) and any(h <= hb for h in hs) else None
def tf_bar_flip(g):
    bar = [o for o in objects(g, 0) if _col(g, o) == 5]
    if len(bar) != 1: return None
    hb = bbox(bar[0])[2] - bbox(bar[0])[0] + 1; out = copy(g)
    for o in objects(g, 0):
        if _col(g, o) == 5: continue
        r0, c0, r1, c1 = bbox(o)
        for r, c in o: out[r][c] = 0
        if r1 - r0 + 1 > hb:
            for r, c in o: out[r0 + r1 - r][c] = g[r][c]
    return out
rule("taller_than_bar_flipped_shorter_erased", "Objects spanning more rows than the grey bar are flipped upside down in place; objects no taller than the bar are erased; the bar stays.", gi_bar_flip, tf_bar_flip)


# 6 more red (2) cells than blue (1): everything falls down; otherwise everything rises.
def gi_rb_gravity(rng):
    H, W = _size(rng, 6, 16); g = blank(H, W); a, b = rng.randint(2, 10), rng.randint(2, 10)
    if a == b: return None
    sprinkle(rng, g, a, 2); sprinkle(rng, g, b, 1)
    for c in colours(rng, rng.randint(0, 2), exclude=(0, 1, 2)): sprinkle(rng, g, rng.randint(1, 6), c)
    return g
def tf_rb_gravity(g):
    cnt = counts(g)
    return _cell_gravity(g, 1 if cnt.get(2, 0) > cnt.get(1, 0) else -1, 0)
rule("two_colour_majority_sets_gravity", "If there are more cells of colour 2 than of colour 1 every cell falls to the bottom, otherwise every cell rises to the top.", gi_rb_gravity, tf_rb_gravity)


# 7 the object nearest the grey marker is output alone at double scale.
def gi_nearest_scale(rng):
    H, W = _size(rng, 8, 18); g = blank(H, W)
    if _place(rng, g, [(0, 0)], 5) is None: return None
    for _ in range(rng.randint(2, 4)):
        sh = _shape(rng, 3, 7)
        if _hw(sh)[0] * _hw(sh)[1] > len(sh): _place(rng, g, sh, rng.choice(NO5))
    obs = [o for o in objects(g, 0) if _col(g, o) != 5]; m = _grey_cell(g)
    d = sorted(min(abs(r - m[0]) + abs(c - m[1]) for r, c in o) for o in obs)
    return g if len(d) >= 2 and d[0] < d[1] else None
def tf_nearest_scale(g):
    m = _grey_cell(g); obs = [o for o in objects(g, 0) if _col(g, o) != 5]
    o = min(obs, key=lambda o: min(abs(r - m[0]) + abs(c - m[1]) for r, c in o))
    return _scale(crop(g, *bbox(o)), 2)
rule("nearest_to_marker_doubled_alone", "Output only the object closest to the grey marker (by step distance), enlarged to twice its size.", gi_nearest_scale, tf_nearest_scale)


# 8 an object's hole count parity selects its recolouring.
def gi_hole_parity(rng):
    H, W = _size(rng, 9, 18); g = blank(H, W); n = rng.randint(2, 5); ks = [1, 2] + [rng.randint(1, 4) for _ in range(n - 2)]
    for k, col in zip(ks, colours(rng, n, exclude=(0, 1, 2))):
        h, w = rng.randint(3, 7), rng.randint(3, 7); inner = [(r, c) for r in range(1, h - 1, 2) for c in range(1, w - 1, 2)]
        if len(inner) < k: return None
        holes = set(rng.sample(inner, k)); sh = [(r, c) for r in range(h) for c in range(w) if (r, c) not in holes]
        if _place(rng, g, sh, col) is None: return None
    return g
def tf_hole_parity(g):
    out = copy(g)
    for o in objects(g, 0):
        k = _holes(g, o)
        if k:
            for r, c in o: out[r][c] = 1 if k % 2 else 2
    return out
rule("hole_parity_picks_recolour", "Each pierced block is recoloured 1 if it has an odd number of holes and 2 if an even number; the holes stay empty.", gi_hole_parity, tf_hole_parity)


# 9 only objects whose colour appears in the top key row survive; the rest take the key row's background colour.
def gi_key_row(rng):
    H, W = _size(rng, 8, 18); K = rng.choice(COLOURS); keys = colours(rng, rng.randint(1, 3), exclude=(0, K))
    non = colours(rng, rng.randint(1, 3), exclude=(0, K, *keys)); g = blank(H, W); g[0] = [K] * W
    for c, k in zip(rng.sample(range(W), len(keys)), keys): g[0][c] = k
    pool = [keys[0], non[0]] + [rng.choice(keys + non) for _ in range(rng.randint(1, 5))]
    for col in pool:
        sh = _shape(rng, 2, 7); h, w = _hw(sh); _place(rng, g, sh, col, rows=(2, H - h))
    present = {_col(g, o) for o in objects(g, 0) if o[0][0] >= 2}
    return g if present & set(keys) and present & set(non) else None
def tf_key_row(g):
    cnt = {}
    for v in g[0]: cnt[v] = cnt.get(v, 0) + 1
    K = max(cnt, key=cnt.get); keys = set(g[0]) - {K}; out = copy(g)
    for o in objects(g, 0):
        if o[0][0] >= 2 and _col(g, o) not in keys:
            for r, c in o: out[r][c] = K
    return out
rule("key_row_filters_field_objects", "The top row is a key: objects whose colour appears as a spot in the key keep their colour, every other object is repainted in the key row's background colour.", gi_key_row, tf_key_row)


# 10 a shape that occurs twice loses its second copy; a shape that occurs once is repainted grey.
def gi_twin(rng):
    H, W = _size(rng, 9, 18); g = blank(H, W); npair = rng.randint(1, 2); nuni = rng.randint(1, 3); shapes = []
    while len(shapes) < npair + nuni:
        sh = frozenset(_shape(rng, 3, 6))
        if sh not in shapes: shapes.append(sh)
    pieces = [(s, rng.choice(NO5)) for s in shapes[:npair] for _ in range(2)] + [(s, rng.choice(NO5)) for s in shapes[npair:]]
    rng.shuffle(pieces)
    for s, col in pieces:
        if _place(rng, g, sorted(s), col) is None: return None
    return g
def tf_twin(g):
    obs = objects(g, 0); cnt = {}
    for o in obs: cnt[_norm(o)] = cnt.get(_norm(o), 0) + 1
    out = copy(g); seen = set()
    for o in sorted(obs, key=lambda o: bbox(o)[:2]):
        n = _norm(o)
        if cnt[n] == 1:
            for r, c in o: out[r][c] = 5
        elif n in seen:
            for r, c in o: out[r][c] = 0
        else: seen.add(n)
    return out
rule("twin_shape_deleted_unique_greyed", "When two objects have the same shape the later one in reading order is erased; an object whose shape appears nowhere else is repainted grey.", gi_twin, tf_twin)


# 11 the one shape with the odd colour is stamped on every marker dot.
def gi_odd_stamp(rng):
    H, W = _size(rng, 10, 20); g = blank(H, W); a, b, m = colours(rng, 3); odd = _shape(rng, 3, 6); ho, wo = _hw(odd)
    if _place(rng, g, odd, b) is None: return None
    for _ in range(rng.randint(2, 4)): _place(rng, g, _shape(rng, 3, 6), a)
    taken, nm = set(), 0
    for _ in range(rng.randint(1, 4)):
        for _ in range(60):
            r0, c0 = rng.randint(0, H - ho), rng.randint(0, W - wo); foot = {(r0 + r, c0 + c) for r in range(ho) for c in range(wo)}
            if _free(g, r0, c0, ho, wo, 1) and not (foot & taken):
                g[r0][c0] = m; taken |= foot; nm += 1; break
    return g if nm and sum(1 for o in objects(g, 0) if _col(g, o) == a) >= 2 else None
def tf_odd_stamp(g):
    obs = objects(g, 0); shapes = [o for o in obs if len(o) > 1]; dots = [o for o in obs if len(o) == 1]; cnt = {}
    for o in shapes: cnt[_col(g, o)] = cnt.get(_col(g, o), 0) + 1
    odd = [o for o in shapes if cnt[_col(g, o)] == 1]
    if len(odd) != 1: return None
    sh = _norm(odd[0]); col = _col(g, odd[0]); out = copy(g); H, W = dims(g)
    for d in dots:
        r0, c0 = d[0]
        for r, c in sh:
            if 0 <= r0 + r < H and 0 <= c0 + c < W: out[r0 + r][c0 + c] = col
    return out
rule("odd_colour_shape_stamped_on_markers", "All shapes but one share a colour; a copy of the odd-coloured shape is stamped at every lone marker cell, with the marker at its top-left corner.", gi_odd_stamp, tf_odd_stamp)


# 12 wider than tall: row histogram; taller than wide: column histogram.
def gi_aspect_hist(rng):
    H, W = _size(rng, 5, 16)
    if H == W: return None
    g = blank(H, W); a, b = colours(rng, 2); sprinkle(rng, g, rng.randint(max(H, W), H * W // 3), a); sprinkle(rng, g, rng.randint(1, max(H, W) // 2), b)
    return g
def tf_aspect_hist(g):
    H, W = dims(g); col = max((kv for kv in counts(g).items() if kv[0]), key=lambda kv: kv[1])[0]; out = blank(H, W)
    if W > H:
        for r in range(H):
            for c in range(sum(1 for v in g[r] if v)): out[r][c] = col
    else:
        for c in range(W):
            k = sum(1 for r in range(H) if g[r][c])
            for r in range(H - k, H): out[r][c] = col
    return out
rule("grid_aspect_picks_histogram", "If the grid is wider than tall each row becomes a left-aligned bar of its coloured-cell count; if taller than wide each column becomes a bottom-aligned bar; bars use the commonest colour.", gi_aspect_hist, tf_aspect_hist)


# 13 object-count parity sets which checkerboard phase the grey overlay takes.
def gi_checker(rng):
    return _scene(rng, 1, 6, 2, 7, cols=NO5)
def tf_checker(g):
    H, W = dims(g); n = len(objects(g, 0)); out = copy(g)
    for r in range(H):
        for c in range(W):
            if g[r][c] == 0 and (r + c) % 2 == n % 2: out[r][c] = 5
    return out
rule("object_parity_sets_checker_phase", "Empty cells get a grey checkerboard: on the even diagonals when the number of objects is even, on the odd diagonals when it is odd.", gi_checker, tf_checker)


# 14 a frame holding a dot is filled with the dot's colour; an empty frame is erased.
def gi_dot_frames(rng):
    H, W = _size(rng, 9, 18); g = blank(H, W); n = rng.randint(2, 4)
    kinds = [True, False] + [rng.random() < 0.5 for _ in range(n - 2)]; rng.shuffle(kinds)
    for has, col in zip(kinds, colours(rng, n)):
        h, w = rng.randint(4, 8), rng.randint(4, 8); pos = _place(rng, g, _ring(h, w), col)
        if pos is None: return None
        if has:
            r0, c0 = pos; g[r0 + rng.randint(1, h - 2)][c0 + rng.randint(1, w - 2)] = rng.choice([x for x in COLOURS if x != col])
    return g
def tf_dot_frames(g):
    out = copy(g)
    for o in components(g, lambda v: v != 0):
        if not _is_ring(o): continue
        r0, c0, r1, c1 = bbox(o); dots = [g[r][c] for r in range(r0 + 1, r1) for c in range(c0 + 1, c1) if g[r][c]]
        if dots: rect(out, r0 + 1, c0 + 1, r1 - 1, c1 - 1, dots[0])
        else:
            for r, c in o: out[r][c] = 0
    return out
rule("dotted_frames_fill_empty_frames_erased", "A hollow frame with a dot inside has its whole interior painted in the dot's colour; a frame with nothing inside is erased.", gi_dot_frames, tf_dot_frames)


# 15 a grey marker on a vertical edge flips the picture left-right, on a horizontal edge top-bottom.
def gi_edge_flip(rng):
    H, W = _size(rng, 7, 18); g = blank(H, W)
    for _ in range(rng.randint(2, 6)):
        sh = _shape(rng, 2, 7); h, w = _hw(sh); _place(rng, g, sh, rng.choice(NO5), rows=(1, H - h - 1), cols_=(1, W - w - 1))
    side = rng.randrange(4)
    r, c = [(0, rng.randint(1, W - 2)), (H - 1, rng.randint(1, W - 2)), (rng.randint(1, H - 2), 0), (rng.randint(1, H - 2), W - 1)][side]
    g[r][c] = 5
    return g if len(objects(g, 0)) >= 3 else None
def tf_edge_flip(g):
    H, W = dims(g); r, c = _grey_cell(g); out = copy(g); out[r][c] = 0
    return flip_h(out) if c in (0, W - 1) else flip_v(out)
rule("edge_marker_picks_flip_axis", "The grey cell on the border is removed and the picture is mirrored left-right if the marker sat on a side edge, top-bottom if it sat on the top or bottom edge.", gi_edge_flip, tf_edge_flip)


# 16 the number of grey dots is the scale factor for the lone shape, output alone.
def gi_dot_scale(rng):
    H, W = _size(rng, 7, 18); g = blank(H, W); k = rng.randint(1, 3); sh = _shape(rng, 3, 6); h, w = _hw(sh)
    if h * w == len(sh) or _place(rng, g, sh, rng.choice(NO5)) is None: return None
    for _ in range(k):
        if _place(rng, g, [(0, 0)], 5) is None: return None
    return g
def tf_dot_scale(g):
    obs = objects(g, 0); dots = [o for o in obs if len(o) == 1 and _col(g, o) == 5]; main = [o for o in obs if len(o) > 1]
    if len(main) != 1: return None
    return _scale(crop(g, *bbox(main[0])), len(dots))
rule("dot_count_scales_lone_shape", "Output the single shape alone, enlarged by a factor equal to the number of grey dots in the grid.", gi_dot_scale, tf_dot_scale)


# 17 a frame whose inner dot matches its colour gets filled; a mismatched dot is wiped.
def gi_match_frames(rng):
    H, W = _size(rng, 10, 20); g = blank(H, W); n = rng.randint(2, 4)
    kinds = [True, False] + [rng.random() < 0.5 for _ in range(n - 2)]; rng.shuffle(kinds)
    for same, col in zip(kinds, colours(rng, n)):
        h, w = rng.randint(5, 9), rng.randint(5, 9); pos = _place(rng, g, _ring(h, w), col)
        if pos is None: return None
        r0, c0 = pos; g[r0 + rng.randint(2, h - 3)][c0 + rng.randint(2, w - 3)] = col if same else rng.choice([x for x in COLOURS if x != col])
    return g
def tf_match_frames(g):
    out = copy(g)
    for o in components(g, lambda v: v != 0):
        if not _is_ring(o): continue
        r0, c0, r1, c1 = bbox(o); col = _col(g, o); dots = [g[r][c] for r in range(r0 + 1, r1) for c in range(c0 + 1, c1) if g[r][c]]
        if dots and dots[0] == col: rect(out, r0 + 1, c0 + 1, r1 - 1, c1 - 1, col)
        else: rect(out, r0 + 1, c0 + 1, r1 - 1, c1 - 1, 0)
    return out
rule("matching_dot_fills_frame_mismatch_clears_dot", "Each frame holds one dot: if the dot has the frame's colour the frame is filled solid, otherwise the dot is erased and the frame stays hollow.", gi_match_frames, tf_match_frames)


# 18 objects touching the grey wall grow by one cell; objects away from it shrink by one cell.
def gi_wall(rng):
    H, W = _size(rng, 10, 18); g = blank(H, W); vert = rng.random() < 0.5
    line = rng.randint(3, (W if vert else H) - 4)
    for i in range(H if vert else W):
        if vert: g[i][line] = 5
        else: g[line][i] = 5
    nt, nf = rng.randint(1, 3), rng.randint(1, 3)
    for i in range(nt + nf):
        h, w = rng.randint(3, 5), rng.randint(3, 5); col = rng.choice(NO5)
        for _ in range(60):
            if i < nt:
                if vert: c0 = rng.choice([line - w, line + 1]); r0 = rng.randint(0, H - h)
                else: r0 = rng.choice([line - h, line + 1]); c0 = rng.randint(0, W - w)
                ok = 0 <= r0 <= H - h and 0 <= c0 <= W - w and all(g[r][c] in (0, 5) for r in range(r0 - 2, r0 + h + 2) for c in range(c0 - 2, c0 + w + 2) if 0 <= r < H and 0 <= c < W)
            else:
                r0, c0 = rng.randint(0, H - h), rng.randint(0, W - w); ok = _free(g, r0, c0, h, w, 2)
            if ok:
                rect(g, r0, c0, r0 + h - 1, c0 + w - 1, col); break
    obs = [o for o in objects(g, 0) if _col(g, o) != 5]
    return g if len(obs) >= 2 else None
def tf_wall(g):
    H, W = dims(g); out = copy(g); grey = set(cells(g, lambda v: v == 5)); nb4 = lambda r, c: ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
    for o in objects(g, 0):
        col = _col(g, o)
        if col == 5: continue
        cs = set(o)
        if any(n in grey for r, c in o for n in nb4(r, c)):
            for r, c in o:
                for nr, nc in nb4(r, c):
                    if 0 <= nr < H and 0 <= nc < W and g[nr][nc] == 0: out[nr][nc] = col
        else:
            for r, c in o:
                if any(n not in cs for n in nb4(r, c)): out[r][c] = 0
    return out
rule("wall_contact_grows_else_erodes", "A block touching the grey wall grows by one cell on every side; a block not touching the wall loses its outer layer of cells.", gi_wall, tf_wall)


# 19 the symmetry of the grey key shape decides whether field objects are mirrored or turned upside down.
def gi_key_sym(rng):
    H, W = _size(rng, 9, 18); g = blank(H, W); sym = rng.random() < 0.5
    for _ in range(60):
        k = [[1 if rng.random() < 0.6 else 0 for _ in range(3)] for _ in range(3)]
        if sym: k = [[row[0], row[1], row[0]] for row in k]
        if any(v for row in k for v in row) and (k == flip_h(k)) == sym and len(components(k, 1, conn8=True)) == 1: break
    else: return None
    for r in range(3):
        for c in range(3):
            if k[r][c]: g[r][c] = 5
    for _ in range(rng.randint(2, 5)):
        sh = _shape(rng, 3, 8); h, w = _hw(sh); _place(rng, g, sh, rng.choice(NO5), rows=(5, H - h))
    return g if len(objects(g, 0)) >= 3 else None
def tf_key_sym(g):
    key = [[1 if g[r][c] == 5 else 0 for c in range(3)] for r in range(3)]; sym = key == flip_h(key); out = copy(g)
    for o in objects(g, 0):
        if _col(g, o) == 5: continue
        r0, c0, r1, c1 = bbox(o)
        for r, c in o: out[r][c] = 0
        for r, c in o: out[r if sym else r0 + r1 - r][c0 + c1 - c] = g[r][c]
    return out
rule("key_symmetry_picks_object_flip", "If the grey key shape in the top-left corner is left-right symmetric every field object is mirrored left-right in place; if it is not, every field object is rotated a half turn in place.", gi_key_sym, tf_key_sym)


# 20 objects sharing the marker's row become 1, its column 2, neither are erased.
def gi_align(rng):
    H, W = _size(rng, 9, 18); g = blank(H, W); mr, mc = rng.randint(2, H - 3), rng.randint(2, W - 3); g[mr][mc] = 5
    kinds = [0, 1, 2] + [rng.randrange(3) for _ in range(rng.randint(0, 3))]; rng.shuffle(kinds)
    for k in kinds:
        sh = _shape(rng, 2, 6); h, w = _hw(sh)
        side_c = rng.choice([(0, mc - w - 1), (mc + 2, W - w)]); side_r = rng.choice([(0, mr - h - 1), (mr + 2, H - h)])
        rows, cols_ = [((mr - h + 1, mr), side_c), (side_r, (mc - w + 1, mc)), (side_r, side_c)][k]
        _place(rng, g, sh, rng.choice([c for c in COLOURS if c not in (1, 2, 5)]), rows=rows, cols_=cols_)
    cls = set()
    for o in objects(g, 0):
        if _col(g, o) == 5: continue
        r0, c0, r1, c1 = bbox(o); cls.add(0 if r0 <= mr <= r1 else 1 if c0 <= mc <= c1 else 2)
    return g if cls == {0, 1, 2} else None
def tf_align(g):
    mr, mc = _grey_cell(g); out = copy(g)
    for o in objects(g, 0):
        if _col(g, o) == 5: continue
        r0, c0, r1, c1 = bbox(o); new = 1 if r0 <= mr <= r1 else 2 if c0 <= mc <= c1 else 0
        for r, c in o: out[r][c] = new
    return out
rule("marker_row_column_alignment_classes", "Objects whose rows include the grey marker's row become colour 1, objects whose columns include its column become colour 2, and objects aligned with neither are erased.", gi_align, tf_align)


# 21 objects of the key cell's colour are completed to their bounding boxes; all other objects are erased.
def gi_key_complete(rng):
    H, W = _size(rng, 8, 18); g = blank(H, W); k = rng.choice(COLOURS); g[0][0] = k; others = colours(rng, 2, exclude=(0, k))
    cols = [k, rng.choice(others)] + [rng.choice([k] + others) for _ in range(rng.randint(0, 4))]
    for col in cols:
        sh = _shape_pred(rng, lambda s: _hw(s)[0] * _hw(s)[1] > len(s), 3, 8)
        if sh: _place(rng, g, sh, col, rows=(2, H - _hw(sh)[0]))
    present = {_col(g, o) for o in objects(g, 0) if o != [(0, 0)]}
    return g if k in present and present - {k} else None
def tf_key_complete(g):
    k = g[0][0]; out = copy(g)
    for o in objects(g, 0):
        if o == [(0, 0)]: continue
        r0, c0, r1, c1 = bbox(o)
        if _col(g, o) == k: rect(out, r0, c0, r1, c1, k)
        else:
            for r, c in o: out[r][c] = 0
    return out
rule("key_colour_objects_completed_rest_erased", "Objects sharing the colour of the top-left key cell are filled out to their full bounding rectangles; objects of any other colour are erased.", gi_key_complete, tf_key_complete)


# 22 the half with more coloured cells pulls everything its way.
def gi_heavy_half(rng):
    H, W = _size(rng, 6, 16); g = blank(H, W)
    for c in colours(rng, rng.randint(1, 3)): sprinkle(rng, g, rng.randint(2, H * W // 6), c)
    l = sum(1 for r in range(H) for c in range(W // 2) if g[r][c]); rt = sum(1 for r in range(H) for c in range((W + 1) // 2, W) if g[r][c])
    return g if l != rt else None
def tf_heavy_half(g):
    H, W = dims(g); l = sum(1 for r in range(H) for c in range(W // 2) if g[r][c]); rt = sum(1 for r in range(H) for c in range((W + 1) // 2, W) if g[r][c])
    if l == rt: return None
    return _cell_gravity(g, 0, -1 if l > rt else 1)
rule("heavier_half_pulls_cells", "Count coloured cells in the left and right halves; every cell slides toward the side that has more and stacks against that edge.", gi_heavy_half, tf_heavy_half)


# 23 a grey bar divides the grid; cells above it rise, cells below it fall.
def gi_bar_split(rng):
    H, W = _size(rng, 8, 18); g = blank(H, W); rb = rng.randint(3, H - 4); g[rb] = [5] * W
    for c in colours(rng, rng.randint(1, 3), exclude=(0, 5)):
        sprinkle(rng, g, rng.randint(2, max(2, H * W // 8)), c)
    up = sum(1 for r in range(rb) for v in g[r] if v); dn = sum(1 for r in range(rb + 1, H) for v in g[r] if v)
    return g if up >= 2 and dn >= 2 else None
def tf_bar_split(g):
    H, W = dims(g); rb = next(r for r in range(H) if all(v == 5 for v in g[r])); out = blank(H, W); out[rb] = [5] * W
    for c in range(W):
        up = [g[r][c] for r in range(rb) if g[r][c]]; dn = [g[r][c] for r in range(rb + 1, H) if g[r][c]]
        for i, v in enumerate(up): out[i][c] = v
        for i, v in enumerate(reversed(dn)): out[H - 1 - i][c] = v
    return out
rule("bar_splits_gravity_directions", "Cells above the full-width grey bar rise and stack against the top edge, cells below it fall and stack against the bottom edge.", gi_bar_split, tf_bar_split)


# 24 the orientation of the big rectangle sets whether dots shoot horizontal or vertical rays.
def gi_orient_rays(rng):
    H, W = _size(rng, 8, 18); g = blank(H, W); h, w = rng.randint(2, 6), rng.randint(2, 6)
    if h == w: return None
    cr, cd = colours(rng, 2)
    if _place(rng, g, _rect(h, w), cr) is None: return None
    for _ in range(rng.randint(1, 5)): _place(rng, g, [(0, 0)], cd)
    return g if any(len(o) == 1 for o in objects(g, 0)) else None
def tf_orient_rays(g):
    H, W = dims(g); obs = objects(g, 0); big = max(obs, key=len); r0, c0, r1, c1 = bbox(big); out = copy(g); horiz = c1 - c0 > r1 - r0
    for o in obs:
        if len(o) != 1: continue
        (r, c), = o; col = g[r][c]
        for dr, dc in ([(0, 1), (0, -1)] if horiz else [(1, 0), (-1, 0)]):
            y, x = r + dr, c + dc
            while 0 <= y < H and 0 <= x < W and g[y][x] == 0: out[y][x] = col; y += dr; x += dc
    return out
rule("largest_orientation_sets_dot_rays", "If the big rectangle is wider than tall every dot extends into a horizontal line, if taller than wide into a vertical line; lines stop at other coloured cells.", gi_orient_rays, tf_orient_rays)


# 25 a block with a bump of its own colour is erased; a block with a differently coloured dot takes the dot's colour.
def gi_adj_dot(rng):
    H, W = _size(rng, 9, 18); g = blank(H, W); n = rng.randint(2, 5)
    kinds = [True, False] + [rng.random() < 0.5 for _ in range(n - 2)]; rng.shuffle(kinds)
    for same in kinds:
        h, w = rng.randint(2, 5), rng.randint(2, 5); col = rng.choice(COLOURS); side = rng.randrange(4)
        dot = [(-1, rng.randrange(w)), (h, rng.randrange(w)), (rng.randrange(h), -1), (rng.randrange(h), w)][side]
        dr, dc = (1 if dot[0] < 0 else 0), (1 if dot[1] < 0 else 0)
        piece = [(r + dr, c + dc, col) for r, c in _rect(h, w)] + [(dot[0] + dr, dot[1] + dc, col if same else rng.choice([x for x in COLOURS if x != col]))]
        if _place_multi(rng, g, piece) is None: return None
    return g
def tf_adj_dot(g):
    out = copy(g)
    for b in _blobs(g):
        cnt = {}
        for r, c in b: cnt[g[r][c]] = cnt.get(g[r][c], 0) + 1
        if len(cnt) == 1:
            for r, c in b: out[r][c] = 0
        else:
            dot = min(cnt, key=cnt.get)
            for r, c in b: out[r][c] = dot
    return out
rule("adjacent_dot_same_colour_erases_else_dyes", "Each block has one cell stuck to its side: if that cell has the block's own colour the whole block is erased, otherwise the block is repainted in the stuck cell's colour.", gi_adj_dot, tf_adj_dot)


# 26 same-colour pairs on a row: close pairs are bridged, far pairs are removed.
def gi_pairs(rng):
    H, W = _size(rng, 7, 18); g = blank(H, W); rows = sorted(rng.sample(range(H), rng.randint(2, min(H // 2, 8))))
    rows = [r for i, r in enumerate(rows) if i == 0 or r - rows[i - 1] >= 2]
    if len(rows) < 2: return None
    kinds = [True, False] + [rng.random() < 0.5 for _ in range(len(rows) - 2)]; rng.shuffle(kinds)
    for r, close in zip(rows, kinds):
        gap = rng.randint(1, 2) if close else rng.randint(4, W - 2); c1 = rng.randint(0, W - gap - 2); col = rng.choice(COLOURS)
        g[r][c1] = g[r][c1 + gap + 1] = col
    return g
def tf_pairs(g):
    out = copy(g)
    for r, row in enumerate(g):
        cs = [c for c, v in enumerate(row) if v]
        if len(cs) != 2: continue
        if cs[1] - cs[0] - 1 <= 2:
            for c in range(cs[0], cs[1] + 1): out[r][c] = row[cs[0]]
        else: out[r][cs[0]] = out[r][cs[1]] = 0
    return out
rule("close_pairs_bridged_far_pairs_removed", "Each row holds a pair of same-coloured cells: pairs at most two cells apart are joined by a line of their colour, pairs further apart are both erased.", gi_pairs, tf_pairs)


# 27 the number of frames decides the fill colour: odd -> 1, even -> 2.
def gi_frame_parity(rng):
    H, W = _size(rng, 8, 18); g = blank(H, W); n = rng.randint(1, 5); col = rng.choice(COLOURS[2:])
    for _ in range(n):
        if _place(rng, g, _ring(rng.randint(3, 7), rng.randint(3, 7)), col) is None: return None
    return g
def tf_frame_parity(g):
    fr = [o for o in components(g, lambda v: v != 0) if _is_ring(o)]; out = copy(g); fill = 1 if len(fr) % 2 else 2
    for o in fr:
        r0, c0, r1, c1 = bbox(o); rect(out, r0 + 1, c0 + 1, r1 - 1, c1 - 1, fill)
    return out
rule("frame_count_parity_picks_fill", "Count the hollow frames: if the count is odd every frame is filled with colour 1, if even with colour 2.", gi_frame_parity, tf_frame_parity)


# 28 small objects touching the largest take its colour; the others stay.
def gi_dye(rng):
    H, W = _size(rng, 9, 18); g = blank(H, W); cb = rng.choice(COLOURS); big = _shape(rng, 9, 14); pos = _place(rng, g, big, cb, margin=2)
    if pos is None: return None
    tgt = {(pos[0] + r, pos[1] + c) for r, c in big}; pal = [c for c in COLOURS if c != cb]
    for _ in range(rng.randint(1, 3)): _place_touching(rng, g, _shape(rng, 2, 4), rng.choice(pal), tgt)
    for _ in range(rng.randint(1, 3)): _place(rng, g, _shape(rng, 2, 4), rng.choice(pal))
    obs = objects(g, 0); big_o = max(obs, key=len)
    if len(big_o) != len(big): return None
    touch = [o for o in obs if o is not big_o and any(abs(r - br) <= 1 and abs(c - bc) <= 1 for r, c in o for br, bc in big_o)]
    return g if touch and len(touch) < len(obs) - 1 else None
def tf_dye(g):
    obs = objects(g, 0); big = max(obs, key=len); cb = _col(g, big); out = copy(g)
    for o in obs:
        if o is not big and any(abs(r - br) <= 1 and abs(c - bc) <= 1 for r, c in o for br, bc in big):
            for r, c in o: out[r][c] = cb
    return out
rule("largest_dyes_its_neighbours", "Every small object that touches the largest object, even at a corner, is repainted in the largest object's colour; objects not touching it keep theirs.", gi_dye, tf_dye)


# 29 a tall grid drops cells to the floor, a wide grid slides them to the right wall.
def gi_aspect_gravity(rng):
    H, W = _size(rng, 5, 16)
    if H == W: return None
    g = blank(H, W)
    for c in colours(rng, rng.randint(1, 3)): sprinkle(rng, g, rng.randint(2, H * W // 6), c)
    return g
def tf_aspect_gravity(g):
    H, W = dims(g)
    return _cell_gravity(g, 1, 0) if H > W else _cell_gravity(g, 0, 1)
rule("grid_aspect_sets_gravity_axis", "If the grid is taller than wide every cell falls to the bottom edge; if wider than tall every cell slides to the right edge.", gi_aspect_gravity, tf_aspect_gravity)


# 30 objects with more cells than there are objects become 1, the rest 2.
def gi_cells_vs_count(rng):
    g = _scene(rng, 3, 7, 2, 9, cols=COLOURS[2:])
    if g is None: return None
    obs = objects(g, 0); n = len(obs)
    return g if any(len(o) > n for o in obs) and any(len(o) <= n for o in obs) else None
def tf_cells_vs_count(g):
    obs = objects(g, 0); n = len(obs); out = copy(g)
    for o in obs:
        for r, c in o: out[r][c] = 1 if len(o) > n else 2
    return out
rule("cells_vs_object_count_recolour", "Count the objects; every object with more cells than that count becomes colour 1 and every other object becomes colour 2.", gi_cells_vs_count, tf_cells_vs_count)


# 31 the divider's colour says which side survives: 1 keeps the left part, 2 keeps the right part.
def gi_divider(rng):
    H, W = _size(rng, 7, 18); g = blank(H, W); cm = rng.randint(3, W - 4); key = rng.choice((1, 2))
    for r in range(H): g[r][cm] = key
    a, b = colours(rng, 2, exclude=(0, 1, 2))
    for col, lo, hi in ((a, 0, cm), (b, 0, cm), (a, cm + 1, W), (b, cm + 1, W)):
        for _ in range(rng.randint(1, max(1, H * (hi - lo) // 6))): g[rng.randrange(H)][rng.randrange(lo, hi)] = col
    return g
def tf_divider(g):
    H, W = dims(g); cm = next(c for c in range(W) if g[0][c] in (1, 2) and all(g[r][c] == g[0][c] for r in range(H)))
    return [row[:cm] for row in g] if g[0][cm] == 1 else [row[cm + 1:] for row in g]
rule("divider_colour_picks_kept_half", "A full-height line splits the grid: if the line is colour 1 output everything left of it, if colour 2 output everything right of it.", gi_divider, tf_divider)


# 32 objects on either side slide toward the grey column until they touch it or each other.
def gi_gather(rng):
    H, W = _size(rng, 9, 20); g = blank(H, W); cm = rng.randint(3, W - 4)
    for r in range(H): g[r][cm] = 5
    for i in range(rng.randint(2, 6)):
        sh = _shape(rng, 2, 6); h, w = _hw(sh); left = i % 2 == 0
        _place(rng, g, sh, rng.choice(NO5), cols_=(0, cm - w - 1) if left else (cm + 2, W - w))
    return g if len(objects(g, 0)) >= 3 else None
def tf_gather(g):
    H, W = dims(g); cm = next(c for c in range(W) if all(g[r][c] == 5 for r in range(H))); out = blank(H, W); occ = set()
    for r in range(H): out[r][cm] = 5; occ.add((r, cm))
    obs = [o for o in objects(g, 0) if _col(g, o) != 5]
    _slide_into(g, out, occ, [o for o in obs if o[0][1] < cm], 0, 1)
    _slide_into(g, out, occ, [o for o in obs if o[0][1] > cm], 0, -1)
    return out
rule("objects_gather_at_marker_column", "Objects left of the grey column slide right and objects right of it slide left until they rest against the column or an object already resting there.", gi_gather, tf_gather)


# 33 field objects matching the grey key shape stay; the others collapse to their bounding-box outline.
def gi_key_match(rng):
    H, W = _size(rng, 9, 18); g = blank(H, W); key = _shape_pred(rng, lambda s: _hw(s)[0] <= 3 and _hw(s)[1] <= 3 and len(s) < 9, 3, 6)
    if key is None: return None
    for r, c in key: g[r][c] = 5
    kn = frozenset(key); n = rng.randint(2, 5); kinds = [True, False] + [rng.random() < 0.5 for _ in range(n - 2)]
    for same in kinds:
        if same: sh = key
        else:
            sh = _shape_pred(rng, lambda s: frozenset(s) != kn and _hw(s)[0] >= 3 and _hw(s)[1] >= 3 and set(s) != set(_ring(*_hw(s))), 5, 9)
            if sh is None: return None
        _place(rng, g, sh, rng.choice(NO5), rows=(5, H - _hw(sh)[0]))
    obs = [o for o in objects(g, 0) if _col(g, o) != 5]
    return g if any(_norm(o) == kn for o in obs) and any(_norm(o) != kn for o in obs) else None
def tf_key_match(g):
    kn = _norm(cells(g, lambda v: v == 5)); out = copy(g)
    for o in objects(g, 0):
        if _col(g, o) == 5 or _norm(o) == kn: continue
        r0, c0, r1, c1 = bbox(o); col = _col(g, o)
        for r, c in o: out[r][c] = 0
        rect(out, r0, c0, r1, c1, col, fill=False)
    return out
rule("key_shape_match_kept_others_boxed", "Field objects with exactly the shape of the grey key in the corner are kept; every other object is replaced by the hollow outline of its bounding box in its own colour.", gi_key_match, tf_key_match)


# 34 if the dots outnumber the blob's cells the blob sinks to the floor, otherwise it rises to the ceiling.
def gi_blob_dots(rng):
    H, W = _size(rng, 8, 18); g = blank(H, W); cb, cd = colours(rng, 2); blob = _shape(rng, 4, 10); h, w = _hw(blob)
    if _place(rng, g, blob, cb, rows=(2, H - h - 2)) is None: return None
    nd = rng.randint(2, 14)
    if nd == len(blob): return None
    for _ in range(nd): _place(rng, g, [(0, 0)], cd)
    return g if sum(1 for o in objects(g, 0) if len(o) == 1) != len(blob) else None
def tf_blob_dots(g):
    H, W = dims(g); obs = objects(g, 0); blob = max(obs, key=len); dots = [o for o in obs if len(o) == 1]
    out = blank(H, W); occ = set()
    for o in dots:
        (r, c), = o; out[r][c] = g[r][c]; occ.add((r, c))
    return _slide_into(g, out, occ, [blob], 1 if len(dots) > len(blob) else -1, 0)
rule("outnumbered_blob_sinks_else_rises", "If the single dots outnumber the cells of the blob the blob drops straight down until blocked, otherwise it rises straight up until blocked; the dots stay.", gi_blob_dots, tf_blob_dots)


# 35 the highest-reaching object sets a water level: every empty cell on or below its top row turns blue.
def gi_water(rng):
    H, W = _size(rng, 7, 18); g = blank(H, W)
    for _ in range(rng.randint(2, 6)):
        sh = _shape(rng, 2, 8); h, w = _hw(sh); _place(rng, g, sh, rng.choice([c for c in COLOURS if c != 8]), rows=(1, H - h))
    top = min((r for r, _ in cells(g, lambda v: v)), default=None)
    return g if top is not None and 1 <= top <= H - 3 else None
def tf_water(g):
    H, W = dims(g); top = min(r for r, _ in cells(g, lambda v: v)); out = copy(g)
    for r in range(top, H):
        for c in range(W):
            if g[r][c] == 0: out[r][c] = 8
    return out
rule("highest_object_sets_water_level", "The object reaching highest sets the water line: every empty cell on or below its top row is flooded with colour 8, rows above stay empty.", gi_water, tf_water)


# 36 parity of the number of distinct colours selects the flip axis.
def gi_colour_parity(rng):
    H, W = _size(rng, 6, 18); g = blank(H, W); k = rng.randint(2, 6); pal = colours(rng, k)
    for i in range(rng.randint(k, k + 4)): _place(rng, g, _shape(rng, 2, 7), pal[i % k])
    return g if len({v for row in g for v in row if v}) == k else None
def tf_colour_parity(g):
    k = len({v for row in g for v in row if v})
    return flip_h(g) if k % 2 else flip_v(g)
rule("distinct_colour_parity_picks_flip", "If the number of distinct colours in the grid is odd the whole grid is mirrored left-right, if even it is mirrored top-bottom.", gi_colour_parity, tf_colour_parity)


# 37 every other object sharing the largest object's colour is erased.
def gi_siblings(rng):
    H, W = _size(rng, 9, 18); g = blank(H, W); cb = rng.choice(COLOURS); pal = [c for c in COLOURS if c != cb]
    if _place(rng, g, _shape(rng, 9, 14), cb) is None: return None
    for _ in range(rng.randint(1, 3)): _place(rng, g, _shape(rng, 2, 5), cb)
    for _ in range(rng.randint(1, 3)): _place(rng, g, _shape(rng, 2, 5), rng.choice(pal))
    obs = objects(g, 0); sizes = sorted(len(o) for o in obs)
    return g if sizes[-1] > sizes[-2] and sum(1 for o in obs if _col(g, o) == cb) >= 2 and any(_col(g, o) != cb for o in obs) else None
def tf_siblings(g):
    obs = objects(g, 0); big = max(obs, key=len); cb = _col(g, big); out = copy(g)
    for o in obs:
        if o is not big and _col(g, o) == cb:
            for r, c in o: out[r][c] = 0
    return out
rule("largest_colour_siblings_erased", "Every object that has the same colour as the largest object, except the largest itself, is erased; objects of other colours stay.", gi_siblings, tf_siblings)


# 38 objects wider than the grey bar at the top are trimmed on the right to the bar's width.
def gi_bar_trim(rng):
    H, W = _size(rng, 9, 18); g = blank(H, W); wb = rng.randint(2, 5)
    for c in range(wb): g[0][c] = 5
    preds = [lambda s: _hw(s)[1] > wb, lambda s: _hw(s)[1] <= wb] + [rng.choice([lambda s: _hw(s)[1] > wb, lambda s: _hw(s)[1] <= wb]) for _ in range(rng.randint(0, 3))]
    for p in preds:
        sh = _shape_pred(rng, lambda s: p(s) and _hw(s)[1] <= min(9, W), 3, 10)
        if sh is None: return None
        _place(rng, g, sh, rng.choice(NO5), rows=(2, H - _hw(sh)[0]))
    ws = [bbox(o)[3] - bbox(o)[1] + 1 for o in objects(g, 0) if _col(g, o) != 5]
    return g if any(w > wb for w in ws) and any(w <= wb for w in ws) else None
def tf_bar_trim(g):
    wb = sum(1 for v in g[0] if v == 5); out = copy(g)
    for o in objects(g, 0):
        if _col(g, o) == 5: continue
        c0 = min(c for _, c in o)
        for r, c in o:
            if c >= c0 + wb: out[r][c] = 0
    return out
rule("bar_width_trims_wider_objects", "Any object wider than the grey bar in the top-left corner loses its columns beyond the bar's width, cut from the right; narrower objects are untouched.", gi_bar_trim, tf_bar_trim)


# 39 of two objects the smaller slides toward the larger until they touch.
def gi_small_to_large(rng):
    H, W = _size(rng, 8, 18); g = blank(H, W); a, b = colours(rng, 2); big = _shape(rng, 7, 12); small = _shape(rng, 2, 5)
    if _place(rng, g, big, a, margin=2) is None or _place(rng, g, small, b, margin=2) is None: return None
    obs = objects(g, 0)
    if len(obs) != 2: return None
    (r0, c0, r1, c1), (s0, t0, s1, t1) = bbox(obs[0]), bbox(obs[1])
    return g if (r1 < s0 or s1 < r0) != (c1 < t0 or t1 < c0) else None
def tf_small_to_large(g):
    H, W = dims(g); obs = objects(g, 0); big = max(obs, key=len); small = min(obs, key=len)
    r0, c0, r1, c1 = bbox(big); s0, t0, s1, t1 = bbox(small)
    if r1 < s0 or s1 < r0: dr, dc = (-1 if s0 > r1 else 1), 0
    else: dr, dc = 0, (-1 if t0 > c1 else 1)
    out = blank(H, W); occ = set(big)
    for r, c in big: out[r][c] = g[r][c]
    return _slide_into(g, out, occ, [small], dr, dc)
rule("smaller_object_slides_to_larger", "The smaller of the two objects slides straight toward the larger one, vertically or horizontally depending on where it lies, until the two touch.", gi_small_to_large, tf_small_to_large)


# 40 column pairs: same colour -> join with a line; different colours -> both erased.
def gi_col_pairs(rng):
    H, W = _size(rng, 7, 18); g = blank(H, W); cols_ = sorted(rng.sample(range(W), rng.randint(2, min(W // 2, 8))))
    cols_ = [c for i, c in enumerate(cols_) if i == 0 or c - cols_[i - 1] >= 2]
    if len(cols_) < 2: return None
    kinds = [True, False] + [rng.random() < 0.5 for _ in range(len(cols_) - 2)]; rng.shuffle(kinds)
    for c, same in zip(cols_, kinds):
        r1, r2 = sorted(rng.sample(range(H), 2))
        if r2 - r1 < 2: r2 = min(H - 1, r1 + 2)
        a = rng.choice(COLOURS); g[r1][c] = a; g[r2][c] = a if same else rng.choice([x for x in COLOURS if x != a])
    return g
def tf_col_pairs(g):
    H, W = dims(g); out = copy(g)
    for c in range(W):
        rs = [r for r in range(H) if g[r][c]]
        if len(rs) != 2: continue
        if g[rs[0]][c] == g[rs[1]][c]:
            for r in range(rs[0], rs[1] + 1): out[r][c] = g[rs[0]][c]
        else: out[rs[0]][c] = out[rs[1]][c] = 0
    return out
rule("column_pair_same_colour_joins_else_erased", "Each marked column holds two cells: if they share a colour they are joined by a vertical line of it, if their colours differ both are erased.", gi_col_pairs, tf_col_pairs)
