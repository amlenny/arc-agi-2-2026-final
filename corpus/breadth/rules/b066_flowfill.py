# b066_flowfill.py -- FLOW AND FILL: a source (coloured cell, nozzle, tap) emits along a thread, pipe, corridor or
# straight line; what it reaches is filled, lit or recoloured, what it does not reach is left or erased. Containers,
# beads, dams, valves, leaks, capacity, overflow, gravity, mirrors, splitters, races between sources, distance bands.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

W = 5
N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
N8 = N4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))
N3 = ((1, 0), (0, -1), (0, 1))


def D(rng, lo=8, hi=30):
    """A side length: about 45% of the time in 21..hi."""
    if hi >= 21 and rng.random() < 0.45:
        return rng.randint(21, hi)
    return rng.randint(lo, min(hi, 20))


def src(rng, ex):
    return rng.choice([c for c in range(1, 10) if c not in ex])


def mk(gen, tf, cond=None, tries=90):
    def make(rng):
        last = None
        for _ in range(tries):
            g = gen(rng)
            if g is None: continue
            last = g
            o = tf(g)
            if o is None or o == g: continue
            if cond is None or cond(g, o): return g
        return last if last is not None else blank(8, 8)
    return make


def bfs(g, starts, ok, nb=N4, maxd=None):
    H, Wd = dims(g); d = {s: 0 for s in starts}; q = list(starts); i = 0
    while i < len(q):
        r, c = q[i]; i += 1
        if maxd is not None and d[(r, c)] >= maxd: continue
        for dr, dc in nb:
            y, x = r + dr, c + dc
            if 0 <= y < H and 0 <= x < Wd and (y, x) not in d and ok(g[y][x]):
                d[(y, x)] = d[(r, c)] + 1; q.append((y, x))
    return d


def scatter(rng, g, dens):
    H, Wd = dims(g); sprinkle(rng, g, int(H * Wd * dens), W)
    for _ in range(rng.randint(1, 2 + H * Wd // 150)):
        r, c = rng.randrange(H), rng.randrange(Wd); n = rng.randint(2, max(2, max(H, Wd) // 3))
        for i in range(n):
            y, x = (r, c + i) if rng.random() < 2 else (r + i, c)
            if y < H and x < Wd and g[y][x] == 0: g[y][x] = W
    return g


def scatter2(rng, g, dens):
    """scatter plus random vertical/horizontal segments"""
    H, Wd = dims(g); sprinkle(rng, g, int(H * Wd * dens), W)
    for _ in range(rng.randint(1, 2 + H * Wd // 120)):
        r, c = rng.randrange(H), rng.randrange(Wd); n = rng.randint(2, max(2, max(H, Wd) // 3)); hz = rng.random() < .5
        for i in range(n):
            y, x = (r, c + i) if hz else (r + i, c)
            if y < H and x < Wd and g[y][x] == 0: g[y][x] = W
    return g


def free_cell(rng, g):
    f = cells(g, lambda v: v == 0)
    return rng.choice(f) if f else None


def put(rng, g, col):
    p = free_cell(rng, g)
    if p: g[p[0]][p[1]] = col
    return p


def srcs(g, ex=(0, W)):
    return cells(g, lambda v: v not in ex)


# =============================================================== band scene: sources on the left, threads, 5x5 frames
def band_gen(modes, same=False, kmin=2):
    def gen(rng):
        k = rng.randint(kmin, 5); H = k * 6 - 1 + rng.randint(0, 3); Wd = D(rng, 16, 30)
        g = blank(H, Wd); s0 = src(rng, (1, 2, 5))
        for b in range(k):
            r0 = b * 6; r = r0 + 2; fc = rng.randint(9, Wd - 5)
            rect(g, r0, fc, r0 + 4, fc + 4, 1, fill=False)
            g[r][0] = s0 if same else src(rng, (1, 2, 5)); mode = rng.choice(modes)
            end = fc - 1
            if mode == 'gap': end = rng.randint(1, fc - 2)
            for c in range(1, end + 1): g[r][c] = W
            if mode == 'dam': g[r][rng.randint(2, fc - 2)] = 2
        return g
    return gen


def run(g, r):
    Wd = len(g[0]); cl = []; c = 1
    while c < Wd and g[r][c] == W: cl.append((r, c)); c += 1
    return cl, c, (g[r][c] if c < Wd else None)


def fill_in(out, r, c, s):
    for y in range(r - 1, r + 2):
        for x in range(c + 1, c + 4): out[y][x] = s


def tf_gap(g):
    out = copy(g)
    for (r, _) in srcs(g, (0, W, 1, 2)):
        pass
    for r in range(len(g)):
        if g[r][0] in (0,): continue
        cl, c, e = run(g, r)
        if e == 1: fill_in(out, r, c, g[r][0])
    return out
rule("thread_gap_blocks_container_fill", "Each source cell at the left edge fills the 3x3 interior of its colour-1 frame with its own colour if an unbroken run of grey (5) cells links the source to the frame's left wall, and leaves the frame empty if there is any empty gap.",
     mk(band_gen(('ok', 'gap')), tf_gap), tf_gap)


def tf_dam(g):
    out = copy(g)
    for r in range(len(g)):
        s = g[r][0]
        if s == 0: continue
        cl, c, e = run(g, r)
        for (y, x) in cl: out[y][x] = s
        if e == 1: fill_in(out, r, c, s)
    return out
rule("dam_stops_thread_flow", "Each source cell at the left edge floods its grey (5) thread cell by cell in its own colour and stops at an empty gap or a colour-2 dam (the dam stays, nothing beyond it is coloured); the frame's 3x3 interior fills only if the thread reaches the frame's left wall.",
     mk(band_gen(('ok', 'gap', 'dam')), tf_dam), tf_dam)


def tf_cap(g):
    out = copy(g); n = 0
    for r in range(len(g)):
        if g[r][0] == 0: continue
        cl, c, e = run(g, r)
        if e == 1 and n < 2:
            fill_in(out, r, c, g[r][0]); n += 1
    return out
rule("supply_fills_first_two_connected", "Counting frames from the top of the grid downward, only the first two frames that are linked to their source by an unbroken grey (5) thread get their 3x3 interior filled with the source colour; any further connected frames and all unconnected frames stay empty.",
     mk(band_gen(('ok', 'ok', 'gap'), kmin=3), tf_cap, lambda g, o: sum(1 for r in range(len(g)) if g[r][0] and run(g, r)[2] == 1) >= 3), tf_cap)


def tf_bar(g):
    rows = [r for r in range(len(g)) if g[r][0]]
    if not rows: return None
    n = sum(1 for r in rows if run(g, r)[2] == 1)
    if n == 0: return None
    return [[g[rows[0]][0]] * n + [0] * (len(rows) - n)]
rule("connected_container_count_bar", "The output is one row as wide as the number of source cells at the left edge, holding that count's worth of source-colour cells from the left, one for each frame that an unbroken grey (5) thread links to its source, and empty cells for the rest.",
     mk(band_gen(('ok', 'gap'), same=True, kmin=3), tf_bar), tf_bar)


# =============================================================== tank scene: gauge bar beside a 5x7 tank
def tanks_gen(leak=False):
    def gen(rng):
        m = rng.randint(2, 4); rows = rng.randint(1, 3); H = 9 * rows + rng.randint(0, 3); Wd = 7 * m + rng.randint(0, 2)
        g = blank(H, Wd)
        for i in range(rows):
            for j in range(m):
                r0 = 9 * i + rng.randint(0, 1) if rows * 9 + 2 <= H else 9 * i; x = 7 * j + 1; r0 = min(r0, H - 7)
                rect(g, r0, x, r0 + 6, x + 4, 1, fill=False)
                s = src(rng, (1, 2, 5))
                if leak:
                    rect(g, r0 + 1, x + 1, r0 + 5, x + 3, s)
                    side = rng.choice((x, x + 4)); li = rng.randint(1, 4); g[r0 + 1 + li][side] = 2
                else:
                    for k in range(rng.randint(1, 5)): g[r0 + 5 - k][x - 1] = s
        return g
    return gen


def frames(g, h, w, col=1):
    return [bbox(cm) for cm in components(g, col, conn8=False) if bbox(cm)[2] - bbox(cm)[0] + 1 == h and bbox(cm)[3] - bbox(cm)[1] + 1 == w]


def tf_level(g):
    out = copy(g); fr = frames(g, 7, 5)
    if not fr: return None
    for r0, c0, r1, c1 in fr:
        n = sum(1 for r in range(r0 + 1, r1) if g[r][c0 - 1] != 0)
        if n == 0: return None
        s = g[r1 - 1][c0 - 1]
        for r in range(r1 - n, r1):
            for c in range(c0 + 1, c1): out[r][c] = s
    return out
rule("gauge_height_sets_fill_level", "Each 7-tall, 5-wide colour-1 tank has a vertical gauge bar in the column left of its left wall, standing on the tank's floor row; the tank's inside is filled with the gauge colour in as many bottom rows as the gauge has cells.",
     mk(tanks_gen(False), tf_level), tf_level)


def tf_leaklvl(g):
    out = copy(g); fr = frames(g, 7, 5)
    if not fr: return None
    for r0, c0, r1, c1 in fr:
        lk = [(r, c) for r in range(r0 + 1, r1) for c in (c0, c1) if g[r][c] == 2]
        if len(lk) != 1: return None
        lr, lc = lk[0]; s = g[r0 + 1][c0 + 1]
        for r in range(r0 + 1, lr):
            for c in range(c0 + 1, c1): out[r][c] = 0
        out[lr][lc + (1 if lc == c1 else -1)] = s
    return out
rule("leak_drains_to_leak_height", "Each full tank (a 7x5 colour-1 frame filled with one colour) has one colour-2 cell in a side wall; the water above the leak's row drains away (rows above the leak become empty, the leak's row and below stay full) and the cell just outside the leak is coloured with the water colour.",
     mk(tanks_gen(True), tf_leaklvl), tf_leaklvl)


# =============================================================== cascade overflow
def cascade_gen(rng):
    k = rng.randint(2, 5); Wd = 6 * k - 1 + rng.randint(0, 2); H = D(rng, 8, 30); g = blank(H, Wd); s = src(rng, (1,))
    for j in range(k): rect(g, 2, 6 * j, 5, 6 * j + 4, 1, fill=False)
    for c in range(rng.randint(3, min(Wd, 6 * k - 1))): g[0][c] = s
    return g


def tf_cascade(g):
    s = g[0][0]; n = sum(1 for v in g[0] if v == s)
    fr = sorted(frames(g, 4, 5), key=lambda b: b[1]); out = copy(g); order = []
    for r0, c0, r1, c1 in fr:
        order += [(r, c) for r in (r1 - 1, r0 + 1) for c in range(c0 + 1, c1)]
    if n > len(order) or s == 0: return None
    for r, c in order[:n]: out[r][c] = s
    return out
rule("overflow_fills_next_container", "The source bar of n cells along the top row is poured into the row of colour-1 frames from left to right; each frame holds 6 cells and takes them bottom row first, left to right, then the top row left to right, and once a frame is full the pouring continues into the next frame to its right until n cells are placed (the bar stays).",
     mk(cascade_gen, tf_cascade), tf_cascade)


# =============================================================== containers with a tap and maybe a leak
def tap_gen(rng):
    m = rng.randint(2, 4); H = D(rng, 11, 30); Wd = 7 * m + rng.randint(0, 2); g = blank(H, Wd)
    for j in range(m):
        r0 = rng.randint(1, H - 6); x = 7 * j + 1
        rect(g, r0, x, r0 + 4, x + 4, 1, fill=False); g[r0 - 1][x + 2] = src(rng, (1, 2, 5))
        if rng.random() < .5: g[r0 + 4][x + rng.randint(1, 3)] = 2
    return g


def tf_tap(g):
    out = copy(g); H = len(g); fr = frames(g, 5, 5)
    if len(fr) < 2: return None
    for r0, c0, r1, c1 in fr:
        s = g[r0 - 1][c0 + 2]; lk = [c for c in range(c0 + 1, c1) if g[r1][c] == 2]
        if s == 0: return None
        if not lk:
            for r in range(r0 + 1, r1):
                for c in range(c0 + 1, c1): out[r][c] = s
        else:
            r = r1 + 1
            while r < H and g[r][lk[0]] == 0: out[r][lk[0]] = s; r += 1
    return out
rule("leaky_container_drips_instead", "Each 5x5 colour-1 container has a tap cell above the middle of its top wall: if its bottom wall has no colour-2 leak cell the inside fills with the tap colour; if it has a leak, the inside stays empty and the tap colour instead drips straight down from the leak through empty cells to the bottom edge or the first non-empty cell.",
     mk(tap_gen, tf_tap), tf_tap)


# =============================================================== beads on a thread
def bead_gen(rng):
    nr = rng.randint(2, 8); H = 2 * nr - 1 + rng.randint(0, 3); Wd = D(rng, 12, 30); g = blank(H, Wd)
    for i in range(nr):
        r = 2 * i; L = rng.randint(Wd - 8, Wd - 1); g[r][0] = src(rng, (5, 8))
        for c in range(1, L + 1): g[r][c] = 8 if rng.random() < .35 else W
        if rng.random() < .55: g[r][rng.randint(3, max(3, L - 2))] = 0
    return g


def tf_beads(mode):
    def tf(g):
        out = copy(g)
        for r in range(len(g)):
            s = g[r][0]
            if s == 0: continue
            c = 1; n = 0
            while c < len(g[0]) and g[r][c] in (W, 8):
                if g[r][c] == 8:
                    n += 1
                    if mode == 'all' or (mode == 'k3' and n <= 3) or (mode == 'odd' and n % 2 == 1): out[r][c] = s
                c += 1
        return out
    return tf
rule("beads_lit_until_thread_gap", "Each source cell at the left edge colours every colour-8 bead on its row in its own colour, travelling right along the thread of grey (5) and bead cells and stopping at the first empty cell; beads after that gap stay colour 8.",
     mk(bead_gen, tf_beads('all')), tf_beads('all'))
rule("beads_first_three_only", "Each source cell at the left edge colours only the first three colour-8 beads met travelling right along its row of grey (5) and bead cells, and also stops at the first empty cell; later beads stay colour 8.",
     mk(bead_gen, tf_beads('k3')), tf_beads('k3'))
rule("beads_alternate_from_source", "Along each row, travelling right from the source cell through grey (5) and colour-8 bead cells until the first empty cell, the 1st, 3rd, 5th... bead are coloured with the source colour and the 2nd, 4th... beads stay colour 8.",
     mk(bead_gen, tf_beads('odd')), tf_beads('odd'))


# =============================================================== pipe networks
def walk(rng, H, Wd, start, n, forbid, taken):
    cur = start; got = [start]; taken.add(start)
    for _ in range(n):
        opts = [(cur[0] + dr, cur[1] + dc) for dr, dc in N4]
        opts = [p for p in opts if 0 <= p[0] < H and 0 <= p[1] < Wd and p not in forbid and p not in taken]
        if not opts: break
        cur = rng.choice(opts); taken.add(cur); got.append(cur)
    return got


def pipe_gen(valves=False):
    def gen(rng):
        H, Wd = D(rng, 7, 30), D(rng, 7, 30); g = blank(H, Wd)
        sp = (rng.randrange(H), rng.randrange(Wd)); taken = {sp}
        s = (rng.choice([r for r, _ in [(sp[0], 0)]]), 0)
        nb = [(sp[0] + dr, sp[1] + dc) for dr, dc in N4 if 0 <= sp[0] + dr < H and 0 <= sp[1] + dc < Wd]
        main = walk(rng, H, Wd, rng.choice(nb), rng.randint(10, max(12, H * Wd // 8)), set(), taken)
        for _ in range(rng.randint(1, 3)):
            main += walk(rng, H, Wd, rng.choice(main), rng.randint(4, 18), set(), taken)
        halo = set(taken) | {(r + dr, c + dc) for r, c in taken for dr, dc in N4}
        sep = []
        for _ in range(rng.randint(1, 3)):
            st = (rng.randrange(H), rng.randrange(Wd))
            if st in halo or st in sep: continue
            sep += walk(rng, H, Wd, st, rng.randint(4, 16), halo, set(sep))
        for r, c in main + sep: g[r][c] = W
        if valves:
            cand = [p for p in main if p not in nb]
            for p in rng.sample(cand, min(len(cand), rng.randint(1, 3))): g[p[0]][p[1]] = 2
        g[sp[0]][sp[1]] = src(rng, (2, 4, 5))
        return g
    return gen


def pipe_reach(g):
    sc = srcs(g, (0, W, 2))
    if len(sc) != 1: return None, None
    return sc[0], bfs(g, sc, lambda v: v == W)


def tf_pipe(mode):
    def tf(g):
        sp, d = pipe_reach(g)
        if sp is None: return None
        s = g[sp[0]][sp[1]]; out = copy(g); H = len(g)
        for p in d:
            if p != sp: out[p[0]][p[1]] = s
        if mode == 'drip':
            for (r, c) in d:
                if (r, c) == sp: continue
                if sum(1 for dr, dc in N4 if (r + dr, c + dc) in d) == 1 and r + 1 < H and g[r + 1][c] == 0:
                    out[r + 1][c] = 4
        return out
    return tf
rule("pipe_network_flooded_from_source", "The grey (5) pipe cells connected (edge-adjacent) to the single coloured source cell all take the source colour; pipe pieces that do not connect to the source stay grey.",
     mk(pipe_gen(), tf_pipe('flood')), tf_pipe('flood'))
rule("closed_valve_blocks_pipe_flow", "The grey (5) pipe cells connected to the source cell take the source colour, but colour-2 valve cells block the flow (they stay colour 2) and pipe beyond a valve stays grey.",
     mk(pipe_gen(True), tf_pipe('flood')), tf_pipe('flood'))
rule("pipe_open_ends_drip_four", "The grey (5) pipe connected to the source cell takes the source colour, and every flooded pipe cell that has exactly one edge-adjacent flooded neighbour (a dead end; the source cell counts as flooded) drips: the empty cell directly below it becomes colour 4.",
     mk(pipe_gen(), tf_pipe('drip')), tf_pipe('drip'))


# =============================================================== open corridor flooding
def maze_gen(dens=(.16, .3), nsrc=1, ex=(5,), sc=None):
    def gen(rng):
        H, Wd = D(rng, 6, 30), D(rng, 6, 30); g = blank(H, Wd); scatter2(rng, g, rng.uniform(*dens))
        cs = rng.sample([c for c in range(1, 10) if c not in ex], nsrc) if sc is None else rng.sample(sc, nsrc)
        for c in cs:
            if put(rng, g, c) is None: return None
        return g
    return gen


def flood_tf(nb, fn=None):
    def tf(g):
        sc = srcs(g)
        if len(sc) != 1: return None
        s = g[sc[0][0]][sc[0][1]]; d = bfs(g, sc, lambda v: v == 0, nb)
        out = copy(g)
        for p, dist in d.items():
            if p != sc[0]: out[p[0]][p[1]] = fn(s, dist) if fn else s
        return out
    return tf


def unreached(g, o): return sum(1 for r in o for v in r if v == 0) >= 3 and sum(1 for r, row in enumerate(o) for c, v in enumerate(row) if v != g[r][c]) >= 4
tf4 = flood_tf(N4); tf8 = flood_tf(N8)
rule("corridor_flood_edge_adjacent", "The single coloured source cell floods every empty cell connected to it through edge-adjacent empty cells, in its own colour; grey (5) walls are never entered and cells walled off from the source stay empty.",
     mk(maze_gen(), tf4, unreached), tf4)
rule("corridor_flood_squeezes_diagonals", "The single coloured source cell floods every empty cell reachable by king moves (including diagonal steps between two touching walls) through empty cells, in its own colour; grey (5) cells are never entered and unreachable cells stay empty.",
     mk(maze_gen((.25, .38)), tf8, lambda g, o: unreached(g, o) and o != tf4(g)), tf8)


def tf_steps(g):
    sc = srcs(g)
    if len(sc) != 1: return None
    s = g[sc[0][0]][sc[0][1]]; d = bfs(g, sc, lambda v: v == 0, N4, maxd=s); out = copy(g)
    for p in d:
        if p != sc[0]: out[p[0]][p[1]] = s
    return out
rule("flood_range_equals_source_digit", "The single source cell with value d (1-9, never 5) floods outward through edge-adjacent empty cells for at most d steps (cells at path distance 1..d) painting them with value d; grey (5) walls stop it and farther cells stay empty.",
     mk(maze_gen((.08, .2)), tf_steps, lambda g, o: o != flood_tf(N4)(g)), tf_steps, digits=True)


def band_fn(s, d): return 2 if d <= 3 else 3 if d <= 6 else 1
tf_dist = flood_tf(N4, band_fn)
rule("flood_distance_bands_two_three_one", "The source cell floods the empty cells connected to it through edge-adjacent empty cells (walls are grey 5): cells at path distance 1-3 from the source become colour 2, 4-6 become colour 3, and 7 or more become colour 1; the source cell and unreachable cells stay as they are.",
     mk(maze_gen((.1, .25), ex=(1, 2, 3, 5)), tf_dist, lambda g, o: any(v == 1 for r in o for v in r) and unreached(g, o)), tf_dist)


def tf_wet(g):
    sc = srcs(g)
    if len(sc) != 1: return None
    s = g[sc[0][0]][sc[0][1]]; d = bfs(g, sc, lambda v: v == 0); out = copy(g)
    for r, row in enumerate(g):
        for c, v in enumerate(row):
            if v == 0: out[r][c] = s if (r, c) in d else 4
    return out
rule("flood_wet_and_dry_pockets", "Empty cells connected to the source cell through edge-adjacent empty cells take the source colour, and every other empty cell (walled-off by the grey 5 cells) becomes colour 4.",
     mk(maze_gen(ex=(4, 5)), tf_wet, lambda g, o: any(v == 4 for r in o for v in r)), tf_wet)


# =============================================================== gravity-fed flow
def tf_grav(g):
    sc = srcs(g)
    if len(sc) != 1: return None
    s = g[sc[0][0]][sc[0][1]]; d = bfs(g, sc, lambda v: v == 0, N3); out = copy(g)
    for p in d:
        if p != sc[0]: out[p[0]][p[1]] = s
    return out


def grav_gen(rng):
    H, Wd = D(rng, 7, 30), D(rng, 7, 30); g = blank(H, Wd); scatter2(rng, g, rng.uniform(.12, .26))
    g[0][rng.randrange(Wd)] = src(rng, (5,)); return g
rule("gravity_fed_down_and_sideways", "The source cell in the top row floods empty cells using only moves down, left and right (never up) through empty cells, painting them in its colour; grey (5) cells are never entered.",
     mk(grav_gen, tf_grav, lambda g, o: unreached(g, o) and tf4(g) != o), tf_grav)


def plat_gen(rng):
    H, Wd = D(rng, 10, 30), D(rng, 8, 30); g = blank(H, Wd)
    for _ in range(max(2, H // 3)):
        r = rng.randint(2, H - 2); l = rng.randint(3, max(3, Wd // 2)); c = rng.randint(0, Wd - l)
        for i in range(l): g[r][c + i] = W
    if g[0][0:] != [0] * Wd: return None
    g[0][rng.randrange(Wd)] = src(rng, (5,)); return g


def tf_fall(g):
    H, Wd = dims(g); sc = srcs(g)
    if len(sc) != 1: return None
    s = g[sc[0][0]][sc[0][1]]; out = copy(g); painted = set(); stack = [sc[0]]; seen = set()
    while stack:
        r, c = stack.pop()
        if (r, c) in seen: continue
        seen.add((r, c))
        while r + 1 < H and g[r + 1][c] == 0 and (r + 1, c) not in painted:
            r += 1; painted.add((r, c))
        if r + 1 < H and g[r + 1][c] == W:
            for dx in (-1, 1):
                x = c
                while 0 <= x + dx < Wd and g[r][x + dx] == 0:
                    x += dx; painted.add((r, x))
                    if r + 1 < H and g[r + 1][x] == 0: stack.append((r, x)); break
    for r, c in painted: out[r][c] = s
    return out
rule("waterfall_splits_at_platforms", "Water from the source cell in the top row falls straight down through empty cells; when it lands on a grey (5) platform it spreads left and right along the platform's top until the platform ends (or an obstacle blocks), then falls again from each end; all water cells take the source colour and the stream ends at the bottom edge.",
     mk(plat_gen, tf_fall, lambda g, o: sum(1 for r in range(len(g)) for c in range(len(g[0])) if o[r][c] != g[r][c]) >= 12), tf_fall)


def rise_gen(rng):
    H, Wd = D(rng, 8, 30), D(rng, 8, 30); g = blank(H, Wd); scatter2(rng, g, rng.uniform(.1, .22))
    m = rng.randint(H // 3, H - 3); g[m][0] = 4
    for c in range(Wd):
        if g[H - 1][c] == W and rng.random() < .8: g[H - 1][c] = 0
    g[H - 1][rng.randrange(1, Wd)] = src(rng, (4, 5)); return g


def tf_rise(g):
    H = len(g); mk_ = cells(g, lambda v: v == 4)
    if len(mk_) != 1: return None
    m = mk_[0][0]; sc = [p for p in srcs(g, (0, W, 4))]
    if len(sc) != 1: return None
    s = g[sc[0][0]][sc[0][1]]; g2 = [[(W if r < m else v) for v in row] for r, row in enumerate(g)]
    d = bfs(g2, sc, lambda v: v == 0); out = copy(g)
    for p in d:
        if p != sc[0]: out[p[0]][p[1]] = s
    return out
rule("rising_water_to_marker_row", "The source cell sits on the bottom row and a colour-4 marker sits in the left column; the water colour fills all empty cells connected to the source through edge-adjacent empty cells but only in rows at or below the marker's row, never entering grey (5) cells.",
     mk(rise_gen, tf_rise, lambda g, o: sum(1 for r in range(len(g)) for c in range(len(g[0])) if o[r][c] != g[r][c]) >= 5), tf_rise)


# =============================================================== streams from nozzles
def shapes_in(g, k, rng, col=8, size=(2, 5)):
    shapes = [random_shape(rng, rng.randint(*size)) for _ in range(k)]
    return place_shapes(rng, g, shapes, [col] * k) is not None


def stream_scene(rng, wall=True, rot=False):
    H, Wd = D(rng, 8, 30), D(rng, 8, 30); g = blank(H, Wd)
    if not shapes_in(g, rng.randint(2, max(3, H * Wd // 45)), rng): return None
    r = rng.randint(1, H - 2)
    if g[r][0] or g[r][1]: return None
    g[r][0] = src(rng, (5, 8))
    if wall:
        wc = rng.randint(Wd // 2, Wd - 2)
        if g[r][wc] != 0: return None
        for rr in range(r - rng.randint(0, 2), r + rng.randint(0, 2) + 1):
            if 0 <= rr < H and g[rr][wc] == 0: g[rr][wc] = W
    if rot:
        for _ in range(rng.randrange(4)): g = rot90(g)
    return g


def ray(g, r, c, dr, dc, stop=(W,)):
    H, Wd = dims(g); o = []; r += dr; c += dc
    while 0 <= r < H and 0 <= c < Wd and g[r][c] not in stop:
        o.append((r, c)); r += dr; c += dc
    return o


def nozzle(g):
    H, Wd = dims(g); n = srcs(g, (0, W, 8))
    if len(n) != 1: return None
    r, c = n[0]
    d = (0, 1) if c == 0 else (0, -1) if c == Wd - 1 else (1, 0) if r == 0 else (-1, 0) if r == H - 1 else None
    return (r, c, d) if d else None


def split_shapes(g, path):
    ps = set(path); cm = components(g, 8, conn8=True)
    return [c for c in cm if any(p in ps for p in c)], [c for c in cm if not any(p in ps for p in c)]


def paint(out, path, s, g):
    for r, c in path:
        if g[r][c] == 0: out[r][c] = s


def tf_stream_erase(g):
    n = nozzle(g)
    if not n: return None
    r, c, d = n; s = g[r][c]; p = ray(g, r, c, *d); lit, dark = split_shapes(g, p); out = copy(g)
    for cm in dark:
        for y, x in cm: out[y][x] = 0
    for cm in lit:
        for y, x in cm: out[y][x] = s
    paint(out, p, s, g); return out
okls = lambda g, o: any(v == 8 for r in g for v in r) and sum(1 for r, row in enumerate(g) for c, v in enumerate(row) if v == 8 and o[r][c] == 0) >= 2 and sum(1 for r, row in enumerate(g) for c, v in enumerate(row) if v == 8 and o[r][c] not in (0, 8)) >= 2
rule("stream_lights_hit_erases_missed", "The nozzle cell at the left edge fires a stream right along its row until the grid edge or the first grey (5) wall cell, passing through shapes: every colour-8 shape the stream touches turns the nozzle colour, the empty cells of the stream are painted in the nozzle colour, and every colour-8 shape not touched is erased.",
     mk(stream_scene, tf_stream_erase, okls), tf_stream_erase)


def tf_first(g):
    n = nozzle(g)
    if not n: return None
    r, c, d = n; s = g[r][c]; p = ray(g, r, c, W, 8) if False else ray(g, r, c, *d, stop=(W, 8)); out = copy(g)
    last = p[-1] if p else (r, c); y, x = last[0] + d[0], last[1] + d[1]
    if not (0 <= y < len(g) and 0 <= x < len(g[0]) and g[y][x] == 8): return None
    for cm in components(g, 8, conn8=True):
        if (y, x) in cm:
            for a, b in cm: out[a][b] = s
    paint(out, p, s, g); return out
rule("stream_stops_at_first_shape", "The nozzle cell at the left edge fires a stream right along its row through empty cells and stops at the first colour-8 shape it meets (grey 5 walls also stop it, but only inputs where a shape comes first appear): the stream cells and that whole first shape turn the nozzle colour, and all other shapes are unchanged.",
     mk(stream_scene, tf_first), tf_first)


def tf_four(g):
    n = nozzle(g)
    if not n: return None
    r, c, d = n; s = g[r][c]; p = ray(g, r, c, *d); lit, dark = split_shapes(g, p); out = copy(g)
    for cm in lit:
        for y, x in cm: out[y][x] = s
    paint(out, p, s, g); return out if lit else None
rule("nozzle_on_any_edge_lights_shapes", "The single nozzle cell on one edge of the grid (not a corner) fires a stream straight inward, perpendicular to that edge, until the opposite edge or a grey (5) wall cell, passing through shapes: empty cells on the way and every colour-8 shape touched by the stream take the nozzle colour; untouched shapes are unchanged.",
     mk(lambda rng: stream_scene(rng, True, True), tf_four, lambda g, o: sum(1 for row in g for v in row if v == 8) > sum(1 for row in o for v in row if v == 8) and any(v == 8 for row in o for v in row)), tf_four)


def cross_gen(rng):
    H, Wd = D(rng, 8, 30), D(rng, 8, 30); g = blank(H, Wd)
    if not shapes_in(g, rng.randint(3, max(4, H * Wd // 40)), rng): return None
    sprinkle(rng, g, rng.randint(1, 4), W)
    if put(rng, g, src(rng, (5, 8))) is None: return None
    return g


def tf_cross(g):
    sc = srcs(g, (0, W, 8))
    if len(sc) != 1: return None
    r, c = sc[0]; s = g[r][c]; p = []
    for d in N4: p += ray(g, r, c, *d)
    lit, dark = split_shapes(g, p); out = copy(g)
    for cm in dark:
        for y, x in cm: out[y][x] = 0
    for cm in lit:
        for y, x in cm: out[y][x] = s
    paint(out, p, s, g); return out
rule("four_way_emitter_lights_or_erases", "The source cell fires four straight streams (up, down, left, right) through empty cells and shapes, each ending at the grid edge or a grey (5) cell: empty stream cells and every colour-8 shape touched by any stream take the source colour, and every colour-8 shape touched by none is erased.",
     mk(cross_gen, tf_cross, okls), tf_cross)


def mirror_step(d, m): return (-d[1], -d[0]) if m == 2 else (d[1], d[0])


def trace(g, r, c, d, split=False):
    H, Wd = dims(g); path = []; hits = 0; q = [(r, c, d)]; seen = set()
    while q:
        r, c, d = q.pop()
        while True:
            r += d[0]; c += d[1]
            if not (0 <= r < H and 0 <= c < Wd) or (r, c, d) in seen: break
            seen.add((r, c, d)); v = g[r][c]
            if not split and v in (2, 4): d = mirror_step(d, v); hits += 1; continue
            if split and v == 3:
                hits += 1; q += [(r, c, (d[1], d[0])), (r, c, (-d[1], -d[0]))]; break
            path.append((r, c))
    return path, hits


def mirrors_gen(shapes):
    def gen(rng):
        H, Wd = D(rng, 8, 30), D(rng, 8, 30); g = blank(H, Wd)
        if shapes and not shapes_in(g, rng.randint(2, max(3, H * Wd // 60)), rng, size=(3, 4)): return None
        r = rng.randint(1, H - 2)
        if g[r][0]: return None
        g[r][0] = src(rng, (2, 4, 5, 8))
        for i in range(rng.randint(3, max(4, H * Wd // 25))):
            p = free_cell(rng, g)
            if p and p[1] > 0 and (i or True): g[p[0]][p[1]] = rng.choice((2, 4))
        if rng.random() < .7:
            cs = [c for c in range(2, Wd) if g[r][c] == 0]
            if cs: g[r][rng.choice(cs)] = rng.choice((2, 4))
        return g
    return gen


def tf_mirror(g):
    n = srcs(g, (0, 2, 4, 8, W))
    if len(n) != 1 or n[0][1] != 0: return None
    r, c = n[0]; s = g[r][c]; p, h = trace(g, r, c, (0, 1))
    if h < 2: return None
    out = copy(g); paint(out, p, s, g); return out
rule("stream_reflects_off_mirrors", "The nozzle at the left edge fires a stream right; a colour-2 cell is a '/' mirror and a colour-4 cell is a '\\' mirror (right turns up at '/', down at '\\'; up turns right at '/', left at '\\'; left turns down at '/', up at '\\'; down turns left at '/', right at '\\'); the stream paints every empty cell it crosses in the nozzle colour, keeps going until it leaves the grid, and mirrors stay as they are.",
     mk(mirrors_gen(False), tf_mirror), tf_mirror)


def tf_mirror_shapes(g):
    n = srcs(g, (0, 2, 4, 8, W))
    if len(n) != 1 or n[0][1] != 0: return None
    r, c = n[0]; s = g[r][c]; p, h = trace(g, r, c, (0, 1))
    if h < 1: return None
    lit, dark = split_shapes(g, p); out = copy(g)
    for cm in dark:
        for y, x in cm: out[y][x] = 0
    for cm in lit:
        for y, x in cm: out[y][x] = s
    paint(out, p, s, g); return out
rule("mirror_stream_lights_shapes_erases_rest", "The nozzle at the left edge fires a stream right, passing through colour-8 shapes and bending at mirrors (colour 2 is '/', colour 4 is '\\') until it leaves the grid; empty cells it crosses and every colour-8 shape it passes through take the nozzle colour, colour-8 shapes it never passes through are erased, and mirrors stay.",
     mk(mirrors_gen(True), tf_mirror_shapes, okls), tf_mirror_shapes)


def split_gen(rng):
    H, Wd = D(rng, 8, 30), D(rng, 8, 30); g = blank(H, Wd); r = rng.randint(2, H - 3)
    g[r][0] = src(rng, (3, 5))
    cs = rng.sample(range(2, Wd), min(Wd - 2, 1)); g[r][cs[0]] = 3
    for _ in range(rng.randint(1, max(2, H * Wd // 90))):
        put(rng, g, 3)
    return g


def tf_split(g):
    n = srcs(g, (0, 3))
    if len(n) != 1 or n[0][1] != 0: return None
    r, c = n[0]; s = g[r][c]; p, h = trace(g, r, c, (0, 1), split=True)
    if h < 2: return None
    out = copy(g); paint(out, p, s, g); return out
rule("stream_splits_at_prisms", "The nozzle at the left edge fires a stream right; when a stream meets a colour-3 splitter cell it ends there and sends two new streams away from it at right angles to its travel direction (both sides); all streams paint the empty cells they cross in the nozzle colour until the grid edge, and splitter cells stay colour 3.",
     mk(split_gen, tf_split), tf_split)


def zig_gen(rng):
    H, Wd = D(rng, 8, 30), D(rng, 4, 14); g = blank(H, Wd); sprinkle(rng, g, int(H * Wd * .05), W)
    c = rng.randrange(Wd)
    if g[0][c]: return None
    g[0][c] = src(rng, (5,)); return g


def tf_zig(g):
    H, Wd = dims(g); n = srcs(g)
    if len(n) != 1 or n[0][0] != 0: return None
    r, c = n[0]; s = g[r][c]; dx = 1; out = copy(g); path = 0
    while r + 1 < H:
        nc = c + dx
        if not (0 <= nc < Wd) or g[r + 1][nc] == W:
            dx = -dx; nc = c + dx
            if not (0 <= nc < Wd) or g[r + 1][nc] == W: break
        r += 1; c = nc; out[r][c] = s; path += 1
    return out if path >= 3 else None
rule("diagonal_stream_bounces_walls", "The nozzle cell in the top row fires a stream that moves one row down and one column right at every step, painting the nozzle colour; if its next cell is off the grid or a grey (5) cell it reverses its sideways direction (left instead of right, and so on) for that step, and if that is blocked too it stops; it ends at the bottom row.",
     mk(zig_gen, tf_zig), tf_zig)


def two_gen(rng):
    H, Wd = D(rng, 8, 30), D(rng, 8, 30); g = blank(H, Wd); r, c = rng.randint(1, H - 1), rng.randint(1, Wd - 1)
    a, b = rng.sample([x for x in range(1, 10) if x not in (5, 6)], 2)
    sprinkle(rng, g, int(H * Wd * .04), W)
    if g[r][0] or g[0][c]: return None
    g[r][0] = a; g[0][c] = b; return g


def tf_two(g):
    H, Wd = dims(g); n = srcs(g, (0, W))
    if len(n) != 2: return None
    ra = [p for p in n if p[1] == 0 and p[0] > 0]; rb = [p for p in n if p[0] == 0 and p[1] > 0]
    if len(ra) != 1 or len(rb) != 1: return None
    pa = ray(g, ra[0][0], 0, 0, 1); pb = ray(g, 0, rb[0][1], 1, 0); out = copy(g)
    for r, c in pa:
        if g[r][c] == 0: out[r][c] = g[ra[0][0]][0]
    for r, c in pb:
        if g[r][c] == 0: out[r][c] = 6 if (r, c) in set(pa) else g[0][rb[0][1]]
    return out if set(pa) & set(pb) else None
rule("crossing_streams_mix_to_six", "One nozzle on the left edge fires a stream right and one nozzle on the top edge fires a stream down, each painting empty cells in its own colour and stopping at the grid edge or a grey (5) cell; the cell where the two streams cross is painted colour 6 (only inputs where they cross appear).",
     mk(two_gen, tf_two), tf_two)


def rng_gen(rng):
    H, Wd = D(rng, 12, 30), D(rng, 12, 30); g = blank(H, Wd); nz = rng.randint(2, min(7, H // 2))
    rows = sorted(rng.sample(range(0, H, 2), nz))
    for r in rows: g[r][0] = rng.choice([1, 2, 3, 4, 6, 7, 8, 9])
    sprinkle(rng, g, int(H * Wd * .04), W)
    for r in rows: g[r][1] = 0 if g[r][1] == 5 else g[r][1]
    return g


def tf_range(g):
    out = copy(g); H, Wd = dims(g); n = [(r, g[r][0]) for r in range(H) if g[r][0] not in (0,)]
    if not n or any(v == W for _, v in n): return None
    for r, d in n:
        for c in range(1, min(Wd, d + 1)):
            if g[r][c] == W: break
            out[r][c] = d
    return out
rule("nozzle_digit_is_stream_range", "Each nozzle cell at the left edge with value d (1-9, never 5) fires a stream to the right that paints the next d cells of its row with value d, stopping early at a grey (5) cell or the grid edge.",
     mk(rng_gen, tf_range), tf_range, digits=True)


# =============================================================== racing sources
def race_tf(n, tie_val, tg=False):
    def tf(g):
        sc = srcs(g, (0, W, 8) if tg else (0, W))
        if len(sc) != n: return None
        ok = (lambda v: v in (0, 8)) if tg else (lambda v: v == 0)
        ds = [bfs(g, [p], ok) for p in sc]; cols = [g[p[0]][p[1]] for p in sc]; out = copy(g)
        for r, row in enumerate(g):
            for c, v in enumerate(row):
                if v != (8 if tg else 0): continue
                best = [(d[(r, c)], i) for i, d in enumerate(ds) if (r, c) in d]
                if not best: continue
                m = min(b[0] for b in best); w = [i for dd, i in best if dd == m]
                out[r][c] = cols[w[0]] if len(w) == 1 else tie_val(g[r][c])
        return out
    return tf


def race_gen(n, targets=False, ex=(5, 8)):
    def gen(rng):
        H, Wd = D(rng, 7, 30), D(rng, 7, 30); g = blank(H, Wd); scatter2(rng, g, rng.uniform(.12, .24))
        for c in rng.sample([c for c in range(1, 10) if c not in ex], n):
            if put(rng, g, c) is None: return None
        if targets:
            for _ in range(rng.randint(3, 9)): put(rng, g, 8)
        return g
    return gen


def race_cond(n, tg=False):
    def cond(g, o):
        base = 8 if tg else 0
        ch = sum(1 for r, row in enumerate(g) for c, v in enumerate(row) if v == base and o[r][c] != base)
        return ch >= (2 if tg else 6)
    return cond
t2 = race_tf(2, lambda v: 9); t3 = race_tf(3, lambda v: v); t8 = race_tf(2, lambda v: v, True)
rule("two_sources_race_ties_nine", "Two coloured source cells flood the empty cells through edge-adjacent empty cells (grey 5 walls; the other source also blocks); each empty cell takes the colour of the source with the shorter path to it, an exact tie becomes colour 9, and cells neither source can reach stay empty.",
     mk(race_gen(2, ex=(5, 9)), t2, race_cond(2)), t2)
rule("three_sources_race_ties_stay_empty", "Three coloured source cells flood the empty cells through edge-adjacent empty cells (grey 5 walls; other sources also block); each empty cell takes the colour of the strictly nearest source by path length, a cell with two or more equally near sources stays empty, as do unreachable cells.",
     mk(race_gen(3, ex=(5,)), t3, race_cond(3)), t3)
rule("race_to_targets_nearer_source_wins", "Two coloured source cells and several colour-8 target cells lie in an area walled by grey (5) cells; each target takes the colour of the source whose path to it through empty or target cells is strictly shorter, ties and unreachable targets stay colour 8, and no other cell changes.",
     mk(race_gen(2, True), t8, race_cond(2, True)), t8)


# =============================================================== rooms
def split_rooms(rng, g, r0, c0, r1, c1, rooms, doors, door_p, depth=0):
    h, w = r1 - r0 + 1, c1 - c0 + 1
    if (h < 5 and w < 5) or (depth > 1 and rng.random() < .25) or h < 3 or w < 3:
        rooms.append((r0, c0, r1, c1)); return
    if h >= 5 and (w < 5 or rng.random() < h / (h + w)):
        k = rng.randint(r0 + 2, r1 - 2)
        for c in range(c0, c1 + 1): g[k][c] = W
        if rng.random() < door_p: doors.append((k, rng.randint(c0, c1)))
        split_rooms(rng, g, r0, c0, k - 1, c1, rooms, doors, door_p, depth + 1); split_rooms(rng, g, k + 1, c0, r1, c1, rooms, doors, door_p, depth + 1)
    else:
        k = rng.randint(c0 + 2, c1 - 2)
        for r in range(r0, r1 + 1): g[r][k] = W
        if rng.random() < door_p: doors.append((rng.randint(r0, r1), k))
        split_rooms(rng, g, r0, c0, r1, k - 1, rooms, doors, door_p, depth + 1); split_rooms(rng, g, r0, k + 1, r1, c1, rooms, doors, door_p, depth + 1)


def rooms_gen(door_p, taps):
    def gen(rng):
        H, Wd = D(rng, 8, 30), D(rng, 8, 30); g = blank(H, Wd); rooms = []; doors = []
        split_rooms(rng, g, 0, 0, H - 1, Wd - 1, rooms, doors, door_p)
        for r, c in doors: g[r][c] = 0
        if taps == 'many':
            for (r0, c0, r1, c1) in rooms:
                if rng.random() < .55:
                    for _ in range(rng.choice((1, 1, 2))): g[rng.randint(r0, r1)][rng.randint(c0, c1)] = rng.choice([1, 2, 3, 4, 7, 8, 9])
        else:
            if put(rng, g, src(rng, (5,))) is None: return None
        return g
    return gen


def tf_rooms_mix(g):
    H, Wd = dims(g); seen = set(); out = copy(g)
    for r in range(H):
        for c in range(Wd):
            if g[r][c] == W or (r, c) in seen: continue
            d = bfs(g, [(r, c)], lambda v: v != W); seen |= set(d)
            cols = {g[y][x] for y, x in d if g[y][x] != 0}
            if not cols: continue
            col = list(cols)[0] if len(cols) == 1 else 6
            for y, x in d:
                if g[y][x] == 0: out[y][x] = col
    return out
rule("sealed_rooms_fill_from_taps", "Grey (5) lines divide the grid into sealed rooms; a room with tap cells of one colour has all its empty cells filled with that colour, a room whose taps have two different colours is filled with colour 6, and rooms with no tap stay empty (taps stay as they are).",
     mk(rooms_gen(0, 'many'), tf_rooms_mix, lambda g, o: any(v == 6 for r in o for v in r)), tf_rooms_mix)
rule("tap_floods_through_doorways", "The single tap cell fills its room and floods every empty cell connected to it through edge-adjacent empty cells, including through one-cell doorways (gaps) in the grey (5) wall lines, in the tap colour; rooms not connected by a doorway stay empty.",
     mk(rooms_gen(.6, 'one'), tf4, unreached), tf4)


def isl_gen(rng):
    H, Wd = D(rng, 8, 30), D(rng, 8, 30); g = blank(H, Wd)
    if not shapes_in(g, rng.randint(3, max(4, H * Wd // 45)), rng): return None
    scatter2(rng, g, rng.uniform(.1, .2))
    if put(rng, g, src(rng, (5, 8))) is None: return None
    return g


def tf_isl(g):
    sc = srcs(g, (0, W, 8))
    if len(sc) != 1: return None
    s = g[sc[0][0]][sc[0][1]]; d = bfs(g, sc, lambda v: v == 0); out = copy(g)
    for p in d:
        if p != sc[0]: out[p[0]][p[1]] = s
    for cm in components(g, 8, conn8=True):
        touched = any((y + dr, x + dc) in d for y, x in cm for dr, dc in N4)
        for y, x in cm: out[y][x] = s if touched else 0
    return out
rule("flood_lights_touched_islands", "The source cell floods all empty cells connected to it through edge-adjacent empty cells (grey 5 walls, colour-8 islands also block) in its own colour; every colour-8 island with a cell edge-adjacent to a flooded cell turns the source colour, and every other colour-8 island is erased.",
     mk(isl_gen, tf_isl, okls), tf_isl)
