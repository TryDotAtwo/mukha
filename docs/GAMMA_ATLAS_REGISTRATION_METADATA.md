# Gamma atlas registration metadata

MoLab foreground stage `gamma_atlas_registration`, 2026-10-05. Previously archived inputs were checked against their source SHA-256 before interpretation. Source and completed report were published with verified remote identities.

| Atlas | g1(L) | g1(R) | Finest voxel resolution | Offset |
|---|---:|---:|---|---|
| subcompartments-v1 | 181 | 186 | 256 nm isotropic | 0,0,0 |
| subcompartments-v2 | 190 | 195 | 256 nm isotropic | 0,0,0 |
| subcompartments-v3 | 190 | 195 | 256 nm isotropic | 0,0,0 |

Label IDs differ by atlas version: never reuse v1 IDs for v2/v3. All volumes are uint64, one channel, compressed_segmentation, 64-cube chunks with 8-cube compression blocks. The neuPrint metadata gives 8 nm isotropic voxels, units nanometers. Its hierarchy explicitly places g1–g5 beneath CNS/CentralBrain/MB(L or R)/gL(L or R). Empty ROI descriptions do not independently establish pedc semantics.

The apparent 32:1 scale ratio is insufficient to prove registration or boundary membership. Before classifying contacts, check the source coordinate convention and any layer transforms, preserve atlas version and source generation, and assess contact membership and boundary uncertainty. No spatial mask or plasticity is admitted by this metadata stage.

Immutable private HF dataset: `TryDotAtwo/faithful-fly-artifacts`. Source commit `c28ee999c95e91a50ae2c35d2912a0f0ec534b83`, manifest `7e5581b0ea7fdb83ec05e752951c4235484bf33e203dbc44ee00df731c9fe645`. Final report commit `255e774f78a9235671e78a6b7b847a6c2ad38aa3`, manifest `5a796824fcce2a7a1d0916d95747c16fe5e995f1325965ff696694efb09b2e25`. Both verified. Full atlas metadata, gamma IDs, hierarchy paths, and ROI synapse aggregates are in the report; the aggregates are not KC-to-MBON11 contact counts.
