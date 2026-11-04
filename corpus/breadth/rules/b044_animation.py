# b044_animation.py -- panels as animation frames; output the next (or missing, or prior) frame.
# Frames are joined side by side separated by full-height grey (5) columns.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

SEP = 5


def _dim(rng, lo=3, hi=9, p=0.32):
    """An axis that appears ONCE in the joined grid (e.g. shared frame height). Occasionally
    lands in 21..30 so a share of inputs sit there."""
    if rng.random() < p:
        return rng.randint(21, 30)
    return rng.randint(lo, hi)


def _mdim(rng, k, lo=3, hi=9, p=0.4):
    """Per-frame size along the axis that gets joined k times (frame width in a horizontal
    filmstrip): capped so k copies plus (k-1) grey separators still fit in 30. Biased toward
    that cap, which often lands the whole joined side in 21..30. None if infeasible."""
    cap = (30 - (k - 1)) // k
    hi2 = min(hi, cap)
    if hi2 < lo:
        return None
    if rng.random() < p:
        return hi2
    return rng.randint(lo, hi2)


def _col(rng, excl=(0, SEP)):
    return rng.choice([c for c in COLOURS if c not in excl])


def _cols(rng, n, excl=(0, SEP)):
    return colours(rng, n, exclude=excl)


def _join(frames):
    h = len(frames[0])
    out = []
    for r in range(h):
        row = []
        for i, f in enumerate(frames):
            if i:
                row.append(SEP)
            row += f[r]
        out.append(row)
    return out


def _split(g, min_k=3):
    h, w = dims(g)
    sc = [c for c in range(w) if all(g[r][c] == SEP for r in range(h))]
    if not sc:
        return None
    frames, start = [], 0
    for c in sc + [w]:
        if c > start:
            frames.append([row[start:c] for row in g])
        start = c + 1
    if len(frames) < min_k or len({len(f[0]) for f in frames}) != 1:
        return None
    return frames


def _nzcells(f):
    h, w = dims(f)
    return [(r, c) for r in range(h) for c in range(w) if f[r][c]]


def _bbox_or_none(cells_):
    return bbox(cells_) if cells_ else None


def _line_positions(rng, h, w, dr, dc, steps):
    """`steps` integer positions along (dr, dc), all within [0,h)x[0,w). None if it cannot fit."""
    if dr > 0:
        r_lo, r_hi = 0, h - 1 - dr * (steps - 1)
    elif dr < 0:
        r_lo, r_hi = -dr * (steps - 1), h - 1
    else:
        r_lo, r_hi = 0, h - 1
    if dc > 0:
        c_lo, c_hi = 0, w - 1 - dc * (steps - 1)
    elif dc < 0:
        c_lo, c_hi = -dc * (steps - 1), w - 1
    else:
        c_lo, c_hi = 0, w - 1
    if r_hi < r_lo or c_hi < c_lo:
        return None
    r0 = rng.randint(r_lo, r_hi); c0 = rng.randint(c_lo, c_hi)
    return [(r0 + i * dr, c0 + i * dc) for i in range(steps)]


# ====================================================================== 1-3 constant-step translation
def _move_make(rng, dr, dc):
    k = rng.randint(3, 5)
    h = _dim(rng, 5, 10); w = _mdim(rng, k, 6, 14)
    if w is None:
        return None
    ow = rng.randint(1, 2)
    maxr0 = h - ow - abs(dr) * k if dr >= 0 else h - ow
    r_lo = max(0, -dr * k) if dr < 0 else 0
    c_lo = max(0, -dc * k) if dc < 0 else 0
    r_hi = h - ow - (dr * k if dr > 0 else 0)
    c_hi = w - ow - (dc * k if dc > 0 else 0)
    if r_hi <= r_lo or c_hi <= c_lo:
        return None
    r0 = rng.randint(r_lo, r_hi - 1); c0 = rng.randint(c_lo, c_hi - 1)
    col = _col(rng)
    frames = []
    for i in range(k):
        f = blank(h, w)
        for d in range(ow):
            f[r0 + i * dr][c0 + i * dc + d] = col
        frames.append(f)
    return _join(frames)


def _move_tf(g):
    frames = _split(g)
    if frames is None:
        return None
    f1, f2 = frames[-2], frames[-1]
    h, w = dims(f1)
    c1, c2 = _nzcells(f1), _nzcells(f2)
    if not c1 or not c2 or len(c1) != len(c2):
        return None
    dr = min(r for r, _ in c2) - min(r for r, _ in c1)
    dc = min(c for _, c in c2) - min(c for _, c in c1)
    if dr == 0 and dc == 0:
        return None
    col = f2[c2[0][0]][c2[0][1]]
    out = blank(h, w)
    for r, c in c2:
        nr, nc = r + dr, c + dc
        if not (0 <= nr < h and 0 <= nc < w):
            return None
        out[nr][nc] = col
    return out


def gi_move_right(rng):
    return _move_make(rng, 0, rng.choice([1, 2]))
rule("anim_slide_right_step", "Panels show a mark sliding right by a fixed step each frame; output the next frame continuing that motion.", gi_move_right, _move_tf)


def gi_move_down(rng):
    return _move_make(rng, rng.choice([1, 2]), 0)
rule("anim_slide_down_step", "Panels show a mark sliding down by a fixed step each frame; output the next frame continuing that motion.", gi_move_down, _move_tf)


def gi_move_diag(rng):
    return _move_make(rng, rng.choice([1, -1]), rng.choice([1, -1]))
rule("anim_slide_diagonal_step", "Panels show a mark sliding diagonally by a fixed step each frame; output the next frame continuing that motion.", gi_move_diag, _move_tf)


# ====================================================================== 4-5 quarter-turn rotation
def _rot_make(rng, cw, k=None):
    k = k if k is not None else rng.randint(3, 4)
    s = _mdim(rng, k, 5, 11)
    if s is None:
        return None
    n = rng.randint(3, min(6, s * s // 3))
    shape = random_shape(rng, n)
    sh = max(r for r, _ in shape) + 1; sw = max(c for _, c in shape) + 1
    if sh > s - 2 or sw > s - 2 or sh == sw:
        return None
    col = _col(rng)
    base = blank(s, s)
    r0, c0 = (s - sh) // 2, (s - sw) // 2
    for r, c in shape:
        base[r0 + r][c0 + c] = col
    cur = base; frames = [cur]
    for _ in range(k - 1):
        cur = rot90(cur) if cw else rot90(rot90(rot90(cur)))
        frames.append(cur)
    return _join(frames)


def _rot_tf(g, cw):
    frames = _split(g)
    if frames is None:
        return None
    last = frames[-1]
    return rot90(last) if cw else rot90(rot90(rot90(last)))


def gi_rot_cw(rng):
    return _rot_make(rng, True)
rule("anim_rotate_quarter_cw", "Panels show an asymmetric shape rotating a quarter turn clockwise each frame; output the next rotation.", gi_rot_cw, lambda g: _rot_tf(g, True))


def gi_rot_ccw(rng):
    return _rot_make(rng, False)
rule("anim_rotate_quarter_ccw", "Panels show an asymmetric shape rotating a quarter turn counter-clockwise each frame; output the next rotation.", gi_rot_ccw, lambda g: _rot_tf(g, False))


# ====================================================================== 6-7 ring / square growth-shrink
def _ring_box(h, w, cr, cc, half, col):
    f = blank(h, w)
    rect(f, cr - half, cc - half, cr + half, cc + half, col, fill=False)
    return f


def _box_half(cells_):
    r0 = min(r for r, _ in cells_); r1 = max(r for r, _ in cells_)
    return (r1 - r0) // 2


def _box_centre(cells_):
    r0 = min(r for r, _ in cells_); r1 = max(r for r, _ in cells_)
    c0 = min(c for _, c in cells_); c1 = max(c for _, c in cells_)
    return (r0 + r1) // 2, (c0 + c1) // 2


def gi_grow_ring(rng, k=None):
    k = k if k is not None else 2
    h = _dim(rng, 9, 18)
    w = _mdim(rng, k, 9, 18)
    if w is None:
        return None
    maxhalf = min(h, w) // 2 - 1
    if maxhalf < k:
        return None
    start = rng.randint(0, maxhalf - k)
    margin = start + k
    if h - 1 - 2 * margin < 0 or w - 1 - 2 * margin < 0:
        return None
    cr = rng.randint(margin, h - 1 - margin); cc = rng.randint(margin, w - 1 - margin)
    col = _col(rng)
    frames = [_ring_box(h, w, cr, cc, start + i, col) for i in range(k)]
    return _join(frames)


def tf_grow_ring(g):
    frames = _split(g, min_k=2)
    if frames is None:
        return None
    f1, f2 = frames[-2], frames[-1]
    c1, c2 = _nzcells(f1), _nzcells(f2)
    if not c1 or not c2:
        return None
    h1 = _box_half(c1); h2 = _box_half(c2)
    step = h2 - h1
    if step <= 0:
        return None
    H, W = dims(f2)
    cr, cc = _box_centre(c2)
    nh = h2 + step
    if cr - nh < 0 or cr + nh >= H or cc - nh < 0 or cc + nh >= W:
        return None
    return _ring_box(H, W, cr, cc, nh, f2[c2[0][0]][c2[0][1]])
rule("anim_grow_ring_outward", "Panels show a square ring growing outward by one layer each frame; output the next, larger ring.", gi_grow_ring, tf_grow_ring)


def _sq_box(h, w, cr, cc, half, col):
    f = blank(h, w)
    rect(f, cr - half, cc - half, cr + half, cc + half, col, fill=True)
    return f


def gi_shrink_square(rng):
    k = 2
    h = _dim(rng, 9, 18)
    w = _mdim(rng, k, 9, 18)
    if w is None:
        return None
    maxhalf = min(h, w) // 2 - 1
    if maxhalf < k:
        return None
    start = rng.randint(k, maxhalf)
    margin = start
    cr = rng.randint(margin, h - 1 - margin); cc = rng.randint(margin, w - 1 - margin)
    col = _col(rng)
    frames = [_sq_box(h, w, cr, cc, start - i, col) for i in range(k)]
    return _join(frames)


def tf_shrink_square(g):
    frames = _split(g, min_k=2)
    if frames is None:
        return None
    f1, f2 = frames[-2], frames[-1]
    c1, c2 = _nzcells(f1), _nzcells(f2)
    if not c1 or not c2:
        return None
    half1 = _box_half(c1); half2 = _box_half(c2)
    step = half1 - half2
    if step <= 0:
        return None
    nh = half2 - step
    if nh < 0:
        return None
    H, W = dims(f2)
    cr, cc = _box_centre(c2)
    return _sq_box(H, W, cr, cc, nh, f2[c2[0][0]][c2[0][1]])
rule("anim_shrink_square_inward", "Panels show a filled square shrinking inward by one layer each frame; output the next, smaller square.", gi_shrink_square, tf_shrink_square)


# ====================================================================== 8 colour cycling
def gi_colour_cycle(rng):
    k = rng.randint(3, 5)
    ph = _dim(rng, 4, 10)
    pw = _mdim(rng, k, 4, 10)
    if pw is None:
        return None
    pal = _cols(rng, rng.randint(3, 4))
    start = rng.randrange(len(pal))
    frames = []
    for i in range(k):
        f = blank(ph, pw)
        rect(f, 1, 1, ph - 2, pw - 2, pal[(start + i) % len(pal)], fill=True)
        frames.append(f)
    return _join(frames)


def tf_colour_cycle(g):
    frames = _split(g)
    if frames is None:
        return None
    seen_cols = []
    for f in frames:
        vs = {v for row in f for v in row if v}
        if len(vs) != 1:
            return None
        seen_cols.append(next(iter(vs)))
    if len(set(seen_cols)) < 2:
        return None
    period = None
    for p in range(1, len(seen_cols)):
        if all(seen_cols[i] == seen_cols[i - p] for i in range(p, len(seen_cols))):
            period = p; break
    if period is None:
        return None
    nxt = seen_cols[len(seen_cols) - period]
    out = []
    for row in frames[-1]:
        out.append([nxt if v else 0 for v in row])
    return out
rule("anim_colour_cycle_fill", "Panels show a filled square cycling through a fixed sequence of colours, one per frame; output the next frame's colour.", gi_colour_cycle, tf_colour_cycle)


# ====================================================================== 9-10 two objects approach / recede
def _two_make(rng, approach):
    k = 3
    step = 1
    margin = step * (k - 1)
    h = _dim(rng, 4, 9)
    gap0 = 2 * margin + 2
    w = _mdim(rng, k, gap0 + 2, 20)
    if w is None:
        return None
    r0 = rng.randint(0, h - 1)
    if approach:
        left0 = rng.randint(0, (w - gap0) // 2)
        right0 = w - 1 - rng.randint(0, (w - gap0) // 2)
        if right0 - left0 < gap0:
            return None
    else:
        if w - 1 - 2 * margin < 1:
            return None
        left0 = rng.randint(margin, w - 2 - margin)
        right0 = rng.randint(left0 + 1, w - 1 - margin)
    ca, cb = _cols(rng, 2)
    frames = []
    for i in range(k):
        f = blank(h, w)
        lc = left0 + i * step if approach else left0 - i * step
        rc = right0 - i * step if approach else right0 + i * step
        if not (0 <= lc < w and 0 <= rc < w) or lc >= rc:
            return None
        f[r0][lc] = ca; f[r0][rc] = cb
        frames.append(f)
    return _join(frames)


def _two_tf(g):
    frames = _split(g)
    if frames is None:
        return None
    f1, f2 = frames[-2], frames[-1]
    h, w = dims(f2)
    c1, c2 = _nzcells(f1), _nzcells(f2)
    if len(c1) != 2 or len(c2) != 2:
        return None
    c1s = sorted(c1, key=lambda p: p[1]); c2s = sorted(c2, key=lambda p: p[1])
    out = blank(h, w)
    for (r1, x1), (r2, x2), col_src in zip(c1s, c2s, [f2[c2s[0][0]][c2s[0][1]], f2[c2s[1][0]][c2s[1][1]]]):
        step = x2 - x1
        nx = x2 + step
        if not (0 <= nx < w):
            return None
        out[r2][nx] = col_src
    if len(_nzcells(out)) != 2:
        return None
    return out
rule("anim_two_marks_approach", "Two marks move toward each other by a fixed step each frame; output the next, closer frame.", lambda rng: _two_make(rng, True), _two_tf)
rule("anim_two_marks_recede", "Two marks move apart from each other by a fixed step each frame; output the next, further-apart frame.", lambda rng: _two_make(rng, False), _two_tf)


# ====================================================================== 11-12 bouncing dot off walls
def _bounce_positions(w, start, dirn, k):
    pos, d = [start], dirn
    p = start
    for _ in range(k - 1):
        p2 = p + d
        if p2 < 0 or p2 >= w:
            d = -d; p2 = p + d
        pos.append(p2); p = p2
    return pos, d


def gi_bounce_h(rng):
    k = rng.randint(4, 5)
    h = _dim(rng, 4, 9); w = _mdim(rng, k, 5, 14)
    if w is None:
        return None
    r0 = rng.randint(0, h - 1); c0 = rng.randint(1, w - 2); d = rng.choice([1, -1])
    pos, _ = _bounce_positions(w, c0, d, k)
    if len(set(pos)) < 3:
        return None
    col = _col(rng)
    frames = []
    for p in pos:
        f = blank(h, w); f[r0][p] = col; frames.append(f)
    return _join(frames)


def tf_bounce_h(g):
    frames = _split(g)
    if frames is None or len(frames) < 3:
        return None
    pts = []
    for f in frames:
        cs = _nzcells(f)
        if len(cs) != 1:
            return None
        pts.append(cs[0])
    h, w = dims(frames[0])
    r = pts[0][0]
    if any(p[0] != r for p in pts):
        return None
    cols = [p[1] for p in pts]
    d = cols[-1] - cols[-2]
    nxt = cols[-1] + d
    if nxt < 0 or nxt >= w:
        d = -d; nxt = cols[-1] + d
    if not (0 <= nxt < w):
        return None
    out = blank(h, w); out[r][nxt] = frames[-1][r][cols[-1]]
    return out
rule("anim_dot_bounce_horizontal", "A dot bounces back and forth between the left and right walls, reversing on contact; output its next position.", gi_bounce_h, tf_bounce_h)


def gi_bounce_v(rng):
    k = rng.randint(4, 5)
    h = _dim(rng, 6, 14); w = _mdim(rng, k, 3, 9)
    if w is None:
        return None
    c0 = rng.randint(0, w - 1); r0 = rng.randint(1, h - 2); d = rng.choice([1, -1])
    pos, _ = _bounce_positions(h, r0, d, k)
    if len(set(pos)) < 3:
        return None
    col = _col(rng)
    frames = []
    for p in pos:
        f = blank(h, w); f[p][c0] = col; frames.append(f)
    return _join(frames)


def tf_bounce_v(g):
    frames = _split(g)
    if frames is None or len(frames) < 3:
        return None
    pts = []
    for f in frames:
        cs = _nzcells(f)
        if len(cs) != 1:
            return None
        pts.append(cs[0])
    h, w = dims(frames[0])
    c = pts[0][1]
    if any(p[1] != c for p in pts):
        return None
    rows = [p[0] for p in pts]
    d = rows[-1] - rows[-2]
    nxt = rows[-1] + d
    if nxt < 0 or nxt >= h:
        d = -d; nxt = rows[-1] + d
    if not (0 <= nxt < h):
        return None
    out = blank(h, w); out[nxt][c] = frames[-1][rows[-1]][c]
    return out
rule("anim_dot_bounce_vertical", "A dot bounces back and forth between the top and bottom walls, reversing on contact; output its next position.", gi_bounce_v, tf_bounce_v)


# ====================================================================== 13-15 progressive reveal of a striped picture
def _reveal_rows_make(rng, grow_down):
    h = _dim(rng, 7, 15)
    period = rng.randint(2, 3)
    k = rng.randint(3, min(5, h - period - 1))
    if k < 3:
        return None
    pal = _cols(rng, period)
    w = _mdim(rng, k, 4, 10)
    if w is None:
        return None
    start = rng.randint(period + 1, h - k)
    frames = []
    for i in range(k):
        n = start + i
        f = blank(h, w)
        rows = range(n) if grow_down else range(h - n, h)
        for r in rows:
            idx = r if grow_down else h - 1 - r
            for c in range(w):
                f[r][c] = pal[idx % period]
        frames.append(f)
    return _join(frames)


def _reveal_rows_tf(g, grow_down):
    frames = _split(g)
    if frames is None:
        return None
    f1, f2 = frames[-2], frames[-1]
    h, w = dims(f2)
    n1 = sum(1 for row in f1 if any(row))
    n2 = sum(1 for row in f2 if any(row))
    if n2 <= n1 or n2 >= h:
        return None
    revealed = list(range(n2)) if grow_down else list(range(h - n2, h))
    seq = [f2[r][0] for r in revealed]
    period = None
    for p in range(1, len(seq)):
        if all(seq[i] == seq[i - p] for i in range(p, len(seq))):
            period = p; break
    if period is None:
        return None
    out = copy(f2)
    nxt_row = n2 if grow_down else h - 1 - n2
    colr = seq[len(seq) - period]
    out[nxt_row] = [colr] * w
    return out
rule("anim_reveal_rows_top_down", "Panels show a striped picture being revealed one more row from the top each frame; output the next, more-revealed frame.", lambda rng: _reveal_rows_make(rng, True), lambda g: _reveal_rows_tf(g, True))
rule("anim_reveal_rows_bottom_up", "Panels show a striped picture being revealed one more row from the bottom each frame; output the next, more-revealed frame.", lambda rng: _reveal_rows_make(rng, False), lambda g: _reveal_rows_tf(g, False))


def gi_reveal_cols(rng):
    k = 3
    period = rng.randint(2, 3)
    w = _mdim(rng, k, period + k + 1, 15)
    if w is None:
        return None
    h = _dim(rng, 4, 10)
    pal = _cols(rng, period)
    start = rng.randint(period + 1, w - k)
    frames = []
    for i in range(k):
        n = start + i
        f = blank(h, w)
        for c in range(n):
            for r in range(h):
                f[r][c] = pal[c % period]
        frames.append(f)
    return _join(frames)


def tf_reveal_cols(g):
    frames = _split(g)
    if frames is None:
        return None
    f1, f2 = frames[-2], frames[-1]
    h, w = dims(f2)
    n1 = sum(1 for c in range(w) if any(f1[r][c] for r in range(h)))
    n2 = sum(1 for c in range(w) if any(f2[r][c] for r in range(h)))
    if n2 <= n1 or n2 >= w:
        return None
    seq = [f2[0][c] for c in range(n2)]
    period = None
    for p in range(1, len(seq)):
        if all(seq[i] == seq[i - p] for i in range(p, len(seq))):
            period = p; break
    if period is None:
        return None
    out = copy(f2)
    colr = seq[len(seq) - period]
    for r in range(h):
        out[r][n2] = colr
    return out
rule("anim_reveal_cols_left_right", "Panels show a striped picture being revealed one more column from the left each frame; output the next, more-revealed frame.", gi_reveal_cols, tf_reveal_cols)


# ====================================================================== 16 cell count increases by one per frame, row-major fill order
def gi_cellcount(rng):
    k = rng.randint(3, 5)
    h = _dim(rng, 5, 10); w = _mdim(rng, k, 5, 10)
    if w is None or k + 1 > h * w:
        return None
    col = _col(rng)
    frames = []
    for i in range(k):
        n = i + 1
        f = blank(h, w); cnt = 0
        for r in range(h):
            for c in range(w):
                if cnt < n:
                    f[r][c] = col; cnt += 1
        frames.append(f)
    return _join(frames)


def tf_cellcount(g):
    frames = _split(g)
    if frames is None:
        return None
    f1, f2 = frames[-2], frames[-1]
    n1, n2 = len(_nzcells(f1)), len(_nzcells(f2))
    if n2 != n1 + 1:
        return None
    h, w = dims(f2)
    if n2 >= h * w:
        return None
    col = next(v for row in f2 for v in row if v)
    expected = blank(h, w); cnt = 0
    for r in range(h):
        for c in range(w):
            if cnt < n2:
                expected[r][c] = col; cnt += 1
    if expected != f2:
        return None
    out = copy(f2); cnt = 0
    for r in range(h):
        for c in range(w):
            if cnt < n2 + 1:
                out[r][c] = col
            cnt += 1
    return out
rule("anim_cellcount_increase_byone", "Panels show one more coloured cell appearing each frame in reading order; output the next frame with one additional cell filled.", gi_cellcount, tf_cellcount)


# ====================================================================== 17-19 bars filling / draining
def gi_bar_fill_v(rng):
    h = _dim(rng, 6, 14)
    k = rng.randint(3, min(5, h - 1))
    if k < 3:
        return None
    w = _mdim(rng, k, 3, 9)
    if w is None:
        return None
    bw = rng.randint(1, min(3, w))
    c0 = rng.randint(0, w - bw)
    start = rng.randint(1, h - k)
    col = _col(rng)
    frames = []
    for i in range(k):
        n = start + i
        f = blank(h, w)
        for r in range(h - n, h):
            for c in range(c0, c0 + bw):
                f[r][c] = col
        frames.append(f)
    return _join(frames)


def tf_bar_fill_v(g):
    frames = _split(g)
    if frames is None:
        return None
    f1, f2 = frames[-2], frames[-1]
    h, w = dims(f2)
    n1 = sum(1 for r in range(h) if any(f1[r]))
    n2 = sum(1 for r in range(h) if any(f2[r]))
    if n2 <= n1 or n2 >= h:
        return None
    col = next(v for row in f2 for v in row if v)
    cols_filled = [c for c in range(w) if f2[h - 1][c]]
    out = copy(f2); newrow = h - 1 - n2
    for c in cols_filled:
        out[newrow][c] = col
    return out
rule("anim_bar_fill_vertical", "A vertical bar fills upward by one row each frame; output the next, taller bar.", gi_bar_fill_v, tf_bar_fill_v)


def gi_bar_fill_h(rng):
    k = rng.randint(3, 5)
    w = _mdim(rng, k, k + 1, 14)
    if w is None:
        return None
    h = _dim(rng, 3, 9)
    bh = rng.randint(1, min(3, h))
    r0 = rng.randint(0, h - bh)
    start = rng.randint(1, w - k)
    col = _col(rng)
    frames = []
    for i in range(k):
        n = start + i
        f = blank(h, w)
        for c in range(n):
            for r in range(r0, r0 + bh):
                f[r][c] = col
        frames.append(f)
    return _join(frames)


def tf_bar_fill_h(g):
    frames = _split(g)
    if frames is None:
        return None
    f1, f2 = frames[-2], frames[-1]
    h, w = dims(f2)
    n1 = sum(1 for c in range(w) if any(f1[r][c] for r in range(h)))
    n2 = sum(1 for c in range(w) if any(f2[r][c] for r in range(h)))
    if n2 <= n1 or n2 >= w:
        return None
    col = next(v for row in f2 for v in row if v)
    rows_filled = [r for r in range(h) if f2[r][0]]
    out = copy(f2); newcol = n2
    for r in rows_filled:
        out[r][newcol] = col
    return out
rule("anim_bar_fill_horizontal", "A horizontal bar fills rightward by one column each frame; output the next, longer bar.", gi_bar_fill_h, tf_bar_fill_h)


def gi_bar_drain_v(rng):
    h = _dim(rng, 6, 14)
    k = rng.randint(3, min(5, h - 1))
    if k < 3:
        return None
    w = _mdim(rng, k, 3, 9)
    if w is None:
        return None
    bw = rng.randint(1, min(3, w))
    c0 = rng.randint(0, w - bw)
    start = rng.randint(k, h)
    col = _col(rng)
    frames = []
    for i in range(k):
        n = start - i
        if n < 1:
            return None
        f = blank(h, w)
        for r in range(h - n, h):
            for c in range(c0, c0 + bw):
                f[r][c] = col
        frames.append(f)
    return _join(frames)


def tf_bar_drain_v(g):
    frames = _split(g)
    if frames is None:
        return None
    f1, f2 = frames[-2], frames[-1]
    h, w = dims(f2)
    n1 = sum(1 for r in range(h) if any(f1[r]))
    n2 = sum(1 for r in range(h) if any(f2[r]))
    if n1 - n2 != 1 or n2 < 1:
        return None
    col = next(v for row in f2 for v in row if v)
    cols_filled = [c for c in range(w) if f2[h - n2][c]]
    nxt = n2 - 1
    if nxt < 1:
        return None
    out = blank(h, w)
    for r in range(h - nxt, h):
        for c in cols_filled:
            out[r][c] = col
    return out
rule("anim_bar_drain_vertical", "A vertical bar loses its top row each frame, draining downward; output the next, shorter bar.", gi_bar_drain_v, tf_bar_drain_v)


# ====================================================================== 20 alternating two states
def _rand_pattern(rng, h, w, cols_):
    f = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.4:
                f[r][c] = rng.choice(cols_)
    return f


def gi_alt2(rng):
    k = rng.randint(3, 5)
    h = _dim(rng, 3, 9); w = _mdim(rng, k, 3, 9)
    if w is None:
        return None
    cols_ = _cols(rng, 2)
    a = _rand_pattern(rng, h, w, cols_)
    b = _rand_pattern(rng, h, w, cols_)
    if a == b or not any(v for row in a for v in row) or not any(v for row in b for v in row):
        return None
    frames = [a if i % 2 == 0 else b for i in range(k)]
    return _join(frames)


def tf_alt2(g):
    frames = _split(g)
    if frames is None or len(frames) < 3:
        return None
    for i in range(2, len(frames)):
        if frames[i] != frames[i - 2]:
            return None
    if frames[-1] == frames[-2]:
        return None
    return frames[-2]
rule("anim_alternate_two_states", "Panels alternate between two fixed states; output the next frame in that alternation.", gi_alt2, tf_alt2)


# ====================================================================== 21 snake grows along a straight path
def gi_snake_straight(rng):
    k = rng.randint(3, 5)
    h = _dim(rng, 5, 12); w = _mdim(rng, k, 5, 12)
    if w is None:
        return None
    dr, dc = rng.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
    pos = _line_positions(rng, h, w, dr, dc, k)
    if pos is None:
        return None
    col = _col(rng)
    frames = []
    for i in range(k):
        f = blank(h, w)
        for j in range(i + 1):
            r, c = pos[j]; f[r][c] = col
        frames.append(f)
    return _join(frames)


def tf_snake_straight(g):
    frames = _split(g)
    if frames is None:
        return None
    f1, f2 = frames[-2], frames[-1]
    c1, c2 = set(_nzcells(f1)), set(_nzcells(f2))
    if len(c2) != len(c1) + 1 or not c1 <= c2:
        return None
    new = next(iter(c2 - c1))
    h, w = dims(f2)
    rs = {p[0] for p in c2}; cs = {p[1] for p in c2}
    col = f2[new[0]][new[1]]
    if len(rs) == 1:
        xs = sorted(p[1] for p in c2)
        dcc = 1 if new[1] == xs[-1] else -1
        nc = new[1] + dcc
        if not (0 <= nc < w):
            return None
        out = copy(f2); out[new[0]][nc] = col; return out
    elif len(cs) == 1:
        ys = sorted(p[0] for p in c2)
        drr = 1 if new[0] == ys[-1] else -1
        nr = new[0] + drr
        if not (0 <= nr < h):
            return None
        out = copy(f2); out[nr][new[1]] = col; return out
    return None
rule("anim_snake_grow_straight", "A straight trail of cells grows by one cell at its leading end each frame; output the next, longer trail.", gi_snake_straight, tf_snake_straight)


# ====================================================================== 22-23 wraparound shift
def gi_shift_cols(rng):
    k = rng.randint(3, 5)
    h = _dim(rng, 3, 9); w = _mdim(rng, k, 4, 10)
    if w is None:
        return None
    cols_ = _cols(rng, rng.randint(2, 3))
    base = [[rng.choice(cols_ + [0]) for _ in range(w)] for _ in range(h)]
    if not any(any(row) for row in base):
        return None

    def shiftrow(row, i):
        i = i % w
        return row[-i:] + row[:-i] if i else row[:]
    frames = [[shiftrow(row, i) for row in base] for i in range(k)]
    return _join(frames)


def tf_shift_cols(g):
    frames = _split(g)
    if frames is None:
        return None
    h, w = dims(frames[0])

    def shiftrow(row, i):
        i = i % w
        return row[-i:] + row[:-i] if i else row[:]
    for i in range(1, len(frames)):
        if frames[i] != [shiftrow(row, 1) for row in frames[i - 1]]:
            return None
    return [shiftrow(row, 1) for row in frames[-1]]
rule("anim_shift_columns_wrap", "The pattern shifts one column to the right each frame, wrapping around the edge; output the next shift.", gi_shift_cols, tf_shift_cols)


def gi_shift_rows(rng):
    k = rng.randint(3, 5)
    h = _dim(rng, 4, 10); w = _mdim(rng, k, 3, 9)
    if w is None:
        return None
    cols_ = _cols(rng, rng.randint(2, 3))
    base = [[rng.choice(cols_ + [0]) for _ in range(w)] for _ in range(h)]
    if not any(any(row) for row in base):
        return None

    def shift_down(gg, i):
        i = i % h
        return gg[-i:] + gg[:-i] if i else [row[:] for row in gg]
    frames = [shift_down(base, i) for i in range(k)]
    return _join(frames)


def tf_shift_rows(g):
    frames = _split(g)
    if frames is None:
        return None
    h, w = dims(frames[0])

    def shift_down(gg, i):
        i = i % h
        return gg[-i:] + gg[:-i] if i else [row[:] for row in gg]
    for i in range(1, len(frames)):
        if frames[i] != shift_down(frames[i - 1], 1):
            return None
    return shift_down(frames[-1], 1)
rule("anim_shift_rows_wrap", "The pattern shifts one row downward each frame, wrapping around the edge; output the next shift.", gi_shift_rows, tf_shift_rows)


# ====================================================================== 24-26 extrapolate backward (before the first shown frame)
def gi_extrap_back_motion(rng):
    dr, dc = rng.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)])
    k = rng.randint(3, 5)
    h = _dim(rng, 5, 10); w = _mdim(rng, k, 6, 14)
    if w is None:
        return None
    pos = _line_positions(rng, h, w, dr, dc, k + 1)
    if pos is None:
        return None
    col = _col(rng)
    frames = []
    for i in range(1, k + 1):
        f = blank(h, w); r, c = pos[i]; f[r][c] = col; frames.append(f)
    return _join(frames)


def tf_extrap_back_motion(g):
    frames = _split(g)
    if frames is None:
        return None
    f0, f1 = frames[0], frames[1]
    c0pts, c1pts = _nzcells(f0), _nzcells(f1)
    if len(c0pts) != 1 or len(c1pts) != 1:
        return None
    h, w = dims(f0)
    (r0, c0), (r1, c1) = c0pts[0], c1pts[0]
    dr, dc = r1 - r0, c1 - c0
    if dr == 0 and dc == 0:
        return None
    pr, pc = r0 - dr, c0 - dc
    if not (0 <= pr < h and 0 <= pc < w):
        return None
    out = blank(h, w); out[pr][pc] = f0[r0][c0]
    return out
rule("anim_extrapolate_backward_motion", "Panels show a mark sliding by a fixed step; output the frame that would have come before the first panel shown.", gi_extrap_back_motion, tf_extrap_back_motion)


def gi_extrap_back_rot(rng):
    cw = rng.choice([True, False])
    full = _rot_make(rng, cw, k=4)
    if full is None:
        return None
    frames = _split(full)
    if frames is None or len(frames) < 4:
        return None
    return _join(frames[1:])


def tf_extrap_back_rot(g):
    frames = _split(g)
    if frames is None or len(frames) < 3:
        return None
    f0, f1 = frames[0], frames[1]
    if f1 == rot90(f0):
        return rot90(rot90(rot90(f0)))
    elif f0 == rot90(f1):
        return rot90(f0)
    return None
rule("anim_extrapolate_backward_rotation", "Panels show a shape rotating a quarter turn each frame; output the frame that would have come before the first panel shown.", gi_extrap_back_rot, tf_extrap_back_rot)


def gi_extrap_back_ring(rng):
    full = gi_grow_ring(rng, k=3)
    if full is None:
        return None
    frames = _split(full, min_k=3)
    if frames is None or len(frames) != 3:
        return None
    return _join(frames[1:])


def tf_extrap_back_ring(g):
    frames = _split(g, min_k=2)
    if frames is None or len(frames) < 2:
        return None
    f0, f1 = frames[0], frames[1]
    c0, c1 = _nzcells(f0), _nzcells(f1)
    if not c0 or not c1:
        return None
    h0 = _box_half(c0); h1 = _box_half(c1)
    step = h1 - h0
    if step <= 0:
        return None
    nh = h0 - step
    if nh < 0:
        return None
    H, W = dims(f0)
    cr, cc = _box_centre(c0)
    if cr - nh < 0 or cr + nh >= H or cc - nh < 0 or cc + nh >= W:
        return None
    return _ring_box(H, W, cr, cc, nh, f0[c0[0][0]][c0[0][1]])
rule("anim_extrapolate_backward_ring_growth", "Panels show a ring growing outward each frame; output the frame that would have come before the first panel shown.", gi_extrap_back_ring, tf_extrap_back_ring)


# ====================================================================== 27-28 interpolate the hidden middle panel
def gi_interp_motion(rng):
    dr, dc = rng.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)])
    h = _dim(rng, 5, 10); w = _mdim(rng, 3, 6, 14)
    if w is None:
        return None
    pos = _line_positions(rng, h, w, dr, dc, 3)
    if pos is None:
        return None
    col = _col(rng)
    f0 = blank(h, w); f0[pos[0][0]][pos[0][1]] = col
    f2 = blank(h, w); f2[pos[2][0]][pos[2][1]] = col
    fmid = blank(h, w)
    return _join([f0, fmid, f2])


def tf_interp_motion(g):
    frames = _split(g)
    if frames is None or len(frames) != 3:
        return None
    f0, fmid, f2 = frames
    if any(v for row in fmid for v in row):
        return None
    c0, c2 = _nzcells(f0), _nzcells(f2)
    if len(c0) != 1 or len(c2) != 1:
        return None
    (r0, cc0), (r2, cc2) = c0[0], c2[0]
    if (r0 + r2) % 2 or (cc0 + cc2) % 2:
        return None
    mr, mc = (r0 + r2) // 2, (cc0 + cc2) // 2
    if (mr, mc) == (r0, cc0) or (mr, mc) == (r2, cc2):
        return None
    h, w = dims(f0)
    out = blank(h, w); out[mr][mc] = f0[r0][cc0]
    return out
rule("anim_interpolate_missing_middle_motion", "The middle panel of three has been blanked; a mark moves at a constant step between the outer two; output the missing middle frame.", gi_interp_motion, tf_interp_motion)


def gi_interp_growth(rng):
    h = _dim(rng, 9, 18)
    period = rng.randint(2, 3)
    pal = _cols(rng, period)
    w = _mdim(rng, 3, 4, 10)
    if w is None:
        return None
    step = 1
    lo = period + 1
    hi = h - 1 - 2 * step
    if hi < lo:
        return None
    n0 = rng.randint(lo, hi)
    n2 = n0 + 2 * step

    def mkframe(n):
        f = blank(h, w)
        for r in range(n):
            for c in range(w):
                f[r][c] = pal[r % period]
        return f
    f0 = mkframe(n0)
    f2 = mkframe(n2)
    fmid = blank(h, w)
    return _join([f0, fmid, f2])


def tf_interp_growth(g):
    frames = _split(g)
    if frames is None or len(frames) != 3:
        return None
    f0, fmid, f2 = frames
    if any(v for row in fmid for v in row):
        return None
    h, w = dims(f2)
    n0 = sum(1 for row in f0 if any(row))
    n2 = sum(1 for row in f2 if any(row))
    if n2 <= n0 or (n2 - n0) % 2 or n2 >= h:
        return None
    nm = (n0 + n2) // 2
    out = blank(h, w)
    for r in range(nm):
        out[r] = f2[r][:]
    return out
rule("anim_interpolate_missing_middle_growth", "The middle panel of three has been blanked; a striped picture is revealed by a steadily growing number of rows between the outer two; output the missing middle frame.", gi_interp_growth, tf_interp_growth)


# ====================================================================== 29 frame count as a bar
def gi_framecount(rng):
    k = rng.randint(3, 8)
    h = _dim(rng, 3, 8); w = _mdim(rng, k, 2, 8)
    if w is None:
        return None
    col = _col(rng)
    frames = []
    for i in range(k):
        f = blank(h, w)
        n = rng.randint(1, min(3, h * w))
        cells_ = rng.sample([(r, c) for r in range(h) for c in range(w)], n)
        for r, c in cells_:
            f[r][c] = col
        frames.append(f)
    return _join(frames)


def tf_framecount(g):
    frames = _split(g)
    if frames is None:
        return None
    cols_found = {v for f in frames for row in f for v in row if v}
    if len(cols_found) != 1:
        return None
    col = next(iter(cols_found))
    k = len(frames)
    width = 12
    if k >= width:
        return None
    return [[col] * k + [0] * (width - k)]
rule("anim_frame_count_to_bar", "Count the panels in the filmstrip; output a single row bar that long in the panels' colour.", gi_framecount, tf_framecount)


# ====================================================================== 30 the frame that breaks a steady progression
def gi_breakmotion(rng):
    k = rng.randint(4, 5)
    dr = rng.choice([1, 2])
    span = dr * (k - 1)
    h = _dim(rng, span + 9, max(span + 9, 30))
    w = _mdim(rng, k, 4, 10)
    if w is None:
        return None
    r0 = rng.randint(2, h - 1 - span - 2)
    c0 = rng.randrange(w)
    col = _col(rng)
    positions = [r0 + i * dr for i in range(k)]
    edge = rng.choice([0, k - 1])
    off = rng.choice([-3, -2, 2, 3])
    newpos = positions[edge] + off
    if not (0 <= newpos < h) or newpos in positions:
        return None
    positions[edge] = newpos
    frames = []
    for p in positions:
        f = blank(h, w); f[p][c0] = col; frames.append(f)
    return _join(frames)


def tf_breakmotion(g):
    frames = _split(g)
    if frames is None or len(frames) < 4:
        return None
    pts = []
    for f in frames:
        cs = _nzcells(f)
        if len(cs) != 1:
            return None
        pts.append(cs[0])
    if len({p[1] for p in pts}) != 1:
        return None
    cols_ = [p[0] for p in pts]

    def is_ap(seq):
        if len(seq) < 2:
            return False
        d = seq[1] - seq[0]
        return all(seq[i] - seq[i - 1] == d for i in range(2, len(seq)))
    if is_ap(cols_[1:]) and not is_ap(cols_):
        bad = 0
    elif is_ap(cols_[:-1]) and not is_ap(cols_):
        bad = len(cols_) - 1
    else:
        return None
    r = pts[0][0]
    return frames[bad]
rule("anim_identify_frame_breaks_sequence", "Almost every panel's mark follows a steady downward step except one; output the panel that breaks that progression.", gi_breakmotion, tf_breakmotion)


# ====================================================================== 31-32 opposite-direction growth variants
def gi_grow_square(rng):
    k = 2
    h = _dim(rng, 9, 18)
    w = _mdim(rng, k, 9, 18)
    if w is None:
        return None
    maxhalf = min(h, w) // 2 - 1
    if maxhalf - k < 0:
        return None
    start = rng.randint(0, maxhalf - k)
    margin = start + k
    if h - 1 - 2 * margin < 0 or w - 1 - 2 * margin < 0:
        return None
    cr = rng.randint(margin, h - 1 - margin); cc = rng.randint(margin, w - 1 - margin)
    col = _col(rng)
    frames = [_sq_box(h, w, cr, cc, start + i, col) for i in range(k)]
    return _join(frames)


def tf_grow_square(g):
    frames = _split(g, min_k=2)
    if frames is None:
        return None
    f1, f2 = frames[-2], frames[-1]
    c1, c2 = _nzcells(f1), _nzcells(f2)
    if not c1 or not c2:
        return None
    h1 = _box_half(c1); h2 = _box_half(c2)
    step = h2 - h1
    if step <= 0:
        return None
    H, W = dims(f2)
    cr, cc = _box_centre(c2)
    nh = h2 + step
    if cr - nh < 0 or cr + nh >= H or cc - nh < 0 or cc + nh >= W:
        return None
    return _sq_box(H, W, cr, cc, nh, f2[c2[0][0]][c2[0][1]])
rule("anim_grow_square_outward", "Panels show a filled square growing outward by one layer each frame; output the next, larger square.", gi_grow_square, tf_grow_square)


def gi_shrink_ring(rng):
    k = 2
    h = _dim(rng, 9, 18)
    w = _mdim(rng, k, 9, 18)
    if w is None:
        return None
    maxlayer = min(h, w) // 2 - 1
    if maxlayer < k:
        return None
    start = rng.randint(0, maxlayer - k)
    margin = start + k
    if h - 1 - 2 * margin < 0 or w - 1 - 2 * margin < 0:
        return None
    cr = rng.randint(margin, h - 1 - margin); cc = rng.randint(margin, w - 1 - margin)
    col = _col(rng)
    frames = [_ring_box(h, w, cr, cc, start + i, col) for i in range(k)]
    return _join(frames)


def tf_shrink_ring(g):
    frames = _split(g, min_k=2)
    if frames is None:
        return None
    f1, f2 = frames[-2], frames[-1]
    c1, c2 = _nzcells(f1), _nzcells(f2)
    if not c1 or not c2:
        return None
    l1 = _box_half(c1); l2 = _box_half(c2)
    step = l2 - l1
    if step <= 0:
        return None
    H, W = dims(f2)
    cr, cc = _box_centre(c2)
    nl = l2 + step
    if cr - nl < 0 or cr + nl >= H or cc - nl < 0 or cc + nl >= W:
        return None
    return _ring_box(H, W, cr, cc, nl, f2[c2[0][0]][c2[0][1]])
rule("anim_shrink_ring_inward", "Panels show a square ring shrinking inward by one layer each frame; output the next, smaller ring.", gi_shrink_ring, tf_shrink_ring)


# ====================================================================== 33 compound: slide and recolour
def gi_move_recolour(rng):
    dc = 1
    k = rng.randint(3, 4)
    h = _dim(rng, 4, 9); w = _mdim(rng, k, dc * k + 2, 16)
    if w is None:
        return None
    pal = _cols(rng, rng.randint(2, 3))
    c0 = rng.randint(0, w - 1 - dc * k)
    r0 = rng.randrange(h)
    frames = []
    for i in range(k):
        f = blank(h, w); f[r0][c0 + i * dc] = pal[i % len(pal)]; frames.append(f)
    return _join(frames)


def tf_move_recolour(g):
    frames = _split(g)
    if frames is None:
        return None
    pts = []; cols_ = []
    for f in frames:
        cs = _nzcells(f)
        if len(cs) != 1:
            return None
        pts.append(cs[0]); cols_.append(f[cs[0][0]][cs[0][1]])
    if len({p[0] for p in pts}) != 1:
        return None
    xs = [p[1] for p in pts]
    d = xs[-1] - xs[-2]
    if d == 0 or any(xs[i] - xs[i - 1] != d for i in range(1, len(xs))):
        return None
    period = None
    for p in range(1, len(cols_)):
        if all(cols_[i] == cols_[i - p] for i in range(p, len(cols_))):
            period = p; break
    if period is None:
        return None
    nxtcol = cols_[len(cols_) - period]
    h, w = dims(frames[0]); r = pts[0][0]; nx = xs[-1] + d
    if not (0 <= nx < w):
        return None
    out = blank(h, w); out[r][nx] = nxtcol
    return out
rule("anim_move_and_recolour_cycle", "A mark both slides right by a fixed step and cycles through a fixed sequence of colours each frame; output the next frame.", gi_move_recolour, tf_move_recolour)


# ====================================================================== 34 size pulses (grows then shrinks)
def _bounce_positions(w, start, dirn, k):
    pos, d = [start], dirn
    p = start
    for _ in range(k - 1):
        p2 = p + d
        if p2 < 0 or p2 >= w:
            d = -d; p2 = p + d
        pos.append(p2); p = p2
    return pos, d


def gi_pulse(rng):
    k = 3
    h = _dim(rng, 6, 16); w = _mdim(rng, k, 6, 16)
    if w is None:
        return None
    maxhalf = min(h, w) // 2 - 1
    if maxhalf < 2:
        return None
    cr = rng.randint(maxhalf, h - 1 - maxhalf); cc = rng.randint(maxhalf, w - 1 - maxhalf)
    h0 = rng.randint(0, maxhalf); d = rng.choice([1, -1])
    pos, _ = _bounce_positions(maxhalf + 1, h0, d, k)
    if len(set(pos)) < 2:
        return None
    col = _col(rng)
    frames = [_sq_box(h, w, cr, cc, p, col) for p in pos]
    return _join(frames)


def tf_pulse(g):
    frames = _split(g)
    if frames is None or len(frames) < 3:
        return None
    halves = []
    cr = cc = None
    for f in frames:
        cs = _nzcells(f)
        if not cs:
            return None
        halves.append(_box_half(cs))
        cr, cc = _box_centre(cs)
    H, W = dims(frames[0]); maxhalf = min(H, W) // 2 - 1
    d = halves[-1] - halves[-2]
    if d == 0:
        return None
    nxt = halves[-1] + d
    if nxt < 0 or nxt > maxhalf:
        d = -d; nxt = halves[-1] + d
    if not (0 <= nxt <= maxhalf):
        return None
    col = next(v for row in frames[-1] for v in row if v)
    return _sq_box(H, W, cr, cc, nxt, col)
rule("anim_square_size_pulse_bounce", "A filled square's size grows and shrinks, bouncing between empty and a maximum; output its next size.", gi_pulse, tf_pulse)


# ====================================================================== 35 raster scan sweep
def gi_raster(rng):
    k = rng.randint(3, 5)
    h = _dim(rng, 4, 9); w = _mdim(rng, k, 5, 12)
    if w is None:
        return None
    total = h * w
    if k + 1 > total:
        return None
    start = rng.randint(0, total - 1 - k)
    col = _col(rng)
    frames = []
    for i in range(k):
        idx = start + i; r, c = divmod(idx, w)
        f = blank(h, w); f[r][c] = col; frames.append(f)
    return _join(frames)


def tf_raster(g):
    frames = _split(g)
    if frames is None:
        return None
    f1, f2 = frames[-2], frames[-1]
    c1, c2 = _nzcells(f1), _nzcells(f2)
    if len(c1) != 1 or len(c2) != 1:
        return None
    h, w = dims(f2)
    idx1 = c1[0][0] * w + c1[0][1]; idx2 = c2[0][0] * w + c2[0][1]
    if idx2 - idx1 != 1:
        return None
    nidx = idx2 + 1
    if nidx >= h * w:
        return None
    nr, nc = divmod(nidx, w)
    out = blank(h, w); out[nr][nc] = f2[c2[0][0]][c2[0][1]]
    return out
rule("anim_raster_scan_sweep", "A single lit cell sweeps left to right along each row in turn, like a scan line; output its next position.", gi_raster, tf_raster)


# ====================================================================== 36 countdown bar from the right
def gi_countdown(rng):
    k = rng.randint(3, 4)
    h = _dim(rng, 3, 8); w = _mdim(rng, k, k + 2, 16)
    if w is None:
        return None
    r0 = rng.randrange(h)
    start = rng.randint(k, w)
    col = _col(rng)
    frames = []
    for i in range(k):
        n = start - i
        if n < 1:
            return None
        f = blank(h, w)
        for c in range(n):
            f[r0][c] = col
        frames.append(f)
    return _join(frames)


def tf_countdown(g):
    frames = _split(g)
    if frames is None:
        return None
    f1, f2 = frames[-2], frames[-1]
    h, w = dims(f2)
    rows1 = [r for r in range(h) if any(f1[r])]
    rows2 = [r for r in range(h) if any(f2[r])]
    if len(rows1) != 1 or len(rows2) != 1 or rows1[0] != rows2[0]:
        return None
    r = rows1[0]
    n1 = sum(1 for c in range(w) if f1[r][c]); n2 = sum(1 for c in range(w) if f2[r][c])
    if n1 - n2 != 1 or n2 < 1:
        return None
    nxt = n2 - 1
    if nxt < 1:
        return None
    col = next(v for v in f2[r] if v)
    out = blank(h, w)
    for c in range(nxt):
        out[r][c] = col
    return out
rule("anim_countdown_bar_shrink_right", "A full-width bar loses one cell from its right end each frame, like a countdown; output the next, shorter bar.", gi_countdown, tf_countdown)


# ====================================================================== 37-38 orbiting a square's corners
def gi_orbit(rng, cw):
    k = rng.randint(3, 5)
    h = _dim(rng, 5, 12); w = _mdim(rng, k, 5, 12)
    if w is None:
        return None
    r0 = rng.randint(0, h - 2); r1 = rng.randint(r0 + 1, h - 1)
    c0 = rng.randint(0, w - 2); c1 = rng.randint(c0 + 1, w - 1)
    corners = [(r0, c0), (r0, c1), (r1, c1), (r1, c0)]
    order = corners if cw else corners[::-1]
    start = rng.randrange(4)
    col = _col(rng)
    frames = []
    for i in range(k):
        f = blank(h, w); r, c = order[(start + i) % 4]; f[r][c] = col; frames.append(f)
    return _join(frames)


def tf_orbit(g, cw):
    frames = _split(g)
    if frames is None:
        return None
    h, w = dims(frames[0])
    pts = []
    for f in frames:
        cs = _nzcells(f)
        if len(cs) != 1:
            return None
        pts.append(cs[0])
    rs = sorted({p[0] for p in pts}); cs_ = sorted({p[1] for p in pts})
    if len(rs) != 2 or len(cs_) != 2:
        return None
    r0, r1 = rs; c0, c1 = cs_
    corners = [(r0, c0), (r0, c1), (r1, c1), (r1, c0)]
    order = corners if cw else corners[::-1]
    idxs = []; col = None
    for f, p in zip(frames, pts):
        if p not in order:
            return None
        idxs.append(order.index(p)); col = f[p[0]][p[1]]
    for i in range(1, len(idxs)):
        if (idxs[i] - idxs[i - 1]) % 4 != 1:
            return None
    nxt = (idxs[-1] + 1) % 4
    r, c = order[nxt]
    out = blank(h, w); out[r][c] = col
    return out
rule("anim_orbit_corners_clockwise", "A mark visits a rectangle's four corners clockwise, one per frame; output its next corner.", lambda rng: gi_orbit(rng, True), lambda g: tf_orbit(g, True))
rule("anim_orbit_corners_counterclockwise", "A mark visits a rectangle's four corners counter-clockwise, one per frame; output its next corner.", lambda rng: gi_orbit(rng, False), lambda g: tf_orbit(g, False))


# ====================================================================== 39 bar fills then resets and fills again
def gi_fillwrap(rng):
    k = rng.randint(4, 5)
    h = _dim(rng, 5, 11); w = _mdim(rng, k, 3, 8)
    if w is None:
        return None
    period = h + 1
    start = rng.randrange(period)
    col = _col(rng)
    frames = []
    for i in range(k):
        n = (start + i) % period
        f = blank(h, w)
        for r in range(h - n, h):
            for c in range(w):
                f[r][c] = col
        frames.append(f)
    return _join(frames)


def tf_fillwrap(g):
    frames = _split(g)
    if frames is None:
        return None
    h, w = dims(frames[0])
    period = h + 1

    def cnt(f):
        return sum(1 for r in range(h) if any(f[r]))
    counts_ = [cnt(f) for f in frames]
    for i in range(1, len(counts_)):
        if (counts_[i] - counts_[i - 1]) % period != 1:
            return None
    nxt = (counts_[-1] + 1) % period
    if nxt == 0:
        return None
    col = None
    for f in frames:
        for row in f:
            for v in row:
                if v:
                    col = v
    if col is None:
        return None
    out = blank(h, w)
    for r in range(h - nxt, h):
        for c in range(w):
            out[r][c] = col
    return out
rule("anim_bar_fill_wrap_reset", "A vertical bar fills upward each frame and, once full, resets to empty and fills again; output its next level.", gi_fillwrap, tf_fillwrap)


# ====================================================================== 40 diagonal billiard bounce off all four walls
def gi_billiard(rng):
    k = rng.randint(4, 5)
    h = _dim(rng, 5, 10); w = _mdim(rng, k, 5, 12)
    if w is None:
        return None
    r0 = rng.randint(1, h - 2); c0 = rng.randint(1, w - 2)
    ddr = rng.choice([1, -1]); ddc = rng.choice([1, -1])
    col = _col(rng)
    pts = [(r0, c0)]
    r, c = r0, c0
    for _ in range(k - 1):
        nr, nc = r + ddr, c + ddc
        if nr < 0 or nr >= h:
            ddr = -ddr; nr = r + ddr
        if nc < 0 or nc >= w:
            ddc = -ddc; nc = c + ddc
        pts.append((nr, nc)); r, c = nr, nc
    if len(set(pts)) < 3:
        return None
    frames = []
    for (r, c) in pts:
        f = blank(h, w); f[r][c] = col; frames.append(f)
    return _join(frames)


def tf_billiard(g):
    frames = _split(g)
    if frames is None or len(frames) < 3:
        return None
    pts = []
    for f in frames:
        cs = _nzcells(f)
        if len(cs) != 1:
            return None
        pts.append(cs[0])
    h, w = dims(frames[0])
    (r1, c1), (r2, c2) = pts[-2], pts[-1]
    ddr = r2 - r1; ddc = c2 - c1
    if ddr == 0 or ddc == 0:
        return None
    nr, nc = r2 + ddr, c2 + ddc
    if nr < 0 or nr >= h:
        ddr = -ddr; nr = r2 + ddr
    if nc < 0 or nc >= w:
        ddc = -ddc; nc = c2 + ddc
    if not (0 <= nr < h and 0 <= nc < w):
        return None
    col = frames[-1][r2][c2]
    out = blank(h, w); out[nr][nc] = col
    return out
rule("anim_dot_bounce_diagonal_both_walls", "A mark bounces diagonally inside the frame, reflecting off whichever wall it reaches; output its next position.", gi_billiard, tf_billiard)
