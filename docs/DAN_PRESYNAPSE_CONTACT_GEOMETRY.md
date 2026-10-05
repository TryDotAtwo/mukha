# DAN presynapse/contact geometry — 2026-10-05

MoLab foreground cell bMsS; private HF verified; all inputs restored from immutable receipts before computation. Full 41460 contact rows retained. 8362 annotated PreSyn points from four DAN bodies. Distances to both pre and post endpoints calculated; 136 exhaustive point-scan comparisons passed.

Result HF b0506b71173fbddfac3e407e435624c7c1b5ebe0; manifest 28163c60953d9da139bdc91a66c98064efb5ecfc4acf0193b795ba6e9b746bd7.
Source HF 59fa3c2e986fc309e4b73b64ab4a3895b720e322; manifest 69040f7e9785cc16760370e9d0b31b8f0956195a12dadcae338774c1158cec9a.
Remote root /tmp/fly-dan-presynapse-contact-geometry-20261005.

Median distances to nearest annotated DAN PreSyn from POST endpoint, robust-gamma1 contact subset (nm):
| MBON body | contacts | PPL101_R 11327 | PPL101_L 11900 | PPL102_L 11618 | PPL102_R 13428 |
|---|---:|---:|---:|---:|---:|
| 10704 | 10315 | 1385.710 | 1319.539 | 56498.900 | 2271.169 |
| 11402 | 13244 | 1198.132 | 1305.815 | 2266.903 | 57840.441 |

Source subprimary g1 counts of PreSyn:
| body | g1(L) | g1(R) | source compartment |
|---|---:|---:|---|
| 11327 PPL101_R | 599 | 873 | axon |
| 11900 PPL101_L | 710 | 702 | axon |
| 11618 PPL102_L | 0 | 147 | axon |
| 13428 PPL102_R | 150 | 0 | dendrite |

PPL101 also has PED(L)/PED(R) PreSyn: 229/283 for 11327 and 257/199 for 11900. These do NOT define a gamma1-pedc mask; whole PED is not admitted as pedc.

Observations: PPL101 annotated presynapses are bilateral. PPL102 gamma1 PreSyn occur contralateral to annotation suffix. PPL102 compartment annotation differs materially across candidates: 147 axon versus 150 dendrite in gamma1. Preserve source asymmetry, do not relabel or exclude PreSyn based on presumed compartment semantics.

Limits: nearest annotated point distance is not partner identity, measured dopamine release, transmitter diffusion radius, or complete release-site coverage. Minconf0.5 source and provisional gamma1 contact classification. Existing unknown statuses retained. No new atlas coverage, independent gamma1/pedc admission, contact-mask, plasticity or learning admission.
Next: independently sample all DAN points against atlas with missing coverage preserved, verify source compartment semantics, and define pedc from evidence rather than whole PED.
