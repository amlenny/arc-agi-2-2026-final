#!/usr/bin/env bash
# build-compose-hiloss.sh [N=4000] [JOBS=6] -- from the last-pair rule-loss ranking of FFT-002: compositions whose FIRST
# component is one of the high-loss breadth rules in evals/hiloss-lastpair-breadth.txt (the 179 breadth rules in the last-pair top 400,
# P4 held-out rules removed) and whose second component is any non-P4 breadth rule, through compose-build.py (harness gates + the
# both-steps-matter gate), 2 blocks of 30 pairs per composition, into synthetic-breadth-compose-hiloss/. Stamps theme_source=compose-hiloss
# and the left rule's rank/median into each _meta.json and the manifest, then runs corpus-verify.py; _VERIFIED is written only on a
# clean screen (invalid 0, pair_collisions 0, input_collisions 0).
# Resumable: compose-build.py skips an existing OUT/<name>/, so re-running with a larger N extends the tree.
set -uo pipefail
N=${1:-4000}; JOBS=${2:-6}; R=$(cd "$(dirname "$0")/.." && pwd); D=$R/breadth; OUT=$R/synthetic-breadth-compose-hiloss
LIST=$R/evals/hiloss-lastpair-breadth.txt; RANK=$R/evals/rule-loss/rule-loss-fft002.json; mkdir -p "$OUT" "$D/logs"; cd "$D"; rm -f "$OUT/_VERIFIED"
echo "== $(date '+%F %T') compose-hiloss: left $(wc -l < "$LIST") rules, N $N candidates, jobs $JOBS, seed 20261024, 2 blocks x 30 pairs"
COMPOSE_LEFT=$LIST BREADTH_DEMOS=29,29 nice -n 10 python3 compose-build.py "$N" 20261024 "$OUT" 2 "$JOBS"
python3 - "$OUT" "$RANK" <<'PY'
import json, os, sys
OUT, RANK = sys.argv[1], sys.argv[2]
rank = {x['rule']: x for x in json.load(open(RANK))['ranked'] if x['source'] == 'breadth'}
man = json.load(open(os.path.join(OUT, '_MANIFEST-breadth.json')))
for d, v in man['rules'].items():
    mp = os.path.join(OUT, d, '_meta.json'); m = json.load(open(mp)); a = d.split('__then__')[0]
    m.update({'theme_source': 'compose-hiloss', 'left_rule': a, 'left_loss_rank': rank.get(a, {}).get('rank'), 'left_median_nll_fft002': rank.get(a, {}).get('median')})
    json.dump(m, open(mp, 'w')); v.update({k: m[k] for k in ('theme_source', 'left_rule', 'left_loss_rank', 'left_median_nll_fft002')})
man.update({'lane': 'breadth-compose-hiloss', 'ranking': 'evals/rule-loss/rule-loss-fft002.json (last-pair median)', 'left_list': 'evals/hiloss-lastpair-breadth.txt'})
json.dump(man, open(os.path.join(OUT, '_MANIFEST-breadth.json'), 'w'), indent=1)
print(f"   manifest stamped: {man['distinct_rules']} compositions, {man['blocks']} blocks, theme_source=compose-hiloss")
PY
echo "== $(date '+%F %T') screen: corpus-verify.py"
nice -n 10 python3 ../corpus-verify.py --pool "$OUT" --out ../corpus-verify-compose-hiloss.json > logs/compose-hiloss-verify.log 2>&1; tail -2 logs/compose-hiloss-verify.log | cut -c1-300
T=$(grep -h "^TOTALS" logs/compose-hiloss-verify.log | tail -1)
if echo "$T" | grep -q "'invalid': 0, 'pair_collisions': 0, 'input_collisions': 0"; then { echo "verified $(date '+%F %T')"; echo "$T"; } > "$OUT/_VERIFIED"; echo "   _VERIFIED written"; else echo "   NOT verified: $T"; fi
echo "== $(date '+%F %T') compose-hiloss done: $(ls "$OUT" | grep -vc '^_') compositions, $(find "$OUT" -name '*.json' ! -name '_*' | wc -l) blocks"
