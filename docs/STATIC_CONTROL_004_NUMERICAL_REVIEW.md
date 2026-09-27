# Actual static-control-004: NUMERICAL APPROVE

Archive41cb1b831f81248fe3d591d68842147b2e5f1983a416cbd149ad0ac92d07ed4d,
396953 bytes; result2b53849cc007872d60ea145db72051822df8ec7204326f2a96cd396b8fad0dab.
Runner5c826fe209170800619ccbf4d1829996d5f8610c and protocol704843a unchanged.
This actual archive had no saved Astra2 numerical review before this task;
prior0d31749 was synthetic implementation review only.

Independent checker tools/check_static_actual.py takes ARCHIVE and exact
reviewed checkout directory. It imports neither production runner. It uses
c**3/s**2, pivoted QR coefficients, scalar fsum inner products and independent
signed/magnitude indicator sums. Archived H0/H1 predictions/errors are copied
and compared exactly to the nested immutable003 archive, never refitted.
All8 input hashes and reviewed code/protocol bytes match. Astra3 retains
comprehensive manifest/provenance/venue review; this is numerical approval.

4648 floating fields pass tolerance1e-12+1e-10*abs(reference), max discrepancy
3.9968028886505635e-15 at transfer/L2/highLum/1/Es. Checked both training ranks,
singular values/condition numbers, scales, all three candidate coefficients/
feasibility/losses, tie selection, training predictions/residuals, all six
transfer predictions/residuals/SSE/Es, separate support fractions and pairwise
outcomes. Both ranks2 and interior fits; no rank fallback occurred in this
actual result. Existing synthetic fallback evidence is not represented as an
observed fallback here. Five checker corruption controls reject altered
coefficient, prediction, support fraction, frozen baseline and all-six summary
under Python -O, after archive-hash authentication.

L1 a=1.1882771096355287,d=-.3432241025551631;
L2 a=2.0457373543123065,d=-1.049877377852933.
Both Hs-versus-H0 and Hs-versus-H1 vectors are:
**worse, worse, improved, worse, worse, worse**, ordered L1 high/light,
L1 low/dark,L1 low/light,L2 high/light,L2 low/dark,L2 low/light.
Only L1 low/light improves. Es values in that order:
1.16597866991656,.38787396884716263,.14815747424246445,
2.5847816951355647,.8019127276283569,.5670619336514205.

Complete numerical ordering=true; all_six_cubic_better_than_H1=false;
prior_temporal003_all_six_improved=false remains unchanged. Differences are
well beyond the frozen numerical deadbands. Numerical reproducibility does
not mean the model succeeded, and rejecting this cubic is not proof that all
static alternatives fail or that memory/recurrent physiology is identified.
Both low/dark transfers worsen even with zero recorded support-extrapolation
fractions, so failures cannot all be attributed to exceeding training bounds.
That descriptive observation does not establish the cause of any residual.

Machine evidence: reports/static-control-004-numerical-review.json.
Tests: set PANG_STATIC_ARCHIVE and PANG_STATIC_REVIEWED_DIR, then run
python -O -m unittest discover -s tests -p test_static_actual_checker.py -v.
Missing paths skip controls and do not constitute a passed review.

Operator reports one completed LOCAL foreground computation after an earlier
interpreter failed at import before fitting. No reviewer Molab call, production
experiment, protocol revision or model sweep was performed. This is independent
reconstruction of the archived result only. Stop this adaptive model sweep per
704843a; retain the complete negative/mixed outcomes and reused-data limitations.
