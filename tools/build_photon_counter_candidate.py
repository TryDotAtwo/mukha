"""Build isolated counter-RNG VisTrans from the pinned coupled-current source."""
from pathlib import Path
import hashlib
import json
import subprocess


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def one(source, old, new):
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f'Expected one source anchor, found {count}: {old[:100]!r}')
    return source.replace(old, new)


COUNTER_RNG = r'''
struct CounterRng {
    unsigned long long seed, tick;
    unsigned int id;
    unsigned long long draw;
    uint4 cache;
};

__device__ __forceinline__ float ff_counter_uniform(CounterRng* rng) {
    const unsigned long long index = rng->draw;
    if (index >= (1ull << 34)) {
        asm volatile("trap;");
        return 0.f;
    }
    ++rng->draw;
    if ((index & 3ull) == 0) {
        const uint4 counter = make_uint4(rng->id, (unsigned int)rng->tick,
                                         (unsigned int)(rng->tick >> 32),
                                         (unsigned int)(index >> 2));
        const uint2 key = make_uint2((unsigned int)rng->seed,
                                     (unsigned int)(rng->seed >> 32));
        rng->cache = curand_Philox4x32_10(counter, key);
    }
    const unsigned int lane = (unsigned int)(index & 3ull);
    const unsigned int word = lane == 0 ? rng->cache.x :
                              lane == 1 ? rng->cache.y :
                              lane == 2 ? rng->cache.z : rng->cache.w;
    return _curand_uniform(word);
}
'''


def transform_header(source):
    source = one(source, '#define LA 0.5', '#define LA 0.5\n' + COUNTER_RNG)
    source = one(source, 'transduction(curandStateXORWOW_t *state, float dt,',
                 'transduction(unsigned long long seed, unsigned long long tick, float dt,')
    source = one(source, 'curandStateXORWOW_t localstate = state[mid];',
                 'CounterRng localstate{seed,tick,(unsigned int)mid,0,make_uint4(0,0,0,0)};')
    source = one(source, '        state[mid] = localstate;',
                 '        // Stateless stream is reconstructed from seed, entity and tick.')
    if source.count('curand_uniform(&localstate)') != 3:
        raise RuntimeError('Unexpected source draw count')
    source = source.replace('curand_uniform(&localstate)', 'ff_counter_uniform(&localstate)')
    return source


def transform_model(source):
    source = one(source, 'photon_coupled_current_build_id.h',
                 'photon_counter_build_id.h')
    source = one(source, '"phototransduction_safe.cuh"',
                 '"phototransduction_counter.cuh"')
    source = one(source, '                                curandStateXORWOW_t* rng,int total,int m,',
                 '                                int total,int m,')
    source = one(source, 'owner[i]=i/m; curand_init(seed,i,0,rng+i);',
                 'owner[i]=i/m;')
    source = one(source, '    DeviceArray<curandStateXORWOW_t> rng;\n', '')
    source = one(source, ',rng(total),host(9*n)', ',host(9*n)')
    source = one(source,
                 '        // Make opaque RNG padding deterministic as well as the initialized fields.\n'
                 '        check(cudaMemset(rng.p,0,size_t(total)*sizeof(curandStateXORWOW_t)));\n', '')
    source = one(source, '(x0.p,owner.p,rng.p,total,m,seed);',
                 '(x0.p,owner.p,total,m,seed);')
    source = one(source, 'transduction<<<blocks,128>>>(rng.p,1e-4f,',
                 'transduction<<<blocks,128>>>(episode_seed,tick,1e-4f,')
    source = one(source, 'std::array<Piece,7> pieces()',
                 'std::array<Piece,6> pieces()')
    source = one(source,
                 '                 {rng.p,size_t(total)*sizeof(curandStateXORWOW_t)},\n', '')
    source = one(source, 'snapshot_magic,1,uint64_t(n)',
                 'snapshot_magic,2,uint64_t(n)')
    source = one(source, 'uint64_t(blocks),sizeof(curandStateXORWOW_t),CUDART_VERSION',
                 'uint64_t(blocks),0,CUDART_VERSION')
    source = one(source, 'header[1]!=1', 'header[1]!=2')
    source = one(source, 'header[5]!=sizeof(curandStateXORWOW_t)', 'header[5]!=0')
    if 'rng.p' in source or 'state[mid]' in source:
        raise RuntimeError('Persistent RNG reference remains')
    return source


def run(root=Path('/marimo/fly-project')):
    root = Path(root)
    from hf_artifact_archive import publish
    base_header = root / 'native/phototransduction_safe.cuh'
    base_model = root / 'build/photon_coupled_current_diagnostic.cu'
    expected = {
        base_header: '4a6d0a73dc52eb9e86c4a17deb1a321e9db61215a5c8c104be1fd4723c22288b',
        base_model: '30e590a1ff30532a06f05b848e69f2e054b66c503189b966f328e76fba7f9541',
    }
    for path, sha in expected.items():
        if digest(path) != sha:
            raise RuntimeError(f'Pinned input changed: {path}')
    folder = root / 'data/derived/photon_counter_candidate_v2'
    folder.mkdir(parents=True, exist_ok=False)
    header = root / 'build/phototransduction_counter.cuh'
    source = root / 'build/photon_counter_diagnostic.cu'
    build_id = root / 'build/photon_counter_build_id.h'
    library = folder / 'libfly_photon_counter_diagnostic.so'
    header.write_text(transform_header(base_header.read_text()))
    source.write_text(transform_model(base_model.read_text()))
    cuda = root / 'build/cuda-13.1.1'
    dependencies = [header, source, root / 'build/photocurrent_coupled.cuh',
                    root / 'build/photoreceptor_hh_coupled.cu',
                    root / 'build/photoreceptor_author_adaptation.cu',
                    cuda / 'include/curand_philox4x32_x.h',
                    cuda / 'include/curand_uniform.h']
    identity = hashlib.sha256(json.dumps(
        {p.relative_to(root).as_posix(): digest(p) for p in dependencies},
        sort_keys=True).encode()).hexdigest()
    build_id.write_text('#pragma once\n#define FP_BUILD_ID "' + identity + '"\n')
    command = [str(cuda / 'bin/nvcc'), '-std=c++17', '-O2', '-lineinfo',
               '-arch=sm_120', '--fmad=false', '-Xptxas=-v', '-shared',
               '-Xcompiler', '-fPIC', '-I', 'native', '-I', 'build',
               '-I', str(cuda / 'include'), '-L', str(cuda / 'lib'),
               str(source.relative_to(root)), '-o', str(library.relative_to(root))]
    built = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=180)
    log = folder / 'build.log'
    log.write_text(built.stdout + built.stderr)
    if built.returncode:
        raise RuntimeError(built.stderr[-4000:])
    report = {
        'scope': 'Isolated counter-Philox full-resolution coupled-current receptor candidate',
        'build_id': identity, 'binary_sha256': digest(library),
        'source_sha256': digest(source), 'transduction_sha256': digest(header),
        'incumbent_source_sha256': digest(base_model),
        'incumbent_transduction_sha256': digest(base_header),
        'build_command': command,
        'checkpoint_version': 2,
        'validation_status': 'compiled only; runtime, replay, distribution and speed unverified',
    }
    result = folder / 'report.json'
    result.write_text(json.dumps(report, indent=2))
    files = [base_header, base_model, header, source, build_id, library, log,
             result, root / 'tools/build_photon_counter_candidate.py',
             *dependencies[2:5]]
    manifest = {'schema': 'faithful-fly-artifacts-v1', 'scope': report['scope'],
                'files': {p.relative_to(root).as_posix(): {'bytes': p.stat().st_size,
                                                           'sha256': digest(p)} for p in files}}
    receipt = publish(root, manifest)
    print('PHOTON_COUNTER_BUILD', json.dumps(report), flush=True)
    print('PHOTON_COUNTER_ARCHIVE', json.dumps(receipt), flush=True)
    return receipt


if __name__ == '__main__':
    run()
