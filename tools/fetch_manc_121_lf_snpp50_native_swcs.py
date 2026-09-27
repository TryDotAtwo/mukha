"""Pin all MANC 1.2.1 native SWCs labelled left-front SNpp50 in Lee metadata."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "data/reference/manc_121_motor_crosswalk/manc_121_meta.feather"
DEST = ROOT / "data/reference/manc_121_lf_snpp50_native_swcs"
BUCKET = "lee-lab_brain-and-nerve-cord-fly-connectome"
PREFIX = "compiled_data/manc_121/manc_manc_space_swc"


def main():
    df = pd.read_feather(META)
    selected = df[(df.cell_type == "SNpp50") & (df.side == "left")
                  & (df.body_part_sensory == "front_leg")]
    ids = sorted(selected.manc_121_id.astype(int).tolist())
    assert ids == [96728, 100531, 163745], ids
    DEST.mkdir(parents=True, exist_ok=True)
    files = []
    for body_id in ids:
        name = f"{PREFIX}/{body_id}.swc"
        api_url = f"https://storage.googleapis.com/storage/v1/b/{BUCKET}/o/{name.replace('/', '%2F')}"
        meta = requests.get(api_url, timeout=30)
        meta.raise_for_status()
        info = meta.json()
        url = f"https://storage.googleapis.com/{BUCKET}/{name}?generation={info['generation']}"
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        data = response.content
        assert len(data) == int(info["size"])
        assert data.lstrip().startswith(b"#")
        (DEST / f"{body_id}.swc").write_bytes(data)
        files.append({"body_id": body_id, "url": url,
                      "generation": info["generation"], "bytes": len(data),
                      "sha256": hashlib.sha256(data).hexdigest()})
    manifest = {"release": "MANC 1.2.1, not MANC 1.0",
                "selection": "all metadata cell_type=SNpp50, side=left, body_part_sensory=front_leg",
                "metadata_sha256": hashlib.sha256(META.read_bytes()).hexdigest(),
                "files": files}
    (DEST / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
