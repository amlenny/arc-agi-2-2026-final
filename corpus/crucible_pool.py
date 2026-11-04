# crucible_pool.py -- one reader for the synthetic corpus, shared by every diagnostic.
#
# TWO LAYOUTS ARE LIVE AT ONCE and every reader has to handle both, so they handle it here rather
# than each keeping its own copy of the rule:
#
#   pool     one directory per source task, one problem per file
#            synthetic/13e47133/midband_13e47133_mid_000.json
#   flat     one file per source holding a map of instance id -> problem
#            probes-nbr/nbrB_3dc255db.json
#
# The midband lane moved to the pool layout; band90 has not yet. A reader that understood only one
# of the two would report the other lane's corpus as empty rather than fail, which is the failure
# mode this module exists to prevent: silence presenting as a result.
import json
import os

POOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "synthetic")


def is_pool(root):
    """True when root holds task DIRECTORIES rather than per-source files."""
    return any(os.path.isdir(os.path.join(root, e)) and not e.startswith("_")
               for e in os.listdir(root))


def sources(root):
    """The set of source task ids a corpus covers, in either layout."""
    out = set()
    for e in sorted(os.listdir(root)):
        p = os.path.join(root, e)
        if e.startswith("_"):
            continue
        if os.path.isdir(p):
            out.add(e)                                   # the directory name IS the task id
        elif e.endswith(".json"):
            out.add(e[:-5].split("_")[-1])               # <lane>_<source>.json
    return out


def load(root, only=None):
    """{source_id: {instance_id: problem}} from either layout.

    only: optional iterable of source ids to restrict to.
    """
    want = set(only) if only is not None else None
    out = {}
    for e in sorted(os.listdir(root)):
        p = os.path.join(root, e)
        if e.startswith("_"):
            continue
        if os.path.isdir(p):
            if want is not None and e not in want:
                continue
            blocks = {}
            for b in sorted(os.listdir(p)):
                if b.endswith(".json") and not b.startswith("_"):
                    blocks[b[:-5]] = json.load(open(os.path.join(p, b)))
            if blocks:
                out[e] = blocks
        elif e.endswith(".json"):
            src = e[:-5].split("_")[-1]
            if want is not None and src not in want:
                continue
            out[src] = json.load(open(p))
    return out


def resolve(name):
    """Accept an absolute path, a bare directory name under corpus/, or '' for the pool."""
    if not name:
        return POOL
    if os.path.isabs(name):
        return name.rstrip("/")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name.rstrip("/"))

def _plain(v, depth=0):
    """Data whose repr is stable across loads: numbers, strings and containers of them. A registry
    holding function objects reprs with addresses and would make the sha differ on every run."""
    if depth > 6:
        return False
    if v is None or isinstance(v, (bool, int, float, str)):
        return True
    if isinstance(v, (list, tuple, set, frozenset)):
        return all(_plain(x, depth + 1) for x in v)
    if isinstance(v, dict):
        return all(_plain(k, depth + 1) and _plain(x, depth + 1) for k, x in v.items())
    return False


def closure_sha(*fns):
    """sha256 over the source of the given functions AND everything they reach in their own module:
    every module-level function they call, transitively, and every module-level data table they
    read. The per-function sha (skeleton_sha) misses a HELPER that several skeletons share -- edit
    the helper and every caller's pool stays stamped current while built from old code, and the
    top-up refusal never fires (seen on 269e22fb 09-18: creature/trace drawn under one unchanged
    sha; named by for the band90 builder). Recorded as skeleton_sha_v2 beside the
    legacy field so pools built before it stay accepted and new pools carry the stronger stamp."""
    import hashlib, inspect, types
    seen, parts = set(), []
    todo = list(fns)
    while todo:
        f = todo.pop(0)
        if not isinstance(f, types.FunctionType) or f in seen:
            continue
        seen.add(f)
        parts.append((f.__module__ or "", f.__qualname__, inspect.getsource(f)))
        g = f.__globals__
        codes = [f.__code__]
        while codes:
            co = codes.pop()
            codes.extend(c for c in co.co_consts if isinstance(c, types.CodeType))
            for name in co.co_names:
                v = g.get(name)
                if isinstance(v, types.FunctionType) and v.__module__ == f.__module__:
                    todo.append(v)
                elif _plain(v):
                    parts.append((f.__module__ or "", "data:" + name, repr(v)))   # a module-level table
    parts = sorted(set((q, src) for _m, q, src in parts))
    return hashlib.sha256("".join(q + src for q, src in parts).encode()).hexdigest()
