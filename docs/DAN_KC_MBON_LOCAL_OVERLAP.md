# Same-KC DAN/MBON11 local overlap — 2026-10-05

MoLab foreground daXv completed with immutable input receipts verified before calculation.
All12072 DAN→knownKC partner rows retained. For each DAN contact, match body_post to body_pre in full41460 candidate KC→MBON11 rows, then nearest SAME-CELL KC presynaptic point to the DAN→KC postsynaptic point. Coordinate units8nm verified from pinned convention.
12040contacts matched;32unmatched retained with null distance/-1 index.3059 exhaustive nearest-point crosschecks passed (one per matchedKC body). Full original DAN fields retained.
Result HFb4f568e0769781a48e5c37e654ca3dfcaa84a172
Manifest dce3f44aba0f174209e87388065075c6b48ef198d535bf31410afa97d598d271
Source HFbc451c27f330895c538f247f87ba9ebc261a10d4
Remote/tmp/fly-dan-kc-mbon-local-overlap-20261005
Artifacts dan-kc-local-distances.parquet and report.json contain all rows and subtype/ROI strata.

Examples PED medians in nm, body11327:
KCab-c L1237.856/R870.427;KCab-m L1059.177/R578.138;KCab-s L1041.014/R712.045.
KCab-p L11226.215/R21272.354 illustrates broad PED/subtype does not specify a single local region. Other strata p95 can reach tens of microns. No distances discarded.
Body11900 KCab-c L1645.885/R711.236;KCab-m L913.178/R634.880;KCab-s L1177.224/R683.894.

Evidence is exact shared KC identity plus Euclidean local distances. It does NOT prove same neurite path, shared bouton, same receptor, transmitter diffusion range, pedc segmentation or plasticity. Query output point nearest index references original41460-row table, not a neuron ID. Matching can use eitherMBON11 candidate; no presumed hemisphere mapping.
Next: intersect both contact endpoints and compartment/region at fine registered anatomy; preserve spatial tails and unmatched cases. Do not pick a radius to force an admitted pedc mask. Physiological calibration remains independently required; no learning enabled.
