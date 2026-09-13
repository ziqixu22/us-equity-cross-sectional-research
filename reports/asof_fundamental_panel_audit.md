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

### Per-variable staleness fields (schema)

The panel schema does **not** collapse staleness into one generic age field. `build_weekly_fundamental_panel()` (`src/us_equity_cross_sectional/fundamentals/asof_panel.py`) attaches a dedicated `{variable}_age_days` column, via the shared `_lineage()` helper, for every flow variable's TTM value and every stock variable's latest instant, and `build_market_cap()` (`src/us_equity_cross_sectional/fundamentals/market_cap.py`) separately attaches `shares_age_days`. The following per-variable fields exist in code today:

`revenue_ttm_age_days`, `net_income_ttm_age_days`, `operating_income_ttm_age_days`, `gross_profit_ttm_age_days`, `capex_ttm_age_days`, `assets_age_days`, `liabilities_age_days`, `stockholders_equity_age_days`, `cash_age_days`, `shares_age_days`.

A separate `fundamental_age_days` (the max `available_at` age across all fundamental fields on a row) is also retained as a single cross-variable rollup, but it supplements — it does not replace — the per-variable fields above.

### Per-variable staleness statistics

| Variable | Count | Median | P90 | Max | Missing fraction |
|---|---:|---:|---:|---:|---:|
| `revenue_ttm_age_days` | Not regenerated in this audit because the current prototype as-of join is too slow; performance optimization is deferred to a later engineering pass. | — | — | — | — |
| `net_income_ttm_age_days` | Not regenerated in this audit because the current prototype as-of join is too slow; performance optimization is deferred to a later engineering pass. | — | — | — | — |
| `operating_income_ttm_age_days` | Not regenerated in this audit because the current prototype as-of join is too slow; performance optimization is deferred to a later engineering pass. | — | — | — | — |
| `gross_profit_ttm_age_days` | Not regenerated in this audit because the current prototype as-of join is too slow; performance optimization is deferred to a later engineering pass. | — | — | — | — |
| `assets_age_days` | Not regenerated in this audit because the current prototype as-of join is too slow; performance optimization is deferred to a later engineering pass. | — | — | — | — |
| `liabilities_age_days` | Not regenerated in this audit because the current prototype as-of join is too slow; performance optimization is deferred to a later engineering pass. | — | — | — | — |
| `stockholders_equity_age_days` | Not regenerated in this audit because the current prototype as-of join is too slow; performance optimization is deferred to a later engineering pass. | — | — | — | — |
| `cash_age_days` | Not regenerated in this audit because the current prototype as-of join is too slow; performance optimization is deferred to a later engineering pass. | — | — | — | — |
| `shares_age_days` | not recoverable at this precision from the existing checked-in artifact | 56.9 (from the 2026-09-11 run) | Not regenerated in this audit because the current prototype as-of join is too slow; performance optimization is deferred to a later engineering pass. (only p95 = 111.9 was previously reported) | 163.8 (from the 2026-09-11 run) | not recoverable at this precision from the existing checked-in artifact |

`shares_age_days`' median and max above are carried over verbatim from the "Staleness" figures already checked into this report from the 2026-09-11 build (median 56.9, p95 111.9, max 163.8, restricted to eligible non-missing rows). That prior run's row-level output (`data/processed/asof_fundamental_panel_2026-09-11.csv`) is not present on disk — the file is gitignored and was not preserved — so its exact `count`, `p90`, and `missing fraction` cannot be recomputed without rerunning the pipeline, and are marked unavailable above rather than estimated.

**Why the other eight fields have no historical figure to fall back on at all:** the 2026-09-11 report only ever surfaced the *aggregate* `shares_age_days` and `fundamental_age_days` distributions (see prior revision of this file). It never computed or reported the per-variable `*_ttm_age_days` / `assets_age_days` / etc. distributions requested here, even though those columns exist in the panel schema. No cached artifact contains them.

## Limitations

- Unresolved mappings remain missing; no silent quarter fill is used.
- The sample has no unresolved multiple-share-class issuer, but the gate remains mandatory for expansion.
- `price_basis_as_of`, `split_history_cutoff`, and `market_data_download_timestamp` are preserved on every row. Future split factors reconcile provider units only and are not predictive inputs.
- **Reporting gap (added in this audit pass):** per-variable staleness statistics for `revenue_ttm_age_days`, `net_income_ttm_age_days`, `operating_income_ttm_age_days`, `gross_profit_ttm_age_days`, `assets_age_days`, `liabilities_age_days`, `stockholders_equity_age_days`, `cash_age_days`, and a full-precision refresh of `shares_age_days` (count, p90, missing fraction) could not be produced without rebuilding the panel from raw SEC/Yahoo inputs. The current prototype `build_weekly_fundamental_panel()` join is O(signals × facts) — timed at roughly 0.11–0.23 seconds per signal row in this session, i.e. on the order of 15–25+ minutes for the full 6,968-row / 8-issuer panel — which is too slow to run as part of a routine audit update. Performance optimization of the as-of join (e.g. pre-partitioning facts by security before the per-signal selection) is deferred to a later engineering pass; it is a performance change only and would not alter any accounting result, since the join's selection keys already include `security_id`.
