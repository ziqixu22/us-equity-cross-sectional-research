"""Build the raw weekly label and price-feature panel; this script performs no factor evaluation."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd

from us_equity_cross_sectional.data.point_in_time import assert_feature_table_excludes_labels, assert_panel_timing
from us_equity_cross_sectional.data.validation import validate_daily_bars
from us_equity_cross_sectional.features.labels import (
    add_forward_return_labels,
    add_relative_return_labels,
    validate_weekly_panel_keys,
)
from us_equity_cross_sectional.features.liquidity import add_liquidity
from us_equity_cross_sectional.features.momentum import add_momentum
from us_equity_cross_sectional.features.reversal import add_reversal
from us_equity_cross_sectional.features.volatility import add_volatility


FEATURE_COLUMNS = [
    "momentum_12_1", "momentum_6_1", "momentum_3_1", "prior_return_1d", "prior_return_5d",
    "prior_return_20d", "reversal_1d", "reversal_5d", "reversal_20d", "realized_vol_20d",
    "realized_vol_60d", "downside_vol_20d", "adv_20d", "adv_60d", "amihud_20d",
]


def load_daily_bars(raw_dir: Path, metadata: pd.DataFrame) -> pd.DataFrame:
    """Normalize provider CSV caches into the small internal daily-bar schema."""
    frames: list[pd.DataFrame] = []
    for symbol in metadata["symbol"]:
        path = raw_dir / f"{symbol}.csv"
        if not path.exists():
            continue
        raw = pd.read_csv(path)
        raw = raw.rename(columns={
            raw.columns[0]: "observed_at", "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Adj Close": "adjusted_close", "Volume": "volume",
            "Dividends": "dividends", "Stock Splits": "stock_splits",
        })
        timestamp = pd.to_datetime(raw["observed_at"], utc=True)
        raw["date"] = timestamp.dt.tz_convert("America/New_York").dt.normalize().dt.tz_localize(None)
        raw["symbol"] = symbol
        raw["security_id"] = f"yf:{symbol}"
        frames.append(raw[[
            "security_id", "symbol", "date", "open", "high", "low", "close", "adjusted_close",
            "volume", "dividends", "stock_splits",
        ]])
    bars = pd.concat(frames, ignore_index=True)
    validate_daily_bars(bars)
    return bars


def market_close_utc(dates: pd.Series) -> pd.Series:
    local = pd.to_datetime(dates).dt.tz_localize("America/New_York") + pd.Timedelta(hours=16)
    return local.dt.tz_convert("UTC")


def select_weekly_research_dates(panel: pd.DataFrame) -> pd.DataFrame:
    """Keep dates that are the final observed market session in each Friday-ended week."""
    unique_dates = pd.Series(panel["date"].drop_duplicates().sort_values())
    weekly_dates = unique_dates.groupby(unique_dates.dt.to_period("W-FRI")).max()
    return panel.loc[panel["date"].isin(weekly_dates)].copy()


def factor_audit_markdown(panel: pd.DataFrame) -> str:
    rows = ["# Milestone 3 Factor Data Audit", "", "No IC, ranking, model, or portfolio result is reported here.", ""]
    rows += ["## Panel coverage", "", f"- Weekly research dates: {panel['research_date'].nunique()}.", f"- Rows: {len(panel):,}; prototype securities: {panel['symbol'].nunique()}.", "- Universe is the current S&P 100 snapshot and is not survivorship-bias-free.", ""]
    rows += ["## Raw-factor coverage and distribution", "", "| Factor | Present | Missing | 1st pct | Median | 99th pct |", "|---|---:|---:|---:|---:|---:|"]
    for column in FEATURE_COLUMNS:
        values = panel[column].dropna()
        rows.append(
            f"| {column} | {len(values):,} | {len(panel) - len(values):,} | "
            f"{values.quantile(.01):.6g} | {values.median():.6g} | {values.quantile(.99):.6g} |"
        )
    rows += ["", "## Cross-sectional and sector availability", "", "| Current sector | Weekly rows | Symbols | Mean raw-feature availability |", "|---|---:|---:|---:|"]
    for sector, group in panel.groupby("current_sector", dropna=False):
        rows.append(
            f"| {sector if pd.notna(sector) else 'missing'} | {len(group):,} | {group['symbol'].nunique()} | "
            f"{group[FEATURE_COLUMNS].notna().mean().mean():.1%} |"
        )
    rows += [
        "",
        "Current sector is a present-day availability diagnostic only. It is not historical sector exposure or industry neutralization.",
        "Market capitalization is not present in the prototype input and is therefore unavailable for this audit.",
        "",
        "## Label availability",
        "",
        "| Label | Present | Missing |",
        "|---|---:|---:|",
    ]
    for horizon in (1, 5, 20):
        column = f"forward_return_{horizon}d"
        rows.append(f"| {column} | {panel[column].notna().sum():,} | {panel[column].isna().sum():,} |")
    return "\n".join(rows) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--snapshot", default="data/metadata/universe_2026-09-11.csv")
    parser.add_argument("--raw-dir", default="data/raw/yfinance_universe/2026-09-11")
    args = parser.parse_args()
    metadata = pd.read_csv(args.root / args.snapshot)
    bars = load_daily_bars(args.root / args.raw_dir, metadata)
    features = add_liquidity(add_volatility(add_reversal(add_momentum(bars))))
    assert_feature_table_excludes_labels(features)
    labelled = add_forward_return_labels(features)
    weekly = select_weekly_research_dates(labelled)
    weekly["research_date"] = weekly["date"]
    weekly = weekly.merge(metadata[["symbol", "current_sector"]], on="symbol", how="left", validate="many_to_one")
    weekly["signal_time"] = market_close_utc(weekly["research_date"])
    weekly["available_at"] = weekly["signal_time"]
    weekly["execution_time"] = market_close_utc(weekly["execution_date"])
    weekly = add_relative_return_labels(weekly)
    validate_weekly_panel_keys(weekly)
    assert_panel_timing(weekly.loc[weekly["execution_time"].notna()])
    columns = [
        "research_date", "security_id", "symbol", "current_sector", "signal_time", "available_at", "execution_date",
        "execution_time", "forward_return_1d", "forward_return_5d", "forward_return_20d", "relative_return_1d",
        "relative_return_5d", "relative_return_20d", *FEATURE_COLUMNS,
    ]
    weekly = weekly[columns].sort_values(["research_date", "security_id"])
    output = args.root / "data/processed" / f"milestone3_weekly_panel_{date.today().isoformat()}.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    weekly.to_csv(output, index=False)
    (args.root / "reports/milestone3_factor_data_audit.md").write_text(factor_audit_markdown(weekly))
    print(output)


if __name__ == "__main__":
    main()
