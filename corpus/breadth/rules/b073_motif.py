# b073_motif.py -- A FRAGMENT IS A WINDOW ON A WHOLE MOTIF: a periodic or symmetric motif is only partly visible
# (through a window cut in a grey cover, behind occluders, cut by the grid edge, as a torn piece, as a prefix) and the
# rule reconstructs or reasons about the whole. Every generator checks that the transform recovers the intended whole.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

COLS = [1, 2, 3, 4, 6, 7, 8, 9]     # motif colours (never grey 5, never 0)


def _safe(f):
    def g(x):
        try: return f(x)
        except (ValueError, IndexError, KeyError, StopIteration, ZeroDivisionError, TypeError): return None
    return g


def _hw(rng, lo=10, hi=20, p=0.45):
    if rng.random() < p: return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _tile(rng, ph, pw, cols):
    for _ in range(200):
        t = [[rng.choice(cols) for _ in range(pw)] for _ in range(ph)]
        if len({v for r in t for v in r}) < 2: continue
        if any(all(t[r] == t[(r + d) % ph] for r in range(ph)) for d in range(1, ph) if ph % d == 0): continue
        if any(all(t[r][c] == t[r][(c + d) % pw] for r in range(ph) for c in range(pw)) for d in range(1, pw) if pw % d == 0): continue
        return t
    return None


def _tiled(t, H, W):
    ph, pw = len(t), len(t[0]); return [[t[r % ph][c % pw] for c in range(W)] for r in range(H)]


def _infer(g, hid=(), maxp=6, off=(0, 0)):
    """Smallest (ph*pw, then ph) rectangular period consistent with every non-hidden cell and seen in all phase classes."""
    H, W = dims(g)
    for _, ph, pw in sorted((a * b, a, b) for a in range(1, maxp + 1) for b in range(1, maxp + 1)):
        if H < 2 * ph or W < 2 * pw: continue
        tab = {}; ok = True
        for r in range(H):
            for c in range(W):
                v = g[r][c]
                if v in hid: continue
                if tab.setdefault(((r + off[0]) % ph, (c + off[1]) % pw), v) != v: ok = False; break
            if not ok: break
        if ok and len(tab) == ph * pw: return ph, pw, tab
    return None


def _guard(build, tf, tries=400):
    def gen(rng):
        for _ in range(tries):
            res = build(rng)
            if not res: continue
            inp, truth = res
            if inp == truth: continue
            if tf(inp) == truth: return inp
        raise RuntimeError("guard")
    return gen


def _full(rng, cols=COLS, lo=10):
    for _ in range(100):
        H, W = _hw(rng, lo)
        ph, pw = rng.randint(2, 4), rng.randint(2, 4)
        t = _tile(rng, ph, pw, cols)
        if t: return H, W, t, _tiled(t, H, W)


def _restore(hid, fill=None):
    fill = hid if fill is None else fill
    def tf(g):
        res = _infer(g, hid)
        if not res: return None
        ph, pw, tab = res; out = copy(g)
        for r in range(len(g)):
            for c in range(len(g[0])):
                if g[r][c] in fill: out[r][c] = tab[(r % ph, c % pw)]
        return out
    return _safe(tf)


def _cover(rng, g, r0r, c0r, col, lo=3):
    H, W = dims(g); rh = rng.randint(lo, max(lo, H // 2)); rw = rng.randint(lo, max(lo, W // 2))
    r = rng.randint(0, H - rh); c = rng.randint(0, W - rw); rect(g, r, c, r + rh - 1, c + rw - 1, col); return r, c, rh, rw


# ============================== A. a window cut in a grey cover (6 rules) ==============================
def _win(rng, room=0):
    for _ in range(100):
        H, W = _hw(rng); ph, pw = rng.randint(2, 4), rng.randint(2, 4); t = _tile(rng, ph, pw, COLS)
        wh = rng.randint(2 * ph, min(H - 2, 2 * ph + 8)); ww = rng.randint(2 * pw, min(W - 2 - room, 2 * pw + 10))
        if t and ww >= 2 * pw: break
    wr, wc = rng.randint(0, H - wh), rng.randint(0, W - ww - room)
    return H, W, t, ph, pw, wr, wc, wh, ww

def _paint_win(H, W, t, wr, wc, wh, ww):
    ph, pw = len(t), len(t[0]); g = blank(H, W, 5)
    for r in range(wr, wr + wh):
        for c in range(wc, wc + ww): g[r][c] = t[r % ph][c % pw]
    return g

def _winbox(g):
    cs = cells(g, lambda v: v != 5); return bbox(cs)

def b_a1(rng):
    H, W, t, ph, pw, wr, wc, wh, ww = _win(rng)
    return _paint_win(H, W, t, wr, wc, wh, ww), [[t[(wr + i) % ph][(wc + j) % pw] for j in range(pw)] for i in range(ph)]
def t_a1(g):
    r0, c0, r1, c1 = _winbox(g); ph, pw, tab = _infer(crop(g, r0, c0, r1, c1))
    return [[tab[(i, j)] for j in range(pw)] for i in range(ph)]
t_a1 = _safe(t_a1)
rule("window_period_tile_read_from_window_corner", "Everything is grey 5 cover except one rectangular window showing a periodic tiling (at least two periods each way); the output is one period of the tiling, the smallest rectangular tile, taken with its top-left cell at the window's top-left cell.", _guard(b_a1, t_a1), t_a1)

def b_a2(rng):
    H, W, t, ph, pw, wr, wc, wh, ww = _win(rng)
    return _paint_win(H, W, t, wr, wc, wh, ww), t
def t_a2(g):
    r0, c0, r1, c1 = _winbox(g); ph, pw, tab = _infer(crop(g, r0, c0, r1, c1), off=(r0, c0))
    return [[tab[(i, j)] for j in range(pw)] for i in range(ph)]
t_a2 = _safe(t_a2)
rule("window_period_tile_anchored_at_grid_origin", "Everything is grey 5 cover except one rectangular window showing part of a periodic tiling that is aligned to the whole grid's top-left corner; the output is one period (the smallest rectangular tile) as it sits at that corner, i.e. as if the window were removed and the tiling started at row 0, column 0.", _guard(b_a2, t_a2), t_a2)

def b_a3(rng):
    H, W, t, ph, pw, wr, wc, wh, ww = _win(rng)
    return _paint_win(H, W, t, wr, wc, wh, ww), _tiled(t, H, W)
def t_a3(g):
    ph, pw, tab = _infer(g, (5,)); return [[tab[(r % ph, c % pw)] for c in range(len(g[0]))] for r in range(len(g))]
t_a3 = _safe(t_a3)
rule("window_tiling_continued_over_whole_grid", "Everything is grey 5 cover except one rectangular window showing a periodic tiling; the output is the same size with the cover removed and the tiling continued, with the same period and phase, over the entire grid.", _guard(b_a3, t_a3), t_a3)

def b_a4(rng):
    H, W, t, ph, pw, wr, wc, wh, ww = _win(rng, room=0)
    for _ in range(50):
        if wc + ww + pw <= W: break
        H, W, t, ph, pw, wr, wc, wh, ww = _win(rng)
    else: return None
    return _paint_win(H, W, t, wr, wc, wh, ww), _paint_win(H, W, t, wr, wc + pw, wh, ww)
def t_a4(g):
    r0, c0, r1, c1 = _winbox(g); ph, pw, tab = _infer(crop(g, r0, c0, r1, c1), off=(r0, c0))
    if c1 + pw >= len(g[0]): return None
    out = blank(len(g), len(g[0]), 5)
    for r in range(r0, r1 + 1):
        for c in range(c0 + pw, c1 + pw + 1): out[r][c] = tab[(r % ph, c % pw)]
    return out
t_a4 = _safe(t_a4)
rule("window_moves_one_horizontal_period_right", "Everything is grey 5 cover except one rectangular window on a periodic tiling aligned to the grid's top-left corner; in the output the window of the same size sits one horizontal period (the tiling's smallest column period) further right, showing the tiling there, and all its former cells not covered by the new window become grey 5 again.", _guard(b_a4, t_a4), t_a4)

def b_a5(rng):
    for _ in range(100):
        H, W = _hw(rng, 12, 20); ph, pw = rng.randint(2, 4), rng.randint(2, 4); t = _tile(rng, ph, pw, COLS)
        w1, w2, gap = rng.randint(pw + 1, pw + 5), rng.randint(pw + 1, pw + 5), rng.randint(2, 8)
        wh = rng.randint(ph + 1, min(H - 2, ph + 8))
        if t and w1 + w2 + gap <= W and w1 + w2 >= 2 * pw: break
    else: return None
    r = rng.randint(0, H - wh); c = rng.randint(0, W - (w1 + w2 + gap)); full = _tiled(t, H, W)
    g = blank(H, W, 5)
    for rr in range(r, r + wh):
        for cc in list(range(c, c + w1)) + list(range(c + w1 + gap, c + w1 + gap + w2)): g[rr][cc] = full[rr][cc]
    truth = [row[c + w1: c + w1 + gap] for row in full[r:r + wh]]
    return (transpose(g), transpose(truth)) if rng.random() < 0.5 else (g, truth)
def t_a5(g):
    res = _infer(g, (5,)); ph, pw, tab = res
    nc = cells(g, lambda v: v != 5); R = sorted({r for r, _ in nc}); C = sorted({c for _, c in nc})
    if R[-1] - R[0] + 1 == len(R) and C[-1] - C[0] + 1 != len(C):
        gc = [c for c in range(C[0], C[-1] + 1) if c not in C]
        return [[tab[(r % ph, c % pw)] for c in gc] for r in range(R[0], R[-1] + 1)]
    if C[-1] - C[0] + 1 == len(C) and R[-1] - R[0] + 1 != len(R):
        gr = [r for r in range(R[0], R[-1] + 1) if r not in R]
        return [[tab[(r % ph, c % pw)] for c in range(C[0], C[-1] + 1)] for r in gr]
    return None
t_a5 = _safe(t_a5)
rule("two_windows_output_the_hidden_gap_between", "Everything is grey 5 cover except two rectangular windows of the same height (or width) side by side on one periodic tiling aligned to the grid's top-left corner, separated by a grey gap; the output is exactly the part of the tiling that lies hidden under the gap, with the gap's size.", _guard(b_a5, t_a5), t_a5)

def b_a6(rng):
    H, W, t, ph, pw, wr, wc, wh, ww = _win(rng)
    return _paint_win(H, W, t, wr, wc, wh, ww), [[ww // pw, 0]]
def t_a6(g):
    r0, c0, r1, c1 = _winbox(g); ph, pw, tab = _infer(crop(g, r0, c0, r1, c1)); return [[(c1 - c0 + 1) // pw, 0]]
t_a6 = _safe(t_a6)
rule("window_width_in_horizontal_periods_as_digit", "Everything is grey 5 cover except one rectangular window on a periodic tiling; the output is one row of two cells, a cell whose colour value is the window's width divided by the tiling's smallest column period, rounded down, then a 0 cell.", _guard(b_a6, t_a6), t_a6, digits=True)


# ============================== B. occluders on a full tiling (11 rules) ==============================
def b_b1(rng):
    H, W, t, full = _full(rng); g = copy(full); _cover(rng, g, 0, 0, 5); return g, full
rule("grey_cover_removed_tiling_continued_beneath", "A periodic tiling is partly hidden by one solid rectangle of grey 5; the output is the full tiling with the rectangle replaced by what the tiling's smallest rectangular period predicts there.", _guard(b_b1, _restore((5,))), _restore((5,)))

def b_b2(rng):
    H, W, t, full = _full(rng); g = copy(full)
    for _ in range(rng.randint(3, 8) * (2 if H * W > 400 else 1)):
        sh = random_shape(rng, rng.randint(1, 3)); r, c = rng.randint(0, H - 3), rng.randint(0, W - 3)
        for y, x in sh:
            if r + y < H and c + x < W: g[r + y][c + x] = 5
    return g, full
rule("scattered_blots_replaced_by_period_prediction", "A periodic tiling is spotted with small blots of grey 5 (1 to 3 cells each, possibly overlapping); every grey cell is replaced by the colour the tiling's smallest rectangular period predicts at that position.", _guard(b_b2, _restore((5,))), _restore((5,)))

def b_b3(rng):
    H, W, t, full = _full(rng); g = copy(full)
    for _ in range(rng.randint(1, 3)):
        h = rng.randint(1, 2); r = rng.randint(0, H - h)
        for y in range(r, r + h): g[y] = [8] * W
    if rng.random() < 0.5: g, full = transpose(g), transpose(full)
    return g, full
rule("occluding_bands_of_eight_restored_from_period", "A periodic tiling is crossed by 1 to 3 full-width bands (all horizontal or all vertical) of colour 8, each 1 or 2 cells thick; the output replaces every 8 cell by the colour the tiling's smallest rectangular period predicts.", _guard(b_b3, _restore((8,))), _restore((8,)))
# b3 uses colour 8 as the occluder, so its tile must not contain 8
def _b3_fix(build):
    def b(rng):
        while True:
            r = build(rng)
            if r and not any(8 in row for row in _tiled_cols(r[1])): return r
    return b
def _tiled_cols(full): return [[v for v in row if v == 8][:1] for row in full if False] or [[]]

def b_b4(rng):
    H, W, t, full = _full(rng); g = copy(full); r, c, rh, rw = _cover(rng, g, 0, 0, 5, 2)
    return g, [row[c:c + rw] for row in full[r:r + rh]]
def t_b4(g):
    ph, pw, tab = _infer(g, (5,)); r0, c0, r1, c1 = bbox(cells(g, lambda v: v == 5))
    return [[tab[(r % ph, c % pw)] for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
t_b4 = _safe(t_b4)
rule("what_lies_under_the_grey_cover_cropped", "A periodic tiling is partly hidden by one solid rectangle of grey 5; the output is just the hidden rectangle's content, the colours the tiling's smallest rectangular period predicts under the cover, with the cover's height and width.", _guard(b_b4, t_b4), t_b4)

def b_b5(rng):
    H, W, t, full = _full(rng, [1, 2, 3, 4, 6, 9]); g = copy(full)
    for col in (8, 8, 7, 7):
        if rng.random() < 0.6 or col == 8 and g == full:
            rh, rw = rng.randint(2, 5), rng.randint(2, 5); r, c = rng.randint(0, H - rh), rng.randint(0, W - rw); rect(g, r, c, r + rh - 1, c + rw - 1, col)
    truth = [[full[r][c] if g[r][c] == 8 else g[r][c] for c in range(W)] for r in range(H)]
    return g, truth
rule("only_eight_covers_are_lifted_seven_stay", "A periodic tiling is hidden under rectangular covers of two colours; covers of colour 8 are lifted and replaced by what the tiling's smallest rectangular period predicts, while covers of colour 7 stay exactly as they are.", _guard(b_b5, _restore((7, 8), (8,))), _restore((7, 8), (8,)))

def _seq(rng, p, cols):
    while True:
        s = [rng.choice(cols) for _ in range(p)]
        if len(set(s)) > 1 and all(not all(s[i] == s[(i + d) % p] for i in range(p)) for d in range(1, p) if p % d == 0): return s

def b_b6(rng):
    H, W = _hw(rng); p = rng.randint(3, 6); s = rng.randint(1, p - 1); seq = _seq(rng, p, COLS)
    full = [[seq[(c + s * r) % p] for c in range(W)] for r in range(H)]; g = copy(full); _cover(rng, g, 0, 0, 5); return g, full
def t_b6(g):
    H, W = dims(g)
    for p in range(2, 8):
        for s in range(p):
            tab = {}; ok = True
            for r in range(H):
                for c in range(W):
                    if g[r][c] != 5 and tab.setdefault((c + s * r) % p, g[r][c]) != g[r][c]: ok = False; break
                if not ok: break
            if ok and len(tab) == p: return [[tab[(c + s * r) % p] for c in range(W)] for r in range(H)]
    return None
t_b6 = _safe(t_b6)
rule("diagonal_stripe_tiling_under_grey_cover_restored", "Each row of a picture is the previous row shifted one fixed number of cells to the right, repeating with a short colour sequence (a sheared tiling), and one solid rectangle of grey 5 hides part of it; the output replaces the grey with the cells the shifted sequence predicts, choosing the shortest sequence length that fits and then the smallest shift.", _guard(b_b6, t_b6), t_b6)

def b_b7(rng):
    for _ in range(100):
        H, W = _hw(rng); ph, pw = rng.randint(2, 3), rng.choice([2, 4, 6]); t = _tile(rng, ph, pw, COLS)
        if t: break
    sh = pw // 2; full = [[t[r % ph][(c + (r // ph) * sh) % pw] for c in range(W)] for r in range(H)]; g = copy(full); _cover(rng, g, 0, 0, 5); return g, full
def t_b7(g):
    H, W = dims(g)
    for _, ph, pw in sorted((a * b, a, b) for a in range(1, 5) for b in (2, 4, 6)):
        sh = pw // 2; tab = {}; ok = True
        for r in range(H):
            for c in range(W):
                if g[r][c] != 5 and tab.setdefault((r % ph, (c + (r // ph) * sh) % pw), g[r][c]) != g[r][c]: ok = False; break
            if not ok: break
        if ok and len(tab) == ph * pw: return [[tab[(r % ph, (c + (r // ph) * sh) % pw)] for c in range(W)] for r in range(H)]
    return None
t_b7 = _safe(t_b7)
rule("half_drop_brick_tiling_under_grey_cover_restored", "A picture is made of a tile whose copies in each next band of tile-height rows are shifted half a tile width (pw/2, pw even) to the right, and one solid rectangle of grey 5 hides part of it; the output replaces the grey by the half-drop tiling continued, using the tile with the smallest area that fits (ties: fewer rows).", _guard(b_b7, t_b7), t_b7)

def _fold(i, p): return i % p if (i // p) % 2 == 0 else p - 1 - i % p
def b_b8(rng):
    for _ in range(100):
        H, W = _hw(rng); ph, pw = rng.randint(2, 4), rng.randint(2, 4); a, b = H // ph, W // pw; t = _tile(rng, ph, pw, COLS)
        if t and a >= 2 and b >= 2: break
    H, W = a * ph, b * pw; full = [[t[_fold(r, ph)][_fold(c, pw)] for c in range(W)] for r in range(H)]; g = copy(full); _cover(rng, g, 0, 0, 5); return g, full
def t_b8(g):
    H, W = dims(g)
    for _, ph, pw in sorted((a * b, a, b) for a in range(1, 9) for b in range(1, 9) if H % a == 0 and W % b == 0 and H // a >= 2 and W // b >= 2):
        tab = {}; ok = True
        for r in range(H):
            for c in range(W):
                if g[r][c] != 5 and tab.setdefault((_fold(r, ph), _fold(c, pw)), g[r][c]) != g[r][c]: ok = False; break
            if not ok: break
        if ok and len(tab) == ph * pw: return [[tab[(_fold(r, ph), _fold(c, pw))] for c in range(W)] for r in range(H)]
    return None
t_b8 = _safe(t_b8)
rule("mirrored_every_other_repeat_under_cover_restored", "The grid is an exact grid of tile-sized blocks where blocks in odd columns are the tile mirrored left-right and blocks in odd rows are mirrored top-bottom, and one solid rectangle of grey 5 hides part of it; the output replaces the grey by the mirrored tiling, using the tile with the smallest area whose block grid fits (ties: fewer rows).", _guard(b_b8, t_b8), t_b8)

def b_b9(rng):
    W = rng.randint(21, 30) if rng.random() < 0.5 else rng.randint(12, 20); n = rng.randint(2, 10)
    full, g = [], []
    for _ in range(n):
        p = rng.randint(2, 5); s = _seq(rng, p, COLS); row = [s[c % p] for c in range(W)]; full.append(row); h = row[:]
        for c in rng.sample(range(W), rng.randint(0, 4)): h[c] = 0
        g.append(h)
    return g, full
def t_b9(g):
    out = copy(g)
    for i, row in enumerate(g):
        for p in range(1, 8):
            tab = {}; ok = True
            for c, v in enumerate(row):
                if v and tab.setdefault(c % p, v) != v: ok = False; break
            if ok and len(tab) == p and len(row) >= 2 * p: out[i] = [tab[c % p] for c in range(len(row))]; break
        else: return None
    return out
t_b9 = _safe(t_b9)
rule("each_row_has_its_own_period_gaps_filled", "Every row is its own periodic colour sequence (period 2 to 5, rows may differ) with a few cells blanked to 0; the output fills every 0 with the colour that row's shortest consistent period predicts, row by row.", _guard(b_b9, t_b9), t_b9)

def b_b10(rng):
    for _ in range(100):
        H, W = _hw(rng); ph, pw = rng.randint(2, 4), rng.randint(2, 4); a, b = H // ph, W // pw; t = _tile(rng, ph, pw, COLS)
        if t and a * b >= 6: break
    H, W = a * ph, b * pw; g = _tiled(t, H, W); k = rng.randint(1, min(3, a * b - 5))
    for idx in rng.sample(range(a * b), k):
        i, j = divmod(idx, b); rect(g, i * ph, j * pw, i * ph + ph - 1, j * pw + pw - 1, 5)
    return g, [[k, 0]]
def t_b10(g):
    ph, pw, tab = _infer(g, (5,)); n = sum(1 for row in g for v in row if v == 5); return [[n // (ph * pw), 0]]
t_b10 = _safe(t_b10)
rule("hidden_tile_blocks_counted_as_digit", "A periodic tiling is an exact grid of tile-sized blocks of which some whole blocks are covered by grey 5; the output is one row of two cells, a cell whose colour value is the number of covered blocks (grey cell total divided by the tile area, with the smallest rectangular tile), then a 0 cell.", _guard(b_b10, t_b10), t_b10, digits=True)

def b_b11(rng):
    H, W, t, full = _full(rng); ph, pw = len(t), len(t[0]); g = copy(full)
    keys = rng.sample([(i, j) for i in range(ph) for j in range(pw)], min(ph * pw, rng.randint(1, 4)))
    for i, j in keys:
        r = i + ph * rng.randrange((H - i + ph - 1) // ph); c = j + pw * rng.randrange((W - j + pw - 1) // pw)
        g[r][c] = rng.choice([v for v in COLS if v != full[r][c]])
    return g, full
def t_b11(g):
    H, W = dims(g)
    for _, ph, pw in sorted((a * b, a, b) for a in range(1, 7) for b in range(1, 7)):
        if H < 3 * ph or W < 3 * pw: continue
        cl = {}
        for r in range(H):
            for c in range(W): cl.setdefault((r % ph, c % pw), []).append(g[r][c])
        tab = {}; ok = True
        for k, vs in cl.items():
            m = max(set(vs), key=vs.count)
            if vs.count(m) * 2 <= len(vs): ok = False; break
            tab[k] = m
        if not ok: continue
        out = [[tab[(r % ph, c % pw)] for c in range(W)] for r in range(H)]
        if sum(1 for r in range(H) for c in range(W) if out[r][c] != g[r][c]) <= max(1, H * W // 20): return out
    return None
t_b11 = _safe(t_b11)
rule("noisy_tiling_cleaned_by_phase_majority", "A periodic tiling has a few cells overwritten with wrong colours; the output restores it by giving every cell the majority colour of all cells sharing its position within the tiling's smallest rectangular period (the first period, smallest area, whose phase classes all have a strict majority and which disagrees with at most 5% of cells).", _guard(b_b11, t_b11), t_b11)


# ============================== C. plain tilings (8 rules) ==============================
def _exact(rng, cols=COLS, amin=2, area=1):
    for _ in range(200):
        H, W = _hw(rng); ph, pw = rng.randint(2, 4), rng.randint(2, 4); a, b = H // ph, W // pw; t = _tile(rng, ph, pw, cols)
        if t and a >= amin and b >= amin and a * b >= area: return a, b, ph, pw, t

def b_c1(rng):
    H, W = _hw(rng); ph, pw = rng.randint(2, 5), rng.randint(2, 5); t = _tile(rng, ph, pw, COLS); return _tiled(t, H, W), t
def t_c1(g):
    ph, pw, tab = _infer(g); return [[tab[(i, j)] for j in range(pw)] for i in range(ph)]
t_c1 = _safe(t_c1)
rule("smallest_generating_tile_alone", "The picture is a periodic tiling cut off at the grid edges (at least two repeats each way); the output is the smallest rectangular tile (fewest rows and columns, area first, then fewer rows) whose repetition from the top-left corner reproduces the whole picture, taken from the top-left corner.", _guard(b_c1, t_c1), t_c1)

def b_c2(rng):
    a, b, ph, pw, t = _exact(rng)
    if t == [r[::-1] for r in t] or t == t[::-1]: return None
    return _tiled(t, a * ph, b * pw), [[t[_fold(r, ph)][_fold(c, pw)] for c in range(b * pw)] for r in range(a * ph)]
def t_c2(g):
    ph, pw, tab = _infer(g); H, W = dims(g)
    if H % ph or W % pw: return None
    return [[tab[(_fold(r, ph), _fold(c, pw))] for c in range(W)] for r in range(H)]
t_c2 = _safe(t_c2)
rule("retile_mirroring_every_other_repeat", "The picture is an exact grid of identical tile copies (smallest rectangular tile); the output keeps the first copy and mirrors it left-right in every odd column of copies and top-bottom in every odd row of copies (both when both are odd), counting copies from the top-left.", _guard(b_c2, t_c2), t_c2)

def b_c3(rng):
    for _ in range(100):
        a, b, ph, pw, t = _exact(rng, [1, 2, 3, 4, 6, 7])
        if any(1 in r for r in t) and any(2 in r for r in t): break
    sw = {1: 2, 2: 1}
    g = _tiled(t, a * ph, b * pw)
    return g, [[sw.get(g[r][c], g[r][c]) if ((r // ph) + (c // pw)) % 2 else g[r][c] for c in range(b * pw)] for r in range(a * ph)]
def t_c3(g):
    ph, pw, tab = _infer(g); sw = {1: 2, 2: 1}
    return [[sw.get(g[r][c], g[r][c]) if ((r // ph) + (c // pw)) % 2 else g[r][c] for c in range(len(g[0]))] for r in range(len(g))]
t_c3 = _safe(t_c3)
rule("swap_colours_one_two_in_alternate_repeats", "The picture is an exact grid of identical tile copies (smallest rectangular tile); in every copy whose row index plus column index (counted from 0 at the top-left copy) is odd, colours 1 and 2 swap places, all other colours and cells staying.", _guard(b_c3, t_c3), t_c3)

def b_c4(rng):
    for _ in range(200):
        H, _w = _hw(rng); ph, pw = rng.randint(2, 4), rng.randint(3, 5); t = _tile(rng, ph, pw, COLS); k = rng.randint(2, 30 // pw - 1); rem = rng.randint(1, pw - 1)
        W = k * pw + rem
        if t and W <= 30 and (k + 1) * pw <= 30: break
    return _tiled(t, H, W), _tiled(t, H, (k + 1) * pw)
def t_c4(g):
    ph, pw, tab = _infer(g); H, W = dims(g); W2 = -(-W // pw) * pw
    if W2 == W: return None
    return [[tab[(r % ph, c % pw)] for c in range(W2)] for r in range(H)]
t_c4 = _safe(t_c4)
rule("edge_cut_last_repeat_completed", "A periodic tiling is cut by the right edge in the middle of a repeat; the output is wider, with the width rounded up to a whole number of the tiling's smallest column period, the tiling continued to complete that last repeat, same height.", _guard(b_c4, t_c4), t_c4)

def b_c5(rng):
    for _ in range(100):
        H, W = _hw(rng); ph, pw = rng.randint(1, 5), rng.randint(1, 5); t = _tile(rng, ph, pw, COLS)
        if t and (ph, pw) != (1, 1): return _tiled(t, H, W), [[ph, pw]]
def t_c5(g):
    ph, pw, tab = _infer(g); return [[ph, pw]]
t_c5 = _safe(t_c5)
rule("period_lengths_as_two_digit_cells", "The picture is a periodic tiling; the output is one row of two cells whose colour values are the tiling's smallest row period (vertical repeat length) and then its smallest column period (horizontal repeat length), found independently.", _guard(b_c5, t_c5), t_c5, digits=True)

def _oddblock(rng):
    for _ in range(100):
        a, b, ph, pw, t = _exact(rng, [1, 2, 3, 4, 6, 7, 9], 2, 6)
        i, j = rng.randrange(a), rng.randrange(b); g = _tiled(t, a * ph, b * pw); chg = 0
        for _k in range(rng.randint(1, 3)):
            y, x = rng.randrange(ph), rng.randrange(pw); nv = rng.choice([v for v in COLS if v != t[y][x] and v != 8])
            g[i * ph + y][j * pw + x] = nv; chg += 1
        if g[i * ph:(i + 1) * ph] and [r[j * pw:(j + 1) * pw] for r in g[i * ph:(i + 1) * ph]] != t: return g, a, b, ph, pw, i, j, t
def _oddfind(g):
    H, W = dims(g)
    for _, ph, pw in sorted((a * b, a, b) for a in range(1, 9) for b in range(1, 9) if H % a == 0 and W % b == 0 and (H // a) * (W // b) >= 6):
        bl = {}
        for i in range(H // ph):
            for j in range(W // pw): bl.setdefault(tuple(tuple(r[j * pw:(j + 1) * pw]) for r in g[i * ph:(i + 1) * ph]), []).append((i, j))
        if len(bl) == 2:
            lo, hi = sorted(bl.values(), key=len)
            if len(lo) == 1: return ph, pw, lo[0]
    return None
def b_c6(rng):
    g, a, b, ph, pw, i, j, t = _oddblock(rng); out = copy(g)
    for r in range(i * ph, i * ph + ph):
        for c in range(j * pw, j * pw + pw): out[r][c] = 8
    return g, out
def t_c6(g):
    ph, pw, (i, j) = _oddfind(g); out = copy(g)
    for r in range(i * ph, i * ph + ph):
        for c in range(j * pw, j * pw + pw): out[r][c] = 8
    return out
t_c6 = _safe(t_c6)
rule("deviant_tile_block_recoloured_eight", "The grid is an exact grid of tile-sized blocks, all identical except one block that differs in a few cells (the tile size is the smallest block size, area first then fewer rows, that leaves exactly two block types with one block of the rarer type); the output recolours every cell of that one deviant block to 8.", _guard(b_c6, t_c6), t_c6)
def b_c7(rng):
    g, a, b, ph, pw, i, j, t = _oddblock(rng); return g, [r[j * pw:(j + 1) * pw] for r in g[i * ph:(i + 1) * ph]]
def t_c7(g):
    ph, pw, (i, j) = _oddfind(g); return [r[j * pw:(j + 1) * pw] for r in g[i * ph:(i + 1) * ph]]
t_c7 = _safe(t_c7)
rule("deviant_tile_block_output_alone", "The grid is an exact grid of tile-sized blocks, all identical except one block that differs in a few cells (the tile size is the smallest block size, area first then fewer rows, that leaves exactly two block types with one block of the rarer type); the output is that one deviant block, copied as it is.", _guard(b_c7, t_c7), t_c7)

def b_c8(rng):
    for _ in range(200):
        a, b, ph, pw, t = _exact(rng)
        if 4 <= a * b <= 9: return _tiled(t, a * ph, b * pw), [[a * b, 0]]
def t_c8(g):
    ph, pw, tab = _infer(g); H, W = dims(g)
    if H % ph or W % pw: return None
    return [[(H // ph) * (W // pw), 0]]
t_c8 = _safe(t_c8)
rule("count_tile_repeats_as_digit", "The picture is an exact grid of identical tile copies (smallest rectangular tile); the output is one row of two cells, a cell whose colour value is the number of copies (rows of copies times columns of copies, at most 9), then a 0 cell.", _guard(b_c8, t_c8), t_c8, digits=True, small_ok=True)


# ============================== D. symmetric motifs seen in part (4 rules) ==============================
def _rnd(rng, h, w, cols=[0] + COLS): return [[rng.choice(cols) for _ in range(w)] for _ in range(h)]
def _n(rng): return rng.randint(11, 15) if rng.random() < 0.5 else rng.randint(3, 9)

def b_d1(rng):
    n = _n(rng); Q = _rnd(rng, n, n); top = [a + a[::-1] for a in Q]; M = top + top[::-1]; qi, qj = rng.randint(0, 1), rng.randint(0, 1)
    g = blank(2 * n, 2 * n, 5)
    for r in range(n):
        for c in range(n): g[qi * n + r][qj * n + c] = M[qi * n + r][qj * n + c]
    return g, M
def t_d1(g):
    n = len(g) // 2
    for qi in (0, 1):
        for qj in (0, 1):
            V = [row[qj * n:(qj + 1) * n] for row in g[qi * n:(qi + 1) * n]]
            if all(5 not in r for r in V):
                Q = [r[::-1] for r in V] if qj else V; Q = Q[::-1] if qi else Q
                top = [a + a[::-1] for a in Q]; return top + top[::-1]
    return None
t_d1 = _safe(t_d1)
rule("one_quadrant_window_completed_by_mirror_symmetry", "A square motif with left-right and top-bottom mirror symmetry is visible in only one quadrant, the other three covered by grey 5; the output is the whole motif, mirrored from the visible quadrant across the vertical and horizontal centre lines.", _guard(b_d1, t_d1), t_d1)

def b_d2(rng):
    n = _n(rng); H = rng.randint(3, 30); L = _rnd(rng, H, n); M = [a + a[::-1] for a in L]; g = copy(M); left = rng.random() < 0.5
    for r in range(H):
        for c in range(n): g[r][c if left else n + c] = 5
    return g, M
def t_d2(g):
    n = len(g[0]) // 2; out = copy(g)
    for r in range(len(g)):
        for c in range(n):
            if g[r][c] == 5: out[r][c] = g[r][2 * n - 1 - c]
            if g[r][2 * n - 1 - c] == 5: out[r][2 * n - 1 - c] = g[r][c]
    return out if all(5 not in r for r in out) else None
t_d2 = _safe(t_d2)
rule("half_cover_completed_by_left_right_mirror", "A motif that is mirror-symmetric left to right is visible in one half only, the other half (left or right) covered entirely by grey 5; the output is the whole motif with the covered half the mirror image of the visible half.", _guard(b_d2, t_d2), t_d2)

def b_d3(rng):
    n = rng.randint(11, 28) if rng.random() < 0.5 else rng.randint(4, 12); M = _rnd(rng, n, n)
    for r in range(n):
        for c in range(r): M[r][c] = M[c][r]
    g = copy(M); low = rng.random() < 0.5
    for r in range(n):
        for c in range(n):
            if (r > c if low else r < c): g[r][c] = 5
    return g, M
def t_d3(g):
    out = copy(g)
    for r in range(len(g)):
        for c in range(len(g)):
            if g[r][c] == 5:
                if g[c][r] == 5: return None
                out[r][c] = g[c][r]
    return out
t_d3 = _safe(t_d3)
rule("covered_triangle_completed_by_diagonal_symmetry", "A square motif that is symmetric across its main diagonal has either its whole lower or its whole upper triangle (diagonal excluded) covered by grey 5; the output replaces each grey cell by its mirror across the main diagonal.", _guard(b_d3, t_d3), t_d3)

def b_d4(rng):
    n = _n(rng); Q = _rnd(rng, n, n); R = lambda m: rot90(m)
    TR = R(Q); BR = R(TR); BL = R(BR); M = [Q[i] + TR[i] for i in range(n)] + [BL[i] + BR[i] for i in range(n)]
    qi, qj = rng.randint(0, 1), rng.randint(0, 1); g = blank(2 * n, 2 * n, 5)
    for r in range(n):
        for c in range(n): g[qi * n + r][qj * n + c] = M[qi * n + r][qj * n + c]
    return g, M
def t_d4(g):
    n = len(g) // 2; h = g
    for _ in range(4):
        V = [r[:n] for r in h[:n]]
        if all(5 not in r for r in V) and all(h[r][c] == 5 for r in range(2 * n) for c in range(2 * n) if r >= n or c >= n):
            TR = rot90(V); BR = rot90(TR); BL = rot90(BR); return [V[i] + TR[i] for i in range(n)] + [BL[i] + BR[i] for i in range(n)]
        h = rot90(h)
    return None
t_d4 = _safe(t_d4)
rule("one_quadrant_window_completed_by_fourfold_rotation", "A square motif with four-fold rotational symmetry (turning it 90 degrees maps it onto itself) is visible in only one quadrant, the other three covered by grey 5; the output is the whole motif, built by turning the visible quadrant clockwise 90, 180 and 270 degrees into the successive quadrants going clockwise from it.", _guard(b_d4, t_d4), t_d4)


# ============================== E. nested frames (2 rules) ==============================
def _rings(rng):
    for _ in range(100):
        H, W = _hw(rng, 14, 24, 0.5); K = (min(H, W) - 1) // 2 + 1; p = rng.randint(2, 3); seq = rng.sample(COLS, p)
        if K >= 2 * p + 3: return H, W, K, p, seq
def _ringgrid(H, W, K, f):
    return [[f(min(r, c, H - 1 - r, W - 1 - c)) for c in range(W)] for r in range(H)]
def b_e1(rng):
    H, W, K, p, seq = _rings(rng); D0 = rng.randint(1, K - 2 * p - 1)
    return _ringgrid(H, W, K, lambda k: seq[k % p] if k >= D0 else 0), _ringgrid(H, W, K, lambda k: seq[k % p])
def t_e1(g):
    H, W = dims(g); K = (min(H, W) - 1) // 2 + 1; cols = [g[k][k] for k in range(K)]; D0 = next(k for k in range(K) if cols[k])
    for p in range(1, K):
        if K - D0 >= 2 * p and all(cols[k] == cols[k + p] for k in range(D0, K - p)):
            full = [cols[D0 + ((k - D0) % p)] for k in range(K)]; return _ringgrid(H, W, K, lambda k: full[k])
    return None
t_e1 = _safe(t_e1)
rule("nested_frames_continued_outward_to_edge", "Concentric rectangular frames (frame k is the ring of cells k steps from the nearest grid edge) repeat a short colour sequence, but only the inner frames are drawn and the outer ones are 0; the output continues the sequence outward through every frame to the grid edge, using the shortest sequence length that fits the drawn frames (at least two repeats).", _guard(b_e1, t_e1), t_e1)
def b_e2(rng):
    H, W, K, p, seq = _rings(rng); V = rng.randint(2 * p + 1, K - 2)
    return _ringgrid(H, W, K, lambda k: seq[k % p] if k < V else 0), _ringgrid(H, W, K, lambda k: seq[k % p])
def t_e2(g):
    H, W = dims(g); K = (min(H, W) - 1) // 2 + 1; cols = [g[k][k] for k in range(K)]; V = next(k for k in range(K) if not cols[k])
    for p in range(1, V):
        if V >= 2 * p and all(cols[k] == cols[k + p] for k in range(V - p)):
            full = cols[:V]
            while len(full) < K: full.append(full[-p])
            return _ringgrid(H, W, K, lambda k: full[k])
    return None
t_e2 = _safe(t_e2)
rule("nested_frames_continued_inward_to_the_core", "Concentric rectangular frames (frame k is the ring of cells k steps from the nearest grid edge) repeat a short colour sequence, but only the outer frames are drawn and the inner core is 0; the output continues the sequence inward through every frame to the centre, using the shortest sequence length that fits the drawn frames (at least two repeats).", _guard(b_e2, t_e2), t_e2)


# ============================== F. object chains and lattices (3 rules) ==============================
def _shape3(rng):
    while True:
        sh = random_shape(rng, rng.randint(3, 6)); r0, c0, r1, c1 = bbox(sh)
        if r1 - r0 <= 2 and c1 - c0 <= 2 and (r1 > r0) and (c1 > c0): return sh, r1 + 1, c1 + 1
def _stamp(g, sh, r, c, col):
    for y, x in sh: g[r + y][c + x] = col
def _chain_canon(fn):
    def tf(g):
        tr = False; objs = objects(g, bg=0, conn8=True)
        if len(objs) < 2: return None
        if len({bbox(o)[0] for o in objs}) != 1:
            g = transpose(g); tr = True; objs = objects(g, bg=0, conn8=True)
            if len({bbox(o)[0] for o in objs}) != 1: return None
        out = fn(g, sorted(objs, key=lambda o: bbox(o)[1]))
        return None if out is None else (transpose(out) if tr else out)
    return _safe(tf)
def _chain_fill(mode):
    def fn(g, objs):
        H, W = dims(g); r0, c0, r1, c1 = bbox(objs[0]); col = g[objs[0][0][0]][objs[0][0][1]]; sh = [(r - r0, c - c0) for r, c in objs[0]]; bw = c1 - c0 + 1
        pos = [bbox(o)[1] for o in objs]; s = min(b - a for a, b in zip(pos, pos[1:])); out = blank(H, W)
        lo, hi = (pos[0], pos[-1]) if mode == 'between' else (pos[0] % s, W - bw)
        for c in range(lo, hi + 1, s): _stamp(out, sh, r0, c, col)
        return out
    return fn
def _chain_build(rng, mode):
    sh, bh, bw = _shape3(rng); n = rng.randint(4, 6); s = rng.randint(bw + 1, min(bw + 3, 27 // (n - 1))); need = (n - 1) * s + bw
    W = rng.randint(need, min(30, need + 6)); H = rng.randint(bh + 2, 14) if rng.random() < 0.6 else rng.randint(21, 30)
    r0 = rng.randint(0, H - bh); col = rng.choice(COLS); g = blank(H, W); truth = blank(H, W)
    if mode == 'between':
        c0 = rng.randint(0, W - need); drop = set(rng.sample(range(1, n - 1), rng.randint(1, min(2, n - 2))))
        for i in range(n):
            _stamp(truth, sh, r0, c0 + i * s, col)
            if i not in drop: _stamp(g, sh, r0, c0 + i * s, col)
    else:
        k = rng.randint(3, 4); c0 = rng.randint(0, W - bw - (k - 1) * s) if W - bw - (k - 1) * s >= 0 else 0
        for i in range(k): _stamp(g, sh, r0, c0 + i * s, col)
        for c in range(c0 % s, W - bw + 1, s): _stamp(truth, sh, r0, c, col)
    return (transpose(g), transpose(truth)) if rng.random() < 0.5 else (g, truth)
t_f1 = _chain_canon(_chain_fill('between'))
rule("chain_of_identical_shapes_missing_copies_restored", "Identical small shapes of one colour stand in a straight row (or column) at equal spacing, but one or two copies strictly between the first and last are missing; the output restores every missing copy, the spacing being the smallest gap between two neighbouring visible copies.", _guard(lambda rng: _chain_build(rng, 'between'), t_f1), t_f1)
t_f2 = _chain_canon(_chain_fill('edges'))
rule("chain_of_shapes_continued_to_both_edges", "Three or four identical small shapes of one colour stand in a straight row (or column) at equal spacing; the output continues the row in both directions with further copies at the same spacing and phase, as many as fit completely inside the grid, the spacing being the smallest gap between two neighbouring visible copies.", _guard(lambda rng: _chain_build(rng, 'edges'), t_f2), t_f2)

def b_f3(rng):
    sh, bh, bw = _shape3(rng); sr, sc = rng.randint(bh + 1, bh + 3), rng.randint(bw + 1, bw + 3); H, W = _hw(rng, 12, 20, 0.5); col = rng.choice(COLS)
    if H < sr + bh + 1 or W < sc + bw + 1: return None
    r0, c0 = rng.randint(0, H - sr - bh), rng.randint(0, W - sc - bw); g = blank(H, W)
    pts = [(r0, c0), (r0, c0 + sc), (r0 + sr, c0), (r0 + sr, c0 + sc)]; pts.pop(rng.randrange(4))
    for r, c in pts: _stamp(g, sh, r, c, col)
    truth = blank(H, W)
    for r in range(r0 % sr, H - bh + 1, sr):
        for c in range(c0 % sc, W - bw + 1, sc): _stamp(truth, sh, r, c, col)
    return g, truth
def t_f3(g):
    H, W = dims(g); objs = objects(g, bg=0, conn8=True)
    if len(objs) != 3: return None
    bb = [bbox(o) for o in objs]; rs = sorted({b[0] for b in bb}); cs = sorted({b[1] for b in bb})
    if len(rs) != 2 or len(cs) != 2: return None
    sr, sc = rs[1] - rs[0], cs[1] - cs[0]; r0, c0, r1, c1 = bb[0]; col = g[objs[0][0][0]][objs[0][0][1]]; sh = [(r - r0, c - c0) for r, c in objs[0]]; bh, bw = r1 - r0 + 1, c1 - c0 + 1
    out = blank(H, W)
    for r in range(rs[0] % sr, H - bh + 1, sr):
        for c in range(cs[0] % sc, W - bw + 1, sc): _stamp(out, sh, r, c, col)
    return out
t_f3 = _safe(t_f3)
rule("three_lattice_copies_complete_the_lattice", "Three identical small shapes of one colour sit at three corners of a rectangle (an L of copies) on a grid lattice; the output draws the shape at every lattice position that fits completely inside the grid, the lattice having the row spacing and column spacing implied by the three copies and passing through them.", _guard(b_f3, t_f3), t_f3)


# ============================== G. torn pieces (2 rules) ==============================
def _torn(rng, rotate):
    for _ in range(200):
        H, W = _hw(rng, 10, 18, 0.4); H = min(H, 24); ph, pw = rng.randint(2, 4), rng.randint(2, 4); t = _tile(rng, ph, pw, COLS)
        hh = rng.randint(2, 4); ww = hh if rotate else rng.randint(2, 4)
        if not t or H < hh * 3 or W < ww * 3: continue
        ra, ca, rb, cb = rng.randint(0, H - hh), rng.randint(0, W - ww), rng.randint(0, H - hh), rng.randint(0, W - ww)
        if not (ra + hh + 1 <= rb or rb + hh + 1 <= ra or ca + ww + 1 <= cb or cb + ww + 1 <= ca): continue
        full = _tiled(t, H, W); A = [r[ca:ca + ww] for r in full[ra:ra + hh]]; B = [r[cb:cb + ww] for r in full[rb:rb + hh]]
        if A == B or (rotate and rot90(rot90(rot90(rot90(A)))) == B): continue
        main = copy(full); rect(main, ra, ca, ra + hh - 1, ca + ww - 1, 0); rect(main, rb, cb, rb + hh - 1, cb + ww - 1, 0)
        show = rot90(A) if rotate else A
        piece = [row + [0] * (W - ww) for row in show]; inp = main + [[5] * W] + piece
        truth = copy(main)
        for i in range(hh):
            for j in range(ww): truth[ra + i][ca + j] = A[i][j]
        return inp, truth
def _torn_tf(rotate):
    def tf(g):
        sep = next(i for i, r in enumerate(g) if all(v == 5 for v in r)); main = g[:sep]; pc = g[sep + 1:]
        r0, c0, r1, c1 = bbox(cells(pc, lambda v: v)); piece = crop(pc, r0, c0, r1, c1)
        cand = rot90(rot90(rot90(piece))) if rotate else piece; hh, ww = len(cand), len(cand[0])
        ph, pw, tab = _infer(main, (0,)); out = copy(main); hit = []
        for comp in components(main, 0, conn8=False):
            a, b, c, d = bbox(comp)
            if (c - a + 1, d - b + 1) == (hh, ww) and len(comp) == hh * ww and all(tab[(a + i) % ph, (b + j) % pw] == cand[i][j] for i in range(hh) for j in range(ww)): hit.append((a, b))
        if len(hit) != 1: return None
        a, b = hit[0]
        for i in range(hh):
            for j in range(ww): out[a + i][b + j] = cand[i][j]
        return out
    return _safe(tf)
t_g1 = _torn_tf(False)
rule("torn_piece_pasted_into_the_hole_it_matches", "A periodic tiling (with no 0 or grey 5 cells) has two rectangular holes of 0 of the same size; below a full grey 5 separator row sits a loose piece (top-left, rest 0); the output is the tiling only (separator and piece removed) with the piece pasted into the one hole whose cells the tiling's smallest period predicts equal to the piece, the other hole staying 0.", _guard(lambda rng: _torn(rng, False), t_g1), t_g1)
t_g2 = _torn_tf(True)
rule("torn_piece_turned_back_then_pasted_in", "A periodic tiling (with no 0 or grey 5 cells) has two square holes of 0 of the same size; below a full grey 5 separator row sits a loose square piece (top-left, rest 0) that was turned 90 degrees clockwise; the output is the tiling only (separator and piece removed) with the piece turned back 90 degrees anticlockwise and pasted into the one hole whose cells the tiling's smallest period predicts equal to it, the other hole staying 0.", _guard(lambda rng: _torn(rng, True), t_g2), t_g2)


# ============================== I. prefixes and M. peepholes ==============================
def b_i1(rng):
    W = rng.randint(21, 30) if rng.random() < 0.5 else rng.randint(12, 20); n = rng.randint(2, 10); g, full = [], []
    for _ in range(n):
        p = rng.randint(2, 5); s = _seq(rng, p, COLS); row = [s[c % p] for c in range(W)]; L = rng.randint(2 * p + 1, max(2 * p + 1, W - 3))
        full.append(row); g.append(row[:L] + [0] * (W - L))
    return g, full
def t_i1(g):
    out = []
    for row in g:
        L = next((i for i, v in enumerate(row) if v == 0), len(row))
        for p in range(1, L // 2 + 1):
            if all(row[c] == row[c - p] for c in range(p, L)): out.append([row[c % p] for c in range(len(row))]); break
        else: return None
    return out
t_i1 = _safe(t_i1)
rule("row_prefixes_continued_by_shortest_period", "Each row starts with a visible run of colours that repeats with a short period and then continues as 0 to the right edge; the output continues every row to the edge, using that row's shortest period consistent with its visible run (the run covers at least two periods).", _guard(b_i1, t_i1), t_i1)

def b_m1(rng):
    for _ in range(100):
        H, W = _hw(rng); ph, pw = rng.choice([3, 5]), rng.choice([3, 5]); t = _tile(rng, ph, pw, COLS)
        if t: break
    full = _tiled(t, H, W); g = [[full[r][c] if r % 2 == 0 and c % 2 == 0 else 5 for c in range(W)] for r in range(H)]; return g, full
def t_m1(g):
    ph, pw, tab = _infer(g, (5,)); return [[tab[(r % ph, c % pw)] for c in range(len(g[0]))] for r in range(len(g))]
t_m1 = _safe(t_m1)
rule("peephole_mesh_tiling_fully_restored", "A periodic tiling is seen only through a mesh of peepholes: cells at even row and even column positions (counting from 0) show the tiling, every other cell is grey 5; the output is the complete tiling, with the smallest rectangular period that fits the visible cells and is seen in every phase.", _guard(b_m1, t_m1), t_m1)
