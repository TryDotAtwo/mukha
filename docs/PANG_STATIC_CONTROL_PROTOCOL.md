# Static cubic control: protocol draft, not permission to run

Status: PROPOSED for peer review. Base public main:
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
  makes the cubic fit non-identifiable at this cutoff: retain that diagnostic,
  do not label the nested linear prediction a successful cubic fit.
- For full rank evaluate the feasible unconstrained least-squares solution,
  the a=0 optimum over d, and explicit nested H0 (d=0). Select minimum loss;
  within 1e-12 + 1e-10*abs(best normalized training loss), prefer nested H0,
  then boundary, then interior. Report all candidate losses and tie decisions.
- Nonfinite inputs, nonpositive training control energy or s_train=0 are
  invalid, not grounds for changing scaling or selecting another training curve.
- No polynomial-degree search, rectifier, saturation fit, monotonicity tuning,
  tau search, per-transfer gain, baseline, time shift, window or split change.
  The signed cubic need not be monotone or bounded: describe it as a restricted
  phenomenological map, not a calibrated physiological nonlinearity.
- Report control amplitude ranges and transfer/train amplitude ratios as
  descriptive extrapolation diagnostics. Do not use them to exclude conditions.

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

## Review and execution boundary

Astra1 integrates; Astra4 reviews mechanism/equations; Astra2 reviews numerical
constraints, identifiability and comparison fairness; Astra3 reviews provenance,
exposure and baseline freezing. Request explicit exact-revision decisions from
all three. Old temporal003 approvals do not carry over. Pending review is not
consensus. No runner is commissioned here. Even unanimous protocol approval
does not override the user's protocol-only boundary or authorize a new run.
