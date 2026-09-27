"""Reconstruct Handler 2019 Fig. 5E/F from pinned preparation-level data.

This is an internal source-data audit and an exploratory population-level
constraint, not a fit or validation of a MaleCNS contact plasticity rule.
"""
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "data/reference/handler2019/Handler2019_Fig2Fig5_Data.xlsx"
TIMING = ROOT / "reports/handler2019_fig2_timing_data.json"
OUT = ROOT / "reports/handler2019_fig5_second_messenger.json"
SHA256 = "4db9b76cd0c41dc014c8d00a9e359bbd4165a7984095cc35d1932f9ee7f501dc"
ISI = [-6.0, -1.2, -0.6, 0.0, 0.5, 6.0]


def near(a, b, tol=1e-8):
    assert math.isclose(float(a), float(b), rel_tol=0, abs_tol=tol), (a, b)


def raw_matrix(sheet, starts, n):
    return np.asarray([[float(sheet.cell(2, col + prep).value) for prep in range(n)]
                       for col in starts], dtype=np.float64)


def normalise_per_preparation(raw):
    low = raw.min(axis=0)
    span = raw.max(axis=0) - low
    assert np.all(span > 0)
    return (raw - low) / span


def main():
    assert hashlib.sha256(BOOK.read_bytes()).hexdigest() == SHA256
    workbook = openpyxl.load_workbook(BOOK, read_only=True, data_only=True)
    camp = raw_matrix(workbook["Fig5D_cAMP timecourse"], [3, 11, 19, 27, 35, 43], 6)
    er = raw_matrix(workbook["Fig5D_ERGCaMP timecourse"], [3, 12, 21, 30, 39, 48], 7)
    camp_norm = normalise_per_preparation(camp)
    neg_er_norm = normalise_per_preparation(-er)
    summary = workbook["Fig5E_(-)ERGCaMPnorm - cAMPnorm"]
    conditions = []
    for index, isi in enumerate(ISI):
        for row in (3 + index, 12 + index, 21 + index, 39 + index):
            assert float(summary.cell(row, 1).value) == isi
        for prep in range(6):
            near(camp[index, prep], summary.cell(3 + index, 2 + prep).value)
            near(camp_norm[index, prep], summary.cell(12 + index, 2 + prep).value)
        for prep in range(7):
            near(er[index, prep], summary.cell(21 + index, 2 + prep).value)
            near(neg_er_norm[index, prep], summary.cell(39 + index, 2 + prep).value)
        mean_camp = float(camp_norm[index].mean())
        mean_er = float(neg_er_norm[index].mean())
        near(mean_camp, summary.cell(12 + index, 9).value)
        near(mean_er, summary.cell(39 + index, 10).value)
        near(mean_er - mean_camp, summary.cell(39 + index, 14).value)
        conditions.append({
            "isi_s": isi,
            "raw_camp_per_preparation": camp[index].tolist(),
            "raw_er_calcium_per_preparation": er[index].tolist(),
            "normalized_camp_mean": mean_camp,
            "normalized_negative_er_mean": mean_er,
            "negative_er_minus_camp": mean_er - mean_camp,
        })
    timing = json.loads(TIMING.read_text(encoding="utf-8"))
    assert timing["workbook_sha256"] == SHA256
    assert [item["isi_s"] for item in timing["conditions"]] == ISI
    x = np.asarray([row["negative_er_minus_camp"] for row in conditions])
    y = np.asarray([row["mean_delta"] for row in timing["conditions"]])
    correlation = float(np.corrcoef(x, y)[0, 1])
    slope, intercept = np.polyfit(x, y, 1)
    report = {
        "source_workbook_sha256": SHA256,
        "source_repository_commit": timing["source_repository_commit"],
        "observable": "Fig. 5E/F second-messenger responses in KC axons, each preparation normalized to its own six-ISI min/max; compared with Fig. 2 gamma4 MBON post-minus-pre means.",
        "reconstruction": "6 cAMP and 7 ER calcium preparation values per ISI, per-preparation normalization, displayed means and Fig. 5F contrast match the workbook within 1e-8.",
        "conditions": conditions,
        "exploratory_six_isi_association": {
            "pearson_r": correlation,
            "ordinary_least_squares_slope": float(slope),
            "ordinary_least_squares_intercept": float(intercept),
            "same_six_isi_as_source_figure": True,
            "independent_validation": False,
        },
        "scope_limit": "Population-level imaging from separate cAMP, ER calcium and MBON preparations; it does not locate signals at individual MaleCNS contacts or establish receptor kinetics.",
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("ISI(s) normalized(-ER)-normalized(cAMP) MBON_delta")
    for row, mb in zip(conditions, y):
        print(f"{row['isi_s']:5g} {row['negative_er_minus_camp']:+.6f} {mb:+.6f}")
    print(f"exploratory Pearson r={correlation:.6f}; no independent validation")


if __name__ == "__main__":
    main()
