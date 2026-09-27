"""Summarize the exploratory candidate-event pad-clearance sweep."""
import hashlib
import json

from flymimic_public_model import ROOT


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    rows = []
    for gap_um in (50, 75, 100, 125, 150, 175, 200):
        stem = f"harness_effective_g_gap_{gap_um}um_events"
        path = ROOT / "reports" / f"{stem}_local.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        trace = ROOT / "data/derived" / f"{stem}_v1" / "traces.npz"
        assert report["trace_sha256"] == sha(trace)
        assert report["executed_source_sha256"] == sha(ROOT / "tools/probe_harness_effective_g.py")
        assert report["motor_event_ticks"] == [190, 641]
        no_event = next(c for c in report["cases"]
                        if c["feedback"] and c["contact"] and not c["pulse"])
        events = next(c for c in report["cases"]
                      if c["feedback"] and c["contact"] and c["pulse"])
        off = next(c for c in report["cases"]
                   if c["feedback"] and not c["contact"] and c["pulse"])
        assert off["max_slide_mm"] == 0
        rows.append({"pad_shift_um": gap_um,
                     "no_event_first_contact_tick": no_event["first_contact_tick"],
                     "no_event_max_slide_mm": no_event["max_slide_mm"],
                     "event_first_contact_tick": events["first_contact_tick"],
                     "event_max_slide_mm": events["max_slide_mm"],
                     "event_max_throttle": events["max_throttle"],
                     "no_contact_control_max_slide_mm": off["max_slide_mm"],
                     "source_report_sha256": sha(path)})
    diagnostic = [r["pad_shift_um"] for r in rows if r["no_event_max_slide_mm"] == 0
                  and r["event_max_slide_mm"] > 0]
    result = {"rows": rows, "sampled_gaps_with_event_contact_and_no_control_leak_um": diagnostic,
              "executed_source_sha256": sha(ROOT / "tools/summarize_cabin_event_gap.py"),
              "scope": "Exploratory grid selected after viewing mechanics; no physiological pad geometry, motor mapping, or robust controller claim."}
    out = ROOT / "reports/cabin_event_gap_sweep.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
