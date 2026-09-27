"""Lossless incident-edge index for every annotated MaleCNS proprioceptor.

This builds anatomical bindings only. No conductance, sign or dynamics is inferred.
The complete accepted graph remains authoritative and is not replaced by this view.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(1<<20),b''):h.update(part)
    return h.hexdigest()
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='data/derived/malecns_proprioceptive_boundary_v1')
    args=parser.parse_args()
    graph=ROOT/'data/derived/malecns_v1_candidates'
    manifest=json.loads((graph/'manifest.json').read_text())
    assert manifest['orientation']=='row=postsynaptic; indices=presynaptic'
    names=['body_ids.npy','indptr.npy','indices.npy','synapse_counts.npy','source_rows.npy','nodes.feather']
    for name in names:
        assert sha(graph/name)==manifest['files'][name]['sha256'],name
    ids=np.load(graph/'body_ids.npy')
    nodes=pd.read_feather(graph/'nodes.feather').set_index('bodyId').loc[ids].reset_index()
    row=np.load(graph/'indptr.npy',mmap_mode='r')
    pre=np.load(graph/'indices.npy',mmap_mode='r')
    count=np.load(graph/'synapse_counts.npy',mmap_mode='r')
    source_rows=np.load(graph/'source_rows.npy',mmap_mode='r')
    sensory=nodes['class'].eq('mechanosensory_proprioceptive').to_numpy()
    selected=np.flatnonzero(sensory).astype(np.uint32)
    local=np.full(len(ids),-1,dtype=np.int32);local[selected]=np.arange(len(selected),dtype=np.int32)
    parts=[]
    for start in range(0,len(pre),1_000_000):
        edge=np.arange(start,min(len(pre),start+1_000_000),dtype=np.uint64)
        post=(np.searchsorted(row,edge,side='right')-1).astype(np.uint32)
        keep=sensory[pre[start:start+len(edge)]] | sensory[post]
        if not keep.any():continue
        edge=edge[keep];post=post[keep];source=pre[edge]
        parts.append(pd.DataFrame({'csr_edge_index':edge,'source_row':source_rows[edge],
            'pre_graph_index':source,'post_graph_index':post,'pre_body_id':ids[source],
            'post_body_id':ids[post],'pre_local_index':local[source],'post_local_index':local[post],
            'synapse_count':count[edge]}))
    edges=pd.concat(parts,ignore_index=True)
    # Independent completeness construction: all outgoing edges, union every
    # selected incoming CSR row. Internal edges must appear once, not twice.
    outgoing=np.flatnonzero(np.isin(pre,selected)).astype(np.uint64)
    incoming=np.concatenate([np.arange(row[i],row[i+1],dtype=np.uint64) for i in selected])
    expected=np.union1d(outgoing,incoming)
    np.testing.assert_array_equal(edges.csr_edge_index.to_numpy(),expected)
    np.testing.assert_array_equal(edges.synapse_count.to_numpy(),count[expected])
    np.testing.assert_array_equal(edges.source_row.to_numpy(),source_rows[expected])
    source_photo=edges.pre_local_index.to_numpy()>=0
    target_photo=edges.post_local_index.to_numpy()>=0
    categories={'proprioceptor_to_other':source_photo & ~target_photo,
                'other_to_proprioceptor':~source_photo & target_photo,
                'proprioceptor_to_proprioceptor':source_photo & target_photo}
    stats={name:{'rows':int(mask.sum()),'synapse_count':int(edges.loc[mask,'synapse_count'].sum())}
           for name,mask in categories.items()}
    assert sum(v['rows'] for v in stats.values())==len(edges)
    cells=nodes.iloc[selected][['bodyId','type','subclass','entryNerve','rootSide','status','selection_reason']].copy().reset_index(drop=True)
    cells.insert(0,'local_index',np.arange(len(selected),dtype=np.uint32))
    cells.insert(1,'graph_index',selected)
    cells['runtime_enabled']=False
    cells['physiological_profile']='unassigned; anatomy is not conductance calibration'
    for name,idx,mask in [('outgoing',edges.pre_local_index,source_photo),('incoming',edges.post_local_index,target_photo)]:
        rows=np.zeros(len(selected),dtype=np.uint64);counts=np.zeros(len(selected),dtype=np.uint64)
        np.add.at(rows,idx[mask].to_numpy(),1)
        np.add.at(counts,idx[mask].to_numpy(),edges.loc[mask,'synapse_count'].to_numpy())
        cells[name+'_rows']=rows;cells[name+'_synapse_count']=counts
    types=nodes.type.fillna('<untyped>').to_numpy()
    typed=edges.assign(pre_type=types[edges.pre_graph_index],post_type=types[edges.post_graph_index])
    pairs=typed.groupby(['pre_type','post_type'],dropna=False).agg(rows=('csr_edge_index','size'),synapse_count=('synapse_count','sum')).reset_index()
    feedback=typed.loc[categories['other_to_proprioceptor']].groupby('pre_type').agg(rows=('csr_edge_index','size'),synapse_count=('synapse_count','sum')).sort_values('synapse_count',ascending=False)
    output=ROOT/args.output;output.mkdir(parents=True,exist_ok=False)
    marker=output/'INCOMPLETE';marker.write_text('Do not load before successful completion')
    cells.to_feather(output/'cells.feather');edges.to_feather(output/'edges.feather');pairs.to_csv(output/'type_pairs.csv',index=False)
    report={'format':'faithful-fly.proprioceptive-boundary.v1','scope':'Complete anatomical incident-edge view; no enabled physiology, CNS truncation or functional receptor binding',
        'graph_manifest_sha256':sha(graph/'manifest.json'),'candidate_population':len(ids),
        'sensory_cells':len(selected),'type_counts':cells.type.value_counts().to_dict(),
        'incident_rows':len(edges),'incident_synapse_count':int(edges.synapse_count.sum()),
        'categories':stats,'sensory_cells_with_incoming_edges':int((cells.incoming_rows>0).sum()),
        'sensory_cells_without_incoming_edges':int((cells.incoming_rows==0).sum()),
        'sensory_cells_without_incident_edges':int(((cells.incoming_rows+cells.outgoing_rows)==0).sum()),
        'largest_non_sensory_input_types':feedback.head(30).reset_index().to_dict('records'),
        'independent_incident_union_exact':True,
        'files':{name:{'sha256':sha(output/name),'bytes':(output/name).stat().st_size} for name in ['cells.feather','edges.feather','type_pairs.csv']}}
    (output/'manifest.json').write_text(json.dumps(report,indent=2))
    (ROOT/'reports/proprioceptive_boundary.json').write_text(json.dumps(report,indent=2))
    marker.unlink()
    print(json.dumps({k:report[k] for k in ['sensory_cells','incident_rows','categories','sensory_cells_with_incoming_edges','sensory_cells_without_incident_edges','largest_non_sensory_input_types']},indent=2))
if __name__=='__main__':main()
