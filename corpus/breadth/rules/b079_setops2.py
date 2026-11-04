# b079_setops2.py -- SET OPERATIONS, SECOND SET: panels (or colour classes on one board) hold collections of shapes or
# loose cells; the output is a summary or a set-operation result (a leftover panel, a Venn drawing, bars of set sizes,
# a flag pair, a ranking, a membership matrix). Panels are separated by a full column of grey 5, shapes are 4-connected
# same-colour groups kept one empty cell apart, "same shape" means equal cell pattern up to translation unless a rule
# says otherwise, and colours are ignored when matching unless a rule says otherwise.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

SEP = 5
OC = [1, 2, 3, 4, 6, 7, 8, 9]
OC34 = [1, 2, 6, 7, 8, 9]


def _safe(f):
    def g(x):
        try: return f(x)
        except (ValueError, IndexError, KeyError, StopIteration, ZeroDivisionError, TypeError): return None
    return g


# ---------------------------------------------------------------- shape helpers
def _norm(cs):
    r0 = min(r for r, c in cs); c0 = min(c for r, c in cs); return tuple(sorted((r - r0, c - c0) for r, c in cs))
def _rot(cs): return _norm([(c, -r) for r, c in cs])
def _refl(cs): return _norm([(r, -c) for r, c in cs])
def _rots(cs):
    out = []; cur = tuple(cs)
    for _ in range(4): cur = _rot(cur); out.append(cur)
    return out
def _dih(cs): return set(_rots(cs)) | set(_rots(_refl(cs)))
def _up(key, k): return _norm([(r * k + i, c * k + j) for r, c in key for i in range(k) for j in range(k)])


def _tpls(rng, n, lo=3, hi=6, maxd=4, asym=True, chiral=False):
    out, used, tries = [], set(), 0
    while len(out) < n and tries < 600:
        tries += 1
        sh = tuple(random_shape(rng, rng.randint(lo, hi))); r0, c0, r1, c1 = bbox(sh)
        if r1 >= maxd or c1 >= maxd: continue
        d = _dih(sh)
        if d & used: continue
        if asym and (_refl(sh) == sh or _rot(sh) == sh): continue
        if chiral and _refl(sh) in set(_rots(sh)): continue
        used |= d; out.append(sh)
    return out if len(out) == n else None


def _fits(g, sh, r, c, margin=1):
    H, W = dims(g)
    for y, x in sh:
        if not (0 <= r + y < H and 0 <= c + x < W): return False
        for a in range(-margin, margin + 1):
            for b in range(-margin, margin + 1):
                yy, xx = r + y + a, c + x + b
                if 0 <= yy < H and 0 <= xx < W and g[yy][xx]: return False
    return True
def _stampo(g, sh, r, c, col):
    for y, x in sh: g[r + y][c + x] = col
def _rand_put(rng, g, sh, col, tries=120):
    H, W = dims(g); h = max(r for r, c in sh) + 1; w = max(c for r, c in sh) + 1
    if h > H or w > W: return None
    for _ in range(tries):
        r, c = rng.randint(0, H - h), rng.randint(0, W - w)
        if _fits(g, sh, r, c): _stampo(g, sh, r, c, col); return (r, c)
    return None
def _layout(rng, hp, wp, objs):
    g = blank(hp, wp)
    for sh, col in sorted(objs, key=lambda o: -len(o[0])):
        if not _rand_put(rng, g, sh, col): return None
    return g


def _join(panels):
    out = []
    for r in range(len(panels[0])):
        row = []
        for i, p in enumerate(panels):
            if i: row.append(SEP)
            row += p[r]
        out.append(row)
    return out
def _panels(g):
    H, W = dims(g); seps = [c for c in range(W) if all(g[r][c] == SEP for r in range(H))]
    cuts = [-1] + seps + [W]
    return [[row[a + 1:b] for row in g] for a, b in zip(cuts, cuts[1:]) if b - a > 1]
def _o(p):
    return [dict(col=p[comp[0][0]][comp[0][1]], key=_norm(comp), cells=comp, pos=(min(r for r, c in comp), min(c for r, c in comp)))
            for comp in sorted(objects(p, bg=0, conn8=False), key=lambda k: (min(k), ))]
def _keys(p): return {o['key'] for o in _o(p)}
def _erase(p, objs):
    out = copy(p)
    for o in objs:
        for r, c in o['cells']: out[r][c] = 0
    return out
def _bar(n, col, w=10): return [col] * n + [0] * (w - n)

def _d2(rng):
    if rng.random() < 0.45: return rng.randint(8, 30), rng.randint(10, 14)
    return rng.randint(7, 14), rng.randint(7, 10)
def _d3(rng):
    if rng.random() < 0.45: return rng.randint(8, 30), rng.randint(7, 9)
    return rng.randint(7, 14), rng.randint(5, 6)
def _cap(hp, wp): return max(2, (hp * wp) // 28)
def _cols(rng, n, pool=OC): return [rng.choice(pool) for _ in range(n)]


# ---------------------------------------------------------------- two-panel object-set generator
def _g2(kc=(1, 2), ka=(1, 3), kb=(0, 2), kd=(0, 0), decoy='rot', rotate_common=False, chiral=False, differ=False, lo=3, hi=6):
    def gen(rng):
        for _ in range(400):
            hp, wp = _d2(rng); cap = _cap(hp, wp)
            nc, na, nb, nd = [rng.randint(*x) for x in (kc, ka, kb, kd)]
            if nc + na + nd > cap or nc + nb + nd > cap or nc + na + nb + nd < 2: continue
            T = _tpls(rng, nc + na + nb + nd, lo, hi, chiral=chiral or decoy == 'mirror')
            if not T: continue
            C, Ao, Bo, D = T[:nc], T[nc:nc + na], T[nc + na:nc + na + nb], T[nc + na + nb:]
            A = [(s, rng.choice(OC)) for s in C + Ao + D]
            def twist(s): return _refl(s) if decoy == 'mirror' else _rot(s)
            Bc = []
            for s in C:
                if rotate_common: s = _rots(s)[rng.randrange(4)]
                Bc.append((s, rng.choice(OC)))
            if differ: Bc = [(s, rng.choice([x for x in OC if x != A[i][1]])) for i, (s, _) in enumerate(Bc)]
            B = Bc + [(s, rng.choice(OC)) for s in Bo] + [(twist(s), rng.choice(OC)) for s in D]
            pa, pb = _layout(rng, hp, wp, A), _layout(rng, hp, wp, B)
            if pa and pb: return _join([pa, pb])
        raise RuntimeError
    return gen
def _two(g):
    ps = _panels(g); return ps if len(ps) == 2 else None


# 1 -----------------------------------------------------------------
def t1(g):
    A, B = _two(g); kb = _keys(B); return _erase(A, [o for o in _o(A) if o['key'] in kb])
rule("a_minus_b_by_shape_translation_only", "Two panels A (left) and B (right) are separated by a grey 5 column; the output is panel A with erased every object whose cell pattern equals, by translation only (no rotation, no mirror, colours ignored), the pattern of some object in B; other objects stay in place.", _g2(kc=(1, 2), ka=(1, 3), kb=(0, 2), kd=(1, 1), decoy='rot'), _safe(t1))

# 2 -----------------------------------------------------------------
def t2(g):
    A, B = _two(g); kb = {r for o in _o(B) for r in _rots(o['key'])}; return _erase(A, [o for o in _o(A) if o['key'] in kb])
rule("a_minus_b_with_b_rotated_no_mirror", "Two panels A (left) and B (right) are separated by a grey 5 column; the output is panel A with erased every object whose cell pattern equals some B object's pattern turned by 0, 90, 180 or 270 degrees (mirror images do NOT count, colours ignored); other objects stay in place.", _g2(kc=(1, 2), ka=(1, 2), kb=(0, 2), kd=(1, 1), decoy='mirror', rotate_common=True, chiral=True, lo=4, hi=6), _safe(t2))

# 3 scaled copies ---------------------------------------------------
def g3(rng):
    for _ in range(400):
        hp, wp = rng.randint(12, 30), rng.randint(12, 14)
        Bt = _tpls(rng, rng.randint(2, 3), 2, 4, maxd=3, asym=False)
        if not Bt: continue
        ks = [rng.choice((2, 3)) for _ in range(rng.randint(1, 2))]
        picks = rng.sample(Bt, len(ks)); A = [(_up(s, k), rng.choice(OC)) for s, k in zip(picks, ks)]
        allup = {_up(s, k) for s in Bt for k in (2, 3)}
        for _t in range(rng.randint(1, 2)):
            sh = tuple(random_shape(rng, rng.randint(5, 8)))
            if sh not in allup and bbox(sh)[2] < 7 and bbox(sh)[3] < 7: A.append((sh, rng.choice(OC)))
        if len(A) == len(ks): continue
        pa, pb = _layout(rng, hp, wp, A), _layout(rng, hp, wp, [(s, rng.choice(OC)) for s in Bt])
        if pa and pb: return _join([pa, pb])
    raise RuntimeError
def t3(g):
    A, B = _two(g); sc = {_up(o['key'], k) for o in _o(B) for k in (2, 3)}
    return _erase(A, [o for o in _o(A) if o['key'] not in sc])
rule("keep_a_objects_that_are_enlarged_b_objects", "Two panels A (left) and B (right) are separated by a grey 5 column; the output is panel A keeping only objects whose pattern equals some B object's pattern enlarged by a whole factor of exactly 2 or exactly 3 (every cell becomes a k by k block, colours ignored); all other A objects are erased.", g3, _safe(t3))

# 4 three bars --------------------------------------------------------
def t4(g):
    A, B = _two(g); a, b = _keys(A), _keys(B)
    if max(len(a & b), len(a - b), len(b - a)) > 10: return None
    return [_bar(len(a & b), 3), _bar(len(a - b), 2), _bar(len(b - a), 4)]
rule("venn_counts_of_shapes_as_three_bars", "Two panels A (left) and B (right) are separated by a grey 5 column and each shape (pattern up to translation, colours ignored) occurs at most once per panel; the output has three rows of width 10, bars padded with 0 from the left: row 0 colour 3 with the number of shapes in both panels, row 1 colour 2 with the number only in A, row 2 colour 4 with the number only in B.", _g2(kc=(0, 3), ka=(0, 3), kb=(0, 3)), _safe(t4))

# 5 subset test -------------------------------------------------------
def t5(g):
    A, B = _two(g); a, b = _keys(A), _keys(B); return [[3 if b <= a else 2, 4 if a <= b else 6]]
rule("subset_test_flags_between_shape_sets", "Two panels A (left) and B (right) are separated by a grey 5 column (shapes compared up to translation, colours ignored); the output is one row of two cells: the first is colour 3 if every shape of B also occurs in A, else colour 2; the second is colour 4 if every shape of A also occurs in B, else colour 6.", _g2(kc=(1, 3), ka=(0, 2), kb=(0, 2)), _safe(t5))

# 12 symmetric difference as one panel --------------------------------
def t12(g):
    A, B = _two(g); a, b = _keys(A), _keys(B); out = blank(len(A), len(A[0]))
    for o in _o(A):
        if o['key'] not in b:
            for r, c in o['cells']: out[r][c] = 2
    for o in _o(B):
        if o['key'] not in a:
            for r, c in o['cells']:
                if out[r][c]: return None
                out[r][c] = 3
    return out
rule("shape_symmetric_difference_drawn_on_one_panel", "Two panels A (left) and B (right) are separated by a grey 5 column; the output is one blank panel with the objects whose pattern (up to translation, colours ignored) occurs in only one panel drawn at their own positions, A's exclusive objects in colour 2 and B's exclusive objects in colour 3, shared objects left out (rejected if two drawn objects would overlap).", _g2(kc=(1, 2), ka=(1, 2), kb=(1, 2)), _safe(t12))

# 13 colour transfer --------------------------------------------------
def t13(g):
    A, B = _two(g); m = {}
    for o in _o(B):
        if m.setdefault(o['key'], o['col']) != o['col']: return None
    out = copy(A)
    for o in _o(A):
        if o['key'] in m:
            for r, c in o['cells']: out[r][c] = m[o['key']]
    return out
rule("a_objects_take_colour_of_same_shape_in_b", "Two panels A (left) and B (right) are separated by a grey 5 column; the output is panel A where every object whose pattern equals (up to translation) some B object's pattern is recoloured to that B object's colour, other objects unchanged.", _g2(kc=(1, 3), ka=(0, 2), kb=(0, 2), differ=True), _safe(t13))

# 14 multiset difference ---------------------------------------------
def g14(rng):
    for _ in range(400):
        hp, wp = _d2(rng); cap = _cap(hp, wp); T = _tpls(rng, rng.randint(2, 3), 3, 5)
        if not T: continue
        ca = [rng.randint(1, 3) for _ in T]; cb = [rng.randint(0, 2) for _ in T]
        if sum(ca) > cap or sum(cb) > cap or sum(min(a, b) for a, b in zip(ca, cb)) == 0 or sum(ca) - sum(min(a, b) for a, b in zip(ca, cb)) == 0: continue
        pa = _layout(rng, hp, wp, [(s, rng.choice(OC)) for s, n in zip(T, ca) for _ in range(n)])
        pb = _layout(rng, hp, wp, [(s, rng.choice(OC)) for s, n in zip(T, cb) for _ in range(n)]) if sum(cb) else blank(hp, wp)
        if pa and pb: return _join([pa, pb])
    raise RuntimeError
def t14(g):
    A, B = _two(g); cb = {}
    for o in _o(B): cb[o['key']] = cb.get(o['key'], 0) + 1
    rem = []
    for o in sorted(_o(A), key=lambda o: o['pos']):
        if cb.get(o['key'], 0) > 0: cb[o['key']] -= 1; rem.append(o)
    return _erase(A, rem)
rule("multiset_difference_first_copies_cancelled", "Two panels A (left) and B (right) are separated by a grey 5 column and shapes (pattern up to translation, colours ignored) may repeat; for each shape appearing a times in A and b times in B, the output is panel A with the first min(a,b) copies of that shape erased, copies ordered by the row then column of their top-left bounding-box corner; the remaining copies stay.", g14, _safe(t14))

# 20 mirror images ----------------------------------------------------
def g20(rng):
    for _ in range(400):
        hp, wp = _d2(rng); cap = _cap(hp, wp); nm, ns, na = rng.randint(1, 2), rng.randint(0, 1), rng.randint(1, 2)
        T = _tpls(rng, nm + ns + na, 3, 6, chiral=True)
        if not T or nm + ns + na > cap: continue
        M, S, Ao = T[:nm], T[nm:nm + ns], T[nm + ns:]
        A = [(s, rng.choice(OC34)) for s in M + S + Ao]; B = [(_refl(s), rng.choice(OC)) for s in M] + [(s, rng.choice(OC)) for s in S]
        pa, pb = _layout(rng, hp, wp, A), _layout(rng, hp, wp, B)
        if pa and pb: return _join([pa, pb])
    raise RuntimeError
def t20(g):
    A, B = _two(g); kb = _keys(B); out = copy(A)
    for o in _o(A):
        if _refl(o['key']) in kb and _refl(o['key']) != o['key']:
            for r, c in o['cells']: out[r][c] = 4
    return out
rule("a_objects_whose_left_right_mirror_is_in_b_recoloured", "Two panels A (left) and B (right) are separated by a grey 5 column; in panel A every object whose left-right mirror image (not the object itself, not a turned copy) equals a pattern of some B object, up to translation, is recoloured 4; the output is panel A, all other objects unchanged.", g20, _safe(t20))

# 24 sub-shape --------------------------------------------------------
def _subset(small, big):
    s = set(small); b = set(big); r0, c0 = small[0]
    return any(all((r - r0 + br, c - c0 + bc) in b for r, c in s) for br, bc in b)
def _grow(rng, cells_, k):
    cs = set(cells_); cur = {rng.choice(sorted(cs))}
    while len(cur) < k:
        nb = [(r + a, c + b) for r, c in cur for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (r + a, c + b) in cs and (r + a, c + b) not in cur]
        if not nb: return None
        cur.add(rng.choice(nb))
    return _norm(cur)
def g24(rng):
    for _ in range(400):
        hp, wp = _d2(rng); cap = _cap(hp, wp); big = [tuple(random_shape(rng, rng.randint(5, 8))) for _ in range(rng.randint(2, 3))]
        if any(bbox(b)[2] > 5 or bbox(b)[3] > 5 for b in big): continue
        B = []
        for b in big[:rng.randint(1, len(big))]:
            s = _grow(rng, b, rng.randint(2, 4))
            if s: B.append(s)
        for _t in range(rng.randint(1, 2)): B.append(tuple(random_shape(rng, rng.randint(3, 4))))
        if len(B) > cap or len(big) > cap: continue
        flags = [any(_subset(b, a) for a in big) for b in B]
        if all(flags) or not any(flags): continue
        pa, pb = _layout(rng, hp, wp, [(s, rng.choice(OC)) for s in big]), _layout(rng, hp, wp, [(s, rng.choice(OC)) for s in B])
        if pa and pb: return _join([pa, pb])
    raise RuntimeError
def t24(g):
    A, B = _two(g); big = [o['key'] for o in _o(A)]
    return _erase(B, [o for o in _o(B) if not any(_subset(o['key'], a) for a in big)])
rule("b_objects_that_fit_inside_an_a_object_kept", "Two panels A (left) and B (right) are separated by a grey 5 column; the output is panel B keeping only objects whose cells, moved by some translation, all fall on cells of a single A object (an equal pattern counts); other B objects are erased.", g24, _safe(t24))

# Venn of two aligned shapes -----------------------------------------
def gv(rng):
    for _ in range(300):
        hp, wp = _d2(rng)
        s1, s2 = [tuple(random_shape(rng, rng.randint(4, 8))) for _ in range(2)]
        if s1 == s2 or any(bbox(s)[2] > 5 or bbox(s)[3] > 5 for s in (s1, s2)): continue
        pa, pb = blank(hp, wp), blank(hp, wp)
        if not _rand_put(rng, pa, s1, rng.choice(OC)) or not _rand_put(rng, pb, s2, rng.choice(OC)): continue
        return _join([pa, pb])
def tv(g):
    A, B = _two(g); a = _o(A); b = _o(B)
    if len(a) != 1 or len(b) != 1: return None
    sa, sb = set(a[0]['key']), set(b[0]['key']); h = max(r for r, c in sa | sb) + 1; w = max(c for r, c in sa | sb) + 1
    return [[3 if (r, c) in sa and (r, c) in sb else 1 if (r, c) in sa else 2 if (r, c) in sb else 0 for c in range(w)] for r in range(h)]
rule("two_shapes_aligned_top_left_venn_drawing", "Two panels A (left) and B (right) are separated by a grey 5 column and each holds one shape; both shapes are moved so their bounding boxes start at the top-left, and the output draws them together on one blank grid just large enough for both: cells in both shapes colour 3, only in A colour 1, only in B colour 2, neither 0.", gv, _safe(tv))


# ---------------------------------------------------------------- three-panel generator
def _g3(pat, perpanel=False):
    def gen(rng):
        for _ in range(500):
            hp, wp = _d3(rng); cnt = {m: rng.randint(*pat.get(m, (0, 0))) for m in range(1, 8)}
            T = _tpls(rng, sum(cnt.values()), 2, 5, maxd=3)
            if not T: continue
            subs = [rng.sample(OC, 3) for _ in range(3)] if perpanel else [OC] * 3
            objs, i = [[], [], []], 0
            for m in range(1, 8):
                for _ in range(cnt[m]):
                    for p in range(3):
                        if m >> p & 1: objs[p].append((T[i], rng.choice(subs[p])))
                    i += 1
            if any(not o or len(o) > _cap(hp, wp) for o in objs): continue
            ps = [_layout(rng, hp, wp, o) for o in objs]
            if all(ps): return _join(ps)
        raise RuntimeError
    return gen
def _three(g):
    ps = _panels(g); return ps if len(ps) == 3 else None
ALL3 = {1: (0, 2), 2: (0, 2), 4: (0, 2), 3: (0, 2), 5: (0, 2), 6: (0, 2), 7: (0, 2)}

def t6(g):
    ps = _three(g); ks = [_keys(p) for p in ps]; com = ks[0] & ks[1] & ks[2]
    if not com: return None
    sizes = sorted((len(k), k) for k in com)
    if len(sizes) > 1 and sizes[-1][0] == sizes[-2][0]: return None
    key = sizes[-1][1]; o = next(o for o in _o(ps[0]) if o['key'] == key)
    h, w = max(r for r, c in key) + 1, max(c for r, c in key) + 1; out = blank(h, w)
    for r, c in key: out[r][c] = o['col']
    return out
rule("largest_shape_common_to_three_panels_cropped", "Three panels separated by grey 5 columns hold shapes compared up to translation, colours ignored; among the shapes present in all three panels, the output is the one with most cells (rejected if two tie), cropped tight and drawn in the colour it has in the first (left) panel.", _g3({7: (1, 3), 1: (0, 2), 2: (0, 2), 4: (0, 2), 3: (0, 1)}), _safe(t6))

def t8(g):
    ps = _three(g); ks = [_keys(p) for p in ps]
    n = [sum(1 for o in _o(ps[i]) if any(o['key'] in ks[j] for j in range(3) if j != i)) for i in range(3)]
    return [[i + 1] for i in sorted(range(3), key=lambda i: (-n[i], i))]
rule("panels_ranked_by_shared_shape_count_column", "Three panels (numbered 1, 2, 3 from the left) separated by grey 5 columns hold shapes compared up to translation, colours ignored; each panel scores the number of its objects whose pattern also occurs in at least one other panel; the output is a column of three cells whose colour values are the panel numbers, best score first, equal scores in panel-number order.", _g3(ALL3), _safe(t8), digits=True)

def t9(g):
    ps = _three(g); ks = [_keys(p) for p in ps]
    ex = [sum(1 for o in _o(ps[i]) if all(o['key'] not in ks[j] for j in range(3) if j != i)) for i in range(3)]
    return ps[max(range(3), key=lambda i: (ex[i], -i))]
rule("panel_with_most_shapes_found_nowhere_else", "Three panels separated by grey 5 columns hold shapes compared up to translation, colours ignored; the output is a copy of the whole panel that has the most objects whose pattern occurs in neither of the other two panels, the leftmost such panel on a tie.", _g3({1: (0, 3), 2: (0, 3), 4: (0, 3), 7: (0, 1), 3: (0, 1), 5: (0, 1), 6: (0, 1)}), _safe(t9))

def t10(g):
    ps = _three(g); cs = {}
    for i, p in enumerate(ps):
        for v in {v for row in p for v in row if v}: cs.setdefault(v, []).append(i + 1)
    ex = sorted((c, l[0]) for c, l in cs.items() if len(l) == 1)
    if not ex: return None
    return [[c for c, _ in ex], [p for _, p in ex]]
rule("colours_used_in_exactly_one_panel_with_panel_number", "Three panels (numbered 1, 2, 3 from the left) separated by grey 5 columns hold coloured shapes; the output has two rows with one column per colour used in exactly one panel, columns in ascending colour value: the top cell is the colour, the bottom cell has the colour value equal to that panel's number.", _g3(ALL3, perpanel=True), _safe(t10), digits=True)

def t11(g):
    ps = _three(g); ks = [_keys(p) for p in ps]; com = ks[0] & ks[1] & ks[2]; out = blank(len(ps[0]), len(ps[0][0]))
    for o in _o(ps[0]):
        if o['key'] in com:
            for r, c in o['cells']: out[r][c] = 4
    return out
rule("shapes_in_all_three_panels_marked_on_first_panel", "Three panels separated by grey 5 columns hold shapes compared up to translation, colours ignored; the output is a blank panel with only those objects of the first (left) panel whose pattern occurs in all three panels drawn at their own positions in colour 4.", _g3({7: (1, 3), 1: (0, 2), 3: (0, 2), 5: (0, 2), 2: (0, 1), 4: (0, 1)}), _safe(t11))

def t21(g):
    ps = _three(g); ks = [_keys(p) for p in ps]; allk = set().union(*ks); n = {1: 0, 2: 0, 3: 0}
    for k in allk: n[sum(1 for s in ks if k in s)] += 1
    return [_bar(n[1], 3), _bar(n[2], 4), _bar(n[3], 6)] if max(n.values()) <= 10 else None
rule("shapes_by_number_of_panels_containing_them_bars", "Three panels separated by grey 5 columns each hold shapes compared up to translation, colours ignored, at most once per panel; the output has three rows of width 10, bars padded with 0 from the left, giving the number of distinct shapes found in exactly one panel (colour 3), exactly two panels (colour 4) and all three panels (colour 6), in that row order.", _g3(ALL3), _safe(t21))

def t25(g):
    ps = _three(g); ks = [_keys(p) for p in ps]
    return [[len(ks[i]) if i == j else len(ks[i] & ks[j]) for j in range(3)] for i in range(3)]
def g25(rng): return _g3({7: (0, 2), 3: (0, 2), 5: (0, 2), 6: (0, 2), 1: (0, 2), 2: (0, 2), 4: (0, 2)})(rng)
rule("shared_shape_count_matrix_of_three_panels", "Three panels separated by grey 5 columns hold shapes compared up to translation, colours ignored, at most once per panel; the output is a 3 by 3 grid indexed panel by panel from the left whose cell (i, j) has the colour value equal to the number of distinct shapes panels i and j share, and whose diagonal cell (i, i) has the colour value equal to the number of distinct shapes in panel i.", g25, _safe(t25), digits=True)

def t28(g):
    ps = _three(g); ks = [_keys(p) for p in ps]; out = copy(ps[0])
    for o in _o(ps[0]):
        n = sum(1 for j in (1, 2) if o['key'] in ks[j])
        if n:
            for r, c in o['cells']: out[r][c] = 3 if n == 1 else 4
    return out
rule("first_panel_objects_coloured_by_how_many_others_share_them", "Three panels separated by grey 5 columns hold shapes compared up to translation, colours ignored; the output is the first (left) panel where an object whose pattern occurs in exactly one of the other two panels is recoloured 3, one occurring in both other panels is recoloured 4, and one occurring in neither stays unchanged.", _g3({7: (1, 2), 3: (1, 2), 5: (1, 2), 1: (1, 2), 2: (0, 1), 4: (0, 1)}), _safe(t28))

def t29(g):
    ps = _three(g); ks = [_keys(p) for p in ps]; return _erase(ps[0], [o for o in _o(ps[0]) if o['key'] in ks[1] or o['key'] in ks[2]])
rule("first_panel_minus_union_of_the_other_two", "Three panels separated by grey 5 columns hold shapes compared up to translation, colours ignored; the output is the first (left) panel with erased every object whose pattern occurs in the second panel or the third panel (or both); objects found in neither stay in place.", _g3({1: (1, 3), 3: (1, 2), 5: (0, 2), 7: (0, 2), 2: (0, 1), 4: (0, 1)}), _safe(t29))

def t26(g):
    ps = _three(g); ks = [_keys(p) for p in ps]; pairs = [(0, 1), (0, 2), (1, 2)]
    best = max(pairs, key=lambda pr: (len(ks[pr[0]] & ks[pr[1]]), -pairs.index(pr)))
    return [[3 if i in best else 0 for i in range(3)]]
rule("most_similar_pair_of_panels_flagged", "Three panels separated by grey 5 columns hold shapes compared up to translation, colours ignored; the output is one row of three cells, one per panel from the left: colour 3 for the two panels of the pair sharing the most distinct shapes, colour 0 for the third; ties go to the first pair in the order (panel 1, panel 2), (panel 1, panel 3), (panel 2, panel 3).", _g3(ALL3), _safe(t26))

def t27(g):
    ps = _three(g); ks = [_keys(p) for p in ps]; n = [len(ks[a] & ks[b]) for a, b in ((0, 1), (0, 2), (1, 2))]
    return [_bar(n[0], 3), _bar(n[1], 4), _bar(n[2], 6)] if max(n) <= 10 else None
rule("pairwise_shared_shape_counts_as_three_bars", "Three panels separated by grey 5 columns each hold shapes compared up to translation, colours ignored, at most once per panel; the output has three rows of width 10, bars padded with 0 from the left, counting the shapes shared by panels 1 and 2 (colour 3), panels 1 and 3 (colour 4), panels 2 and 3 (colour 6), in that row order.", _g3(ALL3), _safe(t27))


# ---------------------------------------------------------------- loose-cell panels
def _dc(rng, k):
    if rng.random() < 0.45: return (rng.randint(8, 30), rng.randint(10, 14)) if k == 2 else (rng.randint(8, 30), rng.randint(7, 9))
    return (rng.randint(6, 14), rng.randint(6, 9)) if k == 2 else (rng.randint(6, 14), rng.randint(4, 6))
def _rc(rng, hp, wp, dens, cols):
    return [[rng.choice(cols) if rng.random() < dens else 0 for _ in range(wp)] for _ in range(hp)]

def gc1(rng):
    hp, wp = _dc(rng, 2); a, b = rng.sample([1, 2, 6, 7, 8, 9], 2)
    return _join([_rc(rng, hp, wp, 0.3, [a]), _rc(rng, hp, wp, 0.3, [b])])
def tc1(g):
    A, B = _two(g); return [[(4 if A[r][c] and B[r][c] else 3 if A[r][c] or B[r][c] else 0) for c in range(len(A[0]))] for r in range(len(A))]
rule("cell_symmetric_difference_and_intersection_painted", "Two same-sized panels of loose coloured cells are separated by a grey 5 column; the output panel has colour 4 where both panels have a nonzero cell, colour 3 where exactly one does, and 0 where neither does.", gc1, _safe(tc1))

def gc2(rng):
    hp, wp = _dc(rng, 3); pal = rng.sample(OC34, 3); return _join([_rc(rng, hp, wp, 0.25, pal) for _ in range(3)])
def tc2(g):
    ps = _three(g)
    def f(r, c):
        vs = {p[r][c] for p in ps if p[r][c]}
        return 0 if not vs else vs.pop() if len(vs) == 1 else 5
    return [[f(r, c) for c in range(len(ps[0][0]))] for r in range(len(ps[0]))]
rule("three_panel_union_conflicts_marked_grey", "Three same-sized panels of loose coloured cells are separated by grey 5 columns; the output panel takes at each position the single colour present there across the panels (equal colours agree), or grey 5 if two panels hold different nonzero colours at that position, or 0 if all three are empty.", gc2, _safe(tc2))

def gc5(rng):
    hp, wp = _dc(rng, 2); col = rng.choice(OC); A = _rc(rng, hp, wp, 0.3, [col]); B = copy(A)
    for r, c in rng.sample([(r, c) for r in range(hp) for c in range(wp)], rng.randint(1, 9)): B[r][c] = 0 if B[r][c] else col
    return _join([A, B])
def tc5(g):
    A, B = _two(g); d = sum(1 for r in range(len(A)) for c in range(len(A[0])) if bool(A[r][c]) != bool(B[r][c])); return [[d, 0]] if d <= 9 else None
rule("number_of_differing_cells_as_digit", "Two same-sized panels of loose cells are separated by a grey 5 column (the right one is the left one with some cells toggled); the output is one row of two cells: a cell whose colour value is the number of positions that are nonzero in exactly one panel (at most 9), then a 0 cell.", gc5, _safe(tc5), digits=True)

def gc6(rng):
    for _ in range(100):
        hp, wp = _dc(rng, 2); s, na, nb = rng.randint(2, 8), rng.randint(3, 10), rng.randint(3, 10)
        pos = rng.sample([(r, c) for r in range(hp) for c in range(wp)], s + na + nb) if hp * wp >= s + na + nb else None
        if not pos: continue
        a, b = rng.choice(OC), rng.choice(OC); A, B = blank(hp, wp), blank(hp, wp)
        for r, c in pos[:s]: A[r][c] = a; B[r][c] = b
        for r, c in pos[s:s + na]: A[r][c] = a
        for r, c in pos[s + na:]: B[r][c] = b
        return _join([A, B])
def tc6(g):
    A, B = _two(g); H, W = dims(A); i = sum(1 for r in range(H) for c in range(W) if A[r][c] and B[r][c]); u = sum(1 for r in range(H) for c in range(W) if A[r][c] or B[r][c])
    return [_bar(i, 3, 30), _bar(u, 4, 30)] if u <= 30 else None
rule("intersection_and_union_cell_counts_as_two_bars", "Two same-sized panels of loose cells are separated by a grey 5 column; the output has two rows of width 30, bars padded with 0 from the left: row 0 colour 3 with the number of positions nonzero in both panels, row 1 colour 4 with the number of positions nonzero in at least one panel.", gc6, _safe(tc6))

def gc9r(rng):
    hp, wp = _dc(rng, 2); A, B = blank(hp, wp), blank(hp, wp); a, b = rng.choice(OC), rng.choice(OC)
    for r in range(hp):
        m = rng.choice((0, 1, 2, 3))
        if m & 1: A[r][rng.randrange(wp)] = a
        if m & 2: B[r][rng.randrange(wp)] = b
    return _join([A, B])
def tc9r(g):
    A, B = _two(g); return [[(4 if any(A[r]) and any(B[r]) else 3 if any(A[r]) else 6 if any(B[r]) else 0)] for r in range(len(A))]
rule("rows_occupied_in_a_b_both_as_a_column", "Two same-sized panels A (left) and B (right) of loose cells are separated by a grey 5 column; the output is a one-cell-wide column as tall as the panels, per row: colour 4 if both panels have a nonzero cell in that row, colour 3 if only A does, colour 6 if only B does, 0 if neither.", gc9r, _safe(tc9r))

def gc9c(rng):
    hp, wp = _dc(rng, 3); ps = [blank(hp, wp) for _ in range(3)]; cs = [rng.choice(OC) for _ in range(3)]
    for c in range(wp):
        m = rng.randint(0, 7)
        for p in range(3):
            if m >> p & 1:
                for _ in range(rng.randint(1, 2)): ps[p][rng.randrange(hp)][c] = cs[p]
    return _join(ps)
def tc9c(g):
    ps = _three(g); W = len(ps[0][0]); return [[{0: 0, 1: 6, 2: 4, 3: 3}[sum(1 for p in ps if any(row[c] for row in p))] for c in range(W)]]
rule("columns_occupied_in_how_many_panels_as_a_row", "Three same-sized panels of loose cells are separated by grey 5 columns; the output is a one-cell-tall row as wide as one panel, per column: colour 3 if all three panels have a nonzero cell in that column, colour 4 if exactly two do, colour 6 if exactly one does, 0 if none does.", gc9c, _safe(tc9c))

def gc10(rng):
    hp, wp = _dc(rng, 2); pal = rng.sample(OC, 5); sa, sb = pal[:3], pal[2:]
    return _join([_rc(rng, hp, wp, 0.3, sa), _rc(rng, hp, wp, 0.25, sb)])
def tc10(g):
    A, B = _two(g); cb = {v for row in B for v in row if v}; return [[v if v not in cb else 0 for v in row] for row in A]
rule("a_cells_whose_colour_is_absent_from_b_kept", "Two same-sized panels A (left) and B (right) of loose coloured cells are separated by a grey 5 column; the output is panel A keeping only cells whose colour is used nowhere in panel B, every other cell erased.", gc10, _safe(tc10))

def gc12(rng):
    for _ in range(100):
        hp, wp = _dc(rng, 2); pal = rng.sample(OC, 3); A = _rc(rng, hp, wp, 0.35, pal[:2]); b = pal[2]; B = blank(hp, wp)
        r0, c0 = rng.randint(0, hp - 3), rng.randint(0, wp - 3)
        for r in range(r0, min(hp, r0 + rng.randint(3, 5))):
            for c in range(c0, min(wp, c0 + rng.randint(3, 5))):
                if rng.random() < 0.5: B[r][c] = b
        for r in range(hp):
            for c in range(wp):
                if B[r][c] and not A[r][c] and rng.random() < 0.7: A[r][c] = rng.choice(pal[:2])
        return _join([A, B])
def tc12(g):
    A, B = _two(g); sh = [(r, c) for r in range(len(A)) for c in range(len(A[0])) if A[r][c] and B[r][c]]
    if len(sh) < 2: return None
    r0, c0, r1, c1 = bbox(sh); return crop(A, r0, c0, r1, c1)
rule("a_cropped_to_box_around_cells_nonzero_in_both", "Two same-sized panels A (left) and B (right) of loose coloured cells are separated by a grey 5 column; the output is the part of panel A inside the smallest box containing every position that is nonzero in both panels (A's cells copied as they are).", gc12, _safe(tc12))


# ---------------------------------------------------------------- cells versus bounding boxes of B objects
def gbb(rng):
    for _ in range(300):
        hp, wp = _d2(rng); a = rng.choice(OC); A = _rc(rng, hp, wp, 0.2, [a])
        B = _layout(rng, hp, wp, [(tuple(random_shape(rng, rng.randint(4, 8))), rng.choice(OC)) for _ in range(rng.randint(2, min(4, _cap(hp, wp))))])
        if B and _bbs(B) is not None: return _join([A, B])
def _bbs(B):
    bs = []
    for o in _o(B):
        r0, c0, r1, c1 = bbox(o['cells'])
        for q in bs:
            if not (r1 < q[0] or q[2] < r0 or c1 < q[1] or q[3] < c0): return None
        bs.append((r0, c0, r1, c1, o['col']))
    return bs
def tbb1(g):
    A, B = _two(g); bs = _bbs(B)
    if bs is None: return None
    return [[A[r][c] if any(q[0] <= r <= q[2] and q[1] <= c <= q[3] for q in bs) else 0 for c in range(len(A[0]))] for r in range(len(A))]
rule("a_cells_inside_bounding_boxes_of_b_objects_kept", "Two same-sized panels A (left, loose cells of one colour) and B (right, a few shapes whose bounding boxes do not overlap, else rejected) are separated by a grey 5 column; the output is panel A keeping only the cells that lie inside the bounding box of some B shape, all other cells erased.", gbb, _safe(tbb1))
def tbb2(g):
    A, B = _two(g); bs = _bbs(B)
    if bs is None: return None
    def f(r, c):
        if not A[r][c]: return 0
        for q in bs:
            if q[0] <= r <= q[2] and q[1] <= c <= q[3]: return q[4]
        return A[r][c]
    return [[f(r, c) for c in range(len(A[0]))] for r in range(len(A))]
rule("a_cells_take_colour_of_b_box_they_lie_in", "Two same-sized panels A (left, loose cells of one colour) and B (right, a few shapes whose bounding boxes do not overlap, else rejected) are separated by a grey 5 column; the output is panel A where every cell inside the bounding box of a B shape takes that shape's colour, cells outside every box unchanged.", gbb, _safe(tbb2))


# ---------------------------------------------------------------- single board with colour classes
def _gboard(masks, cols=(1, 2)):
    def gen(rng):
        for _ in range(400):
            H, W = (rng.randint(21, 30), rng.randint(14, 30)) if rng.random() < 0.45 else (rng.randint(10, 16), rng.randint(10, 16)); cap = _cap(H, W)
            cnt = {m: rng.randint(*masks.get(m, (0, 0))) for m in (1, 2, 3)}; T = _tpls(rng, sum(cnt.values()), 3, 6)
            if not T: continue
            objs, i = [], 0
            for m in (1, 2, 3):
                for _ in range(cnt[m]):
                    for k in range(2):
                        if m >> k & 1: objs.append((T[i], cols[k]))
                    i += 1
            if len(objs) > cap or not objs: continue
            g = _layout(rng, H, W, objs)
            if g: return g
        raise RuntimeError
    return gen
BM = {1: (1, 2), 2: (1, 2), 3: (1, 2)}
def _cls(g):
    o = _o(g); k1 = {x['key'] for x in o if x['col'] == 1}; k2 = {x['key'] for x in o if x['col'] == 2}; return o, k1, k2
def ts5(g):
    o, k1, k2 = _cls(g); return _erase(g, [x for x in o if x['key'] not in (k1 & k2)])
rule("board_keep_shapes_present_in_both_colour_classes", "On one board the objects are colour 1 or colour 2 (two classes, shapes compared up to translation); the output keeps only objects whose pattern occurs among the colour-1 objects and also among the colour-2 objects, erasing every other object.", _gboard(BM), _safe(ts5))
def ts6(g):
    o, k1, k2 = _cls(g); return _erase(g, [x for x in o if x['col'] == 2 or x['key'] in k2])
rule("board_colour_one_shapes_not_in_colour_two_kept", "On one board the objects are colour 1 or colour 2 (shapes compared up to translation); the output keeps only the colour-1 objects whose pattern does not occur among the colour-2 objects, erasing all colour-2 objects and all other colour-1 objects.", _gboard(BM), _safe(ts6))
def ts7(g):
    o, k1, k2 = _cls(g); out = copy(g)
    for x in o:
        if x['key'] in k1 ^ k2:
            for r, c in x['cells']: out[r][c] = 3
    return out
rule("board_shapes_in_only_one_class_recoloured_three", "On one board the objects are colour 1 or colour 2 (shapes compared up to translation); every object whose pattern occurs in only one of the two colour classes is recoloured 3, and objects whose pattern occurs in both classes stay as they are.", _gboard(BM), _safe(ts7))

def gdup(rng):
    for _ in range(400):
        H, W = (rng.randint(21, 30), rng.randint(14, 30)) if rng.random() < 0.45 else (rng.randint(10, 16), rng.randint(10, 16)); cap = _cap(H, W)
        T = _tpls(rng, rng.randint(2, 4), 3, 6); n = [rng.randint(1, 3) for _ in T] if T else []
        if not T or sum(n) > cap or all(x == 1 for x in n) or all(x > 1 for x in n): continue
        g = _layout(rng, H, W, [(s, rng.choice([1, 2, 6, 7, 8, 9])) for s, k in zip(T, n) for _ in range(k)])
        if g: return g
    raise RuntimeError
def tdup(g):
    o = _o(g); cn = {}
    for x in o: cn[x['key']] = cn.get(x['key'], 0) + 1
    out = copy(g)
    for x in o:
        if cn[x['key']] > 1:
            for r, c in x['cells']: out[r][c] = 3
    return out
rule("board_repeated_shapes_recoloured_three", "On one board (no object has colour 3) every object whose cell pattern, up to translation and ignoring colour, also occurs on another object of the board is recoloured 3, and objects with a pattern found nowhere else stay unchanged.", gdup, _safe(tdup))


# ---------------------------------------------------------------- same-position panels
def gsp1(rng):
    for _ in range(400):
        hp, wp = _d2(rng); cap = _cap(hp, wp)
        A = _layout(rng, hp, wp, [(tuple(random_shape(rng, rng.randint(3, 6))), rng.choice([1, 2, 6, 7, 8, 9])) for _ in range(rng.randint(2, cap))])
        B = _layout(rng, hp, wp, [(tuple(random_shape(rng, rng.randint(3, 6))), rng.choice(OC)) for _ in range(rng.randint(2, cap))])
        if A and B: return _join([A, B])
def tsp1(g):
    A, B = _two(g); out = copy(A)
    for o in _o(A):
        if any(B[r][c] for r, c in o['cells']):
            for r, c in o['cells']: out[r][c] = 3
    return out
rule("a_objects_overlapping_b_positions_recoloured_three", "Two same-sized panels A (left) and B (right) are separated by a grey 5 column; the output is panel A where every object having at least one cell at a position where B is nonzero is recoloured 3 (no A object has colour 3), other objects unchanged.", gsp1, _safe(tsp1))

def gsp2(rng):
    for _ in range(400):
        hp, wp = _d2(rng); cap = _cap(hp, wp); big = [tuple(random_shape(rng, rng.randint(5, 9))) for _ in range(rng.randint(2, max(2, cap)))]
        A = blank(hp, wp); pos = []
        for s in sorted(big, key=len, reverse=True):
            p = _rand_put(rng, A, s, rng.choice(OC))
            if not p: break
            pos.append((s, p))
        else:
            B = blank(hp, wp)
            for s, (r, c) in pos[:rng.randint(1, len(pos))]:
                sub = _grow(rng, s, rng.randint(2, 4))
                if not sub: continue
                for y, x in sub:
                    pass
                # place the sub-shape anywhere inside the big object's cells
                cells_ = {(r + y, c + x) for y, x in s}; spots = [(rr, cc) for rr in range(hp) for cc in range(wp) if all((rr + y, cc + x) in cells_ for y, x in sub)]
                if spots:
                    rr, cc = rng.choice(spots)
                    if _fits(B, sub, rr, cc): _stampo(B, sub, rr, cc, rng.choice(OC))
            for _t in range(rng.randint(1, 2)): _rand_put(rng, B, tuple(random_shape(rng, rng.randint(3, 4))), rng.choice(OC))
            ob = _o(B)
            cov = [all(A[r][c] for r, c in o['cells']) for o in ob]
            if ob and any(cov) and not all(cov): return _join([A, B])
    raise RuntimeError
def tsp2(g):
    A, B = _two(g); return _erase(B, [o for o in _o(B) if not all(A[r][c] for r, c in o['cells'])])
rule("b_objects_lying_wholly_on_a_cells_kept", "Two same-sized panels A (left) and B (right) are separated by a grey 5 column; the output is panel B keeping only objects all of whose cells sit at positions where panel A is nonzero, every other B object erased.", gsp2, _safe(tsp2))

def gsp3(rng):
    for _ in range(500):
        hp, wp = _d2(rng); cap = _cap(hp, wp); n = rng.randint(3, max(3, cap)); T = _tpls(rng, n, 3, 5)
        if not T: continue
        A = blank(hp, wp); B = blank(hp, wp); cls = [rng.choice('smx') for _ in T]
        if len(set(cls)) < 3: continue
        ok = True
        for s, k in zip(T, cls):
            p = _rand_put(rng, A, s, rng.choice([1, 2, 6, 7, 8, 9]))
            if not p: ok = False; break
            if k == 's': _stampo(B, s, p[0], p[1], rng.choice(OC))
        if not ok: continue
        for s, k in zip(T, cls):
            if k == 'm':
                pa = next(o['pos'] for o in _o(A) if o['key'] == s)
                for _t in range(80):
                    if _rand_put(rng, B, s, rng.choice(OC)): break
                else: ok = False
        if not ok: continue
        # a moved copy must not coincide with its source position
        pos_ok = all(not any(o['key'] == a['key'] and o['pos'] == a['pos'] for o in _o(B)) for a in _o(A) if cls[T.index(a['key'])] == 'm')
        if pos_ok: return _join([A, B])
def tsp3(g):
    A, B = _two(g); bo = _o(B); out = copy(A)
    for o in _o(A):
        if any(b['key'] == o['key'] and b['pos'] == o['pos'] for b in bo):
            for r, c in o['cells']: out[r][c] = 0
        elif any(b['key'] == o['key'] for b in bo):
            for r, c in o['cells']: out[r][c] = 4
    return out
rule("a_objects_static_moved_or_absent_in_b", "Two same-sized panels A (left) and B (right) are separated by a grey 5 column; in panel A an object whose pattern occurs in B at exactly the same position (colour ignored) is erased, an object whose pattern occurs in B only at other positions is recoloured 4, and an object whose pattern is not in B stays; the output is panel A.", gsp3, _safe(tsp3))
