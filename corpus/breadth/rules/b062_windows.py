# b062_windows.py -- sliding windows and local statistics with non-trivial output.
# Window size/stride/tie-breaks are stated in each rule's description (one sentence, applicable by hand).
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *


def wsize(rng, lo=10, hi=20, p_big=0.35):
    """Grid dims: ~35% of draws put both sides at 21-30 (AUTHORING.md's quarter-large-input floor),
    else the rule's own small/medium range. Per-cell density generators scale with area automatically."""
    if rng.random() < p_big:
        return rng.randint(21, 30), rng.randint(21, 30)
    return size(rng, lo, hi)


def bdim(rng, k, lo, hi, p_big=0.35):
    """One block-grid dimension (rows or cols) of a grid built from kxk blocks: ~35% of the time the
    side lands in 21-30 cells (rows/cols chosen so rows*k, cols*k fall in that band), else the small range."""
    if rng.random() < p_big:
        lo_b, hi_b = -(-21 // k), 30 // k
        return rng.randint(lo_b, hi_b)
    return rng.randint(lo, hi)


def _scene(rng, lo=10, hi=20, density=0.2, exclude0=True):
    h, w = wsize(rng, lo, hi)
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < density:
                g[r][c] = rng.choice(COLOURS)
    return g


def _sprinkle_scene(rng, lo=10, hi=24, k_lo=None, k_hi=None):
    h, w = wsize(rng, lo, hi)
    g = blank(h, w)
    k_lo = k_lo or (h * w // 8)
    k_hi = k_hi or (h * w // 3)
    for _ in range(rng.randint(k_lo, k_hi)):
        g[rng.randrange(h)][rng.randrange(w)] = rng.choice(COLOURS)
    return g


# 1 -- the 3x3 window (stride 1) with the most coloured cells is outlined in colour 5; ties go to the
#      window whose top-left corner is topmost, then leftmost.
def gi_densest3(rng):
    return _sprinkle_scene(rng, 10, 20)
def tf_densest3(g):
    h, w = dims(g)
    if h < 3 or w < 3: return None
    best, bestn = None, -1
    for r in range(h - 2):
        for c in range(w - 2):
            n = sum(1 for dr in range(3) for dc in range(3) if g[r + dr][c + dc] != 0)
            if n > bestn:
                bestn, best = n, (r, c)
    out = copy(g); r, c = best
    for dr in range(3):
        for dc in range(3):
            if dr in (0, 2) or dc in (0, 2):
                if out[r + dr][c + dc] == 0: out[r + dr][c + dc] = 5
    return out
rule("outline_densest_3x3_window", "The 3x3 window (stride 1) with the most coloured cells is outlined in grey, ties going to the topmost then leftmost window.", gi_densest3, tf_densest3)


# 2 -- the 2x2 window (stride 1) with four distinct non-zero colours is filled grey; first such window
#      found scanning row-major.
def gi_fourdistinct(rng):
    h, w = wsize(rng, 10, 20); g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.35: g[r][c] = rng.choice(COLOURS)
    r0, c0 = rng.randrange(h - 1), rng.randrange(w - 1)
    cols = colours(rng, 4)
    g[r0][c0], g[r0][c0 + 1], g[r0 + 1][c0], g[r0 + 1][c0 + 1] = cols
    return g
def tf_fourdistinct(g):
    h, w = dims(g)
    for r in range(h - 1):
        for c in range(w - 1):
            vals = {g[r][c], g[r][c + 1], g[r + 1][c], g[r + 1][c + 1]}
            if 0 not in vals and len(vals) == 4:
                out = copy(g)
                for dr in range(2):
                    for dc in range(2): out[r + dr][c + dc] = 5
                return out
    return None
rule("fill_four_distinct_2x2_window", "The first 2x2 window scanning top-to-bottom, left-to-right whose four cells are four distinct non-zero colours is filled grey.", gi_fourdistinct, tf_fourdistinct)


# 3 -- every 3x3 all-same-non-zero-colour window has its centre marked with colour 5 (overwritten).
def gi_marksame(rng):
    h, w = wsize(rng, 10, 20); g = blank(h, w); col = rng.choice(COLOURS)
    k = rng.randint(2, 4)
    for _ in range(k):
        if h < 3 or w < 3: break
        r0, c0 = rng.randrange(h - 2), rng.randrange(w - 2)
        rect(g, r0, c0, r0 + 2, c0 + 2, col)
    sprinkle(rng, g, rng.randint(3, 10), rng.choice([c for c in COLOURS if c != col]))
    return g
def tf_marksame(g):
    h, w = dims(g)
    if h < 3 or w < 3: return None
    out = copy(g)
    for r in range(h - 2):
        for c in range(w - 2):
            vals = {g[r + dr][c + dc] for dr in range(3) for dc in range(3)}
            if len(vals) == 1 and 0 not in vals:
                out[r + 1][c + 1] = 5
    return out
rule("mark_uniform_3x3_centres", "Every 3x3 window (stride 1) whose nine cells are all the same non-zero colour has its centre recoloured grey.", gi_marksame, tf_marksame)


# 4 -- non-overlapping 3x3 windows (grid cropped to a multiple of 3) sorted by fill count into a row of
#      mini-panels left to right ascending, panels separated by a column of colour 5.
def gi_sortedpanels(rng):
    # output lays every panel in one row (n*4-1 wide); n>7 panels already exceeds the 30-wide output
    # cap, so this rule's panel count -- not its grid side -- is the thing that must stay small (small_ok).
    rows, cols = rng.randint(2, 3), rng.randint(2, 4)
    h, w = rows * 3, cols * 3
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.3: g[r][c] = rng.choice(COLOURS)
    counts_ = []
    for br in range(rows):
        for bc in range(cols):
            n = sum(1 for dr in range(3) for dc in range(3) if g[br * 3 + dr][bc * 3 + dc] != 0)
            counts_.append(n)
    if len(set(counts_)) < 2: return None
    return g
def tf_sortedpanels(g):
    h, w = dims(g)
    if h % 3 or w % 3: return None
    rows, cols = h // 3, w // 3
    panels = []
    for br in range(rows):
        for bc in range(cols):
            blk = [[g[br * 3 + dr][bc * 3 + dc] for dc in range(3)] for dr in range(3)]
            n = sum(1 for row in blk for v in row if v != 0)
            panels.append((n, blk))
    panels.sort(key=lambda p: p[0])
    n = len(panels)
    out = blank(3, n * 4 - 1)
    for i, (_, blk) in enumerate(panels):
        paste(out, blk, 0, i * 4)
        if i < n - 1:
            for r in range(3): out[r][i * 4 + 3] = 5
    return out
rule("panels_sorted_by_fill_count", "The grid is cut into non-overlapping 3x3 panels, row-major, then relaid in one row ordered by ascending coloured-cell count, panels separated by a grey column.", gi_sortedpanels, tf_sortedpanels, small_ok=True)


# 5 -- the row window of width 5 (stride 1, any single row) with the most distinct colours is
#      highlighted by recolouring its background cells to colour 5; ties go to the topmost then
#      leftmost window.
def gi_rowwindow5(rng):
    h, w = wsize(rng, 8, 20, p_big=0.45)
    if w < 5: w = 5
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.4: g[r][c] = rng.choice(COLOURS)
    return g
def tf_rowwindow5(g):
    h, w = dims(g)
    if w < 5: return None
    best, bestn = None, -1
    for r in range(h):
        for c in range(w - 4):
            vals = {g[r][c + k] for k in range(5)} - {0}
            if len(vals) > bestn:
                bestn, best = len(vals), (r, c)
    out = copy(g); r, c = best
    for k in range(5):
        if out[r][c + k] == 0: out[r][c + k] = 5
    return out
rule("highlight_row_window_most_colours", "Among all width-5 row windows (stride 1), the one spanning the most distinct non-zero colours has its empty cells recoloured grey, ties going to the topmost then leftmost window.", gi_rowwindow5, tf_rowwindow5)


# 6 -- the column band of width 3 (stride 1) with the most coloured cells is fully recoloured to colour 5
#      (coloured cells become 5, background stays 0); ties go to the leftmost band.
def gi_densecol(rng):
    h, w = wsize(rng, 10, 20)
    if w < 3: w = 3
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.3: g[r][c] = rng.choice(COLOURS)
    return g
def tf_densecol(g):
    h, w = dims(g)
    if w < 3: return None
    best, bestn = None, -1
    for c in range(w - 2):
        n = sum(1 for r in range(h) for dc in range(3) if g[r][c + dc] != 0)
        if n > bestn: bestn, best = n, c
    out = copy(g)
    for r in range(h):
        for dc in range(3):
            if out[r][best + dc] != 0: out[r][best + dc] = 5
    return out
rule("recolour_densest_column_band", "The width-3 column band (stride 1) containing the most coloured cells has every coloured cell in it recoloured grey, ties going to the leftmost band.", gi_densecol, tf_densecol)


# 7 -- every cell becomes the max colour value found in its own 3x3 neighbourhood (edge cells use a
#      clipped window); digits carry meaning so this pool is NOT colour-permuted.
def gi_maxwin(rng):
    return _sprinkle_scene(rng, 8, 20)
def tf_maxwin(g):
    h, w = dims(g); out = blank(h, w)
    for r in range(h):
        for c in range(w):
            vals = [g[rr][cc] for rr in range(max(0, r - 1), min(h, r + 2)) for cc in range(max(0, c - 1), min(w, c + 2))]
            out[r][c] = max(vals)
    return out
rule("cell_max_in_3x3_window", "Every cell becomes the largest colour value found in its 3x3 neighbourhood (a clipped window at the edges).", gi_maxwin, tf_maxwin, digits=True)


# 8 -- every cell becomes the colour of its most frequent 8-neighbour (not counting itself); ties keep
#      the cell's own colour.
def gi_majnb(rng):
    return _sprinkle_scene(rng, 10, 20, k_lo=None, k_hi=None)
def tf_majnb(g):
    h, w = dims(g); out = blank(h, w)
    for r in range(h):
        for c in range(w):
            nb = [g[rr][cc] for rr in range(max(0, r - 1), min(h, r + 2)) for cc in range(max(0, c - 1), min(w, c + 2)) if (rr, cc) != (r, c)]
            cnt = {}
            for v in nb: cnt[v] = cnt.get(v, 0) + 1
            if not cnt:
                out[r][c] = g[r][c]; continue
            best = max(cnt.values())
            winners = [v for v, n in cnt.items() if n == best]
            out[r][c] = winners[0] if len(winners) == 1 else g[r][c]
    return out
rule("cell_becomes_majority_neighbour_colour", "Every cell becomes the colour that occurs most among its 8 neighbours, keeping its own colour on a tie.", gi_majnb, tf_majnb)


# 9 -- every 3x3 window (stride 1) containing exactly one coloured cell gets that colour moved to the
#      window's centre in the output (background elsewhere in that window), built on a fresh blank grid,
#      later overlaps keep the last write in row-major scan order.
def gi_centre1(rng):
    h, w = wsize(rng, 10, 20); g = blank(h, w)
    k = rng.randint(h * w // 12, h * w // 6)
    free = [(r, c) for r in range(h) for c in range(w)]
    rng.shuffle(free)
    placed = 0
    for r, c in free:
        if placed >= k: break
        if all(g[rr][cc] == 0 for rr in range(max(0, r - 1), min(h, r + 2)) for cc in range(max(0, c - 1), min(w, c + 2))):
            g[r][c] = rng.choice(COLOURS); placed += 1
    return g if placed >= 2 else None
def tf_centre1(g):
    h, w = dims(g)
    if h < 3 or w < 3: return None
    out = blank(h, w)
    for r in range(h - 2):
        for c in range(w - 2):
            vals = [(rr, cc) for rr in range(r, r + 3) for cc in range(c, c + 3) if g[rr][cc] != 0]
            if len(vals) == 1:
                rr, cc = vals[0]
                out[r + 1][c + 1] = g[rr][cc]
    return out if any(v for row in out for v in row) else None
rule("centre_lone_cell_in_3x3", "For every 3x3 window (stride 1) containing exactly one coloured cell, that colour is written to the window's centre on a fresh blank grid, later windows overwriting earlier ones.", gi_centre1, tf_centre1)


# 10 -- cells whose 3x3 window is symmetric left-right (clipped at edges, compared column by column)
#       are marked by recolouring the centre to colour 5, kept if it was already coloured, overwritten if 0.
def gi_symlr(rng):
    h, w = wsize(rng, 10, 20); g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.3: g[r][c] = rng.choice(COLOURS)
    k = rng.randint(1, 3)
    for _ in range(k):
        r0 = rng.randrange(1, h - 1); c0 = rng.randrange(1, w - 1)
        col = rng.choice(COLOURS)
        for dr in range(-1, 2):
            g[r0 + dr][c0 - 1] = col; g[r0 + dr][c0 + 1] = col
    return g
def tf_symlr(g):
    h, w = dims(g); out = copy(g)
    for r in range(h):
        for c in range(w):
            win = [[g[rr][cc] if 0 <= rr < h and 0 <= cc < w else -1 for cc in range(c - 1, c + 2)] for rr in range(r - 1, r + 2)]
            if all(row[0] == row[2] for row in win):
                out[r][c] = 5
    return out
rule("mark_left_right_symmetric_windows", "Every cell whose 3x3 window (edges padded as unmatched) is symmetric left to right, column 0 matching column 2 in every row, is recoloured grey.", gi_symlr, tf_symlr)


# 11 -- the 3x3 window (stride 1) whose count of coloured cells matches a given key count (shown as the
#       lone cell in row 0) is outlined in colour 5; first such window in row-major order, key cell removed
#       from output.
def gi_matchcount(rng):
    h, w = wsize(rng, 11, 20); g = blank(h, w)
    for r in range(1, h):
        for c in range(w):
            if rng.random() < 0.3: g[r][c] = rng.choice(COLOURS)
    found = False
    for r in range(1, h - 2):
        for c in range(w - 2):
            n = sum(1 for dr in range(3) for dc in range(3) if g[r + dr][c + dc] != 0)
            if n in (3, 4, 5): found = True
    if not found: return None
    key_n = rng.choice([3, 4, 5])
    g[0][0] = key_n
    return g
def tf_matchcount(g):
    h, w = dims(g)
    key = g[0][0]
    body = [row[:] for row in g[1:]]
    hb, w2 = dims(body)
    if hb < 3 or w2 < 3: return None
    for r in range(hb - 2):
        for c in range(w2 - 2):
            n = sum(1 for dr in range(3) for dc in range(3) if body[r + dr][c + dc] != 0)
            if n == key:
                out = copy(body)
                for dr in range(3):
                    for dc in range(3):
                        if dr in (0, 2) or dc in (0, 2):
                            if out[r + dr][c + dc] == 0: out[r + dr][c + dc] = 5
                return out
    return None
rule("outline_3x3_window_matching_key_count", "Row 0 holds one cell whose value is a coloured-cell count; the first 3x3 window (stride 1) in the rest of the grid, scanned row-major, with that many coloured cells is outlined grey in the output, which drops row 0.", gi_matchcount, tf_matchcount, digits=True)


# 12 -- the sparsest 4x4 window (stride 1, fewest coloured cells, zero excluded) is filled solid grey;
#       ties go to the topmost then leftmost window.
def gi_sparse4(rng):
    return _sprinkle_scene(rng, 11, 22)
def tf_sparse4(g):
    h, w = dims(g)
    if h < 4 or w < 4: return None
    best, bestn = None, 999
    for r in range(h - 3):
        for c in range(w - 3):
            n = sum(1 for dr in range(4) for dc in range(4) if g[r + dr][c + dc] != 0)
            if n < bestn: bestn, best = n, (r, c)
    out = copy(g); r, c = best
    for dr in range(4):
        for dc in range(4): out[r + dr][c + dc] = 5
    return out
rule("fill_sparsest_4x4_window", "The 4x4 window (stride 1) with the fewest coloured cells is filled solid grey, ties going to the topmost then leftmost window.", gi_sparse4, tf_sparse4)


# 13 -- each 3x3 non-overlapping block becomes a single cell holding its most frequent non-zero colour
#       (grid cropped to a multiple of 3), background (0-majority) blocks become 0.
def gi_downmode(rng):
    rows, cols = rng.randint(3, 7), rng.randint(3, 7)
    h, w = rows * 3, cols * 3
    g = blank(h, w)
    for br in range(rows):
        for bc in range(cols):
            if rng.random() < 0.6:
                col = rng.choice(COLOURS)
                n = rng.randint(1, 9)
                cells_ = rng.sample([(dr, dc) for dr in range(3) for dc in range(3)], n)
                for dr, dc in cells_: g[br * 3 + dr][bc * 3 + dc] = col
    return g
def tf_downmode(g):
    h, w = dims(g)
    if h % 3 or w % 3: return None
    rows, cols = h // 3, w // 3
    out = blank(rows, cols)
    for br in range(rows):
        for bc in range(cols):
            cnt = {}
            for dr in range(3):
                for dc in range(3):
                    v = g[br * 3 + dr][bc * 3 + dc]
                    if v: cnt[v] = cnt.get(v, 0) + 1
            if cnt: out[br][bc] = max(cnt.items(), key=lambda kv: kv[1])[0]
    return out
rule("downsample_3x3_to_mode_colour", "The grid is cut into non-overlapping 3x3 blocks, and each becomes one output cell holding that block's most frequent non-zero colour, or background if the block was empty.", gi_downmode, tf_downmode)


# 14 -- each cell becomes the count (clipped to 9) of coloured neighbours in its 8-neighbourhood,
#       digits carry meaning.
def gi_neighcount(rng):
    return _sprinkle_scene(rng, 8, 20)
def tf_neighcount(g):
    h, w = dims(g); out = blank(h, w)
    for r in range(h):
        for c in range(w):
            n = sum(1 for rr in range(max(0, r - 1), min(h, r + 2)) for cc in range(max(0, c - 1), min(w, c + 2)) if (rr, cc) != (r, c) and g[rr][cc] != 0)
            out[r][c] = min(n, 9)
    return out
rule("cell_neighbour_count_clipped", "Every cell becomes the count (capped at 9) of coloured cells among its 8 neighbours.", gi_neighcount, tf_neighcount, digits=True)


# 15 -- the 3x3 window with the most coloured cells and the one with the fewest (ties: topmost then
#       leftmost each) swap their 3x3 contents in place.
def gi_swapwin(rng):
    return _sprinkle_scene(rng, 10, 20)
def tf_swapwin(g):
    h, w = dims(g)
    if h < 3 or w < 3: return None
    counts_ = []
    for r in range(h - 2):
        for c in range(w - 2):
            n = sum(1 for dr in range(3) for dc in range(3) if g[r + dr][c + dc] != 0)
            counts_.append((n, r, c))
    maxw = min((c for c in counts_ if c[0] == max(x[0] for x in counts_)))
    minw = min((c for c in counts_ if c[0] == min(x[0] for x in counts_)))
    if maxw[0] == minw[0]: return None
    out = copy(g)
    r1, c1 = maxw[1], maxw[2]; r2, c2 = minw[1], minw[2]
    blk1 = [[g[r1 + dr][c1 + dc] for dc in range(3)] for dr in range(3)]
    blk2 = [[g[r2 + dr][c2 + dc] for dc in range(3)] for dr in range(3)]
    paste(out, blk2, r1, c1); paste(out, blk1, r2, c2)
    return out
rule("swap_densest_and_sparsest_3x3", "The 3x3 window (stride 1) with the most coloured cells and the one with the fewest, ties going to the topmost then leftmost window each, swap their contents in place.", gi_swapwin, tf_swapwin)


# 16 -- every 3x3 window whose corners (the four cells at (0,0),(0,2),(2,0),(2,2)) are all the same
#       non-zero colour has its centre set to that colour.
def gi_corners(rng):
    h, w = wsize(rng, 10, 20); g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.35: g[r][c] = rng.choice(COLOURS)
    if h >= 3 and w >= 3:
        for _ in range(rng.randint(1, 3)):
            r0, c0 = rng.randrange(h - 2), rng.randrange(w - 2)
            col = rng.choice(COLOURS)
            g[r0][c0] = g[r0][c0 + 2] = g[r0 + 2][c0] = g[r0 + 2][c0 + 2] = col
            g[r0 + 1][c0 + 1] = rng.choice([c for c in COLOURS if c != col] + [0])
    return g
def tf_corners(g):
    h, w = dims(g)
    if h < 3 or w < 3: return None
    out = copy(g)
    for r in range(h - 2):
        for c in range(w - 2):
            cs = {g[r][c], g[r][c + 2], g[r + 2][c], g[r + 2][c + 2]}
            if len(cs) == 1 and 0 not in cs:
                out[r + 1][c + 1] = g[r][c]
    return out
rule("mark_centre_when_corners_match", "Every 3x3 window (stride 1) whose four corner cells are all the same non-zero colour has its centre set to that colour.", gi_corners, tf_corners)


# 17 -- non-overlapping 2x2 blocks (grid cropped to even dims) become a half-size grid, each output cell
#       holding colour 5 if its block had 2 or more coloured cells, else 0.
def gi_downthresh(rng):
    rows, cols = bdim(rng, 2, 4, 10), bdim(rng, 2, 4, 10)
    h, w = rows * 2, cols * 2
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.3: g[r][c] = rng.choice(COLOURS)
    return g
def tf_downthresh(g):
    h, w = dims(g)
    if h % 2 or w % 2: return None
    rows, cols = h // 2, w // 2
    out = blank(rows, cols)
    for br in range(rows):
        for bc in range(cols):
            n = sum(1 for dr in range(2) for dc in range(2) if g[br * 2 + dr][bc * 2 + dc] != 0)
            if n >= 2: out[br][bc] = 5
    return out
rule("downsample_2x2_threshold", "The grid is cut into non-overlapping 2x2 blocks; each becomes one output cell, grey if the block had 2 or more coloured cells, background otherwise.", gi_downthresh, tf_downthresh)


# 18 -- the row with the highest variance of column-run lengths of coloured cells is recoloured entirely
#       to colour 5 (simplified: the row with the most colour-value transitions, i.e. the row whose
#       coloured cells change colour most often moving left to right) is fully recoloured grey; ties go
#       to the topmost such row.
def gi_mostchanges(rng):
    h, w = wsize(rng, 10, 20); g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.5: g[r][c] = rng.choice(COLOURS)
    return g
def tf_mostchanges(g):
    h, w = dims(g)
    best, bestn = None, -1
    for r in range(h):
        n = sum(1 for c in range(1, w) if g[r][c] != g[r][c - 1])
        if n > bestn: bestn, best = n, r
    out = copy(g)
    for c in range(w): out[best][c] = 5
    return out
rule("recolour_row_most_transitions", "The row with the most colour changes between adjacent cells, moving left to right, is fully recoloured grey, ties going to the topmost such row.", gi_mostchanges, tf_mostchanges)


# 19 -- the column with the most colour changes between adjacent cells is fully recoloured grey; ties go
#       to the leftmost such column.
def gi_mostchangescol(rng):
    h, w = wsize(rng, 10, 20); g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.5: g[r][c] = rng.choice(COLOURS)
    return g
def tf_mostchangescol(g):
    h, w = dims(g)
    best, bestn = None, -1
    for c in range(w):
        n = sum(1 for r in range(1, h) if g[r][c] != g[r - 1][c])
        if n > bestn: bestn, best = n, c
    out = copy(g)
    for r in range(h): out[r][best] = 5
    return out
rule("recolour_column_most_transitions", "The column with the most colour changes between adjacent cells, moving top to bottom, is fully recoloured grey, ties going to the leftmost such column.", gi_mostchangescol, tf_mostchangescol)


# 20 -- every 3x3 window (stride 1) that contains at least 3 distinct non-zero colours has its centre
#       cell recoloured to colour 5 (overwriting whatever was there).
def gi_diversecentre(rng):
    return _sprinkle_scene(rng, 10, 20)
def tf_diversecentre(g):
    h, w = dims(g)
    if h < 3 or w < 3: return None
    out = copy(g)
    for r in range(h - 2):
        for c in range(w - 2):
            vals = {g[r + dr][c + dc] for dr in range(3) for dc in range(3)} - {0}
            if len(vals) >= 3:
                out[r + 1][c + 1] = 5
    return out
rule("mark_centre_of_diverse_3x3", "Every 3x3 window (stride 1) containing at least three distinct non-zero colours has its centre recoloured grey.", gi_diversecentre, tf_diversecentre)


# 21 -- each non-overlapping 3x3 block becomes one cell holding colour 5 if the block is left-right
#       symmetric (column 0 equals column 2 in every row), else colour 0.
def gi_blocksym(rng):
    rows, cols = bdim(rng, 3, 3, 6), bdim(rng, 3, 3, 6)
    h, w = rows * 3, cols * 3
    g = blank(h, w)
    for br in range(rows):
        for bc in range(cols):
            if rng.random() < 0.5:
                col = rng.choice(COLOURS)
                for dr in range(3):
                    v = rng.choice(COLOURS)
                    g[br * 3 + dr][bc * 3 + 1] = v
                    if rng.random() < 0.7:
                        g[br * 3 + dr][bc * 3] = col; g[br * 3 + dr][bc * 3 + 2] = col
                    else:
                        g[br * 3 + dr][bc * 3] = col; g[br * 3 + dr][bc * 3 + 2] = rng.choice(COLOURS)
    return g
def tf_blocksym(g):
    h, w = dims(g)
    if h % 3 or w % 3: return None
    rows, cols = h // 3, w // 3
    out = blank(rows, cols)
    for br in range(rows):
        for bc in range(cols):
            sym = all(g[br * 3 + dr][bc * 3] == g[br * 3 + dr][bc * 3 + 2] for dr in range(3))
            out[br][bc] = 5 if sym else 0
    return out
rule("block_symmetry_map", "The grid is cut into non-overlapping 3x3 blocks, and each becomes one output cell: grey if that block's first and third columns match row by row, background otherwise.", gi_blocksym, tf_blocksym)


# 22 -- the 3x3 window (stride 1) whose coloured-cell count is closest to the grid's overall mean density
#       (coloured cells / total 3x3 windows' average) is outlined in colour 5; concretely, closest to the
#       median window count across all windows, ties going to the topmost then leftmost window.
def gi_medianwin(rng):
    return _sprinkle_scene(rng, 10, 20)
def tf_medianwin(g):
    h, w = dims(g)
    if h < 3 or w < 3: return None
    counts_ = []
    for r in range(h - 2):
        for c in range(w - 2):
            n = sum(1 for dr in range(3) for dc in range(3) if g[r + dr][c + dc] != 0)
            counts_.append((n, r, c))
    vals = sorted(c[0] for c in counts_)
    med = vals[len(vals) // 2]
    best = min(counts_, key=lambda t: (abs(t[0] - med), t[1], t[2]))
    out = copy(g); r, c = best[1], best[2]
    for dr in range(3):
        for dc in range(3):
            if dr in (0, 2) or dc in (0, 2):
                if out[r + dr][c + dc] == 0: out[r + dr][c + dc] = 5
    return out
rule("outline_median_density_3x3", "The 3x3 window (stride 1) whose coloured-cell count is closest to the median count across all windows is outlined grey, ties going to the smaller count then the topmost then leftmost window.", gi_medianwin, tf_medianwin)


# 23 -- a 3x1 vertical window (stride 1, any column) containing three distinct non-zero colours stacked
#       has its middle cell marked grey; first such window found scanning column-major, top to bottom.
def gi_vert3distinct(rng):
    h, w = wsize(rng, 10, 20)
    if h < 3: h = 3
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.4: g[r][c] = rng.choice(COLOURS)
    return g
def tf_vert3distinct(g):
    h, w = dims(g)
    if h < 3: return None
    out = copy(g)
    for c in range(w):
        for r in range(h - 2):
            vals = {g[r][c], g[r + 1][c], g[r + 2][c]}
            if 0 not in vals and len(vals) == 3:
                out[r + 1][c] = 5
                return out
    return None
rule("mark_middle_of_vertical_triple", "The first 3-cell vertical window (stride 1), scanned column by column top to bottom, holding three distinct non-zero colours has its middle cell recoloured grey.", gi_vert3distinct, tf_vert3distinct)


# 24 -- each cell becomes the minimum non-zero colour value in its 3x3 window, or stays 0 if the window
#       has no coloured cell; digits carry meaning.
def gi_minwin(rng):
    return _sprinkle_scene(rng, 8, 20)
def tf_minwin(g):
    h, w = dims(g); out = blank(h, w)
    for r in range(h):
        for c in range(w):
            vals = [g[rr][cc] for rr in range(max(0, r - 1), min(h, r + 2)) for cc in range(max(0, c - 1), min(w, c + 2)) if g[rr][cc] != 0]
            if vals: out[r][c] = min(vals)
    return out
rule("cell_min_nonzero_in_3x3_window", "Every cell becomes the smallest non-zero colour value found in its 3x3 neighbourhood, or stays background if the neighbourhood has none.", gi_minwin, tf_minwin, digits=True)


# 25 -- non-overlapping 3x3 blocks (grid cropped to a multiple of 3) are each replaced by their count of
#       coloured cells rendered as a single digit-valued cell; digits carry meaning.
def gi_blockcount(rng):
    rows, cols = rng.randint(3, 7), rng.randint(3, 7)
    h, w = rows * 3, cols * 3
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.3: g[r][c] = rng.choice(COLOURS)
    return g
def tf_blockcount(g):
    h, w = dims(g)
    if h % 3 or w % 3: return None
    rows, cols = h // 3, w // 3
    out = blank(rows, cols)
    for br in range(rows):
        for bc in range(cols):
            n = sum(1 for dr in range(3) for dc in range(3) if g[br * 3 + dr][bc * 3 + dc] != 0)
            out[br][bc] = n
    return out
# downsample_3x3_to_fill_count dropped 2026-10-12 (review 2: behavioural duplicate of block_cell_count_digits)
# 26 -- the 5x5 window (stride 1) with the most distinct colours is outlined in colour 5; ties go to the
#       topmost then leftmost window.
def gi_densest5(rng):
    return _sprinkle_scene(rng, 12, 24)
def tf_densest5(g):
    h, w = dims(g)
    if h < 5 or w < 5: return None
    best, bestn = None, -1
    for r in range(h - 4):
        for c in range(w - 4):
            vals = {g[r + dr][c + dc] for dr in range(5) for dc in range(5)} - {0}
            if len(vals) > bestn: bestn, best = len(vals), (r, c)
    out = copy(g); r, c = best
    for dr in range(5):
        for dc in range(5):
            if dr in (0, 4) or dc in (0, 4):
                if out[r + dr][c + dc] == 0: out[r + dr][c + dc] = 5
    return out
rule("outline_5x5_window_most_distinct_colours", "The 5x5 window (stride 1) spanning the most distinct non-zero colours is outlined grey, ties going to the topmost then leftmost window.", gi_densest5, tf_densest5)


# 27 -- every 3x3 window that is a palindrome reading its 9 cells in row-major order (cell i equals
#       cell 8-i for all i) has its centre marked colour 5.
def gi_palin3(rng):
    return _sprinkle_scene(rng, 10, 20)
def tf_palin3(g):
    h, w = dims(g)
    if h < 3 or w < 3: return None
    out = copy(g)
    for r in range(h - 2):
        for c in range(w - 2):
            flat = [g[r + dr][c + dc] for dr in range(3) for dc in range(3)]
            if flat == flat[::-1] and any(flat):
                out[r + 1][c + 1] = 5
    return out
rule("mark_palindromic_3x3_windows", "Every 3x3 window (stride 1) whose nine cells read the same forwards and backwards in row-major order has its centre recoloured grey.", gi_palin3, tf_palin3)


# 28 -- each non-overlapping 2x2 block is recoloured to colour 5 if it contains exactly one coloured
#       cell, left unchanged otherwise (grid cropped to even dims).
def gi_singletonblock(rng):
    rows, cols = bdim(rng, 2, 4, 9), bdim(rng, 2, 4, 9)
    h, w = rows * 2, cols * 2
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.25: g[r][c] = rng.choice(COLOURS)
    return g
def tf_singletonblock(g):
    h, w = dims(g)
    if h % 2 or w % 2: return None
    out = copy(g)
    for br in range(0, h, 2):
        for bc in range(0, w, 2):
            vals = [(r, c) for r in (br, br + 1) for c in (bc, bc + 1) if g[r][c] != 0]
            if len(vals) == 1:
                for r in (br, br + 1):
                    for c in (bc, bc + 1): out[r][c] = 5
    return out
rule("recolour_singleton_2x2_blocks", "The grid is cut into non-overlapping 2x2 blocks; every block containing exactly one coloured cell is fully recoloured grey, the rest left unchanged.", gi_singletonblock, tf_singletonblock)


# 29 -- the 3x3 window (stride 1) whose cells sum to the largest total colour value is outlined grey;
#       ties go to the topmost then leftmost window; digits carry meaning.
def gi_sumwin(rng):
    return _sprinkle_scene(rng, 10, 20)
def tf_sumwin(g):
    h, w = dims(g)
    if h < 3 or w < 3: return None
    best, bests = None, -1
    for r in range(h - 2):
        for c in range(w - 2):
            s = sum(g[r + dr][c + dc] for dr in range(3) for dc in range(3))
            if s > bests: bests, best = s, (r, c)
    out = copy(g); r, c = best
    for dr in range(3):
        for dc in range(3):
            if dr in (0, 2) or dc in (0, 2):
                if out[r + dr][c + dc] == 0: out[r + dr][c + dc] = 5
    return out
rule("outline_3x3_max_colour_sum", "The 3x3 window (stride 1) whose nine colour values sum to the largest total is outlined grey, ties going to the topmost then leftmost window.", gi_sumwin, tf_sumwin, digits=True)


# 30 -- each row is replaced by the running count, clipped to 9, of coloured cells seen so far left to
#       right (a width-1 forward window of growing size); digits carry meaning.
def gi_runcount(rng):
    h, w = wsize(rng, 10, 20); g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.3: g[r][c] = rng.choice(COLOURS)
    return g if any(v for row in g for v in row) else None
def tf_runcount(g):
    h, w = dims(g); out = blank(h, w)
    for r in range(h):
        n = 0
        for c in range(w):
            if g[r][c] != 0: n += 1
            out[r][c] = min(n, 9)
    return out
rule("row_running_coloured_count", "Every row is replaced left to right by the running count, capped at 9, of coloured cells encountered so far in that row.", gi_runcount, tf_runcount, digits=True)


# 31 -- the 3x3 window (stride 1) with the most coloured cells on its border ring (the 8 cells excluding
#       centre) is outlined grey; ties go to the topmost then leftmost window.
def gi_ringwin(rng):
    return _sprinkle_scene(rng, 10, 20)
def tf_ringwin(g):
    h, w = dims(g)
    if h < 3 or w < 3: return None
    best, bestn = None, -1
    for r in range(h - 2):
        for c in range(w - 2):
            n = sum(1 for dr in range(3) for dc in range(3) if (dr, dc) != (1, 1) and g[r + dr][c + dc] != 0)
            if n > bestn: bestn, best = n, (r, c)
    out = copy(g); r, c = best
    for dr in range(3):
        for dc in range(3):
            if dr in (0, 2) or dc in (0, 2):
                if out[r + dr][c + dc] == 0: out[r + dr][c + dc] = 5
    return out
rule("outline_3x3_densest_ring", "The 3x3 window (stride 1) with the most coloured cells on its 8-cell border ring, excluding the centre, is outlined grey, ties going to the topmost then leftmost window.", gi_ringwin, tf_ringwin)


# 32 -- every 3x3 window (stride 1) whose centre colour differs from all 8 of its neighbours (a local
#       singleton) has its centre recoloured to colour 5.
def gi_isolated(rng):
    h, w = wsize(rng, 10, 20); g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.25: g[r][c] = rng.choice(COLOURS)
    return g if any(v for row in g for v in row) else None
def tf_isolated(g):
    h, w = dims(g)
    if h < 3 or w < 3: return None
    out = copy(g)
    for r in range(1, h - 1):
        for c in range(1, w - 1):
            if g[r][c] == 0: continue
            nb = [g[rr][cc] for rr in range(r - 1, r + 2) for cc in range(c - 1, c + 2) if (rr, cc) != (r, c)]
            if g[r][c] not in nb:
                out[r][c] = 5
    return out
rule("mark_locally_isolated_colour", "Every coloured cell whose colour appears nowhere among its 8 neighbours is recoloured grey.", gi_isolated, tf_isolated)


# 33 -- non-overlapping 3x3 blocks are stacked into a single output row, each block shrunk to a single
#       column whose cells (top to bottom) are the block's distinct non-zero colours sorted ascending,
#       padded with background below to the tallest block's colour count.
def gi_blockpalette(rng):
    rows, cols = bdim(rng, 3, 2, 4), bdim(rng, 3, 3, 6)
    h, w = rows * 3, cols * 3
    g = blank(h, w)
    for br in range(rows):
        for bc in range(cols):
            k = rng.randint(1, 4)
            cs = colours(rng, k)
            cells_ = rng.sample([(dr, dc) for dr in range(3) for dc in range(3)], k)
            for (dr, dc), col in zip(cells_, cs):
                g[br * 3 + dr][bc * 3 + dc] = col
    return g
def tf_blockpalette(g):
    h, w = dims(g)
    if h % 3 or w % 3: return None
    rows, cols = h // 3, w // 3
    palettes = []
    for br in range(rows):
        for bc in range(cols):
            vals = sorted({g[br * 3 + dr][bc * 3 + dc] for dr in range(3) for dc in range(3)} - {0})
            palettes.append(vals)
    if not palettes or max(len(p) for p in palettes) == 0: return None
    maxk = max(len(p) for p in palettes)
    n = len(palettes)
    out = blank(maxk, n)
    for i, p in enumerate(palettes):
        for j, v in enumerate(p): out[j][i] = v
    return out
rule("blocks_to_palette_columns", "The grid is cut into non-overlapping 3x3 blocks, row-major; each becomes one output column listing its distinct non-zero colours top to bottom in ascending order, padded below with background.", gi_blockpalette, tf_blockpalette)


# 34 -- the 3x3 window (stride 1) with the fewest distinct colours (but at least one coloured cell) is
#       outlined grey; ties go to the topmost then leftmost window.
def gi_uniformwin(rng):
    return _sprinkle_scene(rng, 10, 20)
def tf_uniformwin(g):
    h, w = dims(g)
    if h < 3 or w < 3: return None
    best, bestn = None, 999
    for r in range(h - 2):
        for c in range(w - 2):
            vals = {g[r + dr][c + dc] for dr in range(3) for dc in range(3)} - {0}
            if not vals: continue
            if len(vals) < bestn: bestn, best = len(vals), (r, c)
    if best is None: return None
    out = copy(g); r, c = best
    for dr in range(3):
        for dc in range(3):
            if dr in (0, 2) or dc in (0, 2):
                if out[r + dr][c + dc] == 0: out[r + dr][c + dc] = 5
    return out
rule("outline_3x3_fewest_distinct_colours", "The 3x3 window (stride 1) that contains at least one coloured cell and the fewest distinct colours is outlined grey, ties going to the topmost then leftmost window.", gi_uniformwin, tf_uniformwin)


# 35 -- each cell becomes colour 5 if its 3x3 window contains coloured cells of exactly two distinct
#       colours in equal counts (a local tie), else stays background/unchanged for coloured cells.
def gi_tiewin(rng):
    return _sprinkle_scene(rng, 10, 20)
def tf_tiewin(g):
    h, w = dims(g); out = copy(g)
    for r in range(h):
        for c in range(w):
            cnt = {}
            for rr in range(max(0, r - 1), min(h, r + 2)):
                for cc in range(max(0, c - 1), min(w, c + 2)):
                    v = g[rr][cc]
                    if v: cnt[v] = cnt.get(v, 0) + 1
            if len(cnt) == 2 and len(set(cnt.values())) == 1:
                out[r][c] = 5
    return out
rule("mark_cells_with_local_colour_tie", "Every cell whose 3x3 window (clipped at the edges) contains coloured cells of exactly two distinct colours in equal counts is recoloured grey.", gi_tiewin, tf_tiewin)


# 36 -- the first non-overlapping 3x3 block (row-major) that is entirely background is replaced with a
#       solid grey block; if none is entirely background, return None.
def gi_emptyblock(rng):
    rows, cols = bdim(rng, 3, 3, 6), bdim(rng, 3, 3, 6)
    h, w = rows * 3, cols * 3
    g = blank(h, w)
    empties = [(br, bc) for br in range(rows) for bc in range(cols)]
    rng.shuffle(empties)
    n_empty = rng.randint(1, max(1, len(empties) // 3))
    empty_set = set(empties[:n_empty])
    for br in range(rows):
        for bc in range(cols):
            if (br, bc) in empty_set: continue
            k = rng.randint(1, 5)
            cells_ = rng.sample([(dr, dc) for dr in range(3) for dc in range(3)], k)
            col = rng.choice(COLOURS)
            for dr, dc in cells_: g[br * 3 + dr][bc * 3 + dc] = col
    return g
def tf_emptyblock(g):
    h, w = dims(g)
    if h % 3 or w % 3: return None
    rows, cols = h // 3, w // 3
    for br in range(rows):
        for bc in range(cols):
            vals = {g[br * 3 + dr][bc * 3 + dc] for dr in range(3) for dc in range(3)}
            if vals == {0}:
                out = copy(g)
                rect(out, br * 3, bc * 3, br * 3 + 2, bc * 3 + 2, 5)
                return out
    return None
rule("fill_first_empty_3x3_block", "The grid is cut into non-overlapping 3x3 blocks, row-major; the first block that is entirely background is filled solid grey.", gi_emptyblock, tf_emptyblock)


# 37 -- the 3x3 window (stride 1) centred on each coloured cell is checked; if that window's coloured
#       count (excluding the centre) is odd the centre is recoloured 5, if even it is unchanged; applied
#       to every coloured cell simultaneously on the input.
def gi_parityneigh(rng):
    return _sprinkle_scene(rng, 10, 20)
def tf_parityneigh(g):
    h, w = dims(g); out = copy(g)
    for r in range(h):
        for c in range(w):
            if g[r][c] == 0: continue
            n = sum(1 for rr in range(max(0, r - 1), min(h, r + 2)) for cc in range(max(0, c - 1), min(w, c + 2)) if (rr, cc) != (r, c) and g[rr][cc] != 0)
            if n % 2 == 1: out[r][c] = 5
    return out
rule("mark_coloured_cells_odd_neighbour_parity", "Every coloured cell whose 3x3 window has an odd number of coloured neighbours (excluding itself) is recoloured grey; even counts are left unchanged.", gi_parityneigh, tf_parityneigh)


# 38 -- the top-left 3x3 window and bottom-right 3x3 window (stride 1 positions, i.e. rows/cols
#       0-2 and the last three rows/cols) are compared cell by cell; every differing cell position is
#       marked grey in both locations, matching cells unchanged.
def gi_cornerdiff(rng):
    h, w = wsize(rng, 10, 20)
    if h < 3 or w < 3: h, w = max(h, 3), max(w, 3)
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.4: g[r][c] = rng.choice(COLOURS)
    return g
def tf_cornerdiff(g):
    h, w = dims(g)
    if h < 3 or w < 3: return None
    out = copy(g)
    for dr in range(3):
        for dc in range(3):
            a = g[dr][dc]; b = g[h - 3 + dr][w - 3 + dc]
            if a != b:
                out[dr][dc] = 5; out[h - 3 + dr][w - 3 + dc] = 5
    return out
rule("mark_differences_top_left_vs_bottom_right_3x3", "The top-left 3x3 window and the bottom-right 3x3 window are compared cell by cell; every position where they differ is recoloured grey in both windows.", gi_cornerdiff, tf_cornerdiff)


# 39 -- each non-overlapping 3x3 block's coloured-cell count (clipped to 9) replaces the block's centre
#       cell, leaving the rest of the block as it was (digits carry meaning).
def gi_blockcentrecount(rng):
    rows, cols = rng.randint(3, 7), rng.randint(3, 7)
    h, w = rows * 3, cols * 3
    g = blank(h, w)
    for r in range(h):
        for c in range(w):
            if rng.random() < 0.3: g[r][c] = rng.choice(COLOURS)
    return g
def tf_blockcentrecount(g):
    h, w = dims(g)
    if h % 3 or w % 3: return None
    rows, cols = h // 3, w // 3
    out = copy(g)
    for br in range(rows):
        for bc in range(cols):
            n = sum(1 for dr in range(3) for dc in range(3) if g[br * 3 + dr][bc * 3 + dc] != 0)
            out[br * 3 + 1][bc * 3 + 1] = min(n, 9)
    return out
rule("stamp_block_count_at_centre", "The grid is cut into non-overlapping 3x3 blocks; each block's centre cell is overwritten with that block's coloured-cell count, capped at 9, the rest of the block unchanged.", gi_blockcentrecount, tf_blockcentrecount, digits=True)


# 40 -- the 3x3 window (stride 1) most similar to a fixed 3x3 key pattern shown in the top-left corner
#       of the grid (minimum count of differing cells, ties to the topmost then leftmost window among
#       windows scanned starting after column 3 so the key itself is excluded) is outlined grey; the key
#       block is removed from the output (left as background).
def gi_closestmatch(rng):
    h, w = wsize(rng, 12, 22)
    if w < 7: w = 7
    g = blank(h, w)
    for r in range(h):
        for c in range(3, w):
            if rng.random() < 0.3: g[r][c] = rng.choice(COLOURS)
    key = [[rng.choice([0] + COLOURS) for _ in range(3)] for _ in range(3)]
    if all(v == 0 for row in key for v in row): key[1][1] = rng.choice(COLOURS)
    paste(g, key, 0, 0)
    return g
def tf_closestmatch(g):
    h, w = dims(g)
    if h < 3 or w < 6: return None
    key = [row[:3] for row in g[0:3]]
    out = copy(g)
    for r in range(3): out[r][0] = out[r][1] = out[r][2] = 0
    best, bestd = None, 999
    for r in range(h - 2):
        for c in range(3, w - 2):
            d = sum(1 for dr in range(3) for dc in range(3) if g[r + dr][c + dc] != key[dr][dc])
            if d < bestd: bestd, best = d, (r, c)
    if best is None: return None
    r, c = best
    for dr in range(3):
        for dc in range(3):
            if dr in (0, 2) or dc in (0, 2):
                if out[r + dr][c + dc] == 0: out[r + dr][c + dc] = 5
    return out
rule("outline_3x3_closest_to_key_pattern", "A 3x3 key pattern occupies the top-left corner; among all 3x3 windows (stride 1) starting at column 3 or later, the one with the fewest differing cells from the key is outlined grey, ties going to the topmost then leftmost window, and the key is erased to background in the output.", gi_closestmatch, tf_closestmatch)
