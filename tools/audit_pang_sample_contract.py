"""Source-derived Pang sample boundaries on synthetic traces, not MATLAB replay."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = '7fa5829e37d566e02beaaa87efd6a0f1de4e48c0'
SOURCES = {
    'computeFrameZero1.m': '6ec2fd08c4324e36a337f1c6a3f49ebd024d6bd6',
    'computeFrameZero2.m': '5c4edb0ebc108f65b7745382fffd696c301e8324',
    'compute_bootstrappedMetrics.m': '6d59a6ee4bc0ce6ac39f3e122bb972e19ccb7422',
}


def boundaries(trace, peak_frame, contrast):
    """Return author-style ONE-based boundaries. Peak selection is supplied.

    Missing zero2 maps MATLAB [] to None. A last-frame peak is excluded here:
    zero1's loop may access diffTrace(framePeak+1) beyond the source array.
    Domain validation is this wrapper's policy, not author error handling.
    """
    if (len(trace) < 2 or any(not math.isfinite(x) for x in trace)
            or type(peak_frame) is not int or not 1 <= peak_frame < len(trace)
            or contrast not in (1, 2)):
        raise ValueError('finite trace, interior one-based peak, contrast 1/2 required')
    diff = [trace[0]] + [b-a for a, b in zip(trace, trace[1:])]
    first = 2
    for i in range(peak_frame):
        rhs = diff[i] + .1 * diff[i+1]
        if (contrast == 1 and diff[i+1] < rhs) or (contrast == 2 and diff[i+1] > rhs):
            first = i+1
            break
    second = next((i+1 for i in range(peak_frame-1, len(trace))
                   if (contrast == 1 and trace[i] >= 0)
                   or (contrast == 2 and trace[i] <= 0)), None)
    return first, second


def sampled_areas(trace, peak_frame, contrast, ifi):
    """Port only area expressions, on an explicit valid-window subset.

    Unlike the bootstrap script, this function receives ifi rather than taking
    median(diff(t)). It does not select peaks, infer onset or resample ROIs.
    """
    first, second = boundaries(trace, peak_frame, contrast)
    if not math.isfinite(ifi) or ifi <= 0:
        raise ValueError('positive finite ifi required')
    end = math.floor(.25 / ifi)
    if second is None or not 1 <= first <= second <= end <= len(trace):
        raise ValueError('missing crossing or unsupported author integration window')

    def trapz(start, stop):
        # MATLAB inclusive one-based slice, unit spacing, then %dF/F and ifi.
        values = trace[start-1:stop]
        return sum((a+b)/2 for a, b in zip(values, values[1:])) * 100 * ifi

    a1, a2 = trapz(first, second), trapz(second, end)
    return {'frame_zero1': first, 'frame_zero2': second, 'end_phase2': end,
            'area1_percent_df_f_seconds': a1, 'area2_percent_df_f_seconds': a2,
            'signed_area_ratio': a2/a1 if a1 != 0 else None}


def source_receipts(source_dir):
    receipts = []
    for name, expected in SOURCES.items():
        content = (source_dir / name).read_bytes()
        blob = hashlib.sha1(f'blob {len(content)}\0'.encode()+content).hexdigest()
        if blob != expected:
            raise ValueError(f'{name}: source Git blob mismatch')
        receipts.append({'name': name, 'git_blob': blob,
                         'sha256': hashlib.sha256(content).hexdigest()})
    return receipts


def report(source_dir):
    traces = {
        'opposite_tail': ([0., 1., 3., 1., -1., -1., 2.], .04),
        'returning_first_polarity': ([0., 1., 3., 1., -1., -1., 4., 4.], .03125),
    }
    return {
        'source_commit': COMMIT, 'source_receipts': source_receipts(source_dir),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'scope': 'Synthetic source-derived sample and signed-area arithmetic; no MATLAB execution',
        'fixtures': {name: {'trace': y, 'ifi_seconds': ifi, 'peak_frame': 3,
                            'contrast': 2, 'result': sampled_areas(y, 3, 2, ifi)}
                     for name, (y, ifi) in traces.items()},
        'interpretation': [
            'zero2 includes exact-zero samples and selects a sample, not an interpolated crossing',
            'area1 includes the first opposite-sign sample; a geometric zero split changes areas',
            'endPhase2 is floor(.25/ifi) as a one-based index, not a timestamp search',
            'signed tail can share phase1 sign after recrossing; cancellation is author behavior',
        ],
        'limitations': [
            'Peak supplied: computeFramePeaks and bootstrap ROI sampling are not implemented',
            'No recording-specific stimulus/photodiode metadata or observation calibration',
            'Wrapper rejects missing crossings/out-of-range windows; not author error semantics',
            'Zero first area is represented as null ratio, not MATLAB Inf/NaN',
            'No processed biological curves scored; gate B remains open',
        ],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, default=ROOT/'data/reference/pang_sample_contract')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    text = json.dumps(report(args.source_dir), indent=2) + '\n'
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end='')
