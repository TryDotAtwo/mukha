"""Build a lossless, incoming-CSR candidate-neuron graph from pinned MaleCNS.

The population is Traced OR nonempty superclass, not a claim that every object
is one fully reconstructed biological neuron. Original source remains intact.
No thresholding, duplicate coalescing, or transmitter sign assignment occurs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.feather as feather

PROJECT = Path(__file__).resolve().parents[1]
EDGE_DTYPE = np.dtype([('pre', '<u4'), ('post', '<u4'), ('count', '<u8'), ('source_row', '<u8')])
POLICY = 'status == Traced OR nonempty(strip(superclass))'


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def select_nodes(annotations: pa.Table) -> tuple[pa.Table, pa.Table]:
    ids = annotations['bodyId']
    if ids.null_count or len(np.unique(ids.to_numpy())) != len(ids):
        raise ValueError('bodyId must be unique and non-null')
    if np.any(ids.to_numpy() < 0):
        raise ValueError('negative source ID')
    classes = pc.utf8_trim_whitespace(pc.fill_null(annotations['superclass'], ''))
    traced = pc.equal(pc.fill_null(annotations['status'], ''), 'Traced')
    classified = pc.not_equal(classes, '')
    selected = pc.or_(traced, classified)
    reasons = [
        'traced_and_classified' if a and b else 'traced_without_superclass' if a
        else 'classified_not_traced' if b else 'not_in_declared_population'
        for a, b in zip(traced.to_pylist(), classified.to_pylist())
    ]
    enriched = annotations.append_column('selection_reason', pa.array(reasons))
    nodes = enriched.filter(selected).sort_by('bodyId')
    if len(nodes) == 0 or len(nodes) >= 2**32:
        raise ValueError('population is empty or exceeds uint32 indexing')
    nodes = nodes.append_column('compact_index', pa.array(np.arange(len(nodes), dtype=np.uint32)))
    return nodes, enriched.filter(pc.invert(selected)).sort_by('bodyId')


def locate(ids: np.ndarray, sorted_ids: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if len(sorted_ids) == 0:
        return np.zeros(ids.shape, dtype=np.int64), np.zeros(ids.shape, dtype=bool)
    idx = np.searchsorted(sorted_ids, ids)
    found = (idx < len(sorted_ids)) & (sorted_ids[np.minimum(idx, len(sorted_ids)-1)] == ids)
    return idx, found


def build(annotations: pa.Table, graph_path: Path, out: Path,
          neurotransmitters: pa.Table | None = None, provenance: dict | None = None) -> dict:
    # Refuse overwrites; an interrupted directory remains explicitly incomplete.
    out.mkdir(parents=True, exist_ok=False)
    marker = out / 'INCOMPLETE'
    marker.write_text('Build not yet validated. Do not load.\n', encoding='utf-8')
    nodes, excluded = select_nodes(annotations)
    node_ids = nodes['bodyId'].to_numpy()
    all_ids = np.sort(annotations['bodyId'].to_numpy())
    feather.write_feather(nodes, out / 'nodes.feather', compression='zstd')
    feather.write_feather(excluded, out / 'excluded_annotations.feather', compression='zstd')
    if neurotransmitters is not None:
        nt = neurotransmitters.filter(pc.is_in(neurotransmitters['body'], value_set=nodes['bodyId']))
        feather.write_feather(nt, out / 'neurotransmitters.feather', compression='zstd')
    rows = contacts = kept = 0
    counts = np.zeros((3, 3), dtype=np.uint64)
    sums = np.zeros((3, 3), dtype=np.uint64)
    start = last = time.monotonic()
    temporary = out / 'edges.unsorted.bin'
    with temporary.open('wb') as f, pa.memory_map(str(graph_path), 'r') as source:
        reader = pa.ipc.open_file(source)
        if reader.schema.names != ['body_pre', 'body_post', 'weight']:
            raise ValueError('unexpected graph schema')
        for i in range(reader.num_record_batches):
            b = reader.get_batch(i)
            if any(c.null_count for c in b.columns):
                raise ValueError('null graph value')
            pre, post, weight = (c.to_numpy() for c in b.columns)
            if any(x.dtype != np.dtype('int64') for x in (pre, post, weight)):
                raise ValueError('source endpoints and weights must be int64')
            if np.any(weight <= 0) or np.any(pre < 0) or np.any(post < 0):
                raise ValueError('invalid endpoint or nonpositive weight')
            ip, fp = locate(pre, node_ids)
            iq, fq = locate(post, node_ids)
            _, ap = locate(pre, all_ids)
            _, aq = locate(post, all_ids)
            cp = np.where(fp, 0, np.where(ap, 1, 2))
            cq = np.where(fq, 0, np.where(aq, 1, 2))
            for j in range(3):
                for k in range(3):
                    m = (cp == j) & (cq == k)
                    counts[j, k] += np.uint64(np.count_nonzero(m))
                    sums[j, k] += weight[m].astype(np.uint64).sum()
            mask = fp & fq
            e = np.empty(int(mask.sum()), dtype=EDGE_DTYPE)
            e['pre'], e['post'] = ip[mask], iq[mask]
            e['count'] = weight[mask]
            e['source_row'] = np.flatnonzero(mask).astype(np.uint64) + rows
            e.tofile(f)
            kept += len(e)
            rows += len(weight)
            contacts += int(weight.astype(np.uint64).sum())
            if time.monotonic() - last > 10:
                print(json.dumps({'source_rows': rows, 'retained': kept}), flush=True)
                last = time.monotonic()
    if kept != int(counts[0, 0]) or int(counts.sum()) != rows or int(sums.sum()) != contacts:
        raise RuntimeError('source accounting mismatch')
    if kept:
        edges = np.memmap(temporary, mode='r', dtype=EDGE_DTYPE, shape=(kept,))
        order = np.lexsort((edges['source_row'], edges['pre'], edges['post']))
        destinations = edges['post'][order]
        degree = np.bincount(destinations, minlength=len(node_ids)).astype(np.uint64)
        # Incoming CSR: row=post, column=pre. Never transpose this convention.
        for name, field in [('indices', 'pre'), ('synapse_counts', 'count'), ('source_rows', 'source_row')]:
            target = np.lib.format.open_memmap(out / (name + '.npy'), mode='w+', dtype=EDGE_DTYPE[field], shape=(kept,))
            for begin in range(0, kept, 1 << 20):
                end = min(kept, begin + (1 << 20))
                target[begin:end] = edges[field][order[begin:end]]
            target.flush()
            del target
        self_edges = int(np.count_nonzero(edges['pre'] == edges['post']))
        out_degree = np.bincount(edges['pre'], minlength=len(node_ids))
        duplicate_pairs = int(np.count_nonzero((destinations[1:] == destinations[:-1]) &
            (edges['pre'][order[1:]] == edges['pre'][order[:-1]])))
        del edges, order, destinations
    else:
        degree = np.zeros(len(node_ids), dtype=np.uint64)
        out_degree = degree.copy()
        self_edges = duplicate_pairs = 0
        for name, dt in [('indices', '<u4'), ('synapse_counts', '<u8'), ('source_rows', '<u8')]:
            np.save(out / (name + '.npy'), np.array([], dtype=dt))
    ptr = np.empty(len(node_ids) + 1, dtype='<u8')
    ptr[0] = 0
    np.cumsum(degree, out=ptr[1:])
    np.save(out / 'indptr.npy', ptr)
    np.save(out / 'body_ids.npy', node_ids.astype('<u8'))
    temporary.unlink()
    files = {p.name: {'bytes': p.stat().st_size, 'sha256': sha256(p)}
             for p in sorted(out.iterdir()) if p.is_file() and p.name != 'INCOMPLETE'}
    report = {
        'format': 'flyrocket.incoming-csr.v1', 'population_policy': POLICY,
        'population_claim': 'candidate neural objects, not a count of proven complete biological neurons',
        'orientation': 'row=postsynaptic; indices=presynaptic',
        'source_provenance': provenance or {}, 'nodes': len(nodes), 'edges': kept,
        'retained_synapse_count_sum': int(sums[0, 0]),
        'self_edges_preserved': self_edges, 'duplicate_pair_rows_preserved': duplicate_pairs,
        'isolated_nodes_preserved': int(np.count_nonzero((degree == 0) & (out_degree == 0))),
        'excluded_annotation_rows': len(excluded),
        'selection_reasons': pc.value_counts(nodes['selection_reason']).to_pylist(),
        'boundary_category_order': ['included', 'annotated_outside_population', 'unannotated_segment'],
        'all_source_rows': rows, 'all_source_synapse_count_sum': contacts,
        'source_rows_by_pre_post_category': counts.tolist(),
        'source_counts_by_pre_post_category': sums.tolist(),
        'additional_weight_threshold': None, 'transmitter_signs_assigned': False,
        'files': files, 'elapsed_seconds': round(time.monotonic() - start, 3),
    }
    (out / 'manifest.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    marker.unlink()
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=PROJECT/'data/derived/malecns_v1_candidates')
    args = p.parse_args()
    lock_path = PROJECT/'reports/malecns_source_lock.json'
    lock = json.loads(lock_path.read_text(encoding='utf-8'))
    paths = {}
    for item in lock['files']:
        path = PROJECT/item['local_path']
        if path.stat().st_size != item['bytes'] or sha256(path) != item['sha256']:
            raise ValueError('source verification failed: '+item['name'])
        paths[item['name']] = path
    result = build(
        feather.read_table(paths['body-annotations-male-cns-v1.0-minconf-0.5.feather']),
        paths['connectome-weights-male-cns-v1.0-minconf-0.5.feather'], args.output,
        feather.read_table(paths['body-neurotransmitters-male-cns-v1.0.feather']),
        {'dataset': lock['dataset'], 'source_lock_sha256': sha256(lock_path), 'files': lock['files']})
    report_path = PROJECT/'reports/malecns_runtime_graph.json'
    report_path.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ['nodes', 'edges', 'retained_synapse_count_sum', 'elapsed_seconds']}))


if __name__ == '__main__':
    main()
