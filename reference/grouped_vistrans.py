"""CPU oracle for the published VisTrans per-microvillus event rule.

This is a mathematical prototype of within-tick histogram lumping, not a GPU
replacement or a biologically validated fly retina. Both simulators hold the
receptor's Vm, ns and photon rate fixed during each 0.1 ms tick, as the native
kernel does. The grouped simulator preserves the resulting count-process law
in distribution; it does not preserve per-entity XORWOW trajectories.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
import random
from typing import Iterable


State = tuple[int, int, int, int, int, int, int]
BASAL: State = (0, 50, 0, 0, 0, 0, 0)
LA = 0.5
EPS = 2e-5
DT = 1e-4

# Arrays match native/photon.cu's constant-memory reaction update table.
_FIRST_INDEX = (0, 0, 1, 2, 2, 1, 4, 3, 4, 4, 6, 5, 5, 0)
_SECOND_INDEX = (0, 0, 2, 3, 0, 0, 0, 0, 0, 6, 0, 0, 0, 0)
_FIRST_DELTA = (0, -1, -1, -1, -1, 1, 1, -1, -1, -2, -1, 1, -1, 1)
_SECOND_DELTA = (0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0)
_SELECTION_ORDER = (13, 11, 12, 10, 8, 7, 1, 6, 4, 3, 5, 2, 9)


@dataclass(frozen=True)
class Rates:
    compact: float
    branches: tuple[float, ...]


def reaction_rates(state: State, vm_mV: float, ns: float, photons_per_microvillus_s: float) -> Rates:
    """Mirror the author's compact hazard and sequential branch weights.

    Python float64 differs slightly from the source's mixed float/double CUDA
    arithmetic. This is a law oracle, not a byte-for-byte numerical oracle.
    """
    x0, x1, x2, x3, x4, x5, x6 = state
    vm = vm_mV * 1e-3
    cstar = x5 * 5.5353e-4
    i_in = x6 * 8 * max(-vm, 0.0)
    denominator = 1060 - 120 * cstar + 179.0952 * math.exp(-39.60793 * vm)
    ca = max(1.6e-4, (i_in * 690.9537 + 0.0795979 + 22 * cstar) / denominator)
    fn_tmp = cstar * 5.55555555
    fn_tmp *= fn_tmp * fn_tmp
    fn = ns * fn_tmp / (1 + fn_tmp)
    fp_tmp = ca * 3.3333333333
    fp_tmp *= fp_tmp
    fp = fp_tmp / (1 + fp_tmp)
    photon = photons_per_microvillus_s
    r11 = 54198 * ca * (0.5 - x5 * 5.5353e-4)
    r12_compact = 5.5 * x5
    r10 = 25 * (1 + 10 * fn) * x6
    r8 = 4 * (1 + 37.8 * fn) * x4
    r76 = (1444 + 1598.4 * fn) * x3
    r12_pair = (3.7 * (1 + 40 * fn) + 7.05 * x1) * x0
    r34 = (1560 - 12.6 * x3) * x2
    r5 = 3.5 * (50 - x2 - x1 - x3)
    r9 = 0.015 * (1 + 11.5 * fp) * x4 * (x4 - 1) * (25 - x6) * 0.5
    compact = photon + r11 + r12_compact + r10 + r8 + r76 + r12_pair + r34 + r5 + r9
    branch_by_code = {
        13: photon,
        11: round(30 * 1806.6) * ca * (0.5 - cstar),
        12: round(5.5 * 1806.6) * cstar,
        10: r10,
        8: r8,
        7: 144 * (1 + 11.1 * fn) * x3,
        1: 3.7 * (1 + 40 * fn) * x0,
        6: 1300 * x3,
        4: 3.0 * x2 * x3,
        3: 15.6 * x2 * (100 - x3),
        5: r5,
        2: 7.05 * x1 * x0,
        9: r9,
    }
    branches = tuple(branch_by_code[code] for code in _SELECTION_ORDER)
    if compact < 0 or not math.isfinite(compact) or any(r < 0 or not math.isfinite(r) for r in branches):
        raise ValueError(f"Invalid propensity for state {state}")
    return Rates(compact, branches)


def select_reaction(rates: Rates, unit_uniform: float) -> int:
    """Mirror the nested source selection including its 2e-5 null interval."""
    if not 0.0 <= unit_uniform <= 1.0:
        raise ValueError("Uniform draw outside [0,1]")
    residue = unit_uniform * rates.compact
    if residue <= EPS:
        return 0
    for code, branch in zip(_SELECTION_ORDER, rates.branches):
        residue -= branch
        if residue <= EPS:
            return code
    return 0


def apply_reaction(state: State, code: int) -> State:
    if code == 0:
        return state
    x = list(state)
    a = _FIRST_INDEX[code]
    x[a] += _FIRST_DELTA[code]
    b = _SECOND_INDEX[code]
    if b:
        x[b] += _SECOND_DELTA[code]
    if any(value < 0 or value > 65535 for value in x):
        raise ValueError(f"Reaction {code} leaves uint16 state bounds: {state} -> {x}")
    return tuple(x)  # type: ignore[return-value]


def _open_uniform(rng: random.Random) -> float:
    return 1.0 - rng.random()


def _wait(rate: float, rng: random.Random) -> float:
    return -math.log(_open_uniform(rng)) / rate


def independent_tick(states: Iterable[State], vm_mV: float, ns: float,
                     photon_rate_s: float, rng: random.Random) -> list[State]:
    """Author-style independent SSA for a small CPU test population."""
    values = list(states)
    lam = photon_rate_s / len(values)
    for i, state in enumerate(values):
        rates = reaction_rates(state, vm_mV, ns, lam)
        time = _wait(LA + rates.compact, rng)
        while time <= DT:
            state = apply_reaction(state, select_reaction(rates, _open_uniform(rng)))
            rates = reaction_rates(state, vm_mV, ns, lam)
            time += _wait(LA + rates.compact, rng)
        values[i] = state
    return values


def grouped_tick(histogram: Counter[State], vm_mV: float, ns: float,
                 photon_rate_s: float, rng: random.Random) -> Counter[State]:
    """Population SSA with the same within-tick count-process law.

    This simple reference scans active groups after every event. Its purpose is
    correctness; a native implementation needs an indexed propensity tree.
    """
    counts = +histogram
    n = sum(counts.values())
    lam = photon_rate_s / n
    rates = {state: reaction_rates(state, vm_mV, ns, lam) for state in counts}
    propensity = {state: count * (LA + rates[state].compact) for state, count in counts.items()}
    total = sum(propensity.values())
    time = _wait(total, rng)
    while time <= DT:
        target = rng.random() * total
        cumulative = 0.0
        chosen = None
        for state, weight in propensity.items():
            cumulative += weight
            if target < cumulative:
                chosen = state
                break
        assert chosen is not None
        code = select_reaction(rates[chosen], _open_uniform(rng))
        changed = apply_reaction(chosen, code)
        if changed != chosen:
            counts[chosen] -= 1
            if counts[chosen] == 0:
                del counts[chosen]
                del rates[chosen]
                del propensity[chosen]
            else:
                propensity[chosen] = counts[chosen] * (LA + rates[chosen].compact)
            if changed not in counts:
                counts[changed] = 0
                rates[changed] = reaction_rates(changed, vm_mV, ns, lam)
            counts[changed] += 1
            propensity[changed] = counts[changed] * (LA + rates[changed].compact)
            total = sum(propensity.values())
        time += _wait(total, rng)
    assert sum(counts.values()) == n
    return counts
