# b087_keyed_summaries.py -- A KEY SAYS WHAT TO SUMMARISE. The top rows hold a small key (a colour cell, a digit,
# two cells, a glyph, a marked position, a block of cells) above a full-width grey (5) separator row; below it
# lies the field (scattered cells, objects, objects with holes, touching blobs, quadrant/band-structured cells).
# The output is a count, ratio, histogram, table or legend selected by the key. Fields never use grey; every
# bar is padded with black to a stated width; zero-capable bars start with a grey 5 marker cell.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

SEP = 5
PC = [1, 2, 3, 4, 6, 7, 8, 9]
HC = [1, 2, 3, 4, 6, 7, 9]
N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


# ---------------- output encoders and layout ----------------
def _bar(n, w, col): return [[col] * n + [0] * (w - n)] if 0 < n < w else None
def _mbar(n, w, col): return [[5] + [col] * n + [0] * (w - n)] if 0 <= n <= w else None
def _dig(n): return [[n, 0]] if 1 <= n <= 9 else None
def _pair(n): return [[n // 10, 0, n % 10]] if 0 <= n <= 99 else None


def asm(keyrows, field):
    W = len(field[0]); rows = [list(r) + [0] * (W - len(r)) for r in keyrows]
    return rows + [[SEP] * W] + field


def zones(g):
    rs = next(r for r, row in enumerate(g) if all(v == SEP for v in row)); return g[:rs], g[rs + 1:]


def compact(row):
    out = []
    for v in row:
        if v == 0: break
        out.append(v)
    return out


def cnt_of(field):
    c = counts(field); c.pop(0, None); return c


def objs(field): return [(field[o[0][0]][o[0][1]], sorted(o)) for o in objects(field, 0, conn8=False)]


def fdims(rng, even=False, mult=None, bigp=0.5):
    if rng.random() < bigp: H, W = rng.randint(8, 21), rng.randint(21, 30)
    else: H, W = rng.randint(6, 13), rng.randint(7, 14)
    if even: H -= H % 2; W -= W % 2
    if mult: H = max(2 * mult, H - H % mult)
    return H, W


# ---------------- field builders ----------------
def sc_counts(rng, H, W, spec):
    f = blank(H, W)
    for c, n in spec.items(): sprinkle(rng, f, n, c)
    return f


def sc_s(rng, ncol=(2, 4), cmax=12, even=False, lo=1):
    H, W = fdims(rng, even); cols = rng.sample(PC, rng.randint(*ncol)); spec = {c: rng.randint(lo, cmax) for c in cols}
    return sc_counts(rng, H, W, spec), spec


def sc_o(rng, ncol=3, kr=(3, 7), nr=(1, 8), cols=PC):
    for _ in range(200):
        H, W = fdims(rng); k = rng.randint(*kr) + (3 if W >= 21 else 0)
        pal = rng.sample(cols, ncol); f = blank(H, W)
        if place_shapes(rng, f, [random_shape(rng, rng.randint(*nr)) for _ in range(k)], [rng.choice(pal) for _ in range(k)], margin=1) is None: continue
        return f
    raise RuntimeError("sc_o")


def sc_hollow(rng):
    for _ in range(200):
        H, W = fdims(rng); k = rng.randint(2, 4) + (3 if W >= 21 else 0); shapes = []
        for _ in range(k):
            a, b = rng.randint(3, 6), rng.randint(3, 6); inner = [(r, c) for r in range(1, a - 1) for c in range(1, b - 1)]; holes = []
            for _ in range(rng.randint(0, 3)):
                r, c = rng.choice(inner)
                if all(max(abs(r - x), abs(c - y)) > 1 for x, y in holes): holes.append((r, c))
            shapes.append([(r, c) for r in range(a) for c in range(b) if (r, c) not in holes])
        f = blank(H, W)
        if place_shapes(rng, f, shapes, [rng.choice(HC) for _ in range(k)], margin=1) is None: continue
        return f
    raise RuntimeError("hollow")


def enclosed(f):
    H, W = dims(f); seen = set(); st = [(r, c) for r in range(H) for c in range(W) if f[r][c] == 0 and (r in (0, H - 1) or c in (0, W - 1))]
    seen.update(st)
    while st:
        y, x = st.pop()
        for dy, dx in N4:
            n = (y + dy, x + dx)
            if 0 <= n[0] < H and 0 <= n[1] < W and f[n[0]][n[1]] == 0 and n not in seen: seen.add(n); st.append(n)
    gg = blank(H, W)
    for r in range(H):
        for c in range(W):
            if f[r][c] == 0 and (r, c) not in seen: gg[r][c] = 1
    return components(gg, 1, conn8=False)


def region_owner(f, reg):
    for r, c in reg:
        for dy, dx in N4:
            y, x = r + dy, c + dx
            if 0 <= y < len(f) and 0 <= x < len(f[0]) and f[y][x]: return (y, x)
    return None


def sc_mosaic(rng):
    for _ in range(100):
        H, W = fdims(rng, bigp=0.5); k = min(8, rng.randint(3, 6) + (2 if W >= 21 else 0)); pal = rng.sample(PC, k)
        f = blank(H, W); cells_ = {}
        free = [(r, c) for r in range(H) for c in range(W)]
        for col, (r, c) in zip(pal, rng.sample(free, k)): f[r][c] = col
        target = int(H * W * rng.uniform(0.35, 0.65))
        for _ in range(target * 6):
            if sum(1 for row in f for v in row if v) >= target: break
            r, c = rng.choice([(r, c) for r in range(H) for c in range(W) if f[r][c]])
            dy, dx = rng.choice(N4); y, x = r + dy, c + dx
            if 0 <= y < H and 0 <= x < W and f[y][x] == 0: f[y][x] = f[r][c]
        return f
    raise RuntimeError("mosaic")


def sc_q(rng):
    H, W = fdims(rng, even=True); f = blank(H, W); hh, hw = H // 2, W // 2
    for q in range(4):
        r0, c0 = (q // 2) * hh, (q % 2) * hw
        for col in rng.sample(PC, rng.randint(1, 3)):
            sub = blank(hh, hw); sprinkle(rng, sub, rng.randint(1, 6), col)
            for r in range(hh):
                for c in range(hw):
                    if sub[r][c] and f[r0 + r][c0 + c] == 0: f[r0 + r][c0 + c] = col
    return f


def sc_band3(rng, vertical=False):
    H, W = fdims(rng, mult=3); f = blank(H, W); bh = H // 3
    for b in range(3):
        for col in rng.sample(PC, rng.randint(1, 3)):
            sub = blank(bh, W); sprinkle(rng, sub, rng.randint(1, 7), col)
            for r in range(bh):
                for c in range(W):
                    if sub[r][c] and f[b * bh + r][c] == 0: f[b * bh + r][c] = col
    return transpose(f) if vertical else f


def sc_edge(rng):
    H, W = fdims(rng); f = blank(H, W)
    for col in rng.sample(PC, rng.randint(2, 3)):
        for _ in range(rng.randint(2, 9)):
            side = rng.randrange(4)
            r, c = (0, rng.randrange(W)) if side == 0 else (H - 1, rng.randrange(W)) if side == 1 else (rng.randrange(H), 0) if side == 2 else (rng.randrange(H), W - 1)
            f[r][c] = col
        sprinkle(rng, f, rng.randint(0, 5), col)
    return f


def sc_rows(rng):
    H, W = fdims(rng); f = blank(H, W)
    for r in range(H):
        for c in rng.sample(range(W), min(W, rng.choice((0, 1, 2, 3, 4, 5)))): f[r][c] = rng.choice(PC)
    return f


SHAPES15 = {'dot': [(0, 0)], 'domino': [(0, 0), (0, 1)], 'square': [(0, 0), (0, 1), (1, 0), (1, 1)], 'bar3': [(0, 0), (1, 0), (2, 0)], 'ell': [(0, 0), (1, 0), (1, 1)]}
def norm(cells_):
    r0 = min(r for r, _ in cells_); c0 = min(c for _, c in cells_); return tuple(sorted((r - r0, c - c0) for r, c in cells_))


def sc_shapes(rng):
    for _ in range(200):
        H, W = fdims(rng); k = rng.randint(5, 9) + (4 if W >= 21 else 0); names = list(SHAPES15); sh = [SHAPES15[rng.choice(names)] for _ in range(k)]
        pal = rng.sample([c for c in PC if c != 8], 3); f = blank(H, W)
        if place_shapes(rng, f, sh, [rng.choice(pal) for _ in range(k)], margin=1) is None: continue
        return f, names
    raise RuntimeError("shapes")


def KR(rule_name, desc, gi, tf, **kw):
    rule(rule_name, desc, gi, tf, **kw)


KZ = " The top rows hold the key; below the key is a full-width grey (5) separator row, and the field lies under it."
def key_field(g):
    k, f = zones(g); return k, f


# ================================================================== 1-5 key colour on scatter / objects
def gi1(rng):
    f, spec = sc_s(rng); return asm([[rng.choice(list(spec))]], f)
def tf1(g):
    k, f = key_field(g); return _bar(cnt_of(f).get(k[0][0], 0), 14, k[0][0])
rule("key_colour_cell_count_bar", "The key is one coloured cell; count the field cells of that colour and output one row: that many cells of that colour, then black, 14 cells wide in all." + KZ, gi1, tf1)

def gi2(rng):
    f = sc_o(rng); return asm([[rng.choice([c for c, _ in objs(f)])]], f)
def tf2(g):
    k, f = key_field(g); return _bar(sum(1 for c, _ in objs(f) if c == k[0][0]), 10, 2)
rule("key_colour_object_count_bar", "The key is one coloured cell; count the field's objects (4-connected, one colour) of that colour and output one row of 10 cells: that many red (2) cells, then black." + KZ, gi2, tf2)

def gi3(rng):
    f = sc_hollow(rng); return asm([[rng.choice([c for c, _ in objs(f)])]], f)
def tf3(g):
    k, f = key_field(g); n = 0
    for reg in enclosed(f):
        o = region_owner(f, reg)
        if o and f[o[0]][o[1]] == k[0][0]: n += 1
    return _dig(n)
rule("key_colour_objects_hole_count_digit", "The key is one coloured cell; count the enclosed black regions (not connected through black cells to the field border) that are walled in by objects of that colour, and output one row of two cells: the count as a colour value, then black." + KZ, gi3, tf3, digits=True)

def gi4(rng):
    f = sc_o(rng, nr=(1, 13)); return asm([[rng.choice([c for c, _ in objs(f)])]], f)
def tf4(g):
    k, f = key_field(g); s = [len(o) for c, o in objs(f) if c == k[0][0]]
    return _bar(max(s), 14, k[0][0]) if s else None
rule("key_colour_largest_object_size_bar", "The key is one coloured cell; find the largest object (4-connected) of that colour in the field and output one row: as many cells of that colour as it has cells, then black, 14 cells wide in all." + KZ, gi4, tf4)

def gi5(rng):
    f = sc_o(rng, ncol=2, kr=(3, 6)); return asm([[rng.choice([c for c, _ in objs(f)])]], f)
def tf5(g):
    k, f = key_field(g); ob = [o for c, o in objs(f) if c == k[0][0]]
    rows = [sum(1 for o in ob if any(r == y for r, _ in o)) for y in range(len(f))]
    return [[d, 0] for d in rows] if max(rows) <= 9 else None
rule("key_colour_objects_per_row_digit_column", "The key is one coloured cell; for every field row, top to bottom, count the objects (4-connected, one colour) of that colour having a cell in the row; output one row of two cells per field row: the count as a colour value (empty for 0), then black." + KZ, gi5, tf5, digits=True)

# ================================================================== 6-7, 21, 40 mosaic
def gi6(rng):
    f = sc_mosaic(rng); return asm([[rng.choice(sorted({v for r in f for v in r if v}))]], f)
def adjc(f, col):
    H, W = dims(f); cnt = {}
    for r in range(H):
        for c in range(W):
            if f[r][c] == col:
                for dy, dx in N4:
                    y, x = r + dy, c + dx
                    if 0 <= y < H and 0 <= x < W and f[y][x] and f[y][x] != col: cnt[f[y][x]] = cnt.get(f[y][x], 0) + 1
    return cnt
def tf6(g):
    k, f = key_field(g); cn = adjc(f, k[0][0])
    return [[d, 0] for d, _ in sorted(cn.items(), key=lambda kv: (-kv[1], kv[0]))] if cn else None
rule("key_colour_adjacent_colours_legend", "The key is one coloured cell; list the other colours that touch cells of that colour side to side, ordered by how many touching cell pairs they have with it (most first, ties by smaller colour value); output one row of two cells per listed colour: the colour, then black." + KZ, gi6, tf6, digits=True)

def gi7(rng):
    f = sc_mosaic(rng); a, b = rng.sample(sorted({v for r in f for v in r if v}), 2); return asm([[a, b]], f)
def tf7(g):
    k, f = key_field(g); a, b = k[0][:2]; return _mbar(adjc(f, a).get(b, 0), 14, 8)
rule("key_two_colours_touching_pairs_bar", "The key is two coloured cells a and b; count the side-by-side pairs of one cell of colour a and one cell of colour b in the field and output one row: a grey (5) marker, then that many cyan (8) cells, then black up to 14 cells after the marker." + KZ, gi7, tf7)

def tf21(g):
    k, f = key_field(g); a, b = k[0][:2]; H, W = dims(f); n = 0
    for r in range(H):
        for c in range(W):
            if f[r][c] == a and any(0 <= r + dy < H and 0 <= c + dx < W and f[r + dy][c + dx] == b for dy, dx in N4): n += 1
    return _mbar(n, 14, 3)
rule("key_first_colour_cells_touching_second_bar", "The key is two coloured cells a and b; count the cells of colour a that have a cell of colour b directly above, below, left or right, and output one row: a grey (5) marker, then that many green (3) cells, then black up to 14 cells after the marker." + KZ, gi7, tf21)

def tf40(g):
    k, f = key_field(g); return _dig(len(adjc(f, k[0][0])))
rule("key_colour_neighbour_colour_count_digit", "The key is one coloured cell; count how many different other colours touch cells of that colour side to side, and output one row of two cells: the count as a colour value, then black." + KZ, gi6, tf40, digits=True)

# ================================================================== 8-9 key digit thresholds
def gi8(rng):
    f = sc_o(rng, nr=(1, 8)); return asm([[rng.randint(1, 6)]], f)
def tf8(g):
    k, f = key_field(g); return _dig(sum(1 for _, o in objs(f) if len(o) >= k[0][0]))
rule("key_digit_objects_at_least_that_big_digit", "The key is one digit k (colour value); count the objects (4-connected, one colour) with k or more cells and output one row of two cells: the count as a colour value, then black." + KZ, gi8, tf8, digits=True)

def gi9(rng):
    f, spec = sc_s(rng, (3, 6), 8); return asm([[rng.randint(2, 6)]], f)
def tf9(g):
    k, f = key_field(g); return _dig(sum(1 for n in cnt_of(f).values() if n >= k[0][0]))
rule("key_digit_colours_with_that_many_cells_digit", "The key is one digit k (colour value); count the colours that cover k or more field cells and output one row of two cells: the count as a colour value, then black." + KZ, gi9, tf9, digits=True)

# ================================================================== 10 glyph statistic
GL = {'plus': {(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)}, 'x': {(0, 0), (0, 2), (1, 1), (2, 0), (2, 2)}, 'ring': {(r, c) for r in range(3) for c in range(3)} - {(1, 1)}}
def gi10(rng):
    f = sc_hollow(rng); name = rng.choice(list(GL)); key = [[8 if (r, c) in GL[name] else 0 for c in range(3)] for r in range(3)]
    return asm(key, f)
def tf10(g):
    k, f = key_field(g); sh = {(r, c) for r in range(3) for c in range(3) if k[r][c]}
    if sh == GL['plus']: n = sum(1 for r in f for v in r if v)
    elif sh == GL['x']: n = len(objs(f))
    elif sh == GL['ring']: n = len(enclosed(f))
    else: return None
    return _pair(n)
rule("key_glyph_picks_cells_objects_or_holes_digits", "The key is a 3x3 cyan (8) glyph: a plus asks for the number of coloured cells in the field, an X for the number of objects (4-connected, one colour), a ring for the number of enclosed black regions; output a 1x3 row: tens digit, black, units digit of that number, as colour values." + KZ, gi10, tf10, digits=True)

# ================================================================== 11, 29 edges
EDGE = {'top': (0, 1), 'bottom': (2, 1), 'left': (1, 0), 'right': (1, 2)}
def gi11(rng):
    f = sc_edge(rng); f = [[0 if v == 8 else v for v in r] for r in f]; p = rng.choice(list(EDGE.values())); key = blank(3, 3); key[p[0]][p[1]] = 8
    return asm(key, f)
def tf11(g):
    k, f = key_field(g); pos = [(r, c) for r in range(3) for c in range(3) if k[r][c]]
    if len(pos) != 1: return None
    edge = {v: n for n, v in EDGE.items()}[pos[0]]
    line = f[0] if edge == 'top' else f[-1] if edge == 'bottom' else [r[0] for r in f] if edge == 'left' else [r[-1] for r in f]
    return _bar(sum(1 for v in line if v), 30, 3)
rule("key_position_picks_edge_occupancy_bar", "The key is a 3x3 block holding one cyan (8) cell at top-middle, bottom-middle, left-middle or right-middle, naming the field's top row, bottom row, left column or right column; count the coloured cells in that line and output one row of 30 cells: that many green (3) cells, then black." + KZ, gi11, tf11)

def gi29(rng):
    f = sc_edge(rng); return asm([[rng.choice(sorted({v for r in f for v in r if v}))]], f)
def tf29(g):
    k, f = key_field(g); H, W = dims(f)
    return _bar(sum(1 for r in range(H) for c in range(W) if f[r][c] == k[0][0] and (r in (0, H - 1) or c in (0, W - 1))), 14, k[0][0])
rule("key_colour_cells_on_border_bar", "The key is one coloured cell; count the field cells of that colour lying on the field's outer border and output one row: that many cells of that colour, then black, 14 cells wide in all." + KZ, gi29, tf29)

# ================================================================== 12 pair (colour, n)
def gi12(rng):
    f = sc_o(rng, ncol=2, kr=(4, 8), nr=(1, 9)); c = rng.choice(sorted({c for c, _ in objs(f)}))
    n_ob = sum(1 for cc, _ in objs(f) if cc == c); return asm([[c, rng.randint(1, min(3, n_ob))]], f)
def tf12(g):
    k, f = key_field(g); c, n = k[0][:2]; ob = [o for cc, o in objs(f) if cc == c]
    ob.sort(key=lambda o: (-len(o), o[0]))
    return _dig(len(ob[n - 1])) if 1 <= n <= len(ob) else None
rule("key_colour_and_rank_object_size_digit", "The key is two cells: a colour c, then a digit n (colour value); order the objects (4-connected) of colour c from most to fewest cells (ties: the one whose topmost-then-leftmost cell comes first in reading order) and output one row of two cells: the cell count of the n-th one as a colour value, then black." + KZ, gi12, tf12, digits=True)

# ================================================================== 13, 14, 36, 47 regions
def hist(sub):
    cn = cnt_of(sub)
    if not cn or max(cn.values()) > 12: return None
    return [[c] * n + [0] * (12 - n) for c, n in sorted(cn.items())]
def gi13(rng): return asm([[rng.randint(1, 4)]], sc_q(rng))
def tf13(g):
    k, f = key_field(g); H, W = dims(f); q = k[0][0] - 1
    if not 0 <= q < 4: return None
    r0, c0 = (q // 2) * (H // 2), (q % 2) * (W // 2)
    return hist([row[c0:c0 + W // 2] for row in f[r0:r0 + H // 2]])
rule("key_colour_value_picks_quadrant_histogram", "The key is one colour whose value 1, 2, 3 or 4 names the quadrant of the (even-sized) field to tabulate: 1 top-left, 2 top-right, 3 bottom-left, 4 bottom-right; output one row per colour present in that quadrant, in increasing colour value, each a left-aligned bar of that colour as long as its cell count in the quadrant, padded with black to 12 cells." + KZ, gi13, tf13, digits=True)
def gi14(rng): return asm([[rng.randint(1, 3)]], sc_band3(rng))
def tf14(g):
    k, f = key_field(g); H = len(f); b = k[0][0] - 1
    return hist(f[b * (H // 3):(b + 1) * (H // 3)]) if 0 <= b < 3 else None
rule("key_digit_picks_row_band_histogram", "The key is one digit d (1, 2 or 3, colour value) naming the d-th of three equally tall horizontal bands of the field counted from the top; output one row per colour present in that band, in increasing colour value, each a left-aligned bar of that colour as long as its cell count in the band, padded with black to 12 cells." + KZ, gi14, tf14, digits=True)
def gi36(rng): return asm([[rng.randint(1, 3)]], sc_band3(rng, True))
def tf36(g):
    k, f = key_field(g); W = len(f[0]); b = k[0][0] - 1
    return hist([row[b * (W // 3):(b + 1) * (W // 3)] for row in f]) if 0 <= b < 3 and W % 3 == 0 else None
rule("key_digit_picks_column_band_histogram", "The key is one digit d (1, 2 or 3, colour value) naming the d-th of three equally wide vertical bands of the field counted from the left; output one row per colour present in that band, in increasing colour value, each a left-aligned bar of that colour as long as its cell count in the band, padded with black to 12 cells." + KZ, gi36, tf36, digits=True)
def gi47(rng):
    key = blank(2, 2); p = rng.choice(((0, 0), (0, 1), (1, 0), (1, 1))); key[p[0]][p[1]] = 8
    f = [[0 if v == 8 else v for v in r] for r in sc_q(rng)]; return asm(key, f)
def tf47(g):
    k, f = key_field(g); H, W = dims(f); pos = [(r, c) for r in range(2) for c in range(2) if k[r][c]]
    if len(pos) != 1: return None
    r0, c0 = pos[0][0] * (H // 2), pos[0][1] * (W // 2)
    return _bar(sum(1 for row in f[r0:r0 + H // 2] for v in row[c0:c0 + W // 2] if v), 24, 3)
rule("key_marked_position_quadrant_cell_count_bar", "The key is a 2x2 block with one cyan (8) cell whose position (top-left, top-right, bottom-left, bottom-right) names a quadrant of the (even-sized) field; count the coloured cells in that quadrant and output one row of 24 cells: that many green (3) cells, then black." + KZ, gi47, tf47)

# ================================================================== 15 shape class table
def gi15(rng):
    f, names = sc_shapes(rng); n = rng.choice(names); sh = SHAPES15[n]
    h = max(r for r, _ in sh) + 1; key = blank(h, 3)
    for r, c in sh: key[r][c] = 8
    return asm(key, f)
def tf15(g):
    k, f = key_field(g); ks = norm([(r, c) for r, row in enumerate(k) for c, v in enumerate(row) if v]); per = {}
    for col, o in objs(f):
        if norm(o) == ks: per[col] = per.get(col, 0) + 1
    if not per or max(per.values()) > 8: return None
    return [[c] + [8] * n + [0] * (9 - n) for c, n in sorted(per.items())]
rule("key_shape_class_count_per_colour_table", "The key is a small cyan (8) shape; count, per colour, the field objects with exactly that shape (same orientation); output one row per colour that has any, in increasing colour value: a swatch cell of the colour, then that many cyan (8) cells, then black, 10 cells wide in all." + KZ, gi15, tf15, digits=True)

# ================================================================== 16 ratio
def gi16(rng):
    for _ in range(100):
        H, W = fdims(rng); a, b = rng.sample(PC, 2); cb = rng.randint(1, 4); q = rng.randint(1, 7); ca = cb * q + rng.randint(0, cb - 1)
        if ca + cb > H * W // 2: continue
        spec = {a: ca, b: cb}
        for c in rng.sample([x for x in PC if x not in (a, b)], rng.randint(0, 2)): spec[c] = rng.randint(1, 6)
        return asm([[a, b]], sc_counts(rng, H, W, spec))
    raise RuntimeError
def tf16(g):
    k, f = key_field(g); a, b = k[0][:2]; cn = cnt_of(f)
    return _dig(cn.get(a, 0) // cn[b]) if cn.get(b) else None
rule("key_two_colours_cell_ratio_floor_digit", "The key is two coloured cells a and b; divide the number of field cells of colour a by the number of cells of colour b, drop the fraction, and output one row of two cells: the quotient as a colour value, then black." + KZ, gi16, tf16, digits=True)

# ================================================================== 17 top-k
def gi17(rng):
    for _ in range(100):
        f, spec = sc_s(rng, (4, 7), 12, lo=1)
        if len(set(spec.values())) == len(spec):
            f = [[0 if v == 8 else v for v in r] for r in f]; return asm([[8] * rng.randint(1, 4)], f)
    raise RuntimeError
def tf17(g):
    k, f = key_field(g); n = len(compact(k[0])); cn = sorted(cnt_of(f).items(), key=lambda kv: (-kv[1], kv[0]))[:n]
    return [[c, 0] for c, _ in cn] if cn else None
rule("key_cell_count_is_number_of_top_colours_listed", "The key is a row of k cyan (8) cells; list the k colours with the most field cells (ties: smaller colour value first), most frequent first; output one row of two cells per listed colour: the colour, then black." + KZ, gi17, tf17, digits=True)

# ================================================================== 19, 20 key colour per column / row
def gi19(rng):
    f, spec = sc_s(rng, (2, 3), 14); return asm([[rng.choice(list(spec))]], f)
def tf19(g):
    k, f = key_field(g); c = k[0][0]; row = [min(9, sum(1 for r in range(len(f)) if f[r][x] == c)) for x in range(len(f[0]))]
    return [row] if any(row) else None
rule("key_colour_cells_per_column_digit_row", "The key is one coloured cell; output one row as wide as the field: under each field column, the number of cells of that colour in the column (at most 9 shown) as a colour value, black for 0." + KZ, gi19, tf19, digits=True)
def tf20(g):
    k, f = key_field(g); c = k[0][0]; W = len(f[0])
    out = [[c] * n + [0] * (W - n) for n in (sum(1 for v in row if v == c) for row in f)]
    return out if any(any(r) for r in out) else None
rule("key_colour_cells_per_row_bar_chart", "The key is one coloured cell; output a grid as big as the field where each row holds a left-aligned bar of that colour as long as the number of cells of that colour in the same field row, black elsewhere." + KZ, gi19, tf20)

# ================================================================== 23 k-th most frequent
def gi23(rng):
    for _ in range(100):
        f, spec = sc_s(rng, (3, 6), 12)
        if len(set(spec.values())) == len(spec): return asm([[rng.randint(1, min(3, len(spec)))]], f)
    raise RuntimeError
def tf23(g):
    k, f = key_field(g); cn = sorted(cnt_of(f).items(), key=lambda kv: (-kv[1], kv[0])); d = k[0][0]
    return [[cn[d - 1][0], 0], [0, cn[d - 1][0]]] if 1 <= d <= len(cn) else None
rule("key_digit_picks_nth_most_frequent_colour_swatch", "The key is one digit d (colour value); find the d-th most frequent colour in the field (d=1 is the most frequent; ties: smaller colour value first) and output a 2x2 swatch with that colour on the main diagonal and black elsewhere." + KZ, gi23, tf23, digits=True)

# ================================================================== 25, 39 rows
def gi25(rng): return asm([[rng.randint(1, 4)]], sc_rows(rng))
def tf25(g):
    k, f = key_field(g); return _bar(sum(1 for row in f if sum(1 for v in row if v) >= k[0][0]), 30, 6)
rule("key_digit_rows_with_at_least_that_many_cells_bar", "The key is one digit k (colour value); count the field rows holding k or more coloured cells and output one row of 30 cells: that many magenta (6) cells, then black." + KZ, gi25, tf25, digits=True)
def gi39(rng):
    f = sc_rows(rng); H = len(f); a = rng.randint(1, H); b = min(H, a + rng.randint(0, 2))
    return asm([[min(a, 9), min(b, 9)]], f)
def tf39(g):
    k, f = key_field(g); a, b = k[0][:2]
    return _mbar(sum(1 for row in f[a - 1:b] for v in row if v), 20, 3) if 1 <= a <= b <= len(f) else None
rule("key_two_digits_row_range_cell_count_bar", "The key is two digits a and b (colour values, a at most b); count the coloured cells in field rows a to b inclusive, counting rows from 1 at the top, and output one row: a grey (5) marker, then that many green (3) cells, then black up to 20 cells after the marker." + KZ, gi39, tf39, digits=True)

# ================================================================== 27, 38, 41, 43, 45 objects
def gi_ko(rng, nr=(1, 8), kr=(3, 7), ncol=2):
    f = sc_o(rng, ncol=ncol, kr=kr, nr=nr); return asm([[rng.choice(sorted({c for c, _ in objs(f)}))]], f)
def tf27(g):
    k, f = key_field(g); c = k[0][0]; s = [len(o) for cc, o in objs(f) if cc == c]
    rows = [sum(1 for x in s if x == 1), sum(1 for x in s if 2 <= x <= 3), sum(1 for x in s if x >= 4)]
    return [[c] * n + [0] * (10 - n) for n in rows] if max(rows) < 10 and any(rows) else None
rule("key_colour_objects_by_size_class_bars", "The key is one coloured cell; count the objects (4-connected) of that colour with 1 cell, with 2 or 3 cells and with 4 or more cells; output three rows of 10 cells, top to bottom, left-aligned bars of that colour with those counts, padded with black." + KZ, lambda rng: gi_ko(rng, kr=(4, 8)), tf27)
def tf38(g):
    k, f = key_field(g); c = k[0][0]; return _mbar(sum(len(o) for cc, o in objs(f) if cc == c and len(o) >= 3), 20, c)
rule("key_colour_sum_of_big_objects_bar", "The key is one coloured cell; add up the cells of all objects (4-connected) of that colour that have 3 or more cells and output one row: a grey (5) marker, then that many cells of that colour, then black up to 20 cells after the marker." + KZ, lambda rng: gi_ko(rng, nr=(1, 8)), tf38)
def tf41(g):
    k, f = key_field(g); c = k[0][0]; s = sorted((len(o) for cc, o in objs(f) if cc == c), reverse=True)
    return [[c] * n + [0] * (10 - n) for n in s] if s and s[0] < 10 and len(s) <= 8 else None
rule("key_colour_object_sizes_descending_bar_rows", "The key is one coloured cell; output one row per object (4-connected) of that colour, largest first (equal sizes adjacent), each a left-aligned bar of that colour as long as the object's cell count, padded with black to 10 cells." + KZ, lambda rng: gi_ko(rng, nr=(1, 9)), tf41)
def tf43(g):
    k, f = key_field(g); c = k[0][0]; s = [len(o) for cc, o in objs(f) if cc == c]
    return _dig(sum(s) // len(s)) if s else None
rule("key_colour_mean_object_size_floor_digit", "The key is one coloured cell; divide the total number of cells of that colour's objects (4-connected) by the number of those objects, drop the fraction, and output one row of two cells: the result as a colour value, then black." + KZ, lambda rng: gi_ko(rng, nr=(1, 9)), tf43, digits=True)
def gi45(rng):
    f = sc_o(rng, nr=(1, 9)); return asm([[rng.randint(1, 4)]], f)
def tf45(g):
    k, f = key_field(g); s = sorted((len(o) for _, o in objs(f)), reverse=True); d = k[0][0]
    return _dig(s[d - 1]) if 1 <= d <= len(s) else None
rule("key_digit_picks_nth_largest_object_size_digit", "The key is one digit d (colour value); sort the sizes of all objects (4-connected, one colour) from largest to smallest, equal sizes each listed, and output one row of two cells: the d-th size as a colour value, then black." + KZ, gi45, tf45, digits=True)

# ================================================================== 28, 31, 34 scatter
def gi28(rng):
    for _ in range(100):
        f, spec = sc_s(rng, (3, 5), 13)
        if len(spec) >= 2:
            a, b = rng.sample(list(spec), 2); return asm([[a, b]], f)
    raise RuntimeError
def tf28(g):
    k, f = key_field(g); a, b = k[0][:2]; cn = cnt_of(f); return _mbar(max(0, cn.get(a, 0) - cn.get(b, 0)), 14, a)
rule("key_first_minus_second_colour_cells_clipped_bar", "The key is two coloured cells a and b; output one row: a grey (5) marker, then max(cells of a minus cells of b, 0) cells of colour a, then black up to 14 cells after the marker." + KZ, gi28, tf28)
def gi31(rng):
    f, spec = sc_s(rng, (3, 7), 5); return asm([[rng.randint(1, 5)]], f)
def tf31(g):
    k, f = key_field(g); d = k[0][0]; cs = sorted(c for c, n in cnt_of(f).items() if n == d)
    return [[5] + cs + [0] * (8 - len(cs))] if len(cs) <= 8 else None
rule("key_digit_colours_appearing_exactly_that_often_row", "The key is one digit k (colour value); output one row of 9 cells: a grey (5) marker, then the colours that cover exactly k field cells in increasing colour value, then black." + KZ, gi31, tf31, digits=True)
def gi34(rng):
    f, spec = sc_s(rng, (2, 3), 30, lo=1); return asm([[rng.choice(list(spec))]], f)
def tf34(g):
    k, f = key_field(g); c = k[0][0]; n = cnt_of(f).get(c, 0)
    return [[c if (n >> i) & 1 else 0 for i in range(5, -1, -1)]] if 1 <= n <= 62 else None
rule("key_colour_cell_count_binary_row", "The key is one coloured cell; write the number of field cells of that colour in binary (at most 62) as a row of 6 cells, most significant bit left: a cell of that colour for each 1 bit and black for each 0 bit." + KZ, gi34, tf34)
