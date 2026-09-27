"""Independent numerical review of a retrieved compact-run directory.

Does not authenticate remote execution or replace the artifact manifest check.
Uses copied public MAT inputs; no network, kernel or credential access.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.io import loadmat
from audit_pang_phase_semantics import FILES, verify_blob


def check(run_dir, result=None):
    if result is None:
        result = json.loads((run_dir/'result.json').read_text())
    expected_keys = {(name, row) for name in FILES for row in (0, 1)}
    keys = [(r['file'], r['row']) for r in result['rows']]
    if len(keys) != 8 or set(keys) != expected_keys:
        raise ValueError('missing, duplicated or unexpected curve')
    max_error = 0.

    def near(actual, expected, label):
        nonlocal max_error
        if not math.isfinite(actual) or not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-14):
            raise ValueError(f'numerical mismatch: {label}')
        max_error = max(max_error, abs(actual-expected))

    for r in result['rows']:
        path = run_dir/'inputs'/r['file']
        verify_blob(path.read_bytes(), FILES[r['file']])
        data = loadmat(path)
        t, y = data['t'].ravel(), data['meanResp'][r['row']]
        polarity = (-1, 1)[r['row']]
        dt = float(np.median(np.diff(t)))
        peak = 2+int(np.argmax(polarity*y[2:31]))
        derivative = np.diff(np.concatenate(([0.], y)))
        candidates = np.flatnonzero(polarity*(derivative[1:peak+2]-.1*derivative[1:peak+2]-derivative[:peak+1]) > 0)
        first = int(candidates[0])+1 if len(candidates) else 2
        second = int(np.flatnonzero(polarity*y[peak:] <= 0)[0])+peak+1
        end = math.floor(.25/dt)
        a = float(np.trapezoid(y[first-1:second], dx=dt)*100)
        b = float(np.trapezoid(y[second-1:end], dx=dt)*100)
        for field, value in {'frame_zero1': first, 'frame_zero2': second,
                'end_phase2': end, 'area1_percent_df_f_seconds': a,
                'area2_percent_df_f_seconds': b, 'signed_area_ratio': b/a}.items():
            near(r['sampled'][field], value, field)
        near(r['supplied_peak_frame'], peak+1, 'peak')
        near(r['ifi_seconds'], dt, 'ifi')
        old_end = int(np.searchsorted(t, t[2]+.25, side='right')-1)
        cross = peak+1+int(np.flatnonzero(polarity*y[peak+1:old_end+1] <= 0)[0])
        z = t[cross-1]+(t[cross]-t[cross-1])*abs(y[cross-1])/(abs(y[cross-1])+abs(y[cross]))
        left = float(np.trapezoid(np.r_[y[2:cross], 0.], np.r_[t[2:cross], z]))
        right = float(np.trapezoid(np.r_[0., y[cross:old_end+1]], np.r_[z, t[cross:old_end+1]]))
        for field, value in [('historical_abs_ratio', abs(right/left)),
                ('historical_negative_signed_ratio', -right/left),
                ('sampled_abs_ratio', abs(b/a)), ('sampled_negative_signed_ratio', -b/a)]:
            near(r[field], value, field)
    return {'rows_checked': 8, 'max_absolute_error': max_error,
            'scope': 'Numerical reconstruction on pinned processed means, not remote provenance or biological validation'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', type=Path)
    args = parser.parse_args()
    print(json.dumps(check(args.run_dir), indent=2))
