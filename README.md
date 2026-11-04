# crucible: ARC Prize 2026 (ARC-AGI-2) entry code

Code for a Kaggle entry in ARC Prize 2026: a Qwen3-4B grid model with a 16-token vocabulary, fine-tuned in nine sequential hops, averaged into a two-model soup and run on Kaggle with per-task test-time training, augmentation voting, a difficulty-sorted time scheduler and a margin-gated second pass.

The repo holds training code, kernel and inference code, data-building code and a description of the computational environment. It holds no competition data, datasets or model weights; "Data and third-party code" says where they come from.

## Layout

| Path | What it does |
|---|---|
| `corpus/breadth/` | Synthetic breadth tasks. `rules/` holds 88 batch files of hand-written rules; `harness.py` gates them; `build-breadth.py` builds a tree; `compose-build.py` makes two-step compositions; the `build-*.sh`, `finalise-*.sh`, `fix-*.sh` and `rename-*.sh` scripts built and repaired each tree. |
| `corpus/generators/` | 120 generators, one per ARC-AGI-2 public evaluation task. `nv-stage.py` uses their `transform()` to verify pairs. |
| `corpus/neighborhoods.py`, `corpus/midband.py` | Skeletons for the S120 pool (97 and 23 source tasks). |
| `corpus/build-neighborhoods.py`, `corpus/crucible-build-midband.py`, `corpus/crucible_pool.py` | Emit S120 blocks from those skeletons, with their gates. |
| `corpus/build-s120-pool.sh`, `corpus/s120-build-plan.json` | One ordered S120 build, with its task lists and counts. |
| `corpus/ours-fresh-package.py`, `corpus/screen-ours-fresh.py`, `corpus/crucible-screen-corpus.py`, `corpus/corpus-verify.py`, `corpus/corpus-replay.py` | Screens: legality, duplicates, and collisions with benchmark pairs. The midband builder loads its canonical form from `corpus-replay.py`. |
| `corpus/real-pool-stage.py`, `corpus/real-loo-stage.py` | Re-split blocks from the real ARC tasks. |
| `corpus/nv-stage.py` | Mixes the sources into one hop's corpus. |
| `corpus/build-union-trees.sh`, `corpus/breadth/build-compose.sh` | The three union trees and the compose tree, from the recorded commands. |
| `corpus/lineage-index.py`, `corpus/lineage-query.py`, `corpus/lineage_canon.py`, `corpus/lineage-map.json` | Rebuild the index of pool files a model has never seen. |
| `corpus/evals/`, `corpus/synthetic-breadth/_MANIFEST-breadth.json`, `corpus/midband-split.json` | Small inputs the stagers read: held-out task ids, rule-loss rankings, rule lists, the never-seen index and the breadth rule manifest. These list ids, file names and metrics, not grids. |
| `crucible/crucible-grids15.py`, `crucible/crucible-score.py`, `crucible/crucible-parity.py` | Grid serialization, scoring and the kernel's inference code. These three are the copies embedded in the FR-004 kernel, byte for byte. |
| `crucible/crucible-fft-pack.py`, `crucible/crucible-sdg-train.py` | Pack a corpus into fixed-length token rows. The packer loads the corpus reader from `crucible-sdg-train.py`. |
| `crucible/crucible-fft-train.py`, `crucible/fft-single.yaml` | Full fine-tune trainer and its accelerate config. |
| `crucible/crucible-kaggle-build.py`, `crucible/crucible-profile.py`, `crucible/kaggle-setup-block.txt`, `tools/crucible-kernel-patch-parity.py` | Build a single-file Kaggle kernel and embed sources and flags in it. |
| `kernel/FR-004/`, `kernel/FFT-095/`, `kernel/FFT-099/` | The submitted kernels with their Kaggle metadata. See "Kernels". |
| `configs/hops.json` | Settings of each hop, from the run records. |
| `tools/train-hop.py` | Prints or runs the trainer command of one hop from `configs/hops.json`. |
| `tools/crucible-pick-120-blocks.py`, `tools/crucible-hop2c-stage.py` | Stage the first hop's corpus (hop3). |
| `tools/crucible-fft-to-merged.py`, `tools/crucible-average-merged.py`, `tools/build-soup.sh` | Checkpoint to merged model, and the soup. |

## Computational environment

- **Data building, packing, soup, kernel self-test:** CPU, Python 3.12 with the versions in `requirements.txt`. Each merged model is about 7.3 GB on disk. A recorded compose build ran under a system Python 3.14. `ours-fresh-20261003/` is 1.8 GB on disk.
- **Training:** one Colab NVIDIA A100 80 GB per hop, single process (`fft-single.yaml`, bf16 compute, fp32 master weights). Each step is 32 rows of 16,384 tokens. **The library versions on the Colab runtimes were not recorded.** The runs used the image's preinstalled packages.
- **Kernel:** Kaggle, 4 x NVIDIA L4, internet off, Docker image digest in each `kernel-metadata.json`. Unsloth and flash-attn install from the public kernel `sorokin/pip-install-unsloth-flash-patch`, attached as a kernel source.

## Order of steps

Paths below are relative to the repo root. Steps 1 to 6 need no GPU.

1. **Data.** `./fetch-data.sh` clones ARC-AGI-2, ARC-AGI-1, ConceptARC and MINI-ARC into `crucible/` at the commits used. `./fetch-data.sh --kaggle` also downloads the competition JSON and NVARC's synthetic puzzles, and needs Kaggle credentials and accepted competition rules.
2. **Base model.** Download `sorokin/qwen3_4b_grids15_sft139` from Kaggle Models. Set `CRUCIBLE_BASE_MODEL` to its directory. The packer takes its tokenizer from there.
3. **Breadth trees**, from `corpus/breadth/`:
   - `python3 build-breadth.py --batch rules/<file>.py --blocks 20 --out ../synthetic-breadth` for the batches `b000` to `b065`. The recorded tree has 2,571 rules and 51,370 blocks.
   - `./build-compose.sh`, for `synthetic-breadth-compose` (recorded: 4,542 compositions).
   - `./build-wave2.sh 3 3`, for `synthetic-breadth-wave2` (766 rules).
   - `./build-hiloss.sh`, for `synthetic-breadth-hiloss` (391 rules).
   - `./build-compose-hiloss.sh 4000 6` (recorded: 999 compositions), and `./build-compose-wave2.sh` (recorded: 1,593 compositions). The `finalise-*`, `fix-*` and `rename-*` scripts are the repairs those builds needed. `finalise-*` takes the PIDs of a running build.
   - `corpus/build-union-trees.sh`.
4. **S120 pools.** `corpus/build-s120-pool.sh`.
5. **Real pool.** `python3 corpus/real-pool-stage.py corpus/real-pool-corpus`.
6. **Stage and pack each hop.** Run the hop's `stage_command` and `pack_command` from `configs/hops.json`, from the repo root. The hop3 commands need `$CRUCIBLE_BASE_MODEL` and NVARC's data (`$NVARC_SYNTHETIC`).
7. **Train each hop**, in the order of the table below. `python3 tools/train-hop.py HOP --model-dir DIR --packed DIR --save-dir DIR --ckpt-dir DIR [--continue-from CKPT] [--run]`. Rows with "carried" optimizer state take `--continue-from` with the parent's final checkpoint. Rows with "fresh" start from the parent's merged model.
8. **Convert.** `python3 tools/crucible-fft-to-merged.py <checkpoint>/model.safetensors <reference merged dir> <out dir> <step>` on each final checkpoint. The reference directory supplies config and tokenizer and must have the base model's tensor names.
9. **Soup.** `tools/build-soup.sh <FFT-095 dir> <FFT-099 dir> <out dir>` gives a 0.5 / 0.5 fp32 average, stored as bf16.
10. **Kernel.** Attach the soup as a Kaggle model and run `kernel/FR-004/crucible-parity-kernel.py` on the hardware above. Its `MODEL` path must match the model's mount point. `cd crucible && python3 crucible-parity.py --self-test --second-pass on --difficulty-order on --task-seconds-max 3600 --out /tmp/self-test.json` exercises dispatch, scheduling and scoring without a model or GPU.

## Per-hop settings

Source: `configs/hops.json`, which also holds the stage and pack commands, measured data shares and recorded code versions. All hops: `--optim adamw --master-dtype fp32 --grad-ckpt on --grad-accum 32 --epochs 1 --max-grad-norm 0.5 --w-copied 0.7 --w-changed 1.0 --async-ckpt on --probe-every 42`, 3% warmup (trainer default), 524,288 tokens per step.

| Hop | Model | Parent | Optimizer state | lr | Weight decay | Min lr ratio | Checkpoint every | Steps | Rows | Corpus seed | Pack seed | Data mix (breadth tree, S120, real) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hop3 | FFT-002 | base | none | 1.5e-5 | 0.2 | 0.0 | 84 | 504 of 843 (kept checkpoint) | 26983 | hop3 tag | 107 | synthetic-breadth 0.30, S120 picks 0.40, ARC-AGI-2 training 0.25, NVARC 0.05 |
| vol12a | FFT-054 | hop3 | fresh | 3e-5 | 0.2 | 0.1 | 84 | 161 | 5166 | 1015 | 1006 | compose 0.450, S120 0.3, real 0.25 |
| vol16a | FFT-080 | vol12a | fresh | 3e-5 | 0.2 | 0.1 | 999 | 160 | 5145 | 1028 | 1019 | union13 0.200, S120 0.55, real 0.25 |
| vol17a | FFT-084 | vol16a | carried | 1.5e-5 | 0.01 | 0.1 | 999 | 161 | 5163 | 1030 | 1021 | union13 0.450, S120 0.3, real 0.25 |
| vol18a | FFT-087 | vol17a | carried | 3e-5 | 0.01 | 0.1 | 999 | 161 | 5180 | 1040 | 1021 | union-hiloss 0.450, S120 0.3, real 0.25 |
| vol19a | FFT-089 | vol18a | carried | 1.5e-5 | 0.01 | 0.1 | 999 | 161 | 5162 | 1050 | 1021 | union13 0.450, S120 0.3, real 0.25 |
| vol20a | FFT-092 | vol19a | fresh | 3e-5 | 0.01 | 0.1 | 999 | 161 | 5163 | 1060 | 1021 | union16 0.334, S120 0.333, real 0.333 |
| vol21a | FFT-095 | vol20a | fresh | 1.5e-5 | 0.01 | 0.1 | 999 | 161 | 5161 | 1070 | 1021 | union13 0.450, S120 0.3, real 0.25 |
| vol24c | FFT-099 | vol21a | fresh | 7.5e-6 | 0.01 | 0.1 | 999 | 161 | 5169 | 2412 | 2412 | union13 0.450, S120 0.3, real 0.25 |

FFT-095 and FFT-099 are the soup's two members. The submitted model, FR-004, is their uniform average.

## Kernels

- **FR-004** (submission 57920413) is the exact record of the submitted inference code. `kernel/FR-004/crucible-parity-kernel.py` is byte-identical to the file submitted, SHA-256 `4e736fdb1aa008eb23a8372685d9f246c70c51f47001202d31115167088125cd`. Its embedded sources have short hashes `46dda8d2` (parity), `00f0664f` (grids15), `c6d6efcc` (score), and `crucible/` holds the same three files. Some comments in it carry dates and internal run labels.
- **FFT-095** (submission 57751242) and **FFT-099** (submission 57817240) are the single-model entries. Their `crucible-parity.py` differs from FR-004's: 66 changed lines between FFT-095 and FFT-099 (extra-candidates flags) and 247 between FFT-099 and FR-004 (scheduler and second pass). Both differ from FR-004 in the model path and flags: FR-004 adds `--difficulty-order on --task-seconds-max 3600 --all-ttt-perms 32 --all-min-share 2500 --hard-ttt-perms 64 --hard-frac 0.25 --hard-min-share 3500 --ttt-frac 0.6 --plan-reserve-s 600 --all-ttt-perms 0 --hard-ttt-perms 0 --second-pass on`. Argparse takes the last value of a repeated flag.
- The FFT-095 and FFT-099 copies differ from what was submitted in comment text only, where people's names were removed. Code tokens were compared and are identical. The as-submitted SHA-256 values are FFT-095 `9821cd38bf409b8275b9427ea6f7484bdfc17fd903bb97e7d30bebd4b6d39b82` and FFT-099 `f1ed08343ac21c482b85f1c7a0c3923d14f3a6e9f2b944dad7e97a40f097c692`, so the published files no longer match those values.
- In the metadata files, `<owner>` replaces the Kaggle account name. Replace it to push a kernel.

## What is not scripted end to end, or not reproducible

- **Colab runs.** The hops ran through private wrappers that uploaded datasets and checkpoints and generated notebooks. They are not here. `tools/train-hop.py` issues the same trainer flags; it has not been used for a training run.
- **FFT-002 (hop3).** It is checkpoint s000504 of the second run, at lr 1.5e-5, resumed from s000336 and later from s000420 after runtime losses. The manifest of the first run (lr 3e-5) was the one on record. `configs/hops.json` carries the second run's values and its history. No command was located for the last resume, from s000420 to s000504. Trainer version `37ccfc5` ran hop3 and `008bcd0` ran the later hops; the file here is `008bcd0`. The packer was recorded as `829f053` for hop3 and as `829f053` with uncommitted changes for the later hops; the file here is the source repo's later commit `0bf7f2b`.
- **Compose tree.** Both recorded `compose-build.py` runs (20,000 candidates seed 1, 8,000 candidates seed 2) were stopped by hand, and the manifest was written from the disk. The stopping point was not recorded as a candidate count, and `compose-build.py` was edited after those runs. vol12a was staged while the tree was partial (about 2,500 compositions), so a complete tree gives vol12a different samples.
- **`build-compose-wave2.sh`.** It defaults to 5,000 candidates; the recorded run was stopped by PID and finalised from the disk. `build-compose-hiloss.sh 4000 6` stalled at about 3,800 candidates and was finalised the same way.
- **S120 pools.** The pools were built in several passes between September and October while skeletons were being corrected, with rebuilds and top-ups of single tasks. `corpus/build-s120-pool.sh` runs the final skeletons once at the final counts and the recorded salts and seeds. It has not been run end to end, and its output is not expected to match the original files byte for byte. The dedup step in `ours-fresh-package.py` compares against whatever trees exist on the machine, which were more numerous in the original build. `_build-fftu-*` and `mech` trees existed in the original build but `nv-stage.py` does not read them, so the script omits them.
- **Never-seen index.** `corpus/evals/lineage/never-seen-FFT-002.json.gz` names the original pool files. `nv-stage.py` raises an error on a listed S120 file that does not exist, so on rebuilt pools regenerate the index with `corpus/lineage-index.py` and `corpus/lineage-query.py FFT-002`. That needs a staged `hop3-corpus`. The map in `corpus/lineage-map.json` is cut down to this lineage.
- **Breadth manifest.** `crucible-hop2c-stage.py` checks `corpus/synthetic-breadth/_MANIFEST-breadth.json` against a fixed SHA-256. Rebuilding that tree overwrites the file with one that may fail this check.
- **Probe sets.** `hop2-probes.json` is not here because it contains ARC grids. It is only for monitoring during training, and the trainer runs without it. `nv-stage.py` tries to copy it from `hop6-corpus/` and prints an error if it is absent. `crucible-hop2c-stage.py` stops at its end if `corpus/hop2-corpus/hop2-probes.json` is absent. `corpus/evals/hop1-probes-20261007.json` lists the task ids of P1 to P3; P4 is 128 blocks of the held-out breadth rules (`sorted(rules)[19::20]`). No script here assembles the file.
- **Publishing weights.** The upload of the FR-004 weights as a Kaggle model has no script on record. The kernels read `/kaggle/input/...` mount paths, which are fixed by Kaggle.
- **Trained models.** Hops are not deterministic across library versions. Nothing here claims that a rerun gives the same weights.

## Data and third-party code

Nothing below is in this repo.

- Competition data: Kaggle competition `arc-prize-2026-arc-agi-2`.
- Base model: `sorokin/qwen3_4b_grids15_sft139` on Kaggle Models, from the NVARC 2025 release. Published under the ARC Prize 2025 open-source terms (MIT-0 or CC BY 4.0).
- Kernel dependency: public Kaggle kernel `sorokin/pip-install-unsloth-flash-patch`. Published under the ARC Prize 2025 open-source terms (MIT-0 or CC BY 4.0).
- Datasets: ARC-AGI-2 (https://github.com/arcprize/ARC-AGI-2), ARC-AGI-1 (https://github.com/fchollet/ARC-AGI), ConceptARC (https://github.com/victorvikram/ConceptARC), MINI-ARC (https://github.com/KSB21ST/MINI-ARC), and `sorokin/nvarc-synthetic-puzzles` on Kaggle (hop3, 5% of tokens). RE-ARC was not used.
- NVARC's 2025 release is cited as the source of the base model and its 16-token format. No NVARC code is included.

**Public evaluation tasks.** `corpus/generators/` and the S120 pools were written from the 120 ARC-AGI-2 public evaluation tasks. Scores on that split for these models are not held-out numbers; only the Kaggle leaderboard's hidden test set is.

## License

Offered under MIT-0 (`LICENSE-MIT-0`) or CC BY 4.0 (`LICENSE-CC-BY-4.0`), at the recipient's choice. Copyright 2026 Andrew Leonard.
