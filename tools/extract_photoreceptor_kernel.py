"""Extract author CUDA membrane template without importing/executing PyCUDA code."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    base = ROOT / 'data/reference/vistrans'
    lock = json.loads((ROOT / 'reports/vistrans_reference_sources.json').read_text())
    for entry in lock['files']:
        if hashlib.sha256((base / entry['path']).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Source changed: ' + entry['path'])
    source = base / 'vistrans/NDComponents/PhotoreceptorModel.py'
    tree = ast.parse(source.read_text())
    function = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'get_hh_func')
    assignment = next(x for x in function.body if isinstance(x, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'template' for t in x.targets))
    template = ast.literal_eval(assignment.value)
    kernel = template % {'type': 'double', 'fletter': ''}
    target = ROOT / 'build/photoreceptor_author_hh.cu'
    target.write_text('/*\n' + (base / 'LICENSE').read_text() + '\n*/\n#include <cmath>\n' + kernel)
    additional = []
    for function_name, variable, substitutions, output in (
        ('get_transduction_func', 'template_run', {'type': 'double', 'fletter': '', 'block_size': 128}, 'transduction'),
        ('get_sum_current_func', 'template', {'type': 'double', 'block_size': 256}, 'current'),
        ('get_update_ns_func', 'template', {'type': 'double', 'fletter': ''}, 'adaptation'),
    ):
        fn = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == function_name)
        value = next(x.value for x in fn.body if isinstance(x, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == variable for t in x.targets))
        body = ast.literal_eval(value) % substitutions
        destination = ROOT / f'build/photoreceptor_author_{output}.cu'
        destination.write_text('/*\n' + (base / 'LICENSE').read_text() + '\n*/\n#include <cuda_runtime.h>\n#include <cmath>\nusing ushort = unsigned short;\nstatic_assert(sizeof(ushort)==2);\n' + body)
        additional.append({'function': function_name, 'template_variable': variable,
                           'output': str(destination.relative_to(ROOT)),
                           'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()})
    report = {'scope': 'Unmodified author FP64 membrane kernel, extracted only; not full phototransduction',
              'commit': lock['commit'], 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'kernel_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
              'output': str(target.relative_to(ROOT)), 'source_function': 'get_hh_func',
              'executed': False, 'additional_kernels': additional,
              'input': 'summed current, not RGB or photon rate',
              'output_variables': ['V', 'sa', 'si', 'dra', 'dri', 'nov'],
              'time_contract': 'ddt in seconds; kernel multiplies by 1000; author uses 10 membrane substeps per transduction step',
              'missing': ['stochastic microvillus cascade', 'summed TRP current', 'feedback ns',
                          'graded synaptic coupling', 'independent numerical and biological validation']}
    (ROOT / 'reports/photoreceptor_kernel_extraction.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
