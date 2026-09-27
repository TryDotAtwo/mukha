# CUDA numerical replay

`native/cuda_probe.cu` and `native/cuda_state.inc` implement an experimental
persistent C ABI declared in `native/cuda_state.h`. C++ owns all device buffers
and runs the tick loop. Python supplies fixtures and compares output;
there is no Python callback per neural step. `src/cuda.rs` provides a Rust owner
with validated slice lengths, serialized calls and reusable host output buffers.

The implementation supports FP32 and FP64, incoming CSR, a delay ring, and the same
integration/threshold/delivery/reset ordering as the CPU oracle. It allocates
all storage and cuSPARSE workspace when creating a model. `advance` records
voltage, synaptic state and spikes for at most the configured chunk capacity;
trace memory is O(neurons * chunk_capacity), independent of episode duration.
Calls preserve device state and simulation tick. Recording is synchronous;
streaming storage and backpressure orchestration remain pending.

Checkpoints include tick, voltage, synaptic state, refractory deadlines and the
entire spike delay ring. They bind to graph, weights, sensory mask and parameters,
but not chunk capacity. Header/version and FNV64 checks detect accidental damage;
this is not cryptographic authentication. Use outer SHA256 artifact manifests.
The format uses host-native little-endian IEEE754 fields and is not
interchangeable with the CPU checkpoint format. CPU/GPU cross-restore is untested.
Calls on one handle must be serialized. A device error poisons state until an
explicit reset or valid restoration; rejected host inputs do not mutate state.

cuSPARSE's non-transposed CSR ALG2 was selected for reproducible reduction.
See [NVIDIA generic API documentation](https://docs.nvidia.com/cuda/archive/12.6.1/cusparse/generic-api/generic-api-functions.html).
Installed cuSPARSE rejected mixed 64-bit row offsets / 32-bit columns. The
adapter therefore widens columns to 64 bits, leaving the source graph intact.
This increases device graph storage and must be included in memory measurements.

The first initcheck run found an uninitialized read in the installed cuSPARSE
vector-scaling kernel. Explicitly zeroing the SpMV output before the first tick
resolved it, including with beta=0. The failing log is retained as
`reports/cuda_initcheck_before_fix.log`; do not count numerical agreement alone
as sanitizer success.

## Current Windows build and check

```powershell
.\tools\build_cuda_probe.cmd
python tools/check_cuda_reference.py
python tools/check_cuda_state.py
.\tools\check_cuda_sanitizers.ps1
.\tools\check_cuda_sanitizers.ps1 -TestScript tools/check_cuda_state.py
cargo build --release --offline --features cuda
# Add the project build directory and installed CUDA bin directory to PATH.
.\target\release\faithful-fly.exe cuda-fixture build/brian_fixture.json build/rust_cuda_trace.json
python tools/check_native_reference.py --trace build/rust_cuda_trace.json --report reports/rust_cuda_brian_equivalence.json
```

The build script explicitly targets local SM86 with CUDA 12.5, MSVC and
`--fmad=false`, without fast math. It is not a Blackwell/Molab build script.
Linux can build a shared library with an appropriate installed toolkit:

```sh
nvcc -std=c++17 -O2 --fmad=false -Xcompiler -fPIC --shared native/cuda_probe.cu -o build/libfly_cuda_probe.so -lcusparse
```

That Linux command has not yet been executed. Select and record the actual GPU
architecture before a remote run. Do not infer remote compatibility from the
local Windows result.

Numerical replay evidence: `reports/cuda_brian_equivalence.json`. Persistent
state evidence: `reports/cuda_state.json` and `reports/cuda_state_sanitizers.json`.
Reports carry the exact library hash; older replay reports can refer to an older
build. Checkpoint tests cover chunking, fresh-instance restoration, graph mismatch,
corruption, truncation and explicit reset. These fixtures do not establish
full-graph speed, physiological fidelity or training.

## Full-author-graph pilot status

`shiu-pilot GRAPH PROTOCOL OUTPUT.json` reads the provenance-bound author graph
and preregistered inputs, advances chunks of 32 ticks, and writes every spike as
two little-endian uint32 values (tick, neuron index). It saves an end checkpoint.
It refuses an existing spike file, preserves partial results on its wall-time
limit, and never substitutes missing spikes. This is a bounded one-second pilot,
not yet a resumable long-running training job.

The first full sugar pilot completed, but strict comparison with Brian2 failed.
See `reports/shiu_sugar_pilot_comparison.json` and
`reports/shiu_precision_diagnostic.json`. The first shifted spike occurs near
threshold at 436.4 ms; small voltage differences subsequently change many spikes.
Do not promote small-fixture correctness to full-network numerical equivalence.

The controlled precision experiment (`reports/shiu_precision_control.json`)
subsequently reproduced all native FP32 events in independent PyTorch FP32 and
all Brian2 events in PyTorch FP64. Thus precision is sufficient to explain this
pilot's divergence. These are diagnostic oracles, not a replacement native
runtime. Native FP64 is now implemented and matches the full pilot too:
`reports/shiu_native64_comparison.json`. FP32 and FP64 compile from the same
equations, with separate exported symbols and checkpoint precision tags.

Build FP64 with `tools/build_cuda64.cmd`, then
`cargo build --release --offline --features cuda64`. The Rust pilot derives
double weights from exact signed source counts; it does not widen FP32 weights.
Run `python tools/check_cuda_state.py --dtype float64` for persistence checks.
The sanitizer runner accepts `-TestScript tools/check_cuda_state.py -Dtype float64`.
The FP64 parameter ABI is in `native/lif64.h` and `native/cuda_state64.h`.
