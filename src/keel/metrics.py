"""consistent daily performance measures for a continuously traded market."""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import date

from .engine import Backtest


DAYS_PER_YEAR = 365.2425


@dataclass(frozen=True)
class Metrics:
    cagr: float
    volatility: float
    sharpe: float
    max_drawdown: float
    drawdown_peak: date | None
    drawdown_trough: date | None
    turnover: float
    trades: int
    final_equity: float
    fees_paid: float
    slippage_paid: float


def calculate(result: Backtest) -> Metrics:
    observations = result.observations
    if not observations:
        raise ValueError("empty backtest")
    returns = [row.daily_return for row in observations]
    years = len(returns) / DAYS_PER_YEAR
    cagr = (observations[-1].equity / result.initial_cash) ** (1 / years) - 1
    daily_vol = statistics.stdev(returns) if len(returns) > 1 else 0.0
    volatility = daily_vol * math.sqrt(DAYS_PER_YEAR)
    sharpe = statistics.mean(returns) / daily_vol * math.sqrt(DAYS_PER_YEAR) if daily_vol else 0.0

    peak = result.initial_cash
    peak_day: date | None = None
    worst = 0.0
    worst_peak: date | None = None
    worst_trough: date | None = None
    for row in observations:
        if row.equity > peak:
            peak = row.equity
            peak_day = row.day
        drawdown = row.equity / peak - 1
        if drawdown < worst:
            worst = drawdown
            worst_peak = peak_day
            worst_trough = row.day

    return Metrics(
        cagr,
        volatility,
        sharpe,
        worst,
        worst_peak,
        worst_trough,
        sum(row.turnover for row in observations),
        len(result.fills),
        observations[-1].equity,
        sum(fill.fee for fill in result.fills),
        sum(fill.slippage_cost for fill in result.fills),
    )
