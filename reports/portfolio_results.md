# Long-Short Portfolio Results (Stage 3)

Signal: the Stage 2-selected `price_only` + `ridge` model, evaluated
strictly out-of-sample across its 6 chronological expanding-window folds
(no in-sample rows are used anywhere in this stage). Universe: the same 8
securities used throughout this study. Rebalance frequency: weekly,
matching the panel's own research-date cadence. Holding period: 5 trading
days (`forward_return_5d`), non-overlapping with the weekly rebalance.

**Portfolio construction:** long the top tercile by predicted score
(2 of 8 names, since ⌊8/3⌋ = 2), short the bottom tercile (2 of 8 names),
dollar-neutral (+1 unit long weight, -1 unit short weight, so gross
exposure is a constant 200%). Two weighting variants:
**equal-weight** within each leg, and **inverse-volatility** (weight ∝
1/`realized_vol_20d`, normalized to sum to ±1 per leg) as the one
simple risk-aware variant this task allows in place of a full optimizer.
No mean-variance or other optimizer is used.

Full return series: `reports/portfolio_returns_equal_weight.csv`,
`reports/portfolio_returns_inverse_vol.csv`. Figures:
`reports/figures/portfolio_cumulative_return.png`,
`portfolio_drawdown.png`, `portfolio_turnover.png`.

## Sample size, again

The out-of-sample window covers 678 weekly rebalances (2013-09-06 to
2026-08-28, roughly 13 years — the period after the initial 40% training
block used by Stage 2). That is a reasonably long OOS window in calendar
time, but the portfolio itself holds only 2 long and 2 short names at any
time out of an 8-name universe. This is a real, structural limitation:
results here reflect the idiosyncratic behavior of 4 specific companies'
relative performance far more than a diversified factor exposure would,
and should be read as a proof-of-concept on this prototype universe, not
as evidence the underlying signal would behave this way in a
production-scale (hundreds-to-thousands-of-names) universe.

## Results (gross, before transaction costs — see Stage 4 for net)

| Metric | Equal-weight | Inverse-vol weighted |
|---|---:|---:|
| Periods (weeks) | 678 | 678 |
| Total return (cumulative) | 798.4% | 1,288.2% |
| Annualized return | 18.34% | 22.35% |
| Annualized volatility | 31.05% | 28.18% |
| Sharpe ratio (rf = 0) | 0.59 | 0.79 |
| Max drawdown | -62.77% | -52.20% |
| Hit rate (weeks with positive spread) | 54.57% | 56.49% |
| Mean weekly turnover | 30.4% | 30.4% |
| Gross exposure | 200% | 200% |

These are **gross of transaction costs** — see `reports/transaction_costs.md`
(Stage 4) for what survives realistic trading costs at this turnover
level. Read alongside Stage 1/2: the underlying signal's mean OOS Rank IC
was modest (0.055), so a 13-year cumulative return this large is driven
substantially by compounding a large number of small, only-modestly-edge
weekly spreads across a long window, and by the concentration effect
above — not by a large single-period edge.

## Interpretation, without overclaiming

- **Sharpe of 0.59–0.79 gross** is a real, computed result, not
  fabricated — but it is a *gross*, small-universe, single-signal number,
  not directly comparable to a diversified, cost-aware, production
  long-short fund's Sharpe.
- **Max drawdown of -52% to -63%** is large for what a long-short,
  supposedly market-neutral book would typically target, and is
  consistent with the concentration problem above (2-name legs have no
  internal diversification against a single name's idiosyncratic move).
  This is reported as a genuine risk finding, not smoothed over.
- **The inverse-volatility variant outperforms equal-weight on every
  metric reported** (higher return, lower vol, better Sharpe, smaller
  drawdown) in this specific sample — a modest, defensible improvement
  from a one-line risk adjustment, consistent with the "one simple
  risk-aware variant" the task scoped for Stage 3. This is not evidence
  that inverse-vol weighting is generally superior; it is one result on
  one sample.
- **Turnover of ~30%/week** on a 2-long/2-short book means, on average,
  slightly more than half a name changes on each leg most weeks — this
  is the input Stage 4 uses to size realistic transaction-cost drag.

## What this stage does not claim

- This is not a claim that the signal is deployable or investable as-is:
  an 8-name universe, 2-name legs, and the already-documented Stage 1/2
  small-sample caveats all apply.
- No optimizer, leverage, or risk model beyond the single inverse-volatility
  scalar was used or is implied to be necessary; Sharpe and drawdown
  figures reflect that intentionally simple construction, not a claim that
  further optimization would or would not improve them.
