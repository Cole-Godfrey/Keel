"""generate the deterministic development and held-out reports."""

from __future__ import annotations

import csv
from pathlib import Path

from .chart import write_equity_chart
from .data import META_PATH, ROOT, load_bars
from .metrics import Metrics
from .protocol import verify_seal
from .study import (
    BASE_COSTS, DEV_END, FAST, INITIAL_CASH, SLOW, STRESS_COSTS,
    compare, development_sensitivity, windows,
)


REPORT_DIR = ROOT / "report"


def _percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def _metrics_row(name: str, metric: Metrics) -> str:
    return (
        f"| {name} | {_percent(metric.cagr)} | {_percent(metric.volatility)} | "
        f"{metric.sharpe:.2f} | {_percent(metric.max_drawdown)} | "
        f"{metric.turnover:.2f}× | {metric.trades} | ${metric.final_equity:,.2f} |"
    )


def _write_equity_csv(path: Path, comparison) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["date", "strategy_equity_usd", "buy_hold_equity_usd"])
        for strategy, benchmark in zip(comparison.strategy.observations, comparison.benchmark.observations):
            writer.writerow([strategy.day.isoformat(), f"{strategy.equity:.8f}", f"{benchmark.equity:.8f}"])


def _window_section(name: str, comparison, image_name: str) -> str:
    strategy = comparison.strategy_metrics
    benchmark = comparison.benchmark_metrics
    first = comparison.strategy.observations[0].day
    last = comparison.strategy.observations[-1].day
    peak = strategy.drawdown_peak.isoformat() if strategy.drawdown_peak else "inception"
    trough = strategy.drawdown_trough.isoformat() if strategy.drawdown_trough else "none"
    return "\n".join(
        [
            f"## {name} ({first} to {last})",
            "",
            "| Portfolio | CAGR | Volatility | Sharpe | Max drawdown | Turnover | Trades | Final equity |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
            _metrics_row("50/200 strategy", strategy),
            _metrics_row("Buy and hold", benchmark),
            "",
            f"![{name} equity curve]({image_name})",
            "",
            f"The strategy's deepest close-to-close drawdown was {_percent(strategy.max_drawdown)} "
            f"from {peak} to {trough}. Its CAGR difference versus buy and hold was "
            f"{(strategy.cagr - benchmark.cagr) * 100:+.2f} percentage points.",
            "",
        ]
    )


def _shared_intro(metadata: dict) -> list[str]:
    return [
        "# BTC-USD daily moving-average research",
        "",
        "## Reproduction and source",
        "",
        "Run `./run.sh` from a clone with Python 3.10+ and Git. It runs the standard-library "
        "test suite and regenerates this report, its CSV equity curves, and SVG charts without a network request.",
        "",
        f"The pinned dataset contains {metadata['rows']} consecutive UTC daily BTC-USD OHLCV bars from "
        f"{metadata['start_inclusive']} through the day before {metadata['end_exclusive']}. "
        f"SHA-256: `{metadata['sha256']}`. Source: "
        "[CryptoDataDownload's Bitstamp BTC/USD daily file](https://www.cryptodatadownload.com/data/bitstamp/), "
        "licensed [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). "
        "The source's BTC and USD volume headings are reversed in "
        f"{metadata['reversed_volume_columns']} older rows; we chose the smaller field as BTC volume "
        "only after verifying the implied USD/BTC price against each day's OHLC range. "
        "The source later contains a partial 2026-05-21 bar and no 2026-05-22 bar, so this pinned "
        "study ends on 2026-05-20. The loader rejects gaps, duplicates, invalid prices, and checksum "
        "changes. `python3 -m quantlab.fetch` documents the acquisition code; "
        "the checked-in snapshot is the reproducible input. See `DATA_LICENSE.md` for attribution.",
        "",
        "## Rules and assumptions",
        "",
        f"Start with ${INITIAL_CASH:,.0f} cash, no leverage, no shorting, and no interest. "
        f"After each completed UTC daily bar, compare its trailing {FAST}- and {SLOW}-day closing-price averages. "
        "Hold BTC only when the faster average is strictly above the slower one. "
        "Fill a changed target at the *next* bar's open. All available cash buys BTC rounded down to 0.00000001 BTC; "
        "a flat signal sells all BTC. The benchmark buys at the first evaluation open and holds. "
        "Both portfolios pay the same assumed costs.",
        "",
        f"Base costs per side: {BASE_COSTS.fee_bps:g} basis points fee plus "
        f"{BASE_COSTS.slippage_bps:g} basis points adverse slippage. Stress costs: "
        f"{STRESS_COSTS.fee_bps:g} and {STRESS_COSTS.slippage_bps:g} basis points. "
        "These are research assumptions, not a current Bitstamp fee quote. "
        "Equity is marked at the daily close; the last position is not liquidated. "
        "Daily simple returns include open-to-close P&L on entry days. "
        "CAGR uses 365.2425 days per year; volatility is sample standard deviation times its square root; "
        "Sharpe uses a zero risk-free rate; maximum drawdown includes starting equity. "
        "Turnover is the sum of executed notional divided by the preceding close's equity. "
        "Trades count completed buy or sell executions.",
        "",
        f"The first {250} bars are indicator history only. Development ends before {DEV_END}; "
        "the independent out-of-sample portfolio starts with fresh cash on that date while its signal "
        "may use earlier completed development closes.",
        "",
    ]


def generate(*, development_only: bool = False) -> Path:
    import json

    bars = load_bars()
    metadata = json.loads(META_PATH.read_text())
    development, held_out = windows(bars)
    REPORT_DIR.mkdir(exist_ok=True)
    dev = compare(bars, *development)
    sensitivity = development_sensitivity(bars, *development)
    write_equity_chart(REPORT_DIR / "equity_development.svg", dev.strategy, dev.benchmark, "Development equity")
    _write_equity_csv(REPORT_DIR / "equity_development.csv", dev)

    lines = _shared_intro(metadata)
    lines.append(_window_section("Development", dev, "equity_development.svg"))
    lines.extend(
        [
            "## Development sensitivity",
            "",
            "Each row uses the identical development dates and starts with fresh cash. "
            "Only the sealed 50/200 base-cost setting is evaluated out of sample.",
            "",
            "| Fast / slow | Fee / slippage (bps) | CAGR | Sharpe | Max drawdown | Turnover | Trades |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for fast, slow, costs, metric in sensitivity:
        lines.append(
            f"| {fast}/{slow} | {costs.fee_bps:g}/{costs.slippage_bps:g} | "
            f"{_percent(metric.cagr)} | {metric.sharpe:.2f} | {_percent(metric.max_drawdown)} | "
            f"{metric.turnover:.2f}× | {metric.trades} |"
        )
    lines.append("")

    if development_only:
        output = REPORT_DIR / "DEVELOPMENT.md"
        output.write_text("\n".join(lines).rstrip() + "\n")
        return output

    protocol = verify_seal()
    oos = compare(bars, *held_out)
    write_equity_chart(REPORT_DIR / "equity_oos.svg", oos.strategy, oos.benchmark, "Out-of-sample equity")
    _write_equity_csv(REPORT_DIR / "equity_oos.csv", oos)
    lines.append(_window_section("Out of sample", oos, "equity_oos.svg"))
    lines.extend(
        [
            "## Failure cases and limits",
            "",
            f"The development strategy's base-cost CAGR changes from "
            f"{_percent(dev.strategy_metrics.cagr)} to "
            f"{_percent(next(row[3].cagr for row in sensitivity if row[0] == FAST and row[1] == SLOW and row[2] == STRESS_COSTS))} "
            "under the higher cost assumption. Nearby average lengths in the table show how sensitive the result is "
            "to timing choices. The drawdown dates above identify observed loss episodes.",
            "",
            "Daily bars cannot represent intraday order depth, outages, or real fills. The open is a modeled "
            "execution price; paper trading uses a later live ticker observation with the same signal, "
            "position-sizing, and accounting functions. A single BTC-USD venue does not test other markets "
            "or future regimes. Taxes, custody risk, spread beyond the assumed slippage, and funding costs "
            "are excluded. No live capital was used. The same BTC period was previously evaluated "
            "on Coinbase in a private study, so this venue's holdout is not fully blind across markets.",
            "",
            "## Protocol and operational validation",
            "",
            f"Research code and data were sealed at {protocol['sealed_at_utc']} from development commit "
            f"`{protocol['development_commit']}`. The report command verifies the sealed SHA-256 manifest "
            "before computing out-of-sample results. Paper trading must accumulate 30 consecutive daily "
            "ledger entries, reconcile without differences, and complete its calendar window before "
            "the operational requirement can be marked complete.",
            "",
        ]
    )
    output = REPORT_DIR / "RESEARCH.md"
    output.write_text("\n".join(lines).rstrip() + "\n")
    return output
