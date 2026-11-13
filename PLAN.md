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

### Phase 1 – Nov 14–16: run the loop on free compute (the most important step)
The toolkit is built (section 8). What's left:
1. Upload the toolkit as a private Kaggle dataset: `tools/make_kaggle_dataset.sh`.
2. Push `kaggle/runner/` as a private Kaggle notebook: `kaggle kernels push -p kaggle/runner`. Its first run is a dry run that benchmarks the official build against the fast kickmix build on Kaggle's CPU.
3. Get one free LLM key (NVIDIA NIM is the most generous) and add it as Kaggle Secrets (`VQCC_PROVIDER=nim`, `VQCC_MODEL=…`, `NVIDIA_API_KEY=…`). Every notebook run is then a 40-iteration agent session.
4. Run `tools/drift.py` once a day to catch new public circuits. Every new frontier file is a new seed.
5. Rule: only the **official kickmix build plus the untouched verifier** decides what gets submitted. The fast build is for screening.

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
| Qwen/Qwen3.8-Flash-Next | 180B MoE | API only on free compute (too big for 2×T4) | The model a competitor used for the overnight chemistry loop (thread 752949) |
| Qwen/Qwen3.8-27B (Apache-2.0) | 27.8B dense | One 24–32 GB GPU at Q4/FP8; Cerebras via HF providers | Best single-GPU worker |
| DeepSeek-V4.1-Flash (MIT) | 763B | API (NVIDIA NIM free tier) | Strong reasoning/math "brain" |
| GLM-5.3, Kimi-K3.1-Pro, MiniMax-M3.1-Flash | 0.7–2.8T | API (NIM / OpenRouter) | Second opinions, diversity in evolution |
| gpt-oss-120b / 20b | 120B / 20B | Groq/Cerebras free; 20b fits a T4 | Fast cheap mutations |
| Devstral-2-123B / Devstral-Small-2-24B | | Small fits one GPU at Q4 | Coding-specialised |
| gemma-4-26B-A4B / 31B | | OpenRouter free; fits 2×T4 at Q4 | Cheap worker |

**Free-only rule:** no rented machines. LLM calls go to free API tiers. Small models run on Kaggle's free GPUs. Verifiers run on Kaggle's free CPUs (section 8).

## 8. Free-only infrastructure and our own toolkit

### Free compute (no rented machines)
| Resource | What you get (check your Kaggle quota page, since limits change) | Use it for |
|---|---|---|
| Kaggle CPU notebook | 4 vCPU, ~30 GB RAM, up to 12 h per session, runs in the background after "Save & Run All" | Verifier loops, agent driver (`kaggle/runner`) |
| Kaggle GPU (T4×2 or P100) | Weekly GPU-hour quota (≈30 h) | A local LLM worker (Qwen3.8-27B Q4, gpt-oss-20b, Devstral-Small-24B) served by llama.cpp/vLLM on `127.0.0.1:8000` → `--provider local` |
| Kaggle TPU VM | Weekly TPU quota (≈20 h). TPU host VMs usually have many more CPU cores | **Test this:** run the runner with TPU enabled and read its `nproc`. If it shows dozens of cores, it's the cheapest big verifier box you can get |
| GitHub Actions (private repo) | ~2,000 free minutes/month on 2-core runners | Nightly `tools/drift.py` snapshot + quick checks |
| Google Colab free | ~2 vCPU, sometimes a T4 | Spare worker |
| This cloud session | 4 vCPU (AVX-512) | Building wheels, development, full verifies |
| Free LLM APIs | NVIDIA NIM (DeepSeek-V4.1-Flash, MiniMax-M3.1-Flash, Kimi-K2.6, GLM-5.3-Flash, gpt-oss), Groq (gpt-oss-20b/120b), Cerebras (Qwen3.8-27B, gpt-oss-120b), OpenRouter `:free` (Nemotron-3-Ultra, Gemma-4), Gemini free tier | The driver's "brain" (`--provider nim/groq/cerebras/openrouter/gemini`) |

Rotate providers when one rate-limits you; the driver backs off and retries automatically.

### Toolkit built in this repo
| Piece | File | What it does |
|---|---|---|
| Verify harness | `loop/verify.py` | Official verifier → JSON → `results.jsonl` (with SHA-256) → keeps the best in `best/` |
| Agent driver | `loop/driver.py` | LLM proposes a generator change → build in a sandboxed subprocess → quick verify → full verify → keep/discard → `runs/<task>/journal.jsonl`. Works with any OpenAI-compatible endpoint, free APIs or a local model |
| Seed + brief | `loop/seeds/invsqrt_peephole.py`, `loop/prompts/invsqrt.md` | Starting generator (rewrites the 46-qubit frontier circuit) and the task contract the LLM reads |
| Drifter | `tools/drift.py` | Daily snapshot of leaderboard, notebooks, datasets and topics, plus a `REPORT.md` diff of what moved |
| Circuit catalog | `tools/catalog.py` → `catalog/circuits.csv` | Indexes every circuit file by SHA-256 with static stats |
| Component price list | `tools/components.py` → `catalog/components.csv` | Toffoli and ancilla cost of kickmix building blocks (adders, comparators, lookups, GF(2) multiplies) so designs can be costed before they're written |
| Optimized kickmix wheels | `tools/build_native_kickmix.sh`, `tools/install_kickmix.py` | The PyPI wheel is compiled with `-mno-avx` (SSE only). Our builds enable AVX2 (`x86-64-v3`) / AVX-512 (`x86-64-v4`). Same verifier result, bit for bit, on the invsqrt frontier; the native build runs the full verify ~19% faster here. The installer picks the fastest build the CPU supports |
| Kaggle dataset | `tools/make_kaggle_dataset.sh` → private `kragglenote2forwork/vqcc-toolkit` | Everything above plus the wheels, refusing to upload anything that looks like a credential |
| Kaggle worker | `kaggle/runner/` | Private CPU notebook: installs the fast wheel, checks it against the official build, then runs the driver with keys from Kaggle Secrets |

## 9. Kaggle discussions worth reading
Base URL: `https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/discussion/<id>`

| id | Topic | Why |
|---|---|---|
| 753307 | kickmix is now on PyPI | Official install path (stickied) |
| 750817 | How to get started + official Discord | Organizer links |
| 755427 | Final evaluation scope: published verifier or extra checks? | **Risk:** reachable-state-only ANGLE loaders pass the verifier. Watch for an organizer answer |
| 752010 | Winner source-delivery requirements | Keep generator source for every submitted file |
| 758815 | First public 27+ notebook, from source (Syed) | The base our toolkit seeds from |
| 756476 | Two exact finite-field multiplication complexities, with proofs | DQI GF(2^12) multiply lower bounds (42 Toffolis optimal for that approach) |
| 753607 | DQI: the baselines ratio 60.11 | How DQI's cost and repetition factor behave |
| 753403 | An interactive look inside the invsqrt circuit | Circuit anatomy |
| 754970 | Free introductory guide to FTQC circuit optimization | Background |
| 752949 | Room for local models: one-person setup | Qwen3.8-Flash-Next overnight harness, ~5% chemistry gain |
| 757915 | Fable 5.2 is an expensive beast | Cost of frontier-model agents |
| 757471 | DeepMind paper: formally verified quantum programs (2611.09822) | |
| 754652 | What to learn from this competition | Agent-management lessons |
| 752550 | What are you scoring in each task? | Per-task numbers from others |
| 751968 | Can we have a per-task leaderboard? | |

## 10. Kaggle notebooks and datasets worth forking or reading

**Notebooks** (`https://www.kaggle.com/code/<ref>`)

| Ref | Why |
|---|---|
| heliosli/the-dataset-is-public-now-enjoy | **27.29 frontier**, re-verifies with official verifiers. Submit this first |
| syed3000/vqcc-own-circuit-portfolio-notebook | Rebuilds all three circuits **from source** (27.0) |
| areebbb/qai-fewer-toffolis-same-qubits-lb-27-11042 | DQI cutoff ladder with exact excluded probabilities, product-retention proof harness |
| maoxin123/qcc-v25-coded-word-chemistry | Coded-word chemistry table + 4,044-AND loaders (CC0) |
| atakanaldemir/quantum-circuits-iso-gap-dqi-h5 | Joint W/H2_I refit with L-BFGS + Schur chart |
| mizeroluckygall/quantum-circuits-4044-toffoli-chemistry-guide | Plain-language walkthrough of the 27.29 portfolio |
| sheroleg/quantum-circuits-from-zero-1-sqrt-x-explained | Best invsqrt explainer: 46-qubit anatomy, the 485 one-wire spikes |
| ozertuu/quantum-ai-27-083-vqcc-dqi-cutoff-17 | DQI extractor-cutoff idea |
| kirilltym/quantum-circuits-retained-product-audit, …-conditional-uncompute-audit, …-pi-gauge-weight-refinement | Careful audits of the main techniques |
| prvsiyan/verifier-guided-quantum-circuit-optimization | Verifier-in-the-loop pattern, refit code |
| orecord/quantum-circuit-compilation-pipeline | Independent from-source pipeline (curvature-interpolation invsqrt, THC chemistry) |
| manwithacat/vqcc-hedge-wizardry-notebook | How to hedge the salt-dependent DQI draw |
| sohier/verifiable-circuit-compilation-starter, metric/google-quantum-ai-metric | Official starter and the scoring code |

**Datasets** (`https://www.kaggle.com/datasets/<ref>`)

| Ref | Why |
|---|---|
| heliosli/qcc-circuits-live | The 27.29 circuit files (attached to our runner) |
| syed3000/vqcc-own-circuit-portfolio | Full builder sources for all three tasks |
| manwithacat/vqcc-apache-public-circuits | ~5 GB archive of public circuits |
| manwithacat/vqcc-chemistry-negative-results | What did **not** work in chemistry |
| manwithacat/vqcc-modular-circuit-parts | Reusable parts catalogue |
| kirderf/vqcc-dqi-cutoff-variants | DQI cutoff 15–20 builds |
| prvsiyan/vqcc-verified-best-of-circuits-1106a | Salt-tested circuits |
| sohier/verifiable-circuit-compilation-starter-kit | Official dfthcsos starter kit |

## 11. Open quantum libraries and components

| Library | Use here |
|---|---|
| **kickmix** (`pip install kickmix`, source in quantumlib/Qualtran/kickmix) | The simulator and `CircuitBuilder` primitives: `init_and`/`del_and` (temporary AND), `init_lookup`/`del_lookup` (QROM with measurement-based uncompute), `iadd`/`isub`, `flip_if_less_than`, `left_rotate`, `unary_iteration`, `init_gf2_mul`, `gf2_imul`, `init_gf2_inverse`, `gf2_phase_by_product` |
| **Qualtran** (quantumlib/Qualtran) | Bloqs and resource counts: `bloqs/arithmetic`, `bloqs/chemistry/{df,thc}`, `bloqs/chemistry/trotter/grid_ham/inverse_sqrt.py` (invsqrt reference), `bloqs/data_loading` (QROM/QROAM/select-swap) |
| **OpenFermion** `resource_estimates/{df,thc,sf}` | DF/THC factorization and costing code for task III |
| **PySCF** | Reading the FeMoCo FCIDUMP; integral manipulation for refactorization |
| **Cirq** | Circuit utilities (not needed for scoring) |
| **andigu/uncompute** | Gu et al. circuits and graders (DQI-RS, Coulomb), the closest prior art |
| **OpenEvolve / ShinkaEvolve** | Off-the-shelf evolutionary LLM loops; `loop/driver.py` is a minimal version you control |
| **Stim** | Not needed; design reference for fast bit-sliced simulation |
