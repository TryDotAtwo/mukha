"""Acquire pinned author eye geometry data; no MaleCNS registration implied."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
REPO='neurokernel/neurodriver'
COMMIT='ddafe14295b6fea83e236b3c2ae0334741ed47c9'

def main():
    url=f'https://api.github.com/repos/{REPO}/git/trees/{COMMIT}?recursive=1'
    tree=json.load(urllib.request.urlopen(url,timeout=30))
    if tree.get('truncated'):raise ValueError('Truncated source tree')
    selected=[e for e in tree['tree'] if e['type']=='blob' and
              (e['path'] in ('README.rst','LICENSE','LICENSE.txt','LICENSE.rst','AUTHORS.rst') or
               e['path'].endswith(('/PowerGpotGpot.py','/MorrisLecar.py','/BaseSynapseModel.py','/BaseMembraneModel.py','/Aggregator.py','/NDComponent.py','/LPU.py')))]
    destination=ROOT/'data/reference/neurodriver_graded'
    def fetch(entry):
        path=entry['path'];target=destination/path
        if '..' in Path(path).parts or Path(path).is_absolute():raise ValueError('Invalid tree path')
        source=f'https://raw.githubusercontent.com/{REPO}/{COMMIT}/{path}'
        raw=target.read_bytes() if target.exists() else urllib.request.urlopen(source,timeout=30).read()
        if len(raw)!=entry['size'] or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=entry['sha']:
            raise ValueError(f'Git blob mismatch: {path}')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        return {'path':path,'url':source,'git_blob':entry['sha'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:files=list(pool.map(fetch,selected))
    report={'repository':REPO,'commit':COMMIT,'files':files,'executed':False,
            'scope':'Current author graded-model implementation; historical compatibility with pinned lamina release not established'}
    (ROOT/'reports/neurodriver_graded_sources.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'files':len(files),'bytes':sum(f['bytes'] for f in files),'commit':COMMIT}))

if __name__=='__main__':main()
