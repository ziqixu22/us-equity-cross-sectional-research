# Point-in-Time Fundamental Factor Audit

Snapshot: 2026-09-13. Covers `src/us_equity_cross_sectional/features/fundamental.py`
(`compute_fundamental_factors`). No IC, future-return correlation, quantile
analysis, ML models, portfolios, or backtests are computed anywhere in this
report or the module it audits.

## How to read the coverage numbers in this report

Per the established project constraint (do not rebuild the full weekly
as-of fundamental panel just to produce a report; do not fabricate
statistics that aren't already recoverable from checked-in artifacts), this
audit does **not** invoke `build_weekly_fundamental_panel()` or
`compute_fundamental_factors()` against the real 6,968-row/8-issuer panel —
no row-level output of that panel exists on disk (`data/processed/` is
gitignored and no cached panel CSV is present). Exact `valid_observations`,
`total_observations`, `coverage_pct`, and `missing_pct` figures per factor
are therefore **not available in this audit** and are marked below as *"Not
regenerated in this audit because no cached panel output exists; would
require rebuilding the panel, which is deferred pending the performance
fix already noted in `reports/asof_fundamental_panel_audit.md`."*

Where the existing, already-checked-in `reports/asof_fundamental_panel_audit.md`
gives per-*variable* (not per-factor) presence counts against the real
6,968-row panel, those are cited below as a coverage **upper bound**: a
factor cannot have higher coverage than the least-available of its raw
inputs. These bounds are explicitly approximate (they assume independence
across inputs where more than one is combined) and are never presented as
the factor's actual coverage.

## Factors

### book_to_market — `stockholders_equity / market_cap`

- Category: value. Market-cap dependent: yes (missing whenever `market_cap_eligible` is false).
- Required panel columns: `stockholders_equity`, `market_cap`, `market_cap_eligible`.
- Valid observation count / total observation count / coverage % / missing %: Not regenerated in this audit because no cached panel output exists; would require rebuilding the panel, which is deferred pending the performance fix already noted in `reports/asof_fundamental_panel_audit.md`.
- Coverage upper bound from existing artifacts: ≤ 98.8% (6,883/6,968), bounded by `market_cap` eligibility; `stockholders_equity` itself is reported 100% present (0/6,968 missing) in `reports/asof_fundamental_panel_audit.md`.
- Mapping confidence summary: `StockholdersEquity` (or the noncontrolling-interest variant) is reported "present in all 8" audited issuers in `docs/sec_concept_mapping.md`. No known structural mapping gap.
- PIT confidence: high. `stockholders_equity` is selected by the panel's own `available_at <= signal_time` gate; `market_cap` inherits the panel's staleness/eligibility gate unchanged. This factor adds no new temporal logic (unlike `roa`/`gross_profitability`/`asset_growth`, it needs no prior-year lookup).
- Market-cap dependency: yes — always missing when `market_cap_eligible` is false, by construction (`_safe_ratio` divides by a value that is `NaN` whenever ineligible).
- Financial-sector applicability: no known gap; `StockholdersEquity` is a universal balance-sheet concept, including for JPM.
- Known limitations: inherits whatever fraction of rows are market-cap-ineligible (1.2% in the existing 8-issuer sample); does not distinguish "no equity filing yet" from "equity filed but negative" (a negative `stockholders_equity`, which occurs for some real issuers, produces a legitimately negative `book_to_market`, not a missing one).

### earnings_yield — `net_income_ttm / market_cap`

- Category: value. Market-cap dependent: yes.
- Required panel columns: `net_income_ttm`, `market_cap`, `market_cap_eligible`.
- Valid/total/coverage%/missing%: Not regenerated in this audit because no cached panel output exists; would require rebuilding the panel, which is deferred pending the performance fix already noted in `reports/asof_fundamental_panel_audit.md`.
- Coverage upper bound: ≤ 98.8% (6,883/6,968), bounded by `market_cap` eligibility; `net_income_ttm` itself is reported 100% present (0/6,968 missing).
- Mapping confidence summary: `NetIncomeLoss` is reported "present in all 8" in `docs/sec_concept_mapping.md`. No known structural mapping gap.
- PIT confidence: high, same basis as `book_to_market`.
- Market-cap dependency: yes.
- Financial-sector applicability: no known gap; `NetIncomeLoss` is universal, including for JPM.
- Known limitations: a net loss produces a legitimately negative `earnings_yield` (sign is preserved, per the task's explicit rule and the corresponding unit test), which is correct but must not be mistaken for a missing value downstream.

### sales_to_price — `revenue_ttm / market_cap`

- Category: value. Market-cap dependent: yes.
- Required panel columns: `revenue_ttm`, `market_cap`, `market_cap_eligible`.
- Valid/total/coverage%/missing%: Not regenerated in this audit because no cached panel output exists; would require rebuilding the panel, which is deferred pending the performance fix already noted in `reports/asof_fundamental_panel_audit.md`.
- Coverage upper bound: ≤ 96.4% (revenue_ttm 6,720/6,968 present per the existing panel audit), further reduced by the 1.2% of rows that are market-cap-ineligible; the two gaps are not confirmed to be disjoint, so the true bound could be as low as ≈95.2% if fully additive.
- Mapping confidence summary: revenue concepts (`RevenueFromContractWithCustomerExcludingAssessedTax` / `SalesRevenueNet` / `Revenues`) are reported "present in all 8" in `docs/sec_concept_mapping.md`, but the panel-level `revenue_ttm` still shows 248 missing rows — most likely from TTM's four-consecutive-compatible-quarter requirement (e.g. unit changes or a missing quarter breaking `ttm_from_quarters`), not from unmapped concepts. This audit does not diagnose which issuer/period drives the 248 rows without rebuilding the panel.
- PIT confidence: high; identical basis to the other value factors.
- Market-cap dependency: yes.
- Financial-sector applicability: no known concept-mapping gap for revenue.
- Known limitations: the 3.6% TTM-level missingness (not present at the raw-concept level) means this factor is not perfectly universal even though the underlying concept is; flagged in the decision table below.

### roa — `net_income_ttm / average_assets`, `average_assets = (assets + assets_prior_year_comparable) / 2`

- Category: quality. Market-cap dependent: no.
- Required panel columns: `net_income_ttm`, `assets`, `research_date`, `security_id`.
- Valid/total/coverage%/missing%: Not regenerated in this audit because no cached panel output exists; would require rebuilding the panel, which is deferred pending the performance fix already noted in `reports/asof_fundamental_panel_audit.md`.
- Coverage upper bound: `assets` and `net_income_ttm` are each reported 100% present (0/6,968 missing) in the existing panel audit, so the only real coverage constraint is the prior-year-comparable match rate — which has never been measured against the real panel (no prior report computed it, and this audit does not rebuild the panel to do so). No numeric bound can be honestly stated for this factor beyond "at most 100%, minus whatever fraction of security-weeks fall outside the ±10-day tolerance around 365 days before the earliest available observation for that security" (structurally, this affects at least each security's first ~1 year of history).
- Mapping confidence summary: `Assets` and `NetIncomeLoss` are both "present in all 8" per `docs/sec_concept_mapping.md`.
- PIT confidence: high by construction, and directly unit-tested (`test_no_future_observation_used_for_prior_year_match`, `test_roa_missing_when_prior_year_assets_unavailable`): the prior-year match uses `pd.merge_asof(..., direction="nearest", tolerance=...)` keyed on calendar date, is restricted to strictly earlier `research_date` values regardless of row order, and never substitutes a current-only value when the prior comparable is absent — it returns missing instead, per the task's explicit rule.
- Market-cap dependency: no.
- Financial-sector applicability: no known concept-mapping gap; `Assets`/`NetIncomeLoss` apply to JPM as a bank balance sheet the same as any other issuer.
- Known limitations: (1) the actual real-panel match rate for the prior-year lookup is unverified pending a panel rebuild; (2) every security's earliest ~1 year of weekly history is structurally missing this factor by construction (no prior-year comparable can exist), which is expected PIT behavior, not a defect.

### gross_profitability — `gross_profit_ttm / average_assets`

- Category: quality. Market-cap dependent: no.
- Required panel columns: `gross_profit_ttm`, `assets`, `research_date`, `security_id`.
- Valid/total/coverage%/missing%: Not regenerated in this audit because no cached panel output exists; would require rebuilding the panel, which is deferred pending the performance fix already noted in `reports/asof_fundamental_panel_audit.md`.
- Coverage upper bound: `gross_profit_ttm` is reported 100% present (0/6,968 missing) in the existing panel-level table, but this conflicts with `docs/sec_concept_mapping.md`, which states `GrossProfit` is "unavailable for XOM/JPM/WMT audit mapping" — i.e. 3 of the 8 audited issuers. This audit does not resolve that discrepancy (doing so would require inspecting the real panel or raw facts, which this task does not rebuild); it is called out explicitly as a data-quality caveat rather than silently reconciled. Taking the mapping doc at face value, the honest expectation is that at most 5/8 issuers (62.5% of issuer-weeks) can have a non-missing `gross_profit_ttm` at all.
- Mapping confidence summary: mixed/uncertain — see discrepancy above. `GrossProfit` is a duration concept that many issuers (especially non-retail, non-manufacturing, and financial issuers) do not tag at all, consistent with the documented XOM/JPM/WMT gap.
- PIT confidence: high for the ratio construction itself (same tested prior-year-assets logic as `roa`); confidence in the *input* mapping is lower than for the other quality factors given the discrepancy noted above.
- Market-cap dependency: no.
- Financial-sector applicability: **explicitly not universal.** JPM (and per the mapping doc, XOM and WMT) may legitimately have no `GrossProfit` concept filed at all; per the task's explicit rule, no banking-specific or sector-specific substitute concept is invented here. This factor's applicability is documented as issuer/sector-dependent rather than forced to be comparable across all 8 issuers.
- Known limitations: same prior-year-match caveat as `roa`, plus the mapping-gap caveat above; cross-issuer comparisons of this factor should account for which issuers structurally cannot report it.

### operating_margin — `operating_income_ttm / revenue_ttm`

- Category: quality. Market-cap dependent: no.
- Required panel columns: `operating_income_ttm`, `revenue_ttm`.
- Valid/total/coverage%/missing%: Not regenerated in this audit because no cached panel output exists; would require rebuilding the panel, which is deferred pending the performance fix already noted in `reports/asof_fundamental_panel_audit.md`.
- Coverage upper bound: `operating_income_ttm` is reported 100% present (0/6,968 missing) in the existing panel-level table, which again conflicts with `docs/sec_concept_mapping.md` ("unavailable for XOM/JPM audit mapping" — 2 of 8 issuers). As with `gross_profitability`, this audit flags rather than resolves the discrepancy. Taking the mapping doc at face value, at most 6/8 issuers (75%) should have a non-missing `operating_income_ttm`; combined with `revenue_ttm`'s 96.4% panel-level presence, the honest upper bound is materially below the panel-level table's literal 100%/96.4% figures.
- Mapping confidence summary: mixed/uncertain, same discrepancy as `gross_profitability`.
- PIT confidence: high for the ratio itself — a same-row division with no cross-period lookup, so it carries no additional temporal risk beyond what the panel's own `available_at` gate already provides for both inputs.
- Market-cap dependency: no.
- Financial-sector applicability: **explicitly not universal** for the same documented reason as `gross_profitability` — JPM (a bank) and XOM do not file `OperatingIncomeLoss` in the mapped registry; no substitute concept is invented.
- Known limitations: the operating_income_ttm/revenue_ttm mapping-gap discrepancy above should be reconciled (by inspecting real facts, not by this audit) before this factor's coverage is treated as high-confidence.

### leverage — `liabilities / assets`

- Category: quality. Market-cap dependent: no.
- Required panel columns: `liabilities`, `assets`.
- Valid/total/coverage%/missing%: Not regenerated in this audit because no cached panel output exists; would require rebuilding the panel, which is deferred pending the performance fix already noted in `reports/asof_fundamental_panel_audit.md`.
- Coverage upper bound: `liabilities` and `assets` are each reported 100% present (0/6,968 missing) in the existing panel-level table, which conflicts with `docs/sec_concept_mapping.md` ("missing for KO audit mapping" — 1 of 8 issuers). Taking the mapping doc at face value, at most 7/8 issuers (87.5%) should have a non-missing `liabilities`.
- Mapping confidence summary: mixed/uncertain — same class of discrepancy as the two factors above, but affecting only 1 of 8 issuers rather than 2–3.
- PIT confidence: high; a direct, same-row ratio of two balance-sheet instants, no cross-period lookup.
- Market-cap dependency: no.
- Financial-sector applicability: no rule-based exclusion is needed for JPM specifically (both `Liabilities` and `Assets` are reported present for JPM); the documented gap is issuer-specific (KO), not sector-specific.
- Known limitations: the `Liabilities` mapping-gap discrepancy above (docs say KO is missing it; the panel-level table says 0 missing) should be reconciled before treating this factor's coverage as fully verified.

### asset_growth — `assets / assets_prior_year_comparable - 1`

- Category: investment. Market-cap dependent: no.
- Required panel columns: `assets`, `research_date`, `security_id`.
- Valid/total/coverage%/missing%: Not regenerated in this audit because no cached panel output exists; would require rebuilding the panel, which is deferred pending the performance fix already noted in `reports/asof_fundamental_panel_audit.md`.
- Coverage upper bound: `assets` itself is reported 100% present (0/6,968 missing); the only real coverage constraint, as with `roa`, is the prior-year match rate, which is unverified against the real panel.
- Mapping confidence summary: `Assets` is reported "present in all 8" per `docs/sec_concept_mapping.md`. No known structural mapping gap.
- PIT confidence: high, identical mechanism and test coverage to `roa`'s prior-year lookup (`_prior_year_value`); "no future observation used" is directly unit-tested with a deliberately shuffled, irregularly-spaced fixture.
- Market-cap dependency: no.
- Financial-sector applicability: no known gap; `Assets` applies to JPM's balance sheet the same as any other issuer.
- Known limitations: same as `roa` — the real-panel match rate is unverified, and every security's earliest ~1 year of history is structurally missing this factor by construction.

## Summary coverage table (qualitative; see caveats above)

| Factor | Category | Market-cap dependent | Raw-input coverage bound (existing artifacts) | Prior-year join required | Exact factor-level coverage |
|---|---|---|---|---|---|
| book_to_market | value | yes | ≤ 98.8% | no | not regenerated (see above) |
| earnings_yield | value | yes | ≤ 98.8% | no | not regenerated (see above) |
| sales_to_price | value | yes | ≤ ~95–96% | no | not regenerated (see above) |
| roa | quality | no | ≤ 100% (assets/NI), match rate unknown | yes | not regenerated (see above) |
| gross_profitability | quality | no | ≤ 62.5% per mapping doc (docs vs. panel-table discrepancy) | yes | not regenerated (see above) |
| operating_margin | quality | no | ≤ 75% per mapping doc (docs vs. panel-table discrepancy) | no | not regenerated (see above) |
| leverage | quality | no | ≤ 87.5% per mapping doc (docs vs. panel-table discrepancy) | no | not regenerated (see above) |
| asset_growth | investment | no | ≤ 100% (assets), match rate unknown | yes | not regenerated (see above) |

## Unresolved data-quality note

`docs/sec_concept_mapping.md` documents concept-mapping gaps for `Liabilities`
(KO), `OperatingIncomeLoss` (XOM, JPM), and `GrossProfit` (XOM, JPM, WMT),
but the per-variable presence counts already checked into
`reports/asof_fundamental_panel_audit.md` show 0 missing rows for
`liabilities`, `operating_income_ttm`, and `gross_profit_ttm` across all
6,968 rows. This audit does not attempt to resolve that discrepancy —
doing so would require inspecting the real panel or raw SEC facts, which
this task does not rebuild — and instead surfaces it explicitly wherever
it is relevant (see `gross_profitability`, `operating_margin`, and
`leverage` above, and the decision table). It should be reconciled before
any of those three factors' coverage figures are trusted for research use.

## Tests

`tests/test_fundamental_factors.py` — 14 tests, all passing (see report
section E of the final response for the full run). Full project suite —
51 tests, all passing.
