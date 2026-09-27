"""Build a small, opt-in Molab recovery notebook from pinned local tools."""

from pathlib import Path
import base64
import hashlib


ROOT = Path(__file__).resolve().parents[1]
REPLAY = ROOT / "tools/check_photon_counter_replay.py"
ARCHIVE = ROOT / "tools/hf_artifact_archive.py"
OUT = ROOT / "build/faithful_fly_compact_recovery.py"
REVISION = "dda01dc3784dda21a5854a2ad112c188af1a4fb7"
MANIFEST = "manifests/0d9a3984bf89f1fedf41e13a27de4d52e7c804d6b891e988e1b2232c95ffd39c.json"
BINARY = "data/derived/photon_counter_candidate_v2/libfly_photon_counter_diagnostic.so"


def main():
    replay = REPLAY.read_bytes()
    archive = ARCHIVE.read_bytes()
    replay_b64 = base64.b64encode(replay).decode()
    archive_b64 = base64.b64encode(archive).decode()
    text = f'''import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import os
    import subprocess as _sp
    from pathlib import Path
    start = mo.ui.run_button(label="Restore and verify counter-RNG candidate")
    gpu = _sp.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                         capture_output=True, text=True)
    mo.vstack([
        mo.md("# Faithful fly: compact Molab recovery"),
        mo.md("GPU: `{{}}`; HF_TOKEN present: `{{}}`.".format(
            gpu.stdout.strip() if gpu.returncode == 0 else 'unavailable',
            bool(os.environ.get('HF_TOKEN')))),
        start,
    ])
    return (start, mo, os, Path)


@app.cell
def _(start, mo, os, Path):
    mo.stop(not start.value, mo.md("Press the button to restore the pinned artifact and run the exact replay."))
    import base64
    import hashlib
    import importlib.util
    import json
    import subprocess
    import sys
    from huggingface_hub import HfApi

    token = os.environ.get('HF_TOKEN')
    if not token:
        raise RuntimeError('HF_TOKEN is missing from this notebook Secrets')
    root = Path('/marimo/fly-project')
    repo = 'TryDotAtwo/faithful-fly-artifacts'
    revision = '{REVISION}'
    manifest_name = '{MANIFEST}'
    binary_name = '{BINARY}'
    api = HfApi(token=token)
    info = api.repo_info(repo, repo_type='dataset', revision=revision)
    if not info.private:
        raise RuntimeError('The artifact repository must remain private')
    manifest_path = Path(api.hf_hub_download(repo, manifest_name, repo_type='dataset', revision=revision))
    manifest_bytes = manifest_path.read_bytes()
    expected_manifest = manifest_name.split('/')[-1].split('.')[0]
    if hashlib.sha256(manifest_bytes).hexdigest() != expected_manifest:
        raise RuntimeError('Manifest digest mismatch')
    manifest = json.loads(manifest_bytes)
    if manifest.get('schema') != 'faithful-fly-artifacts-v1':
        raise RuntimeError('Manifest schema mismatch')
    item = manifest['files'][binary_name]
    sha = item['sha256']
    downloaded = Path(api.hf_hub_download(repo, 'objects/' + sha, repo_type='dataset', revision=revision))
    data = downloaded.read_bytes()
    if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != sha:
        raise RuntimeError('Candidate binary digest mismatch')
    binary = root / binary_name
    binary.parent.mkdir(parents=True, exist_ok=True)
    if binary.exists() and binary.read_bytes() != data:
        raise RuntimeError('Existing candidate binary differs')
    binary.write_bytes(data)
    tools = root / 'tools'
    tools.mkdir(parents=True, exist_ok=True)
    for name, encoded, digest in [
        ('check_photon_counter_replay.py', '{replay_b64}', '{hashlib.sha256(replay).hexdigest()}'),
        ('hf_artifact_archive.py', '{archive_b64}', '{hashlib.sha256(archive).hexdigest()}'),
    ]:
        payload = base64.b64decode(encoded)
        if hashlib.sha256(payload).hexdigest() != digest:
            raise RuntimeError('Embedded tool digest mismatch: ' + name)
        target = tools / name
        if target.exists() and target.read_bytes() != payload:
            raise RuntimeError('Existing tool differs: ' + name)
        target.write_bytes(payload)
    spec = importlib.util.spec_from_file_location('fly_counter_replay', tools / 'check_photon_counter_replay.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    folder = root / 'data/derived/photon_counter_replay_v1'
    folder.mkdir(parents=True, exist_ok=True)
    baseline = module.exercise(root, 'baseline')
    fresh_run = subprocess.run(
        [sys.executable, str(tools / 'check_photon_counter_replay.py'), '--phase', 'fresh', '--root', str(root)],
        capture_output=True, text=True, timeout=120, check=True)
    fresh = json.loads(fresh_run.stdout.split('COUNTER_FRESH_RESULT ')[-1])
    if fresh['final_sha256'] != baseline['final_sha256']:
        raise RuntimeError('Fresh-process replay digest mismatch')
    result = {{'candidate_sha256': sha, 'manifest_sha256': expected_manifest,
              'baseline': baseline, 'fresh': fresh,
              'scope': 'One receptor, 10 ticks, one seed and input; no biological or speed claim'}}
    report = folder / 'report.json'
    report.write_text(json.dumps(result, indent=2))
    manifest_out = {{'schema': 'faithful-fly-artifacts-v1', 'scope': result['scope'], 'files': {{}}}}
    for file in [tools / 'check_photon_counter_replay.py', report,
                 folder / 'midpoint.bin', folder / 'baseline_final.bin', folder / 'fresh_final.bin']:
        rel = file.relative_to(root).as_posix()
        manifest_out['files'][rel] = {{'bytes': file.stat().st_size,
                                      'sha256': hashlib.sha256(file.read_bytes()).hexdigest()}}
    sys.path.insert(0, str(tools))
    from hf_artifact_archive import publish
    receipt = publish(root, manifest_out)
    print('COUNTER_REPLAY_RESULT', json.dumps(result), flush=True)
    print('COUNTER_REPLAY_ARCHIVE', json.dumps(receipt), flush=True)
    return


if __name__ == '__main__':
    app.run()
'''
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(OUT, len(text.encode()), hashlib.sha256(text.encode()).hexdigest())


if __name__ == "__main__":
    main()
