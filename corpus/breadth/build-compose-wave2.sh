#!/usr/bin/env bash
# build-compose-wave2.sh [N=5000] [JOBS=8] --
# NEW x OLD compositions. FIRST component = one of the 766 wave2 v6 rules (evals/wave2-v6-rules.txt, the keys of
# synthetic-breadth-wave2/_MANIFEST-breadth.json; P4 held-out names are dropped by the composer), SECOND component = any non-P4
# breadth rule, drawn with p=0.5 from the last-pair high-loss breadth list (evals/hiloss-lastpair-breadth.txt) so the run leans
# toward rules FFT-002 finds hard. Through compose-build.py (harness gates + both-steps-matter), 2 blocks x 30 pairs, into
# synthetic-breadth-compose-wave2/. Stamps theme_source=compose-wave2, left/right rule, and the right rule's loss rank into each
# _meta.json and the manifest (colour_values_matter is already in every _meta from the harness), then runs corpus-verify.py;
# _VERIFIED is written only on a clean screen (invalid 0, pair_collisions 0, input_collisions 0).
# Resumable: compose-build.py skips an existing OUT/<name>/, so re-running with a larger N extends the tree. Log: logs/compose-wave2.log.
set -uo pipefail
N=${1:-5000}; JOBS=${2:-8}; R=$(cd "$(dirname "$0")/.." && pwd); D=$R/breadth; OUT=$R/synthetic-breadth-compose-wave2
LEFT=$R/evals/wave2-v6-rules.txt; RIGHT=$R/evals/hiloss-lastpair-breadth.txt; RANK=$R/evals/rule-loss/rule-loss-fft002.json
mkdir -p "$OUT" "$D/logs"; cd "$D"; rm -f "$OUT/_VERIFIED"
echo "== $(date '+%F %T') compose-wave2: left $(wc -l < "$LEFT") wave2 rules, right bias $(wc -l < "$RIGHT") high-loss rules p=0.5, N $N candidates, jobs $JOBS, seed 20261025, 2 blocks x 30 pairs"
COMPOSE_LEFT=$LEFT COMPOSE_RIGHT=$RIGHT COMPOSE_RIGHT_P=0.5 BREADTH_DEMOS=29,29 nice -n 10 python3 compose-build.py "$N" 20261025 "$OUT" 2 "$JOBS"
python3 - "$OUT" "$RANK" "$RIGHT" <<'PY'
import json, os, sys
OUT, RANK, RIGHT = sys.argv[1], sys.argv[2], sys.argv[3]
rank = {x['rule']: x for x in json.load(open(RANK))['ranked'] if x['source'] == 'breadth'}; hi = set(open(RIGHT).read().split())
man = json.load(open(os.path.join(OUT, '_MANIFEST-breadth.json'))); nhi = 0
for d, v in man['rules'].items():
    mp = os.path.join(OUT, d, '_meta.json'); m = json.load(open(mp)); a, b = d.split('__then__')
    m.update({'theme_source': 'compose-wave2', 'left_rule': a, 'right_rule': b, 'right_in_hiloss_list': b in hi, 'right_loss_rank': rank.get(b, {}).get('rank'), 'right_median_nll_fft002': rank.get(b, {}).get('median')})
    nhi += b in hi
    json.dump(m, open(mp, 'w')); v.update({k: m[k] for k in ('theme_source', 'left_rule', 'right_rule', 'right_in_hiloss_list', 'right_loss_rank', 'right_median_nll_fft002')})
man.update({'lane': 'breadth-compose-wave2', 'left_list': 'evals/wave2-v6-rules.txt', 'right_bias_list': 'evals/hiloss-lastpair-breadth.txt (p=0.5)', 'ranking': 'evals/rule-loss/rule-loss-fft002.json (last-pair median)'})
json.dump(man, open(os.path.join(OUT, '_MANIFEST-breadth.json'), 'w'), indent=1)
print(f"   manifest stamped: {man['distinct_rules']} compositions, {man['blocks']} blocks, {nhi} with a high-loss right component, theme_source=compose-wave2")
PY
echo "== $(date '+%F %T') screen: corpus-verify.py"
nice -n 10 python3 ../corpus-verify.py --pool "$OUT" --out ../corpus-verify-compose-wave2.json > logs/compose-wave2-verify.log 2>&1; tail -2 logs/compose-wave2-verify.log | cut -c1-300
T=$(grep -h "^TOTALS" logs/compose-wave2-verify.log | tail -1)
if echo "$T" | grep -q "'invalid': 0, 'pair_collisions': 0, 'input_collisions': 0"; then { echo "verified $(date '+%F %T')"; echo "$T"; } > "$OUT/_VERIFIED"; echo "   _VERIFIED written"; else echo "   NOT verified: $T"; fi
echo "== $(date '+%F %T') compose-wave2 done: $(ls "$OUT" | grep -vc '^_') compositions, $(find "$OUT" -name '*.json' ! -name '_*' | wc -l) blocks"
