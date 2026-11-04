# Rule authored from the evaluation demonstrations of 195c6913.
#
# A SAMPLE near the top-left lists a repeating unit as contiguous blocks — one colour per block.
# Edge cells of the unit's first colour are EMITTERS. Each emitter sends a ray through the corridor,
# painting the unit in order and continuing the count across turns.
#
# When the ray is blocked it drops a TERMINATOR on the blocking cell and turns perpendicular,
# choosing the direction with the LONGER open run — at the first turn of demo 1 both ways are open,
# eleven cells up against four down, and it goes up. The ray stops when both perpendicular runs are
# empty, and simply ends when it leaves the grid.
from collections import Counter


def _blocks(row, bg):
    out, cur = [], None
    for v in row:
        if v == bg:
            cur = None
        elif cur != v:
            out.append(v)
            cur = v
    return out


def transform(grid):
    h, w = len(grid), len(grid[0])
    # TWO large colours, not one. The corridor the ray travels is more common than the FIELD the
    # sample sits in — 319 corridor cells against 292 field cells in demo 1 — so taking the most
    # common colour as background made the corridor the background and painted 407 cells of noise.
    # The field is the colour the grid opens with; the corridor is the other big one.
    bg = grid[0][0]
    out = [row[:] for row in grid]

    # components of every non-background colour
    seen, comps = set(), []
    for r in range(h):
        for c in range(w):
            if grid[r][c] == bg or (r, c) in seen:
                continue
            v = grid[r][c]
            stack, cur = [(r, c)], []
            seen.add((r, c))
            while stack:
                y, x = stack.pop()
                cur.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if (0 <= ny < h and 0 <= nx < w and (ny, nx) not in seen
                                and grid[ny][nx] == v):
                            seen.add((ny, nx))
                            stack.append((ny, nx))
            comps.append((v, cur))

    corridor = Counter(v for r in grid for v in r if v != bg).most_common(1)[0][0]
    # the corridor is not a marking; it is the medium the ray travels through
    comps = [(v, cur) for v, cur in comps if v != corridor]
    singles = [(v, cur[0]) for v, cur in comps if len(cur) == 1]
    blocks = [(v, cur) for v, cur in comps if len(cur) > 1]
    if not blocks:
        return out

    # the sample band: the row holding the most distinct block colours
    rowscore = {}
    for v, cur in blocks:
        for r, _ in cur:
            rowscore.setdefault(r, set()).add(v)
    sample_row = max(rowscore, key=lambda r: (len(rowscore[r]), -r))
    unit = [v for v in _blocks(grid[sample_row], bg) if v != corridor]
    if len(unit) < 2:
        return out
    sample_cols = {c for v, cur in blocks for r, c in cur if r in rowscore
                   and v in unit and r == sample_row}

    term = next((v for v, cur in blocks if v not in unit), None)
    emitters = [(v, p) for v, p in singles if v == unit[0]]
    if not emitters:
        emitters = [(v, p) for v, p in singles]

    # clear the sample and the terminator's own block
    for v, cur in blocks:
        if v in unit or v == term:
            for r, c in cur:
                out[r][c] = bg

    for v, (er, ec) in emitters:
        r, c = er, ec
        dr, dc = (0, 1) if ec == 0 else (0, -1) if ec == w - 1 else (1, 0) if er == 0 else (-1, 0)
        k = 0
        last_h = dc or None
        last_v = dr or None
        out[r][c] = unit[0]
        guard = 0
        while guard < 4 * h * w:
            guard += 1
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == corridor:
                r, c, k = nr, nc, k + 1
                out[r][c] = unit[k % len(unit)]
                continue
            if not (0 <= nr < h and 0 <= nc < w):
                break            # ran off the grid: the ray ends, no terminator and no turn
            if term is not None:
                out[nr][nc] = term
            best = None
            # THE RAY NEVER REVERSES. Once it has travelled right it only ever travels right
            # again; once it has gone up it only goes up. That is what separates demo 1's second
            # ray — which stops beside a long open row because entering it would mean doubling
            # back — from test 0, which steps into a single open cell because a forward run opens
            # from there. Length alone gets one of the two wrong whichever way it is set.
            def run_len(y, x, ddr, ddc):
                n = 0
                yy, xx = y + ddr, x + ddc
                while 0 <= yy < h and 0 <= xx < w and grid[yy][xx] == corridor:
                    n += 1
                    yy, xx = yy + ddr, xx + ddc
                return n

            def allowed(ddr, ddc):
                if ddc and last_h is not None and ddc != last_h:
                    return False
                if ddr and last_v is not None and ddr != last_v:
                    return False
                return True

            best = None
            for ndr, ndc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                if (ndr, ndc) in ((dr, dc), (-dr, -dc)) or not allowed(ndr, ndc):
                    continue
                n = run_len(r, c, ndr, ndc)
                if n == 0:
                    continue
                ey, ex = r + n * ndr, c + n * ndc
                onward = any(run_len(ey, ex, a, b) for a, b in
                             ((-1, 0), (1, 0), (0, -1), (0, 1))
                             if (a, b) not in ((ndr, ndc), (-ndr, -ndc)) and allowed(a, b))
                if n == 1 and not onward:
                    continue
                if best is None or n > best[0]:
                    best = (n, ndr, ndc)
            if best is None:
                break
            dr, dc = best[1], best[2]
            if dc:
                last_h = dc
            if dr:
                last_v = dr
    return out
