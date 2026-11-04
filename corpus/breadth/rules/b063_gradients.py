# b063_gradients.py -- ordered colour sequences and gradients: a palette row fixes an order; objects,
# stripes, rings, paths and cells are repainted along that order by position/distance/size/index.
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


def _palette_row(rng, k_lo=3, k_hi=6):
    """A palette: k distinct colours in a fixed left-to-right order."""
    k = rng.randint(k_lo, k_hi)
    return colours(rng, k)


def _bigw(rng, lo=21, hi=30, p=0.4):
    """Bias width toward the large-grid band roughly p of the time."""
    return rng.randint(lo, hi) if rng.random() < p else rng.randint(6, 18)


def _hw(rng, lo=8, p=0.45):
    """h,w pair: with probability p BOTH dims land in 21-30 (guarantees a large input); otherwise both
    are small (lo..18). Avoids diluting the large-grid share by sampling a wide range below 21."""
    if rng.random() < p:
        return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, 18), rng.randint(lo, 18)


def _multi_components(g, bg=0):
    """Connected same-colour components across ALL non-bg colours (helper the glib components() doesn't give directly)."""
    return objects(g, bg=bg, conn8=False)


# 1 ---- objects recoloured by left-to-right position along the palette.
def gi_objpos(rng):
    h, w = _hw(rng, 8); g = blank(h, w)
    pal = _palette_row(rng, 3, 6)
    k = len(pal)
    shapes = [random_shape(rng, rng.randint(2, 6)) for _ in range(k)]
    if place_shapes(rng, g, shapes, [rng.choice([c for c in COLOURS if c not in pal] or pal) for _ in range(k)], margin=1) is None:
        return None
    g.append([0] * w)
    for i, c in enumerate(pal):
        g[-1][i] = c
    return g
def tf_objpos(g):
    h, w = dims(g)
    pal = [v for v in g[-1] if v != 0]
    body = g[:-1]
    obs = objects(body, bg=0)
    ordered = sorted(obs, key=lambda o: min(c for _, c in o))
    out = [row[:] for row in body]
    for i, o in enumerate(ordered):
        col = pal[min(i, len(pal) - 1)]
        for r, c in o: out[r][c] = col
    return out + [g[-1]]
rule("gradient_objects_left_to_right", "The bottom row is a palette; objects (minus that row) sorted by their leftmost column take successive palette colours left to right, the last colour repeating for extra objects, and the palette row stays unchanged.", gi_objpos, tf_objpos)


# 2 ---- cells recoloured by distance from a seed marker, nearest = first palette colour.
def gi_distseed(rng):
    h, w = _hw(rng, 8); g = blank(h, w)
    pal = _palette_row(rng, 3, 5)
    sr, sc = rng.randrange(h), rng.randrange(w)
    g[sr][sc] = 8 if 8 not in pal else 9
    k = rng.randint(h * w // 6, h * w // 3)
    cands = [(r, c) for r in range(h) for c in range(w) if (r, c) != (sr, sc)]
    rng.shuffle(cands)
    for r, c in cands[:k]:
        g[r][c] = 1
    g2 = blank(h + 1, w)
    for i, c in enumerate(pal): g2[0][i] = c
    for r in range(h):
        for c in range(w): g2[r + 1][c] = g[r][c]
    return g2
def tf_distseed(g):
    pal = [v for v in g[0] if v != 0]
    body = g[1:]
    h, w = dims(body)
    marker = next((r, c) for r in range(h) for c in range(w) if body[r][c] not in (0, 1))
    mk = body[marker[0]][marker[1]]
    dists = []
    out = [row[:] for row in body]
    for r in range(h):
        for c in range(w):
            if body[r][c] == 1:
                dists.append(abs(r - marker[0]) + abs(c - marker[1]))
    if not dists: return None
    dmax = max(dists) or 1
    for r in range(h):
        for c in range(w):
            if body[r][c] == 1:
                d = abs(r - marker[0]) + abs(c - marker[1])
                idx = min(len(pal) - 1, int(d * len(pal) / (dmax + 1)))
                out[r][c] = pal[idx]
    out[marker[0]][marker[1]] = mk
    return [g[0]] + out
rule("gradient_by_distance_from_seed", "The top row is a palette; a marker cell in the body is the seed, and every colour-1 cell is repainted by Manhattan distance from the seed bucketed evenly across the palette, nearest bucket getting the first palette colour.", gi_distseed, tf_distseed)


# 3 ---- horizontal stripes repainted in palette order from the top.
def gi_stripes(rng):
    h, w = _hw(rng, 9)
    pal = _palette_row(rng, 3, 6)
    stripe_col = rng.choice([c for c in COLOURS if c not in pal])
    g = [[stripe_col] * w for _ in range(h)]
    g.append([0] * w)
    for i, c in enumerate(pal): g[-1][i] = c
    return g
def tf_stripes(g):
    pal = [v for v in g[-1] if v != 0]
    h = len(g) - 1; w = len(g[0])
    out = blank(h, w)
    for r in range(h):
        out[r] = [pal[r % len(pal)]] * w
    return out + [g[-1]]
rule("stripes_in_palette_order_topdown", "The bottom row is a palette; each row above it is repainted solid with the palette colour at index (row number mod palette length), row 0 at the top getting the first colour.", gi_stripes, tf_stripes)


# 4 ---- a straight path between two markers painted as a gradient through the palette.
def gi_path(rng):
    h, w = _hw(rng, 8); g = blank(h, w)
    pal = _palette_row(rng, 3, 5)
    while True:
        if rng.random() < 0.5:
            r = rng.randrange(h); c1, c2 = sorted(rng.sample(range(w), 2))
            if c2 - c1 < len(pal): continue
            g[r][c1] = 8; g[r][c2] = 9
            break
        else:
            c = rng.randrange(w); r1, r2 = sorted(rng.sample(range(h), 2))
            if r2 - r1 < len(pal): continue
            g[r1][c] = 8; g[r2][c] = 9
            break
    g2 = blank(h + 1, w)
    for i, col in enumerate(pal): g2[0][i] = col
    for r in range(h):
        for c in range(w): g2[r + 1][c] = g[r][c]
    return g2
def tf_path(g):
    pal = [v for v in g[0] if v != 0]
    body = g[1:]
    h, w = dims(body)
    a = next((r, c) for r in range(h) for c in range(w) if body[r][c] == 8)
    b = next((r, c) for r in range(h) for c in range(w) if body[r][c] == 9)
    out = [row[:] for row in body]
    if a[0] == b[0]:
        r = a[0]; c0, c1 = sorted((a[1], b[1]))
        n = c1 - c0 + 1
        for i, c in enumerate(range(c0, c1 + 1)):
            out[r][c] = pal[min(len(pal) - 1, i * len(pal) // n)]
    else:
        c = a[1]; r0, r1 = sorted((a[0], b[0]))
        n = r1 - r0 + 1
        for i, r in enumerate(range(r0, r1 + 1)):
            out[r][c] = pal[min(len(pal) - 1, i * len(pal) // n)]
    return [g[0]] + out
rule("path_gradient_a_to_b", "The top row is a palette; two markers (8 and 9) sit on the same row or column, and the straight segment between them is painted as a gradient through the palette in order from the marker with the smaller coordinate to the one with the larger, 8 and 9 themselves replaced too.", gi_path, tf_path)


# 5 ---- objects sorted by size take successive palette colours, smallest first.
def gi_sizesort(rng):
    h, w = _hw(rng, 9); g = blank(h, w)
    pal = _palette_row(rng, 3, 6)
    k = len(pal)
    sizes = rng.sample(range(2, 2 + 2 * k), k)
    shapes = [random_shape(rng, n) for n in sizes]
    other = [c for c in COLOURS if c not in pal] or pal
    if place_shapes(rng, g, shapes, [rng.choice(other) for _ in range(k)], margin=1) is None:
        return None
    g.append([0] * w)
    for i, c in enumerate(pal): g[-1][i] = c
    return g
def tf_sizesort(g):
    pal = [v for v in g[-1] if v != 0]
    body = [row[:] for row in g[:-1]]
    obs = sorted(objects(body, bg=0), key=len)
    out = [row[:] for row in body]
    for i, o in enumerate(obs):
        col = pal[min(i, len(pal) - 1)]
        for r, c in o: out[r][c] = col
    return out + [g[-1]]
rule("gradient_objects_by_size", "The bottom row is a palette; objects (minus that row) sorted smallest to largest by cell count take successive palette colours, extra objects beyond the palette length getting the last colour.", gi_sizesort, tf_sizesort)


# 6 ---- the palette reversed applied right to left across stripes.
def gi_revstripe(rng):
    h, w = _hw(rng, 9)
    pal = _palette_row(rng, 3, 6)
    stripe_col = rng.choice([c for c in COLOURS if c not in pal])
    g = [[stripe_col] * w for _ in range(h)]
    g = [row + [0] for row in g]
    for i, c in enumerate(pal): g[i][-1] = c
    for r in range(len(pal), h): g[r][-1] = 0
    return g
def tf_revstripe(g):
    h = len(g); w = len(g[0]) - 1
    pal = [g[r][-1] for r in range(h) if g[r][-1] != 0]
    rpal = pal[::-1]
    out = blank(h, w)
    for c in range(w):
        idx = min(len(rpal) - 1, c * len(rpal) // w)
        for r in range(h): out[r][c] = rpal[idx]
    return [row + [g[r][-1]] for r, row in enumerate(out)]
rule("vertical_stripes_reversed_palette_r_to_l", "The last column (top down) holds a palette; the body is repainted into vertical stripes using the REVERSED palette order read right to left, so the rightmost columns get the palette's first colour and the leftmost get its last, the key column kept as is.", gi_revstripe, tf_revstripe)


# 7 ---- a ring gradient around a centre marker, concentric rings taking successive palette colours.
def gi_ring(rng):
    side = rng.randint(9, 23) if rng.random() < 0.5 else rng.randint(21, 29)
    side = side if side % 2 == 1 else side + 1
    g = blank(side, side)
    pal = _palette_row(rng, 3, 5)
    cen = side // 2
    g[cen][cen] = 8
    g2 = blank(side + 1, side)
    for i, c in enumerate(pal): g2[0][i] = c
    for r in range(side):
        for c in range(side): g2[r + 1][c] = g[r][c]
    return g2
def tf_ring(g):
    pal = [v for v in g[0] if v != 0]
    body = g[1:]
    side = len(body)
    cen = side // 2
    maxd = max(abs(cen), side - 1 - cen)
    out = blank(side, side)
    for r in range(side):
        for c in range(side):
            d = max(abs(r - cen), abs(c - cen))
            idx = min(len(pal) - 1, d * len(pal) // (maxd + 1))
            out[r][c] = pal[idx]
    return [g[0]] + out
rule("ring_gradient_from_centre", "The top row is a palette; a square body is filled with concentric square rings centred on its middle cell, ring distance measured as Chebyshev distance, nearest ring taking the palette's first colour and rings farther out stepping through the palette outward.", gi_ring, tf_ring)


# 8 ---- the palette repeated cyclically along a boustrophedon (snake) path through the grid.
def gi_snake(rng):
    h, w = _hw(rng, 8)
    pal = _palette_row(rng, 2, 4)
    g = blank(h, w)
    for r in range(h):
        for c in range(w): g[r][c] = 1
    g2 = blank(h + 1, w)
    for i, c in enumerate(pal): g2[0][i] = c
    for r in range(h):
        for c in range(w): g2[r + 1][c] = g[r][c]
    return g2
def tf_snake(g):
    pal = [v for v in g[0] if v != 0]
    body = g[1:]
    h, w = dims(body)
    out = [row[:] for row in body]
    idx = 0
    for r in range(h):
        cs = range(w) if r % 2 == 0 else range(w - 1, -1, -1)
        for c in cs:
            out[r][c] = pal[idx % len(pal)]
            idx += 1
    return [g[0]] + out
rule("snake_path_cyclic_palette", "The top row is a palette; the body below is filled by walking it boustrophedon-style (row 0 left to right, row 1 right to left, and so on) and cycling repeatedly through the palette colours in order as each cell is visited.", gi_snake, tf_snake)


# 9 ---- each row's cells take the palette colour at (row index mod palette length).
def gi_rowmod(rng):
    h, w = _hw(rng, 8); g = blank(h, w)
    pal = _palette_row(rng, 2, 5)
    fill = rng.choice([c for c in COLOURS if c not in pal])
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.6: g[r][c] = fill
    g2 = blank(h + 1, w)
    for i, c in enumerate(pal): g2[0][i] = c
    for r in range(h):
        for c in range(w): g2[r + 1][c] = g[r][c]
    return g2
def tf_rowmod(g):
    pal = [v for v in g[0] if v != 0]
    body = g[1:]
    h, w = dims(body)
    out = [row[:] for row in body]
    for r in range(h):
        col = pal[r % len(pal)]
        for c in range(w):
            if body[r][c] != 0: out[r][c] = col
    return [g[0]] + out
rule("row_colour_by_index_mod_palette", "The top row is a palette; every non-background cell in each row of the body is recoloured with the palette colour at index (that row's position mod the palette length), row 0 directly beneath the palette.", gi_rowmod, tf_rowmod)


# 10 ---- bar chart: each bar's height picks the palette colour by height rank (digits carry meaning).
def gi_barheight(rng):
    if rng.random() < 0.45:
        h, w = rng.randint(21, 30), rng.randint(21, 30)
    else:
        h, w = rng.randint(6, 14), rng.randint(6, 18)
    pal = _palette_row(rng, 3, 6)
    k = len(pal)
    heights = rng.sample(range(1, h + 1), min(k, h))
    if len(heights) < 2: return None
    g = blank(h + 1, w)
    bar_col = rng.choice([c for c in COLOURS if c not in pal])
    cols_used = rng.sample(range(w), len(heights))
    for i, c in enumerate(cols_used):
        for r in range(h - heights[i], h): g[r + 1][c] = bar_col
    for i, c in enumerate(pal): g[0][i] = c
    return g
def tf_barheight(g):
    pal = [v for v in g[0] if v != 0]
    body = g[1:]
    h, w = dims(body)
    cols = [c for c in range(w) if any(body[r][c] for r in range(h))]
    heights = {c: sum(1 for r in range(h) if body[r][c]) for c in cols}
    ordered = sorted(heights.values())
    rank = {v: i for i, v in enumerate(ordered)}
    out = [row[:] for row in body]
    for c in cols:
        idx = min(len(pal) - 1, rank[heights[c]])
        for r in range(h):
            if body[r][c]: out[r][c] = pal[idx]
    return [g[0]] + out
rule("bar_chart_colour_by_height_rank", "The top row is a palette; each vertical bar below it is recoloured using the palette colour at the rank of its height among all bars present (shortest bar gets the first palette colour), with digits=True since height ranks are read off the grid.", gi_barheight, tf_barheight, digits=True)


# 11 ---- objects nearest a marker get the first palette colour, farthest get the last.
def gi_nearmark(rng):
    h, w = _hw(rng, 9); g = blank(h, w)
    pal = _palette_row(rng, 3, 5)
    k = len(pal)
    shapes = [random_shape(rng, rng.randint(2, 5)) for _ in range(k)]
    other = [c for c in COLOURS if c not in pal] or pal
    pos = place_shapes(rng, g, shapes, [rng.choice(other) for _ in range(k)], margin=2)
    if pos is None: return None
    free = [(r, c) for r in range(h) for c in range(w) if g[r][c] == 0]
    if not free: return None
    mr, mc = rng.choice(free)
    g[mr][mc] = 8 if 8 not in pal else 9
    g2 = blank(h + 1, w)
    for i, c in enumerate(pal): g2[0][i] = c
    for r in range(h):
        for c in range(w): g2[r + 1][c] = g[r][c]
    return g2
def tf_nearmark(g):
    pal = [v for v in g[0] if v != 0]
    body = g[1:]
    h, w = dims(body)
    mr, mc = next((r, c) for r in range(h) for c in range(w) if body[r][c] not in (0,) and body[r][c] in (8, 9))
    mk = body[mr][mc]
    obs = objects(body, bg=0)
    obs = [o for o in obs if not (len(o) == 1 and body[o[0][0]][o[0][1]] in (8, 9))]
    def dist(o):
        return min(abs(r - mr) + abs(c - mc) for r, c in o)
    ordered = sorted(obs, key=dist)
    out = [row[:] for row in body]
    for i, o in enumerate(ordered):
        col = pal[min(i, len(pal) - 1)]
        for r, c in o: out[r][c] = col
    out[mr][mc] = mk
    return [g[0]] + out
rule("objects_by_distance_from_marker", "The top row is a palette; a single marker cell sits apart from all objects, and the objects are sorted by Manhattan distance from their nearest cell to the marker, nearest object taking the first palette colour and so on, extras repeating the last colour.", gi_nearmark, tf_nearmark)


# 12 ---- gradient direction set by an arrow glyph (two marker cells pointing left/right/up/down).
def gi_arrowdir(rng):
    h, w = _hw(rng, 8)
    pal = _palette_row(rng, 3, 5)
    direction = rng.choice(["L", "R", "U", "D"])
    g = blank(h, w)
    for r in range(h):
        for c in range(w): g[r][c] = 1
    g2 = blank(h + 1, w)
    for i, c in enumerate(pal): g2[0][i] = c
    for r in range(h):
        for c in range(w): g2[r + 1][c] = g[r][c]
    if direction == "L": g2[0][-1] = 7
    elif direction == "R": g2[0][-2] = 7 if w > 1 else g2[0][-1]
    elif direction == "U": g2[-1][0] = 7
    else: g2[1][0] = 7 if h > 1 else g2[0][0]
    return g2 if direction in ("L", "R", "U", "D") else None
def tf_arrowdir(g):
    pal = [v for v in g[0][:-2] if v != 0] or [v for v in g[0] if v != 0]
    pal = [v for v in g[0] if v != 0 and v != 7]
    body = g[1:]
    h, w = dims(body)
    if g[0][-1] == 7: direction = "L"
    elif len(g[0]) > 1 and g[0][-2] == 7: direction = "R"
    elif g[-1][0] == 7: direction = "U"
    elif h > 1 and g[1][0] == 7: direction = "D"
    else: return None
    out = [row[:] for row in body]
    n = len(pal)
    for r in range(h):
        for c in range(w):
            if direction == "L": idx = min(n - 1, c * n // w)
            elif direction == "R": idx = min(n - 1, (w - 1 - c) * n // w)
            elif direction == "U": idx = min(n - 1, r * n // h)
            else: idx = min(n - 1, (h - 1 - r) * n // h)
            out[r][c] = pal[idx]
    return [g[0]] + out
rule("gradient_direction_from_arrow_glyph", "The top row holds a palette plus one glyph cell valued 7 marking direction (7 at the row's far right = gradient runs left-to-right, far left-ish by convention = right-to-left; a 7 in the body's first column, row 0 means top-to-bottom, row 1 means bottom-to-top), and the whole body is repainted as a gradient through the palette in that direction.", gi_arrowdir, tf_arrowdir)


# 13 ---- two palettes blended alternately by column parity.
def gi_blend(rng):
    h, w = _hw(rng, 8)
    pal_a = _palette_row(rng, 2, 4)
    rest = [c for c in COLOURS if c not in pal_a]
    pal_b = rng.sample(rest, min(len(pal_a), len(rest)))
    if len(pal_b) < 2: return None
    fill = rng.choice([c for c in COLOURS if c not in pal_a and c not in pal_b])
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.7: g[r][c] = fill
    g2 = blank(h + 2, w)
    for i, c in enumerate(pal_a): g2[0][i] = c
    for i, c in enumerate(pal_b): g2[1][i] = c
    for r in range(h):
        for c in range(w): g2[r + 2][c] = g[r][c]
    return g2
def tf_blend(g):
    pal_a = [v for v in g[0] if v != 0]
    pal_b = [v for v in g[1] if v != 0]
    body = g[2:]
    h, w = dims(body)
    out = [row[:] for row in body]
    for r in range(h):
        for c in range(w):
            if body[r][c] == 0: continue
            pal = pal_a if c % 2 == 0 else pal_b
            idx = min(len(pal) - 1, c * len(pal) // w)
            out[r][c] = pal[idx]
    return [g[0], g[1]] + out
rule("two_palettes_blended_by_column_parity", "Rows 0 and 1 each hold a palette (A then B); in the body, even columns are gradient-painted through palette A left to right and odd columns through palette B left to right, each column's position within the full width picking the palette index.", gi_blend, tf_blend)


# 14 ---- diagonal gradient, top-left to bottom-right, keyed by anti-diagonal index.
def gi_diag(rng):
    h, w = _hw(rng, 8)
    pal = _palette_row(rng, 3, 6)
    fill = rng.choice([c for c in COLOURS if c not in pal])
    g = [[fill] * w for _ in range(h)]
    g2 = blank(h + 1, w)
    for i, c in enumerate(pal): g2[0][i] = c
    for r in range(h):
        for c in range(w): g2[r + 1][c] = g[r][c]
    return g2
def tf_diag(g):
    pal = [v for v in g[0] if v != 0]
    body = g[1:]
    h, w = dims(body)
    maxs = h + w - 2
    out = [row[:] for row in body]
    for r in range(h):
        for c in range(w):
            s = r + c
            idx = min(len(pal) - 1, s * len(pal) // (maxs + 1))
            out[r][c] = pal[idx]
    return [g[0]] + out
rule("diagonal_gradient_tl_to_br", "The top row is a palette; the solid-filled body is repainted as a diagonal gradient where each cell's colour is picked from the palette by its row+column sum, bucketed evenly from the top-left corner (first colour) to the bottom-right corner (last colour).", gi_diag, tf_diag)


# 15 ---- objects sorted by size take the palette in DESCENDING order (largest gets first colour).
def gi_sizedesc(rng):
    h, w = _hw(rng, 9); g = blank(h, w)
    pal = _palette_row(rng, 3, 6)
    k = len(pal)
    sizes = rng.sample(range(2, 2 + 2 * k), k)
    shapes = [random_shape(rng, n) for n in sizes]
    other = [c for c in COLOURS if c not in pal] or pal
    if place_shapes(rng, g, shapes, [rng.choice(other) for _ in range(k)], margin=1) is None:
        return None
    g.append([0] * w)
    for i, c in enumerate(pal): g[-1][i] = c
    return g
def tf_sizedesc(g):
    pal = [v for v in g[-1] if v != 0]
    body = [row[:] for row in g[:-1]]
    obs = sorted(objects(body, bg=0), key=len, reverse=True)
    out = [row[:] for row in body]
    for i, o in enumerate(obs):
        col = pal[min(i, len(pal) - 1)]
        for r, c in o: out[r][c] = col
    return out + [g[-1]]
rule("gradient_objects_by_size_desc", "The bottom row is a palette; objects (minus that row) sorted largest to smallest by cell count take successive palette colours, so the biggest object gets the palette's first colour, extras beyond the palette length getting the last colour.", gi_sizedesc, tf_sizedesc)


# 16 ---- concentric rows from the top and bottom simultaneously (outside-in gradient).
def gi_outsidein(rng):
    h, w = _hw(rng, 9)
    pal = _palette_row(rng, 2, 5)
    fill = rng.choice([c for c in COLOURS if c not in pal])
    g = [[fill] * w for _ in range(h)]
    g2 = blank(h + 1, w)
    for i, c in enumerate(pal): g2[0][i] = c
    for r in range(h):
        for c in range(w): g2[r + 1][c] = g[r][c]
    return g2
def tf_outsidein(g):
    pal = [v for v in g[0] if v != 0]
    body = g[1:]
    h, w = dims(body)
    out = [row[:] for row in body]
    for r in range(h):
        d = min(r, h - 1 - r)
        idx = min(len(pal) - 1, d * len(pal) // ((h // 2) + 1))
        out[r] = [pal[idx]] * w
    return [g[0]] + out
rule("row_gradient_outside_in", "The top row is a palette; the body's rows are repainted solid, each row's colour chosen by distance from the NEARER of the top or bottom edge bucketed across the palette, so the outermost rows (top and bottom) get the first colour and the middle rows get the last.", gi_outsidein, tf_outsidein)


# 17 ---- a single column gradient, palette applied left to right, each column one solid colour.
def gi_colgrad(rng):
    h, w = _hw(rng, 6)
    pal = _palette_row(rng, 3, 6)
    fill = rng.choice([c for c in COLOURS if c not in pal])
    g = [[fill] * w for _ in range(h)]
    g2 = blank(h + 1, w)
    for i, c in enumerate(pal): g2[0][i] = c
    for r in range(h):
        for c in range(w): g2[r + 1][c] = g[r][c]
    return g2
def tf_colgrad(g):
    pal = [v for v in g[0] if v != 0]
    body = g[1:]
    h, w = dims(body)
    out = [row[:] for row in body]
    for c in range(w):
        idx = min(len(pal) - 1, c * len(pal) // w)
        for r in range(h): out[r][c] = pal[idx]
    return [g[0]] + out
rule("column_gradient_left_to_right", "The top row is a palette; the solid-filled body below is repainted into vertical bands, each column's colour chosen by its position bucketed evenly across the palette left to right.", gi_colgrad, tf_colgrad)


# 18 ---- cyclic column gradient: palette repeats every len(pal) columns (not stretched).
def gi_colcyc(rng):
    h, w = _hw(rng, 6)
    pal = _palette_row(rng, 2, 5)
    fill = rng.choice([c for c in COLOURS if c not in pal])
    g = [[fill] * w for _ in range(h)]
    g2 = blank(h + 1, w)
    for i, c in enumerate(pal): g2[0][i] = c
    for r in range(h):
        for c in range(w): g2[r + 1][c] = g[r][c]
    return g2
def tf_colcyc(g):
    pal = [v for v in g[0] if v != 0]
    body = g[1:]
    h, w = dims(body)
    out = [row[:] for row in body]
    for c in range(w):
        col = pal[c % len(pal)]
        for r in range(h): out[r][c] = col
    return [g[0]] + out
rule("column_palette_cycle_repeating", "The top row is a palette; the solid body is repainted into vertical stripes of width one column, cycling the palette colours in order and repeating from the first colour once the palette is exhausted (column index mod palette length).", gi_colcyc, tf_colcyc)


# 19 ---- a frame-within-frame gradient: nested rectangular borders coloured in palette order from outside in.
def gi_frames_grad(rng):
    side = rng.randint(9, 23) if rng.random() < 0.6 else rng.randint(21, 29)
    pal = _palette_row(rng, 3, 5)
    g = blank(side, side)
    noise = rng.choice([c for c in COLOURS if c not in pal])
    for _ in range(rng.randint(1, side * side // 4)):
        g[rng.randrange(side)][rng.randrange(side)] = noise
    g2 = blank(side + 1, side)
    for i, c in enumerate(pal): g2[0][i] = c
    for r in range(side):
        for c in range(side): g2[r + 1][c] = g[r][c]
    return g2
def tf_frames_grad(g):
    pal = [v for v in g[0] if v != 0]
    body = g[1:]
    side = len(body)
    out = [row[:] for row in body]
    n = len(pal)
    maxring = (side + 1) // 2
    for r in range(side):
        for c in range(side):
            ring = min(r, c, side - 1 - r, side - 1 - c)
            idx = min(n - 1, ring * n // maxring)
            out[r][c] = pal[idx]
    return [g[0]] + out
rule("nested_frames_gradient_outside_in", "The top row is a palette; a blank square body is filled entirely with nested square frames, ring depth measured as distance to the nearest edge, the outermost ring taking the palette's first colour and deeper rings stepping through the palette toward the centre.", gi_frames_grad, tf_frames_grad)


# 20 ---- objects recoloured by their vertical (top) position, topmost gets first palette colour.
def gi_objtop(rng):
    h, w = _hw(rng, 9); g = blank(h, w)
    pal = _palette_row(rng, 3, 6)
    k = len(pal)
    shapes = [random_shape(rng, rng.randint(2, 6)) for _ in range(k)]
    other = [c for c in COLOURS if c not in pal] or pal
    if place_shapes(rng, g, shapes, [rng.choice(other) for _ in range(k)], margin=1) is None:
        return None
    g.append([0] * w)
    for i, c in enumerate(pal): g[-1][i] = c
    return g
def tf_objtop(g):
    pal = [v for v in g[-1] if v != 0]
    body = [row[:] for row in g[:-1]]
    obs = sorted(objects(body, bg=0), key=lambda o: min(r for r, _ in o))
    out = [row[:] for row in body]
    for i, o in enumerate(obs):
        col = pal[min(i, len(pal) - 1)]
        for r, c in o: out[r][c] = col
    return out + [g[-1]]
rule("gradient_objects_top_to_bottom", "The bottom row is a palette; objects (minus that row) sorted by their topmost row take successive palette colours top object first, extras beyond the palette length repeating the last colour.", gi_objtop, tf_objtop)


# 21 ---- radial gradient from a fixed corner (top-left), Euclidean distance bucketed.
def gi_cornerrad(rng):
    h, w = _hw(rng, 8)
    pal = _palette_row(rng, 3, 6)
    fill = rng.choice([c for c in COLOURS if c not in pal])
    g = [[fill] * w for _ in range(h)]
    g2 = blank(h + 1, w)
    for i, c in enumerate(pal): g2[0][i] = c
    for r in range(h):
        for c in range(w): g2[r + 1][c] = g[r][c]
    return g2
def tf_cornerrad(g):
    pal = [v for v in g[0] if v != 0]
    body = g[1:]
    h, w = dims(body)
    maxd = math.hypot(h - 1, w - 1)
    out = [row[:] for row in body]
    for r in range(h):
        for c in range(w):
            d = math.hypot(r, c)
            idx = min(len(pal) - 1, int(d * len(pal) / (maxd + 1e-9)))
            out[r][c] = pal[idx]
    return [g[0]] + out
rule("radial_gradient_from_top_left_corner", "The top row is a palette; the solid-filled body is repainted as a radial gradient measured by Euclidean distance from the top-left corner cell, bucketed evenly across the palette so the corner itself gets the first colour and the far corner gets the last.", gi_cornerrad, tf_cornerrad)


# 22 ---- stripes repainted bottom-up in palette order (palette's first colour at the BOTTOM).
def gi_stripesup(rng):
    h, w = _hw(rng, 9)
    pal = _palette_row(rng, 3, 6)
    stripe_col = rng.choice([c for c in COLOURS if c not in pal])
    g = [[stripe_col] * w for _ in range(h)]
    g.append([0] * w)
    for i, c in enumerate(pal): g[-1][i] = c
    return g
def tf_stripesup(g):
    pal = [v for v in g[-1] if v != 0]
    h = len(g) - 1; w = len(g[0])
    out = blank(h, w)
    for r in range(h):
        idx = (h - 1 - r) % len(pal)
        out[r] = [pal[idx]] * w
    return out + [g[-1]]
rule("stripes_in_palette_order_bottomup", "The bottom row is a palette; each row above is repainted solid using the palette colour at index ((h-1-row) mod palette length), so the row directly above the palette gets its first colour and colour order climbs upward.", gi_stripesup, tf_stripesup)


# 23 ---- two markers on opposite rows/cols blended as a gradient filling the whole rectangle between them.
def gi_rectgrad(rng):
    h, w = _hw(rng, 8); g = blank(h, w)
    pal = _palette_row(rng, 3, 5)
    for r in range(h):
        for c in range(w): g[r][c] = 1
    g2 = blank(h + 1, w)
    for i, c in enumerate(pal): g2[0][i] = c
    for r in range(h):
        for c in range(w): g2[r + 1][c] = g[r][c]
    return g2
def tf_rectgrad(g):
    pal = [v for v in g[0] if v != 0]
    body = g[1:]
    h, w = dims(body)
    out = [row[:] for row in body]
    n = len(pal)
    for r in range(h):
        for c in range(w):
            pos = (r * w + c)
            idx = min(n - 1, pos * n // (h * w))
            out[r][c] = pal[idx]
    return [g[0]] + out
rule("reading_order_gradient", "The top row is a palette; the solid body is repainted in reading order (row by row, left to right within each row), each cell's flattened position bucketed evenly across the palette, the first cell getting the first colour and the last cell the last.", gi_rectgrad, tf_rectgrad)


# 24 ---- objects recoloured by count of cells, grouped into equal-size buckets of the palette (histogram-style).
def gi_histobucket(rng):
    h, w = _hw(rng, 10); g = blank(h, w)
    pal = _palette_row(rng, 3, 5)
    k = rng.randint(len(pal) + 1, len(pal) * 2)
    shapes = [random_shape(rng, rng.randint(2, 10)) for _ in range(k)]
    other = [c for c in COLOURS if c not in pal] or pal
    if place_shapes(rng, g, shapes, [rng.choice(other) for _ in range(k)], margin=1) is None:
        return None
    g.append([0] * w)
    for i, c in enumerate(pal): g[-1][i] = c
    return g
def tf_histobucket(g):
    pal = [v for v in g[-1] if v != 0]
    body = [row[:] for row in g[:-1]]
    obs = objects(body, bg=0)
    sizes = sorted(set(len(o) for o in obs))
    rank = {s: i for i, s in enumerate(sizes)}
    out = [row[:] for row in body]
    for o in obs:
        idx = min(len(pal) - 1, rank[len(o)])
        for r, c in o: out[r][c] = pal[idx]
    return out + [g[-1]]
rule("objects_by_size_rank_bucketed", "The bottom row is a palette; objects (minus that row) are grouped by their distinct cell counts, counts sorted ascending and numbered 0,1,2,..., and every object takes the palette colour at its count's rank, the same size always getting the same colour.", gi_histobucket, tf_histobucket, digits=True)


# 25 ---- an expanding square spiral painted with the palette cycling at each full turn.
def gi_spiral(rng):
    side = rng.randint(7, 21) if rng.random() < 0.55 else rng.randint(21, 29)
    pal = _palette_row(rng, 2, 4)
    g = blank(side, side)
    noise = rng.choice([c for c in COLOURS if c not in pal])
    for _ in range(rng.randint(1, side * side // 4)):
        g[rng.randrange(side)][rng.randrange(side)] = noise
    g2 = blank(side + 1, side)
    for i, c in enumerate(pal): g2[0][i] = c
    for r in range(side):
        for c in range(side): g2[r + 1][c] = g[r][c]
    return g2
def tf_spiral(g):
    pal = [v for v in g[0] if v != 0]
    body = g[1:]
    side = len(body)
    out = [row[:] for row in body]
    top, bot, left, right = 0, side - 1, 0, side - 1
    idx = 0
    while top <= bot and left <= right:
        for c in range(left, right + 1): out[top][c] = pal[idx % len(pal)]
        idx += 1
        for r in range(top + 1, bot + 1): out[r][right] = pal[idx % len(pal)]
        idx += 1
        if top != bot:
            for c in range(right - 1, left - 1, -1): out[bot][c] = pal[idx % len(pal)]
            idx += 1
        if left != right:
            for r in range(bot - 1, top, -1): out[r][left] = pal[idx % len(pal)]
            idx += 1
        top += 1; bot -= 1; left += 1; right -= 1
    return [g[0]] + out
rule("spiral_rings_cycling_palette", "The top row is a palette; the square body is filled ring by ring from the outside in (each ring is one lap of the square border), each full ring taking the next palette colour in cyclic order starting from the outermost ring with the first colour.", gi_spiral, tf_spiral)


# 26 ---- a chevron (V-shape) gradient keyed by distance from the bottom-middle apex.
def gi_chevron(rng):
    h, w = _hw(rng, 8)
    pal = _palette_row(rng, 3, 6)
    fill = rng.choice([c for c in COLOURS if c not in pal])
    g = [[fill] * w for _ in range(h)]
    g2 = blank(h + 1, w)
    for i, c in enumerate(pal): g2[0][i] = c
    for r in range(h):
        for c in range(w): g2[r + 1][c] = g[r][c]
    return g2
def tf_chevron(g):
    pal = [v for v in g[0] if v != 0]
    body = g[1:]
    h, w = dims(body)
    mid = w // 2
    maxd = (h - 1) + max(mid, w - 1 - mid)
    out = [row[:] for row in body]
    for r in range(h):
        for c in range(w):
            d = (h - 1 - r) + abs(c - mid)
            idx = min(len(pal) - 1, d * len(pal) // (maxd + 1))
            out[r][c] = pal[idx]
    return [g[0]] + out
rule("chevron_gradient_from_bottom_apex", "The top row is a palette; the solid body is repainted as a V-shaped gradient measured as Manhattan distance from the bottom-middle cell (the apex), the apex itself getting the palette's first colour and distance stepping outward and upward through the rest of the palette.", gi_chevron, tf_chevron)


# 27 ---- rows alternate between two palette halves (odd/even split of one palette, not two).
def gi_splitpal(rng):
    h, w = _hw(rng, 8)
    pal = _palette_row(rng, 4, 6)
    fill = rng.choice([c for c in COLOURS if c not in pal])
    g = [[fill] * w for _ in range(h)]
    g2 = blank(h + 1, w)
    for i, c in enumerate(pal): g2[0][i] = c
    for r in range(h):
        for c in range(w): g2[r + 1][c] = g[r][c]
    return g2 if len(pal) >= 4 else None
def tf_splitpal(g):
    pal = [v for v in g[0] if v != 0]
    half = len(pal) // 2
    first, second = pal[:half], pal[half:]
    body = g[1:]
    h, w = dims(body)
    out = [row[:] for row in body]
    for r in range(h):
        pal_r = first if r % 2 == 0 else second
        idx = min(len(pal_r) - 1, r // 2 % len(pal_r))
        for c in range(w): out[r][c] = pal_r[idx]
    return [g[0]] + out
rule("alternating_rows_split_palette_halves", "The top row is a palette split in half (first half for even rows, second half for odd rows); each row of the body is painted solid with its half-palette's colour at index floor(row/2) mod that half's length, even and odd rows cycling independently.", gi_splitpal, tf_splitpal)


# 28 ---- a keyed single-row legend (row of colour+digit cue) maps each digit-bar to palette position by digit value.
def gi_digitbar(rng):
    w = rng.randint(21, 29) if rng.random() < 0.35 else rng.randint(6, 18)
    pal = _palette_row(rng, 4, 6)
    n = len(pal)
    digits_row = [rng.randrange(n) for _ in range(w)]
    g = [digits_row[:]]
    g.append([0] * w)
    for i, c in enumerate(pal): g[-1][i] = c
    return g if len(set(digits_row)) > 1 else None
def tf_digitbar(g):
    pal = [v for v in g[-1] if v != 0]
    digits_row = g[0]
    out = [pal[d] if 0 <= d < len(pal) else d for d in digits_row]
    return [out, g[-1]]
rule("digit_row_lookup_into_palette", "Row 1 is a palette; row 0 holds small index digits (0-based), and each digit is replaced by the palette colour at that index, the palette row unchanged below it; digits=True because the top row's values are literal indices.", gi_digitbar, tf_digitbar, digits=True)


# 29 ---- objects recoloured by distance-rank from the LEFT edge wall (projection gradient).
def gi_wallgrad(rng):
    h, w = _hw(rng, 9); g = blank(h, w)
    pal = _palette_row(rng, 3, 6)
    k = len(pal)
    shapes = [random_shape(rng, rng.randint(2, 6)) for _ in range(k)]
    other = [c for c in COLOURS if c not in pal] or pal
    if place_shapes(rng, g, shapes, [rng.choice(other) for _ in range(k)], margin=1) is None:
        return None
    g.append([0] * w)
    for i, c in enumerate(pal): g[-1][i] = c
    return g
def tf_wallgrad(g):
    pal = [v for v in g[-1] if v != 0]
    body = [row[:] for row in g[:-1]]
    obs = sorted(objects(body, bg=0), key=lambda o: min(c for _, c in o))
    out = [row[:] for row in body]
    n = len(pal)
    for i, o in enumerate(obs):
        idx = min(n - 1, i * n // max(1, len(obs)))
        col = pal[idx]
        for r, c in o: out[r][c] = col
    return out + [g[-1]]
rule("objects_proportional_rank_to_palette", "The bottom row is a palette; objects (minus that row) sorted by their leftmost column take palette colours spread proportionally across the whole palette by rank (rank*paletteLength // objectCount), so with as many objects as palette colours each object gets a distinct one in order, and with fewer objects some palette colours are skipped.", gi_wallgrad, tf_wallgrad)


# 30 ---- gradient along a straight diagonal line object (not axis-aligned), by step count from one end.
def gi_diagline(rng):
    side = rng.randint(21, 29) if rng.random() < 0.3 else rng.randint(7, 18)
    g = blank(side, side)
    pal = _palette_row(rng, 3, 6)
    n = min(len(pal) * 2, side)
    if n < 3: return None
    r0, c0 = 0, rng.randrange(side - n + 1) if side - n + 1 > 0 else 0
    for i in range(n):
        if r0 + i < side and c0 + i < side:
            g[r0 + i][c0 + i] = 1
    g2 = blank(side + 1, side)
    for i, c in enumerate(pal): g2[0][i] = c
    for r in range(side):
        for c in range(side): g2[r + 1][c] = g[r][c]
    return g2
def tf_diagline(g):
    pal = [v for v in g[0] if v != 0]
    body = g[1:]
    h, w = dims(body)
    pts = sorted(cells(body, lambda v: v == 1), key=lambda rc: (rc[0], rc[1]))
    if not pts: return None
    out = [row[:] for row in body]
    n = len(pts)
    for i, (r, c) in enumerate(pts):
        idx = min(len(pal) - 1, i * len(pal) // n)
        out[r][c] = pal[idx]
    return [g[0]] + out
rule("diagonal_line_gradient_by_step", "The top row is a palette; a diagonal line of colour-1 cells runs top-left to bottom-right, and each cell along it is recoloured by its step position from the topmost end, bucketed evenly across the palette so the first step gets the first colour.", gi_diagline, tf_diagline)


# 31 ---- a grid of equal blocks, each block recoloured by its block-row + block-col sum mod palette length.
def gi_blockgrad(rng):
    if rng.random() < 0.45:
        bs = 3; nb = rng.choice([7, 8, 9])
    else:
        bs = rng.choice([2, 3]); nb = rng.randint(3, 5)
    h = w = bs * nb
    if h > 30: h = w = 30 - (30 % bs)
    pal = _palette_row(rng, 2, 5)
    fill = rng.choice([c for c in COLOURS if c not in pal])
    g = [[fill] * w for _ in range(h)]
    noise = rng.choice([c for c in COLOURS if c not in pal and c != fill])
    for _ in range(rng.randint(1, h * w // 4)):
        g[rng.randrange(h)][rng.randrange(w)] = noise
    g2 = blank(h + 1, w)
    for i, c in enumerate(pal): g2[0][i] = c
    for r in range(h):
        for c in range(w): g2[r + 1][c] = g[r][c]
    return g2
def tf_blockgrad(g, bs=None):
    pal = [v for v in g[0] if v != 0]
    body = g[1:]
    h, w = dims(body)
    bs = 2 if h % 2 == 0 and w % 2 == 0 and (h % 3 or w % 3) else (3 if h % 3 == 0 and w % 3 == 0 else None)
    if bs is None: return None
    out = [row[:] for row in body]
    for br in range(h // bs):
        for bc in range(w // bs):
            idx = (br + bc) % len(pal)
            col = pal[idx]
            for r in range(br * bs, br * bs + bs):
                for c in range(bc * bs, bc * bs + bs): out[r][c] = col
    return [g[0]] + out
rule("block_mosaic_gradient_by_sum_mod", "The top row is a palette; the body is a grid of equal square blocks (side 2 or 3, inferred from the body's dimensions), and each block is painted solid with the palette colour at index (block-row + block-column) mod palette length, the top-left block always using index 0.", gi_blockgrad, tf_blockgrad)


# 32 ---- a single marker's hue picks a START index into a fixed-length rainbow applied along columns.
def gi_startidx(rng):
    h, w = _hw(rng, 8)
    pal = _palette_row(rng, 3, 6)
    start = rng.randrange(len(pal))
    fill = rng.choice([c for c in COLOURS if c not in pal])
    g = [[fill] * w for _ in range(h)]
    g2 = blank(h + 1, w)
    for i, c in enumerate(pal): g2[0][i] = c
    g2[0][-1] = start + 1 if (start + 1) not in pal else 0
    for r in range(h):
        for c in range(w): g2[r + 1][c] = g[r][c]
    return g2
def tf_startidx(g):
    pal_full = g[0]
    start_val = pal_full[-1]
    pal = [v for v in pal_full[:-1] if v != 0]
    body = g[1:]
    h, w = dims(body)
    out = [row[:] for row in body]
    n = len(pal)
    start = start_val % n if n else 0
    for c in range(w):
        idx = (start + c * n // w) % n
        for r in range(h): out[r][c] = pal[idx]
    return [g[0]] + out
rule("column_gradient_with_rotated_start", "The top row holds a palette in its first cells and a start-offset value in its last cell; columns of the body are gradient-painted left to right through the palette as usual, but the sequence is rotated to begin at palette index (start value mod palette length) instead of index 0; digits=True is not set because the start cell is itself a colour read back as an index after mod.", gi_startidx, tf_startidx, digits=True)


# 33 ---- objects recoloured by their rightmost column rank, rightmost object first (mirror of rule 1).
def gi_objright(rng):
    h, w = _hw(rng, 8); g = blank(h, w)
    pal = _palette_row(rng, 3, 6)
    k = len(pal)
    shapes = [random_shape(rng, rng.randint(2, 6)) for _ in range(k)]
    other = [c for c in COLOURS if c not in pal] or pal
    if place_shapes(rng, g, shapes, [rng.choice(other) for _ in range(k)], margin=1) is None:
        return None
    g.append([0] * w)
    for i, c in enumerate(pal): g[-1][i] = c
    return g
def tf_objright(g):
    pal = [v for v in g[-1] if v != 0]
    body = [row[:] for row in g[:-1]]
    obs = sorted(objects(body, bg=0), key=lambda o: max(c for _, c in o), reverse=True)
    out = [row[:] for row in body]
    for i, o in enumerate(obs):
        col = pal[min(i, len(pal) - 1)]
        for r, c in o: out[r][c] = col
    return out + [g[-1]]
rule("gradient_objects_right_to_left", "The bottom row is a palette; objects (minus that row) sorted by their rightmost column, farthest right first, take successive palette colours in that order, extras beyond the palette length repeating the last colour.", gi_objright, tf_objright)


# 34 ---- rows of a bar chart recoloured by VALUE RANK read as digits in a legend row (digits carry data).
def gi_legendrank(rng):
    w = rng.randint(21, 29) if rng.random() < 0.3 else rng.randint(5, 18)
    pal = _palette_row(rng, 3, 6)
    n = len(pal)
    vals = [rng.randrange(n) for _ in range(w)]
    if len(set(vals)) < 2: return None
    g = [vals[:], [0] * w]
    for i, c in enumerate(pal): g[1][i] = c
    return g
def tf_legendrank(g):
    pal = [v for v in g[1] if v != 0]
    vals = g[0]
    uniq = sorted(set(vals))
    rank = {v: i for i, v in enumerate(uniq)}
    out = [pal[min(len(pal) - 1, rank[v])] for v in vals]
    return [out, g[1]]
rule("legend_row_values_ranked_to_palette", "Row 1 is a palette; row 0 holds small integer values, and each value is replaced by the palette colour at the RANK of that value among the distinct values present (smallest value present -> first palette colour), not by the raw value itself; digits=True since row 0's cells are literal numeric data.", gi_legendrank, tf_legendrank, digits=True)


# 35 ---- a cross/plus gradient from the centre, Manhattan distance restricted to the same row or column.
def gi_crossgrad(rng):
    h, w = _hw(rng, 9)
    pal = _palette_row(rng, 3, 5)
    g = blank(h, w)
    cr, cc = h // 2, w // 2
    fill = rng.choice([c for c in COLOURS if c not in pal])
    for c in range(w): g[cr][c] = fill
    for r in range(h): g[r][cc] = fill
    g2 = blank(h + 1, w)
    for i, c in enumerate(pal): g2[0][i] = c
    for r in range(h):
        for c in range(w): g2[r + 1][c] = g[r][c]
    return g2
def tf_crossgrad(g):
    pal = [v for v in g[0] if v != 0]
    body = g[1:]
    h, w = dims(body)
    cr, cc = h // 2, w // 2
    out = [row[:] for row in body]
    maxd = max(cr, h - 1 - cr, cc, w - 1 - cc) + 1
    for c in range(w):
        if body[cr][c]:
            d = abs(c - cc); idx = min(len(pal) - 1, d * len(pal) // maxd); out[cr][c] = pal[idx]
    for r in range(h):
        if body[r][cc]:
            d = abs(r - cr); idx = min(len(pal) - 1, d * len(pal) // maxd); out[r][cc] = pal[idx]
    return [g[0]] + out
rule("cross_gradient_from_centre", "The top row is a palette; a plus-shaped cross of coloured cells through the grid's centre row and column is repainted by distance along the arm from the centre cell, the centre itself getting the first palette colour and each arm stepping outward through the rest of the palette.", gi_crossgrad, tf_crossgrad)


# 36 ---- a checkerboard of two alternating palette colours chosen from a longer palette by parity of (r+c) rank.
def gi_checkpal(rng):
    h, w = _hw(rng, 8)
    pal = _palette_row(rng, 4, 6)
    fill = rng.choice([c for c in COLOURS if c not in pal])
    g = [[fill] * w for _ in range(h)]
    g2 = blank(h + 1, w)
    for i, c in enumerate(pal): g2[0][i] = c
    for r in range(h):
        for c in range(w): g2[r + 1][c] = g[r][c]
    return g2
def tf_checkpal(g):
    pal = [v for v in g[0] if v != 0]
    body = g[1:]
    h, w = dims(body)
    out = [row[:] for row in body]
    k = len(pal) // 2
    for r in range(h):
        for c in range(w):
            band = ((r + c) // 2) % k if k else 0
            parity = (r + c) % 2
            idx = band if parity == 0 else band + k
            idx = min(len(pal) - 1, idx)
            out[r][c] = pal[idx]
    return [g[0]] + out
rule("banded_checkerboard_palette_split", "The top row is a palette split into a first half and a second half; the body is painted in diagonal bands of width two (bucketed by (row+col)//2 mod half-length), using the first half's colours on cells where row+col is even and the second half's colours on cells where row+col is odd.", gi_checkpal, tf_checkpal)


# 37 ---- objects' COLOUR COUNT (how many objects share a colour) ranks which palette colour they get.
def gi_colourcount(rng):
    h, w = _hw(rng, 10); g = blank(h, w)
    pal = _palette_row(rng, 3, 5)
    base_cols = colours(rng, rng.randint(2, 4), exclude=tuple(pal) + (0,))
    if len(base_cols) < 2: return None
    k = rng.randint(len(base_cols), len(base_cols) * 3)
    picks = [rng.choice(base_cols) for _ in range(k)]
    shapes = [random_shape(rng, rng.randint(2, 6)) for _ in range(k)]
    if place_shapes(rng, g, shapes, picks, margin=1) is None:
        return None
    g.append([0] * w)
    for i, c in enumerate(pal): g[-1][i] = c
    return g
def tf_colourcount(g):
    pal = [v for v in g[-1] if v != 0]
    body = [row[:] for row in g[:-1]]
    obs = objects(body, bg=0)
    freq = {}
    for o in obs:
        col = body[o[0][0]][o[0][1]]
        freq[col] = freq.get(col, 0) + 1
    ordered_cols = sorted(freq.keys(), key=lambda c: freq[c])
    rank = {c: i for i, c in enumerate(ordered_cols)}
    out = [row[:] for row in body]
    for o in obs:
        orig = body[o[0][0]][o[0][1]]
        idx = min(len(pal) - 1, rank[orig])
        for r, c in o: out[r][c] = pal[idx]
    return out + [g[-1]]
rule("colour_group_frequency_to_palette", "The bottom row is a palette; objects (minus that row) that originally shared the same colour form one group, groups are ranked by how many objects they contain (fewest first), and every object in a group is recoloured with the palette colour at its group's rank.", gi_colourcount, tf_colourcount)


# 38 ---- a half-and-half split grid, left half gradient ascending, right half gradient descending (mirrored ramp).
def gi_mirrorramp(rng):
    h, w = _hw(rng, 8)
    if w % 2: w += 1
    if w > 30: w = 30
    pal = _palette_row(rng, 3, 6)
    fill = rng.choice([c for c in COLOURS if c not in pal])
    g = [[fill] * w for _ in range(h)]
    g2 = blank(h + 1, w)
    for i, c in enumerate(pal): g2[0][i] = c
    for r in range(h):
        for c in range(w): g2[r + 1][c] = g[r][c]
    return g2
def tf_mirrorramp(g):
    pal = [v for v in g[0] if v != 0]
    body = g[1:]
    h, w = dims(body)
    half = w // 2
    out = [row[:] for row in body]
    for c in range(w):
        if c < half:
            idx = min(len(pal) - 1, c * len(pal) // half)
        else:
            cc = w - 1 - c
            idx = min(len(pal) - 1, cc * len(pal) // half)
        for r in range(h): out[r][c] = pal[idx]
    return [g[0]] + out
rule("mirrored_ramp_from_both_edges", "The top row is a palette; the body is split into equal left and right halves, each half independently gradient-painted in columns from its own outer edge inward through the palette, so both the leftmost and rightmost columns get the first palette colour and the two inner edges (meeting at the centre) get the last.", gi_mirrorramp, tf_mirrorramp)


# 39 ---- a staircase gradient: each successive diagonal step-block of fixed width takes the next palette colour.
def gi_staircase(rng):
    h, w = _hw(rng, 9)
    pal = _palette_row(rng, 3, 6)
    fill = rng.choice([c for c in COLOURS if c not in pal])
    g = [[fill] * w for _ in range(h)]
    g2 = blank(h + 1, w)
    for i, c in enumerate(pal): g2[0][i] = c
    for r in range(h):
        for c in range(w): g2[r + 1][c] = g[r][c]
    return g2
def tf_staircase(g):
    pal = [v for v in g[0] if v != 0]
    body = g[1:]
    h, w = dims(body)
    step = max(1, (h + w) // (2 * len(pal)))
    out = [row[:] for row in body]
    maxsum = h + w - 2
    for r in range(h):
        for c in range(w):
            band = (r + c) // step
            idx = min(len(pal) - 1, band)
            out[r][c] = pal[idx]
    return [g[0]] + out
rule("staircase_bands_by_fixed_step", "The top row is a palette; the body is repainted in diagonal bands of fixed width equal to round((height+width)/(2*paletteLength)) (at least 1), banding by (row+col) integer-divided by that width, each successive band stepping to the next palette colour and clamping to the last once the palette runs out.", gi_staircase, tf_staircase)


# 40 ---- a keyed marker pair sets BOTH endpoints' colours explicitly; the gradient interpolates index positions between them, not necessarily palette[0]/palette[-1].
def gi_keyedends(rng):
    h, w = _hw(rng, 8)
    pal = _palette_row(rng, 4, 6)
    i0, i1 = sorted(rng.sample(range(len(pal)), 2))
    fill = rng.choice([c for c in COLOURS if c not in pal])
    g = [[fill] * w for _ in range(h)]
    g2 = blank(h + 1, w)
    for i, c in enumerate(pal): g2[0][i] = c
    g2[0][-1] = i0 + 1 if (i0 + 1) not in pal else 0
    g2[0][-2] = i1 + 1 if (i1 + 1) not in pal and w > 1 else g2[0][-1]
    for r in range(h):
        for c in range(w): g2[r + 1][c] = g[r][c]
    return g2 if w > 1 else None
def tf_keyedends(g):
    full = g[0]
    end_a, end_b = full[-1], full[-2]
    pal = [v for v in full[:-2] if v != 0]
    n = len(pal)
    i0, i1 = end_a % n, end_b % n
    body = g[1:]
    h, w = dims(body)
    out = [row[:] for row in body]
    for c in range(w):
        t = c / max(1, w - 1)
        idx = round(i0 + (i1 - i0) * t)
        idx = max(0, min(n - 1, idx))
        for r in range(h): out[r][c] = pal[idx]
    return [g[0]] + out
rule("column_gradient_between_keyed_indices", "The top row holds a palette in its leading cells and two key cells at its end giving start and end palette indices (mod palette length); columns of the body are gradient-painted left to right, linearly interpolating from the start index at the leftmost column to the end index at the rightmost column, rounding to the nearest palette entry; digits=True because the two key cells are read back as indices.", gi_keyedends, tf_keyedends, digits=True)
