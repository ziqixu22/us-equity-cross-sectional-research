"""Audit SEC Company Facts and submissions metadata before panel construction."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

import requests


ISSUERS = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "KO": "0000021344",
    "JNJ": "0000200406",
    "XOM": "0000034088",
    "JPM": "0000019617",
    "WMT": "0000104169",
    "NVDA": "0001045810",
}
HEADERS = {"User-Agent": "US Equity Cross-Sectional Research Lab ziqixu22"}


def get_json(url: str) -> dict[str, object]:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()


def recent_filing_summary(submissions: dict[str, object]) -> dict[str, object]:
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    accepted = recent.get("acceptanceDateTime", [])
    filed = recent.get("filingDate", [])
    amended = [form for form in forms if form.endswith("/A")]
    return {
        "recent_submission_fields": sorted(recent.keys()),
        "recent_filing_count": len(forms),
        "recent_amended_filing_count": len(amended),
        "acceptance_timestamp_present": bool(accepted),
        "filing_date_present": bool(filed),
        "accession_numbers_present": bool(accessions),
    }


def company_facts_summary(companyfacts: dict[str, object]) -> dict[str, object]:
    facts = companyfacts.get("facts", {})
    us_gaap = facts.get("us-gaap", {})
    observations = []
    amended_forms = 0
    for concept, payload in us_gaap.items():
        for unit, facts_in_unit in payload.get("units", {}).items():
            for fact in facts_in_unit:
                observations.append((concept, unit, fact.get("accn"), fact.get("form"), fact.get("end"), fact.get("filed")))
                amended_forms += int(str(fact.get("form", "")).endswith("/A"))
    duplicate_keys = len(observations) - len(set(observations))
    return {
        "top_level_fields": sorted(companyfacts.keys()),
        "taxonomy_namespaces": sorted(facts.keys()),
        "us_gaap_concept_count": len(us_gaap),
        "fact_observation_count": len(observations),
        "exact_duplicate_fact_records": duplicate_keys,
        "amended_form_fact_count": amended_forms,
        "companyfacts_has_accepted_timestamp": "acceptedTimestamp" in json.dumps(companyfacts),
        "companyfacts_fact_fields_sample": sorted(
            next(iter(next(iter(us_gaap.values())).get("units", {}).values()), [{}])[0].keys()
        ) if us_gaap else [],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    cache_dir = args.root / "data/raw/sec_provider_audit" / date.today().isoformat()
    cache_dir.mkdir(parents=True, exist_ok=True)
    audit: dict[str, object] = {
        "provider": "SEC EDGAR",
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "issuers": {},
        "failures": {},
    }
    for symbol, cik in ISSUERS.items():
        try:
            submissions = get_json(f"https://data.sec.gov/submissions/CIK{cik}.json")
            companyfacts = get_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json")
            (cache_dir / f"{symbol}_submissions.json").write_text(json.dumps(submissions))
            (cache_dir / f"{symbol}_companyfacts.json").write_text(json.dumps(companyfacts))
            audit["issuers"][symbol] = {
                "cik": cik,
                "submissions": recent_filing_summary(submissions),
                "companyfacts": company_facts_summary(companyfacts),
            }
        except Exception as exc:  # preserve failed requests for the data-quality report
            audit["failures"][symbol] = f"{type(exc).__name__}: {exc}"
    output = args.root / "data/manifests" / f"sec_fundamentals_audit_{date.today().isoformat()}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
