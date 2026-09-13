# Point-in-Time Fundamental Factor Audit

Snapshot: 2026-09-13 (updated during Milestone 4C coverage validation; see
`reports/fundamental_factor_coverage_validation.md` for the full
investigation). Covers `src/us_equity_cross_sectional/features/fundamental.py`
(`compute_fundamental_factors`). No IC, future-return correlation, quantile
analysis, ML models, portfolios, or backtests are computed anywhere in this
report or the module it audits.

## What changed since the previous version of this report

The previous version of this report could only give theoretical *upper
bounds* on coverage, because no cached row-level panel output existed and
rebuilding the panel was believed prohibitively slow. This update:

1. Rebuilt the real 6,968-row/8-issuer panel from the already-cached raw
   SEC/Yahoo data (`data/raw/`), using 8-way process parallelism now that
   the panel builder is provably security-independent (see the
   coverage-validation report's performance section) — no network calls,
   ~6.3 minutes wall-clock.
2. In doing so, discovered and fixed a real cross-security data-leakage bug
   in `build_weekly_fundamental_panel()` that had been inflating the
   previous (buggy) panel audit's coverage figures for `liabilities`,
   `operating_income_ttm`, and `gross_profit_ttm` to a false 100%.
3. Discovered and fixed a `pd.merge_asof` crash in this module's own
   `_prior_year_value()` that only manifests on realistic multi-security
   data (not on the small synthetic fixtures used by this module's
   original tests).
4. Discovered, but did **not** fix (out of scope for this pass — see the
   coverage-validation report), two further data-quality issues: (a) a
   single-candidate concept-selection limitation that under-reports
   `stockholders_equity` for JNJ specifically, and (b) a duration-variant
   collision in the standalone-quarter reconstruction that produces
   silently wrong (not just missing) TTM flow values for `revenue_ttm`,
   `net_income_ttm`, `operating_income_ttm`, and `gross_profit_ttm` across
   all 8 issuers.

All coverage numbers below are now **real, measured values** from
`compute_fundamental_factors()` run against the real panel — not
theoretical bounds.

## Factors

### book_to_market — `stockholders_equity / market_cap`

- Category: value. Market-cap dependent: yes.
- Required panel columns: `stockholders_equity`, `market_cap`, `market_cap_eligible`.
- Valid / total / coverage % / missing %: **6,175 / 6,968 / 88.62% / 11.38%.**
- Mapping confidence summary: `StockholdersEquity` (or the noncontrolling-interest
  variant) is present for all 8 issuers, but `normalize_company_facts()`
  only ever uses the *first* candidate concept it finds and never falls
  back to the second for periods the first doesn't cover. This causes
  JNJ specifically to be missing `stockholders_equity` on 81.3% of its
  rows (708 of JNJ's 871 rows — accounting for essentially all of the
  panel-wide missingness). The other 7 issuers are 0% missing. This is a
  known, documented, **not yet fixed** limitation (see coverage-validation
  report); the 88.62% figure is a conservative floor, not a ceiling.
- PIT confidence: high. Both inputs are selected via the panel's own
  `available_at <= signal_time` gate with no additional temporal logic.
- Market-cap dependency: yes — missing whenever `market_cap_eligible` is false.
- Financial-sector applicability: no known gap; JPM's `stockholders_equity`
  is 0% missing.
- Known limitations: the JNJ concept-selection gap above; a negative
  `stockholders_equity` produces a legitimately negative ratio, not a
  missing one.

### earnings_yield — `net_income_ttm / market_cap`

- Category: value. Market-cap dependent: yes.
- Required panel columns: `net_income_ttm`, `market_cap`, `market_cap_eligible`.
- Valid / total / coverage % / missing %: **4,444 / 6,968 / 63.78% / 36.22%.**
- Mapping confidence summary: `NetIncomeLoss` itself is present for all 8
  issuers, but **`net_income_ttm` is subject to the duration-variant
  collision bug** described in the coverage-validation report: 29.9% of
  reconstructed standalone net-income quarters (pooled across all 8
  issuers) are negative, an implausibly high rate for large, generally
  profitable issuers over 2010–2026. Because TTM sums four quarters, a
  single corrupted component does not always flip the final sign — only
  1.6% of *valid* `earnings_yield` values are negative, which understates
  how many are silently wrong in magnitude while still landing on the
  correct side of zero.
- PIT confidence: high for the point-in-time selection mechanism itself
  (no future information is used); **low for value correctness**, given
  the duration-collision bug above. This is a data-quality defect, not a
  PIT-discipline defect.
- Market-cap dependency: yes.
- Financial-sector applicability: no known concept-mapping gap for JPM.
- Known limitations: **do not treat non-missing `earnings_yield` values as
  reliable until the duration-variant collision bug is fixed** (see
  decision table below).

### sales_to_price — `revenue_ttm / market_cap`

- Category: value. Market-cap dependent: yes.
- Required panel columns: `revenue_ttm`, `market_cap`, `market_cap_eligible`.
- Valid / total / coverage % / missing %: **2,558 / 6,968 / 36.71% / 63.29%.**
- Mapping confidence summary: revenue concepts are present for all 8
  issuers at the raw-concept level, but `revenue_ttm` is the variable
  most affected by the duration-variant collision bug: 22.5% of pooled
  reconstructed standalone revenue quarters are negative (Apple's raw
  data alone shows quarters of -26.3B and -33.5B, which is definitionally
  impossible for reported revenue). This also explains the low coverage:
  many weeks fail the "four compatible consecutive quarters" TTM
  requirement outright because a corrupted quarter's unit/value
  incompatibility trips `ttm_from_quarters()`'s rejection.
- PIT confidence: high for the selection mechanism; **not trustworthy for
  value correctness** — see above. Unlike `earnings_yield`/`roa`, zero of
  the 2,558 valid values happen to be visibly negative, meaning the sign
  check gives **no signal at all** here that anything is wrong; only
  direct inspection of the standalone-quarter reconstruction (done in the
  coverage-validation report) surfaces the defect.
- Market-cap dependency: yes.
- Financial-sector applicability: no known raw-concept gap for JPM.
- Known limitations: see the "critical finding" in the coverage-validation
  report; this factor should not be used for research until fixed.

### roa — `net_income_ttm / average_assets`

- Category: quality. Market-cap dependent: no.
- Required panel columns: `net_income_ttm`, `assets`, `research_date`, `security_id`.
- Valid / total / coverage % / missing %: **4,425 / 6,968 / 63.50% / 36.50%.**
- Mapping confidence summary: `Assets` is present for all 8 issuers with
  0% missing; the prior-year join (Task 2 of the coverage-validation
  report) matched 94.14% of eligible rows with a clean day-difference
  profile (median 1 day, max 8 days) and zero future-observation
  selections. The numerator, `net_income_ttm`, carries the same
  duration-collision defect as `earnings_yield` above.
- PIT confidence: high for both the panel's own availability gate and the
  prior-year-comparable join (directly measured and unit-tested); **low
  for numerator correctness**, for the same reason as `earnings_yield`.
- Market-cap dependency: no.
- Financial-sector applicability: no known gap; JPM's `Assets`/`NetIncomeLoss`
  are both 0% missing.
- Known limitations: the numerator-corruption issue above; the earliest
  ~1 year of each security's history structurally lacks a prior-year
  comparable (expected PIT behavior, not a defect).

### gross_profitability — `gross_profit_ttm / average_assets`

- Category: quality. Market-cap dependent: no.
- Required panel columns: `gross_profit_ttm`, `assets`, `research_date`, `security_id`.
- Valid / total / coverage % / missing %: **2,494 / 6,968 / 35.79% / 64.21%.**
- Mapping confidence summary: `GrossProfit` is confirmed absent at the raw
  concept level for XOM, JPM, and WMT (100% missing `gross_profit_ttm` for
  each, exactly matching `docs/sec_concept_mapping.md`) — a legitimate,
  sector/issuer-driven applicability limit, not a bug. Among the 5 issuers
  that do have the concept, `gross_profit_ttm` also carries the
  duration-collision defect (27.2% of pooled reconstructed standalone
  gross-profit quarters are negative).
- PIT confidence: high for the join mechanism; **low for numerator
  correctness** among the 5 issuers where the concept exists at all.
- Market-cap dependency: no.
- Financial-sector applicability: **explicitly not universal** — confirmed,
  not merely documented, that JPM (and XOM, WMT) have zero `GrossProfit`
  facts. No banking-specific substitute is invented, per the task's rule.
- Known limitations: both the structural 3-issuer mapping gap and the
  duration-collision numerator defect apply; do not compare this factor
  across issuers with different mapping availability, and do not treat
  non-missing values as reliable until the collision bug is fixed.

### operating_margin — `operating_income_ttm / revenue_ttm`

- Category: quality. Market-cap dependent: no.
- Required panel columns: `operating_income_ttm`, `revenue_ttm`.
- Valid / total / coverage % / missing %: **1,459 / 6,968 / 20.94% / 79.06%.**
- Mapping confidence summary: `OperatingIncomeLoss` is confirmed absent at
  the raw concept level for XOM and JPM (100% missing `operating_income_ttm`
  for each, exactly matching the mapping doc). The low overall coverage
  (20.94%) reflects **both inputs** being duration-collision-affected and
  TTM-incompatibility-prone simultaneously — `operating_income_ttm` and
  `revenue_ttm` must both independently survive the four-compatible-quarter
  requirement for this ratio to be computable at all, compounding the two
  factors' individual missingness.
- PIT confidence: high for the same-row selection mechanism; **low for
  numerator and denominator correctness** — both inputs carry the
  duration-collision defect (24.8% of pooled operating-income quarters and
  22.5% of pooled revenue quarters are negative).
- Market-cap dependency: no.
- Financial-sector applicability: **explicitly not universal** for XOM/JPM,
  confirmed against raw facts.
- Known limitations: this factor has the lowest real coverage of the eight
  and, given both inputs are duration-collision-affected, the weakest
  correctness confidence of the eight. Do not use until the collision bug
  is fixed.

### leverage — `liabilities / assets`

- Category: quality. Market-cap dependent: no.
- Required panel columns: `liabilities`, `assets`.
- Valid / total / coverage % / missing %: **4,861 / 6,968 / 69.76% / 30.24%.**
- Mapping confidence summary: `Liabilities` is confirmed 100% missing for
  KO and WMT (zero facts in raw data — a genuine, structural mapping gap,
  not a bug), 37.1% missing for NVDA (its `Liabilities` facts only begin
  2015-01-25, while its weekly signal history starts 2010-01-08 — a
  data-availability window limit, not a bug), and 4.8% missing for MSFT
  (same mechanism, a smaller ~6-month window gap in early 2010). AAPL,
  JNJ, JPM, and XOM are all 0% missing.
- PIT confidence: high — a direct, same-row ratio of two instant
  (point-in-time) balance-sheet facts with no cross-period lookup and
  **no exposure to the duration-collision bug**, since instant facts have
  no "3-month vs. cumulative" duration variant to collide.
- Market-cap dependency: no.
- Financial-sector applicability: no issuer-specific exclusion needed for
  JPM (0% missing); the gaps are issuer-specific (KO, WMT structurally;
  NVDA, MSFT by data-window), not sector-specific.
- Known limitations: the three explained, non-bug coverage gaps above.
  This is the more reliable of the two liabilities/assets-based factors
  precisely because it involves no TTM reconstruction.

### asset_growth — `assets / assets_prior_year_comparable - 1`

- Category: investment. Market-cap dependent: no.
- Required panel columns: `assets`, `research_date`, `security_id`.
- Valid / total / coverage % / missing %: **6,560 / 6,968 / 94.14% / 5.86%.**
- Mapping confidence summary: `Assets` is 0% missing for all 8 issuers.
  Coverage is bounded entirely by the prior-year join's measured 94.14%
  match rate (Task 2 of the coverage-validation report); the 408 missing
  rows are exactly, and only, each security's earliest ~51 weeks of
  history (51 × 8 = 408) — the expected consequence of no observation
  existing 365 days before a security's first signal.
- PIT confidence: high, directly measured — zero future-observation
  selections across all 6,968 rows, a tight day-difference distribution
  (median 1 day, max 8 days), and stable behavior around year-end/holiday
  target dates. **No exposure to the duration-collision bug** (instant
  variable only).
- Market-cap dependency: no.
- Financial-sector applicability: no known gap; JPM's `Assets` is 0% missing.
- Known limitations: the structural first-year gap above; otherwise the
  most thoroughly validated of the eight factors in this update.

## Real coverage summary table

| Factor | Valid | Total | Coverage % | Missing % | Correctness confidence |
|---|---:|---:|---:|---:|---|
| book_to_market | 6,175 | 6,968 | 88.62% | 11.38% | High (coverage understated by an unfixed, documented gap; no known wrong values) |
| earnings_yield | 4,444 | 6,968 | 63.78% | 36.22% | **Low** — numerator affected by duration-collision bug |
| sales_to_price | 2,558 | 6,968 | 36.71% | 63.29% | **Low** — numerator affected by duration-collision bug |
| roa | 4,425 | 6,968 | 63.50% | 36.50% | **Low** — numerator affected by duration-collision bug |
| gross_profitability | 2,494 | 6,968 | 35.79% | 64.21% | **Low** — numerator affected by duration-collision bug (where mapped at all) |
| operating_margin | 1,459 | 6,968 | 20.94% | 79.06% | **Low** — both inputs affected by duration-collision bug |
| leverage | 4,861 | 6,968 | 69.76% | 30.24% | High — no TTM exposure; gaps are explained and structural |
| asset_growth | 6,560 | 6,968 | 94.14% | 5.86% | High — no TTM exposure; directly measured PIT join quality |

## Tests

`tests/test_fundamental_factors.py` — 15 tests (14 original + 1 new
regression test for the `merge_asof` sort-order crash), all passing.
`tests/test_asof_fundamental_panel.py` — includes a new regression test
for the cross-security leak bug. Full project suite — 53 tests, all
passing.
