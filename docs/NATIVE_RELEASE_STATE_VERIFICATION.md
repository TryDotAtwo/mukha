# Native release-state and minute-level observation verification

The immutable CUDA build from cb7b18bfe72d8f7aafe72eec475581b479321c14 was restored and verified in MoLab; no rebuild or model changes. All computation ran in one visible foreground cell. Source/input closure: HF 6087d03a80e72ff0fc4db37e9b1145c156523c24, manifest 47de1cf6a93db272c49207e0616d04526bfeaf2560859ef1f4a25989efbf18ed. Durable source: remote_work/verify_native_release_state.py, included in the immutable source closure.

## State contract evidence

A three-neuron, two-edge graph uses distinct release utilization, recovery and efficacy, with separate excitatory and inhibitory inputs. Known source events and delay ticks match exactly. Independent event-level exponential recovery and conductance superposition agree within max absolute error 2.255140518769849e-16 under the frozen 1e-10 tolerance.

Full execution versus six chunks split before/at source events and delayed arrivals is bit-exact across voltage, excitatory/inhibitory conductance and spikes. Explicit reset plus replay is bit-exact. Eight invalid configurations (negative/above-one/nonfinite utilization; zero/nonfinite recovery; negative/nonfinite efficacy; null utilization array) are rejected; the original valid configuration remains intact. Configuration after time advancement is rejected and subsequent continuation matches an untouched handle. These checks are limited to this graph and conditions; release-state checkpoint serialization has not been implemented or tested.

## Three-minute operator

Each of three conditions runs 180000 one-millisecond ticks, three minute sets, 27 verified source events, a separate single-reference trace, and averages four pairs per minute before reference subtraction. Direct-voltage inputs and normalized conductance remain artificial observation surrogates, not optical recruitment or actual voltage clamp.

Baseline U=0.5, recovery 1000 ms and efficacy=1 yields PPR approximately 0.6648523032. U=0.25 yields approximately 0.8324268142 and lower A1. Efficacy=0.5 with U unchanged halves A1 and A2 and preserves baseline PPR. Independent event-level formulas verify each full trajectory and the same observation operator; parameter values are uncalibrated. The small difference from isolated-pair PPR is retained because recovery before each first event is finite rather than silently assumed complete.

Each completed condition was immediately published before the next. Final report and all condition receipts: HF 3c2373646e6be4bcf833a9c31e4269792b3b483c, manifest 9d5fde05237ae01abe22f9bd76700504e9c0b6d07ccc37b8d94bfe8709bccb9b. All remotely verified. No local computation or dataset/result download.

Remaining: CUDA sanitizers, full dependency closure, release checkpoint identity/continuation, measured full-CNS performance and independent physiological parameter/long-term plasticity validation. Sparse gamma recruitment, subtype-specific induction/persistence and real clamped EPSCs are not reproduced. Learning remains disabled and all original full-project gates remain open.
