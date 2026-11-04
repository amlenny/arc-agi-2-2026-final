# b040_negativespace.py -- 40 rules that operate on the EMPTY SPACE (background) rather than the objects:
# largest empty rectangle/square, empty regions ranked/coloured/removed, gaps between objects, complement
# silhouettes, distance-from-objects maps over the background, and empty rows/cols/quadrants.
import sys, os
from collections import deque
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


# ---------------------------------------------------------------- shared helpers
def _sz(rng, lo=6, hi=20, biglo=21, bighi=30, pbig=0.38):
    if rng.random() < pbig:
        return rng.randint(biglo, bighi), rng.randint(biglo, bighi)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _scene(rng, k_lo=2, k_hi=5, n_lo=3, n_hi=8, lo=8, hi=20, margin=1, distinct=False, excl=(0,)):
    h, w = _sz(rng, lo, hi)
    g = blank(h, w)
    k = rng.randint(k_lo, k_hi)
    shapes = [random_shape(rng, rng.randint(n_lo, n_hi)) for _ in range(k)]
    pool = [c for c in COLOURS if c not in excl]
    if distinct:
        k = min(k, len(pool))
        shapes = shapes[:k]
        cols = rng.sample(pool, k)
    else:
        cols = [rng.choice(pool) for _ in range(k)]
    if place_shapes(rng, g, shapes, cols, margin=margin) is None:
        return None
    return g


def bg_regions(g, bg=0):
    return components(g, bg, conn8=False)


def touches_border(reg, H, W):
    return any(r == 0 or r == H - 1 or c == 0 or c == W - 1 for r, c in reg)


def region_neighbour_colours(g, reg, bg=0):
    H, W = dims(g); cols = set()
    for r, c in reg:
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < H and 0 <= nc < W and g[nr][nc] != bg:
                cols.add(g[nr][nc])
    return cols


def bfs_from_nonbg(g, bg=0):
    H, W = dims(g); dist = [[None] * W for _ in range(H)]; q = deque()
    for r in range(H):
        for c in range(W):
            if g[r][c] != bg:
                dist[r][c] = 0; q.append((r, c))
    while q:
        r, c = q.popleft()
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < H and 0 <= nc < W and dist[nr][nc] is None:
                dist[nr][nc] = dist[r][c] + 1; q.append((nr, nc))
    return dist


def largest_zero_rect(g, bg=0):
    """Classic histogram method; returns (r0, c0, r1, c1) of the largest all-bg axis-aligned rectangle."""
    H, W = dims(g); heights = [0] * W; best_area, best = 0, None
    for r in range(H):
        for c in range(W):
            heights[c] = heights[c] + 1 if g[r][c] == bg else 0
        hs = heights + [0]; stack = []
        for i in range(W + 1):
            while stack and hs[stack[-1]] >= hs[i]:
                h = hs[stack.pop()]
                left = stack[-1] + 1 if stack else 0
                area = h * (i - left)
                if area > best_area:
                    best_area = area; best = (r - h + 1, left, r, i - 1)
            stack.append(i)
    return best


# ============================================================ 1
def gi_largestrect(rng):
    return _scene(rng, 2, 6, 3, 9, 8, 20, margin=1, excl=(0, 5))
def tf_largestrect(g):
    box = largest_zero_rect(g, 0)
    if box is None: return None
    r0, c0, r1, c1 = box
    if (r1 - r0 + 1) * (c1 - c0 + 1) < 4: return None
    out = copy(g); rect(out, r0, c0, r1, c1, 5)
    return out
rule("largest_empty_rectangle_filled", "The largest empty axis-aligned rectangle in the background is filled solid with colour 5.", gi_largestrect, tf_largestrect)


# ============================================================ 2
def gi_rankregions(rng):
    g = _scene(rng, 3, 7, 3, 10, 9, 20, margin=1, distinct=True)
    if g is None: return None
    return g if len(bg_regions(g)) >= 2 else None
def tf_rankregions(g):
    out = copy(g); regs = sorted(bg_regions(g), key=len)
    if len(regs) < 2: return None
    for i, reg in enumerate(regs):
        col = min(i + 1, 9)
        for r, c in reg: out[r][c] = col
    return out
rule("empty_regions_ranked_by_size_digits", "Each empty background region is coloured with its size rank (1 = smallest) as a digit.", gi_rankregions, tf_rankregions, digits=True)


# ============================================================ 3
def gi_singlecolborder(rng):
    g = _scene(rng, 3, 7, 3, 8, 9, 22, margin=1, distinct=True)
    if g is None: return None
    return g if len(bg_regions(g)) >= 2 else None
def tf_singlecolborder(g):
    out = copy(g); changed = False
    for reg in bg_regions(g):
        cols = region_neighbour_colours(g, reg)
        if len(cols) == 1:
            col = next(iter(cols))
            for r, c in reg: out[r][c] = col
            changed = True
    return out if changed else None
rule("empty_region_single_colour_border_filled", "A background region whose every touching cell is the same colour is filled with that colour.", gi_singlecolborder, tf_singlecolborder)


# ============================================================ 4
def gi_gapfill(rng):
    h, w = _sz(rng, 7, 18)
    g = blank(h, w)
    r = rng.randrange(h)
    a, b = sorted(rng.sample(range(w), 2))
    if b - a < 2: return None
    colA, colB = colours(rng, 2)
    g[r][a] = colA; g[r][b] = colB
    return g
def tf_gapfill(g):
    h, w = dims(g)
    out = copy(g)
    for r in range(h):
        nz = [(c, v) for c, v in enumerate(g[r]) if v != 0]
        if len(nz) != 2: continue
        (c1, v1), (c2, v2) = nz
        if c2 - c1 < 2 or v1 == v2: continue
        for c in range(c1 + 1, c2): out[r][c] = 8
    return out if out != g else None
rule("gap_between_two_objects_filled_third_colour", "The empty gap on a row between two single-colour markers is filled with colour 8.", gi_gapfill, tf_gapfill)


# ============================================================ 5
def gi_emptycols(rng):
    g = _scene(rng, 2, 5, 3, 8, 8, 20, margin=1, excl=(0, 4))
    if g is None: return None
    h, w = dims(g)
    empty = [c for c in range(w) if all(g[r][c] == 0 for r in range(h))]
    return g if 1 <= len(empty) < w else None
def tf_emptycols(g):
    h, w = dims(g); out = copy(g)
    empty = [c for c in range(w) if all(g[r][c] == 0 for r in range(h))]
    if not empty: return None
    for c in empty:
        for r in range(h): out[r][c] = 4
    return out
rule("fully_empty_columns_highlighted", "Every column with no coloured cell at all is painted solid colour 4.", gi_emptycols, tf_emptycols)


# ============================================================ 6
def gi_largestsquare(rng):
    return _scene(rng, 2, 5, 3, 9, 9, 22, margin=1, excl=(0, 6))
def tf_largestsquare(g):
    H, W = dims(g)
    best = 0; pos = None
    for r0 in range(H):
        for c0 in range(W):
            maxs = min(H - r0, W - c0)
            for s in range(maxs, 0, -1):
                if s <= best: break
                if all(g[r0 + dr][c0 + dc] == 0 for dr in range(s) for dc in range(s)):
                    best = s; pos = (r0, c0, s); break
    if pos is None or best < 2: return None
    r0, c0, s = pos
    out = copy(g); rect(out, r0, c0, r0 + s - 1, c0 + s - 1, 6, fill=False)
    return out
rule("largest_empty_square_outlined", "The largest empty square in the background has its border outlined in colour 6.", gi_largestsquare, tf_largestsquare)


# ============================================================ 7
def gi_mosttouch(rng):
    g = _scene(rng, 3, 7, 3, 8, 10, 22, margin=1, distinct=True, excl=(0, 5))
    if g is None: return None
    return g if len(bg_regions(g)) >= 2 else None
def tf_mosttouch(g):
    regs = bg_regions(g)
    if len(regs) < 2: return None
    best = max(regs, key=lambda reg: len(region_neighbour_colours(g, reg)))
    if len(region_neighbour_colours(g, best)) < 2: return None
    out = copy(g)
    for r, c in best: out[r][c] = 5
    return out
rule("empty_region_most_touching_colours_filled_grey", "The empty region bordering the most distinct object colours is filled grey (5).", gi_mosttouch, tf_mosttouch)


# ============================================================ 8
def gi_twonb(rng):
    h, w = _sz(rng, 7, 18)
    g = blank(h, w)
    k = rng.randint(h * w // 5, h * w // 3)
    for _ in range(k):
        g[rng.randrange(h)][rng.randrange(w)] = rng.choice([c for c in COLOURS if c != 3])
    return g
def tf_twonb(g):
    H, W = dims(g); out = copy(g); changed = False
    for r in range(H):
        for c in range(W):
            if g[r][c] != 0: continue
            n = sum(1 for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
                    if 0 <= r + dr < H and 0 <= c + dc < W and g[r + dr][c + dc] != 0)
            if n == 2:
                out[r][c] = 3; changed = True
    return out if changed else None
rule("empty_cells_two_neighbours_filled", "Every empty cell with exactly two coloured orthogonal neighbours is filled with colour 3.", gi_twonb, tf_twonb)


# ============================================================ 9
def gi_emptyrows(rng):
    g = _scene(rng, 2, 5, 3, 8, 8, 20, margin=1)
    if g is None: return None
    h, w = dims(g)
    empty = [r for r in range(h) if all(v == 0 for v in g[r])]
    return g if 1 <= len(empty) < h else None
def tf_emptyrows(g):
    h, w = dims(g)
    out = [row[:] for row in g if any(v != 0 for v in row)]
    return out if out and len(out) != h else None
rule("empty_rows_removed", "Every row with no coloured cell is deleted and the grid shrinks vertically.", gi_emptyrows, tf_emptyrows)


# ============================================================ 10
def gi_rowgap(rng):
    h, w = _sz(rng, 6, 16)
    g = blank(h, w)
    for r in range(h):
        if rng.random() < 0.5: continue
        a, b = sorted(rng.sample(range(w), 2))
        if b - a < 2: continue
        c1, c2 = colours(rng, 2)
        g[r][a] = c1; g[r][b] = c2
    return g if any(v for row in g for v in row) else None
def tf_rowgap(g):
    h, w = dims(g); out = copy(g); changed = False
    for r in range(h):
        nz = [c for c, v in enumerate(g[r]) if v != 0]
        if len(nz) < 2: continue
        a, b = nz[0], nz[-1]
        leftcol = g[r][a]
        for c in range(a + 1, b):
            if g[r][c] == 0:
                out[r][c] = leftcol; changed = True
    return out if changed else None
rule("row_gap_filled_with_left_colour", "On each row, the empty space between the leftmost and rightmost coloured cell is filled with the leftmost one's colour.", gi_rowgap, tf_rowgap)


# ============================================================ 11
def gi_farthest(rng):
    h, w = _sz(rng, 8, 20)
    g = blank(h, w)
    k = rng.randint(2, 5)
    for _ in range(k):
        g[rng.randrange(h)][rng.randrange(w)] = rng.choice(COLOURS)
    return g if sum(1 for row in g for v in row if v) >= 2 else None
def tf_farthest(g):
    dist = bfs_from_nonbg(g, 0)
    H, W = dims(g)
    best = -1
    for r in range(H):
        for c in range(W):
            if g[r][c] == 0 and dist[r][c] is not None and dist[r][c] > best:
                best = dist[r][c]
    if best <= 1: return None
    out = copy(g)
    for r in range(H):
        for c in range(W):
            if g[r][c] == 0 and dist[r][c] == best:
                out[r][c] = 7
    return out
rule("farthest_empty_cell_from_objects_marked", "The empty cell (or cells) farthest from any coloured cell is marked with colour 7.", gi_farthest, tf_farthest)


# ============================================================ 12
def gi_smallk(rng):
    g = _scene(rng, 3, 7, 2, 7, 10, 22, margin=1, excl=(0, 5))
    if g is None: return None
    return g if len(bg_regions(g)) >= 2 else None
def tf_smallk(g):
    regs = bg_regions(g)
    if len(regs) < 2: return None
    sizes = sorted(len(r) for r in regs)
    k = sizes[len(sizes) // 2] + 1
    out = copy(g); changed = False
    for reg in regs:
        if len(reg) < k:
            for r, c in reg: out[r][c] = 5
            changed = True
    return out if changed else None
rule("small_empty_regions_filled_below_k", "Every empty region smaller than the median region size is filled with colour 5.", gi_smallk, tf_smallk)


# ============================================================ 13
def gi_crosslines(rng):
    h, w = _sz(rng, 10, 24)
    g = blank(h, w)
    k = rng.randint(2, 4)
    pts = set()
    cols = colours(rng, k, exclude=(0, 8))
    for col in cols:
        for _ in range(20):
            r, c = rng.randrange(h), rng.randrange(w)
            if (r, c) not in pts:
                g[r][c] = col; pts.add((r, c)); break
    return g if pts else None
def tf_crosslines(g):
    H, W = dims(g); out = copy(g)
    markers = [(r, c) for r in range(H) for c in range(W) if g[r][c] != 0]
    if not markers: return None
    for r, c in markers:
        for x in range(W):
            if out[r][x] == 0: out[r][x] = 8
        for y in range(H):
            if out[y][c] == 0: out[y][c] = 8
    regs = bg_regions(out, 0)
    if len(regs) < 2: return None
    for i, reg in enumerate(regs):
        col = 1 if i % 2 == 0 else 2
        for r, c in reg: out[r][c] = col
    return out
rule("background_split_by_object_crosslines_alternate", "A grey cross is drawn through every marker's row and column, splitting the background into regions coloured alternately 1 and 2.", gi_crosslines, tf_crosslines)


# ============================================================ 14
def gi_openfour(rng):
    g = _scene(rng, 2, 5, 3, 8, 9, 20, margin=1, excl=(0, 5))
    return g
def tf_openfour(g):
    H, W = dims(g); out = copy(g); changed = False
    for r in range(H):
        for c in range(W):
            if g[r][c] != 0: continue
            up = all(g[y][c] == 0 for y in range(0, r))
            down = all(g[y][c] == 0 for y in range(r + 1, H))
            left = all(g[r][x] == 0 for x in range(0, c))
            right = all(g[r][x] == 0 for x in range(c + 1, W))
            if not (up and down and left and right):
                out[r][c] = 5; changed = True
    return out if changed else None
rule("empty_cells_open_all_four_sides_kept_rest_filled", "An empty cell that can see the border in all four cardinal directions stays empty; every other empty cell is filled with colour 5.", gi_openfour, tf_openfour)


# ============================================================ 15
def gi_complement(rng):
    g = _scene(rng, 2, 5, 3, 9, 8, 20, margin=1, excl=(0, 4))
    return g
def tf_complement(g):
    H, W = dims(g); out = blank(H, W)
    for r in range(H):
        for c in range(W):
            out[r][c] = 0 if g[r][c] != 0 else 4
    return out
rule("object_complement_solid_silhouette", "Every object becomes background and the former background becomes a solid colour-4 silhouette.", gi_complement, tf_complement, primitive=True)
# ============================================================ 16
def gi_regioncountbar(rng):
    g = _scene(rng, 2, 6, 3, 8, 9, 20, margin=1, excl=(0, 6))
    if g is None: return None
    return g if 2 <= len(bg_regions(g)) <= 9 else None
def tf_regioncountbar(g):
    n = len(bg_regions(g))
    if n < 2: return None
    return [[7] + [6] * (n - 1) + [0]]
# empty_region_count_bar dropped 2026-10-12: fails the single-colour-answer / copyable-answer gates at full rebuild; tried widening the generator twice (2026-10-12 restore attempt), still fails on constant_answers/test_answer_in_demos (bg_regions rarely >1 for random shapes) -- left commented per budget
# ============================================================ 17
def gi_onenbcol(rng):
    h, w = _sz(rng, 7, 20)
    g = blank(h, w)
    k = rng.randint(h * w // 6, h * w // 3)
    for _ in range(k):
        g[rng.randrange(h)][rng.randrange(w)] = rng.choice(COLOURS)
    return g
def tf_onenbcol(g):
    H, W = dims(g); out = copy(g); changed = False
    for r in range(H):
        for c in range(W):
            if g[r][c] != 0: continue
            nbs = {g[r + dr][c + dc] for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
                   if 0 <= r + dr < H and 0 <= c + dc < W and g[r + dr][c + dc] != 0}
            if len(nbs) == 1:
                out[r][c] = next(iter(nbs)); changed = True
    return out if changed else None
rule("empty_cells_single_neighbour_colour_recoloured", "An empty cell whose coloured orthogonal neighbours are all one colour is recoloured to that colour.", gi_onenbcol, tf_onenbcol)


# ============================================================ 18
def gi_smallestregion(rng):
    g = _scene(rng, 3, 7, 3, 8, 9, 22, margin=1, excl=(0, 7))
    if g is None: return None
    return g if len(bg_regions(g)) >= 2 else None
def tf_smallestregion(g):
    regs = bg_regions(g)
    if len(regs) < 2: return None
    sizes = sorted(len(r) for r in regs)
    if sizes[0] == sizes[1]: return None
    small = min(regs, key=len)
    out = copy(g)
    for r, c in small: out[r][c] = 7
    return out
rule("smallest_empty_region_filled", "The single smallest empty region is filled with colour 7, all others stay empty.", gi_smallestregion, tf_smallestregion)


# ============================================================ 19
def gi_cornerregions(rng):
    g = _scene(rng, 3, 7, 3, 8, 9, 22, margin=1, excl=(0, 5))
    if g is None: return None
    return g if len(bg_regions(g)) >= 2 else None
def tf_cornerregions(g):
    H, W = dims(g); corners = {(0, 0), (0, W - 1), (H - 1, 0), (H - 1, W - 1)}
    out = copy(g); changed = False
    for reg in bg_regions(g):
        if set(reg) & corners:
            for r, c in reg: out[r][c] = 5
            changed = True
    return out if changed else None
rule("corner_touching_empty_regions_filled", "Every empty region that includes one of the grid's four corners is filled with colour 5.", gi_cornerregions, tf_cornerregions)


# ============================================================ 20
def gi_borderregions(rng):
    g = _scene(rng, 3, 7, 3, 8, 10, 24, margin=1, excl=(0, 5), distinct=True)
    if g is None: return None
    regs = bg_regions(g)
    return g if len(regs) >= 2 else None
def tf_borderregions(g):
    H, W = dims(g); out = copy(g)
    for reg in bg_regions(g):
        if touches_border(reg, H, W):
            for r, c in reg: out[r][c] = 5
    return out
rule("border_touching_empty_regions_filled", "Every empty region that touches the grid's outer edge is filled with colour 5; fully enclosed ones stay empty.", gi_borderregions, tf_borderregions)


# ============================================================ 21
def gi_diaggap(rng):
    h, w = _sz(rng, 7, 18)
    g = blank(h, w)
    n = min(h, w)
    a, b = sorted(rng.sample(range(n), 2))
    if b - a < 2: return None
    col = rng.choice(COLOURS)
    g[a][a] = col; g[b][b] = col
    return g
def tf_diaggap(g):
    h, w = dims(g); out = copy(g); changed = False
    pts_by_col = {}
    for r in range(h):
        for c in range(w):
            if g[r][c] != 0:
                pts_by_col.setdefault(g[r][c], []).append((r, c))
    for col, pts in pts_by_col.items():
        if len(pts) != 2: continue
        (r1, c1), (r2, c2) = pts
        if abs(r1 - r2) == abs(c1 - c2) and r1 != r2:
            dr = 1 if r2 > r1 else -1
            dc = 1 if c2 > c1 else -1
            r, c = r1 + dr, c1 + dc
            while (r, c) != (r2, c2):
                out[r][c] = col; changed = True
                r += dr; c += dc
    return out if changed else None
rule("diagonal_pair_gap_filled", "Two same-colour cells lying on a shared diagonal have the empty diagonal between them filled with that colour.", gi_diaggap, tf_diaggap)


# ============================================================ 22
def gi_emptycolsrm(rng):
    g = _scene(rng, 2, 5, 3, 8, 8, 20, margin=1)
    if g is None: return None
    h, w = dims(g)
    empty = [c for c in range(w) if all(g[r][c] == 0 for r in range(h))]
    return g if 1 <= len(empty) < w else None
def tf_emptycolsrm(g):
    h, w = dims(g)
    keep = [c for c in range(w) if any(g[r][c] != 0 for r in range(h))]
    if not keep or len(keep) == w: return None
    return [[row[c] for c in keep] for row in g]
rule("empty_columns_removed", "Every column with no coloured cell is deleted and the grid shrinks horizontally.", gi_emptycolsrm, tf_emptycolsrm)


# ============================================================ 23
def _place_avoiding(rng, g, shape, col, tries=200, margin=1):
    H, W = dims(g)
    hgt = max(r for r, _ in shape) + 1; wid = max(c for _, c in shape) + 1
    if hgt > H or wid > W: return None
    for _ in range(tries):
        r0, c0 = rng.randint(0, H - hgt), rng.randint(0, W - wid)
        ok = True
        for r, c in shape:
            for dr in range(-margin, margin + 1):
                for dc in range(-margin, margin + 1):
                    rr, cc = r0 + r + dr, c0 + c + dc
                    if 0 <= rr < H and 0 <= cc < W and g[rr][cc] != 0:
                        ok = False; break
                if not ok: break
            if not ok: break
        if ok:
            for r, c in shape: g[r0 + r][c0 + c] = col
            return (r0, c0)
    return None


def gi_arealatch(rng):
    h, w = _sz(rng, 12, 22)
    g = blank(h, w)
    fh, fw = rng.randint(2, 4), rng.randint(2, 4)
    area = fh * fw
    if h - fh - 3 < 1 or w - fw - 3 < 1: return None
    r0, c0 = rng.randint(1, h - fh - 3), rng.randint(1, w - fw - 3)
    wallcol, objcol = colours(rng, 2)
    rect(g, r0, c0, r0 + fh + 1, c0 + fw + 1, wallcol, fill=False)
    shape = random_shape(rng, area)
    if _place_avoiding(rng, g, shape, objcol, margin=1) is None:
        return None
    return g
def tf_arealatch(g):
    objs = objects(g, 0); regs = bg_regions(g)
    out = copy(g); changed = False
    for reg in regs:
        match = next((o for o in objs if len(o) == len(reg)), None)
        if match:
            col = g[match[0][0]][match[0][1]]
            for r, c in reg: out[r][c] = col
            changed = True
    return out if changed else None
rule("empty_region_area_equals_object_area_recoloured", "An empty region whose cell count exactly equals an object's cell count is recoloured to that object's colour.", gi_arealatch, tf_arealatch)


# ============================================================ 24
def gi_narrowgap(rng):
    h, w = _sz(rng, 8, 20)
    g = blank(h, w)
    c = rng.randrange(w)
    k = rng.randint(2, 3)
    col = rng.choice(COLOURS)
    rows = sorted(rng.sample(range(h), 2 * k))
    gaps = [(rows[2 * i], rows[2 * i + 1]) for i in range(k)]
    for a, b in gaps:
        if b - a < 1: return None
        g[a][c] = col; g[b][c] = col
    return g
def tf_narrowgap(g):
    h, w = dims(g); out = copy(g)
    best = None
    for c in range(w):
        pts = [r for r in range(h) if g[r][c] != 0]
        for i in range(len(pts) - 1):
            gap = pts[i + 1] - pts[i] - 1
            if gap > 0 and (best is None or gap < best[0]):
                best = (gap, c, pts[i], pts[i + 1])
    if best is None: return None
    gap, c, a, b = best
    col = g[a][c]
    for r in range(a + 1, b): out[r][c] = col
    return out if out != g else None
rule("narrowest_vertical_gap_filled", "On the column with the narrowest empty gap between two markers of the same colour, that gap is filled with their colour.", gi_narrowgap, tf_narrowgap)


# ============================================================ 25
def gi_nbcountdigit(rng):
    g = _scene(rng, 2, 5, 3, 8, 8, 20, margin=1)
    return g
def tf_nbcountdigit(g):
    H, W = dims(g); out = copy(g); changed = False
    for r in range(H):
        for c in range(W):
            if g[r][c] != 0: continue
            n = sum(1 for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
                    if 0 <= r + dr < H and 0 <= c + dc < W and g[r + dr][c + dc] != 0)
            if n > 0:
                out[r][c] = n; changed = True
    return out if changed else None
rule("empty_cell_neighbour_count_digit_map", "Every empty cell with at least one coloured orthogonal neighbour is replaced by the digit count of such neighbours (0-4).", gi_nbcountdigit, tf_nbcountdigit, digits=True)


# ============================================================ 26
def gi_quadrant(rng):
    g = _scene(rng, 3, 7, 2, 6, 10, 22, margin=1, excl=(0, 9))
    return g
def tf_quadrant(g):
    H, W = dims(g); hh, hw = H // 2, W // 2
    if hh < 1 or hw < 1: return None
    quads = [(0, 0, hh, hw), (0, hw, hh, W), (hh, 0, H, hw), (hh, hw, H, W)]
    counts = []
    for r0, c0, r1, c1 in quads:
        empt = sum(1 for r in range(r0, r1) for c in range(c0, c1) if g[r][c] == 0)
        counts.append(empt)
    best = max(range(4), key=lambda i: counts[i])
    if counts.count(counts[best]) > 1: return None
    out = copy(g); r0, c0, r1, c1 = quads[best]
    for r in range(r0, r1):
        for c in range(c0, c1):
            if g[r][c] == 0: out[r][c] = 9
    return out
rule("majority_empty_quadrant_marked", "The quadrant with the most empty cells has all of its empty cells painted colour 9.", gi_quadrant, tf_quadrant)


# ============================================================ 27
def gi_ring(rng):
    h, w = _sz(rng, 9, 20)
    g = blank(h, w)
    n = rng.randint(3, 8)
    shape = random_shape(rng, n)
    col = rng.choice(COLOURS)
    if place_shapes(rng, g, [shape], [col], margin=2) is None: return None
    return g
def tf_ring(g):
    H, W = dims(g); out = copy(g); changed = False
    obj = cells(g, lambda v: v != 0)
    if not obj: return None
    for r, c in obj:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr, nc = r + dr, c + dc
                if (dr, dc) != (0, 0) and 0 <= nr < H and 0 <= nc < W and g[nr][nc] == 0:
                    out[nr][nc] = 8; changed = True
    return out if changed else None
rule("empty_ring_around_single_object_filled", "Every empty cell touching the single object (including diagonally) is filled with colour 8.", gi_ring, tf_ring)


# ============================================================ 28
def gi_hull(rng):
    h, w = _sz(rng, 9, 22)
    g = blank(h, w)
    k = rng.randint(4, 6)
    col = rng.choice(COLOURS)
    pts = set()
    for _ in range(k):
        for _ in range(30):
            r, c = rng.randrange(h), rng.randrange(w)
            if (r, c) not in pts:
                pts.add((r, c)); g[r][c] = col; break
    return g if len(pts) >= 4 else None
def tf_hull(g):
    H, W = dims(g)
    pts = cells(g, lambda v: v != 0)
    if len(pts) < 4: return None
    rs = [r for r, _ in pts]; cs = [c for _, c in pts]
    r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs)
    if (r1 - r0) < 2 or (c1 - c0) < 2: return None
    out = copy(g); changed = False
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if g[r][c] == 0:
                out[r][c] = 3; changed = True
    return out if changed else None
rule("empty_cells_inside_convex_hull_filled", "Every empty cell inside the bounding box of all marker cells is filled with colour 3.", gi_hull, tf_hull)


# ============================================================ 29
def gi_largestrectoutline(rng):
    return _scene(rng, 2, 6, 3, 9, 8, 20, margin=1, excl=(0, 6))
def tf_largestrectoutline(g):
    box = largest_zero_rect(g, 0)
    if box is None: return None
    r0, c0, r1, c1 = box
    if (r1 - r0 + 1) * (c1 - c0 + 1) < 6: return None
    out = copy(g); rect(out, r0, c0, r1, c1, 6, fill=False)
    return out
rule("largest_empty_rectangle_outlined", "The largest empty axis-aligned rectangle has only its border drawn in colour 6, interior stays empty.", gi_largestrectoutline, tf_largestrectoutline)


# ============================================================ 30
def gi_sizecentre(rng):
    g = _scene(rng, 3, 6, 4, 9, 10, 22, margin=1, distinct=True)
    if g is None: return None
    return g if len(bg_regions(g)) >= 2 else None
def tf_sizecentre(g):
    out = copy(g); changed = False
    for reg in bg_regions(g):
        if len(reg) < 3: continue
        rs = sorted(reg)
        r, c = rs[len(rs) // 2]
        out[r][c] = min(len(reg), 9); changed = True
    return out if changed else None
rule("empty_region_size_painted_centre_digit", "Each empty region (3+ cells) gets one interior cell painted with the digit of its size (capped at 9).", gi_sizecentre, tf_sizecentre, digits=True)


# ============================================================ 31
def gi_swaptag(rng):
    g = _scene(rng, 3, 6, 3, 8, 10, 22, margin=1, excl=(0, 1, 2))
    if g is None: return None
    regs = bg_regions(g)
    if len(regs) < 2: return None
    sizes = sorted((len(r) for r in regs), reverse=True)
    return g if sizes[0] != sizes[1] else None
def tf_swaptag(g):
    regs = bg_regions(g)
    if len(regs) < 2: return None
    regs = sorted(regs, key=len, reverse=True)
    out = copy(g)
    for r, c in regs[0]: out[r][c] = 1
    for r, c in regs[1]: out[r][c] = 2
    return out
rule("two_largest_empty_regions_swap_colour_tag", "The largest empty region is tagged colour 1 and the second largest colour 2; smaller ones stay empty.", gi_swaptag, tf_swaptag)


# ============================================================ 32
def gi_diagonalmark(rng):
    n = rng.randint(21, 30) if rng.random() < 0.38 else rng.randint(6, 20)
    g = blank(n, n)
    k = rng.randint(2, 5)
    shapes = [random_shape(rng, rng.randint(3, 8)) for _ in range(k)]
    pool = [c for c in COLOURS if c not in (0, 4)]
    cols = [rng.choice(pool) for _ in range(k)]
    if place_shapes(rng, g, shapes, cols, margin=1) is None: return None
    return g
def tf_diagonalmark(g):
    H, W = dims(g)
    if H != W: return None
    out = copy(g); changed = False
    for i in range(H):
        if g[i][i] == 0:
            out[i][i] = 4; changed = True
    return out if changed else None
rule("empty_cells_on_main_diagonal_marked", "Every empty cell on the grid's main diagonal is marked colour 4.", gi_diagonalmark, tf_diagonalmark)


# ============================================================ 33
def gi_borderring(rng):
    g = _scene(rng, 2, 5, 3, 8, 10, 22, margin=2, excl=(0, 5))
    return g
def tf_borderring(g):
    H, W = dims(g); out = copy(g); changed = False
    for r in range(H):
        for c in range(W):
            if (r in (0, H - 1) or c in (0, W - 1)) and g[r][c] == 0:
                out[r][c] = 5; changed = True
    return out if changed else None
rule("empty_border_ring_filled", "Every empty cell on the outer border ring of the grid is filled with colour 5.", gi_borderring, tf_borderring)


# ============================================================ 34
def gi_secondregion(rng):
    g = _scene(rng, 3, 7, 3, 8, 10, 22, margin=1, excl=(0, 7))
    if g is None: return None
    regs = bg_regions(g)
    if len(regs) < 2: return None
    sizes = sorted((len(r) for r in regs), reverse=True)
    return g if sizes[1] != sizes[0] else None
def tf_secondregion(g):
    regs = bg_regions(g)
    if len(regs) < 2: return None
    regs = sorted(regs, key=len, reverse=True)
    out = copy(g)
    for r, c in regs[1]: out[r][c] = 7
    return out
rule("second_largest_empty_region_filled", "The second-largest empty region is filled with colour 7; the largest and smaller ones stay empty.", gi_secondregion, tf_secondregion)


# ============================================================ 35
def gi_enclosedoutline(rng):
    h, w = _sz(rng, 10, 22)
    g = blank(h, w)
    cols = colours(rng, rng.randint(1, 2), exclude=(0, 5))
    placed = 0
    for col in cols:
        for _ in range(30):
            fh, fw = rng.randint(4, 7), rng.randint(4, 7)
            if fh + 4 > h or fw + 4 > w: continue
            r0, c0 = rng.randint(1, h - fh - 2), rng.randint(1, w - fw - 2)
            zone = [(r, c) for r in range(r0 - 1, r0 + fh + 1) for c in range(c0 - 1, c0 + fw + 1)]
            if all(0 <= r < h and 0 <= c < w and g[r][c] == 0 for r, c in zone):
                rect(g, r0, c0, r0 + fh - 1, c0 + fw - 1, col, fill=False)
                placed += 1
                break
    return g if placed else None
def tf_enclosedoutline(g):
    H, W = dims(g); out = copy(g); changed = False
    for reg in bg_regions(g):
        if touches_border(reg, H, W) or len(reg) < 2: continue
        regset = set(reg)
        for r, c in reg:
            if any((r + dr, c + dc) not in regset for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))):
                out[r][c] = 5; changed = True
    return out if changed else None
rule("enclosed_empty_regions_outlined", "Every fully enclosed empty region (not touching the grid edge) has only its perimeter cells painted colour 5, leaving its core empty.", gi_enclosedoutline, tf_enclosedoutline)


# ============================================================ 36
def gi_perimeterbar(rng):
    g = _scene(rng, 3, 7, 3, 9, 9, 20, margin=1, excl=(0, 8), distinct=True)
    if g is None: return None
    return g if len(bg_regions(g)) >= 2 else None
def tf_perimeterbar(g):
    regs = bg_regions(g)
    if len(regs) < 2: return None
    smallest = min(regs, key=len)
    regset = set(smallest)
    perim = sum(1 for r, c in smallest
                if any((r + dr, c + dc) not in regset for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))))
    perim = max(2, min(perim, 30))
    return [[7] + [8] * (perim - 1) + [0]]
rule("empty_region_perimeter_bar", "Output a single row as long as the smallest empty region's perimeter cell count: a colour-7 marker cell followed by colour-8 cells, followed by one empty cell.", gi_perimeterbar, tf_perimeterbar)
# ============================================================ 37
def gi_equidist(rng):
    h, w = _sz(rng, 9, 20)
    g = blank(h, w)
    c1, c2 = colours(rng, 2)
    r = rng.randrange(h)
    a, b = sorted(rng.sample(range(w), 2))
    if (b - a) % 2 != 0 or b - a < 2: return None
    g[r][a] = c1; g[r][b] = c2
    return g
def tf_equidist(g):
    dist = bfs_from_nonbg(g, 0)
    H, W = dims(g)
    pts = cells(g, lambda v: v != 0)
    if len(pts) != 2: return None
    out = copy(g); changed = False
    for r in range(H):
        for c in range(W):
            if g[r][c] != 0: continue
            d1 = abs(r - pts[0][0]) + abs(c - pts[0][1])
            d2 = abs(r - pts[1][0]) + abs(c - pts[1][1])
            if d1 == d2:
                out[r][c] = 6; changed = True
    return out if changed else None
rule("empty_cells_equidistant_two_objects_marked", "Every empty cell equally close (Manhattan distance) to both marker cells is painted colour 6.", gi_equidist, tf_equidist)


# ============================================================ 38
def gi_rowmostempty(rng):
    h, w = _sz(rng, 7, 20, pbig=0.38)
    if w < 4: return None
    g = blank(h, w)
    target = rng.randrange(h)
    pool = [c for c in COLOURS if c != 4]
    for r in range(h):
        if r == target:
            if rng.random() < 0.5:
                g[r][rng.randrange(w)] = rng.choice(pool)
            continue
        k = rng.randint(max(1, w // 2), w)
        for i in rng.sample(range(w), k):
            g[r][i] = rng.choice(pool)
    return g
def tf_rowmostempty(g):
    h, w = dims(g)
    counts = [sum(1 for v in row if v == 0) for row in g]
    best = max(range(h), key=lambda r: counts[r])
    if counts.count(counts[best]) > 1 or counts[best] == 0: return None
    out = copy(g)
    for c in range(w):
        if out[best][c] == 0: out[best][c] = 4
    return out
rule("row_with_most_empty_cells_filled", "The single row with the most empty cells has all of its empty cells painted colour 4.", gi_rowmostempty, tf_rowmostempty)


# ============================================================ 39
def gi_colfewestempty(rng):
    g = _scene(rng, 3, 7, 2, 6, 9, 20, margin=1, excl=(0, 2))
    return g
def tf_colfewestempty(g):
    h, w = dims(g)
    counts = [sum(1 for r in range(h) if g[r][c] == 0) for c in range(w)]
    nz = [i for i in range(w) if counts[i] > 0]
    if not nz: return None
    best = min(nz, key=lambda c: counts[c])
    if counts.count(counts[best]) > 1: return None
    out = copy(g)
    for r in range(h):
        if out[r][best] == 0: out[r][best] = 2
    return out
rule("column_with_fewest_empty_cells_marked", "Among columns that have at least one empty cell, the one with the fewest empty cells has them all painted colour 2.", gi_colfewestempty, tf_colfewestempty)


# ============================================================ 40
def gi_totalarea(rng):
    h, w = rng.randint(4, 8), rng.randint(4, 8)
    g = blank(h, w)
    pool = [c for c in COLOURS if c != 9]
    k = rng.randint(0, h * w - 2)
    for r, c in rng.sample([(r, c) for r in range(h) for c in range(w)], k):
        g[r][c] = rng.choice(pool)
    return g
def tf_totalarea(g):
    n = sum(1 for row in g for v in row if v == 0)
    n = min(n, 30)
    if n < 2: return None
    return [[7] + [9] * (n - 1)]
rule("total_empty_area_as_bar", "Output a single row as long as the number of empty cells (capped at 30): a colour-7 marker cell followed by colour-9 cells.", gi_totalarea, tf_totalarea)
