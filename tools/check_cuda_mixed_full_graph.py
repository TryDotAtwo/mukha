"""Numerical full-CNS mixed-output stress check, not phenotype assignment."""
import ctypes as ct
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
base = root / "data/derived/malecns_v1_candidates"
source_report = json.loads((root / "reports/agrawal_13b_connectivity.json").read_text())
candidate_body = 800115
assert any(x["bodyId"] == candidate_body and x["snpp50_51_front_leg_edge_rows"]
           for x in source_report["candidates"])
ids = np.load(base / "body_ids.npy")
row = np.load(base / "indptr.npy")
col = np.load(base / "indices.npy")
counts = np.load(base / "synapse_counts.npy")
candidate_index = int(np.flatnonzero(ids == candidate_body)[0])
assert len(ids) == 167216 and len(col) == 25587572
labels = pd.read_feather(base / "neurotransmitters.feather").set_index("body").reindex(ids).consensus_nt.fillna("missing_annotation")
old_spec = json.loads((root / "data/derived/malecns_sign_diagnostic_float64_checkpoint_v2/report.json").read_text())["spec"]
sign = labels.map(dict(old_spec["shared_assumptions"], unclear=1)).to_numpy()
assert np.isfinite(sign.astype(float)).all()
weight = np.asarray(counts, np.float64) * np.asarray(sign, np.float64)[col] * old_spec["weight_mv_per_contact"]
n = len(ids)
sensory = np.zeros(n, np.uint8)
graded = np.zeros(n, np.uint8)
graded[candidate_index] = 1


class Params(ct.Structure):
    _fields_ = [(name, ct.c_double) for name in
                ("dt_ms", "rest_mv", "reset_mv", "threshold_mv", "membrane_ms", "synapse_ms")]
    _fields_ += [("refractory_ticks", ct.c_uint32), ("delay_ticks", ct.c_uint32)]


cuda_directory = os.add_dll_directory(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\bin")
dll = root / "build/fly_cuda64.dll"
lib = ct.CDLL(str(dll))
lib.ff_cuda64_create.argtypes = [ct.c_uint32, ct.c_uint64, ct.c_void_p, ct.c_void_p,
                                 ct.c_void_p, ct.c_void_p, Params, ct.c_uint32]
lib.ff_cuda64_create.restype = ct.c_void_p
lib.ff_cuda64_create_mixed.argtypes = [ct.c_uint32, ct.c_uint64, ct.c_void_p,
                                       ct.c_void_p, ct.c_void_p, ct.c_void_p,
                                       ct.c_void_p, ct.c_double, Params, ct.c_uint32]
lib.ff_cuda64_create_mixed.restype = ct.c_void_p
lib.ff_cuda64_advance.argtypes = [ct.c_void_p, ct.c_uint32, ct.c_void_p,
                                   ct.c_void_p, ct.c_void_p, ct.c_void_p]
lib.ff_cuda64_checkpoint_size.argtypes = [ct.c_void_p]
lib.ff_cuda64_checkpoint_size.restype = ct.c_size_t
lib.ff_cuda64_save.argtypes = [ct.c_void_p, ct.c_void_p, ct.c_size_t]
lib.ff_cuda64_load.argtypes = [ct.c_void_p, ct.c_void_p, ct.c_size_t]
lib.ff_cuda64_destroy.argtypes = [ct.c_void_p]
lib.ff_cuda64_probe_error.restype = ct.c_char_p
p = Params(0.1, -52, -52, -45, 20, 5, 22, 1)


def create(mixed):
    args = (n, len(col), row.ctypes.data, col.ctypes.data,
            weight.ctypes.data, sensory.ctypes.data)
    handle = (lib.ff_cuda64_create_mixed(*args, graded.ctypes.data, 20.0, p, 4)
              if mixed else lib.ff_cuda64_create(*args, p, 4))
    assert handle, lib.ff_cuda64_probe_error()
    return handle


def run(handle, drive):
    v = np.empty_like(drive)
    g = np.empty_like(drive)
    spikes = np.empty(drive.shape, np.uint8)
    rc = lib.ff_cuda64_advance(handle, len(drive), drive.ctypes.data,
                               v.ctypes.data, g.ctypes.data, spikes.ctypes.data)
    assert rc == 0, lib.ff_cuda64_probe_error()
    return v, g, spikes


drive = np.zeros((4, n), np.float64)
drive[0, candidate_index] = 5.0
mixed = create(True)
legacy = create(False)
try:
    mv, mg, ms = run(mixed, drive[:2])
    size = lib.ff_cuda64_checkpoint_size(mixed)
    state = (ct.c_uint8 * size)()
    assert lib.ff_cuda64_save(mixed, state, size) == 0
    tail = run(mixed, drive[2:])
    mv = np.concatenate((mv, tail[0]))
    mg = np.concatenate((mg, tail[1]))
    ms = np.concatenate((ms, tail[2]))
    lv, lg, ls = run(legacy, drive)
    assert np.all(ms == 0) and np.all(ls == 0)
    assert np.all(lg == 0)
    release = float(np.exp(-p.dt_ms / p.membrane_ms) * 5.0 / 20.0)
    edge_ix = np.flatnonzero(col == candidate_index)
    target_ix = np.searchsorted(row, edge_ix, side="right") - 1
    expected = np.zeros(n, np.float64)
    graded_step_factor = -np.expm1(-p.dt_ms / p.synapse_ms)
    np.add.at(expected, target_ix, weight[edge_ix] * release * graded_step_factor)
    np.testing.assert_allclose(mg[2], expected, rtol=1e-13, atol=1e-13)
    assert np.count_nonzero(mg[2]) == np.count_nonzero(expected)
    resumed = create(True)
    try:
        assert lib.ff_cuda64_load(resumed, state, size) == 0
        for a, b in zip(tail, run(resumed, drive[2:])):
            np.testing.assert_array_equal(a, b)
    finally:
        lib.ff_cuda64_destroy(resumed)
    report = {"scope": "full MaleCNS graph, artificial one-cell diagnostic mask only",
              "source_nodes_sha256": source_report["source_sha256"]["nodes.feather"],
              "runtime_dll_sha256": hashlib.sha256(dll.read_bytes()).hexdigest(),
              "candidate_body_id": candidate_body, "candidate_index": candidate_index,
              "graded_span_mv": 20.0, "voltage_jump_mv": 5.0,
              "graded_step_factor": float(graded_step_factor),
              "direct_outgoing_edge_rows": len(edge_ix),
              "direct_targets_with_nonzero_g_at_tick2": int(np.count_nonzero(mg[2])),
              "analytical_full_vector_match": True,
              "legacy_zero_spikes_and_synaptic_input": True,
              "mixed_checkpoint_suffix_exact": True,
              "biological_phenotype_assignment": False}
    (root / "reports/cuda_mixed_full_graph.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
finally:
    lib.ff_cuda64_destroy(mixed)
    lib.ff_cuda64_destroy(legacy)
