"""Availability-time controls shared by fundamentals and future research panels."""

from __future__ import annotations

import pandas as pd


LABEL_COLUMNS = {"forward_return", "relative_return", "label_end", "label_available_at"}


def assert_feature_table_excludes_labels(features: pd.DataFrame) -> None:
    """Keep future outcomes out of the feature table before model construction."""
    leaked = LABEL_COLUMNS.intersection(features.columns)
    if leaked:
        raise ValueError(f"feature table contains future label columns: {sorted(leaked)}")


def assert_panel_timing(panel: pd.DataFrame) -> None:
    """Enforce feature availability before signal formation and next-session execution."""
    required = {"available_at", "signal_time", "execution_time"}
    missing = required.difference(panel.columns)
    if missing:
        raise ValueError(f"missing timing columns: {sorted(missing)}")
    if (panel["available_at"] > panel["signal_time"]).any():
        raise ValueError("feature available_at must not be after signal_time")
    if (panel["signal_time"] >= panel["execution_time"]).any():
        raise ValueError("execution_time must be strictly after signal_time")


def assert_fundamentals_as_filed(facts: pd.DataFrame) -> None:
    """Reject a fundamental value that was not public at its signal time."""
    required = {"accession_number", "available_at", "signal_time"}
    missing = required.difference(facts.columns)
    if missing:
        raise ValueError(f"missing fundamental columns: {sorted(missing)}")
    if (facts["available_at"] > facts["signal_time"]).any():
        raise ValueError("as-filed fact is not publicly available by signal_time")


def select_latest_as_filed(facts: pd.DataFrame, signal_time: pd.Timestamp) -> pd.DataFrame:
    """Select the newest filing version public by ``signal_time`` per reported fact."""
    required = {
        "security_id",
        "concept",
        "fiscal_period_end",
        "unit",
        "accession_number",
        "available_at",
    }
    missing = required.difference(facts.columns)
    if missing:
        raise ValueError(f"missing fundamental columns: {sorted(missing)}")
    eligible = facts.loc[facts["available_at"] <= signal_time].copy()
    if eligible.empty:
        return eligible
    keys = ["security_id", "concept", "fiscal_period_end", "unit"]
    return (
        eligible.sort_values([*keys, "available_at", "accession_number"])
        .groupby(keys, as_index=False, sort=False)
        .tail(1)
        .reset_index(drop=True)
    )
