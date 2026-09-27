"""Read FlyMimic head poses into a recorded synthetic visual fixture."""
import hashlib
import json
import xml.etree.ElementTree as ET

import numpy as np

from flymimic_public_model import ROOT, MODEL, MODEL_SHA, load_model, mj

FIXTURE = ROOT / "configs/visual_body_pose_fixture.json"
REPORT = ROOT / "reports/visual_body_pose_source.json"


def quat_product(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return np.array([aw*bw-ax*bx-ay*by-az*bz,
                     aw*bx+ax*bw+ay*bz-az*by,
                     aw*by-ax*bz+ay*bw+az*bx,
                     aw*bz+ax*by-ay*bx+az*bw])


def pose(xml_text):
    model, restored = load_model(xml_text)
    data = mj.MjData(model)
    key = mj.mj_name2id(model, mj.mjtObj.mjOBJ_KEY, "default-pose")
    head = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "Head")
    eyes = [mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, name) for name in ("LEye", "REye")]
    assert min(key, head, *eyes) >= 0
    mj.mj_resetDataKeyframe(model, data, key)
    mj.mj_forward(model, data)
    matrix = np.asarray(data.xmat[head]).reshape(3, 3).copy()
    assert np.allclose(matrix.T @ matrix, np.eye(3), atol=1e-12)
    assert np.linalg.det(matrix) > 0
    return matrix, data.xpos[head].copy(), [data.xpos[i].copy() for i in eyes], restored


def main():
    original_text = MODEL.read_text(encoding="utf-8")
    original_matrix, head_position, eye_positions, restored = pose(original_text)
    root = ET.fromstring(original_text)
    thorax = root.find("./worldbody/body[@name='Thorax']")
    assert thorax is not None
    source_quat = np.fromstring(thorax.attrib["quat"], sep=" ")
    assert source_quat.shape == (4,)
    rotated_quat = quat_product(np.array([0., 0., 0., 1.]), source_quat)
    thorax.attrib["quat"] = " ".join(f"{v:.17g}" for v in rotated_quat)
    rotated_text = ET.tostring(root, encoding="unicode")
    rotated_matrix, rotated_head_position, rotated_eye_positions, _ = pose(rotated_text)
    yaw = np.diag([-1., -1., 1.])
    error = float(np.max(np.abs(rotated_matrix - yaw @ original_matrix)))
    assert error < 1e-12
    assert eye_positions[0][1] > eye_positions[1][1]
    synthetic = json.loads((ROOT / "configs/visual_input_fixture.json").read_text(encoding="utf-8"))
    dark, front = synthetic["frames"][0]["rgb"], synthetic["frames"][1]["rgb"]
    fixture = {"optics": synthetic["optics"], "microvilli": synthetic["microvilli"],
               "seed": synthetic["seed"], "blocks": synthetic["blocks"],
               "frames": [{"ticks": 100, "rgb": dark, "local_to_world": original_matrix.tolist()},
                          {"ticks": 500, "rgb": front, "local_to_world": original_matrix.tolist()},
                          {"ticks": 500, "rgb": front, "local_to_world": rotated_matrix.tolist()},
                          {"ticks": 500, "rgb": dark, "local_to_world": rotated_matrix.tolist()}]}
    FIXTURE.write_text(json.dumps(fixture, separators=(",", ":")) + "\n", encoding="utf-8")
    report = {"source_commit": restored["commit"], "source_xml_sha256": MODEL_SHA,
              "keyframe": "default-pose", "thorax_quaternion_source_wxyz": source_quat.tolist(),
              "thorax_quaternion_rotated_wxyz": rotated_quat.tolist(),
              "rotated_xml_sha256": hashlib.sha256(rotated_text.encode()).hexdigest(),
              "head_matrix_source": original_matrix.tolist(),
              "head_matrix_yaw_180": rotated_matrix.tolist(),
              "head_position_source_mm": head_position.tolist(),
              "head_position_yaw_180_mm": rotated_head_position.tolist(),
              "eye_positions_source_mm": [p.tolist() for p in eye_positions],
              "eye_positions_yaw_180_mm": [p.tolist() for p in rotated_eye_positions],
              "rotation_composition_max_error": error,
              "fixture_sha256": hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
              "scope": "Source FlyMimic head orientation feeds synthetic panorama/ray fixture; root yaw is prescribed for diagnosis, no body dynamics, MaleCNS optical registration or KSP camera."}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rotation_composition_max_error": error,
                      "head_matrix_source": report["head_matrix_source"],
                      "head_matrix_yaw_180": report["head_matrix_yaw_180"]}, indent=2))


if __name__ == "__main__":
    main()
