"""One foreground CPU measurement diagnostic; no network, pairing or GPU calls."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
BASE_COMMIT = '469400fb6ecff677e355df514fb1f8ca08da8178'
HISTORICAL_SHA256 = '8acfef3940ce736afda0f95ef4c44cd839259c973b25f5069f8f3965cccc70f1'


@contextmanager
def exclusive_kernel(lock_path):
    import fcntl
    with lock_path.open('a+b') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another foreground diagnostic holds the kernel lock') from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--location', choices=('local-rehearsal', 'molab'), required=True)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', args.run_id):
        raise ValueError('Invalid run ID')
    import numpy as np
    import scipy
    from scipy.io import loadmat
    from audit_pang_sample_contract import sampled_areas, source_receipts
    from audit_pang_phase_semantics import FILES, verify_blob

    source = ROOT / 'data/reference/pang_phase_semantics'
    receipts = source_receipts(source)
    for name, blob in FILES.items():
        verify_blob((source / name).read_bytes(), blob)
    args.output_root.mkdir(parents=True, exist_ok=True)
    preflight = {'location': args.location, 'designated_owner': 'astra1',
                 'python': platform.python_version(), 'numpy': np.__version__,
                 'scipy': scipy.__version__, 'device': 'CPU', 'gpu_used': False,
                 'source_code_receipts': receipts,
                 'free_bytes': shutil.disk_usage(args.output_root).free}
    if preflight['free_bytes'] < 20_000_000:
        raise RuntimeError('Less than 20 MB free for this bounded run')
    if args.preflight:
        print(json.dumps(preflight))
        return
    # All owner launches must use the SAME output root on the one kernel.
    with exclusive_kernel(args.output_root / '.pang-foreground.lock'):
        out = args.output_root / args.run_id
        out.mkdir(exist_ok=False)
        started = time.monotonic()
        historical_path = ROOT / 'reports/pang_author_curve_audit.json'
        rows = []
        try:
            historical_bytes = historical_path.read_bytes()
            if hashlib.sha256(historical_bytes).hexdigest() != HISTORICAL_SHA256:
                raise ValueError('Historical comparator SHA256 mismatch')
            historical = json.loads(historical_bytes)
            for name in FILES:
                mat = loadmat(source / name)
                t, y = mat['t'].ravel(), mat['meanResp']
                if t.shape != (63,) or y.shape != (2, 63):
                    raise ValueError('Unexpected processed-mean array shape')
                if not np.isfinite(t).all() or not np.isfinite(y).all() or not (np.diff(t) > 0).all():
                    raise ValueError('Nonfinite response or invalid clock')
                ifi = float(np.median(np.diff(t)))
                for row, polarity in ((0, -1), (1, 1)):
                    # Supplied historical diagnostic peak rule. Not claimed to
                    # implement source computeFramePeaks or identify flash time.
                    peak0 = 2 + int(np.argmax(polarity * y[row, 2:31]))
                    sample = sampled_areas(y[row].tolist(), peak0 + 1, row + 1, ifi)
                    old = next(r for r in historical['curves'] if r['file'] == name and r['row'] == row)
                    first = old['phase1_area_deltaF_over_F_seconds']
                    second = old['phase2_signed_area_deltaF_over_F_seconds']
                    if first == 0 or sample['signed_area_ratio'] is None:
                        raise ValueError('Undefined ratio; do not coerce to zero')
                    rows.append({'file': name, 'row': row, 'supplied_peak_frame': peak0+1,
                                 'ifi_seconds': ifi, 'sampled': sample,
                                 'historical_area1_df_f_seconds': first,
                                 'historical_area2_df_f_seconds': second,
                                 'historical_abs_ratio': abs(second/first),
                                 'historical_negative_signed_ratio': -second/first,
                                 'sampled_abs_ratio': abs(sample['signed_area_ratio']),
                                 'sampled_negative_signed_ratio': -sample['signed_area_ratio']})
            result = {'schema': 'pang-measurement-diagnostic-v1', 'preflight': preflight,
                      'reference_checkpoint': BASE_COMMIT, 'rows': rows,
                      'seconds': time.monotonic()-started,
                      'scope': 'Combined onset, endpoint and crossing convention sensitivity plus separate sign-display comparison on eight processed means; not an isolated interpolation effect, source ROI bootstrap or biological model scoring',
                      'historical_comparator_sha256': HISTORICAL_SHA256,
                      'peak_policy': 'historical index 2:31 signed maximum, supplied to source-derived helper',
                      'limitations': ['No physical flash alignment or recording-level optical metadata',
                                      'No individual ROI uncertainty, fitted model, MATLAB execution or gate B pass',
                                      'Local rehearsal is not evidence of Molab connectivity or execution']}
            (out / 'result.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
            files = {f'inputs/{name}': source/name for name in list(FILES) + [r['name'] for r in receipts]}
            files['inputs/pang_author_curve_audit.json'] = historical_path
            for name in ('run_pang_measurement_foreground.py', 'audit_pang_sample_contract.py',
                         'audit_pang_phase_semantics.py'):
                files[f'code/{name}'] = ROOT/'tools'/name
            for relative, original in files.items():
                target = out / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, target)
            manifest = {'schema': 'foreground-artifacts-v1', 'run_id': args.run_id,
                        'files': {}}
            for path in sorted(p for p in out.rglob('*') if p.is_file()):
                payload = path.read_bytes()
                manifest['files'][path.relative_to(out).as_posix()] = {
                    'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}
            (out / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
            archive = args.output_root / f'{args.run_id}.tar.gz'
            with tarfile.open(archive, 'x:gz') as tar:
                tar.add(out, arcname=args.run_id)
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            (args.output_root / f'{args.run_id}.sha256').write_text(f'{digest}  {archive.name}\n')
            print(json.dumps({'state': 'completed', 'location': args.location, 'rows': len(rows),
                              'archive': str(archive), 'sha256': digest, 'seconds': result['seconds']}))
        except Exception as error:
            (out/'failure.json').write_text(json.dumps({'state': 'failed', 'type': type(error).__name__})+'\n')
            raise


if __name__ == '__main__':
    main()
