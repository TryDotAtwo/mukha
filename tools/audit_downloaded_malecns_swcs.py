"""Check byte provenance and basic SWC topology for downloaded MaleCNS v1 files."""
import base64
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/raw/malecns_v1_swcs'
REPORT = ROOT / 'reports/malecns_downloaded_swc_audit.json'


def inspect(path):
    nodes = {}
    malformed = 0
    duplicate = 0
    nonfinite = 0
    nonpositive_radius = 0
    with path.open('r', encoding='utf-8') as file:
        for line in file:
            if not line.strip() or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) != 7:
                malformed += 1
                continue
            try:
                key, kind, x, y, z, radius, parent = parts
                key, kind, parent = int(key), int(kind), int(parent)
                xyzr = tuple(map(float, (x, y, z, radius)))
            except ValueError:
                malformed += 1
                continue
            duplicate += key in nodes
            nonfinite += not all(map(math.isfinite, xyzr))
            nonpositive_radius += xyzr[3] <= 0
            nodes[key] = (parent, xyzr[:3])
    roots = sum(parent == -1 for parent, _ in nodes.values())
    missing_parent = sum(parent != -1 and parent not in nodes for parent, _ in nodes.values())
    self_parent = sum(parent == key for key, (parent, _) in nodes.items())
    zero_length_edges = sum(parent in nodes and nodes[parent][1] == xyz
                            for parent, xyz in nodes.values())
    done = set()
    cycles = 0
    for key in nodes:
        if key in done:
            continue
        path = set()
        current = key
        while current in nodes and current not in done and current not in path:
            path.add(current)
            current = nodes[current][0]
        if current in path:
            cycles += 1
        done.update(path)
    return dict(nodes=len(nodes), roots=roots, missing_parent=missing_parent,
                self_parent=self_parent, cycles=cycles, duplicate_id_lines=duplicate,
                malformed_lines=malformed, nonfinite_nodes=nonfinite,
                nonpositive_radius_nodes=nonpositive_radius,
                zero_length_edges=zero_length_edges)


def main():
    inventory_report = json.loads((ROOT / 'reports/malecns_swc_bucket_inventory.json').read_text(encoding='utf-8'))
    path = ROOT / inventory_report['inventory_path']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == inventory_report['inventory_sha256']
    with gzip.open(path, 'rt', newline='', encoding='utf-8') as file:
        inventory = {int(row['body_id']): row for row in csv.DictReader(file)}
    population = set(map(int, np.load(ROOT / 'data/derived/malecns_v1_candidates/body_ids.npy')))
    rows = {}
    for swc in sorted(SOURCE.glob('*.swc')):
        body = int(swc.stem)
        if body not in population:
            raise ValueError(f'SWC outside selected population: {swc}')
        payload = swc.read_bytes()
        meta = inventory[body]
        if (len(payload) != int(meta['bytes']) or
                base64.b64encode(hashlib.md5(payload).digest()).decode() != meta['md5_base64']):
            raise ValueError(f'source byte mismatch: {swc}')
        rows[body] = inspect(swc)
    bad = {str(body): row for body, row in rows.items()
           if row['malformed_lines'] or row['missing_parent'] or row['cycles'] or
           row['duplicate_id_lines'] or row['nonfinite_nodes']}
    report = {
        'dataset': 'male-cns:v1.0',
        'source_inventory_sha256': inventory_report['inventory_sha256'],
        'downloaded_swc_files': len(rows),
        'graph_population': len(population),
        'downloaded_fraction': len(rows) / len(population),
        'total_swc_nodes': sum(row['nodes'] for row in rows.values()),
        'empty_files': sum(row['nodes'] == 0 for row in rows.values()),
        'multi_root_files': sum(row['roots'] > 1 for row in rows.values()),
        'files_with_zero_length_edges': sum(row['zero_length_edges'] > 0 for row in rows.values()),
        'structural_issue_files': bad,
        'scope': 'Basic SWC syntax/topology and source bytes for downloaded files only; '
                 'no EM segmentation, synapse-site, or biological fidelity validation.'
    }
    REPORT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'structural_issue_files'}))
    if bad:
        print(f'structural_issue_files={len(bad)}')


if __name__ == '__main__':
    main()
