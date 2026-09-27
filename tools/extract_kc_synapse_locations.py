"""Resume a generation-pinned KC->KC contact extraction from MaleCNS v1.0.

The complete output is anatomical evidence only. No receptor, axonal segment,
synaptic sign or plasticity state is inferred here.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

import fsspec
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import requests

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "data/derived/malecns_v1_candidates"
OUT = ROOT / "data/derived/kc_synapse_locations_v1"
BASE_URL = ("https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/"
            "flat-connectome/syn-partners-male-cns-v1.0-minconf-0.5.feather")
GENERATION = "1780494942562468"
URL = BASE_URL + "?generation=" + GENERATION
EXPECTED_BATCHES = 4759
EXPECTED_CONTACTS = 1153845
EXPECTED_PAIRS = 642933
CHUNK = 20
SCHEMA = ["x_pre", "y_pre", "z_pre", "body_pre", "conf_pre", "x_post",
          "y_post", "z_post", "body_post", "conf_post", "primary_post"]


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def source_identity():
    response = requests.head(URL, timeout=30)
    response.raise_for_status()
    identity = {"url": BASE_URL, "generation": GENERATION,
                "content_length": int(response.headers["Content-Length"]),
                "etag": response.headers["ETag"],
                "x_goog_hash": response.headers.get("x-goog-hash")}
    assert response.headers.get("x-goog-generation") == GENERATION
    assert identity["content_length"] == 6777179098
    return identity


def expected_pairs(kc_mask):
    body = np.load(GRAPH / "body_ids.npy", mmap_mode="r")
    ptr = np.load(GRAPH / "indptr.npy", mmap_mode="r")
    pre = np.load(GRAPH / "indices.npy", mmap_mode="r")
    weights = np.load(GRAPH / "synapse_counts.npy", mmap_mode="r")
    result = {}
    for post in np.flatnonzero(kc_mask):
        lo, hi = int(ptr[post]), int(ptr[post + 1])
        segment = np.asarray(pre[lo:hi])
        for local in np.flatnonzero(kc_mask[segment]):
            edge = lo + int(local)
            pair = (int(body[int(pre[edge])]), int(body[post]))
            assert pair not in result, "CSR has duplicate KC pair rows"
            result[pair] = int(weights[edge])
    assert len(result) == EXPECTED_PAIRS
    assert sum(result.values()) == EXPECTED_CONTACTS
    return result


def reconcile(state, kc_mask):
    expected = expected_pairs(kc_mask)
    observed = Counter()
    rois = Counter()
    for entry in state["chunks"]:
        if not entry["rows"]:
            continue
        table = pq.read_table(OUT / entry["file"], columns=["body_pre", "body_post", "primary_post"])
        observed.update(zip(table["body_pre"].to_pylist(), table["body_post"].to_pylist()))
        rois.update(table["primary_post"].to_pylist())
    different = [(a, b, expected.get((a, b), 0), observed.get((a, b), 0))
                 for a, b in expected.keys() | observed.keys()
                 if expected.get((a, b), 0) != observed.get((a, b), 0)]
    report = {"scope": "All pinned MaleCNS KC-to-KC contact coordinates and source ROI labels; anatomy only",
              "source": state["source"], "graph_manifest_sha256": state["graph_manifest_sha256"],
              "processed_batches": state["next_batch"],
              "observed_contacts": sum(observed.values()), "expected_contacts": sum(expected.values()),
              "observed_pairs": len(observed), "expected_pairs": len(expected),
              "pair_mismatch_count": len(different), "first_pair_mismatches": sorted(different)[:20],
              "primary_post_counts": {str(key): value for key, value in sorted(
                  rois.items(), key=lambda item: str(item[0]))},
              "complete_and_reconciled": not different and sum(observed.values()) == EXPECTED_CONTACTS}
    (OUT / "reconciliation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not report["complete_and_reconciled"]:
        raise RuntimeError("KC contact reconciliation failed")
    return report


def run(max_chunks, block_mib):
    identity = source_identity()
    manifest_path = GRAPH / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name in ("nodes.feather", "body_ids.npy", "indptr.npy", "indices.npy", "synapse_counts.npy"):
        path = GRAPH / name
        assert path.stat().st_size == manifest["files"][name]["bytes"]
        assert sha(path) == manifest["files"][name]["sha256"]
    nodes = pd.read_feather(GRAPH / "nodes.feather", columns=["bodyId", "class"])
    body = np.load(GRAPH / "body_ids.npy", mmap_mode="r")
    assert np.array_equal(nodes.bodyId.to_numpy(), body)
    kc_mask = nodes["class"].eq("Kenyon_Cell").to_numpy()
    assert int(kc_mask.sum()) == 4064
    kc_values = pa.array(sorted(map(int, body[kc_mask])), type=pa.int64())
    OUT.mkdir(parents=True, exist_ok=True)
    progress_path = OUT / "progress.json"
    if progress_path.exists():
        state = json.loads(progress_path.read_text(encoding="utf-8"))
        assert state["source"] == identity and state["graph_manifest_sha256"] == sha(manifest_path)
        assert state["next_batch"] == sum(x["stop"] - x["start"] for x in state["chunks"])
        assert state["rows"] == sum(x["rows"] for x in state["chunks"])
        for entry in state["chunks"]:
            if entry["rows"]:
                path = OUT / entry["file"]
                assert path.stat().st_size == entry["bytes"] and sha(path) == entry["sha256"]
                assert pq.ParquetFile(path).metadata.num_rows == entry["rows"]
    else:
        assert not list(OUT.iterdir()), "Unrecognized extraction state"
        state = {"source": identity, "graph_manifest_sha256": sha(manifest_path),
                 "next_batch": 0, "rows": 0, "chunks": []}
    start_time = time.monotonic()
    with fsspec.open(URL, "rb", block_size=block_mib << 20) as stream:
        reader = pa.ipc.open_file(stream)
        assert reader.schema.names == SCHEMA
        assert reader.num_record_batches == EXPECTED_BATCHES
        limit = EXPECTED_BATCHES if max_chunks is None else min(
            EXPECTED_BATCHES, state["next_batch"] + max_chunks * CHUNK)
        while state["next_batch"] < limit:
            start = state["next_batch"]
            stop = min(start + CHUNK, limit)
            selected = []
            for index in range(start, stop):
                batch = reader.get_batch(index)
                mask = pc.and_(pc.is_in(batch.column("body_pre"), value_set=kc_values),
                               pc.is_in(batch.column("body_post"), value_set=kc_values))
                part = pa.Table.from_batches([batch]).filter(mask)
                if part.num_rows:
                    selected.append(part)
            rows = sum(part.num_rows for part in selected)
            entry = {"start": start, "stop": stop, "rows": rows}
            if rows:
                combined = pa.concat_tables(selected)
                name = f"contacts-{start:05d}-{stop:05d}.parquet"
                final = OUT / name
                if final.exists():
                    assert pq.read_table(final).equals(combined), f"orphan chunk mismatch: {name}"
                else:
                    temporary = OUT / (name + ".tmp")
                    pq.write_table(combined, temporary, compression="zstd")
                    temporary.replace(final)
                entry.update({"file": name, "bytes": final.stat().st_size, "sha256": sha(final)})
            state["chunks"].append(entry)
            state["rows"] += rows
            state["next_batch"] = stop
            temporary = OUT / "progress.json.tmp"
            temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
            temporary.replace(progress_path)
            print(json.dumps({"next_batch": stop, "of": EXPECTED_BATCHES,
                              "contacts": state["rows"], "elapsed_s": round(time.monotonic()-start_time, 1)}), flush=True)
    if state["next_batch"] == EXPECTED_BATCHES:
        report = reconcile(state, kc_mask)
        print("COMPLETE", report["observed_contacts"], report["observed_pairs"], flush=True)
    else:
        print("PARTIAL", state["next_batch"], state["rows"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-chunks", type=int, default=None)
    parser.add_argument("--block-mib", type=int, default=16)
    args = parser.parse_args()
    if args.max_chunks is not None and args.max_chunks <= 0:
        parser.error("--max-chunks must be positive")
    if not 1 <= args.block_mib <= 64:
        parser.error("--block-mib must be 1..64")
    run(args.max_chunks, args.block_mib)
