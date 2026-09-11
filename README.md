# US Equity Cross-Sectional Return Prediction and Robustness Research

An evidence-first quantitative research project testing whether a small, pre-specified set of price and liquidity features can rank U.S. equities by future relative returns—and whether any apparent signal survives chronological out-of-sample testing and realistic trading-cost assumptions.

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

The executable prototype is designed for a frozen current universe of roughly 100–300 liquid U.S.-listed equities and daily OHLCV data retrieved with `yfinance`.

For stock $i$ on date $t$, the raw daily data conceptually include

$$
\{O_{i,t},H_{i,t},L_{i,t},C_{i,t},V_{i,t}\},
$$

where $O,H,L,C$ are open, high, low, and close prices and $V$ is volume.

Dollar volume is defined as

$$
DV_{i,t}=C_{i,t}V_{i,t}.
$$

Raw downloaded bars are intentionally excluded from Git; the repository is meant to store code, metadata, configuration, and reproducible experiment logic rather than republish vendor data.

### Data limitation

The free prototype uses a current-universe snapshot, so it is **not survivorship-bias-free**. A rigorous historical extension would replace the prototype adapter with CRSP / WRDS data while keeping the feature, validation, model, and portfolio interfaces unchanged.

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

This removes much of the market-wide move and focuses the task on cross-sectional differentiation.

## 5. Pre-Specified Features

The first version intentionally uses a small feature set rather than hundreds of candidate signals.

### 5.1 Twelve-Month Momentum Excluding the Most Recent Month

A standard momentum-style feature is

$$
\text{MOM}_{i,t}
=
\frac{C_{i,t-21}}{C_{i,t-252}}-1.
$$

The most recent 21 trading sessions are skipped to separate medium-term momentum from very short-term reversal effects.

### 5.2 Five-Day Reversal

Short-horizon reversal is represented by

$$
\text{REV5}_{i,t}
=-\left(\frac{C_{i,t}}{C_{i,t-5}}-1\right).
$$

A stock that recently rose sharply therefore receives a more negative reversal signal.

### 5.3 Twenty-Day Realized Volatility

Using daily log returns

$$
r_{i,t}=\log\left(\frac{C_{i,t}}{C_{i,t-1}}\right),
$$

realized volatility is

$$
\sigma_{i,t}^{(20)}
=
\sqrt{252}\;\operatorname{StdDev}
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
\text{DVRATIO}_{i,t}
=
\frac{\overline{DV}_{i,t}^{(5)}}{\overline{DV}_{i,t}^{(60)}}.
$$

### 5.5 Log Average Dollar Volume

$$
\text{LOGADV}_{i,t}
=
\log\left(\overline{DV}_{i,t}^{(60)}\right).
$$

The log transform reduces scale skew across securities with very different liquidity levels.

## 6. Model Sequence

The project follows a simple-to-complex model hierarchy so that incremental value is visible.

### 6.1 Zero-Prediction Baseline

$$
\hat y_{i,t}=0.
$$

Any model should improve meaningfully over this trivial benchmark.

### 6.2 Univariate Sorts

Each feature is tested independently by ranking stocks cross-sectionally. This answers whether the raw signal itself contains useful ordering information before combining features.

### 6.3 Ridge Regression

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

Ridge is useful because it is interpretable, stable under correlated predictors, and provides a strong regularized linear baseline.

Prediction is

$$
\hat y_{i,t}=x_{i,t}^\top\hat\beta.
$$

### 6.4 Gradient Boosting

One nonlinear boosting model is planned as the complexity benchmark. In additive form,

$$
F_M(x)=\sum_{m=1}^{M}\eta f_m(x),
$$

where each $f_m$ is a weak learner and $\eta$ is the learning rate.

The point of this model is not to maximize complexity; it is to test whether nonlinear interactions add stable out-of-sample ranking power beyond Ridge.

## 7. Chronological Validation

Random K-fold cross-validation is inappropriate because adjacent panel observations share temporal structure and forward labels overlap.

The project uses date-based folds and requires training labels to mature before the next validation/test signal date.

Conceptually:

```text
feature date t
    |
    | information available
    v
execution at close t+1
    |
    v
forward return interval
    |
    v
label ends at t+6
```

A training observation is usable only if

$$
\text{label\_end}_{i,t}
<
\text{first validation signal date}.
$$

This prevents forward-return information from leaking across folds.

## 8. Prediction Evaluation

### 8.1 Rank Information Coefficient

The primary cross-sectional prediction metric is Spearman rank correlation between model score and future return:

$$
IC_t
=
\operatorname{Corr}_{\text{Spearman}}
\left(\hat y_{i,t},y_{i,t}\right).
$$

Across evaluation dates,

$$
\overline{IC}
=
\frac{1}{T}\sum_{t=1}^{T}IC_t.
$$

A stable positive IC means higher-scored stocks tend to realize higher future relative returns.

### 8.2 Spread Monotonicity

Stocks are sorted into score quantiles. A useful model should ideally show increasing average future returns from low-score to high-score portfolios.

If $Q_{1,t},\ldots,Q_{5,t}$ are quintiles, desirable behavior is approximately

$$
\mathbb{E}[R_{Q_1}]
<\mathbb{E}[R_{Q_2}]
<\cdots<
\mathbb{E}[R_{Q_5}].
$$

## 9. Portfolio Construction

At each rebalance date, the top quintile is long and the bottom quintile is short.

Initial target exposure is

$$
\sum_i w_{i,t}^{+}=0.5,
\qquad
\sum_i w_{i,t}^{-}=-0.5,
$$

so the portfolio is approximately dollar neutral:

$$
\sum_i w_{i,t}=0.
$$

The gross long-short return is

$$
R_t^{LS}
=
\sum_i w_{i,t}r_{i,t+1}.
$$

## 10. Turnover and Trading Costs

Turnover at rebalance $t$ is measured from pre-trade weights:

$$
\text{Turnover}_t
=
\sum_i
\left|w_{i,t}^{\text{target}}-w_{i,t}^{\text{pretrade}}\right|.
$$

With one-way cost rate $c$,

$$
\text{Cost}_t
=c\times\text{Turnover}_t.
$$

Net return becomes

$$
R_t^{net}=R_t^{gross}-\text{Cost}_t.
$$

The pre-registered sensitivity grid is 0, 5, 10, and 20 bps one-way cost.

## 11. Portfolio Evaluation Metrics

### Annualized Return

For periodic returns $R_t$,

$$
R_{ann}
=\left(\prod_{t=1}^{T}(1+R_t)\right)^{252/T}-1.
$$

### Annualized Volatility

$$
\sigma_{ann}
=\sqrt{252}\;\operatorname{StdDev}(R_t).
$$

### Sharpe Ratio

Ignoring the risk-free rate in the first prototype,

$$
SR
=\frac{\mathbb{E}[R_t]}{\operatorname{StdDev}(R_t)}\sqrt{252}.
$$

### Maximum Drawdown

If cumulative wealth is

$$
W_t=\prod_{s\le t}(1+R_s),
$$

then drawdown is

$$
DD_t=\frac{W_t}{\max_{u\le t}W_u}-1,
$$

and

$$
MDD=\min_t DD_t.
$$

## 12. Robustness Tests

The planned robustness analysis compares:

- expanding-history training
- rolling three-year training
- liquidity restrictions
- 0/5/10/20 bps cost assumptions
- year-by-year Rank IC and portfolio performance

The purpose is to distinguish a genuinely persistent signal from one dependent on a single favorable period or assumption.

## 13. Current Results / Implementation Status

This repository is currently in the **research-design and implementation stage**. The public codebase already contains the experiment specification, package structure, configuration, tests directory, and detailed implementation plan, but the final predictive and portfolio pipeline has not yet been completed.

Therefore, this README intentionally does **not** report Sharpe ratios, Rank IC values, or backtest returns that have not been generated by the repository.

Current status:

- [x] research question and timing convention
- [x] data boundary and free prototype design
- [x] feature definitions
- [x] chronological-validation specification
- [x] model sequence and portfolio rules
- [x] implementation plan
- [ ] frozen prototype universe
- [ ] data ingestion and audit
- [ ] feature/label implementation
- [ ] model training and out-of-sample evaluation
- [ ] portfolio simulation and cost stress tests
- [ ] locked final report

## 14. Repository Structure

```text
.
├── configs/                  # Fixed experiment parameters
├── data/                     # Documentation / metadata; raw bars excluded
├── docs/                     # Data contracts and research notes
├── src/us_equity_cross_sectional/
├── tests/                    # Timing and accounting tests
├── IMPLEMENTATION_PLAN.md
├── pyproject.toml
└── README.md
```

Read [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) for milestone acceptance criteria and research safeguards.

## 15. Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## 16. Interview Summary

A concise way to explain this project is:

> I designed a cross-sectional equity research pipeline where the main challenge is not just choosing a model, but preventing timing leakage and testing whether ranking power survives realistic implementation assumptions. I pre-specify five price/liquidity features, compare zero and univariate baselines with Ridge and one boosting model, evaluate with date-level Rank IC and quintile spreads, and then convert scores into a dollar-neutral long-short portfolio with explicit turnover and transaction-cost accounting. The final test is intentionally locked until the pipeline is complete.

## 17. Limitations

- The free prototype is not survivorship-bias-free.
- `yfinance` is appropriate for pipeline prototyping, not institutional historical-universe research.
- Results should not be interpreted as investment advice.
- No final model or backtest result is claimed until the implementation and locked evaluation are complete.

## 18. License and Data Usage

Code uses the MIT License. Data licenses are separate. Raw Yahoo, WRDS/CRSP, or other vendor data should not be committed to this repository.