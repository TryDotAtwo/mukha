"""Inventory published MaleCNS v1.0 SWCs against the exact runtime population."""
import csv
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'v1.0/segmentation/skeletons-malecns/skeletons-swc/'
API = 'https://storage.googleapis.com/storage/v1/b/flyem-male-cns/o'
OUT = ROOT / 'data/derived/malecns_v1_swc_bucket_inventory.csv.gz'
REPORT = ROOT / 'reports/malecns_swc_bucket_inventory.json'


def main():
    population = set(map(int, np.load(ROOT / 'data/derived/malecns_v1_candidates/body_ids.npy')))
    listed = {}
    token = None
    pages = 0
    session = requests.Session()
    while True:
        params = {'prefix': PREFIX, 'maxResults': 1000,
                  'fields': 'nextPageToken,items(name,size,generation,md5Hash,crc32c)'}
        if token:
            params['pageToken'] = token
        response = session.get(API, params=params, timeout=60)
        response.raise_for_status()
        page = response.json()
        for obj in page.get('items', []):
            name = obj['name']
            if not name.startswith(PREFIX) or not name.endswith('.swc'):
                continue
            stem = name[len(PREFIX):-4]
            if not stem.isdecimal():
                continue
            body = int(stem)
            if body in listed:
                raise ValueError(f'duplicate SWC body ID: {body}')
            listed[body] = (int(obj['size']), obj['generation'], obj.get('md5Hash', ''),
                            obj.get('crc32c', ''))
        pages += 1
        if pages % 50 == 0:
            print(f'pages={pages} swcs={len(listed)}', flush=True)
        token = page.get('nextPageToken')
        if not token:
            break
        if pages >= 1000:
            raise RuntimeError('inventory exceeds 1000 pages; no partial report written')

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, 'wt', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['body_id', 'bytes', 'generation', 'md5_base64', 'crc32c_base64'])
        for body in sorted(listed):
            writer.writerow([body, *listed[body]])
    covered = population & listed.keys()
    missing = population - listed.keys()
    report = {
        'dataset': 'male-cns:v1.0',
        'source': API,
        'prefix': PREFIX,
        'pages': pages,
        'listed_swc_files': len(listed),
        'graph_population': len(population),
        'graph_ids_with_published_swc': len(covered),
        'graph_ids_without_published_swc': len(missing),
        'missing_graph_ids': sorted(missing),
        'published_bytes_for_graph_ids': sum(listed[body][0] for body in covered),
        'inventory_path': str(OUT.relative_to(ROOT)).replace('\\', '/'),
        'inventory_sha256': hashlib.sha256(OUT.read_bytes()).hexdigest(),
        'scope': 'Public bucket metadata listing, not downloaded skeleton validation; '
                 'file existence does not prove morphology completeness.'
    }
    REPORT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'missing_graph_ids'}), flush=True)


if __name__ == '__main__':
    main()
