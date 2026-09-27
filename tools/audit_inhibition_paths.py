"""Query exact graph edges for all crosswalk candidates, including conflicts."""
import hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
g=ROOT/'data/derived/malecns_v1_candidates'
m=json.loads((g/'manifest.json').read_text())
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()
for name in ['nodes.feather','body_ids.npy','indptr.npy','indices.npy','synapse_counts.npy','source_rows.npy']:
    assert sha(g/name)==m['files'][name]['sha256']
cross=json.loads((ROOT/'reports/inhibition_crosswalk_candidates.json').read_text())
ids=np.load(g/'body_ids.npy');nodes=pd.read_feather(g/'nodes.feather').set_index('bodyId').loc[ids]
assert sha(g/'nodes.feather')==cross['source_nodes_sha256']
indptr=np.load(g/'indptr.npy',mmap_mode='r');pre=np.load(g/'indices.npy',mmap_mode='r')
counts=np.load(g/'synapse_counts.npy',mmap_mode='r');rows=np.load(g/'source_rows.npy',mmap_mode='r')
labels={int(c['bodyId']):q['author_label'] for q in cross['matches'] for c in q['candidates']}
selected=np.flatnonzero(np.isin(ids,list(labels)))
out=ROOT/'data/derived/inhibition_candidate_paths_v1'
if out.exists():raise FileExistsError('Immutable output exists')
parts=[]
for start in range(0,len(pre),1000000):
    end=min(start+1000000,len(pre));edge=np.arange(start,end,dtype=np.uint64)
    post=np.searchsorted(indptr,edge,side='right')-1
    # Retain every outgoing candidate edge, not only expected partners.
    keep=np.isin(pre[start:end],selected);edge=edge[keep];post=post[keep]
    parts.append(pd.DataFrame(dict(csr_edge_index=edge,source_row=rows[edge],
        pre_body_id=ids[pre[edge]],post_body_id=ids[post],synapse_count=counts[edge])))
edges=pd.concat(parts,ignore_index=True)
assert edges.csr_edge_index.is_unique
assert len(edges)==int(np.isin(pre,selected).sum())
edges['post_type']=nodes.type.reindex(edges.post_body_id).to_numpy()
edges['post_subclass']=nodes.subclass.reindex(edges.post_body_id).to_numpy()
out.mkdir();edges.to_feather(out/'edges.feather')
summaries=[]
for body,label in labels.items():
    e=edges.loc[edges.pre_body_id.eq(body)]
    sensory=e[e.post_body_id.isin(nodes.index[nodes['class'].eq('mechanosensory_proprioceptive')])]
    candidate=e[e.post_body_id.isin(labels)]
    summaries.append(dict(body_id=body,author_candidate_label=label,type=nodes.loc[body,'type'],
        outgoing_rows=len(e),outgoing_contacts=int(e.synapse_count.sum()),
        proprioceptor_contacts_by_type={str(k):int(v) for k,v in sensory.groupby('post_type',dropna=False).synapse_count.sum().items()},
        candidate_to_candidate=json.loads(candidate.to_json(orient='records'))))
report=dict(graph_manifest_sha256=sha(g/'manifest.json'),source_crosswalk_sha256=sha(ROOT/'reports/inhibition_crosswalk_candidates.json'),
    selected_candidates=len(selected),retained_outgoing_rows=len(edges),summaries=summaries,
    edges_sha256=sha(out/'edges.feather'),all_weights_retained=True,minimum_weight_threshold=None,
    functional_signs_inferred=False,identity_resolved=False,runtime_enabled=False)
(out/'manifest.json').write_text(json.dumps(report,indent=2))
(ROOT/'reports/inhibition_candidate_paths.json').write_text(json.dumps(report,indent=2))
print(json.dumps([dict(body_id=s['body_id'],type=s['type'],rows=s['outgoing_rows'],sensory=s['proprioceptor_contacts_by_type']) for s in summaries],indent=2))
