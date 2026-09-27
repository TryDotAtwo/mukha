"""Inventory annotation candidates only; never infer functional equivalence from names."""
import hashlib
import json
from pathlib import Path
import pyarrow.feather as feather

ROOT=Path(__file__).resolve().parents[1]


def main():
    source=ROOT/'data/raw/malecns_v1/body-annotations-male-cns-v1.0-minconf-0.5.feather'
    lock=json.loads((ROOT/'reports/malecns_source_lock.json').read_text())
    record=next(x for x in lock['files'] if x['name']==source.name)
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    if source_hash!=record['sha256']: raise ValueError('Annotation source lock mismatch')
    frame=feather.read_table(source).to_pandas()
    included=frame.status.eq('Traced') | frame.superclass.fillna('').str.strip().ne('')
    frame=frame[included].copy()
    mn9=frame.type.fillna('').eq('MN9')
    labellar=frame['class'].fillna('').eq('gustatory') & frame.subclass.fillna('').eq('labellar bristle')
    aliases=frame.synonyms.fillna('').str.contains('sugar|bitter',case=False,regex=True)
    table=frame[mn9|labellar|aliases].copy()
    table['candidate_reason']=['MN9 annotation' if value=='MN9' else
        'labellar gustatory annotation' if subclass=='labellar bristle' else
        'central taste-related synonym; not a peripheral input assignment'
        for value,subclass in zip(table.type,table.subclass)]
    table['functional_mapping_status']='unvalidated candidate; do not assign sugar/bitter function by name'
    columns=['bodyId','type','instance','flywireType','superclass','subclass','class','somaSide',
             'rootSide','entryNerve','receptorType','status','matchingNotes','synonyms','candidate_reason','functional_mapping_status']
    path=ROOT/'reports/malecns_transfer_candidates.csv'
    table[columns].to_csv(path,index=False)
    report=dict(source_sha256=source_hash,neural_population_rows=len(frame),
                mn9_candidates=frame.loc[mn9,['bodyId','instance','flywireType']].to_dict('records'),
                labellar_gustatory_candidates=int(labellar.sum()),
                taste_related_synonym_rows=int(aliases.sum()),
                synonym_source='Yao and Scott 2022; https://pmc.ncbi.nlm.nih.gov/articles/PMC8930643/',
                direct_name_search_columns=['type','instance','receptorType'],
                named_sugar_or_bitter_rows=int(frame[['type','instance','receptorType']].fillna('').astype(str)
                    .apply(lambda column:column.str.contains('sugar|bitter',case=False,regex=True)).any(axis=1).sum()),
                candidate_table_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                mapping_accepted=False,
                missing_evidence=['Functional identification of sugar/bitter populations from reconstruction-linked biological sources.',
                                  'Cross-dataset identity and sex-specific differences for source targets.',
                                  'Transfer validation using independent biological outcomes.'],
                scope='Candidate annotation inventory, not a transfer map or physiological validation')
    (ROOT/'reports/malecns_transfer_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
