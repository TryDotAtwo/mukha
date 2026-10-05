# Atlas decoder closure

MoLab foreground cell `prepare_atlas_decoder`, 2026-10-05, prepared compressed-segmentation 2.3.3 in an isolated runtime directory. All eight resolved wheels and their PyPI JSON metadata were checked against published sizes/SHA-256 and archived before offline installation. This does not modify the notebook's package environment.

An asymmetric uint64 array of shape 17x19x23 with distinct x/y/z contributions round-tripped exactly with Fortran order and 8x8x8 compression blocks. This verifies that explicit package invocation only; a real Neuroglancer chunk and cross-channel header handling remain to be tested before atlas contact classification.

Private HF dataset `TryDotAtwo/faithful-fly-artifacts`: source commit `7bac20de9844a266e6dcdaa6d2c29aef5875faf1`, manifest `1032c590dd94b3be613ab11bb7ea6d925971f9562ff1dd0ca84ccbd5214d0581`; verified wheel closure `07b7fd9539f57502ea961a546354f7071ec3d82e`, manifest `5a44df3dacfdaa7154bd844e0836ef3b7a2c720819daf6ca8d8efa8cdaba5d89`; completed report/log receipt `eecba8a3355c93c742709c0388339c25c13ad32d`, manifest `1c9c19b3a7e49b0f33974b858024e80b40088ba3572f767432caaaef5957a9d2`. All verified. No contact mask or learning admitted.

Expert feedback from Astra, relayed by the coordination chat, recommends pinning version/axis/origin, checking bilateral landmarks and DAN/MBON territories, determining gamma1 versus pedc semantics separately, retaining uncertain boundary contacts, reconciling classified/uncertain/outside totals, and testing version/boundary sensitivity. The expert did not independently replay the source audit; this is guidance rather than validation.
