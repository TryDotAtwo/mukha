"""Read-only local KSP/kRPC installation preflight; no game launch or control."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_KSP=Path(r'D:\SteamLibrary\steamapps\common\Kerbal Space Program')
REPORT=ROOT/'reports/ksp_local_preflight.json'


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda:file.read(1024*1024),b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--ksp-root',type=Path,default=DEFAULT_KSP)
    args=parser.parse_args()
    ksp=args.ksp_root.resolve()
    exe=ksp/'KSP_x64.exe'
    mod=ksp/'GameData/kRPC'
    required=[exe,ksp/'buildID64.txt',mod/'KRPC.dll',mod/'KRPC.Core.dll',
              mod/'KRPC.SpaceCenter.dll',mod/'KRPC.Core.json',mod/'KRPC.SpaceCenter.json']
    if any(not path.is_file() for path in required):
        raise FileNotFoundError('incomplete KSP/kRPC local installation')
    build=(ksp/'buildID64.txt').read_text(encoding='utf-8-sig',errors='replace')
    build_id=re.search(r'build id\s*=\s*(\d+)',build)
    if not build_id:
        raise ValueError('KSP build ID not found')
    core=json.loads((mod/'KRPC.Core.json').read_text(encoding='utf-8'))['KRPC']['procedures']
    space=json.loads((mod/'KRPC.SpaceCenter.json').read_text(encoding='utf-8'))['SpaceCenter']['procedures']
    needed={
        'pause_read':'get_Paused' in core,
        'pause_write':'set_Paused' in core,
        'physics_warp_read':'get_PhysicsWarpFactor' in space,
        'physics_warp_write':'set_PhysicsWarpFactor' in space,
        'autopilot_engaged_read':'AutoPilot_get_Engaged' in space,
        'sas_read':'Control_get_SAS' in space,
        'control_state_read':'Control_get_State' in space,
        'control_source_read':'Control_get_Source' in space,
        'throttle_read':'Control_get_Throttle' in space,
        'pitch_read':'Control_get_Pitch' in space,
        'yaw_read':'Control_get_Yaw' in space,
        'roll_read':'Control_get_Roll' in space,
        'pitch_trim_read':'Control_get_PitchTrim' in space,
        'yaw_trim_read':'Control_get_YawTrim' in space,
        'roll_trim_read':'Control_get_RollTrim' in space,
    }
    log=ksp/'KSP.log'
    log_start=''
    if log.is_file():
        with log.open('r',encoding='utf-8',errors='replace') as file:
            log_start=file.readline().strip()
    cfg=mod/'PluginData/settings.cfg'
    report={
        'scope':'Local files and shipped RPC schemas only; no running game, server or physics-step test',
        'ksp_root':str(ksp),
        'ksp_build_id':build_id.group(1),
        'ksp_log_first_line':log_start,
        'ksp_log_predates_krpc_install':log.is_file() and log.stat().st_mtime < (mod/'KRPC.dll').stat().st_mtime,
        'krpc_changelog_release_header':(mod/'CHANGELOG.md').read_text(encoding='utf-8').splitlines()[0],
        'krpc_settings_bytes':cfg.stat().st_size if cfg.is_file() else None,
        'game_data_top_level_directories':sorted(x.name for x in (ksp/'GameData').iterdir() if x.is_dir()),
        'shipped_rpc_capabilities':needed,
        'explicit_physics_single_step_rpc_names':[name for name in list(core)+list(space)
                                                  if re.search(r'(?:step|advance).*(?:physics|fixed)|'
                                                               r'(?:physics|fixed).*(?:step|advance)',name,re.I)],
        'files':{str(path.relative_to(ksp)).replace('\\','/'):{'bytes':path.stat().st_size,
                                                               'sha256':sha(path)} for path in required},
        'live_bridge_verified':False,
        'physics_time_control_verified':False,
        'applied_control_provenance_verified':False,
    }
    REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'ksp_build_id':report['ksp_build_id'],
                      'krpc_release_header':report['krpc_changelog_release_header'],
                      'rpc_capabilities':needed,
                      'explicit_step_rpc_names':report['explicit_physics_single_step_rpc_names'],
                      'live_bridge_verified':False},ensure_ascii=False))


if __name__=='__main__':
    main()
