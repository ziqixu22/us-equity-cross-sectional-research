# V1 Research Specification

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

## Reporting

Each model reports annual date-level Rank IC, coverage, quintile monotonicity, gross/net ledger returns, turnover, cost sensitivity, drawdown, and limitations. A positive IC is not called an executable alpha without demonstrating economically plausible implementation.
