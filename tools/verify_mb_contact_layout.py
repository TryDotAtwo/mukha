"""Verify serialized KC->MBON SoA against source contacts and full CSR."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / 'data/derived/malecns_v1_candidates'
SOURCE = ROOT / 'data/derived/mb_synapse_locations_v1/molab_full'
LAYOUT = ROOT / 'data/derived/mb_synapse_state_layout_v1'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(8 << 20),b''):
            h.update(block)
    return h.hexdigest()


def run():
    manifest=json.loads((LAYOUT/'manifest.json').read_text(encoding='utf-8'))
    assert sha(GRAPH/'manifest.json')==manifest['graph_manifest_sha256']
    source_path=SOURCE/'contacts-00000-04759.parquet'
    assert sha(source_path)==manifest['source_parquet_sha256']
    arrays={}
    for name,meta in manifest['files'].items():
        path=ROOT/meta['path']
        assert path.stat().st_size==meta['bytes'] and sha(path)==meta['sha256']
        arr=np.load(path,mmap_mode='r',allow_pickle=False)
        assert str(arr.dtype)==meta['dtype'] and list(arr.shape)==meta['shape']
        arrays[name]=arr
    src=pq.read_table(source_path).to_pandas()
    n=len(src)
    assert n==manifest['contacts']==463640
    body=np.load(GRAPH/'body_ids.npy',mmap_mode='r')
    ptr=np.load(GRAPH/'indptr.npy',mmap_mode='r')
    indices=np.load(GRAPH/'indices.npy',mmap_mode='r')
    counts=np.load(GRAPH/'synapse_counts.npy',mmap_mode='r')
    site=arrays['contact_site']
    edge_local=arrays['contact_edge_local']
    global_edge=arrays['eligible_global_edge'][edge_local]
    site_pre=arrays['site_pre_index'][site]
    assert np.array_equal(body[site_pre],src.body_pre.to_numpy())
    for axis in 'xyz':
        assert np.array_equal(arrays[f'site_{axis}_pre'][site],src[f'{axis}_pre'].to_numpy())
        assert np.array_equal(arrays[f'contact_{axis}_post'],src[f'{axis}_post'].to_numpy())
    assert np.array_equal(arrays['contact_conf_pre'],src.conf_pre.to_numpy(np.float32))
    assert np.array_equal(arrays['contact_conf_post'],src.conf_post.to_numpy(np.float32))
    roi=np.asarray(manifest['primary_post_roi_names'],dtype=object)
    assert np.array_equal(roi[arrays['contact_primary_post_roi']],src.primary_post.astype(str).to_numpy())
    assert np.array_equal(body[indices[global_edge]],src.body_pre.to_numpy())
    assert np.array_equal(counts[arrays['eligible_global_edge']],arrays['eligible_edge_source_contacts'])
    # CSR is incoming: find the postsynaptic row for each global edge.
    post_index=np.searchsorted(ptr[1:],global_edge,side='right')
    assert np.array_equal(body[post_index],src.body_post.to_numpy())
    for prefix,group_id,group_count in (
        ('site',site,manifest['presynaptic_sites']),
        ('edge',edge_local,manifest['eligible_graph_edges'])):
        order=arrays[f'{prefix}_contact_order']
        offsets=arrays[f'{prefix}_contact_offsets']
        assert len(order)==n and len(offsets)==group_count+1
        assert offsets[0]==0 and offsets[-1]==n
        assert np.array_equal(np.sort(order),np.arange(n,dtype=np.uint32))
        assert np.array_equal(group_id[order],np.repeat(
            np.arange(group_count,dtype=np.uint32),np.diff(offsets).astype(np.intp)))
    assert np.array_equal(np.diff(arrays['edge_contact_offsets']),
                          arrays['eligible_edge_source_contacts'])
    print(json.dumps({'contacts':n,'sites':manifest['presynaptic_sites'],
                      'edges':manifest['eligible_graph_edges'],
                      'serialized_fields_reconstructed':True,
                      'full_csr_link_verified':True},ensure_ascii=False))


if __name__=='__main__':
    run()
