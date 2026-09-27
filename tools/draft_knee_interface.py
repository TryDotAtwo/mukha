"""Explicit engineering proposal from curated targets and measured model axes."""
import hashlib
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    table=ROOT/'reports/curated_motor_targets.csv'
    resolution=json.loads((ROOT/'reports/curated_motor_resolution.json').read_text())
    if sha(table)!=resolution['output_sha256']:raise ValueError('Curated evidence changed')
    calibration=ROOT/'reports/knee_axis_calibration.json'
    axes=json.loads(calibration.read_text())
    lookup={r['leg']:r for r in axes['results']}
    cells=pd.read_csv(table)
    selected=cells[cells.curated_evidence_status.eq('curated_group_and_muscle_label_agree') &
                   cells.curated_target.isin(['Ti flexor','Acc. ti flexor','Ti extensor'])]
    entries=[]
    for _,row in selected.iterrows():
        if row.somaSide not in ['L','R']:raise ValueError('Unknown side')
        leg=row.somaSide.lower()+{'fl':'f','ml':'m','hl':'h'}[row.subclass]
        axis=lookup[leg];flex=row.curated_target!='Ti extensor'
        entries.append({'body_id':int(row.bodyId),'graph_index':int(row.graph_index),
            'curated_manc_group':int(row.mancGroup),'muscle_annotation':row.curated_target,
            'proposed_joint':axis['joint'],'proposed_torque_sign':axis['local_flexion_q_sign' if flex else 'local_extension_q_sign'],
            'gain':None,'activation_time_constant_ms':None,'enabled':False,
            'assumptions':['Effector side equals annotated soma side; needs anatomical validation.',
                           'Muscle action is approximated by a pure knee-pitch torque.',
                           'Accessory and principal flexors aggregate onto one joint axis.']})
    report={'scope':'Disabled engineering interface draft, not a validated biological motor map',
        'curated_table_sha256':sha(table),'axis_calibration_sha256':sha(calibration),
        'entries':entries,'unrepresented_leg_motor_rows':len(cells)-len(entries),
        'unrepresented_cells_remain_in_full_neural_graph':True,
        'ready_for_neural_control':False}
    (ROOT/'configs/knee_interface_draft.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'draft_entries':len(entries),'joints':len(set(e['proposed_joint'] for e in entries)),
                      'enabled':False,'remaining_leg_motor_rows':len(cells)-len(entries)}))

if __name__=='__main__':main()
