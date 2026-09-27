"""Read-only localhost kRPC probe. Never changes craft or game controls."""
import argparse
import importlib.metadata
import json
import socket
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CLIENT=ROOT/'build/krpc_client'
REPORT=ROOT/'reports/ksp_krpc_readonly_probe.json'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--address',default='127.0.0.1')
    parser.add_argument('--rpc-port',type=int,default=50000)
    parser.add_argument('--stream-port',type=int,default=50001)
    args=parser.parse_args()
    if args.address not in ('127.0.0.1','localhost'):
        raise ValueError('read-only preflight is restricted to localhost')
    if not (CLIENT/'krpc/__init__.py').is_file():
        raise FileNotFoundError('install pinned krpc==0.6.0 into build/krpc_client first')
    sys.path.insert(0,str(CLIENT))
    import krpc
    result={'scope':'Read-only connection and reported state; no pause, warp or control writes',
            'client_version':importlib.metadata.version('krpc'),
            'address':args.address,'rpc_port':args.rpc_port,'stream_port':args.stream_port,
            'connected':False,'flight_scene':False,'physics_tick_control_verified':False,
            'applied_control_provenance_verified':False}
    try:
        with socket.create_connection((args.address,args.rpc_port),timeout=2):
            pass
    except OSError as exc:
        result['connection_observation']=f'RPC port unavailable: {type(exc).__name__}'
    else:
        socket.setdefaulttimeout(8)
        conn=krpc.connect(name='Faithful Fly read-only preflight',address=args.address,
                          rpc_port=args.rpc_port,stream_port=args.stream_port)
        try:
            result['connected']=True
            result['server_version']=str(conn.krpc.get_status().version)
            scene=str(conn.krpc.game_scene)
            result['game_scene']=scene
            result['paused']=bool(conn.krpc.paused)
            if 'flight' in scene.lower():
                result['flight_scene']=True
                result['physics_warp_factor']=int(conn.space_center.physics_warp_factor)
                vessel=conn.space_center.active_vessel
                result['autopilot_engaged']=bool(vessel.auto_pilot.engaged)
                control=vessel.control
                result['sas']=bool(control.sas)
                result['pitch_trim']=float(control.pitch_trim)
                result['yaw_trim']=float(control.yaw_trim)
                result['roll_trim']=float(control.roll_trim)
                result['pitch']=float(control.pitch)
                result['yaw']=float(control.yaw)
                result['roll']=float(control.roll)
                result['throttle']=float(control.throttle)
        finally:
            conn.close()
    REPORT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    main()
