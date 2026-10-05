# Four-DAN PreSyn atlas classification — 2026-10-05

MoLab foreground cell DKWV completed. All pinned input segments restored and available chunk SHA256 checked before decoding. All8362 PreSyn sampled at center and27 neighbors (256nm radius), no source rows excluded.198 available chunks;79 missing remainUNKNOWN. Independent compressed-segmentation decoder matched12672 point checks.

| status | points |
|---|---:|
| robust-g1-L | 1413 |
| robust-g1-R | 1627 |
| g1-boundary-sensitive | 249 |
| outside-g1 | 4288 |
| unknown-neighborhood | 785 |

| body | robust g1L | robust g1R | boundary | outside | unknown |
|---|---:|---:|---:|---:|---:|
| 11327 PPL101_R | 584 | 820 | 119 | 792 | 289 |
| 11900 PPL101_L | 680 | 666 | 113 | 732 | 242 |
| 11618 PPL102_L | 0 | 141 | 15 | 1383 | 150 |
| 13428 PPL102_R | 149 | 0 | 2 | 1381 | 104 |

All3181 source-g1 points had comparable center labels; zero source-g1 center mismatches. This confirms cross-format consistency, NOT independent biological anatomy because source ROI and atlas may share provenance. Full atlas neighborhood is a stronger boundary diagnostic than center alone.

HF result935a216bab16efbc125469855a6e0f53535e8aa6
Manifest27d8903b333b95598c12de41a31020ebcace3eefa16edbd955ae4cf911afc52b
Source74c442740f27cc12c126dcccb040300379d374ac
Remote root/tmp/fly-dan-atlas-classification-20261005
Artifacts dan-presynapses-atlas.parquet, strata.csv, report.json.

Missing retainedunknown; all original columns retained. No pedc mask, receptor, release, contact-mask or plasticity admission; no learning enabled. Next: evidence-defined pedc boundary and physiology rather than treating whole PED as pedc. Preserve compartment asymmetry from prior audit.
