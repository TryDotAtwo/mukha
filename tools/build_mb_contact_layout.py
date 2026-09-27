"""Build a lossless KC->MBON contact/site view over the accepted full CSR.

No synaptic efficacy, receptor, dopamine radius, or plasticity is assigned.
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
SOURCE = ROOT / 'data/derived/mb_synapse_locations_v1/molab_full'
OUT = ROOT / 'data/derived/mb_synapse_state_layout_v1'
REPORT = ROOT / 'reports/malecns_mb_contact_layout.json'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def save(name, array, files):
    path = OUT / f'{name}.npy'
    assert not path.exists(), f'Existing output requires inspection: {path}'
    np.save(path, array, allow_pickle=False)
    files[name] = {'path':path.relative_to(ROOT).as_posix(),
                   'dtype':str(array.dtype),'shape':list(array.shape),
                   'bytes':path.stat().st_size,'sha256':sha(path)}


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    assert not (OUT / 'manifest.json').exists(), 'Existing layout requires inspection'
    source_report = json.loads((SOURCE / 'report-00000-04759.json').read_text(encoding='utf-8'))
    contact_path = SOURCE / 'contacts-00000-04759.parquet'
    assert source_report['source']['generation'] == '1780494942562468'
    assert contact_path.stat().st_size == source_report['bytes']
    assert sha(contact_path) == source_report['sha256']
    contacts = pq.read_table(contact_path).to_pandas()
    assert len(contacts) == source_report['contacts'] == 463640
    nodes = pd.read_feather(GRAPH / 'nodes.feather', columns=['bodyId','class'])
    body = np.load(GRAPH / 'body_ids.npy', mmap_mode='r')
    ptr = np.load(GRAPH / 'indptr.npy', mmap_mode='r')
    indices = np.load(GRAPH / 'indices.npy', mmap_mode='r')
    counts = np.load(GRAPH / 'synapse_counts.npy', mmap_mode='r')
    assert np.array_equal(body, nodes.bodyId.to_numpy())
    labels = nodes['class'].fillna('').to_numpy()
    kc = set(map(int, body[labels == 'Kenyon_Cell']))
    mbon_indices = np.flatnonzero(labels == 'MBON')
    assert len(kc) == 4064 and len(mbon_indices) == 97
    edges = []
    for post_index in mbon_indices:
        for edge in range(int(ptr[post_index]), int(ptr[post_index + 1])):
            pre_index = int(indices[edge])
            if int(body[pre_index]) in kc:
                edges.append((int(body[pre_index]),int(body[post_index]),
                              int(edge),int(counts[edge])))
    edge_table = pd.DataFrame(edges, columns=['body_pre','body_post','global_edge','source_contacts'])
    assert len(edge_table) == 61210 and not edge_table.duplicated(['body_pre','body_post']).any()
    edge_table['local_edge'] = np.arange(len(edge_table), dtype=np.uint32)
    contacts['source_contact'] = np.arange(len(contacts), dtype=np.uint32)
    joined = contacts.merge(edge_table, on=['body_pre','body_post'], how='left',
                            validate='many_to_one', sort=False)
    assert len(joined) == len(contacts)
    assert np.array_equal(joined.source_contact.to_numpy(), contacts.source_contact.to_numpy())
    assert not joined.global_edge.isna().any()
    observed = np.bincount(joined.local_edge.to_numpy(np.int64), minlength=len(edges))
    assert np.array_equal(observed, edge_table.source_contacts.to_numpy())
    site_keys = pd.MultiIndex.from_frame(joined[['body_pre','x_pre','y_pre','z_pre']])
    site_ids, site_values = pd.factorize(site_keys, sort=False)
    site_ids = site_ids.astype(np.uint32)
    site_rows = pd.DataFrame(site_values.tolist(), columns=['body_pre','x_pre','y_pre','z_pre'])
    assert len(site_rows) == len(np.unique(site_ids))
    body_to_index = {int(value):i for i,value in enumerate(body)}
    site_pre_index = np.array([body_to_index[int(value)] for value in site_rows.body_pre],
                              dtype=np.uint32)
    assert np.all(labels[site_pre_index] == 'Kenyon_Cell')
    site_order = np.argsort(site_ids, kind='stable').astype(np.uint32)
    site_counts = np.bincount(site_ids, minlength=len(site_rows))
    site_offsets = np.empty(len(site_rows)+1, dtype=np.uint64)
    site_offsets[0] = 0
    np.cumsum(site_counts, out=site_offsets[1:])
    local_edges = joined.local_edge.to_numpy(np.uint32)
    edge_order = np.argsort(local_edges, kind='stable').astype(np.uint32)
    edge_offsets = np.empty(len(edges)+1, dtype=np.uint64)
    edge_offsets[0] = 0
    np.cumsum(observed, out=edge_offsets[1:])
    roi_values = joined.primary_post.astype(str)
    roi_names = sorted(roi_values.unique())
    assert len(roi_names) <= 255
    roi_code = roi_values.map({name:i for i,name in enumerate(roi_names)}).to_numpy(np.uint8)
    files = {}
    arrays = {
        'eligible_global_edge':edge_table.global_edge.to_numpy(np.uint32),
        'eligible_edge_source_contacts':edge_table.source_contacts.to_numpy(np.uint32),
        'contact_edge_local':local_edges,
        'contact_site':site_ids,
        'contact_x_post':joined.x_post.to_numpy(np.int32),
        'contact_y_post':joined.y_post.to_numpy(np.int32),
        'contact_z_post':joined.z_post.to_numpy(np.int32),
        'contact_conf_pre':joined.conf_pre.to_numpy(np.float32),
        'contact_conf_post':joined.conf_post.to_numpy(np.float32),
        'contact_primary_post_roi':roi_code,
        'site_pre_index':site_pre_index,
        'site_x_pre':site_rows.x_pre.to_numpy(np.int32),
        'site_y_pre':site_rows.y_pre.to_numpy(np.int32),
        'site_z_pre':site_rows.z_pre.to_numpy(np.int32),
        'site_contact_offsets':site_offsets,
        'site_contact_order':site_order,
        'edge_contact_offsets':edge_offsets,
        'edge_contact_order':edge_order,
    }
    for name,array in arrays.items():
        save(name,array,files)
    site_posts = joined.groupby(site_ids,sort=False).body_post.nunique().to_numpy()
    partner_distribution = Counter(map(int, site_posts))
    multi_mask = site_posts > 1
    multi_contacts = int(site_counts[multi_mask].sum())
    result = {
        'format':'flyrocket.kc-mbon-contact-site-view.v1',
        'scope':'Complete KC->MBON contact view; no other partners of these presynaptic sites included',
        'graph_manifest_sha256':sha(GRAPH / 'manifest.json'),
        'source_parquet_sha256':source_report['sha256'],
        'source_gcs_generation':source_report['source']['generation'],
        'coordinate_unit':'published 8-nm voxel indices',
        'contacts':len(contacts),'eligible_graph_edges':len(edges),
        'presynaptic_sites':len(site_rows),
        'sites_with_multiple_mbon_partners':int(multi_mask.sum()),
        'contacts_on_multiple_mbon_partner_sites':multi_contacts,
        'max_distinct_mbon_partners_per_site':max(partner_distribution),
        'distinct_mbon_partners_per_site':dict(sorted(partner_distribution.items())),
        'primary_post_roi_names':roi_names,
        'files':files,
        'synaptic_efficacy_assigned':False,
        'dopamine_compartment_assigned':False,
        'plasticity_enabled':False,
        'biological_gate_passed':False,
    }
    assert result['presynaptic_sites'] == 391849
    assert result['sites_with_multiple_mbon_partners'] == 65275
    assert multi_contacts == 137062
    (OUT / 'manifest.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    REPORT.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'contacts':len(contacts),'edges':len(edges),'sites':len(site_rows),
                      'multi_partner_sites':int(multi_mask.sum()),
                      'report':str(REPORT)},ensure_ascii=False))


if __name__ == '__main__':
    run()
