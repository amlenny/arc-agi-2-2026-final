# b013_layers.py -- overlap, occlusion and layers: stacks of solid rectangles whose order is read from which
# one is fully visible, bring-to-front / send-to-back, completing hidden parts, cover counts, intersections,
# unions, shadows, transparency keys, patches over tilings, peeling and onion layers of thick objects.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


# ---------------------------------------------------------------- local helpers
def _size(rng, lo=7, hi=20):
    """At least a third of inputs land in the 21-30 band."""
    if rng.random() < 0.35:
        return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _by_colour(g, skip=(0,)):
    d = {}
    for r, row in enumerate(g):
        for c, v in enumerate(row):
            if v not in skip:
                d.setdefault(v, []).append((r, c))
    return d


def _full(cs):
    r0, c0, r1, c1 = bbox(cs)
    return len(cs) == (r1 - r0 + 1) * (c1 - c0 + 1)


def _layers(g, wild=()):
    """Infer a stack of one-colour solid rectangles. A colour whose bounding box is covered by its own cells
    plus already-peeled (or wild) cells is the next layer down. Returns [(col, r0, c0, r1, c1)] top first."""
    d = _by_colour(g, skip=(0,) + tuple(wild))
    free = set(cells(g, lambda v: v in wild))
    boxes = {col: bbox(cs) for col, cs in d.items()}
    sets = {col: set(cs) for col, cs in d.items()}
    order, remaining = [], set(d)
    while remaining:
        cands = [col for col in sorted(remaining)
                 if all((r, c) in sets[col] or (r, c) in free
                        for r in range(boxes[col][0], boxes[col][2] + 1) for c in range(boxes[col][1], boxes[col][3] + 1))]
        if not cands:
            return None
        col = cands[0]; r0, c0, r1, c1 = boxes[col]
        order.append((col, r0, c0, r1, c1))
        free |= {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)}
        remaining.remove(col)
    return order


def _draw(H, W, layers, base=None):
    """Paint layers (top first) onto a blank grid, bottom first."""
    g = blank(H, W) if base is None else base
    for col, r0, c0, r1, c1 in reversed(layers):
        rect(g, r0, c0, r1, c1, col)
    return g


def _rand_rect(rng, H, W, lo=2, hi=None):
    hi = hi or max(lo, min(H, W) * 2 // 3)
    h, w = rng.randint(lo, min(hi, H)), rng.randint(lo, min(hi, W))
    r0, c0 = rng.randint(0, H - h), rng.randint(0, W - w)
    return r0, c0, r0 + h - 1, c0 + w - 1


def _overlapping_rect(rng, H, W, prev, lo=2, hi=None):
    """A random rectangle partially overlapping prev without containing it."""
    pr0, pc0, pr1, pc1 = prev
    hi = hi or max(lo, min(H, W) * 2 // 3)
    for _ in range(60):
        h, w = rng.randint(lo, min(hi, H)), rng.randint(lo, min(hi, W))
        ra, rb = max(0, pr0 - h + 1), min(H - h, pr1)
        ca, cb = max(0, pc0 - w + 1), min(W - w, pc1)
        if ra > rb or ca > cb:
            continue
        r0, c0 = rng.randint(ra, rb), rng.randint(ca, cb)
        r1, c1 = r0 + h - 1, c0 + w - 1
        if r0 <= pr0 and c0 <= pc0 and r1 >= pr1 and c1 >= pc1:
            continue
        return r0, c0, r1, c1
    return None


def _stack(rng, k, exclude=(5,), lo=2, hw=None, hi=None):
    """A chain of k overlapping solid rectangles, each on top of the previous. Returns (grid, layers top first)
    only when the layer inference reproduces the true order exactly."""
    H, W = hw or _size(rng)
    cols = colours(rng, k, exclude=(0,) + tuple(exclude))
    rects = []
    for i in range(k):
        box = _rand_rect(rng, H, W, lo, hi) if i == 0 else _overlapping_rect(rng, H, W, rects[-1][1:], lo, hi)
        if box is None:
            return None
        rects.append((cols[i],) + box)
    top_first = rects[::-1]
    g = _draw(H, W, top_first)
    if _layers(g) != top_first:
        return None
    return g, top_first


def _mixed(rng, exclude=(5,)):
    """A chain stack plus some isolated rectangles; inference must still read every extent."""
    st = _stack(rng, rng.randint(2, 4), exclude)
    if st is None:
        return None
    g, lay = st; H, W = dims(g)
    used = {c for c, *_ in lay}
    for _ in range(rng.randint(1, 3)):
        free = [c for c in COLOURS if c not in used and c not in exclude]
        if not free:
            break
        r0, c0, r1, c1 = _rand_rect(rng, H, W, 2, max(2, min(H, W) // 3))
        if all(g[r][c] == 0 for r in range(max(0, r0 - 1), min(H, r1 + 2)) for c in range(max(0, c0 - 1), min(W, c1 + 2))):
            col = rng.choice(free); used.add(col); rect(g, r0, c0, r1, c1, col)
    lay2 = _layers(g)
    if lay2 is None or not set(lay) <= set(lay2):
        return None
    return g


def _cover(H, W, layers):
    cnt = blank(H, W)
    for col, r0, c0, r1, c1 in layers:
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                cnt[r][c] += 1
    return cnt


def _depth(g, bg=0):
    """Layer number of each non-background cell: 1 on the outside, growing inward (4-neighbour erosion)."""
    H, W = dims(g); d = blank(H, W); q = []
    for r in range(H):
        for c in range(W):
            if g[r][c] != bg and any(not (0 <= r + dr < H and 0 <= c + dc < W) or g[r + dr][c + dc] == bg
                                     for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                d[r][c] = 1; q.append((r, c))
    i = 0
    while i < len(q):
        r, c = q[i]; i += 1
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < H and 0 <= nc < W and g[nr][nc] != bg and d[nr][nc] == 0:
                d[nr][nc] = d[r][c] + 1; q.append((nr, nc))
    return d


def _blobs(g, bg=0):
    """4-connected components of non-background cells regardless of colour (glib splits by colour)."""
    H, W = dims(g); seen, out = set(), []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or (r, c) in seen:
                continue
            comp, st = [], [(r, c)]; seen.add((r, c))
            while st:
                y, x = st.pop(); comp.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen and g[ny][nx] != bg:
                        seen.add((ny, nx)); st.append((ny, nx))
            out.append(comp)
    return out


def _thick_shape(rng):
    """A 4-connected union of one to three small rectangles, normalised."""
    for _ in range(20):
        cs = set()
        for _ in range(rng.randint(1, 3)):
            h, w = rng.randint(3, 6), rng.randint(3, 6); r0, c0 = rng.randint(0, 4), rng.randint(0, 4)
            cs |= {(r, c) for r in range(r0, r0 + h) for c in range(c0, c0 + w)}
        g = blank(12, 12)
        for r, c in cs:
            g[r][c] = 1
        if len(_blobs(g)) == 1:
            r0 = min(r for r, _ in cs); c0 = min(c for _, c in cs)
            return sorted((r - r0, c - c0) for r, c in cs)
    return None


def _blob_scene(rng, exclude=(5,)):
    H, W = _size(rng, 8, 20); g = blank(H, W); k = rng.randint(1, 4)
    shapes = [_thick_shape(rng) for _ in range(k)]
    if any(s is None for s in shapes):
        return None
    cols = [rng.choice([c for c in COLOURS if c not in exclude]) for _ in range(k)]
    if place_shapes(rng, g, shapes, cols, margin=1) is None:
        return None
    return g


def _period(g, wild=9):
    """Smallest-area (rows, cols) period consistent with every non-wild cell, every residue class seen."""
    H, W = dims(g)
    for area in range(1, H * W + 1):
        for ph in range(1, H + 1):
            if area % ph or area // ph > W:
                continue
            pw = area // ph; ref = {}; ok = True
            for r in range(H):
                for c in range(W):
                    v = g[r][c]
                    if v == wild:
                        continue
                    k = (r % ph, c % pw)
                    if ref.setdefault(k, v) != v:
                        ok = False; break
                if not ok:
                    break
            if ok and len(ref) == ph * pw:
                return ph, pw, ref
    return None


def _tiled(rng, patch=9):
    H, W = _size(rng, 8, 20)
    th, tw = rng.randint(2, 4), rng.randint(2, 4)
    cols = colours(rng, rng.randint(2, 3), exclude=(0, patch))
    tile = [[rng.choice(cols + [0]) for _ in range(tw)] for _ in range(th)]
    if len({v for row in tile for v in row}) < 2:
        return None
    orig = [[tile[r % th][c % tw] for c in range(W)] for r in range(H)]
    ph, pw = rng.randint(2, max(2, H // 3)), rng.randint(2, max(2, W // 3))
    pr, pc = rng.randint(0, H - ph), rng.randint(0, W - pw)
    g = copy(orig); rect(g, pr, pc, pr + ph - 1, pc + pw - 1, patch)
    return g, orig, (pr, pc, pr + ph - 1, pc + pw - 1)


def _restore(g, patch=9):
    p = _period(g, patch)
    if p is None:
        return None
    ph, pw, ref = p
    return [[ref[(r % ph, c % pw)] if v == patch else v for c, v in enumerate(row)] for r, row in enumerate(g)]


def _gen_stack(k_lo, k_hi, exclude=(5,), lo=2):
    def gi(rng):
        st = _stack(rng, rng.randint(k_lo, k_hi), exclude, lo)
        return None if st is None else st[0]
    return gi


# ---------------------------------------------------------------- rules
# 1 top rectangle recoloured grey
def tf_top_grey(g):
    lay = _layers(g)
    if lay is None or len(lay) < 2: return None
    H, W = dims(g); out = copy(g); col, r0, c0, r1, c1 = lay[0]
    return rect(out, r0, c0, r1, c1, 5)
rule("top_rectangle_recoloured_grey", "Overlapping solid rectangles: the one on top (the only one fully visible) is recoloured grey (5).", _gen_stack(2, 5), tf_top_grey)


# 2 bottom rectangle to front
def tf_bottom_front(g):
    lay = _layers(g)
    if lay is None or len(lay) < 2: return None
    H, W = dims(g)
    return _draw(H, W, [lay[-1]] + lay[:-1])
rule("bottom_rectangle_to_front", "The rectangle at the bottom of the pile is brought to the front and drawn complete over the others.", _gen_stack(2, 5), tf_bottom_front)


# 3 hidden frame border completed through the solid rectangle on top
def gi_frame_under(rng):
    H, W = _size(rng); F, S = colours(rng, 2)
    for _ in range(30):
        fr = _rand_rect(rng, H, W, 4); sb = _overlapping_rect(rng, H, W, fr, 2)
        if sb is None: continue
        g = blank(H, W); rect(g, *fr, F, fill=False); rect(g, *sb, S)
        d = _by_colour(g)
        if F in d and bbox(d[F]) == fr and _full(d[S]) and tf_frame_under(g) != g:
            return g
    return None
def tf_frame_under(g):
    d = _by_colour(g)
    if len(d) != 2: return None
    S = [c for c in d if _full(d[c])]
    if len(S) != 1: return None
    F = [c for c in d if c != S[0]][0]
    out = copy(g); return rect(out, *bbox(d[F]), F, fill=False)
rule("hidden_frame_border_completed", "A hollow frame is partly covered by a solid rectangle; the frame's missing border is drawn back on top so its outline is whole.", gi_frame_under, tf_frame_under)


# 4 remove the top rectangle, revealing what was under it
def tf_remove_top(g):
    lay = _layers(g)
    if lay is None or len(lay) < 2: return None
    H, W = dims(g); return _draw(H, W, lay[1:])
rule("top_rectangle_removed_reveals_below", "The fully visible rectangle on top is removed; the rectangles it covered are completed where it was.", _gen_stack(2, 5), tf_remove_top)


# 5 how many rectangles cover each cell
def tf_cover_count(g):
    lay = _layers(g)
    if lay is None or len(lay) < 2: return None
    H, W = dims(g); return _cover(H, W, lay)
rule("rectangle_cover_counts", "Every cell is replaced by the number of rectangles lying over it (reading each rectangle's full extent from its visible edges); empty cells stay 0.", _gen_stack(2, 5), tf_cover_count)


# 6 intersection of two rectangles recoloured grey
def tf_intersection(g):
    lay = _layers(g)
    if lay is None or len(lay) != 2: return None
    (_, a0, b0, a1, b1), (_, c0, d0, c1, d1) = lay
    out = copy(g)
    return rect(out, max(a0, c0), max(b0, d0), min(a1, c1), min(b1, d1), 5)
rule("two_rectangles_intersection_grey", "Two solid rectangles overlap; the cells belonging to both are recoloured grey (5).", _gen_stack(2, 2), tf_intersection)


# 7 outline of the union
def tf_union_outline(g):
    lay = _layers(g)
    if lay is None or len(lay) < 2: return None
    H, W = dims(g); cov = _cover(H, W, lay); out = blank(H, W)
    for r in range(H):
        for c in range(W):
            if cov[r][c] and any(not (0 <= r + dr < H and 0 <= c + dc < W) or cov[r + dr][c + dc] == 0
                                 for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[r][c] = lay[0][0]
    return out
rule("rectangles_union_outline", "The overlapping rectangles are merged into one silhouette whose outline is drawn in the top rectangle's colour; everything inside is emptied.", _gen_stack(2, 4), tf_union_outline)


# 8 a frame cut off by the grid edge, completed about its centre marker
def gi_cut_frame(rng):
    H, W = _size(rng, 6, 20); hh, hw = rng.randint(2, 7), rng.randint(2, 7); F, M = colours(rng, 2)
    cr, cc = rng.randint(0, H - 1), rng.randint(0, W - 1)
    ct, cb, cl, cR = cr - hh < 0, cr + hh >= H, cc - hw < 0, cc + hw >= W
    if (ct and cb) or (cl and cR) or not (ct or cb or cl or cR): return None
    g = blank(H, W)
    for r in range(cr - hh, cr + hh + 1):
        for c in range(cc - hw, cc + hw + 1):
            if 0 <= r < H and 0 <= c < W and (r in (cr - hh, cr + hh) or c in (cc - hw, cc + hw)):
                g[r][c] = F
    g[cr][cc] = M
    return g if sum(v == F for row in g for v in row) >= 3 else None
def tf_cut_frame(g):
    d = _by_colour(g)
    if len(d) != 2: return None
    M = [c for c in d if len(d[c]) == 1]; F = [c for c in d if len(d[c]) > 1]
    if len(M) != 1 or len(F) != 1: return None
    (cr, cc), = d[M[0]]; r0, c0, r1, c1 = bbox(d[F[0]])
    hh, hw = max(cr - r0, r1 - cr), max(cc - c0, c1 - cc)
    out = blank(2 * hh + 1, 2 * hw + 1); rect(out, 0, 0, 2 * hh, 2 * hw, F[0], fill=False); out[hh][hw] = M[0]
    return out
rule("cut_off_frame_completed_about_centre", "A hollow frame with a marked centre runs off the grid edge; output the whole frame, extending the visible sides symmetrically about the centre cell.", gi_cut_frame, tf_cut_frame)


# 9 output the hidden part of the lower rectangle
def tf_hidden_part(g):
    lay = _layers(g)
    if lay is None or len(lay) != 2: return None
    (tcol, *_), (bcol, r0, c0, r1, c1) = lay
    out = crop(g, r0, c0, r1, c1)
    return [[bcol if v == tcol else 0 for v in row] for row in out]
rule("hidden_part_of_lower_rectangle", "Two rectangles overlap; output the lower rectangle's bounding box showing only the part hidden under the upper one, in the lower colour.", _gen_stack(2, 2), tf_hidden_part)


# 10 legend gives stacking order
def gi_legend_order(rng):
    H, W = _size(rng, 8, 20); k = rng.randint(2, 4); cols = colours(rng, k, exclude=(0, 5))
    g = blank(H, W)
    for i, c in enumerate(cols): g[i][0] = c
    for r in range(H): g[r][1] = 5
    rects = []
    for i in range(k):
        box = _rand_rect(rng, H, W - 2, 2) if i == 0 else _overlapping_rect(rng, H, W - 2, rects[-1], 2)
        if box is None: return None
        rects.append(box)
    order = cols[:]; rng.shuffle(order)
    for col, (r0, c0, r1, c1) in zip(order, rects): rect(g, r0, c0 + 2, r1, c1 + 2, col)
    for col, (r0, c0, r1, c1) in zip(order, rects):
        vis = [(r, c) for r, c in cells(g, lambda v: v == col) if c >= 2]
        if not vis or bbox(vis) != (r0, c0 + 2, r1, c1 + 2): return None
    out = tf_legend_order(g)
    return g if out is not None and out != g else None
def tf_legend_order(g):
    H, W = dims(g); legend = [g[r][0] for r in range(H) if g[r][0]]
    out = [row[:2] + [0] * (W - 2) for row in g]
    for col in reversed(legend):
        cs = [(r, c) for r, c in cells(g, lambda v: v == col) if c >= 2]
        if not cs: return None
        rect(out, *bbox(cs), col)
    return out
rule("legend_column_sets_stacking_order", "The left column lists colours from front to back; the rectangles on the right are redrawn stacked in that order, each one's extent read from its visible edges.", gi_legend_order, tf_legend_order)


# 11 one-cell offset grey shadows
def gi_rects_apart(rng, exclude=(5,), margin=1):
    H, W = _size(rng, 7, 20); g = blank(H, W); k = rng.randint(1, 6); n = 0
    for _ in range(60):
        r0, c0, r1, c1 = _rand_rect(rng, H, W, 1, max(2, min(H, W) // 3))
        if all(g[r][c] == 0 for r in range(max(0, r0 - margin), min(H, r1 + margin + 1)) for c in range(max(0, c0 - margin), min(W, c1 + margin + 1))):
            rect(g, r0, c0, r1, c1, rng.choice([c for c in COLOURS if c not in exclude])); n += 1
            if n >= k: break
    return g if n else None
def tf_shadow(g):
    H, W = dims(g); out = copy(g)
    for r, c in cells(g, lambda v: v != 0):
        if r + 1 < H and c + 1 < W and g[r + 1][c + 1] == 0:
            out[r + 1][c + 1] = 5
    return out
rule("rectangles_cast_grey_shadow", "Every rectangle casts a grey (5) shadow one cell down and one cell right, drawn only where the background shows.", lambda rng: gi_rects_apart(rng, (5,), 2), tf_shadow)


# 12 transparency: a key names the colour where two rectangles overlap
def gi_key_overlap(rng):
    H, W = _size(rng, 9, 20); A, B, C = colours(rng, 3, exclude=(0, 5))
    st = _stack(rng, 2, (5, A, B, C), 2, hw=(H - 2, W))
    if st is None: return None
    field, lay = st
    g = [[0] * W, [5] * W] + field
    g[0][0], g[0][1], g[0][2] = A, B, C
    bcol, tcol = lay[1][0], lay[0][0]
    for r in range(2, H):
        for c in range(W):
            if g[r][c] == bcol: g[r][c] = A
            elif g[r][c] == tcol: g[r][c] = B
    return g
def tf_key_overlap(g):
    A, B, C = g[0][0], g[0][1], g[0][2]
    lay = _layers(g[2:])
    if lay is None or len(lay) != 2: return None
    (_, a0, b0, a1, b1), (_, c0, d0, c1, d1) = lay
    out = copy(g)
    return rect(out, max(a0, c0) + 2, max(b0, d0) + 2, min(a1, c1) + 2, min(b1, d1) + 2, C)
rule("overlap_takes_key_mix_colour", "The three cells at the top-left are a key: where the first two colours' rectangles overlap below the grey line, the overlap is painted the third colour.", gi_key_overlap, tf_key_overlap)


# 13 a patch covers a tiled pattern; restore the tiling
def gi_patch_tiling(rng):
    t = _tiled(rng)
    if t is None: return None
    g, orig, _ = t
    return g if _restore(g) == orig else None
rule("patch_removed_tiling_restored", "A solid colour-9 patch hides part of a repeating tiled pattern; the patch is removed and the pattern continued underneath it.", gi_patch_tiling, _restore)


# 14 peel the outer layer of every object
def tf_peel(g):
    d = _depth(g); out = [[v if d[r][c] >= 2 else 0 for c, v in enumerate(row)] for r, row in enumerate(g)]
    return out if any(v for row in out for v in row) else None
rule("peel_outer_layer", "Every object loses its outermost layer: cells that touch the background on any side are erased.", _blob_scene, tf_peel)


# 15 onion layers numbered from the outside
def tf_onion(g):
    d = _depth(g); return [[min(9, d[r][c]) for c in range(len(row))] for r, row in enumerate(g)]
rule("onion_layers_numbered_outside_in", "Each object's cells are renumbered by layer: the outer skin becomes 1, the layer inside it 2, then 3, and so on toward the core.", _blob_scene, tf_onion)


# 16 partly hidden rectangles turn grey
def tf_occluded_grey(g):
    d = _by_colour(g); out = copy(g)
    if not any(not _full(cs) for cs in d.values()): return None
    for col, cs in d.items():
        if not _full(cs):
            for r, c in cs: out[r][c] = 5
    return out
rule("occluded_rectangles_turn_grey", "Rectangles that are partly hidden under another rectangle turn grey (5); rectangles seen in full keep their colour.", _mixed, tf_occluded_grey)


# 17 recolour by depth in the stack
def tf_depth_colour(g):
    lay = _layers(g)
    if lay is None or len(lay) < 2: return None
    H, W = dims(g); return _draw(H, W, [(i + 1,) + l[1:] for i, l in enumerate(lay)])
rule("stack_depth_recolour", "The rectangles are recoloured by their place in the pile: the one on top becomes 1, the one under it 2, and so on down.", _gen_stack(2, 5), tf_depth_colour)


# 18 reverse the stacking order
def tf_reverse_stack(g):
    lay = _layers(g)
    if lay is None or len(lay) < 3: return None
    H, W = dims(g); return _draw(H, W, lay[::-1])
rule("stacking_order_reversed", "The pile of rectangles is turned over: the bottom one ends on top, the top one at the bottom, each kept in place.", _gen_stack(3, 5), tf_reverse_stack)


# 19 keep only the top rectangle
def tf_only_top(g):
    lay = _layers(g)
    if lay is None or len(lay) < 2: return None
    H, W = dims(g); return _draw(H, W, lay[:1])
rule("keep_only_top_rectangle", "Only the rectangle on top of the pile (the one fully visible) is kept; every other rectangle is erased.", _gen_stack(2, 5), tf_only_top)


# 20 keep only the bottom rectangle, completed
def tf_only_bottom(g):
    lay = _layers(g)
    if lay is None or len(lay) < 2: return None
    H, W = dims(g); return _draw(H, W, lay[-1:])
rule("keep_only_bottom_rectangle_completed", "Only the rectangle at the bottom of the pile is kept, drawn complete; the rectangles that covered it are erased.", _gen_stack(2, 5), tf_only_bottom)


# 21 how many rectangles are partly hidden
def tf_hidden_count_row(g):
    d = _by_colour(g); n = len(d); h = sum(not _full(cs) for cs in d.values())
    return [[5] * h + [0] * (n - h)] if 0 < h < n else None
rule("hidden_rectangle_count_row", "Output one row with a cell per rectangle: as many grey (5) cells from the left as there are partly hidden rectangles, the rest empty.", _mixed, tf_hidden_count_row)


# 22 shadows away from the light in a corner
def gi_light(rng):
    g = gi_rects_apart(rng, (5, 8), 1)
    if g is None: return None
    H, W = dims(g); corner = rng.choice([(0, 0), (0, W - 1), (H - 1, 0), (H - 1, W - 1)])
    r, c = corner
    if any(g[y][x] for y in range(max(0, r - 1), min(H, r + 2)) for x in range(max(0, c - 1), min(W, c + 2))): return None
    g[r][c] = 5; return g
def tf_light(g):
    H, W = dims(g); L = cells(g, lambda v: v == 5)
    if len(L) != 1: return None
    (lr, lc), = L; dr, dc = (1 if lr == 0 else -1), (1 if lc == 0 else -1); out = copy(g)
    for r, c in cells(g, lambda v: v not in (0, 5)):
        if 0 <= r + dr < H and 0 <= c + dc < W and g[r + dr][c + dc] == 0:
            out[r + dr][c + dc] = 8
    return out
rule("shadows_away_from_corner_light", "The grey cell in a corner is a light; every rectangle casts a one-cell colour-8 shadow diagonally away from that corner onto the background.", gi_light, tf_light)


# 23 top rectangle sent to the back
def tf_top_to_back(g):
    lay = _layers(g)
    if lay is None or len(lay) < 2: return None
    H, W = dims(g); return _draw(H, W, lay[1:] + lay[:1])
rule("top_rectangle_sent_to_back", "The rectangle on top is sent to the back of the pile: everything it covered is completed over it, and it shows only where nothing else lies.", _gen_stack(2, 5), tf_top_to_back)


# 24 overlap becomes a checkerboard of the two colours
def tf_overlap_checker(g):
    lay = _layers(g)
    if lay is None or len(lay) != 2: return None
    (tcol, a0, b0, a1, b1), (bcol, c0, d0, c1, d1) = lay
    r0, c0_, r1, c1_ = max(a0, c0), max(b0, d0), min(a1, c1), min(b1, d1)
    out = copy(g)
    for r in range(r0, r1 + 1):
        for c in range(c0_, c1_ + 1):
            out[r][c] = bcol if (r - r0 + c - c0_) % 2 == 0 else tcol
    return out if out != g else None
rule("overlap_becomes_checkerboard", "Where two rectangles overlap, the overlap becomes a checkerboard of their two colours, the lower colour at its top-left cell.", _gen_stack(2, 2), tf_overlap_checker)


# 25 top rectangle slides right off the overlap
def gi_slide(rng):
    st = _stack(rng, 2)
    return st[0] if st is not None and tf_slide(st[0]) is not None else None
def tf_slide(g):
    lay = _layers(g)
    if lay is None or len(lay) != 2: return None
    H, W = dims(g); (tcol, a0, b0, a1, b1), bot = lay
    d = bot[4] - b0 + 1
    if b1 + d >= W: return None
    return _draw(H, W, [(tcol, a0, b0 + d, a1, b1 + d), bot])
rule("top_rectangle_slides_right_clear", "The rectangle on top slides right until it just clears the rectangle beneath it, which is then seen whole.", gi_slide, tf_slide)


# 26 striped frame restored after a patch is removed
def gi_striped_patch(rng):
    H, W = _size(rng, 8, 20); F, a, b, P = colours(rng, 4)
    for _ in range(30):
        r0, c0, r1, c1 = _rand_rect(rng, H, W, 5)
        if r1 - r0 < 4: continue
        orig = blank(H, W); rect(orig, r0, c0, r1, c1, F, fill=False)
        for r in range(r0 + 1, r1): rect(orig, r, c0 + 1, r, c1 - 1, a if (r - r0) % 2 else b)
        pb = _overlapping_rect(rng, H, W, (r0, c0, r1, c1), 2)
        if pb is None: continue
        g = copy(orig); rect(g, *pb, P)
        if g != orig and tf_striped_patch(g) == orig: return g
    return None
def tf_striped_patch(g):
    d = _by_colour(g); P = [c for c in d if _full(d[c])]
    if len(P) != 1 or len(d) != 4: return None
    P = P[0]; rest = [rc for c in d if c != P for rc in d[c]]; r0, c0, r1, c1 = bbox(rest)
    F = [c for c in d if c != P and all(r in (r0, r1) or c_ in (c0, c1) for r, c_ in d[c])]
    if len(F) != 1: return None
    par = {}
    for r in range(r0 + 1, r1):
        for c in range(c0 + 1, c1):
            if g[r][c] not in (P, F[0]): par[(r - r0) % 2] = g[r][c]
    if len(par) != 2: return None
    out = copy(g); rect(out, r0, c0, r1, c1, F[0], fill=False)
    for r in range(r0 + 1, r1): rect(out, r, c0 + 1, r, c1 - 1, par[(r - r0) % 2])
    return out
rule("patch_removed_striped_frame_restored", "A solid patch lies over a frame filled with alternating row stripes; the patch is removed and the frame border and stripes are completed underneath.", gi_striped_patch, tf_striped_patch)


# 27 stacking order as a colour column
def tf_order_column(g):
    lay = _layers(g)
    if lay is None or len(lay) < 2: return None
    return [[l[0]] for l in lay]
rule("stacking_order_colour_column", "Output one column listing the rectangles' colours from the one on top of the pile down to the one at the bottom.", _gen_stack(2, 5), tf_order_column)


# 28 unstack into a row of complete rectangles
def tf_unstack_row(g):
    lay = _layers(g)
    if lay is None or len(lay) < 2: return None
    ws = [l[4] - l[2] + 1 for l in lay]; hs = [l[3] - l[1] + 1 for l in lay]
    W = sum(ws) + len(ws) - 1
    if W > 30: return None
    out = blank(max(hs), W); c = 0
    for (col, *_), h, w in zip(lay, hs, ws):
        rect(out, 0, c, h - 1, c + w - 1, col); c += w + 1
    return out
rule("stack_unpacked_to_row", "The piled rectangles are separated and laid side by side, each complete, top-aligned and one column apart, the top of the pile first.", _gen_stack(2, 4), tf_unstack_row)


# 29 each rectangle takes the colour of the one beneath it
def tf_colour_from_below(g):
    lay = _layers(g)
    if lay is None or len(lay) < 2: return None
    H, W = dims(g); new = [(lay[i + 1][0],) + lay[i][1:] for i in range(len(lay) - 1)] + [lay[-1]]
    return _draw(H, W, new)
rule("rectangle_takes_colour_beneath", "Each rectangle takes the colour of the rectangle directly beneath it in the pile; the bottom one keeps its colour.", _gen_stack(2, 5), tf_colour_from_below)


# 30 cover parity
def tf_cover_parity(g):
    lay = _layers(g)
    if lay is None or len(lay) < 2: return None
    H, W = dims(g); cov = _cover(H, W, lay)
    return [[0 if v == 0 else (1 if v % 2 else 2) for v in row] for row in cov]
rule("cover_parity_one_two", "Cells under an odd number of rectangles become 1 and cells under an even number become 2; the rectangles' extents are read from their visible edges.", _gen_stack(2, 5, exclude=(1, 2)), tf_cover_parity)


# 31 exclusive-or of the rectangles
def tf_xor(g):
    lay = _layers(g)
    if lay is None or len(lay) < 2: return None
    H, W = dims(g); cov = _cover(H, W, lay); out = blank(H, W)
    for col, r0, c0, r1, c1 in lay:
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if cov[r][c] == 1: out[r][c] = col
    return out
rule("rectangles_exclusive_or", "Every cell covered by exactly one rectangle keeps that rectangle's colour; cells where rectangles overlap become empty.", _gen_stack(2, 4), tf_xor)


# 32 recolour each object by its number of layers
def tf_layer_count(g):
    d = _depth(g); out = copy(g)
    for o in objects(g, 0, conn8=False):
        m = min(9, max(d[r][c] for r, c in o))
        for r, c in o: out[r][c] = m
    return out if out != g else None
rule("objects_recolour_by_layer_count", "Each object is recoloured with the number of layers it has, counting from the outer skin to the deepest core.", _blob_scene, tf_layer_count)


# 33 keep only each object's core
def tf_core(g):
    d = _depth(g); out = blank(*dims(g))
    for o in objects(g, 0, conn8=False):
        m = max(d[r][c] for r, c in o)
        for r, c in o:
            if d[r][c] == m: out[r][c] = g[r][c]
    return out if out != g else None
rule("objects_keep_only_core", "Each object is reduced to its core: only its deepest layer of cells survives, the rest is erased.", _blob_scene, tf_core)


# 34 top rectangle hollowed
def gi_hollow_top(rng):
    st = _stack(rng, rng.randint(2, 4))
    if st is None: return None
    g, lay = st; _, r0, c0, r1, c1 = lay[0]
    return g if r1 - r0 >= 2 and c1 - c0 >= 2 else None
def tf_hollow_top(g):
    lay = _layers(g)
    if lay is None or len(lay) < 2: return None
    H, W = dims(g); out = _draw(H, W, lay[1:]); col, r0, c0, r1, c1 = lay[0]
    return rect(out, r0, c0, r1, c1, col, fill=False)
rule("top_rectangle_hollowed_shows_below", "The rectangle on top becomes a hollow frame; through its interior the rectangles beneath are completed and the background shows.", gi_hollow_top, tf_hollow_top)


# 35 objects replaced by their shadows
def gi_shapes(rng):
    H, W = _size(rng, 7, 20); g = blank(H, W); k = rng.randint(1, 5)
    shapes = [random_shape(rng, rng.randint(2, 9)) for _ in range(k)]
    cols = [rng.choice([c for c in COLOURS if c != 5]) for _ in range(k)]
    return g if place_shapes(rng, g, shapes, cols, margin=1) is not None else None
def tf_only_shadows(g):
    H, W = dims(g); out = blank(H, W)
    for r, c in cells(g, lambda v: v != 0):
        if r + 1 < H and c + 1 < W: out[r + 1][c + 1] = 5
    return out if any(v for row in out for v in row) else None
rule("objects_replaced_by_offset_shadows", "Every object vanishes and only its grey (5) shadow remains, the same shape shifted one cell down and one cell right.", gi_shapes, tf_only_shadows)


# 36 marked rectangle brought to front
def gi_marked(rng):
    st = _stack(rng, rng.randint(2, 4), (5, 9))
    if st is None: return None
    g, lay = st; i = rng.randint(1, len(lay) - 1); col = lay[i][0]
    r, c = rng.choice(cells(g, lambda v: v == col)); g[r][c] = 9
    return g if _layers(g, wild=(9,)) == lay else None
def tf_marked_front(g):
    lay = _layers(g, wild=(9,)); M = cells(g, lambda v: v == 9)
    if lay is None or len(M) != 1: return None
    (mr, mc), = M; H, W = dims(g)
    i = next((i for i, (_, r0, c0, r1, c1) in enumerate(lay) if r0 <= mr <= r1 and c0 <= mc <= c1), None)
    if i is None or i == 0: return None
    return _draw(H, W, [lay[i]] + lay[:i] + lay[i + 1:])
rule("marked_rectangle_to_front", "The rectangle carrying the colour-9 dot is brought to the front and drawn complete over the others; the dot disappears.", gi_marked, tf_marked_front)


# 37 the two rectangles exchange colours
def tf_swap_colours(g):
    lay = _layers(g)
    if lay is None or len(lay) != 2: return None
    H, W = dims(g); (a, *ra), (b, *rb) = lay
    return _draw(H, W, [(b,) + tuple(ra), (a,) + tuple(rb)])
rule("overlapping_pair_swap_colours", "Two overlapping rectangles exchange colours while keeping their positions and which one is on top.", _gen_stack(2, 2), tf_swap_colours)


# 38 output what lies under the patch
def gi_under_patch(rng):
    t = _tiled(rng)
    if t is None: return None
    g, orig, (r0, c0, r1, c1) = t; want = crop(orig, r0, c0, r1, c1)
    return g if len({v for row in want for v in row}) >= 2 and tf_under_patch(g) == want else None
def tf_under_patch(g):
    full = _restore(g)
    if full is None: return None
    return crop(full, *bbox(cells(g, lambda v: v == 9)))
rule("under_patch_tile_contents", "A colour-9 patch covers part of a repeating tiled pattern; output just the patch's area as the pattern would look underneath it.", gi_under_patch, tf_under_patch)


# 39 grey bars in front of rectangles removed and the rectangles restored
def gi_bars(rng):
    H, W = _size(rng, 8, 20); g = blank(H, W); p = rng.randint(3, 5); off = rng.randrange(p)
    k = rng.randint(1, min(6, W // 3)); cols = colours(rng, k, exclude=(0, 5)); n = 0
    for _ in range(60):
        r0, c0, r1, c1 = _rand_rect(rng, H, W, 2, max(2, min(H, W) // 3))
        if all(g[r][c] == 0 for r in range(max(0, r0 - 1), min(H, r1 + 2)) for c in range(max(0, c0 - 1), min(W, c1 + 2))):
            rect(g, r0, c0, r1, c1, cols[n]); n += 1
            if n >= k: break
    if not n: return None
    orig = copy(g)
    for c in range(off, W, p):
        for r in range(H): g[r][c] = 5
    return g if g != orig and tf_bars(g) == orig else None
def tf_bars(g):
    H, W = dims(g); out = blank(H, W); d = _by_colour(g, skip=(0, 5))
    for col, cs in d.items(): rect(out, *bbox(cs), col)
    return out
rule("grey_bars_removed_rectangles_restored", "Full-height grey bars stand in front of solid rectangles; the bars are removed and each rectangle is filled back in to its full extent.", gi_bars, tf_bars)


# 40 nested rings: colour order reversed
def gi_nested(rng):
    H, W = _size(rng, 8, 20); g = blank(H, W); n = 0
    for _ in range(40):
        k = rng.randint(2, 4); th = [rng.randint(1, 2) for _ in range(k - 1)]; s = 2 * sum(th)
        h, w = rng.randint(s + 1, s + 4), rng.randint(s + 1, s + 4)
        if h > H or w > W: continue
        r0, c0 = rng.randint(0, H - h), rng.randint(0, W - w); r1, c1 = r0 + h - 1, c0 + w - 1
        if not all(g[r][c] == 0 for r in range(max(0, r0 - 1), min(H, r1 + 2)) for c in range(max(0, c0 - 1), min(W, c1 + 2))): continue
        cols = colours(rng, k); off = 0
        for i in range(k):
            rect(g, r0 + off, c0 + off, r1 - off, c1 - off, cols[i]); off += th[i] if i < k - 1 else 0
        n += 1
        if n >= rng.randint(1, 3): break
    return g if n else None
def tf_nested(g):
    out = copy(g)
    for b in _blobs(g):
        d = {}
        for r, c in b: d.setdefault(g[r][c], []).append((r, c))
        order = sorted(d, key=lambda col: -(lambda bb: (bb[2] - bb[0] + 1) * (bb[3] - bb[1] + 1))(bbox(d[col])))
        m = dict(zip(order, order[::-1]))
        for r, c in b: out[r][c] = m[g[r][c]]
    return out
rule("nested_rings_colours_reversed", "Each object is a set of nested rectangular rings; the ring colours are reversed from outside in, the outer ring taking the core's colour and the core taking the outer's.", gi_nested, tf_nested)
