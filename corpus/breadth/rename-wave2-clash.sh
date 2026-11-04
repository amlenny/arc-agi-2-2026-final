#!/usr/bin/env bash
# rename-wave2-clash.sh -- two b078_counting2 rules reused names already registered by b011/b076; the rule definitions
# were renamed, and this renames the matching synthetic-breadth-wave2 directories, their block files, _meta.source and the manifest keys
# to the new names, then re-runs corpus-verify.py and rewrites _VERIFIED only on a clean screen. Blocks themselves are untouched.
set -euo pipefail
R=$(cd "$(dirname "$0")/.." && pwd); OUT=$R/synthetic-breadth-wave2; cd "$R/breadth"; mkdir -p logs
declare -A NEW=([object_count_binary_row]=object_count_binary_row_blue_green [largest_minus_second_largest_bar]=largest_minus_second_largest_bar_marked)
rm -f "$OUT/_VERIFIED"; cp "$OUT/_MANIFEST-breadth.json" "logs/wave2-manifest.bak-$(date +%H%M).json"
for old in "${!NEW[@]}"; do new=${NEW[$old]}
  [ -d "$OUT/$old" ] || { echo "   $old: directory absent, skipping"; continue; }
  mv "$OUT/$old" "$OUT/$new"
  for f in "$OUT/$new/${old}_"*.json; do mv "$f" "$OUT/$new/${new}_${f##*/${old}_}"; done
  python3 - "$OUT" "$old" "$new" <<'PY'
import json, os, sys
OUT, old, new = sys.argv[1:4]
mp = os.path.join(OUT, new, '_meta.json'); m = json.load(open(mp)); m['source'] = new; m['renamed_from'] = old; json.dump(m, open(mp, 'w'))
man = json.load(open(os.path.join(OUT, '_MANIFEST-breadth.json'))); man['rules'][new] = man['rules'].pop(old); man['rules'][new]['renamed_from'] = old
json.dump(man, open(os.path.join(OUT, '_MANIFEST-breadth.json'), 'w'), indent=1)
print(f"   {old} -> {new}: {len([f for f in os.listdir(os.path.join(OUT, new)) if not f.startswith('_')])} blocks, _meta.source and manifest key updated")
PY
done
echo "== $(date '+%F %T') screen: corpus-verify.py on $OUT"
nice -n 10 python3 ../corpus-verify.py --pool "$OUT" --out ../corpus-verify-wave2.json > logs/wave2-verify.log 2>&1 || true
T=$(grep -h "^TOTALS" logs/wave2-verify.log | tail -1); echo "$T" | cut -c1-300
if echo "$T" | grep -q "'invalid': 0, 'pair_collisions': 0, 'input_collisions': 0"; then { echo "verified $(date '+%F %T')"; echo "$T"; } > "$OUT/_VERIFIED"; echo "   _VERIFIED rewritten"; else echo "   NOT verified"; fi
echo "== $(date '+%F %T') rename done: $(ls "$OUT" | grep -vc '^_') rules, $(find "$OUT" -name '*.json' ! -name '_*' | wc -l) blocks"
