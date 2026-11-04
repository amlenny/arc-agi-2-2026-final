# glib.py -- small grid toolkit for breadth-lane rule authors. Grids are lists of lists of ints 0..9.
# Keep rules short: an input generator of 5-20 lines and a transform of 5-20 lines using these helpers.
import random

COLOURS = list(range(1, 10))


def blank(h, w, c=0):
    return [[c] * w for _ in range(h)]


def copy(g):
    return [r[:] for r in g]


def dims(g):
    return len(g), len(g[0])


def size(rng, lo=5, hi=20):
    return rng.randint(lo, hi), rng.randint(lo, hi)


def colours(rng, k, exclude=(0,)):
    """k distinct colours not in exclude."""
    return rng.sample([c for c in COLOURS if c not in exclude], k)


def cells(g, pred):
    return [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if pred(v)]


def bg_colour(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return max(cnt.items(), key=lambda kv: kv[1])[0]


def components(g, pred, conn8=False, bg=None):
    """Connected components of cells where pred(value) (same-colour unless pred says otherwise). Returns
    list of lists of (r, c). pred may be a colour int."""
    if isinstance(pred, int):
        col = pred; pred = lambda v: v == col
    H, W = dims(g)
    seen, out = set(), []
    nb = [(-1, 0), (1, 0), (0, -1), (0, 1)] + ([(-1, -1), (-1, 1), (1, -1), (1, 1)] if conn8 else [])
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or not pred(g[r][c]):
                continue
            comp, st = [], [(r, c)]
            seen.add((r, c))
            while st:
                y, x = st.pop(); comp.append((y, x))
                for dy, dx in nb:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen and pred(g[ny][nx]) and g[ny][nx] == g[y][x]:
                        seen.add((ny, nx)); st.append((ny, nx))
            out.append(comp)
    return out


def objects(g, bg=None, conn8=True):
    """Same-colour components of every non-background colour."""
    bg = bg_colour(g) if bg is None else bg
    return components(g, lambda v: v != bg, conn8=conn8)


def bbox(cells_):
    rs = [r for r, _ in cells_]; cs = [c for _, c in cells_]
    return min(rs), min(cs), max(rs), max(cs)


def crop(g, r0, c0, r1, c1):
    return [row[c0:c1 + 1] for row in g[r0:r1 + 1]]


def paste(g, sub, r0, c0, transparent=None):
    H, W = dims(g)
    for r, row in enumerate(sub):
        for c, v in enumerate(row):
            if transparent is not None and v == transparent:
                continue
            if 0 <= r0 + r < H and 0 <= c0 + c < W:
                g[r0 + r][c0 + c] = v
    return g


def flood(g, r, c, new, conn8=False):
    H, W = dims(g); old = g[r][c]
    if old == new:
        return g
    st = [(r, c)]
    while st:
        y, x = st.pop()
        if 0 <= y < H and 0 <= x < W and g[y][x] == old:
            g[y][x] = new
            st += [(y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)]
            if conn8:
                st += [(y - 1, x - 1), (y - 1, x + 1), (y + 1, x - 1), (y + 1, x + 1)]
    return g


def rot90(g):
    return [list(r) for r in zip(*g[::-1])]


def flip_h(g):
    return [r[::-1] for r in g]


def flip_v(g):
    return g[::-1]


def transpose(g):
    return [list(r) for r in zip(*g)]


def random_shape(rng, n, conn8=False):
    """A random connected set of n cells, normalised to origin. Returns list of (r, c)."""
    cells_ = {(0, 0)}
    nb = [(-1, 0), (1, 0), (0, -1), (0, 1)] + ([(-1, -1), (-1, 1), (1, -1), (1, 1)] if conn8 else [])
    while len(cells_) < n:
        y, x = rng.choice(sorted(cells_)); dy, dx = rng.choice(nb)
        cells_.add((y + dy, x + dx))
    r0 = min(r for r, _ in cells_); c0 = min(c for _, c in cells_)
    return sorted((r - r0, c - c0) for r, c in cells_)


def place_shapes(rng, g, shapes, colours_, margin=1, tries=200, bg=0):
    """Stamp shapes (lists of (r,c)) at random non-overlapping spots with `margin` empty cells around each.
    Returns list of (r0, c0) or None if it could not fit them all."""
    H, W = dims(g)
    taken, pos = set(), []
    for sh, col in zip(shapes, colours_):
        h = max(r for r, _ in sh) + 1; w = max(c for _, c in sh) + 1
        if h > H or w > W:
            return None
        for _ in range(tries):
            r0, c0 = rng.randint(0, H - h), rng.randint(0, W - w)
            foot = {(r0 + r + dr, c0 + c + dc) for r, c in sh for dr in range(-margin, margin + 1) for dc in range(-margin, margin + 1)}
            if not (foot & taken):
                taken |= foot
                for r, c in sh:
                    g[r0 + r][c0 + c] = col
                pos.append((r0, c0))
                break
        else:
            return None
    return pos


def sprinkle(rng, g, k, colour, bg=0):
    """k random background cells set to colour (fewer if the grid fills)."""
    H, W = dims(g)
    free = [(r, c) for r in range(H) for c in range(W) if g[r][c] == bg]
    for r, c in rng.sample(free, min(k, len(free))):
        g[r][c] = colour
    return g


def rect(g, r0, c0, r1, c1, colour, fill=True):
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if fill or r in (r0, r1) or c in (c0, c1):
                g[r][c] = colour
    return g


def counts(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return cnt
