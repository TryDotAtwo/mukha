"""Preserve source NT evidence for circuit candidates without assigning signs."""
import hashlib,json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
g=ROOT/'data/derived/malecns_v1_candidates'
path=g/'neurotransmitters.feather'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((g/'manifest.json').read_text())
assert sha(path)==manifest['files'][path.name]['sha256']
paths=json.loads((ROOT/'reports/inhibition_candidate_paths.json').read_text())
source=pd.read_feather(path)
assert source.body.is_unique
ids=[s['body_id'] for s in paths['summaries']]
selected=source.set_index('body').reindex(ids).reset_index()
assert selected.total_nt_predictions.notna().all()
records=json.loads(selected.to_json(orient='records',double_precision=15))
by_id={int(r['body']):r for r in records}
links=[]
for s in paths['summaries']:
    for e in s['candidate_to_candidate']:
        links.append(dict(pre=e['pre_body_id'],post=e['post_body_id'],
            synapse_count=e['synapse_count'],source_row=e['source_row'],
            presynaptic_consensus_nt=by_id[e['pre_body_id']]['consensus_nt'],
            receptor_mechanism=None,functional_sign=None,runtime_enabled=False))
dest=ROOT/'data/derived/inhibition_chemistry_v1'
if dest.exists():raise FileExistsError('Immutable output exists')
dest.mkdir();selected.to_feather(dest/'candidates.feather')
check=pd.read_feather(dest/'candidates.feather')
pd.testing.assert_frame_equal(selected,check)
report=dict(source_nt_sha256=sha(path),candidate_paths_sha256=sha(ROOT/'reports/inhibition_candidate_paths.json'),
    candidates=records,candidate_connections=links,missing_candidates=0,
    exact_source_columns_preserved=True,source_ground_truth_scope='Source annotation; specimen-specific measurement provenance not established here',
    confidence_scope='Source prediction score, not interpreted as calibrated probability',
    ambiguity='DNg74_a and untyped alternative for MANC10107 have different consensus transmitters',
    functional_signs_assigned=False,runtime_enabled=False,
    output_sha256=sha(dest/'candidates.feather'))
(dest/'manifest.json').write_text(json.dumps(report,indent=2))
(ROOT/'reports/inhibition_chemistry.json').write_text(json.dumps(report,indent=2))
print(json.dumps(dict(candidates=len(records),candidate_connections=len(links),
    consensus_counts=selected.consensus_nt.value_counts().to_dict(),
    source_ground_truth_counts=selected.ground_truth.value_counts().to_dict())))
