"""Build the weekly price and point-in-time fundamental panel."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from us_equity_cross_sectional.features.fundamental import ALL_FACTORS as FUNDAMENTAL_FACTORS
from us_equity_cross_sectional.features.labels import (
    add_forward_return_labels,
    add_relative_return_labels,
    validate_weekly_panel_keys,
)
from us_equity_cross_sectional.features.liquidity import add_liquidity
from us_equity_cross_sectional.features.momentum import add_momentum
from us_equity_cross_sectional.features.reversal import add_reversal
from us_equity_cross_sectional.features.volatility import add_volatility
from us_equity_cross_sectional.research.run_paths import PANEL_PATH, RUN_ROOT, SNAPSHOT, SYMBOLS

PRICE_FACTOR_COLUMNS = [
    "momentum_12_1", "momentum_6_1", "momentum_3_1",
    "reversal_1d", "reversal_5d", "reversal_20d",
    "realized_vol_20d", "realized_vol_60d", "downside_vol_20d",
    "adv_20d", "adv_60d", "amihud_20d",
]
HORIZONS = (1, 5, 20)


def read_price_history(path: Path) -> pd.DataFrame:
    bars = pd.read_csv(path)
    bars["date"] = (
        pd.to_datetime(bars["Date"], utc=True)
        .dt.tz_convert("America/New_York")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    if (bars.empty or bars["date"].isna().any() or not bars["date"].is_monotonic_increasing
            or bars["date"].duplicated().any()):
        raise ValueError(f"Expected nonempty, unique and ordered daily bars in {path}")
    return bars


def select_weekly_research_dates(panel: pd.DataFrame) -> pd.DataFrame:
    """Choose the last observed trading session of each Friday-ended week."""
    dates = panel["date"]
    return panel.loc[dates.eq(dates.groupby(dates.dt.to_period("W-FRI")).transform("max"))].copy()


def main() -> None:
    raw_dir = RUN_ROOT / "data/raw/yfinance_provider_audit" / SNAPSHOT
    frames = []
    for symbol in SYMBOLS:
        bars = read_price_history(raw_dir / f"{symbol}.csv").rename(columns={
            "Open": "open", "High": "high", "Low": "low", "Close": "close",
            "Adj Close": "adjusted_close", "Volume": "volume",
            "Dividends": "dividends", "Stock Splits": "stock_splits",
        })
        bars["symbol"] = bars["security_id"] = symbol
        frames.append(bars)
    daily = pd.concat(frames, ignore_index=True)
    daily = daily.loc[daily["date"].ge("2005-01-01")].copy()
    last_prices = daily.loc[daily["date"].lt(SNAPSHOT)].groupby("symbol")["date"].max()
    if len(last_prices) != len(SYMBOLS) or last_prices.min() < pd.Timestamp(SNAPSHOT) - pd.Timedelta(days=10):
        raise ValueError("At least one price cache does not cover the requested cutoff")
    features = add_liquidity(add_volatility(add_reversal(add_momentum(daily))))
    features = features.loc[features["date"].lt(SNAPSHOT)].copy()
    prices = features[["close", "adjusted_close"]]
    if not (np.isfinite(prices) & prices.gt(0)).all().all():
        raise ValueError("All sampled close and adjusted-close prices must be finite and positive")
    if daily.groupby("symbol")["date"].apply(tuple).nunique() != 1 or daily["symbol"].nunique() != len(SYMBOLS):
        raise ValueError("The prototype requires matching daily trading sessions for all eight symbols")
    labelled = add_forward_return_labels(features, horizons=HORIZONS)
    labelled["execution_price"] = labelled.groupby("symbol")["adjusted_close"].shift(-1)
    weekly = select_weekly_research_dates(labelled)
    next_week = weekly.groupby("symbol")
    weekly["holding_end_date"] = next_week["execution_date"].shift(-1)
    weekly["holding_return"] = next_week["execution_price"].shift(-1) / weekly["execution_price"] - 1
    weekly["research_date"] = weekly["date"]
    weekly = add_relative_return_labels(weekly, horizons=HORIZONS)
    validate_weekly_panel_keys(weekly)

    processed = PANEL_PATH.parent
    fundamentals = pd.read_csv(processed / f"asof_fundamental_panel_{SNAPSHOT}.csv", parse_dates=["research_date"])
    factors = pd.read_csv(processed / f"fundamental_factors_{SNAPSHOT}.csv", parse_dates=["research_date"])
    keys = ["research_date", "security_id"]
    columns = ["research_date", "security_id", "symbol", "execution_date", "holding_end_date", "holding_return", *PRICE_FACTOR_COLUMNS]
    for horizon in HORIZONS:
        columns.extend((f"forward_return_{horizon}d", f"relative_return_{horizon}d", f"label_end_{horizon}d"))
    panel = weekly[columns].merge(fundamentals[keys + ["market_cap", "market_cap_eligible"]], on=keys, how="left", validate="one_to_one")
    panel = panel.merge(factors[keys + list(FUNDAMENTAL_FACTORS)], on=keys, how="left", validate="one_to_one")
    panel = panel.sort_values(keys).reset_index(drop=True)
    panel.to_csv(PANEL_PATH, index=False)
    print(f"{len(panel):,} rows, {panel.research_date.nunique():,} weeks, {panel.security_id.nunique()} securities")
    print(PANEL_PATH)


if __name__ == "__main__":
    main()
