"""Measure source FlyMimic left-front tarsus surface before pad placement."""
import json

import numpy as np
from flymimic_public_model import ROOT, MODEL_SHA, load_model, mj

OUT = ROOT / "reports/flymimic_foot_geometry_local.json"


def world_vertices(model, data, geom_id):
    mesh_id = int(model.geom_dataid[geom_id])
    start, count = model.mesh_vertadr[mesh_id], model.mesh_vertnum[mesh_id]
    vertices = np.asarray(model.mesh_vert[start:start + count], dtype=np.float64)
    rotation = np.asarray(data.geom_xmat[geom_id], dtype=np.float64).reshape(3, 3)
    position = np.asarray(data.geom_xpos[geom_id], dtype=np.float64)
    return vertices @ rotation.T + position


def bounds(vertices):
    return {"minimum_mm": vertices.min(axis=0).tolist(),
            "maximum_mm": vertices.max(axis=0).tolist()}


def main():
    model, restored = load_model()
    foot_id = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "LFTarsus5_geom")
    assert foot_id >= 0 and model.geom_type[foot_id] == mj.mjtGeom.mjGEOM_MESH
    data = mj.MjData(model)
    mj.mj_resetData(model, data)
    mj.mj_forward(model, data)
    neutral_vertices = world_vertices(model, data, foot_id)
    neutral = bounds(neutral_vertices)
    for _ in range(20000):
        data.ctrl[:] = 0.0001
        mj.mj_step(model, data)
    assert not any(warning.number for warning in data.warning)
    relaxed_vertices = world_vertices(model, data, foot_id)
    relaxed = bounds(relaxed_vertices)
    report = {
        "source_commit": restored["commit"], "source_xml_sha256": MODEL_SHA,
        "mujoco_version": mj.__version__, "geom": "LFTarsus5_geom",
        "vertex_count": len(neutral_vertices), "neutral_world_bounds": neutral,
        "relaxed_world_bounds": relaxed, "relax_steps": 20000,
        "relax_time_s": data.time, "background_muscle_command": 0.0001,
        "maximum_absolute_joint_speed_after_relax_model_units_per_s": float(np.max(np.abs(data.qvel))),
        "matches_prior_neutral_y_bounds_within_1e_5_mm": (
            abs(neutral["minimum_mm"][1] - 0.286297) < 1e-5
            and abs(neutral["maximum_mm"][1] - 0.339346) < 1e-5
        ),
        "scope": "World-space source mesh surface for a future passive pad; no contact or neural control.",
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
