# Complete provisional MBON11 gamma1 volume classification

Executed in foreground MoLab on 2026-10-05. All 41460 KC contacts to annotation candidates MBON11 10704 and 11402 were retained, including broad PED and non-gamma strata. Each pre/post source coordinate was mapped provisionally to the v3 256-nm atlas grid using the published 8-nm voxel convention, and sampled at all 27 offsets in {-1,0,1}^3. Expected hemisphere labels were provisionally 190 for 10704 and 195 for 11402.

| Mutually exclusive classification | Contacts |
|---|---:|
| Both pre/post neighborhoods entirely expected g1 | 23559 |
| Both centers expected g1, neighborhood boundary-sensitive | 1233 |
| Near expected g1, centers not both expected g1 | 1304 |
| Outside expected g1 in both sampled neighborhoods | 11627 |
| At least one unknown neighborhood sample | 3737 |
| Total | 41460 |

Both center positions match expected g1 for 24792 contacts. These are numerical sampling results, not an admitted anatomical or physiological mask. The boundary check is an explicit 256-nm grid neighborhood, not a measured anatomical error distribution.

The acquisition plan requested 157 blocks; 147 were generation-pinned and byte-count/MD5 verified, while ten returned metadata HTTP404. Missing blocks remained unknown, never silently zero. Compressed source bytes total 2054316. Each completed input segment was independently archived before advancing. Package decoding agreed with an independent format reader at 9408 points across all available chunks. This establishes decoder agreement, not spatial registration. All contact results, 27-neighbor label lists, strata and logs were archived together after completion.

Private HF `TryDotAtwo/faithful-fly-artifacts`: final input closure commit `fd5ef6b95826bbe33d7dea0e719230a515796049`, manifest `11c50bc6df1322ba054fa1553d6e38183fa1b7931fb4dcbe86a2b58832d3c484`; classifier source commit `d92f466dae344d761f98323050654b769da0d80a`, manifest `657b84218cdc8bef8bb0223b01720b6007c2d7473929887bb35a3a0d0b786d94`; completed classification commit `39c79aac825b2e1e0a22677b2d4b9eaff79cd8f0`, manifest `692bde3910691681fdca1afffef4bc7a46ffbee594af501c0c5144a335cc2fda`. Remote identity and objects verified.

Admission remains open: independent bilateral landmarks and MBON/DAN territory, explicit gamma1 versus pedc semantics, atlas-version sensitivity, KC-subtype/receptor physiology and uncertainty checks. No contact weights changed and no learning was enabled. Further comparisons must preserve all contacts and report gamma and alpha/beta inputs separately.
