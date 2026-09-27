"""Independent scalar oracle for an explicitly scheduled, single-edge diagnostic."""
import hashlib
import json
import math
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

def main():
    source = ROOT / 'build/phototransduction_onset.csv'
    expected = '7be854eb78c2b628d7a92dec7b9d90d6eafcb2e9a33fbe72346771a7e14a1e13'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
    csv = np.genfromtxt(source, delimiter=',', names=True)
    presynaptic = np.column_stack((csv['dark_mv'], csv['light_mv']))
    binary = ROOT / 'build/graded_photoreceptor_input.bin'
    assert np.array_equal(np.fromfile(binary, dtype='<f8').reshape(-1, 2), presynaptic)
    trace = ROOT / 'build/graded_path_trace.bin'
    gpu = np.fromfile(trace, dtype='<f8').reshape(20000, 2, 4)
    cpu = np.empty_like(gpu)
    state = [[-50., .5] for _ in range(4)]
    for tick in range(20000):
        for case in range(4):
            delay = 0 if case == 3 else 10
            pre = presynaptic[tick-delay, 0 if case == 0 else 1] if tick >= delay else -81.9925
            conductance = 0 if case == 2 else min(.032, .0008 * max(0., pre + 80))
            v, n = state[case]
            current = conductance * (-80-v)
            for _ in range(10):
                dn = .0025 * math.cosh((v+5)/20) * (.5*(1+math.tanh((v+5)/10))-n)
                dv = current-.5*(v+50)-2*n*(v+70)-1.1*.5*(1+math.tanh((v+1)/15))*(v-10)+.02
                v, n = v+.01*dv, n+.01*dn
            state[case] = [v, n]
            cpu[tick, :, case] = [v, n]
    errors = np.max(np.abs(gpu-cpu), axis=(0, 2))
    assert np.isfinite(gpu).all() and np.all(errors < 1e-9), errors
    assert np.array_equal(gpu[:, :, 0], gpu[:, :, 2]), 'Disconnected light differs from dark'
    first = [int(np.flatnonzero(gpu[:, 0, i] != gpu[:, 0, 0])[0]) for i in (1, 3)]
    assert first[0]-first[1] == 10, first
    assert np.max(np.abs(gpu[:, 0, 1]-gpu[:, 0, 0])) > .1
    paths = [source, binary, trace, ROOT/'build/graded_path_probe.exe',
             ROOT/'native/graded_path_probe.cu', ROOT/'build/morris_author.cu', Path(__file__)]
    report = dict(passed=True, scope='Single-edge engineering diagnostic; not a MaleCNS circuit or biological calibration',
        ticks=20000, dt_seconds=.0001, delay_ticks=10, membrane_substeps=10,
        schedule='End-of-photoreceptor-tick sample; delayed voltage drives current held over ten postsynaptic substeps',
        max_abs_errors_V_n=errors.tolist(), first_effect_zero_based_ticks_delayed_instant=first,
        disconnected_equals_dark=True, max_voltage_effect_mv=float(np.max(np.abs(gpu[:,0,1]-gpu[:,0,0]))),
        hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    (ROOT/'reports/graded_path_comparison.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
