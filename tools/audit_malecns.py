"""Stream-audit all downloaded MaleCNS graph rows without building a subset.

Category counts describe completeness; they never filter or rewrite the graph.
The source lock is revalidated before an audit result is published.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.feather as feather

from fetch_malecns import digest_file

PROJECT = Path(__file__).resolve().parents[1]
CATEGORY_NAMES = (
    "absent_from_annotation_table",
    "annotation_row_without_superclass",
    "annotation_row_with_nonempty_superclass",
)


def endpoint_categories(ids: np.ndarray, annotation_ids: np.ndarray, categories: np.ndarray) -> np.ndarray:
    index = np.searchsorted(annotation_ids, ids)
    clipped = np.minimum(index, len(annotation_ids) - 1)
    found = (index < len(annotation_ids)) & (annotation_ids[clipped] == ids)
    return np.where(found, categories[clipped], 0).astype(np.uint8)


def audit_graph(path: Path, annotation_ids: np.ndarray, categories: np.ndarray) -> dict:
    edge_counts = np.zeros((3, 3), dtype=np.int64)
    contact_counts = np.zeros((3, 3), dtype=np.int64)
    rows = contacts = self_rows = self_contacts = bad_weights = null_values = 0
    min_id, max_id = None, None
    start = last_print = time.monotonic()
    with pa.memory_map(str(path), "r") as source:
        reader = pa.ipc.open_file(source)
        if reader.schema.names != ["body_pre", "body_post", "weight"]:
            raise ValueError(f"Unexpected graph schema: {reader.schema}")
        for batch_i in range(reader.num_record_batches):
            batch = reader.get_batch(batch_i)
            null_values += sum(column.null_count for column in batch.columns)
            if null_values:
                raise ValueError("Graph contains null endpoints/weights")
            pre, post, weight = (column.to_numpy() for column in batch.columns)
            rows += len(weight)
            contacts += int(weight.sum(dtype=np.int64))
            bad_weights += int(np.count_nonzero(weight <= 0))
            batch_min, batch_max = int(min(pre.min(), post.min())), int(max(pre.max(), post.max()))
            min_id = batch_min if min_id is None else min(min_id, batch_min)
            max_id = batch_max if max_id is None else max(max_id, batch_max)
            self_mask = pre == post
            self_rows += int(np.count_nonzero(self_mask))
            self_contacts += int(weight[self_mask].sum(dtype=np.int64))
            pre_category = endpoint_categories(pre, annotation_ids, categories)
            post_category = endpoint_categories(post, annotation_ids, categories)
            pair_category = pre_category * 3 + post_category
            edge_counts += np.bincount(pair_category, minlength=9).reshape(3, 3)
            for pair_i in range(9):
                contact_counts.flat[pair_i] += weight[pair_category == pair_i].sum(dtype=np.int64)
            now = time.monotonic()
            if now - last_print >= 10:
                print(f"Audited {rows:,} rows ({batch_i+1}/{reader.num_record_batches} batches)", flush=True)
                last_print = now
    if int(edge_counts.sum()) != rows or int(contact_counts.sum()) != contacts:
        raise RuntimeError("Accounting does not reconcile")
    if bad_weights:
        raise ValueError(f"Nonpositive source weights: {bad_weights}")
    return {
        "all_graph_rows": rows,
        "sum_of_source_weights": contacts,
        "self_connection_rows": self_rows,
        "self_connection_sum_of_weights": self_contacts,
        "endpoint_id_range": [min_id, max_id],
        "category_order": list(CATEGORY_NAMES),
        "edge_rows_by_pre_post_category": edge_counts.tolist(),
        "sum_of_weights_by_pre_post_category": contact_counts.tolist(),
        "rows_accounted_for": int(edge_counts.sum()),
        "rows_removed": 0,
        "weights_modified": 0,
        "unique_segment_count": None,
        "unique_segment_count_note": "Not computed by this bounded-memory audit; segment IDs must not be counted as identified biological neurons.",
        "elapsed_seconds": round(time.monotonic() - start, 3),
    }


def main() -> None:
    lock_path = PROJECT / "reports" / "malecns_source_lock.json"
    source_lock = json.loads(lock_path.read_text(encoding="utf-8"))
    sources = {}
    for item in source_lock["files"]:
        path = PROJECT / item["local_path"]
        sha, md5 = digest_file(path)
        if sha != item["sha256"] or md5 != item["source_md5_base64"] or path.stat().st_size != item["bytes"]:
            raise ValueError(f"Source verification failed: {item['name']}")
        sources[item["name"]] = path
    annotations = feather.read_table(sources["body-annotations-male-cns-v1.0-minconf-0.5.feather"])
    ids = annotations["bodyId"].to_numpy()
    if annotations["bodyId"].null_count or len(np.unique(ids)) != len(ids):
        raise ValueError("Annotation body IDs must be non-null and unique")
    superclasses = annotations["superclass"].to_pylist()
    category = np.array([2 if value is not None and value.strip() else 1 for value in superclasses], dtype=np.uint8)
    order = np.argsort(ids)
    annotation_summary = {
        "rows": annotations.num_rows,
        "with_nonempty_superclass": int(np.count_nonzero(category == 2)),
        "without_superclass": int(np.count_nonzero(category == 1)),
        "superclass_counts": pc.value_counts(annotations["superclass"]).to_pylist(),
        "status_counts": pc.value_counts(annotations["status"]).to_pylist(),
    }
    neurotransmitters = feather.read_table(sources["body-neurotransmitters-male-cns-v1.0.feather"])
    graph = audit_graph(sources["connectome-weights-male-cns-v1.0-minconf-0.5.feather"], ids[order], category[order])
    report = {
        "dataset": source_lock["dataset"],
        "source_lock": "reports/malecns_source_lock.json",
        "scope": "Descriptive audit of the full published source graph; no runtime graph, biological model, or training run created.",
        "annotations": annotation_summary,
        "neurotransmitter_rows": neurotransmitters.num_rows,
        "neurotransmitter_sign_rule": "none; original predictions retained without assigning universal excitatory/inhibitory signs",
        "graph": graph,
        "runtime_node_selection": "not yet applied; unannotated segments and fragments require explicit accounting",
    }
    output = PROJECT / "reports" / "malecns_source_audit.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"annotations": annotation_summary["rows"], "with_superclass": annotation_summary["with_nonempty_superclass"], "graph": graph}, indent=2), flush=True)


if __name__ == "__main__":
    main()
