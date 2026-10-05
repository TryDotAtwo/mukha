# Bilateral coarse-skeleton geometry diagnostic — 2026-10-05

All computations ran in MoLab foreground cell yvBj. HF source/convention closure was verified before calculation; all six generation-pinned SWCs and the full 41460-row contact table were restored from immutable receipts.

The official MaleCNS download page specifies unmirrored SWC and synapse coordinates in the same Male CNS EM space, in 8nm units: https://male-cns.janelia.org/download/ . Its retrieved HTML is in the source receipt.

Metric: Euclidean distance from each POST endpoint to the nearest sampled coarse skeleton NODE. This is not nearest segment, neurite surface, synaptic connectivity, or release-site distance. All original rows and unknown atlas statuses are retained. KD-tree results checked against 170 exhaustive full-node scans.

Robust expected-gamma1 rows:
| MBON body | rows | own MBON median nm | PPL101_L | PPL101_R | PPL102_L | PPL102_R |
|---|---:|---:|---:|---:|---:|---:|
| 10704 | 10315 | 822.017 | 1060.475 | 1062.676 | 56330.123 | 1404.222 |
| 11402 | 13244 | 893.174 | 1067.723 | 1054.180 | 1517.039 | 55886.119 |

Observation: nearest-node PPL102 proximity follows the opposite annotation side to MBON11, while both PPL101 skeletons lie near both contact populations. Annotation suffix L/R is not sufficient to map territory; do not interpret same-side PPL102 as an absent gamma1 control. This does not establish release localization or complete anatomy.

Initial same-annotation-side diagnostic preserved as historical evidence:
HF commit de5dab92135d22d8cb06f14c00b852b0e4fb5ffd, manifest 4c71f6f6a37f6bc4d20fd14f2cde9928d0105d8dcabbd9fc4676f2039be3d122.
Bilateral source commit c1983616a80a9584d9b8bfae936322b94629f6d3, manifest 9eae1acb8a92db60ee18ae37fae0be28f77cbc88a532eadba8c53aedc9f7e39a.
Bilateral result commit 33db5a4375e025fad1440a2faad05a32bd594e4d, manifest 1bca7b32d497849b9a01106ea64c9070de47654f436649ea6beffa62d9ac2477.
Remote root /tmp/fly-gamma-skeleton-bilateral-node-distances-20261005.

No contact mask or plasticity admitted; no learning enabled. Next: independently map DAN pre-synapse release-site coordinates and atlas coverage, and determine coarse skeleton limitations before anatomy admission.
