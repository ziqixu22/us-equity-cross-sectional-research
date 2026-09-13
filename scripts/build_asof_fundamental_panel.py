"""Build the cached eight-issuer weekly SEC as-of raw-input panel."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
from us_equity_cross_sectional.fundamentals.asof_panel import build_weekly_fundamental_panel
from us_equity_cross_sectional.fundamentals.sec_facts import normalize_company_facts

SYMBOLS=("AAPL","MSFT","KO","JNJ","XOM","JPM","WMT","NVDA")
SNAPSHOT="2026-09-11"

def audit(panel: pd.DataFrame) -> str:
    lines=["# Weekly As-of Fundamental Panel Audit","",f"Snapshot: {SNAPSHOT}; no ratios, IC, returns, models, or portfolios.","", "## Coverage","",f"- Rows: {len(panel):,}; issuers: {panel.security_id.nunique()}; weekly dates: {panel.research_date.nunique()}.",f"- Date range: {panel.research_date.min().date()} to {panel.research_date.max().date()}.","", "| Year | Rows | Issuers |","|---:|---:|---:|"]
    for year,g in panel.groupby(panel.research_date.dt.year): lines.append(f"| {year} | {len(g):,} | {g.security_id.nunique()} |")
    lines += ["", "## Variable availability", "", "| Variable | Present | Missing |", "|---|---:|---:|"]
    columns=["revenue_ttm","net_income_ttm","operating_income_ttm","gross_profit_ttm","capex_ttm","assets","liabilities","stockholders_equity","cash","shares_raw","market_cap"]
    for c in columns: lines.append(f"| {c} | {panel[c].notna().sum():,} | {panel[c].isna().sum():,} |")
    lines += ["", "## Timing and eligibility", "",f"- Market-cap eligible: {panel.market_cap_eligible.mean():.1%} ({panel.market_cap_eligible.sum():,}/{len(panel):,}).",f"- Exact share acceptance: {(panel.shares_acceptance_source == 'acceptance_datetime').mean():.1%}; filing-date-plus-one-day fallback: {(panel.shares_acceptance_source == 'filing_date_plus_one_day').mean():.1%}.",f"- Multiple-share-class exclusions: {(panel.market_cap_limitation_flag.fillna('').str.contains('multiple_share_class')).sum():,}.",f"- Financial-sector gaps: this eight-issuer audit set includes JPM only; financial-sector coverage is not representative.","", "## Staleness", "", f"- Shares age days (eligible nonmissing): median {panel.shares_age_days.median():.1f}, p95 {panel.shares_age_days.quantile(.95):.1f}, max {panel.shares_age_days.max():.1f}.", f"- Latest fundamental availability age: median {panel.fundamental_age_days.median():.1f}, p95 {panel.fundamental_age_days.quantile(.95):.1f}.", "", "## Limitations", "", "- Unresolved mappings remain missing; no silent quarter fill is used.", "- The sample has no unresolved multiple-share-class issuer, but the gate remains mandatory for expansion.", "- `price_basis_as_of`, `split_history_cutoff`, and `market_data_download_timestamp` are preserved on every row. Future split factors reconcile provider units only and are not predictive inputs."]
    return "\n".join(lines)+"\n"

def main() -> None:
    root=Path(__file__).resolve().parents[1]; sec=root/f"data/raw/sec_provider_audit/{SNAPSHOT}"; yahoo=root/f"data/raw/yfinance_provider_audit/{SNAPSHOT}"; manifest=json.loads((root/f"data/manifests/yfinance_provider_audit_{SNAPSHOT}.json").read_text())
    facts=[]; signals=[]; splits=[]
    for symbol in SYMBOLS:
        cf=json.loads((sec/f"{symbol}_companyfacts.json").read_text()); sub=json.loads((sec/f"{symbol}_submissions.json").read_text()); f=normalize_company_facts(symbol,str(cf["cik"]),cf,sub); f["multiple_share_class_flag"]=False; facts.append(f)
        bars=pd.read_csv(yahoo/f"{symbol}.csv"); date=pd.to_datetime(bars["Date"],utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None); bars["research_date"]=date; bars=bars.loc[bars.research_date.ge(pd.Timestamp("2010-01-01"))].copy(); date=bars.research_date; weekly=bars.loc[date.isin(pd.Series(date.drop_duplicates()).groupby(pd.Series(date.drop_duplicates()).dt.to_period("W-FRI")).max())].copy(); weekly["security_id"]=symbol; weekly["signal_time"]=(pd.to_datetime(weekly.research_date).dt.tz_localize("America/New_York")+pd.Timedelta(hours=16)).dt.tz_convert("UTC"); weekly["price"]=weekly["Close"]; weekly["split_history_complete"]=True; signals.append(weekly[["research_date","security_id","signal_time","price","split_history_complete"]])
        event=bars.loc[bars["Stock Splits"].fillna(0).ne(0),["Stock Splits"]].copy(); event["security_id"]=symbol; event["split_date"]=pd.to_datetime(bars.loc[event.index,"Date"],utc=True); event["split_ratio"]=event["Stock Splits"]; splits.append(event[["security_id","split_date","split_ratio"]])
    panel=build_weekly_fundamental_panel(pd.concat(signals,ignore_index=True),pd.concat(facts,ignore_index=True),pd.concat(splits,ignore_index=True),price_basis_as_of=pd.Timestamp(SNAPSHOT,tz="UTC"),split_history_cutoff=pd.Timestamp(SNAPSHOT,tz="UTC"),market_data_download_timestamp=manifest["downloaded_at"])
    panel.to_csv(root/f"data/processed/asof_fundamental_panel_{SNAPSHOT}.csv",index=False); (root/"reports/asof_fundamental_panel_audit.md").write_text(audit(panel))

if __name__ == "__main__": main()
