# b049_circular.py -- circular and angular arrangements: objects placed around a central marker.
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

OFFS8 = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]  # N,NE,E,SE,S,SW,W,NW clockwise


def _size(rng, large_frac=0.32):
    return rng.randint(21, 30) if rng.random() < large_frac else rng.randint(9, 18)


# ---------- ring8: eight compass positions around a centre marker ----------
def _ring8_build(rng, marker=None, n_colours=None, n_fill=8, large_frac=0.32):
    n = _size(rng, large_frac); h = w = n
    cy, cx = h // 2, w // 2
    R = max(2, min(cy, cx, h - 1 - cy, w - 1 - cx))
    mk = marker if marker is not None else rng.choice(range(1, 10))
    rp = [c for c in range(1, 10) if c != mk]
    k = n_colours or rng.randint(2, len(rp))
    palette = rng.sample(rp, min(k, len(rp)))
    g = blank(h, w); g[cy][cx] = mk
    idxs = list(range(8))
    fillset = idxs if n_fill >= 8 else rng.sample(idxs, n_fill)
    for i in fillset:
        dy, dx = OFFS8[i]
        g[cy + dy * R][cx + dx * R] = rng.choice(palette)
    return g


def _read_ring8(g):
    h, w = dims(g); cy, cx = h // 2, w // 2
    mk = g[cy][cx]
    R = 0
    for r in range(h):
        for c in range(w):
            if (r, c) != (cy, cx) and g[r][c] != 0:
                R = max(R, max(abs(r - cy), abs(c - cx)))
    if R == 0:
        R = max(2, min(cy, cx, h - 1 - cy, w - 1 - cx))
    pos = [(cy + dy * R, cx + dx * R) for dy, dx in OFFS8]
    cols = [g[r][c] if 0 <= r < h and 0 <= c < w else 0 for r, c in pos]
    return mk, cy, cx, R, pos, cols


def _write_ring8(h, w, cy, cx, mk, pos, cols):
    g = blank(h, w); g[cy][cx] = mk
    for (r, c), v in zip(pos, cols):
        if v and 0 <= r < h and 0 <= c < w:
            g[r][c] = v
    return g


def gi_ring8_plain(rng):
    return _ring8_build(rng)


def tf_ring8_cw(g):
    mk, cy, cx, R, pos, cols = _read_ring8(g)
    new = [cols[-1]] + cols[:-1]
    h, w = dims(g)
    return _write_ring8(h, w, cy, cx, mk, pos, new)
rule("ring8_step_clockwise", "Each object on the ring of eight positions around the centre marker moves one step clockwise.", gi_ring8_plain, tf_ring8_cw)


def tf_ring8_ccw(g):
    mk, cy, cx, R, pos, cols = _read_ring8(g)
    new = cols[1:] + cols[:1]
    h, w = dims(g)
    return _write_ring8(h, w, cy, cx, mk, pos, new)
rule("ring8_step_counterclockwise", "Each object on the ring around the centre marker moves one step counterclockwise.", gi_ring8_plain, tf_ring8_ccw)


def gi_ring8_marked(rng):
    g = _ring8_build(rng)
    h, w = dims(g); mk, cy, cx, R, pos, cols = _read_ring8(g)
    m = rng.randrange(8); cols[m] = mk
    return _write_ring8(h, w, cy, cx, mk, pos, cols)


def tf_ring8_opp_marked(g):
    mk, cy, cx, R, pos, cols = _read_ring8(g)
    if mk not in cols:
        return None
    m = cols.index(mk); opp = (m + 4) % 8
    cols[opp] = mk
    h, w = dims(g)
    return _write_ring8(h, w, cy, cx, mk, pos, cols)
rule("ring8_opposite_of_marked_recoloured", "The object diametrically opposite the one marked with the centre's colour is recoloured to the centre's colour.", gi_ring8_marked, tf_ring8_opp_marked)


def tf_ring8_swap_pairs(g):
    mk, cy, cx, R, pos, cols = _read_ring8(g)
    for i in range(4):
        cols[i], cols[i + 4] = cols[i + 4], cols[i]
    h, w = dims(g)
    return _write_ring8(h, w, cy, cx, mk, pos, cols)
rule("ring8_swap_diametric_pairs", "Every object on the ring swaps colours with the object diametrically opposite it.", gi_ring8_plain, tf_ring8_swap_pairs)


_REFLECT_V = {0: 0, 1: 7, 2: 6, 3: 5, 4: 4, 5: 3, 6: 2, 7: 1}
def tf_ring8_reflect_v(g):
    mk, cy, cx, R, pos, cols = _read_ring8(g)
    new = [cols[_REFLECT_V[i]] for i in range(8)]
    h, w = dims(g)
    return _write_ring8(h, w, cy, cx, mk, pos, new)
rule("ring8_reflect_vertical_axis", "The ring of objects around the centre marker is reflected left to right across the vertical axis.", gi_ring8_plain, tf_ring8_reflect_v)


_REFLECT_H = {0: 4, 1: 3, 2: 2, 3: 1, 4: 0, 5: 7, 6: 6, 7: 5}
def tf_ring8_reflect_h(g):
    mk, cy, cx, R, pos, cols = _read_ring8(g)
    new = [cols[_REFLECT_H[i]] for i in range(8)]
    h, w = dims(g)
    return _write_ring8(h, w, cy, cx, mk, pos, new)
rule("ring8_reflect_horizontal_axis", "The ring of objects around the centre marker is reflected top to bottom across the horizontal axis.", gi_ring8_plain, tf_ring8_reflect_h)


def tf_ring8_quadrant_pair(g):
    mk, cy, cx, R, pos, cols = _read_ring8(g)
    for a, b in [(0, 1), (2, 3), (4, 5), (6, 7)]:
        cols[b] = cols[a]
    h, w = dims(g)
    return _write_ring8(h, w, cy, cx, mk, pos, cols)
rule("ring8_recolour_by_angle_quadrant", "Within each 90-degree quadrant of the ring, the second object takes the colour of the first.", gi_ring8_plain, tf_ring8_quadrant_pair)


def tf_ring8_delete12(g):
    mk, cy, cx, R, pos, cols = _read_ring8(g)
    if not cols[0]:
        return None
    cols[0] = 0
    h, w = dims(g)
    return _write_ring8(h, w, cy, cx, mk, pos, cols)
rule("ring8_delete_twelve_oclock", "The object at the twelve o'clock position on the ring is deleted.", gi_ring8_plain, tf_ring8_delete12)


def gi_ring8_gap(rng):
    g = _ring8_build(rng, n_fill=7)
    return g


def tf_ring8_fill_gap(g):
    mk, cy, cx, R, pos, cols = _read_ring8(g)
    if 0 not in cols:
        return None
    i = cols.index(0); cols[i] = mk
    h, w = dims(g)
    return _write_ring8(h, w, cy, cx, mk, pos, cols)
rule("ring8_fill_single_gap", "The one empty position on the ring is filled with the centre marker's colour.", gi_ring8_gap, tf_ring8_fill_gap)


def gi_ring8_digit(rng):
    return _ring8_build(rng, marker=rng.choice(range(1, 10)))


def tf_ring8_rotate_digit(g):
    mk, cy, cx, R, pos, cols = _read_ring8(g)
    steps = (mk - 1) % 7 + 1
    new = cols[-steps:] + cols[:-steps]
    h, w = dims(g)
    return _write_ring8(h, w, cy, cx, mk, pos, new)
rule("ring8_rotate_by_centre_digit", "The ring rotates clockwise by a number of steps equal to the centre marker's digit value.", gi_ring8_digit, tf_ring8_rotate_digit, digits=True)


def tf_ring8_alternate_marked(g):
    mk, cy, cx, R, pos, cols = _read_ring8(g)
    if mk not in cols:
        return None
    m = cols.index(mk)
    other = next((cols[(m + o) % 8] for o in range(1, 8) if cols[(m + o) % 8] not in (0, mk)), None)
    if other is None:
        return None
    new = [0] * 8
    for o in range(8):
        new[(m + o) % 8] = mk if o % 2 == 0 else other
    h, w = dims(g)
    return _write_ring8(h, w, cy, cx, mk, pos, new)
rule("ring8_alternate_from_marked", "Starting from the object marked with the centre's colour, the ring alternates between that colour and one other colour going clockwise.", gi_ring8_marked, tf_ring8_alternate_marked)


def tf_ring8_row(g):
    mk, cy, cx, R, pos, cols = _read_ring8(g)
    if 0 in cols:
        return None
    return [cols[:]]
rule("ring8_colours_to_row_clockwise", "Output a single row listing the ring's colours in clockwise order starting at twelve o'clock.", gi_ring8_plain, tf_ring8_row)


def gi_ring8_arc(rng):
    g = _ring8_build(rng, n_fill=8, n_colours=rng.randint(2, 4))
    h, w = dims(g); mk, cy, cx, R, pos, cols = _read_ring8(g)
    used = set(cols) | {mk}
    free = [c for c in range(1, 10) if c not in used]
    if not free:
        return None
    end = rng.choice(free)
    a = rng.randrange(8); d = rng.choice([2, 3]); b = (a + d) % 8
    cols[a] = end; cols[b] = end
    return _write_ring8(h, w, cy, cx, mk, pos, cols)


def tf_ring8_arc_fill(g):
    mk, cy, cx, R, pos, cols = _read_ring8(g)
    cnt = {}
    for v in cols:
        cnt[v] = cnt.get(v, 0) + 1
    endcol = next((v for v, n in cnt.items() if n == 2 and v not in (0, mk)), None)
    if endcol is None:
        return None
    idxs = [i for i, v in enumerate(cols) if v == endcol]
    a, b = idxs
    f = (b - a) % 8
    if f <= 8 - f:
        between = [(a + k) % 8 for k in range(1, f)]
    else:
        between = [(b + k) % 8 for k in range(1, 8 - f)]
    for i in between:
        cols[i] = endcol
    h, w = dims(g)
    return _write_ring8(h, w, cy, cx, mk, pos, cols)
rule("ring8_arc_fill_between_marked_pair", "The shorter arc between the two ring objects sharing the same tagged colour is filled with that colour.", gi_ring8_arc, tf_ring8_arc_fill)


def tf_ring8_rotate2(g):
    mk, cy, cx, R, pos, cols = _read_ring8(g)
    new = cols[-2:] + cols[:-2]
    h, w = dims(g)
    return _write_ring8(h, w, cy, cx, mk, pos, new)
rule("ring8_rotate_two_steps_clockwise", "The ring rotates clockwise by exactly two positions.", gi_ring8_plain, tf_ring8_rotate2)


def tf_ring8_diag_mirror(g):
    mk, cy, cx, R, pos, cols = _read_ring8(g)
    diag = {0: 2, 1: 1, 2: 0, 3: 7, 4: 6, 5: 5, 6: 4, 7: 3}
    new = [cols[diag[i]] for i in range(8)]
    h, w = dims(g)
    return _write_ring8(h, w, cy, cx, mk, pos, new)
rule("ring8_mirror_diagonal_axis", "The ring is reflected across the diagonal running from the one o'clock to seven o'clock positions.", gi_ring8_plain, tf_ring8_diag_mirror)


def tf_ring8_shift_by_gaps(g):
    mk, cy, cx, R, pos, cols = _read_ring8(g)
    gaps = cols.count(0)
    if gaps == 0:
        return None
    steps = gaps % 8
    if steps == 0:
        return None
    new = cols[-steps:] + cols[:-steps]
    h, w = dims(g)
    return _write_ring8(h, w, cy, cx, mk, pos, new)
rule("ring8_shift_by_count_of_gaps", "The ring rotates clockwise by a number of steps equal to the number of empty positions on it.", gi_ring8_gap, tf_ring8_shift_by_gaps)


def tf_ring8_marked_spreads(g):
    mk, cy, cx, R, pos, cols = _read_ring8(g)
    if mk not in cols:
        return None
    m = cols.index(mk)
    for n in ((m - 1) % 8, (m + 1) % 8):
        if cols[n]:
            cols[n] = mk
    h, w = dims(g)
    return _write_ring8(h, w, cy, cx, mk, pos, cols)
rule("ring8_marked_colour_spreads_to_neighbours", "The object marked with the centre's colour spreads that colour to its two ring neighbours.", gi_ring8_marked, tf_ring8_marked_spreads)


def tf_ring8_quadrant_majority(g):
    mk, cy, cx, R, pos, cols = _read_ring8(g)
    out = cols[:]
    for lo in (0, 2, 4, 6):
        grp = cols[lo:lo + 2]
        nz = [v for v in grp if v]
        if not nz:
            continue
        maj = max(set(nz), key=nz.count)
        out[lo] = maj; out[lo + 1] = maj
    h, w = dims(g)
    return _write_ring8(h, w, cy, cx, mk, pos, out)
rule("ring8_quadrant_majority_colour_fills_quadrant", "Within each quadrant of the ring, both objects take the quadrant's majority colour.", gi_ring8_plain, tf_ring8_quadrant_majority)


# ---------- square ring: the hollow square border around a centre marker ----------
def _sq_coords(cy, cx, R):
    top, bot, left, right = cy - R, cy + R, cx - R, cx + R
    coords = []
    for c in range(left, right):
        coords.append((top, c))
    for r in range(top, bot):
        coords.append((r, right))
    for c in range(right, left, -1):
        coords.append((bot, c))
    for r in range(bot, top, -1):
        coords.append((r, left))
    return coords


def _sqring_build(rng, n_colours=None, fill_frac=1.0, large_frac=0.32, margin=0, R=None):
    n = _size(rng, large_frac); h = w = n
    cy, cx = h // 2, w // 2
    Rmax = max(2, min(cy, cx, h - 1 - cy, w - 1 - cx) - margin)
    RR = R if R is not None else Rmax
    mk = rng.choice(range(1, 10))
    rp = [c for c in range(1, 10) if c != mk]
    k = n_colours or rng.randint(2, min(6, len(rp)))
    palette = rng.sample(rp, k)
    g = blank(h, w); g[cy][cx] = mk
    coords = _sq_coords(cy, cx, RR)
    nfill = len(coords) if fill_frac >= 1.0 else max(3, int(len(coords) * fill_frac))
    fillset = coords if nfill >= len(coords) else rng.sample(coords, nfill)
    for r, c in fillset:
        g[r][c] = rng.choice(palette)
    return g


def _read_sqring(g):
    h, w = dims(g); cy, cx = h // 2, w // 2
    mk = g[cy][cx]
    R = 0
    for r in range(h):
        for c in range(w):
            if g[r][c] != 0 and (r, c) != (cy, cx):
                R = max(R, max(abs(r - cy), abs(c - cx)))
    if R == 0:
        R = max(2, min(cy, cx, h - 1 - cy, w - 1 - cx))
    coords = _sq_coords(cy, cx, R)
    cols = [g[r][c] for r, c in coords]
    return mk, cy, cx, R, coords, cols


def _write_sqring(h, w, cy, cx, mk, coords, cols):
    g = blank(h, w); g[cy][cx] = mk
    for (r, c), v in zip(coords, cols):
        if v and 0 <= r < h and 0 <= c < w:
            g[r][c] = v
    return g


def gi_sqring_plain(rng):
    return _sqring_build(rng)


def tf_sqring_cw(g):
    mk, cy, cx, R, coords, cols = _read_sqring(g)
    new = [cols[-1]] + cols[:-1]
    h, w = dims(g)
    return _write_sqring(h, w, cy, cx, mk, coords, new)
rule("square_ring_step_clockwise", "Every object on the square ring around the centre marker moves one step clockwise along the border.", gi_sqring_plain, tf_sqring_cw)


def tf_sqring_ccw(g):
    mk, cy, cx, R, coords, cols = _read_sqring(g)
    new = cols[1:] + cols[:1]
    h, w = dims(g)
    return _write_sqring(h, w, cy, cx, mk, coords, new)
rule("square_ring_step_counterclockwise", "Every object on the square ring around the centre marker moves one step counterclockwise along the border.", gi_sqring_plain, tf_sqring_ccw)


def gi_sqring_digit(rng):
    return _sqring_build(rng)


def tf_sqring_rotate_digit(g):
    mk, cy, cx, R, coords, cols = _read_sqring(g)
    n = len(cols)
    steps = mk % n
    if steps == 0:
        steps = 1
    new = cols[-steps:] + cols[:-steps]
    h, w = dims(g)
    return _write_sqring(h, w, cy, cx, mk, coords, new)
rule("square_ring_rotate_by_centre_digit", "The square ring rotates clockwise by a number of steps equal to the centre marker's digit value.", gi_sqring_digit, tf_sqring_rotate_digit, digits=True)


def tf_sqring_contract(g):
    mk, cy, cx, R, coords, cols = _read_sqring(g)
    if R < 2:
        return None
    h, w = dims(g)
    out = blank(h, w); out[cy][cx] = mk
    for (r, c), v in zip(coords, cols):
        if not v:
            continue
        nr = cy + round((r - cy) * (R - 1) / R)
        nc = cx + round((c - cx) * (R - 1) / R)
        if 0 <= nr < h and 0 <= nc < w:
            out[nr][nc] = v
    return out
rule("square_ring_contract_one_step", "The square ring of objects contracts one step toward the centre marker.", gi_sqring_plain, tf_sqring_contract)


def gi_sqring_room(rng):
    return _sqring_build(rng, margin=1)


def tf_sqring_expand(g):
    mk, cy, cx, R, coords, cols = _read_sqring(g)
    h, w = dims(g)
    out = blank(h, w); out[cy][cx] = mk
    for (r, c), v in zip(coords, cols):
        if not v:
            continue
        nr = cy + round((r - cy) * (R + 1) / R)
        nc = cx + round((c - cx) * (R + 1) / R)
        if 0 <= nr < h and 0 <= nc < w:
            out[nr][nc] = v
        else:
            out[r][c] = v
    return out
rule("square_ring_expand_one_step", "The square ring of objects expands one step outward away from the centre marker.", gi_sqring_room, tf_sqring_expand)


def tf_sqring_reflect_v(g):
    mk, cy, cx, R, coords, cols = _read_sqring(g)
    idx = {rc: i for i, rc in enumerate(coords)}
    new = cols[:]
    for i, (r, c) in enumerate(coords):
        j = idx.get((r, 2 * cx - c))
        if j is not None:
            new[i] = cols[j]
    h, w = dims(g)
    return _write_sqring(h, w, cy, cx, mk, coords, new)
rule("square_ring_reflect_vertical_axis", "The square ring of objects is reflected left to right across the vertical axis through the centre marker.", gi_sqring_plain, tf_sqring_reflect_v)


def gi_sqring_gap(rng):
    g = _sqring_build(rng, fill_frac=1.0)
    h, w = dims(g); mk, cy, cx, R, coords, cols = _read_sqring(g)
    i = rng.randrange(len(cols)); cols[i] = 0
    return _write_sqring(h, w, cy, cx, mk, coords, cols)


def tf_sqring_fill_gap(g):
    mk, cy, cx, R, coords, cols = _read_sqring(g)
    if 0 not in cols:
        return None
    i = cols.index(0); cols[i] = mk
    h, w = dims(g)
    return _write_sqring(h, w, cy, cx, mk, coords, cols)
rule("square_ring_fill_single_gap", "The one empty position on the square ring is filled with the centre marker's colour.", gi_sqring_gap, tf_sqring_fill_gap)


def tf_sqring_alternate(g):
    mk, cy, cx, R, coords, cols = _read_sqring(g)
    other = next((v for v in cols if v and v != mk), None)
    if other is None:
        return None
    new = [mk if i % 2 == 0 else other for i in range(len(cols))]
    h, w = dims(g)
    return _write_sqring(h, w, cy, cx, mk, coords, new)
rule("square_ring_alternate_from_corner", "Starting at the top-left corner, the square ring alternates between the centre's colour and one other colour going clockwise.", gi_sqring_plain, tf_sqring_alternate)


def tf_sqring_corners(g):
    mk, cy, cx, R, coords, cols = _read_sqring(g)
    idx = {rc: i for i, rc in enumerate(coords)}
    top, bot, left, right = cy - R, cy + R, cx - R, cx + R
    corners = [(top, left), (top, right), (bot, right), (bot, left)]
    changed = False
    for rc in corners:
        i = idx.get(rc)
        if i is not None and cols[i] != mk:
            cols[i] = mk; changed = True
    if not changed:
        return None
    h, w = dims(g)
    return _write_sqring(h, w, cy, cx, mk, coords, cols)
rule("square_ring_corners_recoloured", "The four corner objects of the square ring are recoloured to the centre marker's colour.", gi_sqring_plain, tf_sqring_corners)


def tf_sqring_swap_corners(g):
    mk, cy, cx, R, coords, cols = _read_sqring(g)
    idx = {rc: i for i, rc in enumerate(coords)}
    top, bot, left, right = cy - R, cy + R, cx - R, cx + R
    tl, tr, br, bl = idx[(top, left)], idx[(top, right)], idx[(bot, right)], idx[(bot, left)]
    cols[tl], cols[br] = cols[br], cols[tl]
    cols[tr], cols[bl] = cols[bl], cols[tr]
    h, w = dims(g)
    return _write_sqring(h, w, cy, cx, mk, coords, cols)
rule("square_ring_swap_opposite_corners", "The square ring's opposite corner objects swap colours with each other.", gi_sqring_plain, tf_sqring_swap_corners)


# ---------- scatter: dots at arbitrary angles around a plus-shaped centre marker ----------
def _scatter_build(rng, k=None, large_frac=0.32, same_colour=False):
    n = _size(rng, large_frac); h = w = n
    cy, cx = h // 2, w // 2
    g = blank(h, w)
    mk = rng.choice(range(1, 10))
    for dr, dc in [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]:
        g[cy + dr][cx + dc] = mk
    kk = k or rng.randint(5, 9)
    R = max(3, min(cy, cx, h - 1 - cy, w - 1 - cx) - 1)
    pool = [c for c in range(1, 10) if c != mk]
    dotcol = rng.choice(pool)
    angs = rng.sample(range(0, 360, 5), kk)
    used = {(cy, cx)}
    placed = 0
    for ang in angs:
        rad = math.radians(ang)
        r = cy + round(-R * math.cos(rad)); c = cx + round(R * math.sin(rad))
        if not (0 <= r < h and 0 <= c < w) or (r, c) in used or abs(r - cy) <= 1 and abs(c - cx) <= 1:
            continue
        used.add((r, c))
        g[r][c] = dotcol if same_colour else rng.choice(pool)
        placed += 1
    if placed < 4:
        return None
    return g


def _read_scatter(g):
    h, w = dims(g)
    comps = components(g, lambda v: v != 0)
    mkcomp = next((c for c in comps if len(c) > 1), None)
    if mkcomp is None:
        return None
    mk = g[mkcomp[0][0]][mkcomp[0][1]]
    rs = [r for r, _ in mkcomp]; cs = [c for _, c in mkcomp]
    cy = sum(rs) // len(rs); cx = sum(cs) // len(cs)
    pts = []
    for comp in comps:
        if comp is mkcomp or len(comp) != 1:
            continue
        r, c = comp[0]
        dr, dc = r - cy, c - cx
        ang = math.degrees(math.atan2(dc, -dr)) % 360
        pts.append((ang, r, c, g[r][c]))
    if len(pts) < 2:
        return None
    return mk, cy, cx, pts


def gi_scatter_plain(rng):
    return _scatter_build(rng)


def tf_scatter_row(g):
    res = _read_scatter(g)
    if res is None:
        return None
    mk, cy, cx, pts = res
    pts.sort(key=lambda p: p[0])
    return [[p[3] for p in pts]]
rule("scatter_dots_sorted_by_angle_row", "Output one row listing the scattered dots' colours in clockwise angular order starting at twelve o'clock.", gi_scatter_plain, tf_scatter_row)


def tf_scatter_quadrant_recolour(g):
    res = _read_scatter(g)
    if res is None:
        return None
    mk, cy, cx, pts = res
    out = copy(g)
    table = [c for c in range(1, 10) if c != mk][:4]
    for ang, r, c, col in pts:
        q = int(ang // 90) % 4
        out[r][c] = table[q]
    return out
rule("scatter_dots_recolour_by_quadrant", "Each scattered dot is recoloured according to which quarter-turn quadrant of angle from the centre marker it falls in.", gi_scatter_plain, tf_scatter_quadrant_recolour)


def tf_scatter_delete_top(g):
    res = _read_scatter(g)
    if res is None:
        return None
    mk, cy, cx, pts = res
    best = min(pts, key=lambda p: min(p[0], 360 - p[0]))
    out = copy(g); out[best[1]][best[2]] = 0
    return out
rule("scatter_dots_delete_topmost", "The scattered dot closest to the twelve o'clock direction from the centre marker is deleted.", gi_scatter_plain, tf_scatter_delete_top)


def tf_scatter_swap_opposite(g):
    res = _read_scatter(g)
    if res is None:
        return None
    mk, cy, cx, pts = res
    best = None; bestd = None
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            d = abs(((pts[i][0] - pts[j][0]) % 360) - 180)
            if bestd is None or d < bestd:
                bestd = d; best = (i, j)
    if best is None:
        return None
    i, j = best
    out = copy(g)
    out[pts[i][1]][pts[i][2]] = pts[j][3]
    out[pts[j][1]][pts[j][2]] = pts[i][3]
    return out
rule("scatter_dots_swap_diametric_opposite", "The two scattered dots whose angles from the centre marker are closest to opposite swap colours.", gi_scatter_plain, tf_scatter_swap_opposite)


def tf_scatter_reflect_v(g):
    res = _read_scatter(g)
    if res is None:
        return None
    mk, cy, cx, pts = res
    h, w = dims(g)
    out = blank(h, w)
    for dr, dc in [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]:
        out[cy + dr][cx + dc] = mk
    for ang, r, c, col in pts:
        nc = 2 * cx - c
        if 0 <= nc < w:
            out[r][nc] = col
        else:
            out[r][c] = col
    return out
rule("scatter_dots_reflect_vertical_axis", "The scattered dots around the centre marker are reflected left to right across the vertical axis.", gi_scatter_plain, tf_scatter_reflect_v)


def gi_scatter_even(rng):
    n = _size(rng, 0.32); h = w = n
    cy, cx = h // 2, w // 2
    g = blank(h, w)
    mk = rng.choice(range(1, 10))
    for dr, dc in [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]:
        g[cy + dr][cx + dc] = mk
    k = rng.randint(5, 10)
    R = max(3, min(cy, cx, h - 1 - cy, w - 1 - cx) - 1)
    pool = [c for c in range(1, 10) if c != mk]
    dotcol = rng.choice(pool)
    step = 360 / k
    skip = rng.randrange(k)
    coords = []
    for i in range(k):
        if i == skip:
            continue
        rad = math.radians(i * step)
        r = cy + round(-R * math.cos(rad)); c = cx + round(R * math.sin(rad))
        if not (0 <= r < h and 0 <= c < w) or (abs(r - cy) <= 1 and abs(c - cx) <= 1):
            return None
        coords.append((r, c))
    if len(set(coords)) != len(coords):
        return None
    for r, c in coords:
        g[r][c] = dotcol
    return g


def tf_scatter_restore_missing(g):
    res = _read_scatter(g)
    if res is None:
        return None
    mk, cy, cx, pts = res
    pts.sort(key=lambda p: p[0])
    n = len(pts)
    gaps = [((pts[(i + 1) % n][0] - pts[i][0]) % 360, i) for i in range(n)]
    gaps.sort(reverse=True)
    biggap, i = gaps[0]
    normal = sorted(g for g, _ in gaps)[1] if n > 1 else biggap
    if biggap < normal * 1.5:
        return None
    missing_ang = (pts[i][0] + biggap / 2) % 360
    rs = [p[1] for p in pts]; cs = [p[2] for p in pts]
    R = sum(max(abs(r - cy), abs(c - cx)) for r, c in zip(rs, cs)) / n
    rad = math.radians(missing_ang)
    r = cy + round(-R * math.cos(rad)); c = cx + round(R * math.sin(rad))
    h, w = dims(g)
    if not (0 <= r < h and 0 <= c < w):
        return None
    out = copy(g); out[r][c] = pts[0][3]
    return out
rule("scatter_dots_fill_missing_evenly_spaced", "Dots are evenly spaced around the centre marker with one missing; the missing dot is restored.", gi_scatter_even, tf_scatter_restore_missing)


def gi_scatter_arc(rng):
    n = _size(rng, 0.32); h = w = n
    cy, cx = h // 2, w // 2
    g = blank(h, w)
    mk = rng.choice(range(1, 10))
    for dr, dc in [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]:
        g[cy + dr][cx + dc] = mk
    k = rng.randint(7, 10)
    R = max(3, min(cy, cx, h - 1 - cy, w - 1 - cx) - 1)
    pool = [c for c in range(1, 10) if c != mk]
    basecol, tagcol = rng.sample(pool, 2)
    step = 360 / k
    a = rng.randrange(k); d = rng.choice([3, 4]); b = (a + d) % k
    placed = 0
    for i in range(k):
        rad = math.radians(i * step)
        r = cy + round(-R * math.cos(rad)); c = cx + round(R * math.sin(rad))
        if not (0 <= r < h and 0 <= c < w) or (abs(r - cy) <= 1 and abs(c - cx) <= 1):
            return None
        g[r][c] = tagcol if i in (a, b) else basecol
        placed += 1
    return g if placed == k else None


def tf_scatter_arc_fill(g):
    res = _read_scatter(g)
    if res is None:
        return None
    mk, cy, cx, pts = res
    pts.sort(key=lambda p: p[0])
    n = len(pts)
    cnt = {}
    for p in pts:
        cnt[p[3]] = cnt.get(p[3], 0) + 1
    tagcol = next((v for v, c in cnt.items() if c == 2), None)
    if tagcol is None:
        return None
    idxs = [i for i, p in enumerate(pts) if p[3] == tagcol]
    a, b = idxs
    f = (b - a) % n
    if f <= n - f:
        between = [(a + k) % n for k in range(1, f)]
    else:
        between = [(b + k) % n for k in range(1, n - f)]
    if not between:
        return None
    out = copy(g)
    for i in between:
        out[pts[i][1]][pts[i][2]] = tagcol
    return out
rule("scatter_dots_arc_fill_between_marked", "The shorter arc of dots between the two tagged dots is recoloured to the tag colour.", gi_scatter_arc, tf_scatter_arc_fill)


def tf_scatter_nearest_pair(g):
    res = _read_scatter(g)
    if res is None:
        return None
    mk, cy, cx, pts = res
    best = None; bestd = None
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            d = min(abs(pts[i][0] - pts[j][0]), 360 - abs(pts[i][0] - pts[j][0]))
            if bestd is None or d < bestd:
                bestd = d; best = (i, j)
    if best is None:
        return None
    i, j = best
    out = copy(g)
    out[pts[i][1]][pts[i][2]] = mk
    out[pts[j][1]][pts[j][2]] = mk
    return out
rule("scatter_dots_nearest_pair_connected", "The two scattered dots closest together by angle from the centre marker are both recoloured to the centre's colour.", gi_scatter_plain, tf_scatter_nearest_pair)


def gi_scatter_rank(rng):
    return _scatter_build(rng, k=rng.randint(3, 9))


def tf_scatter_rank(g):
    res = _read_scatter(g)
    if res is None:
        return None
    mk, cy, cx, pts = res
    pts.sort(key=lambda p: p[0])
    out = copy(g)
    for rank, (ang, r, c, col) in enumerate(pts, start=1):
        out[r][c] = rank
    return out
rule("scatter_dots_angle_rank_recolour", "Each scattered dot is recoloured to its rank number in clockwise angular order from twelve o'clock.", gi_scatter_rank, tf_scatter_rank, digits=True)


def tf_scatter_quadrant_bar(g):
    res = _read_scatter(g)
    if res is None:
        return None
    mk, cy, cx, pts = res
    counts = [0, 0, 0, 0]
    for ang, r, c, col in pts:
        counts[int(ang // 90) % 4] += 1
    maxc = max(counts)
    if maxc == 0:
        return None
    out = blank(maxc, 4)
    for qi, cnt in enumerate(counts):
        for rr in range(maxc - cnt, maxc):
            out[rr][qi] = mk
    return out
rule("scatter_dots_count_per_quadrant_bar", "Output a four-column bar chart counting how many scattered dots fall in each quadrant around the centre marker.", gi_scatter_plain, tf_scatter_quadrant_bar)


def tf_ring8_rotate3(g):
    mk, cy, cx, R, pos, cols = _read_ring8(g)
    new = cols[-3:] + cols[:-3]
    h, w = dims(g)
    return _write_ring8(h, w, cy, cx, mk, pos, new)
rule("ring8_rotate_three_steps_clockwise", "The ring rotates clockwise by exactly three positions.", gi_ring8_plain, tf_ring8_rotate3)


def tf_scatter_farthest_from_marker_deleted(g):
    res = _read_scatter(g)
    if res is None:
        return None
    mk, cy, cx, pts = res
    best = max(pts, key=lambda p: (p[1] - cy) ** 2 + (p[2] - cx) ** 2)
    out = copy(g); out[best[1]][best[2]] = 0
    return out
rule("scatter_dots_delete_farthest_from_marker", "The scattered dot farthest from the centre marker is deleted.", gi_scatter_plain, tf_scatter_farthest_from_marker_deleted)
