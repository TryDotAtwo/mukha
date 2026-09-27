"""Offline, CPU-only frozen O/E/C factorial analysis. No transport or execution claim."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import shutil
import platform

import numpy as np
import scipy
from scipy.io import loadmat
from audit_pang_sample_contract import boundaries

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = ('HHH', 'SHH', 'HSH', 'HHS', 'SSH', 'SHS', 'HSS', 'SSS')
METRICS = ('A1', 'A2', 'total', 'Q')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compare(actual, reference, ratio=False):
    residual = actual-reference
    if not all(math.isfinite(v) for v in (actual, reference, residual)):
        return dict(residual=None, absolute_residual=None, passed=False,
                    reason='nonfinite_arithmetic')
    return dict(residual=residual, absolute_residual=abs(residual),
                passed=abs(residual) <= (1e-10 if ratio else 1e-14)+1e-10*abs(reference))


def grid(t, y):
    t, y = np.asarray(t, dtype=float), np.asarray(y, dtype=float)
    if (t.ndim != 1 or y.shape != t.shape or len(t) < 2
            or not np.isfinite(t).all() or not np.isfinite(y).all()
            or not (np.diff(t) > 0).all()):
        raise ValueError('invalid_grid')
    return t, y


def integrate(t, y, start, end):
    """Direct trapezoids on original knots plus interpolated endpoints."""
    if not t[0] <= start <= end <= t[-1]:
        raise ValueError('invalid_interval')
    knots = np.r_[start, t[(t > start) & (t < end)], end]
    vals = np.interp(knots, t, y)
    return float(np.sum(np.diff(knots)*(vals[:-1]+vals[1:])/2))


def evaluate_cube(t, y, peak_time, levels):
    """Public synthetic-test API: levels is [O,E,C], each mapping H/S to time."""
    t, y = grid(t, y)
    cells = []
    for condition in CONDITIONS:
        o, e, c = [float(levels[i][v]) for i, v in enumerate(condition)]
        cell = dict(condition=condition, start=o, end=e, split=c,
                    status='invalid_interval', A1=None, A2=None, total=None,
                    direct_total=None, denominator_magnitude=None, raw_ratio=None, Q=None)
        if t[0] <= o <= peak_time <= c <= e <= t[-1]:
            a1, a2 = integrate(t, y, o, c), integrate(t, y, c, e)
            direct = integrate(t, y, o, e)
            ratio = a2/a1 if a1 != 0 else None
            cell.update(A1=a1, A2=a2, total=a1+a2, direct_total=direct,
                        denominator_magnitude=abs(a1), raw_ratio=ratio,
                        Q=-ratio if ratio is not None else None,
                        conservation=compare(a1+a2, direct),
                        status='ok' if ratio is not None else 'zero_first_area')
            if not all(math.isfinite(v) for v in (a1, a2, direct, a1+a2)) or (ratio is not None and not math.isfinite(ratio)):
                cell['status'] = 'nonfinite_arithmetic'
                for key, value in list(cell.items()):
                    if isinstance(value, float) and not math.isfinite(value):
                        cell[key] = None
                cell.pop('conservation', None)
        cells.append(cell)
    return cells


def validate_cells(cells, levels=None):
    """Reject malformed cubes before any dictionary aggregation.

    Boundary metadata is an exact copy of frozen levels, not a numerical
    estimate: area/ratio tolerances must not permit drift in this identity.
    """
    if not isinstance(cells, (list, tuple)) or len(cells) != len(CONDITIONS):
        raise ValueError('condition_key_mismatch')
    by = {}
    for cell in cells:
        if not isinstance(cell, dict):
            raise ValueError('condition_key_mismatch')
        condition = cell.get('condition')
        if type(condition) is not str or condition not in CONDITIONS or condition in by:
            raise ValueError('condition_key_mismatch')
        by[condition] = cell
        if levels is not None:
            for axis, field in enumerate(('start', 'end', 'split')):
                value = cell.get(field)
                if (type(value) not in (int, float) or not math.isfinite(value)
                        or value != levels[axis][condition[axis]]):
                    raise ValueError('frozen_boundary_mismatch:'+condition+':'+field)
    return by


def contrasts(cells):
    """Unscaled signed differences; averaged effects average over remaining axes."""
    by = validate_cells(cells)
    out = {}
    for metric in METRICS:
        values = {k: c[metric] for k, c in by.items()}
        if any(v is None for v in values.values()):
            out[metric] = {'status': 'undefined_metric'}
            continue
        def effect(axes, fixed):
            total = 0.
            for bits in itertools.product('HS', repeat=len(axes)):
                key = list(fixed)
                for axis, bit in zip(axes, bits):
                    key[axis] = bit
                total += (-1)**bits.count('H')*values[''.join(key)]
            return total
        terms = {}
        for size in (1, 2, 3):
            for axes in itertools.combinations(range(3), size):
                remaining = [i for i in range(3) if i not in axes]
                conditional = {}
                for bits in itertools.product('HS', repeat=len(remaining)):
                    fixed = list('HHH')
                    for axis, bit in zip(remaining, bits):
                        fixed[axis] = bit
                    conditional[''.join(bits) or 'none'] = effect(axes, fixed)
                terms[''.join('OEC'[i] for i in axes)] = {
                    'baseline': effect(axes, 'HHH'), 'conditional': conditional,
                    'averaged': sum(conditional.values())/len(conditional)}
        if any(not math.isfinite(v) for term in terms.values()
               for v in [term['baseline'], term['averaged'], *term['conditional'].values()]):
            out[metric] = {'status': 'nonfinite_contrast'}
            continue
        out[metric] = {'status': 'ok', 'terms': terms,
                       'full_change': values['SSS']-values['HHH'],
                       'baseline_expansion_residual': values['SSS']-values['HHH']-sum(v['baseline'] for v in terms.values())}
    return out


def invariants(cells):
    by = validate_cells(cells)
    checks = []
    for axis in range(3):
        for key in CONDITIONS:
            if key[axis] != 'H':
                continue
            other = key[:axis]+'S'+key[axis+1:]
            a, b = by[key], by[other]
            if any(c['A1'] is None or c['A2'] is None for c in (a, b)):
                checks.append(dict(pair=[key, other], status='undefined'))
                continue
            actual, reference = ((b['A2'], a['A2']) if axis == 0 else
                                 (b['A1'], a['A1']) if axis == 1 else
                                 (b['A1']-a['A1'], -(b['A2']-a['A2'])))
            checks.append(dict(pair=[key, other], status='checked', **compare(actual, reference)))
    return checks


def analyze_curve(t, y, row, archived):
    t, y = grid(t, y)
    if len(t) != 63 or type(row) is not int or row not in (0, 1):
        raise ValueError('invalid_curve_domain')
    polarity = -1 if row == 0 else 1
    peak = 2+int(np.argmax(polarity*y[2:31]))
    first, second = boundaries(y.tolist(), peak+1, row+1)
    ifi = float(np.median(np.diff(t)))
    end_h = int(np.searchsorted(t, t[2]+.25, side='right'))-1
    end_s = math.floor(.25/ifi)-1
    if second is None:
        raise ValueError('missing_crossing')
    j = second-1
    historical = next((i for i in range(peak+1, end_h+1) if polarity*y[i] <= 0), None)
    if historical != j or j < 1 or y[j] == y[j-1]:
        raise ValueError('inconsistent_original_crossing_bracket')
    if not 0 <= end_s < len(t):
        raise ValueError('invalid_end_index')
    if (archived['supplied_peak_frame'] != peak+1 or
            archived['sampled']['frame_zero1'] != first or
            archived['sampled']['frame_zero2'] != second or
            archived['sampled']['end_phase2'] != end_s+1):
        raise ValueError('source_corner_index_mismatch')
    c_h = float(t[j-1]-y[j-1]*(t[j]-t[j-1])/(y[j]-y[j-1]))
    levels = [{'H': float(t[2]), 'S': float(t[first-1])},
              {'H': float(t[end_h]), 'S': float(t[end_s])},
              {'H': c_h, 'S': float(t[j])}]
    cells = evaluate_cube(t, y, float(t[peak]), levels)
    validate_cells(cells, levels)
    closure = {}
    for condition, reference in [('HHH', [archived['historical_area1_df_f_seconds'], archived['historical_area2_df_f_seconds'], archived['historical_negative_signed_ratio']]),
                                  ('SSS', [archived['sampled']['area1_percent_df_f_seconds']/100, archived['sampled']['area2_percent_df_f_seconds']/100, archived['sampled_negative_signed_ratio']])]:
        cell = next(c for c in cells if c['condition'] == condition)
        closure[condition] = {metric: compare(cell[metric], ref, metric == 'Q') if cell[metric] is not None else {'passed': False, 'reason': cell['status']}
                              for metric, ref in zip(('A1', 'A2', 'Q'), reference)}
    checks = invariants(cells)
    accepted = (all(c['status'] == 'ok' and c['conservation']['passed'] for c in cells)
                and all(c.get('passed', False) for c in checks)
                and all(c['passed'] for corner in closure.values() for c in corner.values()))
    return dict(status='ok' if accepted else 'attribution_blocked',
                peak_index=peak, peak_time=float(t[peak]), polarity=polarity,
                start_indices={'H': 2, 'S': first-1}, end_indices={'H': end_h, 'S': end_s},
                bracket_indices=[j-1, j], source_frame_zero1=first, source_frame_zero2=second,
                levels=levels, ifi_seconds=ifi, steps=np.diff(t).tolist(),
                clock_deviation=float(np.max(np.abs(t-(t[0]+np.arange(len(t))*ifi)))),
                cells=cells, corner_closure=closure, invariants=checks,
                contrasts=contrasts(cells) if accepted else {'status': 'attribution_blocked'})


def verify_reference(reference, plan):
    for name, expected in [('result.json', plan['reference_result_sha256']), ('manifest.json', plan['reference_manifest_sha256'])]:
        if digest(reference/name) != expected:
            raise ValueError('reference_hash_mismatch:'+name)
    manifest = json.loads((reference/'manifest.json').read_text())
    for name, receipt in manifest['files'].items():
        path = reference/name
        if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink():
            raise ValueError('unsafe_reference_path')
        if digest(path) != receipt['sha256'] or path.stat().st_size != receipt['bytes']:
            raise ValueError('reference_file_mismatch:'+name)
    for name, expected in plan['input_mat_sha256'].items():
        if digest(reference/'inputs'/name) != expected:
            raise ValueError('mat_hash_mismatch')
    return manifest


def run(reference, output):
    plan_path = ROOT/'configs/pang_window_factor_plan.json'
    plan = json.loads(plan_path.read_text())
    if digest(plan_path) != PLAN_SHA256:
        raise ValueError('frozen_plan_hash_mismatch')
    helper = Path(__file__).with_name('audit_pang_sample_contract.py')
    if digest(helper) != 'b1ea37eaf9ec346d8e4d0f0fb989e30b4e8e73b08804562b802833ef340fc17e':
        raise ValueError('helper_hash_mismatch')
    reference_manifest = verify_reference(reference, plan)
    archived = json.loads((reference/'result.json').read_text())
    # Pinning the entire reference result also pins its schema, policy and typed indices.
    output.mkdir(parents=True, exist_ok=False)
    # Copy only authenticated members, never unrelated files from the input tree.
    for name in [*reference_manifest['files'], 'manifest.json']:
        target = output/'reference'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(reference/name, target)
    verify_reference(output/'reference', plan)
    shutil.copy2(plan_path, output/'plan.json')
    (output/'code').mkdir()
    for path in (Path(__file__), helper):
        shutil.copy2(path, output/'code'/path.name)
    curves, records = [], []
    for name in plan['input_mat_sha256']:
        mat = loadmat(output/'reference/inputs'/name)
        for row in plan['rows']:
            original = next(r for r in archived['rows'] if r['file'] == name and r['row'] == row)
            try:
                curve = analyze_curve(mat['t'].ravel(), mat['meanResp'][row], row, original)
            except ValueError as exc:
                curve = dict(status=str(exc), cells=[dict(condition=c, status=str(exc),
                             A1=None, A2=None, total=None, direct_total=None,
                             denominator_magnitude=None, raw_ratio=None, Q=None,
                             start=None, end=None, split=None) for c in CONDITIONS])
            curve.update(file=name, row=row, input_sha256=plan['input_mat_sha256'][name])
            for cell in curve.pop('cells'):
                records.append(dict(file=name, row=row, input_sha256=curve['input_sha256'], **cell))
            curves.append(curve)
    expected = {(f, r, c) for f in plan['input_mat_sha256'] for r in (0, 1) for c in CONDITIONS}
    if len(records) != 64 or {(r['file'], r['row'], r['condition']) for r in records} != expected:
        raise ValueError('condition_key_mismatch')
    result = dict(schema='pang-window-factors-v1', run_id=output.name, plan_sha256=digest(plan_path),
                  runner_sha256=digest(__file__), peak_policy=plan['fixed_peak_policy'],
                  scope=plan['interpretation'], device='CPU', execution_location='unspecified_by_runner',
                  versions=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__),
                  status='ok' if all(c['status'] == 'ok' for c in curves) else 'attribution_blocked',
                  curves=curves, records=records)
    (output/'result.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    manifest = {p.relative_to(output).as_posix(): {'sha256': digest(p), 'bytes': p.stat().st_size}
                for p in sorted(output.rglob('*')) if p.is_file()}
    (output/'manifest.json').write_text(json.dumps(dict(schema='pang-window-artifacts-v1', run_id=output.name, files=manifest), indent=2)+'\n')
    return result['status']


# Exact config from approved commit39387c3; no runtime override.
PLAN_SHA256 = '263d6f4a55f4277f5804f7a4e8d2c07e8757f839e3935c27b0b60d47b334e099'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    status = run(args.reference_dir, args.output_dir)
    print(status)
    raise SystemExit(0 if status == 'ok' else 2)
