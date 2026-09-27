"""Pin public MaleCNS v1.0 SWCs for the 13 direct SNpp50/51 candidates."""
import hashlib
import json
from pathlib import Path

import requests

root = Path(__file__).resolve().parents[1]
screen = json.loads((root / "reports/agrawal_13b_connectivity.json").read_text())
ids = [x["bodyId"] for x in screen["candidates"] if x["snpp50_51_front_leg_edge_rows"]]
assert len(ids) == 13 and len(set(ids)) == 13
out = root / "data/reference/malecns_v1_agrawal_13b_candidates"
assert not out.exists()
out.mkdir(parents=True)
bucket = "flyem-male-cns"
prefix = "v1.0/segmentation/skeletons-malecns/skeletons-swc/"
entries = []
for body in ids:
    name = f"{prefix}{body}.swc"
    meta_url = f"https://storage.googleapis.com/storage/v1/b/{bucket}/o/{requests.utils.quote(name, safe='')}"
    meta_response = requests.get(meta_url, timeout=30)
    meta_response.raise_for_status()
    meta = meta_response.json()
    assert meta["name"] == name
    pinned_url = f"https://storage.googleapis.com/{bucket}/{name}?generation={meta['generation']}"
    response = requests.get(pinned_url, timeout=30)
    response.raise_for_status()
    payload = response.content
    assert len(payload) == int(meta["size"])
    assert payload.startswith(b"#") or payload[:1].isdigit()
    path = out / f"{body}.swc"
    path.write_bytes(payload)
    entries.append({"body_id": body, "object": name, "generation": meta["generation"],
                    "size": len(payload), "source_md5_base64": meta.get("md5Hash"),
                    "source_crc32c_base64": meta.get("crc32c"),
                    "sha256": hashlib.sha256(payload).hexdigest()})
manifest = {"bucket": bucket, "prefix": prefix,
            "screen_sha256": hashlib.sha256((root / "reports/agrawal_13b_connectivity.json").read_bytes()).hexdigest(),
            "entries": entries,
            "scope": "candidate morphology only; no Agrawal individual-cell identity assigned"}
(out / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"files": len(entries), "bytes": sum(x["size"] for x in entries)}))
