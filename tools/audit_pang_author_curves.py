"""Audit pinned Pang et al. processed L1/L2 mean response curves.

This describes the published processed curves. It does not calibrate a CNS model.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/reference/pang_l1l2_author_curves"
manifest = json.loads((SOURCE / "source_manifest.json").read_text())
rows = []
for item in manifest["items"]:
    path = SOURCE / item["name"]
    assert path.stat().st_size == item["bytes"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
notebook = json.loads((SOURCE / "L1_2responses_to_flashes.ipynb").read_text())
notebook_code = "\n".join("".join(c.get("source", [])) for c in notebook["cells"])
assert "mean_res1=mean_res[1]" in notebook_code
assert "mean_res2=mean_res[0]" in notebook_code
assert "sti_y1[2:5]=1" in notebook_code
assert "sti_y2[2:5]=-1" in notebook_code
assert "label='Model',c='r'" in notebook_code
assert "label='Model',c='blue'" in notebook_code
for item in manifest["items"]:
    if not item["name"].endswith(".mat"):
        continue
    path = SOURCE / item["name"]
    assert path.stat().st_size == item["bytes"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
    data = loadmat(path)
    fields = sorted(k for k in data if not k.startswith("__"))
    expected_fields = ["indivResp", "meanResp", "t"] if "_CDM_" in item["name"] else ["meanResp", "t"]
    assert fields == expected_fields, (path, fields)
    time = np.asarray(data["t"], dtype=float).ravel()
    response = np.asarray(data["meanResp"], dtype=float)
    assert response.shape == (2, 63) and time.shape == (63,)
    assert np.isfinite(response).all() and np.isfinite(time).all()
    assert np.allclose(np.diff(time), 1 / 120, atol=1e-10)
    # The author notebook maps row 0 to its red curve and row 1 to blue;
    # its graph negates the raw fluorescence. In the paper blue denotes light
    # and red dark. Hence raw-positive row 1 is the light response.
    for index, label in [(0, "dark_raw_negative"), (1, "light_raw_positive")]:
        preflash_mean = float(response[index, :2].mean())
        baseline = 0.0  # paper's phase boundary is raw deltaF/F = 0
        y = response[index]
        onset_index = 2  # author notebook creates stimulus at indices 2:5
        first = y[onset_index:31]
        peak_offset = int(np.argmin(first) if index == 0 else np.argmax(first))
        peak_index = onset_index + peak_offset
        # Published Figure 1 metrics integrate the first phase to its zero
        # crossing, then the opposite phase to 250 ms after flash onset.
        end_index = int(np.searchsorted(time, time[onset_index] + 0.25, side="right") - 1)
        polarity = -1 if index == 0 else 1
        crossing = next((j for j in range(peak_index + 1, end_index + 1)
                         if polarity * y[j] <= 0), None)
        if crossing is None:
            phase1_area = float(np.trapezoid(y[onset_index:end_index + 1],
                                             time[onset_index:end_index + 1]))
            phase2_area = None
            area_ratio = None
        else:
            # Linear zero interpolation prevents a whole-frame area bias.
            t0, t1 = time[crossing - 1], time[crossing]
            y0, y1 = y[crossing - 1], y[crossing]
            tcross = float(t0 - y0 * (t1 - t0) / (y1 - y0))
            left_t = np.r_[time[onset_index:crossing], tcross]
            left_y = np.r_[y[onset_index:crossing], 0.0]
            right_t = np.r_[tcross, time[crossing:end_index + 1]]
            right_y = np.r_[0.0, y[crossing:end_index + 1]]
            phase1_area = float(np.trapezoid(left_y, left_t))
            phase2_area = float(np.trapezoid(right_y, right_t))
            area_ratio = float(abs(phase2_area / phase1_area)) if phase1_area else None
        # Only two pre-flash samples exist. A detected zero crossing is
        # unstable if it appears under one pre-flash sample but not another.
        baseline_crossings = {}
        for base_name, base in (("raw_zero", 0.0),
                                ("first_sample", float(response[index, 0])),
                                ("second_sample", float(response[index, 1])),
                                ("mean_first_two", preflash_mean)):
            shifted = response[index] - base
            baseline_crossings[base_name] = any(
                polarity * shifted[j] <= 0
                for j in range(peak_index + 1, end_index + 1)
            )
        robust_crossing = (len(set(baseline_crossings.values())) == 1)
        rows.append({
            "file": item["name"], "row": index, "label": label,
            "baseline_crossings": baseline_crossings,
            "zero_crossing_robust_to_preflash_baseline": robust_crossing,
            "samples": 63, "sampling_hz": 120,
            "nominal_stimulus_onset_s": float(time[onset_index]),
            "response_at_nominal_onset_deltaF_over_F": float(y[onset_index]),
            "onset_sample_to_first_peak_fraction": float(abs(y[onset_index] / y[peak_index])) if y[peak_index] else None,
            "peak_latency_is_physiological": False,
            "first_peak_s_from_trace_start": float(time[peak_index]),
            "first_peak_ms_from_nominal_onset": float((time[peak_index] - time[onset_index]) * 1000),
            "first_peak_deltaF_over_F": float(y[peak_index]),
            "baseline_first_two_samples": preflash_mean,
            "metric_baseline_deltaF_over_F": 0.0,
            "phase1_area_deltaF_over_F_seconds": phase1_area,
            "phase2_signed_area_deltaF_over_F_seconds": phase2_area,
            "phase2_to_phase1_absolute_area_ratio": area_ratio,
            "zero_crossing_s_from_trace_start": None if crossing is None else tcross,
        })
light_signature = {}
for cell_type in ("L1", "L2"):
    light_signature[cell_type] = {}
    for level in ("lowLum", "highLum"):
        match = [r for r in rows if r["file"] == f"{cell_type}_{level}.mat"
                 and r["label"] == "light_raw_positive"]
        assert len(match) == 1
        r = match[0]
        light_signature[cell_type][level] = {
            "first_peak_ms_from_nominal_onset": r["first_peak_ms_from_nominal_onset"],
            "onset_sample_to_first_peak_fraction": r["onset_sample_to_first_peak_fraction"],
            "peak_latency_is_physiological": False,
            "opposite_phase_detected_by_250ms_raw_zero": r["zero_crossing_s_from_trace_start"] is not None,
            "zero_crossing_robust_to_preflash_baseline": r["zero_crossing_robust_to_preflash_baseline"],
            "baseline_crossings": r["baseline_crossings"],
            "phase2_to_phase1_absolute_area_ratio_raw_zero": r["phase2_to_phase1_absolute_area_ratio"],
        }
out = {
    "source_commit": manifest["commit"],
    "light_signature": light_signature,
    "notebook": "computational-model/L1_2responses_to_flashes.ipynb",
    "notebook_stimulus_indices": "2:5",
    "observation": "processed mean raw deltaF/F; author notebook negates it for display, not direct membrane voltage",
    "phase_metric_baseline": "raw deltaF/F zero as in paper; alternative preflash baselines checked for robustness",
    "phase1_start": "notebook nominal sampled stimulus onset; paper describes response onset, so these areas are approximate and not a byte-exact reproduction of its plotted statistics",
    "latency_caveat": "notebook indices 2:5 are model input placement, not measured physical flash onset; the response is already substantial at index 2, so peak minus index-2 time is not physiological latency",
    "control_mat_fields": ["meanResp", "t"],
    "cdm_mat_fields": ["indivResp", "meanResp", "t"],
    "missing_timing_fields": ["physical_flash_onset", "photodiode_trace", "frame_to_projector_alignment"],
    "row_identity": "row 0 dark/red and row 1 light/blue from pinned notebook plus paper color legend; exact cohort still unidentified",
    "model_validation": "not scored: photon delivery and voltage-indicator observation are uncalibrated",
    "curves": rows,
}
path = ROOT / "reports/pang_author_curve_audit.json"
path.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
