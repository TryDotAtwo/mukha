"""Reconcile every extracted KC->MBON contact with the pinned MaleCNS CSR."""
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / 'data/derived/malecns_v1_candidates'
EXTRACT = ROOT / 'data/derived/mb_synapse_locations_v1/molab_full'
OUT = ROOT / 'reports/malecns_mb_synapse_reconciliation.json'
PARTS = ('00000-00100', '00100-04759')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def run():
    nodes = pd.read_feather(GRAPH / 'nodes.feather', columns=['bodyId', 'class'])
    body = np.load(GRAPH / 'body_ids.npy', mmap_mode='r')
    assert np.array_equal(body, nodes.bodyId.to_numpy())
    labels = nodes['class'].fillna('').to_numpy()
    kc = set(map(int, body[labels == 'Kenyon_Cell']))
    mbon = set(map(int, body[labels == 'MBON']))
    assert len(kc) == 4064 and len(mbon) == 97
    ptr = np.load(GRAPH / 'indptr.npy', mmap_mode='r')
    pre = np.load(GRAPH / 'indices.npy', mmap_mode='r')
    weight = np.load(GRAPH / 'synapse_counts.npy', mmap_mode='r')
    expected = Counter()
    source_rows = 0
    for post_index in np.flatnonzero(labels == 'MBON'):
        lo, hi = int(ptr[post_index]), int(ptr[post_index + 1])
        for edge in range(lo, hi):
            pre_id = int(body[pre[edge]])
            if pre_id in kc:
                expected[(pre_id, int(body[post_index]))] += int(weight[edge])
                source_rows += 1
    assert source_rows == 61210 and sum(expected.values()) == 463640
    observed = Counter()
    rois = Counter()
    files = []
    prior_tables = []
    source_identity = None
    for index, name in enumerate(PARTS):
        report_path = EXTRACT / f'report-{name}.json'
        data_path = EXTRACT / f'contacts-{name}.parquet'
        record = json.loads(report_path.read_text(encoding='utf-8'))
        assert record['start_batch'] == (0 if index == 0 else 100)
        assert record['stop_batch'] == (100 if index == 0 else 4759)
        if source_identity is None:
            source_identity = record['source']
        assert record['source'] == source_identity
        assert data_path.stat().st_size == record['bytes'] and sha(data_path) == record['sha256']
        table = pq.read_table(data_path)
        prior_tables.append(table)
        assert table.num_rows == record['contacts']
        assert set(table.column_names) == {'x_pre','y_pre','z_pre','body_pre','conf_pre',
             'x_post','y_post','z_post','body_post','conf_post','primary_post'}
        for column in ('x_pre','y_pre','z_pre','x_post','y_post','z_post'):
            assert table[column].null_count == 0
        pre_ids = table['body_pre'].to_pylist()
        post_ids = table['body_post'].to_pylist()
        assert set(pre_ids) <= kc and set(post_ids) <= mbon
        observed.update(zip(pre_ids, post_ids))
        rois.update(table['primary_post'].to_pylist())
        files.append({'data':data_path.relative_to(ROOT).as_posix(),
                      'data_sha256':record['sha256'],
                      'report':report_path.relative_to(ROOT).as_posix(),
                      'report_sha256':sha(report_path), 'contacts':table.num_rows})
    pinned_report_path = EXTRACT / 'report-00000-04759.json'
    pinned_data_path = EXTRACT / 'contacts-00000-04759.parquet'
    pinned_report = json.loads(pinned_report_path.read_text(encoding='utf-8'))
    assert pinned_report['start_batch'] == 0 and pinned_report['stop_batch'] == 4759
    assert pinned_report['source']['generation']
    assert pinned_report['source']['pinned_url'].endswith(
        '?generation=' + pinned_report['source']['generation'])
    assert pinned_data_path.stat().st_size == pinned_report['bytes']
    assert sha(pinned_data_path) == pinned_report['sha256']
    pinned = pq.read_table(pinned_data_path)
    assert pinned.num_rows == pinned_report['contacts'] == 463640
    assert pinned.schema == prior_tables[0].schema
    same_rows_in_source_order = pinned.equals(pa.concat_tables(prior_tables))
    if not same_rows_in_source_order:
        raise RuntimeError('Pinned full extraction differs from prior two-part extraction')
    mismatches = [(a, b, expected[(a,b)], observed[(a,b)])
                  for a,b in expected.keys() | observed.keys()
                  if expected[(a,b)] != observed[(a,b)]]
    result = {'scope':'Full published MaleCNS KC->MBON synapse partner positions and ROI labels; anatomical only',
              'source':pinned_report['source'],'graph_manifest_sha256':sha(GRAPH/'manifest.json'),
              'files':files,'source_rows':source_rows,'expected_pairs':len(expected),
              'observed_pairs':len(observed),'expected_contacts':sum(expected.values()),
              'observed_contacts':sum(observed.values()),
              'pair_mismatch_count':len(mismatches),'pair_mismatch_examples':sorted(mismatches)[:20],
              'pinned_full_file':{'data':pinned_data_path.relative_to(ROOT).as_posix(),
                  'data_sha256':pinned_report['sha256'],
                  'report':pinned_report_path.relative_to(ROOT).as_posix(),
                  'report_sha256':sha(pinned_report_path),
                  'same_rows_in_source_order_as_prior_parts':same_rows_in_source_order},
              'primary_post_counts':dict(sorted(rois.items())),
              'plasticity_enabled':False,'biological_gate_passed':False}
    OUT.write_text(json.dumps(result,indent=2),encoding='utf-8')
    if mismatches or result['observed_contacts'] != 463640:
        raise RuntimeError(f'Contact reconciliation failed; inspect {OUT}')
    print(json.dumps({'pairs':len(expected),'contacts':sum(observed.values()),
                      'mismatches':len(mismatches),'rois':len(rois),'report':str(OUT)},indent=2))


if __name__ == '__main__':
    run()
