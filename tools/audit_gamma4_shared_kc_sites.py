"""Count coordinate-shared KC output sites for name-matched gamma4 MBONs.

This is anatomy only. A coordinate key is not a proven physical release site.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "data/derived/mb_synapse_state_layout_v1"
GRAPH = ROOT / "data/derived/malecns_v1_candidates"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    manifest = json.loads((LAYOUT / "manifest.json").read_text())
    candidate_report = json.loads((ROOT / "reports/malecns_gamma4_contact_roi_boundary.json").read_text())
    arrays = {}
    for name in ("eligible_global_edge", "contact_edge_local", "contact_site", "contact_primary_post_roi"):
        entry = manifest["files"][name]
        path = ROOT / entry["path"]
        assert digest(path) == entry["sha256"]
        arrays[name] = np.load(path, allow_pickle=False)
    body = np.load(GRAPH / "body_ids.npy", allow_pickle=False)
    ptr = np.load(GRAPH / "indptr.npy", allow_pickle=False)
    assert len(body) + 1 == len(ptr)
    edge = arrays["eligible_global_edge"]
    contact_edge = arrays["contact_edge_local"]
    site = arrays["contact_site"]
    roi = arrays["contact_primary_post_roi"]
    assert len(site) == len(contact_edge) == len(roi) == manifest["contacts"]
    assert len(edge) == manifest["eligible_graph_edges"]
    assert int(contact_edge.max()) < len(edge)
    assert int(site.max()) < manifest["presynaptic_sites"]
    post_body = body[np.searchsorted(ptr[1:], edge, side="right")]
    candidates = [row["bodyId"] for row in candidate_report["per_candidate"]]
    candidate_contact = np.isin(post_body[contact_edge], candidates)
    assert int(candidate_contact.sum()) == candidate_report["candidate_contacts"]
    gamma_roi_ids = [manifest["primary_post_roi_names"].index(name) for name in ("gL(L)", "gL(R)")]
    in_gamma_lobe = np.isin(roi, gamma_roi_ids)
    gamma_candidate_contact = candidate_contact & in_gamma_lobe
    assert int(gamma_candidate_contact.sum()) == candidate_report["candidate_gamma_lobe_contacts"]
    candidate_site = np.bincount(site[candidate_contact], minlength=manifest["presynaptic_sites"]) > 0
    other_site = np.bincount(site[~candidate_contact], minlength=manifest["presynaptic_sites"]) > 0
    shared_site = candidate_site & other_site
    gamma_candidate_site = np.bincount(site[gamma_candidate_contact], minlength=manifest["presynaptic_sites"]) > 0
    other_gamma_site = np.bincount(site[~candidate_contact & in_gamma_lobe], minlength=manifest["presynaptic_sites"]) > 0
    shared_gamma_site = gamma_candidate_site & other_gamma_site
    other_any_site = np.bincount(site[~candidate_contact], minlength=manifest["presynaptic_sites"]) > 0
    shared_gamma_candidate_site_any_roi = gamma_candidate_site & other_any_site
    result = {
        "scope": "Coordinate-shared KC sites of name-matched y4 MBON candidates; anatomy only",
        "layout_manifest_sha256": digest(LAYOUT / "manifest.json"),
        "candidate_report_sha256": digest(ROOT / "reports/malecns_gamma4_contact_roi_boundary.json"),
        "graph_body_ids_sha256": digest(GRAPH / "body_ids.npy"),
        "graph_indptr_sha256": digest(GRAPH / "indptr.npy"),
        "candidate_body_ids": candidates,
        "candidate_contacts": int(candidate_contact.sum()),
        "candidate_coordinate_sites": int(candidate_site.sum()),
        "candidate_coordinate_sites_also_targeting_other_mbon": int(shared_site.sum()),
        "candidate_contacts_on_shared_coordinate_sites": int(shared_site[site[candidate_contact]].sum()),
        "other_mbon_contacts_on_shared_coordinate_sites": int(shared_site[site[~candidate_contact]].sum()),
        "fraction_candidate_contacts_on_shared_coordinate_sites": float(shared_site[site[candidate_contact]].mean()),
        "gamma_lobe_candidate_contacts": int(gamma_candidate_contact.sum()),
        "gamma_lobe_candidate_coordinate_sites": int(gamma_candidate_site.sum()),
        "gamma_lobe_candidate_sites_shared_with_other_mbon_in_gamma_lobe": int(shared_gamma_site.sum()),
        "gamma_lobe_candidate_contacts_on_sites_shared_with_other_mbon_in_gamma_lobe": int(shared_gamma_site[site[gamma_candidate_contact]].sum()),
        "gamma_lobe_candidate_contacts_on_sites_shared_with_other_mbon_any_roi": int(shared_gamma_candidate_site_any_roi[site[gamma_candidate_contact]].sum()),
        "fraction_gamma_lobe_candidate_contacts_on_sites_shared_with_other_mbon_in_gamma_lobe": float(shared_gamma_site[site[gamma_candidate_contact]].mean()),
        "coordinate_key_limitation": "(body_pre,x_pre,y_pre,z_pre) in published 8-nm voxels may merge separate ultrastructure and omits non-MBON targets",
        "gamma4_contact_identity_proven": False,
        "receptor_or_plasticity_assigned": False,
        "biological_gate_passed": False,
    }
    out = ROOT / "reports/malecns_gamma4_shared_kc_sites.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run()
