# b070_sockets.py -- TOOLS AND SOCKETS: multi-part objects (a tool = coloured head glyph + 2-4 cell handle line of a
# second colour; a plug = body row + two prongs; a key = shaft row + teeth) and sockets (a slab of one colour with a
# hole cut as head+slot, an outlet with two prong holes, a lock with five cavities). Rules seat parts by matching one
# PART (head, depth, prong spacing, tooth profile), with rotation/mirror, colour transfer, tie-breaks and counting.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

SHAPES = [  # 3x3 head glyphs, each spans the full 3x3 box and contains the bottom-centre cell (2,1)
    {(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)}, {(0, 0), (0, 1), (0, 2), (1, 1), (2, 1)},
    {(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)}, {(0, 0), (0, 1), (1, 1), (2, 1), (2, 2)},
    {(0, 0), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2)}, {(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (2, 1)},
    {(0, 0), (1, 0), (1, 1), (2, 1), (2, 2)}, {(0, 0), (0, 2), (1, 0), (1, 1), (1, 2), (2, 1)}]
ID = lambda s: s
R1 = rot90
R2 = lambda s: rot90(rot90(s))
R3 = lambda s: rot90(rot90(rot90(s)))
ROT4 = [ID, R1, R2, R3]
FH = flip_h
FV = flip_v


def _pal(rng, n, avoid=()):
    return rng.sample([c for c in range(1, 10) if c not in avoid], n)


def _tool(K, H, si, hl=3):
    s = blank(3 + hl, 3)
    for r, c in SHAPES[si]: s[r][c] = K
    for i in range(hl): s[3 + i][1] = H
    return s


def _sock(F, si, hl=3):
    s = blank(hl + 5, 5, F)
    for r, c in SHAPES[si]: s[1 + r][1 + c] = 0
    for i in range(hl): s[4 + i][2] = 0
    return s


def _up2(s):
    return [[v for v in row for _ in (0, 1)] for row in s for _ in (0, 1)]


def _put(rng, h, w, items, margin=1):
    occ = set(); pos = [None] * len(items)
    for i in sorted(range(len(items)), key=lambda k: -len(items[k]) * len(items[k][0])):
        ih, iw = dims(items[i])
        if ih > h or iw > w: return None
        for _ in range(120):
            r, c = rng.randint(0, h - ih), rng.randint(0, w - iw)
            if any((y, x) in occ for y in range(r - margin, r + ih + margin) for x in range(c - margin, c + iw + margin)): continue
            occ.update((y, x) for y in range(r, r + ih) for x in range(c, c + iw)); pos[i] = (r, c); break
        else:
            return None
    return pos


def _layout(rng, mk, lo=12, hi=20, bigp=0.4):
    for _ in range(300):
        big = rng.random() < bigp
        h, w = (rng.randint(21, 30), rng.randint(21, 30)) if big else (rng.randint(lo, hi), rng.randint(lo, hi))
        items = mk(rng, big)
        if not items: continue
        pos = _put(rng, h, w, items)
        if pos:
            g = blank(h, w)
            for it, (r, c) in zip(items, pos): paste(g, it, r, c, transparent=0)
            return g
    raise RuntimeError("layout")


def _basic(rng, big, ops=None, sock_ops=None, unmatched=0, many=False, hl=3, decoys=0, longer=False, dup=0, bigtool=0, avoid=()):
    nS = rng.randint(3, 5) if big else rng.randint(2, 3)
    shapes = rng.sample(range(8), nS + unmatched)
    hls = [rng.choice((2, 3) if longer else (2, 3, 4)) for _ in range(nS)] if hl == 'rand' else [hl] * nS
    fc = _pal(rng, nS if many else 1, avoid); fcols = fc if many else fc * nS
    tc = [c for c in range(1, 10) if c not in fc and c not in avoid]
    socks = []
    for i in range(nS):
        s = _sock(fcols[i], shapes[i], hls[i])
        if sock_ops: s = rng.choice(ROT4)(s)
        socks.append(s)
    idx = rng.sample(range(nS), rng.randint(1, nS)); tools = []
    for i in idx:
        K, H = rng.sample(tc, 2); tools.append(_tool(K, H, shapes[i], hls[i]))
    for _ in range(dup):
        i = idx[0]; K0 = tools[0][0][1] if SHAPES[shapes[i]] and tools[0][0][1] else None
        K, H = rng.sample(tc, 2)
        while K == max(set(v for row in tools[0] for v in row if v), key=lambda v: sum(r.count(v) for r in tools[0])): K, H = rng.sample(tc, 2)
        tools.append(_tool(K, H, shapes[i], hls[i]))
    for j in range(unmatched):
        K, H = rng.sample(tc, 2); tools.append(_tool(K, H, shapes[nS + j], rng.choice((2, 3, 4)) if hl == 'rand' else hl))
    for _ in range(decoys):
        cand = [i for i in range(nS) if (hls[i] < 4 if longer else True)]
        if not cand: continue
        i = rng.choice(cand); h2 = rng.choice([x for x in (2, 3, 4) if (x > hls[i] if longer else x != hls[i])])
        K, H = rng.sample(tc, 2); tools.append(_tool(K, H, shapes[i], h2))
    for _ in range(bigtool):
        K, H = rng.sample(tc, 2); tools.append(_up2(_tool(K, H, rng.randrange(8), 3)))
    if ops: tools = [rng.choice(ops)(t) for t in tools]
    items = socks + tools; rng.shuffle(items)
    return items


# ---------------- reading ----------------
def _comps(g):
    return _mc(g)


def _mc(g):
    H, W = dims(g); seen = set(); out = []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or g[r][c] == 0: continue
            comp = []; st = [(r, c)]; seen.add((r, c))
            while st:
                y, x = st.pop(); comp.append((y, x))
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    n = (y + dy, x + dx)
                    if 0 <= n[0] < H and 0 <= n[1] < W and n not in seen and g[n[0]][n[1]]:
                        seen.add(n); st.append(n)
            out.append(comp)
    return out


def _majority(sub):
    cnt = counts(sub); cnt.pop(0, None)
    return max(cnt, key=lambda v: cnt[v])


def parse(g):
    socks, tools = [], []
    for comp in _mc(g):
        cols = {g[r][c] for r, c in comp}; r0, c0, r1, c1 = bbox(comp)
        if len(cols) == 1 and len(comp) >= 18:
            zs = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if g[r][c] == 0]
            hb = bbox(zs) if zs else None
            hole = {(r - hb[0], c - hb[1]) for r, c in zs} if zs else set()
            socks.append(dict(F=g[comp[0][0]][comp[0][1]], bb=(r0, c0, r1, c1), hb=hb, hole=hole, cells=comp))
        else:
            sub = blank(r1 - r0 + 1, c1 - c0 + 1)
            for r, c in comp: sub[r - r0][c - c0] = g[r][c]
            K = _majority(sub); Hc = [v for v in cols if v != K]
            tools.append(dict(cells=comp, bb=(r0, c0, r1, c1), sub=sub, K=K, H=Hc[0] if Hc else None))
    return socks, tools


def _fit(tool, sock, ops):
    if not sock['hb']: return None
    hb = sock['hb']; hh, hw = hb[2] - hb[0] + 1, hb[3] - hb[1] + 1
    for op in ops:
        t = op(tool['sub'])
        if dims(t) == (hh, hw) and {(r, c) for r in range(hh) for c in range(hw) if t[r][c]} == sock['hole']:
            return t
    return None


def _assign(tools, socks, ops, order=None):
    used = set(); res = []
    for t in (order or tools):
        for i, s in enumerate(socks):
            if i in used: continue
            img = _fit(t, s, ops)
            if img:
                res.append((t, s, img)); used.add(i); break
    return res


def _erase(out, t, v=0):
    for r, c in t['cells']: out[r][c] = v


def _seat(g, pairs, ghost=0, head_only=False):
    out = copy(g)
    for t, s, img in pairs: _erase(out, t, ghost)
    for t, s, img in pairs:
        if head_only: img = [[v if v == t['K'] else 0 for v in row] for row in img]
        paste(out, img, s['hb'][0], s['hb'][1], transparent=0)
    return out


def _bar(n, w=12):
    return [[2] * n + [0] * (w - n)] if 1 <= n < w else None


def _all_matched(tools, pairs):
    return len(pairs) == len(tools)


def mkb(**kw):
    return lambda rng: _layout(rng, lambda r, b: _basic(r, b, **kw))


# ================================================================== 1-4 seating with transform
SEAT = " Each tool is a 3x3 head glyph of one colour with a handle line of another colour; each socket is a single-colour slab with a hole shaped like a head glyph plus its handle slot."
def tf_seat(ops):
    def f(g):
        socks, tools = parse(g); pairs = _assign(tools, socks, ops)
        return _seat(g, pairs) if _all_matched(tools, pairs) else None
    return f
rule("tool_seats_in_matching_socket", "Each tool moves, unrotated, into the socket whose hole matches its head and handle exactly (the old position becomes black)." + SEAT, mkb(), tf_seat([ID]))
rule("tool_turned_to_fit_socket", "Each tool is lying turned by a quarter, half or three-quarter turn; it is rotated until its handle points down, then moved into the socket whose hole matches it." + SEAT, mkb(ops=[ID, R1, R2, R3]), tf_seat(ROT4))
rule("tool_mirrored_to_fit_socket", "Each tool is either upright or mirrored left-right; mirrored tools are flipped back and every tool is moved into the socket whose hole matches it." + SEAT, mkb(ops=[ID, FH]), tf_seat([ID, FH]))
rule("tool_upside_down_into_socket", "Every tool is flipped top-to-bottom (handle up); each is flipped upright and moved into the socket whose hole matches its head." + SEAT, mkb(ops=[FV]), tf_seat([FV]))


# ================================================================== 5-6 unmatched
def tf_unm_erase(g):
    socks, tools = parse(g); pairs = _assign(tools, socks, [ID]); out = _seat(g, pairs); done = {id(t) for t, _, _ in pairs}
    for t in tools:
        if id(t) not in done: _erase(out, t)
    return out
rule("tool_without_socket_erased", "Each tool moves into the socket whose hole matches its head and handle; a tool with no matching socket is erased to black." + SEAT, mkb(unmatched=2), tf_unm_erase)
def tf_unm_mark(g):
    socks, tools = parse(g); pairs = _assign(tools, socks, [ID]); out = _seat(g, pairs); done = {id(t) for t, _, _ in pairs}
    for t in tools:
        if id(t) not in done:
            for r, c in t['cells']:
                if g[r][c] == t['K']: out[r][c] = 2
    return out
rule("tool_without_socket_head_marked_red", "Each tool moves into the socket whose hole matches it; a tool with no matching socket stays in place and its head cells turn red (2), the handle unchanged." + SEAT, mkb(unmatched=2, avoid=(2,)), tf_unm_mark)


# ================================================================== 7-8 colour transfer
def tf_sock_handle(g):
    socks, tools = parse(g); pairs = _assign(tools, socks, [ID])
    if not _all_matched(tools, pairs): return None
    out = copy(g)
    for t, s, img in pairs:
        _erase(out, t)
        for r, c in s['cells']: out[r][c] = t['H']
    for t, s, img in pairs: paste(out, img, s['hb'][0], s['hb'][1], transparent=0)
    return out
rule("socket_takes_handle_colour_when_seated", "Each tool moves into its matching socket (same head and handle slot), and the whole socket slab is repainted in that tool's handle colour while the seated head keeps its colour." + SEAT, mkb(), tf_sock_handle)
def tf_tool_frame(g):
    socks, tools = parse(g); pairs = _assign(tools, socks, [ID])
    if not _all_matched(tools, pairs): return None
    out = copy(g)
    for t, s, img in pairs:
        for r, c in t['cells']: out[r][c] = s['F']
    return out
rule("tool_takes_frame_colour_of_its_socket", "Tools stay where they are, but each tool (head and handle) is repainted in the slab colour of the one socket whose hole matches it." + SEAT, mkb(many=True), tf_tool_frame)


# ================================================================== 9
def tf_headonly(g):
    socks, tools = parse(g); pairs = _assign(tools, socks, [ID])
    if not _all_matched(tools, pairs): return None
    out = copy(g)
    for t, s, img in pairs:
        for r, c in t['cells']:
            if g[r][c] == t['K']: out[r][c] = 0
    for t, s, img in pairs:
        paste(out, [[v if v == t['K'] else 0 for v in row] for row in img], s['hb'][0], s['hb'][1], transparent=0)
    return out
rule("tool_head_moves_handle_stays", "Only the head moves: each tool's head cells go into the head part of the matching socket's hole, while its handle cells stay where they were and the slot stays black." + SEAT, mkb(), tf_headonly)


# ================================================================== 10
def tf_tie_reading(g):
    socks, tools = parse(g); pairs = _assign(tools, socks, [ID])
    return _seat(g, pairs)
rule("two_tools_one_socket_reading_order", "Each tool moves into its matching socket; when two tools have the same head and there is only one such socket, the tool whose topmost-then-leftmost cell comes first in reading order moves in and the other stays where it is." + SEAT, mkb(dup=1), tf_tie_reading)


# ================================================================== 11
def tf_bigger(g):
    socks, tools = parse(g); pairs = _assign(tools, socks, [ID]); out = _seat(g, pairs); done = {id(t) for t, _, _ in pairs}
    mh = max(s['hb'][2] - s['hb'][0] + 1 for s in socks); mw = max(s['hb'][3] - s['hb'][1] + 1 for s in socks)
    for t in tools:
        if id(t) in done: continue
        h, w = dims(t['sub'])
        if h <= mh and w <= mw: return None
        for r, c in t['cells']: out[r][c] = 2
    return out
rule("oversize_tool_stays_recoloured", "Tools that fit a socket move into it; a tool whose head and handle are twice the size of the holes (larger than every socket) stays and is repainted entirely red (2)." + SEAT, mkb(bigtool=1, avoid=(2,)), tf_bigger)


# ================================================================== 12
def tf_unseated_bar(g):
    socks, tools = parse(g); pairs = _assign(tools, socks, [ID])
    return _bar(len(tools) - len(pairs), 14)
rule("unseated_tools_count_bar", "Count the tools that have no socket with a matching hole and output one row of 14 cells whose first n cells are red (2) and the rest black." + SEAT, lambda rng: _layout(rng, lambda r, b: _basic(r, b, unmatched=rng.randint(1, 3))), tf_unseated_bar, small_ok=True)


# ================================================================== 13-14 depth
def tf_depth(g):
    socks, tools = parse(g); pairs = _assign(tools, socks, [ID])
    return _seat(g, pairs)
rule("tool_seats_only_if_head_and_depth_match", "A tool moves into a socket only when both the head shape and the handle length equal the socket's head and slot depth (slot depth 2, 3 or 4); a tool with the right head but wrong handle length stays." + SEAT, mkb(hl='rand', decoys=2), tf_depth)
def tf_toolong(g):
    socks, tools = parse(g); pairs = _assign(tools, socks, [ID]); out = _seat(g, pairs); done = {id(t) for t, _, _ in pairs}
    for t in tools:
        if id(t) in done: continue
        hd = {(r - t['bb'][0], c - t['bb'][1]) for r, c in t['cells'] if g[r][c] == t['K']}
        hn = sum(1 for r, c in t['cells'] if g[r][c] != t['K'])
        ok = False
        for s in socks:
            if s['hb'] and hd == {p for p in s['hole'] if p[0] < 3} and hn > len(s['hole']) - len(hd): ok = True
        if not ok: return None
        for r, c in t['cells']:
            if g[r][c] != t['K']: out[r][c] = 2
    return out
rule("tool_handle_too_long_marked", "Tools whose head and handle length match a socket move in; a tool whose head matches a socket but whose handle is longer than that socket's slot stays and its handle cells turn red (2)." + SEAT, mkb(hl='rand', decoys=2, longer=True, avoid=(2,)), tf_toolong)


# ================================================================== 15-16 inverse
def _slab_items(rng, big, solid=True):
    n = rng.randint(2, 4) if big else rng.randint(2, 3)
    fc = _pal(rng, n); items = []
    for i in range(n):
        items.append(blank(8, 5, fc[i]))
        others = [c for c in range(1, 10) if c != fc[i]]
        items.append(_tool(rng.choice(others), fc[i], rng.randrange(8), 3))
    rng.shuffle(items)
    return items
def _parse_solid(g):
    slabs, tools = [], []
    for comp in _mc(g):
        cols = {g[r][c] for r, c in comp}; r0, c0, r1, c1 = bbox(comp)
        if len(cols) == 1 and len(comp) >= 18: slabs.append(dict(F=g[comp[0][0]][comp[0][1]], bb=(r0, c0, r1, c1), cells=comp))
        else:
            sub = blank(r1 - r0 + 1, c1 - c0 + 1)
            for r, c in comp: sub[r - r0][c - c0] = g[r][c]
            K = _majority(sub); Hc = [v for v in cols if v != K]
            tools.append(dict(cells=comp, bb=(r0, c0, r1, c1), sub=sub, K=K, H=Hc[0] if Hc else None))
    return slabs, tools
def tf_carve(erase):
    def f(g):
        slabs, tools = _parse_solid(g); out = copy(g)
        for t in tools:
            m = [s for s in slabs if s['F'] == t['H']]
            if len(m) != 1: return None
            s = m[0]
            for r in range(len(t['sub'])):
                for c in range(3):
                    if t['sub'][r][c]: out[s['bb'][0] + 1 + r][s['bb'][1] + 1 + c] = 0
            if erase: _erase(out, t)
        return out
    return f
INV = " Each solid slab has a tool of the same colour as the tool's handle; the tool's head sits on top of a 3-cell handle."
rule("socket_hole_cut_from_its_tool", "For each tool, cut a hole in the solid slab whose colour equals the tool's handle colour: black cells in the tool's head shape starting one row and one column inside the slab's top-left corner, plus the handle slot below; the tool stays." + INV, lambda rng: _layout(rng, _slab_items), tf_carve(False))
rule("socket_hole_cut_tool_consumed", "For each tool, cut a hole in the solid slab whose colour equals the tool's handle colour (the tool's head shape starting one row and one column inside the slab's top-left corner, with its handle slot below), and erase the tool." + INV, lambda rng: _layout(rng, _slab_items), tf_carve(True))


# ================================================================== keys and locks
def _profs(rng, n, nopal=False):
    out = []
    while len(out) < n:
        p = tuple(rng.randint(1, 4) for _ in range(5))
        if p not in out and (not nopal or p != p[::-1]): out.append(p)
    return out
def _key(H, K, p):
    s = blank(5, 5)
    for c in range(5):
        s[0][c] = H
        for r in range(1, p[c] + 1): s[r][c] = K
    return s
def _lock(F, p):
    s = blank(7, 5)
    for r in range(1, 7):
        for c in range(5): s[r][c] = F if r > p[c] else 0
    return s
def _key_items(rng, big, nkeys_unm=0, mirror=False, ucols=None):
    nL = rng.randint(3, 5) if big else rng.randint(2, 3)
    P = _profs(rng, nL + nkeys_unm, mirror)
    F = rng.choice([c for c in range(1, 10) if c != 2]); tc = [c for c in range(1, 10) if c not in (F, 2)]
    items = [_lock(F, p) for p in P[:nL]]
    for p in rng.sample(P[:nL], rng.randint(1, nL)) + P[nL:]:
        H, K = rng.sample(tc, 2); k = _key(H, K, p[::-1] if mirror else p)
        items.append(k)
    rng.shuffle(items); return items
def _parse_kl(g):
    locks, keys = [], []
    for comp in _mc(g):
        cols = {g[r][c] for r, c in comp}; r0, c0, r1, c1 = bbox(comp)
        if c1 - c0 != 4: continue
        if len(cols) == 1:
            r0 = r1 - 5
            prof = tuple(sum(1 for r in range(r0, r1 + 1) if g[r][c] == 0) for c in range(c0, c1 + 1))
            locks.append(dict(F=g[comp[0][0]][comp[0][1]], bb=(r0, c0, r1, c1), prof=prof, cells=comp))
        else:
            cs_ = set(comp); sub = [[g[r][c] if (r, c) in cs_ else 0 for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
            prof = tuple(sum(1 for r in range(1, len(sub)) if sub[r][c]) for c in range(5))
            keys.append(dict(cells=comp, bb=(r0, c0, r1, c1), sub=sub, prof=prof, H=g[r0][c0]))
    return locks, keys
def _match_kl(locks, keys, rev=False):
    res = []; used = set()
    for k in keys:
        for i, l in enumerate(locks):
            if i not in used and l['prof'] == (k['prof'][::-1] if rev else k['prof']):
                res.append((k, l)); used.add(i); break
    return res
def _kl_seat(g, pairs, rev=False, drop=()):
    out = copy(g)
    for k, l in pairs: _erase(out, k)
    for k, l in pairs: paste(out, flip_h(k['sub']) if rev else k['sub'], l['bb'][0] - 1, l['bb'][1], transparent=0)
    return out
KL = " A key is a row of 5 shaft cells with teeth of 1 to 4 cells hanging below each; a lock is a single-colour block with 5 cavities open at the top, one per column."
def tf_key_seat(g):
    locks, keys = _parse_kl(g); pr = _match_kl(locks, keys)
    return _kl_seat(g, pr) if len(pr) == len(keys) else None
rule("key_seats_in_lock_with_same_profile", "Each key moves, shaft directly above the lock's top edge, into the lock whose cavity depths equal the key's tooth lengths column by column (the old key position becomes black)." + KL, lambda rng: _layout(rng, _key_items, 14, 22), tf_key_seat)
def tf_key_tint(g):
    locks, keys = _parse_kl(g); pr = _match_kl(locks, keys); out = copy(g)
    if len(pr) != len(keys): return None
    for k, l in pr:
        for r, c in l['cells']: out[r][c] = k['H']
    return out
rule("lock_takes_shaft_colour_key_stays", "Keys stay put; each lock whose cavity depths equal a key's tooth lengths (column by column) is repainted in that key's shaft colour." + KL, lambda rng: _layout(rng, _key_items, 14, 22), tf_key_tint)
def tf_key_mirror(g):
    locks, keys = _parse_kl(g); pr = _match_kl(locks, keys, True)
    return _kl_seat(g, pr, True) if len(pr) == len(keys) else None
rule("mirrored_key_flipped_into_lock", "Each key is a left-right mirror of the key that fits: flip it, then move it shaft-down-on-top into the lock whose cavity depths equal the key's tooth lengths read right to left (profiles are never symmetric)." + KL, lambda rng: _layout(rng, lambda r, b: _key_items(r, b, 0, True), 14, 22), tf_key_mirror)
def tf_unopened(g):
    locks, keys = _parse_kl(g); pr = _match_kl(locks, keys)
    if len(pr) != len(keys): return None
    out = _kl_seat(g, pr); got = {id(l) for _, l in pr}
    for l in locks:
        if id(l) not in got:
            for r, c in l['cells']: out[r][c] = 2
    return out
rule("keys_seat_unopened_locks_red", "Each key moves into the lock whose cavity depths equal its tooth lengths; every lock that receives no key is repainted red (2)." + KL, lambda rng: _layout(rng, _key_items, 14, 22), tf_unopened)
def tf_key_unm_count(g):
    locks, keys = _parse_kl(g); return _bar(len(keys) - len(_match_kl(locks, keys)))
rule("keys_without_lock_count_bar", "Count the keys whose tooth lengths equal no lock's cavity depths (column by column) and output one row of 12 cells whose first n cells are red (2) and the rest black." + KL, lambda rng: _layout(rng, lambda r, b: _key_items(r, b, rng.randint(1, 3)), 14, 22), tf_key_unm_count, small_ok=True)
def tf_key_unm_erase(g):
    locks, keys = _parse_kl(g); pr = _match_kl(locks, keys); out = _kl_seat(g, pr); got = {id(k) for k, _ in pr}
    for k in keys:
        if id(k) not in got: _erase(out, k)
    return out
rule("keys_without_lock_erased_others_seat", "Each key moves into the lock whose cavity depths equal its tooth lengths; a key that fits no lock is erased." + KL, lambda rng: _layout(rng, lambda r, b: _key_items(r, b, rng.randint(1, 2)), 14, 22), tf_key_unm_erase)


# ================================================================== plugs and outlets
def _plug(B, P, s):
    g = blank(3, s + 1)
    for c in range(s + 1): g[0][c] = B
    for r in (1, 2): g[r][0] = P; g[r][s] = P
    return g
def _outlet(F, s):
    g = blank(5, s + 3)
    for r in range(1, 5):
        for c in range(s + 3): g[r][c] = F
    for r in (1, 2): g[r][1] = 0; g[r][1 + s] = 0
    return g
def _po_items(rng, big, unm=0, dup=0, ocols=False):
    nO = rng.randint(2, 3) if (unm or dup) else (rng.randint(3, 5) if big else rng.randint(2, 3))
    sp = rng.sample(range(2, 7), nO + unm); F = rng.choice([1, 7, 8, 9]); tc = [c for c in range(1, 10) if c != F]
    items = [_outlet(F, s) for s in sp[:nO]]
    for s in rng.sample(sp[:nO], rng.randint(1, nO)) + sp[nO:] + [sp[0]] * dup:
        B, P = rng.sample(tc, 2); items.append(_plug(B, P, s))
    rng.shuffle(items); return items
def _parse_po(g):
    outs, plugs = [], []
    for comp in _mc(g):
        cols = {g[r][c] for r, c in comp}; r0, c0, r1, c1 = bbox(comp)
        if len(cols) == 1:
            zc = sorted({c for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if g[r][c] == 0})
            outs.append(dict(F=g[comp[0][0]][comp[0][1]], bb=(r0, c0, r1, c1), s=zc[-1] - zc[0], cells=comp, zeros=[(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if g[r][c] == 0]))
        else:
            cs_ = set(comp); sub = [[g[r][c] if (r, c) in cs_ else 0 for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
            plugs.append(dict(cells=comp, bb=(r0, c0, r1, c1), sub=sub, s=c1 - c0, B=g[r0][c0]))
    return outs, plugs
def _po_assign(outs, plugs, key=None):
    used = set(); res = []
    for p in (plugs if key is None else sorted(plugs, key=key)):
        for i, o in enumerate(outs):
            if i not in used and o['s'] == p['s']: res.append((p, o)); used.add(i); break
    return res
def _po_seat(g, pairs):
    out = copy(g)
    for p, o in pairs: _erase(out, p)
    for p, o in pairs: paste(out, p['sub'], o['bb'][0] - 1, o['bb'][1] + 1, transparent=0)
    return out
PO = " A plug is a body row with two 2-cell prongs hanging from its ends; an outlet is a single-colour block with two 2-cell prong holes open at the top."
PG = lambda **kw: (lambda rng: _layout(rng, lambda r, b: _po_items(r, b, **kw), 12, 20))
def tf_plug(g):
    outs, plugs = _parse_po(g); pr = _po_assign(outs, plugs)
    return _po_seat(g, pr) if len(pr) == len(plugs) else None
rule("plug_seats_in_outlet_with_same_spacing", "Each plug moves, body row directly above the outlet's top edge, into the outlet whose two prong holes are the same number of columns apart as the plug's prongs (the old plug position becomes black)." + PO, PG(), tf_plug)
def tf_plug_unm(g):
    outs, plugs = _parse_po(g); pr = _po_assign(outs, plugs); out = _po_seat(g, pr); got = {id(p) for p, _ in pr}
    for p in plugs:
        if id(p) not in got:
            for c in range(p['bb'][1], p['bb'][3] + 1): out[p['bb'][0]][c] = 2
    return out
rule("plug_without_outlet_body_red", "Each plug moves into the outlet with the same prong spacing; a plug whose spacing matches no outlet stays and its body row turns red (2)." + PO, PG(unm=2), tf_plug_unm)
def tf_outlet_tint(g):
    outs, plugs = _parse_po(g); pr = _po_assign(outs, plugs); out = copy(g)
    for p, o in pr:
        for r, c in o['cells']: out[r][c] = p['B']
    return out
rule("outlet_takes_plug_body_colour", "Plugs stay put; each outlet whose prong holes are spaced like a plug's prongs is repainted in that plug's body colour, and outlets without a matching plug stay unchanged." + PO, PG(), tf_outlet_tint)
def tf_plug_near(g):
    outs, plugs = _parse_po(g); used = set(); sel = []
    for o in sorted(outs, key=lambda o: o['bb'][:2]):
        cand = [p for p in plugs if p['s'] == o['s'] and id(p) not in used]
        if cand:
            p = min(cand, key=lambda p: (abs(p['bb'][0] - o['bb'][0]) + abs(p['bb'][1] - o['bb'][1]), p['bb'][:2]))
            used.add(id(p)); sel.append((p, o))
    return _po_seat(g, sel)
rule("nearest_plug_takes_the_outlet", "Outlets are served in reading order of their top-left corners; each takes the unused plug with the same prong spacing whose top-left corner is nearest (Manhattan distance, ties to the plug first in reading order), and any other plug stays." + PO, PG(dup=1), tf_plug_near)
def _numplug(rng, big):
    nO = rng.randint(3, 5) if big else rng.randint(2, 3); s = rng.randint(2, 6)
    F, P = rng.sample([6, 7, 8, 9], 2)
    items = [_outlet(F, s) for _ in range(nO)]
    for n in rng.sample(range(1, nO + 1), rng.randint(1, nO)): items.append(_plug(n, P, s))
    rng.shuffle(items); return items
def tf_numplug(g):
    outs, plugs = _parse_po(g); outs.sort(key=lambda o: o['bb'][:2]); pr = []
    for p in plugs:
        if not 1 <= p['B'] <= len(outs): return None
        pr.append((p, outs[p['B'] - 1]))
    return _po_seat(g, pr)
rule("numbered_plug_seats_in_nth_outlet", "All outlets and plugs share one prong spacing; each plug's body colour is a digit n and the plug moves into the n-th outlet, outlets numbered 1.. in reading order of their top-left corners." + PO, lambda rng: _layout(rng, _numplug, 12, 22), tf_numplug, digits=True)
def tf_empty_outlet(g):
    outs, plugs = _parse_po(g); pr = _po_assign(outs, plugs); out = _po_seat(g, pr); got = {id(o) for _, o in pr}
    for o in outs:
        if id(o) not in got:
            for r, c in o['zeros']: out[r][c] = o['s']
    return out
rule("empty_outlet_holes_filled_with_spacing", "Each plug moves into the outlet with the same prong spacing; the two holes of every outlet that gets no plug are filled with the colour whose value equals the number of columns between the two holes." + PO, PG(unm=0, dup=0), tf_empty_outlet, digits=True)
def tf_plug_erase(g):
    outs, plugs = _parse_po(g); pr = _po_assign(outs, plugs); out = _po_seat(g, pr); got = {id(p) for p, _ in pr}
    for p in plugs:
        if id(p) not in got: _erase(out, p)
    return out
rule("plug_without_outlet_erased", "Each plug moves into the outlet with the same prong spacing; a plug with no outlet of that spacing is erased." + PO, PG(unm=2), tf_plug_erase)


# ================================================================== misc tool rules
def tf_absorb(g):
    socks, tools = parse(g); pairs = _assign(tools, socks, [ID])
    if not _all_matched(tools, pairs): return None
    out = copy(g)
    for t, s, img in pairs:
        _erase(out, t); r0, c0, r1, c1 = s['bb']
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1): out[r][c] = t['K']
    return out
rule("socket_absorbs_tool_head_colour", "Each tool is consumed by the socket whose hole matches it: the tool disappears and the socket's whole rectangle (hole included) becomes solid in the tool's head colour." + SEAT, mkb(), tf_absorb)
def tf_rot_sock(g):
    socks, tools = parse(g); pairs = _assign(tools, socks, ROT4)
    return _seat(g, pairs) if _all_matched(tools, pairs) else None
rule("tool_rotated_into_turned_socket", "Sockets lie turned by quarter turns while tools are upright; each tool is rotated by the turn that makes it fit and moved into the socket whose hole matches its head and handle." + SEAT, lambda rng: _layout(rng, lambda r, b: _basic(r, b, sock_ops=True)), tf_rot_sock)
def tf_ghost(g):
    socks, tools = parse(g); pairs = _assign(tools, socks, ROT4)
    return _seat(g, pairs, ghost=8) if _all_matched(tools, pairs) else None
rule("turned_tool_seats_and_leaves_cyan_ghost", "Each tool lies turned by quarter turns; it is rotated until its handle points down and moved into the matching socket, and every cell it vacated becomes cyan (8)." + SEAT, mkb(ops=[R1, R2, R3], avoid=(8,)), tf_ghost)
def tf_vanish(g):
    socks, tools = parse(g); pairs = _assign(tools, socks, [ID]); out = copy(g)
    for t, s, img in pairs:
        _erase(out, t)
        for r, c in s['cells']: out[r][c] = 0
    return out
rule("matched_tool_and_socket_both_vanish", "A tool and the socket whose hole matches it cancel out: both are erased to black; tools and sockets without a partner stay unchanged." + SEAT, lambda rng: _layout(rng, lambda r, b: _basic(r, b, unmatched=1)), tf_vanish)
def tf_closeempty(g):
    socks, tools = parse(g); pairs = _assign(tools, socks, [ID]); out = _seat(g, pairs); got = {id(s) for _, s, _ in pairs}
    for s in socks:
        if id(s) not in got:
            for r, c in [(s['hb'][0] + a, s['hb'][1] + b) for a, b in s['hole']]: out[r][c] = 2
    return out
rule("empty_sockets_filled_red", "Each tool moves into its matching socket; the hole of every socket that receives no tool is filled with red (2)." + SEAT, mkb(avoid=(2,)), tf_closeempty)
def tf_tiecol(g):
    socks, tools = parse(g)
    order = sorted(tools, key=lambda t: (t['K'], t['bb'][:2])); pairs = _assign(tools, socks, [ID], order)
    return _seat(g, pairs)
rule("lower_head_colour_wins_the_socket", "Each tool moves into its matching socket; when two tools have the same head and only one such socket exists, the tool whose head colour has the smaller value moves in and the other stays." + SEAT, mkb(dup=1), tf_tiecol, digits=True)
def _colpair(rng, big):
    n = rng.randint(3, 6) if big else rng.randint(2, 3); si = rng.randrange(8)
    fc = _pal(rng, n); items = [_sock(f, si) for f in fc]
    for f in rng.sample(fc, rng.randint(1, n)):
        items.append(_tool(rng.choice([c for c in range(1, 10) if c != f]), f, si))
    rng.shuffle(items); return items
def tf_colpair(g):
    socks, tools = parse(g); out = copy(g); pairs = []
    for t in tools:
        m = [s for s in socks if s['F'] == t['H']]
        if len(m) != 1: return None
        img = _fit(t, m[0], [ID])
        if not img: return None
        pairs.append((t, m[0], img))
    return _seat(g, pairs)
rule("tool_seats_in_socket_of_its_handle_colour", "All sockets and tools share one head shape; each tool moves into the socket whose slab colour equals the tool's handle colour." + SEAT, lambda rng: _layout(rng, _colpair), tf_colpair)
def _one_sock(rng, big, crop_sock=False):
    n = rng.randint(3, 5) if big else rng.randint(2, 4)
    shapes = rng.sample(range(8), n); F = rng.randrange(1, 10); tc = [c for c in range(1, 10) if c != F]; items = []
    for i, s in enumerate(shapes):
        K, H = rng.sample(tc, 2)
        if crop_sock:
            items.append(_sock(F, s) if i else _tool(K, H, s))
            if i: items[-1] = _sock(rng.randrange(1, 10), s)
            continue
        items.append(_sock(F, s) if i == 0 else _tool(K, H, s))
    if crop_sock:
        items = [_tool(*rng.sample(range(1, 10), 2), shapes[0])] + [_sock(rng.randrange(1, 10), s) for s in shapes]
    else:
        items = [_sock(F, shapes[0])] + [_tool(*rng.sample(tc, 2), s) for s in shapes]
    rng.shuffle(items); return items
def tf_crop_tool(g):
    socks, tools = parse(g)
    if len(socks) != 1: return None
    f = [t for t in tools if _fit(t, socks[0], [ID])]
    return copy(f[0]['sub']) if len(f) == 1 else None
rule("crop_the_tool_that_fits_the_socket", "The grid holds one socket and several tools; output the one tool (head and handle, cropped to its bounding box) whose head and handle match the socket's hole." + SEAT, lambda rng: _layout(rng, _one_sock), tf_crop_tool)
def tf_crop_sock(g):
    socks, tools = parse(g)
    if len(tools) != 1: return None
    f = [s for s in socks if _fit(tools[0], s, [ID])]
    if len(f) != 1: return None
    r0, c0, r1, c1 = f[0]['bb']; return crop(g, r0, c0, r1, c1)
rule("crop_the_socket_that_fits_the_tool", "The grid holds one tool and several sockets; output the one socket (cropped to its bounding box) whose hole matches the tool's head and handle." + SEAT, lambda rng: _layout(rng, lambda r, b: _one_sock(r, b, True)), tf_crop_sock)
def tf_corner(g):
    socks, tools = parse(g); pairs = _assign(tools, socks, [ID]); out = copy(g)
    for t, s, img in pairs: out[s['bb'][0]][s['bb'][1]] = t['H']
    return out
rule("matched_socket_corner_takes_handle_colour", "Tools stay where they are; for each tool, the top-left corner cell of the socket whose hole matches it is repainted in that tool's handle colour." + SEAT, mkb(), tf_corner)
