"""Independent numerical review of the retrieved factor archive; no runner imports.

Reads archive bytes directly. Not a manifest/transport auditor or an experiment
runner. Piecewise-linear segment antiderivatives and Boolean-cube differences
provide independent numerical oracles on the frozen eight processed means.
"""
import argparse
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import tarfile

import numpy as np
from scipy.io import loadmat

PLAN_HASH = '263d6f4a55f4277f5804f7a4e8d2c07e8757f839e3935c27b0b60d47b334e099'
ARCHIVE_HASH = 'af79f4143614bb275c84605b8627b4faf28301cad61aad4d8f4c20425c8cd444'


def review(path):
    blob = Path(path).read_bytes()
    if hashlib.sha256(blob).hexdigest() != ARCHIVE_HASH:
        raise ValueError('not the retrieved window-factor-002 archive')
    with tarfile.open(fileobj=io.BytesIO(blob), mode='r:gz') as archive:
        files = {m.name: archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}
    def read(suffix):
        found = [v for k, v in files.items() if k.endswith('/'+suffix) or k == suffix]
        if len(found) != 1:
            raise ValueError('ambiguous archive member '+suffix)
        return found[0]
    # Exact result path avoids matching reference/result.json.
    roots = [k[:-len('plan.json')] for k in files if k.endswith('plan.json')]
    if len(roots) != 1:
        raise ValueError('ambiguous root')
    root = roots[0]
    plan_bytes = files[root+'plan.json']
    if hashlib.sha256(plan_bytes).hexdigest() != PLAN_HASH:
        raise ValueError('plan drift')
    plan = json.loads(plan_bytes)
    result = json.loads(files[root+'result.json'])
    ref_bytes = files[root+'reference/result.json']
    if hashlib.sha256(ref_bytes).hexdigest() != plan['reference_result_sha256']:
        raise ValueError('reference drift')
    reference = json.loads(ref_bytes)
    counts, maxima = {}, {}
    def eq(actual, expected, label):
        if actual != expected or isinstance(actual, bool) != isinstance(expected, bool):
            raise ValueError(f'{label}: {actual!r} != {expected!r}')
    def near(actual, expected, label, ratio=False):
        group = 'ratio_or_contrast' if ratio else 'area_or_clock'
        if type(actual) not in (int, float) or not math.isfinite(actual):
            raise ValueError(label+': nonfinite/non-numeric')
        error = abs(actual-expected)
        if error > (1e-10 if ratio else 1e-14)+1e-10*abs(expected):
            raise ValueError(f'{label}: {actual} != {expected}')
        counts[group] = counts.get(group, 0)+1
        maxima[group] = max(maxima.get(group, 0), error)
    eq(result['status'], 'ok', 'result status')
    expected_keys = {(f, r, c) for f in plan['input_mat_sha256'] for r in (0, 1) for c in plan['conditions']}
    records = {(x['file'], x['row'], x['condition']): x for x in result['records']}
    eq(len(result['records']), 64, 'record count')
    eq(set(records), expected_keys, 'record keys')
    curves = {(x['file'], x['row']): x for x in result['curves']}
    eq(len(result['curves']), 8, 'curve count')
    eq(set(curves), {(f,r) for f in plan['input_mat_sha256'] for r in (0,1)}, 'curve keys')
    observations = []
    for (name, row), curve in curves.items():
        data = files[root+'reference/inputs/'+name]
        eq(hashlib.sha256(data).hexdigest(), plan['input_mat_sha256'][name], 'MAT digest')
        mat = loadmat(io.BytesIO(data))
        t, y = mat['t'].ravel(), mat['meanResp'][row]
        eq(len(t), 63, 'sample count')
        if not np.isfinite(t).all() or not np.isfinite(y).all() or not (np.diff(t)>0).all():
            raise ValueError('invalid grid')
        sign = (-1, 1)[row]
        peak = max(range(2,31), key=lambda i: sign*y[i])
        derivative = np.diff(np.r_[0.,y])
        candidates = np.flatnonzero(sign*(.9*derivative[1:peak+2]-derivative[:peak+1]) > 0)
        first = int(candidates[0]) if len(candidates) else 1
        j = next(i for i in range(peak,63) if sign*y[i] <= 0)
        dt = float(np.median(np.diff(t)))
        end_h = max(i for i in range(63) if t[i] <= t[2]+.25)
        end_s = math.floor(.25/dt)-1
        eq(next(i for i in range(peak+1,end_h+1) if sign*y[i]<=0), j, 'crossing bracket')
        z = float((t[j-1]*abs(y[j])+t[j]*abs(y[j-1]))/(abs(y[j-1])+abs(y[j])))
        levels = [{'H':float(t[2]),'S':float(t[first])},
                  {'H':float(t[end_h]),'S':float(t[end_s])}, {'H':z,'S':float(t[j])}]
        for field, value in {'peak_index':peak, 'polarity':sign, 'start_indices':{'H':2,'S':first},
                             'end_indices':{'H':end_h,'S':end_s}, 'bracket_indices':[j-1,j],
                             'source_frame_zero1':first+1,'source_frame_zero2':j+1}.items():
            eq(curve[field], value, name+str(row)+field)
        eq(curve['status'], 'ok', 'curve status')
        near(curve['peak_time'], float(t[peak]), 'peak time')
        near(curve['ifi_seconds'], dt, 'ifi')
        near(curve['clock_deviation'], float(max(abs(t-(t[0]+np.arange(63)*dt)))), 'clock deviation')
        eq(curve['steps'], np.diff(t).tolist(), 'steps')
        for a in range(3):
            for level in 'HS':
                near(curve['levels'][a][level], levels[a][level], 'frozen level')
        def area(lo, hi):
            # Integrate each clipped original segment analytically; fsum avoids
            # relying on runner knot concatenation/interpolation/sum ordering.
            parts = []
            for i in range(62):
                left, right = max(lo,float(t[i])), min(hi,float(t[i+1]))
                if right > left:
                    slope = float((y[i+1]-y[i])/(t[i+1]-t[i]))
                    parts.append(float(y[i])*(right-left)+slope*((right-t[i])**2-(left-t[i])**2)/2)
            return math.fsum(parts)
        values = {}
        for condition in plan['conditions']:
            actual = records[name,row,condition]
            o,e,c = (levels[a][condition[a]] for a in range(3))
            if not t[0] <= o <= t[peak] <= c <= e <= t[-1]:
                raise ValueError('invalid expected interval')
            a1,a2 = area(o,c),area(c,e)
            expected = dict(A1=a1,A2=a2,total=a1+a2,direct_total=area(o,e),
                            denominator_magnitude=abs(a1),raw_ratio=a2/a1,Q=-a2/a1,
                            start=o,end=e,split=c)
            eq(actual['status'],'ok','cell status')
            eq(actual['input_sha256'],plan['input_mat_sha256'][name],'cell input')
            for metric,v in expected.items():
                near(actual[metric],v,condition+':'+metric,metric in ('Q','raw_ratio'))
            near(actual['conservation']['residual'], actual['total']-actual['direct_total'], 'conservation residual')
            near(actual['total'],actual['direct_total'],'conservation')
            eq(actual['conservation']['passed'], True, 'conservation flag')
            values[condition] = expected
        archived = next(x for x in reference['rows'] if x['file']==name and x['row']==row)
        for condition,corner in [('HHH',[archived['historical_area1_df_f_seconds'],archived['historical_area2_df_f_seconds'],archived['historical_negative_signed_ratio']]),
                                 ('SSS',[archived['sampled']['area1_percent_df_f_seconds']/100,archived['sampled']['area2_percent_df_f_seconds']/100,archived['sampled_negative_signed_ratio']])]:
            for metric, target in zip(('A1','A2','Q'),corner):
                near(values[condition][metric],target,'archived corner '+metric,metric=='Q')
                closure = curve['corner_closure'][condition][metric]
                near(closure['residual'],records[name,row,condition][metric]-target,'closure residual',metric=='Q')
                eq(closure['passed'],True,'closure flag')
        for metric in ('A1','A2','total','Q'):
            exported = curve['contrasts'][metric]
            eq(exported['status'],'ok','contrast status')
            base_terms=[]
            for axes_mask in range(1,8):
                axes=[a for a in range(3) if axes_mask & (1<<a)]
                others=[a for a in range(3) if a not in axes]
                term=''.join('OEC'[a] for a in axes)
                conditional={}
                for fixed in itertools.product('HS',repeat=len(others)):
                    selected=[]
                    for key in values:
                        if all(key[a]==v for a,v in zip(others,fixed)):
                            selected.append((-1)**sum(key[a]=='H' for a in axes)*values[key][metric])
                    conditional[''.join(fixed) or 'none']=math.fsum(selected)
                out=exported['terms'][term]
                eq(set(out['conditional']),set(conditional),'conditional keys')
                for key,v in conditional.items():
                    near(out['conditional'][key],v,metric+term+key,metric=='Q')
                baseline=conditional.get('H'*len(others) or 'none')
                near(out['baseline'],baseline,'baseline '+metric+term,metric=='Q')
                near(out['averaged'],math.fsum(conditional.values())/len(conditional),'average '+metric+term,metric=='Q')
                base_terms.append(baseline)
            delta=values['SSS'][metric]-values['HHH'][metric]
            near(exported['full_change'],delta,'full change',metric=='Q')
            near(exported['baseline_expansion_residual'],delta-math.fsum(base_terms),'expansion',metric=='Q')
        for axis in range(3):
            for key in values:
                if key[axis]!='H':
                    continue
                other=key[:axis]+'S'+key[axis+1:]
                a,b=values[key],values[other]
                lhs,rhs=(b['A2'],a['A2']) if axis==0 else (b['A1'],a['A1']) if axis==1 else (b['A1']-a['A1'],-(b['A2']-a['A2']))
                near(lhs,rhs,'factor isolation')
        observations.append(dict(file=name,row=row,start_indices=[2,first],end_indices=[end_h,end_s],
                                 bracket=[j-1,j],HHH_Q=values['HHH']['Q'],SSS_Q=values['SSS']['Q'],
                                 delta_Q=values['SSS']['Q']-values['HHH']['Q'],
                                 minimum_abs_A1=min(v['denominator_magnitude'] for v in values.values())))
    return dict(verdict='NUMERICAL APPROVE',archive_sha256=ARCHIVE_HASH,archive_bytes=len(blob),
                runner_commit='f61ef73c869a0d54170b3e4212c1a5605dc4af4b',
                plan_sha256=PLAN_HASH,curves_checked=8,records_checked=64,comparisons=counts,
                max_absolute_errors=maxima,observations=observations,
                method='No runner/helper imports; clipped segment antiderivatives with math.fsum; independently derived indices and cube signed sums',
                limitations=['Eight fixed processed means only; no biological gate closure, animal/ROI uncertainty, calibration or causal shares',
                             'Manifest/transport/identity review belongs to Astra3; numerical review does not establish remote execution',
                             'No Molab request or repeat of measurement001'])


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path)
    args=parser.parse_args()
    print(json.dumps(review(args.archive),indent=2,allow_nan=False))
