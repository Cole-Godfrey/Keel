# Research and publication audit

The 50/200-day rule, base costs, sensitivity grid, and 2024-01-01 holdout boundary were fixed in development commit `b06c295` before this Bitstamp out-of-sample run. `protocol.json` records the full commit, timestamp, and SHA-256 hashes of the data and research sources. The held-out strategy returned 12.32% CAGR through 2026-05-20 versus 28.56% for buy and hold; it did not beat the benchmark.

A previous private Coinbase study had examined BTC over some of the same dates. This creates cross-venue prior knowledge, so the Bitstamp holdout is not fully blind across markets. None of the private Coinbase candles, results, or Git history are part of this public repository. The Bitstamp parameters and code were committed and sealed before its held-out results were calculated.

The licensed Bitstamp source file has reversed volume headings in 911 older selected rows. The importer verified the implied price against each row's OHLC range before standardizing BTC volume. It excludes the source's partial 2026-05-21 bar and missing 2026-05-22 bar. On 2026-09-28, 130 overlapping selected days from the official Bitstamp OHLC API matched the pinned snapshot in open, high, low, close, and BTC volume. The paper feed's recent 250 daily candles and quote endpoint were also checked without sending orders.

The unattended paper runner is scheduled separately from the research run. Its append-only local ledger is ignored by Git. Requirement 10 remains open until 30 consecutive UTC days are recorded automatically and reconciliation finds no discrepancies.
