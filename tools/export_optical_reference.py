"""Export measured eye rays in author cone order, without registering MaleCNS."""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'build/eye-python'))
import numpy as np
import rdata


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    lockpath = ROOT / 'reports/eyemap_reference_sources.json'
    lock = json.loads(lockpath.read_text())
    source = ROOT / 'data/reference/eyemap_2025'
    for entry in lock['files']:
        if digest(source / entry['path']) != entry['sha256']:
            raise ValueError('Source hash mismatch: ' + entry['path'])
    data = rdata.read_rda(source / 'data/microCT/20240701.RData')
    lens, cone = (np.asarray(data[k], dtype=np.float64) for k in ('lens', 'cone'))
    rays = np.asarray(data['ucl_rot_sm'], dtype=np.float64)
    raw = np.asarray(data['ucl_rot'], dtype=np.float64)
    match = np.asarray(data['i_match'])
    n = len(cone)
    if not np.array_equal(np.sort(match), np.arange(1, n + 1)):
        raise ValueError('Lens assignment is not a complete 1-based permutation')
    idx = match.astype(np.int64) - 1
    for array in (lens, cone, rays, raw):
        if array.shape != (n, 3) or not np.isfinite(array).all():
            raise ValueError('Invalid geometry')
    sides = np.asarray(data['ind_left_cone'], dtype=bool)
    lens_sides = np.asarray(data['ind_left_lens'], dtype=bool)
    if not np.array_equal(sides, lens_sides[idx]):
        raise ValueError('Lens/cone assignment crosses eye sides')
    reconstructed = lens[idx] - cone
    reconstructed /= np.linalg.norm(reconstructed, axis=1)[:, None]
    geometry_error = float(np.max(np.abs(reconstructed - raw)))
    norm_error = float(np.max(np.abs(np.linalg.norm(rays, axis=1) - 1)))
    if geometry_error > 1e-12 or norm_error > 1e-12:
        raise ValueError('Stored direction disagrees with author geometry')
    out = ROOT / 'data/derived/optical_reference'
    out.mkdir(parents=True, exist_ok=True)
    target = out / 'rays.csv'
    with target.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['cone_index_1based', 'lens_index_1based', 'side',
                         'lens_x_author_units', 'lens_y_author_units', 'lens_z_author_units',
                         'ray_forward', 'ray_left', 'ray_up', 'malecns_body_id', 'enabled'])
        for i in range(n):
            writer.writerow([i + 1, int(match[i]), 'L' if sides[i] else 'R',
                             *lens[idx[i]], *rays[i], '', 'false'])
    report = {
        'scope': 'Author smoothed optical axes from a separate microCT specimen; no MaleCNS registration',
        'source_lock_sha256': digest(lockpath), 'source_commit': lock['commit'],
        'rays': n, 'left': int(sides.sum()), 'right': int((~sides).sum()),
        'geometry_max_abs_error': geometry_error, 'unit_norm_max_error': norm_error,
        'coordinate_basis': '+X forward, +Y left, +Z up, per proc_uCT.R',
        'position_units': 'preserved author units; not converted to MuJoCo units',
        'index_basis': 'cone order; lens index is author i_match (1-based)',
        'rays_sha256': digest(target), 'enabled': False,
        'missing': ['MaleCNS column registration', 'body eye registration',
                    'acceptance angles and spectral sensitivity', 'phototransduction'],
        'passed': True,
    }
    (ROOT / 'reports/optical_reference_export.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
