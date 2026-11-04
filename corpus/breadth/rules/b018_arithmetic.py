# b018_arithmetic.py -- arithmetic and tables: bars as numbers (sum, difference, max, min, ratio, cumulative,
# median, rounding), dot counts as operands, digit tables with totals, counts laid out as tables and charts.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


def _n(rng, lo, hi, p=0.4):
    """A size in lo..hi that lands in the 21..30 band with probability p when the range reaches it."""
    if hi >= 21 and rng.random() < p:
        return rng.randint(max(lo, 21), min(hi, 30))
    return rng.randint(lo, min(hi, 20))


def _vbars(rng, k, hmax, hmin=1, gap=None, cols=None, extra=0, hs=None):
    """k bottom-aligned bars in columns 0, 1+gap, 2(1+gap)...; returns (grid, heights)."""
    gap = rng.randint(1, 3) if gap is None else gap
    hs = hs or [rng.randint(hmin, hmax) for _ in range(k)]
    H, W = hmax + extra, k + gap * (k - 1)
    if H > 30 or W > 30: return None, hs
    g = blank(H, W); cols = cols or [rng.choice(COLOURS)] * k
    for i, (h, col) in enumerate(zip(hs, cols)):
        for r in range(H - h, H): g[r][i * (gap + 1)] = col
    return g, hs


def _cols(g):
    """(column, height, colour) of every column that holds a bar."""
    H, W = dims(g); out = []
    for c in range(W):
        h = sum(1 for r in range(H) if g[r][c])
        if h: out.append((c, h, g[H - 1][c]))
    return out


def _draw(H, W, bars):
    g = blank(H, W)
    for c, h, col in bars:
        for r in range(H - h, H): g[r][c] = col
    return g


def _hbars(rng, k, W, H, distinct=True):
    """k left-aligned horizontal bars of distinct colours on well-separated rows; returns (grid, [(row, len, col)])."""
    if H < 2 * k - 1: return None, None
    rows = sorted(rng.sample(range(H), k))
    if any(b - a < 2 for a, b in zip(rows, rows[1:])): return None, None
    lens = rng.sample(range(1, W + 1), k) if distinct else [rng.randint(1, W) for _ in range(k)]
    cols = colours(rng, k); g = blank(H, W)
    for r, L, col in zip(rows, lens, cols):
        for c in range(L): g[r][c] = col
    return g, list(zip(rows, lens, cols))


def _hrows(g):
    """(row, length, colour) of every row holding a left-aligned bar."""
    return [(r, sum(1 for v in row if v), row[0]) for r, row in enumerate(g) if row[0]]


def _dots(rng, g, k, col, avoid):
    """k single cells of colour col on empty cells with no 8-neighbour coloured, outside avoid (set of cells)."""
    H, W = dims(g); n = 0
    for _ in range(400):
        if n == k: return True
        r, c = rng.randrange(H), rng.randrange(W)
        if (r, c) in avoid or g[r][c]: continue
        if any(g[r + dr][c + dc] for dr in (-1, 0, 1) for dc in (-1, 0, 1) if 0 <= r + dr < H and 0 <= c + dc < W): continue
        g[r][c] = col; n += 1
    return n == k


def _scene(rng, k_lo, k_hi, n_lo, n_hi, lo=6, hi=30, ncol=None):
    h, w = _n(rng, lo, hi), _n(rng, lo, hi); g = blank(h, w)
    k = rng.randint(k_lo, k_hi)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    pal = colours(rng, ncol) if ncol else COLOURS
    cols = [rng.choice(pal) for _ in range(k)]
    if place_shapes(rng, g, shapes, cols, margin=1) is None: return None
    return g if len(objects(g, 0)) == k else None


# 1 two horizontal bars laid end to end: the sum as a two-colour row.
def gi_sumcat(rng):
    W, H = _n(rng, 6, 30), _n(rng, 4, 30)
    g, bars = _hbars(rng, 2, W, H, distinct=False)
    if g is None or bars[0][1] + bars[1][1] > W: return None
    return g
def tf_sumcat(g):
    W = len(g[0]); (r1, a, ca), (r2, b, cb) = _hrows(g)
    return [[ca] * a + [cb] * b + [0] * (W - a - b)]
rule("bars_sum_concatenated_row", "The two left-aligned bars are laid end to end on one row as wide as the grid, the upper bar's cells first and then the lower bar's, so the row shows their total length.", gi_sumcat, tf_sumcat)


# 2 difference: the shorter bar is erased and the longer one loses that many cells from its right end.
def gi_trim(rng):
    W, H = _n(rng, 6, 30), _n(rng, 4, 30)
    g, bars = _hbars(rng, 2, W, H)
    return g
def tf_trim(g):
    out = copy(g); bars = sorted(_hrows(g), key=lambda t: t[1])
    (rs, a, _), (rl, b, _) = bars
    for c in range(W := len(g[0])): out[rs][c] = 0
    for c in range(b - a, W): out[rl][c] = 0
    return out
rule("longer_bar_trimmed_by_shorter", "Of the two left-aligned bars, the shorter is erased and the longer is cut down from its right end by the shorter one's length, leaving a bar of the difference.", gi_trim, tf_trim)


# 3 max and min of several bars as a two-row summary.
def gi_maxmin(rng):
    W, H = _n(rng, 7, 30), _n(rng, 7, 30)
    g, bars = _hbars(rng, rng.randint(3, 7), W, H)
    return g
def tf_maxmin(g):
    W = len(g[0]); bars = sorted(_hrows(g), key=lambda t: t[1])
    return [[bars[-1][2]] * bars[-1][1] + [0] * (W - bars[-1][1]), [bars[0][2]] * bars[0][1] + [0] * (W - bars[0][1])]
rule("bars_max_row_min_row", "Output two rows as wide as the grid: the longest of the left-aligned bars on top and the shortest beneath it, each in its own colour.", gi_maxmin, tf_maxmin)


# 4 two dot counts on either side of a separator give a rectangle's height and width.
def gi_dotrect(rng):
    H, W = _n(rng, 5, 30), _n(rng, 7, 30); g = blank(H, W)
    sep = rng.randint(3, W - 4); grey, ca, cb = colours(rng, 3)
    for r in range(H): g[r][sep] = grey
    a, b = rng.randint(2, min(12, H * sep // 2)), rng.randint(2, min(12, H * (W - sep - 1) // 2))
    for r, c in rng.sample([(r, c) for r in range(H) for c in range(sep)], a): g[r][c] = ca
    for r, c in rng.sample([(r, c) for r in range(H) for c in range(sep + 1, W)], b): g[r][c] = cb
    return g
def tf_dotrect(g):
    H, W = dims(g); sep = next(c for c in range(W) if g[0][c] and all(g[r][c] == g[0][c] for r in range(H)))
    left = [g[r][c] for r in range(H) for c in range(sep) if g[r][c]]
    right = [g[r][c] for r in range(H) for c in range(sep + 1, W) if g[r][c]]
    return [[left[0] if i % 2 == 0 else right[0]] * len(right) for i in range(len(left))]
rule("dot_counts_rectangle_striped", "A full-height line splits the grid; output a rectangle as tall as the number of dots left of the line and as wide as the number right of it, its rows striped alternately in the left dots' colour then the right dots' colour.", gi_dotrect, tf_dotrect)


# 5 table: one row per colour, one column per object size 1..5, cells hold counts as digits.
def gi_sizetab(rng):
    g = _scene(rng, 4, 14, 1, 5, 7, 30, ncol=rng.randint(2, 5))
    if g is None: return None
    cnt = {}
    for o in objects(g, 0): cnt[(g[o[0][0]][o[0][1]], len(o))] = cnt.get((g[o[0][0]][o[0][1]], len(o)), 0) + 1
    return g if max(cnt.values()) <= 9 else None
def tf_sizetab(g):
    cnt = {}
    for o in objects(g, 0):
        k = (g[o[0][0]][o[0][1]], len(o)); cnt[k] = cnt.get(k, 0) + 1
    cs = sorted({c for c, _ in cnt})
    return [[c] + [cnt.get((c, s), 0) for s in range(1, 6)] for c in cs]
rule("colour_size_table_counts", "Output a table with one row per colour (lowest colour on top): a swatch cell, then five cells holding as digits how many objects of that colour have 1, 2, 3, 4 and 5 cells.", gi_sizetab, tf_sizetab, digits=True)


# 6 bar chart against a threshold marked at both edges: the parts of bars above the line turn colour 2.
def gi_thresh(rng):
    k = rng.randint(3, 12); hmax = _n(rng, 4, 28); col = rng.choice([c for c in COLOURS if c not in (2, 5)])
    g, hs = _vbars(rng, k, hmax, extra=1, cols=[col] * k)
    if g is None or len(g[0]) + 2 > 30: return None
    H = len(g); t = rng.randint(1, H - 2)
    if not any(H - h < t for h in hs) or all(H - h < t for h in hs): return None
    g = [[0] + row + [0] for row in g]; g[t][0] = g[t][-1] = 5
    return g
def tf_thresh(g):
    H, W = dims(g); t = next(r for r in range(H) if g[r][0]); out = copy(g)
    for r in range(t):
        for c in range(1, W - 1):
            if out[r][c]: out[r][c] = 2
    return out
rule("bar_tops_above_threshold_recoloured", "Grey markers on the left and right edges mark a threshold row; every bar cell strictly above that row is repainted colour 2 and the rest of each bar keeps its colour.", gi_thresh, tf_thresh)


# 7 cumulative sums: bar i becomes the total of bars 1..i.
def gi_cumul(rng):
    k = rng.randint(3, 10); hs = [rng.randint(1, 3) for _ in range(k)]
    if sum(hs) > 30: return None
    cols = colours(rng, min(k, 9)); cols = (cols * 2)[:k]
    g, _ = _vbars(rng, k, sum(hs), hs=hs, cols=cols)
    return g
def tf_cumul(g):
    H, W = dims(g); bars = _cols(g); s = 0; out = []
    for c, h, col in bars:
        s += h; out.append((c, s, col))
    return _draw(H, W, out)
rule("bars_cumulative_heights", "Each bar grows to the running total: its own height plus the heights of every bar to its left, keeping its colour.", gi_cumul, tf_cumul)


# 8 the bar of median height is highlighted.
def gi_median(rng):
    k = rng.choice([3, 5, 7, 9, 11]); hmax = _n(rng, k + 1, 30)
    hs = rng.sample(range(1, hmax + 1), k); col = rng.choice([c for c in COLOURS if c != 2])
    g, _ = _vbars(rng, k, hmax, hs=hs, cols=[col] * k)
    return g
def tf_median(g):
    H, W = dims(g); bars = _cols(g); med = sorted(h for _, h, _ in bars)[len(bars) // 2]
    return _draw(H, W, [(c, h, 2 if h == med else col) for c, h, col in bars])
rule("median_height_bar_recoloured", "Among an odd number of bars of distinct heights, the one whose height is the median (as many bars taller as shorter) is repainted colour 2.", gi_median, tf_median)


# 9 odd heights round up to even.
def gi_even(rng):
    k = rng.randint(3, 12); hmax = _n(rng, 3, 29)
    g, hs = _vbars(rng, k, hmax, extra=1)
    return g if g is not None and any(h % 2 for h in hs) else None
def tf_even(g):
    H, W = dims(g)
    return _draw(H, W, [(c, h + h % 2, col) for c, h, col in _cols(g)])
rule("bars_rounded_up_to_even_height", "Every bar with an odd height gains one cell on top so that all bar heights become even; even bars are unchanged.", gi_even, tf_even)


# 10 number of objects times number of colours, as a row of colour segments.
def gi_timesrow(rng):
    g = _scene(rng, 2, 10, 1, 6, 6, 30, ncol=rng.randint(2, 4))
    if g is None: return None
    obs = objects(g, 0); k = len({g[o[0][0]][o[0][1]] for o in obs})
    return g if 2 <= k and len(obs) * k <= 30 else None
def tf_timesrow(g):
    obs = objects(g, 0); cs = sorted({g[o[0][0]][o[0][1]] for o in obs}); n = len(obs)
    return [[c for c in cs for _ in range(n)]]
rule("objects_times_colours_segmented_bar", "Output one row whose length is the number of objects times the number of distinct colours: one segment per colour in colour order, each as long as the object count.", gi_timesrow, tf_timesrow)


# 11 a row of digits becomes a bar chart: column c gets a bar of height d in colour d.
def gi_d2bars(rng):
    W = _n(rng, 5, 30); row = [rng.choice([0, 0] + list(range(1, 10))) if rng.random() < 0.8 else 0 for _ in range(W)]
    return [row] if len({v for v in row if v}) >= 2 else None
def tf_d2bars(g):
    row = g[0]; H = max(row)
    return _draw(H, len(row), [(c, d, d) for c, d in enumerate(row) if d])
rule("digit_row_to_height_bars", "The single row of digits becomes a bar chart as tall as the largest digit: under each digit d stands a bottom-aligned bar of d cells in colour d.", gi_d2bars, tf_d2bars, digits=True)


# 12 bars back to digits: each column's height written as one digit.
def gi_bars2d(rng):
    W = _n(rng, 4, 30); H = rng.randint(3, 9); col = rng.choice(COLOURS); g = blank(H, W)
    hs = [rng.randint(0, H) for _ in range(W)]
    for c, h in enumerate(hs):
        for r in range(H - h, H): g[r][c] = col
    return g if len(set(hs)) >= 2 else None
def tf_bars2d(g):
    H, W = dims(g)
    return [[sum(1 for r in range(H) if g[r][c]) for c in range(W)]]
rule("height_bars_to_digit_row", "The bar chart collapses to one row: each column becomes a single cell holding its bar's height as a digit, 0 where there is no bar.", gi_bars2d, tf_bars2d, digits=True)


# 13 a bar is split in the ratio of the dots above it to the dots below it.
def gi_ratio(rng):
    H, W = _n(rng, 5, 30), _n(rng, 6, 30); g = blank(H, W)
    p, q = rng.randint(1, 4), rng.randint(1, 4); m = rng.randint(2, max(2, W // (p + q)))
    L = m * (p + q)
    if L > W: return None
    r = rng.randint(1, H - 2); c0 = rng.randint(0, W - L); ca, cp, cq = colours(rng, 3)
    for c in range(c0, c0 + L): g[r][c] = ca
    above = {(y, x) for y in range(r, H) for x in range(W)}; below = {(y, x) for y in range(0, r + 1) for x in range(W)}
    if not _dots(rng, g, p, cp, above) or not _dots(rng, g, q, cq, below): return None
    return g
def tf_ratio(g):
    H, W = dims(g); cnt = counts(g); cnt.pop(0, None); bar = max(cnt, key=cnt.get)
    r = next(r for r in range(H) if bar in g[r]); xs = [c for c in range(W) if g[r][c] == bar]
    up = [g[y][x] for y in range(r) for x in range(W) if g[y][x]]; dn = [g[y][x] for y in range(r + 1, H) for x in range(W) if g[y][x]]
    cut = len(xs) * len(up) // (len(up) + len(dn)); out = copy(g)
    for i, c in enumerate(xs): out[r][c] = up[0] if i < cut else dn[0]
    return out
rule("bar_split_in_dot_ratio", "The long bar is recoloured in two parts: the left part takes the colour of the dots above it and the right part the colour of the dots below it, their lengths in the same ratio as the two dot counts.", gi_ratio, tf_ratio)


# 14 a small grid of digits becomes a grid of small bar charts.
def gi_panels(rng):
    R, C = rng.randint(2, 5), rng.randint(2, 15); N = rng.randint(3, 30 // R - 1)
    g = [[rng.randint(0, N) for _ in range(C)] for _ in range(R)]
    return g if max(max(r) for r in g) >= 2 and len({v for r in g for v in r if v}) >= 2 else None
def tf_panels(g):
    R, C = dims(g); N = max(max(r) for r in g); out = blank(R * (N + 1) - 1, 2 * C - 1)
    for i in range(R):
        for j in range(C):
            for k in range(g[i][j]): out[i * (N + 1) + N - 1 - k][2 * j] = g[i][j]
    return out
rule("digit_grid_to_bar_panels", "Every digit d is replaced by a vertical bar of d cells in colour d standing in a panel as tall as the largest digit; panels keep the grid's arrangement with one empty row and column between them.", gi_panels, tf_panels, digits=True)


# 15 swatch and count: one row per colour, the colour then its cell count as a digit.
def gi_swcount(rng):
    H, W = _n(rng, 5, 30), _n(rng, 5, 30); g = blank(H, W); k = rng.randint(2, 6); cs = colours(rng, k)
    free = [(r, c) for r in range(H) for c in range(W)]; rng.shuffle(free)
    if len(free) < 9 * k: return None
    for col in cs:
        n = rng.randint(1, 9)
        for _ in range(n): r, c = free.pop(); g[r][c] = col
    return g
def tf_swcount(g):
    cnt = counts(g); cnt.pop(0, None)
    return [[c, cnt[c]] for c in sorted(cnt)]
rule("swatch_and_count_digit_rows", "Output two columns with one row per colour in colour order: a swatch of the colour on the left and, on the right, a digit giving how many cells of that colour the grid holds.", gi_swcount, tf_swcount, digits=True)


# 16 colours ordered by count form a right-aligned staircase, most frequent on top.
def gi_stair(rng):
    H, W = _n(rng, 5, 30), _n(rng, 5, 30); g = blank(H, W); k = rng.randint(2, 7); cs = colours(rng, k)
    if H * W // k < k: return None
    ns = rng.sample(range(1, min(15, H * W // k) + 1), k)
    free = [(r, c) for r in range(H) for c in range(W)]; rng.shuffle(free)
    for col, n in zip(cs, ns):
        for _ in range(n): r, c = free.pop(); g[r][c] = col
    return g
def tf_stair(g):
    cnt = counts(g); cnt.pop(0, None); order = sorted(cnt, key=lambda c: -cnt[c]); k = len(order)
    return [[0] * i + [col] * (k - i) for i, col in enumerate(order)]
rule("colours_by_count_right_staircase", "Output a square with one row per colour, the most frequent colour on top: the top row is full, each row below is one cell shorter and right-aligned, in the next most frequent colour.", gi_stair, tf_stair)


# 17 a bar of n cells is folded into k rows, k given by the dot count.
def gi_fold(rng):
    H, W = _n(rng, 6, 30), _n(rng, 6, 30); g = blank(H, W); k = rng.randint(2, 5)
    if W // k < 2: return None
    m = rng.randint(2, W // k); n = k * m; r = rng.randint(0, H - k); c0 = rng.randint(0, W - n); cb, cd = colours(rng, 2)
    for c in range(c0, c0 + n): g[r][c] = cb
    block = {(y, x) for y in range(r - 1, r + k + 1) for x in range(c0 - 1, c0 + n + 1)}
    return g if _dots(rng, g, k, cd, block) else None
def tf_fold(g):
    H, W = dims(g); cnt = counts(g); cnt.pop(0, None); bar = max(cnt, key=cnt.get); k = sum(v for c, v in cnt.items() if c != bar)
    r = next(r for r in range(H) if bar in g[r]); xs = [c for c in range(W) if g[r][c] == bar]; m = len(xs) // k
    out = copy(g)
    for c in xs: out[r][c] = 0
    for i in range(k):
        for c in range(xs[0], xs[0] + m): out[r + i][c] = bar
    return out
rule("bar_folded_into_dot_count_rows", "Count the dots; the long bar is refolded, starting from its left end, into that many equal rows stacked downward, and the dots stay where they are.", gi_fold, tf_fold)


# 18 a horizontal and a vertical bar give a framed rectangle's width and height.
def gi_framerect(rng):
    H, W = _n(rng, 6, 30), _n(rng, 6, 30); g = blank(H, W); a, b = rng.randint(3, W), rng.randint(3, H); ch, cv = colours(rng, 2)
    for _ in range(50):
        r, c0 = rng.randrange(H), rng.randint(0, W - a); r0, c = rng.randint(0, H - b), rng.randrange(W)
        hs = {(r, x) for x in range(c0, c0 + a)}; vs = {(y, c) for y in range(r0, r0 + b)}
        if not any((y + dy, x + dx) in vs for y, x in hs for dy in (-1, 0, 1) for dx in (-1, 0, 1)):
            for y, x in hs: g[y][x] = ch
            for y, x in vs: g[y][x] = cv
            return g
    return None
def tf_framerect(g):
    obs = objects(g, 0); hb = next(o for o in obs if len({r for r, _ in o}) == 1); vb = next(o for o in obs if len({c for _, c in o}) == 1)
    a, b = len(hb), len(vb); out = blank(b, a, g[hb[0][0]][hb[0][1]])
    return rect(out, 0, 0, b - 1, a - 1, g[vb[0][0]][vb[0][1]], fill=False)
rule("bar_lengths_rectangle_framed", "Output a rectangle as wide as the horizontal bar and as tall as the vertical bar, filled in the horizontal bar's colour with a one-cell border in the vertical bar's colour.", gi_framerect, tf_framerect)


# 19 a bar repeated once per dot, copies alternating colour.
def gi_repeat(rng):
    H, W = _n(rng, 5, 30), _n(rng, 6, 30); g = blank(H, W); k = rng.randint(2, 5); a = rng.randint(3, min(W, 30 // k))
    r = rng.randrange(H); c0 = rng.randint(0, W - a); cb, cd = colours(rng, 2)
    for c in range(c0, c0 + a): g[r][c] = cb
    return g if _dots(rng, g, k, cd, set()) else None
def tf_repeat(g):
    cnt = counts(g); cnt.pop(0, None); bar = max(cnt, key=cnt.get); dot = next(c for c in cnt if c != bar)
    return [[bar if i % 2 == 0 else dot for i in range(cnt[dot]) for _ in range(cnt[bar])]]
rule("bar_repeated_per_dot_alternating", "Output one row made of the bar repeated end to end once for every dot, the copies alternating between the bar's colour and the dots' colour starting with the bar's.", gi_repeat, tf_repeat)


# 20 bar length divided by the dot count.
def gi_divide(rng):
    H, W = _n(rng, 5, 30), _n(rng, 6, 30); g = blank(H, W); k = rng.randint(2, 5); m = rng.randint(2, max(2, W // k)); n = k * m
    if n > W: return None
    r = rng.randrange(H); c0 = rng.randint(0, W - n); cb, cd = colours(rng, 2)
    for c in range(c0, c0 + n): g[r][c] = cb
    return g if _dots(rng, g, k, cd, set()) else None
def tf_divide(g):
    W = len(g[0]); cnt = counts(g); cnt.pop(0, None); bar = max(cnt, key=cnt.get); k = sum(v for c, v in cnt.items() if c != bar)
    m = cnt[bar] // k
    return [[bar] * m + [0] * (W - m)]
rule("bar_length_divided_by_dots", "Output one row as wide as the grid holding a left-aligned bar in the bar's colour whose length is the bar's length divided by the number of dots.", gi_divide, tf_divide)


# 21 each bar becomes its shortfall from the tallest.
def gi_compl(rng):
    k = rng.randint(3, 12); hmax = _n(rng, 3, 30)
    g, hs = _vbars(rng, k, hmax, hs=[rng.randint(1, hmax) for _ in range(k)])
    return g if g is not None and len(set(hs)) >= 2 and max(hs) == hmax else None
def tf_compl(g):
    H, W = dims(g); bars = _cols(g); top = max(h for _, h, _ in bars)
    return _draw(H, W, [(c, top - h, col) for c, h, col in bars])
rule("bars_complement_to_tallest", "Every bar's height is replaced by how far it fell short of the tallest bar, so the tallest bar vanishes and the shortest becomes the tallest.", gi_compl, tf_compl)


# 22 bars taken in adjacent pairs and summed.
def gi_pairsum(rng):
    k = rng.randint(2, 7); hmax = _n(rng, 2, 15)
    g, hs = _vbars(rng, 2 * k, hmax, extra=hmax)
    return g if g is not None and len(set(hs[i] + hs[i + 1] for i in range(0, 2 * k, 2))) >= 2 else None
def tf_pairsum(g):
    H, W = dims(g); bars = _cols(g); k = len(bars) // 2
    return _draw(H, 2 * k - 1, [(2 * i, bars[2 * i][1] + bars[2 * i + 1][1], bars[2 * i][2]) for i in range(k)])
rule("bar_pairs_summed", "The bars are taken in pairs from the left and each pair is replaced by one bar as tall as the two together, the new bars standing one empty column apart.", gi_pairsum, tf_pairsum)


# 23 running maximum of bar heights.
def gi_runmax(rng):
    k = rng.randint(3, 12); hmax = _n(rng, 3, 30)
    g, hs = _vbars(rng, k, hmax)
    return g if g is not None and any(hs[i] < hs[i - 1] for i in range(1, k)) else None
def tf_runmax(g):
    H, W = dims(g); m = 0; out = []
    for c, h, col in _cols(g):
        m = max(m, h); out.append((c, m, col))
    return _draw(H, W, out)
rule("bars_running_maximum", "Reading left to right, every bar is raised to the height of the tallest bar seen so far, so no bar is shorter than any bar to its left.", gi_runmax, tf_runmax)


# 24 differences between neighbouring bars.
def gi_diffs(rng):
    k = rng.randint(3, 12); hmax = _n(rng, 3, 30)
    g, hs = _vbars(rng, k, hmax)
    return g if g is not None and len(set(abs(hs[i] - hs[i + 1]) for i in range(k - 1))) >= 2 else None
def tf_diffs(g):
    H, W = dims(g); bars = _cols(g); gap = bars[1][0] - bars[0][0]
    return _draw(H, (len(bars) - 2) * gap + 1, [(i * gap, abs(bars[i][1] - bars[i + 1][1]), bars[i][2]) for i in range(len(bars) - 1)])
rule("bars_consecutive_differences", "Each pair of neighbouring bars is replaced by one bar as tall as the difference between their heights, giving one bar fewer than before with the same spacing.", gi_diffs, tf_diffs)


# 25 digits unrolled: digit d becomes d cells of colour d, packed into one row.
def gi_unroll(rng):
    W = _n(rng, 4, 30); k = rng.randint(2, min(7, W)); row = [0] * W
    vals = [rng.randint(1, 9) for _ in range(k)]
    while sum(vals) > 30: vals[vals.index(max(vals))] -= 1
    for c, v in zip(rng.sample(range(W), k), vals): row[c] = v
    return [row] if len(set(vals)) >= 2 else None
def tf_unroll(g):
    return [[d for d in g[0] if d for _ in range(d)]]
rule("digit_row_unrolled_to_runs", "Reading the digits left to right, each digit d is written out as a run of d cells in colour d, the runs packed together into one row and the empty cells dropped.", gi_unroll, tf_unroll, digits=True)


# 26 runs to digits: each run in a row becomes a digit giving its length.
def gi_runs2d(rng):
    H, W = _n(rng, 3, 30), _n(rng, 5, 30); g = blank(H, W); mx = 0
    for r in range(H):
        c = rng.randint(0, 2); k = 0
        while c < W:
            L = rng.randint(1, min(9, W - c))
            if rng.random() < 0.3: c += L; continue
            col = rng.choice(COLOURS)
            for x in range(c, c + L): g[r][x] = col
            c += L + 1; k += 1
        mx = max(mx, k)
    return g if mx >= 1 and len({(sum(1 for v in row if v)) for row in g}) >= 2 else None
def tf_runs2d(g):
    H, W = dims(g); rows = []
    for row in g:
        runs, c = [], 0
        while c < W:
            if row[c]:
                L = 0
                while c + L < W and row[c + L] == row[c]: L += 1
                runs.append(L); c += L
            else: c += 1
        rows.append(runs)
    k = max(len(r) for r in rows)
    return [r + [0] * (k - len(r)) for r in rows]
rule("runs_to_length_digits", "Each row is replaced by the lengths of its unbroken one-colour runs written as digits packed to the left, one digit per run in order; the output is as wide as the most runs any row has.", gi_runs2d, tf_runs2d, digits=True)


# 27 bars clipped at a threshold line marked at both edges.
def gi_clip(rng):
    k = rng.randint(3, 12); hmax = _n(rng, 4, 28); col = rng.choice([c for c in COLOURS if c != 5])
    g, hs = _vbars(rng, k, hmax, extra=1, cols=[col] * k)
    if g is None or len(g[0]) + 2 > 30: return None
    H = len(g); t = rng.randint(1, H - 2)
    if not any(H - h < t for h in hs) or all(H - h < t for h in hs): return None
    g = [[0] + row + [0] for row in g]; g[t][0] = g[t][-1] = 5
    return g
def tf_clip(g):
    H, W = dims(g); t = next(r for r in range(H) if g[r][0]); out = copy(g)
    for r in range(t):
        for c in range(1, W - 1): out[r][c] = 0
    return out
rule("bars_clipped_at_marker_line", "Grey markers on the left and right edges mark a row; every bar is cut off at that row, with everything strictly above it erased and the markers left in place.", gi_clip, tf_clip)


# 28 digit table with row totals appended.
def _digit_table(rng, R, C, cap=9):
    g = []
    for _ in range(R):
        for _ in range(50):
            row = [rng.choice([0, 0, 0, 0, 0, 1, 1, 1, 2, 2]) for _ in range(C)]
            if sum(row) <= cap: g.append(row); break
        else: return None
    return g
def gi_rowsums(rng):
    R, C = _n(rng, 2, 30), rng.randint(3, 9); g = _digit_table(rng, R, C)
    return g if g and len({sum(r) for r in g}) >= 2 else None
def tf_rowsums(g):
    return [r + [sum(r)] for r in g]
rule("digit_table_append_row_sums", "A new column is added at the right of the digit table holding, as a digit, the total of each row.", gi_rowsums, tf_rowsums, digits=True)


# 29 digit table with column totals appended.
def gi_colsums(rng):
    R, C = rng.randint(3, 9), _n(rng, 2, 30); g = _digit_table(rng, C, R)
    if not g or len({sum(r) for r in g}) < 2: return None
    return transpose(g)
def tf_colsums(g):
    return g + [[sum(col) for col in zip(*g)]]
rule("digit_table_append_column_sums", "A new row is added beneath the digit table holding, as a digit, the total of each column.", gi_colsums, tf_colsums, digits=True)


# 30 two dot groups: a, b and a+b as a row of three digits.
def gi_sumdig(rng):
    H, W = _n(rng, 4, 30), _n(rng, 7, 30); g = blank(H, W); sep = rng.randint(3, W - 4); grey, ca, cb = colours(rng, 3)
    for r in range(H): g[r][sep] = grey
    a = rng.randint(1, 8); b = rng.randint(1, 9 - a)
    for r, c in rng.sample([(r, c) for r in range(H) for c in range(sep)], a): g[r][c] = ca
    for r, c in rng.sample([(r, c) for r in range(H) for c in range(sep + 1, W)], b): g[r][c] = cb
    return g
def tf_sumdig(g):
    H, W = dims(g); sep = next(c for c in range(W) if g[0][c] and all(g[r][c] == g[0][c] for r in range(H)))
    a = sum(1 for r in range(H) for c in range(sep) if g[r][c]); b = sum(1 for r in range(H) for c in range(sep + 1, W) if g[r][c])
    return [[a, b, a + b]]
rule("dot_groups_sum_digit_row", "A full-height line splits the grid; output one row of three digits: the number of dots left of the line, the number right of it, and their sum.", gi_sumdig, tf_sumdig, digits=True)


# 31 two digit cells give a chequered rectangle's height and width.
def gi_cheq(rng):
    H, W = _n(rng, 3, 30), _n(rng, 3, 30); g = blank(H, W); a, b = rng.sample(range(2, 10), 2)
    g[0][rng.randint(1, W - 1)] = a; g[rng.randint(1, H - 1)][0] = b
    return g
def tf_cheq(g):
    a = next(v for v in g[0] if v); b = next(row[0] for row in g if row[0])
    return [[a if (i + j) % 2 == 0 else b for j in range(b)] for i in range(a)]
rule("digit_pair_chequered_rectangle", "The digit in the top row gives a height and the digit in the left column a width; output a rectangle of that size chequered in the two digit colours, the height digit's colour in the top-left corner.", gi_cheq, tf_cheq, digits=True)


# 32 each object takes as its value the number of objects of its colour.
def gi_colcount(rng):
    g = _scene(rng, 3, 14, 1, 6, 6, 30, ncol=rng.randint(2, 4))
    if g is None: return None
    cnt = {}
    for o in objects(g, 0): cnt[g[o[0][0]][o[0][1]]] = cnt.get(g[o[0][0]][o[0][1]], 0) + 1
    return g if max(cnt.values()) <= 9 and any(cnt[c] != c for c in cnt) else None
def tf_colcount(g):
    obs = objects(g, 0); cnt = {}
    for o in obs: cnt[g[o[0][0]][o[0][1]]] = cnt.get(g[o[0][0]][o[0][1]], 0) + 1
    out = copy(g)
    for o in obs:
        for r, c in o: out[r][c] = cnt[g[o[0][0]][o[0][1]]]
    return out
# objects_recoloured_by_colour_object_count dropped 2026-10-12 (trio review: behavioural duplicate or one global operation)
# 33 a grey line at the mean bar height.
def gi_meanline(rng):
    k = rng.randint(2, 12); hmax = _n(rng, 3, 30); col = rng.choice([c for c in COLOURS if c != 5])
    for _ in range(30):
        hs = [rng.randint(1, hmax) for _ in range(k)]
        if sum(hs) % k == 0 and len(set(hs)) >= 2 and max(hs) == hmax: break
    else: return None
    g, _ = _vbars(rng, k, hmax, hs=hs, cols=[col] * k)
    return g
def tf_meanline(g):
    H, W = dims(g); bars = _cols(g); m = sum(h for _, h, _ in bars) // len(bars); out = copy(g)
    for c in range(W):
        if not out[H - m][c]: out[H - m][c] = 5
    return out
rule("bars_mean_height_line", "A grey line is drawn across the whole width at the height of the average bar (the row a bar of average height would top out at), painted only on empty cells so the bars show through.", gi_meanline, tf_meanline)


# 34 all bar cells pooled and packed row by row from the top-left.
def gi_pack(rng):
    k = rng.randint(3, 12); hmax = _n(rng, 3, 30)
    g, hs = _vbars(rng, k, hmax)
    return g if g is not None and len(set(hs)) >= 2 else None
def tf_pack(g):
    H, W = dims(g); bars = _cols(g); T = sum(h for _, h, _ in bars); col = bars[0][2]; out = blank(H, W)
    for i in range(T): out[i // W][i % W] = col
    return out
rule("bars_total_cells_packed_rows", "All the bar cells are pooled and laid out again row by row from the top-left corner, filling each row completely before starting the next, so the total is shown as a filled block.", gi_pack, tf_pack)


# 35 the most common bar height is highlighted.
def gi_mode(rng):
    k = rng.randint(4, 12); hmax = _n(rng, 3, 30); col = rng.choice([c for c in COLOURS if c != 2])
    for _ in range(40):
        hs = [rng.randint(1, hmax) for _ in range(k)]; cnt = sorted((hs.count(h) for h in set(hs)), reverse=True)
        if len(cnt) >= 2 and cnt[0] > cnt[1]: break
    else: return None
    g, _ = _vbars(rng, k, hmax, hs=hs, cols=[col] * k)
    return g
def tf_mode(g):
    H, W = dims(g); bars = _cols(g); hs = [h for _, h, _ in bars]; mode = max(set(hs), key=hs.count)
    return _draw(H, W, [(c, h, 2 if h == mode else col) for c, h, col in bars])
rule("most_common_bar_height_recoloured", "The bars whose height occurs more often than any other height are repainted colour 2; the rest keep their colour.", gi_mode, tf_mode)


# 36 heights doubled.
def gi_double(rng):
    k = rng.randint(3, 12); hmax = _n(rng, 2, 15)
    g, hs = _vbars(rng, k, hmax, extra=hmax)
    return g if g is not None and len(set(hs)) >= 2 else None
def tf_double(g):
    H, W = dims(g)
    return _draw(H, W, [(c, 2 * h, col) for c, h, col in _cols(g)])
rule("bars_doubled_height", "Every bar becomes twice as tall as it was.", gi_double, tf_double)


# 38 each row's dot count doubled into a bar.
def gi_rowdouble(rng):
    H, W = _n(rng, 3, 30), _n(rng, 4, 30); g = blank(H, W); col = rng.choice(COLOURS); ks = []
    for r in range(H):
        k = rng.randint(0, W // 2) if rng.random() < 0.7 else 0; ks.append(k)
        for c in rng.sample(range(W), k): g[r][c] = col
    return g if len(set(ks)) >= 2 and max(ks) else None
def tf_rowdouble(g):
    H, W = dims(g); col = max(v for row in g for v in row)
    return [[col] * (2 * sum(1 for v in row if v)) + [0] * (W - 2 * sum(1 for v in row if v)) for row in g]
rule("row_dots_doubled_bar", "Each row is replaced by a left-aligned bar twice as long as the number of coloured cells the row had.", gi_rowdouble, tf_rowdouble)


# 39 the bar loses one cell per dot.
def gi_shorten(rng):
    H, W = _n(rng, 5, 30), _n(rng, 6, 30); g = blank(H, W); k = rng.randint(1, min(6, W - 1)); n = rng.randint(k + 1, W)
    r = rng.randrange(H); c0 = rng.randint(0, W - n); cb, cd = colours(rng, 2)
    for c in range(c0, c0 + n): g[r][c] = cb
    return g if _dots(rng, g, k, cd, set()) else None
def tf_shorten(g):
    H, W = dims(g); cnt = counts(g); cnt.pop(0, None); bar = max(cnt, key=cnt.get); k = sum(v for c, v in cnt.items() if c != bar)
    r = next(r for r in range(H) if bar in g[r]); xs = [c for c in range(W) if g[r][c] == bar]; out = copy(g)
    for c in xs[len(xs) - k:]: out[r][c] = 0
    return out
rule("bar_shortened_by_dot_count", "The bar loses as many cells from its right end as there are dots in the grid; the dots stay.", gi_shorten, tf_shorten)


# 40 each digit row's total as a grey bar.
def gi_rowbars(rng):
    R, C = _n(rng, 2, 30), rng.randint(3, 10); g = _digit_table(rng, R, C, cap=30)
    return g if g and len({sum(r) for r in g}) >= 2 and max(sum(r) for r in g) >= 2 else None
def tf_rowbars(g):
    S = max(sum(r) for r in g)
    return [[5] * sum(r) + [0] * (S - sum(r)) for r in g]
rule("digit_rows_sum_bars", "Each row of digits becomes a left-aligned grey bar as long as the row's total; the output is as wide as the largest total.", gi_rowbars, tf_rowbars, digits=True)


# 41 running totals along each row of digits.
def gi_runtot(rng):
    R, C = _n(rng, 2, 30), _n(rng, 4, 30); g = []
    for _ in range(R):
        for _ in range(50):
            row = [rng.choice([0, 0, 0, 0, 1, 1, 2]) if rng.random() < 0.5 else 0 for _ in range(C)]
            if sum(row) <= 9: g.append(row); break
        else: return None
    return g if any(sum(r) >= 2 for r in g) else None
def tf_runtot(g):
    out = []
    for row in g:
        s, new = 0, []
        for v in row:
            s += v; new.append(s)
        out.append(new)
    return out
rule("digit_rows_running_total", "Every cell is replaced by the running total of its row so far: the sum of itself and every digit to its left, written as a digit.", gi_runtot, tf_runtot, digits=True)
