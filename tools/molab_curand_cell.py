def prepare_fly_curand(toolchain):
    import hashlib, shutil, tarfile, urllib.request
    from pathlib import Path
    spec = {'relative_path': 'libcurand/linux-x86_64/libcurand-linux-x86_64-10.4.1.81-archive.tar.xz', 'sha256': 'e15c2a59c29a0f3eb2b33c34c06cc1e1abba5b1b9ccf5e34c43d9787e84498dc', 'md5': '417353d105f551616de7f204c61f0514', 'size': '86661740'}
    root=Path(toolchain['root'])
    archive=root/'libcurand.tar.xz'
    print('DOWNLOAD libcurand',flush=True)
    if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest()!=spec['sha256']:
        with urllib.request.urlopen('https://developer.download.nvidia.com/compute/cuda/redist/'+spec['relative_path'],timeout=30) as response, archive.open('wb') as out:
            shutil.copyfileobj(response,out)
    assert archive.stat().st_size==int(spec['size'])
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==spec['sha256']
    unpack=root/'libcurand';unpack.mkdir(exist_ok=True)
    with tarfile.open(archive) as tf: tf.extractall(unpack,filter='data')
    source=next(p for p in unpack.iterdir() if p.is_dir())
    shutil.copytree(source/'include',root/'include',dirs_exist_ok=True)
    print('VERIFIED libcurand headers',spec['sha256'],flush=True)
    return spec
fly_curand_headers=prepare_fly_curand(fly_cuda_toolchain)
