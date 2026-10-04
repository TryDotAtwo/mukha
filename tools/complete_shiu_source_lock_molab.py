"""Acquire missing immutable author lock entries in MoLab; archive before use."""
import argparse,importlib.util,json,urllib.request
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);args=p.parse_args()
    root=args.root;source=root/'source'
    spec=importlib.util.spec_from_file_location('source_lock_archive',Path('/tmp/fly-hf-capacity-20261004/tools/hf_artifact_archive.py'))
    archive=importlib.util.module_from_spec(spec);spec.loader.exec_module(archive)
    lock=json.loads((source/'reports/shiu_reference_sources.json').read_text())
    prefix='https://raw.githubusercontent.com/philshiu/Drosophila_brain_model/'+lock['commit']+'/'
    paths=[]
    for record in lock['files']:
        path=archive.checked_path(source,record['path'])
        if not record['source_url'].startswith(prefix):raise RuntimeError('Author source origin differs')
        if not path.exists():
            path.parent.mkdir(parents=True,exist_ok=True)
            with urllib.request.urlopen(record['source_url'],timeout=60) as response,path.open('xb') as output:output.write(response.read())
        if path.stat().st_size!=record['bytes'] or archive.digest(path)!=record['sha256']:raise RuntimeError('Author lock mismatch: '+record['path'])
        paths.append(path)
    paths.append(source/'reports/shiu_reference_sources.json')
    files={str(path.relative_to(root)):{'bytes':path.stat().st_size,'sha256':archive.digest(path)} for path in paths}
    receipt=archive.publish(root,{'schema':'faithful-fly-artifacts-v1','files':files})
    (root/'stage-receipts/complete-author-source.json').write_text(json.dumps(receipt,indent=2))
    print('COMPLETE_AUTHOR_SOURCE_RECEIPT',json.dumps(receipt),flush=True)
if __name__=='__main__':main()
