# Robustness Checks (Stage 5)

Practical robustness checks on the existing Stage 1-4 results, reusing
cached artifacts (research panel, `factor_metrics.csv`, Stage 2/3 model and
portfolio code) rather than rebuilding the pipeline. Full check outputs:
`reports/robustness_*.csv`. Figures: `reports/figures/robustness_factor_horizon.png`,
`reports/figures/robustness_yearly_stability.png`. See
`reports/failure_analysis.md` for the explicit "what did not generalize"
section.

Standing caveat, as in every prior stage: all of this is computed on an
8-security universe. A robustness check on 8 names is not a substitute for
a robustness check on a production-scale universe; it can only tell us
whether a given result is fragile *even within this small sample*, which is
itself informative.

## 1. Horizon robustness (1D / 5D / 20D)

**Factors** (from `reports/factor_metrics.csv`, reused directly, no rerun):
the five strongest 5D factors get *stronger*, not weaker, at 20D
(realized_vol_60d: 0.0538 -> 0.1029; adv_20d: 0.0473 -> 0.0938;
realized_vol_20d: 0.0417 -> 0.0869), and weaker at 1D (0.02-0.03 range) --
consistent with these being slower-moving, persistence-style signals
whose predictive content shows up more at longer horizons. `momentum_12_1`
is the exception: it weakens from 5D (0.0305) to 20D (0.0224), i.e. its
signal decays over the horizon we'd naively expect momentum to work best
at. `reversal_1d/5d/20d` and `amihud_20d` flip sign or stay negative across
all three horizons, another indicator these are not being cherry-picked
into a good-looking horizon.

**Model** (re-fit `ridge`/`price_only` chronologically on 1D, 5D, and 20D
labels -- `reports/robustness_model_horizon.csv`): mean OOS Rank IC rises
with horizon (1D: 0.017, 5D: 0.055, 20D: 0.104), matching the factor-level
pattern. This is a real, consistent finding, not a rerun-until-it-looks-good
result -- the model was fit once per horizon with the same procedure used
throughout.

## 2. Year-by-year stability of the strongest and weakest factors

`reports/robustness_yearly_factor_stability.csv` has full year-by-year mean
IC for the 5 strongest and 5 weakest-but-still-included factors (2005-2026,
~52 weeks/year). Key finding: **even the strongest factors are not stable
every year.** `realized_vol_60d` (the single strongest factor overall,
mean IC 0.0538) has a *negative* mean IC in 2008, 2013, 2018, and 2020-2021 —
years spanning both the financial crisis and a calmer period — alongside
strongly positive years like 2005 (0.21) and 2009 (0.087). This is reported
plainly: the factor's edge is real in aggregate but not present in every
year, which is exactly the kind of instability a robustness check is
supposed to surface, not hide.

## 3. Rebalance-frequency sensitivity

Subsampling the existing weekly OOS predictions to every second research
date (an approximate biweekly rebalance) rather than rebuilding the
pipeline at a different frequency: mean Rank IC actually rises slightly
(0.0547 weekly -> 0.0722 biweekly, `reports/robustness_rebalance_frequency.csv`).
This is a coarse proxy (it does not re-fit the model at biweekly cadence,
just subsamples existing weekly OOS predictions) and the sample shrinks to
339 dates, so this should be read only as "the signal does not obviously
degrade at lower rebalance frequency," not as a validated biweekly
strategy.

## 4. Feature group robustness (price-only vs. fundamentals-only vs. combined)

Already computed in Stage 2 (`reports/model_comparison.md`), reused here
rather than rerun: price-only factors are the only group with a
consistently positive linear-model signal (ridge/ols/elastic_net mean IC
0.055-0.057); fundamentals-only linear models are *negative* (ridge
-0.0043, ols -0.0044, elastic_net -0.019); combined does not improve on
price-only (best combined mean IC 0.0559 vs. price-only best 0.0569,
essentially the price-only signal being carried through, not enhanced by
fundamentals). This robustness check confirms the same conclusion drawn in
Stage 2, using the same evaluation, not a new one — included here for
completeness of the robustness section rather than as a new result.

## 5. Raw vs. standardized/imputed factors

Spearman Rank IC is invariant under any monotonic transform of a factor,
so standardization ((x-mean)/std) alone cannot change it. The one place
this *could* matter is median-imputation of missing values, which is not a
pure monotonic transform of the original column. Checked numerically for
the 5 strongest factors (`reports/robustness_raw_vs_standardized.csv`):
raw and standardized+imputed mean IC are identical to 4 decimal places in
every case tested. This is expected given how sparse missingness is for
these particular (price-derived, near-100%-coverage) factors, and is
reported as a sanity check rather than a novel finding.

## 6. Model stability over time (fold-level)

`reports/robustness_model_fold_stability.csv` (same as reported in Stage 2,
reproduced here for the robustness section): all 6 expanding-window folds
of ridge/price_only/5D have positive mean IC (range 0.035-0.093), with no
fold going negative. This is the strongest stability result in the study:
unlike individual factors (which do have negative years), the ridge
combination model's OOS IC has not gone negative in any tested fold across
2013-2026.

## 7. Cost sensitivity

Already covered in full in Stage 4 (`reports/transaction_costs.md`); not
repeated here beyond the summary that net Sharpe declines substantially
(0.61/0.82 gross -> 0.05/0.18 at 50bps) but does not go negative on the
tested 0-50bps grid.

## Summary judgment

The clearest, most robust finding in this study is the price-factor-only
ridge model's fold-level stability (point 6): positive in 6/6 out-of-sample
folds over 13 years. The weakest, most fragile findings are individual
factor ICs at the yearly level (point 2) and anything involving
fundamentals (point 4) -- both are reported honestly as such rather than
smoothed into a single aggregate number.
