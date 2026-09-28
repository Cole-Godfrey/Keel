# Data and report license

The snapshot in `data/` is adapted from [CryptoDataDownload's Bitstamp BTC/USD daily CSV](https://www.cryptodatadownload.com/data/bitstamp/), downloaded 2026-09-28. CryptoDataDownload offers its free data under [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-nc-sa/4.0/). The normalized CSV, metadata, and data-derived artifacts in `report/` are shared under the same license. This does not imply CryptoDataDownload endorses this project.

Changes to the source: selected the consecutive 2015-09-01 through 2026-05-20 UTC window; dropped the source's URL, timestamp, and symbol columns; ordered rows oldest first; and standardized volume to BTC units. The source reverses its BTC and USD volume headings in 911 older selected rows. Each corrected row was checked against the price implied by its two volume fields. The selected window ends before the source's partial 2026-05-21 bar and missing 2026-05-22 bar. The source-file SHA-256 and normalized-file SHA-256 are in `data/btc_usd_bitstamp_daily.json`.

The Python source code and tests are original project code and are outside this data license.
