"""Weekly SEC as-of panel; raw accounting inputs only, never ratios."""
from __future__ import annotations

import json

import pandas as pd

from us_equity_cross_sectional.features.labels import validate_weekly_panel_keys
from us_equity_cross_sectional.fundamentals.market_cap import build_market_cap
from us_equity_cross_sectional.fundamentals.sec_facts import ttm_from_quarters

FLOW_VARIABLES = ("revenue", "net_income", "operating_income", "gross_profit", "capex")
STOCK_VARIABLES = ("assets", "liabilities", "stockholders_equity", "cash")


def _asof(facts: pd.DataFrame, signal_time: pd.Timestamp) -> pd.DataFrame:
    eligible = facts.loc[
        facts["available_at"].le(signal_time) & facts["fiscal_period_end"].le(signal_time)
    ]
    keys = ["variable", "unit", "concept", "fiscal_period_start", "fiscal_period_end"]
    return eligible.sort_values(["available_at", "accession_number"]).drop_duplicates(keys, keep="last")


def _ttm(flow: pd.DataFrame) -> dict[str, object]:
    """Use four adjacent quarters, keeping direct and cumulative facts distinct."""
    quarters = []
    for _, group in flow.dropna(subset=["fiscal_period_start", "value"]).groupby(
        ["concept", "unit", "fiscal_period_start"], sort=False
    ):
        prior = None
        for row in group.sort_values("fiscal_period_end").itertuples():
            start, end = row.fiscal_period_start, row.fiscal_period_end
            direct = 70 <= (end - start).days <= 110
            if direct:
                quarters.append((end, start, row.available_at, direct, row.value, (row.accession_number,), row))
            elif prior is not None and 70 <= (end - prior.fiscal_period_end).days <= 110:
                quarters.append((
                    end, prior.fiscal_period_end + pd.Timedelta(days=1),
                    max(row.available_at, prior.available_at), direct,
                    row.value - prior.value, (prior.accession_number, row.accession_number), row,
                ))
            prior = row

    # Prefer the newest reported version for a quarter; break ties in favor of
    # directly reported quarters, then use the configured concept order.
    quarters.sort(key=lambda q: (q[0], q[2], q[3], -q[6].concept_priority))
    latest_by_end = {q[0]: q for q in quarters}
    trailing = list(latest_by_end.values())[-4:]
    if len(trailing) < 4:
        return {}
    gaps = [(right[1] - left[0]).days for left, right in zip(trailing, trailing[1:])]
    if any(gap < 1 or gap > 7 for gap in gaps):
        return {}
    try:
        value = ttm_from_quarters([q[4] for q in trailing], [q[6].unit for q in trailing])
    except ValueError:
        return {}
    lineage = dict.fromkeys(accession for q in trailing for accession in q[5])
    return {
        "value": value, "available_at": max(q[2] for q in trailing),
        "component_accessions": json.dumps(list(lineage)), "row": trailing[-1][6],
    }


def _lineage(prefix: str, row: object, signal_time: pd.Timestamp) -> dict[str, object]:
    names={"accession_number":"accession","acceptance_datetime":"acceptance_datetime"}
    fields=("cik","concept","taxonomy","unit","form","accession_number","filed_date","acceptance_datetime","available_at","mapping_confidence")
    return {f"{prefix}_{names.get(field,field)}":getattr(row, field, None) for field in fields} | {f"{prefix}_age_days":(signal_time-pd.to_datetime(getattr(row,"available_at"),utc=True)).total_seconds()/86400}


def build_weekly_fundamental_panel(signals: pd.DataFrame, facts: pd.DataFrame, split_events: pd.DataFrame, *, price_basis_as_of: pd.Timestamp, market_data_download_timestamp: str, split_history_cutoff: pd.Timestamp | None = None, staleness_limit_days: int = 130) -> pd.DataFrame:
    """Select only facts public by each signal and retain per-variable lineage."""
    required={"research_date","security_id","signal_time","price","split_history_complete"}
    missing=required.difference(signals.columns)
    if missing: raise ValueError(f"signals missing columns: {sorted(missing)}")
    facts = facts.reset_index(drop=True)
    for column in ("available_at", "fiscal_period_start", "fiscal_period_end"):
        facts[column] = pd.to_datetime(facts[column], utc=True, format="mixed")
    if "multiple_share_class_flag" not in facts:
        facts["multiple_share_class_flag"] = pd.NA
    if "concept_priority" not in facts:
        facts["concept_priority"] = 0
    issuer_facts = dict(tuple(facts.groupby("security_id")))
    records = []
    trailing_cache = {}
    for _, signal in signals.iterrows():
        signal_time = pd.to_datetime(signal.signal_time, utc=True)
        current = _asof(issuer_facts.get(signal.security_id, facts.iloc[:0]), signal_time)
        out=signal.to_dict()
        for variable in FLOW_VARIABLES:
            flow = current.loc[current.variable.eq(variable)]
            cache_key = (signal.security_id, variable)
            cached = trailing_cache.get(cache_key)
            # Reuse the accounting result only while the exact as-of inputs match.
            # The availability age below is still recomputed for each signal.
            if cached is None or not flow.index.equals(cached[0]):
                cached = (flow.index, _ttm(flow))
                trailing_cache[cache_key] = cached
            ttm = cached[1]
            prefix=f"{variable}_ttm"; out[prefix]=ttm.get("value")
            out[f"{prefix}_component_accessions"]=ttm.get("component_accessions")
            if ttm:
                out.update(_lineage(prefix, ttm["row"], signal_time))
                out[f"{prefix}_available_at"] = ttm["available_at"]
                out[f"{prefix}_age_days"] = (signal_time - ttm["available_at"]).total_seconds() / 86400
        for variable in STOCK_VARIABLES:
            selected=current.loc[current.variable.eq(variable)].sort_values(["fiscal_period_end", "available_at", "concept_priority", "accession_number"], ascending=[True, True, False, True])
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
