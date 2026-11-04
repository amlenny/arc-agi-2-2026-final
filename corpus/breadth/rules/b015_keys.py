# b015_keys.py -- in-grid instructions: one part of the grid encodes what to do to the rest. A key band sits above
# a grey separator row (or along one edge) and the field below is transformed by what the key says.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

SEP = 5                               # separator / dot colour; fields never use it
FC = [1, 2, 3, 4, 6, 7, 8, 9]         # field colours
DIRS = {0: (-1, 0), 1: (0, 1), 2: (1, 0), 3: (0, -1)}   # up, right, down, left


def _fsz(rng, extra, lo=6, hi=20):
    """field size leaving `extra` rows for the key band and separator; ~35% of draws land in the 21-30 band."""
    cap = 30 - extra
    if rng.random() < 0.35 and cap >= 21:
        return rng.randint(21, cap), rng.randint(21, 30)
    return rng.randint(lo, min(hi, cap)), rng.randint(lo, hi)


def _noise(rng, h, w, cols, density=0.3):
    return [[rng.choice(cols) if rng.random() < density else 0 for _ in range(w)] for _ in range(h)]


def _scene(rng, h, w, k_lo, k_hi, n_lo, n_hi, cols, margin=1):
    g = blank(h, w); k = rng.randint(k_lo, k_hi)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    if place_shapes(rng, g, shapes, [rng.choice(cols) for _ in range(k)], margin=margin) is None:
        return None
    return g


def _stack(band, field):
    """key band on top, one grey separator row, field below; the narrower part is padded right with 0."""
    w = max(len(field[0]), max(len(r) for r in band))
    pad = lambda g: [row + [0] * (w - len(row)) for row in g]
    return pad(band) + [[SEP] * w] + pad(field)


def _split(g):
    """(band, field) around the first all-grey row."""
    for i, row in enumerate(g):
        if all(v == SEP for v in row):
            return g[:i], g[i + 1:]
    return None, None


def _tail(g, band, field):
    return band + [[SEP] * len(g[0])] + field


def _blobs(g, bg=0, conn8=True):
    """connected components of non-background cells regardless of colour."""
    H, W = dims(g); seen, out = set(), []
    nb = [(-1, 0), (1, 0), (0, -1), (0, 1)] + ([(-1, -1), (-1, 1), (1, -1), (1, 1)] if conn8 else [])
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or g[r][c] == bg:
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


def _nonempty(g):
    return any(v for row in g for v in row)


def _arrow_band(rng, d, L, col):
    """chevron arrow: a shaft of L cells then a tip, with wings beside the cell before the tip. d: 0 up 1 right 2 down 3 left."""
    if d in (1, 3):
        b = blank(3, L + 1)
        for c in range(L + 1): b[1][c] = col
        wc = L - 1 if d == 1 else 1
        b[0][wc] = b[2][wc] = col
    else:
        b = blank(L + 1, 3)
        for r in range(L + 1): b[r][1] = col
        wr = L - 1 if d == 2 else 1
        b[wr][0] = b[wr][2] = col
    return b


def _arrow_dir(band):
    """(direction, length) of the arrow drawn in the band."""
    pts = cells(band, lambda v: v != 0); r0, c0, r1, c1 = bbox(pts)
    if c1 - c0 > r1 - r0:
        wing = next(c for c in range(c0, c1 + 1) if sum(1 for r in range(r0, r1 + 1) if band[r][c]) == 3)
        return (1 if wing == c1 - 1 else 3), c1 - c0 + 1
    wing = next(r for r in range(r0, r1 + 1) if sum(1 for c in range(c0, c1 + 1) if band[r][c]) == 3)
    return (2 if wing == r1 - 1 else 0), r1 - r0 + 1


def _gravity(g, d):
    k = {2: 0, 1: 1, 0: 2, 3: 3}[d]
    h = g
    for _ in range(k): h = rot90(h)
    H, W = dims(h); out = blank(H, W)
    for c in range(W):
        col = [h[r][c] for r in range(H) if h[r][c]]
        for i, v in enumerate(reversed(col)): out[H - 1 - i][c] = v
    for _ in range((4 - k) % 4): out = rot90(out)
    return out


# 1 example pair (shape -> flipped shape) says how to flip every field object.
def gi_flip(rng):
    A = rng.choice(FC)
    for _ in range(50):
        pat = [[A if rng.random() < 0.5 else 0 for _ in range(3)] for _ in range(3)]
        outs = [flip_h(pat), flip_v(pat), flip_h(flip_v(pat))]
        if pat not in outs and len({str(o) for o in outs}) == 3: break
    else:
        return None
    aft = rng.choice(outs); band = [pat[r] + [0] + aft[r] for r in range(3)]
    h, w = _fsz(rng, 4, 7, 20); w = max(w, 7)
    f = _scene(rng, h, w, 2, 6, 3, 8, FC)
    if f is None: return None
    for o in objects(f, 0):
        r0, c0, r1, c1 = bbox(o)
        if sum(1 for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if f[r][c]) != len(o): return None
    return _stack(band, f)
def tf_flip(g):
    band, f = _split(g); bef = [row[0:3] for row in band]; aft = [row[4:7] for row in band]
    ops = [flip_h, flip_v, lambda x: flip_h(flip_v(x))]
    op = next((o for o in ops if o(bef) == aft), None)
    if op is None: return None
    out = copy(f)
    for o in objects(f, 0):
        r0, c0, r1, c1 = bbox(o); paste(out, op(crop(f, r0, c0, r1, c1)), r0, c0)
    return _tail(g, band, out)
rule("example_pair_sets_object_flip", "The corner shows a pattern and its flipped copy; every object below the separator is flipped the same way inside its own box.", gi_flip, tf_flip)


# 2 key cell names the colour to delete.
def gi_del(rng):
    cols = colours(rng, rng.randint(3, 4), (0, 5)); c = cols[0]
    h, w = _fsz(rng, 2); f = _noise(rng, h, w, cols, 0.35)
    present = {v for row in f for v in row}
    return _stack([[c]], f) if all(x in present for x in cols) else None
def tf_del(g):
    band, f = _split(g); c = band[0][0]
    return [[0 if v == c else v for v in row] for row in f]
rule("key_cell_deletes_colour", "The single key cell above the separator names a colour; output the field below with every cell of that colour erased.", gi_del, tf_del)


# 3 a 3x3 key says which of nine positions get a copy of the motif.
def gi_tile3(rng):
    K = rng.choice(FC); key = [[K if rng.random() < 0.5 else 0 for _ in range(3)] for _ in range(3)]
    n = sum(1 for row in key for v in row if v)
    if n < 2 or n > 7: return None
    mh, mw = rng.randint(3, 9), rng.randint(3, 9)
    motif = _noise(rng, mh, mw, FC, 0.6)
    return _stack(key, motif) if len({v for row in motif for v in row}) >= 3 else None
def tf_tile3(g):
    band, f = _split(g); mh, mw = dims(f); out = blank(3 * mh, 3 * mw)
    for r in range(3):
        for c in range(3):
            if band[r][c]: paste(out, f, r * mh, c * mw)
    return out
rule("key_3x3_tiles_motif", "The 3 by 3 key above the separator is a tiling plan: the output is three motifs wide and tall, with the motif copied wherever the key has a coloured cell.", gi_tile3, tf_tile3)


# 4 digit cell says how many times to repeat the shape.
def gi_rep(rng):
    n = rng.randint(1, 4); c = rng.choice([x for x in FC if x != n])
    h, w = _fsz(rng, 2); f = blank(h, w); sh = random_shape(rng, rng.randint(3, 8))
    if max(cc for _, cc in sh) + 1 > 5: return None
    if place_shapes(rng, f, [sh], [c]) is None: return None
    return _stack([[n]], f)
def tf_rep(g):
    band, f = _split(g); n = band[0][0]; o = objects(f, 0)[0]
    sub = crop(f, *bbox(o)); H, W = dims(sub); out = blank(H, n * W + n - 1)
    for i in range(n): paste(out, sub, 0, i * (W + 1))
    return out
rule("digit_cell_repeats_shape", "The key cell's value n says how many times to repeat the shape: output the shape n times side by side with one empty column between copies.", gi_rep, tf_rep)


# 5 arrow glyph says which way, and how far, to shift the field.
def gi_ashift(rng):
    d, L, col = rng.randrange(4), rng.randint(3, 5), rng.choice(FC); band = _arrow_band(rng, d, L, col)
    h, w = _fsz(rng, len(band) + 1, 9, 20); w = max(w, len(band[0]))
    f = _noise(rng, h, w, colours(rng, rng.randint(2, 4), (0, 5)), 0.3)
    return _stack(band, f)
def tf_ashift(g):
    band, f = _split(g); d, k = _arrow_dir(band); dy, dx = DIRS[d]; H, W = dims(f); out = blank(H, W)
    for r in range(H):
        for c in range(W):
            if f[r][c] and 0 <= r + dy * k < H and 0 <= c + dx * k < W: out[r + dy * k][c + dx * k] = f[r][c]
    return out
rule("arrow_glyph_shifts_field", "The arrow above the separator points a direction; output the field shifted that way by the arrow's length, cells pushed off the edge vanishing.", gi_ashift, tf_ashift)


# 6 colour pair plus a grey count: A becomes B only for objects larger than k cells.
def gi_pairsize(rng):
    A, B = colours(rng, 2, (0, 5)); k = rng.randint(1, 4)
    h, w = _fsz(rng, 2, 8, 20); w = max(w, k + 3)
    f = _scene(rng, h, w, 3, 7, 1, 8, [A, A, A] + [x for x in FC if x not in (A, B)])
    if f is None: return None
    sz = [len(o) for o in objects(f, 0) if f[o[0][0]][o[0][1]] == A]
    if not (any(s > k for s in sz) and any(s <= k for s in sz)): return None
    return _stack([[A, B] + [SEP] * k], f)
def tf_pairsize(g):
    band, f = _split(g); A, B = band[0][0], band[0][1]; k = sum(1 for v in band[0] if v == SEP); out = copy(f)
    for o in objects(f, 0):
        if f[o[0][0]][o[0][1]] == A and len(o) > k:
            for r, c in o: out[r][c] = B
    return _tail(g, band, out)
rule("key_pair_recolours_objects_above_size", "The key row shows colour A, colour B and k grey cells; every object of colour A with more than k cells becomes colour B, smaller ones stay.", gi_pairsize, tf_pairsize)


# 7 a grey counter bar down the left edge says how many rows to keep from the top.
def gi_barrows(rng):
    h, w = _fsz(rng, 0, 6, 20); w = min(w, 29)
    f = _noise(rng, h, w, colours(rng, rng.randint(2, 4), (0, 5)), 0.4); n = rng.randint(1, h - 1)
    return [[SEP if r < n else 0] + f[r] for r in range(h)]
def tf_barrows(g):
    n = sum(1 for row in g if row[0] == SEP)
    return [row[1:] for row in g[:n]]
rule("counter_bar_keeps_top_rows", "The grey bar in the left column has length n; output the first n rows of the field to its right.", gi_barrows, tf_barrows)


# 8 a marker in a 2x2 selector picks which quadrant of the field to output.
def gi_sel(rng):
    key = blank(2, 2); key[rng.randrange(2)][rng.randrange(2)] = 9
    h, w = _fsz(rng, 3, 6, 20); h -= h % 2; w -= w % 2
    return _stack(key, _noise(rng, h, w, colours(rng, rng.randint(2, 4), (0, 5, 9)), 0.4))
def tf_sel(g):
    band, f = _split(g); H, W = dims(f)
    qr, qc = next((r, c) for r in range(2) for c in range(2) if band[r][c])
    return crop(f, qr * H // 2, qc * W // 2, (qr + 1) * H // 2 - 1, (qc + 1) * W // 2 - 1)
rule("selector_marker_picks_quadrant", "The 2 by 2 selector above the separator holds one marker; output the quarter of the field in the matching position.", gi_sel, tf_sel)


# 9 grey dots down the left edge mark the rows to delete.
def gi_dotsdel(rng):
    h, w = _fsz(rng, 0, 6, 20); w = min(w, 29)
    f = _noise(rng, h, w, colours(rng, rng.randint(2, 4), (0, 5)), 0.4)
    marked = set(rng.sample(range(h), rng.randint(1, h - 2)))
    return [[SEP if r in marked else 0] + f[r] for r in range(h)]
def tf_dotsdel(g):
    return [row[1:] for row in g if row[0] != SEP]
rule("left_dots_delete_marked_rows", "Grey dots in the left column mark rows; output the field with the marked rows removed and the rest closed up.", gi_dotsdel, tf_dotsdel)


# 10 the key shape is punched out of every solid rectangle.
def gi_punch(rng):
    K = rng.choice(FC); sh = random_shape(rng, rng.randint(2, 5))
    sh_h, sh_w = max(r for r, _ in sh) + 1, max(c for _, c in sh) + 1
    if sh_h > 3 or sh_w > 3: return None
    band = blank(3, 3)
    for r, c in sh: band[r][c] = K
    h, w = _fsz(rng, 4, 8, 20); f = blank(h, w); n = 0; want = rng.randint(1, 4)
    for _ in range(60):
        if n >= want: break
        rh, rw = rng.randint(sh_h + 2, sh_h + 5), rng.randint(sh_w + 2, sh_w + 5)
        if rh > h or rw > w: continue
        r0, c0 = rng.randint(0, h - rh), rng.randint(0, w - rw)
        if all(f[r][c] == 0 for r in range(max(0, r0 - 1), min(h, r0 + rh + 1)) for c in range(max(0, c0 - 1), min(w, c0 + rw + 1))):
            rect(f, r0, c0, r0 + rh - 1, c0 + rw - 1, rng.choice([x for x in FC if x != K])); n += 1
    return _stack(band, f) if n else None
def tf_punch(g):
    band, f = _split(g); sh = cells([row[:3] for row in band[:3]], lambda v: v != 0); out = copy(f)
    for o in objects(f, 0):
        r0, c0, r1, c1 = bbox(o)
        for r, c in sh: out[r0 + 1 + r][c0 + 1 + c] = 0
    return _tail(g, band, out)
rule("key_shape_punched_from_rectangles", "The small shape above the separator is a punch: it is cut out of every solid rectangle, one cell in from the rectangle's top-left corner.", gi_punch, tf_punch)


# 11 a mini-map with one marked cell says where to put the motif at full scale.
def gi_mmplace(rng):
    hm, wm = rng.randint(2, 5), rng.randint(2, 5)
    mh, mw = rng.randint(2, min(6, 30 // hm)), rng.randint(wm, min(6, 30 // wm))
    B, M = colours(rng, 2, (0, 5)); mp = blank(hm, wm, B); mp[rng.randrange(hm)][rng.randrange(wm)] = M
    motif = _noise(rng, mh, mw, FC, 0.7)
    return _stack(mp, motif) if len({v for row in motif for v in row}) >= 2 else None
def tf_mmplace(g):
    band, f = _split(g); mp = crop(band, *bbox(cells(band, lambda v: v != 0)))
    bg = bg_colour(mp); hm, wm = dims(mp); mh, mw = dims(f)
    mr, mc = next((r, c) for r in range(hm) for c in range(wm) if mp[r][c] != bg)
    out = blank(hm * mh, wm * mw); paste(out, f, mr * mh, mc * mw)
    return out
rule("minimap_places_motif_full_scale", "The small map above the separator has one odd cell; the output is the map blown up to motif-sized blocks, with the motif below the separator placed in the odd cell's block.", gi_mmplace, tf_mmplace)


# 12 legend bars: a bar of length n in colour c means objects of n cells take colour c; unlisted sizes vanish.
def gi_legbars(rng):
    k = rng.randint(2, 4); lens = rng.sample(range(1, 7), k); cs = colours(rng, k, (0, 5, 8))
    band = [[c] * n for c, n in zip(cs, lens)]
    h, w = _fsz(rng, k + 1, 8, 20); f = _scene(rng, h, w, 3, 8, 1, 7, [8])
    if f is None: return None
    sz = [len(o) for o in objects(f, 0)]
    return _stack(band, f) if any(s in lens for s in sz) and any(s not in lens for s in sz) else None
def tf_legbars(g):
    band, f = _split(g); m = {}
    for row in band:
        n = sum(1 for v in row if v)
        if n: m[n] = next(v for v in row if v)
    out = blank(*dims(f))
    for o in objects(f, 0):
        if len(o) in m:
            for r, c in o: out[r][c] = m[len(o)]
    return _tail(g, band, out)
rule("legend_bars_recolour_by_size_delete_rest", "Each legend bar above the separator pairs a length with a colour; grey objects with exactly that many cells take that colour and objects of unlisted sizes are erased.", gi_legbars, tf_legbars)


# 13 a palette row fixes the column order of a cell-count histogram.
def gi_palhist(rng):
    k = rng.randint(2, 5); pal = colours(rng, k, (0, 5)); h, w = _fsz(rng, 2, 5, 14)
    f = _noise(rng, h, w, pal, min(0.3, 20 * k / (h * w))); cnt = counts(f)
    return _stack([pal], f) if all(0 < cnt.get(c, 0) <= 30 for c in pal) else None
def tf_palhist(g):
    band, f = _split(g); pal = [v for v in band[0] if v]; cnt = counts(f); H = max(cnt.get(c, 0) for c in pal)
    out = blank(H, len(pal))
    for i, c in enumerate(pal):
        for r in range(H - cnt.get(c, 0), H): out[r][i] = c
    return out
rule("palette_orders_histogram_columns", "The palette row above the separator gives the column order: output one bottom-aligned bar per palette colour, in that order, as tall as the colour's cell count in the field.", gi_palhist, tf_palhist)


# 14 sample cell gives the colour to flood the background with.
def gi_flood(rng):
    c = rng.choice(FC); h, w = _fsz(rng, 2)
    f = _scene(rng, h, w, 2, 6, 2, 8, [x for x in FC if x != c])
    return _stack([[c]], f) if f else None
def tf_flood(g):
    band, f = _split(g); c = band[0][0]
    return [[c if v == 0 else v for v in row] for row in f]
rule("sample_cell_floods_background", "The sample cell above the separator gives a colour; output the field with every empty cell painted that colour.", gi_flood, tf_flood)


# 15 which corner holds the grey marker selects the rotation.
def gi_crot(rng):
    h, w = _fsz(rng, 0); g = _noise(rng, h, w, colours(rng, rng.randint(2, 4), (0, 5)), 0.3)
    r, c = [(0, 0), (0, w - 1), (h - 1, w - 1), (h - 1, 0)][rng.randrange(4)]; g[r][c] = SEP
    return g
def tf_crot(g):
    H, W = dims(g); out = copy(g)
    ops = [rot90, lambda x: rot90(rot90(x)), lambda x: rot90(rot90(rot90(x))), flip_h]
    for k, (r, c) in enumerate([(0, 0), (0, W - 1), (H - 1, W - 1), (H - 1, 0)]):
        if g[r][c] == SEP:
            out[r][c] = 0
            return ops[k](out)
    return None
rule("corner_marker_picks_rotation", "A grey marker sits in one corner and is removed; top-left turns the grid a quarter clockwise, top-right a half turn, bottom-right three quarters, bottom-left mirrors it left-right.", gi_crot, tf_crot)


# 16 digit cell says the scale factor.
def gi_scale(rng):
    n = rng.randint(2, 4); h, w = rng.randint(3, 30 // n), rng.randint(3, 30 // n)
    return _stack([[n]], _noise(rng, h, w, colours(rng, rng.randint(2, 4), (0, 5)), 0.4))
def tf_scale(g):
    band, f = _split(g); n = band[0][0]
    return [[v for v in row for _ in range(n)] for row in f for _ in range(n)]
rule("digit_key_scales_field", "The key cell's value n is a scale factor: output the field with every cell blown up to an n by n block.", gi_scale, tf_scale)


# 17 arrow glyph sets the direction of gravity.
def gi_agrav(rng):
    d, L, col = rng.randrange(4), rng.randint(3, 5), rng.choice(FC); band = _arrow_band(rng, d, L, col)
    h, w = _fsz(rng, len(band) + 1, 7, 20); w = max(w, len(band[0]))
    return _stack(band, _noise(rng, h, w, colours(rng, rng.randint(2, 4), (0, 5)), 0.25))
def tf_agrav(g):
    band, f = _split(g); d, _ = _arrow_dir(band)
    return _tail(g, band, _gravity(f, d))
rule("arrow_key_sets_gravity", "The arrow above the separator says which way is down: every field cell falls in that direction until it rests on the edge or another cell.", gi_agrav, tf_agrav)


# 18 counter bar length = number of quarter turns.
def gi_barrot(rng):
    n = rng.randint(1, 3); h, w = _fsz(rng, 2, 6, 20); w = max(w, n + 1)
    return _stack([[8] * n], _noise(rng, h, w, colours(rng, rng.randint(2, 4), (0, 5, 8)), 0.35))
def tf_barrot(g):
    band, f = _split(g); n = sum(1 for v in band[0] if v)
    for _ in range(n): f = rot90(f)
    return f
rule("counter_bar_rotates_field", "The bar above the separator has n cells; output the field rotated n quarter turns clockwise.", gi_barrot, tf_barrot)


# 19 key cell names the only colour to keep.
def gi_keep(rng):
    cols = colours(rng, rng.randint(3, 4), (0, 5)); c = cols[0]; h, w = _fsz(rng, 2)
    f = _noise(rng, h, w, cols, 0.35)
    return _stack([[c]], f) if any(v == c for row in f for v in row) else None
def tf_keep(g):
    band, f = _split(g); c = band[0][0]
    return [[v if v == c else 0 for v in row] for row in f]
rule("key_cell_keeps_only_colour", "The key cell above the separator names a colour; output the field with every cell of any other colour erased.", gi_keep, tf_keep)


# 20 a 2x2 key says which quadrants to blank.
def gi_blankq(rng):
    key = [[8 if rng.random() < 0.5 else 0 for _ in range(2)] for _ in range(2)]
    n = sum(1 for row in key for v in row if v)
    if n in (0, 4): return None
    h, w = _fsz(rng, 3, 6, 20); h -= h % 2; w -= w % 2
    return _stack(key, _noise(rng, h, w, colours(rng, rng.randint(2, 4), (0, 5, 8)), 0.4))
def tf_blankq(g):
    band, f = _split(g); H, W = dims(f); out = copy(f)
    for qr in range(2):
        for qc in range(2):
            if band[qr][qc]: rect(out, qr * H // 2, qc * W // 2, (qr + 1) * H // 2 - 1, (qc + 1) * W // 2 - 1, 0)
    return _tail(g, band, out)
rule("key_2x2_blanks_quadrants", "The 2 by 2 key above the separator marks quarters; the matching quarters of the field are wiped empty and the others are kept.", gi_blankq, tf_blankq)


# 21 key colour fills the empty cells of every object's bounding box.
def gi_bbfill(rng):
    c = rng.choice(FC); h, w = _fsz(rng, 2, 8, 20)
    f = _scene(rng, h, w, 2, 6, 4, 9, [x for x in FC if x != c])
    if f is None: return None
    for o in objects(f, 0):
        r0, c0, r1, c1 = bbox(o)
        if sum(1 for r in range(r0, r1 + 1) for cc in range(c0, c1 + 1) if f[r][cc]) != len(o): return None
    return _stack([[c]], f)
def tf_bbfill(g):
    band, f = _split(g); c = band[0][0]; out = copy(f)
    for o in objects(f, 0):
        r0, c0, r1, c1 = bbox(o)
        for r in range(r0, r1 + 1):
            for cc in range(c0, c1 + 1):
                if out[r][cc] == 0: out[r][cc] = c
    return _tail(g, band, out)
rule("key_colour_fills_object_bboxes", "The key cell gives a colour; the empty cells inside each object's bounding box are painted that colour.", gi_bbfill, tf_bbfill)


# 22 grey dots along the bottom edge select the columns to keep.
def gi_botdots(rng):
    h, w = _fsz(rng, 1, 6, 20)
    f = _noise(rng, h, w, colours(rng, rng.randint(2, 4), (0, 5)), 0.4)
    marked = set(rng.sample(range(w), rng.randint(1, w - 1)))
    return f + [[SEP if c in marked else 0 for c in range(w)]]
def tf_botdots(g):
    keep = [c for c, v in enumerate(g[-1]) if v == SEP]
    return [[row[c] for c in keep] for row in g[:-1]]
rule("bottom_dots_select_columns", "Grey dots along the bottom row mark columns; output only the marked columns of the field above, closed up in order.", gi_botdots, tf_botdots)


# 23 key colour is painted onto the largest object.
def gi_klarge(rng):
    c = rng.choice(FC); h, w = _fsz(rng, 2, 8, 20)
    f = _scene(rng, h, w, 2, 6, 2, 9, [x for x in FC if x != c])
    if f is None: return None
    sz = sorted(len(o) for o in objects(f, 0))
    return _stack([[c]], f) if sz[-1] != sz[-2] else None
def tf_klarge(g):
    band, f = _split(g); c = band[0][0]; out = copy(f)
    for r, cc in max(objects(f, 0), key=len): out[r][cc] = c
    return _tail(g, band, out)
rule("key_cell_recolours_largest_object", "The key cell above the separator gives a colour; the largest object in the field is repainted with it.", gi_klarge, tf_klarge)


# 24 digit cell says how many cells each object extends to the right.
def gi_extr(rng):
    n = rng.randint(1, 3); h, w = _fsz(rng, 2, 8, 20)
    f = _scene(rng, h, w, 2, 5, 2, 7, [x for x in FC if x != n], margin=n + 1)
    return _stack([[n]], f) if f else None
def tf_extr(g):
    band, f = _split(g); n = band[0][0]; H, W = dims(f); out = copy(f)
    for r in range(H):
        for c in range(W):
            if f[r][c]:
                for k in range(1, n + 1):
                    if c + k < W and f[r][c + k] == 0: out[r][c + k] = f[r][c]
    return _tail(g, band, out)
rule("digit_key_extends_objects_right", "The key cell's value n says how far: every coloured cell smears n cells to the right in its own colour.", gi_extr, tf_extr)


# 25 objects of the key colour float up to the top; others stay.
def gi_rise(rng):
    c = rng.choice(FC); h, w = _fsz(rng, 2, 8, 20)
    f = _scene(rng, h, w, 3, 7, 1, 6, [c, c] + [x for x in FC if x != c])
    if f is None: return None
    if not any(f[o[0][0]][o[0][1]] == c and min(r for r, _ in o) > 0 for o in objects(f, 0)): return None
    return _stack([[c]], f)
def tf_rise(g):
    band, f = _split(g); c = band[0][0]; out = copy(f)
    for o in sorted(objects(f, 0), key=lambda o: min(r for r, _ in o)):
        if f[o[0][0]][o[0][1]] != c: continue
        for r, cc in o: out[r][cc] = 0
        d = 0
        while all(r - d - 1 >= 0 and out[r - d - 1][cc] == 0 for r, cc in o): d += 1
        for r, cc in o: out[r - d][cc] = c
    return _tail(g, band, out)
rule("key_colour_objects_rise", "The key cell names a colour; every object of that colour rises straight up as a rigid piece until it meets the separator or another object, other objects stay put.", gi_rise, tf_rise)


# 26 a two-colour mini-map says which blocks of the field to keep.
def gi_mmask(rng):
    hm, wm = rng.randint(2, 5), rng.randint(2, 5)
    S = rng.randint(2, min(8, (29 - hm) // hm, 30 // wm))
    mp = [[8 if rng.random() < 0.5 else 1 for _ in range(wm)] for _ in range(hm)]
    if len({v for row in mp for v in row}) < 2: return None
    return _stack(mp, _noise(rng, hm * S, wm * S, colours(rng, rng.randint(2, 4), (0, 5)), 0.4))
def tf_mmask(g):
    band, f = _split(g); r0, c0, r1, c1 = bbox(cells(band, lambda v: v != 0))
    hm, wm = r1 - r0 + 1, c1 - c0 + 1; S = len(f) // hm; out = copy(f)
    for r in range(hm):
        for c in range(wm):
            if band[r0 + r][c0 + c] != 8: rect(out, r * S, c * S, (r + 1) * S - 1, (c + 1) * S - 1, 0)
    return out
rule("minimap_masks_field_blocks", "The mini-map above the separator is grey where blocks are kept and blue where they go; output the field with each block that maps to a blue cell wiped empty.", gi_mmask, tf_mmask)


# 27 a plus or an X glyph says whether markers fire straight or diagonal rays.
def gi_plusx(rng):
    plus = rng.random() < 0.5; key = blank(3, 3)
    for i in range(3):
        if plus: key[1][i] = key[i][1] = 8
        else: key[i][i] = key[i][2 - i] = 8
    h, w = _fsz(rng, 4, 7, 20); f = blank(h, w); k = rng.randint(1, 4)
    if place_shapes(rng, f, [[(0, 0)]] * k, [rng.choice([x for x in FC if x != 8]) for _ in range(k)], margin=2) is None: return None
    return _stack(key, f)
def tf_plusx(g):
    band, f = _split(g)
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)] if band[0][1] else [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    H, W = dims(f); out = copy(f)
    for r, c in cells(f, lambda v: v != 0):
        for dy, dx in dirs:
            y, x = r + dy, c + dx
            while 0 <= y < H and 0 <= x < W:
                if f[y][x] == 0: out[y][x] = f[r][c]
                y += dy; x += dx
    return _tail(g, band, out)
rule("key_glyph_plus_or_x_rays", "The glyph above the separator is a plus or an X; every marker in the field shoots rays to the edges in its colour, straight for a plus and diagonal for an X.", gi_plusx, tf_plusx)


# 28 key colour is the ink for joining same-colour pairs.
def gi_conn(rng):
    c = rng.choice(FC); h, w = _fsz(rng, 2, 7, 20); f = blank(h, w); used = set()
    for col in colours(rng, rng.randint(1, 4), (0, 5, c)):
        for _ in range(30):
            if rng.random() < 0.5:
                r = rng.randrange(h); a, b = sorted(rng.sample(range(w), 2)); seg = {(r, x) for x in range(a, b + 1)}
            else:
                cc = rng.randrange(w); a, b = sorted(rng.sample(range(h), 2)); seg = {(y, cc) for y in range(a, b + 1)}
            if len(seg) >= 3 and not (seg & used):
                used |= seg; e = sorted(seg); f[e[0][0]][e[0][1]] = col; f[e[-1][0]][e[-1][1]] = col; break
    return _stack([[c]], f) if _nonempty(f) else None
def tf_conn(g):
    band, f = _split(g); c = band[0][0]; out = copy(f)
    for col in {v for row in f for v in row if v}:
        pts = cells(f, lambda v: v == col)
        if len(pts) != 2: continue
        (r1, c1), (r2, c2) = pts
        if r1 == r2:
            for x in range(c1 + 1, c2): out[r1][x] = c
        elif c1 == c2:
            for y in range(r1 + 1, r2): out[y][c1] = c
    return _tail(g, band, out)
rule("key_colour_draws_connections", "Pairs of same-coloured cells on one row or column are joined by a line drawn in the key colour shown above the separator, not in their own colour.", gi_conn, tf_conn)


# 29 palette row gives the left-to-right order for lining up the objects.
def gi_pallin(rng):
    k = rng.randint(2, 5); pal = colours(rng, k, (0, 5)); h, w = _fsz(rng, 2, 8, 20); f = blank(h, w)
    if place_shapes(rng, f, [random_shape(rng, rng.randint(2, 5)) for _ in range(k)], pal) is None: return None
    return _stack([pal], f) if len(objects(f, 0)) == k else None
def tf_pallin(g):
    band, f = _split(g); pal = [v for v in band[0] if v]
    subs = [crop(f, *bbox(cells(f, lambda v, c=c: v == c))) for c in pal]
    H = max(len(s) for s in subs); W = sum(len(s[0]) for s in subs) + len(subs) - 1
    if W > 30: return None
    out = blank(H, W); x = 0
    for s in subs:
        paste(out, s, 0, x); x += len(s[0]) + 1
    return out
rule("palette_orders_object_lineup", "The palette row above the separator gives an order; output the objects cut out and lined up top-aligned left to right in that colour order, one empty column apart.", gi_pallin, tf_pallin)


# 30 counter bar length = ring radius around every marker.
def gi_ring(rng):
    n = rng.randint(1, 3); h, w = _fsz(rng, 2, 8, 20); f = blank(h, w); k = rng.randint(1, 4)
    if place_shapes(rng, f, [[(0, 0)]] * k, [rng.choice([x for x in FC if x != 8]) for _ in range(k)], margin=2 * n) is None: return None
    return _stack([[8] * n], f)
def tf_ring(g):
    band, f = _split(g); n = sum(1 for v in band[0] if v); H, W = dims(f); out = copy(f)
    for r, c in cells(f, lambda v: v != 0):
        for y in range(r - n, r + n + 1):
            for x in range(c - n, c + n + 1):
                if max(abs(y - r), abs(x - c)) == n and 0 <= y < H and 0 <= x < W: out[y][x] = f[r][c]
    return _tail(g, band, out)
rule("counter_bar_sets_ring_radius", "The bar above the separator has n cells; every marker in the field is surrounded by a square ring of its colour at distance n.", gi_ring, tf_ring)


# 31 digit cell says keep every n-th row.
def gi_nth(rng):
    n = rng.randint(2, 4); h, w = _fsz(rng, 2, 8, 20)
    return _stack([[n]], _noise(rng, h, w, colours(rng, rng.randint(2, 4), (0, 5)), 0.4))
def tf_nth(g):
    band, f = _split(g); n = band[0][0]
    return f[::n]
rule("digit_key_keeps_every_nth_row", "The key cell's value n says which rows survive: output the first field row and every n-th row after it.", gi_nth, tf_nth)


# 32 example pair: a lone cell becomes a 3x3 pattern; apply to every field cell of that colour.
def gi_c2p(rng):
    A = rng.choice(FC); bef = blank(3, 3); bef[1][1] = A
    for _ in range(30):
        P = [[rng.choice(FC) if rng.random() < 0.45 else 0 for _ in range(3)] for _ in range(3)]
        if 3 <= sum(1 for row in P for v in row if v) <= 6 and P != bef: break
    else:
        return None
    band = [bef[r] + [0] + P[r] for r in range(3)]
    h, w = _fsz(rng, 4, 7, 20); w = max(w, 7); f = blank(h, w); k = rng.randint(2, 6)
    cs = [A] * (k // 2 + 1) + [rng.choice([x for x in FC if x != A]) for _ in range(k - k // 2 - 1)]
    if place_shapes(rng, f, [[(0, 0)]] * k, cs, margin=2) is None: return None
    return _stack(band, f)
def tf_c2p(g):
    band, f = _split(g); A = band[1][1]; P = [row[4:7] for row in band[:3]]; H, W = dims(f); out = copy(f)
    for r, c in cells(f, lambda v: v == A):
        for dr in range(3):
            for dc in range(3):
                y, x = r + dr - 1, c + dc - 1
                if 0 <= y < H and 0 <= x < W: out[y][x] = P[dr][dc]
    return _tail(g, band, out)
rule("example_pair_cell_to_pattern", "The corner example shows a single cell turning into a 3 by 3 pattern; every field cell of that colour is replaced by the pattern centred on it, other cells stay.", gi_c2p, tf_c2p)


# 33 key colour says which object to crop out.
def gi_kcrop(rng):
    c = rng.choice(FC); h, w = _fsz(rng, 2, 8, 20); f = blank(h, w); k = rng.randint(2, 6)
    shapes = [random_shape(rng, rng.randint(3, 8)) for _ in range(k)]
    if place_shapes(rng, f, shapes, [c] + [rng.choice([x for x in FC if x != c]) for _ in range(k - 1)]) is None: return None
    r0, c0, r1, c1 = bbox(shapes[0])
    return None if len(shapes[0]) == (r1 - r0 + 1) * (c1 - c0 + 1) else _stack([[c]], f)
def tf_kcrop(g):
    band, f = _split(g); c = band[0][0]
    return crop(f, *bbox(cells(f, lambda v: v == c)))
rule("key_cell_crops_object_of_colour", "The key cell names a colour; output the bounding box of the one field object of that colour.", gi_kcrop, tf_kcrop)


# 34 key colour: count its cells, output a bar of that length on a field-wide row.
def gi_kcount(rng):
    cols = colours(rng, rng.randint(2, 4), (0, 5)); c = cols[0]; h, w = _fsz(rng, 2, 6, 20)
    f = _noise(rng, h, w, cols[1:], 0.25); sprinkle(rng, f, rng.randint(1, w - 1), c)
    return _stack([[c]], f)
def tf_kcount(g):
    band, f = _split(g); c = band[0][0]; n = sum(1 for row in f for v in row if v == c)
    return [[c if i < n else 0 for i in range(len(f[0]))]]
rule("key_colour_count_bar", "The key cell names a colour; output a single row as wide as the field with a bar of that colour as long as the number of its cells in the field.", gi_kcount, tf_kcount)


# 35 arrow glyph says which way every object casts a shadow to the edge.
def gi_aext(rng):
    d, L, col = rng.randrange(4), rng.randint(3, 5), rng.choice(FC); band = _arrow_band(rng, d, L, col)
    h, w = _fsz(rng, len(band) + 1, 8, 20); w = max(w, len(band[0]))
    f = _scene(rng, h, w, 2, 5, 2, 7, FC)
    return _stack(band, f) if f else None
def tf_aext(g):
    band, f = _split(g); d, _ = _arrow_dir(band); dy, dx = DIRS[d]; H, W = dims(f); out = copy(f)
    for r, c in cells(f, lambda v: v != 0):
        y, x = r + dy, c + dx
        while 0 <= y < H and 0 <= x < W and f[y][x] == 0:
            out[y][x] = f[r][c]; y += dy; x += dx
    return _tail(g, band, out)
rule("arrow_key_extrudes_objects", "The arrow above the separator gives a direction; every coloured field cell extends in that direction in its own colour until it reaches another coloured cell or the edge.", gi_aext, tf_aext)


# 36 the key motif is pasted inside every grey frame.
def gi_mframes(rng):
    mh, mw = rng.randint(2, 3), rng.randint(2, 3)
    motif = [[rng.choice([x for x in FC if x != 8]) for _ in range(mw)] for _ in range(mh)]
    if len({v for row in motif for v in row}) < 2: return None
    h, w = _fsz(rng, mh + 1, 8, 20); f = blank(h, w); n = 0; want = rng.randint(1, 4)
    for _ in range(60):
        if n >= want: break
        r0, c0 = rng.randint(0, h - mh - 2), rng.randint(0, w - mw - 2)
        if all(f[r][c] == 0 for r in range(max(0, r0 - 1), min(h, r0 + mh + 3)) for c in range(max(0, c0 - 1), min(w, c0 + mw + 3))):
            rect(f, r0, c0, r0 + mh + 1, c0 + mw + 1, 8, fill=False); n += 1
    return _stack(motif, f) if n else None
def tf_mframes(g):
    band, f = _split(g); motif = crop(band, *bbox(cells(band, lambda v: v != 0))); out = copy(f)
    for o in components(f, 8):
        r0, c0, r1, c1 = bbox(o); paste(out, motif, r0 + 1, c0 + 1)
    return _tail(g, band, out)
rule("key_motif_fills_frames", "The small motif above the separator is copied into the hollow of every grey frame in the field.", gi_mframes, tf_mframes)


# 37 digit cell says how many times to stack the field vertically.
def gi_vtile(rng):
    n = rng.randint(2, 4); h, w = rng.randint(2, 30 // n), rng.randint(3, 30)
    return _stack([[n]], _noise(rng, h, w, colours(rng, rng.randint(2, 4), (0, 5)), 0.4))
def tf_vtile(g):
    band, f = _split(g); n = band[0][0]
    return [row[:] for _ in range(n) for row in f]
rule("digit_key_tiles_field_vertically", "The key cell's value n says how many copies: output the field repeated n times top to bottom.", gi_vtile, tf_vtile)


# 38 grey dots down the left edge mark the rows to mirror left-right.
def gi_dotsmir(rng):
    h, w = _fsz(rng, 0, 6, 20); w = min(w, 29)
    f = _noise(rng, h, w, colours(rng, rng.randint(2, 4), (0, 5)), 0.35)
    marked = set(rng.sample(range(h), rng.randint(1, h - 1)))
    return [[SEP if r in marked else 0] + f[r] for r in range(h)]
def tf_dotsmir(g):
    return [[row[0]] + (row[1:][::-1] if row[0] == SEP else row[1:]) for row in g]
# left_dots_mirror_marked_rows dropped 2026-10-12 (trio review: behavioural duplicate or one global operation)
# 39 a 2x2 key of colours recolours the field by quadrant.
def gi_q4(rng):
    k4 = colours(rng, 4, (0, 5, 8)); h, w = _fsz(rng, 3, 6, 20); h -= h % 2; w -= w % 2
    f = _scene(rng, h, w, 2, 7, 2, 8, [8])
    return _stack([k4[:2], k4[2:]], f) if f else None
def tf_q4(g):
    band, f = _split(g); H, W = dims(f); out = copy(f)
    for r in range(H):
        for c in range(W):
            if f[r][c]: out[r][c] = band[r * 2 // H][c * 2 // W]
    return _tail(g, band, out)
rule("key_2x2_recolours_quadrants", "The 2 by 2 key above the separator holds four colours; every grey field cell takes the key colour of the quarter it lies in.", gi_q4, tf_q4)


# 40 key pair [A, B]: A cells touching a B cell become B.
def gi_eat(rng):
    cols = colours(rng, rng.randint(2, 4), (0, 5)); h, w = _fsz(rng, 2)
    return _stack([cols[:2]], _noise(rng, h, w, cols, 0.5))
def tf_eat(g):
    band, f = _split(g); A, B = band[0][0], band[0][1]; H, W = dims(f); out = copy(f)
    for r in range(H):
        for c in range(W):
            if f[r][c] == A and any(0 <= r + dy < H and 0 <= c + dx < W and f[r + dy][c + dx] == B for dy, dx in DIRS.values()):
                out[r][c] = B
    return _tail(g, band, out)
rule("key_pair_b_eats_a_neighbours", "The key pair above the separator reads A then B; every A cell in the field that shares a side with a B cell becomes B.", gi_eat, tf_eat)
