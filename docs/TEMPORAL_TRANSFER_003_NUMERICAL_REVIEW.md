# Actual temporal-transfer-003: numerical approval, mixed scientific outcome

NUMERICAL APPROVE archive
`c74de270799633ed056d8b5e6a61a383a4a96797243e3a0453ec28e8ad2af4bb`,336371 bytes,
exact runner `297201d6a0f2946f0e7b4eae86bf356025219fc1`.
Operator reports one LOCAL foreground CPU run, not Molab: native connection
failed before any task submission. Numerical review does not independently
observe that execution venue; Astra3 handles receipt/provenance confirmation.

Independent checker: `tools/check_temporal_actual.py ARCHIVE REVIEWED_RUNNER`.
It never imports/executes production runner code. The latter path is used only
for byte equality and literal input hashes; use exact297201d source. State is
reconstructed by integrating-factor convolution independently from t0 at every
sample, with24-node Gaussian quadrature on each original linear segment.
Full-rank coefficients use pivoted QR least squares (not runner SVD coefficient
reconstruction); SVD still implements the frozen rank diagnostic. Weighted
scores and aggregation use math.fsum. All8 input hashes match, archived runner
bytes match reviewed source, and frozen rank/tolerance policy remains unchanged.

Both32-tau training profiles checked in full: parameters, unconstrained
diagnostics, ranks, singular values, norms/correlations, SSE/normalized score,
selection/ties/warnings and training predictions. All six transfers checked:
unchanged parameter objects, input/target/time arrays, state/predictions/residuals,
energies, raw/normalized SSE, signed improvement and outcome. Summary checked.
4589 floating fields agree; largest absolute discrepancy2.914335439641036e-15
is training/L2/profiles/29/b. Validation tolerance1e-12+1e-10*abs(reference);
this does not change the frozen selection/classification tolerances.

Selected parameters reproduced independently:

| Cell | a | b | tau seconds |
| --- | ---: | ---: | ---: |
| L1 | 1.070273129323712 | -0.17260376731346147 | 0.016095823101123306 |
| L2 | 1.3609614178392453 | 0.21729254631675624 | 0.022369712811886065 |

These are selected algorithmic parameters, not identified cellular constants.

| Transfer | E0 | E1 | E0−E1 |
| --- | ---: | ---: | ---: |
| L1 high light | .1317320315 | .0920219135 | +.0397101180 |
| L1 low dark | .3636628029 | .3362411740 | +.0274216290 |
| L1 low light | .2452827048 | .2093933325 | +.0358893723 |
| L2 high light | .2621349863 | .3218497835 | -.0597147972 |
| L2 low dark | .7399186884 | .6836557957 | +.0562628926 |
| L2 low light | .4718417846 | .4639641855 | +.0078775992 |

All signs are beyond the predeclared numerical deadband. Sum improvement is
0.10744681387342236, but `all_six_improved=false`. The all-six predictive claim
is NOT met. Five improved conditions cannot erase the worsened L2/high/light
condition. This is a mixed transfer outcome under the frozen protocol, not
grounds to change split, tau grid, scoring, sign constraints or tolerances.

Tests for this new checker: one independent analytic-ramp convolution check
plus six decoded-result corruption controls (unselected profile score, selected
coefficient, prediction, residual, heldout error, all-six aggregate). All7 pass
under -O; corruption is inserted after archive authentication so rejection
tests numerical checks rather than just archive SHA. Set PANG_TEMPORAL_ARCHIVE
and PANG_TEMPORAL_RUNNER and run unittest discover for
`test_temporal_actual_checker.py`; absent paths skip corruption controls.
Machine evidence: `reports/temporal-transfer-003-numerical-review.json`.

This is deterministic comparison on historically observed means, with unknown
animal membership/optical/cohort comparability, not six independent animals,
blind/animal-heldout validation, physiological adequacy or recurrent-feedback
identification. No protocol retuning, new Molab request, window repeat or second
scientific experiment was performed; local calculations here are independent
checks of the completed artifact. Astra4 owns broader interpretation; Astra3
owns structure/source/receipt audit. Numerical evidence is ready for integration.
