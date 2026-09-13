# Factor Research (Stage 1)

Universe: 8 securities (AAPL, MSFT, KO, JNJ, XOM, JPM, WMT, NVDA) — the same
issuer set the SEC fundamentals pipeline covers. This is a **small,
prototype cross-section**, not a production universe; every statistic
below is computed from at most 8 names per date, and this caveat applies
to every number in this report. Primary prediction target:
`relative_return_5d` (5-trading-day cross-sectional relative return, i.e.
each security's forward 5-day return minus the equal-weight mean across
the 8 names that date). 1D and 20D horizons are also evaluated. No sign
was flipped based on realized performance; factor formulas and signs are
exactly as defined in `features/momentum.py`, `reversal.py`,
`volatility.py`, `liquidity.py`, and `features/fundamental.py`.

Full metrics: `reports/factor_metrics.csv`. Figures: `reports/figures/`.

## Why the sample-size caveat matters here specifically

With only 8 names, a per-date Spearman Rank IC is computed from as few as
3 pairs (this module's `min_obs` floor) and never more than 8. A "quintile"
sort of 8 names puts roughly 1-2 names per bucket — the quintile-spread
figures below and in `reports/figures/quintile_monotonicity_top_factor.png`
should be read as illustrative, not as a reliable quintile-portfolio
estimate. The mean-IC t-statistics reported below use the naive
`mean_ic / (std_ic / sqrt(n_dates))` formula, which assumes independent
observations across dates; because `relative_return_5d` is a 5-trading-day
return sampled at a weekly (5-trading-day) cadence, consecutive
observations barely overlap, but the number of *independent* return
episodes in this sample is still on the order of the number of calendar
years covered (roughly 15), not the number of weeks (up to ~1,130) — so
these t-statistics should be read as an upper bound on statistical
confidence, not a rigorous significance test.

## Mean Rank IC by factor (5D relative return, sorted descending)

| Factor | n_dates | Coverage % | Mean IC | Std IC | Naive t-stat | ICIR | % positive |
|---|---:|---:|---:|---:|---:|---:|---:|
| realized_vol_60d | 1,118 | 98.9% | 0.0538 | 0.491 | 3.66 | 0.110 | 54.2% |
| adv_20d | 1,126 | 99.6% | 0.0473 | 0.471 | 3.37 | 0.100 | 54.4% |
| sales_to_price | 302 | 28.2% | 0.0441 | 0.491 | 1.56 | 0.090 | 52.6% |
| realized_vol_20d | 1,126 | 99.6% | 0.0417 | 0.470 | 2.98 | 0.089 | 50.8% |
| downside_vol_20d | 1,126 | 99.6% | 0.0317 | 0.464 | 2.29 | 0.068 | 50.7% |
| momentum_12_1 | 1,078 | 95.4% | 0.0305 | 0.458 | 2.19 | 0.067 | 52.3% |
| gross_profitability | 523 | 27.5% | 0.0226 | 0.650 | 0.79 | 0.035 | 50.7% |
| asset_growth | 818 | 72.4% | 0.0183 | 0.430 | 1.21 | 0.043 | 51.7% |
| momentum_3_1 | 1,117 | 98.9% | 0.0139 | 0.426 | 1.09 | 0.033 | 49.0% |
| momentum_6_1 | 1,104 | 97.7% | 0.0072 | 0.443 | 0.54 | 0.016 | 48.9% |
| reversal_5d | 1,129 | 99.9% | 0.0040 | 0.426 | 0.31 | 0.009 | 49.7% |
| reversal_20d | 1,126 | 99.6% | -0.0057 | 0.435 | -0.44 | -0.013 | 48.0% |
| reversal_1d | 1,130 | 100.0% | -0.0082 | 0.426 | -0.65 | -0.019 | 47.8% |
| earnings_yield | 833 | 49.1% | -0.0111 | 0.560 | -0.57 | -0.020 | 47.3% |
| roa | 818 | 48.9% | -0.0185 | 0.560 | -0.95 | -0.033 | 47.6% |
| leverage | 869 | 53.7% | -0.0186 | 0.481 | -1.14 | -0.039 | 47.3% |
| book_to_market | 869 | 68.2% | -0.0245 | 0.470 | -1.54 | -0.052 | 46.8% |
| operating_margin | 284 | 16.1% | -0.0246 | 0.575 | -0.72 | -0.043 | 45.8% |
| amihud_20d | 1,126 | 99.2% | -0.0445 | 0.458 | -3.26 | -0.097 | 45.5% |

(Coverage % for `sales_to_price`, `gross_profitability`, `operating_margin`,
`roa`, `earnings_yield` is real, measured coverage carried over from the
already-fixed fundamental panel — see
`reports/fundamental_factor_coverage_validation.md`. Recall from that
report that `roa`, `earnings_yield`, `sales_to_price`, `gross_profitability`,
and `operating_margin` all depend on TTM flow variables confirmed to
contain silent duration-collision corruption; their IC values here should
be read with that data-quality caveat, not treated as a clean read on
those factors' true predictive content.)

## Alpha decay (1D / 5D / 20D)

See `reports/figures/alpha_decay.png` and `reports/figures/ic_heatmap_factor_horizon.png`
for the full factor × horizon grid (`reports/factor_metrics.csv` columns
`ic_1d`/`ic_5d`/`ic_20d`). Two patterns stand out, both consistent with
economic intuition and neither cherry-picked for size:

- The two ADV/liquidity-family factors (`adv_20d`, `amihud_20d`) and the
  volatility family (`realized_vol_20d`/`60d`, `downside_vol_20d`) show
  monotonically *increasing* magnitude from 1D to 20D (e.g. `realized_vol_60d`:
  0.021 → 0.054 → 0.103), consistent with liquidity/volatility
  characteristics being persistent, slow-moving properties whose
  cross-sectional relationship with returns strengthens over a longer
  horizon rather than reflecting a fast-decaying short-term signal.
- `momentum_12_1` decays from 5D (0.031) to 20D (0.022) after starting
  near zero at 1D (0.010) — a small, noisy, but directionally-expected
  pattern for a 12-1 month momentum measure, which is not built to have
  strong daily predictive power.

## Year-by-year stability and factor persistence

`reports/figures/ic_time_series_strongest.png` plots the 20-week rolling
mean IC for the two strongest factors by |mean IC| (`realized_vol_60d`,
`adv_20d`). Both oscillate around a modest positive mean with no single
year dominating the full-sample average, but neither shows a stable,
sign-consistent regime across the full 2010-2026 span — consistent with a
weak-but-not-obviously-spurious cross-sectional relationship rather than a
robust, always-on factor.

Persistence (week-over-week Spearman rank autocorrelation,
`persistence_rank_autocorr` column): fundamental factors and slower price
factors (`gross_profitability` 0.994, `leverage` 0.997, `book_to_market`
0.991, `adv_20d` 0.989, `momentum_12_1` 0.947) are extremely persistent
week to week, implying a portfolio built on them would trade
infrequently. `reversal_1d` (0.008) and `reversal_5d` (0.021) are
essentially non-persistent by construction (a 1-day/5-day prior return is
a fast-moving quantity), implying very high turnover if traded directly.
This matters for Stage 4 (transaction costs): reversal-type signals will
be far more cost-sensitive than momentum, volatility, liquidity, or
fundamental signals.

## Summary

**Strongest factors** (|mean IC| > 0.03, naive |t| > 2): `realized_vol_60d`,
`adv_20d`, `realized_vol_20d`, `downside_vol_20d`, `momentum_12_1` (all
positive-sign, meaning higher realized volatility / higher dollar volume /
stronger 12-1 momentum associates with higher relative forward return in
this sample), and `amihud_20d` (negative sign — note `amihud_20d` is an
illiquidity measure, so a negative IC here means *more* illiquid names
had *lower* forward relative returns in this sample, the opposite of a
classical illiquidity-premium story; this is reported as-is, not adjusted
to match prior expectation).

**Weakest / near-zero factors:** `reversal_5d` (IC 0.004, essentially
noise), `momentum_6_1` (0.007), `roa`/`earnings_yield`/`operating_margin`
(all small and negative, and all TTM-flow-dependent — see the data-quality
caveat above).

**Unstable factors:** none of the 19 factors shows a clearly stable,
single-direction signal across all three horizons *and* a rolling-window
view that stays consistently on one side of zero; `realized_vol_60d` and
`adv_20d` are the closest to horizon-consistent (same sign at 1D/5D/20D),
but their rolling 20-week IC in the time-series figure still crosses zero
repeatedly.

**Factors with insufficient coverage to draw a real conclusion:**
`operating_margin` (16.1% coverage, only 284 usable dates),
`gross_profitability` (27.5%), `sales_to_price` (28.2%) — for these three,
"no measurable IC" and "genuinely weak factor" are not distinguishable
from "too little data to tell" given both the low date count and the
known TTM-corruption caveat.

**Factors with statistical but weak economic usefulness:** even the
strongest factors here (|mean IC| ≈ 0.04–0.05) are well below what would
typically be considered an economically strong cross-sectional signal in
a production-scale study (mean IC of 0.03–0.05 is often considered modest
even in large universes); at 8 names, an IC of this size translates to a
very small, likely non-implementable expected edge once transaction costs
are considered (see Stage 4).

**Factors worth carrying into ML (Stage 2):** the price/technical family
in full (momentum, reversal, realized/downside volatility, ADV, Amihud) —
these have near-complete coverage (95-100%) across the full 1,130-week
sample, giving the ML stage enough rows to do a meaningful chronological
train/test split. The fundamental factors are carried into the
"fundamentals-only" and "combined" ablations in Stage 2 for honesty and
completeness, but their much lower coverage (16-72%) and the documented
TTM-corruption issue are carried forward explicitly as known caveats on
whatever incremental value Stage 2 finds (or does not find) from adding
them.
