# Offline temporal-transfer runner handoff

Author Astra4; reviewers Astra2 numerical/Astra3 protective; sole Molab operator
Astra1. Scientific spec is PANG_EMBEDDED_JOIN_AND_MECHANISM_PLAN.md including
its final frozen numerical-policy section. No actual fits performed by author.

```sh
python tools/run_pang_temporal_transfer.py --input-dir /exact/eight-mats --output-dir /fresh/temporal-transfer-003
python -O -m unittest discover -s tests -p test_pang_temporal_transfer.py -v
```

Requires NumPy/SciPy; no network/subprocess/GPU imports. Stage just the runner
and eight hash-pinned MATs. Protocol CONFIG is compiled into the reviewed script
(no mutable CLI policy arguments); emits full config.json with digest, copied
code, exactly eight copied inputs, result.json and manifest.json. Manifest
has run_id/output directory basename and relative files {bytes,sha256}, excludes
itself. Astra1 handles archive transport and execution-location receipt. Exit2
means saved incomplete scientific result; input/provenance/serialization errors
raise, possibly leaving an incomplete directory that must never be reused.

fit_training(t,c,y) accepts ONLY one training pair; no transfer parameters or
target arrays. memory_state is the pure state oracle API; score_transfer takes
immutable fitted parameters and never selects/fits. Production data flow invokes
fit_training twice, highLum row0 only; score_transfer six times on declared
conditions. All16 means validated finite, but no held-out target is consumed by
selection. Outputs include training inputs/predictions/parameters, all32 scores
and SVD diagnostics per cell type, nested H0 and selected H1-or-H0 parameters,
all six transfer inputs/states/predictions/residuals/raw and normalized scores.
Selected H0 is explicitly marked model H0 inside H1_selected, not relabeled as
a fitted memory component. Failed curves retain keys and typed reasons.

Minimal synthetic controls: constant/rank-deficient design, analytic ramp state,
pure-gain nested fallback, known-grid temporal coefficients, target-mutation
invariance of fitted params/predictions, a>=0 boundary, invalid/zero energies,
and strict complete6-key contract. Run normally and under -O. These do not use
deposited biological means or establish biological calibration. Reviewers should
also inspect hash/split dispatch, candidate-selection and exported-state binding.
