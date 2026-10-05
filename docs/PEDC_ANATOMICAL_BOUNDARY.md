# pedc anatomical definition and model boundary — 2026-10-05

Primary source Aso et al.2014, eLife3:e04577, DOI10.7554/eLife.04577.
Full XML obtained directly in MoLab from https://www.ebi.ac.uk/europepmc/webservices/rest/PMC4273437/fullTextXML, immutable archive before extraction.
HF primary input1b3a6bd71b528dadb92eacd2e9f8e7975481d0c8
Manifest a3889c937ac1343bb7f1296110c0874d1f3fe9a0aa2a952b5d6a76c8c9c5bac2
HF extraction49e47c32e378b9e70b077c0d48018a59e24dc71e
Manifest af283809f18558eff7ee0d6a489586833b849f6a9f6f3b37b5d272f279dd2552
Remote/tmp/fly-pedc-primary-xml-20261005, completed foregroundXoov.
Columbia PDF attempted first, HTTP403; no PDF retrieval claim.

Primary anatomical description identifies pedc as core of distal pedunculus intersecting alpha/beta KCs and innervated by one MBON and one DAN. Table1 connects PPL1-01 to gamma1pedc and PPL1-02 to gamma1. The text extraction field named page is PARAGRAPH index for XML, not printed PDF page. Duplicate contexts may appear from nested captions; do not count as independent evidence.

Implementation consequence:
- retain alpha/beta KC contacts in anatomical gamma1/pedc investigation; subtype alone cannot reject them;
- gamma-only physiology experiments cannot by themselves validate alpha/beta plasticity;
- whole PED ROI is broader than pedc and cannot define its mask;
- nearest-DAN radius alone does not define pedc without anatomy/registration evidence;
- current gamma1 atlas sampling does not cover an admitted pedc boundary.

Open task: obtain anatomical pedc registration/segmentation or fine contact-defined MBON/DAN territory and independently justify boundary; validate physiology separately by relevant KC class. All41460 original contacts remain retained. No plasticity or learning enabled.
