# b014_lattices.py -- lines, lattices and intersections: a lattice of full lines divides the grid into cells
# (fill, copy, count, shrink to pixels, expand from pixels); intersections (recolour, punch, X vs T, keep only);
# crossings of two colour families (horizontal wins / vertical wins / key); segments that extend, grow, turn,
# thicken, get their endpoints marked; regular lattices repaired or subdivided; parallel pairs filled.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


# ---------------------------------------------------------------- local helpers
def _hw(rng, lo=8, hi=20):
    """Grid size with 40% of draws in the 21-30 band."""
    if rng.random() < 0.4:
        return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _lines(rng, n, k_lo, k_hi, gap=2):
    """k sorted line positions in 0..n-1 leaving at least `gap` cells between lines and to both edges."""
    k_hi = max(k_lo, min(k_hi, (n - 2) // (gap + 1)))
    if n - 2 * gap < k_lo:
        return None
    for _ in range(60):
        k = rng.randint(k_lo, k_hi)
        pos = sorted(rng.sample(range(gap, n - gap), k))
        if all(b - a > gap for a, b in zip(pos, pos[1:])):
            return pos
    return None


def _lattice(rng, h, w, col, k=(1, 6), gap=2, kc=None):
    rows = _lines(rng, h, k[0], k[1], gap); cols = _lines(rng, w, *(kc or k), gap)
    if rows is None or cols is None:
        return None
    g = blank(h, w)
    for r in rows:
        g[r] = [col] * w
    for c in cols:
        for r in range(h):
            g[r][c] = col
    return g, rows, cols


def _regular(rng, col, p_lo=3, p_hi=6):
    """Regular lattice: period p, every cell (p-1) square including the edge cells. 40% of draws 21-30 a side."""
    p = rng.randint(p_lo, p_hi); kmax = 31 // p
    def pick():
        return rng.randint(max(2, -(-22 // p)), kmax) if rng.random() < 0.4 else rng.randint(2, kmax)
    h, w = pick() * p - 1, pick() * p - 1
    rows = list(range(p - 1, h, p)); cols = list(range(p - 1, w, p))
    g = blank(h, w)
    for r in rows:
        g[r] = [col] * w
    for c in cols:
        for r in range(h):
            g[r][c] = col
    return g, rows, cols


def _full(g):
    """(colour, rows, cols) of the full uniform non-zero lines, or None."""
    h, w = dims(g)
    rows = [r for r in range(h) if g[r][0] and all(v == g[r][0] for v in g[r])]
    cols = [c for c in range(w) if g[0][c] and all(g[r][c] == g[0][c] for r in range(h))]
    if not rows and not cols:
        return None
    return (g[rows[0]][0] if rows else g[0][cols[0]]), rows, cols


def _cells(h, w, rows, cols):
    """Lattice cells as (i, j, r0, c0, r1, c1)."""
    rb = [-1] + rows + [h]; cb = [-1] + cols + [w]
    return [(i, j, rb[i] + 1, cb[j] + 1, rb[i + 1] - 1, cb[j + 1] - 1)
            for i in range(len(rb) - 1) for j in range(len(cb) - 1)]


def _interior(cell):
    _, _, r0, c0, r1, c1 = cell
    return [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)]


def _fillcell(g, cell, col):
    rect(g, *cell[2:], col); return g


def _content(g, cell, L):
    return [(r, c, g[r][c]) for r, c in _interior(cell) if g[r][c] and g[r][c] != L]


def _not(rng, *ex):
    return rng.choice([c for c in COLOURS if c not in ex])


def _retry(fn, rng, n=40):
    for _ in range(n):
        g = fn(rng)
        if g is not None:
            return g
    return None


def _segments(rng, h, w, k_lo, k_hi, len_lo, len_hi, exclude=(), unique_axis=False):
    """Straight non-touching segments of random colours; at most one per row / column if unique_axis."""
    g = blank(h, w); taken = set(); used_r, used_c = set(), set(); n = 0
    for _ in range(rng.randint(k_lo, k_hi) * 25):
        if n >= k_hi:
            break
        col = _not(rng, 0, *exclude); L = rng.randint(len_lo, len_hi)
        if rng.random() < 0.5:
            if L > w: continue
            r, c = rng.randrange(h), rng.randint(0, w - L); cs = [(r, c + i) for i in range(L)]
            if unique_axis and r in used_r: continue
        else:
            if L > h: continue
            r, c = rng.randint(0, h - L), rng.randrange(w); cs = [(r + i, c) for i in range(L)]
            if unique_axis and c in used_c: continue
        if set(cs) & taken:
            continue
        taken |= {(y + a, x + b) for y, x in cs for a in (-1, 0, 1) for b in (-1, 0, 1)}
        used_r.add(r); used_c.add(c)
        for y, x in cs:
            g[y][x] = col
        n += 1
        if n >= rng.randint(k_lo, k_hi):
            break
    return g if n >= k_lo else None


# 1 a cell holding one dot is filled with the dot's colour.
def gi_cellfill(rng):
    h, w = _hw(rng); L = rng.choice(COLOURS); lat = _lattice(rng, h, w, L)
    if lat is None: return None
    g, rows, cols = lat; cs = _cells(h, w, rows, cols)
    for cell in rng.sample(cs, rng.randint(1, max(1, len(cs) // 2))):
        r, c = rng.choice(_interior(cell)); g[r][c] = _not(rng, L)
    return g
def tf_cellfill(g):
    f = _full(g)
    if f is None: return None
    L, rows, cols = f; h, w = dims(g); out = copy(g)
    for cell in _cells(h, w, rows, cols):
        ct = _content(g, cell, L)
        if len(ct) == 1: _fillcell(out, cell, ct[0][2])
    return out
rule("lattice_cell_filled_by_its_dot", "Full lines divide the grid into cells; every cell that holds a single dot is filled entirely with that dot's colour.", gi_cellfill, tf_cellfill)


# 2 intersections of the lattice turn colour 2.
def gi_inter(rng):
    h, w = _hw(rng); lat = _lattice(rng, h, w, _not(rng, 2))
    return lat[0] if lat else None
def tf_inter(g):
    f = _full(g)
    if f is None: return None
    L, rows, cols = f; out = copy(g)
    for r in rows:
        for c in cols: out[r][c] = 2
    return out
rule("lattice_intersections_recoloured", "Every cell where a horizontal line crosses a vertical line is recoloured 2; the rest of the lines stay.", gi_inter, tf_inter)


# 3 count the vertical segments crossing each horizontal line -> one bar per line.
def gi_xbars(rng):
    h, w = _hw(rng); V = rng.choice(COLOURS); rows = _lines(rng, h, 2, 5, 2)
    if rows is None: return None
    g = blank(h, w)
    for r, col in zip(rows, colours(rng, len(rows), exclude=(0, V))): g[r] = [col] * w
    cols = _lines(rng, w, 1, min(5, w // 3 - 1), 1)
    if cols is None: return None
    for c in cols:
        a, b = sorted(rng.sample(range(h), 2))
        for r in range(a, b + 1): g[r][c] = V
    return g
def tf_xbars(g):
    h, w = dims(g); bars = []
    for r in range(h):
        if all(g[r]):
            cnt = counts([g[r]]); col = max(cnt, key=cnt.get); bars.append((col, w - cnt[col]))
    m = max(k for _, k in bars) if bars else 0
    if m == 0: return None
    return [[col] * k + [0] * (m - k) for col, k in bars]
rule("crossings_per_horizontal_line_bars", "Output one row per full horizontal line, top to bottom: a bar of its colour as long as the number of vertical segments that cross it.", gi_xbars, tf_xbars)


# 4 a lattice with cells knocked out of its lines is completed.
def gi_broken(rng):
    h, w = _hw(rng); L = rng.choice(COLOURS); lat = _lattice(rng, h, w, L)
    if lat is None: return None
    g, rows, cols = lat
    for r in rows:
        for c in rng.sample(range(w), rng.randint(1, w // 5)): g[r][c] = 0
    for c in cols:
        for r in rng.sample(range(h), rng.randint(1, h // 5)): g[r][c] = 0
    return g
def tf_broken(g):
    h, w = dims(g); cnt = counts(g); cnt.pop(0, None)
    if not cnt: return None
    L = max(cnt, key=cnt.get); out = copy(g)
    for r in range(h):
        if sum(v == L for v in g[r]) * 2 > w: out[r] = [L] * w
    for c in range(w):
        if sum(g[r][c] == L for r in range(h)) * 2 > h:
            for r in range(h): out[r][c] = L
    return out
rule("complete_broken_lattice", "The lattice lines have cells missing; every row and column that is mostly line colour is completed into a full line.", gi_broken, tf_broken)


# 5/6 two colour families cross; the crossing takes the horizontal (or the vertical) line's colour.
def _two_family(rng, over):
    h, w = _hw(rng); rows = _lines(rng, h, 1, 4, 2); cols = _lines(rng, w, 1, 4, 2)
    if rows is None or cols is None: return None
    cs = colours(rng, len(rows) + len(cols)); g = blank(h, w)
    def draw_rows():
        for r, col in zip(rows, cs[:len(rows)]): g[r] = [col] * w
    def draw_cols():
        for c, col in zip(cols, cs[len(rows):]):
            for r in range(h): g[r][c] = col
    if over == "v": draw_rows(); draw_cols()
    else: draw_cols(); draw_rows()
    return g
def _hwins(g):
    h, w = dims(g); out = copy(g)
    cols = [c for c in range(w) if all(g[r][c] == g[0][c] != 0 for r in range(h))]
    for r in range(h):
        if all(g[r]):
            cnt = counts([g[r]]); col = max(cnt, key=cnt.get)
            for c in cols: out[r][c] = col
    return out
rule("crossings_take_horizontal_colour", "Horizontal and vertical lines each have their own colour; where they cross, the crossing cell takes the horizontal line's colour.",
     lambda rng: _two_family(rng, "v"), _hwins)
rule("crossings_take_vertical_colour", "Horizontal and vertical lines each have their own colour; where they cross, the crossing cell takes the vertical line's colour.",
     lambda rng: _two_family(rng, "h"), lambda g: transpose(_hwins(transpose(g))))


# 7 crossings are left empty; the key cell in the top-left corner says what colour fills them.
def gi_key(rng):
    h, w = _hw(rng); A, B, K = colours(rng, 3); rows = _lines(rng, h, 1, 4, 2); cols = _lines(rng, w, 1, 4, 2)
    if rows is None or cols is None: return None
    g = blank(h, w)
    for r in rows: g[r] = [A] * w
    for c in cols:
        for r in range(h): g[r][c] = B
    for r in rows:
        for c in cols: g[r][c] = 0
    g[0][0] = K
    return g
def tf_key(g):
    h, w = dims(g); K = g[0][0]; out = copy(g)
    rows = [r for r in range(h) if sum(1 for v in g[r] if v) * 2 > w]
    cols = [c for c in range(w) if sum(1 for r in range(h) if g[r][c]) * 2 > h]
    for r in rows:
        for c in cols:
            if g[r][c] == 0: out[r][c] = K
    return out
rule("crossings_take_key_colour", "Lines of two colours cross but their crossing cells are empty; each crossing is filled with the colour of the key cell in the top-left corner.", gi_key, tf_key)


# 8 every segment extends along its own line until it meets another segment or the edge.
def gi_extend(rng):
    h, w = _hw(rng); return _segments(rng, h, w, 3, 7, 2, 6, unique_axis=True)
def tf_extend(g):
    h, w = dims(g); out = copy(g)
    segs = [o for o in components(g, lambda v: v != 0) if len(o) >= 2]
    def ray(r, c, dr, dc, col):
        r, c = r + dr, c + dc
        while 0 <= r < h and 0 <= c < w and g[r][c] == 0:
            out[r][c] = col; r += dr; c += dc
    for horiz in (True, False):
        for o in segs:
            r0, c0, r1, c1 = bbox(o); col = g[r0][c0]
            if (r0 == r1) != horiz: continue
            if horiz: ray(r0, c0, 0, -1, col); ray(r0, c1, 0, 1, col)
            else: ray(r0, c0, -1, 0, col); ray(r1, c0, 1, 0, col)
    return out
rule("segments_extend_to_edge_or_line", "Every straight segment grows in both directions along its own line until it reaches another segment or the grid edge; where extensions cross, the vertical one is on top.", gi_extend, tf_extend)


# 9 a row or column holding two or more dots becomes a full line; lone dots stay.
def gi_twodots(rng):
    h, w = _hw(rng); D = rng.choice(COLOURS); rows = _lines(rng, h, 2, 6, 1); cols = _lines(rng, w, 2, 6, 1)
    if rows is None or cols is None: return None
    g = blank(h, w); pts = [(r, c) for r in rows for c in cols]
    for r, c in rng.sample(pts, rng.randint(2, max(2, len(pts) // 2))): g[r][c] = D
    ks = [sum(g[r][c] == D for c in range(w)) for r in rows] + [sum(g[r][c] == D for r in range(h)) for c in cols]
    return g if any(k >= 2 for k in ks) and any(k == 1 for k in ks) else None
def tf_twodots(g):
    h, w = dims(g); out = copy(g); D = max(v for row in g for v in row)
    for r in range(h):
        if sum(1 for v in g[r] if v) >= 2: out[r] = [D] * w
    for c in range(w):
        if sum(1 for r in range(h) if g[r][c]) >= 2:
            for r in range(h): out[r][c] = D
    return out
rule("two_aligned_dots_draw_a_line", "Any row or column that holds two or more dots is drawn as a full line in the dot colour; a row or column with a single dot is left alone.",
     lambda rng: _retry(gi_twodots, rng), tf_twodots)


# 10 the row and the column with the most coloured cells are drawn in grey.
def gi_busy(rng):
    h, w = _hw(rng); g = blank(h, w)
    return sprinkle(rng, g, int(h * w * rng.uniform(0.12, 0.3)), _not(rng, 5))
def tf_busy(g):
    h, w = dims(g)
    rc = [sum(1 for v in row if v) for row in g]; cc = [sum(1 for r in range(h) if g[r][c]) for c in range(w)]
    if rc.count(max(rc)) != 1 or cc.count(max(cc)) != 1: return None
    out = copy(g); out[rc.index(max(rc))] = [5] * w
    for r in range(h): out[r][cc.index(max(cc))] = 5
    return out
rule("busiest_row_and_column_drawn", "The row with the most coloured cells and the column with the most coloured cells are each drawn as a full grey (5) line over the scatter.", gi_busy, tf_busy)


# 11 full lines are erased, scattered dots stay.
def gi_erase(rng):
    h, w = _hw(rng); L = rng.choice(COLOURS); lat = _lattice(rng, h, w, L)
    if lat is None: return None
    g, rows, cols = lat; free = [(r, c) for r in range(h) for c in range(w) if g[r][c] == 0]
    for r, c in rng.sample(free, rng.randint(3, max(3, len(free) // 6))): g[r][c] = _not(rng, L)
    return g
def tf_erase(g):
    f = _full(g)
    if f is None: return None
    L, rows, cols = f; out = copy(g); h, w = dims(g)
    for r in rows: out[r] = [0] * w
    for c in cols:
        for r in range(h): out[r][c] = 0
    return out
rule("erase_full_lines_keep_scatter", "Every line that spans the whole grid is erased; the scattered dots between the lines are kept.", gi_erase, tf_erase)


# 12 every full line becomes two cells wide (downwards / rightwards).
def gi_thick(rng):
    h, w = _hw(rng); lat = _lattice(rng, h, w, rng.choice(COLOURS), gap=3)
    return lat[0] if lat else None
def tf_thick(g):
    f = _full(g)
    if f is None: return None
    L, rows, cols = f; h, w = dims(g); out = copy(g)
    for r in rows:
        if r + 1 < h: out[r + 1] = [L] * w
    for c in cols:
        for r in range(h):
            if c + 1 < w: out[r][c + 1] = L
    return out
rule("lines_thicken_downward_rightward", "Every full line is thickened to two cells: a horizontal line also fills the row below it, a vertical line the column to its right.", gi_thick, tf_thick)


# 13 a segment ending on a marker turns clockwise there and runs on to the edge.
def gi_turn(rng):
    h, w = _hw(rng); L, M = colours(rng, 2); g = blank(h, w); taken = set(); n = 0; k = rng.randint(1, 4)
    for _ in range(80):
        if n >= k: break
        dr, dc = rng.choice([(0, 1), (0, -1), (1, 0), (-1, 0)]); ln = rng.randint(2, 6); r, c = rng.randrange(h), rng.randrange(w)
        seg = [(r + dr * i, c + dc * i) for i in range(ln)]; mk = (r + dr * ln, c + dc * ln)
        y, x = mk[0] + dc, mk[1] - dr; ray = []
        while 0 <= y < h and 0 <= x < w: ray.append((y, x)); y += dc; x -= dr
        path = seg + [mk] + ray
        if not ray or not all(0 <= y < h and 0 <= x < w for y, x in path) or set(path) & taken: continue
        taken |= {(y + a, x + b) for y, x in path for a in (-1, 0, 1) for b in (-1, 0, 1)}
        for y, x in seg: g[y][x] = L
        g[mk[0]][mk[1]] = M; n += 1
    return g if n else None
def tf_turn(g):
    h, w = dims(g); cnt = counts(g); cnt.pop(0, None)
    if len(cnt) != 2: return None
    L = max(cnt, key=cnt.get); M = min(cnt, key=cnt.get); out = copy(g)
    for r, c in cells(g, lambda v: v == M):
        nb = [(dr, dc) for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)) if 0 <= r + dr < h and 0 <= c + dc < w and g[r + dr][c + dc] == L]
        if len(nb) != 1: return None
        dr, dc = -nb[0][0], -nb[0][1]; y, x = r + dc, c - dr
        while 0 <= y < h and 0 <= x < w and g[y][x] == 0:
            out[y][x] = L; y += dc; x -= dr
    return out
rule("line_turns_clockwise_at_marker", "Each segment ends on a marker cell; from the marker the line continues in its own colour, turned a quarter turn clockwise, until it reaches the grid edge.", gi_turn, tf_turn)


# 14 two parallel full lines of the same colour: the strip between them is filled grey.
def gi_between(rng):
    h, w = _hw(rng); k = rng.randint(1, 3); cs = colours(rng, k, exclude=(0, 5)); pos = _lines(rng, h, 2 * k, 2 * k, 1)
    if pos is None: return None
    g = blank(h, w)
    for i, col in enumerate(cs): g[pos[2 * i]] = [col] * w; g[pos[2 * i + 1]] = [col] * w
    return g if rng.random() < 0.5 else transpose(g)
def _between(g):
    h, w = dims(g); rows = [r for r in range(h) if g[r][0] and all(v == g[r][0] for v in g[r])]
    if not rows: return None
    out = copy(g); by = {}
    for r in rows: by.setdefault(g[r][0], []).append(r)
    for rs in by.values():
        if len(rs) == 2:
            for r in range(rs[0] + 1, rs[1]): out[r] = [5] * w
    return out
def tf_between(g):
    o = _between(g)
    if o is not None: return o
    o = _between(transpose(g)); return transpose(o) if o is not None else None
rule("fill_between_same_colour_line_pairs", "Full lines come in parallel pairs of one colour; the strip between the two lines of each pair is filled grey (5).", gi_between, tf_between)


# 15 regular lattice with one interior line missing: restore it.
def gi_missing(rng):
    h, w = _hw(rng); L = rng.choice(COLOURS); p = rng.randint(3, 7)
    rows = list(range(rng.randint(1, p), h, p)); cols = list(range(rng.randint(1, p), w, p))
    if len(rows) < 3 or len(cols) < 3: return None
    g = blank(h, w)
    for r in rows: g[r] = [L] * w
    if rng.random() < 0.5: g[rng.choice(rows[1:-1])] = [0] * w; skip = None
    else: skip = rng.choice(cols[1:-1])
    for c in cols:
        if c == skip: continue
        for r in range(h): g[r][c] = L
    if skip is not None:
        for r in rows: g[r][skip] = L
    return g
def tf_missing(g):
    f = _full(g)
    if f is None: return None
    L, rows, cols = f; h, w = dims(g); out = copy(g)
    gaps = [b - a for a, b in zip(rows, rows[1:])] + [b - a for a, b in zip(cols, cols[1:])]
    if not gaps: return None
    p = min(gaps)
    for a, b in zip(rows, rows[1:]):
        if b - a == 2 * p: out[(a + b) // 2] = [L] * w
    for a, b in zip(cols, cols[1:]):
        if b - a == 2 * p:
            for r in range(h): out[r][(a + b) // 2] = L
    return out
rule("restore_missing_regular_lattice_line", "The lines form a regular evenly spaced lattice except that one line is missing; the missing line is drawn in.",
     lambda rng: _retry(gi_missing, rng), tf_missing)


# 16 each down-right diagonal line becomes a staircase.
def gi_stair(rng):
    h, w = _hw(rng); g = blank(h, w); taken = set(); n = 0
    for col in colours(rng, rng.randint(1, 4)):
        for _ in range(40):
            ln = rng.randint(3, min(10, h, w)); r, c = rng.randint(0, h - ln), rng.randint(0, w - ln)
            path = [(r + i, c + i) for i in range(ln)] + [(r + i, c + i + 1) for i in range(ln) if c + i + 1 < w]
            if set(path) & taken: continue
            taken |= {(y + a, x + b) for y, x in path for a in (-1, 0, 1) for b in (-1, 0, 1)}
            for i in range(ln): g[r + i][c + i] = col
            n += 1; break
    return g if n else None
def tf_stair(g):
    h, w = dims(g); out = copy(g)
    for r, c in cells(g, lambda v: v != 0):
        if c + 1 < w and g[r][c + 1] == 0: out[r][c + 1] = g[r][c]
    return out
rule("diagonal_lines_become_staircases", "Every diagonal line running down and to the right is turned into a staircase: each of its cells gains a copy of itself in the cell to its right.", gi_stair, tf_stair)


# 17 lattice cells coloured by the parity of their cell-row index.
def gi_rowpar(rng):
    h, w = _hw(rng); lat = _lattice(rng, h, w, _not(rng, 1, 2))
    return lat[0] if lat else None
def tf_rowpar(g):
    f = _full(g)
    if f is None: return None
    L, rows, cols = f; h, w = dims(g); out = copy(g)
    for cell in _cells(h, w, rows, cols): _fillcell(out, cell, 1 if cell[0] % 2 == 0 else 2)
    return out
rule("lattice_cells_by_row_parity", "The lattice cells are filled by row: cells in the first, third, fifth... row of cells become 1 and cells in the even rows become 2.", gi_rowpar, tf_rowpar)


# 18 the one solid cell is copied into every cell of its row.
def gi_fillrow(rng):
    h, w = _hw(rng); L, F = colours(rng, 2); lat = _lattice(rng, h, w, L)
    if lat is None: return None
    g, rows, cols = lat; _fillcell(g, rng.choice(_cells(h, w, rows, cols)), F)
    return g
def tf_fillrow(g):
    f = _full(g)
    if f is None: return None
    L, rows, cols = f; h, w = dims(g); cs = _cells(h, w, rows, cols)
    full = [cell for cell in cs if all(g[r][c] not in (0, L) for r, c in _interior(cell))]
    if len(full) != 1: return None
    i, F = full[0][0], g[full[0][2]][full[0][3]]; out = copy(g)
    for cell in cs:
        if cell[0] == i: _fillcell(out, cell, F)
    return out
rule("filled_lattice_cell_copied_along_row", "Exactly one lattice cell is filled solid; every other cell in the same row of cells is filled with that colour too.", gi_fillrow, tf_fillrow)


# 19 the one patterned cell of a regular lattice is copied down its column of cells.
def gi_patcol(rng):
    L, P = colours(rng, 2); g, rows, cols = _regular(rng, L); h, w = dims(g)
    cell = rng.choice(_cells(h, w, rows, cols)); it = _interior(cell)
    for r, c in rng.sample(it, rng.randint(2, len(it) - 1)): g[r][c] = P
    return g
def tf_patcol(g):
    f = _full(g)
    if f is None: return None
    L, rows, cols = f; h, w = dims(g); cs = _cells(h, w, rows, cols)
    src = [cell for cell in cs if _content(g, cell, L)]
    if len(src) != 1: return None
    s = src[0]; out = copy(g)
    for cell in cs:
        if cell[1] == s[1] and cell != s:
            for r, c, v in _content(g, s, L): out[cell[2] + r - s[2]][cell[3] + c - s[3]] = v
    return out
rule("patterned_lattice_cell_copied_down_column", "In a regular lattice one cell holds a small pattern; the pattern is copied into every other cell of the same column of cells, same position inside the cell.", gi_patcol, tf_patcol)


# 20 lattice cells shrink to pixels: one output cell per lattice cell, coloured by its content.
def gi_pix(rng):
    h, w = _hw(rng); L = rng.choice(COLOURS); lat = _lattice(rng, h, w, L)
    if lat is None: return None
    g, rows, cols = lat; n = 0
    for cell in _cells(h, w, rows, cols):
        if rng.random() < 0.6:
            col = _not(rng, L); it = _interior(cell)
            for r, c in rng.sample(it, rng.randint(1, len(it))): g[r][c] = col
            n += 1
    return g if n else None
def tf_pix(g):
    f = _full(g)
    if f is None: return None
    L, rows, cols = f; h, w = dims(g); out = blank(len(rows) + 1, len(cols) + 1)
    for cell in _cells(h, w, rows, cols):
        vs = {v for _, _, v in _content(g, cell, L)}
        if len(vs) > 1: return None
        if vs: out[cell[0]][cell[1]] = vs.pop()
    return out
rule("lattice_cells_to_pixels", "Output one cell per lattice cell, in the same arrangement: the colour of whatever the cell contains, or empty if the cell is empty.", gi_pix, tf_pix)


# 21 the reverse: each pixel becomes a 3x3 cell of a grey-lined lattice.
def gi_expand(rng):
    h, w = rng.randint(2, 7), rng.randint(2, 7); g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.6: g[r][c] = _not(rng, 5)
    return g if len({v for row in g for v in row}) >= 2 else None
def tf_expand(g):
    h, w = dims(g); out = blank(4 * h - 1, 4 * w - 1, 5)
    for r in range(h):
        for c in range(w): rect(out, 4 * r, 4 * c, 4 * r + 2, 4 * c + 2, g[r][c])
    return out
rule("pixels_expand_into_lattice_cells", "Every input cell becomes a 3 by 3 block of its colour, the blocks separated by one-cell grey (5) lattice lines.", gi_expand, tf_expand)


# 22 count horizontal and vertical lines -> two bars.
def gi_lcount(rng):
    h, w = _hw(rng); A, B = colours(rng, 2); rows = _lines(rng, h, 1, 6, 1); cols = _lines(rng, w, 1, 6, 1)
    if rows is None or cols is None: return None
    g = blank(h, w)
    for r in rows: g[r] = [A] * w
    for c in cols:
        for r in range(h): g[r][c] = B
    return g
def tf_lcount(g):
    h, w = dims(g)
    cols = [c for c in range(w) if all(g[r][c] == g[0][c] != 0 for r in range(h))]; rows = [r for r in range(h) if all(g[r])]
    if not rows or not cols: return None
    cnt = counts([g[rows[0]]]); A = max(cnt, key=cnt.get); B = g[0][cols[0]]; m = max(len(rows), len(cols))
    return [[A] * len(rows) + [0] * (m - len(rows)), [B] * len(cols) + [0] * (m - len(cols))]
rule("line_counts_two_bars", "Output two rows: the top one a bar in the horizontal lines' colour as long as the number of horizontal lines, the bottom one likewise for the vertical lines.", gi_lcount, tf_lcount)


# 23 each dot moves to the top-left corner of its lattice cell.
def gi_corner(rng):
    h, w = _hw(rng); L = rng.choice(COLOURS); lat = _lattice(rng, h, w, L)
    if lat is None: return None
    g, rows, cols = lat; cs = _cells(h, w, rows, cols); moved = 0
    for cell in rng.sample(cs, rng.randint(1, len(cs))):
        it = _interior(cell); r, c = rng.choice(it); g[r][c] = _not(rng, L); moved += (r, c) != it[0]
    return g if moved else None
def tf_corner(g):
    f = _full(g)
    if f is None: return None
    L, rows, cols = f; h, w = dims(g); out = copy(g)
    for cell in _cells(h, w, rows, cols):
        ct = _content(g, cell, L)
        if len(ct) == 1:
            r, c, v = ct[0]; out[r][c] = 0; out[cell[2]][cell[3]] = v
    return out
rule("lattice_dots_to_cell_corner", "Each dot inside a lattice cell moves to the top-left corner of its own cell.", gi_corner, tf_corner)


# 24 the row of cells holding the most dots is filled solid.
def gi_busyrow(rng):
    h, w = _hw(rng); L, D = colours(rng, 2); lat = _lattice(rng, h, w, L)
    if lat is None: return None
    g, rows, cols = lat; free = [(r, c) for r in range(h) for c in range(w) if g[r][c] == 0]
    for r, c in rng.sample(free, rng.randint(2, max(2, len(free) // 8))): g[r][c] = D
    return g
def tf_busyrow(g):
    f = _full(g)
    if f is None: return None
    L, rows, cols = f; h, w = dims(g); cs = _cells(h, w, rows, cols); cnt = [0] * (len(rows) + 1); D = set()
    for cell in cs:
        ct = _content(g, cell, L); cnt[cell[0]] += len(ct); D |= {v for _, _, v in ct}
    if len(D) != 1 or cnt.count(max(cnt)) != 1: return None
    out = copy(g); i = cnt.index(max(cnt)); D = D.pop()
    for cell in cs:
        if cell[0] == i: _fillcell(out, cell, D)
    return out
rule("lattice_busiest_cell_row_filled", "Dots are scattered in the lattice cells; the row of cells that holds the most dots has all its cells filled solid with the dot colour.", gi_busyrow, tf_busyrow)


# 25 the intersections are punched out.
def gi_punch(rng):
    h, w = _hw(rng); L = rng.choice(COLOURS); lat = _lattice(rng, h, w, L)
    if lat is None: return None
    g, rows, cols = lat; free = [(r, c) for r in range(h) for c in range(w) if g[r][c] == 0]
    for r, c in rng.sample(free, rng.randint(0, 4)): g[r][c] = _not(rng, L)
    return g
def tf_punch(g):
    f = _full(g)
    if f is None: return None
    L, rows, cols = f; out = copy(g)
    for r in rows:
        for c in cols: out[r][c] = 0
    return out
rule("punch_lattice_intersections", "Every cell where two full lines cross is emptied, leaving the lines broken at their intersections.", gi_punch, tf_punch)


# 26 crossings (four arms) become 2, T-junctions (three arms) become 3.
def gi_tee(rng):
    h, w = _hw(rng); L = _not(rng, 2, 3); lat = _lattice(rng, h, w, L, k=(1, 4), gap=3)
    if lat is None: return None
    g, rows, cols = lat; rb = [-1] + rows + [h]; cb = [-1] + cols + [w]; used_c, used_r = set(cols), set(rows)
    for _ in range(rng.randint(1, 5)):
        if rng.random() < 0.5:
            i = rng.randrange(len(rb) - 1); c = rng.randrange(w)
            if any(abs(c - x) < 2 for x in used_c): continue
            used_c.add(c)
            for r in range(max(rb[i], 0), min(rb[i + 1], h - 1) + 1): g[r][c] = L
        else:
            j = rng.randrange(len(cb) - 1); r = rng.randrange(h)
            if any(abs(r - x) < 2 for x in used_r): continue
            used_r.add(r)
            for c in range(max(cb[j], 0), min(cb[j + 1], w - 1) + 1): g[r][c] = L
    return g
def tf_tee(g):
    h, w = dims(g); out = copy(g)
    for r, c in cells(g, lambda v: v != 0):
        n = sum(1 for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)) if 0 <= r + dr < h and 0 <= c + dc < w and g[r + dr][c + dc] == g[r][c])
        if n == 4: out[r][c] = 2
        elif n == 3: out[r][c] = 3
    return out
rule("mark_crossings_and_tee_junctions", "Where two lines cross through each other (four arms) the cell becomes 2; where a line ends on another line (three arms) the junction becomes 3.", gi_tee, tf_tee)


# 27 the two end cells of every segment are marked.
def gi_ends(rng):
    h, w = _hw(rng); return _segments(rng, h, w, 2, 6, 3, 9, exclude=(4,))
def tf_ends(g):
    h, w = dims(g); out = copy(g)
    for r, c in cells(g, lambda v: v != 0):
        n = sum(1 for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)) if 0 <= r + dr < h and 0 <= c + dc < w and g[r + dr][c + dc] == g[r][c])
        if n == 1: out[r][c] = 4
    return out
rule("segment_endpoints_marked", "The two end cells of every straight segment are recoloured 4; the middle of each segment keeps its colour.", gi_ends, tf_ends)


# 28 down-right diagonals of one colour cross down-left diagonals of another; crossings become grey.
def gi_diagx(rng):
    h, w = _hw(rng); A, B = colours(rng, 2, exclude=(0, 5)); g = blank(h, w)
    def dlen(d): return min(h - 1, w - 1 - d) - max(0, -d) + 1
    def slen(s): return min(h - 1, s) - max(0, s - (w - 1)) + 1
    ds = [d for d in range(-(h - 1), w) if dlen(d) >= 8]; ss = [s for s in range(h + w - 1) if slen(s) >= 4]
    if not ds or not ss: return None
    for d in rng.sample(ds, rng.randint(1, min(3, len(ds)))):
        for r in range(h):
            if 0 <= r + d < w: g[r][r + d] = A
    for s in rng.sample(ss, rng.randint(1, min(3, len(ss)))):
        for r in range(h):
            if 0 <= s - r < w: g[r][s - r] = B
    return g
def tf_diagx(g):
    h, w = dims(g); cnt = counts(g); cnt.pop(0, None)
    if len(cnt) != 2: return None
    da = sb = None
    for X in cnt:
        pts = cells(g, lambda v: v == X); d = {c - r for r, c in pts}; s = {c + r for r, c in pts}
        if len(d) <= 3 and len(s) > 3: da = d
        elif len(s) <= 3 and len(d) > 3: sb = s
    if da is None or sb is None: return None
    out = copy(g)
    for r in range(h):
        for c in range(w):
            if (c - r) in da and (c + r) in sb: out[r][c] = 5
    return out
rule("diagonal_crossings_marked", "Diagonal lines of one colour run down-right and lines of another colour run down-left; every cell where two of them cross becomes grey (5).", gi_diagx, tf_diagx)


# 29 lattice cells filled in a checkerboard.
def gi_check(rng):
    h, w = _hw(rng); lat = _lattice(rng, h, w, _not(rng, 1))
    return lat[0] if lat else None
def tf_check(g):
    f = _full(g)
    if f is None: return None
    L, rows, cols = f; h, w = dims(g); out = copy(g)
    for cell in _cells(h, w, rows, cols):
        if (cell[0] + cell[1]) % 2 == 0: _fillcell(out, cell, 1)
    return out
rule("lattice_cells_checkerboard", "The lattice cells are filled with colour 1 in a checkerboard pattern starting with the top-left cell; the other cells stay empty.", gi_check, tf_check)


# 30 the one dotted cell fills its whole row and column of cells.
def gi_cross(rng):
    h, w = _hw(rng); L, D = colours(rng, 2); lat = _lattice(rng, h, w, L)
    if lat is None: return None
    g, rows, cols = lat; r, c = rng.choice(_interior(rng.choice(_cells(h, w, rows, cols)))); g[r][c] = D
    return g
def tf_cross(g):
    f = _full(g)
    if f is None: return None
    L, rows, cols = f; h, w = dims(g); cs = _cells(h, w, rows, cols)
    src = [cell for cell in cs if _content(g, cell, L)]
    if len(src) != 1 or len(_content(g, src[0], L)) != 1: return None
    i, j = src[0][:2]; D = _content(g, src[0], L)[0][2]; out = copy(g)
    for cell in cs:
        if cell[0] == i or cell[1] == j: _fillcell(out, cell, D)
    return out
rule("dotted_lattice_cell_cross_of_cells", "One lattice cell holds a dot; every cell in that cell's row and every cell in its column is filled solid with the dot's colour.", gi_cross, tf_cross)


# 31 the largest lattice cell is filled with the line colour.
def gi_largest(rng):
    h, w = _hw(rng); L = rng.choice(COLOURS); lat = _lattice(rng, h, w, L)
    if lat is None: return None
    g, rows, cols = lat; areas = sorted(len(_interior(c)) for c in _cells(h, w, rows, cols))
    return g if areas[-1] != areas[-2] else None
def tf_largest(g):
    f = _full(g)
    if f is None: return None
    L, rows, cols = f; h, w = dims(g); cs = _cells(h, w, rows, cols); areas = [len(_interior(c)) for c in cs]
    if areas.count(max(areas)) != 1: return None
    return _fillcell(copy(g), cs[areas.index(max(areas))], L)
rule("largest_lattice_cell_filled", "The lines divide the grid into cells of different sizes; the single largest cell is filled solid with the line colour.",
     lambda rng: _retry(gi_largest, rng), tf_largest)


# 32 single-colour lattice recoloured by orientation.
def gi_orient(rng):
    h, w = _hw(rng); lat = _lattice(rng, h, w, _not(rng, 1, 2, 3))
    return lat[0] if lat else None
def tf_orient(g):
    f = _full(g)
    if f is None: return None
    L, rows, cols = f; h, w = dims(g); out = copy(g)
    for r in rows: out[r] = [1] * w
    for c in cols:
        for r in range(h): out[r][c] = 3 if r in rows else 2
    return out
rule("lattice_lines_coloured_by_orientation", "Horizontal lines become colour 1, vertical lines become colour 2 and the cells where they cross become colour 3.", gi_orient, tf_orient)


# 33 segments that do not span the grid are erased; full lines stay.
def gi_keepfull(rng):
    h, w = _hw(rng); L = rng.choice(COLOURS); lat = _lattice(rng, h, w, L)
    if lat is None: return None
    g, rows, cols = lat; taken = {(r, c) for r in range(h) for c in range(w) if g[r][c] or r in rows or c in cols}
    taken |= {(r + a, c + b) for r in rows for c in range(w) for a in (-1, 1) for b in (0,)} | {(r + a, c + b) for c in cols for r in range(h) for a in (0,) for b in (-1, 1)}
    n = 0
    for _ in range(40):
        if n >= 4: break
        ln = rng.randint(2, 6)
        if rng.random() < 0.5:
            r, c = rng.randrange(h), rng.randint(0, w - ln); cs = [(r, c + i) for i in range(ln)]
        else:
            r, c = rng.randint(0, h - ln), rng.randrange(w); cs = [(r + i, c) for i in range(ln)]
        if set(cs) & taken: continue
        taken |= {(y + a, x + b) for y, x in cs for a in (-1, 0, 1) for b in (-1, 0, 1)}
        for y, x in cs: g[y][x] = L
        n += 1
    return g if n else None
def tf_keepfull(g):
    f = _full(g)
    if f is None: return None
    L, rows, cols = f; h, w = dims(g)
    return [[g[r][c] if r in rows or c in cols else 0 for c in range(w)] for r in range(h)]
rule("keep_only_full_lines", "Only the lines that span the whole grid from edge to edge are kept; every shorter segment of the same colour is erased.", gi_keepfull, tf_keepfull)


# 34 lattice contents shift one cell to the right, wrapping round.
def gi_shift(rng):
    L = rng.choice(COLOURS); g, rows, cols = _regular(rng, L); h, w = dims(g); cs = _cells(h, w, rows, cols)
    if not cols: return None
    for cell in rng.sample(cs, rng.randint(1, max(1, len(cs) // 2))):
        r, c = rng.choice(_interior(cell)); g[r][c] = _not(rng, L)
    return g
def tf_shift(g):
    f = _full(g)
    if f is None or not f[2]: return None
    L, rows, cols = f; h, w = dims(g); cs = _cells(h, w, rows, cols); nc = len(cols) + 1
    by = {(cell[0], cell[1]): cell for cell in cs}; out = copy(g)
    for cell in cs:
        for r, c, v in _content(g, cell, L): out[r][c] = 0
    for cell in cs:
        t = by[(cell[0], (cell[1] + 1) % nc)]
        for r, c, v in _content(g, cell, L): out[t[2] + r - cell[2]][t[3] + c - cell[3]] = v
    return out
rule("lattice_contents_shift_one_cell_right", "Every dot inside a regular lattice moves to the same position in the next cell to the right; dots in the last column wrap round to the first.", gi_shift, tf_shift)


# 35 every segment grows to a full line; verticals over horizontals.
def gi_grow(rng):
    h, w = _hw(rng); return _segments(rng, h, w, 2, 6, 2, 6, unique_axis=True)
def tf_grow(g):
    h, w = dims(g); out = copy(g); segs = [o for o in components(g, lambda v: v != 0) if len(o) >= 2]
    for o in segs:
        r0, c0, r1, c1 = bbox(o)
        if r0 == r1: out[r0] = [g[r0][c0]] * w
    for o in segs:
        r0, c0, r1, c1 = bbox(o)
        if c0 == c1:
            for r in range(h): out[r][c0] = g[r0][c0]
    return out
rule("segments_grow_to_full_lines", "Every straight segment is stretched into a full line across the whole grid in its colour; where lines cross, vertical lines are drawn over horizontal ones.", gi_grow, tf_grow)


# 36 a regular lattice is subdivided: a new line midway between every two neighbouring lines.
def gi_subdiv(rng):
    h, w = _hw(rng, 9); L = rng.choice(COLOURS); p = rng.choice([4, 6])
    rows = list(range(rng.randint(1, p), h, p)); cols = list(range(rng.randint(1, p), w, p))
    if len(rows) < 2 or len(cols) < 2: return None
    g = blank(h, w)
    for r in rows: g[r] = [L] * w
    for c in cols:
        for r in range(h): g[r][c] = L
    return g
def tf_subdiv(g):
    f = _full(g)
    if f is None: return None
    L, rows, cols = f; h, w = dims(g); out = copy(g)
    for a, b in zip(rows, rows[1:]):
        if (b - a) % 2 == 0: out[(a + b) // 2] = [L] * w
    for a, b in zip(cols, cols[1:]):
        if (b - a) % 2 == 0:
            for r in range(h): out[r][(a + b) // 2] = L
    return out
rule("lattice_subdivided_midlines", "A new line of the same colour is drawn exactly midway between every two neighbouring lines of the regular lattice, in both directions.",
     lambda rng: _retry(gi_subdiv, rng), tf_subdiv)


# 37 the lattice lines bounding a dotted cell take the dot's colour.
def gi_border(rng):
    h, w = _hw(rng); L = rng.choice(COLOURS); lat = _lattice(rng, h, w, L)
    if lat is None: return None
    g, rows, cols = lat; cs = _cells(h, w, rows, cols); picked = []
    for cell in rng.sample(cs, len(cs)):
        if len(picked) >= rng.randint(1, 3): break
        if all(abs(cell[0] - p[0]) >= 2 or abs(cell[1] - p[1]) >= 2 for p in picked): picked.append(cell)
    for cell, D in zip(picked, colours(rng, len(picked), exclude=(0, L))):
        r, c = rng.choice(_interior(cell)); g[r][c] = D
    return g
def tf_border(g):
    f = _full(g)
    if f is None: return None
    L, rows, cols = f; h, w = dims(g); out = copy(g)
    for i, j, r0, c0, r1, c1 in _cells(h, w, rows, cols):
        ct = _content(g, (i, j, r0, c0, r1, c1), L)
        if len(ct) != 1: continue
        D = ct[0][2]
        for r in range(r0 - 1, r1 + 2):
            for c in range(c0 - 1, c1 + 2):
                if 0 <= r < h and 0 <= c < w and g[r][c] == L and (r in (r0 - 1, r1 + 1) or c in (c0 - 1, c1 + 1)): out[r][c] = D
    return out
rule("dotted_cell_border_recoloured", "For every lattice cell holding a dot, the pieces of lattice line that frame that cell, corners included, are recoloured with the dot's colour.", gi_border, tf_border)


# 38 two dots in one row (or column) of cells: fill the cells from one to the other.
def gi_span(rng):
    h, w = _hw(rng); L, D = colours(rng, 2)
    lat = _lattice(rng, h, w, L, k=(1, 6), kc=(2, 6)) if rng.random() < 0.5 else None
    if lat is None:
        lat = _lattice(rng, h, w, L, k=(2, 6), kc=(1, 6)); horiz = False
    else: horiz = True
    if lat is None: return None
    g, rows, cols = lat; cs = _cells(h, w, rows, cols); ni, nj = len(rows) + 1, len(cols) + 1
    if horiz: i = rng.randrange(ni); a, b = rng.sample(range(nj), 2); picks = [(i, a), (i, b)]
    else: j = rng.randrange(nj); a, b = rng.sample(range(ni), 2); picks = [(a, j), (b, j)]
    for cell in cs:
        if cell[:2] in picks: r, c = rng.choice(_interior(cell)); g[r][c] = D
    return g
def tf_span(g):
    f = _full(g)
    if f is None: return None
    L, rows, cols = f; h, w = dims(g); cs = _cells(h, w, rows, cols)
    src = [cell for cell in cs if _content(g, cell, L)]
    if len(src) != 2: return None
    (i1, j1), (i2, j2) = src[0][:2], src[1][:2]; D = _content(g, src[0], L)[0][2]; out = copy(g)
    for cell in cs:
        i, j = cell[:2]
        if (i1 == i2 == i and min(j1, j2) <= j <= max(j1, j2)) or (j1 == j2 == j and min(i1, i2) <= i <= max(i1, i2)): _fillcell(out, cell, D)
    return out if i1 == i2 or j1 == j2 else None
rule("cells_between_two_dots_filled", "Two dots sit in two lattice cells of the same row or column of cells; those two cells and every cell between them are filled with the dot colour.", gi_span, tf_span)


# 39 each cell is filled with the colour equal to how many grey dots it held.
def gi_dotcount(rng):
    h, w = _hw(rng); L = rng.choice([6, 7, 8, 9]); lat = _lattice(rng, h, w, L)
    if lat is None: return None
    g, rows, cols = lat; n = 0
    for cell in _cells(h, w, rows, cols):
        it = _interior(cell); k = rng.randint(0, min(4, len(it)))
        for r, c in rng.sample(it, k): g[r][c] = 5
        n += k
    return g if n else None
def tf_dotcount(g):
    f = _full(g)
    if f is None: return None
    L, rows, cols = f; h, w = dims(g); out = copy(g)
    for cell in _cells(h, w, rows, cols):
        k = len(_content(g, cell, L))
        if k > 9: return None
        if k: _fillcell(out, cell, k)
    return out
rule("lattice_cell_fill_by_dot_count", "Each lattice cell holding grey dots is filled solid with the colour whose number equals its dot count (one dot gives 1, two dots 2, and so on).", gi_dotcount, tf_dotcount)


# 40 only the points where segments cross remain.
def gi_xonly(rng):
    h, w = _hw(rng); L = rng.choice(COLOURS); rows = _lines(rng, h, 1, 4, 1); cols = _lines(rng, w, 1, 4, 1)
    if rows is None or cols is None: return None
    hs = [(r,) + tuple(sorted(rng.sample(range(w), 2))) for r in rows]; vs = [(c,) + tuple(sorted(rng.sample(range(h), 2))) for c in cols]
    n = 0
    for r, a, b in hs:
        for c, u, v in vs:
            if a < c < b and u < r < v: n += 1; continue
            if a - 1 <= c <= b + 1 and u - 1 <= r <= v + 1: return None
    if n == 0: return None
    g = blank(h, w)
    for r, a, b in hs:
        for c in range(a, b + 1): g[r][c] = L
    for c, u, v in vs:
        for r in range(u, v + 1): g[r][c] = L
    return g
def tf_xonly(g):
    h, w = dims(g); out = blank(h, w)
    for r, c in cells(g, lambda v: v != 0):
        if 0 < r < h - 1 and 0 < c < w - 1 and all(g[r + dr][c + dc] == g[r][c] for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0))): out[r][c] = g[r][c]
    return out
rule("only_crossings_remain", "Horizontal and vertical segments cross each other; only the cells where a horizontal segment crosses a vertical one are kept, everything else is erased.",
     lambda rng: _retry(gi_xonly, rng), tf_xonly)
