# Stateful native photoreceptor API

`native/photon.h` and `native/photon.cu` expose the previously checked VisTrans
equations through a narrow C ABI. `src/photon.rs` owns the handle through RAII.
CUDA owns molecular arrays, membrane/adaptation state and per-microvillus XORWOW
state. The host retains a preallocated 9-row observation buffer. No allocation
occurs in the native advance loop. Initialization of microvilli runs on the GPU.

`fp_advance` accepts externally supplied per-cell photon rates in photons/second.
Each call holds these rates for a declared number of 0.1 ms ticks. Ten membrane
substeps of 0.01 ms follow the molecular update. All dynamic state persists
between calls; only `fp_reset` or a new instance establishes an episode boundary.
Observation returns integer time ticks and nine SoA rows: V, five gates,
adaptation, last photon input and a reserved zero row. Observations are diagnostic
outputs, not hidden numerical telemetry inputs to the CNS.

`fp_set_neural_feedback` supplies signed endogenous synaptic current in author
membrane units (microampere/cm²), held until replaced and zeroed by reset. It does
not set photon rates or membrane potentials. See `VISUAL_BOUNDARY.md` for the
anatomical motivation and independent numerical comparison. No real MaleCNS
conductance profile is enabled merely by exposing this input.

Only one live instance per library is currently supported because the pinned
kernel binds molecular buffers through CUDA symbols. A second factory call fails
explicitly. Calls are serialized, and a handle captures its CUDA device. The Rust
wrapper is neither Send nor Sync. Invalid dimensions, nonfinite/negative rates,
invalid tick counts and malformed output shapes are rejected before mutation.
CUDA or numerical failure during advance poisons the instance; partial progress
must not be treated as a valid episode. A successful explicit reset is required
before reuse. Representability checks on photon rates are not physiological
calibration; excessively large rates can be expensive.

`fp_checkpoint_size`, `fp_save` and `fp_load` now serialize complete persistent
state into a caller-owned host buffer. They include molecular arrays, membrane
and adaptation, opaque RNG bytes, feedback, tick and seed. Fixed owner/count/index
arrays are reconstructed from dimensions; current and work-queue arrays are
scratch and overwritten before use. Initial RNG padding is explicitly zeroed.
Rust exposes `snapshot`/`restore` and `save_file`/`load_file`.

The format has a 192-byte header with version, population, launch configuration,
RNG ABI size, CUDA runtime version, GPU compute capability and build fingerprint.
The fingerprint records native source hashes, CUDA headers, compiler identities
and flags (`tools/build_photon.py`, `reports/photon_build.json`). FNV-1a checks
metadata and payload, including time and seed; it is accidental-corruption
detection, not authentication of hostile input. Raw RNG bytes are trusted and
build-bound, not a portable interchange format. Compatibility across different
GPUs or platforms has not been established. Invalid headers, lengths, checksums
or invalid floating states are rejected before mutation. CUDA copy failures
poison the model and require successful explicit reset.

Rust file saving uses an exclusive sibling `.pending`, flushes/synchronizes the
file, closes it, and renames it over the destination. Failed publication removes
only its own temporary file. An existing `.pending` fails closed and is not
deleted. File reads check the expected size before allocation and reject short
or trailing data. This is process-level atomic publication; power-loss and remote
filesystem durability are unverified. The checkpoint itself contains no external
stimulus schedule or state of the body/CNS: an experiment must save these too.

## Local evidence

On RTX 3070 Laptop with CUDA 12.5, the C ABI exactly matched the earlier validated
entity-RNG 1,000-tick trace. The reference CSV hash is checked against the earlier
repeatability report. One 1,000-tick call and 1,000 one-tick calls produced identical
observations, including after a change from darkness to stimulation of the other
receptor. Reset, rejected-input state preservation and the one-instance guard
passed. These establish numerical execution, not a calibrated MaleCNS retina.

Rust testing passed ownership, destruction/reuse, reset, rejected input and
split-call equivalence. Compute Sanitizer memcheck (including zero leaked bytes),
racecheck, initcheck and synccheck passed for 1, 3 and 33 receptors, each with
1,001 microvilli, save at tick 20, restore/replay to tick 30 and reset. This is not a full-population or long-run
check. See `reports/photon_abi.json` and `reports/photon_abi_sanitizers.json`.

Fresh independent processes also passed a 3-receptor x 30,001-microvillus
checkpoint at tick 500 and continuation to tick 1,000 with changing external
stimuli. All 5,580,618 final snapshot bytes match, including metadata and RNG;
the resumed factory deliberately used a different seed and prior trajectory.
Eleven malformed snapshot cases were rejected without state mutation, including
time/seed corruption and recomputed-checksum NaN/gate violations. Evidence:
`reports/photon_abi_checkpoint.json`. Rust tests additionally cover full-state
restore, atomic file replacement, abandoned writes, a competing pending file,
Unicode paths and failed publication to a directory.

Reproduction from the repository root on the local Windows toolchain:

```powershell
.\tools\build_photon.cmd
python tools/check_photon_abi.py
python tools/check_photon_abi_checkpoint.py
$env:PATH = (Join-Path (Get-Location) 'build') + ';' + $env:PATH
cargo test --offline --features photon
.\tools\build_photon_abi_probe.cmd
.\tools\check_photon_sanitizers.ps1
```

Author HH/adaptation files in `build` come from the pinned extraction workflow in
`PHOTOTRANSDUCTION.md`. Photon calibration, actual image input, heterogeneous
receptor parameters, full CNS coupling and biological validation remain unfinished.

## Native build retention

The builder now archives each successful native DLL, source files, generated
build-ID header and build report under `build/photon-builds/<identity>.zip`.
`tools/archive_photon_build.py` verifies all source/library hashes and the build
fingerprint before writing. The preceding build was archived before the feedback
API changed, and the new build was archived after compilation. These are local
native-component archives, not a complete experiment/environment backup. CUDA
header/compiler hashes are recorded, but toolchain installations, Rust executable
history, scene state and full CNS checkpoints are not included.
