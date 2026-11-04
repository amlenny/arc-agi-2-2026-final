# b045_anchors.py -- normalising a scene to a grey anchor: translate, wrap, rotate, mirror, crop,
# scale, recolour, offset and align every object relative to one grey (colour 5) marker cell or glyph.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

ANCHOR = 5
ARM = 6
_DIRS4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


def _dims_mixed(rng, p_big=0.4, lo=9, hi=20, blo=21, bhi=30):
    if rng.random() < p_big:
        return rng.randint(blo, bhi), rng.randint(blo, bhi)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _scene_with_anchor(rng, k_lo=2, k_hi=5, n_lo=2, n_hi=8, margin=1, lo=9, hi=20):
    """k random shapes (never coloured ANCHOR) plus one isolated grey anchor cell."""
    h, w = _dims_mixed(rng, lo=lo, hi=hi)
    g = blank(h, w)
    k = rng.randint(k_lo, k_hi)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    cols = [rng.choice([c for c in COLOURS if c != ANCHOR]) for _ in range(k)]
    pos = place_shapes(rng, g, shapes, cols, margin=margin)
    if pos is None:
        return None
    free = cells(g, lambda v: v == 0)
    if not free:
        return None
    ar, ac = rng.choice(free)
    g[ar][ac] = ANCHOR
    return g


def _scene_anchor_region(rng, region_pred, lo=9, hi=20):
    h, w = _dims_mixed(rng, lo=lo, hi=hi)
    g = blank(h, w)
    k = rng.randint(2, 5)
    shapes = [random_shape(rng, rng.randint(2, 7)) for _ in range(k)]
    cols = [rng.choice([c for c in COLOURS if c != ANCHOR]) for _ in range(k)]
    pos = place_shapes(rng, g, shapes, cols, margin=1)
    if pos is None:
        return None
    H, W = dims(g)
    free = [(r, c) for r, c in cells(g, lambda v: v == 0) if region_pred(r, c, H, W)]
    if not free:
        return None
    ar, ac = rng.choice(free)
    g[ar][ac] = ANCHOR
    return g


def _scene_with_glyph(rng, arms=1, lo=9, hi=20):
    h, w = _dims_mixed(rng, lo=lo, hi=hi)
    g = blank(h, w)
    k = rng.randint(2, 4)
    shapes = [random_shape(rng, rng.randint(2, 6)) for _ in range(k)]
    cols = [rng.choice([c for c in COLOURS if c not in (ANCHOR, ARM)]) for _ in range(k)]
    pos = place_shapes(rng, g, shapes, cols, margin=1)
    if pos is None:
        return None
    H, W = dims(g)
    free = [(r, c) for r in range(1, H - 1) for c in range(1, W - 1) if g[r][c] == 0]
    rng.shuffle(free)
    for (pr, pc) in free:
        if arms == 1:
            d = rng.choice(_DIRS4)
            nr, nc = pr + d[0], pc + d[1]
            if 0 <= nr < H and 0 <= nc < W and g[nr][nc] == 0:
                g[pr][pc] = ANCHOR; g[nr][nc] = ARM
                return g
        else:
            vdir = rng.choice([(-1, 0), (1, 0)]); hdir = rng.choice([(0, -1), (0, 1)])
            n1 = (pr + vdir[0], pc + vdir[1]); n2 = (pr + hdir[0], pc + hdir[1])
            if (0 <= n1[0] < H and 0 <= n1[1] < W and 0 <= n2[0] < H and 0 <= n2[1] < W
                    and g[n1[0]][n1[1]] == 0 and g[n2[0]][n2[1]] == 0):
                g[pr][pc] = ANCHOR; g[n1[0]][n1[1]] = ARM; g[n2[0]][n2[1]] = ARM
                return g
    return None


def _scene_with_dots(rng, k_lo=2, k_hi=4, n_lo=4, n_hi=9, margin=2, lo=10, hi=20):
    """Each of k shapes gets one grey dot touching it from outside -- its own anchor."""
    h, w = _dims_mixed(rng, lo=lo, hi=hi)
    g = blank(h, w)
    k = rng.randint(k_lo, k_hi)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    cols = [rng.choice([c for c in COLOURS if c != ANCHOR]) for _ in range(k)]
    pos = place_shapes(rng, g, shapes, cols, margin=margin)
    if pos is None:
        return None
    H, W = dims(g)
    for sh, (r0, c0) in zip(shapes, pos):
        placed = [(r0 + r, c0 + c) for r, c in sh]
        rng.shuffle(placed)
        done = False
        for (pr, pc) in placed:
            for dr, dc in _DIRS4:
                nr, nc = pr + dr, pc + dc
                if 0 <= nr < H and 0 <= nc < W and g[nr][nc] == 0:
                    g[nr][nc] = ANCHOR; done = True
                    break
            if done:
                break
        if not done:
            return None
    return g


def _scene_one_marked(rng, k_lo=2, k_hi=5, n_lo=3, n_hi=8, margin=2, lo=9, hi=20):
    h, w = _dims_mixed(rng, lo=lo, hi=hi)
    g = blank(h, w)
    k = rng.randint(k_lo, k_hi)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    cols = [rng.choice([c for c in COLOURS if c != ANCHOR]) for _ in range(k)]
    pos = place_shapes(rng, g, shapes, cols, margin=margin)
    if pos is None:
        return None
    H, W = dims(g)
    idx = rng.randrange(k)
    sh, (r0, c0) = shapes[idx], pos[idx]
    placed = [(r0 + r, c0 + c) for r, c in sh]
    rng.shuffle(placed)
    for (pr, pc) in placed:
        done = False
        for dr, dc in _DIRS4:
            nr, nc = pr + dr, pc + dc
            if 0 <= nr < H and 0 <= nc < W and g[nr][nc] == 0:
                g[nr][nc] = ANCHOR; done = True
                break
        if done:
            return g
    return None


def _find_anchor(g, col=ANCHOR):
    pts = cells(g, lambda v: v == col)
    return pts[0] if len(pts) == 1 else None


def _dots(g):
    return cells(g, lambda v: v == ANCHOR)


def _dot_for(obj, dots):
    objset = set(obj)
    for (dr, dc) in dots:
        for ddr, ddc in _DIRS4:
            if (dr + ddr, dc + ddc) in objset:
                return (dr, dc)
    return None


def _translate_clip(g, dr, dc, bg=0):
    h, w = dims(g)
    out = blank(h, w, bg)
    for r in range(h):
        for c in range(w):
            if g[r][c] == bg:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w:
                out[nr][nc] = g[r][c]
    return out


def _roll(g, dr, dc):
    h, w = dims(g)
    out = blank(h, w)
    for r in range(h):
        for c in range(w):
            out[(r + dr) % h][(c + dc) % w] = g[r][c]
    return out


def _mode_block(vals):
    cnt = {}
    for v in vals:
        cnt[v] = cnt.get(v, 0) + 1
    return max(cnt.items(), key=lambda kv: (kv[1], kv[0] != 0))[0]


def _downsample_mode(g, factor):
    h, w = dims(g)
    if h % factor or w % factor:
        return None
    oh, ow = h // factor, w // factor
    out = blank(oh, ow)
    for r in range(oh):
        for c in range(ow):
            vals = [g[r * factor + dr][c * factor + dc] for dr in range(factor) for dc in range(factor)]
            out[r][c] = _mode_block(vals)
    return out


def _resize_nn(g, oh, ow):
    h, w = dims(g)
    out = blank(oh, ow)
    for r in range(oh):
        for c in range(ow):
            out[r][c] = g[min(h - 1, r * h // oh)][min(w - 1, c * w // ow)]
    return out


# ---- 1-5 translate (clip) to a corner or the centre ------------------------------------------
def gi_anchor_basic(rng):
    return _scene_with_anchor(rng)


def tf_translate_tl(g):
    a = _find_anchor(g)
    if a is None:
        return None
    return _translate_clip(g, -a[0], -a[1])


rule("anchor_translate_top_left", "The scene slides so the grey anchor cell lands in the top-left corner; cells pushed off an edge are dropped.", gi_anchor_basic, tf_translate_tl)


def tf_translate_tr(g):
    a = _find_anchor(g)
    if a is None:
        return None
    H, W = dims(g)
    return _translate_clip(g, -a[0], (W - 1) - a[1])


rule("anchor_translate_top_right", "The scene slides so the grey anchor cell lands in the top-right corner; cells pushed off an edge are dropped.", gi_anchor_basic, tf_translate_tr)


def tf_translate_bl(g):
    a = _find_anchor(g)
    if a is None:
        return None
    H, W = dims(g)
    return _translate_clip(g, (H - 1) - a[0], -a[1])


rule("anchor_translate_bottom_left", "The scene slides so the grey anchor cell lands in the bottom-left corner; cells pushed off an edge are dropped.", gi_anchor_basic, tf_translate_bl)


def tf_translate_br(g):
    a = _find_anchor(g)
    if a is None:
        return None
    H, W = dims(g)
    return _translate_clip(g, (H - 1) - a[0], (W - 1) - a[1])


rule("anchor_translate_bottom_right", "The scene slides so the grey anchor cell lands in the bottom-right corner; cells pushed off an edge are dropped.", gi_anchor_basic, tf_translate_br)


def tf_translate_centre(g):
    a = _find_anchor(g)
    if a is None:
        return None
    H, W = dims(g)
    return _translate_clip(g, H // 2 - a[0], W // 2 - a[1])


rule("anchor_translate_centre", "The scene slides so the grey anchor cell lands on the grid's centre cell; cells pushed off an edge are dropped.", gi_anchor_basic, tf_translate_centre)


# ---- 6-8 toroidal wrap (nothing is lost) ------------------------------------------------------
def tf_wrap_origin(g):
    a = _find_anchor(g)
    if a is None:
        return None
    return _roll(g, -a[0], -a[1])


rule("anchor_wrap_to_origin", "The whole scene wraps around toroidally, rolling rows and columns until the grey anchor sits at the top-left origin.", gi_anchor_basic, tf_wrap_origin)


def tf_wrap_centre(g):
    a = _find_anchor(g)
    if a is None:
        return None
    H, W = dims(g)
    return _roll(g, H // 2 - a[0], W // 2 - a[1])


rule("anchor_wrap_to_centre", "The whole scene wraps around toroidally, rolling rows and columns until the grey anchor sits on the grid's centre cell.", gi_anchor_basic, tf_wrap_centre)


def tf_wrap_br(g):
    a = _find_anchor(g)
    if a is None:
        return None
    H, W = dims(g)
    return _roll(g, (H - 1) - a[0], (W - 1) - a[1])


rule("anchor_wrap_to_bottom_right", "The whole scene wraps around toroidally, rolling rows and columns until the grey anchor sits at the bottom-right corner.", gi_anchor_basic, tf_wrap_br)


# ---- 9-12 a two-cell (or three-cell) grey glyph sets the scene's rotation ---------------------
def _glyph_dir(g):
    piv = cells(g, lambda v: v == ANCHOR)
    arm = cells(g, lambda v: v == ARM)
    if len(piv) != 1 or len(arm) != 1:
        return None
    (pr, pc), (ar, ac) = piv[0], arm[0]
    return (ar - pr, ac - pc)


def _rotate_until(g, target, max_tries=4):
    cur = g
    for _ in range(max_tries):
        d = _glyph_dir(cur)
        if d is None:
            return None
        if d == target:
            return cur
        cur = rot90(cur)
    return None


def gi_glyph1(rng):
    return _scene_with_glyph(rng, arms=1)


rule("rotate_scene_arm_up", "The grey pivot cell has one yellow-brown arm cell beside it; the whole scene is rotated in 90-degree steps until that arm points straight up.", gi_glyph1, lambda g: _rotate_until(g, (-1, 0)))
rule("rotate_scene_arm_down", "The grey pivot cell has one yellow-brown arm cell beside it; the whole scene is rotated in 90-degree steps until that arm points straight down.", gi_glyph1, lambda g: _rotate_until(g, (1, 0)))
rule("rotate_scene_arm_left", "The grey pivot cell has one yellow-brown arm cell beside it; the whole scene is rotated in 90-degree steps until that arm points left.", gi_glyph1, lambda g: _rotate_until(g, (0, -1)))


def _glyph_dirs2(g):
    piv = cells(g, lambda v: v == ANCHOR)
    arm = cells(g, lambda v: v == ARM)
    if len(piv) != 1 or len(arm) != 2:
        return None
    (pr, pc) = piv[0]
    return frozenset((r - pr, c - pc) for r, c in arm)


def _rotate_until2(g, target, max_tries=4):
    cur = g
    for _ in range(max_tries):
        d = _glyph_dirs2(cur)
        if d is None:
            return None
        if d == target:
            return cur
        cur = rot90(cur)
    return None


def gi_glyph2(rng):
    return _scene_with_glyph(rng, arms=2)


def tf_elbow(g):
    return _rotate_until2(g, frozenset({(-1, 0), (0, 1)}))


rule("rotate_scene_elbow_to_canonical", "The grey pivot cell has two yellow-brown arm cells forming an L; the whole scene is rotated in 90-degree steps until the L opens up and to the right.", gi_glyph2, tf_elbow)


# ---- 13-16 mirror so the anchor lands in a given half -----------------------------------------
def gi_mirror_left(rng):
    return _scene_anchor_region(rng, lambda r, c, H, W: c >= (W + 1) // 2)


rule("mirror_anchor_to_left_half", "The grey anchor starts in the right half; the scene is mirrored left-right so the anchor ends up in the left half.", gi_mirror_left, flip_h, primitive=True)
def gi_mirror_right(rng):
    return _scene_anchor_region(rng, lambda r, c, H, W: c < W // 2)


# mirror_anchor_to_right_half dropped 2026-10-12 (trio review: behavioural duplicate or one global operation)
def gi_mirror_top(rng):
    return _scene_anchor_region(rng, lambda r, c, H, W: r >= (H + 1) // 2)


# mirror_anchor_to_top_half dropped 2026-10-12 (trio review: behavioural duplicate or one global operation)
def gi_mirror_bottom(rng):
    return _scene_anchor_region(rng, lambda r, c, H, W: r < H // 2)


rule("mirror_anchor_to_bottom_half", "The grey anchor starts in the top half; the scene is mirrored top-bottom so the anchor ends up in the bottom half.", gi_mirror_bottom, flip_v, primitive=True)
# ---- 17-21 crop to something keyed by the anchor -----------------------------------------------
def gi_frame(rng):
    h, w = _dims_mixed(rng, lo=10, hi=20)
    g = blank(h, w)
    k = rng.randint(2, 5)
    shapes = [random_shape(rng, rng.randint(2, 6)) for _ in range(k)]
    cols = [rng.choice([c for c in COLOURS if c != ANCHOR]) for _ in range(k)]
    pos = place_shapes(rng, g, shapes, cols, margin=1)
    if pos is None:
        return None
    H, W = dims(g)
    r0, r1 = sorted(rng.sample(range(H), 2))
    c0, c1 = sorted(rng.sample(range(W), 2))
    if r1 - r0 < 2 or c1 - c0 < 2 or g[r0][c0] != 0 or g[r1][c1] != 0:
        return None
    g[r0][c0] = ANCHOR; g[r1][c1] = ANCHOR
    return g


def tf_frame(g):
    dots = cells(g, lambda v: v == ANCHOR)
    if len(dots) != 2:
        return None
    (r0, c0), (r1, c1) = dots
    r0, r1 = min(r0, r1), max(r0, r1); c0, c1 = min(c0, c1), max(c0, c1)
    return crop(g, r0, c0, r1, c1)


rule("crop_to_anchor_frame", "Two grey corner markers pin opposite corners of a frame; the output is the scene cropped to that frame.", gi_frame, tf_frame)

_RAD18 = 3


def gi_window(rng):
    h, w = _dims_mixed(rng, lo=12, hi=20)
    g = blank(h, w)
    k = rng.randint(2, 5)
    shapes = [random_shape(rng, rng.randint(2, 7)) for _ in range(k)]
    cols = [rng.choice([c for c in COLOURS if c != ANCHOR]) for _ in range(k)]
    pos = place_shapes(rng, g, shapes, cols, margin=1)
    if pos is None:
        return None
    H, W = dims(g)
    free = [(r, c) for r in range(_RAD18, H - _RAD18) for c in range(_RAD18, W - _RAD18) if g[r][c] == 0]
    if not free:
        return None
    ar, ac = rng.choice(free)
    g[ar][ac] = ANCHOR
    return g


def tf_window(g):
    a = _find_anchor(g)
    if a is None:
        return None
    return crop(g, a[0] - _RAD18, a[1] - _RAD18, a[0] + _RAD18, a[1] + _RAD18)


rule("crop_window_around_anchor", "The output is a fixed-size square window cropped out of the scene, centred on the grey anchor cell.", gi_window, tf_window)


def gi_quadcrop(rng):
    return _scene_with_anchor(rng, lo=10, hi=20)


def tf_quadcrop(g):
    a = _find_anchor(g)
    if a is None:
        return None
    H, W = dims(g)
    mr, mc = H // 2, W // 2
    r0, r1 = (0, mr - 1) if a[0] < mr else (mr, H - 1)
    c0, c1 = (0, mc - 1) if a[1] < mc else (mc, W - 1)
    if r1 < r0 or c1 < c0:
        return None
    return crop(g, r0, c0, r1, c1)


rule("crop_to_anchor_quadrant", "The grid is split into four quadrants; the output is the one quadrant that contains the grey anchor cell.", gi_quadcrop, tf_quadcrop)


def gi_halfcrop(rng):
    return _scene_with_anchor(rng, lo=10, hi=20)


def tf_half_h(g):
    a = _find_anchor(g)
    if a is None:
        return None
    H, W = dims(g)
    mc = W // 2
    return crop(g, 0, 0, H - 1, mc - 1) if a[1] < mc else crop(g, 0, mc, H - 1, W - 1)


rule("crop_to_half_containing_anchor_horizontal", "The grid is split into a left half and a right half; the output is whichever half contains the grey anchor cell.", gi_halfcrop, tf_half_h)


def tf_half_v(g):
    a = _find_anchor(g)
    if a is None:
        return None
    H, W = dims(g)
    mr = H // 2
    return crop(g, 0, 0, mr - 1, W - 1) if a[0] < mr else crop(g, mr, 0, H - 1, W - 1)


rule("crop_to_half_containing_anchor_vertical", "The grid is split into a top half and a bottom half; the output is whichever half contains the grey anchor cell.", gi_halfcrop, tf_half_v)


# ---- 22-24 scale the scene using the anchor's own size as the factor --------------------------
def gi_blockscale(rng):
    k = rng.randint(2, 5)
    max_m = 30 // k
    if rng.random() < 0.4:
        mh = rng.randint(max(3, max_m - 1), max_m); mw = rng.randint(max(3, max_m - 1), max_m)
    else:
        mh = rng.randint(3, max(3, max_m // 2)); mw = rng.randint(3, max(3, max_m // 2))
    H, W = mh * k, mw * k
    g = blank(H, W)
    n = rng.randint(2, 4)
    shapes = [random_shape(rng, rng.randint(2, 2 * k)) for _ in range(n)]
    cols = [rng.choice([c for c in COLOURS if c != ANCHOR]) for _ in range(n)]
    pos = place_shapes(rng, g, shapes, cols, margin=1)
    if pos is None:
        return None
    free_blocks = [(br, bc) for br in range(mh) for bc in range(mw)
                   if all(g[br * k + dr][bc * k + dc] == 0 for dr in range(k) for dc in range(k))]
    if not free_blocks:
        return None
    br, bc = rng.choice(free_blocks)
    for dr in range(k):
        for dc in range(k):
            g[br * k + dr][bc * k + dc] = ANCHOR
    return g


def tf_blockscale(g):
    comps = [c for c in components(g, ANCHOR, conn8=False) if len(c) > 1]
    if len(comps) != 1:
        return None
    o = comps[0]
    r0, c0, r1, c1 = bbox(o)
    k1, k2 = r1 - r0 + 1, c1 - c0 + 1
    if k1 != k2 or len(o) != k1 * k2:
        return None
    return _downsample_mode(g, k1)


rule("scale_down_to_anchor_block_size", "A solid grey square sits somewhere in the scene; the whole grid is shrunk block by block, using that square's own side length as the block size, so the square becomes one cell.", gi_blockscale, tf_blockscale)


def gi_ruler(rng):
    k = rng.randint(2, 5)
    max_m = 30 // k
    if rng.random() < 0.4:
        mh = rng.randint(max(3, max_m - 1), max_m); mw = rng.randint(max(3, max_m - 1), max_m)
    else:
        mh = rng.randint(3, max(3, max_m // 2)); mw = rng.randint(3, max(3, max_m // 2))
    H, W = mh * k, mw * k
    g = blank(H, W)
    n = rng.randint(2, 4)
    shapes = [random_shape(rng, rng.randint(2, 2 * k)) for _ in range(n)]
    cols = [rng.choice([c for c in COLOURS if c != ANCHOR]) for _ in range(n)]
    pos = place_shapes(rng, g, shapes, cols, margin=1)
    if pos is None:
        return None
    free_rows = [(r, c) for r in range(H) for c in range(W - k + 1)
                 if all(g[r][c + dc] == 0 for dc in range(k))]
    if not free_rows:
        return None
    r, c = rng.choice(free_rows)
    for dc in range(k):
        g[r][c + dc] = ANCHOR
    return g


def tf_ruler(g):
    H, W = dims(g)
    runs = []
    for r in range(H):
        c = 0
        while c < W:
            if g[r][c] == ANCHOR:
                c0 = c
                while c < W and g[r][c] == ANCHOR:
                    c += 1
                runs.append(c - c0)
            else:
                c += 1
    if len(runs) != 1 or runs[0] < 2:
        return None
    return _downsample_mode(g, runs[0])


rule("scale_down_by_anchor_ruler_length", "A straight run of grey cells (a ruler) sits somewhere in the scene; the whole grid is shrunk block by block using the ruler's own length as the block size.", gi_ruler, tf_ruler)


def gi_framescale(rng):
    h, w = _dims_mixed(rng, lo=14, hi=24)
    g = blank(h, w)
    k = rng.randint(2, 5)
    shapes = [random_shape(rng, rng.randint(2, 7)) for _ in range(k)]
    cols = [rng.choice([c for c in COLOURS if c != ANCHOR]) for _ in range(k)]
    pos = place_shapes(rng, g, shapes, cols, margin=1)
    if pos is None:
        return None
    H, W = dims(g)
    if H < 7 or W < 7:
        return None
    r0, r1 = sorted(rng.sample(range(2, H - 2), 2))
    c0, c1 = sorted(rng.sample(range(2, W - 2), 2))
    if r1 - r0 < 2 or c1 - c0 < 2 or g[r0][c0] != 0 or g[r1][c1] != 0:
        return None
    g[r0][c0] = ANCHOR; g[r1][c1] = ANCHOR
    return g


def tf_framescale(g):
    dots = cells(g, lambda v: v == ANCHOR)
    if len(dots) != 2:
        return None
    (r0, c0), (r1, c1) = dots
    r0, r1 = min(r0, r1), max(r0, r1); c0, c1 = min(c0, c1), max(c0, c1)
    fh, fw = r1 - r0 + 1, c1 - c0 + 1
    H, W = dims(g)
    if fh >= H and fw >= W:
        return None
    if fh < 2 or fw < 2:
        return None
    return _resize_nn(g, fh, fw)


rule("scale_scene_to_anchor_frame_size", "Two grey corner markers pin a rectangular frame; the whole scene is resampled so its output size matches that frame's dimensions.", gi_framescale, tf_framescale)


# ---- 25-28 recolour keyed by the anchor (digit codes) ------------------------------------------
def tf_recolour_rel(g):
    H, W = dims(g)
    dots = cells(g, lambda v: v == ANCHOR)
    if len(dots) != 1:
        return None
    d = dots[0]
    objs = [o for o in objects(g, 0) if g[o[0][0]][o[0][1]] != ANCHOR]
    A = None
    for o in objs:
        oset = set(o)
        if any((d[0] + dr, d[1] + dc) in oset for dr, dc in _DIRS4):
            A = g[o[0][0]][o[0][1]]
            break
    if A is None:
        return None
    out = copy(g)
    for r in range(H):
        for c in range(W):
            v = g[r][c]
            if v != 0:
                out[r][c] = ((v - A - 1) % 9) + 1
    return out


rule("recolour_relative_to_anchor_colour", "A grey dot touches one object, naming its colour as the anchor value; every colour in the scene is shifted cyclically so the anchor's colour becomes 1.", _scene_one_marked, tf_recolour_rel, digits=True)


def tf_band(g):
    a = _find_anchor(g)
    if a is None:
        return None
    H, W = dims(g)
    out = copy(g)
    for r in range(H):
        for c in range(W):
            if g[r][c] != 0:
                d = max(abs(r - a[0]), abs(c - a[1]))
                out[r][c] = min(d // 2 + 1, 9)
    return out


rule("recolour_by_distance_band_from_anchor", "Every coloured cell is recoloured by how many steps (in bands of two) it sits from the grey anchor cell.", gi_anchor_basic, tf_band, digits=True)


def gi_rank(rng):
    return _scene_with_anchor(rng, k_lo=3, k_hi=6)


def tf_rank(g):
    a = _find_anchor(g)
    if a is None:
        return None
    objs = [o for o in objects(g, 0) if g[o[0][0]][o[0][1]] != ANCHOR]
    if len(objs) < 2:
        return None
    def dist(o):
        return min(max(abs(r - a[0]), abs(c - a[1])) for r, c in o)
    ranked = sorted(objs, key=dist)
    out = copy(g)
    for i, o in enumerate(ranked):
        rank = min(i + 1, 9)
        for r, c in o:
            out[r][c] = rank
    return out


rule("recolour_objects_rank_by_proximity_to_anchor", "Every object is recoloured by its rank in distance to the grey anchor cell: 1 for the nearest, 2 for the next, and so on.", gi_rank, tf_rank, digits=True)


def gi_adj(rng):
    return _scene_with_anchor(rng, k_lo=3, k_hi=6, margin=0)


def tf_adj(g):
    a = _find_anchor(g)
    if a is None:
        return None
    objs = [o for o in objects(g, 0) if g[o[0][0]][o[0][1]] != ANCHOR]
    if len(objs) < 2:
        return None
    out = copy(g)
    touch_any = far_any = False
    for o in objs:
        touching = any(max(abs(r - a[0]), abs(c - a[1])) <= 1 for r, c in o)
        touch_any = touch_any or touching
        far_any = far_any or not touching
        v = 1 if touching else 2
        for r, c in o:
            out[r][c] = v
    if not (touch_any and far_any):
        return None
    return out


rule("recolour_by_anchor_adjacency", "Every object touching the grey anchor cell is recoloured 1; every object not touching it is recoloured 2.", gi_adj, tf_adj, digits=True)


# ---- 29-30 offsets from the anchor -------------------------------------------------------------
def gi_quad(rng):
    return _scene_with_anchor(rng, k_lo=3, k_hi=6)


def tf_quad(g):
    a = _find_anchor(g)
    if a is None:
        return None
    objs = [o for o in objects(g, 0) if g[o[0][0]][o[0][1]] != ANCHOR]
    if len(objs) < 2:
        return None
    out = copy(g)
    seen = set()
    for o in objs:
        r0, c0, r1, c1 = bbox(o)
        cr, cc = (r0 + r1) / 2, (c0 + c1) / 2
        up = cr <= a[0]; left = cc <= a[1]
        code = (1 if up else 3) + (0 if left else 1)
        seen.add(code)
        for r, c in o:
            out[r][c] = code
    if len(seen) < 2:
        return None
    return out


rule("offset_quadrant_from_anchor", "Every object is recoloured by which quadrant it sits in relative to the grey anchor cell: 1 up-left, 2 up-right, 3 down-left, 4 down-right.", gi_quad, tf_quad, digits=True)


def gi_ring(rng):
    return _scene_with_anchor(rng, k_lo=2, k_hi=4)


def tf_ring(g):
    a = _find_anchor(g)
    if a is None:
        return None
    H, W = dims(g)
    out = copy(g)
    for r in range(H):
        for c in range(W):
            if g[r][c] == 0:
                d = max(abs(r - a[0]), abs(c - a[1]))
                out[r][c] = (d % 9) + 1
    return out


rule("distance_rings_from_anchor", "The background is repainted as concentric rings of colour, cycling through nine bands with distance from the grey anchor cell, while existing objects are left untouched.", gi_ring, tf_ring, digits=True)


# ---- 31-34 align each object's own anchor dot --------------------------------------------------
def gi_dots(rng):
    return _scene_with_dots(rng)


def tf_dots_centre_row(g):
    H, W = dims(g)
    dots = _dots(g)
    objs = [o for o in objects(g, 0) if g[o[0][0]][o[0][1]] != ANCHOR]
    if len(objs) < 2:
        return None
    out = blank(H, W)
    centre = H // 2
    moved = False
    for o in objs:
        d = _dot_for(o, dots)
        if d is None:
            return None
        rs = [r for r, _ in o] + [d[0]]
        lo, hi = min(rs), max(rs)
        dr = centre - d[0]
        dr = max(-lo, min(H - 1 - hi, dr))
        moved = moved or dr != 0
        for (r, c) in o:
            nr = r + dr
            if 0 <= nr < H:
                out[nr][c] = g[r][c]
        nr_d = d[0] + dr
        if 0 <= nr_d < H:
            out[nr_d][d[1]] = ANCHOR
    return out if moved else None


rule("align_object_dots_to_centre_row", "Every object has its own grey anchor dot touching it; each object slides vertically so that dot lands on the grid's centre row.", gi_dots, tf_dots_centre_row)


def tf_dots_centre_col(g):
    H, W = dims(g)
    dots = _dots(g)
    objs = [o for o in objects(g, 0) if g[o[0][0]][o[0][1]] != ANCHOR]
    if len(objs) < 2:
        return None
    out = blank(H, W)
    centre = W // 2
    moved = False
    for o in objs:
        d = _dot_for(o, dots)
        if d is None:
            return None
        cs = [c for _, c in o] + [d[1]]
        lo, hi = min(cs), max(cs)
        dc = centre - d[1]
        dc = max(-lo, min(W - 1 - hi, dc))
        moved = moved or dc != 0
        for (r, c) in o:
            nc = c + dc
            if 0 <= nc < W:
                out[r][nc] = g[r][c]
        nc_d = d[1] + dc
        if 0 <= nc_d < W:
            out[d[0]][nc_d] = ANCHOR
    return out if moved else None


rule("align_object_dots_to_centre_col", "Every object has its own grey anchor dot touching it; each object slides horizontally so that dot lands on the grid's centre column.", gi_dots, tf_dots_centre_col)


def tf_dots_common_col(g):
    H, W = dims(g)
    dots = _dots(g)
    objs = [o for o in objects(g, 0) if g[o[0][0]][o[0][1]] != ANCHOR]
    if len(objs) < 2:
        return None
    pairs = [(o, _dot_for(o, dots)) for o in objs]
    if any(d is None for _, d in pairs):
        return None
    target = min(d[1] for _, d in pairs)
    out = blank(H, W)
    moved = False
    for o, d in pairs:
        cs = [c for _, c in o] + [d[1]]
        lo, hi = min(cs), max(cs)
        dc = max(-lo, min(W - 1 - hi, target - d[1]))
        moved = moved or dc != 0
        for (r, c) in o:
            nc = c + dc
            if 0 <= nc < W:
                out[r][nc] = g[r][c]
        nc_d = d[1] + dc
        if 0 <= nc_d < W:
            out[d[0]][nc_d] = ANCHOR
    return out if moved else None


rule("align_object_dots_to_common_column", "Every object has its own grey anchor dot touching it; every object slides horizontally so that all the dots line up in one shared column.", gi_dots, tf_dots_common_col)


def tf_dots_common_row(g):
    H, W = dims(g)
    dots = _dots(g)
    objs = [o for o in objects(g, 0) if g[o[0][0]][o[0][1]] != ANCHOR]
    if len(objs) < 2:
        return None
    pairs = [(o, _dot_for(o, dots)) for o in objs]
    if any(d is None for _, d in pairs):
        return None
    target = max(d[0] for _, d in pairs)
    out = blank(H, W)
    moved = False
    for o, d in pairs:
        rs = [r for r, _ in o] + [d[0]]
        lo, hi = min(rs), max(rs)
        dr = max(-lo, min(H - 1 - hi, target - d[0]))
        moved = moved or dr != 0
        for (r, c) in o:
            nr = r + dr
            if 0 <= nr < H:
                out[nr][c] = g[r][c]
        nr_d = d[0] + dr
        if 0 <= nr_d < H:
            out[nr_d][d[1]] = ANCHOR
    return out if moved else None


rule("align_object_dots_to_common_row", "Every object has its own grey anchor dot touching it; every object slides vertically so that all the dots line up in one shared row.", gi_dots, tf_dots_common_row)


# ---- 35-36 single-axis shift ---------------------------------------------------------------
def tf_col_to_edge(g):
    a = _find_anchor(g)
    if a is None:
        return None
    return _translate_clip(g, 0, -a[1])


rule("anchor_column_to_left_edge", "The scene slides sideways only, so the column holding the grey anchor cell becomes the left edge; rows are not shifted.", gi_anchor_basic, tf_col_to_edge)


def tf_row_to_edge(g):
    a = _find_anchor(g)
    if a is None:
        return None
    return _translate_clip(g, -a[0], 0)


rule("anchor_row_to_top_edge", "The scene slides up or down only, so the row holding the grey anchor cell becomes the top edge; columns are not shifted.", gi_anchor_basic, tf_row_to_edge)


# ---- 37, 39, 40 symmetry operations keyed by the anchor's position -----------------------------
def gi_rot180(rng):
    h, w = _dims_mixed(rng, lo=9, hi=20)
    g = blank(h, w)
    k = rng.randint(2, 5)
    shapes = [random_shape(rng, rng.randint(2, 7)) for _ in range(k)]
    cols = [rng.choice([c for c in COLOURS if c != ANCHOR]) for _ in range(k)]
    pos = place_shapes(rng, g, shapes, cols, margin=1)
    if pos is None:
        return None
    H, W = dims(g)
    rad = 2
    free = [(r, c) for r in range(rad, H - rad) for c in range(rad, W - rad) if g[r][c] == 0]
    if not free:
        return None
    ar, ac = rng.choice(free)
    g[ar][ac] = ANCHOR
    return g


def tf_rot180(g):
    a = _find_anchor(g)
    if a is None:
        return None
    H, W = dims(g)
    rad = min(a[0], a[1], H - 1 - a[0], W - 1 - a[1])
    if rad < 2:
        return None
    window = crop(g, a[0] - rad, a[1] - rad, a[0] + rad, a[1] + rad)
    window = rot90(rot90(window))
    out = copy(g)
    paste(out, window, a[0] - rad, a[1] - rad)
    return out


rule("rotate_180_about_anchor", "A square window around the grey anchor cell, as large as fits on every side, is rotated 180 degrees in place about that cell.", gi_rot180, tf_rot180)


def gi_diag(rng):
    return _scene_anchor_region(rng, lambda r, c, H, W: r * W > c * H, lo=10, hi=20)


def tf_diag(g):
    a = _find_anchor(g)
    if a is None:
        return None
    H, W = dims(g)
    if a[0] * W <= a[1] * H:
        return None
    return transpose(g)


rule("mirror_scene_based_on_anchor_corner", "The grey anchor starts below the main diagonal; the scene is transposed across that diagonal so the anchor moves toward the upper triangle.", gi_diag, tf_diag, primitive=True)
def gi_reflectrow(rng):
    h, w = _dims_mixed(rng, lo=9, hi=20)
    g = blank(h, w)
    k = rng.randint(2, 5)
    shapes = [random_shape(rng, rng.randint(2, 7)) for _ in range(k)]
    cols = [rng.choice([c for c in COLOURS if c != ANCHOR]) for _ in range(k)]
    pos = place_shapes(rng, g, shapes, cols, margin=1)
    if pos is None:
        return None
    H, W = dims(g)
    rad_min = 2
    if H - 2 * rad_min < 1:
        return None
    free = [(r, c) for r in range(rad_min, H - rad_min) for c in range(W) if g[r][c] == 0]
    if not free:
        return None
    ar, ac = rng.choice(free)
    g[ar][ac] = ANCHOR
    return g


def tf_reflectrow(g):
    a = _find_anchor(g)
    if a is None:
        return None
    H, W = dims(g)
    rad = min(a[0], H - 1 - a[0])
    if rad < 2:
        return None
    window = crop(g, a[0] - rad, 0, a[0] + rad, W - 1)
    return flip_v(window)


rule("reflect_scene_about_anchor_row", "A horizontal band around the grey anchor cell, as tall as fits above and below it, is cropped out and flipped top-to-bottom.", gi_reflectrow, tf_reflectrow)


# ---- 38 a lone single cell's own colour value sets the crop radius (digits) --------------------
def gi_radius(rng):
    h, w = _dims_mixed(rng, lo=10, hi=20)
    g = blank(h, w)
    k = rng.randint(2, 4)
    shapes = [random_shape(rng, rng.randint(4, 9)) for _ in range(k)]
    cols = [rng.choice(COLOURS) for _ in range(k)]
    pos = place_shapes(rng, g, shapes, cols, margin=2)
    if pos is None:
        return None
    H, W = dims(g)
    n = rng.randint(2, 4)
    free = [(r, c) for r in range(n, H - n) for c in range(n, W - n) if g[r][c] == 0]
    if not free:
        return None
    ar, ac = rng.choice(free)
    g[ar][ac] = n
    return g


def tf_radius(g):
    comps = components(g, lambda v: v != 0, conn8=False)
    lone = [o[0] for o in comps if len(o) == 1]
    if len(lone) != 1:
        return None
    (ar, ac) = lone[0]
    n = g[ar][ac]
    if not (1 <= n <= 9):
        return None
    H, W = dims(g)
    r0, c0, r1, c1 = ar - n, ac - n, ar + n, ac + n
    if r0 < 0 or c0 < 0 or r1 > H - 1 or c1 > W - 1:
        return None
    if r1 - r0 < 2 or c1 - c0 < 2:
        return None
    return crop(g, r0, c0, r1, c1)


rule("scene_window_sized_by_anchor_radius", "One lone cell stands apart from every other object; its own colour value is a radius, and the output is the square window of that radius cropped around it.", gi_radius, tf_radius, digits=True)
