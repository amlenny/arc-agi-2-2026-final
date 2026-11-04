# b068_plumbing.py -- PLUMBING: FOLLOWING PIPES AND LABELLING ENDS. Grey (5) pipes are 1-cell-wide paths or trees that
# never touch each other; they end at open ends, coloured caps, fittings, taps and valves. Rules label ends, measure
# and recolour pipes by length/bends, mark junctions and crossings, fill water from taps, split flow at T-junctions.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

P = 5
N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
ALLC = [1, 2, 3, 4, 6, 7, 8, 9]
CAPC = [1, 3, 4, 6, 7, 8, 9]


# ---------------- generation helpers ----------------
def _sz(rng, big=0.4, lo=7, hi=18):
    if rng.random() < big:
        return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _nocc(g, r, c):
    h, w = dims(g)
    return sum(1 for dr, dc in N4 if 0 <= r + dr < h and 0 <= c + dc < w and g[r + dr][c + dc] != 0)


def _fr(g, r, c):
    h, w = dims(g)
    return 0 <= r < h and 0 <= c < w and g[r][c] == 0


def _walk(rng, g, start, n, col, straight=0.55, prev=None):
    r, c = start
    if not _fr(g, r, c) or _nocc(g, r, c) != (0 if prev is None else 1):
        return None
    g[r][c] = col; path = [(r, c)]
    d = (r - prev[0], c - prev[1]) if prev else None
    while len(path) < n:
        r, c = path[-1]
        opts = [dd for dd in N4 if _fr(g, r + dd[0], c + dd[1]) and _nocc(g, r + dd[0], c + dd[1]) == 1]
        if not opts:
            break
        d = d if (d in opts and rng.random() < straight) else rng.choice(opts)
        g[r + d[0]][c + d[1]] = col; path.append((r + d[0], c + d[1]))
    return path


def _undo(g, cells_):
    for r, c in cells_:
        g[r][c] = 0


def _wp(rng, g, start, lo, hi, col=P, straight=0.55, prev=None):
    p = _walk(rng, g, start, rng.randint(lo, hi), col, straight, prev)
    if p and len(p) >= lo:
        return p
    if p:
        _undo(g, p)
    return None


def _attach(rng, g, cell, col):
    r, c = cell
    opts = [(r + dr, c + dc) for dr, dc in N4 if _fr(g, r + dr, c + dc) and _nocc(g, r + dr, c + dc) == 1]
    if not opts:
        return None
    a, b = rng.choice(opts); g[a][b] = col
    return (a, b)


def _bends_of(p):
    return sum(1 for i in range(1, len(p) - 1)
               if (p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]) != (p[i + 1][0] - p[i][0], p[i + 1][1] - p[i][1]))


def mk(rng, lo=3, hi=12, capmode=0, capcols=ALLC, kmin=3, big=0.4, straight=0.55, minbends=0, wall=(), lo_sz=7, hi_sz=18):
    """Paths of grey. capmode 0 none, 1 one cap at a random end, 2 caps at both ends, 3 each end capped w.p. .6.
    Returns (grid, recs) with recs = dicts(p=path cells in order, caps=[cap0 or None, cap1 or None])."""
    for _ in range(200):
        h, w = _sz(rng, big, lo_sz, hi_sz)
        g = blank(h, w); recs = []
        k = rng.randint(kmin, max(kmin + 1, min(14, h * w // 45)))
        for a in range(k * 8):
            if len(recs) >= k:
                break
            if len(recs) < len(wall):
                s = (rng.randrange(h), 0 if wall[len(recs)] == 'l' else w - 1)
            else:
                s = (rng.randrange(h), rng.randrange(w))
            p = _wp(rng, g, s, lo, hi, P, straight)
            if not p:
                continue
            if _bends_of(p) < minbends:
                _undo(g, p); continue
            caps = [None, None]; placed = []; ok = True
            if capmode == 1:
                es = [rng.choice((0, -1))]
            elif capmode == 2:
                es = [0, -1]
            elif capmode == 3:
                es = [e for e in (0, -1) if rng.random() < 0.6]
            else:
                es = []
            for e in es:
                cc = rng.choice(capcols)
                cell = _attach(rng, g, p[e], cc)
                if cell is None:
                    if capmode in (1, 2):
                        ok = False
                    continue
                caps[e] = (cell, cc); placed.append(cell)
            if not ok:
                _undo(g, p + placed); continue
            recs.append(dict(p=p, caps=caps))
        if len(recs) >= kmin:
            return g, recs
    raise RuntimeError("mk failed")


def forest(rng, kmin=3, lo=5, hi=14, big=0.4, capp=0.0, capcols=CAPC, lo_sz=8, hi_sz=18):
    for _ in range(200):
        h, w = _sz(rng, big, lo_sz, hi_sz)
        g = blank(h, w); trees = []
        k = rng.randint(kmin, max(kmin + 1, min(10, h * w // 55)))
        for _a in range(k * 8):
            if len(trees) >= k:
                break
            s = (rng.randrange(h), rng.randrange(w))
            if not _fr(g, *s) or _nocc(g, *s):
                continue
            n = rng.randint(lo, hi); g[s[0]][s[1]] = P; cs = [s]
            for _b in range(300):
                if len(cs) >= n:
                    break
                r, c = rng.choice(cs[-4:]) if rng.random() < 0.7 else rng.choice(cs)
                dr, dc = rng.choice(N4)
                if _fr(g, r + dr, c + dc) and _nocc(g, r + dr, c + dc) == 1:
                    g[r + dr][c + dc] = P; cs.append((r + dr, c + dc))
            if len(cs) < lo:
                _undo(g, cs); continue
            caps = []
            if capp:
                for (r, c) in cs:
                    if sum(1 for dr, dc in N4 if 0 <= r + dr < h and 0 <= c + dc < w and g[r + dr][c + dc] == P) == 1 and rng.random() < capp:
                        cell = _attach(rng, g, (r, c), rng.choice(capcols))
                        if cell: caps.append(cell)
            trees.append(dict(cells=cs, caps=caps))
        if len(trees) >= kmin:
            return g, trees
    raise RuntimeError("forest failed")


# ---------------- reading helpers (work from the grid only) ----------------
def _deg(g, r, c, cols=(P,)):
    h, w = dims(g)
    return sum(1 for dr, dc in N4 if 0 <= r + dr < h and 0 <= c + dc < w and g[r + dr][c + dc] in cols)


def _nbs(g, r, c):
    h, w = dims(g)
    return [(r + dr, c + dc) for dr, dc in N4 if 0 <= r + dr < h and 0 <= c + dc < w]


def _leaves(g, comp, cols=(P,)):
    return [(r, c) for r, c in comp if _deg(g, r, c, cols) == 1]


def _capof(g, cell, pipecols=(P,)):
    return [(n, g[n[0]][n[1]]) for n in _nbs(g, *cell) if g[n[0]][n[1]] != 0 and g[n[0]][n[1]] not in pipecols]


def _order(g, comp, start, cols=(P,)):
    s = set(comp); out = [start]; prev = None; cur = start
    while True:
        nx = [n for n in _nbs(g, *cur) if n in s and n != prev]
        if len(nx) != 1:
            return out if not nx else None
        prev, cur = cur, nx[0]; out.append(cur)


def _mcomps(g, cols):
    h, w = dims(g); seen = set(); out = []
    for r in range(h):
        for c in range(w):
            if (r, c) in seen or g[r][c] not in cols:
                continue
            comp = []; st = [(r, c)]; seen.add((r, c))
            while st:
                y, x = st.pop(); comp.append((y, x))
                for n in _nbs(g, y, x):
                    if n not in seen and g[n[0]][n[1]] in cols:
                        seen.add(n); st.append(n)
            out.append(comp)
    return out


def _isbend(g, r, c, cols=(P,)):
    h, w = dims(g)
    def at(y, x): return 0 <= y < h and 0 <= x < w and g[y][x] in cols
    v = at(r - 1, c) + at(r + 1, c); hz = at(r, c - 1) + at(r, c + 1)
    return v == 1 and hz == 1


def _pc(g):
    return components(g, P)


# ================================================================== 1
def gi_far_end(rng):
    return mk(rng, 3, 12, 1, ALLC)[0]
def tf_far_end(g):
    out = copy(g)
    for comp in _pc(g):
        lv = _leaves(g, comp); caps = [(l, v) for l in lv for _, v in _capof(g, l)]
        if len(lv) != 2 or len(caps) != 1:
            return None
        far = [l for l in lv if l != caps[0][0]][0]
        out[far[0]][far[1]] = caps[0][1]
    return out
rule("pipe_far_end_takes_cap_colour", "Each grey (5) pipe has one coloured cap at one end; the pipe cell at the opposite open end takes the cap's colour and everything else stays.", gi_far_end, tf_far_end)


# ================================================================== 2
def gi_bands(rng):
    return mk(rng, 2, 17, 0, kmin=4)[0]
def tf_bands(g):
    out = copy(g)
    for comp in _pc(g):
        n = len(comp); col = 3 if n <= 5 else (4 if n <= 10 else 2)
        for r, c in comp: out[r][c] = col
    return out
rule("pipe_length_band_recolour", "Recolour each grey (5) pipe by its cell count: 5 cells or fewer green (3), 6 to 10 yellow (4), 11 or more red (2).", gi_bands, tf_bands)


# ================================================================== 3
def gi_bends(rng):
    return mk(rng, 4, 14, 0)[0]
def tf_bends(g):
    out = copy(g); H, W = dims(g)
    for r in range(H):
        for c in range(W):
            if g[r][c] == P and _isbend(g, r, c):
                out[r][c] = 2
    return out
rule("pipe_mark_every_bend", "Every grey (5) pipe cell whose two pipe neighbours are one horizontal and one vertical (a bend) becomes red (2); straight cells and ends stay grey.", gi_bends, tf_bends)


# ================================================================== 4
def gi_junc(rng):
    return forest(rng, 3, 6, 16)[0]
def tf_junc(g):
    out = copy(g); H, W = dims(g)
    for r in range(H):
        for c in range(W):
            if g[r][c] == P and _deg(g, r, c) >= 3:
                out[r][c] = 2
    return out
rule("pipe_mark_junctions", "Every grey (5) pipe cell with three or four grey neighbours (a junction) becomes red (2).", gi_junc, tf_junc)


# ================================================================== 5
def tf_juncdeg(g):
    out = copy(g); H, W = dims(g)
    for r in range(H):
        for c in range(W):
            if g[r][c] == P and _deg(g, r, c) >= 3:
                out[r][c] = 2 if _deg(g, r, c) == 3 else 3
    return out
rule("pipe_junction_colour_by_degree", "In a grey (5) pipe network, a cell with exactly three grey neighbours becomes red (2) and a cell with four grey neighbours becomes green (3).", gi_junc, tf_juncdeg)


# ---------------- crossing scenes ----------------
def _lines(rng, vert_over=None):
    for _ in range(100):
        h, w = _sz(rng, 0.4, 10, 20)
        rows = []; cols_ = []
        for _a in range(rng.randint(1, max(1, h // 5)) * 4):
            r = rng.randint(1, h - 2)
            if all(abs(r - x) >= 2 for x in rows) and len(rows) < max(2, h // 5): rows.append(r)
        for _a in range(rng.randint(1, max(1, w // 5)) * 4):
            c = rng.randint(1, w - 2)
            if all(abs(c - x) >= 2 for x in cols_) and len(cols_) < max(2, w // 5): cols_.append(c)
        hs = []; vs = []
        for r in rows:
            a = rng.randint(0, w - 6); b = rng.randint(a + 5, w - 1); hs.append((r, a, b))
        for c in cols_:
            a = rng.randint(0, h - 6); b = rng.randint(a + 5, h - 1)
            if a in rows or b in rows: continue
            vs.append((c, a, b))
        cr = [(r, c) for r, a, b in hs for c, p, q in vs if a < c < b and p < r < q]
        if cr and len(cr) <= 12:
            return h, w, hs, vs, cr
    raise RuntimeError("lines")


def gi_cross_over(rng):
    h, w, hs, vs, cr = _lines(rng); g = blank(h, w)
    for r, a, b in hs:
        for c in range(a, b + 1): g[r][c] = 1
    for c, a, b in vs:
        for r in range(a, b + 1): g[r][c] = 2
    return g
def tf_cross_over(g):
    out = copy(g); H, W = dims(g)
    for r in range(H):
        for c in range(1, W - 1):
            if g[r][c] == 2 and g[r][c - 1] == 1 and g[r][c + 1] == 1:
                out[r][c] = 1
    return out
rule("pipe_cross_horizontal_on_top", "Horizontal pipes are blue (1) and vertical pipes red (2); wherever a red cell has blue cells on both its left and right (the vertical pipe drawn on top of a crossing), repaint it blue so the horizontal pipe is on top.", gi_cross_over, tf_cross_over)


def gi_cross5(rng):
    h, w, hs, vs, cr = _lines(rng); g = blank(h, w)
    for r, a, b in hs:
        for c in range(a, b + 1): g[r][c] = P
    for c, a, b in vs:
        for r in range(a, b + 1): g[r][c] = P
    return g
def _cross_cells(g):
    H, W = dims(g)
    return [(r, c) for r in range(H) for c in range(W) if g[r][c] == P and _deg(g, r, c) == 4]
def tf_tunnel(g):
    out = copy(g); cr = _cross_cells(g)
    for r, c in cr:
        for dr in (-1, 1):
            if g[r + dr][c] == P: out[r + dr][c] = 4
    for r, c in cr: out[r][c] = 1
    return out
rule("pipe_crossing_tunnel_vertical_under", "Where a vertical and a horizontal grey (5) pipe cross (a grey cell with four grey neighbours) the horizontal pipe is on top: the crossing cell becomes blue (1) and the two vertical-pipe cells directly above and below it become yellow (4) as tunnel mouths; the crossing wins where mouths overlap.", gi_cross5, tf_tunnel)
def tf_crossbar(g):
    n = len(_cross_cells(g))
    return [[2] * n + [0] * (12 - n)] if 1 <= n <= 11 else None
rule("pipe_crossings_count_bar", "Count the crossings (grey 5 cells with four grey neighbours) and output a single row of 12 cells whose first n cells are red (2) and the rest black.", gi_cross5, tf_crossbar, small_ok=True)


# ================================================================== 9
def gi_wallbar(rng):
    return mk(rng, 3, 10, 0, kmin=4, wall=['r'] * rng.randint(1, 4))[0]
def tf_wallbar(g):
    W = len(g[0]); n = sum(1 for comp in _pc(g) if any(c == W - 1 for _, c in comp))
    return [[2] * n + [0] * (12 - n)] if 1 <= n <= 11 else None
rule("pipe_count_reaching_right_wall", "Count the grey (5) pipes that have at least one cell in the rightmost column and output one row of 12 cells whose first n cells are red (2) and the rest black.", gi_wallbar, tf_wallbar, small_ok=True)


# ================================================================== 10
def gi_pipes(rng):
    return mk(rng, 3, 14, 0, kmin=3)[0]
def tf_longest(g):
    cs = _pc(g); best = max(range(len(cs)), key=lambda i: (len(cs[i]), -i)); out = copy(g)
    for r, c in cs[best]: out[r][c] = 2
    return out
rule("pipe_longest_recoloured", "The grey (5) pipe with the most cells turns red (2); on a tie the pipe whose first cell comes first in reading order (top row, then leftmost) wins.", gi_pipes, tf_longest)


# ================================================================== 11
def gi_deadend(rng):
    return mk(rng, 3, 12, 3, ALLC, kmin=4)[0]
def tf_deadend(g):
    out = copy(g)
    for comp in _pc(g):
        lv = _leaves(g, comp)
        if len(lv) != 2: return None
        if not all(_capof(g, l) for l in lv):
            for r, c in comp: out[r][c] = 0
    return out
rule("pipe_dead_end_erased", "A grey (5) pipe is kept only if both of its end cells touch a coloured cap; any grey pipe with an uncapped end is erased to black (the caps stay).", gi_deadend, tf_deadend)


# ================================================================== 12
def gi_samecap(rng):
    cc = rng.sample(ALLC, rng.choice((2, 3)))
    return mk(rng, 3, 12, 2, cc, kmin=4)[0]
def tf_samecap(g):
    out = copy(g)
    for comp in _pc(g):
        lv = _leaves(g, comp)
        if len(lv) != 2: return None
        cs = [{v for _, v in _capof(g, l)} for l in lv]
        if len(cs[0]) != 1 or cs[0] != cs[1]:
            for r, c in comp: out[r][c] = 0
    return out
rule("pipe_same_cap_pair_kept", "Each grey (5) pipe has a coloured cap at both ends; keep the pipe when the two caps have the same colour, otherwise erase the pipe to black (caps stay).", gi_samecap, tf_samecap)


# ================================================================== 13
def gi_morebends(rng):
    return mk(rng, 4, 14, 0, kmin=3)[0]
def tf_mostbends(g):
    cs = _pc(g); sc = [sum(1 for r, c in comp if _isbend(g, r, c)) for comp in cs]
    best = max(range(len(cs)), key=lambda i: (sc[i], -i)); out = copy(g)
    for r, c in cs[best]: out[r][c] = 2
    return out
rule("pipe_most_bends_recoloured", "The grey (5) pipe with the most bend cells turns red (2); on a tie the pipe whose first cell comes first in reading order wins.", gi_morebends, tf_mostbends)


# ================================================================== 14
def _tapped(rng, valves=False):
    g, trees = forest(rng, 3, 6, 16); taps = 0
    for i, t in enumerate(trees):
        if rng.random() < 0.5 or (i == len(trees) - 1 and not taps):
            if i == len(trees) - 1 and taps == len(trees) - 1 and len(trees) > 1: continue
            r, c = rng.choice(t['cells'])
            if _attach(rng, g, (r, c), 3): taps += 1
    if valves:
        for t in trees:
            dc = [(r, c) for r, c in t['cells'] if _deg(g, r, c) == 2]
            for r, c in rng.sample(dc, min(len(dc), rng.randint(0, 3))):
                g[r][c] = rng.choice((2, 4))
    return g
def gi_water(rng):
    return _tapped(rng)
def _bfs_fill(g, passc, out):
    H, W = dims(g); seen = set(); st = [(r, c) for r in range(H) for c in range(W) if g[r][c] == 3]
    for t in st:
        for n in _nbs(g, *t):
            if g[n[0]][n[1]] in passc and n not in seen:
                seen.add(n); q = [n]
                while q:
                    y, x = q.pop(); out[y][x] = 8
                    for m in _nbs(g, y, x):
                        if g[m[0]][m[1]] in passc and m not in seen:
                            seen.add(m); q.append(m)
    return out
def tf_water(g):
    return _bfs_fill(g, (P,), copy(g))
rule("pipe_water_floods_tapped_network", "Every grey (5) pipe network that touches a green (3) tap turns cyan (8) in full; taps stay and untapped networks stay grey.", gi_water, tf_water)


# ================================================================== 15
def gi_numcap(rng):
    return mk(rng, 3, 14, 1, CAPC, kmin=3)[0]
def tf_numcap(g):
    out = copy(g)
    for comp in _pc(g):
        lv = _leaves(g, comp); cl = [l for l in lv if _capof(g, l)]
        if len(lv) != 2 or len(cl) != 1: return None
        d = _capof(g, cl[0])[0][1]; o = _order(g, comp, cl[0])
        for r, c in o[:d]: out[r][c] = 2
    return out
rule("pipe_numbered_cap_fills_n_cells", "A digit cap (value d, never 2 or 5) sits at one end of a grey (5) pipe; the first d pipe cells counted from the cap turn red (2), or the whole pipe if it has fewer than d cells.", gi_numcap, tf_numcap, digits=True)


# ================================================================== 16
def gi_tsplit(rng):
    for _ in range(100):
        h, w = _sz(rng, 0.4, 9, 18); g = blank(h, w); n_ok = 0
        for _a in range(rng.randint(2, max(2, h * w // 90)) * 6):
            if n_ok >= max(2, h * w // 90): break
            p = _wp(rng, g, (rng.randrange(h), rng.randrange(w)), 7, 12)
            if not p: continue
            cap = _attach(rng, g, p[0], rng.choice((2, 3, 4, 6, 7, 8)))
            if not cap: _undo(g, p); continue
            i = rng.randint(2, len(p) - 3); r, c = p[i]
            opts = [n for n in _nbs(g, r, c) if _fr(g, *n) and _nocc(g, *n) == 1]
            if not opts: _undo(g, p + [cap]); continue
            b = _wp(rng, g, rng.choice(opts), 3, 8, prev=(r, c))
            if not b: _undo(g, p + [cap]); continue
            n_ok += 1
        if n_ok >= 2: return g
    raise RuntimeError
def tf_tsplit(g):
    out = copy(g)
    for comp in _pc(g):
        lv = _leaves(g, comp); cl = [l for l in lv if _capof(g, l)]
        if len(lv) != 3 or len(cl) != 1: return None
        n = _capof(g, cl[0])[0][1]; arms = sorted(l for l in lv if l != cl[0])
        out[arms[0][0]][arms[0][1]] = n // 2 + n % 2; out[arms[1][0]][arms[1][1]] = n // 2
    return out
rule("pipe_tjunction_splits_flow", "A digit cap n (2,3,4,6,7 or 8) feeds a grey (5) pipe with one T-junction; the two far open ends become n//2 each, and if n is odd the end that comes first in reading order (top row, then leftmost) gets n//2+1.", gi_tsplit, tf_tsplit, digits=True)


# ================================================================== 17
def tf_junccount(g):
    H, W = dims(g)
    n = sum(1 for r in range(H) for c in range(W) if g[r][c] == P and _deg(g, r, c) >= 3)
    return [[2] * n + [0] * (12 - n)] if 1 <= n <= 11 else None
rule("pipe_junction_count_bar", "Count the grey (5) cells that have three or four grey neighbours and output one row of 12 cells whose first n cells are red (2) and the rest black.", gi_junc, tf_junccount, small_ok=True)


# ================================================================== 18
def gi_forestcap(rng):
    return forest(rng, 3, 6, 16, capp=0.45, capcols=[1, 3, 4, 6, 7, 8, 9])[0]
def tf_leafmark(g):
    out = copy(g); H, W = dims(g)
    for r in range(H):
        for c in range(W):
            if g[r][c] == P and _deg(g, r, c) == 1 and not _capof(g, (r, c)):
                out[r][c] = 2
    return out
rule("pipe_uncapped_ends_marked", "In a branching grey (5) pipe network, every grey end cell (one grey neighbour) that does not touch a coloured cap turns red (2).", gi_forestcap, tf_leafmark)


# ================================================================== 19
def tf_spur(g):
    out = copy(g); H, W = dims(g)
    for r in range(H):
        for c in range(W):
            if g[r][c] == P and _deg(g, r, c) == 1:
                n = [m for m in _nbs(g, r, c) if g[m[0]][m[1]] == P][0]
                if _deg(g, *n) >= 3: out[r][c] = 0
    return out
rule("pipe_one_cell_spurs_cut", "Erase every grey (5) end cell whose single grey neighbour is a junction (a grey cell with three or four grey neighbours), cutting one-cell stubs; all other cells stay.", gi_junc, tf_spur)


# ================================================================== 20
def gi_caplen(rng):
    return mk(rng, 2, 14, 1, [1], kmin=3)[0]
def tf_caplen(g):
    out = copy(g)
    for comp in _pc(g):
        caps = [cp for l in _leaves(g, comp) for cp, _ in _capof(g, l)]
        if len(caps) != 1: return None
        out[caps[0][0]][caps[0][1]] = min(len(comp), 9)
    return out
rule("pipe_cap_shows_length", "The blue (1) cap on one end of each grey (5) pipe is replaced by the number of grey cells in that pipe, with 9 as the maximum.", gi_caplen, tf_caplen, digits=True)


# ================================================================== 21
def gi_fittings(rng):
    g, recs = mk(rng, 5, 14, 0, kmin=3)
    for rc in recs:
        L = len(rc['p']); i = rng.randint(1, L - 4); j = rng.randint(i + 2, L - 2)
        for k in (i, j): g[rc['p'][k][0]][rc['p'][k][1]] = 2
    return g
def tf_fittings(g):
    out = copy(g)
    for comp in _mcomps(g, (P, 2)):
        lv = _leaves(g, comp, (P, 2))
        if len(lv) != 2: return None
        o = _order(g, comp, min(lv), (P, 2)); idx = [i for i, (r, c) in enumerate(o) if g[r][c] == 2]
        if len(idx) != 2: return None
        for r, c in o[idx[0] + 1:idx[1]]: out[r][c] = 3
    return out
rule("pipe_segment_between_fittings", "Each grey (5) pipe has exactly two red (2) fitting cells inside it; the pipe cells strictly between the two fittings turn green (3).", gi_fittings, tf_fittings)


# ================================================================== 22
def gi_turns(rng):
    return mk(rng, 5, 14, 1, [1], kmin=3)[0]
def tf_turns(g):
    out = copy(g)
    for comp in _pc(g):
        cl = [l for l in _leaves(g, comp) if _capof(g, l)]
        if len(cl) != 1: return None
        o = _order(g, comp, cl[0])
        # first step direction from the cap into the pipe is the direction of travel
        cap = _capof(g, cl[0])[0][0]; prev = cap
        for i, (r, c) in enumerate(o):
            if i + 1 >= len(o): break
            d1 = (r - prev[0], c - prev[1]); d2 = (o[i + 1][0] - r, o[i + 1][1] - c)
            cr = d1[0] * d2[1] - d1[1] * d2[0]
            if cr: out[r][c] = 2 if cr > 0 else 3
            prev = (r, c)
    return out
rule("pipe_turn_direction_from_cap", "Walking each grey (5) pipe away from its blue (1) cap, every bend cell turns red (2) if the walker turns left there and green (3) if it turns right.", gi_turns, tf_turns)


# ================================================================== 23
def gi_runs(rng):
    return mk(rng, 6, 18, 0, straight=0.8, kmin=3)[0]
def tf_runs(g):
    out = copy(g); H, W = dims(g)
    for r in range(H):
        c = 0
        while c < W:
            if g[r][c] == P:
                e = c
                while e + 1 < W and g[r][e + 1] == P: e += 1
                if e - c + 1 >= 5:
                    for x in range(c, e + 1): out[r][x] = 2
                c = e + 1
            else: c += 1
    for c in range(W):
        r = 0
        while r < H:
            if g[r][c] == P:
                e = r
                while e + 1 < H and g[e + 1][c] == P: e += 1
                if e - r + 1 >= 5:
                    for y in range(r, e + 1): out[y][c] = 3
                r = e + 1
            else: r += 1
    return out
rule("pipe_long_straight_runs", "In grey (5) pipes, every maximal horizontal run of 5 or more grey cells turns red (2) and every maximal vertical run of 5 or more turns green (3); shorter runs stay grey.", gi_runs, tf_runs)


# ================================================================== 24
def _gaps(g):
    H, W = dims(g); out = {}
    for r in range(H):
        for c in range(W):
            if g[r][c]: continue
            hz = 0 < c < W - 1 and g[r][c - 1] == P and g[r][c + 1] == P
            vt = 0 < r < H - 1 and g[r - 1][c] == P and g[r + 1][c] == P
            if hz and not vt: out[(r, c)] = 2
            elif vt and not hz: out[(r, c)] = 4
            elif hz and vt: out[(r, c)] = None
    return out
def gi_gaps(rng):
    for _ in range(60):
        g, recs = mk(rng, 6, 15, 0, straight=0.7, kmin=3); pun = {}
        for rc in recs:
            p = rc['p']; ok = [i for i in range(1, len(p) - 1) if (p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]) == (p[i + 1][0] - p[i][0], p[i + 1][1] - p[i][1])]
            if ok and rng.random() < 0.8:
                i = rng.choice(ok); r, c = p[i]; pun[(r, c)] = 2 if p[i][0] == p[i - 1][0] else 4; g[r][c] = 0
        if pun and _gaps(g) == pun: return g
    raise RuntimeError
def tf_gaps(g):
    gp = _gaps(g)
    if None in gp.values(): return None
    out = copy(g)
    for (r, c), v in gp.items(): out[r][c] = v
    return out
rule("pipe_gap_leaks_filled_by_direction", "Fill every black cell that has grey (5) pipe cells on both its left and right with red (2), and every black cell with grey on both its top and bottom with yellow (4).", gi_gaps, tf_gaps)


# ---------------- ring scenes ----------------
def _rings(rng, openp):
    for _ in range(100):
        h, w = _sz(rng, 0.4, 10, 20); g = blank(h, w); n = 0
        want = rng.randint(2, max(2, min(6, h * w // 60)))
        for _a in range(want * 10):
            if n >= want: break
            rh, rw = rng.randint(3, 7), rng.randint(3, 7)
            if rh > h or rw > w: continue
            r0, c0 = rng.randint(0, h - rh), rng.randint(0, w - rw)
            if any(g[y][x] for y in range(max(0, r0 - 1), min(h, r0 + rh + 1)) for x in range(max(0, c0 - 1), min(w, c0 + rw + 1))): continue
            rect(g, r0, c0, r0 + rh - 1, c0 + rw - 1, P, fill=False)
            if rng.random() < openp:
                side = [(r0, c) for c in range(c0 + 1, c0 + rw - 1)] + [(r0 + rh - 1, c) for c in range(c0 + 1, c0 + rw - 1)] + \
                       [(r, c0) for r in range(r0 + 1, r0 + rh - 1)] + [(r, c0 + rw - 1) for r in range(r0 + 1, r0 + rh - 1)]
                y, x = rng.choice(side); g[y][x] = 0
            n += 1
        if n >= 2: return g
    raise RuntimeError
def gi_loops(rng):
    g = _rings(rng, 0.0); H, W = dims(g)
    for _ in range(rng.randint(1, 4)):
        _wp(rng, g, (rng.randrange(H), rng.randrange(W)), 3, 12)
    return g
def tf_loops(g):
    out = copy(g)
    for comp in _pc(g):
        if all(_deg(g, r, c) == 2 for r, c in comp):
            for r, c in comp: out[r][c] = 2
    return out
rule("pipe_closed_loops_recoloured", "Every grey (5) pipe that forms a closed loop (each of its cells has exactly two grey neighbours) turns red (2); open pipes stay grey.", gi_loops, tf_loops)


def gi_tank(rng):
    g = _rings(rng, 0.4); H, W = dims(g)
    for _ in range(rng.randint(0, 3)):
        _wp(rng, g, (rng.randrange(H), rng.randrange(W)), 3, 10)
    return g
def tf_tank(g):
    H, W = dims(g); seen = set(); st = [(r, c) for r in range(H) for c in range(W) if (r in (0, H - 1) or c in (0, W - 1)) and g[r][c] == 0]
    seen.update(st)
    while st:
        y, x = st.pop()
        for n in _nbs(g, y, x):
            if g[n[0]][n[1]] == 0 and n not in seen: seen.add(n); st.append(n)
    out = copy(g)
    for r in range(H):
        for c in range(W):
            if g[r][c] == 0 and (r, c) not in seen: out[r][c] = 8
    return out
rule("pipe_sealed_tank_filled", "Fill with cyan (8) every black cell that cannot reach the grid border through orthogonally connected black cells (the inside of a sealed grey 5 pipe loop); loops with a gap hold nothing.", gi_tank, tf_tank)


# ================================================================== 27
def gi_valvepath(rng):
    g, recs = mk(rng, 6, 15, 1, [3], kmin=3)
    for rc in recs:
        p = rc['p']; L = len(p)
        if rc['caps'][0] is None: p = p[::-1]
        idx = rng.sample(range(2, L - 1), min(rng.randint(0, 2), L - 3)) if L > 3 else []
        for i in idx: g[p[i][0]][p[i][1]] = rng.choice((2, 4))
    return g
def tf_valvepath(g):
    out = copy(g); cols = (P, 2, 4, 3)
    for comp in _mcomps(g, cols):
        tap = [l for l in _leaves(g, comp, cols) if g[l[0]][l[1]] == 3]
        if len(tap) != 1: return None
        o = _order(g, comp, tap[0], cols)
        for r, c in o[1:]:
            if g[r][c] == 2: break
            out[r][c] = 8
    return out
rule("pipe_water_stops_at_closed_valve", "Water leaves a green (3) tap along its grey (5) pipe and turns the pipe cells and open yellow (4) valves cyan (8) until the first closed red (2) valve, which and everything beyond it stay unchanged; a pipe with no closed valve fills completely.", gi_valvepath, tf_valvepath)


# ================================================================== 28
def gi_valvetree(rng):
    return _tapped(rng, valves=True)
def tf_valvetree(g):
    return _bfs_fill(g, (P, 4), copy(g))
rule("pipe_water_through_open_valves_tree", "In a branching grey (5) network, cyan (8) water spreads from each green (3) tap through grey cells and open yellow (4) valves, turning them cyan, and is blocked by closed red (2) valves; blocked branches stay unchanged.", gi_valvetree, tf_valvetree)


# ================================================================== 29
def gi_capcol(rng):
    return mk(rng, 3, 12, 1, ALLC, kmin=3, lo_sz=8, hi_sz=20)[0]
def tf_capcol(g):
    cs = _pc(g); rows = []
    for i, comp in enumerate(cs):
        caps = [v for l in _leaves(g, comp) for _, v in _capof(g, l)]
        if len(caps) != 1: return None
        rows.append((-len(comp), i, caps[0]))
    rows.sort()
    return [[v] for _, _, v in rows]
rule("pipe_cap_colours_by_length_column", "Output one column listing the cap colour of each grey (5) pipe, longest pipe (most cells) at the top; equal lengths are ordered by the pipe's first cell in reading order.", gi_capcol, tf_capcol, small_ok=True)


# ================================================================== 30
def gi_capmix(rng):
    return mk(rng, 3, 14, 3, ALLC, kmin=3)[0]
def tf_shortcrop(g):
    cs = _pc(g)
    if len(cs) < 2: return None
    best = min(range(len(cs)), key=lambda i: (len(cs[i]), i)); comp = cs[best]
    cells_ = list(comp) + [cp for r, c in comp for cp, _ in _capof(g, (r, c))]
    r0, c0, r1, c1 = bbox(cells_)
    return crop(g, r0, c0, r1, c1)
rule("pipe_shortest_cropped", "Crop the bounding box (including its caps) of the grey (5) pipe with the fewest cells; on a tie the pipe whose first cell comes first in reading order is cropped.", gi_capmix, tf_shortcrop)


# ================================================================== 31
def gi_swap(rng):
    return mk(rng, 3, 12, 2, ALLC, kmin=3)[0]
def tf_swap(g):
    out = copy(g)
    for comp in _pc(g):
        lv = _leaves(g, comp); cp = [_capof(g, l) for l in lv]
        if len(lv) != 2 or any(len(x) != 1 for x in cp): return None
        (a, va), (b, vb) = cp[0][0], cp[1][0]
        out[a[0]][a[1]] = vb; out[b[0]][b[1]] = va
    return out
rule("pipe_end_caps_swap_colours", "Each grey (5) pipe has a coloured cap at each end; the two caps of every pipe exchange colours.", gi_swap, tf_swap)


# ================================================================== 32
def tf_takecap(g):
    out = copy(g)
    for comp in _pc(g):
        caps = [v for l in _leaves(g, comp) for _, v in _capof(g, l)]
        if len(caps) != 1: return None
        for r, c in comp: out[r][c] = caps[0]
    return out
rule("pipe_takes_cap_colour", "Each grey (5) pipe has one coloured cap at one end; every grey cell of that pipe is repainted in the cap's colour.", gi_far_end, tf_takecap)


# ================================================================== 33
def _span(rng, g, c0):
    h, w = dims(g); pts = []; r, c = 0, c0
    while True:
        for _ in range(rng.randint(1, 5)):
            pts.append((r, c))
            if r == h - 1: return pts
            r += 1
        s = rng.randint(-4, 4); s = max(-c, min(w - 1 - c, s)); step = 1 if s > 0 else -1
        for _ in range(abs(s)):
            pts.append((r, c)); c += step
            if r == h - 1: break
def _place(g, pts):
    placed = []
    for i, (r, c) in enumerate(pts):
        if not _fr(g, r, c) or _nocc(g, r, c) != (0 if i == 0 else 1):
            _undo(g, placed); return False
        g[r][c] = P; placed.append((r, c))
    return True
def gi_topbottom(rng):
    for _ in range(100):
        h, w = _sz(rng, 0.5, 8, 18); g = blank(h, w); span = 0
        for _a in range(12):
            if span >= rng.randint(1, 2): break
            pts = _span(rng, g, rng.randrange(w))
            pts = [(r, c) for i, (r, c) in enumerate(pts) if i == 0 or pts[i - 1] != (r, c)]
            if _place(g, pts): span += 1
        for _a in range(rng.randint(3, 10)):
            s = rng.choice(((0, rng.randrange(w)), (h - 1, rng.randrange(w)), (rng.randrange(h), rng.randrange(w))))
            _wp(rng, g, s, 3, max(4, h - 2))
        if span: return g
    raise RuntimeError
def tf_topbottom(g):
    H = len(g); out = copy(g)
    for comp in _pc(g):
        if any(r == 0 for r, _ in comp) and any(r == H - 1 for r, _ in comp):
            for r, c in comp: out[r][c] = 2
    return out
rule("pipe_top_to_bottom_recoloured", "A grey (5) pipe that has a cell in the top row and a cell in the bottom row turns red (2); all other pipes stay grey.", gi_topbottom, tf_topbottom)


# ================================================================== 34
def gi_bendcap(rng):
    return mk(rng, 3, 12, 1, [1], kmin=3, minbends=1, straight=0.6)[0]
def tf_bendcap(g):
    out = copy(g)
    for comp in _pc(g):
        caps = [cp for l in _leaves(g, comp) for cp, _ in _capof(g, l)]
        n = sum(1 for r, c in comp if _isbend(g, r, c))
        if len(caps) != 1 or not 1 <= n <= 9: return None
        out[caps[0][0]][caps[0][1]] = n
    return out
rule("pipe_cap_shows_bend_count", "The blue (1) cap at one end of each grey (5) pipe is replaced by the number of bend cells in that pipe (cells with one horizontal and one vertical grey neighbour).", gi_bendcap, tf_bendcap, digits=True)


# ================================================================== 35
def tf_corners(g):
    out = copy(g); H, W = dims(g)
    for r in range(H):
        for c in range(W):
            if g[r][c] != P or _deg(g, r, c) != 2: continue
            u = r > 0 and g[r - 1][c] == P; d = r < H - 1 and g[r + 1][c] == P
            l = c > 0 and g[r][c - 1] == P; rt = c < W - 1 and g[r][c + 1] == P
            if rt and d: out[r][c] = 2
            elif l and u: out[r][c] = 3
    return out
rule("pipe_corner_type_marks", "On grey (5) pipes, a bend whose two neighbours are to its right and below turns red (2), a bend whose two neighbours are to its left and above turns green (3); the other two bend types stay grey.", gi_bends, tf_corners)


# ================================================================== 36
def gi_short(rng):
    return mk(rng, 2, 11, 0, kmin=4)[0]
def tf_short(g):
    out = copy(g)
    for comp in _pc(g):
        if len(comp) <= 5:
            for r, c in comp: out[r][c] = 0
    return out
rule("pipe_short_pipes_erased", "Erase every grey (5) pipe with 5 cells or fewer to black; longer pipes stay.", gi_short, tf_short)


# ================================================================== 37
def gi_leak(rng):
    return mk(rng, 3, 10, 1, [3], kmin=3)[0]
def tf_leak(g):
    out = copy(g); H, W = dims(g)
    for comp in _pc(g):
        op = [l for l in _leaves(g, comp) if not _capof(g, l)]
        if len(op) != 1: return None
        o = _order(g, comp, op[0]); (r, c) = o[0]
        if len(o) < 2: return None
        dr, dc = r - o[1][0], c - o[1][1]; y, x = r + dr, c + dc
        while 0 <= y < H and 0 <= x < W and g[y][x] == 0:
            out[y][x] = 8; y += dr; x += dc
    return out
rule("pipe_open_end_leaks_straight", "Each grey (5) pipe has a green (3) cap at one end; from the open end a cyan (8) leak runs straight on in the direction of the pipe's last step until it meets a non-black cell or the grid edge.", gi_leak, tf_leak)


# ================================================================== 38
def gi_dist(rng):
    return mk(rng, 3, 13, 1, [1], kmin=3)[0]
def tf_dist(g):
    out = copy(g)
    for comp in _pc(g):
        cl = [l for l in _leaves(g, comp) if _capof(g, l)]
        if len(cl) != 1: return None
        for i, (r, c) in enumerate(_order(g, comp, cl[0])): out[r][c] = min(i + 1, 9)
    return out
rule("pipe_cells_numbered_from_cap", "Starting from the blue (1) cap, number the cells of each grey (5) pipe 1, 2, 3, ... along the pipe, writing 9 for every cell from the ninth on.", gi_dist, tf_dist, digits=True)


# ================================================================== 39
def gi_sides(rng):
    return mk(rng, 5, 22, 0, kmin=4, wall=[rng.choice('lr') for _ in range(rng.randint(2, 4))], straight=0.75)[0]
def tf_sides(g):
    W = len(g[0]); out = copy(g)
    for comp in _pc(g):
        l = any(c == 0 for _, c in comp); r_ = any(c == W - 1 for _, c in comp)
        col = 6 if (l and r_) else 3 if l else 4 if r_ else None
        if col:
            for y, x in comp: out[y][x] = col
    return out
rule("pipe_wall_touch_colours", "A grey (5) pipe touching the leftmost column turns green (3), one touching the rightmost column turns yellow (4), and one touching both turns magenta (6); pipes touching neither wall stay grey.", gi_sides, tf_sides)


# ================================================================== 40
def gi_hist(rng):
    cc = rng.sample([1, 2, 3, 4, 6, 7, 8, 9], rng.randint(2, 4))
    return mk(rng, 3, 7, 1, cc, kmin=5, lo_sz=9, hi_sz=20)[0]
def tf_hist(g):
    cnt = {}
    for comp in _pc(g):
        caps = [v for l in _leaves(g, comp) for _, v in _capof(g, l)]
        if len(caps) != 1: return None
        cnt[caps[0]] = cnt.get(caps[0], 0) + 1
    W = max(cnt.values())
    if len(cnt) < 2 or W > 30: return None
    return [[v] * n + [0] * (W - n) for v, n in sorted(cnt.items())]
rule("pipe_cap_colour_histogram", "Count the grey (5) pipes by the colour of their single cap and output one row per cap colour, rows ordered by increasing colour value, each row that many cells of that colour left-aligned on black, padded to the largest count.", gi_hist, tf_hist, digits=True, small_ok=True)
