#!/usr/bin/env python
# crucible-kaggle-build.py — generate the Kaggle profiling kernel from crucible-profile.py.
#
# GENERATED, NOT HAND-COPIED. The kernel has to be a single self-contained file, and a
# hand-maintained copy of the profiler would drift from the one that runs locally — at which
# point the two venues stop being comparable, which is the only reason the table exists.
#
# MODELS ARE ATTACHED, NEVER FETCHED. Each entry is a /kaggle/input mount created by
# model_sources in the metadata. The harness is incapable of downloading — see crucible-profile.py
# — so the kernel runs with internet disabled, which is the shape a competition submission runs
# in. Attaching also costs no session time and no disk, so the ~57 GB of candidates is not a
# constraint the way a per-run download would be.
import argparse
import json
import os
import re
import shlex

HERE = os.path.dirname(os.path.abspath(__file__))

DRIVER_HEAD = '''

# ============================== Kaggle driver ==============================
# Each entry is a mounted Kaggle input directory. Nothing is downloaded and nothing is deleted:
# inputs are read-only and shared.
import os, sys as _sys
import torch


def _name_for(mid):
    """A readable label. basename() alone yields the version directory — the mount path
    /kaggle/input/qwen-3/transformers/4b/1 would be labelled "1"."""
    parts = [p for p in mid.strip("/").split("/") if p]
    if "input" in parts:
        parts = parts[parts.index("input") + 1:]
        if parts and parts[0] == "models":
            parts = parts[2:]           # drop "models" and the owner slug
        parts = [p for p in parts if p.lower() not in ("transformers", "pytorch", "keras")]
        parts = [p for p in parts if not p.isdigit()] or parts
        return "-".join(parts)
    return parts[-1] if parts else mid


def _resolve_mount(path):
    """Return the real mount for path, matching segments case-insensitively.

    Kaggle canonicalises the framework segment's casing: a model attached as
    qwen-lm/qwen-3/transformers/4b/1 mounts under .../qwen-3/Transformers/4b/1. A match is
    accepted only when it is unambiguous; anything else returns unchanged, so the caller fails
    on the path that was asked for.
    """
    if os.path.isdir(path):
        return path
    cur = "/"
    for seg in [p for p in path.strip("/").split("/") if p]:
        nxt = os.path.join(cur, seg)
        if os.path.isdir(nxt):
            cur = nxt
            continue
        try:
            hits = [e for e in os.listdir(cur) if e.lower() == seg.lower()]
        except OSError:
            return path
        if len(hits) != 1:
            return path
        cur = os.path.join(cur, hits[0])
    return cur


def preflight(model_paths, expect_gpus, expect_sm=None):
    """Fail in seconds, before any GPU time, rather than after.

    NOTHING HERE INSTALLS. The kernel runs with internet disabled, so a dependency is either in
    the base image or attached as wheels; either way it is present at start or the run has no
    business continuing. The alternative — catching ImportError and skipping the affected phase —
    produces a notebook that completes, looks healthy, and emits a table with a silently empty
    column. On a submission that is a scored run of garbage.
    """
    problems = []
    versions = {}
    for mod in ("torch", "transformers", "peft"):
        try:
            m = __import__(mod)
            versions[mod] = getattr(m, "__version__", "?")
        except ImportError as e:
            versions[mod] = "ABSENT"
            problems.append(f"missing dependency {mod!r} ({e}) — not present in this "
                            f"environment. This harness does not install anything: {mod!r} must "
                            f"already be importable before it runs, whether from the base image "
                            f"or from wheels put in place by a separate setup step.")

    # flash-attn presence, recorded and never required. Measured on Ampere: torch's own sdpa
    # flash backend accepts this model's 32-query/8-KV head shape when enable_gqa is set, so FA2
    # is not load-bearing — but whether the image ships it is a standing open question and this
    # answers it for free on a run that was happening anyway.
    try:
        import flash_attn as _fa
        versions["flash_attn"] = getattr(_fa, "__version__", "?")
    except ImportError:
        versions["flash_attn"] = "absent (not required)"

    # torchao is OPTIONAL for peft in general, so its absence is not a failure — but when it IS
    # present at an incompatible version peft's LoRA path refuses to build. Report it, judge it
    # by the smoke below rather than by presence.
    try:
        import torchao as _tao
        versions["torchao"] = getattr(_tao, "__version__", "?")
    except ImportError:
        versions["torchao"] = "absent (optional)"

    # Importing peft is not enough. It pulls torchao in LAZILY when the LoRA path is built, so a
    # version incompatibility surfaces only once a model is actually wrapped — after the weights
    # have loaded and generation has run. Exercise the real path here, on a toy module, so the
    # failure costs milliseconds instead of a session.
    if "peft" in versions and versions["peft"] != "ABSENT" and "torch" in versions:
        try:
            import torch as _t
            from peft import LoraConfig, get_peft_model
            toy = _t.nn.Sequential(_t.nn.Linear(8, 8))
            toy.config = None
            wrapped = get_peft_model(
                _t.nn.ModuleDict({"0": toy}) if False else toy,
                LoraConfig(r=2, lora_alpha=4, target_modules=["0"], task_type=None))
            wrapped(_t.zeros(1, 8)).sum().backward()
        except ImportError as e:
            problems.append(f"peft LoRA path unusable: {e} — peft imports but its dependencies "
                            f"do not satisfy it. A corrected version must already be in place "
                            f"before this harness runs; it installs nothing.")
        except Exception as e:
            problems.append(f"peft LoRA smoke failed: {type(e).__name__}: {str(e)[:120]}")
    for p in model_paths:
        if not os.path.isdir(p):
            problems.append(f"model not mounted: {p} — check model_sources in kernel-metadata")
        elif not any(f.endswith(".safetensors") for f in os.listdir(p)):
            problems.append(f"no .safetensors under {p}")

    n = 0
    caps = []
    if "torch" in versions:
        import torch
        n = torch.cuda.device_count() if torch.cuda.is_available() else 0
        if expect_gpus is not None and n != expect_gpus:
            problems.append(f"expected {expect_gpus} GPU(s), found {n} — wrong accelerator; the "
                            f"numbers would describe hardware other than the one requested")
        # An unrecognised or unavailable --accelerator is SUBSTITUTED rather than refused: a push
        # asking for NvidiaL4 is accepted and the session runs on a P100. Card count alone does
        # not catch that, so the capability is checked too.
        for i in range(n):
            pr = torch.cuda.get_device_properties(i)
            caps.append(f"{pr.major}.{pr.minor}")
            # A CUDA binary runs on any card of the same major version whose minor is at least
            # the one it was built for: an sm_86 build runs on an sm_89 L4. Exact-match would
            # reject L4 against a list of sm_70/75/80/86/90.
            built = []
            for a in torch.cuda.get_arch_list():
                # The LAST digit is the minor version and the rest is the major: sm_75 is 7.5,
                # sm_90 is 9.0, sm_120 is 12.0.
                digits = a[3:] if a.startswith("sm_") else ""
                if digits.isdigit() and len(digits) >= 2:
                    built.append((int(digits[:-1]), int(digits[-1])))
            if built and not any(mj == pr.major and mn <= pr.minor for mj, mn in built):
                # torch.cuda.is_available() is True and get_device_properties() succeeds on a
                # card this build has no kernels for; the failure arrives at the first real CUDA
                # operation instead.
                problems.append(f"gpu{i} is {pr.name} (sm_{pr.major}{pr.minor}) and this torch "
                                f"build ships {torch.cuda.get_arch_list()} — no kernel image "
                                f"for this card")
        if expect_sm is not None:
            wrong = [f"gpu{i}={c}" for i, c in enumerate(caps) if c != expect_sm]
            if wrong:
                problems.append(f"expected compute capability {expect_sm}, found {wrong} — the "
                                f"accelerator request was substituted; attention backends and "
                                f"dtype support differ by capability")

    # Host resources, recorded every run rather than measured in a session of their own. The
    # decode loops are Python-driven and any CPU-side work at test time competes with them, so
    # the core count is a design input, not trivia.
    try:
        cpus = len(os.sched_getaffinity(0))
    except AttributeError:
        cpus = os.cpu_count()
    ram_gb = None
    try:
        with open("/proc/meminfo") as _mf:
            for _line in _mf:
                if _line.startswith("MemTotal:"):
                    ram_gb = round(int(_line.split()[1]) / 1e6, 1)
                    break
    except OSError:
        pass

    print("== preflight ==")
    for k, v in versions.items():
        print(f"  {k:<14} {v}")
    print(f"  gpus           {n}" + (f"  capability {caps}" if caps else ""))
    print(f"  host           {cpus} usable vCPU"
          + (f", {ram_gb} GB RAM" if ram_gb else ""))
    for p in model_paths:
        print(f"  model          {p}  {'ok' if os.path.isdir(p) else 'MISSING'}")
    if any("not mounted" in x for x in problems):
        # A mount path that does not exist gives no clue whether the attach failed, the
        # framework segment is cased differently, or the layout nests deeper. Have the
        # session report its own layout instead of inferring it.
        print("  --- actual /kaggle/input tree ---")
        root = "/kaggle/input"
        if not os.path.isdir(root):
            print("    /kaggle/input does not exist — nothing is attached at all")
        else:
            for dirpath, dirnames, filenames in os.walk(root):
                depth = dirpath[len(root):].count(os.sep)
                if depth > 6:
                    dirnames[:] = []
                    continue
                print(f"    {dirpath}")
                if filenames:
                    shown = sorted(filenames)[:4]
                    print(f"      files: {shown}{' ...' if len(filenames) > 4 else ''}")
    if problems:
        print("\\n  PREFLIGHT FAILED:")
        for pr in problems:
            print(f"    - {pr}")
        raise SystemExit(1)
    print("  all checks passed\\n", flush=True)


'''

# The profiling driver and the layout driver share the preflight above verbatim.
DRIVER_PROFILE = '''MODELS = __MODELS__
EXPECT_GPUS = __EXPECT_GPUS__
EXPECT_SM = __EXPECT_SM__
BATCH, NEW_TOKENS = 8, 256
TTT_STEPS, TTT_SEQ, TTT_BATCH, LORA_R = 5, 1024, 2, 16
ALLOW_TTT_FAILURE = __ALLOW_TTT_FAILURE__

# Resolve before preflight, and profile the resolved path — preflight must check the path the
# run actually uses.
for _i, _m in enumerate(MODELS):
    _real = _resolve_mount(_m)
    if _real != _m:
        print(f"  mount resolved: {_m} -> {_real}", flush=True)
        MODELS[_i] = _real

preflight(MODELS, EXPECT_GPUS, EXPECT_SM)

dev = describe_devices()
print("== venue ==")
print(f"  host {dev['host']}  torch {dev['torch']}  cuda={dev['cuda_available']}")
for d in dev["devices"]:
    print(f"  gpu{d['index']}: {d['name']}  {d['total_mem_gb']} GB  sm{d['capability']}")
n_gpu = len(dev["devices"])
print(f"  visible GPUs: {n_gpu}\\n", flush=True)

rows = []
for mid in MODELS:
    name = _name_for(mid)
    print(f"################ {mid} ################", flush=True)
    if not os.path.isdir(mid):
        print(f"  NOT MOUNTED: {mid} — check model_sources in kernel-metadata.json")
        continue
    try:
        r = profile_one(mid, batch=BATCH, new_tokens=NEW_TOKENS, ttt_steps=TTT_STEPS,
                        ttt_seq_len=TTT_SEQ, ttt_batch=TTT_BATCH, lora_r=LORA_R,
                        label_in=f"kaggle-{n_gpu}gpu-{name}",
                        allow_ttt_failure=ALLOW_TTT_FAILURE)
        rows.append(r)
        with open(f"/kaggle/working/{name}.json", "w") as fh:
            json.dump(r, fh, indent=1)
    except Exception as e:
        # No swallowing: a model that cannot be profiled fails the kernel. Continuing would emit
        # a summary table missing a row while the run reports success.
        print(f"  profile FAILED: {type(e).__name__}: {str(e)[:200]}")
        raise
    finally:
        # Mounted inputs are read-only and shared; there is nothing to clean up but VRAM.
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        print("", flush=True)

print("\\n" + "=" * 78)
print(f"{'model':<16}{'gen tok/s':>11}{'ttt step s':>12}{'peak GB':>9}{'dtype':>10}")
print("=" * 78)
for r in rows:
    print(f"  {r['label'].split('gpu-')[-1]:<14}{r['gen_tok_s']:>11.1f}"
          f"{(r['ttt']['step_s'] if r['ttt']['step_s'] is not None else float('nan')):>12.2f}"
          f"{(r['peak_mem_gb'] or 0):>9.1f}{r['dtype'].split()[0]:>10}")
print("=" * 78)
print("NOTE: precision differs by hardware (bf16 needs sm80+); fp16 and bf16 rows are NOT")
print("      comparable to each other.")
print("NOTE: multi-GPU here is device_map pipeline sharding, not tensor parallel: it buys")
print("      memory, not speed. A model that fits ONE card can instead run as N independent")
print("      workers, which is the arrangement that matters for per-task sampling budget.")
with open("/kaggle/working/crucible-profile-all.json", "w") as fh:
    json.dump(rows, fh, indent=1)
'''

DRIVER = DRIVER_HEAD + DRIVER_PROFILE

LAYOUT_DRIVER = '''
# ============================ layout experiment ============================
# The layout experiment spawns itself as worker processes — one per card in the replica arm — so
# it has to exist as FILES on disk rather than as inlined kernel code. Both scripts are written
# out byte-for-byte as they are in the repo and this kernel is only a launcher, so the venue runs
# the same code the local machine does.
import subprocess as _sub

_FILES = __FILES__
for _name, _src in _FILES.items():
    with open("/kaggle/working/" + _name, "w") as _fh:
        _fh.write(_src)

ENTRIES = __ENTRIES__
EXPECT_GPUS = __EXPECT_GPUS__
EXPECT_SM = __EXPECT_SM__

# Resolve before preflight, and carry the resolved path into the run — preflight must check the
# path the experiment actually uses.
MIXED = "__MIXED__"
if MIXED:
    _parts = []
    for _m in [x for x in MIXED.split(";") if x.strip()]:
        _p, _sep2, _cards = _m.partition("@")
        _r2 = _resolve_mount(_p)
        if _r2 != _p:
            print(f"  mount resolved: {_p} -> {_r2}", flush=True)
        _parts.append(_r2 + _sep2 + _cards)
    MIXED = ";".join(_parts)

_resolved = []
for _e in ENTRIES:
    _path, _sep, _arms = _e.partition(":")
    _real = _resolve_mount(_path)
    if _real != _path:
        print(f"  mount resolved: {_path} -> {_real}", flush=True)
    _resolved.append(_real + _sep + _arms)
ENTRIES = _resolved

_check = [e.split(":")[0] for e in ENTRIES]
_check += [m.split("@")[0] for m in MIXED.split(";") if m.strip()]
preflight(_check, EXPECT_GPUS, EXPECT_SM)

_cmd = [_sys.executable, "/kaggle/working/crucible-layout.py",
        "--models", ",".join(ENTRIES),
        "--new-tokens", "__NEW_TOKENS__", "--prompt-len", "__PROMPT_LEN__",
        "--ladder", "__LADDER__",
        "--time-budget-min", "__TIME_BUDGET_MIN__",
        "--ttt-batch", "__TTT_BATCH__", "--ttt-steps", "__TTT_STEPS__",__MIXED_ARG____EXTRA_ARGS__
        "--out", "/kaggle/working/crucible-layout.json"]
print("== launching ==\\n  " + " ".join(_cmd) + "\\n", flush=True)
_rc = _sub.call(_cmd)
if _rc != 0:
    # A failed arm fails the kernel: a table holding only the surviving arm is not a comparison.
    raise SystemExit("FAIL: layout experiment exited " + str(_rc))
'''


PARITY_DRIVER = '''
# ============================== parity baseline ==============================
# The parity harness spawns itself as one worker per card, so like the layout experiment it has
# to exist as FILES on disk rather than as inlined kernel code. Every script is written out
# byte-for-byte as it is in the repo, and this kernel is only a launcher, so the venue runs the
# same code the local machine does.
import subprocess as _sub

_FILES = __FILES__
for _name, _src in _FILES.items():
    with open("/kaggle/working/" + _name, "w") as _fh:
        _fh.write(_src)

MODEL = "__MODEL__"
DATA = "__DATA__"
EXPECT_GPUS = __EXPECT_GPUS__
EXPECT_SM = __EXPECT_SM__
RUNS = __RUNS__

def _resolve_attached(path, kinds):
    """Find an attachment whose mount depth is not the one that was asked for.

    Attachments nest differently by kind and the layout is not stable between sessions:
    a dataset appears at /kaggle/input/<slug> or /kaggle/input/datasets/<owner>/<slug>, a
    model at /kaggle/input/models/<owner>/<rest>, and — measured 2026-08-22 — an attached
    COMPETITION at /kaggle/input/competitions/<slug>, never at /kaggle/input/<slug>.
    Rather than encode one guess, try the plausible mounts and take the first that exists.
    """
    import glob as _glob

    rest = path[len("/kaggle/input/"):] if path.startswith("/kaggle/input/") else path
    cands = [path]
    for kind in kinds:
        cands.append(os.path.join("/kaggle/input", kind, rest))
        # The owner segment is not known from the mount path, so let the filesystem supply it.
        cands.extend(sorted(_glob.glob(os.path.join("/kaggle/input", kind, "*", rest))))
    for cand in cands:
        real = _resolve_mount(cand)
        if os.path.isdir(real):
            return real
    return path


MODEL = _resolve_attached(MODEL, ["models"])
DATA = _resolve_attached(DATA, ["competitions", "datasets"])
print(f"  model mount: {MODEL}", flush=True)
print(f"  data  mount: {DATA}", flush=True)

# Preflight FIRST: it is the cheap check that reports what hardware the session actually got,
# and a run that dies before it leaves that unanswered.
preflight([MODEL], EXPECT_GPUS, EXPECT_SM)

if not os.path.isdir(DATA):
    # The split has to come from the competition attachment; without it there is nothing to
    # score against and a run would produce a submission shaped from nothing.
    print("  --- actual /kaggle/input tree ---")
    for _dp, _dn, _fn in os.walk("/kaggle/input"):
        if _dp[len("/kaggle/input"):].count(os.sep) > 3:
            _dn[:] = []
            continue
        print(f"    {_dp}")
    raise SystemExit(f"FAIL: competition data not mounted at {DATA}")

for _i, _extra in enumerate(RUNS):
    _cmd = [_sys.executable, "/kaggle/working/crucible-parity.py",
            "--model-dir", MODEL, "--data", DATA,
            "--out", f"/kaggle/working/crucible-parity-{_i}.json",
            # A single-leg kernel is a SUBMISSION, and the venue nominates a file by name; the
            # per-leg suffix exists only to keep multiple comparison legs from overwriting each
            # other. With one leg there is nothing to disambiguate, so it takes the name the
            # competition expects rather than one that has to be explained at submit time.
            "--submission", ("/kaggle/working/submission.json" if len(RUNS) == 1
                             else f"/kaggle/working/submission-{_i}.json")] + _extra
    print("\\n" + "=" * 78, flush=True)
    print(f"== run {_i}: " + " ".join(_extra), flush=True)
    print("=" * 78 + "\\n", flush=True)
    _rc = _sub.call(_cmd)
    if _rc != 0:
        # A failed leg fails the kernel. A partial result reported as a completed run is the
        # silent-degradation shape this campaign has already paid for once.
        raise SystemExit(f"FAIL: parity run {_i} exited {_rc}")
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="kaggle")
    ap.add_argument("--slug", default="crucible-budget-profile")
    ap.add_argument("--mode", default="profile", choices=["profile", "layout", "parity"],
                    help="profile: the throughput/TTT table. layout: replication vs sharding, "
                         "measured in samples/hour at seq 3072. parity: the posted pack recipe "
                         "on the adopted base, scored against the evaluation split")
    ap.add_argument("--runs", default=[], action="append", metavar="ARGS",
                    help="parity mode: one leg's arguments as a single string. Repeatable, once "
                         "per leg. NOT a delimited list: --members itself uses ';' to separate "
                         "workers. Each leg is a full crucible-parity.py invocation; "
                         "--model-dir, --data, --out and --submission come from the driver")
    ap.add_argument("--data-mount", default="/kaggle/input/arc-prize-2026-arc-agi-2",
                    help="parity mode: the competition attachment holding the split")
    ap.add_argument("--models",
                    default="/kaggle/input/qwen-3/transformers/4b/1",
                    help="comma-separated /kaggle/input mount paths — never hub ids. In layout "
                         "mode an entry may name its arms: <mount>:replica+sharded")
    ap.add_argument("--new-tokens", type=int, default=1024,
                    help="layout mode: generated tokens per sample; with the 2048-token prompt "
                         "the default puts the measurement at sequence length 3072")
    ap.add_argument("--ladder", default="8,32",
                    help="layout mode: aggregate batch sizes; each arm's own max-fit is appended")
    ap.add_argument("--mixed", default="",
                    help="layout mode: run different models at once, each on its own cards: "
                         "'/mount/9b@0,1;/mount/8b@2;/mount/4b@3'")
    ap.add_argument("--prompt-len", type=int, default=2048,
                    help="layout mode: prompt tokens. Real ARC prompts with demo pairs run well "
                         "past 2048; a long prompt costs KV and one prefill, not decode time")
    ap.add_argument("--ttt-steps", type=int, default=5,
                    help="layout mode: timed LoRA steps per member")
    ap.add_argument("--ttt-batch", type=int, default=2,
                    help="layout mode: LoRA step batch. The stock loss materializes "
                         "[batch x seq x vocab]; at vocab 248320 that is ~1 GB per sequence")
    ap.add_argument("--expand-kv", default="auto", choices=["auto", "on", "off"],
                    help="layout mode: expand K/V to the query head count before sdpa. auto "
                         "measures a forward both ways and expands only when it lowers peak "
                         "memory without costing throughput")
    ap.add_argument("--time-budget-min", type=float, default=60.0,
                    help="layout mode: ladder points past this are skipped rather than allowed "
                         "to run out a session")
    ap.add_argument("--title", default="CRUCIBLE budget profile")
    ap.add_argument("--wheels", default=[], action="append", metavar="DIR=SPEC",
                    help="attached wheels dataset mount and the exact pin to install from it, "
                         "e.g. /kaggle/input/datasets/me/wheels=torchao==0.17.0. Repeatable; "
                         "unpinned names are satisfied by whatever is already present and "
                         "become a no-op")
    ap.add_argument("--dataset-sources", default="",
                    help="comma-separated Kaggle dataset refs to attach")
    ap.add_argument("--model-sources", default="",
                    help="comma-separated Kaggle model instance refs to ATTACH, e.g. "
                         "qwen-lm/qwen-3/transformers/4b/1")
    ap.add_argument("--allow-ttt-failure", action="store_true",
                    help="exploratory profiling only; by default a TTT failure fails the run")
    ap.add_argument("--expect-sm", default="",
                    help="expected compute capability, e.g. 8.9 for L4 or 7.5 for T4. An "
                         "unavailable --accelerator is substituted rather than refused, and card "
                         "count alone does not detect that")
    ap.add_argument("--expect-gpus", type=int, default=2,
                    help="preflight dies if the session has a different count — a wrong "
                         "accelerator produces numbers for hardware other than the one requested")
    ap.add_argument("--internet", default="false", choices=["true", "false"],
                    help="default false: models are attached, so no network is needed and the "
                         "kernel matches the submission shape")
    ap.add_argument("--user", default="<owner>")
    ap.add_argument("--competition", default="arc-prize-2026-arc-agi-2",
                    help="attached so the kernel is provisioned with the competition's "
                         "hardware (L4x4) rather than the default notebook accelerators "
                         "(T4x2 / P100), which are a different architecture without bf16")
    a = ap.parse_args()

    src = open(os.path.join(HERE, "crucible-profile.py")).read()
    setup = open(os.path.join(HERE, "kaggle-setup-block.txt")).read()
    installs = []
    for item in a.wheels:
        if "=" not in item:
            raise SystemExit(f"FAIL: --wheels wants DIR=SPEC, got {item!r}")
        d, _, spec = item.partition("=")
        installs.append((d, spec))

    # Drop the CLI entrypoint: a Kaggle kernel takes no argv, and argparse would consume the
    # notebook runner's own arguments.
    src = re.split(r"\nif __name__ == .__main__.:", src)[0]
    if "def profile_one" not in src:
        raise SystemExit("FAIL: crucible-profile.py must expose profile_one() for the kernel "
                         "driver to call. Refactor main() into profile_one() first.")

    os.makedirs(a.out_dir, exist_ok=True)
    models = [m.strip() for m in a.models.split(",") if m.strip()]
    code_file = {"profile": "crucible-profile-kernel.py",
                 "layout": "crucible-layout-kernel.py",
                 "parity": "crucible-parity-kernel.py"}[a.mode]
    with open(os.path.join(a.out_dir, code_file), "w") as fh:
        fh.write("# GENERATED by crucible-kaggle-build.py — do not edit here.\n"
                 "# Source of truth is crucible-profile.py; regenerate after changing it.\n")
        if installs:
            fh.write(setup.replace("__INSTALLS__", repr(installs)))
        if a.mode == "parity":
            # shlex, not split(): a leg carries quoted arguments such as --invalid-note.
            runs = [shlex.split(r) for r in a.runs if r.strip()]
            if not runs:
                raise SystemExit("FAIL: parity mode needs --runs with at least one leg.")
            files = {}
            for name in ("crucible-parity.py", "crucible-grids15.py", "crucible-score.py"):
                path = os.path.join(HERE, name)
                if not os.path.isfile(path):
                    raise SystemExit(f"FAIL: {path} missing — parity mode ships all three.")
                files[name] = open(path).read()
            fh.write(DRIVER_HEAD)
            # __FILES__ is substituted LAST: it carries entire source files, and an earlier
            # substitution would rewrite anything inside them that looked like a placeholder.
            fh.write(PARITY_DRIVER.replace("__MODEL__", models[0])
                                  .replace("__DATA__", a.data_mount)
                                  .replace("__EXPECT_GPUS__", str(a.expect_gpus))
                                  .replace("__EXPECT_SM__", repr(a.expect_sm or None))
                                  .replace("__RUNS__", repr(runs))
                                  .replace("__FILES__", repr(files)))
        elif a.mode == "profile":
            fh.write(src)
            fh.write(DRIVER.replace("__MODELS__", repr(models))
                              .replace("__EXPECT_GPUS__", str(a.expect_gpus))
                              .replace("__EXPECT_SM__", repr(a.expect_sm or None))
                              .replace("__ALLOW_TTT_FAILURE__", str(a.allow_ttt_failure)))
        else:
            # Whole files, __main__ guard included: the layout script is executed as a
            # subprocess, and the profiler is imported by path from beside it.
            files = {}
            for name in ("crucible-profile.py", "crucible-layout.py"):
                path = os.path.join(HERE, name)
                if not os.path.isfile(path):
                    raise SystemExit(f"FAIL: {path} missing — layout mode ships both scripts.")
                files[name] = open(path).read()
            fh.write(DRIVER_HEAD)
            # __FILES__ is substituted LAST: it carries entire source files, and an earlier
            # substitution would rewrite anything inside them that happened to look like a
            # placeholder.
            fh.write(LAYOUT_DRIVER.replace("__ENTRIES__", repr(models))
                                  .replace("__EXPECT_GPUS__", str(a.expect_gpus))
                                  .replace("__EXPECT_SM__", repr(a.expect_sm or None))
                                  .replace("__NEW_TOKENS__", str(a.new_tokens))
                                  .replace("__PROMPT_LEN__", str(a.prompt_len))
                                  .replace("__LADDER__", a.ladder)
                                  .replace("__TIME_BUDGET_MIN__", str(a.time_budget_min))
                                  .replace("__TTT_BATCH__", str(a.ttt_batch))
                                  .replace("__TTT_STEPS__", str(a.ttt_steps))
                                  .replace("__MIXED__", a.mixed)
                                  .replace("__MIXED_ARG__",
                                           ' "--mixed", MIXED,' if a.mixed else "")
                                  .replace("__EXTRA_ARGS__",
                                           f' "--expand-kv", "{a.expand_kv}",')
                                  .replace("__FILES__", repr(files)))

    meta = {
        "id": f"{a.user}/{a.slug}",
        "title": a.title,
        "code_file": code_file,
        "language": "python",
        "kernel_type": "script",
        "is_private": "true",
        "enable_gpu": "true",
        "enable_tpu": "false",
        "enable_internet": a.internet,   # only needed when weights are FETCHED
        "dataset_sources": [d.strip() for d in a.dataset_sources.split(",") if d.strip()],
        "competition_sources": [a.competition] if a.competition else [],
        "kernel_sources": [],
        "model_sources": [m.strip() for m in a.model_sources.split(",") if m.strip()],
    }
    with open(os.path.join(a.out_dir, "kernel-metadata.json"), "w") as fh:
        json.dump(meta, fh, indent=1)

    print(f"  wrote {a.out_dir}/{code_file}")
    print(f"  wrote {a.out_dir}/kernel-metadata.json")
    print(f"  push with: kaggle kernels push -p {a.out_dir} --accelerator <type>")


if __name__ == "__main__":
    main()
