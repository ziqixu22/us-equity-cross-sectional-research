# V1 Research Specification

## Approved Milestone 2 data and timing decisions

- Daily bars are retained as raw inputs. Signals are observed only on the final trading day of each week; daily observations are never pre-aggregated before feature construction.
- At close of weekly signal date \(t\), features may use information through that close. The signal is formed after close; idealized execution is close of the next trading session \(t+1\). A five-session outcome is \(P_{t+6}/P_{t+1}-1\), so the portfolio cannot earn the close-\(t\) return.
- `yfinance` is the Tier-1 research/education provider. Calls use `auto_adjust=False`, `actions=True`, cache raw fields locally, and retain download time and package version. The adapter boundary remains replaceable by CRSP/WRDS.
- SEC fundamentals use an as-filed policy. For a fact, the eligible value at signal time is the latest filing version available by that time. Company Facts `accn` links facts to submissions metadata; `acceptanceDateTime` is preferred. If that link/timestamp is unavailable, the conservative fallback is availability on the next trading session after `filingDate`.
- V1 signal neutralization is size only. Current-sector fields can support exposure diagnostics but are not evidence of historical industry neutrality.
- The current S&P 100 snapshot is acceptable only as a prototype universe. Every later research result must state that its historical panel is not survivorship-bias-free.
- Forward-return horizon \(h\) is an explicit count of close-to-close intervals after execution: \(R_h(t)=P_{t+1+h}/P_{t+1}-1\). Thus \(R_1=P_{t+2}/P_{t+1}-1\), \(R_5=P_{t+6}/P_{t+1}-1\), and \(R_{20}=P_{t+21}/P_{t+1}-1\).

## Hypothesis

Past price and trading activity contain a modest, testable ranking signal for the next five trading sessions' cross-sectional relative total return. Non-linear boosting may improve the ranking relative to Ridge, but any apparent gain may vanish after time-aware evaluation and cost assumptions.

## What would change the conclusion

- Predictive metrics do not persist across validation years.
- Gains arise only from a small number of securities or one year.
- Boosting adds no stable value over Ridge after identical timing and feature controls.
- Net portfolio results disappear at modest pre-declared cost scenarios.
- Data audit identifies a material unresolved adjustment, universe, or timing defect.

## Non-negotiable guardrails

1. No random row split; all folds are defined on unique market dates.
2. No test-period tuning after examining final results.
3. Do not add features/window lengths because a previous run was weak.
4. Preserve the complete experiment log, including failures.
5. The free current-universe prototype must be called a prototype in README, memo and resume discussion.
6. Weekly research scheduling must not cause daily inputs to be aggregated before feature construction.
7. A feature's `available_at` must be no later than `signal_time`, and `signal_time < execution_time`.

## Reporting

Each model reports annual date-level Rank IC, coverage, quintile monotonicity, gross/net ledger returns, turnover, cost sensitivity, drawdown, and limitations. A positive IC is not called an executable alpha without demonstrating economically plausible implementation.
