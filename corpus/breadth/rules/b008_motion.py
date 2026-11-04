# b008_motion.py -- MOTION / PHYSICS / SIMULATION: objects move by vectors, slide until blocked, fall and stack,
# bounce, orbit, rotate about pivots, pour and fill. Every transform is a hand-applicable one-step simulation.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

D4 = {"down": (1, 0), "up": (-1, 0), "left": (0, -1), "right": (0, 1)}
GREY = 5


def _size(rng, lo, hi):
    """Grid size; about 40% of drawn inputs land in the 21-30 band ARC-AGI-2 lives in."""
    if rng.random() < 0.4: return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _sign(x):
    return (x > 0) - (x < 0)


def _rotk(g, k):
    for _ in range(k % 4):
        g = rot90(g)
    return g


def _cell_gravity(g, fixed=()):
    """Every non-fixed coloured cell falls straight down, stacking on the floor, on fixed cells or on each other."""
    h, w = dims(g); out = blank(h, w)
    for c in range(w):
        stops = [r for r in range(h) if g[r][c] in fixed] + [h]
        for r in stops[:-1]: out[r][c] = g[r][c]
        top = 0
        for stop in stops:
            col = [g[r][c] for r in range(top, stop) if g[r][c] != 0]
            for i, v in enumerate(reversed(col)): out[stop - 1 - i][c] = v
            top = stop + 1
    return out


def _rigid_gravity(g, fixed=()):
    """Each same-colour object drops as a block until it rests on the floor, a fixed cell or another object."""
    h, w = dims(g); out = copy(g)
    obs = components(g, lambda v: v != 0 and v not in fixed)
    for o in sorted(obs, key=lambda o: -max(r for r, _ in o)):
        col = out[o[0][0]][o[0][1]]
        for r, c in o: out[r][c] = 0
        s = 0
        while all(r + s + 1 < h and out[r + s + 1][c] == 0 for r, c in o): s += 1
        for r, c in o: out[r + s][c] = col
    return out


def _move_all(g, moves, keep=()):
    """moves: list of (cells, colour, dr, dc). Cells in keep stay. None if anything leaves the grid or overlaps."""
    h, w = dims(g); out = blank(h, w); taken = set()
    for r, c in keep: out[r][c] = g[r][c]; taken.add((r, c))
    for cells_, col, dr, dc in moves:
        for r, c in cells_:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < h and 0 <= nc < w) or (nr, nc) in taken: return None
            taken.add((nr, nc)); out[nr][nc] = col
    return out


def _scene(rng, k_lo, k_hi, n_lo, n_hi, lo, hi, margin, cols=None):
    h, w = _size(rng, lo, hi); g = blank(h, w); k = rng.randint(k_lo, k_hi)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    cs = [rng.choice(cols or COLOURS) for _ in range(k)]
    if place_shapes(rng, g, shapes, cs, margin=margin) is None: return None
    return g


def _ushape(rng, h, w, col):
    """A U-shaped open-top container; returns (grid-with-container, rt, rb, cl, cr)."""
    cl = rng.randint(1, w - 5); cr = rng.randint(cl + 3, min(w - 2, cl + 8))
    rb = rng.randint(h - 3, h - 1); rt = rng.randint(max(2, rb - 7), rb - 2)
    g = blank(h, w)
    for c in range(cl, cr + 1): g[rb][c] = col
    for r in range(rt, rb): g[r][cl] = col; g[r][cr] = col
    return g, rt, rb, cl, cr


# 1 gravity toward the one fully coloured edge.
def gi_wallgrav(rng):
    h, w = _size(rng, 6, 16); wall = rng.choice(COLOURS); g = blank(h, w)
    for c in range(w): g[h - 1][c] = wall
    for _ in range(rng.randint(4, h * w // 4)):
        g[rng.randrange(h - 1)][rng.randrange(w)] = rng.choice([c for c in COLOURS if c != wall])
    g = _rotk(g, rng.randrange(4)); h, w = dims(g)
    edges = [g[0], g[-1], [r[0] for r in g], [r[-1] for r in g]]
    return g if sum(1 for e in edges if e[0] and len(set(e)) == 1) == 1 else None
def tf_wallgrav(g):
    for k in range(4):
        gg = _rotk(g, k)
        if gg[-1][0] and len(set(gg[-1])) == 1: break
    wall = gg[-1][0]
    body = _cell_gravity(gg[:-1]) + [gg[-1]]
    return _rotk(body, 4 - k)
rule("gravity_toward_coloured_wall", "One grid edge is a solid coloured wall; every other cell falls straight toward that wall and stacks against it.", gi_wallgrav, tf_wallgrav)


# 2 rigid fall toward the edge holding the grey marker.
def gi_rigidmarker(rng):
    g = _scene(rng, 2, 5, 2, 7, 7, 16, 1, [c for c in COLOURS if c != GREY])
    if g is None: return None
    h, w = dims(g); side = rng.randrange(4)
    r, c = [(h - 1, rng.randint(1, w - 2)), (rng.randint(1, h - 2), w - 1), (0, rng.randint(1, w - 2)), (rng.randint(1, h - 2), 0)][side]
    if g[r][c] or any(0 <= r + dr < h and 0 <= c + dc < w and g[r + dr][c + dc] for dr, dc in D4.values()): return None
    g[r][c] = GREY
    return g
def tf_rigidmarker(g):
    h, w = dims(g); (r, c), = cells(g, lambda v: v == GREY)
    k = 0 if r == h - 1 else 1 if c == w - 1 else 2 if r == 0 else 3
    gg = _rigid_gravity(_rotk(g, k), fixed=(GREY,))
    return _rotk(gg, 4 - k)
rule("rigid_fall_toward_marker_edge", "A grey cell sits on one grid edge; every object drops as a rigid piece toward that edge and stacks there, the grey cell staying put.", gi_rigidmarker, tf_rigidmarker)


# 3 colour is a velocity: 1 up, 2 down, 3 left, 4 right, two cells each.
VEC = {1: (-2, 0), 2: (2, 0), 3: (0, -2), 4: (0, 2)}
def gi_colvec(rng):
    return _scene(rng, 2, 5, 2, 6, 8, 18, 3, [1, 2, 3, 4])
def tf_colvec(g):
    moves = [(o, g[o[0][0]][o[0][1]], *VEC[g[o[0][0]][o[0][1]]]) for o in objects(g, 0)]
    return _move_all(g, moves)
rule("objects_move_by_colour_vector", "Each object moves two cells in the direction its colour names: 1 up, 2 down, 3 left, 4 right.", gi_colvec, tf_colvec)


# 4 a grey thruster cell stuck to an object pushes it three cells away from itself.
def gi_thruster(rng):
    g = _scene(rng, 1, 4, 2, 6, 8, 18, 4, [c for c in COLOURS if c != GREY])
    if g is None: return None
    h, w = dims(g)
    for o in objects(g, 0):
        for _ in range(20):
            dr, dc = rng.choice(list(D4.values())); r, c = rng.choice(o)
            if 0 <= r - dr < h and 0 <= c - dc < w and g[r - dr][c - dc] == 0:
                g[r - dr][c - dc] = GREY; break
        else: return None
    return g
def tf_thruster(g):
    h, w = dims(g); moves = []
    obs = [o for o in objects(g, 0) if g[o[0][0]][o[0][1]] != GREY]
    for o in obs:
        s = set(o); vec = None
        for r, c in o:
            for dr, dc in D4.values():
                if 0 <= r + dr < h and 0 <= c + dc < w and g[r + dr][c + dc] == GREY: vec = (-3 * dr, -3 * dc)
        if vec is None: return None
        moves.append((o, g[o[0][0]][o[0][1]], *vec))
    return _move_all(g, moves)
rule("thruster_cell_pushes_object_three", "A grey cell touching an object is a thruster: the object moves three cells directly away from it and the grey cell vanishes.", gi_thruster, tf_thruster)


# 5 object moves right by its own cell count.
def gi_shiftcount(rng):
    h, w = _size(rng, 6, 16); w = max(w, 10); g = blank(h, w); k = rng.randint(2, 5)
    shapes = [random_shape(rng, rng.randint(1, 5)) for _ in range(k)]
    if place_shapes(rng, g, shapes, [rng.choice(COLOURS) for _ in range(k)], margin=1) is None: return None
    return g
def tf_shiftcount(g):
    return _move_all(g, [(o, g[o[0][0]][o[0][1]], 0, len(o)) for o in objects(g, 0)])
rule("objects_shift_right_by_cell_count", "Every object slides to the right by as many cells as it has.", gi_shiftcount, tf_shiftcount)


# 6 movers slide right until just before a stopper-coloured cell; other colours are passed over.
def gi_stopper(rng):
    h, w = _size(rng, 6, 16); M, S, T = colours(rng, 3); g = blank(h, w)
    for r in rng.sample(range(h), rng.randint(2, h)):
        c0 = rng.randrange(w - 2); g[r][c0] = M
        if rng.random() < 0.7: g[r][rng.randint(c0 + 2, w - 1)] = S
        for c in rng.sample(range(w), rng.randint(0, 2)):
            if g[r][c] == 0: g[r][c] = T
    g[0][0] = S if g[0][0] == 0 else g[0][0]
    return g
def tf_stopper(g):
    h, w = dims(g); S = g[0][0]; out = copy(g); movers = _movers(g, S)
    if movers is None: return None
    for r, c, M in movers:
        t = next((x for x in range(c + 1, w) if g[r][x] == S), w) - 1
        if out[r][t] not in (0, M): return None
        out[r][c] = 0; out[r][t] = M
    return out
def _movers(g, S):
    """The mover colour: the only non-stopper colour that never appears twice on one row."""
    h, w = dims(g); cand = {}
    for r in range(h):
        for c in range(w):
            v = g[r][c]
            if v and v != S: cand.setdefault(v, []).append((r, c))
    good = [v for v, cs in cand.items() if len({r for r, _ in cs}) == len(cs)]
    if len(good) != 1: return None
    M = good[0]
    return [(r, c, M) for r, c in cand[M]]
rule("slide_right_until_stopper_colour", "The corner cell names the stopper colour; the colour that appears once per row slides right until the cell before a stopper, passing over any other colour.", gi_stopper, tf_stopper)


# 7 a ball with a grey tail bounces diagonally off the top and bottom edges, leaving a trail to the right edge.
def gi_bounce(rng):
    h, w = _size(rng, 5, 16); g = blank(h, w); B = rng.choice([c for c in COLOURS if c != GREY])
    r, c = rng.randint(1, h - 2), rng.randint(1, w // 2); dr = rng.choice([-1, 1])
    g[r][c] = B; g[r - dr][c - 1] = GREY
    return g
def tf_bounce(g):
    h, w = dims(g); (br, bc), = cells(g, lambda v: v not in (0, GREY)); (gr, gc), = cells(g, lambda v: v == GREY)
    B = g[br][bc]; dr = br - gr; out = blank(h, w); r, c = br, bc
    while c < w:
        out[r][c] = B
        if not 0 <= r + dr < h: dr = -dr
        r += dr; c += 1
    return out
rule("ball_bounce_trail_to_right_edge", "The ball flies diagonally away from its grey tail, bouncing off the top and bottom edges, and paints its whole path to the right edge.", gi_bounce, tf_bounce)


# 8 single cells aligned with the big rectangle slide toward it until touching.
def gi_tolargest(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w); A = rng.choice(COLOURS)
    r0, c0 = rng.randint(2, h - 5), rng.randint(2, w - 5); r1, c1 = rng.randint(r0 + 1, min(h - 3, r0 + 4)), rng.randint(c0 + 1, min(w - 3, c0 + 4))
    rect(g, r0, c0, r1, c1, A); n = 0
    for _ in range(rng.randint(2, 6)):
        col = rng.choice([c for c in COLOURS if c != A])
        if rng.random() < 0.5:
            r = rng.randint(r0, r1); c = rng.choice([x for x in range(w) if x < c0 - 1 or x > c1 + 1])
        else:
            c = rng.randint(c0, c1); r = rng.choice([y for y in range(h) if y < r0 - 1 or y > r1 + 1])
        if g[r][c] == 0: g[r][c] = col; n += 1
    return g if n else None
def tf_tolargest(g):
    obs = objects(g, 0); big = max(obs, key=len); r0, c0, r1, c1 = bbox(big); out = copy(g)
    singles = [o[0] for o in obs if len(o) == 1]
    def dist(p): return min(abs(p[0] - r0), abs(p[0] - r1), abs(p[1] - c0), abs(p[1] - c1))
    for r, c in sorted(singles, key=dist):
        dr, dc = (0, _sign(c0 - c)) if r0 <= r <= r1 else (_sign(r0 - r), 0)
        col = out[r][c]; out[r][c] = 0
        while out[r + dr][c + dc] == 0: r += dr; c += dc
        out[r][c] = col
    return out
rule("singletons_slide_to_largest_object", "Each single cell slides straight along its row or column toward the big rectangle until it touches it or something in the way.", gi_tolargest, tf_tolargest)


# 9/10 repel from / attract to a grey centre marker by one cell.
def gi_marker_field(rng):
    h, w = _size(rng, 7, 16); g = blank(h, w); pr, pc = rng.randint(2, h - 3), rng.randint(2, w - 3); g[pr][pc] = GREY
    for _ in range(rng.randint(3, (h * w) // 6)):
        r, c = rng.randrange(h), rng.randrange(w)
        if g[r][c] == 0 and (r, c) != (pr, pc): g[r][c] = rng.choice([c for c in COLOURS if c != GREY])
    return g
def _radial(g, s):
    (pr, pc), = cells(g, lambda v: v == GREY); moves = []
    for r, c in cells(g, lambda v: v not in (0, GREY)):
        dr, dc = s * _sign(r - pr), s * _sign(c - pc)
        if s < 0 and max(abs(r - pr), abs(c - pc)) == 1: dr = dc = 0
        moves.append(([(r, c)], g[r][c], dr, dc))
    return _move_all(g, moves, keep=[(pr, pc)])
def gi_repel_field(rng):
    h, w = _size(rng, 7, 16); g = blank(h, w); pr, pc = rng.randint(2, h - 3), rng.randint(2, w - 3); g[pr][pc] = GREY
    for _ in range(rng.randint(3, (h * w) // 6)):
        r, c = rng.randint(1, h - 2), rng.randint(1, w - 2)
        if g[r][c] == 0: g[r][c] = rng.choice([c for c in COLOURS if c != GREY])
    return g
rule("repel_from_grey_marker_one_cell", "Every coloured cell steps one cell directly away from the grey marker, diagonally if it is off both the marker's row and column.", gi_repel_field, lambda g: _radial(g, 1))
rule("attract_to_grey_marker_one_cell", "Every coloured cell steps one cell toward the grey marker, diagonally where needed; cells already touching it stay.", gi_marker_field, lambda g: _radial(g, -1))


# 11 objects swap sides across the grey axis without being reflected.
def gi_swapaxis(rng):
    h, w = _size(rng, 6, 16); hw = max(4, (w - 1) // 2); w = 2 * hw + 1; g = blank(h, w); k = rng.randint(2, 5)
    shapes = [random_shape(rng, rng.randint(2, 6)) for _ in range(k)]
    if place_shapes(rng, g, shapes, [rng.choice([c for c in COLOURS if c != GREY]) for _ in range(k)], margin=1) is None: return None
    if any(g[r][hw] for r in range(h)): return None
    for r in range(h): g[r][hw] = GREY
    return g
def tf_swapaxis(g):
    h, w = dims(g); moves = []
    for o in objects(g, 0):
        if g[o[0][0]][o[0][1]] == GREY: continue
        r0, c0, r1, c1 = bbox(o); moves.append((o, g[o[0][0]][o[0][1]], 0, (w - 1 - c1) - c0))
    return _move_all(g, moves, keep=[(r, w // 2) for r in range(h)])
rule("objects_swap_sides_across_axis_unreflected", "Each object jumps to the mirror position on the other side of the grey axis line but keeps its orientation.", gi_swapaxis, tf_swapaxis)


# 12 a snake (body line plus head cell) grows forward by its own length.
def gi_snake(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w); n = 0
    for _ in range(rng.randint(1, 3)):
        B, Hd = colours(rng, 2); L = rng.randint(2, 4); dr, dc = rng.choice(list(D4.values()))
        r, c = rng.randrange(h), rng.randrange(w)
        cs = [(r + i * dr, c + i * dc) for i in range(L + 1)]
        if all(0 <= y < h and 0 <= x < w and g[y][x] == 0 and all(not (0 <= y + a < h and 0 <= x + b < w) or g[y + a][x + b] == 0 for a in (-1, 0, 1) for b in (-1, 0, 1)) for y, x in cs):
            for y, x in cs[:-1]: g[y][x] = B
            g[cs[-1][0]][cs[-1][1]] = Hd; n += 1
    return g if n else None
def tf_snake(g):
    h, w = dims(g); out = copy(g)
    for o in objects(g, 0, conn8=False):
        if len(o) != 1: continue
        (hr, hc), = o; Hd = g[hr][hc]
        nb = [(dr, dc) for dr, dc in D4.values() if 0 <= hr + dr < h and 0 <= hc + dc < w and g[hr + dr][hc + dc] not in (0, Hd)]
        if len(nb) != 1: return None
        dr, dc = -nb[0][0], -nb[0][1]; B = g[hr - dr][hc - dc]
        L = 1
        while 0 <= hr - (L + 1) * dr < h and 0 <= hc - (L + 1) * dc < w and g[hr - (L + 1) * dr][hc - (L + 1) * dc] == B: L += 1
        for i in range(L + 1):
            y, x = hr + i * dr, hc + i * dc
            if not (0 <= y < h and 0 <= x < w) or (out[y][x] and i): return None
            out[y][x] = B if i < L else Hd
    return out
rule("snake_grows_by_its_length", "Each snake (a straight body with a differently coloured head) grows forward past its head by its body length, the head moving to the new end.", gi_snake, tf_snake)


# 13 quarter turn about the grey pivot.
def gi_pivot(rng):
    h, w = _size(rng, 7, 16); g = blank(h, w); pr, pc = rng.randint(h // 3, 2 * h // 3), rng.randint(w // 3, 2 * w // 3); g[pr][pc] = GREY
    k = rng.randint(1, 3); shapes = [random_shape(rng, rng.randint(1, 4)) for _ in range(k)]
    if place_shapes(rng, g, shapes, [rng.choice([c for c in COLOURS if c != GREY]) for _ in range(k)], margin=0) is None: return None
    return g if len(cells(g, lambda v: v == GREY)) == 1 else None
def tf_pivot(g):
    (pr, pc), = cells(g, lambda v: v == GREY); h, w = dims(g); out = blank(h, w); out[pr][pc] = GREY
    for r, c in cells(g, lambda v: v not in (0, GREY)):
        nr, nc = pr + (c - pc), pc - (r - pr)
        if not (0 <= nr < h and 0 <= nc < w) or out[nr][nc]: return None
        out[nr][nc] = g[r][c]
    return out
rule("rotate_cells_quarter_turn_around_pivot", "Every coloured cell swings a quarter turn clockwise about the grey pivot cell, which stays where it is.", gi_pivot, tf_pivot)
def tf_pointref(g):
    (pr, pc), = cells(g, lambda v: v == GREY); h, w = dims(g); out = blank(h, w); out[pr][pc] = GREY
    for r, c in cells(g, lambda v: v not in (0, GREY)):
        nr, nc = 2 * pr - r, 2 * pc - c
        if not (0 <= nr < h and 0 <= nc < w) or out[nr][nc]: return None
        out[nr][nc] = g[r][c]
    return out
rule("cells_jump_to_opposite_side_of_pivot", "Every coloured cell jumps to the point the same distance beyond the grey pivot on the opposite side.", gi_pivot, tf_pointref)


# 14/15 beads sitting on a frame ring orbit along it.
def _ring(r0, c0, r1, c1):
    return ([(r0, c) for c in range(c0, c1)] + [(r, c1) for r in range(r0, r1)]
            + [(r1, c) for c in range(c1, c0, -1)] + [(r, c0) for r in range(r1, r0, -1)])
def gi_beads(rng):
    h, w = _size(rng, 6, 16); g = blank(h, w); F = rng.choice(COLOURS)
    r0, c0 = rng.randint(0, h - 4), rng.randint(0, w - 4); r1, c1 = rng.randint(r0 + 3, h - 1), rng.randint(c0 + 3, w - 1)
    ring = _ring(r0, c0, r1, c1); rect(g, r0, c0, r1, c1, F, fill=False)
    for i in rng.sample(range(len(ring)), rng.randint(1, max(1, len(ring) // 4))):
        g[ring[i][0]][ring[i][1]] = rng.choice([c for c in COLOURS if c != F])
    return g
def _orbit(g, step_fn):
    pts = cells(g, lambda v: v != 0); ring = _ring(*bbox(pts)); cnt = {}
    for r, c in ring: cnt[g[r][c]] = cnt.get(g[r][c], 0) + 1
    F = max(cnt, key=cnt.get); beads = [i for i, (r, c) in enumerate(ring) if g[r][c] != F]
    out = copy(g); n = len(ring); s = step_fn(len(beads))
    for r, c in ring: out[r][c] = F
    for i in beads:
        r, c = ring[(i + s) % n]; out[r][c] = g[ring[i][0]][ring[i][1]]
    return out
rule("beads_orbit_frame_one_step_clockwise", "Coloured beads sitting on a hollow frame each move one cell clockwise along the frame.", gi_beads, lambda g: _orbit(g, lambda n: 1))
rule("beads_orbit_frame_anticlockwise_by_count", "Coloured beads sitting on a hollow frame each move anticlockwise along it by as many cells as there are beads.", gi_beads, lambda g: _orbit(g, lambda n: -n))


# 16/17 rows and columns roll by their own cell count.
def gi_rollcount(rng):
    h, w = _size(rng, 5, 14); g = blank(h, w)
    for _ in range(rng.randint(h, h * w // 2)):
        g[rng.randrange(h)][rng.randrange(w)] = rng.choice(COLOURS)
    return g
def tf_rowroll(g):
    w = len(g[0]); out = []
    for row in g:
        k = sum(1 for v in row if v) % w; out.append(row[w - k:] + row[:w - k])
    return out
rule("rows_roll_right_by_cell_count", "Each row is shifted right by the number of coloured cells it holds, cells wrapping from the right edge to the left.", gi_rollcount, tf_rowroll)
def tf_colroll(g):
    t = transpose(g); h = len(g); out = []
    for col in t:
        k = sum(1 for v in col if v) % h; out.append(col[k:] + col[:k])
    return transpose(out)
rule("columns_roll_up_by_cell_count", "Each column is shifted up by the number of coloured cells it holds, cells wrapping from the top edge to the bottom.", gi_rollcount, tf_colroll)


# 18 a hanging column of cells pours into the U-shaped container below.
def gi_pour(rng):
    h, w = _size(rng, 9, 18); C, P = colours(rng, 2); g, rt, rb, cl, cr = _ushape(rng, h, w, C)
    cap = (cr - cl - 1) * (rb - rt); k = rng.randint(1, min(cap, rt - 1))
    c = rng.randint(cl + 1, cr - 1)
    for r in range(k): g[r][c] = P
    return g
def tf_pour(g):
    h, w = dims(g); P = next(v for v in g[0] if v); k = sum(1 for row in g for v in row if v == P)
    Cc = cells(g, lambda v: v not in (0, P)); rt, cl, rb, cr = bbox(Cc); out = copy(g)
    for r, c in cells(g, lambda v: v == P): out[r][c] = 0
    for r in range(rb - 1, rt - 1, -1):
        for c in range(cl + 1, cr):
            if k: out[r][c] = P; k -= 1
    return out
rule("pour_column_into_container", "The hanging column of cells pours into the open container below, filling it from the bottom row up and left to right.", gi_pour, tf_pour)


# 19 water fills the container up to the level of the marker at the left edge.
def gi_level(rng):
    h, w = _size(rng, 8, 18); C = rng.choice([c for c in COLOURS if c != 8]); g, rt, rb, cl, cr = _ushape(rng, h, w, C)
    if cl == 0: return None
    g[rng.randint(rt, rb - 1)][0] = 8
    return g
def tf_level(g):
    (rm, _), = cells(g, lambda v: v == 8); Cc = cells(g, lambda v: v not in (0, 8)); rt, cl, rb, cr = bbox(Cc); out = copy(g)
    for r in range(rm, rb):
        for c in range(cl + 1, cr): out[r][c] = 8
    return out
rule("water_fill_to_level_marker", "The container fills with water colour 8 from its floor up to the row of the water marker on the left edge.", gi_level, tf_level)


# 20 gravity down then everything slides left.
def tf_downleft(g):
    out = _cell_gravity(g); w = len(out[0])
    return [[v for v in row if v] + [0] * (w - sum(1 for v in row if v)) for row in out]
rule("gravity_down_then_left", "All cells fall to the floor and stack, then every cell slides left along its row as far as it can.", gi_rollcount, tf_downleft)


# 21 heavy colours sink, light colours float.
def gi_heavy(rng):
    h, w = _size(rng, 5, 14); g = blank(h, w)
    for _ in range(rng.randint(h, h * w // 2)):
        g[rng.randrange(h)][rng.randrange(w)] = rng.choice(COLOURS)
    vals = {v for row in g for v in row if v}
    return g if any(v <= 4 for v in vals) and any(v >= 5 for v in vals) else None
def tf_heavy(g):
    h, w = dims(g); out = blank(h, w)
    for c in range(w):
        light = [g[r][c] for r in range(h) if 1 <= g[r][c] <= 4]; heavy = [g[r][c] for r in range(h) if g[r][c] >= 5]
        for i, v in enumerate(light): out[i][c] = v
        for i, v in enumerate(reversed(heavy)): out[h - 1 - i][c] = v
    return out
rule("heavy_colours_sink_light_colours_float", "In each column, cells of colours 1-4 float up and stack at the top while cells of colours 5-9 sink and stack at the bottom.", gi_heavy, tf_heavy)


# 22 an object slides toward the lone beacon cell of its own colour until touching.
def gi_beacon(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w); k = rng.randint(1, 3); cols = colours(rng, k)
    shapes = [random_shape(rng, rng.randint(2, 5)) for _ in range(k)]
    if place_shapes(rng, g, shapes, cols, margin=2) is None: return None
    for col in cols:
        o = objects(g, 0); o = next(x for x in o if g[x[0][0]][x[0][1]] == col); r0, c0, r1, c1 = bbox(o)
        for _ in range(30):
            if rng.random() < 0.5:
                r = rng.randint(r0, r1); c = rng.choice([x for x in range(w) if x < c0 - 1 or x > c1 + 1] or [None])
            else:
                c = rng.randint(c0, c1); r = rng.choice([y for y in range(h) if y < r0 - 1 or y > r1 + 1] or [None])
            if r is None or c is None: continue
            if g[r][c] == 0 and all(g[y][x] == 0 for y in range(max(0, r - 1), min(h, r + 2)) for x in range(max(0, c - 1), min(w, c + 2))):
                g[r][c] = col; break
        else: return None
    return g
def tf_beacon(g):
    moves, keep = [], []
    for col in {v for row in g for v in row if v}:
        comps = components(g, col, conn8=True); beacon = [o for o in comps if len(o) == 1]; body = [o for o in comps if len(o) > 1]
        if len(beacon) != 1 or len(body) != 1: return None
        (br, bc), = beacon[0]; o = body[0]; r0, c0, r1, c1 = bbox(o); keep.append((br, bc))
        if r0 <= br <= r1: dr, dc = 0, (bc - c1 - 1) if bc > c1 else (bc + 1 - c0)
        else: dr, dc = ((br - r1 - 1) if br > r1 else (br + 1 - r0)), 0
        moves.append((o, col, dr, dc))
    return _move_all(g, moves, keep=keep)
rule("object_slides_to_its_colour_beacon", "Each object slides straight toward the single lone cell of its own colour until the two touch; the lone cell does not move.", gi_beacon, tf_beacon)


# 23 cells fall through the gaps of a grey platform or rest on it.
def gi_platform(rng):
    h, w = _size(rng, 7, 16); g = blank(h, w); rp = rng.randint(h // 2, h - 3)
    gaps = set(rng.sample(range(w), rng.randint(1, max(1, w // 3))))
    for c in range(w):
        if c not in gaps: g[rp][c] = GREY
    for _ in range(rng.randint(3, w * rp // 3)):
        g[rng.randrange(rp)][rng.randrange(w)] = rng.choice([c for c in COLOURS if c != GREY])
    return g
rule("cells_fall_through_platform_gaps", "Cells above the grey platform fall straight down; those over a gap fall through to the floor, the rest stack on the platform.", gi_platform, lambda g: _cell_gravity(g, fixed=(GREY,)))


# 24 conveyor rows: left-border marker 1 shifts the row right, 2 shifts it left, wrapping.
def gi_conveyor(rng):
    h, w = _size(rng, 5, 14); g = blank(h, w); n = 0
    for r in range(h):
        m = rng.choice([0, 1, 2]); g[r][0] = m
        for c in range(1, w):
            if rng.random() < 0.35: g[r][c] = rng.choice(range(3, 10))
        if m and any(g[r][1:]): n += 1
    return g if n else None
def tf_conveyor(g):
    out = []
    for row in g:
        body = row[1:]
        if row[0] == 1: body = body[-1:] + body[:-1]
        elif row[0] == 2: body = body[1:] + body[:1]
        out.append([row[0]] + body)
    return out
rule("conveyor_rows_shift_by_edge_marker", "A left-edge marker drives its row like a conveyor: 1 shifts the row one cell right, 2 one cell left, both wrapping; unmarked rows stay.", gi_conveyor, tf_conveyor)


# 25 a marble falls from the top, stepping right off one bumper colour and left off the other.
def gi_marble(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w); M, A, B = colours(rng, 3); c = rng.randrange(w); g[0][c] = M
    for _ in range(rng.randint(2, h * w // 6)):
        r, cc = rng.randint(2, h - 1), rng.randrange(w)
        if g[r][cc] == 0: g[r][cc] = rng.choice([A, B])
    g[1][0] = A if g[1][0] == 0 else g[1][0]   # legend: the colour at row 1 col 0 deflects right... keep explicit
    return g
def tf_marble(g):
    h, w = dims(g); c = next(x for x in range(w) if g[0][x]); M = g[0][c]; A = g[1][0]; r = 0; out = copy(g); steps = 0
    while r < h - 1 and steps < 4 * h * w:
        steps += 1; below = g[r + 1][c]
        if below == 0: r += 1
        else:
            c += 1 if below == A else -1
            if not 0 <= c < w or g[r][c]: return None
        out[r][c] = M
    return out if r == h - 1 else None
rule("marble_deflected_by_bumper_colours", "The top marble falls, sidestepping right when it lands on a bumper of the legend colour at the left of row two and left on any other bumper, painting its path to the floor.", gi_marble, tf_marble)


# 26 the object steps right once per grey dot in the grid.
def gi_perdot(rng):
    h, w = _size(rng, 6, 16); w = max(w, 10); g = blank(h, w); col = rng.choice([c for c in COLOURS if c != GREY])
    sh = random_shape(rng, rng.randint(2, 6)); hh = max(r for r, _ in sh) + 1; ww = max(c for _, c in sh) + 1
    r0, c0 = rng.randint(0, h - hh), rng.randint(0, w // 2 - ww)
    for r, c in sh: g[r0 + r][c0 + c] = col
    n = rng.randint(1, min(6, w - c0 - ww))
    body = {(r0 + r, c0 + c) for r, c in sh}; placed = 0
    for _ in range(100):
        r, c = rng.randrange(h), rng.randrange(w)
        if g[r][c] == 0 and (r, c) not in body and all((r + a, c + b) not in body for a in (-1, 0, 1) for b in (-1, 0, 1)) and not (r0 <= r < r0 + hh and c0 <= c < c0 + ww + n + 1):
            g[r][c] = GREY; placed += 1
            if placed == n: break
    return g if placed == n else None
def tf_perdot(g):
    dots = cells(g, lambda v: v == GREY); o = [x for x in objects(g, 0) if g[x[0][0]][x[0][1]] != GREY]
    if len(o) != 1: return None
    return _move_all(g, [(o[0], g[o[0][0][0]][o[0][0][1]], 0, len(dots))], keep=dots)
rule("object_steps_right_once_per_grey_dot", "The object moves right by one cell for every grey dot in the grid; the dots stay.", gi_perdot, tf_perdot)


# 28 two cells of one colour on a row slide toward each other and meet in the middle.
def gi_meet(rng):
    h, w = _size(rng, 5, 16); g = blank(h, w); n = 0
    for r in rng.sample(range(h), rng.randint(1, h)):
        if w < 5: continue
        c1 = rng.randrange(w - 3); d = rng.choice([x for x in range(2, w - c1 - 1) if x % 2 == 0] or [None])
        if d is None: continue
        col = rng.choice(COLOURS); g[r][c1] = col; g[r][c1 + d + 1] = col; n += 1
    return g if n else None
def tf_meet(g):
    out = blank(*dims(g))
    for r, row in enumerate(g):
        cs = [c for c, v in enumerate(row) if v]
        if not cs: continue
        if len(cs) != 2 or (cs[1] - cs[0]) % 2 == 0: return None
        m = (cs[0] + cs[1]) // 2; out[r][m] = row[cs[0]]; out[r][m + 1] = row[cs[0]]
    return out
rule("row_pairs_slide_to_meet_in_middle", "The two cells on each row slide toward each other at equal speed and stop side by side at the middle of the gap.", gi_meet, tf_meet)


# 29 diagonal gravity toward the bottom-right corner.
def tf_diaggrav(rng_g):
    g = rng_g; h, w = dims(g); out = blank(h, w)
    for r, c in sorted(cells(g, lambda v: v != 0), key=lambda p: -(p[0] + p[1])):
        col = g[r][c]
        while r + 1 < h and c + 1 < w and out[r + 1][c + 1] == 0: r += 1; c += 1
        out[r][c] = col
    return out
rule("cells_slide_diagonally_to_bottom_right", "Every cell slides diagonally down and to the right until it reaches an edge or rests against another cell.", gi_rollcount, tf_diaggrav)


# 30 rectangles drop and stack bottom-left, widest at the bottom.
def gi_stackrect(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w); k = rng.randint(2, 4); widths = rng.sample(range(1, w // 2 + 1), k) if w // 2 >= k else None
    if widths is None: return None
    hs = [rng.randint(1, max(1, (h - 1) // k)) for _ in range(k)]
    shapes = [[(r, c) for r in range(hh) for c in range(ww)] for hh, ww in zip(hs, widths)]
    if place_shapes(rng, g, shapes, [rng.choice(COLOURS) for _ in range(k)], margin=1) is None: return None
    return g
def tf_stackrect(g):
    h, w = dims(g); out = blank(h, w); y = h
    for o in sorted(objects(g, 0), key=lambda o: -(bbox(o)[3] - bbox(o)[1])):
        r0, c0, r1, c1 = bbox(o); y -= r1 - r0 + 1
        rect(out, y, 0, y + r1 - r0, c1 - c0, g[o[0][0]][o[0][1]])
    return out
rule("rectangles_stack_bottom_left_widest_first", "The rectangles pile up in the bottom-left corner, left-aligned, the widest at the bottom and narrower ones above.", gi_stackrect, tf_stackrect)


# 31 bubbles rise through water to the surface.
def gi_bubbles(rng):
    h, w = _size(rng, 6, 16); g = blank(h, w); rw = rng.randint(1, h // 2)
    for r in range(rw, h):
        for c in range(w): g[r][c] = 8
    for _ in range(rng.randint(2, (h - rw) * w // 3)):
        g[rng.randint(rw, h - 1)][rng.randrange(w)] = rng.choice([c for c in COLOURS if c != 8])
    return g
def tf_bubbles(g):
    h, w = dims(g); out = copy(g); rw = next(r for r in range(h) if 8 in g[r])
    for c in range(w):
        bub = [g[r][c] for r in range(rw, h) if g[r][c] != 8]
        for r in range(rw, h): out[r][c] = 8
        for i, v in enumerate(bub): out[rw + i][c] = v
    return out
rule("bubbles_rise_to_water_surface", "Coloured bubbles inside the water (colour 8) rise straight up and gather at the water surface in their own column.", gi_bubbles, tf_bubbles)


# 32 objects rise to the top edge leaving an exhaust trail of colour 8.
def gi_exhaust(rng):
    h, w = _size(rng, 7, 16); g = blank(h, w); k = rng.randint(1, 4); used = set()
    for _ in range(k):
        sh = random_shape(rng, rng.randint(2, 5)); ww = max(c for _, c in sh) + 1; hh = max(r for r, _ in sh) + 1
        for _ in range(20):
            c0 = rng.randint(0, w - ww); r0 = rng.randint(1, h - hh)
            if not (set(range(c0 - 1, c0 + ww + 1)) & used):
                used |= set(range(c0, c0 + ww)); col = rng.choice([c for c in COLOURS if c != 8])
                for r, c in sh: g[r0 + r][c0 + c] = col
                break
    return g if used else None
def tf_exhaust(g):
    h, w = dims(g); out = blank(h, w)
    for o in objects(g, 0):
        r0 = bbox(o)[0]; new = {(r - r0, c) for r, c in o}; col = g[o[0][0]][o[0][1]]
        for r, c in o:
            for y in range(r - r0, r + 1):
                if (y, c) not in new: out[y][c] = 8
        for r, c in new: out[r][c] = col
    return out
rule("objects_rise_leaving_exhaust_trail", "Every object shoots straight up to the top edge; the cells it passed over are left filled with exhaust colour 8.", gi_exhaust, tf_exhaust)


# 33 wind blows only single cells to the right; larger objects are too heavy.
def gi_wind(rng):
    g = _scene(rng, 2, 4, 2, 6, 7, 16, 1)
    if g is None: return None
    sprinkle(rng, g, rng.randint(2, 6), rng.choice(COLOURS))
    return g if any(len(o) == 1 for o in objects(g, 0)) else None
def tf_wind(g):
    h, w = dims(g); out = copy(g)
    singles = sorted([o[0] for o in objects(g, 0) if len(o) == 1], key=lambda p: -p[1])
    for r, c in singles:
        col = out[r][c]; out[r][c] = 0
        while c + 1 < w and out[r][c + 1] == 0: c += 1
        out[r][c] = col
    return out
rule("wind_blows_single_cells_right", "Single cells are blown to the right until they hit something; objects of two or more cells are too heavy to move.", gi_wind, tf_wind)


# 34 a beam from the border emitter reflects off grey mirror cells as off '/' mirrors.
def gi_beam(rng):
    h, w = _size(rng, 7, 16); g = blank(h, w); E = rng.choice([c for c in COLOURS if c != GREY]); side = rng.randrange(4)
    r, c = [(0, rng.randint(1, w - 2)), (h - 1, rng.randint(1, w - 2)), (rng.randint(1, h - 2), 0), (rng.randint(1, h - 2), w - 1)][side]
    g[r][c] = E
    for _ in range(rng.randint(1, 6)):
        y, x = rng.randint(1, h - 2), rng.randint(1, w - 2)
        if g[y][x] == 0: g[y][x] = GREY
    return g
def tf_beam(g):
    h, w = dims(g); (r, c), = cells(g, lambda v: v not in (0, GREY)); E = g[r][c]
    dr, dc = (1, 0) if r == 0 else (-1, 0) if r == h - 1 else (0, 1) if c == 0 else (0, -1)
    out = copy(g); steps = 0; drew = False
    while steps < 4 * (h + w):
        steps += 1; r += dr; c += dc
        if not (0 <= r < h and 0 <= c < w): break
        if g[r][c] == GREY: dr, dc = -dc, -dr; continue
        if g[r][c] == E and not drew: pass
        out[r][c] = E; drew = True
    return out if drew else None
rule("beam_reflects_off_grey_mirror_cells", "A beam leaves the border cell into the grid and paints its path; every grey cell is a diagonal mirror that turns it, up becoming right, right becoming up, down becoming left, left becoming down.", gi_beam, tf_beam)


# 35 the water level rises by one row around any rocks.
def gi_tide(rng):
    h, w = _size(rng, 6, 16); g = blank(h, w); rw = rng.randint(2, h - 1)
    for r in range(rw, h):
        for c in range(w): g[r][c] = 8
    k = rng.randint(1, 3); shapes = [random_shape(rng, rng.randint(2, 6)) for _ in range(k)]
    gg = blank(h, w)
    if place_shapes(rng, gg, shapes, [rng.choice([c for c in COLOURS if c != 8]) for _ in range(k)], margin=0) is None: return None
    for r in range(h):
        for c in range(w):
            if gg[r][c]: g[r][c] = gg[r][c]
    return g if any(g[rw - 1][c] == 0 for c in range(w)) else None
def tf_tide(g):
    h, w = dims(g); rw = next(r for r in range(h) if 8 in g[r]); out = copy(g)
    for c in range(w):
        if out[rw - 1][c] == 0: out[rw - 1][c] = 8
    return out
rule("water_level_rises_one_row", "The water (colour 8) rises by one row: every empty cell in the row just above the surface becomes water; rocks stay dry.", gi_tide, tf_tide)


# 36 cells are drawn to a full grey magnet line from both sides.
def gi_magnet(rng):
    h, w = _size(rng, 7, 16); g = blank(h, w); rm = rng.randint(2, h - 3)
    for c in range(w): g[rm][c] = GREY
    for _ in range(rng.randint(4, h * w // 4)):
        r, c = rng.randrange(h), rng.randrange(w)
        if r != rm: g[r][c] = rng.choice([x for x in COLOURS if x != GREY])
    return g
def tf_magnet(g):
    h, w = dims(g); rm = next(r for r in range(h) if all(v == GREY for v in g[r])); out = blank(h, w)
    for c in range(w):
        out[rm][c] = GREY
        up = [g[r][c] for r in range(rm) if g[r][c]]; dn = [g[r][c] for r in range(rm + 1, h) if g[r][c]]
        for i, v in enumerate(reversed(up)): out[rm - 1 - i][c] = v
        for i, v in enumerate(dn): out[rm + 1 + i][c] = v
    return out
rule("cells_attracted_to_grey_magnet_line", "A full grey line is a magnet: cells above it fall onto it and cells below it rise onto it, stacking in their columns.", gi_magnet, tf_magnet)


# 37 each cell advances right by its colour value, wrapping.
def gi_advance(rng):
    h, w = _size(rng, 5, 14); g = blank(h, w)
    for _ in range(rng.randint(3, max(3, h * w // 16))):
        g[rng.randrange(h)][rng.randrange(w)] = rng.choice(COLOURS)
    return g
def tf_advance(g):
    h, w = dims(g); out = blank(h, w)
    for r, c in cells(g, lambda v: v != 0):
        nc = (c + g[r][c]) % w
        if out[r][nc]: return None
        out[r][nc] = g[r][c]
    return out
rule("cells_advance_right_by_colour_value", "Every cell moves right along its row by as many cells as its colour number, wrapping round at the right edge.", gi_advance, tf_advance, digits=True)


# 38 four coloured walls; each object slides to the wall of its own colour.
def gi_ownwall(rng):
    h, w = _size(rng, 9, 18); g = blank(h, w); wc = colours(rng, 4)
    for c in range(w): g[0][c] = wc[0]; g[h - 1][c] = wc[1]
    for r in range(h): g[r][0] = wc[2]; g[r][w - 1] = wc[3]
    k = rng.randint(1, 4); shapes = [random_shape(rng, rng.randint(1, 4)) for _ in range(k)]
    inner = blank(h - 4, w - 4)
    if place_shapes(rng, inner, shapes, [rng.choice(wc) for _ in range(k)], margin=1) is None: return None
    paste(g, inner, 2, 2, transparent=0)
    return g
def tf_ownwall(g):
    h, w = dims(g); out = copy(g)
    vec = {g[0][1]: (-1, 0), g[h - 1][1]: (1, 0), g[1][0]: (0, -1), g[1][w - 1]: (0, 1)}
    inner = [[g[r][c] if 0 < r < h - 1 and 0 < c < w - 1 else 0 for c in range(w)] for r in range(h)]
    obs = objects(inner, 0)
    def dist(o):
        dr, dc = vec[inner[o[0][0]][o[0][1]]]; r0, c0, r1, c1 = bbox(o)
        return {(-1, 0): r0, (1, 0): h - 1 - r1, (0, -1): c0, (0, 1): w - 1 - c1}[(dr, dc)]
    for o in sorted(obs, key=dist):
        col = inner[o[0][0]][o[0][1]]; dr, dc = vec[col]
        for r, c in o: out[r][c] = 0
        s = 0
        while all(out[r + (s + 1) * dr][c + (s + 1) * dc] == 0 for r, c in o): s += 1
        for r, c in o: out[r + s * dr][c + s * dc] = col
    return out
rule("objects_slide_to_wall_of_own_colour", "The four edges are walls of four colours; each object slides straight toward the wall of its own colour until it touches it or another object.", gi_ownwall, tf_ownwall)


# 39 hollow rings expand outward by one cell like a shock wave.
def gi_ringexp(rng):
    h, w = _size(rng, 7, 18); g = blank(h, w); n = 0
    for _ in range(rng.randint(1, 3)):
        s = rng.randint(1, 4); r0, c0 = rng.randint(1, h - s - 2), rng.randint(1, w - s - 2); r1, c1 = r0 + s, c0 + s
        if all(g[r][c] == 0 for r in range(max(0, r0 - 2), min(h, r1 + 3)) for c in range(max(0, c0 - 2), min(w, c1 + 3))):
            rect(g, r0, c0, r1, c1, rng.choice(COLOURS), fill=False); n += 1
    return g if n else None
def tf_ringexp(g):
    h, w = dims(g); out = blank(h, w)
    for o in objects(g, 0):
        r0, c0, r1, c1 = bbox(o)
        if r0 == 0 or c0 == 0 or r1 == h - 1 or c1 == w - 1: return None
        rect(out, r0 - 1, c0 - 1, r1 + 1, c1 + 1, g[o[0][0]][o[0][1]], fill=False)
    return out
rule("rings_expand_outward_one_cell", "Every hollow square ring spreads outward like a wave: it is redrawn one cell larger on every side and the old ring disappears.", gi_ringexp, tf_ringexp)


# 40 a mover cell pushes the block on its row to the right wall.
def gi_push(rng):
    h, w = _size(rng, 5, 16); g = blank(h, w); n = 0
    for r in rng.sample(range(h), rng.randint(1, h)):
        if w < 5: continue
        M, B = colours(rng, 2); c0 = rng.randrange(w - 3); c1 = rng.randint(c0 + 1, w - 2); L = rng.randint(1, min(3, w - 1 - c1))
        g[r][c0] = M
        for c in range(c1, c1 + L): g[r][c] = B
        if c1 + L < w or c1 > c0 + 1: n += 1
    return g if n else None
def tf_push(g):
    h, w = dims(g); out = blank(h, w)
    for r, row in enumerate(g):
        cs = [c for c, v in enumerate(row) if v]
        if not cs: continue
        M = row[cs[0]]; block = [row[c] for c in cs[1:]]
        if any(v == M for v in block): return None
        out[r][w - 1 - len(block)] = M
        for i, v in enumerate(block): out[r][w - len(block) + i] = v
    return out
rule("mover_pushes_block_to_right_wall", "On each row the leftmost cell is a pusher: it slides right, shoving the block ahead of it until the block is against the right wall.", gi_push, tf_push)
