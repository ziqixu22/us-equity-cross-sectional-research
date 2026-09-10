# Implementation Plan

## Outcome

Produce one reproducible, interview-ready research package—not a trading product. The finished project must make it possible to answer: what was known at each decision point, what was tested, what failed, and how costs change the conclusion.

## Data decision

### Primary executable path: frozen current-universe prototype

1. Download a **current** U.S.-listed liquid-equity universe from a documented public source and save the exact snapshot as `data/metadata/universe_YYYY-MM-DD.csv`.
2. Restrict to a manageable first run (about 100–300 liquid common stocks) and record the selection rule before inspecting returns.
3. Use `yfinance` only for daily OHLCV retrieval; save a manifest containing requested tickers, successful tickers, retrieval timestamp, date range, package version, and failed requests.
4. Store raw downloaded bars outside Git. Commit only the universe snapshot, schema, checks, and data-quality summary.

**Claim boundary:** this validates the end-to-end research system. It cannot establish a survivorship-bias-free historical U.S. cross section, historical index membership, or deployable trading capacity.

### Future rigorous path: CRSP/WRDS adapter

When university access is confirmed, add an adapter that supplies permanent security identifiers, historical security attributes and returns consistent with the selected CRSP version. Do not mix older tutorials' delisting-return procedure with current CIZ/v2 returns without checking the data dictionary.

### Separate optional free extension: Open Source Asset Pricing

Use its portfolio returns for a **monthly factor stability** appendix only. Preselect a small number of price/trading signals, use release-vintage data, and describe the authors' signal conventions. Keep it separate from the individual-stock daily pipeline.

## Milestones

| Milestone | Work | Acceptance criteria |
|---|---|---|
| M0 — Contract | Commit `research_spec.md`, config defaults, field dictionary and experiment log template. | A reader can state the question, timing, features, baseline and failure criteria without reading code. |
| M1 — Ingestion | Implement `YahooDailyBarsAdapter`; snapshot universe; write Parquet plus a manifest. | Unique `symbol × date`; request failures captured; no raw data in Git. |
| M2 — Audit | Check calendar, missingness, adjusted-price policy, splits/extreme returns, and dollar-volume unit. Hand-calculate 5 examples. | Tests fail on duplicate bars, future dates, non-monotone dates and bad return units. |
| M3 — Features/labels | Construct five fixed features and five-day relative-return label. | For any observation, `asof_date < execution_date ≤ label_end`; a small fixture matches hand calculations. |
| M4 — Validation | Implement date-level expanding/rolling splits with label maturation purge. | Tests show no training label overlaps a validation/test signal date; no random split path is exposed. |
| M5 — Prediction | Fit zero baseline, univariate sort, Ridge and one boosting model. | A table reports date-level Rank IC, spread monotonicity, coverage and results by year for every model. |
| M6 — Portfolio | Implement non-overlapping five-session rebalancing, drifted pre-trade positions, turnover, and cost scenarios. | Zero return/zero fee leaves NAV unchanged; costs lower NAV by exactly computed amount; initial/final trades are charged. |
| M7 — Robustness | Compare expanding history vs rolling three-year history; run liquidity and 0/5/10/20 bps sensitivity tables. | Only the pre-specified single extension changes; all other configuration hashes agree. |
| M8 — Locked report | Run untouched final period once rules are locked; write research memo and interview narrative. | Results distinguish gross/net performance, limitations, years of failure, and next highest-value experiment. |

## Chronological split

Use a date-level split, then map dates back to panel rows.

```text
signal date t ── close t+1 execution ── return intervals t+2 … t+6 ── label end
      │                     │                                      │
      └──────── feature info is available by t ─────────────────────┘
```

Train only on observations whose `label_end < first_signal_date` in the subsequent validation or test fold. A simple `TimeSeriesSplit(gap=5)` over panel rows is not sufficient because five rows are not five market sessions in a multi-stock panel.

## Suggested module interfaces

```python
DailyBarsAdapter.fetch(universe: pd.DataFrame, start: str, end: str) -> pd.DataFrame
validate_bars(bars: pd.DataFrame) -> AuditReport
build_features_and_labels(bars: pd.DataFrame, spec: FeatureSpec) -> pd.DataFrame
date_folds(panel: pd.DataFrame, spec: SplitSpec) -> Iterable[Fold]
fit_predict(train: pd.DataFrame, predict: pd.DataFrame, model_spec: ModelSpec) -> pd.Series
simulate_portfolio(predictions: pd.DataFrame, bars: pd.DataFrame, spec: PortfolioSpec) -> Ledger
```

Every public function should have a fixture-based test. Exploratory notebooks may call these interfaces but may not replace them.

## MacBook execution budget

Start with 100–300 tickers and 2010 onward. Persist daily bars as partitioned Parquet and features as Parquet. Use `pandas`, `numpy`, `scikit-learn`, `pyarrow`, and `yfinance`; do not introduce distributed processing, GPUs, Docker, Qlib, or an optimizer in v1. Add one model at a time.

## Research log template

For every run, record: Git commit SHA, config hash, universe snapshot, data retrieval timestamp, model, train/validation dates, feature set, execution assumption, cost scenario, metrics, result, and decision. Failed experiments stay in the log.

## Interview deliverables

1. A 90-second explanation: question → timing risk → design → result/limitation.
2. A five-minute walkthrough: data audit, chronological validation, model comparison, cost ledger, one failure case.
3. A four-to-six-page research memo with reproducible table/figure generation.
4. A README that never overstates the free prototype's data quality.
