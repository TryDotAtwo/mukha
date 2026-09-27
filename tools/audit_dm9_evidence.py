"""Bind narrow published physiological evidence to anatomical IDs, without fitting."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda:f.read(1<<20),b''):h.update(data)
    return h.hexdigest()
def main():
    config=ROOT/'configs/visual_physiology_evidence.json'
    evidence=json.loads(config.read_text())
    source=json.loads((ROOT/'reports/dm9_physiology_source.json').read_text())
    assert sha(ROOT/source['local_path'])==source['sha256']
    assert source['doi']==evidence['source_doi']
    graph=ROOT/'data/derived/malecns_v1_candidates'
    gm=json.loads((graph/'manifest.json').read_text())
    for name in ['body_ids.npy','nodes.feather','indptr.npy','indices.npy','synapse_counts.npy']:
        assert sha(graph/name)==gm['files'][name]['sha256'],name
    ids=np.load(graph/'body_ids.npy');nodes=pd.read_feather(graph/'nodes.feather').set_index('bodyId').loc[ids]
    types=nodes.type.fillna('<untyped>').to_numpy()
    dm9=types=='Dm9';dm9_indices=np.flatnonzero(dm9)
    chemistry_path=ROOT/'data/derived/malecns_neurochemistry/nodes.feather'
    chemical_report=json.loads((ROOT/'reports/malecns_neurochemistry_audit.json').read_text())
    assert sha(chemistry_path)==chemical_report['output_sha256']
    chemistry=pd.read_feather(chemistry_path).set_index('body').loc[ids[dm9]]
    boundary=ROOT/'data/derived/malecns_visual_boundary_v1'
    bm=json.loads((boundary/'manifest.json').read_text())
    assert sha(boundary/'edges.feather')==bm['files']['edges.feather']['sha256']
    assert bm['graph_manifest_sha256']==sha(graph/'manifest.json')
    edges=pd.read_feather(boundary/'edges.feather')
    pre=edges.pre_graph_index.to_numpy();post=edges.post_graph_index.to_numpy()
    inner=np.isin(types,evidence['main_inner_types'])
    masks={'inner_to_dm9':inner[pre] & dm9[post], 'dm9_to_inner':dm9[pre] & inner[post]}
    assignments=ROOT/'data/derived/malecns_optic_columns/assignments.csv'
    columns_report=json.loads((ROOT/'reports/optic_column_index.json').read_text())
    assert sha(assignments)==columns_report['files']['assignments.csv']
    table=pd.read_csv(assignments).set_index('body_id');assert table.index.is_unique
    column=np.full(len(ids),'',dtype=object)
    index={int(body):i for i,body in enumerate(ids)}
    for body,record in table.iterrows():column[index[int(body)]]=record['column']
    opposite=((np.isin(types[pre],['R7p','R7y']) & np.isin(types[post],['R8p','R8y'])) |
              (np.isin(types[pre],['R8p','R8y']) & np.isin(types[post],['R7p','R7y'])))
    masks['same_column_r7_r8']=opposite & (column[pre]!='') & (column[pre]==column[post])
    family=np.full(len(edges),'unassigned',dtype=object)
    coverage={}
    for name,mask in masks.items():
        assert np.all(family[mask]=='unassigned')
        family[mask]=name
        coverage[name]={'rows':int(mask.sum()),'contact_count':int(edges.loc[mask,'synapse_count'].sum())}
    edges['evidence_family']=family;edges['runtime_enabled']=False
    # Full Dm9 incident context includes connections not touching photoreceptors.
    row=np.load(graph/'indptr.npy',mmap_mode='r');source_index=np.load(graph/'indices.npy',mmap_mode='r')
    count=np.load(graph/'synapse_counts.npy',mmap_mode='r')
    incoming=np.concatenate([np.arange(row[i],row[i+1],dtype=np.uint64) for i in dm9_indices])
    outgoing=np.flatnonzero(dm9[source_index])
    inputs=pd.DataFrame({'pre_type':types[source_index[incoming]],'contacts':count[incoming]})
    input_types=inputs.groupby('pre_type').agg(rows=('contacts','size'),contact_count=('contacts','sum')).sort_values('contact_count',ascending=False)
    destination=ROOT/'data/derived/dm9_physiology_evidence_v1';destination.mkdir(exist_ok=False)
    marker=destination/'INCOMPLETE';marker.write_text('Evidence export in progress')
    edges.to_feather(destination/'visual_edge_evidence.feather')
    chemistry.reset_index().to_feather(destination/'dm9_chemistry.feather')
    input_types.to_csv(destination/'dm9_all_input_types.csv')
    report={'scope':'Source-linked qualitative evidence only; no calibrated dynamics or enabled MaleCNS transfer',
        'source_snapshot_sha256':source['sha256'],'evidence_config_sha256':sha(config),
        'graph_manifest_sha256':sha(graph/'manifest.json'),'dm9_objects':len(dm9_indices),
        'dm9_consensus_nt':chemistry.consensus_nt.fillna('<missing>').value_counts().to_dict(),
        'full_graph_dm9_incoming_rows':len(incoming),'full_graph_dm9_outgoing_rows':len(outgoing),
        'evidence_coverage':coverage,'unassigned_visual_rows':int((family=='unassigned').sum()),
        'all_visual_rows_retained':len(edges)==bm['incident_rows'],'runtime_enabled':False,
        'readout_conversion_to_voltage_fitted':False,'model_parameters_fitted':False,
        'files':{name:sha(destination/name) for name in ['visual_edge_evidence.feather','dm9_chemistry.feather','dm9_all_input_types.csv']}}
    assert report['all_visual_rows_retained']
    (destination/'manifest.json').write_text(json.dumps(report,indent=2));marker.unlink()
    (ROOT/'reports/dm9_physiology_evidence.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
