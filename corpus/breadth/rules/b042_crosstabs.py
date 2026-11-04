# b042_crosstabs.py -- 40 rules, theme: cross-tabulation and summary grids (panel/quadrant/ninth/row/
# column/colour tables, presence bitmaps, rank tables, margin and bar summaries). One author.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


def _cap(n):
    return max(0, min(9, int(n)))


def _size(rng, lo=6, hi=18, biglo=21, bighi=30, p_big=0.36):
    if rng.random() < p_big:
        return rng.randint(biglo, bighi), rng.randint(biglo, bighi)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _scene(rng, k_lo, k_hi, n_lo, n_hi, lo=6, hi=18, margin=1, p_big=0.36):
    h, w = _size(rng, lo, hi, p_big=p_big)
    g = blank(h, w)
    k = rng.randint(k_lo, k_hi)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    cols = [rng.choice(COLOURS) for _ in range(k)]
    if place_shapes(rng, g, shapes, cols, margin=margin) is None:
        return None
    return g


def _quads(h, w):
    mh, mw = h // 2, w // 2
    return [(0, 0, mh - 1, mw - 1), (0, mw, mh - 1, w - 1), (mh, 0, h - 1, mw - 1), (mh, mw, h - 1, w - 1)]


def _ninths(h, w):
    r1, r2 = h // 3, 2 * h // 3
    c1, c2 = w // 3, 2 * w // 3
    rb = [(0, r1 - 1), (r1, r2 - 1), (r2, h - 1)]
    cb = [(0, c1 - 1), (c1, c2 - 1), (c2, w - 1)]
    return [[(r0, c0, r1b, c1b) for (c0, c1b) in cb] for (r0, r1b) in rb]


def _box_count(g, box, col=None, exclude=(0,)):
    r0, c0, r1, c1 = box
    n = 0
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            v = g[r][c]
            if col is not None:
                if v == col: n += 1
            elif v not in exclude:
                n += 1
    return n


def _box_dominant(g, box, exclude=(0,)):
    cnt = {}
    r0, c0, r1, c1 = box
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            v = g[r][c]
            if v in exclude: continue
            cnt[v] = cnt.get(v, 0) + 1
    return max(cnt.items(), key=lambda kv: kv[1])[0] if cnt else 0


def _box_distinct(g, box, exclude=(0,)):
    s = set()
    r0, c0, r1, c1 = box
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if g[r][c] not in exclude: s.add(g[r][c])
    return s


def _sep_info(g):
    h, w = dims(g)
    pts_by_colour = {}
    for r in range(h):
        for c in range(w):
            v = g[r][c]
            if v == 0: continue
            pts_by_colour.setdefault(v, []).append((r, c))
    for v, pts in pts_by_colour.items():
        full_rows = {r for r in range(h) if all(g[r][c] == v for c in range(w))}
        full_cols = {c for c in range(w) if all(g[r][c] == v for r in range(h))}
        if not full_rows and not full_cols:
            continue
        if all((r in full_rows) or (c in full_cols) for r, c in pts):
            return v, sorted(full_rows), sorted(full_cols)
    return None


def _panel_boxes(g):
    info = _sep_info(g)
    if info is None: return None
    v, sep_rows, sep_cols = info
    h, w = dims(g)
    rbnd = [-1] + sep_rows + [h]
    cbnd = [-1] + sep_cols + [w]
    rows = [(rbnd[i] + 1, rbnd[i + 1] - 1) for i in range(len(rbnd) - 1) if rbnd[i + 1] - 1 >= rbnd[i] + 1]
    cols = [(cbnd[j] + 1, cbnd[j + 1] - 1) for j in range(len(cbnd) - 1) if cbnd[j + 1] - 1 >= cbnd[j] + 1]
    if len(rows) < 1 or len(cols) < 1 or len(rows) * len(cols) < 2:
        return None
    return v, [[(r0, c0, r1, c1) for (c0, c1) in cols] for (r0, r1) in rows]


def _panel_scene(rng, nr, nc, big=False, shapes_per=(1, 3)):
    sep = rng.choice(COLOURS)
    other = [c for c in COLOURS if c != sep]
    span = (6, 9) if big else (3, 5)
    phs = [rng.randint(*span) for _ in range(nr)]
    pws = [rng.randint(*span) for _ in range(nc)]
    h = sum(phs) + (nr - 1); w = sum(pws) + (nc - 1)
    g = blank(h, w)
    rstarts, rc = [], 0
    for i, hh in enumerate(phs):
        rstarts.append(rc); rc += hh
        if i < nr - 1:
            for c in range(w): g[rc][c] = sep
            rc += 1
    cstarts, cc = [], 0
    for j, ww in enumerate(pws):
        cstarts.append(cc); cc += ww
        if j < nc - 1:
            for r in range(h): g[r][cc] = sep
            cc += 1
    pal = rng.sample(other, min(len(other), max(2, min(5, nr * nc + 1))))
    for i in range(nr):
        for j in range(nc):
            r0, c0 = rstarts[i], cstarts[j]
            for _ in range(rng.randint(*shapes_per)):
                col = rng.choice(pal)
                rr = rng.randrange(r0, r0 + phs[i]); cc2 = rng.randrange(c0, c0 + pws[j])
                g[rr][cc2] = col
    return g, pal


# ---------- panel family ----------

# 1 panel count table: distinct non-background colours per panel, as a digit.
def gi_panel_distinct(rng):
    nr, nc = rng.randint(2, 3), rng.randint(2, 3)
    big = rng.random() < 0.4
    g, pal = _panel_scene(rng, nr, nc, big=big, shapes_per=(1, 4))
    return g
def tf_panel_distinct(g):
    pb = _panel_boxes(g)
    if pb is None: return None
    sep, boxes = pb
    return [[_cap(len(_box_distinct(g, b, exclude=(0, sep)))) for b in row] for row in boxes]
rule("panel_distinct_colour_count_digit_grid", "Each panel of the separator-divided grid becomes one cell holding the count of distinct colours it contains, as a digit.", gi_panel_distinct, tf_panel_distinct, digits=True)


# 2 panel dominant colour laid out in the same panel arrangement.
def gi_panel_dom(rng):
    nr, nc = rng.randint(2, 3), rng.randint(2, 3)
    big = rng.random() < 0.4
    g, pal = _panel_scene(rng, nr, nc, big=big, shapes_per=(1, 4))
    return g
def tf_panel_dom(g):
    pb = _panel_boxes(g)
    if pb is None: return None
    sep, boxes = pb
    return [[_box_dominant(g, b, exclude=(0, sep)) for b in row] for row in boxes]
rule("panel_dominant_colour_layout", "Each panel is replaced by one cell holding its most common non-background colour, keeping the panel grid's own layout.", gi_panel_dom, tf_panel_dom)


# 3 which panels are identical to the first panel (two colours).
def gi_panel_ident(rng):
    nr, nc = rng.randint(2, 3), rng.randint(2, 3)
    big = rng.random() < 0.35
    sep = rng.choice(COLOURS)
    other = [c for c in COLOURS if c != sep]
    span = (7, 9) if big else (4, 5)
    k = rng.choice(list(span))
    h = nr * k + (nr - 1); w = nc * k + (nc - 1)
    g = blank(h, w)
    for i in range(1, nr):
        rr = i * k + (i - 1)
        for c in range(w): g[rr][c] = sep
    for j in range(1, nc):
        cc = j * k + (j - 1)
        for r in range(h): g[r][cc] = sep
    panel = blank(k, k)
    pal = rng.sample(other, 2)
    for _ in range(rng.randint(2, k * k // 2)):
        panel[rng.randrange(k)][rng.randrange(k)] = rng.choice(pal)
    reps = 0
    for i in range(nr):
        for j in range(nc):
            r0 = i * k + i; c0 = j * k + j
            use = panel if (i == 0 and j == 0) or rng.random() < 0.5 else [[0] * k for _ in range(k)]
            if use is panel: reps += 1
            for r in range(k):
                for c in range(k):
                    g[r0 + r][c0 + c] = use[r][c] if use is panel else (rng.choice(pal) if rng.random() < 0.3 else 0)
    if reps < 2 or reps >= nr * nc:
        return None
    return g
def tf_panel_ident(g):
    pb = _panel_boxes(g)
    if pb is None: return None
    sep, boxes = pb
    first = crop(g, *boxes[0][0])
    return [[3 if crop(g, *b) == first else 4 for b in row] for row in boxes]
rule("panels_identical_to_first_flag", "Output the panel grid marked colour 3 where a panel's content matches the first panel exactly, colour 4 elsewhere.", gi_panel_ident, tf_panel_ident)


# 4 fill count per panel as a horizontal bar chart, one row per panel in reading order.
def gi_panel_bars(rng):
    nr, nc = rng.randint(2, 3), rng.randint(2, 2)
    big = rng.random() < 0.4
    g, pal = _panel_scene(rng, nr, nc, big=big, shapes_per=(0, 4))
    return g
def tf_panel_bars(g):
    pb = _panel_boxes(g)
    if pb is None: return None
    sep, boxes = pb
    flat = [b for row in boxes for b in row]
    counts = [_cap(_box_count(g, b, exclude=(0, sep))) for b in flat]
    if len(set(counts)) < 2: return None
    out = blank(len(flat), 10)
    for i, n in enumerate(counts):
        for c in range(n): out[i][c] = 5
    return out
rule("panel_fillcount_bars_row", "Each panel's filled-cell count (capped at 9) becomes a bar of colour 5 in a row, one row per panel in reading order.", gi_panel_bars, tf_panel_bars)


# 5 panels flagged by whether they are at least half filled.
def gi_panel_half(rng):
    nr, nc = rng.randint(2, 3), rng.randint(2, 3)
    big = rng.random() < 0.4
    sep = rng.choice(COLOURS)
    other = [c for c in COLOURS if c != sep]
    span = (6, 9) if big else (4, 6)
    phs = [rng.randint(*span) for _ in range(nr)]
    pws = [rng.randint(*span) for _ in range(nc)]
    h = sum(phs) + (nr - 1); w = sum(pws) + (nc - 1)
    g = blank(h, w)
    rstarts, rc = [], 0
    for i, hh in enumerate(phs):
        rstarts.append(rc); rc += hh
        if i < nr - 1:
            for c in range(w): g[rc][c] = sep
            rc += 1
    cstarts, cc = [], 0
    for j, ww in enumerate(pws):
        cstarts.append(cc); cc += ww
        if j < nc - 1:
            for r in range(h): g[r][cc] = sep
            cc += 1
    n_dense, n_total = 0, nr * nc
    for i in range(nr):
        for j in range(nc):
            r0, c0 = rstarts[i], cstarts[j]
            dense = rng.random() < 0.5
            n_dense += dense
            area = phs[i] * pws[j]
            k = rng.randint(area * 6 // 10, area) if dense else rng.randint(0, area * 2 // 10)
            cellset = [(r0 + r, c0 + c) for r in range(phs[i]) for c in range(pws[j])]
            for r, c in rng.sample(cellset, min(k, len(cellset))):
                g[r][c] = rng.choice(other)
    if n_dense == 0 or n_dense == n_total:
        return None
    return g
def tf_panel_half(g):
    pb = _panel_boxes(g)
    if pb is None: return None
    sep, boxes = pb
    out = []
    for row in boxes:
        orow = []
        for (r0, c0, r1, c1) in row:
            area = (r1 - r0 + 1) * (c1 - c0 + 1)
            n = _box_count(g, (r0, c0, r1, c1), exclude=(0, sep))
            orow.append(6 if n * 2 >= area else 7)
        out.append(orow)
    return out
rule("panel_majority_half_flag_grid", "Output the panel grid marked colour 6 where at least half a panel's cells are filled, colour 7 otherwise.", gi_panel_half, tf_panel_half)


# 6 count of a fixed key colour per panel as a digit grid.
def gi_panel_key(rng):
    nr, nc = rng.randint(2, 3), rng.randint(2, 3)
    big = rng.random() < 0.4
    g, pal = _panel_scene(rng, nr, nc, big=big, shapes_per=(1, 4))
    return g
def tf_panel_key(g):
    pb = _panel_boxes(g)
    if pb is None: return None
    sep, boxes = pb
    present = sorted(_box_distinct(g, (0, 0, len(g) - 1, len(g[0]) - 1), exclude=(0, sep)))
    if not present: return None
    key = present[0]
    return [[_cap(_box_count(g, b, col=key)) for b in row] for row in boxes]
rule("panel_key_colour_count_digit_grid", "A key colour is the lowest-valued colour present; each panel becomes a digit cell counting that colour's occurrences inside it.", gi_panel_key, tf_panel_key, digits=True)


# ---------- quadrant family ----------

# 7 colour by quadrant count table.
def gi_quad_table(rng):
    return _scene(rng, 3, 7, 2, 8, lo=8, hi=18, p_big=0.3)
def tf_quad_table(g):
    h, w = dims(g)
    if h < 4 or w < 4: return None
    quads = _quads(h, w)
    present = sorted(set(v for row in g for v in row if v != 0))[:9]
    if not present: return None
    return [[_cap(_box_count(g, q, col=col)) for q in quads] for col in present]
rule("colour_quadrant_count_table", "Build a table: one row per colour present, one column per quadrant (TL,TR,BL,BR), each cell the colour's cell count in that quadrant as a digit.", gi_quad_table, tf_quad_table, digits=True)


# 8 object centroid count per quadrant, 2x2 digit grid.
def gi_quad_centroid(rng):
    return _scene(rng, 3, 8, 2, 6, lo=8, hi=18, p_big=0.3)
def tf_quad_centroid(g):
    h, w = dims(g)
    if h < 4 or w < 4: return None
    obs = objects(g, 0)
    if len(obs) < 2: return None
    mh, mw = h // 2, w // 2
    tl = tr = bl = br = 0
    for o in obs:
        rs = sum(r for r, _ in o) / len(o); cs = sum(c for _, c in o) / len(o)
        if rs < mh and cs < mw: tl += 1
        elif rs < mh: tr += 1
        elif cs < mw: bl += 1
        else: br += 1
    return [[_cap(tl), _cap(tr)], [_cap(bl), _cap(br)]]
rule("quadrant_object_centroid_count_digits", "Output a 2x2 digit grid counting how many objects have their centroid in each quadrant.", gi_quad_centroid, tf_quad_centroid, digits=True)


# 9 dominant colour per quadrant, 2x2 grid.
def gi_quad_dom(rng):
    return _scene(rng, 3, 8, 2, 7, lo=8, hi=18, p_big=0.3)
def tf_quad_dom(g):
    h, w = dims(g)
    if h < 4 or w < 4: return None
    quads = _quads(h, w)
    vals = [_box_dominant(g, q) for q in quads]
    if len(set(vals)) < 2: return None
    return [vals[:2], vals[2:]]
rule("quadrant_dominant_colour_2x2", "Output a 2x2 grid where each cell is the most common non-background colour of the matching quadrant.", gi_quad_dom, tf_quad_dom)


# ---------- ninths family ----------

# 10 3x3 summary of dominant colour per ninth.
def gi_ninths_dom(rng):
    return _scene(rng, 4, 9, 2, 7, lo=9, hi=20, p_big=0.3)
def tf_ninths_dom(g):
    h, w = dims(g)
    if h < 3 or w < 3: return None
    boxes = _ninths(h, w)
    out = [[_box_dominant(g, b) for b in row] for row in boxes]
    if len(set(v for row in out for v in row)) < 2: return None
    return out
rule("ninths_dominant_colour_grid", "Divide the grid into a 3x3 block of ninths; each output cell is the dominant colour of the corresponding ninth.", gi_ninths_dom, tf_ninths_dom)


# 11 3x3 fill density digit grid per ninth.
def gi_ninths_den(rng):
    return _scene(rng, 4, 9, 2, 7, lo=9, hi=20, p_big=0.3)
def tf_ninths_den(g):
    h, w = dims(g)
    if h < 3 or w < 3: return None
    boxes = _ninths(h, w)
    return [[_cap(_box_count(g, b)) for b in row] for row in boxes]
rule("ninths_fill_density_digit_grid", "Divide the grid into a 3x3 block of ninths; each output cell is a digit counting that ninth's filled cells, capped at 9.", gi_ninths_den, tf_ninths_den, digits=True)


# ---------- row family ----------

# 12 row-wise object touch count column.
def gi_row_touch(rng):
    return _scene(rng, 3, 8, 2, 6, lo=8, hi=20, p_big=0.3)
def tf_row_touch(g):
    h, w = dims(g)
    obs = objects(g, 0)
    if len(obs) < 2: return None
    out = blank(h, 1)
    for r in range(h):
        n = sum(1 for o in obs if any(rr == r for rr, _ in o))
        out[r][0] = _cap(n)
    return out
rule("row_object_touch_count_column", "Output one column: each row's cell is a digit counting how many distinct objects touch that row.", gi_row_touch, tf_row_touch, digits=True)


# 13 row-wise distinct colour count column.
def gi_row_dcount(rng):
    return _scene(rng, 3, 8, 2, 6, lo=8, hi=20, p_big=0.3)
def tf_row_dcount(g):
    h, w = dims(g)
    out = blank(h, 1)
    for r in range(h):
        out[r][0] = _cap(len(set(v for v in g[r] if v != 0)))
    if len(set(v for row in out for v in row)) < 2: return None
    return out
rule("row_distinct_colour_count_column", "Output one column: each row's cell is a digit counting the distinct non-background colours in that row.", gi_row_dcount, tf_row_dcount, digits=True)


# 14 row-wise majority object colour column.
def gi_row_majcol(rng):
    return _scene(rng, 3, 8, 2, 6, lo=8, hi=20, p_big=0.3)
def tf_row_majcol(g):
    h, w = dims(g)
    obs = objects(g, 0)
    if len(obs) < 2: return None
    out = blank(h, 1)
    for r in range(h):
        cnt = {}
        for o in obs:
            if any(rr == r for rr, _ in o):
                col = g[o[0][0]][o[0][1]]
                cnt[col] = cnt.get(col, 0) + 1
        if cnt:
            out[r][0] = max(cnt.items(), key=lambda kv: (kv[1], -kv[0]))[0]
    if len(set(v for row in out for v in row)) < 2: return None
    return out
rule("row_majority_object_colour_column", "Output one column: each row's cell holds the colour whose objects most often touch that row.", gi_row_majcol, tf_row_majcol)


# 15 row transition count bars.
def gi_row_trans(rng):
    h, w = _size(rng, lo=8, hi=18, p_big=0.3)
    g = blank(h, w)
    cols = colours(rng, rng.randint(2, 4))
    for r in range(h):
        c = 0
        while c < w:
            run = rng.randint(1, 4)
            col = rng.choice([0] + cols)
            for cc in range(c, min(c + run, w)): g[r][cc] = col
            c += run
    return g
def tf_row_trans(g):
    h, w = dims(g)
    trans = [sum(1 for c in range(w - 1) if g[r][c] != g[r][c + 1]) for r in range(h)]
    m = max(trans)
    if m < 1 or len(set(trans)) < 2: return None
    out = blank(h, m)
    for r, t in enumerate(trans):
        for c in range(t): out[r][c] = 5
    return out
rule("row_transition_count_bars", "Each row's number of colour-to-colour transitions becomes a bar of colour 5 of that length.", gi_row_trans, tf_row_trans)


# 16 row longest-run colour kept, rest erased.
def gi_row_run(rng):
    h, w = _size(rng, lo=8, hi=20, p_big=0.3)
    g = blank(h, w)
    cols = colours(rng, rng.randint(2, 4))
    for r in range(h):
        c = 0
        while c < w:
            run = rng.randint(1, 5)
            col = rng.choice(cols)
            for cc in range(c, min(c + run, w)): g[r][cc] = col
            c += run
    return g
def tf_row_run(g):
    h, w = dims(g)
    out = blank(h, w)
    for r in range(h):
        best_col, best_len, c = None, 0, 0
        while c < w:
            cc = c
            while cc < w and g[r][cc] == g[r][c]: cc += 1
            if g[r][c] != 0 and cc - c > best_len:
                best_len, best_col = cc - c, g[r][c]
            c = cc
        if best_col is not None:
            for c in range(w):
                if g[r][c] == best_col: out[r][c] = best_col
    return out
rule("row_longest_run_colour_erase_rest", "In each row, only the colour forming the longest contiguous run survives; every other cell is cleared to background.", gi_row_run, tf_row_run)


# 17 row mode colour count column.
def gi_row_mode(rng):
    return _scene(rng, 3, 8, 2, 6, lo=8, hi=20, p_big=0.3)
def tf_row_mode(g):
    h, w = dims(g)
    out = blank(h, 1)
    for r in range(h):
        cnt = {}
        for v in g[r]:
            if v != 0: cnt[v] = cnt.get(v, 0) + 1
        if cnt: out[r][0] = _cap(max(cnt.values()))
    if len(set(v for row in out for v in row)) < 2: return None
    return out
rule("row_mode_colour_count_column", "Output one column: each row's cell is a digit counting the occurrences of that row's single most frequent non-background colour.", gi_row_mode, tf_row_mode, digits=True)


# ---------- column family ----------

# 18 column object touch count row.
def gi_col_touch(rng):
    return _scene(rng, 3, 8, 2, 6, lo=8, hi=20, p_big=0.3)
def tf_col_touch(g):
    h, w = dims(g)
    obs = objects(g, 0)
    if len(obs) < 2: return None
    out = blank(1, w)
    for c in range(w):
        n = sum(1 for o in obs if any(cc == c for _, cc in o))
        out[0][c] = _cap(n)
    return out
rule("column_object_touch_count_row", "Output one row: each column's cell is a digit counting how many distinct objects touch that column.", gi_col_touch, tf_col_touch, digits=True)


# 19 column distinct colour count row.
def gi_col_dcount(rng):
    return _scene(rng, 3, 8, 2, 6, lo=8, hi=20, p_big=0.3)
def tf_col_dcount(g):
    h, w = dims(g)
    out = blank(1, w)
    for c in range(w):
        out[0][c] = _cap(len(set(g[r][c] for r in range(h) if g[r][c] != 0)))
    if len(set(v for row in out for v in row)) < 2: return None
    return out
rule("column_distinct_colour_count_row", "Output one row: each column's cell is a digit counting the distinct non-background colours in that column.", gi_col_dcount, tf_col_dcount, digits=True)


# 20 column majority object colour row.
def gi_col_majcol(rng):
    return _scene(rng, 3, 8, 2, 6, lo=8, hi=20, p_big=0.3)
def tf_col_majcol(g):
    h, w = dims(g)
    obs = objects(g, 0)
    if len(obs) < 2: return None
    out = blank(1, w)
    for c in range(w):
        cnt = {}
        for o in obs:
            if any(cc == c for _, cc in o):
                col = g[o[0][0]][o[0][1]]
                cnt[col] = cnt.get(col, 0) + 1
        if cnt:
            out[0][c] = max(cnt.items(), key=lambda kv: (kv[1], -kv[0]))[0]
    if len(set(v for row in out for v in row)) < 2: return None
    return out
rule("column_majority_object_colour_row", "Output one row: each column's cell holds the colour whose objects most often touch that column.", gi_col_majcol, tf_col_majcol)


# ---------- colour family ----------

def _colour_cells(g, col):
    return cells(g, lambda v: v == col)

# 21 per-colour bounding box area bars.
def gi_col_bbox_bars(rng):
    return _scene(rng, 3, 7, 2, 8, lo=8, hi=20, p_big=0.3)
def tf_col_bbox_bars(g):
    h, w = dims(g)
    present = sorted(set(v for row in g for v in row if v != 0))
    if len(present) < 2: return None
    out = blank(len(present), w)
    for i, col in enumerate(present):
        pts = _colour_cells(g, col)
        r0, c0, r1, c1 = bbox(pts)
        area = (r1 - r0 + 1) * (c1 - c0 + 1)
        n = min(area, w)
        for c in range(n): out[i][c] = col
    return out
rule("colour_bbox_area_bars", "One row per colour present (ascending), a bar of that colour as long as its bounding-box area, capped to the grid width.", gi_col_bbox_bars, tf_col_bbox_bars)


# 22 per-colour cell count digit column.
def gi_col_count_col(rng):
    return _scene(rng, 3, 7, 2, 8, lo=8, hi=20, p_big=0.3)
def tf_col_count_col(g):
    present = sorted(set(v for row in g for v in row if v != 0))
    if len(present) < 2: return None
    out = blank(len(present), 1)
    for i, col in enumerate(present):
        out[i][0] = _cap(sum(1 for row in g for v in row if v == col))
    return out
rule("colour_cellcount_digit_column", "One row per colour present (ascending), the cell holding a digit of that colour's total cell count, capped at 9.", gi_col_count_col, tf_col_count_col, digits=True)


# 23 per-colour object count bars.
def gi_col_obj_bars(rng):
    return _scene(rng, 3, 6, 2, 6, lo=8, hi=20, p_big=0.3)
def tf_col_obj_bars(g):
    obs = objects(g, 0)
    present = sorted(set(v for row in g for v in row if v != 0))
    if len(present) < 2: return None
    w = len(g[0])
    out = blank(len(present), w)
    vals = []
    for i, col in enumerate(present):
        n = sum(1 for o in obs if g[o[0][0]][o[0][1]] == col)
        vals.append(n)
        for c in range(min(n, w)): out[i][c] = col
    if len(set(vals)) < 2: return None
    return out
rule("colour_object_count_bars", "One row per colour present (ascending), a bar of that colour as long as the number of separate objects of that colour.", gi_col_obj_bars, tf_col_obj_bars)


# 24 per-colour mean row position as a single dot.
def gi_col_meanpos(rng):
    return _scene(rng, 3, 7, 2, 7, lo=8, hi=20, p_big=0.3)
def tf_col_meanpos(g):
    h, w = dims(g)
    present = sorted(set(v for row in g for v in row if v != 0))[:9]
    if len(present) < 2: return None
    out = blank(h, len(present))
    for i, col in enumerate(present):
        pts = _colour_cells(g, col)
        mr = round(sum(r for r, _ in pts) / len(pts))
        out[min(mr, h - 1)][i] = col
    return out
rule("colour_mean_row_position_dots", "One column per colour present; each column's cell at that colour's mean row position holds the colour, the rest background.", gi_col_meanpos, tf_col_meanpos)


# 25 per-colour bounding box max-side bars.
def gi_col_aspect_bars(rng):
    return _scene(rng, 3, 7, 2, 8, lo=8, hi=20, p_big=0.3)
def tf_col_aspect_bars(g):
    h, w = dims(g)
    present = sorted(set(v for row in g for v in row if v != 0))
    if len(present) < 2: return None
    out = blank(len(present), max(h, w))
    for i, col in enumerate(present):
        pts = _colour_cells(g, col)
        r0, c0, r1, c1 = bbox(pts)
        n = max(r1 - r0 + 1, c1 - c0 + 1)
        for c in range(n): out[i][c] = col
    return out
rule("colour_bbox_aspect_bars", "One row per colour present (ascending), a bar of that colour as long as the longer side of its bounding box.", gi_col_aspect_bars, tf_col_aspect_bars)


# ---------- two-row / pair tables ----------

# 26 two-row summary: colours on the top row, their total counts below.
def gi_top_two_row(rng):
    g = _scene(rng, 3, 7, 2, 6, lo=8, hi=20, p_big=0.3, margin=0)
    if g is None: return None
    w = len(g[0])
    cols = colours(rng, rng.randint(2, min(4, w)))
    for i, c in enumerate(rng.sample(range(w), len(cols))):
        g[0][c] = cols[i]
    return g
def tf_top_two_row(g):
    seen = []
    for v in g[0]:
        if v != 0 and v not in seen: seen.append(v)
    seen = seen[:9]
    if len(seen) < 2: return None
    row0, row1 = [], []
    for col in seen:
        row0.append(col)
        row1.append(_cap(sum(1 for row in g for v in row if v == col)))
    return [row0, row1]
rule("top_row_colour_counts_two_row_summary", "List each colour found on the grid's top row left to right; below each, the digit count of that colour's total cells in the grid.", gi_top_two_row, tf_top_two_row, digits=True)


# 27 border vs interior non-background count pair.
def gi_border_pair(rng):
    return _scene(rng, 3, 8, 2, 7, lo=8, hi=20, p_big=0.3)
def tf_border_pair(g):
    h, w = dims(g)
    if h < 3 or w < 3: return None
    border = interior = 0
    for r in range(h):
        for c in range(w):
            if g[r][c] == 0: continue
            if r in (0, h - 1) or c in (0, w - 1): border += 1
            else: interior += 1
    return [[_cap(border), _cap(interior)]]
rule("border_vs_interior_count_pair", "Output a single 1x2 row: digit count of non-background cells on the border, then a digit count of those in the interior.", gi_border_pair, tf_border_pair, digits=True)


# 28 colour presence quadrant bitmap.
def gi_quad_bitmap(rng):
    return _scene(rng, 3, 7, 2, 7, lo=8, hi=18, p_big=0.3)
def tf_quad_bitmap(g):
    h, w = dims(g)
    if h < 4 or w < 4: return None
    quads = _quads(h, w)
    present = sorted(set(v for row in g for v in row if v != 0))
    if len(present) < 2: return None
    return [[1 if _box_count(g, q, col=col) > 0 else 0 for q in quads] for col in present]
rule("colour_presence_quadrant_bitmap", "One row per colour present, one column per quadrant: 1 if that colour appears anywhere in the quadrant, else 0.", gi_quad_bitmap, tf_quad_bitmap, digits=True)


# 29 row-wise leftmost/rightmost colour pair table.
def gi_row_pair(rng):
    return _scene(rng, 3, 8, 2, 6, lo=8, hi=20, p_big=0.3)
def tf_row_pair(g):
    h, w = dims(g)
    out = blank(h, 2)
    for r in range(h):
        nz = [v for v in g[r] if v != 0]
        if nz:
            left = next(v for v in g[r] if v != 0)
            right = next(v for v in reversed(g[r]) if v != 0)
            out[r][0], out[r][1] = left, right
    if len(set(v for row in out for v in row)) < 2: return None
    return out
# row_leftright_colour_pair_table dropped 2026-10-12 (trio review: behavioural duplicate or one global operation)
# 30 column-wise topmost/bottommost colour pair table.
def gi_col_pair(rng):
    return _scene(rng, 3, 8, 2, 6, lo=8, hi=20, p_big=0.3)
def tf_col_pair(g):
    h, w = dims(g)
    out = blank(2, w)
    for c in range(w):
        col_vals = [g[r][c] for r in range(h) if g[r][c] != 0]
        if col_vals:
            top = next(g[r][c] for r in range(h) if g[r][c] != 0)
            bot = next(g[r][c] for r in reversed(range(h)) if g[r][c] != 0)
            out[0][c], out[1][c] = top, bot
    if len(set(v for row in out for v in row)) < 2: return None
    return out
rule("column_topbottom_colour_pair_table", "Output a two-row table: each column's topmost and bottommost non-background colours (background if the column is empty).", gi_col_pair, tf_col_pair)


# 31 per-colour quadrant rank table.
def gi_quad_rank(rng):
    return _scene(rng, 3, 7, 2, 7, lo=9, hi=18, p_big=0.3)
def tf_quad_rank(g):
    h, w = dims(g)
    if h < 4 or w < 4: return None
    quads = _quads(h, w)
    present = sorted(set(v for row in g for v in row if v != 0))
    if len(present) < 2: return None
    out = []
    for col in present:
        counts4 = [_box_count(g, q, col=col) for q in quads]
        order = sorted(range(4), key=lambda i: (-counts4[i], i))
        ranks = [0] * 4
        for rank, i in enumerate(order, 1):
            ranks[i] = rank if counts4[i] > 0 else 0
        out.append(ranks)
    return out
rule("colour_quadrant_rank_table", "One row per colour present: rank (1 busiest to 4 emptiest) of each quadrant by that colour's cell count there, 0 if absent.", gi_quad_rank, tf_quad_rank, digits=True)


# 32 per-colour above-mean-count flag column.
def gi_above_mean(rng):
    return _scene(rng, 4, 8, 2, 7, lo=8, hi=20, p_big=0.3)
def tf_above_mean(g):
    present = sorted(set(v for row in g for v in row if v != 0))
    if len(present) < 3: return None
    counts = {col: sum(1 for row in g for v in row if v == col) for col in present}
    mean = sum(counts.values()) / len(counts)
    out = [[1 if counts[col] >= mean else 0] for col in present]
    if len(set(v[0] for v in out)) < 2: return None
    return out
rule("colour_count_above_mean_flag_column", "One row per colour present: 1 if its total cell count is at least the mean count across colours, else 0.", gi_above_mean, tf_above_mean, digits=True)


# 33 colour by top/bottom half count table.
def gi_half_tb(rng):
    return _scene(rng, 3, 7, 2, 7, lo=8, hi=20, p_big=0.3)
def tf_half_tb(g):
    h, w = dims(g)
    if h < 2: return None
    mh = h // 2
    present = sorted(set(v for row in g for v in row if v != 0))
    if len(present) < 2: return None
    return [[_cap(_box_count(g, (0, 0, mh - 1, w - 1), col=col)), _cap(_box_count(g, (mh, 0, h - 1, w - 1), col=col))] for col in present]
rule("colour_tophalf_bothalf_count_table", "One row per colour present: digit count of its cells in the top half, then in the bottom half.", gi_half_tb, tf_half_tb, digits=True)


# 34 colour by left/right half count table.
def gi_half_lr(rng):
    return _scene(rng, 3, 7, 2, 7, lo=8, hi=20, p_big=0.3)
def tf_half_lr(g):
    h, w = dims(g)
    if w < 2: return None
    mw = w // 2
    present = sorted(set(v for row in g for v in row if v != 0))
    if len(present) < 2: return None
    return [[_cap(_box_count(g, (0, 0, h - 1, mw - 1), col=col)), _cap(_box_count(g, (0, mw, h - 1, w - 1), col=col))] for col in present]
rule("colour_lefthalf_righthalf_count_table", "One row per colour present: digit count of its cells in the left half, then in the right half.", gi_half_lr, tf_half_lr, digits=True)


# 35 colour by row-third presence bitmap.
def gi_band_bitmap(rng):
    return _scene(rng, 3, 7, 2, 7, lo=9, hi=20, p_big=0.3)
def tf_band_bitmap(g):
    h, w = dims(g)
    if h < 3: return None
    r1, r2 = h // 3, 2 * h // 3
    bands = [(0, 0, r1 - 1, w - 1), (r1, 0, r2 - 1, w - 1), (r2, 0, h - 1, w - 1)]
    present = sorted(set(v for row in g for v in row if v != 0))
    if len(present) < 2: return None
    return [[1 if _box_count(g, b, col=col) > 0 else 0 for b in bands] for col in present]
rule("colour_band_presence_bitmap", "Split the grid into top, middle and bottom thirds; one row per colour present, 1 if it appears in that third else 0.", gi_band_bitmap, tf_band_bitmap, digits=True)


# 36 longest-run colour per row, compact column.
def gi_row_run_col(rng):
    h, w = _size(rng, lo=8, hi=20, p_big=0.3)
    g = blank(h, w)
    cols = colours(rng, rng.randint(2, 4))
    for r in range(h):
        c = 0
        while c < w:
            run = rng.randint(1, 5)
            col = rng.choice(cols)
            for cc in range(c, min(c + run, w)): g[r][cc] = col
            c += run
    return g
def tf_row_run_col(g):
    h, w = dims(g)
    out = blank(h, 1)
    for r in range(h):
        best_col, best_len, c = 0, 0, 0
        while c < w:
            cc = c
            while cc < w and g[r][cc] == g[r][c]: cc += 1
            if g[r][c] != 0 and cc - c > best_len:
                best_len, best_col = cc - c, g[r][c]
            c = cc
        out[r][0] = best_col
    if len(set(v for row in out for v in row)) < 2: return None
    return out
rule("row_longest_run_colour_column", "Output one column: each row's cell holds the colour of that row's longest contiguous run (background if none).", gi_row_run_col, tf_row_run_col)


# 37 row mode-vs-second margin digit column.
def gi_row_margin(rng):
    return _scene(rng, 3, 8, 2, 6, lo=8, hi=20, p_big=0.3)
def tf_row_margin(g):
    h, w = dims(g)
    out = blank(h, 1)
    for r in range(h):
        cnt = {}
        for v in g[r]:
            if v != 0: cnt[v] = cnt.get(v, 0) + 1
        vals = sorted(cnt.values(), reverse=True)
        if vals:
            margin = vals[0] - (vals[1] if len(vals) > 1 else 0)
            out[r][0] = _cap(margin)
    if len(set(v for row in out for v in row)) < 2: return None
    return out
rule("row_mode_margin_digit_column", "Output one column: each row's cell is a digit for how far the row's most frequent colour's count leads the second most frequent.", gi_row_margin, tf_row_margin, digits=True)


# 38 column run count bars.
def gi_col_runbars(rng):
    h, w = _size(rng, lo=8, hi=18, p_big=0.3)
    g = blank(h, w)
    cols = colours(rng, rng.randint(2, 4))
    for c in range(w):
        r = 0
        while r < h:
            run = rng.randint(1, 4)
            col = rng.choice([0] + cols)
            for rr in range(r, min(r + run, h)): g[rr][c] = col
            r += run
    return g
def tf_col_runbars(g):
    h, w = dims(g)
    runs = []
    for c in range(w):
        n, r = 0, 0
        while r < h:
            rr = r
            while rr < h and g[rr][c] == g[r][c]: rr += 1
            n += 1
            r = rr
        runs.append(_cap(n))
    if len(set(runs)) < 2: return None
    m = max(runs)
    out = blank(m, w)
    for c, n in enumerate(runs):
        for r in range(n): out[m - 1 - r][c] = 5
    return out
rule("column_run_count_bars", "Each column's number of vertical colour runs (capped at 9) becomes a bar of colour 5 rising from the bottom.", gi_col_runbars, tf_col_runbars)


# 39 colour by diagonal-half count table (square grids).
def gi_diag_table(rng):
    n = rng.randint(21, 28) if rng.random() < 0.34 else rng.randint(8, 18)
    g = blank(n, n)
    cols = colours(rng, rng.randint(3, 6))
    for _ in range(rng.randint(n, n * n // 2)):
        g[rng.randrange(n)][rng.randrange(n)] = rng.choice(cols)
    return g
def tf_diag_table(g):
    n = len(g)
    present = sorted(set(v for row in g for v in row if v != 0))
    if len(present) < 2: return None
    out = []
    for col in present:
        upper = sum(1 for r in range(n) for c in range(n) if c > r and g[r][c] == col)
        lower = sum(1 for r in range(n) for c in range(n) if r > c and g[r][c] == col)
        out.append([_cap(upper), _cap(lower)])
    return out
rule("diagonal_half_colour_count_table", "Split the square grid by its main diagonal; one row per colour present: digit count above the diagonal, then below it.", gi_diag_table, tf_diag_table, digits=True)


# 40 quadrant distinct-colour richness row.
def gi_quad_rich(rng):
    return _scene(rng, 3, 7, 2, 7, lo=8, hi=18, p_big=0.3)
def tf_quad_rich(g):
    h, w = dims(g)
    if h < 4 or w < 4: return None
    quads = _quads(h, w)
    vals = [_cap(len(_box_distinct(g, q))) for q in quads]
    if len(set(vals)) < 2: return None
    return [vals]
rule("quadrant_richness_distinct_colour_row", "Output a single row of four digits: the number of distinct colours present in each quadrant, TL TR BL BR.", gi_quad_rich, tf_quad_rich, digits=True)
