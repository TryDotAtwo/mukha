"""Extract public rendered README evidence; never read pairing credentials."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
PEAK_BLOB = 'f61df3ffa8c22e0ec9168fd7906ebcc38f1ed0b2'
PEAK_URL = ('https://raw.githubusercontent.com/ClandininLab/L1L2-recurrent-feedback/'
            '7fa5829e37d566e02beaaa87efd6a0f1de4e48c0/'
            'imaging-analysis/HHY_stimulusSpecificAnalysisScripts/computeFramePeaks.m')


class Readme(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.parts = []
        self.sections = 0

    def handle_starttag(self, tag, attrs):
        if tag == 'div':
            if self.depth:
                self.depth += 1
            elif dict(attrs).get('id') == 'readme-sec':
                self.depth = 1
                self.sections += 1

    def handle_endtag(self, tag):
        if self.depth and tag in ('p', 'li', 'h3', 'h4'):
            self.parts.append('\n')
        if self.depth and tag == 'div':
            self.depth -= 1

    def handle_data(self, data):
        if self.depth:
            self.parts.append(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public-html', type=Path, required=True)
    parser.add_argument('--fetch-peak-source', action='store_true')
    args = parser.parse_args()
    html = args.public_html.read_bytes()
    readme = Readme()
    readme.feed(html.decode('utf-8'))
    if readme.sections != 1 or readme.depth != 0:
        raise ValueError('Expected one complete public README section')
    lines = [' '.join(s.split()) for s in ''.join(readme.parts).splitlines()]
    lines = [s for s in lines if s]
    terms = ['Time Series ID', 'Fly ID', 'PWM', 'iResp', 'roiDataMat',
             'imFrameStartTimes', 'pStimDat', 'Out.imFrameTime', 'interpFrameRate']
    evidence = {term: [line for line in lines if term in line] for term in terms}
    if not all(evidence.values()):
        raise ValueError('Public README schema changed or incomplete')
    directory = ROOT / 'data/reference/pang_metadata_readiness'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'computeFramePeaks.m'
    if path.exists():
        code = path.read_bytes()
    elif args.fetch_peak_source:
        with urlopen(PEAK_URL, timeout=30) as response:
            code = response.read(100_000)
    else:
        raise FileNotFoundError('Use --fetch-peak-source once for public helper')
    if hashlib.sha1(f'blob {len(code)}\0'.encode() + code).hexdigest() != PEAK_BLOB:
        raise ValueError('Public peak helper blob mismatch')
    if not path.exists():
        path.write_bytes(code)
    result = {
        'public_landing_url': 'https://datadryad.org/dataset/doi:10.5061/dryad.ngf1vhj4c',
        'public_html_snapshot_sha256': hashlib.sha256(html).hexdigest(),
        'evidence_kind': 'Rendered README text from Astra 1 public landing snapshot; not downloaded README.md or workbook bytes',
        'rendered_readme_text_sha256': hashlib.sha256('\n'.join(lines).encode()).hexdigest(),
        'schema_evidence': evidence,
        'peak_helper': {'url': PEAK_URL, 'git_blob': PEAK_BLOB,
                        'sha256': hashlib.sha256(code).hexdigest(),
                        'scope': 'Static inspection: first extrema over entire supplied vector; opposite extrema over inclusive suffix'},
        'run_readiness': {'eight_processed_mean_diagnostic': True,
                          'recording_specific_physiological_comparison': False,
                          'roi_bootstrap_reconstruction': False},
        'missing_for_physiology': ['actual cohort/ROI membership', 'recording-specific stimcode/PWM/filter rows',
                                  'physical stimulus/frame alignment', 'indicator observation calibration'],
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    out = ROOT / 'reports/pang_metadata_readiness.json'
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'report': str(out), 'evidence_fields': len(evidence),
                      'physiology_ready': False, 'kernel_executed': False}))


if __name__ == '__main__':
    main()
