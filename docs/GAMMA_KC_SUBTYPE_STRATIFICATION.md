# Gamma KC subtype and family evidence — 2026-10-05

Foreground MoLab `join_gamma_kc_subtypes` (cell qrWe) and `summarize_gamma_kc_families` (cell isuC) terminated successfully. Exact body-ID joins preserve all 41,460 candidate contacts, original source columns and row order. No missing presynaptic body IDs or subtype annotations. Pinned population: 167,216 objects; 4,064 Kenyon cells and 97 MBONs. Candidates 10704/11402 have the source MBON11(y1pedc>a/B)_L/R annotations; those remain annotation candidates.

| KC annotation family | Contacts onto candidate MBON11 | Robust expected-g1 contacts | Unknown neighborhoods |
|---|---:|---:|---:|
| gamma | 27820 | 22981 | 68 |
| alpha/beta | 13150 | 355 | 3669 |
| alpha-prime/beta-prime | 490 | 223 | 0 |

The explicit family mapping is archived in the family report. All 14 contacting subtype labels are retained. There are 578 non-gamma annotated contacts among the 23,559 robust expected-g1 contacts (fraction 0.02453414830850206). This is not proof of misregistration or erroneous cell identity: preserve these rows as candidates and physiological controls. A spatial g1 filter alone does not isolate gamma-KC physiology.

Primary anatomical evidence: [Aso et al. 2014, Figure 6](https://pmc.ncbi.nlm.nih.gov/articles/PMC4273436/) describes MBON-gamma1pedc and PPL1-gamma1pedc innervation in both gamma1 and the distal pedunculus core. Therefore whole-PED source ROI is not equivalent to pedc, and a g1-only atlas mask is not complete gamma1pedc coverage. This is an applicability boundary, not an admitted MaleCNS pedc mask.

All computation, restoration, joins, hashes and publication were in MoLab; only text and transport are local. Visible durable source files: tools/join_gamma_kc_subtypes_molab.py and tools/summarize_gamma_kc_families_molab.py. No learning or subtype-specific efficacy assignment enabled.

Annotation input: HF 730ad0486c321891428c3f4499818c4accedb474, manifest b91d7732abea2724fc0ca7b59f338eb7ebe00b911998be0d8d6b09bb87109d6b; nodes SHA-256 4335bd9cb4c0098c36e879ae64e97c76ce4fea96a6ad200b16d99aa5d1d0f5e2 at original immutable HF revision 9ec22f9cb1b0358ee8bef432dd1c9c44c36bb4b8.

Final joined table/strata/report/log receipt: private HF TryDotAtwo/faithful-fly-artifacts commit b0038a27253d4ebadb32c2ea2d75785085264a91, manifest 877edae6b332a5e83a8635143cd198f2440389829ef872d7929d6f26a38b3ce7 (4 files verified).

Final family report/summary receipt: commit ee6efa05066f3b3dcb4be6244ff9b19c21080273, manifest 70921cd8b0f7b2d836fe8c6c0f8eb673ff7870bc4c1c451818e35a51a46677cd (2 files verified).

Remote roots: /tmp/fly-gamma-kc-subtypes-20261005 and /tmp/fly-gamma-kc-family-summary-20261005. No data downloaded locally.

Next required evidence: independent bilateral landmark/DAN territory registration; explicit pedc identification instead of whole-PED union; atlas-version sensitivity; no-learning native EPSC diagnostic with subtype controls and a separately justified optical observation model. Whole-project geometry, physiology, local learning, embodiment, three independent KSP series and recordings remain open.
