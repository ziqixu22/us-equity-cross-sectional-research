# Weekly As-of Fundamental Panel Audit

Snapshot: 2026-09-11; no ratios, IC, returns, models, or portfolios.

## Coverage

- Rows: 6,968; issuers: 8; weekly dates: 871.
- Date range: 2010-01-08 to 2026-09-10.

| Year | Rows | Issuers |
|---:|---:|---:|
| 2010 | 416 | 8 |
| 2011 | 416 | 8 |
| 2012 | 416 | 8 |
| 2013 | 416 | 8 |
| 2014 | 416 | 8 |
| 2015 | 424 | 8 |
| 2016 | 416 | 8 |
| 2017 | 416 | 8 |
| 2018 | 416 | 8 |
| 2019 | 416 | 8 |
| 2020 | 424 | 8 |
| 2021 | 416 | 8 |
| 2022 | 416 | 8 |
| 2023 | 416 | 8 |
| 2024 | 416 | 8 |
| 2025 | 416 | 8 |
| 2026 | 296 | 8 |

## Variable availability

| Variable | Present | Missing |
|---|---:|---:|
| revenue_ttm | 6,720 | 248 |
| net_income_ttm | 6,968 | 0 |
| operating_income_ttm | 6,968 | 0 |
| gross_profit_ttm | 6,968 | 0 |
| capex_ttm | 6,968 | 0 |
| assets | 6,968 | 0 |
| liabilities | 6,968 | 0 |
| stockholders_equity | 6,968 | 0 |
| cash | 6,968 | 0 |
| shares_raw | 6,968 | 0 |
| market_cap | 6,883 | 85 |

## Timing and eligibility

- Market-cap eligible: 98.8% (6,883/6,968).
- Exact share acceptance: 37.7%; filing-date-plus-one-day fallback: 62.3%.
- Multiple-share-class exclusions: 0.
- Financial-sector gaps: this eight-issuer audit set includes JPM only; financial-sector coverage is not representative.

## Staleness

- Shares age days (eligible nonmissing): median 56.9, p95 111.9, max 163.8.
- Latest fundamental availability age: median 9.0, p95 42.9.

## Limitations

- Unresolved mappings remain missing; no silent quarter fill is used.
- The sample has no unresolved multiple-share-class issuer, but the gate remains mandatory for expansion.
- `price_basis_as_of`, `split_history_cutoff`, and `market_data_download_timestamp` are preserved on every row. Future split factors reconcile provider units only and are not predictive inputs.
