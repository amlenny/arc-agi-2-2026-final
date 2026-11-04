# b005_compound.py -- COMPOUND / PANELS / PATTERNS: two-step rules, separator-divided panels combined,
# periodic pattern continuation, noise removal, template stamping, stencils, legend-keyed growth.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


# ---------------------------------------------------------------- helpers (local to this batch)
def _scene(rng, k_lo=2, k_hi=5, n_lo=3, n_hi=8, lo=6, hi=18, margin=1, cols=None):
    h, w = size(rng, lo, hi); g = blank(h, w)
    k = rng.randint(k_lo, k_hi)
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
    """Panels between full-height single-colour separator columns. Returns (panels, sep) or None."""
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


def _panel_grid(rng, k, make_panel, k_lo=2, k_hi=6, w_lo=2, w_hi=6, cols_excl=()):
    """k panels side by side with a fresh separator colour; None unless _split_h recovers exactly k panels."""
    ph, pw = rng.randint(k_lo, k_hi), rng.randint(w_lo, w_hi)
    if k * pw + k - 1 > 30:
        return None
    sep = rng.choice([c for c in COLOURS if c not in cols_excl])
    panels = make_panel(ph, pw, sep)
    if panels is None:
        return None
    g = _join_h(panels, sep)
    sp = _split_h(g)
    if sp is None or len(sp[0]) != k:
        return None
    return g


def _nz(p):
    return sum(1 for row in p for v in row if v)


def _isolated8(g, r, c):
    h, w = dims(g)
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if (dr or dc) and 0 <= r + dr < h and 0 <= c + dc < w and g[r + dr][c + dc]:
                return False
    return True


def _remove_isolated(g):
    out = copy(g); h, w = dims(g)
    for r in range(h):
        for c in range(w):
            if g[r][c] and _isolated8(g, r, c):
                out[r][c] = 0
    return out


def _add_noise(rng, g, k, cols):
    """k single cells, each with all eight neighbours empty, in random colours from cols."""
    h, w = dims(g); n = 0
    for _ in range(k * 30):
        if n >= k:
            break
        r, c = rng.randrange(h), rng.randrange(w)
        if g[r][c] == 0 and _isolated8(g, r, c):
            g[r][c] = rng.choice(cols); n += 1
    return n


def _blobs(g):
    """8-connected groups of non-empty cells regardless of colour."""
    h, w = dims(g); seen, out = set(), []
    for r in range(h):
        for c in range(w):
            if g[r][c] == 0 or (r, c) in seen: continue
            st, comp = [(r, c)], []; seen.add((r, c))
            while st:
                y, x = st.pop(); comp.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and (ny, nx) not in seen and g[ny][nx]:
                            seen.add((ny, nx)); st.append((ny, nx))
            out.append(comp)
    return out


def _gravity(g):
    h, w = dims(g); out = blank(h, w)
    for c in range(w):
        col = [g[r][c] for r in range(h) if g[r][c] != 0]
        for i, v in enumerate(reversed(col)):
            out[h - 1 - i][c] = v
    return out


def _min_period(seq):
    for p in range(1, len(seq) // 2 + 1):
        if all(seq[i] == seq[i - p] for i in range(p, len(seq))):
            return p
    return None


# ================================================================ COMPOUND (two steps)
# 1 gravity, then every column stack takes the colour of its bottom cell.
def gi_grav_bottom(rng):
    h, w = size(rng, 5, 15); g = blank(h, w)
    for _ in range(rng.randint(w, h * w // 2)):
        g[rng.randrange(h)][rng.randrange(w)] = rng.choice(COLOURS)
    return g
def tf_grav_bottom(g):
    out = _gravity(g); h, w = dims(g)
    for c in range(w):
        for r in range(h):
            if out[r][c]:
                out[r][c] = out[h - 1][c]
    return out
rule("gravity_then_bottom_colour", "All cells fall straight down, then each column's stack is recoloured with the colour of its bottom cell.", gi_grav_bottom, tf_grav_bottom)


# 2 crop the largest object, then place its mirror image beside it.
def gi_crop_mirror(rng):
    g = _scene(rng, 2, 5, 3, 10)
    if g is None: return None
    s = sorted(len(o) for o in objects(g, 0))
    return g if s[-1] != s[-2] else None
def tf_crop_mirror(g):
    big = max(objects(g, 0), key=len); sub = crop(g, *bbox(big))
    return [row + row[::-1] for row in sub]
rule("crop_largest_mirror_pair", "Cut out the largest object and output it side by side with its left-right mirror image.", gi_crop_mirror, tf_crop_mirror)


# 3 remove isolated noise cells, then complete the left-right symmetry.
def gi_denoise_mirror(rng):
    h, w2 = rng.randint(5, 14), rng.randint(3, 7); left = blank(h, w2)
    k = rng.randint(1, 3); img = colours(rng, 3); noise = [c for c in COLOURS if c not in img]
    if place_shapes(rng, left, [random_shape(rng, rng.randint(3, 7)) for _ in range(k)], [rng.choice(img) for _ in range(k)], margin=1) is None:
        return None
    g = [row + row[::-1] for row in left]
    nz = cells(g, lambda v: v != 0)
    for r, c in rng.sample(nz, rng.randint(1, max(1, len(nz) // 4))):
        g[r][c] = 0
    if any(_isolated8(g, r, c) for r, c in cells(g, lambda v: v != 0)): return None
    if _add_noise(rng, g, rng.randint(2, 6), noise) < 2: return None
    return g
def tf_denoise_mirror(g):
    out = _remove_isolated(g); h, w = dims(g)
    for r in range(h):
        for c in range(w):
            if out[r][c] == 0 and out[r][w - 1 - c]:
                out[r][c] = out[r][w - 1 - c]
    return out
rule("denoise_then_mirror_complete", "Delete every isolated single cell, then fill each empty cell from its left-right mirror partner.", gi_denoise_mirror, tf_denoise_mirror)


# 4 compact each row to the left, then colour the row by how many cells it holds.
def gi_compact_count(rng):
    h, w = size(rng, 4, 12); g = blank(h, w)
    for r in range(h):
        for c in rng.sample(range(w), rng.randint(0, min(w, 8))):
            g[r][c] = rng.choice(COLOURS)
    return g if any(v for row in g for v in row) else None
def tf_compact_count(g):
    h, w = dims(g); out = blank(h, w)
    for r in range(h):
        n = sum(1 for v in g[r] if v)
        for c in range(n):
            out[r][c] = min(n, 9)
    return out
rule("compact_left_count_colour", "Each row's cells slide to the left edge and are recoloured with the number of cells in that row.", gi_compact_count, tf_compact_count, digits=True)


# 5 remove isolated noise cells, then crop to the surviving object.
def gi_denoise_crop(rng):
    h, w = size(rng, 7, 18); g = blank(h, w); col = rng.choice(COLOURS)
    if place_shapes(rng, g, [random_shape(rng, rng.randint(5, 14))], [col], margin=1) is None: return None
    return g if _add_noise(rng, g, rng.randint(3, 10), COLOURS) >= 3 else None
def tf_denoise_crop(g):
    d = _remove_isolated(g); nz = cells(d, lambda v: v != 0)
    return crop(d, *bbox(nz)) if nz else None
rule("denoise_then_crop_object", "Delete every isolated single cell, then output the bounding box of what remains.", gi_denoise_crop, tf_denoise_crop)


# 6 crop the smallest object, then double its scale.
def gi_crop_small(rng):
    g = _scene(rng, 2, 5, 2, 8)
    if g is None: return None
    s = sorted(len(o) for o in objects(g, 0))
    return g if s[0] != s[1] else None
def tf_crop_small(g):
    small = min(objects(g, 0), key=len); sub = crop(g, *bbox(small))
    return [[v for v in row for _ in (0, 1)] for row in sub for _ in (0, 1)]
rule("crop_smallest_upscale_2x", "Cut out the smallest object and output it enlarged to twice its size.", gi_crop_small, tf_crop_small)


# 7 flip top-bottom, then swap the two colours.
def gi_flip_swap(rng):
    h, w = size(rng, 4, 14); a, b = colours(rng, 2); g = blank(h, w)
    for _ in range(rng.randint(4, h * w // 2)):
        g[rng.randrange(h)][rng.randrange(w)] = rng.choice([a, b])
    return g if len({v for row in g for v in row if v}) == 2 else None
def tf_flip_swap(g):
    cs = sorted({v for row in g for v in row if v})
    if len(cs) != 2: return None
    a, b = cs
    return [[b if v == a else a if v == b else 0 for v in row] for row in g[::-1]]
rule("flip_vertical_swap_colours", "Flip the grid top to bottom, then exchange its two colours.", gi_flip_swap, tf_flip_swap)


# 8 delete the colour that only occurs as scattered single cells, then let the rest fall.
def gi_scatter_grav(rng):
    noise = rng.choice(COLOURS); g = _scene(rng, 2, 5, 2, 7, 7, 16, cols=[c for c in COLOURS if c != noise])
    if g is None: return None
    h, w = dims(g); n = 0
    for _ in range(200):
        r, c = rng.randrange(h), rng.randrange(w)
        if g[r][c] == 0 and all(not (0 <= r + dr < h and 0 <= c + dc < w) or g[r + dr][c + dc] != noise for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            g[r][c] = noise; n += 1
        if n >= rng.randint(4, 10): break
    return g if n >= 3 else None
def _singleton_colours(g):
    out = set()
    for col in {v for row in g for v in row if v}:
        if all(len(o) == 1 for o in components(g, col)):
            out.add(col)
    return out
def tf_scatter_grav(g):
    bad = _singleton_colours(g)
    return _gravity([[0 if v in bad else v for v in row] for row in g])
rule("remove_scattered_then_gravity", "Erase the colour that appears only as scattered single cells, then let every remaining cell fall to the floor.", gi_scatter_grav, tf_scatter_grav)


# 9 line the rectangles up in a row, bottom-aligned, sorted by area.
def gi_rect_lineup(rng):
    h, w = size(rng, 8, 18); g = blank(h, w); k = rng.randint(2, 4); shapes, areas = [], set()
    for _ in range(k):
        rh, rw = rng.randint(1, 4), rng.randint(1, 4)
        if rh * rw in areas: return None
        areas.add(rh * rw); shapes.append([(r, c) for r in range(rh) for c in range(rw)])
    if place_shapes(rng, g, shapes, colours(rng, k), margin=1) is None: return None
    return g
def tf_rect_lineup(g):
    obs = objects(g, 0); rects = []
    for o in obs:
        r0, c0, r1, c1 = bbox(o)
        if len(o) != (r1 - r0 + 1) * (c1 - c0 + 1): return None
        rects.append((len(o), r1 - r0 + 1, c1 - c0 + 1, g[r0][c0]))
    if len({a for a, _, _, _ in rects}) != len(rects): return None
    rects.sort(); H = max(rh for _, rh, _, _ in rects); W = sum(rw for _, _, rw, _ in rects) + len(rects) - 1
    out = blank(H, W); x = 0
    for _, rh, rw, col in rects:
        rect(out, H - rh, x, H - 1, x + rw - 1, col); x += rw + 1
    return out
rule("rectangles_lineup_by_area", "The rectangles are lined up in one row, bottom-aligned and one cell apart, smallest area on the left.", gi_rect_lineup, tf_rect_lineup)


# 10 crop the inside of the frame and invert it with the frame colour.
def gi_frame_invert(rng):
    h, w = size(rng, 6, 16); g = blank(h, w); f, c = colours(rng, 2)
    ih, iw = rng.randint(2, h - 4), rng.randint(2, w - 4); r0, c0 = rng.randint(0, h - ih - 2), rng.randint(0, w - iw - 2)
    rect(g, r0, c0, r0 + ih + 1, c0 + iw + 1, f, fill=False)
    n = 0
    for r in range(r0 + 1, r0 + ih + 1):
        for cc in range(c0 + 1, c0 + iw + 1):
            if rng.random() < 0.45: g[r][cc] = c; n += 1
    return g if 0 < n < ih * iw else None
def tf_frame_invert(g):
    f = g[[r for r in range(len(g)) if any(g[r])][0]][min(c for c in range(len(g[0])) if any(g[r][c] for r in range(len(g))))]
    o = max(components(g, f), key=len); r0, c0, r1, c1 = bbox(o)
    inner = crop(g, r0 + 1, c0 + 1, r1 - 1, c1 - 1)
    return [[f if v == 0 else 0 for v in row] for row in inner]
rule("frame_interior_inverted", "Cut out the inside of the frame; empty cells there take the frame colour and the filled cells become empty.", gi_frame_invert, tf_frame_invert)


# ================================================================ PANELS
# 11 overlay: leftmost panel on top.
def gi_overlay(rng):
    k = rng.randint(2, 4); cs = colours(rng, k + 1)
    return _panel_grid(rng, k, lambda ph, pw, sep: [_dots(rng, ph, pw, [cs[i]], 0.3) for i in range(k)], 3, 7, 3, 6, cols_excl=cs)
def tf_overlay(g):
    sp = _split_h(g)
    if sp is None: return None
    panels, _ = sp; h, w = dims(panels[0]); out = blank(h, w)
    for p in reversed(panels):
        for r in range(h):
            for c in range(w):
                if p[r][c]: out[r][c] = p[r][c]
    return out
rule("panels_overlay_left_on_top", "The panels are stacked into one; where panels disagree the panel further to the left shows.", gi_overlay, tf_overlay)


# 12 majority vote across an odd number of panels.
def gi_majority(rng):
    k = rng.choice([3, 5]); col = rng.choice(COLOURS)
    return _panel_grid(rng, k, lambda ph, pw, sep: [_dots(rng, ph, pw, [col], 0.4) for _ in range(k)], 3, 7, 2, 5, cols_excl=[col])
def tf_majority(g):
    sp = _split_h(g)
    if sp is None: return None
    panels, _ = sp; h, w = dims(panels[0]); out = blank(h, w)
    for r in range(h):
        for c in range(w):
            vs = [p[r][c] for p in panels if p[r][c]]
            if len(vs) * 2 > len(panels): out[r][c] = vs[0]
    return out
rule("panels_vote_more_than_half", "Output one panel where a cell is coloured only if more than half of the panels colour it.", gi_majority, tf_majority)


# 13 pick the panel that differs from all the others.
def gi_odd_panel(rng):
    k = rng.randint(3, 5); cs = colours(rng, rng.randint(1, 3))
    def mk(ph, pw, sep):
        base = _dots(rng, ph, pw, cs, 0.4); odd = rng.randrange(k); panels = []
        for i in range(k):
            p = copy(base)
            if i == odd:
                for _ in range(rng.randint(1, 3)):
                    r, c = rng.randrange(ph), rng.randrange(pw); p[r][c] = rng.choice([x for x in cs + [0] if x != p[r][c]])
            panels.append(p)
        return panels if sum(1 for p in panels if p != base) == 1 else None
    return _panel_grid(rng, k, mk, 2, 6, 2, 5, cols_excl=cs)
def tf_odd_panel(g):
    sp = _split_h(g)
    if sp is None: return None
    panels, _ = sp
    odd = [p for p in panels if sum(1 for q in panels if q == p) == 1]
    return odd[0] if len(odd) == 1 and len(panels) >= 3 else None
rule("panels_pick_the_odd_one", "All panels are identical except one; output that different panel.", gi_odd_panel, tf_odd_panel)


# 14 copy the template panel into every panel holding a marker cell.
def gi_template_panels(rng):
    k = rng.randint(3, 5); m = rng.choice(COLOURS); cs = [c for c in COLOURS if c != m]
    def mk(ph, pw, sep):
        tpl = _dots(rng, ph, pw, rng.sample(cs, 2), 0.5)
        if _nz(tpl) < 3 or _nz(tpl) == ph * pw: return None
        kinds = [rng.random() < 0.6 for _ in range(k - 1)]
        if not any(kinds): return None
        panels = []
        for has in kinds:
            p = blank(ph, pw)
            if has: p[rng.randrange(ph)][rng.randrange(pw)] = m
            panels.append(p)
        panels.insert(rng.randrange(k), tpl); return panels
    return _panel_grid(rng, k, mk, 2, 6, 2, 5, cols_excl=[m])
def tf_template_panels(g):
    sp = _split_h(g)
    if sp is None: return None
    panels, sep = sp
    tpl = [p for p in panels if _nz(p) > 1]
    if len(tpl) != 1: return None
    out = [p if _nz(p) == 0 else tpl[0] for p in panels]
    return _join_h(out, sep)
rule("panels_template_onto_markers", "The one panel holding a picture is copied into every panel that holds a single marker cell; empty panels stay empty.", gi_template_panels, tf_template_panels)


# 15 xor of two panels.
def gi_xor(rng):
    col = rng.choice(COLOURS)
    return _panel_grid(rng, 2, lambda ph, pw, sep: [_dots(rng, ph, pw, [col], 0.45) for _ in range(2)], 3, 10, 3, 10, cols_excl=[col])
def tf_xor(g):
    sp = _split_h(g)
    if sp is None or len(sp[0]) != 2: return None
    a, b = sp[0]; h, w = dims(a)
    return [[(a[r][c] or b[r][c]) if bool(a[r][c]) != bool(b[r][c]) else 0 for c in range(w)] for r in range(h)]
rule("panels_xor", "Output one panel keeping the cells coloured in exactly one of the two panels.", gi_xor, tf_xor)


# 16 intersection of two panels drawn in the separator colour.
def gi_and(rng):
    a, b = colours(rng, 2)
    return _panel_grid(rng, 2, lambda ph, pw, sep: [_dots(rng, ph, pw, [a], 0.55), _dots(rng, ph, pw, [b], 0.55)], 3, 10, 3, 10, cols_excl=[a, b])
def tf_and(g):
    sp = _split_h(g)
    if sp is None or len(sp[0]) != 2: return None
    (a, b), sep = sp; h, w = dims(a)
    out = [[sep if a[r][c] and b[r][c] else 0 for c in range(w)] for r in range(h)]
    return out if any(v for row in out for v in row) else None
rule("panels_and_in_separator_colour", "Output one panel marking, in the separator's colour, the cells coloured in both panels.", gi_and, tf_and)


# 17 reorder the panels by how many coloured cells they hold.
def gi_sort_panels(rng):
    k = rng.randint(3, 5); cs = colours(rng, rng.randint(1, 3))
    def mk(ph, pw, sep):
        ps = [_dots(rng, ph, pw, cs, rng.choice([0.15, 0.3, 0.5, 0.7])) for _ in range(k)]
        ns = [_nz(p) for p in ps]
        return ps if len(set(ns)) == k and ns != sorted(ns) else None
    return _panel_grid(rng, k, mk, 2, 6, 2, 5, cols_excl=cs)
def tf_sort_panels(g):
    sp = _split_h(g)
    if sp is None: return None
    panels, sep = sp
    if len({_nz(p) for p in panels}) != len(panels): return None
    return _join_h(sorted(panels, key=_nz), sep)
rule("panels_sorted_by_cell_count", "The panels are reordered left to right by increasing number of coloured cells; separators stay.", gi_sort_panels, tf_sort_panels)


# 18 each panel floods to its most frequent colour.
def gi_flood_panels(rng):
    k = rng.randint(2, 4); cs = colours(rng, rng.randint(2, 4))
    def mk(ph, pw, sep):
        ps = []
        for _ in range(k):
            p = _dots(rng, ph, pw, cs, 0.6); cnt = counts(p); cnt.pop(0, None)
            if not cnt: return None
            top = sorted(cnt.values())
            if len(top) > 1 and top[-1] == top[-2]: return None
            ps.append(p)
        return ps
    return _panel_grid(rng, k, mk, 3, 6, 3, 6, cols_excl=cs)
def tf_flood_panels(g):
    sp = _split_h(g)
    if sp is None: return None
    panels, sep = sp; out = []
    for p in panels:
        cnt = counts(p); cnt.pop(0, None); top = sorted(cnt.items(), key=lambda kv: -kv[1])
        if not top or (len(top) > 1 and top[0][1] == top[1][1]): return None
        out.append(blank(len(p), len(p[0]), top[0][0]))
    return _join_h(out, sep)
rule("panels_flood_dominant_colour", "Every panel is filled solid with the colour that appears most often inside it.", gi_flood_panels, tf_flood_panels)


# 19 four quadrants split by a cross; output the quadrant with the most coloured cells.
def gi_quadrants(rng):
    qh, qw = rng.randint(2, 7), rng.randint(2, 7); cs = colours(rng, rng.randint(1, 3)); sep = rng.choice([c for c in COLOURS if c not in cs])
    qs = [_dots(rng, qh, qw, cs, rng.choice([0.2, 0.4, 0.6])) for _ in range(4)]
    ns = sorted(_nz(q) for q in qs)
    if ns[-1] == ns[-2] or ns[-1] == 0: return None
    g = blank(2 * qh + 1, 2 * qw + 1, sep)
    for i, q in enumerate(qs):
        paste(g, q, (i // 2) * (qh + 1), (i % 2) * (qw + 1))
    return g
def tf_quadrants(g):
    h, w = dims(g); mr, mc = h // 2, w // 2
    qs = [crop(g, 0, 0, mr - 1, mc - 1), crop(g, 0, mc + 1, mr - 1, w - 1), crop(g, mr + 1, 0, h - 1, mc - 1), crop(g, mr + 1, mc + 1, h - 1, w - 1)]
    ns = sorted(_nz(q) for q in qs)
    return max(qs, key=_nz) if ns[-1] != ns[-2] else None
rule("quadrant_with_most_cells", "A cross of separator lines makes four quadrants; output the quadrant with the most coloured cells.", gi_quadrants, tf_quadrants)


# 20 panels side by side become panels stacked top to bottom.
def gi_stack(rng):
    k = rng.randint(2, 4); cs = colours(rng, rng.randint(1, 4))
    return _panel_grid(rng, k, lambda ph, pw, sep: [_dots(rng, ph, pw, cs, 0.4) for _ in range(k)], 2, 6, 2, 8, cols_excl=cs)
def tf_stack(g):
    sp = _split_h(g)
    if sp is None: return None
    panels, sep = sp; out = []
    for i, p in enumerate(panels):
        if i: out.append([sep] * len(p[0]))
        out += [row[:] for row in p]
    return out if len(out) <= 30 else None
rule("panels_restack_vertically", "The side-by-side panels are restacked top to bottom in the same order, separators becoming horizontal lines.", gi_stack, tf_stack)


# 21 one row listing each panel's dominant colour.
def gi_dominant_row(rng):
    k = rng.randint(2, 6); cs = colours(rng, rng.randint(2, 5))
    def mk(ph, pw, sep):
        ps = []
        for _ in range(k):
            main = rng.choice(cs); p = _dots(rng, ph, pw, [c for c in cs if c != main] + [0], 0.3)
            for r in range(ph):
                for c in range(pw):
                    if rng.random() < 0.65: p[r][c] = main
            cnt = counts(p); cnt.pop(0, None); top = sorted(cnt.values())
            if len(top) > 1 and top[-1] == top[-2]: return None
            ps.append(p)
        return ps
    return _panel_grid(rng, k, mk, 3, 6, 3, 5, cols_excl=cs)
def tf_dominant_row(g):
    sp = _split_h(g)
    if sp is None: return None
    row = []
    for p in sp[0]:
        cnt = counts(p); cnt.pop(0, None); top = sorted(cnt.items(), key=lambda kv: -kv[1])
        if len(top) > 1 and top[0][1] == top[1][1]: return None
        row.append(top[0][0])
    return [row]
rule("panels_dominant_colour_row", "Output a single row giving, left to right, the most frequent colour of each panel.", gi_dominant_row, tf_dominant_row)


# ================================================================ PATTERNS
# 22 continue each row's periodic pattern across the grid.
def gi_row_period(rng):
    h = rng.randint(2, 10); p = rng.randint(2, 5); L = 2 * p + rng.randint(0, p); w = rng.randint(L + 2, min(30, L + 14))
    g = blank(h, w)
    for r in range(h):
        motif = [rng.choice(COLOURS) for _ in range(p)]
        for c in range(L): g[r][c] = motif[c % p]
    return g
def tf_row_period(g):
    h, w = dims(g); L = max(c for row in g for c, v in enumerate(row) if v) + 1
    for p in range(1, L // 2 + 1):
        if all(g[r][c] == g[r][c - p] for r in range(h) for c in range(p, L)):
            return [[g[r][c % p] for c in range(w)] for r in range(h)]
    return None
rule("extend_row_pattern_right", "The repeating pattern begun at the left of every row is continued to the right edge.", gi_row_period, tf_row_period)


# 23 continue a vertically repeating band pattern downward.
def gi_tile_down(rng):
    w = rng.randint(2, 12); p = rng.randint(2, 4); L = 2 * p + rng.randint(0, p); h = rng.randint(L + 2, min(30, L + 14))
    g = blank(h, w); motif = [[rng.choice(COLOURS) for _ in range(w)] for _ in range(p)]
    for r in range(L): g[r] = motif[r % p][:]
    return g
def tf_tile_down(g):
    h, w = dims(g); L = max(r for r in range(h) if any(g[r])) + 1
    for p in range(1, L // 2 + 1):
        if all(g[r] == g[r - p] for r in range(p, L)):
            return [g[r % p][:] for r in range(h)]
    return None
rule("extend_band_pattern_down", "The repeating band of rows at the top is continued down to the bottom edge.", gi_tile_down, tf_tile_down)


# 24 continue a staircase.
def gi_stairs(rng):
    s = rng.randint(1, 3); K = rng.randint(2 * s, 3 * s + 1); w = rng.randint(K + 2, min(30, K + 12)); col = rng.choice(COLOURS)
    h = rng.randint(w // s + 1, min(30, w // s + 4)) if w // s + 1 <= 30 else None
    if h is None: return None
    g = blank(h, w)
    for c in range(K):
        for r in range(h - (c // s + 1), h): g[r][c] = col
    return g
def tf_stairs(g):
    h, w = dims(g); hs = [sum(1 for r in range(h) if g[r][c]) for c in range(w)]
    col = next(v for row in g for v in row if v); s = hs.count(1); K = next((c for c, v in enumerate(hs) if v == 0), w)
    if s == 0 or K >= w or any(hs[c] != c // s + 1 for c in range(K)): return None
    out = blank(h, w)
    for c in range(w):
        for r in range(max(0, h - (c // s + 1)), h): out[r][c] = col
    return out
rule("staircase_continue_right", "The staircase of equal-width steps rising from the bottom-left is continued to the right edge.", gi_stairs, tf_stairs)


# 25 continue concentric rings inward.
def _ring(h, w, r, c):
    return min(r, c, h - 1 - r, w - 1 - c)
def gi_rings(rng):
    p = rng.randint(2, 3); seq = colours(rng, p); L = p + rng.randint(0, 1)
    h, w = rng.randint(2 * L + 3, 20), rng.randint(2 * L + 3, 20); g = blank(h, w)
    for r in range(h):
        for c in range(w):
            k = _ring(h, w, r, c)
            if k < L: g[r][c] = seq[k % p]
    return g
def tf_rings(g):
    h, w = dims(g); n = (min(h, w) + 1) // 2; seq = []
    for k in range(n):
        vs = {g[r][c] for r in range(h) for c in range(w) if _ring(h, w, r, c) == k}
        if len(vs) != 1: return None
        if vs == {0}: break
        seq.append(vs.pop())
    if not seq or len(seq) == n: return None
    p = len(seq)
    for q in range(1, len(seq)):
        if all(seq[i] == seq[i - q] for i in range(q, len(seq))): p = q; break
    return [[seq[_ring(h, w, r, c) % p] for c in range(w)] for r in range(h)]
rule("concentric_rings_continue_inward", "The outer rings set a repeating colour sequence that is continued ring by ring to the centre.", gi_rings, tf_rings)


# 26 repair the holes in a tiled pattern.
def gi_tile_holes(rng):
    ph, pw = rng.randint(2, 4), rng.randint(2, 4); h, w = rng.randint(ph * 2 + 1, 14), rng.randint(pw * 2 + 1, 14)
    cs = colours(rng, rng.randint(2, 4)); motif = [[rng.choice(cs) for _ in range(pw)] for _ in range(ph)]
    g = [[motif[r % ph][c % pw] for c in range(w)] for r in range(h)]
    for r, c in rng.sample([(r, c) for r in range(h) for c in range(w)], rng.randint(2, max(2, h * w // 8))):
        g[r][c] = 0
    return g
def tf_tile_holes(g):
    h, w = dims(g); best = None
    for ph in range(1, h + 1):
        for pw in range(1, w + 1):
            if best and ph * pw >= best[0]: continue
            cls, ok = {}, True
            for r in range(h):
                for c in range(w):
                    v = g[r][c]
                    if not v: continue
                    k = (r % ph, c % pw)
                    if cls.setdefault(k, v) != v: ok = False; break
                if not ok: break
            if ok and len(cls) == ph * pw: best = (ph * pw, ph, pw, cls)
    if not best: return None
    _, ph, pw, cls = best
    return [[cls[(r % ph, c % pw)] for c in range(w)] for r in range(h)]
rule("repair_tiled_pattern_holes", "The grid is a repeating tile with some cells blanked out; fill each blank from the matching cell of another copy.", gi_tile_holes, tf_tile_holes)


# 27 continue diagonal stripes.
def gi_diag(rng):
    k = rng.randint(2, 4); seq = colours(rng, k); L = k + rng.randint(0, k); h, w = size(rng, 4, 14)
    if L >= h + w - 2: return None
    return [[seq[(r + c) % k] if r + c < L else 0 for c in range(w)] for r in range(h)]
def tf_diag(g):
    h, w = dims(g); seq = []
    for d in range(h + w - 1):
        vs = {g[r][d - r] for r in range(h) if 0 <= d - r < w}
        if len(vs) != 1: return None
        if vs == {0}: break
        seq.append(vs.pop())
    if not seq or len(seq) == h + w - 1: return None
    p = len(seq)
    for q in range(1, len(seq)):
        if all(seq[i] == seq[i - q] for i in range(q, len(seq))): p = q; break
    return [[seq[(r + c) % p] for c in range(w)] for r in range(h)]
rule("diagonal_stripes_continue", "The diagonal colour stripes begun in the top-left corner are continued across the whole grid.", gi_diag, tf_diag)


# 28 each row is the row above shifted one step right.
def gi_cyclic(rng):
    h, w = rng.randint(2, 12), rng.randint(3, 12); row = [rng.choice(COLOURS) for _ in range(w)]
    if len(set(row)) < 2: return None
    return [row] + [[0] * w for _ in range(h - 1)]
def tf_cyclic(g):
    h, w = dims(g); row = g[0]
    return [row[-r % w:] + row[:-r % w] if r % w else row[:] for r in range(h)]
# rows_cyclic_shift_from_top dropped 2026-10-12 (trio review: behavioural duplicate or one global operation)
# 29 the block in the top-left corner is tiled over the whole grid.
def gi_corner_tile(rng):
    kh, kw = rng.randint(1, 4), rng.randint(1, 4); h, w = rng.randint(kh + 1, 20), rng.randint(kw + 1, 20)
    if kh == 1 and kw == 1: return None
    block = [[rng.choice(COLOURS) for _ in range(kw)] for _ in range(kh)]
    if len({v for row in block for v in row}) < 2: return None
    g = blank(h, w); paste(g, block, 0, 0); return g
def tf_corner_tile(g):
    h, w = dims(g); nz = cells(g, lambda v: v != 0); r0, c0, r1, c1 = bbox(nz)
    if (r0, c0) != (0, 0): return None
    block = crop(g, 0, 0, r1, c1); kh, kw = dims(block)
    return [[block[r % kh][c % kw] for c in range(w)] for r in range(h)]
rule("corner_block_tiles_grid", "The coloured block in the top-left corner is repeated as a tile across the entire grid.", gi_corner_tile, tf_corner_tile)


# ================================================================ NOISE REMOVAL
# 30 delete isolated single cells.
def gi_isolated(rng):
    g = _scene(rng, 1, 4, 2, 8, 7, 18)
    if g is None: return None
    return g if _add_noise(rng, g, rng.randint(3, 10), COLOURS) >= 2 else None
def tf_isolated(g):
    out = _remove_isolated(g)
    return out if out != g else None
rule("remove_isolated_cells", "Every coloured cell with no coloured neighbour, including diagonals, is erased.", gi_isolated, tf_isolated)


# 31 delete the colour that occurs only as scattered single cells.
def gi_singleton_colour(rng):
    noise = rng.choice(COLOURS); g = _scene(rng, 2, 5, 2, 8, 7, 18, cols=[c for c in COLOURS if c != noise])
    if g is None: return None
    h, w = dims(g); n = 0
    for _ in range(300):
        r, c = rng.randrange(h), rng.randrange(w)
        if g[r][c] == 0 and all(not (0 <= r + dr < h and 0 <= c + dc < w) or g[r + dr][c + dc] != noise for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            g[r][c] = noise; n += 1
        if n >= rng.randint(5, 14): break
    return g if n >= 4 else None
def tf_singleton_colour(g):
    bad = _singleton_colours(g)
    return [[0 if v in bad else v for v in row] for row in g] if bad else None
rule("remove_singleton_colour", "The colour whose cells never touch another cell of the same colour is erased entirely; the objects stay.", gi_singleton_colour, tf_singleton_colour)


# 32 denoise a four-fold symmetric picture by voting among mirror images.
def gi_sym_denoise(rng):
    h2, w2 = rng.randint(3, 8), rng.randint(3, 8); cs = colours(rng, rng.randint(2, 4))
    q = _dots(rng, h2, w2, cs, 0.6); top = [row + row[::-1] for row in q]; g = top + [row[:] for row in top[::-1]]
    h, w = dims(g); seen = set(); n = 0
    for _ in range(100):
        r, c = rng.randrange(h), rng.randrange(w); orb = (min(r, h - 1 - r), min(c, w - 1 - c))
        if orb in seen: continue
        seen.add(orb); g[r][c] = rng.choice([x for x in cs + [0] if x != g[r][c]]); n += 1
        if n >= rng.randint(1, max(1, h2 * w2 // 4)): break
    return g
def tf_sym_denoise(g):
    h, w = dims(g); out = blank(h, w)
    for r in range(h):
        for c in range(w):
            vs = [g[r][c], g[r][w - 1 - c], g[h - 1 - r][c], g[h - 1 - r][w - 1 - c]]
            best = max(set(vs), key=vs.count)
            if vs.count(best) < 3: return None
            out[r][c] = best
    return out
rule("denoise_fourfold_symmetric", "The picture is mirror-symmetric both ways; every cell is reset to the value shared by at least three of its four mirror positions.", gi_sym_denoise, tf_sym_denoise)


# 33 fill single-cell holes inside solid blocks.
def gi_holes(rng):
    h, w = size(rng, 7, 18); g = blank(h, w); k = rng.randint(1, 3); shapes = []
    for _ in range(k):
        rh, rw = rng.randint(3, 6), rng.randint(3, 6); shapes.append([(r, c) for r in range(rh) for c in range(rw)])
    if place_shapes(rng, g, shapes, colours(rng, k), margin=1) is None: return None
    n = 0
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o)
        for _ in range(rng.randint(1, 3)):
            r, c = rng.randint(r0 + 1, r1 - 1), rng.randint(c0 + 1, c1 - 1)
            if all(g[r + dr][c + dc] for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                g[r][c] = 0; n += 1
    return g if n else None
def tf_holes(g):
    out = copy(g); h, w = dims(g)
    for r in range(1, h - 1):
        for c in range(1, w - 1):
            nb = {g[r - 1][c], g[r + 1][c], g[r][c - 1], g[r][c + 1]}
            if g[r][c] == 0 and len(nb) == 1 and 0 not in nb: out[r][c] = nb.pop()
    return out
rule("fill_single_cell_holes", "An empty cell whose four side neighbours all share one colour is filled with that colour.", gi_holes, tf_holes)


# 34 keep only the largest object.
def gi_keep_largest(rng):
    g = _scene(rng, 3, 7, 1, 9, 7, 18)
    if g is None: return None
    s = sorted(len(o) for o in objects(g, 0))
    return g if s[-1] != s[-2] else None
def tf_keep_largest(g):
    big = max(objects(g, 0), key=len); h, w = dims(g); out = blank(h, w)
    for r, c in big: out[r][c] = g[r][c]
    return out
rule("keep_only_largest_object", "Everything except the largest object is erased.", gi_keep_largest, tf_keep_largest)


# 35 each object is recoloured to the colour most of its cells have.
def gi_majority_obj(rng):
    h, w = size(rng, 7, 18); g = blank(h, w); k = rng.randint(1, 4)
    shapes = [random_shape(rng, rng.randint(6, 12)) for _ in range(k)]
    if place_shapes(rng, g, shapes, [rng.choice(COLOURS) for _ in range(k)], margin=1) is None: return None
    for o in _blobs(g):
        main = g[o[0][0]][o[0][1]]
        for r, c in rng.sample(o, rng.randint(1, 2)):
            g[r][c] = rng.choice([x for x in COLOURS if x != main])
    return g
def tf_majority_obj(g):
    out = copy(g)
    for o in _blobs(g):
        vs = [g[r][c] for r, c in o]; best = max(set(vs), key=vs.count)
        if vs.count(best) * 2 <= len(vs): return None
        for r, c in o: out[r][c] = best
    return out
rule("object_majority_recolour", "Each connected object is repainted entirely in the colour held by most of its cells.", gi_majority_obj, tf_majority_obj)


# ================================================================ STAMPING / MASKS / LEGENDS
# 36 the 3x3 motif in the top-left corner is stamped centred on every marker cell.
def gi_stamp_motif(rng):
    h, w = size(rng, 8, 18); m = rng.choice(COLOURS); cs = [c for c in COLOURS if c != m]; g = blank(h, w)
    for r in range(3):
        for c in range(3):
            if rng.random() < 0.7 or (r, c) == (1, 1): g[r][c] = rng.choice(cs)
    if len({g[r][c] for r in range(3) for c in range(3)} - {0}) < 2: return None
    n = 0
    for _ in range(100):
        r, c = rng.randint(1, h - 2), rng.randint(1, w - 2)
        if (r >= 5 or c >= 5) and all(g[y][x] == 0 for y in range(r - 2, r + 3) for x in range(c - 2, c + 3) if 0 <= y < h and 0 <= x < w):
            g[r][c] = m; n += 1
        if n >= rng.randint(1, 4): break
    return g if n else None
def tf_stamp_motif(g):
    motif = crop(g, 0, 0, 2, 2); out = copy(g); h, w = dims(g)
    for r in range(h):
        for c in range(w):
            if g[r][c] and (r > 3 or c > 3): paste(out, motif, r - 1, c - 1)
    return out
rule("stamp_corner_motif_on_markers", "The three-by-three picture in the top-left corner is stamped centred on every marker cell elsewhere.", gi_stamp_motif, tf_stamp_motif)


# 37 copy the one shape onto every single marker cell, in the marker's colour.
def gi_stamp_shape(rng):
    h, w = size(rng, 8, 18); g = blank(h, w); s = rng.choice(COLOURS); shape = random_shape(rng, rng.randint(4, 7))
    sh, sw = max(r for r, _ in shape) + 1, max(c for _, c in shape) + 1; a0 = shape[0]
    k = rng.randint(1, 4); shapes = [shape] + [[(0, 0)]] * k; cs = [s] + [rng.choice([c for c in COLOURS if c != s]) for _ in range(k)]
    if place_shapes(rng, g, shapes, cs, margin=1) is None: return None
    return g if all(0 <= r - a0[0] and r - a0[0] + sh <= h and 0 <= c - a0[1] and c - a0[1] + sw <= w for r, c in cells(g, lambda v: v and v != s)) else None
def tf_stamp_shape(g):
    obs = components(g, lambda v: v != 0, conn8=True); big = [o for o in obs if len(o) > 1]
    if len(big) != 1: return None
    sh = sorted(big[0]); r0, c0 = sh[0]; out = copy(g)
    for o in obs:
        if len(o) == 1:
            (r, c), = o
            for y, x in sh:
                yy, xx = r + y - r0, c + x - c0
                if 0 <= yy < len(g) and 0 <= xx < len(g[0]): out[yy][xx] = g[r][c]
    return out
rule("stamp_shape_in_marker_colour", "The single multi-cell shape is copied onto every lone marker cell, drawn in that marker's colour and anchored at the shape's top-left cell.", gi_stamp_shape, tf_stamp_shape)


# 38 stencil: the right panel's marks select which cells of the left pattern survive.
def gi_stencil(rng):
    cs = colours(rng, rng.randint(2, 4)); m = rng.choice([c for c in COLOURS if c not in cs])
    def mk(ph, pw, sep):
        pat = _dots(rng, ph, pw, cs, 1.0); mask = _dots(rng, ph, pw, [m], 0.45)
        if _nz(mask) in (0, ph * pw): return None
        return [pat, mask]
    return _panel_grid(rng, 2, mk, 3, 10, 3, 10, cols_excl=cs + [m])
def tf_stencil(g):
    sp = _split_h(g)
    if sp is None or len(sp[0]) != 2: return None
    pat, mask = sp[0]; h, w = dims(pat)
    return [[pat[r][c] if mask[r][c] else 0 for c in range(w)] for r in range(h)]
rule("stencil_right_panel_selects_left", "The right panel is a stencil: output the left panel keeping only the cells the stencil marks.", gi_stencil, tf_stencil)


# 39 a stencil blob covers horizontal stripes; reveal the stripes only under the stencil.
def gi_stripe_stencil(rng):
    p = rng.randint(2, 3); seq = colours(rng, p); m = rng.choice([c for c in COLOURS if c not in seq])
    h, w = rng.randint(2 * p + 2, 16), rng.randint(5, 16); g = [[seq[r % p] for _ in range(w)] for r in range(h)]
    shape = random_shape(rng, rng.randint(6, min(24, h * w // 3))); sh, sw = max(r for r, _ in shape) + 1, max(c for _, c in shape) + 1
    if sh > h or sw > w: return None
    r0, c0 = rng.randint(0, h - sh), rng.randint(0, w - sw)
    for r, c in shape: g[r0 + r][c0 + c] = m
    pure = {g[r][0] for r in range(h) if len(set(g[r])) == 1}
    return g if pure == set(seq) else None
def tf_stripe_stencil(g):
    h, w = dims(g); pure = {row[0] for row in g if len(set(row)) == 1}
    ms = {v for row in g for v in row} - pure
    if len(ms) != 1: return None
    m = ms.pop(); out = blank(h, w)
    for r in range(h):
        sc = set(g[r]) - {m}
        if len(sc) != 1: return None
        sc = sc.pop()
        for c in range(w):
            if g[r][c] == m: out[r][c] = sc
    return out
rule("stencil_reveals_stripes", "A blob covers a striped background; output only the stripe colours that lie under the blob, everything else empty.", gi_stripe_stencil, tf_stripe_stencil)


# 40 grow a one-cell ring around each object in the colour the legend assigns to its colour.
def gi_ring_legend(rng):
    k = rng.randint(1, 3); cs = colours(rng, 2 * k); h, w = size(rng, 9, 18); g = blank(h, w)
    for i in range(k): g[0][2 * i], g[0][2 * i + 1] = cs[2 * i], cs[2 * i + 1]
    body = blank(h - 3, w); n = rng.randint(1, 4)
    if place_shapes(rng, body, [random_shape(rng, rng.randint(1, 5)) for _ in range(n)], [cs[2 * rng.randrange(k)] for _ in range(n)], margin=2) is None: return None
    paste(g, body, 3, 0); return g
def tf_ring_legend(g):
    h, w = dims(g); leg = {}
    for c in range(0, w - 1, 2):
        if g[0][c] and g[0][c + 1]: leg[g[0][c]] = g[0][c + 1]
        else: break
    out = copy(g)
    for o in components(g, lambda v: v != 0, conn8=True):
        if o[0][0] < 2: continue
        col = g[o[0][0]][o[0][1]]
        if col not in leg: continue
        for r, c in o:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    y, x = r + dr, c + dc
                    if 2 <= y < h and 0 <= x < w and g[y][x] == 0: out[y][x] = leg[col]
    return out
rule("grow_ring_colour_from_legend", "The top row pairs each object colour with a ring colour; every object grows a one-cell border in its paired colour.", gi_ring_legend, tf_ring_legend)
