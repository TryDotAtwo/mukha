# Retina RNG memory design gate (2026-09-24)

This is a **proposal**, not a replacement implementation or a speed claim.
The grouped-state GPU attempt is rejected in
`GROUPED_RETINA_ARCHITECTURE_REVIEW.md`. This design keeps one independent
microvillus trajectory per element and preserves the source reaction equations.
It changes only how uniform random numbers are generated and checkpointed.

## Current data and measured control

The full retina has 3,377 × 30,000 = **101,310,000** microvilli. The current
native source keeps seven molecular counts in 14 bytes, a 2-byte receptor
owner, and a 48-byte `curandStateXORWOW_t` per element. The persistent hot
arrays therefore occupy about 6.48 GB: 1.42 GB molecules, 0.20 GB owner,
and 4.86 GB RNG state. Reading and writing each once implies 12.97 GB of
logical global-memory traffic per 0.1 ms tick, before caches, extra loads,
and reduction. This is a **traffic model**, not a DRAM measurement.

The target Molab GPU is RTX PRO 6000 Blackwell Server Edition. NVIDIA lists
1,597 GB/s peak memory bandwidth, so the model's ideal read/write floor is
8.12 ms per tick. The measured source transduction stage was 1,565.7 ms for
100 ticks, or 15.66 ms per tick. Peak bandwidth and a logical-byte model do
not establish the actual bottleneck, but the 48-byte RNG state merits a
target-hardware experiment. [NVIDIA product specifications](https://www.nvidia.com/en-us/data-center/rtx-pro-6000-blackwell-server-edition/).

## Proposed semantic change

Use a counter-based Philox generator keyed by fixed experiment seed,
microvillus ID, global neural tick, and draw index within that tick. The draw
index lives in registers during the kernel; it resets at each tick. A tick
boundary checkpoint then needs seed and tick, not a per-element RNG state.
The molecular arrays and 2-byte owner remain unchanged for the first A/B,
so this tests one data-plane change. The source waiting-time and reaction
selection rules remain unchanged, including draws that lead to null events.

Philox is a supported counter-based generator family in NVIDIA cuRANDDx,
including SM120. Its use here is still a **proposal**; the installed Molab
toolkit/dependencies and generated instruction cost need a local feature
probe. [NVIDIA cuRANDDx generator reference](https://docs.nvidia.com/cuda/curanddx/api/description_ops.html).

The active Molab runtime was checked: CUDA 13.1.115 and driver 595.71.05 are
present, but no cuRANDDx header or package was found. The pinned CUDA 13.1
`curand_philox4x32_x.h` does expose `curand_Philox4x32_10(uint4,uint2)`.
This is an implementation-header function, so any candidate using it must
pin the exact header/toolkit, keep known-answer vectors, and reject a changed
build identity. Repeating `curand_init` for all 101.31 million elements
every tick is **not** the proposed path: NVIDIA's cuRAND guide warns that
initialization is costlier than draws and recommends state reuse when using
that API. [NVIDIA cuRAND device API and performance notes](https://docs.nvidia.com/cuda/archive/13.1.0/curand/device-api-overview.html).

The counter/key mapping is now fixed for the diagnostic: Philox key words
are the low/high 32 bits of the 64-bit episode seed. Counter words are
`[global_microvillus_id, tick_low32, tick_high32, draw_block]`, where
`draw_block = floor(draw_index / 4)` and `draw_index mod 4` selects one of the
four returned words. Global ID is checked to fit 32 bits; draw blocks are
checked to fit 32 bits before generation. This mapping is injective over
valid `(id,tick,draw_block)` tuples, so splitting `fp_advance` calls cannot
reuse a counter. The pinned cuRAND FP32 word-to-uniform mapping is also
specified by `curand_uniform.h`; draw ordering in the reaction kernel must
still be frozen before integration.

The counter and uniform-vector gate has passed on the active SM120 GPU:
seven counter/key cases, including 64-bit tick/seed boundaries, matched an
independent CPU Philox4x32-10 implementation byte-for-byte. The pinned
cuRAND FP32 uniform conversion matched at the bit level. Source, binary,
vectors, header hashes and report are verified in private HF revision
`8b1dc9e0b80cc09b2405dd4d6982a5043cfa0218`, manifest
`manifests/42141919c2fcd0b1c0d01ed03ecdb7b1330e2452a0cdb4cd9813555ed59005f1.json`.
This proves the mapping on seven vectors, not RNG statistical quality,
split-call checkpoint behavior, retina fidelity or speed.

The new random stream cannot reproduce the pinned XORWOW trajectory
byte-for-byte. It is eligible only if independent-ensemble distribution,
temporal-correlation and biological response checks agree. Deterministic
replay of the *new* model must be exact across split `fp_advance` calls,
save/restore and process restart. A new checkpoint build identity rejects
old RNG-state checkpoints; no automatic reinterpretation is allowed.

## Buffer and ownership sketch

| Data | Type / shape / bytes at full size | Writer, reader, lifetime, failure |
| --- | --- | --- |
| Molecular state | Existing SoA, 14 bytes × 101.31 M = 1.42 GB | VisTrans kernel writes; next tick reads; retained in checkpoints; source overflow checks remain |
| Receptor owner | `uint16`, 2 bytes × 101.31 M = 0.20 GB | Created at model construction; read-only until reset/destroy; dimensions checked before allocation |
| RNG key metadata | Global seed and 64-bit global tick, constant-size | Model owns; kernel reads; checkpoint stores; reject tick overflow |
| Draw index | Register-local integer per active microvillus | Kernel initializes to zero each tick; increments for every uniform draw; abort on overflow |
| Old XORWOW state | 48 bytes × 101.31 M = 4.86 GB | Retained only in the incumbent model; absent from candidate hot path |

If molecular state and owner remain the only per-element persistent arrays,
the analogous single read/write traffic model falls to 3.24 GB per tick,
with a 2.03 ms peak-bandwidth floor. This is at most a **4× reduction in
modelled bytes**, not a measured runtime gain. Philox arithmetic, registers,
branch divergence and the rest of the stage may erase it.

## Required evidence before adoption

Before the full reaction-kernel A/B, use one **screening** microbenchmark:
101.31 million elements, 16 bytes of live molecular-style state read/written
per tick, one unconditional uniform and two additional uniforms for a
predeclared 3% conditional branch. Compare resident XORWOW state read/write
with counter Philox, 100 timed ticks, warmup, three repeats, GPU events,
identical output traffic and a post-timing checksum. Abort on CUDA failure.
This can reject a compute-heavy RNG substitution early. A win only permits
the full reaction-kernel experiment; it is not a retina speedup claim.

The screen completed on the Molab RTX PRO 6000. For 100 ticks, XORWOW
times were 957.72, 957.18 and 955.76 ms; counter Philox times were
258.55, 258.79 and 258.52 ms. Medians were 957.18 and 258.55 ms, a
**3.70× synthetic RNG/state-stage ratio**. Both full output arrays were
read by post-timing GPU checksums. Source, binary, ptxas build log, run log
and structured report are SHA-verified in private HF revision
`38b5a7d5c9d9d0ab033fe6f9b5270ad27651a781`, manifest
`manifests/d3442fb0789928b5cdedcacb3c6c1ed05b95ba0cf16e531982f61980272e6f68.json`.
This is neither the 1,565.7 ms source VisTrans stage nor a full-CNS A/B.
The reaction law, branch divergence, membrane feedback and checkpoint
behavior must still be tested before any speed claim for the fly.

## First integration slice

The verified Molab base is the corrected coupled-current receptor source
`build/photon_coupled_current_diagnostic.cu` (SHA256
`30e590a1ff30532a06f05b848e69f2e054b66c503189b966f328e76fba7f9541`)
and the unchanged reaction header `native/phototransduction_safe.cuh`
(`4a6d0a73dc52eb9e86c4a17deb1a321e9db61215a5c8c104be1fd4723c22288b`).
Generate a separate candidate source/header rather than mutating the
incumbent. In the header replace only the RNG load/draw/store path with a
register-local counter stream; leave each reaction propensity, branch,
state update and time advance unchanged. Pass `episode_seed` and the global
64-bit tick into the kernel. Draw index starts at zero for each microvillus
at every tick; four words are cached per Philox block. A draw index of
`2^34` or more must fail the episode before counter reuse.

The candidate C ABI keeps `fp_create/reset/advance/observe/save/load`, but
its checkpoint version is 2 and omits per-element RNG state. A version-1
XORWOW checkpoint must be rejected before mutating the candidate. The
incumbent build and its checkpoint behavior are unchanged. First compile
and run one receptor for five ticks, then verify split-call and fresh-process
save/restore exactness on the candidate before distribution or speed tests.

1. Freeze the exact counter/key mapping, uniform-to-float mapping, maximum
   draws per tick, checkpoint format, and split-call replay semantics. Check
   available cuRANDDx/CUDA version on the active Molab GPU. No new kernel
   until these contracts and the test vectors are written.
2. Run a bounded real-memory A/B on the exact device. Same 3,377 × 30,000
   shape, same source reaction and membrane code, warmup and repeated
   medians, hardware metadata, register/spill report, full output writes.
   Measure transduction, full receptor stage, and complete-CNS wall time
   separately. A component gain without an integrated gain does not promote.
3. Check small deterministic test vectors and exact save/restore replay of
   the new model. Compare raw-uniform and molecular-state distributions,
   tails and temporal correlations across independent seeds at gray,
   light and dark inputs, including 100 ms and adapted 500 ms cases.
4. Re-run the matched full-CNS visual responses and existing biological
   controls. The candidate can replace the incumbent only if fidelity gates
   pass and the full application is materially faster. Preserve both source
   and candidate binaries and immutable HF receipts.

The first timing decision threshold is a predeclared ≥1.5× median reduction
in transduction time and ≥1.3× end-to-end improvement on the matched
full-CNS case, with no failed fidelity gate. If it misses, archive the
negative result and retain the incumbent. These are engineering selection
thresholds, not biological claims.

## Full-population candidate screen (2026-09-24)

The isolated counter-Philox candidate ran 3,377 receptors × 30,000
microvilli for 100 ticks at 50,000 photons/s and seed 19503 on the Molab
RTX PRO 6000. `fp_advance` took **1.6134 s** in one run, with final tick 100.
The candidate binary SHA256 was
`179130e1eb50e9de1bac9df4c52f27a1efc379167cf5a40b6a30267afc090a31`.
The report was remotely verified and restored into a fresh Molab directory:
HF revision `1a83fec71c2f8949348a94819a634b3f7a731948`, manifest
`manifests/81f444e6dd776ef20eeebf3ff99aab7f07fe69fd14ba683ae3550d6e7f43758f.json`.
`tools/benchmark_counter_retina.py` records the screening procedure.

The historical corrected XORWOW control at this nominal shape took 1.6234 s,
but it was measured in another run. The candidate has **not** demonstrated
a material speedup. A same-session, repeated A/B must compare the same
reaction and membrane code, build settings, and output contract before any
performance decision. Ensemble distribution and complete-CNS tests remain
unperformed; this screen does not promote the candidate.

### Same-session paired A/B

The pinned coupled-current XORWOW binary (SHA256
`2b24ed9428927c44643e7a269b22da8f827f699e789db5dabcc9b6aeb369665f`)
was restored from HF revision `4504dad5f8ecfe59ba88aacc784c9b01e3a28ac7`
with its manifest and binary hashes checked. The candidate binary above was
already verified in the same live Molab session. At identical shape, seed,
rate and tick count, the alternating order XORWOW/counter/counter/XORWOW/
XORWOW/counter yielded three `fp_advance` times each. Median XORWOW was
**1.623146 s**; median counter was **1.615366 s**, ratio **1.004816×**.
Every run reached tick 100 and produced finite observations. The two RNGs
produce different random streams, so their individual voltages are not
expected to match.

The report passed remote object verification and fresh-directory SHA256
restore at HF revision `c882edbeb0a81dad1074c6c2087518932ceb5297`,
manifest `manifests/4c40328dae971d38b2710d998ecc63b6d1bd175464c875cdab20fe58e3588e0d.json`.
`tools/benchmark_counter_retina_pair.py` records the matched procedure. This
is an isolated whole-retina timing result, **not** a separately timed
transduction stage or complete-CNS measurement. The measured receptor
advance gain is only 0.48%, far below a practical material speedup.
Keep the incumbent XORWOW path. Stage-level profiling and a source-diff
audit would be needed to apply the predeclared transduction threshold
literally; distribution and complete-CNS checks remain prerequisites if
this candidate is reconsidered for biological use.
