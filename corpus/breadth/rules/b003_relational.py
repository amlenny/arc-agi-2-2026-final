# b003_relational.py -- RELATIONAL / LINES / KEYS: projection to walls, rays from markers, connections to the
# nearest object, L-paths, gap filling, legends and separators, border markers, arrows and trails,
# enclosure, nearest-object colouring, bridges.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

D4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def _in(g, r, c):
    return 0 <= r < len(g) and 0 <= c < len(g[0])


def _ray(out, r, c, dr, dc, col, bg=0):
    """Paint bg cells beyond (r,c) along (dr,dc) until a non-bg cell or the edge; return the blocker or None."""
    r += dr; c += dc
    while _in(out, r, c) and out[r][c] == bg:
        out[r][c] = col; r += dr; c += dc
    return (r, c) if _in(out, r, c) else None


def _first_hit(g, r, c, dr, dc, bg=0):
    r += dr; c += dc
    while _in(g, r, c) and g[r][c] == bg:
        r += dr; c += dc
    return (r, c) if _in(g, r, c) else None


def _scatter(rng, g, k, cols, margin=1, rows=None, cols_=None):
    """k single cells with `margin` empty around each; returns [(r, c, colour)] or None."""
    H, W = dims(g); out = []
    rows = rows or range(H); cols_ = cols_ or range(W)
    for i in range(k):
        for _ in range(100):
            r, c = rng.choice(list(rows)), rng.choice(list(cols_))
            if all(g[y][x] == 0 for y in range(r - margin, r + margin + 1) for x in range(c - margin, c + margin + 1) if _in(g, y, x)):
                g[r][c] = cols[i]; out.append((r, c, cols[i])); break
        else:
            return None
    return out


def _rect_shape(h, w):
    return [(r, c) for r in range(h) for c in range(w)]


def _rects(rng, g, k, cols, lo=2, hi=4, margin=1):
    shapes = [_rect_shape(rng.randint(lo, hi), rng.randint(lo, hi)) for _ in range(k)]
    pos = place_shapes(rng, g, shapes, cols, margin=margin)
    if pos is None: return None
    return [(r0, c0, r0 + max(r for r, _ in sh), c0 + max(c for _, c in sh), col) for (r0, c0), sh, col in zip(pos, shapes, cols)]


def _outside(g, wall):
    """Cells reachable from the border without crossing colour `wall`."""
    H, W = dims(g); seen = set(); st = [(r, c) for r in range(H) for c in range(W) if (r in (0, H - 1) or c in (0, W - 1)) and g[r][c] != wall]
    seen |= set(st)
    while st:
        y, x = st.pop()
        for dy, dx in D4:
            n = (y + dy, x + dx)
            if _in(g, *n) and n not in seen and g[n[0]][n[1]] != wall:
                seen.add(n); st.append(n)
    return seen


def _frame(rng, g, col, lo=4, hi=8, margin=1):
    """A hollow rectangle (outer size lo..hi) placed with margin; returns (r0,c0,r1,c1) or None."""
    H, W = dims(g)
    for _ in range(60):
        h, w = rng.randint(lo, hi), rng.randint(lo, hi)
        if h > H or w > W: continue
        r0, c0 = rng.randint(0, H - h), rng.randint(0, W - w); r1, c1 = r0 + h - 1, c0 + w - 1
        if all(g[y][x] == 0 for y in range(r0 - margin, r1 + margin + 1) for x in range(c0 - margin, c1 + margin + 1) if _in(g, y, x)):
            rect(g, r0, c0, r1, c1, col, fill=False); return r0, c0, r1, c1
    return None


# 1 each lone cell projects a line to its nearest wall
def gi_nearest_wall(rng):
    h, w = size(rng, 6, 16); g = blank(h, w)
    return g if _scatter(rng, g, rng.randint(2, 6), [rng.choice(COLOURS) for _ in range(6)], margin=1) else None
def tf_nearest_wall(g):
    H, W = dims(g); out = copy(g)
    for r, c in cells(g, lambda v: v != 0):
        d = [(r, (-1, 0)), (H - 1 - r, (1, 0)), (c, (0, -1)), (W - 1 - c, (0, 1))]; d.sort(key=lambda t: t[0])
        if d[0][0] == d[1][0]: return None
        _ray(out, r, c, *d[0][1], g[r][c])
    return out
rule("project_cell_to_nearest_wall", "Each lone cell draws a line of its colour to the nearest grid edge.", gi_nearest_wall, tf_nearest_wall)


# 2 markers shoot rightwards until a wall segment or the edge
def gi_ray_right(rng):
    h, w = size(rng, 6, 16); g = blank(h, w); a, b = colours(rng, 2)
    for _ in range(rng.randint(1, 3)):
        c = rng.randint(2, w - 1); r0 = rng.randint(0, h - 2); r1 = rng.randint(r0 + 1, min(h - 1, r0 + 6))
        for r in range(r0, r1 + 1): g[r][c] = b
    pts = _scatter(rng, g, rng.randint(2, 5), [a] * 5, margin=0, cols_=range(0, w - 2))
    return g if pts else None
def tf_ray_right(g):
    out = copy(g); cnt = counts(g)
    vals = [c for c in cnt if c]; walls = [c for c in vals if any(len(o) >= 2 for o in components(g, c))]
    marker = [c for c in vals if c not in walls]
    if len(marker) != 1: return None
    for r, c in cells(g, lambda v: v == marker[0]): _ray(out, r, c, 0, 1, marker[0])
    return out
rule("markers_shoot_right_until_wall", "Every single-cell marker extends rightwards in its colour until it meets a wall segment or the edge.", gi_ray_right, tf_ray_right)


# 3 one marker shoots in all four directions until an obstacle
def gi_ray4(rng):
    h, w = size(rng, 7, 16); g = blank(h, w); a, b = colours(rng, 2); k = rng.randint(2, 5)
    if place_shapes(rng, g, [random_shape(rng, rng.randint(2, 6)) for _ in range(k)], [b] * k, margin=1) is None: return None
    return g if _scatter(rng, g, 1, [a], margin=1) else None
def tf_ray4(g):
    out = copy(g); cnt = counts(g); m = [c for c in cnt if c and cnt[c] == 1]
    if len(m) != 1: return None
    (r, c), = cells(g, lambda v: v == m[0])
    for dr, dc in D4: _ray(out, r, c, dr, dc, m[0])
    return out
rule("single_marker_rays_four_ways", "The lone single cell shoots rays of its colour up, down, left and right until each hits an object or the edge.", gi_ray4, tf_ray4)


# 4 marker connects by a straight line to its nearest object
def _aligned_markers(rng, g, rects, a, k, gap_lo=2, gap_hi=6):
    H, W = dims(g); pts = []
    for _ in range(k):
        for _ in range(40):
            r0, c0, r1, c1, _ = rng.choice(rects); d = rng.randint(gap_lo, gap_hi); side = rng.randrange(4)
            r, c = [(rng.randint(r0, r1), c0 - d), (rng.randint(r0, r1), c1 + d), (r0 - d, rng.randint(c0, c1)), (r1 + d, rng.randint(c0, c1))][side]
            dr, dc = [(0, 1), (0, -1), (1, 0), (-1, 0)][side]
            if not _in(g, r, c) or any(g[y][x] != 0 for y in range(r - 1, r + 2) for x in range(c - 1, c + 2) if _in(g, y, x)): continue
            if all(g[r + i * dr][c + i * dc] == 0 for i in range(1, d)):
                g[r][c] = a; pts.append((r, c)); break
        else:
            return None
    return pts
def gi_connect_nearest(rng):
    h, w = size(rng, 8, 18); g = blank(h, w); a, b = colours(rng, 2)
    rects = _rects(rng, g, rng.randint(1, 3), [b] * 3, 2, 4, margin=2)
    if rects is None: return None
    return g if _aligned_markers(rng, g, rects, a, rng.randint(1, 3)) else None
def _nearest_obj_cell(g, r, c, skip):
    best = [(abs(y - r) + abs(x - c), y, x) for y, x in cells(g, lambda v: v != 0 and v != skip)]
    best.sort()
    return best[0] if best else None
def tf_connect_nearest(g):
    out = copy(g); cnt = counts(g); m = [c for c in cnt if c and all(len(o) == 1 for o in components(g, c))]
    if len(m) != 1: return None
    for r, c in cells(g, lambda v: v == m[0]):
        n = _nearest_obj_cell(g, r, c, m[0])
        if n is None or (n[1] != r and n[2] != c): return None
        dr, dc = (0, 1 if n[2] > c else -1) if n[1] == r else (1 if n[1] > r else -1, 0)
        _ray(out, r, c, dr, dc, m[0])
    return out
rule("marker_connects_to_nearest_object", "Each single-cell marker draws a straight line of its colour to the nearest object.", gi_connect_nearest, tf_connect_nearest)


# 5 pairs joined by an L: horizontal from the upper cell, then vertical down
def gi_lpairs(rng):
    h, w = size(rng, 7, 16); g = blank(h, w); k = rng.randint(1, 3); cols = colours(rng, k); taken_r, taken_c = set(), set()
    for col in cols:
        for _ in range(40):
            r1, r2 = rng.sample(range(h), 2); c1, c2 = rng.sample(range(w), 2)
            if {r1, r2} & taken_r or {c1, c2} & taken_c: continue
            taken_r |= {r1, r2}; taken_c |= {c1, c2}; g[r1][c1] = col; g[r2][c2] = col; break
        else:
            return None
    return g
def tf_lpairs(g):
    out = copy(g)
    for col in sorted(set(v for row in g for v in row if v)):
        pts = sorted(cells(g, lambda v: v == col))
        if len(pts) != 2: return None
        (r1, c1), (r2, c2) = pts
        for x in range(min(c1, c2), max(c1, c2) + 1):
            if out[r1][x] == 0: out[r1][x] = col
        for y in range(r1, r2 + 1):
            if out[y][c2] == 0: out[y][c2] = col
    return out
rule("pairs_joined_by_l_path", "Two cells of the same colour are joined by an L: a horizontal run from the upper cell, then a vertical run down to the lower cell.", gi_lpairs, tf_lpairs)


# 6 dashed lines get their gaps filled
def gi_dashed(rng):
    h, w = size(rng, 6, 16); g = blank(h, w); k = rng.randint(1, 3); cols = colours(rng, k); used = set()
    for col in cols:
        for _ in range(40):
            horiz = rng.random() < 0.5; L = rng.randint(4, (w if horiz else h))
            if horiz: r = rng.randrange(h); a = rng.randint(0, w - L); seg = [(r, a + i) for i in range(L)]
            else: c = rng.randrange(w); a = rng.randint(0, h - L); seg = [(a + i, c) for i in range(L)]
            foot = {(y + dy, x + dx) for y, x in seg for dy in (-1, 0, 1) for dx in (-1, 0, 1)}
            if foot & used: continue
            used |= set(seg); keep = [seg[0], seg[-1]] + [p for p in seg[1:-1] if rng.random() < 0.5]
            if len(keep) == L: keep = keep[:-2] + [seg[-1]]
            for y, x in keep: g[y][x] = col
            break
        else:
            return None
    return g
def tf_dashed(g):
    out = copy(g)
    for col in set(v for row in g for v in row if v):
        pts = cells(g, lambda v: v == col); rs = {r for r, _ in pts}; cs = {c for _, c in pts}
        if len(rs) == 1: r = rs.pop(); [out[r].__setitem__(x, col) for x in range(min(cs), max(cs) + 1)]
        elif len(cs) == 1: c = cs.pop(); [out[y].__setitem__(c, col) for y in range(min(rs), max(rs) + 1)]
        else: return None
    return out
rule("fill_gaps_in_dashed_lines", "Each broken straight line of one colour has its gaps filled so it runs solid between its two ends.", gi_dashed, tf_dashed)


# 7 short segments extend to both edges
def gi_extend(rng):
    h, w = size(rng, 6, 16); g = blank(h, w); k = rng.randint(1, 3); cols = colours(rng, k); tr, tc = set(), set()
    for col in cols:
        for _ in range(40):
            if rng.random() < 0.5:
                r = rng.randrange(h); L = rng.randint(2, max(2, w // 2)); a = rng.randint(0, w - L)
                if r in tr or r - 1 in tr or r + 1 in tr: continue
                tr.add(r); [g[r].__setitem__(a + i, col) for i in range(L)]; break
            else:
                c = rng.randrange(w); L = rng.randint(2, max(2, h // 2)); a = rng.randint(0, h - L)
                if c in tc or c - 1 in tc or c + 1 in tc: continue
                tc.add(c); [g[a + i].__setitem__(c, col) for i in range(L)]; break
        else:
            return None
    return g
def tf_extend(g):
    H, W = dims(g); out = copy(g)
    for col in sorted(set(v for row in g for v in row if v)):
        pts = cells(g, lambda v: v == col); rs = {r for r, _ in pts}; cs = {c for _, c in pts}
        if len(rs) == 1: r = rs.pop(); out[r] = [col] * W
        elif len(cs) == 1: c = cs.pop(); [out[y].__setitem__(c, col) for y in range(H)]
        else: return None
    return out
rule("segments_extend_to_both_edges", "Every straight segment is extended in both directions until it spans the whole grid.", gi_extend, tf_extend)


# 8 legend A->B above a separator row, applied to the field below
def gi_legend(rng):
    k = rng.randint(1, 3); w = rng.randint(4, 14); fh = rng.randint(4, 12); g = blank(k + 1 + fh, w)
    cs = colours(rng, 2 * k, exclude=(0, 5)); src, dst = cs[:k], cs[k:]
    for i in range(k): g[i][0] = src[i]; g[i][1] = dst[i]
    g[k] = [5] * w
    for r in range(k + 1, k + 1 + fh):
        for c in range(w):
            if rng.random() < 0.35: g[r][c] = rng.choice(src)
    return g if any(g[r][c] for r in range(k + 1, k + 1 + fh) for c in range(w)) else None
def tf_legend(g):
    sep = next(i for i, row in enumerate(g) if all(v == 5 for v in row)); m = {g[i][0]: g[i][1] for i in range(sep)}
    out = copy(g)
    for r in range(sep + 1, len(g)):
        out[r] = [m.get(v, v) for v in g[r]]
    return out
rule("legend_recolours_field", "The colour pairs above the separator row form a legend; every field cell of a left-hand colour becomes its right-hand colour.", gi_legend, tf_legend)


# 9 left key column assigns colours to objects in top-to-bottom order
def gi_keyorder(rng):
    k = rng.randint(2, 4); h, w = rng.randint(max(6, k + 1), 16), rng.randint(8, 18); g = blank(h, w)
    cs = colours(rng, k + 1, exclude=(0, 5)); key, oc = cs[:k], cs[k]
    for i in range(k): g[i][0] = key[i]
    for r in range(h): g[r][1] = 5
    field = blank(h, w - 2)
    if place_shapes(rng, field, [random_shape(rng, rng.randint(2, 5)) for _ in range(k)], [oc] * k, margin=1) is None: return None
    obs = objects(field, 0)
    if len(obs) != k or len({min(r for r, _ in o) for o in obs}) != k: return None
    paste(g, field, 0, 2); return g
def tf_keyorder(g):
    key = [g[r][0] for r in range(len(g)) if g[r][0]]; field = [row[2:] for row in g]
    obs = sorted(objects(field, 0), key=lambda o: min(r for r, _ in o))
    if len(obs) != len(key): return None
    out = copy(g)
    for col, o in zip(key, obs):
        for r, c in o: out[r][c + 2] = col
    return out
rule("key_column_colours_objects_in_order", "The colours listed down the left key column are given to the field objects in top-to-bottom order.", gi_keyorder, tf_keyorder)


# 10 left-border markers fill their rows
def gi_rowfill(rng):
    h, w = size(rng, 5, 16); g = blank(h, w)
    for r in rng.sample(range(h), rng.randint(1, max(1, h // 3))): g[r][0] = rng.choice(COLOURS)
    return g
def tf_rowfill(g):
    return [[row[0]] * len(row) if row[0] else row[:] for row in g]
rule("left_markers_fill_rows", "Each marker in the left column fills its whole row with the marker colour.", gi_rowfill, tf_rowfill)


# 11 top and left border markers fill columns and rows; columns are painted last
def gi_rowcol(rng):
    h, w = size(rng, 6, 16); g = blank(h, w)
    for r in rng.sample(range(1, h), rng.randint(1, 3)): g[r][0] = rng.choice(COLOURS)
    for c in rng.sample(range(1, w), rng.randint(1, 3)): g[0][c] = rng.choice(COLOURS)
    return g
def tf_rowcol(g):
    H, W = dims(g); out = copy(g)
    for r in range(1, H):
        if g[r][0]: out[r] = [g[r][0]] * W
    for c in range(1, W):
        if g[0][c]:
            for r in range(H): out[r][c] = g[0][c]
    return out
rule("border_markers_fill_rows_and_columns", "Left-border markers fill their rows and top-border markers fill their columns, the columns painted over the rows.", gi_rowcol, tf_rowcol)


# 12 left-border markers recolour the objects on their rows
def gi_rowobj(rng):
    h, w = size(rng, 7, 16); g = blank(h, w); oc = rng.choice(COLOURS); k = rng.randint(2, 5)
    field = blank(h, w - 2)
    if place_shapes(rng, field, [random_shape(rng, rng.randint(2, 6)) for _ in range(k)], [oc] * k, margin=1) is None: return None
    paste(g, field, 0, 2); obs = objects(field, 0); rng.shuffle(obs)
    for o in obs[:rng.randint(1, len(obs))]:
        rows = sorted({r for r, _ in o}); r = rng.choice(rows)
        if g[r][0] == 0: g[r][0] = rng.choice([c for c in COLOURS if c != oc])
    return g if any(g[r][0] for r in range(h)) else None
def tf_rowobj(g):
    out = copy(g); field = [row[2:] for row in g]
    for o in objects(field, 0):
        hit = {g[r][0] for r, _ in o if g[r][0]}
        if len(hit) > 1: return None
        if hit:
            col = hit.pop()
            for r, c in o: out[r][c + 2] = col
    return out
rule("row_markers_recolour_objects_on_row", "An object takes the colour of the left-border marker whose row it touches; untouched objects keep their colour.", gi_rowobj, tf_rowobj)


# arrows: a 3-cell bar with a tip in the middle of one side
def _arrow(d):
    bar = {(-1, 0): [(1, 0), (1, 1), (1, 2), (0, 1)], (1, 0): [(0, 0), (0, 1), (0, 2), (1, 1)],
           (0, -1): [(0, 1), (1, 1), (2, 1), (1, 0)], (0, 1): [(0, 0), (1, 0), (2, 0), (1, 1)]}
    return bar[d]
def _arrow_dir(o):
    if len(o) != 4: return None
    rs = {}; cs = {}
    for r, c in o: rs[r] = rs.get(r, 0) + 1; cs[c] = cs.get(c, 0) + 1
    if 3 in rs.values():
        br = next(r for r, n in rs.items() if n == 3); tip = next(p for p in o if p[0] != br)
        return tip, (tip[0] - br, 0)
    if 3 in cs.values():
        bc = next(c for c, n in cs.items() if n == 3); tip = next(p for p in o if p[1] != bc)
        return tip, (0, tip[1] - bc)
    return None
def gi_arrows(rng):
    h, w = size(rng, 7, 16); g = blank(h, w); k = rng.randint(1, 3); cols = colours(rng, k)
    shapes = [_arrow(rng.choice(D4)) for _ in range(k)]
    return g if place_shapes(rng, g, shapes, cols, margin=1) else None

# 13 arrows leave a trail in the direction they point
def tf_arrow_trail(g):
    out = copy(g)
    for o in objects(g, 0):
        a = _arrow_dir(o)
        if a is None: return None
        (r, c), d = a; _ray(out, r, c, d[0], d[1], g[r][c])
    return out
rule("arrows_shoot_trail", "Each arrow shape (a bar with a tip) draws a line of its colour from the tip in the direction it points, until blocked.", gi_arrows, tf_arrow_trail)

# 14 arrows fly to the edge they point at
def tf_arrow_move(g):
    H, W = dims(g); out = blank(H, W)
    for o in objects(g, 0):
        a = _arrow_dir(o)
        if a is None: return None
        (dr, dc) = a[1]; r0, c0, r1, c1 = bbox(o)
        sh = {(-1, 0): -r0, (1, 0): H - 1 - r1, (0, -1): -c0, (0, 1): W - 1 - c1}[(dr, dc)]
        for r, c in o:
            nr, nc = r + dr * abs(sh), c + dc * abs(sh)
            if out[nr][nc]: return None
            out[nr][nc] = g[r][c]
    return out
rule("arrows_fly_to_pointed_edge", "Each arrow shape slides in the direction it points until it touches the grid edge.", gi_arrows, tf_arrow_move)


# 15 dots inside closed frames are recoloured; dots outside vanish
def gi_encl_dots(rng):
    h, w = size(rng, 8, 18); g = blank(h, w); f, d = colours(rng, 2, exclude=(0, 4))
    n = 0
    for _ in range(rng.randint(1, 2)):
        if _frame(rng, g, f, 4, 8, margin=1): n += 1
    if not n: return None
    sprinkle(rng, g, rng.randint(3, 10), d); return g if counts(g).get(d) else None
def tf_encl_dots(g):
    cnt = counts(g); f = max((c for c in cnt if c), key=lambda c: cnt[c]); out = copy(g); outside = _outside(g, f)
    for r, c in cells(g, lambda v: v != 0 and v != f):
        out[r][c] = 0 if (r, c) in outside else 4
    return out
rule("dots_inside_frames_recoloured_outside_removed", "Dots enclosed by a frame turn colour 4; dots outside every frame are erased.", gi_encl_dots, tf_encl_dots)


# 16 everything outside the closed loops is flooded
def gi_outside(rng):
    h, w = size(rng, 7, 16); g = blank(h, w); f = rng.choice([c for c in COLOURS if c != 8]); n = 0
    for _ in range(rng.randint(1, 3)):
        if _frame(rng, g, f, 3, 8, margin=1): n += 1
    return g if n else None
def tf_outside(g):
    f = max((c for c in counts(g) if c), key=lambda c: counts(g)[c]); out = copy(g)
    for r, c in _outside(g, f): out[r][c] = 8
    return out
rule("flood_outside_closed_loops", "Every cell outside the closed loops is painted colour 8; the loop interiors stay empty.", gi_outside, tf_outside)


# 17 Voronoi by nearest seed colour
def gi_voronoi(rng):
    h, w = size(rng, 5, 12); g = blank(h, w); k = rng.randint(2, 4)
    return g if _scatter(rng, g, k, colours(rng, k), margin=1) else None
def tf_voronoi(g):
    seeds = cells(g, lambda v: v != 0); H, W = dims(g); out = copy(g)
    for r in range(H):
        for c in range(W):
            if g[r][c]: continue
            d = sorted((abs(r - y) + abs(c - x), g[y][x]) for y, x in seeds)
            if len(d) == 1 or d[0][0] != d[1][0]: out[r][c] = d[0][1]
    return out
rule("voronoi_by_nearest_seed", "Every empty cell takes the colour of the nearest seed cell; cells equally near two seeds stay empty.", gi_voronoi, tf_voronoi)


# 18 grey objects take the colour of the nearest seed cell
def gi_obj_seed(rng):
    h, w = size(rng, 8, 18); g = blank(h, w); k = rng.randint(2, 4); s = rng.randint(2, 3); cs = colours(rng, s + 1); oc = cs[0]
    if place_shapes(rng, g, [random_shape(rng, rng.randint(2, 6)) for _ in range(k)], [oc] * k, margin=1) is None: return None
    return g if _scatter(rng, g, s, cs[1:], margin=1) else None
def tf_obj_seed(g):
    cnt = counts(g); seeds = [(r, c) for r, c in cells(g, lambda v: v != 0) if cnt[g[r][c]] == 1]
    oc = [c for c in cnt if c and cnt[c] > 1]
    if len(oc) != 1 or len(seeds) < 2: return None
    out = copy(g)
    for o in components(g, oc[0], conn8=True):
        d = sorted((min(abs(r - y) + abs(c - x) for r, c in o), g[y][x]) for y, x in seeds)
        if d[0][0] == d[1][0]: return None
        for r, c in o: out[r][c] = d[0][1]
    return out
rule("objects_take_nearest_seed_colour", "Each grey object is recoloured with the colour of the single seed cell nearest to it.", gi_obj_seed, tf_obj_seed)


# 19 bridges between facing same-colour rectangles
def _facing_pair(rng, g, cols, gap_lo=1, gap_hi=5, margin=1):
    H, W = dims(g)
    for _ in range(60):
        horiz = rng.random() < 0.5; h1, w1, h2, w2 = [rng.randint(2, 4) for _ in range(4)]; gap = rng.randint(gap_lo, gap_hi)
        if horiz:
            r0 = rng.randint(0, H - max(h1, h2)); c0 = rng.randint(0, W - (w1 + gap + w2))
            if c0 < 0: continue
            off = rng.randint(-(h2 - 1), h1 - 1); ra, rb = r0, r0 + off
            if rb < 0 or rb + h2 > H: continue
            boxes = [(ra, c0, ra + h1 - 1, c0 + w1 - 1), (rb, c0 + w1 + gap, rb + h2 - 1, c0 + w1 + gap + w2 - 1)]
        else:
            c0 = rng.randint(0, W - max(w1, w2)); r0 = rng.randint(0, H - (h1 + gap + h2))
            if r0 < 0: continue
            off = rng.randint(-(w2 - 1), w1 - 1); ca, cb = c0, c0 + off
            if cb < 0 or cb + w2 > W: continue
            boxes = [(r0, ca, r0 + h1 - 1, ca + w1 - 1), (r0 + h1 + gap, cb, r0 + h1 + gap + h2 - 1, cb + w2 - 1)]
        if all(g[y][x] == 0 for b in boxes for y in range(b[0] - margin, b[2] + margin + 1) for x in range(b[1] - margin, b[3] + margin + 1) if _in(g, y, x)):
            for b, col in zip(boxes, cols): rect(g, *b, col)
            return boxes
    return None
def gi_bridge_same(rng):
    h, w = size(rng, 8, 18); g = blank(h, w); k = rng.randint(1, 2); cs = colours(rng, k, exclude=(0, 8)); n = 0
    for col in cs:
        if _facing_pair(rng, g, [col, col]): n += 1
    return g if n else None
def tf_bridge_same(g):
    out = copy(g)
    for col in set(v for row in g for v in row if v):
        obs = components(g, col)
        if len(obs) != 2: return None
        (a0, b0, a1, b1), (c0, d0, c1, d1) = bbox(obs[0]), bbox(obs[1])
        rows = range(max(a0, c0), min(a1, c1) + 1); cols_ = range(max(b0, d0), min(b1, d1) + 1)
        if rows and not cols_:
            for r in rows:
                for c in range(min(b1, d1) + 1, max(b0, d0)): out[r][c] = 8
        elif cols_ and not rows:
            for c in cols_:
                for r in range(min(a1, c1) + 1, max(a0, c0)): out[r][c] = 8
        else: return None
    return out
rule("bridge_between_facing_same_colour_rectangles", "Two rectangles of one colour that face each other are joined by a colour-8 bridge spanning the rows or columns they share.", gi_bridge_same, tf_bridge_same)


# 20 bridge between differently coloured rectangles, each colour reaching halfway
def gi_bridge_half(rng):
    h, w = size(rng, 8, 16); g = blank(h, w); a, b = colours(rng, 2)
    return g if _facing_pair(rng, g, [a, b], gap_lo=2, gap_hi=6) else None
def tf_bridge_half(g):
    out = copy(g); obs = objects(g, 0)
    if len(obs) != 2: return None
    (a0, b0, a1, b1), (c0, d0, c1, d1) = bbox(obs[0]), bbox(obs[1]); ca, cb = g[a0][b0], g[c0][d0]
    rows = range(max(a0, c0), min(a1, c1) + 1); cols_ = range(max(b0, d0), min(b1, d1) + 1)
    if rows and not cols_:
        lo, hi = min(b1, d1) + 1, max(b0, d0); left = ca if b0 < d0 else cb; right = cb if b0 < d0 else ca
        for r in rows:
            for c in range(lo, hi):
                k = c - lo; n = hi - lo
                out[r][c] = left if k < n // 2 else (right if k >= (n + 1) // 2 else 0)
    elif cols_ and not rows:
        lo, hi = min(a1, c1) + 1, max(a0, c0); top = ca if a0 < c0 else cb; bot = cb if a0 < c0 else ca
        for c in cols_:
            for r in range(lo, hi):
                k = r - lo; n = hi - lo
                out[r][c] = top if k < n // 2 else (bot if k >= (n + 1) // 2 else 0)
    else: return None
    return out
rule("bridge_half_each_colour", "The gap between two facing rectangles is bridged, each rectangle's colour reaching halfway; an odd middle cell stays empty.", gi_bridge_half, tf_bridge_half)


# 21 a marker's rays are not drawn, but the grey objects they hit take its colour
def gi_paint_hit(rng):
    h, w = size(rng, 8, 16); g = blank(h, w); k = rng.randint(2, 5); cs = colours(rng, 3); oc = cs[0]
    if place_shapes(rng, g, [random_shape(rng, rng.randint(2, 6)) for _ in range(k)], [oc] * k, margin=1) is None: return None
    return g if _scatter(rng, g, rng.randint(1, 2), cs[1:], margin=1) else None
def tf_paint_hit(g):
    cnt = counts(g); oc = [c for c in cnt if c and cnt[c] > 1]
    if len(oc) != 1: return None
    obs = components(g, oc[0], conn8=True); owner = {p: i for i, o in enumerate(obs) for p in o}; paint = {}
    for r, c in cells(g, lambda v: v != 0 and v != oc[0]):
        for d in D4:
            hit = _first_hit(g, r, c, *d)
            if hit and hit in owner:
                if paint.setdefault(owner[hit], g[r][c]) != g[r][c]: return None
    if not paint: return None
    out = copy(g)
    for i, col in paint.items():
        for r, c in obs[i]: out[r][c] = col
    return out
rule("marker_rays_paint_objects_hit", "Each single marker looks up, down, left and right; the first grey object seen in each direction takes the marker's colour.", gi_paint_hit, tf_paint_hit)


# 22 diagonal rays down-right
def gi_diag(rng):
    h, w = size(rng, 6, 16); g = blank(h, w)
    return g if _scatter(rng, g, rng.randint(2, 5), [rng.choice(COLOURS) for _ in range(5)], margin=1, rows=range(0, h - 1), cols_=range(0, w - 1)) else None
def tf_diag(g):
    out = copy(g)
    for r, c in cells(g, lambda v: v != 0): _ray(out, r, c, 1, 1, g[r][c])
    return out
rule("cells_shoot_diagonal_down_right", "Every cell extends a diagonal line of its colour down and to the right until it is blocked or leaves the grid.", gi_diag, tf_diag)


# 23 crosses through markers
def gi_cross(rng):
    h, w = size(rng, 5, 16); g = blank(h, w); k = rng.randint(1, 3)
    return g if _scatter(rng, g, k, colours(rng, k), margin=1) else None
def tf_cross(g):
    H, W = dims(g); out = copy(g); pts = sorted(cells(g, lambda v: v != 0))
    for r, c in pts: out[r] = [g[r][c]] * W
    for r, c in pts:
        for y in range(H): out[y][c] = g[r][c]
    return out
rule("marker_full_cross_lines", "Each marker draws its full row and full column in its colour; columns are drawn over rows.", gi_cross, tf_cross)


# 24 numbered markers chained 1->2->3.. with L paths of colour 5
def gi_chain(rng):
    h, w = size(rng, 7, 16); g = blank(h, w); k = rng.randint(3, 4)
    return g if _scatter(rng, g, k, list(range(1, k + 1)), margin=1) else None
def tf_chain(g):
    pts = {g[r][c]: (r, c) for r, c in cells(g, lambda v: v != 0)}; out = copy(g); k = max(pts)
    if sorted(pts) != list(range(1, k + 1)): return None
    for i in range(1, k):
        (r1, c1), (r2, c2) = pts[i], pts[i + 1]
        for x in range(min(c1, c2), max(c1, c2) + 1):
            if out[r1][x] == 0: out[r1][x] = 5
        for y in range(min(r1, r2), max(r1, r2) + 1):
            if out[y][c2] == 0: out[y][c2] = 5
    return out
rule("chain_numbered_markers_with_l_paths", "Markers coloured 1, 2, 3... are linked in order by colour-5 L-paths: horizontal from the lower number, then vertical to the next.", gi_chain, tf_chain, digits=True)


# 25 key row maps object size to colour
def gi_keysize(rng):
    k = rng.randint(2, 4); h, w = rng.randint(7, 16), rng.randint(max(6, k), 16); g = blank(h, w)
    cs = colours(rng, k + 1, exclude=(0, 5)); key, oc = cs[:k], cs[k]
    for i in range(k): g[0][i] = key[i]
    g[1] = [5] * w; field = blank(h - 2, w); n = rng.randint(2, 5)
    sizes = [rng.randint(1, k) for _ in range(n)]
    if place_shapes(rng, field, [random_shape(rng, s) for s in sizes], [oc] * n, margin=1) is None: return None
    paste(g, field, 2, 0); return g
def tf_keysize(g):
    key = [v for v in g[0] if v]; out = copy(g)
    for o in objects([row[:] for row in g[2:]], 0):
        if len(o) > len(key): return None
        for r, c in o: out[r + 2][c] = key[len(o) - 1]
    return out
rule("key_row_colours_objects_by_size", "The key row lists colours; an object of n cells in the field below the separator takes the n-th key colour.", gi_keysize, tf_keysize)


# 26 legend pairs swapped both ways
def gi_swap(rng):
    k = rng.randint(1, 3); w = rng.randint(4, 14); fh = rng.randint(4, 12); g = blank(k + 1 + fh, w)
    cs = colours(rng, 2 * k, exclude=(0, 5))
    for i in range(k): g[i][0] = cs[2 * i]; g[i][1] = cs[2 * i + 1]
    g[k] = [5] * w
    for r in range(k + 1, k + 1 + fh):
        for c in range(w):
            if rng.random() < 0.35: g[r][c] = rng.choice(cs)
    return g if any(g[r][c] for r in range(k + 1, k + 1 + fh) for c in range(w)) else None
def tf_swap(g):
    sep = next(i for i, row in enumerate(g) if all(v == 5 for v in row)); m = {}
    for i in range(sep): m[g[i][0]] = g[i][1]; m[g[i][1]] = g[i][0]
    out = copy(g)
    for r in range(sep + 1, len(g)): out[r] = [m.get(v, v) for v in g[r]]
    return out
rule("legend_swaps_colour_pairs", "Each legend pair above the separator names two colours that are exchanged with each other throughout the field below.", gi_swap, tf_swap)


# 27 key shape in a side panel; matching field shapes take the key colour
def _norm(o):
    r0 = min(r for r, _ in o); c0 = min(c for _, c in o); return tuple(sorted((r - r0, c - c0) for r, c in o))
def gi_keyshape(rng):
    h, w = rng.randint(8, 16), rng.randint(12, 20); g = blank(h, w); kc, oc = colours(rng, 2, exclude=(0, 5))
    key = random_shape(rng, rng.randint(3, 5))
    for r, c in key: g[1 + r][1 + c] = kc
    for r in range(h): g[r][5] = 5
    n = rng.randint(3, 5); shapes = [key] + [random_shape(rng, rng.randint(3, 5)) for _ in range(n - 1)]; rng.shuffle(shapes)
    field = blank(h, w - 6)
    if place_shapes(rng, field, shapes, [oc] * n, margin=1) is None: return None
    paste(g, field, 0, 6); return g
def tf_keyshape(g):
    sep = next(c for c in range(len(g[0])) if all(row[c] == 5 for row in g)); panel = [row[:sep] for row in g]
    kobs = objects(panel, 0)
    if len(kobs) != 1: return None
    key = _norm(kobs[0]); kc = panel[kobs[0][0][0]][kobs[0][0][1]]; out = copy(g); hit = 0
    for o in objects([row[sep + 1:] for row in g], 0):
        if _norm(o) == key:
            hit += 1
            for r, c in o: out[r][c + sep + 1] = kc
    return out if hit else None
rule("key_shape_recolours_matching_objects", "Field objects with exactly the shape shown in the side panel are recoloured with the panel shape's colour.", gi_keyshape, tf_keyshape)


# 28 same-coloured top and left border markers connect through an L at their crossing
def gi_border_l(rng):
    h, w = size(rng, 6, 16); g = blank(h, w); k = rng.randint(1, 3); cs = colours(rng, k)
    rows = rng.sample(range(2, h), min(k, h - 2)); cols_ = rng.sample(range(2, w), min(k, w - 2))
    if len(rows) < k or len(cols_) < k: return None
    for col, r, c in zip(cs, rows, cols_): g[r][0] = col; g[0][c] = col
    return g
def tf_border_l(g):
    H, W = dims(g); out = copy(g)
    for col in sorted(set(v for row in g for v in row if v)):
        rs = [r for r in range(1, H) if g[r][0] == col]; cs = [c for c in range(1, W) if g[0][c] == col]
        if len(rs) != 1 or len(cs) != 1: return None
        r, c = rs[0], cs[0]
        for y in range(1, r + 1): out[y][c] = col
        for x in range(1, c + 1): out[r][x] = col
    return out
rule("border_marker_pairs_meet_in_l", "A top-border marker and the left-border marker of the same colour are joined by an L-shaped line that turns at the cell where their column and row cross.", gi_border_l, tf_border_l)


# 29 a nozzle cell on a rectangle's side fires a ray away from the rectangle
def gi_nozzle(rng):
    h, w = size(rng, 8, 18); g = blank(h, w); a, b = colours(rng, 2); k = rng.randint(1, 3)
    rects = _rects(rng, g, k, [b] * k, 2, 4, margin=2)
    if rects is None: return None
    for r0, c0, r1, c1, _ in rects:
        side = rng.randrange(4)
        r, c = [(rng.randint(r0, r1), c0 - 1), (rng.randint(r0, r1), c1 + 1), (r0 - 1, rng.randint(c0, c1)), (r1 + 1, rng.randint(c0, c1))][side]
        if _in(g, r, c) and g[r][c] == 0: g[r][c] = a
    return g if counts(g).get(a) else None
def tf_nozzle(g):
    cnt = counts(g); a = min((c for c in cnt if c), key=lambda c: cnt[c]); out = copy(g)
    for r, c in cells(g, lambda v: v == a):
        d = [(dr, dc) for dr, dc in D4 if _in(g, r + dr, c + dc) and g[r + dr][c + dc] not in (0, a)]
        if len(d) != 1: return None
        _ray(out, r, c, -d[0][0], -d[0][1], a)
    return out
rule("nozzle_on_rectangle_fires_outward", "A single cell stuck to a rectangle's side fires a line of its colour straight away from the rectangle.", gi_nozzle, tf_nozzle)


# 30 a line that ends at a block continues on the far side
def gi_through(rng):
    h, w = size(rng, 8, 18); g = blank(h, w); a, b = colours(rng, 2); k = rng.randint(1, 2)
    rects = _rects(rng, g, k, [b] * k, 2, 4, margin=2)
    if rects is None: return None
    for r0, c0, r1, c1, _ in rects:
        side = rng.randrange(4)
        if side == 0 and c0 >= 3: r = rng.randint(r0, r1); L = rng.randint(2, c0); [g[r].__setitem__(c0 - i, a) for i in range(1, L + 1)]
        elif side == 1 and w - 1 - c1 >= 3: r = rng.randint(r0, r1); L = rng.randint(2, w - 1 - c1); [g[r].__setitem__(c1 + i, a) for i in range(1, L + 1)]
        elif side == 2 and r0 >= 3: c = rng.randint(c0, c1); L = rng.randint(2, r0); [g[r0 - i].__setitem__(c, a) for i in range(1, L + 1)]
        elif side == 3 and h - 1 - r1 >= 3: c = rng.randint(c0, c1); L = rng.randint(2, h - 1 - r1); [g[r1 + i].__setitem__(c, a) for i in range(1, L + 1)]
    return g if counts(g).get(a) else None
def tf_through(g):
    cnt = counts(g); out = copy(g); changed = False
    lines = [c for c in cnt if c and all(len({r for r, _ in o}) == 1 or len({x for _, x in o}) == 1 for o in components(g, c)) and all(len(o) >= 2 for o in components(g, c))]
    if len(lines) != 1: return None
    a = lines[0]
    for o in components(g, a):
        o = sorted(o); ends = [(o[0], (o[0][0] - o[1][0], o[0][1] - o[1][1])), (o[-1], (o[-1][0] - o[-2][0], o[-1][1] - o[-2][1]))]
        for (r, c), (dr, dc) in ends:
            y, x = r + dr, c + dc
            if _in(g, y, x) and g[y][x] not in (0, a):
                while _in(g, y, x) and g[y][x] not in (0, a): y += dr; x += dc
                while _in(g, y, x) and g[y][x] == 0: out[y][x] = a; y += dr; x += dc; changed = True
    return out if changed else None
rule("line_continues_beyond_block", "A line that runs into a block reappears on the block's far side and continues to the grid edge.", gi_through, tf_through)


# 31 frames filled with the colour of the dot inside them
def gi_frame_dot(rng):
    h, w = size(rng, 8, 18); g = blank(h, w); f = rng.choice(COLOURS); n = 0
    for _ in range(rng.randint(1, 3)):
        b = _frame(rng, g, f, 4, 8, margin=1)
        if b:
            r0, c0, r1, c1 = b; g[rng.randint(r0 + 1, r1 - 1)][rng.randint(c0 + 1, c1 - 1)] = rng.choice([c for c in COLOURS if c != f]); n += 1
    return g if n else None
def tf_frame_dot(g):
    cnt = counts(g); f = max((c for c in cnt if c), key=lambda c: cnt[c]); out = copy(g)
    for o in components(g, f):
        r0, c0, r1, c1 = bbox(o); inside = [(r, c) for r in range(r0 + 1, r1) for c in range(c0 + 1, c1) if g[r][c]]
        if len(inside) != 1: return None
        rect(out, r0 + 1, c0 + 1, r1 - 1, c1 - 1, g[inside[0][0]][inside[0][1]])
    return out
rule("frame_filled_with_inner_dot_colour", "Each hollow frame is filled inside with the colour of the single dot it contains.", gi_frame_dot, tf_frame_dot)


# 32 coloured walls; grey objects take the nearest wall's colour
def gi_walls(rng):
    h, w = size(rng, 8, 18); g = blank(h, w); cs = colours(rng, 5); t, b, l, r, oc = cs
    g[0] = [t] * w; g[h - 1] = [b] * w
    for y in range(1, h - 1): g[y][0] = l; g[y][w - 1] = r
    field = blank(h - 4, w - 4); k = rng.randint(2, 5)
    if place_shapes(rng, field, [random_shape(rng, rng.randint(1, 5)) for _ in range(k)], [oc] * k, margin=1) is None: return None
    paste(g, field, 2, 2); return g
def tf_walls(g):
    H, W = dims(g); out = copy(g); inner = [row[1:-1] for row in g[1:-1]]
    for o in objects(inner, 0):
        d = sorted([(min(r for r, _ in o) + 1, g[0][1]), (H - 2 - max(r for r, _ in o), g[H - 1][1]),
                    (min(c for _, c in o) + 1, g[1][0]), (W - 2 - max(c for _, c in o), g[1][W - 1])])
        if d[0][0] == d[1][0]: return None
        for r, c in o: out[r + 1][c + 1] = d[0][1]
    return out
rule("objects_take_nearest_wall_colour", "The four walls are coloured; each grey object inside takes the colour of the wall it is closest to.", gi_walls, tf_walls)


# 33 intersections of marked rows and columns only
def gi_inter(rng):
    h, w = size(rng, 6, 16); g = blank(h, w)
    for r in rng.sample(range(1, h), rng.randint(1, 3)): g[r][0] = rng.choice(COLOURS)
    for c in rng.sample(range(1, w), rng.randint(1, 3)): g[0][c] = rng.choice(COLOURS)
    return g
def tf_inter(g):
    H, W = dims(g); out = copy(g)
    for r in range(1, H):
        for c in range(1, W):
            if g[r][0] and g[0][c]: out[r][c] = g[r][0]
    return out
rule("border_marker_intersections_only", "Only the cells where a left-marked row crosses a top-marked column are painted, in the row marker's colour.", gi_inter, tf_inter)


# 34 diagonal rays from rectangle corners
def gi_corner_rays(rng):
    h, w = size(rng, 8, 18); g = blank(h, w); k = rng.randint(1, 2); cs = colours(rng, k)
    return g if _rects(rng, g, k, cs, 2, 4, margin=2) else None
def tf_corner_rays(g):
    out = copy(g)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o); col = g[r0][c0]
        if len(o) != (r1 - r0 + 1) * (c1 - c0 + 1): return None
        for (r, c), (dr, dc) in [((r0, c0), (-1, -1)), ((r0, c1), (-1, 1)), ((r1, c0), (1, -1)), ((r1, c1), (1, 1))]:
            _ray(out, r, c, dr, dc, col)
    return out
rule("rectangle_corners_shoot_diagonals", "Each rectangle sends a diagonal line of its colour out of all four corners until blocked.", gi_corner_rays, tf_corner_rays)


# 35 markers slide to touch the nearest object
def gi_slide(rng):
    h, w = size(rng, 8, 18); g = blank(h, w); a, b = colours(rng, 2)
    rects = _rects(rng, g, rng.randint(1, 3), [b] * 3, 2, 4, margin=2)
    if rects is None: return None
    return g if _aligned_markers(rng, g, rects, a, rng.randint(1, 3), gap_lo=2, gap_hi=7) else None
def tf_slide(g):
    cnt = counts(g); m = [c for c in cnt if c and all(len(o) == 1 for o in components(g, c))]
    if len(m) != 1: return None
    out = copy(g)
    for r, c in cells(g, lambda v: v == m[0]):
        n = _nearest_obj_cell(g, r, c, m[0])
        if n is None or (n[1] != r and n[2] != c): return None
        dr, dc = (0, 1 if n[2] > c else -1) if n[1] == r else (1 if n[1] > r else -1, 0)
        out[r][c] = 0; out[n[1] - dr][n[2] - dc] = m[0]
    return out
rule("marker_slides_to_touch_nearest_object", "Each single-cell marker moves in a straight line until it sits against the nearest object.", gi_slide, tf_slide)


# 36 a light on one border casts colour-8 shadows behind every object
def gi_shadow(rng):
    h, w = size(rng, 8, 18); g = blank(h, w); lc, oc = colours(rng, 2, exclude=(0, 8)); k = rng.randint(1, 4)
    field = blank(h - 4, w - 4)
    if place_shapes(rng, field, [random_shape(rng, rng.randint(2, 6)) for _ in range(k)], [oc] * k, margin=1) is None: return None
    paste(g, field, 2, 2); side = rng.randrange(4)
    r, c = [(0, rng.randrange(w)), (h - 1, rng.randrange(w)), (rng.randrange(h), 0), (rng.randrange(h), w - 1)][side]
    g[r][c] = lc; return g
def tf_shadow(g):
    H, W = dims(g); cnt = counts(g); lc = [c for c in cnt if c and cnt[c] == 1]
    if len(lc) != 1: return None
    (r, c), = cells(g, lambda v: v == lc[0])
    d = (1, 0) if r == 0 else (-1, 0) if r == H - 1 else (0, 1) if c == 0 else (0, -1) if c == W - 1 else None
    if d is None: return None
    out = copy(g)
    for y, x in cells(g, lambda v: v != 0 and v != lc[0]): _ray(out, y, x, d[0], d[1], 8)
    return out
rule("border_light_casts_shadows", "The single cell on the border is a light; every object casts a colour-8 shadow away from it to the far edge.", gi_shadow, tf_shadow)


# 37 colour-coded rays: 1 up, 2 down, 3 left, 4 right
def gi_coded(rng):
    h, w = size(rng, 6, 16); g = blank(h, w); k = rng.randint(2, 6)
    return g if _scatter(rng, g, k, [rng.randint(1, 4) for _ in range(k)], margin=1) else None
def tf_coded(g):
    out = copy(g); dm = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}
    for r, c in sorted(cells(g, lambda v: v != 0)):
        if g[r][c] not in dm: return None
        _ray(out, r, c, *dm[g[r][c]], g[r][c])
    return out
rule("colour_coded_ray_direction", "Each cell shoots a ray of its colour: colour 1 goes up, 2 down, 3 left, 4 right, stopping at anything in the way.", gi_coded, tf_coded)


# 38 two-cell arrows: tail colour behind head colour; the head fires forward
def gi_domino(rng):
    h, w = size(rng, 6, 16); g = blank(h, w); hc, tc = colours(rng, 2); k = rng.randint(1, 4)
    shapes, cols_ = [], []
    for _ in range(k):
        d = rng.choice(D4); shapes.append([(0, 0), (d[0] if d[0] >= 0 else 0, d[1] if d[1] >= 0 else 0)])
    taken = set()
    for _ in range(k):
        for _ in range(60):
            d = rng.choice(D4); r, c = rng.randrange(h), rng.randrange(w); hr, hcc = r + d[0], c + d[1]
            if not _in(g, hr, hcc): continue
            foot = {(y + dy, x + dx) for y, x in ((r, c), (hr, hcc)) for dy in (-1, 0, 1) for dx in (-1, 0, 1)}
            if foot & taken: continue
            taken |= {(r, c), (hr, hcc)}; g[r][c] = tc; g[hr][hcc] = hc; break
    return g if counts(g).get(hc) else None
def tf_domino(g):
    out = copy(g); heads = {}
    for r, c in cells(g, lambda v: v != 0):
        for dr, dc in D4:
            if _in(g, r + dr, c + dc) and g[r + dr][c + dc] not in (0, g[r][c]):
                heads.setdefault((r, c), []).append((dr, dc))
    pairs = {p: d for p, d in heads.items() if len(d) == 1}
    cols_ = {g[r][c] for r, c in pairs}
    if len(cols_) != 2: return None
    hc = max(cols_)
    for (r, c), d in sorted(pairs.items()):
        if g[r][c] == hc: _ray(out, r, c, -d[0][0], -d[0][1], hc)
    return out
rule("domino_arrows_fire_from_head", "Each two-cell domino fires a ray from its higher-numbered head cell in the direction away from its tail, in the head's colour.", gi_domino, tf_domino, digits=True)


# 39 a frame with one opening: fill inside and leak out through the gap
def gi_leak(rng):
    h, w = size(rng, 8, 18); g = blank(h, w); f = rng.choice([c for c in COLOURS if c != 8]); n = 0
    for _ in range(rng.randint(1, 2)):
        b = _frame(rng, g, f, 4, 8, margin=1)
        if b:
            r0, c0, r1, c1 = b; side = rng.randrange(4)
            r, c = [(r0, rng.randint(c0 + 1, c1 - 1)), (r1, rng.randint(c0 + 1, c1 - 1)), (rng.randint(r0 + 1, r1 - 1), c0), (rng.randint(r0 + 1, r1 - 1), c1)][side]
            g[r][c] = 0; n += 1
    return g if n else None
def tf_leak(g):
    f = max((c for c in counts(g) if c), key=lambda c: counts(g)[c]); out = copy(g)
    for o in components(g, f):
        r0, c0, r1, c1 = bbox(o)
        gaps = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if (r in (r0, r1) or c in (c0, c1)) and g[r][c] != f]
        if len(gaps) != 1: return None
        rect(out, r0 + 1, c0 + 1, r1 - 1, c1 - 1, 8); r, c = gaps[0]; out[r][c] = 8
        d = (-1, 0) if r == r0 else (1, 0) if r == r1 else (0, -1) if c == c0 else (0, 1)
        _ray(out, r, c, d[0], d[1], 8)
    return out
rule("open_frame_fills_and_leaks", "A frame with one opening is filled with colour 8, and the fill leaks out through the opening in a straight line to the edge.", gi_leak, tf_leak)


# 40 top key row recolours each grey cell by its column
def gi_colkey(rng):
    h, w = size(rng, 6, 16); g = blank(h, w); oc = rng.choice([c for c in COLOURS if c != 5]); ks = colours(rng, rng.randint(2, 4), exclude=(0, 5, oc))
    g[0] = [rng.choice(ks) for _ in range(w)]; g[1] = [5] * w
    sprinkle(rng, g, rng.randint(3, (h - 2) * w // 3), oc); return g if counts(g).get(oc) else None
def tf_colkey(g):
    out = copy(g)
    for r in range(2, len(g)):
        for c in range(len(g[0])):
            if g[r][c]: out[r][c] = g[0][c]
    return out
rule("column_key_recolours_cells", "Each grey cell below the separator takes the colour shown at the top of its column in the key row.", gi_colkey, tf_colkey)
