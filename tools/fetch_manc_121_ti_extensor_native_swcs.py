"""Pin two candidate MANC 1.2.1 skeletons in their native space."""

import hashlib
import json
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data/reference/manc_121_ti_extensor_native_swcs"
BUCKET = "lee-lab_brain-and-nerve-cord-fly-connectome"
PREFIX = "compiled_data/manc_121/manc_manc_space_swc"


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    files = []
    for body_id in (11657, 12704):
        name = f"{PREFIX}/{body_id}.swc"
        metadata_url = f"https://storage.googleapis.com/storage/v1/b/{BUCKET}/o/{name.replace('/', '%2F')}"
        meta_response = requests.get(metadata_url, timeout=30)
        meta_response.raise_for_status()
        metadata = meta_response.json()
        generation = metadata["generation"]
        media_url = f"https://storage.googleapis.com/{BUCKET}/{name}?generation={generation}"
        response = requests.get(media_url, timeout=60)
        response.raise_for_status()
        data = response.content
        assert len(data) == int(metadata["size"])
        assert data.lstrip().startswith(b"#")
        path = DEST / f"{body_id}.swc"
        path.write_bytes(data)
        files.append({"body_id": body_id, "url": media_url,
                      "generation": generation, "bytes": len(data),
                      "sha256": hashlib.sha256(data).hexdigest()})
    manifest = {"release": "MANC 1.2.1, not MANC 1.0",
                "source_documentation": "https://github.com/sjcabs/fly_connectome_data_tutorial/blob/main/README.md",
                "files": files}
    (DEST / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
