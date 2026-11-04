# b022_scaling.py -- SCALE AND RESOLUTION: downscale by any/all/majority/top-left, upscale into patterned blocks,
# scale factors between panels, low-res map over high-res texture, blur/pixelate, corrupted zooms, nested scales,
# stretch/squash by a given factor, one object at several scales.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

SEP = 5                                           # grey: separators, frames, markers
PAL = [c for c in COLOURS if c != SEP]            # colours that never collide with grey


def _span(rng, lo, hi, k=1):
    """A length in [lo, hi] divisible by k; ~40% of the time drawn from the 21-30 band when hi allows."""
    if hi >= 21 and rng.random() < 0.4:
        lo = max(lo, 21)
    return rng.choice([n for n in range(lo, hi + 1) if n % k == 0])


def _noise(rng, h, w, cols, density):
    return [[rng.choice(cols) if rng.random() < density else 0 for _ in range(w)] for _ in range(h)]


def _mixed(g):
    return len({v for row in g for v in row}) >= 2


def _up(g, k):
    return [[v for v in row for _ in range(k)] for row in g for _ in range(k)]


def _up_hw(g, kh, kw):
    return [[v for v in row for _ in range(kw)] for row in g for _ in range(kh)]


def _down(g, k, fn):
    """Each k by k block becomes fn(list of its values)."""
    h, w = dims(g)
    return [[fn([g[r][c] for r in range(i * k, i * k + k) for c in range(j * k, j * k + k)])
             for j in range(w // k)] for i in range(h // k)]


def _mode(vals):
    cnt = {}
    for v in vals:
        cnt[v] = cnt.get(v, 0) + 1
    return max(cnt.items(), key=lambda kv: (kv[1], -kv[0]))[0]


def _split(g, sep=SEP):
    """Rows above and below the first full row of sep."""
    r = next(i for i, row in enumerate(g) if all(v == sep for v in row))
    return g[:r], g[r + 1:]


def _pad(g, W):
    return [row + [0] * (W - len(row)) for row in g]


def _pattern_up(g, mask, k):
    """Each coloured cell becomes a k by k block carrying the cell's colour on mask cells."""
    h, w = dims(g); out = blank(h * k, w * k)
    for r in range(h):
        for c in range(w):
            if g[r][c]:
                for dr, dc in mask:
                    out[r * k + dr][c * k + dc] = g[r][c]
    return out


# ---------------------------------------------------------------- downscale -----------------------------------
# 1 any
def gi_any2(rng):
    h, w = _span(rng, 4, 30, 2), _span(rng, 4, 30, 2)
    g = _noise(rng, h, w, [rng.choice(COLOURS)], rng.uniform(0.12, 0.3))
    return g if _mixed(g) else None
def tf_any2(g):
    col = max(v for row in g for v in row)
    return _down(g, 2, lambda b: col if any(b) else 0)
rule("downscale_2x2_any_coloured", "The grid is cut into 2 by 2 blocks; each block becomes one cell, coloured if any cell in the block is coloured.", gi_any2, tf_any2)


# 2 all
def gi_all3(rng):
    h, w = _span(rng, 6, 30, 3), _span(rng, 6, 30, 3); col = rng.choice(COLOURS)
    small = _noise(rng, h // 3, w // 3, [col], rng.uniform(0.3, 0.6)); g = _up(small, 3)
    for i in range(h // 3):
        for j in range(w // 3):
            if small[i][j] and rng.random() < 0.3:
                g[i * 3 + rng.randrange(3)][j * 3 + rng.randrange(3)] = 0      # a solid block loses a cell
            elif not small[i][j] and rng.random() < 0.5:
                for _ in range(rng.randint(1, 7)):
                    g[i * 3 + rng.randrange(3)][j * 3 + rng.randrange(3)] = col  # an empty block gains some
    return g if _mixed(g) else None
def tf_all3(g):
    col = max(v for row in g for v in row)
    return _down(g, 3, lambda b: col if all(b) else 0)
rule("downscale_3x3_all_coloured", "The grid is cut into 3 by 3 blocks; each block becomes one cell, coloured only if every cell of the block is coloured.", gi_all3, tf_all3)


# 3 majority coloured, colour = dominant
def gi_maj3(rng):
    h, w = _span(rng, 6, 30, 3), _span(rng, 6, 30, 3); cols = colours(rng, rng.randint(2, 4))
    g = blank(h, w)
    for i in range(h // 3):
        for j in range(w // 3):
            if rng.random() < 0.5:
                main = rng.choice(cols); n = rng.randint(5, 9); spots = rng.sample(range(9), 9)
                for t in spots[:n]: g[i * 3 + t // 3][j * 3 + t % 3] = main
                for t in spots[n:]: g[i * 3 + t // 3][j * 3 + t % 3] = rng.choice([0] + [c for c in cols if c != main])
            else:
                for t in rng.sample(range(9), rng.randint(0, 4)): g[i * 3 + t // 3][j * 3 + t % 3] = rng.choice(cols)
    return g if _mixed(g) else None
def tf_maj3(g):
    return _down(g, 3, lambda b: _mode([v for v in b if v]) if sum(1 for v in b if v) >= 5 else 0)
# downscale_3x3_majority_dominant_colour dropped 2026-10-12 (trio review: behavioural duplicate or one global operation)
# 4 top-left
def gi_tl3(rng):
    h, w = _span(rng, 6, 30, 3), _span(rng, 6, 30, 3)
    g = _noise(rng, h, w, colours(rng, rng.randint(2, 5)), rng.uniform(0.4, 0.8))
    out = tf_tl3(g)
    return g if _mixed(out) else None
def tf_tl3(g):
    return _down(g, 3, lambda b: b[0])
rule("downscale_3x3_top_left_cell", "The grid is cut into 3 by 3 blocks; each block is replaced by a single cell carrying its top-left cell's colour.", gi_tl3, tf_tl3)


# 6 distinct colour count per block
def gi_dist3(rng):
    h, w = _span(rng, 6, 30, 3), _span(rng, 6, 30, 3)
    g = _noise(rng, h, w, colours(rng, rng.randint(2, 6)), rng.uniform(0.2, 0.6))
    return g if _mixed(tf_dist3(g)) else None
def tf_dist3(g):
    return _down(g, 3, lambda b: len({v for v in b if v}))
rule("downscale_3x3_distinct_colour_count", "The grid is cut into 3 by 3 blocks; each block becomes one cell whose value is the number of different colours in that block.", gi_dist3, tf_dist3, digits=True)


# 7 factor from key digit
def gi_keydown(rng):
    n = rng.randint(2, 4); w = _span(rng, 2 * n, 30, n); h = _span(rng, 2 * n, 28 - 2, n)
    field = _noise(rng, h, w, rng.sample(PAL, rng.randint(2, 4)), rng.uniform(0.4, 0.8))
    g = [[n] + [0] * (w - 1), [SEP] * w] + field
    return g if _mixed(tf_keydown(g)) else None
def tf_keydown(g):
    n = g[0][0]; field = g[2:]
    return _down(field, n, lambda b: b[0])
rule("key_digit_sets_downscale_factor", "The digit in the top-left corner is n; the field below the grey line is shrunk by n, each n by n block keeping only its top-left cell.", gi_keydown, tf_keydown, digits=True)


# 8 uniform block -> colour, mixed block -> grey
def gi_unif(rng):
    h, w = _span(rng, 6, 30, 3), _span(rng, 6, 30, 3); cols = rng.sample(PAL, rng.randint(2, 4)); g = blank(h, w)
    for i in range(h // 3):
        for j in range(w // 3):
            if rng.random() < 0.6:
                rect(g, i * 3, j * 3, i * 3 + 2, j * 3 + 2, rng.choice([0] + cols))
            else:
                while len({g[i * 3 + t // 3][j * 3 + t % 3] for t in range(9)}) < 2:
                    for t in range(9): g[i * 3 + t // 3][j * 3 + t % 3] = rng.choice([0] + cols)
    return g if _mixed(tf_unif(g)) and any(SEP in row for row in tf_unif(g)) else None
def tf_unif(g):
    return _down(g, 3, lambda b: b[0] if len(set(b)) == 1 else SEP)
rule("downscale_3x3_uniform_else_grey", "The grid is cut into 3 by 3 blocks; a block of one single colour becomes a cell of that colour, a block of mixed colours becomes a grey cell.", gi_unif, tf_unif)


# 9 rows only: each band of 3 rows collapses to one row, coloured where any of the three is
def gi_rowband(rng):
    h, w = _span(rng, 6, 30, 3), _span(rng, 4, 30); col = rng.choice(COLOURS)
    g = _noise(rng, h, w, [col], rng.uniform(0.1, 0.25))
    return g if _mixed(tf_rowband(g)) else None
def tf_rowband(g):
    h, w = dims(g); col = max(v for row in g for v in row)
    return [[col if any(g[r][c] for r in range(i * 3, i * 3 + 3)) else 0 for c in range(w)] for i in range(h // 3)]
rule("collapse_row_triples_any_coloured", "Every three consecutive rows collapse into one row that is coloured wherever any of the three rows was coloured; the width is unchanged.", gi_rowband, tf_rowband)


# ---------------------------------------------------------------- upscale into patterns ----------------------
RING = [(r, c) for r in range(3) for c in range(3) if (r, c) != (1, 1)]
CROSS = [(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)]
DIAG = [(0, 0), (1, 1), (2, 2)]
XX = [(0, 0), (1, 1), (2, 2), (0, 2), (2, 0)]
CORN = [(0, 0), (0, 2), (2, 0), (2, 2)]


def _gi_small(rng, lo=3, hi=10, dens=(0.25, 0.5), cols=None):
    h, w = rng.randint(lo, hi), rng.randint(lo, hi)
    g = _noise(rng, h, w, cols or colours(rng, rng.randint(1, 4)), rng.uniform(*dens))
    return g if _mixed(g) else None


def gi_pat(rng): return _gi_small(rng)
rule("upscale_3x_cells_to_rings", "Every coloured cell becomes a 3 by 3 hollow ring of its colour (centre left empty); empty cells become empty 3 by 3 blocks.", gi_pat, lambda g: _pattern_up(g, RING, 3))
rule("upscale_3x_cells_to_crosses", "Every coloured cell becomes a 3 by 3 plus sign of its colour; empty cells become empty 3 by 3 blocks.", gi_pat, lambda g: _pattern_up(g, CROSS, 3))
rule("upscale_3x_cells_to_diagonals", "Every coloured cell becomes a 3 by 3 block holding only a top-left to bottom-right diagonal of its colour; empty cells become empty blocks.", gi_pat, lambda g: _pattern_up(g, DIAG, 3))
rule("upscale_3x_cells_to_x_marks", "Every coloured cell becomes a 3 by 3 X (both diagonals) of its colour; empty cells become empty 3 by 3 blocks.", gi_pat, lambda g: _pattern_up(g, XX, 3))
rule("upscale_3x_cells_to_corner_dots", "Every coloured cell becomes a 3 by 3 block with only its four corners in the cell's colour; empty cells become empty blocks.", gi_pat, lambda g: _pattern_up(g, CORN, 3))


def gi_chk(rng): return _gi_small(rng, 3, 15)
rule("upscale_2x_cells_to_checker", "Every coloured cell becomes a 2 by 2 block with its top-left and bottom-right cells in the cell's colour and the other two empty.", gi_chk, lambda g: _pattern_up(g, [(0, 0), (1, 1)], 2))


# 16 shadow block
def gi_shadow(rng): return _gi_small(rng, 3, 15, cols=rng.sample(PAL, rng.randint(1, 4)))
def tf_shadow(g):
    out = _up(g, 2); h, w = dims(g)
    for r in range(h):
        for c in range(w):
            if g[r][c]: out[2 * r + 1][2 * c + 1] = SEP
    return out
rule("upscale_2x_grey_shadow_corner", "Every cell becomes a 2 by 2 block of its colour, and each coloured block has its bottom-right cell turned grey.", gi_shadow, tf_shadow)


# 17 pattern given by a key
def gi_keypat(rng):
    h, w = rng.randint(3, 8), rng.randint(3, 10)
    mask = sorted(rng.sample([(r, c) for r in range(3) for c in range(3)], rng.randint(3, 7)))
    key = blank(3, w)
    for r, c in mask: key[r][c] = SEP
    field = _noise(rng, h, w, rng.sample(PAL, rng.randint(1, 3)), rng.uniform(0.3, 0.55))
    return key + [[SEP] * w] + field if _mixed(field) else None
def tf_keypat(g):
    mask = [(r, c) for r in range(3) for c in range(3) if g[r][c] == SEP]
    return _pattern_up(g[4:], mask, 3)
rule("key_pattern_stamps_each_cell_3x", "The grey 3 by 3 pattern in the top-left corner is a stamp: each coloured cell below the grey line becomes a 3 by 3 block carrying that pattern in the cell's colour.", gi_keypat, tf_keypat)


# 18 upscale 2x then hollow
def gi_hollow(rng):
    h, w = size(rng, 4, 15); g = blank(h, w); k = rng.randint(1, 4)
    shapes = [random_shape(rng, rng.randint(3, 9)) for _ in range(k)]
    if place_shapes(rng, g, shapes, colours(rng, k), margin=1) is None: return None
    return g
def tf_hollow(g):
    big = _up(g, 2); H, W = dims(big); out = copy(big)
    for r in range(H):
        for c in range(W):
            v = big[r][c]
            if v and all(0 <= r + dr < H and 0 <= c + dc < W and big[r + dr][c + dc] == v for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[r][c] = 0
    return out
rule("upscale_2x_then_hollow", "Every object is enlarged to twice its size and then hollowed out: enlarged cells with same-coloured neighbours on all four sides become empty.", gi_hollow, tf_hollow)


# ---------------------------------------------------------------- scale factor between panels ---------------
def _motif(rng, h, w, cols, lo=0.35, hi=0.7):
    for _ in range(50):
        m = _noise(rng, h, w, cols, rng.uniform(lo, hi))
        if _mixed(m) and all(any(row) for row in m) and all(any(m[r][c] for r in range(h)) for c in range(w)):
            return m
    return None


# 19 motif + empty panel -> scaled motif
def gi_fillpanel(rng):
    k = rng.randint(2, 5); h, w = rng.randint(2, 6), rng.randint(2, 6)
    if k * h > 24 or k * w > 30: return None
    m = _motif(rng, h, w, rng.sample(PAL, rng.randint(1, 3)))
    if m is None: return None
    return _pad(m, k * w) + [[SEP] * (k * w)] + blank(k * h, k * w)
def tf_fillpanel(g):
    top, bot = _split(g); h = len(top); k = len(bot) // h; w = len(g[0]) // k
    return _up([row[:w] for row in top], k)
rule("scale_motif_to_empty_panel_size", "The small motif above the grey line is enlarged by whatever whole factor makes it exactly fill the empty panel below; output the filled panel.", gi_fillpanel, tf_fillpanel)


# 20 large panel + empty frame -> shrunk motif
def gi_shrinkframe(rng):
    k = rng.randint(2, 5); h, w = rng.randint(2, 6), rng.randint(2, 6)
    if k * h + h + 3 > 30 or k * w > 30 or w + 2 > k * w: return None
    m = _motif(rng, h, w, rng.sample(PAL, rng.randint(1, 3)))
    if m is None: return None
    frame = blank(h + 2, k * w); rect(frame, 0, 0, h + 1, w + 1, SEP, fill=False)
    return _up(m, k) + [[SEP] * (k * w)] + frame
def tf_shrinkframe(g):
    top, bot = _split(g); r0, c0, r1, c1 = bbox(cells(bot, lambda v: v == SEP))
    h = r1 - r0 - 1; k = len(top) // h
    return _down(top, k, lambda b: b[0])
rule("shrink_panel_to_fit_grey_frame", "The large picture above the grey line is shrunk by whatever whole factor makes it exactly fit inside the empty grey frame below; output the shrunk picture.", gi_shrinkframe, tf_shrinkframe)


# 21 factor -> bar
def _two_panels(rng, cols_n):
    k = rng.randint(2, 6); h, w = rng.randint(2, 5), rng.randint(2, 5)
    if h + 1 + k * h > 30 or k * w > 30: return None
    m = _motif(rng, h, w, rng.sample(PAL, cols_n))
    if m is None: return None
    return _pad(m, k * w) + [[SEP] * (k * w)] + _up(m, k)
def gi_bar(rng): return _two_panels(rng, 1)
def tf_bar(g):
    top, bot = _split(g); k = len(bot) // len(top); col = max(v for row in top for v in row)
    return [[col] * k + [0]]
rule("scale_factor_between_panels_to_bar", "The picture below the grey line is an enlarged copy of the one above; output a single row holding a bar, in the picture's colour, as long as the enlargement factor, followed by one empty cell.", gi_bar, tf_bar)


# 23 scaled motif fills empty frame inside the whole grid
def gi_framefill(rng):
    H, W = _span(rng, 10, 30), _span(rng, 10, 30); g = blank(H, W)
    k = rng.randint(2, 4); h, w = rng.randint(2, 4), rng.randint(2, 4)
    fh, fw = k * h + 2, k * w + 2
    if fh > H or fw + w + 1 > W: return None
    m = _motif(rng, h, w, rng.sample(PAL, rng.randint(1, 3)))
    if m is None: return None
    if rng.random() < 0.5:
        mr, mc = rng.randint(0, H - h), rng.randint(0, W - fw - w - 1); fr, fc = rng.randint(0, H - fh), rng.randint(mc + w + 1, W - fw)
    else:
        fr, fc = rng.randint(0, H - fh), rng.randint(0, W - fw - w - 1); mr, mc = rng.randint(0, H - h), rng.randint(fc + fw + 1, W - w)
    paste(g, m, mr, mc); rect(g, fr, fc, fr + fh - 1, fc + fw - 1, SEP, fill=False)
    return g
def tf_framefill(g):
    out = copy(g); r0, c0, r1, c1 = bbox(cells(g, lambda v: v == SEP))
    mr0, mc0, mr1, mc1 = bbox(cells(g, lambda v: v not in (0, SEP)))
    m = crop(g, mr0, mc0, mr1, mc1); k = (r1 - r0 - 1) // len(m)
    return paste(out, _up(m, k), r0 + 1, c0 + 1)
rule("motif_enlarged_into_empty_grey_frame", "The empty grey frame is filled with the small motif elsewhere in the grid, enlarged by the whole factor that makes it fit exactly; the motif itself stays.", gi_framefill, tf_framefill)


# ---------------------------------------------------------------- map and texture ----------------------------
def _map_texture(rng, map_cols, tex_cols, tex_density):
    k = rng.randint(2, 4); h, w = rng.randint(2, 6), rng.randint(2, 7)
    if h + 1 + k * h > 30 or k * w > 30: return None
    m = _noise(rng, h, w, map_cols, rng.uniform(0.35, 0.65))
    if not _mixed(m): return None
    tex = _noise(rng, k * h, k * w, tex_cols, tex_density)
    return _pad(m, k * w) + [[SEP] * (k * w)] + tex


def gi_maptex(rng): return _map_texture(rng, [rng.choice(PAL)], rng.sample(PAL, rng.randint(2, 4)), 1.0)
def tf_maptex(g):
    top, bot = _split(g); h = len(top); k = len(bot) // h; w = len(g[0]) // k
    return [[bot[r][c] if top[r // k][c // k] else 0 for c in range(len(bot[0]))] for r in range(len(bot))]
rule("map_masks_texture_blocks", "The small map above the grey line and the large texture below share a scale; output the texture, kept only in blocks whose map cell is coloured and emptied elsewhere.", gi_maptex, tf_maptex)


def gi_mapcol(rng): return _map_texture(rng, rng.sample(PAL, rng.randint(2, 4)), [rng.choice(PAL)], rng.uniform(0.5, 0.8))
def tf_mapcol(g):
    top, bot = _split(g); h = len(top); k = len(bot) // h; w = len(g[0]) // k
    out = [[(top[r // k][c // k] if bot[r][c] else 0) for c in range(len(bot[0]))] for r in range(len(bot))]
    return out if _mixed(out) else None
rule("map_colours_texture_blocks", "The texture below the grey line is repainted block by block in the colour of the matching map cell above the line; blocks under an empty map cell are wiped.", gi_mapcol, tf_mapcol)


# ---------------------------------------------------------------- blur and pixelate --------------------------
def _upnoisy(rng, h, w, k, cols, per_block, dens=(0.4, 0.9)):
    """A k-zoomed small grid with up to per_block cells per block flipped to other values. Returns (small, big)."""
    small = _noise(rng, h // k, w // k, cols, rng.uniform(*dens)); big = _up(small, k); n = 0
    for i in range(h // k):
        for j in range(w // k):
            if rng.random() < 0.5:
                for t in rng.sample(range(k * k), rng.randint(1, per_block)):
                    r, c = i * k + t // k, j * k + t % k
                    big[r][c] = rng.choice([v for v in [0] + cols if v != small[i][j]]); n += 1
    return small, big, n


def gi_pix3(rng):
    h, w = _span(rng, 6, 30, 3), _span(rng, 6, 30, 3)
    small, big, n = _upnoisy(rng, h, w, 3, colours(rng, rng.randint(2, 4)), 3)
    return big if n and _mixed(big) else None
def tf_pix3(g):
    return _up(_down(g, 3, _mode), 3)
rule("pixelate_3x3_blocks_dominant", "Each 3 by 3 block is filled entirely with the colour that occurs most often in it (empty counts); the grid keeps its size.", gi_pix3, tf_pix3)


def gi_blurcol(rng):
    h, w = _span(rng, 6, 30, 3), _span(rng, 4, 30); cols = colours(rng, rng.randint(2, 4))
    small = _noise(rng, h // 3, w, cols, rng.uniform(0.4, 0.8)); g = _up_hw(small, 3, 1); n = 0
    for i in range(h // 3):
        for c in range(w):
            if rng.random() < 0.3:
                g[i * 3 + rng.randrange(3)][c] = rng.choice([v for v in [0] + cols if v != small[i][c]]); n += 1
    return g if n and _mixed(g) else None
def tf_blurcol(g):
    h, w = dims(g); out = copy(g)
    for i in range(h // 3):
        for c in range(w):
            v = _mode([g[i * 3 + t][c] for t in range(3)])
            for t in range(3): out[i * 3 + t][c] = v
    return out
rule("blur_column_triples_to_majority", "Within every band of three rows, each column's three cells all take the colour that appears in at least two of them.", gi_blurcol, tf_blurcol)


def gi_pixrect(rng):
    H, W = _span(rng, 8, 30), _span(rng, 8, 30); cols = rng.sample(PAL, rng.randint(2, 4))
    g = _noise(rng, H, W, cols, rng.uniform(0.3, 0.6))
    ih, iw = rng.randrange(4, min(H - 2, 20) + 1, 2), rng.randrange(4, min(W - 2, 20) + 1, 2)
    r0, c0 = rng.randint(0, H - ih - 2), rng.randint(0, W - iw - 2)
    rect(g, r0, c0, r0 + ih + 1, c0 + iw + 1, SEP, fill=False)
    small, big, n = _upnoisy(rng, ih, iw, 2, cols, 1)
    paste(g, big, r0 + 1, c0 + 1)
    return g if n else None
def tf_pixrect(g):
    out = copy(g); r0, c0, r1, c1 = bbox(cells(g, lambda v: v == SEP))
    inner = crop(g, r0 + 1, c0 + 1, r1 - 1, c1 - 1)
    return paste(out, _up(_down(inner, 2, _mode), 2), r0 + 1, c0 + 1)
rule("pixelate_inside_grey_rectangle", "Only inside the grey rectangle, each 2 by 2 block is filled with its most common colour; everything outside the rectangle is unchanged.", gi_pixrect, tf_pixrect)


# ---------------------------------------------------------------- corrupted zooms ----------------------------
def _corrupt(rng, k, lo, hi, cols=None):
    h, w = rng.randint(lo, hi), rng.randint(lo, hi)
    small = _motif(rng, h, w, cols or colours(rng, rng.randint(2, 4)), 0.4, 0.75)
    if small is None: return None
    big = _up(small, k); r, c = rng.randrange(k * h), rng.randrange(k * w)
    big[r][c] = rng.choice([v for v in [0] + COLOURS if v != big[r][c] and v != SEP])
    return big


def gi_fix2s(rng): return _corrupt(rng, 2, 3, 12)
def tf_fix2s(g): return _down(g, 2, _mode)
rule("zoom_2x_one_wrong_cell_to_small", "The grid is a 2 by 2 enlargement of a small picture with one cell painted wrong; output the small picture with the error corrected by the other three cells of its block.", gi_fix2s, tf_fix2s)


def gi_fix2l(rng): return _corrupt(rng, 2, 3, 12)
def tf_fix2l(g): return _up(_down(g, 2, _mode), 2)
rule("zoom_2x_one_wrong_cell_repaired", "The grid is a 2 by 2 enlargement of a picture with one cell painted wrong; repaint that cell to match the other three cells of its block.", gi_fix2l, tf_fix2l)


def gi_mark3(rng): return _corrupt(rng, 3, 3, 9, rng.sample(PAL, rng.randint(2, 4)))
def tf_mark3(g): return _down(g, 3, lambda b: b[0] if len(set(b)) == 1 else SEP)
# zoom_3x_corrupted_block_marked_grey dropped 2026-10-12 (trio review: behavioural duplicate or one global operation)
# ---------------------------------------------------------------- nested scales ------------------------------
def gi_self(rng):
    h, w = rng.randint(2, 5), rng.randint(2, 5)
    return _motif(rng, h, w, [rng.choice(COLOURS)], 0.4, 0.7)
def tf_self(g):
    h, w = dims(g); out = blank(h * h, w * w)
    for r in range(h):
        for c in range(w):
            if g[r][c]: paste(out, g, r * h, c * w)
    return out
rule("shape_drawn_with_copies_of_itself", "Each coloured cell of the shape is replaced by a whole copy of the shape and each empty cell by an empty block, so the shape is drawn out of itself.", gi_self, tf_self)


def gi_selfcol(rng):
    h, w = rng.randint(2, 5), rng.randint(2, 5)
    return _motif(rng, h, w, colours(rng, rng.randint(2, 4)), 0.4, 0.7)
def tf_selfcol(g):
    h, w = dims(g); out = blank(h * h, w * w)
    for r in range(h):
        for c in range(w):
            if g[r][c]:
                for rr in range(h):
                    for cc in range(w):
                        if g[rr][cc]: out[r * h + rr][c * w + cc] = g[r][c]
    return out
rule("shape_of_self_copies_in_cell_colours", "Each coloured cell is replaced by a copy of the shape's silhouette painted entirely in that cell's colour; empty cells become empty blocks.", gi_selfcol, tf_selfcol)


# ---------------------------------------------------------------- stretch and squash -------------------------
def gi_hstretch(rng):
    k = rng.randint(2, 5); w = rng.randint(max(3, k), 30 // k); h = rng.randint(3, 27)
    field = _noise(rng, h, w, rng.sample(PAL, rng.randint(1, 4)), rng.uniform(0.3, 0.7))
    return [[SEP] * k + [0] * (w - k), [SEP] * w] + field if _mixed(field) else None
def tf_hstretch(g):
    k = sum(1 for v in g[0] if v == SEP)
    return _up_hw(g[2:], 1, k)
rule("grey_bar_length_stretches_width", "The grey bar in the top row has length k; the field below the grey line is stretched sideways so every cell becomes k cells wide, height unchanged.", gi_hstretch, tf_hstretch)


def gi_vstretch(rng):
    k = rng.randint(2, 5); h = rng.randint(max(3, k), 30 // k); w = rng.randint(3, 27)
    field = _noise(rng, h, w, rng.sample(PAL, rng.randint(1, 4)), rng.uniform(0.3, 0.7))
    if not _mixed(field): return None
    return [[SEP if r < k else 0, SEP] + field[r] for r in range(h)]
def tf_vstretch(g):
    k = sum(1 for row in g if row[0] == SEP)
    return _up_hw([row[2:] for row in g], k, 1)
rule("grey_column_marks_stretch_height", "The grey cells at the top of the first column number k; the field right of the grey divider is stretched downward so every cell becomes k cells tall, width unchanged.", gi_vstretch, tf_vstretch)


def gi_sq(rng):
    h, w = _span(rng, 3, 30), _span(rng, 3, 30)
    g = _noise(rng, h, w, colours(rng, rng.randint(2, 5)), rng.uniform(0.3, 0.7))
    return g if _mixed(g[::2]) and _mixed([row[::2] for row in g]) and _mixed([row[::2] for row in g[::2]]) else None
rule("squash_height_drop_every_other_row", "Every second row (the second, fourth, sixth...) is removed, squashing the grid to about half its height.", gi_sq, lambda g: g[::2])
rule("squash_width_drop_every_other_column", "Every second column (the second, fourth, sixth...) is removed, squashing the grid to about half its width.", gi_sq, lambda g: [row[::2] for row in g])
rule("squash_both_keep_odd_rows_and_columns", "Only the first, third, fifth... rows and columns are kept, shrinking the grid to about half its size in both directions.", gi_sq, lambda g: [row[::2] for row in g[::2]])


# ---------------------------------------------------------------- one object at several scales ---------------
def _lone(rng, maxside):
    H, W = _span(rng, 6, 30), _span(rng, 6, 30); g = blank(H, W)
    for _ in range(20):
        sh = random_shape(rng, rng.randint(3, 9))
        if max(r for r, _ in sh) < maxside and max(c for _, c in sh) < maxside: break
    else:
        return None
    if place_shapes(rng, g, [sh], [rng.choice(COLOURS)], margin=0) is None: return None
    return g
def _obj(g):
    o = cells(g, lambda v: v != 0)
    return crop(g, *bbox(o))


def gi_row123(rng): return _lone(rng, 4)
def tf_row123(g):
    m = _obj(g); h, w = dims(m); out = blank(3 * h, 6 * w + 2)
    paste(out, m, 0, 0); paste(out, _up(m, 2), 0, w + 1); paste(out, _up(m, 3), 0, 3 * w + 2)
    return out
rule("object_at_1x_2x_3x_in_a_row", "Cut out the single object and lay it out three times side by side, at its own size, doubled and tripled, top-aligned with one empty column between copies.", gi_row123, tf_row123)


def gi_col123(rng): return _lone(rng, 4)
def tf_col123(g):
    m = _obj(g); h, w = dims(m); out = blank(6 * h + 2, 3 * w)
    paste(out, m, 0, 0); paste(out, _up(m, 2), h + 1, 0); paste(out, _up(m, 3), 3 * h + 2, 0)
    return out
rule("object_at_1x_2x_3x_stacked", "Cut out the single object and stack it three times, at its own size, doubled and tripled, left-aligned with one empty row between copies.", gi_col123, tf_col123)


def gi_mip(rng):
    h, w = _span(rng, 4, 30, 2), _span(rng, 4, 18, 2)
    g = _noise(rng, h, w, [rng.choice(COLOURS)], rng.uniform(0.15, 0.35))
    return g if _mixed(g) and _mixed(tf_any2(g)) else None
def tf_mip(g):
    h, w = dims(g); out = blank(h, w + 1 + w // 2)
    paste(out, g, 0, 0); paste(out, tf_any2(g), 0, w + 1)
    return out
rule("grid_beside_its_half_scale_copy", "Output the grid followed, after one empty column, by a half-size copy in which each 2 by 2 block became one cell coloured if any of its cells was.", gi_mip, tf_mip)


def gi_objscale(rng):
    H, W = _span(rng, 8, 30), _span(rng, 8, 30); g = blank(H, W); k = rng.randint(2, 4)
    shapes = [random_shape(rng, rng.randint(3, 6)) for _ in range(k)]; cols = colours(rng, k)
    shapes = [sh for sh in shapes if max(r for r, _ in sh) < 3 and max(c for _, c in sh) < 3]
    if len(shapes) < 2 or place_shapes(rng, g, shapes, cols[:len(shapes)], margin=1) is None: return None
    return g if len(objects(g, 0)) == len(shapes) else None
def tf_objscale(g):
    obs = sorted(objects(g, 0), key=lambda o: min(c for _, c in o)); tiles = []
    for o in obs:
        m = crop(g, *bbox(o)); k = len(o)
        if len(m) * k > 30 or len(m[0]) * k > 30: return None
        tiles.append(_up(m, k))
    H = max(len(t) for t in tiles); W = sum(len(t[0]) for t in tiles) + len(tiles) - 1; out = blank(H, W); c = 0
    for t in tiles:
        paste(out, t, 0, c); c += len(t[0]) + 1
    return out
rule("objects_scaled_by_cell_count_in_a_row", "Each object is enlarged by a factor equal to its number of cells; the enlarged objects are laid out left to right in the order of their original positions, top-aligned, one empty column apart.", gi_objscale, tf_objscale)
