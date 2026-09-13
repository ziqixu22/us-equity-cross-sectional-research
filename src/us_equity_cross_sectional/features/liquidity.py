"""Raw dollar-volume and conservative Amihud-style liquidity characteristics."""

from __future__ import annotations

import numpy as np
import pandas as pd


def add_split_consistent_volume(bars: pd.DataFrame) -> pd.DataFrame:
    """Put reported volume onto the same post-split share basis as Yahoo's historical close."""
    if not {"symbol", "date", "close", "volume", "stock_splits"}.issubset(bars.columns):
        raise ValueError("split-consistent volume requires symbol, date, close, volume, and stock_splits")
    result = bars.sort_values(["symbol", "date"]).copy()
    split = result["stock_splits"].fillna(0).replace(0, 1.0)
    # A split affects prior rows; the event day is already reported on the new share basis.
    result["split_volume_factor"] = split.groupby(result["symbol"], sort=False).transform(
        lambda values: values.iloc[::-1].cumprod().iloc[::-1] / values
    )
    result["split_consistent_volume"] = result["volume"] * result["split_volume_factor"]
    result["split_consistent_dollar_volume"] = result["close"] * result["split_consistent_volume"]
    return result


def add_liquidity(bars: pd.DataFrame, windows: tuple[int, ...] = (20, 60)) -> pd.DataFrame:
    """Add trailing average dollar volume and split/zero-volume-safe Amihud values."""
    required = {"symbol", "date", "close", "adjusted_close", "volume"}
    missing = required.difference(bars.columns)
    if missing:
        raise ValueError(f"liquidity requires columns: {sorted(missing)}")
    result = add_split_consistent_volume(bars)
    result["dollar_volume"] = result["split_consistent_dollar_volume"]
    for window in windows:
        result[f"adv_{window}d"] = result.groupby("symbol", sort=False)["dollar_volume"].transform(
            lambda values: values.rolling(window, min_periods=window).mean()
        )
    daily_return = result.groupby("symbol", sort=False)["adjusted_close"].transform(
        lambda values: values.pct_change(fill_method=None)
    )
    valid_volume = result["dollar_volume"].where(result["dollar_volume"] > 0)
    amihud = daily_return.abs() / valid_volume
    if "stock_splits" in result:
        amihud = amihud.where(result["stock_splits"].fillna(0).eq(0))
    if 20 in windows:
        result["amihud_20d"] = amihud.groupby(result["symbol"], sort=False).transform(
            lambda values: values.rolling(20, min_periods=20).mean()
        )
    return result
