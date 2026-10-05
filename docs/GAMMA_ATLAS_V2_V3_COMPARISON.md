# Full gamma contact atlas v2/v3 comparison — MoLab, 2026-10-05

Visible foreground cells Ukjd (acquire_gamma_atlas_v2_chunks) and drsG (compare_gamma_atlas_v2_v3) completed successfully. All computation, decoding, hashing, restoration and publication ran in MoLab; local files contain only text source/report and transport. Initial acquisition stopped before data retrieval because the new parent directory did not exist; repaired in the same cell with parents=True.

The frozen 41,460 contact source rows and coordinate convention are unchanged. V2/v3 finest grids match: resolution 256 nm isotropic, shape 2011x1296x1100, offset zero, chunk 64 cubed, compressed segmentation blocks 8 cubed, uint64, one channel. The full segment-ID-to-label dictionaries are equal, including g1(L)=190 and g1(R)=195.

V2 acquired all 157 planned object identities: 147 available chunks (2,059,044 compressed bytes), ten metadata HTTP404 recorded unknown. Each group of at most ten was immutable-HF verified before advancing. Final input closure commit c78cc667e5d43c9e1c62239ee8959501edca6851, manifest d187e5a57c02b5da5a2a53ef888472fa3dd62883ca856d056870a3129c233c0b. Input source commit a201c3af471feb39096458aa2bed28428ee7a804, manifest 132f170caf57fa279c90e04a08fe7a3913df418ba9786549e3727976ed0d8def. Metadata commit 2fc9cbe2f0073690072fca1d0ee7b10545a7782f, manifest d9882a5e035d748fd7b1d5728e4862ab5f67806c6bbafe9ede8679dc68d464b5.

V2 was freshly decoded with the source-pinned isolated compressed-segmentation runtime; independent format-reader checks agree at 9,408 points across all 147 available chunks. Original source columns are equal row for row to the restored v3 table. Full 27-point pre and post neighborhoods and centers were compared, including unknown markers.

| Status | V2 contacts | V3 contacts |
|---|---:|---:|
| Robust expected-g1 | 23559 | 23559 |
| Center-g1 boundary-sensitive | 1233 | 1233 |
| Near-g1 boundary-sensitive | 1304 | 1304 |
| Outside expected-g1 | 11627 | 11627 |
| Unknown neighborhood | 3737 | 3737 |

Changed status contacts: zero. Changed center labels: zero for both endpoints. Changed neighbor labels: zero for both endpoints, including known/unknown transitions. All 23,559 robust-g1 contacts remain robust in both versions. This establishes v2/v3 stability only for the frozen contacts and 256-nm neighborhoods, not whole-volume equivalence or independent anatomical correctness.

Final verified comparison commit: private HF TryDotAtwo/faithful-fly-artifacts, 36284091f29ac8003b2033e1cda3a14f198b5df0. Manifest d0c8b5441c9c1190c1005f1715b1e14dc93b0f1debcec2a6dd944dceb39d79d9. Seven files verified: comparison-numeric-report.json, comparison-report.json, classified-candidates.parquet, classification-strata.csv, classification-numeric-report.json, classification-report.json, classification.log. Comparison source commit 3296074b14067a1536d3eb38d834ac1322f54f4b, manifest 05ac5e6077888676033a0e3890f194f4897337ef88609acadce2d10486f77862.

Remote root /tmp/fly-gamma-contact-sampling-v2-20261005. Current sources: tools/acquire_gamma_atlas_v2_chunks_molab.py and tools/compare_gamma_atlas_v2_v3_molab.py.

Learning remains disabled; contact mask remains unadmitted. V1 has not been compared. Independent bilateral landmark/MBON dendrite/DAN territory registration, pedc geometry/semantics and subtype/receptor physiology remain open. Source-contact counts are not conductance. Next advance should resolve independent anatomy or the preregistered no-learning native EPSC transmission diagnostic; repeating v2/v3 sampling adds no evidence unless inputs change. All original project acceptance gates remain open.
