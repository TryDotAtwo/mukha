# Huang physiological calibration scope audit — MoLab, 2026-10-05

The author workbook contains aggregated Mean and Sem rows, rather than individual animal recordings. Both sheets (`ACVvsETA`, `OCTvsBEN`) have dimension A1:P18 and 13 nonempty rows: a header plus six population mean/SEM pairs. Six observation sessions are represented: pre-training, after 3x training, after 6x training, 1hr, 3hr and 24hr. The remaining triplet rows are blank, not animal counts.

The author `load_original_data.m` selects the mean and SEM rows. Its exclusion of 24hr is commented out. `fit_nonlinear_models.m` passes all six sessions into the fit, including the late memory measurement. Consequently, predictions from supplied parameters at 24hr are calibration comparisons, not independent validation or an animal-level holdout.

## Exact author parameter selection

`model_functions/Error_nonlinear_activation_function_gether.m` selects these columns before each simulation (one-based MATLAB indexing):

| Odor pair | Selected baseline weight columns |
| --- | --- |
| ACV/ETA | 1, 2, 3, 4, 5, 6 |
| OCT/BEN | 7, 8, 9, 4, 5, 6 |

Preserve the executed column selection above when reproducing the fit. It should not be replaced by an interpretation inferred only from fitting-script comments. The existing native ABI accepts the selected six weights; a new nine-weight native ABI is not necessary for this protocol. At the initial audit, the Python and ctypes simulation harnesses hardcoded a two-session output reshape `(6, 2, 2)`. The initial successful Figure5d replay did not establish coverage of the six-session physiological fitting protocol.

The fitting loss uses `nansum` after SEM division. A future fit must explicitly distinguish intended missing observations from nonfinite model predictions and invalid SEM; nonfinite predictions must never improve the loss by disappearing from the sum.

## Provenance and execution

Author source pin: `schnitzer-lab/Luo_Huang_2024_MB_model` at `5d7c08a9a88f923169a0c3008aca68af421e9a7f`. The unchanged author inputs were previously verified and archived at HF commit `62d48988ff2712c029a61912b4ec6cd0e0e4d8d1`.

This workbook inspection ran in a visible foreground MoLab cell `huang_workbook_scope_audit` (Fxvv), without local data processing or download. The analysis source and input identity were archived before workbook inspection:

- Input/source revision: `e6c2ee01f4f58c3f9129351e43c4ad1dfa5c98a1`; manifest `f863e4715dffeec01c17ae6a806dcd8f3e71213a48fa57a03ac2ab531d77ddef`.
- Completed report revision: `f11f1dbdecce9cd817514225cfe7ad58503c16d7`; manifest `2764ea9b2487c7b7b3adccacb78cec389bee2557709541ce2e0096b7d55220ad`.
- Repository: private dataset `TryDotAtwo/faithful-fly-artifacts`; both receipts verified remote identity.

The full structured workbook audit remains on HF/MoLab. This public document records the conclusion and receipts. No parameters were refitted, no new physiological simulation had yet been executed at that initial audit, and no per-contact learning was enabled.

Next numerical check: preserve the author six-session event schedule, select the original weights for each odor pair, generalize both harness output shapes, and compare the native trajectory with the reference. Its residuals against this workbook must remain labeled calibration. Independent physiological validation still requires separately withheld observations or a separately specified external assay; an animal-level split cannot be created from this aggregated workbook.

## Completed six-session numerical check

The output-shape limitation is now fixed at reference commit `69987d6e38cb9da1a49879267ff4114c5450348b`; the native equations and library remain unchanged. The runner at `2c40b26db4ed355504aa6bfbab5fcf6c5c4ac028` follows all 51 events, including six punishment bouts, for each of four model/odor combinations. All native/reference event activities and six imaging sessions pass the fixed 1e-8 threshold. Missing observations are indexed by original cell addresses and preserved, not compacted or filled with zeros.

| Model / odor pair | Maximum event error | Included calibration cells | Cells per session | Calibration RMSE | SEM-weighted squared loss |
| --- | --- | --- | --- | --- | --- |
| 2-module ACV/ETA | 8.881784197001252e-16 | 36 | 8,8,8,8,2,2 | 3.6352426484484806 | 52.954387311811466 |
| 2-module OCT/BEN | 9.769962616701378e-15 | 24 | 8,4,4,4,2,2 | 4.44866794036931 | 59.50584285973031 |
| 3-module ACV/ETA | 3.552713678800501e-15 | 52 | 12,12,12,12,2,2 | 3.275752012403748 | 74.67672700415724 |
| 3-module OCT/BEN | 3.552713678800501e-15 | 34 | 12,6,6,6,2,2 | 3.8077918402877695 | 65.79173419279853 |

Session order is pre-training, after 3x, after 6x, 1hr, 3hr, 24hr. The workbook advertises six sessions but is sparse: the late sessions provide only two observed cells per odor pair. These residuals use supplied parameters without refitting and are descriptive calibration measurements; they are not a preregistered biological acceptance test.

The updated harness also preserves the Figure5d result: all 108 protocols, 18 panels and 1,944 saved author values pass with maximum error 7.105427357601002e-15. The final MoLab cell is idle. Each of four completed conditions was separately published and verified before the next condition. Final HF commit `f7714e1ae6ef05c448534a28e231e670334312d7`, manifest `c54c5c203f139250acb716b3a06d87947804140886ced5ef74cb8962ff2961a7`; full report and all condition receipts: `reports/huang_six_session_calibration_molab.json`.

Two terminal preparation failures preceded the successful run: missing native provenance files (archived failure log at `eb33ccfc22b3690933a61ae555088ccf3d9ce973`), then an overstrict complete-workbook assumption. Both were corrected without changing the native dynamics, author data, supplied parameters or numerical threshold. The successful Figure5d regression from the second attempt was reused by immutable receipt and checked library/reference hashes; it was not needlessly repeated after the parser-only correction.

Numerical protocol coverage is now established. Independent animal validation, MaleCNS transfer, receptor-dependent contact plasticity, body control and KSP acceptance remain open.
