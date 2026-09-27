"""Assess the anatomical boundary for Handler 2019 gamma-4 plasticity transfer.

This does not fit, enable, or validate a plasticity rule.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / 'data/derived/malecns_v1_candidates'
CONTACTS = ROOT / 'data/derived/mb_synapse_locations_v1/molab_full'
OUT = ROOT / 'reports/malecns_handler_gamma4_transfer.json'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def run():
    nodes = pd.read_feather(GRAPH / 'nodes.feather')
    body = np.load(GRAPH / 'body_ids.npy', mmap_mode='r')
    assert np.array_equal(body, nodes.bodyId.to_numpy())
    klass = nodes['class'].fillna('').to_numpy()
    names = nodes.instance.fillna('')
    target = nodes[(klass == 'MBON') & names.str.fullmatch(r'MBON05\(y4>y1y2\)_[LR]')]
    pam08 = nodes[(klass == 'DAN') & names.str.fullmatch(r'PAM08\(y4\)_[LR]')]
    pam07 = nodes[(klass == 'DAN') & names.str.fullmatch(r'PAM07\(y4<y1y2\)_[LR]')]
    assert len(target) == 2 and len(pam08) > 0 and len(pam07) > 0
    assert nodes.loc[klass == 'Kenyon_Cell', 'receptorType'].isna().all()
    report = json.loads((CONTACTS / 'report-00000-04759.json').read_text(encoding='utf-8'))
    path = CONTACTS / 'contacts-00000-04759.parquet'
    assert sha(path) == report['sha256'] and report['source']['generation']
    table = pq.read_table(path, columns=['body_post', 'primary_post'])
    post = table['body_post'].to_numpy()
    roi = table['primary_post'].to_pylist()
    per_target = []
    for row in target.itertuples():
        mask = post == row.bodyId
        counts = Counter(name for name, keep in zip(roi, mask) if keep)
        per_target.append({'body_id':int(row.bodyId),'instance':row.instance,
                           'soma_side':row.somaSide,
                           'kc_contacts':int(mask.sum()),
                           'primary_post_counts':dict(sorted(counts.items()))})
    ptr = np.load(GRAPH / 'indptr.npy', mmap_mode='r')
    pre = np.load(GRAPH / 'indices.npy', mmap_mode='r')
    weight = np.load(GRAPH / 'synapse_counts.npy', mmap_mode='r')
    dan_ids = set(map(int, nodes.loc[klass == 'DAN', 'bodyId']))
    dan_target = []
    for row in target.itertuples():
        index = int(row.compact_index)
        lo, hi = int(ptr[index]), int(ptr[index + 1])
        edges = [(int(body[pre[k]]), int(weight[k])) for k in range(lo, hi)
                 if int(body[pre[k]]) in dan_ids]
        dan_target.append({'body_id':int(row.bodyId),'dan_input_pairs':len(edges),
                           'dan_input_contacts':sum(v for _, v in edges),
                           'pam08_input_contacts':sum(v for i, v in edges if i in set(pam08.bodyId)),
                           'pam07_input_contacts':sum(v for i, v in edges if i in set(pam07.bodyId))})
    result = {
        'scope':'Name-matched gamma-4 anatomical candidate; not a measured per-synapse plasticity transfer',
        'source_graph_manifest_sha256':sha(GRAPH / 'manifest.json'),
        'source_synapse_generation':report['source']['generation'],
        'source_synapse_filtered_sha256':report['sha256'],
        'physiology_source':{'doi':'10.1016/j.cell.2019.05.040',
           'pmcid':'PMC9012144',
           'measured_observable':'GCaMP6s KC-evoked MBON dendritic calcium peak, 2 seconds after KC stimulation; pre/post pairing',
           'timing_sign':'DAN onset minus KC onset; DAN-before-KC potentiation, concurrent or DAN-after-KC depression in gamma-4',
           'controls':'DopR1 loss abolishes forward-pairing depression; DopR2 loss abolishes backward-pairing potentiation',
           'raw_data_status':'Paper states data and custom scripts available upon request to lead contact'},
        'candidate_mbon05':per_target,
        'candidate_pam08_cells':len(pam08),
        'candidate_pam07_cells':len(pam07),
        'dan_to_mbon05_graph_input':dan_target,
        'kc_receptor_type_annotated':0,
        'accepted_cell_identity_transfer':False,
        'per_synapse_teaching_signal_assigned':False,
        'plasticity_enabled':False,
        'biological_gate_passed':False,
    }
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'mbon05_kc_contacts':sum(v['kc_contacts'] for v in per_target),
                      'pam08_cells':len(pam08),'pam07_cells':len(pam07),
                      'receptor_annotations':0, 'report':str(OUT)}, ensure_ascii=False))


if __name__ == '__main__':
    run()
