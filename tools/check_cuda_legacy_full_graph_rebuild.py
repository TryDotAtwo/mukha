"""Replay old full-CNS checkpoints with the rebuilt optional-mixed CUDA DLL."""
import ctypes as ct
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
base = root / "data/derived/malecns_v1_candidates"
archive = root / "data/derived/malecns_sign_diagnostic_float64_checkpoint_v2"
meta = json.loads((archive / "report.json").read_text())
spec = meta["spec"]
assert meta["complete"] and spec["checkpoint_tick"] == 500 and spec["steps"] == 1000
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(base / "manifest.json") == spec["graph_manifest_sha256"]
manifest = json.loads((base / "manifest.json").read_text())
for filename in ("body_ids.npy", "indptr.npy", "indices.npy", "synapse_counts.npy", "neurotransmitters.feather"):
    assert sha(base / filename) == manifest["files"][filename]["sha256"]

ids = np.load(base / "body_ids.npy")
rows = np.load(base / "indptr.npy")
cols = np.load(base / "indices.npy")
counts = np.load(base / "synapse_counts.npy")
labels = pd.read_feather(base / "neurotransmitters.feather").set_index("body").reindex(ids).consensus_nt.fillna("missing_annotation")
source = int(np.flatnonzero(ids == spec["input_body"])[0])
n = len(ids)


class Params(ct.Structure):
    _fields_ = [(name, ct.c_double) for name in
                ("dt_ms", "rest_mv", "reset_mv", "threshold_mv", "membrane_ms", "synapse_ms")]
    _fields_ += [("refractory_ticks", ct.c_uint32), ("delay_ticks", ct.c_uint32)]


cuda_directory = os.add_dll_directory(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\bin")
dll_path = root / "build/fly_cuda64.dll"
lib = ct.CDLL(str(dll_path))
lib.ff_cuda64_create.argtypes = [ct.c_uint32, ct.c_uint64, ct.c_void_p, ct.c_void_p,
                                 ct.c_void_p, ct.c_void_p, Params, ct.c_uint32]
lib.ff_cuda64_create.restype = ct.c_void_p
lib.ff_cuda64_load.argtypes = [ct.c_void_p, ct.c_void_p, ct.c_size_t]
lib.ff_cuda64_advance.argtypes = [ct.c_void_p, ct.c_uint32, ct.c_void_p, ct.c_void_p,
                                   ct.c_void_p, ct.c_void_p]
lib.ff_cuda64_destroy.argtypes = [ct.c_void_p]
lib.ff_cuda64_probe_error.restype = ct.c_char_p

capacity = 20
sense = np.zeros(n, np.uint8)
sense[source] = 1
drive = np.zeros((capacity, n), np.float64)
voltage = np.empty_like(drive)
synapse = np.empty_like(drive)
spikes = np.empty((capacity, n), np.uint8)
variants = []
for name, unknown in spec["variants"].items():
    old = next(x for x in meta["results"] if x["variant"] == name)
    signs = labels.map(dict(spec["shared_assumptions"], unclear=unknown))
    assert signs.notna().all()
    weights = np.asarray(counts, np.float64) * np.asarray(signs, np.float64)[cols] * spec["weight_mv_per_contact"]
    assert hashlib.sha256(weights.tobytes()).hexdigest() == old["weights_sha256"]
    handle = lib.ff_cuda64_create(n, len(cols), rows.ctypes.data, cols.ctypes.data,
                                  weights.ctypes.data, sense.ctypes.data,
                                  Params(0.1, -52, -52, -45, 20, 5, 22, 18), capacity)
    assert handle, lib.ff_cuda64_probe_error()
    checkpoint_path = archive / f"{name}_checkpoint.bin"
    assert sha(checkpoint_path) == meta["files"][checkpoint_path.name]
    checkpoint = np.frombuffer(checkpoint_path.read_bytes(), np.uint8).copy()
    events = []
    try:
        assert lib.ff_cuda64_load(handle, checkpoint.ctypes.data, len(checkpoint)) == 0, lib.ff_cuda64_probe_error()
        for tick in range(500, 1000, capacity):
            drive.fill(0)
            if tick % 100 == 0:
                drive[0, source] = spec["voltage_jump_mv"]
            assert lib.ff_cuda64_advance(handle, capacity, drive.ctypes.data,
                                          voltage.ctypes.data, synapse.ctypes.data,
                                          spikes.ctypes.data) == 0, lib.ff_cuda64_probe_error()
            ts, ix = np.nonzero(spikes)
            events.append(np.column_stack((ts + tick, ix)).astype(np.uint32))
        events = np.concatenate(events)
        archived = np.load(archive / f"{name}_events.npy")
        np.testing.assert_array_equal(events, archived[archived[:, 0] >= 500])
        with np.load(archive / f"{name}_final_state.npz") as old_state:
            np.testing.assert_array_equal(voltage[-1], old_state["v"])
            np.testing.assert_array_equal(synapse[-1], old_state["g"])
        variants.append({"variant": name, "suffix_events_exact": len(events),
                         "final_state_bit_exact": True})
    finally:
        lib.ff_cuda64_destroy(handle)

report = {"scope": "legacy FP64 full MaleCNS graph, archived checkpoint ticks 500-999",
          "new_dll_sha256": sha(dll_path), "old_dll_sha256": meta["library_sha256"],
          "archive_report_sha256": sha(archive / "report.json"), "variants": variants,
          "biological_validation": False}
(root / "reports/cuda_legacy_full_graph_rebuild.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
