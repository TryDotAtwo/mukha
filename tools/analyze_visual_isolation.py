"""Compare blocked and fully isolated visual feedback runs in Molab."""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent))
from hf_artifact_archive import digest,validate_manifest


def run(root):
    from huggingface_hub import HfApi
    r=Path(root);base=r/'data/derived/visual_feedback_flash_v1';api=HfApi()
    receipts={}
    for mode in ('blocked','isolated'):
        for condition in ('gray','light','dark'):
            key=mode+'_'+condition
            receipt=json.loads((r/'reports'/('flash_v1_'+key+'_receipt.json')).read_text())
            p=Path(api.hf_hub_download(receipt['repo_id'],receipt['manifest'],repo_type='dataset',revision=receipt['revision']))
            assert digest(p)==receipt['sha256'],key
            validate_manifest(r,json.loads(p.read_text()))
            receipts[key]=receipt
    with (r/'data/derived/lamina_native_photon_v1/graph.bin').open('rb') as f:
        n,m,nr,nt=map(int,np.fromfile(f,'<u4',4));pre=np.fromfile(f,'<u4',m);post=np.fromfile(f,'<u4',m);f.seek(m*8,1);ri=np.fromfile(f,'<u4',nr);ti=np.fromfile(f,'<u4',nt)
    with (r/'data/derived/image_lamina_probe_v1/rays.bin').open('rb') as f:
        nv=int(np.fromfile(f,'<u4',1)[0]);mapped=np.fromfile(f,'<u4',nv)
    exposed=np.unique(post[np.isin(pre,mapped)])
    types=pd.read_feather(r/'data/derived/malecns_v1_candidates/nodes.feather').set_index('compact_index').loc[ti,'type'].to_numpy()
    masks={typ:np.flatnonzero((types==typ)&np.isin(ti,exposed)) for typ in ('L1','L2')}
    assert all(len(mask)==416 for mask in masks.values())
    means={};records=[]
    for mode in ('blocked','isolated'):
        gray=np.memmap(base/(mode+'_gray')/'output.bin',dtype='<f8',mode='r',shape=(1020,nt,2))[:,:,0]
        for condition,sign in [('light',-1),('dark',1)]:
            trace=np.memmap(base/(mode+'_'+condition)/'output.bin',dtype='<f8',mode='r',shape=(1020,nt,2))[:,:,0]
            assert np.array_equal(gray[:500],trace[:500]),(mode,condition)
            for typ,mask in masks.items():
                mean=(trace[500:,mask]-gray[500:,mask]).mean(axis=1);assert np.isfinite(mean).all()
                means[mode,condition,typ]=mean
                peak=int(np.argmax(sign*mean[:100]));initial=float(sign*mean[peak]);late=float(np.max(-sign*mean[100:500]))
                records.append({'mode':mode,'condition':condition,'cell_type':typ,'cells':416,'initial_signed_peak_mV':initial,'peak_ms':peak+1,'opposite_extremum_101_500_ms_mV':late,'opposite_to_initial_ratio':late/initial if initial>0 else None})
    comparisons=[]
    for condition,sign in [('light',-1),('dark',1)]:
        for typ in ('L1','L2'):
            b=means['blocked',condition,typ];i=means['isolated',condition,typ];diff=i-b
            comparisons.append({'condition':condition,'cell_type':typ,'max_abs_mean_difference_mV':float(abs(diff).max()),'rms_mean_difference_mV':float(np.sqrt(np.mean(diff*diff))),'isolated_biphasic':bool((sign*i[:100]).max()>0 and (-sign*i[100:500]).max()>0)})
    report={'records':records,'comparisons':comparisons,'receipts':receipts,'biological_gate_passed':False,'scope':'Model R1R6-to-R1R6 feedback isolation; single seed, uncalibrated photon scale, no genetic TNT equivalence.','interpretation':'A surviving second phase means the modeled feedback is unnecessary in this parameterization; intrinsic and direct feedforward causes remain unresolved.'}
    return report,means


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('root');args=parser.parse_args()
    report,means=run(args.root)
    o=Path(args.root)/'data/derived/visual_feedback_isolation_v1'
    (o/'full_analysis.json').write_text(json.dumps(report,indent=2))
    np.savez_compressed(o/'mean_responses.npz',**{'_'.join(key):value for key,value in means.items()})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(12,7),sharex=True,constrained_layout=True)
    t=np.arange(1,521)
    for row,typ in enumerate(('L1','L2')):
        for col,condition in enumerate(('light','dark')):
            ax=axes[row,col];b=means['blocked',condition,typ];i=means['isolated',condition,typ]
            ax.plot(t,b,color='#136f83',lw=1.8,label='R1R6→R1R6 включён')
            ax.plot(t,i,color='#d95f02',lw=1.2,ls='--',label='Вся обратная связь отключена')
            ax.axhline(0,color='#777',lw=.6);ax.axvspan(0,20,color='#aaa',alpha=.2);ax.grid(alpha=.2)
            ax.set_title(typ+' · '+('свет' if condition=='light' else 'темнота'))
            ax.set_ylabel('ΔVm к своему серому фону, мВ')
            ay=ax.twinx();ay.plot(t,i-b,color='#752774',lw=.9,alpha=.8);ay.set_ylim(-.025,.025);ay.set_ylabel('Разность режимов, мВ',color='#752774')
    axes[0,0].legend(loc='upper right',fontsize=8)
    for ax in axes[1]:ax.set_xlabel('Время после импульса, мс')
    fig.suptitle('MaleCNS-гибрид: изоляция зрительной обратной связи; один seed, биологическая проверка не пройдена',fontsize=11)
    fig.savefig(o/'isolated_flash_v1.png',dpi=160);plt.close(fig)
    print(json.dumps({'records':report['records'],'comparisons':report['comparisons']},indent=2))
