"""Audit available MaleCNS v1 anatomy without treating soma points as full morphology."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow.feather as feather

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/malecns_v1/body-annotations-male-cns-v1.0-minconf-0.5.feather'
GRAPH = ROOT / 'data/derived/malecns_v1_candidates/body_ids.npy'
OUT = ROOT / 'reports/malecns_geometry_coverage.json'


def valid_point(value):
    return value is not None and len(value) == 3 and all(isinstance(x, int) for x in value)


def main():
    lock = json.loads((ROOT / 'reports/malecns_source_lock.json').read_text(encoding='utf-8'))
    expected = next(x['sha256'] for x in lock['files'] if x['name'] == RAW.name)
    if hashlib.sha256(RAW.read_bytes()).hexdigest() != expected:
        raise ValueError('annotation source hash differs from source lock')
    cols = ['bodyId', 'status', 'superclass', 'somaLocation', 'tosomaLocation']
    table = feather.read_table(RAW, columns=cols).to_pydict()
    ids = np.load(GRAPH)
    idset = set(map(int, ids))
    selected = set()
    groups = {}
    for i, body in enumerate(table['bodyId']):
        body = int(body)
        group = 'included' if body in idset else 'outside_population'
        stats = groups.setdefault(group, dict(rows=0, soma_points=0, to_soma_points=0,
                                               either_point=0, missing_both=0))
        stats['rows'] += 1
        soma = valid_point(table['somaLocation'][i])
        to_soma = valid_point(table['tosomaLocation'][i])
        stats['soma_points'] += soma
        stats['to_soma_points'] += to_soma
        stats['either_point'] += soma or to_soma
        stats['missing_both'] += not (soma or to_soma)
        if group == 'included':
            selected.add(body)
            if not (table['status'][i] == 'Traced' or (table['superclass'][i] or '').strip()):
                raise ValueError(f'included annotation fails population policy: {body}')
    if selected != idset:
        raise ValueError('annotation IDs and graph IDs differ')

    skeleton_ids = set()
    manifest_files = []
    for directory in sorted((ROOT / 'data/reference').glob('malecns_v1_*')):
        manifest = directory / 'source_manifest.json'
        if not manifest.exists():
            continue
        data = json.loads(manifest.read_text(encoding='utf-8'))
        entries = data.get('entries', data.get('items', []))
        if not entries:
            raise ValueError(f'no SWC records in manifest: {manifest}')
        for entry in entries:
            if entry.get('status', 'downloaded') != 'downloaded':
                continue
            body = int(entry.get('body_id', entry.get('bodyId')))
            swc = directory / f'{body}.swc'
            if not swc.is_file() or hashlib.sha256(swc.read_bytes()).hexdigest() != entry['sha256']:
                raise ValueError(f'missing or altered pinned SWC: {swc}')
            skeleton_ids.add(body)
        manifest_files.append(str(manifest.relative_to(ROOT)).replace('\\', '/'))
    report = {
        'dataset': 'male-cns:v1.0',
        'annotation_sha256': expected,
        'graph_population': len(ids),
        'annotation_point_coverage': groups,
        'pinned_v1_swc_manifest_files': manifest_files,
        'distinct_pinned_v1_swc_ids': len(skeleton_ids),
        'pinned_v1_swc_inside_population': len(skeleton_ids & idset),
        'pinned_v1_swc_outside_population': len(skeleton_ids - idset),
        'population_without_local_pinned_swc': len(idset - skeleton_ids),
        'scope': 'Local artifact coverage only; a soma point is not a neurite skeleton, '
                 'and a pinned SWC is not proof of complete morphology or biology.'
    }
    OUT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
