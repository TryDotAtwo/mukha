"""Numerical branch checks; these are not additional biological validation."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'reference'))
from huang import parameters,figure5d_protocol,simulate
from huang_native import simulate as native_simulate

def main():
    source=ROOT/'data/reference/huang_2024/data_and_parameters/Dx_steady_state_nonlinear_3_27-Mar-2023_3modules.mat'
    records=[]
    for valence in [-4,0,4]:
        p=parameters(source,valence)
        # Includes transitions during rest and within a subsequent imaging bout.
        for rest in [10794,10799,10800,10801,10920,21600,86400]:
            events=figure5d_protocol(rest)
            reference=simulate(p,events);native=native_simulate(p,events)
            error=float(np.max(np.abs(reference-native)))
            records.append({'valence':valence,'rest_seconds':rest,'max_absolute_error':error})
    report={'scope':'Native versus NumPy equation/decay branch checks; no independent biological outcome data',
        'cases':records,'passed':all(r['max_absolute_error']<1e-8 for r in records),
        'library_sha256':hashlib.sha256((ROOT/'build/huang_reference.dll').read_bytes()).hexdigest(),
        'parameter_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'full_cns_plasticity_validated':False}
    (ROOT/'reports/huang_decay_branch_checks.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'cases':len(records),'max_absolute_error':max(r['max_absolute_error'] for r in records),'passed':report['passed']}))
    if not report['passed']:raise SystemExit(1)

if __name__=='__main__':main()
