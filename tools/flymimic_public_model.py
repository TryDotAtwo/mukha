"""Load the pinned public FlyMimic model from verified bytes on Windows."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build/flymimic_pydeps"))
import mujoco as mj  # noqa: E402

MODEL = ROOT / "data/reference/flymimic/flymimic/assets/models/best_combined_cvt3.xml"
RESTORE = ROOT / "reports/flymimic_public_restore.json"
MODEL_SHA = "d67ff06d0c684599f00d5f33f8f8ac8ced01ab994c41341b551f8148b6d8aa0b"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_model(xml_text=None):
    restored = json.loads(RESTORE.read_text(encoding="utf-8"))
    assert restored["file_count"] == 73 and sha(MODEL) == MODEL_SHA
    for entry in restored["files"]:
        path = ROOT / entry["path"]
        assert path.stat().st_size == entry["bytes"] and sha(path) == entry["sha256"]
    assert mj.__version__ == "3.14.0"
    assets = {}
    model_dir = MODEL.parent
    for mesh in (model_dir / "meshes/stl").glob("*.stl"):
        relative = mesh.relative_to(model_dir).as_posix()
        assets[relative] = mesh.read_bytes()
    assert len(assets) == 71
    # MuJoCo's Windows XML path loader does not accept this workspace's
    # Cyrillic path. The byte API keeps the verified source XML unchanged.
    if xml_text is None:
        xml_text = MODEL.read_text(encoding="utf-8")
    model = mj.MjModel.from_xml_string(xml_text, assets)
    return model, restored
