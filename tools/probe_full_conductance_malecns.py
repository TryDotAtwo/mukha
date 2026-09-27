"""Full MaleCNS numerical conductance sweep with explicitly provisional parameters."""
import ctypes as ct
import gc
import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.feather as feather

from check_cuda_conductance import Params

ROOT = Path(__file__).resolve().parents[1]
G = ROOT / "data/derived/malecns_v1_candidates"
DLL = ROOT / "build/fly_cuda_conductance.dll"
OUT_PREFIX = "malecns_conductance_candidate_probe_reset"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reversal-inh", type=float, choices=(-70., -48.), required=True)
    parser.add_argument("--unclear-sign", type=int, choices=(-1, 1), required=True)
    parser.add_argument("--input-condition", choices=("sweet", "combined"), default="combined")
    parser.add_argument("--check-reset", action="store_true")
    parser.add_argument("--cut-scapula-roundup", action="store_true")
    args = parser.parse_args()
    condition_part = "_sweet" if args.input_condition == "sweet" else ""
    cut_part = "_cut_scapula_roundup" if args.cut_scapula_roundup else ""
    output = ROOT / f"reports/{OUT_PREFIX}{condition_part}{cut_part}_e{int(args.reversal_inh)}_u{args.unclear_sign}.json"
    if output.exists():
        raise FileExistsError(output)
    manifest = json.loads((G / "manifest.json").read_text())
    for name in ("body_ids.npy", "indptr.npy", "indices.npy", "synapse_counts.npy", "neurotransmitters.feather"):
        if sha(G / name) != manifest["files"][name]["sha256"]:
            raise ValueError("Graph source mismatch: " + name)
    ids = np.load(G / "body_ids.npy", mmap_mode="r")
    row = np.load(G / "indptr.npy", mmap_mode="r")
    col = np.load(G / "indices.npy", mmap_mode="r")
    contacts = np.load(G / "synapse_counts.npy", mmap_mode="r")
    by_id = {int(body): i for i, body in enumerate(ids)}
    cross = json.loads((ROOT / "reports/tastekin2026_malecns_crosswalk.json").read_text())
    sweet_inputs = [by_id[x] for x in cross["populations"]["sweet_candidate_LB3c"]["body_ids"]]
    bitter_inputs = [by_id[x] for x in cross["populations"]["bitter_candidate_LB1a_d"]["body_ids"]]
    inputs = sweet_inputs + bitter_inputs if args.input_condition == "combined" else sweet_inputs
    input_positions = sorted(inputs)
    non_input_slices = []
    previous = 0
    for position in input_positions:
        if previous < position:
            non_input_slices.append(slice(previous, position))
        previous = position + 1
    if previous < len(ids):
        non_input_slices.append(slice(previous, len(ids)))
    targets = {name: [by_id[x] for x in bodies] for name, bodies in {
        "Roundup": [26764, 523040], "G2N-1": [31018, 89638],
        "Scapula": [11896, 12811, 12900], "MN9": [10331, 16949]}.items()}
    chemistry = feather.read_table(G / "neurotransmitters.feather", columns=["body", "consensus_nt"]).to_pandas()
    nt = chemistry.set_index("body").reindex(ids).consensus_nt.fillna("missing_annotation")
    del chemistry
    common = {"acetylcholine": 1, "gaba": -1, "glutamate": -1, "histamine": -1,
              "dopamine": 0, "octopamine": 0, "serotonin": 0, "missing_annotation": 0}
    directory = os.add_dll_directory(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\bin")
    lib = ct.CDLL(str(DLL))
    lib.fc_error.restype = ct.c_char_p
    lib.fc_create.argtypes = [ct.c_uint32, ct.c_uint64] + [ct.c_void_p]*5 + [Params, ct.c_uint32]
    lib.fc_create.restype = ct.c_void_p
    lib.fc_destroy.argtypes = [ct.c_void_p]
    lib.fc_reset.argtypes = [ct.c_void_p]
    lib.fc_advance.argtypes = [ct.c_void_p, ct.c_uint32] + [ct.c_void_p]*5
    n = len(ids)
    cap = 20
    sense = np.zeros(n, np.uint8)
    drive = np.zeros((cap, n), np.float64)
    v = np.empty_like(drive)
    ge = np.empty_like(drive)
    gi = np.empty_like(drive)
    spikes = np.empty((cap, n), np.uint8)
    results = []
    try:
        for reversal in (args.reversal_inh,):
            for unclear in (args.unclear_sign,):
                sign = nt.map(dict(common, unclear=unclear))
                if sign.isna().any():
                    raise ValueError("Unknown NT")
                signed = np.asarray(sign, np.int8)[col]
                # Illustrative conductance: 0.005 per contact is close to
                # 0.275 mV divided by the 52-mV rest-to-0 driving force.
                base = np.asarray(contacts, np.float64)*.005
                w_exc = np.where(signed == 1, base, 0.)
                w_inh = np.where(signed == -1, base, 0.)
                del base, signed
                cut_edges = 0
                cut_contacts = 0
                if args.cut_scapula_roundup:
                    source_indices = {by_id[x] for x in (11896, 12811, 12900)}
                    for body in (26764, 523040):
                        target = by_id[body]
                        for edge in range(int(row[target]), int(row[target + 1])):
                            if int(col[edge]) in source_indices:
                                cut_edges += 1
                                cut_contacts += int(contacts[edge])
                                w_exc[edge] = 0.
                                w_inh[edge] = 0.
                    if (cut_edges, cut_contacts) != (3, 251):
                        raise ValueError(f"Unexpected Scapula→Roundup motif: {cut_edges}, {cut_contacts}")
                handle = lib.fc_create(n, len(col), row.ctypes.data, col.ctypes.data,
                                       w_exc.ctypes.data, w_inh.ctypes.data, sense.ctypes.data,
                                       Params(.1, -52, -52, -45, 20, 5, 0, reversal, 22, 18), cap)
                if not handle:
                    raise RuntimeError(lib.fc_error().decode())
                total = 0
                input_spikes = 0
                sweet_spikes = 0
                bitter_spikes = 0
                min_other = float("inf")
                max_other = -float("inf")
                events = {str(int(ids[i])): [] for group in targets.values() for i in group}
                try:
                    for start in range(0, 1000, cap):
                        drive.fill(0)
                        for tick in range(start, start+cap):
                            if tick % 100 == 0:
                                drive[tick-start, inputs] = 68.75
                        if lib.fc_advance(handle, cap, drive.ctypes.data, v.ctypes.data,
                                          ge.ctypes.data, gi.ctypes.data, spikes.ctypes.data):
                            raise RuntimeError(lib.fc_error().decode())
                        if not np.isfinite(v).all() or not np.isfinite(ge).all() or not np.isfinite(gi).all():
                            raise ValueError("Nonfinite native conductance state")
                        for view in non_input_slices:
                            min_other = min(min_other, float(np.min(v[:, view])))
                            max_other = max(max_other, float(np.max(v[:, view])))
                        total += int(spikes.sum())
                        input_spikes += int(spikes[:, inputs].sum())
                        sweet_spikes += int(spikes[:, sweet_inputs].sum())
                        bitter_spikes += int(spikes[:, bitter_inputs].sum())
                        for body in events:
                            ix = by_id[int(body)]
                            events[body].extend(int(start+t) for t in np.flatnonzero(spikes[:, ix]))
                    if args.check_reset:
                        if lib.fc_reset(handle):
                            raise RuntimeError(lib.fc_error().decode())
                        repeat_total = 0
                        repeat_input = 0
                        repeat_events = {body: [] for body in events}
                        for start in range(0, 1000, cap):
                            drive.fill(0)
                            for tick in range(start, start+cap):
                                if tick % 100 == 0:
                                    drive[tick-start, inputs] = 68.75
                            if lib.fc_advance(handle, cap, drive.ctypes.data, v.ctypes.data,
                                              ge.ctypes.data, gi.ctypes.data, spikes.ctypes.data):
                                raise RuntimeError(lib.fc_error().decode())
                            repeat_total += int(spikes.sum())
                            repeat_input += int(spikes[:, inputs].sum())
                            for body in repeat_events:
                                ix = by_id[int(body)]
                                repeat_events[body].extend(int(start+t) for t in np.flatnonzero(spikes[:, ix]))
                        if (repeat_total != total or repeat_input != input_spikes or
                            repeat_events != events):
                            raise ValueError("Full-graph reset replay changed event counts or target event ticks")
                finally:
                    lib.fc_destroy(handle)
                if not -70.00000001 <= min_other <= max_other <= 0.00000001:
                    raise ValueError("Unforced voltage escaped equilibrium bounds")
                results.append({"reversal_inh_mv": reversal, "unclear_sign": unclear,
                                "input_condition": args.input_condition,
                                "cut_scapula_roundup": args.cut_scapula_roundup,
                                "cut_edge_count": cut_edges,
                                "cut_contact_sum": cut_contacts,
                                "all_spikes": total, "input_spikes": input_spikes,
                                "sweet_population_spikes": sweet_spikes,
                                "bitter_population_spikes": bitter_spikes,
                                "non_input_voltage_min_mv": min_other,
                                "non_input_voltage_max_mv": max_other,
                                "full_graph_reset_replay_exact": bool(args.check_reset),
                                "target_spike_ticks": events,
                                "group_spike_counts": {name: sum(len(events[str(int(ids[ix]))]) for ix in group)
                                                       for name, group in targets.items()}})
                print(reversal, unclear, total, results[-1]["group_spike_counts"], flush=True)
                del w_exc, w_inh, sign
                gc.collect()
    finally:
        directory.close()
    report = {"scope": "Full-graph numerical capability test; parameters are provisional, not assigned MaleCNS receptor physiology",
              "graph_manifest_sha256": sha(G / "manifest.json"),
              "crosswalk_sha256": sha(ROOT / "reports/tastekin2026_malecns_crosswalk.json"),
              "dll_sha256": sha(DLL),
              "temporary_edge_intervention": "Scapula→Roundup conductances zeroed in memory only" if args.cut_scapula_roundup else "none",
              "fixed_parameters": {"dt_ms": .1, "rest_mv": -52, "reversal_exc_mv": 0,
                                   "conductance_per_contact": .005,
                                   "direct_input_mv": 68.75, "input_period_ms": 10,
                                   "time_ms": 100},
              "limitations": ["No source-measured receptor or reversal map for all MaleCNS edges",
                              "Source -48 mV GABA reversal was measured in other adult Drosophila neurons, not Roundup",
                              "-70 mV is only a hypothetical sensitivity point",
                              "Uniform LIF dynamics and direct GRN drive remain unvalidated"],
              "results": results, "biological_validation_passed": False}
    output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
