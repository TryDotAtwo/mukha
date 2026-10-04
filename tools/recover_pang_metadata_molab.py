"""Acquire the official Pang metadata workbook in MoLab, with HF receipts."""
import argparse
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
import zipfile

from hf_artifact_archive import digest, publish

URL = "https://datadryad.org/downloads/file_stream/3732249"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    if not os.environ.get("HF_TOKEN"):
        raise RuntimeError("HF_TOKEN required before acquisition")
    root = Path(args.root)
    root.mkdir(exist_ok=False, parents=True)
    source_files = {}
    for name in ("recover_pang_metadata_molab.py", "hf_artifact_archive.py"):
        source = Path(__file__).parent / name
        target = root / "source" / name
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(source.read_bytes())
        source_files["source/" + name] = {"bytes": target.stat().st_size, "sha256": digest(target)}
    protocol = {"source_commit": args.source_commit, "dataset_doi": "10.5061/dryad.ngf1vhj4c",
                "official_file_id": 3732249, "url": URL, "maximum_bytes": 1048576,
                "scope": "Acquire metadata; no physiology/model agreement claim"}
    (root / "protocol.json").write_text(json.dumps(protocol, indent=2))
    source_files["protocol.json"] = {"bytes": (root/"protocol.json").stat().st_size, "sha256": digest(root/"protocol.json")}
    print("ACQUISITION_SOURCE_RECEIPT", json.dumps(publish(root, {"schema":"faithful-fly-artifacts-v1","files":source_files})), flush=True)
    report = {"url": URL, "acquired": False, "scope": protocol["scope"]}
    outputs = {}
    try:
        with urllib.request.urlopen(URL, timeout=45) as response:
            payload = response.read(1048577)
            report.update({"http_status":response.status, "final_url":response.url,
                           "content_type":response.headers.get("Content-Type"), "bytes":len(payload)})
        if len(payload) > 1048576:
            raise ValueError("Workbook response exceeds preregistered bound")
        target = root / "L1L2_Metadata.xlsx"
        target.write_bytes(payload)
        with zipfile.ZipFile(target) as workbook:
            members = set(workbook.namelist())
            if "[Content_Types].xml" not in members or "xl/workbook.xml" not in members:
                raise ValueError("Response is not an XLSX workbook")
        outputs["L1L2_Metadata.xlsx"] = {"bytes":len(payload),"sha256":digest(target)}
        report["acquired"] = True
        report["workbook_sha256"] = digest(target)
    except urllib.error.HTTPError as error:
        report.update({"http_status":error.code,"error":"Official public download refused"})
    except (urllib.error.URLError, TimeoutError, ValueError, zipfile.BadZipFile) as error:
        report["error_type"] = type(error).__name__
    (root / "acquisition-report.json").write_text(json.dumps(report, indent=2))
    outputs["acquisition-report.json"] = {"bytes":(root/"acquisition-report.json").stat().st_size,
                                         "sha256":digest(root/"acquisition-report.json")}
    print("ACQUISITION_REPORT", json.dumps(report), flush=True)
    print("ACQUISITION_RESULT_RECEIPT", json.dumps(publish(root, {"schema":"faithful-fly-artifacts-v1","files":outputs})), flush=True)

if __name__ == "__main__":
    main()
