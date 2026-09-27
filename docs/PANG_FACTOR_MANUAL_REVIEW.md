# Independent controls for factor implementation review

Plan: `39387c38305d235c90a8887337b1486ed0300550`. Astra 4 implements;
Astra 1 alone may operate Molab after reviews. This packet supplies exact
reference numbers, not a second runner. No biological data are changed.

## Analytical integrator/factor fixture

Piecewise-linear knots: `t=[0,1,1.5,2.5,3,4]`, `y=[0,2,1,-1,-2,0]`.
Freeze peak time 1; O=(0,1), E=(4,3), C=(2,2.5), with H first/S second.
The historical crossing is interior to the 1.5..2.5 segment; sampled crossing
is its opposite-side endpoint. These are supplied test levels, not a test of
author-derived onset or endpoint. All eight orders O≤peak≤C≤E are valid.

The area to t=2 is 2. Starting at t=1 removes +1 from A1. Ending at t=3
removes -1 from A2. Moving C from 2 to 2.5 moves a -1/4 signed strip from
A2 into A1. This proves the factor-isolation identities without software.

| Cell | A1 | A2 | Q=-A2/A1 |
| --- | ---: | ---: | ---: |
| HHH | 2 | -2 | 1 |
| SHH | 1 | -2 | 2 |
| HSH | 2 | -1 | 1/2 |
| HHS | 7/4 | -7/4 | 1 |
| SSH | 1 | -1 | 1 |
| SHS | 3/4 | -7/4 | 7/3 |
| HSS | 7/4 | -3/4 | 3/7 |
| SSS | 3/4 | -3/4 | 1 |

Baseline Q effects O/E/C are 1, -1/2, 0. Pair terms OE/OC/EC at the remaining
H are -1/2, 1/3, -1/14. The triple is -11/42. Their sum is zero, exactly
SSS-HHH, whereas adding only main effects incorrectly gives 1/2. Averaging
each factor's four conditional contrasts gives O=143/168, E=-143/168,
C=11/168. The full rational oracle is `reports/pang_factor_manual_reference.json`.

Additional quadrature controls: sign inversion reverses A1/A2 but preserves Q;
inserting collinear knots preserves all integrals; if C_H=C_S, every contrast
involving C is zero. A returned first-sign tail must preserve negative displayed
Q, not be rectified. Zero denominators and invalid intervals remain failures.

## Source-boundary and 64-row review

Inspect index conversion independently: frozen peak is zero-based
`2+first_argmax(polarity*y[2:31])`; helpers receive peak+1; helper frames convert
back by -1. Compute both O/E/C alternatives once, on original t. In particular
source E is `floor(.25/median(diff(t)))-1`, not rounded and not relative to O_S.
Historical E always refers to `t[2]+.25`. Freeze the first zero/opposite bracket
after peak before changing any factor. Equality to zero may collapse C levels.

Require exactly the Cartesian product of the four pinned filenames, row 0/1,
and all eight distinct H/S triples. Count 64 alone is insufficient. Reordering
is valid; duplicates, omitted failure rows or unexplained extra keys are not.
Every valid cell needs signed areas, denominator, total-window conservation,
and fixed negative ratio. Invalid cells retain typed status and original key.

HHH/SSS compare to archived corners after /100 source-area conversion, with
frozen area tolerances rtol1e-10/atol1e-14 and ratio tolerances
rtol1e-10/atol1e-10. Failed corner closure blocks attribution. Pair/triple
effects and averaged contrasts must follow explicit factor ordering O/E/C.
No percentages of biological causation or p-values follow from these means.

## Completed implementation review

Exact runner `62e1fa5b40bca9af932abd118e80802062b830ff` passed this prewritten
manual oracle in Astra 2's separate checkout. Maximum absolute difference was
1.6653345369377348e-16. Sign inversion, collinear refinement, coincident split,
all main/pair/triple terms and averaged effects passed. A same-sign positive
tail retains negative Q. Nine author synthetic tests independently passed under -O.

A second hand fixture uses t=arange(63)/128 and y[2:5]=[1,3,1], y[5:35]=-1,
zero elsewhere, plus its sign-inverted dark version. It gives peak index3,
O indices H2/S1, E indices H34/S31, bracket4/5, source one-based frames2/6/32.
Historical Q=117/17 and sampled Q=52/9 match; changing O does not move E.
A corrupted historical corner blocks attribution and suppresses contrasts.

The main output dispatcher was tested with analyze_curve replaced by an explicit
synthetic-failure stub: eight calls yielded all64 unique curve/row/condition keys
with typed status and null metrics. This did not integrate real curves and its
scratch output is not scientific evidence. The actual64-condition experiment
remains pending operator review/launch. Verdict: numerical APPROVE for the frozen
plan; artifact/adversarial checks remain Astra 3's separate review responsibility.
Machine-readable review: `reports/astra2_factor_runner_review.json`.

Numerical approval is carried forward to
`f61ef73c869a0d54170b3e4212c1a5605dc4af4b` after exact diff review. This revision
adds shared complete/unique cube-key checks and exact exported-boundary equality
to frozen levels before acceptance/aggregation. Integration, boundary derivation,
contrast arithmetic, reference helper, plan and tolerances are unchanged. The
earlier numerical results remain applicable; they were not needlessly rerun.
Astra 3 independently owns the targeted guard regression before operator launch.
