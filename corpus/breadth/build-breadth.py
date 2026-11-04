#!/usr/bin/env python3
# build-breadth.py [--rules-dir rules] [--only NAME,..] [--batch FILE.py] [--blocks 12] [--out ../synthetic-breadth]
#                  [--check]  -- import every rules/*.py (each registers rules via harness.rule), build one pool per
# rule under --out, print one line per rule (OK/FAIL with reject reasons), write _MANIFEST-breadth.json.
# --check builds nothing on disk: it draws and gates in memory and reports, for authors iterating on a batch.
import argparse, glob, importlib.util, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harness as H  # noqa: E402


def load(files):
    for f in files:
        sp = importlib.util.spec_from_file_location("rules_" + os.path.basename(f)[:-3], f)
        m = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(m)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules-dir", default=os.path.join(HERE, "rules"))
    ap.add_argument("--batch", default="", help="one batch file instead of the whole rules dir")
    ap.add_argument("--only", default="")
    ap.add_argument("--blocks", type=int, default=12)
    ap.add_argument("--min-blocks", type=int, default=8)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "synthetic-breadth"))
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    files = [a.batch] if a.batch else sorted(glob.glob(os.path.join(a.rules_dir, "*.py")))
    load(files)
    want = set(a.only.split(",")) if a.only else set(H.RULES)
    out = a.out if not a.check else os.path.join(HERE, f".check-scratch-{os.getpid()}")
    ok = fail = 0
    for name in sorted(H.RULES):
        if name not in want:
            continue
        m = H.build_pool(H.RULES[name], out, a.blocks, a.min_blocks)
        if m["ok"]:
            ok += 1
            print(f"{'OK* ' if m.get('small_grid_warning') else 'OK  '} {name:34s} blocks {m['blocks']:3d} pairs {m['pairs']:4d} reject {m['reject_rate']:.2f} big {m['big_input_share']:.2f} {m['batch']}")
        else:
            fail += 1
            print(f"FAIL {name:34s} blocks {m['blocks']:3d} reject {m['reject_rate']:.2f} big {m['big_input_share']:.2f} {m['rejects']} {m['batch']}")
    if a.check:
        import shutil; shutil.rmtree(out, ignore_errors=True)
    else:
        man = {}
        for d in sorted(os.listdir(a.out)):
            mp = os.path.join(a.out, d, "_meta.json")
            if os.path.exists(mp):
                mm = json.load(open(mp)); man[d] = {k: mm.get(k) for k in ("batch", "desc", "rule_sha", "blocks", "pairs", "digits", "colour_values_matter", "primitive", "big_input_share")}
        json.dump({"lane": "breadth", "rules": man, "distinct_rules": len(man),
                   "blocks": sum(v["blocks"] for v in man.values())}, open(os.path.join(a.out, "_MANIFEST-breadth.json"), "w"), indent=1)
        print(f"manifest: {len(man)} rules, {sum(v['blocks'] for v in man.values())} blocks")
    print(f"ok {ok} fail {fail}")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
