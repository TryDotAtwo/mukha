"""Compare an actual native trace with the pinned Brian2 fixture."""
import hashlib
import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace',type=Path,default=ROOT/'build/native_trace.json')
    parser.add_argument('--report',type=Path,default=ROOT/'reports/native_brian_equivalence.json')
    args = parser.parse_args()
    fixture_path = ROOT / 'build/brian_fixture.json'
    trace_path = args.trace
    fixture = json.loads(fixture_path.read_text(encoding='utf-8'))
    trace = json.loads(trace_path.read_text(encoding='utf-8'))
    errors = {}
    for field in ('v', 'g', 'spikes'):
        actual = np.asarray(trace[field])
        expected = np.asarray(fixture['expected_' + field])
        if actual.shape != expected.shape or not np.isfinite(actual).all():
            raise ValueError(f'Invalid native {field} trace')
        errors[field] = (int(np.count_nonzero(actual != expected)) if field == 'spikes'
                         else float(np.max(np.abs(actual - expected))))
    passed = (errors['v'] < 0.002 and errors['g'] < 0.002 and errors['spikes'] == 0
              and trace['checkpoint_continuation_exact'] is True
              and trace['corrupt_checkpoint_rejected'] is True)
    report = {
        'backend': trace['backend'],
        'scope': 'five-neuron trace comparison; hardware execution evidence belongs to the runner; not full-brain biology',
        'fixture_sha256': hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
        'trace_sha256': hashlib.sha256(trace_path.read_bytes()).hexdigest(),
        'steps': len(fixture['stimuli']),
        'max_voltage_error_mv': errors['v'],
        'max_synapse_error_mv': errors['g'],
        'spike_mismatches': errors['spikes'],
        'tolerance_mv': 0.002,
        'checkpoint_continuation_exact': trace['checkpoint_continuation_exact'],
        'corrupt_checkpoint_rejected': trace['corrupt_checkpoint_rejected'],
        'passed': passed,
    }
    args.report.write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
