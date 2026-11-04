# b006_assembly.py -- GRID-OF-GRIDS / OUTPUT ASSEMBLY: the output is built from pieces of the input in a new
# arrangement (stack, lay out by map or key, fold panels, jigsaw by matching edges, swatches to stripes...).
# Panel rules use grey (5) separator lines. Sizes are biased so a good share of inputs have a 21-30 side.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

SEP = 5


# ---------- local helpers ----------
def _blobs(g, bg=0):
    """8-connected multi-colour components of non-bg cells (glib.components splits by colour)."""
    H, W = dims(g); seen, out = set(), []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or (r, c) in seen:
                continue
            comp, st = [], [(r, c)]; seen.add((r, c))
            while st:
                y, x = st.pop(); comp.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen and g[ny][nx] != bg:
                            seen.add((ny, nx)); st.append((ny, nx))
            out.append(comp)
    return out


def _crop_obj(g, o):
    r0, c0, r1, c1 = bbox(o); sub = blank(r1 - r0 + 1, c1 - c0 + 1)
    for r, c in o:
        sub[r - r0][c - c0] = g[r][c]
    return sub


def _reading(g, obs):
    return sorted(obs, key=lambda o: bbox(o)[:2])


def _hjoin(parts, gap=0, align="top"):
    H = max(len(p) for p in parts); W = sum(len(p[0]) for p in parts) + gap * (len(parts) - 1)
    if H > 30 or W > 30:
        return None
    out = blank(H, W); c = 0
    for p in parts:
        r0 = 0 if align == "top" else (H - len(p)) if align == "bottom" else (H - len(p)) // 2
        paste(out, p, r0, c); c += len(p[0]) + gap
    return out


def _vjoin(parts, gap=0, align="left"):
    H = sum(len(p) for p in parts) + gap * (len(parts) - 1); W = max(len(p[0]) for p in parts)
    if H > 30 or W > 30:
        return None
    out = blank(H, W); r = 0
    for p in parts:
        c0 = 0 if align == "left" else (W - len(p[0])) if align == "right" else (W - len(p[0])) // 2
        paste(out, p, r, c0); r += len(p) + gap
    return out


def _scene(rng, k_lo, k_hi, n_lo, n_hi, lo=8, hi=30, margin=1, distinct=True):
    h, w = size(rng, lo, hi); g = blank(h, w); k = rng.randint(k_lo, k_hi)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    cols = colours(rng, k) if distinct else [rng.choice(COLOURS) for _ in range(k)]
    if place_shapes(rng, g, shapes, cols, margin=margin) is None:
        return None
    return g if len(objects(g, 0)) == k else None


def _shape_in_box(rng, h, w):
    """An 8-connected shape whose bounding box is exactly h x w, or None."""
    for _ in range(60):
        sh = random_shape(rng, rng.randint(max(h, w), h * w), conn8=True)
        if max(r for r, _ in sh) == h - 1 and max(c for _, c in sh) == w - 1:
            return sh
    return None


def _pattern(rng, h, w, cols, density=0.5):
    """Random multi-colour pattern, at least one cell."""
    p = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < density:
                p[r][c] = rng.choice(cols)
    if not any(v for row in p for v in row):
        p[rng.randrange(h)][rng.randrange(w)] = rng.choice(cols)
    return p


def _mono(rng, h, w, col, density=None):
    return _pattern(rng, h, w, [col], density if density is not None else rng.uniform(0.3, 0.8))


def _hpanels(panels, sep=SEP):
    out = [list(panels[0][r]) for r in range(len(panels[0]))]
    for p in panels[1:]:
        for r in range(len(out)):
            out[r] += [sep] + p[r]
    return out


def _vpanels(panels, sep=SEP):
    out = [row[:] for row in panels[0]]
    for p in panels[1:]:
        out.append([sep] * len(out[0])); out += [row[:] for row in p]
    return out


def _split_cols(g, sep=SEP):
    H, W = dims(g); parts, cur = [], []
    for c in range(W):
        if all(g[r][c] == sep for r in range(H)):
            if cur: parts.append(cur); cur = []
        else:
            cur.append(c)
    if cur: parts.append(cur)
    return [[[g[r][c] for c in cs] for r in range(H)] for cs in parts]


def _split_rows(g, sep=SEP):
    return [transpose(p) for p in _split_cols(transpose(g), sep)]


def _grid_split(g, sep=SEP):
    return [_split_cols(band, sep) for band in _split_rows(g, sep)]


def _dom(p):
    cnt = counts(p); cnt.pop(0, None)
    return max(cnt.items(), key=lambda kv: kv[1])[0] if cnt else 0


def _empty(p):
    return not any(v for row in p for v in row)


def _place_pieces(rng, g, pieces, margin=1):
    shapes = [[(r, c) for r in range(len(p)) for c in range(len(p[0]))] for p in pieces]
    pos = place_shapes(rng, g, shapes, [1] * len(pieces), margin=margin)
    if pos is None:
        return None
    for p, (r0, c0) in zip(pieces, pos):
        paste(g, p, r0, c0)
    return pos


def _swatch_scene(rng, k_lo=2, k_hi=6):
    h, w = size(rng, 6, 30); g = blank(h, w); k = rng.randint(k_lo, k_hi)
    r = rng.randrange(h); c0 = rng.randrange(w - k + 1); cols = colours(rng, k)
    for i, col in enumerate(cols):
        g[r][c0 + i] = col
    return g


def _swatches(g):
    for row in g:
        vals = [v for v in row if v]
        if vals:
            return vals
    return None


# ---------- 1-2 stack objects in reading order ----------
def gi_stack_col(rng):
    return _scene(rng, 2, 5, 3, 6)
def tf_stack_col(g):
    obs = _reading(g, objects(g, 0))
    return _vjoin([_crop_obj(g, o) for o in obs], gap=1, align="left")
rule("stack_objects_column_reading_order", "The objects are cut out and stacked top to bottom in reading order (top row first, then left to right), left-aligned with one empty row between them.", gi_stack_col, tf_stack_col)


def gi_stack_row(rng):
    return _scene(rng, 2, 6, 3, 7)
def tf_stack_row(g):
    obs = sorted(objects(g, 0), key=lambda o: (bbox(o)[1], bbox(o)[0]))
    return _hjoin([_crop_obj(g, o) for o in obs], gap=0, align="bottom")
rule("objects_lined_up_by_column_bottom_aligned", "The objects are cut out and placed side by side, touching, ordered by their leftmost column and resting on a common floor.", gi_stack_row, tf_stack_row)


# ---------- 3 map cells expand to matching objects ----------
def gi_map_expand(rng):
    m, n = rng.randint(2, 3), rng.randint(2, 3); k = rng.randint(2, min(6, m * n - 1))
    H, W = rng.randint(max(10, m + 9), 30), rng.randint(max(10, n + 9), 30)
    g = blank(H, W); cols = colours(rng, k, exclude=(0, SEP))
    for i, (r, c) in enumerate(rng.sample([(r, c) for r in range(m) for c in range(n)], k)):
        g[r][c] = cols[i]
    for c in range(W): g[m][c] = SEP
    for r in range(m): g[r][n] = SEP
    field = blank(H - m - 1, W)
    shapes = [_shape_in_box(rng, 3, 3) for _ in range(k)]
    if any(s is None for s in shapes) or place_shapes(rng, field, shapes, cols, margin=1) is None:
        return None
    for r in range(H - m - 1): g[m + 1 + r] = field[r]
    return g
def tf_map_expand(g):
    rs = next(r for r in range(len(g)) if g[r][0] == SEP); cs = next(c for c in range(len(g[0])) if g[0][c] == SEP)
    field = g[rs + 1:]; by = {}
    for o in objects(field, 0):
        by[field[o[0][0]][o[0][1]]] = _crop_obj(field, o)
    out = blank(rs * 3, cs * 3)
    for r in range(rs):
        for c in range(cs):
            v = g[r][c]
            if v:
                if v not in by: return None
                paste(out, by[v], r * 3, c * 3)
    return out
rule("map_cells_expand_to_matching_objects", "The small map in the top-left corner is blown up three times: each coloured map cell becomes the 3x3 shape of that colour found in the field below.", gi_map_expand, tf_map_expand)


# ---------- 4 panels concatenated in key order ----------
def gi_keyorder(rng):
    k = rng.randint(2, 5); pw = rng.randint(2, (30 - (k - 1)) // k); ph = rng.randint(3, 28)
    cols = colours(rng, k, exclude=(0, SEP)); W = k * pw + k - 1
    body = _hpanels([_mono(rng, ph, pw, c) for c in cols])
    key = [0] * W
    for i, j in enumerate(rng.sample(range(k), k)):
        key[i] = cols[j]
    return [key, [SEP] * W] + body
def tf_keyorder(g):
    key = [v for v in g[0] if v]; panels = _split_cols(g[2:])
    by = {_dom(p): p for p in panels}
    if len(by) != len(panels) or any(c not in by for c in key): return None
    return _hjoin([by[c] for c in key])
rule("panels_concatenate_by_key_order", "The colours in the top key row give an order; the one-colour panels below are joined side by side in that order with the grey lines removed.", gi_keyorder, tf_keyorder)


# ---------- 5 four objects by quadrant of origin ----------
def gi_quad2x2(rng):
    H, W = rng.randint(10, 30), rng.randint(10, 30); g = blank(H, W); hh, hw = H // 2, W // 2
    cols = colours(rng, 4)
    for i, (r0, c0) in enumerate([(0, 0), (0, W - hw), (H - hh, 0), (H - hh, W - hw)]):
        sub = blank(hh, hw)
        if place_shapes(rng, sub, [random_shape(rng, rng.randint(3, 8))], [cols[i]], margin=0) is None: return None
        paste(g, sub, r0, c0)
    return g if len(objects(g, 0)) == 4 else None
def tf_quad2x2(g):
    H, W = dims(g); obs = objects(g, 0)
    if len(obs) != 4: return None
    crops = [_crop_obj(g, o) for o in obs]; mh = max(len(p) for p in crops); mw = max(len(p[0]) for p in crops)
    out = blank(2 * mh, 2 * mw); seen = set()
    for o, p in zip(obs, crops):
        r0, c0, r1, c1 = bbox(o); q = (int((r0 + r1) / 2 >= H / 2 - 0.5), int((c0 + c1) / 2 >= W / 2 - 0.5))
        if q in seen: return None
        seen.add(q); paste(out, p, q[0] * mh, q[1] * mw)
    return out
rule("quadrant_objects_to_2x2", "Each of the four objects is cut out and placed in the quarter of a compact 2x2 layout matching the quarter of the grid it came from.", gi_quad2x2, tf_quad2x2)


# ---------- 6 staircase by size ----------
def gi_stair(rng):
    g = _scene(rng, 3, 5, 2, 7)
    if g is None: return None
    sz = [len(o) for o in objects(g, 0)]
    return g if len(set(sz)) == len(sz) else None
def tf_stair(g):
    obs = sorted(objects(g, 0), key=len); crops = [_crop_obj(g, o) for o in obs]
    H = sum(len(p) for p in crops); W = max(i + len(p[0]) for i, p in enumerate(crops))
    if H > 30 or W > 30: return None
    out = blank(H, W); r = 0
    for i, p in enumerate(crops):
        paste(out, p, r, i); r += len(p)
    return out
rule("objects_staircase_by_size", "The objects are stacked from smallest at the top to largest at the bottom, each one indented one more cell to the right than the one above it.", gi_stair, tf_stair)


# ---------- 7 jigsaw by matching edge colours ----------
def gi_jigsaw(rng):
    k = rng.randint(2, 4); h = rng.randint(3, 7); ws = [rng.randint(3, 6) for _ in range(k)]
    cols = colours(rng, 2 * k - 1); body, conn = cols[:k], cols[k:]
    pieces = []
    for i in range(k):
        p = blank(h, ws[i], body[i])
        if i > 0:
            for r in range(h): p[r][0] = conn[i - 1]
        if i < k - 1:
            for r in range(h): p[r][-1] = conn[i]
        pieces.append(p)
    rng.shuffle(pieces)
    H, W = rng.randint(max(10, h + 2), 30), rng.randint(12, 30); g = blank(H, W)
    return g if _place_pieces(rng, g, pieces) else None
def tf_jigsaw(g):
    ps = [_crop_obj(g, b) for b in _blobs(g)]
    info = [(p[0][1], p[0][0], p[0][-1]) for p in ps]   # body, left, right
    start = [i for i, (b, l, r) in enumerate(info) if l == b]
    if len(start) != 1: return None
    order = [start[0]]
    while len(order) < len(ps):
        cur = info[order[-1]][2]; nxt = [i for i, (b, l, r) in enumerate(info) if l == cur and i not in order]
        if len(nxt) != 1: return None
        order.append(nxt[0])
    return _hjoin([ps[i] for i in order])
rule("jigsaw_match_edge_colours", "The rectangular pieces are joined into one strip: a piece's coloured right edge sits against the piece whose left edge has the same colour, starting from the piece with no coloured left edge.", gi_jigsaw, tf_jigsaw)


# ---------- 8 nearest object colour per corner ----------
def gi_corner4(rng):
    g = _scene(rng, 4, 4, 2, 6, 10, 30)
    return g if g is not None and tf_corner4(g) is not None else None
def tf_corner4(g):
    H, W = dims(g); obs = objects(g, 0)
    if len(obs) != 4: return None
    cen = [((bbox(o)[0] + bbox(o)[2]) / 2, (bbox(o)[1] + bbox(o)[3]) / 2) for o in obs]
    out = blank(2, 2); used = set()
    for (qr, qc), (cr, cc) in zip([(0, 0), (0, 1), (1, 0), (1, 1)], [(0, 0), (0, W - 1), (H - 1, 0), (H - 1, W - 1)]):
        d = [(abs(y - cr) + abs(x - cc), i) for i, (y, x) in enumerate(cen)]; d.sort()
        if d[0][0] == d[1][0] or d[0][1] in used: return None
        used.add(d[0][1]); o = obs[d[0][1]]; out[qr][qc] = g[o[0][0]][o[0][1]]
    return out
rule("nearest_object_colour_per_corner", "Output a 2x2 grid: each cell holds the colour of the object that lies closest to the corresponding corner of the input.", gi_corner4, tf_corner4)


# ---------- 9 halves overlaid, right half transposed ----------
def gi_overlay_t(rng):
    s = rng.randint(4, 14); g = blank(s, 2 * s + 1); cols = colours(rng, rng.randint(2, 4))
    for c in range(s): g[c][s] = SEP
    for _ in range(rng.randint(s, s * s // 2)):
        g[rng.randrange(s)][rng.randrange(s)] = rng.choice(cols)
    for _ in range(rng.randint(s, s * s // 2)):
        g[rng.randrange(s)][s + 1 + rng.randrange(s)] = rng.choice(cols)
    return g
def tf_overlay_t(g):
    s = len(g); left = [row[:s] for row in g]; right = transpose([row[s + 1:] for row in g])
    out = copy(left)
    for r in range(s):
        for c in range(s):
            if out[r][c] == 0: out[r][c] = right[r][c]
    return out if out != left else None
rule("halves_overlay_right_transposed", "The two square halves either side of the grey line are overlaid: the left half stays on top, and the right half is flipped across its diagonal before filling the left half's empty cells.", gi_overlay_t, tf_overlay_t)


# ---------- 10-12, 37 swatch rows ----------
def tf_stripes(g):
    H, W = dims(g); sw = _swatches(g)
    return [[sw[c % len(sw)] for c in range(W)] for _ in range(H)]
rule("swatches_row_to_vertical_stripes", "The row of colour swatches sets a repeating sequence; the whole grid is filled with vertical stripes cycling through those colours from the left edge.", _swatch_scene, tf_stripes)


def tf_nested(g):
    H, W = dims(g); sw = _swatches(g)
    return [[sw[min(r, c, H - 1 - r, W - 1 - c) % len(sw)] for c in range(W)] for r in range(H)]
rule("swatches_to_nested_rectangles", "The row of colour swatches sets a sequence; the whole grid is filled with nested rectangular rings, the outermost ring in the first swatch colour and cycling inward.", _swatch_scene, tf_nested)


def tf_diag(g):
    H, W = dims(g); sw = _swatches(g)
    return [[sw[(r + c) % len(sw)] for c in range(W)] for r in range(H)]
rule("swatches_to_diagonal_stripes", "The row of colour swatches sets a sequence; the whole grid is filled with diagonal stripes cycling through those colours starting at the top-left corner.", _swatch_scene, tf_diag)


def tf_swstair(g):
    sw = _swatches(g); k = len(sw)
    return [[sw[i] if c <= i else 0 for c in range(k)] for i in range(k)]
rule("swatches_to_colour_staircase", "Output a square with one row per swatch: the i-th row is filled from the left with i cells of the i-th swatch colour, forming a staircase.", _swatch_scene, tf_swstair)


# ---------- 13 objects sorted by colour ----------
def gi_colrow(rng):
    return _scene(rng, 2, 6, 3, 7)
def tf_colrow(g):
    obs = sorted(objects(g, 0), key=lambda o: g[o[0][0]][o[0][1]])
    return _hjoin([_crop_obj(g, o) for o in obs], gap=1, align="top")
rule("objects_sorted_by_colour_row", "The objects are cut out and lined up left to right from lowest colour number to highest, top-aligned with one empty column between them.", gi_colrow, tf_colrow, digits=True)


# ---------- 14 four panels fold into a square ----------
def gi_fold4(rng):
    s = rng.randint(3, 6); cols = colours(rng, rng.randint(1, 4), exclude=(0, SEP))
    return _hpanels([_pattern(rng, s, s, cols, rng.uniform(0.3, 0.7)) for _ in range(4)])
def tf_fold4(g):
    p = _split_cols(g)
    if len(p) != 4: return None
    return _vjoin([_hjoin(p[:2]), _hjoin(p[2:])])
rule("four_panels_fold_into_square", "The four panels in a row are rearranged into a 2x2 square: the first two on top, the last two below, with the grey lines removed.", gi_fold4, tf_fold4)


# ---------- 15 panels reversed ----------
def gi_prev(rng):
    k = rng.randint(2, 5); ph = rng.randint(2, 30); cols = colours(rng, rng.randint(1, 3), exclude=(0, SEP))
    ws = [rng.randint(1, 6) for _ in range(k)]
    if sum(ws) + k - 1 > 30: return None
    return _hpanels([_pattern(rng, ph, w, cols) for w in ws])
def tf_prev(g):
    out = _hpanels(_split_cols(g)[::-1])
    return out if out != g else None
rule("panels_reverse_order", "The panels separated by grey lines are put back in reverse order, the last one first, keeping the grey lines between them.", gi_prev, tf_prev)


# ---------- 16 panels sorted by colour value ----------
def gi_psort(rng):
    k = rng.randint(2, 5); pw = rng.randint(2, (30 - (k - 1)) // k); ph = rng.randint(2, 30)
    cols = colours(rng, k, exclude=(0, SEP))
    if cols == sorted(cols): return None
    return _hpanels([_mono(rng, ph, pw, c) for c in cols])
def tf_psort(g):
    return _hpanels(sorted(_split_cols(g), key=_dom))
rule("panels_sorted_by_colour_value", "Each panel is drawn in one colour; the panels are reordered left to right from the lowest colour number to the highest, grey lines kept.", gi_psort, tf_psort, digits=True)


# ---------- 17 two panels interleaved by column ----------
def gi_inter(rng):
    h, w = rng.randint(2, 30), rng.randint(2, 14); cols = colours(rng, rng.randint(1, 4), exclude=(0, SEP))
    return _hpanels([_pattern(rng, h, w, cols, rng.uniform(0.3, 0.8)) for _ in range(2)])
def tf_inter(g):
    a, b = _split_cols(g)
    return [[v for pair in zip(ra, rb) for v in pair] for ra, rb in zip(a, b)]
rule("panels_interleave_columns", "The two panels are zipped together column by column: first column of the left panel, first of the right, second of the left, and so on.", gi_inter, tf_inter)


# ---------- 18-22 grids of panels ----------
def _panel_grid(rng, m, n, make):
    return _vpanels([_hpanels([make(i, j) for j in range(n)]) for i in range(m)])


def gi_gdiag(rng):
    m = rng.randint(2, 4); s = rng.randint(2, (30 - (m - 1)) // m); cols = colours(rng, rng.randint(1, 4), exclude=(0, SEP))
    return _panel_grid(rng, m, m, lambda i, j: _pattern(rng, s, s, cols, rng.uniform(0.3, 0.7)))
def tf_gdiag(g):
    gp = _grid_split(g)
    return _hjoin([gp[i][i] for i in range(len(gp))])
rule("grid_of_panels_pick_diagonal", "In the square grid of panels, the panels on the main diagonal (top-left to bottom-right) are joined side by side without the grey lines.", gi_gdiag, tf_gdiag)


def gi_gtrans(rng):
    m, n = rng.randint(1, 4), rng.randint(1, 4)
    if m == n and m == 1: return None
    s = rng.randint(2, (30 - (max(m, n) - 1)) // max(m, n)); cols = colours(rng, rng.randint(1, 3), exclude=(0, SEP))
    return _panel_grid(rng, m, n, lambda i, j: _pattern(rng, s, s, cols, rng.uniform(0.2, 0.6)))
def tf_gtrans(g):
    gp = _grid_split(g); out = _vpanels([_hpanels([gp[i][j] for i in range(len(gp))]) for j in range(len(gp[0]))])
    return out if out != g else None
rule("grid_of_panels_transpose", "The grid of panels is transposed: the panel in row i, column j moves to row j, column i, each panel itself unchanged and the grey lines redrawn.", gi_gtrans, tf_gtrans)


def gi_gempty(rng):
    m, n = rng.randint(2, 4), rng.randint(2, 4); s = rng.randint(2, (30 - (max(m, n) - 1)) // max(m, n))
    cols = colours(rng, rng.randint(1, 3), exclude=(0, SEP)); keep = rng.randint(2, min(m * n - 1, (30 + 1) // (s + 1)))
    full = set(rng.sample(range(m * n), keep))
    return _panel_grid(rng, m, n, lambda i, j: _pattern(rng, s, s, cols, rng.uniform(0.3, 0.7)) if i * n + j in full else blank(s, s))
def tf_gempty(g):
    ps = [p for band in _grid_split(g) for p in band if not _empty(p)]
    if len(ps) < 2 or len(ps) * (len(ps[0][0]) + 1) - 1 > 30: return None
    return _hpanels(ps)
rule("grid_of_panels_remove_empty", "The empty panels are dropped and the remaining panels are lined up in one row in reading order, grey lines between them.", gi_gempty, tf_gempty)


def gi_gcol(rng):
    m, n = rng.randint(2, 3), rng.randint(2, 3); h = rng.randint(2, (30 - (m * n - 1)) // (m * n)); w = rng.randint(2, (30 - (n - 1)) // n)
    cols = colours(rng, rng.randint(1, 4), exclude=(0, SEP))
    return _panel_grid(rng, m, n, lambda i, j: _pattern(rng, h, w, cols, rng.uniform(0.3, 0.7)))
def tf_gcol(g):
    gp = _grid_split(g)
    return _vpanels([gp[i][j] for j in range(len(gp[0])) for i in range(len(gp))])
rule("grid_of_panels_unrolled_to_column", "The grid of panels is unrolled into a single column, taking the panels column by column: the whole first column top to bottom, then the second, and so on.", gi_gcol, tf_gcol)


def gi_gmap(rng):
    m, n = rng.randint(2, 5), rng.randint(2, 5); s = rng.randint(2, (30 - (max(m, n) - 1)) // max(m, n))
    cols = colours(rng, rng.randint(2, 5), exclude=(0, SEP))
    return _panel_grid(rng, m, n, lambda i, j: _mono(rng, s, s, rng.choice(cols)) if rng.random() < 0.8 else blank(s, s))
def tf_gmap(g):
    out = [[_dom(p) for p in band] for band in _grid_split(g)]
    return out if any(v for row in out for v in row) else None
rule("grid_of_panels_to_colour_map", "Each panel of the grid is reduced to a single cell of its colour (empty if the panel is empty), giving a small map with one cell per panel.", gi_gmap, tf_gmap)


# ---------- 23 one object per panel, cropped and joined ----------
def gi_pobj(rng):
    k = rng.randint(2, 5); pw = rng.randint(4, (30 - (k - 1)) // k); ph = rng.randint(4, 30); panels = []
    for _ in range(k):
        p = blank(ph, pw)
        if place_shapes(rng, p, [random_shape(rng, rng.randint(2, 6))], [rng.choice([c for c in COLOURS if c != SEP])], margin=0) is None: return None
        panels.append(p)
    return _hpanels(panels)
def tf_pobj(g):
    parts = []
    for p in _split_cols(g):
        obs = objects(p, 0)
        if len(obs) != 1: return None
        parts.append(_crop_obj(p, obs[0]))
    return _hjoin(parts, gap=0, align="top")
rule("panel_objects_cropped_and_joined", "Each panel holds one shape; the shapes are cut out to their bounding boxes and joined side by side in panel order, top-aligned and touching.", gi_pobj, tf_pobj)


# ---------- 24 top half from first panel, bottom half from second ----------
def gi_halfhalf(rng):
    h, w = 2 * rng.randint(2, 15), rng.randint(2, 14); cols = colours(rng, rng.randint(1, 4), exclude=(0, SEP))
    return _hpanels([_pattern(rng, h, w, cols, rng.uniform(0.3, 0.8)) for _ in range(2)])
def tf_halfhalf(g):
    a, b = _split_cols(g); h = len(a) // 2
    return a[:h] + b[h:]
rule("panels_top_from_first_bottom_from_second", "Output one panel whose top half is the top half of the left panel and whose bottom half is the bottom half of the right panel.", gi_halfhalf, tf_halfhalf)


# ---------- 25 two panels swap sides ----------
def gi_swap2(rng):
    h = rng.randint(2, 30); w1 = rng.randint(1, 14); w2 = rng.randint(1, 29 - w1)
    if w1 == w2: return None
    cols = colours(rng, rng.randint(1, 4), exclude=(0, SEP))
    return _hpanels([_pattern(rng, h, w1, cols), _pattern(rng, h, w2, cols)])
def tf_swap2(g):
    a, b = _split_cols(g)
    return _hpanels([b, a])
rule("two_panels_swap_sides", "The two panels of different widths trade places across the grey line, each keeping its own contents and width.", gi_swap2, tf_swap2)


# ---------- 26 panels ordered by corner label ----------
def gi_label(rng):
    k = rng.randint(2, 4); pw = rng.randint(2, (30 - (k - 1)) // k); ph = rng.randint(2, 30)
    cols = colours(rng, k, exclude=(0, SEP, 1, 2, 3, 4)); panels = []
    for i, lab in enumerate(rng.sample(range(1, k + 1), k)):
        p = _mono(rng, ph, pw, cols[i]); p[0][0] = lab; panels.append(p)
    return _hpanels(panels)
def tf_label(g):
    ps = _split_cols(g); labs = [p[0][0] for p in ps]
    if sorted(labs) != list(range(1, len(ps) + 1)): return None
    out = []
    for lab, p in sorted(zip(labs, ps)):
        q = copy(p); q[0][0] = 0; out.append(q)
    return _hjoin(out)
rule("panels_concatenate_by_corner_label", "Each panel carries a number 1, 2, 3... in its top-left cell; the panels are joined side by side in numeric order with the labels and grey lines removed.", gi_label, tf_label, digits=True)


# ---------- 27 jigsaw: quadrant pieces tagged at the outer corner ----------
def gi_jigq(rng):
    s = rng.randint(2, 6); cols = colours(rng, rng.randint(2, 4), exclude=(0, SEP))
    pic = [[rng.choice(cols) for _ in range(2 * s)] for _ in range(2 * s)]
    for r, c in [(0, 0), (0, 2 * s - 1), (2 * s - 1, 0), (2 * s - 1, 2 * s - 1)]: pic[r][c] = SEP
    pieces = [crop(pic, r0, c0, r0 + s - 1, c0 + s - 1) for r0 in (0, s) for c0 in (0, s)]; rng.shuffle(pieces)
    H, W = rng.randint(max(12, 2 * s + 4), 30), rng.randint(max(12, 2 * s + 4), 30); g = blank(H, W)
    return g if _place_pieces(rng, g, pieces) else None
def tf_jigq(g):
    ps = [_crop_obj(g, b) for b in _blobs(g)]
    if len(ps) != 4: return None
    s = len(ps[0]); out = blank(2 * s, 2 * s); seen = set()
    for p in ps:
        tags = [(r, c) for r, c in [(0, 0), (0, s - 1), (s - 1, 0), (s - 1, s - 1)] if p[r][c] == SEP]
        if len(tags) != 1 or tags[0] in seen: return None
        seen.add(tags[0]); r, c = tags[0]; paste(out, p, 0 if r == 0 else s, 0 if c == 0 else s)
    return out
rule("jigsaw_quadrants_by_tagged_corner", "Four square pieces each have one grey corner cell; they are assembled into one square so that every grey cell ends up in an outer corner of the result.", gi_jigq, tf_jigq)


# ---------- 28 rectangles ordered by hole count ----------
def gi_holes(rng):
    k = rng.randint(2, 4); cols = colours(rng, k); pieces = []; cnts = rng.sample(range(0, 5), k)
    for i in range(k):
        h, w = rng.randint(3, 6), rng.randint(3, 6); p = blank(h, w, cols[i])
        inner = [(r, c) for r in range(1, h - 1) for c in range(1, w - 1)]
        if cnts[i] > len(inner): return None
        for r, c in rng.sample(inner, cnts[i]): p[r][c] = 0
        pieces.append(p)
    H, W = rng.randint(10, 30), rng.randint(12, 30); g = blank(H, W)
    return g if _place_pieces(rng, g, pieces) else None
def tf_holes(g):
    ps = [crop(g, *bbox(o)) for o in objects(g, 0)]
    cnt = [sum(v == 0 for row in p for v in row) for p in ps]
    if len(set(cnt)) != len(cnt): return None
    return _hjoin([p for _, p in sorted(zip(cnt, ps))], gap=1, align="bottom")
rule("rectangles_ordered_by_hole_count_row", "The rectangles are lined up bottom-aligned with one empty column between them, from the one with the fewest holes on the left to the most holes on the right.", gi_holes, tf_holes)


# ---------- 29 domino chain ----------
def gi_domino(rng):
    k = rng.randint(2, 6); chain = colours(rng, k + 1)
    pieces = [[[chain[i], chain[i + 1]]] for i in range(k)]; rng.shuffle(pieces)
    H, W = rng.randint(6, 30), rng.randint(8, 30); g = blank(H, W)
    return g if _place_pieces(rng, g, pieces) else None
def tf_domino(g):
    ds = [_crop_obj(g, b)[0] for b in _blobs(g)]
    if any(len(d) != 2 for d in ds): return None
    rights = {d[1] for d in ds}; start = [d for d in ds if d[0] not in rights]
    if len(start) != 1: return None
    row = list(start[0]); nxt = {d[0]: d[1] for d in ds}
    while row[-1] in nxt and len(row) <= len(ds) + 1:
        row.append(nxt[row[-1]])
    return [row] if len(row) == len(ds) + 1 else None
rule("domino_chain_to_row", "The two-cell dominoes link into a chain where each domino's right colour is the next domino's left colour; output the chain of colours as one row.", gi_domino, tf_domino)


# ---------- 30 same-box objects overlaid in reading order ----------
def gi_overlay(rng):
    k = rng.randint(2, 3); h, w = rng.randint(3, 6), rng.randint(3, 6)
    shapes = [_shape_in_box(rng, h, w) for _ in range(k)]
    if any(s is None for s in shapes): return None
    H, W = rng.randint(max(10, h + 2), 30), rng.randint(max(10, w + 2), 30); g = blank(H, W)
    if place_shapes(rng, g, shapes, colours(rng, k), margin=1) is None: return None
    return g if len(objects(g, 0)) == k else None
def tf_overlay(g):
    crops = [_crop_obj(g, o) for o in _reading(g, objects(g, 0))]
    if len({(len(p), len(p[0])) for p in crops}) != 1: return None
    out = copy(crops[0])
    for p in crops[1:]:
        for r in range(len(p)):
            for c in range(len(p[0])):
                if out[r][c] == 0: out[r][c] = p[r][c]
    return out
rule("objects_overlaid_in_reading_order", "The equally boxed objects are cut out and stacked on top of each other into one box, the object earliest in reading order on top and later ones showing through its gaps.", gi_overlay, tf_overlay)


# ---------- 31 object repeated as many times as there are grey markers ----------
def gi_repeat(rng):
    H, W = size(rng, 8, 30); g = blank(H, W); n = rng.randint(2, 5); col = rng.choice([c for c in COLOURS if c != SEP])
    shapes = [random_shape(rng, rng.randint(3, 8))] + [[(0, 0)]] * n
    if place_shapes(rng, g, shapes, [col] + [SEP] * n, margin=1) is None: return None
    return g
def tf_repeat(g):
    n = len(cells(g, lambda v: v == SEP)); obs = [o for o in objects(g, 0) if g[o[0][0]][o[0][1]] != SEP]
    if len(obs) != 1: return None
    return _hjoin([_crop_obj(g, obs[0])] * n, gap=1)
rule("object_repeated_marker_count_times", "The single shape is cut out and repeated side by side, one empty column apart, as many times as there are grey marker cells.", gi_repeat, tf_repeat)


# ---------- 32-33 one object, four views ----------
def gi_one(rng):
    return _scene(rng, 1, 1, 3, 9)
def tf_mquad(g):
    p = _crop_obj(g, objects(g, 0)[0])
    top = [row + row[::-1] for row in p]
    return top + top[::-1]
rule("crop_object_mirror_quad", "The single object is cut out and laid out four times in a 2x2 arrangement: as is, mirrored left-right, mirrored top-bottom, and mirrored both ways.", gi_one, tf_mquad)


def gi_sq(rng):
    s = rng.randint(2, 6); sh = _shape_in_box(rng, s, s)
    if sh is None: return None
    H, W = size(rng, max(8, s + 2), 30); g = blank(H, W)
    if place_shapes(rng, g, [sh], [rng.choice(COLOURS)], margin=0) is None: return None
    return g if len(objects(g, 0)) == 1 else None
def tf_pin(g):
    p = _crop_obj(g, objects(g, 0)[0])
    if len(p) != len(p[0]): return None
    r1 = rot90(p); r2 = rot90(r1); r3 = rot90(r2)
    return [a + b for a, b in zip(p, r1)] + [a + b for a, b in zip(r3, r2)]
rule("crop_object_pinwheel", "The single square-boxed object is cut out and placed four times in a 2x2 pinwheel, each copy turned one more quarter turn clockwise going round.", gi_sq, tf_pin)


# ---------- 34 same-colour pairs side by side ----------
def gi_pairs(rng):
    k = rng.randint(2, 3); cols = colours(rng, k); h, w = size(rng, 10, 30); g = blank(h, w)
    shapes = [random_shape(rng, rng.randint(2, 6)) for _ in range(2 * k)]
    if place_shapes(rng, g, shapes, [c for c in cols for _ in range(2)], margin=1) is None: return None
    return g if len(objects(g, 0)) == 2 * k else None
def tf_pairs(g):
    by = {}
    for o in objects(g, 0):
        by.setdefault(g[o[0][0]][o[0][1]], []).append(o)
    rows = []
    for col in sorted(by):
        if len(by[col]) != 2: return None
        a, b = sorted(by[col], key=lambda o: bbox(o)[1])
        rows.append(_hjoin([_crop_obj(g, a), _crop_obj(g, b)], gap=1, align="top"))
    return _vjoin(rows, gap=1, align="left")
rule("same_colour_pairs_side_by_side_rows", "Each colour has two objects; for every colour in numeric order a row is built with the left-hand object, an empty column, then the right-hand object, and the rows are stacked with an empty row between.", gi_pairs, tf_pairs)


# ---------- 35 strip segments stacked ----------
def gi_strip(rng):
    k = rng.randint(2, 6); t = rng.randint(1, 3); m = rng.randint(2, (30 - (k - 1)) // k)
    if k * t > 30: return None
    cols = colours(rng, rng.randint(1, 4), exclude=(0, SEP))
    return _hpanels([_pattern(rng, t, m, cols, rng.uniform(0.4, 0.9)) for _ in range(k)])
def tf_strip(g):
    return _vjoin(_split_cols(g))
rule("strip_segments_stacked", "The strip is cut at the grey dividers and the segments are stacked top to bottom in left-to-right order, making a block as wide as one segment.", gi_strip, tf_strip)


# ---------- 36 edge markers build a frame ----------
def gi_edge(rng):
    H, W = size(rng, 5, 30); g = blank(H, W); a, b, c, d = [rng.choice(COLOURS) for _ in range(4)]
    g[0][rng.randint(1, W - 2)] = a; g[rng.randint(1, H - 2)][W - 1] = b
    g[H - 1][rng.randint(1, W - 2)] = c; g[rng.randint(1, H - 2)][0] = d
    return g
def tf_edge(g):
    H, W = dims(g); a = max(g[0]); c = max(g[H - 1]); d = max(g[r][0] for r in range(H)); b = max(g[r][W - 1] for r in range(H))
    out = blank(H, W)
    for r in range(H): out[r][0] = d; out[r][W - 1] = b
    out[0] = [a] * W; out[H - 1] = [c] * W
    return out
rule("edge_markers_to_coloured_frame", "The one marker on each edge gives that edge its colour: the output is a frame whose top, right, bottom and left sides take the colours of the markers found there, top and bottom rows covering the corners.", gi_edge, tf_edge)


# ---------- 38 swatch block scaled by marker count ----------
def gi_swblock(rng):
    a, b = rng.randint(2, 3), rng.randint(2, 3); n = rng.randint(2, 4); cols = colours(rng, rng.randint(2, 5), exclude=(0, SEP))
    block = [[rng.choice(cols) for _ in range(b)] for _ in range(a)]
    H, W = size(rng, 8, 30); g = blank(H, W)
    if place_shapes(rng, g, [[(r, c) for r in range(a) for c in range(b)]] + [[(0, 0)]] * n, [1] + [SEP] * n, margin=1) is None: return None
    pos = [(r, c) for r in range(H) for c in range(W) if g[r][c] == 1]; r0, c0 = min(pos)
    paste(g, block, r0, c0)
    return g
def tf_swblock(g):
    n = len(cells(g, lambda v: v == SEP)); blk = max(_blobs(g), key=len); p = _crop_obj(g, blk)
    a, b = dims(p)
    if a * n > 30 or b * n > 30: return None
    return [[p[r // n][c // n] for c in range(b * n)] for r in range(a * n)]
rule("swatch_block_scaled_by_marker_count", "The small block of colours is enlarged so that each of its cells becomes an n by n square, where n is the number of grey marker cells in the grid.", gi_swblock, tf_swblock)


# ---------- 39 tower by size ----------
def gi_tower(rng):
    g = _scene(rng, 2, 5, 2, 8)
    if g is None: return None
    sz = [len(o) for o in objects(g, 0)]
    return g if len(set(sz)) == len(sz) else None
def tf_tower(g):
    obs = sorted(objects(g, 0), key=len)
    return _vjoin([_crop_obj(g, o) for o in obs], gap=0, align="centre")
rule("objects_tower_by_size_centred", "The objects are stacked into a tower, smallest on top and largest at the bottom, each one centred horizontally over the one below.", gi_tower, tf_tower)


# ---------- 40 same-box objects into a square grid in reading order ----------
def gi_sqgrid(rng):
    k = rng.choice([4, 9]); s = rng.randint(2, 4) if k == 4 else rng.randint(2, 3)
    shapes = [_shape_in_box(rng, s, s) for _ in range(k)]
    if any(sh is None for sh in shapes): return None
    H, W = size(rng, 12 if k == 4 else 16, 30); g = blank(H, W)
    if place_shapes(rng, g, shapes, [rng.choice(COLOURS) for _ in range(k)], margin=1) is None: return None
    return g if len(objects(g, 0)) == k else None
def tf_sqgrid(g):
    obs = _reading(g, objects(g, 0)); n = int(round(len(obs) ** 0.5))
    if n * n != len(obs): return None
    crops = [_crop_obj(g, o) for o in obs]; s = len(crops[0])
    if any(dims(p) != (s, s) for p in crops): return None
    out = blank(n * s, n * s)
    for i, p in enumerate(crops):
        paste(out, p, (i // n) * s, (i % n) * s)
    return out
rule("objects_into_square_grid_reading_order", "The equally boxed objects are cut out and packed into a square arrangement (2x2 or 3x3) in reading order, touching, with no background between them.", gi_sqgrid, tf_sqgrid)
