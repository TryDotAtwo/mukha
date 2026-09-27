"""Small CPU checks for a grouped VisTrans count-process prototype."""
from collections import Counter
import random

from reference.grouped_vistrans import (
    BASAL, DT, LA, apply_reaction, grouped_tick, independent_tick,
    reaction_rates, select_reaction,
)


def test_source_basal_hazard_includes_author_la():
    rates = reaction_rates(BASAL, -56.0, 1.0, 50_000 / 30_000)
    assert rates.compact > 0
    assert LA + rates.compact > rates.compact
    assert (LA + rates.compact) * DT > 0


def test_source_reaction_selection_and_table():
    rates = reaction_rates(BASAL, -56.0, 1.0, 50_000 / 30_000)
    assert select_reaction(rates, 0.0) == 0
    assert select_reaction(rates, 0.5 / rates.compact) == 13
    assert apply_reaction(BASAL, 13) == (1, 50, 0, 0, 0, 0, 0)
    assert apply_reaction(BASAL, 11) == (0, 50, 0, 0, 0, 1, 0)


def test_grouped_and_individual_conserve_microvilli():
    count = 64
    individual = [BASAL] * count
    grouped = Counter({BASAL: count})
    individual_rng = random.Random(19503)
    grouped_rng = random.Random(19504)
    for _ in range(100):
        individual = independent_tick(individual, -56.0, 1.0, 2_000., individual_rng)
        grouped = grouped_tick(grouped, -56.0, 1.0, 2_000., grouped_rng)
        assert len(individual) == count
        assert sum(grouped.values()) == count
        assert all(value > 0 for value in grouped.values())
        assert all(all(0 <= x <= 65535 for x in state) for state in grouped)
