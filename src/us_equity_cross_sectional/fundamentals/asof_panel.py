"""Weekly SEC as-of panel; raw accounting inputs only, never ratios."""
from __future__ import annotations

import json
import pandas as pd

from us_equity_cross_sectional.features.labels import validate_weekly_panel_keys
from us_equity_cross_sectional.fundamentals.market_cap import build_market_cap

FLOW_VARIABLES = ("revenue", "net_income", "operating_income", "gross_profit", "capex")
STOCK_VARIABLES = ("assets", "liabilities", "stockholders_equity", "cash")


def _asof(facts: pd.DataFrame, signal_time: pd.Timestamp) -> pd.DataFrame:
    eligible = facts.loc[facts["available_at"].le(signal_time)].copy()
    if eligible.empty: return eligible
    keys = ["security_id", "variable", "fiscal_period_end", "unit"]
    return eligible.sort_values([*keys, "available_at", "accession_number"]).groupby(keys, as_index=False).tail(1)


def _quarterly(flow: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for _, group in flow.groupby(["security_id", "variable", "unit", "fiscal_year"], dropna=False):
        group=group.sort_values("fiscal_period_end"); by_fp={r.fiscal_period:r for r in group.itertuples()}
        for fp, prior in (("Q1",None),("Q2","Q1"),("Q3","Q2"),("FY","Q3")):
            row=by_fp.get(fp)
            if row is None or (prior and by_fp.get(prior) is None): continue
            value=row.value if prior is None else row.value-by_fp[prior].value
            rows.append({"security_id":row.security_id,"variable":row.variable,"unit":row.unit,"end":row.fiscal_period_end,"value":value,"available_at":row.available_at,"accessions":[row.accession_number] if prior is None else [by_fp[prior].accession_number,row.accession_number],"row":row})
    return pd.DataFrame(rows)


def _ttm(flow: pd.DataFrame) -> dict[str, object]:
    q=_quarterly(flow)
    if len(q)<4: return {}
    q=q.sort_values("end").tail(4)
    if len(q)!=4 or q.unit.nunique()!=1: return {}
    latest=q.iloc[-1]; lineage=list(dict.fromkeys(a for values in q.accessions for a in values))
    return {"value":q.value.sum(),"available_at":q.available_at.max(),"component_accessions":json.dumps(lineage),"row":latest.row}


def _lineage(prefix: str, row: object, signal_time: pd.Timestamp) -> dict[str, object]:
    names={"accession_number":"accession","acceptance_datetime":"acceptance_datetime"}
    fields=("cik","concept","taxonomy","unit","form","accession_number","filed_date","acceptance_datetime","available_at","mapping_confidence")
    return {f"{prefix}_{names.get(field,field)}":getattr(row, field, None) for field in fields} | {f"{prefix}_age_days":(signal_time-pd.to_datetime(getattr(row,"available_at"),utc=True)).total_seconds()/86400}


def build_weekly_fundamental_panel(signals: pd.DataFrame, facts: pd.DataFrame, split_events: pd.DataFrame, *, price_basis_as_of: pd.Timestamp, market_data_download_timestamp: str, split_history_cutoff: pd.Timestamp | None = None, staleness_limit_days: int = 130) -> pd.DataFrame:
    """Select only facts public by each signal and retain per-variable lineage."""
    required={"research_date","security_id","signal_time","price","split_history_complete"}
    missing=required.difference(signals.columns)
    if missing: raise ValueError(f"signals missing columns: {sorted(missing)}")
    facts=facts.copy(); facts["available_at"]=pd.to_datetime(facts["available_at"],utc=True); facts["fiscal_period_end"]=pd.to_datetime(facts["fiscal_period_end"],utc=True)
    if "multiple_share_class_flag" not in facts: facts["multiple_share_class_flag"]=pd.NA
    records=[]
    for _, signal in signals.iterrows():
        current=_asof(facts,pd.to_datetime(signal.signal_time,utc=True)); out=signal.to_dict()
        for variable in FLOW_VARIABLES:
            ttm=_ttm(current.loc[current.variable.eq(variable)])
            prefix=f"{variable}_ttm"; out[prefix]=ttm.get("value")
            out[f"{prefix}_component_accessions"]=ttm.get("component_accessions")
            if ttm: out.update(_lineage(prefix,ttm["row"],pd.to_datetime(signal.signal_time,utc=True)))
        for variable in STOCK_VARIABLES:
            selected=current.loc[current.variable.eq(variable)].sort_values(["available_at","fiscal_period_end","accession_number"])
            if selected.empty: out[variable]=None; continue
            fact=selected.iloc[-1]; out[variable]=fact.value; out.update(_lineage(variable,fact,pd.to_datetime(signal.signal_time,utc=True)))
            out[f"{variable}_instant_date"]=fact.fiscal_period_end
        share=current.loc[current.variable.eq("shares_outstanding")].copy()
        market_signal=signal.copy(); market_signal["signal_date"]=signal.research_date
        market=build_market_cap(pd.DataFrame([market_signal]),share,split_events,price_basis_as_of=price_basis_as_of,staleness_limit_days=staleness_limit_days,split_history_cutoff=split_history_cutoff,market_data_download_timestamp=market_data_download_timestamp).iloc[0].to_dict()
        for key,value in market.items():
            if key not in out or key.startswith(("shares_","split_","multiple_","market_cap","price_basis")): out[key]=value
        out["price_basis_as_of"]=pd.to_datetime(price_basis_as_of,utc=True)
        out["split_history_cutoff"]=pd.to_datetime(split_history_cutoff or price_basis_as_of,utc=True)
        out["market_data_download_timestamp"]=market_data_download_timestamp
        available=[v for k,v in out.items() if k.endswith("_available_at") and pd.notna(v)]
        out["latest_fundamental_available_at"]=max(available) if available else pd.NaT
        out["fundamental_age_days"]=(pd.to_datetime(signal.signal_time,utc=True)-out["latest_fundamental_available_at"]).total_seconds()/86400 if available else None
        records.append(out)
    panel=pd.DataFrame(records); validate_weekly_panel_keys(panel); return panel
