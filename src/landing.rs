//! Privileged assessment only. Never feed these fields to the fly.
use serde::{Deserialize, Serialize};
use std::{fs, path::Path};

#[derive(Clone, Copy, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Sample {
    pub tick: u64,
    pub time_ns: u64,
    pub contact: bool,
    pub destroyed: bool,
    pub target_distance_m: f64,
    pub speed_mps: f64,
    pub angular_speed_rad_s: f64,
    // Pre-contact solver velocities, not velocities clamped by ground contact.
    pub impact_vertical_mps: Option<f64>,
    pub impact_horizontal_mps: Option<f64>,
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Stability {
    pub max_speed_mps: f64,
    pub max_angular_speed_rad_s: f64,
    pub max_sample_gap_ns: u64,
}

#[derive(Debug, PartialEq, Serialize)]
pub enum Outcome { Incomplete, Failed(String), Success { time_ns: u64 } }

#[derive(Clone, Copy, Debug, PartialEq, Eq, Deserialize, Serialize)]
pub enum Environment { Native, Ksp }

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SeriesPlan {
    pub environment: Environment,
    pub training_seeds: [u64; 3],
    pub start_ids: Vec<u64>,
    pub stability: Stability,
    #[serde(default)]
    pub training_checkpoint_sha256: Option<[String; 3]>,
    #[serde(default)]
    pub start_state_sha256: Option<Vec<String>>,
}
pub struct Trial {
    pub environment: Environment,
    pub seed: u64,
    pub start_id: u64,
    pub outcome: Outcome,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct SeriesInput {
    format: String,
    plan: SeriesPlan,
    trials: Vec<SeriesTrace>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct SeriesTrace {
    seed: u64,
    start_id: u64,
    trace: String,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct TraceBinding {
    seed: u64,
    start_id: u64,
    training_checkpoint_sha256: String,
    start_state_sha256: String,
}

fn valid_sha256(s: &str) -> bool {
    s.len() == 64 && s.bytes().all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase())
}

// Requires one terminal outcome for every preregistered pair. This arithmetic
// does not authenticate the plan's preregistration or trial provenance.
pub fn assess_series(plan: &SeriesPlan, trials: &[Trial]) -> Result<[usize; 3], String> {
    use std::collections::HashSet;
    let starts: HashSet<_>=plan.start_ids.iter().copied().collect();
    let seeds: HashSet<_>=plan.training_seeds.iter().copied().collect();
    if starts.len()!=100 || plan.start_ids.len()!=100 || seeds.len()!=3 || trials.len()!=300 {
        return Err("need three distinct seeds and exactly 100 starts / 300 trials".into());
    }
    let mut seen=HashSet::new();let mut counts=[0;3];
    for trial in trials {
        if trial.environment!=plan.environment || !starts.contains(&trial.start_id) ||
            !seeds.contains(&trial.seed) || !seen.insert((trial.seed,trial.start_id)) {
            return Err("mixed environment, unexpected start/seed or duplicate trial".into());
        }
        let index=plan.training_seeds.iter().position(|s|*s==trial.seed).unwrap();
        match trial.outcome {
            Outcome::Success{..}=>counts[index]+=1,
            Outcome::Failed(_)=>{},
            Outcome::Incomplete=>return Err("unfinished trial cannot complete a series".into()),
        }
    }
    Ok(counts)
}

pub fn series_threshold_passed(counts: [usize;3]) -> bool { counts.iter().all(|n|*n>=90 && *n<=100) }

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Input {
    format: String,
    source: String,
    stability: Stability,
    samples: Vec<Sample>,
    #[serde(default)]
    binding: Option<TraceBinding>,
}

pub fn evaluate(samples: &[Sample], stability: Stability) -> Result<Outcome, String> {
    if !stability.max_speed_mps.is_finite() || stability.max_speed_mps < 0. ||
        !stability.max_angular_speed_rad_s.is_finite() || stability.max_angular_speed_rad_s < 0. ||
        stability.max_sample_gap_ns == 0 || stability.max_sample_gap_ns > 100_000_000 {
        return Err("invalid declared stability thresholds or sampling cadence".into());
    }
    let mut previous: Option<&Sample> = None;
    let mut stable_since = None;
    let mut result = Outcome::Incomplete;
    // Validate the entire supplied trace, even if success occurred earlier.
    for s in samples {
        for x in [s.target_distance_m, s.speed_mps, s.angular_speed_rad_s] {
            if !x.is_finite() || x < 0. {return Err("invalid assessment telemetry".into());}
        }
        if let Some(p) = previous {
            if p.tick.checked_add(1) != Some(s.tick) || s.time_ns <= p.time_ns ||
                s.time_ns-p.time_ns > stability.max_sample_gap_ns {
                return Err("nonconsecutive or missing physics samples".into());
            }
        } else if s.tick != 0 || s.time_ns != 0 || s.contact {
            return Err("trace must start airborne at tick/time zero".into());
        }
        let touchdown = s.contact && previous.is_some_and(|p| !p.contact);
        let mut bad_impact = false;
        match (s.impact_vertical_mps,s.impact_horizontal_mps) {
            (Some(v),Some(h)) if touchdown && v.is_finite() && h.is_finite() && h >= 0. => {
                bad_impact = v.abs() > 2. || h > 1. || s.target_distance_m > 50.;
            },
            (None,None) if !touchdown => {},
            _ => return Err("touchdown requires paired finite pre-contact velocities; other samples forbid them".into()),
        }
        if result == Outcome::Incomplete {
            if s.destroyed {result=Outcome::Failed("destruction".into());}
            else if bad_impact {result=Outcome::Failed("touchdown limits exceeded".into());}
            else {
                let stable = s.contact && s.target_distance_m <= 50. &&
                    s.speed_mps <= stability.max_speed_mps &&
                    s.angular_speed_rad_s <= stability.max_angular_speed_rad_s;
                if stable {
                    let start = *stable_since.get_or_insert(s.time_ns);
                    if s.time_ns-start >= 10_000_000_000 {result=Outcome::Success{time_ns:s.time_ns};}
                } else {stable_since=None;}
            }
        }
        previous=Some(s);
    }
    Ok(result)
}

pub fn run(input: &Path, output: &Path) -> Result<(), String> {
    use sha2::{Digest,Sha256};
    let raw=fs::read(input).map_err(|e|e.to_string())?;
    let data: Input=serde_json::from_slice(&raw).map_err(|e|e.to_string())?;
    if !["faithful-fly.landing-trace.v1", "faithful-fly.landing-trace.v2"].contains(&data.format.as_str()) ||
       !["diagnostic", "native", "ksp"].contains(&data.source.as_str()) {
        return Err("unsupported trace format or source".into());
    }
    let outcome=evaluate(&data.samples,data.stability)?;
    let report=serde_json::json!({"outcome":outcome,"source":data.source,
        "input_sha256":format!("{:x}",Sha256::digest(&raw)),
        "scope":"Assessment of supplied physics trace; origin and fly-control provenance not authenticated"});
    fs::write(output,serde_json::to_vec_pretty(&report).unwrap()).map_err(|e|e.to_string())
}

pub fn run_series(input: &Path, output: &Path) -> Result<(), String> {
    use sha2::{Digest,Sha256};
    let raw=fs::read(input).map_err(|e|e.to_string())?;
    let series:SeriesInput=serde_json::from_slice(&raw).map_err(|e|e.to_string())?;
    if !["faithful-fly.landing-series.v2", "faithful-fly.landing-series.v3"].contains(&series.format.as_str()) || series.trials.len()!=300 {
        return Err("invalid series format or trial count".into());
    }
    let bound = series.format == "faithful-fly.landing-series.v3";
    if bound {
        let checkpoints = series.plan.training_checkpoint_sha256.as_ref().ok_or("missing training checkpoint hashes")?;
        let starts = series.plan.start_state_sha256.as_ref().ok_or("missing start state hashes")?;
        if starts.len()!=series.plan.start_ids.len() ||
            !checkpoints.iter().all(|h|valid_sha256(h)) || !starts.iter().all(|h|valid_sha256(h)) {
            return Err("invalid training checkpoint or start state hashes".into());
        }
        // Distinct labels cannot turn reused artifacts into independent trials.
        // Distinct hashes are necessary here, but do not authenticate provenance.
        if checkpoints.iter().collect::<std::collections::HashSet<_>>().len()!=3 ||
            starts.iter().collect::<std::collections::HashSet<_>>().len()!=starts.len() {
            return Err("bound series requires distinct training checkpoint and start state hashes".into());
        }
    }
    let base=input.parent().ok_or("series input has no parent directory")?;
    let mut trials=Vec::with_capacity(300);
    let mut evidence=Vec::with_capacity(300);
    let mut paths=std::collections::HashSet::new();
    for item in &series.trials {
        let path=Path::new(&item.trace);
        if path.is_absolute() || path.components().any(|c| !matches!(c,std::path::Component::Normal(_))) {
            return Err("trace paths must be relative filenames below the series directory".into());
        }
        if !paths.insert(path.to_path_buf()) {return Err("duplicate trial trace path".into());}
        let bytes=fs::read(base.join(path)).map_err(|e|format!("{}: {e}",item.trace))?;
        let trace:Input=serde_json::from_slice(&bytes).map_err(|e|format!("{}: {e}",item.trace))?;
        let expected=match series.plan.environment {Environment::Native=>"native",Environment::Ksp=>"ksp"};
        if trace.format!=if bound {"faithful-fly.landing-trace.v2"} else {"faithful-fly.landing-trace.v1"} || trace.source!=expected {
            return Err(format!("{}: trace format or environment mismatch",item.trace));
        }
        if bound {
            let b=trace.binding.as_ref().ok_or_else(||format!("{}: missing trace binding",item.trace))?;
            let seed_index=series.plan.training_seeds.iter().position(|s|*s==item.seed)
                .ok_or_else(||format!("{}: unexpected seed",item.trace))?;
            let start_index=series.plan.start_ids.iter().position(|s|*s==item.start_id)
                .ok_or_else(||format!("{}: unexpected start",item.trace))?;
            if b.seed!=item.seed || b.start_id!=item.start_id ||
                b.training_checkpoint_sha256!=series.plan.training_checkpoint_sha256.as_ref().unwrap()[seed_index] ||
                b.start_state_sha256!=series.plan.start_state_sha256.as_ref().unwrap()[start_index] {
                return Err(format!("{}: trace binding differs from series plan",item.trace));
            }
        }
        if trace.stability != series.plan.stability {
            return Err(format!("{}: stability thresholds differ from series plan",item.trace));
        }
        let outcome=evaluate(&trace.samples,series.plan.stability)?;
        evidence.push(serde_json::json!({"seed":item.seed,"start_id":item.start_id,
            "trace":item.trace,"trace_sha256":format!("{:x}",Sha256::digest(&bytes)),"outcome":outcome}));
        trials.push(Trial{environment:series.plan.environment,seed:item.seed,start_id:item.start_id,outcome});
    }
    let counts=assess_series(&series.plan,&trials)?;
    let report=serde_json::json!({"format":"faithful-fly.landing-series-assessment.v2",
        "series_input_sha256":format!("{:x}",Sha256::digest(&raw)),
        "bound_to_declared_checkpoint_and_start":bound,
        "environment":series.plan.environment,"training_seeds":series.plan.training_seeds,
        "start_ids":series.plan.start_ids,"stability":series.plan.stability,"successes_by_seed":counts,
        "series_threshold_passed":series_threshold_passed(counts),"trials":evidence,
        "scope":"Supplied traces only; training, KSP origin, control provenance, plan preregistration and biological gates are not authenticated"});
    fs::write(output,serde_json::to_vec_pretty(&report).map_err(|e|e.to_string())?).map_err(|e|e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    fn config()->Stability {Stability{max_speed_mps:0.1,max_angular_speed_rad_s:0.01,max_sample_gap_ns:100_000_000}}
    fn trace()->Vec<Sample> {(0..=101).map(|i|Sample{tick:i,time_ns:i*100_000_000,
        contact:i>0,destroyed:false,target_distance_m:50.,speed_mps:0.,angular_speed_rad_s:0.,
        impact_vertical_mps:if i==1{Some(-2.)}else{None},
        impact_horizontal_mps:if i==1{Some(1.)}else{None}}).collect()}
    #[test] fn exact_limits_and_duration() {
        let t=trace();assert_eq!(evaluate(&t[..101],config()).unwrap(),Outcome::Incomplete);
        assert_eq!(evaluate(&t,config()).unwrap(),Outcome::Success{time_ns:10_100_000_000});
    }
    #[test] fn clamped_ground_velocity_cannot_hide_hard_impact() {
        let mut t=trace();t[1].impact_vertical_mps=Some(-2.00001);
        assert!(matches!(evaluate(&t,config()).unwrap(),Outcome::Failed(_)));
        t[1].impact_vertical_mps=None;assert!(evaluate(&t,config()).is_err());
    }
    #[test] fn bounce_resets_stability() {
        let mut t=trace();t[60].contact=false;t[61].impact_vertical_mps=Some(-0.1);
        t[61].impact_horizontal_mps=Some(0.);
        assert_eq!(evaluate(&t,config()).unwrap(),Outcome::Incomplete);
    }
    #[test] fn gaps_and_nonfinite_values_fail_closed() {
        let mut t=trace();t.remove(30);assert!(evaluate(&t,config()).is_err());
        let mut t=trace();t[50].speed_mps=f64::NAN;assert!(evaluate(&t,config()).is_err());
    }
    #[test] fn destruction_and_drift_prevent_success() {
        let mut t=trace();t[100].destroyed=true;
        assert!(matches!(evaluate(&t,config()).unwrap(),Outcome::Failed(_)));
        let mut t=trace();t[100].target_distance_m=50.01;
        assert_eq!(evaluate(&t,config()).unwrap(),Outcome::Incomplete);
    }
    #[test] fn series_cannot_pool_seeds_or_mix_environments() {
        let plan=SeriesPlan{environment:Environment::Ksp,training_seeds:[11,22,33],start_ids:(0..100).collect(),stability:config(),training_checkpoint_sha256:None,start_state_sha256:None};
        let mut trials:Vec<_>=plan.training_seeds.iter().flat_map(|&seed|(0..100).map(move |start_id|Trial{
            environment:Environment::Ksp,seed,start_id,
            outcome:if seed==11 && start_id>=89 {Outcome::Failed("impact".into())}
                    else {Outcome::Success{time_ns:12_000_000_000}}})).collect();
        assert_eq!(assess_series(&plan,&trials).unwrap(),[89,100,100]);
        assert!(!series_threshold_passed([89,100,100]));
        assert!(series_threshold_passed([90,90,90]));
        trials[0].environment=Environment::Native;assert!(assess_series(&plan,&trials).is_err());
        trials[0].environment=Environment::Ksp;
        trials[0].start_id=1;assert!(assess_series(&plan,&trials).is_err());
        trials[0].start_id=0;trials.pop();assert!(assess_series(&plan,&trials).is_err());
    }
    #[test] fn series_cli_reads_each_trace_and_records_evidence() {
        let dir=std::env::temp_dir().join(format!("faithful-fly-series-{}-{}",
            std::process::id(),std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()));
        fs::create_dir(&dir).unwrap();
        let mut entries=Vec::new();
        for seed in [11,22,33] {
            for start_id in 0..100 {
                let name=format!("{seed}-{start_id}.json");
                let trace=serde_json::json!({"format":"faithful-fly.landing-trace.v1","source":"ksp",
                    "stability":{"max_speed_mps":0.1,"max_angular_speed_rad_s":0.01,"max_sample_gap_ns":100000000},
                    "samples":[{"tick":0,"time_ns":0,"contact":false,"destroyed":true,
                        "target_distance_m":100.0,"speed_mps":1.0,"angular_speed_rad_s":0.0,
                        "impact_vertical_mps":null,"impact_horizontal_mps":null}]});
                fs::write(dir.join(&name),serde_json::to_vec(&trace).unwrap()).unwrap();
                entries.push(serde_json::json!({"seed":seed,"start_id":start_id,"trace":name}));
            }
        }
        let series=serde_json::json!({"format":"faithful-fly.landing-series.v2",
            "plan":{"environment":"Ksp","training_seeds":[11,22,33],"start_ids":(0..100).collect::<Vec<_>>(),
                    "stability":{"max_speed_mps":0.1,"max_angular_speed_rad_s":0.01,"max_sample_gap_ns":100000000}},
            "trials":entries});
        let input=dir.join("series.json");let output=dir.join("assessment.json");
        fs::write(&input,serde_json::to_vec(&series).unwrap()).unwrap();
        run_series(&input,&output).unwrap();
        let report:serde_json::Value=serde_json::from_slice(&fs::read(&output).unwrap()).unwrap();
        assert_eq!(report["successes_by_seed"],serde_json::json!([0,0,0]));
        assert_eq!(report["series_threshold_passed"],false);
        assert_eq!(report["trials"].as_array().unwrap().len(),300);
        assert_eq!(report["trials"][0]["trace_sha256"].as_str().unwrap().len(),64);
        let altered=dir.join("11-0.json");
        let mut trace:serde_json::Value=serde_json::from_slice(&fs::read(&altered).unwrap()).unwrap();
        trace["stability"]["max_speed_mps"]=serde_json::json!(10.0);
        fs::write(&altered,serde_json::to_vec(&trace).unwrap()).unwrap();
        assert!(run_series(&input,&dir.join("rejected.json")).unwrap_err().contains("stability thresholds"));
        trace["stability"]["max_speed_mps"]=serde_json::json!(0.1);
        fs::write(&altered,serde_json::to_vec(&trace).unwrap()).unwrap();
        let checkpoint_hashes=["a".repeat(64),"b".repeat(64),"c".repeat(64)];
        let start_hashes:Vec<String>=(0..100).map(|i|format!("{i:064x}")).collect();
        let mut series:serde_json::Value=serde_json::from_slice(&fs::read(&input).unwrap()).unwrap();
        series["format"]=serde_json::json!("faithful-fly.landing-series.v3");
        series["plan"]["training_checkpoint_sha256"]=serde_json::json!(checkpoint_hashes);
        series["plan"]["start_state_sha256"]=serde_json::json!(start_hashes);
        for entry in series["trials"].as_array().unwrap() {
            let seed=entry["seed"].as_u64().unwrap();
            let start=entry["start_id"].as_u64().unwrap();
            let path=dir.join(entry["trace"].as_str().unwrap());
            let mut t:serde_json::Value=serde_json::from_slice(&fs::read(&path).unwrap()).unwrap();
            t["format"]=serde_json::json!("faithful-fly.landing-trace.v2");
            t["binding"]=serde_json::json!({"seed":seed,"start_id":start,
                "training_checkpoint_sha256":checkpoint_hashes[[11,22,33].iter().position(|x|*x==seed).unwrap()],
                "start_state_sha256":start_hashes[start as usize]});
            fs::write(path,serde_json::to_vec(&t).unwrap()).unwrap();
        }
        fs::write(&input,serde_json::to_vec(&series).unwrap()).unwrap();
        run_series(&input,&output).unwrap();
        let report:serde_json::Value=serde_json::from_slice(&fs::read(&output).unwrap()).unwrap();
        assert_eq!(report["bound_to_declared_checkpoint_and_start"],true);
        // Reject reuse even when every trace binding agrees with the altered plan.
        for field in ["training_checkpoint_sha256", "start_state_sha256"] {
            let mut reused=series.clone();
            reused["plan"][field][1]=reused["plan"][field][0].clone();
            let changed_seed=if field=="training_checkpoint_sha256" {22} else {11};
            for entry in reused["trials"].as_array().unwrap() {
                let seed=entry["seed"].as_u64().unwrap();
                let start=entry["start_id"].as_u64().unwrap();
                if (field=="training_checkpoint_sha256" && seed==changed_seed) ||
                    (field=="start_state_sha256" && start==1) {
                    let path=dir.join(entry["trace"].as_str().unwrap());
                    let mut t:serde_json::Value=serde_json::from_slice(&fs::read(&path).unwrap()).unwrap();
                    t["binding"][field]=reused["plan"][field][0].clone();
                    fs::write(path,serde_json::to_vec(&t).unwrap()).unwrap();
                }
            }
            fs::write(&input,serde_json::to_vec(&reused).unwrap()).unwrap();
            assert!(run_series(&input,&dir.join("reused-rejected.json")).unwrap_err()
                .contains("distinct training checkpoint and start state hashes"));
            assert!(!dir.join("reused-rejected.json").exists());
            // Restore bindings before testing the next independent intervention.
            for entry in series["trials"].as_array().unwrap() {
                let seed=entry["seed"].as_u64().unwrap();
                let start=entry["start_id"].as_u64().unwrap();
                let path=dir.join(entry["trace"].as_str().unwrap());
                let mut t:serde_json::Value=serde_json::from_slice(&fs::read(&path).unwrap()).unwrap();
                t["binding"]["training_checkpoint_sha256"]=serde_json::json!(checkpoint_hashes[[11,22,33].iter().position(|x|*x==seed).unwrap()]);
                t["binding"]["start_state_sha256"]=serde_json::json!(start_hashes[start as usize]);
                fs::write(path,serde_json::to_vec(&t).unwrap()).unwrap();
            }
        }
        fs::write(&input,serde_json::to_vec(&series).unwrap()).unwrap();
        run_series(&input,&output).unwrap();
        let mut swapped:serde_json::Value=serde_json::from_slice(&fs::read(&altered).unwrap()).unwrap();
        swapped["binding"]["start_state_sha256"]=serde_json::json!(start_hashes[1]);
        fs::write(&altered,serde_json::to_vec(&swapped).unwrap()).unwrap();
        assert!(run_series(&input,&dir.join("rejected.json")).unwrap_err().contains("trace binding differs"));
    }
}

