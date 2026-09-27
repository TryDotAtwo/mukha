"""Check extended native run against immutable 100-ms prefix and causal inputs."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

spec = json.loads(Path('configs/brain_body_duration_pilot.json').read_text())
ticks = spec['ticks']
frames = {}
paths = []
for suffix in ('body.csv', 'spikes.csv', 'environment.csv', 'environment.csv.contacts.csv'):
    path = Path('build/brain_duration_' + suffix)
    old = pd.read_csv('build/brain_contact_' + suffix)
    new = pd.read_csv(path)
    assert np.isfinite(new.to_numpy()).all()
    pd.testing.assert_frame_equal(new[new.tick < 1000].reset_index(drop=True), old, check_exact=True)
    frames[suffix] = new
    paths.append(path)
env, body, events, contact = [frames[s] for s in ('environment.csv', 'body.csv', 'spikes.csv', 'environment.csv.contacts.csv')]
cases = []
for enabled in (0, 1):
    e = env[env.enabled == enabled]
    c = contact[contact.enabled == enabled]
    b = body[body.enabled == enabled]
    assert len(e) == len(c) == ticks and len(b) == 42 * ticks
    np.testing.assert_array_equal(e.tick, np.arange(ticks))
    np.testing.assert_array_equal(c.tick, np.arange(ticks))
    np.testing.assert_allclose(e.time, (e.tick + 1) * .0001, atol=1e-12, rtol=0)
    np.testing.assert_array_equal(e.q_start_mm.to_numpy()[1:], e.q_end_mm.to_numpy()[:-1])
    np.testing.assert_array_equal(e.throttle, np.clip(e.q_start_mm / .3, 0, 1))
    np.testing.assert_allclose(e.effective_g_mm_s2,
        -1000 * np.r_[0, e.thrust_n.to_numpy()[:-1]] / (1000 + np.r_[100, e.fuel_kg.to_numpy()[:-1]]), rtol=1e-14, atol=1e-14)
    if not enabled:
        assert (b.control == 0).all()
    cases.append(dict(motor_enabled=bool(enabled),
        neural_spikes=int((events.enabled == enabled).sum()),
        steps_with_pad_contact=int((c.pad_contacts > 0).sum()),
        maximum_pad_normal_force_model_units=float(c.normal_force_model_units.max()),
        maximum_abs_slider_displacement_mm=float(e.q_end_mm.abs().max()),
        maximum_throttle=float(e.throttle.max()), maximum_thrust_n=float(e.thrust_n.max())))
np.testing.assert_array_equal(events[events.enabled == 0][['tick', 'graph_index']],
                              events[events.enabled == 1][['tick', 'graph_index']])
report = dict(scope=spec['scope'], simulation_seconds=ticks*.0001,
    original_100ms_prefix_exact=True, clock_and_slider_command_checks=True,
    sensory_feedback=False, learning=False, cases=cases,
    hashes={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths + [
        Path('configs/brain_body_duration_pilot.json'), Path('build/brain_body_probe.exe')]})
Path('reports/brain_body_duration_pilot.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
