# b035_overlays.py -- LAYER COMBINATION WITH A KEY: two or three panels, joined side by side (or stacked)
# by a reserved separator colour that never appears in panel content, are combined cell by cell. Row 0 (or,
# for _vstack rules, column 0) is a legend that may hold a small key table (colour A over colour B -> C),
# a priority order, a tie-break colour, a transparency marker, or a mode selector; many rules leave it blank
# (all 0). Content colours never equal the separator colour, so panel boundaries always parse unambiguously.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


# ================================================================ shared scaffold
def _dims(rng, k, lo=5, hi=12, p_big=0.32):
    """Panel (ph, pw) such that the assembled grid is 21-30 a side about p_big of the time."""
    if rng.random() < p_big:
        H, W = rng.randint(21, 30), rng.randint(21, 30)
    else:
        H, W = rng.randint(lo + 2, hi + 2), rng.randint(lo + 2, hi + 2)
    ph = max(3, H - 2)
    pw = max(2, (W - (k - 1)) // k)
    return ph, pw


def _sep(rng, exclude=()):
    return rng.choice([c for c in COLOURS if c not in exclude])


def _panel(rng, ph, pw, cols, density=0.4):
    return [[rng.choice(cols) if rng.random() < density else 0 for _ in range(pw)] for _ in range(ph)]


def _join_h(panels, sep):
    h = len(panels[0])
    out = []
    for r in range(h):
        row = []
        for i, p in enumerate(panels):
            if i:
                row.append(sep)
            row += p[r]
        out.append(row)
    return out


def _assemble(legend, sep, panels):
    body = _join_h(panels, sep)
    W = len(body[0])
    leg = (list(legend) + [0] * W)[:W]
    return [leg, [sep] * W] + body


def _parse(g):
    """-> (legend_row, sep, [panels]) for the row-0/row-1/body layout."""
    legend = g[0]; sep = g[1][0]
    body = g[2:]
    w = len(body[0]); h = len(body)
    sepcols = [c for c in range(w) if all(body[r][c] == sep for r in range(h))]
    panels, start = [], 0
    for c in sepcols + [w]:
        if c > start:
            panels.append([row[start:c] for row in body])
        start = c + 1
    return legend, sep, panels


def _assemble_v(legend, sep, panels):
    return transpose(_assemble(legend, sep, [transpose(p) for p in panels]))


def _parse_v(g):
    legend, sep, panelsT = _parse(transpose(g))
    return legend, sep, [transpose(p) for p in panelsT]


def _build(rng, k, cols_n=3, density=0.4, legend_fn=None, lo=5, hi=12, p_big=0.32, vstack=False):
    ph, pw = _dims(rng, k, lo, hi, p_big)
    sep = _sep(rng, (0,))
    cols = colours(rng, cols_n, exclude=(sep,))
    panels = [_panel(rng, ph, pw, cols, density) for _ in range(k)]
    W = k * pw + (k - 1)
    legend = legend_fn(rng, cols, sep, W) if legend_fn else [0] * W
    return (_assemble_v if vstack else _assemble)(legend, sep, panels), cols, sep, panels


def _mk(rng, k, cols_n=3, density=0.4, legend_fn=None, lo=5, hi=12, p_big=0.32, vstack=False):
    r = _build(rng, k, cols_n, density, legend_fn, lo, hi, p_big, vstack)
    return None if r is None else r[0]


def _getp(g, vstack=False):
    return (_parse_v if vstack else _parse)(g)


def _legend_pairs(rng, cols, sep, W, n_lo=2, n_hi=4):
    n = min(rng.randint(n_lo, n_hi), max(1, W // 3))
    out, seen = [], set()
    tries = 0
    while len(out) < n * 3 and tries < 60:
        tries += 1
        if len(cols) < 2:
            break
        a, b = rng.sample(cols, 2)
        if (a, b) in seen:
            continue
        seen.add((a, b))
        c = rng.choice([x for x in COLOURS if x != sep])
        out += [a, b, c]
    return out


def _parse_pairs(legend):
    d = {}
    for i in range(0, len(legend) - 2, 3):
        a, b, c = legend[i], legend[i + 1], legend[i + 2]
        if a == 0 and b == 0:
            break
        if a and b:
            d[(a, b)] = c
    return d


def _combine2(a, b, table):
    if a and b:
        return table.get((a, b), table.get((b, a), 0))
    return a or b


def _nz_count(output_colours):
    return len(set(v for row in output_colours for v in row))


# ================================================================ A: pairwise key table, 2 panels
def gi_pair(rng):
    return _mk(rng, 2, 3, 0.4, _legend_pairs)
def tf_pair(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 2:
        return None
    table = _parse_pairs(legend)
    if not table:
        return None
    a, b = ps
    h, w = dims(a)
    return [[_combine2(a[r][c], b[r][c], table) for c in range(w)] for r in range(h)]
rule("key_table_overlay_pair", "Two panels overlap; where both are coloured a key table in the top row gives the result, otherwise the coloured one shows through.", gi_pair, tf_pair)


def gi_pair_and(rng):
    return _mk(rng, 2, 3, 0.45, _legend_pairs)
def tf_pair_and(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 2:
        return None
    table = _parse_pairs(legend)
    if not table:
        return None
    a, b = ps; h, w = dims(a)
    out = [[table.get((a[r][c], b[r][c]), table.get((b[r][c], a[r][c]), 0)) if a[r][c] and b[r][c] else 0
            for c in range(w)] for r in range(h)]
    return out if _nz_count(out) > 1 else None
rule("key_table_overlay_and_only", "Only where both panels are coloured does a key table in the top row give the result colour; every other cell is empty.", gi_pair_and, tf_pair_and)


def gi_pair_v(rng):
    return _mk(rng, 2, 3, 0.4, _legend_pairs, vstack=True)
def tf_pair_v(g):
    legend, sep, ps = _getp(g, vstack=True)
    if len(ps) != 2:
        return None
    table = _parse_pairs(legend)
    if not table:
        return None
    a, b = ps; h, w = dims(a)
    return [[_combine2(a[r][c], b[r][c], table) for c in range(w)] for r in range(h)]
rule("key_table_overlay_vstack", "Two panels are stacked top and bottom; a key table in the left column gives the result where both are coloured, else the coloured one shows through.", gi_pair_v, tf_pair_v)


def gi_pair_chain(rng):
    return _mk(rng, 3, 3, 0.35, _legend_pairs)
def tf_pair_chain(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 3:
        return None
    table = _parse_pairs(legend)
    if not table:
        return None
    a, b, c = ps; h, w = dims(a)
    mid = [[_combine2(a[r][x], b[r][x], table) for x in range(w)] for r in range(h)]
    return [[_combine2(mid[r][x], c[r][x], table) for x in range(w)] for r in range(h)]
rule("key_table_chain_three_panels", "Three panels are merged left to right with the same key table, each merge step feeding into the next.", gi_pair_chain, tf_pair_chain)


def gi_pair_fallback(rng):
    def lf(rng, cols, sep, W):
        base = _legend_pairs(rng, cols, sep, W, 1, 2)
        order = rng.sample(cols, len(cols))
        return base + order
    return _mk(rng, 2, 3, 0.4, lf)
def tf_pair_fallback(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 2:
        return None
    table = _parse_pairs(legend)
    tail = [v for v in legend if v]
    order = tail[len(table) * 3:] if table else tail
    rank = {col: i for i, col in enumerate(order)}
    a, b = ps; h, w = dims(a)
    out = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            x, y = a[r][c], b[r][c]
            if x and y:
                out[r][c] = table.get((x, y), table.get((y, x), min((x, y), key=lambda v: rank.get(v, 9))))
            else:
                out[r][c] = x or y
    return out
rule("key_table_overlay_priority_fallback", "Two panels overlap; the key table resolves listed colour pairs and a priority order (also in the top row) decides any pair the table does not list.", gi_pair_fallback, tf_pair_fallback)


def gi_pair_crop(rng):
    return _mk(rng, 2, 4, 0.3, _legend_pairs, lo=8, hi=16)
def tf_pair_crop(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 2:
        return None
    table = _parse_pairs(legend)
    if not table:
        return None
    a, b = ps; h, w = dims(a)
    merged = [[_combine2(a[r][c], b[r][c], table) for c in range(w)] for r in range(h)]
    nz = cells(merged, lambda v: v != 0)
    if not nz:
        return None
    return crop(merged, *bbox(nz))
rule("key_table_overlay_cropped", "Two panels overlap and merge by the key table in the top row, then the result is cropped to its own bounding box.", gi_pair_crop, tf_pair_crop)


# ================================================================ B: priority / majority / blend
def _legend_order(rng, cols, sep, W):
    return rng.sample(cols, len(cols))


def gi_priority(rng):
    return _mk(rng, 3, 3, 0.3, _legend_order)
def tf_priority(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 3:
        return None
    order = [v for v in legend if v]
    rank = {col: i for i, col in enumerate(order)}
    h, w = dims(ps[0])
    out = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            nz = [p[r][c] for p in ps if p[r][c]]
            if nz:
                out[r][c] = min(nz, key=lambda v: rank.get(v, 99))
    return out
rule("priority_legend_stack_three", "Three panels are stacked; at each cell the coloured panel with the highest priority (the order listed in the top row) wins.", gi_priority, tf_priority)


def gi_majority(rng):
    def lf(rng, cols, sep, W):
        return [rng.choice([c for c in COLOURS if c != sep])]
    return _mk(rng, 3, 3, 0.45, lf)
def tf_majority(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 3:
        return None
    tie = legend[0] or 5
    h, w = dims(ps[0])
    out = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            vals = [p[r][c] for p in ps]
            cnt = {}
            for v in vals:
                cnt[v] = cnt.get(v, 0) + 1
            best = max(cnt.values())
            winners = [v for v, n in cnt.items() if n == best]
            out[r][c] = winners[0] if best >= 2 and len(winners) == 1 else (tie if best == 1 else 0)
    return out if _nz_count(out) > 1 else None
rule("majority_vote_three_tie_key", "Three panels vote on each cell's colour; a clean majority wins, and a three-way tie is coloured with the tie colour from the top row.", gi_majority, tf_majority)


def gi_blend(rng):
    def lf(rng, cols, sep, W):
        return [rng.choice([c for c in COLOURS if c != sep])]
    return _mk(rng, 4, 3, 0.4, lf, lo=4, hi=10)
def tf_blend(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 4:
        return None
    tie = legend[0] or 5
    h, w = dims(ps[0])
    out = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            vals = [p[r][c] for p in ps]
            cnt = {}
            for v in vals:
                cnt[v] = cnt.get(v, 0) + 1
            best = max(cnt.values())
            winners = sorted(v for v, n in cnt.items() if n == best)
            out[r][c] = winners[0] if len(winners) == 1 and winners[0] != 0 else (tie if winners[0] != 0 or len(winners) > 1 else 0)
    return out if _nz_count(out) > 1 else None
rule("blend_most_common_four_tie_key", "Four panels are blended; each cell takes the colour that appears in the most panels, and a tie is coloured with the key colour from the top row.", gi_blend, tf_blend)


def gi_unanimous(rng):
    def lf(rng, cols, sep, W):
        return [rng.choice([c for c in COLOURS if c != sep])]
    return _mk(rng, 3, 2, 0.5, lf)
def tf_unanimous(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 3:
        return None
    key = legend[0] or 5
    h, w = dims(ps[0])
    out = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            vals = {p[r][c] for p in ps}
            out[r][c] = vals.pop() if len(vals) == 1 and next(iter([list(vals)] if vals else [0])) != 0 else key
    # recompute cleanly (the line above is awkward with a popped set); do it straight:
    out = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            vals = {p[r][c] for p in ps}
            out[r][c] = (list(vals)[0] if len(vals) == 1 else key)
    return out if _nz_count(out) > 1 else None
rule("unanimous_else_key_three", "Three panels must all agree on a cell's colour for it to survive; any disagreement is painted with the key colour from the top row.", gi_unanimous, tf_unanimous)


# ================================================================ C: difference / overlap counting
def gi_diff(rng):
    def lf(rng, cols, sep, W):
        return rng.sample([c for c in COLOURS if c != sep], 3)
    return _mk(rng, 2, 3, 0.4, lf)
def tf_diff(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 2:
        return None
    only_a, only_b, both = legend[0], legend[1], legend[2]
    a, b = ps; h, w = dims(a)
    out = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            if a[r][c] and b[r][c]:
                out[r][c] = both
            elif a[r][c]:
                out[r][c] = only_a
            elif b[r][c]:
                out[r][c] = only_b
    return out if _nz_count(out) > 1 else None
rule("difference_image_two_panel_key", "Two panels are compared; cells coloured in only the first, only the second, or both are repainted with the three colours listed in the top row, in that order.", gi_diff, tf_diff)


def gi_bucket(rng):
    def lf(rng, cols, sep, W):
        return rng.sample([c for c in COLOURS if c != sep], 3)
    return _mk(rng, 3, 2, 0.45, lf, lo=6, hi=12)
def tf_bucket(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 3:
        return None
    one, two, three = legend[0], legend[1], legend[2]
    h, w = dims(ps[0])
    out = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            n = sum(1 for p in ps if p[r][c])
            out[r][c] = {1: one, 2: two, 3: three}.get(n, 0)
    if len({v for row in out for v in row if v}) < 2:
        return None
    return out
rule("overlap_count_bucket_colour", "Three panels overlap; a cell covered by exactly one, two or all three panels is repainted with the matching colour from the top row.", gi_bucket, tf_bucket)


def gi_count_digit(rng):
    return _mk(rng, 3, 3, 0.4, None, lo=6, hi=12)
def tf_count_digit(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 3:
        return None
    h, w = dims(ps[0])
    out = [[sum(1 for p in ps if p[r][c]) for c in range(w)] for r in range(h)]
    return out if _nz_count(out) > 1 else None
rule("count_panels_per_cell_digit", "Three panels overlap; each output cell becomes the DIGIT count of how many of the three panels colour that cell.", gi_count_digit, tf_count_digit, digits=True)


def gi_count_match_digit(rng):
    def lf(rng, cols, sep, W):
        return [rng.choice(cols)]
    return _mk(rng, 4, 3, 0.4, lf, lo=5, hi=10)
def tf_count_match_digit(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 4:
        return None
    target = legend[0]
    if not target:
        return None
    h, w = dims(ps[0])
    out = [[sum(1 for p in ps if p[r][c] == target) for c in range(w)] for r in range(h)]
    return out if _nz_count(out) > 1 else None
rule("count_cells_matching_key_colour_digit", "Four panels overlap; each output cell becomes the DIGIT count of how many panels show the key colour from the top row at that cell.", gi_count_match_digit, tf_count_match_digit, digits=True)


# ================================================================ D: mask / alpha / transparency
def gi_mask(rng):
    def lf(rng, cols, sep, W):
        a, b = rng.sample(cols, 2)
        return [a, b]
    return _mk(rng, 3, 3, 0.4, lf, lo=6, hi=12)
def tf_mask(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 3:
        return None
    ca, cb = legend[0], legend[1]
    m, a, b = ps; h, w = dims(a)
    out = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            out[r][c] = a[r][c] if m[r][c] == ca else (b[r][c] if m[r][c] == cb else 0)
    return out if _nz_count(out) > 1 else None
rule("mask_panel_two_colour_select", "A mask panel marks each cell with one of two colours from the top row; those cells take their colour from the first content panel or the second accordingly.", gi_mask, tf_mask)


def gi_alpha_swap(rng):
    def lf(rng, cols, sep, W):
        return []
    excl_grey = lambda cols: 5 not in cols
    for _ in range(1):
        pass
    def mk(rng):
        cols3 = colours(rng, 2, exclude=(5,))
        ph, pw = _dims(rng, 3, 5, 12)
        sep = _sep(rng, (0, 5))
        marker = _panel(rng, ph, pw, [5], 0.3)
        a = _panel(rng, ph, pw, cols3, 0.4)
        b = _panel(rng, ph, pw, cols3, 0.4)
        return _assemble([0] * (3 * pw + 2), sep, [marker, a, b])
    return mk(rng)
def tf_alpha_swap(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 3:
        return None
    m, a, b = ps; h, w = dims(a)
    out = [[b[r][c] if m[r][c] == 5 else a[r][c] for c in range(w)] for r in range(h)]
    return out if _nz_count(out) > 1 else None
rule("alpha_marker_swap_two_panel", "A grey marker panel shows where to swap: those cells take the second content panel's colour instead of the first's.", gi_alpha_swap, tf_alpha_swap)


def gi_window(rng):
    def lf(rng, cols, sep, W):
        return [rng.choice(cols)]
    return _mk(rng, 2, 3, 0.5, lf)
def tf_window(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 2:
        return None
    window = legend[0]
    if not window:
        return None
    a, b = ps; h, w = dims(a)
    out = [[b[r][c] if a[r][c] == window else (a[r][c] or b[r][c]) for c in range(w)] for r in range(h)]
    return out if _nz_count(out) > 1 else None
rule("window_colour_transparency_two_panel", "The upper panel sits over the lower one, but wherever it shows the key colour from the top row it is transparent there and the lower panel shows through.", gi_window, tf_window)


def gi_mask_binary(rng):
    return _mk(rng, 3, 3, 0.4, None, lo=6, hi=12)
def tf_mask_binary(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 3:
        return None
    m, a, b = ps; h, w = dims(a)
    out = [[b[r][c] if m[r][c] else a[r][c] for c in range(w)] for r in range(h)]
    return out if _nz_count(out) > 1 else None
rule("mask_binary_select_two_panel", "A mask panel is blank or coloured; blank cells take the first content panel's colour and coloured cells take the second's.", gi_mask_binary, tf_mask_binary)


# ================================================================ E: transform-then-merge
def gi_mirror_h(rng):
    return _mk(rng, 2, 3, 0.4, None, lo=6, hi=12)
def tf_mirror_h(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 2:
        return None
    a, b = ps; b = flip_h(b); h, w = dims(a)
    out = [[a[r][c] or b[r][c] for c in range(w)] for r in range(h)]
    return out if out != a and _nz_count(out) > 1 else None
rule("overlay_mirror_h_then_merge", "The second panel is flipped left to right, then laid over the first wherever the first is empty.", gi_mirror_h, tf_mirror_h)


def gi_mirror_v(rng):
    return _mk(rng, 2, 3, 0.4, None, lo=6, hi=12)
def tf_mirror_v(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 2:
        return None
    a, b = ps; b = flip_v(b); h, w = dims(a)
    out = [[a[r][c] or b[r][c] for c in range(w)] for r in range(h)]
    return out if out != a and _nz_count(out) > 1 else None
rule("overlay_mirror_v_then_merge", "The second panel is flipped top to bottom, then laid over the first wherever the first is empty.", gi_mirror_v, tf_mirror_v)


def gi_rot180(rng):
    return _mk(rng, 2, 3, 0.4, None, lo=6, hi=12)
def tf_rot180(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 2:
        return None
    a, b = ps; b = rot90(rot90(b)); h, w = dims(a)
    out = [[a[r][c] or b[r][c] for c in range(w)] for r in range(h)]
    return out if out != a and _nz_count(out) > 1 else None
rule("overlay_rotate180_then_merge", "The second panel is rotated a half turn, then laid over the first wherever the first is empty.", gi_rot180, tf_rot180)


def gi_offset(rng):
    def lf(rng, cols, sep, W):
        return [rng.randint(0, 9), rng.randint(0, 9)]
    return _mk(rng, 2, 3, 0.4, lf, lo=8, hi=14)
def tf_offset(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 2:
        return None
    a, b = ps; h, w = dims(a)
    dr, dc = legend[0] - 5, legend[1] - 5
    out = copy(a)
    for r in range(h):
        for c in range(w):
            if b[r][c] and 0 <= r + dr < h and 0 <= c + dc < w and out[r + dr][c + dc] == 0:
                out[r + dr][c + dc] = b[r][c]
    return out if out != a and _nz_count(out) > 1 else None
rule("overlay_vector_offset_then_merge", "The second panel is shifted by a vector read off the top row (two cell values, offset from 5), then laid over the first wherever the first is empty.", gi_offset, tf_offset)


# ================================================================ F: post-process
def gi_outline(rng):
    def lf(rng, cols, sep, W):
        return [rng.choice([c for c in COLOURS if c != sep])]
    return _mk(rng, 2, 3, 0.3, lf, lo=8, hi=14)
def tf_outline(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 2:
        return None
    outline = legend[0] or 5
    a, b = ps; h, w = dims(a)
    out = [[a[r][c] or b[r][c] for c in range(w)] for r in range(h)]
    nz = cells(out, lambda v: v != 0)
    if not nz:
        return None
    border = set()
    for r, c in nz:
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if not (0 <= nr < h and 0 <= nc < w) or out[nr][nc] == 0:
                border.add((r, c))
    for r, c in border:
        out[r][c] = outline
    return out if _nz_count(out) > 1 else None
rule("overlay_then_outline_key", "Two panels merge wherever either is coloured, then every cell on the outer edge of the merged shape is repainted with the key colour from the top row.", gi_outline, tf_outline)


def gi_fillholes(rng):
    def lf(rng, cols, sep, W):
        return [rng.choice([c for c in COLOURS if c != sep])]
    return _mk(rng, 2, 3, 0.45, lf, lo=8, hi=14)
def tf_fillholes(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 2:
        return None
    fill = legend[0] or 5
    a, b = ps; h, w = dims(a)
    out = [[a[r][c] or b[r][c] for c in range(w)] for r in range(h)]
    seen = set()
    for r in range(h):
        for c in (0, w - 1):
            if out[r][c] == 0 and (r, c) not in seen:
                st = [(r, c)]; seen.add((r, c))
                while st:
                    y, x = st.pop()
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and out[ny][nx] == 0 and (ny, nx) not in seen:
                            seen.add((ny, nx)); st.append((ny, nx))
    for c in range(w):
        for r in (0, h - 1):
            if out[r][c] == 0 and (r, c) not in seen:
                st = [(r, c)]; seen.add((r, c))
                while st:
                    y, x = st.pop()
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and out[ny][nx] == 0 and (ny, nx) not in seen:
                            seen.add((ny, nx)); st.append((ny, nx))
    changed = False
    for r in range(h):
        for c in range(w):
            if out[r][c] == 0 and (r, c) not in seen:
                out[r][c] = fill; changed = True
    return out if changed and _nz_count(out) > 1 else None
rule("overlay_then_fill_holes_key", "Two panels merge wherever either is coloured, then any empty pocket fully enclosed by the merged shape is filled with the key colour from the top row.", gi_fillholes, tf_fillholes)


# ================================================================ G: how many panels, from a bar
def _bar_build(rng, kmax=4):
    ph, pw = _dims(rng, kmax, 5, 10)
    sep = _sep(rng, (0,))
    barcol = _sep(rng, (0, sep))
    cols = colours(rng, 3, exclude=(sep, barcol))
    k = rng.randint(1, kmax)
    panels = [_panel(rng, ph, pw, cols, 0.4) for _ in range(kmax)]
    W = kmax * pw + (kmax - 1)
    legend = [barcol] * k + [0] * (W - k)
    return _assemble(legend, sep, panels), k


def gi_bar_union(rng):
    r = _bar_build(rng)
    return None if r is None else r[0]
def tf_bar_union(g):
    legend, sep, ps = _getp(g)
    k = sum(1 for v in legend if v)
    if k < 1 or k > len(ps):
        return None
    use = ps[:k]
    h, w = dims(use[0])
    out = [[0] * w for _ in range(h)]
    for p in use:
        for r in range(h):
            for c in range(w):
                if p[r][c]:
                    out[r][c] = p[r][c]
    return out if _nz_count(out) > 1 else None
rule("stack_k_from_bar_union", "A bar in the top row gives a count k; only the first k of the panels are stacked, later ones painted over earlier.", gi_bar_union, tf_bar_union)


def gi_bar_majority(rng):
    r = _bar_build(rng)
    return None if r is None else r[0]
def tf_bar_majority(g):
    legend, sep, ps = _getp(g)
    k = sum(1 for v in legend if v)
    if k < 1 or k > len(ps):
        return None
    use = ps[:k]
    h, w = dims(use[0])
    out = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            vals = [p[r][c] for p in use]
            cnt = {}
            for v in vals:
                cnt[v] = cnt.get(v, 0) + 1
            best = max(cnt.values())
            winners = [v for v, n in cnt.items() if n == best]
            out[r][c] = winners[0] if len(winners) == 1 else 0
    return out if _nz_count(out) > 1 else None
rule("stack_k_from_bar_majority", "A bar in the top row gives a count k; only the first k panels take a per-cell majority vote, ties left empty.", gi_bar_majority, tf_bar_majority)


# ================================================================ H: AND/OR/XOR with a single key colour
def gi_and_key(rng):
    def lf(rng, cols, sep, W):
        return [rng.choice([c for c in COLOURS if c != sep])]
    return _mk(rng, 2, 3, 0.45, lf)
def tf_and_key(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 2:
        return None
    key = legend[0] or 5
    a, b = ps; h, w = dims(a)
    out = [[key if a[r][c] and b[r][c] else 0 for c in range(w)] for r in range(h)]
    return out if _nz_count(out) > 1 else None
rule("and_with_key_colour_two_panel", "Two panels overlap; every cell coloured in both becomes the single key colour from the top row, regardless of which colours they were.", gi_and_key, tf_and_key)


def gi_xor_key(rng):
    def lf(rng, cols, sep, W):
        return rng.sample([c for c in COLOURS if c != sep], 2)
    return _mk(rng, 2, 3, 0.4, lf)
def tf_xor_key(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 2:
        return None
    ka, kb = legend[0], legend[1]
    a, b = ps; h, w = dims(a)
    out = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            if a[r][c] and not b[r][c]:
                out[r][c] = ka
            elif b[r][c] and not a[r][c]:
                out[r][c] = kb
    return out if _nz_count(out) > 1 else None
rule("xor_per_source_key_colour", "Two panels overlap; a cell coloured in only the first becomes the top row's first key colour, a cell coloured in only the second becomes its second.", gi_xor_key, tf_xor_key)


def gi_or_parity(rng):
    def lf(rng, cols, sep, W):
        return rng.sample([c for c in COLOURS if c != sep], 2)
    return _mk(rng, 3, 2, 0.4, lf, lo=6, hi=12)
def tf_or_parity(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 3:
        return None
    odd_c, even_c = legend[0], legend[1]
    h, w = dims(ps[0])
    out = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            n = sum(1 for p in ps if p[r][c])
            if n:
                out[r][c] = odd_c if n % 2 else even_c
    return out if _nz_count(out) > 1 else None
rule("or_parity_key_colour_three", "Three panels overlap; every covered cell is repainted using the top row's first key colour if an odd number of panels cover it, the second if an even number do.", gi_or_parity, tf_or_parity)


# ================================================================ I: key-table merge then a second step
def gi_pair_upscale(rng):
    return _mk(rng, 2, 3, 0.35, _legend_pairs, lo=4, hi=8)
def tf_pair_upscale(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 2:
        return None
    table = _parse_pairs(legend)
    if not table:
        return None
    a, b = ps; h, w = dims(a)
    merged = [[_combine2(a[r][c], b[r][c], table) for c in range(w)] for r in range(h)]
    if 2 * h > 30 or 2 * w > 30:
        return None
    out = []
    for row in merged:
        wide = [v for v in row for _ in (0, 1)]
        out += [wide, wide[:]]
    return out if _nz_count(out) > 1 else None
rule("key_table_overlay_upscale2x", "Two panels merge by the key table in the top row, then the merged result is enlarged two times.", gi_pair_upscale, tf_pair_upscale)


def gi_pair_crop_highlight(rng):
    def lf(rng, cols, sep, W):
        base = _legend_pairs(rng, cols, sep, W, 2, 3)
        hi = rng.choice([v for v in base[2::3]] or [rng.choice(cols)])
        return base + [hi]
    return _mk(rng, 2, 3, 0.4, lf, lo=8, hi=16)
def tf_pair_crop_highlight(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 2:
        return None
    table = _parse_pairs(legend)
    if not table:
        return None
    hi = legend[len(table) * 3] if len(legend) > len(table) * 3 else None
    a, b = ps; h, w = dims(a)
    merged = [[_combine2(a[r][c], b[r][c], table) for c in range(w)] for r in range(h)]
    target = hi if hi in {v for row in merged for v in row} else next((v for row in merged for v in row if v), None)
    if target is None:
        return None
    nz = cells(merged, lambda v: v == target)
    if not nz:
        return None
    return crop(merged, *bbox(nz))
rule("key_table_overlay_crop_to_highlight", "Two panels merge by the key table in the top row, then the result is cropped to the area of the highlight colour the key table also names.", gi_pair_crop_highlight, tf_pair_crop_highlight)


# ================================================================ J/K: priority-by-position and more
def gi_back_front(rng):
    return _mk(rng, 3, 3, 0.35, None, lo=6, hi=14)
def tf_back_front(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 3:
        return None
    a, b, c = ps; h, w = dims(a)
    out = [[c[r][x] or b[r][x] or a[r][x] for x in range(w)] for r in range(h)]
    return out if out != a and _nz_count(out) > 1 else None
rule("overlay_three_panels_back_to_front", "Three panels are stacked; at each cell the last panel's colour wins if it has one, else the middle, else the first.", gi_back_front, tf_back_front)


def gi_front_back(rng):
    return _mk(rng, 3, 3, 0.35, None, lo=6, hi=14)
def tf_front_back(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 3:
        return None
    a, b, c = ps; h, w = dims(a)
    out = [[a[r][x] or b[r][x] or c[r][x] for x in range(w)] for r in range(h)]
    return out if out != a and _nz_count(out) > 1 else None
rule("overlay_three_panels_front_to_back", "Three panels are stacked; at each cell the first panel's colour wins if it has one, else the middle, else the last.", gi_front_back, tf_front_back)


def gi_conflict(rng):
    def lf(rng, cols, sep, W):
        return [rng.choice([c for c in COLOURS if c != sep])]
    return _mk(rng, 2, 3, 0.45, lf)
def tf_conflict(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 2:
        return None
    key = legend[0] or 5
    a, b = ps; h, w = dims(a)
    out = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            x, y = a[r][c], b[r][c]
            out[r][c] = key if (x and y and x != y) else (x or y)
    return out if _nz_count(out) > 1 else None
rule("conflict_highlight_two_panel", "Two panels overlap; where they disagree on colour the cell is repainted with the key colour from the top row, otherwise the coloured one shows through.", gi_conflict, tf_conflict)


def gi_pair_chain_v(rng):
    return _mk(rng, 3, 3, 0.35, _legend_pairs, vstack=True)
def tf_pair_chain_v(g):
    legend, sep, ps = _getp(g, vstack=True)
    if len(ps) != 3:
        return None
    table = _parse_pairs(legend)
    if not table:
        return None
    a, b, c = ps; h, w = dims(a)
    mid = [[_combine2(a[r][x], b[r][x], table) for x in range(w)] for r in range(h)]
    return [[_combine2(mid[r][x], c[r][x], table) for x in range(w)] for r in range(h)]
rule("key_table_chain_three_vstack", "Three panels are stacked top to bottom and merged in order with the same key table, in the left column, feeding each step into the next.", gi_pair_chain_v, tf_pair_chain_v)


def gi_mask_stray(rng):
    def lf(rng, cols, sep, W):
        a, b = rng.sample([c for c in COLOURS if c != sep], 2)
        return [a, b]
    return _mk(rng, 3, 3, 0.4, lf, lo=6, hi=12)
def tf_mask_stray(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 3:
        return None
    active, fallback = legend[0], legend[1]
    m, a, b = ps; h, w = dims(a)
    out = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            mv = m[r][c]
            if mv == 0:
                out[r][c] = a[r][c]
            elif mv == active:
                out[r][c] = b[r][c]
            else:
                out[r][c] = fallback
    return out if _nz_count(out) > 1 else None
rule("mask_select_with_stray_fallback", "A mask panel is blank, the active colour from the top row, or something else entirely; those three cases pick the first content panel, the second, or the fallback colour from the top row.", gi_mask_stray, tf_mask_stray)


def gi_exactly_two(rng):
    def lf(rng, cols, sep, W):
        return [rng.choice([c for c in COLOURS if c != sep])]
    return _mk(rng, 3, 3, 0.4, lf, lo=6, hi=12)
def tf_exactly_two(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 3:
        return None
    key = legend[0] or 5
    h, w = dims(ps[0])
    out = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            nz = [p[r][c] for p in ps if p[r][c]]
            out[r][c] = key if len(nz) == 2 else (nz[0] if nz else 0)
    return out if _nz_count(out) > 1 else None
rule("highlight_exactly_two_of_three", "Three panels overlap; a cell covered by exactly two of them is repainted with the key colour from the top row, and a cell covered by just one keeps its own colour.", gi_exactly_two, tf_exactly_two)


def gi_mode(rng):
    def lf(rng, cols, sep, W):
        return [rng.choice([c for c in COLOURS if c != sep]), rng.choice([c for c in COLOURS if c != sep])]
    return _mk(rng, 2, 3, 0.4, lf)
def tf_mode(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 2:
        return None
    mode = legend[0] % 3
    hit = legend[1] or 5
    a, b = ps; h, w = dims(a)
    out = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            x, y = a[r][c], b[r][c]
            if mode == 0:
                out[r][c] = hit if (x and y) else 0
            elif mode == 1:
                out[r][c] = x or y
            else:
                out[r][c] = hit if (bool(x) != bool(y)) else 0
    return out if _nz_count(out) > 1 else None
rule("mode_selector_and_or_xor", "The top row's first value picks a combining mode (AND, OR or XOR) by its remainder mod three; AND and XOR cells are painted the second key colour, OR keeps each panel's own colour.", gi_mode, tf_mode)


def gi_transparency_chain(rng):
    def lf(rng, cols, sep, W):
        return [rng.choice(cols)]
    return _mk(rng, 3, 3, 0.4, lf, lo=6, hi=12)
def tf_transparency_chain(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 3:
        return None
    marker = legend[0]
    if not marker:
        return None
    a, b, c = ps; h, w = dims(a)
    out = [[0] * w for _ in range(h)]
    for r in range(h):
        for col in range(w):
            for p in (a, b, c):
                v = p[r][col]
                if v and v != marker:
                    out[r][col] = v; break
    return out if _nz_count(out) > 1 else None
rule("transparency_chain_three_panel", "Three panels are stacked front to back; the key colour from the top row acts as transparent in every panel, so the topmost non-transparent, non-empty colour shows at each cell.", gi_transparency_chain, tf_transparency_chain)


def gi_histogram(rng):
    def lf(rng, cols, sep, W):
        return rng.sample([c for c in COLOURS if c != sep], 4)
    return _mk(rng, 3, 2, 0.4, lf, lo=6, hi=12)
def tf_histogram(g):
    legend, sep, ps = _getp(g)
    if len(ps) != 3:
        return None
    key = legend[:4]
    h, w = dims(ps[0])
    present = set()
    for r in range(h):
        for c in range(w):
            present.add(sum(1 for p in ps if p[r][c]))
    if len(present) < 2:
        return None
    return [[key[n] if n in present else 0 for n in range(4)]]
rule("overlap_count_histogram_bar", "Three panels overlap; output a four-cell bar, one cell per possible overlap count (zero to three), coloured from the top row's key wherever that count actually occurs.", gi_histogram, tf_histogram)
