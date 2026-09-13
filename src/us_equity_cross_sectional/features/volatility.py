"""Daily adjusted-return realized-volatility characteristics."""

from __future__ import annotations

import numpy as np
import pandas as pd


def add_volatility(
    bars: pd.DataFrame, windows: tuple[int, ...] = (20, 60), price_column: str = "adjusted_close"
) -> pd.DataFrame:
    """Add annualized standard deviation and 20-day RMS downside volatility through date t."""
    if not {"symbol", "date", price_column}.issubset(bars.columns):
        raise ValueError("volatility requires symbol, date, and adjusted_close")
    result = bars.sort_values(["symbol", "date"]).copy()
    returns = result.groupby("symbol", sort=False)[price_column].transform(
        lambda values: values.pct_change(fill_method=None)
    )
    result["daily_adjusted_return"] = returns
    for window in windows:
        result[f"realized_vol_{window}d"] = returns.groupby(result["symbol"], sort=False).transform(
            lambda values: values.rolling(window, min_periods=window).std(ddof=1) * np.sqrt(252)
        )
    if 20 in windows:
        squared_downside = np.minimum(returns, 0.0) ** 2
        result["downside_vol_20d"] = squared_downside.groupby(result["symbol"], sort=False).transform(
            lambda values: np.sqrt(values.rolling(20, min_periods=20).mean()) * np.sqrt(252)
        )
    return result
