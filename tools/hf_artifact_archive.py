"""Private, content-addressed HF archive. Run hashing/upload/restore in Molab.

Input manifests are explicit project-relative paths with bytes and SHA256.
Credentials are supplied through HF_TOKEN, never included in manifests.
"""
from pathlib import Path, PurePosixPath
import hashlib
import io
import json
import os
import re


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def checked_path(root, name):
    rel = PurePosixPath(name)
    if rel.is_absolute() or '..' in rel.parts or '\\' in name:
        raise ValueError('Unsafe artifact path')
    if any(p.startswith('.') or 'private' in p.lower() or 'credential' in p.lower()
           or 'secret' in p.lower() for p in rel.parts):
        raise ValueError('Private configuration is not an artifact')
    root = Path(root).resolve()
    target = (root / name).resolve()
    if not target.is_relative_to(root):
        raise ValueError('Artifact escapes project')
    return target


def validate_manifest(root, manifest, require_files=True):
    if manifest.get('schema') != 'faithful-fly-artifacts-v1':
        raise ValueError('Unknown manifest schema')
    if not manifest.get('files'):
        raise ValueError('Empty artifact manifest')
    for name, item in manifest['files'].items():
        p = checked_path(root, name)
        if not re.fullmatch('[0-9a-f]{64}', item['sha256']):
            raise ValueError('Invalid digest')
        if type(item['bytes']) is not int or item['bytes'] < 0:
            raise ValueError('Invalid size')
        if require_files and (p.stat().st_size != item['bytes'] or digest(p) != item['sha256']):
            raise ValueError('Artifact differs from manifest: ' + name)


def _paced_commit(api, repo_id, revision, operations_factory, interval_seconds):
    """Serialize commit starts across MoLab publishers; 0 is for offline tests."""
    import fcntl
    import tempfile
    import time
    if interval_seconds == 0:
        return api.create_commit(repo_id, repo_type='dataset',
                                 operations=operations_factory(),
                                 commit_message='Archive completed fly artifacts and manifest',
                                 parent_commit=revision)
    if interval_seconds < 31:
        raise ValueError('Production commit interval must be at least 31 seconds')
    clock = Path(tempfile.gettempdir()) / (
        'faithful-fly-hf-commit-' + hashlib.sha256(repo_id.encode()).hexdigest() + '.json')
    with clock.open('a+', encoding='utf-8') as state:
        fcntl.flock(state.fileno(), fcntl.LOCK_EX)
        state.seek(0)
        saved = state.read()
        previous = float(json.loads(saved)['started_at']) if saved else 0.0
        while previous + interval_seconds > time.time():
            remaining = previous + interval_seconds - time.time()
            print('HF_COMMIT_PACING_SECONDS', round(remaining, 1), flush=True)
            time.sleep(min(remaining, 15.0))
        # Failed attempts also consume the pacing slot. Do not automatically retry 429.
        state.seek(0)
        state.truncate()
        state.write(json.dumps({'started_at': time.time()}))
        state.flush()
        os.fsync(state.fileno())
        return api.create_commit(repo_id, repo_type='dataset',
                                 operations=operations_factory(),
                                 commit_message='Archive completed fly artifacts and manifest',
                                 parent_commit=revision)


def _verify_remote_object(remote, size, sha256, git_blob_id):
    if remote.size != size:
        raise ValueError('Remote size mismatch')
    if remote.lfs:
        if remote.lfs.sha256 != sha256:
            raise ValueError('Remote LFS digest mismatch')
    elif remote.blob_id != git_blob_id:
        raise ValueError('Remote Git blob mismatch')


def _git_blob(path, size):
    h = hashlib.sha1(('blob ' + str(size) + chr(0)).encode())
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def publish(root, manifest, repo_id='TryDotAtwo/faithful-fly-artifacts',
            batch_size=32, commit_interval_seconds=31):
    """Commit immutable outputs atomically, then verify before admitting a receipt.

    A manifest's existence alone is not admission. Failure after a commit returns
    no receipt; consumers must verify its immutable objects before use.
    """
    from huggingface_hub import HfApi, CommitOperationAdd
    from huggingface_hub.utils import disable_progress_bars
    disable_progress_bars()
    validate_manifest(root, manifest)
    if not 1 <= batch_size <= 100:
        raise ValueError('Invalid batch size')
    if commit_interval_seconds != 0 and commit_interval_seconds < 31:
        raise ValueError('Production commit interval must be at least 31 seconds')
    token = os.environ.get('HF_TOKEN')
    if not token:
        raise RuntimeError('Add HF_TOKEN in Molab Secrets; do not put it in source')
    api = HfApi(token=token)
    if api.whoami()['name'] != repo_id.split('/')[0]:
        raise ValueError('Unexpected HF account or repository owner')
    info = api.repo_info(repo_id, repo_type='dataset')
    if not info.private:
        raise ValueError('Archive must be private; refusing public upload')
    unique = {}
    for name, item in manifest['files'].items():
        unique.setdefault(item['sha256'], (name, item))
    all_objects = list(unique.items())
    revision = info.sha
    data = json.dumps(manifest, sort_keys=True, indent=2).encode()
    manifest_hash = hashlib.sha256(data).hexdigest()
    manifest_name = 'manifests/' + manifest_hash + '.json'
    manifest_blob = hashlib.sha1(('blob ' + str(len(data)) + chr(0)).encode() + data).hexdigest()

    def verify_objects(batch, at_revision, allow_missing=False):
        paths = api.get_paths_info(repo_id, ['objects/' + sha for sha, _ in batch],
                                   repo_type='dataset', revision=at_revision)
        returned = {p.path: p for p in paths}
        missing = []
        for sha, (name, item) in batch:
            remote = returned.get('objects/' + sha)
            if remote is None:
                if allow_missing:
                    missing.append((sha, (name, item)))
                    continue
                raise ValueError('Remote object missing')
            _verify_remote_object(remote, item['bytes'], sha,
                                  _git_blob(checked_path(root, name), item['bytes']))
        return missing

    pending = []
    for offset in range(0, len(all_objects), batch_size):
        pending.extend(verify_objects(all_objects[offset:offset + batch_size],
                                      revision, allow_missing=True))
    manifest_paths = api.get_paths_info(repo_id, [manifest_name],
                                        repo_type='dataset', revision=revision)
    existing = {p.path: p for p in manifest_paths}.get(manifest_name)
    if existing is not None:
        _verify_remote_object(existing, len(data), manifest_hash, manifest_blob)
        if pending:
            raise ValueError('Existing manifest references missing objects')
        print('HF_REUSED_VERIFIED_MANIFEST', manifest_name, flush=True)
        return {'repo_id': repo_id, 'repo_type': 'dataset', 'revision': revision,
                'manifest': manifest_name, 'sha256': manifest_hash,
                'files': len(manifest['files']), 'verified': True}

    def operations_for(batch, include_manifest):
        operations = []
        for sha, (name, item) in batch:
            path = checked_path(root, name)
            if path.stat().st_size != item['bytes'] or digest(path) != sha:
                raise ValueError('Artifact changed before upload: ' + name)
            operations.append(CommitOperationAdd(path_in_repo='objects/' + sha,
                                                 path_or_fileobj=path))
        if include_manifest:
            operations.append(CommitOperationAdd(path_in_repo=manifest_name,
                                                 path_or_fileobj=io.BytesIO(data)))
        return operations

    while len(pending) > batch_size:
        batch, pending = pending[:batch_size], pending[batch_size:]
        result = _paced_commit(api, repo_id, revision,
                               lambda: operations_for(batch, False),
                               commit_interval_seconds)
        revision = result.oid
        verify_objects(batch, revision)
        print('HF_VERIFIED_STAGED_OBJECTS', len(batch), flush=True)
    result = _paced_commit(api, repo_id, revision,
                           lambda: operations_for(pending, True),
                           commit_interval_seconds)
    revision = result.oid
    # Verify every object and the manifest at the SAME immutable final commit.
    for offset in range(0, len(all_objects), batch_size):
        verify_objects(all_objects[offset:offset + batch_size], revision)
        print('HF_VERIFIED_OBJECTS', min(offset + batch_size, len(all_objects)),
              '/', len(all_objects), flush=True)
    manifest_paths = api.get_paths_info(repo_id, [manifest_name],
                                        repo_type='dataset', revision=revision)
    remote_manifest = {p.path: p for p in manifest_paths}.get(manifest_name)
    if remote_manifest is None:
        raise ValueError('Remote manifest missing')
    _verify_remote_object(remote_manifest, len(data), manifest_hash, manifest_blob)
    return {'repo_id': repo_id, 'repo_type': 'dataset', 'revision': revision,
            'manifest': manifest_name, 'sha256': manifest_hash,
            'files': len(manifest['files']), 'verified': True}


def restore(root, receipt):
    from huggingface_hub import HfApi
    api = HfApi(token=os.environ.get('HF_TOKEN'))
    if not re.fullmatch('[0-9a-f]{40}', receipt['revision']):
        raise ValueError('Restore requires immutable commit revision')
    common = dict(repo_id=receipt['repo_id'], repo_type='dataset', revision=receipt['revision'])
    downloaded = api.hf_hub_download(filename=receipt['manifest'], **common)
    if digest(downloaded) != receipt['sha256']:
        raise ValueError('Manifest digest mismatch')
    manifest = json.loads(Path(downloaded).read_text())
    validate_manifest(root, manifest, require_files=False)
    for name, item in manifest['files'].items():
        target = checked_path(root, name)
        if target.exists():
            if target.stat().st_size != item['bytes'] or digest(target) != item['sha256']:
                raise ValueError('Refusing to overwrite differing artifact: ' + name)
            continue
        downloaded = Path(api.hf_hub_download(filename='objects/' + item['sha256'], **common))
        if downloaded.stat().st_size != item['bytes'] or digest(downloaded) != item['sha256']:
            raise ValueError('Downloaded artifact mismatch')
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + '.restore-part')
        import shutil
        with downloaded.open('rb') as source, temporary.open('xb') as out:
            shutil.copyfileobj(source, out, 8 * 1024 * 1024)
            out.flush()
            os.fsync(out.fileno())
        if target.exists():
            raise ValueError('Destination appeared during restore')
        temporary.rename(target)
    return {'restored_and_verified': len(manifest['files']), 'revision': receipt['revision']}
