"""generate the deterministic development and held-out reports."""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

from .chart import write_equity_chart
from .data import META_PATH, ROOT, load_bars
from .metrics import Metrics
from .protocol import verify_seal
from .study import (
    BASE_COSTS, DEV_END, FAST, INITIAL_CASH, SLOW, STRESS_COSTS, WARMUP_DAYS,
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
    cagr_gap = (strategy.cagr - benchmark.cagr) * 100
    gap_description = f"{abs(cagr_gap):.2f} percentage points {'higher' if cagr_gap >= 0 else 'lower'}"
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
            f"From {peak} to {trough}, the strategy's close-to-close drawdown reached "
            f"{_percent(strategy.max_drawdown)}. Its CAGR was {gap_description} than buy and hold.",
            "",
        ]
    )


def _shared_intro(metadata: dict) -> list[str]:
    last_day = (date.fromisoformat(metadata["end_exclusive"]) - timedelta(days=1)).isoformat()
    return [
        "# Keel: BTC/USD daily moving-average study",
        "",
        "## Data and reproduction",
        "",
        "Run `./run.sh` from a clone with Python 3.10+ and Git. It runs the standard-library "
        "tests and rebuilds this report, the CSV equity curves, and the SVG charts offline.",
        "",
        f"The snapshot has {metadata['rows']:,} consecutive UTC daily BTC/USD OHLCV bars from "
        f"{metadata['start_inclusive']} through {last_day}. Its SHA-256 is `{metadata['sha256']}`. "
        "It comes from [CryptoDataDownload's Bitstamp daily file]"
        "(https://www.cryptodatadownload.com/data/bitstamp/), licensed under "
        "[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).",
        "",
        f"In {metadata['reversed_volume_columns']} older rows, the source reverses its BTC and USD "
        "volume headings. The importer checked each row's implied price against its OHLC range before "
        "choosing BTC volume. The source also has a partial 2026-05-21 bar and no 2026-05-22 bar. "
        "The loader rejects gaps, duplicates, invalid prices, and checksum changes. "
        "`python3 -m keel.fetch` contains the acquisition code; the included snapshot is the "
        "reproducible input. See `DATA_LICENSE.md` for attribution.",
        "",
        "## Rules and assumptions",
        "",
        f"Both portfolios start with ${INITIAL_CASH:,.0f} cash, with no leverage, shorting, or interest. "
        f"After each completed UTC daily bar, the strategy compares the trailing {FAST}- and "
        f"{SLOW}-day closing-price averages. It holds BTC when the faster average is strictly above "
        "the slower one. A changed target fills at the *next* bar's open. A buy uses all available "
        "cash and rounds BTC down to 0.00000001; a flat signal sells the whole position. "
        "The benchmark buys at the first evaluation open and holds. Both pay the same assumed costs.",
        "",
        f"Base costs per side are {BASE_COSTS.fee_bps:g} basis points in fees and "
        f"{BASE_COSTS.slippage_bps:g} basis points of adverse slippage. The stress run uses "
        f"{STRESS_COSTS.fee_bps:g} and {STRESS_COSTS.slippage_bps:g} basis points. These are "
        "research assumptions, not a current Bitstamp fee quote. Equity is marked at each daily "
        "close, and the final position is left open. Entry-day simple returns include the move "
        "from the open to the close.",
        "",
        "CAGR uses 365.2425 days per year. Volatility is the sample standard deviation of daily "
        "returns times the square root of 365.2425. Sharpe assumes a zero risk-free rate. Maximum "
        "drawdown includes starting equity. Turnover sums executed notional divided by the "
        "preceding close's equity. Each completed buy or sell counts as a trade.",
        "",
        f"The first {WARMUP_DAYS} bars supply indicator history. Development ends before {DEV_END}. "
        "The out-of-sample portfolio starts with fresh cash on that date, although its signal "
        "can use completed closes from the development period.",
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
            "Each run uses the same development dates and starts with fresh cash. "
            "Only the sealed 50/200 setting with base costs went into the holdout.",
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
            f"With higher assumed costs, the development strategy's CAGR fell from "
            f"{_percent(dev.strategy_metrics.cagr)} to "
            f"{_percent(next(row[3].cagr for row in sensitivity if row[0] == FAST and row[1] == SLOW and row[2] == STRESS_COSTS))}. "
            "The nearby moving-average lengths in the table give different results.",
            "",
            "Daily bars cannot capture intraday order depth, outages, or actual fills. The backtest "
            "models execution at the open; paper trading uses a later live quote with the same "
            "signal, position-sizing, and accounting functions. One BTC/USD venue says little about "
            "other markets or future conditions. The model excludes taxes, custody risk, funding "
            "costs, and any spread beyond the assumed slippage. No live capital was used. A previous "
            "private Coinbase study covered some of the same BTC dates, so the Bitstamp holdout "
            "was not fully blind across venues.",
            "",
            "## Protocol and operational validation",
            "",
            f"The original research code and data were sealed at {protocol['sealed_at_utc']} "
            f"from development commit `{protocol['development_commit']}`. The report checks that "
            "seal and the Keel rename manifest before running the holdout. The data, strategy, "
            "accounting, metrics, and chart code retain their original sealed hashes. Among sealed "
            "files, the rename changed report wording and the paper feed's User-Agent. The paper trial needs 30 "
            "consecutive daily ledger entries and a clean reconciliation before it is complete.",
            "",
        ]
    )
    output = REPORT_DIR / "RESEARCH.md"
    output.write_text("\n".join(lines).rstrip() + "\n")
    return output
