"""e12f9a14 -- cargo sprays out of the crates and the jets shoulder each other.

A crate is a 4x4 box: a 2x2 of coloured cargo inside a one-cell wall.  Cargo
escapes through every missing wall cell -- straight out of a gap in a side,
diagonally out of a missing corner -- and streaks away to the edge.

No two jets ever cross.  Wherever a pair would meet, each stops one cell short
and both swing onto the SUM of their two headings, reduced to its simplest
ratio, running on side by side.  Nearer meetings settle first, and a jet that
has been turned can still be turned again by a different jet further out.  A
heading of two rows to one column draws as a stair of alternating steps.

KNOWN-BAD DEMO: train[2]'s cargo-4 crate (rows 10-13, cols 11-14) has three wall
gaps -- top edge, left edge and the bottom-right corner -- and its answer fires
only two, leaving the corner at (13,14) dead.  Every other corner gap in the
task fires, including the geometrically identical one in test[1]'s cargo-2 crate
(rows 4-7, cols 3-6).  The anomaly is in the benchmark answer; this generator
fires all three and so reproduces 3 of 4 demos and both held-out answers.
"""

import math


def _pure(d):
    g = math.gcd(abs(d[0]), abs(d[1])) or 1
    return (d[0] // g, d[1] // g)


def _ray(start, d, H, W):
    out = []
    m = max(abs(d[0]), abs(d[1]))
    if not m:
        return out
    k = 0
    while True:
        k += 1
        p = (int(math.floor(start[0] + d[0] * k / m + 1e-9)),
             int(math.floor(start[1] + d[1] * k / m + 1e-9)))
        if not (0 <= p[0] < H and 0 <= p[1] < W):
            return out
        out.append(p)


def _meet(A, B):
    """Where two jets would foul: index into each of the last safe cell."""
    pos = {p: i for i, p in enumerate(B["cells"])}
    for i, p in enumerate(A["cells"]):
        if p in pos:
            return (i - 1, pos[p] - 1) if i and pos[p] else None
    for i in range(len(A["cells"]) - 1):
        p, q = A["cells"][i], A["cells"][i + 1]
        if p[0] == q[0] or p[1] == q[1]:
            continue
        a, b = (p[0], q[1]), (q[0], p[1])
        if a in pos and b in pos and abs(pos[a] - pos[b]) == 1:
            return (i, min(pos[a], pos[b]))
    return None


def transform(gi):
    H, W = len(gi), len(gi[0])
    flat = [v for row in gi for v in row]
    bg = max(set(flat), key=flat.count)
    rest = [v for v in flat if v != bg]
    wall = max(set(rest), key=rest.count)

    jets = []
    for r in range(H - 1):
        for c in range(W - 1):
            v = gi[r][c]
            if v in (bg, wall) or not all(gi[r + a][c + b] == v for a in (0, 1) for b in (0, 1)):
                continue
            r0, c0 = r - 1, c - 1
            for dr in range(4):
                for dc in range(4):
                    if 1 <= dr <= 2 and 1 <= dc <= 2:
                        continue
                    y, x = r0 + dr, c0 + dc
                    if not (0 <= y < H and 0 <= x < W) or gi[y][x] == wall:
                        continue
                    aim = (-1 if dr == 0 else 1 if dr == 3 else 0,
                           -1 if dc == 0 else 1 if dc == 3 else 0)
                    jets.append({"cargo": v, "cells": [(y, x)] + _ray((y, x), aim, H, W),
                                 "dirs": None, "aim": aim, "bends": [], "met": set()})

    for j in jets:
        j["dirs"] = [j["aim"]] * len(j["cells"])

    for _ in range(40):
        best = None
        for i in range(len(jets)):
            for k in range(i + 1, len(jets)):
                if k in jets[i]["met"]:
                    continue
                hit = _meet(jets[i], jets[k])
                if hit is None or hit[0] < 0 or hit[1] < 0:
                    continue
                score = (max(hit), hit[0] + hit[1], i, k)
                if best is None or score < best[0]:
                    best = (score, i, k, hit)
        if best is None:
            break
        now = best[0][0]
        plan = {}
        for i in range(len(jets)):
            for k in range(i + 1, len(jets)):
                if k in jets[i]["met"]:
                    continue
                hit = _meet(jets[i], jets[k])
                if hit is None or hit[0] < 0 or hit[1] < 0 or max(hit) != now:
                    continue
                A, B = jets[i], jets[k]
                d = _pure((A["dirs"][hit[0]][0] + B["dirs"][hit[1]][0],
                           A["dirs"][hit[0]][1] + B["dirs"][hit[1]][1]))
                for who, idx in ((i, hit[0]), (k, hit[1])):
                    if who not in plan or idx < plan[who][0]:
                        plan[who] = (idx, d)
                A["met"].add(k)
                B["met"].add(i)
        for who, (idx, d) in plan.items():
            J = jets[who]
            J["cells"] = J["cells"][:idx + 1] + _ray(J["cells"][idx], d, H, W)
            J["dirs"] = J["dirs"][:idx + 1] + [d] * (len(J["cells"]) - idx - 1)

    go = [row[:] for row in gi]
    for j in jets:
        for y, x in j["cells"]:
            go[y][x] = j["cargo"]
    return go
