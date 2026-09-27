import json,hashlib,struct,numpy as np,pandas as pd
from pathlib import Path
r=Path('data/derived/malecns_v1_candidates');p=Path('build/brain_body_graph.bin');ids=np.load(r/'body_ids.npy');row=np.load(r/'indptr.npy');col=np.load(r/'indices.npy');cnt=np.load(r/'synapse_counts.npy');rep=json.loads(Path('data/derived/malecns_sign_diagnostic_float64_v2/report.json').read_text());nt=pd.read_feather(r/'neurotransmitters.feather').set_index('body').reindex(ids).consensus_nt.fillna('missing_annotation');sign=nt.map(dict(rep['spec']['shared_assumptions'],unclear=1)).to_numpy(dtype=np.float64);weights=cnt.astype(np.float64)*sign[col]*.275
assert hashlib.sha256(weights.tobytes()).hexdigest()==rep['results'][0]['weights_sha256']
with p.open('xb') as f:
 f.write(struct.pack('<IQI',len(ids),len(col),int(np.flatnonzero(ids==10056)[0])))
 row.astype('<u8').tofile(f);col.astype('<u4').tofile(f);weights.astype('<f8').tofile(f)
m=json.loads(Path('configs/knee_interface_draft.json').read_text());lines=[str(len(m['entries']))]+['{} {}-motor {}'.format(e['graph_index'],e['proposed_joint'],e['proposed_torque_sign']) for e in m['entries']]
Path('build/brain_body_mapping.txt').write_text('\n'.join(lines)+'\n');print('Exported',p.stat().st_size,'bytes')
