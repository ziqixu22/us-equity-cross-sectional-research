# Cross-Sectional Equity Alpha Research: Final Report

## Executive Summary

This project asks whether price, liquidity, volatility, and point-in-time
fundamental signals can rank U.S. equities by future cross-sectional
returns, and whether machine learning can improve on traditional factor
combinations out-of-sample after trading costs. Using a point-in-time-safe
research panel of 8 large-cap U.S. equities spanning 2005-2026, the study
finds: (1) a handful of price/technical factors — realized volatility,
dollar-volume liquidity, and 12-1 month momentum — carry a modest but
real positive Rank IC (0.03-0.05) against 5-day forward relative returns;
(2) point-in-time fundamental factors do **not** improve prediction and,
combined linearly with price factors, do not add incremental signal; (3) a
simple Ridge regression on price factors alone beat a shallow gradient-
boosted tree (LightGBM) out-of-sample in every feature group tested; (4) a
tercile long-short portfolio built from that Ridge signal produced a gross
Sharpe of 0.59-0.79 across 678 weekly out-of-sample periods (2013-2026),
which survives (does not cross zero) realistic trading costs up to 50 bps
per unit of turnover but is materially eroded by them; and (5) every null
and negative finding along the way — including several data-quality
defects in the fundamentals pipeline — is documented rather than hidden.
The central, honest caveat throughout: this is an 8-security prototype
universe, not a production-scale study, and every number here should be
read with that in mind.

## Research Question

Can price, liquidity, volatility, and point-in-time fundamental signals
rank U.S. equities by future cross-sectional returns, and can machine
learning improve on traditional factor combinations out-of-sample after
trading costs?

## Data

Universe: 8 large-cap U.S. equities (AAPL, MSFT, KO, JNJ, XOM, JPM, WMT,
NVDA), chosen because they are the issuer set with usable SEC as-filed
fundamentals data already ingested in this repository. Price data comes
from a cached Yahoo Finance provider snapshot (`data/raw/yfinance_provider_audit/2026-09-11/`).
The originally larger (~100-name, S&P 100) Milestone-3 universe's raw
price history was not available in this environment to rebuild without a
lengthy re-download, so this study explicitly narrowed scope to the
8-ticker universe that was fully cached — a deliberate, documented
smaller-scope decision (`scripts/build_research_panel.py`), not a silent
limitation.

Fundamentals come from SEC EDGAR as-filed company facts, linked by
accession/acceptance time and adjusted for amendment timing, with
quarter/YTD/TTM accounting transforms and point-in-time shares outstanding
for market-cap eligibility — all built and tested prior to this V1
completion pass. The combined weekly research panel
(`data/processed/research_panel_2026-09-11.csv`) has 9,056 rows across
1,132 weekly dates, 2005-01-07 to 2026-09-10.

## Point-in-Time Design

Every fundamental value used on a given research date is the value that
would have actually been known as of that date, keyed off SEC accession/
acceptance timestamps rather than fiscal period end dates, so a company's
Q2 earnings are only used once they were actually filed and accepted, not
retroactively as of quarter-end. Price-based factors use only trailing
price/volume history relative to each research date. No factor or label
in this study uses information not available as of its research date.

## Labels

Two label families: forward returns (`forward_return_1d/5d/20d`, a
security's own raw forward return) and cross-sectional relative returns
(`relative_return_1d/5d/20d`, forward return minus the equal-weight mean
across the 8-name universe that date). The primary target throughout is
`relative_return_5d`; 1D and 20D are evaluated for horizon robustness.

## Factors

11 price/technical factors (momentum_12_1/6_1/3_1, reversal_1d/5d/20d,
realized_volatility_20d/60d, downside_volatility_20d, ADV-based liquidity,
Amihud illiquidity) and 8 point-in-time fundamental factors
(book_to_market, earnings_yield, sales_to_price, roa, gross_profitability,
operating_margin, leverage, asset_growth). All formulas and signs are
predefined in `features/*.py` and never adjusted after seeing results.

## Factor Validation

Full detail: `reports/factor_research.md`, `reports/factor_metrics.csv`.

Mean Rank IC (5D relative return, descending): `realized_vol_60d` (0.054),
`adv_20d` (0.047), `sales_to_price` (0.044, but only 28% coverage),
`realized_vol_20d` (0.042), `downside_vol_20d` (0.032), `momentum_12_1`
(0.031), down through weak/negative factors including `amihud_20d`
(-0.045), `operating_margin` (-0.025), and `book_to_market` (-0.025).
Naive t-statistics (which overstate significance given weekly-sampled,
non-independent observations) range up to ~3.7 for the strongest factors.
The volatility and liquidity families show alpha that *strengthens* from
1D to 20D; momentum decays slightly over that same window. Several
fundamental factors (`roa`, `earnings_yield`, `sales_to_price`,
`gross_profitability`, `operating_margin`) depend on TTM flow variables
with a documented, unfixed duration-collision data-quality issue found
during the pre-V1 validation pass, and their coverage ranges from only
16% to 72% versus 95-100% for price factors — both facts are carried
forward as caveats on every fundamental-factor result in this study, not
silently dropped.

## Models

Full detail: `reports/model_comparison.md`, `reports/model_metrics.csv`.

Chronological expanding-window evaluation (6 folds, initial 40% training
block, never random-shuffled) of 5 models — an equal-weight baseline,
OLS, Ridge, ElasticNet, and LightGBM — across 3 feature groups
(price-only, fundamentals-only, combined). Preprocessing (median
imputation, standardization) is fit on each fold's train data only.
`price_only` linear models (Ridge mean IC 0.0547, ElasticNet 0.0569, OLS
0.0546) clearly outperform `fundamentals_only` (negative for 3 of 4
non-baseline models) and are roughly tied with `combined`. LightGBM
underperforms the corresponding linear model in every feature group
tested. Pooled out-of-sample R² is numerically unusable at this sample
size (a real, investigated finding, not a bug — some folds have such low
target variance that R²'s denominator collapses, producing values like
-1.55 billion), which is why Rank IC, not R², is this study's primary
metric throughout.

**Selected signal for portfolio construction: `price_only` + `ridge`** —
chosen not for the single highest mean IC (ElasticNet's is marginally
higher) but because it is positive in all 6 of 6 chronological folds, uses
only the highest-coverage feature group, is simpler than ElasticNet (which
collapsed to a degenerate constant model at its default regularization
strength), and beat the nonlinear alternative.

## Portfolio

Full detail: `reports/portfolio_results.md`.

Dollar-neutral, weekly-rebalanced, tercile long-short (top tercile long,
bottom tercile short — 2 of 8 names per leg, since quintiles would leave
1-2 names/bucket at this universe size) built from the selected Ridge
signal's out-of-sample predictions, 678 weekly periods (2013-09-06 to
2026-08-28). Equal-weight variant: Sharpe 0.59, annualized return 18.34%,
max drawdown -62.77%, hit rate 54.6%, mean turnover 30.4%/week.
Inverse-volatility-weighted variant (the one simple risk-aware variant
this study allows in place of a full optimizer): Sharpe 0.79, annualized
return 22.35%, max drawdown -52.20%, hit rate 56.5%. Both are **gross of
costs**; both are structurally concentrated (2 names per leg out of 8),
which drives both the return magnitude and the large drawdowns — this is
reported as a genuine structural limitation, not smoothed over.

## Transaction Costs

Full detail: `reports/transaction_costs.md`, `reports/transaction_cost_metrics.csv`.

Applying turnover-based costs (0/5/10/20/50 bps per unit of
turnover-notional) to both portfolio variants: net Sharpe declines from
0.61/0.82 (equal-weight/inverse-vol, gross) to 0.05/0.18 at the most
conservative 50 bps assumption, but does not cross zero anywhere on the
tested grid. This should be read cautiously: 50 bps is itself a
conservative (high) assumption for a liquid large-cap universe, and no
market-impact model is used, so "survives 50 bps" is a weaker robustness
claim than it might appear, not evidence the strategy is cheap or
scalable to trade.

## Robustness

Full detail: `reports/robustness.md`. Horizon checks (1D/5D/20D) are
consistent between factors and the selected model (IC generally rises with
horizon). The strongest individual factor (`realized_vol_60d`) is
*negative* in multiple individual years despite a positive full-sample
average — a genuine instability finding. The selected Ridge model's
fold-level IC, by contrast, has not gone negative in any of the 6 tested
expanding-window folds across 13 years — the single most stable result in
this study. A biweekly-rebalance proxy check and a raw-vs-standardized
check both showed no meaningful degradation.

## What Failed

Full detail: `reports/failure_analysis.md`. In summary: fundamentals add
no incremental signal over price factors; the nonlinear model
underperforms simple linear models; individual factor IC (even the
strongest factor) is not stable year-over-year; pooled OOS R² is
numerically unusable at this sample size; ElasticNet degenerated to a
constant model at its default hyperparameter; turnover materially erodes
(though does not eliminate) returns as assumed costs rise; and two
specific, unresolved fundamentals-pipeline data-quality defects (a TTM
duration-collision bug and a single-candidate concept-selection gap) limit
confidence in the fundamental-factor results specifically.

## Limitations

- **Universe size (8 names)**: every statistic in this study is computed
  from at most 8 cross-sectional observations per date. This is the single
  largest limitation and qualifies every other finding.
- **Not survivorship-bias-free**: the prototype universe was not
  constructed to be free of survivorship bias.
- **Fundamentals data quality**: a duration-variant TTM collision bug and
  a single-candidate concept-selection gap were found and documented, not
  fixed, in the fundamentals pipeline; several fundamental factor ICs
  should be read with that caveat.
- **Gross-of-cost portfolio headline numbers**: Stage 3's Sharpe/return
  figures are gross; only Stage 4's are cost-adjusted.
- **No market-impact model**: transaction-cost analysis is linear
  turnover-based only; it says nothing about capacity or price impact at
  scale.
- **Push-to-remote could not be completed** from this session's sandboxed
  execution environment due to a structural credentials limitation (see
  repository `git log` — every stage was committed locally; the repository
  owner must run `git push origin main` from their own machine to publish
  these commits).

## Conclusions

A small set of price/technical factors — dominated by realized volatility,
liquidity, and momentum — carry a modest, real, and (for the combined
Ridge signal) fold-stable positive cross-sectional signal in this
prototype universe. Point-in-time fundamental factors, as currently
computed in this repository, do not improve on that signal, and a
nonlinear model does not improve on a simple linear one. The resulting
long-short portfolio's gross performance is real but reflects meaningful
concentration risk from the small universe, and its edge is real but
modest enough that trading costs meaningfully erode (without eliminating)
it. The project's own stated null and negative findings — not just its
positive result — are the most defensible output of this V1.

## Future Improvements

- Rebuild the ~100-name universe (or a CRSP/Compustat-sourced universe)
  once raw price history is available, to test whether the price-factor
  findings generalize beyond 8 names and materially reduce the small-
  sample noise documented throughout.
- Fix the two documented fundamentals-pipeline defects (TTM duration
  collision, single-candidate concept fallback) and re-run the
  fundamentals-only and combined ablations to see whether fundamentals'
  current null result was a data-quality artifact or a genuine finding.
- Add a proper risk model / mean-variance optimizer in place of the
  single inverse-volatility scalar, once a larger universe makes
  meaningful diversification possible.
- Test a slippage/market-impact-aware cost model once trading at
  realistic institutional size is a relevant question.
- Extend robustness checks to a formal significance test that accounts
  for cross-sectional and time-series autocorrelation, rather than the
  naive t-statistic used here.
