"""Restore the pinned public FlyMimic MuJoCo model without HF credentials.

Only the author model XML and its mesh directory are extracted. Every blob is
checked against the Git tree at the pinned commit; differing existing files
are refused. This does not restore the project's private cockpit fixtures.
"""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile

import requests

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data/reference/flymimic"
REPORT = ROOT / "reports/flymimic_public_restore.json"
COMMIT = "9ea1131626cd76f7203b74076ef8f0e9cab30bef"
REPO = "gizemozd/FlyMimic"
MODEL = "flymimic/assets/models/best_combined_cvt3.xml"
MESH_PREFIX = "flymimic/assets/models/meshes/"
EXPECTED_MODEL_SHA256 = "d67ff06d0c684599f00d5f33f8f8ac8ced01ab994c41341b551f8148b6d8aa0b"


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def main():
    tree_url = f"https://api.github.com/repos/{REPO}/git/trees/{COMMIT}?recursive=1"
    response = requests.get(tree_url, timeout=30)
    response.raise_for_status()
    tree = response.json()
    assert not tree.get("truncated")
    selected = {item["path"]: item for item in tree["tree"]
                if item["type"] == "blob" and
                (item["path"] == MODEL or item["path"].startswith(MESH_PREFIX))}
    assert MODEL in selected and len(selected) == 73, len(selected)
    archive_url = f"https://codeload.github.com/{REPO}/tar.gz/{COMMIT}"
    response = requests.get(archive_url, timeout=120)
    response.raise_for_status()
    archive_bytes = response.content
    entries = []
    found = set()
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tar:
        for member in tar:
            parts = PurePosixPath(member.name).parts
            if len(parts) < 2:
                continue
            relative = PurePosixPath(*parts[1:]).as_posix()
            if relative not in selected:
                continue
            assert member.isfile() and relative not in found
            found.add(relative)
            data = tar.extractfile(member).read()
            meta = selected[relative]
            assert len(data) == meta["size"] and git_blob(data) == meta["sha"]
            digest = hashlib.sha256(data).hexdigest()
            if relative == MODEL:
                assert digest == EXPECTED_MODEL_SHA256
            target = DEST.joinpath(*PurePosixPath(relative).parts)
            assert target.resolve().is_relative_to(DEST.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                assert target.read_bytes() == data, f"refusing differing file: {target}"
            else:
                target.write_bytes(data)
            entries.append({"path": str(target.relative_to(ROOT)).replace("\\", "/"),
                            "bytes": len(data), "git_blob_sha1": meta["sha"],
                            "sha256": digest})
    assert found == set(selected)
    report = {"repository": f"https://github.com/{REPO}", "commit": COMMIT,
              "archive_sha256": hashlib.sha256(archive_bytes).hexdigest(),
              "files": sorted(entries, key=lambda item: item["path"]),
              "file_count": len(entries),
              "total_uncompressed_bytes": sum(item["bytes"] for item in entries),
              "scope": "Pinned public FlyMimic XML and meshes; no private cockpit fixture, neural mapping or biological validation."}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"files": report["file_count"],
                      "bytes": report["total_uncompressed_bytes"],
                      "model_sha256": EXPECTED_MODEL_SHA256,
                      "archive_sha256": report["archive_sha256"]}))


if __name__ == "__main__":
    main()
