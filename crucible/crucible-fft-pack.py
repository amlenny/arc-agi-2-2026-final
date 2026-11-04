#!/usr/bin/env python3
"""crucible-fft-pack.py --corpus <dir|manifest> --out <dir> [--holdout-root <root>] [--pack-tokens 8192]

CPU-side preparation for crucible-fft-train.py, run BEFORE renting so paid GPU time only trains.

  1. load     sdg.load_corpus (same holdout pruning and fatal skips as the LoRA trainer)
  2. screen   content-level pair hashing vs the evaluation split -- same rule as the LoRA trainer
  3. encode   crucible-grids15.encode_ttt_example: loss on output grids only, exactly as trained
  4. pack     blocks into fixed-length rows of --pack-tokens, in corpus order, with a best-fit
              lookahead window so rows fill without reordering the corpus beyond that window
  5. write    tokens.u8 (vocab is 16 -> one byte/token), mask.u8 (1 = loss on this token),
              rows.json (per row: the [start, length] of each block inside it), index.json

A row is a sequence of whole blocks. Attention never crosses a block boundary: the trainer resets
position ids at every block start, and FlashAttention's varlen kernel treats each run as its own
sequence. The unused tail of a row is filled with pad tokens as one more masked run, so every row
has the SAME length -- static shapes for torch.compile, no per-step recompiles.

The holdout is encoded too (unpacked; the trainer evaluates it per block, per task, the same
definition as the LoRA trainer), into holdout.u8 / holdout.json.
"""
import argparse, json, os, sys, importlib.util, hashlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def _sib(stem):
    spec = importlib.util.spec_from_file_location(stem.replace("-", "_"), os.path.join(HERE, stem + ".py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


sdg = _sib("crucible-sdg-train")
fmt = _sib("crucible-grids15")

ap = argparse.ArgumentParser()
ap.add_argument("--corpus", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--tokenizer", default=os.environ.get("CRUCIBLE_BASE_MODEL", ""),
                help="base model dir (sorokin/qwen3_4b_grids15_sft139); default $CRUCIBLE_BASE_MODEL")
ap.add_argument("--data", default="data-kaggle")
ap.add_argument("--expect-tasks", type=int, default=0)
ap.add_argument("--pack-tokens", type=int, default=16384,
                help="row length. Several examples per row; each EXAMPLE is capped at --max-example")
ap.add_argument("--max-example", type=int, default=8192,
                help="per-example cap = the model's test-time context. Trailing pairs are dropped "
                     "until it fits (never below 2); a block that still does not fit is excluded "
                     "and counted -- launch requires truncated_blocks == 0")
ap.add_argument("--with-test-pair", default="on", choices=["on", "off"],
                help="include each block's test pair (it carries its answer): 4 supervised outputs "
                     "per 3+1 block instead of 3 (FFT spec, strategy 2)")
ap.add_argument("--augment", type=int, default=-1,
                help="seed for per-block augmentation (one random dihedral, one permutation of all 10 "
                     "colours incl. 0, demo-order shuffle); the first block of each task stays "
                     "unaugmented. -1 = off. FFT spec strategy 1.")
ap.add_argument("--views", type=int, default=1,
                help="multi-view epochs: pack the corpus N times in a row, each pass a NEW view of every "
                     "block, so one block's views sit a whole pass apart. N>1 or --view-offset switches to view mode: "
                     "view index vi = view-offset*N + pass; vi 0 = the block as staged (NVARC leaves sample 0 "
                     "unaugmented), vi>0 = dihedral x colour permutation x demo-order shuffle from (augment, block, vi); "
                     "colour 0 (background) stays fixed; colour_values_matter blocks get dihedral + demo order only")
ap.add_argument("--perm-zero", default="off", choices=["on", "off"], help="view mode: permute colour 0 as well (test-time views do); off = 0 fixed")
ap.add_argument("--view-offset", type=int, default=0, help="epoch index: epoch e uses views e*N .. e*N+N-1, never reused")
ap.add_argument("--lookahead", type=int, default=64,
                help="best-fit window: how far past the head of the queue a block may be pulled "
                     "forward to fill a row. Bounds how much the corpus order is perturbed.")
ap.add_argument("--task-key", default="second", choices=["second", "middle"],
                help="which part of a block name is its task for 'first block stays unaugmented': second = hop 1 names "
                     "(<n>_<task>_...); middle = everything between the order prefix and the block number (breadth rule names)")
ap.add_argument("--holdout-root", default="")
ap.add_argument("--holdout-max-per-task", type=int, default=4)
a = ap.parse_args()

from transformers import AutoTokenizer
tok = fmt.load_tokenizer()   # the embedded base tokenizer; see crucible-grids15.py
fmt.assert_tokenizer(tok)
if len(tok) > 256:
    sys.exit(f"FAIL: vocab {len(tok)} does not fit uint8 storage")
PAD = tok.pad_token_id

ev = sdg.scorer.load_tasks(a.data, "evaluation")
# CANONICAL contamination screen: canon() relabels colours by first appearance and takes the smallest
# of the 8 dihedral images, so a pair that only differs from an evaluation pair by a rotation or a
# colour permutation -- exactly what --augment produces -- still collides.
_cv = importlib.util.spec_from_file_location("corpus_verify", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "corpus", "corpus-verify.py"))
cv = importlib.util.module_from_spec(_cv); _cv.loader.exec_module(cv)
eval_pairs = set()
for tid, t in ev.items():
    for p in t.get("train", []) + [x for x in t.get("test", []) if x.get("output")]:
        eval_pairs.add(cv.canon(p["input"], p["output"]))
import random, zlib

skipped, pruned = [], []
tasks = sdg.load_corpus(a.corpus, skipped, pruned)
if skipped:
    sys.exit(f"FAIL: {len(skipped)} unreadable; first {skipped[0]}")
if a.expect_tasks and len(tasks) != a.expect_tasks:
    sys.exit(f"FAIL: --expect-tasks {a.expect_tasks} but {len(tasks)} loaded")

blocks, rejected, too_long, names, pairs_packed, cut_pairs = [], [], 0, [], 0, 0
views = []   # per packed block: the augmentation applied (dihedral, colour map) or None = as staged
seen_task = set()
VIEW_MODE = a.views > 1 or a.view_offset > 0
if VIEW_MODE and a.augment < 0: sys.exit("FAIL: --views/--view-offset need --augment <seed>")
def add_block(tid, t, vi):
    global cut_pairs, too_long, pairs_packed
    pairs = [p for p in t.get("train", [])] + ([x for x in t.get("test", []) if x.get("output")]
                                                if a.with_test_pair == "on" else [])
    if any(cv.canon(p["input"], p["output"]) in eval_pairs for p in pairs):
        rejected.append(tid); return
    demos = [{"input": p["input"], "output": p["output"]} for p in pairs]
    if len(demos) < 2:
        return
    _parts = os.path.basename(str(tid)).split("_")
    task_key = (("_".join(_parts[1:-1]) if a.task_key == "middle" else _parts[1]) if len(_parts) >= 3 else
                (_parts[1] if len(_parts) == 2 else str(tid)))
    view = None
    if VIEW_MODE:
        if vi > 0:
            rng = random.Random((a.augment * 1000003) ^ zlib.crc32(f"{tid}|{vi}".encode()))
            if a.perm_zero == "on":
                # colour 0 permuted too, as make_views does at test time and as the base was trained (NVARC).
                perm = list(range(10)); rng.shuffle(perm); view = (rng.randrange(8), tuple(perm))
            else:
                perm = list(range(1, 10)); rng.shuffle(perm)
                view = (rng.randrange(8), tuple([0] + perm))
            if t.get("_colour_values_matter"):
                view = (view[0], tuple(range(10)))
            demos = [{"input": fmt.apply_view(d["input"], view), "output": fmt.apply_view(d["output"], view)}
                     for d in demos]
            rng.shuffle(demos)
    elif a.augment >= 0 and task_key in seen_task:
        rng = random.Random((a.augment * 1000003) ^ zlib.crc32(str(tid).encode()))
        view = (rng.randrange(8), tuple(rng.sample(range(10), 10)))
        if t.get("_colour_values_matter"):      # rule reads colour values: dihedral only (hop 2 spec)
            view = (view[0], tuple(range(10)))
        demos = [{"input": fmt.apply_view(d["input"], view), "output": fmt.apply_view(d["output"], view)}
                 for d in demos]
        rng.shuffle(demos)
    seen_task.add(task_key)
    ids, labels = fmt.encode_ttt_example(tok, demos)
    while len(ids) > a.max_example and len(demos) > 2:
        demos = demos[:-1]; cut_pairs += 1
        ids, labels = fmt.encode_ttt_example(tok, demos)
    if len(ids) > a.max_example:
        too_long += 1; return
    blocks.append((np.array(ids, np.uint8), np.array([l != -100 for l in labels], np.uint8)))
    names.append(f"{tid}#v{vi}" if VIEW_MODE else tid); views.append(view); pairs_packed += len(demos)

for p_ in range(a.views if VIEW_MODE else 1):
    for tid, t in tasks:
        add_block(tid, t, a.view_offset * a.views + p_)
if VIEW_MODE: rejected = sorted(set(rejected))

# ---- pack: order-preserving best fit within a lookahead window ----
L = a.pack_tokens
queue = list(range(len(blocks)))
rows, qi = [], 0
pending = []
while qi < len(queue) or pending:
    while len(pending) < a.lookahead and qi < len(queue):
        pending.append(queue[qi]); qi += 1
    row, used = [], 0
    while True:
        room = L - used
        fit = [k for k in pending if len(blocks[k][0]) <= room]
        if not fit:
            break
        # head of the queue first if it fits (keeps order); otherwise the largest that fits
        k = pending[0] if pending[0] in fit else max(fit, key=lambda j: len(blocks[j][0]))
        pending.remove(k); row.append(k); used += len(blocks[k][0])
        while len(pending) < a.lookahead and qi < len(queue):
            pending.append(queue[qi]); qi += 1
    rows.append(row)

os.makedirs(a.out, exist_ok=True)
tokens = np.full(len(rows) * L, PAD, np.uint8)
mask = np.zeros(len(rows) * L, np.uint8)
row_meta, real = [], 0
for r, row in enumerate(rows):
    at, spans = r * L, []
    for k in row:
        ids, m = blocks[k]
        tokens[at:at + len(ids)] = ids; mask[at:at + len(ids)] = m
        spans.append([at - r * L, len(ids)]); at += len(ids); real += len(ids)
    row_meta.append(spans)
tokens.tofile(os.path.join(a.out, "tokens.u8"))
mask.tofile(os.path.join(a.out, "mask.u8"))
json.dump(row_meta, open(os.path.join(a.out, "rows.json"), "w"))

hold = {}
if a.holdout_root:
    ho = sdg.load_holdout(a.holdout_root, a.holdout_max_per_task)
    buf_t, buf_m, meta, at = [], [], [], 0
    for tid in sorted(ho):
        for demos in ho[tid]:
            if any(sdg.pair_hash(p["input"], p["output"]) in eval_pairs for p in demos):
                continue
            ids, labels = fmt.encode_ttt_example(tok, demos)
            ids, labels = ids[:L], labels[:L]
            buf_t.append(np.array(ids, np.uint8)); buf_m.append(np.array([l != -100 for l in labels], np.uint8))
            meta.append([tid, at, len(ids)]); at += len(ids)
    np.concatenate(buf_t).tofile(os.path.join(a.out, "holdout.u8"))
    np.concatenate(buf_m).tofile(os.path.join(a.out, "holdout_mask.u8"))
    json.dump(meta, open(os.path.join(a.out, "holdout.json"), "w"))
    hold = {"blocks": len(meta), "tasks": len({m[0] for m in meta}), "tokens": at}

sha = hashlib.sha256(tokens.tobytes() + mask.tobytes()).hexdigest()
# LAUNCH CHECKS (FFT spec): every pair opens with exactly one "user" token (id 11), so the count of
# token 11 in the pack must equal the pairs packed -- a dropped or doubled role token shows here.
n_user = int((tokens == 11).sum())
if n_user != pairs_packed:
    sys.exit(f"FAIL: token-11 count {n_user} != pairs packed {pairs_packed}")
if too_long:
    print(f"  NOTE: {too_long} blocks did not fit {a.max_example} tokens even at 2 pairs -- EXCLUDED")
idx = {"corpus": os.path.abspath(a.corpus), "tokenizer": a.tokenizer, "pad": PAD,
       "pack_tokens": L, "lookahead": a.lookahead, "blocks": len(blocks), "rows": len(rows),
       "real_tokens": real, "fill": real / (len(rows) * L), "loss_tokens": int(mask.sum()),
       "rejected_vs_eval": len(rejected), "rejected_vs_eval_canonical": len(rejected), "truncated_blocks": 0, "excluded_too_long": too_long,
       "pairs_packed": pairs_packed, "pairs_cut_to_fit": cut_pairs, "user_tokens": n_user,
       "with_test_pair": a.with_test_pair, "augment_seed": a.augment, "perm_zero": a.perm_zero, "views": a.views, "view_offset": a.view_offset, "max_example": a.max_example,
       "holdout": hold, "sha256_tokens_mask": sha}
# Run manifest input: which staged blocks (by corpus file id) each packed row holds, in order, with the augmentation
# applied. The trainer reads rows in order, grad_accum x ranks rows per optimizer step, so step s = rows [s*k, (s+1)*k).
json.dump({"rows": [[[os.path.basename(str(names[k])), list(views[k][:1]) + [list(views[k][1])] if views[k] else None]
                     for k in row] for row in rows]}, open(os.path.join(a.out, "rows-blocks.json"), "w"))
idx["rows_blocks"] = "rows-blocks.json"
json.dump(idx, open(os.path.join(a.out, "index.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in idx.items() if k != "corpus"}, indent=1))
