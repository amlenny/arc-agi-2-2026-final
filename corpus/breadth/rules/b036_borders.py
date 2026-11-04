# b036_borders.py -- 40 rules on the theme of drawing borders/outlines by rule: haloes, inner edges,
# hull outlines, grid frames, hole-count-keyed thickness, and related variants. One author (b036).
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

NB4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
NB8 = NB4 + [(-1, -1), (-1, 1), (1, -1), (1, 1)]


def _scene(rng, k_lo=2, k_hi=4, n_lo=3, n_hi=9, lo=10, hi=30, margin=1):
    h, w = size(rng, lo, hi)
    g = blank(h, w)
    k = rng.randint(k_lo, k_hi)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    cols = colours(rng, k)
    if place_shapes(rng, g, shapes, cols, margin=margin) is None:
        return None
    return g


def _ring(g, obj, bg, thickness=1, conn8=False):
    """bg cells within `thickness` steps outward of obj, staying background."""
    H, W = dims(g)
    oset = set(obj)
    nb = NB8 if conn8 else NB4
    ring, cur = set(), set(oset)
    for _ in range(thickness):
        nxt = set()
        for r, c in cur:
            for dr, dc in nb:
                nr, nc = r + dr, c + dc
                if 0 <= nr < H and 0 <= nc < W and (nr, nc) not in oset and g[nr][nc] == bg:
                    nxt.add((nr, nc))
        ring |= nxt
        cur = nxt
    return ring


def _inner_edge(obj, conn8=False):
    """cells of obj that touch a cell outside obj (the object's own outer ring)."""
    oset = set(obj)
    nb = NB8 if conn8 else NB4
    out = set()
    for r, c in oset:
        for dr, dc in nb:
            if (r + dr, c + dc) not in oset:
                out.add((r, c)); break
    return out


def _touches_any(obj, other_cells, conn8=True):
    nb = NB8 if conn8 else NB4
    for r, c in obj:
        for dr, dc in nb:
            if (r + dr, c + dc) in other_cells:
                return True
    return False


def _touches_edge(obj, H, W):
    return any(r == 0 or c == 0 or r == H - 1 or c == W - 1 for r, c in obj)


def _holes(g, obj, bg):
    """count of bg-connected components fully enclosed by obj's bounding box, not reaching the box border."""
    r0, c0, r1, c1 = bbox(obj)
    oset = set(obj)
    seen, n = set(), 0
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if (r, c) in oset or (r, c) in seen or g[r][c] != bg:
                continue
            comp, st, touches_box_edge = [], [(r, c)], False
            seen.add((r, c))
            while st:
                y, x = st.pop(); comp.append((y, x))
                if y in (r0, r1) or x in (c0, c1):
                    touches_box_edge = True
                for dy, dx in NB4:
                    ny, nx = y + dy, x + dx
                    if r0 <= ny <= r1 and c0 <= nx <= c1 and (ny, nx) not in seen and g[ny][nx] == bg:
                        seen.add((ny, nx)); st.append((ny, nx))
            if not touches_box_edge:
                n += 1
    return n


# 1 halo only the objects that touch nothing else.
def gi_isolated(rng):
    return _scene(rng, 3, 5, 3, 8, margin=2)
def tf_isolated(g):
    bg = bg_colour(g); obs = objects(g, bg); out = copy(g); changed = False
    for o in obs:
        others = set(c for oo in obs if oo is not o for c in oo)
        if not _touches_any(o, others):
            col = g[o[0][0]][o[0][1]]
            for r, c in _ring(g, o, bg, 1):
                out[r][c] = col
            changed = True
    return out if changed else None
rule("halo_around_isolated_objects_only", "Draw a one-cell halo, in the object's own colour, around every object that touches no other object.", gi_isolated, tf_isolated)


# 2 halo coloured by the object's nearest neighbour's colour.
def gi_nearest(rng):
    return _scene(rng, 3, 5, 3, 8, margin=3)
def tf_nearest(g):
    bg = bg_colour(g); obs = objects(g, bg)
    if len(obs) < 2:
        return None
    out = copy(g)
    for o in obs:
        best, bd = None, 1e9
        for oo in obs:
            if oo is o:
                continue
            d = min(abs(r1 - r2) + abs(c1 - c2) for r1, c1 in o for r2, c2 in oo)
            if d < bd:
                bd, best = d, oo
        ncol = g[best[0][0]][best[0][1]]
        for r, c in _ring(g, o, bg, 1):
            out[r][c] = ncol
    return out
rule("halo_colour_from_nearest_object", "Each object gets a one-cell halo coloured like its nearest other object.", gi_nearest, tf_nearest)


# 3 two-cell-thick halo around every object.
def gi_thick(rng):
    return _scene(rng, 2, 4, 3, 7, lo=12, hi=30, margin=3)
def tf_thick(g):
    bg = bg_colour(g); obs = objects(g, bg); out = copy(g)
    for o in obs:
        col = g[o[0][0]][o[0][1]]
        for r, c in _ring(g, o, bg, 2):
            out[r][c] = col
    return out
rule("halo_two_cells_thick", "Draw a halo two cells thick, in the object's colour, around every object.", gi_thick, tf_thick)


# 4 halo only on the side facing the grid centre.
def gi_facecentre(rng):
    return _scene(rng, 2, 5, 3, 8, margin=2)
def tf_facecentre(g):
    bg = bg_colour(g); H, W = dims(g); obs = objects(g, bg); out = copy(g)
    cr, cc = (H - 1) / 2, (W - 1) / 2
    for o in obs:
        col = g[o[0][0]][o[0][1]]
        orr, occ = sum(r for r, _ in o) / len(o), sum(c for _, c in o) / len(o)
        ring = _ring(g, o, bg, 1)
        for r, c in ring:
            if (r - orr) * (cr - orr) + (c - occ) * (cc - occ) >= 0:
                out[r][c] = col
    return out
rule("halo_facing_grid_centre_only", "Each object gets a one-cell border only on the side of it that faces the grid's centre.", gi_facecentre, tf_facecentre)


# 5 border the whole grid edge with the grid's most common colour.
def gi_gridedge(rng):
    g = _scene(rng, 2, 5, 3, 8, margin=1)
    return g
def tf_gridedge(g):
    H, W = dims(g); out = copy(g); col = bg_colour(g)
    other = max(((v, c) for v in set(v for row in g for v in row) for c in [v] if v != col), default=None)
    paint = next((v for v in range(1, 10) if v != col), 1)
    for c in range(W):
        out[0][c] = paint; out[H - 1][c] = paint
    for r in range(H):
        out[r][0] = paint; out[r][W - 1] = paint
    return out
rule("grid_edge_border_common_colour", "Draw a one-cell frame around the whole grid, using a colour distinct from the background.", gi_gridedge, tf_gridedge)


# 6 outline the convex hull of each object (background cells on the hull boundary).
def gi_hull(rng):
    return _scene(rng, 1, 3, 6, 12, lo=12, hi=30, margin=3)
def tf_hull(g):
    bg = bg_colour(g); obs = objects(g, bg); out = copy(g)
    for o in obs:
        col = g[o[0][0]][o[0][1]]
        r0, c0, r1, c1 = bbox(o)
        oset = set(o)
        for r in range(max(0, r0 - 1), min(len(g), r1 + 2)):
            for c in range(max(0, c0 - 1), min(len(g[0]), c1 + 2)):
                if g[r][c] != bg or (r, c) in oset:
                    continue
                if (r in (r0 - 1, r1 + 1) and c0 <= c <= c1) or (c in (c0 - 1, c1 + 1) and r0 <= r <= r1):
                    out[r][c] = col
    return out
rule("convex_hull_outline_ring", "Outline each object's bounding box with a one-cell ring in the object's colour.", gi_hull, tf_hull)


# 7 dashed halo: every other cell of the one-cell ring.
def gi_dashed(rng):
    return _scene(rng, 2, 4, 4, 9, lo=10, hi=28, margin=2)
def tf_dashed(g):
    bg = bg_colour(g); obs = objects(g, bg); out = copy(g)
    for o in obs:
        col = g[o[0][0]][o[0][1]]
        ring = sorted(_ring(g, o, bg, 1))
        for i, (r, c) in enumerate(ring):
            if i % 2 == 0:
                out[r][c] = col
    return out
rule("dashed_halo_alternating_cells", "Draw a halo around each object but colour only every other ring cell, in reading order.", gi_dashed, tf_dashed)


# 8 halo corners only: mark the 4 bbox corners just outside each object.
def gi_corners(rng):
    return _scene(rng, 2, 5, 4, 10, margin=2)
def tf_corners(g):
    bg = bg_colour(g); obs = objects(g, bg); out = copy(g); H, W = dims(g); changed = False
    for o in obs:
        col = g[o[0][0]][o[0][1]]
        r0, c0, r1, c1 = bbox(o)
        for r, c in ((r0 - 1, c0 - 1), (r0 - 1, c1 + 1), (r1 + 1, c0 - 1), (r1 + 1, c1 + 1)):
            if 0 <= r < H and 0 <= c < W and g[r][c] == bg:
                out[r][c] = col; changed = True
    return out if changed else None
rule("halo_corners_only", "Mark only the four diagonal corners just outside each object's bounding box, in the object's colour.", gi_corners, tf_corners)


# 9 halo objects larger than k cells only.
def gi_bigonly(rng):
    return _scene(rng, 3, 6, 2, 10, margin=2)
def tf_bigonly(g):
    bg = bg_colour(g); obs = objects(g, bg); out = copy(g); k = 5; changed = False
    for o in obs:
        if len(o) > k:
            col = g[o[0][0]][o[0][1]]
            for r, c in _ring(g, o, bg, 1):
                out[r][c] = col
            changed = True
    return out if changed else None
rule("halo_objects_above_size_threshold", "Draw a one-cell halo only around objects bigger than five cells.", gi_bigonly, tf_bigonly)


# 10 shared halo between two touching objects drawn grey.
def gi_shared(rng):
    h, w = size(rng, 10, 30); g = blank(h, w)
    col1, col2 = colours(rng, 2)
    rh1, rw1 = rng.randint(2, 6), rng.randint(2, 6)
    rh2, rw2 = rng.randint(2, 6), rng.randint(2, 6)
    r0 = rng.randint(1, max(1, h - max(rh1, rh2) - 2))
    c0 = rng.randint(1, max(1, w // 2 - rw1 - 1))
    rect(g, r0, c0, r0 + rh1 - 1, c0 + rw1 - 1, col1)
    c1 = c0 + rw1  # touching directly, no gap
    if c1 + rw2 - 1 >= w:
        return None
    rect(g, r0, c1, r0 + rh2 - 1, c1 + rw2 - 1, col2)
    if len(objects(g, 0)) != 2:
        return None
    return g
def tf_shared(g):
    bg = bg_colour(g); obs = objects(g, bg)
    if len(obs) != 2:
        return None
    a, b = obs
    aset, bset = set(a), set(b)
    shared = set()
    for r, c in a:
        for dr, dc in NB8:
            if (r + dr, c + dc) in bset:
                shared.add((r, c)); shared.add((r + dr, c + dc))
    if not shared:
        return None
    out = copy(g)
    for r, c in shared:
        out[r][c] = 5
    return out
rule("shared_halo_between_touching_objects_grey", "Where two objects touch, recolour the touching cells of both grey.", gi_shared, tf_shared)


# 11 border each region of empty space with the colour of the nearest object.
def gi_region(rng):
    return _scene(rng, 2, 4, 3, 7, lo=12, hi=30, margin=2)
def tf_region(g):
    bg = bg_colour(g); obs = objects(g, bg)
    if len(obs) < 1:
        return None
    out = copy(g)
    for comp in components(g, bg, conn8=False):
        ring = set()
        for r, c in comp:
            for dr, dc in NB4:
                nr, nc = r + dr, c + dc
                if 0 <= nr < len(g) and 0 <= nc < len(g[0]) and g[nr][nc] != bg:
                    ring.add((nr, nc))
        if not ring:
            continue
        col = max(set(g[r][c] for r, c in ring), key=lambda cc: sum(1 for r, c in ring if g[r][c] == cc))
        for r, c in comp:
            if any(0 <= r + dr < len(g) and 0 <= c + dc < len(g[0]) and g[r + dr][c + dc] != bg for dr, dc in NB4):
                out[r][c] = col
    return out
rule("border_each_empty_region", "Every empty region gets its boundary cells coloured like the object colour most adjacent to it.", gi_region, tf_region)


# 12 halo that stops where another object is adjacent (no halo cell abuts a different object).
def gi_stopsat(rng):
    return _scene(rng, 3, 6, 3, 8, margin=1)
def tf_stopsat(g):
    bg = bg_colour(g); obs = objects(g, bg); out = copy(g)
    allcells = set(c for o in obs for c in o)
    for o in obs:
        col = g[o[0][0]][o[0][1]]
        others = allcells - set(o)
        for r, c in _ring(g, o, bg, 1):
            if not any((r + dr, c + dc) in others for dr, dc in NB8):
                out[r][c] = col
    return out
rule("halo_stops_at_neighbouring_object", "Draw a one-cell halo around each object, but skip any halo cell that would touch a different object.", gi_stopsat, tf_stopsat)


# 13 inner border: recolour the one-cell-inside layer of each object grey.
def gi_inner(rng):
    return _scene(rng, 2, 4, 9, 16, lo=12, hi=30, margin=2)
def tf_inner(g):
    bg = bg_colour(g); obs = objects(g, bg); out = copy(g); changed = False
    for o in obs:
        edge = _inner_edge(o, conn8=False)
        interior = set(o) - edge
        inner_edge2 = _inner_edge(interior, conn8=False) if interior else set()
        for r, c in inner_edge2:
            out[r][c] = 5; changed = True
    return out if changed else None
rule("inner_border_one_cell_in", "Recolour grey the ring of cells one cell inside each object's own outer edge.", gi_inner, tf_inner)


# 14 halo colour alternates by object order (reading order of first cell).
def gi_alt(rng):
    return _scene(rng, 3, 6, 3, 7, margin=2)
def tf_alt(g):
    bg = bg_colour(g); obs = sorted(objects(g, bg), key=lambda o: min(o)); out = copy(g)
    a, b = 1, 2
    for i, o in enumerate(obs):
        col = a if i % 2 == 0 else b
        for r, c in _ring(g, o, bg, 1):
            out[r][c] = col
    return out
rule("halo_colour_alternates_by_object_order", "Haloes alternate between two fixed colours, assigned in reading order of the objects.", gi_alt, tf_alt)


# 15 halo colour equals the object's hole count (digits: colour IS a number).
def gi_holes(rng):
    h, w = size(rng, 14, 30); g = blank(h, w); k = rng.randint(2, 4)
    cols = colours(rng, k)
    placed = 0; tries = 0
    while placed < k and tries < 60:
        tries += 1
        col = cols[placed]
        rr0, cc0 = rng.randint(1, h - 8), rng.randint(1, w - 8)
        rr1, cc1 = rr0 + rng.randint(3, 6), cc0 + rng.randint(3, 6)
        if rr1 >= h - 1 or cc1 >= w - 1:
            continue
        if any(g[r][c] for r in range(rr0 - 1, rr1 + 2) for c in range(cc0 - 1, cc1 + 2)):
            continue
        rect(g, rr0, cc0, rr1, cc1, col, fill=False)
        if rng.random() < 0.6 and rr1 - rr0 >= 4 and cc1 - cc0 >= 4:
            g[rr0 + 2][cc0 + 2] = col
        placed += 1
    return g if placed >= 2 else None
def tf_holes(g):
    bg = bg_colour(g); obs = objects(g, bg); out = copy(g); changed = False
    for o in obs:
        n = _holes(g, o, bg)
        n = max(1, min(9, n))
        for r, c in _ring(g, o, bg, 1):
            out[r][c] = n; changed = True
    return out if changed else None
rule("halo_coloured_by_hole_count", "Each object's halo is painted with the colour-number equal to how many enclosed holes it has.", gi_holes, tf_holes, digits=True)


# 16 halo colour by size rank (smallest gets colour 1, next 2, ...).
def gi_rank(rng):
    return _scene(rng, 3, 6, 2, 11, margin=2)
def tf_rank(g):
    bg = bg_colour(g); obs = sorted(objects(g, bg), key=len); out = copy(g)
    if len(set(len(o) for o in obs)) < 2:
        return None
    for i, o in enumerate(obs):
        col = (i % 9) + 1
        for r, c in _ring(g, o, bg, 1):
            out[r][c] = col
    return out
rule("halo_colour_by_size_rank", "Haloes are coloured by size rank: the smallest object's halo is colour 1, the next 2, and so on.", gi_rank, tf_rank)


# 17-20 inner border on one edge only.
def _gi_edgeside(rng):
    return _scene(rng, 2, 5, 6, 14, lo=10, hi=30, margin=2)
def _tf_edgeside(g, side):
    bg = bg_colour(g); obs = objects(g, bg); out = copy(g); changed = False
    for o in obs:
        r0, c0, r1, c1 = bbox(o); oset = set(o)
        col = g[o[0][0]][o[0][1]]
        for r, c in oset:
            if side == "top" and r == r0:
                out[r][c] = 5; changed = True
            elif side == "bottom" and r == r1:
                out[r][c] = 5; changed = True
            elif side == "left" and c == c0:
                out[r][c] = 5; changed = True
            elif side == "right" and c == c1:
                out[r][c] = 5; changed = True
    return out if changed else None
rule("inner_border_top_edge_only", "Recolour grey the top row of cells of every object.", _gi_edgeside, lambda g: _tf_edgeside(g, "top"))
rule("inner_border_bottom_edge_only", "Recolour grey the bottom row of cells of every object.", _gi_edgeside, lambda g: _tf_edgeside(g, "bottom"))
rule("inner_border_left_edge_only", "Recolour grey the leftmost column of cells of every object.", _gi_edgeside, lambda g: _tf_edgeside(g, "left"))
rule("inner_border_right_edge_only", "Recolour grey the rightmost column of cells of every object.", _gi_edgeside, lambda g: _tf_edgeside(g, "right"))


# 21 halo coloured to match the background (a quiet ring that only shows up as object recolour elsewhere); here
# use it to swallow the one-cell ring into bg colour deliberately, shrinking visible objects.
def gi_shrink(rng):
    return _scene(rng, 2, 5, 6, 14, lo=10, hi=30, margin=2)
def tf_shrink(g):
    bg = bg_colour(g); obs = objects(g, bg); out = copy(g); changed = False
    for o in obs:
        if len(o) < 5:
            continue
        for r, c in _inner_edge(o, conn8=False):
            out[r][c] = bg; changed = True
    return out if changed else None
rule("halo_colour_matches_background", "Erase the outer ring of every object with five or more cells back to the background colour.", gi_shrink, tf_shrink)


# 22 bbox corner dots.
def gi_bboxdots(rng):
    return _scene(rng, 2, 5, 5, 12, margin=2)
def tf_bboxdots(g):
    bg = bg_colour(g); obs = objects(g, bg); out = copy(g); H, W = dims(g); changed = False
    for o in obs:
        r0, c0, r1, c1 = bbox(o)
        for r, c in ((r0, c0), (r0, c1), (r1, c0), (r1, c1)):
            out[r][c] = 5; changed = True
    return out if changed else None
rule("bbox_corner_dots", "Recolour grey the cell at each of the four corners of every object's bounding box.", gi_bboxdots, tf_bboxdots)


# 23 halo thickness grows the farther the object is from the grid centre.
def gi_distthick(rng):
    return _scene(rng, 2, 4, 4, 8, lo=14, hi=30, margin=4)
def tf_distthick(g):
    bg = bg_colour(g); H, W = dims(g); obs = objects(g, bg); out = copy(g)
    cr, cc = (H - 1) / 2, (W - 1) / 2
    maxd = max(abs(sum(r for r, _ in o) / len(o) - cr) + abs(sum(c for _, c in o) / len(o) - cc) for o in obs) or 1
    for o in obs:
        col = g[o[0][0]][o[0][1]]
        orr, occ = sum(r for r, _ in o) / len(o), sum(c for _, c in o) / len(o)
        d = abs(orr - cr) + abs(occ - cc)
        t = 1 + int(2 * d / maxd)
        for r, c in _ring(g, o, bg, t):
            out[r][c] = col
    return out
rule("halo_thickness_by_distance_from_centre", "The farther an object sits from the grid's centre, the thicker its halo.", gi_distthick, tf_distthick)


# 24 double ring, alternating two colours.
def gi_doublering(rng):
    return _scene(rng, 1, 3, 6, 12, lo=12, hi=30, margin=4)
def tf_doublering(g):
    bg = bg_colour(g); obs = objects(g, bg); out = copy(g)
    for o in obs:
        r1 = _ring(g, o, bg, 1)
        r2 = _ring(g, o, bg, 2) - r1
        for r, c in r1:
            out[r][c] = 1
        for r, c in r2:
            out[r][c] = 2
    return out
rule("double_ring_alternating_colours", "Draw two concentric rings around each object: the inner ring colour 1, the outer ring colour 2.", gi_doublering, tf_doublering)


# 25 halo colour is the object's own colour plus one (wrapping 1..9).
def gi_plusone(rng):
    return _scene(rng, 2, 5, 4, 10, margin=2)
def tf_plusone(g):
    bg = bg_colour(g); obs = objects(g, bg); out = copy(g)
    for o in obs:
        col = g[o[0][0]][o[0][1]]
        nc = col + 1 if col < 9 else 1
        for r, c in _ring(g, o, bg, 1):
            out[r][c] = nc
    return out
rule("halo_colour_is_object_colour_plus_one", "Each object's halo uses the next colour number after the object's own colour, wrapping from 9 to 1.", gi_plusone, tf_plusone)


# 26 dotted halo: only every third ring cell in reading order.
def gi_dotted(rng):
    return _scene(rng, 1, 3, 8, 16, lo=14, hi=30, margin=3)
def tf_dotted(g):
    bg = bg_colour(g); obs = objects(g, bg); out = copy(g); changed = False
    for o in obs:
        col = g[o[0][0]][o[0][1]]
        ring = sorted(_ring(g, o, bg, 1))
        for i, (r, c) in enumerate(ring):
            if i % 3 == 0:
                out[r][c] = col; changed = True
    return out if changed else None
rule("halo_every_third_cell_dotted", "Draw a dotted halo around each object, colouring only every third ring cell in reading order.", gi_dotted, tf_dotted)


# 27 corner pixels of the object itself (not the bbox) recoloured.
def gi_cornerpix(rng):
    return _scene(rng, 2, 5, 6, 14, margin=2)
def tf_cornerpix(g):
    bg = bg_colour(g); obs = objects(g, bg); out = copy(g); changed = False
    for o in obs:
        oset = set(o)
        for r, c in oset:
            diag_free = sum(1 for dr, dc in ((-1, -1), (-1, 1), (1, -1), (1, 1)) if (r + dr, c + dc) not in oset)
            ortho_free = sum(1 for dr, dc in NB4 if (r + dr, c + dc) not in oset)
            if diag_free >= 3 and ortho_free == 2:
                out[r][c] = 5; changed = True
    return out if changed else None
rule("corner_pixels_of_object_recoloured", "Recolour grey each cell of an object that sits at an outward-pointing right-angle corner of its shape.", gi_cornerpix, tf_cornerpix)


# 28 strip the outer ring of each object away to background, keeping only the interior.
def gi_strip(rng):
    return _scene(rng, 1, 3, 9, 18, lo=12, hi=30, margin=3)
def tf_strip(g):
    bg = bg_colour(g); obs = objects(g, bg); out = copy(g); changed = False
    for o in obs:
        edge = _inner_edge(o, conn8=False)
        if len(edge) == len(o):
            continue
        for r, c in edge:
            out[r][c] = bg; changed = True
    return out if changed else None
rule("strip_outer_ring_to_background", "Erase the outer ring of cells of every object, leaving only each object's interior behind.", gi_strip, tf_strip)


# 29 halo colour is the rarest non-background colour present anywhere in the grid.
def gi_rarest(rng):
    return _scene(rng, 3, 6, 3, 8, margin=2)
def tf_rarest(g):
    bg = bg_colour(g); obs = objects(g, bg); cnt = counts(g)
    cands = {v: n for v, n in cnt.items() if v != bg}
    if len(cands) < 2:
        return None
    rare = min(cands.items(), key=lambda kv: kv[1])[0]
    out = copy(g)
    for o in obs:
        for r, c in _ring(g, o, bg, 1):
            out[r][c] = rare
    return out
rule("halo_colour_is_rarest_grid_colour", "Draw a halo around every object using whichever colour is rarest in the whole grid.", gi_rarest, tf_rarest)


# 30 uniform halo thickness equal to the number of objects in the grid (capped).
def gi_countthick(rng):
    return _scene(rng, 2, 5, 3, 7, lo=12, hi=30, margin=4)
def tf_countthick(g):
    bg = bg_colour(g); obs = objects(g, bg); out = copy(g)
    t = min(3, len(obs))
    for o in obs:
        col = g[o[0][0]][o[0][1]]
        for r, c in _ring(g, o, bg, t):
            out[r][c] = col
    return out
rule("uniform_halo_thickness_by_object_count", "Every object gets a halo whose thickness equals the number of objects in the grid, capped at three.", gi_countthick, tf_countthick)


# 31 draw the full bbox rectangle outline (not just corners) one cell past the object.
def gi_bboxrect(rng):
    return _scene(rng, 2, 4, 5, 12, lo=10, hi=28, margin=3)
def tf_bboxrect(g):
    bg = bg_colour(g); obs = objects(g, bg); out = copy(g); H, W = dims(g); changed = False
    for o in obs:
        col = g[o[0][0]][o[0][1]]
        r0, c0, r1, c1 = bbox(o)
        r0, c0, r1, c1 = r0 - 1, c0 - 1, r1 + 1, c1 + 1
        if r0 < 0 or c0 < 0 or r1 >= H or c1 >= W:
            continue
        for r in range(r0, r1 + 1):
            for c in (c0, c1):
                if g[r][c] == bg:
                    out[r][c] = col; changed = True
        for c in range(c0, c1 + 1):
            for r in (r0, r1):
                if g[r][c] == bg:
                    out[r][c] = col; changed = True
    return out if changed else None
rule("bbox_rectangle_outline_drawn", "Draw a rectangular outline one cell outside each object's full bounding box, in the object's colour.", gi_bboxrect, tf_bboxrect)


# 32 nested frames drawn inward from the grid edge, one per object, ordered by size rank.
def gi_nested(rng):
    h, w = size(rng, 14, 30)
    return blank(h, w)
def tf_nested(g):
    H, W = dims(g); out = copy(g); n = min(4, min(H, W) // 2 - 1)
    if n < 2:
        return None
    for i in range(n):
        col = (i % 9) + 1
        r0, c0, r1, c1 = i, i, H - 1 - i, W - 1 - i
        if r1 <= r0 or c1 <= c0:
            break
        rect(out, r0, c0, r1, c1, col, fill=False)
    return out
rule("nested_frames_by_size_rank", "Draw nested square frames inward from the grid's edge, colour 1 outermost, incrementing inward.", gi_nested, tf_nested)


# 33 halo colour cycles through colours 1..9 by object's reading-order rank.
def gi_cyclerank(rng):
    return _scene(rng, 3, 7, 3, 7, margin=2)
def tf_cyclerank(g):
    bg = bg_colour(g); obs = sorted(objects(g, bg), key=lambda o: min(o)); out = copy(g)
    for i, o in enumerate(obs):
        col = (i % 9) + 1
        for r, c in _ring(g, o, bg, 1):
            out[r][c] = col
    return out
rule("halo_colour_cycles_self_plus_rank", "Haloes are coloured 1, 2, 3, ... cycling through colour numbers in the objects' reading order.", gi_cyclerank, tf_cyclerank)


# 34 mark, on each object, the single border cell nearest the nearest grid wall.
def gi_nearwall(rng):
    return _scene(rng, 2, 5, 4, 10, margin=2)
def tf_nearwall(g):
    bg = bg_colour(g); H, W = dims(g); obs = objects(g, bg); out = copy(g); changed = False
    for o in obs:
        edge = _inner_edge(o, conn8=False)
        best, bd = None, 1e9
        for r, c in edge:
            d = min(r, H - 1 - r, c, W - 1 - c)
            if d < bd:
                bd, best = d, (r, c)
        if best:
            out[best[0]][best[1]] = 5; changed = True
    return out if changed else None
rule("edge_facing_nearest_wall_marked", "On each object, recolour grey the single cell closest to the nearest grid wall.", gi_nearwall, tf_nearwall)


# 35 four-sided grid border, each side a different colour.
def gi_foursided(rng):
    h, w = size(rng, 12, 30)
    return blank(h, w)
def tf_foursided(g):
    H, W = dims(g); out = copy(g)
    top, bottom, left, right = 1, 2, 3, 4
    for c in range(W):
        out[0][c] = top; out[H - 1][c] = bottom
    for r in range(H):
        out[r][0] = left; out[r][W - 1] = right
    return out
rule("four_sided_grid_border_distinct_colours", "Frame the grid's edge with four different colours, one per side: top, bottom, left, right.", gi_foursided, tf_foursided)


# 36 plus-mark at the midpoint of each grid edge.
def gi_plusmarks(rng):
    h, w = size(rng, 10, 30)
    return blank(h, w)
def tf_plusmarks(g):
    H, W = dims(g); out = copy(g)
    out[0][W // 2] = 5; out[H - 1][W // 2] = 5
    out[H // 2][0] = 5; out[H // 2][W - 1] = 5
    return out
rule("plus_marks_at_edge_midpoints", "Recolour grey the single cell at the midpoint of each of the grid's four edges.", gi_plusmarks, tf_plusmarks)


# 37 halo for objects that touch the grid edge, drawn grey (objects away from the edge untouched).
def gi_edgehalo(rng):
    return _scene(rng, 3, 6, 3, 8, lo=10, hi=30, margin=1)
def tf_edgehalo(g):
    bg = bg_colour(g); H, W = dims(g); obs = objects(g, bg); out = copy(g); changed = False
    for o in obs:
        if _touches_edge(o, H, W):
            for r, c in _ring(g, o, bg, 1):
                out[r][c] = 5; changed = True
    return out if changed else None
rule("halo_for_edge_touching_objects_grey", "Objects that touch the grid's outer edge get a grey halo; interior objects are untouched.", gi_edgehalo, tf_edgehalo)


# 38 outline the holes inside objects (recolour the hole interior cells).
def gi_outlinehole(rng):
    h, w = size(rng, 14, 30); g = blank(h, w); k = rng.randint(2, 4)
    cols = colours(rng, k); placed = 0; tries = 0
    while placed < k and tries < 60:
        tries += 1
        col = cols[placed]
        rr0, cc0 = rng.randint(1, h - 8), rng.randint(1, w - 8)
        rr1, cc1 = rr0 + rng.randint(4, 6), cc0 + rng.randint(4, 6)
        if rr1 >= h - 1 or cc1 >= w - 1:
            continue
        if any(g[r][c] for r in range(rr0 - 1, rr1 + 2) for c in range(cc0 - 1, cc1 + 2)):
            continue
        rect(g, rr0, cc0, rr1, cc1, col, fill=False)
        placed += 1
    return g if placed >= 2 else None
def tf_outlinehole(g):
    bg = bg_colour(g); obs = objects(g, bg); out = copy(g); changed = False
    for o in obs:
        r0, c0, r1, c1 = bbox(o)
        oset = set(o)
        for r in range(r0 + 1, r1):
            for c in range(c0 + 1, c1):
                if (r, c) not in oset and g[r][c] == bg:
                    out[r][c] = 5; changed = True
    return out if changed else None
rule("outline_holes_inside_objects", "Recolour grey every background cell enclosed inside an object's bounding box.", gi_outlinehole, tf_outlinehole)


# 39 halo colour keyed by a corner legend marker cell.
def gi_keyed(rng):
    g = _scene(rng, 2, 4, 5, 10, lo=12, hi=30, margin=2)
    if g is None:
        return None
    key = rng.choice([c for c in COLOURS if c not in set(v for row in g for v in row)] or colours(rng, 1))
    g[0][0] = key
    return g
def tf_keyed(g):
    key = g[0][0]; bg = bg_colour(g)
    g2 = copy(g); g2[0][0] = bg
    obs = objects(g2, bg); out = copy(g)
    if not obs:
        return None
    for o in obs:
        for r, c in _ring(g2, o, bg, 1):
            if (r, c) != (0, 0):
                out[r][c] = key
    return out
rule("halo_colour_keyed_by_corner_marker", "Every object's halo is painted with the colour of the marker cell in the grid's top-left corner.", gi_keyed, tf_keyed)


# 40 grid frame with a dashed pattern (every third edge cell lit).
def gi_dashedframe(rng):
    h, w = size(rng, 12, 30)
    return blank(h, w)
def tf_dashedframe(g):
    H, W = dims(g); out = copy(g); changed = False
    for c in range(0, W, 3):
        out[0][c] = 5; changed = True
    for c in range(0, W, 3):
        out[H - 1][c] = 5
    for r in range(0, H, 3):
        out[r][0] = 5
    for r in range(0, H, 3):
        out[r][W - 1] = 5
    return out if changed else None
rule("frame_grid_dashed_pattern", "Draw a dashed grey frame around the grid, lighting every third cell of each edge.", gi_dashedframe, tf_dashedframe)
