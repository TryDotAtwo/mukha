"""Probe the pinned original Brian2 model without editing it."""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'build/python-reference'))
import pandas as pd
import brian2 as b


def main():
    b.prefs.codegen.target = 'numpy'
    spec = importlib.util.spec_from_file_location('original_shiu', ROOT/'data/reference/shiu_2024/model.py')
    model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    results = {'brian2_version': b.__version__, 'backend': 'numpy', 'biological_replication': False}
    with tempfile.TemporaryDirectory(dir=ROOT/'build') as d:
        p = Path(d)
        pd.DataFrame(index=[10,20]).to_csv(p/'nodes.csv')
        pd.DataFrame({'Presynaptic_Index':[0], 'Postsynaptic_Index':[1],
                      'Excitatory x Connectivity':[20]}).to_parquet(p/'edges.parquet')
        for label, reset in [('original', model.default_params['eq_rst']),
                             ('remove_undefined_w_reset', 'v = v_rst; g = 0 * mV')]:
            b.start_scope()
            params = dict(model.default_params, eq_rst=reset)
            try:
                n,s,mon = model.create_model(p/'nodes.csv', p/'edges.parquet', params)
                b.Network(n,s,mon).run(1*b.ms)
                results[label] = {'runs': True, 'spike_count': int(mon.num_spikes)}
            except Exception as e:
                results[label] = {'runs': False, 'error': str(e), 'cause': repr(e.__cause__)}
    (ROOT/'reports/shiu_original_compatibility.json').write_text(json.dumps(results, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
