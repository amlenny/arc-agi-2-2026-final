# b057_stamping.py -- STAMPING WITH PER-MARKER TRANSFORMS. A small template shape is drawn once (in a
# fixed template colour, bbox top-left pinned near the grid's own top-left corner) and several single-cell
# markers sit elsewhere; transform reads the template's cell offsets and, for every marker (processed in
# reading order: top-to-bottom, then left-to-right), stamps a transformed copy of the template with the
# shape's own (0,0) offset cell placed on the marker, unless a rule's description says otherwise.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

TCOL = 7   # default template colour for the single-template rules


# ---------- shared helpers (local to this file) ----------
def _rot_shape(shape, k):
    pts = shape
    for _ in range(k % 4):
        pts = [(c, -r) for r, c in pts]
    r0 = min(r for r, _ in pts); c0 = min(c for _, c in pts)
    return sorted((r - r0, c - c0) for r, c in pts)


def _mirror_h(shape):
    w = max(c for _, c in shape)
    return sorted((r, w - c) for r, c in shape)


def _mirror_v(shape):
    h = max(r for r, _ in shape)
    return sorted((h - r, c) for r, c in shape)


def _transpose_shape(shape):
    return sorted((c, r) for r, c in shape)


def _scale_shape(shape, k):
    out = set()
    for r, c in shape:
        for dr in range(k):
            for dc in range(k):
                out.add((r * k + dr, c * k + dc))
    return sorted(out)


def _bbox_shape(shape):
    return max(r for r, _ in shape) + 1, max(c for _, c in shape) + 1


def _stamp(g, shape, colour, r0, c0, wall=None, skip_occupied=False):
    H, W = dims(g)
    for r, c in shape:
        rr, cc = r0 + r, c0 + c
        if not (0 <= rr < H and 0 <= cc < W):
            continue
        if wall is not None and g[rr][cc] == wall:
            continue
        if skip_occupied and g[rr][cc] != 0:
            continue
        g[rr][cc] = colour


def _template(g, tcol=TCOL):
    pts = cells(g, lambda v: v == tcol)
    if not pts:
        return None
    r0 = min(r for r, _ in pts); c0 = min(c for _, c in pts)
    return sorted((r - r0, c - c0) for r, c in pts)


def _markers(g, exclude=(0, TCOL)):
    h, w = dims(g)
    return sorted((r, c, g[r][c]) for r in range(h) for c in range(w) if g[r][c] not in exclude)


def _scene(rng, marker_colours, tcol=TCOL, k=(2, 4), tmpl_n=(3, 6), lo=10, hi=28, margin=2):
    h, w = size(rng, lo, hi)
    g = blank(h, w)
    shape = random_shape(rng, rng.randint(*tmpl_n))
    th, tw = _bbox_shape(shape)
    if th + margin + 2 >= h or tw + margin + 2 >= w:
        return None
    for r, c in shape:
        g[r][c] = tcol
    kk = rng.randint(*k)
    cand = [(r, c) for r in range(h) for c in range(w) if not (r < th + margin and c < tw + margin)]
    rng.shuffle(cand)
    placed = []
    for r, c in cand:
        if len(placed) >= kk:
            break
        if any(abs(r - pr) <= 1 and abs(c - pc) <= 1 for pr, pc in placed):
            continue
        placed.append((r, c))
    if len(placed) < k[0]:
        return None
    for r, c in placed:
        g[r][c] = rng.choice(marker_colours)
    return g


# ===================================================================================================
# 1. rotate clockwise by marker digit
def gi1(rng):
    return _scene(rng, [1, 2, 3, 4], k=(2, 4))
def tf1(g):
    shape = _template(g)
    if shape is None: return None
    out = copy(g)
    for r, c, col in _markers(g):
        _stamp(out, _rot_shape(shape, col - 1), TCOL, r, c)
    return out
rule("stamp_rotate_cw_by_marker_digit",
     "The template (drawn once in its own colour with its own top-left cell near the grid's top-left) is "
     "stamped, top-left cell on the marker, at every marker in the template colour, rotated clockwise by "
     "(marker colour minus one) quarter turns: colour 1 unrotated, 2 a quarter turn, 3 a half turn, 4 three "
     "quarter turns.", gi1, tf1, digits=True)


# 2. rotate counter-clockwise by marker digit (opposite direction, distinct mapping)
def gi2(rng):
    return _scene(rng, [1, 2, 3, 4], k=(2, 4))
def tf2(g):
    shape = _template(g)
    if shape is None: return None
    out = copy(g)
    for r, c, col in _markers(g):
        _stamp(out, _rot_shape(shape, (4 - (col - 1)) % 4), TCOL, r, c)
    return out
rule("stamp_rotate_ccw_by_marker_digit",
     "The template is stamped at every marker, top-left cell on the marker, in the template colour, rotated "
     "counter-clockwise by (marker colour minus one) quarter turns: colour 1 unrotated, 2 a quarter turn, 3 a "
     "half turn, 4 three quarter turns counter-clockwise.", gi2, tf2, digits=True)


# 3. mirrored horizontally at colour 2, plain at colour 3
def gi3(rng):
    return _scene(rng, [2, 3], k=(2, 4))
def tf3(g):
    shape = _template(g)
    if shape is None: return None
    out = copy(g)
    for r, c, col in _markers(g):
        sh = _mirror_h(shape) if col == 2 else shape
        _stamp(out, sh, TCOL, r, c)
    return out
rule("stamp_mirror_h_colour2_plain_colour3",
     "The template is stamped at every marker, top-left cell on the marker: markers of colour 2 get the "
     "template mirrored left-to-right, markers of colour 3 get it unchanged.", gi3, tf3)


# 4. mirrored vertically at colour 4, plain at colour 6
def gi4(rng):
    return _scene(rng, [4, 6], k=(2, 4))
def tf4(g):
    shape = _template(g)
    if shape is None: return None
    out = copy(g)
    for r, c, col in _markers(g):
        sh = _mirror_v(shape) if col == 4 else shape
        _stamp(out, sh, TCOL, r, c)
    return out
rule("stamp_mirror_v_colour4_plain_colour6",
     "The template is stamped at every marker, top-left cell on the marker: markers of colour 4 get the "
     "template flipped top-to-bottom, markers of colour 6 get it unchanged.", gi4, tf4)


# 5. scaled 2x at grey markers, plain elsewhere
def gi5(rng):
    return _scene(rng, [5, 2], k=(2, 4), tmpl_n=(3, 5))
def tf5(g):
    shape = _template(g)
    if shape is None: return None
    out = copy(g)
    for r, c, col in _markers(g):
        sh = _scale_shape(shape, 2) if col == 5 else shape
        _stamp(out, sh, TCOL, r, c)
    return out
rule("stamp_scaled_2x_at_grey_markers",
     "The template is stamped at every marker, top-left cell on the marker: grey (colour 5) markers get it "
     "stamped at twice its size (every cell becomes a 2x2 block), markers of colour 2 get it stamped at its "
     "normal size.", gi5, tf5)


# 6. scaled 3x at colour 8, plain elsewhere
def gi6(rng):
    return _scene(rng, [8, 3], k=(2, 3), tmpl_n=(2, 4))
def tf6(g):
    shape = _template(g)
    if shape is None: return None
    out = copy(g)
    for r, c, col in _markers(g):
        sh = _scale_shape(shape, 3) if col == 8 else shape
        _stamp(out, sh, TCOL, r, c)
    return out
rule("stamp_scaled_3x_at_colour8_plain_colour3",
     "The template is stamped at every marker, top-left cell on the marker: markers of colour 8 get it "
     "stamped at three times its size (every cell becomes a 3x3 block), markers of colour 3 get it stamped "
     "at its normal size.", gi6, tf6)


# 7. stamped in the marker's own colour
def gi7(rng):
    return _scene(rng, [1, 2, 3, 4, 6, 8, 9], k=(2, 5))
def tf7(g):
    shape = _template(g)
    if shape is None: return None
    out = copy(g)
    for r, c, col in _markers(g):
        _stamp(out, shape, col, r, c)
    return out
rule("stamp_in_marker_own_colour",
     "The template is stamped at every marker, top-left cell on the marker, recoloured to that marker's own "
     "colour rather than the template's drawn colour.", gi7, tf7)


# 8. stamped in marker colour, rotated by that same colour's digit value
def gi8(rng):
    return _scene(rng, [1, 2, 3, 4], k=(2, 4))
def tf8(g):
    shape = _template(g)
    if shape is None: return None
    out = copy(g)
    for r, c, col in _markers(g):
        _stamp(out, _rot_shape(shape, col - 1), col, r, c)
    return out
rule("stamp_in_marker_colour_rotated_by_digit",
     "The template is stamped at every marker, top-left cell on the marker, recoloured to the marker's own "
     "colour and rotated clockwise by (marker colour minus one) quarter turns.", gi8, tf8, digits=True)


# 9. stamped only at markers inside a drawn frame
def gi9(rng):
    h, w = size(rng, 12, 28); g = blank(h, w)
    shape = random_shape(rng, rng.randint(3, 5))
    th, tw = _bbox_shape(shape)
    if th + 4 >= h or tw + 4 >= w: return None
    for r, c in shape: g[r][c] = TCOL
    r0, c0 = rng.randint(th + 2, h - 6), rng.randint(tw + 2, w - 6)
    r1, c1 = rng.randint(r0 + 3, min(h - 2, r0 + 8)), rng.randint(c0 + 3, min(w - 2, c0 + 8))
    rect(g, r0, c0, r1, c1, 5, fill=False)
    inside = [(r, c) for r in range(r0 + 1, r1) for c in range(c0 + 1, c1)]
    outside = [(r, c) for r in range(h) for c in range(w)
               if g[r][c] == 0 and not (r0 <= r <= r1 and c0 <= c <= c1) and not (r < th + 2 and c < tw + 2)]
    rng.shuffle(inside); rng.shuffle(outside)
    n_in, n_out = rng.randint(1, 3), rng.randint(1, 3)
    if len(inside) < n_in or len(outside) < n_out: return None
    for r, c in inside[:n_in]: g[r][c] = 2
    for r, c in outside[:n_out]: g[r][c] = 2
    return g
def tf9(g):
    shape = _template(g)
    if shape is None: return None
    frame = cells(g, lambda v: v == 5)
    if not frame: return None
    r0, c0, r1, c1 = bbox(frame)
    out = copy(g)
    for r, c, col in _markers(g, exclude=(0, TCOL, 5)):
        if r0 < r < r1 and c0 < c < c1:
            _stamp(out, shape, TCOL, r, c)
    return out
rule("stamp_only_markers_inside_frame",
     "A hollow grey rectangle is drawn on the grid; only the markers strictly inside it (not on its border) "
     "get the template stamped on them, top-left cell on the marker; markers outside the frame are left "
     "untouched and get no stamp.", gi9, tf9)


# 10. stamped only at markers outside a drawn frame
def gi10(rng):
    return gi9(rng)
def tf10(g):
    shape = _template(g)
    if shape is None: return None
    frame = cells(g, lambda v: v == 5)
    if not frame: return None
    r0, c0, r1, c1 = bbox(frame)
    out = copy(g)
    for r, c, col in _markers(g, exclude=(0, TCOL, 5)):
        if not (r0 < r < r1 and c0 < c < c1):
            _stamp(out, shape, TCOL, r, c)
    return out
rule("stamp_only_markers_outside_frame",
     "A hollow grey rectangle is drawn on the grid; only the markers strictly outside it get the template "
     "stamped on them, top-left cell on the marker; markers inside the frame are left untouched and get no "
     "stamp.", gi10, tf10)


# 11. centred at colour 2, anchored top-left at colour 3
def gi11(rng):
    return _scene(rng, [2, 3], k=(2, 4), tmpl_n=(3, 6))
def tf11(g):
    shape = _template(g)
    if shape is None: return None
    th, tw = _bbox_shape(shape)
    out = copy(g)
    for r, c, col in _markers(g):
        if col == 2:
            _stamp(out, shape, TCOL, r - th // 2, c - tw // 2)
        else:
            _stamp(out, shape, TCOL, r, c)
    return out
rule("stamp_centred_colour2_topleft_colour3",
     "The template is stamped at every marker in the template colour: at colour-2 markers its bounding box "
     "is centred on the marker, at colour-3 markers its top-left cell is placed on the marker.", gi11, tf11)


# 12. two templates, chosen by marker colour
def gi12(rng):
    h, w = size(rng, 14, 28); g = blank(h, w)
    sh_a = random_shape(rng, rng.randint(3, 5)); sh_b = random_shape(rng, rng.randint(3, 5))
    ah, aw = _bbox_shape(sh_a); bh, bw = _bbox_shape(sh_b)
    if ah + 3 >= h or aw + bw + 6 >= w or bh + 3 >= h: return None
    for r, c in sh_a: g[r][c] = TCOL
    for r, c in sh_b: g[r][c] = 9 if (r, c) not in sh_a else g[r][c]
    off = aw + 3
    for r, c in sh_b: g[r][c + off] = 9
    k = rng.randint(2, 4)
    cand = [(r, c) for r in range(h) for c in range(w) if r >= max(ah, bh) + 2]
    rng.shuffle(cand)
    placed = []
    for r, c in cand:
        if len(placed) >= k: break
        if any(abs(r - pr) <= 1 and abs(c - pc) <= 1 for pr, pc in placed): continue
        placed.append((r, c))
    if len(placed) < 2: return None
    for r, c in placed: g[r][c] = rng.choice([2, 3])
    return g
def tf12(g):
    sh_a = _template(g, TCOL)
    pts9 = cells(g, lambda v: v == 9)
    if sh_a is None or not pts9: return None
    c_mid = min(c for _, c in pts9) + (max(c for _, c in pts9) - min(c for _, c in pts9)) // 2
    left = [(r, c) for r, c in pts9 if c <= c_mid]
    r0 = min(r for r, _ in left); c0 = min(c for r, c in left)
    sh_b = sorted((r - r0, c - c0) for r, c in left)
    out = copy(g)
    for r, c, col in _markers(g, exclude=(0, TCOL, 9)):
        shape = sh_a if col == 2 else sh_b
        _stamp(out, shape, TCOL if col == 2 else 9, r, c)
    return out
rule("stamp_two_templates_by_colour",
     "Two templates are drawn, template A in the template colour and template B (further right) in colour "
     "9; colour-2 markers get template A stamped in the template colour, top-left cell on the marker, and "
     "colour-3 markers get template B stamped in colour 9, top-left cell on the marker.", gi12, tf12)


# 13. clipped by a grey wall: stamp cells landing on the wall are skipped, the wall stays visible
def gi13(rng):
    h, w = size(rng, 14, 28); g = blank(h, w)
    shape = random_shape(rng, rng.randint(3, 6))
    th, tw = _bbox_shape(shape)
    if th + 4 >= h or tw + 4 >= w: return None
    for r, c in shape: g[r][c] = TCOL
    wc = rng.randint(tw + 3, w - 3)
    for r in range(h): g[r][wc] = 5
    k = rng.randint(2, 3)
    cand = [(r, wc - rng.randint(1, min(tw, wc - 1))) for r in range(th + 2, h - 2)]
    rng.shuffle(cand)
    placed = []
    for r, c in cand:
        if c < tw + 1 or c >= wc: continue
        if len(placed) >= k: break
        if any(abs(r - pr) <= 1 for pr, pc in placed): continue
        placed.append((r, c))
    if len(placed) < 2: return None
    for r, c in placed: g[r][c] = 2
    return g
def tf13(g):
    shape = _template(g)
    if shape is None: return None
    out = copy(g)
    for r, c, col in _markers(g, exclude=(0, TCOL, 5)):
        _stamp(out, shape, TCOL, r, c, wall=5)
    return out
rule("stamp_clipped_by_grey_wall",
     "A vertical grey wall runs down the grid; the template is stamped at every marker, top-left cell on "
     "the marker, in the template colour, but any stamp cell that would land on the grey wall is skipped so "
     "the wall stays visible underneath.", gi13, tf13)


# 14. clipped by any already-occupied (non-background) cell
def gi14(rng):
    h, w = size(rng, 14, 28); g = blank(h, w)
    shape = random_shape(rng, rng.randint(3, 6))
    th, tw = _bbox_shape(shape)
    if th + 4 >= h or tw + 4 >= w: return None
    for r, c in shape: g[r][c] = TCOL
    n_block = rng.randint(1, 3)
    for _ in range(n_block):
        rr, cc = rng.randint(th + 2, h - 3), rng.randint(tw + 2, w - 3)
        g[rr][cc] = 8; g[rr][cc + 1] = 8
    k = rng.randint(2, 4)
    cand = [(r, c) for r in range(th + 2, h - th - 2) for c in range(tw + 2, w - tw - 2) if g[r][c] == 0]
    rng.shuffle(cand)
    placed = []
    for r, c in cand:
        if len(placed) >= k: break
        if any(abs(r - pr) <= 1 and abs(c - pc) <= 1 for pr, pc in placed): continue
        placed.append((r, c))
    if len(placed) < 2: return None
    for r, c in placed: g[r][c] = 3
    return g
def tf14(g):
    shape = _template(g)
    if shape is None: return None
    out = copy(g)
    for r, c, col in _markers(g, exclude=(0, TCOL)):
        _stamp(out, shape, TCOL, r, c, skip_occupied=True)
    return out
rule("stamp_clipped_by_occupied_cells",
     "The template is stamped at every marker, top-left cell on the marker, in the template colour, but any "
     "stamp cell that would overwrite a cell that is already non-background (a blocker or another marker) "
     "is skipped, leaving that cell as it was.", gi14, tf14)


# 15. overlapping stamps merged, later marker in reading order on top
def gi15(rng):
    return _scene(rng, [2, 3, 4], k=(3, 5), tmpl_n=(4, 7), margin=0)
def tf15(g):
    shape = _template(g)
    if shape is None: return None
    out = copy(g)
    for r, c, col in _markers(g):
        _stamp(out, shape, col, r, c)
    return out
# stamp_overlap_reading_order_wins dropped 2026-10-12 (review 2: behavioural duplicate of stamp_in_marker_own_colour)
# 16. overlapping stamps merged, earlier marker in reading order wins
def gi16(rng):
    return _scene(rng, [2, 3, 4], k=(3, 5), tmpl_n=(4, 7), margin=0)
def tf16(g):
    shape = _template(g)
    if shape is None: return None
    out = copy(g)
    for r, c, col in sorted(_markers(g), reverse=True):
        _stamp(out, shape, col, r, c)
    return out
rule("stamp_overlap_first_in_order_wins",
     "The template is stamped at every marker, top-left cell on the marker, recoloured to that marker's own "
     "colour, processing markers in reverse reading order (bottom row first, right to left within a row) so "
     "that where two stamps overlap, the one from the earlier marker in normal reading order ends up on "
     "top.", gi16, tf16)


# 17. stamped at every marker then the marker cells are removed (anchor not at the marked cell)
def gi17(rng):
    return _scene(rng, [2, 3, 4, 6], k=(2, 4), tmpl_n=(3, 6))
def tf17(g):
    shape = _template(g)
    if shape is None: return None
    th, tw = _bbox_shape(shape)
    out = copy(g)
    for r, c, col in _markers(g):
        out[r][c] = 0
        _stamp(out, shape, TCOL, r - th // 2, c - tw // 2)
    return out
rule("stamp_then_erase_markers",
     "The template is stamped, bounding box centred on each marker, in the template colour; every original "
     "marker cell is then cleared to background first so no marker colour survives once the stamping is "
     "done.", gi17, tf17)


# 18. stamp count limited to the first k markers in reading order, k = corner digit
def gi18(rng):
    h, w = size(rng, 12, 28); g = blank(h, w)
    shape = random_shape(rng, rng.randint(3, 5))
    th, tw = _bbox_shape(shape)
    if th + 4 >= h or tw + 4 >= w: return None
    for r, c in shape: g[r][c] = TCOL
    k = rng.randint(1, 4)
    g[0][w - 1] = k
    cand = [(r, c) for r in range(h) for c in range(w)
            if not (r < th + 2 and c < tw + 2) and (r, c) != (0, w - 1)]
    rng.shuffle(cand)
    n = rng.randint(k + 1, k + 3)
    placed = []
    for r, c in cand:
        if len(placed) >= n: break
        if any(abs(r - pr) <= 1 and abs(c - pc) <= 1 for pr, pc in placed): continue
        placed.append((r, c))
    if len(placed) < k + 1: return None
    for r, c in placed: g[r][c] = 2
    return g
def tf18(g):
    shape = _template(g)
    if shape is None: return None
    h, w = dims(g)
    k = g[0][w - 1]
    out = copy(g)
    out[0][w - 1] = 0
    markers = _markers(g, exclude=(0, TCOL, g[0][w - 1]) if False else (0, TCOL))
    markers = [m for m in markers if m[:2] != (0, w - 1)]
    for r, c, col in markers[:k]:
        _stamp(out, shape, TCOL, r, c)
    for r, c, col in markers[k:]:
        out[r][c] = 0
    return out
rule("stamp_first_k_markers_corner_digit",
     "The top-right corner cell holds a digit k; markers are taken in reading order (top row first, left to "
     "right); only the first k of them get the template stamped on them, top-left cell on the marker, in "
     "the template colour, and the corner digit is cleared; every later marker is erased to background "
     "with no stamp.", gi18, tf18, digits=True)


# 19. stamp count limited to the last k markers in reading order, k = corner digit
def gi19(rng):
    return gi18(rng)
def tf19(g):
    shape = _template(g)
    if shape is None: return None
    h, w = dims(g)
    k = g[0][w - 1]
    out = copy(g)
    out[0][w - 1] = 0
    markers = [m for m in _markers(g, exclude=(0, TCOL)) if m[:2] != (0, w - 1)]
    n = len(markers)
    for i, (r, c, col) in enumerate(markers):
        if i >= n - k:
            _stamp(out, shape, TCOL, r, c)
        else:
            out[r][c] = 0
    return out
rule("stamp_last_k_markers_corner_digit",
     "The top-right corner cell holds a digit k; markers are taken in reading order (top row first, left to "
     "right); only the last k of them get the template stamped on them, top-left cell on the marker, in the "
     "template colour, and the corner digit is cleared; every earlier marker is erased to background with "
     "no stamp.", gi19, tf19, digits=True)


# 20. anchored at the template's own marked cell (a special colour inside the template, not its bbox corner)
def gi20(rng):
    h, w = size(rng, 12, 28); g = blank(h, w)
    shape = random_shape(rng, rng.randint(4, 7))
    th, tw = _bbox_shape(shape)
    if th + 4 >= h or tw + 4 >= w: return None
    mark = rng.choice(shape[1:]) if len(shape) > 1 else shape[0]
    for r, c in shape: g[r][c] = 9 if (r, c) == mark else TCOL
    k = rng.randint(2, 4)
    cand = [(r, c) for r in range(h) for c in range(w) if not (r < th + 2 and c < tw + 2)]
    rng.shuffle(cand)
    placed = []
    for r, c in cand:
        if len(placed) >= k: break
        if any(abs(r - pr) <= 1 and abs(c - pc) <= 1 for pr, pc in placed): continue
        placed.append((r, c))
    if len(placed) < 2: return None
    for r, c in placed: g[r][c] = 2
    return g
def tf20(g):
    pts = cells(g, lambda v: v in (TCOL, 9))
    if not pts: return None
    r0 = min(r for r, _ in pts); c0 = min(c for _, c in pts)
    mark = next((r - r0, c - c0) for r, c in pts if g[r][c] == 9)
    shape = sorted((r - r0, c - c0) for r, c in pts)
    out = copy(g)
    for r, c, col in _markers(g, exclude=(0, TCOL, 9)):
        _stamp(out, shape, TCOL, r - mark[0], c - mark[1])
    return out
rule("stamp_anchored_at_templates_marked_cell",
     "One cell of the template is drawn in colour 9 instead of the template colour, marking its anchor; the "
     "template is stamped at every marker so that this marked cell (recoloured back to the template colour) "
     "lands exactly on the marker, not the shape's top-left corner.", gi20, tf20)


# 21. dihedral code by digit: 1=identity, 2=quarter turn, 3=mirror, 4=quarter turn then mirror
def gi21(rng):
    return _scene(rng, [1, 2, 3, 4], k=(2, 4))
def tf21(g):
    shape = _template(g)
    if shape is None: return None
    out = copy(g)
    for r, c, col in _markers(g):
        sh = shape
        if col == 2: sh = _rot_shape(shape, 1)
        elif col == 3: sh = _mirror_h(shape)
        elif col == 4: sh = _mirror_h(_rot_shape(shape, 1))
        _stamp(out, sh, TCOL, r, c)
    return out
rule("stamp_dihedral_code_by_marker_digit",
     "The template is stamped at every marker, top-left cell on the marker, in the template colour: colour "
     "1 unchanged, colour 2 rotated a quarter turn clockwise, colour 3 mirrored left-to-right, colour 4 "
     "rotated a quarter turn clockwise and then mirrored left-to-right.", gi21, tf21, digits=True)


# 22. scaled by the marker's own digit value (1, 2 or 3)
def gi22(rng):
    return _scene(rng, [1, 2, 3], k=(2, 3), tmpl_n=(2, 4))
def tf22(g):
    shape = _template(g)
    if shape is None: return None
    out = copy(g)
    for r, c, col in _markers(g):
        _stamp(out, _scale_shape(shape, col), TCOL, r, c)
    return out
rule("stamp_scaled_by_marker_digit_value",
     "The template is stamped at every marker, top-left cell on the marker, in the template colour, scaled "
     "up by the marker's own digit value: colour 1 stamps it at normal size, colour 2 at double size, "
     "colour 3 at triple size.", gi22, tf22, digits=True)


# 23. repeated horizontally, digit times, starting at the marker
def gi23(rng):
    return _scene(rng, [1, 2, 3], k=(2, 3), tmpl_n=(2, 3), lo=12, hi=28)
def tf23(g):
    shape = _template(g)
    if shape is None: return None
    tw = _bbox_shape(shape)[1]
    out = copy(g)
    for r, c, col in _markers(g):
        for i in range(col):
            _stamp(out, shape, TCOL, r, c + i * (tw + 1))
    return out
rule("stamp_repeated_horizontally_by_digit",
     "The template is stamped at every marker, top-left cell on the marker, in the template colour, then "
     "repeated to the right with one blank column of gap between copies, for a total of (marker colour) "
     "copies.", gi23, tf23, digits=True)


# 24. diagonal mirror (transpose) at colour 2, plain at colour 3
def gi24(rng):
    return _scene(rng, [2, 3], k=(2, 4))
def tf24(g):
    shape = _template(g)
    if shape is None: return None
    out = copy(g)
    for r, c, col in _markers(g):
        sh = _transpose_shape(shape) if col == 2 else shape
        _stamp(out, sh, TCOL, r, c)
    return out
rule("stamp_transpose_colour2_plain_colour3",
     "The template is stamped at every marker, top-left cell on the marker, in the template colour: "
     "colour-2 markers get it flipped across its own top-left-to-bottom-right diagonal (rows and columns "
     "swapped), colour-3 markers get it unchanged.", gi24, tf24)


# 25. swap two fixed colours within a two-colour template at colour 2, plain at colour 3
def gi25(rng):
    h, w = size(rng, 12, 28); g = blank(h, w)
    base = random_shape(rng, rng.randint(4, 7))
    th, tw = _bbox_shape(base)
    if th + 4 >= h or tw + 4 >= w: return None
    half = base[: len(base) // 2] or base[:1]
    for r, c in base: g[r][c] = 1 if (r, c) in half else 3
    k = rng.randint(2, 4)
    cand = [(r, c) for r in range(h) for c in range(w) if not (r < th + 2 and c < tw + 2)]
    rng.shuffle(cand)
    placed = []
    for r, c in cand:
        if len(placed) >= k: break
        if any(abs(r - pr) <= 1 and abs(c - pc) <= 1 for pr, pc in placed): continue
        placed.append((r, c))
    if len(placed) < 2: return None
    for r, c in placed: g[r][c] = rng.choice([2, 9])
    return g
def tf25(g):
    pts = cells(g, lambda v: v in (1, 3))
    if not pts: return None
    r0 = min(r for r, _ in pts); c0 = min(c for _, c in pts)
    cells_ = {(r - r0, c - c0): g[r][c] for r, c in pts}
    out = copy(g)
    for r, c, col in _markers(g, exclude=(0, 1, 3)):
        for (dr, dc), v in cells_.items():
            vv = (3 if v == 1 else 1) if col == 2 else v
            rr, cc = r + dr, c + dc
            if 0 <= rr < len(out) and 0 <= cc < len(out[0]): out[rr][cc] = vv
    return out
rule("stamp_colour_swap_within_template_by_marker",
     "The template is drawn in two colours, 1 and 3, in a fixed pattern; it is stamped at every marker, "
     "top-left cell on the marker: at colour-2 markers the two template colours are swapped (1 becomes 3 "
     "and 3 becomes 1), at colour-9 markers it is stamped unchanged.", gi25, tf25)


# 26. filled at colour 2, outline-only at colour 3
def gi26(rng):
    return _scene(rng, [2, 3], k=(2, 4), tmpl_n=(5, 8))
def tf26(g):
    shape = _template(g)
    if shape is None: return None
    sset = set(shape)
    outline = [p for p in shape if any((p[0] + dr, p[1] + dc) not in sset for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)))]
    out = copy(g)
    for r, c, col in _markers(g):
        sh = shape if col == 2 else outline
        _stamp(out, sh, TCOL, r, c)
    return out
rule("stamp_filled_colour2_outline_colour3",
     "The template is stamped at every marker, top-left cell on the marker, in the template colour: "
     "colour-2 markers get every template cell stamped (filled), colour-3 markers get only the template "
     "cells that have at least one 4-neighbour outside the shape (its outline).", gi26, tf26)


# 27. grey markers erased (no stamp), other coloured markers stamped normally
def gi27(rng):
    return _scene(rng, [5, 2, 3], k=(2, 4))
def tf27(g):
    shape = _template(g)
    if shape is None: return None
    out = copy(g)
    for r, c, col in _markers(g):
        if col == 5:
            out[r][c] = 0
        else:
            _stamp(out, shape, TCOL, r, c)
    return out
rule("stamp_grey_markers_erased_others_stamped",
     "Grey (colour 5) markers are simply cleared to background with no stamp; every other marker gets the "
     "template stamped on it, top-left cell on the marker, in the template colour.", gi27, tf27)


# 28. left half of template at colour 2, right half at colour 3
def gi28(rng):
    return _scene(rng, [2, 3], k=(2, 4), tmpl_n=(5, 8))
def tf28(g):
    shape = _template(g)
    if shape is None: return None
    cmax = max(c for _, c in shape)
    mid = cmax // 2
    left = [p for p in shape if p[1] <= mid]
    right = [p for p in shape if p[1] > mid]
    out = copy(g)
    for r, c, col in _markers(g):
        sh = left if col == 2 else right
        _stamp(out, sh, TCOL, r, c)
    return out
rule("stamp_left_half_colour2_right_half_colour3",
     "The template's cells are split by its own vertical midline into a left half and a right half; "
     "colour-2 markers get only the left half stamped on them, colour-3 markers get only the right half, in "
     "both cases with the template's top-left cell placed on the marker.", gi28, tf28)


# 29. progressive scale by reading-order index (1st marker x1, 2nd x2, 3rd x3)
def gi29(rng):
    return _scene(rng, [2], k=(3, 3), tmpl_n=(2, 3), lo=16, hi=28, margin=4)
def tf29(g):
    shape = _template(g)
    if shape is None: return None
    out = copy(g)
    for i, (r, c, col) in enumerate(_markers(g)):
        _stamp(out, _scale_shape(shape, min(i + 1, 3)), TCOL, r, c)
    return out
rule("stamp_progressive_scale_by_reading_order",
     "The template is stamped at every marker, top-left cell on the marker, in the template colour, scaled "
     "up by its own rank in reading order (top row first, left to right): the first marker gets normal "
     "size, the second double size, the third (and any later one) triple size.", gi29, tf29)


# 30. global rotation chosen by a corner digit, applied to every marker alike
def gi30(rng):
    h, w = size(rng, 12, 28); g = blank(h, w)
    shape = random_shape(rng, rng.randint(3, 6))
    th, tw = _bbox_shape(shape)
    if th + 4 >= h or tw + 4 >= w: return None
    for r, c in shape: g[r][c] = TCOL
    k = rng.randint(0, 3)
    g[0][w - 1] = k + 1
    kk = rng.randint(2, 4)
    cand = [(r, c) for r in range(h) for c in range(w) if not (r < th + 2 and c < tw + 2) and (r, c) != (0, w - 1)]
    rng.shuffle(cand)
    placed = []
    for r, c in cand:
        if len(placed) >= kk: break
        if any(abs(r - pr) <= 1 and abs(c - pc) <= 1 for pr, pc in placed): continue
        placed.append((r, c))
    if len(placed) < 2: return None
    for r, c in placed: g[r][c] = 2
    return g
def tf30(g):
    shape = _template(g)
    if shape is None: return None
    h, w = dims(g)
    k = g[0][w - 1] - 1
    out = copy(g); out[0][w - 1] = 0
    sh = _rot_shape(shape, k)
    for r, c, col in _markers(g, exclude=(0, TCOL)):
        if (r, c) == (0, w - 1): continue
        _stamp(out, sh, TCOL, r, c)
    return out
rule("stamp_global_rotation_from_corner_digit",
     "The top-right corner cell holds a digit (1 to 4); every marker, regardless of its own colour, gets "
     "the template stamped on it, top-left cell on the marker, in the template colour, rotated clockwise by "
     "(corner digit minus one) quarter turns; the corner digit is then cleared.", gi30, tf30, digits=True)


# 31. mirrored horizontally if the marker sits in the right half of the grid, plain in the left half
def gi31(rng):
    return _scene(rng, [2], k=(2, 4))
def tf31(g):
    shape = _template(g)
    if shape is None: return None
    w = dims(g)[1]
    out = copy(g)
    for r, c, col in _markers(g):
        sh = _mirror_h(shape) if c >= w // 2 else shape
        _stamp(out, sh, TCOL, r, c)
    return out
rule("stamp_mirror_by_grid_half",
     "The template is stamped at every marker, top-left cell on the marker, in the template colour: a "
     "marker in the right half of the grid (column index at least half the grid's width) gets it mirrored "
     "left-to-right, a marker in the left half gets it unchanged.", gi31, tf31)


# 32. rotated by the marker's rank in reading order, mod 4 (positional code, not colour)
def gi32(rng):
    return _scene(rng, [2], k=(3, 6))
def tf32(g):
    shape = _template(g)
    if shape is None: return None
    out = copy(g)
    for i, (r, c, col) in enumerate(_markers(g)):
        _stamp(out, _rot_shape(shape, i % 4), TCOL, r, c)
    return out
rule("stamp_rotate_by_reading_order_index",
     "The template is stamped at every marker, top-left cell on the marker, in the template colour, "
     "rotated clockwise by a number of quarter turns equal to the marker's own rank in reading order "
     "(top row first, left to right, counting the first marker as rank 0), taken modulo four.", gi32, tf32)


# 33. which of two templates is used depends on which half (top/bottom) the marker sits in
def gi33(rng):
    h, w = size(rng, 14, 28); g = blank(h, w)
    sh_a = random_shape(rng, rng.randint(3, 5)); sh_b = random_shape(rng, rng.randint(3, 5))
    ah, aw = _bbox_shape(sh_a); bh, bw = _bbox_shape(sh_b)
    if ah + bh + 6 >= h or aw + 3 >= w or bw + 3 >= w: return None
    for r, c in sh_a: g[r][c] = TCOL
    for r, c in sh_b: g[r + ah + 1][c] = 9
    k = rng.randint(2, 4)
    cand = [(r, c) for r in range(ah + bh + 3, h) for c in range(w)]
    rng.shuffle(cand)
    placed = []
    for r, c in cand:
        if len(placed) >= k: break
        if any(abs(r - pr) <= 1 and abs(c - pc) <= 1 for pr, pc in placed): continue
        placed.append((r, c))
    if len(placed) < 2: return None
    for r, c in placed: g[r][c] = 2
    return g
def tf33(g):
    sh_a = _template(g, TCOL)
    pts9 = cells(g, lambda v: v == 9)
    if sh_a is None or not pts9: return None
    r0 = min(r for r, _ in pts9); c0 = min(c for _, c in pts9)
    sh_b = sorted((r - r0, c - c0) for r, c in pts9)
    h = dims(g)[0]
    out = copy(g)
    for r, c, col in _markers(g, exclude=(0, TCOL, 9)):
        if r < h // 2:
            _stamp(out, sh_a, TCOL, r, c)
        else:
            _stamp(out, sh_b, 9, r, c)
    return out
rule("stamp_two_templates_by_grid_half",
     "Two templates are drawn, template A (in the template colour) above template B (in colour 9); every "
     "marker in the top half of the grid gets template A stamped on it in the template colour, every "
     "marker in the bottom half gets template B stamped on it in colour 9, both with the template's "
     "top-left cell placed on the marker.", gi33, tf33)


# 34. clipped to a frame's interior bounds (every marker is inside, but overflow past the frame is dropped)
def gi34(rng):
    h, w = size(rng, 16, 28); g = blank(h, w)
    shape = random_shape(rng, rng.randint(4, 7))
    th, tw = _bbox_shape(shape)
    if th + 4 >= h or tw + 4 >= w: return None
    for r, c in shape: g[r][c] = TCOL
    r0, c0 = rng.randint(th + 2, h - 8), rng.randint(tw + 2, w - 8)
    r1, c1 = rng.randint(r0 + 4, min(h - 2, r0 + 9)), rng.randint(c0 + 4, min(w - 2, c0 + 9))
    rect(g, r0, c0, r1, c1, 5, fill=False)
    inside = [(r, c) for r in range(r0 + 1, r1 - 1) for c in range(c0 + 1, c1 - 1)]
    rng.shuffle(inside)
    k = rng.randint(2, 3)
    if len(inside) < k: return None
    for r, c in inside[:k]: g[r][c] = 2
    return g
def tf34(g):
    shape = _template(g)
    frame = cells(g, lambda v: v == 5)
    if shape is None or not frame: return None
    r0, c0, r1, c1 = bbox(frame)
    out = copy(g)
    for r, c, col in _markers(g, exclude=(0, TCOL, 5)):
        for dr, dc in shape:
            rr, cc = r + dr, c + dc
            if r0 < rr < r1 and c0 < cc < c1:
                out[rr][cc] = TCOL
    return out
rule("stamp_clipped_to_frame_interior",
     "A hollow grey rectangle holds every marker; the template is stamped at each marker, top-left cell on "
     "the marker, in the template colour, but any stamp cell that would fall outside the rectangle's "
     "interior (on or beyond its border) is dropped.", gi34, tf34)


# 35. stamp colour cycles through a fixed palette by the marker's rank in reading order
def gi35(rng):
    return _scene(rng, [2], k=(3, 5))
def tf35(g):
    shape = _template(g)
    if shape is None: return None
    palette = [1, 3, 4]
    out = copy(g)
    for i, (r, c, col) in enumerate(_markers(g)):
        _stamp(out, shape, palette[i % 3], r, c)
    return out
rule("stamp_colour_cycles_by_reading_order",
     "The template is stamped at every marker, top-left cell on the marker; the stamp colour cycles through "
     "colours 1, 3, 4 in that fixed order by the marker's rank in reading order (top row first, left to "
     "right), wrapping back to 1 after 4.", gi35, tf35)


# 36. recoloured to the other of two allowed marker colours (swap-recolour)
def gi36(rng):
    return _scene(rng, [2, 3], k=(2, 4))
def tf36(g):
    shape = _template(g)
    if shape is None: return None
    out = copy(g)
    for r, c, col in _markers(g):
        _stamp(out, shape, 3 if col == 2 else 2, r, c)
    return out
rule("stamp_recoloured_to_opposite_marker_colour",
     "The template is stamped at every marker, top-left cell on the marker, recoloured to the OTHER of the "
     "two marker colours in play: a colour-2 marker's stamp is painted in colour 3, and a colour-3 marker's "
     "stamp is painted in colour 2.", gi36, tf36)


# 37. a uniform scale for every marker set by the total marker count
def gi37(rng):
    return _scene(rng, [2], k=(2, 4), tmpl_n=(2, 3), lo=14, hi=28, margin=3)
def tf37(g):
    shape = _template(g)
    if shape is None: return None
    n = len(_markers(g))
    scale = min(n - 1, 3)
    out = copy(g)
    for r, c, col in _markers(g):
        _stamp(out, _scale_shape(shape, scale), TCOL, r, c)
    return out
rule("stamp_scale_set_by_total_marker_count",
     "Every marker gets the template stamped on it, top-left cell on the marker, in the template colour, at "
     "the same scale for all of them: the scale factor is (total number of markers minus one), capped at "
     "three.", gi37, tf37)


# 38. anchored at the template's bottom-right cell instead of its top-left
def gi38(rng):
    return _scene(rng, [2], k=(2, 4))
def tf38(g):
    shape = _template(g)
    if shape is None: return None
    th, tw = _bbox_shape(shape)
    out = copy(g)
    for r, c, col in _markers(g):
        _stamp(out, shape, TCOL, r - (th - 1), c - (tw - 1))
    return out
rule("stamp_anchored_at_bottom_right",
     "The template is stamped at every marker, but anchored by its bottom-right bounding-box cell rather "
     "than its top-left: the marker ends up covered by the template's own last row and last column.",
     gi38, tf38)


# 39. two stamps per marker: one above (plain) and one below (vertically mirrored), flanking it
def gi39(rng):
    return _scene(rng, [2], k=(2, 3), tmpl_n=(2, 3), lo=14, hi=28, margin=5)
def tf39(g):
    shape = _template(g)
    if shape is None: return None
    th, tw = _bbox_shape(shape)
    out = copy(g)
    for r, c, col in _markers(g):
        _stamp(out, shape, TCOL, r - th, c)
        _stamp(out, _mirror_v(shape), TCOL, r + 1, c)
    return out
rule("stamp_mirrored_pair_flanking_marker",
     "Each marker gets two stamps of the template in the template colour: one placed directly above it "
     "(top-left cell of that copy on the row just above the marker, same column) unchanged, and one placed "
     "directly below it, vertically mirrored, with no stamp placed on the marker's own row.", gi39, tf39)


# 40. the template is stamped at every marker and then every marker cell is restored on top, visible
def gi40(rng):
    return _scene(rng, [2, 3, 4], k=(2, 4), tmpl_n=(4, 7))
def tf40(g):
    shape = _template(g)
    if shape is None: return None
    out = copy(g)
    for r, c, col in _markers(g):
        _stamp(out, shape, TCOL, r, c)
        out[r][c] = col
    return out
# stamp_marker_kept_visible_on_top dropped 2026-10-12 (review 2: behavioural duplicate of stamp_clipped_by_occupied_cells)