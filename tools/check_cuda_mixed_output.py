"""Two-cell numerical check of optional graded CUDA output and checkpointing."""
import ctypes as ct
import json
import os
import struct
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
cuda_directory = os.add_dll_directory(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\bin")
LIB = ct.CDLL(str(ROOT / "build/fly_cuda64.dll"))


class Params(ct.Structure):
    _fields_ = [(name, ct.c_double) for name in
                ("dt_ms", "rest_mv", "reset_mv", "threshold_mv", "membrane_ms", "synapse_ms")]
    _fields_ += [("refractory_ticks", ct.c_uint32), ("delay_ticks", ct.c_uint32)]


LIB.ff_cuda64_create.argtypes = [ct.c_uint32, ct.c_uint64, ct.c_void_p, ct.c_void_p,
                                 ct.c_void_p, ct.c_void_p, Params, ct.c_uint32]
LIB.ff_cuda64_create.restype = ct.c_void_p
LIB.ff_cuda64_create_mixed.argtypes = [ct.c_uint32, ct.c_uint64, ct.c_void_p,
                                       ct.c_void_p, ct.c_void_p, ct.c_void_p,
                                       ct.c_void_p, ct.c_double, Params, ct.c_uint32]
LIB.ff_cuda64_create_mixed.restype = ct.c_void_p
LIB.ff_cuda64_advance.argtypes = [ct.c_void_p, ct.c_uint32, ct.c_void_p, ct.c_void_p,
                                   ct.c_void_p, ct.c_void_p]
LIB.ff_cuda64_advance.restype = ct.c_int
LIB.ff_cuda64_checkpoint_size.argtypes = [ct.c_void_p]
LIB.ff_cuda64_checkpoint_size.restype = ct.c_size_t
LIB.ff_cuda64_save.argtypes = [ct.c_void_p, ct.c_void_p, ct.c_size_t]
LIB.ff_cuda64_save.restype = ct.c_int
LIB.ff_cuda64_load.argtypes = [ct.c_void_p, ct.c_void_p, ct.c_size_t]
LIB.ff_cuda64_load.restype = ct.c_int
LIB.ff_cuda64_destroy.argtypes = [ct.c_void_p]
LIB.ff_cuda64_probe_error.restype = ct.c_char_p

row = np.array([0, 0, 1], np.uint64)
col = np.array([0], np.uint32)
weight = np.array([10.0], np.float64)
sensory = np.zeros(2, np.uint8)
graded = np.array([1, 0], np.uint8)
p = Params(0.1, -60.0, -60.0, -40.0, 10.0, 5.0, 2, 1)
drive = np.zeros((8, 2), np.float64)
drive[0, 0] = 10.0


def create(mixed):
    args = (2, 1, row.ctypes.data, col.ctypes.data, weight.ctypes.data,
            sensory.ctypes.data)
    h = (LIB.ff_cuda64_create_mixed(*args, graded.ctypes.data, 20.0, p, 8)
         if mixed else LIB.ff_cuda64_create(*args, p, 8))
    assert h, LIB.ff_cuda64_probe_error()
    return h


def advance(h, x):
    x = np.ascontiguousarray(x)
    v = np.empty_like(x)
    g = np.empty_like(x)
    s = np.empty(x.shape, np.uint8)
    rc = LIB.ff_cuda64_advance(h, len(x), x.ctypes.data, v.ctypes.data,
                               g.ctypes.data, s.ctypes.data)
    assert rc == 0, LIB.ff_cuda64_probe_error()
    return v, g, s


mixed = create(True)
legacy = create(False)
try:
    mv, mg, ms = advance(mixed, drive[:4])
    lv, lg, ls = advance(legacy, drive)
    assert np.all(ms == 0) and np.all(ls == 0)
    assert np.all(lg == 0)
    assert mg[1, 1] == 0 and mg[2, 1] > 0
    graded_step_factor = -np.expm1(-p.dt_ms / p.synapse_ms)
    # At tick 0, the external voltage jump is applied after emission. The
    # first nonzero release is emitted at tick 1 and arrives after one delay.
    first_release = max(0.0, min(1.0,
        (p.rest_mv + np.exp(-p.dt_ms / p.membrane_ms) *
         (mv[0, 0] - p.rest_mv) - p.rest_mv) / 20.0))
    expected_g_at_tick2 = 10.0 * graded_step_factor * first_release
    np.testing.assert_allclose(mg[2, 1], expected_g_at_tick2, rtol=1e-13)
    size = LIB.ff_cuda64_checkpoint_size(mixed)
    checkpoint = (ct.c_uint8 * size)()
    assert LIB.ff_cuda64_save(mixed, checkpoint, size) == 0
    assert struct.unpack_from("<Q", checkpoint, 8)[0] == 3
    assert LIB.ff_cuda64_load(legacy, checkpoint, size) != 0
    rejected = create(True)
    try:
        before = (ct.c_uint8 * size)()
        after = (ct.c_uint8 * size)()
        assert LIB.ff_cuda64_save(rejected, before, size) == 0
        for old_version in (1, 2):
            stale = bytearray(bytes(checkpoint))
            struct.pack_into("<Q", stale, 8, old_version)
            stale_buffer = (ct.c_uint8 * size).from_buffer(stale)
            assert LIB.ff_cuda64_load(rejected, stale_buffer, size) != 0
            assert LIB.ff_cuda64_save(rejected, after, size) == 0
            assert bytes(before) == bytes(after)
    finally:
        LIB.ff_cuda64_destroy(rejected)
    suffix = advance(mixed, drive[4:])
    resumed = create(True)
    try:
        assert LIB.ff_cuda64_load(resumed, checkpoint, size) == 0
        for a, b in zip(suffix, advance(resumed, drive[4:])):
            np.testing.assert_array_equal(a, b)
    finally:
        LIB.ff_cuda64_destroy(resumed)
    report = {"scope": "two-cell diagnostic, uncalibrated linear graded release",
              "legacy_no_spikes_or_input": True,
              "mixed_first_postsynaptic_g_tick": int(np.flatnonzero(mg[:, 1] > 0)[0]),
              "first_release": first_release,
              "graded_step_factor": float(graded_step_factor),
              "expected_g_tick2": expected_g_at_tick2,
              "observed_g_tick2": float(mg[2, 1]),
              "legacy_rejects_mixed_checkpoint": True,
              "mixed_checkpoint_version": 3,
              "mixed_rejects_previous_versions_without_state_mutation": [1, 2],
              "mixed_checkpoint_suffix_exact": True}
    (ROOT / "reports/cuda_mixed_output.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
finally:
    LIB.ff_cuda64_destroy(mixed)
    LIB.ff_cuda64_destroy(legacy)
