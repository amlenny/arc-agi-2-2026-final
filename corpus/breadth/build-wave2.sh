#!/usr/bin/env bash
# build-wave2.sh [BLOCKS=3] [JOBS=3] -- the authoring wave 2 tree (new primitive rules, 30-pair blocks,
# own tree, staged with nv-stage.py --breadth-dir synthetic-breadth-wave2 --br-samples K). Builds every batch
# listed in WAVE2_BATCHES (default: rules/b066*.py and up) under BREADTH_SEED_SALT=wave2 with BREADTH_DEMOS=29,29 (30 pairs per
# block), BLOCKS blocks per rule, then stamps "theme_source" into every <rule>/_meta.json and the manifest (eval-category for
# batches seeded from never-generated eval cues, loss-family for batches drawn from the rule-loss ranking; see THEME_SOURCE below),
# then runs the independent screen corpus-verify.py on the tree. Idempotent: the same salt regenerates the same blocks, so
# re-running after new batches land only adds the new rules. Logs: breadth/logs/wave2-<batch>.log.
set -uo pipefail
BLOCKS=${1:-3}; JOBS=${2:-3}; R=$(cd "$(dirname "$0")/.." && pwd); D=$R/breadth; OUT=$R/synthetic-breadth-wave2
mkdir -p $OUT $D/logs; cd $D
BATCHES=${WAVE2_BATCHES:-$(ls rules/b0[6-9][6-9]*.py rules/b0[7-9]*.py rules/b[1-9]*.py 2>/dev/null | sort -u | tr '\n' ' ')}
echo "== $(date '+%F %T') wave2 build: blocks $BLOCKS jobs $JOBS batches: $BATCHES"
echo $BATCHES | tr ' ' '\n' | xargs -P $JOBS -I{} sh -c 'b=$(basename {} .py); BREADTH_DEMOS=29,29 BREADTH_SEED_SALT=wave2 nice -n 10 python3 build-breadth.py --batch {} --blocks '"$BLOCKS"' --min-blocks 1 --out '"$OUT"' > logs/wave2-$b.log 2>&1; echo "   $b: $(tail -1 logs/wave2-$b.log)"'
# theme_source per batch (edit THEME_SOURCE as batches are added)
python3 - "$OUT" <<'PY'
import json, os, sys
OUT = sys.argv[1]
THEME_SOURCE = {"b066_flowfill.py": "eval-category", "b067_locks.py": "eval-category", "b068_plumbing.py": "eval-category",
                "b069_cuts.py": "eval-category", "b070_sockets.py": "eval-category", "b071_tallies.py": "eval-category",
                "b072_trim.py": "eval-category", "b073_motif.py": "eval-category", "b074_selfkeys.py": "eval-category", "b075_pivots.py": "generic",
                "b076_legends2.py": "loss-family", "b077_crosstabs2.py": "loss-family", "b078_counting2.py": "loss-family", "b079_setops2.py": "loss-family", "b080_sequences2.py": "loss-family", "b081_selection2.py": "loss-family", "b082_indexpanels2.py": "loss-family",
                "b083_assembly2.py": "loss-family", "b084_pipelines2.py": "loss-family", "b085_overlays2.py": "loss-family", "b086_summary_pipelines.py": "loss-family", "b087_keyed_summaries.py": "loss-family"}
man = {}; n = 0
for d in sorted(os.listdir(OUT)):
    mp = os.path.join(OUT, d, "_meta.json")
    if not os.path.exists(mp): continue
    m = json.load(open(mp)); m["theme_source"] = THEME_SOURCE.get(m.get("batch", ""), "loss-family"); json.dump(m, open(mp, "w")); n += 1
    man[d] = {k: m.get(k) for k in ("batch", "desc", "rule_sha", "blocks", "pairs", "digits", "colour_values_matter", "primitive", "big_input_share", "theme_source")}
json.dump({"lane": "breadth-wave2", "rules": man, "distinct_rules": len(man), "blocks": sum(v["blocks"] for v in man.values())}, open(os.path.join(OUT, "_MANIFEST-breadth.json"), "w"), indent=1)
print(f"   stamped theme_source on {n} rules; manifest {len(man)} rules, {sum(v['blocks'] for v in man.values())} blocks")
PY
echo "== $(date '+%F %T') screen: corpus-verify.py"
nice -n 10 python3 ../corpus-verify.py --pool $OUT --out ../corpus-verify-wave2.json > logs/wave2-verify.log 2>&1; tail -2 logs/wave2-verify.log
T=$(grep -h "^TOTALS" logs/wave2-verify.log | tail -1); if echo "$T" | grep -q "'invalid': 0, 'pair_collisions': 0, 'input_collisions': 0"; then { echo "verified $(date '+%F %T')"; echo "$T"; } > $OUT/_VERIFIED; echo "   _VERIFIED written"; else rm -f $OUT/_VERIFIED; echo "   SCREEN NOT CLEAN: _VERIFIED removed"; fi
echo "== $(date '+%F %T') wave2 done: $(ls $OUT | grep -vc '^_') rules, $(find $OUT -name '*.json' ! -name '_*' | wc -l) blocks"
