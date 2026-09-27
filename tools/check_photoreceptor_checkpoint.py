"""Test same-instance in-memory continuation of the entity-RNG photon model."""
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np

ROOT=Path(__file__).resolve().parents[1]

def main():
    executable=ROOT/'build/phototransduction_checkpoint_probe.exe'
    trace=ROOT/'build/phototransduction_checkpoint.csv'
    with trace.open('w') as output:
        result=subprocess.run([str(executable),'1000'],stdout=output,stderr=subprocess.PIPE,
                              text=True,timeout=120,check=True)
    if 'Checkpoint continuation exact:' not in result.stderr:
        raise ValueError('Native comparison did not finish')
    data=np.genfromtxt(trace,delimiter=',',names=True)
    if len(data)!=1500:
        raise ValueError('Wrong trajectory length')
    if not np.array_equal(data['tick'][:1000],np.arange(1,1001)):
        raise ValueError('First trajectory clock mismatch')
    for name in data.dtype.names:
        if not np.array_equal(data[name][500:1000],data[name][1000:]):
            raise ValueError('Post-restore trajectory mismatch: '+name)
    report={'scope':'Same-instance trusted in-memory snapshot at tick 500; replay to tick 1000',
            'passed':True,'native_result':result.stderr.strip(),
            'compared':['packed molecular states','voltage and all membrane gates',
                        'adaptation','photon input','XORWOW states','feedback current',
                        'every recorded voltage/adaptation value after restore'],
            'not_covered':['portable checkpoint file','new process/device restoration',
                           'untrusted state validation','other seeds/intensities'],
            'hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in [executable,trace,ROOT/'native/phototransduction_probe.cu']}}
    (ROOT/'reports/photoreceptor_checkpoint.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
