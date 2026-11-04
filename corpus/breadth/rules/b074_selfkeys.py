# b074_selfkeys.py -- OBJECTS THAT CARRY THEIR OWN INSTRUCTION: the parameter that decides what happens to an object is
# part of the object itself: a marker cell on one side (direction), a count of cells of a second colour (distance), an
# attached tail (copies or throw), a notch (cut), a cap colour, a digit cell, a gap in a frame, a head on a bar.
# Objects with no instruction stay. Moving objects are processed in reading order of their topmost-then-leftmost cell.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

UP, DOWN, LEFT, RIGHT = (-1, 0), (1, 0), (0, -1), (0, 1)
DIRS = [UP, DOWN, LEFT, RIGHT]


def D(rng, lo=8, hi=30):
    if hi >= 21 and rng.random() < 0.45:
        return rng.randint(21, hi)
    return rng.randint(lo, min(hi, 20))


def src(rng, ex=(0,)):
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


def scene(subfn, kmin=2, kmax=4, lo=10, margin=1, per=110):
    def gen(rng):
        H, Wd = D(rng, lo, 30), D(rng, lo, 30); k = rng.randint(kmin, max(kmin, min(kmax, 1 + H * Wd // per))); subs = []
        for _ in range(k):
            s = subfn(rng)
            if s is None: return None
            subs.append(s)
        return scatter_subs(rng, H, Wd, subs, margin)
    return gen


def _mc(g):
    H, W = dims(g); seen = set(); out = []
    for r in range(H):
        for c in range(W):
            if g[r][c] and (r, c) not in seen:
                st = [(r, c)]; seen.add((r, c)); cm = []
                while st:
                    y, x = st.pop(); cm.append((y, x))
                    for dr, dc in N4:
                        ny, nx = y + dr, x + dc
                        if 0 <= ny < H and 0 <= nx < W and g[ny][nx] and (ny, nx) not in seen: seen.add((ny, nx)); st.append((ny, nx))
                out.append(sorted(cm))
    return sorted(out, key=lambda c: c[0])


N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


def body_col(g, cm, ex=()):
    cnt = {}
    for r, c in cm:
        if g[r][c] not in ex: cnt[g[r][c]] = cnt.get(g[r][c], 0) + 1
    return max(cnt, key=cnt.get) if cnt else None


def side_dir(p, b):
    r0, c0, r1, c1 = b
    if p[0] == r0: return UP
    if p[0] == r1: return DOWN
    if p[1] == c0: return LEFT
    if p[1] == c1: return RIGHT
    return None


def slide(g2, cm, d, maxn=None):
    H, W = dims(g2); vals = {p: g2[p[0]][p[1]] for p in cm}
    for r, c in cm: g2[r][c] = 0
    n = 0
    while maxn is None or n < maxn:
        if any(not (0 <= r + d[0] * (n + 1) < H and 0 <= c + d[1] * (n + 1) < W) or g2[r + d[0] * (n + 1)][c + d[1] * (n + 1)] for r, c in cm): break
        n += 1
    for (r, c), v in vals.items(): g2[r + d[0] * n][c + d[1] * n] = v
    return n


def mover(info):
    """info(g, cells) -> None (stay) | 'bad' | (direction, maxsteps or None, consume_cells list)"""
    def tf(g):
        g2 = copy(g); cms = _mc(g)
        if not cms: return None
        for cm in cms:
            i = info(g, cm)
            if i == 'bad': return None
            if i is None: continue
            d, mx = i[0], i[1]
            n = slide(g2, cm, d, mx)
            if len(i) > 2:
                for p in i[2]:
                    g2[p[0] + d[0] * n][p[1] + d[1] * n] = i[3]
        return g2
    return tf


def rect_sub(rng, marks, hlo=3, hhi=6, wlo=3, whi=6, ex=()):
    """solid body with markers [(colour, side index)] on edge cells (non-corner)"""
    h, w = rng.randint(hlo, hhi), rng.randint(wlo, whi); a = src(rng, (0,) + ex + tuple(m[0] for m in marks))
    g = [[a] * w for _ in range(h)]
    for col, s in marks:
        r, c = [(0, rng.randint(1, w - 2)), (h - 1, rng.randint(1, w - 2)), (rng.randint(1, h - 2), 0), (rng.randint(1, h - 2), w - 1)][s]
        g[r][c] = col
    return g


def marked(rng, ncs=(0, 1), mcol=2, ex=()):
    n = rng.choice(ncs); return rect_sub(rng, [(mcol, rng.randrange(4))] if n else [], ex=ex + (mcol,))


# ============================================================ marker on a side = direction
def info_dir(mc=2):
    def info(g, cm):
        ms = [p for p in cm if g[p[0]][p[1]] == mc]
        if not ms: return None
        if len(ms) > 1: return 'bad'
        return side_dir(ms[0], bbox(cm)), None
    return info
t1 = mover(info_dir())
rule("move_toward_marker_side_until_blocked", "Each rectangle has at most one colour-2 marker cell on one of its edges; the rectangle slides in the direction of the side the marker sits on, until the grid edge or another object blocks it; objects are moved one at a time in reading order of their topmost-then-leftmost cell (each sees the others where they currently are), and rectangles with no marker stay.",
     mk(scene(marked), t1), t1)


def info_one(g, cm):
    ms = [p for p in cm if g[p[0]][p[1]] == 2]
    if not ms: return None
    if len(ms) > 1: return 'bad'
    b = bbox(cm); a = body_col(g, cm, (2,))
    return side_dir(ms[0], b), 1, ms, a
t13 = mover(info_one)
rule("marker_moves_one_step_then_vanishes", "Each rectangle has at most one colour-2 marker cell on an edge; the rectangle moves exactly one cell toward the side the marker sits on, and the marker is consumed (its cell takes the rectangle's colour); rectangles with no marker stay; a rectangle that cannot move one cell (grid edge or object in the way) stays where it is.",
     mk(scene(lambda r: marked(r, (1,)), 2, 3, 10, 2), t13), t13)


def info_prio(g, cm):
    m3 = [p for p in cm if g[p[0]][p[1]] == 3]; m2 = [p for p in cm if g[p[0]][p[1]] == 2]
    ms = m3 if m3 else m2
    if not ms: return None
    if len(ms) > 1: return 'bad'
    return side_dir(ms[0], bbox(cm)), None
t11 = mover(info_prio)


def prio_sub(rng):
    k = rng.choice((0, 1, 2, 2)); sides = rng.sample(range(4), 2)
    return rect_sub(rng, [(2, sides[0]), (3, sides[1])][:k] if k == 2 else ([(rng.choice((2, 3)), sides[0])] if k else []), ex=(2, 3))
rule("two_markers_colour_three_wins", "A rectangle may carry a colour-2 marker, a colour-3 marker, or both (on different sides); it slides toward the side of its colour-3 marker if it has one, otherwise toward its colour-2 marker, until the grid edge or another object blocks it; objects move one at a time in reading order of their topmost-then-leftmost cell and unmarked rectangles stay.",
     mk(scene(prio_sub), t11), t11)


def info_cancel(g, cm):
    ms = [p for p in cm if g[p[0]][p[1]] == 2]; b = bbox(cm)
    if not ms: return None
    if len(ms) == 1: return side_dir(ms[0], b), None
    if len(ms) == 2:
        d1, d2 = side_dir(ms[0], b), side_dir(ms[1], b)
        if d1 and d2 and (d1[0] + d2[0], d1[1] + d2[1]) == (0, 0): return 'cancel'
    return 'bad'


def t12(g):
    g2 = copy(g); cms = _mc(g)
    if not cms: return None
    for cm in cms:
        i = info_cancel(g, cm)
        if i == 'bad': return None
        if i is None: continue
        if i == 'cancel':
            for r, c in cm:
                if g[r][c] != 2: g2[r][c] = 5
        else: slide(g2, cm, i[0], None)
    return g2


def cancel_sub(rng):
    k = rng.choice((1, 1, 2, 2)); s = rng.randrange(4)
    return rect_sub(rng, [(2, s)] if k == 1 else [(2, s), (2, s ^ 1)], ex=(2, 5))
rule("opposite_markers_cancel_to_grey", "A rectangle has one or two colour-2 marker cells: with one marker it slides toward the marker's side until the grid edge or another object blocks it (objects move one at a time in reading order of their topmost-then-leftmost cell); with two markers on opposite sides it does not move and its body cells turn colour 5.",
     mk(scene(cancel_sub), t12), t12)


def info_cdir(g, cm):
    d = {2: UP, 3: DOWN, 4: LEFT, 6: RIGHT}; ms = [p for p in cm if g[p[0]][p[1]] in d]
    if not ms: return None
    if len(ms) > 1: return 'bad'
    return d[g[ms[0][0]][ms[0][1]]], None
t20 = mover(info_cdir)
rule("marker_colour_names_the_direction", "Each rectangle has one marker cell on its edge whose colour gives the direction (2 = up, 3 = down, 4 = left, 6 = right, wherever the marker sits); the rectangle slides that way until the grid edge or another object blocks it, objects moving one at a time in reading order of their topmost-then-leftmost cell.",
     mk(scene(lambda r: rect_sub(r, [(r.choice((2, 3, 4, 6)), r.randrange(4))], ex=(2, 3, 4, 6))), t20), t20)


def info_val(g, cm):
    ms = [p for p in cm if g[p[0]][p[1]] in (1, 2, 3, 4)]
    if not ms: return None
    if len(ms) > 1: return 'bad'
    return side_dir(ms[0], bbox(cm)), g[ms[0][0]][ms[0][1]]
t25 = mover(info_val)
rule("marker_value_is_the_step_count", "Each rectangle (colours 5-9) has one marker cell of value d (1-4) on an edge; the rectangle slides d cells toward the side the marker sits on, stopping early if the grid edge or another object blocks it; objects move one at a time in reading order of their topmost-then-leftmost cell.",
     mk(scene(lambda r: rect_sub(r, [(r.randint(1, 4), r.randrange(4))], ex=(1, 2, 3, 4)) ), t25), t25, digits=True)


# ============================================================ counts of a second colour, eyes, frame gaps, bars with heads
def cnt_sub(rng, mark=False, kmax=4):
    h, w = rng.randint(3, 6), rng.randint(3, 6); a = src(rng, (0, 2, 3)); g = [[a] * w for _ in range(h)]
    cs = [(r, c) for r in range(h) for c in range(w)]
    if mark:
        r, c = [(0, rng.randint(1, w - 2)), (h - 1, rng.randint(1, w - 2)), (rng.randint(1, h - 2), 0), (rng.randint(1, h - 2), w - 1)][rng.randrange(4)]
        g[r][c] = 3; cs.remove((r, c))
    for r, c in rng.sample([p for p in cs if not (mark and False)], rng.randint(1, kmax)): g[r][c] = 2
    return g


def info_cnt_fixed(g, cm):
    k = sum(1 for r, c in cm if g[r][c] == 2)
    return (RIGHT, k) if k else None
t2 = mover(info_cnt_fixed)
rule("move_right_by_number_of_colour_two_cells", "Each rectangle contains k cells of colour 2 among its body cells; the whole rectangle slides k cells to the right, stopping early if the grid edge or another object blocks it; objects move one at a time in reading order of their topmost-then-leftmost cell.",
     mk(scene(cnt_sub), t2), t2)


def info_cnt_dir(g, cm):
    k = sum(1 for r, c in cm if g[r][c] == 2); m = [p for p in cm if g[p[0]][p[1]] == 3]
    if len(m) != 1 or not k: return 'bad'
    return side_dir(m[0], bbox(cm)), k
t3 = mover(info_cnt_dir)
rule("move_toward_marker_by_colour_two_count", "Each rectangle has one colour-3 marker cell on an edge and k cells of colour 2 inside its body; it slides k cells toward the side the marker sits on, stopping early if the grid edge or another object blocks it; objects move one at a time in reading order of their topmost-then-leftmost cell.",
     mk(scene(lambda r: cnt_sub(r, True)), t3), t3)


def tf_cnt_col(g):
    out = copy(g)
    for cm in _mc(g):
        k = sum(1 for r, c in cm if g[r][c] == 2)
        if not 1 <= k <= 4: return None
        for r, c in cm: out[r][c] = k
    return out
rule("body_takes_colour_equal_to_its_count", "Each rectangle has k cells (1-4) of colour 2 among its body cells; the whole rectangle, those cells included, is repainted with colour k.",
     mk(scene(lambda r: (lambda g: [[v if v == 2 else r.randint(5, 9) if False else v for v in row] for row in g])(cnt_sub(r))), tf_cnt_col), tf_cnt_col, digits=True)


def eye_sub(rng):
    h, w = rng.randint(5, 9), rng.randint(5, 9); a = src(rng, (0, 2)); g = [[a] * w for _ in range(h)]
    r, c = rng.randint(1, h - 2), rng.randint(1, w - 2); g[r][c] = 2; return g


def info_eye(g, cm):
    e = [p for p in cm if g[p[0]][p[1]] == 2]
    if len(e) != 1: return 'bad'
    r0, c0, r1, c1 = bbox(cm); r, c = e[0]; ds = [(r - r0, UP), (r1 - r, DOWN), (c - c0, LEFT), (c1 - c, RIGHT)]
    m = min(d[0] for d in ds)
    if sum(1 for d in ds if d[0] == m) != 1: return 'bad'
    return [d[1] for d in ds if d[0] == m][0], None
t_eye = mover(info_eye)
rule("rectangle_slides_toward_its_eye", "Each rectangle has one colour-2 cell (an eye) strictly inside its body; the rectangle slides toward the side of its bounding box that the eye is nearest to, until the grid edge or another object blocks it (inputs never have the eye equally near two sides); objects move one at a time in reading order of their topmost-then-leftmost cell.",
     mk(scene(eye_sub), t_eye), t_eye)


def frame_sub(rng):
    h, w = rng.randint(4, 7), rng.randint(4, 7); a = src(rng); g = blank(h, w)
    rect(g, 0, 0, h - 1, w - 1, a, fill=False); s = rng.randrange(4)
    r, c = [(0, rng.randint(1, w - 2)), (h - 1, rng.randint(1, w - 2)), (rng.randint(1, h - 2), 0), (rng.randint(1, h - 2), w - 1)][s]
    g[r][c] = 0; return g


def info_gap(g, cm):
    r0, c0, r1, c1 = bbox(cm); S = set(cm)
    gaps = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if (r in (r0, r1) or c in (c0, c1)) and (r, c) not in S]
    if len(gaps) != 1: return 'bad'
    return side_dir(gaps[0], (r0, c0, r1, c1)), None
t_gap = mover(info_gap)
rule("frame_slides_toward_its_gap", "Each hollow rectangular frame has a one-cell gap in one of its four walls; the frame slides in the direction of the wall that holds the gap, until the grid edge or another object blocks it; objects move one at a time in reading order of their topmost-then-leftmost cell.",
     mk(scene(frame_sub), t_gap), t_gap)


def bar_sub(rng):
    L = rng.randint(2, 6); a = src(rng, (0, 2)); g = [[a] * L + [0]]; g = [[a] * L]
    s = rng.randrange(4)
    g = [[a] * L]; 
    if s in (0, 1): g = [[a] * L]; g[0][0 if s == 0 else L - 1] = 2
    else:
        g = [[a] * L]; g[0][0 if s == 2 else L - 1] = 2; g = transpose(g)
    return g if s < 2 else g


def bar_dir(g, cm):
    h = [p for p in cm if g[p[0]][p[1]] == 2]
    if len(h) != 1: return None
    r0, c0, r1, c1 = bbox(cm); r, c = h[0]
    if r0 == r1: return (LEFT if c == c0 else RIGHT), c1 - c0 + 1
    return (UP if r == r0 else DOWN), r1 - r0 + 1


def info_barlen(g, cm):
    i = bar_dir(g, cm); return None if i is None else (i[0], i[1])
t_bar = mover(info_barlen)
rule("bar_leaps_its_own_length_toward_head", "Each straight bar of 2 to 6 cells has a colour-2 head cell at one end; the bar slides toward the head's end by as many cells as the bar is long, stopping early if the grid edge or another object blocks it; objects move one at a time in reading order of their topmost-then-leftmost cell.",
     mk(scene(bar_sub), t_bar), t_bar)


def tf_head(g):
    out = copy(g); H, W = dims(g)
    for cm in _mc(g):
        i = bar_dir(g, cm)
        if i is None: continue
        d = i[0]; h = [p for p in cm if g[p[0]][p[1]] == 2][0]; a = body_col(g, cm, (2,))
        r, c = h; out[r][c] = a; r += d[0]; c += d[1]
        while 0 <= r < H and 0 <= c < W and out[r][c] == 0: out[r][c] = a; r += d[0]; c += d[1]
        out[r - d[0]][c - d[1]] = 2
    return out
rule("bar_grows_forward_head_moves_to_tip", "Each straight bar has a colour-2 head cell at one end; the bar grows forward from the head, in its body colour, through empty cells until the grid edge or another object, and the colour-2 head ends up on the new tip (the old head cell takes the body colour).",
     mk(scene(bar_sub, 2, 4), tf_head), tf_head)


# ============================================================ caps, tails, notches
def cap_sub(rng):
    h, w = rng.randint(2, 6), rng.randint(2, 6); a = src(rng); c = src(rng, (0, a)); s = rng.randrange(4)
    g = blank(h + 2, w + 2); rect(g, 1, 1, h, w, a)
    pos = [(0, 1 + w // 2), (h + 1, 1 + w // 2), (1 + h // 2, 0), (1 + h // 2, w + 1)][s]; g[pos[0]][pos[1]] = c; return g


def tf_cap(g):
    out = copy(g)
    for cm in _mc(g):
        cnt = {}
        for r, c in cm: cnt[g[r][c]] = cnt.get(g[r][c], 0) + 1
        caps = [v for v, n in cnt.items() if n == 1]
        if len(cnt) != 2 or len(caps) != 1: return None
        cap = caps[0]
        for r, c in cm: out[r][c] = 0 if g[r][c] == cap else cap
    return out
rule("body_takes_cap_colour_cap_removed", "Each rectangle has a one-cell cap of another colour touching the middle of one side; the rectangle is repainted in the cap's colour and the cap cell is erased.",
     mk(scene(cap_sub, 2, 5), tf_cap), tf_cap)


def tail_sub(rng):
    s = rng.randint(2, 3); L = rng.randint(1, 3); a = src(rng, (0, 2)); d = rng.randrange(4); m = 6
    g = blank(2 * m, 2 * m); R0 = m - 1
    rect(g, R0, R0, R0 + s - 1, R0 + s - 1, a)
    for i in range(1, L + 1):
        r, c = [(R0 - i, R0 + 1), (R0 + s - 1 + i, R0 + 1), (R0 + 1, R0 - i), (R0 + 1, R0 + s - 1 + i)][d]; g[r][c] = 2
    cs = [(r, c) for r in range(2 * m) for c in range(2 * m) if g[r][c]]; r0, c0, r1, c1 = bbox(cs)
    return crop(g, r0, c0, r1, c1)


def tf_tail(g):
    H, W = dims(g); out = copy(g); cms = _mc(g)
    if not cms: return None
    new = []
    for cm in cms:
        t = [p for p in cm if g[p[0]][p[1]] == 2]; b = [p for p in cm if g[p[0]][p[1]] != 2]
        if not t or not b: return None
        a = g[b[0][0]][b[0][1]]; r0, c0, r1, c1 = bbox(b); s = r1 - r0 + 1
        tr, tc = t[0]
        d = UP if tr < r0 else DOWN if tr > r1 else LEFT if tc < c0 else RIGHT
        for r, c in t: out[r][c] = 0
        for k in range(1, len(t) + 1):
            for r, c in b: new.append((r + d[0] * k * (s + 1), c + d[1] * k * (s + 1), a))
    for r, c, a in new:
        if not (0 <= r < H and 0 <= c < W): return None
        out[r][c] = a
    return out
rule("tail_length_is_the_copy_count", "Each square block (side 2 or 3) has a straight tail of colour 2, L cells long, attached at the middle of one side; the tail is erased and L copies of the block are stamped one after another in the direction the tail points, each copy one empty cell away from the previous one.",
     mk(scene(tail_sub, 1, 2, 14, 1, 200), tf_tail), tf_tail)


def tf_throw(g):
    g2 = copy(g); cms = _mc(g)
    if not cms: return None
    for cm in cms:
        t = [p for p in cm if g[p[0]][p[1]] == 2]; b = [p for p in cm if g[p[0]][p[1]] != 2]
        if not t or not b: return None
        r0, c0, r1, c1 = bbox(b); tr, tc = t[0]
        d = UP if tr < r0 else DOWN if tr > r1 else LEFT if tc < c0 else RIGHT
        for r, c in t: g2[r][c] = 0
        slide(g2, b, (-d[0], -d[1]), len(t))
    return g2


def throw_sub(rng):
    s = tail_sub(rng); return s
rule("block_thrown_away_from_its_tail", "Each block has a straight colour-2 tail of L cells attached to one side; the tail is erased and the block moves L cells in the direction opposite to the tail (away from it), stopping early if the grid edge or another object blocks it; blocks move one at a time in reading order of their topmost-then-leftmost cell.",
     mk(scene(throw_sub, 2, 3, 14, 1, 150), tf_throw), tf_throw)


def notch_sub(rng):
    h, w = rng.randint(5, 9), rng.randint(5, 9); a = src(rng); g = [[a] * w for _ in range(h)]
    if rng.random() < .5: g[0][rng.randint(2, w - 3)] = 0
    else: g[rng.randint(2, h - 3)][0] = 0
    return g


def notch_of(g, cm):
    S = set(cm); r0, c0, r1, c1 = bbox(cm)
    n = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if (r, c) not in S and (r in (r0, r1) or c in (c0, c1))]
    if len(n) != 1: return None
    r, c = n[0]
    return ('col', c) if r == r0 else ('row', r) if c == c0 else None


def tf_split(apart):
    def tf(g):
        out = copy(g); H, W = dims(g); cms = _mc(g)
        if not cms: return None
        new = []
        for cm in cms:
            n = notch_of(g, cm)
            if not n: return None
            for r, c in cm: out[r][c] = 0
            col = g[cm[0][0]][cm[0][1]]
            for r, c in cm:
                if n[0] == 'col':
                    if c == n[1]: continue
                    new.append((r, c + (0 if not apart else (-1 if c < n[1] else 1)), col))
                else:
                    if r == n[1]: continue
                    new.append((r + (0 if not apart else (-1 if r < n[1] else 1)), c, col))
        for r, c, v in new:
            if not (0 <= r < H and 0 <= c < W): return None
            out[r][c] = v
        return out
    return tf
tsp = tf_split(False); tsa = tf_split(True)
rule("split_the_rectangle_along_its_notch", "Each rectangle has a one-cell notch in its top edge or its left edge; the whole column (for a top notch) or row (for a left notch) through the notch is erased, splitting the rectangle in two.",
     mk(scene(notch_sub, 1, 3, 12, 1, 130), tsp), tsp)
rule("split_along_notch_and_halves_pushed_apart", "Each rectangle has a one-cell notch in its top edge or its left edge; the column (top notch) or row (left notch) through the notch is erased and the two parts each move one cell away from the cut, left part left and right part right for a column, upper part up and lower part down for a row.",
     mk(scene(notch_sub, 1, 3, 12, 2, 130), tsa), tsa)


def tf_grow_side(g):
    out = copy(g); H, W = dims(g); cms = _mc(g)
    if not cms: return None
    for cm in cms:
        ms = [p for p in cm if g[p[0]][p[1]] == 2]
        if len(ms) != 1: return None
        r0, c0, r1, c1 = bbox(cm); d = side_dir(ms[0], (r0, c0, r1, c1)); a = body_col(g, cm, (2,))
        cells_ = [(r0 - 1, c) for c in range(c0, c1 + 1)] if d == UP else [(r1 + 1, c) for c in range(c0, c1 + 1)] if d == DOWN else [(r, c0 - 1) for r in range(r0, r1 + 1)] if d == LEFT else [(r, c1 + 1) for r in range(r0, r1 + 1)]
        for r, c in cells_:
            if not (0 <= r < H and 0 <= c < W) or g[r][c]: return None
            out[r][c] = a
    return out
rule("rectangle_grows_on_its_marker_side", "Each rectangle has one colour-2 marker cell on an edge; the rectangle gains one extra row or column of its body colour along the whole side where the marker sits (the marker stays in place).",
     mk(scene(lambda r: marked(r, (1,)), 2, 4, 10, 2), tf_grow_side), tf_grow_side)


def tf_line(g):
    out = copy(g)
    for cm in _mc(g):
        ms = [p for p in cm if g[p[0]][p[1]] == 2]
        if len(ms) != 1: return None
        r0, c0, r1, c1 = bbox(cm); d = side_dir(ms[0], (r0, c0, r1, c1)); r, c = ms[0]
        for p in cm:
            if (d in (UP, DOWN) and p[1] == c) or (d in (LEFT, RIGHT) and p[0] == r): out[p[0]][p[1]] = 2
    return out
rule("marker_line_drawn_straight_across_body", "Each rectangle has one colour-2 marker cell on an edge; a line of colour 2 is drawn from the marker straight across the rectangle to the opposite edge, replacing the body cells it crosses.",
     mk(scene(lambda r: marked(r, (1,))), tf_line), tf_line)


def tf_ray(g):
    out = copy(g); H, W = dims(g)
    for cm in _mc(g):
        ms = [p for p in cm if g[p[0]][p[1]] == 2]
        if len(ms) != 1: return None
        d = side_dir(ms[0], bbox(cm)); r, c = ms[0][0] + d[0], ms[0][1] + d[1]
        while 0 <= r < H and 0 <= c < W and g[r][c] == 0: out[r][c] = 2; r += d[0]; c += d[1]
    return out
rule("marker_shoots_ray_out_of_the_body", "Each rectangle has one colour-2 marker cell on an edge; from the marker a ray of colour 2 runs straight outward, away from the rectangle, through empty cells until the grid edge or another object.",
     mk(scene(lambda r: marked(r, (1,)), 2, 4, 10, 1), tf_ray), tf_ray)


def hollow_sub(rng):
    h, w = rng.randint(3, 7), rng.randint(3, 7); a = src(rng, (0, 2)); g = [[a] * w for _ in range(h)]
    if rng.random() < .5: g[rng.choice((0, h - 1))][rng.choice((0, w - 1))] = 2
    else: return rect_sub(rng, [(2, rng.randrange(4))], 3, 7, 3, 7, ex=(2,))
    return g


def tf_hollow(g):
    out = copy(g)
    for cm in _mc(g):
        ms = [p for p in cm if g[p[0]][p[1]] == 2]
        if len(ms) != 1: return None
        r0, c0, r1, c1 = bbox(cm); m = ms[0]
        if m in ((r0, c0), (r0, c1), (r1, c0), (r1, c1)):
            for r in range(r0 + 1, r1):
                for c in range(c0 + 1, c1): out[r][c] = 0
    return out
rule("corner_marker_hollows_the_rectangle", "Each rectangle has one colour-2 marker cell: if the marker sits on a corner cell the rectangle is hollowed out (everything except its outer ring of cells is erased); if the marker sits on a non-corner edge cell the rectangle is unchanged.",
     mk(scene(hollow_sub, 2, 4), tf_hollow), tf_hollow)


# ============================================================ pattern objects: flip, rotate, mirror copy
def patt_sub(rng, marker=True, square=False, k=0):
    h, w = rng.randint(3, 6), rng.randint(3, 6)
    if square: w = h
    a, b = rng.sample([c for c in range(1, 10) if c not in (2, 4)], 2); g = [[rng.choice((a, b)) for _ in range(w)] for _ in range(h)]
    if marker:
        r, c = [(0, rng.randint(1, w - 2)), (h - 1, rng.randint(1, w - 2)), (rng.randint(1, h - 2), 0), (rng.randint(1, h - 2), w - 1)][rng.randrange(4)]
        g[r][c] = 4
    return g


def tf_flip(g):
    out = copy(g); H, W = dims(g)
    for cm in _mc(g):
        ms = [p for p in cm if g[p[0]][p[1]] == 4]
        if len(ms) != 1: return None
        r0, c0, r1, c1 = bbox(cm); d = side_dir(ms[0], (r0, c0, r1, c1)); sub = crop(g, r0, c0, r1, c1)
        paste(out, flip_h(sub) if d in (LEFT, RIGHT) else flip_v(sub), r0, c0)
    return out
rule("flip_across_the_axis_of_the_marker_side", "Each patterned rectangle has one colour-4 marker on an edge: if it sits on the left or right edge the rectangle is mirrored left-right, if on the top or bottom edge it is mirrored top-bottom (the marker is mirrored with the rest and so ends on the opposite edge).",
     mk(scene(patt_sub), tf_flip), tf_flip)


def tf_mcopy(g):
    out = copy(g); H, W = dims(g)
    for cm in _mc(g):
        ms = [p for p in cm if g[p[0]][p[1]] == 4]
        if len(ms) != 1: return None
        r0, c0, r1, c1 = bbox(cm); d = side_dir(ms[0], (r0, c0, r1, c1)); sub = crop(g, r0, c0, r1, c1)
        m = flip_v(sub) if d in (UP, DOWN) else flip_h(sub); h, w = dims(m)
        pr, pc = (r0 - h, c0) if d == UP else (r1 + 1, c0) if d == DOWN else (r0, c0 - w) if d == LEFT else (r0, c1 + 1)
        if pr < 0 or pc < 0 or pr + h > H or pc + w > W: return None
        for r in range(h):
            for c in range(w):
                if g[pr + r][pc + c]: return None
        paste(out, m, pr, pc)
    return out
rule("mirror_copy_placed_on_the_marker_side", "Each patterned rectangle has one colour-4 marker on an edge; a mirror image of the whole rectangle (marker included) is placed flush against the side where the marker sits, reflected across that side.",
     mk(scene(patt_sub, 1, 3, 12, 1, 220), tf_mcopy), tf_mcopy)


def rot_sub(rng):
    n = rng.randint(3, 5); g = [[rng.randint(5, 9) for _ in range(n)] for _ in range(n)]; g[0][0] = rng.randint(1, 3); return g


def tf_rotd(g):
    out = copy(g)
    for cm in _mc(g):
        r0, c0, r1, c1 = bbox(cm); sub = crop(g, r0, c0, r1, c1); d = sub[0][0]
        if r1 - r0 != c1 - c0 or not 1 <= d <= 3: return None
        sub[0][0] = 5
        for _ in range(d): sub = rot90(sub)
        # the digit cell's slot is the rotated image of the top-left corner
        dr, dc = {1: (0, r1 - r0), 2: (r1 - r0, c1 - c0), 3: (c1 - c0, 0)}[d]
        sub[dr][dc] = 0; paste(out, sub, r0, c0)
    return out
rule("digit_cell_is_the_rotation_count", "Each square block has a digit d (1-3) in its top-left cell and colours 5-9 elsewhere; the block is rotated clockwise by d quarter turns, and the digit cell (which travels with the rotation) is erased, leaving an empty cell.",
     mk(scene(rot_sub), tf_rotd), tf_rotd, digits=True)


def rotk_sub(rng):
    n = rng.randint(3, 5); a, b = rng.sample([c for c in range(1, 10) if c != 2], 2)
    g = [[rng.choice((a, b)) for _ in range(n)] for _ in range(n)]
    for r, c in rng.sample([(r, c) for r in range(n) for c in range(n)], rng.randint(1, 3)): g[r][c] = 2
    return g


def tf_rotk(g):
    out = copy(g)
    for cm in _mc(g):
        r0, c0, r1, c1 = bbox(cm); sub = crop(g, r0, c0, r1, c1); k = sum(1 for row in sub for v in row if v == 2)
        if r1 - r0 != c1 - c0 or len(cm) != (r1 - r0 + 1) ** 2 or k not in (1, 2, 3): return None
        for _ in range(k): sub = rot90(sub)
        paste(out, sub, r0, c0)
    return out
rule("colour_two_count_is_the_quarter_turns", "Each square block holds k cells (1-3) of colour 2 among its other cells; the whole block is rotated clockwise by k quarter turns, the colour-2 cells turning with it.",
     mk(scene(rotk_sub), tf_rotk), tf_rotk)


# ============================================================ digit cells
def dig_sub(rng, dmax):
    s = rng.randint(2, 3); a = rng.randint(5, 9); g = [[a] * s for _ in range(s)]; g[rng.randrange(s)][rng.randrange(s)] = rng.randint(1, dmax); return g


def tf_dcopy(g):
    out = copy(g); H, W = dims(g); new = []
    for cm in _mc(g):
        ds = [p for p in cm if g[p[0]][p[1]] <= 4]; a = body_col(g, cm, (1, 2, 3, 4))
        if len(ds) != 1: return None
        d = g[ds[0][0]][ds[0][1]]; r0, c0, r1, c1 = bbox(cm); out[ds[0][0]][ds[0][1]] = a; s = c1 - c0 + 1
        for k in range(1, d + 1):
            for r, c in cm: new.append((r, c + k * (s + 1), a))
    for r, c, a in new:
        if c >= W: return None
        out[r][c] = a
    return out
rule("digit_cell_is_the_copy_count", "Each square block (colours 5-9) has one digit cell d (1-3) inside it; the digit cell is repainted with the block's colour and d copies of the block are stamped to its right, one after another, each separated from the previous by one empty column.",
     mk(scene(lambda r: dig_sub(r, 3), 1, 3, 16, 1, 200), tf_dcopy), tf_dcopy, digits=True)


def info_dmove(g, cm):
    ds = [p for p in cm if g[p[0]][p[1]] <= 4]
    if len(ds) != 1: return 'bad'
    return RIGHT, g[ds[0][0]][ds[0][1]], ds, body_col(g, cm, (1, 2, 3, 4))
tdm = mover(info_dmove)
rule("digit_cell_is_the_move_distance", "Each square block (colours 5-9) has one digit cell d (1-4) inside it; the block slides d cells to the right, stopping early if the grid edge or another object blocks it, and the digit cell is repainted with the block's colour (blocks move one at a time in reading order of their topmost-then-leftmost cell).",
     mk(scene(lambda r: dig_sub(r, 4)), tdm), tdm, digits=True)


def tf_dlay(g):
    out = copy(g); H, W = dims(g)
    for cm in _mc(g):
        ds = [p for p in cm if g[p[0]][p[1]] <= 4]; a = body_col(g, cm, (1, 2, 3, 4))
        if len(ds) != 1: return None
        d = g[ds[0][0]][ds[0][1]]; r0, c0, r1, c1 = bbox(cm)
        if r0 - d < 0 or c0 - d < 0 or r1 + d >= H or c1 + d >= W: return None
        for r in range(r0 - d, r1 + d + 1):
            for c in range(c0 - d, c1 + d + 1):
                if out[r][c] and (r, c) not in cm: return None
                out[r][c] = a
    return out
rule("digit_cell_is_the_number_of_layers", "Each square block (colours 5-9) has one digit cell d (1-2) inside it; the digit cell is repainted with the block's colour and the block grows by d layers on all four sides (a solid square d cells larger on every side).",
     mk(scene(lambda r: dig_sub(r, 2), 1, 3, 14, 3, 200), tf_dlay), tf_dlay, digits=True)


# ============================================================ holes, minority, twins
def holes_sub(rng):
    h, w = rng.randint(3, 5), rng.randint(3, 5); a = src(rng); g = [[a] * w for _ in range(h)]
    cs = [(r, c) for r in range(1, h - 1) for c in range(1, w - 1)]; rng.shuffle(cs); ch = []
    for p in cs:
        if all(abs(p[0] - q[0]) + abs(p[1] - q[1]) > 1 for q in ch): ch.append(p)
        if len(ch) == rng.randint(1, 3): break
    if not ch: return None
    for r, c in ch: g[r][c] = 0
    return g


def tf_hcopy(g):
    out = copy(g); H, W = dims(g); new = []
    for cm in _mc(g):
        r0, c0, r1, c1 = bbox(cm); a = g[cm[0][0]][cm[0][1]]; k = (r1 - r0 + 1) * (c1 - c0 + 1) - len(cm)
        if not 1 <= k <= 3: return None
        for j in range(1, k + 1):
            for r, c in cm: new.append((r, c + j * (c1 - c0 + 2), a))
    for r, c, a in new:
        if c >= W: return None
        out[r][c] = a
    return out
rule("hole_count_is_the_copy_count", "Each solid rectangle has k single-cell holes (1-3) inside it; k exact copies of the rectangle, holes included, are stamped to its right, one after another, each separated from the previous by one empty column.",
     mk(scene(holes_sub, 1, 3, 16, 1, 200), tf_hcopy), tf_hcopy)


def mino_sub(rng):
    h, w = rng.randint(3, 6), rng.randint(3, 6); a, b = rng.sample(range(1, 10), 2); g = [[a] * w for _ in range(h)]
    for r, c in rng.sample([(r, c) for r in range(h) for c in range(w)], rng.randint(1, max(1, h * w // 2 - 1))): g[r][c] = b
    return g


def tf_mino(g):
    out = copy(g)
    for cm in _mc(g):
        cnt = {}
        for r, c in cm: cnt[g[r][c]] = cnt.get(g[r][c], 0) + 1
        if len(cnt) != 2 or len(set(cnt.values())) != 2: return None
        m = min(cnt, key=cnt.get)
        for r, c in cm: out[r][c] = m
    return out
rule("object_takes_its_minority_colour", "Each rectangle is made of two colours; the whole rectangle is repainted with whichever of its two colours has fewer cells (inputs never tie).",
     mk(scene(mino_sub), tf_mino), tf_mino)


def twin_scene(rng):
    H, Wd = D(rng, 12, 30), D(rng, 12, 30); k = rng.randint(1, 3); subs = []; used = set()
    for _ in range(k):
        h, w = rng.randint(3, 6), rng.randint(3, 6)
        if (h, w) in used: return None
        used.add((h, w)); a, b = rng.sample([c for c in range(1, 10) if c != 2], 2)
        r, c = [(0, rng.randint(1, w - 2)), (h - 1, rng.randint(1, w - 2)), (rng.randint(1, h - 2), 0), (rng.randint(1, h - 2), w - 1)][rng.randrange(4)]
        A = [[a] * w for _ in range(h)]; A[r][c] = 2; subs += [A, [[b] * w for _ in range(h)]]
    rng.shuffle(subs); return scatter_subs(rng, Wd and H, Wd, subs)


def tf_twin(g):
    out = copy(g); cms = _mc(g); mk_ = [c for c in cms if any(g[r][x] == 2 for r, x in c)]; un = [c for c in cms if c not in mk_]
    if not mk_ or len(mk_) != len(un): return None
    for A in mk_:
        r0, c0, r1, c1 = bbox(A); m = [p for p in A if g[p[0]][p[1]] == 2][0]
        tw = [B for B in un if (bbox(B)[2] - bbox(B)[0], bbox(B)[3] - bbox(B)[1]) == (r1 - r0, c1 - c0)]
        if len(tw) != 1: return None
        b = bbox(tw[0]); out[b[0] + m[0] - r0][b[1] + m[1] - c0] = 2
    return out
rule("marker_copied_to_the_twin_rectangle", "Rectangles come in pairs of equal size and different colours; one of each pair carries a colour-2 marker cell on an edge and its twin has none; the twin gets a colour-2 marker in the same position relative to its own corner (every size appears in only one pair).",
     mk(twin_scene, tf_twin), tf_twin)
