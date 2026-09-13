"""Small, auditable standard-US-GAAP Company Facts adapter."""
from __future__ import annotations

import pandas as pd

CONCEPT_REGISTRY = {
    "revenue": ("us-gaap", ("RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "Revenues"), "USD", "duration"),
    "net_income": ("us-gaap", ("NetIncomeLoss",), "USD", "duration"),
    "assets": ("us-gaap", ("Assets",), "USD", "instant"),
    "liabilities": ("us-gaap", ("Liabilities",), "USD", "instant"),
    "stockholders_equity": ("us-gaap", ("StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"), "USD", "instant"),
    "operating_income": ("us-gaap", ("OperatingIncomeLoss",), "USD", "duration"),
    "gross_profit": ("us-gaap", ("GrossProfit",), "USD", "duration"),
    "cash": ("us-gaap", ("CashAndCashEquivalentsAtCarryingValue",), "USD", "instant"),
    "shares_outstanding": ("dei", ("EntityCommonStockSharesOutstanding",), "shares", "instant"),
    "capex": ("us-gaap", ("PaymentsToAcquirePropertyPlantAndEquipment",), "USD", "duration"),
}


def normalize_company_facts(security_id: str, cik: str, companyfacts: dict, submissions: dict) -> pd.DataFrame:
    """Map only registered standard concepts and retain accession/timing provenance."""
    recent = submissions.get("filings", {}).get("recent", {})
    filing_meta = pd.DataFrame({
        "accession_number": recent.get("accessionNumber", []), "filed_date": recent.get("filingDate", []),
        "acceptance_datetime": recent.get("acceptanceDateTime", []), "submission_form": recent.get("form", []),
    })
    rows = []
    for variable, (taxonomy, concepts, unit, kind) in CONCEPT_REGISTRY.items():
        namespace = companyfacts.get("facts", {}).get(taxonomy, {})
        selected = next((concept for concept in concepts if concept in namespace), None)
        if not selected or unit not in namespace[selected].get("units", {}):
            continue
        for fact in namespace[selected]["units"][unit]:
            row = {"security_id": security_id, "cik": cik, "variable": variable, "taxonomy": taxonomy,
                   "concept": selected, "unit": unit, "kind": kind, "value": fact.get("val"),
                   "fiscal_period_end": fact.get("end"), "fiscal_period_start": fact.get("start"),
                   "fiscal_year": fact.get("fy"), "fiscal_period": fact.get("fp"), "form": fact.get("form"),
                   "accession_number": fact.get("accn"), "filed_date": fact.get("filed"), "mapping_confidence": "standard_us_gaap"}
            rows.append(row)
    facts = pd.DataFrame(rows)
    if facts.empty:
        return facts
    facts = facts.merge(filing_meta, on="accession_number", how="left", suffixes=("", "_submission"))
    facts["acceptance_datetime"] = pd.to_datetime(facts["acceptance_datetime"], utc=True, errors="coerce")
    facts["filed_date"] = pd.to_datetime(facts["filed_date"], utc=True, errors="coerce")
    facts["available_at"] = facts["acceptance_datetime"].fillna(facts["filed_date"] + pd.Timedelta(days=1))
    facts["is_amendment"] = facts["form"].fillna("").str.endswith("/A")
    return facts


def select_as_filed(facts: pd.DataFrame, signal_time: pd.Timestamp) -> pd.DataFrame:
    """Latest public filing by variable, fiscal period, unit, and security as of signal time."""
    eligible = facts.loc[facts.available_at.le(signal_time)].copy()
    keys = ["security_id", "variable", "fiscal_period_end", "unit"]
    return eligible.sort_values([*keys, "available_at", "accession_number"]).groupby(keys, as_index=False).tail(1)


def derive_quarter_from_ytd(current_ytd: float, prior_ytd: float) -> float:
    return current_ytd - prior_ytd


def ttm_from_quarters(values: list[float], units: list[str]) -> float:
    if len(values) != 4 or len(set(units)) != 1 or any(pd.isna(values)):
        raise ValueError("TTM requires four valid comparable quarters in one unit")
    return sum(values)


def standalone_quarter(value: float, prior_ytd: float | None, fiscal_period: str) -> float:
    """Convert compatible YTD values; Q1 is already standalone and FY requires 9M prior."""
    if fiscal_period == "Q1":
        return value
    if fiscal_period in {"Q2", "Q3", "FY"} and prior_ytd is not None:
        return value - prior_ytd
    raise ValueError("standalone quarter requires compatible prior cumulative duration")
