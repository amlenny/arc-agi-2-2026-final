#!/usr/bin/env bash
# finalise-compose-wave2.sh SCRIPT_PID COMPOSE_PID -- stop a running compose-wave2 build whatever it has reached
# (the composer is resumable, so a later re-run with the same seed extends the tree). Stops exactly those pids and their worker tree, then finalises what is on disk:
# manifest (compose-build.py's own manifest()), theme_source/left/right/rank stamps, corpus-verify.py; on input/pair collisions runs
# fix-compose-collisions.sh wave2 (archives the flagged blocks, re-screens); _VERIFIED only on a clean screen.
set -uo pipefail
SP=$1; CP=$2; R=$(cd "$(dirname "$0")/.." && pwd); OUT=$R/synthetic-breadth-compose-wave2; RANK=$R/evals/rule-loss/rule-loss-fft002.json; RIGHT=$R/evals/hiloss-lastpair-breadth.txt; cd "$R/breadth"
kids=$(pgrep -P "$CP"; for f in $(pgrep -P "$CP"); do pgrep -P "$f"; done)
echo "== $(date '+%F %T') stopping script $SP, composer $CP, children: $(echo $kids | tr '\n' ' ')"
kill "$SP" 2>/dev/null; kill "$CP" $kids 2>/dev/null; sleep 3
for p in $SP $CP $kids; do kill -0 "$p" 2>/dev/null && { echo "   $p still alive, SIGKILL"; kill -9 "$p"; }; done; sleep 1
echo "   alive after stop: $(for p in $SP $CP $kids; do kill -0 $p 2>/dev/null && echo -n "$p "; done)"
for d in "$OUT"/*/; do [ -f "$d/_meta.json" ] || { mkdir -p logs/compose-wave2-partial; mv "$d" logs/compose-wave2-partial/; echo "   partial dir set aside: $d"; }; done
python3 - "$OUT" "$RANK" "$RIGHT" <<'PY'
import json, os, sys, importlib.util
OUT, RANK, RIGHT = sys.argv[1], sys.argv[2], sys.argv[3]
sp = importlib.util.spec_from_file_location('cb', 'compose-build.py'); cb = importlib.util.module_from_spec(sp)
sys.argv = ['compose-build.py']; sp.loader.exec_module(cb)      # loads the harness and every rule file, no build (main is argv-guarded)
nr, nb = cb.manifest(OUT)
rank = {x['rule']: x for x in json.load(open(RANK))['ranked'] if x['source'] == 'breadth'}; hi = set(open(RIGHT).read().split())
man = json.load(open(os.path.join(OUT, '_MANIFEST-breadth.json'))); nhi = 0
for d, v in man['rules'].items():
    mp = os.path.join(OUT, d, '_meta.json'); m = json.load(open(mp)); a, b = d.split('__then__')
    m.update({'theme_source': 'compose-wave2', 'left_rule': a, 'right_rule': b, 'right_in_hiloss_list': b in hi, 'right_loss_rank': rank.get(b, {}).get('rank'), 'right_median_nll_fft002': rank.get(b, {}).get('median')})
    nhi += b in hi
    json.dump(m, open(mp, 'w')); v.update({k: m[k] for k in ('theme_source', 'left_rule', 'right_rule', 'right_in_hiloss_list', 'right_loss_rank', 'right_median_nll_fft002')})
man.update({'lane': 'breadth-compose-wave2', 'left_list': 'evals/wave2-v6-rules.txt', 'right_bias_list': 'evals/hiloss-lastpair-breadth.txt (p=0.5)', 'ranking': 'evals/rule-loss/rule-loss-fft002.json (last-pair median)', 'note': 'build stopped by pid; finalised from disk; resumable'})
json.dump(man, open(os.path.join(OUT, '_MANIFEST-breadth.json'), 'w'), indent=1)
print(f"   manifest: {nr} compositions, {nb} blocks, {sum(v['pairs'] for v in man['rules'].values() if v.get('pairs'))} pairs, {nhi} with a high-loss right component, distinct left rules {len(set(v['left_rule'] for v in man['rules'].values()))}")
PY
echo "== $(date '+%F %T') screen: corpus-verify.py"
nice -n 10 python3 ../corpus-verify.py --pool "$OUT" --out ../corpus-verify-compose-wave2.json > logs/compose-wave2-verify.log 2>&1 || true
T=$(grep -h "^TOTALS" logs/compose-wave2-verify.log | tail -1); echo "$T" | cut -c1-300
if echo "$T" | grep -q "'invalid': 0, 'pair_collisions': 0, 'input_collisions': 0"; then { echo "verified $(date '+%F %T')"; echo "$T"; } > "$OUT/_VERIFIED"; echo "   _VERIFIED written"
elif echo "$T" | grep -q "'invalid': 0,"; then echo "   collisions flagged -> fix-compose-collisions.sh wave2"; ./fix-compose-collisions.sh wave2
else echo "   NOT verified (invalid blocks): $T"; fi
echo "== $(date '+%F %T') compose-wave2 finalised: $(ls "$OUT" | grep -vc '^_') compositions, $(find "$OUT" -name '*.json' ! -name '_*' | wc -l) blocks; _VERIFIED: $(cat "$OUT/_VERIFIED" 2>/dev/null | head -1 || echo absent)"
