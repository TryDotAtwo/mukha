"""Pipe native physical rendering to ffmpeg with blocking backpressure."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:raise RuntimeError('ffmpeg/ffprobe required')
    directory=ROOT/'data/derived/contact_diagnostic'
    export=ROOT/'reports/contact_export.json'
    for name,h in json.loads(export.read_text())['files'].items():
        if sha(directory/name)!=h:raise ValueError('Model changed')
    output=ROOT/'build/contact_diagnostic.mp4'
    env=dict(os.environ);env['PATH']=str(ROOT/'data/reference/mujoco_3.9.0/bin')+os.pathsep+env['PATH']
    exe=ROOT/'build/contact_video.exe'
    with (ROOT/'build/contact_video_native.log').open('wb') as native_log, (ROOT/'build/contact_video_encode.log').open('wb') as encoder_log:
        native=subprocess.Popen([str(exe),'data/derived/contact_diagnostic/body.xml','build/contact_video_frames.jsonl'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=native_log)
        encoder=None
        try:
            encoder=subprocess.Popen([ffmpeg,'-y','-f','rawvideo','-pixel_format','rgb24','-video_size','1920x1080',
                '-framerate','30','-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','18',
                '-pix_fmt','yuv420p','-movflags','+faststart',str(output)],stdin=native.stdout,stdout=subprocess.DEVNULL,stderr=encoder_log)
            native.stdout.close();native_code=native.wait(timeout=120);encoder_code=encoder.wait(timeout=30)
        finally:
            for process in [native,encoder]:
                if process is not None and process.poll() is None:process.kill();process.wait()
    if native_code or encoder_code:raise RuntimeError(f'native={native_code}, encoder={encoder_code}; inspect build/contact_video_* logs')
    probe=json.loads(subprocess.check_output([ffprobe,'-v','error','-show_streams','-show_format','-of','json',str(output)]))
    stream=probe['streams'][0]
    passed=stream['width']==1920 and stream['height']==1080 and stream['nb_frames']=='90' and stream['r_frame_rate']=='30/1'
    journal=ROOT/'build/contact_video_frames.jsonl'
    snapshots=[json.loads(line) for line in journal.read_text().splitlines()]
    passed &= len(snapshots)==360 and all(s['tick']==(s['frame']+1)*1000//3 and
        abs(s['time']-s['tick']*0.0001)<1e-9 and s['panel']==i%4 for i,s in enumerate(snapshots))
    report={'scope':'Native mechanical diagnostic video, no brain or rocket; actual MuJoCo poses',
        'passed':passed,'frames':stream['nb_frames'],'fps':stream['r_frame_rate'],'duration':probe['format']['duration'],
        'video_sha256':sha(output),'executable_sha256':sha(exe),'model_export_sha256':sha(export),
        'frame_state_journal_sha256':sha(journal),'frame_state_snapshots':len(snapshots),
        'native_log':(ROOT/'build/contact_video_native.log').read_text(),
        'rendering':'Native MuJoCo OpenGL offscreen; blocking RGB pipe into ffmpeg',
        'trajectory':'30000 physics ticks, frame sampling at floor((frame+1)*1000/3); no interpolation or pose controller'}
    (ROOT/'reports/contact_video.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    if not passed:raise SystemExit(1)

if __name__=='__main__':main()
