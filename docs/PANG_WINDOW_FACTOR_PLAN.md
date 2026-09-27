# Separate measurement-window factors after measurement-001

Status: prospective analysis plan, not executed; revised after Astra 1/2 review.
Astra 1 remains the only
Molab operator on faithful-fly-compact-recovery-v2. This document authorizes no
second kernel request. No physiological confirmation is claimed.

## Interpretation of the retrieved remote result

Reviewed `measurement-001/result.json`, SHA-256
`a271bb07b0d5556ef08a1874353d63145947adce626fec6eef4133135b510591`,
from the externally retrieved archive SHA-256
`713ffec2e9f62553b8a4b350b29611fd02c26f822a96ae93ec8a9617e640b6c2`.
This is the new remote artifact, not the earlier local rehearsal. Operator
transport/export evidence establishes its execution location separately from
its numerical contents. Astra 2/3 own artifact/checker validation; their
fractional-index/schema/policy findings do not turn numerical agreement into
full contract validation. Their corrections require no new Molab run.

The light rows show the following **negative signed ratios** (same display
convention in both columns):

| Curve | Historical boundaries | Sampled boundaries |
| --- | ---: | ---: |
| L1 highLum | -0.04496751 | -0.04968394 |
| L1 lowLum | +0.03798342 | +0.02203296 |
| L2 highLum | +0.47842514 | +0.43279153 |
| L2 lowLum | +0.51335887 | +0.47431745 |

These are deterministic measurement-definition differences on the same
processed means. In particular, L1 highLum's positive net tail relative to its
positive first area produces a negative displayed ratio in both conventions.
The historical absolute ratio hides that sign. The observed differences cannot
identify whether onset, endpoint or phase-boundary choice dominates. They
cannot estimate animal uncertainty, a treatment effect or model physiology.
The reported 0.00248 seconds measures the recorded arithmetic section, not a
whole-job benchmark. Neither GPU use nor biological replication follows.

## Freeze everything except three named factors

Reuse the exact four archived control MAT files, both rows, without refitting,
baseline subtraction, resampling amplitudes, smoothing or changing polarity.
Retain the completed run's restricted peak rule: zero-based
`2 + argmax(polarity*y[2:31])`, first tie, dark polarity -1/light +1.
Do not switch to full-vector author peak selection in this experiment even
though the two rules happen to agree on these inputs. Compute all alternative
boundaries **once per curve** before constructing any condition.

Let `t` be the original 63-point time vector and `ifi=median(diff(t))`. Following
Astra 1/2 review, use the SAME ORIGINAL `t` grid for every integration, with
unchanged sample amplitudes and piecewise-linear interpolation. Record both
`max(abs(t-(t[0]+arange(len(t))*ifi)))` and the actual step differences. Do not
round `ifi` to 1/120 or silently regularize t. The archived sampled corner used
uniform ifi weights; retain its residual against common-t quadrature explicitly.
If corner closure fails the tolerances below, stop three-factor attribution and
report a separate timing-weight issue. Timing arrays are not evidence of the
physiological acquisition frame rate.

| Factor | H: historical choice | S: sampled choice |
| --- | --- | --- |
| O, start | `t[2]` | `t[frameZero1-1]`, derivative-based helper with frozen peak |
| E, end | `t[h]`, `h=searchsorted(t,t[2]+0.25,right)-1` computed once on original t | `t[floor(0.25/ifi)-1]` |
| C, split | zero interpolated between `t[j-1]` and `t[j]` | `t[j]`, first opposite/zero sample, frozen one-based `frameZero2=j+1` |

Use raw fluorescence zero throughout. Compute `j` using the reviewed source
helper and frozen peak; do not search again after changing O or E. Validate
that the original historical crossing corresponds to this bracket on every
curve; a mismatch is a design-domain failure, not permission to choose another
crossing. Exact-zero sample gives coincident C alternatives and a valid zero
contrast. Missing crossing, invalid index or intervals not satisfying
`O <= peak_time <= C <= E` produce explicit failed condition records. No curve
may be silently dropped. **Changing O never recomputes E relative to the new O.**

## Minimal controls and recommended complete design

Four conditions (HHH, SHH, HSH, HHS) are the minimum for three isolated changes
at one shared baseline. Those contrasts are conditional on H choices for the
other factors. They do not give a unique additive attribution of the full
historical-to-sampled ratio change. Because the ratio has a variable denominator,
interactions can occur even when areas have simple additive changes.

Recommend the complete eight-condition design, the smallest full binary design
that measures all main/interaction contrasts without assuming interactions zero:

| ID | O | E | C | Purpose |
| --- | --- | --- | --- | --- |
| HHH | H | H | H | Historical-boundary reference |
| SHH | S | H | H | Start only versus HHH |
| HSH | H | S | H | End only versus HHH |
| HHS | H | H | S | Split only versus HHH |
| SSH | S | S | H | Start/end interaction |
| SHS | S | H | S | Start/split interaction |
| HSS | H | S | S | End/split interaction |
| SSS | S | S | S | Sampled-boundary endpoint and three-factor closure |

This is 8 conditions × 8 curves = 64 deterministic integrations in one future
CPU analysis, with no stochastic seeds or new biological observations. No new
data acquisition is necessary for this measurement question. Freeze the full
design before seeing new condition values; do not select a subset afterward.

## Measurements, discriminators and numerical acceptance

For a common primitive integral `F` of the fixed piecewise-linear curve, store
`A1=F(C)-F(O)`, `A2=F(E)-F(C)` in deltaF/F seconds, total `A1+A2`, raw `A2/A1`
and displayed `Q=-A2/A1`. Divide archived sampled percent-deltaF/F-second fields
by 100 for corner comparisons. Do not rectify either area or Q. If A1 is zero,
store null ratio and a typed reason. For every nonzero denominator record its
magnitude and calculate the signed ratio without clipping or a new exclusion
threshold; nonfinite arithmetic is an explicit failure.

Discriminating invariants at fixed other factors:

- O-only changes A1; A2 is unchanged.
- E-only changes A2; A1 is unchanged.
- C-only transfers a signed strip between phases: `delta A1 = -delta A2`;
  their sum is unchanged. It is not opposite-only area extraction.

Additionally, for EVERY valid cell, `A1+A2` must match a direct integral over
the full fixed [O,E] window using the same quadrature, detecting gaps/overlaps.

Freeze all area/corner/conservation comparisons at `rtol=1e-10, atol=1e-14`
deltaF/F seconds. HHH must reproduce archived historical signed areas; SSS must
reproduce archived sampled areas divided by 100. Store signed and absolute
residuals, not just a pass flag. Compare corner Q at `rtol=1e-10, atol=1e-10`
for all eight nonzero-denominator curves; zero stays undefined. Use the explicit
comparison `abs(actual-reference) <= atol+rtol*abs(reference)` throughout.
These are prospective numerical design choices, not biological effect cutoffs.
A corner mismatch blocks attributing the observed
remote difference to only these three factors; inspect time weighting, peak,
units and source arithmetic without silently revising this plan.

Report the three H-baseline Q contrasts and corresponding area changes for
each curve. Also report mean-over-other-factor contrasts and pair/triple
interaction contrasts from all eight cells. For example,
`I_OE=Q_SSH-Q_SHH-Q_HSH+Q_HHH` at C=H. Triple contrast is
`Q_SSS-Q_SSH-Q_SHS-Q_HSS+Q_SHH+Q_HSH+Q_HHS-Q_HHH`.
These are arithmetic interactions, not biological interactions or statistical
significance. Never sum the three baseline ratio changes and call that the
full effect unless the interaction residual is explicitly accounted for.

## Necessary inputs and prospective output contract

Use archived `inputs/*.mat`, their original t arrays and source hashes; the
three source M helpers; reviewed Python helper implementations; original
historical audit JSON; and the retrieved remote result/manifest for corner
reconciliation. The peak-policy string and schema must be fixed and checked;
integer sample indices must be exact non-boolean integers, while interpolated
split times are continuous values. Pin plan and eventual runner hashes.

Each result row requires curve file/hash, row/polarity, O/E/C levels, original
and common-grid bounds, peak/bracket indices, ifi and clock deviation, areas,
ratios/status, and typed failure reason. Record the exact 64-key Cartesian set,
input/code/plan manifest and external archive receipt in a unique run directory.
No kernel submission is requested by this plan; Astra 1 alone may execute after
explicit coordination and checker review. No rerun is needed to inspect this
document or fix the existing checker.

For a later physiological question, actual ROI/animal membership, recording
stimcode/optical settings, physical frame/flash synchronization and indicator
observation calibration are still necessary. They are not needed for this
bounded factor analysis and cannot be supplied by its results.
