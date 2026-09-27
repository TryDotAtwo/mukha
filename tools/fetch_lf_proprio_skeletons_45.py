"""Pin available v1.0 SWCs for all 45 annotated left-front ProLN afferents."""

import concurrent.futures
import hashlib
import json
from pathlib import Path

import pandas as pd
import requests

from flymimic_public_model import ROOT


GRAPH = ROOT / "data/derived/malecns_v1_candidates/nodes.feather"
PREVIOUS = ROOT / "data/reference/malecns_v1_lf_proprio_skeletons"
OUT = ROOT / "data/reference/malecns_v1_lf_proprio_45_skeletons"
BUCKET = "flyem-male-cns"
PREFIX = "v1.0/segmentation/skeletons-malecns/skeletons-swc/"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fetch(body_id, old):
    name = PREFIX + f"{body_id}.swc"
    meta_url = f"https://storage.googleapis.com/storage/v1/b/{BUCKET}/o/{requests.utils.quote(name, safe='')}"
    meta_response = requests.get(meta_url, timeout=45)
    if meta_response.status_code == 404:
        return {"body_id": body_id, "status": "source_object_missing", "object": name}
    meta_response.raise_for_status()
    meta = meta_response.json()
    assert meta["name"] == name
    pinned_url = f"https://storage.googleapis.com/{BUCKET}/{name}?generation={meta['generation']}"
    if body_id in old and old[body_id]["generation"] == meta["generation"]:
        payload = (PREVIOUS / f"{body_id}.swc").read_bytes()
        assert sha(payload) == old[body_id]["sha256"]
    else:
        response = requests.get(pinned_url, timeout=60)
        response.raise_for_status()
        payload = response.content
    assert len(payload) == int(meta["size"])
    assert payload.startswith(b"#") or payload[:1].isdigit()
    return {"body_id": body_id, "status": "downloaded", "object": name,
            "pinned_url": pinned_url, "generation": meta["generation"],
            "size": len(payload), "source_md5_base64": meta.get("md5Hash"),
            "source_crc32c_base64": meta.get("crc32c"), "sha256": sha(payload),
            "_payload": payload}


def main():
    assert not OUT.exists()
    nodes = pd.read_feather(GRAPH)
    chosen = nodes[(nodes["class"] == "mechanosensory_proprioceptive") &
                   (nodes["entryNerve"] == "ProLN") &
                   (nodes["rootSide"] == "L")].sort_values("bodyId")
    assert len(chosen) == 45
    ids = [int(value) for value in chosen["bodyId"]]
    old_manifest_path = PREVIOUS / "source_manifest.json"
    old = {int(entry["body_id"]): entry for entry in json.loads(
        old_manifest_path.read_text(encoding="utf-8"))["entries"]}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda body_id: fetch(body_id, old), ids))
    OUT.mkdir(parents=True)
    for result in results:
        if result["status"] == "downloaded":
            (OUT / f"{result['body_id']}.swc").write_bytes(result.pop("_payload"))
    manifest = {
        "source": "MaleCNS public GCS v1.0 native EM-coordinate SWC skeletons",
        "selection": "All 45 compact-graph nodes annotated mechanosensory_proprioceptive / ProLN / left",
        "selection_nodes_sha256": sha(GRAPH.read_bytes()),
        "previous_seven_manifest_sha256": sha(old_manifest_path.read_bytes()),
        "coordinate_units": "8 nm per SWC coordinate unit, per author release documentation",
        "entries": results,
    }
    (OUT / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"requested": len(ids), "downloaded": sum(x["status"] == "downloaded" for x in results),
                      "missing": [x["body_id"] for x in results if x["status"] != "downloaded"],
                      "bytes": sum(x.get("size", 0) for x in results)}, indent=2))


if __name__ == "__main__":
    main()
