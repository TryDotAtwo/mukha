"""Reconcile author optic-column cells with complete MaleCNS sensory boundary."""
import hashlib
import json

import pandas as pd

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSIGN = ROOT / "data/derived/malecns_optic_columns/assignments.csv"
CELLS = ROOT / "data/derived/malecns_visual_boundary_v1/cells.feather"
REPORT = ROOT / "reports/visual_column_boundary_reconciliation.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    index_report = json.loads((ROOT / "reports/optic_column_index.json").read_text())
    boundary_report = json.loads((ROOT / "reports/visual_boundary.json").read_text())
    assert sha(ASSIGN) == index_report["files"][ASSIGN.name]
    assignments = pd.read_csv(ASSIGN)
    sensory = pd.read_feather(CELLS)
    assert assignments.body_id.is_unique and sensory.bodyId.is_unique
    joined = assignments.merge(sensory, left_on="body_id", right_on="bodyId", how="left",
                               validate="one_to_one", indicator=True)
    assert ((joined.role == "L1") == (joined._merge == "left_only")).all()
    receptors = joined[joined.role.isin(("R7", "R8"))]
    assert (receptors._merge == "both").all()
    assert (receptors.graph_index_x == receptors.graph_index_y).all()
    assert (receptors.source_cell_type == receptors.type).all()
    assert len(sensory) == boundary_report["selected_cell_count"] if "selected_cell_count" in boundary_report else len(sensory) == 6098
    r7r8 = sensory[sensory.type.str.match(r"^R[78]")]
    unassigned = r7r8[~r7r8.bodyId.isin(assignments.body_id)]
    types = {str(name): int(count) for name, count in unassigned.type.value_counts().items()}
    assert types == {"R7R8_unclear": 85, "R7_unclear": 1}
    outer = int((sensory.type == "R1-R6").sum())
    eyelet = int((sensory.type == "HBeyelet").sum())
    assert (outer, eyelet) == (3377, 7)
    assert outer + eyelet + len(receptors) + len(unassigned) == len(sensory)
    assert len(assignments[assignments.role == "R7"]) == 1299
    assert len(assignments[assignments.role == "R8"]) == 1329
    assert len(assignments[assignments.role == "L1"]) == 1764
    report = {"optic_index_report_sha256": sha(ROOT / "reports/optic_column_index.json"),
              "sensory_boundary_report_sha256": sha(ROOT / "reports/visual_boundary.json"),
              "assignment_csv_sha256": sha(ASSIGN), "sensory_cells_feather_sha256": sha(CELLS),
              "sensory_population": len(sensory), "author_column_assignment_rows": len(assignments),
              "receptor_assignments_in_sensory_boundary": len(receptors),
              "l1_assignments_outside_sensory_boundary": int((joined.role == "L1").sum()),
              "all_r7_r8_body_ids_graph_indices_and_types_match": True,
              "assigned_by_role": {str(k): int(v) for k, v in assignments.role.value_counts().items()},
              "complete_sensory_partition": {"R1-R6_without_column_assignment": outer,
                                              "R7_R8_with_author_column": len(receptors),
                                              "R7_R8_like_without_column": len(unassigned),
                                              "HBeyelet": eyelet},
              "unassigned_r7_r8_like_by_type": types,
              "unassigned_r7_r8_like": unassigned[["bodyId", "graph_index", "type", "rootSide",
                                                    "incoming_rows", "outgoing_rows"]].to_dict(orient="records"),
              "optical_ray_assignments": 0,
              "scope": "Author column-to-MaleCNS anatomical identity only; cannot join other-specimen eyemap rays or infer R1-R6 or spectral response."}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("sensory_population", "author_column_assignment_rows",
                                        "assigned_by_role", "receptor_assignments_in_sensory_boundary",
                                        "l1_assignments_outside_sensory_boundary", "unassigned_r7_r8_like_by_type",
                                        "optical_ray_assignments")}, indent=2))


if __name__ == "__main__":
    main()
