"""Pin the author 20-ms full-field flash family and parse relative luminance."""

import hashlib
import json
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMIT = "7fa5829e37d566e02beaaa87efd6a0f1de4e48c0"
BASE = f"https://raw.githubusercontent.com/ClandininLab/L1L2-recurrent-feedback/{COMMIT}/stimulus/"
DEST = ROOT / "data/reference/pang_20ms_stimulus_family"
OUT = ROOT / "reports/pang_20ms_stimulus_family.json"
FILES = {
    "fullfield_6contrastA_LDflash20ms_Gray500ms.txt": "9334d0f72dd5288da02f63a44b8761940526bd394682c6bbe9c9d24ccb55d334",
    "fullfield_6contrastB_LDflash20ms_Gray500ms.txt": "0cc9f23720f8e8119ea2d66f2a800764ef85b8e3b6d9df1717d6fe3719bd9f12",
    "fullfield_6contrastC_LDflash20ms_Gray500ms.txt": "dd33545236d9d4a23bbfe2fa1668c116300e1ca71c96ef0758e6653f33e4dd65",
    "FullFieldFlashOntoGray.m": "a69879b3b105061002135ff0d306f04a2e70f053b0e8a8dc4d2b05d45a379a21",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    sources = {}
    configurations = {}
    for name, expected_sha in FILES.items():
        path = DEST / name
        url = BASE + name
        if not path.exists():
            with urllib.request.urlopen(url, timeout=30) as response:
                data = response.read()
            assert sha(data) == expected_sha, name
            path.write_bytes(data)
        data = path.read_bytes()
        assert sha(data) == expected_sha, name
        sources[name] = {"url": url, "sha256": expected_sha, "bytes": len(data)}
        if name.endswith(".m"):
            code = data.decode("utf-8")
            assert "FlashContrast" in code and "GrayContrast" in code and "rawStim" in code
            continue
        rows = [line.split() for line in data.decode("utf-8").splitlines() if line.strip()]
        params = {row[0]: row[1:] for row in rows}
        assert params["STIMULUS_CLASS"] == ["FullFieldFlashOntoGray"]
        assert params["EPOCHS"] == ["2"]
        flash_duration = [float(x) for x in params["FlashDuration"]]
        flash_levels = [float(x) for x in params["FlashContrast"]]
        gray_duration = float(params["GrayDuration"][0])
        gray_level = float(params["GrayContrast"][0])
        assert flash_duration == [.02, .02]
        assert gray_duration == .5 and gray_level == .5
        assert len(flash_levels) == 2 and flash_levels[0] < gray_level < flash_levels[1]
        configurations[name] = {
            "flash_duration_seconds_each": flash_duration,
            "flash_relative_projector_levels_dark_light": flash_levels,
            "gray_duration_seconds": gray_duration,
            "gray_relative_projector_level": gray_level,
            "contrast_offsets_from_gray": [value - gray_level for value in flash_levels],
        }
    assert [configurations[name]["flash_relative_projector_levels_dark_light"]
            for name in sorted(configurations)] == [[0.0, 1.0], [.25, .75], [.375, .625]]
    report = {
        "scope": "Source-defined relative projector stimulus family; not a recording-specific assignment or photon calibration",
        "repository_commit": COMMIT,
        "sources": sources,
        "configurations": configurations,
        "limits": ["The Dryad recording metadata mapping series IDs to stimulus codes and optical settings was not acquired.",
                   "Projector contrast 0..1 is not an absorbed-photon rate at the fly receptor."],
        "biological_validation": False,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: entry["contrast_offsets_from_gray"] for name, entry in configurations.items()}, indent=2))


if __name__ == "__main__":
    main()
