# Static implementation numerical review

NUMERICAL APPROVE exact runner5c826fe209170800619ccbf4d1829996d5f8610c,
parent approved protocol704843a695224448470a70527ce8db3649570a16.
Separate clean review checkout; protocol file SHA256 remains
9968b2b5a734441483e0a6391e55a4dbb9edf3fe72de445b78a821d48cac4665.
No actual source arrays, baseline archive or real fit were loaded/executed.

Eight independent synthetic tests pass under Python -O in
tests/test_static_independent_analytic.py. Runner APIs are imported as the
subject under test, never to generate expected fits/predictions. No independent
oracle imports the implementation as its definition of the right answer.

The analytical reference uses t=[0,1,3,4], weights=[1/2,3/2,3/2,1/2],
c=[-2,-1,1,2], scale2, v=c^3/4. Therefore <c,c>=7, <v,c>=19/4,
<v,v>=67/16. These exact products fix the expected coefficients and boundary
optimum independently of the SVD implementation.

Checked cases:

- y=2c+3v recovers a=2,d=3,scale2, interior selection and zero residual;
  supplies exact archived-H0-style gain113/28 rather than deriving it with
  runner code. This covers the production supplied-gain path.
- y=1.7c with supplied gain1.7 selects full-rank nested H0, preserving
  no_resolved_cubic_increment_on_training, not an identified nonlinear effect.
- y=-c+3v makes unconstrained a=-1 infeasible; boundary a=0 gives
  d=3-(19/4)/(67/16)=125/67 and is selected.
- Input{-2,0,2} has rank1: no selected cubic or training prediction; transfer
  prediction/residual/Es/SSE remain null, selected_model=H0, separate copied
  archived fallback and undefined pairwise comparisons. Mutating the copied
  fallback does not mutate baseline evidence.
- Distinct magnitudes{0,1,2} restore rank2 and recover a=2,d=3.
- For training c=[0,1,2], transfer c=[-1,1,3], t=[0,1,3], time weights are
  [.5,1.5,1]. Signed outside fraction is1/2, magnitude outside fraction1/3,
  max|c|/scale=3/2. Predictions[-11/4,11/4,105/4] retain training scale2;
  test-specific normalization would fail this analytic check. No clipping.
- Zero training energy rejects; zero transfer energy and invalid training
  give undefined comparisons with preserved archived baselines, not false ties.
- Fixed comparison deadband: half-tolerance is unresolved, twice-tolerance
  is improved/worse as signed; missing Es stays explicitly undefined.

Reproduce with PANG_STATIC_RUNNER pointing to exact reviewed script, then:
`python -O -m unittest discover -s tests -p test_static_independent_analytic.py -v`.
NumPy/SciPy required. Missing environment path skips tests and is not approval.
Tests initially passed, then the first two were explicitly switched to supplied
H0 gains to cover production semantics; all eight passed again. This was new
implementation verification, not repetition of the completed window experiment.

Source inspection confirms SVD rank1e-12, constrained candidate selection/tie
order, fixed scale and original trapezoid weights, null deficient cubic/separate
fallback, fixed reference-specific deadbands and no source-data fitting in
synthetic controls. Scientific meaning remains restricted to this odd static
map; rank is numerical, not biological precision, and extrapolation is not
evidence of calibrated physiology. Nonlinearity absence under full-rank H0 tie
and nonidentifiability under rank failure remain distinct.

Astra3 owns protective/source/split/dispatch/output checks. Its same-commit
approval and Astra1 operator preparation remain separate requirements. This
numerical approval does not establish a completed result. One local run, only
after both approvals, followed by actual-result review is the existing scope;
704843a stop-rule and prior temporal003 all-six=false are unchanged.
