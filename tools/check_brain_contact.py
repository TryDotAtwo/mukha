"""Read-only contact instrumentation must preserve every original trajectory."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import xml.etree.ElementTree as ET

xml = Path('data/derived/contact_diagnostic/body.xml')
root = ET.parse(xml).getroot()
assert root.find('option').get('integrator', 'Euler') == 'Euler'
hashes = {}
for suffix in ('body', 'spikes', 'environment'):
    old = Path(f'build/brain_rocket_{suffix}.csv')
    new = Path(f'build/brain_contact_{suffix}.csv')
    assert old.read_bytes() == new.read_bytes(), suffix
    hashes[str(new)] = hashlib.sha256(new.read_bytes()).hexdigest()
path = Path('build/brain_contact_environment.csv.contacts.csv')
data = pd.read_csv(path)
assert len(data) == 2000 and np.isfinite(data.to_numpy()).all()
cases = []
for enabled in (0, 1):
    frame = data[data.enabled == enabled]
    np.testing.assert_array_equal(frame.tick, np.arange(1000))
    np.testing.assert_allclose(frame.geometry_time, frame.tick * .0001, atol=1e-15)
    xyz = frame[['foot_x', 'foot_y', 'foot_z']].to_numpy()
    cases.append(dict(motor_enabled=bool(enabled),
        steps_with_pad_contacts=int((frame.pad_contacts > 0).sum()),
        maximum_normal_force_model_units=float(frame.normal_force_model_units.max()),
        foot_geom_center_initial_mm=xyz[0].tolist(),
        foot_geom_center_final_mm=xyz[-1].tolist(),
        foot_geom_center_axis_excursion_mm=np.ptp(xyz, axis=0).tolist()))
hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
hashes[str(xml)] = hashlib.sha256(xml.read_bytes()).hexdigest()
report = dict(scope='100 ms diagnostic, not learned or biologically validated control',
    original_trajectories_byte_identical=True,
    geometry_timestamp='Euler start-of-step; positions are geom centers, not surface distances',
    contact_pairs=[p.attrib for p in root.find('contact')], cases=cases, hashes=hashes)
Path('reports/brain_contact_diagnostic.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
