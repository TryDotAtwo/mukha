"""Fetch pinned, Git-blob-verified original Shiu reference inputs (MIT).

Files are data/research inputs; this command never imports downloaded code or
unpickles objects. A manifest records both Git blob identities and SHA-256.
"""
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = 'philshiu/Drosophila_brain_model'
COMMIT = '91bdd1e7dcf193f3e7ca5a8933497fcef63b7960'
FILES = ['LICENSE', 'model.py', 'Readme.md', 'environment_full.yml',
         'example.ipynb', 'figures.ipynb', 'sez_neurons.pickle',
         '2023_03_23_completeness_630_final.csv',
         '2023_03_23_connectivity_630_final.parquet',
         'results/example/sugarR_100Hz.parquet']


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'FlyRocketResearch'}), timeout=90)


def main():
    tree = json.load(get(f'https://api.github.com/repos/{REPO}/git/trees/{COMMIT}?recursive=1'))
    entries = {i['path']: i for i in tree['tree'] if i['type'] == 'blob'}
    out = ROOT/'data/reference/shiu_2024'
    out.mkdir(parents=True, exist_ok=True)
    records = []
    for name in FILES:
        info = entries[name]
        dest = out/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = f'https://raw.githubusercontent.com/{REPO}/{COMMIT}/{name}'
        if not dest.exists():
            partial = dest.with_suffix(dest.suffix+'.part')
            with get(url) as response, partial.open('wb') as f:
                while chunk := response.read(4 << 20):
                    f.write(chunk)
            partial.replace(dest)
        h = hashlib.sha1(f'blob {info["size"]}\0'.encode())
        sha = hashlib.sha256()
        with dest.open('rb') as f:
            while chunk := f.read(4 << 20):
                h.update(chunk); sha.update(chunk)
        if dest.stat().st_size != info['size'] or h.hexdigest() != info['sha']:
            raise ValueError('Pinned source mismatch: '+name)
        records.append({'path': str(dest.relative_to(ROOT)).replace('\\','/'),
                        'source_url': url, 'bytes': info['size'], 'git_blob': info['sha'], 'sha256': sha.hexdigest()})
        print('Verified '+name, flush=True)
    (ROOT/'reports/shiu_reference_sources.json').write_text(json.dumps({
        'repository': REPO, 'commit': COMMIT, 'license': 'MIT (see downloaded LICENSE)',
        'files': records, 'executed': False}, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
