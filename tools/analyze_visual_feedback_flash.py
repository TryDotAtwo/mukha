"""Analyze all six verified Molab flash conditions, without a biological-pass claim."""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hf_artifact_archive import digest, validate_manifest


def analyze(root):
    from huggingface_hub import HfApi
    r = Path(root)
    base = r / 'data/derived/visual_feedback_flash_v1'
    receipts = {}
    for mode in ('intact', 'blocked'):
        for condition in ('gray', 'light', 'dark'):
            key = mode + '_' + condition
            receipt = json.loads((r / 'reports' / ('flash_v1_' + key + '_receipt.json')).read_text())
            p = Path(HfApi().hf_hub_download(receipt['repo_id'], receipt['manifest'], repo_type='dataset', revision=receipt['revision']))
            assert digest(p) == receipt['sha256']
            validate_manifest(r, json.loads(p.read_text()))
            receipts[key] = receipt
    with (r/'data/derived/lamina_native_photon_v1/graph.bin').open('rb') as f:
        n, m, nr, nt = map(int, np.fromfile(f, '<u4', 4))
        pre = np.fromfile(f, '<u4', m)
        post = np.fromfile(f, '<u4', m)
        f.seek(8*m, 1)
        ri = np.fromfile(f, '<u4', nr)
        ti = np.fromfile(f, '<u4', nt)
    with (r/'data/derived/image_lamina_probe_v1/rays.bin').open('rb') as f:
        count = int(np.fromfile(f, '<u4', 1)[0])
        mapped = np.fromfile(f, '<u4', count)
    exposed = np.unique(post[np.isin(pre, mapped)])
    nodes = pd.read_feather(r/'data/derived/malecns_v1_candidates/nodes.feather').set_index('compact_index')
    types = nodes.loc[ti, 'type'].to_numpy()
    masks = {t: np.flatnonzero((types == t) & np.isin(ti, exposed)) for t in ('L1', 'L2')}
    assert all(len(v) == 416 for v in masks.values())
    records, arrays = [], {}
    for mode in ('intact', 'blocked'):
        gray = np.memmap(base/(mode+'_gray')/'output.bin', dtype='<f8', mode='r', shape=(1020, nt, 2))[:, :, 0]
        for condition, sign in [('light', -1), ('dark', 1)]:
            trace = np.memmap(base/(mode+'_'+condition)/'output.bin', dtype='<f8', mode='r', shape=(1020, nt, 2))[:, :, 0]
            assert np.array_equal(trace[:500], gray[:500]), 'Preflash control mismatch'
            for typ, mask in masks.items():
                response = trace[500:, mask] - gray[500:, mask]
                mean = response.mean(axis=1)
                assert np.isfinite(mean).all()
                key = mode+'_'+condition+'_'+typ
                arrays[key] = mean
                peak = int(np.argmax(sign*mean[:100]))
                initial = float(sign*mean[peak])
                opposite = float(np.max(-sign*mean[100:500]))
                records.append(dict(mode=mode, condition=condition, cell_type=typ, cells=len(mask), initial_signed_peak_mV=initial, peak_ms=peak+1, opposite_extremum_101_500_ms_mV=opposite, opposite_to_initial_ratio=opposite/initial if initial>0 else None))
    report = dict(records=records, inputs=receipts, biological_gate_passed=False, scope='Paired model intervention with matched gray subtraction; single photon seed; fixed diagnostic windows; no fluorescence calibration or genetic equivalence', windows_ms=dict(initial=[1,100], opposite=[101,500]))
    return report, arrays


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('root')
    args = parser.parse_args()
    report, arrays = analyze(args.root)
    output = Path(args.root)/'data/derived/visual_feedback_flash_analysis_v1'
    output.mkdir(exist_ok=False)
    (output/'report.json').write_text(json.dumps(report, indent=2))
    np.savez_compressed(output/'mean_responses.npz', **arrays)
    print(json.dumps(report['records'], indent=2))
