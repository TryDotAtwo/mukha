"""Pin the published Pang projector method and convert radiance units."""

import hashlib
import json
import math
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
URL = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_xml/PMC11769683/unicode"
SOURCE = ROOT / "data/reference/pang_projector_method/PMC11769683_bioc.xml"
OUT = ROOT / "reports/pang_projector_radiance.json"
EXPECTED_SHA = "6c9414dc8e011687d4c515ac17f2035445252578e6172e1d851cb67e21ce0103"
PLANCK_J_S = 6.62607015e-34
LIGHT_M_S = 299792458.0


def main():
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    if not SOURCE.exists():
        with urllib.request.urlopen(URL, timeout=40) as response:
            data = response.read()
        assert hashlib.sha256(data).hexdigest() == EXPECTED_SHA
        SOURCE.write_bytes(data)
    data = SOURCE.read_bytes()
    assert hashlib.sha256(data).hexdigest() == EXPECTED_SHA
    root = ET.fromstring(data)
    passages = [passage.findtext("text") or "" for passage in root.iter("passage")]
    matches = [value for value in passages if "radiance at 482 nm was approximately 78" in value]
    assert len(matches) == 1
    method = matches[0]
    assert "300 Hz" in method and "6 bits/pixel" in method
    assert "482/18-nm bandpass filter" in method
    wavelength_nm = 482.0
    photon_j = PLANCK_J_S * LIGHT_M_S / (wavelength_nm * 1e-9)
    radiance_w_sr_m2 = 78e-3
    photons_per_s_sr_m2 = radiance_w_sr_m2 / photon_j
    report = {
        "scope": "Published projector source physics, dimensional conversion only; no individual receptor absorption estimate",
        "source_url": URL,
        "source_sha256": EXPECTED_SHA,
        "article_doi": "10.1016/j.cub.2024.11.064",
        "reported_projector": {"light_source": "DLP LightCrafter 4500 blue LED",
                               "bandpass_center_nm": 482, "bandpass_width_nm": 18,
                               "refresh_hz": 300, "pixel_levels": 64,
                               "radiance_approx_mw_per_sr_per_m2_at_482nm": 78},
        "conversion": {"assumed_monochromatic_wavelength_nm": wavelength_nm,
                       "photon_energy_j": photon_j,
                       "radiance_photons_per_s_per_sr_per_m2": photons_per_s_sr_m2,
                       "radiance_photons_per_20ms_per_sr_per_m2": photons_per_s_sr_m2 * .02,
                       "projector_frames_per_20ms": 300 * .02},
        "limits": ["The article states an approximate projector radiance, without assigning it to each recording, flash level, PWM or neutral-density setting.",
                   "This is radiance per solid angle and area, not photon arrivals or absorptions per ommatidium.",
                   "Converting to receptor photon rate requires angular acceptance, effective collecting area, transmission and quantum efficiency, plus the recording-specific optical settings."],
        "biological_validation": False,
    }
    assert math.isclose(report["conversion"]["projector_frames_per_20ms"], 6.0)
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["conversion"], indent=2))


if __name__ == "__main__":
    main()
