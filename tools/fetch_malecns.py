"""Download unmodified official MaleCNS v1.0 connectivity and annotations.

Only acquisition/verification runs in Python. This is not a neural simulator.
GCS generation IDs pin remote objects; source MD5 and local SHA-256 are recorded.
No neuron, edge, synapse-count, or neurotransmitter filtering is performed.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import time
import urllib.request
from pathlib import Path

BASE_URL = "https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/"
FILES = (
    "body-annotations-male-cns-v1.0-minconf-0.5.feather",
    "body-neurotransmitters-male-cns-v1.0.feather",
    "connectome-weights-male-cns-v1.0-minconf-0.5.feather",
)
PROJECT = Path(__file__).resolve().parents[1]
CHUNK = 8 * 1024 * 1024


def remote_metadata(name: str) -> dict:
    url = BASE_URL + name
    request = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(request, timeout=60) as response:
        headers = response.headers
        hashes = {}
        for value in headers.get_all("x-goog-hash", []):
            for pair in value.split(","):
                key, digest = pair.strip().split("=", 1)
                hashes[key] = digest
        generation = headers.get("x-goog-generation")
        if not generation or "md5" not in hashes:
            raise RuntimeError(f"Missing generation/MD5 for {name}")
        return {
            "name": name,
            "url": url,
            "pinned_url": url + "?generation=" + generation,
            "gcs_generation": generation,
            "bytes": int(headers["Content-Length"]),
            "source_md5_base64": hashes["md5"],
            "source_crc32c_base64": hashes.get("crc32c"),
        }


def digest_file(path: Path) -> tuple[str, str]:
    sha = hashlib.sha256()
    md5 = hashlib.md5()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(CHUNK), b""):
            sha.update(block)
            md5.update(block)
    return sha.hexdigest(), base64.b64encode(md5.digest()).decode("ascii")


def fetch(item: dict, directory: Path) -> dict:
    target = directory / item["name"]
    if target.exists():
        sha, md5 = digest_file(target)
        if target.stat().st_size != item["bytes"] or md5 != item["source_md5_base64"]:
            raise RuntimeError(f"Existing file fails source verification: {target}")
        print(f"Verified existing {item['name']}", flush=True)
    else:
        partial = target.with_suffix(target.suffix + ".part")
        if partial.exists():
            raise RuntimeError(f"Partial download already exists; inspect it before retry: {partial}")
        sha_state, md5_state = hashlib.sha256(), hashlib.md5()
        total = 0
        started = last_report = time.monotonic()
        print(f"Downloading {item['name']} ({item['bytes'] / 1e6:.1f} MB)", flush=True)
        with urllib.request.urlopen(item["pinned_url"], timeout=90) as response, partial.open("xb") as stream:
            if response.headers.get("x-goog-generation") != item["gcs_generation"]:
                raise RuntimeError("Object generation changed")
            for block in iter(lambda: response.read(CHUNK), b""):
                stream.write(block)
                sha_state.update(block)
                md5_state.update(block)
                total += len(block)
                now = time.monotonic()
                if now - last_report >= 10:
                    print(f"  {total / 1e6:.1f}/{item['bytes'] / 1e6:.1f} MB, {total / max(now-started, 0.001) / 1e6:.1f} MB/s", flush=True)
                    last_report = now
        sha = sha_state.hexdigest()
        md5 = base64.b64encode(md5_state.digest()).decode("ascii")
        if total != item["bytes"] or md5 != item["source_md5_base64"]:
            raise RuntimeError(f"Downloaded file fails source verification: {partial}")
        partial.rename(target)
        print(f"Verified {item['name']}: SHA256={sha}", flush=True)
    return {**item, "local_path": target.relative_to(PROJECT).as_posix(), "sha256": sha, "source_md5_verified": True}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()
    items = [remote_metadata(name) for name in FILES]
    if args.metadata_only:
        print(json.dumps(items, indent=2))
        return
    destination = PROJECT / "data" / "raw" / "malecns_v1"
    destination.mkdir(parents=True, exist_ok=True)
    required = sum(item["bytes"] for item in items if not (destination / item["name"]).exists())
    if shutil.disk_usage(destination).free < required + 2 * 1024**3:
        raise RuntimeError("Insufficient disk space for sources plus 2 GiB reserve")
    # Sequential acquisition gives bounded disk/network pressure and progress.
    verified = [fetch(item, destination) for item in items]
    report = {
        "dataset": "male-cns:v1.0",
        "source_page": "https://male-cns.janelia.org/download/",
        "source_release_confidence": "minconf-0.5 as published; not an extra local filter",
        "local_filtering": "none",
        "scope": "full published segment-to-segment weighted graph plus annotations and body neurotransmitter predictions; not raw microscopy or individual synapse locations",
        "files": verified,
    }
    output = PROJECT / "reports" / "malecns_source_lock.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Source lock: {output}", flush=True)


if __name__ == "__main__":
    main()
