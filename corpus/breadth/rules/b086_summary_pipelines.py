# b086_summary_pipelines.py -- TRANSFORM THEN SUMMARISE: every rule is a two-step chain. Step 1 changes the scene
# (gravity, rigid fall, noise removal, merging, flooding, mirroring, deleting, recolouring, rotating, cropping, shifting,
# dilating, eroding, filling, rays ...); step 2 outputs a summary of the CHANGED scene (bar, digits, table, legend).
# Encodings: digit answers are two cells [tens, units] unless stated; bars are padded with empty cells to a stated width.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
N8 = N4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))


def D(rng, lo=8, hi=29):
    if rng.random() < 0.45: return rng.randint(21, hi)
    return rng.randint(lo, min(hi, 20))


def mk(gen, tf, cond=None, tries=90):
    def make(rng):
        last = None
        for _ in range(tries):
            g = gen(rng)
            if g is None: continue
            last = g
            o = tf(g)
            if o is None or o == g: continue
            if len({v for r in o for v in r}) < 2 or len(o) > 30 or len(o[0]) > 30: continue
            if cond is None or cond(g, o): return g
        return last if last is not None else blank(8, 8)
    return make


def comps(g, conn8=False):
    out = []
    for col in sorted({v for r in g for v in r if v}):
        for c in components(g, col, conn8=conn8): out.append((col, sorted(c)))
    return sorted(out, key=lambda o: o[1][0])


def two(n): return [[n // 10, n % 10]]


def scatter_subs(rng, H, Wd, subs, margin=1):
    g = blank(H, Wd); boxes = []
    for sub in subs:
        h, w = dims(sub)
        if h > H or w > Wd: return None
        for _ in range(150):
            r0, c0 = rng.randint(0, H - h), rng.randint(0, Wd - w)
            if all(r0 > b[2] + margin or r0 + h - 1 < b[0] - margin or c0 > b[3] + margin or c0 + w - 1 < b[1] - margin for b in boxes):
                boxes.append((r0, c0, r0 + h - 1, c0 + w - 1)); paste(g, sub, r0, c0, transparent=0); break
        else:
            return None
    return g


# ------------------------------------------------------------------ scenes
def sa(kmin=3, kmax=7, cmax=8, ncol=(2, 4), margin=1, ex=(0,)):
    def gen(rng):
        H, Wd = D(rng), D(rng); k = rng.randint(kmin, max(kmin, min(kmax, 1 + H * Wd // 50)))
        pc = rng.sample([c for c in range(1, 10) if c not in ex], rng.randint(*ncol)); g = blank(H, Wd)
        return g if place_shapes(rng, g, [random_shape(rng, rng.randint(1, cmax)) for _ in range(k)], [rng.choice(pc) for _ in range(k)], margin=margin) else None
    return gen


def blob(rng):
    h, w = rng.randint(3, 6), rng.randint(3, 6); S = set()
    for _ in range(rng.randint(2, 3)):
        rh, rw = rng.randint(2, h), rng.randint(2, w); r0, c0 = rng.randint(0, h - rh), rng.randint(0, w - rw)
        S |= {(r, c) for r in range(r0, r0 + rh) for c in range(c0, c0 + rw)}
    r0, c0, r1, c1 = bbox(list(S)); return S, r0, c0, r1 - r0 + 1, c1 - c0 + 1


def sb(kmin=2, kmax=6):
    def gen(rng):
        H, Wd = D(rng, 10), D(rng, 10); k = rng.randint(kmin, kmax); pc = rng.sample(range(1, 10), rng.randint(2, 4)); subs = []
        for _ in range(k):
            S, r0, c0, h, w = blob(rng); col = rng.choice(pc); s = blank(h, w)
            for r, c in S: s[r - r0][c - c0] = col
            subs.append(s)
        return scatter_subs(rng, H, Wd, subs)
    return gen


def sdots(dens=(.05, .14), ncol=(2, 5), even=False, ex=(0,), lo=8):
    def gen(rng):
        H, Wd = D(rng, lo), D(rng, lo)
        if even: Wd -= Wd % 2
        pc = rng.sample([c for c in range(1, 10) if c not in ex], rng.randint(*ncol)); g = blank(H, Wd)
        for r, c in rng.sample([(r, c) for r in range(H) for c in range(Wd)], max(6, int(H * Wd * rng.uniform(*dens)))): g[r][c] = rng.choice(pc)
        return g
    return gen


def sd(rng):
    H, Wd = D(rng, 10), D(rng, 10); pc = rng.sample(range(1, 10), rng.randint(3, 5)); subs = []
    for _ in range(rng.randint(2, 4)):
        n = rng.randint(2, 3); ws = [rng.randint(2, 4) for _ in range(n)]; hs = [rng.randint(2, 4) for _ in range(n)]
        cs = [rng.choice(pc)]
        for i in range(1, n): cs.append(rng.choice([c for c in pc if c != cs[-1]]))
        s = blank(max(hs), sum(ws)); x = 0
        for w, h, c in zip(ws, hs, cs): rect(s, 0, x, h - 1, x + w - 1, c); x += w
        subs.append(s)
    for _ in range(rng.randint(0, 2)): subs.append([[rng.choice(pc)]])
    return scatter_subs(rng, H, Wd, subs)


def se(rng):
    H, Wd = D(rng, 10), D(rng, 10); subs = []
    for _ in range(rng.randint(2, 8)):
        h, w = rng.randint(3, 6), rng.randint(3, 6); s = blank(h, w); rect(s, 0, 0, h - 1, w - 1, rng.choice([c for c in range(1, 10) if c != 5]), fill=False)
        if rng.random() < .3:
            a = s[0][0]; side = rng.randrange(4)
            if side == 0: s[0][rng.randint(1, w - 2)] = 0
            elif side == 1: s[h - 1][rng.randint(1, w - 2)] = 0
            elif side == 2: s[rng.randint(1, h - 2)][0] = 0
            else: s[rng.randint(1, h - 2)][w - 1] = 0
        subs.append(s)
    return scatter_subs(rng, H, Wd, subs)


# ------------------------------------------------------------------ 1 rigid fall -> skyline
def rigid_fall(g):
    H, W = dims(g); out = blank(H, W); objs_ = sorted(comps(g), key=lambda o: (-max(r for r, _ in o[1]), o[1][0]))
    for col, cells in objs_:
        d = 0
        while all(r + d + 1 < H and out[r + d + 1][c] == 0 for r, c in cells): d += 1
        for r, c in cells: out[r + d][c] = col
    return out


def tf1(g):
    o = rigid_fall(g); H, W = dims(o)
    return [[min(9, H - min((r for r in range(H) if o[r][c]), default=H)) for c in range(W)]]
rule("rigid_fall_then_skyline_height_digits", "Step 1: every object (4-connected, same colour) falls straight down as a rigid body until it rests on the floor or another cell, objects being dropped in order of their lowest row (lowest first, a tie in reading order of first cells). Step 2: output one row as wide as the grid holding, per column, the height of the stack after the fall (rows from the column's topmost cell to the floor, capped at 9) as a digit.",
     mk(sa(3, 6, 6), tf1), tf1, digits=True)


# ------------------------------------------------------------------ 2 noise -> per-colour object table
def tf2(g):
    H, W = dims(g); out = copy(g); cs = comps(g)
    for col, cells in cs:
        if len(cells) == 1: out[cells[0][0]][cells[0][1]] = 0
    cnt = {}
    for col, cells in comps(out): cnt[col] = cnt.get(col, 0) + 1
    return [[c, min(9, cnt[c])] for c in sorted(cnt)] or None


def snoise(rng):
    g = sa(2, 5, 8, (2, 4))(rng)
    if g is None: return None
    H, W = dims(g); free = [(r, c) for r in range(H) for c in range(W) if g[r][c] == 0 and all(not (0 <= r + dr < H and 0 <= c + dc < W and g[r + dr][c + dc]) for dr, dc in N8)]
    pc = sorted({v for row in g for v in row if v})
    for r, c in rng.sample(free, min(len(free), rng.randint(3, 8))): g[r][c] = rng.choice(pc)
    return g
rule("denoise_then_object_count_table", "Step 1: every object consisting of a single cell (4-connected, same colour) is erased. Step 2: output a table with one row per colour still present, ascending colour value: the colour, then its number of remaining objects (4-connected, same colour) as a digit capped at 9.",
     mk(snoise, tf2), tf2, digits=True)


# ------------------------------------------------------------------ 3 merge touching -> legend
def tf3(g):
    H, W = dims(g); seen = set(); res = []
    for r in range(H):
        for c in range(W):
            if g[r][c] and (r, c) not in seen:
                st = [(r, c)]; seen.add((r, c)); cm = []
                while st:
                    y, x = st.pop(); cm.append((y, x))
                    for dr, dc in N4:
                        ny, nx = y + dr, x + dc
                        if 0 <= ny < H and 0 <= nx < W and g[ny][nx] and (ny, nx) not in seen: seen.add((ny, nx)); st.append((ny, nx))
                cnt = {}
                for y, x in cm: cnt[g[y][x]] = cnt.get(g[y][x], 0) + 1
                res.append((-len(cm), min(cm), min(cnt, key=lambda k: (-cnt[k], k)), len(cm)))
    res.sort()
    return [[col, min(9, n)] for _, _, col, n in res][:9]
rule("merge_touching_then_size_ordered_legend", "Step 1: objects of any colours that touch edge to edge are merged into one object (every group of edge-connected non-empty cells is one merged object). Step 2: output a table with one row per merged object (at most 9 rows), ordered from most cells to fewest (a tie goes to the object whose first cell comes first in reading order): its dominant colour (most cells, a tie going to the lower colour value), then its cell count as a digit capped at 9.",
     mk(sd, tf3), tf3, digits=True)


# ------------------------------------------------------------------ 4 flood enclosed grey -> region bar
def enclosed(g):
    H, W = dims(g); seen = set(); st = [(r, c) for r in range(H) for c in range(W) if (r in (0, H - 1) or c in (0, W - 1)) and g[r][c] == 0]; seen = set(st)
    while st:
        y, x = st.pop()
        for dr, dc in N4:
            ny, nx = y + dr, x + dc
            if 0 <= ny < H and 0 <= nx < W and g[ny][nx] == 0 and (ny, nx) not in seen: seen.add((ny, nx)); st.append((ny, nx))
    return {(r, c) for r in range(H) for c in range(W) if g[r][c] == 0 and (r, c) not in seen}


def tf4(g):
    E = enclosed(g); o = copy(g)
    for r, c in E: o[r][c] = 5
    n = len(components(o, 5, conn8=False))
    return [[6] * n + [0] * (8 - n)] if 1 <= n <= 8 else None
rule("fill_enclosed_grey_then_region_count_bar", "Step 1: every empty region that cannot reach the grid edge through edge-adjacent empty cells (an enclosed region) is painted colour 5. Step 2: output one row of width 8: as many colour-6 cells from the left as there are separate colour-5 regions (edge-connected), the rest empty.",
     mk(se, tf4), tf4)


# ------------------------------------------------------------------ 5 mirror left onto right -> new colours
def tf5(g):
    H, W = dims(g); h = W // 2
    if W % 2: return None
    right_old = {v for r in g for v in r[h:] if v}; right_new = {v for r in g for v in r[:h] if v}
    new = sorted(right_new - right_old)
    return [new + [0] * (9 - len(new))] if new and len(new) <= 9 else None
rule("mirror_left_onto_right_then_new_colours_row", "Step 1: the left half of the grid (even width) is mirrored left-right onto the right half, overwriting it. Step 2: output one row of width 9 listing, ascending, the colours that appear in the right half after the mirroring but did not appear there before, padded with empty cells.",
     mk(sdots(even=True, ncol=(3, 6), dens=(.03, .08)), tf5), tf5)


# ------------------------------------------------------------------ 6 delete largest -> new largest size
def tf6(g):
    cs = comps(g)
    if len(cs) < 2: return None
    big = max(cs, key=lambda o: (len(o[1]), [-o[1][0][0], -o[1][0][1]])); rest = [o for o in cs if o is not big]
    return two(max(len(o[1]) for o in rest))
rule("delete_largest_then_new_largest_size", "Step 1: the object (4-connected, same colour) with the most cells is deleted (a tie deletes the one whose first cell comes first in reading order). Step 2: output one row of two cells: the tens digit and the units digit of the cell count of the largest remaining object.",
     mk(sa(3, 7, 14), tf6), tf6, digits=True)


# ------------------------------------------------------------------ 7 recolour by class then tally regions
def tf7(g):
    H, W = dims(g); o = blank(H, W)
    for col, cells in comps(g):
        n = len(cells); k = 1 if n == 1 else 2 if n <= 3 else 3 if n <= 6 else 4
        for r, c in cells: o[r][c] = k
    return [[k, min(9, len(components(o, k, conn8=True)))] for k in (1, 2, 3, 4)]
rule("recolour_by_size_class_then_region_tally", "Step 1: every object (4-connected, same colour) is repainted by its cell count: colour 1 for 1 cell, 2 for 2-3 cells, 3 for 4-6 cells, 4 for 7 or more. Step 2: output a 4-row table, one row per class colour 1, 2, 3, 4 in that order: the class colour, then the number of 8-connected regions of that colour in the repainted grid (touching objects of one class form one region), capped at 9.",
     mk(sa(4, 9, 9, (2, 4), 0), tf7), tf7, digits=True)


# ------------------------------------------------------------------ 8 rotate -> top row run lengths
def tf8(g):
    o = rot90(g); row = o[0]; runs = []; n = 1
    for i in range(1, len(row)):
        if row[i] == row[i - 1]: n += 1
        else: runs.append(min(9, n)); n = 1
    runs.append(min(9, n)); runs = runs[:12]
    return [runs + [0] * (12 - len(runs))] if len(runs) >= 2 else None
rule("rotate_clockwise_then_top_row_run_lengths", "Step 1: the grid is rotated a quarter turn clockwise. Step 2: output one row of width 12 holding the lengths of the maximal runs of equal values (empty cells count as a value) along the rotated grid's top row, left to right, each capped at 9, only the first 12 runs, padded with empty cells.",
     mk(sdots((.2, .45), (1, 3)), tf8), tf8, digits=True)


# ------------------------------------------------------------------ 9 crop to colour 2 -> table
def s9(rng):
    g = sdots((.12, .3), (2, 4), ex=(0, 2))(rng)
    H, W = dims(g)
    for _ in range(rng.randint(2, 3)): g[rng.randrange(H)][rng.randrange(W)] = 2
    return g


def tf9(g):
    cs = cells(g, lambda v: v == 2)
    if len(cs) < 2: return None
    r0, c0, r1, c1 = bbox(cs); cnt = {}
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if g[r][c] not in (0, 2): cnt[g[r][c]] = cnt.get(g[r][c], 0) + 1
    t = sorted(cnt, key=lambda k: (-cnt[k], k))[:9]
    return [[k, min(9, cnt[k])] for k in t] or None
rule("crop_to_colour_two_then_colour_count_table", "Step 1: the grid is cropped to the bounding box of all colour-2 cells. Step 2: output a table (at most 9 rows) with one row per colour other than 2 and empty found in the crop, ordered by cell count from most to fewest (a tie goes to the lower colour value): the colour, then its cell count in the crop as a digit capped at 9.",
     mk(s9, tf9), tf9, digits=True)


# ------------------------------------------------------------------ 10 shift right with wrap -> touching right edge
def tf10(g):
    o = [[row[(c - 1) % len(row)] for c in range(len(row))] for row in g]; W = len(g[0])
    n = sum(1 for col, cells in comps(o) if any(c == W - 1 for _, c in cells))
    return two(n) if n else None
rule("shift_right_with_wrap_then_edge_touch_count", "Step 1: every cell moves one column to the right, and cells in the last column wrap around to column 0. Step 2: output one row of two cells: the tens and units digits of the number of objects (4-connected, same colour, counted after the shift) that have a cell in the last column.",
     mk(sdots((.1, .28), (2, 4)), tf10), tf10, digits=True)


# ------------------------------------------------------------------ 11 dilate -> object count
def tf11(g):
    H, W = dims(g); o = copy(g)
    for r in range(H):
        for c in range(W):
            if g[r][c]: continue
            cand = [g[r + dr][c + dc] for dr, dc in N8 if 0 <= r + dr < H and 0 <= c + dc < W and g[r + dr][c + dc]]
            if cand: o[r][c] = min(cand)
    return two(len(comps(o)))
rule("dilate_then_object_count", "Step 1: every object grows by one cell in all eight directions; each empty cell touching (including diagonally) any cell takes the lowest colour value among the cells it touches. Step 2: output one row of two cells: the tens and units digits of the number of objects (4-connected, same colour) in the grown grid.",
     mk(sa(4, 9, 5, (2, 3), 2), tf11), tf11, digits=True)


# ------------------------------------------------------------------ 12 erode -> per colour surviving cells
def tf12(g):
    H, W = dims(g); cnt = {}
    for r in range(H):
        for c in range(W):
            v = g[r][c]
            if v and all(0 <= r + dr < H and 0 <= c + dc < W and g[r + dr][c + dc] == v for dr, dc in N4): cnt[v] = cnt.get(v, 0) + 1
    return [[k, cnt[k] // 10, cnt[k] % 10] for k in sorted(cnt)] or None
rule("erode_then_surviving_cells_per_colour", "Step 1: every cell is kept only if all four of its edge neighbours exist and have its own colour (cells on the grid edge are removed); the rest are erased. Step 2: output a table with one row per colour that still has cells, ascending colour value: the colour, then the tens digit and the units digit of its remaining cell count.",
     mk(sb(), tf12), tf12, digits=True)


# ------------------------------------------------------------------ 13 fill bbox -> added cells
def tf13(g):
    n = 0; o = copy(g)
    for col, cells in comps(g, True):
        r0, c0, r1, c1 = bbox(cells)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if g[r][c] == 0 and o[r][c] == 0: o[r][c] = col; n += 1
    return two(n) if 0 < n < 100 else None
rule("fill_bounding_boxes_then_added_cell_count", "Step 1: every object (8-connected, same colour) has the empty cells inside its bounding box filled with its colour (a cell inside several boxes goes to the object first in reading order of first cells). Step 2: output one row of two cells: the tens and units digits of the number of cells that were filled.",
     mk(sb(), tf13), tf13, digits=True)


# ------------------------------------------------------------------ 14 connect row pairs -> longest run
def tf14(g):
    H, W = dims(g); o = copy(g)
    for r in range(H):
        for col in sorted({v for v in g[r] if v}):
            xs = [c for c in range(W) if g[r][c] == col]
            for c in range(xs[0], xs[-1] + 1):
                if o[r][c] == 0: o[r][c] = col
    best = 0
    for row in o:
        n = 0; prev = 0
        for v in row:
            n = n + 1 if v and v == prev else (1 if v else 0); prev = v; best = max(best, n)
    return two(best) if best else None
rule("join_row_pairs_then_longest_run", "Step 1: in every row, for each colour (ascending colour value) the empty cells between its leftmost and rightmost cell in that row are filled with that colour. Step 2: output one row of two cells: the tens and units digits of the length of the longest horizontal run of one colour anywhere in the changed grid.",
     mk(sdots((.04, .1), (2, 4)), tf14), tf14, digits=True)


# ------------------------------------------------------------------ 15 delete most frequent colour -> legend
def tf15(g):
    cnt = {}
    for row in g:
        for v in row:
            if v: cnt[v] = cnt.get(v, 0) + 1
    if len(cnt) < 3: return None
    big = min(cnt, key=lambda k: (-cnt[k], k)); rest = sorted((k for k in cnt if k != big), key=lambda k: (-cnt[k], k))
    return [rest + [0] * (9 - len(rest))]
rule("delete_commonest_colour_then_frequency_legend", "Step 1: every cell of the colour with the most cells is erased (a tie erases the lower colour value). Step 2: output one row of width 9 listing the remaining colours from most cells to fewest (a tie goes to the lower colour value), padded with empty cells.",
     mk(sdots(ncol=(3, 6)), tf15), tf15)


# ------------------------------------------------------------------ 16 recolour to size digit -> distinct row
def tf16(g):
    s = sorted({min(9, len(c)) for _, c in comps(g)})
    return [s + [0] * (9 - len(s))]
rule("recolour_to_cell_count_then_distinct_values_row", "Step 1: every object (4-connected, same colour) is repainted with the colour whose value equals its cell count (capped at 9). Step 2: output one row of width 9 listing, ascending, the distinct colours present after the repainting, padded with empty cells.",
     mk(sa(4, 9, 9, (2, 4), 1), tf16), tf16, digits=True)


# ------------------------------------------------------------------ 17 right rays -> full rows
def s17(rng):
    g = sdots((.02, .06), (2, 4))(rng); H, W = dims(g)
    for r in rng.sample(range(H), max(1, H // 3)): g[r][0] = rng.choice([v for row in g for v in row if v] or [1])
    return g


def tf17(g):
    H, W = dims(g); o = copy(g); full = 0
    for r in range(H):
        cur = 0
        for c in range(W):
            if g[r][c]: cur = g[r][c]
            elif cur: o[r][c] = cur
        if all(o[r]): full += 1
    return two(full) if full else None
rule("rays_to_the_right_then_full_row_count", "Step 1: every non-empty cell sends its colour to the right along its row, filling empty cells until the next non-empty cell or the grid edge. Step 2: output one row of two cells: the tens and units digits of the number of rows with no empty cell left.",
     mk(s17, tf17), tf17, digits=True)


# ------------------------------------------------------------------ 18 remove border objects -> bars per colour
def tf18(g):
    H, W = dims(g); cnt = {}
    for col, cells in comps(g):
        if not any(r in (0, H - 1) or c in (0, W - 1) for r, c in cells): cnt[col] = cnt.get(col, 0) + 1
    return [[k] * min(9, cnt[k]) + [0] * (9 - min(9, cnt[k])) for k in sorted(cnt)] or None
rule("drop_border_objects_then_colour_bar_rows", "Step 1: every object (4-connected, same colour) with a cell on the grid edge is erased. Step 2: output one row of width 9 per colour that still has objects, ascending colour value: a bar of that colour as long as its number of remaining objects (capped at 9), padded with empty cells.",
     mk(sa(4, 9, 6, (2, 4)), tf18), tf18)


# ------------------------------------------------------------------ 19 hollow out -> removed count
def tf19(g):
    H, W = dims(g); n = 0
    for r in range(H):
        for c in range(W):
            v = g[r][c]
            if v and all(0 <= r + dr < H and 0 <= c + dc < W and g[r + dr][c + dc] == v for dr, dc in N8): n += 1
    return two(n) if 0 < n < 100 else None
rule("hollow_out_then_interior_cell_count", "Step 1: every object is hollowed out: a cell is erased if all eight of its neighbours exist and have its own colour (only the outline remains). Step 2: output one row of two cells: the tens and units digits of the number of cells erased.",
     mk(sb(), tf19), tf19, digits=True)


# ------------------------------------------------------------------ 20 fill holes -> per colour added cells
def tf20(g):
    H, W = dims(g); E = enclosed(g); cnt = {}
    for r, c in E:
        cand = [g[r + dr][c + dc] for dr, dc in N4 if 0 <= r + dr < H and 0 <= c + dc < W and g[r + dr][c + dc]]
        if not cand: continue
    for comp in components(blank(H, W), 0, conn8=False) if False else []: pass
    o = copy(g); seen = set()
    for r, c in sorted(E):
        if (r, c) in seen: continue
        st = [(r, c)]; seen.add((r, c)); reg = []
        while st:
            y, x = st.pop(); reg.append((y, x))
            for dr, dc in N4:
                p = (y + dr, x + dc)
                if p in E and p not in seen: seen.add(p); st.append(p)
        nb = {}
        for y, x in reg:
            for dr, dc in N4:
                if 0 <= y + dr < H and 0 <= x + dc < W and g[y + dr][x + dc]: nb[g[y + dr][x + dc]] = nb.get(g[y + dr][x + dc], 0) + 1
        col = min(nb, key=lambda k: (-nb[k], k))
        for y, x in reg: o[y][x] = col
        cnt[col] = cnt.get(col, 0) + len(reg)
    return [[k, cnt[k] // 10, cnt[k] % 10] for k in sorted(cnt)] or None
rule("fill_holes_then_filled_cells_per_colour", "Step 1: every empty region that cannot reach the grid edge through edge-adjacent empty cells is filled with the colour of the cells touching it most often (a tie goes to the lower colour value). Step 2: output a table with one row per colour that filled something, ascending colour value: the colour, then the tens digit and units digit of the number of cells it filled.",
     mk(se, tf20), tf20, digits=True)


# ------------------------------------------------------------------ 22 swap halves -> changed cells
def tf22(g):
    H, W = dims(g)
    if W % 2: return None
    h = W // 2; o = [row[h:] + row[:h] for row in g]
    n = sum(1 for r in range(H) for c in range(W) if o[r][c] != g[r][c])
    return two(n) if 0 < n < 100 else None
rule("swap_halves_then_changed_cell_count", "Step 1: the left half and the right half of the grid (even width) trade places. Step 2: output one row of two cells: the tens and units digits of the number of cells whose value differs from the original grid (capped at 99).",
     mk(sdots((.02, .06), (2, 4), even=True), tf22), tf22, digits=True)


# ------------------------------------------------------------------ 27 seed flood -> remaining empty regions
def s27(rng):
    g = sdots((.18, .3), (1, 1), ex=(0, 2, 3))(rng)
    for r in range(len(g)):
        for c in range(len(g[0])):
            if g[r][c]: g[r][c] = 5
    H, W = dims(g)
    for _ in range(rng.randint(1, 2)): g[rng.randrange(H)][rng.randrange(W)] = 2
    return g


def tf27(g):
    H, W = dims(g); seeds = cells(g, lambda v: v == 2)
    if not seeds: return None
    o = copy(g); d = {}
    st = list(seeds); seen = set(st)
    while st:
        y, x = st.pop()
        for dr, dc in N4:
            ny, nx = y + dr, x + dc
            if 0 <= ny < H and 0 <= nx < W and o[ny][nx] == 0 and (ny, nx) not in seen: seen.add((ny, nx)); o[ny][nx] = 3; st.append((ny, nx))
    n = len(components(o, 0, conn8=False))
    return two(n) if 0 < n < 100 else None
rule("seed_flood_then_leftover_empty_regions", "Step 1: every empty cell reachable from a colour-2 cell through edge-adjacent empty cells is painted colour 3 (cells of colour 5 block it). Step 2: output one row of two cells: the tens and units digits of the number of separate (edge-connected) empty regions still left.",
     mk(s27, tf27), tf27, digits=True)


# ------------------------------------------------------------------ 29 remove smallest per colour -> table
def tf29(g):
    cnt = {}; by = {}
    for col, cells in comps(g): by.setdefault(col, []).append(cells)
    for col, L in by.items():
        if len(L) >= 2:
            sm = min(L, key=lambda c: (len(c), c[0])); L = [c for c in L if c is not sm]
        cnt[col] = len(L)
    return [[k, min(9, cnt[k])] for k in sorted(cnt)]
rule("drop_smallest_per_colour_then_object_count_table", "Step 1: for every colour with two or more objects (4-connected, same colour), its object with the fewest cells is erased (a tie erases the one whose first cell comes first in reading order); colours with a single object lose nothing. Step 2: output a table with one row per colour, ascending colour value: the colour, then its number of remaining objects as a digit capped at 9.",
     mk(sa(4, 9, 6, (2, 3)), tf29), tf29, digits=True)


# ------------------------------------------------------------------ 30 keep largest per colour -> sizes
def tf30(g):
    by = {}
    for col, cells in comps(g):
        if col not in by or len(cells) > len(by[col][0]) : by[col] = (cells,)
    rows = sorted(by, key=lambda k: (-len(by[k][0]), k))
    return [[k, min(9, len(by[k][0]))] for k in rows]
rule("keep_largest_per_colour_then_size_ranking", "Step 1: for every colour only its largest object (4-connected, same colour; a tie keeps the one whose first cell comes first in reading order) is kept. Step 2: output a table with one row per colour, ordered from the largest kept object to the smallest (a tie goes to the lower colour value): the colour, then that object's cell count as a digit capped at 9.",
     mk(sa(4, 9, 9, (3, 5)), tf30), tf30, digits=True)


# ------------------------------------------------------------------ 31 recolour by top-row parity -> two bars
def tf31(g):
    H, W = dims(g); o = blank(H, W)
    for col, cells in comps(g):
        k = 3 if min(r for r, _ in cells) % 2 == 0 else 4
        for r, c in cells: o[r][c] = k
    a, b = len(components(o, 3, conn8=False)), len(components(o, 4, conn8=False))
    return [[3] * min(a, 10) + [0] * (10 - min(a, 10)), [4] * min(b, 10) + [0] * (10 - min(b, 10))] if a or b else None
rule("recolour_by_top_row_parity_then_region_bars", "Step 1: every object (4-connected, same colour) is repainted colour 3 if its topmost row has an even index (counting rows from 0) and colour 4 if odd. Step 2: output two rows of width 10: a colour-3 bar as long as the number of edge-connected colour-3 regions (touching objects form one region), then a colour-4 bar likewise, each capped at 10 and padded with empty cells.",
     mk(sa(4, 9, 7, (2, 4), 0), tf31), tf31)


# ------------------------------------------------------------------ 32 trails down -> bottom row legend
def tf32(g):
    H, W = dims(g); o = copy(g)
    for c in range(W):
        cur = 0
        for r in range(H):
            if g[r][c]: cur = g[r][c]
            elif cur: o[r][c] = cur
    seen = []
    for v in o[-1]:
        if v and v not in seen: seen.append(v)
    return [seen + [0] * (9 - len(seen))] if seen and len(seen) <= 9 else None
rule("trails_down_then_bottom_row_legend", "Step 1: every non-empty cell sends its colour straight down its column, filling empty cells until the next non-empty cell or the floor. Step 2: output one row of width 9 listing the distinct colours of the changed grid's bottom row in order of first appearance from left to right, padded with empty cells.",
     mk(sdots((.01, .04), (3, 6), lo=10), tf32), tf32)


# ------------------------------------------------------------------ 34 fold overlay -> row counts
def tf34(g):
    H, W = dims(g)
    if W % 2: return None
    h = W // 2; col = []
    for r in range(H):
        left = g[r][:h]; right = g[r][h:][::-1]; col.append([min(9, sum(1 for a, b in zip(left, right) if a or b))])
    return col
rule("fold_halves_then_row_count_column", "Step 1: the right half of the grid (even width) is folded over onto the left half by mirroring it left-right, so a cell of the folded grid is non-empty if either its own or its mirrored cell is. Step 2: output one column as tall as the grid holding, per row, the number of non-empty cells of the folded half as a digit capped at 9.",
     mk(sdots((.03, .1), (2, 4), even=True), tf34), tf34, digits=True)


# ------------------------------------------------------------------ extras
def tf35(g):
    cnt = {}
    for row in g:
        for v in row:
            if v: cnt[v] = cnt.get(v, 0) + 1
    if len(cnt) < 2: return None
    least = min(cnt, key=lambda k: (cnt[k], -k)); o = [[0 if v == least else v for v in row] for row in g]
    return two(len(comps(o)))
rule("delete_rarest_colour_then_object_count", "Step 1: every cell of the colour with the fewest cells is erased (a tie erases the higher colour value). Step 2: output one row of two cells: the tens and units digits of the number of objects (4-connected, same colour) left.",
     mk(sa(4, 9, 6, (3, 5), 1), tf35), tf35, digits=True)


def tf36(g):
    o = [[v for v in row if v] for row in g]; n = sum(1 for r in o if r and len(set(r)) == 1)
    return two(n) if n else None
rule("slide_left_then_uniform_row_count", "Step 1: in every row the non-empty cells slide left, keeping their order, with no gaps. Step 2: output one row of two cells: the tens and units digits of the number of non-empty rows whose cells are now all one colour.",
     mk(sdots((.02, .07), (2, 3)), tf36), tf36, digits=True)


def tf37(g):
    H, W = dims(g); cnt = {}
    for row in g:
        for v in row:
            if v: cnt[v] = cnt.get(v, 0) + 1
    if len(cnt) < 2: return None
    o_ = sorted(cnt, key=lambda k: (-cnt[k], k)); a, b = o_[0], o_[1]
    sw = {a: b, b: a}; cnt2 = {sw.get(k, k): v for k, v in cnt.items()}
    t = sorted(cnt2, key=lambda k: (-cnt2[k], k))
    return [[k] * min(9, -(-cnt2[k] // 4)) + [0] * (9 - min(9, -(-cnt2[k] // 4))) for k in t[:9]]
rule("swap_top_two_colours_then_count_bars", "Step 1: the colour with the most cells and the colour with the second most (a tie goes to the lower colour value) trade colours: every cell of one becomes the other. Step 2: output one row of width 9 per colour present, ordered by cell count from most to fewest after the swap (a tie goes to the lower colour value): a bar of that colour of ceil(cell count / 4) cells, capped at 9, padded with empty cells.",
     mk(sdots((.03, .08), (3, 5)), tf37), tf37)


def tf38(g):
    o = [row[::-1] for row in g[::-1]]
    seen = []
    for col, cells in comps(o):
        if col not in seen: seen.append(col)
    return [seen + [0] * (9 - len(seen))] if len(seen) <= 9 else None
rule("rotate_half_turn_then_reading_order_colours", "Step 1: the grid is turned upside down and back to front (a half turn). Step 2: output one row of width 9 listing the colours of the changed grid in order of the first cell of each colour in reading order (row by row, left to right), each colour once, padded with empty cells.",
     mk(sa(3, 8, 6, (3, 6)), tf38), tf38)
