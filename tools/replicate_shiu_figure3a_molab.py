"""Foreground MoLab replication of the original Shiu Figure 3A grid.
Each completed trial is archived before the next trial. No MaleCNS transfer.
"""
import argparse
import ast
import gc
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--sugar", type=int, required=True)
    parser.add_argument("--bitter", type=int, required=True)
    parser.add_argument("--resume", action="store_true", help="Verify published trials and execute only missing trials")
    args = parser.parse_args()
    root, source = args.root, args.source_root
    archive = load_module("shiu_grid_archive", source/"tools/hf_artifact_archive.py")
    import brian2 as b
    import numpy as np
    import pandas as pd
    from huggingface_hub import HfApi
    api = HfApi(token=os.environ["HF_TOKEN"])
    if not api.repo_info("TryDotAtwo/faithful-fly-artifacts", repo_type="dataset").private:
        raise RuntimeError("Expected private HF archive")
    b.prefs.codegen.target = "numpy"
    b.prefs.core.default_float_dtype = np.float64
    inputs = root/"data/reference/shiu_2024"
    expected = {
        "model.py": "fc45837d7122c6ce2a7f3f2f23c515992e4b232aadb919efabb72337fac88e4e",
        "figures.ipynb": "33cd73c0b4b4a291c51b7bab639c4fa28978e49e111ff0d6adbca5687addb84c",
        "2023_03_23_completeness_630_final.csv": "e6b71e17671a9bdb05f55e4bc6774640a1418cb7a05125e0fc994ad40f9bfdfb",
        "2023_03_23_connectivity_630_final.parquet": "94db8c650533bc36ffa3223f2e62325d5648b8d6bd31c3a4e1c804628c7557b3",
    }
    for name, digest in expected.items():
        if archive.digest(inputs/name) != digest:
            raise RuntimeError("Author input identity mismatch: "+name)
    notebook = json.loads((inputs/"figures.ipynb").read_text())
    literals = {}
    for node in ast.parse("".join(notebook["cells"][23]["source"])).body:
        if isinstance(node, ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0], ast.Name):
            key = node.targets[0].id
            if key in ("neu_sugar","neu_bitter","id_mn9","freqs"):
                literals[key] = ast.literal_eval(node.value)
    freqs = list(range(0,201,20))
    if literals["freqs"] != freqs or args.sugar not in freqs or args.bitter not in freqs:
        raise RuntimeError("Condition outside author Figure 3A grid")
    ids = pd.read_csv(inputs/"2023_03_23_completeness_630_final.csv",index_col=0).index.to_numpy()
    mapping = {int(v): i for i,v in enumerate(ids)}
    sugar = [mapping[int(v)] for v in literals["neu_sugar"]]
    bitter = [mapping[int(v)] for v in literals["neu_bitter"]]
    target = mapping[int(literals["id_mn9"])]
    author = load_module("shiu_grid_author",inputs/"model.py")
    if int(author.default_params["n_run"]) != 30:
        raise RuntimeError("Author trial count changed")
    protocol = {
        "schema":"shiu-original-figure3a-grid-v1",
        "author_commit":"91bdd1e7dcf193f3e7ca5a8933497fcef63b7960",
        "source_sha256":expected, "source_notebook_cells":[23,24,25],
        "frequencies_hz":freqs,"trials_per_condition":30,"duration_ms":1000,"dt_ms":0.1,
        "seed_rule":"19303000 + (sugar_index*11+bitter_index)*30 + trial_index",
        "backend":"unmodified author create_model + poi; Brian2 numpy float64",
        "input_rule":"Original Brian2 PoissonInput N=1; both populations zero refractory including 0 Hz",
        "sugar_body_ids":literals["neu_sugar"],"bitter_body_ids":literals["neu_bitter"],
        "mn9_body_id":literals["id_mn9"],
        "brian2":b.__version__,"numpy":np.__version__,"pandas":pd.__version__,
        "acceptance":"Report all 121 conditions with 30 trials; compare author means/SD when reference available. No outcome-based selection or altered weights.",
        "limits":"A condition is a shard of the full author grid; no MaleCNS physiology, local plasticity, or KSP claim.",
    }
    protocol_path = root/"figure3a-grid-protocol.json"
    text = json.dumps(protocol,indent=2)+"\n"
    if protocol_path.exists() and protocol_path.read_text()!=text:
        raise RuntimeError("Preregistered protocol differs")
    protocol_path.write_text(text)
    closure = {str((inputs/name).relative_to(root)):{"bytes":(inputs/name).stat().st_size,"sha256":digest} for name,digest in expected.items()}
    closure["figure3a-grid-protocol.json"]={"bytes":protocol_path.stat().st_size,"sha256":archive.digest(protocol_path)}
    harness = root/"tools/replicate_shiu_figure3a_molab.py"
    closure["tools/replicate_shiu_figure3a_molab.py"]={"bytes":harness.stat().st_size,"sha256":archive.digest(harness)}
    for name in ("hf_artifact_archive.py","run_molab_conductance_finite.py"):
        p = root/"tools"/name
        closure["tools/"+name]={"bytes":p.stat().st_size,"sha256":archive.digest(p)}
    print("GRID_SOURCE_INPUT_CLOSURE",json.dumps(archive.publish(root,{"schema":"faithful-fly-artifacts-v1","files":closure})),flush=True)
    condition_index = freqs.index(args.sugar)*len(freqs)+freqs.index(args.bitter)
    condition = root/"figure3a"/("sugar%03d_bitter%03d"%(args.sugar,args.bitter))
    condition.mkdir(parents=True,exist_ok=args.resume)
    verified_previous = {}
    if args.resume:
        revision = api.repo_info("TryDotAtwo/faithful-fly-artifacts",repo_type="dataset").sha
        manifest_names = [name for name in api.list_repo_files("TryDotAtwo/faithful-fly-artifacts",repo_type="dataset",revision=revision) if name.startswith("manifests/") and name.endswith(".json")]
        prefix = str(condition.relative_to(root))+"/"
        for name in manifest_names:
            path = Path(api.hf_hub_download("TryDotAtwo/faithful-fly-artifacts",name,repo_type="dataset",revision=revision))
            digest = archive.digest(path)
            if name != "manifests/"+digest+".json":
                raise RuntimeError("Archive manifest identity mismatch")
            manifest = json.loads(path.read_text())
            for relative,record in manifest.get("files",{}).items():
                if relative.startswith(prefix):
                    verified_previous.setdefault(relative,[]).append((record,{"repo_id":"TryDotAtwo/faithful-fly-artifacts","repo_type":"dataset","revision":revision,"manifest":name,"sha256":digest}))
        print("RESUME_ARCHIVE_SCAN_COMPLETE",revision,flush=True)
    counts, receipts = [], []
    for trial in range(30):
        started = time.monotonic()
        seed = 19303000+condition_index*30+trial
        directory = condition/("trial%02d"%trial)
        if directory.exists():
            expected_paths = [directory/"report.json",directory/"spikes.bin"]
            matching_manifests = None
            for path in expected_paths:
                if not path.is_file():
                    raise RuntimeError("Incomplete existing trial requires explicit recovery: "+str(directory))
                relative = str(path.relative_to(root))
                matches = [receipt for record,receipt in verified_previous.get(relative,[]) if record["bytes"]==path.stat().st_size and record["sha256"]==archive.digest(path)]
                manifests = {receipt["manifest"]:receipt for receipt in matches}
                matching_manifests = manifests if matching_manifests is None else {name:receipt for name,receipt in matching_manifests.items() if name in manifests}
            if not matching_manifests:
                raise RuntimeError("Existing trial has no verified common remote manifest")
            previous = json.loads(expected_paths[0].read_text())
            if previous["seed"]!=seed or previous["trial"]!=trial or previous["sugar_hz"]!=args.sugar or previous["bitter_hz"]!=args.bitter or previous["protocol_sha256"]!=archive.digest(protocol_path):
                raise RuntimeError("Existing trial protocol mismatch")
            events = np.fromfile(expected_paths[1],dtype="<u4").reshape(-1,2)
            if len(events)!=previous["network_spikes"] or events[events[:,1]==target,0].tolist()!=previous["mn9_ticks"]:
                raise RuntimeError("Existing trial event/report mismatch")
            counts.append(len(previous["mn9_ticks"]))
            receipts.append(next(iter(matching_manifests.values())))
            print("REUSED_VERIFIED_TRIAL",trial,seed,len(previous["mn9_ticks"]),flush=True)
            continue
        archive.require_commit_capacity(api, 'TryDotAtwo/faithful-fly-artifacts', commits_needed=3)
        b.start_scope()
        b.defaultclock.dt = .1*b.ms
        b.seed(seed)
        params = dict(author.default_params)
        params["r_poi"] = args.sugar*b.Hz
        params["r_poi2"] = args.bitter*b.Hz
        neurons,synapses,monitor = author.create_model(inputs/"2023_03_23_completeness_630_final.csv",inputs/"2023_03_23_connectivity_630_final.parquet",params)
        pois,neurons = author.poi(neurons,sugar,bitter,params)
        network = b.Network(neurons,synapses,monitor,*pois)
        print("AUTHOR_TRIAL_START",args.sugar,args.bitter,trial,seed,len(neurons),len(synapses),flush=True)
        network.run(params["t_run"],report="text",report_period=30*b.second)
        ticks = np.rint(np.asarray(monitor.t/b.defaultclock.dt)).astype(np.uint32)
        indices = np.asarray(monitor.i,dtype=np.uint32)
        if np.any(ticks>=10000) or np.any(indices>=len(neurons)):
            raise RuntimeError("Spike outside trial")
        ordering = np.lexsort((indices,ticks))
        directory.mkdir()
        events = np.stack((ticks[ordering],indices[ordering]),axis=1).astype("<u4")
        events.tofile(directory/"spikes.bin")
        mn9 = ticks[indices==target].tolist()
        report = {
            "sugar_hz":args.sugar,"bitter_hz":args.bitter,"trial":trial,"seed":seed,
            "nodes":len(neurons),"edges":len(synapses),"ticks":10000,"network_spikes":len(indices),
            "mn9_ticks":mn9,"mn9_rate_hz":len(mn9),"wall_seconds":time.monotonic()-started,
            "protocol_sha256":archive.digest(protocol_path),
            "scope":"One trial of original author Figure 3A grid; no transfer to MaleCNS",
        }
        (directory/"report.json").write_text(json.dumps(report,indent=2)+"\n")
        files={str(p.relative_to(root)):{"bytes":p.stat().st_size,"sha256":archive.digest(p)} for p in directory.iterdir()}
        receipt = archive.publish(root,{"schema":"faithful-fly-artifacts-v1","files":files})
        receipts.append(receipt)
        counts.append(len(mn9))
        print("AUTHOR_TRIAL_RECEIPT",json.dumps({"trial":trial,"mn9":len(mn9),"receipt":receipt}),flush=True)
        del network, neurons, synapses, monitor, pois
        gc.collect()
    summary = {
        "sugar_hz":args.sugar,"bitter_hz":args.bitter,"trials":30,"mn9_rates_hz":counts,
        "mn9_mean_hz":float(np.mean(counts)),"mn9_sd_population_hz":float(np.std(counts)),
        "mn9_sd_sample_hz":float(np.std(counts,ddof=1)),"trial_receipts":receipts,
        "protocol_sha256":archive.digest(protocol_path),
        "scope":"Completed one 30-trial condition; full 121-condition Figure 3A grid remains incomplete",
    }
    path = condition/"summary.json"
    path.write_text(json.dumps(summary,indent=2)+"\n")
    files={str(path.relative_to(root)):{"bytes":path.stat().st_size,"sha256":archive.digest(path)}}
    print("AUTHOR_CONDITION_RECEIPT",json.dumps(archive.publish(root,{"schema":"faithful-fly-artifacts-v1","files":files})),flush=True)
    print("AUTHOR_CONDITION_SUMMARY",json.dumps({k:v for k,v in summary.items() if k!="trial_receipts"}),flush=True)

if __name__=="__main__":
    main()
