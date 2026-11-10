"""Build the weekly SEC panel and its derived fundamental factors from cached inputs."""
from __future__ import annotations

import json

import pandas as pd

from build_research_panel import read_price_history, select_weekly_research_dates
from us_equity_cross_sectional.features.fundamental import (
    compute_fundamental_factors,
    summarize_factor_coverage,
)
from us_equity_cross_sectional.fundamentals.asof_panel import build_weekly_fundamental_panel
from us_equity_cross_sectional.fundamentals.sec_facts import normalize_company_facts
from us_equity_cross_sectional.research.run_paths import PANEL_PATH, RUN_ROOT, SNAPSHOT, SYMBOLS


def main() -> None:
    sec_dir = RUN_ROOT / "data/raw/sec_provider_audit" / SNAPSHOT
    yahoo_dir = RUN_ROOT / "data/raw/yfinance_provider_audit" / SNAPSHOT
    manifest = json.loads((RUN_ROOT / f"data/manifests/yfinance_provider_audit_{SNAPSHOT}.json").read_text())
    downloaded_at = pd.Timestamp(manifest["downloaded_at"])
    basis = downloaded_at.tz_convert("UTC")
    facts, signals, splits = [], [], []
    for symbol in SYMBOLS:
        companyfacts = json.loads((sec_dir / f"{symbol}_companyfacts.json").read_text())
        submissions = json.loads((sec_dir / f"{symbol}_submissions.json").read_text())
        issuer = normalize_company_facts(symbol, str(companyfacts["cik"]), companyfacts, submissions)
        if issuer.empty:
            raise ValueError(f"SEC response contains no usable facts for {symbol}")
        # The frozen prototype has one publicly traded common class per issuer.
        issuer["multiple_share_class_flag"] = False
        facts.append(issuer)

        bars = read_price_history(yahoo_dir / f"{symbol}.csv")
        weekly = select_weekly_research_dates(
            bars.loc[bars["date"].ge("2010-01-01") & bars["date"].lt(SNAPSHOT)]
        )
        weekly["research_date"] = weekly["date"]
        weekly["security_id"] = symbol
        # Use the earliest scheduled regular-session close, including half days.
        # On full sessions this intentionally defers filings accepted after 13:00 ET.
        weekly["signal_time"] = (
            (weekly["date"] + pd.Timedelta(hours=13)).dt.tz_localize("America/New_York").dt.tz_convert("UTC")
        )
        weekly["price"] = weekly["Close"]
        weekly["split_history_complete"] = True
        signals.append(weekly[["research_date", "security_id", "signal_time", "price", "split_history_complete"]])

        events = bars.loc[bars["Stock Splits"].fillna(0).ne(0), ["Date", "Stock Splits"]].copy()
        events["security_id"] = symbol
        events["split_date"] = pd.to_datetime(events["Date"], utc=True)
        events["split_ratio"] = events["Stock Splits"]
        splits.append(events[["security_id", "split_date", "split_ratio"]])

    panel = build_weekly_fundamental_panel(
        pd.concat(signals, ignore_index=True), pd.concat(facts, ignore_index=True),
        pd.concat(splits, ignore_index=True), price_basis_as_of=basis,
        market_data_download_timestamp=manifest["downloaded_at"],
    )
    factors = compute_fundamental_factors(panel)
    processed = PANEL_PATH.parent
    processed.mkdir(parents=True, exist_ok=True)
    panel.to_csv(processed / f"asof_fundamental_panel_{SNAPSHOT}.csv", index=False)
    factors.to_csv(processed / f"fundamental_factors_{SNAPSHOT}.csv", index=False)
    reports = RUN_ROOT / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    summarize_factor_coverage(factors).to_csv(reports / "fundamental_factor_coverage.csv", index=False)
    print(f"Built {len(panel):,} point-in-time issuer-weeks and eight fundamental factors")


if __name__ == "__main__":
    main()
