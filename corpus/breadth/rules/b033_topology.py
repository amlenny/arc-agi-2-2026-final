# b033_topology.py -- TOPOLOGY OF SHAPES: holes, islands, bridges, convexity, rings, nesting, Euler
# numbers, boundary length, inside/outside tests. One author, 40 rules.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

# ---------------------------------------------------------------- shared topology helpers

def size_mixed(rng, lo=6, hi=18, biglo=21, bighi=30, p_big=0.3):
    if rng.random() < p_big:
        return rng.randint(biglo, bighi), rng.randint(biglo, bighi)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def ncomp4(cellset):
    cellset = set(cellset); seen = set(); n = 0
    for cell in cellset:
        if cell in seen:
            continue
        n += 1; st = [cell]; seen.add(cell)
        while st:
            y, x = st.pop()
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                p = (y + dy, x + dx)
                if p in cellset and p not in seen:
                    seen.add(p); st.append(p)
    return n


def cc4(cells_iter):
    cellset = set(cells_iter); seen = set(); out = []
    for cell in cellset:
        if cell in seen:
            continue
        comp = []; st = [cell]; seen.add(cell)
        while st:
            y, x = st.pop(); comp.append((y, x))
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                p = (y + dy, x + dx)
                if p in cellset and p not in seen:
                    seen.add(p); st.append(p)
        out.append(comp)
    return out


def _reach(g, blocked):
    H, W = dims(g)
    reach = [[False] * W for _ in range(H)]
    st = []
    for r in range(H):
        for c in (0, W - 1):
            if not blocked(r, c) and not reach[r][c]:
                reach[r][c] = True; st.append((r, c))
    for c in range(W):
        for r in (0, H - 1):
            if not blocked(r, c) and not reach[r][c]:
                reach[r][c] = True; st.append((r, c))
    while st:
        y, x = st.pop()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and not blocked(ny, nx) and not reach[ny][nx]:
                reach[ny][nx] = True; st.append((ny, nx))
    return reach


def region_map(g, wall_colours):
    """reach[r][c] True means (r, c) is reachable from the grid border without crossing a wall colour."""
    return _reach(g, lambda r, c: g[r][c] in wall_colours)


def enclosed_cells(g, bg=0):
    """Background cells not reachable from the border (any non-background cell is a wall)."""
    H, W = dims(g)
    reach = _reach(g, lambda r, c: g[r][c] != bg)
    return [(r, c) for r in range(H) for c in range(W) if g[r][c] == bg and not reach[r][c]]


def shape_info(g, bg=0):
    """List of {cells, colour, bbox, holes}. A hole belongs to the object whose bbox contains it."""
    encl = cc4(enclosed_cells(g, bg))
    out = []
    for o in objects(g, bg=bg, conn8=True):
        colour = g[o[0][0]][o[0][1]]
        bb = bbox(o)
        holes = [h for h in encl if bbox(h)[0] >= bb[0] and bbox(h)[1] >= bb[1] and bbox(h)[2] <= bb[2] and bbox(h)[3] <= bb[3]]
        out.append({"cells": o, "colour": colour, "bbox": bb, "holes": holes})
    return out


def bridge_cells(obj):
    cellset = set(obj); base = ncomp4(cellset); out = []
    for cell in obj:
        rest = cellset - {cell}
        if rest and ncomp4(rest) > max(base, 1):
            out.append(cell)
    return out


def patch_dims(cells):
    return max(r for r, c, _ in cells) + 1, max(c for r, c, _ in cells) + 1


def place_patch(rng, g, cells, used, margin=1, tries=300):
    H, W = dims(g); h, w = patch_dims(cells)
    if h > H or w > W:
        return None
    for _ in range(tries):
        r0 = rng.randint(0, H - h); c0 = rng.randint(0, W - w)
        foot = {(r0 + r + dr, c0 + c + dc) for r, c, _ in cells
                for dr in range(-margin, margin + 1) for dc in range(-margin, margin + 1)}
        if not (foot & used):
            used |= foot
            for r, c, col in cells:
                g[r0 + r][c0 + c] = col
            return (r0, c0, h, w)
    return None


def patch_disc(rng, colour):
    h, w = rng.randint(3, 6), rng.randint(3, 6)
    return [(r, c, colour) for r in range(h) for c in range(w)]


def patch_ring(rng, colour):
    h, w = rng.randint(4, 8), rng.randint(4, 8)
    return [(r, c, colour) for r in range(h) for c in range(w) if r in (0, h - 1) or c in (0, w - 1)]


def patch_ring_thick(rng, colour, t=None):
    h, w = rng.randint(7, 11), rng.randint(7, 11)
    t = t if t is not None else rng.randint(1, 2)
    cellset = {(r, c) for r in range(h) for c in range(w)}
    inner = {(r, c) for r in range(t, h - t) for c in range(t, w - t)}
    cellset -= inner
    return [(r, c, colour) for r, c in cellset]


def patch_figure8(rng, colour):
    h, w = rng.randint(5, 9), rng.randint(7, 11)
    cells = [(r, c, colour) for r in range(h) for c in range(w) if r in (0, h - 1) or c in (0, w - 1)]
    midc = w // 2
    cells += [(r, midc, colour) for r in range(h)]
    return cells


def patch_c_shape(rng, colour):
    h, w = rng.randint(4, 8), rng.randint(4, 8)
    cells = {(r, c) for r in range(h) for c in range(w) if r in (0, h - 1) or c in (0, w - 1)}
    gap = rng.randint(1, max(1, w - 2))
    cells -= {(0, gap)}
    return [(r, c, colour) for r, c in cells]


def patch_dumbbell_chain(rng, colour, k):
    cells = []; x = 0
    for i in range(k):
        for r in range(3):
            for c in range(3):
                cells.append((r, x + c, colour))
        x += 3
        if i < k - 1:
            clen = rng.randint(1, 3)
            for d in range(clen):
                cells.append((1, x + d, colour))
            x += clen
    return cells


def patch_diag_chain(rng, colour, k):
    return [(i * 2 + dr, i * 2 + dc, colour) for i in range(k) for dr in range(2) for dc in range(2)]


def patch_notched_rect(rng, colour):
    h, w = rng.randint(5, 9), rng.randint(5, 9)
    cellset = {(r, c) for r in range(h) for c in range(w)}
    side = rng.choice(["top", "bottom", "left", "right"])
    if side in ("top", "bottom"):
        nd = rng.randint(1, max(1, h // 2 - 1)); nl = rng.randint(1, max(1, w - 2))
        start = rng.randint(1, max(1, w - 1 - nl))
        rr = range(nd) if side == "top" else range(h - nd, h)
        cellset -= {(r, c) for r in rr for c in range(start, start + nl)}
    else:
        nd = rng.randint(1, max(1, w // 2 - 1)); nl = rng.randint(1, max(1, h - 2))
        start = rng.randint(1, max(1, h - 1 - nl))
        cc = range(nd) if side == "left" else range(w - nd, w)
        cellset -= {(r, c) for r in range(start, start + nl) for c in cc}
    return [(r, c, colour) for r, c in cellset]


def has_island_inside(g, obj):
    r0, c0, r1, c1 = bbox(obj); oset = set(obj)
    for r in range(r0 + 1, r1):
        for c in range(c0 + 1, c1):
            if (r, c) not in oset and g[r][c] != 0:
                return True
    return False


def gi_mix(rng, kinds, k_lo=2, k_hi=5, size_kw=None):
    size_kw = size_kw or {}
    h, w = size_mixed(rng, **size_kw)
    g = blank(h, w); used = set()
    k = rng.randint(k_lo, k_hi)
    cols = colours(rng, min(k, 9))
    placed = 0
    for i in range(k):
        col = cols[i % len(cols)]
        patch = rng.choice(kinds)(rng, col)
        if place_patch(rng, g, patch, used, margin=1):
            placed += 1
    return g if placed >= 2 else None


# ================================================================== 1
def tf_rows(g):
    info = shape_info(g)
    bands = {0: [], 1: [], 2: []}
    for s in info:
        h = len(s["holes"])
        if h > 2:
            return None
        bands[h].append(s)
    if sum(len(v) for v in bands.values()) < 2:
        return None
    H, W = dims(g); bh = max(1, H // 3); out = blank(H, W)
    for k in (0, 1, 2):
        items = sorted(bands[k], key=lambda s: s["bbox"][1]); x = 0
        for s in items:
            r0, c0, r1, c1 = s["bbox"]; sub = crop(g, r0, c0, r1, c1); h, w = dims(sub)
            if x + w > W or h > bh:
                continue
            paste(out, sub, k * bh, x, transparent=0); x += w + 1
    return out if any(v for row in out for v in row) else None
rule("shapes_sorted_into_hole_count_rows",
     "Shapes are regrouped into three horizontal bands by their hole count: no holes on top, one hole in the middle, two holes on the bottom.",
     lambda rng: gi_mix(rng, [patch_disc, patch_ring, patch_figure8], 3, 6, {"lo": 10, "hi": 20}), tf_rows)


# ================================================================== 2
def tf_simply_connected(g):
    info = shape_info(g); out = copy(g); changed = False
    for s in info:
        new = 3 if len(s["holes"]) == 0 else 8
        if new != s["colour"]:
            changed = True
        for r, c in s["cells"]:
            out[r][c] = new
    return out if changed else None
rule("simply_connected_shapes_recoloured",
     "Every shape with no holes is recoloured 3; every shape with one or more holes is recoloured 8.",
     lambda rng: gi_mix(rng, [patch_disc, patch_ring, patch_figure8], 2, 5, {"lo": 8, "hi": 20}), tf_simply_connected)


# ================================================================== 3
def gi_nearest_fill(rng):
    h, w = size_mixed(rng, lo=14, hi=22); g = blank(h, w); used = set()
    k = rng.randint(3, 5); cols = colours(rng, k)
    kinds = [patch_ring, patch_figure8, patch_disc]
    for i in range(k):
        patch = rng.choice(kinds)(rng, cols[i])
        place_patch(rng, g, patch, used, margin=2)
    return g if len(objects(g, 0)) >= 3 else None
def tf_nearest_fill(g):
    info = shape_info(g)
    if sum(1 for s in info if s["holes"]) == 0:
        return None
    def centroid(s):
        rs = [r for r, c in s["cells"]]; cs = [c for r, c in s["cells"]]
        return sum(rs) / len(rs), sum(cs) / len(cs)
    out = copy(g); changed = False
    for s in info:
        if not s["holes"]:
            continue
        cr, cc = centroid(s)
        others = [o for o in info if o is not s]
        if not others:
            continue
        nearest = min(others, key=lambda o: (centroid(o)[0] - cr) ** 2 + (centroid(o)[1] - cc) ** 2)
        for hole in s["holes"]:
            for r, c in hole:
                out[r][c] = nearest["colour"]; changed = True
    return out if changed else None
rule("hole_filled_by_nearest_shape_colour",
     "Each shape's hole is filled with the colour of whichever other shape's centroid is closest to it.",
     gi_nearest_fill, tf_nearest_fill)


# ================================================================== 4
def gi_island_scene(rng, erase=False):
    h, w = size_mixed(rng, lo=10, hi=20); g = blank(h, w); used = set()
    k = rng.randint(2, 4); cols = colours(rng, k); island_col = rng.choice([c for c in COLOURS if c not in cols])
    any_island = False
    for i in range(k):
        patch = patch_ring(rng, cols[i])
        pos = place_patch(rng, g, patch, used, margin=2)
        if pos is None:
            continue
        r0, c0, ph, pw = pos
        if rng.random() < 0.5 and ph > 3 and pw > 3:
            g[r0 + ph // 2][c0 + pw // 2] = island_col; any_island = True
    return g if any_island and len(objects(g, 0)) >= 2 else None
def tf_mark_island(g):
    changed = False; out = copy(g)
    for o in objects(g, 0, conn8=True):
        if g[o[0][0]][o[0][1]] == 0:
            continue
        if has_island_inside(g, o):
            for r, c in o:
                out[r][c] = 7
            changed = True
    return out if changed else None
rule("shapes_with_island_in_hole_marked",
     "Any ring whose hole contains a separate coloured island is itself recoloured 7; rings with an empty hole are untouched.",
     gi_island_scene, tf_mark_island)


# ================================================================== 5
def tf_erase_island(g):
    out = copy(g); changed = False
    for o in objects(g, 0, conn8=True):
        if g[o[0][0]][o[0][1]] == 0:
            continue
        r0, c0, r1, c1 = bbox(o); oset = set(o)
        for r in range(r0 + 1, r1):
            for c in range(c0 + 1, c1):
                if (r, c) not in oset and g[r][c] != 0:
                    out[r][c] = 0; changed = True
    return out if changed else None
rule("island_inside_hole_erased",
     "Any island of colour sitting inside a ring's hole is erased back to background, leaving the ring intact.",
     gi_island_scene, tf_erase_island)


# ================================================================== 6
def gi_border_mix(rng):
    h, w = size_mixed(rng, lo=10, hi=20); g = blank(h, w); used = set()
    k = rng.randint(3, 5); cols = colours(rng, k); kinds = [patch_disc, patch_ring]
    touched = [False, False]
    for i in range(k):
        patch = rng.choice(kinds)(rng, cols[i]); ph, pw = patch_dims(patch)
        if ph >= h or pw >= w:
            continue
        force_touch = rng.random() < 0.5
        if force_touch:
            r0 = rng.choice([0, h - ph]); c0 = rng.randint(0, w - pw)
        else:
            if h - ph - 2 < 1 or w - pw - 2 < 1:
                continue
            r0 = rng.randint(1, h - ph - 1); c0 = rng.randint(1, w - pw - 1)
        foot = {(r0 + a + d1, c0 + b + d2) for a, b, _ in patch for d1 in (-1, 0, 1) for d2 in (-1, 0, 1)}
        if foot & used:
            continue
        used |= foot
        for a, b, col in patch:
            if 0 <= r0 + a < h and 0 <= c0 + b < w:
                g[r0 + a][c0 + b] = col
        touched[0] = touched[0] or force_touch
        touched[1] = touched[1] or not force_touch
    return g if all(touched) and len(objects(g, 0)) >= 2 else None
def _touches_border(g, o):
    H, W = dims(g)
    return any(r in (0, H - 1) or c in (0, W - 1) for r, c in o)
def tf_border_grey(g):
    out = copy(g); changed = False
    for o in objects(g, 0, conn8=True):
        if _touches_border(g, o):
            for r, c in o:
                out[r][c] = 5
            changed = True
    return out if changed else None
rule("border_touching_shapes_turn_grey",
     "Every shape that touches the edge of the grid is recoloured grey; shapes fully inside the grid keep their colour.",
     gi_border_mix, tf_border_grey)


# ================================================================== 7
def tf_keep_enclosed(g):
    out = copy(g); changed = False
    for o in objects(g, 0, conn8=True):
        if _touches_border(g, o):
            for r, c in o:
                out[r][c] = 0
            changed = True
    return out if changed and any(v for row in out for v in row) else None
rule("keep_only_enclosed_shapes",
     "Any shape touching the grid's edge is erased; only shapes fully enclosed within the grid remain.",
     gi_border_mix, tf_keep_enclosed)


# ================================================================== 8
def gi_dumbbells(rng):
    h, w = size_mixed(rng, lo=12, hi=22); g = blank(h, w); used = set()
    k = rng.randint(2, 4); cols = colours(rng, k); any_db = False
    for i in range(k):
        if rng.random() < 0.7:
            patch = patch_dumbbell_chain(rng, cols[i], rng.randint(2, 3)); any_db = True
        else:
            patch = patch_disc(rng, cols[i])
        place_patch(rng, g, patch, used, margin=1)
    return g if any_db and len(objects(g, 0)) >= 2 else None
def tf_mark_bridge(g):
    out = copy(g); changed = False
    for o in objects(g, 0, conn8=True):
        for r, c in bridge_cells(o):
            out[r][c] = 4; changed = True
    return out if changed else None
rule("bridge_cell_of_dumbbell_marked",
     "Every one-cell-wide bridge joining two lobes of a shape is recoloured 4.",
     gi_dumbbells, tf_mark_bridge)


# ================================================================== 9
def gi_diag_chain(rng):
    h, w = size_mixed(rng, lo=10, hi=20); g = blank(h, w); used = set()
    k = rng.randint(2, 4); cols = colours(rng, k)
    for i in range(k):
        if rng.random() < 0.6:
            patch = patch_diag_chain(rng, cols[i], rng.randint(2, 4))
        else:
            patch = patch_disc(rng, cols[i])
        place_patch(rng, g, patch, used, margin=1)
    return g if len(objects(g, 0, conn8=True)) >= 2 else None
def tf_pieces_by_count(g):
    out = copy(g); changed = False
    for o in objects(g, 0, conn8=True):
        m = ncomp4(set(o))
        if m != 1:
            changed = True
        for r, c in o:
            out[r][c] = m
    return out if changed else None
rule("shape_pieces_after_cut_coloured_by_count",
     "Each shape is recoloured with the number of pieces it splits into under four-way (non-diagonal) connectivity.",
     gi_diag_chain, tf_pieces_by_count,
     digits=True)
RULES_DIGITS_9 = True


# ================================================================== 10
def gi_notched(rng):
    h, w = size_mixed(rng, lo=10, hi=20); g = blank(h, w); used = set()
    k = rng.randint(2, 4); cols = colours(rng, k)
    for i in range(k):
        patch = patch_notched_rect(rng, cols[i]) if rng.random() < 0.7 else patch_disc(rng, cols[i])
        place_patch(rng, g, patch, used, margin=1)
    return g if len(objects(g, 0)) >= 2 else None
def tf_defects(g):
    out = copy(g); changed = False
    for o in objects(g, 0, conn8=True):
        r0, c0, r1, c1 = bbox(o); oset = set(o)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if (r, c) not in oset and g[r][c] == 0:
                    out[r][c] = 6; changed = True
    return out if changed else None
rule("convexity_defect_cells_marked",
     "Background cells that sit inside a shape's bounding box but outside the shape itself are recoloured 6.",
     gi_notched, tf_defects)


# ================================================================== 11
def tf_disc_or_ring(g):
    info = shape_info(g); out = copy(g); changed = False
    for s in info:
        new = 2 if len(s["holes"]) == 0 else 9
        if new != s["colour"]:
            changed = True
        for r, c in s["cells"]:
            out[r][c] = new
    return out if changed else None
rule("disc_or_ring_classification",
     "Solid discs are recoloured 2; hollow rings (one hole) are recoloured 9.",
     lambda rng: gi_mix(rng, [patch_disc, patch_ring], 2, 5, {"lo": 8, "hi": 20}), tf_disc_or_ring)


# ================================================================== 12
def gi_euler_scene(rng):
    return gi_mix(rng, [patch_disc, patch_ring, patch_figure8], 2, 5, {"lo": 12, "hi": 22})
def tf_euler_bar(g):
    info = shape_info(g)
    euler = len(info) - sum(len(s["holes"]) for s in info)
    if euler < 1:
        return None
    n = min(euler, 20)
    return [[5] * n + [0]]
rule("euler_number_bar",
     "The grid's Euler number (shape count minus total hole count) is drawn as a single bar of that many cells.",
     gi_euler_scene, tf_euler_bar)


# ================================================================== 13
def gi_single_shape(rng):
    h, w = size_mixed(rng, lo=10, hi=22); g = blank(h, w); used = set()
    patch = rng.choice([patch_disc, patch_ring, patch_notched_rect])(rng, rng.choice(COLOURS))
    if place_patch(rng, g, patch, used, margin=1) is None:
        return None
    return g
def tf_perimeter_bar(g):
    objs = objects(g, 0, conn8=True)
    if not objs:
        return None
    o = objs[0]; oset = set(o); H, W = dims(g)
    perim = 0
    for r, c in o:
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = r + dy, c + dx
            if not (0 <= ny < H and 0 <= nx < W) or (ny, nx) not in oset:
                perim += 1
    n = min(max(perim, 1), 30)
    return [[4] * n + [0]]
rule("shape_perimeter_length_bar",
     "The shape's boundary length (number of exposed edges) is drawn as a bar of that many cells.",
     gi_single_shape, tf_perimeter_bar)


# ================================================================== 14
def gi_dots_ring(rng):
    h, w = size_mixed(rng, lo=14, hi=24); g = blank(h, w); used = set()
    col = rng.choice(COLOURS); patch = patch_ring(rng, col)
    pos = place_patch(rng, g, patch, used, margin=2)
    if pos is None:
        return None
    r0, c0, ph, pw = pos
    inside = [(r, c) for r in range(r0 + 1, r0 + ph - 1) for c in range(c0 + 1, c0 + pw - 1)]
    outside = [(r, c) for r in range(h) for c in range(w) if g[r][c] == 0 and not (r0 <= r < r0 + ph and c0 <= c < c0 + pw)]
    marker = rng.choice([c for c in COLOURS if c != col])
    placed = 0
    for cellset in (inside, outside):
        if not cellset:
            continue
        for r, c in rng.sample(cellset, min(2, len(cellset))):
            g[r][c] = marker; placed += 1
    return g if placed >= 2 else None
def tf_dot_inout(g):
    cols = set(v for row in g for v in row if v != 0)
    if len(cols) < 2:
        return None
    wall = max(cols, key=lambda c: sum(row.count(c) for row in g))
    marker_cols = [c for c in cols if c != wall]
    if not marker_cols:
        return None
    reach = region_map(g, {wall}); out = copy(g); changed = False
    H, W = dims(g)
    for r in range(H):
        for c in range(W):
            if g[r][c] in marker_cols:
                out[r][c] = 2 if not reach[r][c] else 3; changed = True
    return out if changed else None
rule("dot_inside_or_outside_ring_recoloured",
     "Marker dots enclosed by the ring are recoloured 2; marker dots outside the ring are recoloured 3.",
     gi_dots_ring, tf_dot_inout)


# ================================================================== 15
def gi_nested_rings_dots(rng):
    h, w = size_mixed(rng, lo=16, hi=26); g = blank(h, w)
    cx, cy = w // 2, h // 2
    outer_col, inner_col = colours(rng, 2)
    r_out = min(h, w) // 2 - 1; r_in = r_out - rng.randint(3, 5)
    if r_in < 2:
        return None
    for (rad, col) in ((r_out, outer_col), (r_in, inner_col)):
        r0, c0, r1, c1 = cy - rad, cx - rad, cy + rad, cx + rad
        rect(g, r0, c0, r1, c1, col, fill=False)
    marker = rng.choice([c for c in COLOURS if c not in (outer_col, inner_col)])
    depths = {0: (1, 1), 1: (r_out - 1, cx), 2: (cy, cx)}
    for d, (r, c) in depths.items():
        if 0 <= r < h and 0 <= c < w and g[r][c] == 0:
            g[r][c] = marker
    return g
def tf_dot_depth(g):
    cols = set(v for row in g for v in row if v != 0)
    walls = sorted(cols, key=lambda c: -sum(row.count(c) for row in g))[:2]
    marker_cols = [c for c in cols if c not in walls]
    if not marker_cols:
        return None
    reaches = [region_map(g, {w}) for w in walls]
    out = copy(g); changed = False; H, W = dims(g)
    for r in range(H):
        for c in range(W):
            if g[r][c] in marker_cols:
                depth = sum(1 for rc in reaches if not rc[r][c])
                out[r][c] = depth + 1; changed = True
    return out if changed else None
rule("dot_nesting_depth_recoloured",
     "Each marker dot is recoloured by how many of the two nested square rings enclose it, plus one.",
     gi_nested_rings_dots, tf_dot_depth,
     digits=True)


# ================================================================== 16
def gi_concentric(rng):
    n = rng.randint(2, 4)
    gaps = [rng.randint(2, 3) for _ in range(n)]
    rad = 1; radii = []
    for gp in gaps:
        rad += gp; radii.append(rad)
    size0 = radii[-1]
    if size0 > 13:
        return None
    pad = rng.randint(0, max(0, min(2, (28 - 2 * size0) // 2)))
    h = w = 2 * size0 + 1 + 2 * pad
    if h > 30:
        return None
    cx = cy = size0 + pad
    g = blank(h, w); cols = colours(rng, n)
    for i, col in enumerate(cols):
        r = radii[i]
        rect(g, cy - r, cx - r, cy + r, cx + r, col, fill=False)
    return g
def tf_concentric_mark(g):
    enc = cc4(enclosed_cells(g, 0))
    if not enc:
        return None
    centre = min(enc, key=len)
    n = len(set(v for row in g for v in row if v != 0))
    out = copy(g)
    for r, c in centre:
        out[r][c] = n
    return out
rule("concentric_ring_count_marks_centre",
     "The innermost empty cell of a set of nested square rings is recoloured with the count of rings.",
     gi_concentric, tf_concentric_mark,
     digits=True)


# ================================================================== 17
def tf_total_holes_bar(g):
    info = shape_info(g); total = sum(len(s["holes"]) for s in info)
    if total < 1:
        return None
    return [[1] * min(total, 25) + [0]]
rule("total_hole_count_as_bar",
     "The total number of holes across every shape in the grid is drawn as a single bar of that many cells.",
     lambda rng: gi_mix(rng, [patch_disc, patch_ring, patch_figure8], 2, 5, {"lo": 10, "hi": 22}), tf_total_holes_bar)


# ================================================================== 18
def tf_order_by_hole_area(g):
    info = shape_info(g)
    if len(info) < 2:
        return None
    items = sorted(info, key=lambda s: sum(len(h) for h in s["holes"]))
    H, W = dims(g); maxw = sum(s["bbox"][3] - s["bbox"][1] + 2 for s in items)
    out = blank(max(s["bbox"][2] - s["bbox"][0] + 1 for s in items), min(maxw, 60))
    x = 0
    for s in items:
        r0, c0, r1, c1 = s["bbox"]; sub = crop(g, r0, c0, r1, c1); h, w = dims(sub)
        if x + w > len(out[0]):
            break
        paste(out, sub, 0, x, transparent=0); x += w + 1
    return out if any(v for row in out for v in row) else None
rule("shapes_ordered_left_right_by_hole_area",
     "Every shape is cropped to its own bounding box and laid out in one row, ordered left to right by hole area ascending.",
     lambda rng: gi_mix(rng, [patch_disc, patch_ring, patch_figure8], 3, 5, {"lo": 10, "hi": 20}), tf_order_by_hole_area)


# ================================================================== 19
def tf_keep_largest_hole(g):
    info = shape_info(g)
    areas = [sum(len(h) for h in s["holes"]) for s in info]
    if max(areas, default=0) < 1 or areas.count(max(areas)) > 1:
        return None
    best = info[areas.index(max(areas))]
    H, W = dims(g); out = blank(H, W)
    for r, c in best["cells"]:
        out[r][c] = best["colour"]
    return out
rule("shape_with_largest_hole_kept_alone",
     "Only the one shape with the largest hole is kept; every other shape is erased.",
     lambda rng: gi_mix(rng, [patch_disc, patch_ring, patch_figure8], 3, 5, {"lo": 10, "hi": 20}), tf_keep_largest_hole)


# ================================================================== 20
def tf_zero_hole_grey(g):
    info = shape_info(g); out = copy(g); changed = False
    for s in info:
        if len(s["holes"]) == 0 and s["colour"] != 5:
            for r, c in s["cells"]:
                out[r][c] = 5
            changed = True
    return out if changed else None
rule("zero_hole_shapes_turn_grey",
     "Every shape with zero holes is recoloured grey; shapes that already have a hole are left as they are.",
     lambda rng: gi_mix(rng, [patch_disc, patch_ring, patch_figure8], 2, 5, {"lo": 8, "hi": 20}), tf_zero_hole_grey)


# ================================================================== 21
def gi_for_corner(rng):
    g = gi_mix(rng, [patch_disc, patch_ring, patch_figure8], 3, 6, {"lo": 10, "hi": 20})
    return g
def tf_corner_tally(g):
    info = shape_info(g); count = sum(1 for s in info if len(s["holes"]) == 2)
    if count < 1 or g[0][0] != 0:
        return None
    out = copy(g); out[0][0] = count
    return out
rule("two_hole_shape_tally_corner_digit",
     "The top-left cell is set to the number of figure-eight shapes (exactly two holes) found in the grid.",
     gi_for_corner, tf_corner_tally,
     digits=True)


# ================================================================== 22
def tf_fill_two_hole_only(g):
    info = shape_info(g); out = copy(g); changed = False
    for s in info:
        if len(s["holes"]) == 2:
            for hole in s["holes"]:
                for r, c in hole:
                    out[r][c] = s["colour"]; changed = True
    return out if changed else None
rule("holes_of_two_hole_shapes_filled",
     "Figure-eight shapes (two holes) have both holes filled solid with the shape's own colour; other shapes are untouched.",
     lambda rng: gi_mix(rng, [patch_disc, patch_ring, patch_figure8], 2, 5, {"lo": 10, "hi": 20}), tf_fill_two_hole_only)


# ================================================================== 23
def gi_thick_rings(rng):
    h, w = size_mixed(rng, lo=12, hi=24); g = blank(h, w); used = set()
    k = rng.randint(2, 4); cols = colours(rng, k); ts = []
    for i in range(k):
        t = rng.choice([1, 2]); ts.append(t)
        patch = patch_ring_thick(rng, cols[i], t)
        place_patch(rng, g, patch, used, margin=1)
    return g if len(set(ts)) > 0 and len(objects(g, 0)) >= 2 else None
def tf_thickness(g):
    info = shape_info(g); out = copy(g); changed = False
    for s in info:
        if not s["holes"]:
            continue
        hb = bbox(s["holes"][0]); bb = s["bbox"]
        t = max(1, (hb[0] - bb[0]))
        for r, c in s["cells"]:
            out[r][c] = t
        changed = True
    return out if changed else None
rule("ring_wall_thickness_recoloured",
     "Each ring is recoloured by the thickness of its wall, measured in cells.",
     gi_thick_rings, tf_thickness,
     digits=True)


# ================================================================== 24
def tf_open_vs_closed(g):
    info = shape_info(g); out = copy(g); changed = False
    for s in info:
        new = 6 if len(s["holes"]) >= 1 else 2
        if new != s["colour"]:
            changed = True
        for r, c in s["cells"]:
            out[r][c] = new
    return out if changed else None
rule("open_notch_vs_closed_ring_recoloured",
     "A closed ring (its hole is fully enclosed) is recoloured 6; a ring with a gap in its wall (the hole leaks to the outside) is recoloured 2.",
     lambda rng: gi_mix(rng, [patch_ring, patch_c_shape], 2, 5, {"lo": 10, "hi": 20}), tf_open_vs_closed)


# ================================================================== 25
def tf_nest_depth_recolour(g):
    info = shape_info(g)
    if len(info) < 2:
        return None
    ranked = sorted(info, key=lambda s: -(s["bbox"][2] - s["bbox"][0]) * (s["bbox"][3] - s["bbox"][1]))
    out = copy(g); changed = False
    for i, s in enumerate(ranked, start=1):
        for r, c in s["cells"]:
            out[r][c] = min(i, 9); changed = True
    return out if changed else None
rule("nested_ring_depth_recoloured",
     "Shapes are recoloured by their nesting rank from outermost (1) to innermost, ranked by bounding-box area.",
     gi_nested_rings_dots, tf_nest_depth_recolour,
     digits=True)


# ================================================================== 26
def tf_flag_equal(g):
    info = shape_info(g)
    if not info or g[0][0] != 0:
        return None
    total = sum(len(s["holes"]) for s in info)
    out = copy(g); out[0][0] = 3 if total == len(info) else 7
    return out
rule("hole_count_equals_shape_count_flag",
     "The top-left cell is set to 3 if the grid's total hole count equals its shape count, otherwise 7.",
     lambda rng: gi_mix(rng, [patch_disc, patch_ring, patch_figure8], 2, 5, {"lo": 10, "hi": 20}), tf_flag_equal)


# ================================================================== 27
def gi_dumbbell_chains(rng):
    h, w = size_mixed(rng, lo=12, hi=24); g = blank(h, w); used = set()
    k = rng.randint(1, 3); cols = colours(rng, k); ok = False
    for i in range(k):
        patch = patch_dumbbell_chain(rng, cols[i], rng.randint(2, 4))
        if place_patch(rng, g, patch, used, margin=1):
            ok = True
    return g if ok else None
def tf_bridge_count_bar(g):
    total = sum(len(bridge_cells(o)) for o in objects(g, 0, conn8=True))
    if total < 1:
        return None
    return [[4] * min(total, 25) + [0]]
rule("dumbbell_bridge_count_bar",
     "The total number of one-cell-wide bridge cells across all shapes is drawn as a single bar of that many cells.",
     gi_dumbbell_chains, tf_bridge_count_bar)


# ================================================================== 28
def tf_dot_depth_bar(g):
    cols = set(v for row in g for v in row if v != 0)
    walls = sorted(cols, key=lambda c: -sum(row.count(c) for row in g))[:2]
    marker_cols = [c for c in cols if c not in walls]
    if not marker_cols:
        return None
    reaches = [region_map(g, {w}) for w in walls]
    H, W = dims(g); best = -1
    for r in range(H):
        for c in range(W):
            if g[r][c] in marker_cols:
                depth = sum(1 for rc in reaches if not rc[r][c])
                best = max(best, depth)
    if best < 1:
        return None
    return [[9] * best + [0]]
# dot_curve_nesting_bar dropped 2026-10-12: generator produced identical canonical inputs (dup_input 100%)
# ================================================================== 29
def tf_move_two_hole(g):
    info = shape_info(g); keep = [s for s in info if len(s["holes"]) == 2]
    if not keep:
        return None
    H, W = dims(g); out = blank(H, W); x = 0
    for s in keep:
        r0, c0, r1, c1 = s["bbox"]; sub = crop(g, r0, c0, r1, c1); h, w = dims(sub)
        if x + w > W:
            break
        paste(out, sub, 0, x, transparent=0); x += w + 1
    return out if any(v for row in out for v in row) else None
rule("two_hole_shapes_moved_to_corner",
     "Only figure-eight shapes (two holes) survive, repacked left to right against the top-left corner; all else is erased.",
     lambda rng: gi_mix(rng, [patch_disc, patch_ring, patch_figure8], 3, 6, {"lo": 10, "hi": 22}), tf_move_two_hole)


# ================================================================== 30
def tf_three_way(g):
    info = shape_info(g); mapping = {0: 2, 1: 4, 2: 6}; out = copy(g); changed = False
    for s in info:
        n = min(len(s["holes"]), 2); new = mapping[n]
        if new != s["colour"]:
            changed = True
        for r, c in s["cells"]:
            out[r][c] = new
    return out if changed else None
rule("shapes_coloured_by_hole_count_three_way",
     "Shapes are recoloured 2, 4 or 6 according to whether they have zero, one or two holes.",
     lambda rng: gi_mix(rng, [patch_disc, patch_ring, patch_figure8], 3, 6, {"lo": 10, "hi": 22}), tf_three_way)


# ================================================================== 31
def tf_histogram_rows(g):
    info = shape_info(g)
    if len(info) < 2:
        return None
    items = sorted(info, key=lambda s: s["bbox"][1])
    maxw = max(len(s["holes"]) + 1 for s in items)
    out = blank(len(items), maxw)
    for i, s in enumerate(items):
        for c in range(len(s["holes"]) + 1):
            out[i][c] = s["colour"]
    return out
rule("hole_count_histogram_rows",
     "One output row per shape (ordered left to right), each row a bar whose length is that shape's hole count plus one.",
     lambda rng: gi_mix(rng, [patch_disc, patch_ring, patch_figure8], 3, 6, {"lo": 10, "hi": 22}), tf_histogram_rows)


# ================================================================== 32
def tf_fill_no_island_holes(g):
    out = copy(g); changed = False
    for o in objects(g, 0, conn8=True):
        if has_island_inside(g, o):
            continue
        r0, c0, r1, c1 = bbox(o); oset = set(o); colour = g[o[0][0]][o[0][1]]
        for r in range(r0 + 1, r1):
            for c in range(c0 + 1, c1):
                if (r, c) not in oset and g[r][c] == 0:
                    out[r][c] = colour; changed = True
    return out if changed else None
rule("holes_without_island_filled",
     "A ring's hole is filled solid with the ring's colour only if the hole is empty; holes that contain an island are left alone.",
     gi_island_scene, tf_fill_no_island_holes)


# ================================================================== 33
def tf_rank_colour(g):
    info = shape_info(g)
    if len(info) < 2:
        return None
    ranked = sorted(info, key=lambda s: (len(s["holes"]), s["bbox"][1]))
    out = copy(g); changed = False
    for i, s in enumerate(ranked, start=1):
        for r, c in s["cells"]:
            out[r][c] = min(i, 9); changed = True
    return out if changed else None
rule("shapes_ranked_by_hole_count_colour",
     "Shapes are recoloured by their rank among this scene's shapes when sorted by hole count ascending (ties by position).",
     lambda rng: gi_mix(rng, [patch_disc, patch_ring, patch_figure8], 3, 6, {"lo": 10, "hi": 22}), tf_rank_colour,
     digits=True)


# ================================================================== 34
def tf_erase_outside_dots(g):
    cols = set(v for row in g for v in row if v != 0)
    if len(cols) < 2:
        return None
    wall = max(cols, key=lambda c: sum(row.count(c) for row in g))
    marker_cols = [c for c in cols if c != wall]
    if not marker_cols:
        return None
    reach = region_map(g, {wall}); out = copy(g); changed = False; H, W = dims(g)
    for r in range(H):
        for c in range(W):
            if g[r][c] in marker_cols and reach[r][c]:
                out[r][c] = 0; changed = True
    return out if changed else None
rule("dots_outside_every_ring_erased",
     "Marker dots left outside the ring's enclosed area are erased; dots the ring encloses are kept.",
     gi_dots_ring, tf_erase_outside_dots)


# ================================================================== 35
def tf_tally_bars(g):
    info = shape_info(g)
    a = sum(1 for s in info if len(s["holes"]) == 1); b = sum(1 for s in info if len(s["holes"]) == 2)
    if a + b < 1:
        return None
    w = max(a, b, 1); out = blank(2, w)
    for c in range(a):
        out[0][c] = 2
    for c in range(b):
        out[1][c] = 6
    return out
rule("ring_and_figure8_tally_bars",
     "Two output rows: the top row's length is the count of one-hole rings, the bottom row's length is the count of two-hole shapes.",
     lambda rng: gi_mix(rng, [patch_disc, patch_ring, patch_figure8], 3, 6, {"lo": 10, "hi": 22}), tf_tally_bars)


# ================================================================== 36
def gi_ring_border_mix(rng):
    h, w = size_mixed(rng, lo=10, hi=20); g = blank(h, w); used = set()
    k = rng.randint(3, 5); cols = colours(rng, k); touched = [False, False]
    for i in range(k):
        patch = patch_ring(rng, cols[i]); ph, pw = patch_dims(patch)
        if ph >= h or pw >= w:
            continue
        force_touch = rng.random() < 0.5
        if force_touch:
            r0 = rng.choice([0, h - ph]); c0 = rng.randint(0, w - pw)
        else:
            if h - ph - 2 < 1 or w - pw - 2 < 1:
                continue
            r0 = rng.randint(1, h - ph - 1); c0 = rng.randint(1, w - pw - 1)
        foot = {(r0 + a + d1, c0 + b + d2) for a, b, _ in patch for d1 in (-1, 0, 1) for d2 in (-1, 0, 1)}
        if foot & used:
            continue
        used |= foot
        for a, b, col in patch:
            if 0 <= r0 + a < h and 0 <= c0 + b < w:
                g[r0 + a][c0 + b] = col
        touched[0] = touched[0] or force_touch
        touched[1] = touched[1] or not force_touch
    return g if all(touched) and len(objects(g, 0)) >= 2 else None
def tf_ring_border_touch(g):
    out = copy(g); changed = False
    for o in objects(g, 0, conn8=True):
        new = 1 if _touches_border(g, o) else 8
        if new != g[o[0][0]][o[0][1]]:
            changed = True
        for r, c in o:
            out[r][c] = new
    return out if changed else None
rule("ring_border_touch_recoloured",
     "A ring that touches the grid's edge is recoloured 1; a ring entirely inside the grid is recoloured 8.",
     gi_ring_border_mix, tf_ring_border_touch)


# ================================================================== 37
def tf_largest_shape_corner(g):
    info = shape_info(g)
    if not info or g[0][0] != 0:
        return None
    best = max(info, key=lambda s: len(s["cells"]))
    out = copy(g); out[0][0] = len(best["holes"]) + 1
    return out
rule("largest_shape_hole_count_corner_digit",
     "The top-left cell is set to the hole count of the single largest shape (by cell area), plus one.",
     lambda rng: gi_mix(rng, [patch_disc, patch_ring, patch_figure8], 3, 6, {"lo": 10, "hi": 22}), tf_largest_shape_corner,
     digits=True)


# ================================================================== 38
def gi_ratio_scene(rng):
    h, w = size_mixed(rng, lo=12, hi=24); g = blank(h, w); used = set()
    k = rng.randint(3, 5); cols = colours(rng, k)
    for i in range(k):
        kind = rng.choice([patch_disc, patch_ring_thick])
        patch = kind(rng, cols[i]) if kind is patch_disc else kind(rng, cols[i], rng.choice([1, 2, 3]))
        place_patch(rng, g, patch, used, margin=1)
    return g if len(objects(g, 0)) >= 2 else None
def tf_ratio_bucket(g):
    info = shape_info(g); out = copy(g); changed = False
    for s in info:
        area = len(s["cells"]); holearea = sum(len(h) for h in s["holes"])
        ratio = holearea / area if area else 0
        new = 2 if ratio == 0 else (4 if ratio < 0.3 else 6)
        if new != s["colour"]:
            changed = True
        for r, c in s["cells"]:
            out[r][c] = new
    return out if changed else None
rule("hole_area_ratio_bucket_colour",
     "Shapes are recoloured by the ratio of hole area to shape area: 2 for none, 4 for a thin hole, 6 for a wide hole.",
     gi_ratio_scene, tf_ratio_bucket)


# ================================================================== 39
def tf_single_hole_bar(g):
    info = shape_info(g); n = sum(1 for s in info if len(s["holes"]) == 1)
    if n < 1:
        return None
    return [[min(n, 9)] * n + [0]]
rule("single_hole_shape_count_bar",
     "The count of one-hole shapes (rings) is drawn as a bar of that many cells, each cell coloured with that same count.",
     lambda rng: gi_mix(rng, [patch_disc, patch_ring, patch_figure8], 3, 6, {"lo": 10, "hi": 22}), tf_single_hole_bar,
     digits=True)


# ================================================================== 40
def tf_digest_row(g):
    info = shape_info(g)
    if len(info) < 2:
        return None
    items = sorted(info, key=lambda s: s["bbox"][1])
    return [[min(len(s["holes"]) + 1, 9) for s in items]]
rule("hole_count_digest_row",
     "Output one cell per shape, left to right by position, each coloured with that shape's hole count plus one.",
     lambda rng: gi_mix(rng, [patch_disc, patch_ring, patch_figure8], 3, 6, {"lo": 10, "hi": 22}), tf_digest_row,
     digits=True)
