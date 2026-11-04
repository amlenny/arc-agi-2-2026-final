# b047_glyphs.py -- small glyphs as symbols: fixed 3x3 shapes (plus, x, l, t, ring, diag, dot, bar)
# placed on a lattice with spacing, read back by shape, recoloured/replaced/sorted/counted.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

GLYPHS = {
    "plus": [(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)],
    "x":    [(0, 0), (0, 2), (1, 1), (2, 0), (2, 2)],
    "l":    [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)],
    "t":    [(0, 0), (0, 1), (0, 2), (1, 1), (2, 1)],
    "ring": [(0, 0), (0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2)],
    "diag": [(0, 0), (1, 1), (2, 2)],
    "dot":  [(1, 1)],
    "bar":  [(1, 0), (1, 1), (1, 2)],
}
TYPES = ["plus", "x", "l", "t", "ring", "diag", "dot", "bar"]
CYCLE = TYPES + [TYPES[0]]
MARK = 9


def _rotcells(cs, k):
    out = list(cs)
    for _ in range(k):
        out = [(c, 2 - r) for r, c in out]
    return out


def _norm(cells_):
    r0 = min(r for r, c in cells_); c0 = min(c for r, c in cells_)
    return frozenset((r - r0, c - c0) for r, c in cells_)


_SETS = {t: _norm(cs) for t, cs in GLYPHS.items()}
ROT = {t: [frozenset(_rotcells(GLYPHS[t], k)) for k in range(4)] for t in ("l", "t")}


def _stamp(g, r0, c0, t, col):
    for dr, dc in GLYPHS[t]:
        g[r0 + dr][c0 + dc] = col


def _stamp_oriented(g, r0, c0, t, k, col):
    for dr, dc in _rotcells(GLYPHS[t], k):
        g[r0 + dr][c0 + dc] = col


def _classify_full(cells_):
    s = _norm(cells_)
    for t in ("plus", "x", "ring", "dot", "bar", "diag"):
        if s == _SETS[t]:
            return t, 0
    for t in ("l", "t"):
        for k, variant in enumerate(ROT[t]):
            if s == variant:
                return t, k
    return None, None


def _dims(rng):
    rows = rng.choices([3, 4, 5, 6, 7], weights=[2, 2, 2, 3, 3])[0]
    cols = rng.choices([3, 4, 5, 6, 7], weights=[2, 2, 2, 3, 3])[0]
    return rows, cols


def _lattice(rng, rows, cols, types=TYPES, pool=None, fill=1.0):
    pool = pool or [c for c in COLOURS if c != MARK]
    g = blank(rows * 4 - 1, cols * 4 - 1)
    placements = []
    for i in range(rows):
        for j in range(cols):
            if rng.random() > fill:
                continue
            t = rng.choice(types); col = rng.choice(pool)
            r0, c0 = i * 4, j * 4
            _stamp(g, r0, c0, t, col)
            placements.append((r0, c0, t, col))
    return g, placements


def _add_key_strip(g, key_items):
    """key_items: list of (type, k, colour). Returns new grid with a 4-row key strip on top."""
    h, w = dims(g)
    kw = max(w, len(key_items) * 4 - 1)
    big = blank(h + 4, kw)
    paste(big, g, 4, 0)
    for i, (t, k, col) in enumerate(key_items):
        _stamp_oriented(big, 0, i * 4, t, k, col)
    return big


def _read_key(g, n):
    out = []
    for i in range(n):
        cs = [(r, c) for r in range(3) for c in range(i * 4, i * 4 + 3) if 0 <= c < len(g[0]) and g[r][c] != 0]
        out.append(_classify_full(cs))
    return out


def _glyph_objs(g, below=0):
    """(r0, c0, type, k, colour) for each glyph blob at or below row `below`."""
    out = []
    for comp in components(g, lambda v: v != 0, conn8=True):
        r0 = min(r for r, c in comp)
        if r0 < below:
            continue
        c0 = min(c for r, c in comp)
        col = g[comp[0][0]][comp[0][1]]
        t, k = _classify_full(comp)
        if t is None:
            continue
        out.append((r0, c0, t, k, col))
    return out


def _counts_by_type(objs):
    cnt = {}
    for _, _, t, _, _ in objs:
        cnt[t] = cnt.get(t, 0) + 1
    return cnt


# 1 -------------------------------------------------------------------------
def gi_recolour_key_pair(rng):
    rows, cols = _dims(rng)
    rows = min(rows, 6)
    g, pl = _lattice(rng, rows, cols)
    if len(pl) < 3:
        return None
    present = {t for _, _, t, _ in pl}
    if len(present) < 2:
        return None
    from_t, to_t = rng.sample(sorted(present), 2)
    return _add_key_strip(g, [(from_t, 0, MARK), (to_t, 0, MARK)])


def tf_recolour_key_pair(g):
    key = _read_key(g, 2)
    from_t, to_t = key[0][0], key[1][0]
    out = copy(g)
    for r0, c0, t, k, col in _glyph_objs(g, below=4):
        if t == from_t:
            for dr, dc in GLYPHS[t]:
                out[r0 + dr][c0 + dc] = 0
            _stamp(out, r0, c0, to_t, col)
    return out if out != g else None


rule("recolour_key_pair_glyph", "A key pair of glyphs in the top strip gives (A, B); every glyph of shape A below it is redrawn as shape B, keeping its colour.", gi_recolour_key_pair, tf_recolour_key_pair)


# 2 -------------------------------------------------------------------------
def gi_type_fixed_colour(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, fill=0.85)
    if len({t for _, _, t, _ in pl}) < 2:
        return None
    return g


def tf_type_fixed_colour(g):
    out = copy(g)
    for r0, c0, t, k, col in _glyph_objs(g):
        newcol = TYPES.index(t) + 1
        for dr, dc in GLYPHS[t]:
            out[r0 + dr][c0 + dc] = newcol
    return out if out != g else None


rule("type_decides_glyph_colour", "Every glyph is recoloured to a fixed colour number determined only by its shape type.", gi_type_fixed_colour, tf_type_fixed_colour, digits=True)


# 3 -------------------------------------------------------------------------
def gi_unique_type_recoloured(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, fill=0.8)
    cnt = {}
    for _, _, t, _ in pl:
        cnt[t] = cnt.get(t, 0) + 1
    if list(cnt.values()).count(1) != 1 or len(cnt) < 2:
        return None
    return g


def tf_unique_type_recoloured(g):
    objs = _glyph_objs(g)
    cnt = _counts_by_type(objs)
    uniq = [t for t, n in cnt.items() if n == 1]
    if len(uniq) != 1:
        return None
    out = copy(g)
    for r0, c0, t, k, col in objs:
        if t == uniq[0]:
            for dr, dc in GLYPHS[t]:
                out[r0 + dr][c0 + dc] = 8
    return out if out != g else None


rule("lone_type_recoloured_eight", "The one glyph shape that appears exactly once among all glyphs is recoloured to colour 8.", gi_unique_type_recoloured, tf_unique_type_recoloured)


# 4 -------------------------------------------------------------------------
def gi_majority_erased(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, fill=0.8)
    if len({t for _, _, t, _ in pl}) < 2 or len(pl) < 4:
        return None
    return g


def tf_majority_erased(g):
    objs = _glyph_objs(g)
    cnt = _counts_by_type(objs)
    if not cnt:
        return None
    best = max(cnt.values())
    top = [t for t, n in cnt.items() if n == best]
    if len(top) != 1:
        return None
    out = copy(g)
    for r0, c0, t, k, col in objs:
        if t == top[0]:
            for dr, dc in GLYPHS[t]:
                out[r0 + dr][c0 + dc] = 0
    return out if out != g else None


rule("majority_shape_erased", "Every glyph whose shape is the single most common one is erased.", gi_majority_erased, tf_majority_erased)


# 5 -------------------------------------------------------------------------
def gi_keep_only_majority(rng):
    return gi_majority_erased(rng)


def tf_keep_only_majority(g):
    objs = _glyph_objs(g)
    cnt = _counts_by_type(objs)
    if not cnt:
        return None
    best = max(cnt.values())
    top = [t for t, n in cnt.items() if n == best]
    if len(top) != 1:
        return None
    out = copy(g)
    for r0, c0, t, k, col in objs:
        if t != top[0]:
            for dr, dc in GLYPHS[t]:
                out[r0 + dr][c0 + dc] = 0
    return out if out != g else None


rule("keep_only_majority_shape", "Every glyph is erased except for the shape that occurs most often.", gi_keep_only_majority, tf_keep_only_majority)


# 6 -------------------------------------------------------------------------
def gi_cycle_advance(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, fill=0.75)
    if len(pl) < 3:
        return None
    return g


def tf_cycle_advance(g):
    out = copy(g)
    for r0, c0, t, k, col in _glyph_objs(g):
        nt = CYCLE[TYPES.index(t) + 1]
        for dr, dc in GLYPHS[t]:
            out[r0 + dr][c0 + dc] = 0
        _stamp(out, r0, c0, nt, col)
    return out if out != g else None


rule("glyph_cycle_advance", "Every glyph is replaced by the shape that follows it in the fixed cycle plus, x, l, t, ring, diag, dot, bar.", gi_cycle_advance, tf_cycle_advance)


# 7 -------------------------------------------------------------------------
def gi_cycle_retreat(rng):
    return gi_cycle_advance(rng)


def tf_cycle_retreat(g):
    out = copy(g)
    for r0, c0, t, k, col in _glyph_objs(g):
        i = TYPES.index(t)
        pt = TYPES[i - 1]
        for dr, dc in GLYPHS[t]:
            out[r0 + dr][c0 + dc] = 0
        _stamp(out, r0, c0, pt, col)
    return out if out != g else None


rule("glyph_cycle_retreat", "Every glyph is replaced by the shape that precedes it in the fixed cycle plus, x, l, t, ring, diag, dot, bar.", gi_cycle_retreat, tf_cycle_retreat)


# 8 -------------------------------------------------------------------------
def gi_rotate_l_to_key(rng):
    rows, cols = _dims(rng)
    rows = min(rows, 6)
    pool = [c for c in COLOURS if c != MARK]
    g, pl = _lattice(rng, rows, cols, types=["l"], pool=pool, fill=0.7)
    if len(pl) < 3:
        return None
    k = rng.randint(0, 3)
    for i, (r0, c0, t, col) in enumerate(pl):
        _stamp(g, r0, c0, t, 0)
        _stamp_oriented(g, r0, c0, t, rng.randint(0, 3), col)
    return _add_key_strip(g, [("l", k, MARK)])


def tf_rotate_l_to_key(g):
    key = _read_key(g, 1)
    _, want = key[0]
    out = copy(g)
    for r0, c0, t, k, col in _glyph_objs(g, below=4):
        for dr, dc in GLYPHS["l"]:
            pass
        for dr, dc in _rotcells(GLYPHS["l"], k):
            out[r0 + dr][c0 + dc] = 0
        _stamp_oriented(out, r0, c0, "l", want, col)
    return out if out != g else None


rule("rotate_l_glyphs_to_key_orientation", "Every L-shaped glyph is rotated to match the orientation of the key L glyph in the top strip.", gi_rotate_l_to_key, tf_rotate_l_to_key)


# 9 -------------------------------------------------------------------------
def gi_rotate_t_to_key(rng):
    rows, cols = _dims(rng)
    rows = min(rows, 6)
    pool = [c for c in COLOURS if c != MARK]
    g, pl = _lattice(rng, rows, cols, types=["t"], pool=pool, fill=0.7)
    if len(pl) < 3:
        return None
    k = rng.randint(0, 3)
    for r0, c0, t, col in pl:
        _stamp(g, r0, c0, t, 0)
        _stamp_oriented(g, r0, c0, t, rng.randint(0, 3), col)
    return _add_key_strip(g, [("t", k, MARK)])


def tf_rotate_t_to_key(g):
    key = _read_key(g, 1)
    _, want = key[0]
    out = copy(g)
    for r0, c0, t, k, col in _glyph_objs(g, below=4):
        for dr, dc in _rotcells(GLYPHS["t"], k):
            out[r0 + dr][c0 + dc] = 0
        _stamp_oriented(out, r0, c0, "t", want, col)
    return out if out != g else None


rule("rotate_t_glyphs_to_key_orientation", "Every T-shaped glyph is rotated to match the orientation of the key T glyph in the top strip.", gi_rotate_t_to_key, tf_rotate_t_to_key)


# 10 ------------------------------------------------------------------------
def gi_mirror_listed(rng):
    rows, cols = _dims(rng)
    rows = min(rows, 6)
    pool = [c for c in COLOURS if c != MARK]
    g, pl = _lattice(rng, rows, cols, types=["l", "t", "diag"], pool=pool, fill=0.75)
    present = sorted({t for _, _, t, _ in pl})
    if len(present) < 2:
        return None
    n = rng.randint(1, len(present) - 1)
    keylist = rng.sample(present, n)
    return _add_key_strip(g, [(t, 0, MARK) for t in keylist])


def tf_mirror_listed(g):
    keytypes = {t for r0, c0, t, k, col in _glyph_objs(g) if r0 < 4}
    out = copy(g)
    for r0, c0, t, k, col in _glyph_objs(g, below=4):
        if t not in keytypes:
            continue
        for dr, dc in _rotcells(GLYPHS[t], k):
            out[r0 + dr][c0 + dc] = 0
        for dr, dc in _rotcells(GLYPHS[t], k):
            out[r0 + dr][c0 + (2 - dc)] = col
    return out if out != g else None


rule("mirror_glyphs_in_key_list", "Every glyph whose shape appears in the key strip's list is mirrored left-right; the rest are untouched.", gi_mirror_listed, tf_mirror_listed)


# 11 -------------------------------------------------------------------------
def gi_count_into_bars(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, fill=0.85)
    if len({t for _, _, t, _ in pl}) < 2:
        return None
    return g


def tf_count_into_bars(g):
    objs = _glyph_objs(g)
    cnt = _counts_by_type(objs)
    present = [t for t in TYPES if t in cnt]
    if len(present) < 2:
        return None
    h = max(cnt.values())
    out = blank(h, len(present))
    for j, t in enumerate(present):
        col = TYPES.index(t) + 1
        for r in range(h - cnt[t], h):
            out[r][j] = col
    return out


rule("type_counts_to_bars", "Output one vertical bar per glyph shape present, height equal to how many of that shape occur, ordered plus/x/l/t/ring/diag/dot/bar.", gi_count_into_bars, tf_count_into_bars, digits=True)


# 12 -------------------------------------------------------------------------
def gi_sorted_row(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, fill=0.7)
    if len(pl) < 3:
        return None
    return g


def tf_sorted_row(g):
    objs = _glyph_objs(g)
    if len(objs) < 2:
        return None
    objs.sort(key=lambda o: TYPES.index(o[2]))
    row = [[o[4] for o in objs]]
    return row if len({v for r in row for v in r}) > 1 else None


rule("glyphs_sorted_by_type_row", "Output one row listing every glyph's colour, ordered by shape type (plus first, bar last).", gi_sorted_row, tf_sorted_row)


# 13 -------------------------------------------------------------------------
def gi_join_same_type(rng):
    rows, cols = _dims(rng)
    pool = [c for c in COLOURS if c != MARK]
    g, pl = _lattice(rng, rows, cols, pool=pool, fill=0.6)
    if len(pl) < 4:
        return None
    return g


def tf_join_same_type(g):
    objs = _glyph_objs(g)
    out = copy(g)
    by_type = {}
    for r0, c0, t, k, col in objs:
        by_type.setdefault(t, []).append((r0, c0))
    drew = False
    for t, pts in by_type.items():
        if len(pts) != 2:
            continue
        (r0, c0), (r1, c1) = pts
        cr0, cc0, cr1, cc1 = r0 + 1, c0 + 1, r1 + 1, c1 + 1
        if cr0 == cr1:
            for x in range(min(cc0, cc1), max(cc0, cc1) + 1):
                if out[cr0][x] == 0:
                    out[cr0][x] = MARK; drew = True
        elif cc0 == cc1:
            for y in range(min(cr0, cr1), max(cr0, cr1) + 1):
                if out[y][cc0] == 0:
                    out[y][cc0] = MARK; drew = True
    return out if drew else None


rule("join_same_shape_pairs_with_line", "If exactly two glyphs share the same shape and line up on a lattice row or column, their centres are joined by a line.", gi_join_same_type, tf_join_same_type)


# 14 -------------------------------------------------------------------------
def gi_type_sequence_row(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, fill=0.75)
    pl.sort(key=lambda p: (p[0], p[1]))
    seq = [t for _, _, t, _ in pl]
    if len(set(seq)) < 2:
        return None
    return g


def tf_type_sequence_row(g):
    objs = sorted(_glyph_objs(g), key=lambda o: (o[0], o[1]))
    if len(objs) < 2:
        return None
    row = [[TYPES.index(o[2]) + 1 for o in objs]]
    return row


rule("type_sequence_as_colour_row", "Output one row where each cell is the type-index colour of a glyph, in reading order.", gi_type_sequence_row, tf_type_sequence_row, digits=True)


# 15 -------------------------------------------------------------------------
def gi_rank_by_frequency(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, fill=0.85)
    cnt = {}
    for _, _, t, _ in pl:
        cnt[t] = cnt.get(t, 0) + 1
    if len(set(cnt.values())) < 2:
        return None
    return g


def tf_rank_by_frequency(g):
    objs = _glyph_objs(g)
    cnt = _counts_by_type(objs)
    order = sorted(cnt, key=lambda t: (-cnt[t], t))
    if len(set(cnt.values())) < 2:
        return None
    rank = {t: i + 1 for i, t in enumerate(order)}
    out = copy(g)
    for r0, c0, t, k, col in objs:
        for dr, dc in GLYPHS[t]:
            out[r0 + dr][c0 + dc] = rank[t]
    return out if out != g else None


rule("recolour_by_frequency_rank", "Every glyph is recoloured to the rank number of how common its shape is (1 = most common).", gi_rank_by_frequency, tf_rank_by_frequency, digits=True)


# 16 -------------------------------------------------------------------------
def gi_shrink_to_count_pixel(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, fill=0.75)
    cnt = {}
    for _, _, t, _ in pl:
        cnt[t] = cnt.get(t, 0) + 1
    if not cnt or max(cnt.values()) > 9 or len(pl) < 3:
        return None
    return g


def tf_shrink_to_count_pixel(g):
    objs = _glyph_objs(g)
    cnt = _counts_by_type(objs)
    if any(n > 9 for n in cnt.values()):
        return None
    out = copy(g)
    for r0, c0, t, k, col in objs:
        for dr, dc in GLYPHS[t]:
            out[r0 + dr][c0 + dc] = 0
        out[r0 + 1][c0 + 1] = cnt[t]
    return out if out != g else None


rule("shrink_glyph_to_count_pixel", "Every glyph collapses to a single centre pixel whose colour is the total count of that shape in the grid.", gi_shrink_to_count_pixel, tf_shrink_to_count_pixel, digits=True)


# 17 -------------------------------------------------------------------------
def gi_erase_key_type(rng):
    rows, cols = _dims(rng)
    rows = min(rows, 6)
    pool = [c for c in COLOURS if c != MARK]
    g, pl = _lattice(rng, rows, cols, pool=pool, fill=0.8)
    present = {t for _, _, t, _ in pl}
    if len(present) < 2:
        return None
    t = rng.choice(sorted(present))
    return _add_key_strip(g, [(t, 0, MARK)])


def tf_erase_key_type(g):
    key = _read_key(g, 1)
    target = key[0][0]
    out = copy(g)
    for r0, c0, t, k, col in _glyph_objs(g, below=4):
        if t == target:
            for dr, dc in GLYPHS[t]:
                out[r0 + dr][c0 + dc] = 0
    return out if out != g else None


rule("erase_glyphs_matching_key_type", "A key glyph in the top strip names a shape; every glyph of that shape below it is erased.", gi_erase_key_type, tf_erase_key_type)


# 18 -------------------------------------------------------------------------
def gi_swap_plus_x(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, types=["plus", "x", "dot", "ring"], fill=0.8)
    present = {t for _, _, t, _ in pl}
    if "plus" not in present or "x" not in present:
        return None
    return g


def tf_swap_plus_x(g):
    out = copy(g)
    for r0, c0, t, k, col in _glyph_objs(g):
        if t not in ("plus", "x"):
            continue
        nt = "x" if t == "plus" else "plus"
        for dr, dc in GLYPHS[t]:
            out[r0 + dr][c0 + dc] = 0
        _stamp(out, r0, c0, nt, col)
    return out if out != g else None


rule("swap_plus_and_x_everywhere", "Every plus-shaped glyph becomes an x and every x-shaped glyph becomes a plus; other shapes are untouched.", gi_swap_plus_x, tf_swap_plus_x)


# 19 -------------------------------------------------------------------------
def gi_crop_unique_type(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, fill=0.8)
    cnt = {}
    for _, _, t, _ in pl:
        cnt[t] = cnt.get(t, 0) + 1
    if list(cnt.values()).count(1) != 1 or len(cnt) < 2:
        return None
    return g


def tf_crop_unique_type(g):
    objs = _glyph_objs(g)
    cnt = _counts_by_type(objs)
    uniq = [t for t, n in cnt.items() if n == 1]
    if len(uniq) != 1:
        return None
    r0, c0, t, k, col = next(o for o in objs if o[2] == uniq[0])
    h, w = dims(g)
    r0c, c0c = max(0, r0 - 1), max(0, c0 - 1)
    r1c, c1c = min(h - 1, r0 + 3), min(w - 1, c0 + 3)
    if r0c == 0 and c0c == 0 and r1c == h - 1 and c1c == w - 1:
        return None
    return crop(g, r0c, c0c, r1c, c1c)


rule("crop_unique_shape_glyph", "Output the box (with a one-cell margin) around the one glyph whose shape occurs nowhere else in the grid.", gi_crop_unique_type, tf_crop_unique_type)


# 20 -------------------------------------------------------------------------
def gi_fill_ring_centres(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, types=["ring", "plus", "dot", "l"], fill=0.75)
    if not any(t == "ring" for _, _, t, _ in pl):
        return None
    return g


def tf_fill_ring_centres(g):
    out = copy(g)
    for r0, c0, t, k, col in _glyph_objs(g):
        if t == "ring":
            out[r0 + 1][c0 + 1] = col
    return out if out != g else None


rule("fill_ring_glyph_centres", "Every ring-shaped glyph has its hollow centre filled in with its own colour.", gi_fill_ring_centres, tf_fill_ring_centres)


# 21 -------------------------------------------------------------------------
def gi_plus_to_dot(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, types=["plus", "t", "ring", "bar"], fill=0.75)
    if not any(t == "plus" for _, _, t, _ in pl):
        return None
    return g


def tf_plus_to_dot(g):
    out = copy(g)
    for r0, c0, t, k, col in _glyph_objs(g):
        if t == "plus":
            for dr, dc in GLYPHS[t]:
                out[r0 + dr][c0 + dc] = 0
            out[r0 + 1][c0 + 1] = col
    return out if out != g else None


rule("plus_glyphs_shrink_to_dots", "Every plus-shaped glyph shrinks to a single-pixel dot, keeping its colour.", gi_plus_to_dot, tf_plus_to_dot)


# 22 -------------------------------------------------------------------------
def gi_x_to_ring(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, types=["x", "l", "dot", "t"], fill=0.75)
    if not any(t == "x" for _, _, t, _ in pl):
        return None
    return g


def tf_x_to_ring(g):
    out = copy(g)
    for r0, c0, t, k, col in _glyph_objs(g):
        if t == "x":
            for dr, dc in GLYPHS[t]:
                out[r0 + dr][c0 + dc] = 0
            _stamp(out, r0, c0, "ring", col)
    return out if out != g else None


rule("x_glyphs_become_rings", "Every x-shaped glyph is redrawn as a ring, keeping its colour and position.", gi_x_to_ring, tf_x_to_ring)


# 23 -------------------------------------------------------------------------
def gi_diag_mirrored(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, types=["diag", "bar", "dot", "ring"], fill=0.75)
    if not any(t == "diag" for _, _, t, _ in pl):
        return None
    return g


def tf_diag_mirrored(g):
    out = copy(g)
    for r0, c0, t, k, col in _glyph_objs(g):
        if t == "diag":
            for dr, dc in GLYPHS[t]:
                out[r0 + dr][c0 + dc] = 0
            for dr, dc in GLYPHS[t]:
                out[r0 + dr][c0 + (2 - dc)] = col
    return out if out != g else None


rule("diag_glyphs_mirrored_always", "Every diagonal glyph is always mirrored left-right into the opposite diagonal.", gi_diag_mirrored, tf_diag_mirrored)


# 24 -------------------------------------------------------------------------
def gi_dot_to_plus(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, types=["dot", "l", "ring", "bar"], fill=0.7)
    if not any(t == "dot" for _, _, t, _ in pl):
        return None
    return g


def tf_dot_to_plus(g):
    out = copy(g)
    for r0, c0, t, k, col in _glyph_objs(g):
        if t == "dot":
            _stamp(out, r0, c0, "plus", col)
    return out if out != g else None


rule("dot_glyphs_grow_to_plus", "Every single-pixel dot glyph grows into a plus shape of the same colour.", gi_dot_to_plus, tf_dot_to_plus)


# 25 -------------------------------------------------------------------------
def gi_swap_row_pairs(rng):
    rows, cols = _dims(rng)
    if cols < 2:
        cols = 2
    g, pl = _lattice(rng, rows, cols, fill=1.0)
    if len(pl) < 2:
        return None
    return g


def tf_swap_row_pairs(g):
    objs = _glyph_objs(g)
    by_row = {}
    for o in objs:
        by_row.setdefault(o[0], []).append(o)
    out = copy(g)
    changed = False
    for r0, items in by_row.items():
        items.sort(key=lambda o: o[1])
        for i in range(0, len(items) - 1, 2):
            a, b = items[i], items[i + 1]
            ar0, ac0, at, ak, acol = a; br0, bc0, bt, bk, bcol = b
            if acol == bcol:
                continue
            for dr, dc in _rotcells(GLYPHS[at], ak):
                out[ar0 + dr][ac0 + dc] = bcol
            for dr, dc in _rotcells(GLYPHS[bt], bk):
                out[br0 + dr][bc0 + dc] = acol
            changed = True
    return out if changed else None


rule("swap_colours_of_row_neighbour_pairs", "Within each lattice row, neighbouring glyphs taken two at a time swap colours with each other.", gi_swap_row_pairs, tf_swap_row_pairs)


# 26 -------------------------------------------------------------------------
def gi_count_parity_recolour(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, fill=0.85)
    cnt = {}
    for _, _, t, _ in pl:
        cnt[t] = cnt.get(t, 0) + 1
    evens = sum(1 for n in cnt.values() if n % 2 == 0)
    odds = sum(1 for n in cnt.values() if n % 2 == 1)
    if evens == 0 or odds == 0:
        return None
    return g


def tf_count_parity_recolour(g):
    objs = _glyph_objs(g)
    cnt = _counts_by_type(objs)
    out = copy(g)
    for r0, c0, t, k, col in objs:
        newcol = 2 if cnt[t] % 2 == 0 else 7
        for dr, dc in _rotcells(GLYPHS[t], k):
            out[r0 + dr][c0 + dc] = newcol
    return out if out != g else None


rule("recolour_by_shape_count_parity", "Every glyph is recoloured colour 2 if its shape's total count is even, colour 7 if odd.", gi_count_parity_recolour, tf_count_parity_recolour)


# 27 -------------------------------------------------------------------------
def gi_outline_majority(rng):
    rows, cols = _dims(rng)
    pool = [c for c in COLOURS if c != MARK]
    g, pl = _lattice(rng, rows, cols, pool=pool, fill=0.75)
    cnt = {}
    for _, _, t, _ in pl:
        cnt[t] = cnt.get(t, 0) + 1
    if not cnt:
        return None
    best = max(cnt.values())
    top = [t for t, n in cnt.items() if n == best]
    if len(top) != 1 or best < 2:
        return None
    return g


def tf_outline_majority(g):
    objs = _glyph_objs(g)
    cnt = _counts_by_type(objs)
    if not cnt:
        return None
    best = max(cnt.values())
    top = [t for t, n in cnt.items() if n == best]
    if len(top) != 1:
        return None
    h, w = dims(g)
    out = copy(g)
    drew = False
    for r0, c0, t, k, col in objs:
        if t != top[0]:
            continue
        r0c, c0c, r1c, c1c = max(0, r0 - 1), max(0, c0 - 1), min(h - 1, r0 + 3), min(w - 1, c0 + 3)
        rect(out, r0c, c0c, r1c, c1c, MARK, fill=False)
        drew = True
    return out if drew and out != g else None


rule("outline_majority_shape_glyphs", "Every glyph with the single most common shape gets a colour-9 outline box drawn around it.", gi_outline_majority, tf_outline_majority)


# 28 -------------------------------------------------------------------------
def gi_bar_extends(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, types=["bar", "dot", "ring", "t"], fill=0.7)
    if not any(t == "bar" for _, _, t, _ in pl):
        return None
    return g


def tf_bar_extends(g):
    h, w = dims(g)
    out = copy(g)
    changed = False
    for r0, c0, t, k, col in _glyph_objs(g):
        if t != "bar":
            continue
        for c in range(w):
            if out[r0 + 1][c] == 0:
                out[r0 + 1][c] = col
        changed = True
    return out if changed and out != g else None


rule("bar_glyphs_extend_full_width", "Every bar-shaped glyph's middle row extends into a full line across the grid's width.", gi_bar_extends, tf_bar_extends)


# 29 -------------------------------------------------------------------------
def gi_ring_to_grey(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, types=["ring", "plus", "x", "dot"], fill=0.75)
    if not any(t == "ring" for _, _, t, _ in pl):
        return None
    return g


def tf_ring_to_grey(g):
    out = copy(g)
    for r0, c0, t, k, col in _glyph_objs(g):
        if t == "ring":
            for dr, dc in GLYPHS[t]:
                out[r0 + dr][c0 + dc] = 5
    return out if out != g else None


rule("ring_glyphs_turn_grey", "Every ring-shaped glyph is recoloured to colour 5, regardless of its original colour.", gi_ring_to_grey, tf_ring_to_grey)


# 30 -------------------------------------------------------------------------
def gi_t_flip_vertical(rng):
    rows, cols = _dims(rng)
    pool = [c for c in COLOURS if c != MARK]
    g, pl = _lattice(rng, rows, cols, types=["t", "l", "diag"], pool=pool, fill=0.75)
    if not any(t == "t" for _, _, t, _ in pl):
        return None
    return g


def tf_t_flip_vertical(g):
    out = copy(g)
    for r0, c0, t, k, col in _glyph_objs(g):
        if t != "t":
            continue
        for dr, dc in GLYPHS[t]:
            out[r0 + dr][c0 + dc] = 0
        for dr, dc in GLYPHS[t]:
            out[r0 + (2 - dr)][c0 + dc] = col
    return out if out != g else None


rule("t_glyphs_flipped_vertically", "Every T-shaped glyph is flipped top-to-bottom in place.", gi_t_flip_vertical, tf_t_flip_vertical)


# 31 -------------------------------------------------------------------------
def gi_distinct_type_bar(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, fill=0.8)
    if len({t for _, _, t, _ in pl}) < 2:
        return None
    return g


def tf_distinct_type_bar(g):
    objs = _glyph_objs(g)
    n = len({t for _, _, t, _, _ in objs})
    if n < 1 or n > 9:
        return None
    row = [[3] * n + [0]]
    return row if n < 9 else [[3] * n]


rule("distinct_shape_count_bar", "Output a single bar whose length equals how many different glyph shapes appear in the grid.", gi_distinct_type_bar, tf_distinct_type_bar)


# 32 -------------------------------------------------------------------------
def gi_row_parity_recolour(rng):
    rows, cols = _dims(rng)
    rows = max(rows, 2)
    g, pl = _lattice(rng, rows, cols, fill=0.9)
    if len(pl) < 3:
        return None
    return g


def tf_row_parity_recolour(g):
    out = copy(g)
    for r0, c0, t, k, col in _glyph_objs(g):
        lattice_row = r0 // 4
        newcol = 4 if lattice_row % 2 == 0 else 6
        for dr, dc in _rotcells(GLYPHS[t], k):
            out[r0 + dr][c0 + dc] = newcol
    return out if out != g else None


rule("recolour_by_lattice_row_parity", "Every glyph is recoloured colour 4 if its lattice row is even, colour 6 if odd.", gi_row_parity_recolour, tf_row_parity_recolour)


# 33 -------------------------------------------------------------------------
def gi_col_parity_recolour(rng):
    rows, cols = _dims(rng)
    cols = max(cols, 2)
    g, pl = _lattice(rng, rows, cols, fill=0.9)
    if len(pl) < 3:
        return None
    return g


def tf_col_parity_recolour(g):
    out = copy(g)
    for r0, c0, t, k, col in _glyph_objs(g):
        lattice_col = c0 // 4
        newcol = 1 if lattice_col % 2 == 0 else 3
        for dr, dc in _rotcells(GLYPHS[t], k):
            out[r0 + dr][c0 + dc] = newcol
    return out if out != g else None


rule("recolour_by_lattice_col_parity", "Every glyph is recoloured colour 1 if its lattice column is even, colour 3 if odd.", gi_col_parity_recolour, tf_col_parity_recolour)


# 34 -------------------------------------------------------------------------
def gi_remove_least_common(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, fill=0.8)
    cnt = {}
    for _, _, t, _ in pl:
        cnt[t] = cnt.get(t, 0) + 1
    if len(cnt) < 2:
        return None
    least = min(cnt.values())
    if [n for n in cnt.values() if n == least].__len__() != 1:
        return None
    return g


def tf_remove_least_common(g):
    objs = _glyph_objs(g)
    cnt = _counts_by_type(objs)
    if len(cnt) < 2:
        return None
    least = min(cnt.values())
    bottom = [t for t, n in cnt.items() if n == least]
    if len(bottom) != 1:
        return None
    out = copy(g)
    for r0, c0, t, k, col in objs:
        if t == bottom[0]:
            for dr, dc in _rotcells(GLYPHS[t], k):
                out[r0 + dr][c0 + dc] = 0
    return out if out != g else None


rule("remove_rarest_shape_glyphs", "Every glyph whose shape is the single rarest one in the grid is erased.", gi_remove_least_common, tf_remove_least_common)


# 35 -------------------------------------------------------------------------
def gi_same_type_shares_colour(rng):
    rows, cols = _dims(rng)
    pool = [c for c in COLOURS if c != MARK]
    g, pl = _lattice(rng, rows, cols, pool=pool, fill=0.7)
    by_type = {}
    for _, _, t, c in pl:
        by_type.setdefault(t, []).append(c)
    if not any(len(set(cs)) > 1 for cs in by_type.values()):
        return None
    return g


def tf_same_type_shares_colour(g):
    objs = sorted(_glyph_objs(g), key=lambda o: (o[0], o[1]))
    first_colour = {}
    out = copy(g)
    changed = False
    for r0, c0, t, k, col in objs:
        if t not in first_colour:
            first_colour[t] = col
            continue
        want = first_colour[t]
        if want != col:
            for dr, dc in _rotcells(GLYPHS[t], k):
                out[r0 + dr][c0 + dc] = want
            changed = True
    return out if changed else None


rule("same_shape_glyphs_share_colour", "Every glyph takes on the colour of the first glyph of the same shape, in reading order.", gi_same_type_shares_colour, tf_same_type_shares_colour)


# 36 -------------------------------------------------------------------------
def gi_pair_vs_single_recolour(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, fill=0.85)
    cnt = {}
    for _, _, t, _ in pl:
        cnt[t] = cnt.get(t, 0) + 1
    if not any(n == 2 for n in cnt.values()) or not any(n != 2 for n in cnt.values()):
        return None
    return g


def tf_pair_vs_single_recolour(g):
    objs = _glyph_objs(g)
    cnt = _counts_by_type(objs)
    out = copy(g)
    for r0, c0, t, k, col in objs:
        newcol = 2 if cnt[t] == 2 else 8
        for dr, dc in _rotcells(GLYPHS[t], k):
            out[r0 + dr][c0 + dc] = newcol
    return out if out != g else None


rule("recolour_shapes_occurring_exactly_twice", "Any glyph shape occurring exactly twice is recoloured 2; every other shape is recoloured 8.", gi_pair_vs_single_recolour, tf_pair_vs_single_recolour)


# 37 -------------------------------------------------------------------------
def gi_crop_largest_area_type(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, fill=0.8)
    if len({t for _, _, t, _ in pl}) < 2:
        return None
    return g


def tf_crop_largest_area_type(g):
    objs = _glyph_objs(g)
    area = {"plus": 5, "x": 5, "l": 5, "t": 5, "ring": 8, "diag": 3, "dot": 1, "bar": 3}
    total = {}
    for r0, c0, t, k, col in objs:
        total[t] = total.get(t, 0) + area[t]
    if not total:
        return None
    best = max(total, key=lambda t: total[t])
    inst = [o for o in objs if o[2] == best]
    r0 = min(o[0] for o in inst); c0 = min(o[1] for o in inst)
    r1 = max(o[0] + 2 for o in inst); c1 = max(o[1] + 2 for o in inst)
    if r0 == 0 and c0 == 0 and r1 == len(g) - 1 and c1 == len(g[0]) - 1:
        return None
    return crop(g, r0, c0, r1, c1)


rule("crop_box_around_largest_total_area_shape", "Output the smallest box containing every glyph whose shape covers the most total pixels in the grid.", gi_crop_largest_area_type, tf_crop_largest_area_type)


# 38 -------------------------------------------------------------------------
def gi_edge_glyphs_marked(rng):
    rows, cols = _dims(rng)
    rows = max(rows, 3); cols = max(cols, 3)
    pool = [c for c in COLOURS if c != MARK]
    g, pl = _lattice(rng, rows, cols, pool=pool, fill=0.8)
    if len(pl) < 3:
        return None
    return g


def tf_edge_glyphs_marked(g):
    h, w = dims(g)
    nrows = (h + 1) // 4; ncols = (w + 1) // 4
    out = copy(g)
    changed = False
    for r0, c0, t, k, col in _glyph_objs(g):
        lr, lc = r0 // 4, c0 // 4
        if lr == 0 or lc == 0 or lr == nrows - 1 or lc == ncols - 1:
            for dr, dc in _rotcells(GLYPHS[t], k):
                out[r0 + dr][c0 + dc] = MARK
            changed = True
    return out if changed and out != g else None


rule("recolour_border_lattice_glyphs", "Every glyph sitting in the outermost lattice row or column is recoloured to colour 9.", gi_edge_glyphs_marked, tf_edge_glyphs_marked)


# 39 -------------------------------------------------------------------------
def gi_duplicate_unique_right(rng):
    rows, cols = _dims(rng)
    cols = max(cols, 4)
    g, pl = _lattice(rng, rows, cols, fill=0.6)
    cnt = {}
    for _, _, t, _ in pl:
        cnt[t] = cnt.get(t, 0) + 1
    uniq = [t for t, n in cnt.items() if n == 1]
    if len(uniq) != 1:
        return None
    r0, c0, t, col = next(p for p in pl if p[2] == uniq[0])
    h, w = dims(g)
    if c0 + 4 + 2 >= w or any(g[r0 + dr][c0 + 4 + dc] != 0 for dr in range(3) for dc in range(3)):
        return None
    return g


def tf_duplicate_unique_right(g):
    objs = _glyph_objs(g)
    cnt = _counts_by_type(objs)
    uniq = [t for t, n in cnt.items() if n == 1]
    if len(uniq) != 1:
        return None
    r0, c0, t, k, col = next(o for o in objs if o[2] == uniq[0])
    h, w = dims(g)
    if c0 + 4 + 2 >= w:
        return None
    out = copy(g)
    _stamp_oriented(out, r0, c0 + 4, t, k, col)
    return out if out != g else None


rule("duplicate_lone_shape_glyph_rightward", "The one glyph whose shape appears nowhere else gets a copy of itself stamped one lattice step to its right.", gi_duplicate_unique_right, tf_duplicate_unique_right)


# 40 -------------------------------------------------------------------------
def gi_total_count_bar(rng):
    rows, cols = _dims(rng)
    g, pl = _lattice(rng, rows, cols, fill=0.75)
    if len(pl) < 2 or len(pl) > 9:
        return None
    return g


def tf_total_count_bar(g):
    objs = _glyph_objs(g)
    n = len(objs)
    if n < 1 or n > 9:
        return None
    row = [[6] * n + [0, 0]]
    return row


rule("total_glyph_count_bar", "Output a single bar whose length equals the total number of glyphs anywhere in the grid.", gi_total_count_bar, tf_total_count_bar)
