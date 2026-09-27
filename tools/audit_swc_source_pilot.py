"""Bounded public-source regression for four selected SWCs, not gate A closure."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

from audit_downloaded_malecns_swcs import inspect

ROOT = Path(__file__).resolve().parents[1]
BODIES = (800636, 812953, 815344, 815678)
SOURCE = ROOT / 'data/reference/astra1_swc_source_pilot'
MAX_BYTES = 2_000_000


def verified(payload, row):
    if (len(payload) != int(row['bytes']) or
            base64.b64encode(hashlib.md5(payload).digest()).decode() != row['md5_base64']):
        raise ValueError('SWC bytes differ from generation metadata')
    return hashlib.sha256(payload).hexdigest()


def component_sizes(payload):
    # Independent undirected connectivity calculation, unlike inspector's
    # directed parent-chain walk. Only called after its syntax checks pass.
    parents = {}
    for line in payload.decode().splitlines():
        if line.strip() and not line.startswith('#'):
            fields = line.split()
            parents[int(fields[0])] = int(fields[6])
    adjacency = {key: set() for key in parents}
    for key, parent in parents.items():
        if parent != -1:
            adjacency[key].add(parent)
            adjacency[parent].add(key)
    remaining = set(parents)
    sizes = []
    while remaining:
        pending = [remaining.pop()]
        count = 0
        while pending:
            node = pending.pop()
            count += 1
            for neighbor in adjacency[node]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    pending.append(neighbor)
        sizes.append(count)
    return sorted(sizes, reverse=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    SOURCE.mkdir(parents=True, exist_ok=True)
    receipt_path = SOURCE / 'source_receipts.json'
    report_path = ROOT / 'reports/astra1_swc_source_pilot.json'
    # Published report receipts pin fresh-clone restoration to the exact same
    # generations; do not silently refresh from the live bucket on replay.
    pinned = ({key: row['source'] for key, row in json.loads(report_path.read_text())['rows'].items()}
              if report_path.exists() else {})
    receipts = json.loads(receipt_path.read_text()) if receipt_path.exists() else dict(pinned)
    if pinned and receipts != pinned:
        raise ValueError('Cached receipts differ from committed report')
    for body in BODIES:
        key = str(body)
        path = SOURCE / f'{body}.swc'
        if key not in receipts:
            if not args.fetch:
                raise FileNotFoundError('Initial acquisition requires --fetch')
            name = f'v1.0/segmentation/skeletons-malecns/skeletons-swc/{body}.swc'
            metadata_url = 'https://storage.googleapis.com/storage/v1/b/flyem-male-cns/o/' + quote(name, safe='')
            with urlopen(metadata_url, timeout=30) as response:
                meta = json.load(response)
            if meta['name'] != name or not 0 < int(meta['size']) <= MAX_BYTES:
                raise ValueError('Unexpected object name or oversized source')
            url = f"https://storage.googleapis.com/flyem-male-cns/{name}?generation={meta['generation']}"
            row = {'generation': meta['generation'], 'bytes': int(meta['size']),
                   'md5_base64': meta['md5Hash'], 'url': url, 'metadata_url': metadata_url}
            receipts[key] = row
        if not path.exists():
            if not args.fetch:
                raise FileNotFoundError('Restoring source bytes requires --fetch')
            row = receipts[key]
            with urlopen(row['url'], timeout=30) as response:
                payload = response.read(MAX_BYTES + 1)
            digest = verified(payload, row)
            if 'sha256' in row and row['sha256'] != digest:
                raise ValueError('Restored source SHA256 mismatch')
            row['sha256'] = digest
            path.write_bytes(payload)
        payload = path.read_bytes()
        if verified(payload, receipts[key]) != receipts[key]['sha256']:
            raise ValueError(f'Cached source SHA256 mismatch: {body}')
    receipt_path.write_text(json.dumps(receipts, indent=2) + '\n')
    historical_path = ROOT / 'reports/malecns_ti_extensor_skeleton_integrity.json'
    historical = json.loads(historical_path.read_text())
    rows = {}
    for body in BODIES:
        key = str(body)
        path = SOURCE / f'{body}.swc'
        result = inspect(path)
        if not result['nodes'] or not result['roots'] or any(result[field] for field in (
                'malformed_lines', 'missing_parent', 'cycles', 'duplicate_id_lines', 'nonfinite_nodes')):
            raise ValueError(f'Structural failure: {body}')
        sizes = component_sizes(path.read_bytes())
        old = historical['cells'][key]
        if (result['nodes'] != old['nodes'] or result['roots'] != old['roots'] or
                sizes != old['component_node_counts_descending']):
            raise ValueError(f'Historical topology summary differs: {body}')
        rows[key] = {**result, 'independent_component_sizes': sizes,
                     'historical_topology_summary_matches': True, 'source': receipts[key]}
    report = {
        'scope': 'Four deliberately selected real SWCs, including known multiroot cases; no whole-population coverage claim',
        'selection': list(BODIES), 'rows': rows,
        'total_source_bytes': sum(receipts[str(body)]['bytes'] for body in BODIES),
        'historical_report_sha256': hashlib.sha256(historical_path.read_bytes()).hexdigest(),
        'executed_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'inspector_sha256': hashlib.sha256((ROOT / 'tools/audit_downloaded_malecns_swcs.py').read_bytes()).hexdigest(),
        'limitations': ['New generation/MD5/SHA256 receipts from public v1.0 bucket; historical per-file bytes not independently compared',
                        'Matching topology counts do not establish morphology completeness, motor identity or physiology',
                        'Full graph population and all internal source rows unchanged; gate A remains open']}
    out = ROOT / 'reports/astra1_swc_source_pilot.json'
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'report': str(out), 'files': len(rows),
                      'nodes': sum(row['nodes'] for row in rows.values()),
                      'source_bytes': report['total_source_bytes']}))


if __name__ == '__main__':
    main()
