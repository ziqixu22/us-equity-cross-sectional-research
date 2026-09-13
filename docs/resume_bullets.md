# Resume Bullets

Three variants for the same project, each emphasizing a different angle.
All figures are real, computed results from this repository's
`reports/` — see `reports/final_research_report.md` for the source of
every number. No metric below is fabricated or projected.

## Variant 1: Quant Research

- Built a point-in-time-safe cross-sectional equity research pipeline
  (SEC EDGAR fundamentals + Yahoo price data) with chronological,
  never-random out-of-sample evaluation, validating 19 price and
  fundamental factors via Spearman Rank IC, quantile spreads, and
  alpha-decay analysis across 1D/5D/20D horizons.
- Identified and validated 5 factors (realized volatility, ADV liquidity,
  12-1 month momentum) with fold-stable mean Rank IC of 0.03-0.05 on a
  5-day cross-sectional relative-return target, while explicitly ruling
  out fundamentals as an incremental predictor after testing them
  head-to-head in a linear model.
- Diagnosed and documented a numerical instability in out-of-sample R² at
  small sample sizes (values as extreme as -1.55 billion in one ablation),
  motivating Rank IC as the study's primary evaluation metric and avoiding
  a misleading model-selection criterion.

## Variant 2: Systematic Equities

- Designed and backtested a dollar-neutral, tercile long-short equity
  strategy from a Ridge-regression signal combination, achieving a gross
  Sharpe ratio of 0.79 across 678 out-of-sample weekly rebalances
  (2013-2026), with full turnover and drawdown accounting.
- Built a turnover-based transaction-cost model (0-50 bps sensitivity)
  showing the strategy's net Sharpe survives (does not turn negative)
  under conservative cost assumptions while quantifying a ~78-92%
  reduction in annualized return at the highest tested cost level.
- Ran systematic robustness checks (return-horizon sensitivity,
  year-by-year factor stability, rebalance-frequency sensitivity) and
  reported that even the strongest individual factor's Rank IC is
  negative in several individual years, despite a positive full-sample
  average — a materiality-focused, non-overstated read of the results.

## Variant 3: ML Quant

- Implemented a chronological expanding-window model-evaluation framework
  (scikit-learn Ridge/OLS/ElasticNet, LightGBM) with train-only
  preprocessing fit (median imputation + standardization) to eliminate
  look-ahead leakage, verified by dedicated unit tests asserting no test
  row is ever predicted using future training data.
- Benchmarked a shallow gradient-boosted tree against linear baselines
  across 3 feature groups and found the nonlinear model underperformed
  in every configuration (e.g. 0.038 vs. 0.055 mean Rank IC on price
  factors) — reported the negative result rather than tuning toward a
  preferred outcome.
- Selected a production candidate signal (Ridge on price-only factors,
  positive out-of-sample Rank IC in 6 of 6 chronological folds) using an
  explicit, multi-criteria decision (fold consistency, feature-coverage
  robustness, model simplicity) rather than a single in-sample metric.
