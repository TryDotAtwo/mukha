"""Audit source MaleCNS to MANC ID multiplicity for Ti-extensor candidates."""
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/derived/malecns_v1_candidates/manifest.json"
SOURCE = ROOT / "data/raw/malecns_v1/body-annotations-male-cns-v1.0-minconf-0.5.feather"
SELECTED = ROOT / "data/derived/malecns_v1_candidates/nodes.feather"
MANC = ROOT / "data/reference/manc_v1_motor_crosswalk/manc-v1.0-neuron-properties.feather"
MANC_MANIFEST = ROOT / "data/reference/manc_v1_motor_crosswalk/source_manifest.json"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run():
    manifest = json.loads(MANIFEST.read_text())
    source_entry = next(x for x in manifest["source_provenance"]["files"] if x["name"] == SOURCE.name)
    assert sha(SOURCE) == source_entry["sha256"]
    raw = pd.read_feather(SOURCE)
    selected = pd.read_feather(SELECTED)
    columns = ["bodyId", "instance", "superclass", "type", "mancBodyid", "mancType", "mancGroup", "mancSerial", "matchingNotes", "exitNerve"]
    raw_rows = raw[raw.bodyId.isin([800163, 815344, 815678])][columns].sort_values("bodyId")
    selected_rows = selected[selected.bodyId.isin([800163, 815344, 815678])][columns].sort_values("bodyId")
    assert raw_rows.reset_index(drop=True).equals(selected_rows.reset_index(drop=True))
    assert raw_rows.set_index("bodyId").loc[815344, "mancBodyid"] == 10256
    assert raw_rows.set_index("bodyId").loc[800163, "mancBodyid"] == 10256
    assert raw_rows.set_index("bodyId").loc[815678, "mancBodyid"] == 22126
    manc_source = json.loads(MANC_MANIFEST.read_text())
    assert MANC.stat().st_size == manc_source["bytes"]
    assert sha(MANC) == manc_source["sha256"]
    manc = pd.read_feather(MANC, columns=["bodyId", "instance", "type", "class", "target", "origin", "exitNerve", "somaNeuromere", "somaSide", "group", "serial"])
    manc_rows = manc[manc.bodyId.isin([10256, 22126])].sort_values("bodyId")
    assert len(manc_rows) == 2
    assert manc_rows.set_index("bodyId").loc[10256, "type"] == "IN19A001"
    assert manc_rows.set_index("bodyId").loc[22126, "type"] == "Tergotr. MN"
    male_extensors = raw[raw.type == "Ti extensor MN"]
    manc_extensors = manc[manc.type == "Ti extensor MN"]
    assert len(male_extensors) == len(manc_extensors) == 12
    assigned = set(male_extensors.mancBodyid.dropna().astype(int))
    published_manc_ids = set(manc_extensors.bodyId.astype(int))
    unmatched = sorted(published_manc_ids - assigned)
    invalid = sorted(assigned - published_manc_ids)
    assert unmatched == [10461, 10737, 11657, 11706]
    assert invalid == [10256, 22126]
    candidate_rows = []
    for male_id, manc_id in ((815344, 11657), (815678, 11706)):
        male = male_extensors.set_index("bodyId").loc[male_id]
        target = manc_extensors.set_index("bodyId").loc[manc_id]
        assert int(male.mancGroup) == manc_id
        assert male.somaNeuromere == target.somaNeuromere == "T1"
        assert male.somaSide == ("L" if target.somaSide == "LHS" else "R")
        candidate_rows.append({"malecns_body_id": male_id,
                               "candidate_manc_v1_body_id": manc_id,
                               "shared_type": "Ti extensor MN",
                               "same_neuromere": True, "same_side": True,
                               "malecns_manc_group_equals_candidate_id": True,
                               "individual_morphology_match_verified": False})

    def multiplicity(table):
        counts = table.mancBodyid.dropna().value_counts()
        return {"rows_with_manc_id": int(counts.sum()),
                "unique_manc_ids": len(counts),
                "ids_assigned_to_multiple_malecns_rows": int((counts > 1).sum()),
                "rows_on_nonunique_manc_ids": int(counts[counts > 1].sum()),
                "maximum_multiplicity": int(counts.max())}

    result = {
        "scope": "Published MaleCNS v1.0 annotation ID crosswalk; no morphological or muscle-target validation",
        "source_sha256": sha(SOURCE),
        "selected_nodes_sha256": sha(SELECTED),
        "source_generation": source_entry["gcs_generation"],
        "manc_v1_export_generation": manc_source["gcs_generation"],
        "manc_v1_export_sha256": sha(MANC),
        "manc_v1_rows": json.loads(manc_rows.to_json(orient="records")),
        "ti_extensor_set_reconciliation": {
            "malecns_rows": len(male_extensors),
            "manc_v1_rows": len(manc_extensors),
            "manc_v1_ids_not_present_in_malecns_extensor_bodyid_field": unmatched,
            "malecns_extensor_bodyid_values_with_other_manc_v1_types": invalid,
            "possible_replacement_candidates": candidate_rows,
            "replacement_accepted": False},
        "raw_multiplicity": multiplicity(raw),
        "selected_multiplicity": multiplicity(selected),
        "relevant_rows": raw_rows.where(pd.notna(raw_rows), None).to_dict("records"),
        "left_ti_extensor_manc_id_unique_in_source": False,
        "manc_v1_ids_match_malecns_motor_types": False,
        "individual_motor_to_muscle_identity_verified": False,
        "biological_gate_passed": False,
    }
    path = ROOT / "reports/malecns_motor_manc_crosswalk.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run()
