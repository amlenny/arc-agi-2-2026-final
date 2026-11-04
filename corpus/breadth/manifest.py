#!/usr/bin/env python3
# manifest.py -- regenerate synthetic-breadth/_MANIFEST-breadth.json from the pools' _meta.json; prints totals.
import json, os
root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "synthetic-breadth")
man = {}
for d in sorted(os.listdir(root)):
    mp = os.path.join(root, d, "_meta.json")
    if os.path.exists(mp):
        m = json.load(open(mp)); man[d] = {k: m.get(k) for k in ("batch", "desc", "rule_sha", "blocks", "pairs", "digits", "colour_values_matter", "primitive", "big_input_share", "small_grid_warning")}
json.dump({"lane": "breadth", "rules": man, "distinct_rules": len(man), "blocks": sum(v["blocks"] for v in man.values())},
          open(os.path.join(root, "_MANIFEST-breadth.json"), "w"), indent=1)
print(f"manifest: {len(man)} rules, {sum(v['blocks'] for v in man.values())} blocks, {sum(v['pairs'] for v in man.values())} pairs")
