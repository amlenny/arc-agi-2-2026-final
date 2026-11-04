# b051_legends.py -- 40 rules whose output is a legend/inventory of the scene: tables, swatch rows/
# columns, histograms, palettes, quadrant summaries. Reading order = top-left reading order (row-major,
# top-to-bottom then left-to-right) unless a rule states column-major. All bars/counts are capped at 9
# unless noted; fixed-width rows/columns are padded with background (0) on the side stated.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


# ---------- shared helpers ----------
def _hw(rng, lo=6, himid=20, large_p=0.35):
    if rng.random() < large_p:
        return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, himid), rng.randint(lo, himid)


def _scene(rng, k_lo, k_hi, n_lo, n_hi, lo=6, himid=18, margin=1, large_p=0.35):
    h, w = _hw(rng, lo, himid, large_p)
    g = blank(h, w)
    k = rng.randint(k_lo, min(k_hi, 9))
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    cols = colours(rng, k)
    if place_shapes(rng, g, shapes, cols, margin=margin) is None:
        return None
    return g


def _scene_multi(rng, k_lo, k_hi, n_lo, n_hi, pal_lo=2, pal_hi=4, lo=6, himid=18, margin=1, large_p=0.35):
    h, w = _hw(rng, lo, himid, large_p)
    g = blank(h, w)
    k = rng.randint(k_lo, k_hi)
    pal = colours(rng, rng.randint(pal_lo, min(pal_hi, 9)))
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    cols = [rng.choice(pal) for _ in range(k)]
    if place_shapes(rng, g, shapes, cols, margin=margin) is None:
        return None
    return g


def _ro_objs(g, bg=0):
    obs = objects(g, bg)
    return sorted(obs, key=lambda o: bbox(o)[:2])


def _ocolour(g, o):
    r, c = o[0]
    return g[r][c]


def _shape_sig(o):
    r0 = min(r for r, _ in o); c0 = min(c for _, c in o)
    return tuple(sorted((r - r0, c - c0) for r, c in o))


def _shape_type(o):
    r0, c0, r1, c1 = bbox(o)
    h, w = r1 - r0 + 1, c1 - c0 + 1
    if h == 1 or w == 1:
        return 2
    if h == w and len(o) == h * w:
        return 1
    return 3


def _perimeter(g, o):
    h, w = dims(g); p = 0
    for r, c in o:
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if not (0 <= nr < h and 0 <= nc < w) or g[nr][nc] == 0:
                p += 1
                break
    return p


def _blobs(g, bg=0):
    """Connected regions of ANY non-background colours (4-conn, colour ignored) -- the multi-colour
    blob helper glib does not provide directly."""
    H, W = dims(g); seen, out = set(), []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or g[r][c] == bg:
                continue
            comp, st = [], [(r, c)]; seen.add((r, c))
            while st:
                y, x = st.pop(); comp.append((y, x))
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen and g[ny][nx] != bg:
                        seen.add((ny, nx)); st.append((ny, nx))
            out.append(comp)
    return out


def _bar(colour, n, width=9):
    n = min(n, width)
    return [colour] * n + [0] * (width - n)


# ---------- 1 ----------
def gi_1(rng): return _scene(rng, 2, 6, 2, 12, 6, 18, 1, 0.35)
def tf_1(g):
    obs = _ro_objs(g)
    if len(obs) < 2: return None
    return [[_ocolour(g, o)] + _bar(_ocolour(g, o), len(o)) for o in obs]
rule("legend_colour_size_bar_table", "Table with one row per object ordered by first appearance in reading order: column 0 is a swatch of the object's colour, columns 1-9 a bar of that colour whose length is the object's cell count, capped at 9.", gi_1, tf_1)


# ---------- 2 ----------
def gi_2(rng): return _scene_multi(rng, 3, 8, 2, 10, 3, 6, 6, 18, 1, 0.35)
def tf_2(g):
    obs = _ro_objs(g); seen = []
    for o in obs:
        c = _ocolour(g, o)
        if c not in seen: seen.append(c)
    if not (2 <= len(seen) <= 9): return None
    return [seen + [0] * (9 - len(seen))]
rule("legend_swatch_row_first_appearance", "Output one row of fixed width 9: a swatch for each distinct colour present, ordered by that colour's first appearance in reading order, padded with background on the right.", gi_2, tf_2)


# ---------- 3 ----------
def gi_3(rng): return _scene_multi(rng, 4, 10, 2, 10, 2, 5, 6, 18, 1, 0.35)
def tf_3(g):
    obs = _ro_objs(g); order = []
    for o in obs:
        c = _ocolour(g, o)
        if c not in order: order.append(c)
    if len(order) < 2: return None
    rows = []
    for col in order:
        group = [o for o in obs if _ocolour(g, o) == col]
        rows.append([col, min(len(group), 9), min(max(len(o) for o in group), 9)])
    return rows
rule("legend_colour_count_maxsize_table", "3-column table, one row per distinct colour ordered by first appearance in reading order: colour swatch, count of objects of that colour (capped 9), largest object's cell count among them (capped 9).", gi_3, tf_3)


# ---------- 4 ----------
def gi_4(rng):
    h, w = _hw(rng, 8, 18, 0.35); g = blank(h, w)
    nshapes = rng.randint(2, 3)
    base = [random_shape(rng, rng.randint(3, 7)) for _ in range(nshapes)]
    reps, cols = [], []
    for sh in base:
        for _ in range(rng.randint(2, 4)):
            reps.append(sh); cols.append(rng.choice(COLOURS))
    order = list(range(len(reps))); rng.shuffle(order)
    reps = [reps[i] for i in order]; cols = [cols[i] for i in order]
    if place_shapes(rng, g, reps, cols, margin=1) is None: return None
    return g
def tf_4(g):
    obs = _ro_objs(g)
    sigs, firstcol, counts = [], {}, {}
    for o in obs:
        s = _shape_sig(o)
        if s not in firstcol:
            sigs.append(s); firstcol[s] = _ocolour(g, o)
        counts[s] = counts.get(s, 0) + 1
    if len(sigs) < 2: return None
    return [[firstcol[s]] + _bar(firstcol[s], counts[s]) for s in sigs]
rule("legend_shape_swatch_count_table", "One row per distinct shape (cells normalised to their bounding box, rotations counted separately), ordered by that shape's first appearance in reading order: column 0 a swatch of its first occurrence's colour, columns 1-9 a bar whose length is the number of objects sharing that shape, capped at 9.", gi_4, tf_4)


# ---------- 5 ----------
def gi_5(rng): return _scene_multi(rng, 4, 10, 2, 10, 3, 6, 6, 18, 1, 0.35)
def tf_5(g):
    cnt = {}
    for row in g:
        for v in row:
            if v: cnt[v] = cnt.get(v, 0) + 1
    if len(cnt) < 2: return None
    return [[c] for c in sorted(cnt, key=lambda c: (-cnt[c], c))]
rule("palette_sorted_by_cellcount_desc", "Single column, one swatch per row, listing every colour present sorted by its total cell count from most to least; ties broken by lower colour value first.", gi_5, tf_5)


# ---------- 6 ----------
def gi_6(rng): return _scene_multi(rng, 2, 6, 2, 10, 2, 5, 6, 18, 1, 0.35)
def tf_6(g):
    present = set(v for row in g for v in row if v)
    missing = [c for c in range(1, 10) if c not in present]
    if not missing or len(missing) == 9: return None
    return [missing + [0] * (9 - len(missing))]
rule("legend_missing_colours_row", "Output one row of fixed width 9 listing, in ascending order starting at column 0, the colours 1-9 that do NOT appear anywhere in the input, padded with background on the right.", gi_6, tf_6, digits=True)


# ---------- 7 ----------
def gi_7(rng):
    h, w = _hw(rng, 10, 20, 0.35); g = blank(h, w)
    n = rng.randint(2, 4); placed = 0; tries = 0
    while placed < n and tries < 80:
        tries += 1
        r0, c0 = rng.randint(0, h - 5), rng.randint(0, w - 5)
        r1 = rng.randint(r0 + 3, min(h - 1, r0 + 6)); c1 = rng.randint(c0 + 3, min(w - 1, c0 + 6))
        if all(g[r][c] == 0 for r in range(max(0, r0 - 1), min(h, r1 + 2)) for c in range(max(0, c0 - 1), min(w, c1 + 2))):
            fcol, ccol = rng.sample(COLOURS, 2)
            rect(g, r0, c0, r1, c1, fcol, fill=False)
            g[(r0 + r1) // 2][(c0 + c1) // 2] = ccol
            placed += 1
    return g if placed >= 2 else None
def tf_7(g):
    frames = []
    for o in _ro_objs(g):
        r0, c0, r1, c1 = bbox(o)
        if len(o) == 2 * (r1 - r0 + c1 - c0) and r1 > r0 + 1 and c1 > c0 + 1:
            ccol = 0
            for r in range(r0 + 1, r1):
                for c in range(c0 + 1, c1):
                    if g[r][c]:
                        ccol = g[r][c]; break
                if ccol: break
            frames.append([_ocolour(g, o), ccol])
    return frames if len(frames) >= 2 else None
rule("legend_frame_content_colour_pairs", "Legend table with one row per hollow rectangular frame, ordered by the frame's top-left corner in reading order: column 0 the frame's border colour, column 1 the colour of the marker inside it.", gi_7, tf_7)


# ---------- 8 ----------
def gi_8(rng): return _scene_multi(rng, 4, 10, 2, 10, 3, 6, 10, 22, 1, 0.4)
def tf_8(g):
    h, w = dims(g); hh, hw = h // 2, w // 2
    quads = [(0, hh, 0, hw), (0, hh, hw, w), (hh, h, 0, hw), (hh, h, hw, w)]
    out = [[0, 0], [0, 0]]; any_nonbg = False
    for idx, (r0, r1, c0, c1) in enumerate(quads):
        cnt = {}
        for r in range(r0, r1):
            for c in range(c0, c1):
                v = g[r][c]
                if v: cnt[v] = cnt.get(v, 0) + 1
        best = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if cnt else 0
        if cnt: any_nonbg = True
        out[idx // 2][idx % 2] = best
    return out if any_nonbg else None
rule("legend_quadrant_dominant_colour_2x2", "Split the grid into four quadrants (rows 0..h//2-1 / h//2..h-1 by columns 0..w//2-1 / w//2..w-1); output a 2x2 grid whose cell is the most frequent non-background colour in that quadrant, ties broken by lower colour value, 0 if empty.", gi_8, tf_8)


# ---------- 9 ----------
def gi_9(rng): return _scene_multi(rng, 3, 9, 2, 8, 4, 6, 8, 20, 1, 0.35)
def tf_9(g):
    col = []; any_nonbg = False
    for row in g:
        v = 0
        for x in row:
            if x: v = x; any_nonbg = True; break
        col.append([v])
    return col if any_nonbg else None
rule("legend_row_first_colour_column", "Output a single column with one cell per input row, giving the first non-background colour found scanning that row left to right, or 0 if the row has none.", gi_9, tf_9)


# ---------- 10 ----------
def gi_10(rng): return _scene_multi(rng, 3, 9, 2, 10, 3, 6, 6, 18, 1, 0.35)
def tf_10(g):
    obs = _ro_objs(g)
    if len(obs) < 2: return None
    return [[_ocolour(g, o) for o in obs]]
rule("legend_object_colour_strip_reading_order", "Output one row whose width equals the number of objects: one cell per object giving its colour, ordered left to right by the object's first appearance in reading order.", gi_10, tf_10)


# ---------- 11 ----------
def gi_11(rng): return _scene_multi(rng, 4, 10, 2, 10, 2, 5, 6, 18, 1, 0.35)
def tf_11(g):
    obs = _ro_objs(g); order = []
    for o in obs:
        c = _ocolour(g, o)
        if c not in order: order.append(c)
    if len(order) < 2: return None
    rows = []
    for col in order:
        group = [o for o in obs if _ocolour(g, o) == col]
        rows.append([col, min(len(group), 9), min(sum(len(o) for o in group) // len(group), 9)])
    return rows
rule("legend_colour_count_avgsize_table", "3-column table, one row per distinct colour ordered by first appearance in reading order: colour swatch, object count of that colour (capped 9), floor of the average object size for that colour (capped 9).", gi_11, tf_11)


# ---------- 12 ----------
def gi_12(rng): return _scene_multi(rng, 4, 10, 2, 10, 2, 5, 6, 18, 1, 0.35)
def tf_12(g):
    obs = _ro_objs(g); order = []
    for o in obs:
        c = _ocolour(g, o)
        if c not in order: order.append(c)
    if len(order) < 2: return None
    rows = []
    for col in order:
        group = [o for o in obs if _ocolour(g, o) == col]
        rows.append([col, min(min(len(o) for o in group), 9)])
    return rows
rule("legend_colour_smallest_object_table", "2-column table, one row per distinct colour ordered by first appearance in reading order: colour swatch, and the smallest object's cell count of that colour (capped 9).", gi_12, tf_12)


# ---------- 13 ----------
def gi_13(rng): return _scene_multi(rng, 5, 14, 1, 14, 2, 5, 8, 20, 1, 0.35)
def tf_13(g):
    obs = objects(g, 0)
    if len(obs) < 3: return None
    buckets = [0, 0, 0, 0]
    for o in obs:
        n = len(o)
        buckets[0 if n <= 3 else 1 if n <= 6 else 2 if n <= 9 else 3] += 1
    if sum(1 for b in buckets if b) < 2: return None
    rows = []
    for i, b in enumerate(buckets):
        col = i + 1
        rows.append([col] + _bar(col, b))
    return rows
rule("legend_size_bucket_histogram", "4-row histogram of object sizes bucketed into 1-3, 4-6, 7-9, 10+ cells: row i uses fixed colour i+1 (1..4) as both row label and bar colour, bar length in columns 1-9 equals the count in that bucket, capped at 9.", gi_13, tf_13, digits=True)


# ---------- 14 ----------
def gi_14(rng): return _scene_multi(rng, 4, 10, 2, 10, 2, 5, 6, 18, 1, 0.35)
def tf_14(g):
    cnt = {}
    for o in objects(g, 0):
        c = _ocolour(g, o); cnt[c] = cnt.get(c, 0) + 1
    if len(cnt) < 2: return None
    rows = []
    for c in sorted(cnt):
        rows.append([c] + _bar(c, cnt[c]))
    return rows
rule("legend_colour_ascending_count_bars", "Table with one row per distinct colour present, ordered by ascending colour value: column 0 the swatch, columns 1-9 a bar of that colour whose length is the object count of that colour, capped at 9.", gi_14, tf_14)


# ---------- 15 ----------
def gi_15(rng): return _scene_multi(rng, 3, 9, 2, 8, 4, 6, 8, 20, 1, 0.35)
def tf_15(g):
    h, w = dims(g); row = []; any_nonbg = False
    for c in range(w):
        v = 0
        for r in range(h):
            if g[r][c]: v = g[r][c]; any_nonbg = True; break
        row.append(v)
    return [row] if any_nonbg else None
# legend_column_first_colour_row dropped 2026-10-12 (review 2: behavioural duplicate of top_edge_colour_projection)
# ---------- 16 ----------
def gi_16(rng): return _scene_multi(rng, 4, 10, 2, 10, 3, 6, 10, 22, 1, 0.4)
def tf_16(g):
    h, w = dims(g); hh, hw = h // 2, w // 2
    obs = objects(g, 0)
    if len(obs) < 2: return None
    counts = [[0, 0], [0, 0]]
    for o in obs:
        r0, c0, _, _ = bbox(o)
        counts[0 if r0 < hh else 1][0 if c0 < hw else 1] += 1
    return [[min(v, 9) for v in row] for row in counts]
rule("legend_quadrant_object_count_2x2", "Split the grid into four quadrants by each object's top-left bbox cell (row<h//2 vs >=h//2, column<w//2 vs >=w//2); output a 2x2 grid of the object count in each quadrant, capped at 9.", gi_16, tf_16, digits=True)


# ---------- 17 ----------
def gi_17(rng): return _scene(rng, 2, 6, 2, 12, 6, 18, 1, 0.35)
def tf_17(g):
    obs = _ro_objs(g)
    if len(obs) < 2: return None
    rows = []
    for o in obs:
        r0, c0, r1, c1 = bbox(o); area = (r1 - r0 + 1) * (c1 - c0 + 1)
        col = _ocolour(g, o)
        rows.append([col] + _bar(col, area))
    return rows
rule("legend_colour_bbox_area_bar", "Table with one row per object ordered by first appearance in reading order: column 0 the colour swatch, columns 1-9 a bar of that colour whose length is the object's bounding-box area, capped at 9.", gi_17, tf_17)


# ---------- 18 ----------
def gi_18(rng): return _scene_multi(rng, 4, 10, 2, 10, 2, 5, 6, 18, 1, 0.35)
def tf_18(g):
    obs = _ro_objs(g); order = []
    for o in obs:
        c = _ocolour(g, o)
        if c not in order: order.append(c)
    if len(order) < 2: return None
    cnt = {c: 0 for c in order}
    for o in obs: cnt[_ocolour(g, o)] += 1
    return [[min(cnt[c], 9)] for c in order]
rule("legend_colour_digit_count_column", "Single column, one row per distinct colour ordered by first appearance in reading order, holding the literal count (capped 9) of objects of that colour as a digit value.", gi_18, tf_18, digits=True)


# ---------- 19 ----------
def gi_19(rng): return _scene_multi(rng, 2, 6, 2, 10, 2, 5, 6, 18, 1, 0.35)
def tf_19(g):
    present = set(v for row in g for v in row if v)
    if len(present) < 2: return None
    return [[c if c in present else 0 for c in range(1, 10)]]
rule("legend_colour_presence_row9", "Output one fixed-width-9 row, column i (0-based) holding colour i+1 if that colour is present anywhere in the input, else 0.", gi_19, tf_19, digits=True)


# ---------- 20 ----------
def gi_20(rng): return gi_4(rng)
def tf_20(g):
    obs = _ro_objs(g); seen = set(); row = []
    for o in obs:
        s = _shape_sig(o)
        if s not in seen:
            seen.add(s); row.append(_ocolour(g, o))
    if len(row) < 2: return None
    return [row]
rule("legend_distinct_shape_count_swatch", "Output one row, one cell per distinct shape (bounding-box-normalised cell pattern, rotations counted separately), ordered by that shape's first appearance in reading order, giving the colour of its first occurrence.", gi_20, tf_20)


# ---------- 21 ----------
def gi_21(rng): return _scene_multi(rng, 3, 9, 2, 10, 3, 6, 6, 18, 1, 0.35)
def tf_21(g):
    obs = _ro_objs(g); order = []
    for o in obs:
        c = _ocolour(g, o)
        if c not in order: order.append(c)
    if len(order) < 2: return None
    return [[c, i + 1] for i, c in enumerate(order)]
rule("legend_colour_first_appearance_rank", "2-column table, one row per distinct colour in order of first appearance in reading order: column 0 the swatch, column 1 that colour's 1-based rank of first appearance (a literal digit).", gi_21, tf_21, digits=True)


# ---------- 22 ----------
def gi_22(rng):
    h, w = _hw(rng, 8, 20, 0.35); g = blank(h, w)
    k = rng.randint(4, 9)
    shapes = [random_shape(rng, rng.randint(2, 6)) for _ in range(k)]
    cols = [rng.choice(COLOURS) for _ in range(k)]
    if place_shapes(rng, g, shapes, cols, margin=0) is None: return None
    return g
def tf_22(g):
    blobs = [b for b in _blobs(g, 0) if len(b) >= 2]
    if len(blobs) < 2: return None
    blobs.sort(key=min)
    rows = []
    for b in blobs:
        cnt = {}
        for r, c in b: cnt[g[r][c]] = cnt.get(g[r][c], 0) + 1
        col = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        rows.append([col] + _bar(col, len(b)))
    return rows
rule("legend_blob_dominant_colour_sizes", "Connected regions of any non-background colours (4-connectivity, colour ignored) each become one row, ordered by the blob's topmost-then-leftmost cell in reading order: column 0 the blob's most frequent colour (ties by lower colour value), columns 1-9 a bar of that colour whose length is the blob's total cell count, capped at 9.", gi_22, tf_22)


# ---------- 23 ----------
def gi_23(rng): return _scene_multi(rng, 4, 10, 2, 10, 3, 6, 6, 18, 1, 0.35)
def tf_23(g):
    h, w = dims(g); last = {}; idx = 0
    for r in range(h):
        for c in range(w):
            v = g[r][c]
            if v: last[v] = idx
            idx += 1
    if len(last) < 2: return None
    return [[c] for c in sorted(last, key=lambda c: last[c])]
rule("palette_sorted_by_last_appearance", "Single column, one swatch per row, listing every colour present ordered by the position of its LAST occurrence in reading order (row by row, left to right), earliest last-occurrence first.", gi_23, tf_23)


# ---------- 24 ----------
def gi_24(rng): return _scene_multi(rng, 3, 9, 2, 8, 4, 6, 8, 20, 1, 0.35)
def tf_24(g):
    out = []; any_nonbg = False
    for row in g:
        cnt = {}
        for v in row:
            if v: cnt[v] = cnt.get(v, 0) + 1
        if cnt:
            any_nonbg = True
            best = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        else:
            best = 0
        out.append([best])
    return out if any_nonbg else None
rule("legend_row_dominant_colour_column", "Output a single column with one cell per input row, giving that row's most frequent non-background colour, ties broken by lower colour value, 0 if the row has none.", gi_24, tf_24)


# ---------- 25 ----------
def gi_25(rng): return _scene_multi(rng, 4, 10, 2, 10, 2, 5, 10, 22, 1, 0.4)
def tf_25(g):
    h, w = dims(g); obs = objects(g, 0)
    if len(obs) < 2: return None
    counts = [0] * w; colcnt = [dict() for _ in range(w)]
    for o in obs:
        r0, c0, r1, c1 = bbox(o); col = _ocolour(g, o)
        for c in range(c0, c1 + 1):
            counts[c] += 1; colcnt[c][col] = colcnt[c].get(col, 0) + 1
    H = 9; out = blank(H, w)
    for c in range(w):
        n = min(counts[c], H)
        if n:
            dom = sorted(colcnt[c].items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            for r in range(H - n, H): out[r][c] = dom
    return out if any(counts) else None
rule("legend_column_object_count_bar", "Output a fixed-height-9 bar chart, one column per input column: bar height equals the number of objects whose bounding box spans that column, capped at 9, coloured by that column's most frequent object colour, ties by lower colour value.", gi_25, tf_25)


# ---------- 26 ----------
def gi_26(rng): return _scene_multi(rng, 4, 10, 2, 10, 3, 6, 6, 18, 1, 0.35)
def tf_26(g):
    cnt = {}
    for row in g:
        for v in row:
            if v: cnt[v] = cnt.get(v, 0) + 1
    if not (2 <= len(cnt) <= 9): return None
    order = sorted(cnt, key=lambda c: (-cnt[c], c))
    return [order + [0] * (9 - len(order))]
rule("legend_swatch_row_by_frequency", "Output one row of fixed width 9: a swatch for each distinct colour present, ordered by total cell count from most to least (ties broken by lower colour value), padded with background on the right.", gi_26, tf_26)


# ---------- 27 ----------
def gi_27(rng): return _scene_multi(rng, 4, 10, 2, 10, 2, 5, 6, 18, 1, 0.35)
def tf_27(g):
    obs = _ro_objs(g); order = []
    for o in obs:
        c = _ocolour(g, o)
        if c not in order: order.append(c)
    if len(order) < 2: return None
    rows = []
    for c in order:
        n = sum(1 for o in obs if _ocolour(g, o) == c)
        rows.append([c, 1 if n % 2 == 0 else 2])
    return rows
rule("legend_colour_count_parity_table", "2-column table, one row per distinct colour ordered by first appearance in reading order: column 0 the swatch, column 1 is 1 if that colour's object count is even, 2 if odd.", gi_27, tf_27, digits=True)


# ---------- 28 ----------
def gi_28(rng): return _scene_multi(rng, 4, 10, 2, 10, 2, 5, 6, 18, 1, 0.35)
def tf_28(g):
    obs = _ro_objs(g); tot = {}; order = []
    for o in obs:
        c = _ocolour(g, o)
        if c not in order: order.append(c)
        tot[c] = tot.get(c, 0) + len(o)
    if len(order) < 2: return None
    ranked = sorted(tot, key=lambda c: (-tot[c], c))
    rankof = {c: i + 1 for i, c in enumerate(ranked)}
    return [[c, rankof[c]] for c in order]
rule("legend_colour_size_rank_table", "2-column table, one row per distinct colour ordered by first appearance in reading order: column 0 the swatch, column 1 that colour's rank by total cell count summed across its objects (1 = most total cells, ties by lower colour value).", gi_28, tf_28, digits=True)


# ---------- 29 ----------
def gi_29(rng):
    h, w = _hw(rng, 10, 22, 0.35); g = blank(h, w)
    n = rng.randint(2, 5); cols = colours(rng, n); placed = 0; tries = 0
    while placed < n and tries < 100:
        tries += 1
        rh, rw = rng.randint(3, 7), rng.randint(3, 7)
        if rh > h - 2 or rw > w - 2: continue
        r0, c0 = rng.randint(0, h - rh), rng.randint(0, w - rw)
        r1, c1 = r0 + rh - 1, c0 + rw - 1
        if all(g[r][c] == 0 for r in range(max(0, r0 - 1), min(h, r1 + 2)) for c in range(max(0, c0 - 1), min(w, c1 + 2))):
            rect(g, r0, c0, r1, c1, cols[placed], fill=False); placed += 1
    return g if placed >= 2 else None
def tf_29(g):
    rows = []
    for o in _ro_objs(g):
        r0, c0, r1, c1 = bbox(o)
        if len(o) != 2 * (r1 - r0 + c1 - c0): continue
        holes = (r1 - r0 - 1) * (c1 - c0 - 1); col = _ocolour(g, o)
        rows.append([col] + _bar(col, holes))
    return rows if len(rows) >= 2 else None
rule("legend_object_hole_count_bars", "One row per hollow rectangular frame, ordered by first appearance in reading order: column 0 the frame's colour, columns 1-9 a bar of that colour whose length is the frame's interior cell count, capped at 9.", gi_29, tf_29)


# ---------- 30 ----------
def gi_30(rng): return _scene_multi(rng, 4, 10, 2, 10, 2, 5, 8, 20, 1, 0.35)
def tf_30(g):
    h, w = dims(g); obs = _ro_objs(g); order = []
    for o in obs:
        c = _ocolour(g, o)
        if c not in order: order.append(c)
    if len(order) < 2: return None
    touch = {c: False for c in order}
    for o in obs:
        c = _ocolour(g, o)
        if any(r == 0 or r == h - 1 or cc == 0 or cc == w - 1 for r, cc in o):
            touch[c] = True
    return [[c, 1 if touch[c] else 2] for c in order]
rule("legend_colour_border_touch_table", "2-column table, one row per distinct colour ordered by first appearance in reading order: column 0 the swatch, column 1 is 1 if any object of that colour touches the grid's outer edge, else 2.", gi_30, tf_30, digits=True)


# ---------- 31 ----------
def gi_31(rng): return _scene_multi(rng, 3, 9, 2, 10, 3, 6, 6, 18, 1, 0.35)
def tf_31(g):
    present = sorted(set(v for row in g for v in row if v))
    if len(present) < 2: return None
    return [[c] for c in present]
rule("legend_unique_colours_ascending_column", "Single column listing every distinct colour present, one per row, sorted by ascending colour value.", gi_31, tf_31)


# ---------- 32 ----------
def gi_32(rng): return _scene_multi(rng, 5, 14, 1, 10, 2, 5, 8, 20, 1, 0.35)
def tf_32(g):
    obs = objects(g, 0)
    if len(obs) < 3: return None
    cnt = {1: 0, 2: 0, 3: 0}
    for o in obs: cnt[_shape_type(o)] += 1
    rows = []
    for label in (1, 2, 3):
        if cnt[label]:
            rows.append([label] + _bar(label, cnt[label]))
    return rows if len(rows) >= 2 else None
rule("legend_shape_type_count_rows", "Rows for each shape category present among square (solid filled bounding box, fixed label colour 1), line (single row or column, label 2), other (label 3): columns 1-9 a bar of the label colour whose length is the count of that category, capped at 9.", gi_32, tf_32, digits=True)


# ---------- 33 ----------
def gi_33(rng): return _scene_multi(rng, 4, 10, 2, 10, 3, 6, 9, 21, 1, 0.4)
def tf_33(g):
    h, w = dims(g)
    if h < 3: return None
    bands = [(0, h // 3), (h // 3, 2 * h // 3), (2 * h // 3, h)]
    out = []; any_nonbg = False
    for r0, r1 in bands:
        cnt = {}
        for r in range(r0, r1):
            for v in g[r]:
                if v: cnt[v] = cnt.get(v, 0) + 1
        if cnt:
            any_nonbg = True
            best = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        else:
            best = 0
        out.append([best])
    return out if any_nonbg else None
rule("legend_band_dominant_colour_column", "Split the grid into three horizontal bands of equal height (extra rows in the bottom band): output a 3-row, 1-column grid giving each band's most frequent non-background colour, ties by lower colour value, 0 if empty.", gi_33, tf_33)


# ---------- 34 ----------
def gi_34(rng): return _scene_multi(rng, 3, 9, 2, 10, 3, 6, 6, 18, 1, 0.35)
def tf_34(g):
    obs = _ro_objs(g)
    if len(obs) < 2: return None
    return [[_ocolour(g, o), min(len(o), 9)] for o in obs]
rule("legend_object_colour_cellcount_digits", "2-column table, one row per object ordered by first appearance in reading order: column 0 its colour, column 1 its cell count as a literal digit, capped at 9.", gi_34, tf_34, digits=True)


# ---------- 35 ----------
def gi_35(rng): return _scene_multi(rng, 4, 10, 2, 10, 2, 5, 6, 18, 1, 0.35)
def tf_35(g):
    obs = _ro_objs(g); order = []
    for o in obs:
        c = _ocolour(g, o)
        if c not in order: order.append(c)
    if len(order) < 2: return None
    cnt = {c: 0 for c in order}
    for o in obs: cnt[_ocolour(g, o)] += 1
    return [[min(cnt[c], 9) for c in order]]
rule("legend_colour_count_digit_row", "Single row, one cell per distinct colour ordered by first appearance in reading order, holding the literal count of objects of that colour as a digit, capped at 9.", gi_35, tf_35, digits=True)


# ---------- 36 ----------
def gi_36(rng): return _scene_multi(rng, 3, 8, 2, 10, 3, 6, 6, 18, 1, 0.35)
def tf_36(g):
    h, w = dims(g); seen = []
    for c in range(w):
        for r in range(h):
            v = g[r][c]
            if v and v not in seen: seen.append(v)
    if not (2 <= len(seen) <= 9): return None
    return [seen + [0] * (9 - len(seen))]
rule("legend_swatch_column_by_column_order", "Output one row of fixed width 9: a swatch for each distinct colour present, ordered by first appearance under COLUMN-major reading order (scanning column 0 top-to-bottom, then column 1, and so on), padded with background on the right.", gi_36, tf_36)


# ---------- 37 ----------
def gi_37(rng): return _scene(rng, 2, 6, 2, 12, 6, 18, 1, 0.35)
def tf_37(g):
    obs = _ro_objs(g)
    if len(obs) < 2: return None
    rows = []
    for o in obs:
        col = _ocolour(g, o)
        rows.append([col] + _bar(col, _perimeter(g, o)))
    return rows
rule("legend_shape_perimeter_bar_table", "One row per object ordered by first appearance in reading order: column 0 its colour, columns 1-9 a bar of that colour whose length is the number of the object's cells with at least one background or off-grid 4-neighbour, capped at 9.", gi_37, tf_37)


# ---------- 38 ----------
def gi_38(rng): return _scene_multi(rng, 3, 8, 2, 10, 2, 5, 8, 20, 1, 0.35)
def tf_38(g):
    obs = objects(g, 0)
    if len(obs) < 2: return None
    allcells = [c for o in obs for c in o]
    r0 = min(r for r, _ in allcells); r1 = max(r for r, _ in allcells)
    c0 = min(c for _, c in allcells); c1 = max(c for _, c in allcells)
    sub = crop(g, r0, c0, r1, c1); w = len(sub[0])
    order = []
    for o in _ro_objs(g):
        col = _ocolour(g, o)
        if col not in order: order.append(col)
    if len(order) > w: return None
    return [row[:] for row in sub] + [order + [0] * (w - len(order))]
rule("legend_colours_present_footer_row", "Crop to the bounding box of all objects, then append one extra row at the bottom, padded on the right with background, listing the distinct colours present in order of first appearance in reading order.", gi_38, tf_38)


# ---------- 39 ----------
def gi_39(rng): return _scene_multi(rng, 4, 10, 2, 10, 2, 5, 6, 18, 1, 0.35)
def tf_39(g):
    obs = _ro_objs(g); order = []
    for o in obs:
        c = _ocolour(g, o)
        if c not in order: order.append(c)
    if len(order) < 2: return None
    rows = []
    for col in order:
        tot = sum(bbox(o)[3] - bbox(o)[1] + 1 for o in obs if _ocolour(g, o) == col)
        rows.append([col] + _bar(col, tot))
    return rows
rule("legend_colour_object_width_bar", "One row per distinct colour ordered by first appearance in reading order: column 0 the swatch, columns 1-9 a bar of that colour whose length is the sum of the bounding-box widths of all objects of that colour, capped at 9.", gi_39, tf_39)


# ---------- 40 ----------
def gi_40(rng): return _scene_multi(rng, 3, 9, 2, 10, 2, 5, 6, 18, 1, 0.35)
def tf_40(g):
    obs = _ro_objs(g); order = []
    for o in obs:
        c = _ocolour(g, o)
        if c not in order: order.append(c)
    if len(order) < 2: return None
    rows = []
    for col in order:
        best = max(bbox(o)[3] for o in obs if _ocolour(g, o) == col)
        rows.append([col, min(best, 9)])
    return rows
rule("legend_colour_rightmost_object_column", "2-column table, one row per distinct colour ordered by first appearance in reading order: column 0 the swatch, column 1 the rightmost column index (0-based, capped at 9) reached by any object of that colour.", gi_40, tf_40, digits=True)
