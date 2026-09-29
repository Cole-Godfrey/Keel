# Keel

On the held-out Bitstamp BTC/USD period (2024-01-01 to 2026-05-20), the 50/200-day strategy returned **12.32% CAGR versus 28.56% for buy and hold**. A prior private Coinbase study covered overlapping BTC dates, so this holdout was not fully blind across venues.

**Licenses:** [Code, scripts, and tests: MIT](LICENSE). [Bundled data and data-derived reports: CC BY-NC-SA 4.0](DATA_LICENSE.md), which restricts commercial use. Commercial use of the data requires a separate license from CryptoDataDownload.

Reproduce the study with:

```sh
./run.sh
```

You need Python 3.10+ and Git. The command runs the tests, checks the research seal, and rebuilds [the held-out report](report/RESEARCH.md), [development report](report/DEVELOPMENT.md), CSV equity curves, and SVG charts. It uses the Python standard library and makes no network request.

The dataset covers 3,915 consecutive UTC days, from 2015-09-01 through 2026-05-20. [CryptoDataDownload](https://www.cryptodatadownload.com/data/) licenses its free data under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). The data is included in the repository and pinned by SHA-256. The importer is in `src/keel/fetch.py`; [data attribution](DATA_LICENSE.md) describes the changes to the source file.

The strategy and buy-and-hold benchmark use the same cash-funded execution engine, including fees, slippage, and next-open fills. [The report](report/RESEARCH.md) records the rules, assumptions, sensitivity runs, held-out results, and failure cases. [The audit note](report/AUDIT.md) details the prior Coinbase exposure.

Paper trading reads public Bitstamp candles and quotes, records them in an append-only local ledger, and sends no orders. On macOS, `python3 paper/install.py` schedules the runner every five minutes. The runner acts only between 00:10 and 00:59 UTC. Check the ledger with `PYTHONPATH=src python3 -m keel paper-status`. The computer must be awake, logged in, and online during that window. The status checks dated entries and ledger replay; it cannot verify unattended execution. The 30-day trial remains incomplete.

See [requirement status](STATUS.md).
