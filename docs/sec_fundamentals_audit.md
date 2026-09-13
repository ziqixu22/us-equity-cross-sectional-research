# SEC Fundamentals Audit — Company Facts and Submissions

**Audit date:** 2026-09-11. **Issuers:** AAPL, MSFT, KO, JNJ, XOM, JPM, WMT, NVDA. All eight Company Facts and submissions requests succeeded; raw JSON is cached locally outside Git.

## Observed metadata

Company Facts top-level payloads contain `cik`, `entityName`, and `facts`. Observed fact entries contained `accn`, `end`, `filed`, `form`, `fp`, `frame`, `fy`, and `val`; they did **not** contain an acceptance timestamp. In contrast, every sampled submissions payload exposed `accessionNumber`, `filingDate`, and `acceptanceDateTime`. This supports the approved design: link Company Facts to submissions by accession number and use submission acceptance time as `available_at`.

## Duplicates and amendments

The raw Company Facts sample has repeated exact fact records and amendment forms, so a simple fiscal-period-end join is invalid. Exact duplicate counts ranged from 2,013 (XOM) to 6,098 (JPM); Company Facts amendment-form observations ranged from 0 to 517 across this sample. Submission feeds also contained amended filings for every issuer sampled (16–131 recent amendments).

The as-filed selector therefore groups the same issuer, concept, fiscal period, and unit, then chooses the latest version whose `available_at` is no later than the signal time. It does not overwrite pre-amendment history with later values. If an accession cannot be joined to an acceptance timestamp, the fallback is conservative next-trading-session availability after `filingDate`.

## Limitations

This is a schema/timing audit, not a complete accounting mapper. Concept selection, taxonomy variation, units, duration/instant distinctions, SEC rate limits, issuer-CIK mapping, and amended-filing precedence will be tested before any value, quality, or investment factor is emitted. Re-run `scripts/audit_sec_fundamentals.py` to reproduce the audit.
