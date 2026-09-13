"""Freeze a transparent current liquid-equity prototype universe from S&P 100 constituents."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

SOURCE_URL = "https://en.wikipedia.org/wiki/S%26P_100"
START_DATE = "2010-01-01"
MIN_PRICE = 5.0
MIN_ADV = 10_000_000.0
MIN_HISTORY_DAYS = 252


def fetch_symbols() -> pd.DataFrame:
    """Load the current constituent table and normalize Yahoo ticker punctuation."""
    response = requests.get(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    response.raise_for_status()
    tables = pd.read_html(StringIO(response.text))
    table = next(table for table in tables if "Symbol" in table.columns)
    result = table[["Symbol", "Name", "Sector"]].rename(
        columns={"Symbol": "symbol", "Name": "company", "Sector": "current_sector"}
    )
    result["symbol"] = result["symbol"].str.replace(".", "-", regex=False)
    return result.drop_duplicates("symbol").sort_values("symbol").reset_index(drop=True)


def history_for_symbol(symbol: str, start: str, end: str) -> pd.DataFrame:
    return yf.Ticker(symbol).history(
        start=start, end=end, auto_adjust=False, actions=True, repair=False, keepna=True
    )


def load_cached_history(path: Path) -> pd.DataFrame:
    """Restore a date index from the raw CSV cache without losing timezone information."""
    history = pd.read_csv(path, index_col=0, parse_dates=[0])
    history.index = pd.to_datetime(history.index, utc=True)
    return history


def summarize(symbol: str, history: pd.DataFrame) -> dict[str, object]:
    clean = history.dropna(subset=["Close", "Volume"])
    latest = clean.iloc[-1] if not clean.empty else None
    trailing = clean.tail(60)
    adv = float((trailing["Close"] * trailing["Volume"]).mean()) if len(trailing) == 60 else None
    last_close = float(latest["Close"]) if latest is not None else None
    return {
        "symbol": symbol,
        "last_observation_date": None if latest is None else str(latest.name),
        "last_close": last_close,
        "adv_60d": adv,
        "history_days": int(len(clean)),
        "eligible": bool(
            last_close is not None
            and last_close >= MIN_PRICE
            and adv is not None
            and adv >= MIN_ADV
            and len(clean) >= MIN_HISTORY_DAYS
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--end", default=date.today().isoformat())
    args = parser.parse_args()
    root = args.root
    downloaded_at = datetime.now(timezone.utc).isoformat()
    constituents = fetch_symbols()
    raw_dir = root / "data/raw/yfinance_universe" / date.today().isoformat()
    raw_dir.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, object]] = []
    failures: dict[str, str] = {}
    coverage: dict[int, int] = {}
    cached_symbols = 0
    for symbol in constituents["symbol"]:
        try:
            cache_path = raw_dir / f"{symbol}.csv"
            if cache_path.exists():
                history = load_cached_history(cache_path)
                cached_symbols += 1
            else:
                history = history_for_symbol(symbol, START_DATE, args.end)
            if history.empty:
                raise ValueError("empty response")
            if not cache_path.exists():
                history.to_csv(cache_path)
            summaries.append(summarize(symbol, history))
            for year in history.index.year.unique():
                coverage[int(year)] = coverage.get(int(year), 0) + 1
        except Exception as exc:
            failures[symbol] = f"{type(exc).__name__}: {exc}"

    snapshot = constituents.merge(pd.DataFrame(summaries), on="symbol", how="left")
    snapshot["source_url"] = SOURCE_URL
    snapshot["source_retrieved_at"] = downloaded_at
    snapshot["universe_bias"] = "current_constituents_only; not survivorship-bias-free"
    snapshot_path = root / "data/metadata" / f"universe_{date.today().isoformat()}.csv"
    snapshot.to_csv(snapshot_path, index=False)
    eligible = snapshot.loc[snapshot["eligible"].fillna(False)]
    liquidity = snapshot["adv_60d"].dropna()
    report = [
        "# Data Quality Report — Milestone 2",
        "",
        f"Generated: {downloaded_at}",
        "",
        "## Prototype universe",
        "",
        f"- Source: current S&P 100 constituent table ({SOURCE_URL}).",
        f"- Candidate securities: {len(snapshot)}; successful yfinance histories: {len(summaries)}; request failures: {len(failures)}.",
        f"- Eligible now: {len(eligible)} after close >= ${MIN_PRICE:.2f}, 60-day ADV >= ${MIN_ADV:,.0f}, and at least {MIN_HISTORY_DAYS} daily observations.",
        "- This is a frozen current-constituent prototype, not a historical membership or survivorship-bias-free universe.",
        "",
        "## Coverage through time",
        "",
        "| Year | Securities with any downloaded history |",
        "|---:|---:|",
        *[f"| {year} | {count} |" for year, count in sorted(coverage.items())],
        "",
        "## Liquidity and identifier diagnostics",
        "",
        f"- 60-day ADV (available candidates): min ${liquidity.min():,.0f}; median ${liquidity.median():,.0f}; max ${liquidity.max():,.0f}.",
        f"- Symbols converted from dot to dash for Yahoo compatibility: {', '.join(constituents.loc[constituents['symbol'].str.contains('-'), 'symbol']) or 'none'}.",
        f"- Failed symbols: {json.dumps(failures, sort_keys=True) if failures else 'none'}.",
        "- Raw bars are cached locally outside Git; the committed snapshot records only the selection and aggregate metadata.",
    ]
    (root / "reports/data_quality_report.md").write_text("\n".join(report) + "\n")
    manifest = {
        "provider": "yfinance",
        "provider_version": yf.__version__,
        "downloaded_at": downloaded_at,
        "source_url": SOURCE_URL,
        "start_date": START_DATE,
        "end_date": args.end,
        "filters": {"minimum_price": MIN_PRICE, "minimum_adv_60d": MIN_ADV, "minimum_history_days": MIN_HISTORY_DAYS},
        "raw_cache": str(raw_dir.relative_to(root)),
        "cached_symbols_reused": cached_symbols,
        "snapshot": str(snapshot_path.relative_to(root)),
        "failures": failures,
    }
    manifest_path = root / "data/manifests" / f"universe_build_{date.today().isoformat()}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(snapshot_path)
    print(root / "reports/data_quality_report.md")


if __name__ == "__main__":
    main()
