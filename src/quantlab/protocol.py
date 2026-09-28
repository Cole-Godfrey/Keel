"""seal the model before the out-of-sample backtest is opened."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .data import ROOT, sha256_file
from .study import BASE_COSTS, DEV_END, FAST, SLOW, STRESS_COSTS, WARMUP_DAYS


PROTOCOL_PATH = ROOT / "protocol.json"
TRACKED = (
    "data/btc_usd_bitstamp_daily.csv",
    "data/btc_usd_bitstamp_daily.json",
    "src/quantlab/data.py",
    "src/quantlab/engine.py",
    "src/quantlab/metrics.py",
    "src/quantlab/study.py",
    "src/quantlab/chart.py",
    "src/quantlab/report.py",
    "src/quantlab/paper.py",
)


def _manifest() -> dict[str, str]:
    return {name: sha256_file(ROOT / name) for name in TRACKED}


def seal() -> None:
    if PROTOCOL_PATH.exists():
        raise FileExistsError("protocol already sealed")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip():
        raise RuntimeError("commit the development implementation before sealing")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    protocol = {
        "sealed_at_utc": datetime.now(timezone.utc).isoformat(),
        "development_commit": commit,
        "development_end_exclusive": DEV_END.isoformat(),
        "warmup_days": WARMUP_DAYS,
        "strategy": {"fast": FAST, "slow": SLOW, "initial_cash": 10_000},
        "base_costs_bps": {"fee": BASE_COSTS.fee_bps, "slippage": BASE_COSTS.slippage_bps},
        "stress_costs_bps": {"fee": STRESS_COSTS.fee_bps, "slippage": STRESS_COSTS.slippage_bps},
        "files_sha256": _manifest(),
    }
    PROTOCOL_PATH.write_text(json.dumps(protocol, indent=2, sort_keys=True) + "\n")


def verify_seal() -> dict:
    protocol = json.loads(PROTOCOL_PATH.read_text())
    if protocol["files_sha256"] != _manifest():
        raise ValueError("a sealed data or research source file changed")
    return protocol
