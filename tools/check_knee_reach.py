"""Compare static reach with observed neural motion; no geometry or gain fitting."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd

xml = Path('data/derived/contact_diagnostic/body.xml')
root = ET.parse(xml).getroot()
joint = 'lf_trochanterfemur-lf_tibia-pitch'
actuators = list(root.find('actuator'))
ids = [i for i, a in enumerate(actuators) if a.get('joint') == joint]
assert len(ids) == 1
sweep = pd.read_csv('build/knee_reach.csv')
assert len(sweep) == 401 and np.isfinite(sweep.to_numpy()).all()
neutral = sweep.iloc[np.argmin(np.abs(sweep.delta_rad))]
assert abs(neutral.delta_rad) < 1e-15
assert abs(neutral.distance_mm - .01) < 1e-7
touch = sweep[sweep.contacts > 0]
assert len(touch) > 0
nearest = touch.iloc[np.argmin(np.abs(touch.delta_rad))]
assert nearest.delta_rad < 0
previous = sweep.iloc[np.argmin(np.abs(sweep.delta_rad - (nearest.delta_rad + .001)))]
assert previous.contacts == 0 and previous.distance_mm > 0
body = pd.read_csv('build/brain_contact_body.csv')
observed = body[(body.enabled == 1) & (body.actuator == ids[0])].position - neutral.angle_rad
assert len(observed) == 1000
report = dict(
    scope='Static one-joint reach with other joints at neutral; not dynamic or biological validation',
    initial_surface_gap_mm=float(neutral.distance_mm),
    contact_threshold_bracket_rad=[float(nearest.delta_rad), float(previous.delta_rad)],
    observed_neural_knee_delta_range_rad=[float(observed.min()), float(observed.max())],
    static_contact_within_sampled_joint_range=True,
    geometry_changed=False, gains_changed=False,
    limitation='Passive joint deflection and dynamics are absent from static sweep. Neural diagnostic lasts only 100 ms.',
    hashes={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [xml,
        Path('build/knee_reach.csv'), Path('build/brain_contact_body.csv'),
        Path('native/knee_reach_probe.cpp')]})
Path('reports/knee_reach_diagnostic.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
