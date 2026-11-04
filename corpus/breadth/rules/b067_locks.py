# b067_locks.py -- LOCKS, KEYS AND RELEASE: objects are held (in a capped lane, a cage, a room, behind a
# gate cell, above a door) and are released, moved, rolled out or recoloured only while a stated condition holds;
# otherwise they stay. Lane rules share one scene: grey-5-walled lanes capped at one end, plus a key strip.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

WALL = 5
KEYS = [1, 2, 3, 4, 6, 7, 8, 9]
KEYS8 = [1, 2, 3, 4, 6, 7, 9]


# ======================= lane scene: lanes at rows 1,3,..; grey walls on even rows; key strip last row =======================
def _pick(rng, minw=6):
    if rng.random() < 0.5:
        k, W = rng.randint(10, 14), rng.randint(21, 30)
    else:
        k, W = rng.randint(2, 8), rng.randint(minw, 20)
    return min(k, W - 3), W


def _asm(rng, lanes, keyrow, rev=True, extra=()):
    k, W = len(lanes), len(keyrow)
    g = blank(2 * k + 2, W)
    for r in range(0, 2 * k + 1, 2): g[r] = [WALL] * W
    for i, L in enumerate(lanes):
        L = L[:]
        if rev and rng.random() < 0.5: L.reverse()
        g[2 * i + 1] = L
    g[-1] = keyrow[:]
    for r, c, v in extra: g[r][c] = v
    return transpose(g) if rng.random() < 0.5 else g


def _mk(rng, per_lane, keys=None, prep=None, rev=True, minw=6):
    k, W = _pick(rng, minw)
    st = {'k': k, 'W': W, 'a': rng.randrange(k), 'extra': []}
    st['b'] = (st['a'] + rng.randint(1, k - 1)) % k
    if prep: prep(rng, st)
    lanes = [[WALL] + [0] * (W - 1) for _ in range(k)]
    keyrow = [0] * W
    for i in range(k): per_lane(rng, lanes[i], i, st)
    if keys: keys(rng, keyrow, lanes, st)
    return _asm(rng, lanes, keyrow, rev, st['extra'])


def _canon(fn, rev=True):
    def tf(g):
        H, W = dims(g)
        if H < 6 or W < 6: return None
        row = g[1]
        hz = any(row[i] != WALL and row[i + 1] != WALL for i in range(W - 1))
        c = copy(g) if hz else transpose(g)
        H, W = dims(c)
        if H % 2: return None
        n = (H - 2) // 2
        fl = []
        for i in range(n):
            L = c[2 * i + 1]
            if L[0] == WALL and L[-1] != WALL: fl.append(False)
            elif L[-1] == WALL and L[0] != WALL:
                if not rev: return None
                fl.append(True); c[2 * i + 1] = L[::-1]
            else: return None
        try:
            out = fn(c)
        except (ValueError, IndexError, KeyError):
            return None
        if out is None: return None
        for i in range(n):
            if fl[i]: out[2 * i + 1] = out[2 * i + 1][::-1]
        return out if hz else transpose(out)
    return tf


def _rows(c): return range(1, len(c) - 1, 2)
def _first(L): return next(i for i in range(1, len(L)) if L[i] != 0)
def _roll(L, p, q=None):
    q = len(L) - 1 if q is None else q
    v = L[p]; L[p] = 0; L[q] = v


def _keycols(rng, keyrow, cols_colours):
    W = len(keyrow)
    cols = rng.sample(range(W), len(cols_colours))
    for c, v in zip(cols, cols_colours): keyrow[c] = v


LP = "In a stack of lanes (rows walled in grey 5, or columns if the grid is turned), each capped by a grey 5 at one end and open at the other, "
KS = "the key strip (the last row, or last column when lanes are columns, beyond the final wall)"


# ---------------------------------------------------------------- 1 gate absent
def _g1(rng, L, i, st):
    W = st['W']; p = rng.randint(1, W - 4); L[p] = 3
    if i == st['b'] or (i != st['a'] and rng.random() < 0.5): L[rng.randint(p + 1, W - 2)] = 2
def gi1(rng): return _mk(rng, _g1)
def _t1(c):
    for r in _rows(c):
        L = c[r]
        if 2 not in L: _roll(L, L.index(3))
    return c
rule("gate_absent_marker_rolls_out", LP + "a marker (3) rolls to the open end cell of its lane only if the lane holds no gate cell (2), otherwise it stays where it is.", gi1, _canon(_t1))


# ---------------------------------------------------------------- 2 slide until blocked unless gated
def _g2(rng, L, i, st):
    W = st['W']; p = rng.randint(1, W - 5); L[p] = 3
    for q in rng.sample(range(p + 2, W - 1), min(rng.randint(0, 2), W - p - 3)): L[q] = 8
    if i == st['b'] or (i != st['a'] and rng.random() < 0.4):
        L[rng.choice([x for x in range(1, W - 1) if L[x] == 0])] = 2
def gi2(rng): return _mk(rng, _g2, minw=7)
def _t2(c):
    for r in _rows(c):
        L = c[r]
        if 2 in L: continue
        p = L.index(3); j = p
        while j + 1 < len(L) and L[j + 1] == 0: j += 1
        _roll(L, p, j)
    return c
rule("ungated_marker_slides_until_blocked", LP + "a marker (3) slides toward the open end until the next cell is nonempty (a blocker 8 or the grid edge), but only if its lane has no gate cell (2) anywhere; a gated lane keeps its marker still.", gi2, _canon(_t2))


# ---------------------------------------------------------------- 3 key of marker colour
def _p3(rng, st):
    st['pal'] = rng.sample(KEYS, rng.randint(2, 5))
    st['ks'] = rng.sample(st['pal'], rng.randint(1, len(st['pal']) - 1))
def _g3(rng, L, i, st):
    W = st['W']; pal, ks = st['pal'], st['ks']
    col = rng.choice(ks) if i == st['a'] else rng.choice([x for x in pal if x not in ks]) if i == st['b'] else rng.choice(pal)
    L[rng.randint(1, W - 3)] = col
def _k3(rng, keyrow, lanes, st): _keycols(rng, keyrow, st['ks'])
def gi3(rng): return _mk(rng, _g3, _k3, _p3)
def _t3(c):
    ks = set(c[-1]) - {0}
    for r in _rows(c):
        L = c[r]; p = _first(L)
        if L[p] in ks: _roll(L, p)
    return c
rule("key_of_marker_colour_rolls_marker_out", LP + "a lane's single marker rolls to the open end if the key strip holds a cell of the marker's own colour, otherwise it stays; key cells are left in place.", gi3, _canon(_t3))


# ---------------------------------------------------------------- 4 key consumed, first lane gets it
def _p4(rng, st):
    st['pal'] = rng.sample(KEYS, rng.randint(2, 3))
    st['kc'] = {c: rng.randint(0, 2) for c in st['pal']}
    st['kc'][st['pal'][0]] = max(1, st['kc'][st['pal'][0]])
def _g4(rng, L, i, st):
    W = st['W']; col = st['pal'][0] if i == st['a'] else rng.choice(st['pal']); L[rng.randint(1, W - 3)] = col
def _k4(rng, keyrow, lanes, st):
    cols = [c for c, n in st['kc'].items() for _ in range(n)]
    rng.shuffle(cols); _keycols(rng, keyrow, cols)
def gi4(rng): return _mk(rng, _g4, _k4, _p4)
def _t4(c):
    av = {}
    for i, v in enumerate(c[-1]):
        if v: av.setdefault(v, []).append(i)
    for r in _rows(c):
        L = c[r]; p = _first(L)
        if av.get(L[p]):
            c[-1][av[L[p]].pop(0)] = 0; _roll(L, p)
    return c
rule("used_key_is_erased_first_lane_gets_it", LP + "a marker rolls to the open end if the key strip still holds an unused key of its colour, and that key cell is erased on use; lanes are served from the first wall onward (top, or left when lanes are columns), and a key of one colour serves only one lane, the leftmost such key in the strip being the one used.", gi4, _canon(_t4))


# ---------------------------------------------------------------- 5-7 two gate cells with AND / OR / XOR
GP = [1, 2, 4, 6, 7, 8, 9]
def _pair_rule(pred):
    def prep(rng, st):
        st['pal'] = rng.sample(GP, 4); st['ks'] = rng.sample(st['pal'], 2)
    def per(rng, L, i, st):
        W = st['W']; pal, ks = st['pal'], st['ks']
        for _ in range(60):
            x, y = rng.sample(pal, 2)
            ok = pred(x in ks, y in ks)
            if i == st['a'] and not ok: continue
            if i == st['b'] and ok: continue
            break
        p = rng.randint(1, W - 5); L[p] = 3
        q1, q2 = sorted(rng.sample(range(p + 1, W - 1), 2)); L[q1], L[q2] = x, y
    def keys(rng, keyrow, lanes, st): _keycols(rng, keyrow, st['ks'])
    def tf(c):
        ks = set(c[-1]) - {0}
        for r in _rows(c):
            L = c[r]; p = L.index(3)
            gs = [i for i in range(1, len(L)) if L[i] not in (0, 3)]
            if len(gs) != 2: continue
            if pred(L[gs[0]] in ks, L[gs[1]] in ks):
                for i in gs: L[i] = 0
                _roll(L, p)
        return c
    return (lambda rng: _mk(rng, per, keys, prep, minw=7)), _canon(tf)
gi5, t5 = _pair_rule(lambda a, b: a and b)
rule("two_gates_both_keys_needed", LP + "each lane has a marker (3) followed by two gate cells of different colours; the lane opens only if the key strip holds a key of both gate colours: then both gate cells are erased and the marker rolls to the open end; otherwise the lane is unchanged.", gi5, t5)
gi6, t6 = _pair_rule(lambda a, b: a or b)
rule("two_gates_either_key_enough", LP + "each lane has a marker (3) followed by two gate cells of different colours; the lane opens if the key strip holds a key of at least one of the two gate colours: then both gate cells are erased and the marker rolls to the open end; otherwise the lane is unchanged.", gi6, t6)
gi7, t7 = _pair_rule(lambda a, b: a != b)
rule("two_gates_exactly_one_key", LP + "each lane has a marker (3) followed by two gate cells of different colours; the lane opens only if the key strip holds a key of exactly one of the two gate colours (not both, not neither): then both gate cells are erased and the marker rolls to the open end; otherwise the lane is unchanged.", gi7, t7)


# ---------------------------------------------------------------- 8 series locks
def _p8(rng, st):
    st['pal'] = rng.sample(GP, 5); st['ks'] = rng.sample(st['pal'], rng.randint(2, 3))
def _g8(rng, L, i, st):
    W = st['W']; pal, ks = st['pal'], st['ks']
    p = rng.randint(1, W - 6); L[p] = 3
    n = rng.randint(1, 3)
    for q in sorted(rng.sample(range(p + 1, W - 1), n)): L[q] = rng.choice(pal)
    if i == st['a']:
        q = next(j for j in range(p + 1, W) if L[j]); L[q] = rng.choice(ks)
def _k8(rng, keyrow, lanes, st): _keycols(rng, keyrow, st['ks'])
def gi8(rng): return _mk(rng, _g8, _k8, _p8, minw=8)
def _t8(c):
    ks = set(c[-1]) - {0}
    for r in _rows(c):
        L = c[r]; p = L.index(3); dest = len(L) - 1
        for i in range(p + 1, len(L)):
            if L[i]:
                if L[i] in ks: L[i] = 0
                else: dest = i - 1; break
        _roll(L, p, dest)
    return c
rule("locks_in_series_stop_at_first_unkeyed", LP + "a marker (3) is followed by 1-3 lock cells; scanning from the marker toward the open end, each lock whose colour appears in the key strip is erased, and the marker advances until it sits directly before the first lock whose colour is not in the key strip (later locks stay untouched), or at the open end if every lock was keyed.", gi8, _canon(_t8))


# ---------------------------------------------------------------- 9 wrong key jams (key in wall touching lock)
def _p9(rng, st): st['pal'] = [1, 2, 4, 6, 7, 9]
def _g9(rng, L, i, st):
    W = st['W']; pal = st['pal']
    p = rng.randint(1, W - 5); L[p] = 3
    q = rng.randint(p + 2, W - 2); a = rng.choice(pal); L[q] = a
    if i == st['a']: b = a
    elif i == st['b']: b = rng.choice([x for x in pal if x != a])
    elif rng.random() < 0.3: return
    else: b = a if rng.random() < 0.5 else rng.choice([x for x in pal if x != a])
    st['extra'].append((2 * i + 2, q, b))
def gi9(rng): return _mk(rng, _g9, None, _p9, rev=False, minw=8)
def _t9(c):
    for r in _rows(c):
        L = c[r]; p = L.index(3)
        q = next(i for i in range(1, len(L)) if L[i] not in (0, 3))
        for rr in (r + 1, r - 1):
            if c[rr][q] != WALL:
                if c[rr][q] == L[q]:
                    L[q] = 0; c[rr][q] = WALL; _roll(L, p)
                else: L[q] = 8
                break
    return c
rule("wall_key_matching_lock_opens_wrong_jams", "In a stack of lanes (rows walled in grey 5, or columns if turned) capped by a grey 5 at the left (top) end, a marker (3) sits before a lock cell, and a key cell may replace the wall cell directly beside the lock (on the side away from or toward the next lane); a key of the lock's colour erases the lock, restores that wall cell to grey 5 and rolls the marker to the open end, a key of another colour turns the lock into colour 8 (jammed) and the marker stays, and a lock with no touching key is unchanged.", gi9, _canon(_t9, rev=False))


# ---------------------------------------------------------------- 10 key in the same lane beyond lock
def _g10(rng, L, i, st):
    W = st['W']; pal = st['pal']
    p = rng.randint(1, W - 6); L[p] = 3
    q = rng.randint(p + 1, W - 4); a = rng.choice(pal); L[q] = a
    s = rng.randint(q + 2, W - 2)
    L[s] = a if (i == st['a'] or (i != st['b'] and rng.random() < 0.5)) else rng.choice([x for x in pal if x != a])
def _k10(rng, keyrow, lanes, st): _keycols(rng, keyrow, [rng.choice(st['pal']) for _ in range(rng.randint(2, 5))])
def gi10(rng): return _mk(rng, _g10, _k10, _p9, minw=8)
def _t10(c):
    for r in _rows(c):
        L = c[r]; p = L.index(3)
        a, b = [i for i in range(1, len(L)) if L[i] not in (0, 3)]
        if L[a] == L[b]:
            L[a] = L[b] = 0; _roll(L, p)
    return c
rule("key_in_same_lane_beyond_lock_opens", LP + "a marker (3) is followed by a lock cell and then, further on in the same lane, a key cell; if the key's colour equals the lock's colour both cells are erased and the marker rolls to the open end, otherwise the lane is unchanged; the loose cells in the key strip are decoys and are ignored.", gi10, _canon(_t10))


# ---------------------------------------------------------------- 11 release order from key reading order
def _p11(rng, st): st['pal'] = rng.sample(KEYS, rng.randint(3, 4))
def _g11(rng, L, i, st):
    W = st['W']; n = rng.randint(1, len(st['pal']))
    for q, col in zip(rng.sample(range(1, W - 1), n), rng.sample(st['pal'], n)): L[q] = col
def _k11(rng, keyrow, lanes, st):
    cols = sorted(rng.sample(range(len(keyrow)), len(st['pal']))); cs = st['pal'][:]; rng.shuffle(cs)
    for c, v in zip(cols, cs): keyrow[c] = v
def gi11(rng): return _mk(rng, _g11, _k11, _p11, minw=8)
def _t11(c):
    order = [v for v in c[-1] if v]
    for r in _rows(c):
        L = c[r]; ms = {v for v in L[1:] if v}
        seq = [v for v in order if v in ms]
        if len(seq) != len(ms): return None
        for i in range(1, len(L)): L[i] = 0
        for j, v in enumerate(seq): L[len(L) - 1 - j] = v
    return c
rule("markers_released_in_key_reading_order", LP + "each lane holds 1-4 markers of distinct colours and the key strip lists every marker colour once; markers are released one at a time in the strip's reading order (left to right, or top to bottom when lanes are columns), each rolling to the open end and stopping against the previously released one, so the first released ends at the open end cell and later ones pile up behind it.", gi11, _canon(_t11))


# ---------------------------------------------------------------- 12 counter bar of released lanes
def _g12(rng, L, i, st):
    W = st['W']; p = rng.randint(1, W - 4); L[p] = 3
    if i == st['b'] or (i != st['a'] and rng.random() < 0.5): L[rng.randint(p + 1, W - 2)] = 2
def gi12(rng): return _mk(rng, _g12)
def _t12(c):
    n = 0
    for r in _rows(c):
        L = c[r]
        if 2 not in L: _roll(L, L.index(3)); n += 1
    if n > len(c[0]): return None
    for i in range(n): c[-1][i] = 4
    return c
rule("released_lanes_counted_as_key_strip_bar", LP + "a marker (3) rolls to the open end only if its lane has no gate cell (2), and the number of lanes that released is drawn as a bar of colour 4 filling the key strip from its first cell (left, or top when lanes are columns).", gi12, _canon(_t12))


# ---------------------------------------------------------------- 13 timed release by digit
def _g13(rng, L, i, st):
    W = st['W']; L[1] = rng.randint(1, 4); p = rng.randint(2, W - 6); L[p] = 9
    if rng.random() < 0.4: L[rng.randint(p + 2, W - 2)] = 8
def gi13(rng): return _mk(rng, _g13, minw=8)
def _t13(c):
    for r in _rows(c):
        L = c[r]; d = L[1]; L[1] = 0; p = L.index(9); j = p
        for _ in range(d):
            if j + 1 < len(L) and L[j + 1] == 0: j += 1
            else: break
        _roll(L, p, j)
    return c
rule("timer_digit_sets_roll_steps", LP + "the cell next to the cap holds a timer digit d (colour value 1-4) and a marker (9) sits further along; the timer cell is erased and the marker rolls d cells toward the open end, stopping early if the next cell is nonempty (blocker 8) or the grid edge.", gi13, _canon(_t13), digits=True)


# ---------------------------------------------------------------- 14 latch packs
def _g14(rng, L, i, st):
    W = st['W']; n = rng.randint(1, 4)
    for q in rng.sample(range(2, W - 1), n): L[q] = 3
    if i == st['b'] or (i != st['a'] and rng.random() < 0.5): L[1] = 2
def gi14(rng): return _mk(rng, _g14, minw=8)
def _t14(c):
    for r in _rows(c):
        L = c[r]
        if L[1] == 2: continue
        n = sum(1 for v in L if v == 3)
        for i in range(1, len(L)): L[i] = 0
        for j in range(n): L[len(L) - 1 - j] = 3
    return c
rule("latch_at_cap_holds_markers_else_pack_out", LP + "a lane holds 1-4 markers (3), and a latch cell (2) may sit directly beside the cap; with a latch the markers stay put, without one they are all released and pack against the open end in a contiguous run.", gi14, _canon(_t14))


# ---------------------------------------------------------------- 15 combination lock
def _p15(rng, st):
    m = rng.randint(2, 3); st['code'] = rng.sample(GP, m)
def _g15(rng, L, i, st):
    W = st['W']; code = st['code']; m = len(code)
    if i == st['a']: seq = code[:]
    elif i == st['b']: seq = code[::-1]
    elif rng.random() < 0.5: seq = code[:]
    else:
        seq = code[:]; j = rng.randrange(m); seq[j] = rng.choice([x for x in GP if x != code[j]])
    p = rng.randint(1, W - m - 3); L[p] = 3
    q = rng.randint(p + 1, W - m - 1)
    for j, v in enumerate(seq): L[q + j] = v
def _k15(rng, keyrow, lanes, st):
    for j, v in enumerate(st['code']): keyrow[j] = v
def gi15(rng): return _mk(rng, _g15, _k15, _p15, minw=8)
def _t15(c):
    code = [v for v in c[-1] if v]
    for r in _rows(c):
        L = c[r]; p = L.index(3)
        idx = [i for i in range(1, len(L)) if L[i] not in (0, 3)]
        if [L[i] for i in idx] == code:
            for i in idx: L[i] = 0
            _roll(L, p)
    return c
rule("lock_sequence_must_equal_key_code", LP + "the key strip holds a code of 2-3 coloured cells starting at its first cell, each lane has a marker (3) followed by a run of lock cells, and a lane whose lock colours read from the cap side to the open end equal the code read from the strip's first cell (left, or top) onward has its locks erased and its marker rolled to the open end; any other lane is unchanged.", gi15, _canon(_t15))


# ---------------------------------------------------------------- 16 gate holds back only markers behind it
def _g16(rng, L, i, st):
    W = st['W']; n = rng.randint(2, 4)
    gated = i == st['b'] or (i != st['a'] and rng.random() < 0.6)
    pos = sorted(rng.sample(range(1, W - 1), n + (1 if gated else 0)))
    if gated:
        g = rng.randint(1, n - 1); L[pos[g]] = 2; pos.pop(g)
    for q in pos: L[q] = 3
def gi16(rng): return _mk(rng, _g16, minw=8)
def _t16(c):
    for r in _rows(c):
        L = c[r]; gi = L.index(2) if 2 in L else 0
        mv = [i for i in range(gi + 1, len(L)) if L[i] == 3]
        for i in mv: L[i] = 0
        for j in range(len(mv)): L[len(L) - 1 - j] = 3
    return c
rule("gate_holds_back_only_markers_behind_it", LP + "a lane holds 2-4 markers (3) and maybe one gate cell (2); all markers on the open-end side of the gate (or all markers if there is no gate) are released and pack against the open end in a contiguous run, while markers on the cap side of the gate stay where they are and the gate stays.", gi16, _canon(_t16))


# ---------------------------------------------------------------- 17 marker digit versus gate count
def _g17(rng, L, i, st):
    W = st['W']; g = rng.randint(1, 4); v = rng.choice([1, 2, 3, 4, 6])
    if i == st['a']: v = rng.choice([x for x in [1, 2, 3, 4, 6] if x > g] or [6]); g = min(g, 3) if v <= g else g
    p = rng.randint(1, W - 3 - g); L[p] = v
    for q in rng.sample(range(p + 1, W - 1), g): L[q] = 8
def gi17(rng): return _mk(rng, _g17, minw=8)
def _t17(c):
    for r in _rows(c):
        L = c[r]; p = _first(L); v = L[p]
        g = [i for i in range(len(L)) if L[i] == 8]
        if v > len(g):
            for i in g: L[i] = 0
            _roll(L, p)
    return c
rule("marker_value_must_exceed_gate_count", LP + "a marker whose colour value v (1-4 or 6) is its force sits before g gate cells (8); if v is strictly greater than g all gate cells are erased and the marker rolls to the open end, and if v is less than or equal to g the lane is unchanged.", gi17, _canon(_t17), digits=True)


# ---------------------------------------------------------------- 18 master key
def _p18(rng, st):
    st['pal'] = rng.sample([1, 2, 3, 4, 6, 7, 8], rng.randint(3, 5)); st['master'] = rng.random() < 0.5
    st['ks'] = rng.sample(st['pal'], rng.randint(1, 2))
def _g18(rng, L, i, st):
    W = st['W']; L[rng.randint(1, W - 3)] = rng.choice(st['pal'])
def _k18(rng, keyrow, lanes, st):
    ks = st['ks'][:] + ([9] if st['master'] else [])
    _keycols(rng, keyrow, ks)
def gi18(rng): return _mk(rng, _g18, _k18, _p18)
def _t18(c):
    ks = set(c[-1]) - {0}
    for r in _rows(c):
        L = c[r]; p = _first(L)
        if 9 in ks or L[p] in ks: _roll(L, p)
    return c
rule("master_key_opens_every_lane", LP + "a lane's single marker rolls to the open end if the key strip holds a key of the marker's colour, and if the strip holds a master key (9) every marker rolls out whatever its colour (markers are never colour 9); otherwise the lane stays.", gi18, _canon(_t18))


# ---------------------------------------------------------------- 19 keyhole column
def _p19(rng, st):
    st['cols'] = rng.sample(range(2, st['W'] - 1), st['k']); st['pal'] = [1, 2, 4, 6, 7, 9]; st['kr'] = {}
def _g19(rng, L, i, st):
    W = st['W']; q = st['cols'][i]; a = rng.choice(st['pal']); L[q] = a
    L[rng.randint(1, q - 1)] = 3
    if i == st['a']: v = a
    elif i == st['b']: v = rng.choice([x for x in st['pal'] if x != a])
    else: v = rng.choice([0, a, rng.choice([x for x in st['pal'] if x != a])])
    st['kr'][q] = v
def _k19(rng, keyrow, lanes, st):
    for q, v in st['kr'].items(): keyrow[q] = v
def gi19(rng): return _mk(rng, _g19, _k19, _p19, rev=False)
def _t19(c):
    kr = c[-1]
    for r in _rows(c):
        L = c[r]; p = L.index(3)
        q = next(i for i in range(1, len(L)) if L[i] not in (0, 3))
        if kr[q] == L[q]:
            L[q] = 0; _roll(L, p)
    return c
rule("keyhole_column_key_must_match_lock", "In a stack of lanes (rows walled in grey 5, or columns if turned) capped by a grey 5 at the left (top) end, a marker (3) sits before a lock cell; the lane opens only if the key strip cell in the same column (row, when lanes are columns) as the lock has the lock's colour, then the lock is erased and the marker rolls to the open end; the key stays, and a lane with an empty or different key cell is unchanged.", gi19, _canon(_t19, rev=False))


# ---------------------------------------------------------------- 20 quota of keys
def _g20(rng, L, i, st):
    W = st['W']
    for q in rng.sample(range(1, W - 1), rng.randint(2, 5)): L[q] = 3
def _k20(rng, keyrow, lanes, st): _keycols(rng, keyrow, [6] * rng.randint(1, 3))
def gi20(rng): return _mk(rng, _g20, _k20, minw=8)
def _t20(c):
    n = sum(1 for v in c[-1] if v == 6)
    for r in _rows(c):
        L = c[r]; ms = [i for i in range(1, len(L)) if L[i] == 3]
        mv = ms[-n:] if n else []
        for i in mv: L[i] = 0
        for j in range(len(mv)): L[len(L) - 1 - j] = 3
    return c
rule("key_count_releases_that_many_markers", LP + "the key strip holds n keys (6) and every lane holds 2-5 markers (3); in each lane the n markers nearest the open end (all of them if n is larger) are released and pack against the open end, and the remaining markers stay where they are.", gi20, _canon(_t20))


# ---------------------------------------------------------------- 21 tag colour transfer
def _p21(rng, st):
    st['pal'] = rng.sample(GP, 4); st['ks'] = rng.sample(st['pal'], 2)
def _g21(rng, L, i, st):
    W = st['W']; pal, ks = st['pal'], st['ks']
    L[1] = rng.choice(ks) if i == st['a'] else rng.choice([x for x in pal if x not in ks]) if i == st['b'] else rng.choice(pal)
    L[rng.randint(2, W - 3)] = 3
def gi21(rng): return _mk(rng, _g21, _k18 if False else (lambda rng, kr, l, st: _keycols(rng, kr, st['ks'])), _p21)
def _t21(c):
    ks = set(c[-1]) - {0}
    for r in _rows(c):
        L = c[r]
        if L[1] in ks: L[L.index(3)] = L[1]
    return c
rule("keyed_tag_recolours_marker_in_place", LP + "a tag cell sits beside the cap and a marker (3) further along; if the key strip holds a cell of the tag's colour the marker is recoloured to the tag's colour in place (it does not move), otherwise the lane is unchanged.", gi21, _canon(_t21))


# ---------------------------------------------------------------- 22 key run length matches lock run length
def _p22(rng, st):
    W = st['W']; runs = []; pos = rng.randint(0, 1)
    while True:
        l = rng.randint(1, 4)
        if pos + l > W: break
        runs.append((pos, l)); pos += l + 1
        if len(runs) >= 4 or (len(runs) >= 2 and rng.random() < 0.3): break
    if len(runs) < 2: runs = [(0, 1), (2, 2)]
    st['runs'] = runs; st['lens'] = {l for _, l in runs}
def _g22(rng, L, i, st):
    W = st['W']; lens = sorted(st['lens']); other = [x for x in range(1, 5) if x not in lens]
    if i == st['a'] or (i != st['b'] and rng.random() < 0.5) or not other: n = rng.choice(lens)
    else: n = rng.choice(other)
    p = rng.randint(1, W - 3 - n); L[p] = 3
    for j in range(n): L[p + 1 + j] = 2
def _k22(rng, keyrow, lanes, st):
    for pos, l in st['runs']:
        for j in range(l): keyrow[pos + j] = 4
def gi22(rng): return _mk(rng, _g22, _k22, _p22, minw=8)
def _t22(c):
    lens = set(); n = 0
    for v in list(c[-1]) + [0]:
        if v == 4: n += 1
        elif n: lens.add(n); n = 0
    for r in _rows(c):
        L = c[r]; locks = [i for i in range(len(L)) if L[i] == 2]
        if len(locks) in lens:
            for i in locks: L[i] = 0
            _roll(L, L.index(3))
    return c
rule("key_bar_length_must_equal_lock_bar_length", LP + "a marker (3) is followed by a bar of lock cells (2) of length 1-4 and the key strip holds several bars of key cells (4) separated by gaps; a lane opens if some key bar has exactly the lock bar's length, then its lock bar is erased and the marker rolls to the open end; otherwise it is unchanged.", gi22, _canon(_t22))


# ---------------------------------------------------------------- 23 colour matched gate blocks
def _p23(rng, st): st['pal'] = rng.sample(KEYS, rng.randint(2, 3))
def _g23(rng, L, i, st):
    W = st['W']; pal = st['pal']; c = rng.choice(pal)
    same = i == st['b'] or (i != st['a'] and rng.random() < 0.5)
    g = c if same else rng.choice([x for x in pal if x != c])
    p = rng.randint(1, W - 6 if same else W - 4); L[p] = c
    L[rng.randint(p + 3, W - 2) if same else rng.randint(p + 1, W - 2)] = g
def gi23(rng): return _mk(rng, _g23, None, _p23, minw=8)
def _t23(c):
    for r in _rows(c):
        L = c[r]; p, q = [i for i in range(1, len(L)) if L[i]]
        if L[p] == L[q]: _roll(L, p, q - 1)
        else: _roll(L, p)
    return c
rule("same_colour_gate_stops_marker_other_passes", LP + "a marker is followed by one gate cell; a gate of the marker's own colour stops the marker on the cell directly before it, a gate of any other colour lets the marker roll past it to the open end cell, and gates stay in place.", gi23, _canon(_t23))


# ---------------------------------------------------------------- 24 trail
def gi24(rng): return _mk(rng, _g12)
def _t24(c):
    for r in _rows(c):
        L = c[r]
        if 2 not in L:
            p = L.index(3)
            for i in range(p, len(L) - 1): L[i] = 8
            L[-1] = 3
    return c
rule("ungated_marker_rolls_out_leaving_trail", LP + "a marker (3) rolls to the open end cell only if its lane has no gate cell (2), and every cell it leaves (from its start cell up to the cell before the open end) is painted colour 8; gated lanes are unchanged.", gi24, _canon(_t24))


# ======================= cages, rooms and free-standing scenes =======================
def _gsize(rng):
    if rng.random() < 0.5: return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(9, 20), rng.randint(9, 20)


def _boxes(rng, H, W, specs, margin=1, tries=60):
    placed = []
    for h, w in specs:
        if h > H or w > W: continue
        for _ in range(tries):
            r, c = rng.randint(0, H - h), rng.randint(0, W - w)
            if all(r + h + margin <= r2 or r2 + h2 + margin <= r or c + w + margin <= c2 or c2 + w2 + margin <= c for r2, c2, h2, w2 in placed):
                placed.append((r, c, h, w)); break
    return placed


def _spot(rng, g, rows=None, cols=None):
    H, W = dims(g)
    cand = []
    for r in (range(H) if rows is None else rows):
        for c in (range(W) if cols is None else cols):
            if 0 <= r < H and 0 <= c < W and all(g[r + a][c + b] == 0 for a in (-1, 0, 1) for b in (-1, 0, 1) if 0 <= r + a < H and 0 <= c + b < W):
                cand.append((r, c))
    return rng.choice(cand) if cand else None


def _put(rng, g, col, rows=None, cols=None):
    s = _spot(rng, g, rows, cols)
    if s: g[s[0]][s[1]] = col
    return s


def _ncount(rng, g, lo, hi):
    H, W = dims(g)
    return rng.randint(lo, hi) if H * W < 400 else rng.randint(hi, 2 * hi)


def _cages(rng, pal, sizes=((3, 3), (4, 4), (5, 5), (3, 5), (5, 3), (4, 5)), nlo=2, nhi=5, items=(1, 3), border=None, margin=1):
    """Returns (grid, [(r,c,h,w,colour)]) with ring cages and colour-8 items inside."""
    for _ in range(50):
        H, W = _gsize(rng); g = blank(H, W)
        n = _ncount(rng, g, nlo, nhi)
        placed = _boxes(rng, H, W, [rng.choice(sizes) for _ in range(n)], margin)
        if len(placed) < 2: continue
        out = []
        for r, c, h, w in placed:
            col = border or rng.choice(pal)
            rect(g, r, c, r + h - 1, c + w - 1, col, fill=False)
            inner = [(y, x) for y in range(r + 1, r + h - 1) for x in range(c + 1, c + w - 1)]
            for y, x in rng.sample(inner, min(rng.randint(*items), len(inner))): g[y][x] = 8
            out.append((r, c, h, w, col))
        return g, out
    raise RuntimeError


def _rings(g, skip=(0, 8)):
    out = []
    for col in sorted({v for row in g for v in row} - set(skip)):
        for comp in components(g, col, conn8=False):
            r0, c0, r1, c1 = bbox(comp); h, w = r1 - r0 + 1, c1 - c0 + 1
            if h >= 3 and w >= 3 and len(comp) == 2 * (h + w) - 4:
                out.append(dict(col=col, r0=r0, c0=c0, r1=r1, c1=c1, cells=comp))
    return out


def _grey(g):
    """Grey (5) cages, complete or missing one non-corner cell (the lock/door)."""
    out = []
    for comp in components(g, 5, conn8=False):
        r0, c0, r1, c1 = bbox(comp); h, w = r1 - r0 + 1, c1 - c0 + 1
        p = 2 * (h + w) - 4
        if h >= 3 and w >= 3 and len(comp) in (p, p - 1):
            per = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if r in (r0, r1) or c in (c0, c1)]
            lock = [(r, c) for r, c in per if g[r][c] != 5]
            out.append(dict(r0=r0, c0=c0, r1=r1, c1=c1, cells=comp, lock=lock[0] if lock else None))
    return out


def _free(g, rings):
    cs = set()
    for b in rings:
        for r in range(b['r0'], b['r1'] + 1):
            for c in range(b['c0'], b['c1'] + 1): cs.add((r, c))
    H, W = dims(g)
    return [(r, c, g[r][c]) for r in range(H) for c in range(W) if g[r][c] and (r, c) not in cs]


def _inside(g, b, col=8):
    return [(r, c) for r in range(b['r0'] + 1, b['r1']) for c in range(b['c0'] + 1, b['c1']) if g[r][c] == col]


def _slide(g, cells, dr, dc):
    H, W = dims(g)
    for r, c in sorted(cells, key=lambda x: -(x[0] * dr + x[1] * dc)):
        v = g[r][c]; y, x = r, c
        while 0 <= y + dr < H and 0 <= x + dc < W and g[y + dr][x + dc] == 0: y += dr; x += dc
        g[r][c] = 0; g[y][x] = v


def _keysfor(rng, g, cols_counts):
    for col, n in cols_counts:
        for _ in range(n): _put(rng, g, col)


# ---------------------------------------------------------------- C1 key anywhere opens cage
def gc1(rng):
    pal = rng.sample(KEYS8, rng.randint(2, 4)); g, cg = _cages(rng, pal)
    cs = sorted({x[4] for x in cg}); opn = rng.sample(cs, rng.randint(1, max(1, len(cs) - 1)))
    _keysfor(rng, g, [(c, rng.randint(1, 2)) for c in opn])
    rest = [x for x in KEYS8 if x not in cs]
    if rest: _put(rng, g, rng.choice(rest))
    return g
def tc1(g):
    rs = _rings(g); ks = {v for _, _, v in _free(g, rs)}; out = copy(g)
    for b in rs:
        if b['col'] in ks:
            for r, c in b['cells']: out[r][c] = 0
    return out
rule("cage_opens_if_its_colour_key_exists", "A hollow cage (a rectangular ring of one colour, never 8, holding 8-cells) opens when a loose key cell of the cage's own colour exists anywhere in the grid: the ring is erased and the 8-cells stay; cages with no such key, and the keys, are unchanged.", gc1, tc1)


# ---------------------------------------------------------------- C2 opened cage drops floor, items fall
def tc2(g):
    rs = _rings(g); ks = {v for _, _, v in _free(g, rs)}; out = copy(g); it = []
    for b in rs:
        if b['col'] in ks:
            for c in range(b['c0'], b['c1'] + 1): out[b['r1']][c] = 0
            it += _inside(out, b)
    _slide(out, it, 1, 0)
    return out
rule("opened_cage_loses_floor_items_fall", "A hollow cage (rectangular ring, never colour 8, holding 8-cells) whose colour matches a loose key cell anywhere in the grid has its bottom wall row erased (corners included) and each 8-cell inside falls straight down, lowest first, until the cell below is nonempty or the grid edge; other cages and keys stay.", gc1, tc2)


# ---------------------------------------------------------------- C3 nested cages
def gc3(rng):
    for _ in range(50):
        H, W = _gsize(rng); g = blank(H, W)
        pal = rng.sample(KEYS8, rng.randint(3, 5))
        pl = _boxes(rng, H, W, [(7, 7)] * _ncount(rng, g, 1, 3), 1)
        if not pl: continue
        nests = []
        for r, c, h, w in pl:
            a, b = rng.sample(pal, 2); rect(g, r, c, r + 6, c + 6, a, fill=False)
            rect(g, r + 2, c + 2, r + 4, c + 4, b, fill=False); g[r + 3][c + 3] = 8; nests.append((a, b))
        outer_ok = rng.sample(range(len(nests)), rng.randint(1, len(nests)))
        for i, (a, b) in enumerate(nests):
            if i in outer_ok: _put(rng, g, a)
            if rng.random() < 0.6: _put(rng, g, b)
        return g
    raise RuntimeError
def tc3(g):
    rs = sorted(_rings(g), key=lambda b: -(b['r1'] - b['r0']) * (b['c1'] - b['c0'])); ks = {v for _, _, v in _free(g, rs)}
    out = copy(g); opened = []
    for b in rs:
        par = [p for p in opened + [x for x in rs if x not in opened] if p is not b and p['r0'] < b['r0'] and p['c0'] < b['c0'] and p['r1'] > b['r1'] and p['c1'] > b['c1']]
        ok = b['col'] in ks and all(p in opened for p in par)
        if ok:
            opened.append(b)
            for r, c in b['cells']: out[r][c] = 0
    return out
rule("inner_cage_opens_only_after_outer_opens", "Each nest is a 7x7 ring cage holding a 3x3 ring cage holding an 8-cell; a ring opens (is erased) only if a loose key cell of its own colour exists anywhere in the grid and, for the inner ring, only if its outer ring also opened; otherwise it stays, and the 8-cells and keys are never changed.", gc3, tc3)


# ---------------------------------------------------------------- C4 enough keys for the item count
def gc4(rng):
    pal = rng.sample(KEYS8, rng.randint(2, 3)); g, cg = _cages(rng, pal, items=(1, 3))
    cs = sorted({x[4] for x in cg})
    _keysfor(rng, g, [(c, rng.randint(0, 3)) for c in cs])
    if all(not any(v == cs[0] for _, _, v in _free(g, _rings(g))) for _ in [0]) and len(cs):
        _put(rng, g, cs[0]); _put(rng, g, cs[0])
    return g
def tc4(g):
    rs = _rings(g); fr = _free(g, rs); out = copy(g)
    for b in rs:
        if sum(1 for _, _, v in fr if v == b['col']) >= len(_inside(g, b)):
            for r, c in b['cells']: out[r][c] = 0
    return out
rule("cage_opens_with_enough_keys_for_items", "A hollow cage (rectangular ring, never colour 8, holding 1-3 cells of colour 8) opens, its ring being erased, when the number of loose key cells of the cage's colour in the whole grid is greater than or equal to the number of 8-cells inside it; otherwise it stays, and keys and 8-cells are unchanged.", gc4, tc4)


# ---------------------------------------------------------------- C5 touching key consumed
def gc5(rng):
    for _ in range(50):
        H, W = _gsize(rng); g = blank(H, W); pal = rng.sample([1, 2, 3, 4, 6, 7, 9], 4)
        pl = _boxes(rng, H, W, [rng.choice(((3, 3), (4, 4), (5, 5), (4, 5))) for _ in range(_ncount(rng, g, 2, 5))], 3)
        if len(pl) < 2: continue
        info = list(pl)
        for k, (r, c, h, w) in enumerate(info):
            rect(g, r, c, r + h - 1, c + w - 1, 5, fill=False)
            if rng.random() < 0.5: g[r + 1 + rng.randrange(h - 2)][c + 1 + rng.randrange(w - 2)] = 8
            a = rng.choice(pal); side = rng.choice('NSWE')
            if side == 'N': lr, lc, kr, kc = r, c + 1 + rng.randrange(w - 2), r - 1, None
            elif side == 'S': lr, lc, kr, kc = r + h - 1, c + 1 + rng.randrange(w - 2), r + h, None
            elif side == 'W': lr, lc, kr, kc = r + 1 + rng.randrange(h - 2), c, None, c - 1
            else: lr, lc, kr, kc = r + 1 + rng.randrange(h - 2), c + w - 1, None, c + w
            g[lr][lc] = a
            if kr is None: kr = lr
            if kc is None: kc = lc
            if 0 <= kr < H and 0 <= kc < W and g[kr][kc] == 0 and rng.random() < 0.85:
                g[kr][kc] = a if (k == 0 or rng.random() < 0.55) else rng.choice([x for x in pal if x != a])
        for _ in range(rng.randint(1, 4)): _put(rng, g, rng.choice(pal))
        return g
    raise RuntimeError
def tc5(g):
    H, W = dims(g); out = copy(g); any_ = False
    for b in _grey(g):
        if not b['lock']: continue
        lr, lc = b['lock']; a = g[lr][lc]
        kr, kc = (lr - 1, lc) if lr == b['r0'] else (lr + 1, lc) if lr == b['r1'] else (lr, lc - 1) if lc == b['c0'] else (lr, lc + 1)
        if 0 <= kr < H and 0 <= kc < W and g[kr][kc] == a:
            for r, c in b['cells']: out[r][c] = 0
            out[lr][lc] = 0; out[kr][kc] = 0
    return out
rule("touching_key_of_lock_colour_opens_and_is_used", "A grey 5 cage has one lock cell of some colour set into its wall (never at a corner); a key cell of the same colour directly outside that lock cell opens the cage: the whole cage including its lock and that key are erased, interior cells stay; a cage with a different-colour or no touching key, and all loose keys elsewhere, are unchanged.", gc5, tc5)


# ---------------------------------------------------------------- C6/C7 key in the cage's row (column) span
def _span_scene(rng, rowspan):
    pal = rng.sample(KEYS8, rng.randint(2, 4)); g, cg = _cages(rng, pal, margin=2)
    H, W = dims(g)
    for k, (r, c, h, w, col) in enumerate(cg):
        span = range(r, r + h) if rowspan else range(c, c + w)
        out = [x for x in range(H if rowspan else W) if x not in span]
        if k == 0 or rng.random() < 0.5:
            _put(rng, g, col, rows=span) if rowspan else _put(rng, g, col, cols=span)
        if rng.random() < 0.6 and out:
            _put(rng, g, col, rows=out) if rowspan else _put(rng, g, col, cols=out)
    return g
def gc6(rng): return _span_scene(rng, True)
def tc6(g):
    rs = _rings(g); fr = _free(g, rs); out = copy(g)
    for b in rs:
        if any(v == b['col'] and b['r0'] <= r <= b['r1'] for r, c, v in fr):
            for r, c in b['cells']: out[r][c] = 0
    return out
rule("cage_opens_if_key_shares_a_row_with_it", "A hollow cage (rectangular ring, never colour 8, holding 8-cells) opens, its ring being erased, when a loose key cell of the cage's colour lies in any row the cage occupies (top row to bottom row of the ring); a key of that colour in other rows does not count; 8-cells and keys stay.", gc6, tc6)
def gc7(rng): return _span_scene(rng, False)
def tc7(g):
    rs = _rings(g); fr = _free(g, rs); out = copy(g); it = []
    for b in rs:
        if any(v == b['col'] and b['c0'] <= c <= b['c1'] for r, c, v in fr):
            for c in range(b['c0'], b['c1'] + 1): out[b['r0']][c] = 0
            it += _inside(out, b)
    _slide(out, it, -1, 0)
    return out
rule("cage_roof_opens_if_key_shares_a_column_items_rise", "A hollow cage (rectangular ring, never colour 8, holding 8-cells) with a loose key cell of its colour in any column the cage occupies has its top wall row erased (corners included), and each 8-cell inside rises straight up, topmost first, until the cell above is nonempty or the grid edge; cages without such a key, and keys, stay.", gc7, tc7)


# ---------------------------------------------------------------- C8 key side chooses the exit wall
def gc8(rng):
    for _ in range(50):
        H, W = _gsize(rng); g = blank(H, W)
        pl = _boxes(rng, H, W, [rng.choice(((3, 3), (4, 4), (5, 5), (4, 5), (5, 4))) for _ in range(_ncount(rng, g, 2, 4))], 3)
        if len(pl) < 2: continue
        for k, (r, c, h, w) in enumerate(pl):
            rect(g, r, c, r + h - 1, c + w - 1, 5, fill=False)
            g[r + 1 + rng.randrange(h - 2)][c + 1 + rng.randrange(w - 2)] = 8
            if k == 0 or rng.random() < 0.75:
                s = rng.choice('NSWE')
                if s == 'N': y, x = r - 1, c + 1 + rng.randrange(w - 2)
                elif s == 'S': y, x = r + h, c + 1 + rng.randrange(w - 2)
                elif s == 'W': y, x = r + 1 + rng.randrange(h - 2), c - 1
                else: y, x = r + 1 + rng.randrange(h - 2), c + w
                if 0 <= y < H and 0 <= x < W: g[y][x] = 4
        return g
    raise RuntimeError
def tc8(g):
    H, W = dims(g); out = copy(g)
    for b in _grey(g):
        r0, c0, r1, c1 = b['r0'], b['c0'], b['r1'], b['c1']
        sides = []
        for c in range(c0 + 1, c1):
            if r0 > 0 and g[r0 - 1][c] == 4: sides.append('N')
            if r1 < H - 1 and g[r1 + 1][c] == 4: sides.append('S')
        for r in range(r0 + 1, r1):
            if c0 > 0 and g[r][c0 - 1] == 4: sides.append('W')
            if c1 < W - 1 and g[r][c1 + 1] == 4: sides.append('E')
        if len(sides) > 1: return None
        if not sides: continue
        s = sides[0]; it = _inside(g, b)
        if s in 'NS':
            for c in range(c0 + 1, c1): out[r0 if s == 'N' else r1][c] = 0
        else:
            for r in range(r0 + 1, r1): out[r][c0 if s == 'W' else c1] = 0
        dr, dc = {'N': (-1, 0), 'S': (1, 0), 'W': (0, -1), 'E': (0, 1)}[s]
        _slide(out, it, dr, dc)
    return out
rule("key_side_chooses_exit_wall_item_slides_out", "A grey 5 cage holds one 8-cell; if a key cell (4) touches the outside of one side of the cage (not at a corner), that side's wall cells between the corners are erased and the 8-cell slides in that direction until the next cell is nonempty or the grid edge; the key and a cage with no touching key stay.", gc8, tc8)


# ---------------------------------------------------------------- C9 items recoloured by key
def tc9(g):
    rs = _rings(g); ks = {v for _, _, v in _free(g, rs)}; out = copy(g)
    for b in rs:
        if b['col'] in ks:
            for r, c in _inside(g, b): out[r][c] = b['col']
    return out
rule("cage_key_recolours_items_inside", "A hollow cage (rectangular ring, never colour 8, holding 8-cells) stays closed, but when a loose key cell of the cage's colour exists anywhere in the grid every 8-cell inside is recoloured to the cage's colour; cages without such a key, and keys, are unchanged.", gc1, tc9)


# ---------------------------------------------------------------- C11 door cell, item aligned, key = item colour
def gc11(rng):
    for _ in range(50):
        H, W = _gsize(rng); g = blank(H, W); pal = rng.sample([1, 3, 4, 6, 7, 9], rng.randint(3, 4))
        pl = _boxes(rng, H, W, [rng.choice(((4, 4), (5, 5), (4, 6), (6, 4), (6, 6))) for _ in range(_ncount(rng, g, 2, 4))], 3)
        if len(pl) < 2: continue
        cols = []
        for r, c, h, w in pl:
            rect(g, r, c, r + h - 1, c + w - 1, 5, fill=False); ic = rng.choice(pal); cols.append(ic)
            s = rng.choice('NSWE')
            if s in 'WE':
                dr = r + 1 + rng.randrange(h - 2); g[dr][c if s == 'W' else c + w - 1] = 2; g[dr][c + 1 + rng.randrange(w - 2)] = ic
            else:
                dc = c + 1 + rng.randrange(w - 2); g[r if s == 'N' else r + h - 1][dc] = 2; g[r + 1 + rng.randrange(h - 2)][dc] = ic
        for col in rng.sample(sorted(set(cols)), rng.randint(1, len(set(cols)))): _put(rng, g, col)
        if rng.random() < 0.5: _put(rng, g, rng.choice(pal))
        return g
    raise RuntimeError
def tc11(g):
    H, W = dims(g); out = copy(g); bs = _grey(g); fr = {v for _, _, v in _free(g, bs)}
    for b in bs:
        if not b['lock']: continue
        lr, lc = b['lock']; it = [(r, c) for r in range(b['r0'] + 1, b['r1']) for c in range(b['c0'] + 1, b['c1']) if g[r][c]]
        if len(it) != 1: return None
        ir, ic = it[0]
        if g[ir][ic] not in fr: continue
        dr, dc = (-1, 0) if lr == b['r0'] else (1, 0) if lr == b['r1'] else (0, -1) if lc == b['c0'] else (0, 1)
        out[lr][lc] = 0; _slide(out, [(ir, ic)], dr, dc)
    return out
rule("door_opens_for_item_colour_key_item_slides_out", "A grey 5 cage has a door cell (2) set into one wall (never at a corner) and one coloured item inside on the door's row or column; if a loose key cell of the item's colour exists anywhere outside the cages, the door is erased and the item slides out through it, away from the cage's inside, until the next cell is nonempty or the grid edge; otherwise the cage is unchanged.", gc11, tc11)


# ---------------------------------------------------------------- C12 key consumed, cages served in reading order
def gc12(rng):
    pal = rng.sample(KEYS8, rng.randint(2, 3)); g, cg = _cages(rng, pal, nlo=3, nhi=6, items=(1, 2))
    cs = sorted({x[4] for x in cg}); n = [rng.randint(0, 2) for _ in cs]
    if sum(n) == 0: n[0] = 1
    _keysfor(rng, g, list(zip(cs, n)))
    return g
def tc12(g):
    rs = sorted(_rings(g), key=lambda b: (b['r0'], b['c0'])); out = copy(g)
    ks = {}
    for r, c, v in sorted(_free(g, rs)): ks.setdefault(v, []).append((r, c))
    for b in rs:
        if ks.get(b['col']):
            r, c = ks[b['col']].pop(0); out[r][c] = 0
            for y, x in b['cells']: out[y][x] = 0
    return out
rule("each_key_opens_one_cage_then_is_erased", "A hollow cage (rectangular ring, never colour 8, holding 8-cells) opens, its ring being erased, if an unused loose key cell of its colour exists; each key opens only one cage and is erased, cages being served in reading order of their top-left corners (top row first, then left) and each taking the first unused matching key in reading order; cages left without a key stay.", gc12, tc12)


# ---------------------------------------------------------------- C13 digit key = item count (digits)
def gc13(rng):
    for _ in range(50):
        H, W = _gsize(rng); g = blank(H, W)
        pl = _boxes(rng, H, W, [rng.choice(((4, 4), (5, 4), (5, 5), (6, 5))) for _ in range(_ncount(rng, g, 2, 4))], 2)
        if len(pl) < 2: continue
        ns = []
        for r, c, h, w in pl:
            rect(g, r, c, r + h - 1, c + w - 1, 5, fill=False)
            inner = [(y, x) for y in range(r + 1, r + h - 1) for x in range(c + 1, c + w - 1)]
            n = rng.randint(1, min(4, len(inner))); ns.append(n)
            for y, x in rng.sample(inner, n): g[y][x] = 8
        vals = rng.sample(sorted(set(ns)), rng.randint(1, len(set(ns)))) + ([v for v in (1, 2, 3, 4) if v not in ns][:1] if rng.random() < 0.5 else [])
        for v in vals: _put(rng, g, v)
        return g
    raise RuntimeError
def tc13(g):
    bs = _grey(g); vals = {v for _, _, v in _free(g, bs)}; out = copy(g)
    for b in bs:
        if len(_inside(g, b)) in vals:
            for r, c in b['cells']: out[r][c] = 0
    return out
rule("digit_key_equal_to_item_count_opens_cage", "A grey 5 cage holds 1-4 cells of colour 8; it opens, its whole ring being erased, when a loose key cell whose colour value (1-4) equals the number of 8-cells inside exists anywhere outside the cages; the 8-cells and keys stay, and cages with no such key are unchanged.", gc13, tc13, digits=True)


# ---------------------------------------------------------------- K10 chained cages
def gk10(rng):
    for _ in range(50):
        H, W = _gsize(rng); g = blank(H, W); pal = rng.sample(KEYS8, rng.randint(3, 5))
        pl = _boxes(rng, H, W, [(5, 5)] * _ncount(rng, g, 3, 6), 1)
        if len(pl) < 3: continue
        for r, c, h, w in pl:
            rect(g, r, c, r + 4, c + 4, rng.choice(pal), fill=False); g[r + 2][c + 2] = rng.choice(pal)
        for col in rng.sample(pal, rng.randint(1, 2)): _put(rng, g, col)
        return g
    raise RuntimeError
def tk10(g):
    rs = _rings(g, skip=(0,)); ks = {v for _, _, v in _free(g, rs)}; out = copy(g); done = set(); ch = True
    while ch:
        ch = False
        for i, b in enumerate(rs):
            if i not in done and b['col'] in ks:
                done.add(i); ks.add(g[b['r0'] + 2][b['c0'] + 2]); ch = True
    for i in done:
        for r, c in rs[i]['cells']: out[r][c] = 0
    return out
rule("chained_cages_each_hold_the_next_key", "Each 5x5 ring cage holds one key cell at its centre; a cage opens, its ring being erased, if a key cell of its colour exists outside every cage or inside an already opened cage, and this repeats until nothing more opens; the centre keys and free keys stay, and cages that never get a key remain closed.", gk10, tk10)


# ---------------------------------------------------------------- K9 room with key inside floods
def gk9(rng):
    for _ in range(50):
        H, W = _gsize(rng); g = blank(H, W)
        pl = _boxes(rng, H, W, [(rng.randint(4, 7), rng.randint(4, 7)) for _ in range(_ncount(rng, g, 2, 4))], 2)
        if len(pl) < 2: continue
        for k, (r, c, h, w) in enumerate(pl):
            rect(g, r, c, r + h - 1, c + w - 1, 5, fill=False)
            s = rng.choice('NSWE')
            if s == 'N': g[r][c + 1 + rng.randrange(w - 2)] = 2
            elif s == 'S': g[r + h - 1][c + 1 + rng.randrange(w - 2)] = 2
            elif s == 'W': g[r + 1 + rng.randrange(h - 2)][c] = 2
            else: g[r + 1 + rng.randrange(h - 2)][c + w - 1] = 2
            if k == 0 or rng.random() < 0.5: g[r + 1 + rng.randrange(h - 2)][c + 1 + rng.randrange(w - 2)] = 4
        for _ in range(rng.randint(0, 3)): _put(rng, g, 4)
        return g
    raise RuntimeError
def tk9(g):
    out = copy(g)
    for b in _grey(g):
        if not b['lock']: continue
        ins = [(r, c) for r in range(b['r0'] + 1, b['r1']) for c in range(b['c0'] + 1, b['c1'])]
        if any(g[r][c] == 4 for r, c in ins):
            out[b['lock'][0]][b['lock'][1]] = 0
            for r, c in ins:
                if g[r][c] == 0: out[r][c] = 3
    return out
rule("room_with_key_inside_unlocks_and_floods", "A grey 5 room has a lock cell (2) in its wall (never at a corner); a room that contains a key cell (4) inside it has its lock erased and every empty cell inside filled with colour 3 (the key stays), whereas rooms without a key inside are unchanged and keys outside rooms are ignored.", gk9, tk9)


# ---------------------------------------------------------------- K1 clamps hold objects, the rest fall
def gk1(rng):
    for _ in range(80):
        H, W = _gsize(rng); g = blank(H, W); n = _ncount(rng, g, 3, 6)
        shapes = [random_shape(rng, rng.randint(2, 5)) for _ in range(n)]
        pos = place_shapes(rng, g, shapes, [3] * n, margin=1)
        if not pos: continue
        for sh, (r0, c0) in zip(shapes, pos):
            if rng.random() < 0.4:
                opts = [(r0 + r + a, c0 + c + b) for r, c in sh for a, b in ((-1, 0), (1, 0), (0, -1), (0, 1)) if 0 <= r0 + r + a < H and 0 <= c0 + c + b < W and g[r0 + r + a][c0 + c + b] == 0]
                if opts:
                    y, x = rng.choice(opts); g[y][x] = 2
        return g
    raise RuntimeError
def tk1(g):
    H, W = dims(g); out = copy(g)
    objs = components(g, 3, conn8=False)
    held = lambda o: any(0 <= r + a < H and 0 <= c + b < W and g[r + a][c + b] == 2 for r, c in o for a, b in ((-1, 0), (1, 0), (0, -1), (0, 1)))
    free = [o for o in objs if not held(o)]
    for o in free:
        for r, c in o: out[r][c] = 0
    free = [list(o) for o in free]; moved = True
    for o in free:
        for r, c in o: out[r][c] = 3
    while moved:
        moved = False
        for o in sorted(free, key=lambda o: -max(r for r, c in o)):
            s = set(o)
            if all(r + 1 < H and (out[r + 1][c] == 0 or (r + 1, c) in s) for r, c in o):
                for r, c in o: out[r][c] = 0
                o[:] = [(r + 1, c) for r, c in o]
                for r, c in o: out[r][c] = 3
                moved = True
    return out
rule("clamped_objects_stay_the_rest_fall", "Objects are 4-connected groups of colour 3 and clamps are single cells of colour 2; an object with a clamp cell edge-adjacent to any of its cells is held and does not move, every other object falls rigidly straight down until one of its cells would meet a nonempty cell (a held object, a clamp, another resting object) or the bottom edge; clamps never move.", gk1, tk1)


# ---------------------------------------------------------------- K3 key slides along its row to a lock
def gk3(rng):
    for _ in range(50):
        H, W = _gsize(rng); g = blank(H, W); pal = rng.sample(KEYS, 4)
        rows = rng.sample(range(H), min(H, _ncount(rng, g, 2, 5)))
        for k, r in enumerate(rows):
            n = rng.randint(2, 3)
            if W < n + 4: continue
            p = rng.randint(0, W - n - 3); q = rng.randint(p + 2, W - n)
            a = rng.choice(pal); b = a if (k == 0 or rng.random() < 0.5) else rng.choice([x for x in pal if x != a])
            g[r][p] = a
            for j in range(n): g[r][q + j] = b
        return g
    raise RuntimeError
def tk3(g):
    out = copy(g)
    for r in range(len(g)):
        nz = [c for c, v in enumerate(g[r]) if v]
        if not nz: continue
        if len(nz) < 3: return None
        p, q = nz[0], nz[1]
        if nz[2] != q + 1 or any(g[r][c] != g[r][q] for c in nz[1:]): return None
        if g[r][p] == g[r][q]:
            out[r][p] = 0
            for c in nz[1:]: out[r][c] = 0
        else:
            out[r][p] = 0; out[r][q - 1] = g[r][p]
    return out
rule("key_slides_to_lock_same_colour_both_vanish", "Each used row holds one key cell (leftmost) and, further right with at least one empty cell between them, a lock bar of 2-3 cells; the key slides right until it touches the lock bar, and if key and lock bar have the same colour both are erased, otherwise the key stays resting against the bar; rows with no cells are unchanged.", gk3, tk3)


# ---------------------------------------------------------------- S1/S2 doors in a wall row, tokens above
def gs1(rng):
    for _ in range(50):
        H, W = _gsize(rng); wr = rng.randint(max(3, H // 3), H - 4); g = blank(H, W); g[wr] = [5] * W
        pal = rng.sample([1, 2, 3, 4, 6, 7, 9], rng.randint(2, 4))
        cols = rng.sample(range(W), min(W, rng.randint(3, max(4, W // 2))))
        dcols = cols[:max(2, len(cols) * 2 // 3)]
        for k, c in enumerate(cols):
            if c in dcols: d = rng.choice(pal); g[wr][c] = d
            t = (g[wr][c] if (c in dcols and (k == 0 or rng.random() < 0.5)) else rng.choice(pal))
            g[rng.randint(0, wr - 1)][c] = t
        for _ in range(rng.randint(0, 4)):
            r, c = rng.randint(wr + 1, H - 1), rng.randrange(W)
            if g[r][c] == 0: g[r][c] = 8
        return g
    raise RuntimeError
def ts1(g):
    H, W = dims(g); wr = max(range(H), key=lambda r: sum(1 for v in g[r] if v == 5)); out = copy(g)
    for c in range(W):
        toks = [r for r in range(wr) if g[r][c]]
        if not toks: continue
        if len(toks) != 1: return None
        tr = toks[0]; t = g[tr][c]; out[tr][c] = 0
        if g[wr][c] == t and wr + 1 < H and g[wr + 1][c] == 0:
            r = wr
            while r + 1 < H and out[r + 1][c] == 0: r += 1
            out[r][c] = t
        else: out[wr - 1][c] = t
    return out
rule("matching_door_lets_token_fall_through", "A grey 5 wall row crosses the grid, some of its cells replaced by coloured door cells, with at most one token above it in a column and sparse 8-cells below; a token falls until it rests on the wall, except that a token directly above a door of its own colour passes through (the door stays) and keeps falling until the next cell is nonempty or the bottom edge, provided the cell right under the door is empty.", gs1, ts1)

def gs2(rng):
    for _ in range(50):
        H, W = rng.randint(14, 30), rng.randint(8, 30)
        wr = rng.randint(6, H - 7); g = blank(H, W); g[wr] = [5] * W
        cols = rng.sample(range(W), min(W, rng.randint(2, 5)))
        for k, c in enumerate(cols):
            d = rng.randint(1, 4)
            if k < 3: g[wr][c] = d
            n = rng.randint(max(0, d - 1), min(5, d + 1)) if k < 3 else rng.randint(0, 3)
            if k == 0: n = max(n, d)
            for r in rng.sample(range(0, wr), n): g[r][c] = 8
        return g
    raise RuntimeError
def ts2(g):
    H, W = dims(g); wr = max(range(H), key=lambda r: sum(1 for v in g[r] if v == 5)); out = copy(g)
    for c in range(W):
        n = sum(1 for r in range(wr) if g[r][c] == 8)
        for r in range(wr): out[r][c] = 0
        d = g[wr][c]
        if d in (1, 2, 3, 4) and n >= d:
            for j in range(n): out[H - 1 - j][c] = 8
        else:
            for j in range(n): out[wr - 1 - j][c] = 8
    return out
rule("heavy_pile_forces_numbered_door", "A grey 5 wall row crosses the grid, some of its cells replaced by digit doors of colour value 1-4, and loose 8-cells hang in the columns above; each column's 8-cells settle in a stack resting on the wall, except that in a door column whose count of 8-cells is greater than or equal to the door's digit the whole stack falls through the door (which stays) and settles on the bottom edge.", gs2, ts2, digits=True)
