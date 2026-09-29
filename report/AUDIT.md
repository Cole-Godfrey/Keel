# Research and publication audit

Development commit `b06c295` fixed the 50/200-day rule, base costs, sensitivity grid, and 2024-01-01 holdout boundary before the Bitstamp holdout was run. `protocol.json` records the full commit, seal time, and SHA-256 hashes of the original data and research files. On the holdout through 2026-05-20, the strategy returned 12.32% CAGR; buy and hold returned 28.56%.

A previous private Coinbase study covered some of the same BTC dates. That prior exposure means the Bitstamp holdout was not fully blind across venues. The private candles, results, and Git history are outside this repository. The Bitstamp parameters and code were committed and sealed before their holdout results were calculated.

The Bitstamp source reverses its BTC and USD volume headings in 911 older selected rows. The importer checked each row's implied price against its OHLC range before standardizing BTC volume. It left out the partial 2026-05-21 bar and the missing 2026-05-22 bar. On 2026-09-28, 130 selected days matched the official Bitstamp OHLC API in open, high, low, close, and BTC volume. The paper feed's recent 250 daily candles and quote endpoint were checked without sending orders.

The Keel rename kept the original seal unchanged. `rename.json` pins its checksum and the current hashes of the two sealed source files later changed for report presentation and paper feed/status code. The data, strategy, accounting, metrics, and chart code still match their original sealed hashes.

The paper runner has its own schedule and writes an append-only ledger outside Git. The local ledger held one dated entry when checked on 2026-09-29 UTC. `paper-status` verifies the ledger's dated streak and internal replay, but cannot establish that runs were unattended. The 30-day operational trial remains open until 30 consecutive UTC days are independently verified as unattended and reconciliation finds no discrepancies.
