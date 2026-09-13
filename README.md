# US Equity Cross-Sectional Return Prediction and Robustness Research

**Status: In Progress — Milestones 1–3 complete; Milestone 4 (point-in-time fundamentals) underway. No prediction model, Rank IC, Sharpe ratio, or portfolio backtest has been run yet. Nothing in this document is a performance claim.**

An evidence-first quantitative research project testing whether a small, pre-specified set of price, liquidity, and (from Milestone 4 onward) fundamental features can rank U.S. equities by future relative returns — and whether any apparent signal survives chronological out-of-sample testing and realistic trading-cost assumptions.

## 1. Research Goal

The core question is:

> At the close of trading day $t$, can information available by then rank U.S. equities by their relative total return from close $t+1$ to close $t+6$?

This is deliberately framed as a **cross-sectional ranking problem**, not a point-forecasting problem. The objective is not to predict the exact future return of each stock, but to determine whether stocks can be ordered meaningfully enough to support a long-short portfolio.

The project is designed around three principles:

1. prevent look-ahead bias,
2. compare simple baselines before complex models,
3. report failure honestly if performance does not survive out-of-sample testing or costs.

## 2. Why This Problem Matters

A backtest can look attractive for the wrong reasons: survivorship bias, random train/test splits, overlapping labels, data leakage, unstable feature definitions, or ignoring turnover and costs.

The project therefore treats **research design** as part of the modeling problem. A useful signal should not only fit historical data; it should remain informative when evaluated using only information that would have been available at the time.

## 3. Data Plan

The executable prototype is designed for a frozen current universe of roughly 100–300 liquid U.S.-listed equities. Two data sources are used, each on its own point-in-time discipline:

- **Daily OHLCV** from [`yfinance`](https://github.com/ranaroussi/yfinance) (`auto_adjust=False`, `actions=True`), cached locally as raw CSV. Raw bars are cached during the provider audit; a Parquet layout is only introduced later if a measured need justifies it — the pipeline does not add that dependency speculatively.
- **SEC fundamentals** from EDGAR Company Facts and submissions, mapped to a small registry of standard US-GAAP/DEI concepts only (company-specific extension tags are never silently substituted). Every fact carries CIK, taxonomy, concept, unit, form, accession number, filed date, acceptance timestamp (when linkable), and an explicit `available_at` used for point-in-time selection. See [`docs/sec_concept_mapping.md`](docs/sec_concept_mapping.md) and [`docs/accounting_data_model.md`](docs/accounting_data_model.md).

For stock $i$ on date $t$, the raw daily data conceptually include

$$
\{O_{i,t},H_{i,t},L_{i,t},C_{i,t},V_{i,t}\},
$$

where $O,H,L,C$ are open, high, low, and close prices and $V$ is volume.

Dollar volume is defined as

$$
DV_{i,t}=C_{i,t}V_{i,t}.
$$

Raw downloaded bars and SEC caches are intentionally excluded from Git (`data/raw/`, `data/processed/`); the repository stores code, metadata, configuration, small reproducibility snapshots (e.g. the frozen universe CSV), and reproducible experiment logic rather than republishing vendor data.

### Data limitation

The free prototype uses a current-universe snapshot, so it is **not survivorship-bias-free**. A rigorous historical extension would replace the prototype adapter with CRSP/WRDS data while keeping the feature, validation, model, and portfolio interfaces unchanged.

### Why not use Open Source Asset Pricing as the main data source?

The [Open Source Asset Pricing](https://www.openassetpricing.com/data/) release is excellent for a separate factor-stability extension: it provides stock-level characteristics and daily/monthly **portfolio** returns, with most current data through December 2024. It is not a complete stock-level daily return database for this five-day individual-equity prediction task. Its ready-made signals are also signed according to original papers, so it should not be used to claim an independent discovery of alpha.

## 4. Prediction Target

The forward stock return is defined over a five-session holding interval beginning after the signal date:

$$
r_{i,t}^{(5)}
=
\frac{C_{i,t+6}}{C_{i,t+1}}-1.
$$

The target is a **relative return**, subtracting the equal-weight return of the eligible universe on the same signal date:

$$
y_{i,t}
=
r_{i,t}^{(5)}
-
\frac{1}{N_t}\sum_{j=1}^{N_t}r_{j,t}^{(5)}.
$$

This removes much of the market-wide move and focuses the task on cross-sectional differentiation. Milestone 3 additionally implements 1-day and 20-day horizons ($R_h(t)=P_{t+1+h}/P_{t+1}-1$) as diagnostic labels alongside the primary 5-day target.

## 5. Pre-Specified Price and Liquidity Features

The first version intentionally uses a small feature set rather than hundreds of candidate signals. All are implemented and tested in `src/us_equity_cross_sectional/features/`.

### 5.1 Twelve-Month Momentum Excluding the Most Recent Month

$$
\mathrm{MOM}_{i,t}
=
\frac{C_{i,t-21}}{C_{i,t-252}}-1.
$$

The most recent 21 trading sessions are skipped to separate medium-term momentum from very short-term reversal effects.

### 5.2 Five-Day Reversal

$$
\mathrm{REV5}_{i,t}
=-\left(\frac{C_{i,t}}{C_{i,t-5}}-1\right).
$$

### 5.3 Twenty-Day Realized Volatility

Using daily log returns

$$
r_{i,t}=\log\left(\frac{C_{i,t}}{C_{i,t-1}}\right),
$$

realized volatility is

$$
\sigma_{i,t}^{(20)}
=
\sqrt{252}\;\mathrm{SD}
\left(r_{i,t-19},\ldots,r_{i,t}\right).
$$

### 5.4 Short-vs-Long Dollar-Volume Ratio

Define

$$
\overline{DV}_{i,t}^{(5)}
=
\frac{1}{5}\sum_{k=0}^{4}DV_{i,t-k}
$$

and

$$
\overline{DV}_{i,t}^{(60)}
=
\frac{1}{60}\sum_{k=0}^{59}DV_{i,t-k}.
$$

The liquidity-activity ratio is

$$
\mathrm{DVRATIO}_{i,t}
=
\frac{\overline{DV}_{i,t}^{(5)}}{\overline{DV}_{i,t}^{(60)}}.
$$

### 5.5 Log Average Dollar Volume

$$
\mathrm{LOGADV}_{i,t}
=
\log\left(\overline{DV}_{i,t}^{(60)}\right).
$$

Liquidity inputs are normalized against Yahoo's split-adjustment basis so a corporate action does not create a spurious level shift; see [`reports/liquidity_split_consistency_audit.md`](reports/liquidity_split_consistency_audit.md).

## 6. Milestone 4: Point-in-Time Fundamentals (in progress)

Milestone 4 extends the panel with SEC accounting data under the same no-look-ahead discipline used for prices. Completed so far:

- **As-filed selection**: for any accounting fact, only the latest filing version with `available_at <= signal_time` is used; fiscal period end and instant date are never treated as availability.
- **Standalone-quarter and TTM reconstruction**: Q1 is standalone; Q2/Q3/FY are recovered from YTD figures (`Q_n = YTD_n − YTD_{n-1}`); trailing-twelve-month flow values require four valid, unit-compatible quarters or are left missing (`src/us_equity_cross_sectional/fundamentals/sec_facts.py`).
- **Point-in-time shares and market-cap eligibility gate**: `dei:EntityCommonStockSharesOutstanding` is selected as-of, reconciled to the same split basis as the cached price series, and gated on staleness, exact-acceptance-vs-fallback timing, and unresolved multiple-share-class issuers before a market cap is ever computed (`src/us_equity_cross_sectional/fundamentals/market_cap.py`; see [`docs/market_cap_methodology.md`](docs/market_cap_methodology.md) and [`reports/shares_outstanding_audit.md`](reports/shares_outstanding_audit.md)).
- **Weekly as-of fundamental panel**: joins the above into one `(research_date, security_id)` panel of raw flow/stock variables (revenue, net income, operating income, gross profit, capex TTM; assets, liabilities, equity, cash; shares and market cap), with full per-variable lineage (CIK, concept, taxonomy, accession, filed/acceptance timestamps) and per-variable staleness (`*_age_days`) — see [`src/us_equity_cross_sectional/fundamentals/asof_panel.py`](src/us_equity_cross_sectional/fundamentals/asof_panel.py) and [`reports/asof_fundamental_panel_audit.md`](reports/asof_fundamental_panel_audit.md).

**Not yet built:** book-to-market, earnings yield, sales-to-price, ROA, gross profitability, operating margin, leverage, or asset-growth ratios. No ratio, Rank IC, quantile analysis, model, or portfolio backtest uses fundamentals (or prices) yet.

## 7. Model Sequence (not yet run)

### 7.1 Zero-Prediction Baseline

$$
\hat y_{i,t}=0.
$$

### 7.2 Univariate Sorts

Each feature is tested independently by ranking stocks cross-sectionally. This answers whether the raw signal itself contains useful ordering information before combining features.

### 7.3 Ridge Regression

For standardized feature vector $x_{i,t}$,

$$
\hat\beta
=
\arg\min_{\beta}
\left[
\sum_{(i,t)\in\mathcal{T}}
(y_{i,t}-x_{i,t}^\top\beta)^2
+\lambda\|\beta\|_2^2
\right].
$$

Prediction is

$$
\hat y_{i,t}=x_{i,t}^\top\hat\beta.
$$

### 7.4 Gradient Boosting

$$
F_M(x)=\sum_{m=1}^{M}\eta f_m(x),
$$

where each $f_m$ is a weak learner and $\eta$ is the learning rate.

## 8. Chronological Validation (not yet run)

Random K-fold cross-validation is inappropriate because adjacent panel observations share temporal structure and forward labels overlap.

A training observation is usable only if

$$
\text{label\_end}_{i,t}
<
\text{first validation signal date}.
$$

## 9. Prediction Evaluation (not yet run)

### 9.1 Rank Information Coefficient

The primary cross-sectional prediction metric is Spearman rank correlation:

$$
IC_t
=
\rho_{\mathrm{Spearman}}
\left(\hat y_{i,t},y_{i,t}\right).
$$

Across evaluation dates,

$$
\overline{IC}
=
\frac{1}{T}\sum_{t=1}^{T}IC_t.
$$

### 9.2 Spread Monotonicity

If $Q_{1,t},\ldots,Q_{5,t}$ are score quintiles, desirable behavior is approximately

$$
\mathbb{E}[R_{Q_1}]
<\mathbb{E}[R_{Q_2}]
<\cdots<
\mathbb{E}[R_{Q_5}].
$$

## 10. Portfolio Construction (not yet run)

At each rebalance date, the top quintile is long and the bottom quintile is short.

$$
\sum_i w_{i,t}^{+}=0.5,
\qquad
\sum_i w_{i,t}^{-}=-0.5,
$$

so

$$
\sum_i w_{i,t}=0.
$$

The gross long-short return is

$$
R_t^{LS}=\sum_i w_{i,t}r_{i,t+1}.
$$

## 11. Turnover and Trading Costs (not yet run)

$$
\mathrm{Turnover}_t
=
\sum_i\left|w_{i,t}^{\mathrm{target}}-w_{i,t}^{\mathrm{pretrade}}\right|.
$$

With one-way cost rate $c$,

$$
\mathrm{Cost}_t=c\times\mathrm{Turnover}_t.
$$

Net return becomes

$$
R_t^{net}=R_t^{gross}-\mathrm{Cost}_t.
$$

The pre-registered sensitivity grid is 0, 5, 10, and 20 bps one-way cost.

## 12. Portfolio Evaluation Metrics (not yet run)

### Annualized Return

$$
R_{ann}
=\left(\prod_{t=1}^{T}(1+R_t)\right)^{252/T}-1.
$$

### Annualized Volatility

$$
\sigma_{ann}
=\sqrt{252}\;\mathrm{SD}(R_t).
$$

### Sharpe Ratio

$$
SR
=\frac{\mathbb{E}[R_t]}{\mathrm{SD}(R_t)}\sqrt{252}.
$$

### Maximum Drawdown

If cumulative wealth is

$$
W_t=\prod_{s\le t}(1+R_s),
$$

then

$$
DD_t=\frac{W_t}{\max_{u\le t}W_u}-1,
$$

and

$$
MDD=\min_t DD_t.
$$

## 13. Robustness Tests (planned)

The planned robustness analysis compares:

- expanding-history training
- rolling three-year training
- liquidity restrictions
- 0/5/10/20 bps cost assumptions
- year-by-year Rank IC and portfolio performance

## 14. Current Implementation Status

This repository is in the **research-design and data-infrastructure stage**. No prediction model, Rank IC, Sharpe ratio, or portfolio backtest has been run — this README intentionally does **not** report any such number.

- [x] Research question, timing convention, and pre-registered v1 specification (Milestone 1)
- [x] Frozen prototype universe, price-provider audit, and SEC fundamentals-provider audit (Milestone 2)
- [x] Point-in-time common-shares audit and market-cap split-basis methodology (Milestone 2)
- [x] Price-based factors and 1D/5D/20D forward labels, with hand-checked timing fixtures (Milestone 3)
- [x] Yahoo split-consistent liquidity normalization (Milestone 3)
- [x] SEC concept-mapping foundation and as-filed/point-in-time normalization (Milestone 4)
- [x] Standalone-quarter and TTM reconstruction primitives (Milestone 4)
- [x] Market-cap eligibility gate wired into a point-in-time panel (Milestone 4)
- [x] Weekly as-of fundamental panel: `available_at <= signal_time` join of flow/stock variables with lineage and staleness (Milestone 4)
- [ ] Book-to-market, earnings yield, sales-to-price, ROA, gross profitability, operating margin, leverage, asset-growth ratios (Milestone 4, remaining)
- [ ] Chronological validation splits and baseline/Ridge/boosting model training (Milestone 5)
- [ ] Rank IC, quantile spread, and coverage evaluation (Milestone 5)
- [ ] Portfolio simulation and cost stress tests (Milestone 6–7)
- [ ] Locked final report (Milestone 8)

## 15. Repository Structure

```text
.
├── configs/                        # Fixed experiment parameters (v1_free_prototype.yaml)
├── data/
│   ├── manifests/                  # Download/audit manifests (gitignored JSON, regenerable)
│   ├── metadata/                   # Small, versioned reproducibility snapshots (e.g. universe CSV)
│   ├── raw/                        # Gitignored: cached SEC/Yahoo payloads
│   └── processed/                  # Gitignored: built panels
├── docs/                           # Data contracts, methodology, and audit-trail notes
├── reports/                        # Generated audit reports (markdown, no figures committed)
├── scripts/                        # Build/audit entry points (one script per pipeline stage)
├── src/us_equity_cross_sectional/
│   ├── data/                       # Point-in-time and validation primitives shared across panels
│   ├── features/                   # Price/liquidity feature and label construction
│   └── fundamentals/               # SEC as-filed facts, TTM/standalone transforms, market cap, as-of panel
├── tests/                          # Unit tests for timing, accounting, and panel-key invariants
├── IMPLEMENTATION_PLAN.md
├── pyproject.toml
└── README.md
```

Read [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) for milestone acceptance criteria and research safeguards, and [`docs/leakage_and_bias.md`](docs/leakage_and_bias.md) for the binding time convention and bias register.

## 16. Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Runtime dependencies (`numpy`, `pandas`, `scikit-learn`, `yfinance`, `PyYAML`) and dev/test dependencies (`pytest`, `ruff`) are declared in `pyproject.toml`. Raw data and cache files remain untracked; run the scripts in `scripts/` to regenerate them locally.

```bash
python -m pytest tests/
```

## 17. Interview Summary

> I designed a cross-sectional equity research pipeline where the main challenge is not just choosing a model, but preventing timing leakage and testing whether ranking power survives realistic implementation assumptions. I pre-specify five price/liquidity features, compare zero and univariate baselines with Ridge and one boosting model, evaluate with date-level Rank IC and quintile spreads, and then convert scores into a dollar-neutral long-short portfolio with explicit turnover and transaction-cost accounting. I'm currently extending the panel with point-in-time SEC fundamentals — the same as-filed discipline as prices, with an explicit market-cap eligibility gate and full filing-level lineage — before any ratio, model, or backtest touches the data. The final test is intentionally locked until the pipeline is complete.

## 18. Limitations

- The free prototype is not survivorship-bias-free.
- `yfinance` is appropriate for pipeline prototyping, not institutional historical-universe research.
- SEC Company Facts do not expose XBRL dimensional context, so multiple-share-class issuers cannot be reliably split by class; such issuers are excluded from market-cap-dependent work until resolved (see [`docs/market_cap_methodology.md`](docs/market_cap_methodology.md)).
- Weighted-average basic/diluted shares are never substituted for the point-in-time common-shares fact.
- Financial-sector accounting comparability (e.g. bank balance-sheet structure) is treated as a separate, unresolved question, not defaulted into the standard mapping.
- Results should not be interpreted as investment advice.
- No final model or backtest result is claimed until the implementation and locked evaluation are complete.

## 19. License and Data Usage

Code uses the MIT License. Data licenses are separate. Raw Yahoo, SEC EDGAR, WRDS/CRSP, or other vendor data should not be committed to this repository.
