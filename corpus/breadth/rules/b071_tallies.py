# b071_tallies.py -- TALLY SHEETS: scattered items on a board are counted into a sheet whose layout is the
# point (row order, grouping in fives, binary, running totals, corner or margin placement, two-board differences,
# corrections to an existing sheet). Generators are spread over several scene families (scatter boards, object
# boards, quadrant boards, two-panel boards, board-with-sheet, margin boards, frames).
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

KC = [1, 2, 3, 4, 6, 7, 8, 9]     # item colours (never grey 5)
K8 = [1, 2, 3, 4, 6, 7, 9]


def _hw(rng, lo=10, hi=20, p=0.45):
    if rng.random() < p: return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _place(rng, g, col, n, pred=None, tries=300):
    H, W = dims(g)
    for _ in range(n):
        for _t in range(tries):
            r, c = rng.randrange(H), rng.randrange(W)
            if pred and not pred(r, c): continue
            if all(g[y][x] == 0 for y in range(max(0, r - 1), min(H, r + 2)) for x in range(max(0, c - 1), min(W, c + 2))):
                g[r][c] = col; break
        else: return False
    return True


def _items(rng, H, W, counts, pred=None):
    g = blank(H, W)
    for col, n in counts.items():
        if not _place(rng, g, col, n, pred): return None
    return g


def _cnt(g):
    d = {}
    for row in g:
        for v in row:
            if v: d[v] = d.get(v, 0) + 1
    return d


def _order(g):
    seen = []
    for row in g:
        for v in row:
            if v and v not in seen: seen.append(v)
    return seen


def _pad(rows):
    w = max(1, max(len(r) for r in rows))
    return [r + [0] * (w - len(r)) for r in rows]


def _sgen(lo=1, hi=8, kmin=2, kmax=5, cols=KC):
    def gen(rng):
        for _ in range(60):
            H, W = _hw(rng)
            cs = rng.sample(cols, rng.randint(kmin, kmax))
            g = _items(rng, H, W, {c: rng.randint(lo, hi) for c in cs})
            if g: return g
        raise RuntimeError
    return gen


# ============================== scatter-board sheets (10 rules) ==============================
def t1(g):
    cn = _cnt(g); return _pad([[c] * cn[c] for c in _order(g)])
rule("tally_row_per_colour_first_appearance", "Each item (single cell) adds one mark to its colour's row: rows run top to bottom in the order the colours first appear when the board is read row by row from the top-left, each row holds one cell of its colour per item, left-aligned, padded with 0 to the longest row.", _sgen(), t1)

def t2(g):
    cn = _cnt(g); return _pad([[c] * cn[c] for c in sorted(cn, key=lambda c: (-cn[c], c))])
rule("tally_rows_sorted_count_desc_tie_colour", "One row per colour with one cell of that colour per item, left-aligned and padded with 0: rows are sorted by item count from most to fewest, and colours with equal counts go in ascending colour value.", _sgen(1, 6), t2)

def t3(g):
    cn = _cnt(g); cs = sorted(cn); h = max(cn.values())
    out = blank(h, len(cs))
    for i, c in enumerate(cs):
        for j in range(cn[c]): out[h - 1 - j][i] = c
    return out
rule("tally_columns_per_colour_ascending", "One column per colour, left to right in ascending colour value, each column a bar of that colour with one cell per item, standing on the bottom row of an output as tall as the largest count, padded with 0 above.", _sgen(1, 8), t3)

def _fives(c, n):
    out = []
    for i in range(n):
        if i and i % 5 == 0: out.append(0)
        out.append(c)
    return out
def t4(g):
    cn = _cnt(g); return _pad([_fives(c, cn[c]) for c in _order(g)])
rule("tally_marks_in_fives_with_gap", "Rows follow the colours' first appearance in row-major reading order; each row has one cell of its colour per item, written in groups of five with a single 0 cell between consecutive groups, left-aligned and padded with 0 to the longest row.", _sgen(3, 14, 2, 4), t4)

def t6(g):
    cn = _cnt(g); tot = 0; rows = []
    for c in _order(g):
        tot += cn[c]; rows.append([c] * tot)
    return _pad(rows)
rule("tally_running_total_down_the_sheet", "Rows follow the colours' first appearance in row-major reading order, and row i is a bar in colour i's colour whose length is the total number of items of colours 1..i (the running total including that colour), left-aligned and padded with 0.", _sgen(1, 5, 2, 5), t6)

def t7(g):
    cn = _cnt(g); return _pad([[c, 0] + [5] * cn[c] for c in sorted(cn)])
rule("tally_grey_marks_after_colour_key", "One row per colour in ascending colour value: the first cell is the colour itself, then one 0 cell, then one grey 5 mark per item of that colour; rows are left-aligned and padded with 0 to the longest row.", _sgen(1, 8), t7)

def t8(g):
    cn = _cnt(g); return [[c, cn[c]] for c in sorted(cn)]
rule("tally_digit_pair_per_colour", "A two-column sheet with one row per colour in ascending colour value: the left cell is the colour, the right cell has the colour value equal to the number of items of that colour.", _sgen(1, 9, 2, 5), t8, digits=True)

def t35(g):
    cn = _cnt(g); return _pad([[5] * (cn[c] // 5) + [c] * (cn[c] % 5) for c in sorted(cn)])
rule("tally_full_fives_as_single_grey_cells", "One row per colour in ascending colour value, written as one grey 5 cell for every complete five items followed by one cell of the item colour for each leftover item (count mod 5), left-aligned and padded with 0 to the longest row.", _sgen(1, 14, 2, 4), t35)

def t36(g):
    cn = _cnt(g); return [[c if (cn[c] >> b) & 1 else 0 for b in (3, 2, 1, 0)] for c in sorted(cn)]
rule("tally_count_in_binary_four_bits", "One output row of four cells per colour in ascending colour value, spelling that colour's item count in binary with the most significant bit leftmost: a 1 bit is a cell of the item colour, a 0 bit is a 0 cell.", _sgen(1, 15, 2, 5), t36)

def g39(rng):
    for _ in range(60):
        H, W = _hw(rng); cs = rng.sample([1, 2, 3, 4], rng.randint(2, 3))
        g = _items(rng, H, W, {c: rng.randint(1, 7) for c in cs})
        if g: return g
    raise RuntimeError
def t39(g):
    cn = _cnt(g); return _pad([[i] * cn[i] if cn.get(i) else [5] for i in (1, 2, 3, 4)])
rule("tally_fixed_four_rows_absent_colour_grey_dot", "The output always has four rows for colours 1, 2, 3, 4 in that order, each holding one cell of its colour per item, left-aligned and padded with 0; a colour with no items gets a single grey 5 cell instead (items of other colours do not occur).", g39, t39, digits=True)


# ============================== own-generator scenes ==============================
# --- legend filter: legend row, grey separator, board
def g10(rng):
    for _ in range(60):
        H, W = _hw(rng, 11, 20); lc = rng.sample(K8, rng.randint(2, 4)); ex = rng.sample([c for c in K8 if c not in lc], rng.randint(1, 2))
        g = _items(rng, H - 2, W, {**{c: rng.randint(1, 6) for c in lc}, **{c: rng.randint(1, 4) for c in ex}})
        if not g: continue
        cols = sorted(rng.sample(range(W), len(lc))); head = [0] * W
        for c, v in zip(cols, rng.sample(lc, len(lc))): head[c] = v
        return [head, [5] * W] + g
    raise RuntimeError
def t10(g):
    leg = [v for v in g[0] if v]; cn = _cnt(g[2:])
    return _pad([[c] * cn.get(c, 0) for c in leg])
rule("tally_only_legend_colours_in_legend_order", "The top row is a legend of colours, a full grey 5 row separates it from the board, and each legend colour gets an output row (legend left to right) with one cell of that colour per board item of that colour, left-aligned and padded with 0; board items of colours missing from the legend are ignored.", g10, t10)

# --- items on the outer wall only
def g11(rng):
    for _ in range(60):
        H, W = _hw(rng); cs = rng.sample(K8, rng.randint(2, 4)); g = blank(H, W)
        edge = lambda r, c: r in (0, H - 1) or c in (0, W - 1)
        inner = lambda r, c: not edge(r, c)
        if all(_place(rng, g, c, rng.randint(1, 4), edge) and _place(rng, g, c, rng.randint(0, 5), inner) for c in cs): return g
    raise RuntimeError
def t11(g):
    H, W = dims(g); cn = {}
    for r in range(H):
        for c in range(W):
            if g[r][c] and (r in (0, H - 1) or c in (0, W - 1)): cn[g[r][c]] = cn.get(g[r][c], 0) + 1
    return _pad([[c] * cn[c] for c in sorted(cn)]) if cn else None
rule("tally_only_items_on_the_outer_border", "Only items lying on the outermost ring of the grid (first or last row, first or last column) are counted; the output has one row per colour that has such items, in ascending colour value, with one cell of that colour per border item, left-aligned and padded with 0; interior items are ignored.", g11, t11)

# --- items inside a grey frame
def g41(rng):
    for _ in range(60):
        H, W = _hw(rng, 12, 20); h, w = rng.randint(7, min(12, H - 2)), rng.randint(7, min(12, W - 2))
        r, c = rng.randint(0, H - h), rng.randint(0, W - w); g = blank(H, W); rect(g, r, c, r + h - 1, c + w - 1, 5, fill=False)
        cs = rng.sample(K8, rng.randint(2, 4)); ins = lambda y, x: r < y < r + h - 1 and c < x < c + w - 1
        out = lambda y, x: not (r - 1 <= y <= r + h and c - 1 <= x <= c + w)
        if all(_place(rng, g, k, rng.randint(1, 3), ins) and _place(rng, g, k, rng.randint(0, 4), out) for k in cs): return g
    raise RuntimeError
def t41(g):
    cells_ = cells(g, lambda v: v == 5); r0, c0, r1, c1 = bbox(cells_); cn = {}
    for r in range(r0 + 1, r1):
        for c in range(c0 + 1, c1):
            if g[r][c]: cn[g[r][c]] = cn.get(g[r][c], 0) + 1
    return _pad([[c] * cn[c] for c in sorted(cn)]) if cn else None
rule("tally_only_items_inside_the_grey_frame", "A grey 5 rectangular frame sits on the board; only items strictly inside it are counted, giving one output row per colour found inside in ascending colour value, with one cell of that colour per inside item, left-aligned and padded with 0; items outside the frame are ignored.", g41, t41)

# --- two-colour vote with footer
def g46(rng):
    for _ in range(60):
        H, W = _hw(rng); a, b = rng.sample(KC, 2); na = rng.randint(1, 8); nb = na if rng.random() < 0.25 else rng.randint(1, 8)
        g = _items(rng, H, W, {a: na, b: nb} if rng.random() < 0.5 else {b: nb, a: na})
        if g: return g
    raise RuntimeError
def t46(g):
    cn = _cnt(g); o = _order(g)
    if len(o) != 2: return None
    a, b = o; w = max(cn.values())
    win = a if cn[a] > cn[b] else b if cn[b] > cn[a] else 5
    return _pad([[a] * cn[a], [b] * cn[b], [win] * w])
rule("tally_two_colour_vote_with_winner_footer", "The board holds items of exactly two colours; row 0 is the colour that appears first in row-major reading with one cell per item, row 1 is the other colour likewise, left-aligned and padded with 0, and a footer row as wide as the longer bar is filled with the colour that has more items, or grey 5 if the counts tie.", g46, t46)

# --- countdown sheet
def g37(rng):
    for _ in range(60):
        H, W = _hw(rng, 11, 20); m = rng.randint(2, 8); k = rng.randint(1, m + 2)
        g = _items(rng, H - 2, W, {c: n for c, n in zip(rng.sample(K8, min(3, k)), [k // 3 + (1 if i < k % 3 else 0) for i in range(3)]) if n})
        if g: return [[5] * m + [0] * (W - m), [8] * W] + g
    raise RuntimeError
def t37(g):
    k = sum(1 for row in g[2:] for v in row if v); m = sum(1 for v in g[0] if v == 5); out = copy(g)
    for i in range(max(0, m - k), m): out[0][i] = 0
    return out
rule("tally_countdown_sheet_loses_one_mark_per_item", "Row 0 holds a run of grey 5 marks from the left edge, a full row of 8 separates it from the board, and the board holds single-cell items; one mark is erased from the right end of the run for every item on the board, stopping when no marks remain; the board is unchanged.", g37, t37)

# --- remove small objects and write how many went
def g49(rng):
    for _ in range(80):
        H, W = _hw(rng, 10, 20); g = blank(H - 1, W); n = rng.randint(4, 9) * (2 if H * W > 400 else 1)
        shs = [random_shape(rng, rng.randint(1, 5)) for _ in range(n)]
        if not place_shapes(rng, g, shs, [rng.choice(K8) for _ in shs], margin=1): continue
        return g + [[0] * W]
    raise RuntimeError
def t49(g):
    out = copy(g); n = 0
    for comp in objects(g[:-1], bg=0, conn8=False):
        if len(comp) <= 2:
            n += 1
            for r, c in comp: out[r][c] = 0
    if n == 0 or n > len(g[0]): return None
    for i in range(n): out[-1][i] = 5
    return out
rule("erase_small_objects_and_bar_their_number", "Objects are 4-connected groups of one colour on a board whose last row is empty; every object of 1 or 2 cells is erased and the number of erased objects is written as a bar of grey 5 cells in the last row from its left edge; larger objects stay.", g49, t49)


# ============================== object boards (7 rules) ==============================
def _objgen(maker, nlo=4, nhi=9, cols=K8):
    def gen(rng):
        for _ in range(80):
            H, W = _hw(rng); g = blank(H, W); n = rng.randint(nlo, nhi) * (2 if H * W > 400 else 1)
            shs = [maker(rng) for _ in range(n)]
            if place_shapes(rng, g, shs, [rng.choice(cols[:rng.randint(2, len(cols))]) if False else rng.choice(cols) for _ in shs], margin=1): return g
        raise RuntimeError
    return gen

def _colgen(maker, ncol=(2, 4), nlo=4, nhi=9):
    def gen(rng):
        for _ in range(80):
            H, W = _hw(rng); g = blank(H, W); n = rng.randint(nlo, nhi) * (2 if H * W > 400 else 1)
            cs = rng.sample(KC, rng.randint(*ncol)); shs = [maker(rng) for _ in range(n)]
            if place_shapes(rng, g, shs, [rng.choice(cs) for _ in shs], margin=1): return g
        raise RuntimeError
    return gen

def t12(g):
    rows = []
    for c in _order(g): rows.append([c] * max(len(k) for k in components(g, c, conn8=False)))
    return _pad(rows)
rule("tally_largest_object_of_each_colour", "Rows follow the colours' first appearance in row-major reading order; each row has one cell of its colour per cell of that colour's largest 4-connected object (other objects of the colour are ignored), left-aligned and padded with 0.", _colgen(lambda rng: random_shape(rng, rng.randint(1, 6)), (2, 4), 4, 8), t12)

def t13(g):
    rows = []
    for c in sorted({v for r in g for v in r if v}, reverse=True): rows.append([c] * len(components(g, c, conn8=False)))
    return _pad(rows)
rule("tally_object_count_per_colour_desc_value", "Each 4-connected same-colour object counts as one mark regardless of its size: one row per colour in descending colour value, with one cell of that colour per object, left-aligned and padded with 0.", _colgen(lambda rng: random_shape(rng, rng.randint(1, 5)), (2, 4), 5, 10), t13)

def _mk14(rng):
    k = rng.choice('sdLq')
    if k == 's': return [(0, 0)]
    if k == 'd': return rng.choice([[(0, 0), (0, 1)], [(0, 0), (1, 0)]])
    if k == 'L': return rng.choice([[(0, 0), (0, 1), (1, 0)], [(0, 0), (0, 1), (1, 1)], [(0, 0), (1, 0), (1, 1)], [(0, 1), (1, 0), (1, 1)]])
    return [(0, 0), (0, 1), (1, 0), (1, 1)]
def t14(g):
    cl = [0, 0, 0, 0]
    for o in objects(g, bg=0, conn8=False):
        n = len(o)
        if n > 4 or (n == 3 and (bbox(o)[2] - bbox(o)[0], bbox(o)[3] - bbox(o)[1]) != (1, 1)): return None
        cl[n - 1] += 1
    return _pad([[5] * n for n in cl])
rule("tally_by_shape_class_single_domino_l_square", "Objects are 4-connected single-colour groups; the output has four rows in fixed order: single cells, dominoes (2 cells, either direction), bent three-cell L pieces, and 2x2 squares, each row holding one grey 5 mark per object of that class regardless of the object's colour, left-aligned and padded with 0.", _colgen(_mk14, (2, 5), 5, 10), t14)

def _mk15(rng):
    k = rng.choice('hvs'); n = rng.randint(2, 4)
    if k == 'h': return [(0, j) for j in range(n)]
    if k == 'v': return [(j, 0) for j in range(n)]
    n = rng.randint(2, 3); return [(i, j) for i in range(n) for j in range(n)]
def t15(g):
    cl = [0, 0, 0]
    for o in objects(g, bg=0, conn8=False):
        r0, c0, r1, c1 = bbox(o)
        cl[0 if r0 == r1 else 1 if c0 == c1 else 2] += 1
    return _pad([[5] * n for n in cl])
rule("tally_horizontal_vertical_bars_and_squares", "Objects are straight bars of 2-4 cells or solid squares of 2x2 or 3x3 in any colour; the output has three rows in fixed order, horizontal bars, vertical bars, squares, each with one grey 5 mark per object of that class, left-aligned and padded with 0.", _colgen(_mk15, (2, 5), 5, 10), t15)

def t16(g):
    cl = [0, 0, 0, 0]
    for o in objects(g, bg=0, conn8=False): cl[min(len(o), 4) - 1] += 1
    return _pad([[5] * n for n in cl])
rule("tally_objects_by_size_class_one_two_three_four_plus", "Objects are 4-connected single-colour groups; the output has four rows for objects of 1 cell, 2 cells, 3 cells and 4 or more cells in that order, each with one grey 5 mark per object of the class, left-aligned and padded with 0.", _colgen(lambda rng: random_shape(rng, rng.randint(1, 6)), (2, 5), 5, 10), t16)

def _mk17(rng):
    h, w = rng.randint(3, 5), rng.randint(3, 5)
    return [(i, j) for i in range(h) for j in range(w) if rng.random() < 2 or True] if rng.random() < 0.5 else [(i, j) for i in range(h) for j in range(w) if i in (0, h - 1) or j in (0, w - 1)]
def t17(g):
    cl = [0, 0]
    for o in objects(g, bg=0, conn8=False):
        r0, c0, r1, c1 = bbox(o); cl[0 if len(o) == (r1 - r0 + 1) * (c1 - c0 + 1) else 1] += 1
    return _pad([[5] * n for n in cl])
rule("tally_solid_versus_hollow_rectangles", "Objects are rectangles of 3-5 cells a side, either solid or a hollow one-cell-wide ring, in any colour; the output has two rows, solid rectangles first and hollow rectangles second, each with one grey 5 mark per rectangle, left-aligned and padded with 0.", _colgen(_mk17, (2, 4), 3, 6), t17)

def g18(rng):
    for _ in range(80):
        H, W = _hw(rng); g = blank(H, W); n = rng.randint(4, 9) * (2 if H * W > 400 else 1)
        shs = [random_shape(rng, rng.randint(1, 5)) for _ in range(n)]
        if place_shapes(rng, g, shs, [rng.choice(KC) for _ in shs], margin=1): return g
    raise RuntimeError
def t18(g):
    cl = [0, 0]
    for o in objects(g, bg=0, conn8=False): cl[0 if g[o[0][0]][o[0][1]] in (1, 2, 3) else 1] += 1
    return _pad([[5] * n for n in cl])
rule("tally_colours_one_to_three_versus_rest_objects", "Objects are 4-connected single-colour groups; the output has two rows, first the objects whose colour value is 1, 2 or 3, second all other objects, each with one grey 5 mark per object, left-aligned and padded with 0.", g18, t18, digits=True)


# ============================== quadrant boards (3 rules) ==============================
def _qgen(colour_of, nmax=9):
    def gen(rng):
        for _ in range(80):
            H, W = 2 * rng.randint(5, 15), 2 * rng.randint(5, 15)
            if rng.random() < 0.45: H, W = 2 * rng.randint(11, 15), 2 * rng.randint(11, 15)
            g = blank(H, W); ok = True
            for qr in (0, 1):
                for qc in (0, 1):
                    pred = lambda r, c, qr=qr, qc=qc: (r >= H // 2) == bool(qr) and (c >= W // 2) == bool(qc)
                    for col, n in colour_of(rng):
                        ok = ok and _place(rng, g, col, n, pred)
            if ok and any(g[r][c] for r in range(H) for c in range(W)): return g
        raise RuntimeError
    return gen
def _quad(g, want=None):
    H, W = dims(g); q = [[0, 0], [0, 0]]
    for r in range(H):
        for c in range(W):
            if g[r][c] and (want is None or g[r][c] == want): q[r >= H // 2][c >= W // 2] += 1
    return q
rule("tally_per_quadrant_digit_sheet", "The board is split into four equal quadrants; the output is a 2x2 sheet in the same layout where each cell has the colour value equal to the number of items (single cells of any colour) in that quadrant (at most 9).", _qgen(lambda rng: [(rng.choice(K8), rng.randint(0, 6))]), lambda g: _quad(g), digits=True)
def t20(g):
    q = _quad(g); out = blank(2, 18)
    for i in (0, 1):
        for j in (0, 1):
            for k in range(q[i][j]): out[i][9 * j + k] = 5
    return out
rule("tally_per_quadrant_bars_in_two_by_nine_slots", "The board is split into four equal quadrants; the output has two rows of 18 cells, each quadrant owning a 9-cell slot in the same layout (top-left, top-right, bottom-left, bottom-right), filled from the slot's left end with one grey 5 mark per item (single cells of any colour) in that quadrant, the rest 0.", _qgen(lambda rng: [(rng.choice(K8), rng.randint(0, 6))]), t20)
rule("tally_only_colour_two_per_quadrant_digits", "The board is split into four equal quadrants; the output is a 2x2 sheet in the same layout where each cell has the colour value equal to the number of colour-2 items in that quadrant; items of other colours are ignored.", _qgen(lambda rng: [(2, rng.randint(0, 5)), (rng.choice([1, 3, 4, 6]), rng.randint(0, 4))]), lambda g: _quad(g, 2), digits=True)


# ============================== two-panel boards (4 rules) ==============================
def _twogen(cols, lo=0, hi=7):
    def gen(rng):
        for _ in range(80):
            if rng.random() < 0.45: w, h = rng.randint(10, 14), rng.randint(6, 30)
            else: w, h = rng.randint(5, 9), rng.randint(6, 14)
            cs = rng.sample(cols, rng.randint(2, 4)); L = _items(rng, h, w, {c: rng.randint(lo, hi) for c in cs}); R = _items(rng, h, w, {c: rng.randint(lo, hi) for c in cs})
            if L and R: return [a + [5] + b for a, b in zip(L, R)]
        raise RuntimeError
    return gen
def _split(g):
    W = len(g[0]); sep = next(c for c in range(W) if all(r[c] == 5 for r in g))
    return [r[:sep] for r in g], [r[sep + 1:] for r in g]
def t24(g):
    L, R = map(_cnt, _split(g)); rows = []
    for c in sorted(set(L) | set(R)): rows.append([c] * max(0, L.get(c, 0) - R.get(c, 0)))
    return _pad(rows) if any(rows) else None
rule("tally_left_minus_right_clipped_at_zero", "Two equal boards are separated by a full grey 5 column; the output has one row per colour present in either board, in ascending colour value, with one cell of that colour for each item by which the left board's count exceeds the right board's (a row is all 0 when left is not larger), left-aligned and padded with 0.", _twogen(KC, 0, 7), t24)
def t25(g):
    L, R = map(_cnt, _split(g)); rows = []
    for c in sorted(set(L) | set(R)):
        d = L.get(c, 0) - R.get(c, 0)
        if d: rows.append([c, 0] + [3 if d > 0 else 4] * abs(d))
    return _pad(rows) if rows else None
rule("tally_signed_difference_marks_by_side", "Two equal boards are separated by a full grey 5 column; for every colour whose counts differ the output has a row (ascending colour value) of the colour, a 0 cell, then |left - right| marks that are colour 3 when the left board has more and colour 4 when the right board has more; colours with equal counts get no row; rows are left-aligned and padded with 0.", _twogen([1, 2, 6, 7, 8, 9], 0, 7), t25)
def t26(g):
    L, R = map(_cnt, _split(g)); cs = sorted(set(L) | set(R))
    wl = max([1] + [L.get(c, 0) for c in cs]); wr = max([1] + [R.get(c, 0) for c in cs]); rows = []
    for c in cs:
        a, b = L.get(c, 0), R.get(c, 0)
        rows.append([0] * (wl - a) + [c] * a + [5] + [c] * b + [0] * (wr - b))
    return rows
rule("tally_butterfly_left_and_right_boards", "Two equal boards are separated by a full grey 5 column; the output has one row per colour present in either board in ascending colour value: the left board's count as cells of that colour right-aligned against a central grey 5 cell, and the right board's count as cells left-aligned after it, each side as wide as its largest count (at least 1) and padded with 0.", _twogen(KC, 0, 7), t26)
def t27(g):
    L, R = map(_cnt, _split(g)); rows = []
    for c in sorted(set(L) | set(R)): rows.append(_fives(c, L.get(c, 0) + R.get(c, 0)))
    return _pad(rows)
rule("tally_sum_of_both_boards_in_fives", "Two equal boards are separated by a full grey 5 column; the output has one row per colour present in either board in ascending colour value, holding that colour's total over both boards as cells in groups of five separated by a single 0 cell, left-aligned and padded with 0.", _twogen(KC, 0, 7), t27)


# ============================== board-with-sheet (3 rules) and corner/margin placements ==============================
def _sheetgen(mode):
    def gen(rng):
        for _ in range(80):
            H, W = (rng.randint(21, 30), rng.randint(10, 30)) if rng.random() < 0.5 else (rng.randint(12, 20), rng.randint(10, 20))
            pal = rng.sample(K8, 5); g = blank(H, W); g[5] = [8] * W
            if mode == 'append':
                S = pal[:rng.randint(2, 3)]; O = pal[3:5][:rng.randint(1, 2)]
                for i, c in enumerate(S): g[i][0] = c; m = rng.randint(0, 3); g[i][1:1 + m] = [5] * m
                counts = {**{c: rng.randint(1, 3) for c in S}, **{c: rng.randint(1, 3) for c in O}}
            elif mode == 'fix':
                S = pal[:rng.randint(2, 4)]
                for i, c in enumerate(S): g[i][0] = c; m = rng.randint(0, 5); g[i][1:1 + m] = [5] * m
                counts = {c: rng.randint(0, 5) for c in S}; counts.update({c: rng.randint(1, 3) for c in pal[4:5] if rng.random() < 0.5})
            else:
                j = rng.randint(1, 3); S = pal[:j]
                for i, c in enumerate(S): g[i][0] = c; m = rng.randint(0, 3); g[i][1:1 + m] = [5] * m
                counts = {c: rng.randint(1, 4) for c in pal[:j + rng.randint(1, 5 - j)]}
            sub = _items(rng, H - 6, W, {c: n for c, n in counts.items() if n})
            if sub: return g[:6] + sub
        raise RuntimeError
    return gen
def _srows(g): return [(i, g[i][0]) for i in range(5) if g[i][0]]
def _bcount(g): return _cnt(g[6:])
def t30(g):
    out = copy(g); cn = _bcount(g)
    for i, c in _srows(g):
        m = sum(1 for v in g[i][1:] if v == 5); n = cn.get(c, 0)
        for k in range(n): out[i][1 + m + k] = 5
    for r in range(6, len(g)):
        for q in range(len(g[0])):
            if g[r][q] in {c for _, c in _srows(g)}: out[r][q] = 0
    return out
rule("sheet_absorbs_items_of_its_colours_and_they_vanish", "The top five rows are a sheet: each used row starts with a colour cell followed by grey 5 marks, a full row of 8 separates it from the board; every board item whose colour has a sheet row is erased and one grey 5 mark per erased item is appended after that row's existing marks; items of colours without a sheet row stay.", _sheetgen('append'), t30)
def t31(g):
    out = copy(g); cn = _bcount(g)
    for i, c in _srows(g):
        for q in range(1, len(g[0])): out[i][q] = 0
        for q in range(cn.get(c, 0)): out[i][1 + q] = 5
    return out
rule("sheet_wrong_counts_rewritten_from_board", "The top five rows are a sheet: each used row starts with a colour cell followed by grey 5 marks claiming a count, a full row of 8 separates it from the board; each row's marks are rewritten to exactly the number of board items of that colour (rows already correct stay the same, a colour with no items keeps only its colour cell); the board is unchanged.", _sheetgen('fix'), t31)
def t32(g):
    out = copy(g); have = {c for _, c in _srows(g)}; cn = _bcount(g); nxt = next(i for i in range(5) if not g[i][0])
    for c in _order(g[6:]):
        if c in have: continue
        out[nxt][0] = c
        for q in range(cn[c]): out[nxt][1 + q] = 5
        nxt += 1
    return out
rule("sheet_gains_rows_for_missing_colours", "The top five rows are a sheet whose used rows start with a colour cell followed by grey 5 marks, a full row of 8 separates it from the board; every board colour without a sheet row gets a new row in the next empty sheet row, in order of first appearance reading the board row by row, written as its colour cell then one grey 5 mark per item of that colour; existing rows and the board are unchanged.", _sheetgen('missing'), t32)

def _corner(mode):
    def gen(rng):
        for _ in range(60):
            H, W = _hw(rng, 10, 20); cs = rng.sample(KC, rng.randint(2, 4))
            g = _items(rng, H, W, {c: rng.randint(1, 6) for c in cs})
            if g: return g
        raise RuntimeError
    return gen
def t28(g):
    out = copy(g); cn = _cnt(g)
    for i, c in enumerate(_order(g)):
        for j in range(cn[c]):
            if out[i][j] == 0: out[i][j] = c
    return out
rule("sheet_written_top_left_background_only", "Rows of marks (one per colour in order of first appearance in row-major reading, one cell of that colour per item) are written into the top-left corner starting at row 0 column 0, one sheet row per grid row; a mark is only drawn on a 0 cell, so items already there stay unchanged; the rest of the board is unchanged.", _corner(0), t28)
def t29(g):
    H, W = dims(g); out = copy(g); cn = _cnt(g)
    for i, c in enumerate(_order(g)):
        for j in range(cn[c]):
            if out[H - 1 - i][W - 1 - j] == 0: out[H - 1 - i][W - 1 - j] = c
    return out
rule("sheet_written_bottom_right_growing_upward", "Rows of marks (one per colour in order of first appearance in row-major reading, one cell of that colour per item) are written into the bottom-right corner: the first colour on the last grid row, the next on the row above, each row right-aligned to the last column; a mark is only drawn on a 0 cell, so existing items stay; the rest of the board is unchanged.", _corner(1), t29)
def t38(g):
    H, W = dims(g); out = copy(g); cn = _cnt(g)
    for j, c in enumerate(sorted(cn)):
        for i in range(cn[c]):
            if out[i][W - 1 - j] == 0: out[i][W - 1 - j] = c
    return out
rule("sheet_written_top_right_as_hanging_bars", "A bar per colour hangs from the top edge in the top-right corner: colours in ascending value fill columns from the last column leftward, each bar having one cell of that colour per item, starting at row 0 and going down; a mark is only drawn on a 0 cell, so existing items stay; the rest of the board is unchanged.", _corner(2), t38)


# ============================== margin sheets and frames (3 rules) ==============================
def gm(rng):
    for _ in range(60):
        H, W = _hw(rng); g = blank(H, W); n = rng.randint(6, 16) * (2 if H * W > 400 else 1)
        if all(_place(rng, g, rng.choice(K8), 1) for _ in range(n)): return g
    raise RuntimeError
def t42(g):
    H, W = dims(g); out = copy(g)
    for r in range(H):
        n = sum(1 for v in g[r] if v)
        for j in range(n):
            if out[r][W - 1 - j] == 0: out[r][W - 1 - j] = 5
    return out
rule("row_item_counts_marked_in_right_margin", "Each row's number of items is written as that many grey 5 marks packed against the right edge of the same row (drawn only on 0 cells, so items already there stay); the rest of the board is unchanged.", gm, t42)
def t43(g):
    H, W = dims(g); out = copy(g)
    for c in range(W):
        n = sum(1 for r in range(H) if g[r][c])
        for j in range(n):
            if out[H - 1 - j][c] == 0: out[H - 1 - j][c] = 5
    return out
rule("column_item_counts_marked_in_bottom_margin", "Each column's number of items is written as that many grey 5 marks stacked upward from the bottom edge of the same column (drawn only on 0 cells, so items already there stay); the rest of the board is unchanged.", gm, t43)

def g44(rng):
    for _ in range(80):
        H, W = _hw(rng, 12, 20); n = rng.randint(2, 4) * (2 if H * W > 400 else 1)
        bx = _bx(rng, H, W, [(rng.randint(5, 7), rng.randint(5, 7)) for _ in range(n)])
        if len(bx) < 2: continue
        g = blank(H, W)
        for r, c, h, w in bx:
            rect(g, r, c, r + h - 1, c + w - 1, rng.choice(K8[:-1] if False else [1, 2, 3, 4, 6, 7, 9]), fill=False)
            inner = [(y, x) for y in range(r + 1, r + h - 1) for x in range(c + 1, c + w - 1)]
            for y, x in rng.sample(inner, rng.randint(0, 5)): g[y][x] = 8
        _place(rng, g, 8, rng.randint(1, 4))
        return g
    raise RuntimeError
def _bx(rng, H, W, specs, margin=1):
    placed = []
    for h, w in specs:
        for _ in range(60):
            r, c = rng.randint(0, H - h), rng.randint(0, W - w)
            if all(r + h + margin <= r2 or r2 + h2 + margin <= r or c + w + margin <= c2 or c2 + w2 + margin <= c for r2, c2, h2, w2 in placed):
                placed.append((r, c, h, w)); break
    return placed
def t44(g):
    fr = []
    for col in {v for r in g for v in r} - {0, 8}:
        for comp in components(g, col, conn8=False):
            r0, c0, r1, c1 = bbox(comp)
            if r1 - r0 >= 2 and c1 - c0 >= 2 and len(comp) == 2 * (r1 - r0 + c1 - c0):
                fr.append((r0, c0, col, sum(1 for r in range(r0 + 1, r1) for c in range(c0 + 1, c1) if g[r][c] == 8)))
    if len(fr) < 2: return None
    return _pad([[col] * n for r0, c0, col, n in sorted(fr)])
rule("tally_items_held_in_each_frame_reading_order", "Boards hold hollow rectangular frames (one-cell rings of one colour, never 8) with colour-8 items inside some of them and loose colour-8 items outside; the output has one row per frame in reading order of the frames' top-left corners (top first, then left), holding one cell of the frame's colour per 8-cell inside it, left-aligned and padded with 0 (an empty frame gives an all-0 row); outside items are ignored.", g44, t44)
