"""Paired gray-subtracted CNS and photoreceptor flash responses, no bio pass."""
from pathlib import Path
import json
import os

import numpy as np
import pandas as pd


def phase(mean,sign):
    peak=int(np.argmax(sign*mean[:100]))
    first=float(sign*mean[peak])
    opposite=float(np.max(-sign*mean[100:500]))
    return {'initial_signed_peak_mV':float(mean[peak]),'peak_ms':peak+1,
            'opposite_signed_mV':float(-sign*opposite),
            'opposite_abs_mV':opposite,
            'opposite_to_initial_ratio':opposite/first if first>0 else None}


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from huggingface_hub import HfApi
    from hf_artifact_archive import digest,validate_manifest,publish
    base=root/'data/derived/visual_coupled_flash_v1'
    api=HfApi(token=os.environ.get('HF_TOKEN'))
    receipts={}
    for condition in ('gray','light','dark'):
        receipt=json.loads((base/condition/'receipt.json').read_text())
        manifest_path=Path(api.hf_hub_download(repo_id=receipt['repo_id'],
                            filename=receipt['manifest'],repo_type='dataset',
                            revision=receipt['revision']))
        assert digest(manifest_path)==receipt['sha256']
        validate_manifest(root,json.loads(manifest_path.read_text()))
        receipts[condition]=receipt
    with (root/'data/derived/lamina_native_photon_v1/graph.bin').open('rb') as stream:
        n,m,nr,nt=map(int,np.fromfile(stream,'<u4',4))
        pre=np.fromfile(stream,'<u4',m)
        post=np.fromfile(stream,'<u4',m)
        stream.seek(8*m,1)
        receptor_ids=np.fromfile(stream,'<u4',nr)
        target_ids=np.fromfile(stream,'<u4',nt)
    with (root/'data/derived/image_lamina_probe_v1/rays.bin').open('rb') as stream:
        count=int(np.fromfile(stream,'<u4',1)[0])
        mapped=np.fromfile(stream,'<u4',count)
    exposed=np.unique(post[np.isin(pre,mapped)])
    nodes=pd.read_feather(root/'data/derived/malecns_v1_candidates/nodes.feather').set_index('compact_index')
    types=nodes.loc[target_ids,'type'].to_numpy()
    masks={typ:np.flatnonzero((types==typ)&np.isin(target_ids,exposed)) for typ in ('L1','L2')}
    assert all(len(mask)==416 for mask in masks.values())
    receptor_mask=np.isin(receptor_ids,mapped)
    assert int(receptor_mask.sum())==1843
    gray=np.memmap(base/'gray/output.bin',dtype='<f8',mode='r',shape=(1020,nt,2))[:,:,0]
    gray_receptor=np.memmap(base/'gray/output.bin.feedback',dtype='<f8',mode='r',shape=(1020,2,nr))[:,1,:]
    arrays={}
    records=[]
    for condition,sign in (('light',-1),('dark',1)):
        output=np.memmap(base/condition/'output.bin',dtype='<f8',mode='r',shape=(1020,nt,2))[:,:,0]
        receptor=np.memmap(base/condition/'output.bin.feedback',dtype='<f8',mode='r',shape=(1020,2,nr))[:,1,:]
        assert np.array_equal(output[:500],gray[:500])
        assert np.array_equal(receptor[:500],gray_receptor[:500])
        for typ,mask in masks.items():
            mean=(output[500:,mask]-gray[500:,mask]).mean(axis=1)
            rec={'condition':condition,'population':typ,'cells':len(mask),**phase(mean,sign)}
            records.append(rec)
            arrays[f'{condition}_{typ}']=mean
            print('COUPLED_FLASH_RESPONSE',json.dumps(rec),flush=True)
        mean=(receptor[500:,receptor_mask]-gray_receptor[500:,receptor_mask]).mean(axis=1)
        # Receptor sign may differ from L1/L2 sign, determine from initial response.
        receptor_sign=1 if abs(mean[:100].max())>=abs(mean[:100].min()) else -1
        rec={'condition':condition,'population':'mapped_R1R6','cells':int(receptor_mask.sum()),
             **phase(mean,receptor_sign)}
        records.append(rec)
        arrays[f'{condition}_mapped_R1R6']=mean
        print('COUPLED_FLASH_RESPONSE',json.dumps(rec),flush=True)
    old=root/'data/derived/visual_feedback_flash_v1'
    old_present=all((old/('intact_'+name)/'output.bin').is_file() for name in ('gray','light','dark'))
    comparisons=[]
    if old_present:
        old_gray=np.memmap(old/'intact_gray/output.bin',dtype='<f8',mode='r',shape=(1020,nt,2))[:,:,0]
        for condition in ('light','dark'):
            old_trace=np.memmap(old/('intact_'+condition)/'output.bin',dtype='<f8',mode='r',shape=(1020,nt,2))[:,:,0]
            for typ,mask in masks.items():
                old_mean=(old_trace[500:,mask]-old_gray[500:,mask]).mean(axis=1)
                new_mean=arrays[f'{condition}_{typ}']
                delta=new_mean-old_mean
                comparisons.append({'condition':condition,'population':typ,
                    'max_abs_mean_difference_mV':float(np.max(np.abs(delta))),
                    'rms_mean_difference_mV':float(np.sqrt(np.mean(delta*delta)))})
                arrays[f'{condition}_{typ}_old']=old_mean
    report={'scope':'Gray-subtracted full MaleCNS visual response with within-substep TRP coupling, one seed and uncalibrated light',
            'receipts':receipts,'records':records,'prior_intact_traces_present':old_present,
            'old_vs_new_cross_bridge_descriptive_only':comparisons,
            'cross_bridge_comparison_confounded':True,
            'confound':'The prior visual_feedback_ablation executable used a different configured profile and additional visual routes; these differences cannot be attributed to the receptor library.',
            'biological_gate_passed':False,
            'limitations':'No matched photon calibration or fluorescence observation model; engineered synaptic gains; 1843 mapped right-eye receptors, one seed.'}
    output_dir=root/'data/derived/visual_coupled_flash_analysis_v1'
    output_dir.mkdir(parents=True,exist_ok=False)
    report_path=output_dir/'report.json'
    report_path.write_text(json.dumps(report,indent=2))
    trace_path=output_dir/'mean_responses.npz'
    np.savez_compressed(trace_path,**arrays)
    files=[report_path,trace_path,root/'tools/analyze_visual_coupled_flash.py']
    manifest={'schema':'faithful-fly-artifacts-v1','scope':report['scope'],
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('COUPLED_FLASH_ANALYSIS_ARCHIVE',json.dumps(receipt),flush=True)
    return receipt


if __name__=='__main__':
    run()
