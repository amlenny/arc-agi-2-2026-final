# b025_extrapolation.py -- SERIES AND EXTRAPOLATION: a few terms of a spatial series are shown; the output
# continues the series to the grid edge (or until the next term no longer fits).
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


def _sz(rng, lo=7, hi=20):
    """grid size with ~35% of draws in the 21-30 band."""
    if rng.random() < 0.35:
        return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _fits(H, W, r, c, h, w):
    return 0 <= r and r + h <= H and 0 <= c and c + w <= W


def _stamp(g, sh, r0, c0, col):
    for r, c in sh:
        g[r0 + r][c0 + c] = col


def _shape_hw(sh):
    return max(r for r, _ in sh) + 1, max(c for _, c in sh) + 1


def _norm(o):
    r0, c0, _, _ = bbox(o)
    return tuple(sorted((r - r0, c - c0) for r, c in o))


# ---------------------------------------------------------------- dots in a straight series, both directions
def _series_cells(g):
    pts = sorted(cells(g, lambda v: v != 0))
    if len(pts) < 2: return None
    dr, dc = pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]
    for i in range(2, len(pts)):
        if (pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]) != (dr, dc): return None
    return pts, (dr, dc)


def tf_dot_series(g):
    s = _series_cells(g)
    if s is None: return None
    pts, (dr, dc) = s; H, W = dims(g); out = copy(g)
    seq = [g[r][c] for r, c in pts]; n = len(seq)
    p = next(p for p in range(1, n + 1) if all(seq[i] == seq[i % p] for i in range(n)))
    r, c = pts[-1]; i = n
    while 0 <= r + dr < H and 0 <= c + dc < W:
        r += dr; c += dc; out[r][c] = seq[i % p]; i += 1
    r, c = pts[0]; i = 0
    while 0 <= r - dr < H and 0 <= c - dc < W:
        r -= dr; c -= dc; i -= 1; out[r][c] = seq[i % p]
    return out


def _gen_dots(rng, step, n, seqcols, H, W):
    """place n dots along `step` from a random start with room for one more term; None if impossible."""
    dr, dc = step
    for _ in range(60):
        r0, c0 = rng.randrange(H), rng.randrange(W)
        r_end, c_end = r0 + n * dr, c0 + n * dc
        if 0 <= r_end < H and 0 <= c_end < W:
            g = blank(H, W)
            for i in range(n):
                g[r0 + i * dr][c0 + i * dc] = seqcols[i % len(seqcols)]
            return g
    return None


def gi_ap_line(rng):
    H, W = _sz(rng); d = rng.randint(2, 5)
    step = (0, d) if rng.random() < 0.5 else (d, 0)
    return _gen_dots(rng, step, 3, [rng.choice(COLOURS)], H, W)
rule("ap_dots_line_continue", "Three equally spaced dots on one row or column are continued at the same spacing in both directions to the grid edges.", gi_ap_line, tf_dot_series)


def gi_ap_diag(rng):
    H, W = _sz(rng); d = rng.randint(1, 4)
    return _gen_dots(rng, (d, rng.choice([d, -d])), 3, [rng.choice(COLOURS)], H, W)
rule("ap_dots_diagonal_continue", "Three equally spaced dots on a diagonal are continued at the same spacing in both directions to the grid edges.", gi_ap_diag, tf_dot_series)


def gi_knight(rng):
    H, W = _sz(rng); a, b = rng.choice([(1, 2), (2, 1), (1, 3), (3, 1), (2, 3), (3, 2)])
    return _gen_dots(rng, (a, rng.choice([b, -b])), 3, [rng.choice(COLOURS)], H, W)
rule("knight_step_dots_continue", "Three dots each displaced from the last by the same uneven step (such as one down and two across) are continued with that step in both directions until the edge.", gi_knight, tf_dot_series)


def gi_alt_dots(rng):
    H, W = _sz(rng); d = rng.randint(1, 4)
    step = rng.choice([(0, d), (d, 0), (d, d), (d, -d)])
    return _gen_dots(rng, step, rng.randint(3, 4), colours(rng, 2), H, W)
rule("alternating_dots_spaced_continue", "Equally spaced dots alternating between two colours are continued in both directions to the edges, keeping the spacing and the alternation.", gi_alt_dots, tf_dot_series)


def gi_diag_cycle(rng):
    H, W = _sz(rng); k = rng.randint(3, 4)
    return _gen_dots(rng, (1, rng.choice([1, -1])), rng.randint(k + 1, k + 3), colours(rng, k), H, W)
rule("diagonal_colour_cycle_continue", "A diagonal line of cells whose colours repeat in a fixed cycle is extended in both directions to the edges, continuing the colour cycle.", gi_diag_cycle, tf_dot_series)


# ---------------------------------------------------------------- shape copies along a constant offset
def gi_shape_offset(rng):
    H, W = _sz(rng, 8); sh = random_shape(rng, rng.randint(2, 6)); h, w = _shape_hw(sh)
    for _ in range(60):
        dr, dc = rng.randint(-h - 2, h + 2), rng.randint(-w - 2, w + 2)
        if abs(dr) <= h and abs(dc) <= w: continue
        r0, c0 = rng.randrange(H), rng.randrange(W)
        if _fits(H, W, r0, c0, h, w) and _fits(H, W, r0 + dr, c0 + dc, h, w) and _fits(H, W, r0 + 2 * dr, c0 + 2 * dc, h, w):
            g = blank(H, W); col = rng.choice(COLOURS)
            _stamp(g, sh, r0, c0, col); _stamp(g, sh, r0 + dr, c0 + dc, col)
            return g
    return None
def tf_shape_offset(g):
    obs = objects(g, 0)
    if len(obs) != 2 or _norm(obs[0]) != _norm(obs[1]): return None
    sh = _norm(obs[0]); h, w = _shape_hw(sh); col = g[obs[0][0][0]][obs[0][0][1]]
    (r0, c0), (r1, c1) = sorted(bbox(o)[:2] for o in obs); dr, dc = r1 - r0, c1 - c0
    H, W = dims(g); out = copy(g); r, c = r1 + dr, c1 + dc
    while _fits(H, W, r, c, h, w):
        _stamp(out, sh, r, c, col); r += dr; c += dc
    r, c = r0 - dr, c0 - dc
    while _fits(H, W, r, c, h, w):
        _stamp(out, sh, r, c, col); r -= dr; c -= dc
    return out
rule("shape_two_copies_continue_offset", "A shape appears twice; further copies are drawn at that same displacement in both directions for as long as a whole copy fits in the grid.", gi_shape_offset, tf_shape_offset)


def gi_interp(rng):
    H, W = _sz(rng, 8); sh = random_shape(rng, rng.randint(2, 6)); h, w = _shape_hw(sh); n = rng.randint(2, 5)
    vert = rng.random() < 0.5; step = (h + 1, 0) if vert else (0, w + 1)
    for _ in range(60):
        r0, c0 = rng.randrange(H), rng.randrange(W)
        if _fits(H, W, r0, c0, h, w) and _fits(H, W, r0 + n * step[0], c0 + n * step[1], h, w):
            g = blank(H, W); col = rng.choice(COLOURS)
            _stamp(g, sh, r0, c0, col); _stamp(g, sh, r0 + n * step[0], c0 + n * step[1], col)
            return g
    return None
def tf_interp(g):
    obs = objects(g, 0)
    if len(obs) != 2 or _norm(obs[0]) != _norm(obs[1]): return None
    sh = _norm(obs[0]); h, w = _shape_hw(sh); col = g[obs[0][0][0]][obs[0][0][1]]
    (r0, c0), (r1, c1) = sorted(bbox(o)[:2] for o in obs)
    if r0 == r1 and (c1 - c0) % (w + 1) == 0: step, n = (0, w + 1), (c1 - c0) // (w + 1)
    elif c0 == c1 and (r1 - r0) % (h + 1) == 0: step, n = (h + 1, 0), (r1 - r0) // (h + 1)
    else: return None
    out = copy(g)
    for i in range(1, n):
        _stamp(out, sh, r0 + i * step[0], c0 + i * step[1], col)
    return out
rule("shape_copies_interpolate_between_ends", "The two copies of the shape are the first and last of a row of copies spaced one empty cell apart; the missing copies between them are drawn in.", gi_interp, tf_interp)


# ---------------------------------------------------------------- bars whose heights follow a series
def _bars(g):
    H, W = dims(g); hs = {}
    for c in range(W):
        k = sum(1 for r in range(H) if g[r][c] != 0)
        if k:
            if any(g[r][c] == 0 for r in range(H - k, H)): return None
            hs[c] = k
    cols = sorted(hs)
    if len(cols) < 2: return None
    s = cols[1] - cols[0]
    if any(cols[i + 1] - cols[i] != s for i in range(len(cols) - 1)): return None
    return cols, [hs[c] for c in cols], s, g[H - 1][cols[0]]


def _bars_continue(g, nxt):
    b = _bars(g)
    if b is None: return None
    cols, hs, s, col = b; H, W = dims(g); out = copy(g); c = cols[-1] + s
    while c < W:
        n = nxt(hs)
        if n < 1 or n > H: break
        hs.append(n)
        for r in range(H - n, H): out[r][c] = col
        c += s
    return out


def _gen_bars(rng, hs, H, W):
    s = rng.randint(1, 2); c0 = rng.randint(0, s)
    if c0 + len(hs) * s >= W or max(hs) > H: return None
    g = blank(H, W); col = rng.choice(COLOURS)
    for i, k in enumerate(hs):
        for r in range(H - k, H): g[r][c0 + i * s] = col
    return g


def gi_bars_ap(rng):
    H, W = _sz(rng); a, d = rng.randint(1, 3), rng.randint(1, 3)
    if a + 3 * d > H: return None
    return _gen_bars(rng, [a, a + d, a + 2 * d], H, W)
rule("bars_heights_ap_continue", "Three bars whose heights grow by a fixed amount are followed by more bars to the right, each taller by that same amount, until a bar would not fit the grid height or width.", gi_bars_ap, lambda g: _bars_continue(g, lambda hs: 2 * hs[-1] - hs[-2]))


_FIB = [1, 1, 2, 3, 5, 8, 13, 21, 34]
def gi_bars_fib(rng):
    H, W = _sz(rng); i = rng.randint(0, 2)
    if _FIB[i + 4] > H: return None
    return _gen_bars(rng, _FIB[i:i + 4], H, W)
rule("bars_fibonacci_heights_continue", "Each bar is as tall as the two bars before it together; more bars are added to the right following that rule until one would be taller than the grid.", gi_bars_fib, lambda g: _bars_continue(g, lambda hs: hs[-1] + hs[-2]))


def gi_bar_widths(rng):
    H, W = _sz(rng); hh = rng.randint(1, 4); w1 = rng.randint(1, 2); c0 = rng.randint(0, 2)
    ws = [w1, w1 + 1, w1 + 2]
    if c0 + sum(ws) + 3 + w1 + 3 > W: return None
    g = blank(H, W); col = rng.choice(COLOURS); c = c0
    for w in ws:
        rect(g, H - hh, c, H - 1, c + w - 1, col); c += w + 1
    return g
def tf_bar_widths(g):
    obs = sorted(objects(g, 0), key=lambda o: bbox(o)[1]); H, W = dims(g)
    if len(obs) < 2: return None
    r0, c0, r1, c1 = bbox(obs[-1]); w = c1 - c0 + 1; col = g[r0][c0]
    if w - (bbox(obs[-2])[3] - bbox(obs[-2])[1] + 1) != 1: return None
    out = copy(g); c = c1 + 2; w += 1
    while c + w <= W:
        rect(out, r0, c, r1, c + w - 1, col); c += w + 1; w += 1
    return out
rule("bar_widths_grow_continue", "Blocks of equal height standing side by side get one cell wider each time; more blocks are added to the right, each one wider than the last, as long as a whole block fits.", gi_bar_widths, tf_bar_widths)


# ---------------------------------------------------------------- spirals
def _spiral_in(H, W):
    dirs = [(0, 1), (1, 0), (0, -1), (-1, 0)]; path = [(0, 0)]; occ = {(0, 0)}; r = c = d = 0
    def blocked(r, c, d):
        nr, nc = r + dirs[d][0], c + dirs[d][1]
        if not (0 <= nr < H and 0 <= nc < W) or (nr, nc) in occ: return True
        return (nr + dirs[d][0], nc + dirs[d][1]) in occ
    while True:
        if blocked(r, c, d):
            d = (d + 1) % 4
            if blocked(r, c, d): break
        r += dirs[d][0]; c += dirs[d][1]; path.append((r, c)); occ.add((r, c))
    return path
def gi_spiral_in(rng):
    H, W = _sz(rng, 6); path = _spiral_in(H, W)
    if len(path) - 2 < H + W: return None
    k = rng.randint(H + W, len(path) - 2); g = blank(H, W); col = rng.choice(COLOURS)
    for r, c in path[:k]: g[r][c] = col
    return g
def tf_spiral_in(g):
    H, W = dims(g); col = max(v for row in g for v in row); out = blank(H, W)
    for r, c in _spiral_in(H, W): out[r][c] = col
    return out
rule("spiral_inward_continue", "A line that starts in the top-left corner and spirals clockwise inward along the edges, leaving one empty cell between its turns, is continued until it can go no further.", gi_spiral_in, tf_spiral_in)


def _spiral_out(H, W, r, c):
    dirs = [(0, 1), (1, 0), (0, -1), (-1, 0)]; path = [(r, c)]; L = 2; d = 0
    while True:
        for _ in range(L):
            r += dirs[d][0]; c += dirs[d][1]
            if not (0 <= r < H and 0 <= c < W): return path
            path.append((r, c))
        d = (d + 1) % 4
        if d % 2 == 0: L += 2
def gi_spiral_out(rng):
    H, W = _sz(rng, 8); r, c = rng.randint(2, H - 3), rng.randint(2, W - 3)
    path = _spiral_out(H, W, r, c)
    if len(path) - 2 < 9: return None
    k = rng.randint(9, len(path) - 2); g = blank(H, W); a, b = colours(rng, 2); g[r][c] = a
    for y, x in path[1:k]: g[y][x] = b
    return g
def tf_spiral_out(g):
    H, W = dims(g); cnt = counts(g); seed = [v for v, n in cnt.items() if v and n == 1]
    if len(seed) != 1: return None
    (r, c), = cells(g, lambda v: v == seed[0]); col = [v for v in cnt if v and v != seed[0]][0]
    out = copy(g)
    for y, x in _spiral_out(H, W, r, c)[1:]: out[y][x] = col
    return out
rule("spiral_outward_continue", "From the single seed cell a line spirals outward clockwise, each pair of arms two cells longer than the last so one empty cell separates the turns; it is continued until it reaches the grid edge.", gi_spiral_out, tf_spiral_out)


# ---------------------------------------------------------------- rows of boxes with a per-copy transformation
def _row_boxes(g):
    obs = objects(g, 0)
    if len(obs) < 2: return None
    items = sorted((bbox(o)[1], bbox(o)[0], crop(g, *bbox(o))) for o in obs)
    if len({it[1] for it in items}) != 1: return None
    steps = {items[i + 1][0] - items[i][0] for i in range(len(items) - 1)}
    if len(steps) != 1: return None
    return items, steps.pop()


def _extend_row(g, items, step, pat):
    H, W = dims(g); out = copy(g); r0 = items[0][1]; n = len(items)
    i, c = n, items[-1][0] + step
    while True:
        box = pat(i)
        if c + len(box[0]) > W: break
        paste(out, box, r0, c, transparent=0); c += step; i += 1
    i, c = -1, items[0][0] - step
    while c >= 0:
        paste(out, pat(i), r0, c, transparent=0); c -= step; i -= 1
    return out


def _full_box_shape(rng, n):
    """a shape that touches all four sides of its n x n box, with all four rotations and the mirror distinct."""
    for _ in range(100):
        sh = random_shape(rng, rng.randint(n + 1, n * n - 2), conn8=True)
        if _shape_hw(sh) != (n, n): continue
        box = blank(n, n)
        _stamp(box, sh, 0, 0, 1)
        rots = [box, rot90(box), rot90(rot90(box)), rot90(rot90(rot90(box)))]
        if len({str(b) for b in rots}) == 4 and flip_h(box) not in rots: return box
    return None


def _place_row(rng, H, W, boxes, step, need=1):
    """stamp boxes left to right at `step`, requiring room for `need` more copies beyond the last; None if no room."""
    n = len(boxes[0]); w = len(boxes[0][0])
    if W < (len(boxes) + need) * step - (step - w) or H < n: return None
    r0 = rng.randint(0, H - n); c0 = rng.randint(0, W - ((len(boxes) + need) * step - (step - w)))
    g = blank(H, W)
    for i, b in enumerate(boxes): paste(g, b, r0, c0 + i * step, transparent=0)
    return g


def _box_shape(rng, n, col):
    """a random connected shape stamped into an n x n box (bounding box within the box)."""
    for _ in range(100):
        sh = random_shape(rng, rng.randint(n, n * n - 1))
        if max(_shape_hw(sh)) <= n:
            box = blank(n, n); _stamp(box, sh, 0, 0, col); return box
    return None


def _recol(box, col):
    return [[col if v else 0 for v in row] for row in box]


def gi_rot_copies(rng):
    H, W = _sz(rng, 8); n = rng.randint(3, 4); box = _full_box_shape(rng, n)
    if box is None: return None
    box = _recol(box, rng.choice(COLOURS)); step = n + rng.randint(1, 2)
    return _place_row(rng, H, W, [box, rot90(box)], step)
def tf_rot_copies(g):
    rb = _row_boxes(g)
    if rb is None or len(rb[0]) != 2 or rot90(rb[0][0][2]) != rb[0][1][2]: return None
    b0 = rb[0][0][2]
    def pat(i):
        b = b0
        for _ in range(i % 4): b = rot90(b)
        return b
    return _extend_row(g, rb[0], rb[1], pat)
rule("shape_rotates_each_copy", "Each copy of the shape is a quarter turn clockwise from the copy to its left; more copies are added at the same spacing on both sides, each turned a further quarter.", gi_rot_copies, tf_rot_copies)


def gi_flip_copies(rng):
    H, W = _sz(rng, 8); n = rng.randint(3, 4); box = _full_box_shape(rng, n)
    if box is None: return None
    box = _recol(box, rng.choice(COLOURS)); step = n + rng.randint(1, 2)
    return _place_row(rng, H, W, [box, flip_h(box)], step)
def tf_flip_copies(g):
    rb = _row_boxes(g)
    if rb is None or len(rb[0]) != 2 or flip_h(rb[0][0][2]) != rb[0][1][2]: return None
    b0 = rb[0][0][2]
    return _extend_row(g, rb[0], rb[1], lambda i: b0 if i % 2 == 0 else flip_h(b0))
rule("shape_flips_each_copy", "Copies of a shape alternate between the shape and its left-right mirror; the row of copies is continued at the same spacing to both edges with the alternation kept.", gi_flip_copies, tf_flip_copies)


def gi_two_shapes_alt(rng):
    H, W = _sz(rng, 8); n = rng.randint(2, 4); a, b = colours(rng, 2)
    A, B = _box_shape(rng, n, a), _box_shape(rng, n, b)
    if A is None or B is None or _recol(A, 1) == _recol(B, 1): return None
    step = n + rng.randint(1, 2)
    return _place_row(rng, H, W, [A, B, A], step)
def tf_two_shapes_alt(g):
    rb = _row_boxes(g)
    if rb is None: return None
    items, step = rb
    if len(items) != 3 or items[0][2] != items[2][2] or items[0][2] == items[1][2]: return None
    return _extend_row(g, items, step, lambda i: items[i % 2][2])
rule("two_shapes_alternate_continue", "Two different shapes take turns along a row (first, second, first); the row is continued to both edges at the same spacing, still taking turns.", gi_two_shapes_alt, tf_two_shapes_alt)


def gi_colour_cycle_copies(rng):
    H, W = _sz(rng, 8); n = rng.randint(2, 3); k = rng.randint(2, 3); cols = colours(rng, k)
    box = _box_shape(rng, n, 1)
    if box is None: return None
    step = n + rng.randint(1, 2)
    return _place_row(rng, H, W, [_recol(box, cols[i % k]) for i in range(k + 1)], step)
def tf_colour_cycle_copies(g):
    rb = _row_boxes(g)
    if rb is None: return None
    items, step = rb; seq = [max(v for row in it[2] for v in row) for it in items]; n = len(seq)
    p = next(p for p in range(1, n + 1) if all(seq[i] == seq[i % p] for i in range(n)))
    if p == n: return None
    box = items[0][2]
    return _extend_row(g, items, step, lambda i: _recol(box, seq[i % p]))
rule("shape_copies_colour_cycle_continue", "Identical copies of a shape stand in a row with colours repeating in a cycle; copies are added at the same spacing to both edges, continuing the colour cycle.", gi_colour_cycle_copies, tf_colour_cycle_copies)


# ---------------------------------------------------------------- staircases, squares, pyramids
def gi_stair_widths(rng):
    H, W = _sz(rng, 6); k = rng.randint(3, 5); c0 = rng.randint(0, 2)
    if c0 + (k + 1) * (k + 2) // 2 > W or k + 1 > H: return None
    g = blank(H, W); col = rng.choice(COLOURS)
    for j in range(1, k + 1):
        x = c0 + j * (j - 1) // 2; rect(g, H - j, x, H - 1, x + j - 1, col)
    return g
def tf_stair_widths(g):
    H, W = dims(g); pts = cells(g, lambda v: v != 0); c0 = min(c for _, c in pts); col = g[pts[0][0]][pts[0][1]]
    out = copy(g); j = 1
    while c0 + j * (j - 1) // 2 + j <= W and j <= H:
        x = c0 + j * (j - 1) // 2; rect(out, H - j, x, H - 1, x + j - 1, col); j += 1
    return out
rule("staircase_step_width_grows", "A staircase rising from the floor whose steps are 1, 2, 3... cells wide and as tall as they are wide is continued to the right while a whole step still fits.", gi_stair_widths, tf_stair_widths)


def gi_grow_squares(rng):
    H, W = _sz(rng, 6); s1 = rng.randint(1, 2); c0 = rng.randint(0, 2); rb = rng.randint(s1 + 3, H - 1)
    ss = [s1, s1 + 1, s1 + 2]
    if c0 + sum(ss) + 3 + ss[-1] + 1 > W: return None
    g = blank(H, W); col = rng.choice(COLOURS); c = c0
    for s in ss:
        rect(g, rb - s + 1, c, rb, c + s - 1, col); c += s + 1
    return g
def tf_grow_squares(g):
    obs = sorted(objects(g, 0), key=lambda o: bbox(o)[1]); H, W = dims(g)
    if len(obs) < 2: return None
    r0, c0, rb, c1 = bbox(obs[-1]); s = c1 - c0 + 1; col = g[rb][c0]
    if s - (bbox(obs[-2])[3] - bbox(obs[-2])[1] + 1) != 1: return None
    out = copy(g); c = c1 + 2; s += 1
    while c + s <= W and rb - s + 1 >= 0:
        rect(out, rb - s + 1, c, rb, c + s - 1, col); c += s + 1; s += 1
    return out
rule("growing_squares_continue", "Filled squares standing on a common baseline grow by one cell a side from left to right; the next larger squares are added to the right while they fit.", gi_grow_squares, tf_grow_squares)


def _apex_rows(g, draw):
    H, W = dims(g); pts = cells(g, lambda v: v != 0); r0 = min(r for r, _ in pts)
    top = [c for r, c in pts if r == r0]
    if len(top) != 1: return None
    c = top[0]; col = g[r0][c]; out = copy(g); k = 0
    while r0 + k < H and c - k >= 0 and c + k < W:
        draw(out, r0 + k, c, k, col); k += 1
    return out
def _gen_apex(rng, draw):
    H, W = _sz(rng, 6); m = rng.randint(3, 4)
    if H < m + 1 or W < 2 * m + 1: return None
    r0 = rng.randint(0, H - m - 1); c = rng.randint(m, W - m - 1); g = blank(H, W); col = rng.choice(COLOURS)
    for k in range(m): draw(g, r0 + k, c, k, col)
    return g
def _draw_dots(g, r, c, k, col):
    for j in range(-k, k + 1, 2): g[r][c + j] = col
def _draw_solid(g, r, c, k, col):
    for j in range(-k, k + 1): g[r][c + j] = col
rule("triangle_dot_rows_continue", "Below the apex each row holds one more dot than the row above, the dots two cells apart and centred under the apex; rows are added downward while they fit.", lambda rng: _gen_apex(rng, _draw_dots), lambda g: _apex_rows(g, _draw_dots))
rule("pyramid_rows_continue_down", "A solid pyramid whose rows widen by one cell on each side is continued downward row by row while a whole row still fits in the grid.", lambda rng: _gen_apex(rng, _draw_solid), lambda g: _apex_rows(g, _draw_solid))


# ---------------------------------------------------------------- zigzag and sawtooth paths
def gi_zigzag(rng):
    H, W = _sz(rng, 7); a = rng.randint(1, 5)
    if H < a + 1 or W < 2 * a + 4: return None
    rlo = rng.randint(0, H - a - 1); r = rlo + rng.randint(0, a); d = rng.choice([-1, 1])
    k = rng.randint(2 * a + 2, W - 2); g = blank(H, W); col = rng.choice(COLOURS)
    for c in range(k):
        g[r][c] = col
        if r == rlo: d = 1
        if r == rlo + a: d = -1
        r += d
    return g
def tf_zigzag(g):
    H, W = dims(g); pts = sorted(cells(g, lambda v: v != 0), key=lambda p: p[1])
    if len(pts) < 3 or len({c for _, c in pts}) != len(pts): return None
    rlo, rhi = min(r for r, _ in pts), max(r for r, _ in pts); col = g[pts[0][0]][pts[0][1]]
    (rp, _), (r, c) = pts[-2], pts[-1]; d = r - rp
    if r == rlo: d = 1
    if r == rhi: d = -1
    out = copy(g)
    for x in range(c + 1, W):
        r += d; out[r][x] = col
        if r == rlo: d = 1
        if r == rhi: d = -1
    return out
rule("zigzag_path_continue", "A diagonal path that bounces between a top and bottom level, forming a zigzag, is continued to the right edge with the same levels.", gi_zigzag, tf_zigzag)


def gi_sawtooth(rng):
    H, W = _sz(rng, 7); b = rng.randint(2, 5)
    if H < b + 2 or W < b + 4: return None
    ra = rng.randint(0, H - b - 2); rb = ra + b + 1; g = blank(H, W); col = rng.choice([c for c in COLOURS if c != 5])
    for c in range(W): g[ra][c] = 5; g[rb][c] = 5
    s = rng.randrange(b); k = rng.randint(b + 1, W - 2)
    for c in range(k): g[ra + 1 + (s + c) % b][c] = col
    return g
def tf_sawtooth(g):
    H, W = dims(g); walls = [r for r in range(H) if all(v == 5 for v in g[r])]
    if len(walls) != 2: return None
    ra, rb = walls; pts = sorted(cells(g, lambda v: v not in (0, 5)), key=lambda p: p[1])
    if not pts: return None
    r, c = pts[-1]; col = g[r][c]; out = copy(g)
    for x in range(c + 1, W):
        r = r + 1 if r + 1 < rb else ra + 1; out[r][x] = col
    return out
rule("sawtooth_between_walls_continue", "Between two grey wall rows a path runs diagonally down and right; on reaching the lower wall it restarts just below the upper wall in the next column, and this sawtooth is continued to the right edge.", gi_sawtooth, tf_sawtooth)


# ---------------------------------------------------------------- numeric series (digits)
def gi_pascal(rng):
    H, W = _sz(rng, 4); g = blank(H, W); g[0] = [rng.randint(1, 9) for _ in range(W)]
    g[1] = [((g[0][c - 1] if c else 0) + g[0][c]) % 10 for c in range(W)]
    return g if H >= 4 else None
def tf_pascal(g):
    H, W = dims(g); out = copy(g)
    for r in range(1, H):
        out[r] = [((out[r - 1][c - 1] if c else 0) + out[r - 1][c]) % 10 for c in range(W)]
    return out if out != g else None
rule("pascal_rows_mod_ten_continue", "Each cell is the last digit of the sum of the cell directly above it and the cell above-left; the first two rows are given and the rule fills every row below.", gi_pascal, tf_pascal, digits=True)


def gi_countdown(rng):
    H, W = _sz(rng, 4); g = blank(H, W); tops = [rng.choice([0, 0] + list(range(2, 10))) for _ in range(W)]
    if max(tops) < 3: return None
    for c, n in enumerate(tops):
        if n: g[0][c] = n; g[1][c] = n - 1
    return g
def tf_countdown(g):
    H, W = dims(g); out = copy(g)
    for c in range(W):
        n = g[0][c]
        for r in range(H):
            out[r][c] = n - r if n and n - r >= 1 else 0
    return out
rule("columns_count_down_from_top_digit", "Each column counts down from its top digit, one less per row, and stops after reaching 1; the first two rows are given and the countdown is completed.", gi_countdown, tf_countdown, digits=True)


def gi_digit_rows_ap(rng):
    H, W = _sz(rng, 5); g = blank(H, W); rows = rng.sample(range(H), rng.randint(1, min(4, H))); grown = False
    for r in rows:
        a, d, c0 = rng.randint(1, 4), rng.randint(1, 3), rng.randint(0, min(2, W - 4))
        if a + 2 * d > 9: d = 1
        for i in range(3): g[r][c0 + i] = a + i * d
        grown = grown or (a + 3 * d <= 9 and c0 + 3 < W)
    return g if grown else None
def tf_digit_rows_ap(g):
    H, W = dims(g); out = copy(g)
    for r in range(H):
        cs = [c for c in range(W) if g[r][c]]
        if len(cs) < 2: continue
        d = g[r][cs[1]] - g[r][cs[0]]; v = g[r][cs[-1]]; c = cs[-1] + 1
        while c < W and 1 <= v + d <= 9:
            v += d; out[r][c] = v; c += 1
    return out
rule("digit_rows_arith_continue", "Each row's run of digits rises by a fixed step; the run is extended to the right with that step until the next digit would exceed 9 or the row ends.", gi_digit_rows_ap, tf_digit_rows_ap, digits=True)


# ---------------------------------------------------------------- dot spacing series along one line
def _dots_extend(g, nxt):
    pts = cells(g, lambda v: v != 0); H, W = dims(g)
    rows, colsx = {r for r, _ in pts}, {c for _, c in pts}
    if len(rows) == 1: axis, pos, lim = 0, sorted(colsx), W
    elif len(colsx) == 1: axis, pos, lim = 1, sorted(rows), H
    else: return None
    gaps = [pos[i + 1] - pos[i] for i in range(len(pos) - 1)]
    if len(gaps) < 2: return None
    sign = 1
    if gaps[-1] < gaps[0]: pos, gaps, sign = pos[::-1], gaps[::-1], -1
    out = copy(g); col = g[pts[0][0]][pts[0][1]]; p = pos[-1]
    while True:
        gaps.append(nxt(gaps)); p += sign * gaps[-1]
        if not 0 <= p < lim: break
        if axis == 0: out[pts[0][0]][p] = col
        else: out[p][pts[0][1]] = col
    return out
def _gen_gaps(rng, gaps, need):
    H, W = _sz(rng, 6); L = sum(gaps) + need
    if max(H, W) <= L: return None
    vert = rng.random() < 0.5
    if vert: H, W = max(H, W), min(H, W)
    else: H, W = min(H, W), max(H, W)
    lim = H if vert else W
    if lim <= L: return None
    p0 = rng.randint(0, lim - L - 1); idx = rng.randrange(W if vert else H); g = blank(H, W); col = rng.choice(COLOURS)
    pos = [p0] + [p0 + sum(gaps[:i + 1]) for i in range(len(gaps))]
    if rng.random() < 0.5: pos = [lim - 1 - p for p in pos]
    for p in pos:
        if vert: g[p][idx] = col
        else: g[idx][p] = col
    return g
rule("dots_doubling_spacing_continue", "Along one line the gap between successive dots doubles each time; more dots are added in that direction, each gap twice the last, until the edge.",
     lambda rng: (lambda d: _gen_gaps(rng, [d, 2 * d], 4 * d))(rng.randint(1, 2)), lambda g: _dots_extend(g, lambda gs: 2 * gs[-1]))
rule("dots_spacing_grows_by_one_continue", "Along one line each gap between dots is one cell longer than the gap before; more dots are added in that direction with ever longer gaps until the edge.",
     lambda rng: (lambda s: _gen_gaps(rng, [s, s + 1, s + 2], s + 3))(rng.randint(1, 3)), lambda g: _dots_extend(g, lambda gs: gs[-1] + 1))
rule("dots_fibonacci_spacing_continue", "Along one line each gap between dots is the sum of the two gaps before it (1, 1, 2, 3, 5...); more dots are added in that direction by the same rule until the edge.",
     lambda rng: _gen_gaps(rng, [1, 1, 2], 3), lambda g: _dots_extend(g, lambda gs: gs[-1] + gs[-2]))


# ---------------------------------------------------------------- frames, rings, corner arms
def gi_frames_gap(rng):
    H = rng.randint(13, 30); W = rng.randint(13, 30); cr, cc = rng.randint(3, H - 4), rng.randint(3, W - 4)
    rad = [1, 3, 6, 10, 15, 21]; fit = [x for x in rad if cr - x >= 0 and cr + x < H and cc - x >= 0 and cc + x < W]
    if len(fit) < 3: return None
    shown = fit[:rng.randint(2, len(fit) - 1)]; g = blank(H, W); a, b = colours(rng, 2); g[cr][cc] = a
    for x in shown: rect(g, cr - x, cc - x, cr + x, cc + x, b, fill=False)
    return g
def tf_frames_gap(g):
    H, W = dims(g); cnt = counts(g); seed = [v for v, n in cnt.items() if v and n == 1]
    if len(seed) != 1: return None
    (cr, cc), = cells(g, lambda v: v == seed[0]); b = [v for v in cnt if v and v != seed[0]][0]; out = copy(g)
    for x in [1, 3, 6, 10, 15, 21]:
        if cr - x >= 0 and cr + x < H and cc - x >= 0 and cc + x < W: rect(out, cr - x, cc - x, cr + x, cc + x, b, fill=False)
    return out
rule("frames_increasing_gap_continue", "Square frames around the centre cell lie at distances 1, 3, 6, 10... (each gap one larger than the last); every further frame that fits entirely in the grid is added.", gi_frames_gap, tf_frames_gap)


def gi_rings_alt(rng):
    H, W = _sz(rng, 7); cr, cc = rng.randint(2, H - 3), rng.randint(2, W - 3); a, b = colours(rng, 2); g = blank(H, W)
    for x in (2, 1, 0): rect(g, cr - x, cc - x, cr + x, cc + x, (a, b)[x % 2])
    return g
def tf_rings_alt(g):
    H, W = dims(g); r0, c0, r1, c1 = bbox(cells(g, lambda v: v != 0))
    if r1 - r0 != 4 or c1 - c0 != 4: return None
    cr, cc = r0 + 2, c0 + 2; a, b = g[cr][cc], g[cr - 1][cc]
    return [[(a, b)[max(abs(r - cr), abs(c - cc)) % 2] for c in range(W)] for r in range(H)]
rule("rings_alternate_outward_continue", "Square rings around the centre cell alternate between two colours; the rings are continued outward in the same alternation until the whole grid is covered.", gi_rings_alt, tf_rings_alt)


def _arms(g, s, a, b):
    H, W = dims(g); k = 0
    while k < max(H, W):
        col = (a, b)[(k // s) % 2]
        for c in range(min(k, W - 1) + 1):
            if k < H: g[k][c] = col
        for r in range(min(k, H - 1) + 1):
            if k < W: g[r][k] = col
        k += s
    return g
def gi_corner_arms(rng):
    H, W = _sz(rng, 7); s = rng.randint(2, 3)
    if 3 * s >= max(H, W): return None
    a, b = colours(rng, 2); g = _arms(blank(H, W), s, a, b)
    for k in range(3 * s, max(H, W)):
        for c in range(W):
            if k < H: g[k][c] = 0
        for r in range(H):
            if k < W: g[r][k] = 0
    return g
def tf_corner_arms(g):
    s = next(c for c in range(1, len(g[0])) if g[0][c] != 0 and g[0][c] != g[0][0]) if any(g[0][c] != 0 and g[0][c] != g[0][0] for c in range(1, len(g[0]))) else None
    if s is None: return None
    return _arms(copy(g), s, g[0][0], g[0][s])
rule("corner_arms_alternating_continue", "L-shaped arms spread from the top-left corner at a fixed spacing, alternating between two colours; the series of arms is continued at that spacing and alternation to the far edges.", gi_corner_arms, tf_corner_arms)


# ---------------------------------------------------------------- serpentine path
def _serp(H, W):
    path = []
    for r in range(0, H, 2):
        cs = list(range(W)) if (r // 2) % 2 == 0 else list(range(W - 1, -1, -1))
        path += [(r, c) for c in cs]
        if r + 1 < H: path.append((r + 1, cs[-1]))
    return path
def gi_serp(rng):
    H, W = _sz(rng, 5); path = _serp(H, W)
    if len(path) - 2 < W + 2: return None
    k = rng.randint(W + 2, len(path) - 2); g = blank(H, W); col = rng.choice(COLOURS)
    for r, c in path[:k]: g[r][c] = col
    return g
def tf_serp(g):
    H, W = dims(g); col = max(v for row in g for v in row); out = blank(H, W)
    for r, c in _serp(H, W): out[r][c] = col
    return out
rule("serpentine_path_continue", "A path fills every other row completely, alternating left-to-right and right-to-left, stepping down through the row between at the end of each pass; it is continued to the bottom of the grid.", gi_serp, tf_serp)


# ---------------------------------------------------------------- widths and gaps that grow
def gi_widths_double(rng):
    H, W = _sz(rng, 7); w1 = rng.randint(1, 3); s = rng.randint(1, 2)
    if 8 * w1 > W or 3 * s + 1 > H: return None
    r0 = rng.randint(0, H - 3 * s - 1); g = blank(H, W); col = rng.choice(COLOURS)
    for i in range(3): rect(g, r0 + i * s, 0, r0 + i * s, w1 * 2 ** i - 1, col)
    return g
def tf_widths_double(g):
    H, W = dims(g); rows = [r for r in range(H) if any(g[r])]
    if len(rows) < 2: return None
    s = rows[1] - rows[0]; w = sum(1 for v in g[rows[-1]] if v); col = g[rows[0]][0]; out = copy(g); r = rows[-1] + s
    while r < H and 2 * w <= W:
        w *= 2; rect(out, r, 0, r, w - 1, col); r += s
    return out
rule("widths_double_each_row_continue", "Left-aligned bars on evenly spaced rows double in length from one to the next; further bars are added below while the doubled bar still fits.", gi_widths_double, tf_widths_double)


def gi_dashes(rng):
    H, W = _sz(rng, 6); l1 = rng.randint(1, 2); c0 = rng.randint(0, 2); ls = [l1, l1 + 1, l1 + 2]
    if c0 + sum(ls) + 3 + l1 + 3 > W: return None
    r = rng.randrange(H); g = blank(H, W); col = rng.choice(COLOURS); c = c0
    for L in ls:
        for x in range(L): g[r][c + x] = col
        c += L + 1
    return g
def tf_dashes(g):
    H, W = dims(g); rows = [r for r in range(H) if any(g[r])]
    if len(rows) != 1: return None
    r = rows[0]; runs = [len(o) for o in sorted(components(g, lambda v: v != 0), key=lambda o: o[0][1])]
    if len(runs) < 2 or runs[-1] - runs[-2] != 1: return None
    col = next(v for v in g[r] if v); c = max(c for c in range(W) if g[r][c]) + 2; L = runs[-1] + 1; out = copy(g)
    while c + L <= W:
        for x in range(L): out[r][c + x] = col
        c += L + 1; L += 1
    return out
rule("dash_lengths_grow_continue", "Dashes along one row separated by single gaps grow one cell longer each time; further dashes are added to the right while a whole dash fits.", gi_dashes, tf_dashes)


def gi_gap_grows(rng):
    H, W = _sz(rng, 8); sh = random_shape(rng, rng.randint(2, 5)); h, w = _shape_hw(sh)
    if 4 * w + 6 > W or h > H: return None
    r0 = rng.randint(0, H - h); c0 = rng.randint(0, W - 4 * w - 6); g = blank(H, W); col = rng.choice(COLOURS); c = c0
    for gap in (1, 2, 3):
        _stamp(g, sh, r0, c, col); c += w + gap
    return g
def tf_gap_grows(g):
    obs = sorted(objects(g, 0), key=lambda o: bbox(o)[1])
    if len(obs) < 3 or len({_norm(o) for o in obs}) != 1: return None
    sh = _norm(obs[0]); h, w = _shape_hw(sh); H, W = dims(g); col = g[obs[0][0][0]][obs[0][0][1]]
    r0 = bbox(obs[0])[0]; gap = bbox(obs[-1])[1] - bbox(obs[-2])[3] - 1; c = bbox(obs[-1])[1]; out = copy(g)
    while True:
        gap += 1; c += w + gap
        if c + w > W: break
        _stamp(out, sh, r0, c, col)
    return out
rule("shape_copies_gap_grows_continue", "Copies of a shape along a row are separated by gaps of 1, 2, 3... cells; more copies are added to the right with each gap one wider, while they fit.", gi_gap_grows, tf_gap_grows)


def gi_lines_gaps(rng):
    H, W = _sz(rng, 10); r0 = rng.randint(0, 2)
    if r0 + 9 >= H: return None
    g = blank(H, W); col = rng.choice(COLOURS)
    for r in (r0, r0 + 2, r0 + 5): g[r] = [col] * W
    return transpose(g) if rng.random() < 0.5 else g
def tf_lines_gaps(g):
    H, W = dims(g); t = False
    if not any(all(v for v in row) for row in g):
        g = transpose(g); H, W = W, H; t = True
    rows = [r for r in range(H) if all(g[r])]
    if len(rows) < 3: return None
    gap = rows[-1] - rows[-2]; r = rows[-1]; col = g[r][0]; out = copy(g)
    while True:
        gap += 1; r += gap
        if r >= H: break
        out[r] = [col] * W
    return transpose(out) if t else out
rule("lines_gaps_grow_continue", "Full-length parallel lines are separated by 1, then 2, then 3 empty lines; further lines are added in the same direction with each gap one larger, until the edge.", gi_lines_gaps, tf_lines_gaps)


def gi_stripes_widen(rng):
    H, W = _sz(rng, 8); w1 = rng.randint(1, 2); a, b = colours(rng, 2)
    if 3 * w1 + 3 + 1 > W: return None
    g = blank(H, W); c = 0
    for i, w in enumerate((w1, w1 + 1, w1 + 2)):
        rect(g, 0, c, H - 1, c + w - 1, (a, b)[i % 2]); c += w
    return g
def tf_stripes_widen(g):
    H, W = dims(g); row = g[0]; runs = []
    for c in range(W):
        if not row[c]: break
        if runs and runs[-1][0] == row[c]: runs[-1][1] += 1
        else: runs.append([row[c], 1])
    if len(runs) != 3 or runs[2][1] - runs[1][1] != 1: return None
    c = sum(n for _, n in runs); w = runs[-1][1]; i = 3; out = copy(g)
    while c < W:
        w += 1; rect(out, 0, c, H - 1, min(W - 1, c + w - 1), runs[i % 2][0]); c += w; i += 1
    return out
rule("stripes_widening_continue", "Vertical stripes from the left edge alternate between two colours and each is one cell wider than the last; the stripes are continued to the right edge, the last one cut off where the grid ends.", gi_stripes_widen, tf_stripes_widen)


# ---------------------------------------------------------------- rays, bouncing copies, lattices
def gi_v_rays(rng):
    H, W = _sz(rng, 8); d = rng.randint(1, 3)
    if H < 3 * d + 2 or W < 4 * d + 1: return None
    r0 = rng.randint(0, H - 3 * d - 2); c0 = rng.randint(2 * d, W - 2 * d - 1)
    if c0 < 3 * d and c0 + 3 * d >= W: return None
    a, b = colours(rng, 2); g = blank(H, W); g[r0][c0] = a
    for i in (1, 2):
        g[r0 + i * d][c0 - i * d] = b; g[r0 + i * d][c0 + i * d] = b
    return g
def tf_v_rays(g):
    H, W = dims(g); pts = cells(g, lambda v: v != 0); r0 = min(r for r, _ in pts); top = [(r, c) for r, c in pts if r == r0]
    if len(top) != 1: return None
    _, c0 = top[0]; below = sorted((r, c) for r, c in pts if r > r0)
    if not below: return None
    d = below[0][0] - r0; col = g[below[0][0]][below[0][1]]; out = copy(g)
    for sgn in (-1, 1):
        i = 1
        while r0 + i * d < H and 0 <= c0 + sgn * i * d < W:
            out[r0 + i * d][c0 + sgn * i * d] = col; i += 1
    return out
rule("v_rays_dots_continue", "From the apex two diagonal rays of evenly spaced dots run down-left and down-right; both rays are continued at that spacing until they leave the grid.", gi_v_rays, tf_v_rays)


def _bounce_path(H, W, sh, r, c, dr, dc):
    h, w = _shape_hw(sh); out = []
    while True:
        r += dr; nc = c + dc
        if nc < 0 or nc + w > W:
            dc = -dc; nc = c + dc
            if nc < 0 or nc + w > W: break
        c = nc
        if r + h > H: break
        out.append((r, c))
    return out
def gi_bounce_copies(rng):
    H, W = _sz(rng, 8); sh = random_shape(rng, rng.randint(1, 4)); h, w = _shape_hw(sh)
    if h > 2 or w > 2: return None
    dr = rng.randint(h + 1, h + 3); dc = rng.choice([-1, 1]) * rng.randint(1, 4)
    if W < w + abs(dc) + 1 or H < 3 * dr + h: return None
    r0 = rng.randint(0, H - 3 * dr - h); c0 = rng.randint(max(0, -dc), min(W - w, W - w - dc))
    g = blank(H, W); col = rng.choice(COLOURS); _stamp(g, sh, r0, c0, col); _stamp(g, sh, r0 + dr, c0 + dc, col)
    return g if _bounce_path(H, W, sh, r0 + dr, c0 + dc, dr, dc) else None
def tf_bounce_copies(g):
    obs = objects(g, 0)
    if len(obs) != 2 or _norm(obs[0]) != _norm(obs[1]): return None
    sh = _norm(obs[0]); col = g[obs[0][0][0]][obs[0][0][1]]; H, W = dims(g)
    (r0, c0), (r1, c1) = sorted(bbox(o)[:2] for o in obs)
    if r1 == r0: return None
    out = copy(g)
    for r, c in _bounce_path(H, W, sh, r1, c1, r1 - r0, c1 - c0): _stamp(out, sh, r, c, col)
    return out
rule("shape_copies_bounce_off_sides", "The shape keeps moving down the grid by the same step as between its two shown copies, reversing its sideways direction whenever the next step would cross the left or right edge, until it runs off the bottom.", gi_bounce_copies, tf_bounce_copies)


def gi_lattice(rng):
    H, W = _sz(rng, 9); sh = random_shape(rng, rng.randint(1, 5)); h, w = _shape_hw(sh)
    if h > 3 or w > 3: return None
    dr, dc = rng.randint(h + 1, h + 4), rng.randint(w + 1, w + 4)
    if H < 2 * dr + h or W < 2 * dc + w: return None
    r0 = rng.randint(0, H - dr - h); c0 = rng.randint(0, W - dc - w); g = blank(H, W); col = rng.choice(COLOURS)
    for r, c in ((r0, c0), (r0, c0 + dc), (r0 + dr, c0)): _stamp(g, sh, r, c, col)
    return g
def tf_lattice(g):
    obs = objects(g, 0)
    if len(obs) != 3 or len({_norm(o) for o in obs}) != 1: return None
    sh = _norm(obs[0]); h, w = _shape_hw(sh); col = g[obs[0][0][0]][obs[0][0][1]]; H, W = dims(g)
    ps = [bbox(o)[:2] for o in obs]
    anchor = next((p for p in ps if sum(q[0] == p[0] for q in ps) == 2 and sum(q[1] == p[1] for q in ps) == 2), None)
    if anchor is None: return None
    dr = next(abs(q[0] - anchor[0]) for q in ps if q[1] == anchor[1] and q != anchor)
    dc = next(abs(q[1] - anchor[1]) for q in ps if q[0] == anchor[0] and q != anchor)
    out = copy(g)
    for i in range(-(H // dr) - 1, H // dr + 2):
        for j in range(-(W // dc) - 1, W // dc + 2):
            r, c = anchor[0] + i * dr, anchor[1] + j * dc
            if _fits(H, W, r, c, h, w): _stamp(out, sh, r, c, col)
    return out
rule("shape_lattice_from_three_copies", "Three copies of a shape mark a corner of a regular grid of copies, one neighbour across and one down; the copies are repeated at that spacing over the whole grid wherever a copy fits.", gi_lattice, tf_lattice)
