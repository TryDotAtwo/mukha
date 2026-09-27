"""Check Handler Figure 5D trace-to-summary measurement windows.

The paper defines cAMP as a 4 s post-DAN mean and ER lumen calcium as a 1 s
post-KC mean. Workbook labels give the plotted time windows in seconds.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "data/reference/handler2019/Handler2019_Fig2Fig5_Data.xlsx"
OUT = ROOT / "reports/handler2019_observation_windows.json"
SHA = "4db9b76cd0c41dc014c8d00a9e359bbd4165a7984095cc35d1932f9ee7f501dc"
ISI = [-6.0, -1.2, -0.6, 0.0, 0.5, 6.0]


def sheet_data(sheet):
    rows = list(sheet.values)
    return rows[1], np.asarray([[float(x) if isinstance(x, (int, float)) else np.nan
                                 for x in row] for row in rows[3:]], dtype=np.float64)


def check(name, summary, trace, starts, n, windows):
    results = []
    for isi, col, (lo, hi) in zip(ISI, starts, windows):
        t = trace[:, col - 2]
        y = trace[:, col - 1:col - 1 + n]
        valid = np.isfinite(t) & np.all(np.isfinite(y), axis=1)
        t, y = t[valid], y[valid]
        assert len(t) > 10 and np.allclose(np.diff(t), 0.1, atol=1e-9)
        target = np.asarray(summary[col - 1:col - 1 + n], dtype=np.float64)
        alternatives = {}
        for bound, mask in (
            ("half_open", (t >= lo - 1e-9) & (t < hi - 1e-9)),
            ("closed", (t >= lo - 1e-9) & (t <= hi + 1e-9)),
        ):
            observed = y[mask].mean(axis=0)
            alternatives[bound] = {
                "frames": int(mask.sum()),
                "maximum_absolute_error": float(np.max(np.abs(observed - target))),
            }
        assert alternatives["closed"]["maximum_absolute_error"] < 1e-12
        results.append({"isi_s": isi, "window_s": [lo, hi],
                        "n_preparations": n, "comparisons": alternatives})
    return {"modality": name, "conditions": results}


def main():
    assert hashlib.sha256(BOOK.read_bytes()).hexdigest() == SHA
    workbook = openpyxl.load_workbook(BOOK, read_only=True, data_only=True)
    cs, ct = sheet_data(workbook["Fig5D_cAMP timecourse"])
    es, et = sheet_data(workbook["Fig5D_ERGCaMP timecourse"])
    camp_windows = [(4, 8), (8.8, 12.8), (9.4, 13.4), (10, 14), (10.5, 14.5), (16, 20)]
    er_windows = [(6, 7)] * 6
    modalities = [check("cAMP_FRET", cs, ct, [3, 11, 19, 27, 35, 43], 6, camp_windows),
                  check("ER_lumen_GCaMP", es, et, [3, 12, 21, 30, 39, 48], 7, er_windows)]
    report = {
        "workbook_sha256": SHA,
        "primary_methods": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9012144/",
        "question": "Do the labeled 4 s post-DAN and 1 s post-KC windows reproduce the source summary values from the sampled traces?",
        "sampling": "0.1 s sample interval; source summary includes both endpoints (41 cAMP samples and 11 ER samples). The traces are already baseline-normalized reporter values.",
        "time_axis_caution": "The two workbook sheets use different plotted time origins. The labeled modality-specific windows are verified here; a shared event clock is not inferred from their row timestamps.",
        "modalities": modalities,
        "scope_limit": "Checks published reporter traces, not underlying molecular concentrations, source stimuli delivered to MaleCNS, or a local plasticity rule.",
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for item in modalities:
        print(item["modality"])
        for condition in item["conditions"]:
            print(condition["isi_s"], condition["comparisons"])


if __name__ == "__main__":
    main()
