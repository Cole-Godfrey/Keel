"""read and validate daily BTC-USD candles."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "btc_usd_bitstamp_daily.csv"
META_PATH = ROOT / "data" / "btc_usd_bitstamp_daily.json"


@dataclass(frozen=True)
class Bar:
    day: date
    open: float
    high: float
    low: float
    close: float
    volume: float


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_bars(path: Path = DATA_PATH, metadata_path: Path | None = META_PATH) -> list[Bar]:
    if metadata_path is not None:
        metadata = json.loads(metadata_path.read_text())
        if sha256_file(path) != metadata["sha256"]:
            raise ValueError("data checksum differs from the pinned snapshot")

    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["date", "open", "high", "low", "close", "volume"]:
            raise ValueError("unexpected candle columns")
        bars = [
            Bar(date.fromisoformat(row["date"]), *(float(row[key]) for key in reader.fieldnames[1:]))
            for row in reader
        ]

    if len(bars) < 3653:
        raise ValueError("less than ten years of daily data")
    for index, bar in enumerate(bars):
        values = (bar.open, bar.high, bar.low, bar.close, bar.volume)
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"non-finite candle on {bar.day}")
        if min(bar.open, bar.high, bar.low, bar.close) <= 0 or bar.volume <= 0:
            raise ValueError(f"non-positive candle on {bar.day}")
        if bar.low > min(bar.open, bar.close) or bar.high < max(bar.open, bar.close):
            raise ValueError(f"invalid OHLC range on {bar.day}")
        if index and bar.day != bars[index - 1].day + timedelta(days=1):
            raise ValueError(f"missing or duplicate daily candle at {bar.day}")
    if (bars[-1].day - bars[0].day).days < 3652:
        raise ValueError("history spans less than ten years")
    return bars
