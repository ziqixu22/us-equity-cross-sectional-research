"""Small, provider-independent checks for normalized daily price bars."""

from __future__ import annotations

import pandas as pd


REQUIRED_BAR_COLUMNS = {"symbol", "date", "open", "high", "low", "close", "volume"}


def validate_daily_bars(bars: pd.DataFrame) -> None:
    """Raise ValueError when a normalized daily-bar table violates core invariants."""
    missing = REQUIRED_BAR_COLUMNS.difference(bars.columns)
    if missing:
        raise ValueError(f"missing required daily-bar columns: {sorted(missing)}")
    if bars[["symbol", "date"]].isna().any().any():
        raise ValueError("symbol and date must be non-null")
    if bars.duplicated(["symbol", "date"]).any():
        raise ValueError("duplicate symbol/date records")
    if (bars["volume"] < 0).any():
        raise ValueError("volume must be non-negative")
    if (bars[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("OHLC values must be positive")
    if ((bars["high"] < bars[["open", "low", "close"]].max(axis=1)) | (
        bars["low"] > bars[["open", "high", "close"]].min(axis=1)
    )).any():
        raise ValueError("impossible OHLC relationship")
    ordered = bars.sort_values(["symbol", "date"])
    if ordered.groupby("symbol")["date"].diff().dropna().le(pd.Timedelta(0)).any():
        raise ValueError("dates must strictly increase within symbol")
