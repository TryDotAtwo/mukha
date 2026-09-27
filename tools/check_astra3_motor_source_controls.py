"""Adversarial controls for the raw motor audit; never edits source files."""
import argparse
import csv
import io
import json
from pathlib import Path
from unittest.mock import patch

from audit_astra3_motor_source import audit_source, sha


def check(root, source):
    original = Path.read_bytes
    cases = [('graph_index', '0', 'graph index mismatch'),
             ('mancGroup', '11706.0', 'raw/export mancGroup mismatch'),
             ('rootSide', 'L', 'raw/export rootSide mismatch')]
    results = []
    for field, value, expected in cases:
        rows = list(csv.DictReader(original(root / 'reports/malecns_motor_candidates.csv').decode().splitlines()))
        next(r for r in rows if r['bodyId'] == '815344')[field] = value
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        altered = stream.getvalue().encode()

        def read(path):
            if path.name == 'malecns_motor_candidates.csv':
                return altered
            if path.name == 'malecns_motor_audit.json':
                historical = json.loads(original(path))
                historical['table_sha256'] = sha(altered)
                return json.dumps(historical).encode()
            return original(path)

        with patch.object(Path, 'read_bytes', read):
            try:
                audit_source(root, source)
            except ValueError as error:
                if expected not in str(error):
                    raise
                results.append({'mutation': field, 'rejected': str(error)})
            else:
                raise ValueError(f'{field} mutation was accepted')
    def corrupt_source(path):
        return b'corrupt source' if path == source else original(path)
    with patch.object(Path, 'read_bytes', corrupt_source):
        try:
            audit_source(root, source)
        except ValueError as error:
            if 'raw source identity mismatch' not in str(error):
                raise
            results.append({'mutation': 'source_bytes', 'rejected': str(error)})
        else:
            raise ValueError('corrupt source accepted')
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(check(args.root, args.source), indent=2))
