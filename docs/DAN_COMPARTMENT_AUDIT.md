# DAN compartment contingency audit — 2026-10-05

All 67575 selected source points audited in MoLab cell yEum. Source and kind/compartment/region/confidence tables archived; no fields corrected or discarded.
HF result f9d31be8c5870407fa5d09818c2c895d45138ded
Manifest caeafe6cf1512898288a7e77172e85deac079b3585ff3e5f75edae85ae937463
Source HF b89621a3906e5e610368348a8a34dba6e10ccbc1
Remote root /tmp/fly-dan-compartment-audit-20261005.

Gamma1 source counts:
| Body | region | compartment | PreSyn | PostSyn |
|---|---|---|---:|---:|
| 11327 | g1(L) | axon | 599 | 3540 |
| 11327 | g1(R) | axon | 873 | 3952 |
| 11900 | g1(L) | axon | 710 | 3742 |
| 11900 | g1(R) | axon | 702 | 3893 |
| 11618 | g1(R) | axon | 147 | 1226 |
| 13428 | g1(L) | dendrite | 150 | 1544 |

PreSyn confidence for body11618 gamma1: min0.75 median0.883 max0.978.
PreSyn confidence for body13428 gamma1: min0.701 median0.8705 max0.968.
Thus the compartment asymmetry applies to both point kinds and does not consist solely of near-0.5-confidence detections. Confidence is synapse detection confidence, not demonstrated compartment confidence.

Separate source fields compartment and kind must not be conflated. The audit does NOT prove biological dendritic dopamine release, misannotation, or a correction. Primary documentation search did not establish how the released compartment labels were generated or validated. Preserve uncertainty; do not make compartment semantics a fabricated acceptance criterion.

Next: independent atlas sampling of DAN points; obtain generator/curation provenance for compartment if available. No plasticity/learning admission.
