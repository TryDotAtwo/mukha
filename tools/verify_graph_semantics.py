"""Independent streaming check of every retained source row and its CSR endpoints."""
import json
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.feather as feather

ROOT = Path(__file__).resolve().parents[1]


def main():
    start = time.monotonic()
    graph = ROOT / 'data/derived/malecns_v1_candidates'
    raw = ROOT / 'data/raw/malecns_v1'
    ids, ptr, col, weights, rows = [np.load(graph / (name + '.npy'), mmap_mode='r')
                                  for name in ('body_ids', 'indptr', 'indices', 'synapse_counts', 'source_rows')]
    annotations = feather.read_table(raw / 'body-annotations-male-cns-v1.0-minconf-0.5.feather').to_pandas()
    selected = annotations[(annotations['status'] == 'Traced') |
                           annotations['superclass'].fillna('').str.strip().ne('')]
    # Determine the source ID column from the immutable annotation schema.
    id_column = 'body' if 'body' in selected.columns else 'bodyId'
    expected_ids = np.sort(selected[id_column].to_numpy(dtype=np.uint64))
    if not np.array_equal(ids, expected_ids):
        raise ValueError('Population differs from independent selection')
    if len(ptr) != len(ids) + 1 or ptr[0] != 0 or ptr[-1] != len(col) or np.any(ptr[1:] < ptr[:-1]):
        raise ValueError('Invalid CSR row pointers')
    if len(rows) != len(col) or len(weights) != len(col) or np.any(col >= len(ids)):
        raise ValueError('Invalid CSR arrays')
    order = np.argsort(rows)
    sorted_rows = rows[order]
    if np.any(sorted_rows[1:] <= sorted_rows[:-1]):
        raise ValueError('Source row duplicated')
    population = set(map(int, ids))
    offset = checked = count_sum = 0
    with pa.memory_map(str(raw / 'connectome-weights-male-cns-v1.0-minconf-0.5.feather'), 'r') as source:
        reader = pa.ipc.open_file(source)
        for batch_index in range(reader.num_record_batches):
            batch = reader.get_batch(batch_index)
            pre, post, count = [batch.column(batch.schema.get_field_index(k)).to_numpy()
                                for k in ('body_pre', 'body_post', 'weight')]
            mask = np.isin(pre, ids) & np.isin(post, ids)
            expected_rows = np.flatnonzero(mask).astype(np.uint64) + offset
            end = checked + len(expected_rows)
            if not np.array_equal(sorted_rows[checked:end], expected_rows):
                raise ValueError(f'Missing or extra source rows in batch {batch_index}')
            positions = order[checked:end]
            actual_post = ids[np.searchsorted(ptr, positions, side='right') - 1]
            if not (np.array_equal(ids[col[positions]], pre[mask]) and
                    np.array_equal(actual_post, post[mask]) and
                    np.array_equal(weights[positions], count[mask])):
                raise ValueError(f'Endpoint or weight mismatch in batch {batch_index}')
            checked = end
            count_sum += int(count[mask].sum())
            offset += len(pre)
    if checked != len(rows):
        raise ValueError('Trailing source rows outside export')
    report = dict(passed=True, nodes=len(population), checked_edges=checked,
                  checked_source_rows=offset, retained_synapse_count_sum=count_sum,
                  elapsed_seconds=round(time.monotonic() - start, 3),
                  scope='all source rows and CSR endpoints; no physiological validation')
    (ROOT / 'reports/graph_semantic_verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
