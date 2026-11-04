#!/usr/bin/env python
# crucible-parity.py — the parity baseline: the posted pack recipe, run on the adopted S2 base.
#
# This is the checkpoint every later measurement is a delta against, so it reproduces the posted
# recipe rather than improving on it. Anywhere it departs, the departure is named in a comment
# beside the code and is switchable from the command line, so the cost of the departure can be
# measured instead of argued about.
#
# THE RECIPE, per task:
#   1. Restore the adapter to its initial state. The model is loaded once per worker and reused;
#      only the LoRA weights are reset. Reloading 8 GB per task would dominate the run.
#   2. Test-time training. LoRA r=256 alpha=32 with rslora over q/k/v/o/gate/up/down plus
#      embed_tokens and lm_head, bf16, one epoch over the task's own demonstrations replayed
#      under 8 dihedral symmetries x N colour permutations, loss on the output grids only.
#   3. Decode. Depth-first search over the answer, batched across augmented views of the task,
#      keeping only branches whose CUMULATIVE probability stays above a floor.
#   4. Score. Every distinct candidate is re-scored as a forced continuation under a fixed set of
#      8 augmentations of the same task.
#   5. Select. Candidates are ranked by how many views produced them, minus their mean augmented
#      negative log-likelihood. The top two become the two attempts.
#
# WHY IT LOOKS NOTHING LIKE crucible-solve.py: that harness samples N completions and submits the
# two most frequent. This one enumerates rather than samples, and ranks by a second forward pass
# rather than by frequency. The two are different measurements and their numbers are not
# interchangeable.
#
# Doctrine inherited from the rest of the campaign: bf16, local paths only, cannot fetch, fail
# loud. Nothing is installed at run time.
import argparse
import collections
import math
import hashlib
import importlib.util
import json
import os
import random
import select
import subprocess
import sys
import tempfile
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))


def _sibling(stem):
    """Import a sibling script by path; the dash in the filenames makes them un-importable by
    name."""
    path = os.path.join(HERE, f"{stem}.py")
    if not os.path.isfile(path):
        raise SystemExit(f"FAIL: {path} not found — crucible-parity.py needs it beside itself.")
    spec = importlib.util.spec_from_file_location(stem.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# The default is the adopted base's amputated-vocabulary format. --format swaps in the
# general-vocabulary one; both expose the same interface, so nothing else in this harness changes.
fmt = _sibling("crucible-grids15")
scorer = _sibling("crucible-score")


def _fusedce():
    """Loaded ON DEMAND, not at import. The sliced loss is only used when --fused-ce asks for it,
    and the competition kernel ships a fixed set of files — a module-level import would make an
    optional dependency mandatory at a venue that does not carry it."""
    global _FUSEDCE
    if _FUSEDCE is None:
        _FUSEDCE = _sibling("crucible-fusedce")
    return _FUSEDCE


_FUSEDCE = None


def select_format(name):
    """Bind the format module for this run. grids15 unless requested otherwise."""
    global fmt
    if name != "grids15":
        fmt = _sibling("crucible-general4b")
    return fmt

# The nine module types the posted recipe adapts. embed_tokens and lm_head are in the list and
# are cheap here for a reason that does not generalise: this base has a sixteen-token vocabulary,
# so both matrices are 16 x 2560.
LORA_TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj",
                "embed_tokens", "lm_head"]

DEAD_BEAM_SCORE = 1e4      # a score no branch can reach, used to park exhausted rows in a batch
EXTRA = {}                 # --extra-candidates: task id -> test index -> distinct outside grids

# How far the base-weight fingerprint may move across a merge/unmerge round trip before the base
# is called corrupt. Measured over 120 real cycles the drift is flat at one bf16 quantum, worst
# observed 3.81e-05; 1e-3 is well above that and well below anything a fused adapter would cause.
MERGE_DRIFT_TOL = 1e-3


def merge_probe(model):
    """One adapted base weight, used to spot-check that unmerging restored it.

    Picked by structure rather than by name: peft wraps an adapted module so that the original
    lives at .base_layer, so the first module carrying one is an adapted module whatever the
    architecture calls its projections.
    """
    for _, mod in model.named_modules():
        base = getattr(mod, "base_layer", None)
        if base is not None and getattr(base, "weight", None) is not None:
            return base.weight
    return None


def is_oom(e):
    """Out-of-memory arrives under more than one type and not always as OutOfMemoryError —
    autograd re-raises it as a plain RuntimeError. Matched on the message as well as the type,
    the way crucible-layout.py already does it."""
    import torch
    return isinstance(e, getattr(torch, "OutOfMemoryError", ())) or (
        isinstance(e, RuntimeError) and "out of memory" in str(e).lower())


# ------------------------------------------------------------------ worker protocol
# Machine-readable lines go to stdout with an @ prefix; everything human, plus whatever torch and
# transformers write, goes to stderr and passes straight through to the console. Same shape as
# crucible-layout.py, so the two harnesses fail in the same recognisable way.

def emit(kind, payload):
    sys.stdout.write("@" + kind + " " + json.dumps(payload) + "\n")
    sys.stdout.flush()


def say(msg, flush=True):
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


# ------------------------------------------------------------------ decoding

DEV_SEARCH = None   # (K, TAU) when --dev-search is set; None = the cumulative floor, unchanged
# --floor-mode (spec §4): None = cumulative (today). Else (mode, value, B, K): per-token prunes a token whose
# own p < value; length-norm prunes when the branch's mean NLL per generated token > value. Both bounded:
# at most the top B tokens per position and at most K non-top choices per answer (K < 0 = no cap).
FLOOR = None
FAST_LM = None      # unsloth.FastLanguageModel when --backend unsloth (CRUCIBLE-UNSLOTH-PORT-SPEC.md)


def shape_legal(st, t):
    """--demo-shape: next state if token t is legal under the forced (H, W), else None. st = (H, W, row, col).
    The answer format is digits per row, NEWLINE between rows (none trailing), then IM_END."""
    H, W, r, c = st
    if t == fmt.NEWLINE_ID:
        return (H, W, r + 1, 0) if c == W and r < H - 1 else None
    if t == fmt.IM_END_ID:
        return st if c == W and r == H - 1 else None
    return (H, W, r, c + 1) if c < W else None


def dfs_expand(model, logits, budget, max_score, scores, pos, cache, deadline, dfs_deadline,
               crop, stats, devs=None, shp=None, depth=0):
    """Depth-first search over answers, batched across views, sharing one KV cache.

    The batch rows are DIFFERENT augmented views of the same task, not different branches: each
    row walks its own tree and they advance in lockstep so every step is one batched forward.

    THE FLOOR IS CUMULATIVE, NOT PER-TOKEN. `scores` carries the running negative log-likelihood
    of the branch and a continuation survives only while that total stays under `max_score`.
    With max_score = -log(0.2) the search returns only answers whose whole-sequence probability
    is at least 0.2, which is why it terminates at all: a handful of candidates per view, not a
    beam that has to be truncated. Reading the floor as a per-token threshold overstates the
    candidate count by orders of magnitude and mis-costs every surface built on top of it.

    Only the twelve tokens a grid can contain are ever expanded. The other four are unreachable
    in a well-formed answer, and expanding them would spend the budget proving that.
    """
    import torch

    n = logits.size(0)
    # log_softmax on CPU in fp32: the scores are compared against a threshold and summed across
    # hundreds of positions, and bf16 has ~3 decimal digits.
    nll = (torch.tensor(scores, dtype=torch.float32).view(n, 1)
           - logits.float().cpu().log_softmax(-1))

    suffixes = collections.defaultdict(list)
    candidates = {}
    if devs is None:
        devs = [0] * n
    if shp is None:
        shp = [None] * n
    for i in range(n):
        row = []
        # --demo-shape: only tokens legal under this row's forced (H, W); None = no forcing (today)
        legal = {t: (shape_legal(shp[i], t) if shp[i] is not None else None) for t in fmt.ARC_TOKENS}
        toks = [t for t in fmt.ARC_TOKENS if shp[i] is None or legal[t] is not None]
        if FLOOR is not None:
            mode, val, B, K = FLOOR
            allowed = []
            if devs[i] < 10 ** 6:                 # not a parked row
                order = sorted(toks, key=lambda t: nll[i, t].item())[:B]
                for j, t in enumerate(order):
                    d = devs[i] + (1 if j else 0)
                    if K >= 0 and d > K:
                        continue
                    tok_nll = nll[i, t].item() - scores[i]
                    if mode == "per-token" and math.exp(-tok_nll) < val:
                        continue
                    if mode == "length-norm" and nll[i, t].item() / (depth + 1) > val:
                        continue
                    allowed.append((t, d))
        elif DEV_SEARCH is None:
            allowed = [(t, devs[i]) for t in toks if nll[i, t].item() < max_score]
        else:
            # K-DEVIATION SEARCH. Measured 2026-09-28 (crucible-kdev-reach.py, FT-016, the 39): with
            # gold teacher-forced, the model's top token is gold everywhere but 2-3 positions, and at
            # those gold is 2nd choice 75-91% of the time -- but the product of those p(gold) is
            # ~0.001-0.009, so the cumulative floor cuts it. Here the TOP token is always followed,
            # and the 2nd may be taken where the top is below TAU, at most K times per answer,
            # whatever the running total. Bounded by K, so it terminates without the floor.
            K, TAU = DEV_SEARCH
            if devs[i] > K:
                allowed = []                      # a parked (exhausted) row
            else:
                order = sorted(toks, key=lambda t: nll[i, t].item())
                allowed = []
                if order:
                    p_top = math.exp(-(nll[i, order[0]].item() - scores[i]))
                    allowed = [(order[0], devs[i])]
                    if p_top < TAU and devs[i] < K and len(order) > 1:
                        allowed.append((order[1], devs[i] + 1))
        for t, d in allowed:
            s = nll[i, t].item()
            if t == fmt.IM_END_ID:
                # A complete answer. Recorded with its total score and not expanded further.
                suffixes[i].append((s, [t]))
            elif budget > 1:
                row.append((s, t, d, legal[t]))
        candidates[i] = sorted(row, key=lambda x: x[:3])

    while True:
        now = time.time()
        if now > dfs_deadline or now > deadline:
            stats["timeouts"] += 1
            break

        batch_tokens, batch_scores, batch_devs, batch_shp, alive = [], [], [], [], 0
        for i in range(n):
            if candidates[i]:
                s, t, d, st = candidates[i].pop(0)
                batch_tokens.append(t)
                batch_scores.append(s)
                batch_devs.append(d)
                batch_shp.append(st)
                alive += 1
            else:
                # An exhausted row still has to occupy its slot: the rows share a KV cache and
                # dropping one would shift every later row's history. Parked with a score no
                # continuation can beat, so it contributes nothing.
                batch_tokens.append(fmt.PAD_ID)
                batch_scores.append(DEAD_BEAM_SCORE)
                batch_devs.append(10 ** 6)
                batch_shp.append(None)
        if alive == 0:
            break

        if crop:
            # The cache is one object that every level of the recursion mutates, so it grows as
            # the search descends and does not shrink on the way back up. Measured directly:
            # after a 5-token prefill and three descents the cache holds 8 entries, and the next
            # sibling forward at position 5 attends over all 8 — three of them keys from the
            # branch just abandoned. The reference implementation does not crop.
            #
            # This is a correctness fix, NOT a recipe change, which is why --kv-crop can turn it
            # off. What the contamination is worth on a trained model is unmeasured; on a random
            # one it moves nothing, which says only that the probe was uninformative.
            #
            # Cropped by a NEGATIVE delta rather than to an absolute length: both spellings mean
            # "remove this many" across the transformers versions in play, whereas the absolute
            # form is deprecated from 5.18. The guard matters — a zero delta would be read as the
            # absolute form and empty the cache.
            if hasattr(cache, "get_seq_length"):
                # Unsloth's cache is a list of views of one buffer: a sibling reuses the parent's
                # shorter view and Unsloth writes at buffer[seq_len], overwriting the abandoned
                # branch -- the crop, done by Unsloth (spec section 5). Only an HF cache is cropped.
                excess = cache.get_seq_length() - pos
                if excess > 0:
                    cache.crop(-excess)

        out = model(
            input_ids=torch.tensor(batch_tokens, device=model.device, dtype=torch.long).view(-1, 1),
            position_ids=torch.full((n, 1), pos, device=model.device, dtype=torch.long),
            past_key_values=cache,
            use_cache=True,
            return_dict=True,
        )
        stats["forwards"] += 1

        deeper = dfs_expand(model, out.logits[:, -1], budget - 1, max_score, batch_scores,
                            pos + 1, out.past_key_values, deadline, dfs_deadline, crop, stats,
                            batch_devs, batch_shp, depth + 1)
        for row, beams in deeper.items():
            for s, tokens in beams:
                suffixes[row].append((s, [batch_tokens[row]] + tokens))

    return suffixes


def decode_views(model, prompts, budget, max_score, deadline, dfs_seconds, crop, shapes=None):
    """Prefill a batch of augmented prompts, then search each one's answer tree.

    Prompts in a batch are padded on the LEFT so every row's last position is the token the
    answer continues from — the search advances all rows at one shared position index, which a
    right-padded batch would break.
    """
    import torch

    stats = {"forwards": 0, "timeouts": 0}
    # Every row must already be the same length, because the caller batches by orientation. If
    # that ever stops holding, padding would silently corrupt the shared position index and let
    # rows attend over their own pads — the defect this batching exists to remove. Fail instead.
    widths = {len(p) for p in prompts}
    if len(widths) != 1:
        raise SystemExit(f"FAIL: decode batch has mixed prompt lengths {sorted(widths)}. Views "
                         f"must be batched by grid orientation so no padding is needed; a ragged "
                         f"batch means the grouping was bypassed.")
    width = widths.pop()
    input_ids = torch.tensor(prompts, device=model.device, dtype=torch.long)

    out = model(input_ids=input_ids, use_cache=True, return_dict=True)
    stats["forwards"] += 1
    shp = [((sh[0], sh[1], 0, 0) if sh else None) for sh in shapes] if shapes else None
    suffixes = dfs_expand(model, out.logits[:, -1], budget, max_score,
                          [0.0] * len(prompts), width, out.past_key_values,
                          deadline, time.time() + dfs_seconds, crop, stats, None, shp)
    return {row: sorted(beams) for row, beams in suffixes.items()}, stats


def decode_views_grouped(model, prompts, budget, max_score, deadline, dfs_seconds, crop, shapes=None):
    """decode_views over prompts of possibly DIFFERENT lengths: one call per length, rows remapped.

    Shuffled demo order (reference behaviour, 2026-09-29) happens before fit_demos drops the oldest
    demos, so on a task too long for all its demos two views of one orientation can keep different
    demos and differ in length. decode_views refuses a ragged batch (and must: padding would corrupt
    the shared position index), and its SystemExit would kill the worker. Grouping keeps every call
    unpadded and makes the case non-fatal."""
    groups = collections.defaultdict(list)
    for i, p in enumerate(prompts):
        groups[len(p)].append(i)
    found, stats = {}, {"forwards": 0, "timeouts": 0}
    for _, rows in sorted(groups.items()):
        f, st = decode_views(model, [prompts[i] for i in rows], budget, max_score, deadline,
                             dfs_seconds, crop, [shapes[i] for i in rows] if shapes else None)
        for local, beams in f.items():
            found[rows[local]] = beams
        stats["forwards"] += st["forwards"]; stats["timeouts"] += st["timeouts"]
    return found, stats


def score_candidates(model, tokenizer, examples, batch_size, fused_chunk=0):
    """Negative log-likelihood of each answer as a forced continuation of its prompt.

    Scored in one forward per batch rather than by generation: the answer is already known, so
    only the probability the model assigns to it is wanted.
    """
    import torch

    results = []
    for start in range(0, len(examples), batch_size):
        chunk = examples[start:start + batch_size]
        prompt_ids = [tokenizer.encode(p) for p, _ in chunk]
        answer_ids = [tokenizer.encode(a) for _, a in chunk]
        rows = [p + a for p, a in zip(prompt_ids, answer_ids)]
        width = max(len(r) for r in rows)
        # RIGHT padding here, unlike the decode path: the spans being scored are located by their
        # offset from the start of the row, and left padding would move them.
        padded = [r + [fmt.PAD_ID] * (width - len(r)) for r in rows]
        attention = [[1] * len(r) + [0] * (width - len(r)) for r in rows]
        input_ids = torch.tensor(padded, device=model.device, dtype=torch.long)
        mask = torch.tensor(attention, device=model.device, dtype=torch.long)
        if fused_chunk:
            # Only the answer positions are ever read, so only they are projected. Without this
            # the scoring pass builds full-sequence logits plus an fp32 copy — measured at 7.45 GB
            # for one batch of two at a 248k vocabulary, which does not fit beside the weights.
            results.extend(_fusedce().fused_answer_nll(
                model, input_ids, mask,
                [(len(p), len(a)) for p, a in zip(prompt_ids, answer_ids)], chunk=fused_chunk))
        else:
            out = model(input_ids=input_ids, attention_mask=None if FAST_LM is not None else mask,
                        use_cache=False, return_dict=True)
            logprobs = out.logits.float().cpu().log_softmax(-1)
            for row, p_ids, a_ids in zip(logprobs, prompt_ids, answer_ids):
                # Position i predicts token i+1, so the answer's first token is predicted from the
                # last prompt position.
                span = row[len(p_ids) - 1:len(p_ids) - 1 + len(a_ids)]
                total = span[torch.arange(len(a_ids)), torch.tensor(a_ids)].sum()
                results.append(-total.item())
    return results


# ------------------------------------------------------------------ test-time training

class LooExample(list):
    """--ttt-objective loo (spec §1): context demos then the QUERY demo last; the loss falls on the query's output
    only. A list, so code that measures an example (format_demos) is unchanged."""
    loo = True


def build_loo_examples(tokenizer, pairs, n_perms, max_seq_len, seed, skipped):
    """Spec §1: one example per view; view i's query is demo (i mod n) after the view's shuffle, so every demo is
    the query an equal number of times. Context demos are dropped LARGEST first to fit; never the query. A view
    whose query alone does not fit, or that has no context left, is skipped and counted in skipped[0]."""
    rng = random.Random(seed)
    examples = []
    for i, view in enumerate(fmt.make_views(rng, n_perms)):
        demos, _ = fmt.view_task(pairs, pairs[0]["input"], view)
        rng.shuffle(demos)
        if len(demos) < 2:
            skipped[0] += 1; continue
        q = i % len(demos)
        query, context = demos[q], demos[:q] + demos[q + 1:]
        size = lambda ds: len(encode_ttt_example(tokenizer, ds)[0])
        while context and size(context + [query]) > max_seq_len:
            context.remove(max(context, key=lambda d: size([d])))
        if not context:
            skipped[0] += 1; continue
        examples.append(LooExample(context + [query]))
    rng.shuffle(examples)
    return examples


def build_ttt_examples(tokenizer, pairs, n_perms, max_seq_len, seed):
    """One training example per augmented view: the task's own demonstrations, as chat turns.

    The test input is absent — its answer is what is being predicted, and nothing about it is
    known. What the model trains on is the demonstrations predicting each other, which is the
    same shape as the question it will be requested.
    """
    rng = random.Random(seed)
    examples = []
    for view in fmt.make_views(rng, n_perms):
        demos, _ = fmt.view_task(pairs, pairs[0]["input"], view)
        rng.shuffle(demos)
        demos = fmt.fit_demos(demos, None, None, max_seq_len,
                              lambda t: len(tokenizer.encode(t)))
        if not demos:
            # The reference keeps a one-demo example (loss on that output); only an empty one goes.
            continue
        examples.append(demos)
    rng.shuffle(examples)
    return examples


def encode_ttt_example(tokenizer, demos):
    """Delegate to the format module. The harness must not know how a turn is spelled — that is
    exactly the knowledge that differs between an amputated vocabulary and a model with its own
    chat template."""
    return fmt.encode_ttt_example(tokenizer, demos)


def shuffled_demos(demos, key):
    """Demo order shuffled deterministically per (task, input, view): the reference shuffles demo
    order in EVERY decode and scoring view (arc_loader.augment -> shuffle_ex). Keyed without the
    candidate, so every candidate is scored under the same order."""
    out = list(demos)
    random.Random(zlib.crc32(key.encode()) & 0xFFFFFFFF).shuffle(out)
    return out


TTT_WEIGHTS = None   # (w_copied, w_changed) when --ttt-loss-weights is set; None = plain mean


def ttt_token_classes(tokenizer, demos):
    """Per token of encode_ttt_example(demos): 0 prompt, 1 copied cell, 2 changed cell, 3 answer token of a
    RESIZED output (cells, row and end markers), 4 row/end marker of a same-size output. 3 and 4 both weigh 1.0
    on the weighted path; --ttt-focal-resized acts on 3 only (spec §1: M2 where "changed cell" is undefined)."""
    cls = []
    for pair in demos:
        prompt = (f"{fmt.IM_START}user\n{fmt.grid_to_text(pair['input'])}{fmt.IM_END}"
                  f"{fmt.IM_START}assistant\n")
        p_ids = tokenizer.encode(prompt); a_ids = tokenizer.encode(fmt.reply_text(pair["output"]))
        gi, go = pair["input"], pair["output"]
        same = len(gi) == len(go) and len(gi[0]) == len(go[0])
        c = []
        for r, row in enumerate(go):
            c += [(1 if gi[r][k] == v else 2) if same else 3 for k, v in enumerate(row)]
            if r < len(go) - 1:
                c.append(4 if same else 3)
        c += [4 if same else 3] * (len(a_ids) - len(c))
        cls += [0] * len(p_ids) + c
    return cls


def encode_example(tokenizer, ex):
    """ids, labels and (for the weighted path) token classes of one TTT example. A LooExample keeps the loss on
    its last demo's output only (encode_ttt_example concatenates pair by pair, so the split is exact)."""
    if getattr(ex, "loo", False):
        c_ids, _ = encode_ttt_example(tokenizer, ex[:-1])
        q_ids, q_lab = encode_ttt_example(tokenizer, ex[-1:])
        cls = lambda: [0] * len(c_ids) + ttt_token_classes(tokenizer, ex[-1:])
        return c_ids + q_ids, [-100] * len(c_ids) + q_lab, cls
    ids, labels = encode_ttt_example(tokenizer, ex)
    return ids, labels, lambda: ttt_token_classes(tokenizer, ex)


FOCAL_RESIZED = 0.0   # --ttt-focal-resized G (spec §1): weight class-3 tokens by (1 - p_gold)^G; 0 = off


def train_one_task(model, tokenizer, examples, lr, warmup_ratio, max_grad_norm, deadline,
                   progress=None, fused_chunk=0, selfcheck=None, early_stop=True):
    """One epoch of the posted recipe's optimizer settings.

    THE TRAINER IS WRITTEN OUT RATHER THAN CALLED. The posted recipe drives this through a
    Trainer subclass from unsloth, which is not available at our venue and is not needed: at
    batch 1, gradient accumulation 1 and one epoch, a Trainer is an AdamW loop with a cosine
    schedule and gradient clipping. Written explicitly, the recipe's hyperparameters are visible
    where they take effect and nothing is contributed by a dependency that cannot be installed
    offline. This is an implementation difference, not a recipe difference.
    """
    import math
    import torch

    trainable = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(trainable, lr=lr, weight_decay=0.0)
    total = max(1, len(examples))
    warmup = int(warmup_ratio * total)

    def factor(step):
        if step < warmup:
            return (step + 1) / max(1, warmup)
        progress = (step - warmup) / max(1, total - warmup)
        return 0.5 * (1.0 + math.cos(math.pi * min(1.0, progress)))

    sched = torch.optim.lr_scheduler.LambdaLR(opt, factor)

    model.train()
    losses, steps, max_seq = [], 0, 0
    t_train = time.time()
    reads, best, worse, stop_step = [], None, 0, None
    for demos in examples:
        if time.time() > deadline:
            break
        # --ttt-holdout-demo (spec §2): every 16 steps read the held-out demo; stop after two reads in a row fail
        # to beat the best, never before step 32. The adapter is not restored (an r256 snapshot per read is too big).
        if selfcheck is not None and steps and steps % 16 == 0:
            r = selfcheck(); r["step"] = steps; reads.append(r)
            if best is None or r["loss"] < best:
                best, worse = r["loss"], 0
            else:
                worse += 1
            if early_stop and steps >= 32 and worse >= 2:
                stop_step = steps
                break
        ids, labels, _cls = encode_example(tokenizer, demos)
        if not any(x != -100 for x in labels):
            continue
        if progress is not None:
            progress.update(step=steps, seq=len(ids))
        batch = torch.tensor([ids], device=model.device, dtype=torch.long)
        target = torch.tensor([labels], device=model.device, dtype=torch.long)
        if TTT_WEIGHTS is not None or FOCAL_RESIZED:
            # CHANGED-CELL WEIGHTED TTT. The plain mean is ~80-90% copy cells, so the few cells the
            # rule changes -- where the near-misses are wrong -- carry little of each step.
            cls = _cls()
            if len(cls) != len(ids):
                raise SystemExit("FAIL: TTT class map does not match encode_ttt_example")
            c = torch.tensor(cls[1:], device=model.device)
            wc, wch = TTT_WEIGHTS if TTT_WEIGHTS is not None else (1.0, 1.0)
            w = torch.zeros(len(cls) - 1, device=model.device)
            w[c == 1] = wc; w[c == 2] = wch; w[c == 3] = 1.0; w[c == 4] = 1.0
            w[torch.tensor(labels[1:], device=model.device) == -100] = 0.0   # a LooExample's context
            logits = model(input_ids=batch, use_cache=False).logits[0, :-1].float()
            nll = torch.nn.functional.cross_entropy(logits, batch[0, 1:], reduction="none")
            if FOCAL_RESIZED:
                # M2 on resized outputs, where "changed cell" is undefined: the model's own doubt sets the weight.
                p_gold = torch.exp(-nll.detach())
                w = torch.where(c == 3, w * (1 - p_gold) ** FOCAL_RESIZED, w)
            loss = (nll * w).sum() / w.sum().clamp_min(1e-8)
        elif fused_chunk:
            # The loss logits are the largest tensor in a training step at a big vocabulary —
            # 1.49 MB per token at 248k — and they are avoidable. Same quantity, accumulated in
            # slices. Only used where it has been proven equivalent on the actual model.
            loss = _fusedce().fused_ce_loss(model, batch, target, chunk=fused_chunk)
        else:
            loss = model(input_ids=batch, labels=target, use_cache=False).loss
        loss.backward()
        torch.nn.utils.clip_grad_norm_(trainable, max_grad_norm)
        opt.step()
        sched.step()
        opt.zero_grad(set_to_none=True)
        losses.append(loss.item())
        max_seq = max(max_seq, len(ids))
        steps += 1
    model.eval()
    out_sc = {}
    if selfcheck is not None:
        final = selfcheck(); final["step"] = steps; reads.append(final)
        out_sc = {"selfcheck_reads": reads, "selfcheck_exact_final": final["exact_both"],
                  "selfcheck_stop_step": stop_step}
    return {**out_sc, "steps": steps, "planned": len(examples),
            "step_s": round((time.time() - t_train) / steps, 3) if steps else None,
            "max_seq": max_seq,
            "loss_first": round(losses[0], 4) if losses else None,
            "loss_last": round(losses[-1], 4) if losses else None}


# ------------------------------------------------------------------ worker

def repair_merge_after_failure(model, a):
    """E2 — undo a merge that an exception skipped, and PROVE the base came back.

    The merge is a global mutation of the base weights. `solve_task` merges near the top and
    unmerges at the bottom, so any exception in between — an OOM is the expected one, and the
    worker treats an OOM as a legitimate result rather than a crash — unwinds past the unmerge and
    leaves the adapter fused in. Resetting the adapter afterwards restores the ADAPTER, not the
    base, so every later task silently runs on weights the failed task modified.

    Returns None when there was nothing to repair, else a dict recording the fingerprint check.
    Raises SystemExit(3) if the base does not come back: a model we cannot vouch for makes every
    subsequent number in the run meaningless, and stopping is cheaper than discovering it later.
    """
    if not getattr(a, "_merged", False):
        return None
    try:
        model.unmerge_adapter()
        a._merged = False
    except Exception as ue:
        say(f"  [worker {getattr(a, 'worker_id', '?')}] FATAL: could not unmerge after failure: "
            f"{type(ue).__name__}: {ue}")
        raise SystemExit(3)

    probe = merge_probe(model)
    if probe is None or not getattr(a, "_probe_norm", None):
        return {"unmerged": True, "verified": False,
                "note": "no fingerprint available; unmerge not verified"}
    now = float(probe.detach().float().norm().item())
    drift = abs(now - a._probe_norm) / max(a._probe_norm, 1e-9)
    rec = {"unmerged": True, "verified": True, "baseline": a._probe_norm,
           "after_unmerge": round(now, 6), "rel_drift": round(drift, 9),
           "clean": drift < MERGE_DRIFT_TOL}
    if not rec["clean"]:
        say(f"  [worker {getattr(a, 'worker_id', '?')}] FATAL: base weights did not restore "
            f"after unmerge (rel drift {drift:.3e} > {MERGE_DRIFT_TOL:.0e}). Refusing to "
            f"continue — later tasks would run on a corrupted base.")
        raise SystemExit(3)
    say(f"  [worker {getattr(a, 'worker_id', '?')}] adapter unmerged after failure; "
        f"base verified (rel drift {drift:.3e})")
    return rec


def demo_shape(demos, test_in):
    """--demo-shape (spec §4): the output (H, W) the demos fix, or None. Rule 1: every demo keeps its size
    -> the test input's size. Rule 2: every demo output has one size -> that size. Computed on the VIEW's
    demos and test input, so a transposed view gets the transposed shape. Measured on the public 172
    (2026-10-10): applies on 125 inputs, gold's shape on 120 (5 misfires, which forcing makes unreachable)."""
    sz = lambda g: (len(g), len(g[0]) if g else 0)
    if demos and all(sz(d["input"]) == sz(d["output"]) for d in demos):
        return sz(test_in)
    outs = {sz(d["output"]) for d in demos}
    return outs.pop() if len(outs) == 1 else None


def solve_task(model, tokenizer, task, a, deadline, progress):
    """Test-time training, decoding, scoring and selection for one task.

    progress is updated in place as the task moves through its phases, so a run that dies can
    still say WHERE it died. An out-of-memory failure whose report is just a byte count does not
    answer the question the fit probe exists to ask.
    """
    import torch
    from peft import get_peft_model_state_dict, set_peft_model_state_dict

    t0 = time.time()
    task_deadline = min(deadline, t0 + a.task_seconds)

    # PAIRED A/B. The second arm must decode from the SAME adapter as the first, not from a
    # re-trained one: TTT is stochastic, so re-running it would put a fresh adapter between the
    # two arms and the difference would no longer be the thing under test. Arm A trains and
    # snapshots; arm B restores that snapshot and skips training entirely. Everything downstream
    # — the score views, drawn from the task id, and the eval views, drawn from the fixed
    # eval_seed — is already identical across arms, so the crop is the only varying factor.
    reuse = getattr(a, "_ab_adapter", None)
    set_peft_model_state_dict(
        model, {k: v.clone() for k, v in (reuse if reuse is not None else a._initial).items()},
        adapter_name="default")
    if FAST_LM is not None:
        # MUST run every task: the only thing that deletes the cached inference LoRA (_fast_lora);
        # skipped, the next task decodes on the previous task's adapter (spec section 4).
        FAST_LM.for_training(model, use_gradient_checkpointing=False)

    pairs = task["train"]
    # PRE-TTT DECODE (--pre-ttt-decode on). The adapter is at its initial state here (TTT has not
    # run), so this is the untrained model. Its raw beams are stored per (test input, batch) and fed
    # through the SAME canonicalise/score/pool path after TTT, as a third decode pass.
    pre_store = {}
    if a.pre_ttt_decode == "on":
        _max_new = fmt.max_answer_tokens(); _budget = a.max_seq_len - _max_new
        _tseed = zlib.crc32(task["_id"].encode()) & 0xFFFFFFFF
        if a.merge_for_decode:
            model.merge_adapter()
        if FAST_LM is not None:
            FAST_LM.for_inference(model)
        try:
            for _ti, _test in enumerate(task["test"]):
                _vr = random.Random(_tseed + 1 + _ti if a.eval_seed < 0 else a.eval_seed)
                _views = fmt.make_views(_vr, a.eval_perms)
                for _start, _chunk in enumerate(fmt.batch_views(_views, a.decode_batch)):
                    if time.time() > task_deadline:
                        break
                    _prompts, _kept = [], []
                    for _v in _chunk:
                        _d, _tin = fmt.view_task(pairs, _test["input"], _v)
                        _d = shuffled_demos(_d, f"{task['_id']}|{_ti}|dec|{_v}")
                        _d = fmt.fit_demos(_d, _tin, None, _budget, lambda t: len(tokenizer.encode(t)))
                        if _d:
                            _prompts.append(tokenizer.encode(fmt.build_input(_d, _tin))); _kept.append(_v)
                    if _prompts:
                        with torch.inference_mode():
                            _found, _st = decode_views_grouped(model, _prompts, _max_new, a.max_score,
                                                       task_deadline, a.dfs_seconds, a.kv_crop)
                        pre_store[(_ti, _start)] = (_found, _kept)
        finally:
            if a.merge_for_decode:
                model.unmerge_adapter()
            if FAST_LM is not None:
                FAST_LM.for_training(model, use_gradient_checkpointing=False)
        say(f"  [worker {a.worker_id}] {task['_id']} pre-TTT decode: {len(pre_store)} batches, "
            f"{sum(len(b) for f, _ in pre_store.values() for b in f.values())} beams", flush=True)
    ttt = {"skipped": "ttt disabled"}
    if reuse is not None:
        ttt = {"reused": "adapter carried from the paired arm; TTT deliberately not repeated"}
    elif a.ttt_perms > 0:
        # --ttt-holdout-demo auto (spec §2): on 4+-demo tasks one demo (median output size, ties to the lowest
        # index) is out of ALL TTT examples, as query and as context; it stays in decode and scoring prompts.
        train_pairs, held = pairs, None
        if a.ttt_holdout_demo == "auto" and len(pairs) >= 4:
            sizes = [len(p["output"]) * len(p["output"][0]) for p in pairs]
            order = sorted(range(len(pairs)), key=lambda k: (sizes[k], k))
            hk = order[(len(order) - 1) // 2]
            held = pairs[hk]; train_pairs = pairs[:hk] + pairs[hk + 1:]
        loo_skipped = [0]
        if a.ttt_objective == "loo":
            examples = build_loo_examples(tokenizer, train_pairs, a.ttt_perms, a.ttt_seq_len, a.seed, loo_skipped)
        else:
            examples = build_ttt_examples(tokenizer, train_pairs, a.ttt_perms, a.ttt_seq_len, a.seed)
        selfcheck = None
        if held is not None:
            _sv = fmt.make_views(random.Random(zlib.crc32(f"{task['_id']}|selfcheck".encode()) & 0xFFFFFFFF), 1)[1]
            def selfcheck(_held=held, _ctx=train_pairs, _sv=_sv):
                """Teacher-force the held-out demo under the identity view and one fixed seeded view, other
                demos as context: mean answer loss, and exactness per view and for both."""
                out = {}
                was_training = model.training; model.eval()
                with torch.no_grad():
                    for name, view in (("identity", None), ("seeded", _sv)):
                        if view is None:
                            ctx, q = list(_ctx), _held
                        else:
                            vd, _ = fmt.view_task(_ctx + [_held], _held["input"], view)
                            ctx, q = vd[:-1], vd[-1]
                        ids, labels, _cls = encode_example(tokenizer, LooExample(ctx + [q]))
                        x = torch.tensor([ids], device=model.device)
                        y = torch.tensor(labels[1:], device=model.device)
                        lg = model(input_ids=x, use_cache=False).logits[0, :-1].float()
                        m = y != -100
                        # Loss weighted as TTT trains it (--ttt-loss-weights: copied vs changed cells), so the read is on
                        # the same scale as the training loss and background cells do not earn equal credit.
                        # Exactness stays on every answer token: an answer only counts when every cell is right.
                        nll = torch.nn.functional.cross_entropy(lg, torch.where(m, y, torch.zeros_like(y)), reduction="none")
                        if TTT_WEIGHTS is not None:
                            c = torch.tensor(_cls()[1:], device=model.device)
                            w = torch.ones_like(nll); w[c == 1] = TTT_WEIGHTS[0]; w[c == 2] = TTT_WEIGHTS[1]
                        else:
                            w = torch.ones_like(nll)
                        w = w * m
                        out[name + "_loss"] = float((nll * w).sum() / w.sum().clamp_min(1e-8))
                        out[name + "_exact"] = bool((lg[m].argmax(-1) == y[m]).all())
                if was_training: model.train()
                out["loss"] = (out["identity_loss"] + out["seeded_loss"]) / 2
                out["exact_both"] = out["identity_exact"] and out["seeded_exact"]
                return out
        longest = max((len(tokenizer.encode(fmt.format_demos(e))) for e in examples), default=0)
        progress.update(phase="ttt", examples=len(examples), longest_example=longest)
        # Unsloth trains without checkpointing (the reference's setting), and memory then grows
        # with the example: on L4 it ran out at 5,238 tokens. Long tasks get Unsloth's own
        # checkpointing (numerically exact; it recomputes instead of storing); every other task
        # keeps the full speed. The reset at the top of the next task turns it off again.
        gc_on = FAST_LM is not None and a.unsloth_gc_above and longest > a.unsloth_gc_above
        if gc_on:
            FAST_LM.for_training(model, use_gradient_checkpointing=True)
        say(f"  [worker {a.worker_id}] {task['_id']} TTT: {len(examples)} examples, "
            f"longest {longest} tok" + (", gradient checkpointing ON" if gc_on else ""), flush=True)
        if a.inject_oom_task and task["_id"] == a.inject_oom_task:
            raise torch.cuda.OutOfMemoryError("CUDA out of memory. (injected by --inject-oom-task)")
        # --ttt-frac: TTT may use at most this share of the time left to the task deadline, so a task given
        # more perms (--hard-ttt-perms / --all-ttt-perms) still leaves time to decode. 0 = TTT may run to the deadline.
        ttt_deadline = task_deadline
        if a.ttt_frac > 0:
            ttt_deadline = min(task_deadline, time.time() + a.ttt_frac * max(0.0, task_deadline - time.time()))
        ttt = train_one_task(model, tokenizer, examples, a.lr, a.warmup_ratio,
                             a.max_grad_norm, ttt_deadline, progress, a.fused_ce, selfcheck,
                             early_stop=(a.ttt_adaptive == "off"))
        if a.ttt_adaptive == "on" and held is not None and time.time() < task_deadline:
            # --ttt-adaptive: phase 1 above trained without the held-out demo and read it (no early
            # stop). Phase 2 puts it BACK -- the final adapter has trained on every demo -- and how much more it
            # trains depends on that read: still wrong -> --ttt-adaptive-extra steps, already exact -> --ttt-adaptive-min.
            # Phase 2 continues the same adapter with its own warmup + cosine over its steps.
            n2 = a.ttt_adaptive_min if ttt.get("selfcheck_exact_final") else a.ttt_adaptive_extra
            pool = build_ttt_examples(tokenizer, pairs, a.ttt_perms, a.ttt_seq_len, a.seed + 1)
            ex2 = [pool[k % len(pool)] for k in range(n2)] if pool else []
            p2 = train_one_task(model, tokenizer, ex2, a.lr, a.warmup_ratio, a.max_grad_norm, task_deadline,
                                progress, a.fused_ce, None) if ex2 else {"steps": 0, "planned": 0}
            ttt["phase2"] = {"planned": n2, "steps": p2.get("steps"), "loss_last": p2.get("loss_last"),
                             "reason": "held demo exact" if ttt.get("selfcheck_exact_final") else "held demo NOT exact"}
        ttt.update({"objective": a.ttt_objective, "loo_skipped": loo_skipped[0],
                    "holdout_demo": (pairs.index(held) if held is not None else None)})
        ttt["gradient_checkpointing"] = bool(gc_on) if FAST_LM is not None else a.gradient_checkpointing
    train_s = time.time() - t0
    if getattr(a, "_ab_capture", False) and reuse is None:
        a._ab_adapter = {k: v.clone().detach()
                         for k, v in get_peft_model_state_dict(model).items()}

    # The scoring views are drawn ONCE per task and reused for every candidate, so candidates are
    # compared under identical conditions. Seeded from the task id rather than from the process,
    # so a re-run of one task reproduces its own numbers.
    task_seed = zlib.crc32(task["_id"].encode()) & 0xFFFFFFFF
    score_views = fmt.make_views(random.Random(task_seed), 1)

    # THE ADAPTER IS MERGED FOR DECODE. Left unmerged, every single-token forward pays an extra
    # pair of matmuls per adapted module — several hundred of them — and single-token decode is
    # bound by kernel launches, not arithmetic. Measured on the real architecture: unmerged 1.62x
    # the no-adapter floor, merged 1.02x. THIS IS A DEPARTURE FROM THE REFERENCE (corrected
    # 2026-09-29): unsloth 2026.7.3's for_inference() does NOT merge -- the reference decodes
    # unmerged. Merged bf16 gives slightly different logits and the merge/unmerge round trip drifts
    # the base a little per task (FT-016-c worst 3.07e-05). Kept for speed: unmerged decode at 1.6x
    # does not fit a 240-task submission in 11.9 h. Its score cost is unmeasured.
    # E2 — THE MERGE IS A GLOBAL MUTATION OF THE BASE WEIGHTS, so who is responsible for undoing
    # it must not depend on the code path taken. It used to: the unmerge sits at the bottom of
    # this function, and an OOM raised anywhere between here and there unwinds straight past it.
    # The worker catches that OOM, records it as a legitimate result, and moves to the next task —
    # with the adapter still fused in. Resetting `a._initial` restores the ADAPTER, not the base,
    # so every task after such an OOM runs on a quietly corrupted model and nothing in the payload
    # would say so. The flag below hands the worker's exception path enough state to repair it.
    if FAST_LM is not None:
        FAST_LM.for_inference(model)   # unmerged decode at Unsloth speed; does not merge
    merged = False
    a._merged = False
    if a.merge_for_decode and a.ttt_perms > 0:
        model.merge_adapter()
        merged = True
        a._merged = True

    max_new = fmt.max_answer_tokens()
    prompt_budget = a.max_seq_len - max_new
    entries, diag = [], []

    def decode_input(ti, test, pairs, task_deadline, pre_store):
        """Decode, score and select ONE test input. Returns (entry, diagnostics, ranked).

        A function rather than a loop body so --chain can run it a second time on an input with a
        different demo set and adapter. Its parameters carry the names the body has always used,
        so the body is unchanged: `pairs` is the demo set, `task_deadline` this input's cutoff."""
        progress.update(phase="decode", test_index=ti)
        say(f"  [worker {a.worker_id}] {task['_id']} decode: test input {ti + 1}"
            f"/{len(task['test'])} after {time.time() - t0:.0f}s "
            f"(train {train_s:.0f}s)", flush=True)
        # The reference fixes this seed at 2 for EVERY task, so every task is decoded under the
        # same colour permutations. Ours derived it from the task id, which is a different draw
        # per task — a decode-side difference, since it changes which candidates exist at all and
        # therefore cannot be settled by replaying stored ones.
        # Scoring views drawn PER TEST INPUT, as the reference seeds them per (task, input).
        # --score-perms N draws 8N views from the same rng; make_views draws sequentially, so the
        # first 8 are exactly the views --score-perms 1 uses and N=1 is today's draw unchanged.
        score_views = fmt.make_views(random.Random((task_seed + 7919 * (ti + 1)) & 0xFFFFFFFF),
                                     a.score_perms)
        _vrng = random.Random(task_seed + 1 + ti if a.eval_seed < 0 else a.eval_seed)
        eval_views = fmt.make_views(_vrng, a.eval_perms)
        # Drawn from the SAME rng, so the top-up permutations are fresh rather than repeats of
        # the base ones. Built unconditionally and decoded only if the pool comes up thin; with
        # --topup-below 0 this list is empty and the second pass is skipped entirely, which is
        # byte-for-byte the old behaviour.
        topup_views = fmt.make_views(_vrng, a.topup_perms) if (a.topup_below or a.unsure_count) else []
        n_topup_used = 0; unsure_fired = False
        pooled = collections.defaultdict(list)
        # which view produced each beam (index into this pass's views; top-up +100, pre-TTT +200), so a
        # 24-view run also answers what 16 views would have found: make_views(rng, 2) == make_views(rng, 3)[:16].
        pooled_vi = collections.defaultdict(list)
        known = {}
        n_beams = n_parsed = n_dropped_late = n_scored = 0
        _score_s = 0.0
        dfs_stats = {"forwards": 0, "timeouts": 0}

        # Batched by ORIENTATION, not by position in the list: a batch shares one KV cache and one
        # position index, which is only sound when every row is the same length.
        pre_keys = set()
        for _pass, _views in ((0, eval_views), (1, topup_views),
                              (2, eval_views if pre_store else [])):
            if _pass == 1:
                # --unsure-count K (2026-10-22, adaptive extra time): ALSO top up when the leading candidate came from K or fewer
                # views (or nothing was found). Additive: the extra views join the same pool, scored under the same views, picked by the
                # same rule; an input whose leader has more than K views is never re-decoded. 0 = the thin-pool trigger only.
                _top1 = max((len(v) for v in pooled.values()), default=0)
                _thin = len(pooled) < a.topup_below
                _unsure = a.unsure_count > 0 and _top1 <= a.unsure_count
                if not _views or not (_thin or _unsure) or time.time() > task_deadline:
                    continue
                n_topup_used = len(_views); unsure_fired = _unsure and not _thin
                say(f"    [worker {a.worker_id}] pool {len(pooled)}, leader {_top1} views "
                    f"after {len(eval_views)} views — topping up with {len(_views)} more"
                    f"{' (unsure)' if unsure_fired else ''}", flush=True)
            for start, chunk in enumerate(fmt.batch_views(_views, a.decode_batch)):
                if time.time() > task_deadline:
                    break
                if _pass == 2:
                    found, kept = pre_store.get((ti, start), ({}, []))
                    st = {"forwards": 0, "timeouts": 0}
                else:
                    found = None
                prompts, kept = ([], []) if found is None else ([None], kept)
                shapes = []
                if found is None:
                    for view in chunk:
                        demos, test_in = fmt.view_task(pairs, test["input"], view)
                        demos = shuffled_demos(demos, f"{task['_id']}|{ti}|dec|{view}")
                        demos = fmt.fit_demos(demos, test_in, None, prompt_budget,
                                              lambda t: len(tokenizer.encode(t)))
                        if not demos:
                            continue
                        prompts.append(tokenizer.encode(fmt.build_input(demos, test_in)))
                        kept.append(view)
                        shapes.append(demo_shape(demos, test_in) if a.demo_shape == "on" else None)
                if not prompts:
                    continue

                _t_batch = time.time()
                if found is None:
                    with torch.inference_mode():
                        found, st = decode_views_grouped(model, prompts, max_new, a.max_score,
                                                 task_deadline, a.dfs_seconds, a.kv_crop,
                                                 shapes if any(shapes) else None)
                say(f"    [worker {a.worker_id}] batch {start + 1} ({len(chunk)} views)"
                    f"/{len(eval_views)} views: {time.time() - _t_batch:.0f}s, "
                    f"{st['forwards']} forwards, {sum(len(v) for v in found.values())} beams",
                    flush=True)
                dfs_stats["forwards"] += st["forwards"]
                dfs_stats["timeouts"] += st["timeouts"]

                for row, beams in found.items():
                    view = kept[row]
                    for beam_score, tokens in beams:
                        n_beams += 1
                        # The trailing end marker is not part of the grid.
                        grid = fmt.text_to_grid(tokenizer.decode(tokens[:-1]))
                        if grid is None or not fmt.valid_grid(grid):
                            continue
                        canonical = fmt.invert_view(grid, view)
                        if not fmt.valid_grid(canonical):
                            continue
                        n_parsed += 1
                        key = json.dumps(canonical)
                        if _pass == 2:
                            pre_keys.add(key)
                        if key not in known:
                            # Rescoring a NEW candidate costs 8 forward passes at full prompt length,
                            # so it answers to the per-task cap too. Without this the cap bounds
                            # decoding only, and a task with many distinct candidates runs past it —
                            # over 120 tasks, the difference between a session that finishes and one
                            # that is cut off.
                            #
                            # A late candidate is DROPPED rather than ranked unscored: an unscored
                            # candidate has no comparable selection score, and inventing one would
                            # corrupt the ranking this measurement exists to establish. The count is
                            # recorded per test input and surfaced in the summary, because this
                            # changes what enters the ranking and a silent version of that would be
                            # indistinguishable from a task that simply found fewer candidates.
                            if time.time() > task_deadline:
                                n_dropped_late += 1
                                continue
                            examples = []
                            for sv in score_views:
                                demos, test_in = fmt.view_task(pairs, test["input"], sv)
                                demos = shuffled_demos(demos, f"{task['_id']}|{ti}|score|{sv}")
                                answer = fmt.apply_view(canonical, sv)
                                demos = fmt.fit_demos(demos, test_in, answer, a.max_seq_len,
                                                      lambda t: len(tokenizer.encode(t)))
                                if not demos:
                                    continue
                                examples.append((fmt.build_input(demos, test_in),
                                                 fmt.reply_text(answer)))
                            _t_score = time.time()
                            with torch.inference_mode():
                                known[key] = (score_candidates(model, tokenizer, examples,
                                                               a.score_batch, a.fused_ce)
                                              if examples else [])
                            n_scored += 1
                            _score_s += time.time() - _t_score
                        pooled[key].append(beam_score)
                        pooled_vi[key].append(100 * _pass + _views.index(view))

        # --extra-candidates. Each outside grid for this input is
        # scored under the same views as our own candidates and joins the pool with --extra-votes votes on top of any views
        # that produced it here. Scored even past the task deadline: at most two per input, 8 forwards each, and dropping
        # them would silently turn the ensemble off on exactly the slow tasks.
        extra_keys = set()
        for grid in EXTRA.get(task["_id"], {}).get(ti, []):
            if not fmt.valid_grid(grid):
                continue
            key = json.dumps(grid); extra_keys.add(key)
            if key not in known:
                examples = []
                for sv in score_views:
                    demos, test_in = fmt.view_task(pairs, test["input"], sv)
                    demos = shuffled_demos(demos, f"{task['_id']}|{ti}|score|{sv}")
                    answer = fmt.apply_view(grid, sv)
                    demos = fmt.fit_demos(demos, test_in, answer, a.max_seq_len,
                                          lambda t: len(tokenizer.encode(t)))
                    if demos:
                        examples.append((fmt.build_input(demos, test_in), fmt.reply_text(answer)))
                _t_score = time.time()
                with torch.inference_mode():
                    known[key] = (score_candidates(model, tokenizer, examples, a.score_batch, a.fused_ce)
                                  if examples else [])
                n_scored += 1
                _score_s += time.time() - _t_score

        # Selection: how many views produced this answer, less how surprised the model is by it
        # under the shared augmentations. Occurrence count dominates and the likelihood breaks
        # ties, which is what makes it a vote rather than a confidence ranking.
        ranked = []
        for key in list(pooled) + [k for k in extra_keys if k not in pooled]:
            beam_scores = pooled.get(key, [])
            aug = known.get(key) or []
            aug_mean = sum(aug) / len(aug) if aug else DEAD_BEAM_SCORE
            votes = len(beam_scores) + (a.extra_votes if key in extra_keys else 0.0)
            ranked.append((votes - a.select_nll_weight * aug_mean, key, len(beam_scores), aug_mean,
                           min(beam_scores) if beam_scores else DEAD_BEAM_SCORE))
        ranked.sort(key=lambda x: -x[0])

        # THE CANDIDATE POOL, kept so selection can be retuned without re-running the GPU work.
        # The reference pickles exactly this per subkey and then selects offline, which is how its
        # benchmark compares two selection algorithms for free; collapsing decode, scoring and
        # selection into one pass made every selection question cost a re-run. Held per candidate:
        # the grid, EVERY beam score that produced it (their score_full_probmul_3 sums over all of
        # them, so keeping only the best would discard what it needs), and the per-view NLL
        # vector rather than its mean.
        pool = None
        if a.persist_candidates:
            pool = [{"grid": json.loads(key), "pre_ttt": key in pre_keys, "extra": key in extra_keys,
                     "beam_scores": [round(b, 6) for b in pooled.get(key, [])], "beam_views": pooled_vi.get(key, []),
                     "aug_nll": [round(x, 6) for x in (known.get(key) or [])]}
                    for key in list(pooled) + [k for k in extra_keys if k not in pooled]]

        picks = [json.loads(x[1]) for x in ranked[:2]]
        while len(picks) < 2:
            # An unused attempt is wasted budget, so a blank is a last resort rather than a
            # choice. It is recorded as such in the diagnostics.
            picks.append(picks[0] if picks else [[0]])
        entry = {"attempt_1": picks[0], "attempt_2": picks[1]}

        say(f"  [worker {a.worker_id}] {task['_id']} input {ti + 1} done: {n_beams} beams, "
            f"{len(pooled)} distinct, {n_scored} scored in {_score_s:.0f}s", flush=True)
        gold = test.get("output")
        return entry, {
            "task": task["_id"], "test_index": ti,
            "views": len(eval_views) + n_topup_used, "base_views": len(eval_views),
            "topup_views": n_topup_used, "unsure_topup": unsure_fired, "beams": n_beams, "parsed": n_parsed,
            "distinct": len(pooled), "empty": not ranked,
            "extra_candidates": len(extra_keys), "extra_in_pool": len(extra_keys & set(pooled)),
            "extra_rank": [i for i, x in enumerate(ranked) if x[1] in extra_keys],
            "dropped_past_cap": n_dropped_late,
            "candidates": pool,
            "scored_candidates": n_scored, "scoring_s": round(_score_s, 1),
            # --second-pass pools candidates across two seeds: grid, vote count, mean and count of augmented NLLs.
            "ranked_top": [[k, c, round(m, 6), len(known.get(k) or [])] for _s, k, c, m, _b in ranked[:8]],
            "dfs_forwards": dfs_stats["forwards"], "dfs_timeouts": dfs_stats["timeouts"],
            "top": [{"count": c, "aug_nll": round(m, 4), "select": round(s, 4),
                     "best_beam": round(b, 4)} for s, _, c, m, b in ranked[:4]],
            "any_of_n": bool(gold and any(json.loads(k) == gold for k in pooled)),
            "pass_at_2": bool(gold and any(p == gold for p in picks)),
        }, ranked

    # --chain needs two inputs: one to seed it and one to re-decode.
    chain_on = a.chain == "on" and len(task["test"]) >= 2
    # THE CHAIN PASS HAS ITS OWN SHARE OF THE TASK BUDGET. Without one, the normal pass may run to
    # the task deadline (the floor test saw input 0 take all of it) and the chain would never run.
    # The share is of the time left after TTT, since TTT time is spent either way. Off: unchanged.
    pass_deadline = task_deadline
    if chain_on:
        _now = time.time()
        pass_deadline = _now + max(0.0, task_deadline - _now) * (1.0 - a.chain_budget_frac)
    ranks = []
    for ti, test in enumerate(task["test"]):
        entry, d, ranked = decode_input(ti, test, pairs, pass_deadline, pre_store)
        entries.append(entry); diag.append(d); ranks.append(ranked)

    chain = None
    if chain_on:
        chain = {"chain_used": False, "seed_input": None, "budget_frac": a.chain_budget_frac,
                 "min_views": a.chain_min_views, "min_margin": a.chain_min_margin,
                 "pass_end_s": round(time.time() - t0, 1)}
        # The seed: an input whose rank-1 candidate came from enough views AND leads its rank-2 by
        # enough selection score. A sole candidate has no rank-2; its margin is unbounded (null in
        # the record). Several qualifying -> the widest margin, then most views, then lowest index.
        qual = []
        for ti, ranked in enumerate(ranks):
            if not ranked:
                continue
            count = ranked[0][2]
            margin = ranked[0][0] - ranked[1][0] if len(ranked) > 1 else float("inf")
            if count >= a.chain_min_views and margin >= a.chain_min_margin:
                qual.append((-margin, -count, ti))
        chain["qualifying_inputs"] = sorted(q[2] for q in qual)
        if not qual:
            chain["reason"] = "no input met min views and min margin"
        elif time.time() > task_deadline:
            chain["reason"] = "task deadline already passed"
        else:
            _, _, si = min(qual)
            seed = ranks[si][0]
            seed_margin = seed[0] - ranks[si][1][0] if len(ranks[si]) > 1 else None
            chain.update({"chain_used": True, "seed_input": si, "seed_views": seed[2],
                          "seed_margin": round(seed_margin, 4) if seed_margin is not None else None,
                          "seed_select": round(seed[0], 4), "seed_aug_nll": round(seed[3], 4),
                          "seed_pass": bool(task["test"][si].get("output") is not None
                                            and json.loads(seed[1]) == task["test"][si]["output"])})
            chain_pairs = list(pairs) + [{"input": task["test"][si]["input"],
                                          "output": json.loads(seed[1])}]
            say(f"  [worker {a.worker_id}] {task['_id']} chain: input {si + 1} seeds it "
                f"({seed[2]} views, margin {seed_margin}); {a.chain_ttt_steps} more TTT steps",
                flush=True)
            # More TTT on the SAME adapter, the seed pair now a demo. Same objective and loss
            # weighting as the main pass (TTT_WEIGHTS is global); its own warmup + cosine over its
            # steps, as --ttt-adaptive phase 2 does. The adapter is unmerged to train and merged
            # again to decode; the restore probe below measures the extra round trip.
            if merged:
                model.unmerge_adapter()
                merged = False; a._merged = False
            if FAST_LM is not None:
                FAST_LM.for_training(model, use_gradient_checkpointing=False)
            progress.update(phase="chain_ttt")
            if a.ttt_perms > 0 and a.chain_ttt_steps > 0:
                if a.ttt_objective == "loo":
                    cpool = build_loo_examples(tokenizer, chain_pairs, a.ttt_perms, a.ttt_seq_len,
                                               a.seed + 2, [0])
                else:
                    cpool = build_ttt_examples(tokenizer, chain_pairs, a.ttt_perms, a.ttt_seq_len,
                                               a.seed + 2)
                cex = [cpool[k % len(cpool)] for k in range(a.chain_ttt_steps)] if cpool else []
                ct = (train_one_task(model, tokenizer, cex, a.lr, a.warmup_ratio, a.max_grad_norm,
                                     task_deadline, progress, a.fused_ce, None)
                      if cex else {"steps": 0, "planned": 0})
                chain["ttt"] = {"planned": a.chain_ttt_steps, "steps": ct.get("steps"),
                                "loss_first": ct.get("loss_first"), "loss_last": ct.get("loss_last"),
                                "step_s": ct.get("step_s")}
            else:
                chain["ttt"] = {"planned": 0, "steps": 0}
            if FAST_LM is not None:
                FAST_LM.for_inference(model)
            if a.merge_for_decode and a.ttt_perms > 0:
                model.merge_adapter()
                merged = True; a._merged = True
            # Re-decode every OTHER input. The time left to the task deadline is split evenly over
            # the inputs still to go, recomputed per input, so no one input can starve the rest and
            # time one leaves unused passes to the next.
            others = [ti for ti in range(len(task["test"])) if ti != si]
            chain["inputs"] = []
            for k, ti in enumerate(others):
                _now = time.time()
                in_deadline = _now + max(0.0, task_deadline - _now) / (len(others) - k)
                entry, d, _ranked = decode_input(ti, task["test"][ti], chain_pairs, in_deadline, {})
                before_entry, before_diag = entries[ti], diag[ti]
                # A re-decode that found NOTHING (out of time) keeps the first pass's attempts:
                # its own would be the [[0]] placeholder. Recorded per input as "kept".
                kept = "after" if not d["empty"] else "before"
                if kept == "after":
                    entries[ti], diag[ti] = entry, d
                chain["inputs"].append({
                    "test_index": ti, "kept": kept, "deadline_s": round(in_deadline - t0, 1),
                    "before": {"attempt_1": before_entry["attempt_1"],
                               "attempt_2": before_entry["attempt_2"],
                               "pass_at_2": before_diag["pass_at_2"],
                               "any_of_n": before_diag["any_of_n"], "diagnostics": before_diag},
                    "after": {"attempt_1": entry["attempt_1"], "attempt_2": entry["attempt_2"],
                              "pass_at_2": d["pass_at_2"], "any_of_n": d["any_of_n"],
                              "diagnostics": d}})
        chain["chain_end_s"] = round(time.time() - t0, 1)

    restore = None
    if merged:
        model.unmerge_adapter()
        a._merged = False
        # Merging and unmerging happen in bf16 once per task, 120 times over a split, so a
        # round trip that does not restore would degrade the base weights silently — the
        # shape of failure this campaign has already paid for. Measured over 120 cycles the
        # drift is flat at one bf16 quantum; this checks each task against that baseline
        # rather than trusting it. Log-only: a drift that grows is a finding, not a reason
        # to abandon a task mid-run.
        probe = merge_probe(model)
        if probe is not None and a._probe_norm:
            now = float(probe.detach().float().norm().item())
            restore = {"baseline": a._probe_norm, "after_unmerge": round(now, 6),
                       "rel_drift": round(abs(now - a._probe_norm)
                                          / max(a._probe_norm, 1e-9), 9)}

    out = {"task": task["_id"], "entries": entries, "ttt": ttt, "restore": restore,
           "caveats": getattr(a, "_caveats", []),
           "train_s": round(train_s, 1), "total_s": round(time.time() - t0, 1),
           "diagnostics": diag}
    if a.chain == "on":
        # Present on every task of a chain-on run (null for a one-input task) so a paired read
        # can tell "not eligible" from "not recorded". Absent with --chain off: output unchanged.
        out["chain"] = chain
    return out


def _unsloth_import(a):
    """Stagger + environment + import, as the reference does (spec section 6): Unsloth patches
    globally and compiles into a cache dir on import, so rank r waits for rank r-1's ready file."""
    os.environ.setdefault("UNSLOTH_DISABLE_STATISTICS", "1")
    if os.path.exists("/usr/local/cuda/bin/ptxas"):
        os.environ.setdefault("TRITON_PTXAS_PATH", "/usr/local/cuda/bin/ptxas")
    if a.ttt_loss_weights or a.ttt_focal_resized or a.ttt_holdout_demo != "off":
        os.environ["UNSLOTH_RETURN_LOGITS"] = "1"   # the weighted TTT loss and the self-check read logits
    ready = os.path.join(tempfile.gettempdir(), "crucible-unsloth-ready-{}")
    if a.worker_id > 0:
        t0 = time.time()
        while not os.path.exists(ready.format(a.worker_id - 1)) and time.time() - t0 < 900:
            time.sleep(5)
    import unsloth  # noqa: F401  -- must precede transformers/peft imports
    from unsloth import FastLanguageModel
    open(ready.format(a.worker_id), "w").write("ok")
    import unsloth_zoo, transformers, peft, torch, triton
    a._versions = {m.__name__: getattr(m, "__version__", "?")
                   for m in (unsloth, unsloth_zoo, transformers, peft, torch, triton)}
    say(f"  [worker {a.worker_id}] G0 versions {a._versions}", flush=True)
    return FastLanguageModel


def run_worker(a):
    if a.self_test:
        return run_worker_self_test(a)

    global FAST_LM
    if a.backend == "unsloth":
        FAST_LM = _unsloth_import(a)
    import torch
    from peft import LoraConfig, get_peft_model, get_peft_model_state_dict
    from transformers import AutoModelForCausalLM, AutoTokenizer

    on_cpu = a.allow_cpu and not torch.cuda.is_available()
    if not torch.cuda.is_available() and not a.allow_cpu:
        raise SystemExit("FAIL: worker sees no GPU.")

    select_format(a.format)
    tokenizer = fmt.load_tokenizer()   # embedded base tokenizer: role tokens kept (2026-09-29)
    # Before any weight is loaded: the format module's entire premise is this tokenizer. For the
    # general-vocabulary format this also DERIVES the decoder's token set and fails loud if the
    # tokenizer does not split digits singly.
    fmt.assert_tokenizer(tokenizer)

    if on_cpu:
        # fp32, because half precision on CPU is unsupported for several of the operations here
        # and would fail for a reason that has nothing to do with the code under test.
        dtype = torch.float32
    else:
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    kw = {"attn_implementation": a.attn_impl} if a.attn_impl else {}
    if not on_cpu:
        kw["device_map"] = "auto"
    if a.quant == "int8":
        # THE 3060 INSTRUMENT. 12 GB cannot hold the bf16 recipe (peak 14.02 GB per task on the
        # Kaggle pool run), so the base is held in int8 and the adapter still trains in bf16.
        # This is a DIFFERENT instrument from the Kaggle one: int8 matmuls perturb logits, the
        # DFS prunes on logit thresholds, and the likelihood term ranks on them. Numbers from an
        # int8 run compare with each other, never with a bf16 run — the recipe records it.
        from transformers import BitsAndBytesConfig
        kw["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
    t0 = time.time()
    if FAST_LM is not None:
        model, _utok = FAST_LM.from_pretrained(model_name=a.model_dir, dtype=dtype,
                                               load_in_4bit=False, max_seq_length=a.max_seq_len,
                                               local_files_only=True)
        # The tokenizer Unsloth returns is IGNORED; ours (embedded, guarded) is used. Logged, not
        # fatal: FT-016/020/022 dirs carry the broken BPE tokenizer.json (spec section 3).
        _probe_txt = fmt.build_input([{"input": [[0, 1]], "output": [[2, 3]]}], [[4, 5]])
        a._tok_match = (_utok.encode(_probe_txt) == tokenizer.encode(_probe_txt))
        say(f"  [worker {a.worker_id}] unsloth tokenizer matches ours: {a._tok_match}", flush=True)
    else:
        model = AutoModelForCausalLM.from_pretrained(a.model_dir, dtype=dtype,
                                                     local_files_only=True, **kw)
    load_s = time.time() - t0

    placed = sorted({str(p.device) for p in model.parameters()})
    if not on_cpu and any(d in ("cpu", "disk") for d in placed):
        raise SystemExit(f"FAIL: layers landed on {placed} — every timing would measure offload.")

    if a.gradient_checkpointing and FAST_LM is None:
        # RULED ON. Numerically exact — activations are recomputed during backward instead of
        # held — so it changes memory and time and nothing about what is computed. Measured:
        # without it the per-token cost is 5.63 MB at full depth, capping the usable sequence at
        # ~1,669 tokens and losing half the evaluation split; with it, peak memory stops
        # depending on sequence length. Costs 1.39x on a training step, which is 14% of a run.
        #
        # The reference sets this False because unsloth pays its memory bill for it; we do not
        # have unsloth. Enabled before peft wraps the model, and inert during decode because
        # transformers only checkpoints while training — decode runs under eval().
        model.gradient_checkpointing_enable()
        # Without this the input to the first checkpointed block has no grad_fn, since the
        # embedding is frozen, and the recomputation has nothing to attach to.
        model.enable_input_require_grads()

    if FAST_LM is not None:
        # Unsloth moves embed_tokens to modules_to_save itself; lm_head stays LoRA. Our own
        # --embed-full branch is not applied here, so the embedding is not wrapped twice.
        # Checkpointing must be INSTALLED before any task can switch it on: for_training only flips
        # each layer's flag, and a flag with no checkpoint function behind it raises
        # (_gradient_checkpointing_func missing). transformers' own install is used -- the same
        # checkpointing every HF run has trained with. get_peft_model(use_gradient_checkpointing=
        # "unsloth") was tried and broke even short tasks (embedding index on the wrong device).
        # Every task then sets the flag: off for short tasks, on above --unsloth-gc-above.
        if a.unsloth_gc_above:
            model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model = FAST_LM.get_peft_model(
            model, r=a.lora_r, target_modules=a.targets, lora_alpha=a.lora_alpha, lora_dropout=0.0,
            bias="none", use_gradient_checkpointing=False, random_state=42, use_rslora=True)
    else:
      model = get_peft_model(model, LoraConfig(
        r=a.lora_r, lora_alpha=a.lora_alpha, lora_dropout=0.0, bias="none",
        task_type="CAUSAL_LM", use_rslora=True,
        # The reference's unsloth moves embed_tokens out of LoRA into modules_to_save, so the full
        # 16x2560 embedding trains per task (reset with the adapter). --embed-full off = LoRA on it.
        target_modules=[t for t in a.targets if not (a.embed_full == "on" and t == "embed_tokens")],
        modules_to_save=(["embed_tokens"] if a.embed_full == "on" and "embed_tokens" in a.targets
                         else None)))
    # The posted recipe casts the adapter to the compute dtype instead of keeping fp32 master
    # weights, so the optimizer runs in bf16 throughout. Reproduced deliberately: fp32 adapters
    # would be a different — probably better — recipe, and this run exists to establish parity.
    # --ttt-adapter-dtype fp32 KEEPS the fp32 master copy (base stays bf16). Measured on the training
    # side 2026-09-26: in bf16 a full-size step at lr 2e-5 rounds away on 48% of lora_A. The
    # changed cells' gradient is a small share of each step, so it is the first thing lost.
    if a.ttt_adapter_dtype != "fp32":
        for p in model.parameters():
            if p.dtype == torch.float32:
                p.data = p.data.to(dtype)

    # A caveat that must travel WITH the number, not alongside it in someone's notes. Without
    # cropping, an abandoned branch's state leaks into its sibling. For ordinary attention that is
    # stale keys; for a recurrent layer it is a polluted hidden state that cannot be rolled back at
    # all, which is why cropping is impossible on such an architecture in the first place.
    caveats = []
    # In A/B mode the crop flips per arm, so this runs once with whichever value the flag carried.
    # One arm is crop-off by construction, so the caveat applies to the run either way and must be
    # attached — a caveat that depends on which arm happened to be evaluated first is no caveat.
    if not a.kv_crop or getattr(a, "crop_ab", "off") == "on":
        cfg = getattr(model, "config", None)
        text_cfg = getattr(cfg, "text_config", cfg)
        layer_types = list(getattr(text_cfg, "layer_types", None) or [])
        n_lin = sum(1 for t in layer_types if "linear" in str(t))
        if n_lin:
            caveats.append(
                f"kv-crop OFF with {n_lin}/{len(layer_types)} recurrent (linear-attention) "
                f"layers: an abandoned search branch's HIDDEN STATE leaks into its sibling and "
                f"cannot be rolled back. Cropping is architecturally impossible here. Any number "
                f"from this run carries that caveat.")
        else:
            caveats.append("kv-crop OFF: a search step may attend over keys from an abandoned "
                           "branch (the reference's own behaviour; ~5% on measured throughput).")
    a._caveats = caveats
    for c in caveats:
        say(f"  [worker {a.worker_id}] CAVEAT: {c}")

    _probe = merge_probe(model)
    a._probe_norm = round(float(_probe.detach().float().norm().item()), 6) if _probe is not None \
        else None
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    a._initial = {k: v.clone().detach()
                  for k, v in get_peft_model_state_dict(model, adapter_name="default").items()}

    resident = [round(torch.cuda.memory_allocated(i) / 1e9, 2)
                for i in range(torch.cuda.device_count())] if not on_cpu else []
    say(f"  [worker {a.worker_id}] loaded in {load_s:.1f}s  {dtype}  on {placed}  "
        f"resident {resident} GB  trainable {trainable/1e6:.1f}M")
    emit("READY", {"worker": a.worker_id, "caveats": caveats,
                   "load_s": round(load_s, 1), "dtype": str(dtype),
                   "placed": placed, "resident_gb": resident, "trainable_params": trainable,
                   "attn_implementation": getattr(model.config, "_attn_implementation", "?")})

    tasks = load_split(a.data, a.split)
    deadline = a.end_time if a.end_time else time.time() + a.max_hours * 3600

    for line in sys.stdin:
        parts = line.split()
        if not parts or parts[0] == "quit":
            break
        if parts[0] != "solve":
            raise SystemExit(f"FAIL: worker got unknown command {line!r}")
        tid = parts[1]
        # PER-TASK PLAN (--task-seconds-max / --hard-ttt-perms): the parent may hand this task a
        # larger time cap and more TTT perms than the run default. Applied for this task only and
        # restored after it, so the next task starts from the run's own settings.
        _base_cap, _base_perms = a.task_seconds, a.ttt_perms
        _base_seed, _base_eval_seed = a.seed, a.eval_seed
        if len(parts) >= 4:
            a.task_seconds, a.ttt_perms = float(parts[2]), int(parts[3])
        if len(parts) >= 5 and int(parts[4]):
            # SECOND PASS: a new TTT seed and new eval views, so the pass is an independent sample to pool with the first.
            a.seed += int(parts[4])
            a.eval_seed = a.eval_seed + int(parts[4]) if a.eval_seed >= 0 else a.eval_seed
        if not on_cpu:
            torch.cuda.reset_peak_memory_stats()
        progress = {"phase": "start"}
        try:
            if getattr(a, "crop_ab", "off") == "on":
                # Arm A trains and snapshots; arm B reuses the snapshot. Order is fixed (crop-on
                # first) so it is a constant across tasks rather than another varying factor.
                a._ab_capture, a._ab_adapter = True, None
                a.kv_crop = True
                res_on = solve_task(model, tokenizer, tasks[tid], a, deadline, progress)
                a._ab_capture = False
                a.kv_crop = False
                # EQUALISE THE DECODE BUDGET. The per-task cap is measured from the start of
                # solve_task, and arm A spends part of it on TTT while arm B skips TTT entirely.
                # Left alone, arm B would get the FULL cap for decoding and arm A only what TTT
                # did not consume — so on any task that reaches the cap, the crop-on arm gets
                # truncated first and the crop would appear to cost yield it never cost. Hand arm
                # B exactly the decode window arm A had.
                _saved_cap = a.task_seconds
                a.task_seconds = max(1.0, a.task_seconds - res_on["train_s"])
                res_off = solve_task(model, tokenizer, tasks[tid], a, deadline, progress)
                a.task_seconds = _saved_cap
                a._ab_adapter = None
                result = dict(res_on)
                result["arm"] = "crop_on"
                result["paired_arm"] = {"arm": "crop_off",
                                        "entries": res_off["entries"],
                                        "diagnostics": res_off["diagnostics"],
                                        "total_s": res_off["total_s"],
                                        "restore": res_off["restore"],
                                        "ttt": res_off["ttt"]}
            else:
                result = solve_task(model, tokenizer, tasks[tid], a, deadline, progress)
        except Exception as e:
            if not is_oom(e):
                say(f"  [worker {a.worker_id}] task {tid} FAILED: {type(e).__name__}: {e}")
                raise
            # RECORDED, then reported as a result rather than as a crash. Running out of memory
            # is a legitimate ANSWER for a fit probe — it is the question being requested — and the
            # peak, the phase and the sequence length that caused it are the whole point. Letting
            # the exception kill the worker would throw away every number the run exists to get.
            peak = 0.0 if on_cpu else round(torch.cuda.max_memory_allocated() / 1e9, 2)
            torch.cuda.empty_cache()
            # E2 — REPAIR THE MERGE BEFORE CONTINUING. An OOM between merge and unmerge leaves the
            # adapter fused into the base; continuing would run every later task on weights this
            # task modified. Unmerge, then VERIFY against the fingerprint taken at load rather
            # than trusting that the unmerge worked — the whole failure mode here is a silent one,
            # and an unverified repair is the same class of assumption that created it.
            unmerge_ok = repair_merge_after_failure(model, a)
            say(f"  [worker {a.worker_id}] task {tid} OUT OF MEMORY in {progress.get('phase')} "
                f"at seq {progress.get('seq')}, peak {peak} GB")
            emit("RESULT", {"task": tid, "worker": a.worker_id, "entries": [],
                            "oom": " ".join(str(e).split())[:300], "at": dict(progress),
                            "peak_gb": peak, "ttt": {"oom": True}, "train_s": 0.0,
                            "total_s": 0.0, "diagnostics": [],
                            "unmerge_after_oom": unmerge_ok,
                            "plan": {"task_seconds": a.task_seconds, "ttt_perms": a.ttt_perms}})
            a.task_seconds, a.ttt_perms = _base_cap, _base_perms
            a.seed, a.eval_seed = _base_seed, _base_eval_seed
            continue
        result["peak_gb"] = (0.0 if on_cpu
                             else round(torch.cuda.max_memory_allocated() / 1e9, 2))
        result["worker"] = a.worker_id
        result["plan"] = {"task_seconds": a.task_seconds, "ttt_perms": a.ttt_perms, "seed": a.seed}
        a.task_seconds, a.ttt_perms = _base_cap, _base_perms
        a.seed, a.eval_seed = _base_seed, _base_eval_seed
        say(f"  [worker {a.worker_id}] {tid}  {result['total_s']:.0f}s "
            f"(train {result['train_s']:.0f}s)  peak {result['peak_gb']} GB")
        emit("RESULT", result)
        if not on_cpu:
            torch.cuda.empty_cache()


def run_worker_self_test(a):
    """Answer the protocol without a model or a GPU.

    Every number emitted here is invented. It exercises spawn, dispatch, collection, submission
    assembly and scoring — nothing about the model.
    """
    emit("READY", {"worker": a.worker_id, "load_s": 0.0, "dtype": "self-test", "placed": [],
                   "resident_gb": [], "trainable_params": 0, "attn_implementation": "self-test"})
    tasks = load_split(a.data, a.split)
    for line in sys.stdin:
        parts = line.split()
        if not parts or parts[0] == "quit":
            break
        tid = parts[1]
        n = len(tasks[tid]["test"])
        cap, perms = (float(parts[2]), int(parts[3])) if len(parts) >= 4 else (a.task_seconds, a.ttt_perms)
        off = int(parts[4]) if len(parts) >= 5 else 0
        # Invented candidates: pass 1 prefers [[1]] (2 votes) over [[9]] (1); a second pass votes [[9]] x3, so pooling
        # must flip the pick to [[9]] -- the self-test checks the merge, not the model.
        rtop = [["[[9]]", 3, 0.1, 3]] if off else [["[[1]]", 2, 0.1, 2], ["[[9]]", 1, 0.2, 1]]
        # PARITY_SELFTEST_SCALE > 0: sleep task_cells * scale * perms / run perms, capped at the
        # task's cap, so the scheduler can be exercised against a cost that grows with task size.
        scale = float(os.environ.get("PARITY_SELFTEST_SCALE", "0") or 0)
        took = 0.0
        if scale > 0:
            took = min(cap, task_cells(tasks[tid]) * scale * perms / max(1, a.ttt_perms))
            time.sleep(took)
        emit("RESULT", {"task": tid, "worker": a.worker_id, "plan": {"task_seconds": cap, "ttt_perms": perms, "seed": off},
                        "entries": [{"attempt_1": json.loads(rtop[0][0]), "attempt_2": json.loads(rtop[-1][0])} for _ in range(n)],
                        "ttt": {"steps": 0}, "train_s": 0.0, "total_s": round(took, 3), "peak_gb": 0.0,
                        "diagnostics": [{"task": tid, "test_index": i, "views": 0, "beams": 0,
                                         "parsed": 0, "distinct": 0, "empty": True,
                                         "dfs_forwards": 0, "dfs_timeouts": 0, "top": [], "ranked_top": rtop,
                                         "any_of_n": False, "pass_at_2": False}
                                        for i in range(n)]})


# ------------------------------------------------------------------ parent

def task_cells(task):
    """Grid cells in a task's demos and test inputs: the difficulty measure for dispatch order.
    Over 105 eval tasks (Colab A100, 10-29) it ranks solve time at Spearman 0.75."""
    def n(g):
        return len(g) * len(g[0]) if g and g[0] else 0
    return (sum(n(p["input"]) + n(p.get("output")) for p in task["train"])
            + sum(n(p["input"]) for p in task["test"]))


def dispatch_order(a, tasks, ids):
    """Smallest tasks first with --difficulty-order on, so time the quick ones leave unused
    passes, through the fair share, to the large ones at the end. Off keeps the given order."""
    if a.difficulty_order == "on":
        return sorted(ids, key=lambda t: (task_cells(tasks[t]), t))
    return list(ids)


def hard_tasks(a, tasks, ids):
    """The largest --hard-frac of the run's tasks by cells: the ones --hard-ttt-perms may go to."""
    if a.hard_ttt_perms <= a.ttt_perms:
        return set()
    by_size = sorted(ids, key=lambda t: (task_cells(tasks[t]), t))
    k = int(round(len(by_size) * a.hard_frac))
    return set(by_size[len(by_size) - k:]) if k > 0 else set()


def hard_min_share(a):
    return a.hard_min_share if a.hard_min_share > 0 else 2.0 * a.task_seconds


def plan_task(a, tid, hard, now, end_time, n_workers, n_left):
    """(cap, perms, share) for one task. Never below the run defaults: the cap rises to the fair
    share (bounded by --task-seconds-max) and a hard task gets --hard-ttt-perms only when the
    share is at least hard_min_share. The fair share keeps --plan-reserve-s back for the end."""
    share = (end_time - now - a.plan_reserve_s) * n_workers / max(1, n_left)
    cap, perms = a.task_seconds, a.ttt_perms
    if a.task_seconds_max > cap and share > cap:
        cap = min(a.task_seconds_max, share)
    if a.all_ttt_perms > perms and share >= a.all_min_share:
        perms = a.all_ttt_perms
    if a.hard_ttt_perms > perms and tid in hard and share >= hard_min_share(a):
        perms = a.hard_ttt_perms
    return cap, perms, share


def task_margin(a, r):
    """How sure pass 1 was of a task: the smallest gap, over its inputs, between the top two candidates' selection
    scores (votes - select_nll_weight x mean aug NLL). A single candidate counts as its own score. No candidates = 0."""
    gaps = []
    for d in r.get("diagnostics") or []:
        sel = [c - a.select_nll_weight * m for _k, c, m, _n in d.get("ranked_top") or []]
        gaps.append(0.0 if not sel else (sel[0] - sel[1] if len(sel) > 1 else sel[0]))
    return min(gaps) if gaps else 0.0


def pool_passes(a, r1, r2):
    """Merge a second-pass result into the first, input by input: votes add, augmented NLL means combine weighted by
    how many views produced them, and the usual selection (votes - w x mean NLL) picks the top two. An input the
    second pass did not answer (OOM, out of time, nothing parsed) keeps the first pass's attempts."""
    if r2.get("oom") or len(r2.get("diagnostics") or []) != len(r1.get("diagnostics") or []):
        out = dict(r1); out["pass2"] = {"kept": "pass1", "reason": "oom" if r2.get("oom") else "shape"}
        return out
    entries, diag = [], []
    for e1, d1, d2 in zip(r1["entries"], r1["diagnostics"], r2["diagnostics"]):
        if not d2.get("ranked_top"):
            entries.append(e1); diag.append(dict(d1, pooled="pass1")); continue
        pool = {}
        for k, c, m, n in (d1.get("ranked_top") or []) + d2["ranked_top"]:
            v = pool.setdefault(k, [0, 0.0, 0])
            v[0] += c; v[1] += m * max(n, 1); v[2] += max(n, 1)
        ranked = sorted(((c - a.select_nll_weight * (ms / max(nn, 1)), k, c, ms / max(nn, 1), nn)
                         for k, (c, ms, nn) in pool.items()), key=lambda x: -x[0])
        picks = [json.loads(x[1]) for x in ranked[:2]]
        while len(picks) < 2:
            picks.append(picks[0])
        entries.append({"attempt_1": picks[0], "attempt_2": picks[1]})
        diag.append(dict(d1, pooled="both", ranked_top=[[k, c, round(m, 6), n] for _s, k, c, m, n in ranked[:8]]))
    out = dict(r1)
    out.update(entries=entries, diagnostics=diag, total_s=r1.get("total_s", 0) + r2.get("total_s", 0),
               pass1={"entries": r1["entries"], "total_s": r1.get("total_s")},
               pass2={"kept": "pooled", "total_s": r2.get("total_s"), "plan": r2.get("plan")})
    return out


def load_split(data_dir, split):
    tasks = scorer.load_tasks(data_dir, split)
    for tid, task in tasks.items():
        task["_id"] = tid
    return tasks


class Worker:
    def __init__(self, argv, cards, wid):
        env = dict(os.environ)
        if cards is not None:
            env["CUDA_VISIBLE_DEVICES"] = cards
        cmd = [sys.executable, os.path.abspath(__file__), "--worker",
               "--worker-id", str(wid)] + argv
        self.wid = wid
        self.busy = None
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  text=True, bufsize=1, env=env)

    def fileno(self):
        return self.p.stdout.fileno()

    def read(self, kind):
        for line in self.p.stdout:
            if line.startswith("@" + kind + " "):
                return json.loads(line[len(kind) + 2:])
            if line.startswith("@"):
                raise SystemExit(f"FAIL: worker {self.wid} sent {line.strip()!r}, wanted {kind}")
        rc = self.p.wait()
        raise SystemExit(f"FAIL: worker {self.wid} died (exit {rc}) before sending {kind}. Its "
                         f"stderr is above.")

    def send(self, cmd):
        self.p.stdin.write(cmd + "\n")
        self.p.stdin.flush()

    def close(self):
        try:
            self.send("quit")
            self.p.wait(timeout=120)
        except Exception:
            self.p.kill()


def parse_members(spec, n_default):
    """'0;1;2;3' or '0,1;2,3' — one entry per worker, naming the cards it owns."""
    if not spec:
        return [str(i) for i in range(n_default)]
    return [m.strip() for m in spec.split(";") if m.strip()]


def write_results(a, tasks, ids, results, members, ready, start):
    """Assemble, grade and WRITE the run's output.

    Called after every completed task, not only at the end. A parity session is hours long and
    the venue enforces a hard wall-clock limit, so a run that is cut off must still leave behind
    the tasks it did finish — otherwise an interruption at hour five costs five hours and the
    decision to re-run becomes hostage to sunk cost.
    """
    # The submission must cover every task the venue requested about, not merely the ones this run
    # processed. They differ whenever a run is deliberately partial — a rehearsal against the
    # stand-in, or a session cut short by the wall-clock guard — and a submission missing tasks
    # is malformed rather than merely low-scoring.
    submission = {}
    for tid in getattr(a, "_submission_ids", None) or ids:
        r = results.get(tid)
        n = len(tasks[tid]["test"])
        if r is None or len(r["entries"]) != n:
            # A task that never ran, or that died partway, still needs correctly shaped entries.
            submission[tid] = [{"attempt_1": [[0]], "attempt_2": [[0]]} for _ in range(n)]
        else:
            submission[tid] = r["entries"]

    # Graded on the tasks that RAN. Scoring the placeholder-filled remainder would
    # report a fraction of a split nobody attempted as though it had been attempted.
    graded = scorer.score({t: tasks[t] for t in ids},
                          {t: submission[t] for t in ids})

    diag = [d for r in results.values() for d in r["diagnostics"]]
    n_inputs = max(1, len(diag))
    any_of_n = sum(1 for d in diag if d["any_of_n"]) / n_inputs
    pass_2 = sum(1 for d in diag if d["pass_at_2"]) / n_inputs
    empty = sum(1 for d in diag if d["empty"])

    payload = {
        "model_dir": a.model_dir, "split": a.split, "tasks": len(ids),
        "shard": getattr(a, "_shard_note", None), "task_ids": list(ids),
        "completed": len(results), "unstarted": len(ids) - len(results),
        "workers": len(members), "cards": members,
        "recipe": {"lora_r": a.lora_r, "lora_alpha": a.lora_alpha, "rslora": True,
                   "targets": a.targets, "ttt_examples": 8 * a.ttt_perms, "lr": a.lr,
                   "max_seq_len": a.max_seq_len,
                   "ttt_seq_len": a.ttt_seq_len, "eval_views": 8 * a.eval_perms,
                   "topup_below": a.topup_below, "topup_perms": a.topup_perms, "unsure_count": a.unsure_count,
                   "select_nll_weight": a.select_nll_weight,
                   "score_perms": a.score_perms, "score_views_n": 8 * a.score_perms,
                   "chain": a.chain,
                   "chain_min_views": a.chain_min_views, "chain_min_margin": a.chain_min_margin,
                   "chain_ttt_steps": a.chain_ttt_steps, "chain_budget_frac": a.chain_budget_frac,
                   "dev_search": a.dev_search, "pre_ttt_decode": a.pre_ttt_decode,
                   "floor_mode": a.floor_mode, "token_floor": a.token_floor, "mean_nll_cap": a.mean_nll_cap,
                   "branch_cap": a.branch_cap, "max_deviations": a.max_deviations, "demo_shape": a.demo_shape,
                   "ttt_objective": a.ttt_objective, "ttt_focal_resized": a.ttt_focal_resized,
                   "ttt_holdout_demo": a.ttt_holdout_demo, "ttt_adaptive": a.ttt_adaptive,
                   "ttt_adaptive_extra": a.ttt_adaptive_extra, "ttt_adaptive_min": a.ttt_adaptive_min,
                   "ttt_adapter_dtype": a.ttt_adapter_dtype, "ttt_loss_weights": a.ttt_loss_weights,
                   "embed_full": a.embed_full, "backend": a.backend,
                   "versions": getattr(a, "_versions", None), "unsloth_tokenizer_match": getattr(a, "_tok_match", None), "demo_shuffle": "decode+score", "score_views": "per input",
                   "colour_perm": "fresh per view", "tokenizer": "embedded base WordLevel (roles kept)",
                   "decode_batch": a.decode_batch, "prob_floor": a.prob_floor,
                   "prob_floor_is_cumulative": True, "kv_crop": a.kv_crop,
                   "merge_for_decode": a.merge_for_decode,
                   "gradient_checkpointing": a.gradient_checkpointing,
                   "format": a.format,
                   "fused_ce_chunk": a.fused_ce,
                   "extra_candidates": a.extra_candidates, "extra_votes": a.extra_votes,
                   "persist_candidates": a.persist_candidates,
                   "eval_seed": a.eval_seed,
                   "quant": a.quant,
                   "caveats": sorted({c for r in results.values()
                                      for c in (r.get("caveats") or [])}),
                   "task_seconds": a.task_seconds, "selection": "count - mean augmented nll"},
        "venue": ready,
        # Both aggregation rules, because which one the leaderboard uses is not settled from a
        # primary source. See the header of crucible-score.py.
        "TASK_SCORE_strict": graded["score"], "tasks_solved": graded["solved"],
        "TASK_SCORE_partial": graded["score_partial"], "credit": graded["credit"],
        "per_input_pass_at_2": round(pass_2, 4),
        "per_input_any_of_n": round(any_of_n, 4),
        "selection_headroom": round(any_of_n - pass_2, 4),
        "test_inputs_with_no_candidate": empty,
        "worst_unmerge_drift": max([r["restore"]["rel_drift"] for r in results.values()
                                    if r.get("restore")] or [0.0]),
        "candidates_dropped_past_cap": sum(d.get("dropped_past_cap", 0) for d in diag),
        "tasks_dropping_past_cap": sorted({d["task"] for d in diag
                                           if d.get("dropped_past_cap")}),
        "wall_s": round(time.time() - start, 1),
        "oom": [{"task": t, "at": r["at"], "peak_gb": r["peak_gb"], "error": r["oom"]}
                for t, r in results.items() if r.get("oom")],
        "results": results,
    }
    if a.invalid_note:
        payload["VALID"] = False
        payload["INVALID_REASON"] = a.invalid_note
    with open(a.out, "w") as fh:
        json.dump(payload, fh, indent=1)
    if a.submission:
        with open(a.submission, "w") as fh:
            json.dump(submission, fh)
    return submission, graded, payload


def merge_chunks(paths, tasks, full_ids, allow_incomplete):
    """Recombine chunk results into one score over the whole split.

    A parity baseline is DEFINED over the full evaluation split, so chunks that cannot be proven
    to tile it are not a baseline. Both properties are checked before any number is emitted:

      disjoint      no task may appear in two chunks. An overlap means one task's answer silently
                    overwrites another's, and the score would be computed over a set nobody
                    chose.
      complete      the union must be exactly the split. A missing task is scored zero by the
                    scorer, which is indistinguishable from a task the model failed — the one
                    confusion that would make the parity number wrong in the flattering
                    direction.
    """
    merged, seen_from = {}, {}
    chunks = []
    for path in paths:
        with open(path) as fh:
            payload = json.load(fh)
        chunks.append({"path": path, "shard": payload.get("shard"),
                       "completed": payload.get("completed"),
                       "tasks": payload.get("tasks"),
                       "recipe": payload.get("recipe")})
        for tid, r in (payload.get("results") or {}).items():
            if tid in merged:
                raise SystemExit(
                    f"FAIL: task {tid} appears in two chunks — {seen_from[tid]} and {path}. "
                    f"The chunks are not disjoint, so a merged score would be taken over a set "
                    f"nobody chose. Re-run with a correct --shard partition.")
            merged[tid] = r
            seen_from[tid] = path

    missing = [t for t in full_ids if t not in merged]
    extra = [t for t in merged if t not in set(full_ids)]
    if extra:
        raise SystemExit(f"FAIL: {len(extra)} task(s) in the chunks are not in this split, e.g. "
                         f"{extra[:5]} — the chunks were produced against different data.")
    if missing and not allow_incomplete:
        raise SystemExit(
            f"FAIL: {len(missing)} of {len(full_ids)} tasks are missing from the chunks, e.g. "
            f"{missing[:5]}. A missing task scores zero and is indistinguishable from a failed "
            f"one, so this would understate nothing and overstate coverage. Run the missing "
            f"chunk, or pass --allow-incomplete to emit a clearly-stamped partial number.")

    # The recipe must match across chunks, or the halves are measuring different things.
    recipes = {json.dumps(c["recipe"], sort_keys=True) for c in chunks if c["recipe"]}
    if len(recipes) > 1:
        raise SystemExit("FAIL: chunks were run under different recipes; a merged score would "
                         "average two different experiments. Recipes seen:\n  "
                         + "\n  ".join(sorted(recipes)))
    return merged, chunks, missing


def main():
    ap = argparse.ArgumentParser(description="Parity baseline: the posted pack recipe.")
    ap.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--worker-id", type=int, default=0, help=argparse.SUPPRESS)

    ap.add_argument("--model-dir", default="", help="LOCAL weights. This harness cannot fetch.")
    ap.add_argument("--data", default="data-kaggle")
    ap.add_argument("--split", default="evaluation",
                    choices=["training", "evaluation", "test"])
    ap.add_argument("--tasks", type=int, default=0, help="0 = the whole split")
    ap.add_argument("--task-ids", default="", help="comma-separated ids; overrides --tasks")
    ap.add_argument("--shard", default="",
                    help="run one chunk of the split, as K/N with K counted from 1: '1/4' is the "
                         "first quarter. CONTIGUOUS blocks of the sorted task-id list, so a chunk "
                         "is a nameable range and a failed one is obvious to re-run. The chunks "
                         "are disjoint and cover the split exactly; --merge checks both before it "
                         "will emit a score")
    ap.add_argument("--members", default="",
                    help="one entry per worker naming its cards: '0;1;2;3' for four replicas, "
                         "'0,1;2,3' for two workers of two cards each. Default: one per card")

    ap.add_argument("--lora-r", type=int, default=256)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--targets", default=",".join(LORA_TARGETS))
    ap.add_argument("--ttt-perms", type=int, default=16,
                    help="colour permutations per dihedral symmetry in the training set; the "
                         "posted recipe uses 16, giving 8x16 = 128 examples and one step each. "
                         "0 disables test-time training entirely")
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--warmup-ratio", type=float, default=0.1)
    ap.add_argument("--max-grad-norm", type=float, default=1.0)
    ap.add_argument("--max-seq-len", type=int, default=8192,
                    help="context budget for DECODING and for scoring a candidate")
    ap.add_argument("--ttt-seq-len", type=int, default=0,
                    help="context budget for a TRAINING example; 0 means use --max-seq-len. "
                         "These are separate because they cost completely different amounts: a "
                         "training step holds optimizer state, gradients and full-sequence loss "
                         "logits, while decoding holds none of those and materialises logits for "
                         "one position. Forcing decode down to whatever training can afford would "
                         "leave no room for the prompt — at 1024 the answer alone reserves 931 "
                         "tokens and every demonstration gets dropped")
    ap.add_argument("--seed", type=int, default=42)

    ap.add_argument("--eval-perms", type=int, default=2,
                    help="colour permutations per dihedral symmetry at decode time; 2 gives the "
                         "posted recipe's 16 views")
    ap.add_argument("--topup-below", type=int, default=0,
                    help="ADAPTIVE VIEWS. After the base views are decoded, if the candidate pool "
                         "holds FEWER than this many distinct grids, decode --topup-perms more "
                         "permutations for that input only. 0 disables it (uniform views). "
                         "Measured on 860 inputs: 10%% of inputs produce NO candidate and 8%% "
                         "produce exactly one, and a one-grid pool scores 33%% against 45%% for "
                         "pools of 4-6 -- collapse is a failure signal, not confidence. Raising "
                         "views for EVERY input costs +22%% of run time and also doubles the share "
                         "of tasks hitting the per-task cap (8%% -> 14%%); topping up only the thin "
                         "31%% costs +6.9%% and leaves the healthy pools alone, which is where more "
                         "candidates were not helping anyway.")
    ap.add_argument("--select-nll-weight", type=float, default=1.0,
                    help="SELECTION: candidates rank by  votes - W * mean aug NLL.  1.0 is the posted "
                         "recipe. Tuned offline on the persisted pools of the FT-020 and FT-016 "
                         "spliced evals (crucible-selection-study.py): 0.15-0.35 is a plateau that "
                         "gains 3/0 (FT-020) and 2/1 (FT-016) inputs gained/lost against 1.0, and "
                         "the same value won when fit on either eval and checked on the other.")
    ap.add_argument("--score-perms", type=int, default=1,
                    help="candidate scoring/selection uses 8*N augmented views per test input "
                         "(1 = the 8 the recipe always used; N>1 keeps those 8 as its first 8)")
    ap.add_argument("--chain", default="off", choices=["off", "on"],
                    help="on: for a task with 2+ test inputs, after the normal pass, a confident "
                         "input's rank-1 candidate becomes an extra demo, the adapter trains "
                         "--chain-ttt-steps more, and the OTHER inputs are re-decoded and re-scored")
    ap.add_argument("--chain-min-views", type=int, default=8,
                    help="--chain: the seed's rank-1 candidate must come from at least this many views")
    ap.add_argument("--chain-min-margin", type=float, default=4.0,
                    help="--chain: and lead its rank-2 by at least this much selection score")
    ap.add_argument("--chain-ttt-steps", type=int, default=32,
                    help="--chain: extra TTT steps on the adapter with the seed pair as a demo")
    ap.add_argument("--chain-budget-frac", type=float, default=0.25,
                    help="--chain: share of the post-TTT task time held back for the chain pass; "
                         "the normal pass stops at the rest (only on tasks with 2+ inputs)")
    ap.add_argument("--unsure-count", type=int, default=0,
                    help="also top up an input whose leading candidate came from this many views or fewer (0 = off; 2026-10-22)")
    ap.add_argument("--topup-perms", type=int, default=1,
                    help="extra colour permutations (8 views each) when --topup-below fires")
    ap.add_argument("--decode-batch", type=int, default=4,
                    help="views decoded together, sharing one KV cache")
    ap.add_argument("--score-batch", type=int, default=4)
    ap.add_argument("--prob-floor", type=float, default=0.2,
                    help="minimum probability of a WHOLE answer for the search to keep it. This "
                         "is a cumulative cutoff, not a per-token threshold")
    ap.add_argument("--backend", default="hf", choices=["hf", "unsloth"],
                    help="hf = transformers+PEFT, hand-written loop (every run before the port). "
                         "unsloth = FastLanguageModel load/PEFT/for_training/for_inference, unmerged "
                         "decode, as the reference (CRUCIBLE-UNSLOTH-PORT-SPEC.md).")
    ap.add_argument("--unsloth-gc-above", type=int, default=2400,
                    help="under --backend unsloth, TTT for a task whose longest example exceeds this "
                         "many tokens runs with Unsloth gradient checkpointing ('unsloth'); shorter "
                         "tasks train without it. 0 = never. Without it TTT ran out of memory on L4 "
                         "at 5,238-7,464 tokens (peak 23.3 GB, 2026-09-30); 2,382 peaked at 19.4 GB.")
    ap.add_argument("--inject-oom-task", default="",
                    help="TEST ONLY: raise a CUDA out-of-memory error in TTT for this task id, to "
                         "exercise the recovery path. Never set on a submission.")
    ap.add_argument("--embed-full", default="on", choices=["on", "off"],
                    help="train embed_tokens fully per task (modules_to_save), as the reference's "
                         "unsloth does; off = LoRA on it (every run before 2026-09-29).")
    ap.add_argument("--ttt-objective", default="chain", choices=["chain", "loo"],
                    help="chain = today (whole demo chain, loss on every output); loo = leave-one-out (spec §1)")
    ap.add_argument("--ttt-focal-resized", type=float, default=0.0,
                    help="G: weight resized-output tokens by (1-p_gold)^G (spec §1, M2); 0 = off. Use with loo")
    ap.add_argument("--ttt-holdout-demo", default="off", choices=["off", "auto"],
                    help="auto: 4+-demo tasks hold one demo out of TTT for a self-check and early stop (spec §2)")
    ap.add_argument("--ttt-adaptive", default="off", choices=["off", "on"],
                    help="with --ttt-holdout-demo auto: no early stop; after the held-out read, train a second phase "
                         "with ALL demos, --ttt-adaptive-extra steps if the held demo is still wrong, else --ttt-adaptive-min")
    ap.add_argument("--ttt-adaptive-extra", type=int, default=128)
    ap.add_argument("--ttt-adaptive-min", type=int, default=32)
    ap.add_argument("--floor-mode", default="cumulative", choices=["cumulative", "per-token", "length-norm"],
                    help="decode floor (spec §4). cumulative = today (--prob-floor on the whole answer)")
    ap.add_argument("--token-floor", type=float, default=0.1, help="per-token: min p of each token")
    ap.add_argument("--mean-nll-cap", type=float, default=0.05, help="length-norm: max mean NLL per token")
    ap.add_argument("--branch-cap", type=int, default=2, help="per-token/length-norm: top-B tokens per position")
    ap.add_argument("--max-deviations", type=int, default=-1,
                    help="per-token/length-norm: max non-top choices per answer (-1 = no cap)")
    ap.add_argument("--demo-shape", default="off", choices=["on", "off"],
                    help="force the decoded grid to the (H, W) the demos fix (spec §4); off = today")
    ap.add_argument("--ttt-loss-weights", default="",
                    help="COPIED,CHANGED e.g. 0.1,1.0: weight TTT's loss onto the cells the rule "
                         "changes (the trainer's --w-copied/--w-changed). Empty = plain mean.")
    ap.add_argument("--ttt-adapter-dtype", default="compute", choices=["compute", "fp32"],
                    help="dtype of the TTT adapter. compute = cast to bf16 (the posted recipe, kept "
                         "for parity); fp32 = keep fp32 master weights. ~+4 GB for r=256.")
    ap.add_argument("--dev-search", default="",
                    help="K,TAU e.g. 3,0.9: replace the cumulative floor with a K-deviation search -- "
                         "follow the top token, take the 2nd where the top is below TAU, at most K "
                         "times per answer. Empty = the cumulative --prob-floor, unchanged.")
    ap.add_argument("--pre-ttt-decode", default="off", choices=["off", "on"],
                    help="ALSO decode the base views with the UNTRAINED adapter before TTT and pool "
                         "those answers with the trained ones (scored by the trained model). "
                         "Measured 2026-09-28 on the 39: TTT on solved 8 tasks, TTT off solved 6, "
                         "and only 2 overlap -- TTT loses 4 tasks the untrained model solves.")
    ap.add_argument("--eval-seed", type=int, default=2,
                    help="seed for the decode-time colour permutations. The reference hard-codes "
                         "2 for every task and that is the default here; -1 restores the "
                         "per-task draw the parity baseline ran with")
    ap.add_argument("--extra-candidates", default="",
                    help="comma-separated ARC submission files (another model's attempt_1/attempt_2 per test input): "
                         "every distinct grid is scored like our own candidates and joins selection with --extra-votes")
    ap.add_argument("--extra-votes", type=float, default=1.0,
                    help="votes an extra candidate adds on top of the views that produced it here")
    ap.add_argument("--persist-candidates", default="auto", choices=["auto", "on", "off"],
                    help="AUTO ties it to the MODE, which is what it should always have been: ON "
                         "for --split evaluation, OFF for --split test. An eval has gold, so the "
                         "candidate pool can be labelled and selection retuned offline instead of "
                         "costing a 9.4 h re-run. A SUBMISSION has no gold -- the pool cannot be "
                         "labelled, so writing it buys nothing and costs payload on the only run "
                         "that scores. It was opt-in for a month and never once switched on, "
                         "which is why 860 inputs of selection headroom were unanswerable; making "
                         "it a global default then switched it on for submissions too, which is "
                         "the opposite mistake.")
    ap.add_argument("--fused-ce", type=int, default=0,
                    help="chunk size for the sliced training loss; 0 uses the model's own loss. "
                         "Set only where crucible-fusedce.py has been shown equivalent on THIS "
                         "model at THIS dtype — an unverified loss trains a quietly wrong model")
    ap.add_argument("--format", default="grids15", choices=["grids15", "general4b"],
                    help="grids15: the adopted base's 16-token format. general4b: the same task "
                         "shape rendered with a general model's own chat template, with the "
                         "decoder's token set derived from its tokenizer")
    ap.add_argument("--gradient-checkpointing", default="on", choices=["on", "off"],
                    help="recompute activations during backward instead of storing them. On by "
                         "ruling: it is numerically exact, and off caps the usable sequence at "
                         "~1669 tokens, which loses half the split")
    ap.add_argument("--merge-for-decode", default="on", choices=["on", "off"],
                    help="fold the adapter into the base weights before decoding and unfold it "
                         "afterwards. NOT what the reference does (its unsloth for_inference() "
                         "decodes unmerged); kept for speed -- off costs ~1.6x on decode")
    ap.add_argument("--crop-ab", default="off", choices=["on", "off"],
                    help="Paired kv-crop A/B: TTT ONCE per task, then decode twice from the "
                         "identical adapter with the crop on and off. The pairing is the point — "
                         "TTT is stochastic, so two independent runs would differ by the adapter "
                         "as well as by the crop, and at this effect size that is unrecoverable.")
    ap.add_argument("--kv-crop", default="on", choices=["on", "off"],
                    help="crop the shared KV cache back to the branch point before each step. "
                         "off reproduces the reference implementation, which lets a step attend "
                         "over keys from an abandoned branch")
    ap.add_argument("--task-seconds", type=float, default=1200.0,
                    help="wall-clock cap per task, as in the posted recipe")
    ap.add_argument("--difficulty-order", choices=["off", "on"], default="off",
                    help="dispatch tasks smallest first by grid cells (task_cells)")
    ap.add_argument("--task-seconds-max", type=float, default=0.0,
                    help="raise a task's cap up to this when the fair share of the run time left "
                         "allows it (0 = off: every task gets --task-seconds)")
    ap.add_argument("--hard-ttt-perms", type=int, default=0,
                    help="TTT perms for the largest --hard-frac tasks when the fair share is at "
                         "least --hard-min-share (0 = off)")
    ap.add_argument("--hard-frac", type=float, default=0.25,
                    help="share of the run's tasks, largest by cells, that --hard-ttt-perms may go to")
    ap.add_argument("--hard-min-share", type=float, default=0.0,
                    help="fair share (s) needed before a hard task gets --hard-ttt-perms "
                         "(0 = 2 x --task-seconds)")
    ap.add_argument("--all-ttt-perms", type=int, default=0,
                    help="TTT perms for ANY task once the fair share is at least --all-min-share (0 = off); "
                         "--hard-ttt-perms still applies on top for the hard tasks")
    ap.add_argument("--all-min-share", type=float, default=0.0,
                    help="fair share (s) needed before any task gets --all-ttt-perms")
    ap.add_argument("--ttt-frac", type=float, default=0.0,
                    help="cap TTT at this share of the time left to the task deadline (0 = off)")
    ap.add_argument("--second-pass", choices=["off", "on"], default="off",
                    help="after every task's first pass, re-run tasks with a new seed (least sure first, while time "
                         "allows) and pool both passes' candidates before the top-2 pick")
    ap.add_argument("--second-pass-seed", type=int, default=1000,
                    help="offset added to --seed and --eval-seed for the second pass")
    ap.add_argument("--plan-reserve-s", type=float, default=300.0,
                    help="run time held back from the fair share for the end of the run")
    ap.add_argument("--dfs-seconds", type=float, default=540.0,
                    help="wall-clock cap on a single batched search")
    ap.add_argument("--max-hours", type=float, default=11.9,
                    help="whole-run budget; the venue's limit is 12 h. NOT A GUILLOTINE ON THE "
                         "RESULTS: write_results() rewrites submission.json after every completed "
                         "task, so everything finished is already on disk, and workers honour the "
                         "global end_time so an in-flight task cannot overrun it. Reaching this "
                         "only stops NEW tasks being dispatched; unstarted ones fall back to the "
                         "placeholder. It was 11.5 for a month, which left ~24 min of a 12 h "
                         "allowance unused for no benefit. 11.9 keeps 6 min for the final write.")
    ap.add_argument("--end-time", type=float, default=0.0, help=argparse.SUPPRESS)
    ap.add_argument("--quant", default="off", choices=["off", "int8"],
                    help="hold the BASE in int8 via bitsandbytes (adapter stays bf16). A different "
                         "instrument from bf16; the recipe records it. Requires --merge-for-decode off")
    ap.add_argument("--attn-impl", default="",
                    help="attn_implementation for from_pretrained (flash_attention_2 on L4, "
                         "empty for the library default)")

    ap.add_argument("--out", default="crucible-parity.json")
    ap.add_argument("--submission", default="")
    ap.add_argument("--stand-in-sha", default="",
                    help="sha256 of the newline-joined sorted task ids of the PUBLIC "
                         "stand-in split. When the loaded split matches it, the run is "
                         "a rehearsal: a few tasks run end to end and the rest are "
                         "emitted as shaped placeholders.")
    ap.add_argument("--stand-in-tasks", type=int, default=2,
                    help="how many tasks a rehearsal runs for real.")
    ap.add_argument("--invalid-note", default="",
                    help="stamp every result with a reason it is not comparable — used for the "
                         "T4 harness-survival run, whose numbers describe the harness, not the "
                         "recipe")
    ap.add_argument("--allow-cpu", action="store_true",
                    help="run the model paths on the CPU. FOR THE LOGIC SMOKE ONLY: this box has "
                         "no GPU, so it is the only pre-flight available before a venue session "
                         "is spent. Every timing it produces is meaningless")
    ap.add_argument("--merge", default="",
                    help="comma-separated chunk result files to recombine into one score over "
                         "the whole split. Refuses unless the chunks are disjoint and complete")
    ap.add_argument("--allow-incomplete", action="store_true",
                    help="let --merge emit a stamped partial number despite missing tasks")
    ap.add_argument("--self-test", action="store_true",
                    help="exercise spawn, dispatch and scoring with no model and no GPU. Every "
                         "number it produces is invented; never a substitute for a measurement")
    a = ap.parse_args()

    if a.score_perms < 1:
        raise SystemExit("FAIL: --score-perms must be >= 1")
    if not 0.0 <= a.chain_budget_frac < 1.0:
        raise SystemExit("FAIL: --chain-budget-frac must be in [0, 1)")
    a.targets = [t.strip() for t in a.targets.split(",") if t.strip()]
    a.max_score = -__import__("math").log(a.prob_floor)
    if a.dev_search:
        _k, _tau = a.dev_search.split(",")
        globals()["DEV_SEARCH"] = (int(_k), float(_tau))
    if a.ttt_adaptive == "on" and a.ttt_holdout_demo != "auto":
        raise SystemExit("FAIL: --ttt-adaptive on needs --ttt-holdout-demo auto (it is the held-out read that sizes phase 2)")
    if a.ttt_focal_resized:
        if a.ttt_objective != "loo":
            raise SystemExit("FAIL: --ttt-focal-resized goes with --ttt-objective loo only (spec §1: under chain the "
                             "first output has no context and focal weighting amplifies that noise)")
        globals()["FOCAL_RESIZED"] = a.ttt_focal_resized
    if a.floor_mode != "cumulative":
        if a.dev_search:
            raise SystemExit("FAIL: --floor-mode and --dev-search are two different searches; set one")
        globals()["FLOOR"] = (a.floor_mode, a.token_floor if a.floor_mode == "per-token" else a.mean_nll_cap,
                              a.branch_cap, a.max_deviations)
    if a.backend == "unsloth":
        # Unsloth decodes unmerged at full speed (for_inference does not merge), and its fused
        # kernels replace our fused-CE path. Both forced off (spec sections 4-5).
        a.merge_for_decode = False
        a.fused_ce = 0
    if a.ttt_loss_weights:
        _wc, _wch = a.ttt_loss_weights.split(",")
        globals()["TTT_WEIGHTS"] = (float(_wc), float(_wch))
    a.kv_crop = (a.kv_crop == "on")
    a.merge_for_decode = (a.merge_for_decode == "on")
    a.gradient_checkpointing = (a.gradient_checkpointing == "on")
    if a.quant != "off" and a.merge_for_decode:
        # peft CAN merge into an 8-bit layer, by dequantising, adding, and requantising — which
        # rewrites the base weights with fresh rounding on every task. The unmerge fingerprint
        # would trip on the first task. Refuse rather than silently run a corrupting recipe.
        raise SystemExit("FAIL: --quant requires --merge-for-decode off (merging into an int8 "
                         "base requantises it; the base would not survive the first task)")
    if not a.ttt_seq_len:
        a.ttt_seq_len = a.max_seq_len
    if a.persist_candidates == "auto":
        a.persist_candidates = (a.split == "evaluation")
    else:
        a.persist_candidates = (a.persist_candidates == "on")
    a._probe_norm = None
    # A glob is expanded (recursive) because the Kaggle mount path of a dataset has varied between kernels; a pattern that
    # matches nothing is an error, never a silent run without the extra candidates.
    import glob as _glob
    _files = []
    for _p in [f for f in a.extra_candidates.split(",") if f]:
        _m = sorted(_glob.glob(_p, recursive=True)) if any(c in _p for c in "*?[") else [_p]
        if not _m:
            raise SystemExit(f"--extra-candidates: nothing matches {_p}")
        _files += _m
    for _f in _files:
        for _t, _ins in json.load(open(_f)).items():
            for _ti, _att in enumerate(_ins):
                _l = EXTRA.setdefault(_t, {}).setdefault(_ti, [])
                for _g in (_att.get("attempt_1"), _att.get("attempt_2")):
                    if _g and _g not in _l:
                        _l.append(_g)

    if a.worker:
        select_format(a.format)
        if not a.self_test and not os.path.isdir(a.model_dir):
            raise SystemExit(f"FAIL: --model-dir is not a directory: {a.model_dir}")
        return run_worker(a)

    # Merging reads finished chunk results and scores them; it loads no weights and needs no GPU,
    # so it must not be gated on a model directory.
    if not a.self_test and not a.merge and not os.path.isdir(a.model_dir):
        raise SystemExit(f"FAIL: --model-dir is not a directory: {a.model_dir}\n"
                         f"This harness cannot fetch; attach or materialize the weights first.")

    tasks = load_split(a.data, a.split)
    ids = sorted(tasks)

    if a.merge:
        paths = [x.strip() for x in a.merge.split(",") if x.strip()]
        results, chunks, missing = merge_chunks(paths, tasks, ids, a.allow_incomplete)
        print("== CRUCIBLE parity — merged ==")
        for c in chunks:
            sh = c["shard"]
            label = f"shard {sh['shard']}/{sh['of']} ({sh['first']}..{sh['last']})" if sh \
                else "unsharded"
            print(f"  {label:<44} {c['completed']}/{c['tasks']} tasks   {c['path']}")
        print(f"  merged {len(results)} tasks over a {len(ids)}-task split — "
              f"disjoint and {'COMPLETE' if not missing else f'MISSING {len(missing)}'}\n")
        a._shard_note = {"merged_from": [c["shard"] for c in chunks]}
        if missing:
            a.invalid_note = (f"partial merge: {len(missing)} of {len(ids)} tasks absent; "
                              f"missing tasks score zero and are not distinguishable from "
                              f"failures")
        _sub, graded, payload = write_results(a, tasks, ids, results, [], [], time.time())
        print(f"  TASK SCORE  strict   {graded['score']:.4f}  "
              f"({graded['solved']}/{graded['total']})")
        print(f"  TASK SCORE  partial  {graded['score_partial']:.4f}  "
              f"({graded['credit']}/{graded['total']})")
        print(f"  wrote {a.out}")
        return

    if a.task_ids:
        ids = [t.strip() for t in a.task_ids.split(",") if t.strip()]
        missing = [t for t in ids if t not in tasks]
        if missing:
            raise SystemExit(f"FAIL: no such task in the {a.split} split: {missing}")
    elif a.tasks:
        ids = ids[:a.tasks]

    # REHEARSAL AGAINST THE PUBLIC STAND-IN. A committed notebook run at the venue is handed a
    # PUBLIC placeholder test split, not the hidden one — measured: the mounted file is identical
    # to the copy on disk here, and no solutions accompany it. Its output is therefore discarded
    # and replaced when the notebook is evaluated against the real split, so processing all of it
    # would spend hours of quota producing an answer nobody reads.
    #
    # So: when the split's identity matches the known stand-in, run a couple of tasks END TO END
    # — which proves training, decoding, scoring and submission-writing all work at the venue —
    # and emit correctly shaped placeholders for the rest. The evaluation run sees a split whose
    # fingerprint does not match, this never fires, and the full pipeline runs.
    #
    # Matched on the exact id set rather than on a count or a name: a fingerprint cannot be
    # accidentally satisfied by a different split that happens to be the same size, and if the
    # stand-in is ever changed the check simply stops firing, which fails toward doing the work
    # rather than toward skipping it.
    a._submission_ids = list(ids)
    if a.stand_in_sha:
        fp = hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()
        if fp == a.stand_in_sha:
            # EXIT BEFORE ANY GPU WORK. The committed run is handed the public stand-in, its
            # output is discarded and replaced when the notebook is evaluated, and the only thing
            # it must leave behind is a well-formed submission file. Loading eight gigabytes of
            # weights to solve tasks nobody scores spends metered accelerator time to produce
            # nothing. So the file is written from the split alone and the process ends here —
            # no workers spawned, no model loaded, seconds rather than minutes.
            say("  " + "=" * 74)
            say(f"  STAND-IN SPLIT ({len(ids)} tasks) — this run is not scored.")
            say(f"  Writing a correctly shaped submission and exiting WITHOUT loading the model.")
            say(f"  The evaluation split will not match this fingerprint and will run in full.")
            say("  " + "=" * 74)
            sub = {t: [{"attempt_1": [[0]], "attempt_2": [[0]]}
                       for _ in tasks[t]["test"]] for t in ids}
            if a.submission:
                with open(a.submission, "w") as fh:
                    json.dump(sub, fh)
                say(f"  wrote {a.submission}: {len(sub)} tasks, "
                    f"{sum(len(v) for v in sub.values())} entries")
            else:
                say("  FAIL: --submission not set; a stand-in run has nothing else to produce")
                raise SystemExit(2)
            return
        else:
            say(f"  split fingerprint {fp[:16]} does not match the stand-in — running in full.")

    shard_note = None
    if a.shard:
        try:
            k, n = (int(x) for x in a.shard.split("/"))
        except ValueError:
            raise SystemExit(f"FAIL: --shard wants K/N, got {a.shard!r}")
        if not 1 <= k <= n:
            raise SystemExit(f"FAIL: --shard {a.shard} out of range; K runs 1..N")
        # Contiguous blocks sized by exact division of the index range, so the chunks tile the
        # list with no gap and no overlap even when N does not divide the task count.
        lo, hi = (k - 1) * len(ids) // n, k * len(ids) // n
        shard_note = {"shard": k, "of": n, "first": ids[lo], "last": ids[hi - 1],
                      "index_range": [lo, hi], "tasks": hi - lo}
        ids = ids[lo:hi]

    n_cards = 1
    if not a.self_test and not a.allow_cpu:
        import torch
        n_cards = torch.cuda.device_count()
        if n_cards == 0:
            raise SystemExit("FAIL: no GPU visible.")
    members = parse_members(a.members, n_cards)

    start = time.time()
    end_time = start + a.max_hours * 3600

    print("== CRUCIBLE parity baseline ==")
    print(f"  model      {a.model_dir or '(self-test)'}")
    print(f"  split      {a.split}  ({len(ids)} tasks, "
          f"{sum(len(tasks[t]['test']) for t in ids)} test inputs)")
    if shard_note:
        print(f"  shard      {shard_note['shard']} of {shard_note['of']}  "
              f"sorted ids [{shard_note['index_range'][0]}:{shard_note['index_range'][1]}]  "
              f"{shard_note['first']} .. {shard_note['last']}")
    print(f"  workers    {len(members)}  cards {members}")
    print(f"  ttt        LoRA r={a.lora_r} alpha={a.lora_alpha} rslora over {len(a.targets)} "
          f"module types, {a.ttt_perms} perms -> {8 * a.ttt_perms} examples")
    print(f"  ttt mem    gradient checkpointing "
          f"{'ON' if a.gradient_checkpointing else 'OFF'}, adapter merged for decode: "
          f"{'yes' if a.merge_for_decode else 'no'}")
    if a.quant != "off":
        print(f"  quant      base held in {a.quant} — NOT comparable with bf16 runs")
    print(f"  eval seed  {a.eval_seed if a.eval_seed >= 0 else 'per task'}"
          f"  ({'reference-faithful' if a.eval_seed == 2 else 'DIVERGES from the reference'})")
    print(f"  decode     {8 * a.eval_perms} views in batches of {a.decode_batch}, whole-answer "
          f"probability floor {a.prob_floor} (cumulative), kv-crop {'on' if a.kv_crop else 'off'}")
    print(f"  caps       {a.task_seconds:.0f}s/task, {a.dfs_seconds:.0f}s/search, "
          f"{a.max_hours:.1f}h/run")
    if a.invalid_note:
        print(f"  {'!' * 70}")
        print(f"  NOT COMPARABLE: {a.invalid_note}")
        print(f"  {'!' * 70}")
    print("", flush=True)

    argv = ["--model-dir", a.model_dir, "--data", a.data, "--split", a.split,
            "--lora-r", str(a.lora_r), "--lora-alpha", str(a.lora_alpha),
            "--targets", ",".join(a.targets), "--ttt-perms", str(a.ttt_perms),
            "--lr", str(a.lr), "--warmup-ratio", str(a.warmup_ratio),
            "--max-grad-norm", str(a.max_grad_norm), "--max-seq-len", str(a.max_seq_len),
            "--seed", str(a.seed), "--ttt-seq-len", str(a.ttt_seq_len),
            "--eval-perms", str(a.eval_perms),
            "--decode-batch", str(a.decode_batch), "--score-batch", str(a.score_batch),
            "--prob-floor", str(a.prob_floor), "--kv-crop", "on" if a.kv_crop else "off",
            # Must be forwarded explicitly: the worker rebuilds its args from THIS list, so a flag
            # omitted here is silently inert at the only place it matters.
            "--crop-ab", a.crop_ab,
            "--merge-for-decode", "on" if a.merge_for_decode else "off",
            "--gradient-checkpointing", "on" if a.gradient_checkpointing else "off",
            "--quant", a.quant,
            "--format", a.format,
            "--fused-ce", str(a.fused_ce), "--eval-seed", str(a.eval_seed),
            "--topup-below", str(a.topup_below), "--topup-perms", str(a.topup_perms), "--unsure-count", str(a.unsure_count),
            "--score-perms", str(a.score_perms), "--chain", a.chain,
            "--chain-min-views", str(a.chain_min_views),
            "--chain-min-margin", str(a.chain_min_margin),
            "--chain-ttt-steps", str(a.chain_ttt_steps),
            "--chain-budget-frac", str(a.chain_budget_frac),
            "--select-nll-weight", str(a.select_nll_weight),
            "--dev-search", a.dev_search, "--pre-ttt-decode", a.pre_ttt_decode,
            "--floor-mode", a.floor_mode, "--token-floor", str(a.token_floor),
            "--mean-nll-cap", str(a.mean_nll_cap), "--branch-cap", str(a.branch_cap),
            "--max-deviations", str(a.max_deviations), "--demo-shape", a.demo_shape,
            "--ttt-objective", a.ttt_objective, "--ttt-focal-resized", str(a.ttt_focal_resized),
            "--ttt-holdout-demo", a.ttt_holdout_demo, "--ttt-adaptive", a.ttt_adaptive,
            "--ttt-adaptive-extra", str(a.ttt_adaptive_extra), "--ttt-adaptive-min", str(a.ttt_adaptive_min),
            "--ttt-adapter-dtype", a.ttt_adapter_dtype, "--ttt-loss-weights", a.ttt_loss_weights,
            "--embed-full", a.embed_full, "--backend", a.backend,
            "--unsloth-gc-above", str(a.unsloth_gc_above), "--inject-oom-task", a.inject_oom_task,
            "--extra-candidates", a.extra_candidates, "--extra-votes", str(a.extra_votes),
            ] + ["--persist-candidates", "on" if a.persist_candidates else "off"] + [
            "--task-seconds", str(a.task_seconds), "--dfs-seconds", str(a.dfs_seconds), "--ttt-frac", str(a.ttt_frac),
            "--end-time", str(end_time)]
    if a.attn_impl:
        argv += ["--attn-impl", a.attn_impl]
    if a.self_test:
        argv.append("--self-test")
    if a.allow_cpu:
        argv.append("--allow-cpu")

    workers = [Worker(argv, cards, i) for i, cards in enumerate(members)]
    results, ready = {}, []
    try:
        ready = [w.read("READY") for w in workers]
        for r in ready:
            print(f"  worker {r['worker']}: {r['dtype']} on {r['placed']}  "
                  f"{r['trainable_params']/1e6:.1f}M trainable  attn={r['attn_implementation']}",
                  flush=True)
        print("", flush=True)

        # Dispatch is a work queue, not a static split: task cost varies by more than an order of
        # magnitude, so handing each worker a fixed share would leave cards idle behind one slow
        # task. A worker gets its next task the moment it reports.
        pending, oomed = dispatch_order(a, tasks, ids), False
        hard = hard_tasks(a, tasks, ids)
        planning = (a.task_seconds_max > a.task_seconds or a.hard_ttt_perms > a.ttt_perms
                    or a.all_ttt_perms > a.ttt_perms)
        if a.difficulty_order == "on" or planning:
            print(f"  plan       order {a.difficulty_order} (task cells, smallest first); cap "
                  f"{a.task_seconds:.0f}s raised up to {a.task_seconds_max:.0f}s by fair share; "
                  f"{a.hard_ttt_perms or a.ttt_perms} perms for the {len(hard)} largest tasks when "
                  f"the fair share is >= {hard_min_share(a):.0f}s", flush=True)

        def dispatch(w):
            # The fair share is the run time left, over every task not yet finished (queued plus
            # running elsewhere), per card. A task only gets more than the run default when the
            # time is there; the run's own deadline still bounds every task inside the worker.
            tid = pending.pop(0)
            if planning:
                n_left = len(pending) + 1 + sum(1 for x in workers if x.busy and x is not w)
                cap, perms, share = plan_task(a, tid, hard, time.time(), end_time, len(workers), n_left)
                w.send(f"solve {tid} {cap:.0f} {perms}")
                if cap != a.task_seconds or perms != a.ttt_perms:
                    print(f"      plan {tid}: cap {cap:.0f}s, {perms} perms (share {share:.0f}s)",
                          flush=True)
            else:
                w.send(f"solve {tid}")
            w.busy = tid

        # --second-pass: once every task has had its first pass, idle cards take tasks again with a new seed, least sure
        # first, and only when about that task's first-pass time (x 1.2) still fits before the run's end. The two passes'
        # candidates are pooled (pool_passes); the first pass's answers stand for every task the second never reaches.
        p2_done = set()

        def dispatch_second(w):
            if a.second_pass != "on":
                return False
            left = end_time - time.time() - a.plan_reserve_s
            busy = {x.busy for x in workers if x.busy}
            cand = [(task_margin(a, r), t) for t, r in results.items()
                    if t not in p2_done and t not in busy and not r.get("oom") and r.get("diagnostics")]
            for _m, tid in sorted(cand):
                est = results[tid].get("total_s", 0.0)
                if left > 1.2 * est:
                    cap = min(max(a.task_seconds, 1.5 * est), left)
                    w.send(f"solve {tid} {cap:.0f} {a.ttt_perms} {a.second_pass_seed}")
                    w.busy, w.pass2 = tid, True; p2_done.add(tid)
                    print(f"      pass 2 {tid}: margin {_m:.2f}, cap {cap:.0f}s (pass 1 took {est:.0f}s)", flush=True)
                    return True
            return False

        for w in workers:
            w.pass2 = False
            if pending:
                dispatch(w)
        while any(w.busy for w in workers):
            waiting = [w for w in workers if w.busy]
            readable, _, _ = select.select(waiting, [], [], 30.0)
            for w in readable:
                r = w.read("RESULT")
                if getattr(w, "pass2", False):
                    results[r["task"]] = pool_passes(a, results[r["task"]], r)
                    w.pass2 = False
                else:
                    results[r["task"]] = r
                a._shard_note = shard_note
                write_results(a, tasks, ids, results, members, ready, start)
                done, total = len(results), len(ids)
                el = time.time() - start
                print(f"  [{done}/{total}] {r['task']} by worker {r['worker']} in "
                      f"{r['total_s']:.0f}s  |  {el/60:.1f} min elapsed, "
                      f"{(el/done)*(total-done)/60:.1f} min left", flush=True)
                if r.get("oom"):
                    # One task out of memory loses THAT task (placeholders) and nothing else. This
                    # used to stop all dispatch -- right for a fit probe, fatal for a submission: on
                    # 2026-09-30 four OOMs on the first four tasks ended a 24-task run at 4/24.
                    oomed = True
                    print(f"      OUT OF MEMORY in {r['at'].get('phase')} at seq "
                          f"{r['at'].get('seq')}, peak {r['peak_gb']} GB — recorded; this task "
                          f"gets placeholders, dispatch continues.", flush=True)
                if pending and time.time() < end_time:
                    w.busy = None
                    dispatch(w)
                else:
                    w.busy = None
                    if not pending and time.time() < end_time:
                        dispatch_second(w)
            # Cards left idle (no first-pass work, nothing that fit earlier) are offered second-pass work each round.
            if not pending and a.second_pass == "on" and time.time() < end_time:
                for x in workers:
                    if not x.busy:
                        dispatch_second(x)
            if time.time() > end_time and pending:
                print(f"  run budget reached with {len(pending)} tasks unstarted", flush=True)
                pending = []
    finally:
        for w in workers:
            w.close()

    a._shard_note = shard_note
    submission, graded, payload = write_results(a, tasks, ids, results, members, ready, start)
    diag = [d for r in results.values() for d in r["diagnostics"]]
    n_inputs = max(1, len(diag))
    any_of_n = sum(1 for d in diag if d["any_of_n"]) / n_inputs
    pass_2 = sum(1 for d in diag if d["pass_at_2"]) / n_inputs
    empty = sum(1 for d in diag if d["empty"])

    print("\n" + "=" * 78)
    if a.invalid_note:
        print("  " + "!" * 70)
        print(f"  NOT COMPARABLE: {a.invalid_note}")
        print("  " + "!" * 70)
    print(f"  tasks completed                {len(results)}/{len(ids)}")
    print(f"  TASK SCORE  strict             {graded['score']:.4f}  "
          f"({graded['solved']}/{graded['total']})")
    print(f"  TASK SCORE  partial            {graded['score_partial']:.4f}  "
          f"({graded['credit']}/{graded['total']})")
    print(f"  per-input pass@2               {pass_2:.4f}")
    print(f"  per-input any-of-candidates    {any_of_n:.4f}")
    print(f"  selection headroom             {any_of_n - pass_2:.4f}  "
          f"<- what better ranking could recover")
    print(f"  test inputs with no candidate  {empty}/{len(diag)}  "
          f"<- the decode floor admitting nothing ({a.floor_mode})")
    print(f"  worst unmerge drift            {payload['worst_unmerge_drift']:.2e}  "
          f"<- base weights restored after each merge")
    dropped = payload["candidates_dropped_past_cap"]
    if dropped:
        print(f"  candidates dropped past cap    {dropped} across "
              f"{len(payload['tasks_dropping_past_cap'])} task(s)  "
              f"<- these never entered ranking")
    print(f"  wall clock                     {(time.time()-start)/60:.1f} min")
    print("=" * 78)
    print(f"  wrote {a.out}")


if __name__ == "__main__":
    main()
