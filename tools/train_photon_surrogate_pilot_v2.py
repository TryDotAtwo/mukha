"""Train a deterministic sensory GRU pilot from full VisTrans teacher traces."""
from pathlib import Path
import hashlib
import json
import time

import numpy as np
import torch
from torch import nn


class ReceptorGRU(nn.Module):
    def __init__(self, hidden=24):
        super().__init__()
        self.gru = nn.GRU(1, hidden, 1)
        self.readout = nn.Linear(hidden, 1)

    def forward(self, x, hidden=None):
        y, hidden = self.gru(x, hidden)
        return self.readout(y), hidden


def tensors(path, device):
    with np.load(path) as data:
        x = data['photons_per_s'].copy()
        y = data['voltage_mV'].copy()
    x = np.log1p(x)/np.log1p(100000.)
    y = (y + 81.9925)/100.
    return (torch.from_numpy(x[...,None].astype(np.float32)).to(device),
            torch.from_numpy(y[...,None].astype(np.float32)).to(device))


def predict(model, x):
    model.eval()
    with torch.inference_mode():
        output,_ = model(x)
        return (output[...,0]*100.-81.9925).cpu().numpy()


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from hf_artifact_archive import digest,publish
    base=root/'data/derived/photon_surrogate_teacher_v1'
    output=root/'data/derived/photon_surrogate_pilot_v2'
    output.mkdir(parents=True,exist_ok=True)
    assert not any(output.iterdir()), 'Refusing to overwrite an existing pilot'
    torch.manual_seed(93023)
    torch.backends.cudnn.deterministic=True
    torch.backends.cudnn.benchmark=False
    device=torch.device('cuda')
    x_train,y_train=tensors(base/'train.npz',device)
    x_test,y_test=tensors(base/'holdout.npz',device)
    model=ReceptorGRU(24).to(device)
    optimizer=torch.optim.Adam(model.parameters(),lr=0.003)
    history=[]
    start=time.perf_counter()
    for epoch in range(1,201):
        model.train()
        hidden=None
        losses=[]
        for begin in range(0,len(x_train),200):
            end=min(begin+200,len(x_train))
            optimizer.zero_grad(set_to_none=True)
            prediction,hidden=model(x_train[begin:end],hidden)
            loss=torch.mean((prediction-y_train[begin:end])**2)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(),1.0)
            optimizer.step()
            hidden=hidden.detach()
            losses.append(float(loss.detach()))
        if epoch in (1,20,40,60,80,100,150,200):
            pred=predict(model,x_test)
            truth=(y_test[...,0]*100.-81.9925).cpu().numpy()
            error=pred-truth
            metrics={'epoch':epoch,'train_mse_normalized':float(np.mean(losses)),
                     'holdout_rmse_mV':float(np.sqrt(np.mean(error**2))),
                     'holdout_mae_mV':float(np.mean(np.abs(error))),
                     'holdout_p95_abs_mV':float(np.quantile(np.abs(error),0.95)),
                     'elapsed_s':time.perf_counter()-start}
            history.append(metrics)
            print('SURROGATE_PILOT_EPOCH',json.dumps(metrics),flush=True)
    pred=predict(model,x_test)
    truth=(y_test[...,0]*100.-81.9925).cpu().numpy()
    np.savez_compressed(output/'holdout_predictions.npz',prediction_mV=pred.astype(np.float32),
                        teacher_mV=truth.astype(np.float32))
    torch.save({'state_dict':model.cpu().state_dict(),'hidden':24,'seed':93023},output/'model.pt')
    report={'scope':'PyTorch deterministic GRU sensory pilot fitted to full VisTrans; no CNS/landing; no noise or feedback model',
            'train_source':'data/derived/photon_surrogate_teacher_v1/train.npz',
            'holdout_source':'data/derived/photon_surrogate_teacher_v1/holdout.npz',
            'history':history,'final':history[-1],
            'biological_gate_passed':False,
            'limitations':'One held-out stimulus distribution, no endogenous feedback, no matched biology, no native implementation, deterministic output cannot preserve photoreceptor noise.'}
    report_path=output/'report.json'
    report_path.write_text(json.dumps(report,indent=2))
    files=[report_path,output/'holdout_predictions.npz',output/'model.pt',
           root/'tools/train_photon_surrogate_pilot_v2.py']
    manifest={'schema':'faithful-fly-artifacts-v1','scope':report['scope'],
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('SURROGATE_PILOT_REPORT',json.dumps(report),flush=True)
    print('SURROGATE_PILOT_ARCHIVE',json.dumps(receipt),flush=True)
    return receipt


if __name__=='__main__':
    run()
