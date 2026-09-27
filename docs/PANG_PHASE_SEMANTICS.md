# Pang phase-area semantics audit

Gate B remains open. The historical script integrates the entire tail after the
first zero crossing and then takes its absolute value. Calling this the area of
the opposite phase is ambiguous when the response crosses back. This audit
preserves the historical report and reproduces its eight control-curve integrals
from four original author MAT files at commit
`7fa5829e37d566e02beaaa87efd6a0f1de4e48c0`. Downloaded bytes are verified against
Git blob IDs and SHA-256 receipts are included in the new report. Subsequent
inspection of pinned author MATLAB code confirms that signed net-tail integration
is also the author's definition; cancellation itself is not an implementation bug.

## Executed result

The historical arithmetic reproduces within 1e-14 absolute / 1e-10 relative
tolerance. For the light rows, three definitions give different questions:
absolute net tail allows cancellation; opposite-only area counts all subsequent
opposite-sign pieces; first opposite lobe stops at the next return. All use the
same raw-zero boundary and historical nominal onset/window in this audit.

| Control light curve | Historical abs(net tail)/abs(first) | Opposite-only/abs(first) |
| --- | ---: | ---: |
| L1 highLum | 0.044968 | 0.068239 |
| L1 lowLum | 0.037983 | 0.153045 |
| L2 highLum | 0.478425 | 0.481768 |
| L2 lowLum | 0.513359 | 0.514319 |

For L1 highLum the first area is positive and the **net tail is also positive**
(5.454574e-5 deltaF/F seconds), despite a real negative excursion. The positive
return area exceeds the negative area. For L1 lowLum, cancellation reduces the
net ratio by about fourfold relative to opposite-only area. L2 light curves are
less affected under this window. These are processed-mean descriptions; none is
a per-fly confidence estimate or newly validated physiological criterion.

## Verification and interpretation

An independent piecewise-linear integrator splits every segment at every zero.
Hand-integrated triangular controls verify both signs, return-area conservation,
linear subdivision and the absence of a crossing. It reproduces the historical
signed first and tail integrals for all eight dark/light control curves. The
first opposite-lobe area is recorded separately, without declaring it the paper's
intended metric. The script, source files and input report are hash-bound.

Run with Python, NumPy and SciPy:

```sh
python tools/audit_pang_phase_semantics.py --fetch
python tools/audit_pang_phase_semantics.py
```

The first command downloads four MAT files (5,854 bytes total) and three small
author MATLAB analysis files; the second
uses cached verified files offline. Output: `reports/pang_phase_semantics.json`.
No original report or runtime source is modified.

Peer review by Astra 1 independently reproduced opposite-only integrals using
SciPy quadrature (maximum absolute discrepancy 1.11e-13 across eight curves).
It also found a missing zero-response case: the initial implementation attempted
zero/zero crossing interpolation. The revised metric returns no phase when no
positive peak exists in the requested polarity. Explicit controls now cover
zero response, wrong-polarity-only response, an exact-zero crossing and corrupted
cached source bytes. Source, control and report checks use explicit exceptions
and remain active under `python -O`.

## Author definition recovered after the sensitivity audit

The same commit includes `imaging-analysis/HHY_stimulusSpecificAnalysisScripts/`:
`compute_bootstrappedMetrics.m` lines 117-150 integrate area1 from frameZero1 to
frameZero2 and area2 from frameZero2 to endPhase2 with signed `trapz`, multiplied
by `100 * ifi`. Its areaRatio is **signed area2/area1, without abs**. Thus counting
only opposite-polarity pieces would change this source implementation. The file
uses bootstrapped responding-ROI averages, not the eight processed mean curves
audited here. Static source inspection is not execution of its MATLAB bootstrap.

`computeFrameZero2.m` picks the first opposite-side sample after the peak; it does
not interpolate a zero. `computeFrameZero1.m` uses a derivative-based onset
heuristic, defaulting to frame 2; the analysis ends at `floor(.25/ifi)`. These
boundaries differ from the historical Python notebook-index onset and interpolated
crossing. All three code files are now blob-verified and SHA-256 recorded.

Before a prospective comparison, reproduce the source signed statistic with its
actual ROI/time inputs and document any plotting sign/absolute transformation.
Keep opposite-only and first-lobe values as sensitivity diagnostics. Physical
flash alignment, recording-specific
luminance, observation transform and cohort identity are still missing; this
audit supplies no substitute for those gate requirements. New area definitions
are sensitivity diagnostics, not a correction to the biological source.
