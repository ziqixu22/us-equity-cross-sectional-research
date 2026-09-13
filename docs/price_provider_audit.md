# Price Provider Audit — yfinance

**Audit date:** 2026-09-11. **Package:** yfinance 1.2.0. **Request:** 1990-01-01 through 2026-09-11, `auto_adjust=False`, `actions=True`, `repair=False`, `keepna=True`.

## Sample and observed schema

The sample was AAPL, MSFT, KO, JNJ, XOM, JPM, WMT, NVDA, AMZN, and TSLA: established/dividend-paying issuers, several sectors, and distinct capitalization profiles. All ten requests succeeded. Returned columns were `Open`, `High`, `Low`, `Close`, `Adj Close`, `Volume`, `Dividends`, and `Stock Splits`; the index was `America/New_York` date/time. The last available session in this retrieval was 2026-09-10, so a calendar date must not be treated as proof that a same-day close is available.

## Corporate-action observations

Separate split events were returned for known events, including AAPL 4:1 on 2020-08-31, NVDA 10:1 on 2024-06-10, TSLA 5:1 on 2020-08-31, and WMT 3:1 on 2024-02-26. Around each of these events, returned `Close` values did not show the corresponding mechanical split-sized drop; the price history is therefore already split-adjusted in a provider-specific sense even when `auto_adjust=False`. Dividend-paying names showed non-constant `Adj Close / Close` ratios (for example, AAPL 0.782–1.000; KO 0.417–1.000), while AMZN and TSLA were 1.000 in this sample.

The pipeline will preserve `Close` and `Adj Close` separately. The v1 total-return label will use the approved adjusted-price convention only after Milestone 3 formula tests; raw OHLC and action fields remain available for audit.

## Quality checks

No duplicate `(symbol, date)` rows were found. Dates were continuous relative to the union of the sample's observed sessions once later IPOs were excluded; this is a comparison diagnostic, not a U.S. exchange-calendar proof. NVDA, AMZN, and TSLA naturally have shorter histories because of their listing dates. Raw-close moves above 20% without a reported split were flagged (AAPL 5, JPM 5, NVDA 17, AMZN 19, TSLA 4); these are investigation flags, not evidence of errors.

## Limitations

The audit does not prove vendor correction behavior, delisting treatment, full corporate-action completeness, intraday timing, or institutional quality. Raw responses and the retrieval manifest are cached locally and ignored by Git. Re-run `scripts/audit_price_provider.py` to reproduce this audit.
