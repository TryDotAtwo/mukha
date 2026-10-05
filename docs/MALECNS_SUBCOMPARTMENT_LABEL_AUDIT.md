# MaleCNS gamma subcompartment metadata audit

Executed in the visible MoLab foreground cell `neuprint_subcompartment_audit` on 2026-10-05. All source acquisition, integrity checks, label analysis, and hashing ran in MoLab. No volume or contact classification was performed.

The official `rois/malecns-subcompartments-v1/v2/v3` segment property lists contain explicit `g1(L)` through `g5(L)` and `g1(R)` through `g5(R)`. Their complete label counts are 190, 199, and 199. `Neuprint_Meta_debug.json` independently includes these names in `roiHierarchy` and `roiInfo`. The earlier absence of these labels in fullbrain ROI v4/v5 does not apply to these subcompartment atlases.

Sources were downloaded from generation-pinned GCS object URLs, checked against published byte counts and MD5, and archived to private HF before dependent interpretation. Source closure: `94ccff51bb3f455c18afa3ff5e32eba450a55a33`; metadata inputs: `39cbd678cba937ba72380cbe8586ce70e0f31000`; property inputs: `c4595a328425938c48d7d589d01d303bfbf04309`.

The complete machine-readable report is preserved in private dataset `TryDotAtwo/faithful-fly-artifacts`, immutable commit `b5b5a270dd04a4d0bed222bd18e5eeef025fa83b`, manifest `manifests/d8e74cf1543457ced6ed3796708f75192aec6038da52e6b4ba578cf9c81d6e5a.json`. Remote identity and all reported objects were verified.

## Remaining admission gate

Explicit names establish metadata availability only. Before a gamma1/pedc contact mask can be admitted, verify spatial registration, voxel scale, atlas label IDs, boundary semantics, and classification of the exact KC-to-MBON11 contact coordinates. No contact-level plasticity has been enabled. This audit provides neither physiological validation nor a completed whole-animal or KSP experiment.
