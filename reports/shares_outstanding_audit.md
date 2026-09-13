# SEC Shares Outstanding Audit

**Audit snapshot:** cached SEC Company Facts and submissions downloaded 2026-09-11. **Issuer sample:** AAPL, MSFT, KO, JNJ, XOM, JPM, WMT, and NVDA. The audit uses the repository's registered `dei:EntityCommonStockSharesOutstanding` instant concept and accession-level submissions join. No market capitalization, valuation ratio, IC, or backtest was constructed.

## Audit method

The cached Company Facts payloads contain 559 share observations. For continuity, jump, and staleness diagnostics, observations with the same issuer, instant date, and value were collapsed to the earliest availability, leaving 550 unique instant/value observations. The nine removed rows repeat an already observed instant/value through an amendment or other filing; no instant date has conflicting share values in this sample.

`end` is treated as the share-count **instant date**, not as a duration endpoint. Availability follows the existing adapter: submission `acceptanceDateTime` when the accession joins to the cached `filings.recent` list, otherwise Company Facts `filed` plus one calendar day. Large jumps are consecutive changes greater than 20% in absolute value. Staleness is reported both at first availability (`available_at - instant date`) and immediately before the next observation becomes available.

## Issuer coverage

All eight audited issuers expose `dei:EntityCommonStockSharesOutstanding` in `shares` units.

| Issuer | Raw facts | Unique instants | Instant-date range | Exact acceptance available | Latest instant | Age on 2026-09-11 |
|---|---:|---:|---|---:|---|---:|
| AAPL | 70 | 69 | 2009-06-27 to 2026-07-17 | 44 / 69 (63.8%) | 2026-07-17 | 56 days |
| MSFT | 68 | 68 | 2009-10-19 to 2026-07-23 | 25 / 68 (36.8%) | 2026-07-23 | 50 days |
| KO | 71 | 68 | 2009-07-24 to 2026-04-28 | 33 / 68 (48.5%) | 2026-04-28 | 136 days |
| JNJ | 69 | 69 | 2009-07-26 to 2026-07-17 | 33 / 69 (47.8%) | 2026-07-17 | 56 days |
| XOM | 69 | 68 | 2009-06-30 to 2026-03-31 | 26 / 68 (38.2%) | 2026-03-31 | 164 days |
| JPM | 73 | 69 | 2009-07-31 to 2026-06-30 | 4 / 69 (5.8%) | 2026-06-30 | 73 days |
| WMT | 70 | 70 | 2009-09-04 to 2026-08-26 | 14 / 70 (20.0%) | 2026-08-26 | 16 days |
| NVDA | 69 | 69 | 2009-08-17 to 2026-08-21 | 25 / 69 (36.2%) | 2026-08-21 | 21 days |

Coverage begins partway through 2009, consistent with the phase-in of structured SEC XBRL data rather than issuer listing dates. The sample is intentionally small and does not establish coverage for the larger research universe.

## Yearly coverage and missing periods

| Calendar year of instant date | Issuers represented | Unique instants |
|---:|---:|---:|
| 2009 | 8 | 15 |
| 2010 | 8 | 32 |
| 2011 | 8 | 32 |
| 2012 | 8 | 32 |
| 2013 | 8 | 33 |
| 2014 | 8 | 32 |
| 2015 | 8 | 32 |
| 2016 | 8 | 32 |
| 2017 | 8 | 32 |
| 2018 | 8 | 32 |
| 2019 | 8 | 32 |
| 2020 | 8 | 32 |
| 2021 | 8 | 32 |
| 2022 | 8 | 32 |
| 2023 | 8 | 32 |
| 2024 | 8 | 32 |
| 2025 | 8 | 32 |
| 2026 through audit date | 8 | 22 |

Every issuer has four unique instant dates in every full calendar year from 2010 through 2025. WMT has a fifth date in 2013 because an amended 10-Q supplies a distinct cover-page instant before the next regular 10-Q. The partial boundary years are not missing-period failures: 2009 begins midyear, and 2026 is incomplete at the audit date. Within 2026, six issuers have three observations while KO and XOM have two, so those two are the concrete current-period coverage shortfall in the cache.

Calendar-quarter labels should not be imposed on this concept. The instant is normally the cover-page shares date and need not equal the fiscal quarter end; for example, XOM commonly reports a January 31 cover-date fact for its 10-K and a March 31 fact for its following 10-Q. A calendar-quarter bucket would falsely label XOM's Q4 as missing and Q1 as duplicated. Sequence continuity is better assessed from periodic-filing cadence: the median gap between unique instants is 91 days, the maximum is 126 days, 38 gaps exceed 120 days, and none exceeds 126 days.

## Filing and acceptance availability

All 550 unique observations have an accession number and filing date, and all therefore receive a non-null `available_at`. Only 204 of 550 (37.1%) join to an exact SEC acceptance timestamp in the cached recent-submissions arrays. Exact coverage varies materially by issuer, from 63.8% for AAPL to 5.8% for JPM, because the submissions cache contains only the recent filing arrays while Company Facts reaches back to 2009.

The 346 unmatched observations use the adapter's filing-date-plus-one-calendar-day fallback. That prevents same-day look-ahead but is not an actual acceptance time and is not guaranteed to be a trading session. Later panel construction must retain a flag distinguishing exact acceptance from fallback timing and apply the intended next-trading-session rule before the data is treated as production-quality.

The raw filing mix is 411 10-Q, 136 10-K, five 10-Q/A, five 8-K, and two 10-K/A facts. Amendments and 8-Ks explain repeated facts but introduce no conflicting instant-date values in this sample.

## Staleness

At first availability, the share instant is already a median 7.0 days old; the maximum observed initial age is 39.0 days. If each fact is carried forward until the next fact becomes available, its age immediately before refresh has a median of 99.4 days, a 95th percentile of 139.9 days, and a maximum of 152.0 days. This is expected for a quarterly disclosure rather than a daily security-master field.

At the 2026-09-11 audit snapshot, the latest instant is 16–164 days old across issuers. KO is 136 days old and XOM is 164 days old, while the other six range from 16 to 73 days. Market-cap construction therefore needs an explicit maximum-staleness gate and must emit missing rather than silently carrying an arbitrarily old count.

## Large share-count jumps

Eight consecutive transitions exceed the 20% audit threshold:

| Issuer | From instant/value | To instant/value | Change | Assessment |
|---|---|---|---:|---|
| AAPL | 2014-04-11 / 861,381,000 | 2014-07-11 / 5,987,867,000 | +595.1% (6.951x) | Consistent with 7:1 split |
| AAPL | 2020-07-17 / 4,275,634,000 | 2020-10-16 / 17,001,802,000 | +297.6% (3.976x) | Consistent with 4:1 split |
| KO | 2009-07-24 / 2,317,441,658 | 2009-10-23 / 0 | -100.0% | Invalid zero in 10-Q/A; must be rejected |
| KO | 2009-10-23 / 0 | 2010-02-22 / 2,305,123,938 | Undefined from zero | Recovery from invalid zero, not an economic jump |
| KO | 2012-07-23 / 2,250,961,597 | 2012-10-22 / 4,485,161,506 | +99.3% (1.993x) | Consistent with 2:1 split |
| WMT | 2023-11-28 / 2,692,233,703 | 2024-03-13 / 8,058,048,674 | +199.3% (2.993x) | Consistent with 3:1 split |
| NVDA | 2021-05-21 / 623,000,000 | 2021-08-13 / 2,500,000,000 | +301.3% (4.013x) | Consistent with 4:1 split |
| NVDA | 2024-05-24 / 2,460,000,000 | 2024-08-23 / 24,530,000,000 | +897.2% (9.972x) | Consistent with 10:1 split |

The only non-split large-jump issue is KO's zero fact. A positivity check is mandatory; the zero and the transition out of it cannot be carried into market cap.

## Split consistency and price-basis implication

The six split-related jumps match the cached Yahoo split events closely:

| Issuer | Split date | Reported split | Adjacent SEC instant ratio | Difference from split ratio |
|---|---|---:|---:|---:|
| AAPL | 2014-06-09 | 7:1 | 6.951x | -0.693% |
| AAPL | 2020-08-31 | 4:1 | 3.976x | -0.589% |
| KO | 2012-08-13 | 2:1 | 1.993x | -0.372% |
| WMT | 2024-02-26 | 3:1 | 2.993x | -0.231% |
| NVDA | 2021-07-20 | 4:1 | 4.013x | +0.321% |
| NVDA | 2024-06-10 | 10:1 | 9.972x | -0.285% |

The small deviations are compatible with ordinary issuance or repurchase activity between the adjacent SEC instant dates. The audit supports that SEC cover-page shares change to the post-split basis after each event.

That consistency also reveals a required transformation: the repository's audited Yahoo historical `Close` behaves as split-adjusted across prior dates, while pre-split SEC facts remain on their contemporaneous pre-split share basis. Multiplying those fields directly would mechanically understate pre-split market capitalization and create a discontinuity at the split. Later construction must either put shares onto the provider's back-adjusted price basis with the corresponding cumulative future split factor, or undo that factor in price to restore the contemporaneous basis, then verify continuity around every split. As in the repository's liquidity policy, a future split factor used solely to reconcile units is not signal information; the underlying share fact must still be selected only when it was publicly available. This audit does not implement either transformation.

## Multiple share classes

The SEC concept definition permits separate dimensional members for multiple classes, but the cached Company Facts observations expose only `accn`, `end`, `filed`, `form`, `fp`, `frame`, `fy`, and `val`; they do not expose the original XBRL context or class dimension. The normalized issuer-level fact therefore cannot reliably assign shares to one listed class, distinguish voting and non-voting classes, or allocate an aggregate count across multiple tickers.

The eight-name sample does not test a dual-listed-class issuer. Results cannot be generalized to securities such as separate Class A/Class C tickers. Later market-cap work should either restrict this source to validated single-common-class issuers or obtain class-specific facts from filing-level XBRL/context data and map them to the security master. Issuer-level shares must never be duplicated across multiple listed classes.

## Not weighted-average basic or diluted shares

`EntityCommonStockSharesOutstanding` is a point-in-time cover-page count. It is distinct from the duration concepts `us-gaap:WeightedAverageNumberOfSharesOutstandingBasic` and `us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding`, both of which are present in the cached issuers and are used as denominators for period earnings per share. Weighted-average basic shares average the common shares outstanding over a reporting period; diluted shares additionally reflect potentially dilutive instruments under accounting rules. Neither represents the actual common shares outstanding on a market date, and neither should substitute for the instant fact in market capitalization.

## Conclusion

Point-in-time common shares from `dei:EntityCommonStockSharesOutstanding` are **suitable as the primary SEC input for later prototype market-cap construction, but not suitable for direct use as currently normalized**. The sample has complete eight-issuer coverage, a regular quarterly filing cadence from 2010 through 2025, no conflicting values by instant date, and strong agreement with six observed split ratios.

Before market cap is implemented, the pipeline must: reject non-positive values; distinguish exact acceptance from filing-date fallback; enforce an explicit staleness limit; reconcile shares and price onto one split basis; and exclude or separately resolve multiple-share-class issuers. Subject to those gates, the latest fact available by signal time is an auditable prototype share-count input. It is not yet a production-grade substitute for a class-level, daily shares-outstanding security master.
