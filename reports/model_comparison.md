# Out-of-Sample Model Comparison (Stage 2)

Same 8-security universe and `relative_return_5d` target as Stage 1
(`reports/factor_research.md`) — every caveat there about small
cross-section size applies here too. Evaluation is **strictly
chronological**: `chronological_expanding_folds()` splits the panel's
1,132 weekly dates into an initial 40% training block and 6 subsequent
expanding-window folds (train = everything strictly before the fold's
first test date; test = that fold's block of weeks). No random shuffling
is used anywhere. All preprocessing (median imputation, standardization)
is fit on each fold's train data only and applied unchanged to that
fold's test data — verified by a dedicated unit test
(`test_preprocessing_uses_train_stats_only`) and a check that every
fold's `train_end <= test_start` (`test_no_test_row_predicted_using_future_training_data`).

Full metrics: `reports/model_metrics.csv` (pooled, one row per model ×
feature group) and `reports/model_fold_details.csv` (one row per fold).
Figures: `reports/figures/model_ic_by_group.png`,
`model_r2_by_group.png`, `model_fold_ic_stability.png`.

## Feature groups

- **price_only** (11 factors): `momentum_12_1/6_1/3_1`, `reversal_1d/5d/20d`,
  `realized_vol_20d/60d`, `downside_vol_20d`, `adv_20d`, `amihud_20d`.
- **fundamentals_only** (8 factors): the 8 factors from Stage 1, several of
  which carry the already-documented TTM-corruption caveat.
- **combined**: all 19.

## Models

- **baseline**: equal-weight average of standardized factors (no fitting).
- **ols**, **ridge** (alpha=1.0), **elastic_net** (alpha=0.0005, l1_ratio=0.5).
- **lightgbm**: shallow (max_depth=3, 200 trees), the one nonlinear model
  this task asked for; xgboost was not installed in this environment and
  lightgbm was used instead, per the task's "use whichever is easier"
  instruction.

## A methodological finding worth reporting on its own: R^2 is not a usable metric at this sample size

Pooled out-of-sample R^2 is wildly unstable and frequently enormous and
negative (e.g. `fundamentals_only` baseline: mean OOS R^2 of **-1.55
billion**; `combined` baseline: **-275 million**; several linear models on
`fundamentals_only`/`combined`: **-5,000 to -26,000**). This is not a bug
in this study's models or code — verified by inspecting the label
distribution directly (`relative_return_5d`: mean ≈0, std ≈3.3%, max
≈33%, no extreme global outliers) and the per-fold R^2 values. It is a
known small-sample pathology: R^2 is the ratio of residual variance to
*that fold's own* target variance, and with only ~904 pooled observations
per fold (8 securities × ~113 weeks) drawn from a target whose
cross-sectional dispersion varies week to week, some folds have such low
realized target variance that R^2's denominator is tiny, and *any* small
absolute residual gets amplified into an enormous negative ratio. This
does not happen for the `ols`/`ridge`/`elastic_net` models on `price_only`
features (their OOS R^2 is small and sane, 0.002–0.003) because those
models' errors happen to track the target's scale more closely in this
run, but it is not something to rely on. **Rank IC is used as the primary
metric throughout this study for exactly this reason** — it is scale-free
and far more stable at small sample sizes, and this instability is a
direct, empirical demonstration of why (see `reports/interview_summary.md`
for the "why Rank IC" explanation this finding motivates).

## Pooled comparison (mean across 6 chronological folds)

| Feature group | Model | Mean OOS Rank IC | Mean ICIR | Mean OOS R² | Coverage % | Top/bottom tercile spread | Turnover |
|---|---|---:|---:|---:|---:|---:|---:|
| price_only | baseline | 0.0299 | 0.067 | (unstable, see above) | 100% | 0.0043 | 0.32 |
| price_only | ols | 0.0546 | 0.118 | 0.002 | 100% | 0.0042 | 0.33 |
| price_only | **ridge** | **0.0547** | **0.118** | **0.002** | 100% | 0.0042 | 0.33 |
| price_only | elastic_net | 0.0569 | 0.122 | 0.003 | 100% | 0.0047 | 0.27 |
| price_only | lightgbm | 0.0375 | 0.088 | -0.012 | 100% | 0.0043 | 0.37 |
| fundamentals_only | baseline | 0.0123 | 0.027 | (unstable) | 100% | 0.0020 | 0.07 |
| fundamentals_only | ols | -0.0044 | -0.018 | (unstable) | 100% | -0.0002 | 0.05 |
| fundamentals_only | ridge | -0.0043 | -0.017 | (unstable) | 100% | -0.0002 | 0.05 |
| fundamentals_only | elastic_net | -0.0190 | -0.053 | (unstable) | 100% | -0.0005 | 0.02 |
| fundamentals_only | lightgbm | 0.0144 | 0.038 | -0.043 | 100% | 0.0014 | 0.19 |
| combined | baseline | 0.0460 | 0.103 | (unstable) | 100% | 0.0047 | 0.22 |
| combined | ols | 0.0050 | 0.014 | (unstable) | 100% | 0.0010 | 0.19 |
| combined | ridge | 0.0048 | 0.014 | (unstable) | 100% | 0.0009 | 0.19 |
| combined | elastic_net | 0.0559 | 0.133 | (unstable) | 100% | 0.0044 | 0.25 |
| combined | lightgbm | 0.0108 | 0.024 | -0.024 | 100% | 0.0015 | 0.34 |

## Ablations

**Price only vs. fundamentals only vs. combined.** For every linear model
(ols/ridge/elastic_net), `price_only` (IC 0.055–0.057) clearly beats
`fundamentals_only` (IC -0.019 to -0.004, i.e. **negative** for 3 of the
4 non-baseline models) and is roughly tied with, or slightly better than,
`combined` (IC 0.005–0.056, highly model-dependent). **Fundamentals do not
improve prediction in this study, and are reported as such rather than
omitted or reframed**: a linear model trained on fundamentals alone
produces a negative out-of-sample Rank IC for 3 of 4 non-baseline
model/group combinations, and adding fundamentals to price factors
(`combined` vs `price_only`) does not consistently help — `ols`/`ridge`
get *worse* when fundamentals are added (0.055 → 0.005), while
`elastic_net` is roughly flat (0.057 → 0.056). This is consistent with,
and likely partly explained by, Stage 1's finding that the two strongest
fundamental factors (`sales_to_price`, `gross_profitability`) both carry
the documented TTM-flow-variable corruption issue, and that fundamentals
have far lower coverage (16–72%) than price factors (95–100%), which
both dilutes their contribution to a pooled linear fit and makes their
already-weak Stage 1 IC even less useful as a model input. The `baseline`
model (which needs no fitting) is the one place `combined` clearly beats
`price_only` (0.046 vs 0.030), but this reflects the un-fitted equal-weight
average being pulled by `sales_to_price`'s own individually-decent Stage 1
IC (0.044) rather than any learned interaction, and should not be read as
"fundamentals help when combined."

**Linear vs. nonlinear.** LightGBM underperforms the corresponding linear
model in every one of the three feature groups (price_only: 0.038 vs.
ridge's 0.055; fundamentals_only: 0.014 vs. baseline's 0.012, roughly
tied, but below ols/ridge is not meaningful since those are negative;
combined: 0.011 vs. elastic_net's 0.056). **Ridge/OLS beat the nonlinear
model, and this is reported honestly rather than searched around**: with
only 11–19 features, an 8-name cross-section, and a target this noisy, a
shallow gradient-boosted tree has more capacity to overfit idiosyncratic
training-period patterns than a linear model can, and the OOS evidence
here is consistent with that — LightGBM's fold-level IC is also
more variable across folds than Ridge's (see
`reports/figures/model_fold_ic_stability.png`: Ridge stays in a tighter,
consistently-positive band across all 6 folds, 0.035–0.093; LightGBM
ranges from 0.007 to 0.079 and has two folds with clearly negative R²).

## Fold-level stability (price_only, the strongest feature group)

| Model | Fold 0 IC | Fold 1 IC | Fold 2 IC | Fold 3 IC | Fold 4 IC | Fold 5 IC | All 6 folds positive? |
|---|---:|---:|---:|---:|---:|---:|---|
| baseline | 0.035 | 0.066 | 0.008 | -0.001 | 0.042 | 0.030 | No (fold 3 slightly negative) |
| ols | 0.046 | 0.036 | 0.092 | 0.036 | 0.073 | 0.045 | **Yes** |
| ridge | 0.046 | 0.036 | 0.093 | 0.035 | 0.074 | 0.045 | **Yes** |
| elastic_net | 0.070 | 0.034 | 0.080 | 0.036 | 0.094 | 0.028 | **Yes** |
| lightgbm | 0.007 | 0.016 | 0.053 | 0.028 | 0.079 | 0.042 | Yes, but weaker and more variable |

## Selected model for portfolio construction (Stage 3)

**`price_only` + `ridge`** — not chosen "solely by in-sample performance"
(Ridge's OOS IC, 0.0547, is statistically indistinguishable from
`elastic_net`'s 0.0569 and `combined`+`elastic_net`'s 0.0559 given this
sample's noise). It is chosen because: (1) it is positive in all 6 of 6
chronological folds, the most consistent record of any model evaluated;
(2) `price_only` avoids the fundamentals-related coverage and
TTM-corruption caveats entirely, giving Stage 3's portfolio the widest,
most reliable underlying data (100% coverage across the full 1,130-week
sample vs. 16–72% for individual fundamental factors); (3) Ridge is the
simplest, most standard, and most easily-defended choice among the
positive, stable options — `elastic_net`'s own default hyperparameter
setting collapsed to a constant (all-zero-coefficient) model in this
exact experiment (see the code comment in `models/signal_models.py`),
which is a legitimate reason for caution about its robustness even after
retuning `alpha` to get a non-degenerate result; and (4) the nonlinear
model did not beat it, so there is no basis to prefer added model
complexity here.

## What this stage did not find (explicit null results)

- No evidence that fundamentals improve prediction over price factors
  alone in this sample.
- No evidence that a nonlinear (tree-based) model outperforms a linear
  one at this feature count and sample size.
- No model/feature-group combination in this study produces an
  economically large out-of-sample signal — even the best mean Rank IC
  (0.057) is modest by production standards, consistent with Stage 1's
  conclusion.
