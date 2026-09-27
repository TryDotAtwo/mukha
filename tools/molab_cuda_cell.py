def prepare_fly_cuda():
    import hashlib, json, shutil, subprocess, tarfile, urllib.request
    from pathlib import Path
    packages = {'cuda_nvcc': {'relative_path': 'cuda_nvcc/linux-x86_64/cuda_nvcc-linux-x86_64-13.1.115-archive.tar.xz', 'sha256': '858a74e6caa36fc9b4fa1ec5e8d38f568ab8046ef93dca9ba8b3f01dee09f30d', 'md5': 'ca780856ff3ba0f1512625c9561d635f', 'size': '29853656'}, 'cuda_crt': {'relative_path': 'cuda_crt/linux-x86_64/cuda_crt-linux-x86_64-13.1.115-archive.tar.xz', 'sha256': 'e2861bbc6400815be6689cdc84afddfedc51103189888c8e51a2e9543e55a5b3', 'md5': '1f90321a7b5d3c90fd43dcfde32f4fa8', 'size': '79628'}, 'libnvvm': {'relative_path': 'libnvvm/linux-x86_64/libnvvm-linux-x86_64-13.1.115-archive.tar.xz', 'sha256': '9038a2bf1237d9decdf99d90c4b43639536c9dbe4b3a40d1e6add5413a02096f', 'md5': '07734e404dcfbf1af554655da16b62b0', 'size': '44800332'}, 'cuda_cudart': {'relative_path': 'cuda_cudart/linux-x86_64/cuda_cudart-linux-x86_64-13.1.80-archive.tar.xz', 'sha256': 'b626f4790f46bc9324a1047f2fbcc9a42bc4a722b053056e61cc00da54ad6f32', 'md5': '6292418213e658b4bb9d3191231d1198', 'size': '1549648'}, 'cuda_cccl': {'relative_path': 'cuda_cccl/linux-x86_64/cuda_cccl-linux-x86_64-13.1.115-archive.tar.xz', 'sha256': 'b0fff2704e59d4e6f6f4b7b5b64f96a7bf86760a5696fd6cb6936f8f9cd92d4c', 'md5': 'c09be80208061a2cd75f78cc3dc5a2a7', 'size': '1094324'}}
    root = Path('/tmp/fly-cuda-13.1.1')
    root.mkdir(exist_ok=True)
    for name, spec in packages.items():
        archive = root / (name+'.tar.xz')
        print('DOWNLOAD', name, flush=True)
        if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest()!=spec['sha256']:
            with urllib.request.urlopen('https://developer.download.nvidia.com/compute/cuda/redist/'+spec['relative_path'], timeout=30) as response, archive.open('wb') as out:
                shutil.copyfileobj(response, out)
        assert archive.stat().st_size == int(spec['size'])
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == spec['sha256']
        unpack = root / name
        unpack.mkdir(exist_ok=True)
        with tarfile.open(archive) as tf:
            tf.extractall(unpack, filter='data')
        source = next(p for p in unpack.iterdir() if p.is_dir())
        for child in source.iterdir():
            if child.is_dir():
                shutil.copytree(child,root/child.name,dirs_exist_ok=True,symlinks=False)
        print('VERIFIED', name, spec['sha256'], flush=True)
    result = subprocess.run([str(root/'bin/nvcc'),'--version'], capture_output=True,text=True,check=True)
    print(result.stdout,flush=True)
    return {'root':str(root),'packages':packages,'nvcc':result.stdout}
fly_cuda_toolchain = prepare_fly_cuda()
