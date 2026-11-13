#!/usr/bin/env python3
"""Run an official verifier on a candidate circuit, log the result, and keep the best.

Usage:
  python loop/verify.py invsqrt path/to/invsqrt.kmb [--quick] [--note "what changed"]
  python loop/verify.py dqi     path/to/dqi.kmb     [--quick] [--note ...]

--quick runs fewer shots for fast rejection. Only a full run (no --quick) can replace best/<task>.kmb.
Every run is appended to results.jsonl with the file's SHA-256, so any LB number can be traced to bytes.
"""
import argparse, hashlib, json, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERIFIERS = {
    'invsqrt': (ROOT / 'data/verifiers/invsqrt/verify_submission_invsqrt.py', ['--shots-per-x', '64'],
                # quick: every x 4 times (num_shots must divide batch_size; 4*3133452 = 16*783363)
                ['--shots-per-x', '4', '--batch-size', '16']),
    'dqi': (ROOT / 'data/verifiers/dqi/verify_submission_dqi.py', [], ['--num-shots', '10240']),
}
# Reference costs (score = ref_cost / cost). invsqrt ref from the paper: Q=260, C=7988 -> ~2.0768e6.
REF = {'invsqrt': 2076774.23, 'dqi': 24439463583672.93}


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('task', choices=VERIFIERS)
    ap.add_argument('circuit')
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--salt', default='')
    ap.add_argument('--note', default='')
    a = ap.parse_args()

    script, full_args, quick_args = VERIFIERS[a.task]
    cmd = [sys.executable, str(script), a.circuit] + (quick_args if a.quick else full_args)
    if a.salt:
        cmd += ['--salt', a.salt]
    t0 = time.time()
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    try:
        res = json.loads(out[out.index('{'):])
    except ValueError:
        res = {'status': 'FAIL', 'error': out[-2000:]}
    rec = {
        'time': time.strftime('%Y-%m-%dT%H:%M:%S'), 'task': a.task, 'file': a.circuit,
        'sha256': sha256(a.circuit), 'quick': a.quick, 'salt': a.salt, 'note': a.note,
        'seconds': round(time.time() - t0, 1), 'result': res,
    }
    score = res.get('score') or res.get('cost')
    if res.get('status') == 'PASS' and score:
        rec['ratio'] = REF[a.task] / score
    with open(ROOT / 'results.jsonl', 'a') as f:
        f.write(json.dumps(rec) + '\n')

    best_meta = ROOT / 'best' / f'{a.task}.json'
    if res.get('status') == 'PASS' and not a.quick and score:
        prev = json.loads(best_meta.read_text())['score'] if best_meta.exists() else float('inf')
        if score < prev:
            best_meta.parent.mkdir(exist_ok=True)
            shutil.copy(a.circuit, ROOT / 'best' / f'{a.task}.kmb')
            best_meta.write_text(json.dumps({'score': score, 'sha256': rec['sha256'], 'note': a.note}))
            rec['new_best'] = True
    print(json.dumps({k: rec[k] for k in rec if k != 'result'} | {'status': res.get('status'), 'score': score}, indent=1))


if __name__ == '__main__':
    main()
