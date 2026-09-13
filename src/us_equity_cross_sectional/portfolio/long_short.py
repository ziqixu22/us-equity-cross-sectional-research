"""Weekly long-short tercile portfolio construction from an OOS prediction series.

Only out-of-sample predictions are used (i.e. the ``research_date``/
``security_id`` rows a chronological model-evaluation fold labeled as
test, never as train) -- this module does not itself re-check that, it
trusts its caller to have passed only OOS rows, exactly as
``research/model_evaluation.py`` produces them.

Universe note: with only 8 securities, a classic quintile (5-bucket) long
top / short bottom sort leaves each bucket with 1-2 names. This module
uses **terciles** (top third long, bottom third short) instead, consistent
with the tercile spread metric already used in Stage 2
(``model_evaluation.prediction_turnover``/``top_bottom_tercile_spread``),
and documents this choice rather than reporting a quintile portfolio that
would be even noisier at this scale.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _tercile_legs(group: pd.DataFrame, score_column: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    ranked = group.sort_values(score_column)
    k = max(1, len(ranked) // 3)
    bottom = ranked.head(k)
    top = ranked.tail(k)
    return top, bottom


def build_weekly_long_short_returns(
    oos_predictions: pd.DataFrame, panel: pd.DataFrame, *, score_column: str = "prediction",
    return_column: str = "forward_return_5d", date_column: str = "research_date",
    weighting: str = "equal", risk_column: str = "realized_vol_20d",
) -> pd.DataFrame:
    """Weekly dollar-neutral top-tercile-minus-bottom-tercile portfolio returns.

    ``weighting="equal"``: each leg's names are equal-weighted (weights sum
    to +1 for the long leg, -1 for the short leg -- 200% gross exposure,
    a standard 100/100 long-short convention).
    ``weighting="inverse_vol"``: within each leg, weight is proportional to
    1/realized_vol_20d (from ``panel``, joined on date+security), each leg
    still normalized to sum to +-1. This is the "one simple risk-aware
    variant" this task's Stage 3 allows in place of a full optimizer --
    no covariance matrix or optimization is used, just a per-name scalar.

    Returns one row per rebalance date with: n_long, n_short, long_return,
    short_return, portfolio_return (long_return - short_return, i.e. the
    P&L of +1 long weight and -1 short weight), turnover (fraction of the
    combined long+short name set that changed since the prior date).
    """
    if weighting not in {"equal", "inverse_vol"}:
        raise ValueError("weighting must be 'equal' or 'inverse_vol'")

    merged = oos_predictions.merge(
        panel[[date_column, "security_id", risk_column]], on=[date_column, "security_id"], how="left"
    ) if weighting == "inverse_vol" else oos_predictions.copy()

    rows = []
    prev_names: set[str] | None = None
    for date, group in merged.sort_values(date_column).groupby(date_column):
        sub = group.dropna(subset=[score_column, return_column])
        if len(sub) < 3:
            continue
        top, bottom = _tercile_legs(sub, score_column)
        if top.empty or bottom.empty:
            continue

        if weighting == "equal":
            long_return = top[return_column].mean()
            short_return = bottom[return_column].mean()
        else:
            top_risk = top[risk_column].clip(lower=1e-6).fillna(top[risk_column].median())
            bottom_risk = bottom[risk_column].clip(lower=1e-6).fillna(bottom[risk_column].median())
            top_w = (1 / top_risk) / (1 / top_risk).sum()
            bottom_w = (1 / bottom_risk) / (1 / bottom_risk).sum()
            long_return = float((top_w * top[return_column]).sum())
            short_return = float((bottom_w * bottom[return_column]).sum())

        names = set(top["security_id"]) | set(bottom["security_id"])
        if prev_names is None:
            turnover = np.nan
        else:
            turnover = len(names.symmetric_difference(prev_names)) / (len(names) + len(prev_names))
        prev_names = names

        rows.append({
            date_column: date, "n_long": len(top), "n_short": len(bottom),
            "long_return": long_return, "short_return": short_return,
            "portfolio_return": long_return - short_return, "turnover": turnover,
            "gross_exposure": 2.0,
        })
    return pd.DataFrame(rows)


def portfolio_performance_metrics(returns: pd.DataFrame, *, periods_per_year: int = 52, return_column: str = "portfolio_return") -> dict[str, float]:
    """Standard long-short performance metrics from a weekly return series.

    Sharpe assumes a zero risk-free rate (a long-short spread's "risk-free
    rate" is a modeling choice; zero is the simplest, most defensible
    default and is stated explicitly rather than silently assumed).
    """
    r = returns[return_column].dropna()
    if r.empty:
        return {"n_periods": 0}
    nav = (1 + r).cumprod()
    total_return = float(nav.iloc[-1] - 1)
    n_years = len(r) / periods_per_year
    annualized_return = float((1 + total_return) ** (1 / n_years) - 1) if n_years > 0 else np.nan
    annualized_vol = float(r.std(ddof=1) * np.sqrt(periods_per_year))
    sharpe = float(annualized_return / annualized_vol) if annualized_vol > 0 else np.nan
    running_max = nav.cummax()
    drawdown = nav / running_max - 1
    max_drawdown = float(drawdown.min())
    hit_rate = float((r > 0).mean())
    mean_turnover = float(returns["turnover"].dropna().mean()) if "turnover" in returns else np.nan
    mean_gross = float(returns["gross_exposure"].mean()) if "gross_exposure" in returns else np.nan
    return {
        "n_periods": int(len(r)),
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_vol,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_drawdown,
        "hit_rate": hit_rate,
        "mean_turnover": mean_turnover,
        "mean_gross_exposure": mean_gross,
    }


def cumulative_nav(returns: pd.DataFrame, return_column: str = "portfolio_return", date_column: str = "research_date") -> pd.DataFrame:
    r = returns[[date_column, return_column]].dropna().sort_values(date_column).copy()
    r["nav"] = (1 + r[return_column]).cumprod()
    r["running_max"] = r["nav"].cummax()
    r["drawdown"] = r["nav"] / r["running_max"] - 1
    return r
