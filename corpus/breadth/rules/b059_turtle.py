# b059_turtle.py -- PATHS DRAWN FROM INSTRUCTION SEQUENCES. A row of instruction cells sits above a
# separator row; colour values in that row encode moves (digits=True everywhere here: colour IS a move
# code, never a decoration). A turtle starts at a marker cell below the separator and steps once per
# instruction, drawing the cells it visits. Every rule below states its own encoding and its own stop
# rule in its one-sentence description, per AUTHORING.md's G8 gate.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import rule
from glib import *

MOVE = {1: (-1, 0), 2: (0, 1), 3: (1, 0), 4: (0, -1)}   # 1 up, 2 right, 3 down, 4 left
SEP = 8          # separator row colour, fixed
CANVAS_R0 = 2    # canvas starts below instruction row (0) and separator row (1)


def _canvas(rng, lo=10, hi=30, L_lo=3, L_hi=9):
    H = rng.randint(lo, hi); W = rng.randint(lo, hi)
    L = rng.randint(L_lo, min(L_hi, W))
    g = blank(H, W)
    instr = [rng.randint(1, 4) for _ in range(L)]
    for i, v in enumerate(instr):
        g[0][i] = v
    for c in range(W):
        g[1][c] = SEP
    return g, H, W, instr


def _read_instr(g):
    out = []
    for v in g[0]:
        if v in (1, 2, 3, 4):
            out.append(v)
        else:
            break
    return out


def _run_length_instr(g):
    """Consecutive equal cells in row 0 collapse to one (direction, run-length) pair."""
    raw = _read_instr(g)
    out, i = [], 0
    while i < len(raw):
        j = i
        while j < len(raw) and raw[j] == raw[i]:
            j += 1
        out.append((raw[i], j - i)); i = j
    return out


def _find(g, colour, r_from=CANVAS_R0):
    for r in range(r_from, len(g)):
        for c in range(len(g[0])):
            if g[r][c] == colour:
                return (r, c)
    return None


def _inb(r, c, H, W):
    return CANVAS_R0 <= r < H and 0 <= c < W


def _wrap(r, c, H, W):
    return CANVAS_R0 + (r - CANVAS_R0) % (H - CANVAS_R0), c % W


def _walk(moves, start, H, W, stop, obstacles=None):
    """moves: list of (dr,dc). Returns list of visited cells (excl. start) in order."""
    obstacles = obstacles or set()
    r, c = start; visited = []
    for dr, dc in moves:
        nr, nc = r + dr, c + dc
        if stop == "wrap":
            nr, nc = _wrap(nr, nc, H, W)
        elif not _inb(nr, nc, H, W):
            break
        if (nr, nc) in obstacles:
            break
        r, c = nr, nc
        visited.append((r, c))
    return visited


def _margin_ok(r0, c0, L, H, W):
    return r0 - CANVAS_R0 >= L and H - 1 - r0 >= L and c0 >= L and W - 1 - c0 >= L


# ---------- 1 basic direct-digit, wall stop, fixed path colour ----------
def gi_wall(rng):
    g, H, W, instr = _canvas(rng, 10, 30, 3, 9)
    r0, c0 = rng.randint(CANVAS_R0, H - 1), rng.randint(0, W - 1)
    g[r0][c0] = 6
    return g
def tf_wall(g):
    instr = _read_instr(g); start = _find(g, 6)
    if not instr or not start: return None
    H, W = dims(g)
    vis = _walk([MOVE[v] for v in instr], start, H, W, "wall")
    if not vis: return None
    out = copy(g)
    for r, c in vis: out[r][c] = 9
    return out
rule("turtle_direct_digit_wall_stop",
     "Row 0 (colour 1=up,2=right,3=down,4=left) read left to right is a move list for the turtle starting at the colour-6 marker below the colour-8 separator; it steps once per instruction, drawing each visited cell colour 9, and stops permanently the instant a step would leave the canvas.",
     gi_wall, tf_wall, digits=True)


# ---------- 2 direct-digit, instruction-end stop only (margin guaranteed so the wall is never hit) ----------
def gi_endstop(rng):
    for _ in range(30):
        g, H, W, instr = _canvas(rng, 12, 30, 3, 6)
        r0 = rng.randint(CANVAS_R0, H - 1); c0 = rng.randint(0, W - 1)
        if _margin_ok(r0, c0, len(instr), H, W):
            g[r0][c0] = 6; return g
    return None
def tf_endstop(g):
    instr = _read_instr(g); start = _find(g, 6)
    if not instr or not start: return None
    H, W = dims(g)
    r, c = start; out = copy(g)
    for v in instr:
        dr, dc = MOVE[v]; r, c = r + dr, c + dc
        out[r][c] = 9
    return out if (r, c) != start else None
rule("turtle_direct_digit_instruction_end_stop",
     "Row 0 (1=up,2=right,3=down,4=left) is a move list for the colour-6 turtle below the colour-8 separator; it draws colour 9 on every visited cell and only stops when the instruction list runs out (inputs are built with enough margin that no wall is ever hit).",
     gi_endstop, tf_endstop, digits=True)


# ---------- 3 wrap around edges ----------
def gi_wrap(rng):
    g, H, W, instr = _canvas(rng, 10, 30, 4, 10)
    r0, c0 = rng.randint(CANVAS_R0, H - 1), rng.randint(0, W - 1)
    g[r0][c0] = 6
    return g
def tf_wrap(g):
    instr = _read_instr(g); start = _find(g, 6)
    if not instr or not start: return None
    H, W = dims(g)
    vis = _walk([MOVE[v] for v in instr], start, H, W, "wrap")
    if not vis: return None
    out = copy(g)
    for r, c in vis: out[r][c] = 9
    return out
rule("turtle_direct_digit_wrap_edges",
     "Row 0 (1=up,2=right,3=down,4=left) is a move list for the colour-6 turtle below the colour-8 separator; it draws colour 9 at every visited cell and, instead of stopping at an edge, wraps to the opposite side of the canvas, running the full instruction list.",
     gi_wrap, tf_wrap, digits=True)


# ---------- 4 obstacle stop ----------
def gi_obstacle(rng):
    g, H, W, instr = _canvas(rng, 10, 30, 4, 10)
    r0, c0 = rng.randint(CANVAS_R0, H - 1), rng.randint(0, W - 1)
    g[r0][c0] = 6
    free = [(r, c) for r in range(CANVAS_R0, H) for c in range(W) if g[r][c] == 0 and (r, c) != (r0, c0)]
    if not free: return None
    for r, c in rng.sample(free, min(rng.randint(1, 4), len(free))):
        g[r][c] = 5
    return g
def tf_obstacle(g):
    instr = _read_instr(g); start = _find(g, 6)
    if not instr or not start: return None
    H, W = dims(g)
    obst = {(r, c) for r in range(H) for c in range(W) if g[r][c] == 5}
    vis = _walk([MOVE[v] for v in instr], start, H, W, "wall", obstacles=obst)
    if not vis: return None
    out = copy(g)
    for r, c in vis: out[r][c] = 9
    return out
rule("turtle_direct_digit_obstacle_stop",
     "Row 0 (1=up,2=right,3=down,4=left) is a move list for the colour-6 turtle below the colour-8 separator; it draws colour 9 at every visited cell and stops the instant a step would leave the canvas or land on a colour-5 obstacle.",
     gi_obstacle, tf_obstacle, digits=True)


# ---------- 5 end cell marked ----------
def gi_endmark(rng):
    return gi_wall(rng)
def tf_endmark(g):
    instr = _read_instr(g); start = _find(g, 6)
    if not instr or not start: return None
    H, W = dims(g)
    vis = _walk([MOVE[v] for v in instr], start, H, W, "wall")
    if not vis: return None
    out = copy(g)
    for r, c in vis: out[r][c] = 9
    er, ec = vis[-1]; out[er][ec] = 7
    return out
rule("turtle_direct_digit_end_marked",
     "Row 0 (1=up,2=right,3=down,4=left) is a move list for the colour-6 turtle below the colour-8 separator; it stops the instant a step would leave the canvas, draws every visited cell colour 9 except the final resting cell, which is marked colour 7.",
     gi_endmark, tf_endmark, digits=True)


# ---------- 6 per-instruction colour path ----------
def gi_percolour(rng):
    return gi_wall(rng)
def tf_percolour(g):
    instr = _read_instr(g); start = _find(g, 6)
    if not instr or not start: return None
    H, W = dims(g)
    r, c = start; out = copy(g); moved = False
    for v in instr:
        dr, dc = MOVE[v]; nr, nc = r + dr, c + dc
        if not _inb(nr, nc, H, W): break
        r, c = nr, nc; out[r][c] = v; moved = True
    return out if moved else None
rule("turtle_direct_digit_per_instruction_colour",
     "Row 0 (1=up,2=right,3=down,4=left) is a move list for the colour-6 turtle below the colour-8 separator; each visited cell is painted the same colour as the instruction that produced the step, and the turtle stops the instant a step would leave the canvas.",
     gi_percolour, tf_percolour, digits=True)


# ---------- 7 dotted trail every second step ----------
def gi_dotted(rng):
    return gi_wall(rng)
def tf_dotted(g):
    instr = _read_instr(g); start = _find(g, 6)
    if not instr or not start: return None
    H, W = dims(g)
    vis = _walk([MOVE[v] for v in instr], start, H, W, "wall")
    if len(vis) < 2: return None
    out = copy(g)
    for i, (r, c) in enumerate(vis):
        if i % 2 == 1: out[r][c] = 9
    return out
rule("turtle_direct_digit_dotted_every_second_step",
     "Row 0 (1=up,2=right,3=down,4=left) is a move list for the colour-6 turtle below the colour-8 separator; it stops the instant a step would leave the canvas and marks colour 9 only on every second visited cell (steps 2, 4, 6, ...), leaving the odd steps blank.",
     gi_dotted, tf_dotted, digits=True)


# ---------- 8 two markers, same instructions, both stop at wall ----------
def gi_two_same(rng):
    g, H, W, instr = _canvas(rng, 12, 30, 3, 8)
    pts = rng.sample([(r, c) for r in range(CANVAS_R0, H) for c in range(W)], 2)
    g[pts[0][0]][pts[0][1]] = 6; g[pts[1][0]][pts[1][1]] = 5
    return g
def tf_two_same(g):
    instr = _read_instr(g); s1 = _find(g, 6); s2 = _find(g, 5)
    if not instr or not s1 or not s2: return None
    H, W = dims(g)
    v1 = _walk([MOVE[v] for v in instr], s1, H, W, "wall")
    v2 = _walk([MOVE[v] for v in instr], s2, H, W, "wall")
    if not v1 and not v2: return None
    out = copy(g)
    for r, c in v1: out[r][c] = 9
    for r, c in v2: out[r][c] = 7
    return out
rule("turtle_two_markers_same_instructions",
     "Row 0 (1=up,2=right,3=down,4=left) is one move list applied independently to two turtles, the colour-6 marker (path drawn colour 9) and the colour-5 marker (path drawn colour 7), each below the shared colour-8 separator; each turtle stops the instant its own step would leave the canvas.",
     gi_two_same, tf_two_same, digits=True)


# ---------- 9 second marker reads instructions right to left ----------
def gi_two_rev(rng):
    return gi_two_same(rng)
def tf_two_rev(g):
    instr = _read_instr(g); s1 = _find(g, 6); s2 = _find(g, 5)
    if not instr or not s1 or not s2: return None
    H, W = dims(g)
    v1 = _walk([MOVE[v] for v in instr], s1, H, W, "wall")
    v2 = _walk([MOVE[v] for v in reversed(instr)], s2, H, W, "wall")
    if not v1 and not v2: return None
    out = copy(g)
    for r, c in v1: out[r][c] = 9
    for r, c in v2: out[r][c] = 7
    return out
rule("turtle_second_marker_reads_instructions_reversed",
     "Row 0 (1=up,2=right,3=down,4=left) is the move list; the colour-6 marker reads it left to right (path colour 9) while the colour-5 marker reads the same row right to left (path colour 7), both below the colour-8 separator, each stopping the instant its own step would leave the canvas.",
     gi_two_rev, tf_two_rev, digits=True)


# ---------- 10 mirrored left/right when marker on right half ----------
def gi_mirror(rng):
    return gi_wall(rng)
def tf_mirror(g):
    instr = _read_instr(g); start = _find(g, 6)
    if not instr or not start: return None
    H, W = dims(g)
    if start[1] >= W // 2:
        instr = [{1: 1, 2: 4, 3: 3, 4: 2}[v] for v in instr]
    vis = _walk([MOVE[v] for v in instr], start, H, W, "wall")
    if not vis: return None
    out = copy(g)
    for r, c in vis: out[r][c] = 9
    return out
rule("turtle_mirrored_on_right_half",
     "Row 0 (1=up,2=right,3=down,4=left) is the move list for the colour-6 turtle below the colour-8 separator; if the marker sits in the right half of the canvas the left/right instructions (2 and 4) are swapped before walking, the path is drawn colour 9, and the turtle stops the instant a step would leave the canvas.",
     gi_mirror, tf_mirror, digits=True)


# ---------- 11 repeat instructions k times, k = corner digit ----------
def gi_repeat(rng):
    for _ in range(30):
        g, H, W, instr = _canvas(rng, 12, 30, 3, 6)
        r0 = rng.randint(CANVAS_R0, H - 1); c0 = rng.randint(0, W - 1)
        k = rng.randint(1, 3)
        if _margin_ok(r0, c0, len(instr) * k, H, W) and (r0, c0) != (H - 1, W - 1):
            g[r0][c0] = 6; g[H - 1][W - 1] = k
            return g
    return None
def tf_repeat(g):
    instr = _read_instr(g); start = _find(g, 6)
    H, W = dims(g)
    k = g[H - 1][W - 1]
    if not instr or not start or not (1 <= k <= 9): return None
    moves = [MOVE[v] for v in instr] * k
    vis = _walk(moves, start, H, W, "wall")
    if not vis: return None
    out = copy(g)
    for r, c in vis: out[r][c] = 9
    return out
rule("turtle_repeat_sequence_corner_digit",
     "Row 0 (1=up,2=right,3=down,4=left) is a move list the colour-6 turtle below the colour-8 separator repeats k times in order, where k is the digit stored in the canvas's bottom-right corner cell; the path is drawn colour 9 and the turtle stops the instant a step would leave the canvas.",
     gi_repeat, tf_repeat, digits=True)


# ---------- 12 run-length instructions ----------
def gi_runlen(rng):
    g, H, W, _ = _canvas(rng, 12, 30, 4, 10)
    # overwrite row 0 with runs: pick a few (direction,count) pairs and lay them out
    runs = []
    total = 0
    while total < len(g[0]) and len(runs) < 6:
        d = rng.randint(1, 4); n = rng.randint(1, 3)
        if total + n > len(g[0]): break
        runs.append((d, n)); total += n
    for i in range(len(g[0])): g[0][i] = 0
    i = 0
    for d, n in runs:
        for _ in range(n): g[0][i] = d; i += 1
    r0, c0 = rng.randint(CANVAS_R0, H - 1), rng.randint(0, W - 1)
    g[r0][c0] = 6
    return g if runs else None
def tf_runlen(g):
    runs = _run_length_instr(g); start = _find(g, 6)
    if not runs or not start: return None
    H, W = dims(g)
    moves = [MOVE[d] for d, n in runs for _ in range(n)]
    vis = _walk(moves, start, H, W, "wall")
    if not vis: return None
    out = copy(g)
    for r, c in vis: out[r][c] = 9
    return out
rule("turtle_run_length_instructions",
     "Row 0 above the colour-8 separator holds direction codes (1=up,2=right,3=down,4=left) in runs; each run of n equal cells means move n steps in that direction, applied in order to the colour-6 turtle; the path is drawn colour 9 and the turtle stops the instant a step would leave the canvas.",
     gi_runlen, tf_runlen, digits=True)


# ---------- 13 turn-based encoding, wall stop ----------
def gi_turn(rng):
    H = rng.randint(12, 30); W = rng.randint(12, 30)
    L = rng.randint(5, min(12, W))
    g = blank(H, W)
    for i in range(L):
        g[0][i] = 5 if rng.random() < 0.35 else 3
    for c in range(W): g[1][c] = SEP
    r0, c0 = rng.randint(CANVAS_R0, H - 1), rng.randint(0, W - 1)
    g[r0][c0] = 6
    return g
def tf_turn(g):
    codes = []
    for v in g[0]:
        if v in (5, 3): codes.append(v)
        else: break
    start = _find(g, 6)
    if not codes or not start: return None
    H, W = dims(g)
    heading = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # right, down, left, up (clockwise)
    hi = 0; r, c = start; out = copy(g); moved = False
    for code in codes:
        if code == 5:
            hi = (hi + 1) % 4
        else:
            dr, dc = heading[hi]; nr, nc = r + dr, c + dc
            if not _inb(nr, nc, H, W): break
            r, c = nr, nc; out[r][c] = 9; moved = True
    return out if moved else None
rule("turtle_turn_based_grey_right_wall_stop",
     "Row 0 above the colour-8 separator is a turn program for the colour-6 turtle, initially heading right: colour 5 (grey) turns the turtle 90 degrees clockwise in place, colour 3 steps it one cell forward in its current heading; steps are drawn colour 9 and the turtle stops permanently the instant a step would leave the canvas.",
     gi_turn, tf_turn, digits=True)


# ---------- 14 turn-based, wrap ----------
def gi_turnwrap(rng):
    return gi_turn(rng)
def tf_turnwrap(g):
    codes = []
    for v in g[0]:
        if v in (5, 3): codes.append(v)
        else: break
    start = _find(g, 6)
    if not codes or not start: return None
    H, W = dims(g)
    heading = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    hi = 0; r, c = start; out = copy(g); moved = False
    for code in codes:
        if code == 5:
            hi = (hi + 1) % 4
        else:
            dr, dc = heading[hi]; r, c = _wrap(r + dr, c + dc, H, W); out[r][c] = 9; moved = True
    return out if moved else None
rule("turtle_turn_based_grey_right_wrap",
     "Row 0 above the colour-8 separator is a turn program for the colour-6 turtle, initially heading right: colour 5 (grey) turns it 90 degrees clockwise in place, colour 3 steps it one cell forward in its current heading; steps are drawn colour 9 and, instead of stopping, the turtle wraps to the opposite edge of the canvas and runs the whole program.",
     gi_turnwrap, tf_turnwrap, digits=True)


# ---------- 15 turn-based with obstacles ----------
def gi_turnobst(rng):
    g = gi_turn(rng)
    H, W = dims(g)
    start = _find(g, 6)
    free = [(r, c) for r in range(CANVAS_R0, H) for c in range(W) if g[r][c] == 0 and (r, c) != start]
    if not free: return g
    for r, c in rng.sample(free, min(rng.randint(1, 3), len(free))):
        g[r][c] = 7
    return g
def tf_turnobst(g):
    codes = []
    for v in g[0]:
        if v in (5, 3): codes.append(v)
        else: break
    start = _find(g, 6)
    if not codes or not start: return None
    H, W = dims(g)
    obst = {(r, c) for r in range(H) for c in range(W) if g[r][c] == 7}
    heading = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    hi = 0; r, c = start; out = copy(g); moved = False
    for code in codes:
        if code == 5:
            hi = (hi + 1) % 4
        else:
            dr, dc = heading[hi]; nr, nc = r + dr, c + dc
            if not _inb(nr, nc, H, W) or (nr, nc) in obst: break
            r, c = nr, nc; out[r][c] = 9; moved = True
    return out if moved else None
rule("turtle_turn_based_obstacle_stop",
     "Row 0 above the colour-8 separator is a turn program for the colour-6 turtle, initially heading right: colour 5 (grey) turns it 90 degrees clockwise in place, colour 3 steps it one cell forward in its current heading; steps are drawn colour 9 and the turtle stops permanently the instant a step would leave the canvas or land on a colour-7 obstacle.",
     gi_turnobst, tf_turnobst, digits=True)


# ---------- 16 closed rectangle perimeter, filled ----------
def gi_closed(rng):
    H = rng.randint(12, 30); W = rng.randint(12, 30)
    h = rng.randint(2, min(6, H - CANVAS_R0 - 4)); w = rng.randint(2, min(6, W - 6))
    g = blank(H, W)
    runs = [(2, w), (3, h), (4, w), (1, h)]  # right w, down h, left w, up h -> closed loop
    i = 0
    for d, n in runs:
        for _ in range(n):
            if i >= W: return None
            g[0][i] = d; i += 1
    for c in range(W): g[1][c] = SEP
    r0 = rng.randint(CANVAS_R0, H - 1 - h); c0 = rng.randint(0, W - 1 - w)
    g[r0][c0] = 6
    return g
def tf_closed(g):
    runs = _run_length_instr(g); start = _find(g, 6)
    if not runs or not start: return None
    H, W = dims(g)
    moves = [MOVE[d] for d, n in runs for _ in range(n)]
    vis = _walk(moves, start, H, W, "wall")
    if not vis or vis[-1] != start: return None   # must close exactly
    out = copy(g)
    for r, c in vis: out[r][c] = 9
    loop = set(vis) | {start}
    rs = [p[0] for p in loop]; cs = [p[1] for p in loop]
    for r in range(min(rs) + 1, max(rs)):
        for c in range(min(cs) + 1, max(cs)):
            if (r, c) not in loop: out[r][c] = 7
    return out
rule("turtle_closed_rectangle_filled",
     "Row 0 above the colour-8 separator holds a run-length move list (1=up,2=right,3=down,4=left) that forms a rectangle and returns the colour-6 turtle exactly to its start; the perimeter is drawn colour 9 and, because the path closes, its interior is filled colour 7.",
     gi_closed, tf_closed, digits=True)


# ---------- 17 obstacle stop + dotted trail ----------
def gi_obst_dot(rng):
    return gi_obstacle(rng)
def tf_obst_dot(g):
    instr = _read_instr(g); start = _find(g, 6)
    if not instr or not start: return None
    H, W = dims(g)
    obst = {(r, c) for r in range(H) for c in range(W) if g[r][c] == 5}
    vis = _walk([MOVE[v] for v in instr], start, H, W, "wall", obstacles=obst)
    if len(vis) < 2: return None
    out = copy(g)
    for i, (r, c) in enumerate(vis):
        if i % 2 == 1: out[r][c] = 9
    return out
rule("turtle_obstacle_stop_dotted_trail",
     "Row 0 (1=up,2=right,3=down,4=left) is a move list for the colour-6 turtle below the colour-8 separator; it stops the instant a step would leave the canvas or land on a colour-5 obstacle, marking colour 9 only on every second visited cell and leaving the odd steps blank.",
     gi_obst_dot, tf_obst_dot, digits=True)


# ---------- 18 per-instruction colour, wrap ----------
def gi_percolour_wrap(rng):
    return gi_wrap(rng)
def tf_percolour_wrap(g):
    instr = _read_instr(g); start = _find(g, 6)
    if not instr or not start: return None
    H, W = dims(g)
    r, c = start; out = copy(g); moved = False
    for v in instr:
        dr, dc = MOVE[v]; r, c = _wrap(r + dr, c + dc, H, W); out[r][c] = v; moved = True
    return out if moved else None
rule("turtle_per_instruction_colour_wrap",
     "Row 0 (1=up,2=right,3=down,4=left) is a move list for the colour-6 turtle below the colour-8 separator; each visited cell is painted the colour of the instruction that produced the step, and instead of stopping at an edge the turtle wraps to the opposite side, running the full list.",
     gi_percolour_wrap, tf_percolour_wrap, digits=True)


# ---------- 19 two markers, obstacles, independent stop ----------
def gi_two_obst(rng):
    g, H, W, instr = _canvas(rng, 12, 30, 3, 7)
    pts = rng.sample([(r, c) for r in range(CANVAS_R0, H) for c in range(W)], 2)
    g[pts[0][0]][pts[0][1]] = 6; g[pts[1][0]][pts[1][1]] = 4 if False else 5
    # note: 5 already used as second marker here; obstacles get colour 7 to avoid clash
    free = [(r, c) for r in range(CANVAS_R0, H) for c in range(W) if g[r][c] == 0]
    if not free: return None
    for r, c in rng.sample(free, min(rng.randint(1, 3), len(free))):
        g[r][c] = 7
    return g
def tf_two_obst(g):
    instr = _read_instr(g); s1 = _find(g, 6); s2 = _find(g, 5)
    if not instr or not s1 or not s2: return None
    H, W = dims(g)
    obst = {(r, c) for r in range(H) for c in range(W) if g[r][c] == 7}
    v1 = _walk([MOVE[v] for v in instr], s1, H, W, "wall", obstacles=obst)
    v2 = _walk([MOVE[v] for v in instr], s2, H, W, "wall", obstacles=obst)
    if not v1 and not v2: return None
    out = copy(g)
    for r, c in v1: out[r][c] = 9
    for r, c in v2: out[r][c] = 2
    return out
rule("turtle_two_markers_shared_obstacles",
     "Row 0 (1=up,2=right,3=down,4=left) is one move list applied to two turtles, colour-6 (path drawn 9) and colour-5 (path drawn 2), both below the colour-8 separator and sharing the same colour-7 obstacle cells; each turtle stops independently the instant its own step would leave the canvas or land on an obstacle.",
     gi_two_obst, tf_two_obst, digits=True)


# ---------- 20 mirrored on right half + wrap ----------
def gi_mirror_wrap(rng):
    return gi_wrap(rng)
def tf_mirror_wrap(g):
    instr = _read_instr(g); start = _find(g, 6)
    if not instr or not start: return None
    H, W = dims(g)
    if start[1] >= W // 2:
        instr = [{1: 1, 2: 4, 3: 3, 4: 2}[v] for v in instr]
    vis = _walk([MOVE[v] for v in instr], start, H, W, "wrap")
    if not vis: return None
    out = copy(g)
    for r, c in vis: out[r][c] = 9
    return out
rule("turtle_mirrored_on_right_half_wrap",
     "Row 0 (1=up,2=right,3=down,4=left) is the move list for the colour-6 turtle below the colour-8 separator; if the marker sits in the right half of the canvas the left/right instructions (2 and 4) are swapped before walking, the path is drawn colour 9, and the turtle wraps around any edge instead of stopping, running the full list.",
     gi_mirror_wrap, tf_mirror_wrap, digits=True)


# ---------- 21 repeat corner digit + wrap ----------
def gi_repeat_wrap(rng):
    g, H, W, instr = _canvas(rng, 12, 30, 3, 6)
    r0, c0 = rng.randint(CANVAS_R0, H - 1), rng.randint(0, W - 1)
    k = rng.randint(1, 3)
    if (r0, c0) == (H - 1, W - 1): return None
    g[r0][c0] = 6; g[H - 1][W - 1] = k
    return g
def tf_repeat_wrap(g):
    instr = _read_instr(g); start = _find(g, 6)
    H, W = dims(g)
    k = g[H - 1][W - 1]
    if not instr or not start or not (1 <= k <= 9): return None
    moves = [MOVE[v] for v in instr] * k
    vis = _walk(moves, start, H, W, "wrap")
    if not vis: return None
    out = copy(g)
    for r, c in vis: out[r][c] = 9
    return out
rule("turtle_repeat_sequence_corner_digit_wrap",
     "Row 0 (1=up,2=right,3=down,4=left) is a move list the colour-6 turtle below the colour-8 separator repeats k times in order, where k is the digit stored in the canvas's bottom-right corner cell; the path is drawn colour 9 and the turtle wraps around any edge instead of stopping.",
     gi_repeat_wrap, tf_repeat_wrap, digits=True)


# ---------- 22 run-length instructions, wrap ----------
def gi_runlen_wrap(rng):
    return gi_runlen(rng)
def tf_runlen_wrap(g):
    runs = _run_length_instr(g); start = _find(g, 6)
    if not runs or not start: return None
    H, W = dims(g)
    moves = [MOVE[d] for d, n in runs for _ in range(n)]
    vis = _walk(moves, start, H, W, "wrap")
    if not vis: return None
    out = copy(g)
    for r, c in vis: out[r][c] = 9
    return out
rule("turtle_run_length_instructions_wrap",
     "Row 0 above the colour-8 separator holds direction codes (1=up,2=right,3=down,4=left) in runs; each run of n equal cells means move n steps in that direction, applied in order to the colour-6 turtle, which wraps around any edge instead of stopping and runs the full list; the path is drawn colour 9.",
     gi_runlen_wrap, tf_runlen_wrap, digits=True)


# ---------- 23 end marked, wrap ----------
def gi_endmark_wrap(rng):
    return gi_wrap(rng)
def tf_endmark_wrap(g):
    instr = _read_instr(g); start = _find(g, 6)
    if not instr or not start: return None
    H, W = dims(g)
    vis = _walk([MOVE[v] for v in instr], start, H, W, "wrap")
    if not vis: return None
    out = copy(g)
    for r, c in vis: out[r][c] = 9
    er, ec = vis[-1]; out[er][ec] = 7
    return out
rule("turtle_direct_digit_end_marked_wrap",
     "Row 0 (1=up,2=right,3=down,4=left) is a move list for the colour-6 turtle below the colour-8 separator; it wraps around any edge instead of stopping, runs the full list, draws every visited cell colour 9 except the final cell reached, which is marked colour 7.",
     gi_endmark_wrap, tf_endmark_wrap, digits=True)


# ---------- 24 two turtles, end cells marked, wall stop ----------
def gi_two_endmark(rng):
    return gi_two_same(rng)
def tf_two_endmark(g):
    instr = _read_instr(g); s1 = _find(g, 6); s2 = _find(g, 5)
    if not instr or not s1 or not s2: return None
    H, W = dims(g)
    v1 = _walk([MOVE[v] for v in instr], s1, H, W, "wall")
    v2 = _walk([MOVE[v] for v in instr], s2, H, W, "wall")
    if not v1 or not v2: return None
    out = copy(g)
    for r, c in v1: out[r][c] = 9
    for r, c in v2: out[r][c] = 9
    out[v1[-1][0]][v1[-1][1]] = 7
    out[v2[-1][0]][v2[-1][1]] = 2
    return out
rule("turtle_two_markers_end_cells_marked",
     "Row 0 (1=up,2=right,3=down,4=left) is one move list applied to two turtles, colour-6 and colour-5, both below the colour-8 separator; both paths are drawn colour 9, each turtle stops the instant its own step would leave the canvas, and each turtle's final resting cell is marked separately, colour 7 for the colour-6 turtle and colour 2 for the colour-5 turtle.",
     gi_two_endmark, tf_two_endmark, digits=True)


# ---------- 25 run-length with end marker ----------
def gi_runlen_end(rng):
    return gi_runlen(rng)
def tf_runlen_end(g):
    runs = _run_length_instr(g); start = _find(g, 6)
    if not runs or not start: return None
    H, W = dims(g)
    moves = [MOVE[d] for d, n in runs for _ in range(n)]
    vis = _walk(moves, start, H, W, "wall")
    if not vis: return None
    out = copy(g)
    for r, c in vis: out[r][c] = 9
    er, ec = vis[-1]; out[er][ec] = 7
    return out
rule("turtle_run_length_instructions_end_marked",
     "Row 0 above the colour-8 separator holds direction codes (1=up,2=right,3=down,4=left) in runs; each run of n equal cells means move n steps in that direction for the colour-6 turtle, which stops the instant a step would leave the canvas; every visited cell is drawn colour 9 except the final cell, marked colour 7.",
     gi_runlen_end, tf_runlen_end, digits=True)


# ---------- 26 dotted trail, wrap ----------
def gi_dotted_wrap(rng):
    return gi_wrap(rng)
def tf_dotted_wrap(g):
    instr = _read_instr(g); start = _find(g, 6)
    if not instr or not start: return None
    H, W = dims(g)
    vis = _walk([MOVE[v] for v in instr], start, H, W, "wrap")
    if len(vis) < 2: return None
    out = copy(g)
    for i, (r, c) in enumerate(vis):
        if i % 2 == 1: out[r][c] = 9
    return out
rule("turtle_dotted_every_second_step_wrap",
     "Row 0 (1=up,2=right,3=down,4=left) is a move list for the colour-6 turtle below the colour-8 separator; it wraps around any edge instead of stopping, runs the full list, and marks colour 9 only on every second visited cell (steps 2, 4, 6, ...), leaving the odd steps blank.",
     gi_dotted_wrap, tf_dotted_wrap, digits=True)


# ---------- 27 mirrored + per-instruction colour ----------
def gi_mirror_colour(rng):
    return gi_wall(rng)
def tf_mirror_colour(g):
    instr = _read_instr(g); start = _find(g, 6)
    if not instr or not start: return None
    H, W = dims(g)
    if start[1] >= W // 2:
        instr = [{1: 1, 2: 4, 3: 3, 4: 2}[v] for v in instr]
    r, c = start; out = copy(g); moved = False
    for v in instr:
        dr, dc = MOVE[v]; nr, nc = r + dr, c + dc
        if not _inb(nr, nc, H, W): break
        r, c = nr, nc; out[r][c] = v; moved = True
    return out if moved else None
rule("turtle_mirrored_on_right_half_per_instruction_colour",
     "Row 0 (1=up,2=right,3=down,4=left) is the move list for the colour-6 turtle below the colour-8 separator; if the marker sits in the right half of the canvas, left/right (2 and 4) are swapped before walking, each visited cell is painted the colour of the instruction that produced the step, and the turtle stops the instant a step would leave the canvas.",
     gi_mirror_colour, tf_mirror_colour, digits=True)


# ---------- 28 turn-based, per-step colour alternation ----------
def gi_turn_alt(rng):
    return gi_turn(rng)
def tf_turn_alt(g):
    codes = []
    for v in g[0]:
        if v in (5, 3): codes.append(v)
        else: break
    start = _find(g, 6)
    if not codes or not start: return None
    H, W = dims(g)
    heading = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    hi = 0; r, c = start; out = copy(g); moved = False; step_n = 0
    for code in codes:
        if code == 5:
            hi = (hi + 1) % 4
        else:
            dr, dc = heading[hi]; nr, nc = r + dr, c + dc
            if not _inb(nr, nc, H, W): break
            r, c = nr, nc; out[r][c] = 9 if step_n % 2 == 0 else 2; step_n += 1; moved = True
    return out if moved else None
rule("turtle_turn_based_alternating_step_colour",
     "Row 0 above the colour-8 separator is a turn program for the colour-6 turtle, initially heading right: colour 5 (grey) turns it 90 degrees clockwise in place, colour 3 steps it one cell forward; successive steps alternate colour 9, colour 2, colour 9, ... and the turtle stops permanently the instant a step would leave the canvas.",
     gi_turn_alt, tf_turn_alt, digits=True)


# ---------- 29 closed square, outline only (no fill), size reported by width of row? keep distinct: mark corners ----------
def gi_closed_corners(rng):
    return gi_closed(rng)
def tf_closed_corners(g):
    runs = _run_length_instr(g); start = _find(g, 6)
    if not runs or not start: return None
    H, W = dims(g)
    moves = [MOVE[d] for d, n in runs for _ in range(n)]
    vis = _walk(moves, start, H, W, "wall")
    if not vis or vis[-1] != start: return None
    out = copy(g)
    for r, c in vis: out[r][c] = 9
    loop = [start] + vis
    rs = sorted(set(p[0] for p in loop)); cs = sorted(set(p[1] for p in loop))
    for r in (rs[0], rs[-1]):
        for c in (cs[0], cs[-1]):
            out[r][c] = 7
    return out
rule("turtle_closed_rectangle_corners_marked",
     "Row 0 above the colour-8 separator holds a run-length move list (1=up,2=right,3=down,4=left) that forms a rectangle and returns the colour-6 turtle exactly to its start; the perimeter is drawn colour 9 and the four corner cells of the bounding rectangle are marked colour 7.",
     gi_closed_corners, tf_closed_corners, digits=True)


# ---------- 30 per-instruction colour + end marked ----------
def gi_colour_end(rng):
    return gi_wall(rng)
def tf_colour_end(g):
    instr = _read_instr(g); start = _find(g, 6)
    if not instr or not start: return None
    H, W = dims(g)
    r, c = start; out = copy(g); path = []
    for v in instr:
        dr, dc = MOVE[v]; nr, nc = r + dr, c + dc
        if not _inb(nr, nc, H, W): break
        r, c = nr, nc; path.append((r, c, v))
    if not path: return None
    for r, c, v in path: out[r][c] = v
    lr, lc, _ = path[-1]; out[lr][lc] = 7
    return out
rule("turtle_per_instruction_colour_end_marked",
     "Row 0 (1=up,2=right,3=down,4=left) is a move list for the colour-6 turtle below the colour-8 separator; each visited cell is painted the colour of the instruction that produced the step, except the final resting cell, which is overwritten colour 7; the turtle stops the instant a step would leave the canvas.",
     gi_colour_end, tf_colour_end, digits=True)


# ---------- 31 obstacle stop + per-instruction colour ----------
def gi_obst_colour(rng):
    return gi_obstacle(rng)
def tf_obst_colour(g):
    instr = _read_instr(g); start = _find(g, 6)
    if not instr or not start: return None
    H, W = dims(g)
    obst = {(r, c) for r in range(H) for c in range(W) if g[r][c] == 5}
    r, c = start; out = copy(g); moved = False
    for v in instr:
        dr, dc = MOVE[v]; nr, nc = r + dr, c + dc
        if not _inb(nr, nc, H, W) or (nr, nc) in obst: break
        r, c = nr, nc; out[r][c] = v; moved = True
    return out if moved else None
rule("turtle_obstacle_stop_per_instruction_colour",
     "Row 0 (1=up,2=right,3=down,4=left) is a move list for the colour-6 turtle below the colour-8 separator; each visited cell is painted the colour of the instruction that produced the step, and the turtle stops the instant a step would leave the canvas or land on a colour-5 obstacle.",
     gi_obst_colour, tf_obst_colour, digits=True)


# ---------- 32 two markers, mirrored reading for second ----------
def gi_two_mirror(rng):
    return gi_two_same(rng)
def tf_two_mirror(g):
    instr = _read_instr(g); s1 = _find(g, 6); s2 = _find(g, 5)
    if not instr or not s1 or not s2: return None
    H, W = dims(g)
    swap = {1: 1, 2: 4, 3: 3, 4: 2}
    v1 = _walk([MOVE[v] for v in instr], s1, H, W, "wall")
    v2 = _walk([MOVE[swap[v]] for v in instr], s2, H, W, "wall")
    if not v1 and not v2: return None
    out = copy(g)
    for r, c in v1: out[r][c] = 9
    for r, c in v2: out[r][c] = 7
    return out
rule("turtle_second_marker_left_right_swapped",
     "Row 0 (1=up,2=right,3=down,4=left) is the move list; the colour-6 marker follows it directly (path colour 9) while the colour-5 marker follows the same list with left and right swapped, i.e. 2 and 4 exchanged (path colour 7), both below the colour-8 separator, each stopping the instant its own step would leave the canvas.",
     gi_two_mirror, tf_two_mirror, digits=True)


# ---------- 33 run-length + per-run colour (colour = direction, not count) ----------
def gi_runlen_colour(rng):
    return gi_runlen(rng)
def tf_runlen_colour(g):
    runs = _run_length_instr(g); start = _find(g, 6)
    if not runs or not start: return None
    H, W = dims(g)
    r, c = start; out = copy(g); moved = False
    for d, n in runs:
        for _ in range(n):
            dr, dc = MOVE[d]; nr, nc = r + dr, c + dc
            if not _inb(nr, nc, H, W): break
            r, c = nr, nc; out[r][c] = d; moved = True
        else:
            continue
        break
    return out if moved else None
rule("turtle_run_length_per_direction_colour",
     "Row 0 above the colour-8 separator holds direction codes (1=up,2=right,3=down,4=left) in runs; each run of n equal cells moves the colour-6 turtle n steps in that direction, and every visited cell is painted that same direction's colour; the turtle stops the instant a step would leave the canvas.",
     gi_runlen_colour, tf_runlen_colour, digits=True)


# ---------- 34 wrap + obstacle (wrap but obstacles still block) ----------
def gi_wrap_obst(rng):
    g, H, W, instr = _canvas(rng, 12, 30, 4, 9)
    r0, c0 = rng.randint(CANVAS_R0, H - 1), rng.randint(0, W - 1)
    g[r0][c0] = 6
    free = [(r, c) for r in range(CANVAS_R0, H) for c in range(W) if g[r][c] == 0 and (r, c) != (r0, c0)]
    if not free: return None
    for r, c in rng.sample(free, min(rng.randint(1, 3), len(free))):
        g[r][c] = 5
    return g
def tf_wrap_obst(g):
    instr = _read_instr(g); start = _find(g, 6)
    if not instr or not start: return None
    H, W = dims(g)
    obst = {(r, c) for r in range(H) for c in range(W) if g[r][c] == 5}
    r, c = start; out = copy(g); moved = False
    for v in instr:
        dr, dc = MOVE[v]; nr, nc = _wrap(r + dr, c + dc, H, W)
        if (nr, nc) in obst: break
        r, c = nr, nc; out[r][c] = 9; moved = True
    return out if moved else None
rule("turtle_wrap_edges_obstacle_stop",
     "Row 0 (1=up,2=right,3=down,4=left) is a move list for the colour-6 turtle below the colour-8 separator; it wraps to the opposite edge whenever a step would leave the canvas, but stops permanently the instant a (possibly wrapped) step would land on a colour-5 obstacle, drawing colour 9 on every visited cell.",
     gi_wrap_obst, tf_wrap_obst, digits=True)


# ---------- 35 turn-based + repeat corner digit ----------
def gi_turn_repeat(rng):
    H = rng.randint(12, 30); W = rng.randint(12, 30)
    L = rng.randint(4, min(9, W))
    g = blank(H, W)
    for i in range(L):
        g[0][i] = 5 if rng.random() < 0.35 else 3
    for c in range(W): g[1][c] = SEP
    r0, c0 = rng.randint(CANVAS_R0, H - 1), rng.randint(0, W - 1)
    k = rng.randint(1, 2)
    if (r0, c0) == (H - 1, W - 1): return None
    g[r0][c0] = 6; g[H - 1][W - 1] = k
    return g
def tf_turn_repeat(g):
    codes = []
    for v in g[0]:
        if v in (5, 3): codes.append(v)
        else: break
    start = _find(g, 6)
    H, W = dims(g)
    k = g[H - 1][W - 1]
    if not codes or not start or not (1 <= k <= 9): return None
    codes = codes * k
    heading = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    hi = 0; r, c = start; out = copy(g); moved = False
    for code in codes:
        if code == 5:
            hi = (hi + 1) % 4
        else:
            dr, dc = heading[hi]; nr, nc = r + dr, c + dc
            if not _inb(nr, nc, H, W): break
            r, c = nr, nc; out[r][c] = 9; moved = True
    return out if moved else None
rule("turtle_turn_based_repeat_corner_digit",
     "Row 0 above the colour-8 separator is a turn program (colour 5 grey = turn 90 degrees clockwise, colour 3 = step forward) that the colour-6 turtle, initially heading right, repeats k times in order, where k is the digit in the canvas's bottom-right corner cell; steps are drawn colour 9 and the turtle stops permanently the instant a step would leave the canvas.",
     gi_turn_repeat, tf_turn_repeat, digits=True)


# ---------- 36 closed path, filled, fill colour keyed by loop size parity ----------
def gi_closed_keyed(rng):
    return gi_closed(rng)
def tf_closed_keyed(g):
    runs = _run_length_instr(g); start = _find(g, 6)
    if not runs or not start: return None
    H, W = dims(g)
    moves = [MOVE[d] for d, n in runs for _ in range(n)]
    vis = _walk(moves, start, H, W, "wall")
    if not vis or vis[-1] != start: return None
    loop = set(vis) | {start}
    rs = [p[0] for p in loop]; cs = [p[1] for p in loop]
    area = (max(rs) - min(rs) - 1) * (max(cs) - min(cs) - 1)
    fill = 7 if area % 2 == 0 else 2
    out = copy(g)
    for r, c in vis: out[r][c] = 9
    for r in range(min(rs) + 1, max(rs)):
        for c in range(min(cs) + 1, max(cs)):
            if (r, c) not in loop: out[r][c] = fill
    return out
rule("turtle_closed_rectangle_filled_parity_colour",
     "Row 0 above the colour-8 separator holds a run-length move list (1=up,2=right,3=down,4=left) that forms a rectangle and returns the colour-6 turtle exactly to its start; the perimeter is drawn colour 9 and the interior is filled colour 7 if the interior's cell count is even, colour 2 if odd.",
     gi_closed_keyed, tf_closed_keyed, digits=True)


# ---------- 37 per-instruction colour + wrap + dotted (every step but alt colour/blank) combined distinctly ----------
def gi_wrap_dot_colour(rng):
    return gi_wrap(rng)
def tf_wrap_dot_colour(g):
    instr = _read_instr(g); start = _find(g, 6)
    if not instr or not start: return None
    H, W = dims(g)
    r, c = start; out = copy(g); moved = False; i = 0
    for v in instr:
        dr, dc = MOVE[v]; r, c = _wrap(r + dr, c + dc, H, W)
        if i % 2 == 1: out[r][c] = v
        moved = True; i += 1
    return out if moved else None
rule("turtle_wrap_edges_dotted_per_instruction_colour",
     "Row 0 (1=up,2=right,3=down,4=left) is a move list for the colour-6 turtle below the colour-8 separator; it wraps to the opposite edge whenever a step would leave the canvas and runs the full list, marking only every second visited cell (steps 2, 4, 6, ...) with the colour of the instruction that produced that step.",
     gi_wrap_dot_colour, tf_wrap_dot_colour, digits=True)


# ---------- 38 two markers, instructions end stop (margin guaranteed), end marked ----------
def gi_two_endstop(rng):
    for _ in range(30):
        g, H, W, instr = _canvas(rng, 14, 30, 3, 6)
        L = len(instr)
        cand = [(r, c) for r in range(CANVAS_R0, H) for c in range(W) if _margin_ok(r, c, L, H, W)]
        if len(cand) >= 2:
            p1, p2 = rng.sample(cand, 2)
            g[p1[0]][p1[1]] = 6; g[p2[0]][p2[1]] = 5
            return g
    return None
def tf_two_endstop(g):
    instr = _read_instr(g); s1 = _find(g, 6); s2 = _find(g, 5)
    if not instr or not s1 or not s2: return None
    out = copy(g)
    for start, col in ((s1, 9), (s2, 2)):
        r, c = start
        for v in instr:
            dr, dc = MOVE[v]; r, c = r + dr, c + dc
        out[r][c] = col
    return out
rule("turtle_two_markers_end_only_instruction_end_stop",
     "Row 0 (1=up,2=right,3=down,4=left) is a move list each of two turtles, colour-6 and colour-5, follows in full below the colour-8 separator (inputs are built with enough margin that no wall is ever hit); only each turtle's final resting cell is marked, colour 9 for the colour-6 turtle and colour 2 for the colour-5 turtle.",
     gi_two_endstop, tf_two_endstop, digits=True)


# ---------- 39 run-length instructions, two markers ----------
def gi_runlen_two(rng):
    g = gi_runlen(rng)
    if g is None: return None
    H, W = dims(g)
    start = _find(g, 6)
    free = [(r, c) for r in range(CANVAS_R0, H) for c in range(W) if g[r][c] == 0]
    if not free: return None
    r2, c2 = rng.choice(free)
    g[r2][c2] = 5
    return g
def tf_runlen_two(g):
    runs = _run_length_instr(g); s1 = _find(g, 6); s2 = _find(g, 5)
    if not runs or not s1 or not s2: return None
    H, W = dims(g)
    moves = [MOVE[d] for d, n in runs for _ in range(n)]
    v1 = _walk(moves, s1, H, W, "wall")
    v2 = _walk(moves, s2, H, W, "wall")
    if not v1 and not v2: return None
    out = copy(g)
    for r, c in v1: out[r][c] = 9
    for r, c in v2: out[r][c] = 7
    return out
rule("turtle_run_length_instructions_two_markers",
     "Row 0 above the colour-8 separator holds direction codes (1=up,2=right,3=down,4=left) in runs, each run of n equal cells meaning move n steps in that direction; the same run-length program is applied independently to the colour-6 turtle (path colour 9) and the colour-5 turtle (path colour 7), each stopping the instant its own step would leave the canvas.",
     gi_runlen_two, tf_runlen_two, digits=True)


# ---------- 40 mirrored + obstacle stop ----------
def gi_mirror_obst(rng):
    return gi_obstacle(rng)
def tf_mirror_obst(g):
    instr = _read_instr(g); start = _find(g, 6)
    if not instr or not start: return None
    H, W = dims(g)
    if start[1] >= W // 2:
        instr = [{1: 1, 2: 4, 3: 3, 4: 2}[v] for v in instr]
    obst = {(r, c) for r in range(H) for c in range(W) if g[r][c] == 5}
    vis = _walk([MOVE[v] for v in instr], start, H, W, "wall", obstacles=obst)
    if not vis: return None
    out = copy(g)
    for r, c in vis: out[r][c] = 9
    return out
rule("turtle_mirrored_on_right_half_obstacle_stop",
     "Row 0 (1=up,2=right,3=down,4=left) is the move list for the colour-6 turtle below the colour-8 separator; if the marker sits in the right half of the canvas, left/right (2 and 4) are swapped before walking, the path is drawn colour 9, and the turtle stops the instant a step would leave the canvas or land on a colour-5 obstacle.",
     gi_mirror_obst, tf_mirror_obst, digits=True)
