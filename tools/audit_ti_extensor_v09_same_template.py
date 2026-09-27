"""Descriptive, version-mismatched Ti extensor morphology check in VNC space."""

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/reference/ti_extensor_template_crosswalk"
MANIFEST = DATA / "source_manifest.json"
OUT = ROOT / "reports/ti_extensor_v09_same_template.json"


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ids = [815344, 815678, 11657, 12704, 11706, 13115]
    labels = {
        815344: "malecns_v09_815344",
        815678: "malecns_v09_815678",
        11657: "manc_11657",
        12704: "manc_12704",
        11706: "manc_11706",
        13115: "manc_13115",
    }
    xyz = {}
    topology = {}
    for ident in ids:
        label = labels[ident]
        item = next(x for x in manifest["items"] if x["id"] == ident and
                    x["template"] == "JRC2018UnisexVNC")
        raw = (DATA / (label + ".swc")).read_bytes()
        assert len(raw) == item["bytes"]
        assert hashlib.sha256(raw).hexdigest() == item["sha256"]
        swc = np.loadtxt(DATA / (label + ".swc"), comments="#")
        xyz[ident] = swc[:, 2:5]
        topology[ident] = swc[:, 6]

    comparisons = []
    for male, manc_ids in ((815344, (11657, 12704)),
                            (815678, (11706, 13115))):
        for manc in manc_ids:
            forward = cKDTree(xyz[manc]).query(xyz[male], workers=-1)[0]
            reverse = cKDTree(xyz[male]).query(xyz[manc], workers=-1)[0]
            comparisons.append({
                "male_v09": male,
                "manc_v10": manc,
                "male_to_manc_median_um": float(np.median(forward)),
                "manc_to_male_median_um": float(np.median(reverse)),
                "male_to_manc_p90_um": float(np.quantile(forward, .9)),
                "manc_to_male_p90_um": float(np.quantile(reverse, .9)),
            })

    topology_check = {}
    for ident in (815344, 815678):
        v10 = np.loadtxt(DATA / f"malecns_{ident}.swc", comments="#")
        topology_check[str(ident)] = {
            "same_node_count": bool(len(v10) == len(topology[ident])),
            "same_parent_sequence": bool(np.array_equal(v10[:, 6], topology[ident])),
            "v09_root_count": int(np.count_nonzero(topology[ident] == -1)),
            "v10_root_count": int(np.count_nonzero(v10[:, 6] == -1)),
        }

    report = {
        "scope": "Descriptive cross-version morphology; no motor identity or muscle assignment",
        "source_manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "same_template": "JRC2018UnisexVNC",
        "same_dataset_release": False,
        "vfb_manc_dataset_page_release": "v1.2.1",
        "vfb_manc_dataset_page": "https://www.virtualflybrain.org/term/male-adult-nerve-cord-manc-connectome-neurons-takemura2023/",
        "topology_check": topology_check,
        "comparisons": comparisons,
        "conclusion": "Nearest-neighbor rankings depend on direction and tail; no unique match established. VFB MaleCNS v0.9 and VFB MANC dataset page v1.2.1 cannot validate v1.0-to-v1.0 identity.",
        "biological_gate_passed": False,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
