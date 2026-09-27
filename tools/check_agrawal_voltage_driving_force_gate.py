"""Test whether the current-based native synapse can express a 13Balpha voltage-dependence sign."""
import ctypes as ct
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DLL = ROOT / "build/fly_cuda64.dll"
PAPER = ROOT / "data/reference/agrawal2020/elife-60299-v2.pdf"
OUT = ROOT / "reports/agrawal_voltage_driving_force_gate.json"
cuda_dir = os.add_dll_directory(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\bin")
lib = ct.CDLL(str(DLL))


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
lib.ff_cuda64_advance.restype = ct.c_int
lib.ff_cuda64_destroy.argtypes = [ct.c_void_p]
lib.ff_cuda64_probe_error.restype = ct.c_char_p

row = np.array([0, 0, 1], np.uint64)
col = np.array([0], np.uint32)
sensory = np.zeros(2, np.uint8)
graded = np.array([1, 0], np.uint8)
p = Params(0.1, -60.0, -60.0, 100.0, 10.0, 5.0, 20, 10)
a = math.exp(-p.dt_ms / p.membrane_ms)


def run(post_baseline_shift_mv, weight_value):
    weight = np.array([weight_value], np.float64)
    h = lib.ff_cuda64_create_mixed(2, 1, row.ctypes.data, col.ctypes.data,
                                   weight.ctypes.data, sensory.ctypes.data,
                                   graded.ctypes.data, 20.0, p, 256)
    assert h, lib.ff_cuda64_probe_error()
    values = {}
    elapsed = 0
    try:
        for sample_ms in (20, 100):
            remaining = round(sample_ms / p.dt_ms) - elapsed
            while remaining:
                count = min(remaining, 256)
                drive = np.zeros((count, 2), np.float64)
                # The graded source stays at -50 mV before integration.
                drive[:, 0] = 10.0 / a - 10.0
                if elapsed == 0:
                    drive[0, 0] = 10.0 / a
                # This sets the no-synapse receiving baseline to rest +/-5 mV.
                drive[:, 1] = (1.0 - a) * post_baseline_shift_mv
                voltage = np.empty_like(drive)
                synapse = np.empty_like(drive)
                spikes = np.empty(drive.shape, np.uint8)
                assert lib.ff_cuda64_advance(h, count, drive.ctypes.data,
                                              voltage.ctypes.data, synapse.ctypes.data,
                                              spikes.ctypes.data) == 0, lib.ff_cuda64_probe_error()
                assert not np.any(spikes)
                elapsed += count
                remaining -= count
            values[str(sample_ms)] = {"post_voltage_mv": float(voltage[-1, 1]),
                                      "post_synaptic_state": float(synapse[-1, 1]),
                                      "source_voltage_mv": float(voltage[-1, 0])}
    finally:
        lib.ff_cuda64_destroy(h)
    return values


cases = {(shift, weight): run(shift, weight)
         for shift in (-5.0, 5.0) for weight in (0.0, 1.0)}
responses = {}
for sample in ("20", "100"):
    hyper = cases[(-5.0, 1.0)][sample]["post_voltage_mv"] - cases[(-5.0, 0.0)][sample]["post_voltage_mv"]
    depol = cases[(5.0, 1.0)][sample]["post_voltage_mv"] - cases[(5.0, 0.0)][sample]["post_voltage_mv"]
    assert hyper > 0 and depol > 0
    assert abs(hyper - depol) < 1e-10
    responses[sample] = {"hyperpolarized_baseline_evoked_mv": hyper,
                         "depolarized_baseline_evoked_mv": depol,
                         "depolarized_over_hyperpolarized": depol / hyper,
                         "difference_mv": depol - hyper}

report = {
    "source": "Agrawal et al. 2020 eLife 60299, Figure 2 supplement 1E/F and accompanying text",
    "source_pdf_sha256": hashlib.sha256(PAPER.read_bytes()).hexdigest(),
    "published_qualitative_observation": "Depolarizing a 13Balpha cell reduced its membrane-potential changes during tibia extension and flexion; authors infer changing excitatory driving force.",
    "native_dll_sha256": hashlib.sha256(DLL.read_bytes()).hexdigest(),
    "model": "two-cell uncalibrated FP64 mixed graded-source/current-based receiving synapse",
    "receiving_baselines_target_mv": [-65.0, -55.0],
    "presynaptic_voltage_target_mv": -50.0,
    "unit_graded_weight": 1.0,
    "no_spikes": True,
    "responses": responses,
    "result": "The current-based native synapse has equal evoked voltage amplitude at both receiving baselines; this model class cannot express the observed driving-force dependence in this subthreshold setting.",
    "biological_fit": False,
    "limitations": ["The published injection current, absolute voltage, and sensory waveform are not reproduced.",
                    "This does not identify the underlying biological connection as chemical or electrical.",
                    "A conductance-based candidate needs independent parameters and source-supported validation before enabling it in MaleCNS."]}
OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(responses))
cuda_dir.close()
