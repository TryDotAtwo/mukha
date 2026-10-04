"""Offline archive admission/atomicity checks; execute only in MoLab."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import hf_artifact_archive as archive

class FakeAPI:
    private = True
    corrupt = False
    use_lfs = False
    missing_manifest = False
    snapshots = {}
    commits = []
    requests = []
    head = "a"*40

    @classmethod
    def reset(cls):
        cls.private,cls.corrupt,cls.use_lfs,cls.missing_manifest=True,False,False,False
        cls.head="a"*40
        cls.snapshots={cls.head:{}}
        cls.commits=[]
        cls.requests=[]

    def __init__(self, **kwargs):
        pass

    def whoami(self):
        return {"name":"TryDotAtwo"}

    def repo_info(self,*args,**kwargs):
        return SimpleNamespace(private=self.private,sha=self.head)

    def create_commit(self,repo_id,operations,**kwargs):
        assert kwargs["parent_commit"]==self.head
        staged=dict(self.snapshots[self.head])
        for operation in operations:
            source=operation.path_or_fileobj
            data=Path(source).read_bytes() if isinstance(source,(str,Path)) else source.getvalue()
            staged[operation.path_in_repo]=data
        self.commits.append([operation.path_in_repo for operation in operations])
        type(self).head=("%040x"%len(self.commits))
        self.snapshots[self.head]=staged
        return SimpleNamespace(oid=self.head)

    def get_paths_info(self,repo_id,paths,**kwargs):
        revision=kwargs["revision"]
        self.requests.append((revision,list(paths)))
        objects=self.snapshots[revision]
        result=[]
        for name in paths:
            if name not in objects or (self.missing_manifest and name.startswith("manifests/")):
                continue
            data=objects[name]
            blob=hashlib.sha1(("blob "+str(len(data))+chr(0)).encode()+data).hexdigest()
            lfs=SimpleNamespace(sha256=("0"*64 if self.corrupt else hashlib.sha256(data).hexdigest())) if self.use_lfs else None
            result.append(SimpleNamespace(path=name,size=len(data),lfs=lfs,
                                          blob_id="0"*40 if self.corrupt else blob))
        return result

    def hf_hub_download(self,filename,**kwargs):
        data=self.snapshots[kwargs["revision"]][filename]
        path=Path(self.download_root)/hashlib.sha256(filename.encode()).hexdigest()
        path.write_bytes(data)
        return str(path)

def manifest(root,names):
    return {"schema":"faithful-fly-artifacts-v1","files":{
        name:{"bytes":(root/name).stat().st_size,"sha256":archive.digest(root/name)}
        for name in names}}

def publish(root,record,**kwargs):
    return archive.publish(root,record,commit_interval_seconds=0,**kwargs)

def run():
    checks=[]
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/"source";root.mkdir()
        (root/"trace.bin").write_bytes(b"known-episode"+bytes([0,1]))
        record=manifest(root,["trace.bin"])
        for unsafe in ("../token","/tmp/token","build/molab_pair.private.json",".env","a/../../b"):
            try:archive.checked_path(root,unsafe)
            except ValueError:pass
            else:raise AssertionError("Unsafe path accepted")
        (root/"escape").symlink_to(Path(td),target_is_directory=True)
        try:archive.checked_path(root,"escape/file")
        except ValueError:pass
        else:raise AssertionError("Symlink escape accepted")
        checks.append("unsafe and secret paths rejected")
        with patch.dict(os.environ,{"HF_TOKEN":"offline-fixture-token"}),patch("huggingface_hub.HfApi",FakeAPI):
            FakeAPI.reset()
            FakeAPI.corrupt=True
            receipt=None
            try:receipt=publish(root,record)
            except ValueError as error:assert "blob" in str(error)
            else:raise AssertionError("Corrupt remote identity admitted")
            assert receipt is None
            # Atomic commit may exist; a verified receipt MUST NOT exist.
            assert len(FakeAPI.commits)==1
            checks.append("remote Git mismatch withholds admission after atomic commit")

            FakeAPI.reset()
            receipt=publish(root,record)
            assert receipt["files"]==1 and receipt["verified"] is True
            assert len(FakeAPI.commits)==1
            assert len(FakeAPI.commits[0])==2
            assert any(p.startswith("objects/") for p in FakeAPI.commits[0])
            assert any(p.startswith("manifests/") for p in FakeAPI.commits[0])
            repeated=publish(root,record)
            assert repeated["revision"]==receipt["revision"] and len(FakeAPI.commits)==1
            checks.append("one commit includes object and manifest; repeated publish creates none")

            (root/"alias.bin").write_bytes((root/"trace.bin").read_bytes())
            alias=publish(root,manifest(root,["trace.bin","alias.bin"]))
            assert alias["files"]==2 and len(FakeAPI.commits[-1])==1
            assert FakeAPI.commits[-1][0].startswith("manifests/")
            checks.append("duplicate content deduplicated; verified existing object reused")

            FakeAPI.download_root=Path(td)/"downloads";FakeAPI.download_root.mkdir()
            restored=Path(td)/"restore"
            archive.restore(restored,receipt)
            assert (restored/"trace.bin").read_bytes()==(root/"trace.bin").read_bytes()
            (restored/"trace.bin").write_bytes(b"changed")
            try:archive.restore(restored,receipt)
            except ValueError as error:assert "overwrite" in str(error)
            else:raise AssertionError("Differing restore target overwritten")
            checks.append("old immutable receipt restores exactly after a later commit; no overwrite")

            FakeAPI.reset()
            FakeAPI.use_lfs=True
            publish(root,record)
            FakeAPI.corrupt=True
            try:publish(root,record)
            except ValueError as error:assert "LFS" in str(error)
            else:raise AssertionError("Corrupt LFS object admitted")
            checks.append("LFS SHA256 checked")

            FakeAPI.reset()
            FakeAPI.missing_manifest=True
            try:publish(root,record)
            except ValueError as error:assert "manifest missing" in str(error)
            else:raise AssertionError("Missing final manifest admitted")
            checks.append("missing final manifest withholds receipt")

            FakeAPI.reset()
            FakeAPI.private=False
            try:publish(root,record)
            except ValueError as error:assert "private" in str(error)
            else:raise AssertionError("Public archive accepted")
            assert not FakeAPI.commits
            checks.append("public repository rejected before commit")

            FakeAPI.reset()
            (root/"second.bin").write_bytes(b"second payload")
            (root/"third.bin").write_bytes(b"third payload")
            large=publish(root,manifest(root,["trace.bin","second.bin","third.bin"]),batch_size=1)
            assert len(FakeAPI.commits)==3
            final_requests=[paths for revision,paths in FakeAPI.requests if revision==large["revision"]]
            assert sum(any(p.startswith("objects/") for p in paths) for paths in final_requests)==3
            assert any(any(p.startswith("manifests/") for p in paths) for paths in final_requests)
            checks.append("bounded staging rechecks all objects and manifest at final immutable commit")

            FakeAPI.reset()
            def mutate_before_commit(api,repo_id,revision,factory,interval):
                (root/"trace.bin").write_bytes(b"changed during pacing")
                return api.create_commit(repo_id,operations=factory(),parent_commit=revision)
            with patch.object(archive,"_paced_commit",mutate_before_commit):
                try:publish(root,record)
                except ValueError as error:assert "changed before upload" in str(error)
                else:raise AssertionError("Mutation during pacing accepted")
            assert not FakeAPI.commits
            checks.append("local mutation during commit wait rejected before upload")

            try:archive.publish(root,manifest(root,["trace.bin"]),commit_interval_seconds=30)
            except ValueError as error:assert "31" in str(error)
            else:raise AssertionError("Unsafe production pacing accepted")
            checks.append("production pacing minimum validated")
    print(json.dumps({"archive_contract_checks":"passed","network_upload_tested":False,"checks":checks}))

if __name__=="__main__":
    run()
