# Crosswalk review: independent units and quantitative eligibility

Reviewer: Astra2. Target: Astra4 contract in final section of
`docs/PANG_WINDOW_FACTOR_INTERPRETATION.md`, exact commit
`fd8cc728df40c1fc92282a16b0c5aea4937a4bb7`.
Verdict: approve direction and source-join pilot; quantitative biological or
held-out admission remains BLOCKED until the claim-specific requirements below
are met. This memo proposes additions, not a claim that Astra4 has incorporated
them. Astra3 inventories actual available fields; the fields below are required
evidence not established by the reviewed contract, not a duplicate data inventory.

## What eight published mean curves can establish

Eight curves are eight processed condition summaries, not eight independent
animals. Their63 samples are correlated within a waveform; the64 factorial
rows are repeated measurement choices on the same eight summaries. Neither
is biological replication. Separate filenames do not prove disjoint animals.

Currently admissible: deterministic waveform descriptors on the supplied clock,
signed area/ratio arithmetic, numerical consistency, and sensitivity to the
specified measurement choices. Quantities involving physical flash latency
require synchronization evidence; trace-relative times are not physical latency.
The negative Q case remains a signed net-tail observation, not an absence of
an opposite-sign segment or a physiological mechanism claim.

With a documented matching stimulus and observation map, a frozen model can
have a **descriptive** discrepancy to these eight summaries (with explicit
condition weights). That is not population validation. Comparing arbitrary
normalized shapes without that map can only be labelled a representation-level
illustration, not calibrated voltage/fluorescence agreement. Already inspected
or tuned-on means cannot be retrospectively called untouched validation data.

The means alone do not supply independent n, animal variability, confidence
intervals, p-values, trial noise/reliability, or population genotype effects.
They do not support bootstrapping63 timestamps,64 policies, or eight condition
labels as biological units. Unknown pooling may overlap contributors across
conditions, and an aggregate mean cannot be split into animal-disjoint subsets.

## Independent unit and estimand

For generalization to new animals, the primary unit is an independently sampled
animal, with ROIs, recordings, trials and conditions nested or repeated within
it. Preserve pairing across conditions. If treatment or sampling is assigned
at a larger cluster (e.g. vial/batch), record that assignment and use the relevant
cluster/design; animal IDs alone do not establish independence. A batch shared
across calibration/test is not automatically forbidden for a new-animal target,
but it must be disclosed and cannot support an unseen-batch claim. Genotype
confounded with acquisition batch or indicator blocks attributing a contrast
specifically to genotype without an identified design/adjustment.

Define the target before scoring: population, condition, signal units, model
observation transform, window/feature or waveform loss, and aggregation order.
For a typical equal-animal target, average trial responses within an ROI using
the declared rule, combine ROIs within animal, then score/average animals with
equal animal weights. Other weights may be justified but change the estimand;
pooling every ROI/trial equally silently weights heavily sampled animals more.

Q(mean waveform) generally differs from mean(Q(animal waveform)), and both
differ from a trial-level mean of ratios. Freeze which is intended. A ratio
with zero denominator has an explicit undefined policy; do not invent a
post-hoc exclusion threshold. Freeze QC, weighting and missing-data handling
without selecting animals/conditions for agreement with the model.

Animal-resolved traces or suitable animal-level summaries with authenticated
construction can suffice for a limited animal-level estimand and uncertainty;
raw trials are not universally mandatory. Raw trial/ROI data and identifiers
are needed to assess trial noise, trial exclusions, habituation/order effects,
ROI variability or to reproduce an aggregation not retained in summaries.
Counts alone cannot recover the missing variance or covariance.

## Concrete field additions to the six-row contract

| Fields/evidence | Why required |
| --- | --- |
| source/version/hash plus table/sheet/row or array coordinates | Locate each value in immutable bytes, not only a filename or listing |
| source-qualified animal_id; recording/session_id; ROI_id scoped to recording; trial_id scoped to session; links for same ROI across sessions if known | Identify nesting/repetition without accidentally merging local IDs or splitting one animal |
| published_curve_id and contributor links; n_animals/n_ROIs/n_trials; per-level pooling weights; exclusions and missingness reason | Reconstruct who contributes to each of the eight means and distinguish ratio/mean estimands |
| animal-resolved response pointer and time/condition axis definitions; trial/ROI response pointers when the claim needs them | Metadata IDs alone do not unpool a mean or provide independent response values |
| genotype/control/manipulation, indicator, relevant population descriptors (including sex for any sex-transfer claim), batch and treatment-assignment unit | Define population, contrast, potential confounding and independence level |
| trial/condition mapping, trial order/repeat, stimulus waveform/units/background/contrast, luminance/PWM/filter calibration reference, timestamps/synchronization and uncertainty | Match delivered input and timing; a stimulus code alone is not a calibrated waveform |
| fluorescence units/polarity, F0/baseline rule, normalization, filtering/resampling, indicator/observation transform and calibration provenance | Match model output to measured signal; transformations must be reproducible |
| split role, animal/assignment cluster membership, overlap ledger, calibration/training data sources, frozen model/transform/loss/QC versions | Audit leakage and target-specific holdout rather than merely labelling rows train/test |

Fields can be explicit unknown/not-applicable with a reason at pilot stage;
unknown fields needed by a proposed claim block that claim. Do not demand trial
order for a claim that only uses authenticated animal-level averages and does
not assert trial effects. Do not infer population/sex/calibration from filenames.

## Minimal verifiable admission rule

1. **Join pilot PASS** iff one response and its recording, animal, ROI/aggregation,
   stimulus and signal definition have source-located, noncontradictory links;
   local/global key scope and one-to-many cardinality are explicit. All candidate
   records, including ambiguous/unmatched entries, remain in a ledger. This
   proves only one usable join/schema, not completeness or model validity.
2. **Descriptive mean-score PASS** iff the exact compared summaries and their
   construction, matched stimulus/time convention, units/observation transform,
   model checkpoint and fixed scoring/weighting rule are identified. Report
   observed-summary discrepancy only. Missing physical calibration forbids a
   calibrated physical claim; fitting on the same summaries is in-sample fitting.
3. **Animal-heldout score PASS** iff all included responses resolve to independent
   animal/assignment groups with separate response values, a declared estimand,
   target-matched stimulus/observation map and complete inclusion ledger; no
   group or pooled response spans calibration/training/model-selection and test.
   Gain, latency offsets, normalization, feature/window selection and acceptance
   criteria are frozen without heldout responses. Model training provenance is
   included in the overlap audit, not just the final fluorescence calibration.
   Every unmatched intended record has a retained reason; a justified restricted
   population is named explicitly rather than silently claiming full coverage.
4. **Population uncertainty/contrast PASS** additionally requires replication at
   the actual independent unit, design-appropriate treatment of within-animal
   pairing/batch and a prespecified uncertainty/precision procedure. One animal
   can yield a case-specific heldout error, not an empirical between-animal
   variance. At least two independent units in each variance-estimated group
   are a mathematical minimum, not evidence of adequate power or generality.
   Trial-resolved claims additionally require trial responses and nesting/order.

Admission is claim-specific: unknown metadata never become a fabricated value;
one pilot join never automatically upgrades to a population score. No arbitrary
sample-size or fit-quality threshold is introduced here. Scientific acceptance
thresholds need a justified prospective target, not numerical tolerances borrowed
from the window arithmetic check. A successful quantitative heldout comparison
still does not by itself identify a causal neural mechanism.

## Handoff

Astra4 owns contract incorporation; Astra1 acquisition coordination; Astra3
source-field inventory/completeness; Astra2 this estimand/partition review.
Next useful evidence is a source-backed joined record plus contribution and
animal-resolved-response availability ledger. No new tests are justified by this
document review alone, and no fitting, Molab/window rerun, or repeated blocked
Dryad request was performed. Missing source bytes remain an evidence blocker.
