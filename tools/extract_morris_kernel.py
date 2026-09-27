"""Extract unchanged licensed author FP64 kernel without executing author Python."""
import ast
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]

def main():
    base=ROOT/'data/reference/neurodriver_graded'
    lock=json.loads((ROOT/'reports/neurodriver_graded_sources.json').read_text())
    for e in lock['files']:
        if hashlib.sha256((base/e['path']).read_bytes()).hexdigest()!=e['sha256']:
            raise ValueError('Changed source: '+e['path'])
    source=base/'neurokernel/LPU/NDComponents/MembraneModels/MorrisLecar.py'
    tree=ast.parse(source.read_text())
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='MorrisLecar')
    fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='get_update_template')
    template=ast.literal_eval(fn.body[0].value)
    kernel=template%{k:'double' for k in set(re.findall(r'%\((.*?)\)s',template))}
    out=ROOT/'build/morris_author.cu'
    out.write_text('/*\n'+(base/'LICENSE.rst').read_text()+'\n*/\n#include <cmath>\n'+kernel)
    (ROOT/'reports/morris_kernel_source.json').write_text(json.dumps({
        'commit':lock['commit'],'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'kernel_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'scope':'Unchanged author FP64 kernel'},indent=2))

if __name__=='__main__':main()
