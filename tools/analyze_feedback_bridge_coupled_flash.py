"""Matched old/new receptor comparison within one configured full-CNS bridge."""
from pathlib import Path
import json
import os

import numpy as np
import pandas as pd


def response_stats(mean, sign):
    signed=sign*mean
    peak=int(np.argmax(signed[:100]))
    first=float(signed[peak])
    opposite=float(np.max(-signed[100:500]))
    return {'min_mV':float(np.min(mean)),'min_ms':int(np.argmin(mean))+1,
            'max_mV':float(np.max(mean)),'max_ms':int(np.argmax(mean))+1,
            'initial_signed_peak_mV':float(mean[peak]),'initial_peak_ms':peak+1,
            'opposite_abs_mV':opposite,
            'opposite_to_initial_ratio':opposite/first if first>0 else None}


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from huggingface_hub import HfApi
    from hf_artifact_archive import digest,validate_manifest,publish
    old=root/'data/derived/visual_feedback_flash_v1'
    new=root/'data/derived/visual_feedback_coupled_flash_v1'
    api=HfApi(token=os.environ.get('HF_TOKEN'))
    receipts={}
    for name in ('gray','light','dark'):
        receipt=json.loads((new/name/'receipt.json').read_text())
        manifest_path=Path(api.hf_hub_download(repo_id=receipt['repo_id'],
                            filename=receipt['manifest'],repo_type='dataset',revision=receipt['revision']))
        assert digest(manifest_path)==receipt['sha256']
        validate_manifest(root,json.loads(manifest_path.read_text()))
        receipts[name]=receipt
        old_stimulus=old/('intact_'+name)/'stimulus.bin'
        assert digest(new/name/'stimulus.bin')==digest(old_stimulus)
    with (root/'data/derived/lamina_native_photon_v1/graph.bin').open('rb') as stream:
        n,m,nr,nt=map(int,np.fromfile(stream,'<u4',4))
        pre=np.fromfile(stream,'<u4',m)
        post=np.fromfile(stream,'<u4',m)
        stream.seek(8*m,1)
        receptor_ids=np.fromfile(stream,'<u4',nr)
        target_ids=np.fromfile(stream,'<u4',nt)
    with (root/'data/derived/image_lamina_probe_v1/rays.bin').open('rb') as stream:
        mapped=np.fromfile(stream,'<u4',int(np.fromfile(stream,'<u4',1)[0]))
    exposed=np.unique(post[np.isin(pre,mapped)])
    nodes=pd.read_feather(root/'data/derived/malecns_v1_candidates/nodes.feather').set_index('compact_index')
    types=nodes.loc[target_ids,'type'].to_numpy()
    masks={typ:np.flatnonzero((types==typ)&np.isin(target_ids,exposed)) for typ in ('L1','L2')}
    assert all(len(mask)==416 for mask in masks.values())
    receptor_mask=np.isin(receptor_ids,mapped)
    assert int(receptor_mask.sum())==1843
    traces={}
    records=[]
    baselines=[]
    for variant,base in (('original',old),('coupled',new)):
        folder=lambda name:base/('intact_'+name if variant=='original' else name)
        gray=np.memmap(folder('gray')/'output.bin',dtype='<f8',mode='r',shape=(1020,nt,2))[:,:,0]
        gray_receptor=np.memmap(folder('gray')/'output.bin.feedback',dtype='<f8',mode='r',shape=(1020,2,nr))[:,1,:]
        for typ,mask in masks.items():
            baselines.append({'variant':variant,'population':typ,
                              'preflash_voltage_mV':float(gray[499,mask].mean())})
        baselines.append({'variant':variant,'population':'mapped_R1R6',
                          'preflash_voltage_mV':float(gray_receptor[499,receptor_mask].mean())})
        for name,sign in (('light',-1),('dark',1)):
            output=np.memmap(folder(name)/'output.bin',dtype='<f8',mode='r',shape=(1020,nt,2))[:,:,0]
            receptor=np.memmap(folder(name)/'output.bin.feedback',dtype='<f8',mode='r',shape=(1020,2,nr))[:,1,:]
            assert np.array_equal(output[:500],gray[:500])
            assert np.array_equal(receptor[:500],gray_receptor[:500])
            for typ,mask in masks.items():
                mean=(output[500:,mask]-gray[500:,mask]).mean(axis=1)
                traces[f'{variant}_{name}_{typ}']=mean
                rec={'variant':variant,'condition':name,'population':typ,'cells':len(mask),
                     **response_stats(mean,sign)}
                records.append(rec)
                print('MATCHED_FLASH_RESPONSE',json.dumps(rec),flush=True)
            mean=(receptor[500:,receptor_mask]-gray_receptor[500:,receptor_mask]).mean(axis=1)
            traces[f'{variant}_{name}_mapped_R1R6']=mean
            rec={'variant':variant,'condition':name,'population':'mapped_R1R6',
                 'cells':int(receptor_mask.sum()),**response_stats(mean,-sign)}
            records.append(rec)
            print('MATCHED_FLASH_RESPONSE',json.dumps(rec),flush=True)
    comparisons=[]
    for name in ('light','dark'):
        for typ in ('L1','L2','mapped_R1R6'):
            a=traces[f'original_{name}_{typ}']
            b=traces[f'coupled_{name}_{typ}']
            delta=b-a
            rec={'condition':name,'population':typ,
                 'max_abs_mean_difference_mV':float(np.max(np.abs(delta))),
                 'rms_mean_difference_mV':float(np.sqrt(np.mean(delta*delta)))}
            comparisons.append(rec)
            print('MATCHED_FLASH_COMPARISON',json.dumps(rec),flush=True)
    report={'scope':'Matched full configured visual bridge old-versus-coupled receptor, 500/20/500ms, one seed',
            'new_receipts':receipts,'records':records,'baselines':baselines,
            'comparisons':comparisons,'biological_gate_passed':False,
            'correction_of_prior_cross_bridge_comparison':{
                'prior_manifest':'manifests/c0c43f5db6c426d70f4379cab0d6463e8b8f616b1c4d39f7be886b190a26a5cd.json',
                'reason':'Prior old/new comparison changed the entire configured visual bridge, including visual profile and remaining routes; it cannot isolate receptor coupling.'},
            'limitations':'Uncalibrated photon mapping and engineered neural parameters; numerical diagnostic, not biological validation.'}
    folder=root/'data/derived/visual_feedback_coupled_analysis_v1'
    folder.mkdir(parents=True,exist_ok=False)
    report_path=folder/'report.json'
    report_path.write_text(json.dumps(report,indent=2))
    trace_path=folder/'mean_responses.npz'
    np.savez_compressed(trace_path,**traces)
    files=[report_path,trace_path,root/'tools/analyze_feedback_bridge_coupled_flash.py']
    manifest={'schema':'faithful-fly-artifacts-v1','scope':report['scope'],
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('MATCHED_FLASH_ANALYSIS_ARCHIVE',json.dumps(receipt),flush=True)
    return receipt


if __name__=='__main__':run()
