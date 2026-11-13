# Task brief: invsqrt (Benchmark I)

You are improving a Python **generator** that writes a kickmix circuit file.

## Contract the circuit must meet (checked by the official verifier, no exceptions)
- One input register named `x`: 22 qubits, little-endian, x in [1, 3,133,452]. Must be restored.
- Effect: |x>|0> -> exp(2*pi*i / sqrt(x)) |x>|0>. Phase error per x must be <= 2^-24 / sqrt(x) turns.
- Every other qubit is scratch and must end in |0>. Every x is run 64 times with seeded HMR/R outcomes.
- Cost = Q * (mean Toffoli-like per shot + T/4). Each non-Clifford Z_POW costs
  0.56*log2(1/eps) + 5.3 T, with eps set by the error margin left over (about 28 T each now).
- Lower cost is better. Score ratio = 2,076,774.23 / cost.

## Current frontier (what you start from)
- 46 qubits, 1,480.75 mean Toffolis, 33 rotations -> 1,712.3 Toffoli-eq, cost 78,765.6 (ratio 26.37).
- At 1,712 Toffoli-eq per qubit, removing ONE qubit is worth ~37 Toffolis. Removing one rotation is worth ~7 Toffoli-eq.
- The circuit sits at 45 live wires most of the time and touches a 46th wire in ~485 short spikes
  (usually one Toffoli target or a second ripple-adder carry).

## Ideas worth trying (one per attempt)
1. Eliminate 46-wire spikes: temporary-AND with HMR uncompute (Gidney 1709.06648), conditionally clean
   ancillae (Khattar–Gidney 2407.17966), borrow a dirty wire that is idle at that moment, reorder gates.
2. Merge or remove Z_POW rotations: sum phase contributions on the same wire, absorb Clifford parts.
3. Peephole: cancel gate pairs separated by gates that commute with them; fold X into controls.
4. Bigger: a different algorithm with fewer live wires (Gu et al. 2610.22367: 128 linear segments keyed by
   exponent parity + top mantissa bits, lookup erased by measurement).

## How to answer
Return exactly:
1. A line `HYPOTHESIS: <one sentence: what you change and the expected cost effect>`
2. ONE complete Python file in a ```python block. It keeps the same CLI: `python gen.py OUT.kmb` writes the
   circuit and prints one JSON stats line. Only use `kickmix`, `numpy` and the standard library. No network.
