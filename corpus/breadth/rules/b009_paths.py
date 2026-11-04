# b009_paths.py -- paths, mazes, connectivity, regions. Walls are one colour W, open cells are 0,
# markers/seeds are other colours. All connectivity is 4-neighbour; ties break by reading order.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


def _nb(g, r, c):
    h, w = dims(g)
    return [(r + dr, c + dc) for dr, dc in N4 if 0 <= r + dr < h and 0 <= c + dc < w]


def _comps(g, pred):
    """4-connected components of cells with pred(value), NOT split by colour (glib splits)."""
    h, w = dims(g); seen, out = set(), []
    for r in range(h):
        for c in range(w):
            if (r, c) in seen or not pred(g[r][c]): continue
            comp, st = [], [(r, c)]; seen.add((r, c))
            while st:
                y, x = st.pop(); comp.append((y, x))
                for n in _nb(g, y, x):
                    if n not in seen and pred(g[n[0]][n[1]]): seen.add(n); st.append(n)
            out.append(sorted(comp))
    return out


def _bfs(g, starts, ok):
    """Path distances from starts through cells where ok(value); dict (r,c)->d."""
    d = {s: 0 for s in starts}; q = list(starts)
    for y, x in q:
        for n in _nb(g, y, x):
            if n not in d and ok(g[n[0]][n[1]]): d[n] = d[(y, x)] + 1; q.append(n)
    return d


def _path(g, a, b, ok):
    """Cells of the unique shortest a->b path (inclusive), or None if unreachable or not unique."""
    da = _bfs(g, [a], ok); db = _bfs(g, [b], ok)
    if b not in da: return None
    D = da[b]; cells_ = [p for p in da if p in db and da[p] + db[p] == D]
    return sorted(cells_) if len(cells_) == D + 1 else None


def _regions(g, W):
    return _comps(g, lambda v: v != W)


def _wall(rng, exclude=()):
    return rng.choice([c for c in COLOURS if c not in exclude])


def _field(rng, lo=7, hi=16, border=True, segs=(2, 6), dens=0.0, exclude=(), big=0.4):
    """Random straight wall segments (plus optional border and noise) in colour W. Returns g, W.
    Segment count scales with grid size so big grids still split into several regions."""
    h, w = _sz(rng, lo, hi, big); W = _wall(rng, exclude); g = blank(h, w)
    if border: rect(g, 0, 0, h - 1, w - 1, W, fill=False)
    scale = max(1, (h + w) // 16)
    for _ in range(rng.randint(*segs) * scale):
        full = scale > 1 and rng.random() < 0.5
        if rng.random() < 0.5:
            r = rng.randrange(h); a, b = (0, w - 1) if full else sorted(rng.sample(range(w), 2))
            for c in range(a, b + 1): g[r][c] = W
        else:
            c = rng.randrange(w); a, b = (0, h - 1) if full else sorted(rng.sample(range(h), 2))
            for r in range(a, b + 1): g[r][c] = W
    if dens: sprinkle(rng, g, int(h * w * dens), W)
    return g, W


def _noise(rng, lo=6, hi=14, dens=(0.2, 0.4), exclude=(), big=0.4):
    h, w = _sz(rng, lo, hi, big); W = _wall(rng, exclude); g = blank(h, w)
    sprinkle(rng, g, int(h * w * rng.uniform(*dens)), W)
    return g, W


def _rooms(rng, lo=6, hi=12, gap=(1, 4), doors=(0, 3), exclude=(), big=0.5, hw=None):
    """Full wall lines at random spacing make a grid of small rooms; a few wall cells are knocked out as doors."""
    h, w = hw or _sz(rng, lo, hi, big); W = _wall(rng, exclude); g = blank(h, w)
    rect(g, 0, 0, h - 1, w - 1, W, fill=False)
    r = 0
    while r < h - 1:
        r += rng.randint(*gap) + 1
        if r < h - 1:
            for c in range(w): g[r][c] = W
    c = 0
    while c < w - 1:
        c += rng.randint(*gap) + 1
        if c < w - 1:
            for r in range(h): g[r][c] = W
    inner = [(r, c) for r in range(1, h - 1) for c in range(1, w - 1) if g[r][c] == W
             and ((g[r - 1][c] == 0 and g[r + 1][c] == 0) or (g[r][c - 1] == 0 and g[r][c + 1] == 0))]
    for r, c in rng.sample(inner, min(len(inner), rng.randint(*doors))): g[r][c] = 0
    return g, W


def _maze(rng, lo=7, hi=21, exclude=()):
    """Perfect maze (recursive backtracker) on odd dims; open cells at odd coordinates."""
    if rng.random() < 0.4: lo, hi = 21, 29
    h, w = rng.randrange(lo, hi + 1, 2), rng.randrange(lo, hi + 1, 2); W = _wall(rng, exclude)
    g = blank(h, w, W); g[1][1] = 0; seen = {(1, 1)}; st = [(1, 1)]
    while st:
        r, c = st[-1]
        nbs = [(r + dr, c + dc) for dr, dc in ((-2, 0), (2, 0), (0, -2), (0, 2))
               if 0 < r + dr < h - 1 and 0 < c + dc < w - 1 and (r + dr, c + dc) not in seen]
        if nbs:
            nr, nc = rng.choice(nbs); g[(r + nr) // 2][(c + nc) // 2] = 0; g[nr][nc] = 0; seen.add((nr, nc)); st.append((nr, nc))
        else:
            st.pop()
    return g, W


def _sz(rng, lo, hi, big=0.4):
    """Grid size: with probability `big` both sides fall in the 21-30 band ARC-AGI-2 lives in."""
    if rng.random() < big:
        return rng.randint(21, 30), rng.randint(21, 30)
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _open(g):
    return cells(g, lambda v: v == 0)


def _pick(rng, g, k):
    o = _open(g)
    return rng.sample(o, k) if len(o) >= k else None


# 1 shortest path between two markers through walls, drawn in the marker colour.
def gi_sp(rng):
    g, W = _noise(rng, 7, 16, (0.2, 0.35), big=0.6); M = _wall(rng, (W,))
    p = _pick(rng, g, 2)
    if not p: return None
    for r, c in p: g[r][c] = M
    path = _path(g, p[0], p[1], lambda v: v != W)
    return g if path and len(path) >= 5 else None
def tf_sp(g):
    W = bg_colour([[v for v in row if v] for row in g] or g); mk = cells(g, lambda v: v and v != W)
    if len(mk) != 2: return None
    path = _path(g, mk[0], mk[1], lambda v: v != W)
    if not path: return None
    out = copy(g); M = g[mk[0][0]][mk[0][1]]
    for r, c in path: out[r][c] = M
    return out
rule("shortest_path_between_markers", "The two marker cells are joined by their unique shortest path around the walls, drawn in the marker colour.", gi_sp, tf_sp)


# helper: wall colour = most common non-zero colour
def _W(g):
    cnt = counts(g); cnt.pop(0, None)
    return max(sorted(cnt), key=lambda k: cnt[k]) if cnt else None


# 2 flood the region containing the marker.
def gi_flood(rng):
    g, W = _field(rng, 7, 16, True, (2, 6)); M = _wall(rng, (W,)); p = _pick(rng, g, 1)
    if not p: return None
    g[p[0][0]][p[0][1]] = M
    return g if len(_regions(g, W)) >= 2 else None
def tf_flood(g):
    W = _W(g); mk = cells(g, lambda v: v and v != W)
    if len(mk) != 1: return None
    out = copy(g); M = g[mk[0][0]][mk[0][1]]
    for r, c in _bfs(g, mk, lambda v: v != W): out[r][c] = M
    return out
rule("flood_marker_region", "The whole region that contains the marker cell is filled with the marker's colour.", gi_flood, tf_flood)


# 3 regions coloured by area rank.
def gi_rank(rng):
    g, W = _field(rng, 7, 16, True, (3, 7), big=0.55)
    regs = _regions(g, W); areas = sorted(len(r) for r in regs)
    return g if 2 <= len(regs) <= 9 and len(set(areas)) == len(areas) else None
def tf_rank(g):
    W = _W(g); regs = sorted(_regions(g, W), key=len); out = copy(g)
    for i, reg in enumerate(regs):
        for r, c in reg: out[r][c] = i + 1
    return out
rule("regions_by_area_rank", "Each walled-off region is filled by its size rank: the smallest region becomes 1, the next 2, and so on.", gi_rank, tf_rank, digits=True)


# 4 regions coloured by their number of cells.
def gi_area(rng):
    g, W = _rooms(rng, 5, 10, (1, 3), (0, 4), big=0.75) if rng.random() < 0.7 else _field(rng, 5, 9, True, (3, 8), big=0)
    regs = _regions(g, W)
    return g if 2 <= len(regs) and all(len(r) <= 9 for r in regs) and len({len(r) for r in regs}) >= 2 else None
def tf_area(g):
    W = _W(g); out = copy(g)
    for reg in _regions(g, W):
        if len(reg) > 9: return None
        for r, c in reg: out[r][c] = len(reg)
    return out
rule("regions_by_cell_count", "Each walled-off region is filled with the number equal to how many cells it has.", gi_area, tf_area, digits=True)


# 5 dead ends of a maze.
def gi_dead(rng):
    g, W = _maze(rng, 7, 19, (2,)); return g
def tf_dead(g):
    W = _W(g); out = copy(g)
    for r, c in _open(g):
        if sum(1 for y, x in _nb(g, r, c) if g[y][x] != W) == 1: out[r][c] = 2
    return out
rule("maze_dead_ends_marked", "Every open cell of the maze with only one open neighbour (a dead end) is marked with colour 2.", gi_dead, tf_dead)


# 6 open cells coloured by how many open neighbours they have.
def gi_deg(rng):
    g, W = _noise(rng, 6, 14, (0.25, 0.45), (1, 2, 3, 4)); return g
def tf_deg(g):
    W = _W(g); out = copy(g)
    for r, c in _open(g):
        k = sum(1 for y, x in _nb(g, r, c) if g[y][x] == 0)
        out[r][c] = k
    return out
rule("open_cells_by_open_neighbour_count", "Each open cell is filled with the number of its open side-neighbours (1 to 4); open cells with none stay empty.", gi_deg, tf_deg, digits=True)


# 7 the one region touching both the left and right edges.
def gi_span(rng):
    g, W = _noise(rng, 7, 16, (0.25, 0.4), (3,)); h, w = dims(g)
    regs = [r for r in _regions(g, W) if any(c == 0 for _, c in r) and any(c == w - 1 for _, c in r)]
    return g if len(regs) == 1 and len(_regions(g, W)) >= 3 else None
def tf_span(g):
    W = _W(g); h, w = dims(g); out = copy(g)
    regs = [r for r in _regions(g, W) if any(c == 0 for _, c in r) and any(c == w - 1 for _, c in r)]
    if len(regs) != 1: return None
    for r, c in regs[0]: out[r][c] = 3
    return out
rule("region_spanning_left_to_right", "The single open region that reaches both the left and the right edge is filled with colour 3.", gi_span, tf_span)


# 8 regions coloured by how many markers they contain.
def gi_mcount(rng):
    g, W = _field(rng, 8, 16, True, (3, 7), exclude=(1, 2, 3, 4, 5, 6)); M = _wall(rng, (W, 1, 2, 3, 4, 5, 6))
    regs = _regions(g, W)
    if len(regs) < 2: return None
    sprinkle(rng, g, rng.randint(2, 8), M)
    return g if all(sum(1 for r, c in reg if g[r][c] == M) <= 6 for reg in regs) else None
def tf_mcount(g):
    W = _W(g); out = copy(g)
    for reg in _regions(g, W):
        k = sum(1 for r, c in reg if g[r][c] != 0)
        for r, c in reg:
            if g[r][c] == 0 and k: out[r][c] = k
    return out
rule("regions_by_marker_count", "Each region's empty cells are filled with the number of marker cells that region contains; regions without markers stay empty.", gi_mcount, tf_mcount, digits=True)


# 9 perimeter of the marker's region.
def gi_perim(rng):
    g, W = _field(rng, 8, 16, True, (1, 4)); M = _wall(rng, (W,)); p = _pick(rng, g, 1)
    if not p: return None
    g[p[0][0]][p[0][1]] = M
    reg = _bfs(g, p, lambda v: v != W)
    inner = [(r, c) for r, c in reg if all(g[y][x] != W for y, x in _nb(g, r, c)) and len(_nb(g, r, c)) == 4]
    return g if len(inner) >= 2 else None
def tf_perim(g):
    W = _W(g); mk = cells(g, lambda v: v and v != W)
    if len(mk) != 1: return None
    M = g[mk[0][0]][mk[0][1]]; out = copy(g)
    for r, c in _bfs(g, mk, lambda v: v != W):
        if len(_nb(g, r, c)) < 4 or any(g[y][x] == W for y, x in _nb(g, r, c)): out[r][c] = M
    return out
rule("marker_region_perimeter", "The cells of the marker's region that touch a wall or the grid edge are painted in the marker's colour; the interior stays empty.", gi_perim, tf_perim)


# 10 cells reachable from the seed within k steps, k = the seed's colour.
def gi_steps(rng):
    g, W = _noise(rng, 7, 16, (0.15, 0.3)); S = _wall(rng, (W,)); p = _pick(rng, g, 1)
    if not p: return None
    g[p[0][0]][p[0][1]] = S
    d = _bfs(g, p, lambda v: v == 0)
    return g if max(d.values()) > S else None
def tf_steps(g):
    W = _W(g); mk = cells(g, lambda v: v and v != W)
    if len(mk) != 1: return None
    S = g[mk[0][0]][mk[0][1]]; out = copy(g)
    for p, d in _bfs(g, mk, lambda v: v == 0).items():
        if d <= S: out[p[0]][p[1]] = S
    return out
rule("reachable_within_seed_value_steps", "Every open cell reachable from the seed in at most k steps around the walls takes the seed's colour, where k is the seed's colour number.", gi_steps, tf_steps, digits=True)


# 11 spanning tree of markers by nearest-first L-shaped links.
def gi_tree(rng):
    h, w = _sz(rng, 7, 16); g = blank(h, w); M = _wall(rng, (8,)); k = rng.randint(3, 6)
    pts = rng.sample([(r, c) for r in range(h) for c in range(w)], k)
    for r, c in pts: g[r][c] = M
    return g if tf_tree(g) is not None else None
def tf_tree(g):
    mk = cells(g, lambda v: v != 0); M = g[mk[0][0]][mk[0][1]]; out = copy(g)
    tree, rest = [mk[0]], mk[1:]
    while rest:
        cand = sorted((abs(a[0] - b[0]) + abs(a[1] - b[1]), b, a) for a in tree for b in rest)
        if len(cand) > 1 and cand[0][0] == cand[1][0]: return None
        _, b, a = cand[0]
        for c in range(min(a[1], b[1]), max(a[1], b[1]) + 1): out[a[0]][c] = out[a[0]][c] or 8
        for r in range(min(a[0], b[0]), max(a[0], b[0]) + 1): out[r][b[1]] = out[r][b[1]] or 8
        tree.append(b); rest.remove(b)
    return out
rule("markers_spanning_tree_l_links", "Starting from the top-left marker, the nearest unlinked marker is repeatedly joined to the linked set by a colour-8 L-path (horizontal first) until all markers are connected.", gi_tree, tf_tree)


# 12 cells where two flood fills meet.
def gi_meet(rng):
    g, W = _noise(rng, 7, 16, (0.1, 0.3), (5,)); A, B = colours(rng, 2, (0, W, 5)); p = _pick(rng, g, 2)
    if not p: return None
    g[p[0][0]][p[0][1]] = A; g[p[1][0]][p[1][1]] = B
    return g if tf_meet(g) is not None else None
def tf_meet(g):
    W = _W(g); mk = cells(g, lambda v: v and v != W)
    if len(mk) != 2: return None
    da = _bfs(g, [mk[0]], lambda v: v == 0); db = _bfs(g, [mk[1]], lambda v: v == 0); out = copy(g); n = 0
    for p in da:
        if p in db and da[p] == db[p] and g[p[0]][p[1]] == 0: out[p[0]][p[1]] = 5; n += 1
    return out if n else None
rule("two_floods_meeting_cells", "Floods spread one step at a time from both seeds; the open cells both floods reach at the same moment are marked with colour 5.", gi_meet, tf_meet)


# 13 geodesic Voronoi: each open cell takes the colour of the seed nearest by path.
def gi_gvor(rng):
    g, W = _noise(rng, 7, 16, (0.15, 0.3)); k = rng.randint(2, 4); cs = colours(rng, k, (0, W)); p = _pick(rng, g, k)
    if not p: return None
    for (r, c), col in zip(p, cs): g[r][c] = col
    return g
def tf_gvor(g):
    W = _W(g); seeds = cells(g, lambda v: v and v != W); out = copy(g)
    ds = [_bfs(g, [s], lambda v: v == 0) for s in seeds]
    for r, c in _open(g):
        best = sorted((d[(r, c)], i) for i, d in enumerate(ds) if (r, c) in d)
        if best and (len(best) == 1 or best[0][0] < best[1][0]): out[r][c] = g[seeds[best[0][1]][0]][seeds[best[0][1]][1]]
    return out
rule("geodesic_voronoi_with_walls", "Each open cell takes the colour of the seed that is nearest by walking distance around the walls; cells equally near two seeds stay empty.", gi_gvor, tf_gvor)


# 14 corridors (no 2x2 open block) vs rooms.
def gi_corr(rng):
    g, W = _noise(rng, 7, 16, (0.25, 0.4), (3, 4)); return g if tf_corr(g) is not None else None
def tf_corr(g):
    W = _W(g); h, w = dims(g); room = set()
    for r in range(h - 1):
        for c in range(w - 1):
            if g[r][c] == g[r + 1][c] == g[r][c + 1] == g[r + 1][c + 1] == 0: room |= {(r, c), (r + 1, c), (r, c + 1), (r + 1, c + 1)}
    out = copy(g); op = _open(g)
    if not room or len(room) == len(op): return None
    for r, c in op: out[r][c] = 3 if (r, c) in room else 4
    return out
rule("corridors_vs_rooms", "Open cells that belong to some 2 by 2 open block are rooms (colour 3); all other open cells are corridors (colour 4).", gi_corr, tf_corr)


# 15 count the regions -> a row of that many cells.
def gi_rcount(rng):
    g, W = _field(rng, 6, 14, True, (2, 7)); n = len(_regions(g, W)); return g if 1 <= n <= 30 else None
def tf_rcount(g):
    W = _W(g); n = len(_regions(g, W)); return [[W] * n + [0]] if n <= 29 else None
rule("region_count_row", "Output a single row of the wall colour with one cell per separate open region, followed by one empty cell.", gi_rcount, tf_rcount)
# 16 label regions in reading order of first appearance.
def gi_label(rng):
    g, W = _field(rng, 7, 16, True, (2, 6), exclude=(1, 2, 3, 4, 5), big=0.6); n = len(_regions(g, W)); return g if 2 <= n < W else None
def tf_label(g):
    W = _W(g); out = copy(g); regs = sorted(_regions(g, W), key=lambda r: r[0])
    if len(regs) > 9: return None
    for i, reg in enumerate(regs):
        for r, c in reg: out[r][c] = i + 1
    return out
rule("regions_labelled_reading_order", "Regions are numbered 1, 2, 3... in the order their first cell is met reading left to right, top to bottom, and filled with that number.", gi_label, tf_label, digits=True)


# 17 fill the largest region.
def gi_big(rng):
    g, W = _field(rng, 7, 16, True, (2, 6), exclude=(3,)); a = sorted(len(r) for r in _regions(g, W))
    return g if len(a) >= 2 and a[-1] != a[-2] else None
def tf_big(g):
    W = _W(g); reg = max(_regions(g, W), key=len); out = copy(g)
    for r, c in reg: out[r][c] = 3
    return out
rule("largest_region_filled", "The open region with the most cells is filled with colour 3.", gi_big, tf_big)


# 18 fill the smallest region.
def gi_small(rng):
    g, W = _field(rng, 7, 16, True, (2, 6), exclude=(2,)); a = sorted(len(r) for r in _regions(g, W))
    return g if len(a) >= 2 and a[0] != a[1] else None
def tf_small(g):
    W = _W(g); reg = min(_regions(g, W), key=len); out = copy(g)
    for r, c in reg: out[r][c] = 2
    return out
rule("smallest_region_filled", "The open region with the fewest cells is filled with colour 2.", gi_small, tf_small)


# 19 enclosed regions (not touching the border) filled.
def _touches(reg, h, w):
    return any(r in (0, h - 1) or c in (0, w - 1) for r, c in reg)
def gi_encl(rng):
    g, W = _field(rng, 7, 16, False, (3, 8), exclude=(8,)); h, w = dims(g); regs = _regions(g, W)
    return g if any(not _touches(r, h, w) for r in regs) and any(_touches(r, h, w) for r in regs) else None
def tf_encl(g):
    W = _W(g); h, w = dims(g); out = copy(g)
    for reg in _regions(g, W):
        if not _touches(reg, h, w):
            for r, c in reg: out[r][c] = 8
    return out
rule("enclosed_regions_filled", "Open regions completely enclosed by wall segments are filled with colour 8; regions that reach the grid edge stay empty.", gi_encl, tf_encl)


# 20 shortest path length -> bar.
def gi_plen(rng):
    g, W = _noise(rng, 6, 14, (0.2, 0.35)); M = _wall(rng, (W,)); p = _pick(rng, g, 2)
    if not p: return None
    for r, c in p: g[r][c] = M
    d = _bfs(g, [p[0]], lambda v: v != W)
    return g if p[1] in d and 2 <= d[p[1]] <= 30 else None
def tf_plen(g):
    W = _W(g); mk = cells(g, lambda v: v and v != W)
    if len(mk) != 2: return None
    d = _bfs(g, [mk[0]], lambda v: v != W)
    return [[g[mk[0][0]][mk[0][1]]] * d[mk[1]] + [0]] if mk[1] in d and d[mk[1]] <= 29 else None
rule("path_length_bar", "Output one row in the marker colour whose length is the number of steps on the shortest path between the two markers, followed by one empty cell.", gi_plen, tf_plen)
# 21 crop to the marker's region, region filled.
def gi_rcrop(rng):
    g, W = _field(rng, 8, 18, True, (3, 7)); M = _wall(rng, (W,)); p = _pick(rng, g, 1)
    if not p: return None
    g[p[0][0]][p[0][1]] = M
    return g if len(_regions(g, W)) >= 2 else None
def tf_rcrop(g):
    W = _W(g); mk = cells(g, lambda v: v and v != W)
    if len(mk) != 1: return None
    M = g[mk[0][0]][mk[0][1]]; reg = list(_bfs(g, mk, lambda v: v != W)); out = copy(g)
    for r, c in reg: out[r][c] = M
    return crop(out, *bbox(reg))
rule("marker_region_cropped", "Output the bounding box of the region holding the marker, with that region filled in the marker's colour.", gi_rcrop, tf_rcrop)


# 22 distance parity ripples from a seed.
def gi_par(rng):
    g, W = _noise(rng, 6, 15, (0.15, 0.3), (1, 2)); S = _wall(rng, (W, 1, 2)); p = _pick(rng, g, 1)
    if not p: return None
    g[p[0][0]][p[0][1]] = S; return g
def tf_par(g):
    W = _W(g); mk = cells(g, lambda v: v and v != W)
    if len(mk) != 1: return None
    out = copy(g)
    for p, d in _bfs(g, mk, lambda v: v == 0).items():
        if d: out[p[0]][p[1]] = 1 if d % 2 else 2
    return out
rule("geodesic_distance_parity", "Every open cell reachable from the seed is coloured 1 if its walking distance is odd and 2 if it is even.", gi_par, tf_par)


# 23 distance digits.
def gi_dig(rng):
    g, W = _noise(rng, 5, 12, (0.15, 0.3)); S = _wall(rng, (W,)); p = _pick(rng, g, 1)
    if not p: return None
    g[p[0][0]][p[0][1]] = S; d = _bfs(g, p, lambda v: v == 0)
    return g if max(d.values()) >= 3 else None
def tf_dig(g):
    W = _W(g); mk = cells(g, lambda v: v and v != W)
    if len(mk) != 1: return None
    h, w = dims(g); out = blank(h, w)
    for p, d in _bfs(g, mk, lambda v: v == 0).items():
        if 1 <= d <= 9: out[p[0]][p[1]] = d
    return out
rule("geodesic_distance_digits", "Every cell becomes its walking distance from the seed (1 to 9); the seed, the walls and cells farther than 9 become empty.", gi_dig, tf_dig, digits=True)


# 24 farthest cells from the seed.
def gi_far(rng):
    g, W = _noise(rng, 6, 15, (0.15, 0.3)); S = _wall(rng, (W,)); p = _pick(rng, g, 1)
    if not p: return None
    g[p[0][0]][p[0][1]] = S; d = _bfs(g, p, lambda v: v == 0)
    return g if max(d.values()) >= 3 else None
def tf_far(g):
    W = _W(g); mk = cells(g, lambda v: v and v != W)
    if len(mk) != 1: return None
    d = _bfs(g, mk, lambda v: v == 0); m = max(d.values()); out = copy(g); S = g[mk[0][0]][mk[0][1]]
    for p, k in d.items():
        if k == m: out[p[0]][p[1]] = S
    return out
rule("farthest_cells_from_seed", "The open cells with the longest walking distance from the seed are painted in the seed's colour.", gi_far, tf_far)


# 25 perfect maze solved corner to corner.
def gi_msolve(rng):
    g, W = _maze(rng, 7, 19, (3,)); return g
def tf_msolve(g):
    W = _W(g); h, w = dims(g); path = _path(g, (1, 1), (h - 2, w - 2), lambda v: v != W)
    if not path: return None
    out = copy(g)
    for r, c in path: out[r][c] = 3
    return out
rule("maze_corner_to_corner_path", "The only route through the maze from the top-left open cell to the bottom-right open cell is drawn in colour 3.", gi_msolve, tf_msolve)


# 26 markers reachable from the seed take its colour.
def _seed_markers(rng, lo=7, hi=16):
    g, W = _noise(rng, lo, hi, (0.25, 0.4)); S, M = colours(rng, 2, (0, W)); p = _pick(rng, g, rng.randint(3, 7))
    if not p: return None
    g[p[0][0]][p[0][1]] = S
    for r, c in p[1:]: g[r][c] = M
    reach = _bfs(g, [p[0]], lambda v: v != W); got = [q for q in p[1:] if q in reach]
    return (g, W, S, M, got) if got and len(got) < len(p) - 1 else None
def _seed_of(g):
    W = _W(g); mk = cells(g, lambda v: v and v != W); cnt = counts(g)
    singles = [p for p in mk if cnt[g[p[0]][p[1]]] == 1]
    return (W, singles[0]) if len(singles) == 1 else (W, None)
def gi_reach(rng):
    x = _seed_markers(rng); return x[0] if x else None
def tf_reach(g):
    W, s = _seed_of(g)
    if s is None: return None
    S = g[s[0]][s[1]]; out = copy(g)
    for p in _bfs(g, [s], lambda v: v != W):
        if g[p[0]][p[1]] not in (0, S): out[p[0]][p[1]] = S
    return out
rule("reachable_markers_take_seed_colour", "Every marker that can be reached from the single seed cell around the walls is recoloured with the seed's colour; unreachable markers stay.", gi_reach, tf_reach)


# 27 count of reachable markers -> column.
def gi_rcnt(rng):
    x = _seed_markers(rng); return x[0] if x else None
def tf_rcnt(g):
    W, s = _seed_of(g)
    if s is None: return None
    S = g[s[0]][s[1]]; n = sum(1 for p in _bfs(g, [s], lambda v: v != W) if g[p[0]][p[1]] not in (0, S))
    M = next(v for row in g for v in row if v not in (0, W, S))
    return [[M] for _ in range(n)] + [[0]] if n else None
rule("reachable_marker_count_column", "Output a single column in the marker colour, one cell for each marker reachable from the seed around the walls, followed by one empty cell.", gi_rcnt, tf_rcnt)
# 28 regions without markers filled.
def gi_nomk(rng):
    g, W = _field(rng, 8, 16, True, (3, 7), exclude=(5,)); M = _wall(rng, (W, 5)); regs = _regions(g, W)
    if len(regs) < 2: return None
    sprinkle(rng, g, rng.randint(1, 5), M)
    has = [any(g[r][c] == M for r, c in reg) for reg in regs]
    return g if any(has) and not all(has) else None
def tf_nomk(g):
    W = _W(g); out = copy(g)
    for reg in _regions(g, W):
        if all(g[r][c] == 0 for r, c in reg):
            for r, c in reg: out[r][c] = 5
    return out
rule("regions_without_markers_filled", "Every region that contains no marker is filled with colour 5; regions holding a marker are unchanged.", gi_nomk, tf_nomk)


# 29 walls around the marker's region recoloured.
def gi_wrec(rng):
    g, W = _field(rng, 7, 16, True, (2, 6)); M = _wall(rng, (W,)); p = _pick(rng, g, 1)
    if not p: return None
    g[p[0][0]][p[0][1]] = M
    return g if len(_regions(g, W)) >= 2 else None
def tf_wrec(g):
    W = _W(g); mk = cells(g, lambda v: v and v != W)
    if len(mk) != 1: return None
    M = g[mk[0][0]][mk[0][1]]; out = copy(g)
    for r, c in _bfs(g, mk, lambda v: v != W):
        for y, x in _nb(g, r, c):
            if g[y][x] == W: out[y][x] = M
    return out
rule("walls_around_marker_region_recoloured", "Every wall cell that borders the marker's region is recoloured with the marker's colour.", gi_wrec, tf_wrec)


# 30 chokepoints: open cells whose removal splits their region.
def gi_choke(rng):
    g, W = _noise(rng, 6, 12, (0.3, 0.45), (2,)); return g if tf_choke(g) is not None else None
def tf_choke(g):
    W = _W(g); out = copy(g); n0 = len(_comps(g, lambda v: v != W)); n = 0
    for r, c in _open(g):
        g[r][c] = W; k = len(_comps(g, lambda v: v != W)); g[r][c] = 0
        if k > n0: out[r][c] = 2; n += 1
    return out if n else None
rule("chokepoint_cells_marked", "Every open cell whose removal would split its region into two pieces is marked with colour 2.", gi_choke, tf_choke)


# 31 grey markers recoloured by the reading-order rank of their region.
def gi_grp(rng):
    g, W = _field(rng, 8, 16, True, (2, 5), exclude=(1, 2, 3, 4, 5, 6, 7, 9), big=0.55); regs = _regions(g, W)
    if not 2 <= len(regs) <= 7: return None
    sprinkle(rng, g, rng.randint(3, 10), 9)
    return g if len({i for i, reg in enumerate(regs) if any(g[r][c] == 9 for r, c in reg)}) >= 2 else None
def tf_grp(g):
    out = copy(g); regs = sorted(_regions(g, 8), key=lambda r: r[0])
    if len(regs) > 7: return None
    for i, reg in enumerate(regs):
        for r, c in reg:
            if g[r][c] == 9: out[r][c] = i + 1
    return out
rule("markers_grouped_by_region", "Walls are colour 8; regions are numbered 1, 2, 3... in reading order of their first cell, and every colour-9 marker takes the number of the region it lies in.", gi_grp, tf_grp, digits=True)


# 32 areas of the regions as a row.
def gi_arow(rng):
    if rng.random() < 0.5:
        hw = (rng.randint(21, 30), rng.randint(5, 9)); g, W = _rooms(rng, gap=(1, 3), doors=(0, 2), hw=hw if rng.random() < 0.5 else hw[::-1])
    else:
        g, W = _field(rng, 5, 10, True, (3, 8), big=0)
    regs = _regions(g, W)
    return g if 2 <= len(regs) <= 30 and all(len(r) <= 9 for r in regs) and len({len(r) for r in regs}) >= 2 else None
def tf_arow(g):
    W = _W(g); regs = sorted(_regions(g, W), key=lambda r: r[0])
    return [[len(r) for r in regs]] if len(regs) <= 30 and all(len(r) <= 9 for r in regs) else None
rule("region_areas_row", "Output one row listing the cell count of each region, ordered by where each region first appears in reading order.", gi_arow, tf_arow, digits=True)


# 33 depth from the nearest wall.
def gi_depth(rng):
    g, W = _field(rng, 7, 16, True, (0, 3), 0.05); d = tf_depth(g)
    return g if d is not None and max(v for row in d for v in row) >= 2 else None
def tf_depth(g):
    W = _W(g); h, w = dims(g); out = blank(h, w); d = _bfs(g, cells(g, lambda v: v == W), lambda v: v == 0)
    for p, k in d.items():
        if k > 9: return None
        if k: out[p[0]][p[1]] = k
    return out
rule("depth_from_nearest_wall", "Every open cell becomes its walking distance to the nearest wall cell (1 next to a wall, 2 one further in, ...); the walls themselves become empty.", gi_depth, tf_depth)


# 34 regions coloured by how many grid edges they touch.
def gi_edges(rng):
    g, W = _field(rng, 7, 16, False, (3, 7), exclude=(1, 2, 3, 4, 5)); h, w = dims(g)
    ks = {tf_edges_k(reg, h, w) for reg in _regions(g, W)}
    return g if len(ks) >= 2 else None
def tf_edges_k(reg, h, w):
    return (any(r == 0 for r, _ in reg) + any(r == h - 1 for r, _ in reg) + any(c == 0 for _, c in reg) + any(c == w - 1 for _, c in reg))
def tf_edges(g):
    W = _W(g); h, w = dims(g); out = copy(g)
    for reg in _regions(g, W):
        k = tf_edges_k(reg, h, w)
        for r, c in reg: out[r][c] = k + 1
    return out
rule("regions_by_edges_touched", "Each region is filled with one more than the number of grid edges it touches: 1 for enclosed, up to 5 for touching all four.", gi_edges, tf_edges, digits=True)


# 35 region with the most markers filled.
def gi_most(rng):
    g, W = _field(rng, 8, 16, True, (3, 7)); M = _wall(rng, (W,)); regs = _regions(g, W)
    if len(regs) < 2: return None
    sprinkle(rng, g, rng.randint(3, 9), M)
    ks = sorted(sum(1 for r, c in reg if g[r][c] == M) for reg in regs)
    return g if ks[-1] > ks[-2] else None
def tf_most(g):
    W = _W(g); regs = _regions(g, W); reg = max(regs, key=lambda reg: sum(1 for r, c in reg if g[r][c] != 0)); out = copy(g)
    M = next(g[r][c] for r, c in reg if g[r][c] != 0)
    for r, c in reg: out[r][c] = M
    return out
rule("region_with_most_markers_filled", "The region containing the most marker cells is filled entirely with the marker colour.", gi_most, tf_most)


# 36 prune dead ends repeatedly.
def gi_prune(rng):
    g, W = _noise(rng, 7, 16, (0.2, 0.35)); o = tf_prune(g)
    return g if o is not None and any(v == 0 for row in o for v in row) else None
def tf_prune(g):
    W = _W(g); out = copy(g); changed = True
    while changed:
        changed = False
        for r, c in _open(out):
            if sum(1 for y, x in _nb(out, r, c) if out[y][x] == 0) <= 1: out[r][c] = W; changed = True
    return out if out != g else None
rule("prune_dead_ends_fully", "Dead-end open cells (at most one open neighbour) are turned into wall, again and again, until no dead end remains.", gi_prune, tf_prune)


# 37 shortest path from the marker to the nearest edge cell.
def gi_exit(rng):
    g, W = _noise(rng, 7, 16, (0.25, 0.4)); M = _wall(rng, (W,)); h, w = dims(g)
    inner = [(r, c) for r, c in _open(g) if 1 < r < h - 2 and 1 < c < w - 2]
    if not inner: return None
    r, c = rng.choice(inner); g[r][c] = M
    return g if tf_exit(g) is not None else None
def tf_exit(g):
    W = _W(g); mk = cells(g, lambda v: v and v != W); h, w = dims(g)
    if len(mk) != 1: return None
    d = _bfs(g, mk, lambda v: v != W); edge = sorted((k, p) for p, k in d.items() if p[0] in (0, h - 1) or p[1] in (0, w - 1))
    if not edge or (len(edge) > 1 and edge[0][0] == edge[1][0]): return None
    path = _path(g, mk[0], edge[0][1], lambda v: v != W)
    if not path or len(path) < 3: return None
    out = copy(g); M = g[mk[0][0]][mk[0][1]]
    for r, c in path: out[r][c] = M
    return out
rule("path_to_nearest_edge", "From the marker, the unique shortest route around the walls to the nearest grid-edge cell is drawn in the marker's colour.", gi_exit, tf_exit)


# 38 are the two markers connected? 1x1 answer.
def gi_conn(rng):
    g, W = _noise(rng, 6, 14, (0.3, 0.45), (2, 3)); M = _wall(rng, (W, 2, 3)); p = _pick(rng, g, 2)
    if not p: return None
    for r, c in p: g[r][c] = M
    return g
def tf_conn(g):
    W = _W(g); mk = cells(g, lambda v: v and v != W)
    if len(mk) != 2: return None
    return [[3 if mk[1] in _bfs(g, [mk[0]], lambda v: v != W) else 2, 0]]
rule("markers_connected_flag", "Output a single cell: colour 3 if the two markers lie in the same open region, colour 2 if walls separate them; followed by one empty cell.", gi_conn, tf_conn, demos=(2, 2))
# 39 region sizes as bars, largest first.
def gi_rbars(rng):
    if rng.random() < 0.6:
        hw = (rng.randint(21, 30), rng.randint(8, 14)); g, W = _rooms(rng, gap=(2, 5), doors=(1, 6), hw=hw if rng.random() < 0.5 else hw[::-1])
    else:
        g, W = _field(rng, 6, 12, True, (3, 8), big=0)
    regs = _regions(g, W)
    return g if 2 <= len(regs) <= 30 and max(len(r) for r in regs) <= 30 and len({len(r) for r in regs}) >= 2 else None
def tf_rbars(g):
    W = _W(g); a = sorted((len(r) for r in _regions(g, W)), reverse=True)
    if len(a) > 30 or a[0] > 30: return None
    return [[W] * k + [0] * (a[0] - k) for k in a]
rule("region_sizes_bars", "Output one left-aligned bar per region in the wall colour, as long as that region's cell count, largest region on top.", gi_rbars, tf_rbars)


# 40 turning cells of the shortest path.
def gi_turn(rng):
    g, W = _noise(rng, 7, 16, (0.2, 0.35), (3,), big=0.6); M = _wall(rng, (W, 3)); p = _pick(rng, g, 2)
    if not p: return None
    for r, c in p: g[r][c] = M
    return g if tf_turn(g) is not None else None
def tf_turn(g):
    W = _W(g); mk = cells(g, lambda v: v and v != W)
    if len(mk) != 2: return None
    path = _path(g, mk[0], mk[1], lambda v: v != W)
    if not path or len(path) < 4: return None
    seq = [mk[0]]; rest = set(path) - {mk[0]}
    while rest:
        seq.append(next(n for n in _nb(g, *seq[-1]) if n in rest)); rest.discard(seq[-1])
    out = copy(g); n = 0
    for i in range(1, len(seq) - 1):
        if (seq[i][0] - seq[i - 1][0], seq[i][1] - seq[i - 1][1]) != (seq[i + 1][0] - seq[i][0], seq[i + 1][1] - seq[i][1]): out[seq[i][0]][seq[i][1]] = 3; n += 1
    return out if n else None
rule("shortest_path_turn_cells", "Along the unique shortest path between the two markers, only the cells where the path changes direction are marked with colour 3.", gi_turn, tf_turn)


# 41 regions by area parity.
def gi_apar(rng):
    g, W = _field(rng, 7, 16, True, (3, 7), exclude=(1, 2)); regs = _regions(g, W)
    return g if len(regs) >= 2 and len({len(r) % 2 for r in regs}) == 2 else None
def tf_apar(g):
    W = _W(g); out = copy(g)
    for reg in _regions(g, W):
        for r, c in reg: out[r][c] = 1 if len(reg) % 2 else 2
    return out
rule("regions_by_area_parity", "Regions with an odd number of cells are filled with colour 1 and regions with an even number with colour 2.", gi_apar, tf_apar)


# 42 wall cells that separate two different regions (doors).
def gi_door(rng):
    g, W = _field(rng, 7, 16, True, (2, 6), exclude=(3,)); return g if len(_regions(g, W)) >= 2 and tf_door(g) is not None else None
def tf_door(g):
    W = _W(g); lab = {}
    for i, reg in enumerate(_regions(g, W)):
        for p in reg: lab[p] = i
    out = copy(g); n = 0
    for r, c in cells(g, lambda v: v == W):
        if len({lab[p] for p in _nb(g, r, c) if p in lab}) >= 2: out[r][c] = 3; n += 1
    return out if n else None
rule("wall_cells_between_regions", "Every wall cell that has two different open regions among its side-neighbours is marked with colour 3.", gi_door, tf_door)
