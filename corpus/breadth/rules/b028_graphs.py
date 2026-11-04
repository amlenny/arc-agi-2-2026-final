# b028_graphs.py -- GRIDS AS GRAPHS. Nodes are single cells of one colour sitting on a lattice (spacing s >= 3);
# edges are straight orthogonal runs of a second colour joining lattice-adjacent nodes. Because nodes never touch
# and every edge run has length s-1 >= 2, the edge colour is exactly the colour owning multi-cell components and
# every other non-zero cell is a node (marker colours included), so detection is exact.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collections import deque
from harness import rule
from glib import *


# ---------------------------------------------------------------- generation
def _lat(rng, ss=(3, 4, 5)):
    """Spacing s and lattice nr x nc; grid is (nr-1)*s+3 square-ish. ~45% of draws land in the 21-30 band."""
    s = rng.choice(ss)
    if rng.random() < 0.45:
        lo, hi = -(-18 // s) + 1, (30 - 3) // s + 1
    else:
        lo, hi = 2, max(2, (19 - 3) // s + 1)
    return s, rng.randint(lo, hi), rng.randint(lo, hi)


def _nbrs(p, nr, nc):
    i, j = p
    return [(i + di, j + dj) for di, dj in ((0, 1), (1, 0), (0, -1), (-1, 0)) if 0 <= i + di < nr and 0 <= j + dj < nc]


def _ladj(nodes, edges):
    adj = {p: set() for p in nodes}
    for e in edges:
        a, b = tuple(e); adj[a].add(b); adj[b].add(a)
    return adj


def _gen(rng, kind="any", pn=0.7, pe=0.6, extra=0.3, drop_iso=True, nmin=2, nmax=None, ss=(3, 4, 5)):
    """Random lattice graph -> (s, nr, nc, nodes, edges). kind: any | conn (connected + extra links) | tree | path."""
    s, nr, nc = _lat(rng, ss)
    if kind == "any":
        nodes = {(i, j) for i in range(nr) for j in range(nc) if rng.random() < pn}
        edges = {frozenset((a, b)) for a in nodes for b in _nbrs(a, nr, nc) if b in nodes and rng.random() < pe}
        if drop_iso:
            nodes = {a for a in nodes if any(a in e for e in edges)}
    else:
        hi = max(nmin, int(nr * nc * rng.uniform(0.3, 0.8)))
        n = rng.randint(nmin, min(hi, nmax) if nmax else hi)
        start = (rng.randrange(nr), rng.randrange(nc)); nodes = {start}; edges = set(); tries = 0
        while len(nodes) < n and tries < 600:
            tries += 1
            a = rng.choice(sorted(nodes))
            if kind == "path" and sum(1 for e in edges if a in e) >= 2:
                continue
            free = [b for b in _nbrs(a, nr, nc) if b not in nodes]
            if free:
                b = rng.choice(free); nodes.add(b); edges.add(frozenset((a, b)))
        if kind == "conn":
            edges |= {frozenset((a, b)) for a in nodes for b in _nbrs(a, nr, nc) if b in nodes and rng.random() < extra}
    if len(nodes) < nmin or (nmax and len(nodes) > nmax):
        return None
    return s, nr, nc, nodes, edges


def _render(G, ncol, ecol, marks=None):
    s, nr, nc, nodes, edges = G
    g = blank((nr - 1) * s + 3, (nc - 1) * s + 3)
    for e in edges:
        a, b = sorted(e)
        for k in range(1, s):
            g[1 + a[0] * s + (b[0] - a[0]) * k][1 + a[1] * s + (b[1] - a[1]) * k] = ecol
    for p in nodes:
        g[1 + p[0] * s][1 + p[1] * s] = (marks or {}).get(p, ncol)
    return g


def _two(rng, exclude=()):
    return colours(rng, 2, exclude=(0,) + tuple(exclude))


def _digit_cols(rng):
    e = rng.randint(5, 9)
    return rng.choice([c for c in COLOURS if c != e]), e


# ---------------------------------------------------------------- parsing
def _parse(g):
    """-> dict(nodes: pos->colour, adj, edges: frozenset->run cells, ecol, ncol (majority node colour), s) or None."""
    H, W = dims(g)
    multi = {g[c[0][0]][c[0][1]] for c in components(g, lambda v: v != 0) if len(c) > 1}
    if len(multi) != 1:
        return None
    ecol = multi.pop()
    nodes = {(r, c): v for r, row in enumerate(g) for c, v in enumerate(row) if v and v != ecol}
    if not nodes:
        return None
    adj = {p: set() for p in nodes}; edges = {}
    for (r, c) in nodes:
        for dr, dc in ((0, 1), (1, 0)):
            run = []; y, x = r + dr, c + dc
            while 0 <= y < H and 0 <= x < W and g[y][x] == ecol:
                run.append((y, x)); y += dr; x += dc
            if run and (y, x) in nodes:
                adj[(r, c)].add((y, x)); adj[(y, x)].add((r, c)); edges[frozenset(((r, c), (y, x)))] = run
    if not edges:
        return None
    cnt = {}
    for v in nodes.values():
        cnt[v] = cnt.get(v, 0) + 1
    return dict(nodes=nodes, adj=adj, edges=edges, ecol=ecol, ncol=max(cnt, key=cnt.get),
                s=len(next(iter(edges.values()))) + 1, H=H, W=W)


def _comps(adj):
    seen, out = set(), []
    for p in adj:
        if p in seen:
            continue
        comp, st = {p}, [p]
        while st:
            a = st.pop()
            for b in adj[a]:
                if b not in comp:
                    comp.add(b); st.append(b)
        seen |= comp; out.append(comp)
    return out


def _bfs(adj, src):
    dist = {src: 0}; q = deque([src])
    while q:
        a = q.popleft()
        for b in adj[a]:
            if b not in dist:
                dist[b] = dist[a] + 1; q.append(b)
    return dist


def _fresh(*used):
    return next(c for c in COLOURS if c not in used)


def _is_bridge(adj, e):
    a, b = tuple(e)
    adj2 = {p: set(q) for p, q in adj.items()}; adj2[a].discard(b); adj2[b].discard(a)
    return b not in _bfs(adj2, a)


def _marks(P):
    """Nodes whose colour is not the majority node colour, sorted."""
    return sorted(p for p, v in P["nodes"].items() if v != P["ncol"])


def _route(P, A, B):
    """The unique shortest node sequence A..B along the edges, or None if none or several."""
    adj = P["adj"]; dist = _bfs(adj, A)
    if B not in dist:
        return None
    cnt = {A: 1}
    for p in sorted(dist, key=dist.get):
        if p != A:
            cnt[p] = sum(cnt.get(q, 0) for q in adj[p] if dist[q] == dist[p] - 1)
    if cnt[B] != 1:
        return None
    path = [B]
    while path[-1] != A:
        path.append(next(q for q in adj[path[-1]] if dist[q] == dist[path[-1]] - 1))
    return path[::-1]


def _edge_cells(P, a, b):
    return P["edges"][frozenset((a, b))]


def _comp_cells(P, comp):
    cs = list(comp)
    for e, run in P["edges"].items():
        if next(iter(e)) in comp:
            cs += run
    return cs


# ---------------------------------------------------------------- rules
# 1
def gi_degree(rng):
    G = _gen(rng, "any", nmin=3)
    return _render(G, *_digit_cols(rng)) if G else None
def tf_degree(g):
    P = _parse(g)
    if not P: return None
    out = copy(g)
    for p in P["nodes"]: out[p[0]][p[1]] = len(P["adj"][p])
    return out
rule("nodes_recoloured_by_degree", "Each node is recoloured with the number of links it has (1 to 4); the links stay as drawn.", gi_degree, tf_degree, digits=True)


# 2
def gi_leaves(rng):
    G = _gen(rng, rng.choice(["any", "conn", "tree"]), nmin=3)
    return _render(G, *_two(rng)) if G else None
def tf_leaves(g):
    P = _parse(g)
    if not P: return None
    out = copy(g); m = _fresh(P["ncol"], P["ecol"]); hit = False
    for p, nb in P["adj"].items():
        if len(nb) == 1: out[p[0]][p[1]] = m; hit = True
    return out if hit else None
rule("leaf_nodes_marked", "Every node with exactly one link is recoloured with a new marker colour.", gi_leaves, tf_leaves)


# 3
def gi_erase_edges(rng):
    G = _gen(rng, "any", nmin=2)
    return _render(G, *_two(rng)) if G else None
def tf_erase_edges(g):
    P = _parse(g)
    if not P: return None
    out = copy(g)
    for run in P["edges"].values():
        for r, c in run: out[r][c] = 0
    return out
rule("edges_erased_nodes_kept", "All the connecting lines are erased, leaving only the node cells where they stood.", gi_erase_edges, tf_erase_edges)


# 4
def gi_iso(rng):
    G = _gen(rng, "any", pn=0.6, pe=0.5, drop_iso=False, nmin=3)
    if not G: return None
    adj = _ladj(G[3], G[4])
    if not G[4] or not any(len(v) == 0 for v in adj.values()): return None
    return _render(G, *_two(rng))
def tf_iso(g):
    P = _parse(g)
    if not P: return None
    out = copy(g)
    for p, nb in P["adj"].items():
        if not nb: out[p[0]][p[1]] = 0
    return out
rule("unlinked_nodes_deleted", "Nodes that have no link to any other node are erased; linked nodes and their lines stay.", gi_iso, tf_iso)


# 5
def gi_diam(rng):
    G = _gen(rng, "tree", nmin=4)
    return _render(G, *_two(rng)) if G else None
def tf_diam(g):
    P = _parse(g)
    if not P: return None
    adj = P["adj"]; best, pairs = 0, []
    for a in adj:
        d = _bfs(adj, a)
        if len(d) < len(adj): return None
        for b, v in d.items():
            if v > best: best, pairs = v, [(a, b)]
            elif v == best: pairs.append((a, b))
    if len(pairs) != 2: return None
    out = copy(g); m = _fresh(P["ncol"], P["ecol"])
    for p in pairs[0]: out[p[0]][p[1]] = m
    return out
rule("longest_path_end_nodes_marked", "The two nodes at the ends of the longest route through the tree are recoloured with a marker colour.", gi_diam, tf_diam)


# 6
def gi_rank(rng):
    G = _gen(rng, "any", pn=0.6, pe=0.45, nmin=3)
    if not G or len(_comps(_ladj(G[3], G[4]))) < 2: return None
    return _render(G, *_digit_cols(rng))
def tf_rank(g):
    P = _parse(g)
    if not P: return None
    cs = sorted(_comps(P["adj"]), key=len, reverse=True)
    if len(cs) < 2 or len(cs) > 9 or len({len(c) for c in cs}) != len(cs): return None
    out = copy(g)
    for k, comp in enumerate(cs, 1):
        for r, c in _comp_cells(P, comp): out[r][c] = k
    return out
rule("components_coloured_by_size_rank", "Each separate network is recoloured whole with its rank by node count: 1 for the biggest, 2 next, and so on.", gi_rank, tf_rank, digits=True)


# 7
def gi_cycle(rng):
    G = _gen(rng, rng.choice(["conn", "any"]), extra=0.4, pe=0.7, nmin=4)
    return _render(G, *_two(rng)) if G else None
def tf_cycle(g):
    P = _parse(g)
    if not P: return None
    out = copy(g); m = _fresh(P["ncol"], P["ecol"]); hit = False
    for e in P["edges"]:
        if not _is_bridge(P["adj"], e):
            for p in e: out[p[0]][p[1]] = m; hit = True
    return out if hit else None
rule("cycle_nodes_marked", "Every node that lies on a closed loop of links is recoloured with a marker colour.", gi_cycle, tf_cycle)


# 8
def gi_hubgrey(rng):
    G = _gen(rng, rng.choice(["any", "conn"]), nmin=3)
    return _render(G, *_two(rng, exclude=(5,))) if G else None
def tf_hubgrey(g):
    P = _parse(g)
    if not P: return None
    degs = sorted((len(nb) for nb in P["adj"].values()), reverse=True)
    if len(degs) > 1 and degs[0] == degs[1]: return None
    p = max(P["adj"], key=lambda q: len(P["adj"][q])); out = copy(g); out[p[0]][p[1]] = 5
    return out
rule("most_linked_node_turns_grey", "The single node with the most links becomes grey (5).", gi_hubgrey, tf_hubgrey)


# 9
def gi_route(rng):
    G = _gen(rng, "conn", nmin=5)
    if not G: return None
    adj = _ladj(G[3], G[4]); a = rng.choice(sorted(G[3])); d = _bfs(adj, a)
    far = [b for b, v in d.items() if v >= 2]
    if not far: return None
    n, e, m = colours(rng, 3)
    return _render(G, n, e, {a: m, rng.choice(far): m})
def tf_route(g):
    P = _parse(g)
    if not P: return None
    mk = _marks(P)
    if len(mk) != 2 or P["nodes"][mk[0]] != P["nodes"][mk[1]]: return None
    path = _route(P, mk[0], mk[1])
    if not path: return None
    out = copy(g); m = P["nodes"][mk[0]]
    for a, b in zip(path, path[1:]):
        out[b[0]][b[1]] = m
        for r, c in _edge_cells(P, a, b): out[r][c] = m
    return out
rule("shortest_route_between_marked_nodes", "The shortest route along the lines between the two marked nodes is recoloured in the markers' colour.", gi_route, tf_route)


# 10
def gi_root_only(rng):
    G = _gen(rng, "any", pn=0.6, pe=0.5, nmin=4)
    if not G or len(_comps(_ladj(G[3], G[4]))) < 2: return None
    n, e, m = colours(rng, 3)
    return _render(G, n, e, {rng.choice(sorted(G[3])): m})
def tf_root_only(g):
    P = _parse(g)
    if not P: return None
    mk = _marks(P)
    if len(mk) != 1: return None
    keep = set(_bfs(P["adj"], mk[0])); out = copy(g)
    for comp in _comps(P["adj"]):
        if comp != keep:
            for r, c in _comp_cells(P, comp): out[r][c] = 0
    return out
rule("nodes_unreachable_from_root_deleted", "Every node and line not connected to the marked root node is erased.", gi_root_only, tf_root_only)


# 11
def gi_same_edges(rng):
    G = _gen(rng, "any", nmin=3)
    if not G: return None
    pal = colours(rng, rng.randint(2, 3)); e = rng.choice([c for c in COLOURS if c not in pal])
    marks = {p: rng.choice(pal) for p in G[3]}
    if not any(marks[a] == marks[b] for a, b in map(tuple, G[4])): return None
    return _render(G, pal[0], e, marks)
def tf_same_edges(g):
    P = _parse(g)
    if not P: return None
    out = copy(g); hit = False
    for e, run in P["edges"].items():
        a, b = tuple(e)
        if P["nodes"][a] == P["nodes"][b]:
            for r, c in run: out[r][c] = P["nodes"][a]
            hit = True
    return out if hit else None
rule("links_between_same_colour_nodes_take_colour", "A line joining two nodes of the same colour is recoloured with that colour; lines between different colours stay.", gi_same_edges, tf_same_edges)


# 12
def gi_comp_row(rng):
    G = _gen(rng, "any", pn=0.6, pe=0.45, nmin=3)
    if not G: return None
    cs = _comps(_ladj(G[3], G[4]))
    if not 2 <= len(cs) <= 8 or len({len(c) for c in cs}) != len(cs): return None
    pal = colours(rng, len(cs) + 1)
    marks = {p: pal[k] for k, comp in enumerate(cs) for p in comp}
    return _render(G, pal[0], pal[-1], marks)
def tf_comp_row(g):
    P = _parse(g)
    if not P: return None
    cs = sorted(_comps(P["adj"]), key=len, reverse=True)
    if len({len(c) for c in cs}) != len(cs): return None
    return [[P["nodes"][next(iter(c))] for c in cs]]
rule("component_colours_listed_by_size", "Output one row with each network's colour, ordered from the network with most nodes to the fewest.", gi_comp_row, tf_comp_row)


# 13
def gi_centre(rng):
    G = _gen(rng, "tree", nmin=3)
    return _render(G, *_two(rng)) if G else None
def tf_centre(g):
    P = _parse(g)
    if not P: return None
    adj = P["adj"]; deg = {p: len(a) for p, a in adj.items()}; alive = set(adj)
    while len(alive) > 2:
        leaves = {p for p in alive if deg[p] <= 1}
        if not leaves: return None
        alive -= leaves
        for p in leaves:
            for q in adj[p]:
                if q in alive: deg[q] -= 1
    out = copy(g); m = _fresh(P["ncol"], P["ecol"])
    for p in alive: out[p[0]][p[1]] = m
    return out
rule("tree_centre_marked", "Leaves are peeled off the tree layer by layer until one or two nodes remain; those centre nodes are marked.", gi_centre, tf_centre)


# 14
def gi_arrows(rng):
    G = _gen(rng, "tree", nmin=3)
    if not G: return None
    n, e, m = colours(rng, 3)
    return _render(G, n, e, {rng.choice(sorted(G[3])): m})
def tf_arrows(g):
    P = _parse(g)
    if not P: return None
    mk = _marks(P)
    if len(mk) != 1: return None
    root = mk[0]; d = _bfs(P["adj"], root); out = copy(g); m = P["nodes"][root]
    for e, run in P["edges"].items():
        a, b = tuple(e)
        if a not in d: continue
        child = a if d[a] > d[b] else b
        tip = min(run, key=lambda q: abs(q[0] - child[0]) + abs(q[1] - child[1]))
        out[tip[0]][tip[1]] = m
    return out
rule("links_pointed_away_from_root", "Each line gets an arrow tip in the root's colour at the end farther from the marked root node.", gi_arrows, tf_arrows)


# 15
def gi_depth(rng):
    G = _gen(rng, "tree", nmin=3)
    if not G: return None
    n, e = _digit_cols(rng)
    return _render(G, n, e, {rng.choice(sorted(G[3])): _fresh(n, e)})
def tf_depth(g):
    P = _parse(g)
    if not P: return None
    mk = _marks(P)
    if len(mk) != 1: return None
    d = _bfs(P["adj"], mk[0])
    if len(d) != len(P["adj"]) or max(d.values()) >= 9: return None
    out = copy(g)
    for p, v in d.items(): out[p[0]][p[1]] = v + 1
    return out
rule("tree_nodes_coloured_by_depth", "Each node is recoloured with its depth from the marked root: the root 1, its neighbours 2, theirs 3, and so on.", gi_depth, tf_depth, digits=True)


# 16
def gi_adjtab(rng):
    G = _gen(rng, "any", pn=rng.uniform(0.3, 0.6), pe=0.6, nmin=2, nmax=30)
    return _render(G, *_two(rng)) if G else None
def tf_adjtab(g):
    P = _parse(g)
    if not P: return None
    ps = sorted(P["adj"]); n = len(ps)
    if n > 30: return None
    return [[P["ecol"] if i == j else (P["ncol"] if ps[j] in P["adj"][ps[i]] else 0) for j in range(n)] for i in range(n)]
rule("adjacency_table_of_network", "Output a square table, one row and column per node in reading order: node colour where two nodes are linked, line colour on the diagonal.", gi_adjtab, tf_adjtab)


# 17
def gi_deghist(rng):
    G = _gen(rng, rng.choice(["any", "conn"]), nmin=3)
    return _render(G, *_two(rng)) if G else None
def tf_deghist(g):
    P = _parse(g)
    if not P: return None
    cnt = [sum(1 for nb in P["adj"].values() if len(nb) == d) for d in (1, 2, 3, 4)]
    h = max(cnt); out = blank(h, 4)
    for c, k in enumerate(cnt):
        for r in range(h - k, h): out[r][c] = P["ncol"]
    return out
rule("degree_histogram_four_columns", "Output four columns of bars: how many nodes have 1, 2, 3 and 4 links, left to right.", gi_deghist, tf_deghist)


# 18
def gi_nvse(rng):
    G = _gen(rng, rng.choice(["any", "conn", "tree"]), nmin=2)
    return _render(G, *_two(rng)) if G else None
def tf_nvse(g):
    P = _parse(g)
    if not P: return None
    n, e = len(P["adj"]), len(P["edges"]); h = max(n, e); out = blank(h, 2)
    for r in range(h - n, h): out[r][0] = P["ncol"]
    for r in range(h - e, h): out[r][1] = P["ecol"]
    return out
rule("node_count_and_link_count_bars", "Output two bars: a node-coloured bar as tall as the node count beside a line-coloured bar as tall as the link count.", gi_nvse, tf_nvse)


# 19
def gi_prune(rng):
    G = _gen(rng, rng.choice(["tree", "conn", "any"]), nmin=4)
    return _render(G, *_two(rng)) if G else None
def tf_prune(g):
    P = _parse(g)
    if not P: return None
    out = copy(g); hit = False
    for p, nb in P["adj"].items():
        if len(nb) == 1:
            out[p[0]][p[1]] = 0; hit = True
            for r, c in _edge_cells(P, p, next(iter(nb))): out[r][c] = 0
    return out if hit and any(v for row in out for v in row) else None
rule("leaf_nodes_and_their_links_pruned", "Every node with a single link is removed together with that link.", gi_prune, tf_prune)


# 20
def gi_bridges(rng):
    G = _gen(rng, rng.choice(["conn", "any"]), extra=0.35, pe=0.7, nmin=4)
    return _render(G, *_two(rng)) if G else None
def tf_bridges(g):
    P = _parse(g)
    if not P: return None
    out = copy(g); m = _fresh(P["ncol"], P["ecol"]); hit = False
    for e, run in P["edges"].items():
        if _is_bridge(P["adj"], e):
            for r, c in run: out[r][c] = m
            hit = True
    return out if hit else None
rule("bridge_links_recoloured", "A line whose removal would split its network in two is recoloured with a marker colour.", gi_bridges, tf_bridges)


# 21
def gi_ends(rng):
    G = _gen(rng, "any", nmin=3)
    if not G: return None
    keep = {p for p in G[3] if rng.random() < 0.3} or {rng.choice(sorted(G[3]))}
    if len(keep) == len(G[3]): return None
    return _render((G[0], G[1], G[2], keep, G[4]), *_two(rng))
def tf_ends(g):
    cs = components(g, lambda v: v != 0); H, W = dims(g)
    multi = {g[c[0][0]][c[0][1]] for c in cs if len(c) > 1}; single = {g[c[0][0]][c[0][1]] for c in cs if len(c) == 1}
    if len(multi) != 1 or len(single) != 1: return None
    ncol = single.pop(); out = copy(g)
    for c in cs:
        if len(c) < 2: continue
        q = sorted(c); (r0, c0), (r1, c1) = q[0], q[-1]
        dr, dc = (r1 > r0) - (r1 < r0), (c1 > c0) - (c1 < c0)
        for y, x in ((r0 - dr, c0 - dc), (r1 + dr, c1 + dc)):
            if 0 <= y < H and 0 <= x < W and out[y][x] == 0: out[y][x] = ncol
    return out
rule("missing_nodes_added_at_line_ends", "Every line end that has no node gets a node cell in the node colour.", gi_ends, tf_ends)


# 22
def gi_linkall(rng):
    G = _gen(rng, "any", pn=0.75, pe=0.4, drop_iso=False, nmin=3)
    if not G or not G[4]: return None
    s, nr, nc, nodes, edges = G
    if all(frozenset((a, b)) in edges for a in nodes for b in _nbrs(a, nr, nc) if b in nodes): return None
    return _render(G, *_two(rng))
def tf_linkall(g):
    P = _parse(g)
    if not P: return None
    s = P["s"]; out = copy(g); hit = False
    for (r, c) in P["adj"]:
        for dr, dc in ((0, 1), (1, 0)):
            q = (r + dr * s, c + dc * s)
            if q in P["adj"] and all(g[r + dr * k][c + dc * k] == 0 for k in range(1, s)):
                for k in range(1, s): out[r + dr * k][c + dc * k] = P["ecol"]
                hit = True
    return out if hit else None
rule("all_neighbouring_nodes_linked", "Every pair of nodes one lattice step apart on a row or column that is not yet joined gets a line between them.", gi_linkall, tf_linkall)


# 23
def gi_csize(rng):
    G = _gen(rng, "any", pn=0.55, pe=0.45, drop_iso=False, nmin=3)
    return _render(G, *_digit_cols(rng)) if G else None
def tf_csize(g):
    P = _parse(g)
    if not P: return None
    out = copy(g)
    for comp in _comps(P["adj"]):
        if len(comp) > 9: return None
        for p in comp: out[p[0]][p[1]] = len(comp)
    return out
rule("nodes_coloured_by_component_size", "Each node is recoloured with the number of nodes in its own network (a lone node becomes 1).", gi_csize, tf_csize, digits=True)


# 24
def gi_largest(rng):
    G = _gen(rng, "any", pn=0.6, pe=0.45, nmin=3)
    if not G or len(_comps(_ladj(G[3], G[4]))) < 2: return None
    return _render(G, *_two(rng))
def tf_largest(g):
    P = _parse(g)
    if not P: return None
    cs = sorted(_comps(P["adj"]), key=len, reverse=True)
    if len(cs) < 2 or len(cs[0]) == len(cs[1]): return None
    out = copy(g)
    for comp in cs[1:]:
        for r, c in _comp_cells(P, comp): out[r][c] = 0
    return out
rule("only_largest_network_kept", "Only the network with the most nodes is kept; every other network is erased.", gi_largest, tf_largest)


# 25
def gi_smallest(rng):
    G = _gen(rng, "any", pn=0.6, pe=0.45, nmin=3)
    if not G or len(_comps(_ladj(G[3], G[4]))) < 2: return None
    return _render(G, *_two(rng))
def tf_smallest(g):
    P = _parse(g)
    if not P: return None
    cs = sorted(_comps(P["adj"]), key=len)
    if len(cs) < 2 or len(cs[0]) == len(cs[1]): return None
    out = copy(g)
    for r, c in _comp_cells(P, cs[0]): out[r][c] = 0
    return out
rule("smallest_network_deleted", "The network with the fewest nodes is erased; the others stay.", gi_smallest, tf_smallest)


# 26
def gi_faces(rng):
    G = _gen(rng, rng.choice(["conn", "any"]), extra=0.5, pe=0.75, pn=0.8, nmin=4)
    return _render(G, *_two(rng)) if G else None
def tf_faces(g):
    P = _parse(g)
    if not P: return None
    H, W = dims(g); seen = set()
    st = [(r, c) for r in range(H) for c in range(W) if (r in (0, H - 1) or c in (0, W - 1)) and g[r][c] == 0]
    while st:
        y, x = st.pop()
        if (y, x) in seen or not (0 <= y < H and 0 <= x < W) or g[y][x] != 0: continue
        seen.add((y, x)); st += [(y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)]
    out = copy(g); m = _fresh(P["ncol"], P["ecol"]); hit = False
    for r in range(H):
        for c in range(W):
            if g[r][c] == 0 and (r, c) not in seen: out[r][c] = m; hit = True
    return out if hit else None
rule("enclosed_faces_of_network_filled", "Every empty region fenced in by nodes and lines is filled with a marker colour.", gi_faces, tf_faces)


# 27
def gi_unfold(rng):
    G = _gen(rng, "path", nmin=3)
    return _render(G, *_two(rng)) if G else None
def tf_unfold(g):
    P = _parse(g)
    if not P: return None
    adj = P["adj"]; ends = [p for p, nb in adj.items() if len(nb) == 1]
    if len(ends) != 2 or any(len(nb) > 2 for nb in adj.values()) or len(_comps(adj)) != 1: return None
    n = len(adj); return [[P["ncol"]] + ([P["ecol"]] * (P["s"] - 1) + [P["ncol"]]) * (n - 1)]
rule("winding_path_graph_straightened", "The single winding chain of nodes and lines is laid out as one straight horizontal row, node, line, node, line, and so on.", gi_unfold, tf_unfold)


# 28
def gi_sizebars(rng):
    G = _gen(rng, "any", pn=0.6, pe=0.45, nmin=3)
    if not G or len(_comps(_ladj(G[3], G[4]))) < 2: return None
    return _render(G, *_two(rng))
def tf_sizebars(g):
    P = _parse(g)
    if not P: return None
    sizes = sorted((len(c) for c in _comps(P["adj"])), reverse=True)
    if len(sizes) < 2: return None
    return [[P["ncol"]] * k + [0] * (sizes[0] - k) for k in sizes]
rule("component_sizes_as_bar_rows", "Output one left-aligned bar per network, as long as its node count, longest bar on top.", gi_sizebars, tf_sizebars)


# 29
def gi_parity(rng):
    G = _gen(rng, rng.choice(["conn", "tree"]), nmin=3)
    if not G: return None
    n, e, m = colours(rng, 3)
    return _render(G, n, e, {rng.choice(sorted(G[3])): m})
def tf_parity(g):
    P = _parse(g)
    if not P: return None
    mk = _marks(P)
    if len(mk) != 1: return None
    d = _bfs(P["adj"], mk[0]); out = copy(g); m = P["nodes"][mk[0]]
    for p, v in d.items():
        if v % 2: out[p[0]][p[1]] = m
    return out
rule("odd_steps_from_root_take_root_colour", "Every node an odd number of links away from the marked root is recoloured in the root's colour.", gi_parity, tf_parity)


# 30
def gi_mid(rng):
    G = _gen(rng, rng.choice(["any", "conn"]), nmin=2, ss=(4, 6))
    return _render(G, *_two(rng)) if G else None
def tf_mid(g):
    P = _parse(g)
    if not P or P["s"] % 2: return None
    out = copy(g); m = _fresh(P["ncol"], P["ecol"])
    for run in P["edges"].values():
        r, c = run[(P["s"] - 2) // 2]; out[r][c] = m
    return out
rule("link_midpoints_marked", "The middle cell of every line between two nodes is recoloured with a marker colour.", gi_mid, tf_mid)


# 31
def gi_infect(rng):
    G = _gen(rng, rng.choice(["conn", "any"]), nmin=4)
    if not G: return None
    n, e, m = colours(rng, 3)
    return _render(G, n, e, {rng.choice(sorted(G[3])): m})
def tf_infect(g):
    P = _parse(g)
    if not P: return None
    mk = _marks(P)
    if len(mk) != 1 or not P["adj"][mk[0]]: return None
    out = copy(g); m = P["nodes"][mk[0]]
    for p in P["adj"][mk[0]]: out[p[0]][p[1]] = m
    return out
rule("marked_node_colours_its_neighbours", "The nodes directly linked to the one marked node take the marker's colour.", gi_infect, tf_infect)


# 32
def gi_flood(rng):
    G = _gen(rng, "any", pn=0.6, pe=0.5, nmin=4)
    if not G: return None
    n, e, m = colours(rng, 3)
    return _render(G, n, e, {rng.choice(sorted(G[3])): m})
def tf_flood(g):
    P = _parse(g)
    if not P: return None
    mk = _marks(P)
    if len(mk) != 1: return None
    d = _bfs(P["adj"], mk[0])
    if len(d) < 2: return None
    out = copy(g); m = P["nodes"][mk[0]]
    for p in d: out[p[0]][p[1]] = m
    return out
rule("marker_colour_floods_whole_network", "Every node reachable along the lines from the marked node takes the marker's colour; other networks are untouched.", gi_flood, tf_flood)


# 33
def gi_tworoots(rng):
    G = _gen(rng, "conn", nmin=6)
    if not G: return None
    n, e, a, b = colours(rng, 4); pa, pb = rng.sample(sorted(G[3]), 2)
    return _render(G, n, e, {pa: a, pb: b})
def tf_tworoots(g):
    P = _parse(g)
    if not P: return None
    mk = _marks(P)
    if len(mk) != 2 or P["nodes"][mk[0]] == P["nodes"][mk[1]]: return None
    da, db = _bfs(P["adj"], mk[0]), _bfs(P["adj"], mk[1]); out = copy(g); hit = False
    for p in P["adj"]:
        if p in mk or p not in da or p not in db or da[p] == db[p]: continue
        out[p[0]][p[1]] = P["nodes"][mk[0] if da[p] < db[p] else mk[1]]; hit = True
    return out if hit else None
rule("nodes_take_colour_of_nearer_root", "Each node takes the colour of whichever of the two marked nodes is fewer links away; ties stay unchanged.", gi_tworoots, tf_tworoots)


# 34
def gi_dissolve(rng):
    G = _gen(rng, rng.choice(["path", "conn", "any"]), nmin=3)
    return _render(G, *_two(rng)) if G else None
def tf_dissolve(g):
    P = _parse(g)
    if not P: return None
    out = copy(g); hit = False
    for p, nb in P["adj"].items():
        if len(nb) == 2:
            a, b = nb
            if a[0] == b[0] or a[1] == b[1]: out[p[0]][p[1]] = P["ecol"]; hit = True
    return out if hit else None
rule("straight_through_nodes_dissolved", "A node with exactly two links in a straight line is removed and the line runs straight through it.", gi_dissolve, tf_dissolve)


# 35
def gi_corner(rng):
    G = _gen(rng, rng.choice(["path", "conn", "tree"]), nmin=3)
    return _render(G, *_two(rng)) if G else None
def tf_corner(g):
    P = _parse(g)
    if not P: return None
    out = copy(g); m = _fresh(P["ncol"], P["ecol"]); hit = False
    for p, nb in P["adj"].items():
        if len(nb) == 2:
            a, b = nb
            if a[0] != b[0] and a[1] != b[1]: out[p[0]][p[1]] = m; hit = True
    return out if hit else None
rule("corner_nodes_marked", "A node with exactly two links that meet at a right angle is recoloured with a marker colour.", gi_corner, tf_corner)


# 36
def gi_toggle(rng):
    G = _gen(rng, "any", pn=0.75, pe=0.5, drop_iso=False, nmin=3)
    return _render(G, *_two(rng)) if G and G[4] else None
def tf_toggle(g):
    P = _parse(g)
    if not P: return None
    s = P["s"]; out = copy(g)
    for (r, c) in P["adj"]:
        for dr, dc in ((0, 1), (1, 0)):
            if (r + dr * s, c + dc * s) in P["adj"]:
                vals = {g[r + dr * k][c + dc * k] for k in range(1, s)}
                new = 0 if vals == {P["ecol"]} else (P["ecol"] if vals == {0} else None)
                if new is None: return None
                for k in range(1, s): out[r + dr * k][c + dc * k] = new
    return out
rule("neighbour_links_toggled", "Between every pair of neighbouring nodes a line is erased if present and drawn if absent.", gi_toggle, tf_toggle)


# 37
def gi_subtree(rng):
    G = _gen(rng, "tree", nmin=3, nmax=9)
    if not G: return None
    n, e = _digit_cols(rng)
    return _render(G, n, e, {rng.choice(sorted(G[3])): _fresh(n, e)})
def tf_subtree(g):
    P = _parse(g)
    if not P: return None
    mk = _marks(P)
    if len(mk) != 1: return None
    d = _bfs(P["adj"], mk[0])
    if len(d) != len(P["adj"]) or len(d) > 9: return None
    size = {}
    for p in sorted(d, key=d.get, reverse=True):
        size[p] = 1 + sum(size[q] for q in P["adj"][p] if d[q] == d[p] + 1)
    out = copy(g)
    for p, v in size.items(): out[p[0]][p[1]] = v
    return out
rule("tree_nodes_coloured_by_subtree_size", "Each node is recoloured with the number of nodes in its branch below the marked root, itself included; the root gets the total.", gi_subtree, tf_subtree, digits=True)


# 38
def gi_cut(rng):
    G = _gen(rng, rng.choice(["conn", "any"]), extra=0.35, pe=0.65, nmin=4)
    return _render(G, *_two(rng)) if G else None
def tf_cut(g):
    P = _parse(g)
    if not P: return None
    adj = P["adj"]; out = copy(g); m = _fresh(P["ncol"], P["ecol"]); hit = False
    for p, nb in adj.items():
        if len(nb) < 2: continue
        adj2 = {q: set(v) - {p} for q, v in adj.items() if q != p}
        if any(q not in _bfs(adj2, next(iter(nb))) for q in nb): out[p[0]][p[1]] = m; hit = True
    return out if hit else None
rule("cut_vertices_marked", "A node whose removal would split its network into separate pieces is recoloured with a marker colour.", gi_cut, tf_cut)


# 39
def gi_degseq(rng):
    G = _gen(rng, rng.choice(["any", "conn", "tree"]), pn=rng.uniform(0.3, 0.6), nmin=3, nmax=30)
    return _render(G, *_digit_cols(rng)) if G else None
def tf_degseq(g):
    P = _parse(g)
    if not P: return None
    degs = sorted((len(nb) for nb in P["adj"].values()), reverse=True)
    return [degs] if len(set(degs)) > 1 else None
rule("degree_sequence_row", "Output one row listing the number of links of every node, largest first.", gi_degseq, tf_degseq, digits=True)


# 40
def gi_route_row(rng):
    G = _gen(rng, "conn", nmin=5)
    if not G: return None
    adj = _ladj(G[3], G[4]); a = rng.choice(sorted(G[3])); d = _bfs(adj, a)
    far = [b for b, v in d.items() if v >= 2]
    if not far: return None
    n, e, m = colours(rng, 3)
    return _render(G, n, e, {a: m, rng.choice(far): m})
def tf_route_row(g):
    P = _parse(g)
    if not P: return None
    mk = _marks(P)
    if len(mk) != 2 or P["nodes"][mk[0]] != P["nodes"][mk[1]]: return None
    path = _route(P, mk[0], mk[1])
    if not path: return None
    m = P["nodes"][mk[0]]; row = [m]
    for i in range(1, len(path)):
        row += [P["ecol"]] * (P["s"] - 1) + [m if i == len(path) - 1 else P["ncol"]]
    return [row]
rule("route_between_marks_laid_out_straight", "The shortest route between the two marked nodes is output as one straight row: marker, lines and intermediate nodes, marker.", gi_route_row, tf_route_row)
