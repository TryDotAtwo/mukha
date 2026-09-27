# Embedded identity route and one conditional mechanistic discriminator

Prospective plan, not executed; Astra4. Supersedes treating an absent XLSX as
a blocker for the entire project. No new window-policy experiment is proposed.

## An XLSX is not intrinsically required

The official [Dryad rendered README](https://datadryad.org/dataset/doi:10.5061/dryad.ngf1vhj4c),
sections Analyzed data and Exceptions, describes metadata inside analyzed MAT:
roiDataMat/roiMetaMat, seriesID, flyID, genotype, stimcode, ROI identifiers,
iResp, pStimDat, and variant allRespFlies/allMetadata structures. A genuine
record carrying those fields and its response can establish a minimal
recording→animal/ROI→nominal-stimulus link without a separate workbook.

Acceptance is semantic, not a filename checklist. Preserve source-qualified
keys and one-based indices; verify selected iResp against the actual ROI array,
and use another selection field (e.g. selectediResp) only if its source-defined
meaning and values are present, not as an assumed interchangeable alias.
Check agreement of repeated metadata across structures; conflicts and missing
values remain explicit. Optical transfer and physical epoch synchronization
are additional claim-specific checks, not prerequisites for merely identifying
an animal and nominal stimulus. Complete identity still does not recover
contributors or animal responses from already pooled means.

## Bounded official software-archive check

[Zenodo13367946](https://zenodo.org/records/13367946), DOI10.5281/zenodo.13367946,
open software record, publication2024-08-26. Official API lists:

| File | Bytes | Published MD5 | Inspection |
| --- | ---: | --- | --- |
| imaging-analysis.zip | 346641 | ab8412190bef160000f35b082ed99a68 | All member names inspected;304 entries including archive metadata; no MAT |
| computational-model.zip | 1031073 | 528e122df6102c7f0f8085cd7269df2b |36 entries; nine MAT headers inspected |
| stimulus.zip | 110668916 | 2d060bbfeb2f5dbec0f751673869e60e | Listed only; payload not inspected |

Two small ZIPs downloaded through public API-advertised content URLs; actual
size/MD5 match. SHA256 respectively
d7daf020fb4fb3e4000ef9d9d4b6792331f361141c27e6f9da42571c5dc1f9ec and
c35ea6c7b167250befd968a6c9068f78dc692b19ed308bd464c0166bcf6a7108.
Machine receipts: `reports/pang_zenodo_bounded_check.json`.
The initial inspection response was truncated by the tool output budget;
small ZIPs were reread for bounded receipts. No Dryad endpoint or authorization
workaround was used; no ZIP code was run or extracted to executable locations.

Model ZIP contains four control meanResp/t files; four CDM
meanResp/indivResp/t files; one natural meanResp_fixed/indivResp_fixed/t_fixed
file. No top-level biological identity structures in these nine MATs. Imaging
code references flyID/seriesID and consumes metadata, but variable names in
software are not observed biological records. The five notebooks are
CDM_results, L1_2responses_to_flashes, Latency_plots, L2_responses_to_nat and
Simulation. This is an archived modeling/analysis source, not newly acquired
animal metadata. Absence is bounded to the two inspected payloads; the large
stimulus ZIP and other potential data sources are not declared empty.

## ONE fallback experiment if linked response bytes remain unavailable

Question: can a single positive gain explain the control→CDM waveform relation
across flash polarity and nominal luminance, or is a stable temporal-memory
component predictively necessary within these fixed processed means?

This is a conditional model-class discriminator, not physiological calibration.
CDM is an octopamine receptor agonist, not a specific recurrent-path blockade.
An effective temporal term is compatible with recurrent adaptation but also
feedforward, indicator and other effects. Neither outcome identifies topology.

Inputs: exact existing eight control means and eight CDM means (four MATs per
condition), raw fractional deltaF/F, original63-point t. Freeze file hashes,
row polarity and units before fitting. Do not use anonymous indivResp as animal
replicates. Do not use the natural-stimulus file or add another experiment.

For each cell type L1/L2, let c(t) be a control mean and y(t) the corresponding
CDM mean. Compare:

- H0: yhat(t)=a*c(t), a>=0 (gain only).
- H1: yhat(t)=a*c(t)+b*(c(t)-z(t)), a>=0, signed b;
  tau*dz/dt=c(t)-z(t), tau>0 (gain plus one stable temporal-memory component).

H0 is nested at b=0. The state equation is an effective stable filter, not a
cell/edge assignment or a calibrated recurrent conductance. Fit separate
parameters for L1/L2; do not pool their amplitudes. No intercept, time shift,
rectification, baseline subtraction, per-test normalization or trace resampling.
The same preprocessing applies to H0/H1. State initially z(t0)=c(t0), an explicit
unverified prehistory assumption held fixed for all curves and both hypotheses.

Use piecewise-linear c on original t. State update on each interval d is exact:
z_next=exp(-d/tau)*z+c_i*(1-exp(-d/tau))
+slope*(d-tau*(1-exp(-d/tau))). No new phase-window choices.

Parameter-selection protocol, to be frozen after peer review BEFORE execution:

1. Fit ONLY highLum dark for each cell type. Existing curves have been viewed
   previously: withheld here means excluded from parameter fitting, NOT unseen
   or prospectively blinded biological data.
2. H0: one nonnegative least-squares gain. H1:32 logarithmically spaced tau
   values from median(diff(t)) to0.25s; for each solve least squares in a,b
   with a>=0, b unrestricted. Use quadrature-weighted full-record squared error
   (original-grid trapezoid weights) for both. At an unconstrained a<0, solve
   the a=0 boundary optimum. Include the nested H0 prediction explicitly.
3. Choose minimum training error only; exact ties prefer nested H0, then the
   smaller tau. Report all training tau scores and parameters, not just winner.
   A boundary optimum or poorly separated tau scores flags limited timescale
   identification, not a detected biological timescale.
4. Freeze parameters and predict highLum light, lowLum dark, lowLum light for
   each cell type: six transfer tests, no refitting. Raw predictions and residual
   arrays are primary outputs. Report full-record weighted SSE and SSE divided
   by the corresponding control-waveform energy; zero energy is undefined,
   not silently removed. These deterministic summaries have no biological CI.
5. Report per-curve error difference H0−H1 and aggregate sum across the six
   declared normalized errors. Gains in training alone do not favor H1. Mixed
   transfer outcomes must remain mixed; no retrospective removal or new split.

Discriminators: lower error on every declared transfer curve supports the
temporal-memory class over scalar gain conditionally on assumptions; no
improvement rejects its predictive utility here, not all feedback. Mixed
results mean neither universal description is established. No arbitrary
physiological acceptance threshold or p-value is set. Model flexibility and
earlier exposure to the curves are limitations even if all predictions improve.

Critical assumptions: corresponding nominal files used comparable physical
stimuli and observation transformations; preprocessing and cohort composition
do not account for the apparent shape change; initial-state assumption is
adequate. These cannot currently be verified from anonymous means. Therefore
even successful transfer cannot separate CDM circuit action from unmatched
illumination, indicator processing or composition. Published dataset sex also
does not establish transfer to the male connectome. Strong physiological gate B
remains open, but the effective gain-only versus temporal-memory question is
usefully testable without pretending those gaps are resolved.

## Ownership and stop condition

Proposal sent in Astra4 message37; pending peer ACK, no execution authorization:
Astra4 owns equations/frozen protocol; Astra2 owns fit/estimand and independent
prediction review; Astra3 owns exact inputs/provenance and observed embedded
metadata checks; Astra1 owns integration and is the sole eventual Molab operator.
No other kernels or agents. If an actual linked analyzed MAT is found first,
prefer a bounded join pilot and reassess this conditional plan before launch;
do not run both paths automatically. Otherwise agree this one experiment,
implement/review once, run once, and report discriminating outcomes/limitations.
No expanding window tests or general inventories. Missing XLSX alone is never
a reason to stop all scientific work.
