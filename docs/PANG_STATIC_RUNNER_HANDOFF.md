# Static-control implementation handoff

Exact approved scientific protocol704843a, unchanged bytes/hash. Later user
authorization permits implementation and one gated local CPU run, superseding
the historical protocol-only execution boundary, not its model/metrics/stop rule.
Astra4 sole implementation owner; Astra2 numerical review; Astra3 protection/
split review; Astra1 sole later operator. No Molab retry. No actual fit by author.

```sh
python tools/run_pang_static_control.py --baseline-archive /path/temporal-transfer-003.tar.gz --output-dir /fresh/static-control-004
python -O -m unittest discover -s tests -p test_pang_static_control.py -v
```

Dependencies: Python3, NumPy, SciPy. Stage tools/run_pang_static_control.py,
unchanged tools/run_pang_temporal_transfer.py and
docs/PANG_STATIC_CONTROL_PROTOCOL.md in the same repository layout. Set BLAS
thread count externally to1 for the operator's single-thread CPU execution.
No subprocess, network or archive-code execution is performed by the runner.

The temporal helper supplies only unchanged array/weight/finite/error/tolerance/
key utilities and constants. Neither temporal fit nor temporal prediction is
called. Its SHA256 is verified alongside the exact protocol SHA before static
analysis. The baseline archive SHA and its manifest/result/eight input hashes
are verified before reading source arrays. Archive members are read in memory,
not executed or extracted as paths. Only meanResp/t are used. Real inputs are
never supplied to author synthetic tests.

All inputs and H0/H1 evidence come from the original hashed archive; there is no
independent mutable --input-dir. Production fit_static receives the archived
H0 gain as nested-candidate gain; archived H0/H1 parameters, predictions and
errors are separately preserved without refitting. Training uses highLum row0
only. The pure analyze(data,baseline) API supports independent synthetic dispatch
and leakage checks without bypassing production archive authentication.

Public APIs:

- fit_static(t,c,y,h0_a=None): training-only static fit. The optional default
  computes a synthetic nested gain; production always supplies archived h0_a.
- support(t,c,training): signed/magnitude support fractions with time weights.
- score_static(t,c,y,training,archived): no fitting, immutable scale; copies
  archived baselines, preserves null cubic plus separately labelled H0 fallback.
- analyze(data,baseline): exactly two training and six transfer records. Zero/
  nonfinite failures remain typed; no row dropping or condition repair.

Full-rank candidates are H0,boundary,interior in declared tie order. Infeasible
interior a<0 is recorded, not selectable. Rank<2 yields no pseudoinverse cubic;
prediction/Es=null, selected_model=H0, separate archived fallback_H0. Full-rank
nested H0 yields valid nested predictions with its exact identity and training
status, not a claim of identified nonlinearity. No universal cubic-superiority
claim is made unless both cells actually select Hs and all six comparisons
are defined. The entire six-vector remains primary. Previous temporal003
all_six_improved is copied unchanged, under an explicitly separate key.

Output directory must not exist. Artifacts: original baseline-temporal003.tar.gz,
two copied scripts, protocol.md, config.json, result.json, manifest.json.
Manifest uses run_id=directory basename and files mapping to bytes/SHA256,
excluding itself. Config is compiled into reviewed code with no policy overrides.
Result stores config/code hashes, version/location disclaimers, two training
records with candidates/parameters/diagnostics/predictions, six transfer records
with frozen baselines, cubic residuals/errors, support diagnostics and complete
pairwise outcomes. Archive contains the original eight inputs transitively;
do not drop it from export. Astra1 supplies actual venue/operator receipt.

CLI exit0 means all six numerical comparisons defined, not biological success
or superiority. Exit2 means saved incomplete comparison, including rank fallback.
An exception/partial directory is never a successful artifact; do not reuse its
path or silently alter protocol. Operator should preserve failure evidence.

Nine synthetic test methods cover known cubic coefficients, constrained boundary,
rank1 on {-s,0,+s}, separate H0 fallback, full-rank H0 tie, exact signed/magnitude
support with unequal time intervals, frozen scale/target-mutation independence,
zero/nonfinite/deadband behavior, exact2+6 dispatch and baseline immutability,
and corrupt archive rejection before fitting. No real data calculation. Both
independent exact-code approvals are needed before Astra1's one run. After its
result review, stop this model sweep as required by704843a, whatever the outcome.
