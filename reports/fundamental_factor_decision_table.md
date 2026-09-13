# Fundamental Factor Decision Table

Updated during Milestone 4C coverage validation
(`reports/fundamental_factor_coverage_validation.md`). Decisions below are
based only on accounting meaning, mapping quality, PIT defensibility,
coverage, financial-sector comparability, and data quality — **never** on
observed future-return performance, IC, or backtest results (none of which
are computed anywhere in this task). Real, measured coverage numbers
(not theoretical bounds) are now available for all 8 factors; see
`reports/fundamental_factor_audit.md`.

## What changed since the previous version of this table

The previous version of this table (based on theoretical coverage bounds
and documented-but-unverified mapping gaps) rated 2 factors INCLUDE and 6
INCLUDE WITH FLAG, with no DEFER. Rebuilding the real panel surfaced a
**systemic, silent data-correctness defect** — not merely a coverage gap —
in every factor built from a TTM flow variable (`net_income_ttm`,
`revenue_ttm`, `operating_income_ttm`, `gross_profit_ttm`): a
duration-variant collision in the standalone-quarter reconstruction
produces implausible, silently wrong quarterly values (confirmed 22.5%–
29.9% of pooled reconstructed standalone quarters across all 8 issuers are
negative, for concepts that are essentially never negative at these
issuers). Because this can occur without ever showing up as a missing
value or even a negative final number (a corrupted quarter can still sum
to a positive TTM), coverage percentages and sign checks alone cannot
detect it — only direct inspection of the standalone-quarter
reconstruction did. This is a materially more serious problem than a
coverage gap: a coverage gap means "less data to work with," while this
means "some of the data that looks present is wrong." Per your explicit
rule that decisions must rest on accounting meaning, mapping quality, PIT
defensibility, coverage, sector comparability, and data quality — and
never on future-return evidence — this data-quality defect is decisive on
its own and moves every affected factor to **DEFER**.

| Factor | Decision | Change | Rationale |
|---|---|---|---|
| book_to_market | **INCLUDE** | unchanged | `stockholders_equity` and `market_cap` are both instant/point-in-time values with no duration-length ambiguity — no exposure to the collision bug. Real coverage 88.62%, understated by a documented-but-unfixed single-issuer (JNJ) concept-selection gap that produces no wrong values, only conservative missingness. PIT logic is a direct division inheriting the panel's own gates. |
| earnings_yield | **DEFER** | ↓ from INCLUDE | Numerator `net_income_ttm` is built from the standalone-quarter reconstruction now confirmed to silently corrupt ~30% of standalone quarters pooled across issuers. Real coverage (63.78%) is not the limiting concern — value correctness is. Only 1.6% of the resulting factor values are visibly negative, meaning the sign check catches a small fraction of the actual corruption; most corrupted values likely remain silently wrong in magnitude while landing on the plausible side of zero. Do not use until the duration-collision bug is fixed. |
| sales_to_price | **DEFER** | unchanged from prior flag, now stronger | Numerator `revenue_ttm` is the *most* affected variable (22.5% of pooled standalone quarters negative, confirmed directly on real Apple data: -26.3B and -33.5B "quarterly revenue"). Zero of the 2,558 valid factor values are visibly negative — the sign check gives **no signal whatsoever** here, which is worse than a visible defect: there is currently no way to distinguish a correct from a corrupted non-missing value without re-deriving it from raw facts. |
| roa | **DEFER** | ↓ from INCLUDE WITH FLAG | The prior-year `assets` join itself is now directly measured and clean (94.14% match rate, 0 future selections, tight day-difference distribution — this part of the factor is well-validated). But the numerator `net_income_ttm` carries the same duration-collision defect as `earnings_yield`. A sound denominator does not rescue an unreliable numerator. |
| gross_profitability | **DEFER** | ↓ from INCLUDE WITH FLAG | Same numerator defect as `roa` (27.2% of pooled standalone gross-profit quarters negative among the 5 issuers where the concept exists at all), compounded with the already-legitimate, confirmed 3-issuer (XOM/JPM/WMT) structural mapping gap. The mapping gap alone would still justify only a flag (per the task's explicit rule that financial-sector non-universality is legitimate); the numerator-correctness defect is what moves this to DEFER. |
| operating_margin | **DEFER** | ↓ from INCLUDE WITH FLAG | Both numerator (`operating_income_ttm`, 24.8% of pooled quarters negative) and denominator (`revenue_ttm`, 22.5% negative) are duration-collision-affected simultaneously, on top of the confirmed 2-issuer (XOM/JPM) structural mapping gap. This factor has both the lowest real coverage (20.94%) and the weakest correctness confidence of the eight. |
| leverage | **INCLUDE WITH FLAG** | unchanged | `liabilities` and `assets` are both instant values — no exposure to the collision bug. Real coverage (69.76%) is fully explained: 100% missing for KO/WMT (confirmed zero raw facts, structural), 37.1% for NVDA and 4.8% for MSFT (confirmed data-availability window limits, not bugs), 0% for the remaining 4 issuers including JPM. Flag reflects these explained, non-bug gaps, not a correctness concern. |
| asset_growth | **INCLUDE WITH FLAG** | unchanged | `assets` alone (instant, 0% missing) plus the same prior-year join now directly measured clean (94.14% match rate, 0 future selections). No exposure to the collision bug. The only flag is the structural, expected first-year-of-history gap (408 rows, exactly 51 weeks × 8 issuers) — the most thoroughly validated of the eight factors in this update. |

## Summary

- **INCLUDE:** `book_to_market` — no correctness concern found; its one
  coverage limitation (JNJ) is documented, understood, and non-fabricating.
- **INCLUDE WITH FLAG:** `leverage`, `asset_growth` — both are built purely
  from instant/point-in-time balance-sheet variables with no TTM exposure,
  and both now have real, directly-measured coverage/match-rate numbers
  backing the flag rather than theoretical bounds.
- **DEFER:** `earnings_yield`, `sales_to_price`, `roa`, `gross_profitability`,
  `operating_margin` — all five depend on at least one TTM flow variable
  now confirmed to be built from a standalone-quarter reconstruction that
  silently produces implausible (and likely wrong-magnitude) values for
  ~22–30% of the underlying quarters across all 8 issuers. This is a data
  *correctness* defect, not merely a coverage limitation, and it cannot be
  reliably detected downstream (a corrupted TTM value can still be
  positive and plausible-looking). None of these five should be used in
  factor-level predictive research until `_asof()`'s fact-selection logic
  is fixed to disambiguate duration variants (e.g., by including
  `fiscal_period_start`, or the implied duration length, in its grouping
  key) and `standalone_quarter()`'s YTD assumption is verified against the
  selected fact's actual duration rather than assumed from its `fp` label.

No decision above was informed by, or would change based on, any
future-return, IC, or backtest result — none were computed. Every DEFER
above is driven entirely by a concrete, reproduced data-correctness defect
in the underlying panel construction, not by coverage percentages alone
(coverage percentages are reported for completeness but were explicitly
not the deciding factor — `sales_to_price`, for example, would still be
deferred even if its coverage were much higher, because zero of its valid
values show any statistical signal of the underlying corruption).
