"""Pre-registered short-term reversal characteristics."""

from __future__ import annotations

import pandas as pd


def add_reversal(bars: pd.DataFrame, price_column: str = "adjusted_close") -> pd.DataFrame:
    """Store raw prior returns and the registered reversal score, their negative."""
    if not {"symbol", "date", price_column}.issubset(bars.columns):
        raise ValueError("reversal requires symbol, date, and adjusted_close")
    result = bars.sort_values(["symbol", "date"]).copy()
    grouped = result.groupby("symbol", sort=False)[price_column]
    for horizon in (1, 5, 20):
        prior = result[price_column] / grouped.shift(horizon) - 1
        observations = grouped.transform(
            lambda values: values.rolling(horizon + 1, min_periods=horizon + 1).count()
        )
        result[f"prior_return_{horizon}d"] = prior.where(observations.ge(horizon + 1))
        result[f"reversal_{horizon}d"] = -result[f"prior_return_{horizon}d"]
    return result
