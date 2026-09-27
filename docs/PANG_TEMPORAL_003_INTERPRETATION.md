# temporal-transfer-003: mixed conditional transfer, not a universal advantage

Actual execution: one LOCAL foreground CPU run by Astra1, approved runner
297201d6a0f2946f0e7b4eae86bf356025219fc1. Molab session discovery failed
before task code was submitted; no remote experiment was executed and no HTTP
status was established. This result must not be labeled a Molab execution.

Archive SHA256 c74de270799633ed056d8b5e6a61a383a4a96797243e3a0453ec28e8ad2af4bb,
336371 bytes. Result SHA256
4f277a6d77d12ea8c15a1b16b89e5f2f8d376af4f84390636b303a22ba04b49a.
Source: Astra1 outputs/temporal-transfer-003/temporal-transfer-003/result.json.
Astra4 read stored parameters/profiles/errors and summarized them; no fitting,
simulation, boundary changes or test-driven parameter choice was performed.
Astra2 actual numerical reconstruction and Astra3 archive/provenance verdicts
were pending when this report was written.

## Fixed question and answer

H0 is scale-only yhat=a*c. H1 is yhat=a*c+b*(c-z), tau*z'=c-z,
with z(t0)=c(t0). Each cell type was fit only on highLum dark. Predictions on
highLum light, lowLum dark and lowLum light were frozen transfers, not newly
optimized fits. All63 samples on original t enter the same weighted loss.

The predefined question was whether H1 improves ALL SIX transfers beyond the
numerical deadband. Answer: NO. Five improve; L2/highLum/light worsens.
`all_six_improved=false` is the appropriate verdict, not a near-pass. Training
improvement, five favorable signs, or aggregate improvement cannot replace the
declared criterion. This does not prove H0 adequate either.

## Errors in every transfer

E = trapezoid-weighted SSE divided by that curve's CONTROL waveform energy.
E is dimensionless; it is not R², variance explained, an animal effect size,
or error normalized by CDM target energy. Percent change below is only the
descriptive reduction relative to H0's error on the SAME curve.

| Cell / nominal level / polarity | E0 scale | E1 filter | E0−E1 | H0 error reduction |
| --- | ---: | ---: | ---: | ---: |
| L1 high light | 0.13173203 | 0.09202191 | +0.03971012 | +30.14% |
| L1 low dark | 0.36366280 | 0.33624117 | +0.02742163 | +7.54% |
| L1 low light | 0.24528270 | 0.20939333 | +0.03588937 | +14.63% |
| L2 high light | 0.26213499 | 0.32184978 | -0.05971480 | -22.78% |
| L2 low dark | 0.73991869 | 0.68365580 | +0.05626289 | +7.60% |
| L2 low light | 0.47184178 | 0.46396419 | +0.00787760 | +1.67% |

All differences exceed the frozen numerical comparison tolerance; none is
a roundoff tie. The smallest positive improvement is not thereby biologically
meaningful: the tolerance distinguishes floating-point effects, not physiology.

For reference, unnormalized SSE in (fractional deltaF/F)^2 seconds:

| Transfer, same order | SSE0 | SSE1 |
| --- | ---: | ---: |
| L1 high light | 7.26573409e-6 | 5.07550629e-6 |
| L1 low dark | 4.44224684e-6 | 4.10728367e-6 |
| L1 low light | 5.82415467e-6 | 4.97197369e-6 |
| L2 high light | 1.02857879e-5 | 1.26289079e-5 |
| L2 low dark | 1.18930619e-5 | 1.09887219e-5 |
| L2 low light | 1.19587908e-5 | 1.17591337e-5 |

The sum of normalized errors is2.21457300→2.10712618, improvement0.10744681.
L1 accounts for0.10302112 (sum0.74067754→0.63765642). L2 contributes only
0.00442569 (sum1.47389546→1.46946976): high-light deterioration nearly cancels
both low-level improvements. An aggregate-only summary would conceal the
important transfer failure. No new weights are selected to change this result.

## Parameters and what the selected filter means

| Fit (high dark only) | H0 gain | H1 a | H1 b | tau ms | Training E0→E1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| L1 | 1.01775590 | 1.07027313 | -0.17260377 | 16.095823 | 0.12792606→0.12180227 |
| L2 | 1.47452885 | 1.36096142 | +0.21729255 | 22.369713 | 0.50090210→0.48940080 |

Training error reductions are4.79% and2.30%, respectively. H1's larger parameter
and tau-search flexibility prevents interpreting this as evidence of mechanism.
Neither a=0 boundary nor nested H0 was selected.

Ignoring the finite-record initial transient, the effective transfer function
is a+b*s*tau/(1+s*tau). Its DC gain is a, and high-frequency limit is a+b.
For L1 these are1.07027 and0.89767: relative attenuation of rapid components.
For L2 they are1.36096 and1.57825: relative enhancement of rapid components.
This is a characterization of the RESPONSE-TO-RESPONSE fitted filter, not
of a photoreceptor, synapse, membrane conductance or physical-stimulus response.
Opposite b signs are not identified excitation/inhibition or CDM receptor signs.

L1's dark-trained transformation transfers better than H0 to all three tested
conditions. L2's does not transfer uniformly even when the nominal luminance
is retained and only flash polarity changes. This locates a failure of this
universal L2 linear response-mapping assumption; it does not isolate its cause.
Do not repair it by changing tau, baseline, windows or gain on the failed curve.

## Numerical rank versus timescale identification

All32 candidates for each cell have weighted rank2 at the declared cutoff.
Selected weighted singular values are:

- L1:0.00697878456 and0.00284142337; condition number2.45609;
  normalized column correlation0.55725.
- L2:0.00558869756 and0.00206741276; condition number2.70323;
  normalized column correlation0.72706.

Across the grid, condition numbers range2.438–3.903 for L1 and2.489–6.566
for L2. Thus exact/rank-threshold collinearity did not drive the choice. Both
minima are interior (indices6 and9), each with one numerical winner and no
reported rank/tie/boundary warning. This establishes numerical solvability of
the chosen fixed-tau regressions, NOT structural or statistical identification.

L1's runner-up17.962313ms has score0.1218280839 versus0.1218022714:
gap2.58125e-5, versus tie tolerance1.31802e-11. The gap is only0.02119% of
the minimum error. L2's runner-up20.045243ms has score0.4894053752 versus
0.4894007989 at22.369713ms: gap4.57631e-6, versus tolerance4.99401e-11,
only0.000935% of the minimum error. The scores are numerically distinct but
the nearby profiles are practically flat on the scale of total residual error.
No noise model is available to turn those gaps into a confidence interval.

Tau is selected on a32-point logarithmic grid8.333333–250ms, with c-dependent
refitted a,b at each point. It is not a measured16.1ms or22.4ms biological
time constant. No continuous refinement, alternative initialization or interval
search was performed. Fixed z0=c0 and unknown pre-recording history remain
limitations; first-sample alignment and fluorescence filtering can affect this
effective timescale without any change in neural feedback.

## Alternatives not excluded

1. Static nonlinear observation: a single-valued y=a*c+d*c^3 can violate H0
   without memory. H1's partial improvement cannot eliminate that alternative.
2. Indicator/processing dynamics: bleaching baseline fit, ROI selection,
   averaging, filtering, resampling and fluorescence-to-voltage transforms
   were not identified separately. Effective temporal differences could arise
   there rather than in neural recurrence.
3. Unverified matching: nominal high/low filenames do not establish equal
   illumination, stimulus delivery, animal composition or recording history
   between control and CDM. Within-condition means can have different
   contributors. CDM is not a specific feedback-path blockade.
4. Design limitations: two training processed means, six transfer processed
   means, previously observed data, no source-qualified animal-heldout split.
   Time samples and anonymous ROI rows do not provide independent animal n.

Therefore this experiment answers a bounded effective-model transfer question.
It neither establishes universal filter superiority nor validates biology,
causal recurrence, physical stimulus calibration or male-connectome transfer.

## Next step only if the remaining question merits it

No experiment is launched by this report. Close independent numerical and
archive reviews first; preserve the mixed result and current predictions.

One genuinely targeted, but narrower, follow-up question would be whether the
previously named memoryless cubic alternative accounts for the same transfers
as well as frozen H1. A prospective separate comparison could fit
Hs=a*c+d*c^3/s_train^2, s_train=max|c_train|, on the SAME high-dark training
pair per cell type, with a>=0, signed d and rank diagnostics; no tau search,
new normalization, changed split or failed-curve refit. Compare its six errors
to the already frozen H0/H1 predictions. A held-out advantage for Hs would
show an explicit static explanation is competitive; an advantage for H1 would
only reject THIS restricted static alternative, not arbitrary static maps.
Both may fail. Because proposal selection occurs after seeing the current
outcomes, this would be exploratory on historically seen data, not independent
confirmation or a retroactive change to temporal-transfer-003.

If the objective instead is to distinguish arbitrary instantaneous maps from
history dependence, this cubic comparison is insufficient. A stronger design
needs responses at the same controlled instantaneous input reached through
different known histories, with observation dynamics controlled/calibrated.
Static F(c) predicts identical outputs for matched c; the frozen temporal map
can predict different outputs through z. The current anonymous processed means
do not establish such matched histories. Even a history effect would still
not distinguish recurrent neural dynamics from feedforward/indicator dynamics.

Thus do not trigger another run merely because5/6 is promising. Astra1/2/3
should approve the narrow static-control question only if it is the scientific
target; otherwise pursue the evidence needed for the stronger intervention.
Astra4 owns this interpretation; no new computational task ownership or
operator permission is assumed.
