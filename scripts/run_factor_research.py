"""Stage 1: evaluate every price and fundamental factor on the real research panel."""
from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from us_equity_cross_sectional.research.factor_evaluation import (
    daily_rank_ic, evaluate_all_factors, quantile_returns, yearly_ic_stability,
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
ALL_FACTORS = PRICE_FACTORS + FUNDAMENTAL_FACTORS
PRIMARY_LABEL = "relative_return_5d"


def main() -> None:
    panel = pd.read_csv(ROOT / "data/processed/research_panel_2026-09-11.csv")
    panel["research_date"] = pd.to_datetime(panel["research_date"])

    metrics = evaluate_all_factors(panel, ALL_FACTORS, primary_label=PRIMARY_LABEL)
    metrics = metrics.sort_values("mean_ic", ascending=False).reset_index(drop=True)
    metrics.to_csv(ROOT / "reports/factor_metrics.csv", index=False)

    # Figure 1: mean Rank IC bar chart (primary 5D horizon)
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = ["#2a7f62" if v > 0 else "#c0392b" for v in metrics["mean_ic"]]
    ax.barh(metrics["factor"], metrics["mean_ic"], color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Mean Rank IC (5D relative return)")
    ax.set_title("Mean Rank IC by factor (8-security universe; n_dates shown in table)")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "mean_rank_ic_by_factor.png", dpi=140)
    plt.close(fig)

    # Figure 2: IC heatmap by factor/horizon
    heat = metrics.set_index("factor")[["ic_1d", "ic_5d", "ic_20d"]]
    fig, ax = plt.subplots(figsize=(6, 8))
    im = ax.imshow(heat.values, aspect="auto", cmap="RdBu_r", vmin=-0.3, vmax=0.3)
    ax.set_yticks(range(len(heat.index))); ax.set_yticklabels(heat.index)
    ax.set_xticks(range(3)); ax.set_xticklabels(["1D", "5D", "20D"])
    ax.set_title("Mean Rank IC by factor and horizon")
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            v = heat.values[i, j]
            if pd.notna(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, label="Mean Rank IC")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "ic_heatmap_factor_horizon.png", dpi=140)
    plt.close(fig)

    # Figure 3: IC time series for the two strongest factors by |mean_ic|
    strongest = metrics.reindex(metrics["mean_ic"].abs().sort_values(ascending=False).index).head(2)["factor"].tolist()
    fig, ax = plt.subplots(figsize=(10, 4))
    for f in strongest:
        ic = daily_rank_ic(panel, f, PRIMARY_LABEL)
        if ic.empty:
            continue
        ic = ic.sort_values("research_date")
        ax.plot(ic["research_date"], ic["rank_ic"].rolling(20, min_periods=5).mean(), label=f)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("20-week rolling mean Rank IC, two strongest factors")
    ax.legend()
    plt.tight_layout()
    fig.savefig(FIG_DIR / "ic_time_series_strongest.png", dpi=140)
    plt.close(fig)

    # Figure 4: quintile monotonicity for the strongest factor
    top_factor = strongest[0]
    q = quantile_returns(panel, top_factor, PRIMARY_LABEL, n_quantiles=5)
    fig, ax = plt.subplots(figsize=(6, 4))
    if not q.empty:
        q = q.sort_values("quantile")
        ax.bar(q["quantile"].astype(str), q["mean"])
    ax.set_title(f"Quintile mean 5D relative return: {top_factor}\n(n=8/date; each quintile ~1-2 names)")
    ax.set_xlabel("Quintile (0=low, 4=high)")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "quintile_monotonicity_top_factor.png", dpi=140)
    plt.close(fig)

    # Figure 5: alpha decay across horizons for top 5 factors by |mean_ic|
    top5 = metrics.reindex(metrics["mean_ic"].abs().sort_values(ascending=False).index).head(5)
    fig, ax = plt.subplots(figsize=(8, 5))
    for _, row in top5.iterrows():
        ax.plot(["1D", "5D", "20D"], [row["ic_1d"], row["ic_5d"], row["ic_20d"]], marker="o", label=row["factor"])
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Alpha decay: mean Rank IC by horizon (top 5 |IC| factors)")
    ax.legend()
    plt.tight_layout()
    fig.savefig(FIG_DIR / "alpha_decay.png", dpi=140)
    plt.close(fig)

    # Figure 6: factor correlation heatmap
    corr = panel[ALL_FACTORS].corr(method="spearman")
    fig, ax = plt.subplots(figsize=(9, 8))
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr))); ax.set_xticklabels(corr.columns, rotation=90, fontsize=7)
    ax.set_yticks(range(len(corr))); ax.set_yticklabels(corr.index, fontsize=7)
    fig.colorbar(im, ax=ax, label="Spearman correlation")
    ax.set_title("Factor correlation matrix (Spearman, all rows)")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "factor_correlation_heatmap.png", dpi=140)
    plt.close(fig)

    print(metrics[["factor", "n_dates", "coverage_pct", "mean_ic", "icir", "pct_positive"]].to_string(index=False))
    print("\nsaved reports/factor_metrics.csv and 6 figures to reports/figures/")


if __name__ == "__main__":
    main()
