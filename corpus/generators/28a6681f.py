# Rule authored from the evaluation demonstrations of 28a6681f.
#
# COLOUR 1 IS WATER. It is conserved because nothing creates or destroys it — it falls, spreads
# along the surface, and comes to rest wherever the shapes can hold it. That is why "which cells
# get filled" resisted a local predicate: horizontal flanking is necessary because a resting cell
# has walls beside it, and it over-generates because most flanked cells are in basins the water
# never reaches.
#
# The two things a static rule cannot see, both visible the moment the grids are drawn:
#   * a basin that LEAKS holds nothing. Demo 2's V is wide open at the top and looks like the
#     obvious container, but its point is not sealed — the water drains straight through it into
#     the small yellow cup underneath, which is where it ends up.
#   * water OVERFLOWS. Demo 0's reservoir fills to the top of the wall beside it and the surplus
#     runs over, falls down the next channel and fills that instead. The 4 cells that move are
#     exactly that channel's capacity.
#
# So this is simulated rather than predicated. Water falls if it can, otherwise slides along its
# own surface to the nearest column where it can fall, which levels a pool flat by itself.
# WATER IS NAMED BY ITS COLOUR because nothing in a grid distinguishes it. Every colour's count is
# conserved, so conservation names nothing. Water is a solid rectangle touching the top edge in
# demo 0 and neither in demo 1. It is the heaviest non-board colour in demos 0 and 1 and the
# lightest in demo 2. No cell of any colour is left unsupported in demos 0 and 1, so a test for
# "has not settled yet" separates nothing either.
WATER = 1


def transform(grid):
    h, w = len(grid), len(grid[0])
    wall = [[grid[r][c] not in (0, WATER) for c in range(w)] for r in range(h)]
    units = [(r, c) for r in range(h) for c in range(w) if grid[r][c] == WATER]
    wet = [[False] * w for _ in range(h)]

    def solid(r, c):
        return not (0 <= r < h) or not (0 <= c < w) or wall[r][c] or wet[r][c]

    # LOWEST UNIT FIRST. A basin fills from the bottom, so the units that are already deep settle
    # first and the ones above them become the surplus that runs over the rim. Settling the top
    # ones first strands them in basins the lower water would have filled anyway.
    for (sr, sc) in sorted(units, key=lambda p: -p[0]):
        r, c = sr, sc
        for _ in range(4 * h * w):
            if not solid(r + 1, c):
                r += 1
                continue
            # cannot fall: run along the surface for the nearest column that can, not crossing a
            # wall and not passing through water already at rest
            best = None
            for d in (-1, 1):
                k = c + d
                while 0 <= k < w and not wall[r][k] and not wet[r][k]:
                    if not solid(r + 1, k):
                        if best is None or abs(k - c) < abs(best - c):
                            best = k
                        break
                    k += d
            if best is None:
                break
            c = best
        wet[r][c] = True

    return [[WATER if wet[r][c] else (grid[r][c] if wall[r][c] else 0)
             for c in range(w)] for r in range(h)]
