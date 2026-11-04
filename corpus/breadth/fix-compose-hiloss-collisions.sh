#!/usr/bin/env bash
# fix-compose-hiloss-collisions.sh -- corpus-verify flagged input collisions (block inputs equal to ARC train1000 inputs) in the
# compose-hiloss tree, all from one-row digit left components (digit_row_unrolled_to_runs, run_length_encode_row), as in the hiloss tree.
# Moves each flagged block to breadth/logs/compose-hiloss-collisions/ (archive, not delete), fixes the composition's _meta blocks/pairs
# and the manifest, sets aside any composition left with no blocks, re-runs the screen and writes _VERIFIED only on a clean TOTALS.
set -uo pipefail
R=$(cd "$(dirname "$0")/.." && pwd); OUT=$R/synthetic-breadth-compose-hiloss; cd "$R/breadth"; A=logs/compose-hiloss-collisions; mkdir -p "$A"
python3 - "$OUT" "$A" <<'PY'
import json, os, sys, shutil
OUT, A = sys.argv[1], sys.argv[2]
v = json.load(open(os.path.join(OUT, '..', 'corpus-verify-compose-hiloss.json')))
man = json.load(open(os.path.join(OUT, '_MANIFEST-breadth.json'))); moved = 0; emptied = []
for t in v['tasks']:
    files = sorted({c[0] for c in t['input_collisions']} | {c[0] for c in t['pair_collisions']})
    if not files: continue
    d = os.path.join(OUT, t['task'])
    for f in files:
        os.makedirs(os.path.join(A, t['task']), exist_ok=True); shutil.move(os.path.join(d, f), os.path.join(A, t['task'], f)); moved += 1
    left = [f for f in os.listdir(d) if f.endswith('.json') and not f.startswith('_')]
    mp = os.path.join(d, '_meta.json'); m = json.load(open(mp))
    per = (m.get('pairs') or 0) // max(m.get('blocks') or 1, 1)
    m['blocks'] = len(left); m['pairs'] = per * len(left); m['collision_blocks_removed'] = files; json.dump(m, open(mp, 'w'))
    if left: man['rules'][t['task']].update({'blocks': m['blocks'], 'pairs': m['pairs']})
    else:
        shutil.move(d, os.path.join(A, t['task'] + '.emptied')); man['rules'].pop(t['task']); emptied.append(t['task'])
    print(f"   {t['task']}: moved {len(files)} block(s), {len(left)} left")
man['distinct_rules'] = len(man['rules']); man['blocks'] = sum(x['blocks'] for x in man['rules'].values())
json.dump(man, open(os.path.join(OUT, '_MANIFEST-breadth.json'), 'w'), indent=1)
print(f"   moved {moved} blocks to {A}; compositions emptied and set aside: {emptied}; manifest now {man['distinct_rules']} compositions, {man['blocks']} blocks")
PY
echo "== $(date '+%F %T') re-screen"
nice -n 10 python3 ../corpus-verify.py --pool "$OUT" --out ../corpus-verify-compose-hiloss.json > logs/compose-hiloss-verify.log 2>&1 || true
T=$(grep -h "^TOTALS" logs/compose-hiloss-verify.log | tail -1); echo "$T" | cut -c1-300
if echo "$T" | grep -q "'invalid': 0, 'pair_collisions': 0, 'input_collisions': 0"; then { echo "verified $(date '+%F %T')"; echo "$T"; } > "$OUT/_VERIFIED"; echo "   _VERIFIED written"; else echo "   NOT verified"; fi
echo "== $(date '+%F %T') done: $(ls "$OUT" | grep -vc '^_') compositions, $(find "$OUT" -name '*.json' ! -name '_*' | wc -l) blocks"
