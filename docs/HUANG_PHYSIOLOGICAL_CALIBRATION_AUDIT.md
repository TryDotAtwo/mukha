# Huang physiological calibration scope audit — MoLab, 2026-10-05

The author workbook contains aggregated Mean and Sem rows, rather than individual animal recordings. Both sheets (`ACVvsETA`, `OCTvsBEN`) have dimension A1:P18 and 13 nonempty rows: a header plus six population mean/SEM pairs. Six observation sessions are represented: pre-training, after 3x training, after 6x training, 1hr, 3hr and 24hr. The remaining triplet rows are blank, not animal counts.

The author `load_original_data.m` selects the mean and SEM rows. Its exclusion of 24hr is commented out. `fit_nonlinear_models.m` passes all six sessions into the fit, including the late memory measurement. Consequently, predictions from supplied parameters at 24hr are calibration comparisons, not independent validation or an animal-level holdout.

## Exact author parameter selection

`model_functions/Error_nonlinear_activation_function_gether.m` selects these columns before each simulation (one-based MATLAB indexing):

| Odor pair | Selected baseline weight columns |
| --- | --- |
| ACV/ETA | 1, 2, 3, 4, 5, 6 |
| OCT/BEN | 7, 8, 9, 4, 5, 6 |

Preserve the executed column selection above when reproducing the fit. It should not be replaced by an interpretation inferred only from fitting-script comments. The existing native ABI accepts the selected six weights; a new nine-weight native ABI is not necessary for this protocol. The current Python and ctypes simulation harnesses, however, hardcode a two-session output reshape `(6, 2, 2)`. Their successful Figure5d replay does not establish coverage of the six-session physiological fitting protocol.

The fitting loss uses `nansum` after SEM division. A future fit must explicitly distinguish intended missing observations from nonfinite model predictions and invalid SEM; nonfinite predictions must never improve the loss by disappearing from the sum.

## Provenance and execution

Author source pin: `schnitzer-lab/Luo_Huang_2024_MB_model` at `5d7c08a9a88f923169a0c3008aca68af421e9a7f`. The unchanged author inputs were previously verified and archived at HF commit `62d48988ff2712c029a61912b4ec6cd0e0e4d8d1`.

This workbook inspection ran in a visible foreground MoLab cell `huang_workbook_scope_audit` (Fxvv), without local data processing or download. The analysis source and input identity were archived before workbook inspection:

- Input/source revision: `e6c2ee01f4f58c3f9129351e43c4ad1dfa5c98a1`; manifest `f863e4715dffeec01c17ae6a806dcd8f3e71213a48fa57a03ac2ab531d77ddef`.
- Completed report revision: `f11f1dbdecce9cd817514225cfe7ad58503c16d7`; manifest `2764ea9b2487c7b7b3adccacb78cec389bee2557709541ce2e0096b7d55220ad`.
- Repository: private dataset `TryDotAtwo/faithful-fly-artifacts`; both receipts verified remote identity.

The full structured workbook audit remains on HF/MoLab. This public document records the conclusion and receipts. No parameters were refitted, no new physiological simulation was executed, and no per-contact learning was enabled.

Next numerical check: preserve the author six-session event schedule, select the original weights for each odor pair, generalize both harness output shapes, and compare the native trajectory with the reference. Its residuals against this workbook must remain labeled calibration. Independent physiological validation still requires separately withheld observations or a separately specified external assay; an animal-level split cannot be created from this aggregated workbook.
