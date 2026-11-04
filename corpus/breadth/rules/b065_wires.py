# b065_wires.py -- SIGNALS ALONG WIRES: grey (colour 5) paths connect coloured source cells to lamps
# (hollow 3x3 rings of a fixed marker colour, or solid grey 3x3 blocks fused to the wire's end). A lamp
# lights in the colour of the source it is wired to, PROVIDED the wire between them is an unbroken chain
# of grey cells. 40 distinct rules on that theme: conflicts, gates, switches, gaps, junctions, counting.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

WIRE = 5


# ---------- shared detection helpers (generic: work off the grid, not generator state) ----------
def _grey_comp(g):
    return components(g, WIRE, conn8=False)


def _multi_comp(g, colset):
    """Connected components over several DIFFERENT colour values (glib's components() only
    flood-fills within one colour even with a custom predicate, so gate/switch cells fused to
    a grey wire need their own connectivity scan)."""
    H, W = dims(g); seen = set(); out = []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or g[r][c] not in colset:
                continue
            comp = []; st = [(r, c)]; seen.add((r, c))
            while st:
                y, x = st.pop(); comp.append((y, x))
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen and g[ny][nx] in colset:
                        seen.add((ny, nx)); st.append((ny, nx))
            out.append(comp)
    return out


def _touching(comp, cell):
    r, c = cell
    return any(abs(r - rr) + abs(c - cc) == 1 for rr, cc in comp)


def _comp_touch(a, b):
    sb = set(b)
    return any((rr + dr, cc + dc) in sb for rr, cc in a for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)))


def _adjacent_colours(g, comp, exclude=(0, WIRE, 2)):
    h, w = dims(g); seen = set(comp); out = {}
    for r, c in comp:
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in seen:
                v = g[nr][nc]
                if v not in exclude:
                    out.setdefault(v, []).append((nr, nc))
    return out


def _ring_touching(g, comp, mark):
    for rc in components(g, mark, conn8=False):
        r0, c0, r1, c1 = bbox(rc)
        if r1 - r0 == 2 and c1 - c0 == 2 and len(rc) == 8 and _comp_touch(comp, rc):
            return (r0, c0, r0 + 1, c0 + 1)
    return None


def _block_cells(g, comp):
    s = set(comp); out = set()
    for r, c in comp:
        if all((r + dr, c + dc) in s for dr in range(3) for dc in range(3)):
            for dr in range(3):
                for dc in range(3):
                    out.add((r + dr, c + dc))
    return out


# ---------- shared layout helpers ----------
def _draw_h(g, r, c0, length, col=WIRE):
    for i in range(length): g[r][c0 + i] = col


def _draw_v(g, c, r0, length, col=WIRE):
    for i in range(length): g[r0 + i][c] = col


def _ring(g, r0, c0, mark):
    rect(g, r0, c0, r0 + 2, c0 + 2, mark, fill=False)
    return (r0 + 1, c0 + 1)


def _big(rng, lo=20, hi=30):
    s = rng.randint(lo, hi); return s, s


# arm helpers: attach a short wire+source to one side of a ring at (r0, c0) without ever
# overwriting the ring's own border cells. Each returns the list of wire cells, or None if it
# would run off the grid (the caller then rejects the input).
def _west_arm(g, r0, c0, col, length):
    row = r0 + 1; start = c0 - 1 - length
    if start < 0: return None
    g[row][start] = col; cells = []
    for i in range(1, length + 1):
        g[row][start + i] = WIRE; cells.append((row, start + i))
    return cells


def _east_arm(g, r0, c0, col, length):
    w = len(g[0]); row = r0 + 1; pos = c0 + 2 + 1 + length
    if pos >= w: return None
    g[row][pos] = col; cells = []
    for i in range(1, length + 1):
        g[row][pos - i] = WIRE; cells.append((row, pos - i))
    return cells


def _south_arm(g, r0, c0, col, length):
    h = len(g); c = c0 + 1; pos = r0 + 2 + 1 + length
    if pos >= h: return None
    g[pos][c] = col; cells = []
    for i in range(1, length + 1):
        g[pos - i][c] = WIRE; cells.append((pos - i, c))
    return cells


# ================================================================== 1
def gi_basic(rng):
    h, w = _big(rng); g = blank(h, w)
    length = rng.randint(3, w - 8); r = rng.randint(1, h - 2); cs = rng.randint(0, w - length - 6)
    src = colours(rng, 1, exclude=(0, 2))[0]
    g[r][cs] = src; _draw_h(g, r, cs + 1, length)
    _ring(g, r - 1, cs + length + 1, 2)
    return g
def tf_basic(g):
    out = copy(g)
    for comp in _grey_comp(g):
        rg = _ring_touching(g, comp, 2)
        srcs = _adjacent_colours(g, comp)
        if rg and len(srcs) == 1:
            col = list(srcs)[0]; r0, c0, cen_r, cen_c = rg
            out[cen_r][cen_c] = col
    return out
rule("wire_lights_lamp_source_colour", "A grey wire carries its single source cell's colour to the centre of the hollow ring lamp it touches.", gi_basic, tf_basic)


# ================================================================== 2
def gi_blocklamp(rng):
    h, w = _big(rng); g = blank(h, w)
    length = rng.randint(3, w - 9); r = rng.randint(2, h - 3); cs = rng.randint(0, w - length - 7)
    src = colours(rng, 1, exclude=(0,))[0]
    g[r][cs] = src; _draw_h(g, r, cs + 1, length)
    rect(g, r - 1, cs + length + 1, r + 1, cs + length + 3, WIRE, fill=True)
    return g
def tf_blocklamp(g):
    out = copy(g)
    for comp in _grey_comp(g):
        blk = _block_cells(g, comp)
        srcs = _adjacent_colours(g, comp)
        if blk and len(srcs) == 1:
            col = list(srcs)[0]
            for r, c in blk: out[r][c] = col
    return out
rule("block_lamp_lights_source_colour", "A grey wire fused to a solid 3x3 grey block lights the whole block in the colour of its one source cell.", gi_blocklamp, tf_blocklamp)


# ================================================================== 3
def gi_pathcolour(rng):
    h, w = _big(rng); g = blank(h, w)
    length = rng.randint(4, w - 6); r = rng.randint(1, h - 2); cs = rng.randint(0, w - length - 2)
    src = colours(rng, 1, exclude=(0,))[0]
    g[r][cs] = src; _draw_h(g, r, cs + 1, length)
    return g
def tf_pathcolour(g):
    out = copy(g)
    for comp in _grey_comp(g):
        srcs = _adjacent_colours(g, comp)
        if len(srcs) == 1:
            col = list(srcs)[0]
            for r, c in comp: out[r][c] = col
    return out
rule("wire_path_recolours_to_source", "Every grey wire cell is recoloured to the colour of the single source cell it is wired to; lamps are not involved.", gi_pathcolour, tf_pathcolour)


# ================================================================== 4
def gi_disc(rng):
    h, w = _big(rng); g = blank(h, w)
    length = rng.randint(3, w - 10)
    r = rng.randint(1, h - 2); cs = rng.randint(0, w - length - 8)
    _draw_h(g, r, cs, length)   # no source cell: dangling wire
    _ring(g, r - 1, cs + length, 2)
    return g
def tf_disc(g):
    out = copy(g)
    for comp in _grey_comp(g):
        rg = _ring_touching(g, comp, 2)
        srcs = _adjacent_colours(g, comp)
        if rg and not srcs:
            r0, c0, cr, cc = rg; out[cr][cc] = WIRE   # dark lamp marked grey
    return out
rule("disconnected_wire_lamp_stays_dark", "A wire with no source cell lights nothing; its ring lamp's centre is marked grey to show it stayed dark.", gi_disc, tf_disc)


# ================================================================== 5
def gi_multi(rng):
    h, w = _big(rng); g = blank(h, w); k = rng.randint(2, 3)
    rows = rng.sample(range(1, h - 1), k)
    for r in rows:
        length = rng.randint(3, w // 2); cs = rng.randint(0, w - length - 6)
        src = colours(rng, 1, exclude=(0, 2))[0]
        g[r][cs] = src; _draw_h(g, r, cs + 1, length)
        if r - 1 >= 0 and r + 1 < h: _ring(g, r - 1, cs + length + 1, 2)
    return g if len(_grey_comp(g)) >= k else None
def tf_multi(g):
    out = copy(g)
    for comp in _grey_comp(g):
        rg = _ring_touching(g, comp, 2); srcs = _adjacent_colours(g, comp)
        if rg and len(srcs) == 1:
            r0, c0, cr, cc = rg; out[cr][cc] = list(srcs)[0]
    return out
rule("multi_wire_each_lamp_own_colour", "Each of several independent wires lights only its own ring lamp, in its own source's colour.", gi_multi, tf_multi)


# ================================================================== 6
def gi_unwired(rng):
    h, w = _big(rng); g = blank(h, w)
    r0, c0 = rng.randint(1, h - 4), rng.randint(1, w - 4)
    _ring(g, r0, c0, 2)
    src = colours(rng, 1, exclude=(0, 2))[0]
    r1 = rng.randint(1, h - 2); c1 = rng.randint(1, w - 2)
    while abs(r1 - (r0 + 1)) + abs(c1 - c0) < 6:
        r1 = rng.randint(1, h - 2); c1 = rng.randint(1, w - 2)
    g[r1][c1] = src
    return g
def tf_unwired(g):
    out = copy(g)
    for rc in components(g, 2, conn8=False):
        r0, c0, r1, c1 = bbox(rc)
        if r1 - r0 == 2 and c1 - c0 == 2 and len(rc) == 8:
            out[r0 + 1][c0 + 1] = WIRE
    return out
rule("unwired_lamp_remains_unlit", "A ring lamp with no wire touching it at all has its centre marked grey; nearby unconnected sources do nothing.", gi_unwired, tf_unwired)


# ================================================================== 7
def gi_gapmark(rng):
    h, w = _big(rng); g = blank(h, w)
    length = rng.randint(6, w - 10); r = rng.randint(1, h - 2); cs = rng.randint(0, w - length - 6)
    src = colours(rng, 1, exclude=(0, 2, 9))[0]
    g[r][cs] = src; _draw_h(g, r, cs + 1, length)
    gap = rng.randint(cs + 2, cs + length - 1)
    g[r][gap] = 0
    _ring(g, r - 1, cs + length + 1, 2)
    return g
def tf_gapmark(g):
    out = copy(g)
    for comp in _grey_comp(g):
        rg = _ring_touching(g, comp, 2); srcs = _adjacent_colours(g, comp)
        if rg:
            r0, c0, cr, cc = rg
            out[cr][cc] = WIRE if len(srcs) != 1 or not srcs else list(srcs)[0]
    h, w = dims(g)
    for r in range(h):
        for c in range(w):
            if g[r][c] == 0 and 0 < c < w - 1 and g[r][c - 1] == WIRE and g[r][c + 1] == WIRE:
                out[r][c] = 9
    return out
rule("broken_wire_gap_marked_blocks_lamp", "A one-cell gap in the wire (background between two grey ends) is painted 9 and the lamp it would have fed stays dark grey.", gi_gapmark, tf_gapmark)


# ================================================================== 8
def gi_twobreak(rng):
    h, w = _big(rng); g = blank(h, w)
    rows = rng.sample(range(1, h - 1), 2); broken_row = rng.choice(rows)
    for r in rows:
        length = rng.randint(5, w // 2); cs = rng.randint(0, w - length - 6)
        src = colours(rng, 1, exclude=(0, 2))[0]
        g[r][cs] = src; _draw_h(g, r, cs + 1, length)
        if r == broken_row:
            g[r][cs + 1 + length // 2] = 0
        _ring(g, r - 1, cs + length + 1, 2)
    return g
def tf_twobreak(g):
    out = copy(g)
    for comp in _grey_comp(g):
        rg = _ring_touching(g, comp, 2); srcs = _adjacent_colours(g, comp)
        if rg:
            r0, c0, cr, cc = rg
            out[cr][cc] = list(srcs)[0] if len(srcs) == 1 else WIRE
    return out
rule("two_wires_only_unbroken_lights", "Of two wires only the one with no gap lights its lamp; the broken wire's lamp stays grey.", gi_twobreak, tf_twobreak)


# ================================================================== 9
def gi_gapone(rng):
    h, w = _big(rng); g = blank(h, w)
    length = rng.randint(10, w - 8); r = rng.randint(1, h - 2); cs = rng.randint(0, w - length - 6)
    src = colours(rng, 1, exclude=(0, 2))[0]
    g[r][cs] = src; _draw_h(g, r, cs + 1, length)
    gap = cs + 1 + length - 2  # gap near the far end, long wire before it
    g[r][gap] = 0
    _ring(g, r - 1, cs + length + 1, 2)
    return g
def tf_gapone(g):
    out = copy(g)
    for comp in _grey_comp(g):
        rg = _ring_touching(g, comp, 2); srcs = _adjacent_colours(g, comp)
        if rg:
            r0, c0, cr, cc = rg
            out[cr][cc] = list(srcs)[0] if len(srcs) == 1 else WIRE
    return out
rule("gap_size_one_breaks_regardless_length", "Even a single-cell gap near the lamp end of a long wire stops the signal completely; the lamp stays grey.", gi_gapone, tf_gapone)


# ---------- gates: colour 8 cell passes the signal, colour 4 cell blocks it (digits) ----------
# ================================================================== 10
def gi_gatepass(rng):
    h, w = _big(rng); g = blank(h, w)
    length = rng.randint(6, w - 10); r = rng.randint(1, h - 2); cs = rng.randint(0, w - length - 6)
    src = colours(rng, 1, exclude=(0, 2, 4, 8))[0]
    g[r][cs] = src; _draw_h(g, r, cs + 1, length)
    g[r][cs + 1 + length // 2] = 8
    _ring(g, r - 1, cs + length + 1, 2)
    return g
def tf_gatepass(g):
    out = copy(g)
    for comp in _grey_comp(g) :
        pass
    for comp in _multi_comp(g, {WIRE, 8}):
        rg = _ring_touching(g, comp, 2); srcs = _adjacent_colours(g, comp, exclude=(0, WIRE, 2, 8))
        if rg and len(srcs) == 1:
            r0, c0, cr, cc = rg; out[cr][cc] = list(srcs)[0]
    return out
rule("gate_pass_colour_lets_signal_through", "A colour-8 cell sitting on the wire passes the signal straight through; the lamp lights the source's colour.", gi_gatepass, tf_gatepass, digits=True)


# ================================================================== 11
def gi_gateblock(rng):
    h, w = _big(rng); g = blank(h, w)
    length = rng.randint(6, w - 10); r = rng.randint(1, h - 2); cs = rng.randint(0, w - length - 6)
    src = colours(rng, 1, exclude=(0, 2, 4, 8))[0]
    g[r][cs] = src; _draw_h(g, r, cs + 1, length)
    g[r][cs + 1 + length // 2] = 4
    _ring(g, r - 1, cs + length + 1, 2)
    return g
def tf_gateblock(g):
    out = copy(g)
    for comp in _multi_comp(g, {WIRE, 8}):
        rg = _ring_touching(g, comp, 2); srcs = _adjacent_colours(g, comp, exclude=(0, WIRE, 2, 8))
        if rg:
            r0, c0, cr, cc = rg
            out[cr][cc] = list(srcs)[0] if len(srcs) == 1 else WIRE
    return out
rule("gate_block_colour_stops_signal", "A colour-4 cell sitting on the wire blocks the signal; a wire interrupted by one never lights its lamp.", gi_gateblock, tf_gateblock, digits=True)


# ================================================================== 12
def gi_gatechain(rng):
    h, w = _big(rng); g = blank(h, w)
    length = rng.randint(10, w - 8); r = rng.randint(1, h - 2); cs = rng.randint(0, w - length - 6)
    src = colours(rng, 1, exclude=(0, 2, 4, 8))[0]
    g[r][cs] = src; _draw_h(g, r, cs + 1, length)
    p1, p2 = cs + 1 + length // 3, cs + 1 + 2 * length // 3
    g[r][p1] = rng.choice([4, 8]); g[r][p2] = rng.choice([4, 8])
    _ring(g, r - 1, cs + length + 1, 2)
    return g
def tf_gatechain(g):
    out = copy(g)
    for comp in _multi_comp(g, {WIRE, 8}):
        rg = _ring_touching(g, comp, 2); srcs = _adjacent_colours(g, comp, exclude=(0, WIRE, 2, 8))
        if rg:
            r0, c0, cr, cc = rg
            out[cr][cc] = list(srcs)[0] if len(srcs) == 1 else WIRE
    return out
rule("wire_with_two_gates_all_must_pass", "A wire crossing two gate cells only lights its lamp if every gate on it is colour 8; one colour-4 gate kills the whole signal.", gi_gatechain, tf_gatechain, digits=True)


# ================================================================== 13
def gi_twingates(rng):
    h, w = _big(rng); g = blank(h, w)
    rows = rng.sample(range(1, h - 1), 2); gates = [8, 4]; rng.shuffle(gates)
    for r, gate in zip(rows, gates):
        length = rng.randint(6, w // 2); cs = rng.randint(0, w - length - 6)
        src = colours(rng, 1, exclude=(0, 2, 4, 8))[0]
        g[r][cs] = src; _draw_h(g, r, cs + 1, length)
        g[r][cs + 1 + length // 2] = gate
        _ring(g, r - 1, cs + length + 1, 2)
    return g
def tf_twingates(g):
    out = copy(g)
    for comp in _multi_comp(g, {WIRE, 8}):
        rg = _ring_touching(g, comp, 2); srcs = _adjacent_colours(g, comp, exclude=(0, WIRE, 2, 8))
        if rg:
            r0, c0, cr, cc = rg
            out[cr][cc] = list(srcs)[0] if len(srcs) == 1 else WIRE
    return out
rule("twin_wires_different_gates_compare", "Of two gated wires the one gated by colour 8 lights its lamp, the one gated by colour 4 leaves its lamp grey.", gi_twingates, tf_twingates, digits=True)


# ---------- switches: a fixed switch cell toggles transmission ----------
# ================================================================== 14
def gi_swon(rng):
    h, w = _big(rng); g = blank(h, w)
    length = rng.randint(6, w - 10); r = rng.randint(1, h - 2); cs = rng.randint(0, w - length - 6)
    src = colours(rng, 1, exclude=(0, 2, 6))[0]
    g[r][cs] = src; _draw_h(g, r, cs + 1, length)
    g[r][cs + 1 + length // 2] = 6
    _ring(g, r - 1, cs + length + 1, 2)
    return g
def tf_swon(g):
    out = copy(g)
    for comp in _multi_comp(g, {WIRE, 6}):
        rg = _ring_touching(g, comp, 2); srcs = _adjacent_colours(g, comp, exclude=(0, WIRE, 2, 6))
        if rg and len(srcs) == 1:
            r0, c0, cr, cc = rg; out[cr][cc] = list(srcs)[0]
    return out
rule("switch_on_colour_enables_transmission", "A colour-6 switch cell on the wire is 'on' and lets the source's colour reach the lamp.", gi_swon, tf_swon)


# ================================================================== 15
def gi_swoff(rng):
    h, w = _big(rng); g = blank(h, w)
    length = rng.randint(6, w - 10); r = rng.randint(1, h - 2); cs = rng.randint(0, w - length - 6)
    src = colours(rng, 1, exclude=(0, 2, 7))[0]
    g[r][cs] = src; _draw_h(g, r, cs + 1, length)
    g[r][cs + 1 + length // 2] = 7
    _ring(g, r - 1, cs + length + 1, 2)
    return g
def tf_swoff(g):
    out = copy(g)
    for comp in _multi_comp(g, {WIRE, 7}):
        rg = _ring_touching(g, comp, 2)
        if rg:
            r0, c0, cr, cc = rg; out[cr][cc] = WIRE
    return out
rule("switch_off_colour_disables_transmission", "A colour-7 switch cell on the wire is 'off' and keeps the lamp dark regardless of the source.", gi_swoff, tf_swoff)


# ================================================================== 16
def gi_swboth(rng):
    h, w = _big(rng); g = blank(h, w)
    rows = rng.sample(range(1, h - 1), 2); states = [6, 7]; rng.shuffle(states)
    for r, st in zip(rows, states):
        length = rng.randint(6, w // 2); cs = rng.randint(0, w - length - 6)
        src = colours(rng, 1, exclude=(0, 2, 6, 7))[0]
        g[r][cs] = src; _draw_h(g, r, cs + 1, length)
        g[r][cs + 1 + length // 2] = st
        _ring(g, r - 1, cs + length + 1, 2)
    return g
def tf_swboth(g):
    out = copy(g)
    for comp in _multi_comp(g, {WIRE, 6, 7}):
        rg = _ring_touching(g, comp, 2)
        if not rg: continue
        r0, c0, cr, cc = rg
        if any(g[r][c] == 7 for r, c in comp):
            out[cr][cc] = WIRE
        else:
            srcs = _adjacent_colours(g, comp, exclude=(0, WIRE, 2, 6, 7))
            out[cr][cc] = list(srcs)[0] if len(srcs) == 1 else WIRE
    return out
rule("switch_state_decides_two_wires", "Each wire carries one switch cell: colour 6 lets its lamp light the source colour, colour 7 keeps it dark.", gi_swboth, tf_swboth)


# ---------- k-step propagation: signal travels k cells where k is the source's colour value (digits) ----------
# ================================================================== 17
def gi_kstep(rng):
    h, w = _big(rng); g = blank(h, w)
    src = rng.randint(1, 7)
    length = rng.randint(src + 3, w - 4)
    r = rng.randint(0, h - 1); cs = rng.randint(0, w - length - 2)
    g[r][cs] = src; _draw_h(g, r, cs + 1, length, col=0)
    for i in range(length): g[r][cs + 1 + i] = WIRE
    return g
def tf_kstep(g):
    out = copy(g); h, w = dims(g)
    for r in range(h):
        c = 0
        while c < w:
            if g[r][c] not in (0, WIRE):
                k = g[r][c]; cc = c + 1
                lit = 0
                while cc < w and g[r][cc] == WIRE and lit < k:
                    out[r][cc] = k; cc += 1; lit += 1
            c += 1
    return out
rule("signal_propagates_k_steps_then_grey", "The signal travels k wire cells from its source, k being the source's colour value, then the rest of the wire stays grey.", gi_kstep, tf_kstep, digits=True)


# ================================================================== 18
def gi_kreach(rng):
    h, w = _big(rng); g = blank(h, w)
    src = rng.randint(2, 8)
    length = rng.randint(2, w - 8)
    r = rng.randint(1, h - 2); cs = rng.randint(0, w - length - 6)
    g[r][cs] = src; _draw_h(g, r, cs + 1, length)
    _ring(g, r - 1, cs + length + 1, 2)
    return g
def tf_kreach(g):
    out = copy(g)
    for comp in _grey_comp(g):
        rg = _ring_touching(g, comp, 2); srcs = _adjacent_colours(g, comp)
        if rg and len(srcs) == 1:
            r0, c0, cr, cc = rg; col = list(srcs)[0]
            out[cr][cc] = col if col >= len(comp) else WIRE
    return out
rule("lamp_lights_only_if_k_reaches_it", "The lamp lights only if the source's colour value is at least the wire's length in cells; a shorter reach leaves it grey.", gi_kreach, tf_kreach, digits=True)


# ================================================================== 19
def gi_kvaries(rng):
    h, w = _big(rng); g = blank(h, w)
    src = rng.choice([1, 2, 3, 4, 5, 6]) if False else rng.randint(1, 6)
    length = rng.randint(src, w - 4)
    r = rng.randint(0, h - 1); cs = rng.randint(0, w - length - 2)
    g[r][cs] = src
    for i in range(length): g[r][cs + 1 + i] = WIRE
    return g
def tf_kvaries(g):
    out = copy(g); h, w = dims(g)
    for r in range(h):
        c = 0
        while c < w:
            if g[r][c] not in (0, WIRE):
                k = g[r][c]; cc = c + 1; lit = 0
                while cc < w and g[r][cc] == WIRE and lit < k:
                    out[r][cc] = k; cc += 1; lit += 1
            c += 1
    return out
# k_step_varies_per_block dropped 2026-10-12 (review 2: behavioural duplicate of signal_propagates_k_steps_then_grey)
# ---------- conflicts: a lamp wired to two different-coloured sources ----------
# ================================================================== 20
def gi_conflict(rng):
    h, w = _big(rng); g = blank(h, w)
    r0, c0 = rng.randint(3, h - 6), rng.randint(3, w - 8)
    cen = _ring(g, r0, c0, 2)
    c1, c2 = colours(rng, 2, exclude=(0, 2))
    if _west_arm(g, r0, c0, c1, 2) is None: return None
    if _south_arm(g, r0, c0, c2, 2) is None: return None
    return g
def tf_conflict(g):
    out = copy(g)
    for comp in _grey_comp(g):
        rg = _ring_touching(g, comp, 2); srcs = _adjacent_colours(g, comp)
        if rg:
            r0, c0, cr, cc = rg
            out[cr][cc] = list(srcs)[0] if len(srcs) == 1 else WIRE
    return out
rule("two_sources_conflict_lights_grey", "A lamp wired to two sources of different colours cannot pick one and lights grey instead.", gi_conflict, tf_conflict)


# ================================================================== 21
def gi_noconflict(rng):
    h, w = _big(rng); g = blank(h, w)
    r0, c0 = rng.randint(3, h - 6), rng.randint(3, w - 8)
    cen = _ring(g, r0, c0, 2)
    col = colours(rng, 1, exclude=(0, 2))[0]
    if _west_arm(g, r0, c0, col, 2) is None: return None
    if _south_arm(g, r0, c0, col, 2) is None: return None
    return g
def tf_noconflict(g):
    out = copy(g)
    for comp in _grey_comp(g):
        rg = _ring_touching(g, comp, 2); srcs = _adjacent_colours(g, comp)
        if rg and len(srcs) == 1:
            r0, c0, cr, cc = rg; out[cr][cc] = list(srcs)[0]
    return out
rule("two_sources_same_colour_no_conflict", "A lamp wired to two sources that happen to share one colour lights that colour, with no conflict.", gi_noconflict, tf_noconflict)


# ================================================================== 22
_KEYMIX = {(1, 2): 3, (1, 3): 2, (2, 3): 1, (1, 6): 7, (1, 7): 6, (6, 7): 1}
def gi_keymix(rng):
    h, w = _big(rng); g = blank(h, w)
    pair = rng.choice(list(_KEYMIX.keys()))
    r0, c0 = rng.randint(3, h - 6), rng.randint(3, w - 8)
    cen = _ring(g, r0, c0, 2)
    if _west_arm(g, r0, c0, pair[0], 2) is None: return None
    if _south_arm(g, r0, c0, pair[1], 2) is None: return None
    return g
def tf_keymix(g):
    out = copy(g)
    for comp in _grey_comp(g):
        rg = _ring_touching(g, comp, 2); srcs = tuple(sorted(_adjacent_colours(g, comp)))
        if rg:
            r0, c0, cr, cc = rg
            out[cr][cc] = _KEYMIX.get(srcs, WIRE)
    return out
rule("two_sources_key_mixed_colour", "A lamp wired to two different sources lights the fixed key-mix colour for that pair (1+2->3, 1+3->2, 2+3->1, 1+6->7, 1+7->6, 6+7->1), grey if the pair has no key.", gi_keymix, tf_keymix, digits=True)


# ================================================================== 23
def gi_nearer(rng):
    h, w = _big(rng); g = blank(h, w)
    length = rng.randint(8, w - 10); r = rng.randint(2, h - 3); cs = rng.randint(0, w - length - 6)
    _draw_h(g, r, cs + 1, length)
    c1, c2 = colours(rng, 2, exclude=(0, 2))
    third = max(1, length // 3)
    p_far = cs + 1 + rng.randint(0, third)
    p_near = cs + length - rng.randint(0, third)
    if p_near <= p_far: p_near = p_far + 1
    g[r - 1][p_far] = c1
    g[r - 1][p_near] = c2
    _ring(g, r - 1, cs + length + 1, 2)
    return g
def tf_nearer(g):
    out = copy(g)
    for comp in _grey_comp(g):
        rg = _ring_touching(g, comp, 2)
        if not rg: continue
        r0, c0, cr, cc = rg
        srcs = _adjacent_colours(g, comp)
        best, bd = None, 10 ** 9
        for col, cells_ in srcs.items():
            for r, c in cells_:
                d = abs(r - cr) + abs(c - cc)
                if d < bd: bd, best = d, col
        out[cr][cc] = best if best is not None else WIRE
    return out
rule("nearer_source_wins_on_shared_wire", "When one wire has a source cell at each end, the lamp lights the colour of whichever source is physically closer to it.", gi_nearer, tf_nearer)


# ---------- AND / OR lamps fed by multiple wires ----------
# ================================================================== 24
def gi_and2(rng):
    h, w = _big(rng); g = blank(h, w)
    r0, c0 = rng.randint(3, h - 6), rng.randint(3, w - 8)
    cen = _ring(g, r0, c0, 2)
    col = colours(rng, 1, exclude=(0, 2))[0]
    wa = _west_arm(g, r0, c0, col, 3); sa = _south_arm(g, r0, c0, col, 3)
    if wa is None or sa is None: return None
    if rng.random() < 0.6:
        br, bc = rng.choice(wa + sa); g[br][bc] = 0
    return g
def tf_and2(g):
    out = copy(g)
    for rc in components(g, 2, conn8=False):
        r0, c0, r1, c1 = bbox(rc)
        if r1 - r0 != 2 or c1 - c0 != 2 or len(rc) != 8: continue
        cen = (r0 + 1, c0 + 1)
        comps = [cp for cp in _grey_comp(g) if _comp_touch(rc, cp)]
        ok = len(comps) >= 2 and all(len(_adjacent_colours(g, cp)) == 1 for cp in comps)
        if ok:
            cols = {list(_adjacent_colours(g, cp))[0] for cp in comps}
            out[cen[0]][cen[1]] = list(cols)[0] if len(cols) == 1 else WIRE
        else:
            out[cen[0]][cen[1]] = WIRE
    return out
rule("and_lamp_needs_both_wires_intact", "A lamp fed by two wires lights only if BOTH are unbroken chains reaching it; either one broken leaves it dark.", gi_and2, tf_and2)


# ================================================================== 25
def gi_or2(rng):
    h, w = _big(rng); g = blank(h, w)
    r0, c0 = rng.randint(3, h - 6), rng.randint(3, w - 8)
    cen = _ring(g, r0, c0, 2)
    col = colours(rng, 1, exclude=(0, 2))[0]
    wa = _west_arm(g, r0, c0, col, 3); sa = _south_arm(g, r0, c0, col, 3)
    if wa is None or sa is None: return None
    if rng.random() < 0.6:
        br, bc = rng.choice(wa + sa); g[br][bc] = 0
    return g
def tf_or2(g):
    out = copy(g)
    for rc in components(g, 2, conn8=False):
        r0, c0, r1, c1 = bbox(rc)
        if r1 - r0 != 2 or c1 - c0 != 2 or len(rc) != 8: continue
        cen = (r0 + 1, c0 + 1)
        comps = [cp for cp in _grey_comp(g) if _comp_touch(rc, cp)]
        cols = set()
        for cp in comps:
            srcs = _adjacent_colours(g, cp)
            if len(srcs) == 1: cols.add(list(srcs)[0])
        out[cen[0]][cen[1]] = list(cols)[0] if len(cols) == 1 else (WIRE if cols else WIRE)
    return out
rule("or_lamp_needs_one_wire_intact", "A lamp fed by two same-colour wires lights that colour if AT LEAST ONE wire is an unbroken chain reaching it.", gi_or2, tf_or2)


# ================================================================== 26
def gi_and3(rng):
    h, w = _big(rng); g = blank(h, w)
    r0, c0 = rng.randint(4, h - 7), rng.randint(4, w - 10)
    cen = _ring(g, r0, c0, 2)
    col = colours(rng, 1, exclude=(0, 2))[0]
    wa = _west_arm(g, r0, c0, col, 3); sa = _south_arm(g, r0, c0, col, 3); ea = _east_arm(g, r0, c0, col, 3)
    if wa is None or sa is None or ea is None: return None
    if rng.random() < 0.7:
        br, bc = rng.choice(wa + sa + ea); g[br][bc] = 0
    return g
def tf_and3(g):
    out = copy(g)
    for rc in components(g, 2, conn8=False):
        r0, c0, r1, c1 = bbox(rc)
        if r1 - r0 != 2 or c1 - c0 != 2 or len(rc) != 8: continue
        cen = (r0 + 1, c0 + 1)
        comps = [cp for cp in _grey_comp(g) if _comp_touch(rc, cp)]
        ok = len(comps) >= 3 and all(len(_adjacent_colours(g, cp)) == 1 for cp in comps)
        if ok:
            cols = {list(_adjacent_colours(g, cp))[0] for cp in comps}
            out[cen[0]][cen[1]] = list(cols)[0] if len(cols) == 1 else WIRE
        else:
            out[cen[0]][cen[1]] = WIRE
    return out
rule("and_lamp_three_wires_all_required", "A lamp fed by three wires lights its colour only if ALL THREE reach it unbroken; any single break leaves it dark.", gi_and3, tf_and3)


# ---------- junctions / crossings ----------
# ================================================================== 27
def gi_cross(rng):
    h, w = _big(rng); g = blank(h, w)
    c1, c2 = colours(rng, 2, exclude=(0, 2))
    len1 = rng.randint(3, 6); r0 = rng.randint(0, h - len1 - 5)
    c = rng.randint(2, w - 3)
    g[r0][c] = c1; _draw_v(g, c, r0 + 1, len1)
    _ring(g, r0 + 1 + len1, c - 1, 2)
    len2 = rng.randint(3, 6); cs2 = rng.randint(0, w - len2 - 5)
    choices = [rr for rr in range(1, h - 1) if rr < r0 - 1 or rr > r0 + len1 + 3]
    if not choices: return None
    r1 = rng.choice(choices)
    g[r1][cs2] = c2; _draw_h(g, r1, cs2 + 1, len2)
    _ring(g, r1 - 1, cs2 + len2 + 1, 2)
    return g
def tf_cross(g):
    out = copy(g)
    for comp in _grey_comp(g):
        rg = _ring_touching(g, comp, 2); srcs = _adjacent_colours(g, comp)
        if rg and len(srcs) == 1:
            r0, c0, cr, cc = rg; out[cr][cc] = list(srcs)[0]
    return out
rule("crossing_wires_pass_independently", "Two unrelated wires, one vertical and one horizontal, each light their own lamp in their own source's colour, unaffected by the other.", gi_cross, tf_cross)


# ================================================================== 28
def gi_split2(rng):
    h, w = _big(rng); g = blank(h, w)
    r = rng.randint(2, h - 3); c = rng.randint(4, w - 10)
    col = colours(rng, 1, exclude=(0, 2))[0]
    g[r][c] = col; g[r][c + 1] = WIRE; g[r][c + 2] = WIRE
    g[r][c + 3] = WIRE
    _ring(g, r - 1, c + 4, 2)
    if r + 2 >= h: return None
    g[r + 1][c + 2] = WIRE
    _ring(g, r + 2, c + 1, 2)
    return g
def tf_split2(g):
    out = copy(g)
    for comp in _grey_comp(g):
        rg = _ring_touching(g, comp, 2); srcs = _adjacent_colours(g, comp)
        if rg and len(srcs) == 1:
            r0, c0, cr, cc = rg; out[cr][cc] = list(srcs)[0]
    return out
rule("junction_splits_to_two_lamps", "A wire that splits into two branches at a junction cell lights both branches' lamps in the single source's colour.", gi_split2, tf_split2)


# ================================================================== 29
def gi_split3(rng):
    h, w = _big(rng); g = blank(h, w)
    r = rng.randint(4, h - 5); c = rng.randint(4, w - 5)
    col = colours(rng, 1, exclude=(0, 2))[0]
    g[r][c - 2] = col; g[r][c - 1] = WIRE; g[r][c] = WIRE
    g[r - 1][c] = WIRE; g[r + 1][c] = WIRE; g[r][c + 1] = WIRE
    if not (r - 3 >= 0 and r + 3 < h and c + 3 < w): return None
    g[r - 2][c] = WIRE; _ring(g, r - 3, c - 1, 2)
    g[r + 2][c] = WIRE; _ring(g, r + 3, c - 1, 2)
    g[r][c + 2] = WIRE; _ring(g, r - 1, c + 3, 2)
    return g
def tf_split3(g):
    out = copy(g)
    for comp in _grey_comp(g):
        rg = _ring_touching(g, comp, 2); srcs = _adjacent_colours(g, comp)
        if rg and len(srcs) == 1:
            r0, c0, cr, cc = rg; out[cr][cc] = list(srcs)[0]
    return out
rule("junction_distributes_to_three_lamps", "A single wire that branches three ways at a junction lights all three lamps it reaches in the one source's colour.", gi_split3, tf_split3)


# ---------- longest / shortest wire wins ----------
# ================================================================== 30
def gi_longest(rng):
    h, w = _big(rng); g = blank(h, w); k = 3
    rows = rng.sample(range(1, h - 1), k)
    lengths = rng.sample(range(3, w // 2), k)
    while lengths[0] == max(lengths) or len(set(lengths)) < k:
        lengths = rng.sample(range(3, w // 2), k)
    for r, length in zip(rows, lengths):
        cs = rng.randint(0, w - length - 6)
        col = colours(rng, 1, exclude=(0, 2))[0]
        g[r][cs] = col; _draw_h(g, r, cs + 1, length); _ring(g, r - 1, cs + length + 1, 2)
    return g
def tf_longest(g):
    out = copy(g); comps = _grey_comp(g)
    best = max(comps, key=len) if comps else None
    for comp in comps:
        rg = _ring_touching(g, comp, 2)
        if not rg: continue
        r0, c0, cr, cc = rg
        if comp is best:
            srcs = _adjacent_colours(g, comp)
            out[cr][cc] = list(srcs)[0] if len(srcs) == 1 else WIRE
        else:
            out[cr][cc] = WIRE
    return out
rule("longest_wire_lamp_lights_rest_dark", "Among several wire-and-lamp pairs, only the lamp on the longest wire (most grey cells) lights up; the rest stay grey.", gi_longest, tf_longest)


# ================================================================== 31
def gi_shortest(rng):
    h, w = _big(rng); g = blank(h, w); k = 3
    rows = rng.sample(range(1, h - 1), k)
    lengths = rng.sample(range(3, w // 2), k)
    while len(set(lengths)) < k:
        lengths = rng.sample(range(3, w // 2), k)
    for r, length in zip(rows, lengths):
        cs = rng.randint(0, w - length - 6)
        col = colours(rng, 1, exclude=(0, 2))[0]
        g[r][cs] = col; _draw_h(g, r, cs + 1, length); _ring(g, r - 1, cs + length + 1, 2)
    return g
def tf_shortest(g):
    out = copy(g); comps = _grey_comp(g)
    best = min(comps, key=len) if comps else None
    for comp in comps:
        rg = _ring_touching(g, comp, 2)
        if not rg: continue
        r0, c0, cr, cc = rg
        if comp is best:
            srcs = _adjacent_colours(g, comp)
            out[cr][cc] = list(srcs)[0] if len(srcs) == 1 else WIRE
        else:
            out[cr][cc] = WIRE
    return out
rule("shortest_wire_lamp_lights_rest_dark", "Among several wire-and-lamp pairs, only the lamp on the shortest wire (fewest grey cells) lights up; the rest stay grey.", gi_shortest, tf_shortest)


# ---------- counting ----------
# ================================================================== 32
def gi_countin(rng):
    h, w = _big(rng); g = blank(h, w)
    r0, c0 = rng.randint(4, h - 7), rng.randint(4, w - 10)
    n = rng.randint(1, 3)
    fns = [_west_arm, _south_arm, _east_arm]; rng.shuffle(fns)
    cen = _ring(g, r0, c0, 2)
    for fn in fns[:n]:
        col = colours(rng, 1, exclude=(0, 2))[0]
        if fn(g, r0, c0, col, 3) is None: return None
    return g
def tf_countin(g):
    out = copy(g)
    for rc in components(g, 2, conn8=False):
        r0, c0, r1, c1 = bbox(rc)
        if r1 - r0 != 2 or c1 - c0 != 2 or len(rc) != 8: continue
        cen = (r0 + 1, c0 + 1)
        n = sum(1 for cp in _grey_comp(g) if _comp_touch(rc, cp))
        out[cen[0]][cen[1]] = n
    return out
rule("lamp_digit_counts_incoming_wires", "A ring lamp's centre is painted with the DIGIT equal to the number of separate wires touching it (colour value = count).", gi_countin, tf_countin, digits=True)


# ================================================================== 33
def gi_countlen(rng):
    h, w = _big(rng); g = blank(h, w)
    length = rng.randint(1, 8); r = rng.randint(1, h - 2); cs = rng.randint(0, w - 12)
    col = colours(rng, 1, exclude=(0, 2))[0]
    g[r][cs] = col; _draw_h(g, r, cs + 1, length); _ring(g, r - 1, cs + length + 1, 2)
    return g
def tf_countlen(g):
    out = copy(g)
    for comp in _grey_comp(g):
        rg = _ring_touching(g, comp, 2)
        if rg:
            r0, c0, cr, cc = rg
            out[cr][cc] = min(len(comp), 9)
    return out
rule("lamp_digit_counts_wire_length", "A ring lamp's centre is painted with the DIGIT equal to the wire's length in cells, capped at 9.", gi_countlen, tf_countlen, digits=True)


# ================================================================== 34
def gi_nolamp(rng):
    h, w = _big(rng); g = blank(h, w)
    length = rng.randint(4, w - 4); r = rng.randint(0, h - 1); cs = rng.randint(0, w - length - 2)
    col = colours(rng, 1, exclude=(0,))[0]
    g[r][cs] = col; _draw_h(g, r, cs + 1, length)
    return g
def tf_nolamp(g):
    out = copy(g)
    for comp in _grey_comp(g):
        srcs = _adjacent_colours(g, comp)
        if len(srcs) == 1:
            for r, c in comp: out[r][c] = list(srcs)[0]
    return out
# wire_recolours_no_lamp_present dropped 2026-10-12 (review 2: behavioural duplicate of wire_path_recolours_to_source)
# ================================================================== 35
def gi_nocross(rng):
    h, w = _big(rng); g = blank(h, w); k = 2
    rows = rng.sample(range(0, h), k)
    cols_used = []
    for r in rows:
        length = rng.randint(3, w - 4); cs = rng.randint(0, w - length - 2)
        col = colours(rng, 1, exclude=(0,))[0]
        g[r][cs] = col; _draw_h(g, r, cs + 1, length)
        cols_used.append(col)
    return g if cols_used[0] != cols_used[1] else None
def tf_nocross(g):
    out = copy(g)
    for comp in _grey_comp(g):
        srcs = _adjacent_colours(g, comp)
        if len(srcs) == 1:
            for r, c in comp: out[r][c] = list(srcs)[0]
    return out
# two_independent_wires_no_crosstalk dropped 2026-10-12 (review 2: behavioural duplicate of wire_path_recolours_to_source)
# ================================================================== 36
def gi_gatepartial(rng):
    h, w = _big(rng); g = blank(h, w)
    length = rng.randint(8, w - 8); r = rng.randint(1, h - 2); cs = rng.randint(0, w - length - 4)
    col = colours(rng, 1, exclude=(0, 4, 8))[0]
    gate_at = cs + 1 + length // 2
    g[r][cs] = col; _draw_h(g, r, cs + 1, length)
    g[r][gate_at] = 4
    return g
def tf_gatepartial(g):
    out = copy(g); h, w = dims(g)
    for r in range(h):
        c = 0
        while c < w:
            if g[r][c] not in (0, WIRE, 4):
                col = g[r][c]; cc = c + 1
                while cc < w and g[r][cc] == WIRE:
                    out[r][cc] = col; cc += 1
                if cc < w and g[r][cc] == 4:
                    break
            c += 1
    return out
rule("gate_pass_partial_recolour_to_gate", "A wire recolours to its source's colour only up to the first colour-4 gate it meets; the wire past the gate stays grey.", gi_gatepartial, tf_gatepartial, digits=True)


# ================================================================== 37
def gi_ringblock(rng):
    h, w = _big(rng); g = blank(h, w)
    r = rng.randint(4, h - 5); c = rng.randint(4, w - 12)
    if r - 3 < 0 or r + 3 >= h or c + 4 >= w: return None
    col = colours(rng, 1, exclude=(0, 2))[0]
    g[r][c] = col; g[r][c + 1] = WIRE; g[r][c + 2] = WIRE
    g[r - 1][c + 2] = WIRE; g[r - 2][c + 2] = WIRE; _ring(g, r - 3, c + 1, 2)
    g[r + 1][c + 2] = WIRE
    rect(g, r + 1, c + 2, r + 3, c + 4, WIRE, fill=True)
    return g
def tf_ringblock(g):
    out = copy(g)
    for comp in _grey_comp(g):
        srcs = _adjacent_colours(g, comp)
        rg = _ring_touching(g, comp, 2)
        blk = _block_cells(g, comp)
        if len(srcs) != 1: continue
        col = list(srcs)[0]
        if rg:
            r0, c0, cr, cc = rg; out[cr][cc] = col
        for r, c in blk: out[r][c] = col
    return out
rule("ring_and_block_lamp_same_source", "One source feeds a wire that branches to both a ring lamp and a grey block lamp; both light in the source's colour.", gi_ringblock, tf_ringblock)


# ================================================================== 38
def gi_fargate(rng):
    h, w = _big(rng); g = blank(h, w)
    length = rng.randint(10, w - 8); r = rng.randint(1, h - 2); cs = rng.randint(0, w - length - 6)
    col = colours(rng, 1, exclude=(0, 2))[0]
    g[r][cs] = col; _draw_h(g, r, cs + 1, length)
    gap = cs + length - 1   # gap right next to the lamp end
    g[r][gap] = 0
    _ring(g, r - 1, cs + length + 1, 2)
    return g
def tf_fargate(g):
    out = copy(g)
    for comp in _grey_comp(g):
        rg = _ring_touching(g, comp, 2); srcs = _adjacent_colours(g, comp)
        if rg:
            r0, c0, cr, cc = rg
            out[cr][cc] = list(srcs)[0] if len(srcs) == 1 else WIRE
    return out
rule("closer_gap_still_blocks_far_source", "A gap one cell from the lamp still fully blocks a source many cells away; proximity to the lamp does not matter.", gi_fargate, tf_fargate)


# ================================================================== 39
def gi_swdefault(rng):
    h, w = _big(rng); g = blank(h, w)
    length = rng.randint(6, w - 10); r = rng.randint(1, h - 2); cs = rng.randint(0, w - length - 6)
    col = colours(rng, 1, exclude=(0, 2, 6, 7))[0]
    has_switch = rng.random() < 0.5
    g[r][cs] = col; _draw_h(g, r, cs + 1, length)
    if has_switch:
        g[r][cs + 1 + length // 2] = 6
    _ring(g, r - 1, cs + length + 1, 2)
    return g
def tf_swdefault(g):
    out = copy(g)
    for comp in _multi_comp(g, {WIRE, 6}):
        rg = _ring_touching(g, comp, 2); srcs = _adjacent_colours(g, comp, exclude=(0, WIRE, 2, 6))
        if rg and len(srcs) == 1:
            r0, c0, cr, cc = rg; out[cr][cc] = list(srcs)[0]
    return out
rule("switch_missing_defaults_to_on", "A wire with no switch cell at all behaves as if always on and lights its lamp normally; a colour-6 switch, if present, also lets it through.", gi_swdefault, tf_swdefault)


# ================================================================== 40
def gi_multigap(rng):
    h, w = _big(rng); g = blank(h, w); k = rng.randint(2, 3)
    rows = rng.sample(range(1, h - 1), k)
    for r in rows:
        length = rng.randint(6, w // 2); cs = rng.randint(0, w - length - 6)
        col = colours(rng, 1, exclude=(0, 2, 9))[0]
        g[r][cs] = col; _draw_h(g, r, cs + 1, length)
        g[r][cs + 1 + length // 2] = 0
        _ring(g, r - 1, cs + length + 1, 2)
    return g
def tf_multigap(g):
    out = copy(g)
    for comp in _grey_comp(g):
        rg = _ring_touching(g, comp, 2)
        if rg:
            r0, c0, cr, cc = rg; out[cr][cc] = WIRE
    h, w = dims(g)
    for r in range(h):
        for c in range(1, w - 1):
            if g[r][c] == 0 and g[r][c - 1] == WIRE and g[r][c + 1] == WIRE:
                out[r][c] = 9
    return out
rule("multiple_gaps_each_marked", "Every one-cell gap on every wire is painted 9 to mark the break, and every lamp whose wire has a gap stays grey.", gi_multigap, tf_multigap)
