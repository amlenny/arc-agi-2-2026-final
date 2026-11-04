# b023_orientation.py -- shape orientation and heading: oriented glyphs (arrows, spears, hooks, chevrons,
# wedges), staples (U shapes), tees and L hooks each have a heading; rules read the heading and act on it.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

HEAD = ["N", "E", "S", "W"]
DIR = {"N": (-1, 0), "E": (0, 1), "S": (1, 0), "W": (0, -1)}
OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}
CW = {"N": "E", "E": "S", "S": "W", "W": "N"}
# canonical glyphs point north; the FIRST cell is the tip (front cell)
GLYPHS = {
    "arrow": [(0, 1), (1, 0), (1, 1), (1, 2), (2, 1), (3, 1)],
    "spear": [(0, 1), (1, 1), (2, 0), (2, 1), (2, 2)],
    "hook": [(0, 0), (1, 0), (2, 0), (2, 1)],
    "chevron": [(0, 2), (1, 1), (1, 3), (2, 0), (2, 4)],
    "wedge": [(0, 2), (1, 1), (1, 2), (1, 3), (2, 0), (2, 1), (2, 2), (2, 3), (2, 4)],
}


def _rotcw(cells_):
    h = max(r for r, _ in cells_) + 1
    return [(c, h - 1 - r) for r, c in cells_]


def _norm(cells_):
    r0 = min(r for r, _ in cells_); c0 = min(c for _, c in cells_)
    return [(r - r0, c - c0) for r, c in cells_]


POSE, LOOK = {}, {}
for _n, _sh in GLYPHS.items():
    _cur = _sh
    for _hd in HEAD:
        _p = _norm(_cur); POSE[(_n, _hd)] = _p; LOOK[tuple(sorted(_p))] = (_n, _hd, _p[0])
        _cur = _rotcw(_cur)
assert len(LOOK) == 20


def _ident(o):
    """(family, heading, tip (r,c), (r0,c0)) for a glyph component, else None."""
    r0 = min(r for r, _ in o); c0 = min(c for _, c in o)
    k = LOOK.get(tuple(sorted((r - r0, c - c0) for r, c in o)))
    if k is None: return None
    n, hd, (tr, tc) = k
    return n, hd, (r0 + tr, c0 + tc), (r0, c0)


def _glyphs(g, strict=True):
    """[(cells, colour, family, heading, tip, origin)] over all non-grey objects; None if a non-glyph is seen."""
    out = []
    for o in objects(g, 0):
        col = g[o[0][0]][o[0][1]]
        if col == 5: continue
        k = _ident(o)
        if k is None:
            if strict: return None
            continue
        out.append((o, col) + k)
    return out


def _gsize(rng, lo=8, hi=20):
    if rng.random() < 0.35: return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _stamp(rng, g, shape, col, margin=1, tries=120):
    """Stamp one shape where its margin footprint is empty in the CURRENT grid. Returns (r0,c0) or None."""
    H, W = dims(g); h = max(r for r, _ in shape) + 1; w = max(c for _, c in shape) + 1
    if h > H or w > W: return None
    for _ in range(tries):
        r0, c0 = rng.randint(0, H - h), rng.randint(0, W - w)
        if all(g[r0 + r + dr][c0 + c + dc] == 0 for r, c in shape for dr in range(-margin, margin + 1)
               for dc in range(-margin, margin + 1) if 0 <= r0 + r + dr < H and 0 <= c0 + c + dc < W):
            for r, c in shape: g[r0 + r][c0 + c] = col
            return r0, c0
    return None


def _scene(rng, k_lo=2, k_hi=5, fams=None, heads=None, margin=1, lo=8, cols=None):
    h, w = _gsize(rng, lo); g = blank(h, w); k = rng.randint(k_lo, k_hi)
    fams = fams or list(GLYPHS); heads = heads or HEAD
    picks = [(rng.choice(fams), rng.choice(heads)) for _ in range(k)]
    cs = cols or [rng.choice([c for c in COLOURS if c != 5]) for _ in range(k)]
    if place_shapes(rng, g, [POSE[p] for p in picks], cs, margin=margin) is None: return None
    return g


def _ray_cells(g, r, c, hd):
    """Cells from (r,c) exclusive stepping in hd until the edge, stopping before a non-empty cell; (cells, hit)."""
    H, W = dims(g); dr, dc = DIR[hd]; path = []
    r += dr; c += dc
    while 0 <= r < H and 0 <= c < W:
        if g[r][c] != 0: return path, (r, c)
        path.append((r, c)); r += dr; c += dc
    return path, None


def _redraw(g, moves):
    """moves: [(old cells, new cells, colour)]. Erase all old, draw new; None on collision or out of bounds."""
    out = copy(g); H, W = dims(g)
    for old, _, _ in moves:
        for r, c in old: out[r][c] = 0
    for _, new, col in moves:
        for r, c in new:
            if not (0 <= r < H and 0 <= c < W) or out[r][c] != 0: return None
            out[r][c] = col
    return out


def _repose(fam, hd, origin):
    r0, c0 = origin
    return [(r0 + r, c0 + c) for r, c in POSE[(fam, hd)]]


# ---------------------------------------------------------------- recolour / mark by heading
def tf_heading_colour(g):
    gl = _glyphs(g); out = copy(g)
    if not gl: return None
    for o, col, fam, hd, tip, org in gl:
        for r, c in o: out[r][c] = HEAD.index(hd) + 1
    return out
rule("glyphs_recoloured_by_heading", "Every pointed shape is repainted by the way it points: 1 up, 2 right, 3 down, 4 left.",
     lambda rng: _scene(rng, 2, 6, cols=[rng.choice([6, 7, 8, 9])] * 6), tf_heading_colour, digits=True)


def tf_tip_grey(g):
    gl = _glyphs(g); out = copy(g)
    if not gl: return None
    for o, col, fam, hd, (r, c), org in gl: out[r][c] = 5
    return out
rule("glyph_tip_turns_grey", "The front cell (the tip) of every pointed shape turns grey (5); the rest of the shape keeps its colour.",
     lambda rng: _scene(rng, 2, 6), tf_tip_grey)


def tf_dot_ahead(g):
    gl = _glyphs(g); out = copy(g); H, W = dims(g)
    if not gl: return None
    for o, col, fam, hd, (r, c), org in gl:
        dr, dc = DIR[hd]; rr, cc = r + 2 * dr, c + 2 * dc
        if not (0 <= rr < H and 0 <= cc < W) or out[rr][cc] != 0 or out[r + dr][c + dc] != 0: return None
        out[rr][cc] = 5
    return out
rule("grey_dot_two_ahead_of_glyph", "A grey (5) dot is placed two cells in front of the tip of every pointed shape, in the direction it points.",
     lambda rng: _scene(rng, 2, 6, margin=2), tf_dot_ahead)


def tf_wall_mark(g):
    gl = _glyphs(g); out = copy(g); H, W = dims(g)
    if not gl: return None
    for o, col, fam, hd, tip, org in gl:
        path, hit = _ray_cells(g, tip[0], tip[1], hd)
        if hit is None and path: r, c = path[-1]; out[r][c] = col
    return out
rule("glyph_marks_border_cell_ahead", "Each pointed shape with a clear view ahead paints the border cell it points at in its own colour; nothing is drawn in between.",
     lambda rng: _scene(rng, 2, 6), tf_wall_mark)


# ---------------------------------------------------------------- rotate / reorient in place
def _reorient_all(g, target):
    gl = _glyphs(g)
    if not gl: return None
    moves = []
    for o, col, fam, hd, tip, org in gl:
        t = target(gl, (o, col, fam, hd, tip, org))
        if t is None: return None
        moves.append((o, _repose(fam, t, org), col))
    return _redraw(g, moves)


rule("glyphs_rotate_to_point_up", "Every pointed shape is turned in place, about the top-left corner of its box, so that it points up.",
     lambda rng: _scene(rng, 2, 6, margin=2), lambda g: _reorient_all(g, lambda gl, x: "N"))


def _largest_head(gl, x):
    sz = sorted(len(o) for o, *_ in gl)
    if len(sz) > 1 and sz[-1] == sz[-2]: return None
    return max(gl, key=lambda t: len(t[0]))[3]
rule("glyphs_align_to_largest_heading", "Every pointed shape is turned in place to point the same way as the shape with the most cells.",
     lambda rng: _scene(rng, 3, 6, margin=2), lambda g: _reorient_all(g, _largest_head))


def _majority_head(gl, x):
    cnt = {}
    for t in gl: cnt[t[3]] = cnt.get(t[3], 0) + 1
    top = sorted(cnt.values())
    if len(top) > 1 and top[-1] == top[-2]: return None
    return max(cnt, key=cnt.get)
rule("glyphs_align_to_majority_heading", "Every pointed shape is turned in place to point the way most of the shapes already point.",
     lambda rng: _scene(rng, 3, 7, margin=2), lambda g: _reorient_all(g, _majority_head))


def gi_odd_head(rng):
    hd = rng.choice(HEAD); odd = rng.choice([h for h in HEAD if h != hd]); k = rng.randint(3, 6)
    h, w = _gsize(rng, 9); g = blank(h, w)
    picks = [(rng.choice(list(GLYPHS)), hd) for _ in range(k - 1)] + [(rng.choice(list(GLYPHS)), odd)]
    cs = [rng.choice([c for c in COLOURS if c != 5]) for _ in picks]
    return g if place_shapes(rng, g, [POSE[p] for p in picks], cs, margin=2) else None
def _odd_target(gl, x):
    cnt = {}
    for t in gl: cnt[t[3]] = cnt.get(t[3], 0) + 1
    if len(cnt) != 2 or min(cnt.values()) != 1: return None
    return max(cnt, key=cnt.get)
rule("odd_heading_glyph_turned_to_match", "All pointed shapes face one way except one; that odd shape is turned in place to face the same way as the others.",
     gi_odd_head, lambda g: _reorient_all(g, _odd_target))


def tf_face_wall(g):
    gl = _glyphs(g); H, W = dims(g)
    if not gl: return None
    moves = []
    for o, col, fam, hd, tip, org in gl:
        r0, c0, r1, c1 = bbox(o)
        d = {"N": r0, "S": H - 1 - r1, "W": c0, "E": W - 1 - c1}
        best = sorted(d.values())
        if best[0] == best[1]: return None
        moves.append((o, _repose(fam, min(d, key=d.get), org), col))
    return _redraw(g, moves)
rule("glyphs_face_nearest_wall", "Every pointed shape is turned in place to point at the grid edge nearest to it.",
     lambda rng: _scene(rng, 2, 5, margin=2), tf_face_wall)


def tf_colour_heading(g):
    gl = _glyphs(g)
    if not gl: return None
    return _redraw(g, [(o, _repose(fam, HEAD[col - 1], org), col) for o, col, fam, hd, tip, org in gl])
rule("colour_dictates_glyph_heading", "Each pointed shape is turned in place to the heading its colour names: 1 up, 2 right, 3 down, 4 left.",
     lambda rng: _scene(rng, 2, 6, margin=2, cols=[rng.randint(1, 4) for _ in range(6)]), tf_colour_heading, digits=True)


def tf_pivot_tip(g):
    gl = _glyphs(g)
    if not gl: return None
    moves = []
    for o, col, fam, hd, (tr, tc), org in gl:
        p = POSE[(fam, CW[hd])]; pr, pc = p[0]
        moves.append((o, [(tr + r - pr, tc + c - pc) for r, c in p], col))
    return _redraw(g, moves)
rule("glyphs_pivot_clockwise_about_tip", "Every pointed shape swings a quarter turn clockwise about its tip; the tip cell stays where it is.",
     lambda rng: _scene(rng, 2, 5, margin=3, lo=10), tf_pivot_tip)


def tf_mirror_left(g):
    gl = _glyphs(g); out = copy(g)
    if not gl or not any(t[3] == "W" for t in gl): return None
    for o, col, fam, hd, tip, org in gl:
        if hd != "W": continue
        r0, c0, r1, c1 = bbox(o)
        for r, c in o: out[r][c] = 0
        for r, c in o: out[r][c0 + c1 - c] = col
    return out
rule("left_pointing_glyphs_mirrored", "Every pointed shape that points left is mirrored left-to-right inside its own box; shapes pointing any other way stay.",
     lambda rng: _scene(rng, 2, 6), tf_mirror_left)


# ---------------------------------------------------------------- motion along the heading
def _advance(g, steps, shadow=None, flip=False):
    gl = _glyphs(g)
    if not gl: return None
    moves = []
    for o, col, fam, hd, tip, org in gl:
        nh = OPP[hd] if flip else hd; dr, dc = DIR[nh]; n = steps(o)
        base = _repose(fam, nh, org) if flip else o
        moves.append((o, [(r + n * dr, c + n * dc) for r, c in base], col))
    out = _redraw(g, moves)
    if out is None or shadow is None: return out
    for old, new, col in moves:
        for r, c in set(old) - set(new): out[r][c] = shadow
    return out


rule("glyphs_step_one_in_heading", "Every pointed shape moves one cell in the direction it points.",
     lambda rng: _scene(rng, 2, 6), lambda g: _advance(g, lambda o: 1))
rule("glyphs_advance_by_cell_count", "Every pointed shape moves forward, in the direction it points, by as many cells as it has.",
     lambda rng: _scene(rng, 2, 5, lo=12), lambda g: _advance(g, len))
rule("glyphs_step_leaving_grey_shadow", "Every pointed shape moves one cell in its heading, and the cells it vacates turn grey (5).",
     lambda rng: _scene(rng, 2, 6), lambda g: _advance(g, lambda o: 1, shadow=5))
rule("glyphs_about_face_then_advance_two", "Every pointed shape turns a half turn in its box to face the other way, then moves two cells in its new heading.",
     lambda rng: _scene(rng, 2, 5, margin=2, lo=10), lambda g: _advance(g, lambda o: 2, flip=True))


# ---------------------------------------------------------------- glyphs and what lies ahead
def gi_targets(rng, every=False, dot_only=False, k_lo=2, k_hi=5):
    g = _scene(rng, k_lo, k_hi, margin=2)
    if g is None: return None
    gl = _glyphs(g); H, W = dims(g); placed = 0
    for o, col, fam, hd, tip, org in gl:
        if not every and rng.random() < 0.4: continue
        path, hit = _ray_cells(g, tip[0], tip[1], hd)
        if len(path) < 3:
            if every: return None
            continue
        r, c = rng.choice(path[2:])
        sh = [(0, 0)] if dot_only else rng.choice([[(0, 0)], [(0, 0), (0, 1)], [(0, 0), (1, 0)], [(0, 0), (0, 1), (1, 1)], [(0, 0), (1, 0), (1, 1)]])
        ar, ac = rng.choice(sh)
        cells_ = [(r + rr - ar, c + cc - ac) for rr, cc in sh]
        if all(0 <= y < H and 0 <= x < W and g[y][x] == 0 and all(g[yy][xx] == 0 for yy in range(y - 1, y + 2) for xx in range(x - 1, x + 2)
               if 0 <= yy < H and 0 <= xx < W and (yy, xx) not in cells_) for y, x in cells_):
            for y, x in cells_: g[y][x] = 5
            placed += 1
        elif every: return None
    return g if placed else None


def tf_paint_target(g):
    gl = _glyphs(g); out = copy(g)
    if not gl: return None
    for o, col, fam, hd, tip, org in gl:
        path, hit = _ray_cells(g, tip[0], tip[1], hd)
        if hit and g[hit[0]][hit[1]] == 5: flood(out, hit[0], hit[1], col)
    return out
rule("glyph_paints_grey_target_ahead", "Each pointed shape looks straight ahead; the first thing it sees, if it is a grey blob, is repainted in the shape's colour.",
     lambda rng: gi_targets(rng), tf_paint_target)


def tf_pull_dot(g):
    gl = _glyphs(g); out = copy(g)
    if not gl: return None
    for o, col, fam, hd, tip, org in gl:
        path, hit = _ray_cells(g, tip[0], tip[1], hd)
        if hit and g[hit[0]][hit[1]] == 5 and path:
            out[hit[0]][hit[1]] = 0; r, c = path[0]; out[r][c] = 5
    return out
rule("pointed_at_dot_pulled_to_tip", "A grey dot that a pointed shape is aimed at slides back to the cell directly in front of that shape's tip.",
     lambda rng: gi_targets(rng, dot_only=True), tf_pull_dot)


def tf_slide_to_target(g):
    gl = _glyphs(g)
    if not gl: return None
    moves = []
    for o, col, fam, hd, tip, org in gl:
        path, hit = _ray_cells(g, tip[0], tip[1], hd)
        if hit is None: return None
        n = len(path); dr, dc = DIR[hd]
        moves.append((o, [(r + n * dr, c + n * dc) for r, c in o], col))
    return _redraw(g, moves)
rule("glyph_slides_up_to_its_target", "Every pointed shape slides forward until its tip is directly against the grey dot it is aimed at.",
     lambda rng: gi_targets(rng, every=True, dot_only=True, k_lo=1, k_hi=4), tf_slide_to_target)


def tf_vanish_unaimed(g):
    gl = _glyphs(g); out = copy(g)
    if not gl: return None
    for o, col, fam, hd, tip, org in gl:
        path, hit = _ray_cells(g, tip[0], tip[1], hd)
        if hit is None:
            for r, c in o: out[r][c] = 0
    return out
rule("glyphs_aimed_at_nothing_vanish", "A pointed shape with nothing ahead of it before the grid edge is erased; a shape aimed at something stays.",
     lambda rng: gi_targets(rng, k_lo=3, k_hi=6), tf_vanish_unaimed)


def gi_one_marker(rng):
    g = _scene(rng, 2, 6, margin=2)
    if g is None: return None
    gl = _glyphs(g); o, col, fam, hd, tip, org = rng.choice(gl)
    path, hit = _ray_cells(g, tip[0], tip[1], hd)
    if len(path) < 3: return None
    r, c = rng.choice(path[2:]); g[r][c] = 5
    return g
def tf_crop_aimed(g):
    gl = _glyphs(g)
    if not gl: return None
    hits = [o for o, col, fam, hd, tip, org in gl if (lambda p: p[1] and g[p[1][0]][p[1][1]] == 5)(_ray_cells(g, tip[0], tip[1], hd))]
    if len(hits) != 1: return None
    return crop(g, *bbox(hits[0]))
rule("crop_glyph_aimed_at_grey_marker", "Exactly one pointed shape is aimed straight at the single grey marker; output that shape's bounding box.",
     gi_one_marker, tf_crop_aimed)


# ---------------------------------------------------------------- pairs of glyphs
def gi_facing(rng, k_pairs=1, extra=(0, 3)):
    h, w = _gsize(rng, 9); g = blank(h, w); fams = list(GLYPHS)
    for _ in range(k_pairs):
        for _try in range(30):
            vert = rng.random() < 0.5; fa, fb = rng.choice(fams), rng.choice(fams)
            a, b = (("S", "N") if vert else ("E", "W"))
            pa, pb = POSE[(fa, a)], POSE[(fb, b)]
            ha, wa = max(r for r, _ in pa) + 1, max(c for _, c in pa) + 1
            hb, wb = max(r for r, _ in pb) + 1, max(c for _, c in pb) + 1
            gap = rng.randint(1, 8)
            if vert:
                ta, tb = pa[0], pb[0]; r0 = rng.randint(0, h - 1); c0 = rng.randint(0, w - 1)
                ra, ca = r0, c0 - ta[1]; rb, cb = r0 + ha + gap, c0 - tb[1]
            else:
                ta, tb = pa[0], pb[0]; r0 = rng.randint(0, h - 1); c0 = rng.randint(0, w - 1)
                ra, ca = r0 - ta[0], c0; rb, cb = r0 - tb[0], c0 + wa + gap
            cells_a = [(ra + r, ca + c) for r, c in pa]; cells_b = [(rb + r, cb + c) for r, c in pb]
            allc = cells_a + cells_b
            if all(0 <= r < h and 0 <= c < w for r, c in allc) and all(
                    g[y][x] == 0 for r, c in allc for y in range(r - 1, r + 2) for x in range(c - 1, c + 2) if 0 <= y < h and 0 <= x < w):
                col = rng.choice([c for c in COLOURS if c != 5]); col2 = col if rng.random() < 0.5 else rng.choice([c for c in COLOURS if c != 5])
                for r, c in cells_a: g[r][c] = col
                for r, c in cells_b: g[r][c] = col2
                break
        else:
            return None
    for _ in range(rng.randint(*extra)):
        _stamp(rng, g, POSE[(rng.choice(fams), rng.choice(HEAD))], rng.choice([c for c in COLOURS if c != 5]), margin=1)
    return g


def _facing_pairs(g, gl):
    """pairs (A, B, path) where A's tip ray hits B's tip and B points back at A."""
    tips = {t[4]: t for t in gl}; pairs = []
    for t in gl:
        path, hit = _ray_cells(g, t[4][0], t[4][1], t[3])
        u = tips.get(hit)
        if u and u[3] == OPP[t[3]] and t[4] < u[4]: pairs.append((t, u, path))
    return pairs


def tf_join_facing(g):
    gl = _glyphs(g)
    if not gl: return None
    out = copy(g); pairs = _facing_pairs(g, gl)
    if not pairs: return None
    for a, b, path in pairs:
        for r, c in path: out[r][c] = 5
    return out
rule("facing_glyphs_joined_by_grey_line", "Two pointed shapes aimed straight at each other are joined tip to tip by a grey (5) line; other shapes are left alone.",
     lambda rng: gi_facing(rng, rng.randint(1, 2)), tf_join_facing)


def tf_close_gap(g):
    gl = _glyphs(g)
    if not gl: return None
    pairs = _facing_pairs(g, gl)
    if not pairs: return None
    moves = []
    for a, b, path in pairs:
        n = len(path) // 2; da, db = DIR[a[3]], DIR[b[3]]
        moves.append((a[0], [(r + n * da[0], c + n * da[1]) for r, c in a[0]], a[1]))
        moves.append((b[0], [(r + n * db[0], c + n * db[1]) for r, c in b[0]], b[1]))
    return _redraw(g, moves)
rule("facing_glyphs_close_the_gap", "Two pointed shapes aimed at each other slide toward one another at the same speed until their tips touch, or one empty cell remains when the gap is odd.",
     lambda rng: gi_facing(rng, 1, (0, 2)), tf_close_gap)


def tf_share_first_colour(g):
    gl = _glyphs(g)
    if not gl: return None
    out = copy(g); first = {}
    for t in sorted(gl, key=lambda t: t[5]):
        first.setdefault(t[3], t[1])
    for o, col, fam, hd, tip, org in gl:
        for r, c in o: out[r][c] = first[hd]
    return out
rule("same_heading_glyphs_take_first_colour", "Shapes pointing the same way are painted alike: each takes the colour of the topmost (then leftmost) shape with that heading.",
     lambda rng: _scene(rng, 3, 7), tf_share_first_colour)


# ---------------------------------------------------------------- summaries / crops
def tf_heading_strip(g):
    gl = _glyphs(g)
    if not gl: return None
    gl = sorted(gl, key=lambda t: (HEAD.index(t[3]), t[5]))
    tiles = [crop(g, *bbox(o)) for o, *_ in gl]
    for t, (o, *_rest) in zip(tiles, gl):
        for r in range(len(t)):
            for c in range(len(t[0])):
                if t[r][c] != _rest[0]: t[r][c] = 0
    H = max(len(t) for t in tiles); out = []
    for r in range(H):
        row = []
        for i, t in enumerate(tiles):
            row += (t[r] if r < len(t) else [0] * len(t[0])) + ([0] if i < len(tiles) - 1 else [])
        out.append(row)
    return out
rule("glyphs_lined_up_in_heading_order", "The pointed shapes are laid out left to right in a strip, one empty column apart, ordered by heading: up first, then right, down, left.",
     lambda rng: _scene(rng, 2, 5), tf_heading_strip)


def tf_heading_bars(g):
    gl = _glyphs(g)
    if not gl: return None
    cnt = [sum(1 for t in gl if t[3] == h) for h in HEAD]
    return [[i + 1 if c < cnt[i] else 0 for c in range(max(cnt))] for i in range(4)]
rule("heading_count_bar_chart", "Output four rows, one per heading up/right/down/left, each a bar in colour 1, 2, 3 or 4 as long as the number of shapes pointing that way.",
     lambda rng: _scene(rng, 2, 8), tf_heading_bars, digits=True)


def tf_crop_unique_heading(g):
    gl = _glyphs(g)
    if not gl: return None
    cnt = {}
    for t in gl: cnt[t[3]] = cnt.get(t[3], 0) + 1
    ones = [h for h, n in cnt.items() if n == 1]
    if len(ones) != 1 or len(cnt) < 2: return None
    o = next(t[0] for t in gl if t[3] == ones[0])
    return crop(g, *bbox(o))
rule("crop_glyph_with_unique_heading", "Exactly one shape points a way no other shape does; output that shape's bounding box.",
     lambda rng: _scene(rng, 3, 7), tf_crop_unique_heading)


def tf_crop_point_up(g):
    gl = _glyphs(g)
    if not gl or len(gl) != 1 or gl[0][3] == "N": return None
    o, col, fam, hd, tip, org = gl[0]; p = POSE[(fam, "N")]
    out = blank(max(r for r, _ in p) + 1, max(c for _, c in p) + 1)
    for r, c in p: out[r][c] = col
    return out
rule("single_glyph_cropped_pointing_up", "Output just the single pointed shape, cut out to its own box and turned so that it points up.",
     lambda rng: _scene(rng, 1, 1), tf_crop_point_up)


# ---------------------------------------------------------------- chevrons
def tf_chevron_trail(g):
    gl = _glyphs(g); out = copy(g)
    if not gl: return None
    for o, col, fam, hd, tip, org in gl:
        if fam != "chevron": continue
        path, hit = _ray_cells(g, tip[0], tip[1], OPP[hd])
        for r, c in path: out[r][c] = col
    return out
rule("chevrons_trail_backward_to_edge", "Each chevron draws a line of its own colour from its point straight backward, away from where it points, until it reaches the edge or another shape.",
     lambda rng: _scene(rng, 2, 5, fams=["chevron"]), tf_chevron_trail)


def tf_chevron_echo(g):
    gl = _glyphs(g); out = copy(g); H, W = dims(g)
    if not gl: return None
    for o, col, fam, hd, tip, org in gl:
        dr, dc = DIR[OPP[hd]]
        for r, c in o:
            rr, cc = r + 2 * dr, c + 2 * dc
            if not (0 <= rr < H and 0 <= cc < W) or g[rr][cc] != 0: return None
            out[rr][cc] = 5
    return out
rule("chevron_grey_echo_two_behind", "Behind every chevron, two cells back from it, a grey (5) copy of the chevron is drawn nested inside its opening.",
     lambda rng: _scene(rng, 2, 5, fams=["chevron"], margin=2), tf_chevron_echo)


# ---------------------------------------------------------------- staples (U shapes): open side = heading
def _staple_cells(hd, p, wd):
    """U opening hd: prongs of p cells above a base of width wd (wd >= 3), as normalised cells."""
    cells_ = [(r, 0) for r in range(p)] + [(r, wd - 1) for r in range(p)] + [(p, c) for c in range(wd)]
    for _ in range(HEAD.index(hd)): cells_ = _norm(_rotcw(cells_))
    return cells_


def _staple(o):
    """(heading, bbox) if o is a hollow rectangle outline missing exactly one full side (corners kept)."""
    r0, c0, r1, c1 = bbox(o); s = set(o)
    if r1 - r0 < 1 or c1 - c0 < 1: return None
    frame = {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if r in (r0, r1) or c in (c0, c1)}
    sides = {"N": {(r0, c) for c in range(c0 + 1, c1)}, "S": {(r1, c) for c in range(c0 + 1, c1)},
             "W": {(r, c0) for r in range(r0 + 1, r1)}, "E": {(r, c1) for r in range(r0 + 1, r1)}}
    for hd, side in sides.items():
        if side and s == frame - side: return hd, (r0, c0, r1, c1)
    return None


def gi_staples(rng, k_lo=1, k_hi=4, margin=1):
    h, w = _gsize(rng, 8); g = blank(h, w); k = rng.randint(k_lo, k_hi); n = 0
    for _ in range(k):
        sh = _staple_cells(rng.choice(HEAD), rng.randint(1, 4), rng.randint(3, 6))
        if _stamp(rng, g, sh, rng.choice([c for c in COLOURS if c not in (5, 8)]), margin=margin): n += 1
    return g if n else None


def _staples(g):
    out = []
    for o in objects(g, 0):
        k = _staple(o)
        if k is None: return None
        out.append((o, g[o[0][0]][o[0][1]]) + k)
    return out


def tf_staple_fill(g):
    st = _staples(g); out = copy(g)
    if not st: return None
    for o, col, hd, (r0, c0, r1, c1) in st:
        s = set(o)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if (r, c) not in s: out[r][c] = 8
    return out
rule("staple_filled_between_prongs", "Every staple (a U shape) has the space between its two prongs filled with colour 8, right up to the open end.",
     gi_staples, tf_staple_fill)


def tf_staple_seal(g):
    st = _staples(g); out = copy(g)
    if not st: return None
    for o, col, hd, (r0, c0, r1, c1) in st:
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if (r in (r0, r1) or c in (c0, c1)) and (r, c) not in set(o): out[r][c] = 5
    return out
rule("staples_sealed_with_grey", "Every staple (a U shape) is closed into a hollow rectangle by a grey (5) bar across its open end.",
     gi_staples, tf_staple_seal)


def tf_staple_colour(g):
    st = _staples(g); out = copy(g)
    if not st: return None
    for o, col, hd, bb in st:
        for r, c in o: out[r][c] = HEAD.index(hd) + 1
    return out
rule("staples_recoloured_by_open_side", "Every staple (a U shape) is repainted by which way it opens: 1 up, 2 right, 3 down, 4 left.",
     lambda rng: gi_staples(rng, 2, 5), tf_staple_colour, digits=True)


def tf_staple_prongs(g):
    st = _staples(g); out = copy(g)
    if not st: return None
    for o, col, hd, (r0, c0, r1, c1) in st:
        ends = {"N": [(r0, c0), (r0, c1)], "S": [(r1, c0), (r1, c1)], "W": [(r0, c0), (r1, c0)], "E": [(r0, c1), (r1, c1)]}[hd]
        for r, c in ends:
            path, hit = _ray_cells(g, r, c, hd)
            for y, x in path: out[y][x] = col
    return out
rule("staple_prongs_extend_to_edge", "Both prongs of every staple (a U shape) grow out through its open side, in the staple's colour, until they hit the edge or another shape.",
     gi_staples, tf_staple_prongs)


def gi_facing_staples(rng):
    h, w = _gsize(rng, 9); g = blank(h, w)
    for _try in range(40):
        p1, p2, wd, gap = rng.randint(1, 3), rng.randint(1, 3), rng.randint(3, 6), rng.randint(1, 7)
        a = _staple_cells("S", p1, wd); b = _staple_cells("N", p2, wd)
        r0, c0 = rng.randint(0, h - 1), rng.randint(0, w - 1)
        cells_ = [(r0 + r, c0 + c) for r, c in a] + [(r0 + p1 + 1 + gap + r, c0 + c) for r, c in b]
        if rng.random() < 0.5: cells_ = [(c, r) for r, c in cells_]
        if all(0 <= r < h and 0 <= c < w for r, c in cells_) and all(
                g[y][x] == 0 for r, c in cells_ for y in range(r - 1, r + 2) for x in range(c - 1, c + 2) if 0 <= y < h and 0 <= x < w):
            col = rng.choice([c for c in COLOURS if c != 5])
            for r, c in cells_: g[r][c] = col
            break
    else:
        return None
    for _ in range(rng.randint(0, 2)):
        _stamp(rng, g, _staple_cells(rng.choice(HEAD), rng.randint(1, 3), rng.randint(3, 6)), rng.choice([c for c in COLOURS if c != 5]))
    return g
def tf_join_staples(g):
    st = _staples(g)
    if not st: return None
    out = copy(g); done = False
    for a in st:
        for b in st:
            oa, ca, ha, (ar0, ac0, ar1, ac1) = a; ob, cb, hb, (br0, bc0, br1, bc1) = b
            if hb != OPP[ha] or ca != cb: continue
            if ha == "S" and (ac0, ac1) == (bc0, bc1) and br0 > ar1:
                cols_ = [ac0, ac1]; rows_ = range(ar1 + 1, br0)
            elif ha == "E" and (ar0, ar1) == (br0, br1) and bc0 > ac1:
                cols_ = range(ac1 + 1, bc0); rows_ = [ar0, ar1]
            else: continue
            if all(g[r][c] == 0 for r in rows_ for c in cols_):
                for r in rows_:
                    for c in cols_: out[r][c] = ca
                done = True
    return out if done else None
rule("facing_staples_join_into_frame", "Two staples of one colour that open toward each other with their prongs lined up have the prongs extended to meet, making one hollow rectangle.",
     gi_facing_staples, tf_join_staples)


# ---------------------------------------------------------------- L hooks of varying arm length
def _hook(o):
    """(corner, long end, short end) for an L made of one full bbox row and one full bbox column, unequal arms."""
    r0, c0, r1, c1 = bbox(o); s = set(o)
    if r1 == r0 or c1 == c0 or len(o) != (r1 - r0) + (c1 - c0) + 1: return None
    for rr in (r0, r1):
        for cc in (c0, c1):
            if s == {(rr, c) for c in range(c0, c1 + 1)} | {(r, cc) for r in range(r0, r1 + 1)}:
                vend = (r1 if rr == r0 else r0, cc); hend = (rr, c1 if cc == c0 else c0)
                lv, lh = r1 - r0, c1 - c0
                if lv == lh: return None
                return (rr, cc), (vend if lv > lh else hend), (hend if lv > lh else vend)
    return None


def gi_hooks(rng, k_lo=2, k_hi=5):
    h, w = _gsize(rng, 8); g = blank(h, w); n = 0
    for _ in range(rng.randint(k_lo, k_hi)):
        arm, foot = rng.randint(3, 6), rng.randint(1, 2)
        sh = [(r, 0) for r in range(arm)] + [(arm - 1, c) for c in range(1, foot + 1)]
        for _ in range(rng.randrange(4)): sh = _norm(_rotcw(sh))
        if rng.random() < 0.5: sh = _norm([(r, -c) for r, c in sh])
        if _stamp(rng, g, sh, rng.choice([c for c in COLOURS if c != 5])): n += 1
    return g if n else None


def _hooks(g):
    out = []
    for o in objects(g, 0, conn8=False):
        k = _hook(o)
        if k is None: return None
        out.append((o, g[o[0][0]][o[0][1]]) + k)
    return out


def tf_hook_foot_grows(g):
    hk = _hooks(g); out = copy(g); H, W = dims(g)
    if not hk: return None
    for o, col, (kr, kc), (lr, lc), (sr, sc) in hk:
        L = max(abs(lr - kr), abs(lc - kc)); dr = (sr - kr) and (1 if sr > kr else -1); dc = (sc - kc) and (1 if sc > kc else -1)
        for i in range(1, L + 1):
            r, c = kr + i * dr, kc + i * dc
            if not (0 <= r < H and 0 <= c < W) or (out[r][c] != 0 and (r, c) not in o): return None
            out[r][c] = col
    return out
rule("hook_short_arm_grows_to_match", "Every L hook has its short arm lengthened until both arms are equal, in the hook's own colour.",
     gi_hooks, tf_hook_foot_grows)


def tf_hook_frame(g):
    hk = _hooks(g); out = copy(g)
    if not hk: return None
    for o, col, k, l, s in hk:
        r0, c0, r1, c1 = bbox(o)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if (r in (r0, r1) or c in (c0, c1)) and out[r][c] == 0: out[r][c] = 5
    return out
rule("hooks_completed_to_grey_frames", "Every L hook is completed into the hollow outline of its bounding box; the added cells are grey (5).",
     lambda rng: gi_hooks(rng, 1, 4), tf_hook_frame)


def tf_hook_corner_colour(g):
    hk = _hooks(g); out = copy(g)
    if not hk: return None
    for o, col, (kr, kc), l, s in hk:
        r0, c0, r1, c1 = bbox(o)
        code = {(r0, c0): 1, (r0, c1): 2, (r1, c1): 3, (r1, c0): 4}[(kr, kc)]
        for r, c in o: out[r][c] = code
    return out
rule("hooks_recoloured_by_corner_position", "Every L hook is repainted by where its corner sits in its own box: 1 top-left, 2 top-right, 3 bottom-right, 4 bottom-left.",
     lambda rng: gi_hooks(rng, 2, 6), tf_hook_corner_colour, digits=True)


# ---------------------------------------------------------------- tees: a bar with a stem from its middle
def _tee(o):
    """(bar cells, stem cells, heading of the stem, stem end) for a T of odd bar width with a centred stem."""
    r0, c0, r1, c1 = bbox(o); s = set(o)
    for hd in HEAD:
        if hd in "NS":
            br = r1 if hd == "N" else r0; bar = {(br, c) for c in range(c0, c1 + 1)}
            if (c1 - c0) % 2: continue
            m = (c0 + c1) // 2; stem = {(r, m) for r in range(r0, r1 + 1)} - bar; end = (r0, m) if hd == "N" else (r1, m)
        else:
            bc = c1 if hd == "W" else c0; bar = {(r, bc) for r in range(r0, r1 + 1)}
            if (r1 - r0) % 2: continue
            m = (r0 + r1) // 2; stem = {(m, c) for c in range(c0, c1 + 1)} - bar; end = (m, c0) if hd == "W" else (m, c1)
        if stem and s == bar | stem: return bar, stem, hd, end
    return None


def gi_tees(rng, k_lo=2, k_hi=5):
    h, w = _gsize(rng, 9); g = blank(h, w); n = 0
    for _ in range(rng.randint(k_lo, k_hi)):
        bw, st = rng.choice([3, 5, 7]), rng.randint(1, 5)
        sh = [(st, c) for c in range(bw)] + [(r, bw // 2) for r in range(st)]
        for _ in range(rng.randrange(4)): sh = _norm(_rotcw(sh))
        if _stamp(rng, g, sh, rng.choice([c for c in COLOURS if c != 5])): n += 1
    return g if n else None


def _tees(g):
    out = []
    for o in objects(g, 0, conn8=False):
        k = _tee(o)
        if k is None: return None
        out.append((o, g[o[0][0]][o[0][1]]) + k)
    return out


def tf_tee_stem_match(g):
    ts = _tees(g); out = copy(g); H, W = dims(g)
    if not ts: return None
    for o, col, bar, stem, hd, end in ts:
        want = len(bar) // 2; have = len(stem)
        if want == have: continue
        dr, dc = DIR[hd]; (br, bc) = next(iter(bar)); m = [p for p in bar if any(q in stem for q in [(p[0] + dr, p[1] + dc)])][0]
        for r, c in stem: out[r][c] = 0
        for i in range(1, want + 1):
            r, c = m[0] + i * dr, m[1] + i * dc
            if not (0 <= r < H and 0 <= c < W) or (out[r][c] != 0 and (r, c) not in o): return None
            out[r][c] = col
    return out
rule("tee_stem_resized_to_half_bar", "Every T shape's stem is lengthened or shortened, in the T's colour, until it is as long as one arm of its bar (the cells on one side of the junction).",
     gi_tees, tf_tee_stem_match)


def tf_tee_stem_end_dot(g):
    ts = _tees(g); out = copy(g); H, W = dims(g)
    if not ts: return None
    for o, col, bar, stem, hd, (er, ec) in ts:
        dr, dc = DIR[hd]; r, c = er + dr, ec + dc
        if not (0 <= r < H and 0 <= c < W) or g[r][c] != 0: return None
        out[r][c] = 5
    return out
rule("grey_dot_beyond_tee_stem", "A grey (5) dot is placed in the cell just beyond the end of every T shape's stem, continuing the stem's direction.",
     lambda rng: gi_tees(rng, 2, 6), tf_tee_stem_end_dot)
