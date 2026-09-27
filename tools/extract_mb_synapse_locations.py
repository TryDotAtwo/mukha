"""Stream pinned MaleCNS synapse partner batches; retain only KC->MBON contacts.

This is anatomical evidence, not a plasticity assignment. Run with --max-batches
for a bounded pilot, then without it to resume until the source is exhausted.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import fsspec
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import requests

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / 'data/derived/malecns_v1_candidates'
OUT = ROOT / 'data/derived/mb_synapse_locations_v1'
URL = ('https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/'
       'flat-connectome/syn-partners-male-cns-v1.0-minconf-0.5.feather')
EXPECTED = 463640


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def reconcile_pairs(state, kc, mbon):
    body = np.load(GRAPH / 'body_ids.npy', mmap_mode='r')
    ptr = np.load(GRAPH / 'indptr.npy', mmap_mode='r')
    pre = np.load(GRAPH / 'indices.npy', mmap_mode='r')
    weight = np.load(GRAPH / 'synapse_counts.npy', mmap_mode='r')
    expected = Counter()
    mbon_indices = np.flatnonzero(np.isin(body, list(mbon)))
    for post_index in mbon_indices:
        lo, hi = int(ptr[post_index]), int(ptr[post_index + 1])
        for edge in range(lo, hi):
            pre_id = int(body[pre[edge]])
            if pre_id in kc:
                expected[(pre_id, int(body[post_index]))] += int(weight[edge])
    observed = Counter()
    rois = Counter()
    for entry in state['shards']:
        path = OUT / entry['file']
        table = pq.read_table(path, columns=['body_pre', 'body_post', 'primary_post'])
        observed.update(zip(table['body_pre'].to_pylist(), table['body_post'].to_pylist()))
        rois.update(table['primary_post'].to_pylist())
    mismatches = [(a, b, expected[(a,b)], observed[(a,b)])
                  for a,b in expected.keys() | observed.keys()
                  if expected[(a,b)] != observed[(a,b)]]
    result = {'source': state['source'], 'graph_manifest_sha256': state['graph_manifest_sha256'],
              'processed_batches': state['next_batch'], 'contacts': sum(observed.values()),
              'graph_contacts': sum(expected.values()), 'graph_pairs': len(expected),
              'observed_pairs': len(observed), 'pair_mismatch_count': len(mismatches),
              'first_pair_mismatches': sorted(mismatches)[:20],
              'primary_post_counts': dict(sorted(rois.items())),
              'scope': 'Synapse coordinates and source ROI labels only; no local plasticity rule or biological validation'}
    path = OUT / 'reconciliation.json'
    path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    if mismatches or result['contacts'] != EXPECTED:
        raise RuntimeError(f'Per-pair reconciliation failed; inspect {path}')
    return result


def run(max_batches, block_mib):
    source = requests.head(URL, timeout=30).headers
    identity = {'url': URL, 'content_length': int(source['Content-Length']),
                'etag': source['ETag'], 'x_goog_hash': source.get('x-goog-hash')}
    assert identity['content_length'] == 6777179098
    nodes = pd.read_feather(GRAPH / 'nodes.feather', columns=['bodyId', 'class'])
    kc = set(map(int, nodes.loc[nodes['class'].eq('Kenyon_Cell'), 'bodyId']))
    mbon = set(map(int, nodes.loc[nodes['class'].eq('MBON'), 'bodyId']))
    assert len(kc) == 4064 and len(mbon) == 97
    graph_manifest = digest(GRAPH / 'manifest.json')
    OUT.mkdir(parents=True, exist_ok=True)
    state_path = OUT / 'progress.json'
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding='utf-8'))
        assert state['source'] == identity and state['graph_manifest_sha256'] == graph_manifest
        assert 0 <= state['next_batch'] <= 4759
        assert len({x['batch'] for x in state['shards']}) == len(state['shards'])
        verified_rows = 0
        for entry in state['shards']:
            assert 0 <= entry['batch'] < state['next_batch']
            path = OUT / entry['file']
            assert path.name == f"batch-{entry['batch']:05d}.parquet"
            assert digest(path) == entry['sha256'], path
            assert pq.ParquetFile(path).metadata.num_rows == entry['rows'], path
            verified_rows += entry['rows']
        assert verified_rows == state['rows']
    else:
        assert not list(OUT.iterdir()), 'Unrecognized output files need inspection'
        state = {'source': identity, 'graph_manifest_sha256': graph_manifest,
                 'next_batch': 0, 'rows': 0, 'shards': []}

    with fsspec.open(URL, 'rb', block_size=block_mib << 20) as stream:
        reader = pa.ipc.open_file(stream)
        assert reader.schema.names == ['x_pre', 'y_pre', 'z_pre', 'body_pre',
            'conf_pre', 'x_post', 'y_post', 'z_post', 'body_post', 'conf_post', 'primary_post']
        stop = reader.num_record_batches
        if max_batches is not None:
            stop = min(stop, state['next_batch'] + max_batches)
        kc_values = pa.array(sorted(kc), type=pa.int64())
        mbon_values = pa.array(sorted(mbon), type=pa.int64())
        for index in range(state['next_batch'], stop):
            batch = reader.get_batch(index)
            keep = pc.and_(pc.is_in(batch.column('body_pre'), value_set=kc_values),
                           pc.is_in(batch.column('body_post'), value_set=mbon_values))
            selected = pa.Table.from_batches([batch]).filter(keep)
            name = f'batch-{index:05d}.parquet'
            if selected.num_rows:
                path = OUT / name
                if path.exists():
                    assert pq.read_table(path).equals(selected), f'Orphan shard mismatch: {path}'
                else:
                    pq.write_table(selected, path, compression='zstd')
                state['shards'].append({'batch': index, 'file': name,
                                        'rows': selected.num_rows, 'sha256': digest(path)})
            state['rows'] += selected.num_rows
            state['next_batch'] = index + 1
            temporary = OUT / 'progress.json.tmp'
            temporary.write_text(json.dumps(state, indent=2), encoding='utf-8')
            temporary.replace(state_path)
            if (index + 1) % 20 == 0:
                print(json.dumps({'next_batch': index + 1, 'of': reader.num_record_batches,
                                  'matched_contacts': state['rows']}), flush=True)
        if state['next_batch'] == reader.num_record_batches:
            report = reconcile_pairs(state, kc, mbon)
            print('COMPLETE', report['contacts'], report['graph_pairs'], flush=True)
        else:
            print('PARTIAL', state['next_batch'], reader.num_record_batches,
                  state['rows'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-batches', type=int, default=None)
    parser.add_argument('--block-mib', type=int, default=32)
    args = parser.parse_args()
    if args.max_batches is not None and args.max_batches <= 0:
        parser.error('--max-batches must be positive')
    if not 1 <= args.block_mib <= 128:
        parser.error('--block-mib must be between 1 and 128')
    run(args.max_batches, args.block_mib)
