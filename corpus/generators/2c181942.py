# Rule authored from the evaluation demonstrations of 2c181942.
#
# One component holds SEVERAL colours — the core — and carries a two-cell ARM of a different colour
# on each side. Every other component is a single-colour shape. A shape whose colour matches an arm
# TRAVELS to that arm and docks against it; a shape matching no arm is DELETED.
#
# The shape is re-oriented to dock. Of the eight rotations and reflections, the one that fits is the
# one whose contact line lands exactly on the arm's own cells — that constraint picks a single
# orientation, so nothing here is a guess about which way round a shape should go.
from collections import Counter


def _components(grid, bg):
    h, w = len(grid), len(grid[0])
    seen, out = set(), []
    for r in range(h):
        for c in range(w):
            if grid[r][c] == bg or (r, c) in seen:
                continue
            stack, comp = [(r, c)], []
            seen.add((r, c))
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if (0 <= ny < h and 0 <= nx < w and (ny, nx) not in seen
                                and grid[ny][nx] != bg):
                            seen.add((ny, nx))
                            stack.append((ny, nx))
            out.append(comp)
    return out


def _mask(grid, comp):
    r0 = min(r for r, _ in comp)
    c0 = min(c for _, c in comp)
    r1 = max(r for r, _ in comp)
    c1 = max(c for _, c in comp)
    m = [[None] * (c1 - c0 + 1) for _ in range(r1 - r0 + 1)]
    for r, c in comp:
        m[r - r0][c - c0] = grid[r][c]
    return m, r0, c0


def _orients(m):
    """All eight rotations and reflections.

    The rotation is NOT fixed: demo 0's 3-shape docks as a clockwise quarter turn and demo 1's
    1-shape docks as a counter-clockwise one, so committing to either loses a demo. What picks the
    answer is the contact line matching the arm, plus — where several orientations still match —
    the one that protrudes LEAST from the core. The untransformed shape always matches at some
    offset and always sticks out further, which is exactly the false positive to exclude.
    """
    def rot(a):
        return [list(row) for row in zip(*a[::-1])]
    out, cur = [], m
    for _ in range(4):
        out.append(cur)
        out.append([row[::-1] for row in cur])
        cur = rot(cur)
    return out


def transform(grid):
    h, w = len(grid), len(grid[0])
    bg = Counter(v for row in grid for v in row).most_common(1)[0][0]
    comps = _components(grid, bg)

    core = next((c for c in comps if len({grid[r][x] for r, x in c}) > 1), None)
    if core is None:
        return [row[:] for row in grid]

    cm, cr0, cc0 = _mask(grid, core)
    ch_, cw_ = len(cm), len(cm[0])

    # each side's arm: the cells of the core sitting on that edge, and their colour
    arms = {}
    for side, cells in (
            ("top", [(0, c) for c in range(cw_) if cm[0][c] is not None]),
            ("bottom", [(ch_ - 1, c) for c in range(cw_) if cm[ch_ - 1][c] is not None]),
            ("left", [(r, 0) for r in range(ch_) if cm[r][0] is not None]),
            ("right", [(r, cw_ - 1) for r in range(ch_) if cm[r][cw_ - 1] is not None])):
        if cells:
            arms[side] = ({cm[r][c] for r, c in cells}.pop(), cells)

    out = [[bg] * w for _ in range(h)]
    for r, c in core:
        out[r][c] = grid[r][c]

    for comp in comps:
        if comp is core:
            continue
        colour = grid[comp[0][0]][comp[0][1]]
        side = next((s for s, (col, _) in arms.items() if col == colour), None)
        if side is None:
            continue                                  # no matching arm: the shape is deleted
        m, _, _ = _mask(grid, comp)
        _, acells = arms[side]

        # THE SHAPE NEED NOT SPAN THE CORE. Demo 2 docks a 4x2 shape onto a 4-wide core, so
        # requiring equal extent rejected every orientation and dropped two shapes silently. What
        # actually pins the fit is the CONTACT LINE: the cells of the shape that touch the core
        # must sit on exactly the arm's own cells. Orientation and offset are searched together
        # and the constraint leaves one answer.
        arm_rows = {cr0 + r for r, _ in acells}
        arm_cols = {cc0 + c for _, c in acells}
        cands = []
        for om in _orients(m):
            oh, ow = len(om), len(om[0])
            if side in ("left", "right"):
                contact = ow - 1 if side == "left" else 0
                c0 = cc0 - ow if side == "left" else cc0 + cw_
                for r0 in range(cr0 - oh, cr0 + ch_ + 1):
                    if {r0 + r for r in range(oh) if om[r][contact] is not None} == arm_rows:
                        cands.append((ow, r0, c0, om))
                        break
            else:
                contact = oh - 1 if side == "top" else 0
                r0 = cr0 - oh if side == "top" else cr0 + ch_
                for c0 in range(cc0 - ow, cc0 + cw_ + 1):
                    if {c0 + c for c in range(ow) if om[contact][c] is not None} == arm_cols:
                        cands.append((oh, r0, c0, om))
                        break
        placed = min(cands, key=lambda t: t[0])[1:] if cands else None
        if not placed:
            continue
        r0, c0, om = placed
        for r in range(len(om)):
            for c in range(len(om[0])):
                if om[r][c] is not None and 0 <= r0 + r < h and 0 <= c0 + c < w:
                    out[r0 + r][c0 + c] = om[r][c]
    return out
