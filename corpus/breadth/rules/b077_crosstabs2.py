# b077_crosstabs2.py -- CROSS-TABULATION AND SUMMARY GRIDS, SECOND SET: the output is a small table computed from the
# scene (colours x shape classes, colours x bands/halves/thirds, ninths and quadrants, border/hollow contingency, size-class
# bar chart, adjacency and co-occurrence matrices, rankings, margin borders). Digits are literal cell values (digits=True).
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


def D(rng, lo=8, hi=29):
    if rng.random() < 0.45: return rng.randint(21, hi)
    return rng.randint(lo, min(hi, 20))


def cp(n): return min(9, int(n))


def mk(gen, tf, cond=None, tries=90):
    def make(rng):
        last = None
        for _ in range(tries):
            g = gen(rng)
            if g is None: continue
            last = g
            o = tf(g)
            if o is None or o == g: continue
            if len({v for r in o for v in r}) < 2: continue
            if cond is None or cond(g, o): return g
        return last if last is not None else blank(8, 8)
    return make


def scatter_subs(rng, H, Wd, subs, margin=1):
    g = blank(H, Wd); boxes = []
    for sub in subs:
        h, w = dims(sub)
        if h > H or w > Wd: return None
        for _ in range(150):
            r0, c0 = rng.randint(0, H - h), rng.randint(0, Wd - w)
            if all(r0 > b[2] + margin or r0 + h - 1 < b[0] - margin or c0 > b[3] + margin or c0 + w - 1 < b[1] - margin for b in boxes):
                boxes.append((r0, c0, r0 + h - 1, c0 + w - 1)); paste(g, sub, r0, c0, transparent=0); break
        else:
            return None
    return g


def objs(g):
    out = []
    for col in sorted({v for r in g for v in r if v}):
        for c in components(g, col, conn8=False): out.append((col, sorted(c)))
    return sorted(out, key=lambda o: o[1][0])


def cols_of(g): return sorted({v for r in g for v in r if v})


def pad(rows):
    w = max(len(r) for r in rows); return [r + [0] * (w - len(r)) for r in rows]


def ninth(r, n): return 0 if r < n // 3 else 1 if r < 2 * n // 3 else 2


# ---------------------------------------------------------------- scene families
def f1(reuse=False, kmax=8):
    def gen(rng):
        H, Wd = D(rng), D(rng); k = rng.randint(3, max(3, min(kmax, 1 + H * Wd // 45))); pc = rng.sample(range(1, 10), rng.randint(2, 5))
        if reuse:
            base = [random_shape(rng, rng.randint(2, 5)) for _ in range(rng.randint(2, 3))]; shapes = [rng.choice(base) for _ in range(k)]
        else:
            shapes = [random_shape(rng, rng.randint(1, 8)) for _ in range(k)]
        g = blank(H, Wd)
        return g if place_shapes(rng, g, shapes, [rng.choice(pc) for _ in range(k)], margin=1) else None
    return gen


def klass(cells):
    r0, c0, r1, c1 = bbox(cells); h, w = r1 - r0 + 1, c1 - c0 + 1; n = len(cells)
    return 'S' if n == 1 else 'L' if n == h * w and min(h, w) == 1 else 'R' if n == h * w else 'O'


def f2(rng, big=False):
    H, Wd = D(rng), D(rng); k = rng.randint(3, max(3, min(9, 1 + H * Wd // 45))); pc = rng.sample(range(1, 10), rng.randint(2, 5)); shapes = []
    for _ in range(k):
        t = rng.choice('SLRRO' if not big else 'LRROO')
        if t == 'S': s = [(0, 0)]
        elif t == 'L':
            n = rng.randint(2, 5); s = [(0, i) for i in range(n)] if rng.random() < .5 else [(i, 0) for i in range(n)]
        elif t == 'R': s = [(r, c) for r in range(rng.randint(2, 4)) for c in range(rng.randint(2, 4))]
        else:
            s = random_shape(rng, rng.randint(4, 9))
            if klass(s) != 'O': return None
        if t == 'R':
            h = rng.randint(2, 4); w = rng.randint(2, 4); s = [(r, c) for r in range(h) for c in range(w)]
        shapes.append(s)
    g = blank(H, Wd)
    return g if place_shapes(rng, g, shapes, [rng.choice(pc) for _ in range(k)], margin=1) else None


def f3(dens=(.05, .14), npool=(2, 5)):
    def gen(rng):
        H, Wd = D(rng), D(rng); pc = rng.sample(range(1, 10), rng.randint(*npool)); g = blank(H, Wd)
        free = [(r, c) for r in range(H) for c in range(Wd)]
        for r, c in rng.sample(free, max(6, int(H * Wd * rng.uniform(*dens)))): g[r][c] = rng.choice(pc)
        return g
    return gen


def f4(rng):
    H, Wd = D(rng), D(rng); k = rng.randint(3, max(3, min(8, 1 + H * Wd // 50))); pc = rng.sample(range(1, 10), rng.randint(2, 4)); subs = []
    for _ in range(k):
        h, w = rng.randint(3, 7), rng.randint(3, 7); a = rng.choice(pc); s = [[a] * w for _ in range(h)]
        if rng.random() < .5: rect(s, 1, 1, h - 2, w - 2, 0)
        subs.append(s)
    return scatter_subs(rng, H, Wd, subs)


def f5(rng):
    H, Wd = D(rng, 10), D(rng, 10); pc = rng.sample(range(1, 10), rng.randint(3, 6)); subs = []
    for _ in range(rng.randint(2, 4)):
        n = rng.randint(2, 3); ws = [rng.randint(2, 4) for _ in range(n)]; hs = [rng.randint(2, 4) for _ in range(n)]
        cs = [rng.choice(pc)]
        for i in range(1, n): cs.append(rng.choice([c for c in pc if c != cs[-1]]))
        s = blank(max(hs), sum(ws)); x = 0
        for w, h, c in zip(ws, hs, cs): rect(s, 0, x, h - 1, x + w - 1, c); x += w
        subs.append(s)
    return scatter_subs(rng, H, Wd, subs)


def f6(rng):
    H, Wd = D(rng), D(rng); pc = rng.sample(range(1, 10), rng.randint(2, 5)); g = blank(H, Wd)
    for _ in range(rng.randint(3, 9)):
        a = rng.choice(pc); L = rng.randint(3, max(3, min(H, Wd) - 1))
        if rng.random() < .5:
            r = rng.randrange(H); c = rng.randint(0, Wd - L)
            for i in range(L): g[r][c + i] = a
        else:
            c = rng.randrange(Wd); r = rng.randint(0, H - L)
            for i in range(L): g[r + i][c] = a
    return g


def f7(rng):
    H, Wd = D(rng, 10), D(rng, 10); subs = []
    for _ in range(rng.randint(2, 4)):
        h, w = rng.randint(5, 8), rng.randint(5, 8); a, b = rng.sample(range(1, 10), 2); s = blank(h, w); rect(s, 0, 0, h - 1, w - 1, a, fill=False)
        for r, c in rng.sample([(r, c) for r in range(2, h - 2) for c in range(2, w - 2)], rng.randint(1, min(6, (h - 4) * (w - 4)))): s[r][c] = b
        subs.append(s)
    return scatter_subs(rng, H, Wd, subs, 1)


# ---------------------------------------------------------------- rules
def tf1(g):
    os_ = objs(g); cs = cols_of(g); cl = 'SLRO'
    return [[cp(sum(1 for c, cells in os_ if c == col and klass(cells) == k)) for k in cl] for col in cs]
rule("colour_by_shape_class_count_table", "One row per colour present (ascending colour value), four columns for shape classes S = single cell, L = straight line of 2 or more cells (a filled 1-wide bounding box), R = filled rectangle at least 2x2, O = any other shape; each cell is the digit count of that colour's objects in the class (4-connected same-colour objects), capped at 9.",
     mk(f2, tf1), tf1, digits=True)


def tf13(g):
    os_ = objs(g); out = []
    for col in cols_of(g):
        row = []
        for k in 'SLRO':
            n = min(3, sum(1 for c, cells in os_ if c == col and klass(cells) == k)); row += [col] * n + [0] * (3 - n)
        out.append(row)
    return out
rule("colour_by_shape_class_bar_table", "One row per colour present (ascending colour value), twelve columns in four segments of width 3 for shape classes S = single cell, L = straight line of 2 or more cells, R = filled rectangle at least 2x2, O = any other shape; each segment holds, from its left, one cell of the row's colour per object of that class (4-connected, same colour), at most 3, rest empty.",
     mk(f2, tf13), tf13)


def tf2(g):
    H, W = dims(g); nb = -(-H // 4)
    return [[col if any(g[r][c] == col for r in range(4 * b, min(H, 4 * b + 4)) for c in range(W)) else 0 for b in range(nb)] for col in cols_of(g)]
rule("colour_by_four_row_band_presence_table", "Cut the grid into row-bands of 4 rows (the last band may be shorter); one table row per colour present (ascending colour value), one column per band from the top, holding the colour itself if it appears anywhere in the band and empty otherwise.",
     mk(f3((.03, .08)), tf2), tf2)


def tf3(g):
    H, W = dims(g); out = blank(3, 3); os_ = objs(g)
    for col in sorted({c for c, _ in os_}, reverse=True):
        best = max([cells for c, cells in os_ if c == col], key=lambda s: (len(s), -s[0][0], -s[0][1]))
        out[ninth(best[0][0], H)][ninth(best[0][1], W)] = col
    return out
rule("ninth_holding_each_colours_largest_object", "Divide the grid into a 3x3 block of ninths (row cuts at h//3 and 2h//3, column cuts at w//3 and 2w//3); for each colour find its largest object (most cells; a tie goes to the one whose first cell in reading order comes first) and write the colour into the 3x3 output cell for the ninth containing that first cell; if two colours land in the same ninth, the smaller colour value is written.",
     mk(f1(), tf3), tf3)


def tf4(g):
    H, W = dims(g); mh, mw = H // 2, W // 2; out = []
    for (r0, r1) in ((0, mh), (mh, H)):
        row = []
        for (c0, c1) in ((0, mw), (mw, W)):
            cnt = {}
            for r in range(r0, r1):
                for c in range(c0, c1):
                    if g[r][c]: cnt[g[r][c]] = cnt.get(g[r][c], 0) + 1
            row.append(min(cnt, key=lambda k: (cnt[k], k)) if cnt else 0)
        out.append(row)
    return out
rule("quadrant_rarest_colour_2x2", "Split the grid into four quadrants (row cut at h//2, column cut at w//2); the 2x2 output holds, per quadrant, the non-background colour with the fewest cells there (a tie goes to the smaller colour value), or empty if the quadrant has none.",
     mk(f3(), tf4), tf4)


def tf5(g):
    H, W = dims(g); os_ = objs(g); out = []
    for col in cols_of(g):
        l = sum(1 for c, cells in os_ if c == col and cells[0][1] < W // 2); r = sum(1 for c, cells in os_ if c == col and cells[0][1] >= W // 2)
        out.append([cp(l), cp(r), cp(abs(l - r))])
    return out
rule("colour_object_count_halves_and_difference", "One row per colour present (ascending), three digit columns: the number of that colour's objects whose first cell in reading order lies in the left half (column < w//2), the number in the right half (column >= w//2), and the absolute difference of the two; counts capped at 9.",
     mk(f1(), tf5), tf5, digits=True)


def tf6(g):
    H, W = dims(g); out = blank(H + 1, W + 1)
    out[0][0] = len(cols_of(g))
    for c in range(W): out[0][c + 1] = cp(sum(1 for r in range(H) if g[r][c]))
    for r in range(H): out[r + 1][0] = cp(sum(1 for v in g[r] if v))
    return out
rule("margin_counts_as_border_only", "The output is one row and one column larger than the input and holds only a border: its top-left cell is the number of distinct colours present, the rest of the top row holds each input column's count of non-empty cells (capped 9), the rest of the left column holds each input row's count (capped 9), and the interior is empty.",
     mk(lambda r: (lambda g: g)(f3((.04, .1))(r)), tf6), tf6, digits=True)


def tf7(g):
    return [[col, min(9, min(r for r, row in enumerate(g) if col in row) // 3)] for col in cols_of(g)]
rule("colour_topmost_row_index_table", "One row per colour present (ascending), two columns: the colour, then the digit floor(r/3) (r = 0-based row of that colour's topmost cell, capped at 9).",
     mk(f1(), tf7), tf7, digits=True)


def tf8(g):
    cnt = {}
    for row in g:
        for v in row:
            if v: cnt[v] = cnt.get(v, 0) + 1
    order = sorted(cnt, key=lambda k: (-cnt[k], k))
    return [[i + 1, col, cp(cnt[col] // 2)] for i, col in enumerate(order)]
rule("area_ranking_table_rank_colour_area", "One row per colour present, ordered by total cell count from most to least (a tie goes to the smaller colour value): the rank 1, 2, 3 ..., the colour, and the digit floor(total cells / 2) capped at 9.",
     mk(f1(), tf8), tf8, digits=True)


def hollow_objs(g):
    H, W = dims(g); seen = set(); st = [(r, c) for r in range(H) for c in range(W) if (r in (0, H - 1) or c in (0, W - 1)) and g[r][c] == 0]
    seen = set(st)
    while st:
        y, x = st.pop()
        for dr, dc in N4:
            ny, nx = y + dr, x + dc
            if 0 <= ny < H and 0 <= nx < W and g[ny][nx] == 0 and (ny, nx) not in seen: seen.add((ny, nx)); st.append((ny, nx))
    res = []
    for col, cells in objs(g):
        hol = any(g[y][x] == 0 and (y, x) not in seen for y in range(bbox(cells)[0], bbox(cells)[2] + 1) for x in range(bbox(cells)[1], bbox(cells)[3] + 1))
        tb = any(r in (0, H - 1) or c in (0, W - 1) for r, c in cells); res.append((col, cells, hol, tb))
    return res


def tf9(g):
    o = hollow_objs(g); out = [[0, 0], [0, 0]]
    for col, cells, hol, tb in o: out[0 if tb else 1][0 if hol else 1] += 1
    return [[cp(v) for v in r] for r in out]
rule("border_touch_by_hollow_contingency_2x2", "A 2x2 digit table of the objects (4-connected, same colour): row 0 = objects touching the grid edge, row 1 = objects not touching it; column 0 = hollow objects (a bounding-box cell that is empty and cannot be reached from the grid edge through empty cells), column 1 = solid objects; counts capped at 9.",
     mk(f4, tf9), tf9, digits=True)


def tf10(g):
    cnt = [0] * 4
    for col, cells in objs(g): n = len(cells); cnt[0 if n == 1 else 1 if n <= 4 else 2 if n <= 9 else 3] += 1
    return [[6 + i] + [5] * cp(cnt[i]) + [0] * (9 - cp(cnt[i])) for i in range(4)]
rule("size_class_bar_chart_with_legend_column", "A 4-row bar chart of the objects (4-connected, same colour) by cell count: rows in order for sizes 1, 2-4, 5-9 and 10 or more, column 0 a legend cell of colour 6, 7, 8, 9 for the four rows, then a bar of colour 5 in columns 1-9 as long as the object count in that class (capped at 9).",
     mk(lambda r: f2(r, True), tf10), tf10)


def tf11(g):
    os_ = objs(g); idx = {}
    for i, (c, cells) in enumerate(os_):
        for p in cells: idx[p] = i
    pairs = set()
    for p, i in idx.items():
        for dr, dc in N4:
            j = idx.get((p[0] + dr, p[1] + dc))
            if j is not None and j != i: pairs.add((min(i, j), max(i, j)))
    cs = cols_of(g)
    if not pairs: return None
    m = [[0] * len(cs) for _ in cs]
    for i, j in pairs:
        a, b = cs.index(os_[i][0]), cs.index(os_[j][0]); m[a][b] += 1
        if a != b: m[b][a] += 1
    return [[cp(v) for v in r] for r in m]
rule("colour_adjacency_pair_count_matrix", "A symmetric square digit matrix over the colours present (ascending, same order for rows and columns): the cell for colours a and b is the number of pairs of objects (4-connected, same colour), one of colour a and one of colour b, that share an edge (the diagonal counts touching pairs of the same colour), capped at 9.",
     mk(f5, tf11), tf11, digits=True)


def tf12(g):
    sh = {}
    for col, cells in objs(g):
        r0, c0 = bbox(cells)[:2]; sh.setdefault(col, set()).add(frozenset((r - r0, c - c0) for r, c in cells))
    return [[col, cp(len(sh[col]))] for col in sorted(sh)]
rule("distinct_shape_count_per_colour_table", "One row per colour present (ascending), two columns: the colour, then the digit count of different shapes among its objects (4-connected, same colour; two objects are the same shape if their cells match after moving them to a common corner, turned or flipped copies count as different), capped at 9.",
     mk(f1(True), tf12), tf12, digits=True)


def tf14(g):
    out = []
    for col, cells in objs(g):
        r0, c0, r1, c1 = bbox(cells); out.append([col, cp(r1 - r0 + 1), cp(c1 - c0 + 1)])
    return out
rule("object_height_width_digit_table", "One row per object (4-connected, same colour) in reading order of its first cell: its colour, the digit height of its bounding box and the digit width of its bounding box (each capped at 9).",
     mk(f2, tf14), tf14, digits=True)


def tf15(g):
    H, W = dims(g); out = []
    for col in cols_of(g):
        row = [0, 0, 0]
        for r in range(H):
            for c in range(W):
                if g[r][c] == col: row[0 if c < W // 3 else 1 if c < 2 * W // 3 else 2] += 1
        out.append([cp(v) for v in row])
    return out
rule("colour_by_vertical_third_count_table", "Cut the grid into three vertical thirds (column cuts at w//3 and 2w//3); one row per colour present (ascending), three digit columns with the number of that colour's cells in the left, middle and right third, each capped at 9.",
     mk(f3((.03, .07)), tf15), tf15, digits=True)


def tf16(g):
    H, W = dims(g); nb = -(-H // 5); cs = cols_of(g); out = [[0] * len(cs) for _ in range(nb)]
    for col, cells in objs(g): out[cells[0][0] // 5][cs.index(col)] += 1
    return [[cp(v) for v in r] for r in out]
rule("row_band_by_colour_object_count_table", "Cut the grid into row-bands of 5 rows (the last may be shorter); one table row per band from the top, one column per colour present (ascending); each cell is the digit count of that colour's objects (4-connected, same colour) whose first cell in reading order lies in the band, capped at 9.",
     mk(f1(), tf16), tf16, digits=True)


def tf18(g):
    out = []
    for col in cols_of(g):
        cs = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v == col]; r0, c0, r1, c1 = bbox(cs)
        out.append([col, r0 // 3, c0 // 3, r1 // 3, c1 // 3])
    return out
rule("colour_extent_table_in_thirds", "One row per colour present (ascending), five columns: the colour, then floor(r/3) for its topmost row, floor(c/3) for its leftmost column, floor(r/3) for its bottom row and floor(c/3) for its rightmost column (the grid is at most 29 cells a side so every value is at most 9).",
     mk(f1(), tf18), tf18, digits=True)


def tf19(g):
    rows = []
    for col in cols_of(g):
        rows.append((min(c for row in g for c, v in enumerate(row) if v == col), col))
    return [[col, c // 3] for c, col in sorted(rows)]
rule("colours_ordered_by_leftmost_column_table", "One row per colour present, ordered by the column of its leftmost cell from left to right (a tie goes to the smaller colour value), two columns: the colour, then the digit floor(c/3) of that leftmost column.",
     mk(f1(), tf19), tf19, digits=True)


def tf21(g):
    os_ = objs(g); ns = [len(c) for _, c in os_]
    return [[cp(len(os_)), len(cols_of(g)), cp(max(ns)), cp(min(ns))]]
rule("scene_summary_four_digits", "A single row of four digits: the number of objects (4-connected, same colour, capped 9), the number of distinct colours, the cell count of the largest object (capped 9) and the cell count of the smallest object (capped 9).",
     mk(f2, tf21), tf21, digits=True)


def tf22(g):
    out = []
    for col in cols_of(g):
        ns = [len(c) for k, c in objs(g) if k == col]
        out.append([cp(sum(1 for n in ns if n == 1)), cp(sum(1 for n in ns if 2 <= n <= 4)), cp(sum(1 for n in ns if n >= 5))])
    return out
rule("colour_by_size_class_count_table", "One row per colour present (ascending), three digit columns counting that colour's objects (4-connected, same colour) with exactly 1 cell, with 2 to 4 cells, and with 5 or more cells; counts capped at 9.",
     mk(f2, tf22), tf22, digits=True)


def tf23(g):
    o = hollow_objs(g); out = []
    for col in cols_of(g):
        out.append([col, cp(sum(1 for c, _, h, _ in o if c == col and h)), cp(sum(1 for c, _, h, _ in o if c == col and not h))])
    return out
rule("colour_hollow_solid_count_table", "One row per colour present (ascending), three columns: the colour, the digit count of its hollow objects (a bounding-box cell that is empty and cannot be reached from the grid edge through empty cells), and the digit count of its solid objects; counts capped at 9.",
     mk(f4, tf23), tf23, digits=True)


def tf24(g):
    out = []
    for col in cols_of(g):
        row = [0, 0, 0]
        for k, cells in objs(g):
            if k == col:
                r0, c0, r1, c1 = bbox(cells); h, w = r1 - r0 + 1, c1 - c0 + 1; row[0 if w > h else 1 if h > w else 2] += 1
        out.append([cp(v) for v in row])
    return out
rule("colour_by_orientation_count_table", "One row per colour present (ascending), three digit columns counting that colour's objects (4-connected, same colour) whose bounding box is wider than tall, taller than wide, and square; counts capped at 9.",
     mk(f2, tf24), tf24, digits=True)


def tf25(g):
    o = hollow_objs(g); out = []
    for col in cols_of(g):
        out.append([col, cp(sum(1 for c, _, _, t in o if c == col and t)), cp(sum(1 for c, _, _, t in o if c == col and not t))])
    return out
rule("colour_border_touch_count_table", "One row per colour present (ascending), three columns: the colour, the digit count of its objects (4-connected, same colour) that touch the grid edge, and the digit count that do not; counts capped at 9.",
     mk(f4, tf25), tf25, digits=True)


def tf26(g):
    H, W = dims(g); out = []
    for col in cols_of(g):
        cs = [(r, c) for r in range(H) for c in range(W) if g[r][c] == col]
        out.append([int(any(r == 0 for r, _ in cs)), int(any(r == H - 1 for r, _ in cs)), int(any(c == 0 for _, c in cs)), int(any(c == W - 1 for _, c in cs))])
    return out
rule("colour_by_grid_edge_contact_table", "One row per colour present (ascending), four columns for the top, bottom, left and right edge of the grid, each holding the digit 1 if the colour has a cell on that edge and 0 otherwise.",
     mk(f6, tf26), tf26, digits=True)


def tf28(g):
    os_ = sorted(objs(g), key=lambda o: (-len(o[1]), o[1][0]))
    return [[col] * cp(len(c)) + [0] * (9 - cp(len(c))) for col, c in os_]
rule("objects_by_size_bar_chart", "One row per object (4-connected, same colour), ordered by cell count from most to least (a tie goes to the object whose first cell comes first in reading order), as a bar in the object's colour of length equal to its cell count (capped at 9) starting at the left of a row of width 9, padded with empty cells.",
     mk(f1(), tf28), tf28)


def tf30(g):
    H, W = dims(g); out = blank(2, W)
    for c in range(W):
        col = [g[r][c] for r in range(H) if g[r][c]]; out[0][c] = cp(len(col)); out[1][c] = col[0] if col else 0
    return out
rule("column_count_and_top_colour_two_rows", "Output two rows as wide as the input: the top row holds each column's number of non-empty cells as a digit (capped at 9), the bottom row holds the colour of that column's topmost non-empty cell (empty if the column has none).",
     mk(f3((.03, .08)), tf30), tf30, digits=True)


def tf31(g):
    H, W = dims(g)
    return [[cp(sum(1 for v in g[r] if v)), next((v for v in g[r] if v), 0)] for r in range(H)]
rule("row_count_and_left_colour_two_columns", "Output two columns as tall as the input: the left column holds each row's number of non-empty cells as a digit (capped at 9), the right column holds the colour of that row's leftmost non-empty cell (empty if the row has none).",
     mk(f3((.03, .08)), tf31), tf31, digits=True)


def tf33(g):
    H, W = dims(g); mh, mw = H // 2, W // 2
    q = [sum(1 for r in range(a, b) for c in range(c0, c1) if g[r][c]) for (a, b) in ((0, mh), (mh, H)) for (c0, c1) in ((0, mw), (mw, W))]
    order = sorted(range(4), key=lambda i: (-q[i], i)); rk = [0] * 4
    for n, i in enumerate(order): rk[i] = n + 1
    return [rk[:2], rk[2:]]
rule("quadrant_density_rank_2x2", "Split the grid into four quadrants (row cut at h//2, column cut at w//2); the 2x2 output ranks them by number of non-empty cells, 1 for the most filled to 4 for the least filled, with ties going to the earlier quadrant in the order top-left, top-right, bottom-left, bottom-right.",
     mk(f3(), tf33), tf33, digits=True)


def tf34(g):
    H, W = dims(g); out = blank(3, 3)
    for col, cells in objs(g): out[ninth(cells[0][0], H)][ninth(cells[0][1], W)] += 1
    return [[cp(v) for v in r] for r in out]
rule("ninth_object_count_digit_grid", "Divide the grid into a 3x3 block of ninths (row cuts at h//3 and 2h//3, column cuts at w//3 and 2w//3); each output cell is the digit count of objects (4-connected, same colour) whose first cell in reading order lies in that ninth, capped at 9.",
     mk(f1(), tf34), tf34, digits=True)


def tf35(g):
    H, W = dims(g); sets = [[set() for _ in range(3)] for _ in range(3)]
    for r in range(H):
        for c in range(W):
            if g[r][c]: sets[ninth(r, H)][ninth(c, W)].add(g[r][c])
    return [[len(s) for s in row] for row in sets]
rule("ninth_distinct_colour_count_grid", "Divide the grid into a 3x3 block of ninths (row cuts at h//3 and 2h//3, column cuts at w//3 and 2w//3); each output cell is the digit number of distinct non-empty colours inside that ninth.",
     mk(f3((.04, .12)), tf35), tf35, digits=True)


def tf41(g):
    cs = cols_of(g); rows = [{v for v in row if v} for row in g]
    return [[cp(sum(1 for s in rows if a in s and b in s)) for b in cs] for a in cs]
rule("colour_row_cooccurrence_matrix", "A square digit matrix over the colours present (ascending, same order for rows and columns): the cell for colours a and b is the number of grid rows containing both a and b (on the diagonal, the number of rows containing a), capped at 9.",
     mk(f6, tf41), tf41, digits=True)


def tf46(g):
    out = []
    for col, cells in objs(g):
        r0, c0, r1, c1 = bbox(cells); h, w = r1 - r0 + 1, c1 - c0 + 1
        if h < 5 or w < 5 or len(cells) != 2 * (h + w) - 4: continue
        inner = [g[r][c] for r in range(r0 + 1, r1) for c in range(c0 + 1, c1) if g[r][c]]
        if not inner or len(set(inner)) != 1 or inner[0] == col: return None
        out.append([col, inner[0], cp(len(inner))])
    return out or None
rule("frame_contents_colour_and_count_table", "One row per hollow rectangular frame (its border colour is the colour of its top-left corner), ordered by the frame's top-left corner in reading order: the border colour, the colour of the cells inside it, and the digit count of those inside cells (capped at 9).",
     mk(f7, tf46), tf46, digits=True)
