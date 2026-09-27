# Pang source/calibration evidence and minimum acquisition request

2026-09-27. Astra4 static primary-source review; no Molab, fitting, stimulus
experiment or Dryad file-download request. Complements Astra3's actual-file
inventory and Astra2's estimand review b46b14c; does not duplicate them.

## Evidence identities and limits

1. [Dryad public dataset / rendered README](https://datadryad.org/dataset/doi:10.5061/dryad.ngf1vhj4c),
   existing local `dryad-page.html`, SHA256
   cc0b026161ea89f8b740ef575e9e075ea0845feefde0a2d6f61275456554fb01.
   Read its complete rendered README this turn. Sections below refer to its
   actual headings, not to an acquired standalone README or spreadsheet.
   Local `Dryad_README.md` is118-byte HTML403; Astra3 separately confirmed
   `L1L2_Metadata.xlsx` is HTML403. Neither filename establishes acquisition.
2. Immutable author repository revision
   [7fa5829e37d566e02beaaa87efd6a0f1de4e48c0](https://github.com/ClandininLab/L1L2-recurrent-feedback/tree/7fa5829e37d566e02beaaa87efd6a0f1de4e48c0).
   Three newly read source files are transcribed with line numbers, source URLs
   and original-byte SHA256 in `reports/pang_calibration_source_excerpts.json`.
   Reconstructed text matches original hashes and Git blob identities in the
   pinned author tree. These are static scripts, not proof of which invocation
   generated any particular deposited file.
3. [Article DOI10.1016/j.cub.2024.11.064](https://doi.org/10.1016/j.cub.2024.11.064),
   [PMC11769683](https://pmc.ncbi.nlm.nih.gov/articles/PMC11769683/).
   Original XML is not present in the inspected local caches. Earlier committed
   `reports/pang_projector_radiance.json` pins BioC XML SHA256
   6c9414dc8e011687d4c515ac17f2035445252578e6172e1d851cb67e21ce0103
   and a projector-method paragraph. Current public BioC fetch returned429 once;
   public EuropePMC fullTextXML returned500 once. Neither was retried. Article
   numbers below are explicitly prior-audit evidence, NOT freshly re-read article
   text. Exact page/subsection cannot be certified from those bytes this turn;
   no invented article anchor or methods quotation is supplied.

## What is documented, at which granularity?

| Evidence location | Documented content and units | Granularity / remaining gap |
| --- | --- | --- |
| README: Metadata spreadsheet → Time series information/parameters | Time Series ID per live recording, Leica YYMMDD_fly#LDM### or Bruker Tseries-YYMMDD-###; Frames; Imaging Frame Rate in Hz | Schema only; values for our means not available |
| README: Metadata spreadsheet → Fly information | Fly ID; genotype including driver, indicator, TNT/ort/CDM; age in days; all dataset flies female | Protocol/schema and figure-group fly lists, not ROI contributor joins; sex transfer to male connectome remains explicit |
| README: Metadata spreadsheet → Stimulus parameters | Search stimulus precedes experimental stimulus, same field of view; adjacent same-Z rows identify same FOV; optical filters common to dataset, color center/FWHM in nm and ND optical density | Common-filter statement is known; actual numeric filter cells and recording-to-stimcode rows remain missing |
| Same subsection | LED current(mA)=1.8×PWM+140; original rows blank in PWM used200 | PWM is electrical drive, not luminance. Default applies to documented blank cells, NOT to an unacquired row. Formula gives500mA at200, not an observed setting for every curve |
| README: Laser parameters | Wavelength nm; post-objective power kept5–15mW; ditherHold0 implies filtering for ~25Hz laser artifact,1 no filter; Bruker values differ | Imaging laser settings, not visual stimulus photon flux; per-record dither state unknown |
| README: Analyzed data (.mat files) → stimulus-aligned responses | t seconds; rats mean; stdErr/stdErrs SEM; dark{1,1}, light{1,2}; BIN_SHIFT seconds | Described nested ROI data, not observed in the four control exports |
| Same section → processed time series | imFrameStartTimes/imIFI seconds; avSignal pixel mean, dSignal background subtraction, fSignal filtered if dither present; dFF normalized fluorescence | Exact baseline fit/ROI membership/epoch contributors must be bound to actual records |
| Same section → pStimDat | rcStim0..1; rcStimInd1 dark/2 light/3 gray; stimEpochStartTimes/lightStartTimes/darkStartTimes seconds; pdThresh volts; stimvalIF; stimEpochTimesIF | Sufficient named fields to request physical alignment; the arrays themselves are missing |
| Same section → raw stimulus / interpolation settings | Duration/FlashDuration/GrayDuration/stimIFI seconds; contrasts relative0..1; interpFrameRate Hz; binWidthMult averaging-bin multiplier | Resampled/aligned spacing is not raw imaging or projector frame rate |
| README: Exceptions | Natural stimulus may combine two time series in roiDataMatMeans; interpFrameRate=-1 means no rolling average or frame-rate resampling; L1split control/TNT uses allRespFlies/respROIMat | Different branches cannot be treated as one universal averaging pipeline |
| README: Raw data (zip files) | Leica LIF plus stim.mat; Bruker TIFF and photodiode CSV; Out.pdData volts, Out.pdTime; Out.imFrameTime maps photodiode points to imaging frames; NIDAQScanRate Hz; RepeatRNGSeed/Out.rndSeed | Raw organization documented, not acquired; Leica trigger mapping not applicable unchanged to Bruker |

The README describes rats/dFF as “% deltaF/F (as decimal numbers)”. Preserve
this wording in source metadata, but use an explicit numerical conversion:
the inspected computeDFF returns dimensionless F/F0−1, while metric code
multiplies areas by100 for percent-deltaF/F seconds. Thus0.01 fractional change
is1 percent; do not multiply an already-percent export again. README yScale and
inv are plotting controls, not a voltage calibration.

The README also lists named flies for Figs1/3/5 control/CDM and other figure
groups. These are useful candidate identities, but do not attach anonymous
exported rows or weights to those flies. Names should be source-qualified:
date/fly strings alone must not be presumed globally unique across datasets.

## Stimulus source: exact locations, not inferred recording assignment

The immutable [A configuration](https://github.com/ClandininLab/L1L2-recurrent-feedback/blob/7fa5829e37d566e02beaaa87efd6a0f1de4e48c0/stimulus/fullfield_6contrastA_LDflash20ms_Gray500ms.txt#L4),
[B configuration](https://github.com/ClandininLab/L1L2-recurrent-feedback/blob/7fa5829e37d566e02beaaa87efd6a0f1de4e48c0/stimulus/fullfield_6contrastB_LDflash20ms_Gray500ms.txt#L4)
and [C configuration](https://github.com/ClandininLab/L1L2-recurrent-feedback/blob/7fa5829e37d566e02beaaa87efd6a0f1de4e48c0/stimulus/fullfield_6contrastC_LDflash20ms_Gray500ms.txt#L4)
specify at lines4–8: two0.02s flashes,0.5s gray at0.5, RepeatRNGSeed0;
dark/light levels are respectively0/1,0.25/0.75,0.375/0.625. They are relative
projector values, not photon rates. SHA256 values match the frozen stimulus
report9334d0f7...,0cc9f237...,dd335452... respectively (full hashes in
`reports/pang_20ms_stimulus_family.json`).

[FullFieldFlashOntoGray.m](https://github.com/ClandininLab/L1L2-recurrent-feedback/blob/7fa5829e37d566e02beaaa87efd6a0f1de4e48c0/stimulus/FullFieldFlashOntoGray.m#L72),
SHA256 a69879b3b105061002135ff0d306f04a2e70f053b0e8a8dc4d2b05d45a379a21:
lines77–78 round requested durations to integer frames using supplied ifi;
lines83–90 choose default or shuffled RNG; lines112–124 randomly choose a flash
then gray; lines160–164 save seed/count/stimIFI. Its header line25 mistakenly
labels FlashContrast “sec”; configuration values, implementation and README
identify it as relative luminance, not time. Do not promote that comment typo
into a units contract. Exact delivered epoch times require photodiode data.

Many additional flash configurations exist (including different backgrounds,
durations and gray intervals). A/B/C are an inspected family, not proof that
all four mean files used one of those three. The two repository README files
`stimulus/README.md` and `imaging-analysis/README.md` each contain only a title
and one generic descriptive line; neither supplies a calibration table.

Earlier article audit reports DLP LightCrafter4500 blue LED,482/18nm bandpass,
300Hz refresh,6bits/pixel, approximate radiance78mW sr^-1 m^-2 at482nm.
These are protocol-wide prior-audit numbers.300Hz would give six frames in20ms,
but is not measured timing for a particular recording. The monochromatic
conversion1.89e17 photons s^-1 sr^-1 m^-2 is radiance, NOT photons absorbed per
receptor. Angular acceptance, collecting area, transmission/quantum efficiency
and recording-specific optical calibration are needed for that inference.
PWM-current formula does not supply a measured PWM-to-radiance transfer curve.

## Averaging and zero baseline: directly inspected code

- [computeDFF.m lines3–9,38–49](https://github.com/ClandininLab/L1L2-recurrent-feedback/blob/7fa5829e37d566e02beaaa87efd6a0f1de4e48c0/imaging-analysis/computeDFF.m#L3):
  two-exponential bleaching fit to supplied baselineSignal/baselineTimes;
  dFF=bksSignal/baselineF−1. The chosen fitting interval sets fluorescence zero.
  This is not resting membrane voltage, and the caller's baseline interval
  must be preserved. SHA25686d09a60bf84c706798721025249bc7ef6815d84411155467e57ad328296257b.
- [shortFlashProcessed_saveMean.m lines28–56](https://github.com/ClandininLab/L1L2-recurrent-feedback/blob/7fa5829e37d566e02beaaa87efd6a0f1de4e48c0/imaging-analysis/HHY_stimulusSpecificAnalysisScripts/shortFlashProcessed_saveMean.m#L28):
  selects roiDataMat(iResp,2), collects each ROI's rats, takes mean(rats,1),
  stores those same rows as indivResp, and copies t from first ROI. No animal
  regrouping/weighting appears in this script. SHA256
  e5c9daf537b4a3f20c7708e3b1c6ccac66b37f3e1cba943a1ffa4c6c6c447cb7.
  This establishes script semantics, not which exact invocation generated
  current MATs. In particular four controls lack indivResp despite this script's
  updated save line; exporting with another version remains possible.
- [analyze_FullFieldFlashOntoGray.m lines16–24,54–56](https://github.com/ClandininLab/L1L2-recurrent-feedback/blob/7fa5829e37d566e02beaaa87efd6a0f1de4e48c0/imaging-analysis/analyze_FullFieldFlashOntoGray.m#L16):
  dispatches reference/no-reference ROI-selection and stimulus-locked averaging
  helpers; saves roiDataMat/roiMetaMat/iResp/iInv/binWidthMult/interpFrameRate/inv/yScale.
  Selection thresholds and exact epoch-bin weights are not specified by this
  wrapper alone. SHA256faf71824c5d539e7e80beb59400f44ea89a7817d5d386165a7cc38c65b5b019e.
- Previously inspected [compute_bootstrappedMetrics.m](https://github.com/ClandininLab/L1L2-recurrent-feedback/blob/7fa5829e37d566e02beaaa87efd6a0f1de4e48c0/imaging-analysis/HHY_stimulusSpecificAnalysisScripts/compute_bootstrappedMetrics.m):
  nBReps10000, nSamples=selected ROI count; draws ROI indices with replacement,
  averages traces first, then computes area ratios. This is not an animal-level
  bootstrap or the mean of animal ratios. Our code reading does not establish
  that this script's bootstrap matches the design-based uncertainty required now.

Astra3's inventory reports four CDM exports with anonymous indivResp rows and
a natural-stimulus export with anonymous indivResp_fixed rows. They are more
than eight means but do not contain the identity/aggregation/physical-timing
join. Do not relabel those rows as animals or trials. Current data support
deterministic descriptors, not an animal-heldout score.

## Minimal request to the user (coordinate once through Astra1)

Please provide an authorized export for ONE selected control condition first,
not the entire raw dataset:

1. Valid `L1L2_Metadata.xlsx`, or relevant `All Metadata` rows with headers and
   source/version: Time Series ID, Fly ID, genotype/indicator, age/sex, Stimulus
   or stimcode, Frames/Imaging Frame Rate, Z-depth/FOV, color/ND filters, PWM,
   ditherHold and relevant acquisition settings. Preserve original blank cells
   distinctly from unknown/unavailable fields; apply PWM200 only where the
   source documents an originally blank PWM cell.
2. ONE matching analyzed MAT containing roiDataMat, roiMetaMat, iResp (or the
   documented allRespFlies variant), ROI/recording/fly keys, t/rats and acquisition
   timestamps, pStimDat/stimDat, interpFrameRate/binWidthMult, plus which rows
   contribute to the chosen exported curve and their weights/exclusions.
   Include baseline-fit/normalization settings or a source-qualified processing
   version/config. Anonymous indivResp alone does not suffice.
3. For that recording, synchronized photodiode/epoch arrays already embedded in
   the MAT may suffice; request separate stim.mat/CSV only if those are absent.
   For quantitative physical-input scoring add measured stimulus radiance or
   a calibration relation tied to actual PWM/filter/geometry. Do not invent it
   from the article's approximate protocol value.

That package allows a missingness-preserving source-join PILOT, not population
validation. For a later animal-heldout score, additionally require separable
animal response summaries with known construction, assignment/batch keys and
the complete target contributor population. Raw trials are needed for trial
noise/order/reliability claims, not universally. A quantitative voltage/fluorescence
comparison also needs a justified indicator observation transform. Freeze all
calibration/normalization/model-selection choices outside held-out animals and
assignment clusters. Score Q-of-mean or mean-animal-Q only as explicitly chosen
estimands; never substitute one for the other.

If the requested fields are unavailable, report them as unavailable. Do not
manufacture joins from file ordering, genotype fly lists, highLum/lowLum labels,
or a63-point time grid. No further window experiment or biological pass follows.
