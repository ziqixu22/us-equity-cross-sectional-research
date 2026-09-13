"""Summarize price/volume basis consistency around audited Yahoo split events."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from us_equity_cross_sectional.features.liquidity import add_split_consistent_volume

CASES = [("AAPL", "2020-08-31", "4:1"), ("NVDA", "2024-06-10", "10:1"), ("TSLA", "2020-08-31", "5:1"), ("WMT", "2024-02-26", "3:1")]


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    base = root / "data/raw/yfinance_provider_audit/2026-09-11"
    report = ["# Liquidity / Split Consistency Audit", "", "Yahoo `Close` is back-adjusted for splits in the audited histories, while `Volume` does not show the corresponding mechanical pre-split multiplier. Raw `Close × Volume` therefore understates historical dollar volume before a later split.", ""]
    for symbol, event_date, ratio in CASES:
        raw = pd.read_csv(base / f"{symbol}.csv")
        raw = raw.rename(columns={raw.columns[0]: "observed_at", "Close": "close", "Adj Close": "adjusted_close", "Volume": "volume", "Stock Splits": "stock_splits"})
        raw["date"] = pd.to_datetime(raw["observed_at"], utc=True).dt.tz_convert("America/New_York").dt.normalize().dt.tz_localize(None)
        raw["symbol"] = symbol
        audited = add_split_consistent_volume(raw)
        index = audited.index[audited["date"].eq(pd.Timestamp(event_date))][0]
        window = audited.loc[index - 2:index + 2]
        report += [f"## {symbol} — {ratio} on {event_date}", "", "| Date | Close | Adj Close | Volume | Split | Close×Volume | Split-consistent Close×Volume |", "|---|---:|---:|---:|---:|---:|---:|"]
        for row in window.itertuples():
            report.append(f"| {row.date.date()} | {row.close:.3f} | {row.adjusted_close:.3f} | {row.volume:,.0f} | {row.stock_splits:.1f} | {row.close * row.volume:,.0f} | {row.split_consistent_dollar_volume:,.0f} |")
        report.append("")
    report += ["## Policy", "", "`split_consistent_volume[t] = reported_volume[t] × product(split ratios strictly after t)`. The split event date itself is on the new share basis and is not multiplied by that event’s ratio. ADV uses `Close × split_consistent_volume`; Amihud uses adjusted-return magnitude over that denominator and excludes split dates. This is a provider-basis repair, not proof of exchange-quality consolidated dollar volume; ADV and Amihud remain prototype-quality under Yahoo data.", ""]
    (root / "reports/liquidity_split_consistency_audit.md").write_text("\n".join(report))


if __name__ == "__main__":
    main()
