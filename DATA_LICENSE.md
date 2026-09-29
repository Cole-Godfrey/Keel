# Data and report license

The snapshot in `data/` comes from [CryptoDataDownload's Bitstamp BTC/USD daily CSV](https://www.cryptodatadownload.com/data/bitstamp/), downloaded on 2026-09-28. CryptoDataDownload licenses its free data under [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-nc-sa/4.0/). The normalized CSV, metadata, and data-derived files in `report/` use the same license. CryptoDataDownload has not endorsed Keel.

We kept the consecutive UTC bars from 2015-09-01 through 2026-05-20, sorted them oldest first, and removed the source's URL, timestamp, and symbol columns. We also standardized volume to BTC units. In 911 older rows, the source reverses its BTC and USD volume headings. The importer checked the price implied by both volume fields against each row's OHLC range before choosing the BTC value. The window stops before the partial 2026-05-21 bar and the missing 2026-05-22 bar. SHA-256 hashes for both files are in `data/btc_usd_bitstamp_daily.json`.

The Python code and tests are original project work and are outside this data license.
