"""Keep build-bound checkpoints reproducible across native library rebuilds."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parents[1]
def archive_build():
    report=json.loads((ROOT/'reports/photon_build.json').read_text())
    identity=report['build_identity'];assert re.fullmatch('[a-f0-9]{64}',identity)
    fingerprint={k:v for k,v in report.items() if k not in ('build_identity','command','binary_sha256')}
    assert hashlib.sha256(json.dumps(fingerprint,sort_keys=True).encode()).hexdigest()==identity
    files={}
    for name,expected in report['sources'].items():
        path=(ROOT/name).resolve();assert path.is_relative_to(ROOT)
        data=path.read_bytes();assert hashlib.sha256(data).hexdigest()==expected,name
        files[name]=data
    library=(ROOT/report['command'][-1]).resolve();assert library.is_relative_to(ROOT)
    data=library.read_bytes();assert hashlib.sha256(data).hexdigest()==report['binary_sha256']
    files[str(library.relative_to(ROOT)).replace('\\','/')]=data
    files['reports/photon_build.json']=json.dumps(report,indent=2).encode()
    files['build/photon_build_id.h']=('#pragma once\n#define FP_BUILD_ID "'+identity+'"\n').encode()
    destination=ROOT/'build/photon-builds';destination.mkdir(exist_ok=True)
    path=destination/(identity+'.zip')
    if path.exists():
        with zipfile.ZipFile(path) as z:
            assert set(z.namelist())==set(files)
            assert all(z.read(name)==value for name,value in files.items())
    else:
        with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for name,value in files.items():z.writestr(name,value)
    print('Archived verified native build',identity)
    return path
if __name__=='__main__':archive_build()
