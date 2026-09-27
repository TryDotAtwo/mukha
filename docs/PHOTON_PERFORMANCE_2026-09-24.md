# Full-resolution photoreceptor performance audit (2026-09-24)

This audit uses the corrected within-substep TRP-current candidate; it does
not relax the full MaleCNS connectome or certify the candidate biologically.
The Molab device reported **NVIDIA RTX PRO 6000 Blackwell Server Edition**,
compute capability 12.0, driver 595.71.05, about 97,887 MiB VRAM. The
CUDA 13.1.1 toolkit came from the project's pinned build runtime. Nsight
Systems, Nsight Compute and Compute Sanitizer were absent from the session;
timings below come from an instrumented separate CUDA build on that GPU.

At 3,377 receptors × 30,000 microvilli, 50,000 photons/s, seed 19503 and
100 × 0.1 ms steps, the uninstrumented corrected receptor advanced in
1.6234 s. The instrumented library gave byte-identical observed state and
1.6247 s elapsed. Its summed stage times were:

| Stage | 100-step time | Share of measured advance |
| --- | ---: | ---: |
| Stochastic microvillus transduction | 1,565.7 ms | 96.4% |
| Current reduction | 36.8 ms | 2.3% |
| Membrane Hodgkin–Huxley | 14.1 ms | 0.9% |
| State readback and numerical checks | 7.0 ms | 0.4% |
| Calcium-adaptation update | 1.0 ms | 0.1% |

The instrumented stages include explicit synchronizations, but the total
was within 0.1% of the reference in this pair. Source, binary, profiler
script and comparison report are SHA-verified in private HF at revision
`5a4c89fad9bf6332f1fe31f0822e711a8f0d8e9d`, manifest
`manifests/1e6899eeab04c092a79d4a24658f4eb3e1222b6603d4f176278dd0faffb3378b.json`.
An independent repeat captured the kernel's stage output as a file and
reported 1,565.7/36.8/14.2/8.1/1.1 ms for transduction/current/HH/readback/
adaptation; the full stdout and structured addendum are SHA-verified at
revision `76535f722ce4c18f5047ea00300f32788bb18f4a`, manifest
`manifests/21e09382246814af80fe3d7c24a8b2338c620302f395f8d1569fe893e7c0909e.json`.

Three launch hypotheses were tested, with negative results:

1. Replacing atomic warp work allocation by static warp-stride assignment
   preserved the complete 64-receptor checkpoint payload bit-for-bit and
   all 3,377-receptor observations. It **slowed** 100 steps from 1.624 to
   1.847 s. Variable per-microvillus reaction work makes static assignment
   prone to imbalance. Revision `e66ad2469cc7ff54c90c1a0401130fb7723f957b`,
   manifest `manifests/b276f3c626399c508ec12bab1d5152fe6e9e360e236972ec712cea6a03d4cebf.json`.
2. A three-repeat dynamic-grid sweep from 256 to 8192 CUDA blocks found
   medians of 2.186, 1.666, 1.628, 1.629, 1.628 and 1.629 s for 256,
   512, 1024, 2048, 4096 and 8192 blocks. The 4096-block median beat
   1024 by only 0.03%, below a useful practical improvement. All final
   observations matched exactly. Revision
   `66baaf8e1dd56770a812982ea3c6725fd72532f4`, manifest
   `manifests/1c5de50865da432530981634610ab42987ebae0fbf8421387564bff644ba27d7.json`.
3. `ptxas` reported 72 registers per transduction thread and no spills
   for the reference. Caps of 64, 56 and 48 introduced spills, kept the
   observed state exact, and changed two-repeat median times from 1.626 s
   to 1.627, 1.630 and 1.631 s. Revision
   `a4dfaa4f4088cb28fb8dd9b13e93746a4110e7be`, manifest
   `manifests/f95af49f4284c4ce1cb13fb9789beb4175a9c335f19088a858ffa85e1836e00d.json`.

The configured whole-CNS 1,020 ms flash cases took about 329–331 s each.
Those wall times include the full graph, other visual routes, host/device
transfers and file recording, so the 1.62 s / 10 ms isolated receptor timing
must not be presented as end-to-end fly speed. The evidence makes further
launch-count tuning, register capping and simple static scheduling poor next
investments. A large speedup requires a different transduction algorithm or
sensory reduction with explicit error bounds against the full model and
biological physiology. The current 24-state GRU surrogate in
`PHOTON_SURROGATE.md` fails waveform preservation and was trained on the
earlier held-current teacher; it is not a production replacement.

## Molecular-state multiplicity and turnover

To test whether an event-driven, grouped-state implementation could avoid
visiting all 30,000 microvilli every 0.1 ms, eight receptor checkpoints were
examined under constant 50,000 photons/s. At 100 ms, the median receptor had
2,850.5 distinct molecular state vectors, 58.36% of microvilli remained in
the basal state, and 92.68% belonged to a state shared by at least two
microvilli. At 500 ms the respective values were 3,779, 19.17% and 91.90%.
Source and structured results are SHA-verified at private HF revision
`29943ec72fdddacb6a130e52130fd40bc1407847`, manifest
`manifests/73e0bb97a87ef708e808dc0ea7aaa9266a04b4bac4d4fb061044b78a83852f87.json`.

For 20 consecutive ticks after 500 ms of adaptation, a separate eight-cell
sample changed molecular state in a median **3.245%** of microvilli per tick,
about 974 of 30,000 per receptor. The observed range was 3.183–3.308%.
These changes are only a lower bound on reaction events because a microvillus
may react more than once or return to the same state within a tick. The
exact-state source and result are verified at revision
`a0d8239df22fe98a990bb444e5834918b9c806e5`, manifest
`manifests/781ddeec7ce67e0e7316c66393675ee1aa1034f9be2872002e40cda1e73c10fe.json`.

The data support a concrete next prototype: within each receptor, represent
identical molecular state vectors by a count and simulate their stochastic
reaction hazards as a population process over the fixed 0.1 ms tick. Because
the measured voltage, adaptation and photon rate are common to a receptor
over that tick, equal microvilli are exchangeable for aggregate current.
This can preserve the **distribution** of the published reaction process if
the grouped sampler is exact, but it will not reproduce the same per-entity
XORWOW sequence or byte-identical checkpoint. It needs an independent
reaction-law oracle, distribution tests across seeds, tail and temporal
correlation checks, and full-CNS visual comparisons before use. The 3.2%
turnover is not a measured 30× speedup; grouping, state maintenance and
event selection all have costs.

## Grouped reaction law: first independent checks

`reference/grouped_vistrans.py` implements a small CPU population SSA oracle.
Within one 0.1 ms tick it groups identical molecular states, holds each
receptor's voltage/adaptation/photon input fixed, and samples events from
count-weighted hazards. It intentionally retains the source kernel's `LA=0.5`
waiting hazard and its separate reaction selection from `sumrate`, including
the `2e-5` null interval. It is therefore a model of the *implemented* law,
not a silently revised phototransduction equation.

For 500 independent and 500 grouped CPU ensembles (128 microvilli, 20 ticks,
fixed −56 mV, `ns=1`, 50,000 photons/s), the four measured end-state means
were within 1.87 combined standard errors. The small CPU grouped run took
0.812 s versus 6.143 s for the independent run. This is a **CPU pilot speed
ratio**, not a GPU or full-fly throughput estimate. Source, report and script
are SHA-verified in private HF at revision
`2a1bd74d41340a60b374cf42208f24e351a8b940`, manifest
`manifests/bf854bfcbfdbf682cbeee54a144a0a85ebe0ea8436da5dfbd2f4013cae7a86c2.json`.

An independent CUDA diagnostic then ran the unchanged source reaction kernel
at the same fixed inputs on 512 receptor ensembles, 128 microvilli each and
20 ticks. The CUDA and grouped CPU means differed by 0.60, −1.19, 1.94 and
0.00 combined standard errors for basal-state count and sums of `x0`, `x5`
and `x6`, respectively. All passed the declared 4.5-SE screen. The CUDA
diagnostic, binary, raw rows and report are SHA-verified at revision
`5b3b8f21fa024c2901c3c61839d19f05ee21da5f`, manifest
`manifests/eadf0181704a8cd451e81ade32eb9874ef61edbc0ed5666e827eca0a52117efa.json`.

This tests four means at one fixed setting. It does not establish tail
behavior, temporal correlations, voltage-coupled behavior, biological
fidelity, or GPU performance. The next implementation gate is a flat,
preallocated per-receptor state histogram with indexed event selection on
GPU, followed by full-retina timing and broader distribution tests. The
grouped implementation cannot replace the source kernel until those pass.

The first grouped CUDA implementation did **not** pass that gate. Its short
10 ms fixed-input diagnostic was fast, but a 100 ms full-receptor run exhausted
all hash tables; a tombstone-reuse variant timed out after 180 s on a smaller
512-receptor case. The design is rejected for production. See
`GROUPED_RETINA_ARCHITECTURE_REVIEW.md` for the buffer/work analysis and the
required design gate before another kernel.

The adapted-state rate audit adds a separate algorithmic constraint. At 500 ms
of constant light, the median of eight receptors had about 1,376 expected
waiting events per 0.1 ms step, with roughly 247 microvilli at instantaneous
`hazard × dt > 1`. This is not a path-probability bound, but a one-transition
per-tick shortcut cannot be an exact replacement. SHA-verified report:
HF revision `fd681aa8d6e435db6483797a9f06d8788bfa75dc`, manifest
`manifests/aa5c7d08a0d6c533fa80617d577cb2a4c8fc918105d8792496e98a5ac095789a.json`.

The next candidate is specified before implementation in
`RETINA_RNG_MEMORY_DESIGN.md`: retain per-microvillus parallelism and test
whether removing 48-byte persistent XORWOW state through a counter-based
generator reduces actual full-CNS wall time. The byte calculation is a
hypothesis, not a measured bandwidth result; RNG-law and biological checks
remain mandatory.
