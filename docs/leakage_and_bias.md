# Leakage and Bias Register

## Binding time convention

For weekly research date \(t\), a signal is formed after the market close using daily data available through that close. The earliest v1 execution is the next trading session's close, \(t+1\). The first return earned is therefore the close-to-close return from \(t+1\) to \(t+2\), not any return ending at close \(t\). Horizon \(h\) always means exactly \(h\) return intervals: \(R_h(t)=P_{t+1+h}/P_{t+1}-1\). A five-session label is therefore \(P_{t+6}/P_{t+1}-1\), never an ambiguous “fifth day after execution.”

Every feature row must satisfy `max(feature.available_at) <= signal_time < execution_time`. The code rejects a violation rather than shifting it silently.

## Fundamental information boundary

Fiscal period end is never an availability timestamp. Company Facts records carry filing date and accession number but not an acceptance timestamp in the observed sample. The submission feed carries `acceptanceDateTime` and `accessionNumber`; the production join will use that link. An original filing remains the historical value until an amended filing is itself public. If a defensible acceptance time cannot be linked, the fact is available only from the next trading session after its filing date.

## Universe bias and identifiers

The prototype is a snapshot of **current** S&P 100 constituents filtered by current price, liquidity, and history. It is not a historical-membership universe, does not establish that delisted names are represented, and is not survivorship-bias-free. `symbol` is a provider key only; future joins must retain SEC CIK/accession lineage and use an effective-dated mapping when a durable security identifier becomes available.

Current S&P sector labels are retained only as a present-day exposure diagnostic. They cannot be used to claim historical industry neutralization.

## Provider and adjustment limitations

Yahoo/yfinance is an unofficial public-data route. It can revise history, does not provide an institutional securities master or delisting returns, and its adjustment conventions must be treated as observed provider behavior—not assumed economic truth. Raw `Close`, `Adj Close`, dividends, and splits are retained separately. The price audit is required before scaling data collection.

## Other controls

- Cross-sectional transformations and model preprocessing are fit using training information only.
- Overlapping labels are purged at chronological split boundaries.
- Universe membership, raw retrieval time, provider version, and configuration are recorded per run.
- Trial definitions and failures remain in the research log to limit factor-mining and final-test leakage.
