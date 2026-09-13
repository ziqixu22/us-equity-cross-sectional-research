"""Chronological expanding-window out-of-sample evaluation for signal-combination models.

No random shuffling anywhere in this module: every split is defined by a
cutoff date, train is everything strictly before it, test is a block of
weeks after it. This matches the point-in-time discipline used throughout
this project -- a model must never see a future observation during
training, and a model's hyperparameters/preprocessing statistics
(imputation medians, standardization mean/std) are fit on train data only
and then applied unchanged to test data.

Same small-cross-section caveat as ``factor_evaluation.py``: this is
evaluated on an 8-security universe. Out-of-sample R^2 and Rank IC at this
scale are noisy; folds are reported individually, not just pooled, so
instability across folds is visible rather than averaged away.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import r2_score

from us_equity_cross_sectional.models.signal_models import (
    apply_preprocessing, build_model, fit_preprocessing,
)


def chronological_expanding_folds(
    dates: pd.Series, n_folds: int = 6, min_train_fraction: float = 0.4
) -> list[tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]]:
    """Return (train_end, test_start, test_end) cutoffs for expanding-window folds.

    The first ``min_train_fraction`` of unique dates form the initial
    training block; the remaining dates are split into ``n_folds`` equal
    blocks, each used once as a test set while all dates strictly before
    it (initial train block plus every earlier test block) are train.
    This is an expanding window: fold k's train set is a strict superset
    of fold k-1's.
    """
    unique_dates = np.sort(dates.unique())
    n = len(unique_dates)
    start_idx = int(n * min_train_fraction)
    remaining = unique_dates[start_idx:]
    if len(remaining) < n_folds:
        n_folds = max(1, len(remaining) // 10) or 1
    blocks = np.array_split(remaining, n_folds)
    folds = []
    for block in blocks:
        if len(block) == 0:
            continue
        train_end = block[0]  # train is strictly before this
        test_start, test_end = block[0], block[-1]
        folds.append((pd.Timestamp(train_end), pd.Timestamp(test_start), pd.Timestamp(test_end)))
    return folds


def _daily_rank_ic(frame: pd.DataFrame, pred_col: str, label_col: str, date_col: str) -> pd.DataFrame:
    rows = []
    for date, group in frame.groupby(date_col):
        sub = group[[pred_col, label_col]].dropna()
        if len(sub) < 3 or sub[pred_col].nunique() < 2 or sub[label_col].nunique() < 2:
            continue
        ic, _ = stats.spearmanr(sub[pred_col], sub[label_col])
        if not np.isnan(ic):
            rows.append({date_col: date, "rank_ic": ic})
    return pd.DataFrame(rows)


def evaluate_model_chronologically(
    panel: pd.DataFrame, feature_columns: list[str], label_column: str, model_name: str,
    date_column: str = "research_date", n_folds: int = 6, min_train_fraction: float = 0.4,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit ``model_name`` on an expanding window; return (fold_metrics, oos_predictions).

    ``fold_metrics`` has one row per fold: n_train, n_test, out-of-sample
    R^2, mean Rank IC, ICIR, prediction coverage, and top-minus-bottom
    predicted-decile spread of the actual label. ``oos_predictions`` has
    one row per out-of-sample observation (date, security, prediction,
    actual label) across all folds, for downstream portfolio construction.
    """
    frame = panel[[date_column, "security_id", label_column, *feature_columns]].copy()
    frame = frame.dropna(subset=[label_column])
    folds = chronological_expanding_folds(frame[date_column], n_folds=n_folds, min_train_fraction=min_train_fraction)

    fold_rows = []
    pred_rows = []
    for fold_i, (train_end, test_start, test_end) in enumerate(folds):
        train = frame.loc[frame[date_column] < train_end]
        test = frame.loc[frame[date_column].between(test_start, test_end)]
        if len(train) < 30 or test.empty:
            continue
        train_X, train_y = train[feature_columns], train[label_column].to_numpy()
        test_X = test[feature_columns]

        imputer, scaler = fit_preprocessing(train_X)
        train_X_t = apply_preprocessing(train_X, imputer, scaler)
        test_X_t = apply_preprocessing(test_X, imputer, scaler)

        model = build_model(model_name)
        model.fit(train_X_t, train_y)
        preds = model.predict(test_X_t)

        result = test[[date_column, "security_id", label_column]].copy()
        result["prediction"] = preds
        result["fold"] = fold_i
        pred_rows.append(result)

        ic_frame = _daily_rank_ic(result, "prediction", label_column, date_column)
        mean_ic = ic_frame["rank_ic"].mean() if not ic_frame.empty else np.nan
        std_ic = ic_frame["rank_ic"].std(ddof=1) if len(ic_frame) > 1 else np.nan
        icir = mean_ic / std_ic if pd.notna(std_ic) and std_ic > 0 else np.nan

        r2 = r2_score(result[label_column], result["prediction"]) if len(result) > 1 else np.nan

        spread_rows = []
        for date, group in result.groupby(date_column):
            if len(group) < 4:
                continue
            ranked = group.sort_values("prediction")
            k = max(1, len(ranked) // 3)  # top/bottom tercile, appropriate for n=8
            top = ranked.tail(k)[label_column].mean()
            bottom = ranked.head(k)[label_column].mean()
            spread_rows.append(top - bottom)
        mean_spread = float(np.mean(spread_rows)) if spread_rows else np.nan

        fold_rows.append({
            "fold": fold_i, "train_end": train_end, "test_start": test_start, "test_end": test_end,
            "n_train": len(train), "n_test": len(test), "oos_r2": r2,
            "mean_ic": mean_ic, "icir": icir, "n_ic_dates": len(ic_frame),
            "coverage_pct": float(result["prediction"].notna().mean() * 100),
            "top_bottom_tercile_spread": mean_spread,
        })

    fold_metrics = pd.DataFrame(fold_rows)
    oos_predictions = pd.concat(pred_rows, ignore_index=True) if pred_rows else pd.DataFrame()
    return fold_metrics, oos_predictions


def pooled_summary(fold_metrics: pd.DataFrame) -> dict[str, float]:
    """Simple across-fold summary (mean of fold metrics, not re-pooled predictions)."""
    if fold_metrics.empty:
        return {"n_folds": 0}
    return {
        "n_folds": int(len(fold_metrics)),
        "mean_oos_r2": float(fold_metrics["oos_r2"].mean()),
        "mean_ic": float(fold_metrics["mean_ic"].mean()),
        "mean_icir": float(fold_metrics["icir"].mean()),
        "mean_coverage_pct": float(fold_metrics["coverage_pct"].mean()),
        "mean_top_bottom_spread": float(fold_metrics["top_bottom_tercile_spread"].mean()),
    }


def prediction_turnover(oos_predictions: pd.DataFrame, date_column: str = "research_date", top_frac: float = 1 / 3) -> float:
    """Fraction of the top-tercile-by-prediction set that changes week over week."""
    if oos_predictions.empty:
        return float("nan")
    wide = oos_predictions.pivot_table(index=date_column, columns="security_id", values="prediction")
    wide = wide.sort_index()
    changes = []
    prev_top = None
    for _, row in wide.iterrows():
        row = row.dropna()
        if len(row) < 3:
            continue
        k = max(1, int(len(row) * top_frac))
        top = set(row.sort_values(ascending=False).head(k).index)
        if prev_top is not None:
            changed = len(top.symmetric_difference(prev_top)) / (2 * k)
            changes.append(changed)
        prev_top = top
    return float(np.mean(changes)) if changes else float("nan")
