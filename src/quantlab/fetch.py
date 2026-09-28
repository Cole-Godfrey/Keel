"""import a licensed Bitstamp BTC/USD daily snapshot from CryptoDataDownload."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import tempfile
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .data import DATA_PATH, META_PATH


SOURCE_URL = "https://www.cryptodatadownload.com/cdd/Bitstamp_BTCUSD_d.csv"
LICENSE_URL = "https://creativecommons.org/licenses/by-nc-sa/4.0/"
START = date(2015, 9, 1)
END = date(2026, 5, 21)
COLUMNS = ["unix", "date", "symbol", "open", "high", "low", "close", "Volume BTC", "Volume USD"]


def import_snapshot(raw_path: Path, output: Path = DATA_PATH, meta: Path = META_PATH) -> None:
    if output.exists() or meta.exists():
        raise FileExistsError("snapshot already exists; choose new output paths")

    with raw_path.open(newline="") as handle:
        attribution = handle.readline().strip()
        reader = csv.DictReader(handle)
        if "CryptoDataDownload" not in attribution or reader.fieldnames != COLUMNS:
            raise ValueError("unexpected source format or attribution")
        candles: dict[date, tuple[str, str, str, str, str]] = {}
        volume_columns_reversed = 0
        for row in reader:
            day = date.fromisoformat(row["date"][:10])
            if not START <= day < END:
                continue
            timestamp_day = datetime.fromtimestamp(int(row["unix"]), tz=timezone.utc).date()
            if row["symbol"] != "BTC/USD" or timestamp_day != day or row["date"][11:] != "00:00:00":
                raise ValueError(f"invalid source identity or UTC day on {day}")
            if day in candles:
                raise ValueError(f"duplicate daily candle on {day}")
            opening, high, low, close = (float(row[key]) for key in ("open", "high", "low", "close"))
            btc_column, usd_column = float(row["Volume BTC"]), float(row["Volume USD"])
            values = (opening, high, low, close, btc_column, usd_column)
            if not all(math.isfinite(value) and value > 0 for value in values):
                raise ValueError(f"invalid price or volume on {day}")
            if low > min(opening, close) or high < max(opening, close):
                raise ValueError(f"invalid OHLC range on {day}")
            # older source rows have the BTC and USD volume headings reversed.
            btc_volume = min(btc_column, usd_column)
            implied_price = max(btc_column, usd_column) / btc_volume
            if not low * 0.98 <= implied_price <= high * 1.02:
                raise ValueError(f"volume units cannot be verified on {day}")
            if btc_column > usd_column:
                volume_columns_reversed += 1
            volume = row["Volume BTC"] if btc_column < usd_column else row["Volume USD"]
            candles[day] = (row["open"], row["high"], row["low"], row["close"], volume)

    expected = (END - START).days
    if len(candles) != expected or any(START + timedelta(days=index) not in candles for index in range(expected)):
        raise ValueError("source has a missing daily candle in the selected window")

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["date", "open", "high", "low", "close", "volume"])
        for day in sorted(candles):
            writer.writerow([day.isoformat(), *candles[day]])
    metadata = {
        "source": SOURCE_URL,
        "source_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        "source_license": LICENSE_URL,
        "product": "Bitstamp BTC/USD",
        "granularity_seconds": 86400,
        "start_inclusive": START.isoformat(),
        "end_exclusive": END.isoformat(),
        "rows": expected,
        "reversed_volume_columns": volume_columns_reversed,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }
    meta.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-file", type=Path)
    parser.add_argument("--output", type=Path, default=DATA_PATH)
    parser.add_argument("--meta", type=Path, default=META_PATH)
    args = parser.parse_args()
    if args.source_file is None:
        request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "quantlab-research/0.1"})
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
        with tempfile.NamedTemporaryFile() as handle:
            handle.write(raw)
            handle.flush()
            import_snapshot(Path(handle.name), args.output, args.meta)
    else:
        import_snapshot(args.source_file, args.output, args.meta)


if __name__ == "__main__":
    main()
