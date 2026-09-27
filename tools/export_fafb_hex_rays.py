"""Export pinned other-specimen FAFB hex coordinates with measured optical rays."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build/eye-python"))
import rdata

SOURCE = ROOT / "data/reference/eyemap_2025"
REGISTRATION = ROOT / "data/derived/optical_reference/fafb_registration.csv"
OUT = ROOT / "data/derived/optical_reference/fafb_hex_rays.csv"
REPORT = ROOT / "reports/fafb_hex_ray_export.json"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    lock_path = ROOT / "reports/eyemap_reference_sources.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    for item in lock["files"]:
        path = SOURCE / item["path"]
        assert path.stat().st_size == item["bytes"] and sha(path) == item["sha256"]
    prior = json.loads((ROOT / "reports/eye_registration_audit.json").read_text(encoding="utf-8"))
    assert sha(REGISTRATION) == prior["output_sha256"]
    eye = rdata.read_rda(SOURCE / "data/eyemap.RData")
    lens_grid = np.asarray(eye["lens_ixy"])
    assert lens_grid.shape == (852, 3) and np.isfinite(lens_grid).all()
    assert np.equal(lens_grid, np.floor(lens_grid)).all()
    lens_grid = lens_grid.astype(np.int64)
    assert np.array_equal(np.sort(lens_grid[:, 0]), np.arange(1, 853))
    assert len(set(map(tuple, lens_grid[:, 1:]))) == 852
    table = pd.DataFrame(lens_grid, columns=["right_lens_row_1based", "fafb_hex_x", "fafb_hex_y"])
    rays = pd.read_csv(REGISTRATION)
    assert len(rays) == 778 and rays.right_lens_row_1based.is_unique
    joined = rays.merge(table, on="right_lens_row_1based", validate="one_to_one")
    assert len(joined) == len(rays)
    assert joined[["ray_forward", "ray_left", "ray_up"]].notna().all().all()
    assert joined.malecns_body_id.isna().all() and (~joined.enabled.astype(bool)).all()
    output = joined[["author_Mi1_row_1based", "right_lens_row_1based",
                     "fafb_hex_x", "fafb_hex_y", "global_lens_row_1based",
                     "global_cone_row_1based", "ray_forward", "ray_left", "ray_up"]]
    output.to_csv(OUT, index=False, float_format="%.17g")
    report = {
        "scope": "Measured other-specimen microCT optical rays aligned to FAFB hex grid via published Mi1/lens map; no MaleCNS mapping",
        "source_lock_sha256": sha(lock_path),
        "source_eyemap_rdata_sha256": sha(SOURCE / "data/eyemap.RData"),
        "prior_fafb_registration_sha256": sha(REGISTRATION),
        "right_lenses_with_hex": len(table),
        "matched_fafb_hex_rays": len(output),
        "unmatched_right_lenses": len(table) - len(output),
        "fafb_hex_bounds": {axis: {"min": int(table[axis].min()), "max": int(table[axis].max())}
                             for axis in ("fafb_hex_x", "fafb_hex_y")},
        "output_csv_sha256": sha(OUT),
        "male_cns_body_ids_assigned": 0,
        "enabled": False,
        "limitation": "FAFB and MaleCNS are different specimens with different hex origins; no cross-dataset landmarks or body rotation were validated.",
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("right_lenses_with_hex",
          "matched_fafb_hex_rays", "unmatched_right_lenses", "fafb_hex_bounds")}, indent=2))


if __name__ == "__main__":
    main()

