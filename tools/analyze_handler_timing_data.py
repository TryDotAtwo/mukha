"""Audit per-preparation Handler 2019 Figure 2D/2E timing measurements.

The pinned workbook was redistributed by Gkanias et al. in their published
IncentiveCircuit source repository. This script checks its plotted delta table
against paired pre/post rows before extracting a numerical validation fixture.
"""
import hashlib
import itertools
import json
import math
from pathlib import Path

import openpyxl
from scipy.stats import t

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "data/reference/handler2019/Handler2019_Fig2Fig5_Data.xlsx"
REPORT = ROOT / "reports/handler2019_fig2_timing_data.json"
EXPECTED_SHA256 = "4db9b76cd0c41dc014c8d00a9e359bbd4165a7984095cc35d1932f9ee7f501dc"
COMMIT = "1610c80072fe8bb59bd397e7a61f716393a509b9"
SOURCE_URL = ("https://raw.githubusercontent.com/InsectRobotics/IncentiveCircuit/"
              + COMMIT + "/src/incentive/data/handler2019/Handler2019_Fig2Fig5_Data.xlsx")


def group(sheet, start):
    values = []
    column = start
    # The -0.6 s post header is one blank column before its six values.
    if sheet.cell(3, column).value is None:
        column += 1
    while isinstance(sheet.cell(3, column).value, (int, float)):
        values.append(float(sheet.cell(3, column).value))
        column += 1
    return values


def main():
    digest = hashlib.sha256(BOOK.read_bytes()).hexdigest()
    assert digest == EXPECTED_SHA256, "reference workbook changed"
    workbook = openpyxl.load_workbook(BOOK, read_only=True, data_only=True)
    sheet = workbook["Fig2D-2E_gamma4MBON"]
    # Source columns are headed pre/post, with one column per preparation.
    starts = [(-6.0, 3, 9), (-1.2, 16, 22), (-0.6, 29, 35),
              (0.0, 43, 49), (0.5, 55, 61), (6.0, 68, 74)]
    results = []
    for row, (isi, pre_col, post_col) in enumerate(starts, 3):
        assert sheet.cell(2, pre_col).value == "pre"
        assert sheet.cell(2, post_col).value == "post"
        pre, post = group(sheet, pre_col), group(sheet, post_col)
        assert len(pre) == len(post) and len(pre) >= 5
        delta = [after - before for before, after in zip(pre, post)]
        assert float(sheet.cell(row, 80).value) == isi
        published_deltas = [sheet.cell(row, col).value for col in range(81, 87)]
        published_deltas = [float(value) for value in published_deltas if value is not None]
        assert len(delta) == len(published_deltas)
        assert all(math.isclose(a, b, abs_tol=1e-12) for a, b in zip(delta, published_deltas))
        mean = sum(delta) / len(delta)
        assert math.isclose(mean, float(sheet.cell(row, 87).value), abs_tol=1e-12)
        sem = (sum((x - mean) ** 2 for x in delta) / (len(delta) - 1)) ** 0.5 / len(delta) ** 0.5
        margin = float(t.ppf(0.975, len(delta) - 1)) * sem
        results.append({"isi_s": isi, "pre": pre, "post": post, "paired_delta": delta,
                        "n_preparations": len(delta), "mean_delta": mean, "sem_delta": sem,
                        "mean_delta_95pct_t_interval": [mean - margin, mean + margin]})
    assert [row["n_preparations"] for row in results] == [5, 5, 6, 5, 5, 5]
    far, near = results[1]["paired_delta"], results[2]["paired_delta"]
    observed_difference = sum(far) / len(far) - sum(near) / len(near)
    pooled = far + near
    extreme = 0
    total = 0
    for selected in itertools.combinations(range(len(pooled)), len(far)):
        a = [pooled[i] for i in selected]
        subset = set(selected)
        b = [pooled[i] for i in range(len(pooled)) if i not in subset]
        difference = sum(a) / len(a) - sum(b) / len(b)
        extreme += difference >= observed_difference - 1e-12
        total += 1
    report = {
        "primary_paper": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9012144/",
        "paper_doi": "10.1016/j.cell.2019.05.040",
        "workbook_source": SOURCE_URL, "workbook_sha256": digest,
        "source_repository_commit": COMMIT,
        "observable": "per-preparation change in peak KC-evoked gamma4 MBON GCaMP response, post minus pre",
        "time_convention": "ISI = DAN stimulus time minus KC stimulus time, seconds",
        "interval_note": "Two-sided Student-t interval on paired deltas; descriptive, no multiple-comparison correction.",
        "source_internal_check": "All paired deltas and displayed means reconstructed from workbook pre/post values within 1e-12.",
        "conditions": results,
        "exploratory_backward_monotonicity_check": {
            "simple_rule_prediction": "For a positive one-sided DAN-before-KC exponential trace, the mean effect at -0.6 s must be at least the effect at -1.2 s.",
            "observed_mean_minus1p2_minus_minus0p6": observed_difference,
            "all_minus1p2_preparations_greater_than_all_minus0p6": min(far) > max(near),
            "exact_one_sided_permutation_p_unadjusted": extreme / total,
            "permutations": total,
            "interpretation": "The simple monotonic backward trace contradicts these wild-type measurements; exploratory comparison, not a fitted mechanistic model.",
        },
        "scope_limit": "Figure 2D/2E wild type only. Figure 6 receptor-null preparation-level data are absent from this workbook. No MaleCNS transfer is established.",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("ISI(s) n mean_delta 95%CI")
    for row in results:
        lo, hi = row["mean_delta_95pct_t_interval"]
        print(f"{row['isi_s']:5g} {row['n_preparations']} {row['mean_delta']:+.6f} [{lo:+.6f}, {hi:+.6f}]")


if __name__ == "__main__":
    main()
