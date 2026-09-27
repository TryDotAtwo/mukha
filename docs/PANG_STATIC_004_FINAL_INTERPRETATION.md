# static-control-004: restricted cubic fails to transfer uniformly; sweep closed

## Actual result and evidence boundary

Protocol704843a695224448470a70527ce8db3649570a16; unchanged approved
runner5c826fe209170800619ccbf4d1829996d5f8610c. Astra1 reports one actual LOCAL
foreground single-thread CPU calculation, exit0. An earlier default-interpreter
attempt failed at import NumPy before data access, fitting or output creation;
the original failure receipt is retained separately. An existing interpreter
was then used without model/config/source changes. This is not a Molab run,
nor two successful scientific fits. No Molab retry occurred.

Archive:396953 bytes, SHA256
41cb1b831f81248fe3d591d68842147b2e5f1983a416cbd149ad0ac92d07ed4d.
Result SHA256
2b53849cc007872d60ea145db72051822df8ec7204326f2a96cd396b8fad0dab.
Source: Astra1 reports/recorded_runs/static-control-004.tar.gz.
This report reads stored results/parameters; derived percentages and polynomial
gain evaluations below are explanatory summaries, not changed scoring or fits.
Independent actual numerical reconstruction belongs to Astra2; archive/receipt
review belongs to Astra3 and was pending at first writing.

## Frozen six-condition answer

Hs=a*c+d*c^3/s_train^2 was fit only to each cell type's highLum/dark mean.
Its scale is fixed from training. Archived H0/H1 predictions and errors were
not refitted. E is full-record trapezoid-weighted SSE divided by the respective
CONTROL waveform energy, not R², a variance fraction or a biological effect.

| Transfer | Frozen E0 | Frozen E1 | Es cubic | E0−Es | E1−Es |
| --- | ---: | ---: | ---: | ---: | ---: |
| L1 high light | 0.13173203 | 0.09202191 | 1.16597867 | -1.03424664 | -1.07395676 |
| L1 low dark | 0.36366280 | 0.33624117 | 0.38787397 | -0.02421117 | -0.05163279 |
| L1 low light | 0.24528270 | 0.20939333 | 0.14815747 | +0.09712523 | +0.06123586 |
| L2 high light | 0.26213499 | 0.32184978 | 2.58478170 | -2.32264671 | -2.26293191 |
| L2 low dark | 0.73991869 | 0.68365580 | 0.80191273 | -0.06199404 | -0.11825693 |
| L2 low light | 0.47184178 | 0.46396419 | 0.56706193 | -0.09522015 | -0.10309775 |

All six comparisons are defined and beyond numerical tie tolerances. Hs is
better than BOTH baselines only for L1/lowLum/light:39.60% lower error than
H0 and29.24% lower than H1. It loses to both on the other five conditions.
On L1/highLum/light, its error is8.85 times H0 and12.67 times H1; on
L2/highLum/light,9.86 times H0 and8.03 times H1. The remaining losses are
smaller but cannot be discarded: L1 low dark +6.66%/+15.36%, L2 low dark
+8.38%/+17.30%, and L2 low light +20.18%/+22.22% relative to H0/H1 errors.

The secondary sum of normalized errors is E0=2.21457300,
E1=2.10712618, Es=5.65576647. This is not the primary endpoint and does
not authorize a selected aggregate, a new weighting scheme or biological n=6.
The complete vector is worse,worse,improved,worse,worse,worse versus both
baselines. There is no universal ordering in favor of either nonlinear class:
H1 loses to Hs on one condition, and Hs loses on five.

`all_six_cubic_better_than_H1=false`. Separately, the prior experiment's
`temporal003 all_six_improved=false` remains unchanged: H1 previously improved
five H0 comparisons but worsened L2/highLum/light. Adding Hs does not rescue,
relabel or overwrite that negative result.

## Training fit and rank did not establish transfer validity

| Cell | a | d | s_train (fractional dF/F) | Training E0→Es | Weighted condition number |
| --- | ---: | ---: | ---: | ---: | ---: |
| L1 | 1.18827711 | -0.34322410 | 0.02414729 | 0.12792606→0.11662058 | 4.09007 |
| L2 | 2.04573735 | -1.04987738 | 0.02737652 | 0.50090210→0.28153372 | 3.02010 |

Both selected full-rank interior Hs, with no a=0 boundary, no tie and no H0
fallback. Weighted singular values are(0.00744434,0.00182010) for L1 and
(0.00561616,0.00185959) for L2. The rank policy did not silently replace an
unidentifiable cubic. Training error reductions of8.84% and43.79% therefore
coexist with poor transfer, especially for L2. Good solvability and stronger
training approximation do not imply valid extrapolation, biological coefficient
precision or held-out population performance. H1 also had a different search
budget (32 tau choices); this remains a restricted adequacy comparison, not a
complexity-matched mechanism selection test.

## Signed support and amplitude extrapolation

These are frozen CONTROL support diagnostics using time weights, not fractions
of animals, signal energy or variance. Neither diagnostic changes a score.

| Transfer | max|c|/s_train | Time outside signed training interval | Time outside |c|≤s_train |
| --- | ---: | ---: | ---: |
| L1 high light | 2.29046 | 4.84% | 4.84% |
| L1 low dark | 0.79603 | 0% | 0% |
| L1 low light | 1.41651 | 3.23% | 3.23% |
| L2 high light | 1.65166 | 6.45% | 3.23% |
| L2 low dark | 0.95705 | 0% | 0% |
| L2 low light | 1.36709 | 4.84% | 1.61% |

L1 training signed support is[-0.02250496,0.02414729]; L2 support is
[-0.02737652,0.01213484]. In L2, a positive input can leave the signed training
interval well before it exceeds the largest TRAINING absolute amplitude, which
was negative. The two extrapolation diagnostics therefore answer different
questions. The odd symmetry Hs(-c)=-Hs(c) was imposed, not verified physiology.

Both fitted d are negative. Their instantaneous effective gains
g(c)=a+d*(c/s_train)^2 decrease with magnitude and eventually change sign.
At the stored positive high-light control maxima, this gain is approximately
-0.61235 for L1(c=0.05530844) and-0.81831 for L2(c=0.04521669).
Consequently the frozen polynomial predicts approximately-0.03386811 and
-0.03700106 at those positive inputs. This algebraic behavior explains a
concrete extrapolation vulnerability of the chosen unbounded cubic; it is
not observed biological sign reversal or a calibrated saturation law.

Even within the training amplitude range, monotonicity is not guaranteed:
the derivative a+3d*(c/s_train)^2 crosses zero at |c|/s_train≈1.07426(L1)
and0.80593(L2). The latter lies within L2's training magnitude range. These
are descriptive evaluations of frozen coefficients, not new fit constraints.
We do NOT clip, constrain d, introduce saturation or remove high-light inputs.

Extrapolation is NOT the entire explanation: both low-dark curves become worse
despite lying inside their signed training ranges; L1 low-light improves despite
leaving its training range. The result therefore limits this particular common
odd amplitude mapping, rather than supporting a claim that a support check alone
would repair its predictive performance. Small time fractions outside support
also need not imply small squared-error contributions at high amplitude.

## What is and is not learned

The specified static cubic is not a generally successful alternative to frozen
H0/H1 across these six reused conditions. It is competitive on one condition
only. This disproves neither arbitrary static observation nonlinearities nor
feedforward/indicator explanations, and does not make H1 biologically correct.
H1's own nonuniform transfer remains evidence against universal superiority
under its original criterion. Neither model's relative error establishes
absolute physiological adequacy without a justified noise/observation model.

The cubic form was named before temporal003 but chosen for follow-up, with
final policies, after its outcomes were inspected. Programmatic training-only
fitting does not remove human model-selection adaptivity. These are processed
means with uncertain contributor matching, input calibration and observation
transform; anonymous rows and63 timestamps are not independent animal samples.
No biological CI, p-value, causal CDM assignment, identified feedback topology,
male-connectome transfer or independent-cohort validation follows.

## Stop-rule closure

The ONE permitted static control has been calculated. Scientific model-sweep
selection is CLOSED under704843a regardless of this mixed outcome. Only the
already assigned independent numerical/structural result checks and publication
remain. No further model, degree, offset, asymmetry, saturation, scale, split,
window, weighting, tau-range or cohort-selection variant on these means is
proposed or authorized by this report. No rescue of the single failed003
condition and no reinterpretation of either all-six criterion.

Mechanistic conclusions could be reopened only with NEW independent constraints:

- source-qualified independent animal/recording responses and known contributor/
  assignment structure, allowing genuinely separate calibration and validation;
- measured matching of physical stimulus/timing and independently justified
  indicator/processing dynamics, so an effective filter is not mistaken for
  neural feedback;
- controlled identical instantaneous inputs reached through distinct histories,
  with the observation dynamics accounted for, to test static versus effective
  history dependence;
- selective causal perturbation or independently supported circuit constraints
  to distinguish recurrent topology from feedforward/indicator alternatives.

These are conditions for stronger inference, not a new inventory, acquisition
request or proposed run. No new computation or model fit was performed for this
interpretation. Stop-rule closure is not a project-wide claim that no further
mathematical information exists; it ends adaptive mechanism claims based on
further fitting of these same already inspected means.
