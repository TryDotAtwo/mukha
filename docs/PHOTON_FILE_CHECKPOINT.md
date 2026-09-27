# Build-bound phototransduction file checkpoints

`native/photon_checkpoint.hpp` and the `FF_FILE_CHECKPOINT` branch of `native/phototransduction_probe.cu` add diagnostic save/resume across process exits. Build with entity RNG and a 64-character `FF_CHECKPOINT_BUILD_ID` derived from sources, compiler/toolchain, cuRAND and flags. The in-memory replay mode is mutually exclusive.

CLI: `probe 1000 ONSET save checkpoint.bin`, then a separate `probe 1000 ONSET resume checkpoint.bin`. Save occurs before tick 500 is advanced; resume starts at that same boundary. The test also emits `checkpoint.bin.final` for comparison. Current time and protocol are fixed by the validated header, not inferred from a CSV.

The container has twelve uint64 header fields, a 64-byte build identity and the raw persistent payload. Header checks cover schema, population, microvilli, duration, onset, saved tick, RNG state size, payload length, CUDART version and seed. FNV-1a checks accidental payload corruption. All header, length and integrity checks finish before copying restored state to the GPU. Scratch buffers are recomputed; device pointers are reconstructed in the new process.

This format uses host byte order and raw cuRAND state. It is trusted and build-bound, not a stable cross-platform checkpoint ABI and not authenticated against malicious edits. Writes now use an exclusively created sibling `.pending` file, flush and OS file sync, followed by atomic replacement on supported local filesystems. An exception before publication preserves the previous destination and removes only the temporary file owned by this writer. A stale or competing `.pending` file causes a closed failure and is never silently removed. Directory fsync, power-loss durability, network-filesystem semantics and periodic rotation retaining earlier generations remain unverified.

## Evidence

On Molab RTX PRO 6000 Blackwell, two separate-process tests (light onset 250 and 750, checkpoint at 500, final tick 1000) reproduced every final state byte and every recorded continuation sample. Each case rejected truncated, appended, payload-corrupted, build-ID-corrupted and configuration-corrupted files. `reports/molab_photon_file_checkpoint.json` records commands, source hashes, binary hash and snapshot hashes. No full-brain checkpoint is claimed.

The executable, two snapshots, final states and CSVs were exported locally under `build/molab_file_checkpoint_artifacts`. Run `python tools/check_file_checkpoint_export.py` to verify the exported bundle hashes and continuation traces. The live notebook test cell source is mirrored in `build/molab_file_checkpoint_cell.py`.

## Atomic publication validation

`native/atomic_checkpoint_test.cpp` passed on local Windows/MSVC and Molab Linux/g++: initial publication, abandoned write, collision with another pending writer, replacement and failed publication. The full GPU fresh-process continuation and malformed-input tests were repeated after integration; both onset cases pass (`reports/molab_photon_file_atomic.json`). The newly exported snapshots, executable and traces are in `build/molab_file_atomic_artifacts`; verify with `python tools/check_file_checkpoint_export.py --bundle build/molab_file_atomic_bundle.txt --destination build/molab_file_atomic_artifacts`. These tests exercise exceptions and ordinary process operation, not physical power cuts.
