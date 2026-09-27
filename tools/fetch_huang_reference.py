"""Acquire immutable author sources and fitted parameters for the MB baseline."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
REPO='schnitzer-lab/Luo_Huang_2024_MB_model'
COMMIT='5d7c08a9a88f923169a0c3008aca68af421e9a7f'

def main():
    url=f'https://api.github.com/repos/{REPO}/git/trees/{COMMIT}?recursive=1'
    tree=json.load(urllib.request.urlopen(url,timeout=30))
    if tree.get('truncated'):raise ValueError('Truncated source tree')
    selected=[e for e in tree['tree'] if e['type']=='blob' and
              (e['path']=='README.md' or e['path'].startswith('data_and_parameters/') or
               e['path']=='matlab_code/figure_code_examples/figures/figure5d27-Mar-2023_3modules.fig' or
               (e['path'].endswith('.m') and '/customcolormap/' not in e['path']))]
    destination=ROOT/'data/reference/huang_2024'
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
            'scope':'Original recurrent MB equation model and fitted data; not a spiking full-CNS plasticity implementation'}
    (ROOT/'reports/huang_reference_sources.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'files':len(files),'bytes':sum(f['bytes'] for f in files),'commit':COMMIT}))

if __name__=='__main__':main()
