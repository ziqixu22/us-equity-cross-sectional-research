"""Pre-registered intermediate-horizon momentum characteristics."""

from __future__ import annotations

import pandas as pd


DEFINITIONS = {"momentum_12_1": (252, 21), "momentum_6_1": (126, 21), "momentum_3_1": (63, 21)}


def add_momentum(bars: pd.DataFrame, price_column: str = "adjusted_close") -> pd.DataFrame:
    """Use P[t-skip] / P[t-lookback] - 1; no recent-day return enters the score."""
    if not {"symbol", "date", price_column}.issubset(bars.columns):
        raise ValueError("momentum requires symbol, date, and adjusted_close")
    result = bars.sort_values(["symbol", "date"]).copy()
    grouped = result.groupby("symbol", sort=False)[price_column]
    for name, (lookback, skip) in DEFINITIONS.items():
        observations = grouped.transform(
            lambda values: values.rolling(lookback + 1, min_periods=lookback + 1).count()
        )
        result[name] = grouped.shift(skip) / grouped.shift(lookback) - 1
        result.loc[observations.lt(lookback + 1), name] = float("nan")
    return result
