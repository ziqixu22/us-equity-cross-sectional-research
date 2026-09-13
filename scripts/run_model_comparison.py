"""Stage 2: chronological out-of-sample model comparison and ablations."""
from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from us_equity_cross_sectional.research.model_evaluation import (
    evaluate_model_chronologically, pooled_summary, prediction_turnover,
)

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "reports/figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

PRICE_FACTORS = [
    "momentum_12_1", "momentum_6_1", "momentum_3_1",
    "reversal_1d", "reversal_5d", "reversal_20d",
    "realized_vol_20d", "realized_vol_60d", "downside_vol_20d",
    "adv_20d", "amihud_20d",
]
FUNDAMENTAL_FACTORS = [
    "book_to_market", "earnings_yield", "sales_to_price",
    "roa", "gross_profitability", "operating_margin", "leverage", "asset_growth",
]
COMBINED_FACTORS = PRICE_FACTORS + FUNDAMENTAL_FACTORS
LABEL = "relative_return_5d"
MODELS = ["baseline", "ols", "ridge", "elastic_net", "lightgbm"]
FEATURE_GROUPS = {"price_only": PRICE_FACTORS, "fundamentals_only": FUNDAMENTAL_FACTORS, "combined": COMBINED_FACTORS}


def main() -> None:
    panel = pd.read_csv(ROOT / "data/processed/research_panel_2026-09-11.csv")
    panel["research_date"] = pd.to_datetime(panel["research_date"])

    all_rows = []
    all_preds = {}
    all_fold_details = []
    for group_name, feature_cols in FEATURE_GROUPS.items():
        for model_name in MODELS:
            fold_metrics, oos = evaluate_model_chronologically(
                panel, feature_cols, LABEL, model_name, n_folds=6, min_train_fraction=0.4
            )
            if fold_metrics.empty:
                continue
            summary = pooled_summary(fold_metrics)
            turnover = prediction_turnover(oos)
            row = {"feature_group": group_name, "model": model_name, "turnover": turnover, **summary}
            all_rows.append(row)
            all_preds[(group_name, model_name)] = oos
            fd = fold_metrics.copy()
            fd["feature_group"] = group_name
            fd["model"] = model_name
            all_fold_details.append(fd)
            print(group_name, model_name, "->", {k: round(v, 4) if isinstance(v, float) else v for k, v in row.items() if k not in ("feature_group", "model")})

    metrics = pd.DataFrame(all_rows)
    metrics.to_csv(ROOT / "reports/model_metrics.csv", index=False)
    fold_details = pd.concat(all_fold_details, ignore_index=True)
    fold_details.to_csv(ROOT / "reports/model_fold_details.csv", index=False)

    # Figure: mean OOS Rank IC by model x feature group
    pivot = metrics.pivot(index="model", columns="feature_group", values="mean_ic").reindex(MODELS)
    pivot = pivot[["price_only", "fundamentals_only", "combined"]]
    fig, ax = plt.subplots(figsize=(8, 5))
    pivot.plot(kind="bar", ax=ax)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("Mean OOS Rank IC (5D relative return)")
    ax.set_title("Out-of-sample Rank IC by model and feature group")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "model_ic_by_group.png", dpi=140)
    plt.close(fig)

    # Figure: OOS R^2 by model x feature group
    pivot_r2 = metrics.pivot(index="model", columns="feature_group", values="mean_oos_r2").reindex(MODELS)
    pivot_r2 = pivot_r2[["price_only", "fundamentals_only", "combined"]]
    fig, ax = plt.subplots(figsize=(8, 5))
    pivot_r2.plot(kind="bar", ax=ax)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("Mean OOS R^2")
    ax.set_title("Out-of-sample R^2 by model and feature group")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "model_r2_by_group.png", dpi=140)
    plt.close(fig)

    # Figure: fold-level IC stability for combined-feature models
    fig, ax = plt.subplots(figsize=(9, 5))
    for model_name in MODELS:
        fd = fold_details.loc[(fold_details.feature_group == "combined") & (fold_details.model == model_name)]
        if fd.empty:
            continue
        ax.plot(fd["fold"], fd["mean_ic"], marker="o", label=model_name)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Fold (expanding window, chronological)")
    ax.set_ylabel("Mean Rank IC")
    ax.set_title("Fold-level OOS Rank IC stability, combined features")
    ax.legend()
    plt.tight_layout()
    fig.savefig(FIG_DIR / "model_fold_ic_stability.png", dpi=140)
    plt.close(fig)

    print("\n=== pooled model comparison ===")
    print(metrics.round(4).to_string(index=False))

    # Save best-model OOS predictions for Stage 3 portfolio construction.
    best_row = metrics.sort_values("mean_ic", ascending=False).iloc[0]
    best_key = (best_row["feature_group"], best_row["model"])
    best_preds = all_preds[best_key]
    best_preds.to_csv(ROOT / "data/processed/best_model_oos_predictions.csv", index=False)
    print("\nbest by mean OOS IC:", best_key, "saved predictions to data/processed/best_model_oos_predictions.csv")


if __name__ == "__main__":
    main()
