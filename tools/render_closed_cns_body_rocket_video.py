"""Render a synchronized diagnostic clip from exact saved simulation states.

The clip is not a KSP landing, training run, or biological validation.
"""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from flymimic_public_model import ROOT, load_model, mj
from probe_flymimic_passive_throttle import modified_xml


CAPTURE = ROOT / "data/derived/closed_cns_body_rocket_capture_v1/frames.npz"
CAPTURE_REPORT = ROOT / "reports/closed_cns_body_rocket_capture.json"
SOURCE = ROOT / "data/derived/closed_cns_body_rocket_checkpoint_v1/trace.npz"
SOURCE_REPORT = ROOT / "reports/closed_cns_body_rocket_checkpoint.json"
OUT = ROOT / "data/derived/closed_cns_body_rocket_video_v1"
REPORT = ROOT / "reports/closed_cns_body_rocket_video.json"
FPS = 25
WIDTH, HEIGHT = 768, 384


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compose_video(path, model, body_states, ticks, traces, events, camera):
    renderer = mj.Renderer(model, HEIGHT, HEIGHT)
    data = mj.MjData(model)
    font = ImageFont.load_default(size=16)
    raw_hash = hashlib.sha256()
    preview = None
    with imageio.get_writer(path, format="FFMPEG", mode="I", fps=FPS,
                            codec="libx264", pixelformat="yuv420p",
                            macro_block_size=16, ffmpeg_log_level="error",
                            output_params=["-metadata", "creation_time=",
                                           "-movflags", "+faststart"]) as writer:
        for i, tick in enumerate(ticks):
            mj.mj_setState(model, data, body_states[i], mj.mjtState.mjSTATE_INTEGRATION)
            mj.mj_forward(model, data)
            renderer.update_scene(data, camera=camera)
            frame = renderer.render().copy()
            rgb = Image.new("RGB", (WIDTH, HEIGHT), (15, 20, 27))
            rgb.paste(Image.fromarray(frame), (0, 0))
            draw = ImageDraw.Draw(rgb)
            sample = traces[int(tick) - 1]
            event_count = int(np.searchsorted(events[:, 0], tick, side="left"))
            lines = [
                "MaleCNS / FlyMimic / rocket",
                "DIAGNOSTIC REPLAY",
                f"simulation time: {tick * .1:6.1f} ms",
                f"neural events: {event_count:4d}",
                f"motor spike, last tick: {int(sample[6])}",
                f"pad contact, step start: {int(sample[5])}",
                f"slider: {sample[1]:.6f} mm",
                f"throttle: {min(1.0, max(0.0, sample[9] / .3)):.5f}",
                f"rocket altitude: {sample[11]:.5f} m",
                f"rocket velocity: {sample[12]:.6f} m/s",
                f"cabin accel: {sample[8]:.3f} mm/s2",
                "playback 40x slower than simulation",
            ]
            y = 16
            for line in lines:
                draw.text((HEIGHT + 15, y), line, fill=(225, 231, 239), font=font)
                y += 28
            array = np.asarray(rgb)
            raw_hash.update(array.tobytes())
            writer.append_data(array)
            if i == 49:
                preview = array.copy()
    renderer.close()
    return raw_hash.hexdigest(), preview


def main(verify=False):
    capture_report = json.loads(CAPTURE_REPORT.read_text(encoding="utf-8"))
    source_report = json.loads(SOURCE_REPORT.read_text(encoding="utf-8"))
    assert sha(CAPTURE) == capture_report["frame_states_sha256"]
    assert sha(SOURCE) == source_report["files"]["trace.npz"]
    assert capture_report["closed_report_sha256"] == sha(SOURCE_REPORT)
    with np.load(CAPTURE) as frames:
        ticks = frames["tick"].copy()
        body_states = frames["body_state"].copy()
        rocket_states = frames["rocket_state"].copy()
    with np.load(SOURCE) as source:
        traces = source["continuous"].copy()
        events = np.vstack((source["prefix_events"], source["tail_events"]))
    assert len(ticks) == len(body_states) == len(rocket_states) == 100
    assert traces.shape == (1000, 15)
    assert np.array_equal(ticks, np.arange(10, 1001, 10))
    assert np.array_equal(rocket_states[:, :5], traces[ticks - 1, 10:15])
    pad = json.loads((ROOT / "reports/flymimic_keyframe_contact_local.json").read_text(
        encoding="utf-8"))["geometry"]["keyframe_passive_2s"]["positive_x_pad_center_mm"]
    xml = modified_xml(pad, True, "+1 0 0")
    assert hashlib.sha256(xml.encode()).hexdigest() == source_report["body_model_xml_sha256"]
    model, _ = load_model(xml)
    camera = mj.MjvCamera()
    camera.type = mj.mjtCamera.mjCAMERA_FREE
    camera.lookat[:] = [pad[0], pad[1], pad[2] + .8]
    camera.distance = 5.5
    camera.azimuth = 145
    camera.elevation = -15
    config = {"width": WIDTH, "height": HEIGHT, "fps": FPS,
              "frame_step_ticks": 10, "playback_slowdown": 40,
              "camera": {"lookat": camera.lookat.tolist(), "distance": camera.distance,
                         "azimuth": camera.azimuth, "elevation": camera.elevation},
              "mujoco_version": mj.__version__, "imageio_version": imageio.__version__
              if hasattr(imageio, "__version__") else "imageio.v2"}
    if verify:
        prior = json.loads(REPORT.read_text(encoding="utf-8"))
        assert prior["capture_sha256"] == sha(CAPTURE)
        assert prior["source_trace_sha256"] == sha(SOURCE)
        assert prior["config"] == config
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "verify.mp4"
            raw, _ = compose_video(path, model, body_states, ticks, traces,
                                   events, camera)
            assert raw == prior["uncompressed_frames_sha256"]
            assert sha(path) == prior["mp4_sha256"]
        print(json.dumps({"video_byte_exact_on_rerender": True}, indent=2))
        return
    assert not OUT.exists() and not REPORT.exists()
    OUT.mkdir(parents=True)
    movie = OUT / "diagnostic.mp4"
    raw, preview = compose_video(movie, model, body_states, ticks, traces,
                                 events, camera)
    preview_path = OUT / "frame_0050.png"
    Image.fromarray(preview).save(preview_path)
    with imageio.get_reader(movie) as reader:
        decoded_count = sum(1 for _ in reader)
    assert decoded_count == 100
    report = {"scope": "Synchronized diagnostic FlyMimic/CNS/radial-rocket clip; not KSP landing video",
              "capture_sha256": sha(CAPTURE), "source_trace_sha256": sha(SOURCE),
              "source_report_sha256": sha(SOURCE_REPORT),
              "config": config, "frame_count": decoded_count,
              "first_simulation_time_ms": float(ticks[0] * .1),
              "last_simulation_time_ms": float(ticks[-1] * .1),
              "video_duration_s": decoded_count / FPS,
              "uncompressed_frames_sha256": raw,
              "mp4_sha256": sha(movie), "preview_sha256": sha(preview_path),
              "biological_validation": False,
              "limits": ["Artificial four-cell sensory encoder and hypothetical motor-muscle map",
                         "Radial diagnostic rocket, not KSP or a trained landing",
                         "Sampled contact refers to physics step start, while body pose is after integration"]}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("frame_count", "video_duration_s",
                      "mp4_sha256")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    main(args.verify)
