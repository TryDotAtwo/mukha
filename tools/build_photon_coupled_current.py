"""Diagnostic: recompute TRP current from current membrane voltage each HH substep."""
from pathlib import Path
import hashlib
import json
import subprocess


def replace_one(source,old,new):
    assert source.count(old)==1,(old,source.count(old))
    return source.replace(old,new)


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    original_current=(root/'native/photocurrent_safe.cuh').read_text()
    current=replace_one(original_current,
        '''        double Vm = (d_Vm[bid]-TRP_REV) * 0.001;
        double I_in;
        if(Vm < 0)
            I_in = total_open_channel * G_TRP * (-Vm);
        else
            I_in = 0;

        I_all[bid] = I_fb[bid] + I_in / 15.7; // convert pA into \\muA/cm^2''',
        '''        // Hold channel count over the 0.1-ms receptor tick, not its current.
        // HH applies the current driving force using its current membrane voltage.
        I_all[bid] = total_open_channel * (G_TRP * 0.001 / 15.7);''')
    current_path=root/'build/photocurrent_coupled.cuh'
    current_path.write_text(current)

    original_hh=(root/'build/photoreceptor_hh_exact_gates.cu').read_text()
    hh=replace_one(original_hh,
                   'hh(double* I_all, double* d_V, double* d_sa, double* d_si,',
                   'hh(double* I_all, double* I_fb, double* d_V, double* d_sa, double* d_si,')
    hh=replace_one(hh,'        double I = I_all[tid];',
                   '        double channel_conductance = I_all[tid];\n        double feedback = I_fb[tid];')
    hh=replace_one(hh,'            dx = (I - G_K*(V-E_K)',
                   '            double I = feedback + channel_conductance * fmax(-V, 0.0);\n            dx = (I - G_K*(V-E_K)')
    hh_path=root/'build/photoreceptor_hh_coupled.cu'
    hh_path.write_text(hh)

    original=(root/'build/photon_exact_gates_diagnostic.cu').read_text()
    source=replace_one(original,'photon_exact_gates_build_id.h','photon_coupled_current_build_id.h')
    source=replace_one(source,'photocurrent_safe.cuh','photocurrent_coupled.cuh')
    source=replace_one(source,'photoreceptor_hh_exact_gates.cu','photoreceptor_hh_coupled.cu')
    source=replace_one(source,'hh<<<(n+31)/32,32>>>(current.p,state.p,',
                       'hh<<<(n+31)/32,32>>>(current.p,feedback.p,state.p,')
    source_path=root/'build/photon_coupled_current_diagnostic.cu'
    source_path.write_text(source)
    identity=hashlib.sha256((source+current+hh).encode()).hexdigest()
    header=root/'build/photon_coupled_current_build_id.h'
    header.write_text('#pragma once\n#define FP_BUILD_ID "'+identity+'"\n')
    binary=root/'build/libfly_photon_coupled_current_diagnostic.so'
    nvcc=root/'build/cuda-13.1.1/bin/nvcc'
    cuda_root=nvcc.parent.parent
    command=[str(nvcc),'-std=c++17','-O2','-lineinfo','-arch=sm_120','--fmad=false',
             '-shared','-Xcompiler','-fPIC','-I','native','-I','build',
             '-I',str(cuda_root/'include'),'-L',str(cuda_root/'lib'),
             str(source_path.relative_to(root)),'-o',str(binary.relative_to(root))]
    try:
        subprocess.run(command,cwd=root,check=True,capture_output=True,text=True)
    except subprocess.CalledProcessError as exc:
        print('COUPLED_CURRENT_BUILD_ERROR',exc.stderr[-4000:],flush=True)
        raise
    report={'build_id':identity,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
            'current_sha256':hashlib.sha256(current.encode()).hexdigest(),
            'hh_sha256':hashlib.sha256(hh.encode()).hexdigest(),
            'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
            'change':'Same channel count each 0.1ms, TRP conductance multiplied by current substep V; exact gate integrator retained. Diagnostic only.'}
    (root/'build/photon_coupled_current_build.json').write_text(json.dumps(report,indent=2))
    print('COUPLED_CURRENT_BUILD',json.dumps(report),flush=True)
    return report


if __name__=='__main__':
    run()
