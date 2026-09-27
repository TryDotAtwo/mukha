# Grouped VisTrans GPU architecture review (2026-09-24)

This records a rejected fixed-input GPU prototype and the design gate before another implementation. It does not change the accepted retina or biological gate. The reference path remains `native/phototransduction_safe.cuh`.

## Semantic contract

One receptor contains 30,000 independently evolving microvilli. During each 0.1 ms neural step they share membrane voltage, adaptation factor and photon rate. Their seven-element molecular states are identical only when all seven integer counts agree. A grouped implementation may change random-number trajectories, but must preserve the joint distribution of aggregate current and molecular state at each observation. The pinned source's `LA=0.5` waiting hazard, `sumrate` branch selection and `2e-5` null interval are part of the implemented law. A hash may locate states, but a full state comparison resolves collisions. Capacity failure must stop the episode, never drop a state.

The current oracle is limited: 512 original-CUDA versus 512 grouped-CUDA independent ensembles, 128 microvilli × 20 ticks with fixed −56 mV, `ns=1`, 50,000 photons/s. The four measured means differed by −1.77, +1.73, −1.53 and +1.00 combined standard errors. These statistics do not prove joint-law, tail, temporal, or voltage-coupled equivalence.

## Measured implementation and why it fails

`native/vistrans_grouped_probe.cu` is a diagnostic, one CUDA thread per receptor, with a 16,384-slot open-addressed hash table and a Fenwick tree. It preallocates a state key (14 bytes), count (4 bytes), and tree value (8 bytes) per slot. For 3,377 receptors, the principal arrays require about 1.44 GB before allocator/runtime overhead. A slot stores exact molecular state, so hash collisions do not alter identity. The source starts all microvilli in the basal state, which makes this implementation unusually cheap for the first few milliseconds.

On the RTX PRO 6000 Blackwell Server Edition in Molab:

| Fixed-input workload | Prototype result | Interpretation |
| --- | --- | --- |
| 512 receptors × 128 microvilli × 20 ticks | 7.38 ms, no capacity errors | Small distribution fixture only |
| 3,377 × 30,000 × 100 ticks (10 ms) | 179.1 ms, no capacity errors | Positive short component diagnostic; no current or CNS integration |
| 3,377 × 30,000 × 1,000 ticks (100 ms), no slot reuse | 11.43 s, all 3,377 receptors overflowed | Invalid output; table tracks historical states, not just live groups |
| 512 × 30,000 × 1,000 ticks, tombstone reuse | Timed out after 180 s | The repair does not make this design viable |

The 10 ms source control previously took 1.566 s in *transduction alone* at 3,377 × 30,000. That measurement and the 179.1 ms prototype use different output contracts and setup; their ratio is **not** an accepted speedup. Longer equal-contract tests already fail. In the tombstone variant, searching past removed keys can scan most of 16,384 slots as the table fills. The Fenwick updates and event choices are serial within each receptor, while adjacent GPU lanes touch unrelated hash slots. These are architectural costs, not launch-grid tuning issues.

At 500 ms, a measured receptor had about 3,779 *active* distinct states and about 974 molecular state changes per 0.1 ms tick. Across 3,377 receptors, that is at least 3.29 million state changes per neural tick. A serial per-receptor event loop therefore carries substantial ordered work even if hash lookup is made constant-time. This lower bound excludes repeated or state-neutral reactions. It is a workload count, not a GPU-time prediction.

An additional source-model measurement used eight receptors after 100 and
500 ms of constant light. The Python rate formula is an approximation to the
CUDA kernel's mixed-precision arithmetic, so it screens architecture rather
than certifying exact numerical rates. The median sum of instantaneous
waiting hazards times 0.1 ms was 1,887 per receptor at 100 ms and 1,376 at
500 ms. At 500 ms, a median 247 of 30,000 microvilli had individual
`hazard × dt > 1`; at 100 ms, 500 did. Applying a *frozen* hazard Poisson
formula would predict about 214 and 396 microvilli, respectively, with two
or more attempted events. These numbers are not bounds on the true
state-dependent paths, because a reaction changes the hazard. They do rule
out assuming that one transition per microvillus per tick is an exact
implementation. Report and source are SHA-verified in private HF revision
`fd681aa8d6e435db6483797a9f06d8788bfa75dc`, manifest
`manifests/aa5c7d08a0d6c533fa80617d577cb2a4c8fc918105d8792496e98a5ac095789a.json`.

## Decision ledger

| Status | Decision | Evidence / next gate |
| --- | --- | --- |
| Confirmed | Preserve the pinned stochastic reaction law and full receptor population while studying speed | Biological-fidelity requirement; source kernel |
| Rejected | Promote the one-thread-per-receptor hash/Fenwick prototype | Long test overflow and 180 s timeout; wrong access and work granularity |
| Confirmed | Keep the existing CUDA implementation as incumbent | It has full-state regression and measured complete-stage behavior; biological gate remains open |
| Open | Exact faster population algorithm with parallel work inside each receptor | Requires an event-dependency proof and a small multi-tick oracle before GPU scheduling |
| Rejected | Assume at most one molecular transition per 0.1 ms tick | Exactness fails by construction; measured adapted-state hazards make numerical truncation particularly risky |
| Open | Exact optimization of per-entity kernel (state/RNG layout, reaction path) | Must preserve same per-entity state and prove a material end-to-end gain on target hardware |

## Gate for the next GPU design

Before another CUDA implementation, specify the logical transition and exactness contract, then derive the maximum live and historical state counts from representative 10 ms, 100 ms and 500 ms snapshots. Give each device buffer its ABI size, shape, alignment, writer, reader, valid count, lifetime, and overflow response. Estimate per-tick event work and which lanes can perform it concurrently without changing the process. If the design relies on grouped transitions, prove how simultaneous draws handle state-dependent rates and events that change state within the same 0.1 ms tick. Compare the predicted work against the fastest source control before writing kernels.

The first executable gate then uses small deterministic and stochastic distribution oracles, followed by 100 ms and adapted 500 ms target-hardware cases. Timing requires warmup, repeated medians, identical inputs and output contract, capacity/failure rows, and full visual-CNS integration. A short fixed-input win alone cannot authorize replacement.
