# Cross-Sectional Equity Alpha Research

**Can price, liquidity, volatility, and point-in-time fundamental signals rank U.S. equities by future cross-sectional returns — and can machine learning improve on traditional factor combinations out-of-sample, after trading costs?**

This matters because it is the core question behind any systematic
equity strategy: does a signal actually predict *relative* performance
before it is spent on costs, and does adding complexity (fundamentals, a
nonlinear model) actually help, or just add risk of overfitting? This
project answers both questions honestly on a small prototype universe,
including reporting the things that did *not* work.

**Full results:** [`reports/final_research_report.md`](reports/final_research_report.md) ·
**Interview-ready summary:** [`reports/interview_summary.md`](reports/interview_summary.md) ·
**What failed:** [`reports/failure_analysis.md`](reports/failure_analysis.md)

## Pipeline

```
Point-in-Time Data (SEC EDGAR + Yahoo prices)
        │
Point-in-Time Factors (11 price/technical, 8 fundamental)
        │
Factor Validation (Rank IC, quantile spreads, decay, stability)
        │
ML Signal Combination (baseline / OLS / Ridge / ElasticNet / LightGBM,
                        chronological expanding-window OOS)
        │
Long-Short Portfolio (tercile, dollar-neutral, weekly rebalance)
        │
Transaction Costs (0/5/10/20/50 bps, turnover-based)
        │
Robustness + Failure Analysis
        │
Final Report / Resume / Interview Summary
```

## Data and point-in-time methodology

Universe: 8 large-cap U.S. equities (AAPL, MSFT, KO, JNJ, XOM, JPM, WMT,
NVDA). The runner caches Yahoo Finance prices and SEC EDGAR Company Facts
and submissions for this fixed universe.

The fundamental panel uses SEC filing acceptance timestamps where available
and a conservative filing-date fallback otherwise. It retains accession
lineage, accounts for amendments and quarter/YTD/TTM durations, and uses
as-filed shares outstanding for market-cap eligibility. Forward returns
serve as outcome labels. Factor signs are fixed before evaluation.

This is a deliberately small **prototype** universe, not a
production-scale study — see [Limitations](#limitations).

## Factor families

- **Price/technical (11)**: momentum (12-1, 6-1, 3-1 month), reversal
  (1d/5d/20d), realized volatility (20d/60d), downside volatility (20d),
  ADV-based liquidity, Amihud illiquidity.
- **Fundamental (8, point-in-time)**: book-to-market, earnings yield,
  sales-to-price, ROA, gross profitability, operating margin, leverage,
  asset growth.

## Validation framework

Cross-sectional Spearman Rank IC by date, mean/median/std/ICIR,
positive-IC frequency, quantile portfolio spreads, alpha decay across
1D/5D/20D horizons, year-by-year stability, and week-over-week factor
persistence. Full methodology and results:
[`reports/factor_research.md`](reports/factor_research.md).

## ML models

Chronological expanding-window evaluation (never random-shuffled): an
equal-weight baseline, OLS, Ridge, ElasticNet, and LightGBM, each
evaluated on price-only, fundamentals-only, and combined feature groups.
All preprocessing is fit on training data only. Full methodology and
results: [`reports/model_comparison.md`](reports/model_comparison.md).

## Portfolio construction

Dollar-neutral, weekly-rebalanced, top-tercile-long / bottom-tercile-short
(terciles rather than quintiles, appropriate for an 8-name universe), with
an equal-weight and an inverse-volatility-weighted variant. Full
methodology and results:
[`reports/portfolio_results.md`](reports/portfolio_results.md).

## Transaction costs

Trading cost scenarios use 0/5/10/20/50 bps per unit of traded notional.
The [historical cost report](reports/transaction_costs.md) documents the
original turnover proxy.

## Historical V1 results

The figures below and the linked narrative reports archive the original study.
The revised pipeline changes training-label timing, SEC duration handling,
holding periods, and trading-cost accounting. Results from a new run are
written to `research_summary.md`.

| Stage | Headline result |
|---|---|
| Factors | Strongest: `realized_vol_60d`, `adv_20d`, `realized_vol_20d`, `downside_vol_20d`, `momentum_12_1` (mean Rank IC 0.03-0.05). Weakest/negative: `amihud_20d`, `operating_margin`, `book_to_market`. |
| Models | `price_only` + Ridge selected: positive OOS Rank IC in 6/6 chronological folds (mean 0.0547). Fundamentals do not improve prediction; LightGBM underperforms linear models in every feature group. |
| Portfolio | 678 weekly OOS periods (2013-2026), gross: Sharpe 0.59 (equal-weight) / 0.79 (inverse-vol), max drawdown -63% / -52%. |
| Costs | Net Sharpe falls to 0.05 / 0.18 at 50 bps but does not cross zero in the tested 0-50 bps range. |

All numbers above are real, computed results with full detail and
caveats in the linked reports — none are illustrative or aspirational.

## Robustness and what failed

Robustness checks (horizon, year-by-year stability, rebalance frequency,
raw vs. standardized factors, fold-level model stability) are in
[`reports/robustness.md`](reports/robustness.md). This project treats
null and negative findings as required output, not something to hide —
see [`reports/failure_analysis.md`](reports/failure_analysis.md) for a
consolidated list, including: fundamentals add no incremental signal, the
nonlinear model underperforms linear models, individual factor IC is not
stable year-over-year even for the strongest factor, and out-of-sample R²
is numerically unusable at this sample size (motivating Rank IC as the
primary metric throughout).

## Limitations

- **8-security prototype universe** — every statistic here is computed
  from at most 8 cross-sectional names per date, not a production-scale
  universe. The originally larger (~100-name) universe's raw price
  history was not available to rebuild in this environment; this is a
  documented scope decision, not a silent gap.
- Prototype universe is not survivorship-bias-free.
- The historical fundamental-factor results are affected by the two accounting issues described in
  `reports/fundamental_factor_audit.md`. The revised pipeline retains duration variants and registered concept aliases.
- Portfolio headline Sharpe/return figures in Stage 3 are gross of costs;
  see Stage 4 for cost-adjusted figures.
- No market-impact or capacity model.

## Repository structure

```text
.
├── src/us_equity_cross_sectional/
│   ├── data/            # Yahoo Finance price adapter
│   ├── fundamentals/    # SEC EDGAR PIT ingestion, as-of panel construction
│   ├── features/        # Momentum, reversal, volatility, liquidity, fundamental factors, labels
│   ├── research/         # Factor evaluation and model evaluation frameworks
│   ├── models/           # Signal-combination model definitions
│   └── portfolio/        # Long-short portfolio construction and performance metrics
├── scripts/              # Panel build and stage-by-stage research scripts
├── reports/              # All generated research reports, metrics CSVs, and figures
├── docs/                 # Resume bullets, data contracts
└── tests/                # Unit tests
```

## Reproduce the research

Install the package and run the test suite from the repository root with Python 3.10 or later.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
```

Set `SEC_USER_AGENT` in your shell to your name or organization followed by a contact email.
See the [SEC developer guidance](https://www.sec.gov/about/developer-resources).
Run the entire pipeline in a dedicated output directory.

```bash
export SEC_USER_AGENT="Researcher name contact@example.com"
python scripts/run_research.py --as-of 2026-09-11 --run-dir runs/2026-09-11
```

The command downloads the eight Yahoo histories and SEC Company Facts and submissions,
then generates the accounting panel, fundamental factors, combined research panel,
factor and model comparisons, portfolio, costs, robustness checks, and
`reports/research_summary.md`. The price cutoff is exclusive. A fresh download can
differ from the archived snapshot because providers revise their data. The manifest
records retrieval information and a successful run records SHA-256 hashes of all
inputs and package versions. An incomplete provider download stops the run and records
which requests failed.

For an offline rerun, place the cached files in the following structure inside the run
directory and add `--offline` to the same command. Cached files and outputs stay local.

| Path inside run directory | Required inputs |
|---|---|
| `data/raw/yfinance_provider_audit/<as-of>/` | Eight ticker CSVs with daily bars and corporate actions |
| `data/raw/sec_provider_audit/<as-of>/` | `<ticker>_companyfacts.json` and `<ticker>_submissions.json` for all eight tickers |
| `data/manifests/` | `yfinance_provider_audit_<as-of>.json` and `sec_fundamentals_audit_<as-of>.json` |

### Revised methodology

- Market features use the last observed session of each Friday-ended week.
  For SEC facts, the cutoff is conservatively set at 1:00 p.m. ET to accommodate
  shortened sessions. Reports accepted later that day enter the next weekly signal.
- The model keeps its next-session-close entry and fixed 1-, 5-, or 20-session labels.
  Each fold purges training observations whose labels mature on or after the first
  test signal date.
- The weekly portfolio holds to the following rebalance's execution close.
  Costs use signed position changes against drifted gross weights, including
  entry and liquidation. Sharpe uses annualized arithmetic mean excess return
  over annualized volatility, with a zero risk-free rate.
- Comparisons remain exploratory on the frozen eight-name universe. Results on
  overlapping historical dates are descriptive because price-only Ridge was selected
  in the original study. Cost sensitivity covers trading fees with a gross-weight
  drift approximation. Borrow fees and market impact are outside the model.

## For recruiters / interviewers

[`docs/resume_bullets.md`](docs/resume_bullets.md) has three resume-bullet
variants (Quant Research, Systematic Equities, ML Quant).
[`reports/interview_summary.md`](reports/interview_summary.md) has a
30-second answer, a 2-minute answer, and a detailed technical walkthrough
of every design decision in this project.

## Learn it for interviews

Use the project-specific [Interview Guide](docs/INTERVIEW_GUIDE.md) for a walkthrough of the methodology, key concepts, likely interview questions, and the limitations of the research.
