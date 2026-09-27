"""Compare sampled-model error with teacher seed-to-seed variability."""
from pathlib import Path
import json
import numpy as np


def rms(x):
    return float(np.sqrt(np.mean(np.square(x))))


def run(root=Path('/marimo/fly-project')):
    root = Path(root)
    path = root/'data/derived/photon_sampled_benchmark_v1/traces.npz'
    traces = np.load(path)
    result = {}
    for pulse in ('light', 'dark'):
        teacher = [traces[f'{pulse}_reference_{seed}'].astype(np.float64)
                   for seed in (19503, 19504, 19505)]
        mean_teacher = [x.mean(axis=1) for x in teacher]
        reference_cell_variability = [rms(teacher[i][100:] - teacher[j][100:])
                                      for i, j in ((0,1), (0,2), (1,2))]
        reference_population_variability = [rms(mean_teacher[i][100:] - mean_teacher[j][100:])
                                            for i, j in ((0,1), (0,2), (1,2))]
        candidates = {}
        for m in (256,1024,4096):
            cell = []
            population = []
            for i, seed in enumerate((19503,19504,19505)):
                cand = traces[f'{pulse}_{m}_{seed}'].astype(np.float64)
                cell.append(rms(cand[100:] - teacher[i][100:]))
                population.append(rms(cand[100:].mean(axis=1) - mean_teacher[i][100:]))
            candidates[str(m)] = {'cell_rmse_mV': cell, 'population_rmse_mV': population}
        result[pulse] = {'teacher_pairwise_cell_rmse_mV': reference_cell_variability,
                         'teacher_pairwise_population_rmse_mV': reference_population_variability,
                         'candidates': candidates}
    print('SAMPLED_NOISE_ANALYSIS', json.dumps(result), flush=True)
    (root/'data/derived/photon_sampled_benchmark_v1/noise_analysis.json').write_text(json.dumps(result,indent=2))
    return result


if __name__ == '__main__':
    run()
