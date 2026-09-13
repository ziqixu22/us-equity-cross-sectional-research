"""Point-in-time fundamental factors built only from the weekly as-of fundamental panel.

Every input here is a column already produced by
``us_equity_cross_sectional.fundamentals.asof_panel.build_weekly_fundamental_panel``.
That panel selects each accounting fact with ``available_at <= signal_time``,
so any ratio built purely from its columns inherits the same point-in-time
(PIT) discipline without this module re-deriving or re-checking availability
itself. The one exception is the "prior-year comparable" lookup used by
``roa``, ``gross_profitability``, and ``asset_growth``: it reuses another
row of the *same* panel for the same security at an earlier ``research_date``
-- never a later one -- so it cannot introduce future information either.

This module does not run Rank IC, quantile analysis, models, portfolios, or
backtests, and does not winsorize, z-score, or neutralize. It also never
imputes a missing accounting value or fabricates a prior-year comparable:
if the required inputs are not both present, the factor is missing.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: Trading calendars do not land a weekly research date exactly 365 days
#: apart every year (52 vs. 53-week years), so the prior-year match is the
#: nearest same-security observation to ``research_date - 365 days`` within
#: this many days. It is a calendar-alignment tolerance only, not a
#: methodology choice about how "prior year" is defined.
PRIOR_YEAR_TOLERANCE_DAYS = 10

VALUE_FACTORS = ("book_to_market", "earnings_yield", "sales_to_price")
QUALITY_FACTORS = ("roa", "gross_profitability", "operating_margin", "leverage")
INVESTMENT_FACTORS = ("asset_growth",)
ALL_FACTORS = VALUE_FACTORS + QUALITY_FACTORS + INVESTMENT_FACTORS

#: Formula, required panel columns, and market-cap dependency for every
#: factor. Used by this module's tests and by the factor audit report; it is
#: not consulted for research decisions -- see reports/fundamental_factor_decision_table.md.
FACTOR_METADATA = {
    "book_to_market": {
        "formula": "stockholders_equity / market_cap",
        "category": "value",
        "required_columns": ("stockholders_equity", "market_cap", "market_cap_eligible"),
        "market_cap_dependent": True,
    },
    "earnings_yield": {
        "formula": "net_income_ttm / market_cap",
        "category": "value",
        "required_columns": ("net_income_ttm", "market_cap", "market_cap_eligible"),
        "market_cap_dependent": True,
    },
    "sales_to_price": {
        "formula": "revenue_ttm / market_cap",
        "category": "value",
        "required_columns": ("revenue_ttm", "market_cap", "market_cap_eligible"),
        "market_cap_dependent": True,
    },
    "roa": {
        "formula": "net_income_ttm / average_assets, average_assets = (assets + assets_prior_year_comparable) / 2",
        "category": "quality",
        "required_columns": ("net_income_ttm", "assets", "research_date", "security_id"),
        "market_cap_dependent": False,
    },
    "gross_profitability": {
        "formula": "gross_profit_ttm / average_assets, average_assets = (assets + assets_prior_year_comparable) / 2",
        "category": "quality",
        "required_columns": ("gross_profit_ttm", "assets", "research_date", "security_id"),
        "market_cap_dependent": False,
    },
    "operating_margin": {
        "formula": "operating_income_ttm / revenue_ttm",
        "category": "quality",
        "required_columns": ("operating_income_ttm", "revenue_ttm"),
        "market_cap_dependent": False,
    },
    "leverage": {
        "formula": "liabilities / assets",
        "category": "quality",
        "required_columns": ("liabilities", "assets"),
        "market_cap_dependent": False,
    },
    "asset_growth": {
        "formula": "assets / assets_prior_year_comparable - 1",
        "category": "investment",
        "required_columns": ("assets", "research_date", "security_id"),
        "market_cap_dependent": False,
    },
}

REQUIRED_PANEL_COLUMNS = {
    "research_date", "security_id", "market_cap", "market_cap_eligible",
    "stockholders_equity", "net_income_ttm", "revenue_ttm", "assets",
    "liabilities", "gross_profit_ttm", "operating_income_ttm",
}


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Divide two series, rejecting non-finite operands and zero denominators.

    A zero, NaN, or infinite numerator or denominator yields a missing
    result rather than zero, inf, or -inf. Sign is otherwise preserved
    exactly: a negative numerator (e.g. a net loss) produces a negative
    ratio, not a rejected one.
    """
    numerator = pd.to_numeric(numerator, errors="coerce").astype("float64")
    denominator = pd.to_numeric(denominator, errors="coerce").astype("float64")
    invalid = ~np.isfinite(numerator) | ~np.isfinite(denominator) | denominator.eq(0)
    with np.errstate(divide="ignore", invalid="ignore"):
        result = numerator / denominator
    result = result.mask(invalid)
    return result.replace([np.inf, -np.inf], np.nan)


def _prior_year_value(
    panel: pd.DataFrame, value_column: str, tolerance_days: int = PRIOR_YEAR_TOLERANCE_DAYS
) -> pd.Series:
    """For each row, the same security's ``value_column`` nearest to 365 days earlier.

    Only rows with a strictly earlier ``research_date`` are eligible, so no
    future observation can ever be selected as a "prior-year comparable" --
    this holds regardless of how the input rows happen to be ordered.
    Matching is date-based (nearest to the 365-day mark, within
    ``tolerance_days``), not a fixed row-count lookback, so an irregular
    weekly cadence (a data gap, or a 53-week calendar year) cannot silently
    misalign the comparison. No prior value is fabricated: a security with
    no match inside the tolerance window gets a missing prior value, never
    a substitute from a different-length lookback.
    """
    working = panel[["security_id", "research_date"]].copy()
    working["_row_id"] = panel.index
    working["_target_date"] = working["research_date"] - pd.Timedelta(days=365)

    source = panel[["security_id", "research_date", value_column]].dropna(subset=["research_date"])
    source = source.sort_values("research_date").rename(
        columns={"research_date": "_match_date", value_column: "_prior_value"}
    )

    # ``pd.merge_asof`` requires the "on" column to be sorted for the *whole*
    # frame even when ``by`` is also given -- sorting by (security_id, date)
    # only leaves each security's block internally sorted, but the overall
    # ``_target_date``/``_match_date`` column still jumps backwards wherever
    # ``security_id`` changes, which pandas rejects ("left keys must be
    # sorted") on any panel with more than one security whose date ranges
    # interleave. This was invisible in this module's original small,
    # single/two-security synthetic test fixtures (where the compound sort
    # happened to also be globally date-monotonic) and only surfaced when
    # run against the real multi-security panel. Sorting by the date column
    # alone (not compounded with security_id first) is what ``merge_asof``
    # actually requires; ``by="security_id"`` below still restricts each
    # match to the same security.
    working = working.sort_values("_target_date")
    merged = pd.merge_asof(
        working,
        source,
        left_on="_target_date",
        right_on="_match_date",
        by="security_id",
        direction="nearest",
        tolerance=pd.Timedelta(days=tolerance_days),
    )
    # Belt-and-suspenders causal guard: the match must be strictly before the
    # current row's own research_date. With a 10-day tolerance around a
    # 365-day target this can never trigger in practice, but the rule is
    # enforced explicitly rather than relied upon implicitly.
    is_future_or_same = merged["_match_date"] >= merged["research_date"]
    merged.loc[is_future_or_same, "_prior_value"] = np.nan

    merged = merged.set_index("_row_id").reindex(panel.index)
    return merged["_prior_value"]


def _average_with_prior(panel: pd.DataFrame, column: str, prior: pd.Series) -> pd.Series:
    """Average of a current value and its prior-year comparable; missing if either is."""
    current = pd.to_numeric(panel[column], errors="coerce")
    prior = pd.to_numeric(prior, errors="coerce")
    average = (current + prior) / 2
    return average.mask(current.isna() | prior.isna())


def compute_fundamental_factors(
    panel: pd.DataFrame, *, prior_year_tolerance_days: int = PRIOR_YEAR_TOLERANCE_DAYS
) -> pd.DataFrame:
    """Build the eight point-in-time fundamental factors from a weekly as-of panel.

    ``panel`` must be the output (or a superset of the columns) of
    ``build_weekly_fundamental_panel``. Returns one row per input row, keyed
    by ``(research_date, security_id)``, with one column per factor plus
    ``average_assets`` and ``assets_prior_year_comparable`` for auditability.
    """
    missing = REQUIRED_PANEL_COLUMNS.difference(panel.columns)
    if missing:
        raise ValueError(f"panel missing required columns: {sorted(missing)}")

    panel = panel.copy()
    panel["research_date"] = pd.to_datetime(panel["research_date"])

    market_cap_eligible = panel["market_cap_eligible"].fillna(False).astype(bool)
    eligible_market_cap = panel["market_cap"].where(market_cap_eligible)

    prior_assets = _prior_year_value(panel, "assets", prior_year_tolerance_days)
    average_assets = _average_with_prior(panel, "assets", prior_assets)

    out = panel[["research_date", "security_id"]].copy()

    # VALUE -- all three are missing whenever market_cap_eligible is False,
    # because eligible_market_cap is already NaN in that case.
    out["book_to_market"] = _safe_ratio(panel["stockholders_equity"], eligible_market_cap)
    out["earnings_yield"] = _safe_ratio(panel["net_income_ttm"], eligible_market_cap)
    out["sales_to_price"] = _safe_ratio(panel["revenue_ttm"], eligible_market_cap)

    # QUALITY
    out["roa"] = _safe_ratio(panel["net_income_ttm"], average_assets)
    out["gross_profitability"] = _safe_ratio(panel["gross_profit_ttm"], average_assets)
    out["operating_margin"] = _safe_ratio(panel["operating_income_ttm"], panel["revenue_ttm"])
    out["leverage"] = _safe_ratio(panel["liabilities"], panel["assets"])

    # INVESTMENT -- assets/assets_prior - 1, written as (assets - prior)/prior
    # so the same zero-denominator / non-finite handling in _safe_ratio applies.
    out["asset_growth"] = _safe_ratio(panel["assets"] - prior_assets, prior_assets)

    # Retained for auditability, not treated as factors themselves.
    out["assets_prior_year_comparable"] = prior_assets
    out["average_assets"] = average_assets

    return out


def summarize_factor_coverage(factors: pd.DataFrame, factor_names: tuple[str, ...] = ALL_FACTORS) -> pd.DataFrame:
    """Count/coverage/missing-fraction summary for each factor column present.

    Intended for both this module's tests and reports/fundamental_factor_audit.md;
    it makes no claim about a specific panel unless it is actually run against one.
    """
    rows = []
    total = len(factors)
    for name in factor_names:
        if name not in factors.columns:
            continue
        valid = factors[name].notna().sum()
        rows.append({
            "factor": name,
            "total_observations": total,
            "valid_observations": int(valid),
            "coverage_pct": (valid / total * 100) if total else float("nan"),
            "missing_pct": ((total - valid) / total * 100) if total else float("nan"),
        })
    return pd.DataFrame(rows)
