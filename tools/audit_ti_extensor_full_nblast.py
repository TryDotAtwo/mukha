"""Audit all 12 published MaleCNS Ti extensor neurons against VFB MANC.

This is a morphology screen across dataset releases, not an identity proof.
"""

import hashlib
import json
from pathlib import Path

import navis
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "reports/ti_extensor_v1_vnc_registration.json"
VFB = ROOT / "data/reference/ti_extensor_template_crosswalk"
MALE_ANNOT = ROOT / "data/raw/malecns_v1/body-annotations-male-cns-v1.0-minconf-0.5.feather"
MANC_ANNOT = ROOT / "data/reference/manc_v1_motor_crosswalk/manc-v1.0-neuron-properties.feather"
OUT = ROOT / "reports/ti_extensor_full_nblast.json"
SEGMENT = {"ProLN": "T1", "MesoLN": "T2", "MetaLN": "T3"}
SIDE = {"LHS": "L", "RHS": "R"}


def dotprops(points, ident, k):
    dp = navis.make_dotprops(points, k=k)
    dp.id = str(ident)
    dp.units = "1 um"
    return dp


def matrix(query, target):
    frame = navis.nblast(navis.NeuronList(query), navis.NeuronList(target),
                         scores="mean", normalized=True, smat="auto",
                         n_cores=1, progress=False)
    return {str(i): {str(j): float(frame.loc[str(i), str(j)])
                     for j in frame.columns} for i in frame.index}


def main():
    reg = json.loads(REG.read_text())
    manifest = json.loads((VFB / "source_manifest.json").read_text())
    male_annot = pd.read_feather(MALE_ANNOT)
    manc_annot = pd.read_feather(MANC_ANNOT)
    male_rows = male_annot[male_annot["type"] == "Ti extensor MN"]
    manc_rows = manc_annot[manc_annot["type"] == "Ti extensor MN"]
    assert len(male_rows) == len(manc_rows) == 12

    male = {}
    for item in reg["results"]:
        path = ROOT / item["output"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        male[item["bodyId"]] = np.load(path)
    assert set(male) == set(male_rows.bodyId.astype(int))

    manc = {}
    for item in manifest["items"]:
        if not item["dataset"].startswith("MANC"):
            continue
        path = VFB / f'manc_{item["id"]}.swc'
        raw = path.read_bytes()
        assert len(raw) == item["bytes"]
        assert hashlib.sha256(raw).hexdigest() == item["sha256"]
        manc[item["id"]] = np.loadtxt(path, comments="#")[:, 2:5]
    assert set(manc) == set(manc_rows.bodyId.astype(int))

    groups = {}
    for row in male_rows.itertuples():
        key = SEGMENT[row.exitNerve] + "_" + row.instance.rsplit("_", 1)[-1]
        groups.setdefault(key, {"male": [], "manc": []})["male"].append(int(row.bodyId))
    for row in manc_rows.itertuples():
        key = row.somaNeuromere + "_" + SIDE[row.somaSide]
        groups.setdefault(key, {"male": [], "manc": []})["manc"].append(int(row.bodyId))
    assert len(groups) == 6
    assert all(len(g["male"]) == len(g["manc"]) == 2 for g in groups.values())
    for g in groups.values():
        g["male"].sort()
        g["manc"].sort()

    scores = {}
    for k in (10, 20, 40):
        scores[str(k)] = {}
        for key, g in sorted(groups.items()):
            q = [dotprops(male[i], i, k) for i in g["male"]]
            t = [dotprops(manc[i], i, k) for i in g["manc"]]
            scores[str(k)][key] = matrix(q, t)
        print(f"computed six groups at k={k}", flush=True)

    k20 = scores["20"]
    best = []
    for key, g in sorted(groups.items()):
        for ident in g["male"]:
            options = sorted(k20[key][str(ident)].items(),
                             key=lambda x: x[1], reverse=True)
            annotated = male_rows.loc[male_rows.bodyId == ident,
                                      "mancBodyid"].iloc[0]
            annotated_id = None if pd.isna(annotated) else int(annotated)
            annotated_manc = manc_annot.loc[manc_annot.bodyId == annotated_id] if annotated_id else manc_annot.iloc[:0]
            stable = all(
                max(scores[str(k)][key][str(ident)].items(), key=lambda x: x[1])[0]
                == options[0][0] for k in (10, 20, 40)
            )
            best.append({
                "male_id": ident,
                "segment_side": key,
                "best_manc_id": int(options[0][0]),
                "best_score": options[0][1],
                "margin_to_second": options[0][1] - options[1][1],
                "best_is_k_stable": stable,
                "male_v1_mancBodyid": annotated_id,
                "mancBodyid_matches_best": annotated_id == int(options[0][0]),
                "mancBodyid_type_in_official_manc_v1": (
                    None if annotated_manc.empty else str(annotated_manc.iloc[0]["type"])
                ),
            })

    report = {
        "scope": "All 12 Ti extensor MN morphology screen; no muscle assignment",
        "registration_report_sha256": hashlib.sha256(REG.read_bytes()).hexdigest(),
        "vfb_manifest_sha256": hashlib.sha256((VFB / "source_manifest.json").read_bytes()).hexdigest(),
        "male_annotation_sha256": hashlib.sha256(MALE_ANNOT.read_bytes()).hexdigest(),
        "manc_v1_annotation_sha256": hashlib.sha256(MANC_ANNOT.read_bytes()).hexdigest(),
        "male_count": len(male), "manc_count": len(manc),
        "groups": groups,
        "method": {"navis_version": navis.__version__, "dotprops_k": [10, 20, 40],
                   "scores": "mean", "normalized": True, "smat": "auto",
                   "caveat": "Auto score matrix is FCWB-trained, not VNC-specific; VFB MANC SWC release is not individually confirmed as v1.0."},
        "within_group_matrices": scores,
        "within_group_best_at_k20": best,
        "k_stable_best_count": sum(x["best_is_k_stable"] for x in best),
        "published_mancBodyid_matches_best_count": sum(x["mancBodyid_matches_best"] for x in best),
        "candidate_only_count": sum(not x["mancBodyid_matches_best"] for x in best),
        "biological_gate_passed": False,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()
