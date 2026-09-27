//! Privileged assessment only. Never feed these fields to the fly.
use std::{fs, path::Path};

#[derive(Clone, Copy, Debug)]
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

#[derive(Clone, Copy, Debug)]
pub struct Stability {
    pub max_speed_mps: f64,
    pub max_angular_speed_rad_s: f64,
    pub max_sample_gap_ns: u64,
}

#[derive(Debug, PartialEq)]
pub enum Outcome { Incomplete, Failed(String), Success { time_ns: u64 } }

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Environment { Native, Ksp }


pub struct SeriesPlan {
    pub environment: Environment,
    pub training_seeds: [u64; 3],
    pub start_ids: Vec<u64>,
}
pub struct Trial {
    pub environment: Environment,
    pub seed: u64,
    pub start_id: u64,
    pub outcome: Outcome,
}


struct SeriesInput {
    format: String,
    plan: SeriesPlan,
    trials: Vec<SeriesTrace>,
}


struct SeriesTrace {
    seed: u64,
    start_id: u64,
    trace: String,
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


struct Input {
    format: String,
    source: String,
    stability: Stability,
    samples: Vec<Sample>,
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


fn main() {
 let samples:Vec<Sample>=(0..=101).map(|i|Sample {tick:i,time_ns:i*100_000_000,contact:i>0,destroyed:false,target_distance_m:1.,speed_mps:5.,angular_speed_rad_s:3.,impact_vertical_mps:if i==1{Some(-1.)}else{None},impact_horizontal_mps:if i==1{Some(0.)}else{None}}).collect();
 let strict=Stability {max_speed_mps:0.1,max_angular_speed_rad_s:0.01,max_sample_gap_ns:100_000_000};
 let loose=Stability {max_speed_mps:10.,max_angular_speed_rad_s:10.,max_sample_gap_ns:100_000_000};
 let a=evaluate(&samples,strict).unwrap(); let b=evaluate(&samples,loose).unwrap();
 assert_eq!(a,Outcome::Incomplete); assert!(matches!(b,Outcome::Success{..}));
 println!("strict={:?}; loose={:?}",a,b);
}
