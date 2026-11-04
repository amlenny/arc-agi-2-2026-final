#!/usr/bin/env python
# crucible-score.py — local ARC-AGI-2 scorer (CRUCIBLE C0).
#
# Reproduces Kaggle's scoring so a candidate can be measured at home before it costs a
# submission. Rules the scoring implements, and which are load-bearing:
#
#   * EXACT MATCH. A predicted grid counts only if every cell matches. No partial credit, no
#     shape tolerance.
#   * TWO ATTEMPTS per test input, scored as a hit if EITHER matches. No penalty for a wrong
#     attempt, so an unused second attempt is wasted budget rather than a safe choice.
#
# WHICH AGGREGATION RULE IS OFFICIAL IS NOT YET SETTLED FROM A PRIMARY SOURCE, so both are
# computed and both are reported. They differ only on the 49 evaluation tasks that carry more
# than one test input.
#
#   strict     a task counts only when ALL of its test inputs are solved.
#   partial    each test input earns 1/N of its task.
#
# Evidence currently favours PARTIAL, on two independent lines:
#   1. Published leaderboard scores are not multiples of 1/120. The evaluation split is 71
#      one-input, 46 two-input and 3 three-input tasks, so partial credit produces halves and
#      thirds and nothing else. 71.25% is 85.5/120 and 37.22% is 44+2/3 over 120 — neither is
#      reachable when every task contributes an integer.
#   2. The 2025 winning submission's own validator awards 1/len(test) per solved test input.
# Neither is the rule text. The competition's Evaluation tab renders client-side and needs a
# human browser read to close this, the same way the runtime limit was closed.
#
# Nothing here picks a winner: `score` remains the strict number every earlier campaign
# measurement was taken under, so no past figure silently changes meaning, and `score_partial`
# sits beside it.
#
# Submission shape follows Kaggle's sample_submission.json:
#   {task_id: [{"attempt_1": grid, "attempt_2": grid}, ...one entry per test input...]}
#
# THE KAGGLE 'test' SPLIT IS A PLACEHOLDER. Measured 2026-08-19: all 240 of its task ids are
# exact copies of training tasks (test∩training = 240/240, test∩evaluation = 0). The file exists
# so a notebook run produces a correctly-shaped submission; at Kaggle's server-side rerun the
# real private set replaces it under the same filename. A local run against it therefore
# validates pipeline shape and runtime ONLY — its answers are worthless as signal, and the
# private set's task count is unknown (240 here proves nothing; do not hard-code it).
#
# Stdlib only — this has to run inside the offline competition notebook as well as at home.
import argparse
import collections
import json
import os
import sys

# Paths resolve from this file's own location. Never absolute, never home-anchored: this tree is
# cloned to a different place on every box it runs on, and inside the competition notebook it is
# somewhere else again.
HERE = os.path.dirname(os.path.abspath(__file__))


def load_tasks(data_dir, split):
    """Load a split from EITHER layout, preferring Kaggle's.

    Two layouts exist and they are NOT interchangeable:
      kaggle : arc-agi_<split>_challenges.json  (test entries carry only 'input')
             + arc-agi_<split>_solutions.json   (list of output grids per task)
      github : data/<split>/<task_id>.json      (test entries carry 'output' inline)

    KAGGLE IS AUTHORITATIVE. Measured 2026-08-18: the two sources share all 120 evaluation task
    ids but disagree on 5 of them — 4a21e3da, abc82100, b6f77b65, f560132c and faa9f03d each
    carry MORE test inputs in the Kaggle snapshot, and faa9f03d has one fewer demo pair. The
    upstream repo keeps a changelog of task revisions, so the mirror drifts. Scoring against the
    github copy would therefore disagree with the leaderboard on those tasks.
    """
    kag_c = os.path.join(data_dir, f"arc-agi_{split}_challenges.json")
    kag_s = os.path.join(data_dir, f"arc-agi_{split}_solutions.json")
    if os.path.exists(kag_c):
        with open(kag_c) as fh:
            tasks = json.load(fh)
        if os.path.exists(kag_s):
            with open(kag_s) as fh:
                sol = json.load(fh)
            for tid, task in tasks.items():
                outs = sol.get(tid)
                if outs is None:
                    continue
                if len(outs) != len(task["test"]):
                    raise SystemExit(f"FAIL: {tid} has {len(task['test'])} test inputs but "
                                     f"{len(outs)} solutions — mismatched files")
                for t, o in zip(task["test"], outs):
                    t["output"] = o
        # No solutions file is normal for the held-out test split; scoring it is impossible and
        # says so rather than silently reporting zero.
        return tasks

    d = os.path.join(data_dir, "data", split)
    if not os.path.isdir(d):
        raise SystemExit(f"FAIL: no data at {data_dir} — expected either "
                         f"arc-agi_{split}_challenges.json or data/{split}/")
    tasks = {}
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(d, fn)) as fh:
            tasks[fn[:-5]] = json.load(fh)
    return tasks


def grids_equal(a, b):
    """Exact match including shape. Guards against the common failure of comparing a ragged or
    string-typed grid to an int grid and silently getting False for the wrong reason."""
    if a is None or b is None:
        return False
    if len(a) != len(b):
        return False
    for ra, rb in zip(a, b):
        if len(ra) != len(rb):
            return False
        for ca, cb in zip(ra, rb):
            if int(ca) != int(cb):
                return False
    return True


def score(tasks, submission, verbose=False):
    per_task, missing, malformed = {}, [], []
    for tid, task in tasks.items():
        tests = task.get("test", [])
        preds = submission.get(tid)
        if preds is None:
            missing.append(tid)
            per_task[tid] = {"solved": False, "n_test": len(tests), "n_hit": 0}
            continue
        if len(preds) != len(tests):
            # A submission with the wrong number of entries is scored zero for the task rather
            # than partially, matching Kaggle, and is reported so it is not mistaken for a
            # modelling failure.
            malformed.append((tid, len(preds), len(tests)))
            per_task[tid] = {"solved": False, "n_test": len(tests), "n_hit": 0}
            continue
        hits = 0
        for t, p in zip(tests, preds):
            gold = t.get("output")
            if any(grids_equal(p.get(k), gold) for k in ("attempt_1", "attempt_2")):
                hits += 1
        per_task[tid] = {"solved": hits == len(tests), "n_test": len(tests), "n_hit": hits}

    solved = sum(1 for v in per_task.values() if v["solved"])
    total = len(tasks)
    # Fractional credit, summed over tasks. A task with no test inputs would be degenerate;
    # it contributes nothing rather than dividing by zero.
    credit = sum(v["n_hit"] / v["n_test"] for v in per_task.values() if v["n_test"])
    return {
        "score": solved / total if total else 0.0,
        "solved": solved, "total": total,
        "score_partial": credit / total if total else 0.0,
        "credit": round(credit, 4),
        "missing_tasks": missing, "malformed_tasks": malformed,
        "per_task": per_task,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data-kaggle",
                    help="Kaggle competition dir (authoritative) or the github mirror clone")
    ap.add_argument("--split", default="evaluation",
                    choices=["training", "evaluation", "test"])
    ap.add_argument("--submission", help="submission json; omit to just describe the split")
    ap.add_argument("--out", help="write the full result json here")
    a = ap.parse_args()

    tasks = load_tasks(a.data, a.split)
    gradable = sum(1 for t in tasks.values() if all("output" in x for x in t.get("test", [])))
    ntest = collections.Counter(len(t.get("test", [])) for t in tasks.values())
    ntrain = collections.Counter(len(t.get("train", [])) for t in tasks.values())
    print(f"== ARC-AGI-2 {a.split} ==\n  tasks: {len(tasks)}")
    print(f"  test inputs per task : {dict(sorted(ntest.items()))}")
    print(f"  demo pairs per task  : {dict(sorted(ntrain.items()))}")
    multi = sum(n for k, n in ntest.items() if k > 1)
    print(f"  tasks with >1 test input: {multi}"
          f"  <- the only tasks the strict and partial rules disagree on")
    print(f"  gradable (outputs present): {gradable}/{len(tasks)}")
    if gradable == 0:
        print(f"  NOTE: no solutions for this split — it is held out. Nothing local can score it.")

    if not a.submission:
        return

    # Refuse to score a split with no ground truth: every comparison would be False and the
    # result would print as a real-looking 0.0000.
    if gradable == 0:
        raise SystemExit("FAIL: not scorable — no ground truth for any task in this split "
                         "(held out); refusing to fabricate a 0.0 score")

    with open(a.submission) as fh:
        sub = json.load(fh)
    r = score(tasks, sub)
    print(f"\n== SCORE ==")
    print(f"  strict   {r['solved']}/{r['total']} tasks = {r['score']:.4f}"
          f"   (a task counts only when every test input is solved)")
    print(f"  partial  {r['credit']}/{r['total']} tasks = {r['score_partial']:.4f}"
          f"   (each test input earns 1/N)")
    print(f"  the two differ only on tasks with more than one test input; which rule is "
          f"official is not yet settled from a primary source")
    if r["missing_tasks"]:
        print(f"  MISSING from submission: {len(r['missing_tasks'])} tasks "
              f"(scored zero) e.g. {r['missing_tasks'][:3]}")
    if r["malformed_tasks"]:
        print(f"  WRONG ENTRY COUNT: {len(r['malformed_tasks'])} tasks (scored zero) "
              f"e.g. {r['malformed_tasks'][:3]} as (task, given, expected)")
    partial = [t for t, v in r["per_task"].items() if not v["solved"] and v["n_hit"] > 0]
    if partial:
        print(f"  partially-hit tasks (some test inputs right, task still zero): {len(partial)}")

    if a.out:
        with open(a.out, "w") as fh:
            json.dump(r, fh, indent=1)
        print(f"  wrote {a.out}")


if __name__ == "__main__":
    main()
