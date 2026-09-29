"""write dependency-free SVG equity curves."""

from __future__ import annotations

import math
from pathlib import Path

from .engine import Backtest


def write_equity_chart(path: Path, strategy: Backtest, benchmark: Backtest, title: str) -> None:
    if len(strategy.observations) != len(benchmark.observations):
        raise ValueError("equity curves must use the same dates")
    width, height = 1100, 550
    left, right, top, bottom = 85, 35, 70, 80
    plot_width, plot_height = width - left - right, height - top - bottom
    series = [strategy.observations, benchmark.observations]
    values = [math.log10(row.equity / strategy.initial_cash) for rows in series for row in rows]
    low, high = min(values), max(values)
    padding = max(0.08, (high - low) * 0.08)
    low, high = low - padding, high + padding

    def point(index: int, row) -> str:
        x = left + index / max(1, len(strategy.observations) - 1) * plot_width
        y = top + (high - math.log10(row.equity / strategy.initial_cash)) / (high - low) * plot_height
        return f"{x:.2f},{y:.2f}"

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{title}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="36" font-family="Arial,sans-serif" font-size="22" font-weight="bold">{title}</text>',
        f'<text x="{left}" y="57" font-family="Arial,sans-serif" font-size="12" fill="#555">Equity relative to $10,000, logarithmic vertical scale</text>',
    ]
    for tick in range(5):
        exponent = low + tick * (high - low) / 4
        y = top + (high - exponent) / (high - low) * plot_height
        ratio = 10**exponent
        elements.extend(
            [
                f'<line x1="{left}" y1="{y:.2f}" x2="{width-right}" y2="{y:.2f}" stroke="#ddd"/>',
                f'<text x="{left-10}" y="{y+4:.2f}" text-anchor="end" font-family="Arial,sans-serif" font-size="12">{ratio:.1f}×</text>',
            ]
        )
    colors = ("#176baf", "#d17722")
    for rows, color in zip(series, colors):
        points = " ".join(point(index, row) for index, row in enumerate(rows))
        elements.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/>')
    for index, label in ((0, "50/200 strategy"), (1, "buy and hold")):
        x = left + index * 210
        elements.append(f'<line x1="{x}" y1="{height-42}" x2="{x+30}" y2="{height-42}" stroke="{colors[index]}" stroke-width="3"/>')
        elements.append(f'<text x="{x+38}" y="{height-38}" font-family="Arial,sans-serif" font-size="14">{label}</text>')
    first = strategy.observations[0].day.isoformat()
    last = strategy.observations[-1].day.isoformat()
    elements.append(f'<text x="{left}" y="{height-65}" font-family="Arial,sans-serif" font-size="12">{first}</text>')
    elements.append(f'<text x="{width-right}" y="{height-65}" text-anchor="end" font-family="Arial,sans-serif" font-size="12">{last}</text>')
    elements.append("</svg>")
    path.write_text("\n".join(elements) + "\n")
