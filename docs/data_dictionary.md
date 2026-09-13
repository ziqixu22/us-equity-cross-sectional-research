# Milestone 2 Canonical Panel Contract

The conceptual primary key is `(research_date, security_id)`. `symbol` is retained as effective-dated provider metadata and is not a permanent identity claim.

| Field | Meaning | Milestone 2 rule |
|---|---|---|
| `security_id` | internal durable identifier when available | not inferred from ticker alone |
| `symbol` | yfinance symbol used for price retrieval | normalized only for provider syntax, e.g. `BRK.B` → `BRK-B` |
| `observation_time` | time a raw observation was recorded | daily price bars are New York exchange-date observations |
| `available_at` | earliest defensible usable timestamp | price close after close; SEC submission acceptance time when linked |
| `signal_time` | after-close time on final trading day of a week | features may not use a later `available_at` |
| `execution_time` | next-trading-session close in v1 | must be strictly later than `signal_time` |
| `date` | trading-session date | unique with `symbol` for normalized bars |
| `open`, `high`, `low`, `close`, `adjusted_close`, `volume` | retained provider price fields | raw provider fields retained before transformations |
| `dividends`, `stock_splits` | provider corporate-action fields | never silently folded into a price definition |
| `cik`, `accession_number`, `form_type`, `filing_date`, `accepted_timestamp` | SEC lineage and timing fields | required for selected fundamentals where available |

No forward return or later label field belongs in this panel during Milestone 2.

## Milestone 3 weekly fields

`forward_return_1d`, `forward_return_5d`, and `forward_return_20d` are adjusted-close outcomes from execution through exactly 1, 5, or 20 close-to-close intervals. `relative_return_*` subtracts the same-date equal-weight observed cross-sectional mean. Raw price characteristics are `momentum_12_1`, `momentum_6_1`, `momentum_3_1`, prior and signed reversal returns at 1/5/20D, realized/downside volatility, ADV, and `amihud_20d`. Missing means insufficient valid history or future observations; no Milestone 3 feature is imputed.
