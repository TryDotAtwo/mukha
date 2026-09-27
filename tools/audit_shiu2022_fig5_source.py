"""Pin the published raw Figure 5 fluorescence time series and protocol scale."""
import hashlib
import json
import statistics
from pathlib import Path

import openpyxl
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/reference/shiu2022/elife-79887-fig5-data1-v3.xlsx"
EXPECTED_SHA256 = "bf84dd582638fb5fa2520566b9949c3c66ba5c90ee126d5ba74c15018dc9758d"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if sha(SOURCE) != EXPECTED_SHA256:
        raise ValueError("Source workbook hash mismatch")
    book = openpyxl.load_workbook(SOURCE, read_only=True, data_only=True)
    sheets = []
    for sheet in book:
        data = list(sheet.values)
        title = str(data[0][0])
        if "G2N-1" in title:
            cell_type = "G2N-1"
        elif "Roundup" in title:
            cell_type = "Roundup"
        else:
            raise ValueError("Unexpected Figure 5 sheet")
        headers = data[1]
        frames = [r for r in data[2:] if isinstance(r[0], (int, float))]
        light = [int(r[0]) for r in frames if r[2] == 1]
        if light != list(range(14, 18)) + list(range(32, 36)) + list(range(50, 54)):
            raise ValueError("Unexpected optogenetic light schedule")
        groups = {}
        for condition, marker in (("sweet", "_Gr5a_Fly"),
                                  ("sweet_plus_bitter", "_Gr5a-Gr66a_Fly"),
                                  ("bitter", "Gr66a_Fly")):
            columns = [i for i, h in enumerate(headers) if isinstance(h, str) and marker in h]
            if condition == "bitter":
                columns += [i for i, h in enumerate(headers) if isinstance(h, str) and "-Gr66a_Fly" in h]
                columns = [i for i in columns if "Gr5a-" not in str(headers[i])]
            columns = sorted(set(columns))
            per_fly = []
            for col in columns:
                light_values = [float(r[col]) for r in frames if r[2] == 1 and isinstance(r[col], (int, float))]
                pre_values = [float(r[col]) for r in frames if r[0] in (10, 11, 12, 13) and isinstance(r[col], (int, float))]
                if len(light_values) != 12 or len(pre_values) != 4:
                    raise ValueError("Incomplete fluorescence series")
                auc_values = [float(r[col]) for r in frames if r[0] in (15, 16, 17, 18)
                              and isinstance(r[col], (int, float))]
                if len(auc_values) != 4:
                    raise ValueError("Incomplete published AUC window")
                per_fly.append({"column": headers[col],
                                "light_on_mean_delta_f_over_f": statistics.mean(light_values),
                                "pre_first_pulse_mean_delta_f_over_f": statistics.mean(pre_values),
                                "difference": statistics.mean(light_values) - statistics.mean(pre_values),
                                "first_pulse_auc_frame_units": float(np.trapezoid(auc_values, dx=1.0)),
                                "first_pulse_auc_seconds": float(np.trapezoid(auc_values, dx=.67))})
            groups[condition] = {"fly_count": len(per_fly), "per_fly": per_fly,
                                 "median_light_on_delta_f_over_f": statistics.median(x["light_on_mean_delta_f_over_f"] for x in per_fly),
                                 "median_light_minus_pre": statistics.median(x["difference"] for x in per_fly),
                                 "median_first_pulse_auc_frame_units": statistics.median(x["first_pulse_auc_frame_units"] for x in per_fly),
                                 "median_first_pulse_auc_seconds": statistics.median(x["first_pulse_auc_seconds"] for x in per_fly)}
        sheets.append({"sheet": sheet.title, "workbook_title": title,
                       "cell_type": cell_type,
                       "light_on_frame_indices": light,
                       "light_on_time_s": [float(r[1]) for r in frames if r[2] == 1],
                       "frame_period_s": float(frames[1][1] - frames[0][1]),
                       "groups": groups})
    report = {"source_url": "https://cdn.elifesciences.org/articles/79887/elife-79887-fig5-data1-v3.xlsx",
              "source_sha256": sha(SOURCE),
              "article": "https://doi.org/10.7554/eLife.79887",
              "metric_note": "Author methods specify NumPy trapz of frames 15-18 for optogenetic AUC; both frame-unit and 0.67-second-spacing medians are reported. Earlier all-light-frame mean remains exploratory, not the article statistic. No Quade test reproduced.",
              "condition_note": "Workbook titles say fed animals; article Figure 5 caption says food-deprived flies. This discrepancy is unresolved. Methods specify female progeny and three two-second 660-nm pulses at 10-second intervals.",
              "sheets": sheets}
    dest = ROOT / "reports/shiu2022_fig5_source_audit.json"
    dest.write_text(json.dumps(report, indent=2) + "\n")
    for item in sheets:
        print(item["cell_type"], {k: (v["fly_count"], v["median_first_pulse_auc_frame_units"])
                                  for k, v in item["groups"].items()})


if __name__ == "__main__":
    main()
