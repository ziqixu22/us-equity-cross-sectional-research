"""Forward close-to-close labels with an explicit one-session execution lag."""

from __future__ import annotations

import pandas as pd


def add_forward_return_labels(bars: pd.DataFrame, horizons: tuple[int, ...] = (1, 5, 20)) -> pd.DataFrame:
    """Add labels where horizon ``h`` is P[t+1+h] / P[t+1] - 1 for a signal at t."""
    required = {"symbol", "date", "adjusted_close"}
    missing = required.difference(bars.columns)
    if missing:
        raise ValueError(f"missing label columns: {sorted(missing)}")
    result = bars.sort_values(["symbol", "date"]).copy()
    price = result.groupby("symbol", sort=False)["adjusted_close"]
    dates = result.groupby("symbol", sort=False)["date"]
    result["execution_date"] = dates.shift(-1)
    execution_price = price.shift(-1)
    for horizon in horizons:
        if horizon <= 0:
            raise ValueError("forward-return horizon must be positive")
        result[f"forward_return_{horizon}d"] = price.shift(-(horizon + 1)) / execution_price - 1
    return result


def add_relative_return_labels(panel: pd.DataFrame, horizons: tuple[int, ...] = (1, 5, 20)) -> pd.DataFrame:
    """Subtract the same-date equal-weight cross-sectional forward-return mean."""
    if "research_date" not in panel:
        raise ValueError("relative-return labels require research_date")
    result = panel.copy()
    for horizon in horizons:
        column = f"forward_return_{horizon}d"
        if column not in result:
            raise ValueError(f"missing forward-return label: {column}")
        benchmark = result.groupby("research_date", sort=False)[column].transform("mean")
        result[f"relative_return_{horizon}d"] = result[column] - benchmark
    return result


def validate_weekly_panel_keys(panel: pd.DataFrame) -> None:
    """Require one observation per prototype security and weekly research date."""
    required = {"research_date", "security_id"}
    missing = required.difference(panel.columns)
    if missing:
        raise ValueError(f"missing panel-key columns: {sorted(missing)}")
    if panel.duplicated(["research_date", "security_id"]).any():
        raise ValueError("duplicate research_date/security_id key")
