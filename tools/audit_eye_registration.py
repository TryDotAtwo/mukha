"""Preserve author FAFB-to-microCT matches; never interpret row indices as body IDs."""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'build/eye-python'))
import numpy as np
import rdata


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    lockpath = ROOT / 'reports/eyemap_reference_sources.json'
    lock = json.loads(lockpath.read_text())
    base = ROOT / 'data/reference/eyemap_2025'
    for entry in lock['files']:
        if sha(base / entry['path']) != entry['sha256']:
            raise ValueError('Source changed: ' + entry['path'])
    eye = rdata.read_rda(base / 'data/eyemap.RData')
    ct = rdata.read_rda(base / 'data/microCT/20240701.RData')
    mapping = np.asarray(eye['eyemap'])
    if not np.isfinite(mapping).all() or not np.equal(mapping, np.floor(mapping)).all():
        raise ValueError('Invalid index table')
    mapping = mapping.astype(np.int64)
    right_lenses = np.flatnonzero(~np.asarray(ct['ind_left_lens'], dtype=bool))
    permutation = np.asarray(ct['i_match']).astype(np.int64) - 1
    if not np.array_equal(np.sort(permutation), np.arange(len(permutation))):
        raise ValueError('Nonpermutation lens map')
    inverse = np.argsort(permutation)
    if ((mapping < 1).any() or (mapping[:, 1] > len(right_lenses)).any()
            or (mapping[:, 0] > len(eye['utp_Mi1_rot'])).any()):
        raise ValueError('Index out of bounds')
    if any(len(np.unique(mapping[:, i])) != len(mapping) for i in (0, 1)):
        raise ValueError('Repeated mapping index')
    lens_global = right_lenses[mapping[:, 1] - 1]
    cone_global = inverse[lens_global]
    rays = np.asarray(eye['ucl_rot_sm'])
    expected = np.asarray(ct['ucl_rot_sm'])[cone_global]
    if rays.shape != expected.shape or not np.isfinite(rays).all() or not np.isfinite(expected).all():
        raise ValueError('Invalid ray coordinates')
    error = float(np.max(np.abs(rays - expected)))
    if error > 1e-12:
        raise ValueError('Author eye-map ray order disagrees with microCT')
    if not np.array_equal(mapping[:, ::-1], np.asarray(eye['lens_Mi1'])):
        raise ValueError('Mi1/lens inverse table disagrees')
    n = int(np.asarray(eye['Npt']).item())
    if n != len(mapping):
        raise ValueError('Npt disagrees with measured map')
    auxiliary = np.asarray(eye['ucl_rot_aux'])
    if not np.array_equal(auxiliary[:n], rays):
        raise ValueError('Auxiliary table prefix changed')
    out = ROOT / 'data/derived/optical_reference'
    out.mkdir(parents=True, exist_ok=True)
    path = out / 'fafb_registration.csv'
    with path.open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['author_Mi1_row_1based', 'right_lens_row_1based',
                    'global_lens_row_1based', 'global_cone_row_1based',
                    'ray_forward', 'ray_left', 'ray_up', 'malecns_body_id', 'enabled'])
        for i, pair in enumerate(mapping):
            w.writerow([*pair, lens_global[i] + 1, cone_global[i] + 1, *rays[i], '', 'false'])
    report = {
        'scope': 'Author FAFB Mi1 row indices matched to another specimen microCT; not MaleCNS IDs',
        'source_lock_sha256': sha(lockpath), 'matched_rows': n,
        'right_lenses': len(right_lenses), 'unmatched_right_lenses': len(right_lenses) - n,
        'author_Mi1_rows': len(eye['utp_Mi1_rot']),
        'unmatched_author_Mi1_rows': len(eye['utp_Mi1_rot']) - n,
        'synthetic_boundary_rows_excluded': len(auxiliary) - n,
        'ray_order_max_abs_error': error, 'output_sha256': sha(path),
        'enabled': False, 'passed': True,
        'limitation': 'No cross-dataset landmarks or body registration established; row indices are not neuron identities',
    }
    (ROOT / 'reports/eye_registration_audit.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
