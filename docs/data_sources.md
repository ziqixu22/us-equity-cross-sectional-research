# Data sources and claim boundaries

## yfinance / Yahoo Finance prototype

- Source: <https://github.com/ranaroussi/yfinance>
- Use: free daily OHLCV for a frozen, current-universe local prototype.
- Strength: no account or cloud infrastructure is required; works on a MacBook.
- Boundary: unofficial wrapper, personal/research use only according to its README; not a complete historical securities master, delisting feed, or historical-index-constituent source.

## Open Source Asset Pricing extension

- Source: <https://www.openassetpricing.com/data/>
- Use: separate monthly factor-stability appendix using its published portfolio returns.
- Boundary: portfolio-return and characteristic release; not a replacement for individual-stock daily price/return labels in the main project.

## CRSP/WRDS future adapter

- Source: <https://wrds-www.wharton.upenn.edu/pages/about/data-vendors/center-for-research-in-security-prices-crsp/>
- Use: only after confirming UIUC authorization and permitted publication of derived outputs.
- Boundary: no data exported to Git; schema and return treatment must match the exact licensed version.
