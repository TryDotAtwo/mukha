# Pang sample-boundary contract

The author code selects an actual zero/opposite-side **sample**, then integrates
inclusive sample slices. It does not split a segment at its interpolated zero.
Signed tail cancellation is source behavior; opposite-only areas are sensitivity
diagnostics, not a replacement score.

`tools/audit_pang_sample_contract.py` implements a restricted, source-derived
Python translation of `computeFrameZero1.m`, `computeFrameZero2.m` and the area
expressions in `compute_bootstrappedMetrics.m` at author commit
`7fa5829e37d566e02beaaa87efd6a0f1de4e48c0`. It verifies their exact Git blobs.
Source directory URL:
https://github.com/ClandininLab/L1L2-recurrent-feedback/tree/7fa5829e37d566e02beaaa87efd6a0f1de4e48c0/imaging-analysis/HHY_stimulusSpecificAnalysisScripts

Download those three files into `data/reference/pang_sample_contract`, or pass
an existing byte-pinned directory with `--source-dir`. The audit itself is offline.

```sh
python3 -m unittest discover -s tests -p test_pang_sample_contract.py -v
python3 tools/audit_pang_sample_contract.py --output reports/pang_sample_contract.json
```

## Checked arithmetic

All reported indices are MATLAB-style one-based. The first boundary pads zero,
compares successive derivatives using the author's 10% expression, and defaults
to frame 2. The second boundary starts at the supplied peak, accepts equality
to zero, and selects the first opposite-side sample. The integration endpoint
is `floor(.25/ifi)`, not an absolute-time search. Areas use unit-spacing trapezoids
multiplied by `100*ifi`; ratios retain their sign.

For `[0,1,3,1,-1,-1,2]`, light contrast, peak frame 3 and `ifi=.04`, boundaries
are 1 and 5, endpoint 6. Hand sums give first area 18, second area -4 in
percent dF/F seconds, ratio -2/9. Splitting geometrically at frame 4.5 instead
would give first area 19. This is an analysis-definition difference.
For `[0,1,3,1,-1,-1,4,4]` and `ifi=.03125`, both signed areas are 14.0625 and
ratio is +1 despite the intervening opposite lobe. This is not an author bug.

Six stdlib tests cover hand-integrated areas, dark/light symmetry, recrossing,
exact zero, missing crossing, absent response, wrapper-domain rejection and
mutated source bytes. The absent-response helper reproduces the source's
boundary behavior; it is not evidence that a physiological phase exists.

## Limits

This is not execution of MATLAB or the ROI bootstrap. Peak frame and `ifi` are
explicit inputs; `computeFramePeaks`, median frame interval, peak latency, ROI
sampling and recording-specific preprocessing are outside scope. Only synthetic
traces are evaluated; no biological processed means are scored.

Wrapper policy deliberately rejects a last-frame peak, absent crossing, and
windows outside the available array. The source helper can access the next
derivative after its peak; its boundary/error behavior outside this subset has
not been replicated. Missing MATLAB `[]` becomes Python `None`; zero-area ratios
become JSON null rather than MATLAB Inf/NaN. These choices are explicit and do
not silently repair the published algorithm. Gate B remains open pending
recording metadata, observation matching and independent biological evidence.
