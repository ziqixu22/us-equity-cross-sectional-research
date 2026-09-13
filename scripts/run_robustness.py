"""Stage 5: robustness checks and explicit failure/non-generalization analysis.

Reuses existing cached artifacts (research panel, Stage 1 factor_metrics.csv,
Stage 2 model evaluation code, Stage 3 OOS predictions) rather than rebuilding
anything from scratch, per the "do not rerun slow pipelines repeatedly"
operating rule. Only a small number of additional, cheap chronological model
refits are run here (different label horizons; a lower-frequency resample of
the existing weekly predictions), all still expanding-window / chronological.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from us_equity_cross_sectional.research.factor_evaluation import yearly_ic_stability
from us_equity_cross_sectional.research.model_evaluation import (
    evaluate_model_chronologically, pooled_summary,
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
STRONG_FACTORS = ["realized_vol_60d", "adv_20d", "realized_vol_20d", "downside_vol_20d", "momentum_12_1"]
WEAK_FACTORS = ["amihud_20d", "operating_margin", "book_to_market", "leverage", "roa"]


def main() -> None:
    panel = pd.read_csv(ROOT / "data/processed/research_panel_2026-09-11.csv")
    panel["research_date"] = pd.to_datetime(panel["research_date"])
    factor_metrics = pd.read_csv(ROOT / "reports/factor_metrics.csv")

    checks = {}

    # --- Check 1: horizon robustness for the strongest factors (reuse Stage 1 output) ---
    horizon_cols = ["factor", "ic_1d", "icir_1d", "ic_5d", "icir_5d", "ic_20d", "icir_20d"]
    checks["factor_horizon"] = factor_metrics[horizon_cols].copy()

    # --- Check 2: model horizon robustness (re-fit ridge/price_only on 1D/20D labels) ---
    horizon_rows = []
    for h, label in [("1d", "relative_return_1d"), ("5d", "relative_return_5d"), ("20d", "relative_return_20d")]:
        fold_metrics, _ = evaluate_model_chronologically(panel, PRICE_FACTORS, label, "ridge", n_folds=6, min_train_fraction=0.4)
        summary = pooled_summary(fold_metrics)
        horizon_rows.append({"horizon": h, **summary})
    checks["model_horizon"] = pd.DataFrame(horizon_rows)

    # --- Check 3: yearly stability of the strongest factors and weakest factors ---
    yearly_rows = []
    for factor in STRONG_FACTORS + WEAK_FACTORS:
        yearly = yearly_ic_stability(panel, factor, "relative_return_5d")
        for _, row in yearly.iterrows():
            yearly_rows.append({"factor": factor, "year": int(row["year"]), "mean_ic": row["mean"], "n_dates": int(row["count"])})
    checks["yearly_factor_stability"] = pd.DataFrame(yearly_rows)

    # --- Check 4: model stability over time (fold-level IC, price_only ridge, primary 5D) ---
    fold_metrics_5d, oos_5d = evaluate_model_chronologically(panel, PRICE_FACTORS, "relative_return_5d", "ridge", n_folds=6, min_train_fraction=0.4)
    checks["model_fold_stability"] = fold_metrics_5d[["fold", "test_start", "test_end", "n_test", "mean_ic", "oos_r2"]]

    # --- Check 5: rebalance-frequency robustness (subsample every 2nd research date) ---
    # Cheap check reusing the already-computed weekly OOS predictions rather than
    # re-running the pipeline on a differently-resampled panel.
    dates_sorted = sorted(oos_5d["research_date"].unique())
    biweekly_dates = set(dates_sorted[::2])
    oos_biweekly = oos_5d[oos_5d["research_date"].isin(biweekly_dates)]

    def _mean_ic(frame: pd.DataFrame) -> float:
        rows = []
        for _, g in frame.groupby("research_date"):
            sub = g[["prediction", "relative_return_5d"]].dropna()
            if len(sub) < 3 or sub["prediction"].nunique() < 2:
                continue
            ic, _ = stats.spearmanr(sub["prediction"], sub["relative_return_5d"])
            if not np.isnan(ic):
                rows.append(ic)
        return float(np.mean(rows)) if rows else np.nan

    checks["rebalance_frequency"] = pd.DataFrame([
        {"rebalance": "weekly (all dates)", "n_dates": oos_5d["research_date"].nunique(), "mean_ic": _mean_ic(oos_5d)},
        {"rebalance": "biweekly (every 2nd date)", "n_dates": len(biweekly_dates), "mean_ic": _mean_ic(oos_biweekly)},
    ])

    # --- Check 6: raw vs standardized factor IC (Spearman Rank IC is invariant to
    # any monotonic transform, including standardization -- verified numerically
    # rather than just asserted, since standardization here also involves
    # median-imputation of missing values which is NOT a pure monotonic transform
    # of the raw column and could in principle change ranks where imputation
    # occurs). ---
    raw_vs_std_rows = []
    for factor in STRONG_FACTORS:
        raw_ic = factor_metrics.loc[factor_metrics.factor == factor, "mean_ic"].iloc[0]
        col = panel[factor]
        imputed = col.fillna(col.median())
        standardized = (imputed - imputed.mean()) / imputed.std(ddof=0)
        tmp = panel[["research_date", "relative_return_5d"]].copy()
        tmp["std_factor"] = standardized
        ic_rows = []
        for _, g in tmp.groupby("research_date"):
            sub = g[["std_factor", "relative_return_5d"]].dropna()
            if len(sub) < 3 or sub["std_factor"].nunique() < 2:
                continue
            ic, _ = stats.spearmanr(sub["std_factor"], sub["relative_return_5d"])
            if not np.isnan(ic):
                ic_rows.append(ic)
        std_ic = float(np.mean(ic_rows)) if ic_rows else np.nan
        raw_vs_std_rows.append({"factor": factor, "raw_mean_ic": raw_ic, "standardized_imputed_mean_ic": std_ic})
    checks["raw_vs_standardized"] = pd.DataFrame(raw_vs_std_rows)

    # save all check tables
    for name, df in checks.items():
        df.to_csv(ROOT / f"reports/robustness_{name}.csv", index=False)
        print(f"\n=== {name} ===")
        print(df.round(4).to_string(index=False))

    # figure: factor IC across horizons for strongest/weakest factors
    fig, ax = plt.subplots(figsize=(9, 5))
    plot_factors = STRONG_FACTORS + ["amihud_20d"]
    fm = factor_metrics.set_index("factor")
    for f in plot_factors:
        if f in fm.index:
            ax.plot(["1d", "5d", "20d"], [fm.loc[f, "ic_1d"], fm.loc[f, "ic_5d"], fm.loc[f, "ic_20d"]], marker="o", label=f)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("Mean Rank IC")
    ax.set_title("Factor IC across horizons (robustness)")
    ax.legend(fontsize=8)
    plt.tight_layout()
    fig.savefig(FIG_DIR / "robustness_factor_horizon.png", dpi=140)
    plt.close(fig)

    # figure: yearly IC stability, strongest factor
    fig, ax = plt.subplots(figsize=(9, 4))
    yfs = checks["yearly_factor_stability"]
    for f in STRONG_FACTORS:
        sub = yfs[yfs.factor == f]
        ax.plot(sub["year"], sub["mean_ic"], marker="o", label=f)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Year-by-year mean Rank IC, strongest factors")
    ax.legend(fontsize=8)
    plt.tight_layout()
    fig.savefig(FIG_DIR / "robustness_yearly_stability.png", dpi=140)
    plt.close(fig)

    print("\nsaved reports/robustness_*.csv and 2 figures")


if __name__ == "__main__":
    main()
