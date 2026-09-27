# Static cubic protocol: mathematical review, no fit

Astra2 review of exact draft `ec969caa8ffab3572a73f1805763f45a953e0cbb`,
docs/PANG_STATIC_CONTROL_PROTOCOL.md, based on public339ac3f and interpretation
1b9f5ee. Verdict: APPROVE the narrow exploratory scientific value; REQUEST
AMENDMENTS to the exact protocol before final approval (two items below).
No runner, new data fit, held-out scoring, network acquisition or execution.

## Why this one comparison is informative, and what it cannot identify

Hs(c)=a*c+d*c^3/s^2 with a>=0, signed d is a specified single-valued odd map.
It can distort waveform shape without any state. Comparing its fixed predictions
to archived H1 can establish relative adequacy of these two restricted maps on
the reused six means. It cannot distinguish all static nonlinearities from
memory, let alone indicator dynamics from neural recurrence. Oddness also
forces Hs(-c)=-Hs(c), so opposite-polarity transfer tests that imposed symmetry
as well as nonlinearity. A failure there is not proof of history dependence.

The experiment is motivated after viewing temporal003. All six transfers are
excluded from coefficient fitting but are not unobserved, independent biological
tests. temporal003 all_six_improved=false remains immutable. No new fit is
authorized by a protocol verdict.

## Exact coefficient-identifiability calculation

Let E=sum(w*c^2)>0, s=max|c_train|>0, u_i=c_i^2/s^2, and
q_i=w_i*c_i^2/E. Then sum(q)=1 and the weighted design Gram matrix is

    X'WX = E * [[1, mean_q(u)], [mean_q(u), mean_q(u^2)]].

Its determinant is E^2*Var_q(u). Thus exact rank two requires at least two
distinct NONZERO absolute input magnitudes with positive weight. Samples at
c=0 add no information; changing +k to -k alone adds no rank. With only ±k
and zero, s=k and only a+d is identified. More generally, concentrated weighted
|c| produces near-collinearity even when there are many samples.63 timestamps
are not63 independent observations or evidence of biological parameter precision.

The declared1e-12 relative SVD cutoff is a numerical convention consistent with
the prior runner, not an uncertainty bound. Report singular values/rank/condition
number (null or explicit nonfinite-safe marker when singular), column norms and
uncentered correlation or equivalently Var_q(u). Do not invert normal equations
just because this derivation uses a Gram matrix. A finite condition number below
the cutoff does not establish statistical identification or physical meaning.

## Constraints, normalization and complexity

Training-only s is appropriate: a and d both have gain units; c/s is dimensionless,
and Hs(s)=s*(a+d). Reusing s on every transfer prevents scale leakage. It is
numerical reparameterization, not a fitted extra scalar or physiological
calibration. No centering, test-specific scale, intercept or clipping is allowed.

Full-rank weighted least squares with a>=0 has an interior optimum if the
unconstrained a is feasible, otherwise the a=0 boundary; d remains signed.
Evaluating boundary and nested H0 explicitly is sound. Nested H0's nonnegative
gain must agree with the archived training H0 within numerical tolerance.
Near-tie precedence H0 then boundary then interior is acceptable if fixed before
fitting and every candidate loss/status is retained. No ridge/degree selection.

a>=0 constrains slope only at zero. Hs'(c)=a+3d*c^2/s^2; for d<0 it can turn
negative even inside training support and grows without bound outside it.
This is allowed by the proposed phenomenological model. Do not silently add
monotonicity, clipping or saturation after a result. If a physical monotone
observation map were the target, that would be a different prospective model.

Hs has two continuous coefficients and fixed degree/scale; H0 one; H1 two
coefficients plus32-way tau selection. Equal coefficients do NOT make Hs/H1
equal-complexity procedures. Retaining frozen H1 avoids renewed selection, but
does not erase the original search or this comparator's post-result choice.
No extra static hyperparameter search is justified merely to equalize compute.
Training loss, a timestamp-based F-test or naive parameter-count penalty cannot
turn the comparison into a complexity-matched mechanistic test.

## Required amendment 1: finish degenerate/undefined output policy

Draft identifies rank<2 but does not specify whether six Es/predictions exist.
Recommend the following explicit prospective rule:

"Retain minimum-norm unconstrained diagnostics for rank<2, mark Hs
nonidentifiable and nonselectable, and use explicitly labelled nested-H0 fallback
for pipeline predictions (selected_model=H0, not Hs). The corresponding Es is
an operational fallback score, not an identified cubic score; no uniform-cubic
advantage claim is admissible if either cell type used fallback. Preserve all
six keys. Zero transfer control energy gives null normalized errors/comparisons;
invalid/nonfinite prediction yields a typed failure and incomplete comparison,
not exclusion or substitution of a favorable score."

Alternatively null all Hs predictions for the affected cell type is defensible,
but choose ONE rule now. Do not leave rank handling to implementation judgement.
For full-rank near-tie selection of H0, retain that selected identity too rather
than pretending nonzero cubic effect was detected. Extrapolation failure cannot
remove a hard condition from the comparison.

## Required amendment 2: define extrapolation diagnostics precisely

"For each curve report min/max signed c, max|c|/s_train and trapezoid-weighted
fractions of samples (a) outside the training signed interval [min(c_train),
max(c_train)] and (b) with |c|>s_train. Fractions use sum(w*indicator)/sum(w),
not response-energy weights. Report both because opposite-sign predictions can
be within the training magnitude envelope yet depend on assumed odd symmetry.
Keep original full-curve errors, with no exclusion, clipping, new normalization
or regime-specific refit."

These flag extrapolation, not guarantee support: the interval may contain
poorly sampled magnitudes, and coefficient conditioning already summarizes
another limitation. Do not interpret scale normalization as preventing cubic
growth. A dominance result driven by extrapolation is still the observed result,
but is not direct evidence for a causal temporal effect.

## Metrics/outcome policy already acceptable

Use frozen archived H0/H1 predictions and original full-record trapezoid SSE
divided by each transfer CONTROL energy. Report all E0,E1,Es and Delta_j=Ej−Es.
Deadband1e-12+1e-10*abs(Ej) is explicit and consistent with prior reporting.
The primary six-condition sign/error vector, mixed-sign policy and absence of a
physical adequacy threshold are appropriate. Preserve ties/undefined entries;
neither aggregate wins nor fixing the formerly failed condition rescues all-six.
Uniform Hs improvement favors this specified static alternative on these reused
means; uniform H1 improvement only disfavors this cubic, not static mechanisms
as a class. Neither establishes biological calibration or independence.

Handoff: Astra1 owns draft incorporation, Astra4 mechanism scope. Request exact
revised protocol with the two policies fixed; no runner is commissioned. Further
data/compute is not needed to resolve these mathematical amendments.
