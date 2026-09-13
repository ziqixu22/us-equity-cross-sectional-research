"""Point-in-time, split-basis-compatible prototype market-cap eligibility."""

from __future__ import annotations

import math

import pandas as pd


DEFAULT_STALENESS_LIMIT_DAYS = 130

_SIGNAL_COLUMNS = {
    "security_id", "signal_time", "signal_date", "price", "split_history_complete",
}
_SHARE_COLUMNS = {
    "security_id", "variable", "unit", "value", "fiscal_period_end", "available_at",
    "accession_number", "acceptance_datetime", "filed_date", "multiple_share_class_flag",
}
_SPLIT_COLUMNS = {"security_id", "split_date", "split_ratio"}


def _require_columns(frame: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = columns.difference(frame.columns)
    if missing:
        raise ValueError(f"{name} missing columns: {sorted(missing)}")


def _utc(value: object) -> pd.Timestamp:
    return pd.to_datetime(value, utc=True, errors="coerce")


def _empty_audit() -> dict[str, object]:
    return {
        "shares_raw": float("nan"),
        "shares_split_adjusted": float("nan"),
        "shares_instant_date": pd.NaT,
        "shares_available_at": pd.NaT,
        "shares_age_days": float("nan"),
        "shares_accession": None,
        "shares_acceptance_source": None,
        "split_adjustment_factor": float("nan"),
        "multiple_share_class_flag": pd.NA,
    }


def build_market_cap(
    signals: pd.DataFrame,
    shares: pd.DataFrame,
    split_events: pd.DataFrame,
    *,
    price_basis_as_of: pd.Timestamp,
    staleness_limit_days: int = DEFAULT_STALENESS_LIMIT_DAYS,
    split_history_cutoff: pd.Timestamp | None = None,
    market_data_download_timestamp: str | None = None,
) -> pd.DataFrame:
    """Attach as-filed, Yahoo-basis-compatible market cap and audit columns.

    ``price`` is Yahoo historical Close on its cached, split-adjusted basis.
    ``split_events`` must be the explicit corporate-action history used by that
    price cache; no split is inferred from a movement in prices or shares.
    ``split_history_complete`` is a security/date-specific assertion supplied
    by the price audit. False or missing rejects the observation.
    """
    _require_columns(signals, _SIGNAL_COLUMNS, "signals")
    _require_columns(shares, _SHARE_COLUMNS, "shares")
    _require_columns(split_events, _SPLIT_COLUMNS, "split_events")
    if staleness_limit_days < 0:
        raise ValueError("staleness_limit_days must be non-negative")
    basis_as_of = _utc(price_basis_as_of)
    if pd.isna(basis_as_of):
        raise ValueError("price_basis_as_of must be a valid timestamp")

    source = shares.loc[shares["variable"].eq("shares_outstanding")].copy()
    source["available_at"] = pd.to_datetime(source["available_at"], utc=True, errors="coerce")
    source["instant"] = pd.to_datetime(source["fiscal_period_end"], utc=True, errors="coerce")
    source["acceptance"] = pd.to_datetime(source["acceptance_datetime"], utc=True, errors="coerce")
    source["filed"] = pd.to_datetime(source["filed_date"], utc=True, errors="coerce")

    events = split_events.copy()
    events["split_date"] = pd.to_datetime(events["split_date"], utc=True, errors="coerce")
    events["split_ratio"] = pd.to_numeric(events["split_ratio"], errors="coerce")

    output = []
    for _, signal in signals.iterrows():
        row = signal.to_dict()
        audit = _empty_audit()
        limitations: list[str] = []
        signal_time = _utc(signal["signal_time"])
        price = pd.to_numeric(pd.Series([signal["price"]]), errors="coerce").iloc[0]
        candidates = source.loc[
            source["security_id"].eq(signal["security_id"])
            & source["available_at"].notna()
            & source["available_at"].le(signal_time)
        ].sort_values(["available_at", "instant", "accession_number"])

        if pd.isna(signal_time):
            limitations.append("invalid_signal_time")
        elif candidates.empty:
            has_security_facts = source["security_id"].eq(signal["security_id"]).any()
            limitations.append("shares_unavailable" if has_security_facts else "shares_missing")
        else:
            fact = candidates.iloc[-1]
            raw = pd.to_numeric(pd.Series([fact["value"]]), errors="coerce").iloc[0]
            instant = fact["instant"]
            acceptance_source = (
                "acceptance_datetime" if pd.notna(fact["acceptance"]) else "filing_date_plus_one_day"
            )
            audit.update({
                "shares_raw": raw,
                "shares_instant_date": instant,
                "shares_available_at": fact["available_at"],
                "shares_accession": fact["accession_number"],
                "shares_acceptance_source": acceptance_source,
                "multiple_share_class_flag": fact["multiple_share_class_flag"],
            })
            if pd.notna(signal_time) and pd.notna(instant):
                audit["shares_age_days"] = (signal_time - instant).total_seconds() / 86_400

            if fact["unit"] != "shares":
                limitations.append("unit_mismatch")
            if pd.isna(raw) or raw <= 0:
                limitations.append("nonpositive_shares")
            if pd.isna(instant) or instant > signal_time:
                limitations.append("invalid_share_instant")
            if pd.isna(fact["acceptance"]):
                expected_fallback = fact["filed"] + pd.Timedelta(days=1)
                if pd.isna(fact["filed"]) or fact["available_at"] != expected_fallback:
                    limitations.append("availability_unresolved")
            if (
                pd.isna(audit["shares_age_days"])
                or audit["shares_age_days"] > staleness_limit_days
            ):
                limitations.append("stale_shares")
            if pd.isna(fact["multiple_share_class_flag"]) or bool(fact["multiple_share_class_flag"]):
                limitations.append("multiple_share_class_unresolved")

            security_events = events.loc[events["security_id"].eq(signal["security_id"])]
            invalid_events = security_events.loc[
                security_events["split_date"].isna()
                | security_events["split_ratio"].isna()
                | security_events["split_ratio"].le(0)
            ]
            if (
                pd.isna(signal["split_history_complete"])
                or not bool(signal["split_history_complete"])
                or signal_time.normalize() > basis_as_of.normalize()
            ):
                limitations.append("split_basis_unresolved")
            elif not invalid_events.empty:
                limitations.append("split_basis_unresolved")
            elif pd.notna(instant):
                relevant = security_events.loc[
                    security_events["split_date"].gt(instant)
                    & security_events["split_date"].le(basis_as_of)
                ]
                factor = relevant["split_ratio"].prod() if not relevant.empty else 1.0
                audit["split_adjustment_factor"] = factor
                audit["shares_split_adjusted"] = raw * factor

        if pd.isna(price) or not math.isfinite(price) or price <= 0:
            limitations.append("invalid_price")
        eligible = not limitations
        row.update(audit)
        row["price_basis_as_of"] = basis_as_of
        row["split_history_cutoff"] = _utc(split_history_cutoff or basis_as_of)
        row["market_data_download_timestamp"] = market_data_download_timestamp
        row["market_cap_eligible"] = eligible
        row["market_cap_limitation_flag"] = None if eligible else ";".join(sorted(set(limitations)))
        row["market_cap"] = (
            price * audit["shares_split_adjusted"] if eligible else float("nan")
        )
        output.append(row)
    return pd.DataFrame(output)
