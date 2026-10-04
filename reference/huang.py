"""Research translation of Luo/Huang recurrent MB model, pinned 5d7c08a.

Derived from GPL-3.0-or-later author MATLAB code, copyright 2024 Junjie Luo,
Cheng Huang and Mark J. Schnitzer. Preserve author update order and ten fixed
iterations. Not a per-synapse spiking plasticity rule.
"""
import numpy as np
from scipy.io import loadmat

def fitted_parameters(path):
    data=loadmat(path)
    values=data['para_mu'].ravel(order='F');offset=0;result=[]
    for bounds in data['mat_lu_cell'].ravel(order='F'):
        low=bounds[:,:,0];mask=(low!=bounds[:,:,1]).ravel(order='F')
        flat=low.ravel(order='F').copy();count=int(mask.sum())
        flat[mask]=values[offset:offset+count];offset+=count
        result.append(flat.reshape(low.shape,order='F'))
    if offset!=len(values):raise ValueError('Parameter packing mismatch')
    return result


def parameters(path, valence):
    result=fitted_parameters(path)
    firing=np.array([valence]*3+[31.6,5.8,17.8])
    result[0]=((np.eye(6)-result[3].T)@firing*(2/(1+np.exp(-0.05*5))))[None,:]
    return result

def figure5d_protocol(rest):
    events=[]
    for name in ['imaging','training','rest','imaging']:
        if name=='rest':events.append((name,rest,np.zeros(2),0,0));continue
        duration,isi=(5,120) if name=='imaging' else (30,135)
        for i,(length,odor) in enumerate([(duration,[1,0]),(isi,[0,0]),(duration,[0,1]),(isi,[0,0])]):
            imaging=(1 if i==0 else 2 if i==2 else 0) if name=='imaging' else 0
            events.append((name,length,np.array(odor),int(name=='training' and i==0),imaging))
    # Explicit author modification to the first imaging session's last ISI.
    name,_,odor,pun,img=events[3];events[3]=(name,300,odor,pun,img)
    return events

def simulate(params,events):
    wpun=np.array([27.85,0,11.38,0,0,0])
    baseline=np.array([0,0,0,35.2,9.,11.2])
    maximum=np.array([71.66,17.9,31.16])
    weights0=np.vstack([params[0],params[0]])
    weights=weights0.copy();recurrent=params[3]
    fw0=float(params[1].item());fwdt=float(params[2].ravel(order='F')[0])
    tau=params[4].ravel();adapt_tau=float(params[5].item())
    delta=np.zeros((2,3));odor_start=np.ones(2);records=[]
    last_training=max(i for i,e in enumerate(events) if e[0]=='training')
    elapsed=0.
    def activation(x):return np.concatenate([x[:3],np.minimum(np.maximum(x[3:],0),maximum)])
    inverse=np.linalg.inv(np.eye(6)-recurrent)
    for i,(_,duration,odor,punishment,imaging) in enumerate(events):
        end=odor_start*np.exp(-0.05*duration*odor)
        end=1-(1-end)*np.exp(-duration/adapt_tau)
        mean=(odor_start+end)/2;odor_start=end;kc=mean*odor
        drive=weights.T@kc+wpun*punishment
        activity=inverse@drive
        for _ in range(10):activity=activation(drive+baseline+recurrent.T@activity)-baseline
        induction=fw0*duration/90*(weights[:,:3].T@kc+recurrent[3:,:3].T@activity[3:])
        induction+=fwdt*wpun[:3]*duration/90*punishment
        delta+=np.outer(kc,induction)
        if i>last_training:elapsed+=duration
        early=tau[[0,1,1]];late=tau[[0,2,2]];transition=10800
        if elapsed<=transition:delta*=np.exp(-duration/early)
        elif transition>elapsed-duration:
            first=transition-(elapsed-duration)
            delta*=np.exp(-first/early)*np.exp(-(duration-first)/late)
        else:delta*=np.exp(-duration/late)
        weights=weights0+np.concatenate([np.zeros((2,3)),delta],axis=1)
        if imaging:records.append(activity.copy())
    if not records or len(records)%2:
        raise ValueError('Expected complete CS+/CS- imaging pairs')
    return np.stack(records,axis=1).reshape(6,2,len(records)//2,order='F')


def physiological_parameters(path, odor_pair):
    """Exact column selection in the author's fitting-error wrapper."""
    result=fitted_parameters(path)
    if result[0].shape!=(1,9):
        raise ValueError('Expected original nine baseline weights')
    if odor_pair=='ACVvsETA':
        columns=[0,1,2,3,4,5]
    elif odor_pair=='OCTvsBEN':
        columns=[6,7,8,3,4,5]
    else:
        raise ValueError('Unknown author odor pair')
    result[0]=result[0][:,columns].copy()
    return result


def physiological_protocol():
    """Six imaging sessions used by the unchanged author calibration."""
    events=[];rests=iter([3600,3600*2-250,3600*21-250*2])
    sessions=['imaging','training','imaging','training','imaging',
              'rest','imaging','rest','imaging','rest','imaging']
    for name in sessions:
        if name=='rest':
            events.append((name,next(rests),np.zeros(2),0,0))
            continue
        duration,isi,repeats=(30,135,3) if name=='training' else (5,120,1)
        for repeat in range(repeats):
            for i,(length,odor) in enumerate([(duration,[1,0]),(isi,[0,0]),
                                               (duration,[0,1]),(isi,[0,0])]):
                imaging=(1 if i==0 else 2 if i==2 else 0) if name=='imaging' else 0
                events.append((name,length,np.array(odor),
                               int(name=='training' and i==0),imaging))
    return events
