# US Equity Cross-Sectional Return Prediction and Robustness Research

An evidence-first Quant Research portfolio project: test whether a small, pre-specified set of price and volume features predicts five-trading-day cross-sectional relative returns, and whether any incremental prediction survives out-of-sample evaluation and transparent trading-cost assumptions.

## Research question

> At the close of trading day *t*, can information available by then rank U.S. equities by their relative total return from the close of *t+1* to the close of *t+6*?

The first version compares a zero-prediction baseline, univariate sorts, Ridge regression, and one gradient-boosting model. It reports failures as results; it does not optimize until a backtest looks attractive.

## Free, Mac-friendly data plan

The executable **prototype** uses [`yfinance`](https://github.com/ranaroussi/yfinance) with a locally frozen current-universe CSV. It is free, works locally on macOS, and can download daily OHLCV for a controlled sample of liquid U.S. securities.

This is deliberately not described as a survivorship-bias-free U.S. equity study. `yfinance` is an unofficial, research/education-oriented wrapper around Yahoo's public APIs; the downloaded data is subject to Yahoo's terms. The current-universe prototype is for validating the research pipeline, not for making a broad historical-universe claim.

For a rigorous extension, the code is organized so that a licensed CRSP/WRDS adapter can replace the prototype adapter without changing feature, split, model, or portfolio interfaces. The repository will never publish commercial raw data or API keys.

### Why not use Open Source Asset Pricing as the main data source?

The [Open Source Asset Pricing](https://www.openassetpricing.com/data/) release is excellent for a separate factor-stability extension: it provides stock-level characteristics and daily/monthly **portfolio** returns, with most current data through December 2024. It is not a complete stock-level daily return database for this five-day individual-equity prediction task. Its ready-made signals are also signed according to original papers, so it should not be used to claim an independent discovery of alpha.

## Pre-registered v1 specification

| Component | Decision |
|---|---|
| Signal timing | Compute at close of *t*; earliest idealized execution is close of *t+1*. |
| Label | Total return from close *t+1* to close *t+6*, minus the equal-weight return of the eligible universe on the same signal date. |
| Features | 12-month momentum excluding the latest 21 sessions; 5-day reversal; 20-day realized volatility; 5-day/60-day dollar-volume ratio; log 60-day average dollar volume. |
| Eligibility | Fixed downloaded universe; at least 252 usable daily observations and required lookbacks; eligibility diagnostics retained by date. |
| Evaluation | Chronological dates only. No random K-fold. Training labels must mature before the next validation/test signal date. |
| Models | Zero prediction → univariate sort → Ridge → one boosting model. Same dates, features and execution assumptions. |
| Portfolio | Rebalance every five trading sessions; top/bottom quintiles equal weight; +0.5 long / -0.5 short initial target weights. |
| Costs | Report gross and 0/5/10/20 bps one-way cost scenarios. Borrow cost is sensitivity analysis, not observed data. |

## Repository structure

```text
.
├── configs/                  # Fixed experiment parameters
├── data/                     # Documentation only; raw data is gitignored
├── docs/                     # Data contracts and implementation notes
├── notebooks/                # Exploration only; not the source of truth
├── reports/                  # Generated figures and research memo
├── src/us_equity_cross_sectional/
│   ├── data/                 # yfinance / future CRSP adapters
│   ├── features/             # Feature construction and labels
│   ├── models/               # Baselines, Ridge, boosting
│   ├── validation/           # Date-based splits and metrics
│   └── portfolio/            # Ledger, turnover and cost scenarios
└── tests/                    # Unit tests for timing and accounting invariants
```

## Implementation status

- [x] Research scope, data boundary, directory structure, and implementation plan
- [ ] Freeze a public prototype universe and implement download manifest
- [ ] Audit daily bars and feature/label timing with hand-calculated examples
- [ ] Build chronological baselines and prediction metrics
- [ ] Build portfolio ledger, cost stress tests, and risk diagnostics
- [ ] Run locked final test and write research memo

Read [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) before implementing. It specifies milestones, acceptance tests, and what may and may not be claimed from the free prototype.

## Local setup target

Python 3.11+ on macOS. Use a local virtual environment; raw data and cache files remain untracked.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## License and data usage

Code will use the MIT License. Data licenses are separate: do not commit raw Yahoo, WRDS/CRSP, or other vendor data. Cite the exact data adapter, extraction date, ticker-universe snapshot, and terms used in any report.
