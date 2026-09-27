"""Reconstruct motor identities from pinned raw MaleCNS annotations.

Requires numpy and pyarrow; no graph edge or physiology validation is implied.
"""
import argparse
import csv
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pyarrow.feather as feather

from audit_astra3_motor_evidence import require, indexed


def sha(data):
    return hashlib.sha256(data).hexdigest()


def audit_source(root, source):
    lock_bytes = (root / 'reports/malecns_source_lock.json').read_bytes()
    lock = next(r for r in json.loads(lock_bytes)['files'] if r['name'] == source.name)
    data = source.read_bytes()
    require(len(data) == lock['bytes'] and sha(data) == lock['sha256'], 'raw source identity mismatch')
    fields = ['bodyId', 'status', 'superclass', 'subclass', 'type', 'instance',
              'somaSide', 'rootSide', 'somaNeuromere', 'exitNerve', 'mancBodyid',
              'mancType', 'mancGroup', 'matchingNotes', 'synonyms']
    raw = feather.read_table(io.BytesIO(data), columns=fields).to_pylist()
    require(all(r['bodyId'] is not None for r in raw), 'null source bodyId')
    require(len({r['bodyId'] for r in raw}) == len(raw), 'duplicate source bodyId')
    selected = sorted((r for r in raw if r['status'] == 'Traced' or (r['superclass'] or '').strip()), key=lambda r: r['bodyId'])
    require(len(selected) == 167216, 'selected population changed')
    ids = io.BytesIO()
    np.save(ids, np.array([r['bodyId'] for r in selected], dtype='<u8'), allow_pickle=False)
    historical = json.loads((root / 'reports/malecns_motor_audit.json').read_bytes())
    require(sha(ids.getvalue()) == historical['graph_ids_sha256'], 'reconstructed ID array differs from archived graph ID digest')
    motors = {str(r['bodyId']): (i, r) for i, r in enumerate(selected) if r['superclass'] in ('vnc_motor', 'cb_motor')}
    csv_bytes = (root / 'reports/malecns_motor_candidates.csv').read_bytes()
    require(sha(csv_bytes) == historical['table_sha256'], 'motor export identity mismatch')
    exported = indexed(csv.DictReader(csv_bytes.decode('utf-8-sig').splitlines()))
    require(set(exported) == set(motors), 'raw/export motor population mismatch')
    comparisons = 0
    for body, (index, row) in motors.items():
        require(int(exported[body]['graph_index']) == index, f'{body}: graph index mismatch')
        for field in fields:
            value = row[field]
            actual = exported[body]['source_type_label' if field == 'type' else field]
            if field in ('bodyId', 'mancBodyid', 'mancGroup') and value is not None:
                equal = actual != '' and Decimal(actual) == Decimal(str(value))
            else:
                equal = actual == ('' if value is None else str(value))
            require(equal, f'{body}: raw/export {field} mismatch')
            comparisons += 1
    group_rows = [dict(row, graph_index=index) for index, row in motors.values() if row['mancGroup'] in (11657, 11706)]
    require({r['bodyId'] for r in group_rows} == {800636, 804257, 815344, 815678}, 'raw curated group membership differs')
    predictions = {str(target): [{'bodyId': r['bodyId'], 'type': r['type'], 'superclass': r['superclass']} for r in selected if r['mancBodyid'] == target] for target in (10256, 22126)}
    return {
        'schema': 'astra3-raw-motor-source-v1',
        'source': {k: lock[k] for k in ('name', 'pinned_url', 'gcs_generation', 'bytes', 'sha256')},
        'source_lock_sha256': sha(lock_bytes), 'export_sha256': sha(csv_bytes),
        'reconstructed_graph_ids_sha256': sha(ids.getvalue()),
        'selected_population': len(selected), 'motor_population': len(motors),
        'leg_motor_population': sum(r['subclass'] in ('fl', 'ml', 'hl') for _, r in motors.values()),
        'source_fields_compared': comparisons, 'graph_indices_compared': len(motors),
        'raw_group_members': group_rows, 'selected_predicted_id_multiplicity': predictions,
        'scope': 'Raw annotation-to-export identity and reconstructed sorted population indices; no graph edges, morphology, individual MANC identity or physiology verified',
        'gate_D_passed': False,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = json.dumps(audit_source(args.root, args.source), sort_keys=True, indent=2) + '\n'
    if args.output:
        args.output.write_text(result, encoding='utf-8')
    else:
        print(result, end='')
