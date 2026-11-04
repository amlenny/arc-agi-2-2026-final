# b021_containers.py -- containers and nesting: hollow frames that hold items or other frames.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


def _gsize(rng, lo=9, big=0.4):
    if rng.random() < big:
        return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, 20), rng.randint(lo, 20)


def _free(g, r0, c0, r1, c1, m=1):
    H, W = dims(g)
    return all(g[r][c] == 0 for r in range(r0 - m, r1 + m + 1) for c in range(c0 - m, c1 + m + 1) if 0 <= r < H and 0 <= c < W)


def _place_frames(rng, g, k, ih=(2, 7), iw=(2, 7), m=2, cols=None, same=None, top=1):
    """k hollow frames, interiors ih x iw (or all `same`), margin m apart. Returns [(r0,c0,r1,c1,col)] or None."""
    H, W = dims(g); fr = []
    for i in range(k):
        for _ in range(80):
            h = same[0] if same else rng.randint(*ih); w = same[1] if same else rng.randint(*iw)
            if h + 2 > H - top - 1 or w + 2 > W - 2: continue
            r0 = rng.randint(top, H - h - 3); c0 = rng.randint(1, W - w - 3); r1, c1 = r0 + h + 1, c0 + w + 1
            if _free(g, r0, c0, r1, c1, m):
                col = cols[i] if cols else rng.choice(COLOURS)
                rect(g, r0, c0, r1, c1, col, fill=False); fr.append((r0, c0, r1, c1, col)); break
        else:
            return None
    return fr


def _interior(f, gap=0):
    return [(r, c) for r in range(f[0] + 1 + gap, f[2] - gap) for c in range(f[1] + 1 + gap, f[3] - gap)]


def _fill_items(rng, g, f, n, cols, gap=0):
    """n random interior cells of frame f coloured from cols (gap=1 keeps them off the wall)."""
    cells_ = _interior(f, gap); pick = rng.sample(cells_, min(n, len(cells_)))
    for r, c in pick: g[r][c] = rng.choice(cols)
    return len(pick)


def _frames(g):
    """Intact hollow rectangles as (r0,c0,r1,c1,col), sorted top-left first."""
    out = []
    for o in components(g, lambda v: v != 0):
        r0, c0, r1, c1 = bbox(o)
        if r1 - r0 >= 2 and c1 - c0 >= 2 and len(o) == 2 * (r1 - r0 + c1 - c0):
            col = g[o[0][0]][o[0][1]]
            if all(g[r][c] == col for r in (r0, r1) for c in range(c0, c1 + 1)) and all(g[r][c] == col for c in (c0, c1) for r in range(r0, r1 + 1)):
                out.append((r0, c0, r1, c1, col))
    return sorted(out)


def _items(g, f):
    return [(r, c) for r, c in _interior(f) if g[r][c]]


def _blobs(g, cells_):
    """8-connected multi-colour components among the given cells."""
    todo, out = set(cells_), []
    while todo:
        st = [todo.pop()]; comp = []
        while st:
            y, x = st.pop(); comp.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if (y + dy, x + dx) in todo:
                        todo.discard((y + dy, x + dx)); st.append((y + dy, x + dx))
        out.append(sorted(comp))
    return out


def _depth(fr, f):
    return sum(1 for o in fr if o[0] < f[0] and o[1] < f[1] and o[2] > f[2] and o[3] > f[3])


def _nested(rng, g, depth, cols, m=1):
    """One nested set of `depth` frames with gaps of 1-2 between levels; returns outer-first list or None."""
    H, W = dims(g); gaps = [rng.randint(1, 2) for _ in range(depth - 1)]
    need = 3 + sum(2 * (1 + x) for x in gaps)
    if need > H - 2 or need > W - 2: return None
    for _ in range(60):
        h, w = rng.randint(need, H - 2), rng.randint(need, W - 2)
        r0, c0 = rng.randint(1, H - h - 1), rng.randint(1, W - w - 1); r1, c1 = r0 + h - 1, c0 + w - 1
        if _free(g, r0, c0, r1, c1, m): break
    else:
        return None
    out = []
    for lvl in range(depth):
        rect(g, r0, c0, r1, c1, cols[lvl], fill=False); out.append((r0, c0, r1, c1, cols[lvl]))
        if lvl == depth - 1: break
        rest = 3 + sum(2 * (1 + x) for x in gaps[lvl + 1:]); gp = gaps[lvl]
        nh = rng.randint(rest, r1 - r0 + 1 - 2 * (1 + gp)); nw = rng.randint(rest, c1 - c0 + 1 - 2 * (1 + gp))
        nr0 = rng.randint(r0 + 1 + gp, r1 - gp - nh); nc0 = rng.randint(c0 + 1 + gp, c1 - gp - nw)
        r0, c0, r1, c1 = nr0, nc0, nr0 + nh - 1, nc0 + nw - 1
    return out


def _scene_items(rng, k=(2, 4), per=(0, 5), gap=0, item_cols=None, ih=(2, 7), iw=(2, 7), same=None, top=1, m=2, cols=None):
    """Frames with random items; returns (g, frames) or None."""
    h, w = _gsize(rng); g = blank(h, w)
    fr = _place_frames(rng, g, rng.randint(*k), ih, iw, m=m, same=same, top=top, cols=cols)
    if fr is None: return None
    for f in fr:
        ic = item_cols if item_cols else [c for c in COLOURS if c != f[4]]
        _fill_items(rng, g, f, rng.randint(*per), ic, gap)
    return g, fr


# 1 recolour frames by nesting depth
def gi_depth(rng):
    h, w = _gsize(rng, 12); g = blank(h, w); n = 0
    for _ in range(rng.randint(1, 3)):
        d = rng.randint(1, 3); s = _nested(rng, g, d, [rng.choice(COLOURS) for _ in range(d)])
        if s: n = max(n, d)
    return g if n >= 2 else None
def tf_depth(g):
    fr = _frames(g); out = copy(g)
    for f in fr:
        d = _depth(fr, f) + 1
        rect(out, *f[:4], d, fill=False)
    return out
rule("frames_numbered_by_nesting_depth", "Every hollow frame is recoloured with its nesting depth: 1 if no frame surrounds it, 2 if one does, 3 if two do.", gi_depth, tf_depth, digits=True)


# 2 contents move to the empty frame
def gi_to_empty(rng):
    s = _scene_items(rng, (2, 2), (0, 0), same=(rng.randint(2, 6), rng.randint(2, 6)))
    if s is None: return None
    g, fr = s; src = rng.choice(fr)
    _fill_items(rng, g, src, rng.randint(1, 5), [c for c in COLOURS if c not in (fr[0][4], fr[1][4])])
    return g
def tf_to_empty(g):
    fr = _frames(g)
    if len(fr) != 2: return None
    src = [f for f in fr if _items(g, f)]; dst = [f for f in fr if not _items(g, f)]
    if len(src) != 1: return None
    out = copy(g); s, d = src[0], dst[0]
    for r, c in _items(g, s):
        out[r][c] = 0; out[r - s[0] + d[0]][c - s[1] + d[1]] = g[r][c]
    return out
rule("contents_move_to_empty_frame", "Two frames of the same size: everything inside the occupied frame moves into the empty frame, keeping its position relative to the frame.", gi_to_empty, tf_to_empty)


# 3 contents of the smaller frame move into the larger one
def gi_to_larger(rng):
    h, w = _gsize(rng, 12); g = blank(h, w); a, b = colours(rng, 2)
    big = _place_frames(rng, g, 1, (5, 9), (5, 9), cols=[a])
    small = _place_frames(rng, g, 1, (2, 4), (2, 4), cols=[b])
    if not big or not small: return None
    _fill_items(rng, g, small[0], rng.randint(1, 4), [c for c in COLOURS if c not in (a, b)])
    return g
def tf_to_larger(g):
    fr = _frames(g)
    if len(fr) != 2: return None
    s, d = sorted(fr, key=lambda f: (f[2] - f[0]) * (f[3] - f[1]))
    out = copy(g)
    for r, c in _items(g, s):
        out[r][c] = 0; out[r - s[0] + d[0]][c - s[1] + d[1]] = g[r][c]
    return out
rule("small_frame_contents_move_to_large_frame", "The items inside the smaller frame move into the larger frame, placed at the same offset from its top-left corner.", gi_to_larger, tf_to_larger)


# 4 dots in a grey frame move to the frame of their own colour
def gi_to_match(rng):
    k = rng.randint(2, 3); cols = colours(rng, k, exclude=(0, 5))
    s = _scene_items(rng, (k + 1, k + 1), (0, 0), same=(rng.randint(2, 5), rng.randint(2, 5)), cols=[5] + cols)
    if s is None: return None
    g, fr = s; _fill_items(rng, g, fr[0], rng.randint(2, 6), cols)
    return g if _items(g, fr[0]) else None
def tf_to_match(g):
    fr = _frames(g); grey = [f for f in fr if f[4] == 5]
    if len(grey) != 1: return None
    out = copy(g); s = grey[0]; by = {f[4]: f for f in fr}
    for r, c in _items(g, s):
        d = by.get(g[r][c])
        if d is None: return None
        out[r][c] = 0; out[r - s[0] + d[0]][c - s[1] + d[1]] = g[r][c]
    return out
rule("dots_leave_grey_frame_for_matching_frame", "Each dot inside the grey frame moves to the frame of its own colour, keeping the same position inside the frame.", gi_to_match, tf_to_match)


# 5 count the items in a frame, mark that many cells on its top wall
def gi_wallcount(rng):
    s = _scene_items(rng, (2, 4), (1, 4), iw=(4, 8))
    if s is None: return None
    g, fr = s
    return g if all(len(_items(g, f)) <= f[3] - f[1] - 1 for f in fr) else None
def tf_wallcount(g):
    fr = _frames(g); out = copy(g)
    if not fr: return None
    for f in fr:
        n = len(_items(g, f))
        if n > f[3] - f[1] - 1: return None
        for i in range(n): out[f[0]][f[1] + 1 + i] = 8
    return out
rule("item_count_marked_on_top_wall", "For each frame, as many cells of its top wall as it holds items are recoloured 8, starting just right of the corner.", gi_wallcount, tf_wallcount)


# 6 frame holding the most items is filled solid
def gi_fullest(rng):
    s = _scene_items(rng, (2, 4), (0, 6))
    if s is None: return None
    g, fr = s; ns = sorted(len(_items(g, f)) for f in fr)
    return g if ns[-1] > ns[-2] else None
def tf_fullest(g):
    fr = _frames(g)
    if len(fr) < 2: return None
    f = max(fr, key=lambda f: len(_items(g, f))); out = copy(g)
    rect(out, *f[:4], f[4]); return out
rule("frame_with_most_items_filled_solid", "The frame enclosing the most items is filled solid in its own colour, covering its items; other frames are unchanged.", gi_fullest, tf_fullest)


# 7 items leave their frames and line up along the top row
def gi_lineup(rng):
    s = _scene_items(rng, (2, 4), (0, 4), top=2)
    if s is None: return None
    g, fr = s; n = sum(len(_items(g, f)) for f in fr)
    return g if 1 <= n <= len(g[0]) else None
def tf_lineup(g):
    fr = _frames(g); out = copy(g); seq = []
    for f in fr:
        for r, c in _items(g, f):
            seq.append(g[r][c]); out[r][c] = 0
    if not seq or len(seq) > len(g[0]) or any(g[0]): return None
    for i, v in enumerate(seq): out[0][i] = v
    return out
rule("items_leave_frames_line_up_on_top_row", "Every item leaves its frame and the items are listed left to right along the top row, frames read top-left first and items in reading order.", gi_lineup, tf_lineup)


# 8 items not matching their frame's colour are expelled to the right of the frame
def gi_expel(rng):
    h, w = _gsize(rng, 12); g = blank(h, w)
    fr = _place_frames(rng, g, rng.randint(1, 3), (3, 6), (3, 6), m=3)
    if fr is None: return None
    for f in fr:
        if f[3] + 1 >= w: return None
        _fill_items(rng, g, f, rng.randint(1, 4), [f[4]] + colours(rng, 2, exclude=(0, f[4])), gap=1)
    return g if any(g[r][c] != f[4] for f in fr for r, c in _items(g, f)) else None
def tf_expel(g):
    fr = _frames(g); out = copy(g); W = len(g[0])
    if not fr: return None
    for f in fr:
        for r, c in _items(g, f):
            if g[r][c] != f[4]:
                if f[3] + 1 >= W or out[r][f[3] + 1]: return None
                out[r][c] = 0; out[r][f[3] + 1] = g[r][c]
    return out
rule("mismatched_items_expelled_right_of_frame", "Items whose colour differs from their frame's are pushed out to sit just outside the frame's right wall on their own row; matching items stay.", gi_expel, tf_expel)


# 9 nested frames swap colours inner-out
def gi_invert(rng):
    h, w = _gsize(rng, 12); g = blank(h, w); n = 0
    for _ in range(rng.randint(1, 3)):
        if _nested(rng, g, 2, colours(rng, 2), m=1): n += 1
    return g if n else None
def tf_invert(g):
    fr = _frames(g); out = copy(g)
    for f in fr:
        inner = [o for o in fr if _depth([f], o)]
        if len(inner) == 1:
            rect(out, *f[:4], inner[0][4], fill=False); rect(out, *inner[0][:4], f[4], fill=False)
    return out
rule("nested_frame_pair_swaps_colours", "Each frame that sits inside another exchanges colours with its enclosing frame: inner colour goes to the outer wall and outer colour to the inner wall.", gi_invert, tf_invert)


# 10 frames shrink to hug their contents
def gi_shrink(rng):
    s = _scene_items(rng, (1, 3), (1, 4), gap=1, ih=(4, 8), iw=(4, 8))
    if s is None: return None
    g, fr = s
    return g if any(bbox(_items(g, f)) != (f[0] + 1, f[1] + 1, f[2] - 1, f[3] - 1) for f in fr) else None
def tf_shrink(g):
    fr = _frames(g); out = copy(g)
    if not fr: return None
    for f in fr:
        it = _items(g, f)
        if not it: continue
        r0, c0, r1, c1 = bbox(it)
        rect(out, *f[:4], 0, fill=False); rect(out, r0 - 1, c0 - 1, r1 + 1, c1 + 1, f[4], fill=False)
    return out
rule("frames_shrink_to_hug_contents", "Each frame is redrawn as the tightest frame around its contents, one empty cell between items and wall; empty frames stay.", gi_shrink, tf_shrink)


# 11 frame grows to enclose the dots lying just outside it
def gi_grow(rng):
    h, w = _gsize(rng, 12); g = blank(h, w)
    fr = _place_frames(rng, g, 1, (2, 6), (2, 6), m=4)
    if fr is None: return None
    r0, c0, r1, c1, col = fr[0]; dc = rng.choice([c for c in COLOURS if c != col]); n = 0
    for _ in range(rng.randint(1, 3)):
        side = rng.randrange(4); d = rng.randint(2, 3)
        if side == 0: r, c = r0 - d, rng.randint(c0, c1)
        elif side == 1: r, c = r1 + d, rng.randint(c0, c1)
        elif side == 2: r, c = rng.randint(r0, r1), c0 - d
        else: r, c = rng.randint(r0, r1), c1 + d
        if 1 <= r < h - 1 and 1 <= c < w - 1 and g[r][c] == 0: g[r][c] = dc; n += 1
    return g if n else None
def tf_grow(g):
    fr = _frames(g)
    if len(fr) != 1: return None
    f = fr[0]; dots = [(r, c) for r, c in cells(g, lambda v: v != 0) if not (f[0] <= r <= f[2] and f[1] <= c <= f[3])]
    if not dots: return None
    r0, c0, r1, c1 = bbox(dots + [(f[0], f[1]), (f[2], f[3])])
    r0, c0, r1, c1 = min(r0, f[0]) - (1 if r0 < f[0] else 0), min(c0, f[1]) - (1 if c0 < f[1] else 0), max(r1, f[2]) + (1 if r1 > f[2] else 0), max(c1, f[3]) + (1 if c1 > f[3] else 0)
    H, W = dims(g)
    if r0 < 0 or c0 < 0 or r1 >= H or c1 >= W: return None
    out = copy(g); rect(out, *f[:4], 0, fill=False); rect(out, r0, c0, r1, c1, f[4], fill=False)
    for r, c in dots: out[r][c] = g[r][c]
    return out
rule("frame_grows_to_enclose_outside_dots", "The frame expands on whichever sides are needed so that every dot lying outside it ends up inside, one cell clear of the new wall.", gi_grow, tf_grow)


# 12 items fall to the floor of their own frame
def gi_fall(rng):
    s = _scene_items(rng, (1, 4), (1, 6), ih=(3, 7))
    if s is None: return None
    g, fr = s
    return g if any(r < f[2] - 1 and g[r + 1][c] == 0 for f in fr for r, c in _items(g, f)) else None
def tf_fall(g):
    fr = _frames(g); out = copy(g)
    if not fr: return None
    for f in fr:
        for c in range(f[1] + 1, f[3]):
            col = [g[r][c] for r in range(f[0] + 1, f[2]) if g[r][c]]
            for r in range(f[0] + 1, f[2]): out[r][c] = 0
            for i, v in enumerate(reversed(col)): out[f[2] - 1 - i][c] = v
    return out
rule("items_fall_to_frame_floor", "Inside every frame the items drop straight down until they rest on the frame's bottom wall or on another item.", gi_fall, tf_fall)


# 13 frames sorted into a row by number of contents
def gi_sortrow(rng):
    s = _scene_items(rng, (2, 4), (0, 5), ih=(2, 5), iw=(2, 5))
    if s is None: return None
    g, fr = s; ns = [len(_items(g, f)) for f in fr]
    return g if len(set(ns)) == len(ns) and sum(f[3] - f[1] + 2 for f in fr) <= 30 else None
def tf_sortrow(g):
    fr = sorted(_frames(g), key=lambda f: len(_items(g, f)))
    if len(fr) < 2: return None
    H = max(f[2] - f[0] + 1 for f in fr); W = sum(f[3] - f[1] + 2 for f in fr) - 1
    out = blank(H, W); x = 0
    for f in fr:
        paste(out, crop(g, *f[:4]), 0, x); x += f[3] - f[1] + 2
    return out
rule("frames_sorted_by_item_count_into_row", "The frames with their contents are lined up in one row, top-aligned and one column apart, fewest items on the left and most on the right.", gi_sortrow, tf_sortrow)


# 14 a frame with one open side spills its contents out that side
def gi_spill(rng):
    h, w = _gsize(rng, 12); g = blank(h, w)
    fr = _place_frames(rng, g, 1, (3, 7), (3, 7), m=3)
    if fr is None: return None
    r0, c0, r1, c1, col = fr[0]; side = rng.randrange(4)
    if side == 0: rect(g, r0, c0 + 1, r0, c1 - 1, 0)
    elif side == 1: rect(g, r1, c0 + 1, r1, c1 - 1, 0)
    elif side == 2: rect(g, r0 + 1, c0, r1 - 1, c0, 0)
    else: rect(g, r0 + 1, c1, r1 - 1, c1, 0)
    _fill_items(rng, g, fr[0], rng.randint(1, 5), [c for c in COLOURS if c != col], gap=1)
    return g
def tf_spill(g):
    H, W = dims(g); obs = objects(g, 0, conn8=False); walls = max(obs, key=len); r0, c0, r1, c1 = bbox(walls); col = g[walls[0][0]][walls[0][1]]
    miss = [(r, c) for r in (r0, r1) for c in range(c0, c1 + 1) if g[r][c] != col] + [(r, c) for c in (c0, c1) for r in range(r0 + 1, r1) if g[r][c] != col]
    if not miss: return None
    if all(r == r0 for r, _ in miss): dr, dc = -1, 0
    elif all(r == r1 for r, _ in miss): dr, dc = 1, 0
    elif all(c == c0 for _, c in miss): dr, dc = 0, -1
    elif all(c == c1 for _, c in miss): dr, dc = 0, 1
    else: return None
    items = [(r, c) for r in range(r0 + 1, r1) for c in range(c0 + 1, c1) if g[r][c]]
    out = copy(g)
    for r, c in items: out[r][c] = 0
    for r, c in sorted(items, key=lambda p: -(p[0] * dr + p[1] * dc)):
        y, x = r, c
        while 0 <= y + dr < H and 0 <= x + dc < W and out[y + dr][x + dc] == 0: y, x = y + dr, x + dc
        out[y][x] = g[r][c]
    return out
rule("open_sided_frame_spills_items_out", "One wall of the frame is missing; every item inside slides out through that open side and keeps going until it hits the grid edge or another item.", gi_spill, tf_spill)


# 15 contents of gapped frames leak away
def gi_leak(rng):
    s = _scene_items(rng, (2, 4), (1, 4), gap=1, ih=(3, 6), iw=(3, 6))
    if s is None: return None
    g, fr = s; opened = 0
    for f in fr:
        if rng.random() < 0.5:
            side = rng.randrange(4)
            if side == 0: g[f[0]][rng.randint(f[1] + 1, f[3] - 1)] = 0
            elif side == 1: g[f[2]][rng.randint(f[1] + 1, f[3] - 1)] = 0
            elif side == 2: g[rng.randint(f[0] + 1, f[2] - 1)][f[1]] = 0
            else: g[rng.randint(f[0] + 1, f[2] - 1)][f[3]] = 0
            opened += 1
    return g if 0 < opened < len(fr) else None
def tf_leak(g):
    out = copy(g); closed = {f[:4] for f in _frames(g)}; any_ = False
    for o in objects(g, 0, conn8=False):
        r0, c0, r1, c1 = bbox(o)
        if len(o) == 2 * (r1 - r0 + c1 - c0) - 1 and (r0, c0, r1, c1) not in closed:
            for r in range(r0 + 1, r1):
                for c in range(c0 + 1, c1):
                    if out[r][c]: out[r][c] = 0; any_ = True
    return out if any_ else None
rule("gapped_frames_lose_contents", "A frame with a one-cell gap in its wall loses everything inside it; sealed frames keep their contents.", gi_leak, tf_leak)


# 16 frame takes the majority colour of its contents
def gi_majority(rng):
    s = _scene_items(rng, (1, 4), (2, 7), ih=(3, 6), iw=(3, 6))
    if s is None: return None
    g, fr = s
    for f in fr:
        cnt = {}
        for r, c in _items(g, f): cnt[g[r][c]] = cnt.get(g[r][c], 0) + 1
        v = sorted(cnt.values())
        if len(v) > 1 and v[-1] == v[-2]: return None
    return g
def tf_majority(g):
    fr = _frames(g); out = copy(g)
    if not fr: return None
    for f in fr:
        cnt = {}
        for r, c in _items(g, f): cnt[g[r][c]] = cnt.get(g[r][c], 0) + 1
        if not cnt: continue
        v = sorted(cnt.values())
        if len(v) > 1 and v[-1] == v[-2]: return None
        rect(out, *f[:4], max(cnt, key=cnt.get), fill=False)
    return out
rule("frame_takes_commonest_content_colour", "Each frame is repainted in the colour that occurs most often among the items inside it.", gi_majority, tf_majority)


# 17 histogram of item counts per frame
def gi_hist(rng):
    s = _scene_items(rng, (2, 5), (0, 7), iw=(2, 5), ih=(2, 6))
    if s is None: return None
    g, fr = s
    return g if sum(len(_items(g, f)) for f in fr) and len({f[1] for f in fr}) == len(fr) else None
def tf_hist(g):
    fr = sorted(_frames(g), key=lambda f: f[1]); ns = [len(_items(g, f)) for f in fr]
    if not fr or not max(ns): return None
    out = blank(max(ns), len(fr))
    for i, (f, n) in enumerate(zip(fr, ns)):
        for r in range(n): out[max(ns) - 1 - r][i] = f[4]
    return out
rule("frame_item_counts_as_bars", "Output one column per frame, frames taken left to right: a bottom-aligned bar in the frame's colour as tall as the number of items it holds.", gi_hist, tf_hist)


# 18 two frames exchange contents
def gi_swap(rng):
    s = _scene_items(rng, (2, 2), (1, 5), same=(rng.randint(2, 6), rng.randint(2, 6)))
    if s is None: return None
    g, fr = s
    return g if [g[r][c] for r, c in _interior(fr[0])] != [g[r][c] for r, c in _interior(fr[1])] else None
def tf_swap(g):
    fr = _frames(g)
    if len(fr) != 2: return None
    a, b = fr; out = copy(g)
    for (r, c), (y, x) in zip(_interior(a), _interior(b)): out[r][c], out[y][x] = g[y][x], g[r][c]
    return out
rule("two_frames_exchange_contents", "The two equal frames swap their contents: whatever lay inside the first now lies inside the second at the same offset, and vice versa.", gi_swap, tf_swap)


# 19 frame recoloured with its item count as a digit
def gi_countcol(rng):
    s = _scene_items(rng, (2, 4), (1, 9), ih=(2, 5), iw=(2, 5))
    if s is None: return None
    g, fr = s
    return g if len({len(_items(g, f)) for f in fr}) > 1 else None
def tf_countcol(g):
    fr = _frames(g); out = copy(g)
    if not fr: return None
    for f in fr:
        n = len(_items(g, f))
        if not 1 <= n <= 9: return None
        rect(out, *f[:4], n, fill=False)
    return out
rule("frame_recoloured_with_item_count", "Each frame's wall is recoloured with the digit equal to how many items it encloses.", gi_countcol, tf_countcol, digits=True)


# 20 the one occupied frame's contents are copied into every empty frame
def gi_copyall(rng):
    s = _scene_items(rng, (2, 4), (0, 0), same=(rng.randint(2, 5), rng.randint(2, 5)))
    if s is None: return None
    g, fr = s; src = rng.choice(fr)
    _fill_items(rng, g, src, rng.randint(1, 5), [c for c in COLOURS if c not in {f[4] for f in fr}])
    return g
def tf_copyall(g):
    fr = _frames(g); src = [f for f in fr if _items(g, f)]
    if len(src) != 1 or len(fr) < 2: return None
    s = src[0]; out = copy(g)
    for d in fr:
        for r, c in _items(g, s): out[r - s[0] + d[0]][c - s[1] + d[1]] = g[r][c]
    return out
rule("occupied_frame_contents_copied_to_empty_frames", "The contents of the single occupied frame are copied into every empty frame at the same offset, the original staying in place.", gi_copyall, tf_copyall)


# 21 the frame with the fewest items is erased, contents and all
def gi_fewest(rng):
    s = _scene_items(rng, (2, 4), (0, 6))
    if s is None: return None
    g, fr = s; ns = sorted(len(_items(g, f)) for f in fr)
    return g if ns[0] < ns[1] else None
def tf_fewest(g):
    fr = _frames(g)
    if len(fr) < 2: return None
    f = min(fr, key=lambda f: len(_items(g, f))); out = copy(g)
    rect(out, *f[:4], 0); return out
rule("frame_with_fewest_items_erased", "The frame holding the fewest items is erased together with everything inside it; the other frames are untouched.", gi_fewest, tf_fewest)


# 22 contents mirrored left-to-right within each frame
def gi_mirrorin(rng):
    s = _scene_items(rng, (1, 4), (1, 5), iw=(3, 7))
    if s is None: return None
    g, fr = s
    return g if any([g[r][c] for r, c in _interior(f)] != [g[r][f[1] + f[3] - c] for r, c in _interior(f)] for f in fr) else None
def tf_mirrorin(g):
    fr = _frames(g); out = copy(g)
    if not fr: return None
    for f in fr:
        for r, c in _interior(f): out[r][f[1] + f[3] - c] = g[r][c]
    return out
rule("contents_mirrored_inside_each_frame", "The contents of every frame are flipped left-to-right within the frame's interior; the frames themselves do not move.", gi_mirrorin, tf_mirrorin)


# 23 output the interior of the innermost nested frame
def gi_deepest(rng):
    h, w = _gsize(rng, 14); g = blank(h, w); d = rng.randint(2, 3)
    s = _nested(rng, g, d, [rng.choice(COLOURS) for _ in range(d)])
    if s is None: return None
    inner = s[-1]
    if inner[2] - inner[0] < 3 or inner[3] - inner[1] < 3: return None
    _fill_items(rng, g, inner, rng.randint(1, 4), [c for c in COLOURS if c != inner[4]], gap=1)
    for f in s[:-1]:
        for _ in range(rng.randint(0, 3)):
            r, c = rng.choice(_interior(f, 1))
            if g[r][c] == 0 and all(g[r + dr][c + dc] == 0 for dr in (-1, 0, 1) for dc in (-1, 0, 1)): g[r][c] = rng.choice(COLOURS)
    return g if _items(g, inner) else None
def tf_deepest(g):
    fr = _frames(g)
    if not fr: return None
    f = max(fr, key=lambda f: _depth(fr, f))
    if _depth(fr, f) < 1: return None
    return crop(g, f[0] + 1, f[1] + 1, f[2] - 1, f[3] - 1)
rule("deepest_frame_interior_cropped", "Output is the inside of the most deeply nested frame, without its wall.", gi_deepest, tf_deepest)


# 24 alternate bands between nested frames filled
def gi_bands(rng):
    h, w = _gsize(rng, 12); g = blank(h, w); n = 0
    for _ in range(rng.randint(1, 2)):
        d = rng.randint(2, 4); s = _nested(rng, g, d, [rng.choice([c for c in COLOURS if c != 8]) for _ in range(d)])
        if s: n += 1
    return g if n else None
def tf_bands(g):
    fr = _frames(g); out = copy(g)
    for f in fr:
        if _depth(fr, f) % 2 == 0 and any(_depth([f], o) for o in fr):
            for r, c in _interior(f):
                if not any(o[0] <= r <= o[2] and o[1] <= c <= o[3] for o in fr if _depth([f], o)): out[r][c] = 8
    return out if out != g else None
rule("alternate_nesting_bands_filled_grey", "Inside each nested set, the gap between the outermost frame and the next one in is filled with 8, the next gap is left empty, and so on alternating inward.", gi_bands, tf_bands)


# 25 loose dots of a frame's colour are gathered into that frame
def gi_gather(rng):
    h, w = _gsize(rng, 12); g = blank(h, w); k = rng.randint(1, 3); cols = colours(rng, k)
    fr = _place_frames(rng, g, k, (2, 5), (2, 5), m=2, cols=cols)
    if fr is None: return None
    for f in fr:
        n = rng.randint(1, min(5, len(_interior(f))))
        for _ in range(n):
            for _ in range(30):
                r, c = rng.randint(1, h - 2), rng.randint(1, w - 2)
                if g[r][c] == 0 and all(g[r + dr][c + dc] == 0 for dr in (-1, 0, 1) for dc in (-1, 0, 1)): g[r][c] = f[4]; break
    return g if sum(1 for _ in cells(g, lambda v: v != 0)) > sum(2 * (f[2] - f[0] + f[3] - f[1]) for f in fr) else None
def tf_gather(g):
    fr = _frames(g); out = copy(g); loose = [(r, c) for r, c in cells(g, lambda v: v != 0) if not any(f[0] <= r <= f[2] and f[1] <= c <= f[3] for f in fr)]
    if not fr or not loose: return None
    by = {f[4]: f for f in fr}
    if len(by) != len(fr): return None
    for col in by:
        pts = [p for p in loose if g[p[0]][p[1]] == col]; cells_ = _interior(by[col])
        if len(pts) > len(cells_): return None
        for (r, c), (y, x) in zip(pts, cells_): out[r][c] = 0; out[y][x] = col
    return out
rule("loose_dots_gathered_into_same_colour_frame", "Every loose dot moves into the frame of its own colour, the dots packing the frame's interior row by row from the top-left.", gi_gather, tf_gather)


# 26 contents of square frames rotate a quarter turn clockwise
def gi_rotin(rng):
    n = rng.randint(2, 6); s = _scene_items(rng, (1, 4), (1, 4), same=(n, n))
    if s is None: return None
    g, fr = s
    return g if any(crop(g, *f[:4]) != rot90(crop(g, *f[:4])) for f in fr) else None
def tf_rotin(g):
    fr = _frames(g); out = copy(g)
    if not fr: return None
    for f in fr:
        if f[2] - f[0] != f[3] - f[1]: return None
        paste(out, rot90(crop(g, f[0] + 1, f[1] + 1, f[2] - 1, f[3] - 1)), f[0] + 1, f[1] + 1)
    return out
rule("contents_rotate_quarter_turn_in_square_frame", "Inside every square frame the contents are turned a quarter turn clockwise about the frame's centre; the frames stay put.", gi_rotin, tf_rotin)


# 27 empty frames collapse to a single centre cell
def gi_collapse(rng):
    s = _scene_items(rng, (2, 5), (0, 3), ih=(3, 7), iw=(3, 7))
    if s is None: return None
    g, fr = s; e = [f for f in fr if not _items(g, f)]
    return g if 0 < len(e) else None
def tf_collapse(g):
    fr = _frames(g); out = copy(g); hit = False
    for f in fr:
        if not _items(g, f):
            rect(out, *f[:4], 0, fill=False); out[(f[0] + f[2]) // 2][(f[1] + f[3]) // 2] = f[4]; hit = True
    return out if hit else None
rule("empty_frames_collapse_to_centre_dot", "Every frame with nothing inside collapses to a single cell of its colour at its centre; frames holding items are kept.", gi_collapse, tf_collapse)


# 28 items slide to the nearest wall of their frame
def gi_cling(rng):
    s = _scene_items(rng, (1, 3), (1, 4), gap=1, ih=(4, 8), iw=(4, 8))
    if s is None: return None
    g, fr = s
    for f in fr:
        for r, c in _items(g, f):
            ds = sorted([r - f[0], f[2] - r, c - f[1], f[3] - c])
            if ds[0] == ds[1]: return None
    return g if any(_items(g, f) for f in fr) else None
def tf_cling(g):
    fr = _frames(g); out = copy(g)
    if not fr: return None
    for f in fr:
        for r, c in _items(g, f):
            ds = [(r - f[0], f[0] + 1, c), (f[2] - r, f[2] - 1, c), (c - f[1], r, f[1] + 1), (f[3] - c, r, f[3] - 1)]
            ds.sort()
            if ds[0][0] == ds[1][0]: return None
            out[r][c] = 0; _, y, x = ds[0]
            if out[y][x] and (y, x) != (r, c): return None
            out[y][x] = g[r][c]
    return out
rule("items_cling_to_nearest_frame_wall", "Each item inside a frame slides straight to the wall of its frame that is closest and stops against it.", gi_cling, tf_cling)


# 29 all contents packed into the largest frame
def gi_merge(rng):
    h, w = _gsize(rng, 12); g = blank(h, w); k = rng.randint(2, 4)
    big = _place_frames(rng, g, 1, (4, 8), (4, 8))
    small = _place_frames(rng, g, k - 1, (2, 3), (2, 3))
    if not big or not small: return None
    for f in small: _fill_items(rng, g, f, rng.randint(1, 3), [c for c in COLOURS if c != f[4]])
    _fill_items(rng, g, big[0], rng.randint(0, 2), [c for c in COLOURS if c != big[0][4]])
    tot = sum(len(_items(g, f)) for f in small + big)
    return g if tot and tot <= len(_interior(big[0])) else None
def tf_merge(g):
    fr = _frames(g)
    if len(fr) < 2: return None
    big = max(fr, key=lambda f: len(_interior(f))); seq = []
    for f in fr:
        for r, c in _items(g, f): seq.append(g[r][c])
    cells_ = _interior(big)
    if len(seq) > len(cells_): return None
    out = copy(g)
    for f in fr:
        for r, c in _items(g, f): out[r][c] = 0
    for (r, c), v in zip(cells_, seq): out[r][c] = v
    return out
rule("all_items_packed_into_largest_frame", "Every item from every frame is gathered into the largest frame, packed row by row from its top-left interior cell in the order the items were read.", gi_merge, tf_merge)


# 30 frame and its single-colour contents swap colours
def gi_swapcol(rng):
    h, w = _gsize(rng); g = blank(h, w)
    fr = _place_frames(rng, g, rng.randint(1, 4), (2, 6), (2, 6))
    if fr is None: return None
    for f in fr: _fill_items(rng, g, f, rng.randint(1, 5), [rng.choice([c for c in COLOURS if c != f[4]])], gap=1 if min(f[2] - f[0], f[3] - f[1]) > 3 else 0)
    return g if all(len({g[r][c] for r, c in _items(g, f)}) == 1 for f in _frames(g)) and len(_frames(g)) == len(fr) else None
def tf_swapcol(g):
    fr = _frames(g); out = copy(g)
    if not fr: return None
    for f in fr:
        it = _items(g, f); cs = {g[r][c] for r, c in it}
        if len(cs) != 1: return None
        ic = cs.pop(); rect(out, *f[:4], ic, fill=False)
        for r, c in it: out[r][c] = f[4]
    return out
rule("frame_and_contents_swap_colours", "Each frame takes the colour of the items inside it and those items take the frame's old colour.", gi_swapcol, tf_swapcol)


# 31 table of frame colour beside its content colour
def gi_table(rng):
    h, w = _gsize(rng); g = blank(h, w)
    fr = _place_frames(rng, g, rng.randint(2, 5), (2, 5), (2, 5))
    if fr is None or len({f[0] for f in fr}) != len(fr): return None
    for f in fr: _fill_items(rng, g, f, rng.randint(1, 4), [rng.choice([c for c in COLOURS if c != f[4]])], gap=1 if min(f[2] - f[0], f[3] - f[1]) > 3 else 0)
    return g if len(_frames(g)) == len(fr) else None
def tf_table(g):
    fr = sorted(_frames(g), key=lambda f: f[0]); out = []
    if len(fr) < 2 or len({f[0] for f in fr}) != len(fr): return None
    for f in fr:
        cs = {g[r][c] for r, c in _items(g, f)}
        if len(cs) != 1: return None
        out.append([f[4], cs.pop()])
    return out
rule("frame_colour_content_colour_table", "Output a two-column table with one row per frame from top to bottom: the frame's colour on the left and the colour of its contents on the right.", gi_table, tf_table)


# 32 all frames redrawn concentric about the largest
def gi_concentric(rng):
    h, w = _gsize(rng, 14); g = blank(h, w); k = rng.randint(2, 4); hs = sorted(rng.sample(range(2, 13, 2), k), reverse=True); ws = sorted(rng.sample(range(2, 13, 2), k), reverse=True)
    fr = []
    for i in range(k):
        f = _place_frames(rng, g, 1, (hs[i], hs[i]), (ws[i], ws[i]), m=1)
        if f is None: return None
        fr += f
    b = fr[0]; cy, cx = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    return g if len({f[4] for f in fr}) == k else None
def tf_concentric(g):
    fr = sorted(_frames(g), key=lambda f: -len(_interior(f)))
    if len(fr) < 2: return None
    b = fr[0]; out = blank(*dims(g)); rect(out, *b[:4], b[4], fill=False)
    for f in fr[1:]:
        h, w = f[2] - f[0], f[3] - f[1]
        if (b[2] - b[0] - h) % 2 or (b[3] - b[1] - w) % 2: return None
        r0 = b[0] + (b[2] - b[0] - h) // 2; c0 = b[1] + (b[3] - b[1] - w) // 2
        rect(out, r0, c0, r0 + h, c0 + w, f[4], fill=False)
    return out
rule("frames_nest_concentrically_in_largest", "Every smaller frame is moved to sit centred inside the largest frame, so all the frames become one concentric nest.", gi_concentric, tf_concentric)


# 33 a nested set is unpacked into a row, largest first
def gi_unnest(rng):
    h, w = _gsize(rng, 14); g = blank(h, w); d = rng.randint(2, 4)
    s = _nested(rng, g, d, [rng.choice(COLOURS) for _ in range(d)])
    if s is None or sum(f[3] - f[1] + 2 for f in s) - 1 > 30: return None
    return g
def tf_unnest(g):
    fr = sorted(_frames(g), key=lambda f: -len(_interior(f)))
    if len(fr) < 2: return None
    H = fr[0][2] - fr[0][0] + 1; W = sum(f[3] - f[1] + 2 for f in fr) - 1
    if W > 30: return None
    out = blank(H, W); x = 0
    for f in fr:
        rect(out, 0, x, f[2] - f[0], x + f[3] - f[1], f[4], fill=False); x += f[3] - f[1] + 2
    return out
rule("nested_frames_unpacked_into_row", "The nested frames are taken apart and laid side by side, top-aligned and one column apart, the outermost on the left and the innermost on the right.", gi_unnest, tf_unnest)


# 34 frame wall opens facing an outside dot
def gi_open(rng):
    h, w = _gsize(rng, 12); g = blank(h, w)
    fr = _place_frames(rng, g, rng.randint(1, 3), (2, 6), (2, 6), m=4)
    if fr is None: return None
    for f in fr:
        r0, c0, r1, c1, col = f; side = rng.randrange(4); d = rng.randint(2, 3)
        if side == 0: r, c = r0 - d, rng.randint(c0 + 1, c1 - 1)
        elif side == 1: r, c = r1 + d, rng.randint(c0 + 1, c1 - 1)
        elif side == 2: r, c = rng.randint(r0 + 1, r1 - 1), c0 - d
        else: r, c = rng.randint(r0 + 1, r1 - 1), c1 + d
        if not (0 <= r < h and 0 <= c < w) or g[r][c]: return None
        g[r][c] = rng.choice([x for x in COLOURS if x != col])
    return g
def tf_open(g):
    fr = _frames(g); out = copy(g)
    if not fr: return None
    dots = [(r, c) for r, c in cells(g, lambda v: v != 0) if not any(f[0] <= r <= f[2] and f[1] <= c <= f[3] for f in fr)]
    for f in fr:
        near = [(r, c) for r, c in dots if (f[1] < c < f[3] and (r < f[0] or r > f[2])) or (f[0] < r < f[2] and (c < f[1] or c > f[3]))]
        if len(near) != 1: return None
        r, c = near[0]
        if f[1] < c < f[3]: out[f[0] if r < f[0] else f[2]][c] = 0
        else: out[r][f[1] if c < f[1] else f[3]] = 0
    return out
rule("frame_wall_opens_toward_outside_dot", "Each frame has one dot outside it facing a wall; the wall cell directly in line with that dot is removed, opening the frame toward it.", gi_open, tf_open)


# 35 a dot aligned with the gap enters the frame and the gap seals
def gi_enter(rng):
    h, w = _gsize(rng, 12); g = blank(h, w)
    fr = _place_frames(rng, g, rng.randint(1, 3), (3, 6), (3, 6), m=4)
    if fr is None: return None
    for f in fr:
        r0, c0, r1, c1, col = f; side = rng.randrange(4); d = rng.randint(1, 3); dc = rng.choice([x for x in COLOURS if x != col])
        if side == 0: gr, gc, r, c = r0, rng.randint(c0 + 1, c1 - 1), r0 - d, None
        elif side == 1: gr, gc, r, c = r1, rng.randint(c0 + 1, c1 - 1), r1 + d, None
        elif side == 2: gr, gc, r, c = rng.randint(r0 + 1, r1 - 1), c0, None, c0 - d
        else: gr, gc, r, c = rng.randint(r0 + 1, r1 - 1), c1, None, c1 + d
        r = gr if r is None else r; c = gc if c is None else c
        if not (0 <= r < h and 0 <= c < w) or g[r][c]: return None
        g[gr][gc] = 0; g[r][c] = dc
    return g
def tf_enter(g):
    out = copy(g); hit = False
    for o in objects(g, 0, conn8=False):
        r0, c0, r1, c1 = bbox(o); col = g[o[0][0]][o[0][1]]
        if len(o) != 2 * (r1 - r0 + c1 - c0) - 1 or r1 - r0 < 2: continue
        gap = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if (r in (r0, r1) or c in (c0, c1)) and g[r][c] != col]
        if len(gap) != 1: continue
        gr, gc = gap[0]
        if gr == r0: dr, dc = -1, 0
        elif gr == r1: dr, dc = 1, 0
        elif gc == c0: dr, dc = 0, -1
        else: dr, dc = 0, 1
        y, x = gr + dr, gc + dc; H, W = dims(g)
        while 0 <= y < H and 0 <= x < W and g[y][x] == 0: y, x = y + dr, x + dc
        if not (0 <= y < H and 0 <= x < W): return None
        out[y][x] = 0; out[gr][gc] = col; out[gr - dr][gc - dc] = g[y][x]; hit = True
    return out if hit else None
rule("dot_enters_frame_through_gap_which_seals", "The dot in line with a frame's gap passes through it to the first cell inside, and the gap is sealed behind it in the frame colour.", gi_enter, tf_enter)


# 36 frames ranked by item count
def gi_rank(rng):
    s = _scene_items(rng, (2, 5), (0, 6), ih=(2, 5), iw=(2, 5))
    if s is None: return None
    g, fr = s; ns = [len(_items(g, f)) for f in fr]
    return g if len(set(ns)) == len(ns) else None
def tf_rank(g):
    fr = sorted(_frames(g), key=lambda f: -len(_items(g, f)))
    if len(fr) < 2 or len({len(_items(g, f)) for f in fr}) != len(fr): return None
    out = copy(g)
    for i, f in enumerate(fr): rect(out, *f[:4], i + 1, fill=False)
    return out
rule("frames_ranked_by_item_count", "The frames are recoloured by rank of how much they hold: the fullest frame becomes 1, the next fullest 2, and so on.", gi_rank, tf_rank, digits=True)


# 37 frame interior filled in frame colour, items become holes
def gi_holes(rng):
    s = _scene_items(rng, (1, 4), (1, 5), gap=0)
    if s is None: return None
    g, fr = s
    return g if len(_frames(g)) == len(fr) else None
def tf_holes(g):
    fr = _frames(g); out = copy(g)
    if not fr: return None
    for f in fr:
        for r, c in _interior(f): out[r][c] = 0 if g[r][c] else f[4]
    return out
rule("frame_filled_items_become_holes", "Each frame is filled solid in its own colour, except that every cell where an item sat is left empty, turning the items into holes.", gi_holes, tf_holes)


# 38 motif in a frame's top-left corner tiles the interior
def gi_tilein(rng):
    h, w = _gsize(rng, 12); g = blank(h, w); mh, mw = rng.randint(1, 3), rng.randint(1, 3); k = rng.randint(1, 3)
    if mh * mw < 2: mw = 2
    fr = _place_frames(rng, g, k, (mh * rng.randint(2, 4), mh * 4), (mw * rng.randint(2, 4), mw * 4), m=1)
    if fr is None: return None
    for f in fr:
        if (f[2] - f[0] - 1) % mh or (f[3] - f[1] - 1) % mw: return None
        for r in range(mh):
            for c in range(mw):
                if rng.random() < 0.6: g[f[0] + 1 + r][f[1] + 1 + c] = rng.choice([x for x in COLOURS if x != f[4]])
        if not any(g[f[0] + 1 + r][f[1] + 1 + c] for r in range(mh) for c in range(mw)): return None
    return g if len(_frames(g)) == k else None
def tf_tilein(g):
    fr = _frames(g); out = copy(g)
    if not fr: return None
    for f in fr:
        it = _items(g, f)
        if not it: return None
        r0, c0, r1, c1 = bbox(it)
        if (r0, c0) != (f[0] + 1, f[1] + 1): return None
        mh, mw = r1 - r0 + 1, c1 - c0 + 1
        if (f[2] - f[0] - 1) % mh or (f[3] - f[1] - 1) % mw: return None
        for r, c in _interior(f): out[r][c] = g[r0 + (r - r0) % mh][c0 + (c - c0) % mw]
    return out
rule("corner_motif_tiles_frame_interior", "The small motif in each frame's top-left interior corner is repeated to tile the whole interior of that frame.", gi_tilein, tf_tilein)


# 39 items project onto the right wall of their frame
def gi_project(rng):
    s = _scene_items(rng, (1, 4), (1, 5), ih=(3, 7))
    if s is None: return None
    g, fr = s
    for f in fr:
        rows = [r for r, c in _items(g, f)]
        if len(rows) != len(set(rows)): return None
    return g if any(_items(g, f) for f in fr) else None
def tf_project(g):
    fr = _frames(g); out = copy(g)
    if not fr: return None
    for f in fr:
        rows = {}
        for r, c in _items(g, f): rows.setdefault(r, []).append(g[r][c])
        for r, vs in rows.items():
            if len(vs) != 1: return None
            out[r][f[3]] = vs[0]
    return out
rule("items_project_colour_onto_right_wall", "Each item paints the cell of its frame's right wall on its own row with its colour.", gi_project, tf_project)


# 40 crop the frame with the most items
def gi_cropfull(rng):
    s = _scene_items(rng, (2, 4), (0, 6))
    if s is None: return None
    g, fr = s; ns = sorted(len(_items(g, f)) for f in fr)
    return g if ns[-1] > ns[-2] else None
def tf_cropfull(g):
    fr = _frames(g)
    if len(fr) < 2: return None
    ns = sorted(len(_items(g, f)) for f in fr)
    if ns[-1] == ns[-2]: return None
    return crop(g, *max(fr, key=lambda f: len(_items(g, f)))[:4])
rule("crop_frame_with_most_items", "Output is the frame that holds the most items, wall included, with its contents.", gi_cropfull, tf_cropfull)
