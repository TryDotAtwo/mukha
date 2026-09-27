"""No-network archive contract checks; run in Molab before real HF upload."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import hf_artifact_archive as archive


class FakeAPI:
    objects = {}
    commits = []
    corrupt = False
    private = True

    def __init__(self, **kwargs):
        pass

    def whoami(self):
        return {'name': 'TryDotAtwo'}

    def create_repo(self, *args, **kwargs):
        assert kwargs['private'] is True

    def repo_info(self, *args, **kwargs):
        return SimpleNamespace(private=self.private, sha='a'*40)

    def create_commit(self, repo_id, operations, **kwargs):
        for op in operations:
            source = op.path_or_fileobj
            data = Path(source).read_bytes() if isinstance(source, (str, Path)) else source.getvalue()
            self.objects[op.path_in_repo] = data
        self.commits.append([op.path_in_repo for op in operations])
        return SimpleNamespace(oid='b'*40)

    def get_paths_info(self, repo_id, paths, **kwargs):
        result=[]
        for name in paths:
            data=self.objects[name]
            blob=hashlib.sha1(('blob '+str(len(data))+'\0').encode()+data).hexdigest()
            result.append(SimpleNamespace(path=name,size=len(data),lfs=None,
                                          blob_id='0'*40 if self.corrupt else blob))
        return result

    def hf_hub_download(self, filename, **kwargs):
        p=Path(self.download_root)/hashlib.sha256(filename.encode()).hexdigest()
        p.write_bytes(self.objects[filename])
        return str(p)


def run():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/'source';root.mkdir();(root/'trace.bin').write_bytes(b'known-episode\0\1')
        manifest={'schema':'faithful-fly-artifacts-v1','files':{'trace.bin':{
            'bytes':15,'sha256':archive.digest(root/'trace.bin')}}}
        manifest['files']['trace.bin']['bytes']=(root/'trace.bin').stat().st_size
        for unsafe in ['../token','/tmp/token','build/molab_pair.private.json','.env','a/../../b']:
            try:archive.checked_path(root,unsafe)
            except ValueError:pass
            else:raise AssertionError('Unsafe path accepted')
        (root/'escape').symlink_to(Path(td),target_is_directory=True)
        try:archive.checked_path(root,'escape/file')
        except ValueError:pass
        else:raise AssertionError('Symlink escape accepted')
        with patch.dict(os.environ,{'HF_TOKEN':'test-token-never-transmitted'}), patch('huggingface_hub.HfApi',FakeAPI):
            FakeAPI.corrupt=True
            try:archive.publish(root,manifest)
            except ValueError as e:assert 'blob' in str(e)
            else:raise AssertionError('Corrupt remote blob accepted')
            assert not any(k.startswith('manifests/') for k in FakeAPI.objects)
            FakeAPI.corrupt=False
            receipt=archive.publish(root,manifest)
            assert receipt['files']==1
            FakeAPI.download_root=Path(td)/'downloads';FakeAPI.download_root.mkdir()
            destination=Path(td)/'restore'
            archive.restore(destination,receipt)
            assert (destination/'trace.bin').read_bytes()==(root/'trace.bin').read_bytes()
            (destination/'trace.bin').write_bytes(b'changed')
            try:archive.restore(destination,receipt)
            except ValueError as e:assert 'overwrite' in str(e)
            else:raise AssertionError('Differing destination overwritten')
            FakeAPI.private=False
            before=len(FakeAPI.commits)
            try:archive.publish(root,manifest)
            except ValueError as e:assert 'private' in str(e)
            else:raise AssertionError('Public upload allowed')
            assert len(FakeAPI.commits)==before
    print(json.dumps({'archive_contract_checks':'passed','network_upload_tested':False,
                      'checked':['path traversal','symlink escape','secret path rejection',
                                 'remote hash mismatch before manifest','restore byte equality',
                                 'no overwrite','private repository requirement']}))


if __name__=='__main__':run()
