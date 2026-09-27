"""Freeze a same-image head-yaw intervention for native visual input."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = json.loads((ROOT / "configs/visual_input_fixture.json").read_text(encoding="utf-8"))
dark = source["frames"][0]["rgb"]
front = source["frames"][1]["rgb"]
identity = [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]
yaw_180 = [[-1., 0., 0.], [0., -1., 0.], [0., 0., 1.]]
fixture = {"optics": source["optics"], "microvilli": source["microvilli"],
           "seed": source["seed"], "blocks": source["blocks"],
           "frames": [{"ticks": 100, "rgb": dark, "local_to_world": identity},
                      {"ticks": 500, "rgb": front, "local_to_world": identity},
                      {"ticks": 500, "rgb": front, "local_to_world": yaw_180},
                      {"ticks": 500, "rgb": dark, "local_to_world": yaw_180}]}
path = ROOT / "configs/visual_head_pose_fixture.json"
path.write_text(json.dumps(fixture, separators=(",", ":")) + "\n", encoding="utf-8")
print(path)
