# window-factor-002: measurement attribution, not physiological validation

Interpretation of the actual retrieved Molab result, not a new calculation of
the eight input curves. Operator Astra1 reports one CPU execution after both
reviews of f61ef73c869a0d54170b3e4212c1a5605dc4af4b. Independent actual-result
numerical audit belongs to Astra2 and structure/provenance audit to Astra3;
Astra2 subsequently APPROVED the actual archive in evidence commit
c182c2f4cf596ba71f8715e33bd22a86b3aedc46: 2152 independent numerical
comparisons pass (maximum ratio/contrast discrepancy1.78e-15). Astra3's
actual-result structure verdict remains pending at this handoff.

Archive: 40875 bytes, SHA256
af79f4143614bb275c84605b8627b4faf28301cad61aad4d8f4c20425c8cd444.
Result SHA256:
b8faacd293a1fff141dfdc3bb4161cee6f0d8b8bdd134fc3d88c913c5c3332f1.
Source is `window-factor-002-retrieved/window-factor-002/result.json` in
Astra1's outputs. Values below summarize its records/contrasts; no runner or
quadrature was executed by Astra4 during interpretation.

## What changed

Q=-A2/A1 is dimensionless, with signed raw deltaF/F areas. HHH is the historical
window and SSS the sampled window, BOTH expressed in this same signed display
convention. This is not a decomposition of the historical absolute-value display.

For every curve, O moves the start from16.6667ms to0ms; E moves the end
from266.6667ms to241.6667ms. Times are relative to the supplied trace origin,
not established physical flash onset. C moves an interpolated zero to the next
sample. These three alternatives were frozen independently, not recomputed
conditionally. Raw baseline, peak and original time grid remain fixed.

| Curve / stimulus row | C H→S (ms) | Q HHH→SSS | Full change |
| --- | ---: | ---: | ---: |
| L1 high / dark | 40.000003→41.666667 | 5.86937520→5.11946314 | -0.74991205 |
| L1 high / light | 67.747094→75.000000 | -0.04496751→-0.04968394 | -0.00471644 |
| L1 low / dark | 45.730797→50.000000 | 2.31952614→2.26064849 | -0.05887765 |
| L1 low / light | 53.610699→58.333333 | 0.03798342→0.02203296 | -0.01595045 |
| L2 high / dark | 43.994467→50.000000 | 2.50743460→2.26318789 | -0.24424670 |
| L2 high / light | 49.082318→50.000000 | 0.47842514→0.43279153 | -0.04563361 |
| L2 low / dark | 56.063216→58.333333 | 1.45831096→1.31364966 | -0.14466130 |
| L2 low / light | 57.512808→58.333333 | 0.51335887→0.47431745 | -0.03904141 |

## Isolated changes and interactions

O, E, C below are single-factor changes from HHH. I is the SUM of the three
pairwise and one triple H-baseline differences, not an unexplained remainder.
Thus full change = O+E+C+I, before rounding. This expansion is conditional on
the selected H reference; it is not a unique causal allocation to factors.

| Curve / row | O | E | C | I |
| --- | ---: | ---: | ---: | ---: |
| L1 high / dark | -0.51039716 | -0.30588674 | +0.05204010 | +0.01433175 |
| L1 high / light | +0.00353571 | +0.00085606 | -0.00986051 | +0.00075231 |
| L1 low / dark | +0.06138583 | -0.15209089 | +0.03760118 | -0.00577378 |
| L1 low / light | -0.00028914 | -0.00833818 | -0.00737802 | +0.00005489 |
| L2 high / dark | -0.17751932 | -0.16031898 | +0.11357928 | -0.01998768 |
| L2 high / light | -0.03414407 | -0.01176056 | -0.00056335 | +0.00083437 |
| L2 low / dark | -0.03952279 | -0.10897399 | +0.00132869 | +0.00250680 |
| L2 low / light | -0.02244853 | -0.01716389 | -0.00017387 | +0.00074488 |

For L1 high dark, O and E reinforce each other and C partly offsets them.
For L1 low dark, earlier E dominates but O and C substantially cancel it;
the small net difference must not be read as insensitivity to each boundary.
For L2 high dark, O and E are comparable and C strongly offsets them; the net
interaction -0.01998768 also matters. For L2 low dark, E dominates, O reinforces,
and C is small.

For L1 high light, the split effect dominates and overcomes the positive O/E
effects. Q stays negative, meaning the net tail and first area have the same
sign; this is not an absence of an opposite-sign segment. For L1 low light,
E and C contribute comparably, with little onset effect. For L2 high light,
onset dominates, end contributes less, and split is tiny. For L2 low light,
onset and end both matter; split is again tiny. No common interpolation-only
explanation works across the eight curves.

### Pair and triple terms (H-baseline finite differences)

| Curve / row | OE | OC | EC | OEC |
| --- | ---: | ---: | ---: | ---: |
| L1 high / dark | +0.0265997180 | -0.0095452566 | -0.0032690802 | +0.0005463641 |
| L1 high / light | -0.0000673103 | +0.0008127672 | +0.0000080779 | -0.0000012255 |
| L1 low / dark | -0.0040250573 | +0.0028211352 | -0.0043339782 | -0.0002358776 |
| L1 low / light | +0.0000634736 | +0.0000543913 | -0.0000639482 | +0.0000009736 |
| L2 high / dark | +0.0113501332 | -0.0209635769 | -0.0120794056 | +0.0017051702 |
| L2 high / light | +0.0008393233 | +0.0000060011 | -0.0000127026 | +0.0000017493 |
| L2 low / dark | +0.0029533869 | -0.0001475779 | -0.0003159268 | +0.0000169158 |
| L2 low / light | +0.0007505552 | -0.0000000640 | -0.0000061326 | +0.0000005247 |

For comparison, averaging each single-factor contrast over all four choices
of the other factors gives the following values. These are NOT additive shares
of the endpoint difference and should not be summed as such.

| Curve / row | Mean O | Mean E | Mean C |
| --- | ---: | ---: | ---: |
| L1 high / dark | -0.50173334 | -0.29408483 | +0.04576953 |
| L1 high / light | +0.00390813 | +0.00082614 | -0.00945040 |
| L1 low / dark | +0.06072490 | -0.15632938 | +0.03678579 |
| L1 low / light | -0.00022997 | -0.00833818 | -0.00738255 |
| L2 high / dark | -0.18189975 | -0.16025732 | +0.09748408 |
| L2 high / light | -0.03372097 | -0.01134681 | -0.00056627 |
| L2 low / dark | -0.03811566 | -0.10765104 | +0.00110117 |
| L2 low / light | -0.02207316 | -0.01679155 | -0.00017684 |

## Why areas are simpler than ratios

O changes A1 only; E changes A2 only; C transfers the same signed strip between
them, conserving A1+A2. The original-t primitive is linear, so area pair/triple
terms vanish apart from roundoff (largest stored absolute term2.17e-19).
Ratio interactions therefore do not require a nonlinear biological mechanism:
changing the denominator in -A2/A1 already supplies nonadditivity.

Area changes below are in 1e-6 deltaF/F seconds. For C the A2 change is the
negative of the listed A1 change. For O, delta A2=0; for E, delta A1=0.

| Curve / row | O: delta A1 | E: delta A2 | C: delta A1 |
| --- | ---: | ---: | ---: |
| L1 high / dark | -38.93059 | -125.03319 | +4.32228 |
| L1 high / light | +103.51543 | -1.03840 | -11.33914 |
| L1 low / dark | +9.67522 | -57.07410 | +10.39721 |
| L1 low / light | +5.79113 | +6.29498 | -5.74595 |
| L2 high / dark | -39.62311 | -83.37350 | +36.43808 |
| L2 high / light | +72.59269 | +11.10870 | -1.01913 |
| L2 low / dark | -15.79740 | -61.79858 | +1.63931 |
| L2 low / light | +37.77723 | +14.17947 | -0.29506 |

## How fully does this explain measurement001?

All64 stored cells have accepted status. The largest historical/sampled corner
area residual is8.67e-19 deltaF/F seconds and Q residual8.88e-16, well within
the frozen tolerances. Maximum per-cell full-window conservation residual is
4.34e-19; the stored seven-term Q expansion residual is zero on every curve.
Original-t versus median-ifi grid deviation is1.11e-16 seconds for every curve.
Thus the proposed three-factor description accounts for the original signed
window discrepancy within numerical precision. A fourth timing-weight factor
is not required for THESE inputs at the chosen tolerances. This does not prove
that the physical recording clock or interpolation model is accurate.

Expansion closure alone is algebraic and is not independent validation; the
archived-corner agreement, frozen-boundary checks and independent reviewer
reconstruction are separate evidence. We do not assign percentages of causation,
p-values or biological error bars. There are eight processed mean traces and
64 measurement policies, not64 biological replicates. No ROI/animal uncertainty,
recording-specific illumination, indicator-to-voltage calibration, sex transfer,
model fit or held-out prediction has been established.

## Next gate: recording-to-stimulus and observation eligibility

Stop expanding the window cube after the independent actual-result audits.
The bounded question is answered. Gate B remains open. Proposed next deliverable
is a source-backed join table, not another model or Molab run:

| Required evidence | Eligible use | Failure policy |
| --- | --- | --- |
| Immutable workbook/README/raw-recording bytes with version/hash | Define the recording population | Metadata listing alone does not qualify |
| Recording, animal and ROI identifiers joined to mean/genotype | Animal-level calibration/held-out split; ROI nesting | No random ROI split across the same animal |
| Recording-specific stimcode, waveform, PWM/filter/luminance | Match dark/light protocol and physical stimulus | highLum/lowLum is not a numeric calibration or A/B/C assignment |
| Acquisition timestamps plus flash/photodiode synchronization | Estimate peak latency on a physical clock | Supplied t spacing alone cannot establish flash onset |
| Indicator identity/polarity/response transform and units | Compare predicted observation, not raw membrane voltage to fluorescence | Unknown transform blocks quantitative voltage agreement |
| Independent control/manipulation recordings and animal split | Freeze calibration on control animals; test held-out animals and source-backed manipulation | No post-hoc gain fitting on test curves |

First acceptance milestone: one verified recording→animal/ROI→stimcode→observation
join, with explicit missing fields, then extend to the intended comparison set.
Do not silently discard unmatched records. Preserve a full missingness ledger.
If bytes remain unavailable, request a user-provided public export or a genuinely
different authorized mirror once; do not repeat known Dryad401/403 downloads.
There is no current authority to contact authors or submit another kernel job.

Roles ACKed by Astra1 (message31) and Astra2 (actual numerical approval):
Astra1 acquisition coordination; Astra4 eligibility
and observation contract; Astra2 estimands/animal split; Astra3 provenance and
join completeness. Astra3's next-scope ACK remains pending, not a claim of acquired
metadata or closed gate. It narrows the next work to a real evidence dependency.
