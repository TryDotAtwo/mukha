"""Connectivity-derived column candidates; no silent sensory assignment."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.feather as feather

ROOT=Path(__file__).resolve().parents[1]
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()

def main():
    graph=ROOT/'data/derived/malecns_v1_candidates'
    manifest=json.loads((graph/'manifest.json').read_text())
    for name in ['body_ids.npy','indptr.npy','indices.npy','synapse_counts.npy','nodes.feather']:
        if sha(graph/name)!=manifest['files'][name]['sha256']:raise ValueError(f'Graph changed: {name}')
    ids=np.load(graph/'body_ids.npy');index={int(x):i for i,x in enumerate(ids)}
    nodes=feather.read_table(graph/'nodes.feather').to_pandas().set_index('bodyId').loc[ids]
    r16=nodes.type.eq('R1-R6').to_numpy()
    anchors=nodes[nodes.type.isin(['L1','L2','L3']) & nodes.assignedOlHex1.notna() & nodes.assignedOlHex2.notna() & nodes.somaSide.isin(['L','R'])]
    row=np.load(graph/'indptr.npy');pre=np.load(graph/'indices.npy',mmap_mode='r');counts=np.load(graph/'synapse_counts.npy',mmap_mode='r')
    evidence=[];groups=defaultdict(lambda:defaultdict(lambda:defaultdict(int)))
    conflict_report=ROOT/'data/derived/malecns_optic_columns/coordinate_conflicts.json'
    optic=json.loads((ROOT/'reports/optic_column_index.json').read_text())
    if sha(conflict_report)!=optic['files']['coordinate_conflicts.json']:raise ValueError('Conflict report changed')
    conflict_ids={int(x['body_id']) for x in json.loads(conflict_report.read_text())}
    for body,a in anchors.iterrows():
        post=index[int(body)];begin,end=int(row[post]),int(row[post+1])
        column=f'ME_{a.somaSide}_col_{int(a.assignedOlHex1):02d}_{int(a.assignedOlHex2):02d}'
        for edge in range(begin,end):
            source=int(pre[edge])
            if not r16[source]:continue
            weight=int(counts[edge]);groups[source][a.type][column]+=weight
            evidence.append({'r16_body_id':int(ids[source]),'r16_graph_index':source,'anchor_body_id':int(body),
                'anchor_type':a.type,'column':column,'synapse_count':weight,'csr_edge_index':edge,
                'anchor_has_source_coordinate_conflict':int(body) in conflict_ids})
    records=[]
    source_conflict_inputs={e['r16_body_id'] for e in evidence if e['anchor_has_source_coordinate_conflict']}
    for i in np.flatnonzero(r16):
        type_candidates={};ties=False
        for celltype,support in groups[int(i)].items():
            maximum=max(support.values());winners=sorted(c for c,w in support.items() if w==maximum)
            ties|=len(winners)!=1
            type_candidates[celltype]={'columns':winners,'top_count':maximum,'total_count':sum(support.values()),'all_column_counts':dict(support)}
        winners={c for x in type_candidates.values() for c in x['columns']}
        candidate=next(iter(winners)) if len(winners)==1 and not ties else None
        root_side=nodes.iloc[i].rootSide
        side_consistent=bool(candidate and isinstance(root_side,str) and candidate.startswith(f'ME_{root_side}_'))
        status=('no_anchor_contacts' if not type_candidates else 'tied_or_disagreeing' if not candidate else
                'side_unresolved_or_conflicting' if not side_consistent else
                'single_anchor_type_only' if len(type_candidates)<2 else 'multi_type_agreement_candidate')
        records.append({'body_id':int(ids[i]),'graph_index':int(i),'root_side':root_side if isinstance(root_side,str) else None,
            'status':status,'candidate_column':candidate,'anchor_evidence':type_candidates,
            'touches_coordinate_conflict':int(ids[i]) in source_conflict_inputs,'enabled':False})
    out=ROOT/'data/derived/malecns_optic_columns'
    candidate_path=out/'r16_candidates.json';candidate_path.write_text(json.dumps(records,indent=2))
    edge_path=out/'r16_anchor_edges.csv';pd.DataFrame(evidence).to_csv(edge_path,index=False)
    statuses=pd.Series([r['status'] for r in records]).value_counts().to_dict()
    report={'scope':'Inference from complete-graph anatomical contacts; not independently validated visual fields',
        'graph_manifest_sha256':sha(graph/'manifest.json'),'r16_neurons':len(records),'anchor_neurons':len(anchors),
        'evidence_rows':len(evidence),'status_counts':statuses,
        'inputs_touching_coordinate_conflict':len(source_conflict_inputs),'candidate_sha256':sha(candidate_path),
        'edges_sha256':sha(edge_path),'visual_input_enabled':False,
        'caveats':['Top-count agreement is not a statistical confidence estimate.',
                   'Unassigned L1/L2/L3 coordinates limit available anchors.',
                   'A known source coordinate conflict is retained in evidence.',
                   'Column identity is not an optical viewing direction or phototransduction model.']}
    (ROOT/'reports/r16_column_inference.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
