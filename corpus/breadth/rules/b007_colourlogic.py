# b007_colourlogic.py -- colour logic and conditionals: recolour by neighbourhood, by legend permutation,
# by parity, by distance bands, by row/column facts, by touching chains. 40 rules.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

N4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
N8 = N4 + [(-1, -1), (-1, 1), (1, -1), (1, 1)]
NDIAG = [(-1, -1), (-1, 1), (1, -1), (1, 1)]


def _size(rng, lo=5, hi=20):
    """Grid size; about 35% of inputs land in the 21-30 band where ARC-AGI-2 lives."""
    if rng.random() < 0.35:
        return rng.randint(21, 30), rng.randint(21, 30)
    return size(rng, lo, hi)


def _nbrs(g, r, c, nb=N4):
    H, W = dims(g)
    return [(r + dy, c + dx) for dy, dx in nb if 0 <= r + dy < H and 0 <= c + dx < W]


def _blobs(g, bg=0, conn8=True):
    """Connected components of non-bg cells regardless of colour (glib.components splits by colour)."""
    H, W = dims(g); seen, out = set(), []; nb = N8 if conn8 else N4
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or (r, c) in seen: continue
            comp, st = [], [(r, c)]; seen.add((r, c))
            while st:
                y, x = st.pop(); comp.append((y, x))
                for ny, nx in _nbrs(g, y, x, nb):
                    if (ny, nx) not in seen and g[ny][nx] != bg:
                        seen.add((ny, nx)); st.append((ny, nx))
            out.append(comp)
    return out


def _scatter(rng, h, w, k, cols):
    g = blank(h, w)
    for r, c in rng.sample([(r, c) for r in range(h) for c in range(w)], min(k, h * w)):
        g[r][c] = rng.choice(cols)
    return g


def _scene(rng, k_lo=2, k_hi=5, n_lo=3, n_hi=8, lo=6, hi=18, margin=1, cols=None):
    h, w = _size(rng, lo, hi); g = blank(h, w); k = rng.randint(k_lo, k_hi)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    cs = [rng.choice(cols or COLOURS) for _ in range(k)]
    return g if place_shapes(rng, g, shapes, cs, margin=margin) is not None else None


def _rects(rng, lo=6, hi=18, k_lo=2, k_hi=5, cols=None, margin=1, side=(2, 5)):
    h, w = _size(rng, lo, hi); g = blank(h, w); k = rng.randint(k_lo, k_hi)
    shapes = [[(r, c) for r in range(rng.randint(*side)) for c in range(rng.randint(*side))] for _ in range(k)]
    cs = [rng.choice(cols or COLOURS) for _ in range(k)]
    return g if place_shapes(rng, g, shapes, cs, margin=margin) is not None else None


def _colour_of(g, o):
    return g[o[0][0]][o[0][1]]


# 1 cells on a colour boundary turn grey.
def gi_boundary(rng):
    h, w = _size(rng, 6, 16); g = blank(h, w); cols = colours(rng, rng.randint(2, 4), exclude=(0, 5))
    for _ in range(rng.randint(3, 7)):
        r0, c0 = rng.randrange(h), rng.randrange(w); r1, c1 = min(h - 1, r0 + rng.randint(1, 5)), min(w - 1, c0 + rng.randint(1, 5))
        rect(g, r0, c0, r1, c1, rng.choice(cols))
    return g
def tf_boundary(g):
    out = copy(g)
    for (r, c) in cells(g, lambda v: v != 0):
        if any(g[y][x] != 0 and g[y][x] != g[r][c] for y, x in _nbrs(g, r, c)):
            out[r][c] = 5
    return out
rule("touching_different_colour_becomes_grey", "Every coloured cell that shares a side with a cell of a different colour turns grey (5).", gi_boundary, tf_boundary)


# 2 empty cells count the distinct colours around them.
def gi_distinct_nb(rng):
    h, w = _size(rng, 5, 14); return _scatter(rng, h, w, rng.randint(3, h * w // 5), colours(rng, rng.randint(2, 5)))
def tf_distinct_nb(g):
    out = copy(g)
    for (r, c) in cells(g, lambda v: v == 0):
        k = len({g[y][x] for y, x in _nbrs(g, r, c, N8) if g[y][x]})
        if k: out[r][c] = k
    return out
rule("empty_cell_counts_distinct_neighbour_colours", "Each empty cell becomes the number of distinct colours among its eight neighbours; cells with no coloured neighbour stay empty.", gi_distinct_nb, tf_distinct_nb, digits=True)


# 3 the top row lists a colour cycle; every field colour advances one step.
def gi_cycle(rng):
    h, w = _size(rng, 7, 16); k = rng.randint(2, min(5, w)); cols = colours(rng, k, exclude=(0, 5))
    g = _scatter(rng, h, w, rng.randint(h, h * w // 3), cols)
    g[0] = [0] * w; g[1] = [5] * w
    for i, c in enumerate(cols): g[0][i] = c
    return g if any(v for row in g[2:] for v in row) else None
def tf_cycle(g):
    cols = [v for v in g[0] if v]; nxt = {c: cols[(i + 1) % len(cols)] for i, c in enumerate(cols)}
    out = copy(g)
    for r in range(2, len(g)):
        out[r] = [nxt.get(v, v) for v in g[r]]
    return out
rule("legend_row_cycles_colours", "The colours listed in the top row form a cycle; below the separator every cell of one listed colour becomes the next colour in the list, the last wrapping to the first.", gi_cycle, tf_cycle)


# 4 checkerboard parity recolour.
def gi_parity(rng):
    return _scene(rng, 2, 5, 3, 9, cols=[c for c in COLOURS if c > 2])
def tf_parity(g):
    return [[(1 if (r + c) % 2 == 0 else 2) if v else 0 for c, v in enumerate(row)] for r, row in enumerate(g)]
rule("coloured_cells_by_diagonal_parity", "Every coloured cell becomes 1 if its row plus column index is even and 2 if odd, like a checkerboard stencil.", gi_parity, tf_parity)


# 5 distance bands around objects.
def gi_bands(rng):
    return _scene(rng, 1, 3, 2, 6, 8, 16, margin=3, cols=[c for c in COLOURS if c > 3])
def tf_bands(g):
    H, W = dims(g); out = copy(g); occ = cells(g, lambda v: v != 0)
    for r in range(H):
        for c in range(W):
            if g[r][c]: continue
            d = min(max(abs(r - y), abs(c - x)) for y, x in occ)
            if d <= 3: out[r][c] = d
    return out
rule("chebyshev_bands_around_objects", "Empty cells one step from any object become 1, two steps become 2, three steps become 3 (king moves); farther cells stay empty.", gi_bands, tf_bands, digits=True)


# 6/7 lattice of rectangles; each takes the colour of the one above / to the left.
def _lattice(rng):
    big = rng.random() < 0.4
    R, C = (rng.randint(4, 6), rng.randint(4, 6)) if big else (rng.randint(2, 4), rng.randint(2, 4))
    ch, cw = rng.randint(3, min(7, 29 // R)), rng.randint(3, min(7, 29 // C))
    h, w = R * ch + 1, C * cw + 1; g = blank(h, w); n = 0
    for i in range(R):
        for j in range(C):
            if rng.random() < 0.8:
                a, b = rng.randint(1, ch - 1), rng.randint(1, cw - 1)
                rect(g, 1 + i * ch, 1 + j * cw, i * ch + a, j * cw + b, rng.choice(COLOURS)); n += 1
    return g if n >= 3 else None
def _take_from(g, axis):
    obs = objects(g, 0, conn8=False); out = copy(g); boxes = [bbox(o) for o in obs]
    for o, (r0, c0, r1, c1) in zip(obs, boxes):
        best = None
        for p, (q0, p0, q1, p1) in zip(obs, boxes):
            if axis == 0 and q1 < r0 and not (p1 < c0 or p0 > c1) and (best is None or q1 > best[1]): best = (p, q1)
            if axis == 1 and p1 < c0 and not (q1 < r0 or q0 > r1) and (best is None or p1 > best[1]): best = (p, p1)
        if best:
            for r, c in o: out[r][c] = _colour_of(g, best[0])
    return out
rule("object_takes_colour_of_object_above", "Each rectangle is recoloured with the colour of the nearest rectangle directly above it; rectangles with nothing above keep their colour.", _lattice, lambda g: _take_from(g, 0))
rule("object_takes_colour_of_object_left", "Each rectangle is recoloured with the colour of the nearest rectangle directly to its left; rectangles with nothing to the left keep their colour.", _lattice, lambda g: _take_from(g, 1))


# 8 invert each object within its bounding box.
def gi_invert(rng):
    g = _scene(rng, 2, 5, 3, 8, margin=2)
    if g is None: return None
    boxes = [bbox(o) for o in objects(g, 0)]
    for i, (a0, b0, a1, b1) in enumerate(boxes):
        for (c0, d0, c1, d1) in boxes[i + 1:]:
            if not (a1 < c0 or c1 < a0 or b1 < d0 or d1 < b0): return None
    return g
def tf_invert(g):
    out = copy(g)
    for o in objects(g, 0):
        col = _colour_of(g, o); r0, c0, r1, c1 = bbox(o)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                out[r][c] = 0 if g[r][c] else col
    return out
rule("invert_each_object_in_bbox", "Inside each object's bounding box the filled cells become empty and the empty cells take the object's colour.", gi_invert, tf_invert)


# 9/10 rows judged by whether they hold a key colour.
def gi_keyrows(rng):
    h, w = _size(rng, 5, 14); cols = colours(rng, rng.randint(2, 4), exclude=(0, 2, 3, 8)) + [2, 3]
    return _scatter(rng, h, w, rng.randint(h, h * w // 3), cols)
def tf_rows_filled(g):
    return [[(8 if v == 0 else v) for v in row] if 2 in row else row[:] for row in g]
def tf_rows_cleared(g):
    return [row[:] if 3 in row else [0] * len(row) for row in g]
rule("rows_holding_colour_two_filled_grey", "Every row that contains a colour-2 cell has its empty cells painted 8; other rows are untouched.", gi_keyrows, tf_rows_filled)
rule("rows_lacking_colour_three_cleared", "Every row that contains no colour-3 cell is wiped empty; rows holding a 3 are kept as they are.", gi_keyrows, tf_rows_cleared)


# 11 row colour and column colour agree -> paint.
def gi_agree(rng):
    h, w = _size(rng, 5, 14); cols = colours(rng, rng.randint(2, 3), exclude=(0, 5)); g = blank(h, w)
    for r in range(1, h): g[r][0] = rng.choice(cols)
    for c in range(1, w): g[0][c] = rng.choice(cols)
    g[0][0] = 5
    return g
def tf_agree(g):
    out = copy(g)
    for r in range(1, len(g)):
        for c in range(1, len(g[0])):
            if g[r][0] == g[0][c]: out[r][c] = g[r][0]
    return out
rule("row_column_colour_agreement", "The left column colours each row and the top row colours each column; an interior cell is painted where its row colour equals its column colour.", gi_agree, tf_agree)


# 12 A->B inside frames, B->A outside.
def gi_frames_ab(rng):
    h, w = _size(rng, 9, 18); g = blank(h, w); a, b = colours(rng, 2, exclude=(0, 5)); n = 0
    for _ in range(40):
        r0, c0 = rng.randint(0, h - 5), rng.randint(0, w - 5); r1, c1 = rng.randint(r0 + 3, min(h - 1, r0 + 8)), rng.randint(c0 + 3, min(w - 1, c0 + 8))
        if all(g[r][c] == 0 for r in range(max(0, r0 - 1), min(h, r1 + 2)) for c in range(max(0, c0 - 1), min(w, c1 + 2))):
            rect(g, r0, c0, r1, c1, 5, fill=False); n += 1
        if n >= rng.randint(1, 2): break
    if not n: return None
    for r, c in rng.sample(cells(g, lambda v: v == 0), rng.randint(6, max(6, h * w // 5))):
        g[r][c] = rng.choice([a, b])
    g[0][0], g[0][1] = a, b
    return g
def _inside_frames(g):
    H, W = dims(g); ins = set()
    for o in components(g, 5, conn8=False):
        r0, c0, r1, c1 = bbox(o)
        if len(o) == 2 * (r1 - r0 + c1 - c0):
            ins |= {(r, c) for r in range(r0 + 1, r1) for c in range(c0 + 1, c1)}
    return ins
def tf_frames_ab(g):
    a, b = g[0][0], g[0][1]; ins = _inside_frames(g); out = copy(g)
    for r in range(1, len(g)):
        for c in range(len(g[0])):
            v = g[r][c]
            if (r, c) in ins and v == a: out[r][c] = b
            elif (r, c) not in ins and v == b: out[r][c] = a
    return out
rule("swap_ab_inside_frames_ba_outside", "The two cells at the top-left name colours A then B: inside the grey frames every A becomes B, outside the frames every B becomes A.", gi_frames_ab, tf_frames_ab)


# 13 each coloured cell becomes its row's distinct-colour count.
def gi_rowdistinct(rng):
    h, w = _size(rng, 5, 14); return _scatter(rng, h, w, rng.randint(h, h * w // 3), colours(rng, rng.randint(2, 6)))
def tf_rowdistinct(g):
    out = []
    for row in g:
        k = len({v for v in row if v}); out.append([k if v else 0 for v in row])
    return out
rule("cells_become_row_distinct_colour_count", "Every coloured cell is replaced by the number of distinct colours present in its row.", gi_rowdistinct, tf_rowdistinct, digits=True)


# 14 colour spreads along chains of touching grey cells.
def gi_chain(rng):
    h, w = _size(rng, 6, 14); g = blank(h, w); p = rng.uniform(0.3, 0.5)
    for r in range(h):
        for c in range(w):
            if rng.random() < p: g[r][c] = 5
    blobs = [b for b in _blobs(g, conn8=False) if len(b) >= 3]
    if not blobs: return None
    cols = colours(rng, min(len(blobs), rng.randint(1, 3)), exclude=(0, 5))
    for b, col in zip(rng.sample(blobs, len(cols)), cols):
        r, c = rng.choice(b); g[r][c] = col
    return g
def tf_chain(g):
    out = copy(g)
    for b in _blobs(g, conn8=False):
        seeds = {g[r][c] for r, c in b if g[r][c] != 5}
        if len(seeds) > 1: return None
        if seeds:
            col = seeds.pop()
            for r, c in b: out[r][c] = col
    return out
rule("colour_spreads_along_touching_grey_chain", "A coloured cell passes its colour to every grey cell linked to it through a side-touching chain of grey cells; grey chains with no coloured cell stay grey.", gi_chain, tf_chain)


# 15 grey cells adopt the one colour around them.
def gi_sole(rng):
    h, w = _size(rng, 5, 14); g = _scatter(rng, h, w, rng.randint(3, h * w // 4), colours(rng, rng.randint(2, 4), exclude=(0, 5)))
    return sprinkle(rng, g, rng.randint(3, h * w // 4), 5)
def tf_sole(g):
    out = copy(g)
    for (r, c) in cells(g, lambda v: v == 5):
        s = {g[y][x] for y, x in _nbrs(g, r, c, N8) if g[y][x] not in (0, 5)}
        if len(s) == 1: out[r][c] = s.pop()
    return out
rule("grey_cells_take_sole_neighbour_colour", "A grey cell whose eight neighbours show exactly one non-grey colour takes that colour; grey cells with no or several neighbouring colours stay grey.", gi_sole, tf_sole)


# 16 neighbour-count parity.
def gi_nbparity(rng):
    h, w = _size(rng, 5, 14); col = rng.choice([c for c in COLOURS if c > 2]); g = blank(h, w); p = rng.uniform(0.25, 0.5)
    for r in range(h):
        for c in range(w):
            if rng.random() < p: g[r][c] = col
    return g if any(v for row in g for v in row) else None
def tf_nbparity(g):
    out = copy(g)
    for (r, c) in cells(g, lambda v: v != 0):
        n = sum(1 for y, x in _nbrs(g, r, c, N8) if g[y][x])
        out[r][c] = 1 if n % 2 else 2
    return out
rule("cell_recolour_by_neighbour_count_parity", "Every coloured cell becomes 1 if it has an odd number of coloured neighbours (eight directions) and 2 if even.", gi_nbparity, tf_nbparity)


# 17 quadrant recolour.
def gi_quad(rng):
    h, w = _size(rng, 6, 18); h -= h % 2; w -= w % 2; g = blank(h, w)
    shapes = [random_shape(rng, rng.randint(2, 7)) for _ in range(rng.randint(2, 6))]
    cs = [rng.choice([c for c in COLOURS if c > 4]) for _ in shapes]
    return g if place_shapes(rng, g, shapes, cs) is not None else None
def tf_quad(g):
    H, W = dims(g)
    return [[(1 + (2 if r >= H // 2 else 0) + (1 if c >= W // 2 else 0)) if v else 0 for c, v in enumerate(row)] for r, row in enumerate(g)]
rule("colour_by_quadrant", "Every coloured cell is recoloured by the quarter of the grid it lies in: top-left 1, top-right 2, bottom-left 3, bottom-right 4.", gi_quad, tf_quad)


# 18 colours ranked by frequency.
def gi_rank(rng):
    h, w = _size(rng, 5, 14); g = _scatter(rng, h, w, rng.randint(4, h * w // 3), colours(rng, rng.randint(2, 5)))
    cnt = counts(g); cnt.pop(0, None)
    return g if len(cnt) >= 2 and len(set(cnt.values())) == len(cnt) else None
def tf_rank(g):
    cnt = counts(g); cnt.pop(0, None); order = sorted(cnt, key=lambda c: -cnt[c]); m = {c: i + 1 for i, c in enumerate(order)}
    return [[m.get(v, 0) for v in row] for row in g]
rule("colours_ranked_by_frequency", "The most frequent colour becomes 1, the next most frequent 2, and so on; the cell layout is unchanged.", gi_rank, tf_rank, digits=True)


# 19 row majority fills the row's empties.
def gi_rowmaj(rng):
    h, w = _size(rng, 4, 12); g = blank(h, w); cols = colours(rng, rng.randint(2, 4))
    for r in range(h):
        if rng.random() < 0.3: continue
        dom = rng.choice(cols); n = rng.randint(2, max(2, w // 2))
        for c in rng.sample(range(w), min(w, n + rng.randint(0, 2))):
            g[r][c] = dom
        for c in rng.sample(range(w), rng.randint(0, 1)):
            g[r][c] = rng.choice(cols)
    return g
def tf_rowmaj(g):
    out = []
    for row in g:
        cnt = {}
        for v in row:
            if v: cnt[v] = cnt.get(v, 0) + 1
        top = sorted(cnt.items(), key=lambda kv: -kv[1])
        if top and (len(top) == 1 or top[0][1] > top[1][1]):
            out.append([top[0][0] if v == 0 else v for v in row])
        else:
            out.append(row[:])
    return out
rule("row_majority_colour_fills_row_empties", "In each row the colour with the most cells fills the row's empty cells; rows that are empty or tied are left alone.", gi_rowmaj, tf_rowmaj)


# 20 objects recoloured by how many other objects they touch.
def gi_touch(rng):
    g = _rects(rng, 7, 16, 3, 7, margin=0, side=(1, 4))
    return g if g is not None and len(objects(g, 0, conn8=False)) >= 2 else None
def tf_touch(g):
    obs = objects(g, 0, conn8=False); out = copy(g); sets = [set(o) for o in obs]
    for i, o in enumerate(obs):
        halo = {(y, x) for r, c in o for y, x in _nbrs(g, r, c, N8)} - sets[i]
        n = sum(1 for j, s in enumerate(sets) if j != i and halo & s)
        for r, c in o: out[r][c] = min(9, n + 1)
    return out
rule("objects_recolour_by_touch_count", "Each rectangle is recoloured with one plus the number of other rectangles it touches (corners count).", gi_touch, tf_touch, digits=True)


# 21 single gaps between like colours.
def gi_gaps(rng):
    h, w = _size(rng, 6, 15); g = blank(h, w)
    for _ in range(rng.randint(2, 6)):
        col = rng.choice(COLOURS)
        if rng.random() < 0.5:
            r = rng.randrange(h); a = rng.randrange(w - 2); b = rng.randint(a + 2, w - 1)
            for c in range(a, b + 1): g[r][c] = col
            for c in range(a + 1, b, 2):
                if rng.random() < 0.5: g[r][c] = 0
        else:
            c = rng.randrange(w); a = rng.randrange(h - 2); b = rng.randint(a + 2, h - 1)
            for r in range(a, b + 1): g[r][c] = col
            for r in range(a + 1, b, 2):
                if rng.random() < 0.5: g[r][c] = 0
    return g
def tf_gaps(g):
    H, W = dims(g); out = copy(g)
    for r in range(H):
        for c in range(W):
            if g[r][c]: continue
            if 0 < c < W - 1 and g[r][c - 1] and g[r][c - 1] == g[r][c + 1]: out[r][c] = g[r][c - 1]
            elif 0 < r < H - 1 and g[r - 1][c] and g[r - 1][c] == g[r + 1][c]: out[r][c] = g[r - 1][c]
    return out
rule("fill_single_gaps_between_same_colour", "An empty cell whose left and right neighbours are the same colour, or whose upper and lower neighbours are, takes that colour.", gi_gaps, tf_gaps)


# 22 distance to border.
def gi_border_d(rng):
    h, w = _size(rng, 6, 16); return _scatter(rng, h, w, rng.randint(h, h * w // 3), [c for c in COLOURS if c > 4])
def tf_border_d(g):
    H, W = dims(g)
    return [[(min(r, c, H - 1 - r, W - 1 - c, 3) + 1) if v else 0 for c, v in enumerate(row)] for r, row in enumerate(g)]
rule("recolour_by_distance_to_border", "Every coloured cell becomes 1 on the grid edge, 2 one step in, 3 two steps in, and 4 anywhere deeper.", gi_border_d, tf_border_d, digits=True)


# 23 complement colours.
def gi_compl(rng):
    return _scene(rng, 2, 6, 2, 8, cols=[c for c in COLOURS if c != 5])
def tf_compl(g):
    return [[10 - v if v else 0 for v in row] for row in g]
rule("complement_colours_ten_minus", "Every coloured cell of value c becomes 10 minus c, so 1 and 9, 2 and 8, 3 and 7, 4 and 6 swap.", gi_compl, tf_compl, digits=True, primitive=True)


# 24 rarest colour becomes commonest.
def gi_rarest(rng):
    h, w = _size(rng, 5, 14); g = _scatter(rng, h, w, rng.randint(6, h * w // 3), colours(rng, rng.randint(3, 5)))
    cnt = counts(g); cnt.pop(0, None); vals = sorted(cnt.values())
    return g if len(vals) >= 3 and vals[0] < vals[1] and vals[-1] > vals[-2] else None
def tf_rarest(g):
    cnt = counts(g); cnt.pop(0, None); lo = min(cnt, key=cnt.get); hi = max(cnt, key=cnt.get)
    return [[hi if v == lo else v for v in row] for row in g]
rule("rarest_colour_becomes_commonest", "All cells of the colour with the fewest cells are repainted in the colour with the most cells.", gi_rarest, tf_rarest)


# 25 grey object takes the colour of the one object touching it.
def gi_greytouch(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w); taken = set(); n = 0
    for _ in range(rng.randint(2, 5)):
        for _t in range(30):
            a, b = rng.randint(1, 3), rng.randint(1, 3); a2, b2 = rng.randint(1, 3), rng.randint(1, 3)
            r0, c0 = rng.randrange(h), rng.randrange(w); horiz = rng.random() < 0.5
            r1, c1 = (r0, c0 + b) if horiz else (r0 + a, c0)
            A = {(r0 + i, c0 + j) for i in range(a) for j in range(b)}; B = {(r1 + i, c1 + j) for i in range(a2) for j in range(b2)}
            foot = {(y + dy, x + dx) for y, x in A | B for dy in (-1, 0, 1) for dx in (-1, 0, 1)}
            if all(0 <= y < h and 0 <= x < w for y, x in A | B) and not (foot & taken):
                taken |= foot; col = rng.choice([c for c in COLOURS if c != 5])
                for y, x in A: g[y][x] = col
                for y, x in B: g[y][x] = 5
                n += 1; break
    return g if n else None
def tf_greytouch(g):
    out = copy(g)
    for o in components(g, 5, conn8=False):
        s = {g[y][x] for r, c in o for y, x in _nbrs(g, r, c) if g[y][x] not in (0, 5)}
        if len(s) == 1:
            col = s.pop()
            for r, c in o: out[r][c] = col
    return out
# grey_object_takes_touching_colour dropped 2026-10-12 (behavioural duplicate of colour_spreads_along_touching_grey_chain)
# 26 objects alternate the two corner colours left to right.
def gi_alt(rng):
    h, w = _size(rng, 7, 18); g = blank(h, w); a, b = colours(rng, 2, exclude=(0, 5)); k = rng.randint(2, 6)
    shapes = [random_shape(rng, rng.randint(2, 6)) for _ in range(k)]
    sub = blank(h - 2, w)
    if place_shapes(rng, sub, shapes, [5] * k) is None: return None
    obs = objects(sub, 0); lefts = sorted(bbox(o)[1] for o in obs)
    if len(set(lefts)) != len(lefts): return None
    g[0][0], g[0][w - 1] = a, b
    for r in range(h - 2): g[r + 2] = sub[r]
    return g
def tf_alt(g):
    a, b = g[0][0], g[0][-1]; out = copy(g)
    for i, o in enumerate(sorted(components(g, 5, conn8=True), key=lambda o: bbox(o)[1])):
        for r, c in o: out[r][c] = a if i % 2 == 0 else b
    return out
rule("objects_alternate_two_corner_colours", "Going left to right, the grey objects are painted alternately with the top-left corner colour and the top-right corner colour.", gi_alt, tf_alt)


# 27 each coloured cell becomes its column's fill count.
def gi_colcount(rng):
    h, w = _size(rng, 4, 12); g = _scatter(rng, h, w, rng.randint(w, min(h * w // 3, 4 * w)), colours(rng, rng.randint(1, 4)))
    return g if all(sum(1 for r in range(h) if g[r][c]) <= 9 for c in range(w)) else None
def tf_colcount(g):
    H, W = dims(g); n = [sum(1 for r in range(H) if g[r][c]) for c in range(W)]
    return [[n[c] if v else 0 for c, v in enumerate(row)] for row in g]
rule("cells_become_column_fill_count", "Every coloured cell is replaced by the number of coloured cells in its column.", gi_colcount, tf_colcount, digits=True)


# 28 row takes leftmost colour.
def gi_leftmost(rng):
    h, w = _size(rng, 4, 14); return _scatter(rng, h, w, rng.randint(h, h * w // 2), colours(rng, rng.randint(2, 5)))
def tf_leftmost(g):
    out = []
    for row in g:
        first = next((v for v in row if v), 0); out.append([first if v else 0 for v in row])
    return out
rule("row_takes_leftmost_colour", "All coloured cells in a row are repainted with the colour of that row's leftmost coloured cell.", gi_leftmost, tf_leftmost)


# 29 row takes its majority colour.
def gi_rowmaj2(rng):
    return gi_rowmaj(rng)
def tf_rowmaj2(g):
    out = []
    for row in g:
        cnt = {}
        for v in row:
            if v: cnt[v] = cnt.get(v, 0) + 1
        top = sorted(cnt.items(), key=lambda kv: -kv[1])
        if not top: out.append(row[:]); continue
        if len(top) > 1 and top[0][1] == top[1][1]: return None
        out.append([top[0][0] if v else 0 for v in row])
    return out
rule("row_takes_majority_colour", "All coloured cells in a row are repainted with the colour that occurs most often in that row.", gi_rowmaj2, tf_rowmaj2)


# 30 halo around colour 2.
def gi_halo(rng):
    h, w = _size(rng, 5, 14); cols = colours(rng, rng.randint(1, 3), exclude=(0, 2, 8)) + [2]
    g = _scatter(rng, h, w, rng.randint(2, h * w // 6), cols)
    return g if any(v == 2 for row in g for v in row) else None
def tf_halo(g):
    out = copy(g)
    for (r, c) in cells(g, lambda v: v == 2):
        for y, x in _nbrs(g, r, c, N8):
            if g[y][x] == 0: out[y][x] = 8
    return out
rule("halo_around_colour_two", "Every empty cell touching a colour-2 cell, including diagonally, is painted 8; other colours get no halo.", gi_halo, tf_halo)


# 31 invert rows with a left grey marker.
def gi_invrows(rng):
    h, w = _size(rng, 4, 12); g = blank(h, w); m = 0
    for r in range(h):
        col = rng.choice([c for c in COLOURS if c != 5])
        for c in rng.sample(range(1, w), rng.randint(1, w - 2)): g[r][c] = col
        if rng.random() < 0.5: g[r][0] = 5; m += 1
    return g if 0 < m else None
def tf_invrows(g):
    out = copy(g)
    for r, row in enumerate(g):
        if row[0] != 5: continue
        s = {v for v in row[1:] if v}
        if len(s) != 1: return None
        col = s.pop(); out[r] = [5] + [0 if v else col for v in row[1:]]
    return out
rule("invert_rows_with_left_grey_marker", "In every row whose first cell is grey, the coloured cells become empty and the empty cells take that row's colour; unmarked rows stay.", gi_invrows, tf_invrows)


# 32 fill row/column crossings of a colour.
def gi_cross(rng):
    h, w = _size(rng, 6, 14); cols = colours(rng, rng.randint(1, 3)); g = blank(h, w)
    for col in cols:
        for r, c in rng.sample([(r, c) for r in range(h) for c in range(w)], rng.randint(2, 4)): g[r][c] = col
    return g
def tf_cross(g):
    H, W = dims(g); out = copy(g); cs = sorted({v for row in g for v in row if v})
    rows = {c: {r for r in range(H) if c in g[r]} for c in cs}; colsets = {c: {x for x in range(W) if any(g[r][x] == c for r in range(H))} for c in cs}
    for r in range(H):
        for c in range(W):
            if g[r][c]: continue
            q = [k for k in cs if r in rows[k] and c in colsets[k]]
            if len(q) == 1: out[r][c] = q[0]
    return out
rule("fill_row_column_crossings_of_colour", "An empty cell is painted colour c when some cell of c lies in its row and some cell of c lies in its column; cells claimed by two colours stay empty.", gi_cross, tf_cross)


# 33 edge cells vs interior cells of objects.
def gi_edgeint(rng):
    return _rects(rng, 6, 16, 1, 4, cols=[c for c in COLOURS if c > 2], side=(3, 6))
def tf_edgeint(g):
    H, W = dims(g); out = copy(g)
    for (r, c) in cells(g, lambda v: v != 0):
        nb = _nbrs(g, r, c)
        out[r][c] = 2 if len(nb) == 4 and all(g[y][x] == g[r][c] for y, x in nb) else 1
    return out
rule("object_edge_cells_one_interior_two", "Coloured cells with same-coloured neighbours on all four sides become 2; every other coloured cell becomes 1.", gi_edgeint, tf_edgeint)


# 34 Manhattan parity rings from seeds.
def gi_manh(rng):
    h, w = _size(rng, 5, 13); return _scatter(rng, h, w, rng.randint(1, 4), [c for c in COLOURS if c > 2])
def tf_manh(g):
    H, W = dims(g); seeds = cells(g, lambda v: v != 0); out = copy(g)
    for r in range(H):
        for c in range(W):
            if g[r][c]: continue
            d = min(abs(r - y) + abs(c - x) for y, x in seeds); out[r][c] = 1 if d % 2 else 2
    return out
rule("manhattan_parity_rings_from_seeds", "Every empty cell is coloured 1 if its step distance to the nearest seed is odd and 2 if even, forming diamond rings; seeds stay.", gi_manh, tf_manh)


# 35 grey takes nearest colour in its row.
def gi_rownear(rng):
    h, w = _size(rng, 4, 14); g = _scatter(rng, h, w, rng.randint(h, h * w // 3), colours(rng, rng.randint(2, 4), exclude=(0, 5)))
    return sprinkle(rng, g, rng.randint(2, h * w // 4), 5)
def tf_rownear(g):
    out = copy(g); W = len(g[0])
    for r, row in enumerate(g):
        for c, v in enumerate(row):
            if v != 5: continue
            best = sorted((abs(c - x), x) for x in range(W) if row[x] not in (0, 5))
            if best and (len(best) == 1 or best[0][0] != best[1][0]): out[r][c] = row[best[0][1]]
    return out
rule("grey_takes_nearest_colour_in_row", "Each grey cell takes the colour of the nearest coloured cell in its own row; grey cells with no nearest or an equidistant pair stay grey.", gi_rownear, tf_rownear)


# 36 colour-count parity.
def gi_cntpar(rng):
    h, w = _size(rng, 5, 14); return _scatter(rng, h, w, rng.randint(4, h * w // 3), colours(rng, rng.randint(2, 5), exclude=(0, 1, 2)))
def tf_cntpar(g):
    cnt = counts(g)
    return [[(1 if cnt[v] % 2 else 2) if v else 0 for v in row] for row in g]
rule("odd_count_colours_one_even_two", "Every cell whose colour appears an odd number of times in the grid becomes 1; cells of colours appearing an even number of times become 2.", gi_cntpar, tf_cntpar)


# 37 shift colours by marker count.
_RING = [1, 2, 3, 4, 6, 7, 8, 9]
def gi_shift(rng):
    h, w = _size(rng, 6, 15); k = rng.randint(1, min(4, w)); g = _scatter(rng, h, w, rng.randint(h, h * w // 3), rng.sample(_RING, rng.randint(2, 4)))
    g[0] = [5] * k + [0] * (w - k)
    return g if any(v for row in g[1:] for v in row) else None
def tf_shift(g):
    k = sum(1 for v in g[0] if v == 5); out = copy(g)
    for r in range(1, len(g)):
        out[r] = [_RING[(_RING.index(v) + k) % 8] if v else 0 for v in g[r]]
    return out
rule("shift_colours_by_grey_marker_count", "Count the grey cells in the top row; every field colour advances that many steps along the sequence 1 2 3 4 6 7 8 9, wrapping around.", gi_shift, tf_shift, digits=True)


# 38 fill the centre of an X.
def gi_xcentre(rng):
    h, w = _size(rng, 6, 15); g = blank(h, w); taken = set(); n = 0
    for _ in range(rng.randint(1, 5)):
        for _t in range(30):
            r, c = rng.randint(1, h - 2), rng.randint(1, w - 2); pts = {(r + dy, c + dx) for dy, dx in NDIAG} | {(r, c)}
            foot = {(y + dy, x + dx) for y, x in pts for dy in (-1, 0, 1) for dx in (-1, 0, 1)}
            if not (foot & taken):
                taken |= foot; col = rng.choice(COLOURS)
                for y, x in pts - {(r, c)}: g[y][x] = col
                n += 1; break
    return sprinkle(rng, g, rng.randint(0, 4), rng.choice(COLOURS)) if n else None
def tf_xcentre(g):
    H, W = dims(g); out = copy(g)
    for r in range(1, H - 1):
        for c in range(1, W - 1):
            if g[r][c] == 0:
                s = {g[r + dy][c + dx] for dy, dx in NDIAG}
                if len(s) == 1 and 0 not in s: out[r][c] = s.pop()
    return out
rule("fill_centre_of_four_diagonal_cells", "An empty cell whose four diagonal neighbours all share one colour is filled with that colour, completing the X.", gi_xcentre, tf_xcentre)


# 39 later duplicates in a row turn grey.
def gi_dupgrey(rng):
    h, w = _size(rng, 4, 12); return _scatter(rng, h, w, rng.randint(h * 2, h * w // 2), colours(rng, rng.randint(2, 4), exclude=(0, 5)))
def tf_dupgrey(g):
    out = []
    for row in g:
        seen = set(); new = []
        for v in row:
            new.append(5 if v and v in seen else v); seen.add(v)
        out.append(new)
    return out
rule("later_duplicates_in_row_turn_grey", "Reading each row left to right, the first cell of each colour keeps its colour and every later cell of that colour turns grey.", gi_dupgrey, tf_dupgrey)


# 40 objects recoloured by how many objects share their colour.
def gi_groupsize(rng):
    h, w = _size(rng, 8, 18); g = blank(h, w); k = rng.randint(3, 8); cols = colours(rng, rng.randint(1, 3))
    shapes = [random_shape(rng, rng.randint(2, 6)) for _ in range(k)]
    if place_shapes(rng, g, shapes, [rng.choice(cols) for _ in range(k)]) is None: return None
    return g if len(objects(g, 0)) == k else None
def tf_groupsize(g):
    obs = objects(g, 0); cnt = {}
    for o in obs: cnt[_colour_of(g, o)] = cnt.get(_colour_of(g, o), 0) + 1
    out = copy(g)
    for o in obs:
        for r, c in o: out[r][c] = min(9, cnt[_colour_of(g, o)])
    return out
rule("objects_recolour_by_colour_group_size", "Every object is recoloured with the number of separate objects that share its original colour.", gi_groupsize, tf_groupsize, digits=True)
