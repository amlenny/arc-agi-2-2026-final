# b031_equalise.py -- theme: EQUALISING AND BALANCING. 40 rules: grow/trim bars and objects to match
# the largest/smallest, move cells between stacks or halves until balanced, equalise colour/row/column
# counts, level containers, respace gaps evenly. All transforms deterministic; ties broken by reading
# order (row-major, then column).
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


def size_mixed(rng, lo=6, hi=16, big_lo=21, big_hi=30, p_big=0.32):
    """At least ~a third of draws land in the 21-30 band, as AUTHORING.md requires."""
    if rng.random() < p_big:
        return rng.randint(big_lo, big_hi), rng.randint(big_lo, big_hi)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def reading(cells_):
    return sorted(cells_, key=lambda rc: (rc[0], rc[1]))


def multi_blobs(g, bg=0, conn8=True):
    """Connected components ignoring colour (any non-bg cells touching belong together). glib.components
    forces same-colour membership even with a custom pred, so this is a local helper for multi-colour blobs."""
    H, W = dims(g); seen, out = set(), []
    nb = [(-1, 0), (1, 0), (0, -1), (0, 1)] + ([(-1, -1), (-1, 1), (1, -1), (1, 1)] if conn8 else [])
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or g[r][c] == bg:
                continue
            comp, st = [], [(r, c)]; seen.add((r, c))
            while st:
                y, x = st.pop(); comp.append((y, x))
                for dy, dx in nb:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen and g[ny][nx] != bg:
                        seen.add((ny, nx)); st.append((ny, nx))
            out.append(comp)
    return out


# ---------- 1 grow vertical bars up to the tallest ----------
def gi_growv(rng):
    h, w = size_mixed(rng, 6, 14, 21, 30)
    col = rng.choice(COLOURS)
    heights = [rng.randint(0, h) for _ in range(w)]
    if len({x for x in heights if x > 0}) < 2:
        return None
    g = blank(h, w)
    for c, k in enumerate(heights):
        for r in range(h - k, h):
            g[r][c] = col
    return g
def tf_growv(g):
    h, w = dims(g); col = max(v for row in g for v in row)
    if col == 0: return None
    heights = [sum(1 for r in range(h) if g[r][c] == col) for c in range(w)]
    t = max(heights)
    out = blank(h, w)
    for c, k in enumerate(heights):
        k2 = t if k > 0 else 0
        for r in range(h - k2, h): out[r][c] = col
    return out
rule("grow_vbars_to_tallest", "Every non-empty vertical bar grows upward until it is as tall as the tallest bar.", gi_growv, tf_growv)


# ---------- 2 grow horizontal bars right to the widest ----------
def gi_growh(rng):
    h, w = size_mixed(rng, 6, 14, 21, 30)
    col = rng.choice(COLOURS)
    widths = [rng.randint(0, w) for _ in range(h)]
    if len({x for x in widths if x > 0}) < 2:
        return None
    g = blank(h, w)
    for r, k in enumerate(widths):
        for c in range(k): g[r][c] = col
    return g
def tf_growh(g):
    h, w = dims(g); col = max(v for row in g for v in row)
    if col == 0: return None
    widths = [sum(1 for c in range(w) if g[r][c] == col) for r in range(h)]
    t = max(widths)
    out = blank(h, w)
    for r, k in enumerate(widths):
        k2 = t if k > 0 else 0
        for c in range(k2): out[r][c] = col
    return out
rule("grow_hbars_to_widest", "Every non-empty horizontal bar grows rightward until it is as long as the widest bar.", gi_growh, tf_growh)


# ---------- 3 trim vertical bars down to the shortest ----------
def gi_trimv(rng):
    h, w = size_mixed(rng, 6, 14, 21, 30)
    col = rng.choice(COLOURS)
    heights = [rng.randint(1, h) for _ in range(w)]
    if len(set(heights)) < 2:
        return None
    g = blank(h, w)
    for c, k in enumerate(heights):
        for r in range(h - k, h): g[r][c] = col
    return g
def tf_trimv(g):
    h, w = dims(g); col = max(v for row in g for v in row)
    if col == 0: return None
    heights = [sum(1 for r in range(h) if g[r][c] == col) for c in range(w)]
    nz = [x for x in heights if x > 0]
    if not nz: return None
    m = min(nz)
    out = blank(h, w)
    for c, k in enumerate(heights):
        k2 = m if k > 0 else 0
        for r in range(h - k2, h): out[r][c] = col
    return out
rule("trim_vbars_to_shortest", "Every vertical bar is cut down from the top until it is as short as the shortest bar.", gi_trimv, tf_trimv)


# ---------- 4 trim horizontal bars to the shortest ----------
def gi_trimh(rng):
    h, w = size_mixed(rng, 6, 14, 21, 30)
    col = rng.choice(COLOURS)
    widths = [rng.randint(1, w) for _ in range(h)]
    if len(set(widths)) < 2:
        return None
    g = blank(h, w)
    for r, k in enumerate(widths):
        for c in range(k): g[r][c] = col
    return g
def tf_trimh(g):
    h, w = dims(g); col = max(v for row in g for v in row)
    if col == 0: return None
    widths = [sum(1 for c in range(w) if g[r][c] == col) for r in range(h)]
    nz = [x for x in widths if x > 0]
    if not nz: return None
    m = min(nz)
    out = blank(h, w)
    for r, k in enumerate(widths):
        k2 = m if k > 0 else 0
        for c in range(k2): out[r][c] = col
    return out
rule("trim_hbars_to_shortest", "Every horizontal bar is cut from the right until it is as short as the shortest bar.", gi_trimh, tf_trimh)


# ---------- 5 equalise horizontal gaps between full-height vertical bars ----------
def gi_vgaps(rng):
    h, w = size_mixed(rng, 8, 16, 21, 30)
    col = rng.choice(COLOURS); k = rng.randint(3, 5)
    if w < k * 2 - 1: return None
    positions = [0]
    for i in range(1, k):
        room = w - 1 - positions[-1] - (k - i - 1) * 2
        if room < 1: return None
        gap = rng.randint(1, room)
        positions.append(positions[-1] + 1 + gap)
    if positions[-1] >= w: return None
    gaps = [positions[i + 1] - positions[i] - 1 for i in range(k - 1)]
    if len(set(gaps)) < 2: return None
    g = blank(h, w)
    for p in positions:
        for r in range(h): g[r][p] = col
    return g
def tf_vgaps(g):
    h, w = dims(g); col = max(v for row in g for v in row)
    if col == 0: return None
    cols = [c for c in range(w) if g[0][c] == col]
    if len(cols) < 3: return None
    k = len(cols); span = cols[-1] - cols[0]
    total_gap = span - (k - 1)
    if total_gap < 0: return None
    base, rem = divmod(total_gap, k - 1)
    out = blank(h, w); pos = cols[0]
    for r in range(h): out[r][pos] = col
    for i in range(k - 1):
        pos += 1 + base + (1 if i < rem else 0)
        for r in range(h): out[r][pos] = col
    return out
rule("equalise_vbar_horizontal_gaps", "The vertical bars are respaced so every gap between neighbours is the same width, the leftmost bar staying put.", gi_vgaps, tf_vgaps)


# ---------- 6 equalise vertical gaps between full-width horizontal bars ----------
def gi_hgaps(rng):
    h, w = size_mixed(rng, 8, 16, 21, 30)
    col = rng.choice(COLOURS); k = rng.randint(3, 5)
    if h < k * 2 - 1: return None
    positions = [0]
    for i in range(1, k):
        room = h - 1 - positions[-1] - (k - i - 1) * 2
        if room < 1: return None
        gap = rng.randint(1, room)
        positions.append(positions[-1] + 1 + gap)
    if positions[-1] >= h: return None
    gaps = [positions[i + 1] - positions[i] - 1 for i in range(k - 1)]
    if len(set(gaps)) < 2: return None
    g = blank(h, w)
    for p in positions:
        for c in range(w): g[p][c] = col
    return g
def tf_hgaps(g):
    h, w = dims(g); col = max(v for row in g for v in row)
    if col == 0: return None
    rows = [r for r in range(h) if g[r][0] == col]
    if len(rows) < 3: return None
    k = len(rows); span = rows[-1] - rows[0]
    total_gap = span - (k - 1)
    if total_gap < 0: return None
    base, rem = divmod(total_gap, k - 1)
    out = blank(h, w); pos = rows[0]
    for c in range(w): out[pos][c] = col
    for i in range(k - 1):
        pos += 1 + base + (1 if i < rem else 0)
        for c in range(w): out[pos][c] = col
    return out
rule("equalise_hbar_vertical_gaps", "The horizontal bars are respaced so every gap between neighbours is the same height, the topmost bar staying put.", gi_hgaps, tf_hgaps)


# ---------- banded rectangle helper for object-size rules ----------
def _row_bands(rng, h, w, k):
    """k row-bands stacked top to bottom with 1-row gaps, each holding a left-aligned rectangle of a
    random width and the band's full height. Returns g, list of (r0, c0, r1, c1, colour)."""
    if h < k * 2 - 1: return None
    bands, r = [], 0
    rem_rows = h - (k - 1)  # rows available for bands after mandatory 1-row gaps
    heights = []
    for i in range(k):
        left = rem_rows - sum(heights) - (k - 1 - i)
        hh = rng.randint(1, max(1, left))
        heights.append(hh)
    g = blank(h, w); blocks = []; cols_used = []
    r = 0
    for i in range(k):
        rw = rng.randint(1, w)
        col = rng.choice(COLOURS)
        rect(g, r, 0, r + heights[i] - 1, rw - 1, col)
        blocks.append((r, 0, r + heights[i] - 1, rw - 1, col))
        cols_used.append(rw)
        r += heights[i] + 1
    if len(set(cols_used)) < 2: return None
    return g, blocks


def _col_bands(rng, h, w, k):
    """k column-bands left to right with 1-column gaps, each a top-aligned rectangle of random height
    and the band's full width. Returns g, list of (r0, c0, r1, c1, colour)."""
    if w < k * 2 - 1: return None
    rem_cols = w - (k - 1)
    widths = []
    for i in range(k):
        left = rem_cols - sum(widths) - (k - 1 - i)
        ww = rng.randint(1, max(1, left))
        widths.append(ww)
    g = blank(h, w); blocks = []; c = 0; rows_used = []
    for i in range(k):
        rh = rng.randint(1, h)
        col = rng.choice(COLOURS)
        rect(g, 0, c, rh - 1, c + widths[i] - 1, col)
        blocks.append((0, c, rh - 1, c + widths[i] - 1, col))
        rows_used.append(rh)
        c += widths[i] + 1
    if len(set(rows_used)) < 2: return None
    return g, blocks


# ---------- 7 grow each block rightward to the widest block's width ----------
def gi_blockw(rng):
    h, w = size_mixed(rng, 8, 16, 21, 30)
    res = _row_bands(rng, h, w, rng.randint(3, 4))
    return None if res is None else res[0]
def tf_blockw(g):
    h, w = dims(g)
    blocks = [(min(r for r in range(h) if g[r][c] for c in [None])) for c in []]
    # recover bands by scanning rows for colour runs
    bands = []
    r = 0
    while r < h:
        row = g[r]
        if any(row):
            r0 = r
            while r < h and any(g[r]):
                r += 1
            r1 = r - 1
            col = max(v for rr in range(r0, r1 + 1) for v in g[rr])
            width = sum(1 for v in g[r0] if v == col)
            bands.append((r0, r1, col, width))
        else:
            r += 1
    if len(bands) < 2: return None
    tgt = max(b[3] for b in bands)
    out = copy(g)
    for r0, r1, col, width in bands:
        for rr in range(r0, r1 + 1):
            for c in range(width, tgt):
                out[rr][c] = col
    return out
rule("grow_object_bbox_width_to_largest", "Each rectangular block grows rightward until it is as wide as the widest block.", gi_blockw, tf_blockw)


# ---------- 8 grow each block downward to the tallest block's height ----------
def gi_blockh(rng):
    h, w = size_mixed(rng, 8, 16, 21, 30)
    res = _col_bands(rng, h, w, rng.randint(3, 4))
    return None if res is None else res[0]
def tf_blockh(g):
    h, w = dims(g)
    cols_t = [[r for r in range(h) if g[r][c]] for c in range(w)]
    bands = []
    c = 0
    while c < w:
        colvals = [g[r][c] for r in range(h)]
        if any(colvals):
            c0 = c
            while c < w and any(g[r][c] for r in range(h)):
                c += 1
            c1 = c - 1
            col = max(v for cc in range(c0, c1 + 1) for v in (g[r][cc] for r in range(h)))
            height = sum(1 for r in range(h) if g[r][c0] == col)
            bands.append((c0, c1, col, height))
        else:
            c += 1
    if len(bands) < 2: return None
    tgt = max(b[3] for b in bands)
    out = copy(g)
    for c0, c1, col, height in bands:
        for cc in range(c0, c1 + 1):
            for r in range(height, tgt):
                out[r][cc] = col
    return out
rule("grow_object_bbox_height_to_largest", "Each rectangular block grows downward until it is as tall as the tallest block.", gi_blockh, tf_blockh)


# ---------- 9 shrink each block's width to the narrowest ----------
def gi_shrinkw(rng):
    h, w = size_mixed(rng, 8, 16, 21, 30)
    res = _row_bands(rng, h, w, rng.randint(3, 4))
    return None if res is None else res[0]
def tf_shrinkw(g):
    h, w = dims(g)
    bands = []; r = 0
    while r < h:
        if any(g[r]):
            r0 = r
            while r < h and any(g[r]): r += 1
            r1 = r - 1
            col = max(v for rr in range(r0, r1 + 1) for v in g[rr])
            width = sum(1 for v in g[r0] if v == col)
            bands.append((r0, r1, col, width))
        else:
            r += 1
    if len(bands) < 2: return None
    tgt = min(b[3] for b in bands)
    out = blank(h, w)
    for r0, r1, col, width in bands:
        for rr in range(r0, r1 + 1):
            for c in range(tgt): out[rr][c] = col
    return out
rule("shrink_object_bbox_width_to_smallest", "Each rectangular block is trimmed from the right until it is as narrow as the narrowest block.", gi_shrinkw, tf_shrinkw)


# ---------- 10 shrink each block's height to the shortest ----------
def gi_shrinkh(rng):
    h, w = size_mixed(rng, 8, 16, 21, 30)
    res = _col_bands(rng, h, w, rng.randint(3, 4))
    return None if res is None else res[0]
def tf_shrinkh(g):
    h, w = dims(g)
    bands = []; c = 0
    while c < w:
        if any(g[r][c] for r in range(h)):
            c0 = c
            while c < w and any(g[r][c] for r in range(h)): c += 1
            c1 = c - 1
            col = max(v for cc in range(c0, c1 + 1) for v in (g[r][cc] for r in range(h)))
            height = sum(1 for r in range(h) if g[r][c0] == col)
            bands.append((c0, c1, col, height))
        else:
            c += 1
    if len(bands) < 2: return None
    tgt = min(b[3] for b in bands)
    out = blank(h, w)
    for c0, c1, col, height in bands:
        for cc in range(c0, c1 + 1):
            for r in range(tgt): out[r][cc] = col
    return out
rule("shrink_object_bbox_height_to_smallest", "Each rectangular block is trimmed from the bottom until it is as short as the shortest block.", gi_shrinkh, tf_shrinkh)


# ---------- 11 grow each object's cell count (padding rightward) to match the largest object ----------
def _scene(rng, k_lo, k_hi, n_lo, n_hi, lo, hi, margin=1):
    h, w = size_mixed(rng, lo, hi, 21, 30)
    k = rng.randint(k_lo, k_hi)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    cols = [rng.choice(COLOURS) for _ in range(k)]
    if place_shapes(rng, (g := blank(h, w)), shapes, cols, margin=margin) is None:
        return None
    return g
def gi_growcount(rng):
    g = _scene(rng, 3, 5, 3, 9, 8, 18, margin=2)
    if g is None: return None
    sizes = {len(o) for o in objects(g, 0)}
    return g if len(sizes) > 1 else None
def tf_growcount(g):
    h, w = dims(g)
    obs = objects(g, 0)
    tgt = max(len(o) for o in obs)
    out = copy(g)
    for o in obs:
        col = g[o[0][0]][o[0][1]]
        need = tgt - len(o)
        if need <= 0: continue
        r0, c0, r1, c1 = bbox(o)
        c = c1 + 1
        row = r0
        while need > 0 and row <= r1:
            if c < w and out[row][c] == 0:
                out[row][c] = col; need -= 1; c += 1
            else:
                row += 1; c = c1 + 1
    return out
rule("equalise_object_cellcount_grow_right", "Each object gains cells padded to the right of its bounding box until it has as many cells as the largest object.", gi_growcount, tf_growcount)


# ---------- 12 shrink each object's cell count to match the smallest object, in reading order ----------
def gi_shrinkcount(rng):
    g = _scene(rng, 3, 5, 3, 9, 8, 18, margin=1)
    if g is None: return None
    sizes = {len(o) for o in objects(g, 0)}
    return g if len(sizes) > 1 else None
def tf_shrinkcount(g):
    obs = objects(g, 0)
    tgt = min(len(o) for o in obs)
    out = copy(g)
    for o in obs:
        if len(o) <= tgt: continue
        drop = len(o) - tgt
        for r, c in reading(o)[::-1][:drop]:
            out[r][c] = 0
    return out
rule("equalise_object_cellcount_shrink_reading_order", "Each object loses its last cells (in reading order) until it has as few cells as the smallest object.", gi_shrinkcount, tf_shrinkcount)


# ---------- 13 equalise colour counts to the rarest colour ----------
def gi_colourrare(rng):
    h, w = size_mixed(rng, 8, 18, 21, 30, p_big=0.45)
    g = blank(h, w)
    cols = colours(rng, rng.randint(2, 4))
    free = [(r, c) for r in range(h) for c in range(w)]
    rng.shuffle(free)
    counts_ = {}
    i = 0
    for col in cols:
        n = rng.randint(1, max(2, (h * w) // (3 * len(cols))))
        for _ in range(n):
            if i >= len(free): break
            r, c = free[i]; i += 1; g[r][c] = col
        counts_[col] = n
    if len(set(counts_.values())) < 2: return None
    return g
def tf_colourrare(g):
    cnt = counts(g)
    nz = {c: n for c, n in cnt.items() if c != 0}
    if len(nz) < 2: return None
    m = min(nz.values())
    out = copy(g)
    for col, n in nz.items():
        if n <= m: continue
        pts = reading(cells(g, lambda v: v == col))
        for r, c in pts[m:]:
            out[r][c] = 0
    return out
rule("equalise_colour_counts_to_rarest", "Every colour loses its extra cells, in reading order, until it appears exactly as often as the rarest colour.", gi_colourrare, tf_colourrare)


# ---------- 14 two colours only: the common one is trimmed to match the rarer ----------
def gi_colourpair(rng):
    h, w = size_mixed(rng, 8, 16, 21, 30)
    g = blank(h, w)
    a, b = colours(rng, 2)
    free = [(r, c) for r in range(h) for c in range(w)]
    rng.shuffle(free)
    na = rng.randint(2, (h * w) // 3)
    nb = rng.randint(2, (h * w) // 3)
    if na == nb: return None
    i = 0
    for _ in range(na):
        r, c = free[i]; i += 1; g[r][c] = a
    for _ in range(nb):
        r, c = free[i]; i += 1; g[r][c] = b
    return g
def tf_colourpair(g):
    cnt = counts(g)
    nz = {c: n for c, n in cnt.items() if c != 0}
    if len(nz) != 2: return None
    m = min(nz.values())
    out = copy(g)
    for col, n in nz.items():
        if n <= m: continue
        pts = reading(cells(g, lambda v: v == col))
        for r, c in pts[m:]:
            out[r][c] = 0
    return out
rule("equalise_two_colour_counts_pairwise", "The more common of two colours loses its extra cells, in reading order, until both colours appear equally often.", gi_colourpair, tf_colourpair)


# ---------- 15 balance two column stacks by moving cells until equal (shared colour) ----------
def gi_twostacks(rng):
    h, w = size_mixed(rng, 8, 16, 21, 30)
    col = rng.choice(COLOURS)
    c1, c2 = sorted(rng.sample(range(w), 2))
    h1, h2 = rng.randint(1, h), rng.randint(1, h)
    if h1 == h2: return None
    g = blank(h, w)
    for r in range(h - h1, h): g[r][c1] = col
    for r in range(h - h2, h): g[r][c2] = col
    return g
def tf_twostacks(g):
    h, w = dims(g); col = max(v for row in g for v in row)
    if col == 0: return None
    cols_ = [c for c in range(w) if g[h - 1][c] == col]
    if len(cols_) != 2: return None
    c1, c2 = cols_
    h1 = sum(1 for r in range(h) if g[r][c1] == col)
    h2 = sum(1 for r in range(h) if g[r][c2] == col)
    total = h1 + h2
    lo, hi = total // 2, total - total // 2
    a, b = (hi, lo) if h1 >= h2 else (lo, hi)
    out = blank(h, w)
    for r in range(h - a, h): out[r][c1] = col
    for r in range(h - b, h): out[r][c2] = col
    return out
rule("balance_two_column_stacks", "Cells are moved between the two column stacks until their heights are as equal as possible, the taller stack keeping any odd remainder.", gi_twostacks, tf_twostacks)


# ---------- 16 balance two row stacks (horizontal analogue) ----------
def gi_tworows(rng):
    h, w = size_mixed(rng, 8, 16, 21, 30)
    col = rng.choice(COLOURS)
    r1, r2 = sorted(rng.sample(range(h), 2))
    w1, w2 = rng.randint(1, w), rng.randint(1, w)
    if w1 == w2: return None
    g = blank(h, w)
    for c in range(w1): g[r1][c] = col
    for c in range(w2): g[r2][c] = col
    return g
def tf_tworows(g):
    h, w = dims(g); col = max(v for row in g for v in row)
    if col == 0: return None
    rows_ = [r for r in range(h) if g[r][0] == col]
    if len(rows_) != 2: return None
    r1, r2 = rows_
    w1 = sum(1 for c in range(w) if g[r1][c] == col)
    w2 = sum(1 for c in range(w) if g[r2][c] == col)
    total = w1 + w2
    lo, hi = total // 2, total - total // 2
    a, b = (hi, lo) if w1 >= w2 else (lo, hi)
    out = blank(h, w)
    for c in range(a): out[r1][c] = col
    for c in range(b): out[r2][c] = col
    return out
rule("balance_two_row_stacks", "Cells are moved between the two row stacks until their lengths are as equal as possible, the longer stack keeping any odd remainder.", gi_tworows, tf_tworows)


# ---------- 17 seesaw: remove from the heavier side of a pivot ----------
def gi_seesaw(rng):
    h, w = size_mixed(rng, 10, 20, 21, 30, p_big=0.45)
    r = rng.randrange(h)
    piv = rng.randrange(2, w - 2)
    key = rng.choice(COLOURS)
    dot = rng.choice([c for c in COLOURS if c != key])
    g = blank(h, w); g[r][piv] = key
    left = rng.sample(range(0, piv), rng.randint(1, piv))
    right = rng.sample(range(piv + 1, w), rng.randint(1, w - piv - 1))
    if len(left) == len(right): return None
    for c in left: g[r][c] = dot
    for c in right: g[r][c] = dot
    return g
def tf_seesaw(g):
    h, w = dims(g)
    row = next(r for r in range(h) if any(v for v in g[r]))
    key = next(v for v in g[row] if v and g[row].count(v) == 1 and v != 0)
    piv = g[row].index(key)
    dot = next((v for v in g[row] if v not in (0, key)), None)
    if dot is None: return None
    left = [c for c in range(piv) if g[row][c] == dot]
    right = [c for c in range(piv + 1, w) if g[row][c] == dot]
    if len(left) == len(right): return None
    out = copy(g)
    if len(left) > len(right):
        extra = len(left) - len(right)
        for c in sorted(left)[:extra]: out[row][c] = 0
    else:
        extra = len(right) - len(left)
        for c in sorted(right, reverse=True)[:extra]: out[row][c] = 0
    return out
rule("seesaw_remove_from_heavy_side", "Dots are removed, farthest from the pivot first, from whichever side of the pivot marker has more until both sides balance.", gi_seesaw, tf_seesaw)


# ---------- 18 fill containers to the fullest level ----------
def _frames(rng, h, w, n_lo=2, n_hi=3):
    g = blank(h, w); wall = rng.choice(COLOURS); fillc = rng.choice([c for c in COLOURS if c != wall])
    frames_ = []
    for _ in range(40):
        r0, c0 = rng.randint(0, h - 4), rng.randint(0, w - 4)
        r1, c1 = rng.randint(r0 + 3, min(h - 1, r0 + 7)), rng.randint(c0 + 3, min(w - 1, c0 + 7))
        if all(g[r][c] == 0 for r in range(max(0, r0 - 1), min(h, r1 + 2)) for c in range(max(0, c0 - 1), min(w, c1 + 2))):
            rect(g, r0, c0, r1, c1, wall, fill=False)
            frames_.append((r0, c0, r1, c1))
        if len(frames_) >= rng.randint(n_lo, n_hi): break
    return (g, wall, fillc, frames_) if len(frames_) >= 2 else None
def gi_fillfull(rng):
    h, w = size_mixed(rng, 12, 20, 21, 30)
    res = _frames(rng, h, w)
    if res is None: return None
    g, wall, fillc, frames_ = res
    levels = []
    for r0, c0, r1, c1 in frames_:
        ih = r1 - r0 - 1
        lvl = rng.randint(0, ih)
        for r in range(r1 - lvl, r1): rect(g, r, c0 + 1, r, c1 - 1, fillc)
        levels.append(lvl)
    return g if len(set(levels)) > 1 else None
def tf_fillfull(g):
    h, w = dims(g)
    wall = None
    cnt = counts(g)
    nz = [c for c in cnt if c != 0]
    if len(nz) != 2: return None
    wall, fillc = (nz[0], nz[1]) if cnt[nz[0]] >= cnt[nz[1]] else (nz[1], nz[0])
    comps = components(g, lambda v: v == wall, conn8=False)
    frames_ = []
    for o in comps:
        r0, c0, r1, c1 = bbox(o)
        if len(o) == 2 * (r1 - r0 + c1 - c0) and r1 - r0 >= 3 and c1 - c0 >= 3:
            frames_.append((r0, c0, r1, c1))
    if len(frames_) < 2: return None
    out = copy(g)
    lvls = []
    for r0, c0, r1, c1 in frames_:
        lvl = sum(1 for r in range(r0 + 1, r1) if out[r][c0 + 1] == fillc)
        lvls.append(lvl)
    tgt = max(lvls)
    for (r0, c0, r1, c1), lvl in zip(frames_, lvls):
        for r in range(r1 - tgt, r1): rect(out, r, c0 + 1, r, c1 - 1, fillc)
    return out
rule("fill_frames_to_fullest_level", "Every hollow frame is filled from the bottom until its fill reaches the level of the fullest frame.", gi_fillfull, tf_fillfull)


# ---------- 19 drain containers to the emptiest level ----------
def gi_drainempty(rng):
    return gi_fillfull(rng)
def tf_drainempty(g):
    h, w = dims(g); cnt = counts(g)
    nz = [c for c in cnt if c != 0]
    if len(nz) != 2: return None
    wall, fillc = (nz[0], nz[1]) if cnt[nz[0]] >= cnt[nz[1]] else (nz[1], nz[0])
    comps = components(g, lambda v: v == wall, conn8=False)
    frames_ = []
    for o in comps:
        r0, c0, r1, c1 = bbox(o)
        if len(o) == 2 * (r1 - r0 + c1 - c0) and r1 - r0 >= 3 and c1 - c0 >= 3:
            frames_.append((r0, c0, r1, c1))
    if len(frames_) < 2: return None
    out = copy(g)
    lvls = []
    for r0, c0, r1, c1 in frames_:
        lvl = sum(1 for r in range(r0 + 1, r1) if out[r][c0 + 1] == fillc)
        lvls.append(lvl)
    tgt = min(lvls)
    if len(set(lvls)) < 2: return None
    for (r0, c0, r1, c1), lvl in zip(frames_, lvls):
        for r in range(r0 + 1, r1 - tgt): rect(out, r, c0 + 1, r, c1 - 1, 0)
    return out
rule("trim_frames_to_emptiest_level", "Every hollow frame is drained from the top of its fill until its level matches the emptiest frame.", gi_drainempty, tf_drainempty)


# ---------- 20 equalise dot counts inside containers ----------
def gi_dotsinframe(rng):
    h, w = size_mixed(rng, 12, 20, 21, 30)
    res = _frames(rng, h, w, 2, 3)
    if res is None: return None
    g, wall, dot, frames_ = res
    counts_ = []
    for r0, c0, r1, c1 in frames_:
        inside = [(r, c) for r in range(r0 + 1, r1) for c in range(c0 + 1, c1)]
        n = rng.randint(1, min(len(inside), (r1 - r0 - 1) * (c1 - c0 - 1)))
        for r, c in rng.sample(inside, n): g[r][c] = dot
        counts_.append(n)
    return g if len(set(counts_)) > 1 else None
def tf_dotsinframe(g):
    cnt = counts(g)
    nz = [c for c in cnt if c != 0]
    if len(nz) != 2: return None
    wall, dot = (nz[0], nz[1]) if cnt[nz[0]] >= cnt[nz[1]] else (nz[1], nz[0])
    comps = components(g, lambda v: v == wall, conn8=False)
    frames_ = []
    for o in comps:
        r0, c0, r1, c1 = bbox(o)
        if len(o) == 2 * (r1 - r0 + c1 - c0) and r1 - r0 >= 3 and c1 - c0 >= 3:
            frames_.append((r0, c0, r1, c1))
    if len(frames_) < 2: return None
    out = copy(g)
    conts = []
    for r0, c0, r1, c1 in frames_:
        dots = reading([(r, c) for r in range(r0 + 1, r1) for c in range(c0 + 1, c1) if out[r][c] == dot])
        conts.append(dots)
    m = min(len(d) for d in conts)
    for dots in conts:
        for r, c in dots[m:]:
            out[r][c] = 0
    return out
rule("equalise_dots_inside_frames", "Each frame's interior dots lose their extras, in reading order, until every frame holds as few dots as the sparsest one.", gi_dotsinframe, tf_dotsinframe)


# ---------- 21 equalise row cell-counts by growing shorter rows rightward ----------
def gi_rowgrow(rng):
    h, w = size_mixed(rng, 8, 16, 21, 30)
    g = blank(h, w)
    ns = []
    for r in range(h):
        col = rng.choice(COLOURS)
        n = rng.randint(1, w)
        for c in range(n): g[r][c] = col
        ns.append(n)
    return g if len(set(ns)) > 1 else None
def tf_rowgrow(g):
    h, w = dims(g)
    rows = []
    for r in range(h):
        n = sum(1 for v in g[r] if v)
        rows.append(n)
    tgt = max(rows)
    out = copy(g)
    for r in range(h):
        n = rows[r]
        if n == 0 or n >= tgt: continue
        col = next(v for v in g[r] if v)
        for c in range(n, tgt): out[r][c] = col
    return out
rule("equalise_row_cellcounts_grow_right", "Every row with coloured cells is padded on the right until it has as many filled cells as the fullest row.", gi_rowgrow, tf_rowgrow)


# ---------- 22 equalise row cell-counts by trimming the right end ----------
def gi_rowtrim(rng):
    h, w = size_mixed(rng, 8, 16, 21, 30, p_big=0.45)
    g = blank(h, w)
    ns = []
    for r in range(h):
        col = rng.choice(COLOURS)
        n = rng.randint(1, w)
        for c in range(n): g[r][c] = col
        ns.append(n)
    return g if len(set(ns)) > 1 else None
def tf_rowtrim(g):
    h, w = dims(g)
    rows = [sum(1 for v in g[r] if v) for r in range(h)]
    nz = [n for n in rows if n > 0]
    if not nz: return None
    tgt = min(nz)
    out = copy(g)
    for r in range(h):
        n = rows[r]
        if n <= tgt: continue
        for c in range(tgt, n): out[r][c] = 0
    return out
rule("equalise_row_cellcounts_trim_right", "Every row with coloured cells is trimmed from the right until it has as few filled cells as the sparsest row.", gi_rowtrim, tf_rowtrim)


# ---------- 23 equalise column cell-counts by growing downward ----------
def gi_colgrow(rng):
    h, w = size_mixed(rng, 8, 16, 21, 30)
    g = blank(h, w)
    ns = []
    for c in range(w):
        col = rng.choice(COLOURS)
        n = rng.randint(1, h)
        for r in range(n): g[r][c] = col
        ns.append(n)
    return g if len(set(ns)) > 1 else None
def tf_colgrow(g):
    h, w = dims(g)
    colsn = [sum(1 for r in range(h) if g[r][c]) for c in range(w)]
    tgt = max(colsn)
    out = copy(g)
    for c in range(w):
        n = colsn[c]
        if n == 0 or n >= tgt: continue
        col = next(g[r][c] for r in range(h) if g[r][c])
        for r in range(n, tgt): out[r][c] = col
    return out
rule("equalise_column_cellcounts_grow_down", "Every column with coloured cells is padded downward until it has as many filled cells as the fullest column.", gi_colgrow, tf_colgrow)


# ---------- 24 equalise column cell-counts by trimming from the bottom ----------
def gi_coltrim(rng):
    h, w = size_mixed(rng, 8, 16, 21, 30)
    g = blank(h, w)
    ns = []
    for c in range(w):
        col = rng.choice(COLOURS)
        n = rng.randint(1, h)
        for r in range(n): g[r][c] = col
        ns.append(n)
    return g if len(set(ns)) > 1 else None
def tf_coltrim(g):
    h, w = dims(g)
    colsn = [sum(1 for r in range(h) if g[r][c]) for c in range(w)]
    nz = [n for n in colsn if n > 0]
    if not nz: return None
    tgt = min(nz)
    out = copy(g)
    for c in range(w):
        n = colsn[c]
        if n <= tgt: continue
        for r in range(tgt, n): out[r][c] = 0
    return out
rule("equalise_column_cellcounts_trim_down", "Every column with coloured cells is trimmed from the bottom until it has as few filled cells as the sparsest column.", gi_coltrim, tf_coltrim)


# ---------- 25 balance left and right halves of scattered dots ----------
def gi_halflr(rng):
    h, w = size_mixed(rng, 10, 20, 21, 30)
    if w < 4: return None
    mid = w // 2
    col = rng.choice(COLOURS)
    g = blank(h, w)
    left_free = [(r, c) for r in range(h) for c in range(mid)]
    right_free = [(r, c) for r in range(h) for c in range(mid, w)]
    nl = rng.randint(1, len(left_free) // 2)
    nr = rng.randint(1, len(right_free) // 2)
    if nl == nr: return None
    for r, c in rng.sample(left_free, nl): g[r][c] = col
    for r, c in rng.sample(right_free, nr): g[r][c] = col
    return g
def tf_halflr(g):
    h, w = dims(g); col = max(v for row in g for v in row)
    if col == 0: return None
    mid = w // 2
    left = reading(cells(g, lambda v: v == col) and [(r, c) for r, c in cells(g, lambda v: v == col) if c < mid])
    right = reading([(r, c) for r, c in cells(g, lambda v: v == col) if c >= mid])
    if len(left) == len(right): return None
    out = copy(g)
    if len(left) > len(right):
        extra = len(left) - len(right)
        for r, c in sorted(left, key=lambda rc: -rc[1])[:extra]: out[r][c] = 0
    else:
        extra = len(right) - len(left)
        for r, c in sorted(right, key=lambda rc: rc[1])[:extra]: out[r][c] = 0
    return out
rule("balance_left_right_halves", "Dots are removed, nearest the centre line first, from whichever half of the grid has more until the two halves balance.", gi_halflr, tf_halflr)


# ---------- 26 balance top and bottom halves of scattered dots ----------
def gi_halftb(rng):
    h, w = size_mixed(rng, 10, 20, 21, 30)
    if h < 4: return None
    mid = h // 2
    col = rng.choice(COLOURS)
    g = blank(h, w)
    top_free = [(r, c) for r in range(mid) for c in range(w)]
    bot_free = [(r, c) for r in range(mid, h) for c in range(w)]
    nt = rng.randint(1, len(top_free) // 2)
    nb = rng.randint(1, len(bot_free) // 2)
    if nt == nb: return None
    for r, c in rng.sample(top_free, nt): g[r][c] = col
    for r, c in rng.sample(bot_free, nb): g[r][c] = col
    return g
def tf_halftb(g):
    h, w = dims(g); col = max(v for row in g for v in row)
    if col == 0: return None
    mid = h // 2
    pts = cells(g, lambda v: v == col)
    top = [(r, c) for r, c in pts if r < mid]
    bot = [(r, c) for r, c in pts if r >= mid]
    if len(top) == len(bot): return None
    out = copy(g)
    if len(top) > len(bot):
        extra = len(top) - len(bot)
        for r, c in sorted(top, key=lambda rc: -rc[0])[:extra]: out[r][c] = 0
    else:
        extra = len(bot) - len(top)
        for r, c in sorted(bot, key=lambda rc: rc[0])[:extra]: out[r][c] = 0
    return out
rule("balance_top_bottom_halves", "Dots are removed, nearest the centre line first, from whichever half of the grid has more until the two halves balance.", gi_halftb, tf_halftb)


# ---------- 27 equalise the gaps between objects placed in a single row ----------
def gi_rowgaps(rng):
    h, w = size_mixed(rng, 10, 20, 21, 30)
    k = rng.randint(3, 4)
    widths = [rng.randint(1, 3) for _ in range(k)]
    row = rng.randrange(h)
    need = sum(widths) + (k - 1)
    if need >= w: return None
    positions = [0]
    for i in range(1, k):
        room = w - positions[-1] - widths[i - 1] - sum(widths[i:]) - (k - i - 1)
        if room < 1: return None
        gap = rng.randint(1, room)
        positions.append(positions[-1] + widths[i - 1] + gap)
    gaps = [positions[i + 1] - (positions[i] + widths[i]) for i in range(k - 1)]
    if len(set(gaps)) < 2: return None
    g = blank(h, w)
    for p, wdt in zip(positions, widths):
        col = rng.choice(COLOURS)
        for c in range(p, p + wdt): g[row][c] = col
    return g
def tf_rowgaps(g):
    h, w = dims(g)
    row = next((r for r in range(h) if any(g[r])), None)
    if row is None: return None
    objs = []
    c = 0
    while c < w:
        if g[row][c]:
            c0 = c; col = g[row][c]
            while c < w and g[row][c] == col: c += 1
            objs.append((c0, c - 1, col))
        else:
            c += 1
    if len(objs) < 3: return None
    widths = [c1 - c0 + 1 for c0, c1, _ in objs]
    gaps = [objs[i + 1][0] - objs[i][1] - 1 for i in range(len(objs) - 1)]
    total_gap = sum(gaps); k = len(objs)
    base, rem = divmod(total_gap, k - 1)
    out = blank(h, w)
    pos = objs[0][0]
    for i, (c0, c1, col) in enumerate(objs):
        for c in range(pos, pos + widths[i]): out[row][c] = col
        if i < k - 1:
            pos += widths[i] + base + (1 if i < rem else 0)
    return out
rule("equalise_gaps_between_row_objects", "The objects in the row are respaced so every gap between neighbours is the same width, the leftmost object staying put.", gi_rowgaps, tf_rowgaps)


# ---------- 28 respace dots on a line evenly ----------
def gi_linedots(rng):
    h, w = size_mixed(rng, 10, 20, 21, 30, p_big=0.45)
    k = rng.randint(4, 6)
    if w < k + 2: return None
    row = rng.randrange(h)
    col = rng.choice(COLOURS)
    pts = sorted(rng.sample(range(w), k))
    gaps = [pts[i + 1] - pts[i] for i in range(k - 1)]
    if len(set(gaps)) < 2: return None
    g = blank(h, w)
    for c in pts: g[row][c] = col
    return g
def tf_linedots(g):
    h, w = dims(g); col = max(v for row in g for v in row)
    if col == 0: return None
    row = next(r for r in range(h) if col in g[r])
    pts = [c for c in range(w) if g[row][c] == col]
    if len(pts) < 4: return None
    span = pts[-1] - pts[0]; k = len(pts)
    base, rem = divmod(span, k - 1)
    out = blank(h, w)
    pos = pts[0]
    out[row][pos] = col
    for i in range(k - 1):
        pos += base + (1 if i < rem else 0)
        out[row][pos] = col
    return out
rule("equalise_spacing_of_line_dots", "The dots on the line are respaced evenly between the first and last dot, which stay fixed.", gi_linedots, tf_linedots)


# ---------- 29 redistribute one colour's total count evenly across its bars ----------
def gi_redistribar(rng):
    h, w = size_mixed(rng, 10, 20, 21, 30)
    col = rng.choice(COLOURS)
    k = rng.randint(3, 5)
    if w < k * 2: return None
    cs = sorted(rng.sample(range(w), k))
    heights = [rng.randint(1, h) for _ in range(k)]
    if len(set(heights)) < 2: return None
    g = blank(h, w)
    for c, hh in zip(cs, heights):
        for r in range(h - hh, h): g[r][c] = col
    return g
def tf_redistribar(g):
    h, w = dims(g); col = max(v for row in g for v in row)
    if col == 0: return None
    cs = [c for c in range(w) if g[h - 1][c] == col]
    if len(cs) < 3: return None
    heights = [sum(1 for r in range(h) if g[r][c] == col) for c in cs]
    total = sum(heights); k = len(cs)
    base, rem = divmod(total, k)
    out = blank(h, w)
    for i, c in enumerate(cs):
        hh = base + (1 if i < rem else 0)
        for r in range(h - hh, h): out[r][c] = col
    return out
rule("redistribute_colour_evenly_across_bars", "The colour's total cell count is shared out evenly across its bars, left to right, any remainder going to the leftmost bars.", gi_redistribar, tf_redistribar)


# ---------- 30 move dots between two containers until their counts are equal ----------
def gi_twocontainers(rng):
    h, w = size_mixed(rng, 14, 22, 21, 30)
    wall = rng.choice(COLOURS); dot = rng.choice([c for c in COLOURS if c != wall])
    g = blank(h, w)
    r0a, c0a = 1, 1
    r0b, c0b = 1, w // 2 + 1
    sz = min(h - 2, w // 2 - 2)
    if sz < 3: return None
    rect(g, r0a, c0a, r0a + sz - 1, c0a + sz - 1, wall, fill=False)
    rect(g, r0b, c0b, r0b + sz - 1, c0b + sz - 1, wall, fill=False)
    inside_a = [(r, c) for r in range(r0a + 1, r0a + sz - 1) for c in range(c0a + 1, c0a + sz - 1)]
    inside_b = [(r, c) for r in range(r0b + 1, r0b + sz - 1) for c in range(c0b + 1, c0b + sz - 1)]
    na = rng.randint(0, len(inside_a))
    nb = rng.randint(0, len(inside_b))
    if na == nb: return None
    for r, c in rng.sample(inside_a, na): g[r][c] = dot
    for r, c in rng.sample(inside_b, nb): g[r][c] = dot
    return g
def tf_twocontainers(g):
    cnt = counts(g)
    nz = [c for c in cnt if c != 0]
    if len(nz) != 2: return None
    wall, dot = (nz[0], nz[1]) if cnt[nz[0]] >= cnt[nz[1]] else (nz[1], nz[0])
    comps = components(g, lambda v: v == wall, conn8=False)
    boxes = []
    for o in comps:
        r0, c0, r1, c1 = bbox(o)
        if len(o) == 2 * (r1 - r0 + c1 - c0):
            boxes.append((r0, c0, r1, c1))
    if len(boxes) != 2: return None
    boxes.sort(key=lambda b: (b[0], b[1]))
    out = copy(g)
    insides = []
    for r0, c0, r1, c1 in boxes:
        inside = [(r, c) for r in range(r0 + 1, r1) for c in range(c0 + 1, c1)]
        insides.append(inside)
    filled = [[(r, c) for r, c in ins if g[r][c] == dot] for ins in insides]
    na, nb = len(filled[0]), len(filled[1])
    if na == nb: return None
    total = na + nb
    lo, hi = total // 2, total - total // 2
    ta, tb = (hi, lo) if na >= nb else (lo, hi)
    if na > ta:
        for r, c in reading(filled[0])[ta:]: out[r][c] = 0
    elif na < ta:
        empties = reading([p for p in insides[0] if g[p[0]][p[1]] != dot])
        for r, c in empties[:ta - na]: out[r][c] = dot
    if nb > tb:
        for r, c in reading(filled[1])[tb:]: out[r][c] = 0
    elif nb < tb:
        empties = reading([p for p in insides[1] if g[p[0]][p[1]] != dot])
        for r, c in empties[:tb - nb]: out[r][c] = dot
    return out
rule("redistribute_dots_between_two_containers", "Dots move from the fuller container to the emptier one, filling or clearing in reading order, until both hold as equal a count as possible.", gi_twocontainers, tf_twocontainers)


# ---------- 31 equalise the four arm lengths of a plus shape ----------
def gi_plusarms(rng):
    h, w = size_mixed(rng, 12, 22, 21, 30)
    col = rng.choice(COLOURS)
    cy, cx = rng.randint(6, h - 7), rng.randint(6, w - 7)
    up, down, left_, right_ = (rng.randint(1, 5) for _ in range(4))
    if len({up, down, left_, right_}) < 2: return None
    g = blank(h, w); g[cy][cx] = col
    for d in range(1, up + 1): g[cy - d][cx] = col
    for d in range(1, down + 1): g[cy + d][cx] = col
    for d in range(1, left_ + 1): g[cy][cx - d] = col
    for d in range(1, right_ + 1): g[cy][cx + d] = col
    return g
def tf_plusarms(g):
    h, w = dims(g); col = max(v for row in g for v in row)
    if col == 0: return None
    pts = cells(g, lambda v: v == col)
    rows_ = {r for r, _ in pts}; cols_ = {c for _, c in pts}
    if len(rows_) < 2 or len(cols_) < 2: return None
    cy = [r for r in rows_ if sum(1 for rr, cc in pts if rr == r) == max(sum(1 for rr, cc in pts if rr == rx) for rx in rows_)][0]
    cx = [c for c in cols_ if (cy, c) in pts and sum(1 for rr, cc in pts if cc == c) >= 1]
    # the centre is the unique cell present in both the longest row-run and column-run
    cx_candidates = [c for r, c in pts if r == cy]
    cx = sorted(cx_candidates)[len(cx_candidates) // 2] if len(cx_candidates) % 2 else cx_candidates[0]
    # fall back: centre is the cell whose row and column both have cells on both sides
    centre = None
    for r, c in pts:
        left_ = sum(1 for rr, cc in pts if rr == r and cc < c)
        right_ = sum(1 for rr, cc in pts if rr == r and cc > c)
        up = sum(1 for rr, cc in pts if cc == c and rr < r)
        down = sum(1 for rr, cc in pts if cc == c and rr > r)
        if left_ and right_ and up and down:
            centre = (r, c); break
    if centre is None: return None
    cy, cx = centre
    up = sum(1 for r, c in pts if c == cx and r < cy)
    down = sum(1 for r, c in pts if c == cx and r > cy)
    left_ = sum(1 for r, c in pts if r == cy and c < cx)
    right_ = sum(1 for r, c in pts if r == cy and c > cx)
    m = min(up, down, left_, right_)
    if m == max(up, down, left_, right_): return None
    out = copy(g)
    for d in range(m + 1, up + 1): out[cy - d][cx] = 0
    for d in range(m + 1, down + 1): out[cy + d][cx] = 0
    for d in range(m + 1, left_ + 1): out[cy][cx - d] = 0
    for d in range(m + 1, right_ + 1): out[cy][cx + d] = 0
    return out
rule("equalise_plus_arm_lengths", "Every arm of the plus shape is trimmed from its tip until all four arms are as short as the shortest arm.", gi_plusarms, tf_plusarms)


# ---------- 32 equalise marker counts in the four quadrants ----------
def gi_quadmarkers(rng):
    h, w = size_mixed(rng, 12, 22, 21, 30)
    if h < 6 or w < 6: return None
    mr, mc = h // 2, w // 2
    col = rng.choice(COLOURS)
    g = blank(h, w)
    quads = [(0, mr, 0, mc), (0, mr, mc, w), (mr, h, 0, mc), (mr, h, mc, w)]
    ns = []
    for r0, r1, c0, c1 in quads:
        free = [(r, c) for r in range(r0, r1) for c in range(c0, c1)]
        n = rng.randint(1, max(1, len(free) // 3))
        for r, c in rng.sample(free, min(n, len(free))): g[r][c] = col
        ns.append(min(n, len(free)))
    return g if len(set(ns)) > 1 else None
def tf_quadmarkers(g):
    h, w = dims(g); col = max(v for row in g for v in row)
    if col == 0: return None
    mr, mc = h // 2, w // 2
    quads = [(0, mr, 0, mc), (0, mr, mc, w), (mr, h, 0, mc), (mr, h, mc, w)]
    groups = []
    for r0, r1, c0, c1 in quads:
        pts = reading([(r, c) for r in range(r0, r1) for c in range(c0, c1) if g[r][c] == col])
        groups.append(pts)
    m = min(len(p) for p in groups)
    out = copy(g)
    for pts in groups:
        for r, c in pts[m:]: out[r][c] = 0
    return out
rule("equalise_quadrant_marker_counts", "Each quadrant's markers lose their extras, in reading order, until every quadrant holds as few as the sparsest quadrant.", gi_quadmarkers, tf_quadmarkers)


# ---------- 33 bar height set to match a legend digit (digit = colour value) ----------
def gi_legendbar(rng):
    h, w = size_mixed(rng, 10, 18, 21, 30)
    if h < 4: return None
    d = rng.randint(1, min(9, h - 1))
    g = blank(h, w)
    c = rng.randrange(w)
    g[0][c] = d
    cur = rng.randint(1, h - 1)
    if cur == d: return None
    for r in range(h - cur, h): g[r][c] = d
    return g
def tf_legendbar(g):
    h, w = dims(g)
    pos = next(((r, c) for r in [0] for c in range(w) if g[0][c] != 0), None)
    if pos is None: return None
    _, c = pos; d = g[0][c]
    if not (1 <= d <= 9): return None
    cur = sum(1 for r in range(1, h) if g[r][c] == d)
    out = copy(g)
    for r in range(1, h): out[r][c] = 0
    for r in range(h - d, h): out[r][c] = d
    return out
rule("match_bar_height_to_legend_digit", "The bar below the legend cell grows or shrinks until its height equals the legend's digit.", gi_legendbar, tf_legendbar, digits=True)


# ---------- 34 row bar length set to match a leading digit cell ----------
def gi_digitrow(rng):
    h, w = size_mixed(rng, 10, 18, 21, 30)
    if w < 4: return None
    g = blank(h, w)
    ds = []
    for r in range(h):
        d = rng.randint(1, min(9, w - 1))
        g[r][0] = d
        cur = rng.randint(0, w - 1)
        for c in range(1, 1 + cur): g[r][c] = d
        ds.append((d, cur))
    if all(d == cur for d, cur in ds): return None
    return g
def tf_digitrow(g):
    h, w = dims(g)
    out = copy(g)
    changed = False
    for r in range(h):
        d = g[r][0]
        if not (1 <= d <= 9): return None
        for c in range(1, w): out[r][c] = 0
        for c in range(1, 1 + d):
            if c < w: out[r][c] = d
        if out[r] != g[r]: changed = True
    return out if changed else None
rule("match_column_height_to_digit_row", "Every row's bar grows or shrinks until its length equals the digit at the row's start.", gi_digitrow, tf_digitrow, digits=True)


# ---------- 35 two differently-coloured bars moved toward their average height ----------
def gi_meetavg(rng):
    h, w = size_mixed(rng, 10, 18, 21, 30)
    a, b = colours(rng, 2)
    c1, c2 = sorted(rng.sample(range(w), 2))
    h1, h2 = rng.randint(1, h), rng.randint(1, h)
    if abs(h1 - h2) < 2: return None
    g = blank(h, w)
    for r in range(h - h1, h): g[r][c1] = a
    for r in range(h - h2, h): g[r][c2] = b
    return g
def tf_meetavg(g):
    h, w = dims(g)
    cnt = counts(g); nz = [c for c in cnt if c != 0]
    if len(nz) != 2: return None
    c1 = next(c for c in range(w) if g[h - 1][c] == nz[0])
    c2 = next(c for c in range(w) if g[h - 1][c] == nz[1])
    a, b = nz
    h1 = sum(1 for r in range(h) if g[r][c1] == a)
    h2 = sum(1 for r in range(h) if g[r][c2] == b)
    move = abs(h1 - h2) // 2
    if move == 0: return None
    out = blank(h, w)
    if h1 > h2:
        nh1, nh2 = h1 - move, h2 + move
    else:
        nh1, nh2 = h1 + move, h2 - move
    for r in range(h - nh1, h): out[r][c1] = a
    for r in range(h - nh2, h): out[r][c2] = b
    return out
rule("equalise_two_coloured_bars_to_average", "The taller bar donates height to the shorter bar, each keeping its own colour, until they are as close to the average height as an even split allows.", gi_meetavg, tf_meetavg)


# ---------- 36 trim thick frame borders down to the thinnest frame's thickness ----------
def gi_bordertrim(rng):
    h, w = size_mixed(rng, 14, 24, 21, 30)
    col = rng.choice(COLOURS)
    g = blank(h, w)
    boxes = []
    for _ in range(40):
        t = rng.randint(1, 3)
        sz = rng.randint(2 * t + 3, 2 * t + 9)
        r0, c0 = rng.randint(0, h - sz), rng.randint(0, w - sz)
        if r0 < 0 or c0 < 0: continue
        region_ok = all(g[r][c] == 0 for r in range(max(0, r0 - 1), min(h, r0 + sz + 1)) for c in range(max(0, c0 - 1), min(w, c0 + sz + 1)))
        if region_ok:
            for layer in range(t):
                rect(g, r0 + layer, c0 + layer, r0 + sz - 1 - layer, c0 + sz - 1 - layer, col, fill=False)
            boxes.append(t)
        if len(boxes) >= 3: break
    return g if len(set(boxes)) > 1 and len(boxes) >= 2 else None
def tf_bordertrim(g):
    h, w = dims(g); col = max(v for row in g for v in row)
    if col == 0: return None
    comps = components(g, col, conn8=False)
    out = copy(g)
    thick = []
    boxes = []
    for o in comps:
        r0, c0, r1, c1 = bbox(o)
        t = 1
        while all(g[r0 + t][c0 + t] == col for _ in [0]) is False:
            break
        # measure thickness by scanning inward along the top-left corner
        tt = 0
        rr, cc = r0, c0
        while rr <= r1 and cc <= c1 and g[rr][cc] == col:
            tt += 1; rr += 1; cc += 1
        thick.append(tt); boxes.append((r0, c0, r1, c1))
    if len(boxes) < 2 or len(set(thick)) < 2: return None
    m = min(thick)
    for (r0, c0, r1, c1), t in zip(boxes, thick):
        for layer in range(m, t):
            rect(out, r0 + layer, c0 + layer, r1 - layer, c1 - layer, 0, fill=False)
    return out
rule("equalise_border_frame_thickness", "Every frame's border loses its outer layers until it is as thin as the thinnest frame's border.", gi_bordertrim, tf_bordertrim)


# ---------- 37 add a cell to the smaller object of each consecutive pair ----------
def gi_pairadd(rng):
    g = _scene(rng, 4, 6, 3, 9, 10, 20, margin=2)
    if g is None: return None
    obs = objects(g, 0)
    if len(obs) < 2: return None
    sizes = sorted(len(o) for o in obs)
    if sizes[0] == sizes[1] and len(set(sizes)) < 2: return None
    return g
def tf_pairadd(g):
    h, w = dims(g)
    obs = sorted(objects(g, 0), key=lambda o: bbox(o)[:2])
    if len(obs) < 2: return None
    out = copy(g)
    changed = False
    for i in range(0, len(obs) - 1, 2):
        a, b = obs[i], obs[i + 1]
        small = a if len(a) < len(b) else (b if len(b) < len(a) else None)
        if small is None: continue
        col = g[small[0][0]][small[0][1]]
        r0, c0, r1, c1 = bbox(small)
        placed = False
        for r in range(r0, r1 + 1):
            c = c1 + 1
            if c < w and out[r][c] == 0:
                out[r][c] = col; placed = True; break
        if placed: changed = True
    return out if changed else None
rule("add_cell_to_smaller_of_each_pair", "Objects are paired off in reading order and each pair's smaller object gains one cell beside its bounding box.", gi_pairadd, tf_pairadd)


# ---------- 38 seesaw: add cells to the lighter side instead of removing ----------
def gi_seesawadd(rng):
    h, w = size_mixed(rng, 14, 24, 21, 30)
    r = rng.randrange(h)
    piv = w // 2
    key = rng.choice(COLOURS)
    dot = rng.choice([c for c in COLOURS if c != key])
    g = blank(h, w); g[r][piv] = key
    maxside = piv - 2
    nl = rng.randint(1, max(1, maxside // 2))
    nr = rng.randint(1, max(1, maxside // 2))
    if nl == nr: return None
    left_cells = rng.sample(range(0, piv), nl)
    right_cells = rng.sample(range(piv + 1, w), nr)
    for c in left_cells: g[r][c] = dot
    for c in right_cells: g[r][c] = dot
    return g
def tf_seesawadd(g):
    h, w = dims(g)
    row = next((r for r in range(h) if any(g[r])), None)
    if row is None: return None
    key = None
    for c in range(w):
        v = g[row][c]
        if v and sum(1 for cc in range(w) if g[row][cc] == v) == 1:
            key = v; piv = c; break
    if key is None: return None
    dot = next((v for v in g[row] if v not in (0, key)), None)
    if dot is None: return None
    left = sorted(c for c in range(piv) if g[row][c] == dot)
    right = sorted(c for c in range(piv + 1, w) if g[row][c] == dot)
    if len(left) == len(right): return None
    out = copy(g)
    if len(left) < len(right):
        need = len(right) - len(left)
        free = [c for c in range(piv - 1, -1, -1) if g[row][c] == 0]
        for c in free[:need]: out[row][c] = dot
    else:
        need = len(left) - len(right)
        free = [c for c in range(piv + 1, w) if g[row][c] == 0]
        for c in free[:need]: out[row][c] = dot
    return out
rule("seesaw_add_to_light_side", "Dots are added, nearest the pivot first, to whichever side of the pivot marker has fewer until both sides balance.", gi_seesawadd, tf_seesawadd)


# ---------- 39 grow the shorter of two differently-coloured bars to match the taller ----------
def gi_growshorter(rng):
    h, w = size_mixed(rng, 10, 18, 21, 30)
    a, b = colours(rng, 2)
    c1, c2 = sorted(rng.sample(range(w), 2))
    h1, h2 = rng.randint(1, h), rng.randint(1, h)
    if h1 == h2: return None
    g = blank(h, w)
    for r in range(h - h1, h): g[r][c1] = a
    for r in range(h - h2, h): g[r][c2] = b
    return g
def tf_growshorter(g):
    h, w = dims(g)
    cnt = counts(g); nz = [c for c in cnt if c != 0]
    if len(nz) != 2: return None
    c1 = next(c for c in range(w) if g[h - 1][c] == nz[0])
    c2 = next(c for c in range(w) if g[h - 1][c] == nz[1])
    a, b = nz
    h1 = sum(1 for r in range(h) if g[r][c1] == a)
    h2 = sum(1 for r in range(h) if g[r][c2] == b)
    if h1 == h2: return None
    out = copy(g)
    tgt = max(h1, h2)
    if h1 < h2:
        for r in range(h - tgt, h): out[r][c1] = a
    else:
        for r in range(h - tgt, h): out[r][c2] = b
    return out
rule("grow_shorter_colour_bar_to_match", "The shorter of the two coloured bars grows upward, in its own colour, until it is as tall as the taller bar.", gi_growshorter, tf_growshorter)


# ---------- 40 equalise several bars to their median height ----------
def gi_median(rng):
    h, w = size_mixed(rng, 10, 20, 21, 30)
    col = rng.choice(COLOURS)
    k = rng.randint(3, 5)
    if w < k * 2: return None
    cs = sorted(rng.sample(range(w), k))
    heights = [rng.randint(1, h) for _ in range(k)]
    if len(set(heights)) < 3: return None
    g = blank(h, w)
    for c, hh in zip(cs, heights):
        for r in range(h - hh, h): g[r][c] = col
    return g
def tf_median(g):
    h, w = dims(g); col = max(v for row in g for v in row)
    if col == 0: return None
    cs = [c for c in range(w) if g[h - 1][c] == col]
    if len(cs) < 3: return None
    heights = [sum(1 for r in range(h) if g[r][c] == col) for c in cs]
    srt = sorted(heights)
    n = len(srt)
    med = srt[n // 2] if n % 2 else (srt[n // 2 - 1] + srt[n // 2]) // 2
    if med in (min(heights), max(heights)) and len(set(heights)) <= 2: return None
    out = blank(h, w)
    for c, hh in zip(cs, heights):
        for r in range(h - med, h): out[r][c] = col
    return out if out != g else None
rule("equalise_bar_heights_to_median", "Every bar grows or shrinks until it is exactly as tall as the group's median height.", gi_median, tf_median)
