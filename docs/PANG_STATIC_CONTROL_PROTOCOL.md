# Static cubic control: protocol draft, not permission to run

Status: REVISED for exact-revision peer review; execution remains forbidden. Base public main:
339ac3f1c511960a79dd21777c2476951f2fc5dc.
Scientific basis: PANG_TEMPORAL_003_INTERPRETATION.md (Astra4 1b9f5ee).
No new fit, implementation, experiment or retrospective rescue is part of this document.

## Question and scientific value

Does one specified memoryless nonlinear response mapping compete with the
already frozen temporal mapping on the same six transfer means? This is a
narrow model-adequacy comparison, worth considering because static observation
nonlinearity remains an explicit alternative to temporal processing. It cannot
distinguish arbitrary static maps from memory, neural from indicator dynamics,
or feedforward from recurrent circuitry. It does not close a biological gate.

H0 excludes amplitude-dependent gain as well as history dependence. Hs adds
gain a+d*(c/s_train)^2 without a state: competitiveness would give a concrete
static alternative, not establish memoryless biology. The cubic is the
lowest-order odd zero-intercept polynomial extension of H0, not a search over
nonlinear families. Its imposed Hs(-c)=-Hs(c) symmetry is unvalidated physiology.

The choice to pursue it follows inspection of temporal003 results; any future
comparison is exploratory even though this alternative was named beforehand.
The six curves are held out from coefficient fitting, not from human inspection.
No claim of blind, independent-cohort or animal-heldout validation is permitted.

## Frozen design proposed for review

- Inputs: exactly the eight source MAT files and hashes in temporal003; original
  63-sample grids and processed mean response pairs. No new data selection.
- Fit separately for L1 and L2 on highLum/dark only, once per cell type.
- Hs(c) = a*c + d*c^3/s_train^2, with a >= 0, signed d, and
  s_train = max(abs(c_train)). Freeze s_train from training control alone and
  reuse it unchanged for all transfers. No intercept or new offset correction.
- Minimize original-grid trapezoid-weighted SSE. Divide by training CONTROL
  energy only for reporting and numerical tie decisions, as in temporal003.
- Weighted design columns are c and c^3/s_train^2. Use SVD rank cutoff 1e-12
  relative to largest singular value. Report singular values, condition number,
  coefficients, rank and whether the a=0 boundary is active. Rank below two
  makes Hs nonidentifiable/nonselectable: set cubic predictions and cubic Es
  to null with reason rank_deficient, selected_model=H0, and retain the frozen
  archived H0 predictions/scores separately as labelled fallback outputs.
  Keep all six condition keys; fallback scores are not cubic evidence.
  No universal cubic-superiority conclusion is possible if either cell falls
  back. Do not use a pseudoinverse cubic extrapolation for a deficient design.
- For full rank evaluate the feasible unconstrained least-squares solution,
  the a=0 optimum over d, and explicit nested H0 (d=0). Select minimum loss;
  within 1e-12 + 1e-10*abs(best normalized training loss), prefer nested H0,
  then boundary, then interior. Report all candidate losses and tie decisions.
  Full-rank H0 selection retains selected_model=H0 and the label
  no_resolved_cubic_increment_on_training; report its valid nested predictions
  without calling it successful identification of a nonlinear contribution.
- Nonfinite inputs, nonpositive training control energy or s_train=0 are
  invalid, not grounds for changing scaling or selecting another training curve.
  Nonpositive transfer CONTROL energy or nonfinite predictions/scores produces
  a typed undefined comparison, retaining its key and reason, never a zero,
  numerical tie or excluded condition. Any undefined condition prevents a
  complete six-condition ordering. Invalid training leaves cubic outputs
  undefined for all three transfers of that cell; archived baselines remain
  separately preserved, not relabelled as successful Hs predictions.
- No polynomial-degree search, rectifier, saturation fit, monotonicity tuning,
  tau search, per-transfer gain, baseline, time shift, window or split change.
  The signed cubic need not be monotone or bounded: describe it as a restricted
  phenomenological map, not a calibrated physiological nonlinearity.
- Report signed min/max c for training and every transfer, max(abs(c))/s_train,
  and two separate time-weighted support fractions: sum(w*I)/sum(w), with I
  respectively indicating c outside [min(c_train),max(c_train)] and
  abs(c)>s_train. Thus unseen signed support and excess magnitude are distinct;
  opposite polarity may be inside magnitude support while relying on unvalidated
  odd symmetry. Diagnostics must not trigger clipping, exclusion, new scaling
  or refitting. All weights are the same original-grid trapezoid weights.

With E=sum(w*c^2), u=c^2/s_train^2 and q=w*c^2/E, the weighted Gram determinant
is E^2 Var_q(u). Distinct nonzero magnitudes, not merely opposite signs or many
samples, are needed for rank two. Values only in {0,-s_train,+s_train} identify
only a+d. Numerical rank is not biological precision. Hs has two coefficients;
H1 had two coefficients plus 32 tau choices, so complexity is unequal. Do not
add static model search to equalize computation budgets.

## Frozen comparator and complete outcome policy

Use archived H0/H1 predictions, parameters and scores, without refitting, from
reports/recorded_runs/temporal-transfer-003.tar.gz, SHA256
c74de270799633ed056d8b5e6a61a383a4a96797243e3a0453ec28e8ad2af4bb.
Archive result SHA256:
4f277a6d77d12ea8c15a1b16b89e5f2f8d376af4f84390636b303a22ba04b49a.

For L1 and L2 each, score highLum/light, lowLum/dark, lowLum/light, with
the same per-curve CONTROL energy and original-grid weights. Retain all six.
Report E0, E1, Es and pairwise deltas E0-Es and E1-Es. Compare Es to baseline
Ej using deadband 1e-12 + 1e-10*abs(Ej), j in {0,1}: lower beyond deadband
is improvement, within is numerical tie, higher beyond is deterioration.
Do not turn this floating-point threshold into biological significance.

The primary descriptive output is the entire six-condition sign/error vector,
not a selected aggregate or the previously failed condition alone. A uniform
Hs advantage over H1 would make this specific static alternative competitive
on these reused means; a uniform H1 advantage only disfavors THIS cubic.
Mixed signs imply condition dependence, not a universal winner. Both may be
inadequate, and no absolute adequacy/noise threshold has been identified.
Report training losses separately; unequal flexibility (H1 includes tau search)
prevents treating fit improvements as a complexity-matched mechanism test.

temporal003 all_six_improved=false remains untouched: five improve, while
L2/highLum/light worsens by 0.059714797247573115 normalized error. No new
comparator outcome can replace that experiment's criterion or verdict.

## Exposure ledger: not new independent evidence

The cubic AND training-only scale were named before temporal003 (Astra3
message31), but deliberately not selected for that experiment. Choosing this
follow-up and its final fitting/rank/tie/reporting rules occurs after all six
outcomes were known. Naming an alternative is not preregistration. Training-only
coefficient fitting cannot make this an independent model-selection test.
Astra1 has performed no Hs fitting or variant search; peer reviews report none
in their review work. This is a bounded activity record, not proof about all
unobserved activity. Any future amendment must retain this exposure history.

| Material | Exposure and allowed interpretation |
| --- | --- |
| Two highLum/dark control-CDM mean pairs | Already inspected and used for temporal003 fitting; reused training only. |
| Six high/low-polarity transfer mean pairs | Already inspected, scored and interpreted; parameter-held-out only. |
| Eight historical phase-integral curves and measurement001/window-factor002 outputs | Same processed source material; new summaries or window partitions are not new recordings. |
| CDM anonymous indivResp arrays | Known ROI-level arrays without qualified animal/trial join; neither rows nor time samples establish independent animal n. |
| Known natural-stimulus MAT (52 x 708) | Previously inspected, different stimulus; not a newly acquired matched independent cohort. |
| Zenodo 13367946 computational/imaging source distributions | Alternate distribution/schema evidence alone does not establish new recordings; byte identity requires member comparison, and byte difference does not establish biological independence. |
| Published archives, bundle restore and independent checker runs | Reproducibility evidence for the same data/calculations, not independent biological tests. |

A stronger history-dependence experiment would require matched instantaneous
inputs with differing controlled histories and calibrated observation dynamics.
These processed means do not supply that design. No additional metadata request
to the user is implied, and absence of this design does not erase the bounded
model-comparison question.

## Stop rule on these already inspected means

If separately authorized in the future, perform at most this ONE frozen cubic
comparison and its independent arithmetic/provenance review, then end this
model sweep regardless of win, loss, mixed signs, ties or rank failure. No
degree, offset, asymmetry, saturation, sign-constraint, scale, split, weight,
window, tau-range or cohort-selection changes to repair a condition or obtain
all-six success. Publish the complete outcome, including uninteresting results.

Reopen the mechanism question only with an externally grounded restriction,
validated observation map, genuinely independent source-qualified responses
or controlled history contrast, documented before examining its outcomes and
not selected to explain these residuals. More flexibility on these means may
describe them better but does not supply that new mechanistic evidence. This
is a stop rule for adaptive model searches, not a claim of no remaining
mathematical information and not a project-wide stop or new user data request.

## Review and execution boundary

Astra1 integrates; Astra4 reviews mechanism/equations; Astra2 reviews numerical
constraints, identifiability and comparison fairness; Astra3 reviews provenance,
exposure and baseline freezing. Request explicit exact-revision decisions from
all three. Old temporal003 approvals do not carry over. Pending review is not
consensus. No runner is commissioned here. Even unanimous protocol approval
does not override the user's protocol-only boundary or authorize a new run.
