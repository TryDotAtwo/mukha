"""Pin public FeCO connectivity data; no CAVE credentials or code execution."""
import hashlib,json
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
COMMIT='4328b1d5549749f1014c4d73cccc0c5241d98ae4'
FILES=['README.md']+['synapse_tables/'+n for n in [
    'feco_annotation_table.csv','downstream_feco_annotation_table.csv',
    'upstream_feco_annotation_table.csv','feco_downstream_connections.csv',
    'feco_upstream_connections.csv','third_order_club_annotation_table.csv']]
dest=ROOT/'data/reference/lee_feco';dest.mkdir(parents=True,exist_ok=True)
files={};session=requests.Session()
for name in FILES:
    url=f'https://raw.githubusercontent.com/sagrawal/Lee_2024/{COMMIT}/{name}'
    r=session.get(url,stream=True,timeout=30);r.raise_for_status()
    raw=bytearray()
    for part in r.iter_content(1<<20):
        raw.extend(part)
        if len(raw)>8*1024**2:raise ValueError('reference file exceeds cap')
    p=dest/name;p.parent.mkdir(exist_ok=True)
    if p.exists() and p.read_bytes()!=raw:raise ValueError('existing reference differs')
    p.write_bytes(raw)
    files[name]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
report=dict(repository='https://github.com/sagrawal/Lee_2024',commit=COMMIT,
    doi='10.1038/s41467-025-59302-3',files=files,
    scope='Published FANC connectivity tables, not a MaleCNS mapping or physiological rate model',
    code_executed=False,credentials_used=False)
(ROOT/'reports/feco_reference_sources.json').write_text(json.dumps(report,indent=2))
print(json.dumps(dict(commit=COMMIT,files=len(files),bytes=sum(v['bytes'] for v in files.values()))))
