"""Check graded release at equal physical time across three CUDA timesteps."""
import ctypes as ct
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np

root = Path(__file__).resolve().parents[1]
cuda_directory = os.add_dll_directory(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\bin")
dll = root / "build/fly_cuda64.dll"
lib = ct.CDLL(str(dll))


class Params(ct.Structure):
    _fields_ = [(name, ct.c_double) for name in
                ("dt_ms", "rest_mv", "reset_mv", "threshold_mv", "membrane_ms", "synapse_ms")]
    _fields_ += [("refractory_ticks", ct.c_uint32), ("delay_ticks", ct.c_uint32)]


lib.ff_cuda64_create_mixed.argtypes = [ct.c_uint32, ct.c_uint64, ct.c_void_p,
                                       ct.c_void_p, ct.c_void_p, ct.c_void_p,
                                       ct.c_void_p, ct.c_double, Params, ct.c_uint32]
lib.ff_cuda64_create_mixed.restype = ct.c_void_p
lib.ff_cuda64_advance.argtypes = [ct.c_void_p, ct.c_uint32, ct.c_void_p,
                                   ct.c_void_p, ct.c_void_p, ct.c_void_p]
lib.ff_cuda64_destroy.argtypes = [ct.c_void_p]
lib.ff_cuda64_probe_error.restype = ct.c_char_p
row = np.array([0, 0, 1], np.uint64)
col = np.array([0], np.uint32)
weight = np.array([1.0], np.float64)
sensory = np.zeros(2, np.uint8)
graded = np.array([1, 0], np.uint8)
times_ms = (20.0, 100.0)
traces = []

for dt in (0.2, 0.1, 0.05):
    delay_ticks = round(1.0 / dt)
    refractory_ticks = round(2.0 / dt)
    assert math.isclose(delay_ticks * dt, 1.0) and math.isclose(refractory_ticks * dt, 2.0)
    p = Params(dt, -60.0, -60.0, 100.0, 10.0, 5.0, refractory_ticks, delay_ticks)
    handle = lib.ff_cuda64_create_mixed(2, 1, row.ctypes.data, col.ctypes.data,
                                        weight.ctypes.data, sensory.ctypes.data,
                                        graded.ctypes.data, 20.0, p, 256)
    assert handle, lib.ff_cuda64_probe_error()
    a = math.exp(-dt / p.membrane_ms)
    post_voltage_delta = 10.0 / a
    values = {}
    elapsed = 0
    try:
        for target_ms in times_ms:
            steps = round(target_ms / dt) - elapsed
            while steps:
                chunk = min(steps, 256)
                drive = np.zeros((chunk, 2), np.float64)
                drive[:, 0] = post_voltage_delta - 10.0
                if elapsed == 0:
                    drive[0, 0] = post_voltage_delta
                v = np.empty_like(drive)
                g = np.empty_like(drive)
                spikes = np.empty(drive.shape, np.uint8)
                assert lib.ff_cuda64_advance(handle, chunk, drive.ctypes.data,
                                              v.ctypes.data, g.ctypes.data,
                                              spikes.ctypes.data) == 0, lib.ff_cuda64_probe_error()
                assert not np.any(spikes)
                elapsed += chunk
                steps -= chunk
            active_steps = max(0, elapsed - delay_ticks - 1)
            expected = 0.5 * (1.0 - math.exp(-active_steps * dt / p.synapse_ms))
            np.testing.assert_allclose(g[-1, 1], expected, rtol=0, atol=2e-12)
            values[str(int(target_ms))] = {"observed_g": float(g[-1, 1]),
                                           "analytical_g": expected,
                                           "observed_receiver_voltage_mv": float(v[-1, 1]),
                                           "source_pre_integration_voltage_mv": -50.0,
                                           "active_physical_ms": active_steps * dt}
    finally:
        lib.ff_cuda64_destroy(handle)
    traces.append({"dt_ms": dt, "delay_ticks": delay_ticks,
                   "refractory_ticks": refractory_ticks, "values": values})

spread_20 = max(x["values"]["20"]["observed_g"] for x in traces) - min(x["values"]["20"]["observed_g"] for x in traces)
spread_100 = max(x["values"]["100"]["observed_g"] for x in traces) - min(x["values"]["100"]["observed_g"] for x in traces)
continuum_20 = 0.5 * (1.0 - math.exp(-(20.0 - 1.0) / 5.0))
continuum_errors_20 = [abs(x["values"]["20"]["observed_g"] - continuum_20) for x in traces]
continuum_voltage_20 = -60.0 + 0.5 * (1.0 - math.exp(-(20.0 - 1.0) / 10.0)) ** 2
voltage_errors_20 = [abs(x["values"]["20"]["observed_receiver_voltage_mv"]
                         - continuum_voltage_20) for x in traces]
assert continuum_errors_20[0] > continuum_errors_20[1] > continuum_errors_20[2]
assert voltage_errors_20[0] > voltage_errors_20[1] > voltage_errors_20[2]
assert spread_20 < 0.0005 and spread_100 < 1e-8
report = {"scope": "voltage-clamped two-cell numerical diagnostic at equal physical time",
          "dll_sha256": hashlib.sha256(dll.read_bytes()).hexdigest(),
          "weight_semantics_for_graded_source": "steady synaptic-state contribution at unit release",
          "step_contribution": "weight * release * (1-exp(-dt/tau_synapse))",
          "graded_release_raw": 0.5, "refractory_physical_ms": 2.0,
          "delay_physical_ms": 1.0, "traces": traces,
          "g_spread_at_20ms": spread_20, "g_spread_at_100ms": spread_100,
          "continuum_g_at_20ms": continuum_20,
          "errors_toward_continuum_at_20ms": continuum_errors_20,
          "idealized_continuum_receiver_voltage_at_20ms_mv": continuum_voltage_20,
          "voltage_errors_toward_idealized_continuum_at_20ms_mv": voltage_errors_20,
          "voltage_continuum_scope": "Constant source release=0.5 beginning at a physical 1-ms delay, tau_m=10ms, tau_s=5ms: V-rest=0.5*(1-exp(-(t-delay)/10ms))^2. The CUDA source initial step and split scheduling approach this limit; this is not an exact solution for arbitrary network inputs.",
          "biological_calibration": False}
(root / "reports/cuda_mixed_dt_convergence.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"g_spread_at_20ms": spread_20, "g_spread_at_100ms": spread_100,
                  "g_at_100ms": [x["values"]["100"]["observed_g"] for x in traces]}))
