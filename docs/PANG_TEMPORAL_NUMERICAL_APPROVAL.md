# Exact temporal runner: independent numerical approval

NUMERICAL APPROVE `297201d6a0f2946f0e7b4eae86bf356025219fc1`, reviewed in a
separate detached local checkout. No deposited training or transfer curve was
loaded/scored; no Molab request was made. This is approval of implementation
and frozen numerical policy, not an actual-result or physiological approval.

## Frozen policy explicitly accepted

The following supersedes my alternative suggested values in516daf1:

- SVD rank = count(singular_value >1e-12*sigma_max), strictly greater.
  Rank<2 has explicit nonidentifiable status, retains minimum-norm diagnostic
  coefficients and scores, but is not eligible for selection. Nested H0 remains.
  This disclosed restriction narrows the fitted procedure; it does not prove
  absence of memory if rank excludes candidates.
- Training score = trapezoid SSE / training control energy. Define global best
  among eligible candidates first. Ties have score−best <=1e-12+1e-10*abs(best);
  choose H0 first, otherwise smallest tau. No dependence on traversal updates
  or transfer scores. All32 profiles remain in output, including exclusions.
- Transfer E = trapezoid SSE / that transfer control's energy. Delta=E0−E1;
  improve if Delta>1e-12+1e-10*abs(E0), worsen if Delta below its negative,
  otherwise numerically unresolved. The reference is explicitly E0, not the
  aggregate or min(E0,E1). Raw Delta is retained. These are computational
  thresholds, not significance levels or biological effect-size thresholds.
- Zero training energy is a typed failure; zero transfer energy has null
  normalized scores and no complete all-six conclusion. No data exclusion
  threshold is imposed on finite nonzero energy. Extreme nonfinite arithmetic
  must fail rather than be interpreted scientifically.

I accept this declared1e-12 relative rank convention instead of my earlier
63*epsilon suggestion, and its reference-specific comparison tolerance rather
than my earlier max(1,E0,E1) proposal. Policies were inspected before any real
curve fitting by this reviewer; no post-result policy selection occurred.

## Independently derived synthetic controls

`tests/test_temporal_independent_analytic.py` imports only the exact specified
runner API. Analytic targets never use the runner state recurrence to generate
their expected answers. Nine tests pass under Python -O:

1. Frozen constants and explicit tolerance function.
2. Irregular-grid linear ramps of both signs and a zero ramp: exact
   c−z=slope*tau*(1−exp(−(t−t0)/tau)), z0=c0.
3. Scale-only target1.7*c: selected nested H0 and three novel synthetic ramp
   transfers match with unresolved H0/H1 difference.
4. Memory target .8*c+1.3*r, tau at fixed grid index12: recovered a,b,tau and
   three sign/amplitude/offset-varied synthetic transfer predictions match the
   independently generated analytic target; all three improve over H0.
5. Constant .7 input: all32 candidates rank1, b diagnostic zero, H0 selected.
6. Nearly constant1+1e-14*t: numerical rank/exclusion agrees with frozen cutoff.
7. Zero training energy rejected; zero transfer energy preserves raw SSE=.25
   with undefined normalized error, not apparent successful transfer.
8. Negative unconstrained a: a=0 boundary coefficient checked against an
   independent scalar trapezoid inner-product ratio for b.
9. Synthetic known E0=1: half-deadband ties, twice-deadband improvement and
   worsening classified correctly, without relying on real data outcomes.

Reproduction: set PANG_TEMPORAL_RUNNER to the reviewed script, then run
`python -O -m unittest discover -s tests -p test_temporal_independent_analytic.py -v`.
NumPy/SciPy required. Missing runner variable skips, so an approval requires the
observed nine executed tests, not a skipped-suite exit code. Initial checkout
selected the author's old branch and lacked the file; corrected to exact detached
297201d before running any numerical test. No other runner revision tested.

## Scope and handoff

Code inspection confirms the exact linear-input recurrence, weighted SVD,
constrained a=0 solution, training-only candidate selection, frozen prediction
parameters and explicit state reset. Stability is not parameter identification;
flat/boundary tau and column degeneracy remain interpretive warnings. An
effective temporal-model advantage does not exclude static nonlinear effects,
indicator/cohort/optical differences or identify recurrent feedback.

Astra3 owns protective/input/dispatch/export review; its exact-commit approval
and Astra1 preflight are separate prerequisites. Astra1 alone may run Molab.
No anonymous ROI is counted as an animal. No previous window suite was repeated,
no real held-out target was evaluated, and no second experiment is proposed.
