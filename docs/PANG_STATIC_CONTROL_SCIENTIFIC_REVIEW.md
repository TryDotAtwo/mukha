# Scientific review of one static cubic control

Astra4; protocol/discussion ONLY. Reviewed owner draft
ec969caa8ffab3572a73f1805763f45a953e0cbb, based on public339ac3f.
No implementation, fits, scores, parameter sweeps, new experiments or downloads
were performed for this review. Replies: own messages43/44; Astra2 mathematical
review6c6f64eb and Astra3 methodology message36 read and accepted.

## Decision and discriminating value

Approve the scientific value of ONE restricted exploratory comparison, subject
to exact revised protocol incorporating undefined/fallback outcomes, signed
support diagnostics, exposure history and the stop rule below. This is not
unconditional approval of draft execution or a request to implement a runner.

Hs(c)=a*c+d*c^3/s_train^2, a>=0, signed d,
s_train=max(abs(c_train)), adds instantaneous amplitude-dependent gain
a+d*(c/s_train)^2 to H0. No state or history enters Hs. H0 is nested at d=0.
Consequently, an Hs advantage over the frozen H1 is a constructive example of
how a static mapping can be competitive despite H1's partial advantage over
H0. It would not show that the biological system is memoryless. Conversely,
an H1 advantage rejects only this particular static model's predictive ranking,
not all static nonlinearities, indicator dynamics or feedforward alternatives.

The proposed cubic is the lowest-order ODD zero-intercept polynomial extension
of the linear map. It introduces one linear coefficient and imposes the same
amplitude-dependent rule on both polarities: Hs(-c)=-Hs(c). Odd symmetry is an
explicit restriction, not a biological observation. Adding a quadratic, offset,
saturation curve or polarity-specific coefficients would ask a different
question and enable unplanned model selection. No such variants are selected
or tested here. Signed d permits compression or expansion locally, but neither
monotonicity nor boundedness is guaranteed: derivative=a+3d*c^2/s_train^2.
It is a phenomenological map, not a calibrated indicator law or receptor model.

Training-only scale fixes units and avoids transfer-dependent normalization.
It does not convert training amplitudes into a measured operating range. H1
had two coefficients plus a32-point tau search, versus two coefficients for
Hs; this is not a complexity-matched mechanism test. No extra static search
is justified simply to match computation budgets.

## Single common protocol recommended to owner

- Preserve the same eight hashed MATs, full63-point original grids, raw units,
  two highLum-dark training pairs and six transfer pairs. Fit separately by
  L1/L2, not by transfer polarity or the known failing condition.
- Freeze s_train on the training control. Use original-grid weighted SSE,
  constrained a>=0 and signed d, SVD relative rank threshold1e-12, explicit
  nested H0 and a=0 boundary; retain all candidate diagnostics and tie choices.
- For rank<2 report Hs nonidentifiable/nonselectable and a separately labelled
  H0 fallback. Keep all six keys. Full-rank selection of H0 under the declared
  tie rule also means no resolved cubic increment, not cubic identification.
- Record signed training/transfer min/max, max|c|/s_train, and time-weighted
  fractions outside the signed training interval and outside |c|<=s_train.
  These distinguish sign-support from magnitude-support extrapolation. They
  must not trigger clipping, dropping conditions, rescaling or redesign.
- Read archived H0/H1 predictions and errors unchanged, bound to temporal003
  archive c74de270799633ed056d8b5e6a61a383a4a96797243e3a0453ec28e8ad2af4bb.
  Report E0,E1,Es and both E0−Es/E1−Es for all six conditions. Each normalized
  error uses its OWN control energy. Pairwise numerical deadband stays
  1e-12+1e-10*abs(reference baseline error), never a biological threshold.
- Invalid/nonfinite/zero-energy cases retain typed undefined outcomes. No
  universal cubic-success conclusion if either cell's cubic is nonidentifiable
  or falls back to H0. Training performance and aggregates are secondary.

The exact identifiability argument from Astra2 is instructive: with
E=sum(w*c²), u=c²/s² and q=w*c²/E,
det(X'WX)=E² Var_q(u). Distinct nonzero magnitudes are required; simply observing
+s and -s or many repeated timepoints identifies only a+d. Weighted rank2
does not establish biological coefficient precision or independent animal n.

## Outcomes to declare before any future fit

| Outcome | Permitted conclusion | Not permitted |
| --- | --- | --- |
| Hs uniformly lower error than H1 | This specific static mapping is competitive on all reused transfer means | Biology is static; neural/indicator mechanism identified |
| H1 uniformly lower error than Hs | This odd cubic is less predictive on these reused means | Memory is necessary; all static maps rejected |
| Mixed pairwise signs | Condition-dependent ordering; no universal winner | Focus on the known L2 high-light failure or a favorable aggregate |
| Numerical ties | Differences unresolved at the numerical rule | Mechanisms equivalent or physiologically indistinguishable |
| H0 selected/fallback or invalid comparison | No resolved identifiable cubic contribution, or comparison undefined | Count fallback as a successful cubic or silently remove keys |
| Training gain only | Better description of reused training curve | Transfer advantage or biological support |
| Both have substantial residuals | Relative comparison only; absolute adequacy unestablished without a noise/observation model | A relative winner is physiologically adequate |

The prior temporal003 all-six outcome stays FALSE in every row of this table.
A new Hs-vs-H1 vector must not replace its denominator, endpoint or verdict.

## Reuse, stop rule and what would genuinely reopen the question

The cubic/training-scale form was named before temporal003 (Astra3 message31),
then deliberately excluded from the two-class experiment. The decision to
pursue this follow-up and its final numerical/reporting choices occur AFTER
all six outcomes were inspected. Naming a possible alternative was not
preregistration of this follow-up. Coefficient fitting can be leak-free while
human model-selection remains adaptive. Astra4 confirms no Hs variant has
been fitted or tried in this chat; this is not an assertion about unobserved
activity outside it.

Stop after this ONE pre-frozen cubic comparison and its independent arithmetic/
provenance closure, regardless of uniform win, loss, mixed signs, ties or rank
failure. Do not cycle polynomial degrees, offsets, sign restrictions, nonlinear
saturation, scales, splits, windows, tau ranges or exclusion rules on these same
viewed means to repair a condition or obtain all-six. Those changes could add
descriptive flexibility, but not new discriminating evidence for the present
mechanistic question under unknown observation/input/cohort mappings.

Reopen only when an independently grounded restriction, validated observation
map, source-qualified independent responses, or a controlled history contrast
creates a genuinely new prediction not selected from these observed residuals.
For example, identical instantaneous inputs reached through different controlled
histories can discriminate instantaneous maps from effective history dependence,
provided observation dynamics are controlled. It still would not automatically
separate recurrent circuitry from feedforward/indicator dynamics.

This is not a claim that the means contain no further mathematical information;
it is a stop criterion for adaptive model sweeps as evidence about mechanism.
No additional source request, fit or experiment is initiated by this memo.

Ownership: Astra1 exact protocol integration; Astra2 numerical identifiability/
fairness; Astra3 reuse/provenance; Astra4 restricted scientific interpretation
and stop rule. Exact revised protocol ACK remains to be recorded after owner
integration. Unanimous scientific agreement still does not authorize execution
under the user's present plan-only boundary.
