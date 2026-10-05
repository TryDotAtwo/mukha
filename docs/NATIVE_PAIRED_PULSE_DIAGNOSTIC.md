# Native no-learning paired-pulse diagnostic — MoLab, 2026-10-05

Foreground cell seBm (`native_paired_pulse_diagnostic_v3`) completed five conditions on RTX PRO 6000 Blackwell Server Edition (compute capability 12.0, driver 595.71.05). Unchanged native source: project commit d06ce5a7a68b7a67828b57b15d9d989a3dd287bc; CUDA blob 2afbb065cc45d61a2d6f3b9a6917fe8285762d4a; header blob cfa0da1bb64e8193a6d9c92f31aa8ae11565ee6d.

This is a two-neuron numerical diagnostic, not full MaleCNS physiology. Artificial 50-mV direct jumps at ticks 10/410 produce precisely one source event per jump (ticks 11/411). Synaptic delay is two ticks; arrivals are ticks 13/413. Parameters are declared engineering choices: dt 1 ms, membrane time 20 ms, synaptic decay 100 ms, excitatory gain 0.1, resting/reset -60 mV, threshold -40 mV, reversal 0 mV. No biological parameter fit, optical-to-spike model or three-minute published baseline schedule is claimed. No postsynaptic spikes occurred.

Independent analytical observation: for arrival ticks a_j, g[k]=sum_j w exp(-(k-a_j)/100) for k>=a_j. The existing native trace is compared against this closed form. A fixed holding-voltage observation gives current per unit leak conductance: I/g_L = g*(V_hold-E_exc); its magnitude is 60*g in mV. Absolute EPSC in pA is unidentifiable without a measured leak conductance; no such value is invented. The native voltage is not clamped; this is an offline normalized conductance readout, not an implemented voltage-clamp electrophysiology model.

| Condition | Gain | Maximum conductance error | Tail-subtracted A2/A1 |
|---|---:|---:|---:|
| No input | 0.1 | 0 | undefined |
| Single event | 0.1 | 2.0816681711721685e-16 | undefined |
| Pair, 400-ms onset interval | 0.1 | 2.1510571102112408e-16 | 1.0000000000000004 |
| Half scalar gain, labelled presynaptic | 0.05 | 1.0755285551056204e-16 | 1.0000000000000004 |
| Half scalar gain, labelled postsynaptic | 0.05 | 1.0755285551056204e-16 | 1.0000000000000004 |

Frozen software tolerance: 1e-10. Both scalar interventions use the same native gain input and therefore produce identical voltage, conductance, event and oracle arrays; they do not implement actual extracellular calcium or receptor blockade. Their identity demonstrates the representation's inability to distinguish these mechanisms, not an independently implemented intervention comparison. Tail-subtracted PPR=1 is the additive-kernel mathematical identity, not a biological target.

Primary comparison requirement: [Yamada et al. 2024, Figure 1](https://par.nsf.gov/servlets/purl/10583452) reports altered extracellular Ca/Mg changing both first EPSC and PPR, while partial nicotinic receptor blockade reduces first EPSC without detected PPR change. Thus a single scalar-gain parameter is insufficient for this physiological dissociation. Separate presynaptic release dynamics and postsynaptic observation/efficacy are needed before physiological admission; no new mechanism was enabled by this diagnostic.

Execution repair: v1 compilation lacked CCCL nv/target (log HF5a255b6b9132705c1f3ab18325760b534441cc05 / ac54268b207e65e3b481cde8b79183da4c9c6b4dec3736552cf41926b33c6883). CCCL13.0.85 wheel was verified against published PyPI SHA-256 and archived before extraction. V2 incorrectly passed versioned .so.12 to nvcc (log HFb7b7131d490f14ee1a2929a83981e68dbbe2b713 /7d304cc19288339128f8ef9a4111d9b75acf3bdd42b448f069beb15a17818814). V3 passes it through -Xlinker; native model code unchanged.

Source/build-input receipt: e8a958a8ab455a35df368e3f1e75f33d1dac5b09 /9dffa1be7f518937f8a08d96aa673b3d46afee205842aa1359f78aec235ef0b1.
Binary/build-log receipt:38d448f387197424b2a2f89699dc836c5cccf4b5 /e7b2e30a8869a37450fbba88e4d5a226173aae842aff1f5cf96a7b9e5243d161.
CCCLwheel/metadata receipt: b7b7131d490f14ee1a2929a83981e68dbbe2b713 /6e7dd1486ddd1bb4950ee9f7a3b93166f46eb48245bbcadc160eee8bd770cc56.
Final verified report: private HF TryDotAtwo/faithful-fly-artifacts, commit dc86507032b0187ec0260d89b4035288c33b5849, manifest526fc1bb4084534a901d322c9961a30b25c0af6d71e53d4c8cf967be8095b2fb. It binds all five immediately published condition receipts, full arrays and logs. Build identities include compiler and cuSPARSE hashes; complete CUDA dependency wheels are not archived, so no complete reproducible-build admission follows.

Remote root:/tmp/fly-native-paired-pulse-v3-20261005. Source:tools/run_native_paired_pulse_diagnostic_v3_molab.py. All compute/builds/data/verification ran in MoLab; no binary or arrays downloaded locally. No broad sanitizer, complete physiology, anatomy, local learning or full-project gate passes follow. Learning remains disabled. Next: preregister a separate falsifiable presynaptic release hypothesis and its independently observed calibration/assessment boundaries while continuing pedc/DAN anatomy.
