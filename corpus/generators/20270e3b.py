# Rule authored from the evaluation demonstrations of 20270e3b.
#
# THE 4-COUNT IS CONSERVED EXACTLY in every pair (36, 20, 16, 22, 34 in and out). Nothing is
# added or destroyed; the shape is CUT IN TWO and the halves are pushed back together, and the
# 1s are only padding, which is why the output's size is whatever the reassembled shape needs.
#
# The two markers are SOCKETS, one on each half, sitting where the cut was made. Reassembly
# puts the cells immediately behind one socket onto the other socket's cells — the two sockets
# swap into each other's place, which is what butting the cut edges together means.
#
# A LOOSE FRAGMENT TOUCHES NEITHER SOCKET AND STILL BELONGS TO A HALF — the one it sits beside.
# Demo 0's 2-cell piece at (4,10) is connected to nothing, sits beside the travelling half, and
# rides along to (4,4). Test 1's single cell at (1,3) sits inside the ANCHOR half and must not
# move; travelling it by default put it at row -2 and grew the answer from 8x8 to 10x8. Nearest
# socket-owning piece decides.
#
# The output is then the reassembled shape's own bounding box on a background of 1. There is no
# separate crop rule to find — every output is exactly that box.
from collections import Counter, deque

# WHICH COLOUR IS THE SHAPE CANNOT BE READ OFF FREQUENCY. Demo 2 is 16 cells of shape against 5 of
# background, so "most common colour is the background" picks the shape and the reassembly never
# starts. The structure decides it instead: with the right colour each socket has its own half
# behind it, so the two sockets own DIFFERENT components. With the wrong one both sockets end up
# facing the same blob of padding between them, and that is the test.


def _groups(grid, want):
    h, w = len(grid), len(grid[0])
    seen, out = set(), []
    for r in range(h):
        for c in range(w):
            if grid[r][c] in want and (r, c) not in seen:
                q = deque([(r, c)])
                seen.add((r, c))
                cells = []
                while q:
                    y, x = q.popleft()
                    cells.append((y, x))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        n = (y + dy, x + dx)
                        if (0 <= n[0] < h and 0 <= n[1] < w and n not in seen
                                and grid[n[0]][n[1]] in want):
                            seen.add(n)
                            q.append(n)
                out.append(sorted(cells))
    return out


def _norm(cells):
    r0 = min(r for r, _ in cells); c0 = min(c for _, c in cells)
    return frozenset((r - r0, c - c0) for r, c in cells)


def _socket_colours(grid, counts):
    """The two sockets are the two faces of ONE cut, so they are the same shape. That names the
    socket colour on 5 of the 6 pairs outright; demo 2's body also falls in two congruent halves,
    and there the socket is the smaller of the two candidates — a cut face cannot outweigh the
    shape it was cut from."""
    out = []
    for v in sorted(counts):
        g = _groups(grid, {v})
        if len(g) == 2 and _norm(g[0]) == _norm(g[1]):
            out.append(v)
    return sorted(out, key=lambda v: counts[v])


def transform(grid):
    h, w = len(grid), len(grid[0])
    counts = Counter(v for row in grid for v in row)
    for sock in _socket_colours(grid, counts):
        got = _reassemble(grid, h, w, counts, _groups(grid, {sock}), sock)
        if got is not None:
            return got
    return [row[:] for row in grid]


def _reassemble(grid, h, w, counts, sockets, SOCKET):

    # THE SHAPE IS A CUT OBJECT, so it lies in two or three pieces; the padding is scattered in
    # more. Among the colours that assemble at all, the one in the FEWEST components is the shape.
    # Frequency cannot decide it — demo 2 has more shape than padding, and the test's padding is a
    # single blob that simply fails to assemble.
    best = None
    for body in sorted(v for v in counts if v != SOCKET):
        got = _assemble(grid, h, w, counts, sockets, body, SOCKET)
        if got is None:
            continue
        key = (len(_groups(grid, {body})), counts[body])
        if best is None or key < best[0]:
            best = (key, got)
    return best[1] if best else None


def _assemble(grid, h, w, counts, sockets, body, SOCKET):
    bg = next((v for v in counts if v not in (SOCKET, body)), None)
    if bg is None:
        return None
    pieces = _groups(grid, {body})
    if len(pieces) < 2:
        return None

    def behind(sock):
        """The body cells orthogonally touching a socket — the cut face of its own half."""
        out = set()
        for (r, c) in sock:
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (r + dy, c + dx)
                if 0 <= n[0] < h and 0 <= n[1] < w and grid[n[0]][n[1]] == body:
                    out.add(n)
        return sorted(out)

    faces = [behind(s) for s in sockets]
    if not faces[0] or not faces[1]:
        return None

    # THE ANCHOR IS THE LARGER HALF, and the choice is not cosmetic. Anchoring on the small half
    # makes every other component travel, which drags loose fragments away from the half they
    # belong to — demo 0's 2-cell piece sits beside the small half and must move WITH it.
    owner = []
    for f in faces:
        for i, p in enumerate(pieces):
            if f[0] in p:
                owner.append(i)
                break
    if len(owner) != 2 or owner[0] == owner[1]:
        return None
    a = 0 if len(pieces[owner[0]]) >= len(pieces[owner[1]]) else 1
    b = 1 - a

    # the moving half's cut face lands on the anchor's socket
    dr = sockets[a][0][0] - faces[b][0][0]
    dc = sockets[a][0][1] - faces[b][0][1]

    def near(cells_of, target):
        return min(abs(r - y) + abs(c - x) for (r, c) in cells_of for (y, x) in target)

    cells = set()
    for i, p in enumerate(pieces):
        if i == owner[a]:
            travels = False
        elif i == owner[b]:
            travels = True
        else:
            travels = near(p, pieces[owner[b]]) < near(p, pieces[owner[a]])
        for (r, c) in p:
            cells.add((r + dr, c + dc) if travels else (r, c))

    r0 = min(r for r, _ in cells); r1 = max(r for r, _ in cells)
    c0 = min(c for _, c in cells); c1 = max(c for _, c in cells)
    out = [[bg] * (c1 - c0 + 1) for _ in range(r1 - r0 + 1)]
    for (r, c) in cells:
        out[r - r0][c - c0] = body
    return out
