#!/usr/bin/env python3
# compose-build.py N SEED OUT [BLOCKS=2] [JOBS=8] -- two-step compositions:
# NEW two-step rules made programmatically from the existing breadth rules. For a random pair (A, B):
# make_input = A.make_input, transform(x) = B.transform(A.transform(x)); description = A's sentence, then B's;
# sha = sha256(A.sha : B.sha). A composition passes only if (1) the harness's own gates pass on its blocks
# (identity, constant answers, G1/G2 simple-hypothesis, benchmark screen, distinct inputs, reject rate) and
# (2) BOTH steps matter: on >= 80% of its pairs the output differs from A(x) alone and from B(x) alone, so a
# composition that one step erases is dropped. Pairs with a P4 held-out component (sorted(rules)[19::20]) are
# never composed. Blocks are written in the breadth layout (OUT/<name>/NNN.json + _meta.json) so nv-stage.py
# --breadth-dir OUT [--br-samples K] reads them; BREADTH_DEMOS controls pairs per block (29,29 = 30-pair puzzles).
# Each candidate gets COMPOSE_TIMEOUT seconds (default 60); a slow pair is skipped, not a crash. Resumable: an
# existing OUT/<name>/ is skipped. Writes OUT/_MANIFEST-breadth.json at the end (same shape as build-breadth.py).
# COMPOSE_LEFT=<file of rule names>: the first component A is drawn from that list (e.g. a new authoring wave) and B from
# every other rule, so a wave is composed with the whole tree; COMPOSE_EITHER=1 draws A or B from the list at random.
# COMPOSE_RIGHT=<file> COMPOSE_RIGHT_P=0.5: with probability P the second component B is drawn from that list (e.g. the high-loss
# breadth rules) instead of the whole non-P4 pool, so a run can be biased toward rules the model finds hard.
import sys, os, random, time, hashlib, json, glob, importlib.util, collections, multiprocessing as mp, signal, shutil
B = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, B)
import harness as H

def load_all():
    for f in sorted(glob.glob(os.path.join(B, 'rules', '*.py'))):
        sp = importlib.util.spec_from_file_location('rules_' + os.path.basename(f)[:-3], f); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
load_all()
NAMES = sorted(H.RULES); P4 = set(NAMES[19::20])

def composed(a, b):
    A, Bq = H.RULES[a], H.RULES[b]
    def tf(g):
        y = A.transform([r[:] for r in g])
        if y is None or not H.well_formed(y): return None
        return Bq.transform([r[:] for r in y])
    r = H.Rule.__new__(H.Rule)
    r.name = f"{a}__then__{b}"; r.desc = A.desc.rstrip('. ') + '. Then: ' + Bq.desc
    r.make_input = A.make_input; r.transform = tf; r.demos = (3, 5)
    r.digits = A.digits or Bq.digits; r.primitive = False; r.small_ok = A.small_ok or Bq.small_ok
    r.batch = 'compose'; r.sha = hashlib.sha256((A.sha + ':' + Bq.sha).encode()).hexdigest()
    return r

class _TO(BaseException): pass   # BaseException so the rule-level "except Exception" guards cannot swallow the per-candidate alarm (stall seen 2026-10-24)
def _alarm(sig, frm): raise _TO('timeout')

def work(args):
    a, b, out, blocks = args
    name = f"{a}__then__{b}"; d = os.path.join(out, name)
    if os.path.exists(os.path.join(d, '_meta.json')):
        return (a, b, 'skip', 0, 0.0)
    t0 = time.time(); signal.signal(signal.SIGALRM, _alarm); signal.alarm(int(os.environ.get('COMPOSE_TIMEOUT', '60')))
    try:
        m = H.build_pool(composed(a, b), out, blocks=blocks, min_blocks=max(1, blocks * 2 // 3))
        if m['ok']:
            A, Bq = H.RULES[a], H.RULES[b]; n = both = 0
            for f in glob.glob(os.path.join(d, '*.json')):
                if os.path.basename(f).startswith('_'): continue
                for p in (lambda blk: blk['train'] + blk['test'])(json.load(open(f))):
                    n += 1
                    try: ya = A.transform([r[:] for r in p['input']])
                    except Exception: ya = None
                    try: yb = Bq.transform([r[:] for r in p['input']])
                    except Exception: yb = None
                    both += (p['output'] != ya and p['output'] != yb)
            m['both_matter'] = round(both / max(1, n), 2); m['components'] = [a, b]
            if both < 0.8 * n: m['ok'] = False; m['rejects'] = {'degenerate_composition': n - both}
            else:
                mm = json.load(open(os.path.join(d, '_meta.json'))); mm.update({'both_matter': m['both_matter'], 'components': [a, b]}); json.dump(mm, open(os.path.join(d, '_meta.json'), 'w'))
        if not m['ok']: shutil.rmtree(d, ignore_errors=True)
        return (a, b, 'ok' if m['ok'] else 'fail', m['blocks'], round(time.time() - t0, 1))
    except BaseException as e:
        shutil.rmtree(d, ignore_errors=True)
        return (a, b, 'timeout' if isinstance(e, _TO) else 'error', 0, round(time.time() - t0, 1))
    finally:
        signal.alarm(0)

def manifest(out):
    man = {}
    for d in sorted(os.listdir(out)):
        mp_ = os.path.join(out, d, '_meta.json')
        if os.path.exists(mp_):
            mm = json.load(open(mp_)); man[d] = {k: mm.get(k) for k in ('batch', 'desc', 'rule_sha', 'blocks', 'pairs', 'digits', 'colour_values_matter', 'primitive', 'big_input_share', 'both_matter', 'components')}
    json.dump({'lane': 'breadth-compose', 'rules': man, 'distinct_rules': len(man), 'blocks': sum(v['blocks'] for v in man.values())}, open(os.path.join(out, '_MANIFEST-breadth.json'), 'w'), indent=1)
    return len(man), sum(v['blocks'] for v in man.values())

if __name__ == '__main__':
    N, SEED, OUT = int(sys.argv[1]), int(sys.argv[2]), os.path.abspath(sys.argv[3]); blocks = int(sys.argv[4]) if len(sys.argv) > 4 else 2; jobs = int(sys.argv[5]) if len(sys.argv) > 5 else 8
    os.makedirs(OUT, exist_ok=True); rng = random.Random(SEED); pool_names = [n for n in NAMES if n not in P4]
    left = [n for n in open(os.environ['COMPOSE_LEFT']).read().split() if n in H.RULES and n not in P4] if os.environ.get('COMPOSE_LEFT') else pool_names
    if os.environ.get('COMPOSE_LEFT'): print(f"left set: {len(left)} rules from {os.environ['COMPOSE_LEFT']}", flush=True)
    right = [n for n in open(os.environ['COMPOSE_RIGHT']).read().split() if n in H.RULES and n not in P4] if os.environ.get('COMPOSE_RIGHT') else []; right_p = float(os.environ.get('COMPOSE_RIGHT_P', '0.5'))
    if right: print(f"right bias: {len(right)} rules from {os.environ['COMPOSE_RIGHT']} drawn with p={right_p}, else any non-P4 rule", flush=True)
    pairs = []; seen = set()
    while len(pairs) < N:
        a = rng.choice(left); b = rng.choice(right) if right and rng.random() < right_p else rng.choice(pool_names)
        if a == b: continue
        if os.environ.get('COMPOSE_EITHER') == '1' and rng.random() < 0.5: a, b = b, a
        if (a, b) in seen: continue
        seen.add((a, b)); pairs.append((a, b, OUT, blocks))
    t0 = time.time(); cnt = collections.Counter(); done = 0
    with mp.Pool(jobs) as pool:
        for r in pool.imap_unordered(work, pairs, chunksize=4):
            cnt[r[2]] += 1; done += 1
            if done % 200 == 0: print(f"{time.strftime('%F %T')} {done}/{N} {dict(cnt)} elapsed {time.time()-t0:.0f}s", flush=True)
    nr, nb = manifest(OUT)
    print(f"{time.strftime('%F %T')} DONE {dict(cnt)} wall {time.time()-t0:.0f}s | manifest: {nr} compositions, {nb} blocks -> {OUT}", flush=True)
