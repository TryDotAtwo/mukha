"""Prefer curated group evidence; retain unresolved cells in the full graph."""
import hashlib
import json
from pathlib import Path
import pandas as pd
from join_motor_targets import normal, SHA

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    source=ROOT/'data/reference/manc_motor/elife-96084-supp3-v1.csv'
    candidates=ROOT/'reports/malecns_motor_candidates.csv'
    if sha(source)!=SHA:raise ValueError('Target source changed')
    audit=json.loads((ROOT/'reports/malecns_motor_audit.json').read_text())
    if sha(candidates)!=audit['table_sha256']:raise ValueError('Candidates changed')
    a=pd.read_csv(candidates);a=a[a.subclass.isin(['fl','ml','hl'])].copy()
    source_frame=pd.read_csv(source)
    targets=source_frame.groupby('group').target.agg(lambda x:sorted(set(x.dropna().str.strip())))
    a['curated_group_targets']=a.mancGroup.map(targets)
    a['curated_target']=a.curated_group_targets.map(lambda x:x[0] if isinstance(x,list) and len(x)==1 else '')
    a['curated_evidence_status']=[
        'no_curated_group' if pd.isna(group) else
        'group_missing_or_ambiguous' if not target else
        'limb_only_target' if target in ['front leg','middle leg','hind leg'] else
        'muscle_label_disagreement' if normal(label)!=normal(target) else
        'curated_group_and_muscle_label_agree'
        for group,target,label in zip(a.mancGroup,a.curated_target,a.source_type_label)]
    a['mapping_status']='mechanical mapping not enabled; gains, axes and effector-side validation pending'
    output=ROOT/'reports/curated_motor_targets.csv';a.to_csv(output,index=False)
    serial=ROOT/'data/reference/manc_motor/elife-96084-supp6-v1.csv'
    serial_sha='b56b0563f6a6000b2a43fbc7ebec46297668e8e3b6c6d596843d5ad5aab83a65'
    if sha(serial)!=serial_sha:raise ValueError('Serial source changed')
    s=pd.read_csv(serial)
    shared=s.merge(source_frame[['bodyid','target']],on='bodyid',suffixes=('_serial','_target'),validate='one_to_one')
    disagreements=int(shared.target_serial.map(normal).ne(shared.target_target.map(normal)).sum())
    report={'scope':'Curated group-to-muscle annotation evidence, no mechanical mapping',
        'semantics_source':'https://natverse.org/malecns/reference/mcns_predict_group.html',
        'source_sha256':SHA,'candidate_sha256':sha(candidates),'output_sha256':sha(output),
        'status_counts':a.curated_evidence_status.value_counts().to_dict(),
        'serial_source_url':'https://cdn.elifesciences.org/articles/96084/elife-96084-supp6-v1.csv',
        'serial_source_sha256':serial_sha,'serial_target_shared_ids':len(shared),
        'serial_target_disagreements':disagreements,'enabled_motor_mappings':0}
    (ROOT/'reports/curated_motor_resolution.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
