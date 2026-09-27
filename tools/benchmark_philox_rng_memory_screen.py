"""Bounded Molab screening benchmark; never promotes a retina replacement."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import time


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(root=Path('/marimo/fly-project')):
    root = Path(root)
    from hf_artifact_archive import publish
    cuda = root / 'build/cuda-13.1.1'
    source = root / 'native/philox_rng_memory_screen.cu'
    folder = root / 'data/derived/philox_rng_memory_screen_v1'
    folder.mkdir(parents=True, exist_ok=False)
    binary = folder / 'rng_memory_screen'
    command = [str(cuda / 'bin/nvcc'), '-std=c++17', '-O2', '--fmad=false',
               '-arch=sm_120', '-Xptxas=-v', '-I', str(cuda / 'include'),
               '-L', str(cuda / 'lib'), str(source), '-o', str(binary)]
    built = subprocess.run(command, capture_output=True, text=True, timeout=180)
    (folder / 'build.log').write_text(built.stdout + built.stderr)
    if built.returncode:
        raise RuntimeError('compile failed: ' + built.stderr[-3000:])
    command_run = [str(binary), '19503']
    start = time.perf_counter()
    timed_out = False
    try:
        process = subprocess.run(command_run, capture_output=True, text=True, timeout=240)
        stdout, stderr, exit_code = process.stdout, process.stderr, process.returncode
    except subprocess.TimeoutExpired as error:
        timed_out = True
        stdout = (error.stdout or b'').decode(errors='replace')
        stderr = (error.stderr or b'').decode(errors='replace')
        exit_code = None
    wall = time.perf_counter() - start
    (folder / 'run.log').write_text(stdout + '\nSTDERR\n' + stderr)
    parsed = None
    for line in stdout.splitlines():
        print(line, flush=True)
        if line.startswith('RNG_SCREEN_RESULT '):
            parsed = dict(re.findall(r'(\w+)=([^ ]+)', line))
    report = {
        'scope': 'Synthetic real-memory XORWOW versus counter Philox screen; not VisTrans',
        'gpu': 'NVIDIA RTX PRO 6000 Blackwell Server Edition, sm_120',
        'source_sha256': digest(source), 'binary_sha256': digest(binary),
        'build_command': command, 'run_command': command_run,
        'return_code': exit_code, 'timed_out': timed_out, 'wall_s': wall,
        'result': parsed,
        'limitations': 'Fixed 3% extra-draw branch; no VisTrans reaction equations, receptor current, CNS, biology, or checkpoint test.'
    }
    result_path = folder / 'report.json'
    result_path.write_text(json.dumps(report, indent=2))
    files = [source, binary, folder / 'build.log', folder / 'run.log', result_path,
             root / 'tools/benchmark_philox_rng_memory_screen.py']
    manifest = {'schema': 'faithful-fly-artifacts-v1', 'scope': report['scope'],
                'files': {p.relative_to(root).as_posix(): {'bytes': p.stat().st_size,
                                                           'sha256': digest(p)} for p in files}}
    receipt = publish(root, manifest)
    print('RNG_SCREEN_ARCHIVE', json.dumps(receipt), flush=True)
    if timed_out or exit_code != 0 or parsed is None:
        raise RuntimeError('RNG memory screen did not complete; see archived report')
    print('RNG_SCREEN_SUMMARY', json.dumps(parsed), flush=True)
    return receipt


if __name__ == '__main__':
    run()
