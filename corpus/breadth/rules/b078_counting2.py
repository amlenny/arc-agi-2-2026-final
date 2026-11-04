# b078_counting2.py -- COUNTING AND ARITHMETIC, SECOND SET: the output is a count, sum, difference, ratio or
# parity written as a bar, a digit, a digit pair, a tally or a binary row (never a transformed picture). Scenes:
# separated objects, objects with holes, scattered coloured cells, horizontal/vertical bars, digit cells,
# row bands, touching objects, symmetric/asymmetric objects, solid rectangles, dominoes. Every encoding is stated;
# outputs always contain at least two colours (bars are padded with black to a stated width; zero-capable bars
# start with a grey 5 marker cell).
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


# ---------------- output encoders ----------------
def _bar(n, w, col):
    return [[col] * n + [0] * (w - n)] if 0 < n < w else None


def _mbar(n, w, col):
    """grey 5 marker cell, then a left-aligned bar of n cells of col, padded with black to w cells."""
    return [[5] + [col] * n + [0] * (w - n)] if 0 <= n <= w else None


def _dig(n):
    return [[n, 0]] if 1 <= n <= 9 else None


def _pair(n):
    return [[n // 10, 0, n % 10]] if 0 <= n <= 99 else None


# ---------------- scene builders ----------------
def _sz(rng, lo=8, hi=16, bigp=0.4):
    big = rng.random() < bigp
    return (rng.randint(21, 30), rng.randint(21, 30), True) if big else (rng.randint(lo, hi), rng.randint(lo, hi), False)


def sc_obj(rng, kr=(2, 6), nr=(1, 8), ncol=None, hole=False):
    for _ in range(100):
        h, w, big = _sz(rng)
        k = rng.randint(kr[0], kr[1] + (4 if big else 0))
        shapes = [random_shape(rng, rng.randint(*nr)) for _ in range(k)]
        pal = colours(rng, ncol) if ncol else COLOURS
        g = blank(h, w)
        if place_shapes(rng, g, shapes, [rng.choice(pal) for _ in range(k)], margin=1) is None: continue
        return g
    raise RuntimeError("obj")


def obs(g):
    return [(g[o[0][0]][o[0][1]], o) for o in objects(g, 0, conn8=False)]


def sc_hollow(rng):
    for _ in range(100):
        h, w, big = _sz(rng)
        k = rng.randint(2, 4 + (3 if big else 0)); shapes = []
        for _ in range(k):
            a, b = rng.randint(3, 6), rng.randint(3, 6)
            inner = [(r, c) for r in range(1, a - 1) for c in range(1, b - 1)]
            holes = []
            for _ in range(rng.randint(0, 3)):
                r, c = rng.choice(inner)
                if all(max(abs(r - x), abs(c - y)) > 1 for x, y in holes): holes.append((r, c))
            shapes.append([(r, c) for r in range(a) for c in range(b) if (r, c) not in holes])
        g = blank(h, w)
        if place_shapes(rng, g, shapes, [rng.choice(COLOURS) for _ in range(k)], margin=1) is None: continue
        return g
    raise RuntimeError("hollow")


def enclosed(g):
    H, W = dims(g); seen = set(); st = [(r, c) for r in range(H) for c in range(W) if g[r][c] == 0 and (r in (0, H - 1) or c in (0, W - 1))]
    seen.update(st)
    while st:
        y, x = st.pop()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            n = (y + dy, x + dx)
            if 0 <= n[0] < H and 0 <= n[1] < W and g[n[0]][n[1]] == 0 and n not in seen: seen.add(n); st.append(n)
    left = [(r, c) for r in range(H) for c in range(W) if g[r][c] == 0 and (r, c) not in seen]
    gg = blank(H, W)
    for r, c in left: gg[r][c] = 1
    return components(gg, 1, conn8=False)


def sc_scat(rng, ncol=(2, 5), cmax=13, fixed=None, distinct=False, big_ok=True):
    for _ in range(200):
        h, w, big = _sz(rng, 5, 14, 0.55 if big_ok else 0)
        pal = list(fixed) if fixed else colours(rng, rng.randint(*ncol))
        cnt = {c: rng.randint(1 if not fixed else 0, cmax) for c in pal}
        if distinct and len(set(cnt.values())) < len(cnt): continue
        g = blank(h, w)
        for c, n in cnt.items(): sprinkle(rng, g, n, c)
        if sum(cnt.values()) >= 3: return g
    raise RuntimeError("scat")


def _cnt(g):
    return {c: n for c, n in counts(g).items() if c}


def sc_bars(rng, vertical=False, kr=(2, 6), lr=(1, 9)):
    for _ in range(100):
        h, w, big = _sz(rng, 8, 16, 0.4)
        if vertical: h, w = w, h
        # horizontal bars on alternate-ish rows, one bar per used row
        rows = rng.sample(range(0, h, 2), min(len(range(0, h, 2)), rng.randint(*kr) + (2 if big else 0)))
        g = blank(h, w)
        for r in rows:
            L = rng.randint(lr[0], min(lr[1], w)); c0 = rng.randint(0, w - L); col = rng.choice(COLOURS)
            for c in range(c0, c0 + L): g[r][c] = col
        if len(rows) >= 2: return transpose(g) if vertical else g
    raise RuntimeError("bars")


def sc_dig(rng, kr=(2, 8), exact=None):
    h, w, big = _sz(rng, 5, 14)
    k = exact or rng.randint(*kr); g = blank(h, w)
    for r, c in rng.sample([(r, c) for r in range(h) for c in range(w)], k): g[r][c] = rng.randint(1, 9)
    return g


def sc_band(rng):
    for _ in range(100):
        h, w, big = _sz(rng, 9, 20, 0.4)
        nb = rng.randint(2, 4 + (1 if big else 0)); g = blank(h, w); rows = []
        bh = [rng.randint(3, 5) for _ in range(nb)]
        if sum(bh) + nb - 1 > h: continue
        r = 0
        for i in range(nb):
            rows.append((r, r + bh[i] - 1)); r += bh[i]
            if i < nb - 1:
                for c in range(w): g[r][c] = 5
                r += 1
        ok = True
        for (a, b) in rows:
            k = rng.randint(0, 5); shapes = [random_shape(rng, rng.randint(1, 3)) for _ in range(k)]
            sub = blank(b - a + 1, w)
            if k and place_shapes(rng, sub, shapes, [rng.choice([c for c in COLOURS if c != 5]) for _ in range(k)], margin=1) is None: ok = False; break
            for rr in range(b - a + 1): g[a + rr] = [v if v else g[a + rr][c] for c, v in enumerate(sub[rr])]
        if ok: return g
    raise RuntimeError("band")


def sc_touch(rng):
    for _ in range(200):
        h, w, big = _sz(rng, 6, 12)
        k = min(9, rng.randint(4, 8 + (2 if big else 0))); pal = rng.sample(COLOURS, k); g = blank(h, w); ok = True
        for col in pal:
            sh = random_shape(rng, rng.randint(2, 6)); sh_h = max(r for r, _ in sh) + 1; sh_w = max(c for _, c in sh) + 1
            if sh_h > h or sh_w > w: ok = False; break
            for _t in range(80):
                a, b = rng.randint(0, h - sh_h), rng.randint(0, w - sh_w)
                if all(g[a + r][b + c] == 0 for r, c in sh):
                    for r, c in sh: g[a + r][b + c] = col
                    break
            else: ok = False; break
        if ok: return g
    raise RuntimeError("touch")


def touch_graph(g):
    H, W = dims(g); adj = {c: set() for c in _cnt(g)}
    for r in range(H):
        for c in range(W):
            for dr, dc in ((1, 0), (0, 1)):
                y, x = r + dr, c + dc
                if y < H and x < W and g[r][c] and g[y][x] and g[r][c] != g[y][x]:
                    adj[g[r][c]].add(g[y][x]); adj[g[y][x]].add(g[r][c])
    return adj


def sym_shape(rng, n):
    base = random_shape(rng, n); w = max(c for _, c in base)
    cs = set(base) | {(r, 2 * 0 + (-c)) for r, c in base}
    c0 = min(c for _, c in cs)
    return sorted((r, c - c0) for r, c in cs)


def sc_sym(rng):
    for _ in range(100):
        h, w, big = _sz(rng, 8, 16)
        k = rng.randint(3, 6 + (3 if big else 0))
        shapes = [sym_shape(rng, rng.randint(2, 4)) if rng.random() < 0.5 else random_shape(rng, rng.randint(3, 7)) for _ in range(k)]
        g = blank(h, w)
        if place_shapes(rng, g, shapes, [rng.choice(COLOURS) for _ in range(k)], margin=1) is None: continue
        return g
    raise RuntimeError("sym")


def is_sym(o):
    r0, c0, r1, c1 = bbox(o); s = set(o)
    return all(((r, c0 + c1 - c) in s) for r, c in o)


def sc_rects(rng):
    for _ in range(100):
        h, w, big = _sz(rng, 8, 16)
        k = rng.randint(2, 5 + (3 if big else 0)); shapes = []
        for _ in range(k):
            a, b = rng.randint(1, 4), rng.randint(1, 4)
            shapes.append([(r, c) for r in range(a) for c in range(b)])
        g = blank(h, w)
        if place_shapes(rng, g, shapes, [rng.choice(COLOURS) for _ in range(k)], margin=1) is None: continue
        return g
    raise RuntimeError("rects")


def sc_domino(rng):
    for _ in range(100):
        h, w, big = _sz(rng, 7, 14)
        k = rng.randint(3, 7 + (4 if big else 0)); shapes = []
        for _ in range(k):
            t = rng.random()
            shapes.append([(0, 0), (0, 1)] if t < 0.3 else [(0, 0), (1, 0)] if t < 0.6 else random_shape(rng, rng.choice((1, 3, 4))))
        g = blank(h, w)
        if place_shapes(rng, g, shapes, [rng.choice(COLOURS) for _ in range(k)], margin=1) is None: continue
        return g
    raise RuntimeError("domino")


def sc_dots(rng):
    h, w, big = _sz(rng, 6, 16); g = blank(h, w)
    for r, c in rng.sample([(r, c) for r in range(h - 1) for c in range(w)], rng.randint(3, 14)): g[r][c] = 2
    return g


# ================================================================== object-scene rules
def gi_obj(rng): return sc_obj(rng)
def gi_obj_s(rng): return sc_obj(rng, nr=(1, 9))
def gi_obj_c(rng): return sc_obj(rng, kr=(3, 9), ncol=rng.randint(2, 4))

def tf_mean(g):
    sz = [len(o) for _, o in obs(g)]; k = len(sz)
    return _mbar((2 * sum(sz) + k) // (2 * k), 12, 4)
rule("mean_object_size_bar", "Take the mean number of cells per object (4-connected, one colour each), round halves up, and output one row: a grey (5) marker cell, then that many yellow (4) cells, then black up to 12 cells after the marker.", gi_obj, tf_mean)
def tf_ratio(g):
    sz = [len(o) for _, o in obs(g)]; return _dig(max(sz) // min(sz))
rule("largest_over_smallest_object_floor_digit", "Divide the cell count of the biggest object by the cell count of the smallest object, drop the fraction, and output one row of two cells: that number as a colour value, then black.", gi_obj_s, tf_ratio, digits=True)
def tf_parity(g):
    return [[3, 0, 3]] if len(obs(g)) % 2 == 0 else [[4, 0, 4]]
rule("object_count_parity_swatch", "Count the objects; output a 1x3 row [3,0,3] (green, black, green) if the count is even and [4,0,4] (yellow, black, yellow) if it is odd.", gi_obj, tf_parity)
def tf_bands(g):
    sz = [len(o) for _, o in obs(g)]; cnt = [sum(1 for s in sz if s <= 3), sum(1 for s in sz if 4 <= s <= 6), sum(1 for s in sz if s >= 7)]
    if max(cnt) > 10: return None
    return [[v] * n + [0] * (10 - n) for v, n in zip((1, 2, 3), cnt)]
rule("object_size_band_three_bars", "Count the objects with 3 or fewer cells, with 4 to 6 cells and with 7 or more cells; output three rows of width 10, top to bottom a blue (1), a red (2) and a green (3) left-aligned bar of those counts, padded with black.", gi_obj_s, tf_bands)
def tf_tally(g):
    n = len(obs(g))
    if n > 12: return None
    return [[2, 2, 2]] * (n // 3) + [[4] * (n % 3) + [0] * (3 - n % 3)]
rule("object_count_tally_rows_of_three", "Count the objects n; output n//3 rows of three red (2) cells followed by one last row holding n mod 3 yellow (4) cells left-aligned and padded with black to width 3.", gi_obj, tf_tally)
def gi_obj_many(rng): return sc_obj(rng, kr=(1, 12), nr=(1, 3))
def tf_binary(g):
    n = len(obs(g))
    return [[1 if (n >> i) & 1 else 3 for i in (4, 3, 2, 1, 0)]] if 1 <= n <= 15 else None
rule("object_count_binary_row_blue_green", "Write the object count n (1 to 15) in binary as a row of 5 cells, most significant bit on the left: a blue (1) cell for each 1 bit and a green (3) cell for each 0 bit.", gi_obj_many, tf_binary)
def tf_objcol(g):
    o = obs(g); return _mbar(len(o) - len({c for c, _ in o}), 12, 6)
rule("objects_minus_colours_bar", "Output one row: a grey (5) marker, then as many magenta (6) cells as (number of objects) minus (number of distinct colours among them), then black up to 12 cells after the marker.", gi_obj_c, tf_objcol)
def tf_above(g):
    sz = [len(o) for _, o in obs(g)]; return _dig(sum(1 for s in sz if s * len(sz) > sum(sz)))
rule("objects_above_mean_size_digit", "Count the objects whose cell count is strictly greater than the mean cell count of all objects; output one row of two cells: that count as a colour value, then black.", gi_obj_s, tf_above, digits=True)
def tf_gap(g):
    sz = sorted((len(o) for _, o in obs(g)), reverse=True)
    return _mbar(sz[0] - sz[1], 12, 2) if len(sz) >= 2 else None
rule("largest_minus_second_largest_bar_marked", "Output one row: a grey (5) marker, then as many red (2) cells as the biggest object's cell count minus the second biggest's (0 on a tie), then black up to 12 cells after the marker.", gi_obj_s, tf_gap)
def tf_area(g):
    o = max(obs(g), key=lambda t: (len(t[1]), -t[1][0][0] * 1000 - t[1][0][1]))[1]
    r0, c0, r1, c1 = bbox(o); return _pair((r1 - r0 + 1) * (c1 - c0 + 1))
rule("largest_object_rows_times_columns_digits", "Find the object with most cells (ties: the one whose topmost-then-leftmost cell comes first in reading order); multiply the number of rows by the number of columns of its bounding box and output a 1x3 row: tens digit, black, units digit, as colour values.", gi_obj, tf_area, digits=True)
def tf_perim(g):
    best = max(obs(g), key=lambda t: (len(t[1]), -t[1][0][0] * 1000 - t[1][0][1]))[1]; s = set(best)
    return _pair(sum(4 - sum(((r + a, c + b) in s) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))) for r, c in best))
rule("largest_object_perimeter_digits", "Find the object with most cells (ties: topmost-then-leftmost cell first in reading order); its perimeter is the number of cell sides not shared with another cell of the object (grid edges count as free sides); output a 1x3 row: tens digit, black, units digit, as colour values.", gi_obj, tf_perim, digits=True)
def tf_border(g):
    H, W = dims(g); bd = sum(1 for _, o in obs(g) if any(r in (0, H - 1) or c in (0, W - 1) for r, c in o)); it = len(obs(g)) - bd
    return [[2] * bd + [0] * (12 - bd), [3] * it + [0] * (12 - it)] if bd < 12 and it < 12 else None
rule("border_touching_vs_interior_bars", "Count the objects with a cell on the grid border and the objects with none; output two rows of width 12: a red (2) bar of the border count on top and a green (3) bar of the interior count below, each padded with black.", gi_obj, tf_border)
def tf_largest_ties(g):
    sz = [len(o) for _, o in obs(g)]; return _dig(sum(1 for x in sz if 2 * x >= max(sz)))
rule("objects_at_least_half_the_biggest_digit", "Count the objects whose cell count is at least half of the biggest object's cell count (the biggest included); output one row of two cells: that count as a colour value, then black.", gi_obj_s, tf_largest_ties, digits=True)


# ================================================================== hollow rules
def _holes(g):
    ob = obs(g); omap = {}
    for i, (_, o) in enumerate(ob):
        for cell in o: omap[cell] = i
    per = [0] * len(ob); H, W = dims(g)
    for reg in enclosed(g):
        r, c = reg[0]
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (r + dr, c + dc) in omap: per[omap[(r + dr, c + dc)]] += 1; break
        else:
            for r, c in reg:
                nb = [omap[(r + a, c + b)] for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (r + a, c + b) in omap]
                if nb: per[nb[0]] += 1; break
    return per
def tf_holeobj(g): return _mbar(sum(1 for x in _holes(g) if x), 12, 3)
rule("objects_with_a_hole_bar", "Count the objects that enclose at least one black region (a black region not connected through black cells to the grid border); output one row: a grey (5) marker, then that many green (3) cells, then black up to 12 cells after the marker.", sc_hollow, tf_holeobj)
def tf_stamps(g):
    m = len(enclosed(g))
    if not 1 <= m <= 7: return None
    row = []
    for i in range(m): row += ([8, 8] + ([0] if i < m - 1 else []))
    return [row[:], row[:]]
rule("enclosed_regions_as_two_by_two_stamps", "Count the enclosed black regions m (1 to 7); output two identical rows holding m 2x2 stamps of cyan (8) side by side, separated by one black column.", sc_hollow, tf_stamps)
def tf_holes_digit(g): return _dig(len(enclosed(g)))
rule("total_enclosed_regions_digit", "Count all enclosed black regions in the grid; output one row of two cells: that count as a colour value, then black.", sc_hollow, tf_holes_digit, digits=True)
def tf_mosthole(g): return _mbar(max(_holes(g)), 6, 2)
rule("most_holes_in_one_object_bar", "Find the object that encloses the most black regions; output one row: a grey (5) marker, then that many red (2) cells, then black up to 6 cells after the marker.", sc_hollow, tf_mosthole)


# ================================================================== scatter rules
def gi_sdist(rng): return sc_scat(rng, (3, 5), 13, distinct=True)
def tf_signed(g):
    cn = sorted(_cnt(g).items(), key=lambda kv: -kv[1])
    if len(cn) < 2 or cn[0][1] == cn[1][1] or (len(cn) > 2 and cn[1][1] == cn[2][1]): return None
    d = cn[0][1] - cn[1][1]
    if d > 12: return None
    row = [0] * 25; row[12] = 5
    if cn[0][0] < cn[1][0]:
        for i in range(d): row[13 + i] = cn[0][0]
    else:
        for i in range(d): row[11 - i] = cn[0][0]
    return [row]
rule("two_most_frequent_colours_signed_bar", "Take the two colours with the most cells and the difference d of their cell counts (at most 12); output a row of 25 cells with a grey (5) cell in the middle (index 12) and d cells of the more frequent colour next to it: to the right if that colour's value is smaller than the other colour's value, to the left if larger; rest black.", gi_sdist, tf_signed, digits=True)
def gi_ab(rng):
    g = sc_scat(rng, fixed=[1, 2, 3], cmax=12)
    return g
def tf_ab(g):
    c = _cnt(g); return _mbar(max(0, c.get(1, 0) - c.get(2, 0)), 14, 1)
rule("blue_minus_red_cells_clipped_bar", "Count the blue (1) cells A and the red (2) cells B; output one row: a grey (5) marker, then max(A-B, 0) blue cells, then black up to 14 cells after the marker.", gi_ab, tf_ab)
def gi_scat(rng): return sc_scat(rng, (3, 6), 4)
def tf_twice(g): return _dig(sum(1 for n in _cnt(g).values() if n >= 2))
rule("colours_used_at_least_twice_digit", "Count the colours that appear in at least 2 cells; output one row of two cells: that count as a colour value, then black.", gi_scat, tf_twice, digits=True)
def tf_odd(g): return _dig(sum(1 for n in _cnt(g).values() if n % 2))
rule("colours_with_odd_cell_count_digit", "Count the colours whose total number of cells is odd; output one row of two cells: that count as a colour value, then black.", gi_scat, tf_odd, digits=True)
def tf_rowcol(g):
    H, W = dims(g); rows = sum(1 for r in g if any(r)); cols = sum(1 for c in range(W) if any(g[r][c] for r in range(H)))
    return [[2] * rows + [0] * (30 - rows), [3] * cols + [0] * (30 - cols)]
rule("occupied_rows_and_columns_bars", "Count the rows that contain a coloured cell and the columns that contain one; output two rows of width 30: a red (2) bar of the row count on top and a green (3) bar of the column count below, padded with black.", gi_scat, tf_rowcol)
def tf_range(g):
    c = list(_cnt(g).values()); return _mbar(max(c) - min(c), 14, 6)
rule("colour_count_range_bar", "Take the largest and the smallest per-colour cell count; output one row: a grey (5) marker, then (largest minus smallest) magenta (6) cells, then black up to 14 cells after the marker.", gi_scat, tf_range)
def tf_above_avg(g):
    c = list(_cnt(g).values()); return _dig(sum(1 for n in c if n * len(c) > sum(c)))
rule("colours_above_average_cells_digit", "Count the colours whose cell count is strictly above the mean cell count per colour; output one row of two cells: that count as a colour value, then black.", gi_scat, tf_above_avg, digits=True)
def tf_meancol(g):
    c = list(_cnt(g).values()); return _mbar(sum(c) // len(c), 14, 4)
rule("mean_cells_per_colour_floor_bar", "Divide the total number of coloured cells by the number of distinct colours and drop the fraction; output one row: a grey (5) marker, then that many yellow (4) cells, then black up to 14 cells after the marker.", gi_scat, tf_meancol)


# ================================================================== bar rules
def gi_hb(rng): return sc_bars(rng)
def runs(g):
    out = []
    for r, row in enumerate(g):
        c = 0
        while c < len(row):
            if row[c]:
                e = c
                while e + 1 < len(row) and row[e + 1] == row[c]: e += 1
                out.append(e - c + 1); c = e + 1
            else: c += 1
    return out
def tf_sum5(g):
    s = sum(runs(g))
    if s > 59: return None
    return [[2] * (s // 5) + [0] * (12 - s // 5), [4] * (s % 5) + [0] * (12 - s % 5)]
rule("horizontal_bar_total_in_fives", "Add up the lengths of all horizontal bars (maximal horizontal runs of one colour); output two rows of width 12: the top row has total//5 red (2) cells, the bottom row total mod 5 yellow (4) cells, each left-aligned and padded with black.", gi_hb, tf_sum5)
def gi_vb(rng): return sc_bars(rng, vertical=True)
def tf_vsum(g):
    return _pair(sum(runs(transpose(g))))
rule("vertical_bar_heights_sum_digits", "Add up the heights of all vertical bars (maximal vertical runs of one colour); output a 1x3 row: tens digit, black, units digit of the total, as colour values.", gi_vb, tf_vsum, digits=True)
def tf_spread(g):
    r = runs(g); return _mbar(max(r) - min(r), 10, 3)
rule("longest_minus_shortest_bar_length", "Take the longest and shortest horizontal bar (maximal horizontal run of one colour); output one row: a grey (5) marker, then (longest minus shortest) green (3) cells, then black up to 10 cells after the marker.", gi_hb, tf_spread)
def tf_longshort(g):
    r = runs(g); lo = sum(1 for x in r if x < 5); hi = len(r) - lo
    return [[2] * hi + [0] * (12 - hi), [3] * lo + [0] * (12 - lo)] if hi < 12 and lo < 12 else None
rule("bars_long_vs_short_counts", "Count the horizontal bars (maximal horizontal runs of one colour) of length 5 or more and those of length 4 or less; output two rows of width 12: a red (2) bar of the long count on top and a green (3) bar of the short count below, padded with black.", gi_hb, tf_longshort)


# ================================================================== digit-cell rules
def gi_dsum(rng): return sc_dig(rng, (2, 9))
def tf_dsum(g): return _pair(sum(v for row in g for v in row))
rule("digit_cells_sum_digit_pair", "Add the colour values of all coloured cells; output a 1x3 row: tens digit, black, units digit of the sum, as colour values.", gi_dsum, tf_dsum, digits=True)
def gi_dprod(rng): return sc_dig(rng, exact=2)
def tf_dprod(g):
    v = [x for row in g for x in row if x]; return _pair(v[0] * v[1]) if len(v) == 2 else None
rule("two_digit_cells_product_digit_pair", "The grid holds exactly two coloured cells; multiply their colour values and output a 1x3 row: tens digit, black, units digit of the product, as colour values.", gi_dprod, tf_dprod, digits=True)
def tf_big(g):
    return _mbar(sum(1 for row in g for v in row if v > 4), 10, 2)
rule("cells_valued_above_four_bar", "Count the coloured cells whose colour value is greater than 4; output one row: a grey (5) marker, then that many red (2) cells, then black up to 10 cells after the marker.", gi_dsum, tf_big, digits=True)
def tf_dspread(g):
    v = [x for row in g for x in row if x]; return _mbar(max(v) - min(v), 8, 3)
rule("largest_minus_smallest_cell_value_bar", "Take the largest and smallest colour value among the coloured cells; output one row: a grey (5) marker, then (largest minus smallest) green (3) cells, then black up to 8 cells after the marker.", gi_dsum, tf_dspread, digits=True)
def tf_running(g):
    H, W = dims(g); out = copy(g); run = 0
    for c in range(W):
        run += sum(1 for r in range(H - 1) if g[r][c] == 2); out[H - 1][c] = min(run, 9)
    return out
rule("running_dot_count_into_bottom_row", "Red (2) dots lie above an empty bottom row; write into each bottom-row cell the number of red dots in columns 0 up to and including its column, as a colour value, with 9 as the maximum; everything else is copied.", sc_dots, tf_running, digits=True)


# ================================================================== band rules
def band_counts(g):
    H, W = dims(g); lines = [r for r in range(H) if all(v == 5 for v in g[r])]; edges = [-1] + lines + [H]; out = []
    for a, b in zip(edges, edges[1:]):
        sub = g[a + 1:b]
        out.append(len(objects(sub, 0, conn8=False)) if sub else 0)
    return out
def tf_bandcol(g):
    c = band_counts(g)
    return [[x, 0] for x in c] if max(c) <= 9 and any(c) else None
rule("objects_per_band_digit_column", "Full-width grey (5) lines split the grid into bands; output one row per band, top to bottom, of two cells: the number of objects (4-connected, one colour) in that band as a colour value, then black.", sc_band, tf_bandcol, digits=True)
def tf_bandmax(g):
    c = band_counts(g)
    return _dig(c.index(max(c)) + 1) if max(c) > 0 else None
rule("band_with_most_objects_index_digit", "Full-width grey (5) lines split the grid into bands; output one row of two cells: the 1-based number of the band (counted from the top) holding the most objects, the topmost band on a tie, as a colour value, then black.", sc_band, tf_bandmax, digits=True)


# ================================================================== touching rules
def tf_two(g):
    return _mbar(sum(1 for s in touch_graph(g).values() if len(s) == 2), 10, 3)
rule("objects_touching_exactly_two_others_bar", "Objects are single-colour shapes (one per colour) that may touch side to side; count the objects that touch exactly two other objects and output one row: a grey (5) marker, then that many green (3) cells, then black up to 10 cells after the marker.", sc_touch, tf_two)
def tf_pairs(g):
    return _mbar(sum(len(s) for s in touch_graph(g).values()) // 2, 12, 6)
rule("touching_object_pairs_bar", "Objects are single-colour shapes (one per colour) that may touch side to side; count the pairs of different objects that touch and output one row: a grey (5) marker, then that many magenta (6) cells, then black up to 12 cells after the marker.", sc_touch, tf_pairs)


# ================================================================== symmetry, rectangles, dominoes
def tf_sym(g):
    o = [x for _, x in obs(g)]; s = sum(1 for x in o if is_sym(x)); a = len(o) - s
    return [[2] * s + [0] * (10 - s), [3] * a + [0] * (10 - a)] if s < 10 and a < 10 else None
rule("symmetric_vs_asymmetric_objects_bars", "Count the objects that are left-right mirror symmetric (each cell's mirror about the bounding box's vertical middle is also in the object) and those that are not; output two rows of width 10: a red (2) bar of the symmetric count on top and a green (3) bar of the asymmetric count below, padded with black.", sc_sym, tf_sym)
def tf_win(g):
    H, W = dims(g); n = sum(1 for r in range(H - 1) for c in range(W - 1) if g[r][c] and g[r][c] == g[r + 1][c] == g[r][c + 1] == g[r + 1][c + 1])
    return _mbar(n, 20, 6)
rule("solid_two_by_two_windows_bar", "Count the positions where four cells forming a 2x2 square share one colour (overlapping squares each count); output one row: a grey (5) marker, then that many magenta (6) cells, then black up to 20 cells after the marker.", sc_rects, tf_win)
def tf_domino(g):
    hz = vt = 0
    for _, o in obs(g):
        if len(o) == 2:
            if o[0][0] == o[1][0]: hz += 1
            else: vt += 1
    return [[2] * hz + [0] * (10 - hz), [3] * vt + [0] * (10 - vt)] if hz < 10 and vt < 10 else None
rule("horizontal_vs_vertical_dominoes_bars", "Count the objects of exactly two cells lying side by side (horizontal) and those stacked (vertical); output two rows of width 10: a red (2) bar of the horizontal count on top and a green (3) bar of the vertical count below, padded with black.", sc_domino, tf_domino)
