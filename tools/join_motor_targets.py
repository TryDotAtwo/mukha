"""Exact reconstruction-ID join; conflicts remain unresolved, never auto-wired."""
import hashlib
import json
from pathlib import Path
import urllib.request
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
URL='https://cdn.elifesciences.org/articles/96084/elife-96084-supp3-v1.csv'
SHA='c46e3cec1a5114b8d981d5f0383012c8e7fcdebd6c4e3eaffe4ac3ba1def2e94'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def normal(value):
    return str(value).strip().removesuffix(' MN').strip().casefold()

def main():
    source=ROOT/'data/reference/manc_motor/elife-96084-supp3-v1.csv'
    if not source.exists():
        raw=urllib.request.urlopen(URL,timeout=30).read()
        if hashlib.sha256(raw).hexdigest()!=SHA:raise ValueError('Published source bytes differ from pin')
        source.parent.mkdir(parents=True,exist_ok=True);source.write_bytes(raw)
    if sha(source)!=SHA:raise ValueError('MANC supplement hash mismatch')
    candidates=ROOT/'reports/malecns_motor_candidates.csv'
    audit=json.loads((ROOT/'reports/malecns_motor_audit.json').read_text())
    if sha(candidates)!=audit['table_sha256']:raise ValueError('Candidate table changed')
    motor=pd.read_csv(candidates)
    legs=motor[motor.subclass.isin(['fl','ml','hl'])].copy()
    manc=pd.read_csv(source).add_prefix('manc_')
    result=legs.merge(manc,left_on='mancBodyid',right_on='manc_bodyid',how='left',validate='many_to_one',indicator=True)
    matched=result._merge.eq('both')
    result['exact_id_match']=matched
    result['match_basis']='predicted mancBodyid; exact key lookup is not curated cell identity'
    result['source_label_disagreement']=matched & (result.source_type_label.map(normal)!=result.manc_target.map(normal))
    result['manc_exit_side']=result.manc_exit_nerve.str.extract(r'_([LR])$')[0]
    result['side_metadata_disagreement']=matched & result.manc_exit_side.notna() & result.somaSide.notna() & result.manc_exit_side.ne(result.somaSide)
    result['source_target_is_limb_only']=result.manc_target.isin(['front leg','middle leg','hind leg'])
    result['mapping_status']='unapproved; cross-dataset annotation evidence, not a mechanical map'
    result=result.drop(columns=['_merge'])
    path=ROOT/'reports/malecns_manc_motor_targets.csv'
    result.to_csv(path,index=False)
    conflicts=result[result.source_label_disagreement|result.side_metadata_disagreement]
    conflict_path=ROOT/'reports/motor_target_conflicts.csv';conflicts.to_csv(conflict_path,index=False)
    report={'source_url':URL,'source_sha256':SHA,'candidate_sha256':sha(candidates),
        'joined_table_sha256':sha(path),'conflicts_sha256':sha(conflict_path),
        'leg_rows':len(result),'exact_id_matches':int(matched.sum()),
        'unmatched_with_manc_id':int((~matched & result.mancBodyid.notna()).sum()),
        'missing_manc_id':int(result.mancBodyid.isna().sum()),
        'source_label_disagreements':int(result.source_label_disagreement.sum()),
        'side_metadata_disagreements':int(result.side_metadata_disagreement.sum()),
        'limb_only_targets':int(result.source_target_is_limb_only.sum()),
        'matched_without_confidence':int((matched & result['manc_match_certainty(1-5)'].isna()).sum()),
        'approved_mappings':0,
        'match_basis':'mancBodyid is predicted, not curated; use mancGroup for curated groups',
        'semantics_source':'https://natverse.org/malecns/reference/mcns_predict_group.html',
        'scope':'Exact lookup of predicted IDs only, not confirmed cross-dataset identity'}
    (ROOT/'reports/motor_target_join.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
