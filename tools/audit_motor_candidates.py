"""Preserve motor identities and source labels; do not infer muscle mechanics."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pyarrow.feather as feather

ROOT=Path(__file__).resolve().parents[1]

def main():
    source=ROOT/'data/raw/malecns_v1/body-annotations-male-cns-v1.0-minconf-0.5.feather'
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    lock=json.loads((ROOT/'reports/malecns_source_lock.json').read_text())
    expected=next(x for x in lock['files'] if x['name']==source.name)['sha256']
    if digest!=expected:raise ValueError('Source annotations changed')
    frame=feather.read_table(source).to_pandas()
    frame=frame[frame.status.eq('Traced')|frame.superclass.fillna('').str.strip().ne('')]
    ids_path=ROOT/'data/derived/malecns_v1_candidates/body_ids.npy'
    ids=np.load(ids_path)
    if len(np.unique(ids))!=len(ids):raise ValueError('Duplicate graph IDs')
    index={int(value):i for i,value in enumerate(ids)}
    motors=frame[frame.superclass.isin(['vnc_motor','cb_motor'])].copy()
    if not motors.bodyId.map(lambda x:int(x) in index).all():raise ValueError('Motor absent from complete graph')
    motors['graph_index']=motors.bodyId.map(lambda x:index[int(x)])
    motors['limb_annotation']=motors.subclass.map({'fl':'front','ml':'middle','hl':'hind'}).fillna('not a leg annotation')
    motors['source_type_label']=motors.type
    motors['mapping_status']='source annotation only; mechanical mapping unapproved'
    motors['approved_joint']=''
    motors['approved_torque_sign']=''
    motors['approved_gain']=''
    motors['mechanical_evidence']=''
    columns=['bodyId','graph_index','superclass','subclass','limb_annotation',
        'source_type_label','instance','somaSide','rootSide','somaNeuromere','exitNerve',
        'mancBodyid','mancType','mancGroup','matchingNotes','synonyms','status',
        'mapping_status','approved_joint','approved_torque_sign','approved_gain','mechanical_evidence']
    output=ROOT/'reports/malecns_motor_candidates.csv'
    motors[columns].sort_values('graph_index').to_csv(output,index=False)
    legs=motors[motors.subclass.isin(['fl','ml','hl'])]
    report={
        'scope':'Source annotation inventory joined to full graph; no enabled motor mapping',
        'source_sha256':digest,'graph_ids_sha256':hashlib.sha256(ids_path.read_bytes()).hexdigest(),
        'table_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
        'motor_rows':len(motors),'leg_motor_rows':len(legs),
        'leg_rows_with_manc_id':int(legs.mancBodyid.notna().sum()),
        'leg_rows_without_manc_id':int(legs.mancBodyid.isna().sum()),
        'leg_rows_without_root_side':int(legs.rootSide.isna().sum()),
        'counts_by_limb_and_soma_side':[
            {'limb':str(limb),'soma_side':str(side),'count':int(count)}
            for (limb,side),count in legs.groupby(['subclass','somaSide'],dropna=False).size().items()],
        'type_labels':{str(k):int(v) for k,v in legs.type.value_counts(dropna=False).items()},
        'mapping_accepted':False,
        'required_evidence':[
            'Validate MaleCNS-to-MANC matches and muscle-target evidence, including unresolved cells.',
            'Resolve effector side; somaSide alone is not proof of peripheral laterality.',
            'Derive torque signs from anatomical actions and FlyGym joint axes.',
            'Declare gains, time constants and actuator limits as measured or engineering assumptions.',
            'Freeze mapping before rocket training and validate single-path interventions.']}
    (ROOT/'reports/malecns_motor_audit.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='type_labels'},indent=2))

if __name__=='__main__':main()
