"""Summarize completed onset protocol; does not claim fit to experimental data."""
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]

def main():
    trace=ROOT/'build/phototransduction_onset.csv'
    x=np.genfromtxt(trace,delimiter=',',names=True)
    if len(x)!=20000 or not np.array_equal(x['tick'],np.arange(1,20001)):
        raise ValueError('Incomplete or nonsequential trace')
    if not all(np.isfinite(x[k]).all() for k in x.dtype.names):
        raise ValueError('Nonfinite state')
    # Tick 5000 ends at 0.5 s before onset; tick 5001 is the first illuminated interval.
    pre=x[:5000]; post=x[5000:]; tail=x[-2000:]
    pre_error=float(np.max(np.abs(pre['light_mv']-pre['dark_mv'])))
    peak_index=int(np.argmax(post['light_mv']))+5000
    peak=float(x['light_mv'][peak_index]); late=float(tail['light_mv'].mean())
    report={
        'scope':'One-seed, one-intensity model onset protocol; not biological or complete Figure 15 validation',
        'complete':True,'ticks':20000,'dt_seconds':.0001,'onset_seconds':.5,
        'light_photons_per_second':100000,'seed':19303,
        'pre_onset_max_light_dark_difference_mv':pre_error,
        'peak_light_mv':peak,'peak_time_seconds':float(x['tick'][peak_index]*.0001),
        'late_window_seconds':[1.8,2.0],'late_light_mean_mv':late,
        'late_light_std_mv':float(tail['light_mv'].std()),
        'late_dark_mean_mv':float(tail['dark_mv'].mean()),
        'peak_minus_late_mv':peak-late,
        'final_adaptation':[float(x['dark_ns'][-1]),float(x['light_ns'][-1])],
        'qualitative_checks':{'pre_onset_equal':pre_error<1e-9,
                              'light_depolarizes':late>float(tail['dark_mv'].mean()),
                              'peak_exceeds_late_mean':peak>late},
        'limitations':['no raw recording comparison','no published numeric curve error',
                       'single seed','single intensity','no steady-state proof'],
        'hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in (trace,ROOT/'build/phototransduction_safe_probe.exe',
                            ROOT/'reports/photoreceptor_protocol_source.json')},
    }
    (ROOT/'reports/photoreceptor_onset.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    import os
    os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'build/matplotlib-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,1,sharex=True,figsize=(9,6),layout='constrained')
    time=x['tick']*.0001
    axes[0].plot(time,x['dark_mv'],label='Dark: 0 photons/s')
    axes[0].plot(time,x['light_mv'],label='100,000 photons/s after 0.5 s')
    axes[0].set_ylabel('Membrane potential (mV)');axes[0].legend()
    axes[1].plot(time,x['light_ns'],label='Illuminated receptor adaptation')
    axes[1].set_ylabel('Adaptation state');axes[1].set_xlabel('Simulation time (s)')
    for ax in axes:ax.axvline(.5,color='black',linestyle=':',linewidth=.8)
    fig.suptitle('Native photon model: one seed, two receptors\nNumerical protocol; not a biological validation')
    fig.savefig(ROOT/'build/photoreceptor_onset.png',dpi=150)
    plt.close(fig)

if __name__=='__main__':main()
