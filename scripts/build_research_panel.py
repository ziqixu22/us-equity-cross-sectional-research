"""Build the combined weekly price+fundamental research panel for Stage 1.

Scope note (explicit, non-fabricated limitation): the full Milestone 3
S&P-100 price-factor universe (data/raw/yfinance_universe/) is not present
in this environment (data/raw/ is gitignored and that particular cache was
not part of what survived the earlier data-loss/restoration incident).
Rebuilding it would mean re-downloading ~100 tickers of multi-year daily
history, which this task's operating rules explicitly discourage
("do not rebuild slow data pipelines repeatedly", "prefer a defensible
smaller-scope result"). The 8-ticker universe used for the SEC fundamentals
panel (data/raw/yfinance_provider_audit/2026-09-11/) *is* fully cached
(daily OHLCV+dividends+splits back to each ticker's IPO), so this script
uses that same 8-ticker universe for price factors, which lets every price
factor and every fundamental factor be evaluated on one consistent panel.
This is a smaller, explicitly-scoped-down universe than the original
Milestone 3 report describes, not a claim that it reproduces that report.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from us_equity_cross_sectional.features.labels import (
    add_forward_return_labels,
    add_relative_return_labels,
    validate_weekly_panel_keys,
)
from us_equity_cross_sectional.features.liquidity import add_liquidity
from us_equity_cross_sectional.features.momentum import add_momentum
from us_equity_cross_sectional.features.reversal import add_reversal
from us_equity_cross_sectional.features.volatility import add_volatility

ROOT = Path(__file__).resolve().parents[1]
SYMBOLS = ("AAPL", "MSFT", "KO", "JNJ", "XOM", "JPM", "WMT", "NVDA")
SNAPSHOT = "2026-09-11"

PRICE_FACTOR_COLUMNS = [
    "momentum_12_1", "momentum_6_1", "momentum_3_1",
    "reversal_1d", "reversal_5d", "reversal_20d",
    "realized_vol_20d", "realized_vol_60d", "downside_vol_20d",
    "adv_20d", "adv_60d", "amihud_20d",
]
FUNDAMENTAL_FACTOR_COLUMNS = [
    "book_to_market", "earnings_yield", "sales_to_price",
    "roa", "gross_profitability", "operating_margin", "leverage", "asset_growth",
]
ALL_FACTOR_COLUMNS = PRICE_FACTOR_COLUMNS + FUNDAMENTAL_FACTOR_COLUMNS


def load_daily_bars() -> pd.DataFrame:
    raw_dir = ROOT / f"data/raw/yfinance_provider_audit/{SNAPSHOT}"
    frames = []
    for symbol in SYMBOLS:
        raw = pd.read_csv(raw_dir / f"{symbol}.csv")
        raw = raw.rename(columns={
            raw.columns[0]: "observed_at", "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Adj Close": "adjusted_close", "Volume": "volume",
            "Dividends": "dividends", "Stock Splits": "stock_splits",
        })
        timestamp = pd.to_datetime(raw["observed_at"], utc=True)
        raw["date"] = timestamp.dt.tz_convert("America/New_York").dt.normalize().dt.tz_localize(None)
        raw["symbol"] = symbol
        raw["security_id"] = symbol
        frames.append(raw[[
            "security_id", "symbol", "date", "open", "high", "low", "close", "adjusted_close",
            "volume", "dividends", "stock_splits",
        ]])
    bars = pd.concat(frames, ignore_index=True)
    return bars.loc[bars.date.ge(pd.Timestamp("2005-01-01"))].copy()


def select_weekly_research_dates(panel: pd.DataFrame) -> pd.DataFrame:
    unique_dates = pd.Series(panel["date"].drop_duplicates().sort_values())
    weekly_dates = unique_dates.groupby(unique_dates.dt.to_period("W-FRI")).max()
    return panel.loc[panel["date"].isin(weekly_dates)].copy()


def market_close_utc(dates: pd.Series) -> pd.Series:
    local = pd.to_datetime(dates).dt.tz_localize("America/New_York") + pd.Timedelta(hours=16)
    return local.dt.tz_convert("UTC")


def main() -> None:
    bars = load_daily_bars()
    features = add_liquidity(add_volatility(add_reversal(add_momentum(bars))))
    labelled = add_forward_return_labels(features, horizons=(1, 5, 20))
    weekly = select_weekly_research_dates(labelled)
    weekly["research_date"] = weekly["date"]
    weekly = add_relative_return_labels(weekly, horizons=(1, 5, 20))
    validate_weekly_panel_keys(weekly)

    fundamentals = pd.read_csv(ROOT / f"data/processed/asof_fundamental_panel_{SNAPSHOT}_fixed.csv")
    fundamentals["research_date"] = pd.to_datetime(fundamentals["research_date"])
    factors = pd.read_csv(ROOT / f"data/processed/fundamental_factors_{SNAPSHOT}_fixed.csv")
    factors["research_date"] = pd.to_datetime(factors["research_date"])
    fund_merged = fundamentals[["research_date", "security_id", "market_cap", "market_cap_eligible"]].merge(
        factors, on=["research_date", "security_id"], how="left", suffixes=("", "_dup")
    )

    price_cols = [
        "research_date", "security_id", "symbol",
        "forward_return_1d", "forward_return_5d", "forward_return_20d",
        "relative_return_1d", "relative_return_5d", "relative_return_20d",
        *PRICE_FACTOR_COLUMNS,
    ]
    panel = weekly[price_cols].merge(fund_merged, on=["research_date", "security_id"], how="left")
    panel = panel.sort_values(["research_date", "security_id"]).reset_index(drop=True)

    out_path = ROOT / f"data/processed/research_panel_{SNAPSHOT}.csv"
    panel.to_csv(out_path, index=False)
    print("rows", len(panel), "dates", panel.research_date.nunique(), "securities", panel.security_id.nunique())
    print("saved to", out_path)


if __name__ == "__main__":
    main()
