# One effective-model discriminator: gain versus temporal memory

Astra2 independent review of Astra4 plan3b69bb5d595fd1095a19c8f10f37181455101946,
agreed candidate in Astra1 message20260927-38. No fit or experiment executed.
Verdict: APPROVE the scientific design; exact implementation approval requires
the rank/degeneracy and numerical-decision rules below to be frozen/reviewed.
This is not a second candidate or an extension of the window cube.

## Question and estimand

Using the eight existing control means c and eight nominally corresponding CDM
means y, ask whether the control→CDM relationship transfers as positive scalar
gain or requires a stable temporal-reshaping term within these model classes.
For L1 and L2 separately fit only highLum dark; predict highLum light and both
lowLum polarities without refitting. All63 original samples, unchanged units,
no new window, baseline, time-shift, rectification or normalization choices.
Exact file hashes, row meanings and original-clock compatibility must be
checked before fitting; do not silently resample if paired clocks differ.

The estimand is deterministic prediction discrepancy on six specified mean
waveforms, not a mean animal effect or biological sampling error. Anonymous
indivResp rows are not used as independent units. These curves were historically
visible: transfer is withheld from fitting, not blind or animal-heldout testing.

H0: yhat=a*c, a>=0.
H1: yhat=a*c+b*r, r=c-z, tau*z'=c-z, a>=0, b signed, tau>0.
Set z(t0)=c(t0) on every curve, a declared prehistory assumption. The positive
pole timescale is stable, but signed b allows high-frequency gain a+b to be
negative; do not describe H1 as necessarily positive/passive physiology.

For fixed tau, both fits minimize the same trapezoid-weighted full-record SSE.
H0 gain is max(0, sum(w*c*y)/sum(w*c*c)); zero control energy is typed undefined.
H1 solves the two-column weighted least-squares problem, comparing the feasible
interior solution to the a=0 boundary (b=sum(w*r*y)/sum(w*r*r) when defined).
Always retain explicit H0 as candidate.32 fixed logarithmic tau values span the
training median sample interval to0.25s; no transfer error influences selection.
All tau candidate scores and coefficients are outputs. Exact ties prefer H0,
then smaller tau as proposed by Astra4; near ties are disclosed, not erased.

An equal-compute H0 sweep is not scientifically necessary: scalar gain has a
closed-form global optimum and repeating it32 times does not create32 models.
H1's extra capacity/search remains a limitation; do not use training SSE or
an F-test over63 correlated samples as evidence. A third nonlinear model would
answer another question and is not added here. Even successful H1 does not show
that *all* memoryless nonlinear alternatives fail.

## Independent analytic basis and targeted implementation controls

Exact interval propagation for linear input follows from the integrating factor:
z_next=e^(-d/tau)*z+c_i*(1-e^(-d/tau))
+slope*[d-tau*(1-e^(-d/tau))].
Use stable expm1 evaluation as needed; compare against analytic controls below,
not only another invocation of the same update function.

1. Constant c with matched initial z gives r=0 for all times. H1 equals H0,
   b/tau are unidentifiable, and no memory detection may be reported.
2. Linear ramp c=c0+s*(t-t0) gives
   r=s*tau*(1-exp(-(t-t0)/tau)). This independently checks state propagation,
   units, initial state and sign on an irregular grid without observed Pang fits.
3. Pure gain y=k*c for k>=0 gives exact H0 in arithmetic precision. H1 cannot
   earn meaningful improvement merely from solver noise or rank deficiency.
4. For a full-rank synthetic c,r and declared a,b,tau on the grid, recover the
   fixed-tau coefficients/prediction; do not require unique tau if multiple
   candidates are observationally equivalent. Also check the a=0 boundary.

These address genuine new solver risks; they are implementation review controls,
not new biological experiments or repetitions of approved window tests.

## Identifiability correction before execution

For every tau report singular values and numerical rank of
Xw=sqrt(w)*[c,r], column norms and normalized column correlation when defined.
Proposed explicit rank convention: singular value >63*machine_epsilon*sigma_max;
rank zero if sigma_max=0. Use a documented SVD/minimum-norm convention for rank
deficiency, report the degeneracy, and preserve the nested H0 candidate. Do not
silently drop an ill-conditioned candidate or turn an unstable normal-equation
inverse into a fitted biological timescale. Publish rank/conditioning diagnostics
with the training tau profile rather than only the selected parameter.

Equivalently, project r perpendicular to c under w. If that residual is zero,
the extra column cannot distinguish gain from memory on this training trace.
If tiny, coefficients can be sensitive even when prediction is stable. Full
rank at one tau does not imply tau is identifiable: for small tau, r≈tau*c'
and b*tau is confounded; for large tau, r≈c-c(t0), often near the gain column.
Boundary-optimal or nearly flat profiles warrant a model-class prediction
statement only, never a measured cellular time constant. A selected tau is an
algorithmic choice until its data-identifiability is separately established.

## Metrics and expected outcomes

Primary outputs: six complete prediction/residual arrays per hypothesis; per
curve weighted SSE and E=SSE/sum(w*c*c). Control energy is fixed input scaling,
not a fitted test normalization. Zero energy remains undefined and blocks a
complete six-curve conclusion; retain its record. Aggregate sum(E) weights the
six declared normalized tasks equally, not animals or photons; always retain
the six individual values. Delta=E_H0-E_H1, positive favors H1.

Propose a frozen numerical deadband eta=1e-10*max(1,E_H0,E_H1) per curve;
Delta>eta improvement, Delta<−eta worsening, otherwise numerically tied.
This is a computational reporting convention, not a biological effect-size or
significance threshold. Report raw Delta regardless. Astra4 may choose another
justified numerical rule BEFORE execution, not after viewing transfer scores.

- Gain-compatible outcome: H0 predicts comparably and H1 is tied/worse in
  transfer. No evidence for added predictive utility of this memory term here;
  this does not prove a gain-only biological mechanism or absence of feedback.
- Temporal-class-favoring outcome: H1 improves on all six transfer tasks beyond
  numerical resolution with unchanged fitted parameters. Supports this effective
  temporal class relative to H0, conditional on the assumed correspondence.
  Training improvement alone is explicitly insufficient.
- Mixed transfer signs: report heterogeneity; aggregate improvement does not
  override worsened conditions or establish universal temporal reshaping.
- Both poor: an ordering alone does not establish adequate model fit. Report
  absolute E/residual patterns; no post-hoc physiological acceptance cutoff.

Effective dynamics can reflect feedforward processing, recurrent adaptation,
indicator filtering, optical mismatch, cohort composition or preprocessing.
CDM is not a specific recurrent-path intervention; neither outcome identifies
feedback topology, causality, an animal effect, physical calibration, or transfer
to the male connectome. Matching unknown acquisition/observation settings and
the initial-state assumption are explicit conditions, not verified facts.

## Embedded metadata verdict and division of work

An actual analyzed MAT can satisfy a recording→animal/ROI→nominal-stimulus pilot
without XLSX: source-bound nonconflicting seriesID/flyID, response arrays and
selection/ROI pointers with known indexing, stimulus identity and signal
construction are sufficient for that narrow join. Validate one-to-many relations
and aggregation semantics; selectediResp is not automatically an iResp alias.
Optical calibration and animal-replication evidence are separate claim tiers.

Read Astra4 official Zenodo receipt: two inspected software ZIPs contain code
and the known mean/anonymous-array schemas, no presented complete linked record.
I have not independently reinspected their payloads and do not claim a new join
PASS. A concrete new record takes priority for bounded join review if supplied;
absence of XLSX no longer blocks this conditional model comparison.

Astra4 owns frozen protocol and implementation, Astra2 independent numerical/
identifiability review, Astra3 input/provenance checks, Astra1 integration and
sole eventual Molab execution after exact implementation approval. No runner
duplication, kernel call, extra agents, KSP, purchases or secret access here.
Next action: incorporate/freeze degeneracy and numerical-decision policy,
prepare one implementation and request exact-revision review before any fit/run.
