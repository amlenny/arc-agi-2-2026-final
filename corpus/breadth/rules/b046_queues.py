# b046_queues.py -- queues, stacks and order operations on object sequences.
# Objects are rendered either as a horizontal row of full-height colour blocks (a "queue", read
# column-wise, blocks separated by one background column) or as a vertical column of full-width
# colour blocks (a "stack", read row-wise). Local helpers below do the reading/rendering; glib's
# components()/objects() are not needed since blocks are solid runs of one colour.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

PALETTE = [c for c in COLOURS if c != 5]   # 5 is reserved as the grey marker/divider colour
GREY = 5


def gen_segs(rng, n, wlo=1, whi=3, allow_repeat=False, palette=None):
    pal = palette or PALETTE
    segs, prev = [], None
    for _ in range(n):
        choices = pal if allow_repeat else [c for c in pal if c != prev]
        c = rng.choice(choices)
        segs.append((c, rng.randint(wlo, whi)))
        prev = c
    return segs


def big_h(rng, big_p=0.3, lo=2, hi=6):
    return rng.randint(21, 30) if rng.random() < big_p else rng.randint(lo, hi)


def col_colour(g, c):
    h = len(g); v = g[0][c]
    return v if all(g[r][c] == v for r in range(h)) else -1


def read_queue(g):
    h, w = dims(g); segs = []; c = 0
    while c < w:
        v = col_colour(g, c)
        if v <= 0:
            c += 1; continue
        c0 = c
        while c < w and col_colour(g, c) == v:
            c += 1
        segs.append((v, c - c0))
    return segs


def render_queue(h, segs, gap=1):
    w = sum(wd for _, wd in segs) + gap * max(0, len(segs) - 1)
    g = blank(h, max(w, 1)); c = 0
    for v, wd in segs:
        for cc in range(c, c + wd):
            for r in range(h):
                g[r][cc] = v
        c += wd + gap
    return g


def row_colour(g, r):
    w = len(g[0]); v = g[r][0]
    return v if all(g[r][cc] == v for cc in range(w)) else -1


def read_queue_rows(g):
    h, w = dims(g); segs = []; r = 0
    while r < h:
        v = row_colour(g, r)
        if v <= 0:
            r += 1; continue
        r0 = r
        while r < h and row_colour(g, r) == v:
            r += 1
        segs.append((v, r - r0))
    return segs


def render_queue_rows(w, segs, gap=1):
    h = sum(ht for _, ht in segs) + gap * max(0, len(segs) - 1)
    g = blank(max(h, 1), w); r = 0
    for v, ht in segs:
        for rr in range(r, r + ht):
            for cc in range(w):
                g[rr][cc] = v
        r += ht + gap
    return g


def with_marker_row(body, marker_cols):
    w = len(body[0])
    mrow = [GREY if c in marker_cols else 0 for c in range(w)]
    return [mrow] + [row[:] for row in body]


def split_marker(g):
    return g[0], g[1:]


def seg_col_of(segs, idx, gap=1):
    """starting column of segs[idx] if rendered with render_queue."""
    c = 0
    for i, (_, wd) in enumerate(segs):
        if i == idx:
            return c
        c += wd + gap


def two_col_grid(bodyA, bodyB, gap=1):
    H = max(len(bodyA), len(bodyB)); wA = len(bodyA[0]); wB = len(bodyB[0])
    bodyA = bodyA + [[0] * wA for _ in range(H - len(bodyA))]
    bodyB = bodyB + [[0] * wB for _ in range(H - len(bodyB))]
    return [ra + [0] * gap + rb for ra, rb in zip(bodyA, bodyB)]


def split_two_cols(g):
    H, W = dims(g)
    gap_cols = [c for c in range(W) if all(g[r][c] == 0 for r in range(H))]
    if not gap_cols:
        return None
    leftW = gap_cols[0]
    rightStart = leftW
    while rightStart in gap_cols:
        rightStart += 1
    if leftW == 0 or rightStart >= W:
        return None
    return crop(g, 0, 0, H - 1, leftW - 1), crop(g, 0, rightStart, H - 1, W - 1)


# 1 ---------------------------------------------------------------
def gi_1(rng):
    n = rng.randint(3, 7); segs = gen_segs(rng, n); h = big_h(rng)
    return render_queue(h, segs)
def tf_1(g):
    segs = read_queue(g)
    if len(segs) < 2: return None
    return render_queue(len(g), segs[1:])
rule("queue_dequeue_front", "The first object in the queue leaves and the rest close up to fill the gap.", gi_1, tf_1)


# 2 ---------------------------------------------------------------
def gi_2(rng):
    n = rng.randint(3, 7); segs = gen_segs(rng, n); h = big_h(rng)
    return render_queue(h, segs)
def tf_2(g):
    segs = read_queue(g)
    if len(segs) < 2: return None
    new = segs[1:] + segs[:1]
    if new == segs: return None
    return render_queue(len(g), new)
rule("queue_advance_wrap_front_to_back", "The queue advances one step: the front object wraps around to become the new back.", gi_2, tf_2)


# 3 ---------------------------------------------------------------
def gi_3(rng):
    n = rng.randint(3, 7); segs = gen_segs(rng, n); h = big_h(rng)
    return render_queue(h, segs)
def tf_3(g):
    segs = read_queue(g)
    if len(segs) < 2: return None
    new = segs[-1:] + segs[:-1]
    if new == segs: return None
    return render_queue(len(g), new)
rule("queue_last_to_front", "The last object in the queue moves around to the front; everyone else shifts back one slot.", gi_3, tf_3)


# 4 ---------------------------------------------------------------
def gi_4(rng):
    n = rng.randint(3, 6); segs = gen_segs(rng, n); h = big_h(rng, hi=5)
    k = rng.randint(1, n - 1)
    body = render_queue(h, segs)
    return with_marker_row(body, set(range(k)))
def tf_4(g):
    mrow, body = split_marker(g)
    k = sum(1 for v in mrow if v == GREY)
    segs = read_queue(body)
    if not segs: return None
    k = k % len(segs)
    if k == 0: return None
    new = segs[k:] + segs[:k]
    return render_queue(len(body), new)
rule("queue_rotate_left_by_grey_dot_count", "The queue rotates left by k positions, where k is the number of grey dots in the marker row above it.", gi_4, tf_4)


# 5 ---------------------------------------------------------------
def gi_5(rng):
    n = rng.randint(4, 8); segs = gen_segs(rng, n); h = big_h(rng)
    return render_queue(h, segs)
def tf_5(g):
    segs = read_queue(g)
    new = [s for i, s in enumerate(segs) if i % 2 == 0]
    if len(new) == len(segs): return None
    return render_queue(len(g), new)
# queue_remove_every_second dropped 2026-10-12 (trio review: behavioural duplicate or one global operation)
# 6 ---------------------------------------------------------------
def gi_6(rng):
    n = rng.randint(2, 5); ha = big_h(rng, hi=5)
    widths = [rng.randint(1, 3) for _ in range(n)]
    colsA = []; colsB = []; prevA = prevB = None
    for _ in range(n):
        a = rng.choice([x for x in PALETTE if x != prevA]); colsA.append(a); prevA = a
        b = rng.choice([x for x in PALETTE if x != prevB]); colsB.append(b); prevB = b
    segsA = list(zip(colsA, widths)); segsB = list(zip(colsB, widths))
    bodyA = render_queue(ha, segsA); bodyB = render_queue(ha, segsB)
    w = len(bodyA[0])
    return bodyA + [[0] * w] + bodyB
def tf_6(g):
    H = len(g); w = len(g[0])
    sep = next((r for r in range(H) if all(v == 0 for v in g[r])), None)
    if sep is None: return None
    top, bottom = g[:sep], g[sep + 1:]
    A, B = read_queue(top), read_queue(bottom)
    if len(A) != len(B) or not A: return None
    new = []
    for a, b in zip(A, B):
        new += [a, b]
    return render_queue(len(top), new)
rule("queue_merge_two_rows_alternating", "Two queues stacked with a blank row between them merge into one, alternating objects from each.", gi_6, tf_6)


# 7 ---------------------------------------------------------------
def gi_7(rng):
    n = rng.randint(3, 7)
    for _ in range(10):
        segs = gen_segs(rng, n)
        if segs != segs[::-1]:
            break
    else:
        return None
    h = big_h(rng)
    return render_queue(h, segs)
def tf_7(g):
    segs = read_queue(g)
    new = segs[::-1]
    if new == segs: return None
    return render_queue(len(g), new)
rule("queue_reverse_order", "The whole queue reverses: the last object becomes first and the first becomes last.", gi_7, tf_7, primitive=True)
# 8 ---------------------------------------------------------------
def gi_8(rng):
    n = rng.randint(3, 6); segs = gen_segs(rng, n); h = big_h(rng, hi=5)
    body = render_queue(h, segs)
    idx = rng.randint(1, n - 1)
    col = seg_col_of(segs, idx)
    return with_marker_row(body, {col})
def tf_8(g):
    mrow, body = split_marker(g)
    mcol = next((c for c, v in enumerate(mrow) if v == GREY), None)
    if mcol is None: return None
    segs = read_queue(body)
    idx = None; c = 0
    for i, (_, wd) in enumerate(segs):
        if c <= mcol < c + wd: idx = i; break
        c += wd + 1
    if idx is None or idx == 0: return None
    new = [segs[idx]] + segs[:idx] + segs[idx + 1:]
    return render_queue(len(body), new)
rule("queue_dot_marked_jumps_to_front", "The object marked by a dot above it jumps to the front of the queue; the rest keep their relative order.", gi_8, tf_8)


# 9 ---------------------------------------------------------------
def gi_9(rng):
    n = rng.randint(3, 6)
    cols = rng.sample(PALETTE, n)
    widths = [rng.randint(1, 3) for _ in range(n)]
    segs = list(zip(cols, widths))
    h = big_h(rng)
    return render_queue(h, segs)
def tf_9(g):
    segs = read_queue(g)
    widths = [w for _, w in segs]
    new_cols = sorted(v for v, _ in segs)
    new = list(zip(new_cols, widths))
    if new == segs: return None
    return render_queue(len(g), new)
rule("queue_stable_sort_by_colour_keep_slots", "Objects are sorted by colour value but each stays in its original slot width; only the colours shuffle into ascending order.", gi_9, tf_9)


# 10 ---------------------------------------------------------------
def gi_10(rng):
    n1 = rng.randint(2, 4); n2 = rng.randint(2, 4)
    segsA = gen_segs(rng, n1); segsB = gen_segs(rng, n2)
    h = big_h(rng)
    full = segsA + [(GREY, 1)] + segsB
    return render_queue(h, full)
def tf_10(g):
    segs = read_queue(g)
    div = next((i for i, (v, _) in enumerate(segs) if v == GREY), None)
    if div is None: return None
    A, B = segs[:div], segs[div + 1:]
    if not A or not B: return None
    return render_queue(len(g), B + A)
rule("queue_split_at_divider_swap_halves", "A grey divider splits the queue in two; the halves swap places and the divider is removed.", gi_10, tf_10)


# 11 ---------------------------------------------------------------
def gi_11(rng):
    nA = rng.randint(2, 4); nB = rng.randint(1, 3)
    segsA = gen_segs(rng, nA); segsB = gen_segs(rng, nB)
    lw = rng.randint(2, 4); rw = rng.randint(2, 4)
    bodyA = render_queue_rows(lw, segsA); bodyB = render_queue_rows(rw, segsB)
    return two_col_grid(bodyA, bodyB)
def tf_11(g):
    res = split_two_cols(g)
    if res is None: return None
    L, R = res
    A, B = read_queue_rows(L), read_queue_rows(R)
    if not A: return None
    popped = A[0]; newA = A[1:]; newB = [popped] + B
    lw, rw = len(L[0]), len(R[0])
    bodyA = render_queue_rows(lw, newA) if newA else blank(1, lw)
    bodyB = render_queue_rows(rw, newB)
    return two_col_grid(bodyA, bodyB)
rule("stack_pop_top_to_second_stack", "The top block of the left stack pops off and is pushed onto the top of the right stack.", gi_11, tf_11)


# 12 ---------------------------------------------------------------
def gi_12(rng):
    n = rng.randint(3, 6)
    segs = gen_segs(rng, n, wlo=1, whi=rng.choice([3, 5]))
    heights = [h for _, h in segs]
    if heights.count(max(heights)) != 1: return None
    w = big_h(rng, lo=3, hi=6)
    return render_queue_rows(w, segs)
def tf_12(g):
    segs = read_queue_rows(g)
    if len(segs) < 2: return None
    mx = max(segs, key=lambda s: s[1])
    idx = segs.index(mx)
    if idx == len(segs) - 1: return None
    new = segs[:idx] + segs[idx + 1:] + [mx]
    return render_queue_rows(len(g[0]), new)
rule("stack_tallest_to_back", "The tallest block in the stack moves to the very bottom; the rest shift up to fill in.", gi_12, tf_12)


# 13 ---------------------------------------------------------------
def gi_13(rng):
    n = rng.randint(4, 8)
    segs = gen_segs(rng, n, allow_repeat=True)
    cols = [v for v, _ in segs]
    if len(set(cols)) == len(cols): return None
    h = big_h(rng)
    return render_queue(h, segs)
def tf_13(g):
    segs = read_queue(g)
    seen, new = set(), []
    for v, w in segs:
        if v in seen: continue
        seen.add(v); new.append((v, w))
    if len(new) == len(segs): return None
    return render_queue(len(g), new)
rule("queue_remove_duplicate_colours_keep_first", "Later objects whose colour already appeared earlier in the queue are removed, keeping only the first of each colour.", gi_13, tf_13)


# 14 ---------------------------------------------------------------
def gi_14(rng):
    n = rng.randint(3, 6); segs = gen_segs(rng, n); h = big_h(rng)
    gaps = [rng.randint(2, 4) for _ in range(n - 1)]
    if not gaps or min(gaps) <= 1: gaps = gaps or [2]
    w = sum(wd for _, wd in segs) + sum(gaps)
    g = blank(h, w); c = 0
    for i, (v, wd) in enumerate(segs):
        for cc in range(c, c + wd):
            for r in range(h): g[r][cc] = v
        c += wd
        if i < len(gaps): c += gaps[i]
    return g
def tf_14(g):
    segs = read_queue(g)
    if not segs: return None
    out = render_queue(len(g), segs, gap=1)
    if out == g: return None
    return out
rule("queue_compress_remove_gaps", "The queue is compressed so the ragged gaps between objects shrink to one cell each.", gi_14, tf_14)


# 15 ---------------------------------------------------------------
def gi_15(rng):
    n = rng.randint(4, 7); segs = []; prev = None
    for i in range(n):
        c = prev if (i > 0 and rng.random() < 0.5) else rng.choice(PALETTE)
        segs.append((c, rng.randint(1, 3))); prev = c
    if not any(segs[i][0] == segs[i + 1][0] for i in range(len(segs) - 1)): return None
    h = big_h(rng)
    return render_queue(h, segs)
def tf_15(g):
    segs = read_queue(g); new = []
    for v, w in segs:
        if new and new[-1][0] == v:
            new[-1] = (v, new[-1][1] + w)
        else:
            new.append((v, w))
    if new == segs: return None
    return render_queue(len(g), new)
rule("queue_merge_adjacent_same_colour", "Neighbours in the queue that share a colour merge into one wider object, closing the gap between them.", gi_15, tf_15)


# 16 ---------------------------------------------------------------
def gi_16(rng):
    n = rng.randint(3, 6); segs = gen_segs(rng, n)
    widths = [w for _, w in segs]
    if widths.count(max(widths)) != 1: return None
    h = big_h(rng)
    return render_queue(h, segs)
def tf_16(g):
    segs = read_queue(g)
    mx = max(segs, key=lambda s: s[1])
    idx = segs.index(mx)
    if idx == 0: return None
    new = [mx] + segs[:idx] + segs[idx + 1:]
    return render_queue(len(g), new)
rule("queue_largest_to_front", "The widest object in the queue moves to the front; everyone else keeps their order behind it.", gi_16, tf_16)


# 17 ---------------------------------------------------------------
def gi_17(rng):
    n = rng.randint(3, 6); segs = gen_segs(rng, n)
    widths = [w for _, w in segs]
    if widths.count(min(widths)) != 1: return None
    h = big_h(rng)
    return render_queue(h, segs)
def tf_17(g):
    segs = read_queue(g)
    mn = min(segs, key=lambda s: s[1])
    idx = segs.index(mn)
    if idx == len(segs) - 1: return None
    new = segs[:idx] + segs[idx + 1:] + [mn]
    return render_queue(len(g), new)
rule("queue_smallest_to_back", "The narrowest object in the queue moves to the very back; everyone else keeps their order ahead of it.", gi_17, tf_17)


# 18 ---------------------------------------------------------------
def gi_18(rng):
    n = rng.randint(3, 7); segs = gen_segs(rng, n); h = big_h(rng)
    return render_queue(h, segs)
def tf_18(g):
    segs = read_queue(g)
    if len(segs) < 2: return None
    new = segs[:]
    new[0], new[-1] = new[-1], new[0]
    if new == segs: return None
    return render_queue(len(g), new)
rule("queue_swap_first_and_last", "The first and last objects in the queue trade places; everyone in between stays put.", gi_18, tf_18)


# 19 ---------------------------------------------------------------
def gi_19(rng):
    n = rng.randint(4, 7); segs = gen_segs(rng, n); h = big_h(rng, hi=5)
    k = rng.randint(1, n - 2)
    body = render_queue(h, segs)
    return with_marker_row(body, set(range(k)))
def tf_19(g):
    mrow, body = split_marker(g)
    k = sum(1 for v in mrow if v == GREY)
    segs = read_queue(body)
    if not segs: return None
    k = min(k, len(segs) - 1)
    if k <= 0: return None
    return render_queue(len(body), segs[k:])
rule("queue_dequeue_k_by_dot_count", "The front k objects leave the queue, where k is the number of grey dots in the marker row above it.", gi_19, tf_19)


# 20 ---------------------------------------------------------------
def gi_20(rng):
    n = rng.randint(2, 4) * 2; segs = gen_segs(rng, n); h = big_h(rng)
    return render_queue(h, segs)
def tf_20(g):
    segs = read_queue(g); n = len(segs)
    if n < 4 or n % 2: return None
    half = n // 2
    A, B = segs[:half], segs[half:]
    new = []
    for a, b in zip(A, B):
        new += [a, b]
    if new == segs: return None
    return render_queue(len(g), new)
rule("queue_split_half_interleave_zipper", "The queue is split into front and back halves, then the two halves zip together, alternating one object from each.", gi_20, tf_20)


# 21 ---------------------------------------------------------------
def gi_21(rng):
    n = rng.randint(4, 8); segs = gen_segs(rng, n); h = big_h(rng)
    return render_queue(h, segs)
def tf_21(g):
    segs = read_queue(g)
    new = segs[0::2]
    if len(new) == len(segs) or not new: return None
    return render_queue(len(g), new)
rule("queue_keep_odd_positions", "Only the objects standing at odd positions (1st, 3rd, 5th, ...) survive, compacted together.", gi_21, tf_21)


# 22 ---------------------------------------------------------------
def gi_22(rng):
    n = rng.randint(4, 8); segs = gen_segs(rng, n); h = big_h(rng)
    return render_queue(h, segs)
def tf_22(g):
    segs = read_queue(g)
    new = segs[1::2]
    if not new or len(new) == len(segs): return None
    return render_queue(len(g), new)
rule("queue_keep_even_positions", "Only the objects standing at even positions (2nd, 4th, 6th, ...) survive, compacted together.", gi_22, tf_22)


# 23 ---------------------------------------------------------------
def gi_23(rng):
    n = rng.randint(3, 7)
    for _ in range(10):
        segs = gen_segs(rng, n, wlo=1, whi=4)
        if segs != segs[::-1]:
            break
    else:
        return None
    w = big_h(rng, lo=3, hi=6)
    return render_queue_rows(w, segs)
def tf_23(g):
    segs = read_queue_rows(g)
    new = segs[::-1]
    if new == segs: return None
    return render_queue_rows(len(g[0]), new)
rule("stack_reverse_order", "The stack turns upside down: the top block becomes the bottom and the bottom becomes the top.", gi_23, tf_23, primitive=True)
# 24 ---------------------------------------------------------------
def gi_24(rng):
    n = rng.randint(2, 4)
    segsA = gen_segs(rng, n, wlo=1, whi=3); segsB = gen_segs(rng, n, wlo=1, whi=3)
    lw = rng.randint(2, 4); rw = rng.randint(2, 4)
    bodyA = render_queue_rows(lw, segsA); bodyB = render_queue_rows(rw, segsB)
    return two_col_grid(bodyA, bodyB)
def tf_24(g):
    res = split_two_cols(g)
    if res is None: return None
    L, R = res
    A, B = read_queue_rows(L), read_queue_rows(R)
    if not A or not B: return None
    new = []
    for a, b in zip(A, B):
        new += [a, b]
    new += A[len(B):] if len(A) > len(B) else B[len(A):]
    w = len(L[0])
    return render_queue_rows(w, new)
rule("stack_merge_two_columns_alternating", "Two side-by-side stacks merge into one, alternating a block from the left stack with a block from the right stack top-down.", gi_24, tf_24)


# 25 ---------------------------------------------------------------
def gi_25(rng):
    n = rng.randint(3, 6); segs = gen_segs(rng, n); h = big_h(rng, hi=5)
    body = render_queue(h, segs)
    idx = rng.randint(1, n - 1)
    col = seg_col_of(segs, idx)
    return with_marker_row(body, {col})
def tf_25(g):
    mrow, body = split_marker(g)
    mcol = next((c for c, v in enumerate(mrow) if v == GREY), None)
    if mcol is None: return None
    segs = read_queue(body)
    idx = None; c = 0
    for i, (_, wd) in enumerate(segs):
        if c <= mcol < c + wd: idx = i; break
        c += wd + 1
    if idx is None or idx == 0: return None
    new = segs[:]
    new[idx - 1], new[idx] = new[idx], new[idx - 1]
    return render_queue(len(body), new)
rule("queue_marked_object_bubbles_forward", "The object marked by a dot above it swaps with the one directly ahead of it, bubbling forward one step.", gi_25, tf_25)


# 26 ---------------------------------------------------------------
def gi_26(rng):
    n = rng.randint(3, 6); segs = gen_segs(rng, n); h = big_h(rng, hi=5)
    body = render_queue(h, segs)
    idx = rng.randint(0, n - 2)
    col = seg_col_of(segs, idx)
    return with_marker_row(body, {col})
def tf_26(g):
    mrow, body = split_marker(g)
    mcol = next((c for c, v in enumerate(mrow) if v == GREY), None)
    if mcol is None: return None
    segs = read_queue(body)
    idx = None; c = 0
    for i, (_, wd) in enumerate(segs):
        if c <= mcol < c + wd: idx = i; break
        c += wd + 1
    if idx is None or idx == len(segs) - 1: return None
    new = segs[:]
    new[idx + 1], new[idx] = new[idx], new[idx + 1]
    return render_queue(len(body), new)
rule("queue_marked_object_bubbles_backward", "The object marked by a dot above it swaps with the one directly behind it, bubbling backward one step.", gi_26, tf_26)


# 27 ---------------------------------------------------------------
def gi_27(rng):
    n = rng.randint(3, 6); segs = gen_segs(rng, n); h = big_h(rng, hi=5)
    k = rng.randint(1, n - 1)
    body = render_queue(h, segs)
    return with_marker_row(body, set(range(k)))
def tf_27(g):
    mrow, body = split_marker(g)
    k = sum(1 for v in mrow if v == GREY)
    segs = read_queue(body)
    if not segs: return None
    k = k % len(segs)
    if k == 0: return None
    new = segs[-k:] + segs[:-k]
    return render_queue(len(body), new)
rule("queue_rotate_right_by_dot_count", "The queue rotates right by k positions, where k is the number of grey dots in the marker row above it.", gi_27, tf_27)


# 28 ---------------------------------------------------------------
def gi_28(rng):
    n = rng.randint(3, 7)
    widths = rng.sample(range(1, 7), min(n, 6)) if n <= 6 else [rng.randint(1, 6) for _ in range(n)]
    while len(widths) < n: widths.append(rng.randint(1, 6))
    cols, prev = [], None
    for _ in range(n):
        c = rng.choice([x for x in PALETTE if x != prev]); cols.append(c); prev = c
    segs = list(zip(cols, widths))
    h = big_h(rng)
    return render_queue(h, segs)
def tf_28(g):
    segs = read_queue(g)
    new = sorted(segs, key=lambda s: s[1])
    if new == segs: return None
    return render_queue(len(g), new)
rule("queue_sort_by_width_ascending", "The objects are reordered from narrowest to widest, left to right.", gi_28, tf_28)


# 29 ---------------------------------------------------------------
def gi_29(rng):
    n = rng.randint(3, 7)
    widths = rng.sample(range(1, 7), min(n, 6)) if n <= 6 else [rng.randint(1, 6) for _ in range(n)]
    while len(widths) < n: widths.append(rng.randint(1, 6))
    cols, prev = [], None
    for _ in range(n):
        c = rng.choice([x for x in PALETTE if x != prev]); cols.append(c); prev = c
    segs = list(zip(cols, widths))
    h = big_h(rng)
    return render_queue(h, segs)
def tf_29(g):
    segs = read_queue(g)
    new = sorted(segs, key=lambda s: -s[1])
    if new == segs: return None
    return render_queue(len(g), new)
rule("queue_sort_by_width_descending", "The objects are reordered from widest to narrowest, left to right.", gi_29, tf_29)


# 30 ---------------------------------------------------------------
def gi_30(rng):
    n = rng.randint(4, 7); segs = []
    for _ in range(n):
        if rng.random() < 0.35:
            segs.append((GREY, rng.randint(1, 2)))
        else:
            segs.append((rng.choice(PALETTE), rng.randint(1, 3)))
    greys = sum(1 for v, _ in segs if v == GREY)
    if greys == 0 or greys == n: return None
    h = big_h(rng)
    return render_queue(h, segs)
def tf_30(g):
    segs = read_queue(g)
    new = [s for s in segs if s[0] != GREY]
    if len(new) == len(segs) or not new: return None
    return render_queue(len(g), new)
rule("queue_remove_grey_markers_compact", "Every grey marker object is deleted from the queue and the remaining objects compact together.", gi_30, tf_30)


# 31 ---------------------------------------------------------------
def gi_31(rng):
    n = rng.randint(2, 6); segs = gen_segs(rng, n); h = big_h(rng)
    return render_queue(h, segs)
def tf_31(g):
    segs = read_queue(g)
    if not segs: return None
    new = segs + [segs[-1]]
    return render_queue(len(g), new)
rule("queue_duplicate_last_append", "A copy of the last object is appended to the back of the queue.", gi_31, tf_31)


# 32 ---------------------------------------------------------------
def gi_32(rng):
    n = rng.randint(2, 6); segs = gen_segs(rng, n); h = big_h(rng)
    return render_queue(h, segs)
def tf_32(g):
    segs = read_queue(g)
    if not segs: return None
    new = [segs[0]] + segs
    return render_queue(len(g), new)
rule("queue_duplicate_first_prepend", "A copy of the first object is inserted at the very front of the queue.", gi_32, tf_32)


# 33 ---------------------------------------------------------------
def gi_33(rng):
    n = rng.randint(2, 4) * 2
    cols, prev = [], None
    for i in range(n):
        c = rng.choice([x for x in PALETTE if x != prev]); cols.append(c); prev = c
    for i in range(0, n, 2):
        if cols[i] == cols[i + 1]:
            return None
    widths = [rng.randint(1, 3) for _ in range(n)]
    segs = list(zip(cols, widths))
    h = big_h(rng)
    return render_queue(h, segs)
def tf_33(g):
    segs = read_queue(g); new = segs[:]
    for i in range(0, len(new) - 1, 2):
        new[i], new[i + 1] = new[i + 1], new[i]
    if new == segs: return None
    return render_queue(len(g), new)
rule("queue_pairwise_swap_adjacent", "Objects swap in pairs: the 1st and 2nd trade places, then the 3rd and 4th, and so on down the queue.", gi_33, tf_33)


# 34 ---------------------------------------------------------------
def gi_34(rng):
    n = rng.randint(3, 7); segs = gen_segs(rng, n); h = big_h(rng)
    return render_queue(h, segs)
def tf_34(g):
    segs = read_queue(g); n = len(segs)
    if n < 3: return None
    mid = n // 2
    new = segs[:mid] + segs[mid + 1:]
    return render_queue(len(g), new)
rule("queue_remove_middle_object", "The object standing in the middle of the queue is removed and the two sides close the gap.", gi_34, tf_34)


# 35 ---------------------------------------------------------------
def gi_35(rng):
    n = rng.randint(3, 6); segs = gen_segs(rng, n, wlo=1, whi=3)
    sw = rng.randint(2, 5)
    body = render_queue_rows(sw, segs)
    H = len(body)
    idx = rng.randint(1, n - 1)
    r0 = 0
    for i, (_, ht) in enumerate(segs):
        if i == idx: break
        r0 += ht + 1
    marker = [[GREY] if r == r0 else [0] for r in range(H)]
    return [m + [0] + row for m, row in zip(marker, body)]
def tf_35(g):
    H = len(g)
    mcol = [row[0] for row in g]
    body = [row[2:] for row in g]
    midx = next((i for i, v in enumerate(mcol) if v == GREY), None)
    if midx is None: return None
    segs = read_queue_rows(body)
    idx = None; r = 0
    for i, (_, ht) in enumerate(segs):
        if r <= midx < r + ht: idx = i; break
        r += ht + 1
    if idx is None or idx == 0: return None
    new = [segs[idx]] + segs[:idx] + segs[idx + 1:]
    return render_queue_rows(len(body[0]), new)
rule("stack_marked_moves_to_top", "The block marked by a dot beside it moves to the top of the stack; the rest keep their relative order below it.", gi_35, tf_35)


# 36 ---------------------------------------------------------------
def gi_36(rng):
    nA = rng.randint(2, 4); nB = rng.randint(2, 4)
    segsA = gen_segs(rng, nA); segsB = gen_segs(rng, nB)
    ha = big_h(rng, hi=5)
    bodyA = render_queue(ha, segsA); bodyB = render_queue(ha, segsB)
    wA, wB = len(bodyA[0]), len(bodyB[0]); W = max(wA, wB)
    padA = [row + [0] * (W - wA) for row in bodyA]
    padB = [row + [0] * (W - wB) for row in bodyB]
    return padA + [[0] * W] + padB
def tf_36(g):
    H = len(g)
    sep = next((r for r in range(H) if all(v == 0 for v in g[r])), None)
    if sep is None: return None
    top, bottom = g[:sep], g[sep + 1:]
    A, B = read_queue(top), read_queue(bottom)
    if not A or not B: return None
    new = A + B
    return render_queue(len(top), new)
rule("queue_concat_two_rows", "Two queues stacked with a blank row between them join end to end into a single queue, the top queue first.", gi_36, tf_36)


# 37 ---------------------------------------------------------------
def gi_37(rng):
    n = rng.randint(4, 7); segs = []; prev = None
    for i in range(n):
        c = prev if (i > 0 and rng.random() < 0.45) else rng.choice(PALETTE)
        segs.append((c, rng.randint(1, 3))); prev = c
    runs = []
    i = 0
    while i < len(segs):
        j = i
        while j + 1 < len(segs) and segs[j + 1][0] == segs[i][0]: j += 1
        runs.append(j - i); i = j + 1
    if max(runs) < 1: return None
    h = big_h(rng)
    return render_queue(h, segs)
def tf_37(g):
    segs = read_queue(g)
    runs = []
    i = 0
    while i < len(segs):
        j = i
        while j + 1 < len(segs) and segs[j + 1][0] == segs[i][0]: j += 1
        runs.append((i, j)); i = j + 1
    if not runs: return None
    longest = max(runs, key=lambda r: r[1] - r[0])
    new = segs[:longest[0]] + segs[longest[1] + 1:]
    if not new or new == segs: return None
    return render_queue(len(g), new)
rule("queue_remove_longest_run", "The longest unbroken run of same-coloured objects in the queue is deleted entirely, and the rest close up.", gi_37, tf_37)


# 38 ---------------------------------------------------------------
def gi_38(rng):
    n = rng.randint(4, 8); segs = gen_segs(rng, n); h = big_h(rng)
    return render_queue(h, segs)
def tf_38(g):
    segs = read_queue(g); n = len(segs)
    if n < 4: return None
    half = n // 2
    new = segs[:half][::-1] + segs[half:]
    if new == segs: return None
    return render_queue(len(g), new)
rule("queue_reverse_front_half", "The front half of the queue reverses in place; the back half stays as it was.", gi_38, tf_38)


# 39 ---------------------------------------------------------------
def gi_39(rng):
    n = rng.randint(4, 8); segs = gen_segs(rng, n); h = big_h(rng)
    return render_queue(h, segs)
def tf_39(g):
    segs = read_queue(g); n = len(segs)
    if n < 4: return None
    half = n // 2
    new = segs[:half] + segs[half:][::-1]
    if new == segs: return None
    return render_queue(len(g), new)
rule("queue_reverse_back_half", "The back half of the queue reverses in place; the front half stays as it was.", gi_39, tf_39)


# 40 ---------------------------------------------------------------
def gi_40(rng):
    n = rng.randint(3, 6); segs = gen_segs(rng, n); h = big_h(rng, hi=5)
    body = render_queue(h, segs)
    idx = rng.randint(0, n - 2)
    col = seg_col_of(segs, idx)
    return with_marker_row(body, {col})
def tf_40(g):
    mrow, body = split_marker(g)
    mcol = next((c for c, v in enumerate(mrow) if v == GREY), None)
    if mcol is None: return None
    segs = read_queue(body)
    idx = None; c = 0
    for i, (_, wd) in enumerate(segs):
        if c <= mcol < c + wd: idx = i; break
        c += wd + 1
    if idx is None or idx == len(segs) - 1: return None
    new = segs[:idx] + segs[idx + 1:] + [segs[idx]]
    return render_queue(len(body), new)
rule("queue_marked_moves_to_back", "The object marked by a dot above it moves all the way to the back of the queue; the rest keep their relative order.", gi_40, tf_40)
