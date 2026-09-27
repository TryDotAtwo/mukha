"""Verify contact causality and feedback in the rocket-cabin gap sweep."""
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/native_cabin_gap_verification.json'
GAPS = ((0., 'native_cabin_loop_local.json', 'native_cabin_loop_v1'),
        (.05, 'native_cabin_gap_50um_local.json', 'native_cabin_gap_50um_v1'),
        (.1, 'native_cabin_gap_100um_local.json', 'native_cabin_gap_100um_v1'),
        (.2, 'native_cabin_gap_200um_local.json', 'native_cabin_gap_200um_v1'))

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def first(values):
    indices = np.flatnonzero(values)
    return int(indices[0]) if len(indices) else None

def main():
    summaries = []
    for gap, filename, folder in GAPS:
        source = ROOT / 'reports' / filename
        report = json.loads(source.read_text(encoding='utf-8'))
        path = ROOT / 'data/derived' / folder / 'traces.npz'
        assert sha(path) == report['traces_sha256']
        assert report['pad_shift_mm'] == gap
        assert sha(ROOT / 'build/rocket_vertical_abi.dll') == report['rocket_abi_sha256']
        with np.load(path) as trace:
            base = 'feedback_1_contact_1_pulse_'
            nopulse, active = base+'0_', base+'1_'
            no_contact = 'feedback_1_contact_0_pulse_1_'
            assert np.all(trace[no_contact+'slide'] == 0)
            assert np.all(trace[no_contact+'throttle'] == 0)
            assert np.all(trace[nopulse+'slide'] == 0) if gap else True
            assert np.array_equal(trace[no_contact+'altitude'],
                                  trace['feedback_1_contact_0_pulse_0_altitude'])
            contacts = trace[active+'contacts']
            slide = trace[active+'slide']
            throttle = trace[active+'throttle']
            assert np.max(np.abs(throttle[1:] - np.clip(slide[:-1]/.3, 0, 1))) < 1e-15
            event = {'pad_shift_mm': gap, 'active_first_contact_tick': first(contacts),
                     'active_first_slide_tick': first(slide),
                     'active_first_throttle_tick': first(throttle),
                     'no_pulse_first_contact_tick': first(trace[nopulse+'contacts']),
                     'active_peak_slide_mm': float(slide.max()),
                     'no_pulse_peak_slide_mm': float(trace[nopulse+'slide'].max()),
                     'active_final_altitude_m': float(trace[active+'altitude'][-1]),
                     'ballistic_final_altitude_m': report['ballistic_final_altitude_m']}
            if gap == .05:
                assert event['no_pulse_first_contact_tick'] is None
                assert event['active_first_contact_tick'] == event['active_first_slide_tick'] == 255
                assert event['active_first_throttle_tick'] == 256
                open_slide = trace['feedback_0_contact_1_pulse_1_slide']
                open_alt = trace['feedback_0_contact_1_pulse_1_altitude']
                event['first_feedback_slide_difference_tick'] = first(slide != open_slide)
                event['first_feedback_altitude_difference_tick'] = first(
                    trace[active+'altitude'] != open_alt)
                event['max_feedback_slide_difference_mm'] = float(np.max(np.abs(slide-open_slide)))
                event['max_feedback_altitude_difference_m'] = float(np.max(
                    np.abs(trace[active+'altitude']-open_alt)))
                assert event['first_feedback_slide_difference_tick'] > 256
                assert event['max_feedback_slide_difference_mm'] > 0
            summaries.append(event)
    result = {'passed': True, 'source_report_hashes': {name: sha(ROOT/'reports'/name)
              for _, name, _ in GAPS}, 'gap_sweep': summaries,
              'scope': 'Native rocket and explicit MuJoCo cabin mechanics under prescribed muscle pulse; gap is an engineering design parameter, not biological or KSP validation.'}
    REPORT.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summaries, indent=2))

if __name__ == '__main__': main()
