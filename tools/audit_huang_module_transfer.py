"""Assess anatomical coverage for Huang γ1/α2/α3 modules without transfer."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
EXTRACT = ROOT/'data/derived/mb_synapse_locations_v1/molab_full'
NODES = ROOT/'data/derived/malecns_v1_candidates/nodes.feather'
AUTHOR = ROOT/'data/reference/huang_2024/matlab_code/model_fitting/fit_nonlinear_models.m'
OUT = ROOT/'reports/malecns_huang_module_anatomy.json'
TARGET_TYPES = ('MBON11','MBON18','MBON14')
DAN_TYPES = ('PPL101','PPL105','PPL104')


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(8<<20),b''):
            h.update(block)
    return h.hexdigest()


def run():
    nodes=pd.read_feather(NODES,columns=['bodyId','class','type','instance'])
    targets=nodes[nodes['class'].eq('MBON') & nodes['type'].isin(TARGET_TYPES)]
    assert targets.bodyId.is_unique
    target_ids=set(map(int,targets.bodyId))
    by_cell=defaultdict(Counter)
    all_selected=0
    for part in ('00000-00100','00100-04759'):
        path=EXTRACT/f'contacts-{part}.parquet'
        table=pq.read_table(path,columns=['body_post','primary_post'])
        for body,roi in zip(table['body_post'].to_pylist(),table['primary_post'].to_pylist()):
            if body in target_ids:
                by_cell[int(body)][roi]+=1
                all_selected+=1
    cells=[]
    for row in targets.itertuples(index=False):
        counts=by_cell[int(row.bodyId)]
        cells.append({'bodyId':int(row.bodyId),'type':row.type,'instance':row.instance,
                      'contacts':sum(counts.values()),'primary_post_counts':dict(sorted(counts.items()))})
    dan=nodes[nodes['class'].eq('DAN') & nodes['type'].isin(DAN_TYPES)]
    result={'scope':'Name-matched candidate anatomy for Huang 2024 aggregate modules; no accepted cell identity transfer or plasticity rule',
            'author_fit_source_sha256':sha(AUTHOR),'source_synapse_report_sha256':sha(ROOT/'reports/malecns_mb_synapse_reconciliation.json'),
            'module_labels_in_author_source':['PPL1-gamma1pedc / MBON-gamma1pedc',
                "PPL1-alpha-prime2alpha2 / MBON-alpha2sc",'PPL1-alpha3 / MBON-alpha3'],
            'candidate_mbon_types':list(TARGET_TYPES),'candidate_dan_types':list(DAN_TYPES),
            'candidate_mbon_cells':cells,'candidate_mbon_contacts':all_selected,
            'candidate_dan_cells':[{'bodyId':int(r.bodyId),'type':r.type,'instance':r.instance}
                                    for r in dan.itertuples(index=False)],
            'limitations':['Primary neuropil labels are broad lobes, not γ1/α2/α3 microcompartments',
                'MBON11 has KC contacts in multiple source ROIs',
                'Pairwise contact locations do not specify dopamine release, receptors or a local learning law',
                'Author variables are population level and cannot directly set individual MaleCNS synaptic weights'],
            'mapping_accepted':False,'plasticity_enabled':False,'biological_gate_passed':False}
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    assert sum(x['contacts'] for x in cells)==all_selected
    print(json.dumps({'cells':len(cells),'contacts':all_selected,
                      'by_type':{kind:sum(x['contacts'] for x in cells if x['type']==kind)
                                 for kind in TARGET_TYPES},
                      'dan_candidates':len(dan)},indent=2))


if __name__=='__main__':
    run()
