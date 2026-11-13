#!/usr/bin/env python3
"""Seed generator for the agent driver: rewrite an existing invsqrt circuit with peephole passes.

Contract every generator must follow (the driver relies on it):
  python GENERATOR.py OUT.kmb      -> writes OUT.kmb, prints one JSON line of stats, exits 0
Inputs it may read: the env var VQCC_ROOT (repo root) and files under it. No network.

Passes here are deliberately simple and provably safe; the agent's job is to add better ones
(e.g. remove the 485 one-wire spikes at 46 live qubits, merge rotations, re-order to free a wire).
"""
import json, os, sys, tempfile
from pathlib import Path

import kickmix as km

ROOT = Path(os.environ.get('VQCC_ROOT', Path(__file__).resolve().parents[2]))
BASE = ROOT / 'frontier' / 'invsqrt.kmb'   # 46-qubit public frontier, ratio 26.37
SELF_INVERSE = {'X', 'CX', 'CCX', 'SWAP', 'CSWAP', 'Z', 'CZ', 'CCZ'}


def cancel_adjacent_pairs(lines):
    """Remove back-to-back identical self-inverse gates (same operands, same condition)."""
    out = []
    for ln in lines:
        op = ln.split(' ', 1)[0]
        if out and op in SELF_INVERSE and out[-1] == ln:
            out.pop()
        else:
            out.append(ln)
    return out


def main(dst):
    tmp = Path(tempfile.mkdtemp())
    km.Circuit.from_file(str(BASE)).to_file(str(tmp / 'in.kmx'))
    lines = [l.rstrip('\n') for l in open(tmp / 'in.kmx')]
    n0 = len(lines)
    lines = cancel_adjacent_pairs(lines)
    (tmp / 'out.kmx').write_text('\n'.join(lines) + '\n')
    c = km.Circuit.from_file(str(tmp / 'out.kmx'))
    c.to_file(dst)
    s = c.operation_statistics()
    print(json.dumps({'qubits': c.num_qubits, 'static_toffoli': s.num_toffoli_like,
                      'lines_removed': n0 - len(lines)}))


if __name__ == '__main__':
    main(sys.argv[1])
