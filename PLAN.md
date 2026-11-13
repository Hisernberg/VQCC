# Google Quantum AI – Verifiable Quantum Circuit Compilation: status and plan

*Snapshot: 2026-11-13 ~19:15 UTC. Competition: `google-verifiable-quantum-circuit-compilation`.*

## 1. Where you stand

| | Value |
|---|---|
| Your best public LB | **25.09022** (2026-11-07, a re-pack of maoxin's public build) |
| Your rank | ~1309 / 3000 |
| Submissions so far | 19 (Oct 28 – Nov 7). None in the last 6 days |
| Leader | 29.90871 (Entangled Team), then 29.76, 29.31, 29.09, 29.07 |
| Rank 10 / 20 / 50 / 100 / 500 | 27.996 / 27.538 / 27.308 / 27.290 / 27.108 |
| Big ties on the board | 180 teams at 27.11, 165 teams at 27.29 (all the same public notebooks) |

All 19 of your submissions are byte-pins or recombinations of public notebooks. None has an original circuit in it.
That's why the score went up only when the public frontier did. The frontier has since moved
from ~25.0 to **27.29**, so you are now ~2.2 points behind what anyone can download.

## 2. The public frontier (27.29) per task

GM = (r_invsqrt · r_dqi · r_chem)^(1/3); r = reference cost / your cost.

| Task | Best public file | Qubits | Cost | Ratio | Main idea that got there |
|---|---|---:|---:|---:|---|
| invsqrt | `4560ac0c` (Syed Asad Ali generator, ahoirg 64-row table build) | 46 | ~78,766 | 26.37 | Normalize in place → in-place sqrt (12-bit root + 10-bit remainder) → short division; 33 rotations; measurement-based (HMR) uncompute; classically controlled fix-ups |
| dqi | `821bf8d1` (Syed v12 decoder, extractor cutoff 18 by ozertuu, 241 retained products by areebbb) | 889 | 3.602e11 (≈382.6k Toffoli/shot) | 67.85 | Continued-fraction (Schur/Thiele) decoder instead of Berlekamp–Massey; GF(2^12)=GF(4)^6 multiply in 42 Toffolis (14-product bilinear); product caching/retention; weight cutoff (stop decoding weights that are too rare to matter); HMR cleanup |
| dfthcsos | maoxin123 coded-word (8, 143, 44) table + 15 loaders at 4,044 AND/pass, W/H2_I refit | 427 | ~2.954e8 | 11.36 | Compact DF-THC shape, 8-bit angles, loaders storing codes on XOR of 5 words, Reed–Muller constraints on low word bits, joint L-BFGS refit of W/H2_I inside the 20 mHa limits |

Score sensitivity: improving any one task by 5% / 10% / 20% / 32% adds +0.45 / +0.88 / +1.71 / +2.65 to the GM.
The leader (29.91) is 1.316× better than the public frontier in the product of ratios. For example: 10% on each task, or ~32% on one.

## 3. What the forum and the notebooks tell you

- **The winning pattern is a fast build → verify → keep/discard loop**, not one-shot prompting. Everyone runs the unmodified official verifiers locally before submitting.
- **Algorithm changes beat polishing.** The invsqrt 62→46-qubit jump (−14% cost) came from a new algorithm, after weeks of agents polishing the 62-qubit design for tiny gains.
- **invsqrt: one qubit is worth about 38 Toffolis** (cost = Q × T_eq). The 46-qubit circuit sits at 45 live wires almost all the time and needs a 46th wire at 485 short spikes. Removing those spikes (in-place carries, borrowed/dirty ancillas, re-ordering) is a concrete target worth ~2%. A different algorithm that runs at ≤40 wires would be worth much more.
- **dqi: the score squares the qubits** (Q² × T × repetition factor). A 1% cut in qubits is worth a 2% cut in Toffolis. The DQI score is **salt-dependent**: one failed shot out of 102,400 costs about −0.04 GM, so people "hedge" by trying several builds.
- **dfthcsos: the best entries sit on the accuracy limits** (20 mHa, gap and norm floors). The remaining gains are in cheaper loaders and in co-optimizing λ with the table. Watch thread 755427 ("Final evaluation scope"): loaders that are only correct on the reachable word states pass the verifier, and the organizers have not yet said whether that will be allowed at the end. Don't build your score on that loophole.
- **Local models can work.** One competitor runs Qwen3.8-Flash-Next on 2× RTX 5070 Ti in an overnight harness and reports chemistry gains of ~5% over public (thread 752949).
- **Licensing/credit.** Most public builds are Apache-2.0 with credit lineages. Prize winners must deliver source (thread 752010), so keep your own generators, not only .kmb files.

## 4. Plan

### Phase 0 – today (≈1 h): get onto the frontier
1. Fork **heliosli/the-dataset-is-public-now-enjoy** (27.29, re-verifies all files with the official verifiers) or **syed3000/vqcc-own-circuit-portfolio-notebook** (builds everything from source). Run it and submit. You go from 25.09 → ~27.29 (rank ~1300 → ~100–260, in the tie).
2. Rotate every token you pasted in chat (see the end of this document).

### Phase 1 – Nov 14–16: build your own loop (the most important step)
1. Local workspace: `pip install kickmix` (now on PyPI), the competition `verifiers/`, Syed's source dataset (`syed3000/vqcc-own-circuit-portfolio`) and maoxin's chemistry (`maoxin123/qcc-v25-coded-word-chemistry`).
2. One script per task: `build → official verifier → cost → append to results.jsonl → keep if better`. Quick checks first (subset or reduced shots), the full official verifier only for candidates that might be kept.
3. Pin every candidate by SHA-256 and store the generator source next to it (you'll need it to claim a prize).
4. Put the loop under an agent harness (Claude Code / Codex as the "brain", a local or free open model as the overnight worker). Give it a journal file and a hard rule: a result only counts if the untouched official verifier says PASS.

### Phase 2 – Nov 16 → mid-Dec: pick one task and go deep
Don't spread across all three. Choose by your strengths:

- **invsqrt (smallest, fastest loop: best place to start).**
  (a) Remove the 485 one-wire spikes in Syed's 46-qubit circuit → 45 qubits (≈ −2%).
  (b) Try qubit-lean algorithm families: in-place digit-by-digit (restoring/non-restoring) sqrt fused with the division; table + one Newton step with a phase-gradient register; split 1/√x into a QROM-loaded coarse phase plus a low-degree fine phase that adds straight into the phase (no product kept, so there is nothing to un-multiply).
  (c) Cut rotations: every rotation is priced in T gates, so merge phase terms and reuse the phase-gradient adder.
- **dqi (largest headroom in absolute terms; heavy files, ~500 MB, slow verifies).**
  (a) Qubits first (Q² in the cost): in-place syndrome updates, shared field-multiplier workspace.
  (b) Fewer Toffolis per GF(2^12) multiply/square (squaring is linear over GF(2): it should be free), reuse of retained products.
  (c) Tune the weight cutoff against the repetition factor using the official input law (paper Eq. 43).
- **dfthcsos (classical optimization: good if you're strong in numerical optimization).**
  (a) Re-run the factorization with λ_eff as the objective and the accuracy limits as hard constraints (L-BFGS / augmented Lagrangian; symmetry shift Hsym).
  (b) Co-design the angle table with the loaders (Reed–Muller / coded words, fewer distinct words, 7-bit angles where the error budget allows).
  (c) Fewer, cheaper loaders (4,044 → <4,000 AND/pass).

### Phase 3 – mid-Dec → Jan 20: harden and hedge
- Run every final candidate through the full official verifier several times with different salts.
- For DQI, keep 2–3 builds with the same cost and pick finals that don't share a failure mode.
- Final selection: one "safe" (fully verified, no loophole) and one "max" submission.
- Team merger deadline is **Jan 13**. If you have one strong task, merging with a team strong on another task is the fastest GM gain.

### Prize notes
- **Mid-competition milestone (Nov 20, 7 days away)** requires the highest public LB *and* a public notebook. The leader is at 29.91. Not realistic from 25.09; don't chase it.
- **Single-task prizes ($10k each)** are judged per task. Going deep on one task (Phase 2) is the right strategy for them too.

## 5. Must-read papers (verified arXiv IDs), ranked by usefulness here

**Read first**
1. **Khattar et al., arXiv:2610.23832**: the companion paper and the contract for all three tasks (also `data/verifiable_circuit_compilation.pdf`). The authors' own Gemini agent circuits are hash-committed and will be released after the competition.
2. **Gu, Kemeny, Yelin, Lukin, arXiv:2610.22367**, "Discovering state-of-the-art quantum circuits with LLMs" (OpenEvolve). Reports DQI RS decoding at 12× (Berlekamp–Massey with a rescaled update, phase-only Forney at 23 Toffoli/position, half-degree EEA for 1/σ′, linear phase absorbed into Clifford Z) and a Coulomb 1/√x-type task at 9.9× (128 linear segments keyed by exponent parity plus the top 6 mantissa bits, MBUC-erased lookup). **Code: github.com/andigu/uncompute** (Apache-2.0; needs porting to kickmix).
3. **Shirobokov et al. (DeepMind/GQAI), arXiv:2611.09822**, "Discovering formally verified quantum programs with AI" (Lean, fusion task 11×).
4. **Babbush et al., arXiv:2603.28846** (origin of kickmix) and **Long et al., arXiv:2609.28882** (ecdsa.fail community record-and-replay arithmetic, about 2× fewer Toffolis).

**invsqrt / arithmetic**
- Rubin et al., stopping power, 2308.12352
- Su et al., first quantization, 2105.12767
- Sanders et al., 2007.07391 (inverse-sqrt costing)
- Häner–Roetteler–Svore, 1805.12445
- Gidney, halving addition, 1709.06648 (temporary AND)
- Gidney, windowed arithmetic, 1905.07682
- Khattar–Gidney, conditionally clean ancillae, **2407.17966** (directly relevant to the 46→45 qubit spikes)
- Kliuchnikov et al., rotation synthesis, 2203.10064 (the verifier's rotation price)
- Sanders et al., black-box state preparation, 1807.03206

**dqi / Reed–Solomon**
- Jordan et al., DQI, 2408.08292
- Khattar et al., optimized DQI, 2510.10967
- Proos–Zalka, quant-ph/0301141
- Roetteler et al., 1706.06752
- Häner et al., 2001.09580
- Litinski, 2306.08585
- Bernstein–Yang divsteps (constant-time GCD)
- Note: the field is GF(2^12) (α¹²+α⁶+α⁴+α+1), RS [4095, 4025, 71], decoding ℓ=35 errors. Squaring is GF(2)-linear (no Toffolis).

**dfthcsos / chemistry**
- **Low et al., PRX 2025, 2502.15882** (DF/THC hybrid, spectrum amplification, SOS shift: this is the cost model)
- Lee et al., THC, 2011.03494
- von Burg et al., DF, 2007.14460
- Reiher et al., FeMoCo, 1605.03590
- Berry et al., 1902.02134
- Babbush et al., 1805.03662
- Low–Kliuchnikov–Schaeffer, SELECT-SWAP QROAM, 1812.00954
- Oumarou et al., 2212.07957
- Rocca et al., 2403.03502
- Loaiza & Izmaylov, 2304.13772
- Loaiza et al., 2208.08272
- Caesura et al., 2501.06165

**Agentic search**
- AlphaEvolve, 2506.13131
- AlphaTensor-Quantum, 2402.14396
- ShinkaEvolve, 2509.19349
- FunSearch (Nature 2023)

## 6. Repos

| Repo | Why |
|---|---|
| quantumlib/Qualtran (`kickmix/`, `docs/kickmix/`) | Simulator, .kmx format, `CircuitBuilder` primitives (`init_and`/`del_and`, `init_lookup`, `iadd`, `gf2_*`, `unary_iteration`) |
| andigu/uncompute | Gu et al. circuits and graders for DQI-RS and Coulomb: the closest published prior art to tasks I and II |
| quantumlib/OpenFermion `resource_estimates/{df,thc}` | DF/THC factorization and costing code for task III |
| algorithmicsuperintelligence/openevolve, SakanaAI/ShinkaEvolve | Ready-made evolutionary LLM search loops; plug the official verifier in as the fitness function |
| google-deepmind/alphaevolve_results | Reference for the prompt/program-database pattern |
| ecdsafail/ecdsafail-challenge | The predecessor harness, with lessons on salt and verification |
| Kaggle datasets: `syed3000/vqcc-own-circuit-portfolio` (full source of the 27.0 builders), `heliosli/qcc-circuits-live` (27.29 files), `manwithacat/vqcc-apache-public-circuits` (5 GB archive of all public circuits), `manwithacat/vqcc-chemistry-negative-results` (what didn't work), `kirderf/vqcc-dqi-cutoff-variants` | |

## 7. Models for the agent loop

There is **no official "Qwen 4"** yet; only an experimental `qwen4_exp` architecture exists. Real options as of Nov 2026:

| Model | Size | Where it runs | Use |
|---|---|---|---|
| Qwen/Qwen3.8-Flash-Next | 180B MoE | vast.ai 2×48–80 GB GPUs, or API | The model a competitor used for the overnight chemistry loop (thread 752949) |
| Qwen/Qwen3.8-27B (Apache-2.0) | 27.8B dense | One 24–32 GB GPU at Q4/FP8; Cerebras via HF providers | Best single-GPU worker |
| DeepSeek-V4.1-Flash (MIT) | 763B | API (NVIDIA NIM free tier) | Strong reasoning/math "brain" |
| GLM-5.3, Kimi-K3.1-Pro, MiniMax-M3.1-Flash | 0.7–2.8T | API (NIM / OpenRouter) | Second opinions, diversity in evolution |
| gpt-oss-120b / 20b | 120B / 20B | Groq/Cerebras free; 20b fits a T4 | Fast cheap mutations |
| Devstral-2-123B / Devstral-Small-2-24B | | Small fits one GPU at Q4 | Coding-specialised |
| gemma-4-26B-A4B / 31B | | OpenRouter free; fits 2×T4 at Q4 | Cheap worker |

**Budget advice ($10–20 on vast.ai):** that's roughly 25–50 h of an RTX 4090/5090, or 6–10 h of an H100. The circuits are verified on **CPU**, not GPU. Spend most of it on a **many-core CPU box** (32–64 vCPU, ≈$0.2–0.5/h) to run verifiers in parallel. Use free APIs (NIM, Groq, Cerebras, OpenRouter `:free`) for the LLM. Rent a GPU only if you want Qwen3.8-27B running locally overnight without rate limits.
