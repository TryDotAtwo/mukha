"""Inspect measurement-001 preservation in memory; no kernel or numerical run."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

from audit_pang_phase_semantics import FILES
from audit_pang_sample_contract import SOURCES

RUNNER = 'ea7f4945cff90e390868a425180db595c2fb6683'
ARCHIVE = '713ffec2e9f62553b8a4b350b29611fd02c26f822a96ae93ec8a9617e640b6c2'
BASELINE = '8acfef3940ce736afda0f95ef4c44cd839259c973b25f5069f8f3965cccc70f1'
POLICY = 'historical index 2:31 signed maximum, supplied to source-derived helper'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def review(archive, repo):
    payload = archive.read_bytes()
    require(len(payload) == 21622 and sha(payload) == ARCHIVE, 'archive receipt mismatch')
    contents, names = {}, set()
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as tar:
        for member in tar.getmembers():
            path = PurePosixPath(member.name)
            require(not path.is_absolute() and '..' not in path.parts and path.parts[0] == 'measurement-001', 'unsafe member path')
            require(member.name not in names, 'duplicate member')
            names.add(member.name)
            require(member.isdir() or member.isfile(), 'non-regular member')
            if member.isfile():
                require(member.size < 2_000_000, 'unexpected member size')
                contents[str(path.relative_to('measurement-001'))] = tar.extractfile(member).read()
    manifest = json.loads(contents['manifest.json'])
    expected = {'result.json', 'inputs/pang_author_curve_audit.json'}
    expected |= {f'inputs/{name}' for name in FILES.keys() | SOURCES.keys()}
    scripts = ('run_pang_measurement_foreground.py', 'audit_pang_sample_contract.py', 'audit_pang_phase_semantics.py')
    expected |= {f'code/{name}' for name in scripts}
    require(set(contents) == expected | {'manifest.json'}, 'unexpected or missing archive files')
    require(set(manifest['files']) == expected and manifest['run_id'] == 'measurement-001', 'manifest set/run ID mismatch')
    for name, receipt in manifest['files'].items():
        require(len(contents[name]) == receipt['bytes'] and sha(contents[name]) == receipt['sha256'], f'manifest mismatch {name}')
    source_blobs = {}
    for name, expected_blob in dict(FILES, **SOURCES).items():
        data = contents[f'inputs/{name}']
        blob = hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()
        require(blob == expected_blob, f'public input identity mismatch {name}')
        source_blobs[name] = blob
    for name in scripts:
        committed = subprocess.check_output(['git', '-C', str(repo), 'show', f'{RUNNER}:tools/{name}'])
        require(contents[f'code/{name}'] == committed, f'archived code differs from runner commit: {name}')
    require(sha(contents['inputs/pang_author_curve_audit.json']) == BASELINE, 'historical baseline mismatch')
    result = json.loads(contents['result.json'])
    require(result['schema'] == 'pang-measurement-diagnostic-v1' and result['peak_policy'] == POLICY, 'schema/policy mismatch')
    require(result['historical_comparator_sha256'] == BASELINE, 'result baseline identity mismatch')
    require(result['reference_checkpoint'] == '469400fb6ecff677e355df514fb1f8ca08da8178', 'base checkpoint mismatch')
    require(len(result['rows']) == 8, 'expected eight rows')
    for row in result['rows']:
        require(type(row['supplied_peak_frame']) is int, 'noninteger peak')
        require(all(type(row['sampled'][key]) is int for key in ('frame_zero1','frame_zero2','end_phase2')), 'noninteger boundary')
    require(result['preflight']['device'] == 'CPU' and result['preflight']['gpu_used'] is False, 'device declaration changed')
    return {'archive_sha256': ARCHIVE, 'manifest_files_verified': len(expected),
            'public_input_blobs_verified': source_blobs, 'archived_code_matches_commit': RUNNER,
            'historical_baseline_sha256': BASELINE, 'schema_policy_and_frame_types_match': True,
            'result_scope': result['scope'], 'result_limitations': result['limitations'],
            'provenance_limit': 'Independent preservation/source verification. Remote execution/sole ownership relies on operator transport receipt, not location label or archive alone.',
            'numerical_checker_rerun': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(review(args.archive, args.repo), indent=2)+'\n')
