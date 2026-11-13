#!/usr/bin/env python3
"""Measure the cost of kickmix's built-in building blocks -> catalog/components.csv.

This gives the agents a price list: "an n-bit quantum add costs X Toffolis and Y extra qubits",
so a proposed design can be costed before anyone writes it. Each component is built in isolation with
km.CircuitBuilder, and the static counts are read with operation_statistics(). Ancilla = qubits beyond
the registers the component acts on.

Usage: python tools/components.py
"""
import csv
from pathlib import Path

import kickmix as km

OUT = Path(__file__).resolve().parent.parent / 'catalog'
ROWS = []


def record(name, n, build):
    b = km.CircuitBuilder()
    try:
        io_qubits = build(b)
    except Exception as e:  # keep going; note which configurations the builder rejects
        print(f'skip {name} n={n}: {e}')
        return
    c = b.finish_circuit()
    s = c.operation_statistics()
    ROWS.append({'component': name, 'n': n, 'toffoli_like': s.num_toffoli_like, 't_like': s.num_t_like,
                 'qubits_total': c.num_qubits, 'io_qubits': io_qubits, 'ancilla': c.num_qubits - io_qubits,
                 'ops': len(c), 'reaction_depth': c.reaction_depth()})


def qadd(n):
    def f(b):
        a = b.create_quantum_register(n, 'a'); t = b.create_quantum_register(n, 't')
        b.iadd(a, target=t)
        return 2 * n
    return f


def cadd(n, k):
    def f(b):
        t = b.create_quantum_register(n, 't')
        b.iadd(k, target=t)
        return n
    return f


def ctl_qadd(n):
    def f(b):
        a = b.create_quantum_register(n, 'a'); t = b.create_quantum_register(n, 't'); c = b.create_quantum_register(1, 'c')
        b.iadd(a, target=t, control=c[0])
        return 2 * n + 1
    return f


def cmp_q(n):
    def f(b):
        a = b.create_quantum_register(n, 'a'); r = b.create_quantum_register(n, 'r'); t = b.create_quantum_register(1, 't')
        b.flip_if_less_than(a, r, target=t[0])
        return 2 * n + 1
    return f


def cmp_c(n, k):
    def f(b):
        a = b.create_quantum_register(n, 'a'); t = b.create_quantum_register(1, 't')
        b.flip_if_less_than(a, k, target=t[0])
        return n + 1
    return f


def lookup(addr_bits, width):
    def f(b):
        a = b.create_quantum_register(addr_bits, 'a'); t = b.create_quantum_register(width, 't')
        table = [(i * 2654435761) % (1 << width) for i in range(1 << addr_bits)]
        b.init_lookup(table=table, address=a, target=t)
        return addr_bits + width
    return f


def lookup_roundtrip(addr_bits, width):
    def f(b):
        a = b.create_quantum_register(addr_bits, 'a'); t = b.create_quantum_register(width, 't')
        table = [(i * 2654435761) % (1 << width) for i in range(1 << addr_bits)]
        b.init_lookup(table=table, address=a, target=t)
        b.del_lookup(table=table, address=a, target=t)
        return addr_bits + width
    return f


def gf2_mul(m):
    def f(b):
        fld = km.GF2Field(m)
        x = b.create_quantum_register(m, 'x'); y = b.create_quantum_register(m, 'y')
        b.init_gf2_mul(x, y, field=fld)
        return 3 * m  # inputs + product register
    return f


def main():
    for n in (8, 12, 16, 22, 24, 28, 32):
        record('iadd quantum', n, qadd(n))
        record('iadd classical const', n, cadd(n, (1 << (n - 1)) + 12345 % (1 << (n - 1))))
        record('controlled iadd quantum', n, ctl_qadd(n))
        record('less_than quantum', n, cmp_q(n))
        record('less_than const', n, cmp_c(n, 3 * (1 << (n - 2)) + 1))
    for a in (2, 4, 6, 8, 10):
        for w in (8, 16, 32):
            record(f'lookup init w={w}', a, lookup(a, w))
            record(f'lookup init+del(MBUC) w={w}', a, lookup_roundtrip(a, w))
    for m in (4, 6, 8, 12):
        try:
            record('gf2 mul (init)', m, gf2_mul(m))
        except Exception as e:
            print('gf2 mul', m, 'failed:', e)
    OUT.mkdir(exist_ok=True)
    with open(OUT / 'components.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(ROWS[0]))
        w.writeheader()
        w.writerows(ROWS)
    for r in ROWS:
        print(f"{r['component']:28s} n={r['n']:3d} T={r['toffoli_like']:5d} anc={r['ancilla']:3d} depth={r['reaction_depth']}")


if __name__ == '__main__':
    main()
