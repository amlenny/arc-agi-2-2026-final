#!/usr/bin/env bash
# finalise-compose-hiloss.sh SCRIPT_PID COMPOSE_PID -- stop a stalled compose-hiloss build and keep what it wrote
# (the recorded build stalled after 3800/4000 candidates: one worker ran one candidate for hours: compose-build.py's _TO timeout subclasses Exception and the both-steps-matter check swallows
# Exception, so the alarm fired once and was eaten). Stops exactly those pids and their worker tree, then finalises what is on disk:
# manifest (compose-build.py's own manifest()), theme_source/rank stamps, corpus-verify.py, _VERIFIED only on a clean screen.
set -uo pipefail
SP=$1; CP=$2; R=$(cd "$(dirname "$0")/.." && pwd); OUT=$R/synthetic-breadth-compose-hiloss; RANK=$R/evals/rule-loss/rule-loss-fft002.json; cd "$R/breadth"
kids=$(pgrep -P "$CP"; for f in $(pgrep -P "$CP"); do pgrep -P "$f"; done)
echo "== $(date '+%F %T') stopping script $SP, composer $CP, children: $(echo $kids | tr '\n' ' ')"
kill "$SP" 2>/dev/null; kill "$CP" $kids 2>/dev/null; sleep 3
for p in $SP $CP $kids; do kill -0 "$p" 2>/dev/null && { echo "   $p still alive, SIGKILL"; kill -9 "$p"; }; done; sleep 1
echo "   alive after stop: $(for p in $SP $CP $kids; do kill -0 $p 2>/dev/null && echo -n "$p "; done)"
for d in "$OUT"/*/; do [ -f "$d/_meta.json" ] || { mkdir -p logs/compose-hiloss-partial; mv "$d" logs/compose-hiloss-partial/; echo "   partial dir set aside: $d"; }; done
python3 - "$OUT" "$RANK" <<'PY'
import json, os, sys, importlib.util
OUT, RANK = sys.argv[1], sys.argv[2]
sp = importlib.util.spec_from_file_location('cb', 'compose-build.py'); cb = importlib.util.module_from_spec(sp)
sys.argv = ['compose-build.py']; sp.loader.exec_module(cb)      # loads the harness and every rule file, no build (main is argv-guarded)
nr, nb = cb.manifest(OUT)
rank = {x['rule']: x for x in json.load(open(RANK))['ranked'] if x['source'] == 'breadth'}
man = json.load(open(os.path.join(OUT, '_MANIFEST-breadth.json')))
for d, v in man['rules'].items():
    mp = os.path.join(OUT, d, '_meta.json'); m = json.load(open(mp)); a = d.split('__then__')[0]
    m.update({'theme_source': 'compose-hiloss', 'left_rule': a, 'left_loss_rank': rank.get(a, {}).get('rank'), 'left_median_nll_fft002': rank.get(a, {}).get('median')})
    json.dump(m, open(mp, 'w')); v.update({k: m[k] for k in ('theme_source', 'left_rule', 'left_loss_rank', 'left_median_nll_fft002')})
man.update({'lane': 'breadth-compose-hiloss', 'ranking': 'evals/rule-loss/rule-loss-fft002.json (last-pair median)', 'left_list': 'evals/hiloss-lastpair-breadth.txt', 'note': 'build stopped at ~3800/4000 candidates (stalled worker); finalised from disk'})
json.dump(man, open(os.path.join(OUT, '_MANIFEST-breadth.json'), 'w'), indent=1)
print(f"   manifest: {nr} compositions, {nb} blocks, {sum(v['pairs'] for v in man['rules'].values() if v.get('pairs'))} pairs, distinct left rules {len(set(v['left_rule'] for v in man['rules'].values()))}")
PY
echo "== $(date '+%F %T') screen: corpus-verify.py"
nice -n 10 python3 ../corpus-verify.py --pool "$OUT" --out ../corpus-verify-compose-hiloss.json > logs/compose-hiloss-verify.log 2>&1 || true
T=$(grep -h "^TOTALS" logs/compose-hiloss-verify.log | tail -1); echo "$T" | cut -c1-300
if echo "$T" | grep -q "'invalid': 0, 'pair_collisions': 0, 'input_collisions': 0"; then { echo "verified $(date '+%F %T')"; echo "$T"; } > "$OUT/_VERIFIED"; echo "   _VERIFIED written"; else echo "   NOT verified"; fi
echo "== $(date '+%F %T') compose-hiloss finalised: $(ls "$OUT" | grep -vc '^_') compositions, $(find "$OUT" -name '*.json' ! -name '_*' | wc -l) blocks"
