"""Independent result-contract mutations; does not implement numerical scoring."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys


def review(checker_tools, run_dir):
    sys.path.insert(0, str(checker_tools))
    spec = importlib.util.spec_from_file_location('reviewed_checker', checker_tools/'check_pang_measurement_result.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = json.loads((run_dir/'result.json').read_text())
    module.check(run_dir, copy.deepcopy(original))
    shuffled = copy.deepcopy(original)
    shuffled['rows'].reverse()
    module.check(run_dir, shuffled)
    cases = []
    for key in ('schema', 'peak_policy'):
        for value in ('incorrect-claim', None, False):
            altered = copy.deepcopy(original)
            altered[key] = value
            cases.append((f'{key}={value!r}', altered))
        altered = copy.deepcopy(original)
        del altered[key]
        cases.append((f'{key} missing', altered))
    for key in ('supplied_peak_frame', 'frame_zero1', 'frame_zero2', 'end_phase2'):
        for mode in ('tiny_fraction', 'fraction', 'float_integer', 'boolean'):
            altered = copy.deepcopy(original)
            container = altered['rows'][0] if key == 'supplied_peak_frame' else altered['rows'][0]['sampled']
            value = container[key]
            container[key] = {'tiny_fraction': value+5e-13, 'fraction': value+.25,
                              'float_integer': float(value), 'boolean': True}[mode]
            cases.append((f'{key}:{mode}', altered))
    findings = []
    for name, altered in cases:
        try:
            module.check(run_dir, altered)
        except (ValueError, TypeError, KeyError) as error:
            findings.append({'case': name, 'rejected': True, 'exception': type(error).__name__})
        else:
            findings.append({'case': name, 'rejected': False})
    return {'baseline_accepted': True, 'row_permutation_accepted': True,
            'cases': findings, 'all_negative_cases_rejected': all(r['rejected'] for r in findings),
            'scope': 'Schema/policy/frame contract only; invokes reviewed checker without reimplementing numerical arithmetic'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checker-tools', type=Path, required=True)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = review(args.checker_tools.resolve(), args.run_dir.resolve())
    text = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end='')
    raise SystemExit(0 if result['all_negative_cases_rejected'] else 1)
