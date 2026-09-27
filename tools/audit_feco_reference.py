"""Check published FeCO annotation joins and aggregate synapse rows, not scores."""
import hashlib,json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
source=json.loads((ROOT/'reports/feco_reference_sources.json').read_text())
base=ROOT/'data/reference/lee_feco'
for name,meta in source['files'].items():
    raw=(base/name).read_bytes()
    assert len(raw)==meta['bytes'] and hashlib.sha256(raw).hexdigest()==meta['sha256']
folder=base/'synapse_tables'
a=pd.read_csv(folder/'feco_annotation_table.csv',dtype={'pt_root_id':'uint64','pt_supervoxel_id':'uint64'})
assert a.pt_root_id.is_unique and a.valid.eq('t').all()
dest=ROOT/'data/derived/fanc_feco_reference_v1'
if dest.exists():raise FileExistsError('Immutable output already exists')
dest.mkdir();(dest/'INCOMPLETE').write_text('unfinished')
stats={};files={}
for direction,side in [('downstream','pre_pt_root_id'),('upstream','post_pt_root_id')]:
    f=pd.read_csv(folder/f'feco_{direction}_connections.csv',dtype={'pre_pt_root_id':'uint64','post_pt_root_id':'uint64','id':'uint64'})
    assert f.id.is_unique and f.valid.eq('t').all()
    assert f[side].isin(a.pt_root_id).all()
    pairs=f.groupby(['pre_pt_root_id','post_pt_root_id'],sort=True).size().rename('synapse_rows').reset_index()
    assert int(pairs.synapse_rows.sum())==len(f)
    counts=f.groupby(side).size()
    annotated=a[['pt_root_id','classification_system','cell_type']].copy()
    annotated['synapse_rows']=annotated.pt_root_id.map(counts).fillna(0).astype('uint64')
    stats[direction]=dict(rows=len(f),pairs=len(pairs),zero_degree_annotated_neurons=int((annotated.synapse_rows==0).sum()),
        score_range=[int(f.score.min()),int(f.score.max())],
        class_totals=annotated.groupby('cell_type').synapse_rows.sum().astype(int).to_dict())
    path=dest/f'{direction}_pairs.feather';pairs.to_feather(path)
    files[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
report=dict(commit=source['commit'],annotated_neurons=len(a),
    nerve_class_counts=a.groupby(['classification_system','cell_type']).size().rename('neurons').reset_index().to_dict('records'),
    connectivity=stats,files=files,score_used_as_weight=False,additional_threshold_applied=False,
    scope='FANC reference subset only; all published records retained, not full biological connectivity',
    malecns_crosswalk_verified=False,functional_rate_model_fitted=False,runtime_enabled=False)
(dest/'manifest.json').write_text(json.dumps(report,indent=2))
(ROOT/'reports/feco_reference_audit.json').write_text(json.dumps(report,indent=2))
(dest/'INCOMPLETE').unlink()
print(json.dumps(stats,indent=2))
