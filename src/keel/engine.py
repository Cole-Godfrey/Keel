"""shared signal, cash accounting, and next-bar backtest execution."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import date
from typing import Sequence

from .data import Bar


@dataclass(frozen=True)
class Costs:
    fee_bps: float
    slippage_bps: float

    def __post_init__(self) -> None:
        if not all(math.isfinite(value) and value >= 0 for value in (self.fee_bps, self.slippage_bps)):
            raise ValueError("costs must be finite and nonnegative")


@dataclass(frozen=True)
class Portfolio:
    cash: float
    units: float

    def equity(self, price: float) -> float:
        return self.cash + self.units * price


@dataclass(frozen=True)
class Fill:
    day: date
    side: str
    units: float
    reference_price: float
    execution_price: float
    notional: float
    fee: float
    slippage_cost: float
    cash_after: float
    units_after: float

    def to_json(self) -> dict:
        result = asdict(self)
        result["day"] = self.day.isoformat()
        return result


@dataclass(frozen=True)
class Observation:
    day: date
    equity: float
    daily_return: float
    cash: float
    units: float
    turnover: float


@dataclass(frozen=True)
class Backtest:
    observations: list[Observation]
    fills: list[Fill]
    initial_cash: float


def moving_average_target(closes: Sequence[float], fast: int, slow: int) -> int:
    if not 1 <= fast < slow:
        raise ValueError("require 1 <= fast < slow")
    if len(closes) < slow:
        return 0
    fast_mean = sum(closes[-fast:]) / fast
    slow_mean = sum(closes[-slow:]) / slow
    return int(fast_mean > slow_mean)


def execute_target(
    portfolio: Portfolio,
    target: int,
    reference_price: float,
    costs: Costs,
    day: date,
) -> tuple[Portfolio, Fill | None]:
    if target not in (0, 1):
        raise ValueError("target must be flat or fully invested")
    if not math.isfinite(reference_price) or reference_price <= 0:
        raise ValueError("reference price must be positive and finite")
    if not all(math.isfinite(x) and x >= 0 for x in (portfolio.cash, portfolio.units)):
        raise ValueError("portfolio must be cash funded and long only")

    if target == 1 and portfolio.units == 0:
        execution_price = reference_price * (1 + costs.slippage_bps / 10_000)
        # round down to the exchange's eight decimal BTC unit precision.
        units = math.floor(portfolio.cash / (execution_price * (1 + costs.fee_bps / 10_000)) * 1e8) / 1e8
        if units == 0:
            return portfolio, None
        notional = units * execution_price
        fee = notional * costs.fee_bps / 10_000
        cash_after = portfolio.cash - notional - fee
        if cash_after < -1e-8:
            raise ArithmeticError("buy spent more cash than available")
        updated = Portfolio(max(0.0, cash_after), units)
        fill = Fill(day, "buy", units, reference_price, execution_price, notional, fee,
                    units * (execution_price - reference_price), updated.cash, updated.units)
        return updated, fill

    if target == 0 and portfolio.units > 0:
        execution_price = reference_price * (1 - costs.slippage_bps / 10_000)
        if execution_price <= 0:
            raise ValueError("sell slippage makes price nonpositive")
        units = portfolio.units
        notional = units * execution_price
        fee = notional * costs.fee_bps / 10_000
        updated = Portfolio(portfolio.cash + notional - fee, 0.0)
        fill = Fill(day, "sell", units, reference_price, execution_price, notional, fee,
                    units * (reference_price - execution_price), updated.cash, updated.units)
        return updated, fill

    return portfolio, None


def run_backtest(
    bars: Sequence[Bar],
    start: int,
    end: int,
    costs: Costs,
    *,
    fast: int = 50,
    slow: int = 200,
    benchmark: bool = False,
    initial_cash: float = 10_000.0,
) -> Backtest:
    if not 0 <= start < end <= len(bars):
        raise ValueError("invalid evaluation window")
    if start < slow and not benchmark:
        raise ValueError("evaluation starts before full signal history")
    if not math.isfinite(initial_cash) or initial_cash <= 0:
        raise ValueError("initial cash must be positive")

    portfolio = Portfolio(initial_cash, 0.0)
    observations: list[Observation] = []
    fills: list[Fill] = []
    prior_equity = initial_cash
    closes = [bar.close for bar in bars]

    for index in range(start, end):
        bar = bars[index]
        # the signal uses closes through yesterday; today's open is the first fill price.
        target = 1 if benchmark else moving_average_target(closes[:index], fast, slow)
        portfolio, fill = execute_target(portfolio, target, bar.open, costs, bar.day)
        traded = 0.0
        if fill is not None:
            fills.append(fill)
            traded = fill.notional / prior_equity
        equity = portfolio.equity(bar.close)
        if not math.isfinite(equity) or equity <= 0:
            raise ArithmeticError(f"invalid equity on {bar.day}")
        observations.append(
            Observation(bar.day, equity, equity / prior_equity - 1, portfolio.cash, portfolio.units, traded)
        )
        prior_equity = equity
    return Backtest(observations, fills, initial_cash)
