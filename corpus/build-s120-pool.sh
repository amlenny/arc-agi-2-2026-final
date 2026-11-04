#!/usr/bin/env bash
# build-s120-pool.sh [synthetic|fresh|all] -- one ordered pass over the S120 pools, using the task lists and counts in
# s120-build-plan.json. Two trees come out:
#   synthetic/              the pool hop 3's picks came from; also the packer's --holdout-root
#   ours-fresh-20261003/    the pool nv-stage.py draws from in every later hop (nbrB, nbrB-doesnt-fixed, fft-nbrB, fft-nbrB-doesnt-fixed, midband)
# The original pools were built in several passes while skeletons were being corrected. This script runs the final skeletons once
# at the final counts; salts and seeds are the recorded ones. It does not reproduce the original files byte for byte.
set -euo pipefail
cd "$(dirname "$0")"
WHAT=${1:-all}; J=${JOBS:-4}; F=ours-fresh-20261003
plan() { python3 -c "import json,sys; p=json.load(open('s120-build-plan.json')); exec(sys.argv[1])" "$1"; }

# synthetic/: one builder per lane, per-grade and holdout counts from each task's recorded _meta.json.
build_synthetic() {
  plan "
for t,v in p['synthetic'].items(): print(v['lane'],t,v['per_grade'],v['holdout_per_grade'])" | while read -r lane t per hold; do
    if [ "$lane" = midband ]; then
      python3 crucible-build-midband.py --only "$t" --per-grade "$per" --holdout-per-grade "$hold"
    else
      NBR_OUT=synthetic NBR_ONLY="$t" NBR_PER_GRADE="$per" NBR_HOLDOUT_PER_GRADE="$hold" NBR_VERIFY_TRIES=4000 python3 -u build-neighborhoods.py
    fi
  done
}

# ours-fresh-20261003/: midband, then the dedup index, then nbrB, then the FFT-format blocks (5-7 demos), as recorded.
build_fresh() {
  mkdir -p "$F"
  python3 crucible-build-midband.py --out ours-fresh-tmp-midband --seed 20261003 --per-grade 55 --holdout-per-grade 0
  python3 crucible-build-midband.py --out ours-fresh-tmp-midband --seed 20261004 --per-grade 75 --holdout-per-grade 0
  python3 screen-ours-fresh.py ours-fresh-tmp-midband midband "$F" 196
  python3 - <<'PY'
import importlib.util, os, pickle, sys
sys.argv = ["x"]
sp = importlib.util.spec_from_file_location("pk", "ours-fresh-package.py"); pk = importlib.util.module_from_spec(sp); sp.loader.exec_module(pk)
pickle.dump(pk.existing_index(os.path.abspath("ours-fresh-20261003")), open("ours-fresh-20261003/_existing-index.pkl", "wb"))
PY
  local IDX=$F/_existing-index.pkl MAIN DOES SALT PER ALL k t per
  MAIN=$(plan "print(','.join(p['fresh_nbrB']['tasks']))"); DOES=$(plan "print(','.join(p['fresh_nbrB']['doesnt_fixed']))")
  SALT=$(plan "print(p['fresh_nbrB']['salt'])"); PER=$(plan "print(p['fresh_nbrB']['per_grade'])")
  NBR_OUT=$F/_build-nbrB NBR_ONLY="$MAIN,$DOES" NBR_PER_GRADE=$PER NBR_HOLDOUT_PER_GRADE=0 NBR_VERIFY_TRIES=4000 NBR_SEED_SALT=$SALT python3 -u build-neighborhoods.py
  python3 ours-fresh-package.py --kind nbrB --build "$F/_build-nbrB" --out "$F/nbrB" --tasks "$MAIN" --index-cache "$IDX"
  python3 ours-fresh-package.py --kind nbrB --build "$F/_build-nbrB" --out "$F/nbrB-doesnt-fixed" --tasks "$DOES" --per-task 187 --index-cache "$IDX"
  SALT=$(plan "print(p['fresh_fft']['salt'])")
  for k in 5 6 7; do
    plan "
for t,n in p['fresh_fft']['groups']['$k']['per_grade'].items(): print(t,n)" | while read -r t per; do
      NBR_OUT=$F/_build-fft-k$k NBR_ONLY=$t NBR_PER_GRADE=$per NBR_HOLDOUT_PER_GRADE=0 NBR_VERIFY_TRIES=4000 NBR_DEMOS=$k NBR_SEED_SALT=$SALT python3 -u build-neighborhoods.py
    done
    ALL=$(plan "print(','.join(p['fresh_fft']['groups']['$k']['fft_nbrB']))")
    python3 ours-fresh-package.py --kind nbrB --build "$F/_build-fft-k$k" --out "$F/fft-nbrB/k$k" --tasks "$ALL" --per-task 100000 --demos "$k" --index-cache "$IDX"
    ALL=$(plan "print(','.join(p['fresh_fft']['groups']['$k']['fft_nbrB_doesnt_fixed']))")
    python3 ours-fresh-package.py --kind nbrB --build "$F/_build-fft-k$k" --out "$F/fft-nbrB-doesnt-fixed/k$k" --tasks "$ALL" --per-task 100000 --demos "$k" --index-cache "$IDX"
  done
}

case $WHAT in
  synthetic) build_synthetic;;
  fresh)     build_fresh;;
  all)       build_synthetic; build_fresh;;
  *)         echo "usage: $0 [synthetic|fresh|all]" >&2; exit 2;;
esac
