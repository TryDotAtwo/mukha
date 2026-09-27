# Molab native execution evidence

Notebook: https://molab.marimo.io/notebooks/nb_swoxyEkQ49XKqaajMAuPtR

The live session was checked before work; there were no GPU jobs. CUDA 12.8.93 failed to compile against the host math headers (cospi/sinpi exception specifications). The official CUDA 13.1.1 redistributions were downloaded and SHA-256 checked. Required components are cuda_nvcc, cuda_crt, libnvvm, cuda_cudart and cuda_cccl. The compiler is 13.1.115. The merged redistributions use `lib`, so the link command explicitly adds that directory. `tools/molab_cuda_cell.py` holds the reproducible setup cell, with pinned package hashes. Remote work stayed attached to the foreground marimo cell and SSE execution.

The unchanged Morris-Lecar author kernel and diagnostic driver were compiled with `-arch=sm_120 --fmad=false`. The four-cell, 10,000-step trace on RTX PRO 6000 Blackwell Server Edition matched the CPU-validated local GPU trace exactly. See `reports/molab_morris_comparison.json` and `reports/molab_cuda_toolchain.json`. Source text transfer normalizes line endings; report hashes describe the actual Linux source text.

The trace and Linux executable were exported to `build/molab_morris_trace.bin` and `build/molab_morris_probe_linux`, and their SHA-256 values verified locally. The authoritative live cell sources were exported to `build/fly_cuda_toolchain_setup_cell.py` and `build/fly_morris_blackwell_validation_cell.py`. Large binary export uses gzip to avoid marimo console truncation.

This validates this numerical probe only. Rust, complete graph execution, full-body integration, learning and KSP are still pending. Toolchain files under `/tmp` are temporary and must be rebuilt after sandbox loss. CPU affinity is not a CPU quota; UI allocation remains distinct from runtime affinity. Authentication lives only in ignored `build/molab_pair.private.json`; do not publish it.

## Phototransduction checkpoint on Blackwell

The safe VisTrans diagnostic was compiled with CUDA 13.1.115, pinned cuRAND 10.4.1.81 headers, `sm_120`, `--fmad=false`, entity RNG, 16 blocks and checkpoint replay. Two photoreceptors each contain 30,000 microvilli. At 0.1 ms per tick, the first trajectory runs 1,000 ticks; a snapshot at tick 500 is restored and the last 500 ticks repeated. Native comparison verifies all 3,720,160 persistent-state bytes, including molecular state and XORWOW state. Every exported voltage/adaptation sample after restore is identical too.

Evidence: `reports/molab_photon_checkpoint.json`. Local verification: `python tools/check_molab_photon_checkpoint.py`. The CSV and Linux executable are exported with verified SHA-256 hashes. Large compressed binaries are exported in 32,768-character chunks with explicit offsets and final length to avoid marimo console truncation. Saved live cell: `build/fly_photon_blackwell_checkpoint_cell.py`.

This is same-instance trusted memory restore, not a portable checkpoint or cross-device RNG equivalence. The recorded ~0.97 s wall time includes process startup and CSV generation and is not a full-retina or full-brain performance estimate. No biological calibration is established by this numerical check.

## Sandbox recovery
After the interrupted 1,000-tick resource run, a new sandbox was connected through the same saved notebook. Preflight found no GPU workload and 0 MiB device memory used. CUDA 13.1.115 and pinned cuRAND headers were rebuilt with package hash checks. Heavy validation cells were disabled before rebuilding dependencies to prevent reactive reruns. This recovery does not produce a replacement result for the interrupted measurement. Evidence: reports/molab_sandbox_recovery.json.
