# Conductance finite-state acceptance protocol

Question: does the CUDA conductance API fail closed when finite inputs overflow internal arithmetic, while preserving the ordinary finite trajectory?

This is a numerical runtime contract. It does not validate MaleCNS physiology, learning, full-graph speed or checkpoint continuation.

## Fixed conditions

Baseline source: main commit `28c8adb140fb33327fe3754f02ca422b5f9350c1`. Candidate: the immutable commit passed to `tools/run_molab_conductance_finite.py`; record it in metadata and HF source closure. Both builds use the same installed MoLab CUDA toolchain, RTX PRO 6000 Blackwell, `sm_120`, C++17, O2 and `--fmad=false`.

Use only tiny one/two/three-cell CSR fixtures. Do not load the full connectome. Device is exclusive for the bounded foreground run. All downloads, compilation, execution and hashing occur in MoLab. HF source/input receipt must precede compilation; build and result receipts gate subsequent stages.

## Required observations

1. Baseline reproduces a successful API status with nonfinite output for repeated finite direct-voltage input and for overflowing incoming conductance from two presynaptic cells. If reproduction fails, the premise is unresolved; do not silently change fixtures until a preferred answer appears.
2. Candidate rejects both cases before copying numerical output buffers. Sentinel buffers remain untouched. A subsequent call is rejected until an explicit reset succeeds.
3. Explicit reset restores a finite zero-drive trajectory for each handle.
4. A NaN direct input is rejected before mutation and does not invalidate an otherwise healthy model.
5. The ordinary eight-tick two-cell spiking fixture has bit-exact V/ge/gi/spike outputs between baseline and candidate on this device/build configuration.

All five checks must pass. Preserve terminal failure logs and report any missing check. An invalid chunk has no valid continuation state; reset starts a new trajectory and does not resume the failed episode. Other CUDA transport/copy failures may leave partial output buffers and must not be published as valid results.

## Execution and persistence

Run `tools/run_molab_conductance_finite.py` in a visible foreground notebook cell using exact source/baseline commits and a fresh remote directory. The runner emits stage receipts after server-verified content-addressed publication to private `TryDotAtwo/faithful-fly-artifacts`. On a failed build/test, archive the terminal log and stop. On HF failure, stop progression; no local export or fallback.

Prepared code and a draft PR are not test evidence. Do not mark the draft ready until remote execution and immutable result receipts are verified.
