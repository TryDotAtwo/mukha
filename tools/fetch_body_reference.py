"""Fetch pinned NeuroMechFly assets and its supported native MuJoCo runtime."""
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
COMMIT='ca65a510c2afe6ac61c51df4f274c8d190c2f95f'


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'faithful-fly-research'}),timeout=45) as response:
        return response.read()


def main():
    tree=json.loads(get(f'https://api.github.com/repos/NeLy-EPFL/flygym/git/trees/{COMMIT}?recursive=1'))
    if tree.get('truncated'): raise ValueError('Incomplete source tree')
    destination=ROOT/'data/reference/flygym_2.1.0'
    records=[]
    for entry in tree['tree']:
        name=entry['path']
        selected=(name.startswith('src/flygym/assets/model/neuromechfly/') or
                  (name.startswith('src/flygym/') and name.endswith('.py')) or name in ('LICENSE','README.md','pyproject.toml'))
        if entry['type']!='blob' or not selected: continue
        path=destination/name
        if not path.resolve().is_relative_to(destination.resolve()): raise ValueError('Unsafe source path')
        url=f'https://raw.githubusercontent.com/NeLy-EPFL/flygym/{COMMIT}/{name}'
        content=path.read_bytes() if path.exists() else get(url)
        blob=hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
        if len(content)!=entry['size'] or blob!=entry['sha']: raise ValueError('Source blob mismatch: '+name)
        path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():path.write_bytes(content)
        records.append(dict(path=str(path.relative_to(ROOT)),source_url=url,bytes=len(content),git_blob=blob,
                            sha256=hashlib.sha256(content).hexdigest()))
        if len(records)%20==0:print(json.dumps(dict(flygym_files_verified=len(records))),flush=True)
    archive=ROOT/'data/reference/mujoco_3.9.0.zip'
    url='https://github.com/google-deepmind/mujoco/releases/download/3.9.0/mujoco-3.9.0-windows-x86_64.zip'
    expected='544f44a8a7df3e94648a7eaf41500f4456eb59f9f01df3ec2cfb03bdbf5c2bb9'
    content=archive.read_bytes() if archive.exists() else get(url)
    if len(content)!=12617742 or hashlib.sha256(content).hexdigest()!=expected: raise ValueError('MuJoCo release hash mismatch')
    if not archive.exists():archive.write_bytes(content)
    runtime=ROOT/'data/reference/mujoco_3.9.0'
    extracted=[]
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            target=runtime/member.filename
            if not target.resolve().is_relative_to(runtime.resolve()) or (member.external_attr>>16)&0o170000==0o120000:
                raise ValueError('Unsafe archive member')
            if member.is_dir():continue
            data=zipped.read(member)
            if target.exists() and target.read_bytes()!=data: raise ValueError('Existing runtime differs')
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists():target.write_bytes(data)
            extracted.append(dict(path=str(target.relative_to(ROOT)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
    report=dict(flygym_repository='NeLy-EPFL/flygym',flygym_tag='v2.1.0',flygym_commit=COMMIT,
                flygym_files=records,mujoco_version='3.9.0',mujoco_source_url=url,mujoco_archive_sha256=expected,
                runtime_files=extracted,
                version_reason='Pinned FlyGym pyproject.toml requires mujoco>=3.9,<3.10; latest 3.13 was not selected.',
                scope='Published anatomy/configuration and native runtime acquired; no body simulation or neural motor mapping validated',
                executed=False)
    (ROOT/'reports/body_reference_sources.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(flygym_files=len(records),runtime_files=len(extracted),executed=False)))


if __name__=='__main__':main()
