# Gamma contact source ROI crosscheck — MoLab, 2026-10-05

Continuation accepted from chat `Обнови плагин и аудит проекта`; prior owner confirmed all transports terminal and no new work. Authoritative branch: `codex/yamada-independent-plasticity`, draft PR #8. Original full-project gates remain open.

A visible foreground MoLab cell `audit_gamma_source_roi_crosscheck_v2` independently recomputed every stored classification using scalar per-row checks, including the 27 pre/post neighbors and center at index 13. All 41,460 rows agree exactly: 23,559 robust expected-g1; 1,233 center boundary-sensitive; 1,304 near boundary-sensitive; 11,627 outside; 3,737 unknown. All rows are retained.

The source contains `primary_post`, not `primary_pre`. Initial v1 stopped with KeyError before result publication. Its source was archived at HF `aa5ecb749aeb27f4365c83feac72603c915db878`, manifest `5f2190b7731f15b796cd7abd11455e291dcf4c677ffa9dad7250d41213a020e7`. V2 explicitly compares only post endpoints. The empty pre map in the report means not evaluated, not zero contacts.

Among 29,122 post endpoints whose source ROI and atlas labels both identify a side, there are zero L/R mismatches: 12,083 L/L, 17,039 R/R. This is a same-specimen metadata consistency diagnostic, not independent landmark registration.

All 9,189 source-PED post contacts are either atlas background (5,620) or unknown (3,569). No PED post contact has a nonzero known subcompartment center label in this table. This does not identify pedc or justify a PED-to-g1 union; unknown remains unknown.

Source receipt: HF `927d80665e051ad9a9f26009a63013190e6d4b6d`, manifest `453b544e29343487febb7bfa37492a8e498f2e2bf621a204e40339ee24a1ddd4`.
Metadata receipt: same commit, manifest `4590282173f3f13a94f2135cc86df2a54d3dbcc3284f51e03c8fbe191a442d1f`.
Classification input restored and verified: `39c79aac825b2e1e0a22677b2d4b9eaff79cd8f0`, manifest `692bde3910691681fdca1afffef4bc7a46ffbee594af501c0c5144a335cc2fda`.
Final verified result receipt: private dataset `TryDotAtwo/faithful-fly-artifacts`, commit `f0f4c7b0b6f3e002dac2e8487d26da685f18fd3d`, manifest `69f1e13a91774e30e81b6b3f25747fffacf40b0c080ea86ba735737093fb45df`; immutable files `report.json`, `source-roi-atlas-strata.csv`.

Remote root: `/tmp/fly-gamma-source-roi-crosscheck-v2-20261005`. Visible cell `cbge` terminated successfully. Learning remains disabled; contact mask not admitted. No project computation or data download ran locally.

Next gates: join pinned KC subtype annotations; independent bilateral landmarks and DAN territory; gamma1/pedc semantics; atlas-version sensitivity; separately preregistered no-learning EPSC transmission diagnostic. Source ROI consistency does not replace those checks. The original whole-CNS geometry, physiology, embodiment, three-seed KSP evaluation and synchronized recording requirements remain open.
