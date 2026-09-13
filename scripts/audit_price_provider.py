"""Audit yfinance daily-bar behavior for a small, diverse U.S.-equity sample."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

from us_equity_cross_sectional.data.validation import validate_daily_bars


SYMBOLS = ["AAPL", "MSFT", "KO", "JNJ", "XOM", "JPM", "WMT", "NVDA", "AMZN", "TSLA"]


def download_history(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Return the unmodified field set supplied by yfinance for one ticker."""
    return yf.Ticker(symbol).history(
        start=start, end=end, auto_adjust=False, actions=True, repair=False, keepna=True
    )


def normalize_for_validation(symbol: str, history: pd.DataFrame) -> pd.DataFrame:
    index_name = history.index.name or "Date"
    bars = history.reset_index().rename(columns={index_name: "date"})
    bars.columns = [str(column).lower().replace(" ", "_") for column in bars.columns]
    if "date" not in bars and "datetime" in bars:
        bars = bars.rename(columns={"datetime": "date"})
    bars["symbol"] = symbol
    return bars


def audit_history(symbol: str, history: pd.DataFrame) -> dict[str, object]:
    bars = normalize_for_validation(symbol, history)
    validate_daily_bars(bars)
    close_return = bars["close"].pct_change()
    suspicious = bars.loc[
        close_return.abs().gt(0.20) & bars.get("stock_splits", pd.Series(0, index=bars.index)).eq(0),
        ["date", "close"],
    ]
    split_rows = bars.loc[bars.get("stock_splits", pd.Series(0, index=bars.index)).ne(0)]
    dividend_rows = bars.loc[bars.get("dividends", pd.Series(0, index=bars.index)).ne(0)]
    adjusted = bars.get("adj_close")
    adjustment_ratio = adjusted / bars["close"] if adjusted is not None else pd.Series(dtype=float)
    return {
        "symbol": symbol,
        "rows": int(len(bars)),
        "first_date": str(bars["date"].iloc[0]),
        "last_date": str(bars["date"].iloc[-1]),
        "index_timezone": str(getattr(history.index, "tz", None)),
        "columns": list(history.columns.astype(str)),
        "duplicate_symbol_dates": int(bars.duplicated(["symbol", "date"]).sum()),
        "split_events": [
            {"date": str(row.date), "ratio": float(row.stock_splits)}
            for row in split_rows[["date", "stock_splits"]].itertuples(index=False)
        ],
        "dividend_event_count": int(len(dividend_rows)),
        "adjustment_ratio_min": None if adjustment_ratio.empty else float(adjustment_ratio.min()),
        "adjustment_ratio_max": None if adjustment_ratio.empty else float(adjustment_ratio.max()),
        "suspicious_raw_close_jumps_over_20pct_without_split": [
            {"date": str(row.date), "close": float(row.close)}
            for row in suspicious.itertuples(index=False)
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="1990-01-01")
    parser.add_argument("--end", default=date.today().isoformat())
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    downloaded_at = datetime.now(timezone.utc).isoformat()
    cache_dir = args.root / "data/raw/yfinance_provider_audit" / date.today().isoformat()
    cache_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []
    failures: dict[str, str] = {}
    histories: dict[str, pd.DataFrame] = {}
    for symbol in SYMBOLS:
        try:
            history = download_history(symbol, args.start, args.end)
            if history.empty:
                raise ValueError("empty response")
            history.to_csv(cache_dir / f"{symbol}.csv")
            histories[symbol] = history
            results.append(audit_history(symbol, history))
        except Exception as exc:  # provider failures must be recorded, not dropped
            failures[symbol] = f"{type(exc).__name__}: {exc}"

    reference_sessions = set().union(*(set(frame.index.date) for frame in histories.values()))
    for result in results:
        symbol_dates = set(histories[result["symbol"]].index.date)
        result["missing_relative_to_union_sessions"] = len(reference_sessions - symbol_dates)

    manifest = {
        "provider": "yfinance",
        "provider_version": yf.__version__,
        "downloaded_at": downloaded_at,
        "request": {"start": args.start, "end": args.end, "auto_adjust": False, "actions": True},
        "symbols": SYMBOLS,
        "raw_cache": str(cache_dir.relative_to(args.root)),
        "successful_symbols": [result["symbol"] for result in results],
        "failures": failures,
        "audits": results,
    }
    output = args.root / "data/manifests" / f"yfinance_provider_audit_{date.today().isoformat()}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, default=str) + "\n")
    print(output)


if __name__ == "__main__":
    main()
