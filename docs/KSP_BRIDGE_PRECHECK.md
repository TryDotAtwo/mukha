# KSP bridge precheck — 2026-09-26

The local Steam installation is at `D:/SteamLibrary/steamapps/common/Kerbal
Space Program`. `buildID64.txt` says build 03190, and the last KSP log identifies
1.12.5.3190. `GameData/kRPC` contains the v0.6.0 server assemblies and shipped
RPC schemas. File hashes and RPC names are in
`reports/ksp_local_preflight.json`. A bounded headless diagnostic launch on
2026-09-26 reached the assembly loader: `KSP.log` listed `KRPC.Core v0.6.0.0`
and the other kRPC assemblies. The owned process was stopped;
`reports/ksp_plugin_load_probe.json` records this narrow result. A second
diagnostic attempt was interrupted before reaching the main menu; its log ends
during ModuleManager instantiation, no new report was produced, and no KSP
process remains. Assembly loading does not establish plugin initialization,
a running RPC server, or a usable flight scene.

The shipped kRPC schema exposes pause, physics warp, raw control/trim reads,
SAS and AutoPilot. It has no named RPC for exactly one physics step. This
schema observation does not prove that stepping is impossible through a
game-side extension. The [official kRPC extension documentation](https://krpc.github.io/krpc/0.6.0/extending.html)
describes RPC execution in `FixedUpdate` and yielding across physics ticks;
that is a possible integration point requiring a live test. The
[official AutoPilot documentation](https://krpc.github.io/krpc/0.6.0/python/api/space-center/auto-pilot.html)
states that an engaged AutoPilot holds SAS off. An SAS=false record alone is
therefore insufficient to prove an unaided landing.

The Python client v0.6.0 with protobuf 7.36.2 is installed only in
`build/krpc_client`, using `configs/requirements-ksp-client.txt`. Recreate it
with `python -m pip install --target build/krpc_client -r
configs/requirements-ksp-client.txt`; this does not install the client globally.
Running
`python -I tools/probe_ksp_krpc_readonly.py` observed no responsive local RPC
server at port 50000 and wrote `reports/ksp_krpc_readonly_probe.json`. The
probe only reads state. The separate diagnostic launch did not establish a
server handshake, craft operation, physics step, applied-control audit, or
KSP landing.

Next live bridge gate: start the installed game and a localhost kRPC server;
record server/game versions and a fixed craft/save hash. Establish whether a
bounded command exchange can advance exactly one declared physics interval
while the full model computes slower than wall time. Record actual tick/time,
requested and applied controls, AutoPilot/SAS/trim/action-group state, and all
contact transitions. If stock kRPC cannot provide the time boundary, build a
minimal game-side tick gate that transports physical control positions and
measurements only, with no guidance or stabilization.
