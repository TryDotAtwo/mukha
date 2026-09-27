"""Matched isolated XORWOW/counter retina timing in one Molab session.

Both libraries must be restored from the pinned HF manifests and verified
before running. This measures fp_advance only, not model construction or CNS.
"""

import ctypes as c
import hashlib
import json
import math
from pathlib import Path
import statistics
import time


ROOT = Path("/marimo/fly-project")
PATHS = {
    "xorwow": ROOT / "build/libfly_photon_coupled_current_diagnostic.so",
    "counter": ROOT / "data/derived/photon_counter_candidate_v2/libfly_photon_counter_diagnostic.so",
}
EXPECTED_SHA256 = {
    "xorwow": "2b24ed9428927c44643e7a269b22da8f827f699e789db5dabcc9b6aeb369665f",
    "counter": "179130e1eb50e9de1bac9df4c52f27a1efc379167cf5a40b6a30267afc090a31",
}


def open_library(path: Path):
    lib = c.CDLL(str(path))
    lib.fp_create.argtypes = [c.c_uint32, c.c_uint32, c.c_uint64, c.c_uint32]
    lib.fp_create.restype = c.c_void_p
    lib.fp_destroy.argtypes = [c.c_void_p]
    lib.fp_advance.argtypes = [c.c_void_p, c.c_void_p, c.c_size_t, c.c_uint32]
    lib.fp_advance.restype = c.c_int
    lib.fp_observe.argtypes = [c.c_void_p, c.c_void_p, c.c_size_t, c.POINTER(c.c_uint64)]
    lib.fp_observe.restype = c.c_int
    lib.fp_last_error.restype = c.c_char_p
    lib.fp_build_identity.restype = c.c_char_p
    return lib


def run():
    for name, path in PATHS.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != EXPECTED_SHA256[name]:
            raise RuntimeError(f"{name} library SHA256 mismatch")
    libs = {name: open_library(path) for name, path in PATHS.items()}
    cells, microvilli, ticks, seed = 3377, 30000, 100, 19503
    rate = (c.c_double * cells)(*([50000.0] * cells))
    order = ["xorwow", "counter", "counter", "xorwow", "xorwow", "counter"]
    rows = []
    for run_number, name in enumerate(order, 1):
        lib = libs[name]
        handle = lib.fp_create(cells, microvilli, seed, 1024)
        if not handle:
            raise RuntimeError(f"{name}: {lib.fp_last_error().decode()}")
        try:
            observed = (c.c_double * (9 * cells))()
            tick = c.c_uint64()
            start = time.perf_counter()
            rc = lib.fp_advance(handle, rate, cells, ticks)
            elapsed = time.perf_counter() - start
            if rc:
                raise RuntimeError(f"{name}: {lib.fp_last_error().decode()}")
            if lib.fp_observe(handle, observed, len(observed), c.byref(tick)):
                raise RuntimeError(f"{name}: {lib.fp_last_error().decode()}")
            if tick.value != ticks or not all(math.isfinite(x) for x in observed):
                raise RuntimeError("invalid final state")
            row = {"variant": name, "run": run_number, "elapsed_s": elapsed,
                   "tick": tick.value, "first_voltage_mV": observed[0],
                   "last_voltage_mV": observed[cells - 1]}
            rows.append(row)
            print("PAIRED_RETINA_RUN", json.dumps(row), flush=True)
        finally:
            lib.fp_destroy(handle)
    medians = {name: statistics.median(row["elapsed_s"] for row in rows
                                      if row["variant"] == name) for name in PATHS}
    report = {
        "scope": "Same-session isolated full-resolution VisTrans A/B; creation excluded from fp_advance timing",
        "cells": cells, "microvilli_per_cell": microvilli, "ticks": ticks,
        "photon_rate_s": 50000, "seed": seed, "order": order, "runs": rows,
        "median_s": medians,
        "xorwow_over_counter_ratio": medians["xorwow"] / medians["counter"],
        "binary_sha256": EXPECTED_SHA256,
        "build_id": {name: lib.fp_build_identity().decode() for name, lib in libs.items()},
        "limitations": "Different random streams; no distribution equivalence, complete-CNS timing or biological validation",
        "biological_gate_passed": False,
    }
    print("PAIRED_RETINA_RESULT", json.dumps(report), flush=True)
    return report


if __name__ == "__main__":
    run()
