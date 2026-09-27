"""Resumable, generation-pinned acquisition of the selected MaleCNS SWCs."""
import argparse
import base64
import concurrent.futures
import csv
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/malecns_swc_bucket_inventory.json'
OUT = ROOT / 'data/raw/malecns_v1_swcs'


def check(path, row):
    payload = path.read_bytes()
    return (len(payload) == int(row['bytes']) and
            base64.b64encode(hashlib.md5(payload).digest()).decode() == row['md5_base64'])


def fetch(body, row):
    path = OUT / f'{body}.swc'
    if path.exists():
        if not check(path, row):
            raise ValueError(f'existing SWC differs from inventory: {path}')
        return 'verified_existing', path.stat().st_size
    prefix = 'https://storage.googleapis.com/flyem-male-cns/v1.0/segmentation/'
    url = prefix + f'skeletons-malecns/skeletons-swc/{body}.swc'
    response = requests.get(url, params={'generation': row['generation']}, timeout=90)
    response.raise_for_status()
    payload = response.content
    if len(payload) != int(row['bytes']):
        raise ValueError(f'byte count mismatch for {body}')
    if base64.b64encode(hashlib.md5(payload).digest()).decode() != row['md5_base64']:
        raise ValueError(f'source MD5 mismatch for {body}')
    temp = path.with_suffix('.swc.part')
    temp.write_bytes(payload)
    temp.replace(path)
    return 'downloaded', len(payload)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-new', type=int, default=256)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    if args.max_new < 1 or not 1 <= args.workers <= 32:
        raise ValueError('invalid max-new or worker count')
    report = json.loads(REPORT.read_text(encoding='utf-8'))
    inventory_path = ROOT / report['inventory_path']
    assert hashlib.sha256(inventory_path.read_bytes()).hexdigest() == report['inventory_sha256']
    with gzip.open(inventory_path, 'rt', encoding='utf-8', newline='') as file:
        inventory = {int(row['body_id']): row for row in csv.DictReader(file)}
    ids = sorted(map(int, np.load(ROOT / 'data/derived/malecns_v1_candidates/body_ids.npy')))
    assert set(ids) <= inventory.keys()
    OUT.mkdir(parents=True, exist_ok=True)
    pending = [body for body in ids if not (OUT / f'{body}.swc').exists()][:args.max_new]
    existing = [body for body in ids if (OUT / f'{body}.swc').exists()]
    for body in existing:
        if not check(OUT / f'{body}.swc', inventory[body]):
            raise ValueError(f'existing SWC differs from inventory: {body}')
    downloaded = 0
    bytes_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(fetch, body, inventory[body]): body for body in pending}
        for future in concurrent.futures.as_completed(futures):
            status, size = future.result()
            assert status == 'downloaded'
            downloaded += 1
            bytes_count += size
            if downloaded % 512 == 0:
                print(f'downloaded={downloaded}/{len(pending)} bytes={bytes_count}', flush=True)
    print(json.dumps({'previous_verified': len(existing), 'new_downloaded': downloaded,
                      'new_bytes': bytes_count, 'local_total': len(existing) + downloaded,
                      'population': len(ids), 'source_inventory_sha256': report['inventory_sha256']}))


if __name__ == '__main__':
    main()
