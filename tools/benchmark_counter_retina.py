"""Bounded isolated counter-RNG receptor screen; run inside Molab."""

import argparse
import ctypes as c
import hashlib
import json
from pathlib import Path
import time


def run(root: Path, cells: int = 3377, ticks: int = 100) -> dict:
    path = root / "data/derived/photon_counter_candidate_v2/libfly_photon_counter_diagnostic.so"
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

    microvilli = 30000
    seed = 19503
    photon_rate = 50000.0
    rate = (c.c_double * cells)(*([photon_rate] * cells))
    observed = (c.c_double * (9 * cells))()
    tick = c.c_uint64()
    handle = lib.fp_create(cells, microvilli, seed, 1024)
    if not handle:
        raise RuntimeError(lib.fp_last_error().decode())
    try:
        begin = time.perf_counter()
        result = lib.fp_advance(handle, rate, cells, ticks)
        elapsed = time.perf_counter() - begin
        if result:
            raise RuntimeError(lib.fp_last_error().decode())
        if lib.fp_observe(handle, observed, len(observed), c.byref(tick)):
            raise RuntimeError(lib.fp_last_error().decode())
        if tick.value != ticks:
            raise RuntimeError("incorrect final tick")
        return {
            "cells": cells,
            "microvilli_per_cell": microvilli,
            "ticks": ticks,
            "photon_rate_s": photon_rate,
            "seed": seed,
            "elapsed_s": elapsed,
            "first_voltage_mV": observed[0],
            "last_voltage_mV": observed[cells - 1],
            "build_id": lib.fp_build_identity().decode(),
            "binary_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "scope": "isolated candidate receptor, single run; no same-session XORWOW control or biological claim",
        }
    finally:
        lib.fp_destroy(handle)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/marimo/fly-project"))
    parser.add_argument("--cells", type=int, default=3377)
    parser.add_argument("--ticks", type=int, default=100)
    args = parser.parse_args()
    print("COUNTER_FULL_RETINA_SCREEN", json.dumps(run(args.root, args.cells, args.ticks)))
