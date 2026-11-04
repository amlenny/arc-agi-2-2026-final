#!/usr/bin/env bash
# fetch-data.sh -- download the public datasets the pipeline reads, at the exact commits we used, into crucible/.
# Needs git; the Kaggle steps need the kaggle CLI with credentials and accepted competition rules.
#   ./fetch-data.sh            ARC-AGI-2, ARC-AGI-1, ConceptARC, MINI-ARC (git, about 50 MB)
#   ./fetch-data.sh --kaggle   also the competition JSON (data-kaggle) and NVARC's synthetic puzzles (6 GB, hop 3 only)
set -euo pipefail
cd "$(dirname "$0")/crucible"
clone() {   # clone <dir> <url> <commit>
  if [ -d "$1/.git" ]; then echo "have $1"; else git clone -q "$2" "$1"; fi
  git -C "$1" -c advice.detachedHead=false checkout -q "$3"; echo "$1 @ $(git -C "$1" rev-parse --short HEAD)"
}
clone data-arc-agi-2            https://github.com/arcprize/ARC-AGI-2.git      f3283f727488ad98fe575ea6a5ac981e4a188e49
mkdir -p data-sources
clone data-sources/arc-agi-1    https://github.com/fchollet/ARC-AGI.git        399030444e0ab0cc8b4e199870fb20b863846f34
clone data-sources/conceptarc   https://github.com/victorvikram/ConceptARC.git 0e67da6af879e4bad3d7cd3c196e8d551b445725
clone data-sources/mini-arc     https://github.com/KSB21ST/MINI-ARC.git        792d082c40d496f2f106f63fa7125bb115c8230b
if [ "${1:-}" = --kaggle ]; then
  mkdir -p data-kaggle && kaggle competitions download arc-prize-2026-arc-agi-2 -p data-kaggle -q
  (cd data-kaggle && for z in *.zip; do [ -f "$z" ] && unzip -q -o "$z" && rm "$z"; done)
  kaggle datasets download sorokin/nvarc-synthetic-puzzles -p data-sources/nvarc-synthetic-puzzles --unzip -q
fi
