"""Independent two-cell recurrence checks for the separate CUDA conductance ABI."""
import ctypes as ct
import hashlib
import json
import os
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DLL = ROOT / "build/fly_cuda_conductance.dll"
OUT = ROOT / "reports/cuda_conductance_abi_reset.json"


class Params(ct.Structure):
    _fields_ = [(name, ct.c_double) for name in (
        "dt_ms", "rest_mv", "reset_mv", "threshold_mv", "membrane_ms",
        "synapse_ms", "reversal_exc_mv", "reversal_inh_mv")]
    _fields_ += [("refractory_ticks", ct.c_uint32), ("delay_ticks", ct.c_uint32)]


def run(lib, excitatory, inhibitory, chunks, check_reset=False):
    row = np.array([0, 0, 1], np.uint64)
    col = np.array([0], np.uint32)
    ex = np.array([excitatory], np.float64)
    inh = np.array([inhibitory], np.float64)
    sensory = np.array([1, 0], np.uint8)
    p = Params(.1, -52, -52, -45, 20, 5, 0, -70, 22, 1)
    handle = lib.fc_create(2, 1, row.ctypes.data, col.ctypes.data,
                           ex.ctypes.data, inh.ctypes.data, sensory.ctypes.data,
                           p, max(chunks))
    if not handle:
        raise RuntimeError(lib.fc_error().decode())
    values = []
    elapsed = 0
    try:
        for repeat in range(2 if check_reset else 1):
            elapsed = 0
            values = []
            for chunk in chunks:
                drive = np.zeros((chunk, 2), np.float64)
                if elapsed == 0:
                    drive[0, 0] = 68.75
                v = np.empty_like(drive)
                ge = np.empty_like(drive)
                gi = np.empty_like(drive)
                spike = np.empty((chunk, 2), np.uint8)
                rc = lib.fc_advance(handle, chunk, drive.ctypes.data, v.ctypes.data,
                                    ge.ctypes.data, gi.ctypes.data, spike.ctypes.data)
                if rc:
                    raise RuntimeError(lib.fc_error().decode())
                values.append(np.column_stack((v, ge, gi, spike)))
                elapsed += chunk
            combined = np.concatenate(values)
            if repeat == 0:
                original = combined
                if check_reset and lib.fc_reset(handle):
                    raise RuntimeError(lib.fc_error().decode())
            else:
                np.testing.assert_array_equal(combined, original)
    finally:
        lib.fc_destroy(handle)
    return original


def reference(excitatory, inhibitory, ticks):
    p = dict(dt=.1, rest=-52., reset=-52., threshold=-45., tau_m=20., tau_s=5.,
             ee=0., ei=-70., refractory=22, delay=1)
    v = [-52., -52.]
    ge = [0., 0.]
    gi = [0., 0.]
    nxt = [0, 0]
    history = []
    result = np.zeros((ticks, 8), np.float64)
    for tick in range(ticks):
        fired = [0, 0]
        active = [tick >= nxt[k] for k in range(2)]
        for k in range(2):
            if active[k]:
                total = 1 + ge[k] + gi[k]
                equilibrium = (p["rest"] + ge[k]*p["ee"] + gi[k]*p["ei"])/total
                v[k] = equilibrium + (v[k]-equilibrium)*np.exp(-p["dt"]*total/p["tau_m"])
            ge[k] *= np.exp(-p["dt"]/p["tau_s"])
            gi[k] *= np.exp(-p["dt"]/p["tau_s"])
            fired[k] = int(active[k] and v[k] > p["threshold"])
        delayed = history[tick-p["delay"]] if tick >= p["delay"] else [0, 0]
        ge[1] += excitatory*delayed[0]
        gi[1] += inhibitory*delayed[0]
        if active[0] and tick == 0:
            v[0] += 68.75
        for k in range(2):
            if fired[k]:
                v[k] = p["reset"]
                nxt[k] = tick + (0 if k == 0 else p["refractory"])
        history.append(fired)
        result[tick] = [v[0], v[1], ge[0], ge[1], gi[0], gi[1], fired[0], fired[1]]
    return result


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    directory = os.add_dll_directory(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\bin")
    lib = ct.CDLL(str(DLL))
    lib.fc_error.restype = ct.c_char_p
    lib.fc_create.argtypes = [ct.c_uint32, ct.c_uint64] + [ct.c_void_p]*5 + [Params, ct.c_uint32]
    lib.fc_create.restype = ct.c_void_p
    lib.fc_destroy.argtypes = [ct.c_void_p]
    lib.fc_reset.argtypes = [ct.c_void_p]
    lib.fc_advance.argtypes = [ct.c_void_p, ct.c_uint32] + [ct.c_void_p]*5
    cases = []
    try:
        for name, exc, inh in (("zero", 0., 0.), ("excitatory", .2, 0.),
                               ("inhibitory", 0., .2), ("mixed", .1, .1)):
            gpu = run(lib, exc, inh, [12], check_reset=True)
            cpu = reference(exc, inh, 12)
            np.testing.assert_allclose(gpu, cpu, rtol=0, atol=2e-14)
            split = run(lib, exc, inh, [3, 4, 5])
            np.testing.assert_array_equal(gpu, split)
            if name == "excitatory":
                assert -52 < gpu[5, 1] < 0 and gpu[2, 3] == .2
            if name == "inhibitory":
                assert -70 < gpu[5, 1] < -52 and gpu[2, 5] == .2
            if name == "zero":
                assert np.all(gpu[:, 1] == -52)
            cases.append({"name": name, "receiver_voltage_tick_5_mv": float(gpu[5, 1]),
                          "receiver_exc_state_tick_2": float(gpu[2, 3]),
                          "receiver_inh_state_tick_2": float(gpu[2, 5]),
                          "cpu_max_abs_error": float(np.max(np.abs(gpu-cpu))),
                          "chunk_equivalence": True, "reset_replay_exact": True})
    finally:
        directory.close()
    report = {"scope": "Two-cell numerical ABI verification, not full MaleCNS or receptor validation",
              "dll_sha256": hashlib.sha256(DLL.read_bytes()).hexdigest(),
              "source_sha256": hashlib.sha256((ROOT / "native/cuda_conductance.cu").read_bytes()).hexdigest(),
              "cases": cases, "passed": True}
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
