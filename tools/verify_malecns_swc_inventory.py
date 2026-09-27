"""Verify saved bucket inventory and pinned local SWC generations offline."""
import csv
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/malecns_swc_bucket_inventory.json'


def main():
    report = json.loads(REPORT.read_text(encoding='utf-8'))
    path = ROOT / report['inventory_path']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == report['inventory_sha256']
    with gzip.open(path, 'rt', encoding='utf-8', newline='') as file:
        reader = csv.DictReader(file)
        assert reader.fieldnames == ['body_id', 'bytes', 'generation', 'md5_base64', 'crc32c_base64']
        inventory = {}
        for row in reader:
            body = int(row['body_id'])
            assert body not in inventory
            inventory[body] = row
    ids = set(map(int, np.load(ROOT / 'data/derived/malecns_v1_candidates/body_ids.npy')))
    covered = ids & inventory.keys()
    assert len(inventory) == report['listed_swc_files']
    assert len(ids) == report['graph_population']
    assert len(covered) == report['graph_ids_with_published_swc']
    assert sorted(ids - inventory.keys()) == report['missing_graph_ids']
    assert sum(int(inventory[body]['bytes']) for body in covered) == report['published_bytes_for_graph_ids']
    pinned = set()
    for manifest in sorted((ROOT / 'data/reference').glob('malecns_v1_*/source_manifest.json')):
        data = json.loads(manifest.read_text(encoding='utf-8'))
        entries = data.get('entries', data.get('items', []))
        assert entries
        for entry in entries:
            if entry.get('status', 'downloaded') != 'downloaded':
                continue
            body = int(entry.get('body_id', entry.get('bodyId')))
            assert body in inventory
            assert inventory[body]['generation'] == str(entry['generation'])
            pinned.add(body)
    print(json.dumps({'passed': True, 'inventory_rows': len(inventory),
                      'selected_swc_objects': len(covered), 'pinned_generation_matches': len(pinned)}))


if __name__ == '__main__':
    main()
