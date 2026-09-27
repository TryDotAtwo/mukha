# Review contract for the first compact recovery run

Proposed operator: Astra 1 alone. Notebook: `faithful-fly-compact-recovery-v2`.
This is a CPU measurement-sensitivity diagnostic, not a model run or a biological
gate pass. Other peers review local code/artifacts and do not write to its kernel.

## Scientific scope

Use only the eight processed control curves in the four already pinned
`L1/L2_highLum/lowLum.mat` files. Preserve raw deltaF/F, row identity and all
63 samples. These means do not supply individual ROI bootstrap inputs,
recording IDs, calibrated photon rates or measured flash timing. Do not assign
one stimulus family to a luminosity label or silently baseline-subtract.

Peak selection must be a declared diagnostic rule shared across comparison
branches (for example, the historical polarity extremum over Python `[2:31]`).
That rule is not `computeFramePeaks.m` replication. Record both the zero-based
array index and the one-based peak passed to the sampled helper.

Record the actual `median(diff(t))`, any interval-uniformity check and the
resulting integer `floor(.25/ifi)`. Do not silently replace the measured array
interval with `1/120` or round the endpoint: floor is sensitive to floating
representation. The author's endpoint is a one-based sample index, whereas
the historical endpoint is a timestamp search relative to nominal index 2.

## Required comparison outputs

For each file/row, retain:

- Input Git blob/SHA256; row/contrast and supplied peak rule.
- Nominal onset, first/second sampled boundary, interpolated crossing if used,
  integration endpoint and index convention for each branch.
- Signed first and second areas with explicit units. Historical deltaF/F-second
  integrals need a factor of 100 to compare to source percent-deltaF/F seconds.
- Signed raw ratio `area2/area1`, source display `-area2/area1` and legacy
  `abs(area2/area1)` as distinct fields. Never relabel abs as source display.
- A reason when a crossing, window or nonzero denominator is unavailable;
  do not silently skip a curve or turn missing output into zero.

If sampled-author and historical branches change onset, endpoint and crossing
together, call the difference a **combined convention sensitivity**. Attributing
it specifically to interpolation requires an additional matched-onset/endpoint
comparison. Rectification can be isolated algebraically on the same areas.

## Acceptance and existing reference controls

All eight intended curve identities must appear exactly once. Source checks and
invalid-domain checks must survive `python -O`. The run must retain the source
commit, runner hash, declared assumptions, output checksums and terminal status.
Numerical comparison uses scale-aware tolerances; byte equality is appropriate
only for identical serialization/environment claims.

Already reviewed controls in `3639331` need not be rerun merely for repetition:
light `[0,1,3,1,-1,-1,2]`, peak 3, ifi .04 gives boundaries 1/5, endpoint 6,
areas 18/-4 and signed ratio -2/9. Returning-tail fixture gives raw ratio +1,
source display -1 and legacy absolute +1. These are useful independent expected
values if new runner transformations need a regression check.

No token, tokenized endpoint or pairing contents belong in source cells,
manifests or reports. The artifact provenance above uses only public source
identifiers and numerical settings. Dryad 401/403 is an independent unresolved
access dependency; the run neither retries it nor claims to resolve it.

## Independent numerical checker

`python tools/check_pang_measurement_result.py /path/to/retrieved/run-directory`
reconstructs the eight-curve result from the archived public MAT bytes, checking
source Git blobs, curve uniqueness, supplied peak, interval, boundaries, signed
areas and four ratio fields. It uses vector derivative comparisons and NumPy
trapezoids independently of the runner's sampled helper; historical integrals
are rebuilt from segments rather than trusted from the stored baseline report.
It is scoped to the declared historical `[2:31]` peak policy and fixed eight
processed means. A different protocol requires its own review.

Local review of runner `7df31f79da4a00412aa169ef0a4f3ee3f2849b3f` matched all
fields at relative tolerance 1e-12 / absolute 1e-14, maximum absolute discrepancy
8.881784197001252e-16. In-memory display-sign, area-unit and duplicate-row
mutations were rejected under `python -O`. This checker does not authenticate
remote execution, enforce single ownership or replace archive-manifest checks.
