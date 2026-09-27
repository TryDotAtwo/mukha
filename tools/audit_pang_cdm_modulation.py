"""Descriptive Pang control/CDM mean comparison; no fly-level inference."""
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/reference/pang_l1l2_author_curves"
manifest = json.loads((SOURCE / "source_manifest.json").read_text())
for item in manifest["items"]:
    path = SOURCE / item["name"]
    assert path.stat().st_size == item["bytes"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
audit = json.loads((ROOT / "reports/pang_author_curve_audit.json").read_text())
rows = {(r["file"], r["row"]): r for r in audit["curves"]}
comparisons = []
for cell in ("L1", "L2"):
    for level in ("lowLum", "highLum"):
        control_name = f"{cell}_{level}.mat"
        cdm_name = f"{cell}_CDM_{level}.mat"
        control = loadmat(SOURCE / control_name)
        cdm = loadmat(SOURCE / cdm_name)
        assert np.array_equal(control["t"], cdm["t"])
        indiv = cdm["indivResp"].ravel()
        assert len(indiv) == 2
        for row in (0, 1):
            assert indiv[row].shape[1] == 63
            assert np.allclose(indiv[row].mean(axis=0), cdm["meanResp"][row], atol=1e-15, rtol=0)
            cr = rows[(control_name, row)]
            dr = rows[(cdm_name, row)]
            a = cr["phase2_signed_area_deltaF_over_F_seconds"]
            b = dr["phase2_signed_area_deltaF_over_F_seconds"]
            comparisons.append({
                "cell": cell, "level": level,
                "flash": "dark" if row == 0 else "light",
                "cdm_cell_traces": int(indiv[row].shape[0]),
                "control_individual_traces_available": False,
                "control_first_peak_raw_deltaF_over_F": cr["first_peak_deltaF_over_F"],
                "cdm_first_peak_raw_deltaF_over_F": dr["first_peak_deltaF_over_F"],
                "control_phase2_signed_area_raw_deltaF_over_F_s": a,
                "cdm_phase2_signed_area_raw_deltaF_over_F_s": b,
                "cdm_to_control_abs_phase2_area": None if a in (None, 0) or b is None else abs(b / a),
                "control_phase2_to_phase1_abs_area_ratio": cr["phase2_to_phase1_absolute_area_ratio"],
                "cdm_phase2_to_phase1_abs_area_ratio": dr["phase2_to_phase1_absolute_area_ratio"],
                "control_baseline_crossing_robust": cr["zero_crossing_robust_to_preflash_baseline"],
                "cdm_baseline_crossing_robust": dr["zero_crossing_robust_to_preflash_baseline"],
            })
out = {
    "source_commit": manifest["commit"],
    "intervention": "chlordimeform (CDM), octopamine receptor agonist; not a direct feedback-path blockade",
    "scope": "descriptive control-versus-CDM processed mean curves from author repository",
    "inferential_limit": "CDM has cell traces but no fly IDs here; controls lack individual traces. No fly-level uncertainty, p-value or paired causal estimate.",
    "stimulus_limit": "highLum and lowLum files have matching names and 120-Hz time axes, but recording-specific intensity/filter/PWM are not pinned.",
    "phase_metric": "raw deltaF/F zero; approximate first-phase start at notebook nominal stimulus onset",
    "comparisons": comparisons,
}
path = ROOT / "reports/pang_cdm_modulation_audit.json"
path.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
