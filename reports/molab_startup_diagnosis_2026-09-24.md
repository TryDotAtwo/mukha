# Molab notebook startup diagnosis (2026-09-24)

## Observed

- The original `faithful-fly-malecns-native` notebook and a dashboard duplicate repeatedly failed before a sandbox URL became available. The UI once showed `Installing dependencies` immediately before the failure.
- The exported original is 1,149,720 bytes (SHA-256 `6cdf06430badbf0311d5c186bef907d7906fb6f832fb2d3448d90b65b9cb304e`), with 255 marimo cells, 251 enabled. Enabled cells include CUDA toolchain downloads, source reconstruction, compilation, and archive operations.
- A one-cell imported notebook started on RTX Pro 6000 and executed a Python cell. `/dev/nvidia0` and `nvidia-smi` were present. The notebook is https://molab.marimo.io/notebooks/nb_sNfGmWCGQcefp8jgDfHpMN.
- In that clean notebook `HF_TOKEN` was absent and `/marimo/fly-project` did not exist. Thus notebook secrets and local sandbox files do not automatically carry over.
- A modified copy of the large notebook with all cells disabled failed to import with a generic `Failed to upload notebook`; this does not isolate the startup fault.

## Conclusion and next isolation step

The GPU service is operational. The failure follows the large historical notebook or its bootstrap, not every Molab GPU session. The exact crashing cell or dependency is **not established**: no sandbox startup log was available. Stop using the historical notebook as the executable entry point. Keep code and artifacts in versioned files/HF; use a small Molab notebook with explicit sequential stages and bounded runs. The next controlled test is to import small subsets of cells (or a minimal recovery runner), then add stages until the failing startup behavior is reproduced. Verify HF authorization in the new notebook before restoration; never print or embed the token in a cell or log.

This diagnosis proves neither biological validation nor end-to-end fly performance.

## Compact recovery (same day)

- Generated a two-cell, opt-in notebook with `tools/generate_compact_molab.py`. It pins the HF manifest and binary hash, verifies downloaded bytes, runs the one-receptor split-call/checkpoint replay in the Molab GPU sandbox, then publishes the completed replay artifact to HF. The recovery cell does not run until its button is pressed.
- Imported the corrected notebook as [faithful-fly-compact-recovery-v2](https://molab.marimo.io/notebooks/nb_6tmwBC8Dq1922wWciRPctp) and selected RTX Pro 6000. Its first cell executed, and `nvidia-smi` reported `NVIDIA RTX PRO 6000 Blackwell Server Edition`; the notebook reported zero errors. This supersedes a false-negative `/dev/nvidia0` probe during startup.
- `HF_TOKEN` was added to this notebook's Secrets. A scratchpad check confirmed access to the private HF dataset; the first cell's earlier `HF_TOKEN present: False` output is stale because it ran before the secret was added.
- The opt-in GPU replay restored a pinned binary and input manifest, verified their SHA256, and passed same-process, split-call, old-checkpoint-version rejection, and fresh-process checkpoint continuation checks. Scope: one receptor, ten ticks, one seed and input; this is an engineering replay, not biological validation or a speed result.
- The replay was archived at HF commit `23b6f0d34d2600ac756c874a590e8e1457af6cd5`, manifest `manifests/5c6722539249b905828ff06dc89910757bb96bd7a66d0ccfd95719f73ca904a8.json`. Four content objects were verified remotely. A fresh-directory restore downloaded and SHA256-verified all five file paths.
