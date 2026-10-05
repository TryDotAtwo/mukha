# Native Yamada minute-level observation diagnostic

Executed entirely in foreground MoLab on the unchanged native two-neuron conductance CUDA library. The prior immutable diagnostic report and its native build were restored and verified before use. No rebuild or parameter fit was performed.

The 180,000-tick schedule (dt=1 ms) contains three minute sets. Each set starts with one reference event, followed at 10, 20, 30 and 40 seconds by pairs separated by 400 ms. All 27 source event ticks were checked exactly; no postsynaptic spikes or inhibitory conductance occurred. The full conductance trajectory agrees with an independent exponential superposition within the frozen 1e-10 tolerance.

For each minute, a separately recorded reference trace is subtracted from the average of four paired traces. A1 and reference-subtracted A2 are both 0.1 normalized conductance, with PPR=1.0 on all three minutes. These are software identities of the static additive kernel, not measured biological targets.

Source/input closure HF: 080595aa47a7fe330f8cbd28a1e019f7fd3266a3, manifest 69b15a5467ba13185a213c12eeed2238d93f1b8783ab0cdd26abe6e2a7388e36. Completed condition log/report/arrays HF: 13a8665fd5c1ef3c5f217da6c9907370240e7cdd, manifest 003af2494585a145eebfca5f8608a475e3a204675922d5d2924f0b00156dd4c0. Both remotely verified. Durable transport source: remote_work/run_yamada_minute_operator.py (also included in the HF source closure).

Limits: one-millisecond direct voltage drives are artificial event surrogates, not optogenetic recruitment; normalized conductance is not absolute EPSC or a physical voltage-clamp simulation. Window lengths and sample-level peak observation are software choices, not recovered author analysis code. Sparse gamma KC recruitment, release dynamics, receptor efficacy, induction, subtype-specific persistence, full MaleCNS transfer and quantitative physiological calibration remain open. Learning remains disabled.

Next: an explicitly separate release-state and postsynaptic-efficacy candidate, with the above observation operator, independent numerical verification and intervention tests. Qualitative agreement alone must not be called physiological validation.
