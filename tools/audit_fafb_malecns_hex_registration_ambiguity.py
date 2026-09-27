"""Quantify ambiguity of shape-only FAFB/MaleCNS hex-grid registration."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build/eye-python"))
import rdata

SOURCE = ROOT / "data/reference/eyemap_2025/data/eyemap.RData"
MALE_COLUMNS = ROOT / "data/derived/malecns_optic_columns/columns.csv"
FAFB_RAYS = ROOT / "data/derived/optical_reference/fafb_hex_rays.csv"
OUT = ROOT / "reports/fafb_malecns_hex_registration_ambiguity.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source_lock = json.loads((ROOT / "reports/eyemap_reference_sources.json").read_text(encoding="utf-8"))
    source_entry = next(x for x in source_lock["files"] if x["path"] == "data/eyemap.RData")
    assert SOURCE.stat().st_size == source_entry["bytes"] and sha(SOURCE) == source_entry["sha256"]
    column_report = json.loads((ROOT / "reports/optic_column_index.json").read_text(encoding="utf-8"))
    assert sha(MALE_COLUMNS) == column_report["files"]["columns.csv"]
    rays_report = json.loads((ROOT / "reports/fafb_hex_ray_export.json").read_text(encoding="utf-8"))
    assert sha(FAFB_RAYS) == rays_report["output_csv_sha256"]
    lens = np.asarray(rdata.read_rda(SOURCE)["lens_ixy"])
    assert lens.shape == (852, 3) and np.isfinite(lens).all()
    assert np.equal(lens, np.floor(lens)).all()
    lens = lens[:, 1:].astype(np.int64)
    assert len(set(map(tuple, lens))) == 852
    male = (pd.read_csv(MALE_COLUMNS).query("side == 'R'")[["hex1", "hex2"]]
            .to_numpy(dtype=np.int64))
    assert len(male) == len(set(map(tuple, male))) == 892
    male_set = set(map(tuple, male))
    rotation = np.array([[0, -1], [1, 1]], dtype=np.int64)
    reflection = np.array([[0, 1], [1, 0]], dtype=np.int64)
    power = np.eye(2, dtype=np.int64)
    candidates = []
    orientation_best = []
    for turn in range(6):
        for reflected, transform in ((False, power), (True, reflection @ power)):
            transformed = lens @ transform.T
            delta = male[:, None, :] - transformed[None, :, :]
            dx, dy = delta[:, :, 0].ravel(), delta[:, :, 1].ravel()
            assert (np.abs(dx) <= 100).all() and (np.abs(dy) <= 100).all()
            counts = np.bincount((dx + 100) * 201 + (dy + 100), minlength=201 * 201)
            top = np.argsort(counts)[-3:][::-1]
            for rank, index in enumerate(top):
                candidates.append({"rotation_sixth_turns": turn,
                                   "reflected": reflected,
                                   "matrix": transform.tolist(),
                                   "shift_hex1": int(index // 201 - 100),
                                   "shift_hex2": int(index % 201 - 100),
                                   "overlapping_lenses": int(counts[index]),
                                   "orientation_rank": rank + 1})
            orientation_best.append(candidates[-3])
        power = rotation @ power
    candidates.sort(key=lambda x: (-x["overlapping_lenses"], x["reflected"],
                                   x["rotation_sixth_turns"], x["shift_hex1"], x["shift_hex2"]))
    first, second = candidates[:2]
    assert first["overlapping_lenses"] > second["overlapping_lenses"]
    measured = pd.read_csv(FAFB_RAYS)
    ray_points = measured[["fafb_hex_x", "fafb_hex_y"]].to_numpy(dtype=np.int64)
    ray_vectors = measured[["ray_forward", "ray_left", "ray_up"]].to_numpy(dtype=float)
    assert np.max(np.abs(np.linalg.norm(ray_vectors, axis=1) - 1)) < 1e-12
    def ray_map(candidate):
        matrix = np.asarray(candidate["matrix"], dtype=np.int64)
        shift = np.array([candidate["shift_hex1"], candidate["shift_hex2"]])
        mapped = ray_points @ matrix.T + shift
        return {tuple(k): v for k, v in zip(mapped, ray_vectors) if tuple(k) in male_set}
    left, right = ray_map(first), ray_map(second)
    shared = sorted(set(left) & set(right))
    angles = np.degrees(np.arccos(np.clip(
        np.array([np.dot(left[key], right[key]) for key in shared]), -1, 1)))
    assert len(shared) > 0
    report = {
        "scope": "Shape-only diagnostic over hypothesized 12 axial-hex symmetries and all integer translations; no accepted cross-specimen registration",
        "source_eyemap_sha256": sha(SOURCE),
        "male_columns_sha256": sha(MALE_COLUMNS),
        "fafb_hex_rays_sha256": sha(FAFB_RAYS),
        "male_right_columns": len(male),
        "fafb_right_lenses": len(lens),
        "orientation_best_candidates": sorted(orientation_best,
                                              key=lambda x: -x["overlapping_lenses"]),
        "top_candidates": candidates[:12],
        "top_two_measured_rays_on_male_grid": [len(left), len(right)],
        "top_two_shared_male_columns_with_measured_rays": len(shared),
        "top_two_ray_angle_disagreement_deg": {
            "min": float(np.min(angles)), "median": float(np.median(angles)),
            "p90": float(np.quantile(angles, 0.9)), "max": float(np.max(angles))},
        "interpretation": "Large grid overlap under several nearby transforms does not identify homologous cells. The top two shape candidates differ by roughly one column and yield distinct optical rays on the same MaleCNS columns. Landmarks and held-out optical/anatomical validation are required.",
        "registration_accepted": False,
        "male_cns_neuron_ray_assignments": 0,
        "visual_input_enabled": False,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("top_candidates",
       "top_two_shared_male_columns_with_measured_rays", "top_two_ray_angle_disagreement_deg")}, indent=2)[:2200])


if __name__ == "__main__":
    main()

