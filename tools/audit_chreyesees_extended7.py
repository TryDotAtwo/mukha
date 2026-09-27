"""Inspect publisher source data without treating absent samples as zeros."""
import hashlib
import io
import json
import zipfile
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
source = json.loads((ROOT/'reports/chreyesees_extended7_source.json').read_text())
raw = (ROOT/'data/reference/chreyesees_paper/extended_data_7.zip').read_bytes()
assert len(raw) == source['bytes']
assert hashlib.sha256(raw).hexdigest() == source['sha256']
with zipfile.ZipFile(io.BytesIO(raw)) as archive:
    assert archive.namelist() == ['Figure S7.parquet']
    payload = archive.read('Figure S7.parquet')
frame = pd.read_parquet(io.BytesIO(payload))
times = [c for c in frame if c.startswith('t=')]
assert len(times) == 100
finite = np.isfinite(frame[times].to_numpy())
groups = []
for name in frame.cell_type.unique():
    mask = frame.cell_type.eq(name).to_numpy()
    group = finite[mask]
    groups.append(dict(cell_type=name,rows=int(mask.sum()),
                       rows_with_any_time_sample=int(group.any(axis=1).sum()),
                       rows_with_all_time_samples=int(group.all(axis=1).sum()),
                       finite_time_samples=int(group.sum())))
report = dict(archive_sha256=source['sha256'],
    parquet_sha256=hashlib.sha256(payload).hexdigest(),rows=len(frame),
    time_columns=times,groups=groups,
    non_time_columns=[c for c in frame if c not in times],
    contains_named_weight_matrix=False,
    scope='Publisher Extended Data 7 source-data inventory; no fitted weights recovered or model validated')
(ROOT/'reports/chreyesees_extended7_audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps(dict(rows=len(frame),groups=groups),indent=2))
