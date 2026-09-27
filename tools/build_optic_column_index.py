"""Index author column assignments without inventing missing photoreceptors."""
import hashlib
import json
from pathlib import Path
import re
import numpy as np
import pandas as pd
import pyarrow.feather as feather

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    lock_path=ROOT/'reports/optic_column_sources.json';lock=json.loads(lock_path.read_text())
    for e in lock['files']:
        if sha(ROOT/e['path'])!=e['sha256']:raise ValueError('Column source changed')
    graph=ROOT/'data/derived/malecns_v1_candidates'
    manifest=json.loads((graph/'manifest.json').read_text())
    for name in ['body_ids.npy','nodes.feather']:
        if sha(graph/name)!=manifest['files'][name]['sha256']:raise ValueError('Graph changed')
    ids=np.load(graph/'body_ids.npy');indices={int(v):i for i,v in enumerate(ids)}
    nodes=feather.read_table(graph/'nodes.feather').to_pandas().set_index('bodyId')
    workbook=ROOT/'data/reference/malecns_optic/optic-column-type-assignments-v1.0.xlsx'
    records=[];missing=[];conflicts=[];columns=[]
    for sheet in ['Right OL','Left OL']:
        frame=pd.read_excel(workbook,sheet_name=sheet)
        for _,r in frame.iterrows():
            match=re.fullmatch(r'ME_([LR])_col_(\d+)_(\d+)',r['column'])
            if not match:raise ValueError('Unknown column syntax')
            side,h1,h2=match.groups();h1,h2=int(h1),int(h2)
            columns.append({'column':r['column'],'side':side,'hex1':h1,'hex2':h2,'column_type':r.column_type})
            for role in ['L1','R7','R8']:
                body=int(r[role])
                if body==-99:
                    missing.append({'column':r['column'],'role':role,'reason':'author: no cell of this type found'});continue
                if body<=0 or body not in indices:raise ValueError(f'Assigned cell absent from full graph: {body}')
                n=nodes.loc[body]
                record={'body_id':body,'graph_index':indices[body],'role':role,
                    'column':r['column'],'side':side,'hex1':h1,'hex2':h2,
                    'column_type':r.column_type,'source_cell_type':n['type'],
                    'mapping_scope':'author anatomical column; optical ray and phototransduction not assigned'}
                if role=='L1' and pd.notna(n.assignedOlHex1) and pd.notna(n.assignedOlHex2):
                    if (int(n.assignedOlHex1),int(n.assignedOlHex2))!=(h1,h2):
                        conflicts.append(dict(record,annotation_hex1=int(n.assignedOlHex1),annotation_hex2=int(n.assignedOlHex2)))
                records.append(record)
    out=ROOT/'data/derived/malecns_optic_columns';out.mkdir(parents=True,exist_ok=True)
    assignments=pd.DataFrame(records);assignments.to_csv(out/'assignments.csv',index=False)
    pd.DataFrame(columns).to_csv(out/'columns.csv',index=False)
    pd.DataFrame(missing).to_csv(out/'missing.csv',index=False)
    pd.DataFrame(conflicts).to_json(out/'coordinate_conflicts.json',orient='records',indent=2)
    duplicates=assignments[assignments.body_id.duplicated(keep=False)]
    duplicates.to_csv(out/'multiple_assignments.csv',index=False)
    report={'scope':'Author anatomical column assignments, not implemented vision',
        'source_lock_sha256':sha(lock_path),'columns':len(columns),
        'columns_with_any_cell':int(assignments.column.nunique()),
        'assignment_rows':len(assignments),'role_counts':assignments.role.value_counts().to_dict(),
        'missing_cell_slots':len(missing),'multiple_assignment_rows':len(duplicates),
        'l1_coordinate_conflicts':len(conflicts),'files':{p.name:sha(p) for p in out.iterdir() if p.is_file()},
        'remaining':['R1-R6 receptive-field mapping','Optical directions in anatomical eye coordinates',
                     'Spectral response and phototransduction','Native image-to-sensory input validation'],
        'visual_input_enabled':False}
    (ROOT/'reports/optic_column_index.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
