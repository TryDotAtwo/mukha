"""One frozen scale-versus-filter comparison; CPU/offline; no biological verdict."""
import argparse
import hashlib
import json
import math
import platform
from pathlib import Path
import shutil

import numpy as np
import scipy
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[1]
RCOND = 1e-12
ATOL, RTOL = 1e-12, 1e-10
TESTS = (('highLum', 1), ('lowLum', 0), ('lowLum', 1))
HASHES = {
    'L1_highLum.mat': 'bbc8c90dbc57fba0c4d2afdebe29797e06360448a9dfb0b9018cd32583da6746',
    'L1_lowLum.mat': '8b539a2b34c39e8fec11e6576f3f7badd1fc80815e93319093a4cf41ea03d33a',
    'L2_highLum.mat': '1c9266f5c387a217013f8715a49f6351f78e9a9de9894a5ac2892b2a06cf6e36',
    'L2_lowLum.mat': '49c0e5587618f9d11e0dea12a218b6eecd511e563d8d42ad986e9c410c6d012c',
    'L1_CDM_highLum.mat': '4425910a67db801af030652ff1d7d6428edbc6da90539869f375d25ffba7eac0',
    'L1_CDM_lowLum.mat': '0608ea5df61490290f2143993a307d4edd7fa5a234089aedc8c6cec250af0e04',
    'L2_CDM_highLum.mat': 'e19bd5d5e40863d509c72fb3d7348d96e9469f0d1ab6256897d4ef2b5366e5dc',
    'L2_CDM_lowLum.mat': '0a835999723058712b6a311ec9ec52dca36333313dfb3ced9493bde89c4d6e3e',
}
CONFIG = dict(schema='pang-temporal-transfer-plan-v1', input_sha256=HASHES,
              fit=[['L1', 'highLum', 0], ['L2', 'highLum', 0]],
              transfer=[[cell, level, row] for cell in ('L1', 'L2') for level, row in TESTS],
              units='raw fractional deltaF/F', row_policy='0 dark; 1 light',
              H0='a*c; a>=0', H1='a*c+b*(c-z); a>=0; signed b',
              state='tau*zprime=c-z; original-grid linear c; z0=c0',
              tau_grid='32 geomspace(median(diff(training_t)),0.25 seconds)',
              rank_rcond=RCOND, rank_policy='minimum-norm diagnostics; rank<2 excluded from selection',
              comparison_atol=ATOL, comparison_rtol=RTOL,
              fit_metric='trapezoid weighted SSE / training control energy',
              transfer_metric='trapezoid weighted SSE / corresponding control energy',
              tie_policy='near global minimum: H0 first, then smallest tau',
              scope='Two effective response-to-response models; no memory necessity, feedback identity, physical calibration or animal-heldout claim')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finite(value):
    if not np.isfinite(value).all():
        raise ValueError('nonfinite_arithmetic')
    return value


def arrays(t, c, y=None):
    t, c = np.asarray(t, float), np.asarray(c, float)
    if t.ndim != 1 or c.shape != t.shape or len(t) < 2:
        raise ValueError('invalid_shape')
    finite(t); finite(c)
    if not np.all(np.diff(t) > 0):
        raise ValueError('invalid_time')
    if y is not None:
        y = np.asarray(y, float)
        if y.shape != c.shape:
            raise ValueError('invalid_shape')
        finite(y)
    return t, c, y


def weights(t):
    d = np.diff(t)
    return np.r_[d[0]/2, (d[:-1]+d[1:])/2, d[-1]/2]


def memory_state(t, c, tau):
    t, c, _ = arrays(t, c)
    if not math.isfinite(tau) or tau <= 0:
        raise ValueError('invalid_tau')
    z = np.empty_like(c); z[0] = c[0]
    for i, d in enumerate(np.diff(t)):
        u = -math.expm1(-float(d)/tau)
        z[i+1] = z[i] + (c[i]-z[i])*u + (c[i+1]-c[i])/d*(d-tau*u)
    return finite(z)


def error(w, y, prediction):
    residual = finite(y-prediction)
    return float(finite(np.dot(w, residual*residual)))


def tolerance(reference):
    return ATOL+RTOL*abs(reference)


def fit_training(t, c, y):
    """Only one training pair enters this API. No transfer values or tuning hooks."""
    t, c, y = arrays(t, c, y)
    w = weights(t); energy = float(finite(np.dot(w, c*c)))
    if energy == 0:
        raise ValueError('zero_training_control_energy')
    a0 = max(0., float(finite(np.dot(w*c, y)/energy)))
    h0 = dict(model='H0', a=a0, b=0., tau=None, status='ok',
              sse=error(w, y, a0*c))
    h0['score'] = float(finite(h0['sse']/energy))
    dt = float(np.median(np.diff(t)))
    if dt > .25:
        raise ValueError('invalid_tau_grid')
    profiles = []
    for index, tau in enumerate(np.geomspace(dt, .25, 32)):
        z = memory_state(t, c, float(tau))
        X = np.column_stack((c, c-z))*np.sqrt(w)[:, None]
        target = y*np.sqrt(w)
        U, singular, V = np.linalg.svd(X, full_matrices=False)
        rank = int(np.sum(singular > RCOND*singular[0]))
        coef = V[:rank].T @ ((U[:, :rank].T @ target)/singular[:rank])
        a, b = map(float, finite(coef))
        norms = np.linalg.norm(X, axis=0)
        corr = float(np.dot(X[:, 0]/norms[0], X[:, 1]/norms[1])) if np.all(norms > 0) else None
        unconstrained = [a, b]
        if a < 0:
            a = 0.
            b = float(np.dot(X[:, 1], target)/np.dot(X[:, 1], X[:, 1])) if norms[1] > 0 else 0.
        sse = error(w, y, finite(a*c+b*(c-z)))
        profiles.append(dict(model='H1', index=index, tau=float(tau), a=a, b=b,
                             unconstrained_minimum_norm=unconstrained,
                             singular_values=singular.tolist(), rank=rank,
                             column_correlation=corr, column_norms=norms.tolist(),
                             status='ok' if rank == 2 else 'nonidentifiable',
                             a_boundary=a == 0., sse=sse, score=float(finite(sse/energy))))
    eligible = [h0]+[p for p in profiles if p['status'] == 'ok']
    best = min(p['score'] for p in eligible)
    tied = [p for p in eligible if p['score']-best <= tolerance(best)]
    selected = dict(tied[0])  # H0 first, then increasing tau
    warnings = []
    if any(p['rank'] < 2 for p in profiles):
        warnings.append('nonidentifiable_candidates_excluded')
    if len(tied) > 1:
        warnings.append('numerically_tied_profile')
    if selected.get('index') in (0, 31):
        warnings.append('boundary_tau')
    return dict(status='ok', H0=h0, selected=selected, profiles=profiles,
                training_control_energy=energy, training_t=t.tolist(),
                training_control=c.tolist(), training_target=y.tolist(),
                training_predictions={name: predict(t, c, p)[0].tolist()
                                      for name, p in [('H0', h0), ('H1_selected', selected)]},
                warnings=warnings, tied_candidates=len(tied))


def predict(t, c, parameter):
    t, c, _ = arrays(t, c)
    if parameter['model'] == 'H0':
        return finite(parameter['a']*c), None
    z = memory_state(t, c, parameter['tau'])
    return finite(parameter['a']*c+parameter['b']*(c-z)), z


def score_transfer(t, c, y, training):
    t, c, y = arrays(t, c, y)
    w = weights(t); energy = float(finite(np.dot(w, c*c)))
    models = {}
    for name, parameter in [('H0', training['H0']), ('H1_selected', training['selected'])]:
        prediction, state = predict(t, c, parameter)
        sse = error(w, y, prediction)
        models[name] = dict(parameters=parameter, prediction=prediction.tolist(),
                            residual=(y-prediction).tolist(), sse=sse,
                            normalized_error=float(finite(sse/energy)) if energy else None,
                            state=state.tolist() if state is not None else None)
    delta = None; outcome = 'zero_control_energy'
    if energy:
        e0, e1 = [models[k]['normalized_error'] for k in ('H0', 'H1_selected')]
        delta = e0-e1
        outcome = ('improved' if delta > tolerance(e0) else
                   'worse' if delta < -tolerance(e0) else 'numerically_unresolved')
    return dict(status='ok' if energy else 'zero_control_energy', t=t.tolist(),
                control=c.tolist(), target=y.tolist(), control_energy=energy,
                models=models, error_improvement=delta, outcome=outcome)


def validate_keys(records):
    expected = {(cell, level, row) for cell in ('L1', 'L2') for level, row in TESTS}
    if len(records) != 6:
        raise ValueError('transfer_key_mismatch')
    keys = []
    for r in records:
        if type(r.get('row')) is not int:
            raise ValueError('transfer_key_mismatch')
        keys.append((r.get('cell'), r.get('level'), r['row']))
    if set(keys) != expected:
        raise ValueError('transfer_key_mismatch')


def run(source, output):
    # Only exact eight files are read/copied. Unknown input-directory files ignored.
    for name, digest in HASHES.items():
        if sha(source/name) != digest:
            raise ValueError('input_hash_mismatch:'+name)
    output.mkdir(parents=True, exist_ok=False)
    (output/'inputs').mkdir(); (output/'code').mkdir()
    data = {}
    for name, digest in HASHES.items():
        path = output/'inputs'/name
        shutil.copy2(source/name, path)
        if sha(path) != digest:
            raise ValueError('copied_input_hash_mismatch')
        mat = loadmat(path)
        t, means = np.asarray(mat['t']).ravel(), np.asarray(mat['meanResp'])
        if means.shape != (2, 63) or t.shape != (63,):
            raise ValueError('invalid_input_shape')
        arrays(t, means[0], means[1])
        data[name] = (t, means)
    def pair(cell, level, row):
        t, control = data[f'{cell}_{level}.mat']
        other_t, target = data[f'{cell}_CDM_{level}.mat']
        if not np.array_equal(t, other_t):
            raise ValueError('unmatched_pair_time')
        return t, control[row], target[row]
    training, records = {}, []
    for cell in ('L1', 'L2'):
        try:
            training[cell] = fit_training(*pair(cell, 'highLum', 0))
        except (ValueError, np.linalg.LinAlgError) as exc:
            training[cell] = dict(status=str(exc))
        for level, row in TESTS:
            try:
                if training[cell]['status'] != 'ok':
                    raise ValueError('training_failed')
                result = score_transfer(*pair(cell, level, row), training[cell])
            except (ValueError, np.linalg.LinAlgError) as exc:
                result = dict(status=str(exc), outcome='undefined', error_improvement=None)
            records.append(dict(cell=cell, level=level, row=row, **result))
    validate_keys(records)
    valid = all(r['status'] == 'ok' for r in records)
    summary = dict(status='ok' if valid else 'incomplete',
                   all_six_improved=all(r['outcome'] == 'improved' for r in records) if valid else None,
                   sum_normalized_error_improvement=sum(r['error_improvement'] for r in records) if valid else None)
    result = dict(schema='pang-temporal-transfer-result-v1', run_id=output.name,
                  scope=CONFIG['scope'], device='CPU', location='not_asserted_by_runner',
                  versions=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__),
                  training=training, transfers=records, summary=summary,
                  runner_sha256=sha(__file__))
    config_bytes = (json.dumps(CONFIG, indent=2, allow_nan=False)+'\n').encode()
    (output/'config.json').write_bytes(config_bytes)
    result['config_sha256'] = hashlib.sha256(config_bytes).hexdigest()
    shutil.copy2(__file__, output/'code'/Path(__file__).name)
    (output/'result.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    files = {p.relative_to(output).as_posix(): dict(bytes=p.stat().st_size, sha256=sha(p))
             for p in sorted(output.rglob('*')) if p.is_file()}
    (output/'manifest.json').write_text(json.dumps(dict(run_id=output.name, files=files), indent=2)+'\n')
    return summary['status']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    status = run(args.input_dir, args.output_dir)
    print(status)
    raise SystemExit(0 if status == 'ok' else 2)
