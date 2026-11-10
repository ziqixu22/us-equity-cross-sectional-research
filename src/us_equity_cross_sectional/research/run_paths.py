"""Paths for a fresh run, with historical script defaults for existing callers."""
import os
from pathlib import Path

RUN_ROOT = Path(os.environ.get("EQUITY_RUN_DIR", Path(__file__).resolve().parents[3]))
SNAPSHOT = os.environ.get("EQUITY_SNAPSHOT", "2026-09-11")
PANEL_PATH = RUN_ROOT / "data/processed" / f"research_panel_{SNAPSHOT}.csv"
SYMBOLS = ("AAPL", "MSFT", "KO", "JNJ", "XOM", "JPM", "WMT", "NVDA")
