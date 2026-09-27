"""Pin seven primary MaleCNS v1.0 SWC skeletons for sensory morphology audit."""

import hashlib
import json

import requests

from flymimic_public_model import ROOT


IDS = (817697, 821306, 908487, 912317, 815843, 817680, 935383)
BUCKET = "flyem-male-cns"
PREFIX = "v1.0/segmentation/skeletons-malecns/skeletons-swc/"
OUT = ROOT / "data/reference/malecns_v1_lf_proprio_skeletons"


def main():
    assert not OUT.exists()
    OUT.mkdir(parents=True)
    entries = []
    for body in IDS:
        name = PREFIX + f"{body}.swc"
        meta_url = f"https://storage.googleapis.com/storage/v1/b/{BUCKET}/o/{requests.utils.quote(name, safe='')}"
        meta_response = requests.get(meta_url, timeout=30)
        meta_response.raise_for_status()
        meta = meta_response.json()
        assert meta["name"] == name
        pinned_url = f"https://storage.googleapis.com/{BUCKET}/{name}?generation={meta['generation']}"
        response = requests.get(pinned_url, timeout=30)
        response.raise_for_status()
        payload = response.content
        assert len(payload) == int(meta["size"])
        assert payload.startswith(b"#") or payload[:1].isdigit()
        path = OUT / f"{body}.swc"
        path.write_bytes(payload)
        entries.append({"body_id": body, "object": name,
                        "pinned_url": pinned_url,
                        "generation": meta["generation"],
                        "size": len(payload), "source_md5_base64": meta.get("md5Hash"),
                        "source_crc32c_base64": meta.get("crc32c"),
                        "sha256": hashlib.sha256(payload).hexdigest()})
    manifest = {"source": "MaleCNS public GCS release, v1.0 native EM-coordinate SWC skeletons",
                "coordinate_units": "8 nm per SWC coordinate unit, per author release-bucket documentation for SWC skeletons",
                "bucket": BUCKET, "prefix": PREFIX, "entries": entries,
                "scope": "Seven selected cells for morphology review, not a complete sensory reconstruction"}
    (OUT / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                               encoding="utf-8")
    print(json.dumps({"files": len(entries), "total_bytes": sum(x["size"] for x in entries)}, indent=2))


if __name__ == "__main__":
    main()
