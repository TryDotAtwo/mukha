"""SHA-verify and archive derived surrogate diagnostics to private HF storage."""
from pathlib import Path
import json


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from hf_artifact_archive import digest,publish
    files=[root/'data/derived/photon_sampled_benchmark_v1/noise_analysis.json',
           root/'data/derived/photon_surrogate_flash_v1/signed_phases.json',
           root/'tools/analyze_photon_sampled_noise.py',
           root/'tools/analyze_surrogate_flash_phases.py',
           root/'tools/archive_photon_surrogate_analyses.py']
    manifest={'schema':'faithful-fly-artifacts-v1',
              'scope':'Derived noise and sign-aware flash diagnostics for reduced photoreceptor models',
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('SURROGATE_ANALYSES_ARCHIVE',json.dumps(receipt),flush=True)
    return receipt


if __name__=='__main__':
    run()
