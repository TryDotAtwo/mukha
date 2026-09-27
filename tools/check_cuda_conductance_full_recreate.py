"""Exercise two sequential full-CSR handle lifecycles in one process."""
import ctypes as ct
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from check_cuda_conductance import Params

ROOT = Path(__file__).resolve().parents[1]
G = ROOT / "data/derived/malecns_v1_candidates"
DLL = ROOT / "build/fly_cuda_conductance.dll"
OUT = ROOT / "reports/cuda_conductance_full_recreate.json"


def gpu_free(cudart):
    free = ct.c_size_t()
    total = ct.c_size_t()
    rc = cudart.cudaMemGetInfo(ct.byref(free), ct.byref(total))
    if rc:
        raise RuntimeError(f"cudaMemGetInfo={rc}")
    return int(free.value), int(total.value)


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    row = np.load(G / "indptr.npy", mmap_mode="r")
    col = np.load(G / "indices.npy", mmap_mode="r")
    n = len(row)-1
    edges = len(col)
    zero = np.zeros(edges, np.float64)
    sense = np.zeros(n, np.uint8)
    drive = np.zeros(n, np.float64)
    v = np.empty(n, np.float64)
    ge = np.empty(n, np.float64)
    gi = np.empty(n, np.float64)
    spikes = np.empty(n, np.uint8)
    directory = os.add_dll_directory(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\bin")
    lib = ct.CDLL(str(DLL))
    cudart = ct.CDLL("cudart64_12.dll")
    lib.fc_error.restype = ct.c_char_p
    lib.fc_create.argtypes = [ct.c_uint32, ct.c_uint64] + [ct.c_void_p]*5 + [Params, ct.c_uint32]
    lib.fc_create.restype = ct.c_void_p
    lib.fc_destroy.argtypes = [ct.c_void_p]
    lib.fc_advance.argtypes = [ct.c_void_p, ct.c_uint32] + [ct.c_void_p]*5
    before = gpu_free(cudart)
    states = []
    try:
        for iteration in (1, 2):
            handle = lib.fc_create(n, edges, row.ctypes.data, col.ctypes.data,
                                   zero.ctypes.data, zero.ctypes.data, sense.ctypes.data,
                                   Params(.1, -52, -52, -45, 20, 5, 0, -70, 22, 18), 1)
            if not handle:
                raise RuntimeError(f"create iteration {iteration}: {lib.fc_error().decode()}")
            during = gpu_free(cudart)
            try:
                if lib.fc_advance(handle, 1, drive.ctypes.data, v.ctypes.data,
                                  ge.ctypes.data, gi.ctypes.data, spikes.ctypes.data):
                    raise RuntimeError(lib.fc_error().decode())
                if not (np.all(v == -52) and np.all(ge == 0) and
                        np.all(gi == 0) and np.all(spikes == 0)):
                    raise ValueError("Zero-input full-graph baseline changed")
            finally:
                lib.fc_destroy(handle)
            after = gpu_free(cudart)
            states.append({"iteration": iteration, "free_during_bytes": during[0],
                           "free_after_destroy_bytes": after[0]})
    finally:
        directory.close()
    report = {"scope": "Two sequential full-CSR zero-weight GPU handle lifecycles; no synaptic physiology",
              "dll_sha256": hashlib.sha256(DLL.read_bytes()).hexdigest(),
              "graph_manifest_sha256": hashlib.sha256((G / "manifest.json").read_bytes()).hexdigest(),
              "gpu_free_before_bytes": before[0], "gpu_total_bytes": before[1],
              "states": states, "passed": True}
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
