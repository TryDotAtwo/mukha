# Complete MBON11 candidate atlas sampling plan

MoLab foreground `plan_gamma_contact_sampling`, 2026-10-05, selected all 41460 previously reconciled KC contacts onto candidate MBON11 body IDs 10704 and 11402. All original contact shards were reverified via immutable HF receipts. Pre and post coordinates and the 27 neighboring coarse voxel positions require 157 v3 atlas chunks. Decoded memory upper bound: 329252864 bytes. Candidate coordinate ratio remains 32 source voxels per atlas voxel; it is not admitted registration.

Broad source post-ROI strata include 14440 gL(R), 10844 gL(L), 5079 PED(R), 4110 PED(L), 3026 CentralBrain-unspecified and other lobar/outside contacts. No stratum is discarded. Under the provisional 8-nm coordinate convention, pre-post distance median is 155.5378 nm and maximum 540.5183 nm; these values are a plausibility diagnostic, not proof of units.

The candidate table and complete immutable chunk acquisition plan are verified in private HF `TryDotAtwo/faithful-fly-artifacts`, commit `f4153cc33a77074a13563ed6e2f3213b647f1c91`, manifest `e0481ebae5f585933edcfbfe16f41d2dc19ead452918ffa16a49d3ed094895f0`. Source receipt: `21918918df72fddd4c2f6d31b4312af8e3aef3cb`, manifest `7347a78c6a50ef6dfcbdb60fdf3cfbf407aa5c1dc9837c8f6ab410b5ab3ae2c0`.

Atlas acquisition is a separate foreground stage. Each completed group of at most ten generation-pinned objects is archived and verified before advancing. Missing object metadata is recorded as unknown; it is not silently interpreted as zero. Contact classification, anatomical registration, pedc semantics, physiological acceptance and learning remain open.
