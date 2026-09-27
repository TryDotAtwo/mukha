"""Run the native body probe and bind evidence to exported model and runtime."""
import hashlib
import argparse
import csv
import math
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--motor', action='store_true')
    args = parser.parse_args()
    tag = 'body_motor' if args.motor else 'body'
    export_path = ROOT / f'reports/{tag}_export.json'
    export = json.loads(export_path.read_text())
    model_dir = ROOT / f'data/derived/{tag}_diagnostic'
    for name, digest in export['files'].items():
        if sha(model_dir / name) != digest:
            raise RuntimeError(f'Model hash mismatch: {name}')
    runtime = ROOT / 'data/reference/mujoco_3.9.0/bin'
    exe = ROOT / f'build/{tag}_probe.exe'
    env = dict(os.environ)
    env['PATH'] = str(runtime) + os.pathsep + env['PATH']
    command = [str(exe), f'data/derived/{tag}_diagnostic/body.xml']
    trace = ROOT / 'build/body_motor_trace.csv'
    if args.motor:
        command.append('build/body_motor_trace.csv')
    result = subprocess.run(command,
                            cwd=ROOT, env=env, capture_output=True, text=True,
                            timeout=120)
    report = {'returncode': result.returncode, 'stdout': result.stdout,
              'stderr': result.stderr, 'executable_sha256': sha(exe),
              'runtime_sha256': sha(runtime / 'mujoco.dll'),
              'export_report_sha256': sha(export_path),
              'scope': 'Diagnostic joint motor pulse' if args.motor else 'Passive tethered body only; no contacts with controls or neural input',
              'passed': result.returncode == 0}
    if args.motor and trace.exists():
        report['trace_sha256'] = sha(trace)
        report['trace_bytes'] = trace.stat().st_size
        checks = dict(rows=0, pre_pulse_equal=True, finite=True,
                      force_bounded=True, force_matches_pulse=True,
                      clock_valid=True)
        max_difference = 0.0
        with trace.open(newline='') as stream:
            for i, row in enumerate(csv.DictReader(stream)):
                tick = int(row['tick'])
                values = [float(v) for v in row.values()]
                checks['finite'] &= all(math.isfinite(v) for v in values)
                checks['clock_valid'] &= tick == i+1 and abs(float(row['time'])-tick*0.0001)<1e-9
                expected = 1.0 if 2000 <= i < 4000 else 0.0
                checks['force_bounded'] &= abs(float(row['force'])) <= 1.0
                checks['force_matches_pulse'] &= float(row['force']) == expected
                difference = max(abs(float(row[f'baseline_q{j}'])-float(row[f'driven_q{j}']))
                                 for j in range(export['nq']))
                if i < 2000:
                    checks['pre_pulse_equal'] &= difference == 0.0
                max_difference = max(max_difference, difference)
                checks['rows'] += 1
        checks['expected_rows'] = checks['rows'] == 10000
        checks['motor_changes_pose'] = max_difference > 1e-5
        report['trace_checks'] = checks
        report['passed'] &= all(checks.values())
    (ROOT / f'reports/{tag}_native.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    if not report['passed']:
        raise SystemExit(result.returncode or 1)

if __name__ == '__main__':
    main()
