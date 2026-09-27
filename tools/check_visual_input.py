"""Verify the executed image fixture, full-state replay and source identities."""
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parents[1]
def sha(data): return hashlib.sha256(data).hexdigest()
source=(ROOT/'configs/visual_input_fixture.json').read_bytes()
fixture=json.loads(source)
report=json.loads((ROOT/'reports/visual_input_fixture.json').read_text())
resumed=json.loads((ROOT/'reports/visual_input_resumed.json').read_text())
assert report['passed'] and report['full_state_continuation_exact']
assert report['input_sha256']==resumed['input_sha256']==sha(source)
assert report['optics']==fixture['optics']
config=fixture['optics']
assert config['width']==8 and config['height']==4
assert config['rays']==[[1.,0.,0.],[-1.,0.,0.]]
assert config['rgb_to_photons']==[[100000.,0.,0.],[100000.,0.,0.]]
ordered={key:config[key] for key in ('width','height','rays','rgb_to_photons','assumption_note')}
fingerprint=hashlib.sha256(json.dumps(ordered,separators=(',',':'),ensure_ascii=False).encode())
fingerprint.update(report['native_photon_build_identity'].encode())
paths=['src/visual_input.rs','src/vision.rs','src/photon.rs','native/retina.cpp','native/retina.h']
for path in paths: fingerprint.update((ROOT/path).read_bytes())
assert fingerprint.hexdigest()==report['configuration_identity']==resumed['configuration_identity']
build=json.loads((ROOT/'reports/photon_build.json').read_text())
assert build['build_identity']==report['native_photon_build_identity']
assert build['binary_sha256']==sha((ROOT/'build/fly_photon.dll').read_bytes())
assert len(report['frames'])==len(fixture['frames'])==4
expected_rates=[[0.,0.],[100000.,0.],[0.,100000.],[0.,0.]]
tick=0
for i,(image,frame,rates) in enumerate(zip(fixture['frames'],report['frames'],expected_rates)):
    tick+=image['ticks']
    assert frame['frame']==i+1 and frame['tick']==tick
    assert frame['rgb_f32le_sha256']==sha(struct.pack('<'+'f'*len(image['rgb']),*image['rgb']))
    state=frame['state_soa']
    assert len(state)==18 and all(map(math.isfinite,state))
    assert all(0<=x<=1 for x in state[2:12])
    assert state[14:16]==rates
assert report['frames'][0]['state_soa'][0]==report['frames'][0]['state_soa'][1]
assert report['frames'][1]['state_soa'][0]>report['frames'][1]['state_soa'][1]+1
assert report['frames'][2]['state_soa'][1]>report['frames'][2]['state_soa'][0]+1
assert resumed['tick']==tick==2600 and resumed['final_frame']==4 and resumed['restored_frame']==2
assert resumed['state_soa']==report['frames'][-1]['state_soa']
assert resumed['final_snapshot_sha256']==report['final_snapshot_sha256']
filename=report['checkpoint_file'];assert Path(filename).name==filename
checkpoint=(ROOT/'reports'/filename).read_bytes()
assert sha(checkpoint)==report['checkpoint_sha256']
assert checkpoint[:8]==b'FFVIS001' and struct.unpack_from('<Q',checkpoint,8)[0]==1
assert checkpoint[16:48].hex()==report['configuration_identity']
assert struct.unpack_from('<Q',checkpoint,48)[0]==report['checkpoint_frame']==2
assert struct.unpack_from('<Q',checkpoint,56)[0]==len(checkpoint)-96
assert checkpoint[64:96].hex()==sha(checkpoint[:64]+checkpoint[96:])
assert struct.unpack_from('<Q',checkpoint,96+64)[0]==1100
result={'passed':True,'scope':'Native two-ray image fixture with explicit engineering RGB coefficients; no MaleCNS mapping, biological calibration, brain or body control',
        'recorded_image_hashes_verified':True,'analytic_photon_rates_exact':True,
        'front_back_light_reactions_verified':True,'fresh_process_full_state_continuation_exact':True,
        'configuration_and_source_identity_verified':True,
        'input_sha256':sha(source),'checkpoint_sha256':sha(checkpoint),
        'final_snapshot_sha256':report['final_snapshot_sha256'],
        'executable_sha256':sha((ROOT/'target/debug/faithful-fly.exe').read_bytes()),
        'native_library_sha256':build['binary_sha256'],
        'source_hashes':{path:sha((ROOT/path).read_bytes()) for path in paths}}
(ROOT/'reports/visual_input_verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
