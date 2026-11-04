"""8b7bacbf -- ink runs down the thread and fills the beads on it.

Closed rings lie about the grid like beads, and threads run between them,
ducking under each ring and coming out the far side.  At the loose end of a
thread sits a single cell of an ink colour.

Every ring strung on that thread is flooded with that ink.  Rings on a thread
with no ink at its end are left hollow, and so is everything else.
"""

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
N8 = N4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))


def _blobs(pool, near, shade=None):
    seen, out = set(), []
    for p in sorted(pool):
        if p in seen:
            continue
        st, comp = [p], []
        seen.add(p)
        while st:
            q = st.pop()
            comp.append(q)
            for dy, dx in near:
                n = (q[0] + dy, q[1] + dx)
                if n in pool and n not in seen and (shade is None or shade(n) == shade(q)):
                    seen.add(n)
                    st.append(n)
        out.append(comp)
    return out


def transform(gi):
    H, W = len(gi), len(gi[0])
    flat = [v for row in gi for v in row]
    bg = max(set(flat), key=flat.count)
    inks = [v for v in set(flat) if v != bg and flat.count(v) == 1]

    hollow = {(r, c) for r in range(H) for c in range(W) if gi[r][c] == bg}
    beads = []
    for hole in _blobs(hollow, N4):
        edge = set()
        for y, x in hole:
            for dy, dx in N4:
                n = (y + dy, x + dx)
                if 0 <= n[0] < H and 0 <= n[1] < W and gi[n[0]][n[1]] != bg:
                    edge.add(gi[n[0]][n[1]])
        if len(edge) != 1:
            continue
        shell = edge.pop()
        ring = set()
        for y, x in hole:
            for dy, dx in N8:
                n = (y + dy, x + dx)
                if 0 <= n[0] < H and 0 <= n[1] < W and gi[n[0]][n[1]] == shell:
                    ring.add(n)
        beads.append((hole, ring))

    worn = set().union(*[r for _, r in beads]) if beads else set()
    thread = {(r, c) for r in range(H) for c in range(W)
              if gi[r][c] != bg and (r, c) not in worn and gi[r][c] not in inks}
    strands = _blobs(thread, N8, lambda p: gi[p[0]][p[1]])

    # where two threads cross, one of them is hidden for a cell: rejoin its ends
    home = {}
    for i, s in enumerate(strands):
        for q in s:
            home[q] = i
    root = list(range(len(strands)))

    def find(i):
        while root[i] != i:
            root[i] = root[root[i]]
            i = root[i]
        return i

    for r in range(H):
        for c in range(W):
            if gi[r][c] == bg:
                continue
            mine = home.get((r, c))
            side = {home[(r + dy, c + dx)] for dy, dx in N8
                    if (r + dy, c + dx) in home and home[(r + dy, c + dx)] != mine}
            for a in side:
                for b in side:
                    if a != b and gi[strands[a][0][0]][strands[a][0][1]] == gi[strands[b][0][0]][strands[b][0][1]]:
                        root[find(a)] = find(b)
    joined = {}
    for i in range(len(strands)):
        joined.setdefault(find(i), []).extend(strands[i])
    strands = list(joined.values())

    go = [row[:] for row in gi]
    for ink in inks:
        spot = next((r, c) for r in range(H) for c in range(W) if gi[r][c] == ink)
        live = [i for i, s in enumerate(strands)
                if any((spot[0] + dy, spot[1] + dx) in set(s) for dy, dx in N8)]
        seen_s, seen_b = set(live), set()
        while live:
            nxt = []
            for i in live:
                cells = set(strands[i])
                for j, (hole, ring) in enumerate(beads):
                    if j in seen_b:
                        continue
                    if any((y + dy, x + dx) in cells for y, x in ring for dy, dx in N8):
                        seen_b.add(j)
                        for y, x in hole:
                            go[y][x] = ink
                        for k, s in enumerate(strands):
                            if k not in seen_s and any((y + dy, x + dx) in set(s)
                                                       for y, x in ring for dy, dx in N8):
                                seen_s.add(k)
                                nxt.append(k)
            live = nxt
    return go
