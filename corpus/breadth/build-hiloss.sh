#!/usr/bin/env bash
# build-hiloss.sh [BLOCKS=3] [JOBS=3] -- the high-loss breadth tree (from the rule-loss ranking of FFT-002):
# rebuilds the rules listed in evals/hiloss-rules.txt (top breadth rules by all-pair median NLL, P4 held-out rules excluded) under
# BREADTH_SEED_SALT=hiloss with BREADTH_DEMOS=29,29 (30-pair blocks), BLOCKS per rule, into synthetic-breadth-hiloss/, then stamps
# theme_source=loss-family plus the rule's rank and median NLL into each <rule>/_meta.json and the manifest, then runs corpus-verify.py.
set -uo pipefail
BLOCKS=${1:-3}; JOBS=${2:-3}; R=$(cd "$(dirname "$0")/.." && pwd); D=$R/breadth; OUT=$R/synthetic-breadth-hiloss
LIST=$R/evals/hiloss-rules.txt; mkdir -p $OUT $D/logs; cd $D
echo "== $(date '+%F %T') hiloss build: $(wc -l < $LIST) rules, blocks $BLOCKS, jobs $JOBS"
split -n l/$JOBS -d $LIST $D/logs/hiloss-chunk-
for c in $D/logs/hiloss-chunk-*; do
  ( BREADTH_DEMOS=29,29 BREADTH_SEED_SALT=hiloss nice -n 10 python3 build-breadth.py --only "$(tr '\n' ',' < $c | sed 's/,$//')" --blocks $BLOCKS --min-blocks 1 --out $OUT > logs/hiloss-$(basename $c).log 2>&1; echo "   $(basename $c): $(tail -1 logs/hiloss-$(basename $c).log)" ) &
done; wait
python3 - "$OUT" <<'PY'
import json, os, sys
OUT = sys.argv[1]; rank = json.load(open('../evals/hiloss-rank.json')); man = {}
for d in sorted(os.listdir(OUT)):
    mp = os.path.join(OUT, d, '_meta.json')
    if not os.path.exists(mp): continue
    m = json.load(open(mp)); m['theme_source'] = 'loss-family'; m.update({'loss_rank': rank.get(d, {}).get('rank'), 'median_nll_fft002': rank.get(d, {}).get('median_nll')}); json.dump(m, open(mp, 'w'))
    man[d] = {k: m.get(k) for k in ('batch', 'desc', 'rule_sha', 'blocks', 'pairs', 'digits', 'colour_values_matter', 'primitive', 'big_input_share', 'theme_source', 'loss_rank', 'median_nll_fft002')}
json.dump({'lane': 'breadth-hiloss', 'ranking': 'evals/rule-loss/rule-loss-fft002-allpair.json (preliminary, all-pair median)', 'rules': man, 'distinct_rules': len(man), 'blocks': sum(v['blocks'] for v in man.values())}, open(os.path.join(OUT, '_MANIFEST-breadth.json'), 'w'), indent=1)
print(f"   manifest: {len(man)} rules, {sum(v['blocks'] for v in man.values())} blocks, theme_source=loss-family")
PY
nice -n 10 python3 ../corpus-verify.py --pool $OUT --out ../corpus-verify-hiloss.json > logs/hiloss-verify.log 2>&1; tail -1 logs/hiloss-verify.log | cut -c1-200
echo "== $(date '+%F %T') hiloss done: $(ls $OUT | grep -vc '^_') rules, $(find $OUT -name '*.json' ! -name '_*' | wc -l) blocks"
