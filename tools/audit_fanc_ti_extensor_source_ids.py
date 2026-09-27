"""Recover the two published FANC tibia-extensor segment IDs from source links."""

import hashlib
import json
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/reference/azevedo2024_appendix"
PDF = DATA / "nature_supplement.pdf"
STATE = DATA / "ti_extensor_neuroglancer.json"
OUT = ROOT / "reports/fanc_ti_extensor_source_ids.json"
PDF_SHA = "dcbb671d7831eb64f7554af4a32f59e3f2eb0dc1b1294e4876f2838a603076ba"
STATE_SHA = "cf0ee2947192d3260548f67b98c17c11f65f3583dba910b5e50c0a1d5f5fdf4a"


def check(path, expected):
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError(f"hash mismatch: {path}: {actual}")


def main():
    check(PDF, PDF_SHA)
    check(STATE, STATE_SHA)
    pdf = fitz.open(PDF)
    assert "tibia extensor" in pdf[1].get_text().lower()
    links = [link["uri"] for link in pdf[1].get_links() if "ti_extensor.json" in link.get("uri", "")]
    assert len(links) == 1, links
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert links[0].split("json_url=")[1] == (
        "https://raw.githubusercontent.com/EllenLesser/Azevedo_Lesser_Phelps_Mark_2023/main/jsons/ti_extensor.json"
    )
    layers = [x for x in state["layers"] if x.get("name") == "published FANC neurons"]
    assert len(layers) == 1
    ids = layers[0]["segments"]
    assert ids == ["648518346493238080", "648518346495797355"]
    report = {
        "source_article": "https://doi.org/10.1038/s41586-024-07389-x",
        "supplement_url": "https://media.springernature.com/original/springer-static/esm/art:10.1038%2Fs41586-024-07389-x/MediaObjects/41586_2024_7389_MOESM1_ESM.pdf",
        "supplement_sha256": PDF_SHA,
        "supplement_pdf_page_1based": 2,
        "source_link": links[0],
        "neuroglancer_state_sha256": STATE_SHA,
        "published_fanc_t1_tibia_extensor_segment_ids": ids,
        "fanc_mn39_vs_mn40_segment_assignment_verified": False,
        "fanc_to_manc_identity_verified": False,
        "male_cns_motor_mapping_enabled": False,
        "scope": "Published pair of FANC T1 tibia-extensor segments, without individual fast/slow or MANC mapping",
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(ids)


if __name__ == "__main__":
    main()
