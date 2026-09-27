"""Untuned full-graph replication check at published feeding-circuit cell types."""
import ctypes as ct
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.feather as feather

from check_cuda_reference import Params

ROOT = Path(__file__).resolve().parents[1]
G = ROOT / "data/derived/malecns_v1_candidates"
OUT = ROOT / "reports/tastekin2026_premotor_probe.json"
TARGET_IDS = {"Roundup": [26764, 523040], "G2N-1": [31018, 89638],
              "Scapula": [11896, 12811, 12900]}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    manifest = json.loads((G / "manifest.json").read_text())
    for name in ("body_ids.npy", "indptr.npy", "indices.npy", "synapse_counts.npy",
                 "neurotransmitters.feather", "nodes.feather"):
        if sha(G / name) != manifest["files"][name]["sha256"]:
            raise ValueError("Graph hash mismatch: " + name)
    cross = json.loads((ROOT / "reports/tastekin2026_malecns_crosswalk.json").read_text())
    nodes = feather.read_table(G / "nodes.feather").to_pandas().set_index("bodyId")
    ids = np.load(G / "body_ids.npy")
    rows = np.load(G / "indptr.npy")
    cols = np.load(G / "indices.npy")
    counts = np.load(G / "synapse_counts.npy")
    by_id = {int(value): i for i, value in enumerate(ids)}
    for name, bodies in TARGET_IDS.items():
        if any(name not in str(nodes.at[body, "synonyms"]) for body in bodies):
            raise ValueError("Named target annotation mismatch: " + name)
    observed = {name: [by_id[body] for body in bodies] for name, bodies in TARGET_IDS.items()}
    sweet = [by_id[body] for body in cross["populations"]["sweet_candidate_LB3c"]["body_ids"]]
    bitter = [by_id[body] for body in cross["populations"]["bitter_candidate_LB1a_d"]["body_ids"]]
    nt = pd.read_feather(G / "neurotransmitters.feather").set_index("body").reindex(ids).consensus_nt.fillna("missing_annotation")
    common = {"acetylcholine": 1, "gaba": -1, "glutamate": -1, "histamine": -1,
              "dopamine": 0, "octopamine": 0, "serotonin": 0, "missing_annotation": 0}
    params64 = type("Params64", (ct.Structure,), {"_fields_": [
        (name, ct.c_double if kind is ct.c_float else kind) for name, kind in Params._fields_]})
    directory = os.add_dll_directory(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\bin")
    dll = ROOT / "build/fly_cuda64.dll"
    lib = ct.CDLL(str(dll))
    lib.ff_cuda64_probe_error.restype = ct.c_char_p
    lib.ff_cuda64_create.argtypes = [ct.c_uint32, ct.c_uint64] + [ct.c_void_p] * 4 + [params64, ct.c_uint32]
    lib.ff_cuda64_create.restype = ct.c_void_p
    lib.ff_cuda64_destroy.argtypes = [ct.c_void_p]
    lib.ff_cuda64_advance.argtypes = [ct.c_void_p, ct.c_uint32] + [ct.c_void_p] * 4
    cap = 20
    n = len(ids)
    sense = np.zeros(n, np.uint8)
    drive = np.zeros((cap, n), np.float64)
    voltage = np.empty_like(drive)
    synapse = np.empty_like(drive)
    spikes = np.empty((cap, n), np.uint8)
    results = []
    try:
        for unclear in (1, -1):
            signs = nt.map(dict(common, unclear=unclear))
            if signs.isna().any():
                raise ValueError("Unmapped transmitter")
            weights = np.asarray(counts, np.float64) * np.asarray(signs, np.float64)[cols] * .275
            for condition, chosen in (("baseline", []), ("sweet_LB3c", sweet),
                                      ("bitter_LB1a_d", bitter), ("sweet_plus_bitter", sweet + bitter)):
                handle = lib.ff_cuda64_create(n, len(cols), rows.ctypes.data, cols.ctypes.data,
                                              weights.ctypes.data, sense.ctypes.data,
                                              params64(.1, -52, -52, -45, 20, 5, 22, 18), cap)
                if not handle:
                    raise RuntimeError(lib.ff_cuda64_probe_error().decode())
                events = {str(body): [] for bodies in TARGET_IDS.values() for body in bodies}
                vtraces = {str(body): [] for bodies in TARGET_IDS.values() for body in bodies}
                mn9_events = {str(body): [] for body in (10331, 16949)}
                input_events = 0
                try:
                    for start in range(0, 1000, cap):
                        drive.fill(0)
                        for tick in range(start, start + cap):
                            if tick % 100 == 0:
                                drive[tick - start, chosen] = 68.75
                        if lib.ff_cuda64_advance(handle, cap, drive.ctypes.data,
                                                 voltage.ctypes.data, synapse.ctypes.data,
                                                 spikes.ctypes.data):
                            raise RuntimeError(lib.ff_cuda64_probe_error().decode())
                        input_events += int(spikes[:, chosen].sum())
                        for body in events:
                            ix = by_id[int(body)]
                            events[body].extend(int(start + tick) for tick in np.flatnonzero(spikes[:, ix]))
                            vtraces[body].extend(float(value) for value in voltage[:, ix])
                        for body in mn9_events:
                            ix = by_id[int(body)]
                            mn9_events[body].extend(int(start + tick) for tick in np.flatnonzero(spikes[:, ix]))
                finally:
                    lib.ff_cuda64_destroy(handle)
                results.append({"unclear_sign": unclear, "condition": condition,
                                "input_spikes": input_events, "target_spike_ticks": events,
                                "target_voltage_mean_mv": {k: float(np.mean(v)) for k, v in vtraces.items()},
                                "target_voltage_min_mv": {k: min(v) for k, v in vtraces.items()},
                                "mn9_spike_ticks": mn9_events})
                print(unclear, condition, {name: sum(len(events[str(b)]) for b in bodies)
                                          for name, bodies in TARGET_IDS.items()}, flush=True)
    finally:
        directory.close()
    previous = json.loads((ROOT / "reports/tastekin2026_malecns_mn9_probe.json").read_text())
    for result in results:
        expected = next(item for item in previous["results"]
                        if item["unclear_sign"] == result["unclear_sign"] and item["condition"] == result["condition"])
        if result["mn9_spike_ticks"] != expected["mn9_spike_ticks"] or result["input_spikes"] != expected["input_spikes"]:
            raise ValueError("Untuned repeat disagrees with original trial")
    report = {"scope": "Untuned full MaleCNS circuit probe against Shiu 2022 Roundup and G2N-1 qualitative intervention; no calcium observation model or preparation-matched receptor input",
              "reference": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9292995/",
              "graph_manifest_sha256": sha(G / "manifest.json"),
              "crosswalk_sha256": sha(ROOT / "reports/tastekin2026_malecns_crosswalk.json"),
              "dll_sha256": sha(dll), "target_body_ids": TARGET_IDS,
              "results": results, "biological_validation_passed": False}
    OUT.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
