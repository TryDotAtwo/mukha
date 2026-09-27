"""Preserve annotated proprioceptors; do not infer a functional sensory encoder."""
import hashlib,json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
graph=ROOT/'data/derived/malecns_v1_candidates'
manifest=json.loads((graph/'manifest.json').read_text())
raw=(graph/'nodes.feather').read_bytes()
assert hashlib.sha256(raw).hexdigest()==manifest['files']['nodes.feather']['sha256']
nodes=pd.read_feather(graph/'nodes.feather')
selected=nodes[nodes['class'].eq('mechanosensory_proprioceptive')].copy()
assert selected.bodyId.is_unique and selected.compact_index.is_unique
leg_nerves={'ProLN':'front','MesoLN':'middle','MetaLN':'hind'}
selected['candidate_leg_segment']=selected.entryNerve.map(leg_nerves)
selected['peripheral_side_annotation']=selected.rootSide
selected['functional_encoder']=None
selected['joint_binding']=None
selected['gain']=None
selected['runtime_enabled']=False
chord=selected[selected['subclass'].eq('chordotonal organ')]
group=chord.groupby(['entryNerve','rootSide'],dropna=False).size().rename('objects').reset_index()
all_leg=nodes[nodes.entryNerve.isin(leg_nerves)]
report=dict(scope='Anatomical candidate inventory only; no functional FeCO assignment or neural injection',
    node_source_sha256=hashlib.sha256(raw).hexdigest(),
    graph_manifest_sha256=hashlib.sha256((graph/'manifest.json').read_bytes()).hexdigest(),
    annotated_proprioceptors=len(selected),chordotonal_objects=len(chord),
    leg_nerve_chordotonal_objects=int(chord.entryNerve.isin(leg_nerves).sum()),
    other_chordotonal_objects=int((~chord.entryNerve.isin(leg_nerves)).sum()),
    chordotonal_nerve_side_counts=group.to_dict('records'),
    proprioceptive_subclasses=selected['subclass'].fillna('unassigned').value_counts().to_dict(),
    all_leg_nerve_class_counts=all_leg.groupby(['entryNerve','class'],dropna=False).size().rename('objects').reset_index().fillna('unassigned').to_dict('records'),
    runtime_enabled=False,
    limitations=['Annotations are not a completeness estimate of biological sensory populations',
                 'Leg nerve does not uniquely identify a joint or receptor subtype',
                 'Root side is preserved separately; no soma-side substitution',
                 'No position/velocity/contact-to-spike transduction is fitted'])
dest=ROOT/'data/derived/proprioceptive_candidates_v1'
if dest.exists():raise FileExistsError('Immutable output already exists')
dest.mkdir();(dest/'INCOMPLETE').write_text('incomplete export')
out=dest/'nodes.feather';selected.reset_index(drop=True).to_feather(out)
reloaded=pd.read_feather(out)
pd.testing.assert_frame_equal(selected[nodes.columns].reset_index(drop=True),reloaded[nodes.columns])
assert not reloaded.runtime_enabled.any()
report['output_sha256']=hashlib.sha256(out.read_bytes()).hexdigest()
(dest/'manifest.json').write_text(json.dumps(report,indent=2))
(ROOT/'reports/proprioceptive_candidates.json').write_text(json.dumps(report,indent=2))
(dest/'INCOMPLETE').unlink()
print(json.dumps({k:v for k,v in report.items() if k not in ['all_leg_nerve_class_counts']},indent=2))
