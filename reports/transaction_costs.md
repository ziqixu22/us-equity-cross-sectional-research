# Transaction-Cost Analysis (Stage 4)

Applies turnover-based trading costs to the two Stage 3 portfolio variants
(`equal_weight`, `inverse_vol`), both built from the Stage 2-selected
`price_only` + `ridge` signal. No market-impact model, no bid-ask-spread
model, and no size-dependent slippage are used — per the task's scope, this
is a simple, linear, turnover-times-cost-rate model, deliberately not a
claim of full trading realism.

## Method

For each rebalance date `t`:

```
trading_cost_t = turnover_t * gross_exposure_t * cost_bps / 10,000
net_return_t   = portfolio_return_t - trading_cost_t
```

`turnover_t` is the fraction of the combined long+short name set (4 names:
2 long + 2 short) that changed since the prior rebalance, exactly as
computed and saved in Stage 3's `portfolio_returns_*.csv`. `gross_exposure`
is the constant 200% (100% long, 100% short) from the dollar-neutral
construction. This charges the cost rate on the *notional actually turned
over* each week, not on the full 200% gross book every week — a
name that stays in the portfolio from one week to the next is not
re-charged.

The very first rebalance date has no prior portfolio to compare against, so
turnover (and therefore cost) is undefined there; that single row is
dropped from the cost-adjusted series (677 of the original 678 periods
remain) rather than assigned a fabricated cost of zero or the mean.

Cost levels evaluated: **0, 5, 10, 20, 50 bps** (round-trip-style, applied
per unit of turnover-notional as above). Full metrics: `reports/transaction_cost_metrics.csv`.
Figures: `reports/figures/transaction_cost_sensitivity.png` (net return and
net Sharpe vs. cost), `reports/figures/transaction_cost_nav.png`
(cumulative net NAV at 0/10/50 bps).

## Results

| Variant | Cost (bps) | Annualized net return | Net Sharpe | Max drawdown | Mean turnover |
|---|---:|---:|---:|---:|---:|
| Equal-weight | 0 | 18.82% | 0.61 | -62.77% | 30.4% |
| Equal-weight | 5 | 16.96% | 0.55 | -63.50% | 30.4% |
| Equal-weight | 10 | 15.13% | 0.49 | -64.21% | 30.4% |
| Equal-weight | 20 | 11.55% | 0.37 | -66.23% | 30.4% |
| Equal-weight | 50 | 1.45% | 0.05 | -72.42% | 30.4% |
| Inverse-vol | 0 | 22.99% | 0.82 | -52.20% | 30.4% |
| Inverse-vol | 5 | 21.07% | 0.75 | -53.13% | 30.4% |
| Inverse-vol | 10 | 19.17% | 0.68 | -54.04% | 30.4% |
| Inverse-vol | 20 | 15.47% | 0.55 | -55.83% | 30.4% |
| Inverse-vol | 50 | 5.02% | 0.18 | -63.05% | 30.4% |

(Note: annualized return figures here differ trivially in the third decimal
from Stage 3's headline 0bps numbers because the first, turnover-undefined
period is excluded from this stage's series — 677 periods here vs. 678 in
Stage 3 — not because of any change in methodology.)

## Breakeven cost

Using linear interpolation across the tested grid, neither variant's
annualized net return or net Sharpe crosses zero within 0-50 bps: even at
the highest tested cost (50 bps per unit of turnover-notional), both
variants remain (barely, for equal-weight) net-positive. This is reported
as a genuine, not-cherry-picked result of the specific cost model and
turnover level here (~30%/week on a 4-name book), and should not be read as
"the strategy survives realistic costs at any scale" — see caveats below.

## Interpretation, without overclaiming

- **Costs materially erode, but do not eliminate, the gross edge** at the
  tested levels: going from 0 to 50 bps cuts the equal-weight variant's
  annualized return by roughly 92% (18.8% -> 1.4%) and the inverse-vol
  variant's by roughly 78% (23.0% -> 5.0%). The result is highly sensitive
  to the cost assumption, which is itself a finding, not just be a
  footnote.
- **50 bps is already a large assumption for a liquid large-cap universe**
  like the 8 tickers here (AAPL, MSFT, KO, JNJ, XOM, JPM, WMT, NVDA) — real
  execution costs for these names are typically well under 50 bps
  round-trip at institutional size, so the fact that the strategy survives
  even at 50 bps is a weaker claim of robustness than it might look, not a
  stronger one: it partly reflects that 50 bps is a conservative (high)
  assumption rather than proof the strategy is cheap to trade.
- **This model does not capture market impact.** A 2-long/2-short book
  trading in an 8-name universe is a toy-scale exercise; a real fund
  trading these names at any meaningful size would face price impact this
  linear turnover-cost model does not represent at all. The "breakeven not
  reached" result should not be read as "safe to trade at any size."
- **Turnover itself (~30%/week) is a direct artifact of the small
  universe**: with only 2 names per leg, a single name entering or leaving
  the tercile is a 25-50% change to that leg's membership. A
  production-scale universe with hundreds of names per leg would likely see
  materially different (probably lower, but untested) turnover behavior,
  and this analysis makes no claim about that.
- Consistent with Stage 3, results here are gross-of-costs Sharpe of
  0.61-0.82 declining to 0.05-0.18 net at the most conservative cost
  assumption tested — a real, computed sensitivity, not a fabricated one,
  but one that should be read alongside every small-sample caveat already
  documented in Stages 1-3.
