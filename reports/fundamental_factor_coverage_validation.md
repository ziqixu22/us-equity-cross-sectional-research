# Fundamental Factor Coverage Validation (Milestone 4C)

Snapshot: 2026-09-13, run against the real 8-issuer/6,968-row weekly as-of
panel (`data/processed/asof_fundamental_panel_2026-09-11_fixed.csv`, built
from the already-cached raw SEC/Yahoo data in `data/raw/`, using the panel
builder's own methodology unchanged apart from the two bug fixes documented
below). No Rank IC, future-return correlation, quantile returns, ML models,
portfolio construction, or backtests are computed anywhere in this report.

## Task 1 — Root cause of the coverage discrepancy

**The discrepancy was real, and it was caused by an actual correctness bug
in `build_weekly_fundamental_panel()`, not by stale documentation, a
fallback concept, or a scope difference.**

`current = _asof(facts, signal_time)` selects the latest as-of-eligible
fact per `(security_id, variable, fiscal_period_end, unit)` across **all**
securities present in the `facts` table passed in. The per-signal selection
that followed it, however, filtered only by `variable` —

```python
ttm = _ttm(current.loc[current.variable.eq(variable)])                 # flow variables
selected = current.loc[current.variable.eq(variable)]...                # stock variables
```

— never by the signal's own `security_id`. In a single-security build (the
shape used by this module's existing unit tests) this is invisible, because
there is nothing else in `current` to leak from. In the real 8-issuer
combined build, it means: whenever a security has **zero** facts for a
given variable (as KO and WMT genuinely have zero `Liabilities` facts, and
XOM and JPM have zero `OperatingIncomeLoss`/`GrossProfit` facts, confirmed
directly against the raw cached `*_companyfacts.json`), that security's
row silently inherited **another issuer's** most-recently-available value
for that variable instead of correctly reporting it missing.

Reproduced directly: building a two-issuer panel of AAPL + KO, KO's
`liabilities` column came back populated with AAPL's own liabilities value
and `liabilities_cik` literally set to Apple's CIK (`320193`) on every KO
row, even though KO has no `Liabilities` concept in its SEC filings at all.
This explains exactly why the previous `reports/asof_fundamental_panel_audit.md`
reported 0 missing rows for `liabilities`, `operating_income_ttm`, and
`gross_profit_ttm` across the full panel — those "present" values were
frequently a leaked value from a *different* security, not a legitimate
mapped observation for that row's own issuer.

None of the six investigated possibilities you listed was the actual cause:
mapping is not scoped to "mapped issuers only," no fallback concept
substitution is involved, the two audits' issuer/date scope is identical,
the missingness metric (`.notna().sum()`) is computed correctly, and the
text in `docs/sec_concept_mapping.md` is *not* stale — it was independently
re-verified against the raw `companyfacts.json` for every flagged issuer in
this task and found accurate (see table below). The bug is specifically a
missing `security_id` filter in `build_weekly_fundamental_panel()`.

### Independent verification against raw SEC data

| Concept | Confirmed missing for | Matches `docs/sec_concept_mapping.md`? |
|---|---|---|
| `Liabilities` | KO, WMT | Partial — the doc only names KO; **WMT was an undocumented second gap**, found by reading the raw `companyfacts.json` directly. |
| `OperatingIncomeLoss` | XOM, JPM | Yes, exact match. |
| `GrossProfit` | XOM, JPM, WMT | Yes, exact match. |
| `Revenue*` (any of the 3 candidates) | none of the 8 | Yes — doc says present in all 8; confirmed. |
| `Assets` | none of the 8 | Yes — doc says present in all 8; confirmed. |
| `StockholdersEquity` / `...IncludingPortionAttributableToNoncontrollingInterest` | none of the 8 (at least one candidate always present) | Yes — doc says present in all 8; confirmed. |

### Fix applied

`build_weekly_fundamental_panel()` now restricts `current` to the signal's
own `security_id` immediately after the as-of selection:

```python
current = _asof(facts, pd.to_datetime(signal.signal_time, utc=True))
current = current.loc[current.security_id.eq(signal.security_id)]
```

Verified by direct reproduction (KO's `liabilities` is now correctly `NaN`
in the same AAPL+KO combined build) and by a systematic equivalence check:
building a combined 4-issuer panel and 4 single-issuer panels and comparing
every column numerically found zero differences after the fix (a naive
string-based comparison used earlier in this investigation produced false
"mismatches" that were purely `int` vs `float`/`NaN` vs `None` formatting
artifacts, not real value differences — resolved by comparing numerically).
A new regression test, `test_variable_missing_for_one_security_is_not_leaked_from_another`
in `tests/test_asof_fundamental_panel.py`, builds two securities together
where one has zero facts for a variable and asserts it stays missing.

### A second, distinct data-quality finding surfaced by this investigation (not a bug, not fixed)

`stockholders_equity` was also named in your Task 1 list. Its real
per-issuer missingness is 0% for 7 of 8 issuers but **81.3% for JNJ**
(708 of JNJ's 871 rows — which is, not coincidentally, exactly the
panel-wide `stockholders_equity` missing count). Root cause:
`normalize_company_facts()`'s concept selection —
```python
selected = next((concept for concept in concepts if concept in namespace), None)
```
— picks the **first** candidate concept that exists anywhere in a
company's filing history and uses **only** that one, for the company's
entire history. It does not fall back to a second candidate to fill
periods the first one doesn't cover. JNJ evidently tags `StockholdersEquity`
directly for only a recent, small slice of its filing history (its raw
`companyfacts.json` has just 20 facts under that concept) and tags
`StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest`
for the rest — but because `StockholdersEquity` is found at all, the other,
more complete candidate is never consulted. This is a real, explainable,
and likely-fixable coverage gap, but it is a **different bug** from the
cross-security leak above (it produces a legitimately-scoped missing value,
not a wrong one), it is more invasive to fix correctly (merging two
candidate concepts by fiscal period without double-counting or preferring
a less-authoritative tag), and it is outside this task's stated bottleneck
of resolving the leak/discrepancy and computing real coverage. It is left
**unfixed**, flagged explicitly here and in the two updated reports, and
recommended as a follow-up engineering task. Its effect: `book_to_market`'s
real coverage figure below (88.6%) is understated relative to what a
proper multi-candidate-concept fallback would likely achieve (~98.8%,
bounded only by market-cap eligibility) — this is a coverage-completeness
limitation, not a correctness defect, since no wrong value is produced.

## Task 2 — Prior-year comparable match audit

Run against the real 6,968-row panel's `assets` column via
`_prior_year_value()` (used by `roa`, `gross_profitability`, and
`asset_growth`).

| Metric | Value |
|---|---:|
| Total rows | 6,968 |
| Rows with current `assets` present (eligible) | 6,968 (100%) |
| Matched prior-year rows | 6,560 |
| Unmatched rows | 408 |
| Match rate | 94.14% |
| Match rate, per issuer | identical 94.14% (820/871) for all 8 issuers |
| Day-difference (target date vs. matched date), abs: min | 0 days |
| Day-difference, abs: median | 1 day |
| Day-difference, abs: p90 | 1 day |
| Day-difference, abs: max | 8 days |
| Future `research_date` ever selected | **0** — never |
| Multiple candidates within the ±10-day window | Expected and harmless (see below) |
| Stability around year-end / holidays | Stable — see below |

**Unmatched rows are exactly, and only, each security's earliest ~51 weeks
of history** (408 = 51 weeks × 8 issuers, all falling in calendar year
2010) — the structurally-expected consequence of there being no
observation ~365 days before a security's very first signal. This is
correct PIT behavior, not a defect: no prior value is available yet, so
none is fabricated.

**Day-difference distribution:** tight and well inside tolerance (median 1
day, max 8 days, using a ±10-day window). The nonzero values come from
ordinary weekday drift — a Friday-anchored weekly research date one
calendar year earlier does not always land on the exact same weekday
(52 vs. 53-week spans), so the nearest actual observation is typically 0–1
trading weeks off, never close to the 10-day boundary.

**Multiple candidates within tolerance:** essentially every consecutive
pair of weekly observations for every security is ≤20 days apart (i.e.,
more than one observation can fall inside a given ±10-day window around a
target date). This is expected given weekly research-date density and is
**not** an ambiguity bug: `direction="nearest"` in `pd.merge_asof` always
resolves to a single, deterministic closest candidate by construction, and
the explicit causal guard (`_match_date >= research_date`) further
guarantees the candidate is never a future observation regardless of how
many candidates exist nearby. No case of an ambiguous or non-deterministic
match was found.

**Year-end/holiday stability:** of the 1,168 rows whose target date
(`research_date - 365 days`) falls in December or January, 1,104 matched
(94.5%, consistent with the overall 94.14% rate — the gap is explained
entirely by the same early-2010 unmatched rows, not by any year-end-specific
effect), with the same tight day-difference distribution (median 1 day,
max 8 days). No evidence of misalignment around year-end or holiday
calendars.

**Conclusion: no bug found in the prior-year matching logic itself.** The
±10-day tolerance rule is not changed, per your instruction. (A separate,
unrelated bug — `pd.merge_asof` requiring its "on" column sorted for the
*whole* frame even when `by` is used — was found and fixed; see "Bugs
found and fixed" below. It made the function crash on realistic
multi-security data; it did not affect which matches were selected once
fixed, since the fix only changes the sort order fed to `merge_asof`, not
the matching criteria.)

## Task 3 — Real factor coverage

Computed by running `compute_fundamental_factors()` (after the merge_asof
sort fix below) against the real, leak-fixed 6,968-row panel — not
theoretical upper bounds.

| Factor | Valid | Total | Coverage % | Missing % |
|---|---:|---:|---:|---:|
| book_to_market | 6,175 | 6,968 | 88.62% | 11.38% |
| earnings_yield | 4,444 | 6,968 | 63.78% | 36.22% |
| sales_to_price | 2,558 | 6,968 | 36.71% | 63.29% |
| roa | 4,425 | 6,968 | 63.50% | 36.50% |
| gross_profitability | 2,494 | 6,968 | 35.79% | 64.21% |
| operating_margin | 1,459 | 6,968 | 20.94% | 79.06% |
| leverage | 4,861 | 6,968 | 69.76% | 30.24% |
| asset_growth | 6,560 | 6,968 | 94.14% | 5.86% |

These coverage percentages are accurate counts of non-missing values. They
are **not**, by themselves, a statement that every non-missing value is
correct — see the critical finding below, which affects every factor built
from a TTM flow variable (`earnings_yield`, `sales_to_price`, `roa`,
`gross_profitability`, `operating_margin`).

### Critical finding: TTM flow-variable values contain silent corruption, independent of the leak bug

While investigating why `revenue_ttm` coverage was so low, inspecting the
underlying standalone-quarter reconstruction for AAPL's revenue surfaced
quarter values of **-26,295,000,000**, **-33,506,000,000**, and similar —
Apple has never reported negative quarterly revenue. Tracing one case
(fiscal period end 2019-03-30) to the raw facts showed the root cause:
SEC filers routinely tag the *same* concept (e.g.
`RevenueFromContractWithCustomerExcludingAssessedTax`) with **both** a
3-month standalone duration **and** a 6-month year-to-date cumulative
duration for the same `fiscal_period_end` and `fiscal_period` ("Q2") label
— they differ only in `fiscal_period_start`. `_asof()`'s grouping key,
`["security_id", "variable", "fiscal_period_end", "unit"]`, does not
include `fiscal_period_start`, so these two differently-scaled facts
collide into a single group and `.tail(1)` picks whichever happens to sort
last by `(available_at, accession_number)` — sometimes the 3-month value,
sometimes the 6-month YTD value, essentially arbitrarily. `standalone_quarter()`
then subtracts a prior-period value from whichever one was picked,
assuming it is always the YTD cumulative figure. When it isn't, the
result is nonsensical (near-zero or large-magnitude negative).

This is confirmed **systemic**, not an AAPL artifact: across all 8
issuers' raw facts, 22.5% of reconstructed standalone revenue quarters,
29.9% of net-income quarters, 24.8% of operating-income quarters, and
27.2% of gross-profit quarters are negative — implausibly high for
loss-making frequency at large, profitable blue-chip issuers over
2010–2026. (`capex` shows a much smaller 2.9% negative rate, consistent
with the same mechanism occurring less often for that concept.)

Because TTM values are a *sum* of four such standalone quarters, a single
corrupted quarter does not always flip the sign of the resulting
`*_ttm` value — a large, correct positive quarter can still dominate a sum
that includes one garbage component. This is why the sign-check on the
final factor values understates the problem: of the *factor* values
themselves, only 1.6–1.7% of valid `earnings_yield`/`roa` observations and
0% of `sales_to_price`/`gross_profitability`/`operating_margin`
observations are visibly negative — but a TTM value built from a corrupted
component can be **silently wrong in magnitude** (off by tens of billions
of dollars) while still landing on the correct side of zero, with no
statistical signal to flag it. Coverage/missingness percentages cannot
detect this; only direct inspection of the standalone-quarter
reconstruction (done here) surfaces it.

**This bug is distinct from the cross-security leak (which is fixed) and
from the JNJ stockholders_equity concept-selection gap (which is
documented but not fixed).** It lives in `_asof()`'s fact-selection key
(missing `fiscal_period_start`/duration-length disambiguation) and in
`normalize_company_facts()`/`standalone_quarter()`'s implicit assumption
that a selected Q2/Q3/FY fact is always the YTD cumulative variant. Fixing
it correctly requires deciding, per concept, which duration variant is the
"YTD" one to feed to `standalone_quarter()` — a real methodology/design
decision, not a one-line fix, and explicitly out of scope for "the specific
bottleneck needed to generate the panel reproducibly" that this task
authorized optimizing. **It is left unfixed in this task, flagged here in
the strongest terms, and should be treated as a blocking data-quality issue
for any factor built from a TTM flow variable before Rank IC research.**
It does not affect `book_to_market` or `leverage` (both built from instant/
stock variables, which are selected directly with no duration-length
ambiguity — an instant fact has no "3-month vs. cumulative" variant), nor
`asset_growth` (uses `assets`, also an instant variable).

## Performance note (how the real panel was generated)

The known O(signals × facts) per-security cost (~0.11 s/row, unchanged
from the prior audit's estimate — the leak-bug fix did not materially
change this) still makes a naive single-process 8-issuer build take on the
order of ~13–20+ minutes. Per your instruction to inspect a smarter
rebuild before accepting that cost: `build_market_cap()` already filters
its own `shares`/`signals` inputs by `security_id` internally, and — once
the leak-bug fix above makes `build_weekly_fundamental_panel()` fully
security-scoped — running it **once per security on that security's own
signals/facts/splits alone** is mathematically identical to running it on
the full combined multi-security input (verified above by a zero-diff
numeric comparison across 4 issuers). This makes the 8 issuers'
computations fully independent, so they were run as 8 parallel OS processes
(`multiprocessing.Pool`) over the already-cached raw SEC/Yahoo data in
`data/raw/` (no network calls). On this sandbox's 2 physical cores this
still completed in **~6.3 minutes wall-clock** (vs. an estimated 13–20+
minutes serial) — real, not hypothetical, since per-symbol timings are
logged: AAPL 372s, MSFT 375s, KO 380s, JNJ 362s, XOM 297s, JPM 278s, WMT
344s, NVDA 371s CPU-time, overlapped across processes. No change was made
to the per-row accounting algorithm itself — this is orchestration only,
made safe specifically *by* the leak-bug fix (before that fix, per-security
parallel decomposition would have silently changed results, since a
security's row would no longer be able to "borrow" another security's
value once the two builds are run separately with disjoint input). The
underlying O(signals × facts) per-security cost itself remains
unoptimized and is still the right target for a future dedicated
performance pass; today's fix was scoped to "reproducibly generate the
panel" for this validation task, not to permanently solve the algorithmic
complexity.

## Bugs found and fixed in this task

1. **Cross-security data leakage** in `build_weekly_fundamental_panel()`
   (`src/us_equity_cross_sectional/fundamentals/asof_panel.py`) — see Task 1
   above. Fixed by filtering `current` to the signal's own `security_id`.
   Regression test added: `test_variable_missing_for_one_security_is_not_leaked_from_another`.
2. **`pd.merge_asof` sort-order crash** in `_prior_year_value()`
   (`src/us_equity_cross_sectional/features/fundamental.py`) — sorting the
   left frame by `(security_id, target_date)` is not globally
   date-monotonic once more than one security's date ranges interleave
   (as any real multi-issuer panel's do), and `merge_asof` requires the
   "on" column sorted for the whole frame even when `by` is supplied. This
   was invisible in the module's original tests (small, coincidentally
   date-monotonic fixtures) and only surfaced when run against the real
   panel, where it raised `ValueError: left keys must be sorted`. Fixed by
   sorting on the date column alone (still passing `by="security_id"` for
   per-security matching). Regression test added:
   `test_prior_year_match_across_interleaved_securities_does_not_crash`.

## Bugs found and NOT fixed in this task (documented limitations, follow-up required)

3. **Single-candidate concept selection with no fallback merge** in
   `normalize_company_facts()` (`src/us_equity_cross_sectional/fundamentals/sec_facts.py`)
   — causes JNJ's `stockholders_equity` to be 81.3% missing even though a
   second registered candidate concept covers most of the gap. Affects
   `book_to_market`'s real coverage figure (understated). See Task 1 above.
4. **Duration-variant collision in standalone-quarter reconstruction**
   (`_asof()`'s grouping key in `asof_panel.py`, combined with
   `standalone_quarter()`'s YTD assumption in `sec_facts.py`) — causes
   silently wrong (not just missing) TTM values for `revenue_ttm`,
   `net_income_ttm`, `operating_income_ttm`, and `gross_profit_ttm`. See
   the "Critical finding" above. This is the most consequential open issue
   in Milestone 4 and should be the top priority for the next engineering
   pass, ahead of any further coverage or performance work.

## Remaining limitations

- The real coverage figures in Task 3 are accurate counts, but for the
  five TTM-flow-dependent factors they should not be read as a proxy for
  correctness — bug 4 above means a "valid" value can still be wrong.
- Bug 3 (JNJ stockholders_equity) means `book_to_market`'s and `leverage`'s
  reported coverage is a conservative floor, not a ceiling — fixing it
  would likely raise real coverage without changing any already-correct
  value.
- The prior-year join's ~94% match rate and clean day-difference profile
  (Task 2) apply to the `assets` column specifically; they were not
  separately re-verified for every column `_prior_year_value()` could in
  principle be called on (only `assets` is used by any of the 8 factors
  today), though the mechanism is column-agnostic.
- The underlying O(signals × facts) per-row cost is unchanged; parallel
  per-security orchestration reduced wall-clock time for this one
  validation run but did not reduce total compute cost, and a routine
  re-run of this scale should not be assumed to be cheap.
