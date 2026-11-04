# b024_textures.py -- textures, periodic patterns and noise: two-period tilings with holes, defects or a misaligned
# patch; boundaries between textures; stripes vs solids (keep one, erase the other); periods read off as bars or
# digits; checkerboard/stripe conversions; hatched, dashed and textured objects; noise defined by colour count.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


# ---------------------------------------------------------------- local helpers
def _hw(rng, lo=6, hi=20):
    """Grid size with 40% of draws in the 21-30 band."""
    if rng.random() < 0.4:
        return rng.randint(max(lo, 21), 30), rng.randint(max(lo, 21), 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _primitive(t):
    """True when no proper divisor of the tile's height or width is also a period (wrapping)."""
    pr, pc = len(t), len(t[0])
    for d in range(1, pr):
        if pr % d == 0 and all(t[r] == t[(r + d) % pr] for r in range(pr)):
            return False
    for d in range(1, pc):
        if pc % d == 0 and all(t[r][c] == t[r][(c + d) % pc] for r in range(pr) for c in range(pc)):
            return False
    return True


def _tile(rng, pr, pc, cols):
    for _ in range(80):
        t = [[rng.choice(cols) for _ in range(pc)] for _ in range(pr)]
        if len({v for row in t for v in row}) >= min(2, len(cols)) and _primitive(t):
            return t
    return None


def _render(t, h, w, dr=0, dc=0):
    pr, pc = len(t), len(t[0])
    return [[t[(r + dr) % pr][(c + dc) % pc] for c in range(w)] for r in range(h)]


def _texture(rng, cols, pr_lo=1, pr_hi=4, pc_lo=1, pc_hi=4):
    """A primitive tile tiled over a grid at least three tiles each way. Returns (grid, tile) or None."""
    pr, pc = rng.randint(pr_lo, pr_hi), rng.randint(pc_lo, pc_hi)
    t = _tile(rng, pr, pc, cols)
    if t is None:
        return None
    h, w = _hw(rng, max(6, 3 * pr, 3 * pc), 20)
    return _render(t, h, w), t


def _find_tile(g, hole=None, ignore=frozenset(), tol=0.0):
    """Smallest-area (pr, pc) whose per-phase majority, ignoring hole-coloured and ignored cells, explains the
    grid with at most tol*H*W mismatches. Returns (pr, pc, tile) or None."""
    H, W = dims(g)
    for _, pr, pc in sorted((pr * pc, pr, pc) for pr in range(1, H // 2 + 1) for pc in range(1, W // 2 + 1)):
        tile = [[None] * pc for _ in range(pr)]; bad = 0; ok = True
        for i in range(pr):
            for j in range(pc):
                cnt = {}
                for r in range(i, H, pr):
                    for c in range(j, W, pc):
                        v = g[r][c]
                        if v != hole and (r, c) not in ignore:
                            cnt[v] = cnt.get(v, 0) + 1
                if not cnt:
                    ok = False; break
                v, n = max(cnt.items(), key=lambda kv: (kv[1], -kv[0]))
                tile[i][j] = v; bad += sum(cnt.values()) - n
            if not ok:
                break
        if ok and bad <= tol * H * W:
            return pr, pc, tile
    return None


def _holes(rng, g, k, c=0):
    H, W = dims(g)
    for r, x in rng.sample([(r, x) for r in range(H) for x in range(W)], min(k, H * W)):
        g[r][x] = c
    return g


def _blobs(g, bg=0):
    """4-connected components of non-background cells regardless of colour."""
    return components(g, lambda v: v != bg)  # same-colour only; multi-colour grouping below


def _mblobs(g, bg=0):
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


def _row_period(seq):
    """Smallest p with seq[i] == seq[i+p] for every i (no wrap)."""
    for p in range(1, len(seq)):
        if all(seq[i] == seq[i + p] for i in range(len(seq) - p)):
            return p
    return len(seq)


def _bands(rng, w, cols, w_lo=1, w_hi=5):
    """Vertical bands covering width w: list of (width, colour), adjacent colours differ."""
    out, left, last = [], w, None
    while left > 0:
        bw = min(left, rng.randint(w_lo, w_hi)); col = rng.choice([c for c in cols if c != last])
        out.append((bw, col)); left -= bw; last = col
    return out


def _paint_bands(bands, h):
    row = []
    for bw, col in bands:
        row += [col] * bw
    return [row[:] for _ in range(h)]


# ---------------------------------------------------------------- 1 two-period texture with holes restored
def gi_holes(rng):
    pr, pc = rng.sample(range(1, 5), 2)
    tx = _texture(rng, colours(rng, rng.randint(2, 4)), pr, pr, pc, pc)
    if tx is None: return None
    g, t = tx; h, w = dims(g); truth = copy(g)
    _holes(rng, g, rng.randint(2, h * w // 5))
    return g if tf_holes(copy(g)) == truth else None
def tf_holes(g):
    f = _find_tile(g, hole=0)
    return _render(f[2], *dims(g)) if f else None
# two_period_texture_holes_restored dropped 2026-10-12 (trio review: behavioural duplicate or one global operation)
# ---------------------------------------------------------------- 2 two textures meet: draw the boundary
def gi_boundary(rng):
    cs = colours(rng, rng.randint(4, 6), exclude=(0, 5)); ca, cb = cs[:len(cs) // 2], cs[len(cs) // 2:]
    h, w = _hw(rng, 8, 20)
    ta = _tile(rng, rng.randint(1, 3), rng.randint(1, 3), ca); tb = _tile(rng, rng.randint(1, 3), rng.randint(1, 3), cb)
    if ta is None or tb is None: return None
    s = rng.randint(3, w - 3); g = _render(ta, h, w); b = _render(tb, h, w)
    for r in range(h):
        g[r][s:] = b[r][s:]
    if rng.random() < 0.5:
        g = transpose(g)
    return g if tf_boundary(copy(g)) is not None else None
def tf_boundary(g):
    for view, gg in ((0, g), (1, transpose(g))):
        H, W = dims(gg); sa = {gg[r][0] for r in range(H)}
        cs = [{gg[r][c] for r in range(H)} for c in range(W)]
        split = [c for c in range(1, W) if all(x <= sa for x in cs[:c]) and all(not (x & sa) for x in cs[c:])]
        if split:
            out = blank(H, W)
            for r in range(H): out[r][split[0]] = 5
            return transpose(out) if view else out
    return None
rule("two_textures_boundary_line", "Two different textures share the grid, one on each side of a straight split; output only a grey line along the first row or column of the second texture.", gi_boundary, tf_boundary)


# ---------------------------------------------------------------- 3 the one tile that breaks the pattern turns grey
def gi_oddtile(rng):
    pr, pc = rng.randint(2, 4), rng.randint(2, 4); cols = colours(rng, rng.randint(2, 3), exclude=(0, 5))
    t = _tile(rng, pr, pc, cols)
    if t is None: return None
    big = rng.random() < 0.4
    nr = rng.randint(max(2, 21 // pr) if big else 2, 30 // pr); nc = rng.randint(max(2, 21 // pc) if big else 2, 30 // pc)
    if nr * nc < 4: return None
    g = _render(t, nr * pr, nc * pc); odd = _tile(rng, pr, pc, cols)
    if odd is None or odd == t: return None
    i, j = rng.randrange(nr), rng.randrange(nc); paste(g, odd, i * pr, j * pc)
    truth = copy(g); rect(truth, i * pr, j * pc, i * pr + pr - 1, j * pc + pc - 1, 5)
    return g if tf_oddtile(copy(g)) == truth else None
def tf_oddtile(g):
    H, W = dims(g)
    for _, pr, pc in sorted((pr * pc, pr, pc) for pr in range(1, H // 2 + 1) for pc in range(1, W // 2 + 1) if H % pr == 0 and W % pc == 0):
        tiles = {(i, j): crop(g, i, j, i + pr - 1, j + pc - 1) for i in range(0, H, pr) for j in range(0, W, pc)}
        if len(tiles) < 4: continue
        key = {}
        for k, t in tiles.items(): key.setdefault(str(t), []).append(k)
        if len(key) == 2 and min(len(v) for v in key.values()) == 1:
            (i, j), = min(key.values(), key=len); out = copy(g)
            return rect(out, i, j, i + pr - 1, j + pc - 1, 5)
    return None
rule("odd_tile_in_periodic_pattern_turns_grey", "The grid is tiled with one repeating block except for a single block that differs; that whole block is painted grey.", gi_oddtile, tf_oddtile)


# ---------------------------------------------------------------- 4 stripes inside a frame turn perpendicular
def gi_perp(rng):
    p = rng.randint(2, 4); seq = colours(rng, p, exclude=(0, 5)); h, w = _hw(rng, 8, 20)
    g = [[seq[r % p]] * w for r in range(h)]
    r0, c0 = rng.randint(1, h - 4), rng.randint(1, w - 4); r1, c1 = rng.randint(r0 + 3, min(h - 2, r0 + 12)), rng.randint(c0 + 3, min(w - 2, c0 + 12))
    rect(g, r0, c0, r1, c1, 5, fill=False)
    return g
def tf_perp(g):
    H, W = dims(g); fr = [o for o in components(g, 5) if len(o) > 4]
    if len(fr) != 1: return None
    r0, c0, r1, c1 = bbox(fr[0]); col0 = [g[r][0] for r in range(H)]; p = _row_period(col0); out = copy(g)
    for r in range(r0 + 1, r1):
        for c in range(c0 + 1, c1):
            out[r][c] = col0[(r0 + 1 + c - c0 - 1) % p]
    return out
rule("stripes_inside_frame_turn_perpendicular", "The grid has horizontal stripes and one grey frame; inside the frame the same stripe sequence runs vertically instead, starting again at the frame's inner left edge.", gi_perp, tf_perp)


# ---------------------------------------------------------------- 5/6 striped background with solid objects
def _striped_scene(rng):
    p = rng.randint(2, 4); seq = colours(rng, p); h, w = _hw(rng, 8, 20)
    g = [[seq[r % p]] * w for r in range(h)]; k = rng.randint(1, 5)
    ob = blank(h, w); shapes = [random_shape(rng, rng.randint(3, 8)) for _ in range(k)]
    cols = [rng.choice([c for c in COLOURS if c not in seq]) for _ in range(k)]
    if place_shapes(rng, ob, shapes, cols, margin=1) is None: return None
    if any(max(c for _, c in s) - min(c for _, c in s) + 1 > w // 3 for s in shapes): return None
    return paste(g, ob, 0, 0, transparent=0)
def tf_keep_objects(g):
    H, W = dims(g); out = blank(H, W)
    for r in range(H):
        maj = max(set(g[r]), key=g[r].count)
        for c in range(W):
            if g[r][c] != maj: out[r][c] = g[r][c]
    return out
rule("striped_background_keep_only_objects", "Solid objects lie on a background of horizontal colour stripes; the stripes are erased to black and only the objects remain.", _striped_scene, tf_keep_objects)
def tf_keep_stripes(g):
    return [[max(set(row), key=row.count)] * len(row) for row in g]
rule("striped_background_remove_objects", "Solid objects lie on a background of horizontal colour stripes; the objects are removed and each row is restored to its stripe colour.", _striped_scene, tf_keep_stripes)


# ---------------------------------------------------------------- 7 stripe period read off as a bar
def gi_period_bar(rng):
    p = rng.randint(2, 7); h, w = _hw(rng, 2 * p + 1, 20); seq = [rng.choice(colours(rng, rng.randint(2, 4))) for _ in range(p)]
    if _row_period(seq + seq) != p: return None
    return [[seq[c % p] for c in range(w)] for _ in range(h)]
def tf_period_bar(g):
    p = _row_period(g[0]); W = len(g[0])
    return [[5] * p + [0] * (W - p)] if p < W else None
rule("stripe_period_as_grey_bar", "The grid is vertical stripes repeating with some period; output a single row as wide as the grid with a grey bar as long as that period.", gi_period_bar, tf_period_bar)


# ---------------------------------------------------------------- 8 striped block shifts right by one period
def gi_block_shift(rng):
    p = rng.randint(2, 4); seq = colours(rng, p); h, w = _hw(rng, 8, 20)
    bh, bw = rng.randint(2, h // 2), rng.randint(2 * p, max(2 * p, w - p - 2))
    if bw + p > w: return None
    r0, c0 = rng.randint(0, h - bh), rng.randint(0, w - bw - p); g = blank(h, w)
    for r in range(r0, r0 + bh):
        for c in range(c0, c0 + bw): g[r][c] = seq[(c - c0) % p]
    return g
def tf_block_shift(g):
    cs = cells(g, lambda v: v != 0); r0, c0, r1, c1 = bbox(cs); row = g[r0][c0:c1 + 1]; p = _row_period(row)
    if c1 + p >= len(g[0]): return None
    out = blank(*dims(g))
    for r, c in cs: out[r][c + p] = g[r][c]
    return out
rule("striped_block_shifts_one_period_right", "A block filled with vertical stripes moves right by exactly one repetition of its stripe sequence.", gi_block_shift, tf_block_shift)


# ---------------------------------------------------------------- 9 checkerboard: holes filled, phases swapped
def gi_checker_swap(rng):
    a, b = colours(rng, 2); h, w = _hw(rng, 5, 20)
    g = [[a if (r + c) % 2 == 0 else b for c in range(w)] for r in range(h)]
    return _holes(rng, g, rng.randint(1, h * w // 4))
def tf_checker_swap(g):
    H, W = dims(g); maj = []
    for par in (0, 1):
        vals = [g[r][c] for r in range(H) for c in range(W) if (r + c) % 2 == par and g[r][c] != 0]
        if not vals: return None
        maj.append(max(set(vals), key=vals.count))
    return [[maj[1 - (r + c) % 2] for c in range(W)] for r in range(H)]
rule("checkerboard_holes_filled_phases_swapped", "A two-colour checkerboard has black holes; the holes are filled and then the two checkerboard colours exchange places.", gi_checker_swap, tf_checker_swap)


# ---------------------------------------------------------------- 10 solid objects become hatched
def _solid_scene(rng, n_lo=4, n_hi=12, k_lo=1, k_hi=5, exclude=(0, 5)):
    h, w = _hw(rng, 7, 20); g = blank(h, w); k = rng.randint(k_lo, k_hi)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    cols = [rng.choice([c for c in COLOURS if c not in exclude]) for _ in range(k)]
    return g if place_shapes(rng, g, shapes, cols, margin=1) is not None else None
def tf_hatch(g):
    out = copy(g)
    for r, c in cells(g, lambda v: v != 0):
        if (r + c) % 2 == 1: out[r][c] = 5
    return out
rule("objects_hatched_diagonally", "Every solid object is redrawn as a diagonal hatch: its cells on odd diagonals turn grey while those on even diagonals keep the colour.", _solid_scene, tf_hatch)


# ---------------------------------------------------------------- 11 the repeating unit of a 2D texture
def gi_unit(rng):
    tx = _texture(rng, colours(rng, rng.randint(2, 4)), 1, 5, 1, 5)
    if tx is None or (len(tx[1]), len(tx[1][0])) == (1, 1): return None
    return tx[0] if tf_unit(copy(tx[0])) == tx[1] else None
def tf_unit(g):
    f = _find_tile(g)
    return f[2] if f else None
rule("texture_repeating_unit_extracted", "The grid is a texture made by repeating one block in both directions; output just that smallest repeating block.", gi_unit, tf_unit)


# ---------------------------------------------------------------- 12 corner swatch texture fills the object silhouette
def gi_swatch_fill(rng):
    pr, pc = rng.randint(2, 3), rng.randint(2, 3); t = _tile(rng, pr, pc, colours(rng, rng.randint(2, 3)))
    if t is None: return None
    h, w = _hw(rng, 9, 20); g = blank(h, w); paste(g, t, 0, 0)
    x = rng.choice([c for c in COLOURS if c not in {v for row in t for v in row}])
    sh = random_shape(rng, rng.randint(5, 14)); sr, sc = max(r for r, _ in sh) + 1, max(c for _, c in sh) + 1
    if sr > h - pr - 1: return None
    r0 = rng.randint(pr + 1, h - sr); c0 = rng.randint(0, w - sc)
    for r, c in sh: g[r0 + r][c0 + c] = x
    return g
def tf_swatch_fill(g):
    bl = _mblobs(g); sw = next((b for b in bl if (0, 0) in b), None)
    if sw is None: return None
    r0, c0, r1, c1 = bbox(sw); t = crop(g, r0, c0, r1, c1); pr, pc = dims(t); out = copy(g)
    for b in bl:
        if b is not sw:
            for r, c in b: out[r][c] = t[r % pr][c % pc]
    return out
rule("corner_swatch_textures_object", "A small texture swatch sits in the top-left corner; the solid object below is refilled with that texture continued across the grid from the corner.", gi_swatch_fill, tf_swatch_fill)


# ---------------------------------------------------------------- 13 noise = any colour outside the top two by count
def gi_toptwo(rng):
    h, w = _hw(rng, 7, 20); g = blank(h, w); a = rng.choice(COLOURS); k = rng.randint(2, 6)
    if place_shapes(rng, g, [random_shape(rng, rng.randint(4, 10)) for _ in range(k)], [a] * k, margin=0) is None: return None
    na = sum(row.count(a) for row in g); others = [c for c in COLOURS if c != a]
    free = [(r, c) for r in range(h) for c in range(w) if g[r][c] == 0]
    for r, c in rng.sample(free, min(len(free), rng.randint(2, min(na - 1, h * w // 6)))):
        g[r][c] = rng.choice(others)
    cnt = counts(g)
    return g if sorted(cnt, key=cnt.get)[-2:] in ([0, a], [a, 0]) and len(cnt) > 2 else None
def tf_toptwo(g):
    cnt = counts(g); top = sorted(cnt, key=lambda k: (cnt[k], k))[-2:]; bg = max(top, key=cnt.get)
    return [[v if v in top else bg for v in row] for row in g]
rule("noise_outside_top_two_colours_cleared", "Only the two most common colours are real; every cell of any other colour is replaced by the most common colour.", gi_toptwo, tf_toptwo)


# ---------------------------------------------------------------- 14 speckled lines restored, speckles removed
def gi_speckled(rng):
    h, w = _hw(rng, 8, 20); L = rng.choice(COLOURS); g = blank(h, w)
    rows = rng.sample(range(h), rng.randint(1, max(1, h // 3))); cols_ = rng.sample(range(w), rng.randint(0, max(1, w // 3)))
    for r in rows: g[r] = [L] * w
    for c in cols_:
        for r in range(h): g[r][c] = L
    truth = copy(g)
    for r, c in rng.sample([(r, c) for r in range(h) for c in range(w)], rng.randint(3, h * w // 8)):
        g[r][c] = rng.choice([x for x in COLOURS if x != L])
    return g if tf_speckled(copy(g)) == truth else None
def tf_speckled(g):
    H, W = dims(g); cnt = counts(g); cnt.pop(0, None)
    if not cnt: return None
    L = max(cnt, key=lambda k: (cnt[k], k)); out = blank(H, W)
    for r in range(H):
        if g[r].count(L) * 5 >= W * 3: out[r] = [L] * W
    for c in range(W):
        if sum(g[r][c] == L for r in range(H)) * 5 >= H * 3:
            for r in range(H): out[r][c] = L
    return out
rule("speckled_lines_restored_speckles_removed", "Full rows and columns of one colour are peppered with speckles of other colours; the lines are made solid again and every speckle elsewhere is erased.", gi_speckled, tf_speckled)


# ---------------------------------------------------------------- 15 texture inverted inside the object's silhouette
def gi_invert_sil(rng):
    a, b, x = colours(rng, 3); tx = _texture(rng, [a, b], 1, 3, 1, 3)
    if tx is None: return None
    g, t = tx; h, w = dims(g); sh = random_shape(rng, rng.randint(5, min(14, h * w // 5)))
    sr, sc = max(r for r, _ in sh) + 1, max(c for _, c in sh) + 1
    if sr > h or sc > w: return None
    r0, c0 = rng.randint(0, h - sr), rng.randint(0, w - sc); truth = copy(g)
    for r, c in sh:
        g[r0 + r][c0 + c] = x; truth[r0 + r][c0 + c] = b if truth[r0 + r][c0 + c] == a else a
    return g if tf_invert_sil(copy(g)) == truth else None
def tf_invert_sil(g):
    cnt = counts(g)
    if len(cnt) != 3: return None
    x = min(cnt, key=lambda k: (cnt[k], k)); a, b = [k for k in cnt if k != x]
    f = _find_tile(g, hole=x)
    if not f: return None
    full = _render(f[2], *dims(g))
    return [[(b if full[r][c] == a else a) if g[r][c] == x else g[r][c] for c in range(len(g[0]))] for r in range(len(g))]
rule("texture_inverted_inside_silhouette", "A solid shape covers part of a two-colour texture; the shape is replaced by the texture with its two colours swapped, the rest unchanged.", gi_invert_sil, tf_invert_sil)


# ---------------------------------------------------------------- 16 stripes thickening left to right, continued
def gi_gradient(rng):
    a, b = colours(rng, 2); h, w = _hw(rng, 10, 24); k = rng.randint(2, 4)
    if k * (k + 1) // 2 + k + 1 > w: return None
    g = blank(h, w); c = 0
    for i in range(1, k + 1):
        for _ in range(i):
            for r in range(h): g[r][c] = (a, b)[(i - 1) % 2]
            c += 1
    return g
def tf_gradient(g):
    H, W = dims(g); row = g[0]; widths, cols_, c = [], [], 0
    while c < W and row[c] != 0:
        n = c
        while n < W and row[n] == row[c]: n += 1
        widths.append(n - c); cols_.append(row[c]); c = n
    if len(widths) < 2 or widths != list(range(1, len(widths) + 1)): return None
    out = copy(g); i = len(widths)
    while c < W:
        i += 1
        for _ in range(i):
            if c < W:
                for r in range(H): out[r][c] = cols_[(i - 1) % 2]
                c += 1
    return out
rule("thickening_stripes_continued_right", "Vertical stripes alternate between two colours and each stripe is one cell wider than the last; the sequence is continued across the black remainder of the grid.", gi_gradient, tf_gradient)


# ---------------------------------------------------------------- 17/24/38 textured vs solid rectangles
def _rect_scene(rng, kinds, lo_k=2, hi_k=6, exclude=(0, 5)):
    """Non-overlapping rectangles each drawn in one of the given kinds: 'solid', 'checker', 'hstripe'. Returns (grid, kinds-used)."""
    h, w = _hw(rng, 8, 20); g = blank(h, w); used = []
    for _ in range(rng.randint(lo_k, hi_k)):
        for _ in range(30):
            rh, rw = rng.randint(2, 6), rng.randint(2, 6); r0, c0 = rng.randint(0, h - rh), rng.randint(0, w - rw)
            if all(g[r][c] == 0 for r in range(max(0, r0 - 1), min(h, r0 + rh + 1)) for c in range(max(0, c0 - 1), min(w, c0 + rw + 1))):
                kind = rng.choice(kinds); a, b = colours(rng, 2, exclude=exclude)
                for r in range(r0, r0 + rh):
                    for c in range(c0, c0 + rw):
                        g[r][c] = a if kind == "solid" else (a if (r + c) % 2 == 0 else b) if kind == "checker" else (a if (r - r0) % 2 == 0 else b)
                used.append(kind); break
    return (g, used) if used else None
def gi_tex_vs_solid(rng):
    sc = _rect_scene(rng, ["solid", "checker"])
    return sc[0] if sc and len(set(sc[1])) == 2 else None
def tf_keep_textured(g):
    out = copy(g)
    for b in _mblobs(g):
        if len({g[r][c] for r, c in b}) == 1:
            for r, c in b: out[r][c] = 0
    return out
rule("checkered_rectangles_kept_solid_erased", "Some rectangles are solid and some are checkered in two colours; the solid ones are erased and the checkered ones stay.", gi_tex_vs_solid, tf_keep_textured)


# ---------------------------------------------------------------- 18 striped rectangles recoloured by stripe width (digit)
def gi_stripe_width(rng):
    h, w = _hw(rng, 8, 20); g = blank(h, w); n = 0
    for _ in range(rng.randint(2, 6)):
        for _ in range(30):
            s = rng.randint(1, 4); rh, rw = rng.randint(2 * s + 1, min(h, 4 * s + 2)), rng.randint(2, 7)
            if rh > h: continue
            r0, c0 = rng.randint(0, h - rh), rng.randint(0, w - rw)
            if all(g[r][c] == 0 for r in range(max(0, r0 - 1), min(h, r0 + rh + 1)) for c in range(max(0, c0 - 1), min(w, c0 + rw + 1))):
                a, b = colours(rng, 2, exclude=(0, 1, 2, 3, 4))
                for r in range(r0, r0 + rh):
                    for c in range(c0, c0 + rw): g[r][c] = a if ((r - r0) // s) % 2 == 0 else b
                n += 1; break
    return g if n else None
def tf_stripe_width(g):
    out = copy(g)
    for b in _mblobs(g):
        r0, c0, r1, c1 = bbox(b); s = 0
        while r0 + s <= r1 and g[r0 + s][c0] == g[r0][c0]: s += 1
        for r, c in b: out[r][c] = s
    return out
rule("striped_rectangles_recoloured_by_stripe_width", "Each rectangle is filled with horizontal stripes of two colours; the rectangle becomes solid in the colour whose number equals the stripe thickness.", gi_stripe_width, tf_stripe_width, digits=True)


# ---------------------------------------------------------------- 19 stripes become a checkerboard
def gi_stripes2(rng):
    a, b = colours(rng, 2); h, w = _hw(rng, 4, 20)
    return [[(a, b)[c % 2] for c in range(w)] for _ in range(h)]
def tf_stripes2(g):
    return [row if r % 2 == 0 else row[1:] + row[:1] for r, row in enumerate(g)]
rule("stripes_become_checkerboard", "Vertical stripes of two alternating colours become a checkerboard: every odd row is shifted one cell to the left.", gi_stripes2, tf_stripes2)


# ---------------------------------------------------------------- 20 checkerboard becomes horizontal stripes
def gi_checker(rng):
    a, b = colours(rng, 2); h, w = _hw(rng, 4, 20)
    return [[(a, b)[(r + c) % 2] for c in range(w)] for r in range(h)]
def tf_checker_rows(g):
    return [[row[0]] * len(row) for row in g]
rule("checkerboard_to_horizontal_stripes", "A two-colour checkerboard becomes horizontal stripes: every row is filled with the colour of its leftmost cell.", gi_checker, tf_checker_rows)


# ---------------------------------------------------------------- 21 rectangles striped across their short axis
def gi_rects_axis(rng):
    h, w = _hw(rng, 8, 20); g = blank(h, w); n = 0
    for _ in range(rng.randint(2, 6)):
        for _ in range(30):
            rh, rw = rng.randint(2, 7), rng.randint(2, 7)
            if rh == rw: continue
            r0, c0 = rng.randint(0, h - rh), rng.randint(0, w - rw)
            if all(g[r][c] == 0 for r in range(max(0, r0 - 1), min(h, r0 + rh + 1)) for c in range(max(0, c0 - 1), min(w, c0 + rw + 1))):
                rect(g, r0, c0, r0 + rh - 1, c0 + rw - 1, rng.choice(colours(rng, 1, exclude=(0, 5)))); n += 1; break
    return g if n else None
def tf_rects_axis(g):
    out = copy(g)
    for b in _mblobs(g):
        r0, c0, r1, c1 = bbox(b); wide = (c1 - c0) > (r1 - r0)
        for r, c in b:
            if ((c - c0) if wide else (r - r0)) % 2 == 1: out[r][c] = 5
    return out
rule("rectangles_striped_across_short_axis", "Each solid rectangle is striped with grey: wide rectangles get alternate columns greyed, tall rectangles alternate rows, starting from their top-left corner.", gi_rects_axis, tf_rects_axis)


# ---------------------------------------------------------------- 22 defect cells in a texture marked grey
def gi_defects(rng):
    tx = _texture(rng, colours(rng, rng.randint(2, 4), exclude=(0, 5)), 1, 4, 1, 4)
    if tx is None: return None
    g, t = tx; h, w = dims(g); truth = copy(g); tc = sorted({v for row in t for v in row})
    for r, c in rng.sample([(r, c) for r in range(h) for c in range(w)], rng.randint(1, max(1, h * w // 25))):
        g[r][c] = rng.choice([v for v in tc if v != g[r][c]]); truth[r][c] = 5
    return g if tf_defects(copy(g)) == truth else None
def tf_defects(g):
    f = _find_tile(g, tol=0.08)
    if not f: return None
    full = _render(f[2], *dims(g))
    return [[5 if g[r][c] != full[r][c] else g[r][c] for c in range(len(g[0]))] for r in range(len(g))]
rule("texture_defect_cells_marked_grey", "The grid is a repeating texture in which a few cells carry the wrong colour; each wrong cell is marked grey.", gi_defects, tf_defects)


# ---------------------------------------------------------------- 23 misaligned patch inside a frame realigned
def gi_misaligned(rng):
    tx = _texture(rng, colours(rng, rng.randint(2, 3), exclude=(0, 5)), 1, 4, 1, 4)
    if tx is None: return None
    g, t = tx; h, w = dims(g); pr, pc = dims(t)
    if h < 7 or w < 7: return None
    r0, c0 = rng.randint(0, h - 5), rng.randint(0, w - 5); r1, c1 = rng.randint(r0 + 3, min(h - 1, r0 + 12)), rng.randint(c0 + 3, min(w - 1, c0 + 12))
    dr, dc = rng.randrange(pr), rng.randrange(pc)
    if (dr, dc) == (0, 0): return None
    truth = copy(g); rect(truth, r0, c0, r1, c1, 5, fill=False); rect(g, r0, c0, r1, c1, 5, fill=False)
    for r in range(r0 + 1, r1):
        for c in range(c0 + 1, c1): g[r][c] = t[(r + dr) % pr][(c + dc) % pc]
    return g if tf_misaligned(copy(g)) == truth else None
def tf_misaligned(g):
    fr = [o for o in components(g, 5) if len(o) > 4]
    if len(fr) != 1: return None
    r0, c0, r1, c1 = bbox(fr[0]); inner = {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)}
    f = _find_tile(g, ignore=inner)
    if not f: return None
    full = _render(f[2], *dims(g)); out = copy(g)
    for r in range(r0 + 1, r1):
        for c in range(c0 + 1, c1): out[r][c] = full[r][c]
    return out
rule("misaligned_texture_patch_realigned", "Inside a grey frame the surrounding texture is shifted out of step; the patch is redrawn so the texture runs continuously through the frame.", gi_misaligned, tf_misaligned)


# ---------------------------------------------------------------- 24 textured objects turn solid grey
def gi_tex_grey(rng):
    sc = _rect_scene(rng, ["solid", "checker", "hstripe"])
    return sc[0] if sc and "solid" in sc[1] and len(set(sc[1])) >= 2 else None
def tf_tex_grey(g):
    out = copy(g)
    for b in _mblobs(g):
        if len({g[r][c] for r, c in b}) > 1:
            for r, c in b: out[r][c] = 5
    return out
rule("textured_rectangles_turn_solid_grey", "Rectangles drawn in a two-colour texture become solid grey; rectangles already of a single colour are left alone.", gi_tex_grey, tf_tex_grey)


# ---------------------------------------------------------------- 25 texture's two periods as two bars
def gi_two_bars(rng):
    tx = _texture(rng, colours(rng, rng.randint(2, 4), exclude=(0, 5)), 1, 6, 1, 6)
    if tx is None or dims(tx[1]) == (1, 1): return None
    return tx[0] if _find_tile(tx[0])[2] == tx[1] else None
def tf_two_bars(g):
    f = _find_tile(g)
    if not f: return None
    pr, pc, _ = f; W = max(pr, pc) + 1
    return [[5] * pr + [0] * (W - pr), [5] * pc + [0] * (W - pc)]
rule("texture_row_and_column_periods_as_bars", "The grid is a repeating texture; output two rows of grey bars, the top one as long as the texture's vertical period and the bottom one as long as its horizontal period.", gi_two_bars, tf_two_bars)


# ---------------------------------------------------------------- 26 texture retiled from its unit rotated a quarter turn
def gi_rot_tile(rng):
    tx = _texture(rng, colours(rng, rng.randint(2, 4)), 2, 4, 2, 4)
    if tx is None: return None
    return tx[0] if _find_tile(tx[0])[2] == tx[1] else None
def tf_rot_tile(g):
    f = _find_tile(g)
    return _render(rot90(f[2]), *dims(g)) if f else None
rule("texture_unit_rotated_and_retiled", "The grid's repeating block is rotated a quarter turn clockwise and the grid is refilled by repeating the rotated block from the top-left corner.", gi_rot_tile, tf_rot_tile)


# ---------------------------------------------------------------- 27 widest band turns grey
def gi_widest(rng):
    h, w = _hw(rng, 6, 20); bands = _bands(rng, w, colours(rng, rng.randint(2, 5), exclude=(0, 5)))
    ws = sorted(b[0] for b in bands)
    return _paint_bands(bands, h) if len(bands) > 2 and ws[-1] != ws[-2] else None
def _runs(row):
    out, c = [], 0
    while c < len(row):
        n = c
        while n < len(row) and row[n] == row[c]: n += 1
        out.append((c, n - c, row[c])); c = n
    return out
def tf_widest(g):
    runs = _runs(g[0]); start, bw, _ = max(runs, key=lambda t: t[1]); out = copy(g)
    for row in out:
        for c in range(start, start + bw): row[c] = 5
    return out
rule("widest_vertical_band_turns_grey", "The grid is divided into vertical bands of different widths; the single widest band is repainted grey.", gi_widest, tf_widest)


# ---------------------------------------------------------------- 28 bands sorted by width
def gi_sort_bands(rng):
    h, w = _hw(rng, 6, 20); bands = _bands(rng, w, colours(rng, rng.randint(2, 5)))
    ws = [b[0] for b in bands]
    return _paint_bands(bands, h) if len(bands) > 2 and ws != sorted(ws) else None
def tf_sort_bands(g):
    runs = sorted(_runs(g[0]), key=lambda t: (t[1], t[0]))
    return _paint_bands([(bw, col) for _, bw, col in runs], len(g))
rule("vertical_bands_sorted_by_width", "The vertical colour bands are reordered from narrowest on the left to widest on the right.", gi_sort_bands, tf_sort_bands)


# ---------------------------------------------------------------- 29 stripe orientation per band -> solid label
def gi_orient(rng):
    a, b = colours(rng, 2, exclude=(0, 1, 2)); h, w = _hw(rng, 6, 20); g = blank(h, w); c = 0; kinds = set()
    while c < w:
        bw = min(w - c, rng.randint(2, 6)); horiz = rng.random() < 0.5; kinds.add(horiz)
        for r in range(h):
            for x in range(c, c + bw): g[r][x] = (a, b)[r % 2] if horiz else (a, b)[(x - c) % 2]
        c += bw
    return g if len(kinds) == 2 else None
def tf_orient(g):
    H, W = dims(g)
    return [[2 if all(g[r][c] == g[0][c] for r in range(H)) else 1 for c in range(W)] for _ in range(H)]
rule("stripe_orientation_bands_labelled", "The grid is split into vertical bands striped either horizontally or vertically in the same two colours; horizontally striped bands become solid 1 and vertically striped bands solid 2.", gi_orient, tf_orient)


# ---------------------------------------------------------------- 30 stripes stretched in place
def gi_stretch(rng):
    p = rng.randint(2, 5); seq = colours(rng, p); h, w = _hw(rng, 2 * p, 20)
    return [[seq[c % p] for c in range(w)] for _ in range(h)]
def tf_stretch(g):
    return [[row[c // 2] for c in range(len(row))] for row in g]
rule("stripes_doubled_in_width_in_place", "Every vertical stripe becomes twice as wide, the pattern growing from the left edge and whatever no longer fits being cut off at the right.", gi_stretch, tf_stretch)


# ---------------------------------------------------------------- 31 holes in a texture counted as a bar
def gi_hole_count(rng):
    tx = _texture(rng, colours(rng, rng.randint(2, 4), exclude=(0, 5)), 1, 4, 1, 4)
    if tx is None: return None
    g = tx[0]; h, w = dims(g)
    return _holes(rng, g, rng.randint(1, w - 1))
def tf_hole_count(g):
    W = len(g[0]); k = sum(row.count(0) for row in g)
    return [[5] * k + [0] * (W - k)] if 0 < k < W else None
rule("texture_hole_count_bar", "A repeating texture has black holes; output one row as wide as the grid with a grey bar one cell long per hole.", gi_hole_count, tf_hole_count)


# ---------------------------------------------------------------- 32 rows grouped by which texture they belong to
def gi_group_rows(rng):
    cs = colours(rng, rng.randint(4, 6)); ca, cb = cs[:len(cs) // 2], cs[len(cs) // 2:]; h, w = _hw(rng, 6, 20)
    ta = _tile(rng, rng.randint(1, 3), rng.randint(1, 4), ca); tb = _tile(rng, rng.randint(1, 3), rng.randint(1, 4), cb)
    if ta is None or tb is None: return None
    A, B = _render(ta, h, w), _render(tb, h, w); which = [rng.random() < 0.5 for _ in range(h)]
    if all(which) or not any(which) or which == sorted(which, reverse=True): return None
    which[0] = True
    return [A[r] if which[r] else B[r] for r in range(h)]
def tf_group_rows(g):
    sets = [set(row) for row in g]; grp = set(g[0]); changed = True
    while changed:
        changed = False
        for s in sets:
            if s & grp and not s <= grp: grp |= s; changed = True
    first = [row for row in g if set(row) <= grp]; rest = [row for row in g if not set(row) <= grp]
    return first + rest if rest else None
rule("rows_grouped_by_texture", "Rows of two textures with different colours are interleaved; the rows sharing the top row's texture move to the top in their order, the other texture's rows follow below.", gi_group_rows, tf_group_rows)


# ---------------------------------------------------------------- 33 textured block outlined in its majority colour
def gi_tex_outline(rng):
    sc = _rect_scene(rng, ["checker", "hstripe"], 1, 4)
    if not sc: return None
    g = sc[0]
    return g if all(max(bbox(b)[2] - bbox(b)[0], bbox(b)[3] - bbox(b)[1]) >= 2 for b in _mblobs(g)) else None
def tf_tex_outline(g):
    out = copy(g)
    for b in _mblobs(g):
        vals = [g[r][c] for r, c in b]; maj = max(sorted(set(vals)), key=vals.count); r0, c0, r1, c1 = bbox(b)
        rect(out, r0, c0, r1, c1, 0); rect(out, r0, c0, r1, c1, maj, fill=False)
    return out
rule("textured_rectangle_outlined_in_majority_colour", "Each textured rectangle is reduced to its outline drawn in the texture's more frequent colour, its interior emptied.", gi_tex_outline, tf_tex_outline)


# ---------------------------------------------------------------- 34 diagonal stripes with holes restored
def gi_diag_holes(rng):
    p = rng.randint(2, 6); cols = colours(rng, rng.randint(2, min(4, p)))
    for _ in range(40):
        seq = [rng.choice(cols) for _ in range(p)]
        if len(set(seq)) >= 2 and _row_period(seq * 3) == p: break
    else: return None
    h, w = _hw(rng, p + 2, 20); g = [[seq[(r + c) % p] for c in range(w)] for r in range(h)]; truth = copy(g)
    _holes(rng, g, rng.randint(2, h * w // 4))
    return g if tf_diag_holes(copy(g)) == truth else None
def tf_diag_holes(g):
    H, W = dims(g)
    for p in range(1, H + W):
        cls = [{g[r][c] for r in range(H) for c in range(W) if (r + c) % p == k} - {0} for k in range(p)]
        if all(len(s) == 1 for s in cls):
            return [[next(iter(cls[(r + c) % p])) for c in range(W)] for r in range(H)]
    return None
rule("diagonal_stripes_holes_restored", "The grid is diagonal stripes repeating a colour sequence, with black holes; each hole is filled with the colour of its diagonal.", gi_diag_holes, tf_diag_holes)


# ---------------------------------------------------------------- 35 object borders dashed
def gi_dashed(rng):
    return _solid_scene(rng, 6, 16, 1, 4)
def tf_dashed(g):
    H, W = dims(g); out = copy(g)
    for r, c in cells(g, lambda v: v != 0):
        edge = any(not (0 <= r + dr < H and 0 <= c + dc < W) or g[r + dr][c + dc] != g[r][c] for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if edge and (r + c) % 2 == 1: out[r][c] = 5
    return out
rule("object_borders_dashed_grey", "Each object's border cells alternate with grey along odd diagonals, giving a dashed outline; interior cells keep their colour.", gi_dashed, tf_dashed)


# ---------------------------------------------------------------- 36 fine checkerboard becomes coarse
def tf_coarse(g):
    a, b = g[0][0], g[0][1]
    return [[a if ((r // 2) + (c // 2)) % 2 == 0 else b for c in range(len(g[0]))] for r in range(len(g))]
rule("checkerboard_cells_doubled_to_two_by_two", "The one-cell checkerboard becomes a checkerboard of two-by-two blocks, the top-left colour staying in place.", gi_checker, tf_coarse)


# ---------------------------------------------------------------- 37 noisy vertical stripes restored
def gi_noisy_cols(rng):
    p = rng.randint(2, 5); seq = colours(rng, p); h, w = _hw(rng, 6, 20)
    g = [[seq[c % p] for c in range(w)] for _ in range(h)]; others = [c for c in COLOURS if c not in seq] or [0]
    for r, c in rng.sample([(r, c) for r in range(h) for c in range(w)], rng.randint(1, h * w // 5)):
        g[r][c] = rng.choice(others)
    return g
def tf_noisy_cols(g):
    H, W = dims(g); out = blank(H, W)
    for c in range(W):
        col = [g[r][c] for r in range(H)]; maj = max(sorted(set(col)), key=col.count)
        for r in range(H): out[r][c] = maj
    return out
rule("noisy_vertical_stripes_restored", "Vertical colour stripes are peppered with cells of foreign colours; every column is restored to its most common colour.", gi_noisy_cols, tf_noisy_cols)


# ---------------------------------------------------------------- 38 checkered vs striped rectangles counted
def gi_count_kinds(rng):
    sc = _rect_scene(rng, ["checker", "hstripe"], 2, 7)
    return sc[0] if sc else None
def tf_count_kinds(g):
    ch = st = 0
    for b in _mblobs(g):
        r0, c0, r1, c1 = bbox(b)
        if c1 == c0 or r1 == r0: return None
        if g[r0][c0] != g[r0][c0 + 1]: ch += 1
        else: st += 1
    W = max(ch, st) + 1
    return [[5] * ch + [0] * (W - ch), [5] * st + [0] * (W - st)]
rule("checkered_vs_striped_rectangles_count_bars", "Output two rows of grey bars: the top counts the checkered rectangles and the bottom counts the horizontally striped ones.", gi_count_kinds, tf_count_kinds)


# ---------------------------------------------------------------- 39 bands recoloured by width (digit)
def gi_band_digit(rng):
    h, w = _hw(rng, 5, 20); bands = _bands(rng, w, colours(rng, rng.randint(2, 4), exclude=(0, 1, 2, 3, 4)), 1, 4)
    return _paint_bands(bands, h) if len({b[0] for b in bands}) > 1 else None
def tf_band_digit(g):
    return _paint_bands([(bw, bw) for _, bw, _ in _runs(g[0])], len(g))
rule("vertical_bands_recoloured_by_width_digit", "Each vertical band is repainted in the colour whose number equals the band's width in cells.", gi_band_digit, tf_band_digit, digits=True)


# ---------------------------------------------------------------- 40 unit tile of a textured block on black
def gi_block_unit(rng):
    pr, pc = rng.randint(1, 4), rng.randint(1, 4); t = _tile(rng, pr, pc, colours(rng, rng.randint(2, 4)))
    if t is None or (pr, pc) == (1, 1): return None
    h, w = _hw(rng, 8, 20); bh, bw = rng.randint(2 * pr, min(h, 4 * pr + 2)), rng.randint(2 * pc, min(w, 4 * pc + 2))
    r0, c0 = rng.randint(0, h - bh), rng.randint(0, w - bw); g = blank(h, w)
    paste(g, _render(t, bh, bw), r0, c0)
    return g if tf_block_unit(copy(g)) == t else None
def tf_block_unit(g):
    f = _find_tile(crop(g, *bbox(cells(g, lambda v: v != 0))))
    return f[2] if f else None
rule("textured_block_unit_tile_extracted", "A textured block lies on a black background; output the block's smallest repeating unit.", gi_block_unit, tf_block_unit)
