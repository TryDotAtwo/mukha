"""Pin the complete published 2021 left-T1 motor-neuron SWC comparison set."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote

import requests


ROOT = Path(__file__).resolve().parents[1]
COMMIT = "5097916fb0d8a0ca627fe4583575ecd6d4cf1ed9"
REPO = "htem/GridTape_VNC_paper"
PREFIX = "neuron_reconstructions/skeletons_in_FANC_space/motor_neurons/left T1"
OUT = ROOT / "data/reference/fanc_2021_t1_motor_swcs"


def fetch(entry):
    path = entry["path"]
    url = f"https://raw.githubusercontent.com/{REPO}/{COMMIT}/{quote(path, safe='/')}"
    response = requests.get(url, timeout=45)
    response.raise_for_status()
    raw = response.content
    assert len(raw) == entry["size"]
    target = OUT / Path(path).name
    target.write_bytes(raw)
    return {"name": target.name, "source_path": path, "url": url,
            "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    url = f"https://api.github.com/repos/{REPO}/git/trees/{COMMIT}?recursive=1"
    response = requests.get(url, timeout=45)
    response.raise_for_status()
    tree = response.json()
    assert tree.get("truncated") is False
    entries = [x for x in tree["tree"] if x["path"].startswith(PREFIX) and x["path"].endswith(".swc")]
    assert len(entries) == 69
    OUT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=8) as pool:
        files = sorted(pool.map(fetch, entries), key=lambda x: x["name"])
    manifest = {
        "scope": "Complete 2021 FANC left-T1 motor SWC set; not 2024 cell-ID crosswalk",
        "source_repository": f"https://github.com/{REPO}",
        "source_commit": COMMIT,
        "tree_url": url,
        "files": files,
    }
    (OUT / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(len(files), sum(x["bytes"] for x in files), flush=True)


if __name__ == "__main__":
    main()
