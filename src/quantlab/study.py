"""preregistered windows, parameters, and transaction-cost assumptions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .data import Bar
from .engine import Backtest, Costs, run_backtest
from .metrics import Metrics, calculate


DEV_END = date(2024, 1, 1)
WARMUP_DAYS = 250
INITIAL_CASH = 10_000.0
FAST = 50
SLOW = 200
BASE_COSTS = Costs(fee_bps=60, slippage_bps=10)
STRESS_COSTS = Costs(fee_bps=100, slippage_bps=30)
SENSITIVITY = ((40, 180), (40, 200), (50, 180), (50, 200), (50, 220), (60, 200), (60, 220))


@dataclass(frozen=True)
class Comparison:
    strategy: Backtest
    benchmark: Backtest
    strategy_metrics: Metrics
    benchmark_metrics: Metrics


def windows(bars: list[Bar]) -> tuple[tuple[int, int], tuple[int, int]]:
    boundary = next((index for index, bar in enumerate(bars) if bar.day >= DEV_END), None)
    if boundary is None or boundary <= WARMUP_DAYS or len(bars) - boundary < 365:
        raise ValueError("development or out-of-sample window is too short")
    return (WARMUP_DAYS, boundary), (boundary, len(bars))


def compare(
    bars: list[Bar], start: int, end: int, costs: Costs = BASE_COSTS,
    fast: int = FAST, slow: int = SLOW,
) -> Comparison:
    strategy = run_backtest(bars, start, end, costs, fast=fast, slow=slow, initial_cash=INITIAL_CASH)
    benchmark = run_backtest(bars, start, end, costs, benchmark=True, initial_cash=INITIAL_CASH)
    return Comparison(strategy, benchmark, calculate(strategy), calculate(benchmark))


def development_sensitivity(bars: list[Bar], start: int, end: int) -> list[tuple[int, int, Costs, Metrics]]:
    rows = []
    for fast, slow in SENSITIVITY:
        for costs in (BASE_COSTS, STRESS_COSTS):
            result = run_backtest(bars, start, end, costs, fast=fast, slow=slow, initial_cash=INITIAL_CASH)
            rows.append((fast, slow, costs, calculate(result)))
    return rows
