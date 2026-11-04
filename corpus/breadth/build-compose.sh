#!/usr/bin/env bash
# build-compose.sh [JOBS_A=8] [JOBS_B=3] -- the synthetic-breadth-compose tree, with the two recorded compose-build.py commands.
# Both original runs were stopped by hand once enough compositions existed, and the tree's manifest was written from what was
# on disk (4,542 compositions, 9,056 blocks). This script lets both runs finish, so it visits more candidates than they did.
# compose-build.py skips a composition that already has a directory, and writes the manifest when it finishes.
set -uo pipefail
JA=${1:-8}; JB=${2:-3}; cd "$(dirname "$0")"; OUT=../synthetic-breadth-compose; mkdir -p logs
BREADTH_DEMOS=29,29 BREADTH_SEED_SALT=compose1 COMPOSE_TIMEOUT=60 nice -n 10 python3 compose-build.py 20000 1 "$OUT" 2 "$JA" > logs/compose1-build.log 2>&1
BREADTH_DEMOS=29,29 BREADTH_SEED_SALT=compose1 COMPOSE_TIMEOUT=60 nice -n 10 python3 compose-build.py 8000 2 "$OUT" 2 "$JB" > logs/compose1b-build.log 2>&1
tail -n 1 logs/compose1b-build.log
