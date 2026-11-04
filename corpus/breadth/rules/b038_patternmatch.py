# b038_patternmatch.py -- theme: finding a given key pattern in the grid. A small key shape sits above
# a full-width separator row (colour SEP); the field below holds several occurrences of the key (exact,
# recoloured, rotated, mirrored, or size-matched, per rule) plus distractor shapes that never match.
# Shared plumbing below; each rule wires a match criterion to an output action, plus a handful of
# bespoke rules (odd-one-out, second-key replace, shift, row/column sequence key).
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

SEP = 5     # reserved: the separator row's colour, never used for shapes or background
MARK = 4    # reserved: the highlight colour used by "mark" actions


def _palette(exclude=()):
    return [c for c in range(1, 10) if c not in exclude]


def _norm(cells_):
    r0 = min(r for r, _ in cells_); c0 = min(c for _, c in cells_)
    return frozenset((r - r0, c - c0) for r, c in cells_)


def _rots(shape):
    pts = set(shape); out = []
    for _ in range(4):
        out.append(_norm(pts)); pts = {(c, -r) for r, c in pts}
    return out


def _refl_only(shape):
    return [_norm({(r, -c) for r, c in shape}), _norm({(-r, c) for r, c in shape})]


def _refl_rots(shape):
    out = list(_rots(shape))
    for v in _refl_only(shape):
        out += _rots(v)
    return out


def _sep_row(g):
    for i, row in enumerate(g):
        if row[0] == SEP and all(v == SEP for v in row):
            return i
    return None


def _split(g):
    i = _sep_row(g)
    if i is None or i == 0 or i >= len(g) - 1:
        return None
    return g[:i], g[i + 1:], i


def _key_shape(key_grid):
    cs = [(r, c) for r, row in enumerate(key_grid) for c, v in enumerate(row) if v]
    if not cs:
        return None, None
    col = key_grid[cs[0][0]][cs[0][1]]
    return _norm(cs), col


def _field_objs(field):
    return components(field, lambda v: v != 0, conn8=False)


def _match_pred(mode):
    table = {
        "exact": lambda s, c, ks, kc: s == ks and c == kc,
        "anycolour": lambda s, c, ks, kc: s == ks,
        "rot": lambda s, c, ks, kc: c == kc and s in _rots(ks),
        "rot_any": lambda s, c, ks, kc: s in _rots(ks),
        "refl": lambda s, c, ks, kc: c == kc and s in _refl_only(ks),
        "refl_any": lambda s, c, ks, kc: s in _refl_only(ks),
        "rotrefl": lambda s, c, ks, kc: c == kc and s in _refl_rots(ks),
        "rotrefl_any": lambda s, c, ks, kc: s in _refl_rots(ks),
        "size": lambda s, c, ks, kc: c == kc and len(s) == len(ks),
        "size_any": lambda s, c, ks, kc: len(s) == len(ks),
    }
    return table[mode]


def _occ_variant_shape(rng, shape, mode):
    if mode in ("rot", "rot_any"):
        return list(rng.choice(_rots(shape)))
    if mode in ("refl", "refl_any"):
        return list(rng.choice(_refl_only(shape)))
    if mode in ("rotrefl", "rotrefl_any"):
        return list(rng.choice(_refl_rots(shape)))
    if mode in ("size", "size_any"):
        for _ in range(30):
            alt = random_shape(rng, len(shape))
            if _norm(alt) != _norm(shape):
                return list(alt)
        return list(shape)
    return list(shape)


def _occ_colour(rng, kcol, other, mode):
    if mode == "anycolour" or mode.endswith("_any"):
        return rng.choice(other + [kcol])
    return kcol


def _gen(rng, mode, n_lo=3, n_hi=6, w_lo=9, w_hi=18, fh_lo=6, fh_hi=16, n_occ=(2, 4), n_dist=(1, 3), big=False):
    if big:
        if rng.random() < 0.5:
            w_lo, w_hi = 21, 30
        else:
            fh_lo, fh_hi = 18, 22
    W = rng.randint(w_lo, w_hi)
    shape = random_shape(rng, rng.randint(n_lo, n_hi))
    sh_h = max(r for r, _ in shape) + 1; sh_w = max(c for _, c in shape) + 1
    if sh_w > W:
        return None
    kh = max(sh_h, 2)
    kcol = rng.choice(_palette(exclude=(SEP, MARK)))
    key = blank(kh, W)
    for r, c in shape:
        key[r][c] = kcol
    fh = rng.randint(fh_lo, fh_hi)
    if kh + 1 + fh > 30:
        fh = max(fh_lo, 30 - kh - 1)
    field = blank(fh, W)
    occupied = set()

    def fits(cells_, margin=1):
        if not all(0 <= r < fh and 0 <= c < W for r, c in cells_):
            return False
        exp = set()
        for r, c in cells_:
            for dr in (-margin, 0, margin):
                for dc in (-margin, 0, margin):
                    exp.add((r + dr, c + dc))
        return not (exp & occupied)

    def stamp(cells_, col):
        for r, c in cells_:
            field[r][c] = col; occupied.add((r, c))

    other = _palette(exclude=(SEP, MARK, kcol))
    n_o = rng.randint(*n_occ); placed = 0
    for _ in range(n_o * 30):
        if placed >= n_o:
            break
        vs = _occ_variant_shape(rng, shape, mode)
        col = _occ_colour(rng, kcol, other, mode)
        r0 = rng.randrange(fh); c0 = rng.randrange(W)
        cells_ = [(r0 + r, c0 + c) for r, c in vs]
        if fits(cells_):
            stamp(cells_, col); placed += 1
    if placed == 0:
        return None
    n_d = rng.randint(*n_dist); dplaced = 0
    for _ in range(n_d * 30):
        if dplaced >= n_d:
            break
        dn = len(shape)
        tries = 0
        while dn == len(shape) and tries < 10:
            dn = rng.randint(2, n_hi + 3); tries += 1
        dshape = random_shape(rng, dn)
        col = rng.choice(other) if other else kcol
        r0 = rng.randrange(fh); c0 = rng.randrange(W)
        cells_ = [(r0 + r, c0 + c) for r, c in dshape]
        if fits(cells_):
            stamp(cells_, col); dplaced += 1
    return [row[:] for row in key] + [[SEP] * W] + [row[:] for row in field]


def _matches(field, mode, ks, kc):
    pred = _match_pred(mode)
    return [comp for comp in _field_objs(field)
            if pred(_norm(comp), field[comp[0][0]][comp[0][1]], ks, kc)]


# ---------- action builders: each returns a transform(g) given a mode ----------

def _tf_highlight(mode):
    def tf(g):
        sp = _split(g)
        if sp is None:
            return None
        key, field, idx = sp
        ks, kc = _key_shape(key)
        if ks is None:
            return None
        ms = _matches(field, mode, ks, kc)
        if not ms:
            return None
        out = copy(g)
        for comp in ms:
            for (r, c) in comp:
                out[idx + 1 + r][c] = MARK
        return out if out != g else None
    return tf


def _tf_recolour_to_key(mode):
    def tf(g):
        sp = _split(g)
        if sp is None:
            return None
        key, field, idx = sp
        ks, kc = _key_shape(key)
        if ks is None:
            return None
        ms = _matches(field, mode, ks, kc)
        if not ms:
            return None
        out = copy(g)
        for comp in ms:
            for (r, c) in comp:
                out[idx + 1 + r][c] = kc
        return out if out != g else None
    return tf


def _tf_frame(mode):
    def tf(g):
        sp = _split(g)
        if sp is None:
            return None
        key, field, idx = sp
        ks, kc = _key_shape(key)
        if ks is None:
            return None
        ms = _matches(field, mode, ks, kc)
        if not ms:
            return None
        out = copy(g); H, W = dims(out)
        for comp in ms:
            r0, c0, r1, c1 = bbox(comp)
            r0 += idx + 1; r1 += idx + 1
            for r in range(max(0, r0 - 1), min(H, r1 + 2)):
                for c in range(max(0, c0 - 1), min(W, c1 + 2)):
                    if r in (r0 - 1, r1 + 1) or c in (c0 - 1, c1 + 1):
                        out[r][c] = MARK
        return out if out != g else None
    return tf


def _tf_erase_others(mode):
    def tf(g):
        sp = _split(g)
        if sp is None:
            return None
        key, field, idx = sp
        ks, kc = _key_shape(key)
        if ks is None:
            return None
        pred = _match_pred(mode)
        out = copy(g); changed = False
        for comp in _field_objs(field):
            s = _norm(comp); c = field[comp[0][0]][comp[0][1]]
            if not pred(s, c, ks, kc):
                for (r, cc) in comp:
                    out[idx + 1 + r][cc] = 0
                changed = True
        return out if changed and out != g else None
    return tf


def _tf_count_bar(mode, vertical=False):
    def tf(g):
        sp = _split(g)
        if sp is None:
            return None
        key, field, idx = sp
        ks, kc = _key_shape(key)
        if ks is None:
            return None
        n = len(_matches(field, mode, ks, kc))
        if n == 0:
            return None
        if vertical:
            return [[kc, 0] for _ in range(n)]
        return [[kc] * n, [0] * n]
    return tf


def _tf_count_square(mode):
    def tf(g):
        sp = _split(g)
        if sp is None:
            return None
        key, field, idx = sp
        ks, kc = _key_shape(key)
        if ks is None:
            return None
        n = len(_matches(field, mode, ks, kc))
        if n == 0:
            return None
        return [[kc] * n + [0] for _ in range(n)]
    return tf


def _tf_crop(mode, which):
    def tf(g):
        sp = _split(g)
        if sp is None:
            return None
        key, field, idx = sp
        ks, kc = _key_shape(key)
        if ks is None:
            return None
        ms = _matches(field, mode, ks, kc)
        if not ms:
            return None
        if which == "union":
            boxes = [bbox(c) for c in ms]
            r0 = min(b[0] for b in boxes); c0 = min(b[1] for b in boxes)
            r1 = max(b[2] for b in boxes); c1 = max(b[3] for b in boxes)
        else:
            ms.sort(key=lambda comp: (min(r for r, _ in comp), min(c for _, c in comp)))
            chosen = ms[0] if which == "first" else ms[-1]
            r0, c0, r1, c1 = bbox(chosen)
        out = crop(field, r0, c0, r1, c1)
        return out if out != g else out
    return tf


def _mk_gi(mode, **kw):
    def gi(rng):
        return _gen(rng, mode, **kw)
    return gi


# ---------- 1-10: highlight ----------
rule("highlight_exact_key_matches", "Every field occurrence of the key shape, same colour and orientation, is recoloured to mark 4.",
     _mk_gi("exact", big=True), _tf_highlight("exact"))
rule("highlight_matches_any_colour", "Every field shape matching the key's outline, in any colour, is recoloured to mark 4.",
     _mk_gi("anycolour"), _tf_highlight("anycolour"))
rule("highlight_matches_rotated", "Every field occurrence of the key shape rotated by any multiple of 90 degrees, same colour, is recoloured to mark 4.",
     _mk_gi("rot", big=True), _tf_highlight("rot"))
rule("highlight_matches_rotated_any_colour", "Every field shape matching a rotation of the key outline, in any colour, is recoloured to mark 4.",
     _mk_gi("rot_any"), _tf_highlight("rot_any"))
rule("highlight_matches_mirrored", "Every field occurrence of the key shape's mirror image, same colour, is recoloured to mark 4.",
     _mk_gi("refl", big=True), _tf_highlight("refl"))
rule("highlight_matches_mirrored_any_colour", "Every field shape matching the key outline mirrored, in any colour, is recoloured to mark 4.",
     _mk_gi("refl_any"), _tf_highlight("refl_any"))
rule("highlight_matches_any_orientation", "Every field occurrence of the key shape in any rotation or mirror image, same colour, is recoloured to mark 4.",
     _mk_gi("rotrefl", big=True), _tf_highlight("rotrefl"))
rule("highlight_matches_any_orientation_any_colour", "Every field shape matching the key outline in any rotation or mirror and any colour is recoloured to mark 4.",
     _mk_gi("rotrefl_any"), _tf_highlight("rotrefl_any"))
rule("highlight_matches_by_cell_count", "Every field shape with the same cell count as the key and the key's colour is recoloured to mark 4.",
     _mk_gi("size", big=True), _tf_highlight("size"))
rule("highlight_matches_by_cell_count_any_colour", "Every field shape with the same cell count as the key, any colour, is recoloured to mark 4.",
     _mk_gi("size_any"), _tf_highlight("size_any"))

# ---------- 11-15: recolour matches to the key's own colour ----------
rule("recolour_colour_matches_to_key_colour", "Every field shape matching the key's outline, whatever its own colour, is repainted the key's colour.",
     _mk_gi("anycolour", big=True), _tf_recolour_to_key("anycolour"))
rule("recolour_rotated_matches_to_key_colour", "Every field shape matching a rotation of the key outline, whatever its colour, is repainted the key's colour.",
     _mk_gi("rot_any"), _tf_recolour_to_key("rot_any"))
rule("recolour_mirrored_matches_to_key_colour", "Every field shape matching the key outline mirrored, whatever its colour, is repainted the key's colour.",
     _mk_gi("refl_any", big=True), _tf_recolour_to_key("refl_any"))
rule("recolour_any_orientation_matches_to_key_colour", "Every field shape matching the key outline in any rotation or mirror, whatever its colour, is repainted the key's colour.",
     _mk_gi("rotrefl_any"), _tf_recolour_to_key("rotrefl_any"))
rule("recolour_same_size_matches_to_key_colour", "Every field shape with the key's cell count, whatever its own colour, is repainted the key's colour.",
     _mk_gi("size_any", big=True), _tf_recolour_to_key("size_any"))

# ---------- 16-19: frame matches ----------
rule("frame_exact_matches", "A one-cell mark-4 frame is drawn just outside every exact occurrence of the key.",
     _mk_gi("exact"), _tf_frame("exact"))
rule("frame_matches_any_colour", "A one-cell mark-4 frame is drawn just outside every field shape matching the key's outline, in any colour.",
     _mk_gi("anycolour", big=True), _tf_frame("anycolour"))
rule("frame_rotated_matches", "A one-cell mark-4 frame is drawn just outside every rotated occurrence of the key, same colour.",
     _mk_gi("rot"), _tf_frame("rot"))
rule("frame_matches_any_orientation_any_colour", "A one-cell mark-4 frame is drawn just outside every field shape matching the key in any rotation, mirror, or colour.",
     _mk_gi("rotrefl_any", big=True), _tf_frame("rotrefl_any"))

# ---------- 20-22: erase the non-matches ----------
rule("erase_non_matching_objects", "Every field shape that is not an exact occurrence of the key is erased, leaving only the matches.",
     _mk_gi("exact", big=True), _tf_erase_others("exact"))
rule("erase_objects_not_matching_shape", "Every field shape whose outline does not match the key's, regardless of colour, is erased.",
     _mk_gi("anycolour"), _tf_erase_others("anycolour"))
rule("erase_objects_not_matching_cell_count", "Every field shape whose cell count differs from the key's is erased.",
     _mk_gi("size_any", big=True), _tf_erase_others("size_any"))

# ---------- 23-27: count as bar ----------
rule("count_exact_matches_as_row_bar", "Output a two-row bar whose top row, in the key's colour, is as long as the number of exact key occurrences in the field.",
     _mk_gi("exact"), _tf_count_bar("exact"))
rule("count_colour_matches_as_row_bar", "Output a two-row bar whose top row, in the key's colour, is as long as the number of field shapes matching the key's outline.",
     _mk_gi("anycolour", big=True), _tf_count_bar("anycolour"))
rule("count_rotated_matches_as_column_bar", "Output a two-column bar whose left column, in the key's colour, is as tall as the number of rotated key occurrences.",
     _mk_gi("rot"), _tf_count_bar("rot", vertical=True))
rule("count_any_orientation_matches_as_bar", "Output a two-row bar whose top row, in the key's colour, is as long as the number of field shapes matching the key in any rotation, mirror, or colour.",
     _mk_gi("rotrefl_any", big=True), _tf_count_bar("rotrefl_any"))
rule("count_same_size_matches_as_column_bar", "Output a two-column bar whose left column, in the key's colour, is as tall as the number of field shapes sharing the key's cell count.",
     _mk_gi("size_any"), _tf_count_bar("size_any", vertical=True))

# ---------- 28-29: count as square ----------
rule("count_matches_as_square", "Output a square block, side length equal to the number of exact key occurrences, in the key's colour, with one extra background column.",
     _mk_gi("exact", big=True), _tf_count_square("exact"))
rule("count_colour_matches_as_square", "Output a square block, side length equal to the number of field shapes matching the key's outline, in the key's colour, with one extra background column.",
     _mk_gi("anycolour"), _tf_count_square("anycolour"))

# ---------- 30-33: crop to matches ----------
rule("crop_to_first_exact_match", "Output the bounding box of the first exact key occurrence in the field, in reading order.",
     _mk_gi("exact", big=True), _tf_crop("exact", "first"))
rule("crop_to_last_exact_match", "Output the bounding box of the last exact key occurrence in the field, in reading order.",
     _mk_gi("exact"), _tf_crop("exact", "last"))
rule("crop_to_union_of_colour_matches", "Output the smallest box covering every field shape matching the key's outline, any colour.",
     _mk_gi("anycolour", big=True), _tf_crop("anycolour", "union"))
rule("crop_to_union_of_exact_matches", "Output the smallest box covering every exact occurrence of the key in the field.",
     _mk_gi("exact"), _tf_crop("exact", "union"))


# ---------- 34: odd one out (differs from the key by one cell, same colour) ----------
def _near_shape(rng, shape):
    cells_ = set(shape); cand = set()
    for r, c in cells_:
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nb = (r + dr, c + dc)
            if nb not in cells_:
                cand.add(nb)
    if not cand:
        return list(cells_)
    extra = rng.choice(sorted(cand)); cells_.add(extra)
    return list(_norm(cells_))


def gi_odd(rng):
    W = rng.randint(10, 20)
    shape = random_shape(rng, rng.randint(3, 6))
    sh_h = max(r for r, _ in shape) + 1; sh_w = max(c for _, c in shape) + 1
    if sh_w > W:
        return None
    kh = max(sh_h, 2); kcol = rng.choice(_palette(exclude=(SEP, MARK)))
    key = blank(kh, W)
    for r, c in shape:
        key[r][c] = kcol
    fh = rng.randint(8, 18)
    field = blank(fh, W); occupied = set()

    def fits(cells_, margin=1):
        if not all(0 <= r < fh and 0 <= c < W for r, c in cells_):
            return False
        exp = set()
        for r, c in cells_:
            for dr in (-margin, 0, margin):
                for dc in (-margin, 0, margin):
                    exp.add((r + dr, c + dc))
        return not (exp & occupied)

    def stamp(cells_, col):
        for r, c in cells_:
            field[r][c] = col; occupied.add((r, c))

    placed = 0
    for _ in range(90):
        if placed >= rng.randint(2, 4):
            break
        r0 = rng.randrange(fh); c0 = rng.randrange(W)
        cells_ = [(r0 + r, c0 + c) for r, c in shape]
        if fits(cells_):
            stamp(cells_, kcol); placed += 1
    if placed == 0:
        return None
    near = _near_shape(rng, shape)
    near_ok = False
    for _ in range(60):
        r0 = rng.randrange(fh); c0 = rng.randrange(W)
        cells_ = [(r0 + r, c0 + c) for r, c in near]
        if fits(cells_):
            stamp(cells_, kcol); near_ok = True; break
    if not near_ok:
        return None
    other = _palette(exclude=(SEP, MARK, kcol))
    n_d = rng.randint(1, 3); dplaced = 0
    for _ in range(90):
        if dplaced >= n_d:
            break
        dn = rng.randint(2, 7)
        dshape = random_shape(rng, dn); col = rng.choice(other)
        r0 = rng.randrange(fh); c0 = rng.randrange(W)
        cells_ = [(r0 + r, c0 + c) for r, c in dshape]
        if fits(cells_):
            stamp(cells_, col); dplaced += 1
    return [row[:] for row in key] + [[SEP] * W] + [row[:] for row in field]


def tf_odd(g):
    sp = _split(g)
    if sp is None:
        return None
    key, field, idx = sp
    ks, kc = _key_shape(key)
    if ks is None:
        return None
    out = copy(g); found = False
    for comp in _field_objs(field):
        s = _norm(comp); c = field[comp[0][0]][comp[0][1]]
        if c == kc and s != ks:
            for (r, cc) in comp:
                out[idx + 1 + r][cc] = MARK
            found = True
    return out if found and out != g else None


rule("mark_odd_one_out_near_match", "The one field shape sharing the key's colour but differing from it by a single cell is recoloured to mark 4.", gi_odd, tf_odd)


# ---------- 35-36: replace matches with a second key pattern ----------
def gi_replace2(rng, rotated=False):
    W = rng.randint(10, 20)
    shapeA = random_shape(rng, rng.randint(3, 5))
    shapeB = random_shape(rng, rng.randint(3, 5))
    hA = max(r for r, _ in shapeA) + 1; wA = max(c for _, c in shapeA) + 1
    hB = max(r for r, _ in shapeB) + 1; wB = max(c for _, c in shapeB) + 1
    if max(wA, wB) > W:
        return None
    cA, cB = colours(rng, 2, exclude=(0, SEP, MARK))
    key = blank(hA + hB, W)
    for r, c in shapeA:
        key[r][c] = cA
    for r, c in shapeB:
        key[hA + r][c] = cB
    fh = rng.randint(8, 18)
    field = blank(fh, W); occupied = set()

    def fits(cells_, margin=1):
        if not all(0 <= r < fh and 0 <= c < W for r, c in cells_):
            return False
        exp = set()
        for r, c in cells_:
            for dr in (-margin, 0, margin):
                for dc in (-margin, 0, margin):
                    exp.add((r + dr, c + dc))
        return not (exp & occupied)

    def stamp(cells_, col):
        for r, c in cells_:
            field[r][c] = col; occupied.add((r, c))

    placed = 0; n_o = rng.randint(2, 4)
    for _ in range(90):
        if placed >= n_o:
            break
        vs = list(rng.choice(_rots(shapeA))) if rotated else list(shapeA)
        r0 = rng.randrange(fh); c0 = rng.randrange(W)
        cells_ = [(r0 + r, c0 + c) for r, c in vs]
        if fits(cells_):
            stamp(cells_, cA); placed += 1
    if placed == 0:
        return None
    other = _palette(exclude=(SEP, MARK, cA, cB))
    n_d = rng.randint(1, 3); dplaced = 0
    for _ in range(90):
        if dplaced >= n_d:
            break
        dn = rng.randint(2, 7)
        if dn in (len(shapeA), len(shapeB)):
            continue
        dshape = random_shape(rng, dn); col = rng.choice(other) if other else cA
        r0 = rng.randrange(fh); c0 = rng.randrange(W)
        cells_ = [(r0 + r, c0 + c) for r, c in dshape]
        if fits(cells_):
            stamp(cells_, col); dplaced += 1
    return [row[:] for row in key] + [[SEP] * W] + [row[:] for row in field]


def _tf_replace2(rotated=False):
    def tf(g):
        sp = _split(g)
        if sp is None:
            return None
        key, field, idx = sp
        comps = components(key, lambda v: v != 0, conn8=False)
        if len(comps) != 2:
            return None
        comps.sort(key=lambda comp: min(r for r, _ in comp))
        compA, compB = comps[0], comps[1]
        colA = key[compA[0][0]][compA[0][1]]; colB = key[compB[0][0]][compB[0][1]]
        shapeA = _norm(compA); shapeB = list(_norm(compB))
        targets = _rots(shapeA) if rotated else [shapeA]
        out = copy(g); changed = False
        for comp in _field_objs(field):
            s = _norm(comp); c = field[comp[0][0]][comp[0][1]]
            if c == colA and s in targets:
                r0 = min(r for r, _ in comp); c0 = min(cc for _, cc in comp)
                r1 = max(r for r, _ in comp); c1 = max(cc for _, cc in comp)
                for r in range(r0, r1 + 1):
                    for cc in range(c0, c1 + 1):
                        out[idx + 1 + r][cc] = 0
                for (r, cc) in shapeB:
                    rr, ccc = idx + 1 + r0 + r, c0 + cc
                    if 0 <= rr < len(out) and 0 <= ccc < len(out[0]):
                        out[rr][ccc] = colB
                changed = True
        return out if changed and out != g else None
    return tf


rule("replace_matches_with_second_key_pattern",
     "Every field occurrence of the key's first shape is erased and replaced, anchored at its top-left corner, with the key's second shape.",
     lambda rng: gi_replace2(rng, rotated=False), _tf_replace2(rotated=False))
rule("replace_rotated_matches_with_second_key_pattern",
     "Every field shape matching any rotation of the key's first shape is erased and replaced, anchored at its top-left corner, with the key's second shape.",
     lambda rng: gi_replace2(rng, rotated=True), _tf_replace2(rotated=True))


# ---------- 37-38: shift matches one cell ----------
def _tf_shift(dr, dc):
    def tf(g):
        sp = _split(g)
        if sp is None:
            return None
        key, field, idx = sp
        ks, kc = _key_shape(key)
        if ks is None:
            return None
        ms = _matches(field, "exact", ks, kc)
        if not ms:
            return None
        out = copy(g); H, W = dims(out)
        for comp in ms:
            for (r, c) in comp:
                out[idx + 1 + r][c] = 0
        for comp in ms:
            for (r, c) in comp:
                rr, cc = idx + 1 + r + dr, c + dc
                if idx + 1 <= rr < H and 0 <= cc < W:
                    out[rr][cc] = kc
        return out if out != g else None
    return tf


rule("shift_matches_one_right", "Every exact occurrence of the key in the field slides one cell to the right.",
     _mk_gi("exact", big=True), _tf_shift(0, 1))
rule("shift_matches_one_down", "Every exact occurrence of the key in the field slides one cell down.",
     _mk_gi("exact"), _tf_shift(1, 0))


# ---------- 39: the field row containing the key's colour sequence ----------
def gi_row_seq(rng, big=False):
    L = rng.randint(3, 6)
    pal = _palette(exclude=(SEP,))
    seq = [rng.choice(pal) for _ in range(L)]
    W = rng.randint(21, 30) if big else rng.randint(max(L + 4, 10), 20)
    key = [[0] * W]
    for i, v in enumerate(seq):
        key[0][i] = v
    fh = rng.randint(6, 16)
    field = [[rng.choice(pal) for _ in range(W)] for _ in range(fh)]
    r_match = rng.randrange(fh); c_off = rng.randrange(0, W - L + 1)
    for i, v in enumerate(seq):
        field[r_match][c_off + i] = v
    matches = []
    for r, row in enumerate(field):
        for c in range(len(row) - L + 1):
            if row[c:c + L] == seq:
                matches.append(r); break
    if len(matches) != 1:
        return None
    return key + [[SEP] * W] + field


def tf_row_seq(g):
    sp = _split(g)
    if sp is None:
        return None
    key, field, idx = sp
    seq = [v for v in key[0] if v != 0]
    if not seq:
        return None
    L = len(seq); matches = []
    for r, row in enumerate(field):
        for c in range(len(row) - L + 1):
            if row[c:c + L] == seq:
                matches.append(r); break
    if len(matches) != 1:
        return None
    return [field[matches[0]][:]]


rule("row_containing_key_sequence", "Output, as a single row, the one field row that contains the key's colour sequence as a contiguous run.",
     lambda rng: gi_row_seq(rng, big=True), tf_row_seq)


# ---------- 40: the field column containing the key's colour sequence ----------
def gi_col_seq(rng):
    L = rng.randint(3, 6)
    pal = _palette(exclude=(SEP,))
    seq = [rng.choice(pal) for _ in range(L)]
    H = rng.randint(max(L + 4, 10), 18)
    W = rng.randint(6, 14)
    key = blank(L, W)
    for i, v in enumerate(seq):
        key[i][0] = v
    field = blank(H, W)
    for c in range(W):
        for r in range(H):
            field[r][c] = rng.choice(pal)
    c_match = rng.randrange(W); r_off = rng.randrange(0, H - L + 1)
    for i, v in enumerate(seq):
        field[r_off + i][c_match] = v

    def col_of(c):
        return [field[r][c] for r in range(H)]

    matches = []
    for c in range(W):
        col = col_of(c)
        for r in range(H - L + 1):
            if col[r:r + L] == seq:
                matches.append(c); break
    if len(matches) != 1:
        return None
    return key + [[SEP] * W] + field


def tf_col_seq(g):
    sp = _split(g)
    if sp is None:
        return None
    key, field, idx = sp
    seq = [key[r][0] for r in range(len(key)) if key[r][0] != 0]
    if not seq:
        return None
    L = len(seq); H = len(field); W = len(field[0])
    matches = []
    for c in range(W):
        col = [field[r][c] for r in range(H)]
        for r in range(H - L + 1):
            if col[r:r + L] == seq:
                matches.append(c); break
    if len(matches) != 1:
        return None
    c = matches[0]
    return [[field[r][c]] for r in range(H)]


rule("column_matching_key_sequence", "Output, as a single column, the one field column that contains the key's colour sequence as a contiguous run.", gi_col_seq, tf_col_seq)
