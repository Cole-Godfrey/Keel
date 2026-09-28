"""verify idempotent paper entries and reconciliation with shared accounting."""

from __future__ import annotations

import json
import io
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from quantlab.paper import _history, _ticker, record_once, reconcile, status


class PaperTests(unittest.TestCase):
    def test_thirty_day_streak_survives_a_later_gap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            first = datetime(2026, 9, 29, 0, 15, tzinfo=timezone.utc)

            def history(day):
                offset = (day - first.date()).days
                return [float(1000 + offset + index) for index in range(200)]

            def ticker(now):
                return {"time": now.isoformat(), "price": "1200", "bid": "1199", "ask": "1201"}

            with patch("quantlab.paper.verify_seal"), patch("quantlab.paper._history", side_effect=history), patch("quantlab.paper._ticker", side_effect=ticker):
                for index in range(30):
                    record_once(first + timedelta(days=index), path)
                completed = status(path)
                self.assertTrue(completed["complete"])
                self.assertEqual(completed["consecutive_days"], 30)
                self.assertEqual(completed["completed_window"], {"start": "2026-09-29", "end": "2026-10-28"})
                record_once(first + timedelta(days=31), path)
            after_gap = status(path)
            self.assertTrue(after_gap["complete"])
            self.assertEqual(after_gap["consecutive_days"], 1)
            self.assertEqual(after_gap["longest_consecutive_days"], 30)

    def test_replay_detects_changed_overlapping_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            first = datetime(2026, 9, 29, 0, 15, tzinfo=timezone.utc)
            ticker = {"time": first.isoformat(), "price": "100", "bid": "99", "ask": "101"}
            with patch("quantlab.paper.verify_seal"), patch("quantlab.paper._history", side_effect=[[90.0] * 200, [91.0] * 200]), patch("quantlab.paper._ticker", return_value=ticker):
                record_once(first, path)
                with self.assertRaisesRegex(ValueError, "history changed"):
                    record_once(first + timedelta(days=1), path)
            self.assertEqual(status(path)["entries"], 1)

    def test_bitstamp_unix_ticker_timestamp(self) -> None:
        now = datetime(2026, 9, 29, 0, 15, 10, tzinfo=timezone.utc)
        payload = {
            "timestamp": str(int(now.timestamp()) - 1),
            "last": "100",
            "bid": "99",
            "ask": "101",
        }
        with patch("quantlab.paper.urllib.request.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
            self.assertEqual(_ticker(now), {"time": "2026-09-29T00:15:09+00:00", "price": "100", "bid": "99", "ask": "101"})

    def test_bitstamp_history_requires_250_completed_days(self) -> None:
        day = datetime(2026, 9, 29, tzinfo=timezone.utc).date()
        start = day - timedelta(days=250)
        rows = [
            {"timestamp": str(int(datetime.combine(start + timedelta(days=index), datetime.min.time(), tzinfo=timezone.utc).timestamp())), "close": str(100 + index)}
            for index in range(250)
        ]
        payload = {"data": {"pair": "BTC/USD", "ohlc": rows}}
        with patch("quantlab.paper.urllib.request.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
            self.assertEqual(_history(day), [float(150 + index) for index in range(200)])
        payload["data"]["ohlc"].pop(50)
        with patch("quantlab.paper.urllib.request.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
            with self.assertRaisesRegex(ValueError, "gap"):
                _history(day)

    def test_entry_replays_and_duplicate_run_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            now = datetime(2026, 9, 29, 0, 15, tzinfo=timezone.utc)
            ticker = {"time": now.isoformat(), "price": "100", "bid": "99", "ask": "101"}
            closes = [90.0] * 150 + [100.0] * 50
            with patch("quantlab.paper.verify_seal"), patch("quantlab.paper._history", return_value=closes), patch("quantlab.paper._ticker", return_value=ticker):
                first = record_once(now, path)
                second = record_once(now, path)
            self.assertEqual(first, second)
            self.assertEqual(status(path)["entries"], 1)
            self.assertEqual(status(path)["consecutive_days"], 1)
            self.assertEqual(reconcile(path)[0]["fill"]["side"], "buy")

    def test_changed_fill_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            now = datetime(2026, 9, 29, 0, 15, tzinfo=timezone.utc)
            ticker = {"time": now.isoformat(), "price": "100", "bid": "99", "ask": "101"}
            closes = [90.0] * 150 + [100.0] * 50
            with patch("quantlab.paper.verify_seal"), patch("quantlab.paper._history", return_value=closes), patch("quantlab.paper._ticker", return_value=ticker):
                record_once(now, path)
            event = json.loads(path.read_text())
            event["fill"]["fee"] = 0
            path.write_text(json.dumps(event) + "\n")
            with self.assertRaises(ValueError):
                reconcile(path)


if __name__ == "__main__":
    unittest.main()
