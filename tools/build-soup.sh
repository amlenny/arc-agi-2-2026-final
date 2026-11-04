#!/usr/bin/env bash
# build-soup.sh <fft095-dir> <fft099-dir> <out-dir> -- the submitted model: a uniform fp32 average of two merged full
# fine-tunes (FFT-095 and FFT-099), written as bf16 safetensors.
set -euo pipefail
python3 "$(dirname "$0")/crucible-average-merged.py" --out "${3:?out dir}" --model "${1:?FFT-095 dir}:0.5" --model "${2:?FFT-099 dir}:0.5"
