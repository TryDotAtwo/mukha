"""Audit published FlyMimic XML for explicit FeCO sensory mechanics."""

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
XML = ROOT / "data/reference/flymimic/flymimic/assets/models/best_combined_cvt3.xml"
OUT = ROOT / "reports/flymimic_feco_structure.json"
BIOLOGICAL_SOURCE = "https://doi.org/10.1016/j.neuron.2023.07.009"


def main():
    raw = XML.read_bytes()
    root = ET.fromstring(raw)
    tendons = root.find("tendon")
    tendon_names = [x.get("name") for x in tendons] if tendons is not None else []
    sensors = root.find("sensor")
    sensor_names = [x.get("name") for x in sensors] if sensors is not None else []
    names = [(node.tag, node.get("name")) for node in root.iter()
             if node.get("name") and any(term in node.get("name").lower()
                                        for term in ("feco", "arculum", "chordotonal"))]
    assert len(tendon_names) == 15
    assert len(sensor_names) == 0
    assert not names
    joints = [node.get("name") for node in root.iter("joint")]
    assert "joint_LFTibia_pitch" in joints
    result = {
        "scope": "Explicit FeCO sensory-structure inventory in the original FlyMimic XML; no modified body variants",
        "xml_sha256": hashlib.sha256(raw).hexdigest(),
        "left_front_knee_joint_present": True,
        "tendon_count": len(tendon_names),
        "tendon_names": tendon_names,
        "sensor_count": len(sensor_names),
        "named_feco_arculum_or_chordotonal_elements": names,
        "biological_source": BIOLOGICAL_SOURCE,
        "source_constraint": "Mamiya et al. measured flexion-dependent arculum and claw-cap-cell motion and persistent claw tension even at full tibia extension; their FeCO model includes medial/lateral tendons, fibrils, dendrites, and surrounding tissue.",
        "interpretation": "The source XML has joint mechanics and named muscle tendons, but no explicit FeCO/arculum sensory structure or sensor. Joint q alone is not a measured claw dendritic strain.",
        "malecns_snpp50_per_cell_tuning_identified": False,
        "biological_validation": False,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("xml_sha256", "tendon_count", "sensor_count",
                                            "named_feco_arculum_or_chordotonal_elements")}, indent=2))


if __name__ == "__main__":
    main()
