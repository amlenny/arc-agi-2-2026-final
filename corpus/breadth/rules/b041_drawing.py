# b041_drawing.py -- GEOMETRIC DRAWING FROM CONTROL POINTS: scattered dots act as control points that
# define lines, polygons, and derived constructions (rectangles, triangles, diamonds, bisectors, stairs,
# fans, grids) drawn deterministically with Bresenham-style lines. A quarter or more of inputs 21-30 a side.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


# ---- local helpers -------------------------------------------------------------------------------------
def _big(rng, lo=21, hi=30):
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _dims(rng, small_lo, small_hi, big_frac=0.3):
    """Pick h, w so that ~big_frac of calls land in the 21..30 band."""
    if rng.random() < big_frac:
        return _big(rng)
    return rng.randint(small_lo, small_hi), rng.randint(small_lo, small_hi)


def _bresenham(r0, c0, r1, c1):
    """Points on the line segment from (r0,c0) to (r1,c1), Bresenham, inclusive both ends."""
    pts = []
    dr, dc = r1 - r0, c1 - c0
    sr = 1 if dr > 0 else -1 if dr < 0 else 0
    sc = 1 if dc > 0 else -1 if dc < 0 else 0
    adr, adc = abs(dr), abs(dc)
    r, c = r0, c0
    if adr >= adc:
        err = 0
        for _ in range(adr + 1):
            pts.append((r, c))
            err += adc
            if err * 2 >= adr:
                c += sc; err -= adr
            r += sr
    else:
        err = 0
        for _ in range(adc + 1):
            pts.append((r, c))
            err += adr
            if err * 2 >= adc:
                r += sr; err -= adc
            c += sc
    return pts


def _draw_line(g, p0, p1, colour):
    H, W = dims(g)
    for r, c in _bresenham(p0[0], p0[1], p1[0], p1[1]):
        if 0 <= r < H and 0 <= c < W:
            g[r][c] = colour
    return g


def _dots(rng, h, w, k, cols=None, one_per_colour=True):
    """k random distinct points, each stamped with a colour from cols (default distinct colours)."""
    pts = rng.sample([(r, c) for r in range(h) for c in range(w)], k)
    if cols is None:
        cols = colours(rng, k) if one_per_colour else [rng.choice(COLOURS) for _ in range(k)]
    return pts, cols


def _place_dots(g, pts, cols):
    for (r, c), col in zip(pts, cols):
        g[r][c] = col
    return g


def _far_apart(pts, min_d=3):
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            if abs(pts[i][0] - pts[j][0]) + abs(pts[i][1] - pts[j][1]) < min_d:
                return False
    return True


# 1 two dots of the same colour: draw the rectangle outline using them as opposite corners. ---------------
def gi_rect_outline_corners(rng):
    h, w = _dims(rng, 6, 16)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    r0, c0 = rng.randrange(h), rng.randrange(w)
    r1, c1 = rng.randrange(h), rng.randrange(w)
    if abs(r0 - r1) < 2 or abs(c0 - c1) < 2:
        return None
    g[r0][c0] = col; g[r1][c1] = col
    return g
def tf_rect_outline_corners(g):
    out = copy(g)
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 2:
        return None
    (r0, c0), (r1, c1) = pts
    col = g[r0][c0]
    r0, r1 = sorted((r0, r1)); c0, c1 = sorted((c0, c1))
    rect(out, r0, c0, r1, c1, col, fill=False)
    return out
rule("rect_outline_from_two_corner_dots", "Two dots of the same colour mark opposite corners of a rectangle whose outline is drawn in that colour.", gi_rect_outline_corners, tf_rect_outline_corners)


# 2 three dots: draw the triangle outline joining them with straight lines. -------------------------------
def gi_triangle_outline(rng):
    h, w = _dims(rng, 8, 18)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    pts = rng.sample([(r, c) for r in range(h) for c in range(w)], 3)
    if not _far_apart(pts, 4):
        return None
    _place_dots(g, pts, [col, col, col])
    return g
def tf_triangle_outline(g):
    out = copy(g)
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 3:
        return None
    col = g[pts[0][0]][pts[0][1]]
    _draw_line(out, pts[0], pts[1], col)
    _draw_line(out, pts[1], pts[2], col)
    _draw_line(out, pts[2], pts[0], col)
    return out
rule("triangle_outline_from_three_dots", "Three same-coloured dots are joined pairwise with straight lines to draw a triangle outline.", gi_triangle_outline, tf_triangle_outline)


# 3 dots numbered by colour (1,2,3,...) connected in colour order into a polyline. -------------------------
def gi_colour_order_polyline(rng):
    h, w = _dims(rng, 8, 18)
    g = blank(h, w)
    k = rng.randint(3, 5)
    pts, _ = _dots(rng, h, w, k)
    cols = list(range(1, k + 1))
    rng.shuffle(cols)
    if not _far_apart(pts, 3):
        return None
    _place_dots(g, pts, cols)
    return g
def tf_colour_order_polyline(g):
    out = copy(g)
    pts = cells(g, lambda v: v != 0)
    ordered = sorted(pts, key=lambda p: g[p[0]][p[1]])
    for i in range(len(ordered) - 1):
        _draw_line(out, ordered[i], ordered[i + 1], g[ordered[i][0]][ordered[i][1]])
    return out
rule("connect_dots_in_colour_order", "Dots are numbered by their colour value and joined in ascending colour order into a polyline.", gi_colour_order_polyline, tf_colour_order_polyline)


# 4 centre dot and a radius dot define a diamond (rotated square) outline. --------------------------------
def gi_diamond_from_radius(rng):
    h, w = _dims(rng, 10, 20)
    g = blank(h, w)
    cr, cc = rng.randint(4, h - 5), rng.randint(4, w - 5)
    radius = rng.randint(2, min(cr, cc, h - 1 - cr, w - 1 - cc))
    if radius < 2:
        return None
    rcol, dcol = colours(rng, 2)
    g[cr][cc] = rcol
    g[cr - radius][cc] = dcol
    return g
def tf_diamond_from_radius(g):
    out = copy(g)
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 2:
        return None
    centre = next(p for p in pts if cells(g, lambda v: v == g[p[0]][p[1]]).__len__() or True)
    # identify centre as the point whose colour is not on the axis-offset point
    c1, c2 = pts
    r = abs(c1[0] - c2[0]) + abs(c1[1] - c2[1])
    centre = c1 if (c1[0] == c2[0] or c1[1] == c2[1]) else None
    if centre is None:
        return None
    cr, cc = centre
    col = g[cr][cc]
    radius = max(abs(c2[0] - cr), abs(c2[1] - cc))
    tips = [(cr - radius, cc), (cr + radius, cc), (cr, cc - radius), (cr, cc + radius)]
    for i in range(4):
        _draw_line(out, tips[i], tips[(i + 1) % 4], col)
    return out
rule("diamond_from_centre_and_radius_dot", "A centre dot and a radius dot on its axis define a diamond whose outline is drawn in the centre dot's colour.", gi_diamond_from_radius, tf_diamond_from_radius)


# 5 four dots mark the corners of a rectangle which is drawn filled. --------------------------------------
def gi_rect_filled_four_dots(rng):
    h, w = _dims(rng, 8, 18)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    r0, r1 = sorted(rng.sample(range(h), 2))
    c0, c1 = sorted(rng.sample(range(w), 2))
    if r1 - r0 < 2 or c1 - c0 < 2:
        return None
    for r, c in [(r0, c0), (r0, c1), (r1, c0), (r1, c1)]:
        g[r][c] = col
    return g
def tf_rect_filled_four_dots(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 4:
        return None
    col = g[pts[0][0]][pts[0][1]]
    rs = [p[0] for p in pts]; cs = [p[1] for p in pts]
    out = copy(g)
    rect(out, min(rs), min(cs), max(rs), max(cs), col, fill=True)
    return out
rule("rect_filled_from_four_corner_dots", "Four dots of the same colour mark the corners of a rectangle which is drawn filled in that colour.", gi_rect_filled_four_dots, tf_rect_filled_four_dots)


# 6 a dot and an edge marker define a straight line to the edge. -------------------------------------------
def gi_dot_to_edge_marker(rng):
    h, w = _dims(rng, 8, 18)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    side = rng.choice(["top", "bottom", "left", "right"])
    if side in ("top", "bottom"):
        er = 0 if side == "top" else h - 1
        ec = rng.randrange(w)
        dr = rng.randint(2, h - 3) if h > 5 else None
        dc = ec
    else:
        ec = 0 if side == "left" else w - 1
        er = rng.randrange(h)
        dc = rng.randint(2, w - 3) if w > 5 else None
        dr = er
    if dr is None or dc is None:
        return None
    g[er][ec] = col
    g[dr][dc] = col
    return g if (er, ec) != (dr, dc) else None
def tf_dot_to_edge_marker(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 2:
        return None
    out = copy(g)
    col = g[pts[0][0]][pts[0][1]]
    _draw_line(out, pts[0], pts[1], col)
    return out
rule("line_from_dot_to_edge_marker", "A dot and a marker on the border, both the same colour, are joined by a straight line.", gi_dot_to_edge_marker, tf_dot_to_edge_marker)


# 7 parallel lines drawn vertically through every dot of one colour. ---------------------------------------
def gi_parallel_vlines(rng):
    h, w = _dims(rng, 8, 20)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    k = rng.randint(2, 5)
    cs = rng.sample(range(w), k)
    rs = [rng.randrange(h) for _ in cs]
    for r, c in zip(rs, cs):
        g[r][c] = col
    return g
def tf_parallel_vlines(g):
    out = copy(g)
    h, w = dims(g)
    for r, c in cells(g, lambda v: v != 0):
        col = g[r][c]
        for y in range(h):
            out[y][c] = col
    return out
rule("vertical_lines_through_each_dot", "Every dot of the colour grows into a full vertical line through its column.", gi_parallel_vlines, tf_parallel_vlines)


# 8 bounding rectangle outline of all dots of each colour. --------------------------------------------------
def gi_bbox_per_colour(rng):
    h, w = _dims(rng, 10, 22)
    g = blank(h, w)
    cols = colours(rng, rng.randint(2, 3))
    for col in cols:
        k = rng.randint(2, 4)
        pts = rng.sample([(r, c) for r in range(h) for c in range(w)], k)
        for r, c in pts:
            g[r][c] = col
    return g if len(cells(g, lambda v: v != 0)) >= 4 else None
def tf_bbox_per_colour(g):
    out = copy(g)
    for col in set(v for row in g for v in row if v):
        pts = cells(g, lambda v: v == col)
        rs = [p[0] for p in pts]; cs = [p[1] for p in pts]
        if max(rs) - min(rs) >= 1 and max(cs) - min(cs) >= 1:
            rect(out, min(rs), min(cs), max(rs), max(cs), col, fill=False)
    return out
rule("bounding_rect_of_each_colour_dots", "For each colour the bounding rectangle of its dots is outlined in that colour.", gi_bbox_per_colour, tf_bbox_per_colour)


# 9 midpoint between each pair of same-coloured dots is marked with a new fixed colour. -----------------
def gi_midpoint_pairs(rng):
    h, w = _dims(rng, 8, 18)
    g = blank(h, w)
    cols = colours(rng, rng.randint(2, 3))
    placed = 0
    for col in cols:
        r0, c0 = rng.randrange(h), rng.randrange(w)
        r1, c1 = rng.randrange(h), rng.randrange(w)
        if (r0 + r1) % 2 != 0 or (c0 + c1) % 2 != 0 or (r0, c0) == (r1, c1):
            continue
        g[r0][c0] = col; g[r1][c1] = col
        placed += 1
    return g if placed >= 2 else None
def tf_midpoint_pairs(g):
    out = copy(g)
    h, w = dims(g)
    mark = 8 if 8 not in set(v for row in g for v in row) else 9
    for col in set(v for row in g for v in row if v):
        pts = cells(g, lambda v: v == col)
        if len(pts) != 2:
            continue
        (r0, c0), (r1, c1) = pts
        mr, mc = (r0 + r1) // 2, (c0 + c1) // 2
        out[mr][mc] = mark
    return out
rule("midpoint_of_same_colour_pairs", "The midpoint of each same-coloured pair of dots is marked with a single fixed colour.", gi_midpoint_pairs, tf_midpoint_pairs)


# 10 perpendicular bisector line (axis-aligned approximation) between two dots. ------------------------------
def gi_perp_bisector(rng):
    h, w = _dims(rng, 8, 18)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    r0 = rng.randrange(h)
    r1 = rng.randrange(h)
    c = rng.randrange(w)
    if r0 == r1:
        return None
    g[r0][c] = col; g[r1][c] = col
    return g
def tf_perp_bisector(g):
    out = copy(g)
    h, w = dims(g)
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 2:
        return None
    col = g[pts[0][0]][pts[0][1]]
    (r0, c0), (r1, c1) = pts
    mr = (r0 + r1) // 2
    for x in range(w):
        out[mr][x] = col
    return out
rule("perpendicular_bisector_of_two_dots", "Two dots sharing a column are bisected by a horizontal line through their midpoint.", gi_perp_bisector, tf_perp_bisector)


# 11 a plus (cross) through each dot clipped to the grid frame. ----------------------------------------------
def gi_plus_through_dots(rng):
    h, w = _dims(rng, 8, 20)
    g = blank(h, w)
    k = rng.randint(1, 3)
    cols = colours(rng, k)
    pts = rng.sample([(r, c) for r in range(h) for c in range(w)], k)
    for (r, c), col in zip(pts, cols):
        g[r][c] = col
    return g
def tf_plus_through_dots(g):
    out = copy(g)
    h, w = dims(g)
    for r, c in cells(g, lambda v: v != 0):
        col = g[r][c]
        for x in range(w):
            out[r][x] = col
        for y in range(h):
            out[y][c] = col
    return out
rule("plus_cross_through_each_dot", "A plus-shaped cross is drawn through each dot, clipped to the grid's edges.", gi_plus_through_dots, tf_plus_through_dots)


# 12 concentric square rings around a dot, spaced up to the nearest other dot. -------------------------------
def gi_concentric_rings(rng):
    h, w = _dims(rng, 12, 22)
    g = blank(h, w)
    cr, cc = rng.randint(5, h - 6), rng.randint(5, w - 6)
    col = rng.choice(COLOURS)
    other_col = rng.choice([c for c in COLOURS if c != col])
    d = rng.randint(3, 4)
    g[cr][cc] = col
    g[cr][cc + d] = other_col
    return g
def tf_concentric_rings(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 2:
        return None
    (r0, c0), (r1, c1) = pts
    col = g[r0][c0]
    dist = max(abs(r0 - r1), abs(c0 - c1))
    out = copy(g)
    h, w = dims(g)
    for ring in range(1, dist):
        r_lo, r_hi, c_lo, c_hi = r0 - ring, r0 + ring, c0 - ring, c0 + ring
        if r_lo < 0 or r_hi >= h or c_lo < 0 or c_hi >= w:
            break
        rect(out, r_lo, c_lo, r_hi, c_hi, col, fill=False)
    return out
rule("concentric_rings_to_nearest_dot", "Concentric square rings are drawn around a dot, spaced one cell apart, out to the distance of the nearest other dot.", gi_concentric_rings, tf_concentric_rings)


# 13 a staircase path (unit steps) from one dot to another. --------------------------------------------------
def gi_staircase(rng):
    h, w = _dims(rng, 8, 20)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    r0, c0 = rng.randrange(h), rng.randrange(w)
    dr = rng.randint(2, min(6, h - 1))
    dc = rng.randint(2, min(6, w - 1))
    r1 = r0 + dr if r0 + dr < h else r0 - dr
    c1 = c0 + dc if c0 + dc < w else c0 - dc
    if r1 < 0 or c1 < 0:
        return None
    g[r0][c0] = col; g[r1][c1] = col
    return g
def tf_staircase(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 2:
        return None
    out = copy(g)
    (r0, c0), (r1, c1) = pts
    col = g[r0][c0]
    r, c = r0, c0
    sr = 1 if r1 > r0 else -1
    sc = 1 if c1 > c0 else -1
    while (r, c) != (r1, c1):
        out[r][c] = col
        if r != r1:
            r += sr; out[r][c] = col
        if c != c1:
            c += sc
    out[r1][c1] = col
    return out
rule("staircase_path_between_two_dots", "A staircase path of alternating single-cell vertical and horizontal steps is drawn from one dot to another.", gi_staircase, tf_staircase)


# 14 each dot joined to the nearest border point by a straight line. ------------------------------------------
def gi_dots_to_border(rng):
    h, w = _dims(rng, 10, 20)
    g = blank(h, w)
    k = rng.randint(1, 3)
    cols = colours(rng, k)
    pts = []
    tries = 0
    while len(pts) < k and tries < 100:
        tries += 1
        r, c = rng.randint(2, h - 3), rng.randint(2, w - 3)
        if (r, c) not in pts:
            pts.append((r, c))
    if len(pts) < k:
        return None
    for (r, c), col in zip(pts, cols):
        g[r][c] = col
    return g
def tf_dots_to_border(g):
    out = copy(g)
    h, w = dims(g)
    for r, c in cells(g, lambda v: v != 0):
        col = g[r][c]
        dists = [(r, (0, c)), (h - 1 - r, (h - 1, c)), (c, (r, 0)), (w - 1 - c, (r, w - 1))]
        _, target = min(dists, key=lambda x: x[0])
        _draw_line(out, (r, c), target, col)
    return out
rule("dot_joined_to_nearest_border_point", "Each dot is joined by a straight line to the nearest point on the grid's border.", gi_dots_to_border, tf_dots_to_border)


# 15 horizontal and vertical grid lines through every dot (full crosshatch). -----------------------------------
def gi_full_gridlines(rng):
    h, w = _dims(rng, 10, 22)
    g = blank(h, w)
    k = rng.randint(2, 4)
    col = rng.choice(COLOURS)
    pts = rng.sample([(r, c) for r in range(h) for c in range(w)], k)
    for r, c in pts:
        g[r][c] = col
    return g
def tf_full_gridlines(g):
    out = copy(g)
    h, w = dims(g)
    rs = {r for r, c in cells(g, lambda v: v != 0)}
    cs = {c for r, c in cells(g, lambda v: v != 0)}
    col = next(v for row in g for v in row if v)
    for r in rs:
        for x in range(w):
            out[r][x] = col
    for c in cs:
        for y in range(h):
            out[y][c] = col
    return out
rule("grid_lines_through_all_dots", "Horizontal and vertical lines are drawn through every dot's row and column, forming a crosshatch.", gi_full_gridlines, tf_full_gridlines)


# 16 two dots of different colours: draw an L-shaped (right-angle) path between them, elbow at the first's row. --
def gi_elbow_path(rng):
    h, w = _dims(rng, 8, 18)
    g = blank(h, w)
    col1, col2 = colours(rng, 2)
    r0, c0 = rng.randrange(h), rng.randrange(w)
    r1, c1 = rng.randrange(h), rng.randrange(w)
    if r0 == r1 or c0 == c1:
        return None
    g[r0][c0] = col1; g[r1][c1] = col2
    return g
def tf_elbow_path(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 2:
        return None
    out = copy(g)
    p0, p1 = pts
    col = g[p0[0]][p0[1]]
    elbow = (p0[0], p1[1])
    _draw_line(out, p0, elbow, col)
    _draw_line(out, elbow, p1, col)
    return out
rule("elbow_path_between_two_dots", "An L-shaped right-angle path, coloured with the first dot's colour, connects the two dots via a bend below the first.", gi_elbow_path, tf_elbow_path)


# 17 diagonal 'X' through the whole grid drawn from each of the four corner dots. ----------------------------
def gi_corner_dot_diagonals(rng):
    h, w = _dims(rng, 8, 20)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    corner = rng.choice([(0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)])
    g[corner[0]][corner[1]] = col
    return g
def tf_corner_dot_diagonals(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 1:
        return None
    out = copy(g)
    h, w = dims(g)
    r, c = pts[0]
    col = g[r][c]
    opp = (h - 1 - r, w - 1 - c)
    _draw_line(out, (r, c), opp, col)
    return out
# diagonal_from_corner_dot dropped 2026-10-12: same behaviour as corner_emitter_diagonal_straight_path (b032)
# 18 three dots: draw the triangle's filled interior (scanline fill) in a second colour. ----------------------
def gi_triangle_filled(rng):
    h, w = _dims(rng, 10, 20)
    g = blank(h, w)
    outline_col, fill_col = colours(rng, 2)
    pts = rng.sample([(r, c) for r in range(h) for c in range(w)], 3)
    rs = [p[0] for p in pts]
    if max(rs) - min(rs) < 4 or not _far_apart(pts, 4):
        return None
    _place_dots(g, pts, [outline_col] * 3)
    g[0][0] = fill_col if g[0][0] == 0 else g[0][0]
    return g if g[0][0] == fill_col else None
def tf_triangle_filled(g):
    pts = cells(g, lambda v: v == next((v for row in g for v in row if v), 0))
    all_pts = cells(g, lambda v: v != 0)
    fill_col = g[0][0]
    outline_pts = [p for p in all_pts if p != (0, 0)]
    if len(outline_pts) != 3:
        return None
    col = g[outline_pts[0][0]][outline_pts[0][1]]
    out = copy(g)
    out[0][0] = 0
    a, b, c = sorted(outline_pts)
    for row in range(a[0], c[0] + 1):
        xs = []
        for p, q in [(a, b), (b, c), (a, c)]:
            if p[0] == q[0]:
                continue
            lo, hi = sorted((p[0], q[0]))
            if lo <= row <= hi:
                t = (row - p[0]) / (q[0] - p[0])
                xs.append(p[1] + t * (q[1] - p[1]))
        if xs:
            x0, x1 = round(min(xs)), round(max(xs))
            for col_i in range(x0, x1 + 1):
                if out[row][col_i] == 0:
                    out[row][col_i] = fill_col
    for p, q in [(a, b), (b, c), (a, c)]:
        _draw_line(out, p, q, col)
    return out
rule("triangle_filled_from_three_dots", "Three dots define a triangle whose outline and interior are filled using the dot colour and a marker colour at the origin.", gi_triangle_filled, tf_triangle_filled)


# 19 pair of dots on the same row define a horizontal segment, repeated every k rows below (vertical fan). ----
def gi_repeat_segment_rows(rng):
    h, w = _dims(rng, 10, 20)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    r0 = rng.randint(0, 2)
    c0, c1 = sorted(rng.sample(range(w), 2))
    gap = rng.randint(2, 4)
    if r0 + gap * 2 >= h:
        return None
    g[r0][c0] = col; g[r0][c1] = col
    marker = rng.choice([c for c in COLOURS if c != col])
    g[h - 1][0] = marker
    return g
def tf_repeat_segment_rows(g):
    h, w = dims(g)
    out = copy(g)
    marker_r = h - 1
    marker_col = g[marker_r][0]
    row_pts = cells(g, lambda v: v != 0 and v != marker_col)
    if len(row_pts) != 2 or row_pts[0][0] != row_pts[1][0]:
        return None
    r0, c0 = row_pts[0]; _, c1 = row_pts[1]
    col = g[r0][c0]
    gap = 2
    r = r0 + gap
    while r < marker_r:
        out[r][c0] = col; out[r][c1] = col
        r += gap
    return out
rule("segment_repeated_down_at_fixed_gap", "A horizontal segment between two dots is repeated downward at a fixed row gap, stopping at a marker row.", gi_repeat_segment_rows, tf_repeat_segment_rows)


# 20 two dots: draw a rectangle outline AND mark its centre with a third fixed colour. -------------------------
def gi_rect_outline_with_centre(rng):
    h, w = _dims(rng, 8, 18)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    r0, r1 = sorted(rng.sample(range(h), 2))
    c0, c1 = sorted(rng.sample(range(w), 2))
    if r1 - r0 < 3 or c1 - c0 < 3:
        return None
    g[r0][c0] = col; g[r1][c1] = col
    return g
def tf_rect_outline_with_centre(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 2:
        return None
    (r0, c0), (r1, c1) = pts
    col = g[r0][c0]
    r0s, r1s = sorted((r0, r1)); c0s, c1s = sorted((c0, c1))
    out = copy(g)
    rect(out, r0s, c0s, r1s, c1s, col, fill=False)
    mr, mc = (r0s + r1s) // 2, (c0s + c1s) // 2
    mark = 5 if col != 5 else 6
    out[mr][mc] = mark
    return out
rule("rect_outline_with_marked_centre", "Two dots define a rectangle whose outline is drawn, and its exact centre cell is marked with a fixed colour.", gi_rect_outline_with_centre, tf_rect_outline_with_centre)


# 21 dots of one colour joined to the single dot of another colour, star shape. ---------------------------------
def gi_star_to_hub(rng):
    h, w = _dims(rng, 10, 22)
    g = blank(h, w)
    hub_col, spoke_col = colours(rng, 2)
    hr, hc = rng.randint(3, h - 4), rng.randint(3, w - 4)
    g[hr][hc] = hub_col
    k = rng.randint(2, 4)
    pts = rng.sample([(r, c) for r in range(h) for c in range(w) if (r, c) != (hr, hc)], k)
    for r, c in pts:
        g[r][c] = spoke_col
    return g
def tf_star_to_hub(g):
    out = copy(g)
    hub_pts = cells(g, lambda v: v != 0)
    counts_ = counts(g)
    cols_by_count = sorted(((v, k) for k, v in counts_.items() if k != 0), key=lambda x: x[0])
    if len(cols_by_count) != 2:
        return None
    hub_col = cols_by_count[0][1]
    hub = next(p for p in hub_pts if g[p[0]][p[1]] == hub_col)
    spokes = [p for p in hub_pts if g[p[0]][p[1]] != hub_col]
    for p in spokes:
        _draw_line(out, hub, p, g[p[0]][p[1]])
    return out
rule("spokes_from_hub_dot_to_each_point", "Several dots of one colour are each joined by a straight spoke to the single hub dot of another colour.", gi_star_to_hub, tf_star_to_hub)


# 22 two dots on the same column: draw a vertical ladder (rungs every 2 rows) between them. ----------------------
def gi_ladder(rng):
    h, w = _dims(rng, 10, 20)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    c = rng.randrange(w)
    r0, r1 = sorted(rng.sample(range(h), 2))
    if r1 - r0 < 4 or c + 1 >= w:
        return None
    g[r0][c] = col; g[r1][c] = col
    return g
def tf_ladder(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 2 or pts[0][1] != pts[1][1]:
        return None
    out = copy(g)
    (r0, c), (r1, _) = sorted(pts)
    col = g[r0][c]
    for r in range(r0, r1 + 1):
        out[r][c] = col
    for r in range(r0, r1 + 1, 2):
        if c + 1 < len(g[0]):
            out[r][c + 1] = col
    return out
rule("ladder_between_two_column_dots", "Two dots sharing a column are joined by a vertical rail with rungs sticking out every other row.", gi_ladder, tf_ladder)


# 23 all dots of one colour: draw the convex hull edges connecting the extreme points (axis-aligned diamond hull).
def gi_hull_extremes(rng):
    h, w = _dims(rng, 12, 24)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    k = rng.randint(4, 6)
    pts = rng.sample([(r, c) for r in range(h) for c in range(w)], k)
    for r, c in pts:
        g[r][c] = col
    return g
def tf_hull_extremes(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) < 4:
        return None
    col = g[pts[0][0]][pts[0][1]]
    top = min(pts, key=lambda p: p[0])
    bottom = max(pts, key=lambda p: p[0])
    left = min(pts, key=lambda p: p[1])
    right = max(pts, key=lambda p: p[1])
    out = copy(g)
    for p, q in [(top, right), (right, bottom), (bottom, left), (left, top)]:
        if p != q:
            _draw_line(out, p, q, col)
    return out
rule("extreme_points_hull_quad", "The topmost, bottommost, leftmost and rightmost dots of a colour are joined in order into a hull outline.", gi_hull_extremes, tf_hull_extremes)


# 24 dot plus a number-coded dot (digit colour = length) draws a ray of that length rightward. -------------------
def gi_ray_length_coded(rng):
    h, w = _dims(rng, 8, 20)
    g = blank(h, w)
    length = rng.randint(2, min(8, w - 2))
    r = rng.randrange(h)
    c = rng.randint(0, w - length - 1)
    g[r][c] = length
    return g
def tf_ray_length_coded(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 1:
        return None
    r, c = pts[0]
    length = g[r][c]
    out = copy(g)
    w = len(g[0])
    for x in range(c, min(c + length, w)):
        out[r][x] = length
    return out
rule("ray_drawn_with_length_equal_to_colour", "A single dot's colour value is its length in cells: a ray of that many cells is drawn rightward from it.", gi_ray_length_coded, tf_ray_length_coded, digits=True)


# 25 two dots of the same colour on the border: connect with a line that bends at the grid's centre row. ---------
def gi_border_to_border_bend(rng):
    h, w = _dims(rng, 10, 20)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    c0 = rng.randrange(w)
    c1 = rng.randrange(w)
    if c0 == c1:
        return None
    g[0][c0] = col
    g[h - 1][c1] = col
    return g
def tf_border_to_border_bend(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 2:
        return None
    out = copy(g)
    h, w = dims(g)
    col = g[pts[0][0]][pts[0][1]]
    p0, p1 = pts
    mid_r = h // 2
    bend0 = (mid_r, p0[1])
    bend1 = (mid_r, p1[1])
    _draw_line(out, p0, bend0, col)
    _draw_line(out, bend0, bend1, col)
    _draw_line(out, bend1, p1, col)
    return out
rule("border_dots_joined_via_centre_bend", "Two dots on the top and bottom edges are joined by a path that runs straight down, bends at the middle row, and continues to the target.", gi_border_to_border_bend, tf_border_to_border_bend)


# 26 three collinear-free dots: draw the circle... approximated as an axis-aligned octagon ring around centroid. --
def gi_centroid_ring(rng):
    h, w = _dims(rng, 12, 22)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    pts = rng.sample([(r, c) for r in range(5, h - 5) for c in range(5, w - 5)], 3)
    if not _far_apart(pts, 4):
        return None
    _place_dots(g, pts, [col] * 3)
    return g
def tf_centroid_ring(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 3:
        return None
    col = g[pts[0][0]][pts[0][1]]
    cr = sum(p[0] for p in pts) // 3
    cc = sum(p[1] for p in pts) // 3
    radius = max(abs(p[0] - cr) + abs(p[1] - cc) for p in pts) // 2 + 1
    out = copy(g)
    h, w = dims(g)
    r0, r1, c0, c1 = cr - radius, cr + radius, cc - radius, cc + radius
    if r0 < 0 or r1 >= h or c0 < 0 or c1 >= w:
        return None
    rect(out, r0, c0, r1, c1, col, fill=False)
    return out
rule("ring_around_centroid_of_three_dots", "Three dots define a centroid; a square ring is drawn around it sized to roughly enclose all three.", gi_centroid_ring, tf_centroid_ring)


# 27 parallel diagonal lines through every dot of one colour (45 degree). -----------------------------------------
def gi_parallel_diagonals(rng):
    h, w = _dims(rng, 10, 22)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    k = rng.randint(2, 4)
    pts = rng.sample([(r, c) for r in range(h) for c in range(w)], k)
    diffs = {r - c for r, c in pts}
    if len(diffs) != k:
        return None
    for r, c in pts:
        g[r][c] = col
    return g
def tf_parallel_diagonals(g):
    out = copy(g)
    h, w = dims(g)
    for r0, c0 in cells(g, lambda v: v != 0):
        col = g[r0][c0]
        k = r0 - c0
        for r in range(h):
            c = r - k
            if 0 <= c < w:
                out[r][c] = col
    return out
rule("diagonal_lines_through_each_dot", "Every dot grows into a full 45 degree diagonal line passing through it.", gi_parallel_diagonals, tf_parallel_diagonals)


# 28 dots numbered by colour connected pairwise ascending to form nested rectangles (telescoping). ------------------
def gi_telescope_rects(rng):
    h, w = _dims(rng, 14, 24)
    g = blank(h, w)
    k = rng.randint(2, 3)
    cols = sorted(colours(rng, k))
    cr, cc = h // 2, w // 2
    used = set()
    for i, col in enumerate(cols):
        d = (i + 1) * 2
        if cr - d < 0 or cr + d >= h or cc - d < 0 or cc + d >= w:
            return None
        g[cr - d][cc - d] = col
        g[cr + d][cc + d] = col
    return g
def tf_telescope_rects(g):
    out = copy(g)
    cols = sorted(set(v for row in g for v in row if v))
    for col in cols:
        pts = cells(g, lambda v: v == col)
        if len(pts) != 2:
            continue
        (r0, c0), (r1, c1) = pts
        r0s, r1s = sorted((r0, r1)); c0s, c1s = sorted((c0, c1))
        rect(out, r0s, c0s, r1s, c1s, col, fill=False)
    return out
rule("telescoping_rects_by_colour_order", "Each colour's pair of dots defines a rectangle outline; drawn together they nest like a telescope.", gi_telescope_rects, tf_telescope_rects)


# 29 one dot defines an arrow: a second small marker dot nearby gives the direction to extend a ray to the edge. ---
def gi_arrow_direction_ray(rng):
    h, w = _dims(rng, 10, 20)
    g = blank(h, w)
    col, dir_col = colours(rng, 2)
    r, c = rng.randint(3, h - 4), rng.randint(3, w - 4)
    dr, dc = rng.choice([(-1, 0), (1, 0), (0, -1), (0, 1)])
    g[r][c] = col
    g[r + dr][c + dc] = dir_col
    return g
def tf_arrow_direction_ray(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 2:
        return None
    counts_ = counts(g)
    cols_sorted = sorted((v for k, v in counts_.items() if k != 0))
    base = next(p for p in pts if cells(g, lambda v: v == g[p[0]][p[1]]))
    (r0, c0), (r1, c1) = pts
    col0 = g[r0][c0]
    dr, dc = r1 - r0, c1 - c0
    out = copy(g)
    h, w = dims(g)
    r, c = r1, c1
    while 0 <= r < h and 0 <= c < w:
        out[r][c] = col0
        r += dr; c += dc
    return out
rule("arrow_marker_extends_ray_to_edge", "A dot with an adjacent direction marker shoots a ray in that direction out to the grid's edge, in the dot's own colour.", gi_arrow_direction_ray, tf_arrow_direction_ray)


# 30 every pair of same-coloured dots on the grid gets the shorter of the two axis lines drawn between them. --------
def gi_shortest_axis_connect(rng):
    h, w = _dims(rng, 10, 20)
    g = blank(h, w)
    cols = colours(rng, rng.randint(2, 3))
    placed = 0
    for col in cols:
        r0, c0 = rng.randrange(h), rng.randrange(w)
        r1, c1 = rng.randrange(h), rng.randrange(w)
        if (r0, c0) == (r1, c1):
            continue
        g[r0][c0] = col; g[r1][c1] = col
        placed += 1
    return g if placed >= 2 else None
def tf_shortest_axis_connect(g):
    out = copy(g)
    for col in set(v for row in g for v in row if v):
        pts = cells(g, lambda v: v == col)
        if len(pts) != 2:
            continue
        (r0, c0), (r1, c1) = pts
        _draw_line(out, (r0, c0), (r1, c1), col)
    return out
rule("straight_line_between_same_colour_pairs", "Every pair of dots sharing a colour is joined by the Bresenham straight line between them.", gi_shortest_axis_connect, tf_shortest_axis_connect)


# 31 a dot and a frame marker: draw a rectangle whose outline passes through the frame markers, dot as centre. ------
def gi_frame_markers_rect(rng):
    h, w = _dims(rng, 12, 22)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    cr, cc = h // 2, w // 2
    dr = rng.randint(2, min(cr, h - 1 - cr))
    dc = rng.randint(2, min(cc, w - 1 - cc))
    g[cr][cc] = col
    g[cr - dr][cc - dc] = col
    return g
def tf_frame_markers_rect(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 2:
        return None
    col = g[pts[0][0]][pts[0][1]]
    (r0, c0), (r1, c1) = pts
    cr, cc = r0, c0
    dr, dc = abs(r1 - r0), abs(c1 - c0)
    out = copy(g)
    rect(out, cr - dr, cc - dc, cr + dr, cc + dc, col, fill=False)
    return out
rule("rect_outline_centred_on_dot", "A centre dot and an offset marker define a rectangle outline symmetric around the centre dot.", gi_frame_markers_rect, tf_frame_markers_rect)


# 32 all dots of one colour: fan of lines from the leftmost dot to every other dot of that colour. -------------------
def gi_fan_from_leftmost(rng):
    h, w = _dims(rng, 10, 22)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    k = rng.randint(3, 5)
    pts = rng.sample([(r, c) for r in range(h) for c in range(w)], k)
    for r, c in pts:
        g[r][c] = col
    return g
def tf_fan_from_leftmost(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) < 3:
        return None
    col = g[pts[0][0]][pts[0][1]]
    hub = min(pts, key=lambda p: (p[1], p[0]))
    out = copy(g)
    for p in pts:
        if p != hub:
            _draw_line(out, hub, p, col)
    return out
rule("fan_of_lines_from_leftmost_dot", "Every dot of a colour is joined by a straight line back to the leftmost dot of that colour, forming a fan.", gi_fan_from_leftmost, tf_fan_from_leftmost)


# 33 two dots define a right triangle: the outline uses the axis-aligned legs plus the hypotenuse. --------------------
def gi_right_triangle_legs(rng):
    h, w = _dims(rng, 10, 20)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    r0, c0 = rng.randrange(h), rng.randrange(w)
    r1, c1 = rng.randrange(h), rng.randrange(w)
    if abs(r0 - r1) < 2 or abs(c0 - c1) < 2:
        return None
    g[r0][c0] = col; g[r1][c1] = col
    return g
def tf_right_triangle_legs(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 2:
        return None
    (r0, c0), (r1, c1) = pts
    col = g[r0][c0]
    corner = (r0, c1)
    out = copy(g)
    _draw_line(out, (r0, c0), corner, col)
    _draw_line(out, corner, (r1, c1), col)
    _draw_line(out, (r1, c1), (r0, c0), col)
    return out
rule("right_triangle_from_two_dots", "Two dots are the ends of a right triangle's hypotenuse; its two axis-aligned legs plus the hypotenuse are drawn.", gi_right_triangle_legs, tf_right_triangle_legs)


# 34 the outline of the regular octagon-approximation square rotated 45 around a single dot, sized by a second. --------
def gi_rotated_square_radius(rng):
    h, w = _dims(rng, 14, 24)
    g = blank(h, w)
    col, rcol = colours(rng, 2)
    cr, cc = h // 2, w // 2
    radius = rng.randint(3, min(cr, cc, h - 1 - cr, w - 1 - cc) - 1)
    if radius < 2:
        return None
    g[cr][cc] = col
    g[cr][cc + radius] = rcol
    return g
def tf_rotated_square_radius(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 2:
        return None
    (r0, c0), (r1, c1) = pts
    col = g[r0][c0]
    radius = max(abs(r1 - r0), abs(c1 - c0))
    out = copy(g)
    corners = [(r0 - radius, c0), (r0, c0 + radius), (r0 + radius, c0), (r0, c0 - radius)]
    for i in range(4):
        _draw_line(out, corners[i], corners[(i + 1) % 4], col)
    return out
rule("rotated_square_from_dot_and_radius", "A centre dot and a radius marker define a 45 degree rotated square (diamond) outline.", gi_rotated_square_radius, tf_rotated_square_radius)


# 35 two vertically stacked dots of the same colour: draw a zigzag connecting them via the grid's quarter columns. ----
def gi_zigzag_quarters(rng):
    h, w = _dims(rng, 14, 24)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    c0 = w // 4
    c1 = 3 * w // 4
    r0 = rng.randint(0, h // 3)
    r1 = rng.randint(2 * h // 3, h - 1)
    if r1 <= r0 + 2:
        return None
    g[r0][c0] = col; g[r1][c1] = col
    return g
def tf_zigzag_quarters(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 2:
        return None
    (r0, c0), (r1, c1) = pts
    col = g[r0][c0]
    mid_r = (r0 + r1) // 2
    out = copy(g)
    _draw_line(out, (r0, c0), (mid_r, c0), col)
    _draw_line(out, (mid_r, c0), (mid_r, c1), col)
    _draw_line(out, (mid_r, c1), (r1, c1), col)
    return out
rule("zigzag_path_between_two_dots", "Two dots are joined by a zigzag path: down, across, then down again, in their shared colour.", gi_zigzag_quarters, tf_zigzag_quarters)


# 36 each dot of a colour gets a small plus mark (radius 1) instead of growing lines: distinguishes density. ----------
def gi_small_plus_marks(rng):
    h, w = _dims(rng, 10, 22)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    k = rng.randint(2, 5)
    pts = []
    tries = 0
    while len(pts) < k and tries < 100:
        tries += 1
        r, c = rng.randint(1, h - 2), rng.randint(1, w - 2)
        if (r, c) not in pts:
            pts.append((r, c))
    if len(pts) < k:
        return None
    for r, c in pts:
        g[r][c] = col
    return g
def tf_small_plus_marks(g):
    out = copy(g)
    h, w = dims(g)
    for r, c in cells(g, lambda v: v != 0):
        col = g[r][c]
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w:
                out[nr][nc] = col
    return out
rule("small_plus_marks_on_each_dot", "Each dot grows a small plus mark into its four immediate neighbours.", gi_small_plus_marks, tf_small_plus_marks)


# 37 two dots of different colours: draw the line between them, coloured by alternating the two colours. -------------
def gi_alternating_colour_line(rng):
    h, w = _dims(rng, 10, 20)
    g = blank(h, w)
    col1, col2 = colours(rng, 2)
    r0, c0 = rng.randrange(h), rng.randrange(w)
    r1, c1 = rng.randrange(h), rng.randrange(w)
    if (r0, c0) == (r1, c1):
        return None
    g[r0][c0] = col1; g[r1][c1] = col2
    return g
def tf_alternating_colour_line(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 2:
        return None
    p0, p1 = pts
    col1, col2 = g[p0[0]][p0[1]], g[p1[0]][p1[1]]
    line = _bresenham(p0[0], p0[1], p1[0], p1[1])
    out = copy(g)
    for i, (r, c) in enumerate(line):
        out[r][c] = col1 if i % 2 == 0 else col2
    return out
rule("line_coloured_alternating_endpoints", "A straight line is drawn between two differently coloured dots, its cells alternating between the two colours.", gi_alternating_colour_line, tf_alternating_colour_line)


# 38 dots along a diagonal get a chevron/arrow shape at each, pointing towards the grid centre. ------------------------
def gi_chevrons_toward_centre(rng):
    h, w = _dims(rng, 14, 24)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    k = rng.randint(2, 4)
    margin = 2
    pts = []
    tries = 0
    while len(pts) < k and tries < 100:
        tries += 1
        r, c = rng.randint(margin, h - 1 - margin), rng.randint(margin, w - 1 - margin)
        if (r, c) not in pts:
            pts.append((r, c))
    if len(pts) < k:
        return None
    for r, c in pts:
        g[r][c] = col
    return g
def tf_chevrons_toward_centre(g):
    out = copy(g)
    h, w = dims(g)
    cr, cc = h // 2, w // 2
    for r, c in cells(g, lambda v: v != 0):
        col = g[r][c]
        dr = 1 if cr > r else -1 if cr < r else 0
        dc = 1 if cc > c else -1 if cc < c else 0
        for off_r, off_c in [(dr, 0), (0, dc)]:
            nr, nc = r + off_r, c + off_c
            if 0 <= nr < h and 0 <= nc < w:
                out[nr][nc] = col
    return out
rule("chevron_mark_toward_grid_centre", "Each dot grows a two-cell chevron mark pointing toward the centre of the grid.", gi_chevrons_toward_centre, tf_chevrons_toward_centre)


# 39 two same-row dots draw the segment, then a copy of the segment is stamped directly below (mirrored gap). -------
def gi_segment_stamped_below(rng):
    h, w = _dims(rng, 10, 20)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    r = rng.randint(0, h // 2 - 2)
    c0, c1 = sorted(rng.sample(range(w), 2))
    gap = rng.randint(3, h // 2)
    if r + gap >= h:
        return None
    g[r][c0] = col; g[r][c1] = col
    return g
def tf_segment_stamped_below(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 2 or pts[0][0] != pts[1][0]:
        return None
    out = copy(g)
    r = pts[0][0]
    c0, c1 = sorted(p[1] for p in pts)
    col = g[r][c0]
    for c in range(c0, c1 + 1):
        out[r][c] = col
    h = len(g)
    gap = max(3, h // 2 - r)
    r2 = r + gap
    if r2 < h:
        for c in range(c0, c1 + 1):
            out[r2][c] = col
    return out
rule("segment_drawn_then_stamped_below", "Two same-row dots define a filled segment, which is copied straight down at a fixed gap.", gi_segment_stamped_below, tf_segment_stamped_below)


# 40 N dots of one colour sorted by row: consecutive ones joined by straight lines forming an open polyline path. ------
def gi_sorted_polyline(rng):
    h, w = _dims(rng, 12, 24)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    k = rng.randint(4, 6)
    pts = rng.sample([(r, c) for r in range(h) for c in range(w)], k)
    if not _far_apart(pts, 3):
        return None
    for r, c in pts:
        g[r][c] = col
    return g
def tf_sorted_polyline(g):
    pts = cells(g, lambda v: v != 0)
    if len(pts) < 3:
        return None
    col = g[pts[0][0]][pts[0][1]]
    ordered = sorted(pts, key=lambda p: (p[0], p[1]))
    out = copy(g)
    for i in range(len(ordered) - 1):
        _draw_line(out, ordered[i], ordered[i + 1], col)
    return out
rule("polyline_through_dots_sorted_by_row", "Dots of one colour, sorted top to bottom, are joined in order into an open polyline.", gi_sorted_polyline, tf_sorted_polyline)
