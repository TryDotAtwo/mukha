# Independent gamma1 plasticity gate

Primary source: [Yamada et al., DOI 10.1113/JP285745](https://pmc.ncbi.nlm.nih.gov/articles/PMC11068490/). This gate stays separate from Handler gamma4 and Huang population-level memory models.

Before native candidate execution, fix gamma-KC/MBON-gamma1pedc contact identity, intervention delivery and EPSC/PPR observation model. Test low-dose forskolin alone, paired KC activation, and KC-only/solvent controls. Track cAMP in active and inactive axons separately. High-dose forskolin and alpha/beta KCs require separate protocols.

Reject a rule whose sole activity-independent cAMP signal necessarily changes all contacts equally. Activity dependence downstream of cAMP remains a candidate, not an established quantitative rule. Report magnitude and time course only against acquired recording or figure data with declared extraction uncertainty. Nonsignificant group differences do not establish exact equality or an equivalence margin.

Raw recordings require an author request; none has been sent. Source acquisition alone cannot validate learning. Plasticity stays disabled pending contact mapping, native intervention comparisons and independent observations. No fitted coefficient, duration or compartment identity is accepted by this document.

## Official atlas label route checked in MoLab

The complete explicitly referenced label lists in official fullbrain ROI v4/v5
contain 90 and 82 labels. Neither names gamma1/pedc separately; both provide
broad gL and PED labels. Source generations, checksums and immutable receipts
are in reports/gamma1_official_roi_labels_molab.json. Full source responses
and the audit report are archived at verified HF revision
1fecf23bc09da213a94b2ef84f3a81c0eb9535c0.

Do not use gL/PED membership as a verified gamma1 contact mask. This audit did
not inspect all alternative ROI sources, neuPrint hierarchy, volumes or meshes.
Continue independent model/physiology replication with explicit compartment
uncertainty while investigating a source-backed local assignment; the absence
of atlas labels does not justify inventing or enabling a teaching mask.


## Explicit subcompartment labels and coordinate evidence (2026-10-05)

The official malecns-subcompartments v1/v2/v3 property lists explicitly contain
g1–g5 for both hemispheres (190/199/199 total labels). The neuPrint debug
hierarchy independently places them under MB(L/R)/gL(L/R). This changes the
available anatomical route; the earlier scoped fullbrain v4/v5 finding remains
valid for those lists only. See docs/MALECNS_SUBCOMPARTMENT_LABEL_AUDIT.md.
Verified metadata report HF commit b5b5a270dd04a4d0bed222bd18e5eeef025fa83b.

Pin v3 g1 IDs 190(L), 195(R), finest 256-nm isotropic resolution and zero offset.
Do not reuse v1 IDs (181/186). The official Neuroglancer dataset state attaches
v3 directly in the 8-nm MaleCNS space without an additional transform. The
publisher download documentation explicitly specifies synapse voxel units of
8 nm. These support the proposed coordinate scale, but do not replace bilateral
landmark/territory checks. See docs/GAMMA_ATLAS_REGISTRATION_METADATA.md and
docs/NEUROGLANCER_TRANSFORM_AUDIT.md.

The original 463640 KC-MBON contact shards have been restored and verified in
current MoLab. All 41460 MBON11 candidate contacts remain in a fixed table. Their
pre/post positions plus 27 coarse-neighbor positions require 157 atlas chunks.
The plan/table were archived before acquisition at f4153cc33a77074a13563ed6e2f3213b647f1c91.
A real chunk was read by two independent decoders agreeing at 126 points; its
first provisional contact sampled label zero, and was not promoted to gamma1.
See docs/GAMMA_CONTACT_SAMPLING_PLAN.md and docs/REAL_ATLAS_CHUNK_DECODER_PROBE.md.

Mask admission still requires gamma1 versus pedc semantics, bilateral registration,
MBON/DAN territory correspondence, retained uncertain/outside contacts and exact
total reconciliation, and atlas-version/boundary sensitivity. Expert guidance
from Astra is advisory, not independent source replay. A paired-pulse no-learning
transmission assay can falsify a model but cannot validate anatomical registration.
No contact plasticity is enabled by these source or decoder checks.
