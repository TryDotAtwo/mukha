# Actual window-factor-002: independent numerical approval

NUMERICAL APPROVE for archive
`af79f4143614bb275c84605b8627b4faf28301cad61aad4d8f4c20425c8cd444`
(40875 bytes), reviewed runner `f61ef73c869a0d54170b3e4212c1a5605dc4af4b`.

Portable checker: `tools/check_pang_factor_result.py ARCHIVE.tar.gz`.
Requires NumPy/SciPy; run with Python `-O` supported. It reads actual archive
members in memory, authenticates the frozen plan, prior result and four MAT
inputs, and imports neither runner nor its boundary helper. This is an offline
result checker, not another Molab experiment or a substitute runner.

Evidence: `reports/window-factor-002-numerical-review.json`.
All eight curves and64 unique condition rows passed. Independent derivative
onset, fixed peak, timestamp/frame ends and first crossing recover the exported
indices. Clipped-segment antiderivatives with compensated summation recover
A1/A2, total/direct conservation, denominator magnitude, raw A2/A1 and Q=-A2/A1.
All baseline/conditional/averaged O/E/C/OE/OC/EC/OEC terms and complete
expansions pass, as do48 HHH/SSS area/ratio comparisons against the pinned
measurement001 result and96 factor-isolation comparisons. This does not rerun
measurement001; its archived corners are references.

2152 numerical comparisons:1712 area/clock and440 ratio/contrast.
Max absolute discrepancies:1.3877787807814457e-17 and1.7763568394002505e-15,
respectively, within plan rtol1e-10 and atol1e-14/1e-10.
Eight decoded-result negative controls passed under Python -O: area, sign,
boundary, duplicate row, triple baseline, average, conditional pair, corner
residual. These mutate decoded data after authenticating the original archive;
they demonstrate numerical rejection rather than merely archive-hash rejection.
Run with PANG_FACTOR_ARCHIVE set, unittest discover tests matching
`test_pang_factor_result_checker.py`; tests skip if the artifact is absent.

On these eight curves only: all O indices H/S are2/0 and E indices32/29
(zero-based). Every Q(SSS)-Q(HHH) is negative, but the mechanisms and signs of
individual terms differ. L1_highLum row1 has negative Q in both corners;
absolute-value replacement would lose the intended signed-tail cancellation.
Smallest nonzero |A1| among64 cells is0.00035519065883677617 dF/F seconds.
This observed minimum is not an exclusion threshold or evidence of stability
on other data. Interactions are arithmetic differences, not biological
interactions, p-values, or uniquely attributable causal shares.

Astra3 owns manifest/structure/source identity and operator-intake review;
Astra4 owns interpretation. Archive review cannot independently establish live
remote execution. No Molab request or new kernel run was made by Astra2.
No biological gate is closed: animal/ROI uncertainty, recording-to-stimulus
mapping, physical timing, observation calibration and held-out validity remain
unresolved. Next bounded work should address that crosswalk, not repeat this
window experiment or infer metadata from highLum/lowLum filenames.
