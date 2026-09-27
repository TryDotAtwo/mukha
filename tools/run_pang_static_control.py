"""Exactly one exploratory cubic control under protocol704843a; offline CPU."""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import platform
import shutil
import tarfile

import numpy as np
import scipy
from scipy.io import loadmat
from run_pang_temporal_transfer import HASHES, TESTS, arrays, weights, finite, error, tolerance, validate_keys

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = '704843a695224448470a70527ce8db3649570a16'
PROTOCOL_SHA = '9968b2b5a734441483e0a6391e55a4dbb9edf3fe72de445b78a821d48cac4665'
ARCHIVE_SHA = 'c74de270799633ed056d8b5e6a61a383a4a96797243e3a0453ec28e8ad2af4bb'
RESULT_SHA = '4f277a6d77d12ea8c15a1b16b89e5f2f8d376af4f84390636b303a22ba04b49a'
HELPER_SHA = '56a4dde910687e8adfc9a538c939cbe202f8184e1cb1dbe57ecc83ed27d17f4e'
RCOND = 1e-12
CONFIG = dict(schema='pang-static-control-plan-v1', protocol_commit=PROTOCOL,
              protocol_sha256=PROTOCOL_SHA, archive_sha256=ARCHIVE_SHA,
              input_sha256=HASHES, units='raw fractional deltaF/F',
              training=[[c, 'highLum', 0] for c in ('L1', 'L2')],
              transfers=[[c, l, r] for c in ('L1', 'L2') for l, r in TESTS],
              model='a*c+d*c^3/s_train^2; a>=0; signed d; s_train=max(abs(training control))',
              rank_rcond=RCOND, tie='H0 then boundary then interior; atol1e-12+rtol1e-10*abs(best normalized loss)',
              rank_failure='null cubic/Es; separate archived H0 fallback',
              loss='original-grid trapezoid SSE / own control energy',
              comparisons='E0-Es and E1-Es; atol1e-12+rtol1e-10*abs(reference error)',
              scope='Exploratory reused means; no independent validation or biological mechanism identification',
              stop_rule='One cubic comparison and independent review, then stop this adaptive model sweep regardless of outcome',
              prior_temporal003_all_six_improved=False)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def basis(c, scale):
    # Algebraically c^3/s^2; ratio form avoids unnecessary intermediate overflow.
    return finite(c*(c/scale)**2)


def fit_static(t, c, y, h0_a=None):
    """Training-only API. h0_a in production is the immutable archived H0 gain."""
    t, c, y = arrays(t, c, y)
    w = weights(t); energy = float(finite(np.dot(w, c*c)))
    scale = float(np.max(np.abs(c)))
    if energy <= 0 or scale == 0:
        raise ValueError('zero_training_control_energy')
    cubic = basis(c, scale)
    X = finite(np.column_stack((c, cubic))*np.sqrt(w)[:, None])
    target = finite(y*np.sqrt(w))
    u, singular, vt = np.linalg.svd(X, full_matrices=False)
    rank = int(np.sum(singular > RCOND*singular[0]))
    result = dict(status='rank_deficient' if rank < 2 else 'ok', rank=rank,
                  singular_values=singular.tolist(),
                  condition_number=float(singular[0]/singular[1])
                  if singular[1] > 0 and singular[1] >= singular[0]/np.finfo(float).max else None,
                  scale=scale, training_energy=energy, training_min=float(min(c)),
                  training_max=float(max(c)), training_t=t.tolist(),
                  training_control=c.tolist(), training_target=y.tolist(),
                  selected_model='H0', selected=None, candidates=[],
                  training_prediction=None, training_residual=None)
    if rank < 2:
        # No pseudoinverse cubic extrapolation or substituted cubic score.
        return result
    coefficients = finite(vt.T @ ((u.T @ target)/singular))
    a, d = map(float, coefficients)
    if h0_a is None:
        h0_a = max(0., float(finite(np.dot(w*c, y)/energy)))
    if not np.isfinite(h0_a) or h0_a < 0:
        raise ValueError('invalid_archived_H0_gain')
    boundary_d = float(finite(np.dot(w*cubic, y)/np.dot(w, cubic*cubic)))
    # Predeclared tie order; infeasible interior retained, never selected.
    for kind, ca, cd in [('H0', float(h0_a), 0.), ('boundary', 0., boundary_d), ('interior', a, d)]:
        prediction = finite(ca*c+cd*cubic)
        sse = error(w, y, prediction)
        result['candidates'].append(dict(kind=kind, a=ca, d=cd, feasible=ca >= 0,
                                         a_boundary=ca == 0., sse=sse,
                                         score=float(finite(sse/energy))))
    feasible = [p for p in result['candidates'] if p['feasible']]
    best = min(p['score'] for p in feasible)
    tied = [p for p in feasible if p['score']-best <= tolerance(best)]
    selected = copy.deepcopy(tied[0])
    prediction = finite(selected['a']*c+selected['d']*cubic)
    result.update(selected=selected, selected_model='H0' if selected['kind'] == 'H0' else 'Hs',
                  status='no_resolved_cubic_increment_on_training' if selected['kind'] == 'H0' else 'ok',
                  tied_candidates=[p['kind'] for p in tied],
                  training_prediction=prediction.tolist(), training_residual=(y-prediction).tolist())
    return result


def support(t, c, training):
    t, c, _ = arrays(t, c)
    w = weights(t); scale = training['scale']
    outside_signed = (c < training['training_min']) | (c > training['training_max'])
    outside_magnitude = np.abs(c) > scale
    return dict(training_min=training['training_min'], training_max=training['training_max'],
                transfer_min=float(min(c)), transfer_max=float(max(c)),
                max_abs_over_training_scale=float(finite(np.max(np.abs(c))/scale)),
                outside_signed_time_fraction=float(np.dot(w, outside_signed)/sum(w)),
                outside_magnitude_time_fraction=float(np.dot(w, outside_magnitude)/sum(w)))


def compare_score(reference, score):
    if score is None:
        return dict(delta=None, outcome='undefined')
    finite([reference, score])
    delta = float(finite(reference-score))
    return dict(delta=delta, outcome='improved' if delta > tolerance(reference) else
                'worse' if delta < -tolerance(reference) else 'numerically_unresolved')


def score_static(t, c, y, training, archived):
    # Preserve baselines even if training/transfer fails; never mutate archived objects.
    base = dict(H0=copy.deepcopy(archived['models']['H0']),
                H1=copy.deepcopy(archived['models']['H1_selected']))
    result = dict(status='undefined', selected_model=training.get('selected_model'),
                  baselines=base, fallback_H0=None, prediction=None, residual=None,
                  Es=None, sse=None, support=None,
                  versus_H0=compare_score(0., None), versus_H1=compare_score(0., None))
    try:
        t, c, y = arrays(t, c, y)
        result.update(t=t.tolist(), control=c.tolist(), target=y.tolist())
        if training['status'] not in ('ok', 'no_resolved_cubic_increment_on_training', 'rank_deficient'):
            raise ValueError('invalid_training')
        result['support'] = support(t, c, training)
        if training['status'] == 'rank_deficient':
            result.update(status='rank_deficient', fallback_H0=copy.deepcopy(base['H0']))
            return result
        energy = float(finite(np.dot(weights(t), c*c)))
        if energy <= 0:
            raise ValueError('zero_transfer_control_energy')
        p = training['selected']
        prediction = finite(p['a']*c+p['d']*basis(c, training['scale']))
        sse = error(weights(t), y, prediction); score = float(finite(sse/energy))
        result.update(status='ok', control_energy=energy, prediction=prediction.tolist(),
                      residual=(y-prediction).tolist(), sse=sse, Es=score,
                      versus_H0=compare_score(base['H0']['normalized_error'], score),
                      versus_H1=compare_score(base['H1']['normalized_error'], score))
    except (ValueError, FloatingPointError) as exc:
        result['status'] = str(exc)
    return result


def analyze(data, baseline):
    """Pure dispatch for synthetic leakage tests; baseline is already authenticated by CLI."""
    validate_keys(baseline['transfers'])
    if set(baseline['training']) != {'L1', 'L2'}:
        raise ValueError('training_key_mismatch')
    def pair(cell, level, row):
        t, means = data[f'{cell}_{level}.mat']
        ot, target = data[f'{cell}_CDM_{level}.mat']
        if not np.array_equal(t, ot):
            raise ValueError('pair_clock_mismatch')
        return t, means[row], target[row]
    training, transfers = {}, []
    for cell in ('L1', 'L2'):
        try:
            training[cell] = fit_static(*pair(cell, 'highLum', 0), h0_a=baseline['training'][cell]['H0']['a'])
        except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
            training[cell] = dict(status=str(exc), selected_model=None, selected=None)
        for level, row in TESTS:
            original = next(r for r in baseline['transfers'] if (r['cell'],r['level'],r['row']) == (cell,level,row))
            result = score_static(*pair(cell, level, row), training[cell], original)
            transfers.append(dict(cell=cell, level=level, row=row, **result))
    validate_keys(transfers)
    complete = all(r['status'] == 'ok' for r in transfers)
    cubic_identified = all(t['selected_model'] == 'Hs' for t in training.values())
    return dict(training=training, transfers=transfers,
                summary=dict(complete_six_ordering=complete,
                             all_six_cubic_better_than_H1=all(r['versus_H1']['outcome'] == 'improved' for r in transfers)
                             if complete and cubic_identified else None,
                             prior_temporal003_all_six_improved=baseline['summary']['all_six_improved']))


def read_archive(path):
    raw = Path(path).read_bytes()
    if digest(raw) != ARCHIVE_SHA:
        raise ValueError('baseline_archive_hash_mismatch')
    payload = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        seen = set()
        for entry in archive:
            p = PurePosixPath(entry.name)
            if p.is_absolute() or '..' in p.parts or entry.name in seen:
                raise ValueError('unsafe_archive_path')
            seen.add(entry.name)
            if entry.isdir():
                continue
            if not entry.isfile() or not p.parts or p.parts[0] != 'temporal-transfer-003':
                raise ValueError('unsafe_archive_member')
            key = '/'.join(p.parts[1:])
            payload[key] = archive.extractfile(entry).read()
    manifest = json.loads(payload['manifest.json'])
    if set(payload) != set(manifest['files']) | {'manifest.json'}:
        raise ValueError('baseline_manifest_set_mismatch')
    for key, receipt in manifest['files'].items():
        if digest(payload[key]) != receipt['sha256'] or len(payload[key]) != receipt['bytes']:
            raise ValueError('baseline_manifest_hash_mismatch')
    if digest(payload['result.json']) != RESULT_SHA:
        raise ValueError('baseline_result_hash_mismatch')
    data = {}
    for name, expected in HASHES.items():
        content = payload['inputs/'+name]
        if digest(content) != expected:
            raise ValueError('input_hash_mismatch')
        mat = loadmat(io.BytesIO(content))
        t, means = np.asarray(mat['t']).ravel(), np.asarray(mat['meanResp'])
        if t.shape != (63,) or means.shape != (2,63):
            raise ValueError('input_shape_mismatch')
        arrays(t, means[0], means[1])
        data[name] = (t, means)
    baseline = json.loads(payload['result.json'])
    if baseline['schema'] != 'pang-temporal-transfer-result-v1' or baseline['summary']['all_six_improved'] is not False:
        raise ValueError('prior_result_contract_mismatch')
    return raw, data, baseline


def run(archive_path, output):
    protocol = ROOT/'docs/PANG_STATIC_CONTROL_PROTOCOL.md'
    helper = Path(__file__).with_name('run_pang_temporal_transfer.py')
    if digest(protocol.read_bytes()) != PROTOCOL_SHA or digest(helper.read_bytes()) != HELPER_SHA:
        raise ValueError('protocol_or_helper_hash_mismatch')
    raw, data, baseline = read_archive(archive_path)
    output.mkdir(parents=True, exist_ok=False)
    (output/'code').mkdir()
    (output/'baseline-temporal003.tar.gz').write_bytes(raw)
    shutil.copy2(protocol, output/'protocol.md')
    for source in (Path(__file__), helper):
        shutil.copy2(source, output/'code'/source.name)
    result = analyze(data, baseline)
    result.update(schema='pang-static-control-result-v1', run_id=output.name,
                  exploratory=True, config=CONFIG, runner_sha256=digest(Path(__file__).read_bytes()),
                  execution_location='not_asserted_by_runner', device='CPU',
                  versions=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__))
    config_bytes = (json.dumps(CONFIG, indent=2, allow_nan=False)+'\n').encode()
    (output/'config.json').write_bytes(config_bytes)
    result['config_sha256'] = digest(config_bytes)
    (output/'result.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    files = {p.relative_to(output).as_posix(): dict(bytes=p.stat().st_size,sha256=digest(p.read_bytes()))
             for p in sorted(output.rglob('*')) if p.is_file()}
    (output/'manifest.json').write_text(json.dumps(dict(run_id=output.name,files=files),indent=2)+'\n')
    return 'ok' if result['summary']['complete_six_ordering'] else 'incomplete'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-archive', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    status = run(args.baseline_archive, args.output_dir)
    print(status)
    raise SystemExit(0 if status == 'ok' else 2)
