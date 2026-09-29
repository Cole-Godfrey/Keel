"""independent examples for returns, fills, costs, sizing, and leakage."""

from __future__ import annotations

import math
import unittest
from datetime import date, timedelta

from keel.data import Bar
from keel.engine import Costs, Portfolio, execute_target, moving_average_target, run_backtest
from keel.metrics import DAYS_PER_YEAR, calculate


def bars_from_prices(opens: list[float], closes: list[float]) -> list[Bar]:
    first = date(2020, 1, 1)
    return [
        Bar(first + timedelta(days=index), opening, max(opening, closing), min(opening, closing), closing, 1000.0)
        for index, (opening, closing) in enumerate(zip(opens, closes))
    ]


class ExecutionTests(unittest.TestCase):
    def test_buy_sells_all_and_never_borrows(self) -> None:
        costs = Costs(fee_bps=100, slippage_bps=50)
        start = Portfolio(1000.0, 0.0)
        bought, buy = execute_target(start, 1, 100.0, costs, date(2020, 1, 1))
        self.assertIsNotNone(buy)
        self.assertEqual(buy.side, "buy")
        self.assertAlmostEqual(buy.execution_price, 100.5)
        self.assertAlmostEqual(buy.fee, buy.notional * 0.01)
        self.assertGreaterEqual(bought.cash, 0)
        self.assertLess(bought.cash, 0.000002)
        self.assertEqual(round(bought.units, 8), bought.units)
        self.assertEqual(execute_target(bought, 1, 110.0, costs, date(2020, 1, 2))[1], None)

        sold, sell = execute_target(bought, 0, 100.0, costs, date(2020, 1, 3))
        self.assertIsNotNone(sell)
        self.assertAlmostEqual(sell.execution_price, 99.5)
        self.assertAlmostEqual(sell.fee, sell.notional * 0.01)
        self.assertEqual(sold.units, 0)
        self.assertAlmostEqual(sold.cash, bought.cash + sell.notional - sell.fee)
        self.assertLess(sold.cash, 1000)

    def test_fills_use_next_open_and_charge_costs(self) -> None:
        bars = bars_from_prices([10, 10, 15, 15], [10, 20, 15, 15])
        free = run_backtest(bars, 2, 4, Costs(0, 0), fast=1, slow=2, initial_cash=100)
        costly = run_backtest(bars, 2, 4, Costs(100, 50), fast=1, slow=2, initial_cash=100)
        self.assertEqual([fill.side for fill in free.fills], ["buy", "sell"])
        self.assertEqual(free.fills[0].day, bars[2].day)
        self.assertEqual(free.fills[0].reference_price, 15)
        self.assertLess(costly.observations[-1].equity, free.observations[-1].equity)
        self.assertGreater(costly.fills[0].fee, 0)
        self.assertGreater(costly.fills[0].slippage_cost, 0)

    def test_zero_cash_cannot_create_a_position(self) -> None:
        state, fill = execute_target(Portfolio(0, 0), 1, 100, Costs(0, 0), date(2020, 1, 1))
        self.assertEqual(state, Portfolio(0, 0))
        self.assertIsNone(fill)


class ReturnsAndLeakageTests(unittest.TestCase):
    def test_return_metrics_against_hand_calculation(self) -> None:
        bars = bars_from_prices([10, 10], [11, 12])
        result = run_backtest(bars, 0, 2, Costs(0, 0), benchmark=True, initial_cash=100)
        self.assertEqual([round(row.equity, 8) for row in result.observations], [110, 120])
        self.assertAlmostEqual(result.observations[0].daily_return, 0.1)
        self.assertAlmostEqual(result.observations[1].daily_return, 120 / 110 - 1)
        metrics = calculate(result)
        self.assertAlmostEqual(metrics.cagr, 1.2 ** (DAYS_PER_YEAR / 2) - 1)
        self.assertAlmostEqual(metrics.turnover, 1.0)
        self.assertEqual(metrics.trades, 1)
        self.assertEqual(metrics.max_drawdown, 0)

    def test_max_drawdown_includes_starting_cash(self) -> None:
        bars = bars_from_prices([10, 10], [9, 8])
        result = run_backtest(bars, 0, 2, Costs(0, 0), benchmark=True, initial_cash=100)
        metrics = calculate(result)
        self.assertAlmostEqual(metrics.max_drawdown, -0.2)
        self.assertIsNone(metrics.drawdown_peak)
        self.assertEqual(metrics.drawdown_trough, bars[1].day)

    def test_current_close_cannot_trigger_current_open_trade(self) -> None:
        bars = bars_from_prices([10, 9, 9, 100], [10, 9, 100, 100])
        result = run_backtest(bars, 2, 4, Costs(0, 0), fast=1, slow=2, initial_cash=100)
        self.assertEqual([fill.day for fill in result.fills], [bars[3].day])
        self.assertEqual(result.observations[0].units, 0)
        self.assertEqual(result.fills[0].reference_price, 100)

    def test_future_prices_do_not_change_earlier_fills(self) -> None:
        original = bars_from_prices([10, 20, 30, 40, 50], [10, 20, 30, 40, 50])
        changed = list(original)
        changed[4] = Bar(changed[4].day, 900, 900, 1, 1, 1000)
        first = run_backtest(original, 2, 5, Costs(0, 0), fast=1, slow=2)
        second = run_backtest(changed, 2, 5, Costs(0, 0), fast=1, slow=2)
        self.assertEqual(first.fills[0], second.fills[0])
        self.assertEqual(first.observations[:2], second.observations[:2])

    def test_indicator_uses_exactly_prior_closes(self) -> None:
        self.assertEqual(moving_average_target([10, 9], 1, 2), 0)
        self.assertEqual(moving_average_target([10, 9, 100], 1, 2), 1)
        self.assertEqual(moving_average_target([10], 1, 2), 0)


if __name__ == "__main__":
    unittest.main()
