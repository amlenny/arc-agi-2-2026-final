# b054_completion.py -- completing partial objects from evidence: a bounding box, a symmetry, a period,
# or a sibling instance tells the solver exactly what the missing part must be.
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


def multiblob(g, bg=0, conn8=True):
    """Connected components over ALL non-background colours at once (a shape may use >1 colour)."""
    H, W = dims(g); seen, out = set(), []
    nb = [(-1, 0), (1, 0), (0, -1), (0, 1)] + ([(-1, -1), (-1, 1), (1, -1), (1, 1)] if conn8 else [])
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or g[r][c] == bg:
                continue
            comp, st = [], [(r, c)]; seen.add((r, c))
            while st:
                y, x = st.pop(); comp.append((y, x))
                for dy, dx in nb:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen and g[ny][nx] != bg:
                        seen.add((ny, nx)); st.append((ny, nx))
            out.append(comp)
    return out


# ---------------------------------------------------------------- 1
def gi_rect_corner_pixel(rng):
    h, w = size(rng, 6, 22); g = blank(h, w); col = rng.choice(COLOURS)
    r0, c0 = rng.randint(0, h - 4), rng.randint(0, w - 4)
    r1, c1 = r0 + rng.randint(3, min(h - 1, r0 + 10) - r0), c0 + rng.randint(3, min(w - 1, c0 + 10) - c0)
    rect(g, r0, c0, r1, c1, col, fill=False)
    corner = rng.choice([(r0, c0), (r0, c1), (r1, c0), (r1, c1)])
    g[corner[0]][corner[1]] = 0
    return g
def tf_rect_corner_pixel(g):
    out = copy(g); pts = cells(g, lambda v: v != 0); rs = [r for r, _ in pts]; cs = [c for _, c in pts]
    r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs); col = g[r0][c0] if g[r0][c0] else g[rs[0]][cs[0]]
    col = next(v for row in g for v in row if v)
    for r, c in [(r0, c0), (r0, c1), (r1, c0), (r1, c1)]:
        if out[r][c] == 0: out[r][c] = col
    return out
rule("rect_outline_missing_corner_pixel",
     "A rectangle outline has one corner pixel erased; the other three corners fix the bounding box, so the missing corner is repainted in the outline's colour.",
     gi_rect_corner_pixel, tf_rect_corner_pixel)


# ---------------------------------------------------------------- 2
def gi_rect_corner_bite(rng):
    h, w = size(rng, 8, 24); g = blank(h, w); col = rng.choice(COLOURS)
    r0, c0 = rng.randint(0, h - 5), rng.randint(0, w - 5)
    r1 = r0 + rng.randint(4, min(9, h - 1 - r0)); c1 = c0 + rng.randint(4, min(9, w - 1 - c0))
    rect(g, r0, c0, r1, c1, col, fill=True)
    corner = rng.choice([(r0, c0), (r0, c1), (r1, c0), (r1, c1)])
    bh, bw = rng.randint(1, 2), rng.randint(1, 2)
    br0 = corner[0] if corner[0] == r0 else corner[0] - bh + 1
    bc0 = corner[1] if corner[1] == c0 else corner[1] - bw + 1
    for r in range(br0, br0 + bh):
        for c in range(bc0, bc0 + bw):
            g[r][c] = 0
    return g
def tf_rect_corner_bite(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    rs = [r for r, _ in pts]; cs = [c for _, c in pts]
    r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs); col = g[pts[0][0]][pts[0][1]]
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            out[r][c] = col
    return out
rule("rect_filled_corner_bite_restored",
     "A solid rectangle has a small rectangular bite missing from one corner; the surviving cells' bounding box fixes the rectangle, so the bite is repainted solid.",
     gi_rect_corner_bite, tf_rect_corner_bite)


# ---------------------------------------------------------------- 3
def gi_rect_missing_side(rng):
    h, w = size(rng, 8, 24); g = blank(h, w); col = rng.choice(COLOURS)
    r0, c0 = rng.randint(0, h - 5), rng.randint(0, w - 5)
    r1 = r0 + rng.randint(4, min(10, h - 1 - r0)); c1 = c0 + rng.randint(4, min(10, w - 1 - c0))
    rect(g, r0, c0, r1, c1, col, fill=False)
    side = rng.choice(["top", "bottom", "left", "right"])
    if side == "top": [g[r0].__setitem__(c, 0) for c in range(c0, c1 + 1)]
    elif side == "bottom": [g[r1].__setitem__(c, 0) for c in range(c0, c1 + 1)]
    elif side == "left": [g[r].__setitem__(c0, 0) for r in range(r0, r1 + 1)]
    else: [g[r].__setitem__(c1, 0) for r in range(r0, r1 + 1)]
    return g
def tf_rect_missing_side(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    rs = [r for r, _ in pts]; cs = [c for _, c in pts]
    r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs); col = g[pts[0][0]][pts[0][1]]
    rect(out, r0, c0, r1, c1, col, fill=False)
    return out
rule("rect_frame_missing_full_side",
     "A hollow rectangle frame is missing one entire side; the three remaining sides fix the frame's extent, so the missing side is drawn in full.",
     gi_rect_missing_side, tf_rect_missing_side)


# ---------------------------------------------------------------- 4
def gi_dotted_border(rng):
    h, w = size(rng, 9, 24); g = blank(h, w); col = rng.choice(COLOURS)
    r0, c0 = rng.randint(0, h - 6), rng.randint(0, w - 6)
    r1 = r0 + rng.randint(5, min(11, h - 1 - r0)); c1 = c0 + rng.randint(5, min(11, w - 1 - c0))
    rect(g, r0, c0, r1, c1, col, fill=False)
    pts = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if r in (r0, r1) or c in (c0, c1)]
    for i, (r, c) in enumerate(pts):
        if i % 2 == 1: g[r][c] = 0
    return g
def tf_dotted_border(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    rs = [r for r, _ in pts]; cs = [c for _, c in pts]
    r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs); col = g[pts[0][0]][pts[0][1]]
    rect(out, r0, c0, r1, c1, col, fill=False)
    return out
# dotted_rect_border_to_solid dropped 2026-10-12 (review 2: behavioural duplicate of rect_frame_missing_full_side)
# ---------------------------------------------------------------- 5
def gi_checkerboard_gaps(rng):
    h, w = size(rng, 8, 24); g = blank(h, w); col = rng.choice(COLOURS)
    r0, c0 = rng.randint(0, h - 5), rng.randint(0, w - 5)
    r1 = r0 + rng.randint(4, min(10, h - 1 - r0)); c1 = c0 + rng.randint(4, min(10, w - 1 - c0))
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if (r + c) % 2 == 0: g[r][c] = col
    full = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if (r + c) % 2 == 0]
    for r, c in rng.sample(full, max(1, len(full) // 4)):
        g[r][c] = 0
    return g
def tf_checkerboard_gaps(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    rs = [r for r, _ in pts]; cs = [c for _, c in pts]
    r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs); col = g[pts[0][0]][pts[0][1]]
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if (r + c) % 2 == 0: out[r][c] = col
    return out
rule("checkerboard_rect_gaps_restored",
     "A checkerboard-painted rectangle has some of its coloured cells erased to background; row+column parity over the surviving extent fixes which cells must be coloured, so they are repainted.",
     gi_checkerboard_gaps, tf_checkerboard_gaps)


# ---------------------------------------------------------------- 6
def gi_nested_frame_gap(rng):
    h, w = size(rng, 12, 26); g = blank(h, w); outer, inner = colours(rng, 2)
    r0, c0 = rng.randint(0, h - 9), rng.randint(0, w - 9)
    r1 = r0 + rng.randint(8, min(13, h - 1 - r0)); c1 = c0 + rng.randint(8, min(13, w - 1 - c0))
    rect(g, r0, c0, r1, c1, outer, fill=False)
    ir0, ic0, ir1, ic1 = r0 + 2, c0 + 2, r1 - 2, c1 - 2
    rect(g, ir0, ic0, ir1, ic1, inner, fill=False)
    side = rng.choice(["top", "bottom", "left", "right"])
    if side == "top": [g[ir0].__setitem__(c, 0) for c in range(ic0, ic1 + 1)]
    elif side == "bottom": [g[ir1].__setitem__(c, 0) for c in range(ic0, ic1 + 1)]
    elif side == "left": [g[r].__setitem__(ic0, 0) for r in range(ir0, ir1 + 1)]
    else: [g[r].__setitem__(ic1, 0) for r in range(ir0, ir1 + 1)]
    return g
def tf_nested_frame_gap(g):
    out = copy(g); outer = cells(g, lambda v: v != 0)
    rs = [r for r, _ in outer]; cs = [c for _, c in outer]
    r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs)
    inner_col = None
    for r, c in outer:
        if r not in (r0, r1) and c not in (c0, c1):
            inner_col = g[r][c]; break
    if inner_col is None: return None
    rect(out, r0 + 2, c0 + 2, r1 - 2, c1 - 2, inner_col, fill=False)
    return out
rule("nested_square_frames_inner_gap_closed",
     "An inner frame sits two cells inside an outer frame but is missing one full side; the outer frame fixes the inner frame's margin and extent, so the missing side is drawn.",
     gi_nested_frame_gap, tf_nested_frame_gap)


# ---------------------------------------------------------------- 7
def _diamond_cells(cy, cx, rad):
    return {(cy + dy, cx + dx) for dy in range(-rad, rad + 1) for dx in range(-rad, rad + 1) if abs(dy) + abs(dx) == rad}
def gi_diamond_chunk(rng):
    h, w = size(rng, 10, 24); g = blank(h, w); col = rng.choice(COLOURS)
    rad = rng.randint(3, min(h, w) // 2 - 1)
    cy, cx = rng.randint(rad, h - 1 - rad), rng.randint(rad, w - 1 - rad)
    pts = _diamond_cells(cy, cx, rad)
    for r, c in pts: g[r][c] = col
    chunk = rng.choice(["NE", "NW", "SE", "SW"])
    def sign(v): return 1 if v > 0 else (-1 if v < 0 else 0)
    drop = [(r, c) for r, c in pts if (sign(r - cy), sign(c - cx)) == {"NE": (-1, 1), "NW": (-1, -1), "SE": (1, 1), "SW": (1, -1)}[chunk]]
    for r, c in drop: g[r][c] = 0
    return g if drop else None
def tf_diamond_chunk(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    rs = [r for r, _ in pts]; cs = [c for _, c in pts]
    cy, cx = (min(rs) + max(rs)) // 2, (min(cs) + max(cs)) // 2
    rad = max(abs(r - cy) + abs(c - cx) for r, c in pts)
    col = g[pts[0][0]][pts[0][1]]
    full = _diamond_cells(cy, cx, rad)
    for r, c in full: out[r][c] = col
    return out
rule("diamond_outline_chunk_restored_fourfold",
     "A diamond ring (constant taxicab distance from its centre) is missing a whole quadrant arc; the centre and radius, fixed by the surviving cells, regenerate the full ring.",
     gi_diamond_chunk, tf_diamond_chunk)


# ---------------------------------------------------------------- 8
def gi_diamond_bite(rng):
    h, w = size(rng, 9, 22); g = blank(h, w); col = rng.choice(COLOURS)
    rad = rng.randint(3, min(h, w) // 2 - 1)
    cy, cx = rng.randint(rad, h - 1 - rad), rng.randint(rad, w - 1 - rad)
    filled = {(r, c) for r in range(cy - rad, cy + rad + 1) for c in range(cx - rad, cx + rad + 1) if abs(r - cy) + abs(c - cx) <= rad}
    for r, c in filled: g[r][c] = col
    bite = rng.sample(sorted(c for c in filled if abs(c[0] - cy) + abs(c[1] - cx) >= rad - 1), k=min(3, len(filled)))
    for r, c in bite: g[r][c] = 0
    return g
def tf_diamond_bite(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    rs = [r for r, _ in pts]; cs = [c for _, c in pts]
    cy, cx = (min(rs) + max(rs)) // 2, (min(cs) + max(cs)) // 2
    rad = max(abs(r - cy) + abs(c - cx) for r, c in pts)
    col = g[pts[0][0]][pts[0][1]]
    for r in range(cy - rad, cy + rad + 1):
        for c in range(cx - rad, cx + rad + 1):
            if abs(r - cy) + abs(c - cx) <= rad and 0 <= r < len(out) and 0 <= c < len(out[0]):
                out[r][c] = col
    return out
rule("diamond_filled_bite_restored_pointsym",
     "A solid diamond has a bite taken out of its edge; the diamond's centre and radius, read off the surviving cells, regenerate every cell within that taxicab radius.",
     gi_diamond_bite, tf_diamond_bite)


# ---------------------------------------------------------------- 9
def _circle_cells(cy, cx, rad):
    pts = set()
    for ang in range(0, 360):
        import math
        r = cy + round(rad * math.sin(math.radians(ang))); c = cx + round(rad * math.cos(math.radians(ang)))
        pts.add((r, c))
    return pts
def gi_circle_gap_pointsym(rng):
    h, w = size(rng, 10, 24); g = blank(h, w); col = rng.choice(COLOURS)
    rad = rng.randint(3, min(h, w) // 2 - 1)
    cy, cx = rng.randint(rad, h - 1 - rad), rng.randint(rad, w - 1 - rad)
    pts = {(r, c) for r, c in _circle_cells(cy, cx, rad) if 0 <= r < h and 0 <= c < w}
    for r, c in pts: g[r][c] = col
    drop = rng.sample(sorted(pts), k=max(1, len(pts) // 6))
    keep = {(2 * cy - r, 2 * cx - c) for r, c in drop}
    drop = [p for p in drop if p not in keep or True]
    for r, c in drop: g[r][c] = 0
    return g if drop else None
def tf_circle_gap_pointsym(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    rs = [r for r, _ in pts]; cs = [c for _, c in pts]
    cy, cx = (min(rs) + max(rs)) // 2, (min(cs) + max(cs)) // 2
    col = g[pts[0][0]][pts[0][1]]; H, W = dims(g)
    for r, c in pts:
        pr, pc = 2 * cy - r, 2 * cx - c
        if 0 <= pr < H and 0 <= pc < W and out[pr][pc] == 0:
            out[pr][pc] = col
    return out
rule("circle_ring_gap_restored_pointsym",
     "A circular ring is missing a scatter of cells; every surviving ring cell has a point-reflected twin through the centre, and that twin's colour fills any gap.",
     gi_circle_gap_pointsym, tf_circle_gap_pointsym)


# ---------------------------------------------------------------- 10
def gi_circle_quarter(rng):
    h, w = size(rng, 10, 24); g = blank(h, w); col = rng.choice(COLOURS)
    rad = rng.randint(3, min(h, w) // 2 - 1)
    cy, cx = rng.randint(rad, h - 1 - rad), rng.randint(rad, w - 1 - rad)
    pts = {(r, c) for r, c in _circle_cells(cy, cx, rad) if 0 <= r < h and 0 <= c < w}
    for r, c in pts: g[r][c] = col
    for r, c in pts:
        if r >= cy and c >= cx: g[r][c] = 0
    return g
def rot90_pt(cy, cx, r, c):
    dy, dx = r - cy, c - cx
    return cy + dx, cx - dy
def tf_circle_quarter(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    rs = [r for r, _ in pts]; cs = [c for _, c in pts]
    cy, cx = (min(rs) + max(rs)) // 2, (min(cs) + max(cs)) // 2
    col = g[pts[0][0]][pts[0][1]]; H, W = dims(g)
    for r, c in list(pts):
        p = (r, c)
        for _ in range(3):
            p = rot90_pt(cy, cx, *p)
            if 0 <= p[0] < H and 0 <= p[1] < W and out[p[0]][p[1]] == 0:
                out[p[0]][p[1]] = col
    return out
rule("circle_ring_quarter_arc_restored_rotation",
     "A circular ring's entire lower-right quarter is erased; rotating any surviving arc cell 90/180/270 degrees about the centre lands on the missing quarter and supplies its colour.",
     gi_circle_quarter, tf_circle_quarter)


# ---------------------------------------------------------------- 11
def gi_octagon_gap(rng):
    h, w = size(rng, 9, 22); g = blank(h, w); col = rng.choice(COLOURS)
    rad = rng.randint(2, 4); cy, cx = rng.randint(rad + 1, h - 2 - rad), rng.randint(rad + 1, w - 2 - rad)
    ring = [(cy - rad, cx), (cy - rad, cx + rad), (cy, cx + rad), (cy + rad, cx + rad),
            (cy + rad, cx), (cy + rad, cx - rad), (cy, cx - rad), (cy - rad, cx - rad)]
    for r, c in ring: g[r][c] = col
    gap = rng.randrange(len(ring))
    gr, gc = ring[gap]; g[gr][gc] = 0
    return g
def tf_octagon_gap(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    rs = [r for r, _ in pts]; cs = [c for _, c in pts]
    r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs); col = g[pts[0][0]][pts[0][1]]
    cy, cx = (r0 + r1) // 2, (c0 + c1) // 2
    ring = [(r0, cx), (r0, c1), (cy, c1), (r1, c1), (r1, cx), (r1, c0), (cy, c0), (r0, c0)]
    for r, c in ring:
        if out[r][c] == 0: out[r][c] = col
    return out
rule("octagon_ring_single_gap_filled",
     "An eight-point ring (corners and edge midpoints of a square) has exactly one point erased; the other seven fix the square's bounding box, so the missing point is repainted.",
     gi_octagon_gap, tf_octagon_gap)


# ---------------------------------------------------------------- 12
def gi_plus_short_arm(rng):
    h, w = size(rng, 9, 22); g = blank(h, w); col = rng.choice(COLOURS)
    arm = rng.randint(3, min(h, w) // 2 - 1)
    cy, cx = rng.randint(arm, h - 1 - arm), rng.randint(arm, w - 1 - arm)
    for d in range(-arm, arm + 1):
        g[cy + d][cx] = col; g[cy][cx + d] = col
    side = rng.choice(["up", "down", "left", "right"]); short = rng.randint(1, arm - 1)
    if side == "up":
        for d in range(short, arm + 1): g[cy - d][cx] = 0
    elif side == "down":
        for d in range(short, arm + 1): g[cy + d][cx] = 0
    elif side == "left":
        for d in range(short, arm + 1): g[cy][cx - d] = 0
    else:
        for d in range(short, arm + 1): g[cy][cx + d] = 0
    return g
def tf_plus_short_arm(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    col = g[pts[0][0]][pts[0][1]]
    rowcells = [c for r, c in pts if r == pts[0][0]]
    rows_by_col = {}
    for r, c in pts: rows_by_col.setdefault(c, []).append(r)
    cy = max(rows_by_col.items(), key=lambda kv: len(kv[1]))[0]
    cols_by_row = {}
    for r, c in pts: cols_by_row.setdefault(r, []).append(c)
    cx = max(cols_by_row.items(), key=lambda kv: len(kv[1]))[0]
    vert = sorted(r for r, c in pts if c == cx); horiz = sorted(c for r, c in pts if r == cy)
    arm = max(max(cy - vert[0], vert[-1] - cy), max(cx - horiz[0], horiz[-1] - cx))
    for d in range(-arm, arm + 1):
        out[cy + d][cx] = col; out[cy][cx + d] = col
    return out
rule("plus_short_arm_extended_to_match",
     "A plus sign has one arm shorter than the other three; the longest surviving arm fixes the true arm length, so the short arm is extended to match it.",
     gi_plus_short_arm, tf_plus_short_arm)


# ---------------------------------------------------------------- 13
def gi_plus_missing_arm(rng):
    h, w = size(rng, 9, 22); g = blank(h, w); col = rng.choice(COLOURS)
    arm = rng.randint(3, min(h, w) // 2 - 1)
    cy, cx = rng.randint(arm, h - 1 - arm), rng.randint(arm, w - 1 - arm)
    for d in range(-arm, arm + 1):
        g[cy + d][cx] = col; g[cy][cx + d] = col
    side = rng.choice(["up", "down", "left", "right"])
    if side == "up":
        for d in range(1, arm + 1): g[cy - d][cx] = 0
    elif side == "down":
        for d in range(1, arm + 1): g[cy + d][cx] = 0
    elif side == "left":
        for d in range(1, arm + 1): g[cy][cx - d] = 0
    else:
        for d in range(1, arm + 1): g[cy][cx + d] = 0
    return g
def tf_plus_missing_arm(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    col = g[pts[0][0]][pts[0][1]]
    rows_by_col = {}
    for r, c in pts: rows_by_col.setdefault(c, []).append(r)
    cy, vcol = max(rows_by_col.items(), key=lambda kv: len(kv[1]))
    cols_by_row = {}
    for r, c in pts: cols_by_row.setdefault(r, []).append(c)
    cx, hrow = max(cols_by_row.items(), key=lambda kv: len(kv[1]))
    vert = rows_by_col[cx] if cx in rows_by_col else vcol
    horiz = cols_by_row[cy] if cy in cols_by_row else hrow
    arm = max(max(cy - min(vert), max(vert) - cy), max(cx - min(horiz), max(horiz) - cx))
    for d in range(-arm, arm + 1):
        out[cy + d][cx] = col; out[cy][cx + d] = col
    return out
rule("plus_missing_arm_redrawn_full_length",
     "A plus sign is missing one arm entirely; the three surviving arms fix the centre and common arm length, so the missing arm is redrawn at that length.",
     gi_plus_missing_arm, tf_plus_missing_arm)


# ---------------------------------------------------------------- 14
def gi_x_diag_partial(rng):
    h, w = size(rng, 9, 22); g = blank(h, w); col = rng.choice(COLOURS)
    arm = rng.randint(3, min(h, w) // 2 - 1)
    cy, cx = rng.randint(arm, h - 1 - arm), rng.randint(arm, w - 1 - arm)
    for d in range(-arm, arm + 1):
        g[cy + d][cx + d] = col; g[cy + d][cx - d] = col
    quad = rng.choice([(1, 1), (1, -1), (-1, 1), (-1, -1)])
    erase_from = rng.randint(1, arm - 1)
    for d in range(erase_from, arm + 1):
        g[cy + quad[0] * d][cx + quad[1] * d] = 0
    return g
def tf_x_diag_partial(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    col = g[pts[0][0]][pts[0][1]]
    rs = [r for r, _ in pts]; cs = [c for _, c in pts]
    cy, cx = (min(rs) + max(rs)) // 2, (min(cs) + max(cs)) // 2
    arm = max(abs(r - cy) for r, c in pts)
    for d in range(-arm, arm + 1):
        out[cy + d][cx + d] = col; out[cy + d][cx - d] = col
    return out
rule("x_cross_diagonal_partial_restored",
     "An X made of two equal diagonals has one quadrant's arm cut short; the centre and the other three arms fix the common arm length, so the cut arm is redrawn to it.",
     gi_x_diag_partial, tf_x_diag_partial)


# ---------------------------------------------------------------- 15
def gi_hollow_plus_notch(rng):
    au, ad, al, ar = (rng.randint(3, 8) for _ in range(4))
    cy, cx = au + 1, al + 1
    h, w = au + ad + 3, al + ar + 3
    g = blank(h, w); col = rng.choice(COLOURS)
    pts = {(cy + d, cx) for d in range(-au, ad + 1)} | {(cy, cx + d) for d in range(-al, ar + 1)}
    pts |= {(cy + d, cx + 1) for d in range(-au, ad + 1)} | {(cy + 1, cx + d) for d in range(-al, ar + 1)}
    pts = {p for p in pts if 0 <= p[0] < h and 0 <= p[1] < w}
    for r, c in pts: g[r][c] = col
    corner = rng.choice([(1, 1), (1, -1), (-1, 1), (-1, -1)])
    dr = cy + (1 if corner[0] == 1 else 0); dc = cx + (1 if corner[1] == 1 else 0)
    drop = [(dr, dc)]
    for r, c in drop: g[r][c] = 0
    return g if drop else None
def tf_hollow_plus_notch(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    if not pts: return None
    col = g[pts[0][0]][pts[0][1]]
    rows_by_col = {}
    for r, c in pts: rows_by_col.setdefault(c, []).append(r)
    cx = max(rows_by_col.items(), key=lambda kv: len(kv[1]))[0]
    cols_by_row = {}
    for r, c in pts: cols_by_row.setdefault(r, []).append(c)
    cy = max(cols_by_row.items(), key=lambda kv: len(kv[1]))[0]
    diag = {(cy, cx): (cy + 1, cx + 1), (cy + 1, cx + 1): (cy, cx),
            (cy, cx + 1): (cy + 1, cx), (cy + 1, cx): (cy, cx + 1)}
    for p, opp in diag.items():
        if out[p[0]][p[1]] == 0 and out[opp[0]][opp[1]] != 0:
            out[p[0]][p[1]] = col
    return out
rule("hollow_plus_corner_notch_mirror_filled",
     "A thick plus (two one-cell-wide bars crossing) is missing one of the four cells where the bars overlap; that overlap block is always point-symmetric about its own centre, so the missing cell is filled from its diagonal partner.",
     gi_hollow_plus_notch, tf_hollow_plus_notch)


# ---------------------------------------------------------------- 16
def gi_object_vbar(rng):
    h, w = size(rng, 10, 24); g = blank(h, w); col = rng.choice(COLOURS)
    rad = rng.randint(3, min(h, w) // 2 - 2)
    cy, cx = rng.randint(rad, h - 1 - rad), rng.randint(rad, w - 1 - rad)
    for d in range(-rad, rad + 1):
        for e in range(-rad, rad + 1):
            if d * d + e * e <= rad * rad: g[cy + d][cx + e] = col
    bar_c = cx + rng.choice([-1, 0, 1])
    grey = 5 if col != 5 else 6
    for r in range(h):
        g[r][bar_c] = grey
    return g
def tf_object_vbar(g):
    out = copy(g); grey = 5 if any(v == 5 for row in g for v in row) and not all(v in (0, 5) for row in g for v in row if v == 5 and False) else None
    bar_col = None
    H, W = dims(g)
    colcount = {}
    for r in range(H):
        colcount[g[r][0]] = colcount.get(g[r][0], 0)
    bar_c = None
    for c in range(W):
        if all(g[r][c] == g[0][c] for r in range(H)) and g[0][c] != 0:
            bar_c = c; bar_col = g[0][c]; break
    if bar_c is None: return None
    obj_col = next(v for row in g for v in row if v != 0 and v != bar_col)
    pts = cells(g, lambda v: v == obj_col)
    if not pts: return None
    cx_candidates = [c for r, c in pts]
    for r in range(H):
        d = bar_c - 1
        mirror_c = None
        left = out[r][bar_c - 1] if bar_c - 1 >= 0 else 0
        right = out[r][bar_c + 1] if bar_c + 1 < W else 0
        src = left if left == obj_col else (right if right == obj_col else 0)
        if src == obj_col:
            # reflect the opposite side across the bar column into the bar cell
            opp_c = bar_c - (1 if left == obj_col else -1)
            out[r][bar_c] = obj_col
    return out
rule("object_under_vertical_bar_mirror_completed",
     "A circular blob is cut by a one-cell vertical bar of a distinct colour; wherever the blob colour touches the bar on either side, the bar cell between them is repainted the blob's colour.",
     gi_object_vbar, tf_object_vbar)


# ---------------------------------------------------------------- 17
def gi_object_hbar(rng):
    h, w = size(rng, 10, 24); g = blank(h, w); col = rng.choice(COLOURS)
    rad = rng.randint(3, min(h, w) // 2 - 2)
    cy, cx = rng.randint(rad, h - 1 - rad), rng.randint(rad, w - 1 - rad)
    for d in range(-rad, rad + 1):
        for e in range(-rad, rad + 1):
            if d * d + e * e <= rad * rad: g[cy + d][cx + e] = col
    grey = 5 if col != 5 else 6
    bar_r = cy + rng.choice([-1, 0, 1])
    for c in range(len(g[0])):
        g[bar_r][c] = grey
    return g
def tf_object_hbar(g):
    out = copy(g); H, W = dims(g)
    bar_r = None; bar_col = None
    for r in range(H):
        if all(g[r][c] == g[r][0] for c in range(W)) and g[r][0] != 0:
            bar_r = r; bar_col = g[r][0]; break
    if bar_r is None: return None
    obj_col = next(v for row in g for v in row if v != 0 and v != bar_col)
    for c in range(W):
        up = out[bar_r - 1][c] if bar_r - 1 >= 0 else 0
        down = out[bar_r + 1][c] if bar_r + 1 < H else 0
        if up == obj_col or down == obj_col:
            out[bar_r][c] = obj_col
    return out
rule("object_under_horizontal_bar_mirror_completed",
     "A circular blob is cut by a one-cell horizontal bar of a distinct colour; wherever the blob colour touches the bar above or below, that bar cell is repainted the blob's colour.",
     gi_object_hbar, tf_object_hbar)


# ---------------------------------------------------------------- 18
def gi_rect_under_bar(rng):
    h, w = size(rng, 10, 24); g = blank(h, w); col = rng.choice(COLOURS)
    r0, c0 = rng.randint(0, h - 6), rng.randint(0, w - 6)
    r1 = r0 + rng.randint(5, min(10, h - 1 - r0)); c1 = c0 + rng.randint(5, min(10, w - 1 - c0))
    rect(g, r0, c0, r1, c1, col, fill=True)
    grey = 5 if col != 5 else 6
    if rng.random() < 0.5:
        bar_r = rng.randint(r0, r1)
        for c in range(len(g[0])): g[bar_r][c] = grey
    else:
        bar_c = rng.randint(c0, c1)
        for r in range(len(g)): g[r][bar_c] = grey
    return g
def tf_rect_under_bar(g):
    out = copy(g); H, W = dims(g)
    bar_col = None
    for r in range(H):
        if all(g[r][c] == g[r][0] for c in range(W)) and g[r][0] != 0:
            bar_col = g[r][0]; break
    if bar_col is None:
        for c in range(W):
            if all(g[r][c] == g[0][c] for r in range(H)) and g[0][c] != 0:
                bar_col = g[0][c]; break
    if bar_col is None: return None
    pts = cells(g, lambda v: v != 0 and v != bar_col)
    if not pts: return None
    rs = [r for r, _ in pts]; cs = [c for _, c in pts]
    r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs); col = g[pts[0][0]][pts[0][1]]
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if out[r][c] == bar_col: out[r][c] = col
    return out
rule("rect_under_bar_completed_to_bbox",
     "A solid rectangle is crossed by a full-width or full-height bar of a different colour; the rectangle's bounding box, fixed by its surviving corners, determines which bar cells to repaint its colour.",
     gi_rect_under_bar, tf_rect_under_bar)


# ---------------------------------------------------------------- 19
def gi_row_motif_bar(rng):
    h, w = size(rng, 9, 22); g = blank(h, w); col = rng.choice(COLOURS)
    period = rng.randint(3, 5); r = rng.randrange(h)
    for c in range(w):
        if c % period == 0: g[r][c] = col
    grey = 5 if col != 5 else 6
    bc = rng.randint(1, w - 2)
    for c in range(max(0, bc - 1), min(w, bc + 2)):
        g[r][c] = grey if g[r][c] != 0 or True else g[r][c]
    for c in range(max(0, bc - 1), min(w, bc + 2)):
        g[r][c] = grey
    return g
def tf_row_motif_bar(g):
    out = copy(g); H, W = dims(g)
    for r in range(H):
        colours_in_row = set(g[r])
        if len(colours_in_row) >= 2:
            grey_candidates = [v for v in colours_in_row if v != 0]
            # bar colour = colour whose cells are contiguous and colour not matching motif elsewhere
            for bar_col in grey_candidates:
                bar_cells = [c for c in range(W) if g[r][c] == bar_col]
                if not bar_cells: continue
                if max(bar_cells) - min(bar_cells) + 1 == len(bar_cells):
                    motif_cols = [c for c in range(W) if g[r][c] not in (0, bar_col)]
                    if len(motif_cols) < 2: continue
                    period = motif_cols[1] - motif_cols[0]
                    for k in range(1, len(motif_cols)):
                        if motif_cols[k] - motif_cols[k - 1] != period:
                            period = None; break
                    if period is None: continue
                    motif_col = g[r][motif_cols[0]]
                    phase = motif_cols[0] % period
                    for c in bar_cells:
                        if c % period == phase:
                            out[r][c] = motif_col
                        else:
                            out[r][c] = 0
    return out
rule("row_motif_under_bar_completed_from_period",
     "A row has a colour dotted at a fixed period, but a short bar of a different colour overwrites part of the row; the surviving period on either side determines which cells under the bar get the dot colour and which stay empty.",
     gi_row_motif_bar, tf_row_motif_bar)


# ---------------------------------------------------------------- 20
def gi_row_period_gaps(rng):
    h, w = size(rng, 10, 24); g = blank(h, w); col = rng.choice(COLOURS)
    period = rng.randint(2, 4); r = rng.randrange(h)
    cells_on = [c for c in range(w) if c % period == 0]
    for c in cells_on: g[r][c] = col
    drop_n = max(1, len(cells_on) // 4)
    for c in rng.sample(cells_on, min(drop_n, len(cells_on) - 2)):
        g[r][c] = 0
    return g
def tf_row_period_gaps(g):
    out = copy(g); H, W = dims(g)
    for r in range(H):
        on = [c for c in range(W) if g[r][c] != 0]
        if len(on) < 2: continue
        col = g[r][on[0]]
        diffs = sorted(set(b - a for a, b in zip(on, on[1:])))
        period = diffs[0]
        for d in diffs:
            if d % period != 0: period = None; break
        if period is None: continue
        phase = on[0] % period
        for c in range(W):
            if c % period == phase: out[r][c] = col
    return out
rule("row_period_gaps_restored",
     "A row is dotted at a fixed spacing but some dots are missing; the spacing read off the surviving dots fixes every position that must be dotted.",
     gi_row_period_gaps, tf_row_period_gaps)


# ---------------------------------------------------------------- 21
def gi_col_period_gaps(rng):
    h, w = size(rng, 10, 24); g = blank(h, w); col = rng.choice(COLOURS)
    period = rng.randint(2, 4); c = rng.randrange(w)
    rows_on = [r for r in range(h) if r % period == 0]
    for r in rows_on: g[r][c] = col
    drop_n = max(1, len(rows_on) // 4)
    for r in rng.sample(rows_on, min(drop_n, len(rows_on) - 2)):
        g[r][c] = 0
    return g
def tf_col_period_gaps(g):
    out = copy(g); H, W = dims(g)
    for c in range(W):
        on = [r for r in range(H) if g[r][c] != 0]
        if len(on) < 2: continue
        col = g[on[0]][c]
        diffs = sorted(set(b - a for a, b in zip(on, on[1:])))
        period = diffs[0]
        for d in diffs:
            if d % period != 0: period = None; break
        if period is None: continue
        phase = on[0] % period
        for r in range(H):
            if r % period == phase: out[r][c] = col
    return out
rule("column_period_gaps_restored",
     "A column is dotted at a fixed spacing but some dots are missing; the spacing read off the surviving dots fixes every position that must be dotted.",
     gi_col_period_gaps, tf_col_period_gaps)


# ---------------------------------------------------------------- 22
def gi_staircase_missing_step(rng):
    sw = rng.randint(2, 3); n = rng.randint(5, 7)
    h, w = n * sw + rng.randint(0, 3), n * sw + rng.randint(0, 3)
    g = blank(h, w); col = rng.choice(COLOURS)
    r0, c0 = rng.randint(0, h - n * sw), rng.randint(0, w - n * sw)
    steps = []
    for i in range(n):
        r, c = r0 + i * sw, c0 + i * sw
        steps.append((r, c))
        for dr in range(sw):
            for dc in range(sw):
                g[r + dr][c + dc] = col
    skip = rng.randint(1, n - 2)
    r, c = steps[skip]
    for dr in range(sw):
        for dc in range(sw):
            g[r + dr][c + dc] = 0
    return g
def tf_staircase_missing_step(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    col = g[pts[0][0]][pts[0][1]]
    blocks = multiblob(g)
    if len(blocks) < 2: return None
    boxes = sorted((bbox(b) for b in blocks), key=lambda b: b[0])
    sw = boxes[0][2] - boxes[0][0] + 1
    step = sw
    r0, c0 = boxes[0][0], boxes[0][1]
    full_n = (boxes[-1][0] - r0) // step + 1
    for i in range(full_n):
        r, c = r0 + i * step, c0 + i * step
        if not any(b[0] == r for b in boxes):
            for dr in range(sw):
                for dc in range(sw):
                    out[r + dr][c + dc] = col
    return out
rule("staircase_missing_step_restored",
     "A diagonal staircase of equal square steps is missing one step; the step size and spacing fixed by the surviving steps determine where the missing block goes, and it is repainted.",
     gi_staircase_missing_step, tf_staircase_missing_step)


# ---------------------------------------------------------------- 23
def gi_halves_col_gap(rng):
    h, w = size(rng, 10, 24); half_w = rng.randint(3, 8)
    shape = random_shape(rng, rng.randint(6, half_w * 4), conn8=False)
    maxc = max(c for _, c in shape)
    left = [(r, c) for r, c in shape if c <= maxc // 2]
    right = [(r, c) for r, c in shape if c > maxc // 2]
    if not left or not right: return None
    col = rng.choice(COLOURS)
    gap = rng.randint(2, 5)
    rshift = max(c for _, c in left) + 1 + gap
    g = blank(h, w)
    try:
        for r, c in left: g[r][c] = col
        for r, c in right: g[r][c - (min(c for _, c in right)) + rshift] = col
    except IndexError:
        return None
    return g
def tf_halves_col_gap(g):
    H, W = dims(g)
    cols_with = [c for c in range(W) if any(g[r][c] != 0 for r in range(H))]
    if not cols_with: return None
    empty_cols = [c for c in range(min(cols_with), max(cols_with) + 1) if c not in cols_with]
    if not empty_cols: return None
    keep_cols = [c for c in range(W) if c not in empty_cols]
    out = [[g[r][c] for c in keep_cols] for r in range(H)]
    return out
rule("halves_split_by_column_gap_reunited",
     "A single shape has been pulled apart into two pieces with an empty column gap between them; removing exactly the empty columns slides the pieces back together into one shape.",
     gi_halves_col_gap, tf_halves_col_gap)


# ---------------------------------------------------------------- 24
def gi_halves_row_gap(rng):
    h, w = size(rng, 10, 24); half_h = rng.randint(3, 8)
    shape = random_shape(rng, rng.randint(6, half_h * 4), conn8=False)
    maxr = max(r for r, _ in shape)
    top = [(r, c) for r, c in shape if r <= maxr // 2]
    bottom = [(r, c) for r, c in shape if r > maxr // 2]
    if not top or not bottom: return None
    col = rng.choice(COLOURS)
    gap = rng.randint(2, 5)
    bshift = max(r for r, _ in top) + 1 + gap
    g = blank(h, w)
    try:
        for r, c in top: g[r][c] = col
        for r, c in bottom: g[r - (min(r for r, _ in bottom)) + bshift][c] = col
    except IndexError:
        return None
    return g
def tf_halves_row_gap(g):
    H, W = dims(g)
    rows_with = [r for r in range(H) if any(g[r][c] != 0 for c in range(W))]
    if not rows_with: return None
    empty_rows = [r for r in range(min(rows_with), max(rows_with) + 1) if r not in rows_with]
    if not empty_rows: return None
    keep_rows = [r for r in range(H) if r not in empty_rows]
    out = [g[r][:] for r in keep_rows]
    return out
rule("halves_split_by_row_gap_reunited",
     "A single shape has been pulled apart into two pieces with an empty row gap between them; removing exactly the empty rows slides the pieces back together into one shape.",
     gi_halves_row_gap, tf_halves_row_gap)


# ---------------------------------------------------------------- 25
def gi_shape_cut_diag(rng):
    size_ = rng.randint(4, 7); shift = rng.randint(3, 5)
    h = size_ + shift + rng.randint(1, 3); w = size_ * 2 + 2 + rng.randint(0, 3)
    g = blank(h, w); col = rng.choice(COLOURS)
    for i in range(size_):
        for j in range(size_):
            g[i][j] = col
    for i in range(size_):
        for j in range(size_):
            nr = i + shift
            if nr < h: g[nr][j + size_ + 2] = col
    return g
def tf_shape_cut_diag(g):
    H, W = dims(g); blobs = multiblob(g)
    if len(blobs) != 2: return None
    b1, b2 = blobs
    col = g[b1[0][0]][b1[0][1]]
    c_left = min(c for _, c in b1 + b2); c_right = max(c for _, c in b1 + b2)
    r_top = min(r for r, _ in b1 + b2); r_bot = max(r for r, _ in b1 + b2)
    out = blank(H, W)
    for r in range(r_top, r_bot + 1):
        for c in range(c_left, c_right + 1):
            out[r][c] = col
    return out
rule("shape_cut_diagonally_rejoined_across_gap",
     "A rectangle was sliced in two and the right piece slid down, leaving a staggered gap; the two pieces' combined bounding box is the original rectangle, which is repainted solid.",
     gi_shape_cut_diag, tf_shape_cut_diag)


# ---------------------------------------------------------------- 26
def gi_marker_same_colour(rng):
    h, w = size(rng, 9, 22); g = blank(h, w); col, marker = colours(rng, 2)
    shape = random_shape(rng, rng.randint(8, 18), conn8=False)
    r0 = rng.randint(0, h - (max(r for r, _ in shape) + 1)); c0 = rng.randint(0, w - (max(c for _, c in shape) + 1))
    cells_ = [(r0 + r, c0 + c) for r, c in shape]
    marked = rng.sample(cells_, max(1, len(cells_) // 4))
    for r, c in cells_:
        g[r][c] = marker if (r, c) in marked else col
    return g
def tf_marker_same_colour(g):
    out = copy(g); cnt = {}
    for row in g:
        for v in row:
            if v != 0: cnt[v] = cnt.get(v, 0) + 1
    if len(cnt) != 2: return None
    col = max(cnt.items(), key=lambda kv: kv[1])[0]
    for r, row in enumerate(g):
        for c, v in enumerate(row):
            if v != 0 and v != col: out[r][c] = col
    return out
rule("marker_colour_fills_missing_cells_same_colour",
     "A shape is drawn mostly in one colour but a minority of its cells are marked in a second colour standing in for missing fill; the majority colour, read off the shape, is painted over every marked cell.",
     gi_marker_same_colour, tf_marker_same_colour)


# ---------------------------------------------------------------- 27
def gi_marker_mirror_colour(rng):
    h, w = size(rng, 9, 22); g = blank(h, w)
    half_w = w // 2
    cols = colours(rng, rng.randint(2, 3))
    marker = (set(COLOURS) - set(cols)).pop()
    shape = random_shape(rng, rng.randint(6, 12), conn8=False)
    maxc = max(c for _, c in shape)
    if maxc >= half_w: return None
    r0 = rng.randint(0, h - (max(r for r, _ in shape) + 1))
    for r, c in shape:
        col = rng.choice(cols)
        g[r0 + r][c] = col
        g[r0 + r][w - 1 - c] = col
    mirror_cells = [(r0 + r, w - 1 - c) for r, c in shape]
    marked = rng.sample(mirror_cells, max(1, len(mirror_cells) // 3))
    for r, c in marked:
        g[r][c] = marker
    return g
def tf_marker_mirror_colour(g):
    out = copy(g); H, W = dims(g)
    cnt = {}
    for row in g:
        for v in row:
            if v != 0: cnt[v] = cnt.get(v, 0) + 1
    marker = min(cnt.items(), key=lambda kv: kv[1])[0] if cnt else None
    if marker is None: return None
    changed = False
    for r in range(H):
        for c in range(W):
            if g[r][c] == marker:
                mc = W - 1 - c
                if g[r][mc] != 0 and g[r][mc] != marker:
                    out[r][c] = g[r][mc]; changed = True
    return out if changed else None
rule("marker_colour_fills_missing_cells_mirror_colour",
     "A left-right symmetric pattern has some cells replaced by a rare marker colour; the mirror cell across the vertical midline still holds the true colour, which is copied into the marked cell.",
     gi_marker_mirror_colour, tf_marker_mirror_colour)


# ---------------------------------------------------------------- 28
def gi_two_colour_side(rng):
    h, w = size(rng, 10, 24); g = blank(h, w); good, marker = colours(rng, 2)
    r0, c0 = rng.randint(0, h - 6), rng.randint(0, w - 6)
    r1 = r0 + rng.randint(5, min(9, h - 1 - r0)); c1 = c0 + rng.randint(5, min(9, w - 1 - c0))
    rect(g, r0, c0, r1, c1, good, fill=False)
    side = rng.choice(["top", "bottom", "left", "right"])
    if side == "top": [g[r0].__setitem__(c, marker) for c in range(c0, c1 + 1)]
    elif side == "bottom": [g[r1].__setitem__(c, marker) for c in range(c0, c1 + 1)]
    elif side == "left": [g[r].__setitem__(c0, marker) for r in range(r0, r1 + 1)]
    else: [g[r].__setitem__(c1, marker) for r in range(r0, r1 + 1)]
    return g
def tf_two_colour_side(g):
    out = copy(g); cnt = {}
    for row in g:
        for v in row:
            if v != 0: cnt[v] = cnt.get(v, 0) + 1
    if len(cnt) != 2: return None
    good = max(cnt.items(), key=lambda kv: kv[1])[0]
    for r, row in enumerate(g):
        for c, v in enumerate(row):
            if v != 0 and v != good: out[r][c] = good
    return out
# two_colour_outline_marker_side_restored dropped 2026-10-12 (review 2: behavioural duplicate of marker_colour_fills_missing_cells_same_colour)
# ---------------------------------------------------------------- 29
def gi_convex_bite(rng):
    h, w = size(rng, 9, 22); g = blank(h, w); col = rng.choice(COLOURS)
    r0, c0 = rng.randint(0, h - 7), rng.randint(0, w - 7)
    size_ = rng.randint(6, 9)
    pts = {(r0 + i, c0 + j) for i in range(size_) for j in range(size_) if i + j >= size_ // 3 and i + j <= 2 * size_ - size_ // 3}
    for r, c in pts:
        if 0 <= r < h and 0 <= c < w: g[r][c] = col
    bite = rng.sample(sorted(pts), max(1, len(pts) // 6))
    for r, c in bite:
        if 0 <= r < h and 0 <= c < w: g[r][c] = 0
    return g
def tf_convex_bite(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    if not pts: return None
    col = g[pts[0][0]][pts[0][1]]
    rs = [r for r, _ in pts]; cs = [c for _, c in pts]
    r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs)
    pset = set(pts)
    for r in range(r0, r1 + 1):
        inrow = sorted(c for rr, c in pts if rr == r)
        if inrow:
            for c in range(inrow[0], inrow[-1] + 1):
                out[r][c] = col
    return out
rule("convex_hull_bite_filled",
     "A roughly diamond-shaped solid blob has a bite taken out of one edge; filling each row between the leftmost and rightmost surviving cell restores the convex shape.",
     gi_convex_bite, tf_convex_bite)


# ---------------------------------------------------------------- 30
def gi_blob_mirror_bite(rng):
    h, w = size(rng, 9, 22); g = blank(h, w); col = rng.choice(COLOURS)
    half = random_shape(rng, rng.randint(5, 9), conn8=False)
    maxc = max(c for _, c in half)
    r0, c0 = rng.randint(0, h - (max(r for r, _ in half) + 1) - 1), rng.randint(0, (w - 2 * maxc - 2) // 1 if w > 2 * maxc + 2 else 0)
    if w <= 2 * maxc + 2: return None
    full = set()
    for r, c in half:
        full.add((r0 + r, c0 + c)); full.add((r0 + r, c0 + 2 * maxc + 1 - c))
    for r, c in full: g[r][c] = col
    bite = rng.sample(sorted(full), max(1, len(full) // 5))
    for r, c in bite: g[r][c] = 0
    return g if bite else None
def tf_blob_mirror_bite(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    if not pts: return None
    col = g[pts[0][0]][pts[0][1]]
    cs = [c for _, c in pts]; c0, c1 = min(cs), max(cs)
    axis = (c0 + c1)
    H, W = dims(g)
    for r, c in pts:
        mc = axis - c
        if 0 <= mc < W and out[r][mc] == 0:
            out[r][mc] = col
    return out
rule("blob_bite_filled_by_mirror_axis",
     "A blob built to be left-right symmetric about its own bounding box has a bite missing on one side; the mirror cell across that axis, if intact, supplies the missing colour.",
     gi_blob_mirror_bite, tf_blob_mirror_bite)


# ---------------------------------------------------------------- 31
def gi_rect_multi_bite(rng):
    h, w = size(rng, 10, 24); g = blank(h, w); col = rng.choice(COLOURS)
    r0, c0 = rng.randint(0, h - 7), rng.randint(0, w - 7)
    r1 = r0 + rng.randint(6, min(10, h - 1 - r0)); c1 = c0 + rng.randint(6, min(10, w - 1 - c0))
    rect(g, r0, c0, r1, c1, col, fill=True)
    edge = rng.choice(["top", "bottom", "left", "right"])
    for _ in range(rng.randint(2, 4)):
        if edge == "top":
            c = rng.randint(c0, c1); g[r0][c] = 0
        elif edge == "bottom":
            c = rng.randint(c0, c1); g[r1][c] = 0
        elif edge == "left":
            r = rng.randint(r0, r1); g[r][c0] = 0
        else:
            r = rng.randint(r0, r1); g[r][c1] = 0
    return g
def tf_rect_multi_bite(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    if not pts: return None
    rs = [r for r, _ in pts]; cs = [c for _, c in pts]
    r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs); col = g[pts[0][0]][pts[0][1]]
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            out[r][c] = col
    return out
# rect_multi_bite_filled_to_bbox dropped 2026-10-12 (review 2: behavioural duplicate of rect_filled_corner_bite_restored)
# ---------------------------------------------------------------- 32
def _t_glyph(col):
    return {(0, 0), (0, 1), (0, 2), (1, 1), (2, 1)}, col
def _h_glyph(col):
    return {(0, 0), (1, 0), (2, 0), (0, 2), (1, 2), (2, 2), (1, 1)}, col
def _l_glyph(col):
    return {(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)}, col
_TEMPLATES = {"T": {(0, 0), (0, 1), (0, 2), (1, 1), (2, 1)},
              "H": {(0, 0), (1, 0), (2, 0), (0, 2), (1, 2), (2, 2), (1, 1)},
              "L": {(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)}}
def gi_glyph_twin(rng):
    h, w = size(rng, 10, 24); g = blank(h, w); col = rng.choice(COLOURS)
    kind = rng.choice(list(_TEMPLATES)); tpl = _TEMPLATES[kind]
    th = max(r for r, _ in tpl) + 1; tw = max(c for _, c in tpl) + 1
    n = rng.randint(2, 3)
    pos = place_shapes(rng, g, [sorted(tpl)] * n, [col] * n, margin=1)
    if pos is None: return None
    broken = rng.randrange(n)
    r0, c0 = pos[broken]
    drop = rng.sample(sorted(tpl), max(1, len(tpl) // 3))
    for r, c in drop:
        g[r0 + r][c0 + c] = 0
    return g
def tf_glyph_twin(g):
    out = copy(g); blobs = multiblob(g)
    if len(blobs) < 2: return None
    boxes = [bbox(b) for b in blobs]
    shapes = []
    for b, bb in zip(blobs, boxes):
        r0, c0, r1, c1 = bb
        shapes.append(frozenset((r - r0, c - c0) for r, c in b))
    sizes = [len(s) for s in shapes]
    full_idx = max(range(len(shapes)), key=lambda i: sizes[i])
    broken_idx = min(range(len(shapes)), key=lambda i: sizes[i])
    if full_idx == broken_idx: return None
    template = shapes[full_idx]; r0, c0, r1, c1 = boxes[broken_idx]
    col = g[blobs[broken_idx][0][0]][blobs[broken_idx][0][1]]
    for r, c in template:
        out[r0 + r][c0 + c] = col
    return out
rule("glyph_instance_restored_from_twin_template",
     "Two or more copies of the same glyph appear on the grid; one has cells erased, and an intact twin's full cell pattern is the template copied onto the broken one.",
     gi_glyph_twin, tf_glyph_twin)


# ---------------------------------------------------------------- 33
def gi_h_mirror_stroke(rng):
    h, w = size(rng, 10, 22); g = blank(h, w); col = rng.choice(COLOURS)
    ht = rng.randint(3, 5)
    r0, c0 = rng.randint(0, h - ht), rng.randint(0, w - 3)
    for r in range(ht):
        g[r0 + r][c0] = col; g[r0 + r][c0 + 2] = col
    g[r0 + ht // 2][c0 + 1] = col
    side = rng.choice([0, 2])
    for r in range(ht):
        g[r0 + r][c0 + side] = 0
    return g
def tf_h_mirror_stroke(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    if not pts: return None
    col = g[pts[0][0]][pts[0][1]]
    cs = sorted(set(c for _, c in pts))
    if len(cs) < 2: return None
    c_left, c_right = cs[0], cs[-1]
    rs_left = [r for r, c in pts if c == c_left]
    rs_right = [r for r, c in pts if c == c_right]
    if len(rs_left) >= len(rs_right):
        for r in rs_left: out[r][c_right] = col if out[r][c_right] == 0 else out[r][c_right]
        missing = set(rs_left) - set(rs_right)
        for r in missing: out[r][c_right] = col
    else:
        missing = set(rs_right) - set(rs_left)
        for r in missing: out[r][c_left] = col
    return out
rule("letter_h_missing_stroke_mirror_restored",
     "An H glyph has one whole vertical stroke erased; the surviving stroke's row span is the true height, which is copied to redraw the missing stroke at the mirrored column.",
     gi_h_mirror_stroke, tf_h_mirror_stroke)


# ---------------------------------------------------------------- 34
def gi_l_foot_from_siblings(rng):
    h, w = size(rng, 10, 24); g = blank(h, w); col = rng.choice(COLOURS)
    foot = rng.randint(2, 4); leg = rng.randint(3, 5)
    n = rng.randint(2, 3)
    shapes = []
    for _ in range(n):
        s = [(r, 0) for r in range(leg)] + [(leg - 1, c) for c in range(1, foot)]
        shapes.append(s)
    pos = place_shapes(rng, g, shapes, [col] * n, margin=1)
    if pos is None: return None
    broken = rng.randrange(n); r0, c0 = pos[broken]
    short = rng.randint(1, foot - 1)
    for c in range(short, foot):
        g[r0 + leg - 1][c0 + c] = 0
    return g
def tf_l_foot_from_siblings(g):
    out = copy(g); blobs = multiblob(g)
    if len(blobs) < 2: return None
    col = g[blobs[0][0][0]][blobs[0][0][1]]
    foots = []
    for b in blobs:
        r1 = max(r for r, _ in b); cs_at_bottom = sorted(c for r, c in b if r == r1)
        foots.append(max(cs_at_bottom) - min(cs_at_bottom) + 1)
    true_foot = max(foots)
    idx = foots.index(min(foots))
    if foots[idx] == true_foot: return None
    b = blobs[idx]; r1 = max(r for r, _ in b); c0 = min(c for r, c in b if r == r1)
    for c in range(c0, c0 + true_foot):
        out[r1][c] = col
    return out
rule("letter_l_foot_length_from_siblings",
     "Several L-shaped glyphs share one foot length, but one L's foot is shorter; the longest foot among the siblings is the true length, so the short one is extended to match.",
     gi_l_foot_from_siblings, tf_l_foot_from_siblings)


# ---------------------------------------------------------------- 35
def gi_plus_cluster_majority(rng):
    h, w = size(rng, 12, 26); g = blank(h, w); col = rng.choice(COLOURS)
    arm_common = rng.randint(2, 4); n = rng.randint(3, 5)
    shapes = []
    arms = [arm_common] * (n - 1) + [rng.randint(1, arm_common - 1) if arm_common > 1 else 1]
    rng.shuffle(arms)
    for a in arms:
        s = [(a, a + d) for d in range(-a, a + 1)] + [(a + d, a) for d in range(-a, a + 1)]
        shapes.append(s)
    pos = place_shapes(rng, g, shapes, [col] * n, margin=1)
    if pos is None: return None
    return g if len(set(arms)) > 1 else None
def tf_plus_cluster_majority(g):
    out = copy(g); blobs = multiblob(g)
    if len(blobs) < 3: return None
    col = g[blobs[0][0][0]][blobs[0][0][1]]
    infos = []
    for b in blobs:
        rs = [r for r, _ in b]; cs = [c for _, c in b]
        cy = (min(rs) + max(rs)) // 2; cx = (min(cs) + max(cs)) // 2
        arm = max(max(cy - min(rs), max(rs) - cy), max(cx - min(cs), max(cs) - cx))
        infos.append((arm, cy, cx, b))
    from collections import Counter
    common = Counter(a for a, _, _, _ in infos).most_common(1)[0][0]
    for arm, cy, cx, b in infos:
        if arm != common:
            for d in range(-common, common + 1):
                if 0 <= cy + d < len(out): out[cy + d][cx] = col
                if 0 <= cx + d < len(out[0]): out[cy][cx + d] = col
    return out
rule("plus_cluster_arm_length_from_majority",
     "Several plus-shaped glyphs are scattered on the grid and most share one arm length, but one is smaller; the majority arm length across all the pluses is the true length, so the odd one is redrawn at it.",
     gi_plus_cluster_majority, tf_plus_cluster_majority)


# ---------------------------------------------------------------- 36
def gi_arrow_tail(rng):
    h, w = size(rng, 10, 24); g = blank(h, w); col = rng.choice(COLOURS)
    tail = rng.randint(3, 7)
    r0, c0 = rng.randint(0, h - tail - 1), rng.randint(2, w - 3)
    for d in range(tail):
        g[r0 + d][c0] = col
    g[r0 + tail][c0 - 1] = col; g[r0 + tail][c0 + 1] = col; g[r0 + tail][c0] = col
    short_from = rng.randint(1, tail - 1)
    for d in range(short_from):
        g[r0 + d][c0] = 0
    return g
def tf_arrow_tail(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    if not pts: return None
    col = g[pts[0][0]][pts[0][1]]
    head_r = max(r for r, c in pts if len([x for x in pts if x[0] == r]) >= 3)
    head_row_cells = [c for r, c in pts if r == head_r]
    cx = sum(head_row_cells) // len(head_row_cells)
    bottom = head_r
    top_existing = min((r for r, c in pts if c == cx), default=head_r)
    for r in range(0, bottom):
        out[r][cx] = col
    return out
rule("arrow_glyph_missing_tail_restored",
     "An arrow's head is intact but its tail shaft is erased down to a shorter stub; the head fixes the shaft's column, so the shaft is redrawn all the way up from the head.",
     gi_arrow_tail, tf_arrow_tail)


# ---------------------------------------------------------------- 37
def gi_triangle_missing_edge(rng):
    h, w = size(rng, 10, 22); g = blank(h, w); col = rng.choice(COLOURS)
    base = rng.randint(5, 8); r0, c0 = rng.randint(0, h - base), rng.randint(0, w - base)
    pts = set()
    for i in range(base):
        pts.add((r0 + i, c0)); pts.add((r0 + base - 1, c0 + i)); pts.add((r0 + i, c0 + i))
    for r, c in pts: g[r][c] = col
    edge = rng.choice(["left", "bottom", "hyp"])
    if edge == "left":
        for i in range(base): g[r0 + i][c0] = 0
    elif edge == "bottom":
        for i in range(base): g[r0 + base - 1][c0 + i] = 0
    else:
        for i in range(base): g[r0 + i][c0 + i] = 0
    return g
def tf_triangle_missing_edge(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    if not pts: return None
    col = g[pts[0][0]][pts[0][1]]
    rs = [r for r, _ in pts]; cs = [c for _, c in pts]
    r0, c0 = min(rs), min(cs); base = max(rs) - r0 + 1
    for i in range(base):
        out[r0 + i][c0] = col; out[r0 + base - 1][c0 + i] = col; out[r0 + i][c0 + i] = col
    return out
rule("triangle_outline_missing_edge_restored",
     "A right-triangle outline (left edge, bottom edge, hypotenuse) is missing one full edge; the corner positions fixed by the other two edges determine the base length, so the missing edge is redrawn.",
     gi_triangle_missing_edge, tf_triangle_missing_edge)


# ---------------------------------------------------------------- 38
def gi_zigzag_gap(rng):
    h, w = size(rng, 10, 24); g = blank(h, w); col = rng.choice(COLOURS)
    n = rng.randint(6, min(h, w) - 2); c0 = rng.randint(0, w - n)
    pts = []
    r = rng.randint(1, h - 2); up = True
    for i in range(n):
        pts.append((r, c0 + i))
        r += -1 if up else 1
        up = not up
        r = max(0, min(h - 1, r))
    for r, c in pts: g[r][c] = col
    gap_at = rng.randint(2, n - 3)
    g[pts[gap_at][0]][pts[gap_at][1]] = 0
    return g
def tf_zigzag_gap(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    if len(pts) < 3: return None
    col = g[pts[0][0]][pts[0][1]]
    bycol = sorted(pts, key=lambda p: p[1])
    H, W = dims(g)
    cmin, cmax = bycol[0][1], bycol[-1][1]
    present = {c: r for r, c in bycol}
    for c in range(cmin, cmax + 1):
        if c not in present:
            left = present.get(c - 1); right = present.get(c + 1)
            if left is not None and right is not None:
                out[(left + right) // 2][c] = col
    return out
rule("zigzag_line_gap_continued",
     "A one-cell-wide zigzag line is missing one cell; the two line cells immediately on either side of the gap fix its row by their midpoint, so the gap is filled.",
     gi_zigzag_gap, tf_zigzag_gap)


# ---------------------------------------------------------------- 39
def gi_diag_line_gap(rng):
    h, w = size(rng, 10, 24); g = blank(h, w); col = rng.choice(COLOURS)
    n = rng.randint(6, min(h, w))
    r0, c0 = rng.randint(0, h - n), rng.randint(0, w - n)
    for i in range(n): g[r0 + i][c0 + i] = col
    gap_at = rng.randint(1, n - 2)
    g[r0 + gap_at][c0 + gap_at] = 0
    return g
def tf_diag_line_gap(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    if not pts: return None
    col = g[pts[0][0]][pts[0][1]]
    rs = [r for r, _ in pts]; cs = [c for _, c in pts]
    r0, r1 = min(rs), max(rs); c0 = min(cs)
    for i in range(r1 - r0 + 1):
        out[r0 + i][c0 + i] = col
    return out
rule("diagonal_line_gap_continued",
     "A straight diagonal line of cells has one cell missing in the middle; the line's two surviving endpoints fix its full extent, so every cell along it is repainted.",
     gi_diag_line_gap, tf_diag_line_gap)


# ---------------------------------------------------------------- 40
def gi_spiral_gap(rng):
    h, w = size(rng, 11, 24); g = blank(h, w); col = rng.choice(COLOURS)
    rad = rng.randint(3, min(h, w) // 2 - 1)
    cy, cx = rng.randint(rad, h - 1 - rad), rng.randint(rad, w - 1 - rad)
    pts = set()
    for rr in range(1, rad + 1):
        for ang in range(0, 360, 15):
            import math
            r = cy + round(rr * math.sin(math.radians(ang))); c = cx + round(rr * math.cos(math.radians(ang)))
            if 0 <= r < h and 0 <= c < w: pts.add((r, c))
    rings = {}
    for r, c in pts:
        rr = round(((r - cy) ** 2 + (c - cx) ** 2) ** 0.5)
        rings.setdefault(rr, []).append((r, c))
    target_ring = rng.choice(list(rings))
    drop = rng.sample(rings[target_ring], max(1, len(rings[target_ring]) // 3))
    for r, c in pts: g[r][c] = col
    for r, c in drop: g[r][c] = 0
    return g if drop else None
def tf_spiral_gap(g):
    out = copy(g); pts = cells(g, lambda v: v != 0)
    if not pts: return None
    col = g[pts[0][0]][pts[0][1]]
    rs = [r for r, _ in pts]; cs = [c for _, c in pts]
    cy, cx = (min(rs) + max(rs)) // 2, (min(cs) + max(cs)) // 2
    H, W = dims(g)
    for r, c in list(pts):
        p = (r, c)
        for _ in range(3):
            p = rot90_pt(cy, cx, *p)
            if 0 <= p[0] < H and 0 <= p[1] < W and out[p[0]][p[1]] == 0:
                out[p[0]][p[1]] = col
    return out
# spiral_gap_closed_rotation dropped 2026-10-12 (review 2: behavioural duplicate of circle_ring_quarter_arc_restored_rotation)