# b083_assembly2.py -- OUTPUT ASSEMBLED FROM PIECES, SECOND SET: the output is a new grid built from cropped objects,
# panels, quadrants, rows/columns or corner blocks of the input (ordered by size/colour/parity, scaled, outlined, mirrored,
# labelled, interleaved, overlaid, joined in a stated order with stated gaps and alignment).
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

GREY = 5


def D(rng, lo=8, hi=30):
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


def objs(g):
    out = []
    for col in sorted({v for r in g for v in r if v}):
        for c in components(g, col, conn8=True): out.append((col, sorted(c)))
    return sorted(out, key=lambda o: o[1][0])


def cropo(g, cells):
    r0, c0, r1, c1 = bbox(cells); s = blank(r1 - r0 + 1, c1 - c0 + 1)
    for r, c in cells: s[r - r0][c - c0] = g[r][c]
    return s


def hcat(parts, gap=0, align='top'):
    H = max(len(p) for p in parts); W = sum(len(p[0]) for p in parts) + gap * (len(parts) - 1); out = blank(H, W); x = 0
    for p in parts:
        paste(out, p, 0 if align == 'top' else H - len(p), x); x += len(p[0]) + gap
    return out


def vcat(parts, gap=0, align='left'):
    W = max(len(p[0]) for p in parts); H = sum(len(p) for p in parts) + gap * (len(parts) - 1); out = blank(H, W); y = 0
    for p in parts:
        paste(out, p, y, 0 if align == 'left' else W - len(p[0])); y += len(p) + gap
    return out


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
def sa(kmin=3, kmax=7, cmax=8, distinct=True, ex=(0,)):
    """scattered random connected shapes"""
    def gen(rng):
        H, Wd = D(rng, 8, 30), D(rng, 8, 30); k = rng.randint(kmin, max(kmin, min(kmax, 1 + H * Wd // 50)))
        pool = [c for c in range(1, 10) if c not in ex]; cs = rng.sample(pool, k) if distinct and k <= len(pool) else [rng.choice(pool) for _ in range(k)]
        g = blank(H, Wd)
        return g if place_shapes(rng, g, [random_shape(rng, rng.randint(1, cmax)) for _ in range(k)], cs, margin=1) else None
    return gen


def blob(rng, ex=(0,)):
    h, w = rng.randint(3, 6), rng.randint(3, 6); S = set()
    for _ in range(rng.randint(2, 3)):
        rh, rw = rng.randint(2, h), rng.randint(2, w); r0, c0 = rng.randint(0, h - rh), rng.randint(0, w - rw)
        S |= {(r, c) for r in range(r0, r0 + rh) for c in range(c0, c0 + rw)}
    r0, c0, r1, c1 = bbox(list(S)); return S, r1 - r0 + 1, c1 - c0 + 1


def sb(kmin=2, kmax=5, ex=(0,)):
    def gen(rng):
        H, Wd = D(rng, 10, 30), D(rng, 10, 30); k = rng.randint(kmin, kmax); cs = rng.sample([c for c in range(1, 10) if c not in ex], k); subs = []
        for col in cs:
            S, h, w = blob(rng); r0, c0 = bbox(list(S))[:2]; s = blank(h, w)
            for r, c in S: s[r - r0][c - c0] = col
            subs.append(s)
        return scatter_subs(rng, H, Wd, subs)
    return gen


def box_obj(rng, h, w, col):
    s = blank(h, w); rect(s, 0, 0, h - 1, w - 1, col, fill=False)
    for r in range(1, h - 1):
        for c in range(1, w - 1):
            if rng.random() < .45: s[r][c] = col
    return s


def s4(kmin=2, kmax=4, even=False):
    def gen(rng):
        H, Wd = D(rng, 10, 30), D(rng, 10, 30); h = rng.randint(4, 6); w = rng.choice((4, 6)) if even else rng.randint(4, 6)
        k = rng.randint(kmin, kmax); cs = rng.sample(range(1, 10), k); subs = [box_obj(rng, h, w, c) for c in cs]
        if len({tuple(map(tuple, s)) for s in subs}) < k: return None
        return scatter_subs(rng, H, Wd, subs)
    return gen


def s3(dens=(.35, .6), ncol=(2, 4), even=False, lo=8):
    def gen(rng):
        H, Wd = D(rng, lo, 30), D(rng, lo, 30)
        if even: H, Wd = H - H % 2, Wd - Wd % 2
        pc = rng.sample(range(1, 10), rng.randint(*ncol)); d = rng.uniform(*dens)
        return [[rng.choice(pc) if rng.random() < d else 0 for _ in range(Wd)] for _ in range(H)]
    return gen


def panel(rng, h, w, pc, d):
    return [[rng.choice(pc) if rng.random() < d else 0 for _ in range(w)] for _ in range(h)]


def s2(equal=False, kmin=3, kmax=5, marker=False):
    def gen(rng):
        h = D(rng, 4, 26); k = rng.randint(kmin, kmax); w0 = rng.randint(4, 6); ws = [w0] * k if equal else [rng.randint(4, 6) for _ in range(k)]
        if h > 30 or sum(ws) + k - 1 > 30: return None
        pc = [c for c in range(1, 10) if c not in (GREY, 4)][:] if marker else [c for c in range(1, 10) if c != GREY]
        pcs = rng.sample(pc, rng.randint(2, 4)); ps = [panel(rng, h, w, pcs, rng.uniform(.25, .55)) for w in ws]
        if marker:
            i = rng.randrange(k); r, c = rng.randrange(h), rng.randrange(ws[i]); ps[i][r][c] = 4
        parts = []
        for i, p in enumerate(ps):
            if i: parts.append([[GREY] for _ in range(h)])
            parts.append(p)
        return hcat(parts)
    return gen


def split_cols(g):
    """panels separated by full grey columns"""
    W = len(g[0]); seps = [c for c in range(W) if all(r[c] == GREY for r in g)]; ps = []; x = 0
    for s in seps + [W]:
        if s > x: ps.append([r[x:s] for r in g])
        x = s + 1
    return ps


# ------------------------------------------------------------------ object rules
def tf1(g):
    os_ = objs(g)
    if len(os_) < 2: return None
    return hcat([cropo(g, c) for _, c in sorted(os_, key=lambda o: (len(o[1]), o[1][0]))], 1)
rule("objects_row_ascending_size_gap_one", "Each object (8-connected, same colour) is cropped to its bounding box and laid left to right in a row from fewest cells to most (a tie goes to the object whose first cell comes first in reading order), top-aligned, with one empty column between neighbours.",
     mk(sa(), tf1), tf1)


def tf2(g):
    os_ = objs(g)
    if len(os_) < 2: return None
    return vcat([cropo(g, c) for _, c in sorted(os_, key=lambda o: (o[0], o[1][0]))], 1, 'left')
rule("objects_column_ascending_colour_value", "Each object (8-connected, same colour) is cropped to its bounding box and stacked top to bottom from the lowest colour value to the highest (objects of one colour keep reading order), left-aligned, with one empty row between neighbours.",
     mk(sa(distinct=False), tf2), tf2, digits=True)


def tf3(g):
    os_ = sorted(objs(g), key=lambda o: (-len(o[1]), o[1][0]))
    if len(os_) < 2: return None
    return hcat([cropo(g, os_[0][1]), cropo(g, os_[1][1])], 1)
rule("two_largest_objects_side_by_side", "Only the two objects (8-connected, same colour) with the most cells are kept (a tie goes to the object whose first cell comes first in reading order); they are cropped to their bounding boxes and laid side by side, larger on the left, top-aligned, with one empty column between.",
     mk(sa(), tf3), tf3)


def tf4(g):
    os_ = objs(g)
    if len(os_) < 2: return None
    cr = [cropo(g, c) for _, c in os_]; m = max(max(len(s), len(s[0])) for s in cr); k = 1
    while k * k < len(cr): k += 1
    out = blank(k * m, k * m)
    for i, s in enumerate(cr): paste(out, s, (i // k) * m, (i % k) * m)
    return out
rule("objects_packed_into_smallest_square_of_boxes", "Let m be the largest side of any object's bounding box and n the object count; the output is a k by k arrangement of m by m boxes, k the smallest integer with k*k >= n, the objects (8-connected, same colour) filling the boxes row by row in reading order, each object cropped and placed at the top-left of its box, unused boxes empty.",
     mk(sa(3, 9, 6), tf4), tf4)


def tf5(g):
    H, W = dims(g); h, w = H // 2, W // 2
    q = lambda a, b: [row[b * w:(b + 1) * w] for row in g[a * h:(a + 1) * h]]
    return vcat([hcat([q(1, 1), q(0, 0)]), hcat([q(0, 1), q(1, 0)])]) if False else hcat([q(1, 1), q(0, 0)]) and (lambda tl, tr, bl, br: [a + b for a, b in zip(tl, tr)] + [a + b for a, b in zip(bl, br)])(q(1, 1), q(0, 0), q(0, 1), q(1, 0))
rule("quadrants_rearranged_clockwise_shift", "The grid is cut into four equal quadrants (even sides) and reassembled: the top-left of the output is the input's bottom-right quadrant, the top-right is the input's top-left, the bottom-left is the input's top-right and the bottom-right is the input's bottom-left.",
     mk(s3(even=True), tf5), tf5)


def tf6(g):
    os_ = objs(g)
    if len(os_) != 1: return None
    s = cropo(g, os_[0][1]); return vcat([hcat([s, s]), hcat([s, s])])
rule("single_object_tiled_two_by_two", "The one object is cropped to its bounding box and repeated in a 2x2 tiling of copies that touch, all copies identical to the original.",
     mk(sa(1, 1, 9), tf6), tf6)


def tf7(g):
    os_ = objs(g)
    if len(os_) < 2: return None
    rows = []
    for col, cells in os_:
        r0, c0, r1, c1 = bbox(cells); S = set(cells); rows.append([[g[r0][c] if (r0, c) in S else 0 for c in range(c0, c1 + 1)]])
    return vcat(rows, 0, 'left')
rule("top_row_of_each_object_stacked", "For each object (8-connected, same colour) in reading order of its first cell, take only the top row of its bounding box (its own cells there, empty cells elsewhere in the row); the rows are stacked top to bottom, left-aligned, touching, padded on the right with empty cells to the widest.",
     mk(sa(3, 7, 7), tf7), tf7)


def tf8(g):
    os_ = objs(g)
    if len(os_) < 2: return None
    cols = []
    for col, cells in os_:
        r0, c0, r1, c1 = bbox(cells); S = set(cells); cols.append([[g[r][c0] if (r, c0) in S else 0] for r in range(r0, r1 + 1)])
    return hcat(cols, 0, 'top')
rule("leftmost_column_of_each_object_strips", "For each object (8-connected, same colour) in reading order of its first cell, take only the leftmost column of its bounding box (its own cells there, empty cells elsewhere in the column); the columns are laid left to right, top-aligned, touching, padded below with empty cells to the tallest.",
     mk(sa(3, 7, 7), tf8), tf8)


def tf9(g):
    os_ = objs(g); odd = [cropo(g, c) for col, c in os_ if col % 2]; even = [cropo(g, c) for col, c in os_ if col % 2 == 0]
    if not odd or not even: return None
    return hcat([vcat(odd, 1), vcat(even, 1)], 1, 'top')
rule("objects_two_columns_by_colour_parity", "Each object (8-connected, same colour) is cropped to its bounding box; objects of odd colour value are stacked in the left column and objects of even colour value in the right column, each column in reading order of the objects' first cells, left-aligned with one empty row between neighbours, the two columns top-aligned with one empty column between them.",
     mk(sa(3, 7, 7, False), tf9), tf9, digits=True)


def tf10(g):
    os_ = objs(g)
    if len(os_) < 2: return None
    cr = [cropo(g, c) for _, c in os_]; Hm = max(len(s) for s in cr); parts = []
    for s in cr:
        h, w = len(s), len(s[0]); nw = max(1, (w * Hm) // h); parts.append([[s[(r * h) // Hm][(c * w) // nw] for c in range(nw)] for r in range(Hm)])
    return hcat(parts, 1)
rule("objects_scaled_to_tallest_height_row", "Let H be the tallest bounding-box height among the objects (8-connected, same colour); each object is cropped and rescaled by nearest neighbour to height H and width max(1, floor(width*H/height)) (output cell (r,c) copies source cell (floor(r*height/H), floor(c*width/newwidth))), and the results are laid left to right in reading order of the objects' first cells with one empty column between.",
     mk(sa(2, 5, 8), tf10), tf10)


def tf11(g):
    os_ = objs(g)
    if len(os_) < 2: return None
    parts = []
    for col, cells in os_:
        S = set(cells); r0, c0, r1, c1 = bbox(cells); s = blank(r1 - r0 + 1, c1 - c0 + 1)
        for r, c in cells:
            if not all((r + dr, c + dc) in S for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))): s[r - r0][c - c0] = col
        parts.append(s)
    return hcat(parts, 1)
rule("object_outlines_only_row", "Each object (8-connected, same colour) is cropped to its bounding box and reduced to its outline (every cell whose four edge neighbours are not all object cells is kept, the inner cells are erased); the outlines are laid left to right in reading order of the objects' first cells, top-aligned, with one empty column between.",
     mk(sb(), tf11, lambda g, o: True), tf11)


def tf12(g):
    os_ = objs(g)
    if len(os_) < 2: return None
    return vcat([hcat([s, flip_h(s)]) for s in [cropo(g, c) for _, c in os_]], 1, 'left')
rule("each_object_followed_by_its_mirror", "Each object (8-connected, same colour) is cropped to its bounding box and placed immediately left of its own left-right mirror image (touching); these pairs are stacked top to bottom in reading order of the objects' first cells, left-aligned, with one empty row between.",
     mk(sb(), tf12), tf12)


def tf13(g):
    os_ = objs(g)
    if len(os_) < 2: return None
    cr = [(len(s), s) for s in [cropo(g, c) for _, c in os_]]
    return hcat([s for _, s in sorted(enumerate(cr), key=lambda t: (-t[1][0], t[0]))] and [t[1][1] for t in sorted(enumerate(cr), key=lambda t: (-t[1][0], t[0]))], 1, 'bottom')
rule("objects_on_shared_baseline_tallest_first", "Each object (8-connected, same colour) is cropped to its bounding box; they are laid left to right ordered by bounding-box height, tallest first (a tie goes to the earlier object in reading order of first cells), all resting on the bottom row of the output, with one empty column between.",
     mk(sb(), tf13), tf13)


def tf14(g):
    os_ = objs(g)
    if len(os_) < 2: return None
    cr = sorted(enumerate([cropo(g, c) for _, c in os_]), key=lambda t: (len(t[1][0]), t[0]))
    return vcat([s for _, s in cr], 0, 'right')
rule("objects_stacked_right_aligned_narrowest_first", "Each object (8-connected, same colour) is cropped to its bounding box and stacked top to bottom from the narrowest bounding box to the widest (a tie goes to the earlier object in reading order of first cells), touching, aligned to the right edge.",
     mk(sb(), tf14), tf14)


def tf31(g):
    os_ = objs(g)
    if len(os_) < 2 or any(col == GREY for col, _ in os_): return None
    parts = []
    for col, cells in os_:
        s = cropo(g, cells); h, w = dims(s); p = blank(h + 2, w + 2, GREY); paste(p, s, 1, 1); parts.append(p)
    return hcat(parts, 0)
rule("objects_in_grey_frames_joined_row", "Each object (8-connected, same colour, never grey) is cropped to its bounding box and surrounded by a one-cell frame of colour 5; the framed pieces are laid left to right in reading order of the objects' first cells, touching, top-aligned.",
     mk(sb(ex=(0, GREY)), tf31), tf31)


def tf32(g):
    os_ = objs(g)
    if len(os_) < 2: return None
    parts = []
    for col, cells in os_:
        s = cropo(g, cells); lab = [[min(9, len(cells))] + [0] * (len(s[0]) - 1)]; parts.append(vcat([lab, s]))
    return hcat(parts, 1)
rule("objects_with_size_digit_label_row", "Each object (8-connected, same colour) is cropped to its bounding box and given one extra row on top whose leftmost cell holds its cell count as a digit (capped at 9) and whose other cells are empty; the labelled pieces are laid left to right in reading order of the objects' first cells, top-aligned, with one empty column between.",
     mk(sb(), tf32), tf32, digits=True)


def tf33(g):
    os_ = objs(g)
    if len(os_) < 2: return None
    parts = []
    for col, cells in sorted(os_, key=lambda o: (-(bbox(o[1])[2] - bbox(o[1])[0] + 1) * (bbox(o[1])[3] - bbox(o[1])[1] + 1), o[1][0])):
        r0, c0, r1, c1 = bbox(cells); parts.append([[col] * (c1 - c0 + 1) for _ in range(r1 - r0 + 1)])
    return hcat(parts, 1)
rule("filled_bounding_boxes_largest_area_first", "Each object (8-connected, same colour) is replaced by a solid rectangle of its colour the size of its bounding box; the rectangles are laid left to right from the largest bounding-box area to the smallest (a tie goes to the earlier object in reading order of first cells), top-aligned, with one empty column between.",
     mk(sa(3, 7, 8), tf33), tf33)


# ------------------------------------------------------------------ panel rules
def tf15(g):
    ps = split_cols(g)
    if len(ps) < 2: return None
    return hcat(ps[::-1])
rule("panels_joined_in_reverse_without_grey", "The grey (5) columns split the grid into panels; the panels are joined in reverse order, last panel first, touching, with the grey columns removed.",
     mk(s2(), tf15), tf15)


def tf16(g):
    ps = split_cols(g); m = [i for i, p in enumerate(ps) if any(v == 4 for r in p for v in r)]
    if len(ps) < 2 or len(m) != 1: return None
    return hcat([ps[m[0]]] + [p for i, p in enumerate(ps) if i != m[0]])
rule("marker_panel_first_then_the_rest", "The grey (5) columns split the grid into panels and exactly one panel contains a colour-4 marker cell; the panels are joined touching, grey columns removed, with the marker panel first followed by the other panels in their original left-to-right order.",
     mk(s2(marker=True), tf16), tf16)


def tf17(g):
    ps = split_cols(g)
    if len(ps) < 2: return None
    return hcat([p for _, p in sorted(enumerate(ps), key=lambda t: (sum(1 for r in t[1] for v in r if v), t[0]))])
rule("panels_ordered_by_filled_cells_ascending", "The grey (5) columns split the grid into panels; the panels are joined touching, grey columns removed, from the one with the fewest non-empty cells to the one with the most (a tie keeps the original left-to-right order).",
     mk(s2(), tf17), tf17)


def tf19(g):
    ps = split_cols(g)
    if len(ps) < 2 or len({(len(p), len(p[0])) for p in ps}) != 1: return None
    return [[max(p[r][c] for p in ps) for c in range(len(ps[0][0]))] for r in range(len(ps[0]))]
rule("equal_panels_overlaid_highest_colour_wins", "The grey (5) columns split the grid into equally sized panels; the output is one panel in which each cell holds the highest colour value found at that position across all panels (empty if every panel is empty there).",
     mk(s2(True, 3, 5), tf19), tf19, digits=True)


def grid_panels(rng):
    r_, c_ = rng.randint(2, 4), rng.randint(2, 5); h, w = rng.randint(3, 6), rng.randint(3, 6)
    if rng.random() < .5: r_, c_, h, w = rng.randint(3, 4), rng.randint(4, 5), rng.randint(5, 6), rng.randint(5, 6)
    if r_ * h + r_ - 1 > 30 or c_ * w + c_ - 1 > 30: return None
    pcs = rng.sample([c for c in range(1, 10) if c != GREY], rng.randint(2, 4)); g = blank(r_ * h + r_ - 1, c_ * w + c_ - 1)
    for i in range(r_):
        for j in range(c_): paste(g, panel(rng, h, w, pcs, rng.uniform(.3, .6)), i * (h + 1), j * (w + 1))
    for i in range(1, r_): g[i * (h + 1) - 1] = [GREY] * len(g[0])
    for j in range(1, c_):
        for r in range(len(g)): g[r][j * (w + 1) - 1] = GREY
    return g


def tf41(g):
    H, W = dims(g); rs = [r for r in range(H) if all(v == GREY for v in g[r])]; cs = [c for c in range(W) if all(g[r][c] == GREY for r in range(H))]
    rb, x = [], 0
    for s in rs + [H]:
        rb.append((x, s)); x = s + 1
    cb, x = [], 0
    for s in cs + [W]:
        cb.append((x, s)); x = s + 1
    parts = []
    for i, (a, b) in enumerate(rb):
        row = [[r[c0:c1] for r in g[a:b]] for c0, c1 in cb]
        parts += row if i % 2 == 0 else row[::-1]
    return hcat(parts) if len(parts) > 1 else None
rule("panel_grid_unrolled_in_snake_row", "Grey (5) lines split the grid into a grid of equal panels; the panels are joined into one row, touching, grey lines removed, taking the first panel row left to right, the second panel row right to left, the third left to right again, and so on.",
     mk(grid_panels, tf41), tf41, small_ok=True)


# ------------------------------------------------------------------ quadrant and strip rules
def quads(g):
    H, W = dims(g); h, w = H // 2, W // 2
    return [[row[b * w:(b + 1) * w] for row in g[a * h:(a + 1) * h]] for a in (0, 1) for b in (0, 1)]


def tf21(g):
    q = quads(g); h, w = len(q[0]), len(q[0][0])
    return [[next((qq[r][c] for qq in q if qq[r][c]), 0) for c in range(w)] for r in range(h)]
rule("quadrants_overlaid_top_left_first", "The grid (even sides) is cut into four equal quadrants and they are stacked into one quadrant-sized grid: each cell takes the value from the first non-empty quadrant in the order top-left, top-right, bottom-left, bottom-right (empty if all four are empty there).",
     mk(s3((.15, .35), even=True), tf21), tf21)


def tf22(g): return vcat(quads(g))
rule("quadrants_stacked_in_reading_order", "The grid (even sides) is cut into four equal quadrants and they are stacked into a single column, touching, in the order top-left, top-right, bottom-left, bottom-right.",
     mk(s3(even=True, lo=8), tf22), tf22)


def tf23(g):
    q = quads(g); return hcat([p for _, p in sorted(enumerate(q), key=lambda t: (sum(1 for r in t[1] for v in r if v), t[0]))])
rule("quadrants_in_a_row_by_filled_cells", "The grid (even sides) is cut into four equal quadrants and they are laid left to right, touching, from the quadrant with the fewest non-empty cells to the one with the most (a tie goes to the earlier quadrant in the order top-left, top-right, bottom-left, bottom-right).",
     mk(s3((.15, .5), even=True), tf23), tf23)


def tf35(g):
    H, W = dims(g)
    if H < 6 or W < 6: return None
    b = lambda r, c: [row[c:c + 3] for row in g[r:r + 3]]
    return vcat([hcat([b(0, 0), b(0, W - 3)]), hcat([b(H - 3, 0), b(H - 3, W - 3)])])
rule("four_corner_blocks_joined_square", "The four 3x3 blocks at the corners of the grid are cut out and joined into one 6x6 grid: top-left block at the top-left, top-right block at the top-right, bottom-left block at the bottom-left, bottom-right block at the bottom-right, touching.",
     mk(s3((.3, .6)), tf35), tf35)


def tf37a(g):
    return g[0::2] + g[1::2] if len(g) > 2 else None
rule("even_rows_then_odd_rows", "The rows are regrouped: first all rows with an even 0-based index (0, 2, 4 ...) in their original order, then all rows with an odd index (1, 3, 5 ...) in their original order; the width stays the same.",
     mk(s3(), tf37a), tf37a)


def tf37b(g):
    return [row[0::2] + row[1::2] for row in g]
rule("even_columns_then_odd_columns", "The columns are regrouped: first all columns with an even 0-based index (0, 2, 4 ...) in their original order, then all columns with an odd index (1, 3, 5 ...) in their original order; the height stays the same.",
     mk(s3(), tf37b), tf37b)


# ------------------------------------------------------------------ equally boxed objects
def boxed(g):
    os_ = objs(g); cr = [cropo(g, c) for _, c in os_]
    if len(cr) < 2 or len({(len(s), len(s[0])) for s in cr}) != 1: return None
    return cr


def tf27(g):
    cr = boxed(g)
    if not cr or len(cr) != 2: return None
    A, B = cr; w = len(A[0]); return [A[r][:w // 2] + B[r][w // 2:] for r in range(len(A))]
rule("left_half_of_first_right_half_of_second", "Two equally boxed objects (8-connected, same colour, even width) are cropped; the output is one box whose left half (the first width/2 columns) comes from the object whose first cell is earlier in reading order and whose right half comes from the other object.",
     mk(s4(2, 2, True), tf27), tf27)


def tf28(g):
    cr = boxed(g)
    if not cr or len(cr) != 2: return None
    A, B = cr; return vcat([hcat([A, B]), hcat([B, A])])
rule("two_objects_alternating_two_by_two", "Two equally boxed objects (8-connected, same colour) are cropped and tiled 2x2, touching, as [first, second] over [second, first], where first is the object whose first cell is earlier in reading order.",
     mk(s4(2, 2), tf28), tf28)


def tf29(g):
    cr = boxed(g)
    if not cr: return None
    n = len(cr); return [[cr[c % n][r][c] for c in range(len(cr[0][0]))] for r in range(len(cr[0]))]
rule("column_j_taken_from_object_j_mod_n", "N equally boxed objects (8-connected, same colour) are cropped and numbered 0..N-1 in reading order of their first cells; the output is one box in which column j is copied from object (j mod N).",
     mk(s4(2, 4), tf29), tf29)


def tf30(g):
    cr = boxed(g)
    if not cr: return None
    n = len(cr); return [cr[r % n][r][:] for r in range(len(cr[0]))]
rule("row_i_taken_from_object_i_mod_n", "N equally boxed objects (8-connected, same colour) are cropped and numbered 0..N-1 in reading order of their first cells; the output is one box in which row i is copied from object (i mod N).",
     mk(s4(2, 4), tf30), tf30)
