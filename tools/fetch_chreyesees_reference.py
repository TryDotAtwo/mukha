"""Acquire pinned author source/data without installing or executing it."""
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
import requests

ROOT = Path(__file__).resolve().parents[1]
COMMIT = '91cf92581d2abaea72b96a994d69ed6d83ae05f9'
API = 'https://gitlab.com/api/v4/projects/51649890'
OUT = ROOT / 'data/reference/chreyesees'


def main():
    session = requests.Session()
    entries = []
    page = 1
    while True:
        response = session.get(API+'/repository/tree', params=dict(
            ref=COMMIT, recursive=True, per_page=100, page=page), timeout=30)
        response.raise_for_status()
        batch = response.json()
        entries.extend(batch)
        if not response.headers.get('X-Next-Page'):
            break
        page = int(response.headers['X-Next-Page'])
    files = {}
    total = 0
    for entry in entries:
        name = entry['path']
        if entry['type'] != 'blob' or '__pycache__' in name or name.endswith(('.pyc', '.DS_Store', '.gitkeep')):
            continue
        path = OUT / name
        if not path.resolve().is_relative_to(OUT.resolve()):
            raise ValueError('Unsafe repository path')
        response = session.get(API+'/repository/files/'+quote(name, safe='')+'/raw',
                               params={'ref': COMMIT}, stream=True, timeout=60)
        response.raise_for_status()
        chunks = []
        size = 0
        for chunk in response.iter_content(1024*1024):
            size += len(chunk)
            total += len(chunk)
            if size > 32*1024**2 or total > 100*1024**2:
                raise ValueError('Bounded acquisition size exceeded')
            chunks.append(chunk)
        data = b''.join(chunks)
        if path.exists() and path.read_bytes() != data:
            raise ValueError(f'Refusing to replace different content: {name}')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        files[name] = dict(bytes=size, sha256=hashlib.sha256(data).hexdigest())
    report = dict(repository='https://gitlab.com/rbehnialab/chreyesees',
                  doi='10.1038/s41593-024-01640-4', commit=COMMIT, files=files,
                  total_bytes=total, author_code_executed=False,
                  scope='Source and processed data acquisition; no model replication or MaleCNS transfer')
    (ROOT/'reports/chreyesees_sources.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(dict(commit=COMMIT, files=len(files), bytes=total)))


if __name__ == '__main__':
    main()
