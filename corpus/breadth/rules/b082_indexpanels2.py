# b082_indexpanels2.py -- A SMALL GRID INDEXES, ADDRESSES OR PROGRAMS A GRID OF PANELS, SECOND SET. Index zones are
# 1xN digit/colour rows (compact, or aligned one cell above each panel's first column), single cells, a 2x2 selector,
# an m x n mask block or a glyph; panels sit in a strip (horizontal or, by transposition, vertical) or an m x n grid.
# A grey (5) separator row/column system divides index zone from panels and panel from panel (panels never use 5).
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

SEP = 5
PC = [1, 2, 3, 4, 6, 7, 8, 9]


# ---------------- layout helpers ----------------
def pat(rng, ph, pw, cols, dens=0.55):
    for _ in range(50):
        p = [[rng.choice(cols) if rng.random() < dens else 0 for _ in range(pw)] for _ in range(ph)]
        n = sum(1 for r in p for v in r if v)
        if 3 <= n < ph * pw: return p
    return [[cols[0]] * pw for _ in range(ph)]


def pats(rng, n, ph, pw, cols, dens=0.55, single=False):
    out = []
    pal = rng.sample(cols, n) if single and len(cols) >= n else None
    while len(out) < n:
        p = pat(rng, ph, pw, [pal[len(out)]] if pal else cols, dens)
        if p not in out: out.append(p)
    return out


def hjoin(panels):
    out = [list(r) for r in panels[0]]
    for p in panels[1:]:
        for r in range(len(out)): out[r] += [SEP] + list(p[r])
    return out


def vjoin(panels):
    out = [list(r) for r in panels[0]]
    for p in panels[1:]:
        out.append([SEP] * len(out[0])); out += [list(r) for r in p]
    return out


def hjoin0(panels):
    out = [list(r) for r in panels[0]]
    for p in panels[1:]:
        for r in range(len(out)): out[r] += list(p[r])
    return out


def asm(idx_rows, body):
    W = len(body[0])
    rows = [list(r) + [0] * (W - len(r)) for r in idx_rows]
    return rows + [[SEP] * W] + body


def zones(g):
    rs = next(r for r, row in enumerate(g) if all(v == SEP for v in row))
    return g[:rs], g[rs + 1:]


def split_cols(body):
    W = len(body[0]); parts = []; cur = []
    for c in range(W):
        if all(row[c] == SEP for row in body):
            if cur: parts.append(cur); cur = []
        else: cur.append(c)
    if cur: parts.append(cur)
    return [[[row[c] for c in cs] for row in body] for cs in parts]


def split_rows(body):
    return [transpose(p) for p in split_cols(transpose(body))]


def parse_h(g):
    idx_rows, body = zones(g); return idx_rows, split_cols(body)


def compact(idx_row):
    out = []
    for v in idx_row:
        if v == 0: break
        out.append(v)
    return out


def aligned(idx_row, panels):
    pw = len(panels[0][0]); return [idx_row[i * (pw + 1)] for i in range(len(panels))]


def al_row(vals, pw):
    row = []
    for v in vals: row += [v] + [0] * pw
    return row[:-1] if row else row


def hdims(rng, square=False, nmin=3, nmax=5):
    if rng.random() < 0.6:
        N = rng.randint(max(nmin, 4), max(nmax, 5)); W = rng.randint(21, 30); pw = (W - (N - 1)) // N
        if pw < 3: N, pw = 4, 4
    else:
        N = rng.randint(nmin, min(nmax, 4)); pw = rng.randint(3, 4)
    ph = pw if square else rng.randint(3, 5)
    return N, ph, pw


def nfg(p): return sum(1 for r in p for v in r if v)
def dom(p):
    c = counts(p); c.pop(0, None)
    return min(c, key=lambda k: (-c[k], k)) if c else 0
def overlay(ps):
    out = blank(len(ps[0]), len(ps[0][0]))
    for p in ps:
        for r, row in enumerate(p):
            for c, v in enumerate(row):
                if v: out[r][c] = v
    return out
def rolled(p, d): return [row[-d:] + row[:-d] if d else row[:] for row in p]
def rotn(p, k):
    for _ in range(k % 4): p = rot90(p)
    return p


# ---------------- horizontal-strip scene R1 (index row above, N panels) ----------------
HS = " The top row holds the index; below a grey (5) separator row, N panels of equal size sit side by side divided by grey columns."
def R1(idx_fn, square=False, nmin=3, nmax=5, single=False, dens=0.55):
    def gi(rng):
        for _ in range(100):
            N, ph, pw = hdims(rng, square, nmin, nmax)
            ps = pats(rng, N, ph, pw, PC, dens, single)
            idx = idx_fn(rng, N, ph, pw, ps)
            if idx is None: continue
            kind, vals = idx
            row = vals if kind == 'c' else al_row(vals, pw)
            body = hjoin(ps)
            if len(row) <= len(body[0]): return asm([row], body)
        raise RuntimeError
    return gi


def V(gi): return lambda rng: transpose(gi(rng))
def vt(core): return lambda g: (lambda o: transpose(o) if o else None)(core(transpose(g)))


# ================================================================== R1 rules
def ix_pick(rng, N, ph, pw, ps):
    return 'c', [rng.randint(1, N) for _ in range(rng.randint(2, N + 1))]
def tf_pick(g):
    idx, ps = parse_h(g); v = compact(idx[0])
    return hjoin([ps[x - 1] for x in v]) if all(1 <= x <= len(ps) for x in v) else None
rule("index_row_digits_pick_panels_in_order", "A top-row index of digits (colour values, each 1 to N) names panels by their left-to-right number; output those panels joined side by side in the index's order (a panel may repeat) with grey (5) columns between them." + HS, R1(ix_pick), tf_pick, digits=True)

def ix_del(rng, N, ph, pw, ps):
    k = rng.randint(1, N - 1); d = set(rng.sample(range(N), k)); return 'a', [2 if i in d else 0 for i in range(N)]
def tf_del(g):
    idx, ps = parse_h(g); a = aligned(idx[0], ps); keep = [p for p, v in zip(ps, a) if v == 0]
    return hjoin(keep) if keep else None
rule("index_marks_panels_to_delete_rest_repacked", "A red (2) index cell sits above the first column of each panel to be deleted (other panels have an empty index cell); output the remaining panels joined left to right with grey (5) columns between them." + HS, R1(ix_del), tf_del)

def ix_min(rng, N, ph, pw, ps):
    return 'c', rng.sample(range(1, 10), N)
def tf_min(g):
    idx, ps = parse_h(g); v = compact(idx[0])[:len(ps)]; return ps[v.index(min(v))]
rule("index_smallest_digit_panel_output", "The index row holds N distinct digits (colour values), one per panel from left to right; output the panel whose digit is smallest." + HS, R1(ix_min), tf_min, digits=True)

def tf_sorted(g):
    idx, ps = parse_h(g); v = compact(idx[0])[:len(ps)]
    return hjoin([ps[i] for i in sorted(range(len(ps)), key=lambda i: v[i])])
rule("panels_sorted_by_index_digits_ascending", "The index row holds N distinct digits (colour values), one per panel from left to right; output the panels joined side by side ordered by their digit from smallest to largest, with grey (5) columns between them." + HS, R1(ix_min), tf_sorted, digits=True)

def ix_ov(rng, N, ph, pw, ps):
    k = rng.randint(2, N); return 'c', rng.sample(range(1, N + 1), k)
def tf_ov(g):
    idx, ps = parse_h(g); v = compact(idx[0]); return overlay([ps[x - 1] for x in v]) if all(1 <= x <= len(ps) for x in v) else None
rule("panels_overlaid_in_index_order_later_on_top", "The index row lists distinct panel numbers (digits as colour values, panels numbered 1 to N from the left); output one panel-sized grid made by overlaying the named panels in the listed order, a later panel's coloured cell replacing an earlier one's, black elsewhere." + HS, R1(ix_ov, single=True, dens=0.4), tf_ov, digits=True)

def ix_rec(rng, N, ph, pw, ps):
    v = [rng.choice(PC + [0, 0]) for _ in range(N)]
    return ('a', v) if any(v) else None
def tf_rec(g):
    idx, ps = parse_h(g); a = aligned(idx[0], ps)
    return hjoin([[[c if (c and v) else v for v in row] for row in p] for p, c in zip(ps, a)])
rule("index_colour_recolours_each_panel", "An index cell above the first column of each panel is either empty or a colour; every coloured cell of that panel is repainted in the index colour (empty index: panel unchanged); output the panels joined left to right with grey (5) columns, without the index." + HS, R1(ix_rec), tf_rec)

def ix_rot(rng, N, ph, pw, ps): return 'a', [rng.randint(0, 3) for _ in range(N)]
def tf_rot(g):
    idx, ps = parse_h(g); a = aligned(idx[0], ps); return hjoin([rotn(p, d) for p, d in zip(ps, a)])
rule("index_digit_rotates_each_panel", "Panels are square; the index cell above each panel's first column is empty (0) or a digit 1 to 3 (colour value); each panel is rotated that many quarter turns clockwise; output the panels joined left to right with grey (5) columns, without the index." + HS, R1(ix_rot, square=True), tf_rot, digits=True)

def ix_xy(rng, N, ph, pw, ps): return 'c', [rng.randint(1, ph), rng.randint(1, pw)]
def tf_xy(g):
    idx, ps = parse_h(g); r, c = compact(idx[0])[:2]
    return [[p[r - 1][c - 1] for p in ps]] if r <= len(ps[0]) and c <= len(ps[0][0]) else None
rule("coordinate_pair_reads_one_cell_per_panel", "The index holds two digits (colour values): a row number and a column number, both counted from 1 inside a panel; output one row listing, from left to right, the cell at that (row, column) of each panel." + HS, R1(ix_xy, dens=0.7), tf_xy, digits=True)

def ix_rowd(rng, N, ph, pw, ps): return 'a', [rng.randint(1, ph) for _ in range(N)]
def tf_rowd(g):
    idx, ps = parse_h(g); a = aligned(idx[0], ps)
    return [p[d - 1] for p, d in zip(ps, a)] if all(1 <= d <= len(ps[0]) for d in a) else None
rule("index_digit_picks_a_row_from_each_panel", "The index cell above each panel's first column is a digit (colour value) naming a row of that panel counted from 1 at its top; output the picked rows stacked top to bottom in panel order (leftmost panel on top), each as wide as a panel." + HS, R1(ix_rowd, dens=0.7), tf_rowd, digits=True)

def ix_roll(rng, N, ph, pw, ps): return 'a', [rng.randint(0, 3) for _ in range(N)]
def tf_roll(g):
    idx, ps = parse_h(g); a = aligned(idx[0], ps); return hjoin([rolled(p, d) for p, d in zip(ps, a)])
rule("index_digit_rolls_each_panel_right", "The index cell above each panel's first column is empty (0) or a digit 1 to 3 (colour value); each panel's rows are rolled right by that many cells, cells leaving on the right re-entering on the left; output the panels joined left to right with grey (5) columns, without the index." + HS, R1(ix_roll), tf_roll, digits=True)

def ix_sum(rng, N, ph, pw, ps): return 'c', [rng.randint(1, 9) for _ in range(rng.randint(2, 3))]
def tf_sum(g):
    idx, ps = parse_h(g); return ps[sum(compact(idx[0])) % len(ps)]
rule("index_digit_sum_mod_n_picks_panel", "The index holds 2 or 3 digits (colour values); add them, take the remainder after dividing by N (the panel count), and output the panel at that position counted from 0 on the left." + HS, R1(ix_sum), tf_sum, digits=True)

def ix_xor(rng, N, ph, pw, ps):
    d = set(rng.sample(range(N), 2)); return 'a', [2 if i in d else 0 for i in range(N)]
def tf_xor(g):
    idx, ps = parse_h(g); a = aligned(idx[0], ps); m = [p for p, v in zip(ps, a) if v == 2]
    if len(m) != 2: return None
    return [[8 if bool(x) != bool(y) else 0 for x, y in zip(r1, r2)] for r1, r2 in zip(*m)]
rule("two_marked_panels_xor_in_cyan", "Exactly two panels have a red (2) index cell above their first column; output one panel-sized grid with a cyan (8) cell wherever exactly one of those two panels is coloured and black elsewhere." + HS, R1(ix_xor), tf_xor)

def ix_grp(rng, N, ph, pw, ps):
    v = [rng.choice((1, 2, 3)) for _ in range(N)]
    return ('a', v) if len(set(v)) >= 2 and len(set(v)) < N else None
def tf_grp(g):
    idx, ps = parse_h(g); a = aligned(idx[0], ps); order = []
    for v in a:
        if v not in order: order.append(v)
    return hjoin([overlay([p for p, x in zip(ps, a) if x == v]) for v in order])
rule("same_index_colour_panels_overlaid_in_groups", "Each panel has a coloured index cell (blue 1, red 2 or green 3) above its first column; panels sharing an index colour are overlaid into one panel (the one further right on top where both are coloured); output one overlaid panel per index colour, in order of first appearance from the left, joined with grey (5) columns." + HS, R1(ix_grp, single=True, dens=0.4), tf_grp)


# ================================================================== R2: vertical stacks (the same scene transposed)
VS = " The left column holds the index; right of a grey (5) separator column, N panels of equal size are stacked top to bottom divided by grey rows."
def ix_2nd(rng, N, ph, pw, ps): return 'c', rng.sample(range(1, 10), N)
def tf_2nd(g):
    idx, ps = parse_h(g); v = compact(idx[0])[:len(ps)]
    return ps[sorted(range(len(v)), key=lambda i: -v[i])[1]]
rule("vertical_index_second_largest_digit_panel", "The index column holds N distinct digits (colour values), one per panel from top to bottom; output the panel whose digit is the second largest." + VS, V(R1(ix_2nd)), vt(tf_2nd), digits=True)

def ix_tr(rng, N, ph, pw, ps): return 'a', [rng.choice((0, 2, 3, 4)) for _ in range(N)]
def tf_tr(g):
    idx, ps = parse_h(g); a = aligned(idx[0], ps); ops = {0: lambda p: p, 2: flip_h, 3: flip_v, 4: lambda p: rot90(rot90(p))}
    return hjoin([ops[v](p) for p, v in zip(ps, a)])
rule("vertical_index_colour_selects_panel_flip", "The index cell left of each panel's first row is empty, red (2), green (3) or yellow (4): empty leaves the panel unchanged, red flips it top to bottom, green flips it left to right, yellow turns it half a turn; output the panels stacked top to bottom with grey (5) rows between them, without the index." + VS, V(R1(ix_tr)), vt(tf_tr), digits=True)

def ix_tile(rng, N, ph, pw, ps): return None
def gi_tile(rng):
    for _ in range(100):
        R = rng.randint(2, 4); Ls = [rng.randint(1, 3) for _ in range(R)]
        N = R; ph = rng.randint(3, 5)
        pw = (rng.randint(21, 30) - (N - 1)) // N if rng.random() < 0.85 else rng.randint(3, 4)
        if sum(Ls) * pw > 30 or pw < 3: continue
        ps = pats(rng, N, ph, pw, PC)
        idx = []
        for i, L in enumerate(Ls): idx += [1 if i % 2 == 0 else 2] * L
        body = hjoin(ps)
        if len(idx) <= len(body[0]): return transpose(asm([idx], body))
    raise RuntimeError
def tf_tile(g):
    idx, ps = parse_h(g); v = idx[0]; runs = []
    for x in compact(v):
        if runs and runs[-1][0] == x: runs[-1][1] += 1
        else: runs.append([x, 1])
    if len(runs) != len(ps): return None
    seq = [p for p, (_, L) in zip(ps, runs) for _ in range(L)]
    return hjoin0(seq)
rule("vertical_index_run_lengths_tile_copies", "The index column alternates between runs of blue (1) and red (2) cells starting with blue; there is one run per panel, top to bottom, and the length of run i is how many copies of panel i to use; output the copies stacked top to bottom in panel order with no separators.", lambda rng: gi_tile(rng), vt(tf_tile))

def ix_first(rng, N, ph, pw, ps):
    v = [rng.choice((1, 2, 3)) for _ in range(N)]
    k = sum(1 for x in v if x == v[0]); return ('a', v) if 2 <= k < N else None
def tf_first(g):
    idx, ps = parse_h(g); a = aligned(idx[0], ps); return hjoin([p for p, x in zip(ps, a) if x == a[0]])
rule("vertical_index_matching_first_colour_kept", "Each panel has a coloured index cell (blue 1, red 2 or green 3) left of its first row; keep the panels whose index colour equals the topmost panel's index colour and output them stacked top to bottom with grey (5) rows between them, without the index." + VS, V(R1(ix_first)), vt(tf_first))

def ix_odd(rng, N, ph, pw, ps):
    v = [rng.randint(1, 9) for _ in range(N)]; return ('a', v) if 0 < sum(1 for x in v if x % 2 == 0) < N else None
def tf_odd(g):
    idx, ps = parse_h(g); a = aligned(idx[0], ps); k = [p for p, x in zip(ps, a) if x % 2 == 0]
    return hjoin(k) if k else None
rule("vertical_index_odd_digits_delete_panels", "Each panel has a digit (colour value) in the index column beside its first row; panels with an odd digit are deleted and the rest are output stacked top to bottom with grey (5) rows between them, without the index." + VS, V(R1(ix_odd)), vt(tf_odd), digits=True)

def ix_mean(rng, N, ph, pw, ps):
    v = [rng.randint(1, 9) for _ in range(N)]; k = sum(1 for x in v if x * N > sum(v)); return ('c', v) if 0 < k < N else None
def tf_mean(g):
    idx, ps = parse_h(g); v = compact(idx[0])[:len(ps)]; k = [p for p, x in zip(ps, v) if x * len(v) > sum(v)]
    return hjoin(k) if k else None
rule("vertical_index_above_mean_digit_panels_kept", "The index column holds one digit (colour value) per panel from top to bottom; keep the panels whose digit is strictly greater than the mean of all the digits and output them stacked top to bottom in their original order with grey (5) rows between them." + VS, V(R1(ix_mean)), vt(tf_mean), digits=True)

def ix_perm(rng, N, ph, pw, ps): return 'c', rng.sample(range(1, N + 1), N)
def tf_perm(g):
    idx, ps = parse_h(g); v = compact(idx[0])[:len(ps)]; out = [None] * len(ps)
    for p, s in zip(ps, v):
        if not 1 <= s <= len(ps): return None
        out[s - 1] = p
    return hjoin(out)
rule("vertical_index_digit_is_destination_slot", "The index column holds a permutation of 1 to N (colour values), one per panel from top to bottom; the digit of a panel is the slot it moves to counted from the top; output the panels stacked in slot order with grey (5) rows between them." + VS, V(R1(ix_perm)), vt(tf_perm), digits=True)

def gi_diff(rng):
    for _ in range(100):
        N, ph, pw = hdims(rng); ps = pats(rng, N, ph, pw, PC)
        a, b = rng.randint(1, 9), rng.randint(1, 9)
        if a != b and abs(a - b) <= N: return transpose(asm([[a, b]], hjoin(ps)))
    raise RuntimeError
def tf_diff(g):
    idx, ps = parse_h(g); a, b = compact(idx[0])[:2]; d = abs(a - b); return ps[d - 1] if 1 <= d <= len(ps) else None
rule("vertical_index_digit_difference_picks_panel", "The index column holds two digits (colour values); the panel number is their absolute difference, counted from 1 at the top; output that panel." + VS, gi_diff, vt(tf_diff), digits=True)

def ix_firstk(rng, N, ph, pw, ps): return 'c', [rng.randint(2, N)]
def tf_firstk(g):
    idx, ps = parse_h(g); k = compact(idx[0])[0]; return hjoin(ps[:k]) if 2 <= k <= len(ps) else None
rule("vertical_index_digit_takes_first_k_panels", "The index column holds one digit k (colour value, 2 or more); output the top k panels stacked top to bottom with grey (5) rows between them." + VS, V(R1(ix_firstk)), vt(tf_firstk), digits=True)


# ================================================================== Q: 2x2 selector scene
QS = " A 2x2 selector sits in the top-left corner above a grey (5) separator row; below it four equal square panels sit side by side divided by grey columns."
def gi_q(kind):
    def gi(rng):
        for _ in range(100):
            big = rng.random() < 0.6; s = rng.randint(5, 6) if big else rng.randint(3, 4); ph = pw = s
            if kind == 'col':
                cols = rng.sample(PC, 4); ps = [pat(rng, s, s, [c], 0.55) for c in cols]; sel = rng.sample(cols, 4)
            elif kind == 'num':
                ps = pats(rng, 4, s, s, PC); sel = rng.sample(range(1, 5), 4)
            else:
                ps = pats(rng, 4, s, s, PC); sel = [rng.randint(0, 3) for _ in range(4)]
            return asm([[sel[0], sel[1]], [sel[2], sel[3]]], hjoin(ps))
    return gi
def q_parse(g):
    idx, body = zones(g); return [idx[0][:2], idx[1][:2]], split_cols(body)
def q_out(a, b, c, d): return vjoin([hjoin([a, b]), hjoin([c, d])])
def tf_qcol(g):
    sel, ps = q_parse(g); m = {dom(p): p for p in ps}
    return q_out(m[sel[0][0]], m[sel[0][1]], m[sel[1][0]], m[sel[1][1]]) if all(v in m for r in sel for v in r) else None
rule("selector_colours_place_panels_in_quadrants", "Each of the four panels is drawn in one colour; the 2x2 selector holds those four colours; output a 2x2 arrangement of the panels, each quadrant holding the panel whose colour matches the selector cell at that position, with grey (5) separator lines between the panels." + QS, gi_q('col'), tf_qcol)
def tf_qnum(g):
    sel, ps = q_parse(g); return q_out(*[ps[sel[i][j] - 1] for i in (0, 1) for j in (0, 1)]) if all(1 <= v <= 4 for r in sel for v in r) else None
rule("selector_digits_place_panels_in_quadrants", "The 2x2 selector holds the digits 1 to 4 (colour values, each once); output a 2x2 arrangement where each quadrant shows the panel whose number (counted 1 to 4 from the left) equals the selector digit at that position, with grey (5) separator lines between the panels." + QS, gi_q('num'), tf_qnum, digits=True)
def tf_qrot(g):
    sel, ps = q_parse(g); d = [sel[0][0], sel[0][1], sel[1][0], sel[1][1]]
    return q_out(*[rotn(p, k) for p, k in zip(ps, d)])
rule("selector_digits_rotate_quadrant_panels", "Panel k (counted 1 to 4 from the left) goes to quadrant k in reading order (top-left, top-right, bottom-left, bottom-right) of a 2x2 arrangement, rotated clockwise by the selector digit (0 to 3, colour value; empty means 0) found at that quadrant's position in the selector; grey (5) separator lines lie between the panels." + QS, gi_q('rot'), tf_qrot, digits=True)


# ================================================================== G: m x n panel grids
GS = " An index zone sits above a grey (5) separator row; below it an m x n grid of equal panels is divided by grey rows and columns."
def gi_g(kind):
    def gi(rng):
        for _ in range(200):
            big = rng.random() < 0.6
            m, n = (3, 3) if big else (rng.randint(2, 3), rng.randint(2, 3)); s = rng.randint(6, 7) if big else rng.randint(3, 4)
            cols = PC if kind not in ('dom',) else rng.sample(PC, 3)
            grid = [[pat(rng, s, s, rng.sample(cols, 2) if kind == 'mask' else cols, 0.2 if kind == 'cnt' else 0.6) for _ in range(n)] for _ in range(m)]
            body = vjoin([hjoin(r) for r in grid])
            if kind == 'mask':
                mk = [[rng.choice((0, 8)) for _ in range(n)] for _ in range(m)]
                if 0 < sum(1 for r in mk for v in r if v) < m * n: return asm(mk, body)
            elif kind == 'xy': return asm([[rng.randint(1, m), rng.randint(1, n)]], body)
            elif kind == 'row': return asm([[rng.randint(1, m)]], body)
            elif kind == 'col': return asm([[rng.randint(1, n)]], body)
            elif kind == 'swap':
                r = rng.sample(range(1, m + 1), 2); return asm([r], body)
            elif kind == 'dom':
                c = rng.choice(cols); doms = [[dom(p) for p in r] for r in grid]
                k = sum(1 for r in doms for v in r if v == c)
                if 0 < k < m * n: return asm([[c]], body)
            elif kind == 'cnt':
                k = rng.randint(2, 9)
                t = sum(1 for r in grid for p in r if nfg(p) > k)
                if 0 < t < m * n and k <= 9: return asm([[k]], body)
    return gi
def g_parse(g):
    idx, body = zones(g); return idx, [split_cols(b) for b in split_rows(body)]
def big2(a): return [[v for v in row for _ in (0, 1)] for row in a for _ in (0, 1)]
def grid_out(gr): return vjoin([hjoin(r) for r in gr])
def tf_gmask(g):
    idx, gr = g_parse(g); m, n = len(gr), len(gr[0])
    return [[dom(gr[i][j]) if idx[i][j] else 0 for j in range(n)] for i in range(m)]
rule("mask_cells_take_their_panels_majority_colour", "The index is an m x n block (m rows, n columns, same shape as the panel grid) of cyan (8) and empty cells; output an m x n grid where each cyan cell is replaced by the most frequent coloured value in the panel at the same position (ties: the smaller colour value) and each empty cell stays black." + GS, gi_g('mask'), tf_gmask)
def tf_gxy(g):
    idx, gr = g_parse(g); r, c = idx[0][:2]
    return gr[r - 1][c - 1] if r <= len(gr) and c <= len(gr[0]) else None
rule("row_and_column_digits_pick_one_panel_of_grid", "The index holds two digits (colour values): a panel row number and a panel column number, both counted from 1 from the top-left; output that panel of the grid." + GS, gi_g('xy'), tf_gxy, digits=True)
def tf_grow(g):
    idx, gr = g_parse(g); d = idx[0][0]; return hjoin(gr[d - 1]) if d <= len(gr) else None
rule("row_digit_outputs_that_panel_row_joined", "The index holds one digit d (colour value); output the d-th row of panels (counted from 1 at the top) joined left to right with grey (5) columns between them." + GS, gi_g('row'), tf_grow, digits=True)
def tf_gcol(g):
    idx, gr = g_parse(g); d = idx[0][0]; return vjoin([r[d - 1] for r in gr]) if d <= len(gr[0]) else None
rule("column_digit_outputs_that_panel_column_stacked", "The index holds one digit d (colour value); output the d-th column of panels (counted from 1 at the left) stacked top to bottom with grey (5) rows between them." + GS, gi_g('col'), tf_gcol, digits=True)
def tf_gswap(g):
    idx, gr = g_parse(g); a, b = idx[0][:2]
    if not (1 <= a <= len(gr) and 1 <= b <= len(gr)) or a == b: return None
    gr = [r[:] for r in gr]; gr[a - 1], gr[b - 1] = gr[b - 1], gr[a - 1]; return grid_out(gr)
rule("two_row_digits_swap_panel_rows_of_grid", "The index holds two different digits (colour values) naming panel rows counted from 1 at the top; output the whole panel grid with those two rows of panels exchanged, the grey (5) separator lines redrawn, and the index removed." + GS, gi_g('swap'), tf_gswap, digits=True)
def tf_gdom(g):
    idx, gr = g_parse(g); c = idx[0][0]
    return big2([[c if dom(p) == c else 0 for p in r] for r in gr])
rule("index_colour_marks_panels_with_that_majority", "The index is one coloured cell; output a grid with one 2x2 block per panel (m x n blocks): that colour where the panel's most frequent coloured value (ties: smaller colour value) equals the index colour, black elsewhere." + GS, gi_g('dom'), tf_gdom)
def tf_gcnt(g):
    idx, gr = g_parse(g); k = idx[0][0]
    return big2([[8 if nfg(p) > k else 0 for p in r] for r in gr])
rule("index_digit_marks_panels_with_more_cells", "The index is one digit k (colour value); output a grid with one 2x2 block per panel (m x n blocks): cyan (8) if the panel has more than k coloured cells, black otherwise." + GS, gi_g('cnt'), tf_gcnt, digits=True)


# ================================================================== M: index cell(s) or glyph above a strip
def gi_m(kind):
    def gi(rng):
        for _ in range(300):
            N, ph, pw = hdims(rng, False, 3, 5)
            if kind == 'glyph':
                if ph * pw < 9: continue
                ms = [pat(rng, ph, pw, [1], 0.5) for _ in range(N)]
                if len({str(m) for m in ms}) < N: continue
                k = rng.randrange(N); ps = [[[rng.choice(PC) if v else 0 for v in row] for row in m] for m in ms]
                col = [rng.choice(PC) for _ in range(N)]
                ps = [[[col[i] if v else 0 for v in row] for row in m] for i, m in enumerate(ms)]
                glyph = [[8 if v else 0 for v in row] for row in ms[k]]
                return asm(glyph, hjoin(ps))
            if kind == 'domc':
                c = rng.choice(PC); k = rng.randrange(N); ps = []
                for i in range(N):
                    d = c if i == k else rng.choice([x for x in PC if x != c]); o = rng.choice([x for x in PC if x != d])
                    ps.append(pat(rng, ph, pw, [d, d, d, o], 0.65))
                if [i for i, p in enumerate(ps) if dom(p) == c] == [k]: return asm([[c]], hjoin(ps))
            if kind in ('cnt', 'cnt_rank'):
                cs = rng.sample(range(1, min(ph * pw, 9) + 1), N); ps = []
                for cnt_ in cs:
                    cells_ = rng.sample([(r, c) for r in range(ph) for c in range(pw)], cnt_); col = rng.choice(PC)
                    p = blank(ph, pw)
                    for r, c in cells_: p[r][c] = col
                    ps.append(p)
                if kind == 'cnt': return asm([[rng.choice(cs)]], hjoin(ps))
                return asm([[rng.randint(1, N)]], hjoin(ps))
            if kind == 'right': return asm([[rng.randint(1, N)]], hjoin(pats(rng, N, ph, pw, PC)))
            if kind == 'most':
                c = rng.choice(PC); others = [x for x in PC if x != c]; ps = pats(rng, N, ph, pw, [c, c] + others[:2], 0.6)
                cc = [sum(row.count(c) for row in p) for p in ps]
                if cc.count(max(cc)) == 1 and max(cc) > 0: return asm([[c]], hjoin(ps))
    return gi
def tf_mglyph(g):
    idx, ps = parse_h(g); mk = {(r, c) for r, row in enumerate(idx) for c, v in enumerate(row[:len(ps[0][0])]) if v}
    f = [p for p in ps if {(r, c) for r, row in enumerate(p) for c, v in enumerate(row) if v} == mk]
    return f[0] if len(f) == 1 else None
MS = " An index zone sits above a grey (5) separator row; below it N equal panels sit side by side divided by grey columns."
rule("panel_whose_shape_matches_index_glyph_output", "The index is a glyph, a cyan (8) shape the size of one panel; exactly one panel has coloured cells in exactly the glyph's positions (its colour differs from cyan); output that panel." + MS, gi_m('glyph'), tf_mglyph)
def tf_mdom(g):
    idx, ps = parse_h(g); c = idx[0][0]; f = [p for p in ps if dom(p) == c]; return f[0] if len(f) == 1 else None
rule("panel_with_index_colour_as_majority_output", "The index is one coloured cell; output the one panel whose most frequent coloured value is that colour." + MS, gi_m('domc'), tf_mdom)
def tf_mcnt(g):
    idx, ps = parse_h(g); d = idx[0][0]; f = [p for p in ps if nfg(p) == d]; return f[0] if len(f) == 1 else None
rule("panel_with_index_digit_many_cells_output", "The index is one digit d (colour value); output the one panel that has exactly d coloured cells." + MS, gi_m('cnt'), tf_mcnt, digits=True)
def tf_mright(g):
    idx, ps = parse_h(g); d = idx[0][0]; return ps[len(ps) - d] if 1 <= d <= len(ps) else None
rule("index_digit_counts_panels_from_the_right", "The index is one digit d (colour value); output the d-th panel counted from 1 starting at the rightmost panel." + MS, gi_m('right'), tf_mright, digits=True)
def tf_mmost(g):
    idx, ps = parse_h(g); c = idx[0][0]; cc = [sum(r.count(c) for r in p) for p in ps]; return ps[cc.index(max(cc))] if cc.count(max(cc)) == 1 else None
rule("panel_with_most_cells_of_index_colour_output", "The index is one coloured cell; output the panel that contains the most cells of that colour (exactly one panel has strictly the most)." + MS, gi_m('most'), tf_mmost)
def tf_mrank(g):
    idx, ps = parse_h(g); d = idx[0][0]; o = sorted(ps, key=lambda p: -nfg(p)); return o[d - 1] if 1 <= d <= len(o) else None
rule("index_digit_picks_nth_largest_panel_by_cells", "Panels have different numbers of coloured cells; the index is one digit d (colour value); output the panel with the d-th most coloured cells (d=1 is the fullest)." + MS, gi_m('cnt_rank'), tf_mrank, digits=True)
