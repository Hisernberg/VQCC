#!/usr/bin/env python3
"""Index every circuit file under the given folders into catalog/circuits.{jsonl,csv}.

One row per unique SHA-256 (the same bytes under several names/datasets are merged, all paths kept).
Static stats only (cheap): qubits, bits, registers, instruction count, Toffoli-like / T-like / non-Clifford
Z_POW counts and reaction depth. Static Toffoli counts over-count circuits with classically-conditioned
blocks; the verifier's per-shot mean is the real cost (use loop/verify.py for that).

Usage: python tools/catalog.py frontier syed data/sample_submission [--max-mb 200]
"""
import argparse, csv, hashlib, json, lzma, os, sys, tempfile
from pathlib import Path

import kickmix as km

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'catalog'
EXTS = ('.kmb', '.kmx', '.kmb.xz', '.kmx.xz')


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def guess_task(path, regs):
    names = set(regs)
    if 'x' in names:
        return 'invsqrt'
    if any(n.startswith('S') and n[1:].isdigit() for n in names):
        return 'dqi'
    p = path.lower()
    if 'angle' in p:
        return 'dfthcsos'
    if 'dqi' in p:
        return 'dqi'
    if 'invsqrt' in p:
        return 'invsqrt'
    return 'unknown'


def stats_for(raw, suffix):
    with tempfile.NamedTemporaryFile(suffix=suffix) as f:
        f.write(raw)
        f.flush()
        c = km.Circuit.from_file(f.name)
    s = c.operation_statistics()
    regs = {str(k): len(v) for k, v in c.register_data.items()}
    return {
        'num_qubits': c.num_qubits, 'num_bits': c.num_bits, 'num_registers': c.num_registers,
        'registers': regs if len(regs) <= 12 else {'_count': len(regs)},
        'num_ops': len(c), 'toffoli_like_static': s.num_toffoli_like, 't_like_static': s.num_t_like,
        'z_pow_nonclifford': s.num_z_pow(min_clifford_hierarchy_level=4),
        'reaction_depth': c.reaction_depth(), '_regnames': list(regs),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dirs', nargs='+')
    ap.add_argument('--max-mb', type=float, default=200, help='skip loading files larger than this (hash only)')
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    jl = OUT / 'circuits.jsonl'
    rows = {}
    if jl.exists():
        for line in jl.read_text().splitlines():
            r = json.loads(line)
            rows[r['sha256']] = r
    for d in a.dirs:
        for p in sorted(Path(d).rglob('*')):
            if not p.is_file() or not p.name.endswith(EXTS):
                continue
            raw = p.read_bytes()
            if p.name.endswith('.xz'):
                raw = lzma.decompress(raw)
            h = sha256_bytes(raw)
            rel = os.path.relpath(p, ROOT)
            if h in rows:
                if rel not in rows[h]['paths']:
                    rows[h]['paths'].append(rel)
                continue
            r = {'sha256': h, 'short': h[:8], 'paths': [rel], 'bytes': len(raw)}
            if len(raw) <= a.max_mb * 2**20:
                try:
                    st = stats_for(raw, '.kmx' if '.kmx' in p.name else '.kmb')
                    r['task'] = guess_task(rel, st.pop('_regnames'))
                    r.update(st)
                except Exception as e:  # unreadable file: keep the hash, record why
                    r['error'] = str(e)[:300]
            else:
                r['task'] = guess_task(rel, [])
                r['skipped'] = f'> {a.max_mb} MB'
            rows[h] = r
            print(f"{r.get('task','?'):9s} {h[:8]} q={r.get('num_qubits','-')} T={r.get('toffoli_like_static','-')} {rel}")
    with open(jl, 'w') as f:
        for r in rows.values():
            f.write(json.dumps(r) + '\n')
    cols = ['task', 'short', 'num_qubits', 'toffoli_like_static', 't_like_static', 'z_pow_nonclifford',
            'num_ops', 'reaction_depth', 'bytes', 'paths']
    with open(OUT / 'circuits.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in sorted(rows.values(), key=lambda r: (r.get('task', ''), r.get('num_qubits') or 0)):
            w.writerow([';'.join(r[c]) if c == 'paths' else r.get(c, '') for c in cols])
    print(f'{len(rows)} unique circuits -> {jl}')


if __name__ == '__main__':
    main()
