#!/usr/bin/env python3
"""Independent screen of the synthetic pool: counts, validity, duplicates, contamination.

Written without reference to the builder's own screen so the two cannot share a blind spot.
Canonical form of a pair: colours relabelled by first appearance in the input (row-major, output
colours absent from the input relabelled after), then the lexicographically smallest of the 8
dihedral images. A pool pair whose canonical form equals a real pair's is a PAIR collision; an
input-only match is reported separately as the weaker signal.

usage: corpus-verify.py [--pool synthetic] [--out corpus-verify-report.json] [--workers N]
"""
import argparse, hashlib, json, os, sys, collections
from multiprocessing import Pool
import numpy as np

ARC2 = os.environ.get("ARC_DATA") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "crucible", "data-kaggle")
ARC1_EVAL = (os.environ.get("ARC1_EVAL")
             or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "crucible", "data-sources", "arc-agi-1", "data", "evaluation"))


def relabel(inp, out):
    order = []
    seen = set()
    for v in inp.ravel():
        if v not in seen:
            seen.add(v); order.append(v)
    for v in out.ravel():
        if v not in seen:
            seen.add(v); order.append(v)
    lut = np.zeros(10, dtype=np.int8)
    for i, v in enumerate(order):
        lut[v] = i
    return lut[inp], lut[out]


def dihedral(a):
    for k in range(4):
        r = np.rot90(a, k)
        yield r
        yield r[:, ::-1]


def canon(inp, out):
    inp = np.asarray(inp, dtype=np.int8); out = np.asarray(out, dtype=np.int8)
    best = None
    for ti, to in zip(dihedral(inp), dihedral(out)):
        a, b = relabel(ti, to)
        key = (a.shape, a.tobytes(), b.shape, b.tobytes())
        if best is None or key < best:
            best = key
    return hashlib.sha1(repr(best).encode()).hexdigest()


def canon_input(inp):
    inp = np.asarray(inp, dtype=np.int8)
    best = None
    for ti in dihedral(inp):
        a, _ = relabel(ti, ti[:0])
        key = (a.shape, a.tobytes())
        if best is None or key < best:
            best = key
    return hashlib.sha1(repr(best).encode()).hexdigest()


def valid_grid(g):
    if not isinstance(g, list) or not g or not all(isinstance(r, list) for r in g):
        return 'not a grid'
    w = len(g[0])
    if w == 0 or any(len(r) != w for r in g):
        return 'ragged or empty'
    if len(g) > 30 or w > 30:
        return 'side > 30'
    if any((not isinstance(v, int)) or v < 0 or v > 9 for r in g for v in r):
        return 'value outside 0-9'
    return None


def real_pairs():
    pairs = []   # (source, task, kind, input, output)
    ch = json.load(open(f'{ARC2}/arc-agi_evaluation_challenges.json'))
    so = json.load(open(f'{ARC2}/arc-agi_evaluation_solutions.json'))
    for t, task in ch.items():
        for p in task['train']:
            pairs.append(('eval120', t, 'train', p['input'], p['output']))
        for i, p in enumerate(task['test']):
            pairs.append(('eval120', t, 'test', p['input'], so[t][i]))
    ch = json.load(open(f'{ARC2}/arc-agi_training_challenges.json'))
    so = json.load(open(f'{ARC2}/arc-agi_training_solutions.json'))
    for t, task in ch.items():
        for p in task['train']:
            pairs.append(('train1000', t, 'train', p['input'], p['output']))
        for i, p in enumerate(task['test']):
            pairs.append(('train1000', t, 'test', p['input'], so[t][i]))
    if os.path.isdir(ARC1_EVAL):
        for f in sorted(os.listdir(ARC1_EVAL)):
            if not f.endswith('.json'):
                continue
            task = json.load(open(os.path.join(ARC1_EVAL, f)))
            for p in task['train']:
                pairs.append(('arc1eval', f[:-5], 'train', p['input'], p['output']))
            for p in task['test']:
                pairs.append(('arc1eval', f[:-5], 'test', p['input'], p['output']))
    return pairs


def scan_task(args):
    pool, task, real_pair_keys, real_input_keys, holdout = args
    d = os.path.join(pool, task)
    # THE HOLDOUT WAS COUNTED AND NEVER READ. `files` below excludes every underscore-prefixed name,
    # so _holdout contributed a block count and not one of its pairs ever reached the contamination
    # index -- 2,603 blocks and 10,415 pairs, the set generalisation is measured on, unscreened.
    # --holdout scans those instead of the main blocks; it is the same screen pointed one level in.
    if holdout:
        d = os.path.join(d, '_holdout')
        if not os.path.isdir(d):
            return dict(task=task, blocks=0, pairs=0, holdout_blocks=0, invalid=[], no_train_or_test=0,
                        input_eq_output=0, empty_output=0, shas=collections.Counter(),
                        exact_dup_pairs=0, pair_collisions=[], input_collisions=[])
    rep = dict(task=task, blocks=0, pairs=0, holdout_blocks=0, invalid=[], no_train_or_test=0,
               input_eq_output=0, empty_output=0, shas=collections.Counter(), pair_hashes=collections.Counter(),
               pair_collisions=[], input_collisions=[])
    files = sorted(f for f in os.listdir(d) if f.endswith('.json') and not f.startswith('_'))
    hd = os.path.join(d, '_holdout')
    if os.path.isdir(hd):
        rep['holdout_blocks'] = sum(1 for f in os.listdir(hd) if f.endswith('.json'))
    for f in files:
        try:
            b = json.load(open(os.path.join(d, f)))
        except Exception as e:
            rep['invalid'].append((f, 'unreadable')); continue
        rep['blocks'] += 1
        rep['shas'][b.get('_skeleton_sha', 'NONE')[:8]] += 1
        if not b.get('train') or not b.get('test'):
            rep['no_train_or_test'] += 1
        for kind in ('train', 'test'):
            for i, p in enumerate(b.get(kind, [])):
                rep['pairs'] += 1
                ei, eo = valid_grid(p.get('input')), valid_grid(p.get('output'))
                if ei or eo:
                    rep['invalid'].append((f, f'{kind}[{i}] ' + (ei or eo))); continue
                if p['input'] == p['output']:
                    rep['input_eq_output'] += 1
                if not any(v for r in p['output'] for v in r):
                    rep['empty_output'] += 1
                h = hashlib.sha1((json.dumps(p['input']) + '|' + json.dumps(p['output'])).encode()).hexdigest()
                rep['pair_hashes'][h] += 1
                ck = canon(p['input'], p['output'])
                if ck in real_pair_keys:
                    rep['pair_collisions'].append((f, kind, i, real_pair_keys[ck]))
                else:
                    ik = canon_input(p['input'])
                    if ik in real_input_keys:
                        rep['input_collisions'].append((f, kind, i, real_input_keys[ik]))
    ph = rep.pop('pair_hashes')
    rep['exact_dup_pairs'] = sum(v - 1 for v in ph.values() if v > 1)
    rep['shas'] = dict(rep['shas'])
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pool', default='synthetic')
    ap.add_argument('--out', default='corpus-verify-report.json')
    ap.add_argument('--workers', type=int, default=max(1, os.cpu_count() - 1))
    ap.add_argument('--holdout', action='store_true',
                    help="scan each task's _holdout blocks instead of its main blocks")
    a = ap.parse_args()
    rp = real_pairs()
    real_pair_keys, real_input_keys = {}, {}
    for src, t, kind, i, o in rp:
        real_pair_keys.setdefault(canon(i, o), f'{src}:{t}:{kind}')
        real_input_keys.setdefault(canon_input(i), f'{src}:{t}:{kind}')
    by_src = collections.Counter(s for s, *_ in rp)
    print('real pairs indexed:', dict(by_src), 'unique canonical pairs', len(real_pair_keys), flush=True)
    # --pool POINTED AT ONE TASK READ ONLY ITS _holdout AND CALLED IT THE POOL. Every subdirectory
    # was treated as a task, so `--pool synthetic/0934a4d8` found `_holdout`, scanned its 16 blocks,
    # and printed blocks:16 with every collision count at zero — a clean report on 2.6% of the pool,
    # indistinguishable from a clean report on all of it. Found 2026-09-15 screening a rebuild.
    # A directory holding block .json files directly IS a task, not a container of tasks, and an
    # underscore-prefixed directory is never a task (the holdout is counted, not scanned as one).
    own = sorted(f for f in os.listdir(a.pool) if f.endswith('.json') and not f.startswith('_'))
    if own:
        root, tasks = os.path.dirname(a.pool.rstrip('/')) or '.', [os.path.basename(a.pool.rstrip('/'))]
        a.pool = root
        print('SINGLE TASK: %s holds block files directly, scanning it as one task' % tasks[0])
    else:
        tasks = sorted(t for t in os.listdir(a.pool)
                       if os.path.isdir(os.path.join(a.pool, t)) and not t.startswith('_'))
    if not tasks:
        print('NOTHING TO SCAN under %s — not a pass, nothing was read.' % a.pool)
        return 2
    with Pool(a.workers) as pl:
        reps = pl.map(scan_task, [(a.pool, t, real_pair_keys, real_input_keys, a.holdout) for t in tasks])
    tot = collections.Counter()
    for r in reps:
        for k in ('blocks', 'pairs', 'holdout_blocks', 'no_train_or_test', 'input_eq_output', 'empty_output', 'exact_dup_pairs'):
            tot[k] += r[k]
        tot['invalid'] += len(r['invalid']); tot['pair_collisions'] += len(r['pair_collisions']); tot['input_collisions'] += len(r['input_collisions'])
        tot['tasks_multi_sha'] += len(r['shas']) > 1
    json.dump(dict(totals=dict(tot), tasks=reps), open(a.out, 'w'), indent=1)
    print('TOTALS', dict(tot))
    for r in reps:
        flags = []
        if r['invalid']: flags.append(f"invalid {len(r['invalid'])}")
        if r['pair_collisions']: flags.append(f"PAIR-COLLISIONS {len(r['pair_collisions'])}")
        if r['input_collisions']: flags.append(f"input-collisions {len(r['input_collisions'])}")
        if r['exact_dup_pairs']: flags.append(f"dups {r['exact_dup_pairs']}")
        if r['input_eq_output']: flags.append(f"in==out {r['input_eq_output']}")
        if r['empty_output']: flags.append(f"empty-out {r['empty_output']}")
        if len(r['shas']) > 1: flags.append(f"shas {r['shas']}")
        if flags:
            print(r['task'], r['blocks'], r['pairs'], ' | '.join(flags))


if __name__ == '__main__':
    main()
