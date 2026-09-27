# Prepared measurement diagnostic, not physiological replication

Astra 1 is the sole proposed/acknowledged Molab kernel operator, using
`faithful-fly-compact-recovery-v2`. This preparation uses local public source
inspection only. No pairing file, credential or tokenized URL is required here.

## Concrete next experiment

Use the four pinned control MAT files and both rows (eight processed means).
Compare reviewed source-sampled signed areas and downstream negative ratio
with historical interpolated areas and absolute ratio. Run once on CPU in a
unique directory, preserving the frozen inputs and all boundary/area outputs.
This checks measurement conventions in the recovered environment. It does not
run a biological model, reconstruct ROI bootstrap, or pass gate B.

The author's `computeFramePeaks.m` (blob
`f61df3ffa8c22e0ec9168fd7906ebcc38f1ed0b2`) selects first min/max over the
**entire supplied vector**, then opposite max/min over the inclusive suffix
starting at that first peak. Preserve first occurrence on ties. Restricting
the vector to a 250-ms window changes the domain and must be stated separately.
The sampled-area wrapper has explicit restrictions on peak/window validity;
an unsupported case must remain visible rather than be repaired by moving a peak.

Before execution record input hashes, row labels, vector length, time array,
peak rule/domain, frame interval rule, one-based boundary/end indices and
undefined-ratio policy. Record raw signed ratio, negative display ratio and
historical absolute ratio separately. The window and sign contributions can
then be inspected without mistaking either for neural dynamics. Preserve all
eight cases even when a ratio is negative or a calculation is undefined.

## What the public README actually supplies

`reports/pang_metadata_readiness.json` extracts evidence from the public landing
page's rendered README, using Astra 1's preserved HTML snapshot. It hashes the
snapshot and normalized README text and quotes relevant fields. It does **not**
claim identity to unavailable downloadable README/workbook bytes.

| Required association | Documented source fields | What remains missing |
| --- | --- | --- |
| Recording and animal | Time Series ID; seriesID; Fly ID/flyID | Actual rows/cohort of the four mean curves |
| Search versus experiment | roiDataMat(:,1) versus (:,2); iResp; roiMask | Original selected ROI membership |
| Stimulus identity | stimcode; stimDat; workbook Stimulus | Per-recording waveform assignment |
| Physical timing | pStimDat.lightStartTimes/darkStartTimes; imFrameStartTimes; Out.imFrameTime | Actual stimulus/frame alignment values |
| Resampled observation | t; BIN_SHIFT; interpFrameRate; binWidthMult | Exact preprocessing provenance for supplied means |
| Optical setting | Workbook PWM, color/ND filters | Actual row values and absorbed-photon calibration |

The README says blank workbook PWM values used 200 and gives LED current
`1.8 * PWM + 140` mA. That rule cannot assign 200 to a mean curve with no joined
workbook row. LED current itself is not absorbed photon rate. The README
distinguishes microscope frame times/intervals from stimulus-aligned/resampled
time bins; a 120-Hz output grid must not be labeled the acquisition frame rate.

## Reproduction and decision

```sh
python tools/audit_pang_metadata_readiness.py --public-html PUBLIC_LANDING_SNAPSHOT --fetch-peak-source
```

Subsequent execution omits `--fetch-peak-source`. Only the supplied public HTML
snapshot is read; the optional acquisition is one immutable public author M
file. No Dryad download or Molab request occurs. The exact public README fields
support the schema above, not their unobserved values.

Proceed with the bounded measurement diagnostic after runner/protocol review.
Keep physiological comparison blocked on real metadata/observation evidence.
Dryad authorization and Molab pairing are distinct access questions.
