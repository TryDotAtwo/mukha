"""Align source chemistry with the complete graph, preserving all uncertainty."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.feather as feather

ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()

def main():
    source=ROOT/'data/raw/malecns_v1/body-neurotransmitters-male-cns-v1.0.feather'
    lock=json.loads((ROOT/'reports/malecns_source_lock.json').read_text())
    expected=next(x for x in lock['files'] if x['name']==source.name)['sha256']
    if sha(source)!=expected:raise ValueError('Neurotransmitter source changed')
    graph=ROOT/'data/derived/malecns_v1_candidates'
    manifest=json.loads((graph/'manifest.json').read_text())
    if manifest['orientation']!='row=postsynaptic; indices=presynaptic':raise ValueError('Unexpected graph orientation')
    for name in ['body_ids.npy','indices.npy','synapse_counts.npy']:
        if sha(graph/name)!=manifest['files'][name]['sha256']:raise ValueError('Graph artifact changed')
    ids=np.load(graph/'body_ids.npy')
    table=feather.read_table(source).to_pandas()
    if table.body.duplicated().any():raise ValueError('Duplicate chemistry ID')
    aligned=pd.DataFrame({'body':ids,'graph_index':np.arange(len(ids),dtype=np.uint32)}).merge(table,on='body',how='left',validate='one_to_one',indicator=True)
    aligned['chemistry_source_present']=aligned.pop('_merge').eq('both')
    aligned['transmission_effect_status']='unassigned; receptor-dependent physiology is not specified by transmitter label'
    destination=ROOT/'data/derived/malecns_neurochemistry';destination.mkdir(parents=True,exist_ok=True)
    path=destination/'nodes.feather';aligned.to_feather(path)
    outgoing_rows=np.zeros(len(ids),dtype=np.uint64)
    outgoing_counts=np.zeros(len(ids),dtype=np.uint64)
    pres=np.load(graph/'indices.npy',mmap_mode='r')
    counts=np.load(graph/'synapse_counts.npy',mmap_mode='r')
    for start in range(0,len(pres),1_000_000):
        indices=pres[start:start+1_000_000]
        np.add.at(outgoing_rows,indices,np.uint64(1))
        np.add.at(outgoing_counts,indices,counts[start:start+1_000_000])
    labels=aligned.consensus_nt.fillna('missing').replace('','missing')
    summary=[]
    for label in sorted(labels.unique()):
        mask=labels.eq(label).to_numpy()
        summary.append({'source_consensus':label,'neurons':int(mask.sum()),
                        'outgoing_graph_rows':int(outgoing_rows[mask].sum()),
                        'outgoing_synapse_count_sum':int(outgoing_counts[mask].sum())})
    gt=aligned.ground_truth.fillna('').str.strip().ne('')
    prediction=aligned.predicted_nt.fillna('')
    report={'scope':'Source chemistry alignment only; no transmitter-to-effect assignments or removed edges',
        'source_sha256':expected,'graph_ids_sha256':sha(graph/'body_ids.npy'),
        'output_sha256':sha(path),'nodes':len(aligned),'graph_rows':len(pres),
        'graph_manifest_sha256':sha(graph/'manifest.json'),
        'source_missing_neurons':int((~aligned.chemistry_source_present).sum()),
        'source_ground_truth_label_rows':int(gt.sum()),
        'consensus_vs_individual_prediction_disagreements':int((prediction.ne('') & prediction.ne(aligned.consensus_nt.fillna(''))).sum()),
        'individual_confidence_missing':int(aligned.predicted_nt_confidence.isna().sum()),
        'by_consensus':summary,'receptor_effects_assigned':False,
        'required_hypotheses':['Postsynaptic receptor-dependent signs and time constants.',
            'Explicit treatment of unknown or unclear labels without deleting anatomical edges.',
            'Separate slow modulatory transmission from fast synaptic-current assumptions.',
            'Sensitivity variants for source prediction uncertainty.']}
    if sum(x['outgoing_graph_rows'] for x in summary)!=len(pres):raise ValueError('Coverage mismatch')
    (ROOT/'reports/malecns_neurochemistry_audit.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
