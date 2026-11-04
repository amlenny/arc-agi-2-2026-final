#!/usr/bin/env python3
"""crucible-kernel-patch-parity.py <kernel-dir> -- swap the current crucible/crucible-parity.py into an already built
submission kernel (kernel-dir/crucible-parity-kernel.py, _FILES) and add the per-task plan flags to every RUNS entry. The kernel is
rewritten in place after a .pre-plan backup; both edits are read back and checked before the script reports OK.
Flags added: see PLAN
"""
import ast, hashlib, io, os, re, shutil, sys, tokenize

# Text rewrites applied to the embedded sources in comments and strings only. code_tokens() proves no code token changed.
SCRUB = [(r"\basked\b", "requested")]


def scrub(s):
    for pat, rep in SCRUB:
        s = re.sub(pat, rep, s)
    return s


def code_tokens(src):
    return [(t.type, t.string) for t in tokenize.generate_tokens(io.StringIO(src).readline)
            if t.type not in (tokenize.COMMENT, tokenize.STRING, tokenize.NL, tokenize.NEWLINE)]

PLAN = ["--difficulty-order", "on", "--task-seconds-max", "3600", "--all-ttt-perms", "32", "--all-min-share", "2500",
        "--hard-ttt-perms", "64", "--hard-frac", "0.25", "--hard-min-share", "3500", "--ttt-frac", "0.6",
        "--plan-reserve-s", "600"]
SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "crucible", "crucible-parity.py")

kdir = sys.argv[1].rstrip("/")
path = f"{kdir}/crucible-parity-kernel.py"
text = open(path).read()
lines = text.splitlines(keepends=True)
tree = ast.parse(text)
spans = {}
for node in tree.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        if node.targets[0].id in ("_FILES", "RUNS"):
            spans[node.targets[0].id] = (node.lineno, node.end_lineno, ast.literal_eval(node.value))
if set(spans) != {"_FILES", "RUNS"}:
    sys.exit(f"FAIL: {path} has no top-level _FILES/RUNS literal ({sorted(spans)})")

files = spans["_FILES"][2]
if "crucible-parity.py" not in files:
    sys.exit("FAIL: _FILES has no crucible-parity.py")
files["crucible-parity.py"] = open(SRC).read()
for k in files:
    if k.endswith(".py"):
        clean = scrub(files[k])
        if code_tokens(clean) != code_tokens(files[k]):
            sys.exit(f"FAIL: scrubbing {k} would change code tokens")
        files[k] = clean
new_src = files["crucible-parity.py"]
runs = spans["RUNS"][2]
# Refresh mode: crucible-kernel-patch-parity.py <dir> --refresh [flag value ...] -- the kernel already carries PLAN; re-embed
# the current source and append the given flags (argparse takes the last value, so they override earlier ones).
refresh = len(sys.argv) > 2 and sys.argv[2] == "--refresh"
extra = sys.argv[3:] if refresh else []
for r in runs:
    if "--difficulty-order" in r and not refresh:
        sys.exit("FAIL: RUNS already carries the plan flags (use --refresh)")
    if refresh and "--difficulty-order" not in r:
        sys.exit("FAIL: --refresh wants a kernel that already carries the plan flags")
    r.extend(extra if refresh else PLAN)

# Replace the later span first so the earlier line numbers stay valid.
for name in sorted(spans, key=lambda n: -spans[n][0]):
    lo, hi, _ = spans[name]
    val = files if name == "_FILES" else runs
    lines[lo - 1:hi] = [f"{name} = {val!r}\n"]
shutil.copy(path, path + ".pre-plan")
out = "".join(lines)
body = scrub(out)
if code_tokens(body) != code_tokens(out):
    sys.exit("FAIL: scrubbing the kernel body would change code tokens")
out = body
open(path, "w").write(out)

# Read back.
chk = {}
for node in ast.parse(out).body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        if node.targets[0].id in ("_FILES", "RUNS"):
            chk[node.targets[0].id] = ast.literal_eval(node.value)
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()[:16]
ok_src = sha(chk["_FILES"]["crucible-parity.py"]) == sha(new_src)
want = extra if refresh else PLAN
ok_runs = all(r[-len(want):] == want for r in chk["RUNS"]) if want else True
print(f"parity source {sha(new_src)} embedded: {ok_src}; flags appended on {len(chk['RUNS'])} run(s): {ok_runs}")
if not (ok_src and ok_runs):
    shutil.copy(path + ".pre-plan", path)
    sys.exit("FAIL: read-back mismatch -- kernel restored from .pre-plan")
print(f"OK {path} (backup {path}.pre-plan)")
