"""Conditional optical ceiling for the Pang et al. flash, not absorbed-photon calibration."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
H = 6.62607015e-34
C = 299792458.0
LAMBDA_M = 482e-9
RADIANCE_W_SR_M2 = 78e-3
ACCEPTANCE_FWHM_DEG = 8.23
FWHM_RAD = math.radians(ACCEPTANCE_FWHM_DEG)
SIGMA_RAD = FWHM_RAD / (2 * math.sqrt(2 * math.log(2)))
# Small-angle Gaussian integral over solid angle. This assumes a uniformly
# filled central receptive field and treats the full facet as effective pupil.
OMEGA_SR = 2 * math.pi * SIGMA_RAD**2
PHOTON_ENERGY_J = H * C / LAMBDA_M
cases = []
for facet_diameter_um in (16.0, 17.0):
    area_m2 = math.pi * (facet_diameter_um * 1e-6 / 2)**2
    photons_per_s = RADIANCE_W_SR_M2 * area_m2 * OMEGA_SR / PHOTON_ENERGY_J
    cases.append({
        "facet_diameter_um": facet_diameter_um,
        "facet_area_m2": area_m2,
        "ideal_weighted_incident_photons_per_s": photons_per_s,
        "existing_model_100k_fraction_of_ideal_incident": 100000 / photons_per_s,
    })
out = {
    "scope": "conditional optical upper ceiling for one central facet; not receptor absorption rate",
    "sources": {
        "radiance": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11769683/",
        "facet_diameter": "https://elifesciences.org/articles/26117",
        "acceptance_angle": "https://pubmed.ncbi.nlm.nih.gov/21368135/",
    },
    "radiance_W_sr_inverse_m2_inverse_at_482nm": RADIANCE_W_SR_M2,
    "facet_diameter_um_range": [16, 17],
    "female_nearly_dark_adapted_R1R6_fwhm_deg": ACCEPTANCE_FWHM_DEG,
    "gaussian_effective_solid_angle_sr": OMEGA_SR,
    "photon_energy_J": PHOTON_ENERGY_J,
    "cases": cases,
    "assumptions": [
        "Pang radiance is treated as total narrowband radiance at 482 nm; spectral convention unverified",
        "Uniform screen fills the central angular receptive field",
        "Entire geometric facet acts as a receptor's effective entrance pupil",
        "Gaussian angular response with reported FWHM; small-angle approximation",
        "100 percent optical transmission, rhabdomere capture and quantum yield for the ceiling",
    ],
    "missing_for_absorbed_flux": [
        "per-recording filter and PWM settings", "screen spectral radiance and geometry",
        "sex/adaptation matched acceptance", "effective pupil fraction, lens transmission and rhabdomere absorption",
    ],
    "calibration_status": "not calibrated; this ideal optical ceiling cannot select a model photon rate",
}
path = ROOT / "reports/pang_ideal_photon_ceiling.json"
path.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
