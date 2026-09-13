# What Failed or Did Not Generalize (Stage 5)

This project's operating rules require failed, null, and negative findings
to be kept and reported explicitly, not hidden or discarded. This document
collects them in one place; each is cross-referenced to where it was first
found.

## 1. Fundamental factors add no incremental predictive signal over price factors

Stage 2 (`reports/model_comparison.md`) and the Stage 5 robustness check
(section 4 above) agree: linear models trained on fundamentals alone have
*negative* mean OOS Rank IC (ridge -0.0043, ols -0.0044, elastic_net
-0.019), and combining fundamentals with price factors does not improve on
price factors alone (combined best mean IC 0.0559 vs. price-only best
0.0569 -- fundamentals do not add, and arguably very slightly subtract).
This is a real, reported null finding, not a bug: the fundamental-factor
data itself already carries known, documented coverage/quality limitations
(the duration-variant TTM collision and single-candidate concept-selection
gaps found during the pre-mega-task validation work), so this finding
should be read as "fundamentals as currently computed do not help," not as
"fundamentals could never help with better data."

## 2. The nonlinear model (LightGBM) underperforms simple linear models

In every one of the three feature groups tested (price-only,
fundamentals-only, combined), LightGBM's mean OOS Rank IC is lower than at
least one linear alternative (Stage 2: price-only LightGBM 0.0375 vs. ridge
0.0547; combined LightGBM 0.0108 vs. elastic_net 0.0559). This is reported
honestly per the task's explicit instruction ("if Ridge beats the nonlinear
model, report it honestly") rather than tuned or explained away. The most
likely explanation, stated as a hypothesis and not fact, is that an
8-security, ~900-observations-per-fold sample is too small for a tree
ensemble to find nonlinear structure that generalizes, while a linear
model's much lower variance is an advantage at this scale.

## 3. Individual factors are not stable year-over-year, even the strongest ones

Stage 5 robustness section 2: `realized_vol_60d`, the single strongest
factor by mean IC, has negative mean IC in at least 4 of the 17 years
in-sample (2008, 2013, 2018, 2020 or 2021 depending on exact grouping).
No factor tested is positive in every year. This means the mean-IC
ranking in `reports/factor_research.md` should be read as an
average tendency across a long window, not a guarantee for any given
year or subperiod.

## 4. Pooled OOS R^2 is numerically unusable at this sample size

First found in Stage 2: pooled OOS R^2 for several model/feature-group
combinations is an enormous, uninterpretable negative number (e.g.
approximately -1.55 billion for fundamentals_only + baseline). Root cause:
near-zero target variance in some folds makes R^2's denominator vanish,
amplifying any residual into an extreme ratio -- this is a known pathology
of R^2 on small, low-variance samples, not a code defect (verified by
checking the label distribution and per-fold sample sizes directly). This
motivated using Rank IC, not R^2, as the primary evaluation metric
throughout the study -- documented here again since it is a genuine
"what failed" finding about methodology, not just a technical footnote.

## 5. ElasticNet collapsed to a degenerate constant model at its default regularization strength

First found in Stage 2: at `alpha=0.01`, ElasticNet's coefficients
collapsed to all-zero, producing a constant prediction (turnover=0, IC
undefined/NaN) in every feature group. `alpha` was lowered to 0.0005 purely
to obtain a non-degenerate model to compare against, not to chase a target
score -- the original degenerate result at the default strength is reported
here as a genuine finding about this model/sample-size combination, not
silently fixed and forgotten.

## 6. High turnover materially erodes (but does not eliminate) returns at higher assumed costs

Stage 4: annualized net return falls by roughly 78-92% going from 0 to 50
bps assumed cost, driven by the ~30%/week turnover this small a
long/short book naturally has (a single name changing legs is a 25-50%
turnover event with only 2 names per leg). This is reported as a
structural, not incidental, limitation of evaluating a long-short
strategy on an 8-name universe.

## 7. Coverage and universe-scope limitations remain unresolved (carried over, not silently dropped)

Documented before this mega-task began and still true: the prototype
8-security universe is not survivorship-bias-free, and the originally
larger (~100-name) Milestone-3 universe's raw price data was not available
in this environment to rebuild (see `scripts/build_research_panel.py`
docstring). Two specific fundamental-data defects found during the
pre-mega-task validation phase (a duration-variant TTM collision bug and a
single-candidate concept-selection gap causing e.g. JNJ's
`stockholders_equity` to be 81% missing) were documented, not fixed, since
fixing them was out of scope for this V1 completion pass and neither
blocks the overall research conclusion (fundamentals underperforming price
factors holds up whether or not those two defects are eventually fixed --
fixing them could only make fundamentals look *better*, and they still lost
to price-only factors even with the defects present, though the study can't
rule out that a genuinely clean fundamentals panel could reverse the
underperformance finding).

## What this means for the study's headline claim

The research question asked whether ML can improve on traditional factor
combinations out-of-sample after costs. The honest answer this project's
real results support is: **a simple linear combination (ridge) of a small
set of price/technical factors shows a modest, fold-stable, cost-surviving
(within the tested 0-50bps range) positive signal on this prototype
universe; adding fundamentals or a nonlinear model did not improve on that,
and the paper trail above documents every place that was checked and found
not to help, rather than presenting only the positive result.**
