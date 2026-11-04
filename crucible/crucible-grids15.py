#!/usr/bin/env python
# crucible-grids15.py — the grids_v15 serialization the adopted S2 base was trained on.
#
# SEPARATE FROM crucible-encode.py ON PURPOSE, and the two must never be swapped. The adopted
# base (sorokin/qwen3_4b_grids15_sft139) carries a SIXTEEN-token vocabulary: the digits 0-9, a
# newline, the two words "user" and "assistant", and three specials. Nothing else is
# representable. crucible-encode.py's prompt — an English instruction, "Example N input:"
# headings, <grid> delimiters — maps almost entirely to the unknown token against this model, so
# a run using it would measure a format mismatch and report it as a capability number.
#
# What that vocabulary forces, and what it therefore settles:
#   * A grid is dense digits, one row per line. There is no space token, so the spaced style is
#     unrepresentable and the rowlen style's separator does not exist. The encoding-style
#     question is closed on this base, not open.
#   * There is no delimiter to close. A completed answer is marked by <|im_end|> and nothing
#     else, so truncation is detected by its ABSENCE — the mechanism crucible-encode.py gets
#     from its closing tag.
#   * The task specification is carried entirely by the demonstration pairs, laid out as a
#     multi-turn chat: each pair is one user turn (input grid) and one assistant turn (output
#     grid). There is no instruction because there is no way to write one.
#
# Format and vocabulary were read from the model's own config/tokenizer files and from the
# published NVARC training and submission code. That code is unlicensed, so it is a source of
# FACTS here and nothing else: everything below is written against the observed format.
#
# Stdlib only — this runs inside the offline competition notebook as well as at home.
import json

# --- vocabulary -------------------------------------------------------------------------------
# Hard-coded because it is a property of the model, not a preference, and because a harness that
# silently accepted a different tokenizer would produce a plausible-looking wrong number.
# assert_tokenizer() below checks the loaded tokenizer against it and fails loudly.
VOCAB = {
    "0": 0, "1": 1, "2": 2, "3": 3, "4": 4,
    "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "\n": 10, "user": 11, "assistant": 12,
    "<|endoftext|>": 13, "<|im_start|>": 14, "<|im_end|>": 15,
}

DIGIT_IDS = tuple(range(10))
NEWLINE_ID = 10
USER_ID = 11
ASSISTANT_ID = 12
PAD_ID = 13          # <|endoftext|>; declared unk_token, but the WordLevel load RAISES on unknown text
IM_START_ID = 14
IM_END_ID = 15

# The only tokens a grid answer can legally contain. The decoder expands nothing else, which is
# what makes an exhaustive search over answers affordable at all: eleven continuations per
# position instead of a full vocabulary.
ARC_TOKENS = DIGIT_IDS + (NEWLINE_ID, IM_END_ID)

IM_START = "<|im_start|>"
IM_END = "<|im_end|>"

MAX_SIDE = 30        # ARC grids are at most 30x30; anything larger is a parse failure


# THE TOKENIZER, carried in the code rather than read from a model directory.
#
# 2026-09-29 (Kaggle logs): AutoTokenizer on this model
# builds a BPE tokenizer from vocab.json with no merges. It cannot form the words "user" and
# "assistant", has no unk, and DROPS them: every turn lost its two role tokens (ids 11/12) in every
# TTT example, decode prompt and score of every run and every submission until this date. The
# base's own tokenizer.json is WordLevel and keeps them. Merged models saved through AutoTokenizer
# carry the broken BPE file, so the model directory cannot be trusted either: the correct
# tokenizer is embedded here, byte-for-byte the base's tokenizer.json, and built from this string.
BASE_TOKENIZER_JSON = '{\n  "version": "1.0",\n  "truncation": null,\n  "padding": null,\n  "added_tokens": [\n    {\n      "id": 13,\n      "content": "<|endoftext|>",\n      "single_word": false,\n      "lstrip": false,\n      "rstrip": false,\n      "normalized": false,\n      "special": true\n    },\n    {\n      "id": 14,\n      "content": "<|im_start|>",\n      "single_word": false,\n      "lstrip": false,\n      "rstrip": false,\n      "normalized": false,\n      "special": true\n    },\n    {\n      "id": 15,\n      "content": "<|im_end|>",\n      "single_word": false,\n      "lstrip": false,\n      "rstrip": false,\n      "normalized": false,\n      "special": true\n    }\n  ],\n  "normalizer": {\n    "type": "NFC"\n  },\n  "pre_tokenizer": {\n    "type": "Sequence",\n    "pretokenizers": [\n      {\n        "type": "Split",\n        "pattern": {\n          "Regex": "(?i:\'s|\'t|\'re|\'ve|\'m|\'ll|\'d)|[^\\\\r\\\\n\\\\p{L}\\\\p{N}]?\\\\p{L}+|\\\\p{N}| ?[^\\\\s\\\\p{L}\\\\p{N}]+[\\\\r\\\\n]*|\\\\s*[\\\\r\\\\n]+|\\\\s+(?!\\\\S)|\\\\s+"\n        },\n        "behavior": "Isolated",\n        "invert": false\n      },\n      {\n        "type": "ByteLevel",\n        "add_prefix_space": false,\n        "trim_offsets": false,\n        "use_regex": false\n      }\n    ]\n  },\n  "post_processor": {\n    "type": "ByteLevel",\n    "add_prefix_space": false,\n    "trim_offsets": false,\n    "use_regex": false\n  },\n  "decoder": {\n    "type": "ByteLevel",\n    "add_prefix_space": false,\n    "trim_offsets": false,\n    "use_regex": false\n  },\n  "model": {\n    "type": "WordLevel",\n    "vocab": {\n      "0": 0,\n      "1": 1,\n      "2": 2,\n      "3": 3,\n      "4": 4,\n      "5": 5,\n      "6": 6,\n      "7": 7,\n      "8": 8,\n      "9": 9,\n      "Ċ": 10,\n      "user": 11,\n      "assistant": 12\n    },\n    "unk_token": "<|endoftext|>"\n  }\n}'


def load_tokenizer():
    """The grids_v15 tokenizer, built from BASE_TOKENIZER_JSON and checked by assert_tokenizer."""
    from tokenizers import Tokenizer
    from transformers import PreTrainedTokenizerFast
    tok = PreTrainedTokenizerFast(tokenizer_object=Tokenizer.from_str(BASE_TOKENIZER_JSON),
                                  pad_token="<|endoftext|>", eos_token="<|im_end|>")
    assert_tokenizer(tok)
    return tok


def assert_tokenizer(tok):
    """Fail before any GPU time if the tokenizer is not the 16-token one this format assumes.

    A general-purpose tokenizer would merge digit runs into single tokens, which breaks three
    things at once: one-token-per-cell budgeting, the decoder's token set, and the meaning of the
    cumulative-probability cutoff. None of those failures is visible in the output — the run
    completes and reports a number.
    """
    # len(), not .vocab_size: the three specials are ADDED tokens, so vocab_size reports 13 while
    # the embedding matrix the model was trained with is 16 rows.
    size = len(tok)
    if size != len(VOCAB):
        raise SystemExit(f"FAIL: tokenizer holds {size} tokens, expected {len(VOCAB)} "
                         f"(vocab_size {getattr(tok, 'vocab_size', '?')} plus added specials). "
                         f"This is not the grids_v15 tokenizer; the format in this module does "
                         f"not apply to it.")
    for text, expected in VOCAB.items():
        got = tok.convert_tokens_to_ids(text if text != "\n" else "Ċ")
        if got != expected:
            raise SystemExit(f"FAIL: tokenizer maps {text!r} to id {got}, expected {expected}.")
    # A grid row must be one token per cell. If it is not, every length estimate in the harness
    # is wrong by an unknown factor.
    ids = tok.encode("0123456789")
    if ids != list(DIGIT_IDS):
        raise SystemExit(f"FAIL: '0123456789' encodes to {ids}, expected one token per digit. "
                         f"Digit runs are being merged.")
    # THE ROLE TOKENS. convert_tokens_to_ids("user") == 11 passed on the broken BPE load while
    # encode("user") returned []; only encoding a real prompt shows it. Round trip, role presence,
    # and no PAD -- all three, on a full prompt. (Unknown text does NOT fall back to PAD: encode()
    # raises "WordLevel error: Missing [UNK] token". Our format never produces such text.)
    probe = build_input([{"input": [[0, 1], [2, 3]], "output": [[4, 5]]}], [[6, 7]])
    pids = tok.encode(probe)
    if tok.decode(pids) != probe:
        raise SystemExit(f"FAIL: tokenizer does not round-trip a prompt: {tok.decode(pids)!r}")
    if pids.count(VOCAB["user"]) != 2 or pids.count(VOCAB["assistant"]) != 2:
        raise SystemExit(f"FAIL: role tokens missing from an encoded prompt {pids} -- the "
                         f"'user'/'assistant' words are being dropped (the pre-2026-09-29 bug).")
    if PAD_ID in pids:
        raise SystemExit(f"FAIL: an encoded prompt contains PAD {PAD_ID}: {pids}")


# --- serialization ----------------------------------------------------------------------------

def grid_to_text(grid):
    """Dense digits, one row per line, no trailing newline.

    A malformed cell is named here rather than left to int(). It surfaced as a bare TypeError
    eleven frames below the caller, identifying neither the cell nor which of the two callers --
    training encoding a corpus block, or inference encoding a task -- and cost a run at step 8817.
    text_to_grid returns None for malformed input because a model's output can legitimately be
    garbage; a grid arriving HERE malformed is a defect upstream, so it raises instead.
    """
    rows = []
    for r, row in enumerate(grid):
        for c, v in enumerate(row):
            if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 9:
                raise ValueError(f"grid_to_text: cell [{r}][{c}] is {v!r}, "
                                 f"not an integer 0-9")
        rows.append("".join(str(v) for v in row))
    return "\n".join(rows)


def text_to_grid(text):
    """Parse a serialized grid back, or None when it is not a well-formed grid.

    Returning None rather than a repaired grid is load-bearing: a malformed completion has to
    stay classifiable as malformed, or it becomes indistinguishable from a confident wrong
    answer. Non-digit characters are dropped rather than rejected because the model can only emit
    digits and newlines in the first place — the failure this guards is raggedness, which is what
    a truncated completion produces.
    """
    if text is None:
        return None
    rows = []
    for line in text.strip().split("\n"):
        row = [int(ch) for ch in line if ch.isdigit()]
        if row:
            rows.append(row)
    if not rows or len(rows) > MAX_SIDE:
        return None
    width = len(rows[0])
    if width == 0 or width > MAX_SIDE:
        return None
    if any(len(r) != width for r in rows):
        return None
    return rows


def valid_grid(grid):
    """A grid the competition would accept: 1..30 on each side, colours 0-9 only."""
    if not grid or len(grid) > MAX_SIDE:
        return False
    width = len(grid[0])
    if not 1 <= width <= MAX_SIDE:
        return False
    return all(len(r) == width and all(0 <= int(c) <= 9 for c in r) for r in grid)


# --- prompt construction ----------------------------------------------------------------------
# The chat turns are concatenated with NO separator between them. That is the template the base
# was trained under; inserting the newline a conventional ChatML template would add puts a token
# in a position the model has never seen there.

def _turn(role_id, content):
    role = "user" if role_id == USER_ID else "assistant"
    return f"{IM_START}{role}\n{content}{IM_END}"


def format_demos(pairs):
    """The demonstration pairs, as alternating user/assistant turns."""
    return "".join(_turn(USER_ID, grid_to_text(p["input"]))
                   + _turn(ASSISTANT_ID, grid_to_text(p["output"])) for p in pairs)


def build_input(pairs, test_input):
    """Everything the model reads before it generates: demos, the test input, and the opening of
    the assistant turn it has to complete."""
    return (format_demos(pairs) + _turn(USER_ID, grid_to_text(test_input))
            + f"{IM_START}assistant\n")


def build_text(pairs, test_input, test_output):
    """A complete example — prompt plus answer. Used for test-time training and for scoring a
    candidate answer under an augmentation."""
    return build_input(pairs, test_input) + grid_to_text(test_output) + IM_END


def reply_text(grid):
    """The answer half alone, which is the span a score is taken over."""
    return grid_to_text(grid) + IM_END


def max_answer_tokens():
    """Token budget for the largest legal answer: 30x30 digits, 29 newlines, the end marker, and
    one spare so a completion that wants exactly the maximum is not cut off by the bound."""
    return MAX_SIDE * MAX_SIDE + (MAX_SIDE - 1) + 1 + 1


# --- augmentation -----------------------------------------------------------------------------
# A view is one dihedral symmetry plus one colour permutation, applied to every grid in the task.
# The result is a different surface form of the same rule, which is what both test-time training
# and multi-view scoring consume.
#
# The colour permutation covers all ten colours INCLUDING 0. crucible-encode.py deliberately
# holds 0 fixed on the grounds that background is structural; this base was trained with 0
# permuted like any other colour, so holding it fixed here would present views the model was
# never trained on. The two modules differ because the models differ.

def _rot90(grid):
    """One quarter turn counter-clockwise, matching numpy's rot90 so the view numbering below
    lines up with the orientation the base was trained under."""
    return [list(r) for r in zip(*[row for row in grid])][::-1]


def _transpose(grid):
    return [list(r) for r in zip(*grid)]


def dihedral(grid, tid):
    """One of the eight symmetries of the square, tid 0-7."""
    g = grid
    if tid >= 4:
        g = _transpose(g)
    for _ in range(tid % 4):
        g = _rot90(g)
    return g


def undihedral(grid, tid):
    """Inverse of dihedral() for the same tid."""
    g = grid
    for _ in range((4 - tid % 4) % 4):
        g = _rot90(g)
    if tid >= 4:
        g = _transpose(g)
    return g


def recolor(grid, perm):
    """Apply a colour permutation. perm[c] is the colour c becomes."""
    return [[perm[int(c)] for c in row] for row in grid]


def unrecolor(grid, perm):
    inverse = [0] * 10
    for src, dst in enumerate(perm):
        inverse[dst] = src
    return recolor(grid, inverse)


def apply_view(grid, view):
    tid, perm = view
    return recolor(dihedral(grid, tid), perm)


def invert_view(grid, view):
    tid, perm = view
    return undihedral(unrecolor(grid, perm), tid)


def view_task(pairs, test_input, view):
    """Apply a view to a whole task, demos and test input alike."""
    return ([{"input": apply_view(p["input"], view), "output": apply_view(p["output"], view)}
             for p in pairs],
            apply_view(test_input, view))


# CRUCIBLE_VIEWS_ZERO_FIXED=1: every view keeps colour 0 at 0 (test of matching the FFT packer's views; 2026-10-21).
_ZERO_FIXED = __import__("os").environ.get("CRUCIBLE_VIEWS_ZERO_FIXED") == "1"
def make_views(rng, n_perms):
    """The eight dihedral symmetries crossed with n_perms colour permutations.

    The identity permutation is not privileged: every view carries a drawn permutation, because
    the base saw permuted colours throughout training and an unpermuted view is not the
    'canonical' one from its point of view.
    """
    # A FRESH permutation for EVERY view, as the reference does (arc_loader.augment calls
    # permute_rnd_all_ per key). Until 2026-09-29 one permutation was shared by all 8 dihedral views
    # of a draw: TTT saw 16 distinct colourings instead of 128, decode 2 instead of 16, and the 8
    # scoring views ONE -- so the selection signal was 8 correlated readings of one colouring.
    views = []
    for _ in range(n_perms):
        for tid in range(8):
            perm = list(range(10))
            rng.shuffle(perm)
            if _ZERO_FIXED:
                # Background held at 0, as the FFT packer trains (crucible-fft-pack.py L119-120). Off by default.
                perm = [0] + [p for p in perm if p != 0]
            views.append((tid, tuple(perm)))
    return views


# --- length control ---------------------------------------------------------------------------

def fit_demos(pairs, test_input, test_output, budget, count_tokens):
    """Drop demonstration pairs, oldest first, until the example fits the context budget.

    Dropping rather than truncating is the only option that keeps the example well-formed: a
    truncated demo pair teaches a transformation that does not hold. Returns the pairs that fit,
    possibly empty.

    test_input None measures the demonstrations alone, which is the training-side example; a
    test_input with no test_output measures a prompt with nothing appended, which is the
    inference-side one.
    """
    kept = list(pairs)
    while kept:
        if test_input is None:
            text = format_demos(kept)
        elif test_output is None:
            text = build_input(kept, test_input)
        else:
            text = build_text(kept, test_input, test_output)
        if count_tokens(text) <= budget:
            return kept
        kept = kept[1:]
    return kept


def encode_ttt_example(tok, demos):
    """Token ids plus labels for one training example, loss on the output grids only.

    Built segment by segment rather than by locating role markers in a finished sequence: the
    spans are known exactly at construction time, and a scan for marker ids silently mislabels
    the moment a grid happens to contain the same value.
    """
    ids, labels = [], []
    for pair in demos:
        prompt = (f"{IM_START}user\n{grid_to_text(pair['input'])}{IM_END}"
                  f"{IM_START}assistant\n")
        answer = reply_text(pair["output"])
        p_ids = tok.encode(prompt)
        a_ids = tok.encode(answer)
        ids.extend(p_ids + a_ids)
        labels.extend([-100] * len(p_ids) + a_ids)
    return ids, labels


def swaps_axes(tid):
    """Whether this dihedral element transposes the grid's dimensions.

    A transpose swaps height and width; so does an odd number of quarter turns. Both together
    cancel. Two views agreeing on this predicate therefore produce grids of identical shape.
    """
    return (tid >= 4) != (tid % 4 in (1, 3))


def batch_views(views, size):
    """Group views into batches whose members share a grid ORIENTATION.

    This is the reference's batching, and the reason for it is not cosmetic. A batch of views is
    decoded through one shared KV cache with a single position index, and the reference can build
    it with a bare tensor and no attention mask because every row is the same length. That holds
    only when the grids have the same shape.

    Batching views in arbitrary order mixes transposed with untransposed grids. Those differ in
    row count, so they differ in row-separator count, so the prompts differ in length and the
    batch has to be padded — after which the shared position index is wrong for the padded rows
    and, with no mask, they attend over their own padding. Measured before this fix: 68% of decode
    batches on the parity run were padded.

    Grouping by orientation removes the padding rather than compensating for it. Colour
    permutation is irrelevant here: it maps digits to digits and cannot change a token count.
    """
    groups = {}
    for v in views:
        groups.setdefault(swaps_axes(v[0]), []).append(v)
    out = []
    for g in groups.values():
        for i in range(0, len(g), size):
            out.append(g[i:i + size])
    return out


if __name__ == "__main__":
    # Self-check: no model, no GPU. Proves the serialization round-trips and that every view is
    # invertible, which is what the decoder relies on when it maps a candidate back to canonical
    # orientation before candidates from different views are pooled.
    import random

    g = [[1, 2, 3], [4, 5, 6]]
    assert grid_to_text(g) == "123\n456"
    assert text_to_grid("123\n456") == g
    assert text_to_grid("123\n45") is None, "ragged rows must not parse"
    assert text_to_grid("") is None
    assert text_to_grid("\n".join("0" * 31 for _ in range(2))) is None, "over-wide must not parse"
    assert text_to_grid("\n".join("0" for _ in range(31))) is None, "over-tall must not parse"
    assert valid_grid(g) and not valid_grid([[1, 2], [3]])

    # Every dihedral symmetry must invert, on a non-square grid so a transpose that is silently
    # dropped cannot pass.
    for tid in range(8):
        assert undihedral(dihedral(g, tid), tid) == g, f"dihedral {tid} does not invert"
    # The eight must be distinct as maps, or the view set is smaller than it claims to be.
    square = [[1, 2], [3, 4]]
    assert len({json.dumps(dihedral(square, t)) for t in range(8)}) == 8, "views collide"

    rng = random.Random(0)
    views = make_views(rng, 2)
    assert len(views) == 16 and len(set(views)) == 16
    for v in views:
        assert invert_view(apply_view(g, v), v) == g, f"view {v} does not invert"
        pairs_v, test_v = view_task([{"input": g, "output": square}], square, v)
        assert invert_view(pairs_v[0]["input"], v) == g
        assert invert_view(test_v, v) == square

    # A colour permutation that moves 0 must actually move it — this is the documented difference
    # from crucible-encode.py and a silent revert would be invisible in any downstream number.
    assert recolor([[0]], [7, 1, 2, 3, 4, 5, 6, 0, 8, 9]) == [[7]]
    assert unrecolor([[7]], [7, 1, 2, 3, 4, 5, 6, 0, 8, 9]) == [[0]]

    demo = [{"input": [[1]], "output": [[2]]}]
    text = build_text(demo, [[3]], [[4]])
    assert text == ("<|im_start|>user\n1<|im_end|><|im_start|>assistant\n2<|im_end|>"
                    "<|im_start|>user\n3<|im_end|><|im_start|>assistant\n4<|im_end|>"), text
    assert build_input(demo, [[3]]) + reply_text([[4]]) == text
    assert max_answer_tokens() == 931

    # Demo dropping, counted in characters so the check needs no tokenizer.
    long_demos = [{"input": [[i]], "output": [[i]]} for i in range(5)]
    fitted = fit_demos(long_demos, [[9]], [[9]], 200, len)
    assert 0 <= len(fitted) < 5 and fitted == long_demos[len(long_demos) - len(fitted):]

    # Orientation grouping must make every batch shape-homogeneous, which is what removes the
    # padding the decoder was silently mishandling.
    vs = make_views(random.Random(1), 2)
    for b in batch_views(vs, 4):
        assert len({swaps_axes(t) for t, _ in b}) == 1, "a batch mixes orientations"
    assert sorted(v for b in batch_views(vs, 4) for v in b) == sorted(vs), \
        "batching dropped or duplicated a view"
    assert {swaps_axes(t) for t in range(8)} == {True, False}
    assert [t for t in range(8) if not swaps_axes(t)] == [0, 2, 5, 7]

    print("-- self-check passed --")
    print(json.dumps({"vocab": len(VOCAB), "arc_tokens": len(ARC_TOKENS),
                      "max_answer_tokens": max_answer_tokens()}))
