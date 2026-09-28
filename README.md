# Quant Lab

Reproduce a noncommercial BTC/USD moving-average study from a pinned Bitstamp daily OHLCV snapshot:

```sh
./run.sh
```

Requires Python 3.10+ and Git. The command uses only the Python standard library, makes no network request, runs the tests, verifies the sealed data and research code, and regenerates [the report](report/RESEARCH.md) with CSV equity curves and SVG charts.

The dataset contains 3,915 consecutive UTC days from 2015-09-01 through 2026-05-20. [CryptoDataDownload](https://www.cryptodatadownload.com/data/bitstamp/) offers it under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/); see [data attribution and changes](DATA_LICENSE.md). Acquisition and normalization are in `src/quantlab/fetch.py`. The supplied snapshot is pinned by SHA-256, so a clean clone needs no data download.

The strategy and buy-and-hold benchmark share one cash-funded execution engine with fees, slippage, and next-open fills. The report covers rules, assumptions, sensitivity, held-out results, and failure cases. A prior private Coinbase study examined the same BTC period; this is disclosed in [the audit note](report/AUDIT.md).

Paper trading reads public Bitstamp candles and quotes, writes an append-only local ledger, and never sends an order. On macOS, `python3 paper/install.py` schedules it every five minutes; it acts only from 00:10 to 00:59 UTC. Check progress with `PYTHONPATH=src python3 -m quantlab paper-status`. The computer must remain awake, logged in, and online during that window. The 30-consecutive-day requirement is pending until the ledger proves it.

See [requirement status](STATUS.md).
