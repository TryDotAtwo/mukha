"""Quantify annotation coverage over every accepted neuron and edge, no signs."""
import hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];g=ROOT/'data/derived/malecns_v1_candidates'
m=json.loads((g/'manifest.json').read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
for name in ['body_ids.npy','indices.npy','synapse_counts.npy','neurotransmitters.feather']:
 assert sha(g/name)==m['files'][name]['sha256']
ids=np.load(g/'body_ids.npy');pre=np.load(g/'indices.npy',mmap_mode='r');w=np.load(g/'synapse_counts.npy',mmap_mode='r')
nt=pd.read_feather(g/'neurotransmitters.feather');assert nt.body.is_unique
n=nt.set_index('body').reindex(ids)
labels=n.consensus_nt.fillna('missing_annotation')
cats=sorted(labels.unique());codes=pd.Categorical(labels,categories=cats).codes
rows=np.zeros(len(cats),dtype=np.int64);contacts=rows.copy()
for start in range(0,len(pre),1000000):
 c=codes[pre[start:start+1000000]];weights=w[start:start+1000000]
 rows+=np.bincount(c,minlength=len(cats))
 for k in range(len(cats)):contacts[k]+=np.sum(weights[c==k],dtype=np.int64)
assert int(rows.sum())==len(pre)
assert int(contacts.sum())==int(np.sum(w,dtype=np.int64))
report=dict(graph_manifest_sha256=sha(g/'manifest.json'),neurons=len(ids),edge_rows=len(pre),
 contacts=int(contacts.sum()),groups=[dict(consensus_nt=label,neurons=int((labels==label).sum()),
  outgoing_edge_rows=int(rows[k]),outgoing_contacts=int(contacts[k])) for k,label in enumerate(cats)],
 missing_body_ids=[int(i) for i in ids[labels.to_numpy()=='missing_annotation']],
 unclear_body_ids=[int(i) for i in ids[labels.to_numpy()=='unclear']],
 source_prediction_disagrees_with_consensus=int((n.predicted_nt.notna() & n.consensus_nt.notna() & n.predicted_nt.ne(n.consensus_nt)).sum()),
 signs_assigned=False,warning='Transmitter identity does not uniquely determine receptor action; glutamate and modulatory effects require context. No implicit excitatory default.',
 runtime_enabled=False)
(ROOT/'reports/full_graph_chemistry_coverage.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report['groups'],indent=2))
