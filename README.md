# Keel

Keel reproduces a noncommercial BTC/USD moving-average study using a pinned daily Bitstamp dataset:

```sh
./run.sh
```

You need Python 3.10+ and Git. The command runs the tests, checks the research seal, and rebuilds [the report](report/RESEARCH.md), CSV equity curves, and SVG charts. It uses the Python standard library and makes no network request.

The dataset covers 3,915 consecutive UTC days, from 2015-09-01 through 2026-05-20. [CryptoDataDownload](https://www.cryptodatadownload.com/data/bitstamp/) licenses it under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). The data is included in the repository and pinned by SHA-256. The importer is in `src/keel/fetch.py`; [data attribution](DATA_LICENSE.md) describes the changes to the source file.

The strategy and buy-and-hold benchmark use the same cash-funded execution engine, including fees, slippage, and next-open fills. The report records the rules, assumptions, sensitivity runs, held-out results, and failure cases. [The audit note](report/AUDIT.md) discloses an earlier private Coinbase study of the same BTC period.

Paper trading reads public Bitstamp candles and quotes, records them in an append-only local ledger, and sends no orders. On macOS, `python3 paper/install.py` schedules the runner every five minutes. It records one entry per day between 00:10 and 00:59 UTC. Check the ledger with `PYTHONPATH=src python3 -m keel paper-status`. The computer must be awake, logged in, and online during that window. The 30-day trial is still in progress.

See [requirement status](STATUS.md).
