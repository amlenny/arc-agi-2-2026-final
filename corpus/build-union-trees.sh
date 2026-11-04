#!/usr/bin/env bash
# build-union-trees.sh -- the three symlink union trees the hops stage from. Run after the source trees exist.
#   synthetic-breadth-union13      compose + wave2 (5,308 rules)
#   synthetic-breadth-union16      compose + wave2 + compose-wave2 + compose-hiloss + hiloss (8,290 rules)
#   synthetic-breadth-union-hiloss hiloss + compose-hiloss (1,390 rules)
# Earlier trees in a list win when a rule name occurs twice; compose and compose-hiloss share one name.
set -euo pipefail
cd "$(dirname "$0")"
union() {  # union <out> <tree> ...
  local out=$1; shift
  rm -rf "$out"; mkdir "$out"
  local n=0 t r b
  for t in "$@"; do
    for r in "$t"/*/; do
      b=$(basename "$r"); case $b in _*) continue;; esac
      [ -e "$out/$b" ] && continue
      ln -s "../$t/$b" "$out/$b"; n=$((n+1))
    done
  done
  echo "$out: $n rules"
}
union synthetic-breadth-union13 synthetic-breadth-compose synthetic-breadth-wave2
union synthetic-breadth-union16 synthetic-breadth-compose synthetic-breadth-wave2 synthetic-breadth-compose-wave2 synthetic-breadth-compose-hiloss synthetic-breadth-hiloss
union synthetic-breadth-union-hiloss synthetic-breadth-hiloss synthetic-breadth-compose-hiloss
