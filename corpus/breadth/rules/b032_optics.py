# b032_optics.py -- OPTICS: beams, mirrors, splitters, prisms, filters, absorbers, lenses, walls,
# shadows (ray casting) and periscopes. Every transform is a hand-applicable, deterministic beam
# trace: a beam enters at a border cell, travels in a straight line, and reacts to special cells it
# crosses. Structural marker colours (mirrors=3/4, splitter=6, prism=7, wall=8, block=9, filter=2)
# are hard-coded within a rule the way GREY is in b008_motion.py; beam/emitter colours vary with rng.
import sys, os
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


def _size(rng, lo=6, hi=18):
    """Grid size; about 30% of drawn inputs land in the 21-30 band ARC-AGI-2 lives in."""
    if rng.random() < 0.32:
        return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _emitter(rng, h, w):
    """A random non-corner border cell and the inward direction from it."""
    side = rng.choice(("top", "bottom", "left", "right"))
    if side == "top":
        return 0, rng.randint(1, w - 2), 1, 0
    if side == "bottom":
        return h - 1, rng.randint(1, w - 2), -1, 0
    if side == "left":
        return rng.randint(1, h - 2), 0, 0, 1
    return rng.randint(1, h - 2), w - 1, 0, -1


def _find_emitter(g, structural=()):
    """The one non-corner border cell with a colour not in `structural`, and its inward direction."""
    h, w = dims(g)
    for r in range(h):
        for c in range(w):
            v = g[r][c]
            if v == 0 or v in structural:
                continue
            if r == 0 and 0 < c < w - 1:
                return r, c, 1, 0, v
            if r == h - 1 and 0 < c < w - 1:
                return r, c, -1, 0, v
            if c == 0 and 0 < r < h - 1:
                return r, c, 0, 1, v
            if c == w - 1 and 0 < r < h - 1:
                return r, c, 0, -1, v
    return None


def _find_emitters(g, structural=()):
    h, w = dims(g)
    out = []
    for r in range(h):
        for c in range(w):
            v = g[r][c]
            if v == 0 or v in structural:
                continue
            if r == 0 and 0 < c < w - 1: out.append((r, c, 1, 0, v))
            elif r == h - 1 and 0 < c < w - 1: out.append((r, c, -1, 0, v))
            elif c == 0 and 0 < r < h - 1: out.append((r, c, 0, 1, v))
            elif c == w - 1 and 0 < r < h - 1: out.append((r, c, 0, -1, v))
    return out


def _cast(g, r, c, dr, dc, colour, mirror_a=None, mirror_b=None, splitter=None, absorber=None,
          wall=None, filt=None, lens=None):
    """Trace a beam from (r, c) heading (dr, dc) across grid g. Returns (path, event). path is the
    list of (row, col, colour-to-paint) for the BACKGROUND cells crossed (colour may change along the
    way, e.g. after a filter). event is ("edge",), ("wall", r, c), ("absorbed", r, c, colour) or
    ("split", r, c, dr, dc, colour)."""
    h, w = dims(g)
    path = []
    steps = 0
    while 0 <= r < h and 0 <= c < w and steps < h * w * 4 + 8:
        steps += 1
        v = g[r][c]
        if wall is not None and v == wall:
            return path, ("wall", r, c)
        if absorber is not None and v == absorber:
            return path, ("absorbed", r, c, colour)
        if v == 0:
            path.append((r, c, colour))
        if filt is not None and v in filt:
            colour = v
        if mirror_a is not None and v == mirror_a:
            dr, dc = -dc, -dr
        elif mirror_b is not None and v == mirror_b:
            dr, dc = dc, dr
        elif lens is not None and v == lens:
            dr, dc = 1, 1
        elif splitter is not None and v == splitter:
            return path, ("split", r, c, dr, dc, colour)
        r, c = r + dr, c + dc
    return path, ("edge", None, None)


def _paint(g, path):
    for r, c, col in path:
        g[r][c] = col


def _trace_split(g, r, c, dr, dc, colour, splitter, mirror_a=None, mirror_b=None, depth=0):
    """Beam forks at `splitter` into straight-ahead and one perpendicular branch."""
    if depth > 6:
        return []
    path, ev = _cast(g, r, c, dr, dc, colour, mirror_a=mirror_a, mirror_b=mirror_b, splitter=splitter)
    if ev[0] == "split":
        sr, sc, sdr, sdc, scol = ev[1], ev[2], ev[3], ev[4], ev[5]
        out = list(path)
        for ndr, ndc in ((sdr, sdc), (-sdc, -sdr)):
            out += _trace_split(g, sr + ndr, sc + ndc, ndr, ndc, scol, splitter, mirror_a, mirror_b, depth + 1)
        return out
    return path


def _trace_prism(g, r, c, dr, dc, colour, prism, mirror_a=None, mirror_b=None, depth=0):
    """Beam fans at `prism` into three: straight ahead and both perpendiculars."""
    if depth > 6:
        return []
    path, ev = _cast(g, r, c, dr, dc, colour, mirror_a=mirror_a, mirror_b=mirror_b, splitter=prism)
    if ev[0] == "split":
        sr, sc, sdr, sdc, scol = ev[1], ev[2], ev[3], ev[4], ev[5]
        out = list(path)
        for ndr, ndc in ((sdr, sdc), (-sdc, -sdr), (sdc, sdr)):
            out += _trace_prism(g, sr + ndr, sc + ndc, ndr, ndc, scol, prism, mirror_a, mirror_b, depth + 1)
        return out
    return path


def _cast_count_turns(g, r, c, dr, dc, mirror_a, mirror_b):
    h, w = dims(g)
    turns = 0
    lastr, lastc = r, c
    steps = 0
    while 0 <= r < h and 0 <= c < w and steps < h * w * 4 + 8:
        steps += 1
        v = g[r][c]
        lastr, lastc = r, c
        if v == mirror_a:
            dr, dc = -dc, -dr; turns += 1
        elif v == mirror_b:
            dr, dc = dc, dr; turns += 1
        r, c = r + dr, c + dc
    return turns, lastr, lastc


def _ray_passes(h, w, r, c, dr, dc, target):
    while 0 <= r < h and 0 <= c < w:
        if (r, c) == target:
            return True
        r += dr; c += dc
    return False


# ---------------------------------------------------------------- 1
def gi_straight(rng):
    h, w = _size(rng, 6, 16)
    g = blank(h, w)
    r, c, dr, dc = _emitter(rng, h, w)
    g[r][c] = rng.choice(COLOURS)
    return g
def tf_straight(g):
    found = _find_emitter(g)
    if not found: return None
    r, c, dr, dc, col = found
    out = copy(g)
    path, ev = _cast(out, r + dr, c + dc, dr, dc, col)
    if not path: return None
    _paint(out, path)
    return out
rule("beam_border_emitter_straight_path", "A beam leaves the one border emitter cell, travels straight into the grid and paints every empty cell it crosses the emitter's colour.", gi_straight, tf_straight)


# ---------------------------------------------------------------- 2
def gi_slash(rng):
    h, w = _size(rng, 8, 18)
    g = blank(h, w)
    r, c, dr, dc = _emitter(rng, h, w)
    col = rng.choice([x for x in COLOURS if x != 3])
    g[r][c] = col
    path, ev = _cast(g, r + dr, c + dc, dr, dc, col)
    if len(path) < 2: return None
    mr, mc, _ = rng.choice(path[:-1]) if len(path) > 1 else path[0]
    g[mr][mc] = 3
    return g
def tf_slash(g):
    found = _find_emitter(g, structural=(3,))
    if not found: return None
    r, c, dr, dc, col = found
    out = copy(g)
    path, ev = _cast(out, r + dr, c + dc, dr, dc, col, mirror_a=3)
    _paint(out, path)
    return out
rule("beam_forward_slash_mirror_turn", "A beam travels straight until it meets a '/' mirror (colour 3), which turns it 90 degrees, and paints its whole path.", gi_slash, tf_slash)


# ---------------------------------------------------------------- 3
def gi_backslash(rng):
    h, w = _size(rng, 8, 18)
    g = blank(h, w)
    r, c, dr, dc = _emitter(rng, h, w)
    col = rng.choice([x for x in COLOURS if x != 4])
    g[r][c] = col
    path, ev = _cast(g, r + dr, c + dc, dr, dc, col)
    if len(path) < 2: return None
    mr, mc, _ = rng.choice(path[:-1]) if len(path) > 1 else path[0]
    g[mr][mc] = 4
    return g
def tf_backslash(g):
    found = _find_emitter(g, structural=(4,))
    if not found: return None
    r, c, dr, dc, col = found
    out = copy(g)
    path, ev = _cast(out, r + dr, c + dc, dr, dc, col, mirror_b=4)
    _paint(out, path)
    return out
rule("beam_back_slash_mirror_turn", "A beam travels straight until it meets a '\\' mirror (colour 4), which turns it 90 degrees the other way, and paints its whole path.", gi_backslash, tf_backslash)


# ---------------------------------------------------------------- 4
def gi_maze(rng):
    h, w = _size(rng, 14, 26)
    g = blank(h, w)
    r, c, dr, dc = _emitter(rng, h, w)
    col = rng.choice([x for x in COLOURS if x not in (3, 4)])
    g[r][c] = col
    nmirrors = rng.randint(2, 5)
    placed = 0
    for _ in range(nmirrors):
        path, ev = _cast(g, r + dr, c + dc, dr, dc, col, mirror_a=3, mirror_b=4)
        if len(path) < 2: break
        pr, pc, _ = rng.choice(path[:-1]) if len(path) > 1 else path[0]
        g[pr][pc] = rng.choice((3, 4))
        placed += 1
    if placed < 2: return None
    return g
def tf_maze(g):
    found = _find_emitter(g, structural=(3, 4))
    if not found: return None
    r, c, dr, dc, col = found
    out = copy(g)
    path, ev = _cast(out, r + dr, c + dc, dr, dc, col, mirror_a=3, mirror_b=4)
    _paint(out, path)
    return out
rule("beam_mixed_mirror_maze", "A beam zig-zags through several '/' and '\\' mirrors (colours 3 and 4), each turning it 90 degrees, and paints its whole path.", gi_maze, tf_maze)


# ---------------------------------------------------------------- 5
def gi_split(rng):
    h, w = _size(rng, 12, 24)
    g = blank(h, w)
    r, c, dr, dc = _emitter(rng, h, w)
    col = rng.choice([x for x in COLOURS if x != 6])
    g[r][c] = col
    path, ev = _cast(g, r + dr, c + dc, dr, dc, col)
    if len(path) < 3: return None
    pr, pc, _ = rng.choice(path[1:-1]) if len(path) > 2 else path[0]
    g[pr][pc] = 6
    return g
def tf_split(g):
    found = _find_emitter(g, structural=(6,))
    if not found: return None
    r, c, dr, dc, col = found
    out = copy(g)
    path = _trace_split(out, r + dr, c + dc, dr, dc, col, 6)
    if not path: return None
    _paint(out, path)
    return out
rule("beam_splitter_cell_forks_two", "A beam travels straight until it meets a splitter cell (colour 6), which forks it into a straight beam and a perpendicular one; both paint their path.", gi_split, tf_split)


# ---------------------------------------------------------------- 6
def gi_cross(rng):
    h, w = _size(rng, 10, 20)
    g = blank(h, w)
    cols = rng.sample(COLOURS, 2)
    ems = []
    tries = 0
    while len(ems) < 2 and tries < 60:
        tries += 1
        r, c, dr, dc = _emitter(rng, h, w)
        if g[r][c] == 0:
            g[r][c] = cols[len(ems)]
            ems.append((r, c, dr, dc))
    if len(ems) < 2: return None
    return g
def tf_cross(g):
    ems = _find_emitters(g)
    if len(ems) != 2: return None
    out = copy(g)
    paint = {}
    for r, c, dr, dc, col in ems:
        path, _ = _cast(out, r + dr, c + dc, dr, dc, col)
        for pr, pc, pcol in path:
            paint[(pr, pc)] = 5 if (pr, pc) in paint else pcol
    if not paint: return None
    for (pr, pc), col in paint.items():
        out[pr][pc] = col
    return out
rule("two_colour_beams_cross_to_grey", "Two beams of different colours cross the grid in straight lines from two border emitters; any cell their paths share turns grey.", gi_cross, tf_cross)


# ---------------------------------------------------------------- 7
def gi_count3(rng):
    h, w = _size(rng, 12, 22)
    g = blank(h, w)
    placed = 0
    tries = 0
    while placed < 3 and tries < 60:
        tries += 1
        r, c, dr, dc = _emitter(rng, h, w)
        if g[r][c] == 0:
            g[r][c] = 1
            placed += 1
    if placed < 3: return None
    return g
def tf_count3(g):
    ems = _find_emitters(g)
    if len(ems) < 2: return None
    out = copy(g)
    cnt = {}
    for r, c, dr, dc, col in ems:
        path, _ = _cast(out, r + dr, c + dc, dr, dc, 1)
        for pr, pc, _ in path:
            cnt[(pr, pc)] = cnt.get((pr, pc), 0) + 1
    if not cnt: return None
    for (pr, pc), n in cnt.items():
        out[pr][pc] = min(n, 9)
    return out
rule("three_beams_crossing_count_digit", "Three beams cross the grid in straight lines; every cell is coloured with the number of beams that pass through it.", gi_count3, tf_count3, digits=True)


# ---------------------------------------------------------------- 8
def gi_absorb(rng):
    h, w = _size(rng, 10, 20)
    g = blank(h, w)
    r, c, dr, dc = _emitter(rng, h, w)
    col = rng.choice([x for x in COLOURS if x != 9])
    g[r][c] = col
    path, ev = _cast(g, r + dr, c + dc, dr, dc, col)
    if len(path) < 3: return None
    idx = rng.randint(1, len(path) - 2)
    pr, pc, _ = path[idx]
    length = rng.randint(2, 4)
    if dr != 0:
        c0 = max(0, pc - length // 2); c1 = min(w - 1, c0 + length - 1)
        for cc in range(c0, c1 + 1): g[pr][cc] = 9
    else:
        r0 = max(0, pr - length // 2); r1 = min(h - 1, r0 + length - 1)
        for rr in range(r0, r1 + 1): g[rr][pc] = 9
    return g
def tf_absorb(g):
    found = _find_emitter(g, structural=(9,))
    if not found: return None
    r, c, dr, dc, col = found
    out = copy(g)
    path, ev = _cast(out, r + dr, c + dc, dr, dc, col, absorber=9)
    _paint(out, path)
    if ev[0] == "absorbed":
        h, w = dims(out)
        for rr in range(h):
            for cc in range(w):
                if out[rr][cc] == 9:
                    out[rr][cc] = col
    return out
rule("beam_absorbed_by_black_block_recolours_it", "A beam travels straight until it hits a block (colour 9); the whole block is recoloured with the beam's colour.", gi_absorb, tf_absorb)


# ---------------------------------------------------------------- 9
def gi_filter(rng):
    h, w = _size(rng, 10, 20)
    g = blank(h, w)
    r, c, dr, dc = _emitter(rng, h, w)
    col = rng.choice([x for x in COLOURS if x != 2])
    g[r][c] = col
    path, ev = _cast(g, r + dr, c + dc, dr, dc, col)
    if len(path) < 3: return None
    idx = rng.randint(1, len(path) - 2)
    pr, pc, _ = path[idx]
    g[pr][pc] = 2
    return g
def tf_filter(g):
    found = _find_emitter(g, structural=(2,))
    if not found: return None
    r, c, dr, dc, col = found
    out = copy(g)
    path, ev = _cast(out, r + dr, c + dc, dr, dc, col, filt={2})
    _paint(out, path)
    return out
rule("beam_through_colour_filter_takes_colour", "A beam travels straight; once it crosses a coloured filter cell (colour 2) it takes on that colour for the rest of its path.", gi_filter, tf_filter)


# ---------------------------------------------------------------- 10
def gi_filter2(rng):
    h, w = _size(rng, 12, 24)
    g = blank(h, w)
    r, c, dr, dc = _emitter(rng, h, w)
    f1, f2 = rng.sample(COLOURS, 2)
    col = rng.choice([x for x in COLOURS if x not in (f1, f2)])
    g[r][c] = col
    path, ev = _cast(g, r + dr, c + dc, dr, dc, col)
    if len(path) < 5: return None
    i1, i2 = sorted(rng.sample(range(1, len(path) - 1), 2))
    pr1, pc1, _ = path[i1]; pr2, pc2, _ = path[i2]
    g[pr1][pc1] = f1; g[pr2][pc2] = f2
    return g
def tf_filter2(g):
    found = _find_emitter(g)
    if not found: return None
    r, c, dr, dc, col = found
    filt_colours = {v for row in g for v in row if v not in (0, col)}
    if not filt_colours: return None
    out = copy(g)
    path, ev = _cast(out, r + dr, c + dc, dr, dc, col, filt=filt_colours)
    _paint(out, path)
    return out
rule("beam_through_two_filters_last_colour_wins", "A beam crosses two filter cells of different colours in a row; from the second one onward it paints with the colour of the LAST filter it crossed.", gi_filter2, tf_filter2)


# ---------------------------------------------------------------- 11
def gi_filtercount(rng):
    h, w = _size(rng, 12, 24)
    g = blank(h, w)
    r, c, dr, dc = _emitter(rng, h, w)
    col = rng.choice([x for x in COLOURS if x != 2])
    g[r][c] = col
    path, ev = _cast(g, r + dr, c + dc, dr, dc, col)
    k = rng.randint(1, min(4, max(1, len(path) - 2)))
    if len(path) < k + 2: return None
    idxs = sorted(rng.sample(range(1, len(path) - 1), k))
    for i in idxs:
        pr, pc, _ = path[i]
        g[pr][pc] = 2
    return g
def tf_filtercount(g):
    found = _find_emitter(g, structural=(2,))
    if not found: return None
    r, c, dr, dc, col = found
    out = copy(g)
    path, ev = _cast(out, r + dr, c + dc, dr, dc, col)
    cnt = sum(row.count(2) for row in g)
    if cnt == 0 or not path: return None
    _paint(out, path)
    lr, lc, _ = path[-1]
    out[lr][lc] = min(cnt, 9)
    return out
rule("beam_filter_count_as_digit", "A beam paints its straight path with its own colour, but the last cell of that path is coloured with the number of filter cells (colour 2) it crossed.", gi_filtercount, tf_filtercount, digits=True)


# ---------------------------------------------------------------- 12
def gi_bouncev(rng):
    h, w = _size(rng, 10, 22)
    if h < 5: return None
    k = rng.randint(1, 4)
    g = blank(h, w)
    r = rng.randint(0, h - 1)
    g[r][0] = k
    return g
def tf_bouncev(g):
    h, w = dims(g)
    r0 = None; k = None
    for r in range(h):
        if g[r][0] != 0:
            r0, k = r, g[r][0]; break
    if r0 is None or h < 3: return None
    out = copy(g)
    r, dr, bounces, cells = r0, 1, 0, []
    for c in range(w):
        cells.append((r, c))
        nr = r + dr
        if nr < 0 or nr >= h:
            dr = -dr; bounces += 1
            if bounces >= k: break
        r = r + dr
    if len(cells) < 2: return None
    for rr, cc in cells:
        if out[rr][cc] == 0: out[rr][cc] = 5
    return out
rule("beam_bounces_off_top_bottom_k_times", "A beam leaves the left edge heading right and down; its colour (a digit) is how many times it must bounce off the top and bottom edges before it stops, and it paints its whole path.", gi_bouncev, tf_bouncev, digits=True)


# ---------------------------------------------------------------- 13
def gi_bounceh(rng):
    h, w = _size(rng, 10, 22)
    if w < 5: return None
    k = rng.randint(1, 4)
    g = blank(h, w)
    c = rng.randint(0, w - 1)
    g[0][c] = k
    return g
def tf_bounceh(g):
    h, w = dims(g)
    c0 = None; k = None
    for c in range(w):
        if g[0][c] != 0:
            c0, k = c, g[0][c]; break
    if c0 is None or w < 3: return None
    out = copy(g)
    c, dc, bounces, cells = c0, 1, 0, []
    for r in range(h):
        cells.append((r, c))
        nc = c + dc
        if nc < 0 or nc >= w:
            dc = -dc; bounces += 1
            if bounces >= k: break
        c = c + dc
    if len(cells) < 2: return None
    for rr, cc in cells:
        if out[rr][cc] == 0: out[rr][cc] = 5
    return out
rule("beam_bounces_off_left_right_k_times", "A beam leaves the top edge heading down and right; its colour (a digit) is how many times it must bounce off the left and right edges before it stops, and it paints its whole path.", gi_bounceh, tf_bounceh, digits=True)


# ---------------------------------------------------------------- 14
def _billiard_step(r, c, dr, dc, h, w):
    nr, nc = r + dr, c + dc
    if nr < 0 or nr >= h: dr = -dr; nr = r + dr
    if nc < 0 or nc >= w: dc = -dc; nc = c + dc
    return nr, nc, dr, dc
def gi_billiard(rng):
    h, w = _size(rng, 8, 20)
    if h < 4 or w < 4: return None
    r, c, dr, dc = 0, 0, 1, 1
    T = rng.randint(3, (h + w) * 2)
    for _ in range(T):
        r, c, dr, dc = _billiard_step(r, c, dr, dc, h, w)
    if (r, c) == (0, 0): return None
    g = blank(h, w)
    g[r][c] = 5
    return g
def tf_billiard(g):
    h, w = dims(g)
    tgt = None
    for r in range(h):
        for c in range(w):
            if g[r][c] == 5: tgt = (r, c)
    if tgt is None: return None
    out = copy(g)
    r, c, dr, dc = 0, 0, 1, 1
    cells = [(0, 0)]
    steps = 0
    while (r, c) != tgt and steps < h * w * 4 + 8:
        steps += 1
        r, c, dr, dc = _billiard_step(r, c, dr, dc, h, w)
        cells.append((r, c))
    if (r, c) != tgt: return None
    for rr, cc in cells:
        out[rr][cc] = 3
    out[tgt[0]][tgt[1]] = 5
    return out
rule("diagonal_billiard_beam_to_target", "A beam leaves the top-left corner diagonally, bouncing off all four edges like a billiard ball, and paints its path until it reaches the marked target cell.", gi_billiard, tf_billiard)


# ---------------------------------------------------------------- 15
def gi_prism(rng):
    h, w = _size(rng, 12, 24)
    g = blank(h, w)
    r, c, dr, dc = _emitter(rng, h, w)
    col = rng.choice([x for x in COLOURS if x != 7])
    g[r][c] = col
    path, ev = _cast(g, r + dr, c + dc, dr, dc, col)
    if len(path) < 3: return None
    pr, pc, _ = rng.choice(path[1:-1]) if len(path) > 2 else path[0]
    g[pr][pc] = 7
    return g
def tf_prism(g):
    found = _find_emitter(g, structural=(7,))
    if not found: return None
    r, c, dr, dc, col = found
    out = copy(g)
    path = _trace_prism(out, r + dr, c + dc, dr, dc, col, 7)
    if not path: return None
    _paint(out, path)
    return out
rule("prism_cell_splits_beam_three_ways", "A beam travels straight until it meets a prism cell (colour 7), which fans it into three beams: straight ahead and both perpendiculars; all three paint their path.", gi_prism, tf_prism)


# ---------------------------------------------------------------- 16
def gi_wallstop(rng):
    h, w = _size(rng, 10, 22)
    g = blank(h, w)
    r, c, dr, dc = _emitter(rng, h, w)
    col = rng.choice([x for x in COLOURS if x != 8])
    g[r][c] = col
    if dr != 0:
        wr = rng.randint(2, h - 3) if h > 5 else h // 2
        for cc in range(w): g[wr][cc] = 8
    else:
        wc = rng.randint(2, w - 3) if w > 5 else w // 2
        for rr in range(h): g[rr][wc] = 8
    return g
def tf_wallstop(g):
    found = _find_emitter(g, structural=(8,))
    if not found: return None
    r, c, dr, dc, col = found
    out = copy(g)
    path, ev = _cast(out, r + dr, c + dc, dr, dc, col, wall=8)
    _paint(out, path)
    if ev[0] == "wall":
        out[ev[1]][ev[2]] = col
    return out
rule("beam_stops_at_wall_lights_impact_cell", "A beam travels straight until it hits a solid wall line (colour 8); the beam's own colour lights up the exact wall cell it struck.", gi_wallstop, tf_wallstop)


# ---------------------------------------------------------------- 17
def gi_slit(rng):
    h, w = _size(rng, 10, 22)
    g = blank(h, w)
    r, c, dr, dc = _emitter(rng, h, w)
    col = rng.choice([x for x in COLOURS if x != 8])
    g[r][c] = col
    if dr != 0:
        wr = rng.randint(2, h - 3) if h > 5 else h // 2
        gap = rng.randrange(w)
        for cc in range(w):
            if cc != gap: g[wr][cc] = 8
    else:
        wc = rng.randint(2, w - 3) if w > 5 else w // 2
        gap = rng.randrange(h)
        for rr in range(h):
            if rr != gap: g[rr][wc] = 8
    return g
def tf_slit(g):
    found = _find_emitter(g, structural=(8,))
    if not found: return None
    r, c, dr, dc, col = found
    out = copy(g)
    path, ev = _cast(out, r + dr, c + dc, dr, dc, col, wall=8)
    _paint(out, path)
    if ev[0] == "wall":
        out[ev[1]][ev[2]] = col
    return out
# beam_wall_gap_passes_single_slit dropped 2026-10-12 (trio review: behavioural duplicate or one global operation)
# ---------------------------------------------------------------- 18
def gi_wallblock(rng):
    h, w = _size(rng, 14, 26)
    g = blank(h, w)
    r, c, dr, dc = _emitter(rng, h, w)
    col = rng.choice([x for x in COLOURS if x not in (8, 9)])
    g[r][c] = col
    if dr != 0:
        wr = rng.randint(2, h - 5) if h > 7 else h // 2
        gap = rng.randrange(w)
        for cc in range(w):
            if cc != gap: g[wr][cc] = 8
        br = wr + dr * 2
        if 0 <= br < h: g[br][gap] = 9
    else:
        wc = rng.randint(2, w - 5) if w > 7 else w // 2
        gap = rng.randrange(h)
        for rr in range(h):
            if rr != gap: g[rr][wc] = 8
        bc = wc + dc * 2
        if 0 <= bc < w: g[gap][bc] = 9
    return g
def tf_wallblock(g):
    found = _find_emitter(g, structural=(8, 9))
    if not found: return None
    r, c, dr, dc, col = found
    out = copy(g)
    path, ev = _cast(out, r + dr, c + dc, dr, dc, col, wall=8, absorber=9)
    _paint(out, path)
    if ev[0] == "wall":
        out[ev[1]][ev[2]] = col
    elif ev[0] == "absorbed":
        h2, w2 = dims(out)
        for rr in range(h2):
            for cc in range(w2):
                if out[rr][cc] == 9: out[rr][cc] = col
    return out
rule("beam_passes_gap_then_absorbed_by_block", "A beam that lines up with a wall's single gap passes through and is then absorbed by a block beyond it, which turns the beam's colour; otherwise it just stops at the wall.", gi_wallblock, tf_wallblock)


# ---------------------------------------------------------------- 19
def gi_shadow_right(rng):
    h, w = _size(rng, 10, 24)
    g = blank(h, w)
    blockcol = rng.choice(COLOURS)
    placed = 0
    for r in range(h):
        if rng.random() < 0.7:
            c = rng.randint(1, w - 2)
            g[r][c] = blockcol
            placed += 1
    if placed < 2: return None
    return g
def tf_shadow_right(g):
    h, w = dims(g)
    used = {v for row in g for v in row}
    lit = next((c for c in COLOURS if c not in used), None)
    if lit is None: return None
    out = copy(g)
    for r in range(h):
        hitc = None
        for c in range(w):
            if g[r][c] != 0: hitc = c; break
        rng_end = w if hitc is None else hitc
        for c in range(rng_end): out[r][c] = lit
    return out
rule("shadow_cast_rightward_from_left_light", "Light shines into every row from its left edge; cells before the first block in that row light up, cells behind it stay dark.", gi_shadow_right, tf_shadow_right)


# ---------------------------------------------------------------- 20
def gi_shadow_down(rng):
    h, w = _size(rng, 10, 24)
    g = blank(h, w)
    blockcol = rng.choice(COLOURS)
    placed = 0
    for c in range(w):
        if rng.random() < 0.7:
            r = rng.randint(1, h - 2)
            g[r][c] = blockcol
            placed += 1
    if placed < 2: return None
    return g
def tf_shadow_down(g):
    h, w = dims(g)
    used = {v for row in g for v in row}
    lit = next((c for c in COLOURS if c not in used), None)
    if lit is None: return None
    out = copy(g)
    for c in range(w):
        hitr = None
        for r in range(h):
            if g[r][c] != 0: hitr = r; break
        rng_end = h if hitr is None else hitr
        for r in range(rng_end): out[r][c] = lit
    return out
rule("shadow_cast_downward_from_top_light", "Light shines into every column from the top edge; cells above the first block in that column light up, cells behind it stay dark.", gi_shadow_down, tf_shadow_down)


# ---------------------------------------------------------------- 21
def gi_shadow2(rng):
    h, w = _size(rng, 10, 20)
    g = blank(h, w)
    blockcol = rng.choice(COLOURS)
    cand = [(r, c) for r in range(1, h) for c in range(1, w)]
    k = min(rng.randint(2, max(2, (h * w) // 12)), len(cand))
    for r, c in rng.sample(cand, k):
        g[r][c] = blockcol
    return g
def tf_shadow2(g):
    h, w = dims(g)
    used = {v for row in g for v in row}
    A = next((c for c in COLOURS if c not in used), None)
    if A is None: return None
    B = next((c for c in COLOURS if c not in used and c != A), None)
    if B is None: return None
    litL = [[False] * w for _ in range(h)]
    for r in range(h):
        blocked = False
        for c in range(w):
            litL[r][c] = (not blocked) and g[r][c] == 0
            if g[r][c] != 0: blocked = True
    litT = [[False] * w for _ in range(h)]
    for c in range(w):
        blocked = False
        for r in range(h):
            litT[r][c] = (not blocked) and g[r][c] == 0
            if g[r][c] != 0: blocked = True
    out = copy(g)
    for r in range(h):
        for c in range(w):
            if g[r][c] == 0:
                if litL[r][c] and litT[r][c]: out[r][c] = B
                elif litL[r][c] or litT[r][c]: out[r][c] = A
    return out
rule("shadow_two_lights_double_lit_marker", "Light shines in from the left and from the top; a cell lit by both marks a special colour, a cell lit by only one marks another, and cells reached by neither stay dark.", gi_shadow2, tf_shadow2)


# ---------------------------------------------------------------- 22
def gi_shadowlen(rng):
    h, w = _size(rng, 12, 24)
    if h < 7: return None
    g = blank(h, w)
    blockcol = rng.choice(COLOURS)
    ncols = rng.randint(2, max(2, w // 3))
    for c in rng.sample(range(w), ncols):
        top = rng.randint(0, h // 2)
        ht = rng.randint(1, min(4, h - top - 2))
        for r in range(top, top + ht): g[r][c] = blockcol
    return g
def tf_shadowlen(g):
    h, w = dims(g)
    used = {v for row in g for v in row}
    if 0 not in used: return None
    lit = next((c for c in COLOURS if c not in used), None)
    if lit is None: return None
    shadow = next((c for c in COLOURS if c not in used and c != lit), None)
    if shadow is None: return None
    out = copy(g)
    for c in range(w):
        block_rs = [r for r in range(h) if g[r][c] != 0]
        if not block_rs:
            for r in range(h): out[r][c] = lit
            continue
        top, bottom = min(block_rs), max(block_rs)
        ht = bottom - top + 1
        for r in range(h):
            if g[r][c] != 0: continue
            if r < top: out[r][c] = lit
            elif bottom < r <= bottom + ht: out[r][c] = shadow
            else: out[r][c] = lit
    return out
rule("shadow_length_matches_block_height_digit", "Light shines down each column from the top; the dark shadow below a block extends for exactly as many cells as the block is tall, then the cell is lit again.", gi_shadowlen, tf_shadowlen, digits=True)


# ---------------------------------------------------------------- 23
def gi_periscope(rng):
    h, w = _size(rng, 12, 24)
    if h < 8 or w < 8: return None
    r, c, dr, dc = _emitter(rng, h, w)
    if dc != 1: return None
    col = rng.choice([x for x in COLOURS if x != 4])
    g = blank(h, w)
    g[r][c] = col
    c1 = rng.randint(c + 2, w - 4)
    r1 = rng.randint(r + 2, h - 2)
    if c1 <= c or r1 <= r: return None
    g[r][c1] = 4
    g[r1][c1] = 4
    return g
def tf_periscope(g):
    found = _find_emitter(g, structural=(4,))
    if not found: return None
    r, c, dr, dc, col = found
    out = copy(g)
    path, ev = _cast(out, r + dr, c + dc, dr, dc, col, mirror_b=4)
    if not path: return None
    _paint(out, path)
    return out
# periscope_two_mirrors_vertical_shift dropped 2026-10-12 (trio review: behavioural duplicate or one global operation)
# ---------------------------------------------------------------- 24
def gi_gate(rng):
    h, w = _size(rng, 10, 22)
    g = blank(h, w)
    r, c, dr, dc = _emitter(rng, h, w)
    beam_col, other = rng.sample(COLOURS, 2)
    gate_col = beam_col if rng.random() < 0.5 else other
    g[r][c] = beam_col
    path, ev = _cast(g, r + dr, c + dc, dr, dc, beam_col)
    if len(path) < 3: return None
    idx = rng.randrange(1, len(path) - 1)
    pr, pc, _ = path[idx]
    g[pr][pc] = gate_col
    return g
def tf_gate(g):
    found = _find_emitter(g)
    if not found: return None
    r, c, dr, dc, beam_col = found
    h, w = dims(g)
    gate = None
    for rr in range(h):
        for cc in range(w):
            if g[rr][cc] != 0 and (rr, cc) != (r, c):
                gate = (rr, cc, g[rr][cc])
    if gate is None: return None
    gr, gc, gcol = gate
    out = copy(g)
    if gcol == beam_col:
        path, ev = _cast(out, r + dr, c + dc, dr, dc, beam_col)
        _paint(out, path)
    else:
        path, ev = _cast(out, r + dr, c + dc, dr, dc, beam_col, absorber=gcol)
        _paint(out, path)
        out[gr][gc] = 5
    return out
rule("wall_blocks_unless_beam_colour_matches_gate", "A beam meets a single gate cell; if the gate's colour matches the beam's colour the beam passes straight through, otherwise it is absorbed and the gate flashes grey.", gi_gate, tf_gate)


# ---------------------------------------------------------------- 25
def gi_retro(rng):
    h, w = _size(rng, 8, 20)
    g = blank(h, w)
    r, c, dr, dc = _emitter(rng, h, w)
    col = rng.choice([x for x in COLOURS if x not in (6, 5)])
    g[r][c] = col
    path, ev = _cast(g, r + dr, c + dc, dr, dc, col)
    if len(path) < 2: return None
    mr, mc, _ = rng.choice(path)
    g[mr][mc] = 6
    return g
def tf_retro(g):
    found = _find_emitter(g, structural=(6,))
    if not found: return None
    r, c, dr, dc, col = found
    out = copy(g)
    path, ev = _cast(out, r + dr, c + dc, dr, dc, col, lens=None, mirror_a=None, mirror_b=None)
    # retro-reflector: a single pass, then reverse and retrace back to the emitter
    retro_hit = None
    h, w = dims(out)
    rr, cc = r + dr, c + dc
    steps = 0
    full_path = []
    while 0 <= rr < h and 0 <= cc < w and steps < h * w * 2 + 8:
        steps += 1
        if out[rr][cc] == 0:
            full_path.append((rr, cc, col))
        if out[rr][cc] == 6:
            retro_hit = (rr, cc); break
        rr, cc = rr + dr, cc + dc
    if retro_hit is None: return None
    rdr, rdc = -dr, -dc
    rr, cc = retro_hit[0] + rdr, retro_hit[1] + rdc
    steps = 0
    while 0 <= rr < h and 0 <= cc < w and steps < h * w * 2 + 8:
        steps += 1
        if out[rr][cc] == 0:
            full_path.append((rr, cc, col))
        rr, cc = rr + rdr, cc + rdc
    _paint(out, full_path)
    out[r][c] = 5 if col != 5 else 7
    return out
rule("retroreflector_wall_returns_beam_to_emitter", "A beam hits a retro-reflector cell (colour 6) and bounces straight back the way it came; when it returns to the emitter, the emitter cell is marked as having received its own beam back.", gi_retro, tf_retro)


# ---------------------------------------------------------------- 26
def gi_target(rng):
    h, w = _size(rng, 14, 26)
    g = blank(h, w)
    n = rng.randint(2, 3)
    ems = []
    tries = 0
    while len(ems) < n and tries < 80:
        tries += 1
        r, c, dr, dc = _emitter(rng, h, w)
        if g[r][c] == 0:
            used_cols = [e[4] for e in ems]
            avail = [x for x in COLOURS if x != 9 and x not in used_cols]
            if not avail: continue
            col = rng.choice(avail)
            g[r][c] = col
            ems.append((r, c, dr, dc, col))
    if len(ems) < 2: return None
    winner = rng.choice(ems)
    line = []
    r, c = winner[0] + winner[2], winner[1] + winner[3]
    while 0 <= r < h and 0 <= c < w:
        line.append((r, c)); r += winner[2]; c += winner[3]
    if not line: return None
    tr, tc = rng.choice(line)
    g[tr][tc] = 9
    hits = sum(1 for e in ems if _ray_passes(h, w, e[0] + e[2], e[1] + e[3], e[2], e[3], (tr, tc)))
    if hits != 1: return None
    return g
def tf_target(g):
    h, w = dims(g)
    ems = _find_emitters(g, structural=(9,))
    tgt = None
    for rr in range(h):
        for cc in range(w):
            if g[rr][cc] == 9: tgt = (rr, cc)
    if tgt is None or len(ems) < 2: return None
    winners = [e for e in ems if _ray_passes(h, w, e[0] + e[2], e[1] + e[3], e[2], e[3], tgt)]
    if len(winners) != 1: return None
    out = copy(g)
    out[winners[0][0]][winners[0][1]] = 5
    return out
rule("emitter_recolour_reaches_target", "Several emitters each send a straight beam; exactly one beam's path reaches the marked target, and only that emitter's cell is recoloured grey.", gi_target, tf_target)


# ---------------------------------------------------------------- 27
def tf_losers(g):
    h, w = dims(g)
    ems = _find_emitters(g, structural=(9,))
    tgt = None
    for rr in range(h):
        for cc in range(w):
            if g[rr][cc] == 9: tgt = (rr, cc)
    if tgt is None or len(ems) < 2: return None
    winners = [e for e in ems if _ray_passes(h, w, e[0] + e[2], e[1] + e[3], e[2], e[3], tgt)]
    if len(winners) != 1: return None
    out = copy(g)
    for e in ems:
        if (e[0], e[1]) != (winners[0][0], winners[0][1]):
            out[e[0]][e[1]] = 0
    return out
rule("losing_emitters_erased_winner_kept", "Several emitters each send a straight beam toward a marked target; every emitter whose beam does NOT reach the target is erased, leaving only the one that does.", gi_target, tf_losers)


# ---------------------------------------------------------------- 28
def gi_lens(rng):
    h, w = _size(rng, 12, 24)
    g = blank(h, w)
    r, c, dr, dc = _emitter(rng, h, w)
    col = rng.choice([x for x in COLOURS if x != 2])
    g[r][c] = col
    path, ev = _cast(g, r + dr, c + dc, dr, dc, col)
    if len(path) < 3: return None
    idx = rng.randrange(1, len(path) - 1)
    pr, pc, _ = path[idx]
    g[pr][pc] = 2
    return g
def tf_lens(g):
    found = _find_emitter(g, structural=(2,))
    if not found: return None
    r, c, dr, dc, col = found
    out = copy(g)
    path, ev = _cast(out, r + dr, c + dc, dr, dc, col, lens=2)
    if not path: return None
    _paint(out, path)
    return out
rule("lens_cell_bends_beam_diagonal", "A beam travels straight until it meets a lens cell (colour 2), which always bends it onto the down-right diagonal, and paints its whole path.", gi_lens, tf_lens)


# ---------------------------------------------------------------- 29
def gi_diverge(rng):
    h, w = _size(rng, 14, 26)
    g = blank(h, w)
    r, c, dr, dc = _emitter(rng, h, w)
    col = rng.choice([x for x in COLOURS if x != 2])
    g[r][c] = col
    path, ev = _cast(g, r + dr, c + dc, dr, dc, col)
    if len(path) < 4: return None
    idx = rng.randrange(1, len(path) - 2)
    pr, pc, _ = path[idx]
    if pr >= h - 2 or pr < 1: return None
    g[pr][pc] = 2
    return g
def tf_diverge(g):
    found = _find_emitter(g, structural=(2,))
    if not found: return None
    r, c, dr, dc, col = found
    out = copy(g)
    path, ev = _cast(out, r + dr, c + dc, dr, dc, col, splitter=2)
    full = list(path)
    if ev[0] == "split":
        sr, sc = ev[1], ev[2]
        for ndr, ndc in ((1, -1), (1, 1)):
            p2, _ = _cast(out, sr + ndr, sc + ndc, ndr, ndc, col)
            full += p2
    if len(full) < 2: return None
    _paint(out, full)
    return out
rule("diverging_lens_splits_beam_two_diagonals", "A beam meets a diverging lens (colour 2), which always splits it into two beams heading down-left and down-right regardless of its incoming direction.", gi_diverge, tf_diverge)


# ---------------------------------------------------------------- 30
def gi_focal(rng):
    h = rng.randrange(8, 24)
    w = rng.choice(list(range(9, 25, 2)))
    if rng.random() < 0.3:
        h = rng.randrange(21, 30)
        w = rng.choice(list(range(21, 31, 2)))
    g = blank(h, w)
    col1, col2 = rng.sample(COLOURS, 2)
    g[0][0] = col1
    g[0][w - 1] = col2
    return g
def tf_focal(g):
    h, w = dims(g)
    col1 = g[0][0]; col2 = g[0][w - 1]
    if col1 == 0 or col2 == 0: return None
    out = copy(g)
    r, c, p1 = 1, 1, []
    while r < h and 0 <= c < w and g[r][c] == 0:
        p1.append((r, c)); r += 1; c += 1
    r, c, p2 = 1, w - 2, []
    while r < h and 0 <= c < w and g[r][c] == 0:
        p2.append((r, c)); r += 1; c -= 1
    meet = set(p1) & set(p2)
    if not meet: return None
    for rr, cc in p1:
        if (rr, cc) not in meet: out[rr][cc] = col1
    for rr, cc in p2:
        if (rr, cc) not in meet: out[rr][cc] = col2
    for rr, cc in meet:
        out[rr][cc] = 5
    return out
rule("converging_beams_meet_at_focal_cell", "Two beams leave the top corners heading diagonally inward; where their paths meet is marked grey, the rest of each path keeps its own colour.", gi_focal, tf_focal)


# ---------------------------------------------------------------- 31
def gi_turncount(rng):
    h, w = _size(rng, 14, 26)
    g = blank(h, w)
    r, c, dr, dc = _emitter(rng, h, w)
    col = rng.choice([x for x in COLOURS if x not in (3, 4)])
    g[r][c] = col
    nmirrors = rng.randint(1, 3)
    placed = 0
    for _ in range(nmirrors):
        path, ev = _cast(g, r + dr, c + dc, dr, dc, col, mirror_a=3, mirror_b=4)
        if len(path) < 2: break
        idx = rng.randrange(len(path) - 1)
        pr, pc, _ = path[idx]
        g[pr][pc] = rng.choice((3, 4))
        placed += 1
    if placed == 0: return None
    return g
def tf_turncount(g):
    found = _find_emitter(g, structural=(3, 4))
    if not found: return None
    r, c, dr, dc, col = found
    turns, lr, lc = _cast_count_turns(g, r + dr, c + dc, dr, dc, 3, 4)
    out = copy(g)
    out[lr][lc] = min(max(turns, 1), 9)
    return out
rule("mirror_path_turn_count_digit_marker", "A beam winds through several mirrors; the cell where it finally leaves the grid is coloured with the number of turns it made along the way.", gi_turncount, tf_turncount, digits=True)


# ---------------------------------------------------------------- 32
def gi_filtmirror(rng):
    h, w = _size(rng, 14, 26)
    g = blank(h, w)
    r, c, dr, dc = _emitter(rng, h, w)
    col = rng.choice([x for x in COLOURS if x not in (2, 3)])
    g[r][c] = col
    path, ev = _cast(g, r + dr, c + dc, dr, dc, col)
    if len(path) < 4: return None
    i1 = rng.randrange(0, len(path) - 2)
    pr1, pc1, _ = path[i1]
    g[pr1][pc1] = 2
    i2 = rng.randrange(i1 + 1, len(path) - 1)
    pr2, pc2, _ = path[i2]
    g[pr2][pc2] = 3
    return g
def tf_filtmirror(g):
    found = _find_emitter(g, structural=(2, 3))
    if not found: return None
    r, c, dr, dc, col = found
    out = copy(g)
    path, ev = _cast(out, r + dr, c + dc, dr, dc, col, mirror_a=3, filt={2})
    if not path: return None
    _paint(out, path)
    return out
rule("filter_then_mirror_combo_path", "A beam crosses a filter cell (colour 2), taking on that colour, and then meets a '/' mirror (colour 3) that turns it 90 degrees; it paints its whole bent, recoloured path.", gi_filtmirror, tf_filtmirror)


# ---------------------------------------------------------------- 33
def gi_mixcross(rng):
    h, w = _size(rng, 10, 20)
    g = blank(h, w)
    cols = rng.sample(range(1, 10), 2)
    ems = []
    tries = 0
    while len(ems) < 2 and tries < 60:
        tries += 1
        r, c, dr, dc = _emitter(rng, h, w)
        if g[r][c] == 0:
            g[r][c] = cols[len(ems)]
            ems.append((r, c, dr, dc))
    if len(ems) < 2: return None
    return g
def tf_mixcross(g):
    ems = _find_emitters(g)
    if len(ems) != 2: return None
    out = copy(g)
    paths = []
    for r, c, dr, dc, col in ems:
        p, _ = _cast(out, r + dr, c + dc, dr, dc, col)
        paths.append({(pr, pc): col for pr, pc, _ in p})
    if not paths[0] or not paths[1]: return None
    all_cells = set(paths[0]) | set(paths[1])
    for rr, cc in all_cells:
        if (rr, cc) in paths[0] and (rr, cc) in paths[1]:
            a, b = paths[0][(rr, cc)], paths[1][(rr, cc)]
            out[rr][cc] = ((a + b - 1) % 9) + 1
        elif (rr, cc) in paths[0]:
            out[rr][cc] = paths[0][(rr, cc)]
        else:
            out[rr][cc] = paths[1][(rr, cc)]
    return out
rule("colour_pair_crossing_lookup_mix", "Two beams of different colours cross the grid; where their paths overlap, the cell is coloured with the sum of the two colour numbers wrapped into 1-9.", gi_mixcross, tf_mixcross, digits=True)


# ---------------------------------------------------------------- 34
def gi_merge(rng):
    h, w = _size(rng, 10, 22)
    g = blank(h, w)
    col = rng.choice(COLOURS)
    n = rng.randint(2, 3)
    placed = 0
    tries = 0
    while placed < n and tries < 60:
        tries += 1
        r, c, dr, dc = _emitter(rng, h, w)
        if g[r][c] == 0:
            g[r][c] = col
            placed += 1
    if placed < 2: return None
    return g
def tf_merge(g):
    ems = _find_emitters(g)
    if len(ems) < 2: return None
    out = copy(g)
    any_path = False
    for r, c, dr, dc, col in ems:
        path, _ = _cast(out, r + dr, c + dc, dr, dc, col)
        if path: any_path = True
        _paint(out, path)
    if not any_path: return None
    return out
rule("multi_emitter_same_colour_merge_path", "Several emitters of the same colour each send a straight beam; the output is the union of all their painted paths.", gi_merge, tf_merge)


# ---------------------------------------------------------------- 35
def gi_pathlen(rng):
    h, w = _size(rng, 10, 24)
    k = rng.randint(1, 9)
    g = blank(h, w)
    r, c, dr, dc = _emitter(rng, h, w)
    avail = (h if dr else w) - 1
    if avail < k + 1: return None
    g[r][c] = k
    return g
def tf_pathlen(g):
    found = _find_emitter(g)
    if not found: return None
    r, c, dr, dc, k = found
    out = copy(g)
    h, w = dims(g)
    cnt = 0
    rr, cc = r + dr, c + dc
    while cnt < k and 0 <= rr < h and 0 <= cc < w:
        out[rr][cc] = 5
        rr += dr; cc += dc; cnt += 1
    if cnt == 0: return None
    return out
rule("beam_emitter_colour_sets_path_length_digit", "A beam leaves its emitter and travels exactly as many cells as the emitter's colour (a digit) before stopping, even if the grid continues.", gi_pathlen, tf_pathlen, digits=True)


# ---------------------------------------------------------------- 36
def gi_diag(rng):
    h, w = _size(rng, 8, 20)
    g = blank(h, w)
    corner = rng.choice([(0, 0, 1, 1), (0, w - 1, 1, -1), (h - 1, 0, -1, 1), (h - 1, w - 1, -1, -1)])
    r, c, dr, dc = corner
    g[r][c] = rng.choice(COLOURS)
    return g
def tf_diag(g):
    h, w = dims(g)
    corners = {(0, 0): (1, 1), (0, w - 1): (1, -1), (h - 1, 0): (-1, 1), (h - 1, w - 1): (-1, -1)}
    found = None
    for (r, c), (dr, dc) in corners.items():
        if g[r][c] != 0:
            found = (r, c, dr, dc, g[r][c]); break
    if not found: return None
    r, c, dr, dc, col = found
    out = copy(g)
    rr, cc = r + dr, c + dc
    painted = False
    while 0 <= rr < h and 0 <= cc < w:
        out[rr][cc] = col; rr += dr; cc += dc; painted = True
    if not painted: return None
    return out
rule("corner_emitter_diagonal_straight_path", "A beam leaves a corner cell diagonally and paints a straight diagonal line all the way to the opposite corner's edge.", gi_diag, tf_diag)


# ---------------------------------------------------------------- 37
def gi_reach(rng):
    h, w = _size(rng, 10, 22)
    g = blank(h, w)
    r, c, dr, dc = _emitter(rng, h, w)
    col = rng.choice([x for x in COLOURS if x != 9])
    g[r][c] = col
    path, ev = _cast(g, r + dr, c + dc, dr, dc, col)
    if len(path) < 2: return None
    tr, tc, _ = rng.choice(path)
    g[tr][tc] = 9
    return g
def tf_reach(g):
    found = _find_emitter(g, structural=(9,))
    if not found: return None
    r, c, dr, dc, col = found
    h, w = dims(g)
    tgt = None
    for rr in range(h):
        for cc in range(w):
            if g[rr][cc] == 9: tgt = (rr, cc)
    if tgt is None: return None
    out = copy(g)
    path, ev = _cast(out, r + dr, c + dc, dr, dc, col)
    _paint(out, path)
    out[tgt[0]][tgt[1]] = col
    return out
rule("beam_reaches_target_recolours_target_to_emitter", "A beam travels straight across the grid; the marked target cell it passes through is recoloured to the emitter's colour.", gi_reach, tf_reach)


# ---------------------------------------------------------------- 38
def gi_twomaze(rng):
    h, w = _size(rng, 14, 26)
    g = blank(h, w)
    ems = []
    tries = 0
    while len(ems) < 2 and tries < 60:
        tries += 1
        r, c, dr, dc = _emitter(rng, h, w)
        if g[r][c] == 0:
            col = rng.choice([x for x in COLOURS if x not in (3, 4)])
            g[r][c] = col
            ems.append((r, c, dr, dc, col))
    if len(ems) < 2: return None
    nmirrors = rng.randint(1, 4)
    for _ in range(nmirrors):
        e = rng.choice(ems)
        path, ev = _cast(g, e[0] + e[2], e[1] + e[3], e[2], e[3], e[4], mirror_a=3, mirror_b=4)
        if len(path) < 2: continue
        pr, pc, _ = rng.choice(path)
        g[pr][pc] = rng.choice((3, 4))
    return g
def tf_twomaze(g):
    ems = _find_emitters(g, structural=(3, 4))
    if len(ems) < 2: return None
    out = copy(g)
    any_path = False
    for r, c, dr, dc, col in ems:
        path, ev = _cast(out, r + dr, c + dc, dr, dc, col, mirror_a=3, mirror_b=4)
        if path: any_path = True
        _paint(out, path)
    if not any_path: return None
    return out
rule("mirror_maze_two_emitters_distinct_exits", "Two emitters each send a beam through a shared field of mirrors; each beam bends independently and paints its own path in its own colour.", gi_twomaze, tf_twomaze)


# ---------------------------------------------------------------- 39
def gi_splitabsorb(rng):
    h, w = _size(rng, 16, 28)
    g = blank(h, w)
    r, c, dr, dc = _emitter(rng, h, w)
    col = rng.choice([x for x in COLOURS if x not in (6, 9)])
    g[r][c] = col
    path, ev = _cast(g, r + dr, c + dc, dr, dc, col)
    if len(path) < 4: return None
    idx = rng.randrange(1, len(path) - 2)
    sr, sc, _ = path[idx]
    g[sr][sc] = 6
    pdr, pdc = -dc, -dr
    br, bc = sr + pdr * 2, sc + pdc * 2
    if not (0 <= br < h and 0 <= bc < w) or g[br][bc] != 0:
        return None
    g[br][bc] = 9
    return g
def tf_splitabsorb(g):
    found = _find_emitter(g, structural=(6, 9))
    if not found: return None
    r, c, dr, dc, col = found
    out = copy(g)
    path, ev = _cast(out, r + dr, c + dc, dr, dc, col, splitter=6)
    full = list(path)
    if ev[0] == "split":
        sr, sc, sdr, sdc, scol = ev[1], ev[2], ev[3], ev[4], ev[5]
        for ndr, ndc in ((sdr, sdc), (-sdc, -sdr)):
            p2, ev2 = _cast(out, sr + ndr, sc + ndc, ndr, ndc, scol, absorber=9)
            full += p2
            if ev2[0] == "absorbed":
                h2, w2 = dims(out)
                for rr in range(h2):
                    for cc in range(w2):
                        if out[rr][cc] == 9: out[rr][cc] = scol
    if len(full) < 2: return None
    _paint(out, full)
    return out
rule("splitter_one_branch_absorbed_other_continues", "A beam forks at a splitter cell; one branch runs straight to the far edge while the other is absorbed by a block, which turns the beam's colour.", gi_splitabsorb, tf_splitabsorb)


# ---------------------------------------------------------------- 40
def gi_recombine(rng):
    h, w = _size(rng, 16, 28)
    if h < 10 or w < 10: return None
    r, c, dr, dc = _emitter(rng, h, w)
    if dr != 1 or dc != 0: return None
    col = rng.choice([x for x in COLOURS if x not in (3, 4, 6)])
    g = blank(h, w)
    g[r][c] = col
    sc = c
    if sc < 2: return None
    sr = rng.randint(r + 1, h - 5)
    g[sr][sc] = 6
    g[sr][sc - 2] = 3
    g[sr + 3][sc - 2] = 4
    return g
def tf_recombine(g):
    found = _find_emitter(g, structural=(3, 4, 6))
    if not found: return None
    r, c, dr, dc, col = found
    if dr != 1 or dc != 0: return None
    out = copy(g)
    path = _trace_split(out, r + dr, c + dc, dr, dc, col, 6, mirror_a=3, mirror_b=4)
    if not path: return None
    cnt = Counter((pr, pc) for pr, pc, _ in path)
    _paint(out, path)
    for (pr, pc), n in cnt.items():
        if n > 1: out[pr][pc] = 5
    return out
rule("splitter_branches_recombine_to_grey", "A beam forks at a splitter; one branch runs straight down while the other detours through two mirrors and rejoins the first branch's column, and the cell where they reunite turns grey.", gi_recombine, tf_recombine)
