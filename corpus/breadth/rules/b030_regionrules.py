# b030_regionrules.py -- DIFFERENT RULES IN DIFFERENT REGIONS: a separator (line, frame, diagonal, lattice,
# marker) splits the grid and each region gets its own fixed operation. Separators and markers are grey (5);
# content never uses 5, so a full grey row/column or a grey component is the separator by construction.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

SEP = 5


# ---------------------------------------------------------------- shared helpers
def _one(rng, lo, hi, big=0.38):
    """One side length; a good third of the time in the 21-30 band."""
    return rng.randint(21, 30) if rng.random() < big else rng.randint(lo, hi)


def _sz(rng, lo=8, hi=20):
    if rng.random() < 0.38:
        return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _pal(rng, k, extra=()):
    return colours(rng, k, exclude=(0, SEP) + tuple(extra))


def _scatter(rng, g, r0, c0, r1, c1, cols, density=0.3):
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if rng.random() < density:
                g[r][c] = rng.choice(cols)
    return g


def _shapes_in(rng, g, r0, c0, r1, c1, k, n_lo=3, n_hi=7, cols=None, margin=1, shapes=None, two_tone=False):
    """Place k random shapes (or the given shapes) inside the rectangle; False if they did not fit."""
    sub = blank(r1 - r0 + 1, c1 - c0 + 1)
    cols = cols or _pal(rng, 4)
    shapes = shapes or [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    pos = place_shapes(rng, sub, shapes, [rng.choice(cols) for _ in shapes], margin=margin)
    if pos is None:
        return False
    if two_tone:
        for sh, (y, x) in zip(shapes, pos):
            if len(sh) > 2 and rng.random() < 0.6:
                other = rng.choice(cols)
                for r, c in rng.sample(sh, len(sh) // 2):
                    sub[y + r][x + c] = other
    paste(g, sub, r0, c0, transparent=0)
    return True


def _rect_shape(h, w, hollow=False):
    return [(r, c) for r in range(h) for c in range(w) if not hollow or r in (0, h - 1) or c in (0, w - 1)]


def _rects(rng, k, lo=2, hi=5, hollow=False):
    return [_rect_shape(rng.randint(lo, hi), rng.randint(lo, hi), hollow) for _ in range(k)]


def _full_cols(g, col=SEP):
    H, W = dims(g)
    return [c for c in range(W) if all(g[r][c] == col for r in range(H))]


def _full_rows(g, col=SEP):
    return [r for r, row in enumerate(g) if all(v == col for v in row)]


def _full_cols_any(g):
    H, W = dims(g)
    return [c for c in range(W) if g[0][c] and all(g[r][c] == g[0][c] for r in range(H))]


def _full_rows_any(g):
    return [r for r, row in enumerate(g) if row[0] and all(v == row[0] for v in row)]


def _spans(idx, n):
    """The index ranges between separators idx within 0..n-1."""
    out, s = [], 0
    for i in list(idx) + [n]:
        if i > s:
            out.append((s, i - 1))
        s = i + 1
    return out


def _split_v(g):
    cs = _full_cols(g); H, W = dims(g)
    if len(cs) != 1 or cs[0] in (0, W - 1):
        return None
    return crop(g, 0, 0, H - 1, cs[0] - 1), crop(g, 0, cs[0] + 1, H - 1, W - 1)


def _join_v(parts):
    out = [list(r) for r in parts[0]]
    for p in parts[1:]:
        out = [a + [SEP] + b for a, b in zip(out, p)]
    return out


def _split_h(g):
    rs = _full_rows(g); H, W = dims(g)
    if len(rs) != 1 or rs[0] in (0, H - 1):
        return None
    return crop(g, 0, 0, rs[0] - 1, W - 1), crop(g, rs[0] + 1, 0, H - 1, W - 1)


def _join_h(parts):
    out = []
    for i, p in enumerate(parts):
        if i:
            out.append([SEP] * len(p[0]))
        out += [list(r) for r in p]
    return out


def _vline_grid(rng, lo=6, hi=20):
    """Grid with one full grey column at least 3 from either edge; returns g, c."""
    h, w = _sz(rng, lo, hi); w = max(w, 8); g = blank(h, w)
    c = rng.randint(3, w - 4)
    for r in range(h):
        g[r][c] = SEP
    return g, c


def _hline_grid(rng, lo=6, hi=20):
    h, w = _sz(rng, lo, hi); h = max(h, 8); g = blank(h, w)
    r = rng.randint(3, h - 4)
    g[r] = [SEP] * w
    return g, r


def _panel_dims(rng):
    """k equal panels of width pw plus k-1 separators, a third of the time 21-30 wide in total."""
    if rng.random() < 0.38:
        k = rng.choice([2, 3, 4]); pw = {2: rng.randint(10, 14), 3: rng.randint(7, 9), 4: rng.randint(5, 6)}[k]
    else:
        k = rng.choice([2, 3, 4]); pw = {2: rng.randint(4, 9), 3: rng.randint(4, 6), 4: 4}[k]
    return k, pw


def _panels_v(rng, hlo=5, hhi=20):
    """Vertical panels (side by side); returns g, [(c0, c1)], H."""
    k, pw = _panel_dims(rng); H = _one(rng, hlo, hhi); W = k * pw + k - 1; g = blank(H, W)
    for i in range(1, k):
        for r in range(H):
            g[r][i * (pw + 1) - 1] = SEP
    return g, [(i * (pw + 1), i * (pw + 1) + pw - 1) for i in range(k)], H


def _panels_h(rng, wlo=5, whi=20):
    """Horizontal panels (stacked); returns g, [(r0, r1)], W."""
    k, ph = _panel_dims(rng); W = _one(rng, wlo, whi); H = k * ph + k - 1; g = blank(H, W)
    for i in range(1, k):
        g[i * (ph + 1) - 1] = [SEP] * W
    return g, [(i * (ph + 1), i * (ph + 1) + ph - 1) for i in range(k)], W


def _cross(rng, square=False):
    """Grey cross through the middle; returns g and the four quadrant boxes TL, TR, BL, BR."""
    a = _one(rng, 3, 9, 0.38) if not square else None
    if square:
        s = rng.randint(10, 14) if rng.random() < 0.38 else rng.randint(3, 9); a = b = s
    else:
        a = rng.randint(10, 14) if rng.random() < 0.38 else rng.randint(3, 9)
        b = rng.randint(10, 14) if rng.random() < 0.38 else rng.randint(3, 9)
    H, W = 2 * a + 1, 2 * b + 1; g = blank(H, W)
    g[a] = [SEP] * W
    for r in range(H):
        g[r][b] = SEP
    return g, [(0, 0, a - 1, b - 1), (0, b + 1, a - 1, W - 1), (a + 1, 0, H - 1, b - 1), (a + 1, b + 1, H - 1, W - 1)]


def _quadrants(g):
    rs, cs = _full_rows(g), _full_cols(g)
    if len(rs) != 1 or len(cs) != 1:
        return None
    H, W = dims(g); a, b = rs[0], cs[0]
    return [(0, 0, a - 1, b - 1), (0, b + 1, a - 1, W - 1), (a + 1, 0, H - 1, b - 1), (a + 1, b + 1, H - 1, W - 1)]


def _blobs(g, conn8=True):
    """Connected components of ALL non-zero cells regardless of colour (glib.components splits by colour)."""
    H, W = dims(g); seen, out = set(), []
    nb = [(-1, 0), (1, 0), (0, -1), (0, 1)] + ([(-1, -1), (-1, 1), (1, -1), (1, 1)] if conn8 else [])
    for r in range(H):
        for c in range(W):
            if g[r][c] == 0 or (r, c) in seen:
                continue
            comp, st = [], [(r, c)]; seen.add((r, c))
            while st:
                y, x = st.pop(); comp.append((y, x))
                for dy, dx in nb:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and g[ny][nx] and (ny, nx) not in seen:
                        seen.add((ny, nx)); st.append((ny, nx))
            out.append(comp)
    return out


def _grav(s, d="down"):
    if d == "down":
        H, W = dims(s); out = blank(H, W)
        for c in range(W):
            col = [s[r][c] for r in range(H) if s[r][c]]
            for i, v in enumerate(reversed(col)):
                out[H - 1 - i][c] = v
        return out
    if d == "up":
        return flip_v(_grav(flip_v(s)))
    if d == "right":
        return transpose(_grav(transpose(s)))
    return flip_h(_grav(flip_h(s), "right"))


def _grav_masked(g, free):
    """Cells fall within each maximal vertical run of `free` cells; everything else is untouched."""
    H, W = dims(g); out = copy(g)
    for c in range(W):
        r = 0
        while r < H:
            if (r, c) not in free:
                r += 1; continue
            r1 = r
            while r1 + 1 < H and (r1 + 1, c) in free:
                r1 += 1
            vals = [g[y][c] for y in range(r, r1 + 1) if g[y][c]]
            for y in range(r, r1 + 1):
                out[y][c] = 0
            for i, v in enumerate(reversed(vals)):
                out[r1 - i][c] = v
            r = r1 + 1
    return out


def _rigid(s, d="up"):
    """Multi-colour blobs move as rigid pieces toward the top (or bottom) until blocked, stepping together."""
    if d == "down":
        return flip_v(_rigid(flip_v(s)))
    H, W = dims(s); blobs = [[(r, c, s[r][c]) for r, c in b] for b in _blobs(s)]
    occ = {(r, c) for b in blobs for r, c, _ in b}; moved = True
    while moved:
        moved = False
        for b in blobs:
            mine = {(r, c) for r, c, _ in b}
            if all(r > 0 and ((r - 1, c) in mine or (r - 1, c) not in occ) for r, c, _ in b):
                occ -= mine; b[:] = [(r - 1, c, v) for r, c, v in b]; occ |= {(r, c) for r, c, _ in b}; moved = True
    out = blank(H, W)
    for b in blobs:
        for r, c, v in b:
            out[r][c] = v
    return out


def _hollow(s):
    H, W = dims(s); out = copy(s)
    for r in range(H):
        for c in range(W):
            v = s[r][c]
            if v and all(0 <= r + dr < H and 0 <= c + dc < W and s[r + dr][c + dc] == v for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[r][c] = 0
    return out


def _fillbbox(s):
    out = copy(s)
    for o in components(s, lambda v: v != 0, conn8=True):
        rect(out, *bbox(o), s[o[0][0]][o[0][1]])
    return out


def _fillholes(s):
    """Empty cells not reachable from the border take the colour of the cells enclosing them."""
    H, W = dims(s); out = copy(s)
    reach = {(r, c) for r in range(H) for c in range(W) if (r in (0, H - 1) or c in (0, W - 1)) and s[r][c] == 0}
    st = list(reach)
    while st:
        y, x = st.pop()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < H and 0 <= nx < W and s[ny][nx] == 0 and (ny, nx) not in reach:
                reach.add((ny, nx)); st.append((ny, nx))
    for hole in components(s, lambda v: v == 0):
        if hole[0] in reach:
            continue
        nb = [s[y + dy][x + dx] for y, x in hole for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))
              if 0 <= y + dy < H and 0 <= x + dx < W and s[y + dy][x + dx]]
        col = max(set(nb), key=nb.count)
        for y, x in hole:
            out[y][x] = col
    return out


def _invert(s, col):
    return [[0 if v else col for v in row] for row in s]


def _shift(s, dr, dc):
    H, W = dims(s)
    return [[s[(r - dr) % H][(c - dc) % W] for c in range(W)] for r in range(H)]


def _rot180(s):
    return flip_v(flip_h(s))


def _rot270(s):
    return rot90(rot90(rot90(s)))


def _compact(s, d="left"):
    return _grav(s, d)


def _apply(g, box, fn):
    r0, c0, r1, c1 = box
    paste(g, fn(crop(g, r0, c0, r1, c1)), r0, c0)
    return g


def _frame_grid(rng, square=False, lo=8, hi=20):
    """A grey hollow frame somewhere in the grid; returns g and the frame's bbox."""
    h, w = _sz(rng, lo, hi)
    if square:
        n = min(h, w); h = w = n
    ih = rng.randint(3, max(3, h - 4)); iw = ih if square else rng.randint(3, max(3, w - 4))
    if ih + 2 > h or iw + 2 > w:
        return None
    r0 = rng.randint(0, h - ih - 2); c0 = rng.randint(0, w - iw - 2)
    g = blank(h, w); rect(g, r0, c0, r0 + ih + 1, c0 + iw + 1, SEP, fill=False)
    return g, (r0, c0, r0 + ih + 1, c0 + iw + 1)


def _find_frame(g):
    fr = components(g, SEP, conn8=False)
    if len(fr) != 1:
        return None
    return bbox(fr[0])


def _ok(g):
    """Reject a generator result with no content at all."""
    return g if any(v not in (0, SEP) for row in g for v in row) else None


# ---------------------------------------------------------------- 1 left mirrored, right gravity
def gi_lmrg(rng):
    g, c = _vline_grid(rng); h, w = dims(g); cols = _pal(rng, 3)
    _scatter(rng, g, 0, 0, h - 1, c - 1, cols, 0.3); _scatter(rng, g, 0, c + 1, h - 1, w - 1, cols, 0.3)
    return _ok(g)
def tf_lmrg(g):
    p = _split_v(g)
    return _join_v([flip_h(p[0]), _grav(p[1])]) if p else None
rule("split_left_mirror_right_gravity", "A grey column splits the grid: everything left of it is mirrored left-right within its half, everything right of it falls to the bottom edge.", gi_lmrg, tf_lmrg)


# 2 top recoloured by size, bottom outlined (digits)
def gi_trbo(rng):
    g, r = _hline_grid(rng, 8, 20); h, w = dims(g)
    a = _shapes_in(rng, g, 0, 0, r - 1, w - 1, rng.randint(2, 5), 1, 9, cols=_pal(rng, 3))
    b = _shapes_in(rng, g, r + 1, 0, h - 1, w - 1, rng.randint(1, 4), shapes=_rects(rng, rng.randint(1, 4), 3, 6), cols=_pal(rng, 3))
    return g if a and b else None
def tf_trbo(g):
    p = _split_h(g)
    if not p: return None
    top = copy(p[0])
    for o in objects(p[0], 0):
        for r, c in o: top[r][c] = len(o)
    return _join_h([top, _hollow(p[1])])
rule("split_top_recolour_by_size_bottom_outlined", "A grey row splits the grid: each object above it is recoloured with its number of cells, and each solid block below it is reduced to its outline.", gi_trbo, tf_trbo, digits=True)


# 3 inside the frame rotate, outside delete
def gi_fro(rng):
    fg = _frame_grid(rng, square=True)
    if not fg: return None
    g, (r0, c0, r1, c1) = fg; h, w = dims(g); cols = _pal(rng, 3)
    _scatter(rng, g, r0 + 1, c0 + 1, r1 - 1, c1 - 1, cols, 0.35)
    for r in range(h):
        for c in range(w):
            if (r < r0 or r > r1 or c < c0 or c > c1) and rng.random() < 0.2: g[r][c] = rng.choice(cols)
    return _ok(g)
def tf_fro(g):
    fb = _find_frame(g)
    if not fb: return None
    r0, c0, r1, c1 = fb; h, w = dims(g); out = blank(h, w)
    rect(out, r0, c0, r1, c1, SEP, fill=False)
    return paste(out, rot90(crop(g, r0 + 1, c0 + 1, r1 - 1, c1 - 1)), r0 + 1, c0 + 1)
rule("frame_inside_rotated_outside_erased", "Inside the grey frame the picture is turned a quarter turn clockwise; everything outside the frame is erased.", gi_fro, tf_fro)


# 4 above the diagonal keep, below take the mirror colour
def gi_dkm(rng):
    n = _one(rng, 5, 20); g = blank(n, n); cols = _pal(rng, 4)
    return _ok(_scatter(rng, g, 0, 0, n - 1, n - 1, cols, 0.35))
def tf_dkm(g):
    n = len(g); out = copy(g)
    for r in range(n):
        for c in range(r):
            out[r][c] = g[c][r]
    return out
rule("diagonal_above_kept_below_mirrored", "Cells on or above the main diagonal keep their colour; every cell below the diagonal is replaced by the colour of its mirror cell across the diagonal.", gi_dkm, tf_dkm)


# 5 panel marker menu: 1 flip, 2 fill holes, 3 erase (digits)
def gi_pm1(rng):
    g, pans, H = _panels_v(rng, 6, 20); cols = _pal(rng, 3, extra=(1, 2, 3))
    for c0, c1 in pans:
        if not _shapes_in(rng, g, 1, c0, H - 1, c1, 1, shapes=_rects(rng, rng.randint(1, 2), 3, min(5, c1 - c0 + 1), hollow=True), cols=cols): return None
        sprinkle(rng, g, rng.randint(0, 3), rng.choice(cols))
        g[0][c0] = rng.randint(1, 3)
    return _ok(g)
def _menu(g, pans, axis, ops):
    out = copy(g); H, W = dims(g)
    for a0, a1 in pans:
        box = (0, a0, H - 1, a1) if axis == "v" else (a0, 0, a1, W - 1)
        m = out[box[0]][box[1]]
        if m not in ops: return None
        out[box[0]][box[1]] = 0; _apply(out, box, ops[m])
    return out
def tf_pm1(g):
    pans = _spans(_full_cols(g), len(g[0]))
    return _menu(g, pans, "v", {1: flip_h, 2: _fillholes, 3: lambda s: blank(*dims(s))})
rule("panel_marker_menu_flip_fillholes_erase", "Each panel between grey columns carries a marker in its top-left cell that is removed: marker 1 mirrors the panel left-right, 2 fills every enclosed hole in the panel, 3 erases the panel.", gi_pm1, tf_pm1, digits=True)


# 6 quadrants get fixed rotations
def gi_qrot(rng):
    g, qs = _cross(rng, square=True); cols = _pal(rng, 3)
    for q in qs: _scatter(rng, g, *q, cols, 0.3)
    return _ok(g)
def tf_qrot(g):
    qs = _quadrants(g)
    if not qs: return None
    out = copy(g)
    for q, fn in zip(qs, (rot90, _rot180, _rot270, lambda s: s)): _apply(out, q, fn)
    return out
rule("quadrants_fixed_rotations", "A grey cross makes four square quadrants: the top-left turns a quarter clockwise, the top-right a half turn, the bottom-left a quarter anticlockwise, and the bottom-right stays.", gi_qrot, tf_qrot)


# 7 only the panel holding the grey dot gets gravity
def gi_dotg(rng):
    g, pans, H = _panels_v(rng, 6, 20); line = _pal(rng, 1)[0]; cols = _pal(rng, 3, extra=(line,))
    for r in range(H):
        for c in range(len(g[0])):
            if g[r][c] == SEP: g[r][c] = line
    for c0, c1 in pans: _scatter(rng, g, 0, c0, H - 1, c1, cols, 0.3)
    c0, c1 = rng.choice(pans); r, c = rng.randint(0, H - 2), rng.randint(c0, c1); g[r][c] = SEP
    return g if any(g[y][c] == 0 for y in range(r + 1, H)) else None
def tf_dotg(g):
    H, W = dims(g); pans = _spans(_full_cols_any(g), W); dots = cells(g, lambda v: v == SEP)
    if len(dots) != 1: return None
    out = copy(g); r, c = dots[0]; out[r][c] = 0
    for c0, c1 in pans:
        if c0 <= c <= c1: _apply(out, (0, c0, H - 1, c1), _grav)
    return out
rule("grey_dot_panel_only_gravity", "Coloured lines divide the grid into panels; only in the panel holding the single grey dot do the cells fall to the bottom (the dot vanishes), the other panels are untouched.", gi_dotg, tf_dotg)


# 8 left of the line objects rise, right of it objects fall
def gi_lrrf(rng):
    g, c = _vline_grid(rng, 8, 20); h, w = dims(g); cols = _pal(rng, 4)
    a = _shapes_in(rng, g, 0, 0, h - 1, c - 1, rng.randint(1, 4), 2, 6, cols, two_tone=True)
    b = _shapes_in(rng, g, 0, c + 1, h - 1, w - 1, rng.randint(1, 4), 2, 6, cols, two_tone=True)
    return g if a and b else None
def tf_lrrf(g):
    p = _split_v(g)
    return _join_v([_rigid(p[0], "up"), _rigid(p[1], "down")]) if p else None
rule("line_left_objects_rise_right_objects_fall", "A grey column splits the grid: objects left of it rise as rigid pieces until they meet the top edge or another object, objects right of it fall the same way to the bottom.", gi_lrrf, tf_lrrf)


# 9 border-marked rows reversed, marked columns sorted (digits)
def gi_brrc(rng):
    h, w = _sz(rng, 7, 20); g = blank(h, w); cols = _pal(rng, 4)
    _scatter(rng, g, 1, 1, h - 1, w - 1, cols, 0.35)
    for r in rng.sample(range(1, h), rng.randint(1, max(1, h // 3))): g[r][0] = SEP
    for c in rng.sample(range(1, w), rng.randint(1, max(1, w // 3))): g[0][c] = SEP
    return g
def tf_brrc(g):
    H, W = dims(g); out = copy(g)
    for r in range(1, H):
        if g[r][0] == SEP: out[r][1:] = g[r][1:][::-1]
    for c in range(1, W):
        if g[0][c] == SEP:
            vals = sorted(out[r][c] for r in range(1, H) if out[r][c])
            for r in range(1, H): out[r][c] = 0
            for i, v in enumerate(reversed(vals)): out[H - 1 - i][c] = v
    return out
rule("border_marked_rows_reversed_columns_sorted", "Grey marks in the left column name rows that are reversed left-to-right; grey marks in the top row name columns whose cells drop to the bottom sorted so the lowest colour number sits highest.", gi_brrc, tf_brrc, digits=True)


# 10 hollow diamonds filled, solid squares hollowed
def _diamond(rad):
    return [(r, c) for r in range(2 * rad + 1) for c in range(2 * rad + 1) if abs(r - rad) + abs(c - rad) == rad]
def gi_dsq(rng):
    h, w = _sz(rng, 9, 20); g = blank(h, w); k = rng.randint(2, 5)
    shapes = [_diamond(rng.randint(2, 4)) if rng.random() < 0.5 else _rect_shape(*(rng.randint(3, 6),) * 2) for _ in range(k)]
    return g if _shapes_in(rng, g, 0, 0, h - 1, w - 1, k, shapes=shapes, cols=_pal(rng, 4)) and len(objects(g, 0)) == k else None
def tf_dsq(g):
    out = copy(g)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o); col = g[o[0][0]][o[0][1]]
        if len(o) == (r1 - r0 + 1) * (c1 - c0 + 1): rect(out, r0 + 1, c0 + 1, r1 - 1, c1 - 1, 0)
        else: paste(out, _fillholes(crop(g, r0, c0, r1, c1)), r0, c0)
    return out
rule("hollow_diamonds_filled_solid_squares_hollowed", "Every hollow diamond is filled solid in its colour and every solid square is hollowed to its outline.", gi_dsq, tf_dsq)


# 11 the band between two lines is inverted
def _two_hlines(rng):
    h, w = _sz(rng, 9, 20); g = blank(h, w)
    r1 = rng.randint(2, h - 5); r2 = rng.randint(r1 + 3, min(h - 2, r1 + 10))
    g[r1] = [SEP] * w; g[r2] = [SEP] * w
    return g, r1, r2
def gi_binv(rng):
    g, r1, r2 = _two_hlines(rng); h, w = dims(g); band = _pal(rng, 1)[0]; cols = _pal(rng, 3, extra=(band,))
    _scatter(rng, g, 0, 0, r1 - 1, w - 1, cols, 0.3); _scatter(rng, g, r2 + 1, 0, h - 1, w - 1, cols, 0.3)
    _scatter(rng, g, r1 + 1, 0, r2 - 1, w - 1, [band], 0.4)
    return g if any(v == band for row in g[r1 + 1:r2] for v in row) else None
def tf_binv(g):
    rs = _full_rows(g)
    if len(rs) != 2: return None
    band = {v for row in g[rs[0] + 1:rs[1]] for v in row if v}
    if len(band) != 1: return None
    out = copy(g); col = band.pop()
    for r in range(rs[0] + 1, rs[1]): out[r] = [0 if v else col for v in g[r]]
    return out
rule("band_between_lines_inverted", "In the band between the two grey rows the coloured cells become empty and the empty cells take the band's colour; everything outside the band is untouched.", gi_binv, tf_binv)


# 12 left hollowed, right filled to bounding box
def gi_lhrf(rng):
    g, c = _vline_grid(rng, 8, 20); h, w = dims(g); cols = _pal(rng, 4)
    a = _shapes_in(rng, g, 0, 0, h - 1, c - 1, 1, shapes=_rects(rng, rng.randint(1, 3), 3, 6), cols=cols)
    b = _shapes_in(rng, g, 0, c + 1, h - 1, w - 1, rng.randint(1, 4), 3, 7, cols)
    return g if a and b else None
def tf_lhrf(g):
    p = _split_v(g)
    return _join_v([_hollow(p[0]), _fillbbox(p[1])]) if p else None
rule("split_left_hollow_right_fill_bbox", "A grey column splits the grid: solid blocks left of it are hollowed to outlines, objects right of it are filled out to their bounding rectangles.", gi_lhrf, tf_lhrf)


# 13 top rows shift right, bottom rows shift left
def gi_tsbs(rng):
    g, r = _hline_grid(rng); h, w = dims(g); cols = _pal(rng, 3)
    _scatter(rng, g, 0, 0, r - 1, w - 1, cols, 0.3); _scatter(rng, g, r + 1, 0, h - 1, w - 1, cols, 0.3)
    return _ok(g)
def tf_tsbs(g):
    p = _split_h(g)
    return _join_h([_shift(p[0], 0, 1), _shift(p[1], 0, -1)]) if p else None
rule("split_top_shift_right_bottom_shift_left", "A grey row splits the grid: every row above it slides one cell right and every row below it slides one cell left, cells wrapping round at the edges.", gi_tsbs, tf_tsbs)


# 14 left flipped vertically, right half turn
def tf_lfrh(g):
    p = _split_v(g)
    return _join_v([flip_v(p[0]), _rot180(p[1])]) if p else None
rule("split_left_flip_vertical_right_half_turn", "A grey column splits the grid: the left side is flipped top-to-bottom and the right side is turned a half turn in place.", gi_lmrg, tf_lfrh)


# 15 inside the frame mirrored, outside gravity
def gi_fmog(rng):
    fg = _frame_grid(rng)
    if not fg: return None
    g, (r0, c0, r1, c1) = fg; h, w = dims(g); cols = _pal(rng, 3)
    _scatter(rng, g, r0 + 1, c0 + 1, r1 - 1, c1 - 1, cols, 0.35)
    for r in range(h):
        for c in range(w):
            if (r < r0 or r > r1 or c < c0 or c > c1) and rng.random() < 0.25: g[r][c] = rng.choice(cols)
    return _ok(g)
def tf_fmog(g):
    fb = _find_frame(g)
    if not fb: return None
    r0, c0, r1, c1 = fb; h, w = dims(g)
    out = _grav_masked(g, {(r, c) for r in range(h) for c in range(w) if r < r0 or r > r1 or c < c0 or c > c1})
    return _apply(out, (r0 + 1, c0 + 1, r1 - 1, c1 - 1), flip_h)
rule("frame_inside_mirrored_outside_gravity", "Inside the grey frame the picture is mirrored left-right; outside the frame every cell falls straight down until it meets the floor, the frame, or another cell.", gi_fmog, tf_fmog)




# 17 quadrants: erase, fill bbox, hollow, flip
def gi_qefh(rng):
    g, qs = _cross(rng); cols = _pal(rng, 4)
    _scatter(rng, g, *qs[0], cols, 0.3)
    _shapes_in(rng, g, *qs[1], rng.randint(1, 3), 3, 6, cols)
    _shapes_in(rng, g, *qs[2], 1, shapes=_rects(rng, rng.randint(1, 2), 3, 5), cols=cols)
    _scatter(rng, g, *qs[3], cols, 0.3)
    return _ok(g)
def tf_qefh(g):
    qs = _quadrants(g)
    if not qs: return None
    out = copy(g)
    for q, fn in zip(qs, (lambda s: blank(*dims(s)), _fillbbox, _hollow, flip_h)): _apply(out, q, fn)
    return out
rule("quadrants_erase_fill_hollow_flip", "A grey cross makes four quadrants: the top-left is erased, objects in the top-right are filled to their bounding boxes, blocks in the bottom-left are hollowed, and the bottom-right is mirrored left-right.", gi_qefh, tf_qefh)


# 18 only the quadrant with the grey dot turns a half turn
def gi_dotq(rng):
    g, qs = _cross(rng); line = _pal(rng, 1)[0]; cols = _pal(rng, 3, extra=(line,)); h, w = dims(g)
    for r in range(h):
        for c in range(w):
            if g[r][c] == SEP: g[r][c] = line
    for q in qs: _scatter(rng, g, *q, cols, 0.3)
    q = rng.choice(qs); g[rng.randint(q[0], q[2])][rng.randint(q[1], q[3])] = SEP
    return g
def tf_dotq(g):
    rs, cs = _full_rows_any(g), _full_cols_any(g); dots = cells(g, lambda v: v == SEP)
    if len(rs) != 1 or len(cs) != 1 or len(dots) != 1: return None
    H, W = dims(g); a, b = rs[0], cs[0]; r, c = dots[0]; out = copy(g); out[r][c] = 0
    q = (0 if r < a else a + 1, 0 if c < b else b + 1, a - 1 if r < a else H - 1, b - 1 if c < b else W - 1)
    return _apply(out, q, _rot180)
rule("grey_dot_quadrant_half_turn", "A coloured cross makes four quadrants; only the quadrant holding the single grey dot is turned a half turn (the dot vanishes), the other three are untouched.", gi_dotq, tf_dotq)


# 19 stacked panel marker menu: 1 half turn, 2 invert, 3 outline (digits)
def gi_pm2(rng):
    g, pans, W = _panels_h(rng, 6, 20); cols = _pal(rng, 4, extra=(1, 2, 3))
    for r0, r1 in pans:
        col = rng.choice(cols)
        if not _shapes_in(rng, g, r0 + 1, 0, r1, W - 1, 1, shapes=_rects(rng, rng.randint(1, 3), 2, min(5, r1 - r0)), cols=[col]): return None
        g[r0][0] = rng.randint(1, 3)
    return _ok(g)
def tf_pm2(g):
    def inv(s):
        cs = {v for row in s for v in row if v}
        return _invert(s, cs.pop()) if len(cs) == 1 else None
    pans = _spans(_full_rows(g), len(g))
    try:
        return _menu(g, pans, "h", {1: _rot180, 2: inv, 3: _hollow})
    except TypeError:
        return None
rule("panel_marker_menu_halfturn_invert_outline", "Each panel between grey rows carries a marker in its top-left cell that is removed: marker 1 turns the panel a half turn, 2 swaps the panel's filled and empty cells in its one colour, 3 reduces its blocks to outlines.", gi_pm2, tf_pm2, digits=True)


# 20 panel marker menu: gravity direction (digits)
def gi_pm3(rng):
    g, pans, H = _panels_v(rng, 6, 20); cols = _pal(rng, 3, extra=(1, 2, 3, 4))
    for c0, c1 in pans:
        _scatter(rng, g, 1, c0, H - 1, c1, cols, 0.3); g[0][c0] = rng.randint(1, 4)
    return _ok(g)
def tf_pm3(g):
    pans = _spans(_full_cols(g), len(g[0]))
    return _menu(g, pans, "v", {1: lambda s: _grav(s, "down"), 2: lambda s: _grav(s, "up"), 3: lambda s: _grav(s, "left"), 4: lambda s: _grav(s, "right")})
rule("panel_marker_menu_gravity_direction", "Each panel between grey columns carries a marker in its top-left cell that is removed and sets which way its cells fall: 1 down, 2 up, 3 left, 4 right.", gi_pm3, tf_pm3, digits=True)


# 21 band between two vertical lines slides left
def _two_vlines(rng):
    h, w = _sz(rng, 9, 20); g = blank(h, w)
    c1 = rng.randint(2, w - 5); c2 = rng.randint(c1 + 3, min(w - 2, c1 + 10))
    for r in range(h): g[r][c1] = SEP; g[r][c2] = SEP
    return g, c1, c2
def gi_bsl(rng):
    g, c1, c2 = _two_vlines(rng); h, w = dims(g); cols = _pal(rng, 3)
    for a, b in ((0, c1 - 1), (c1 + 1, c2 - 1), (c2 + 1, w - 1)): _scatter(rng, g, 0, a, h - 1, b, cols, 0.3)
    return _ok(g)
def tf_bsl(g):
    cs = _full_cols(g)
    if len(cs) != 2: return None
    return _apply(copy(g), (0, cs[0] + 1, len(g) - 1, cs[1] - 1), lambda s: _compact(s, "left"))
rule("band_between_vertical_lines_slide_left", "Between the two grey columns every cell slides left along its row until it rests against the left line or another cell; outside the band nothing changes.", gi_bsl, tf_bsl)


# 22 band between two horizontal lines flipped vertically
def gi_bfv(rng):
    g, r1, r2 = _two_hlines(rng); h, w = dims(g); cols = _pal(rng, 3)
    for a, b in ((0, r1 - 1), (r1 + 1, r2 - 1), (r2 + 1, h - 1)): _scatter(rng, g, a, 0, b, w - 1, cols, 0.3)
    return _ok(g)
def tf_bfv(g):
    rs = _full_rows(g)
    if len(rs) != 2: return None
    return _apply(copy(g), (rs[0] + 1, 0, rs[1] - 1, len(g[0]) - 1), flip_v)
rule("band_between_lines_flipped_vertically", "The band between the two grey rows is flipped top-to-bottom in place; everything above and below the band is untouched.", gi_bfv, tf_bfv)


# 23 outer two-cell ring erased, core mirrored
def gi_orc(rng):
    h, w = _sz(rng, 8, 20); g = blank(h, w); cols = _pal(rng, 3)
    return _ok(_scatter(rng, g, 0, 0, h - 1, w - 1, cols, 0.3))
def tf_orc(g):
    H, W = dims(g); out = blank(H, W)
    return _apply(paste(out, crop(g, 2, 2, H - 3, W - 3), 2, 2), (2, 2, H - 3, W - 3), flip_h)
rule("outer_two_ring_erased_core_mirrored", "Every cell within two of the grid edge is erased; the core inside that border is mirrored left-right.", gi_orc, tf_orc)


# 24 left keeps only the largest object, right only the smallest
def gi_lls(rng):
    g, c = _vline_grid(rng, 8, 20); h, w = dims(g); cols = _pal(rng, 4)
    a = _shapes_in(rng, g, 0, 0, h - 1, c - 1, rng.randint(2, 4), 1, 7, cols, two_tone=True)
    b = _shapes_in(rng, g, 0, c + 1, h - 1, w - 1, rng.randint(2, 4), 1, 7, cols, two_tone=True)
    return g if a and b else None
def _keep(s, pick):
    bl = _blobs(s)
    if len(bl) < 2: return None
    sizes = sorted(len(b) for b in bl)
    if pick(sizes) in (sizes[0], sizes[-1]) and sizes.count(pick(sizes)) > 1: return None
    keep = next(b for b in bl if len(b) == pick(sizes)); out = blank(*dims(s))
    for r, c in keep: out[r][c] = s[r][c]
    return out
def tf_lls(g):
    p = _split_v(g)
    if not p: return None
    l, r = _keep(p[0], max), _keep(p[1], min)
    return _join_v([l, r]) if l and r else None
rule("split_left_largest_only_right_smallest_only", "A grey column splits the grid: left of it only the largest object survives, right of it only the smallest object survives; all other objects are erased.", gi_lls, tf_lls)


# 25 left: connect same-colour pairs; right: erase single cells
def gi_lcre(rng):
    g, c = _vline_grid(rng, 8, 20); h, w = dims(g); cols = _pal(rng, 6)
    rows = rng.sample(range(h), min(h, rng.randint(1, 4)))
    for row, col in zip(rows, cols):
        a, b = sorted(rng.sample(range(c), 2))
        if b - a < 2: continue
        g[row][a] = g[row][b] = col
    singles = [[(0, 0)] for _ in range(rng.randint(2, 6))]
    ok = _shapes_in(rng, g, 0, c + 1, h - 1, w - 1, 1, shapes=_rects(rng, 1, 2, 4) + [random_shape(rng, rng.randint(3, 6))] + singles, cols=_pal(rng, 3))
    return g if ok and any(v for row in g for v in row[:c]) else None
def tf_lcre(g):
    p = _split_v(g)
    if not p: return None
    l = copy(p[0])
    for col in {v for row in p[0] for v in row if v}:
        pts = cells(p[0], lambda v: v == col)
        if len(pts) == 2 and pts[0][0] == pts[1][0]:
            for x in range(pts[0][1], pts[1][1] + 1): l[pts[0][0]][x] = col
    r = copy(p[1])
    for b in _blobs(p[1]):
        if len(b) == 1: r[b[0][0]][b[0][1]] = 0
    return _join_v([l, r])
rule("split_left_connect_pairs_right_erase_singles", "A grey column splits the grid: left of it each pair of same-coloured cells on one row is joined by a line of that colour, right of it every isolated single cell is erased.", gi_lcre, tf_lcre)


# 26 marked rows slide right, marked columns fall
def tf_mrsc(g):
    H, W = dims(g); out = copy(g)
    for r in range(1, H):
        if g[r][0] == SEP:
            vals = [v for v in g[r][1:] if v]; out[r][1:] = [0] * (W - 1 - len(vals)) + vals
    for c in range(1, W):
        if g[0][c] == SEP:
            vals = [out[r][c] for r in range(1, H) if out[r][c]]
            for r in range(1, H): out[r][c] = 0
            for i, v in enumerate(reversed(vals)): out[H - 1 - i][c] = v
    return out
rule("marked_rows_slide_right_marked_columns_fall", "Grey marks in the left column name rows whose cells slide to the right edge; grey marks in the top row name columns whose cells then fall to the bottom edge.", gi_brrc, tf_mrsc)


# 27 above the diagonal slide left, below it fall
def tf_dslf(g):
    n = len(g); out = copy(g)
    for r in range(n):
        vals = [g[r][c] for c in range(r + 1, n) if g[r][c]]
        for c in range(r + 1, n): out[r][c] = 0
        for i, v in enumerate(vals): out[r][r + 1 + i] = v
    for c in range(n):
        vals = [g[r][c] for r in range(c + 1, n) if g[r][c]]
        for r in range(c + 1, n): out[r][c] = 0
        for i, v in enumerate(reversed(vals)): out[n - 1 - i][c] = v
    return out
rule("diagonal_above_slide_left_below_fall", "Cells above the main diagonal slide left along their row until they rest against the diagonal or another cell; cells below it fall down their column to the bottom edge; diagonal cells stay.", gi_dkm, tf_dslf)


# 28 nested frames: between recolour 1, inside 2, outside erased
def gi_nfz(rng):
    h, w = _sz(rng, 12, 22); g = blank(h, w); cols = _pal(rng, 3, extra=(1, 2))
    r0, c0 = rng.randint(0, h - 10), rng.randint(0, w - 10)
    r1, c1 = rng.randint(r0 + 9, h - 1), rng.randint(c0 + 9, w - 1)
    rect(g, r0, c0, r1, c1, SEP, fill=False)
    i0, j0 = rng.randint(r0 + 3, r1 - 6), rng.randint(c0 + 3, c1 - 6)
    i1, j1 = rng.randint(i0 + 2, r1 - 3), rng.randint(j0 + 2, c1 - 3)
    rect(g, i0, j0, i1, j1, SEP, fill=False)
    for r in range(h):
        for c in range(w):
            if g[r][c] == 0 and rng.random() < 0.3: g[r][c] = rng.choice(cols)
    return g
def tf_nfz(g):
    fr = sorted(components(g, SEP, conn8=False), key=len)
    if len(fr) != 2: return None
    (i0, j0, i1, j1), (r0, c0, r1, c1) = bbox(fr[0]), bbox(fr[1]); H, W = dims(g); out = copy(g)
    for r in range(H):
        for c in range(W):
            if g[r][c] in (0, SEP): continue
            if not (r0 < r < r1 and c0 < c < c1): out[r][c] = 0
            elif i0 < r < i1 and j0 < c < j1: out[r][c] = 2
            else: out[r][c] = 1
    return out
rule("nested_frames_zones_recolour_outside_erased", "Two grey frames nest: cells between the outer and inner frame become colour 1, cells inside the inner frame become colour 2, and cells outside the outer frame are erased.", gi_nfz, tf_nfz)


# 29 vertical thirds: flip, gravity, half turn
def gi_vt(rng):
    pw = rng.randint(7, 9) if rng.random() < 0.38 else rng.randint(3, 6); H = _one(rng, 5, 20)
    g = blank(H, 3 * pw + 2); cols = _pal(rng, 3)
    for c0 in (0, pw + 1, 2 * pw + 2): _scatter(rng, g, 0, c0, H - 1, c0 + pw - 1, cols, 0.3)
    for r in range(H): g[r][pw] = g[r][2 * pw + 1] = SEP
    return _ok(g)
def tf_vt(g):
    cs = _full_cols(g); H, W = dims(g)
    if len(cs) != 2: return None
    out = copy(g)
    for (c0, c1), fn in zip(_spans(cs, W), (flip_h, _grav, _rot180)): _apply(out, (0, c0, H - 1, c1), fn)
    return out
rule("vertical_thirds_flip_gravity_halfturn", "Two grey columns make three panels: the left panel is mirrored left-right, the middle panel's cells fall to the bottom, and the right panel is turned a half turn.", gi_vt, tf_vt)


# 30 horizontal thirds: shift right, hollow, fall
def gi_ht(rng):
    ph = rng.randint(7, 9) if rng.random() < 0.38 else rng.randint(3, 6); W = _one(rng, 6, 20)
    g = blank(3 * ph + 2, W); cols = _pal(rng, 3)
    _scatter(rng, g, 0, 0, ph - 1, W - 1, cols, 0.3)
    _shapes_in(rng, g, ph + 1, 0, 2 * ph, W - 1, 1, shapes=_rects(rng, rng.randint(1, 3), 3, min(5, ph)), cols=cols)
    _scatter(rng, g, 2 * ph + 2, 0, 3 * ph + 1, W - 1, cols, 0.3)
    g[ph] = [SEP] * W; g[2 * ph + 1] = [SEP] * W
    return _ok(g)
def tf_ht(g):
    rs = _full_rows(g); H, W = dims(g)
    if len(rs) != 2: return None
    out = copy(g)
    for (r0, r1), fn in zip(_spans(rs, H), (lambda s: _shift(s, 0, 1), _hollow, _grav)): _apply(out, (r0, 0, r1, W - 1), fn)
    return out
rule("horizontal_thirds_shift_hollow_fall", "Two grey rows make three bands: the top band slides one cell right with wrap-around, blocks in the middle band are hollowed to outlines, and the bottom band's cells fall to the floor.", gi_ht, tf_ht)


# 31 lattice panels: checkerboard of flip axes
def _lattice(rng, square=False):
    kr, kc = rng.randint(2, 3), rng.randint(2, 3)
    if rng.random() < 0.38:
        ph = rng.randint(10, 14) if kr == 2 else rng.randint(7, 9)
    else:
        ph = rng.randint(3, 8) if kr == 2 else rng.randint(3, 5)
    if square: pw = ph
    else: pw = (rng.randint(10, 14) if kc == 2 else rng.randint(7, 9)) if rng.random() < 0.38 else (rng.randint(3, 8) if kc == 2 else rng.randint(3, 5))
    H, W = kr * ph + kr - 1, kc * pw + kc - 1; g = blank(H, W)
    for i in range(1, kr): g[i * (ph + 1) - 1] = [SEP] * W
    for j in range(1, kc):
        for r in range(H): g[r][j * (pw + 1) - 1] = SEP
    boxes = [(i * (ph + 1), j * (pw + 1), i * (ph + 1) + ph - 1, j * (pw + 1) + pw - 1, i, j) for i in range(kr) for j in range(kc)]
    return g, boxes
def _lattice_boxes(g):
    H, W = dims(g)
    return [(r0, c0, r1, c1, i, j) for i, (r0, r1) in enumerate(_spans(_full_rows(g), H)) for j, (c0, c1) in enumerate(_spans(_full_cols(g), W))]
def gi_lcf(rng):
    g, boxes = _lattice(rng); cols = _pal(rng, 3)
    for b in boxes: _scatter(rng, g, *b[:4], cols, 0.3)
    return _ok(g)
def tf_lcf(g):
    out = copy(g)
    for r0, c0, r1, c1, i, j in _lattice_boxes(g): _apply(out, (r0, c0, r1, c1), flip_h if (i + j) % 2 == 0 else flip_v)
    return out
rule("lattice_panels_checker_flip_axes", "Grey lines make a lattice of panels: panels in checkerboard position with the top-left one are mirrored left-right, the other panels are flipped top-to-bottom.", gi_lcf, tf_lcf)


# 32 lattice rows rotate by row index
def gi_lrr(rng):
    g, boxes = _lattice(rng, square=True); cols = _pal(rng, 3)
    for b in boxes: _scatter(rng, g, *b[:4], cols, 0.3)
    return _ok(g)
def tf_lrr(g):
    out = copy(g); rots = (rot90, _rot180, _rot270)
    for r0, c0, r1, c1, i, j in _lattice_boxes(g): _apply(out, (r0, c0, r1, c1), rots[i % 3])
    return out
rule("lattice_rows_rotate_by_row_index", "Grey lines make a lattice of square panels: every panel in the first row turns a quarter clockwise, in the second row a half turn, in the third row a quarter anticlockwise.", gi_lrr, tf_lrr)


# 33 left recolour by cell count, right by height (digits)
def gi_lsrh(rng):
    g, c = _vline_grid(rng, 8, 20); h, w = dims(g); cols = _pal(rng, 3)
    a = _shapes_in(rng, g, 0, 0, h - 1, c - 1, rng.randint(1, 4), 1, 9, cols)
    b = _shapes_in(rng, g, 0, c + 1, h - 1, w - 1, rng.randint(1, 4), 2, 9, cols)
    return g if a and b else None
def tf_lsrh(g):
    p = _split_v(g)
    if not p: return None
    l, r = copy(p[0]), copy(p[1])
    for o in objects(p[0], 0):
        for y, x in o: l[y][x] = len(o)
    for o in objects(p[1], 0):
        r0, _, r1, _ = bbox(o)
        if r1 - r0 + 1 > 9: return None
        for y, x in o: r[y][x] = r1 - r0 + 1
    return _join_v([l, r])
rule("split_left_size_digit_right_height_digit", "A grey column splits the grid: each object left of it is recoloured with its number of cells, each object right of it with its height in rows.", gi_lsrh, tf_lsrh, digits=True)


# 34 inside the frame swap two colours, outside cleared
def gi_fsw(rng):
    fg = _frame_grid(rng)
    if not fg: return None
    g, (r0, c0, r1, c1) = fg; h, w = dims(g); a, b, x = _pal(rng, 3)
    _scatter(rng, g, r0 + 1, c0 + 1, r1 - 1, c1 - 1, [a, b], 0.5)
    for r in range(h):
        for c in range(w):
            if (r < r0 or r > r1 or c < c0 or c > c1) and rng.random() < 0.25: g[r][c] = rng.choice([a, b, x])
    inside = {g[r][c] for r in range(r0 + 1, r1) for c in range(c0 + 1, c1) if g[r][c]}
    return g if len(inside) == 2 else None
def tf_fsw(g):
    fb = _find_frame(g)
    if not fb: return None
    r0, c0, r1, c1 = fb; h, w = dims(g); out = blank(h, w); rect(out, r0, c0, r1, c1, SEP, fill=False)
    inside = sorted({g[r][c] for r in range(r0 + 1, r1) for c in range(c0 + 1, c1) if g[r][c]})
    if len(inside) != 2: return None
    swap = {inside[0]: inside[1], inside[1]: inside[0]}
    for r in range(r0 + 1, r1):
        for c in range(c0 + 1, c1):
            if g[r][c]: out[r][c] = swap[g[r][c]]
    return out
rule("frame_inside_swap_colours_outside_cleared", "Inside the grey frame the two colours trade places with each other; everything outside the frame is erased.", gi_fsw, tf_fsw)


# 35 top rows compact left, bottom rows compact right
def tf_tlbr(g):
    p = _split_h(g)
    return _join_h([_compact(p[0], "left"), _compact(p[1], "right")]) if p else None
rule("split_top_compact_left_bottom_compact_right", "A grey row splits the grid: above it every row's cells slide to the left edge, below it every row's cells slide to the right edge.", gi_tsbs, tf_tlbr)


# 36 side-by-side panels: odd ones hollowed, even ones filled
def gi_poe(rng):
    g, pans, H = _panels_v(rng, 6, 20); cols = _pal(rng, 4)
    for c0, c1 in pans:
        if not _shapes_in(rng, g, 0, c0, H - 1, c1, 1, shapes=_rects(rng, rng.randint(1, 2), 3, 4) + [random_shape(rng, rng.randint(3, 6))], cols=cols): return None
    return _ok(g)
def tf_poe(g):
    H, W = dims(g); out = copy(g)
    for i, (c0, c1) in enumerate(_spans(_full_cols(g), W)): _apply(out, (0, c0, H - 1, c1), _hollow if i % 2 == 0 else _fillbbox)
    return out
rule("panels_odd_hollowed_even_filled", "Grey columns make a row of panels: in the first, third, fifth... panel every block is hollowed to its outline, in the second, fourth... panel every object is filled out to its bounding box.", gi_poe, tf_poe)


# 37 left colours step up by one, right turns grey (digits)
_CYC = [1, 2, 3, 4, 6, 7, 8, 9]
def tf_lcrg(g):
    p = _split_v(g)
    if not p: return None
    l = [[_CYC[(_CYC.index(v) + 1) % 8] if v else 0 for v in row] for row in p[0]]
    r = [[SEP if v else 0 for v in row] for row in p[1]]
    return _join_v([l, r])
rule("split_left_colour_plus_one_right_grey", "A grey column splits the grid: left of it every colour number goes up by one (skipping grey, 9 wraps to 1), right of it every coloured cell turns grey.", gi_lmrg, tf_lcrg, digits=True)


# 38 anti-diagonal: above falls onto the line, below erased
def gi_adf(rng):
    n = _one(rng, 6, 20); g = blank(n, n); cols = _pal(rng, 3)
    _scatter(rng, g, 0, 0, n - 1, n - 1, cols, 0.3)
    for r in range(n): g[r][n - 1 - r] = SEP
    return _ok(g)
def tf_adf(g):
    n = len(g); out = _grav_masked(g, {(r, c) for r in range(n) for c in range(n) if r + c < n - 1})
    for r in range(n):
        for c in range(n):
            if r + c > n - 1: out[r][c] = 0
    return out
rule("antidiagonal_above_falls_onto_line_below_erased", "A grey line runs from the top-right to the bottom-left corner: cells above it fall down their column until they rest on the line or another cell, cells below it are erased.", gi_adf, tf_adf)


# 39 quadrant corner marker menu (digits)
def gi_qcm(rng):
    g, qs = _cross(rng); cols = _pal(rng, 3, extra=(1, 2, 3, 4)); H, W = dims(g)
    for q in qs: _scatter(rng, g, *q, cols, 0.3)
    for r, c in ((0, 0), (0, W - 1), (H - 1, 0), (H - 1, W - 1)): g[r][c] = rng.randint(1, 4)
    return g
def tf_qcm(g):
    qs = _quadrants(g)
    if not qs: return None
    H, W = dims(g); out = copy(g); ops = {1: flip_h, 2: flip_v, 3: lambda s: blank(*dims(s)), 4: lambda s: s}
    for q, (r, c) in zip(qs, ((0, 0), (0, W - 1), (H - 1, 0), (H - 1, W - 1))):
        m = g[r][c]
        if m not in ops: return None
        out[r][c] = 0; _apply(out, q, ops[m])
    return out
rule("quadrant_corner_marker_menu", "A grey cross makes four quadrants, each with a marker in its outer corner that is removed: marker 1 mirrors that quadrant left-right, 2 flips it top-to-bottom, 3 erases it, 4 leaves it alone.", gi_qcm, tf_qcm, digits=True)


# 40 band between two vertical lines: empty cells checkered grey
def tf_bcg(g):
    cs = _full_cols(g)
    if len(cs) != 2: return None
    out = copy(g)
    for r in range(len(g)):
        for c in range(cs[0] + 1, cs[1]):
            if g[r][c] == 0 and (r + c) % 2 == 0: out[r][c] = SEP
    return out
rule("band_between_lines_empty_checkered_grey", "Between the two grey columns every empty cell on an even diagonal (row plus column even) is painted grey, making a checkerboard around the coloured cells; outside the band nothing changes.", gi_bsl, tf_bcg)




# 42 inside the frame fill to bbox, outside hollowed
def gi_ffoh(rng):
    fg = _frame_grid(rng, lo=10, hi=20)
    if not fg: return None
    g, (r0, c0, r1, c1) = fg; h, w = dims(g); cols = _pal(rng, 3)
    _shapes_in(rng, g, r0 + 1, c0 + 1, r1 - 1, c1 - 1, rng.randint(1, 3), 3, 6, cols)
    sub = blank(h, w); _shapes_in(rng, sub, 0, 0, h - 1, w - 1, 1, shapes=_rects(rng, rng.randint(1, 3), 3, 5), cols=cols)
    for r in range(h):
        for c in range(w):
            if sub[r][c] and (r < r0 - 1 or r > r1 + 1 or c < c0 - 1 or c > c1 + 1): g[r][c] = sub[r][c]
    return _ok(g)
def tf_ffoh(g):
    fb = _find_frame(g)
    if not fb: return None
    r0, c0, r1, c1 = fb; h, w = dims(g); out = _hollow(g); rect(out, r0, c0, r1, c1, SEP, fill=False)
    return paste(out, _fillbbox(crop(g, r0 + 1, c0 + 1, r1 - 1, c1 - 1)), r0 + 1, c0 + 1)
rule("frame_inside_fill_bbox_outside_hollowed", "Inside the grey frame every object is filled out to its bounding box; outside the frame every block is hollowed to its outline.", gi_ffoh, tf_ffoh)
