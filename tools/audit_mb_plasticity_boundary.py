"""Anatomical MB population boundary; does not enable plasticity."""
from collections import defaultdict
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd
import pyarrow as pa


ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / 'data/derived/malecns_v1_candidates'
OUT = ROOT / 'reports/malecns_mb_plasticity_boundary.json'
CLASSES = ('Kenyon_Cell', 'MBON', 'DAN')


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def run():
    manifest_path = GRAPH / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    raw_edges = ROOT / 'data/raw/malecns_v1/connectome-weights-male-cns-v1.0-minconf-0.5.feather'
    raw_columns = pa.ipc.open_file(raw_edges).schema.names
    assert raw_columns == ['body_pre', 'body_post', 'weight']
    checked = ['nodes.feather', 'neurotransmitters.feather', 'body_ids.npy',
               'indptr.npy', 'indices.npy', 'synapse_counts.npy', 'source_rows.npy']
    for name in checked:
        path = GRAPH / name
        record = manifest['files'][name]
        assert path.stat().st_size == record['bytes'] and sha(path) == record['sha256'], name

    nodes = pd.read_feather(GRAPH / 'nodes.feather', columns=['bodyId', 'compact_index',
                                                             'class', 'type', 'instance'])
    n = len(nodes)
    assert n == manifest['nodes'] and np.array_equal(nodes.compact_index.to_numpy(),
                                                    np.arange(n, dtype=np.uint32))
    body = np.load(GRAPH / 'body_ids.npy', mmap_mode='r')
    assert np.array_equal(nodes.bodyId.to_numpy(), body)
    ptr = np.load(GRAPH / 'indptr.npy', mmap_mode='r')
    pre = np.load(GRAPH / 'indices.npy', mmap_mode='r')
    counts = np.load(GRAPH / 'synapse_counts.npy', mmap_mode='r')
    source = np.load(GRAPH / 'source_rows.npy', mmap_mode='r')
    assert len(ptr) == n+1 and int(ptr[-1]) == manifest['edges']
    assert len(pre) == len(counts) == len(source) == manifest['edges']

    labels = nodes['class'].fillna('').to_numpy()
    membership = {name: labels == name for name in CLASSES}
    chemistry = pd.read_feather(GRAPH / 'neurotransmitters.feather',
                                columns=['body', 'consensus_nt', 'predicted_nt', 'ground_truth'])
    assert chemistry.body.is_unique
    annotated = nodes[['bodyId', 'class', 'instance']].merge(
        chemistry, left_on='bodyId', right_on='body', how='left', validate='one_to_one')
    chemistry_counts = {}
    for name in CLASSES:
        values = annotated.loc[membership[name], 'consensus_nt'].fillna('missing')
        chemistry_counts[name] = {str(k): int(v) for k, v in values.value_counts().items()}
    dan_exceptions = annotated.loc[membership['DAN'] & annotated.consensus_nt.ne('dopamine'),
                                   ['bodyId', 'instance', 'consensus_nt', 'predicted_nt', 'ground_truth']]
    by_pair = defaultdict(lambda: {'edge_rows': 0, 'contacts': 0,
                                   'presynaptic_cells': set(), 'postsynaptic_cells': set()})
    mbons = []
    for post_class in CLASSES:
        for post in np.flatnonzero(membership[post_class]):
            lo, hi = int(ptr[post]), int(ptr[post+1])
            segment = np.asarray(pre[lo:hi])
            if segment.size:
                assert int(segment.max()) < n
            if post_class == 'MBON':
                item = {'bodyId': int(body[post]), 'type': nodes.at[post, 'type'],
                        'instance': nodes.at[post, 'instance']}
            for pre_class in CLASSES:
                mask = membership[pre_class][segment]
                if not mask.any():
                    if post_class == 'MBON':
                        item[pre_class + '_edge_rows'] = 0
                        item[pre_class + '_contacts'] = 0
                    continue
                indices = np.flatnonzero(mask) + lo
                total = int(np.sum(counts[indices], dtype=np.uint64))
                entry = by_pair[(pre_class, post_class)]
                entry['edge_rows'] += int(len(indices))
                entry['contacts'] += total
                entry['presynaptic_cells'].update(map(int, pre[indices]))
                entry['postsynaptic_cells'].add(int(post))
                if post_class == 'MBON':
                    item[pre_class + '_edge_rows'] = int(len(indices))
                    item[pre_class + '_contacts'] = total
            if post_class == 'MBON':
                mbons.append(item)

    pairs = []
    for (pre_class, post_class), entry in sorted(by_pair.items()):
        pairs.append({'presynaptic_class': pre_class, 'postsynaptic_class': post_class,
                      'edge_rows': entry['edge_rows'], 'contacts': entry['contacts'],
                      'distinct_presynaptic_cells': len(entry['presynaptic_cells']),
                      'distinct_postsynaptic_cells': len(entry['postsynaptic_cells'])})
    report = {'scope': 'Exact anatomical class-pair counts on accepted MaleCNS CSR; no plasticity rule, sign, receptor, dopamine compartment, or functional transfer assigned',
              'graph_manifest_sha256': sha(manifest_path),
              'raw_edge_columns': raw_columns,
              'raw_edge_sha256': sha(raw_edges),
              'checked_file_sha256': {name: manifest['files'][name]['sha256'] for name in checked},
              'population_counts': {name: int(membership[name].sum()) for name in CLASSES},
              'source_chemistry_counts': chemistry_counts,
              'instance_compartment_label_coverage': {
                  name: {'with_parenthesized_label': int(annotated.loc[membership[name], 'instance'].fillna('').str.contains('(', regex=False).sum()),
                         'total': int(membership[name].sum())}
                  for name in CLASSES},
              'dan_non_dopamine_consensus': dan_exceptions.where(pd.notna(dan_exceptions), None).to_dict('records'),
              'pairs': pairs, 'mbon_inputs': mbons,
              'source_rows_preserved_in_graph': True,
              'plasticity_enabled': False, 'biological_gate_passed': False}
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'report': str(OUT), 'populations': report['population_counts'],
                      'pairs': pairs}, indent=2))


if __name__ == '__main__':
    run()
