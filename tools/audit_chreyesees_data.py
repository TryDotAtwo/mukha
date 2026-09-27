"""Inventory the pinned processed observations; never interpret missing as zero."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
source = json.loads((ROOT/'reports/chreyesees_sources.json').read_text())
base = ROOT/'data/reference/chreyesees'
for name, metadata in source['files'].items():
    raw = (base/name).read_bytes()
    assert len(raw) == metadata['bytes']
    assert hashlib.sha256(raw).hexdigest() == metadata['sha256'], name
frame = pd.read_parquet(base/'data/compiled_data.parquet')
numeric = frame.select_dtypes(include='number')
report = dict(
    commit=source['commit'], all_source_hashes_verified=True,
    rows=len(frame), columns=list(frame.columns),
    rows_per_cell_type={str(k):int(v) for k,v in frame.groupby('cell_type').size().items()},
    missing_per_column={k:int(v) for k,v in frame.isna().sum().items()},
    nonfinite_per_numeric_column={k:int((~np.isfinite(numeric[k])).sum()) for k in numeric},
    duplicated_full_rows=int(frame.duplicated().sum()),
    dm9_rows=int(frame.cell_type.eq('Dm9').sum()),
    input_columns=['rh1','rh3','rh4','rh5','rh6'],
    response_column='r',
    source_code_executed=False, published_fit_reproduced=False,
    malecns_transfer_enabled=False,
    scope='Processed data inventory only; units and fitting protocol require author-method reconciliation')
(ROOT/'reports/chreyesees_data_audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
