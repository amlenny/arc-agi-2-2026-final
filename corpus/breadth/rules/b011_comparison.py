# b011_comparison.py -- comparison and relations between objects or regions: which of two is bigger / taller /
# wider / has more holes, pairs joined by a line or touching, same-vs-unique property classes, per-row and
# per-half contests, objects measured against a frame or a reference, stacks and bars equalised or differenced.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


# ---------------------------------------------------------------- local helpers
def _size(rng, lo=6, hi=18):
    """Grid dims; about 40% of the time both sides land in the 21-30 band."""
    if rng.random() < 0.4:
        return rng.randint(21, 30), rng.randint(21, 30)
    return size(rng, lo, hi)


def _col(g, o):
    return g[o[0][0]][o[0][1]]


def _hw(sh):
    return max(r for r, _ in sh) + 1, max(c for _, c in sh) + 1


def _bh(o):
    r0, c0, r1, c1 = bbox(o); return r1 - r0 + 1


def _bw(o):
    r0, c0, r1, c1 = bbox(o); return c1 - c0 + 1


def _shape(rng, lo=3, hi=8):
    return frozenset(random_shape(rng, rng.randint(lo, hi)))


def _rect(h, w):
    return frozenset((r, c) for r in range(h) for c in range(w))


def _ring(h, w):
    return frozenset((r, c) for r in range(h) for c in range(w) if r in (0, h - 1) or c in (0, w - 1))


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
    """Stamp sh (set of (r,c)) in colour col at a random spot with `margin` empty cells around; returns (r0,c0)."""
    H, W = dims(g); h, w = _hw(sh)
    rlo, rhi = rows or (0, H - h); clo, chi = cols_ or (0, W - w)
    rhi, chi = min(rhi, H - h), min(chi, W - w)
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
    if h > H or w > W:
        return None
    for _ in range(tries):
        r0, c0 = rng.randint(0, H - h), rng.randint(0, W - w)
        if _free(g, r0, c0, h, w, margin):
            for r, c, col in cells_cols:
                g[r0 + r][c0 + c] = col
            return r0, c0
    return None


def _blobs(g, bg=0):
    """4-connected components of non-background cells regardless of colour (glib.components splits by colour)."""
    H, W = dims(g); seen, out = set(), []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or (r, c) in seen:
                continue
            comp, st = [], [(r, c)]; seen.add((r, c))
            while st:
                y, x = st.pop(); comp.append((y, x))
                for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen and g[ny][nx] != bg:
                        seen.add((ny, nx)); st.append((ny, nx))
            out.append(comp)
    return out


def _holes(g, o):
    """Number of enclosed empty regions inside o's bounding box."""
    r0, c0, r1, c1 = bbox(o); cs = set(o)
    sub = [[1 if (r, c) in cs else 0 for c in range(c0 - 1, c1 + 2)] for r in range(r0 - 1, r1 + 2)]
    h, w = dims(sub)
    return sum(1 for cm in components(sub, 0) if all(0 < r < h - 1 and 0 < c < w - 1 for r, c in cm))


def _punch(rng, g, r0, c0, h, w, k):
    """Cut k single-cell holes into the interior of the rectangle at (r0,c0), no two holes adjacent."""
    interior = [(r, c) for r in range(r0 + 1, r0 + h - 1) for c in range(c0 + 1, c0 + w - 1)]
    rng.shuffle(interior); got = []
    for r, c in interior:
        if len(got) == k:
            break
        if all(abs(r - y) > 1 or abs(c - x) > 1 for y, x in got):
            got.append((r, c)); g[r][c] = 0
    return len(got) == k


def _objs(g):
    return components(g, lambda v: v != 0, conn8=False)


def _bars(g):
    """Column -> height for bottom-anchored vertical bars; colour of each from its bottom cell."""
    H, W = dims(g)
    return {c: sum(1 for r in range(H) if g[r][c]) for c in range(W) if g[H - 1][c]}


# ---------------------------------------------------------------- 1 taller of two is recoloured grey
def gi_taller(rng):
    h, w = _size(rng, 6, 16); g = blank(h, w); c = rng.choice([x for x in COLOURS if x != 5])
    a, b = _shape(rng, 3, 9), _shape(rng, 3, 9)
    if _hw(a)[0] == _hw(b)[0]: return None
    return g if _place(rng, g, a, c) and _place(rng, g, b, c) else None
def tf_taller(g):
    obs = _objs(g)
    if len(obs) != 2 or _bh(obs[0]) == _bh(obs[1]): return None
    out = copy(g)
    for r, c in max(obs, key=_bh): out[r][c] = 5
    return out
rule("taller_of_two_recoloured_grey", "Of the two objects, the one spanning more rows is repainted grey (5); the other is unchanged.", gi_taller, tf_taller)


# ---------------------------------------------------------------- 2 wider of two erased
def gi_wider(rng):
    h, w = _size(rng, 6, 16); g = blank(h, w)
    a, b = _shape(rng, 3, 9), _shape(rng, 3, 9)
    if _hw(a)[1] == _hw(b)[1]: return None
    return g if _place(rng, g, a, rng.choice(COLOURS)) and _place(rng, g, b, rng.choice(COLOURS)) else None
def tf_wider(g):
    obs = _objs(g)
    if len(obs) != 2 or _bw(obs[0]) == _bw(obs[1]): return None
    out = copy(g)
    for r, c in max(obs, key=_bw): out[r][c] = 0
    return out
rule("wider_of_two_erased", "Of the two objects, the one spanning more columns is erased; the narrower one stays.", gi_wider, tf_wider)


# ---------------------------------------------------------------- 3 the rectangle with more holes gets them filled
def gi_moreholes(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w); ks = rng.sample(range(0, 5), 2)
    for k in ks:
        rh, rw = rng.randint(5, 8), rng.randint(5, 8); p = _place(rng, g, _rect(rh, rw), rng.choice([x for x in COLOURS if x != 8]))
        if p is None or not _punch(rng, g, p[0], p[1], rh, rw, k): return None
    return g
def tf_moreholes(g):
    obs = _objs(g)
    if len(obs) != 2: return None
    hs = [_holes(g, o) for o in obs]
    if hs[0] == hs[1]: return None
    o = obs[hs.index(max(hs))]; r0, c0, r1, c1 = bbox(o); out = copy(g)
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if out[r][c] == 0: out[r][c] = 8
    return out
rule("more_holes_rectangle_holes_filled", "Of the two rectangles, the one with more holes has every hole filled with colour 8; the other keeps its holes.", gi_moreholes, tf_moreholes)


# ---------------------------------------------------------------- 4/5 pairs joined by a grey line
def _joined_pairs(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w); r = 0; n = 0
    while r + 3 <= h:
        bh = rng.randint(2, min(5, h - r))
        ha, hb = rng.randint(2, bh), rng.randint(2, bh); wa, wb = rng.randint(1, 5), rng.randint(1, 5)
        if ha * wa == hb * wb or wa + wb + 2 > w: r += bh + 1; continue
        ca, cb = colours(rng, 2, exclude=(0, 5)); gap = rng.randint(2, w - wa - wb)
        c0 = rng.randint(0, w - wa - wb - gap); ra, rb = r + rng.randint(0, bh - ha), r + rng.randint(0, bh - hb)
        lo, hi = max(ra, rb), min(ra + ha, rb + hb) - 1
        if lo > hi: r += bh + 1; continue
        rect(g, ra, c0, ra + ha - 1, c0 + wa - 1, ca); rect(g, rb, c0 + wa + gap, rb + hb - 1, c0 + wa + gap + wb - 1, cb)
        lr = rng.randint(lo, hi)
        for x in range(c0 + wa, c0 + wa + gap): g[lr][x] = 5
        n += 1; r += bh + 1 + rng.randint(0, 2)
        if n >= rng.randint(1, 4): break
    return g if n else None
def _pair_ends(g, line):
    r = line[0][0]; cs = [c for _, c in line]; H, W = dims(g); a, b = min(cs) - 1, max(cs) + 1
    if a < 0 or b >= W or g[r][a] in (0, 5) or g[r][b] in (0, 5): return None
    obs = components(g, lambda v: v not in (0, 5), conn8=False)
    oa = next(o for o in obs if (r, a) in set(o)); ob = next(o for o in obs if (r, b) in set(o))
    return oa, ob
def tf_joined_smaller(g):
    out = copy(g); done = 0
    for line in components(g, 5):
        if len({r for r, _ in line}) != 1: return None
        ends = _pair_ends(g, line)
        if ends is None or len(ends[0]) == len(ends[1]): return None
        small, big = sorted(ends, key=len); col = _col(g, big)
        for r, c in small: out[r][c] = col
        done += 1
    return out if done else None
rule("line_joined_pairs_smaller_takes_larger_colour", "Each grey line joins two rectangles; the rectangle with fewer cells is repainted in the colour of the larger one.", _joined_pairs, tf_joined_smaller)
def tf_joined_line(g):
    out = copy(g); done = 0
    for line in components(g, 5):
        if len({r for r, _ in line}) != 1: return None
        ends = _pair_ends(g, line)
        if ends is None or len(ends[0]) == len(ends[1]): return None
        col = _col(g, max(ends, key=len))
        for r, c in line: out[r][c] = col
        done += 1
    return out if done else None
rule("joined_pair_line_takes_larger_colour", "Each grey line joins two rectangles; the line is repainted in the colour of whichever rectangle has more cells.", _joined_pairs, tf_joined_line)


# ---------------------------------------------------------------- 6 shared cell count vs unique cell count
def gi_samesize(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w); k = rng.randint(3, 7)
    sizes = [rng.randint(2, 7) for _ in range(k)]
    cnt = {s: sizes.count(s) for s in sizes}
    if not any(v > 1 for v in cnt.values()) or not any(v == 1 for v in cnt.values()): return None
    for s in sizes:
        if _place(rng, g, _shape(rng, s, s), rng.choice([x for x in COLOURS if x not in (1, 2)])) is None: return None
    return g
def tf_samesize(g):
    obs = _objs(g); cnt = {}
    for o in obs: cnt[len(o)] = cnt.get(len(o), 0) + 1
    out = copy(g)
    for o in obs:
        for r, c in o: out[r][c] = 1 if cnt[len(o)] > 1 else 2
    return out
rule("same_cell_count_one_unique_two", "Objects whose cell count matches another object's become 1; objects with a cell count no other object has become 2.", gi_samesize, tf_samesize)


# ---------------------------------------------------------------- 7 odd colour erased
def gi_oddcol(rng):
    h, w = _size(rng, 7, 18); g = blank(h, w); k = rng.randint(3, 7); c, d = colours(rng, 2); odd = rng.randrange(k)
    for i in range(k):
        if _place(rng, g, _shape(rng, 2, 7), d if i == odd else c) is None: return None
    return g
def tf_oddcol(g):
    obs = _objs(g); cnt = {}
    for o in obs: cnt[_col(g, o)] = cnt.get(_col(g, o), 0) + 1
    odd = [o for o in obs if cnt[_col(g, o)] == 1]
    if len(odd) != 1 or len(cnt) != 2: return None
    out = copy(g)
    for r, c in odd[0]: out[r][c] = 0
    return out
rule("odd_colour_object_erased", "All objects share one colour except one; the differently coloured object is erased.", gi_oddcol, tf_oddcol)


# ---------------------------------------------------------------- 8 per row: minority colour erased
def _two_colour_rows(rng):
    h, w = _size(rng, 5, 16); g = blank(h, w); a, b = colours(rng, 2)
    for r in range(h):
        if rng.random() < 0.15: continue
        for c in range(w):
            if rng.random() < rng.choice([0.3, 0.5, 0.7]): g[r][c] = rng.choice([a, b])
    return g
def tf_rowminority(g):
    out = copy(g); cols = sorted({v for row in g for v in row if v})
    if len(cols) != 2: return None
    a, b = cols
    for r, row in enumerate(g):
        na, nb = row.count(a), row.count(b)
        if na != nb:
            loser = b if na > nb else a
            for c, v in enumerate(row):
                if v == loser: out[r][c] = 0
    return out
rule("row_minority_colour_erased", "In every row, cells of the colour that appears fewer times in that row are erased; tied rows are unchanged.", _two_colour_rows, tf_rowminority)


# ---------------------------------------------------------------- 9/10 per row: left half vs right half
def _half_rows(rng):
    h, hw = rng.randint(4, 16), rng.randint(2, 8)
    if rng.random() < 0.4: h, hw = rng.randint(21, 30), rng.randint(11, 15)
    g = blank(h, 2 * hw)
    for r in range(h):
        if rng.random() < 0.15: continue
        col = rng.choice(COLOURS)
        for c in range(2 * hw):
            if rng.random() < rng.choice([0.25, 0.5, 0.75]): g[r][c] = col
    return g
def tf_halffill(g):
    H, W = dims(g); hw = W // 2; out = copy(g)
    for r in range(H):
        cols = {v for v in g[r] if v}
        if len(cols) != 1: continue
        col = cols.pop(); nl = sum(1 for v in g[r][:hw] if v); nr = sum(1 for v in g[r][hw:] if v)
        if nl == nr: continue
        out[r] = [col] * hw + [0] * hw if nl > nr else [0] * hw + [col] * hw
    return out
rule("row_halves_richer_side_filled", "In each row, whichever half holds more coloured cells is filled solid with that row's colour and the other half is emptied; tied rows stay.", _half_rows, tf_halffill)
def tf_halfcol(g):
    H, W = dims(g); hw = W // 2; out = []
    for r in range(H):
        nl = sum(1 for v in g[r][:hw] if v); nr = sum(1 for v in g[r][hw:] if v)
        out.append([1 if nl > nr else 2 if nr > nl else 0])
    return out if len({v[0] for v in out}) >= 2 else None
rule("row_half_winner_column", "Output one column with a cell per row: 1 if the row's left half has more coloured cells, 2 if the right half has more, empty on a tie.", _half_rows, tf_halfcol)


# ---------------------------------------------------------------- 11 block inside a frame vs the frame's interior
def gi_framecontent(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w); n = 0
    for _ in range(rng.randint(1, 3)):
        fh, fw = rng.randint(5, min(10, h)), rng.randint(5, min(10, w)); f, c = colours(rng, 2)
        p = _place(rng, g, _ring(fh, fw), f)
        if p is None: continue
        ih, iw = fh - 2, fw - 2; bh, bw = rng.randint(1, ih), rng.randint(1, iw)
        if 2 * bh * bw == ih * iw: continue
        r0, c0 = p[0] + 1 + rng.randint(0, ih - bh), p[1] + 1 + rng.randint(0, iw - bw)
        rect(g, r0, c0, r0 + bh - 1, c0 + bw - 1, c); n += 1
    return g if n else None
def tf_framecontent(g):
    out = copy(g); n = 0
    for o in _objs(g):
        if not _is_ring(o): continue
        r0, c0, r1, c1 = bbox(o); f = _col(g, o)
        inner = [(r, c) for r in range(r0 + 1, r1) for c in range(c0 + 1, c1) if g[r][c] not in (0, f)]
        if not inner: continue
        area = (r1 - r0 - 1) * (c1 - c0 - 1)
        if 2 * len(inner) == area: return None
        if 2 * len(inner) > area:
            for r, c in o: out[r][c] = g[inner[0][0]][inner[0][1]]
        else:
            for r, c in inner: out[r][c] = f
        n += 1
    return out if n else None
rule("frame_vs_content_size_recolour", "A block inside a frame covering more than half of the frame's interior gives its colour to the frame; a block covering half or less takes the frame's colour.", gi_framecontent, tf_framecontent)


# ---------------------------------------------------------------- 12/31 two stacks
def _two_stacks(rng, mind=1):
    h, w = _size(rng, 5, 14); g = blank(h, w); a, b = colours(rng, 2)
    ca, cb = sorted(rng.sample(range(w), 2)); ha, hb = rng.randint(1, h - 1), rng.randint(1, h - 1)
    if abs(ha - hb) < mind: return None
    for r in range(h - ha, h): g[r][ca] = a
    for r in range(h - hb, h): g[r][cb] = b
    return g
def tf_stackdiff(g):
    H, W = dims(g); bars = _bars(g)
    if len(bars) != 2: return None
    (c1, h1), (c2, h2) = bars.items()
    if h1 == h2: return None
    tall, d = (c1, h1 - h2) if h1 > h2 else (c2, h2 - h1); col = g[H - 1][tall]
    return [[col] if r >= H - d else [0] for r in range(H)]
rule("stack_height_difference_column", "Output a single column as tall as the grid: a bar from the bottom in the taller stack's colour, as long as the difference between the two stacks' heights.", lambda rng: _two_stacks(rng, 1), tf_stackdiff)
def tf_level(g):
    H, W = dims(g); bars = _bars(g)
    if len(bars) != 2: return None
    (c1, h1), (c2, h2) = bars.items()
    if abs(h1 - h2) < 2: return None
    tall, short = (c1, c2) if h1 > h2 else (c2, c1); tot = h1 + h2; nt, ns = (tot + 1) // 2, tot // 2
    out = copy(g); col = g[H - 1][tall]
    for r in range(H):
        if r < H - nt: out[r][tall] = 0
        if H - ns <= r < H - min(h1, h2): out[r][short] = col
    return out
rule("stacks_level_out", "Cells are moved from the top of the taller stack onto the shorter one until the two stacks are level (the taller keeps one extra if the total is odd); moved cells keep the taller stack's colour.", lambda rng: _two_stacks(rng, 2), tf_level)


# ---------------------------------------------------------------- 13/14 bars equalised
def _bars_scene(rng, lo=1):
    h, w = _size(rng, 5, 14); g = blank(h, w); k = rng.randint(2, max(2, w // 2)); cs = sorted(rng.sample(range(w), k))
    hs = [rng.randint(lo, h - 1) for _ in cs]
    if len(set(hs)) < 2: return None
    for c, k_ in zip(cs, hs):
        col = rng.choice(COLOURS)
        for r in range(h - k_, h): g[r][c] = col
    return g
def tf_eq_tall(g):
    H, W = dims(g); bars = _bars(g); T = max(bars.values()); out = copy(g)
    if T == min(bars.values()): return None
    for c, k in bars.items():
        for r in range(H - T, H - k): out[r][c] = g[H - 1][c]
    return out
rule("equalise_bars_to_tallest", "Every vertical bar is extended upward in its own colour until it is as tall as the tallest bar.", _bars_scene, tf_eq_tall)
def tf_eq_short(g):
    H, W = dims(g); bars = _bars(g); S = min(bars.values()); out = copy(g)
    if S == max(bars.values()): return None
    for c, k in bars.items():
        for r in range(H - k, H - S): out[r][c] = 0
    return out
rule("trim_bars_to_shortest", "Every vertical bar is cut down to the height of the shortest bar.", _bars_scene, tf_eq_short)


# ---------------------------------------------------------------- 15 odd orientation bar
def gi_oddorient(rng):
    h, w = _size(rng, 7, 18); g = blank(h, w); k = rng.randint(3, 7); c = rng.choice([x for x in COLOURS if x != 8])
    vert = rng.random() < 0.5; odd = rng.randrange(k)
    for i in range(k):
        n = rng.randint(2, 6); sh = _rect(n, 1) if vert != (i == odd) else _rect(1, n)
        if _place(rng, g, sh, c) is None: return None
    return g
def tf_oddorient(g):
    obs = _objs(g); v = [o for o in obs if _bw(o) == 1]; hz = [o for o in obs if _bh(o) == 1]
    odd = v if len(v) == 1 and len(hz) > 1 else hz if len(hz) == 1 and len(v) > 1 else None
    if odd is None: return None
    out = copy(g)
    for r, c in odd[0]: out[r][c] = 8
    return out
rule("odd_orientation_bar_recoloured", "All bars lie the same way except one; the bar whose orientation differs from the rest is repainted colour 8.", gi_oddorient, tf_oddorient)


# ---------------------------------------------------------------- 16/17 touching rectangle pairs
def _touch_pairs(rng, key):
    h, w = _size(rng, 8, 18); g = blank(h, w); n = 0
    for _ in range(rng.randint(1, 4)):
        ha, wa, hb, wb = [rng.randint(1, 5) for _ in range(4)]
        if key(ha, wa) == key(hb, wb): continue
        a, b = colours(rng, 2); dr = rng.randint(-(hb - 1), ha - 1)
        cells = [(r, c, a) for r in range(ha) for c in range(wa)] + [(r + dr, wa + c, b) for r in range(hb) for c in range(wb)]
        m = min(r for r, _, _ in cells); cells = [(r - m, c, col) for r, c, col in cells]
        if rng.random() < 0.5: cells = [(c, r, col) for r, c, col in cells]
        if _place_multi(rng, g, cells): n += 1
    return g if n else None
def _touch_tf(g, key):
    out = copy(g); n = 0
    for blob in _blobs(g):
        parts = components([[v if (r, c) in set(blob) else 0 for c, v in enumerate(row)] for r, row in enumerate(g)], lambda v: v != 0)
        if len(parts) != 2: return None
        ka, kb = key(parts[0]), key(parts[1])
        if ka == kb: return None
        win, lose = (parts[0], parts[1]) if ka > kb else (parts[1], parts[0])
        for r, c in lose: out[r][c] = _col(g, win)
        n += 1
    return out if n else None
rule("touching_pairs_smaller_takes_larger_colour", "Two rectangles pressed together form a pair; in each pair the rectangle with fewer cells is repainted in the colour of the larger one.",
     lambda rng: _touch_pairs(rng, lambda h, w: h * w), lambda g: _touch_tf(g, len))
rule("touching_pairs_taller_takes_shorter_colour", "Two rectangles pressed together form a pair; in each pair the rectangle spanning more rows is repainted in the colour of the shorter one.",
     lambda rng: _touch_pairs(rng, lambda h, w: h), lambda g: _touch_tf(g, lambda o: -_bh(o)))


# ---------------------------------------------------------------- 18 colour count difference bar
def gi_coldiff(rng):
    h, w = _size(rng, 5, 14); g = blank(h, w); a, b = colours(rng, 2); mx = min(w - 1, h * w // 3)
    na, nb = rng.sample(range(1, mx + 1), 2)
    sprinkle(rng, g, na, a); sprinkle(rng, g, nb, b)
    return g
def tf_coldiff(g):
    H, W = dims(g); cnt = {k: v for k, v in counts(g).items() if k}
    if len(cnt) != 2: return None
    (a, na), (b, nb) = cnt.items()
    if na == nb: return None
    win, d = (a, na - nb) if na > nb else (b, nb - na)
    return [[win] * d + [0] * (W - d)] if d < W else None
rule("colour_count_difference_bar", "Output one row as wide as the grid: a bar in the more frequent colour, as long as the difference between the two colours' cell counts.", gi_coldiff, tf_coldiff)


# ---------------------------------------------------------------- 19 half with more objects
def gi_halfobjs(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w); d = w // 2
    for r in range(h): g[r][d] = 5
    kl, kr = rng.sample(range(0, 5), 2); cols = [x for x in COLOURS if x not in (1, 2, 5)]
    for _ in range(kl):
        if _place(rng, g, _shape(rng, 1, 5), rng.choice(cols), cols_=(0, d - 2)) is None: return None
    for _ in range(kr):
        if _place(rng, g, _shape(rng, 1, 5), rng.choice(cols), cols_=(d + 2, w)) is None: return None
    return g
def tf_halfobjs(g):
    H, W = dims(g); d = next(c for c in range(W) if all(g[r][c] == 5 for r in range(H)))
    obs = components(g, lambda v: v not in (0, 5), conn8=False)
    left = [o for o in obs if o[0][1] < d]; right = [o for o in obs if o[0][1] > d]
    if len(left) == len(right): return None
    out = copy(g)
    for o in obs:
        for r, c in o: out[r][c] = 1 if (len(left) > len(right)) == (o in left) else 2
    return out
rule("half_with_more_objects_recoloured", "A grey line splits the grid; the objects on the side with more separate objects become 1 and those on the other side become 2.", gi_halfobjs, tf_halfobjs)


# ---------------------------------------------------------------- 20 quadrant with fewest cells cleared
def gi_quadfew(rng):
    h, w = _size(rng, 7, 18); g = blank(h, w); R, C = rng.randint(2, h - 3), rng.randint(2, w - 3)
    for r in range(h): g[r][C] = 5
    for c in range(w): g[R][c] = 5
    ds = rng.sample([0.1, 0.25, 0.4, 0.55, 0.7], 4); i = 0
    for rs in ((0, R), (R + 1, h)):
        for cs in ((0, C), (C + 1, w)):
            for r in range(*rs):
                for c in range(*cs):
                    if rng.random() < ds[i]: g[r][c] = rng.choice([x for x in COLOURS if x != 5])
            i += 1
    return g
def tf_quadfew(g):
    H, W = dims(g); R = next(r for r in range(H) if all(v == 5 for v in g[r])); C = next(c for c in range(W) if all(g[r][c] == 5 for r in range(H)))
    quads = [(rs, cs) for rs in ((0, R), (R + 1, H)) for cs in ((0, C), (C + 1, W))]
    n = [sum(1 for r in range(*rs) for c in range(*cs) if g[r][c]) for rs, cs in quads]
    if n.count(min(n)) != 1 or min(n) == 0: return None
    rs, cs = quads[n.index(min(n))]; out = copy(g)
    for r in range(*rs):
        for c in range(*cs): out[r][c] = 0
    return out
rule("quadrant_with_fewest_cells_cleared", "Grey lines cut the grid into four quadrants; the quadrant holding the fewest coloured cells is emptied.", gi_quadfew, tf_quadfew)


# ---------------------------------------------------------------- 21 longer of two segments per row
def gi_rowsegs(rng):
    h, w = _size(rng, 6, 16); g = blank(h, w); c = rng.choice([x for x in COLOURS if x != 1]); r = rng.randint(0, 1); n = 0
    while r < h:
        if rng.random() < 0.7 and w >= 5:
            la, lb = rng.sample(range(1, max(2, (w - 1) // 2 + 1)), 2) if w >= 5 else (1, 2)
            if la + lb + 1 <= w:
                gap = rng.randint(1, w - la - lb); c0 = rng.randint(0, w - la - lb - gap)
                for x in range(c0, c0 + la): g[r][x] = c
                for x in range(c0 + la + gap, c0 + la + gap + lb): g[r][x] = c
                n += 1
        r += rng.randint(1, 3)
    return g if n else None
def tf_rowsegs(g):
    out = copy(g); n = 0
    for r, row in enumerate(g):
        segs = [o for o in components(g, lambda v: v != 0) if o[0][0] == r]
        if len(segs) != 2: continue
        if len(segs[0]) == len(segs[1]): return None
        for _, c in max(segs, key=len): out[r][c] = 1
        n += 1
    return out if n else None
rule("longer_segment_per_row_recoloured", "Each row holding two horizontal segments has the longer segment repainted colour 1; the shorter keeps its colour.", gi_rowsegs, tf_rowsegs)


# ---------------------------------------------------------------- 22 compare each object to a grey reference object
def gi_refsize(rng):
    h, w = _size(rng, 7, 18); g = blank(h, w); k = rng.randint(2, 6); cols = [x for x in COLOURS if x not in (1, 2, 3, 5)]
    if _place(rng, g, _shape(rng, 2, 7), 5) is None: return None
    for _ in range(k):
        if _place(rng, g, _shape(rng, 1, 9), rng.choice(cols)) is None: return None
    return g
def tf_refsize(g):
    obs = _objs(g); ref = [o for o in obs if _col(g, o) == 5]
    if len(ref) != 1: return None
    n = len(ref[0]); out = copy(g)
    for o in obs:
        if o is ref[0]: continue
        for r, c in o: out[r][c] = 1 if len(o) > n else 2 if len(o) < n else 3
    return out
rule("compare_size_to_grey_reference", "Objects with more cells than the grey object become 1, with fewer become 2, and with exactly as many become 3; the grey object stays.", gi_refsize, tf_refsize)


# ---------------------------------------------------------------- 23 keep objects taller than the grey bar
def gi_refheight(rng):
    h, w = _size(rng, 7, 18); g = blank(h, w); k = rng.randint(2, 6); n = rng.randint(2, 6)
    if _place(rng, g, _rect(n, 1), 5) is None: return None
    for _ in range(k):
        if _place(rng, g, _shape(rng, 2, 9), rng.choice([x for x in COLOURS if x != 5])) is None: return None
    return g
def tf_refheight(g):
    obs = _objs(g); ref = [o for o in obs if _col(g, o) == 5]
    if len(ref) != 1: return None
    n = _bh(ref[0]); out = copy(g); keep = gone = 0
    for o in obs:
        if o is ref[0]: continue
        if _bh(o) > n: keep += 1
        else:
            gone += 1
            for r, c in o: out[r][c] = 0
    return out if keep and gone else None
rule("keep_objects_taller_than_grey_bar", "Only objects spanning more rows than the grey bar are kept; shorter or equal objects are erased and the bar stays.", gi_refheight, tf_refheight)


# ---------------------------------------------------------------- 24 largest minus second-largest bar
def gi_top2(rng):
    h, w = _size(rng, 7, 16); g = blank(h, w); k = rng.randint(2, 5); sizes = [rng.randint(1, 9) for _ in range(k)]
    s = sorted(sizes)
    if s[-1] == s[-2] or s[-1] - s[-2] >= w: return None
    for n in sizes:
        if _place(rng, g, _shape(rng, n, n), rng.choice(COLOURS)) is None: return None
    return g
def tf_top2(g):
    H, W = dims(g); obs = sorted(_objs(g), key=len)
    if len(obs) < 2 or len(obs[-1]) == len(obs[-2]): return None
    d = len(obs[-1]) - len(obs[-2])
    return [[_col(g, obs[-1])] * d + [0] * (W - d)] if d < W else None
rule("largest_minus_second_largest_bar", "Output one row as wide as the grid: a bar in the largest object's colour whose length is how many more cells it has than the second-largest object.", gi_top2, tf_top2)


# ---------------------------------------------------------------- 25/26 bars compared to neighbour / to average
def _full_bars(rng, lo=1):
    h, w = _size(rng, 4, 14); c = rng.choice([x for x in COLOURS if x not in (1, 2)]); g = blank(h, w)
    hs = [rng.randint(lo, h) for _ in range(w)]
    if len(set(hs)) < 2: return None
    for x, k in enumerate(hs):
        for r in range(h - k, h): g[r][x] = c
    return g
def tf_vsright(g):
    H, W = dims(g); hs = [sum(1 for r in range(H) if g[r][c]) for c in range(W)]; out = copy(g)
    for c in range(W - 1):
        if hs[c] != hs[c + 1]:
            for r in range(H - hs[c], H): out[r][c] = 1 if hs[c] > hs[c + 1] else 2
    return out
rule("bars_recoloured_vs_right_neighbour", "Each bar taller than the bar to its right becomes 1 and each bar shorter than its right neighbour becomes 2; equal pairs and the last bar keep their colour.", lambda rng: _full_bars(rng, 1), tf_vsright)
def tf_vsmean(g):
    H, W = dims(g); hs = [sum(1 for r in range(H) if g[r][c]) for c in range(W)]; m = sum(hs) / W; out = copy(g)
    for c in range(W):
        if hs[c] != m:
            for r in range(H - hs[c], H): out[r][c] = 1 if hs[c] > m else 2
    return out
rule("bars_above_average_one_below_two", "Bars taller than the average bar height become 1 and bars shorter than it become 2; bars exactly at the average keep their colour.", lambda rng: _full_bars(rng, 0), tf_vsmean)


# ---------------------------------------------------------------- 27 frame with the most dots takes the dot colour
def gi_framedots(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w); f, d = colours(rng, 2); k = rng.randint(2, 4); ns = rng.sample(range(0, 7), k); n = 0
    for cnt in ns:
        fh, fw = rng.randint(4, min(9, h)), rng.randint(4, min(9, w)); p = _place(rng, g, _ring(fh, fw), f)
        if p is None: continue
        inner = [(r, c) for r in range(p[0] + 1, p[0] + fh - 1) for c in range(p[1] + 1, p[1] + fw - 1)]
        if len(inner) < cnt: return None
        for r, c in rng.sample(inner, cnt): g[r][c] = d
        n += 1
    return g if n >= 2 else None
def tf_framedots(g):
    frames = [o for o in _objs(g) if _is_ring(o)]
    if len(frames) < 2: return None
    f = _col(g, frames[0]); ns = []
    for o in frames:
        r0, c0, r1, c1 = bbox(o); ns.append([(r, c) for r in range(r0 + 1, r1) for c in range(c0 + 1, c1) if g[r][c] not in (0, f)])
    best = max(ns, key=len)
    if sum(1 for x in ns if len(x) == len(best)) != 1 or not best: return None
    out = copy(g); d = g[best[0][0]][best[0][1]]
    for r, c in frames[ns.index(best)]: out[r][c] = d
    return out
rule("frame_with_most_dots_takes_dot_colour", "Of the hollow frames, the one enclosing the most dots is repainted in the dots' colour; the other frames are unchanged.", gi_framedots, tf_framedots)


# ---------------------------------------------------------------- 28 colour with more separate objects erased
def gi_moreobjs(rng):
    h, w = _size(rng, 7, 18); g = blank(h, w); a, b = colours(rng, 2); ka, kb = rng.sample(range(1, 6), 2)
    for col, k in ((a, ka), (b, kb)):
        for _ in range(k):
            if _place(rng, g, _shape(rng, 1, 6), col) is None: return None
    return g
def tf_moreobjs(g):
    obs = _objs(g); cnt = {}
    for o in obs: cnt[_col(g, o)] = cnt.get(_col(g, o), 0) + 1
    if len(cnt) != 2 or len(set(cnt.values())) != 2: return None
    loser = max(cnt, key=cnt.get); out = copy(g)
    for o in obs:
        if _col(g, o) == loser:
            for r, c in o: out[r][c] = 0
    return out
rule("colour_with_more_objects_erased", "Two colours each form several objects; every object of the colour that has more separate objects is erased.", gi_moreobjs, tf_moreobjs)


# ---------------------------------------------------------------- 29 rows won per colour -> two columns
def tf_rowswon(g):
    H, W = dims(g); cols = sorted({v for row in g for v in row if v})
    if len(cols) != 2: return None
    a, b = cols; wa = sum(1 for row in g if row.count(a) > row.count(b)); wb = sum(1 for row in g if row.count(b) > row.count(a))
    if wa + wb == 0 or wa == wb: return None
    return [[a if r >= H - wa else 0, b if r >= H - wb else 0] for r in range(H)]
rule("rows_won_per_colour_two_columns", "Output two columns as tall as the grid: the left bar counts the rows where the first colour has more cells, the right bar the rows where the second colour has more.", _two_colour_rows, tf_rowswon)


# ---------------------------------------------------------------- 30 per column: top half vs bottom half
def gi_colhalves(rng):
    hh, w = rng.randint(2, 8), rng.randint(4, 16)
    if rng.random() < 0.4: hh, w = rng.randint(11, 15), rng.randint(21, 30)
    g = blank(2 * hh, w)
    for c in range(w):
        if rng.random() < 0.15: continue
        for r in range(2 * hh):
            if rng.random() < rng.choice([0.25, 0.5, 0.75]): g[r][c] = rng.choice(COLOURS)
    return g
def tf_colhalves(g):
    H, W = dims(g); hh = H // 2; out = copy(g)
    for c in range(W):
        nt = sum(1 for r in range(hh) if g[r][c]); nb = sum(1 for r in range(hh, H) if g[r][c])
        if nt == nb: continue
        for r in (range(hh, H) if nt > nb else range(hh)): out[r][c] = 0
    return out
rule("column_halves_richer_half_kept", "In each column, the half (top or bottom) with more coloured cells is kept and the other half of that column is emptied; tied columns stay.", gi_colhalves, tf_colhalves)


# ---------------------------------------------------------------- 32 nearer of two objects to the grey marker
def gi_nearer(rng):
    h, w = _size(rng, 7, 18); g = blank(h, w); c = rng.choice([x for x in COLOURS if x not in (5, 8)])
    if _place(rng, g, frozenset({(0, 0)}), 5, margin=2) is None: return None
    for _ in range(2):
        if _place(rng, g, _shape(rng, 2, 8), c, margin=2) is None: return None
    return g
def tf_nearer(g):
    obs = _objs(g); m = [o for o in obs if _col(g, o) == 5]; rest = [o for o in obs if _col(g, o) != 5]
    if len(m) != 1 or len(rest) != 2: return None
    (mr, mc), = m[0]
    ds = [min(abs(r - mr) + abs(c - mc) for r, c in o) for o in rest]
    if ds[0] == ds[1]: return None
    out = copy(g)
    for r, c in rest[ds.index(min(ds))]: out[r][c] = 8
    return out
rule("nearer_object_to_marker_recoloured", "Of the two objects, the one closer to the lone grey cell (by step distance) is repainted colour 8.", gi_nearer, tf_nearer)


# ---------------------------------------------------------------- 33 pairs reordered so the larger is on the left
def gi_pairorder(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w); r = rng.randint(0, 1); n = 0
    while r + 2 <= h:
        bh = rng.randint(2, min(6, h - r)); a, b = _shape(rng, 2, 8), _shape(rng, 2, 8)
        (ha, wa), (hb, wb) = _hw(a), _hw(b)
        if len(a) == len(b) or ha > bh or hb > bh or wa + wb + 1 > w: r += bh + 1; continue
        gap = rng.randint(1, w - wa - wb); c0 = rng.randint(0, w - wa - wb - gap)
        ca, cb = rng.choice(COLOURS), rng.choice(COLOURS); ra, rb = r + rng.randint(0, bh - ha), r + rng.randint(0, bh - hb)
        for y, x in a: g[ra + y][c0 + x] = ca
        for y, x in b: g[rb + y][c0 + wa + gap + x] = cb
        n += 1; r += bh + 1 + rng.randint(0, 2)
    return g if n else None
def tf_pairorder(g):
    H, W = dims(g); out = copy(g); obs = _objs(g); swapped = 0
    rows = [any(g[r]) for r in range(H)]; r = 0
    while r < H:
        if not rows[r]: r += 1; continue
        r1 = r
        while r1 + 1 < H and rows[r1 + 1]: r1 += 1
        band = sorted([o for o in obs if r <= o[0][0] <= r1], key=lambda o: bbox(o)[1])
        if len(band) != 2 or len(band[0]) == len(band[1]): return None
        if len(band[1]) > len(band[0]):
            s, b = band; sr0, sc0, sr1, sc1 = bbox(s); br0, bc0, br1, bc1 = bbox(b)
            for y, x in s: out[y][x] = 0
            for y, x in b: out[y][x] = 0
            for y, x in b: out[y][x - bc0 + sc0] = _col(g, b)
            for y, x in s: out[y][x + bc1 - sc1] = _col(g, s)
            swapped += 1
        r = r1 + 1
    return out if swapped else None
rule("pairs_reordered_larger_left", "Each horizontal band holds two objects; where the one with more cells is on the right, the two trade sides so the larger sits at the left end and the smaller at the right end of the span.", gi_pairorder, tf_pairorder)


# ---------------------------------------------------------------- 34 richer side of a horizontal line shaded
def gi_richside(rng):
    h, w = _size(rng, 6, 16); g = blank(h, w); R = rng.randint(1, h - 2)
    for c in range(w): g[R][c] = 5
    da, db = rng.sample([0.1, 0.25, 0.4, 0.6], 2)
    for r in range(h):
        if r == R: continue
        for c in range(w):
            if rng.random() < (da if r < R else db): g[r][c] = rng.choice([x for x in COLOURS if x not in (5, 8)])
    return g
def tf_richside(g):
    H, W = dims(g); R = next(r for r in range(H) if all(v == 5 for v in g[r]))
    na = sum(1 for r in range(R) for v in g[r] if v); nb = sum(1 for r in range(R + 1, H) for v in g[r] if v)
    if na == nb: return None
    out = copy(g)
    for r in (range(R) if na > nb else range(R + 1, H)):
        for c in range(W):
            if out[r][c] == 0: out[r][c] = 8
    return out
rule("richer_side_of_line_shaded", "A grey line splits the grid top from bottom; on the side holding more coloured cells every empty cell is shaded colour 8.", gi_richside, tf_richside)


# ---------------------------------------------------------------- 35 smaller frame nests inside the larger
def gi_nest(rng):
    h, w = _size(rng, 9, 18); g = blank(h, w); f, s = colours(rng, 2)
    fh, fw = rng.randint(7, min(14, h)), rng.randint(7, min(14, w)); sh, sw = rng.randint(3, fh - 4), rng.randint(3, fw - 4)
    if _place(rng, g, _ring(fh, fw), f) is None or _place(rng, g, _ring(sh, sw), s) is None: return None
    return g
def tf_nest(g):
    obs = _objs(g)
    if len(obs) != 2 or not all(_is_ring(o) for o in obs): return None
    s, b = sorted(obs, key=len); sr0, sc0, sr1, sc1 = bbox(s); br0, bc0, br1, bc1 = bbox(b)
    ih, iw = br1 - br0 - 1, bc1 - bc0 - 1; sh, sw = sr1 - sr0 + 1, sc1 - sc0 + 1
    if sh > ih - 2 or sw > iw - 2: return None
    out = copy(g); col = _col(g, s)
    for r, c in s: out[r][c] = 0
    r0, c0 = br0 + 1 + (ih - sh) // 2, bc0 + 1 + (iw - sw) // 2
    for r, c in s: out[r - sr0 + r0][c - sc0 + c0] = col
    return out
rule("smaller_frame_nests_in_larger", "Of the two hollow frames, the smaller is moved to sit centred inside the larger one, leaving its old place empty.", gi_nest, tf_nest)


# ---------------------------------------------------------------- 36 only the rectangle with the most holes is kept
def gi_mostholes(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w); k = rng.randint(2, 4); ks = rng.sample(range(0, 5), k)
    for n in ks:
        rh, rw = rng.randint(5, 8), rng.randint(5, 8); p = _place(rng, g, _rect(rh, rw), rng.choice(COLOURS))
        if p is None or not _punch(rng, g, p[0], p[1], rh, rw, n): return None
    return g
def tf_mostholes(g):
    obs = _objs(g); hs = [_holes(g, o) for o in obs]
    if len(obs) < 2 or hs.count(max(hs)) != 1: return None
    keep = obs[hs.index(max(hs))]; out = blank(*dims(g))
    for r, c in keep: out[r][c] = g[r][c]
    return out
rule("rectangle_with_most_holes_kept", "Only the rectangle with the most holes is kept, holes and all; every other rectangle is erased.", gi_mostholes, tf_mostholes)


# ---------------------------------------------------------------- 37 longest segment recoloured, shortest erased
def gi_segs(rng):
    h, w = _size(rng, 6, 16); g = blank(h, w); c = rng.choice([x for x in COLOURS if x != 1]); k = rng.randint(3, min(6, (h + 1) // 2, w - 1))
    if k < 3: return None
    ls = rng.sample(range(2, w + 1), k); rs = sorted(rng.sample(range(h), k))
    if any(b - a < 2 for a, b in zip(rs, rs[1:])): return None
    for r, L in zip(rs, ls):
        c0 = rng.randint(0, w - L)
        for x in range(c0, c0 + L): g[r][x] = c
    return g
def tf_segs(g):
    obs = sorted(_objs(g), key=len)
    if len(obs) < 3 or len(obs[0]) == len(obs[1]) or len(obs[-1]) == len(obs[-2]): return None
    out = copy(g)
    for r, c in obs[0]: out[r][c] = 0
    for r, c in obs[-1]: out[r][c] = 1
    return out
rule("longest_segment_one_shortest_erased", "Among the horizontal segments, the longest is repainted colour 1 and the shortest is erased; the others are unchanged.", gi_segs, tf_segs)


# ---------------------------------------------------------------- 38 smaller object replaced by a copy of the larger
def gi_replace(rng):
    h, w = _size(rng, 7, 18); g = blank(h, w); a, b = colours(rng, 2); big, small = _shape(rng, 4, 9), _shape(rng, 1, 8)
    if len(big) <= len(small): return None
    if _place(rng, g, big, a) is None: return None
    bh, bw = _hw(big); sh, sw = _hw(small)
    for _ in range(60):
        r0, c0 = rng.randint(0, h - max(bh, sh)), rng.randint(0, w - max(bw, sw))
        if _free(g, r0, c0, bh, bw, 1) and _free(g, r0, c0, sh, sw, 1):
            for r, c in small: g[r0 + r][c0 + c] = b
            return g
    return None
def tf_replace(g):
    H, W = dims(g); obs = sorted(_objs(g), key=len)
    if len(obs) != 2 or len(obs[0]) == len(obs[1]): return None
    s, b = obs; sr0, sc0, _, _ = bbox(s); br0, bc0, _, _ = bbox(b); out = copy(g); col = _col(g, b); bs = set(b)
    for r, c in s: out[r][c] = 0
    for r, c in b:
        y, x = r - br0 + sr0, c - bc0 + sc0
        if not (0 <= y < H and 0 <= x < W) or (y, x) in bs: return None
        out[y][x] = col
    return out
rule("smaller_replaced_by_copy_of_larger", "The smaller of the two objects is erased and a copy of the larger object, in its own colour, is drawn with its top-left corner where the smaller one's was.", gi_replace, tf_replace)


# ---------------------------------------------------------------- 39 half with more distinct colours kept
def gi_morecolours(rng):
    h, w = _size(rng, 6, 16); g = blank(h, w); d = w // 2
    for r in range(h): g[r][d] = 5
    kl, kr = rng.sample(range(1, 6), 2); pool = [x for x in COLOURS if x != 5]
    for cs, lo, hi in ((rng.sample(pool, kl), 0, d), (rng.sample(pool, kr), d + 1, w)):
        for r in range(h):
            for c in range(lo, hi):
                if rng.random() < 0.4: g[r][c] = rng.choice(cs)
    return g
def tf_morecolours(g):
    H, W = dims(g); d = next(c for c in range(W) if all(g[r][c] == 5 for r in range(H)))
    L = {g[r][c] for r in range(H) for c in range(d) if g[r][c]}; R = {g[r][c] for r in range(H) for c in range(d + 1, W) if g[r][c]}
    if len(L) == len(R): return None
    out = copy(g)
    for r in range(H):
        for c in (range(d + 1, W) if len(L) > len(R) else range(d)): out[r][c] = 0
    return out
rule("half_with_more_distinct_colours_kept", "A grey line splits the grid; the side using more distinct colours is kept and the other side is emptied.", gi_morecolours, tf_morecolours)


# ---------------------------------------------------------------- 40 objects compared with the number of grey dots
def gi_dotcount(rng):
    h, w = _size(rng, 7, 18); g = blank(h, w); k = rng.randint(1, 6); cols = [x for x in COLOURS if x not in (1, 2, 5)]
    for _ in range(rng.randint(2, 5)):
        if _place(rng, g, _shape(rng, 2, 9), rng.choice(cols)) is None: return None
    for _ in range(k):
        if _place(rng, g, frozenset({(0, 0)}), 5) is None: return None
    return g
def tf_dotcount(g):
    obs = _objs(g); k = sum(1 for o in obs if _col(g, o) == 5)
    if not k: return None
    out = copy(g)
    for o in obs:
        if _col(g, o) == 5 or len(o) == k: continue
        for r, c in o: out[r][c] = 1 if len(o) > k else 2
    return out
rule("objects_compared_to_grey_dot_count", "Count the grey dots; every object with more cells than that count becomes 1, with fewer becomes 2, and with exactly that many keeps its colour.", gi_dotcount, tf_dotcount)
