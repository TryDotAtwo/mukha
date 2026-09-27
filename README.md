# Faithful fly / Mun landing

Ardor continuation: [handoff](ARDOR_HANDOFF.md) and
[four-chat setup status](handoff/ARDOR_STATUS.md).
Large scientific inputs and outputs are distributed separately through
[GitHub Releases](https://github.com/TryDotAtwo/mukha/releases).
Original project code is MIT licensed; [third-party terms](THIRD_PARTY.md) remain
with their respective sources.

Research implementation in progress. The accepted scope and gates are in
[WORK_PLAN.md](WORK_PLAN.md). A successful landing cannot substitute for passing
the biological and causal checks.

## Implemented

- Provenance-locked MaleCNS import, complete candidate-population incoming CSR,
  source-row identities, annotations and boundary accounting.
- Pinned original Shiu model and a deterministic Brian2 numerical fixture.
- PyTorch oracle and native C++ FP32 stepping behind a Rust-owned C ABI wrapper.
- Native checkpoint save/restore and artifact hash verification.
- Stateful CUDA photoreceptors with external photon input and a Rust C ABI
  wrapper (`photon` feature); see [PHOTON_NATIVE_API.md](docs/PHOTON_NATIVE_API.md).
- Native image-to-photoreceptor integration with explicit engineering optical
  assumptions, recorded image hashes and exact fresh-process continuation;
  see [VISUAL_INPUT_PIPELINE.md](docs/VISUAL_INPUT_PIPELINE.md). Real MaleCNS
  optical registration and spectral calibration remain unresolved.

The native CPU backend and experimental persistent CUDA/cuSPARSE backend passed
the same numerical fixture; CUDA checks ran on a physical RTX 3070 Laptop;
see [CUDA_PROBE.md](docs/CUDA_PROBE.md). Neither backend has yet reproduced the
full MaleCNS biological experiments. A physical body/contact diagnostic and its
recording exist ([BODY_DIAGNOSTIC.md](docs/BODY_DIAGNOSTIC.md)); they are not driven
by the CNS. There is no trained rocket pilot or completed KSP bridge.

Rust now drives persistent CUDA state directly with the optional `cuda` feature.
A full original Shiu sugar pilot has run, but its comparison with Brian2 failed:
the first near-threshold spike shifts by one tick at 436.4 ms. This discrepancy
is explained by a controlled precision comparison. Native FP64 now matches all
9,440 Brian2 spike events for this pilot; biological replication is not passed.
Use feature `cuda64` after building `tools/build_cuda64.cmd` for this reference path.

The Molab full-CNS visual flash diagnostic and its corrected photoreceptor
variant are recorded in [VISUAL_CAUSALITY.md](docs/VISUAL_CAUSALITY.md).
The controlled old/new bridge comparison preserves the L1/L2 response, but
the visual biological gate remains failed. The measured GPU bottleneck and
negative launch-tuning results are in
[PHOTON_PERFORMANCE_2026-09-24.md](docs/PHOTON_PERFORMANCE_2026-09-24.md).

## Reproduce current checks

Use Python with `requirements-reference.txt`, Rust and a C++17 compiler.
The reference scripts also support Brian2 installed under `build/python-reference`.
Run from this directory:

```powershell
python tools/fetch_reference.py
python tools/check_brian_reference.py
cargo build --release --offline
.\target\release\faithful-fly.exe fixture build/brian_fixture.json build/native_trace.json
python tools/check_native_reference.py
python -m pytest tests/test_connectome.py -q
.\target\release\faithful-fly.exe verify-graph data/derived/malecns_v1_candidates
python tools/verify_malecns_csr_semantics.py
python tools/verify_graph_semantics.py
```

The fast CSR check verifies file hashes, array shapes, all index bounds,
strict ordering within every postsynaptic row, unique source-row and body IDs,
and the manifest's contact, self-edge and isolated-node totals. The subsequent
source-semantic check rereads every retained row from the original Feather
export and compares its endpoints and contact count. Neither establishes
transmitter signs, neural dynamics or biological completeness.

Offline Cargo requires cached dependencies; otherwise use the ordinary online
build. Source acquisition and graph construction are separate bounded operations:
`tools/fetch_malecns.py`, `tools/audit_malecns.py`, `tools/build_connectome.py`.
The builder refuses an existing output directory. Do not overwrite source data.

Reports in `reports/` distinguish numerical fixtures, source provenance and
graph integrity. Raw datasets and large generated traces are ignored by Git.
See `docs/NUMERICAL_CONTRACT.md` for the integration schedule and units.
