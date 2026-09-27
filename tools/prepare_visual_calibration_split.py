"""Preregister an exploratory split; not the original manuscript fitting split."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'data/reference/chreyesees/data/compiled_data.parquet'
DEST = ROOT/'data/derived/chreyesees_calibration_v1'
WT = {'pR7','yR7','pR8','yR8','pDm8','yDm8','Tm5a','Tm5b','Tm5c','Tm20'}
PERT = {'Tm20-Tnt','Tm5a-TnT','Tm5b-GCaMP-TNT','Tm5c-Tnt'}
INPUTS = ['rh1','rh3','rh4','rh5','rh6']
SALT = b'faithful-fly-visual-calibration-v1\0'


def main():
    manifest = json.loads((ROOT/'reports/chreyesees_sources.json').read_text())
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert source_hash == manifest['files']['data/compiled_data.parquet']['sha256']
    f = pd.read_parquet(SOURCE)
    assert set(f.cell_type) == WT | PERT
    assert not f.duplicated(INPUTS+['cell_type']).any()
    x = f[INPUTS].to_numpy(dtype='<f8',copy=True)
    assert np.isfinite(x).all()
    x[x==0] = 0  # Canonicalize signed zero; do not round or alter other values.
    keys = [hashlib.sha256(SALT+row.tobytes()).hexdigest() for row in x]
    partitions = ['holdout' if int(k[:16],16)%5==0 else 'calibration' for k in keys]
    split = ['perturbation' if c in PERT else p for c,p in zip(f.cell_type,partitions)]
    result = f.copy()
    result.insert(0,'source_row',np.arange(len(f),dtype=np.uint64))
    result['stimulus_key'] = keys
    result['stimulus_partition'] = partitions
    result['split'] = split
    train = result[result.split=='calibration']
    held = result[result.split=='holdout']
    assert set(train.stimulus_key).isdisjoint(set(held.stimulus_key))
    assert set(train.cell_type) <= WT
    assert len(result[result.split=='perturbation']) == f.cell_type.isin(PERT).sum()
    pd.testing.assert_frame_equal(f,result[f.columns])
    counts = {str(k):int(v) for k,v in result.groupby('split').size().items()}
    if DEST.exists():
        raise FileExistsError('Immutable split destination already exists')
    DEST.mkdir(parents=True)
    (DEST/'INCOMPLETE').write_text('Do not consume until manifest is complete')
    output = DEST/'observations.feather'
    result.reset_index(drop=True).to_feather(output)
    report = dict(source_sha256=source_hash, output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
        split_counts=counts, salt=SALT.decode().replace('\0','\\0'),
        rule='SHA256(salt + five little-endian float64 inputs); first 64 bits modulo 5 == 0 is holdout',
        exact_stimulus_overlap_train_holdout=0, all_perturbations_excluded_from_calibration=True,
        original_values_preserved=True, split_independent_of_responses=True,
        cell_split_counts=result.groupby(['cell_type','split']).size().rename('rows').reset_index().to_dict('records'),
        negative_input_values={c:int((f[c]<0).sum()) for c in INPUTS},
        limitations=['Not manuscript gamut selection', 'Not an animal-independent split: identities unavailable',
                    'Only exact stimulus equality grouped; nearby stimuli may cross partitions',
                    'Input transformation unresolved; columns are not validated photon rates'],
        fitting_performed=False, biological_validation_passed=False)
    (DEST/'manifest.json').write_text(json.dumps(report,indent=2))
    (ROOT/'reports/visual_calibration_split.json').write_text(json.dumps(report,indent=2))
    (DEST/'INCOMPLETE').unlink()
    print(json.dumps(counts))


if __name__ == '__main__':
    main()
