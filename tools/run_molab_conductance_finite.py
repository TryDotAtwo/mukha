"""Foreground MoLab-only build/test with immediate verified HF stage receipts."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile

REPO = "TryDotAtwo/faithful-fly-artifacts"

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8*1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def run_logged(command, cwd, log_path):
    # Foreground child owned by this visible notebook execution. No detached jobs.
    with log_path.open("w") as log:
        proc = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, bufsize=1)
        lines = queue.Queue()
        def collect():
            try:
                for line in proc.stdout:
                    lines.put(line)
            finally:
                lines.put(None)
        reader = threading.Thread(target=collect)
        reader.start()
        ended = False
        started = time.monotonic()
        try:
            while not ended:
                try:
                    line = lines.get(timeout=15)
                except queue.Empty:
                    print("HEARTBEAT", log_path.name, int(time.monotonic()-started), flush=True)
                    continue
                if line is None:
                    ended = True
                else:
                    log.write(line)
                    log.flush()
                    print(line[:2000], end="" if line.endswith("\n") else "\n", flush=True)
            code = proc.wait()
            reader.join()
        except BaseException:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            reader.join()
            raise
    return code

def publish(root, paths, archive, stage, receipts):
    files = {}
    for relative in paths:
        path = root / relative
        files[relative] = {"bytes": path.stat().st_size, "sha256": sha(path)}
    receipt = archive.publish(root, {"schema": "faithful-fly-artifacts-v1", "files": files})
    receipt["stage"] = stage
    receipts.append(receipt)
    print("HF_STAGE_RECEIPT", json.dumps(receipt, sort_keys=True), flush=True)
    # Each next stage depends on publish() having verified objects and committed its manifest.
    return receipt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-commit", required=True)
    ap.add_argument("--baseline-commit", required=True)
    ap.add_argument("--root", required=True)
    args = ap.parse_args()
    if not os.environ.get("HF_TOKEN"):
        raise RuntimeError("HF_TOKEN missing from MoLab Secrets")
    from huggingface_hub import HfApi
    api = HfApi(token=os.environ["HF_TOKEN"])
    info = api.repo_info(REPO, repo_type="dataset")
    if not info.private or api.whoami()["name"] != "TryDotAtwo":
        raise RuntimeError("Expected private project archive and owner")
    # No work resumes into an ambiguous prior directory.
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=False)
    logs = root / "logs"
    logs.mkdir()
    checkout = root / "source"
    subprocess.run(["git", "init", str(checkout)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(checkout), "remote", "add", "origin",
                    "https://github.com/TryDotAtwo/mukha.git"], check=True)
    for revision in (args.source_commit, args.baseline_commit):
        subprocess.run(["git", "-C", str(checkout), "fetch", "--depth=1", "origin", revision],
                       check=True, capture_output=True)
    subprocess.run(["git", "-C", str(checkout), "checkout", "--detach", args.source_commit],
                   check=True, capture_output=True)
    actual = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
    if actual != args.source_commit:
        raise RuntimeError("Source commit mismatch")
    baseline = root / "baseline"
    baseline.mkdir()
    for filename in ("cuda_conductance.cu", "cuda_conductance.h"):
        data = subprocess.check_output(["git", "-C", str(checkout), "show",
                                       args.baseline_commit + ":native/" + filename])
        (baseline / filename).write_bytes(data)
    nvcc = shutil.which("nvcc")
    if not nvcc:
        raise RuntimeError("No nvcc installed; stop instead of local build fallback")
    cuda = Path(nvcc).resolve().parent.parent
    if not (cuda / "include/cusparse.h").exists():
        raise RuntimeError("cuSPARSE headers missing")
    libdir = cuda / "lib"
    cusparse = libdir / "libcusparse.so.12"
    if not cusparse.exists():
        raise RuntimeError("Expected installed cuSPARSE library missing")
    hardware = subprocess.check_output(["nvidia-smi",
        "--query-gpu=name,compute_cap,memory.total,driver_version",
        "--format=csv,noheader"], text=True)
    active = subprocess.check_output(["nvidia-smi",
        "--query-compute-apps=pid,process_name", "--format=csv,noheader"], text=True).strip()
    if active:
        raise RuntimeError("GPU already has compute processes; stop instead of competing")
    # Recover missing CCCL from a pinned official wheel, inside MoLab only.
    dependency_paths = []
    cccl = cuda / "include"
    if not (cccl / "nv/target").exists():
        dependencies = root / "dependencies"
        dependencies.mkdir()
        with urllib.request.urlopen("https://pypi.org/pypi/nvidia-cuda-cccl/13.0.85/json", timeout=30) as response:
            package = json.load(response)
        wheels = [f for f in package["urls"] if f["filename"].endswith(".whl")
                  and "manylinux2014_x86_64" in f["filename"]]
        if len(wheels) != 1:
            raise RuntimeError("Expected unique pinned Linux CCCL wheel")
        entry = wheels[0]
        if not entry["url"].startswith("https://files.pythonhosted.org/"):
            raise RuntimeError("Unexpected dependency origin")
        wheel = dependencies / entry["filename"]
        with urllib.request.urlopen(entry["url"], timeout=60) as response:
            wheel.write_bytes(response.read())
        if sha(wheel) != entry["digests"]["sha256"]:
            raise RuntimeError("CCCL wheel identity mismatch")
        extracted = dependencies / "cccl"
        with zipfile.ZipFile(wheel) as archive_file:
            for name in archive_file.namelist():
                if Path(name).is_absolute() or ".." in Path(name).parts:
                    raise RuntimeError("Unsafe wheel member")
            archive_file.extractall(extracted)
        targets = [extracted / "nvidia/cu13/include/nv/target"]
        targets = [path for path in targets if path.is_file()]
        if len(targets) != 1:
            raise RuntimeError("Expected unique CCCL nv/target")
        cccl = targets[0].parent.parent
        dependency_paths.append(str(wheel.relative_to(root)))
    toolchain = subprocess.check_output([nvcc, "--version"], text=True)
    metadata = {"source_commit": actual, "baseline_commit": args.baseline_commit,
                "gpu": hardware, "nvcc": toolchain, "cccl_include": str(cccl), "dependency_files": dependency_paths, "flags": ["-std=c++17", "-O2",
                "-arch=sm_120", "--fmad=false", "--shared", "-Xcompiler=-fPIC"],
                "scope": "Tiny GPU arithmetic failure regression, not physiology or full-graph performance"}
    (root / "metadata.json").write_text(json.dumps(metadata, indent=2))
    archive_spec = importlib.util.spec_from_file_location("fly_archive",
                                                         checkout / "tools/hf_artifact_archive.py")
    archive = importlib.util.module_from_spec(archive_spec)
    archive_spec.loader.exec_module(archive)
    receipts = []
    closure = ["metadata.json", "baseline/cuda_conductance.cu", "baseline/cuda_conductance.h",
               "source/AGENTS.md", "source/native/cuda_conductance.cu", "source/native/cuda_conductance.h",
               "source/tools/check_conductance_finite_state.py",
               "source/tools/run_molab_conductance_finite.py", "source/tools/hf_artifact_archive.py",
               "source/docs/CONDUCTANCE_FINITE_PROTOCOL.md"]
    closure.extend(dependency_paths)
    publish(root, closure, archive, "source-input-closure", receipts)
    outputs = root / "outputs"
    outputs.mkdir()
    libraries = {}
    for label, src in (("baseline", baseline), ("candidate", checkout / "native")):
        target = outputs / (label + ".so")
        log = logs / (label + "-build.log")
        command = [nvcc, "-std=c++17", "-O2", "-arch=sm_120", "--fmad=false",
                   "--shared", "-Xcompiler=-fPIC", "-I" + str(cuda/"include"), "-I" + str(cccl),
                   str(src/"cuda_conductance.cu"), "-o", str(target), "-Xlinker", str(cusparse),
                   "-Xlinker=-rpath," + str(libdir)]
        status = run_logged(command, root, log)
        stage_paths = [str(log.relative_to(root))]
        if status == 0:
            libraries[label] = target
            stage_paths.append(str(target.relative_to(root)))
        publish(root, stage_paths, archive, label + "-build", receipts)
        if status:
            raise RuntimeError(label + " build failed; its log is archived")
    report = outputs / "finite-state-report.json"
    log = logs / "finite-state-test.log"
    command = [sys.executable, str(checkout/"tools/check_conductance_finite_state.py"),
               "--library", str(libraries["candidate"]), "--baseline", str(libraries["baseline"]),
               "--report", str(report)]
    status = run_logged(command, root, log)
    final_paths = [str(log.relative_to(root))]
    if report.exists():
        final_paths.append(str(report.relative_to(root)))
    publish(root, final_paths, archive, "finite-state-test", receipts)
    (root / "receipts.json").write_text(json.dumps(receipts, indent=2))
    publish(root, ["receipts.json"], archive, "receipt-chain", [])
    if status:
        raise RuntimeError("GPU regression failed; its terminal log is archived")
    print("REMOTE_SLICE_COMPLETE", json.dumps({"source_commit": actual, "test_passed": True,
                                               "result_receipt": receipts[-1]}), flush=True)

if __name__ == "__main__":
    main()
