# b019_automata.py -- local cellular rules, one or more exact deterministic steps: Life variants, morphology
# (erode / dilate / open / close / outline), contagion, sand, rock-paper-scissors, Ising-style relaxation,
# thinning, corner marking, neighbour counts, 1-D elementary automata, traffic, sandpile toppling.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
N4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
DG = [(-1, -1), (-1, 1), (1, -1), (1, 1)]


def _sz(rng, lo=6, hi=16):
    """A third of inputs land in the 21-30 band."""
    if rng.random() < 0.35:
        return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _nbs(g, r, c, offs):
    H, W = dims(g)
    return [g[r + dr][c + dc] for dr, dc in offs if 0 <= r + dr < H and 0 <= c + dc < W]


def _noise(rng, cols, p, lo=6, hi=16):
    h, w = _sz(rng, lo, hi)
    g = [[rng.choice(cols) if rng.random() < p else 0 for _ in range(w)] for _ in range(h)]
    return g if any(v for row in g for v in row) else None


def _rects(rng, cols, density=0.08, lo=6, hi=16, side=(2, 6)):
    """Filled rectangles stamped over an empty grid, overlapping allowed."""
    h, w = _sz(rng, lo, hi); g = blank(h, w)
    for _ in range(max(2, int(h * w * density / 8))):
        rh, rw = rng.randint(side[0], min(side[1], h)), rng.randint(side[0], min(side[1], w))
        r0, c0 = rng.randint(0, h - rh), rng.randint(0, w - rw)
        rect(g, r0, c0, r0 + rh - 1, c0 + rw - 1, rng.choice(cols))
    return g


def _regions(rng, cols, lo=6, hi=16):
    """A grid with no empty cells: a base colour with rectangular patches of other colours."""
    h, w = _sz(rng, lo, hi); g = blank(h, w, rng.choice(cols))
    for _ in range(max(3, h * w // 40)):
        rh, rw = rng.randint(2, max(2, h // 2)), rng.randint(2, max(2, w // 2))
        r0, c0 = rng.randint(0, h - rh), rng.randint(0, w - rw)
        rect(g, r0, c0, r0 + rh - 1, c0 + rw - 1, rng.choice(cols))
    return g


def _shapes(rng, cols, n_lo=3, n_hi=8, lo=6, hi=16, margin=1, per_cells=30):
    """Random blobs placed apart; keeps whatever fitted."""
    h, w = _sz(rng, lo, hi); g = blank(h, w)
    k = max(2, h * w // per_cells)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    place_shapes(rng, g, shapes, [rng.choice(cols) for _ in shapes], margin=margin)
    return g if any(v for row in g for v in row) else None


def _punch(rng, g, frac):
    """Erase a fraction of the coloured cells (holes and notches)."""
    cs = cells(g, lambda v: v != 0)
    for r, c in rng.sample(cs, int(len(cs) * frac)):
        g[r][c] = 0
    return g


def _alive(g):
    vs = {v for row in g for v in row if v}
    return vs.pop() if len(vs) == 1 else None


def _life(g, alive, born=(3,), survive=(2, 3)):
    H, W = dims(g); out = blank(H, W)
    for r in range(H):
        for c in range(W):
            n = sum(1 for v in _nbs(g, r, c, N8) if v)
            if (g[r][c] and n in survive) or (not g[r][c] and n in born):
                out[r][c] = alive
    return out


def _erode4(g):
    H, W = dims(g); out = blank(H, W)
    for r in range(H):
        for c in range(W):
            if g[r][c] and all(0 <= r + dr < H and 0 <= c + dc < W and g[r + dr][c + dc] for dr, dc in N4):
                out[r][c] = g[r][c]
    return out


def _dilate4(g):
    H, W = dims(g); out = copy(g)
    for r in range(H):
        for c in range(W):
            if not g[r][c]:
                nb = [v for v in _nbs(g, r, c, N4) if v]
                if nb: out[r][c] = min(nb)
    return out


# 1 Conway Life, one step.
def gi_life(rng):
    return _noise(rng, [rng.choice(COLOURS)], rng.uniform(0.3, 0.45))
def tf_life(g):
    a = _alive(g)
    return _life(g, a) if a else None
rule("life_one_step", "One step of Conway's Life: a coloured cell survives with two or three coloured neighbours (eight directions), an empty cell is born with exactly three; everything else empties.", gi_life, tf_life)


# 2 Conway Life, two steps.
def tf_life2(g):
    a = _alive(g)
    return _life(_life(g, a), a) if a else None
rule("life_two_steps", "Two steps of Conway's Life (survive on two or three neighbours, birth on exactly three, eight directions) applied one after the other.", gi_life, tf_life2)


# 3 HighLife (birth on 3 or 6).
def tf_highlife(g):
    a = _alive(g)
    return _life(g, a, born=(3, 6)) if a else None
rule("highlife_one_step", "One Life step where an empty cell is born with three or six coloured neighbours and a coloured cell survives with two or three (eight directions).", gi_life, tf_highlife)


# 4 Seeds (B2/S): every live cell dies, birth on exactly two.
def gi_seeds(rng):
    return _noise(rng, [rng.choice(COLOURS)], rng.uniform(0.15, 0.3))
def tf_seeds(g):
    a = _alive(g)
    return _life(g, a, born=(2,), survive=()) if a else None
rule("seeds_rule_one_step", "One step of the Seeds automaton: every coloured cell empties, and an empty cell with exactly two coloured neighbours (eight directions) becomes coloured.", gi_seeds, tf_seeds)


# 5 Life without death.
def gi_lwd(rng):
    return _noise(rng, [rng.choice(COLOURS)], rng.uniform(0.2, 0.35))
def tf_lwd(g):
    a = _alive(g)
    return _life(g, a, born=(3,), survive=tuple(range(9))) if a else None
rule("life_without_death_one_step", "One step of Life without death: coloured cells always stay, and an empty cell with exactly three coloured neighbours (eight directions) becomes coloured.", gi_lwd, tf_lwd)


# 6 Immigration Life: two live colours; a born cell takes the majority colour of its three parents.
def gi_immig(rng):
    return _noise(rng, colours(rng, 2), rng.uniform(0.3, 0.45))
def tf_immig(g):
    H, W = dims(g); out = blank(H, W)
    for r in range(H):
        for c in range(W):
            live = [v for v in _nbs(g, r, c, N8) if v]
            if g[r][c] and len(live) in (2, 3):
                out[r][c] = g[r][c]
            elif not g[r][c] and len(live) == 3:
                out[r][c] = max(set(live), key=live.count)
    return out
rule("immigration_life_one_step", "One Life step with two live colours: a cell survives on two or three live neighbours keeping its colour, and a cell born from exactly three takes the colour two or more of those three share.", gi_immig, tf_immig)


# 7 Brian's Brain: on (3) -> dying (7) -> off; off with exactly two on neighbours turns on.
def gi_brain(rng):
    h, w = _sz(rng); g = blank(h, w)
    for r in range(h):
        for c in range(w):
            x = rng.random(); g[r][c] = 3 if x < 0.3 else 7 if x < 0.4 else 0
    return g if any(v == 3 for row in g for v in row) else None
def tf_brain(g):
    H, W = dims(g); out = blank(H, W)
    for r in range(H):
        for c in range(W):
            if g[r][c] == 3: out[r][c] = 7
            elif g[r][c] == 7: out[r][c] = 0
            elif sum(1 for v in _nbs(g, r, c, N8) if v == 3) == 2: out[r][c] = 3
    return out
rule("brians_brain_one_step", "One step of Brian's Brain: every 3 cell becomes 7, every 7 cell empties, and an empty cell with exactly two 3-neighbours (eight directions) becomes 3.", gi_brain, tf_brain)


# 8 majority smoothing over the 3x3 window.
def gi_major(rng):
    g = _rects(rng, colours(rng, rng.randint(2, 3)), density=0.14, side=(3, 8))
    H, W = dims(g)
    for _ in range(H * W // 7):
        g[rng.randrange(H)][rng.randrange(W)] = rng.choice([0] + COLOURS)
    return g
def tf_major(g):
    H, W = dims(g); out = copy(g)
    for r in range(H):
        for c in range(W):
            win = _nbs(g, r, c, N8) + [g[r][c]]; cnt = {v: win.count(v) for v in set(win)}
            top = max(cnt.values()); best = [v for v in cnt if cnt[v] == top]
            if len(best) == 1: out[r][c] = best[0]
    return out
rule("majority_smoothing_3x3", "One smoothing step: every cell takes the value that occurs most often in its 3 by 3 window (itself included, empty counts as a value); a tie leaves the cell unchanged.", gi_major, tf_major)


# 9 erosion, plus kernel.
def gi_erode(rng):
    return _rects(rng, colours(rng, rng.randint(1, 3)), density=0.12, side=(3, 8))
# erode_plus_kernel dropped 2026-10-12 (trio review: behavioural duplicate or one global operation)
# 10 erosion, square kernel.
def tf_erode8(g):
    H, W = dims(g); out = blank(H, W)
    for r in range(H):
        for c in range(W):
            if g[r][c] and all(0 <= r + dr < H and 0 <= c + dc < W and g[r + dr][c + dc] for dr, dc in N8):
                out[r][c] = g[r][c]
    return out
rule("erode_square_kernel", "One erosion step: a coloured cell stays only if all eight neighbours are coloured (grid edge counts as empty); every other coloured cell empties.", gi_erode, tf_erode8)


# 11 dilation into diagonal neighbours only.
def gi_dildiag(rng):
    return _shapes(rng, colours(rng, rng.randint(1, 3)), 2, 6, margin=2, per_cells=45)
def tf_dildiag(g):
    H, W = dims(g); out = copy(g)
    for r in range(H):
        for c in range(W):
            if not g[r][c]:
                nb = [v for v in _nbs(g, r, c, DG) if v]
                if nb: out[r][c] = min(set(nb), key=lambda v: (-nb.count(v), v))
    return out
rule("dilate_diagonal_kernel", "One dilation step along diagonals only: every empty cell with a coloured diagonal neighbour takes the most frequent colour among its diagonal neighbours, the lowest colour number on a tie.", gi_dildiag, tf_dildiag)


# 12 closing: dilate then erode (plus kernel).
def gi_close(rng):
    return _punch(rng, _rects(rng, [rng.choice(COLOURS)], density=0.12, side=(3, 8)), 0.1)
def tf_close(g):
    return _erode4(_dilate4(g))
rule("close_plus_kernel", "Two steps: first every empty cell with a coloured side-neighbour takes that colour, then every coloured cell lacking one of its four coloured side-neighbours (grid edge counts as empty) empties; small holes and notches are filled.", gi_close, tf_close)


# 13 opening: erode then dilate (plus kernel).
def gi_open(rng):
    g = _rects(rng, [rng.choice(COLOURS)], density=0.1, side=(3, 7)); H, W = dims(g); col = max(v for row in g for v in row)
    sprinkle(rng, g, H * W // 20, col)
    for _ in range(rng.randint(1, 3)):
        r, c0 = rng.randrange(H), rng.randrange(W); L = rng.randint(3, 8)
        for c in range(c0, min(W, c0 + L)): g[r][c] = col
    return g
def tf_open(g):
    return _dilate4(_erode4(g))
rule("open_plus_kernel", "Two steps: first every coloured cell lacking one of its four coloured side-neighbours (grid edge counts as empty) empties, then every empty cell beside a surviving coloured cell takes its colour; lone cells and one-cell-thin lines vanish.", gi_open, tf_open)


# 14 outline where touching colours count as filled.
def gi_outline(rng):
    return _rects(rng, colours(rng, rng.randint(2, 4)), density=0.2, side=(3, 9))
def tf_outline(g):
    H, W = dims(g); out = copy(g)
    for r in range(H):
        for c in range(W):
            if g[r][c] and all(0 <= r + dr < H and 0 <= c + dc < W and g[r + dr][c + dc] for dr, dc in N4):
                out[r][c] = 0
    return out
rule("outline_multicolour_touching", "Every coloured cell with no empty side-neighbour is erased, even when its neighbours are other colours, so touching blocks of different colours leave one joint outline against the empty background.", gi_outline, tf_outline)


# 15 dilate only into cells with two or more coloured neighbours.
def gi_dil2(rng):
    return _shapes(rng, [rng.choice(COLOURS)], 2, 7, margin=1, per_cells=35)
def tf_dil2(g):
    a = _alive(g)
    if not a: return None
    H, W = dims(g); out = copy(g)
    for r in range(H):
        for c in range(W):
            if not g[r][c] and sum(1 for v in _nbs(g, r, c, N8) if v) >= 2: out[r][c] = a
    return out
rule("dilate_into_two_plus_neighbours", "One step: an empty cell becomes coloured only if at least two of its eight neighbours are coloured; coloured cells stay.", gi_dil2, tf_dil2)


# 16 cells with exactly two coloured neighbours swap between the two colours.
def gi_flip2(rng):
    return _noise(rng, colours(rng, 2), rng.uniform(0.35, 0.5))
def tf_flip2(g):
    vs = sorted({v for row in g for v in row if v})
    if len(vs) != 2: return None
    a, b = vs; H, W = dims(g); out = copy(g)
    for r in range(H):
        for c in range(W):
            if g[r][c] and sum(1 for v in _nbs(g, r, c, N8) if v) == 2: out[r][c] = b if g[r][c] == a else a
    return out
rule("flip_colour_on_exactly_two_neighbours", "One step on a two-colour grid: every coloured cell with exactly two coloured neighbours (eight directions) switches to the other colour; all other cells stay.", gi_flip2, tf_flip2)


# 17 grow objects one ring at a time until the first contact.
def gi_grow(rng):
    return _shapes(rng, colours(rng, rng.randint(2, 4)), 1, 5, margin=rng.randint(1, 3), per_cells=60)
def tf_grow(g):
    H, W = dims(g); obs = objects(g, 0, conn8=True)
    if len(obs) < 2: return None
    lab = {cell: i for i, o in enumerate(obs) for cell in o}; col = [g[o[0][0]][o[0][1]] for o in obs]
    for _ in range(60):
        new = {}
        for (r, c), i in list(lab.items()):
            for dr, dc in N4:
                p = (r + dr, c + dc)
                if 0 <= p[0] < H and 0 <= p[1] < W and p not in lab: new.setdefault(p, set()).add(i)
        if not new: return None
        touched = any(len(s) > 1 for s in new.values())
        for p, s in new.items(): lab[p] = min(s)
        touched = touched or any(lab.get((r + dr, c + dc), i) != i for (r, c), i in new.items() for dr, dc in N4)
        if touched: break
    out = blank(H, W)
    for (r, c), i in lab.items(): out[r][c] = col[i]
    return out
rule("grow_objects_until_first_touch", "Every object grows one cell on all four sides per step, all at once, and growth stops after the first step in which two objects touch; a cell reached by two objects at once goes to the one earlier in reading order.", gi_grow, tf_grow)


# 18 infection: colour 2 spreads into colour 1 for exactly two steps.
def gi_infect(rng):
    g = _rects(rng, [1], density=0.2, side=(3, 9)); ones = cells(g, lambda v: v == 1)
    if len(ones) < 6: return None
    for r, c in rng.sample(ones, rng.randint(1, max(1, len(ones) // 40))): g[r][c] = 2
    return g
def _infect(g, steps):
    H, W = dims(g)
    for _ in range(steps):
        out = copy(g)
        for r in range(H):
            for c in range(W):
                if g[r][c] == 1 and any(v == 2 for v in _nbs(g, r, c, N4)): out[r][c] = 2
        g = out
    return g
def tf_infect2(g):
    return _infect(g, 2) if any(v == 2 for row in g for v in row) else None
rule("infection_spreads_two_steps", "Colour 2 infects colour 1 for exactly two steps: in each step every 1 cell sharing a side with a 2 cell becomes 2; empty cells block the spread.", gi_infect, tf_infect2)


# 19/20 forest fire: trees 3, fire 2, ash 5.
def gi_fire(rng):
    g = _noise(rng, [3], rng.uniform(0.6, 0.8))
    if g is None: return None
    trees = cells(g, lambda v: v == 3)
    for r, c in rng.sample(trees, min(len(trees), rng.randint(1, 4))): g[r][c] = 2
    return g
def _burn(g, steps):
    H, W = dims(g)
    for _ in range(steps):
        out = copy(g)
        for r in range(H):
            for c in range(W):
                if g[r][c] == 2: out[r][c] = 5
                elif g[r][c] == 3 and any(v == 2 for v in _nbs(g, r, c, N4)): out[r][c] = 2
        g = out
    return g
def tf_fire1(g):
    return _burn(g, 1) if any(v == 2 for row in g for v in row) else None
def tf_fire3(g):
    return _burn(g, 3) if any(v == 2 for row in g for v in row) else None
rule("forest_fire_one_step", "One step of a forest fire: every burning cell (2) becomes ash (5) and every tree (3) sharing a side with a burning cell catches fire (2).", gi_fire, tf_fire1)
rule("forest_fire_three_steps", "Three steps of a forest fire, each turning burning cells (2) to ash (5) and setting trees (3) beside a burning cell on fire (2).", gi_fire, tf_fire3)


# 21/22 sand: falls, slides down-left then down-right; grey (5) walls fixed.
def gi_sand(rng):
    h, w = _sz(rng, 7, 16); g = blank(h, w); s = rng.choice([c for c in COLOURS if c != 5])
    for _ in range(rng.randint(1, 3)):
        r, c0 = rng.randint(h // 2, h - 2), rng.randrange(w); L = rng.randint(2, max(2, w // 2))
        for c in range(c0, min(w, c0 + L)): g[r][c] = 5
    for r in range(h):
        for c in range(w):
            if g[r][c] == 0 and rng.random() < (0.35 if r < h * 0.6 else 0.1): g[r][c] = s
    return g
def _sweep(g, s):
    H, W = dims(g); moved = False
    for r in range(H - 2, -1, -1):
        for c in range(W):
            if g[r][c] != s: continue
            for dc in (0, -1, 1):
                if 0 <= c + dc < W and g[r + 1][c + dc] == 0:
                    g[r + 1][c + dc] = s; g[r][c] = 0; moved = True; break
    return moved
def _sandcol(g):
    vs = {v for row in g for v in row if v and v != 5}
    return vs.pop() if len(vs) == 1 else None
def tf_sand_settle(g):
    s = _sandcol(g)
    if not s: return None
    out = copy(g); n = 0
    while _sweep(out, s) and n < 300: n += 1
    return out
def tf_sand_step(g):
    s = _sandcol(g)
    if not s: return None
    out = copy(g); _sweep(out, s); return out
rule("sand_settles_fully", "Sand (the non-grey colour) falls until nothing moves: scanning bottom row upward and left to right, a grain moves down if that cell is empty, else down-left, else down-right; grey cells are fixed walls.", gi_sand, tf_sand_settle)
rule("sand_falls_one_step", "One sand step, scanning bottom row upward and left to right: each grain moves one cell down if empty, otherwise down-left, otherwise down-right, or stays; grey cells are fixed walls.", gi_sand, tf_sand_step)


# 23 rock-paper-scissors: 2 beats 1, 3 beats 2, 1 beats 3.
def gi_rps(rng):
    return _regions(rng, [1, 2, 3])
def tf_rps(g):
    H, W = dims(g); out = copy(g); beats = {1: 2, 2: 3, 3: 1}
    for r in range(H):
        for c in range(W):
            if beats[g[r][c]] in _nbs(g, r, c, N4): out[r][c] = beats[g[r][c]]
    return out
rule("rock_paper_scissors_one_step", "One step on a grid of colours 1, 2 and 3 where 2 beats 1, 3 beats 2 and 1 beats 3: every cell with a side-neighbour of the colour that beats it takes that colour.", gi_rps, tf_rps, digits=True)


# 24 Ising-like relaxation on the even checkerboard cells.
def gi_ising(rng):
    g = _regions(rng, colours(rng, 2)); H, W = dims(g); vs = sorted({v for row in g for v in row})
    if len(vs) != 2: return None
    a, b = vs
    for _ in range(H * W // 6):
        r, c = rng.randrange(H), rng.randrange(W); g[r][c] = a if g[r][c] == b else b
    return g
def tf_ising(g):
    H, W = dims(g); out = copy(g)
    for r in range(H):
        for c in range(W):
            if (r + c) % 2: continue
            nb = _nbs(g, r, c, N4); cnt = {v: nb.count(v) for v in set(nb)}; top = max(cnt.values())
            best = [v for v in cnt if cnt[v] == top]
            if len(best) == 1: out[r][c] = best[0]
    return out
rule("ising_relax_even_cells_one_step", "One relaxation step on a two-colour grid: every cell whose row plus column is even takes the colour held by most of its side-neighbours, staying put on a tie; odd cells do not change.", gi_ising, tf_ising)


# 25 thinning thick bars to one-cell centrelines.
def gi_thin(rng):
    h, w = _sz(rng, 8, 16); g = blank(h, w); k = max(2, h * w // 50); shapes = []
    for _ in range(k):
        t, L = rng.randint(2, 3), rng.randint(4, max(4, min(h, w) - 2))
        shapes.append([(r, c) for r in range(t) for c in range(L)] if rng.random() < 0.5 else [(r, c) for r in range(L) for c in range(t)])
    place_shapes(rng, g, shapes, [rng.choice(COLOURS) for _ in shapes], margin=1)
    return g if any(v for row in g for v in row) else None
def tf_thin(g):
    H, W = dims(g); out = blank(H, W)
    def run(r, c, dr, dc):
        n = 0; v = g[r][c]
        while 0 <= r + dr < H and 0 <= c + dc < W and g[r + dr][c + dc] == v: n += 1; r += dr; c += dc
        return n
    for r in range(H):
        for c in range(W):
            if not g[r][c]: continue
            u, d, l, rt = run(r, c, -1, 0), run(r, c, 1, 0), run(r, c, 0, -1), run(r, c, 0, 1)
            keep = (u == d or u == d + 1) if l + rt >= u + d else (l == rt or l == rt + 1)
            if keep: out[r][c] = g[r][c]
    return out
rule("thin_bars_to_centrelines", "Each thick bar is thinned in one pass to a one-cell line: a cell survives only if it sits in the middle of the bar's thickness, taking the lower or right-hand of the two middle cells when the thickness is even.", gi_thin, tf_thin)


# 26 outer corners of blocks marked grey.
def gi_corners(rng):
    h, w = _sz(rng, 7, 16); g = blank(h, w); k = max(2, h * w // 45)
    shapes = [[(r, c) for r in range(rng.randint(2, 6)) for c in range(rng.randint(2, 6))] for _ in range(k)]
    place_shapes(rng, g, shapes, [rng.choice([c for c in COLOURS if c != 5]) for _ in shapes], margin=1)
    return g if any(v for row in g for v in row) else None
def tf_corners(g):
    H, W = dims(g); out = copy(g)
    for r in range(H):
        for c in range(W):
            if not g[r][c]: continue
            vert = sum(1 for dr in (-1, 1) if 0 <= r + dr < H and g[r + dr][c])
            horz = sum(1 for dc in (-1, 1) if 0 <= c + dc < W and g[r][c + dc])
            if vert == 1 and horz == 1: out[r][c] = 5
    return out
rule("mark_block_corners_grey", "Every coloured cell with exactly one coloured neighbour above or below and exactly one to the left or right (an outer corner of a block) is recoloured grey (5).", gi_corners, tf_corners)


# 27 cells become their count of same-colour 8-neighbours.
def gi_count8(rng):
    return _noise(rng, colours(rng, rng.randint(2, 3)), rng.uniform(0.45, 0.6))
def tf_count8(g):
    H, W = dims(g); out = blank(H, W)
    for r in range(H):
        for c in range(W):
            if g[r][c]: out[r][c] = sum(1 for v in _nbs(g, r, c, N8) if v == g[r][c])
    return out
rule("cells_count_same_colour_8_neighbours", "Every coloured cell is replaced by the number of its eight neighbours that share its colour; a cell with none becomes empty.", gi_count8, tf_count8, digits=True)


# 28 cells become their count of empty side-neighbours.
def gi_count_empty(rng):
    return _rects(rng, colours(rng, rng.randint(1, 3)), density=0.14, side=(2, 7))
def tf_count_empty(g):
    H, W = dims(g); out = blank(H, W)
    for r in range(H):
        for c in range(W):
            if g[r][c]: out[r][c] = sum(1 for dr, dc in N4 if not (0 <= r + dr < H and 0 <= c + dc < W) or not g[r + dr][c + dc])
    return out
rule("cells_count_empty_side_neighbours", "Every coloured cell is replaced by the number of its four side-neighbours that are empty or off the grid; fully enclosed cells become empty.", gi_count_empty, tf_count_empty, digits=True)


# 29-31 one-dimensional elementary automata, top row seeds each row below.
def gi_ca(rng):
    h, w = _sz(rng, 5, 16); g = blank(h, w); col = rng.choice(COLOURS)
    for c in range(w):
        if rng.random() < 0.35: g[0][c] = col
    return g if any(g[0]) and h >= 3 else None
def _ca(g, table):
    a = _alive(g)
    if not a: return None
    H, W = dims(g); out = blank(H, W); out[0] = g[0][:]
    for r in range(1, H):
        prev = [1 if v else 0 for v in out[r - 1]]
        for c in range(W):
            l, m, rr = prev[c - 1] if c else 0, prev[c], prev[c + 1] if c + 1 < W else 0
            out[r][c] = a if table & (1 << (l * 4 + m * 2 + rr)) else 0
    return out
rule("elementary_ca_rule90_rows", "The top row seeds a one-dimensional automaton (Wolfram rule 90): each cell of every lower row is coloured exactly when the cells above-left and above-right differ, off-grid counting as empty.", gi_ca, lambda g: _ca(g, 90))
rule("elementary_ca_rule30_rows", "The top row seeds a one-dimensional automaton (Wolfram rule 30): a cell is coloured exactly when the cell above-left differs from the OR of the cells above and above-right, off-grid counting as empty.", gi_ca, lambda g: _ca(g, 30))
rule("elementary_ca_rule110_rows", "The top row seeds a one-dimensional automaton (Wolfram rule 110): a cell is coloured when at least one of the cells above or above-right is coloured, except when all three cells above-left, above and above-right are coloured.", gi_ca, lambda g: _ca(g, 110))


# 32 traffic (rule 184): every car moves right if the cell ahead is empty.
def gi_traffic(rng):
    return _noise(rng, colours(rng, rng.randint(1, 3)), rng.uniform(0.35, 0.55))
def tf_traffic(g):
    H, W = dims(g); out = blank(H, W)
    for r in range(H):
        for c in range(W):
            if g[r][c]:
                if c + 1 < W and g[r][c + 1] == 0: out[r][c + 1] = g[r][c]
                else: out[r][c] = g[r][c]
    return out
rule("traffic_cars_step_right", "One traffic step: every coloured cell whose right-hand neighbour is empty moves one cell right, all at once; cells blocked by a neighbour or the edge stay.", gi_traffic, tf_traffic)


# 33 fill empty cells with three matching side-neighbours.
def gi_fill3(rng):
    return _punch(rng, _rects(rng, colours(rng, rng.randint(1, 3)), density=0.14, side=(3, 8)), 0.08)
def tf_fill3(g):
    H, W = dims(g); out = copy(g)
    for r in range(H):
        for c in range(W):
            if not g[r][c]:
                nb = [v for v in _nbs(g, r, c, N4) if v]
                for v in set(nb):
                    if nb.count(v) >= 3: out[r][c] = v
    return out
rule("fill_empty_with_three_same_sides", "One step: an empty cell with at least three of its four side-neighbours in the same colour takes that colour; other cells stay.", gi_fill3, tf_fill3)


# 34 remove cells with fewer than two same-colour neighbours.
def gi_prune2(rng):
    return _noise(rng, colours(rng, rng.randint(1, 3)), rng.uniform(0.4, 0.55))
def tf_prune2(g):
    H, W = dims(g); out = copy(g)
    for r in range(H):
        for c in range(W):
            if g[r][c] and sum(1 for v in _nbs(g, r, c, N8) if v == g[r][c]) < 2: out[r][c] = 0
    return out
rule("remove_cells_under_two_same_neighbours", "One step: every coloured cell with fewer than two neighbours of its own colour (eight directions) is erased; the rest stay.", gi_prune2, tf_prune2)


# 35 every cell falls one step if the cell below is empty.
def gi_fall1(rng):
    return _noise(rng, colours(rng, rng.randint(1, 3)), rng.uniform(0.25, 0.4))
def tf_fall1(g):
    H, W = dims(g); out = blank(H, W)
    for r in range(H):
        for c in range(W):
            if g[r][c]:
                if r + 1 < H and g[r + 1][c] == 0: out[r + 1][c] = g[r][c]
                else: out[r][c] = g[r][c]
    return out
rule("cells_fall_one_step", "One gravity step: every coloured cell whose cell directly below is empty moves down exactly one cell, all at once; cells resting on something or on the floor stay.", gi_fall1, tf_fall1)


# 36/37 sandpile toppling: a cell of 4 or more gives one to each side-neighbour.
def gi_pile(rng):
    h, w = _sz(rng); g = [[rng.randint(1, 9) if rng.random() < 0.45 else 0 for _ in range(w)] for _ in range(h)]
    return g if any(v >= 4 for row in g for v in row) else None
def _topple(g):
    H, W = dims(g); out = copy(g); moved = False
    for r in range(H):
        for c in range(W):
            if g[r][c] >= 4:
                out[r][c] -= 4; moved = True
                for dr, dc in N4:
                    if 0 <= r + dr < H and 0 <= c + dc < W: out[r + dr][c + dc] += 1
    return out, moved
def tf_pile1(g):
    return _topple(g)[0]
def tf_pile_settle(g):
    for _ in range(3000):
        g, moved = _topple(g)
        if not moved: return g
    return None
rule("sandpile_topple_one_step", "One toppling step: every cell holding 4 or more loses 4 and adds 1 to each of its four side-neighbours, all at once; grains pushed off the grid edge are lost.", gi_pile, tf_pile1, digits=True)
rule("sandpile_topple_until_stable", "Toppling repeats until every cell holds at most 3: in each step all cells of 4 or more lose 4 and add 1 to each side-neighbour, grains leaving the grid being lost.", gi_pile, tf_pile_settle, digits=True)


# 38 equality with the right-hand neighbour.
def gi_eqright(rng):
    g = _regions(rng, colours(rng, rng.randint(2, 3)), lo=6, hi=16); H, W = dims(g)
    for _ in range(H * W // 8): g[rng.randrange(H)][rng.randrange(W)] = rng.choice(COLOURS)
    return g if W >= 3 else None
def tf_eqright(g):
    return [[1 if row[c] == row[c + 1] else 2 for c in range(len(row) - 1)] for row in g]
rule("equal_to_right_neighbour_map", "Output is one column narrower: each cell becomes 1 if the input cell matched the cell to its right and 2 if it differed.", gi_eqright, tf_eqright)


# 39 colour borders marked grey.
def gi_borders(rng):
    return _regions(rng, colours(rng, rng.randint(2, 4), exclude=(0, 5)))
def tf_borders(g):
    H, W = dims(g); out = copy(g)
    for r in range(H):
        for c in range(W):
            if any(v != g[r][c] for v in _nbs(g, r, c, N4)): out[r][c] = 5
    return out
rule("mark_colour_borders_grey", "Every cell that has a side-neighbour of a different colour is recoloured grey (5); cells surrounded by their own colour stay.", gi_borders, tf_borders)


# 40 parity rule: on when an odd number of side-neighbours is on.
def gi_parity(rng):
    return _noise(rng, [rng.choice(COLOURS)], rng.uniform(0.25, 0.45))
def tf_parity(g):
    a = _alive(g)
    if not a: return None
    H, W = dims(g); out = blank(H, W)
    for r in range(H):
        for c in range(W):
            if sum(1 for v in _nbs(g, r, c, N4) if v) % 2: out[r][c] = a
    return out
rule("parity_of_side_neighbours_one_step", "One step: a cell becomes coloured exactly when an odd number of its four side-neighbours were coloured, regardless of its own state; otherwise it becomes empty.", gi_parity, tf_parity)
