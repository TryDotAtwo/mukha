"""Pin a sparse direct Dm9 support alternative to the diagnostic graph.

This is a sign hypothesis for selected source contacts, not a receptor model.
The original full graph and its runtime weights are left unchanged.
"""

import hashlib
import json

import numpy as np
import pandas as pd

from flymimic_public_model import ROOT
from probe_live_cns_flymimic import GRAPH, graph_arrays


SOURCE = ROOT / "data/derived/dm9_physiology_evidence_v1/visual_edge_evidence.feather"
EVIDENCE = ROOT / "reports/dm9_physiology_evidence.json"
DIAGNOSTIC = ROOT / "data/derived/malecns_sign_diagnostic_float64_v2/report.json"
OUT = ROOT / "data/derived/dm9_direct_support_variant_v1"
REPORT = ROOT / "reports/dm9_direct_support_variant.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not OUT.exists() and not REPORT.exists()
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    diagnostic = json.loads(DIAGNOSTIC.read_text(encoding="utf-8"))
    assert sha(SOURCE) == evidence["files"][SOURCE.name]
    assert diagnostic["spec"]["shared_assumptions"]["glutamate"] == -1
    edges = pd.read_feather(SOURCE)
    selected = edges.loc[edges.evidence_family.eq("dm9_to_inner")]
    assert len(selected) == evidence["evidence_coverage"]["dm9_to_inner"]["rows"]
    offsets = selected.csr_edge_index.to_numpy(dtype=np.int64)
    assert len(np.unique(offsets)) == len(offsets)
    n, total, _, row, col, weights = graph_arrays()
    assert len(row) == n + 1 and len(weights) == total
    pre = selected.pre_graph_index.to_numpy(dtype=np.uint32)
    post = selected.post_graph_index.to_numpy(dtype=np.int64)
    assert np.all(row[post] <= offsets) and np.all(offsets < row[post + 1])
    assert np.array_equal(col[offsets], pre)
    contacts = selected.synapse_count.to_numpy(dtype=np.float64)
    baseline = -contacts * diagnostic["spec"]["weight_mv_per_contact"]
    assert np.array_equal(weights[offsets], baseline)
    assert int(contacts.sum()) == evidence["evidence_coverage"]["dm9_to_inner"]["contact_count"]
    alternative = -weights[offsets]
    assert np.all(alternative > 0)
    OUT.mkdir(parents=True)
    patch_path = OUT / "csr_edge_offsets.npy"
    np.save(patch_path, offsets)
    report = {
        "scope": "Sparse direct-support sign alternative for source-identified Dm9 to named R7/R8 contacts",
        "source_evidence_sha256": sha(SOURCE), "evidence_report_sha256": sha(EVIDENCE),
        "diagnostic_report_sha256": sha(DIAGNOSTIC), "baseline_graph_sha256": sha(GRAPH),
        "csr_edge_offsets_sha256": sha(patch_path),
        "changed_edge_rows": len(offsets), "changed_contacts": int(contacts.sum()),
        "distinct_dm9_sources": len(np.unique(pre)),
        "distinct_r7_r8_targets": len(np.unique(post)),
        "baseline_direct_weight_sum_mv": float(weights[offsets].sum()),
        "alternative_direct_weight_sum_mv": float(alternative.sum()),
        "patch_operation": "multiply only listed CSR weights by -1 in a separately named diagnostic run",
        "unchanged_edge_rows": total - len(offsets),
        "source_claim": "Dm9 provides likely excitatory glutamatergic support to inner photoreceptors; net circuit feedback can be inhibitory",
        "known_limits": ["Direct receptor and conductance are not established",
                         "Female calcium findings have not been transferred to this male individual-cell model",
                         "Uniform diagnostic 0.275 mV/contact gain remains unmeasured",
                         "No physiological visual stimulus or dynamic response is tested here"],
        "runtime_enabled": False, "biological_validation": False,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("changed_edge_rows", "changed_contacts",
                      "distinct_dm9_sources", "distinct_r7_r8_targets")}, indent=2))


if __name__ == "__main__":
    main()
