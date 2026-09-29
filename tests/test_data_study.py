"""verify pinned history and the development/holdout boundary."""

from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import date

from keel.data import load_bars
from keel.study import BASE_COSTS, compare, windows


class DataAndSplitTests(unittest.TestCase):
    def test_snapshot_is_contiguous_and_over_ten_years(self) -> None:
        bars = load_bars()
        self.assertEqual(len(bars), 3915)
        self.assertEqual(bars[0].day, date(2015, 9, 1))
        self.assertEqual(bars[-1].day, date(2026, 5, 20))
        self.assertEqual(bars[0].volume, 23816.39)

    def test_holdout_prices_cannot_change_development_results(self) -> None:
        bars = load_bars()
        development, held_out = windows(bars)
        self.assertEqual(bars[held_out[0]].day, date(2024, 1, 1))
        baseline = compare(bars, *development, costs=BASE_COSTS)
        changed = list(bars)
        first_holdout = held_out[0]
        changed[first_holdout] = replace(changed[first_holdout], close=changed[first_holdout].close * 2)
        perturbed = compare(changed, *development, costs=BASE_COSTS)
        self.assertEqual(baseline.strategy_metrics, perturbed.strategy_metrics)
        self.assertEqual(baseline.benchmark_metrics, perturbed.benchmark_metrics)


if __name__ == "__main__":
    unittest.main()
