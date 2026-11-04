# b069_cuts.py -- CUTS, HALVES AND COMPLEMENTS: a shape is cut by a straight, stepped or jagged line (the cut's own colour
# or a gap) into faces that fit each other exactly. Missing halves, matching loose halves by cut profile (translation,
# mirror, rotation), reassembly, cut moves, exposed faces, pieces counted/ranked/kept, bounding-box complements.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


def D(rng, lo=8, hi=30):
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


def prof(rng, h, lo, hi, mode='step'):
    for _ in range(30):
        p = [rng.randint(lo, hi)]
        for _ in range(h - 1):
            d = rng.choice((-1, 0, 0, 1)) if mode == 'step' else rng.choice((-3, -2, -1, 1, 2, 3))
            p.append(min(hi, max(lo, p[-1] + d)))
        if len(set(p)) > 1: return p
    return p


def mkcut(h, w, p, a, k, b=None):
    return [[a if c < p[r] else k if c == p[r] else (b if b else a) for c in range(w)] for r in range(h)]


def paste_margin(rng, H, Wd, sub):
    h, w = dims(sub)
    if h + 2 > H or w + 2 > Wd: return None
    g = blank(H, Wd); paste(g, sub, rng.randint(1, H - h - 1), rng.randint(1, Wd - w - 1)); return g


def scene(builder, hmin=5, wmin=6, rot=False):
    def gen(rng):
        H, Wd = D(rng, hmin + 2, 30), D(rng, wmin + 2, 30)
        h = rng.randint(hmin, min(H - 2, max(hmin, int(H * .75)))); w = rng.randint(wmin, min(Wd - 2, max(wmin, int(Wd * .75))))
        sub = builder(rng, h, w)
        return None if sub is None else paste_margin(rng, H, Wd, sub)
    return gen


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


# ============================================================ rules on one rectangle cut by a colour-2 line
def b_cut(mode, ex=(2,), b=False):
    def bd(rng, h, w):
        a = src(rng, ex + (0,)); bb = src(rng, ex + (a,)) if b else None
        return mkcut(h, w, prof(rng, h, 1, w - 2, mode), a, 2, bb)
    return bd


def tf_close(g):
    out = copy(g); W = len(g[0])
    for r, row in enumerate(g):
        if 2 in row:
            if row.count(2) != 1: return None
            c = row.index(2); i = c; j = c + 1
            while j < W and row[j] != 0: out[r][i] = row[j]; i += 1; j += 1
            out[r][i] = 0
    return out
rule("close_cut_by_shifting_right_face", "In every row of the colour-2 cut shape the cut cell is removed and the cells to its right in that row slide one step left to fill it, leaving one empty cell at the row's right end.",
     mk(scene(b_cut('jag')), tf_close), tf_close)


def tf_stepcut(g):
    out = copy(g)
    for r, row in enumerate(g):
        if 2 in row:
            c = row.index(2)
            if c + 1 >= len(row) or row[c + 1] == 0 or row.count(2) != 1: return None
            out[r][c] = row[c - 1] if c else row[c + 1]; out[r][c + 1] = 2
    return out
rule("cut_moves_one_step_right", "Every colour-2 cut cell moves one cell to the right in its row: the cut cell takes the face colour and the cell just right of it becomes colour 2.",
     mk(scene(b_cut('step')), tf_stepcut), tf_stepcut)


def tf_side(g):
    out = copy(g)
    for r, row in enumerate(g):
        if 2 in row:
            c = row.index(2)
            for i in range(len(row)):
                if row[i] != 0 and i != c: out[r][i] = 3 if i < c else 4
    return out
rule("halves_recoloured_by_side_of_cut", "In every row, the shape cells left of the colour-2 cut cell become colour 3 and the shape cells right of it become colour 4; the cut cells stay colour 2.",
     mk(scene(b_cut('jag', (2, 3, 4))), tf_side), tf_side)


def b_marker(rng, h, w):
    p = prof(rng, h, 1, w - 2, 'jag'); a = src(rng, (0, 2, 8)); s = mkcut(h, w, p, a, 2)
    r = rng.randrange(h); left = rng.random() < .5
    c = rng.randrange(p[r]) if left else rng.randint(p[r] + 1, w - 1)
    s[r][c] = 8; return s


def tf_marker(g):
    out = copy(g); mk_ = cells(g, lambda v: v == 8)
    if len(mk_) != 1: return None
    mr, mc = mk_[0]; cc = [(r, row.index(2)) for r, row in enumerate(g) if 2 in row]
    if not cc: return None
    cut = dict(cc)
    if mr not in cut: return None
    left = mc < cut[mr]
    for r, c in cc:
        for i in range(len(g[0])):
            if g[r][i] != 0 and ((i >= c) if left else (i <= c)) and g[r][i] != 8: out[r][i] = 0
    return out
rule("keep_face_holding_marker", "A colour-2 cut line divides a shape into a left and a right face, and one cell of colour 8 sits in one face: that face is kept (with its marker) and the other face and every cut cell are erased.",
     mk(scene(b_marker), tf_marker), tf_marker)


def b_pieces(cutcol, partial=True, nmax=3):
    def bd(rng, h, w):
        a = src(rng, (0, 2, 8)) if cutcol == 2 else 8
        s = [[a] * w for _ in range(h)]
        for _ in range(rng.randint(1, nmax)):
            if rng.random() < .5 and h >= 5:
                r = rng.randint(1, h - 2); l = w if rng.random() > .3 or not partial else rng.randint(2, w - 1)
                for c in range(l): s[r][c] = cutcol
            elif w >= 5:
                c = rng.randint(1, w - 2); l = h if rng.random() > .3 or not partial else rng.randint(2, h - 1)
                for r in range(l): s[r][c] = cutcol
        return s
    return bd


def pcs(g):
    cols = {v for r in g for v in r if v not in (0, 2)}
    if len(cols) != 1: return None
    return components(g, cols.pop(), conn8=False)


def tf_cntbar(g):
    c = pcs(g)
    if not c or len(c) < 2 or len(c) > 16: return None
    return [[g[c[0][0][0]][c[0][0][1]]] * len(c) + [0] * (16 - len(c))]
rule("pieces_made_by_cuts_count_bar", "The rectangle is divided by colour-2 cut lines (full or partial); the output is one row 16 cells wide holding, from the left, as many cells in the rectangle's colour as there are pieces (rest empty), where a piece is a group of edge-adjacent rectangle cells.",
     mk(scene(b_pieces(2)), tf_cntbar), tf_cntbar)


def tf_largest(g):
    c = pcs(g)
    if not c or len(c) < 2: return None
    s = sorted(c, key=len)
    if len(s[-1]) == len(s[-2]): return None
    out = blank(*dims(g))
    for r, cc in s[-1]: out[r][cc] = g[r][cc]
    return out
rule("keep_largest_piece_after_cuts", "The rectangle cut by colour-2 lines falls into pieces of edge-adjacent cells; only the piece with the most cells is kept and everything else, cut cells included, is erased (inputs never tie for largest).",
     mk(scene(b_pieces(2)), tf_largest), tf_largest)


def tf_smallest(g):
    c = pcs(g)
    if not c or len(c) < 2: return None
    s = sorted(c, key=len)
    if len(s[0]) == len(s[1]): return None
    out = copy(g)
    for r, cc in s[0]: out[r][cc] = 3
    return out
rule("smallest_piece_after_cuts_turns_three", "The rectangle cut by colour-2 lines falls into pieces of edge-adjacent cells; the piece with the fewest cells turns colour 3 and the rest is unchanged (inputs never tie for smallest).",
     mk(scene(b_pieces(2), 6, 6), tf_smallest), tf_smallest)


def ordered_pieces(g):
    c = components(g, 8, conn8=False)
    return sorted(c, key=lambda p: (min(x[1] for x in p), min(x[0] for x in p)))


def tf_num(g):
    c = ordered_pieces(g)
    if len(c) < 2 or len(c) > 6: return None
    out = copy(g)
    for i, p in enumerate(c):
        for r, cc in p: out[r][cc] = i + 1
    return out
rule("pieces_numbered_left_to_right", "The colour-8 rectangle is split by empty gap lines into pieces of edge-adjacent cells; the pieces are numbered from 1 in order of their leftmost column (a tie goes to the piece whose top cell is higher) and each piece is recoloured with its own number.",
     mk(scene(b_pieces(0, False, 3), 6, 7), tf_num), tf_num, digits=True)


def tf_rank(g):
    c = components(g, 8, conn8=False)
    if len(c) < 2 or len(c) > 6: return None
    s = sorted(c, key=lambda p: -len(p))
    if len({len(p) for p in s}) < len(s): return None
    out = copy(g)
    for i, p in enumerate(s):
        for r, cc in p: out[r][cc] = i + 1
    return out
rule("pieces_ranked_by_area_digits", "The colour-8 rectangle is split by empty gap lines into pieces of edge-adjacent cells; the largest piece becomes colour 1, the next largest colour 2, and so on down to the smallest (inputs never have two pieces of equal area).",
     mk(scene(b_pieces(0, False, 3), 6, 7), tf_rank), tf_rank, digits=True)


# ============================================================ two parallel cuts
def b_three(rng, h, w):
    d = rng.randint(3, 5)
    if w < d + 5: return None
    p = prof(rng, h, 1, w - 2 - d, 'step'); a = src(rng, (0, 2, 3, 4)); s = [[a] * w for _ in range(h)]
    for r in range(h): s[r][p[r]] = 2; s[r][p[r] + d] = 3
    return s


def tf_middle(g):
    cols = {v for r in g for v in r if v not in (0, 2, 3)}
    if len(cols) != 1: return None
    c = sorted(components(g, cols.pop(), conn8=False), key=lambda p: sum(x[1] for x in p) / len(p))
    if len(c) != 3: return None
    r0, c0, r1, c1 = bbox(c[1]); out = blank(r1 - r0 + 1, c1 - c0 + 1)
    for r, cc in c[1]: out[r - r0][cc - c0] = g[r][cc]
    return out
rule("middle_piece_between_two_cuts", "A shape is cut into three pieces by a colour-2 line and a colour-3 line running side by side; the output is the middle piece alone, cropped to its bounding box with empty cells elsewhere.",
     mk(scene(b_three, 6, 9), tf_middle), tf_middle)


def tf_band(g):
    out = copy(g)
    for r, row in enumerate(g):
        if 2 in row and 3 in row:
            a, b = row.index(2), row.index(3)
            for i in range(a + 1, b): out[r][i] = 4
    return out
rule("band_between_two_cuts_recoloured", "In each row, the cells strictly between the colour-2 cut cell and the colour-3 cut cell become colour 4; everything else stays.",
     mk(scene(b_three, 6, 9), tf_band), tf_band)


# ============================================================ gap cuts and exposed faces
def b_gap(rng, h, w):
    p = prof(rng, h, 1, w - 2, 'jag'); a = src(rng, (0, 4)); return mkcut(h, w, p, a, 0)


def tf_gapfill(g):
    out = copy(g); H, W = dims(g); n = 0
    for r in range(H):
        for c in range(1, W - 1):
            if g[r][c] == 0 and g[r][c - 1] != 0 and g[r][c + 1] != 0: out[r][c] = 4; n += 1
    return out if n else None
rule("gap_cut_filled_with_four", "The shape is cut by an empty jagged line, one empty cell in each row; every empty cell that has a shape cell directly left and a shape cell directly right of it becomes colour 4.",
     mk(scene(b_gap), tf_gapfill), tf_gapfill)


def b_two(rng, h, w):
    p = prof(rng, h, 1, w - 1, 'jag'); a, b = rng.sample([c for c in range(1, 10) if c not in (6, 7)], 2)
    return [[a if c < p[r] else b for c in range(w)] for r in range(h)]


def rot_random(builder):
    def bd(rng, h, w):
        s = builder(rng, h, w)
        if s is None: return None
        for _ in range(rng.randrange(4)): s = rot90(s)
        return s
    return bd


def tf_exposed(g):
    out = copy(g); H, W = dims(g); cs = sorted({v for r in g for v in r if v not in (0,)})
    if len(cs) != 2: return None
    for r in range(H):
        for c in range(W):
            v = g[r][c]
            if v == 0: continue
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                y, x = r + dr, c + dc
                if 0 <= y < H and 0 <= x < W and g[y][x] not in (0, v):
                    out[r][c] = 6 if v == min(cs) else 7; break
    return out
rule("exposed_faces_along_the_cut_marked", "A rectangle is made of two faces of different colours meeting along a jagged line; every cell with an edge-adjacent cell of the other face (the cells that would be exposed if the faces were pulled apart) becomes colour 6 if it belongs to the face of smaller colour value and colour 7 if it belongs to the other face.",
     mk(scene(rot_random(b_two)), tf_exposed), tf_exposed, digits=True)


def tf_apart(g):
    H, W = dims(g); cs = sorted({v for r in g for v in r if v})
    if len(cs) != 2: return None
    out = blank(H, W)
    for r in range(H):
        for c in range(W):
            if g[r][c] == 0: continue
            if g[r][c] == cs[0]: out[r][c] = g[r][c]
            elif c + 1 < W: out[r][c + 1] = g[r][c]
            else: return None
    return out
rule("halves_pulled_apart_one_cell", "A rectangle is two faces of different colours; the face with the larger colour value moves one cell to the right, opening a one-cell empty gap along the cut, while the other face stays.",
     mk(scene(b_two), tf_apart, lambda g, o: True), tf_apart, digits=True)


# ============================================================ straighten, profile key, steps
def tf_straight(g):
    out = copy(g); cut = {r: row.index(2) for r, row in enumerate(g) if 2 in row}
    if not cut: return None
    r0 = min(cut); p0 = cut[r0]
    for r, c in cut.items():
        out[r][c] = g[r][c - 1]; 
    for r in cut: out[r][p0] = 2
    return out
rule("straighten_jagged_cut_to_top_row", "The jagged colour-2 cut is replaced by a straight vertical cut in the column where the cut is in the shape's top row: every old cut cell takes the face colour and the cell in that column in each row becomes colour 2.",
     mk(scene(b_cut('jag')), tf_straight), tf_straight)


def tf_steps(g):
    cut = [row.index(2) for row in g if 2 in row]
    n = sum(1 for i in range(1, len(cut)) if cut[i] != cut[i - 1])
    if not cut or n == 0 or n > 30: return None
    return [[2] * n + [0] * (len(cut) - n)]
rule("cut_step_count_bar", "The output is one row as wide as the cut shape is tall, holding from the left one colour-2 cell per step in the colour-2 cut (rest empty): count the rows (going down) where the cut sits in a different column from the row above it.",
     mk(scene(b_cut('step', (2,)), 7, 6), tf_steps), tf_steps)


def key_gen(rng):
    h = rng.randint(5, 12); H, Wd = D(rng, h + 2, 30), D(rng, 15, 30)
    w = rng.randint(7, Wd - 8)
    if w + 7 > Wd: return None
    dk = prof(rng, h, 1, 4, 'step'); a = src(rng, (0, 2, 5)); xa = rng.randint(0, Wd - w - 7); r0 = rng.randint(0, H - h)
    g = blank(H, Wd)
    for r in range(h):
        g[r0 + r][xa] = 5; g[r0 + r][xa + dk[r]] = 2
        for c in range(w): g[r0 + r][xa + 6 + c] = a
    return g


def tf_key(g):
    out = copy(g); an = cells(g, lambda v: v == 5)
    if not an: return None
    xa = an[0][1]; a = [v for row in g for v in row if v not in (0, 2, 5)][0]
    for r, c in an: out[r][c] = 0
    for r, row in enumerate(g):
        if 2 in row:
            dk = row.index(2) - xa; out[r][row.index(2)] = 0
            x0 = xa + 6; out[r][x0 + dk] = 2
    return out
rule("cut_profile_key_applied_to_rectangle", "A grey (5) anchor bar stands left of a colour-2 profile line; the rectangle to its right has the same height: the output erases the key and cuts the rectangle with the same profile, so in each row the rectangle cell whose offset from the rectangle's left edge equals the key cell's offset from the anchor bar becomes colour 2 (the rectangle's left edge is 6 columns right of the anchor).",
     mk(key_gen, tf_key), tf_key)


# ============================================================ reflect a face across a cut
def diag_gen(rng):
    n = rng.randint(4, 14); H, Wd = D(rng, n + 2, 30), D(rng, n + 2, 30); a = src(rng, (0, 2)); g = blank(n, n)
    for r in range(n):
        g[r][r] = 2
        for c in range(r):
            if rng.random() < .6: g[r][c] = a
    return paste_margin(rng, H, Wd, g)


def tf_diag(g):
    cut = cells(g, lambda v: v == 2)
    if len(cut) < 4: return None
    r0, c0, r1, c1 = bbox(cut); out = copy(g)
    for i in range(r1 - r0 + 1):
        for j in range(i):
            if g[r0 + i][c0 + j] != 0: out[r0 + j][c0 + i] = g[r0 + i][c0 + j]
    return out
rule("reflect_face_across_diagonal_cut", "A square holds a colour-2 cut along its main diagonal (top-left to bottom-right) and a pattern of cells below-left of it; the pattern is mirrored across the diagonal cut into the empty upper-right part of the square.",
     mk(diag_gen, tf_diag), tf_diag)


def straight_gen(rng):
    k = rng.randint(2, 10); h = rng.randint(4, 20); H, Wd = D(rng, h + 2, 30), D(rng, 2 * k + 3, 30)
    a, b = rng.sample([c for c in range(1, 10) if c != 2], 2); g = blank(h, 2 * k + 1)
    for r in range(h):
        g[r][k] = 2
        for c in range(k):
            if rng.random() < .6: g[r][c] = rng.choice((a, b))
    if not any(g[r][0] for r in range(h)): return None
    return paste_margin(rng, H, Wd, g)


def tf_mirrcut(g):
    cut = cells(g, lambda v: v == 2)
    if not cut: return None
    c = cut[0][1]; nz = cells(g, lambda v: v != 0); k = c - min(x[1] for x in nz); out = copy(g)
    for r in range(len(g)):
        for j in range(1, k + 1): out[r][c + j] = g[r][c - j]
    return out
rule("mirror_face_across_straight_cut", "A vertical colour-2 cut line has a pattern of coloured cells on its left and nothing on its right; the pattern is mirrored across the cut line into the right side (the pattern's width, measured from the cut to the leftmost non-empty cell, is mirrored).",
     mk(straight_gen, tf_mirrcut), tf_mirrcut)


# ============================================================ bounding-box complements
def blob_sub(rng, lo=5, hi=16):
    n = rng.randint(lo, hi); s = random_shape(rng, n, conn8=rng.random() < .5)
    h = max(r for r, _ in s) + 1; w = max(c for _, c in s) + 1
    if h < 2 or w < 2 or len(s) == h * w: return None
    a = src(rng, (0, 2)); g = blank(h, w)
    for r, c in s: g[r][c] = a
    return g


def blobs_gen(kmax):
    def gen(rng):
        H, Wd = D(rng, 8, 30), D(rng, 8, 30); subs = []
        for _ in range(rng.randint(1, kmax)):
            b = blob_sub(rng)
            if b is None: return None
            subs.append(b)
        return scatter_subs(rng, H, Wd, subs)
    return gen


def tf_bboxfill(g):
    out = copy(g); objs = objects(g, 0, conn8=True)
    for cm in objs:
        r0, c0, r1, c1 = bbox(cm)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if g[r][c] == 0: out[r][c] = 2
    return out
rule("bounding_box_complement_filled_two", "Every object (cells touching by edge or corner) sits in its bounding box; the empty cells inside each bounding box become colour 2 and the object stays.",
     mk(blobs_gen(4), tf_bboxfill, lambda g, o: len(objects(g, 0, True)) == len({0}) or True), tf_bboxfill)


def tf_bboxneg(g):
    out = copy(g)
    for cm in objects(g, 0, conn8=True):
        r0, c0, r1, c1 = bbox(cm); a = g[cm[0][0]][cm[0][1]]
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1): out[r][c] = a if g[r][c] == 0 else 0
    return out
rule("bounding_box_negative_in_place", "Every object (cells touching by edge or corner) is replaced, inside its own bounding box, by its complement: the empty cells of the box take the object's colour and the object's cells become empty.",
     mk(blobs_gen(4), tf_bboxneg), tf_bboxneg)


def tf_compcrop(g):
    cm = objects(g, 0, conn8=True)
    if len(cm) != 1: return None
    r0, c0, r1, c1 = bbox(cm[0]); a = g[cm[0][0][0]][cm[0][0][1]]
    return [[a if g[r][c] == 0 else 0 for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
rule("complement_in_bounding_box_output", "The output is the single object's bounding box cut out of the grid, with the object's cells made empty and the box's empty cells filled with the object's colour.",
     mk(blobs_gen(1), tf_compcrop), tf_compcrop)


def tf_compcnt(g):
    cm = objects(g, 0, conn8=True)
    if len(cm) != 1: return None
    r0, c0, r1, c1 = bbox(cm[0]); n = (r1 - r0 + 1) * (c1 - c0 + 1) - len(cm[0])
    return [[g[cm[0][0][0]][cm[0][0][1]]] * n + [0] * ((r1 - r0 + 1) * (c1 - c0 + 1) - n)] if 0 < n else None
rule("complement_cell_count_bar", "The output is one row as wide as the object's bounding box has cells, holding from the left as many cells in the object's colour as there are empty cells inside that box (rest empty); the count is the number of empty cells inside the object's bounding box (the object's cells not counted).",
     mk(blobs_gen(1), tf_compcnt), tf_compcnt)


def frame_gen(rng):
    H, Wd = D(rng, 8, 30), D(rng, 9, 30); h = rng.randint(3, H - 2); w = rng.randint(4, Wd - 2)
    p = prof(rng, h, 1, w - 1, 'jag'); a = src(rng, (0, 3, 5)); g = blank(h + 2, w + 2, 5)
    for r in range(h):
        for c in range(w): g[r + 1][c + 1] = a if c < p[r] else 0
    return paste_margin(rng, H, Wd, g) if h + 4 <= H and w + 4 <= Wd else None


def frame_in(g):
    f = cells(g, lambda v: v == 5)
    if not f: return None
    r0, c0, r1, c1 = bbox(f); return r0 + 1, c0 + 1, r1 - 1, c1 - 1


def tf_framefill(g):
    b = frame_in(g)
    if not b: return None
    out = copy(g)
    for r in range(b[0], b[2] + 1):
        for c in range(b[1], b[3] + 1):
            if g[r][c] == 0: out[r][c] = 3
    return out
rule("missing_half_filled_inside_frame", "A grey (5) rectangular frame holds one face of a cut rectangle against its left wall; the rest of the frame's inside, the missing face, is filled with colour 3.",
     mk(frame_gen, tf_framefill), tf_framefill)


def tf_framecrop(g):
    b = frame_in(g)
    if not b: return None
    a = [v for row in g for v in row if v not in (0, 5)][0]
    return [[a if g[r][c] == 0 else 0 for c in range(b[1], b[3] + 1)] for r in range(b[0], b[2] + 1)]
rule("missing_half_output_from_frame", "A grey (5) rectangular frame holds one face of a cut rectangle; the output is the frame's inside with the shown face erased and the missing face drawn in the shown face's colour.",
     mk(frame_gen, tf_framecrop), tf_framecrop)


# ============================================================ loose halves: matching and reassembly
def norm(S):
    r0 = min(r for r, _ in S); c0 = min(c for _, c in S); return frozenset((r - r0, c - c0) for r, c in S)


def flipH(S): return norm({(r, -c) for r, c in S})
def rot_a(S): return norm({(c, -r) for r, c in S})
def rot_b(S): return rot_a(rot_a(S))
def rot_c(S): return rot_a(rot_b(S))
TT = [lambda S: S]; MM = [flipH]; RR = [rot_a, rot_b, rot_c]


def placements(A, B):
    """offsets (dr, dc) at which B tiles a full rectangle with A"""
    hA = max(r for r, _ in A) + 1; wA = max(c for _, c in A) + 1
    hB = max(r for r, _ in B) + 1; wB = max(c for _, c in B) + 1; out = []
    for dr in range(-hB, hA + 1):
        for dc in range(-wB, wA + 1):
            Bs = {(r + dr, c + dc) for r, c in B}
            if Bs & A: continue
            U = A | Bs; r0 = min(r for r, _ in U); r1 = max(r for r, _ in U); c0 = min(c for _, c in U); c1 = max(c for _, c in U)
            if len(U) == (r1 - r0 + 1) * (c1 - c0 + 1): out.append((dr, dc))
    return out


def partner(A, B, tfs):
    return any(placements(A, norm(t(B))) for t in tfs) or any(placements(B, norm(t(A))) for t in tfs)


def half_pair(rng):
    h = rng.randint(3, 6); w = rng.randint(4, 7); p = prof(rng, h, 1, w - 1, 'jag' if rng.random() < .5 else 'step')
    L = {(r, c) for r in range(h) for c in range(p[r])}; R = {(r, c) for r in range(h) for c in range(p[r], w)}
    return norm(L), norm(R)


def piece_sub(S, col=8):
    g = blank(max(r for r, _ in S) + 1, max(c for _, c in S) + 1)
    for r, c in S: g[r][c] = col
    return g


def match_gen(mode, orphans=0):
    def gen(rng):
        H, Wd = D(rng, 12, 30), D(rng, 12, 30); subs = []; k = rng.randint(2, 4)
        for i in range(k):
            L, R = half_pair(rng)
            if mode == 'M': R = flipH(R)
            if mode == 'R':
                for _ in range(rng.randint(1, 3)): R = rot_a(R)
            subs += [piece_sub(L), piece_sub(R)]
        for _ in range(orphans): subs.append(piece_sub(half_pair(rng)[0]))
        rng.shuffle(subs); return scatter_subs(rng, H, Wd, subs)
    return gen


def pairs_of(g, tfs, orph=False):
    comps = components(g, 8, conn8=False)
    sets = [norm(c) for c in comps]; pr = []; used = {}
    for i in range(len(comps)):
        for j in range(i + 1, len(comps)):
            if partner(sets[i], sets[j], tfs): pr.append((i, j)); used[i] = used.get(i, 0) + 1; used[j] = used.get(j, 0) + 1
    if any(v != 1 for v in used.values()): return None
    if not orph and len(used) != len(comps): return None
    return comps, pr, used


def tf_match(tfs):
    def tf(g):
        res = pairs_of(g, tfs)
        if not res or len(res[1]) < 2: return None
        comps, pr, _ = res; out = copy(g)
        pr = sorted(pr, key=lambda p: min(min(comps[p[0]]), min(comps[p[1]])))
        for n, (i, j) in enumerate(pr):
            for r, c in comps[i] + comps[j]: out[r][c] = n + 1
        return out
    return tf
mt, mm, mr = tf_match(TT), tf_match(MM), tf_match(RR)
rule("match_loose_halves_by_translation", "Several colour-8 pieces lie on the grid and each has exactly one partner that, slid (not turned or flipped) against it, forms a solid rectangle with it; each pair is recoloured with its pair number, pairs numbered 1, 2, ... by the reading-order position (top row first, then left) of their earliest cell.",
     mk(match_gen('T'), mt), mt, digits=True)
rule("match_loose_halves_after_flip", "Several colour-8 pieces lie on the grid and each has exactly one partner that, after a left-right flip of one piece and then sliding, forms a solid rectangle with it; each pair is recoloured with its pair number, pairs numbered 1, 2, ... by the reading-order position (top row first, then left) of their earliest cell.",
     mk(match_gen('M'), mm), mm, digits=True)
rule("match_loose_halves_after_turn", "Several colour-8 pieces lie on the grid and each has exactly one partner that, after a quarter, half or three-quarter turn of one piece and then sliding, forms a solid rectangle with it; each pair is recoloured with its pair number, pairs numbered 1, 2, ... by the reading-order position (top row first, then left) of their earliest cell.",
     mk(match_gen('R'), mr), mr, digits=True)


def tf_orphan(g):
    res = pairs_of(g, TT, True)
    if not res: return None
    comps, pr, used = res; out = copy(g)
    if len(used) == len(comps) or not pr: return None
    for i, c in enumerate(comps):
        if i not in used:
            for r, cc in c: out[r][cc] = 0
    return out
rule("unpaired_halves_erased", "Colour-8 pieces lie on the grid; those that have a partner which, slid (not turned or flipped) against them, forms a solid rectangle stay, and every piece with no such partner is erased.",
     mk(match_gen('T', 2), tf_orphan), tf_orphan)


def asm_gen(mode):
    def gen(rng):
        H, Wd = D(rng, 10, 30), D(rng, 10, 30); L, R = half_pair(rng)
        if mode == 'M': R = flipH(R)
        if mode == 'R':
            for _ in range(rng.randint(1, 3)): R = rot_a(R)
        a, b = rng.sample(range(1, 10), 2); subs = [piece_sub(L, a), piece_sub(R, b)]; rng.shuffle(subs)
        return scatter_subs(rng, H, Wd, subs)
    return gen


def tf_asm(tfs):
    def tf(g):
        cs = sorted({v for r in g for v in r if v}); 
        if len(cs) != 2: return None
        comps = sorted([components(g, v, conn8=False) for v in cs], key=lambda x: 0)
        pcs_ = [cm[0] for cm in comps]
        if any(len(cm) != 1 for cm in comps): return None
        pcs_.sort(key=min); A, B = pcs_; ca, cb = g[A[0][0]][A[0][1]], g[B[0][0]][B[0][1]]
        An = norm(A); res = set()
        for t in tfs:
            Bn = norm(t(B))
            for dr, dc in placements(An, Bn):
                U = {(r, c): ca for r, c in An}; U.update({(r + dr, c + dc): cb for r, c in Bn})
                r0 = min(r for r, _ in U); c0 = min(c for _, c in U); r1 = max(r for r, _ in U); c1 = max(c for _, c in U)
                res.add(tuple(tuple(U[(r, c)] for c in range(c0, c1 + 1)) for r in range(r0, r1 + 1)))
        if len(res) != 1: return None
        return [list(r) for r in res.pop()]
    return tf
for nm, md, tfs, txt in (("reassemble_two_halves_slid_together", 'T', TT, "slid (not turned or flipped)"),
                         ("reassemble_two_halves_one_flipped", 'M', MM, "flipped left-right and then slid"),
                         ("reassemble_two_halves_one_turned", 'R', RR, "turned by a quarter, half or three-quarter turn and then slid")):
    f = tf_asm(tfs)
    rule(nm, "Two pieces of different colours lie on the grid; the output is the solid rectangle they form when the piece whose earliest cell comes first in reading order (top row, then left) stays as drawn and the other piece is " + txt + " against it, each piece keeping its colour.",
         mk(asm_gen(md), f), f)


def socket_gen(rng):
    H, Wd = D(rng, 12, 30), D(rng, 12, 30); L, R = half_pair(rng); subs = [piece_sub(L, 2), piece_sub(R)]
    for _ in range(rng.randint(2, 4)):
        L2, R2 = half_pair(rng); subs.append(piece_sub(R2))
    rng.shuffle(subs); return scatter_subs(rng, H, Wd, subs)


def tf_socket(g):
    s = components(g, 2, conn8=False)
    if len(s) != 1: return None
    S = norm(s[0]); ps = components(g, 8, conn8=False); hit = [p for p in ps if placements(S, norm(p))]
    if len(hit) != 1: return None
    out = copy(g)
    for r, c in hit[0]: out[r][c] = 3
    return out
rule("piece_fitting_the_socket_recoloured", "One colour-2 piece is the socket and several colour-8 pieces are candidates; the single candidate that, slid (not turned or flipped) against the socket, forms a solid rectangle with it turns colour 3 and the other candidates stay (inputs have exactly one fitting candidate).",
     mk(socket_gen, tf_socket), tf_socket)


# ============================================================ jigsaw tab and slot
def jig_gen(rng):
    k = rng.randint(1, 3); H = D(rng, 7 * k + 1, 30); Wd = D(rng, 14, 30); cs = rng.sample([1, 2, 3, 4, 6, 7, 8, 9], 2 * k)
    g = blank(H, Wd); off = rng.randint(0, H - 7 * k)
    for b in range(k):
        hb = rng.randint(4, 6); wA = rng.randint(3, 5); wB = rng.randint(3, 5); th = rng.randint(1, 2); t = rng.randint(1, hb - th - 1)
        gap = rng.randint(1, max(1, Wd - (wA + 1 + wB) - 2)); xa = rng.randint(0, max(0, Wd - (wA + 1 + wB + gap)))
        xb = xa + wA + 1 + gap
        if xb + wB > Wd: return None
        r0 = off + b * 7
        for r in range(hb):
            for c in range(wA): g[r0 + r][xa + c] = cs[2 * b]
            for c in range(wB):
                if not (t <= r < t + th and c == 0): g[r0 + r][xb + c] = cs[2 * b + 1]
        for r in range(t, t + th): g[r0 + r][xa + wA] = cs[2 * b]
    return g


def tf_jig(g):
    out = copy(g); H, W = dims(g); cols = sorted({v for r in g for v in r if v})
    comps = [components(g, v, conn8=False) for v in cols]
    if any(len(c) != 1 for c in comps): return None
    comps = [c[0] for c in comps]; done = set()
    for i, A in enumerate(comps):
        for j, B in enumerate(comps):
            if i != j and i not in done and j not in done and bbox(A)[0] == bbox(B)[0] and bbox(A)[2] == bbox(B)[2] and bbox(A)[1] < bbox(B)[1]:
                a = set(A); col = g[B[0][0]][B[0][1]]; s = 0
                while all(c - s - 1 >= 0 and (r, c - s - 1) not in a for r, c in B): s += 1
                for r, c in B: out[r][c] = 0
                for r, c in B: out[r][c - s] = col
                done |= {i, j}
    return out if len(done) == len(comps) else None
rule("jigsaw_tab_into_slot_joined", "In each row band a left piece has a tab sticking out of its right side and a right piece of another colour has a matching slot in its left side; the right piece slides left, as far as it can without overlapping the left piece, until the tab sits in the slot.",
     mk(jig_gen, tf_jig), tf_jig)


def slide_gen(rng):
    h = rng.randint(4, 14); w = rng.randint(7, 20); H, Wd = D(rng, h + 2, 30), D(rng, w + 2, 30)
    if h + 2 > H or w + 2 > Wd: return None
    d = rng.randint(2, 4)
    if w < d + 4: return None
    p = prof(rng, h, 1, w - 2 - d, 'jag'); a, b = rng.sample(range(1, 10), 2); g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if c < p[r]: g[r][c] = a
            elif c >= p[r] + d: g[r][c] = b
    return paste_margin(rng, H, Wd, g)


def tf_slide(g):
    H, W = dims(g); cols = sorted({v for r in g for v in r if v})
    if len(cols) != 2: return None
    A = cells(g, lambda v: v == cols[0]); Bs = set(cells(g, lambda v: v == cols[1])); a, b = cols
    if bbox(A)[1] > bbox(list(Bs))[1]: A, Bs, a, b = list(Bs), set(A), b, a
    s = 0
    while all(c + s + 1 < W and (r, c + s + 1) not in Bs for r, c in A): s += 1
    out = blank(H, W)
    for r, c in Bs: out[r][c] = b
    for r, c in A: out[r][c + s] = a
    return out
rule("faces_slide_together_until_touching", "A rectangle is split into a left face and a right face of different colours separated by an empty jagged channel of constant width; the left face slides right as far as it can without overlapping the right face, so the two faces touch along the cut.",
     mk(slide_gen, tf_slide), tf_slide)
