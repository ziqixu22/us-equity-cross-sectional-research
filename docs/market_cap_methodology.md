# Market-Cap Eligibility and Share-Basis Methodology

## Scope

`fundamentals.market_cap.build_market_cap` is a narrow prototype layer. It joins a signal-date Yahoo price with the latest SEC `dei:EntityCommonStockSharesOutstanding` fact that was public by the signal time, evaluates eligibility, and retains its provenance. It does not build a fundamental panel or a valuation ratio.

## Canonical historical basis

The selected price is Yahoo historical `Close` on the cache's split-adjusted basis. The canonical share basis is therefore **the number of common shares expressed on the same price-cache basis as of `price_basis_as_of`**.

The caller supplies an explicit split-event table from the same audited Yahoo cache: `security_id`, `split_date`, and positive `split_ratio`. For a share fact measured at instant `s`, the adjustment factor is:

`product(split_ratio for split_date > s and split_date <= price_basis_as_of)`.

`shares_split_adjusted = shares_raw × split_adjustment_factor` and, only when eligible, `market_cap = price × shares_split_adjusted`.

This rule does not infer a split from a price or share-count jump. It is reproducible from cached corporate-action records, bounded by the explicit price-cache snapshot date, and is necessary because the price cache retrospectively expresses earlier prices on a later split basis. Split factors reconcile units only; public availability of the SEC fact remains the information-timing gate.

The caller must set `split_history_complete` for each security/signal observation. A false or missing assertion, missing/invalid split ratio, or non-positive ratio produces `split_basis_unresolved` and no market cap. A zero-event history is acceptable only when the caller has explicitly verified that history as complete.

Every output row records `price_basis_as_of`, `split_history_cutoff`, and `market_data_download_timestamp`. Future split ratios in the factor are provider-basis unit normalization only, never predictive information or an eligibility substitute for the SEC fact's own `available_at`.

## Eligibility rule

`market_cap_eligible` is true exactly when all of the following hold:

- The latest selected `shares_outstanding` fact has `unit == "shares"` and a positive numeric value.
- `shares_available_at <= signal_time`; no later filing is selected.
- The share instant is no older than the registered staleness threshold.
- Its availability is an exact acceptance timestamp or the documented filing-date-plus-one-day fallback.
- The split history is complete and produces a resolvable factor.
- `multiple_share_class_flag` is explicitly false.
- Signal price is positive and finite.

Otherwise `market_cap` is missing and `market_cap_limitation_flag` contains one or more machine-readable reasons, including `nonpositive_shares`, `shares_unavailable`, `unit_mismatch`, `availability_unresolved`, `stale_shares`, `split_basis_unresolved`, or `multiple_share_class_unresolved`.

The returned audit columns are `shares_raw`, `shares_split_adjusted`, `shares_instant_date`, `shares_available_at`, `shares_age_days`, `shares_accession`, `shares_acceptance_source`, `split_adjustment_factor`, `multiple_share_class_flag`, `market_cap_eligible`, `market_cap_limitation_flag`, and `market_cap`.

## Staleness rule

The pre-registered prototype limit is **130 calendar days**, exposed as `DEFAULT_STALENESS_LIMIT_DAYS` and an explicit `staleness_limit_days` parameter. This is a reporting-mechanics choice, not a return-optimized parameter: the share audit measured a 91-day median observation interval and a 39-day maximum initial filing lag, which sum to 130 days. It rejects cached KO (136 days) and XOM (164 days) at the audit snapshot rather than extending quarterly data indefinitely. A later data-quality study may report sensitivity to alternative limits; it must not tune the limit on IC or backtest outcomes.

## Split examples

- AAPL shares dated 2014-04-11 are multiplied by `7 × 4 = 28` using the explicit 2014-06-09 and 2020-08-31 split records. This is compatible with the later-basis Yahoo historical Close cache.
- NVDA shares dated 2021-05-21 are multiplied by `4 × 10 = 40` using the explicit 2021-07-20 and 2024-06-10 split records.

The prior audit found adjacent SEC share-count ratios of 6.951x and 3.976x for those AAPL events, and 4.013x and 9.972x for those NVDA events, consistent with the reported splits plus ordinary share-count changes between SEC instants.

## Multiple share classes

Company Facts does not retain the filing XBRL context needed to allocate an issuer-level count to separate listed share classes. The layer deliberately performs no reconstruction. Any unknown or true `multiple_share_class_flag` makes the security ineligible, avoiding duplicated issuer shares across tickers. A class-specific security master or filing-level context mapping is required before such securities can be admitted.
