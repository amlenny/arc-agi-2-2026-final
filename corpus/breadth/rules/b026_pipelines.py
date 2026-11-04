# b026_pipelines.py -- THREE-STEP PIPELINES: every rule chains three simple operations (denoise, gravity,
# crop, rotate, tile, scale, frame, outline, fill holes, recolour, delete, slide, sort, count-to-bar, split
# panels, overlay, mirror, invert) in an order no earlier batch used. Each description names the three steps.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


# ---------------------------------------------------------------- helpers (local to this batch)
def _size(rng, lo=6, hi=18, big=True):
    """~35% of inputs land in the 21-30 band when the rule allows it."""
    if big and rng.random() < 0.35:
        return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _scene(rng, k_lo=2, k_hi=5, n_lo=3, n_hi=8, lo=6, hi=18, margin=1, cols=None, big=True, more=True):
    h, w = _size(rng, lo, hi, big); g = blank(h, w)
    k = rng.randint(k_lo, k_hi) + (2 if more and h * w > 400 else 0)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    cs = [rng.choice(cols or COLOURS) for _ in range(k)]
    if place_shapes(rng, g, shapes, cs, margin=margin) is None:
        return None
    return g


def _dots(rng, h, w, cols, density):
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < density:
                g[r][c] = rng.choice(cols)
    return g


def _blobs(g, bg=0, conn8=True):
    """Connected components of non-bg cells regardless of colour (glib.components splits by colour)."""
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


def _denoise(g):
    """Erase coloured cells with no coloured 8-neighbour."""
    H, W = dims(g); out = copy(g)
    for r in range(H):
        for c in range(W):
            if g[r][c] and not any(0 <= r + dr < H and 0 <= c + dc < W and g[r + dr][c + dc]
                                   for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc):
                out[r][c] = 0
    return out


def _gravity(g):
    h, w = dims(g); out = blank(h, w)
    for c in range(w):
        col = [g[r][c] for r in range(h) if g[r][c]]
        for i, v in enumerate(reversed(col)):
            out[h - 1 - i][c] = v
    return out


def _compact_left(g):
    return [[v for v in row if v] + [0] * sum(1 for v in row if not v) for row in g]


def _slide_left(g, objs):
    """Objects slide left as rigid bodies, leftmost first, until the wall or another object."""
    H, W = dims(g); out = blank(H, W)
    for o in sorted(objs, key=lambda o: min(c for _, c in o)):
        cs = [(r, c, g[r][c]) for r, c in o]; d = 0
        while not any(c - d - 1 < 0 or out[r][c - d - 1] for r, c, _ in cs):
            d += 1
        for r, c, v in cs:
            out[r][c - d] = v
    return out


def _scale(g, k):
    return [[v for v in row for _ in range(k)] for row in g for _ in range(k)]


def _frame(g, col):
    w = len(g[0]) + 2
    return [[col] * w] + [[col] + row + [col] for row in g] + [[col] * w]


def _hollow(g):
    """Coloured cells whose four side neighbours are all coloured become empty."""
    H, W = dims(g); out = copy(g)
    for r in range(1, H - 1):
        for c in range(1, W - 1):
            if g[r][c] and g[r - 1][c] and g[r + 1][c] and g[r][c - 1] and g[r][c + 1]:
                out[r][c] = 0
    return out


def _outline_keep(g):
    """Keep only coloured cells that have an empty side neighbour or lie on the edge."""
    H, W = dims(g); out = blank(H, W)
    for r in range(H):
        for c in range(W):
            if g[r][c] and (r in (0, H - 1) or c in (0, W - 1) or not (g[r - 1][c] and g[r + 1][c] and g[r][c - 1] and g[r][c + 1])):
                out[r][c] = g[r][c]
    return out


def _mask_crop(g, o):
    r0, c0, r1, c1 = bbox(o); sub = blank(r1 - r0 + 1, c1 - c0 + 1)
    for r, c in o:
        sub[r - r0][c - c0] = g[r][c]
    return sub


def _bbox_all(g):
    cs = cells(g, lambda v: v != 0)
    return bbox(cs) if cs else None


def _touches_border(g, o):
    H, W = dims(g)
    return any(r in (0, H - 1) or c in (0, W - 1) for r, c in o)


def _join_h(panels, sep):
    out = []
    for r in range(len(panels[0])):
        row = []
        for i, p in enumerate(panels):
            if i:
                row.append(sep)
            row += p[r]
        out.append(row)
    return out


def _split_h(g):
    h, w = dims(g)
    sc = [c for c in range(w) if g[0][c] != 0 and all(g[r][c] == g[0][c] for r in range(h))]
    if not sc:
        return None
    sep = g[0][sc[0]]
    if any(g[0][c] != sep for c in sc):
        return None
    panels, start = [], 0
    for c in sc + [w]:
        if c > start:
            panels.append([row[start:c] for row in g])
        start = c + 1
    if len({len(p[0]) for p in panels}) != 1:
        return None
    return panels, sep


def _panels(rng, k, ph_lo=4, ph_hi=12, pw_lo=3, pw_hi=8, big=True, wide=False, dens=(0.25, 0.5)):
    """k side-by-side dot panels with a fresh separator; returns (grid, sep) or None.
    big: ~35% of inputs are 21-30 tall (or, with wide=True, 21-30 wide with height capped at ph_hi)."""
    if big and rng.random() < 0.35:
        pw = rng.randint(max(pw_lo, (21 - k + 1) // k + 1), (30 - k + 1) // k)
        ph = rng.randint(ph_lo, ph_hi) if wide else rng.randint(21, 30)
    else:
        ph, pw = rng.randint(ph_lo, ph_hi), rng.randint(pw_lo, pw_hi)
    if k * pw + k - 1 > 30:
        return None
    sep = rng.choice([c for c in COLOURS if c != 5]); cols = colours(rng, rng.randint(1, 2), exclude=(0, sep, 5))
    panels = [_dots(rng, ph, pw, cols, rng.uniform(*dens)) for _ in range(k)]
    g = _join_h(panels, sep)
    sp = _split_h(g)
    return (g, sep) if sp and len(sp[0]) == k else None


def _rects(rng, h, w, n, hollow, cols, lo=3, hi=7, margin=1, border_ok=True):
    """n non-overlapping rectangles; returns list of (r0,c0,r1,c1,colour) or None."""
    g = blank(h, w); out = []
    for i in range(n):
        for _ in range(60):
            rh, rw = rng.randint(lo, min(hi, h)), rng.randint(lo, min(hi, w))
            r0, c0 = rng.randint(0, h - rh), rng.randint(0, w - rw)
            r1, c1 = r0 + rh - 1, c0 + rw - 1
            if all(g[r][c] == 0 for r in range(max(0, r0 - margin), min(h, r1 + margin + 1)) for c in range(max(0, c0 - margin), min(w, c1 + margin + 1))):
                rect(g, r0, c0, r1, c1, cols[i], fill=not hollow[i]); out.append((r0, c0, r1, c1, cols[i])); break
        else:
            return None
    return g, out


# ================================================================ rules
# 1 denoise -> gravity -> column parity colour
def gi_p01(rng):
    g = _scene(rng, 2, 5, 3, 7, 7, 18)
    if g is None: return None
    return sprinkle(rng, g, rng.randint(3, 10), rng.choice(COLOURS))
def tf_p01(g):
    out = _gravity(_denoise(g))
    return [[(1 if c % 2 == 0 else 2) if v else 0 for c, v in enumerate(row)] for row in out]
rule("denoise_gravity_column_parity", "Erase every isolated single cell, then let all remaining cells fall to the floor, then recolour the stacks 1 in even columns and 2 in odd columns.", gi_p01, tf_p01)


# 2 crop largest -> rotate -> tile 2x2
def gi_p02(rng):
    g = _scene(rng, 2, 5, 3, 8, 7, 18)
    if g is None: return None
    s = sorted(len(o) for o in objects(g, 0))
    return g if len(s) >= 2 and s[-1] != s[-2] else None
def tf_p02(g):
    sub = rot90(_mask_crop(g, max(objects(g, 0), key=len)))
    top = [row + row for row in sub]
    return top + top
rule("crop_largest_rotate_tile_2x2", "Cut out the largest object, then rotate it a quarter turn clockwise, then tile that piece two by two.", gi_p02, tf_p02)


# 3 keep border-touching -> mirror -> fill hollow rectangles
def gi_p03(rng):
    h, w = _size(rng, 8, 18); n = rng.randint(2, 4) + (2 if h * w > 400 else 0)
    hollow = [True] * n; cols = [rng.choice(COLOURS) for _ in range(n)]
    res = _rects(rng, h, w, n, hollow, cols, lo=3, hi=7, margin=0)
    if res is None: return None
    g, rs = res
    touch = [r0 == 0 or c0 == 0 or r1 == h - 1 or c1 == w - 1 for r0, c0, r1, c1, _ in rs]
    return g if any(touch) and not all(touch) else None
def tf_p03(g):
    H, W = dims(g); out = blank(H, W)
    for o in objects(g, 0):
        if _touches_border(g, o):
            for r, c in o: out[r][c] = g[r][c]
    out = flip_h(out)
    for o in objects(out, 0):
        r0, c0, r1, c1 = bbox(o)
        if r1 - r0 >= 2 and c1 - c0 >= 2: rect(out, r0 + 1, c0 + 1, r1 - 1, c1 - 1, out[o[0][0]][o[0][1]])
    return out
rule("border_frames_mirror_fill", "Keep only the hollow rectangles touching the grid edge, then mirror the grid left to right, then fill each surviving rectangle solid in its own colour.", gi_p03, tf_p03)


# 4 count objects per colour -> bars -> sort longest on top
def gi_p04(rng):
    g = _scene(rng, 3, 9, 1, 4, 7, 18, cols=colours(rng, rng.randint(2, 4)))
    if g is None: return None
    cnt = {}
    for o in objects(g, 0):
        col = g[o[0][0]][o[0][1]]; cnt[col] = cnt.get(col, 0) + 1
    return g if len(cnt) >= 2 and len(set(cnt.values())) == len(cnt) else None
def tf_p04(g):
    cnt = {}
    for o in objects(g, 0):
        col = g[o[0][0]][o[0][1]]; cnt[col] = cnt.get(col, 0) + 1
    w = max(cnt.values())
    return [[col] * n + [0] * (w - n) for col, n in sorted(cnt.items(), key=lambda kv: -kv[1])]
rule("colour_object_counts_bars_longest_top", "Count the objects of each colour, then draw one left-aligned bar per colour as long as its count, then stack the bars with the longest on top.", gi_p04, tf_p04)


# 5 extract odd object -> scale 2x -> frame in the others' colour
def gi_p05(rng):
    uniq, shared = colours(rng, 2); k = rng.randint(3, 6)
    g = _scene(rng, k, k, 3, 7, 8, 18, cols=[shared], more=False)
    if g is None: return None
    obs = objects(g, 0)
    if len(obs) != k: return None
    o = rng.choice(obs)
    for r, c in o: g[r][c] = uniq
    return g
def tf_p05(g):
    obs = objects(g, 0); cnt = counts(g)
    o = next(o for o in obs if sum(1 for p in obs if g[p[0][0]][p[0][1]] == g[o[0][0]][o[0][1]]) == 1)
    other = next(g[p[0][0]][p[0][1]] for p in obs if p is not o)
    return _frame(_scale(_mask_crop(g, o), 2), other)
rule("odd_colour_object_scale2_frame_others", "Cut out the one object whose colour no other object has, then enlarge it two times, then surround it with a one-cell border in the other objects' colour.", gi_p05, tf_p05)


# 6 recolour by size rank -> delete rank 1 -> slide left
def gi_p06(rng):
    g = _scene(rng, 3, 6, 2, 9, 8, 18, margin=1, more=False)
    if g is None: return None
    s = [len(o) for o in objects(g, 0)]
    return g if len(set(s)) == len(s) and len(s) <= 9 else None
def tf_p06(g):
    H, W = dims(g); obs = sorted(objects(g, 0), key=len, reverse=True); out = blank(H, W)
    for i, o in enumerate(obs):
        if i == 0: continue
        for r, c in o: out[r][c] = i + 1
    return _slide_left(out, obs[1:])
rule("size_rank_recolour_drop_first_slide_left", "Recolour every object with its size rank (largest 1, next 2, and so on), then delete rank 1, then slide the remaining objects left until they touch the wall or each other.", gi_p06, tf_p06, digits=True)


# 7 split panels -> overlay -> outline
def gi_p07(rng):
    res = _panels(rng, rng.randint(2, 4))
    return res[0] if res else None
def tf_p07(g):
    panels, sep = _split_h(g); ph, pw = dims(panels[0]); out = blank(ph, pw)
    for p in reversed(panels):
        for r in range(ph):
            for c in range(pw):
                if p[r][c]: out[r][c] = p[r][c]
    return _outline_keep(out)
rule("panels_overlay_then_outline", "Split the grid at the separator columns, then stack the panels into one with the leftmost panel winning conflicts, then keep only the cells of that picture that border an empty cell or the edge.", gi_p07, tf_p07)


# 8 rise -> rotate -> recolour rows by cell count
def gi_p08(rng):
    h, w = _size(rng, 5, 15); g = blank(h, w)
    for c in range(w):
        for r in rng.sample(range(h), rng.randint(0, min(9, h))):
            g[r][c] = rng.choice(COLOURS)
    return g if any(v for row in g for v in row) else None
def tf_p08(g):
    up = flip_v(_gravity(flip_v(g))); rot = rot90(up)
    return [[len([v for v in row if v]) if v else 0 for v in row] for row in rot]
rule("rise_rotate_rows_recoloured_by_count", "Every cell rises to the top of its column, then the grid turns a quarter turn clockwise, then each row's cells are recoloured with the number of cells in that row.", gi_p08, tf_p08, digits=True)


# 9 denoise -> crop -> mirror below
def gi_p09(rng):
    g = _scene(rng, 1, 3, 3, 8, 7, 18, more=False)
    if g is None: return None
    g = sprinkle(rng, g, rng.randint(3, 12), rng.choice(COLOURS))
    bb = _bbox_all(_denoise(g))
    return g if bb and bb[2] - bb[0] + 1 <= 15 else None
def tf_p09(g):
    d = _denoise(g); bb = _bbox_all(d)
    if bb is None: return None
    sub = crop(d, *bb)
    return sub + flip_v(sub)
rule("denoise_crop_mirror_below", "Erase every isolated single cell, then cut the remaining picture to its bounding box, then append its top-to-bottom mirror image underneath.", gi_p09, tf_p09)


# 10 keep largest -> hollow -> move to top-left corner
def gi_p10(rng):
    h, w = _size(rng, 8, 18); n = rng.randint(2, 4) + (2 if h * w > 400 else 0)
    res = _rects(rng, h, w, n, [False] * n, [rng.choice(COLOURS) for _ in range(n)], lo=3, hi=8)
    if res is None: return None
    g, rs = res; areas = sorted((r1 - r0 + 1) * (c1 - c0 + 1) for r0, c0, r1, c1, _ in rs)
    return g if areas[-1] != areas[-2] and len(objects(g, 0)) == n else None
def tf_p10(g):
    H, W = dims(g); o = max(objects(g, 0), key=len); sub = _hollow(_frame(_mask_crop(g, o), 0))[1:-1]
    sub = [row[1:-1] for row in sub]
    return paste(blank(H, W), sub, 0, 0)
rule("keep_largest_hollow_to_corner", "Keep only the largest rectangle, then hollow it out leaving its one-cell outline, then slide it into the top-left corner.", gi_p10, tf_p10)


# 11 delete border-touching -> grey bbox frames -> mirror
def gi_p11(rng):
    g = _scene(rng, 2, 5, 3, 7, 8, 18, margin=2, cols=[c for c in COLOURS if c != 5])
    if g is None: return None
    t = [_touches_border(g, o) for o in objects(g, 0)]
    return g if any(t) and not all(t) else None
def tf_p11(g):
    H, W = dims(g); out = blank(H, W)
    for o in objects(g, 0):
        if _touches_border(g, o): continue
        r0, c0, r1, c1 = bbox(o)
        for r in range(r0 - 1, r1 + 2):
            for c in range(c0 - 1, c1 + 2):
                if 0 <= r < H and 0 <= c < W and (r in (r0 - 1, r1 + 1) or c in (c0 - 1, c1 + 1)): out[r][c] = 5
        for r, c in o: out[r][c] = g[r][c]
    return flip_h(out)
rule("drop_border_objects_grey_frames_mirror", "Delete every object touching the grid edge, then draw a grey frame one cell outside each remaining object's bounding box, then mirror the grid left to right.", gi_p11, tf_p11)


# 12 connect pairs -> crop -> transpose
def gi_p12(rng):
    h, w = _size(rng, 7, 18); g = blank(h, w); used = set(); n = 0
    for col in colours(rng, rng.randint(1, 4)):
        for _ in range(30):
            if rng.random() < 0.5:
                r = rng.randrange(h); a, b = sorted(rng.sample(range(w), 2)); seg = {(r, x) for x in range(a, b + 1)}
            else:
                c = rng.randrange(w); a, b = sorted(rng.sample(range(h), 2)); seg = {(y, c) for y in range(a, b + 1)}
            if len(seg) >= 3 and not (seg & used):
                used |= seg; e = sorted(seg); g[e[0][0]][e[0][1]] = col; g[e[-1][0]][e[-1][1]] = col; n += 1; break
    return g if n else None
def tf_p12(g):
    out = copy(g)
    for col in set(v for row in g for v in row if v):
        pts = cells(g, lambda v: v == col)
        if len(pts) != 2: continue
        (r1, c1), (r2, c2) = pts
        if r1 == r2:
            for x in range(min(c1, c2), max(c1, c2) + 1): out[r1][x] = col
        elif c1 == c2:
            for y in range(min(r1, r2), max(r1, r2) + 1): out[y][c1] = col
    return transpose(crop(out, *_bbox_all(out)))
rule("connect_pairs_crop_transpose", "Join each same-colour pair of cells on one row or column with a line, then cut the grid to the bounding box of everything coloured, then transpose it.", gi_p12, tf_p12)


# 13 count objects -> diagonal square in largest's colour -> scale 2x
def gi_p13(rng):
    g = _scene(rng, 2, 8, 1, 6, 7, 18)
    if g is None: return None
    s = sorted(len(o) for o in objects(g, 0))
    return g if 2 <= len(s) <= 15 and s[-1] != s[-2] else None
def tf_p13(g):
    obs = objects(g, 0); n = len(obs); o = max(obs, key=len); col = g[o[0][0]][o[0][1]]
    return _scale([[col if r == c else 0 for c in range(n)] for r in range(n)], 2)
rule("object_count_diagonal_largest_colour_2x", "Count the objects, then draw a square that many cells wide with its main diagonal in the largest object's colour, then enlarge it two times.", gi_p13, tf_p13)


# 14 keep majority colour -> compact rows left -> mirror beside
def gi_p14(rng):
    h = rng.randint(21, 30) if rng.random() < 0.35 else rng.randint(5, 15); w = rng.randint(4, 15)
    g = _dots(rng, h, w, colours(rng, rng.randint(2, 3)), rng.uniform(0.3, 0.6)); cnt = counts(g); cnt.pop(0, None)
    v = sorted(cnt.values())
    return g if len(v) >= 2 and v[-1] != v[-2] else None
def tf_p14(g):
    cnt = counts(g); cnt.pop(0, None); keep = max(cnt, key=cnt.get)
    comp = _compact_left([[v if v == keep else 0 for v in row] for row in g])
    return [row + row[::-1] for row in comp]
rule("majority_colour_compact_left_mirror_beside", "Keep only the most frequent colour, then slide each row's cells to the left wall, then place the grid's left-right mirror image beside it.", gi_p14, tf_p14)


# 15 split -> xor -> upscale 2x
def gi_p15(rng):
    res = _panels(rng, 2, ph_hi=15, pw_hi=8, wide=True)
    return res[0] if res and len(res[0]) <= 15 and len(res[0][0]) // 2 <= 15 else None
def tf_p15(g):
    (a, b), sep = _split_h(g); ph, pw = dims(a)
    x = [[(a[r][c] or b[r][c]) if bool(a[r][c]) != bool(b[r][c]) else 0 for c in range(pw)] for r in range(ph)]
    return _scale(x, 2) if any(v for row in x for v in row) else None
rule("panels_xor_upscale_2x", "Split the grid at the separator, then keep only the cells coloured in exactly one of the two panels, then enlarge the result two times.", gi_p15, tf_p15)


# 16 sort objects by size in a row -> recolour by rank
def gi_p16(rng):
    g = _scene(rng, 2, 6, 2, 8, 8, 18, more=False)
    if g is None: return None
    obs = objects(g, 0); s = [len(o) for o in obs]
    if len(set(s)) != len(s) or len(s) > 9: return None
    return g if sum(bbox(o)[3] - bbox(o)[1] + 1 for o in obs) + len(obs) - 1 <= 30 else None
def tf_p16(g):
    obs = sorted(objects(g, 0), key=len); subs = [_mask_crop(g, o) for o in obs]
    H = max(len(s) for s in subs); W = sum(len(s[0]) for s in subs) + len(subs) - 1; out = blank(H, W); c = 0
    for i, s in enumerate(subs):
        paste(out, [[i + 1 if v else 0 for v in row] for row in s], H - len(s), c); c += len(s[0]) + 1
    return out
rule("objects_row_by_size_recolour_rank", "Cut out the objects, then lay them in one row bottom-aligned from smallest to largest with one empty column between, then recolour each with its position number 1, 2, 3 and so on.", gi_p16, tf_p16, digits=True)


# 17 rotate -> gravity -> recolour stacks by height
def gi_p17(rng):
    h, w = _size(rng, 5, 15); g = blank(h, w)
    for r in range(h):
        for c in rng.sample(range(w), rng.randint(0, min(9, w))):
            g[r][c] = rng.choice(COLOURS)
    return g if any(v for row in g for v in row) else None
def tf_p17(g):
    out = _gravity(rot90(g)); H, W = dims(out)
    hs = [sum(1 for r in range(H) if out[r][c]) for c in range(W)]
    return [[hs[c] if v else 0 for c, v in enumerate(row)] for row in out]
rule("rotate_gravity_stacks_coloured_by_height", "Turn the grid a quarter turn clockwise, then let every cell fall to the floor, then recolour each column's stack with its height.", gi_p17, tf_p17, digits=True)


# 18 erase rarest colour -> fill pinholes -> crop
def gi_p18(rng):
    h, w = _size(rng, 8, 18); n = rng.randint(1, 3) + (1 if h * w > 400 else 0)
    cols = colours(rng, n + 1); noise = cols[-1]
    res = _rects(rng, h, w, n, [False] * n, cols[:n], lo=3, hi=8)
    if res is None: return None
    g, rs = res
    for r0, c0, r1, c1, _ in rs:
        for _ in range(rng.randint(1, 3)):
            r, c = rng.randint(r0 + 1, r1 - 1), rng.randint(c0 + 1, c1 - 1)
            if all(g[y][x] for y, x in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))): g[r][c] = 0
    sprinkle(rng, g, rng.randint(1, 6), noise); cnt = counts(g)
    return g if cnt.get(noise, 0) and cnt[noise] < min(v for k, v in cnt.items() if k not in (0, noise)) else None
def tf_p18(g):
    cnt = counts(g); cnt.pop(0, None); rare = min(cnt, key=cnt.get); H, W = dims(g)
    g2 = [[0 if v == rare else v for v in row] for row in g]; out = copy(g2)
    for r in range(1, H - 1):
        for c in range(1, W - 1):
            nb = {g2[r - 1][c], g2[r + 1][c], g2[r][c - 1], g2[r][c + 1]}
            if g2[r][c] == 0 and len(nb) == 1 and 0 not in nb: out[r][c] = nb.pop()
    return crop(out, *_bbox_all(out))
rule("erase_rarest_fill_pinholes_crop", "Erase the colour with the fewest cells, then fill every single-cell hole with the colour surrounding it, then cut the grid to the bounding box of what remains.", gi_p18, tf_p18)


# 19 downscale 2x -> rotate 180 -> grey frame
def gi_p19(rng):
    s = rng.randint(11, 14) if rng.random() < 0.35 else rng.randint(3, 10); t = rng.randint(3, 14)
    small = _dots(rng, s, t, colours(rng, rng.randint(2, 4), exclude=(0, 5)), rng.uniform(0.3, 0.7))
    return _scale(small, 2) if any(v for row in small for v in row) else None
def tf_p19(g):
    H, W = dims(g)
    if H % 2 or W % 2: return None
    small = [[g[r][c] for c in range(0, W, 2)] for r in range(0, H, 2)]
    return _frame(rot90(rot90(small)), 5)
rule("downscale_half_rotate_180_grey_frame", "Shrink the grid by half taking each 2 by 2 block's colour, then turn it upside down, then add a grey border around it.", gi_p19, tf_p19)


# 20 connect pairs -> mark crossings grey -> keep only endpoints and crossings
def gi_p20(rng):
    h, w = _size(rng, 7, 18); g = blank(h, w); cols = colours(rng, rng.randint(2, 4), exclude=(0, 5)); hs, vs = [], []
    for i, col in enumerate(cols):
        for _ in range(30):
            if i % 2 == 0:
                r = rng.randrange(h); a, b = sorted(rng.sample(range(w), 2))
                if b - a >= 2 and all(abs(r - r2) >= 1 for r2, _, _ in hs) and all(not (a <= c2 <= b and y0 <= r <= y1 and (r in (y0, y1) or c2 in (a, b))) for c2, y0, y1 in vs):
                    hs.append((r, a, b)); g[r][a] = g[r][b] = col; break
            else:
                c = rng.randrange(w); a, b = sorted(rng.sample(range(h), 2))
                if b - a >= 2 and all(abs(c - c2) >= 1 for c2, _, _ in vs) and all(not (a <= r2 <= b and x0 <= c <= x1 and (r2 in (a, b) or c in (x0, x1))) for r2, x0, x1 in hs):
                    vs.append((c, a, b)); g[a][c] = g[b][c] = col; break
    cross = any(x0 < c < x1 and y0 < r < y1 for r, x0, x1 in hs for c, y0, y1 in vs)
    return g if cross and len(cells(g, lambda v: v != 0)) == 2 * len(cols) else None
def tf_p20(g):
    H, W = dims(g); lines = []
    for col in set(v for row in g for v in row if v):
        pts = cells(g, lambda v: v == col)
        if len(pts) != 2: return None
        (r1, c1), (r2, c2) = pts
        lines.append({(r1, x) for x in range(c1, c2 + 1)} if r1 == r2 else {(y, c1) for y in range(r1, r2 + 1)} if c1 == c2 else set())
    out = copy(g)
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            for r, c in lines[i] & lines[j]:
                if g[r][c] == 0: out[r][c] = 5
    return out
rule("connect_pairs_grey_crossings_keep_points", "Join each same-colour pair with a straight line, then paint grey every cell where two lines cross, then erase the lines again leaving only the pair cells and the grey crossings.", gi_p20, tf_p20)


# 21 hollow objects -> mirror -> grey frame
def gi_p21(rng):
    h, w = _size(rng, 7, 16); n = rng.randint(2, 4) + (2 if h * w > 400 else 0)
    if h > 28 or w > 28: return None
    res = _rects(rng, h, w, n, [False] * n, [rng.choice([c for c in COLOURS if c != 5]) for _ in range(n)], lo=3, hi=7)
    return res[0] if res else None
def tf_p21(g):
    inner = [row[1:-1] for row in _hollow(_frame(g, 0))[1:-1]]
    return _frame(flip_h(inner), 5)
rule("hollow_objects_mirror_grey_frame", "Hollow every rectangle to its outline, then mirror the grid left to right, then add a grey border around the whole grid.", gi_p21, tf_p21)


# 22 delete largest -> recolour rest in its colour -> gravity
def gi_p22(rng):
    g = _scene(rng, 3, 6, 2, 8, 7, 18)
    if g is None: return None
    obs = objects(g, 0); s = sorted(len(o) for o in obs)
    if s[-1] == s[-2]: return None
    big = max(obs, key=len)
    return g if any(g[o[0][0]][o[0][1]] != g[big[0][0]][big[0][1]] for o in obs) else None
def tf_p22(g):
    H, W = dims(g); obs = objects(g, 0); big = max(obs, key=len); col = g[big[0][0]][big[0][1]]; out = blank(H, W)
    for o in obs:
        if o is big: continue
        for r, c in o: out[r][c] = col
    return _gravity(out)
rule("delete_largest_recolour_rest_gravity", "Delete the largest object, then repaint every remaining object in the deleted object's colour, then let all cells fall to the floor.", gi_p22, tf_p22)


# 23 split panels -> count cells per panel as bars -> sort ascending
def gi_p23(rng):
    k = rng.randint(2, 5)
    if rng.random() < 0.35:
        ph = rng.randint(21, 30); pw = rng.randint(max(2, (21 - k + 1) // k + 1), (30 - k + 1) // k)
    else:
        ph, pw = rng.randint(3, 8), rng.randint(2, 5)
    if k * pw + k - 1 > 30: return None
    sep = rng.choice([c for c in COLOURS if c != 5]); cols = [rng.choice([c for c in COLOURS if c not in (sep, 5)]) for _ in range(k)]
    ns = rng.sample(range(1, min(30, ph * pw) + 1), k); panels = []
    for col, n in zip(cols, ns):
        panels.append(sprinkle(rng, blank(ph, pw), n, col))
    g = _join_h(panels, sep); sp = _split_h(g)
    return g if sp and len(sp[0]) == k else None
def tf_p23(g):
    panels, sep = _split_h(g)
    bars = sorted(((sum(1 for row in p for v in row if v), next(v for row in p for v in row if v)) for p in panels))
    H = bars[-1][0]; out = blank(H, len(bars))
    for c, (n, col) in enumerate(bars):
        for r in range(H - n, H): out[r][c] = col
    return out
rule("panels_cell_counts_bars_sorted_ascending", "Split the grid at the separators, then draw for each panel a vertical bar in its colour as tall as its cell count, then order the bars shortest on the left.", gi_p23, tf_p23)


# 24 crop single object -> scale 2x -> grey checker
def gi_p24(rng):
    g = _scene(rng, 1, 1, 4, 12, 7, 18, cols=[c for c in COLOURS if c != 5], more=False)
    return g if g is not None and len(objects(g, 0)) == 1 else None
def tf_p24(g):
    s = _scale(_mask_crop(g, objects(g, 0)[0]), 2)
    return [[5 if v and (r + c) % 2 else v for c, v in enumerate(row)] for r, row in enumerate(s)]
rule("crop_object_scale2_grey_checker", "Cut out the single object, then enlarge it two times, then paint grey every coloured cell whose row and column indices add to an odd number.", gi_p24, tf_p24)


# 25 sort rows by count -> compact left -> recolour by row majority
def gi_p25(rng):
    h, w = _size(rng, 4, 14); cols = colours(rng, rng.randint(2, 3)); g = blank(h, w)
    for r in range(h):
        k = rng.randint(0, w); main = rng.choice(cols)
        for c in rng.sample(range(w), k): g[r][c] = main if rng.random() < 0.7 else rng.choice(cols)
    return g if any(v for row in g for v in row) else None
def tf_p25(g):
    rows = sorted(g, key=lambda row: -sum(1 for v in row if v)); out = []
    for row in _compact_left(rows):
        cnt = {}
        for v in row:
            if v: cnt[v] = cnt.get(v, 0) + 1
        if cnt:
            top = sorted(cnt.values())
            if len(top) > 1 and top[-1] == top[-2]: return None
            m = max(cnt, key=cnt.get); out.append([m if v else 0 for v in row])
        else:
            out.append(row)
    return out
rule("rows_sorted_by_count_compact_majority_colour", "Reorder the rows so the fullest is on top, then slide each row's cells to the left wall, then repaint each row entirely in its most common colour.", gi_p25, tf_p25)


# 26 mirror complete -> rise -> hollow
def gi_p26(rng):
    h = rng.randint(21, 30) if rng.random() < 0.35 else rng.randint(5, 14); w = rng.randint(2, 12); left = blank(h, w)
    for _ in range(rng.randint(h, h * w // 2 + h)):
        left[rng.randrange(h)][rng.randrange(w)] = rng.choice(COLOURS)
    return [row + [0] * w for row in left]
def tf_p26(g):
    w = len(g[0]) // 2; m = [row[:w] + row[:w][::-1] for row in g]
    up = flip_v(_gravity(flip_v(m)))
    return [row[1:-1] for row in _hollow(_frame(up, 0))[1:-1]]
rule("mirror_complete_rise_hollow", "Fill the empty right half with the mirror of the left half, then let every cell rise to the top, then empty each cell whose four side neighbours are all coloured.", gi_p26, tf_p26)


# 27 invert -> keep largest component -> crop
def gi_p27(rng):
    h, w = _size(rng, 7, 18); col = rng.choice(COLOURS); g = blank(h, w)
    for r in rng.sample(range(1, h - 1), rng.randint(1, 3)):
        for c in range(w): g[r][c] = col
    for c in rng.sample(range(1, w - 1), rng.randint(1, 3)):
        for r in range(h): g[r][c] = col
    sprinkle(rng, g, rng.randint(2, 6 + h * w // 40), col)
    inv = [[0 if v else col for v in row] for row in g]; comps = components(inv, col)
    s = sorted(len(o) for o in comps)
    if len(s) < 2 or s[-1] == s[-2]: return None
    big = max(comps, key=len); r0, c0, r1, c1 = bbox(big)
    return g if len(big) < (r1 - r0 + 1) * (c1 - c0 + 1) else None
def tf_p27(g):
    col = next(v for row in g for v in row if v); inv = [[0 if v else col for v in row] for row in g]
    comps = components(inv, col); big = max(comps, key=len)
    return _mask_crop(inv, big)
rule("invert_keep_largest_region_crop", "Swap coloured and empty cells, then keep only the largest connected region of the result, then cut it to its bounding box.", gi_p27, tf_p27)


# 28 recolour by quadrant -> rotate -> crop
def gi_p28(rng):
    g = _scene(rng, 3, 7, 2, 6, 8, 18)
    if g is None: return None
    H, W = dims(g); mh, mw = H // 2, W // 2
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o)
        if (r0 < mh) != (r1 < mh) or (c0 < mw) != (c1 < mw): return None
    qs = {(bbox(o)[0] < mh, bbox(o)[1] < mw) for o in objects(g, 0)}
    return g if len(qs) >= 2 else None
def tf_p28(g):
    H, W = dims(g); mh, mw = H // 2, W // 2; out = blank(H, W)
    for o in objects(g, 0):
        r0, c0, _, _ = bbox(o); q = (0 if r0 < mh else 2) + (0 if c0 < mw else 1) + 1
        for r, c in o: out[r][c] = q
    out = rot90(out)
    return crop(out, *_bbox_all(out))
rule("quadrant_recolour_rotate_crop", "Recolour each object 1, 2, 3 or 4 by the quadrant it sits in (top-left, top-right, bottom-left, bottom-right), then turn the grid a quarter turn clockwise, then cut it to the bounding box of the objects.", gi_p28, tf_p28)


# 29 extend right -> transpose -> longest line grey
def gi_p29(rng):
    h, w = _size(rng, 6, 18); g = blank(h, w); rows = rng.sample(range(h), rng.randint(2, min(h, 7))); lens = set()
    for r in rows:
        c = rng.randrange(w)
        if w - c in lens: return None
        lens.add(w - c); g[r][c] = rng.choice([x for x in COLOURS if x != 5])
    return g
def tf_p29(g):
    H, W = dims(g); out = blank(H, W)
    for r in range(H):
        for c in range(W):
            if g[r][c]:
                for x in range(c, W): out[r][x] = g[r][c]
    t = transpose(out); lines = objects(t, 0, conn8=False); big = max(lines, key=len)
    for r, c in big: t[r][c] = 5
    return t
rule("extend_right_transpose_longest_grey", "Every cell extends a line of its colour to the right wall, then the grid is transposed, then the longest line is repainted grey.", gi_p29, tf_p29)


# 30 stack by width -> mirror -> frame
def gi_p30(rng):
    g = _scene(rng, 2, 5, 2, 8, 8, 18, cols=[c for c in COLOURS if c != 5], more=False)
    if g is None: return None
    obs = objects(g, 0); ws = [bbox(o)[3] - bbox(o)[1] for o in obs]
    if len(set(ws)) != len(ws): return None
    return g if sum(bbox(o)[2] - bbox(o)[0] + 1 for o in obs) + len(obs) + 1 <= 30 and max(ws) + 3 <= 30 else None
def tf_p30(g):
    obs = sorted(objects(g, 0), key=lambda o: bbox(o)[3] - bbox(o)[1]); subs = [_mask_crop(g, o) for o in obs]
    W = max(len(s[0]) for s in subs); H = sum(len(s) for s in subs) + len(subs) - 1; out = blank(H, W); r = 0
    for s in subs:
        paste(out, s, r, 0); r += len(s) + 1
    return _frame(flip_h(out), 5)
rule("stack_by_width_mirror_grey_frame", "Cut out the objects and stack them top to bottom from narrowest to widest, left-aligned with one empty row between, then mirror the stack left to right, then add a grey border.", gi_p30, tf_p30)


# 31 swap two colours -> gravity right -> remove singles
def gi_p31(rng):
    h, w = _size(rng, 5, 15); a, b = colours(rng, 2)
    g = _dots(rng, h, w, [a, b], rng.uniform(0.15, 0.4)); cnt = counts(g)
    return g if cnt.get(a) and cnt.get(b) else None
def tf_p31(g):
    cs = sorted({v for row in g for v in row if v})
    if len(cs) != 2: return None
    a, b = cs; sw = [[b if v == a else a if v == b else 0 for v in row] for row in g]
    right = [[0] * sum(1 for v in row if not v) + [v for v in row if v] for row in sw]
    return _denoise(right)
rule("swap_two_colours_gravity_right_denoise", "Exchange the two colours, then slide every cell right to the wall, then erase any cell left with no coloured neighbour.", gi_p31, tf_p31)


# 32 split -> and -> crop -> scale 2x
def gi_p32(rng):
    res = _panels(rng, 2, ph_hi=15, pw_hi=8, wide=True)
    if res is None: return None
    g, sep = res; (a, b), _ = _split_h(g); ph, pw = dims(a)
    both = [[a[r][c] if a[r][c] and b[r][c] else 0 for c in range(pw)] for r in range(ph)]
    bb = _bbox_all(both)
    return g if bb and (bb[2] - bb[0] + 1) * 2 <= 30 and (bb[3] - bb[1] + 1) * 2 <= 30 and len({v for row in both for v in row}) > 1 else None
def tf_p32(g):
    (a, b), sep = _split_h(g); ph, pw = dims(a)
    both = [[a[r][c] if a[r][c] and b[r][c] else 0 for c in range(pw)] for r in range(ph)]
    bb = _bbox_all(both)
    return _scale(crop(both, *bb), 2) if bb else None
rule("panels_and_crop_upscale_2x", "Split the grid at the separator, then keep only the cells coloured in both panels using the left panel's colour, then cut to their bounding box and enlarge two times.", gi_p32, tf_p32)


# 33 grow plus -> overlaps grey -> crop
def gi_p33(rng):
    h, w = _size(rng, 6, 18); g = blank(h, w); cols = [c for c in COLOURS if c != 5]
    n = rng.randint(2, 6) + (4 if h * w > 400 else 0)
    for _ in range(n):
        g[rng.randrange(h)][rng.randrange(w)] = rng.choice(cols)
    return g if len(cells(g, lambda v: v != 0)) >= 2 else None
def tf_p33(g):
    H, W = dims(g); out = blank(H, W); cover = blank(H, W)
    for r, c in cells(g, lambda v: v != 0):
        for dr, dc in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            y, x = r + dr, c + dc
            if 0 <= y < H and 0 <= x < W: out[y][x] = g[r][c]; cover[y][x] += 1
    for r in range(H):
        for c in range(W):
            if cover[r][c] > 1: out[r][c] = 5
    return crop(out, *_bbox_all(out))
rule("grow_plus_overlaps_grey_crop", "Every cell grows into a plus sign of its colour, then every cell reached by two or more plus signs turns grey, then the grid is cut to the bounding box of the colour.", gi_p33, tf_p33)


# 34 colour histogram -> sort tallest left -> scale 2x
def gi_p34(rng):
    h, w = _size(rng, 4, 10); k = rng.randint(2, 4); d = min(0.35, rng.uniform(0.4, 1.0) * 9 * k / (h * w))
    g = _dots(rng, h, w, colours(rng, k), d); cnt = counts(g); cnt.pop(0, None)
    return g if len(cnt) >= 2 and len(set(cnt.values())) == len(cnt) and max(cnt.values()) <= 15 else None
def tf_p34(g):
    cnt = counts(g); cnt.pop(0, None); bars = sorted(cnt.items(), key=lambda kv: -kv[1]); H = bars[0][1]
    out = blank(H, len(bars))
    for c, (col, n) in enumerate(bars):
        for r in range(H - n, H): out[r][c] = col
    return _scale(out, 2)
rule("colour_histogram_tallest_left_2x", "Count the cells of each colour, then draw one vertical bar per colour as tall as its count with the tallest on the left, then enlarge the chart two times.", gi_p34, tf_p34)


# 35 rotate -> tile side by side -> grey frame
def gi_p35(rng):
    h, w = rng.randint(2, 14), (rng.randint(21, 28) if rng.random() < 0.35 else rng.randint(2, 13))
    g = _dots(rng, h, w, colours(rng, rng.randint(1, 3), exclude=(0, 5)), rng.uniform(0.3, 0.7))
    return g if any(v for row in g for v in row) else None
def tf_p35(g):
    r = rot90(g)
    return _frame([row + row for row in r], 5)
rule("rotate_tile_side_by_side_grey_frame", "Turn the grid a quarter turn clockwise, then place two copies side by side, then add a grey border around the pair.", gi_p35, tf_p35)


# 36 denoise -> fill bounding boxes -> recolour by height
def gi_p36(rng):
    g = _scene(rng, 2, 5, 3, 8, 8, 18, margin=2)
    if g is None: return None
    return sprinkle(rng, g, rng.randint(2, 8), rng.choice(COLOURS))
def tf_p36(g):
    d = _denoise(g); H, W = dims(g); out = blank(H, W)
    for o in sorted(objects(d, 0), key=lambda o: bbox(o)):
        r0, c0, r1, c1 = bbox(o)
        if r1 - r0 + 1 > 9: return None
        rect(out, r0, c0, r1, c1, r1 - r0 + 1)
    return out if any(v for row in out for v in row) else None
rule("denoise_fill_bboxes_colour_by_height", "Erase every isolated single cell, then replace each remaining object by its filled bounding box, then colour each box with the number of rows it spans.", gi_p36, tf_p36, digits=True)


# 37 delete smallest -> flip vertical -> border objects grey
def gi_p37(rng):
    g = _scene(rng, 3, 6, 2, 8, 7, 18, cols=[c for c in COLOURS if c != 5])
    if g is None: return None
    obs = objects(g, 0); s = sorted(len(o) for o in obs)
    if s[0] == s[1]: return None
    small = min(obs, key=len)
    return g if any(_touches_border(g, o) for o in obs if o is not small) and not all(_touches_border(g, o) for o in obs if o is not small) else None
def tf_p37(g):
    H, W = dims(g); obs = objects(g, 0); small = min(obs, key=len); out = copy(g)
    for r, c in small: out[r][c] = 0
    out = flip_v(out)
    for o in objects(out, 0):
        if _touches_border(out, o):
            for r, c in o: out[r][c] = 5
    return out
rule("delete_smallest_flip_border_objects_grey", "Delete the smallest object, then flip the grid top to bottom, then repaint grey every object touching the grid edge.", gi_p37, tf_p37)


# 38 enclosed background grey -> erase objects -> crop
def gi_p38(rng):
    h, w = _size(rng, 8, 18); n = rng.randint(2, 3) + (2 if h * w > 400 else 0)
    res = _rects(rng, h, w, n, [True] * n, [rng.choice([c for c in COLOURS if c != 5]) for _ in range(n)], lo=3, hi=8)
    return res[0] if res else None
def tf_p38(g):
    H, W = dims(g); mark = copy(g)
    for r in range(H):
        for c in range(W):
            if (r in (0, H - 1) or c in (0, W - 1)) and mark[r][c] == 0: flood(mark, r, c, -1)
    out = [[5 if v == 0 else 0 for v in row] for row in mark]
    bb = _bbox_all(out)
    return crop(out, *bb) if bb else None
rule("enclosed_background_grey_erase_objects_crop", "Paint grey every empty cell sealed off from the grid edge, then erase all the original objects, then cut the grid to the bounding box of the grey.", gi_p38, tf_p38)


# 39 transpose -> gravity -> row parity colours
def gi_p39(rng):
    h, w = _size(rng, 5, 15); g = blank(h, w)
    for _ in range(rng.randint(3, h * w // 3)):
        g[rng.randrange(h)][rng.randrange(w)] = rng.choice(COLOURS)
    return g if any(v for row in g for v in row) else None
def tf_p39(g):
    out = _gravity(transpose(g)); H = len(out)
    return [[(1 if (H - 1 - r) % 2 == 0 else 2) if v else 0 for v in row] for r, row in enumerate(out)]
rule("transpose_gravity_rows_alternate_colours", "Transpose the grid, then let every cell fall to the floor, then recolour the bottom row 1, the next row up 2, alternating upward.", gi_p39, tf_p39)


# 40 crop inside grey frame -> rotate 180 -> scale 2x
def gi_p40(rng):
    h, w = _size(rng, 7, 18); ih, iw = rng.randint(2, min(h - 2, 13)), rng.randint(2, min(w - 2, 13))
    r0, c0 = rng.randint(0, h - ih - 2), rng.randint(0, w - iw - 2); g = blank(h, w)
    rect(g, r0, c0, r0 + ih + 1, c0 + iw + 1, 5, fill=False)
    inner = _dots(rng, ih, iw, colours(rng, rng.randint(1, 3), exclude=(0, 5)), rng.uniform(0.3, 0.7))
    if not any(v for row in inner for v in row): return None
    paste(g, inner, r0 + 1, c0 + 1)
    sprinkle(rng, g, rng.randint(0, 6), rng.choice([c for c in COLOURS if c != 5]))
    return g if inner != rot90(rot90(inner)) else None
def tf_p40(g):
    fr = [o for o in components(g, 5, conn8=False) if len(o) >= 8]
    if len(fr) != 1: return None
    r0, c0, r1, c1 = bbox(fr[0])
    return _scale(rot90(rot90(crop(g, r0 + 1, c0 + 1, r1 - 1, c1 - 1))), 2)
rule("crop_grey_frame_interior_rotate_180_2x", "Cut out the inside of the grey frame, then turn it upside down, then enlarge it two times.", gi_p40, tf_p40)
