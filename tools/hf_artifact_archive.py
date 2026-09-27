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


def publish(root, manifest, repo_id='TryDotAtwo/faithful-fly-artifacts', batch_size=32):
    from huggingface_hub import HfApi, CommitOperationAdd
    from huggingface_hub.utils import disable_progress_bars
    disable_progress_bars()
    validate_manifest(root, manifest)
    if not 1 <= batch_size <= 100:
        raise ValueError('Invalid batch size')
    token = os.environ.get('HF_TOKEN')
    if not token:
        raise RuntimeError('Add HF_TOKEN in Molab Secrets; do not put it in source')
    api = HfApi(token=token)
    if api.whoami()['name'] != repo_id.split('/')[0]:
        raise ValueError('Unexpected HF account or repository owner')
    # Repository is created separately; the runtime token needs only this repo.
    info = api.repo_info(repo_id, repo_type='dataset')
    if not info.private:
        raise ValueError('Archive must be private; refusing public upload')
    unique = {}
    for name, item in manifest['files'].items():
        unique.setdefault(item['sha256'], (name, item))
    pending = list(unique.items())
    revision = info.sha
    for start in range(0, len(pending), batch_size):
        batch = pending[start:start + batch_size]
        operations = []
        for sha, (name, item) in batch:
            p = checked_path(root, name)
            # Inputs must be completed, immutable artifacts; recheck before upload.
            if p.stat().st_size != item['bytes'] or digest(p) != sha:
                raise ValueError('Artifact changed before upload: ' + name)
            operations.append(CommitOperationAdd(path_in_repo='objects/' + sha, path_or_fileobj=p))
        result = api.create_commit(repo_id, repo_type='dataset', operations=operations,
                                   commit_message='Archive verified fly artifacts', parent_commit=revision)
        revision = result.oid
        paths = api.get_paths_info(repo_id, ['objects/' + sha for sha, _ in batch],
                                  repo_type='dataset', revision=revision)
        returned = {p.path: p for p in paths}
        for sha, (name, item) in batch:
            remote = returned['objects/' + sha]
            if remote.size != item['bytes']:
                raise ValueError('Remote size mismatch')
            if remote.lfs:
                if remote.lfs.sha256 != sha:
                    raise ValueError('Remote LFS digest mismatch')
            else:
                # Git blob identity includes the length header, unlike file SHA256.
                h = hashlib.sha1(('blob ' + str(item['bytes']) + '\0').encode())
                with checked_path(root, name).open('rb') as f:
                    for chunk in iter(lambda: f.read(1024 * 1024), b''):
                        h.update(chunk)
                if h.hexdigest() != remote.blob_id:
                    raise ValueError('Remote Git blob mismatch')
        print('HF_VERIFIED_OBJECTS', min(start + batch_size, len(pending)), '/', len(pending), flush=True)
    data = json.dumps(manifest, sort_keys=True, indent=2).encode()
    manifest_hash = hashlib.sha256(data).hexdigest()
    name = 'manifests/' + manifest_hash + '.json'
    result = api.create_commit(repo_id, repo_type='dataset', parent_commit=revision,
                              operations=[CommitOperationAdd(path_in_repo=name, path_or_fileobj=io.BytesIO(data))],
                              commit_message='Publish complete verified artifact manifest')
    return {'repo_id': repo_id, 'repo_type': 'dataset', 'revision': result.oid,
            'manifest': name, 'sha256': manifest_hash, 'files': len(manifest['files'])}


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
