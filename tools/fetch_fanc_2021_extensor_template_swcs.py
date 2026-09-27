"""Pin two full 2021 FANC manual SWCs in the published female VNC template."""

import hashlib
import json
from pathlib import Path
from urllib.parse import quote

import requests


ROOT = Path(__file__).resolve().parents[1]
COMMIT = "5097916fb0d8a0ca627fe4583575ecd6d4cf1ed9"
PREFIX = "neuron_reconstructions/skeletons_in_JRC2018_VNC_FEMALE_space/motor_neurons/"
NEURONS = (581, 9001)
OUT = ROOT / "data/reference/fanc_2021_ti_extensor_template_swcs"


def main():
    tree_url = f"https://api.github.com/repos/htem/GridTape_VNC_paper/git/trees/{COMMIT}?recursive=1"
    r = requests.get(tree_url, timeout=45)
    r.raise_for_status()
    tree = r.json()
    assert tree.get("truncated") is False
    OUT.mkdir(parents=True, exist_ok=True)
    files = []
    for ident in NEURONS:
        candidates = [x for x in tree["tree"] if x["path"].startswith(PREFIX)
                      and x["path"].endswith(" - elastic transform.swc")
                      and f"(neuron {ident})" in x["path"]]
        assert len(candidates) == 1, (ident, candidates)
        entry = candidates[0]
        url = f"https://raw.githubusercontent.com/htem/GridTape_VNC_paper/{COMMIT}/{quote(entry['path'], safe='/')}"
        r = requests.get(url, timeout=45)
        r.raise_for_status()
        assert len(r.content) == entry["size"]
        path = OUT / f"{ident}.swc"
        path.write_bytes(r.content)
        files.append({"neuron_id": ident, "source_path": entry["path"],
                      "url": url, "bytes": len(r.content),
                      "sha256": hashlib.sha256(r.content).hexdigest()})
    manifest = {
        "scope": "2021 FANC manual SWCs in published JRC2018 VNC female template; cross-release segment association is morphological",
        "source_commit": COMMIT,
        "tree_url": tree_url,
        "files": files,
    }
    (OUT / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print([(x["neuron_id"], x["bytes"]) for x in files], flush=True)


if __name__ == "__main__":
    main()
