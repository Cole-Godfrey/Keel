"""append-only daily paper execution with deterministic reconciliation."""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import urllib.request
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from .data import ROOT
from .engine import Portfolio, execute_target, moving_average_target
from .protocol import verify_seal
from .study import BASE_COSTS, FAST, INITIAL_CASH, SLOW


PAPER_DIR = ROOT / "paper"
EVENTS_PATH = PAPER_DIR / "events.jsonl"
LOCK_PATH = PAPER_DIR / "lock"
OHLC_URL = "https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=86400&limit=250&exclude_current_candle=true"
TICKER_URL = "https://www.bitstamp.net/api/v2/ticker/btcusd/"


def _digest(event: dict) -> str:
    payload = json.dumps(event, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _read_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def reconcile(path: Path = EVENTS_PATH) -> list[dict]:
    portfolio = Portfolio(INITIAL_CASH, 0.0)
    previous_day: date | None = None
    previous_closes: list[float] | None = None
    previous_hash = "0" * 64
    events = _read_events(path)
    for event in events:
        day = date.fromisoformat(event["day"])
        if previous_day is not None and day <= previous_day:
            raise ValueError("paper ledger dates are not strictly increasing")
        if date.fromisoformat(event["signal_day"]) != day - timedelta(days=1):
            raise ValueError("paper signal uses the wrong day")
        if event["previous_hash"] != previous_hash:
            raise ValueError("paper hash chain differs")
        recorded_hash = event["hash"]
        without_hash = {key: value for key, value in event.items() if key != "hash"}
        if _digest(without_hash) != recorded_hash:
            raise ValueError("paper event was modified")
        closes = event["history_closes"]
        if len(closes) != SLOW or not all(math.isfinite(value) and value > 0 for value in closes):
            raise ValueError("invalid paper signal history")
        if previous_day == day - timedelta(days=1) and previous_closes is not None:
            if previous_closes[1:] != closes[:-1]:
                raise ValueError("paper signal history changed across consecutive days")
        target = moving_average_target(closes, FAST, SLOW)
        if target != event["target"]:
            raise ValueError("paper signal differs from shared strategy")
        if event["portfolio_before"] != {"cash": portfolio.cash, "units": portfolio.units}:
            raise ValueError("paper opening portfolio differs")
        bid = event["ticker_bid"]
        ask = event["ticker_ask"]
        last = event["ticker_last_price"]
        if not all(math.isfinite(value) and value > 0 for value in (bid, ask, last)) or bid > ask:
            raise ValueError("paper ticker is invalid")
        expected_reference = ask if target == 1 and portfolio.units == 0 else (
            bid if target == 0 and portfolio.units > 0 else last
        )
        if event["reference_price"] != expected_reference:
            raise ValueError("paper reference price differs from side quote")
        portfolio, fill = execute_target(portfolio, target, event["reference_price"], BASE_COSTS, day)
        expected_fill = fill.to_json() if fill else None
        if expected_fill != event["fill"]:
            raise ValueError("paper fill differs from shared execution engine")
        if event["portfolio_after"] != {"cash": portfolio.cash, "units": portfolio.units}:
            raise ValueError("paper closing portfolio differs")
        expected_equity = portfolio.equity(event["ticker_last_price"])
        if not math.isclose(expected_equity, event["equity_at_quote"], rel_tol=1e-12):
            raise ValueError("paper marked equity differs")
        previous_day, previous_closes, previous_hash = day, closes, recorded_hash
    return events


def status(path: Path = EVENTS_PATH) -> dict:
    events = reconcile(path)
    streak = 0
    longest = 0
    longest_end: date | None = None
    previous_day: date | None = None
    for event in events:
        day = date.fromisoformat(event["day"])
        streak = streak + 1 if previous_day == day - timedelta(days=1) else 1
        if streak > longest:
            longest = streak
            longest_end = day
        previous_day = day
    ledger_window = None
    if longest >= 30 and longest_end is not None:
        ledger_window = {
            "start": (longest_end - timedelta(days=longest - 1)).isoformat(),
            "end": longest_end.isoformat(),
        }
    # dated entries and replay cannot establish that the scheduled runner was unattended.
    return {
        "entries": len(events),
        "consecutive_days": streak,
        "longest_consecutive_days": longest,
        "last_day": events[-1]["day"] if events else None,
        "ledger_window": ledger_window,
        "unattended_verified": False,
        "complete": False,
        "discrepancies": 0,
    }


def _history(day: date) -> list[float]:
    start = day - timedelta(days=250)
    request = urllib.request.Request(OHLC_URL, headers={"User-Agent": "keel-paper/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload["data"]["pair"] != "BTC/USD":
        raise ValueError("recent Bitstamp candles have the wrong market")
    raw = payload["data"]["ohlc"]
    by_day = {datetime.fromtimestamp(int(row["timestamp"]), tz=timezone.utc).date(): row for row in raw}
    if len(raw) != 250 or len(by_day) != 250 or any(start + timedelta(days=index) not in by_day for index in range(250)):
        raise ValueError("recent Bitstamp candles contain a gap or unfinished day")
    closes = [float(by_day[start + timedelta(days=index)]["close"]) for index in range(50, 250)]
    if not all(math.isfinite(close) and close > 0 for close in closes):
        raise ValueError("recent Bitstamp candles have invalid closes")
    return closes


def _ticker(now: datetime) -> dict:
    request = urllib.request.Request(TICKER_URL, headers={"User-Agent": "keel-paper/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    tick_time = datetime.fromtimestamp(int(payload["timestamp"]), tz=timezone.utc)
    if tick_time.date() != now.date() or abs((now - tick_time).total_seconds()) > 300:
        raise ValueError("ticker is stale or from another UTC day")
    ticker = {
        "time": tick_time.isoformat(),
        "price": payload["last"],
        "bid": payload["bid"],
        "ask": payload["ask"],
    }
    for key in ("price", "bid", "ask"):
        value = float(ticker[key])
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"invalid ticker {key}")
    if float(ticker["bid"]) > float(ticker["ask"]):
        raise ValueError("crossed ticker bid and ask")
    return ticker


def record_once(now: datetime | None = None, path: Path = EVENTS_PATH) -> dict:
    verify_seal()
    supplied_clock = now is not None
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must have a timezone")
    now = now.astimezone(timezone.utc)
    if not (time(0, 10) <= now.time() < time(1, 0)):
        raise ValueError("paper runner acts only from 00:10 to 00:59 UTC")
    day = now.date()
    path.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        events = reconcile(path)
        if events and events[-1]["day"] == day.isoformat():
            return status(path)
        closes = _history(day)
        if events and date.fromisoformat(events[-1]["day"]) == day - timedelta(days=1):
            if events[-1]["history_closes"][1:] != closes[:-1]:
                raise ValueError("paper signal history changed across consecutive days")
        quote_now = now if supplied_clock else datetime.now(timezone.utc)
        if quote_now.date() != day or not (time(0, 10) <= quote_now.time() < time(1, 0)):
            raise ValueError("quote request passed the UTC paper window")
        ticker = _ticker(quote_now)
        before = Portfolio(INITIAL_CASH, 0.0)
        if events:
            before = Portfolio(**events[-1]["portfolio_after"])
        target = moving_average_target(closes, FAST, SLOW)
        # use the contemporaneous side quote; the shared engine adds assumed slippage and fees.
        if target == 1 and before.units == 0:
            reference = float(ticker["ask"])
        elif target == 0 and before.units > 0:
            reference = float(ticker["bid"])
        else:
            reference = float(ticker["price"])
        after, fill = execute_target(before, target, reference, BASE_COSTS, day)
        event = {
            "day": day.isoformat(),
            "signal_day": (day - timedelta(days=1)).isoformat(),
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "history_closes": closes,
            "target": target,
            "ticker_time": ticker["time"],
            "ticker_last_price": float(ticker["price"]),
            "ticker_bid": float(ticker["bid"]),
            "ticker_ask": float(ticker["ask"]),
            "reference_price": reference,
            "portfolio_before": {"cash": before.cash, "units": before.units},
            "portfolio_after": {"cash": after.cash, "units": after.units},
            "fill": fill.to_json() if fill else None,
            "equity_at_quote": after.equity(float(ticker["price"])),
            "previous_hash": events[-1]["hash"] if events else "0" * 64,
        }
        event["hash"] = _digest(event)
        with path.open("a") as handle:
            handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return status(path)
