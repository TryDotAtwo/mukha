"""Measured motor activity and declared passive load, without fitting parameters."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from scipy.signal import lfilter

model = Path('data/derived/contact_diagnostic/body.xml')
root = ET.parse(model).getroot()
actuators = list(root.find('actuator'))
names = [a.get('name') for a in actuators]
body = pd.read_csv('build/brain_duration_body.csv')
events = pd.read_csv('build/brain_duration_spikes.csv')
events = events[events.enabled == 1]
mapping = Path('build/brain_body_mapping.txt').read_text().splitlines()
assert int(mapping[0]) == len(mapping) - 1 == 24
expected = np.zeros((10000, len(actuators)))
channels = []
for line in mapping[1:]:
    index, name, sign = line.split()
    index, sign = int(index), int(sign)
    ticks = events[events.graph_index == index].tick.to_numpy()
    impulses = np.bincount(ticks, minlength=10000).astype(float)
    activity = lfilter([1.], [1., -np.exp(-.0001/.020)], impulses)
    expected[:, names.index(name)] += .1 * sign * activity
    channels.append(dict(graph_index=index, actuator=name, sign=sign, spikes=len(ticks)))
expected = np.clip(expected, -1, 1)
on = body[body.enabled == 1]
actual = on.pivot(index='tick', columns='actuator', values='control').to_numpy()
np.testing.assert_allclose(actual, expected, atol=1e-12, rtol=1e-12)
joint_name = 'lf_trochanterfemur-lf_tibia-pitch'
joint = root.find(".//joint[@name='" + joint_name + "']")
k = float(joint.get('stiffness'))
ref = float(joint.get('springref'))
axis = next(i for i, a in enumerate(actuators) if a.get('joint') == joint_name)
trace = on[on.actuator == axis]
reach = json.loads(Path('reports/knee_reach_diagnostic.json').read_text())
threshold = np.abs(reach['contact_threshold_bracket_rad'])
report = dict(
    scope='Engineering actuator budget for the one-second diagnostic; not physiological muscle calibration',
    independent_filter_max_abs_error=float(np.max(np.abs(actual-expected))),
    channels=channels,
    left_front=dict(spikes=sum(c['spikes'] for c in channels if c['actuator'] == names[axis]),
        command_min=float(trace.control.min()), command_mean=float(trace.control.mean()),
        max_extension_rad=float(ref-trace.position.min()),
        spring_stiffness_model_units_per_rad=k,
        static_spring_load_at_contact_model_units=(k*threshold).tolist(),
        mean_command_over_stiffness_rad=float(abs(trace.control.mean())/k)),
    interpretation='For an isolated unit-gain joint at rest, even the observed peak command is below the spring load at the static contact threshold. This is not a dynamic impossibility proof: coupled inertia, other joints and future stimuli can change the result.',
    next_requirement='Calibrate the engineering motor/body interface against independent physiological or biomechanical data before adjusting gains or training.',
    hashes={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [model,
        Path('build/brain_duration_body.csv'), Path('build/brain_duration_spikes.csv'),
        Path('build/brain_body_mapping.txt'), Path('reports/knee_reach_diagnostic.json')]})
Path('reports/motor_budget_diagnostic.json').write_text(json.dumps(report, indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ('channels', 'hashes')}, indent=2))
