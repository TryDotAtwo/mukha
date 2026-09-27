# MaleCNS visual population boundary

`tools/build_visual_boundary.py` verifies the accepted full-graph hashes and
builds a lossless incident-edge view for all 6,098 `ol_sensory` candidates. It
retains seven HBeyelet objects and eight objects with no incident edges inside
the accepted population. This view does not replace the full 167,216-candidate
graph or establish complete biological reconstruction. External-segment contacts
remain in the original boundary accounting.

| Direction | Edge rows | Sum of contact counts |
|---|---:|---:|
| Sensory to other | 71,711 | 602,256 |
| Other to sensory | 24,435 | 182,991 |
| Sensory to sensory | 3,265 | 49,546 |
| Incident union | 99,411 | 834,793 |

6,020 selected objects have incoming edges. The largest non-sensory input type
by contact count is Dm9: 5,285 rows and 141,372 contacts. Others include L4, L2,
C2, Lai and L3. These are anatomical inputs, not measured signs or conductances.
An image-only feedforward receptor fixture cannot represent this recurrent
circuitry on its own.

`cells.feather` preserves body IDs, graph/local indices, types, selection/status
annotations and incoming/outgoing counts. Runtime flags are false and profiles
unassigned. `edges.feather` preserves both endpoint IDs, graph/local indices,
contact counts, original source rows and full-graph CSR edge indices.
`type_pairs.csv` aggregates without pruning. Weak edges, sensory mutual edges
and isolated objects are retained.

Construction scans the incoming CSR in chunks. Independently, every outgoing
edge and every sensory incoming row are combined by set union. Both edge sets,
source-row identities and counts match exactly. Evidence:
`reports/visual_boundary.json` and the artifact manifest under
`data/derived/malecns_visual_boundary_v1`.

## Native feedback interface

The pinned current kernel already computes `I_total = I_feedback + I_photo/15.7`.
`fp_set_neural_feedback` now supplies its per-cell feedback array in author
membrane units (microampere/cm²). Finite signed currents are held until replaced,
cleared at explicit reset and included in checkpoints. Invalid inputs fail before
mutation. Rust exposes `Photoreceptors::set_neural_feedback`.

`tools/check_photon_neural_feedback.py` compares dark receptors under a signed
current pulse on [25,75) ms against independent CPU membrane/adaptation equations
at every tick. Maximum voltage error is 1.4210854715202004e-14 mV. Restore at 50 ms
without reapplying current reproduces the complete final state exactly. Invalid
feedback preserves state. Evidence: `reports/photon_neural_feedback.json`.
This is current injection, not a calibrated MaleCNS circuit or biological test.

Anatomical contact counts are **not automatically converted into currents**.
The mixed CNS runtime still requires conductance/receptor/reversal/scale/delay
profiles and a declared integration schedule. The image fixture retains zero
feedback because it has no downstream CNS. Rocket telemetry must not enter the
neural feedback interface.
