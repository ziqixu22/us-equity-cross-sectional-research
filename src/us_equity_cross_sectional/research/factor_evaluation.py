"""Cross-sectional factor evaluation: Rank IC, quantile spreads, decay, stability.

Scope and honesty notes (read before interpreting any number this module
produces):

- The research panel evaluated here has only 8 securities per
  cross-section (see ``scripts/build_research_panel.py`` for why). Every
  per-date statistic below (Rank IC, quantile means) is computed from at
  most 8 observations. This is far below what a production cross-sectional
  study would use (hundreds to thousands of names) and every daily/weekly
  IC value is intrinsically noisy. Aggregated statistics (mean IC, ICIR)
  partially average out that noise across dates, but do not eliminate the
  small cross-section problem, and quintile (5-group) sorts are especially
  unreliable with only 8 names per date (each "quintile" holds 1-2 names).
  This module reports what the data supports and states sample-size
  caveats explicitly rather than presenting these numbers as
  production-grade.
- Signs are never flipped based on realized performance. Whatever sign a
  factor's formula defines (see ``features/fundamental.py`` and the price
  factor modules) is the sign evaluated here.
- No factor is discarded for having a weak or near-zero result; this
  module and the reports built from it are required to report failed and
  null findings, not just successes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def daily_rank_ic(
    panel: pd.DataFrame, factor: str, label: str, date_column: str = "research_date", min_obs: int = 3
) -> pd.DataFrame:
    """Per-date cross-sectional Spearman correlation between a factor and a forward label.

    A date is skipped (not zero-filled) when fewer than ``min_obs`` names
    have both the factor and the label non-missing that date -- Spearman
    correlation is not meaningful on 1-2 points, and skipping (rather than
    fabricating a 0.0) keeps ``n_dates`` an honest denominator.
    """
    rows = []
    for date, group in panel.groupby(date_column):
        sub = group[[factor, label]].dropna()
        if len(sub) < min_obs:
            continue
        if sub[factor].nunique() < 2 or sub[label].nunique() < 2:
            continue
        ic, _ = stats.spearmanr(sub[factor], sub[label])
        if np.isnan(ic):
            continue
        rows.append({date_column: date, "rank_ic": ic, "n": len(sub)})
    return pd.DataFrame(rows)


def summarize_ic(ic_frame: pd.DataFrame) -> dict[str, float]:
    """Mean/median/std/ICIR/positive-frequency summary of a daily_rank_ic() output."""
    if ic_frame.empty:
        return {
            "n_dates": 0, "mean_ic": np.nan, "median_ic": np.nan, "std_ic": np.nan,
            "icir": np.nan, "pct_positive": np.nan,
        }
    ic = ic_frame["rank_ic"]
    std = ic.std(ddof=1)
    return {
        "n_dates": int(len(ic)),
        "mean_ic": float(ic.mean()),
        "median_ic": float(ic.median()),
        "std_ic": float(std) if pd.notna(std) else np.nan,
        "icir": float(ic.mean() / std) if pd.notna(std) and std > 0 else np.nan,
        "pct_positive": float((ic > 0).mean()),
    }


def quantile_returns(
    panel: pd.DataFrame, factor: str, label: str, n_quantiles: int = 5,
    date_column: str = "research_date", min_obs: int | None = None,
) -> pd.DataFrame:
    """Per-date mean forward label by within-date factor quantile bucket.

    ``min_obs`` defaults to ``n_quantiles`` (need at least one name per
    bucket to form every bucket that date); dates with fewer names, or
    where the factor has too few distinct values to form ``n_quantiles``
    groups, are skipped rather than padded with an empty/duplicated
    bucket.
    """
    min_obs = min_obs or n_quantiles
    rows = []
    for date, group in panel.groupby(date_column):
        sub = group[[factor, label]].dropna()
        if len(sub) < min_obs or sub[factor].nunique() < n_quantiles:
            continue
        try:
            bucket = pd.qcut(sub[factor], n_quantiles, labels=False, duplicates="drop")
        except ValueError:
            continue
        if bucket.nunique() < n_quantiles:
            continue
        sub = sub.assign(bucket=bucket)
        means = sub.groupby("bucket")[label].mean()
        for b, m in means.items():
            rows.append({date_column: date, "quantile": int(b), "mean_label": m})
    long = pd.DataFrame(rows)
    if long.empty:
        return long
    return long.groupby("quantile")["mean_label"].agg(["mean", "std", "count"]).reset_index()


def quantile_spread(
    panel: pd.DataFrame, factor: str, label: str, n_quantiles: int = 5, date_column: str = "research_date"
) -> dict[str, float]:
    """Mean top-quantile-minus-bottom-quantile forward label, averaged across dates."""
    rows = []
    min_obs = n_quantiles
    for date, group in panel.groupby(date_column):
        sub = group[[factor, label]].dropna()
        if len(sub) < min_obs or sub[factor].nunique() < n_quantiles:
            continue
        try:
            bucket = pd.qcut(sub[factor], n_quantiles, labels=False, duplicates="drop")
        except ValueError:
            continue
        if bucket.nunique() < n_quantiles:
            continue
        sub = sub.assign(bucket=bucket)
        top = sub.loc[sub.bucket.eq(bucket.max()), label].mean()
        bottom = sub.loc[sub.bucket.eq(0), label].mean()
        rows.append(top - bottom)
    if not rows:
        return {"n_dates": 0, "mean_spread": np.nan, "std_spread": np.nan}
    arr = np.array(rows)
    return {
        "n_dates": int(len(arr)),
        "mean_spread": float(np.mean(arr)),
        "std_spread": float(np.std(arr, ddof=1)) if len(arr) > 1 else np.nan,
    }


def alpha_decay(panel: pd.DataFrame, factor: str, horizons: tuple[str, ...] = ("1d", "5d", "20d")) -> pd.DataFrame:
    """Mean Rank IC of one factor against forward_return_{h} for each horizon."""
    rows = []
    for h in horizons:
        label = f"forward_return_{h}"
        if label not in panel.columns:
            continue
        ic = daily_rank_ic(panel, factor, label)
        summary = summarize_ic(ic)
        rows.append({"horizon": h, **summary})
    return pd.DataFrame(rows)


def yearly_ic_stability(panel: pd.DataFrame, factor: str, label: str, date_column: str = "research_date") -> pd.DataFrame:
    """Mean Rank IC per calendar year -- a simple, sample-size-appropriate stability check."""
    ic = daily_rank_ic(panel, factor, label, date_column=date_column)
    if ic.empty:
        return ic
    ic["year"] = pd.to_datetime(ic[date_column]).dt.year
    return ic.groupby("year")["rank_ic"].agg(["mean", "std", "count"]).reset_index()


def factor_coverage(panel: pd.DataFrame, factor: str) -> dict[str, float]:
    total = len(panel)
    valid = panel[factor].notna().sum()
    return {
        "valid_observations": int(valid),
        "total_observations": int(total),
        "coverage_pct": float(valid / total * 100) if total else np.nan,
    }


def factor_persistence(panel: pd.DataFrame, factor: str, date_column: str = "research_date", security_column: str = "security_id") -> dict[str, float]:
    """Week-over-week rank autocorrelation of a factor -- a simple turnover/persistence proxy.

    Computed as the average cross-sectional Spearman correlation between a
    factor's values this week and the same securities' values the prior
    research date. High persistence means a factor-based portfolio would
    trade infrequently; low persistence implies high turnover.
    """
    wide = panel.pivot_table(index=date_column, columns=security_column, values=factor)
    wide = wide.sort_index()
    if len(wide) < 2:
        return {"n_pairs": 0, "mean_rank_autocorr": np.nan}
    corrs = []
    dates = wide.index.tolist()
    for i in range(1, len(dates)):
        prev = wide.iloc[i - 1]
        curr = wide.iloc[i]
        both = pd.concat([prev, curr], axis=1).dropna()
        if len(both) < 3 or both.iloc[:, 0].nunique() < 2 or both.iloc[:, 1].nunique() < 2:
            continue
        corr, _ = stats.spearmanr(both.iloc[:, 0], both.iloc[:, 1])
        if not np.isnan(corr):
            corrs.append(corr)
    if not corrs:
        return {"n_pairs": 0, "mean_rank_autocorr": np.nan}
    return {"n_pairs": len(corrs), "mean_rank_autocorr": float(np.mean(corrs))}


def evaluate_all_factors(
    panel: pd.DataFrame, factors: list[str], primary_label: str = "relative_return_5d",
    horizons: tuple[str, ...] = ("1d", "5d", "20d"), n_quantiles: int = 5,
) -> pd.DataFrame:
    """One row per factor: coverage, primary-horizon IC summary, spread, decay, persistence."""
    rows = []
    for factor in factors:
        coverage = factor_coverage(panel, factor)
        ic = daily_rank_ic(panel, factor, primary_label)
        ic_summary = summarize_ic(ic)
        spread = quantile_spread(panel, factor, primary_label, n_quantiles=n_quantiles)
        decay = alpha_decay(panel, factor, horizons=horizons)
        persistence = factor_persistence(panel, factor)
        row = {"factor": factor, **coverage, **ic_summary, **{f"spread_{k}": v for k, v in spread.items()}}
        for _, d in decay.iterrows():
            row[f"ic_{d['horizon']}"] = d["mean_ic"]
            row[f"icir_{d['horizon']}"] = d["icir"]
        row["persistence_rank_autocorr"] = persistence["mean_rank_autocorr"]
        rows.append(row)
    return pd.DataFrame(rows)
